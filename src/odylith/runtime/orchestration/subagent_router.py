"""Accuracy-first subagent routing for bounded Codex delegation.

This module provides one centralized contract for deciding whether a bounded
task should stay in the main thread or be delegated to a subagent with an
explicit model and reasoning-effort profile.

Invariants:
- Hard main-thread refusal gates always win over weighted scoring.
- `gpt-5.4` `xhigh` remains a gated tier and is never the default score winner
  unless a critical-risk gate or explicit escalation unlocks it.
- Adaptive tuning only shifts soft profile bias in local gitignored state under
  `.odylith/`; it never changes hard-gate semantics.
- Route audit can reuse Compass local timeline events, but that audit path is
  optional and remains local-only runtime state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence
import uuid

from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.common import log_compass_timeline_event as compass_timeline
from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.evaluation import odylith_evaluation_ledger
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.orchestration import subagent_router_assessment_runtime
from odylith.runtime.orchestration import subagent_router_runtime_policy


_SCORE_MIN = 0
_SCORE_MAX = 4
_TUNING_VERSION = "v1"
DEFAULT_TUNING_PATH = ".odylith/subagent_router/tuning.v1.json"
DEFAULT_STREAM_PATH = "odylith/compass/runtime/codex-stream.v1.jsonl"
DEFAULT_COMPONENT_ID = "subagent-router"
_PROFILE_BIAS_LIMIT = 0.75
_DEFAULT_BIAS_DELTA = 0.05
_DEFAULT_FAMILY_BIAS_DELTA = 0.07
_OUTCOME_LEDGER_LIMIT = 512
_DEFAULT_IDLE_TIMEOUT_MINUTES = 10
_DEFAULT_REUSE_WINDOW = "explicit_same_scope_followup_queued_only"
_DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES = 3
_DEFAULT_WAITING_POLICY = "send_input_or_close"
_DEFAULT_IDLE_TIMEOUT_ACTION = "close_agent"
_DEFAULT_IDLE_TIMEOUT_ESCALATION = "resume_main_thread_or_reroute_fresh_slice"
_HOST_SUPPORTED_AGENT_TYPES: tuple[str, ...] = ("default", "explorer", "worker")
_HOST_UI_VISIBILITY_NOTE = (
    "Codex desktop may still show parent-thread model/reasoning controls in the delegated thread UI "
    "for some combinations even when explicit spawn overrides are passed."
)
_HOST_CUSTOM_AGENT_TYPE_NOTE = (
    "The current native `spawn_agent` tool accepts only built-in `agent_type` values "
    "(`default`, `explorer`, `worker`), so named custom agents from `.codex/agents/` "
    "are not selectable through this host tool."
)
_PROFILE_PRIORITY: dict[str, int] = {
    "main_thread": 0,
    "mini_medium": 1,
    "mini_high": 2,
    "spark_medium": 3,
    "codex_medium": 4,
    "codex_high": 5,
    "gpt54_high": 6,
    "gpt54_xhigh": 7,
}
_RUNTIME_EARNED_DEPTH_SELECTION_MODES: frozenset[str] = frozenset(
    {
        "critical_accuracy",
        "deep_validation",
        "implementation_primary",
        "bounded_write",
        "validation_focused",
        "analysis_synthesis",
        "architecture_grounding",
        "architecture_change",
    }
)
_RUNTIME_SUPPORT_SELECTION_MODES: frozenset[str] = frozenset(
    {
        "support_fast_lane",
        "analysis_scout",
        "validation_support",
        "architecture_synthesis",
    }
)
_WRITE_KEYWORDS: tuple[str, ...] = (
    "implement",
    "build",
    "add",
    "create",
    "change",
    "edit",
    "patch",
    "refactor",
    "update",
    "fix",
)
_MECHANICAL_KEYWORDS: tuple[str, ...] = (
    "rename",
    "typo",
    "format",
    "lint",
    "comment",
    "docstring",
    "boilerplate",
    "mechanical",
    "simple",
    "small",
)
_AMBIGUITY_KEYWORDS: tuple[str, ...] = (
    "investigate",
    "why",
    "not sure",
    "unclear",
    "ambiguous",
    "review",
    "audit",
    "design",
    "figure out",
    "deep",
)
_RISK_KEYWORDS: tuple[str, ...] = (
    "auth",
    "security",
    "migration",
    "schema",
    "shared",
    "control-plane",
    "release",
    "contract",
    "policy",
    "deployment",
    "critical",
    "incident",
    "customer impact",
    "data loss",
    "privacy",
    "outage",
    "availability",
    "production",
)
_REVERSIBILITY_KEYWORDS: tuple[str, ...] = (
    "delete",
    "migrate",
    "rollback",
    "contract",
    "policy",
    "release",
    "security",
    "auth",
)
_LATENCY_KEYWORDS: tuple[str, ...] = (
    "quick",
    "fast",
    "urgent",
    "hotfix",
    "small",
    "tiny",
)
_DEPTH_KEYWORDS: tuple[str, ...] = (
    "accurate",
    "accuracy",
    "thorough",
    "deep",
    "careful",
    "robust",
    "high confidence",
    "xhigh",
)
_VALIDATION_KEYWORDS: tuple[str, ...] = (
    "test",
    "tests",
    "pytest",
    "validate",
    "validation",
    "verify",
    "verification",
    "check",
    "checks",
    "prove",
    "coverage",
    "regression",
    "reproduce",
    "make ",
)
_COORDINATION_KEYWORDS: tuple[str, ...] = (
    "plan",
    "design",
    "integrate",
    "coordinate",
    "merge",
    "handoff",
    "rollout",
    "communication",
    "multi-agent",
    "cross-worker",
)
_FEATURE_KEYWORDS: tuple[str, ...] = (
    "feature",
    "new capability",
    "add support",
    "build support",
    "new flow",
    "new behavior",
)
_TRIVIAL_EXPLANATION_KEYWORDS: tuple[str, ...] = (
    "what is",
    "how do",
    "explain",
    "summarize",
    "define",
    "why is",
)
_READ_ONLY_SYNTHESIS_KEYWORDS: tuple[str, ...] = (
    "single root cause",
    "root cause",
    "compare",
    "tradeoff",
    "best design",
    "design direction",
    "recommend",
    "choose",
    "decision",
    "synthesize",
)
_DIAGNOSTIC_KEYWORDS: tuple[str, ...] = (
    "diagnose",
    "diagnostic",
    "root cause",
    "failure mode",
    "regression",
    "investigate",
    "why",
    "trace",
    "forensics",
)
_BOUNDED_SCOPE_KEYWORDS: tuple[str, ...] = (
    "bounded",
    "keep the change isolated",
    "focused",
    "only",
    "limit",
    "isolated",
    "single file",
    "exact",
    "specific",
)
_OPEN_ENDED_SCOPE_KEYWORDS: tuple[str, ...] = (
    "architecture",
    "architectural",
    "strategy",
    "system-wide",
    "repo-wide",
    "across the repository",
    "broad refactor",
    "sweeping",
    "holistic",
    "end-to-end",
    "redesign",
)
_KNOWN_TASK_FAMILIES: tuple[str, ...] = (
    "mechanical_patch",
    "bounded_bugfix",
    "bounded_feature",
    "analysis_review",
    "critical_change",
    "coordination_heavy",
)
_EXPLICIT_PATH_TOKEN_RE = re.compile(r"(?P<token>[A-Za-z0-9_./-]+)")
_EXPLICIT_PATH_PREFIXES: tuple[str, ...] = (
    "agents-guidelines/",
    "alerts/",
    "bin/",
    "odylith/casebook/bugs/",
    "configs/",
    "contracts/",
    "odylith/runtime/contracts/",
    "docker/",
    "docs/",
    "infra/",
    "mk/",
    "mocks/",
    "monitoring/",
    "app/",
    "odylith/technical-plans/",
    "policies/",
    "src/",
    "services/",
    "skills/",
    "tests/",
)
_EXPLICIT_ROOT_FILES: frozenset[str] = frozenset(
    {
        ".gitignore",
        "AGENTS.md",
        "Makefile",
        "README.md",
        "hatch.toml",
        "platform_envs.sh",
        "pyproject.toml",
    }
)
_VALIDATION_ONLY_TEST_PHRASES: tuple[str, ...] = (
    "keep tests green",
    "keep the tests green",
    "tests green",
    "pass tests",
    "passing tests",
    "run tests",
)


@dataclass(frozen=True)
class ImpliedWriteSurfaceRule:
    """Prompt phrases that imply a write surface must be declared explicitly."""

    surface_key: str
    phrases: tuple[str, ...]
    required_prefixes: frozenset[str]
    label: str


_IMPLIED_WRITE_SURFACE_RULES: tuple[ImpliedWriteSurfaceRule, ...] = (
    ImpliedWriteSurfaceRule(
        surface_key="tests",
        phrases=(
            "matching tests",
            "update tests",
            "update the tests",
            "refresh tests",
            "refresh the tests",
            "add tests",
            "add a test",
            "add regression test",
            "add regression tests",
            "focused test",
            "focused tests",
            "test coverage",
        ),
        required_prefixes=frozenset({"tests", "mocks"}),
        label="tests/",
    ),
    ImpliedWriteSurfaceRule(
        surface_key="docs",
        phrases=("documentation", "docs", "runbook", "operator guidance", "skill", "skills"),
        required_prefixes=frozenset({"docs", "skills", "agents-guidelines"}),
        label="docs/skills/agents-guidelines",
    ),
    ImpliedWriteSurfaceRule(
        surface_key="governance",
        phrases=("diagram", "atlas", "registry", "component registry", "mermaid", "catalog"),
        required_prefixes=frozenset({"odylith"}),
        label="odylith/ governed artifact paths",
    ),
    ImpliedWriteSurfaceRule(
        surface_key="contracts",
        phrases=("contract", "schema"),
        required_prefixes=frozenset({"contracts", "odylith/runtime/contracts"}),
        label="contracts/ or odylith/runtime/contracts/",
    ),
)

_ODYLITH_DOC_SURFACE_SEGMENTS: frozenset[str] = frozenset(
    {
        "agents-guidelines",
        "atlas",
        "casebook",
        "docs",
        "radar",
        "registry",
        "runtime",
        "skills",
        "surfaces",
        "technical-plans",
    }
)


def _delegated_profile_values() -> tuple[str, ...]:
    return (
        RouterProfile.MINI_MEDIUM.value,
        RouterProfile.MINI_HIGH.value,
        RouterProfile.SPARK_MEDIUM.value,
        RouterProfile.CODEX_MEDIUM.value,
        RouterProfile.CODEX_HIGH.value,
        RouterProfile.GPT54_HIGH.value,
        RouterProfile.GPT54_XHIGH.value,
    )


def _default_profile_bias_map() -> dict[str, float]:
    return {profile: 0.0 for profile in _delegated_profile_values()}


def _default_outcome_counts_map() -> dict[str, dict[str, int]]:
    return {profile: {} for profile in _delegated_profile_values()}


def _default_family_profile_bias_map() -> dict[str, dict[str, float]]:
    return {family: _default_profile_bias_map() for family in _KNOWN_TASK_FAMILIES}


def _default_family_outcome_counts_map() -> dict[str, dict[str, dict[str, int]]]:
    return {family: _default_outcome_counts_map() for family in _KNOWN_TASK_FAMILIES}


class RouterProfile(str, Enum):
    MAIN_THREAD = "main_thread"
    MINI_MEDIUM = "mini_medium"
    MINI_HIGH = "mini_high"
    SPARK_MEDIUM = "spark_medium"
    CODEX_MEDIUM = "codex_medium"
    CODEX_HIGH = "codex_high"
    GPT54_HIGH = "gpt54_high"
    GPT54_XHIGH = "gpt54_xhigh"

    @property
    def model(self) -> str:
        if self in {RouterProfile.MINI_MEDIUM, RouterProfile.MINI_HIGH}:
            return "gpt-5.4-mini"
        if self is RouterProfile.SPARK_MEDIUM:
            return "gpt-5.3-codex-spark"
        if self in {RouterProfile.CODEX_MEDIUM, RouterProfile.CODEX_HIGH}:
            return "gpt-5.3-codex"
        if self is RouterProfile.MAIN_THREAD:
            return ""
        return "gpt-5.4"

    @property
    def reasoning_effort(self) -> str:
        if self in {RouterProfile.MINI_MEDIUM, RouterProfile.SPARK_MEDIUM, RouterProfile.CODEX_MEDIUM}:
            return "medium"
        if self is RouterProfile.GPT54_XHIGH:
            return "xhigh"
        if self is RouterProfile.MAIN_THREAD:
            return ""
        return "high"


def _router_profile_from_token(value: Any) -> RouterProfile | None:
    token = _normalize_token(value)
    try:
        return RouterProfile(token)
    except ValueError:
        return None


def _router_profile_from_runtime(model: Any, reasoning_effort: Any) -> RouterProfile | None:
    runtime_model = _normalize_string(model)
    runtime_reasoning = _normalize_token(reasoning_effort)
    if runtime_model == "gpt-5.4-mini":
        if runtime_reasoning == "high":
            return RouterProfile.MINI_HIGH
        if runtime_reasoning == "medium":
            return RouterProfile.MINI_MEDIUM
    if runtime_model == "gpt-5.3-codex-spark" and runtime_reasoning == "medium":
        return RouterProfile.SPARK_MEDIUM
    if runtime_model == "gpt-5.3-codex":
        if runtime_reasoning == "high":
            return RouterProfile.CODEX_HIGH
        if runtime_reasoning == "medium":
            return RouterProfile.CODEX_MEDIUM
    if runtime_model == "gpt-5.4":
        if runtime_reasoning == "xhigh":
            return RouterProfile.GPT54_XHIGH
        if runtime_reasoning == "high":
            return RouterProfile.GPT54_HIGH
    return None


class RouterInputError(ValueError):
    """Fail-closed router input or compatibility error."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: Sequence[str] | None = None,
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.code = _normalize_token(code) or "router_input_error"
        self.message = _normalize_string(message) or "router input error"
        self.details = [_normalize_string(item) for item in (details or []) if _normalize_string(item)]
        self.exit_code = int(exit_code)

    def as_payload(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error_code": self.code,
            "message": self.message,
            "details": list(self.details),
        }


@dataclass
class RouteRequest:
    """Bounded route request gathered before delegation."""

    prompt: str
    acceptance_criteria: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    workstreams: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    phase: str = ""
    task_kind: str = ""
    needs_write: bool = False
    latency_sensitive: bool = False
    correctness_critical: bool = False
    requires_multi_agent_adjudication: bool = False
    evolving_context_required: bool = False
    evidence_cone_grounded: bool = False
    accuracy_preference: str = "accuracy"
    context_signals: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskAssessment:
    """Normalized feature scores that drive the route decision."""

    prompt: str
    task_kind: str
    task_family: str
    phase: str
    needs_write: bool
    correctness_critical: bool
    feature_implementation: bool
    mixed_phase: bool
    requires_multi_agent_adjudication: bool
    evolving_context_required: bool
    evidence_cone_grounded: bool
    ambiguity: int
    blast_radius: int
    context_breadth: int
    coordination_cost: int
    reversibility_risk: int
    mechanicalness: int
    write_scope_clarity: int
    acceptance_clarity: int
    artifact_specificity: int
    validation_clarity: int
    latency_pressure: int
    requested_depth: int
    accuracy_bias: int
    earned_depth: int
    delegation_readiness: int
    base_confidence: int
    accuracy_preference: str
    phase_tokens: list[str] = field(default_factory=list)
    semantic_signals: dict[str, list[str]] = field(default_factory=dict)
    hard_gate_hits: list[str] = field(default_factory=list)
    feature_reasons: dict[str, list[str]] = field(default_factory=dict)
    context_signal_summary: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RoutingDecision:
    """Selected profile or explicit main-thread refusal."""

    delegate: bool
    profile: str
    model: str
    reasoning_effort: str
    agent_role: str
    close_after_result: bool
    idle_timeout_minutes: int
    reuse_window: str
    waiting_policy: str
    why: str
    escalation_profile: str
    hard_gate_hits: list[str]
    prequeue_same_scope_reuse_claim_minutes: int = 0
    decision_id: str = ""
    task_family: str = ""
    refusal_stage: str = ""
    routing_confidence: int = 0
    manual_review_recommended: bool = False
    rescope_required: bool = False
    score_margin: float = 0.0
    failure_signals: list[str] = field(default_factory=list)
    prompt_wrapper_delta: list[str] = field(default_factory=list)
    spawn_overrides: dict[str, Any] = field(default_factory=dict)
    spawn_agent_overrides: dict[str, Any] = field(default_factory=dict)
    close_agent_overrides: dict[str, Any] = field(default_factory=dict)
    host_tool_contract: dict[str, Any] = field(default_factory=dict)
    runtime_banner_lines: list[str] = field(default_factory=list)
    spawn_task_message: str = ""
    native_spawn_payload: dict[str, Any] = field(default_factory=dict)
    spawn_contract_lines: list[str] = field(default_factory=list)
    idle_timeout_action: str = ""
    idle_timeout_escalation: str = ""
    termination_expectation: str = ""
    task_class_profile: str = ""
    task_class_model: str = ""
    task_class_reasoning_effort: str = ""
    task_class_policy_lines: list[str] = field(default_factory=list)
    explanation_lines: list[str] = field(default_factory=list)
    scorecard: dict[str, float] = field(default_factory=dict)
    assessment: dict[str, Any] = field(default_factory=dict)
    odylith_execution_profile: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.why = _sanitize_user_facing_text(self.why)
        self.explanation_lines = _sanitize_user_facing_lines(self.explanation_lines)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteOutcome:
    """Structured result classification for one delegated pass."""

    accepted: bool = False
    blocked: bool = False
    ambiguous: bool = False
    artifact_missing: bool = False
    quality_too_weak: bool = False
    escalated: bool = False
    broader_coordination: bool = False
    outcome_id: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TuningState:
    """Local-only adaptive tuning state."""

    version: str = _TUNING_VERSION
    updated_at: str = ""
    profile_bias: dict[str, float] = field(default_factory=_default_profile_bias_map)
    outcome_counts: dict[str, dict[str, int]] = field(default_factory=_default_outcome_counts_map)
    family_profile_bias: dict[str, dict[str, float]] = field(default_factory=_default_family_profile_bias_map)
    family_outcome_counts: dict[str, dict[str, dict[str, int]]] = field(default_factory=_default_family_outcome_counts_map)
    applied_outcome_keys: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskClassPolicy:
    """Explicit routed baseline for each delegated task family."""

    task_family: str
    default_profile: RouterProfile
    minimum_profile: RouterProfile
    default_agent_role: str
    rationale: str


@dataclass(frozen=True)
class DelegatedLeafLifecyclePayload:
    """One routed source of truth for native spawn and closeout handoff."""

    agent_role: str
    termination_expectation: str
    spawn_overrides: dict[str, Any]
    spawn_agent_overrides: dict[str, Any]
    close_agent_overrides: dict[str, Any]
    host_tool_contract: dict[str, Any]
    runtime_banner_lines: list[str]


_TASK_CLASS_POLICIES: dict[str, TaskClassPolicy] = {
    "mechanical_patch": TaskClassPolicy(
        task_family="mechanical_patch",
        default_profile=RouterProfile.SPARK_MEDIUM,
        minimum_profile=RouterProfile.SPARK_MEDIUM,
        default_agent_role="worker",
        rationale="Mechanical bounded edits default to Spark medium for speed unless stronger accuracy signals promote them.",
    ),
    "bounded_bugfix": TaskClassPolicy(
        task_family="bounded_bugfix",
        default_profile=RouterProfile.CODEX_MEDIUM,
        minimum_profile=RouterProfile.CODEX_MEDIUM,
        default_agent_role="worker",
        rationale="Bounded understood fixes default to Codex medium so code-writing leaves use a coding-optimized tier before promoting deeper.",
    ),
    "bounded_feature": TaskClassPolicy(
        task_family="bounded_feature",
        default_profile=RouterProfile.CODEX_HIGH,
        minimum_profile=RouterProfile.CODEX_MEDIUM,
        default_agent_role="worker",
        rationale="New bounded write behavior defaults to Codex high, with GPT-5.4 reserved for the riskier or more architecture-heavy cases.",
    ),
    "analysis_review": TaskClassPolicy(
        task_family="analysis_review",
        default_profile=RouterProfile.MINI_HIGH,
        minimum_profile=RouterProfile.MINI_MEDIUM,
        default_agent_role="explorer",
        rationale="Bounded read-only analysis defaults to a high-effort GPT-5.4 mini explorer tier and promotes only when ambiguity or risk demand more depth.",
    ),
    "critical_change": TaskClassPolicy(
        task_family="critical_change",
        default_profile=RouterProfile.GPT54_HIGH,
        minimum_profile=RouterProfile.GPT54_HIGH,
        default_agent_role="worker",
        rationale="Critical or hard-to-reverse changes default to GPT-5.4 high; `xhigh` stays gated behind explicit risk triggers.",
    ),
    "coordination_heavy": TaskClassPolicy(
        task_family="coordination_heavy",
        default_profile=RouterProfile.MAIN_THREAD,
        minimum_profile=RouterProfile.MAIN_THREAD,
        default_agent_role="main_thread",
        rationale="Coordination-heavy work should stay local and be re-scoped before any delegated retry.",
    ),
}


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_multiline_string(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_string(item) for item in value if _normalize_string(item)]
    token = _normalize_string(value)
    return [token] if token else []


def _assessment_host_runtime(assessment: TaskAssessment) -> str:
    summary = dict(assessment.context_signal_summary or {})
    return host_runtime_contract.resolve_host_runtime(
        summary.get("host_runtime"),
        summary.get("odylith_execution_host_runtime"),
    )


def _native_spawn_supported_for_assessment(assessment: TaskAssessment) -> bool:
    return host_runtime_contract.native_spawn_supported(
        _assessment_host_runtime(assessment),
        default_when_unknown=False,
    )


def _count_or_list_len(payload: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    value = _mapping_value(payload, list_key)
    return max(
        len(value) if isinstance(value, list) else len(_normalize_list(value)),
        _int_value(_mapping_value(payload, count_key)),
    )


def _normalize_context_signals(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {_normalize_string(key): raw for key, raw in value.items() if _normalize_string(key)}


def _embedded_governance_signal(context_packet: Mapping[str, Any]) -> dict[str, Any]:
    route = _mapping_value(context_packet, "route")
    if not isinstance(route, Mapping):
        return {}
    governance = _mapping_value(route, "governance")
    if not isinstance(governance, Mapping):
        return {}
    return {
        _normalize_string(key): raw
        for key, raw in governance_signal_codec.expand_governance_signal(governance).items()
        if _normalize_string(key) and raw not in ("", [], {}, None, False)
    }


def _validation_bundle_from_context(
    context_signals: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    validation_bundle = _mapping_value(context_signals, "validation_bundle")
    if isinstance(validation_bundle, Mapping):
        return dict(validation_bundle)
    governance = _embedded_governance_signal(context_packet)
    compact: dict[str, Any] = {}
    for key in (
        "recommended_command_count",
        "strict_gate_command_count",
        "plan_binding_required",
        "governed_surface_sync_required",
    ):
        value = _mapping_value(governance, key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _governance_obligations_from_context(
    context_signals: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    governance_obligations = _mapping_value(context_signals, "governance_obligations")
    if isinstance(governance_obligations, Mapping):
        return dict(governance_obligations)
    governance = _embedded_governance_signal(context_packet)
    compact: dict[str, Any] = {}
    for key in (
        "touched_workstream_count",
        "primary_workstream_id",
        "touched_component_count",
        "primary_component_id",
        "required_diagram_count",
        "linked_bug_count",
        "closeout_doc_count",
        "workstream_state_action_count",
    ):
        value = _mapping_value(governance, key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _surface_refs_from_context(
    context_signals: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    surface_refs = _mapping_value(context_signals, "surface_refs")
    if isinstance(surface_refs, Mapping):
        return dict(surface_refs)
    governance = _embedded_governance_signal(context_packet)
    compact: dict[str, Any] = {}
    for key in ("surface_count", "reason_group_count"):
        value = _mapping_value(governance, key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _extract_context_signals_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    explicit = payload.get("context_signals")
    if isinstance(explicit, Mapping):
        return _normalize_context_signals(explicit)
    extracted: dict[str, Any] = {}
    for key in (
        "routing_handoff",
        "context_packet",
        "evidence_pack",
        "optimization_snapshot",
        "architecture_audit",
        "validation_bundle",
        "governance_obligations",
        "surface_refs",
    ):
        value = payload.get(key)
        if isinstance(value, Mapping):
            extracted[key] = dict(value)
    diagram_watch_gaps = payload.get("diagram_watch_gaps")
    if isinstance(diagram_watch_gaps, list):
        extracted["diagram_watch_gaps"] = list(diagram_watch_gaps)
    if extracted:
        return _normalize_context_signals(extracted)
    return _normalize_context_signals(payload.get("routing_handoff", {}))


def _mapping_value(payload: Mapping[str, Any], key: str) -> Any:
    wanted = _normalize_token(key)
    for raw_key, raw_value in payload.items():
        if _normalize_token(raw_key) == wanted:
            return raw_value
    alias = {
        "parallelism_hint": "p",
        "reasoning_bias": "b",
        "routing_confidence": "rc",
        "intent_family": "i",
        "intent_mode": "m",
        "intent_critical_path": "cp",
        "intent_confidence": "ic",
        "intent_explicit": "ix",
        "context_richness": "cr",
        "accuracy_posture": "ap",
        "utility_score": "us",
        "context_density_level": "cd",
        "reasoning_readiness_level": "rr",
    }.get(wanted, "")
    if alias:
        for raw_key, raw_value in payload.items():
            if _normalize_token(raw_key) == alias:
                return raw_value
    return None


def _context_signal_root(context_signals: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = _mapping_value(context_signals, "routing_handoff")
    return nested if isinstance(nested, Mapping) else context_signals


def _context_lookup(payload: Mapping[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = _mapping_value(current, key)
    return current


def _selected_counts_mapping(value: Any) -> dict[str, int]:
    if isinstance(value, Mapping):
        return {
            str(key).strip(): _int_value(raw)
            for key, raw in value.items()
            if str(key).strip() and _int_value(raw) > 0
        }
    token = _normalize_token(value)
    if not token:
        return {}
    alias_map = {
        "c": "commands",
        "d": "docs",
        "t": "tests",
        "g": "guidance",
    }
    counts: dict[str, int] = {}
    for alias, raw_count in re.findall(r"([cdtg])(\d+)", token):
        key = alias_map.get(alias, "")
        count = _int_value(raw_count)
        if key and count > 0:
            counts[key] = count
    return counts


def _context_signal_score(value: Any) -> int:
    if isinstance(value, bool):
        return _SCORE_MAX if value else _SCORE_MIN
    if isinstance(value, (int, float)):
        return _clamp_score(value)
    if isinstance(value, Mapping):
        for key in ("score", "level", "confidence", "rating", "value"):
            nested = _mapping_value(value, key)
            if nested is not None:
                return _context_signal_score(nested)
        return _SCORE_MIN
    token = _normalize_token(value)
    if token in {"none", "unknown", "false", "unready", "blocked"}:
        return 0
    if token in {"low", "weak", "light", "minimal"}:
        return 1
    if token in {"medium", "moderate", "partial"}:
        return 2
    if token in {"high", "strong", "grounded", "actionable", "ready"}:
        return 3
    if token in {"very_high", "max", "maximum", "full"}:
        return 4
    return 0


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


_USER_FACING_CHATTER_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("The current runtime handoff", "The current slice"),
    ("the current runtime handoff", "the current slice"),
    ("The retained runtime handoff", "The current slice"),
    ("the retained runtime handoff", "the current slice"),
    ("The retained context packet", "The current slice"),
    ("the retained context packet", "the current slice"),
    ("The current retained packet", "The current slice"),
    ("the current retained packet", "the current slice"),
    ("The retained packet", "The current slice"),
    ("the retained packet", "the current slice"),
    ("runtime handoff", "current slice"),
    ("runtime context packet", "current slice"),
    ("Control advisories", "Recent execution evidence"),
    ("control advisories", "recent execution evidence"),
    ("advisory loop", "recent execution evidence"),
    ("packetizer alignment", "execution fit"),
    ("runtime-backed", "measured"),
    ("native-spawn-ready", "delegation-ready"),
    ("route-ready", "ready for delegation"),
    ("hold-local", "local-first"),
    ("runtime memory contracts", "grounded evidence"),
    ("runtime contracts", "grounded contracts"),
    ("runtime optimization posture", "recent execution posture"),
    ("retained evidence pack", "current evidence set"),
)


def _sanitize_user_facing_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for needle, replacement in _USER_FACING_CHATTER_REPLACEMENTS:
        text = text.replace(needle, replacement)
    return re.sub(r"\s+", " ", text).strip()


def _sanitize_user_facing_lines(values: Sequence[str]) -> list[str]:
    return _dedupe_strings(_sanitize_user_facing_text(value) for value in values)


def _context_signal_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) > 0
    if isinstance(value, Mapping):
        for key in ("enabled", "ready", "supported", "allowed", "active", "value"):
            nested = _mapping_value(value, key)
            if nested is not None:
                return _context_signal_bool(nested)
    token = _normalize_token(value)
    return token in {"1", "true", "yes", "y", "on", "ready", "supported", "primary", "support"}


def _context_signal_level(score: int) -> str:
    value = _clamp_score(score)
    if value >= 4:
        return "high"
    if value >= 2:
        return "medium"
    if value >= 1:
        return "low"
    return "none"


def _scaled_numeric_signal(value: Any) -> int:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return _clamp_score(round(numeric * _SCORE_MAX))
        if numeric > _SCORE_MAX:
            return _clamp_score(round(numeric / 25.0))
        return _clamp_score(numeric)
    return _context_signal_score(value)


def _normalized_rate(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric = numeric / 100.0 if numeric <= 100.0 else 1.0
    return max(0.0, min(1.0, numeric))


def _latency_pressure_signal(value: Any) -> int:
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        return 0
    if numeric >= 12000.0:
        return 4
    if numeric >= 6000.0:
        return 3
    if numeric >= 2500.0:
        return 2
    if numeric >= 1000.0:
        return 1
    return 0


def _execution_profile_candidate(value: Any) -> dict[str, Any]:
    return tooling_memory_contracts.execution_profile_mapping(value)


def _synthesized_execution_profile_candidate(
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    if not bool(route.get("route_ready")) or bool(route.get("narrowing_required")):
        return {}
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    selected_counts = _selected_counts_mapping(retrieval_plan.get("selected_counts"))
    governance = governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), Mapping) else {}
    )
    family = _normalize_token(packet_quality.get("intent_family"))
    confidence = _normalize_token(packet_quality.get("routing_confidence"))
    validation_count = _int_value(selected_counts.get("tests")) + _int_value(selected_counts.get("commands"))
    guidance_count = _int_value(selected_counts.get("guidance"))
    governance_contract = any(
        (
            _int_value(governance.get("closeout_doc_count")) > 0,
            _int_value(governance.get("strict_gate_command_count")) > 0,
            _normalize_bool(governance.get("plan_binding_required")),
            _normalize_bool(governance.get("governed_surface_sync_required")),
        )
    )
    profile = "mini_medium"
    model = "gpt-5.4-mini"
    reasoning_effort = "medium"
    agent_role = "explorer"
    selection_mode = "analysis_scout"
    if family in {"implementation", "write", "bugfix"}:
        if governance_contract and _int_value(governance.get("strict_gate_command_count")) > 0:
            profile = "gpt54_high"
            model = "gpt-5.4"
            reasoning_effort = "high"
            selection_mode = "deep_validation"
        else:
            profile = "codex_high" if confidence == "high" and (validation_count > 0 or guidance_count >= 2) else "codex_medium"
            model = "gpt-5.3-codex"
            reasoning_effort = "high" if profile == "codex_high" else "medium"
            selection_mode = "bounded_write"
        agent_role = "worker"
    elif family == "validation":
        profile = "codex_high" if confidence == "high" or validation_count >= 2 else "codex_medium"
        model = "gpt-5.3-codex"
        reasoning_effort = "high" if profile == "codex_high" else "medium"
        agent_role = "worker"
        selection_mode = "validation_focused"
    elif family in {"docs", "governance"}:
        profile = "spark_medium" if governance_contract else "mini_medium"
        model = "gpt-5.3-codex-spark" if profile == "spark_medium" else "gpt-5.4-mini"
        reasoning_effort = "medium"
        agent_role = "worker" if profile == "spark_medium" else "explorer"
        selection_mode = "support_fast_lane" if profile == "spark_medium" else "analysis_scout"
    elif family in {"analysis", "review", "diagnosis"}:
        profile = "mini_high" if confidence == "high" or governance_contract or validation_count > 0 or guidance_count > 0 else "mini_medium"
        model = "gpt-5.4-mini"
        reasoning_effort = "high" if profile == "mini_high" else "medium"
        agent_role = "explorer"
        selection_mode = "analysis_synthesis" if profile == "mini_high" else "analysis_scout"
    return {
        "profile": profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "agent_role": agent_role,
        "selection_mode": selection_mode,
        "delegate_preference": "delegate",
        "source": "context_packet_route",
    }


def _execution_profile_mapping(
    *,
    root: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    evidence_pack: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return subagent_router_runtime_policy._execution_profile_mapping(root=root, context_packet=context_packet, evidence_pack=evidence_pack, optimization_snapshot=optimization_snapshot)



def _preferred_router_profile_from_execution_profile(profile: Mapping[str, Any]) -> RouterProfile | None:
    return subagent_router_runtime_policy._preferred_router_profile_from_execution_profile(profile=profile)



def _decision_odylith_execution_profile(
    *,
    assessment: TaskAssessment,
    selected: RouterProfile | None = None,
) -> dict[str, Any]:
    return subagent_router_runtime_policy._decision_odylith_execution_profile(assessment=assessment, selected=selected)



def _odylith_execution_guard_reason(assessment: TaskAssessment) -> str:
    return subagent_router_runtime_policy._odylith_execution_guard_reason(assessment=assessment)



def _apply_odylith_execution_priors(
    *,
    scorecard: Mapping[str, float],
    assessment: TaskAssessment,
    allow_xhigh: bool,
) -> tuple[dict[str, float], list[str]]:
    return subagent_router_runtime_policy._apply_odylith_execution_priors(scorecard=scorecard, assessment=assessment, allow_xhigh=allow_xhigh)



def _build_host_message(*sections: Sequence[str]) -> str:
    rendered_sections: list[str] = []
    for section in sections:
        lines = [_normalize_multiline_string(line) for line in section if _normalize_multiline_string(line)]
        if lines:
            rendered_sections.append("\n".join(lines))
    return "\n\n".join(rendered_sections).strip()


def _clamp_score(value: int | float) -> int:
    return max(_SCORE_MIN, min(_SCORE_MAX, int(round(float(value)))))


def _clamp_bias(value: float) -> float:
    return max(-_PROFILE_BIAS_LIMIT, min(_PROFILE_BIAS_LIMIT, float(value)))


def _agent_role_for_assessment(
    assessment: TaskAssessment,
    *,
    profile: RouterProfile | None = None,
) -> str:
    if assessment.needs_write:
        return "worker"
    summary = dict(assessment.context_signal_summary or {})
    recommended_role = _normalize_token(summary.get("odylith_execution_agent_role", ""))
    confidence = _clamp_score(summary.get("odylith_execution_confidence_score", 0) or 0)
    if recommended_role in {"explorer", "worker"} and confidence >= 3:
        return recommended_role
    if profile in {RouterProfile.MINI_MEDIUM, RouterProfile.MINI_HIGH} and assessment.task_family == "analysis_review":
        return "explorer"
    if not assessment.needs_write and assessment.task_family == "analysis_review":
        return "explorer"
    return "worker"


def _host_tool_contract(*, profile: RouterProfile, assessment: TaskAssessment) -> dict[str, Any]:
    if profile is RouterProfile.MAIN_THREAD:
        return {}
    agent_role = _agent_role_for_assessment(assessment, profile=profile)
    host_runtime = _assessment_host_runtime(assessment)
    native_spawn_supported = _native_spawn_supported_for_assessment(assessment)
    contract = {
        "tool_name": "spawn_agent",
        "built_in_agent_types_only": True,
        "supported_agent_types": list(_HOST_SUPPORTED_AGENT_TYPES),
        "named_custom_agent_type_supported": False,
        "ui_controls_authoritative_for_requested_runtime": False,
        "requested_runtime_source_fields": [
            "model",
            "reasoning_effort",
            "spawn_agent_overrides",
            "runtime_banner_lines",
        ],
        "visibility_notice": (
            (
                f"{_HOST_UI_VISIBILITY_NOTE} Treat the routed runtime banner and structured spawn payload as "
                "the authoritative requested runtime for the delegated leaf."
            )
            if native_spawn_supported
            else "Treat the routed runtime banner as local execution guidance only in this host."
        ),
        "custom_agent_type_note": _HOST_CUSTOM_AGENT_TYPE_NOTE,
        "agent_role": agent_role,
        "requested_model": profile.model,
        "requested_reasoning_effort": profile.reasoning_effort,
        "host_runtime": host_runtime or "unknown",
        "native_spawn_supported": native_spawn_supported,
    }
    if not native_spawn_supported:
        contract["local_guidance_only"] = True
        contract["unsupported_reason"] = (
            "Native subagent spawn is validated only in Codex today; keep this routed runtime as local execution guidance in the current host."
        )
    return contract


def _runtime_banner_lines(*, profile: RouterProfile, assessment: TaskAssessment) -> list[str]:
    if profile is RouterProfile.MAIN_THREAD:
        return []
    banner_reason = _task_class_policy_for(assessment).rationale
    agent_role = _agent_role_for_assessment(assessment, profile=profile)
    host_runtime = _assessment_host_runtime(assessment) or "unknown"
    if not _native_spawn_supported_for_assessment(assessment):
        return [
            f"REQUESTED RUNTIME: {profile.model} / {profile.reasoning_effort}",
            f"WHY THIS TIER: {banner_reason}",
            f"MODEL: {profile.model}",
            f"REASONING: {profile.reasoning_effort}",
            f"AGENT ROLE: {agent_role}",
            (
                "HOST NOTE: Native subagent spawn is not supported in this host "
                f"(`{host_runtime}`); treat this routed runtime as local execution guidance only."
            ),
        ]
    return [
        f"REQUESTED RUNTIME: {profile.model} / {profile.reasoning_effort}",
        f"WHY THIS TIER: {banner_reason}",
        f"MODEL: {profile.model}",
        f"REASONING: {profile.reasoning_effort}",
        f"AGENT ROLE: {agent_role}",
        (
            "HOST NOTE: Codex desktop may still show parent-thread model/reasoning controls in this "
            "delegated thread UI for some combinations. Treat this banner and the structured spawn payload as the authoritative "
            "requested runtime for this leaf."
        ),
    ]


def _spawn_task_message(
    *,
    request: RouteRequest,
    profile: RouterProfile,
    assessment: TaskAssessment,
    termination_expectation: str,
) -> str:
    task_lines = ["TASK", _normalize_multiline_string(request.prompt)]
    acceptance_lines = ["ACCEPTANCE CRITERIA", *[f"- {item}" for item in request.acceptance_criteria]]
    allowed_path_lines = ["ALLOWED PATHS", *[f"- {path}" for path in request.allowed_paths]]
    validation_lines = ["VALIDATION COMMANDS", *[f"- {command}" for command in request.validation_commands]]
    termination_lines = ["TERMINATION EXPECTATION", termination_expectation]
    return _build_host_message(
        _runtime_banner_lines(profile=profile, assessment=assessment),
        task_lines,
        acceptance_lines,
        allowed_path_lines,
        validation_lines,
        termination_lines,
    )


def _native_spawn_payload(*, profile: RouterProfile, assessment: TaskAssessment, message: str) -> dict[str, Any]:
    if profile is RouterProfile.MAIN_THREAD or not _native_spawn_supported_for_assessment(assessment):
        return {}
    spawn_agent_overrides = _spawn_agent_overrides(profile=profile, assessment=assessment)
    return {
        "tool_name": "spawn_agent",
        "agent_type": spawn_agent_overrides["agent_type"],
        "model": spawn_agent_overrides["model"],
        "reasoning_effort": spawn_agent_overrides["reasoning_effort"],
        "message": message,
    }


def _task_class_policy_for(assessment: TaskAssessment) -> TaskClassPolicy:
    return _TASK_CLASS_POLICIES.get(assessment.task_family, _TASK_CLASS_POLICIES["bounded_bugfix"])


def _task_class_policy_lines(policy: TaskClassPolicy) -> list[str]:
    if policy.default_profile is RouterProfile.MAIN_THREAD:
        return [f"task-class policy `{policy.task_family}` stays local by default", policy.rationale]
    return [
        (
            f"task-class policy `{policy.task_family}` defaults to `{policy.default_profile.value}` "
            f"({policy.default_profile.model} / {policy.default_profile.reasoning_effort})"
        ),
        policy.rationale,
    ]


def _termination_expectation(assessment: TaskAssessment) -> str:
    handoff_kind = "patch" if assessment.needs_write else "findings report"
    return (
        f"Stop after handing off the bounded {handoff_kind} for the routed scope; "
        "the main thread integrates the result and then closes the delegated leaf."
    )


def _delegated_leaf_lifecycle_payload(
    *,
    profile: RouterProfile,
    assessment: TaskAssessment,
) -> DelegatedLeafLifecyclePayload:
    agent_role = _agent_role_for_assessment(assessment, profile=profile)
    termination_expectation = _termination_expectation(assessment)
    if _native_spawn_supported_for_assessment(assessment):
        spawn_overrides = {
            "agent_role": agent_role,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "apply_parent_defaults": False,
            "close_after_result": True,
            "default_post_result_action": "close_agent",
            "queued_followup_required_for_reuse": True,
            "allow_prequeue_same_scope_reuse_claim": True,
            "prequeue_same_scope_reuse_claim_minutes": _DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES,
            "idle_timeout_minutes": _DEFAULT_IDLE_TIMEOUT_MINUTES,
            "idle_timeout_action": _DEFAULT_IDLE_TIMEOUT_ACTION,
            "idle_timeout_escalation": _DEFAULT_IDLE_TIMEOUT_ESCALATION,
            "reuse_window": _DEFAULT_REUSE_WINDOW,
            "waiting_policy": _DEFAULT_WAITING_POLICY,
            "termination_expectation": termination_expectation,
        }
        spawn_agent_overrides = {
            "agent_type": agent_role,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        }
        close_agent_overrides = {
            "tool_name": "close_agent",
            "id_source": "delegated_leaf_id",
            "close_after_result": True,
            "close_on_idle_timeout": True,
            "close_on_main_thread_completion": True,
            "default_post_result_action": "close_agent",
            "queued_followup_required_for_reuse": True,
            "allow_prequeue_same_scope_reuse_claim": True,
            "prequeue_same_scope_reuse_claim_minutes": _DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES,
            "idle_timeout_minutes": _DEFAULT_IDLE_TIMEOUT_MINUTES,
            "idle_timeout_action": _DEFAULT_IDLE_TIMEOUT_ACTION,
            "idle_timeout_escalation": _DEFAULT_IDLE_TIMEOUT_ESCALATION,
            "reuse_window": _DEFAULT_REUSE_WINDOW,
            "waiting_policy": _DEFAULT_WAITING_POLICY,
            "termination_expectation": termination_expectation,
        }
    else:
        spawn_overrides = {}
        spawn_agent_overrides = {}
        close_agent_overrides = {}
    host_tool_contract = _host_tool_contract(profile=profile, assessment=assessment)
    runtime_banner_lines = _runtime_banner_lines(profile=profile, assessment=assessment)
    return DelegatedLeafLifecyclePayload(
        agent_role=agent_role,
        termination_expectation=termination_expectation,
        spawn_overrides=spawn_overrides,
        spawn_agent_overrides=spawn_agent_overrides,
        close_agent_overrides=close_agent_overrides,
        host_tool_contract=host_tool_contract,
        runtime_banner_lines=runtime_banner_lines,
    )


def _spawn_overrides(*, profile: RouterProfile, assessment: TaskAssessment) -> dict[str, Any]:
    return _delegated_leaf_lifecycle_payload(profile=profile, assessment=assessment).spawn_overrides


def _spawn_agent_overrides(*, profile: RouterProfile, assessment: TaskAssessment) -> dict[str, Any]:
    return _delegated_leaf_lifecycle_payload(profile=profile, assessment=assessment).spawn_agent_overrides


def _close_agent_overrides(*, profile: RouterProfile, assessment: TaskAssessment) -> dict[str, Any]:
    return _delegated_leaf_lifecycle_payload(profile=profile, assessment=assessment).close_agent_overrides


def _spawn_contract_lines(*, profile: RouterProfile, assessment: TaskAssessment) -> list[str]:
    lifecycle = _delegated_leaf_lifecycle_payload(profile=profile, assessment=assessment)
    if not lifecycle.spawn_overrides:
        host_runtime = _assessment_host_runtime(assessment) or "unknown"
        return [
            (
                "native `spawn_agent` is not supported in the current host "
                f"(`{host_runtime}`), so keep this routed runtime as local execution guidance only"
            ),
            (
                f"if this same bounded leaf runs in a Codex-compatible host, request "
                f"`model={profile.model}` and `reasoning_effort={profile.reasoning_effort}`"
            ),
            f"termination expectation: {lifecycle.termination_expectation}",
        ]
    spawn_overrides = lifecycle.spawn_overrides
    spawn_agent_overrides = lifecycle.spawn_agent_overrides
    close_agent_overrides = lifecycle.close_agent_overrides
    return [
        (
            f"spawn one `{spawn_overrides['agent_role']}` subagent and override parent defaults with "
            f"model=`{spawn_overrides['model']}` and reasoning_effort=`{spawn_overrides['reasoning_effort']}`"
        ),
        (
            "for native `spawn_agent` calls, pass "
            f"`agent_type={spawn_agent_overrides['agent_type']}` "
            f"`model={spawn_agent_overrides['model']}` "
            f"and `reasoning_effort={spawn_agent_overrides['reasoning_effort']}` directly"
        ),
        "do not inherit the parent thread model or reasoning weight for delegated leaves",
        "use the emitted `spawn_task_message` verbatim as `spawn_agent.message`; do not rebuild the runtime banner from separate fields",
        "apply the emitted `spawn_agent_overrides` payload directly for native host calls and use `spawn_overrides` for the richer lifecycle contract",
        (
            "keep the spawned delegated leaf id in the host ledger and apply the emitted "
            "`close_agent_overrides` payload once the main thread has fully completed the work"
        ),
        (
            "default post-result action is `close_agent`; sustained reuse still requires an explicit same-scope "
            "follow-up queued in the host ledger"
        ),
        (
            f"if the main thread has a real immediate same-scope reuse case but has not queued the next prompt yet, "
            f"it may record a bounded reuse claim for up to `{_DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES}` "
            "minutes before either queuing that follow-up or closing the leaf"
        ),
        (
            f"if the delegated leaf remains `waiting on instruction` for "
            f"`{_DEFAULT_IDLE_TIMEOUT_MINUTES}` minutes or longer, `{_DEFAULT_IDLE_TIMEOUT_ACTION}` "
            f"and `{_DEFAULT_IDLE_TIMEOUT_ESCALATION}`"
        ),
        (
            f"native closeout payload: `tool_name={close_agent_overrides['tool_name']}` "
            f"`id_source={close_agent_overrides['id_source']}` "
            "with `close_on_main_thread_completion=true`"
        ),
        "desktop UI controls are not authoritative for per-call subagent model/reasoning overrides; surface the routed runtime inside the delegated transcript",
        "the current native host accepts only built-in `agent_type` values, so named custom agents cannot be selected through `spawn_agent`",
        f"termination expectation: {spawn_overrides['termination_expectation']}",
    ]


def _apply_task_class_policy_floor(
    *,
    selected: RouterProfile,
    policy: TaskClassPolicy,
) -> tuple[RouterProfile, list[str]]:
    policy_lines = _task_class_policy_lines(policy)
    if policy.minimum_profile is RouterProfile.MAIN_THREAD:
        return selected, policy_lines
    if _PROFILE_PRIORITY.get(selected.value, 0) >= _PROFILE_PRIORITY.get(policy.minimum_profile.value, 0):
        return selected, policy_lines
    policy_lines.append(
        f"task-class floor promoted `{selected.value}` to `{policy.minimum_profile.value}` before delegation"
    )
    return policy.minimum_profile, policy_lines


def tuning_state_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / DEFAULT_TUNING_PATH).resolve()


def _load_json_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def load_tuning_state(*, repo_root: Path) -> TuningState:
    path = tuning_state_path(repo_root=repo_root)
    payload = _load_json_mapping(path)
    if str(payload.get("version", "")).strip() not in {"", _TUNING_VERSION}:
        return TuningState()
    state = TuningState()
    bias_payload = payload.get("profile_bias", {})
    if isinstance(bias_payload, Mapping):
        for profile in list(state.profile_bias):
            state.profile_bias[profile] = _clamp_bias(float(bias_payload.get(profile, 0.0) or 0.0))
    counts_payload = payload.get("outcome_counts", {})
    if isinstance(counts_payload, Mapping):
        for profile in list(state.outcome_counts):
            row = counts_payload.get(profile, {})
            if isinstance(row, Mapping):
                state.outcome_counts[profile] = {
                    _normalize_token(key): max(0, int(value or 0))
                    for key, value in row.items()
                    if _normalize_token(key)
                }
    family_bias_payload = payload.get("family_profile_bias", {})
    if isinstance(family_bias_payload, Mapping):
        for task_family, row in family_bias_payload.items():
            family_key = _normalize_token(task_family)
            if not family_key or not isinstance(row, Mapping):
                continue
            state.family_profile_bias.setdefault(family_key, _default_profile_bias_map())
            for profile in list(state.family_profile_bias[family_key]):
                state.family_profile_bias[family_key][profile] = _clamp_bias(float(row.get(profile, 0.0) or 0.0))
    family_counts_payload = payload.get("family_outcome_counts", {})
    if isinstance(family_counts_payload, Mapping):
        for task_family, family_row in family_counts_payload.items():
            family_key = _normalize_token(task_family)
            if not family_key or not isinstance(family_row, Mapping):
                continue
            state.family_outcome_counts.setdefault(family_key, _default_outcome_counts_map())
            for profile, row in family_row.items():
                profile_key = _normalize_token(profile)
                if profile_key not in state.family_outcome_counts[family_key] or not isinstance(row, Mapping):
                    continue
                state.family_outcome_counts[family_key][profile_key] = {
                    _normalize_token(key): max(0, int(value or 0))
                    for key, value in row.items()
                    if _normalize_token(key)
                }
    ledger_payload = payload.get("applied_outcome_keys", {})
    if isinstance(ledger_payload, Mapping):
        normalized_ledger: dict[str, str] = {}
        for raw_key, raw_value in ledger_payload.items():
            key = _normalize_string(raw_key)
            value = _normalize_string(raw_value)
            if key and value:
                normalized_ledger[key] = value
        while len(normalized_ledger) > _OUTCOME_LEDGER_LIMIT:
            stale_key = next(iter(normalized_ledger))
            normalized_ledger.pop(stale_key, None)
        state.applied_outcome_keys = normalized_ledger
    state.updated_at = _normalize_string(payload.get("updated_at", ""))
    return state


def save_tuning_state(*, repo_root: Path, state: TuningState) -> Path:
    path = tuning_state_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def route_request_from_mapping(payload: Mapping[str, Any]) -> RouteRequest:
    context_signals = _extract_context_signals_payload(payload)
    return RouteRequest(
        prompt=_normalize_string(payload.get("prompt", "")),
        acceptance_criteria=_normalize_list(payload.get("acceptance_criteria", [])),
        allowed_paths=_normalize_list(payload.get("allowed_paths", [])),
        workstreams=_normalize_list(payload.get("workstreams", [])),
        artifacts=_normalize_list(payload.get("artifacts", [])),
        validation_commands=_normalize_list(payload.get("validation_commands", [])),
        components=_normalize_list(payload.get("components", [])),
        phase=_normalize_token(payload.get("phase", "")),
        task_kind=_normalize_token(payload.get("task_kind", "")),
        needs_write=_normalize_bool(payload.get("needs_write", False)),
        latency_sensitive=_normalize_bool(payload.get("latency_sensitive", False)),
        correctness_critical=_normalize_bool(payload.get("correctness_critical", False)),
        requires_multi_agent_adjudication=_normalize_bool(payload.get("requires_multi_agent_adjudication", False)),
        evolving_context_required=_normalize_bool(payload.get("evolving_context_required", False)),
        evidence_cone_grounded=_normalize_bool(payload.get("evidence_cone_grounded", False)),
        accuracy_preference=_normalize_token(payload.get("accuracy_preference", "accuracy")) or "accuracy",
        context_signals=_normalize_context_signals(context_signals),
    )


def route_outcome_from_mapping(payload: Mapping[str, Any]) -> RouteOutcome:
    return RouteOutcome(
        accepted=_normalize_bool(payload.get("accepted", False)),
        blocked=_normalize_bool(payload.get("blocked", False)),
        ambiguous=_normalize_bool(payload.get("ambiguous", False)),
        artifact_missing=_normalize_bool(payload.get("artifact_missing", False)),
        quality_too_weak=_normalize_bool(payload.get("quality_too_weak", False)),
        escalated=_normalize_bool(payload.get("escalated", False)),
        broader_coordination=_normalize_bool(payload.get("broader_coordination", False)),
        outcome_id=_normalize_string(payload.get("outcome_id", "")),
        notes=_normalize_string(payload.get("notes", "")),
    )


def _context_signal_summary(request: RouteRequest) -> dict[str, Any]:
    return subagent_router_assessment_runtime._context_signal_summary(request)


def _contains_any(text: str, phrases: Sequence[str]) -> bool:
    return any(_phrase_matches(text, token) for token in phrases)


def _matched_phrases(text: str, phrases: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(token for token in phrases if _phrase_matches(text, token)))


def _keyword_score(text: str, phrases: Sequence[str]) -> int:
    hits = sum(1 for token in phrases if _phrase_matches(text, token))
    return _clamp_score(hits)


def _strip_relative_prefix(token: str) -> str:
    normalized = token.strip().rstrip(".,:;")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def infer_explicit_paths(text: str) -> list[str]:
    """Extract explicit repo paths from prompt text without corrupting case."""

    seen: set[str] = set()
    paths: list[str] = []
    for match in _EXPLICIT_PATH_TOKEN_RE.finditer(str(text or "")):
        token = _strip_relative_prefix(match.group("token"))
        if not token:
            continue
        if token in _EXPLICIT_ROOT_FILES or any(token.startswith(prefix) for prefix in _EXPLICIT_PATH_PREFIXES):
            if token not in seen:
                seen.add(token)
                paths.append(token)
    return paths


def _path_prefix(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    return parts[0] if parts else ""


def surface_prefixes_for_path(path: str) -> frozenset[str]:
    parts = [part for part in str(path).split("/") if part]
    if not parts:
        return frozenset()

    prefixes: set[str] = {parts[0]}
    suffix = Path(str(path)).suffix.lower()
    markdown_like = suffix in {".md", ".mdx", ".rst", ".txt"}

    def _apply_odylith_surface(second_segment: str) -> None:
        if second_segment in {"skills", "agents-guidelines"}:
            prefixes.add(second_segment)
        if markdown_like or second_segment in _ODYLITH_DOC_SURFACE_SEGMENTS:
            prefixes.add("docs")
        if second_segment == "runtime" and len(parts) >= 3 and parts[2] == "contracts":
            prefixes.add("contracts")

    if parts[0] == "odylith" and len(parts) >= 2:
        _apply_odylith_surface(parts[1])
    if parts[:5] == ["src", "odylith", "bundle", "assets", "odylith"] and len(parts) >= 6:
        _apply_odylith_surface(parts[5])

    return frozenset(prefixes)


def _phrase_matches(text: str, phrase: str) -> bool:
    token = _normalize_string(phrase).lower()
    if not token:
        return False
    normalized_text = text.lower()
    phrase_parts = [re.escape(part) for part in re.split(r"[\s_-]+", token) if part]
    if not phrase_parts:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\s_-]+".join(phrase_parts) + r"(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def _infer_phase_tokens(text: str, *, task_kind: str, phase: str) -> set[str]:
    phases: set[str] = set()
    if phase:
        phases.add(phase)
    if task_kind:
        if task_kind in {"feature_implementation", "implementation", "bugfix"}:
            phases.add("implementation")
        elif task_kind in {"analysis", "review"}:
            phases.add(task_kind)
        elif task_kind == "planning":
            phases.add("planning")
    if _contains_any(text, _WRITE_KEYWORDS):
        phases.add("implementation")
    if _contains_any(text, ("review", "audit")):
        phases.add("review")
    if _contains_any(text, ("analyze", "analysis", "investigate", "why")):
        phases.add("analysis")
    if _contains_any(text, ("plan", "design", "rollout")):
        phases.add("planning")
    return phases


def infer_implied_write_surfaces(prompt: str, acceptance_criteria: Sequence[str] | None = None) -> list[ImpliedWriteSurfaceRule]:
    """Return declared write surfaces implied by prompt language."""

    criteria = " ".join(_normalize_list(acceptance_criteria or []))
    text = " ".join(part for part in (_normalize_string(prompt), criteria) if part).lower()
    implied: list[ImpliedWriteSurfaceRule] = []
    for rule in _IMPLIED_WRITE_SURFACE_RULES:
        if not _contains_any(text, rule.phrases):
            continue
        if rule.surface_key == "tests" and _contains_any(text, _VALIDATION_ONLY_TEST_PHRASES):
            explicit_test_write = _contains_any(text, rule.phrases)
            if not explicit_test_write:
                continue
        implied.append(rule)
    return implied


def infer_prompt_semantics(prompt: str, acceptance_criteria: Sequence[str] | None = None) -> dict[str, list[str]]:
    """Extract reusable prompt-level semantic markers for planner and router layers."""

    criteria = " ".join(_normalize_list(acceptance_criteria or []))
    prompt_text = _normalize_string(prompt)
    text = " ".join(part for part in (prompt_text, criteria) if part).lower()
    signals: dict[str, list[str]] = {}
    synthesis_hits: list[str] = []
    diagnostic_hits: list[str] = []
    for name, phrases in (
        ("trivial_explanation", _TRIVIAL_EXPLANATION_KEYWORDS),
        ("diagnostic", _DIAGNOSTIC_KEYWORDS),
        ("bounded_scope", _BOUNDED_SCOPE_KEYWORDS),
        ("open_ended_scope", _OPEN_ENDED_SCOPE_KEYWORDS),
        ("requested_depth", _DEPTH_KEYWORDS),
    ):
        hits = _matched_phrases(text, phrases)
        if hits:
            signals[name] = hits
            if name == "diagnostic":
                diagnostic_hits = hits
    synthesis_hits = _matched_phrases(text, _READ_ONLY_SYNTHESIS_KEYWORDS)
    if synthesis_hits or len(diagnostic_hits) >= 2:
        signals["synthesis_required"] = list(dict.fromkeys([*synthesis_hits, *diagnostic_hits]))
    implied_surface_hits = [rule.surface_key for rule in infer_implied_write_surfaces(prompt_text, acceptance_criteria)]
    if implied_surface_hits:
        signals["implied_write_surfaces"] = implied_surface_hits
    return signals


def _task_family_key(value: Any) -> str:
    return _normalize_token(value) or "analysis_review"


def _new_decision_id() -> str:
    return f"route-{uuid.uuid4().hex}"


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _route_request_validation_errors(request: RouteRequest) -> list[str]:
    errors: list[str] = []
    if not _normalize_string(request.prompt):
        errors.append("prompt is required")
    return errors


def _ensure_valid_route_request(request: RouteRequest, *, code: str = "invalid_route_request") -> None:
    errors = _route_request_validation_errors(request)
    if errors:
        raise RouterInputError(
            code=code,
            message="route request is missing the minimum required context",
            details=errors,
        )


def _task_assessment_from_mapping(payload: Mapping[str, Any] | None) -> TaskAssessment | None:
    if not payload:
        return None
    try:
        normalized = dict(payload)
        normalized.setdefault("evidence_cone_grounded", False)
        normalized.setdefault("earned_depth", 0)
        normalized.setdefault("delegation_readiness", 0)
        return TaskAssessment(**normalized)
    except TypeError:
        return None


def _assessment_for_followup(
    *,
    decision: RoutingDecision,
    request: RouteRequest | None,
    assessment: TaskAssessment | None,
    code: str,
) -> TaskAssessment:
    if assessment is not None:
        return assessment
    embedded = _task_assessment_from_mapping(decision.assessment if isinstance(decision.assessment, Mapping) else None)
    if embedded is not None:
        return embedded
    if request is not None:
        request_errors = _route_request_validation_errors(request)
        if not request_errors:
            return assess_request(request)
    details: list[str] = []
    if not decision.assessment:
        details.append("decision payload did not include an assessment block")
    else:
        details.append("decision payload included an incomplete or incompatible assessment block")
    if request is None:
        details.append("no request payload was supplied for assessment reconstruction")
    else:
        details.extend(_route_request_validation_errors(request) or ["request payload could not be used to rebuild assessment"])
    raise RouterInputError(
        code=code,
        message="follow-up routing requires embedded assessment data or a valid request payload",
        details=details,
    )


def _validated_profile(decision: RoutingDecision) -> RouterProfile:
    try:
        return RouterProfile(decision.profile)
    except ValueError as exc:
        raise RouterInputError(
            code="invalid_decision_profile",
            message="decision payload used an unsupported router profile",
            details=[f"profile={decision.profile or '<empty>'}"],
        ) from exc


def _decision_identity(decision: RoutingDecision, *, task_family: str) -> str:
    decision_id = _normalize_string(decision.decision_id)
    if decision_id:
        return decision_id
    assessment_payload = dict(decision.assessment) if isinstance(decision.assessment, Mapping) else {}
    fallback_payload = {
        "profile": decision.profile,
        "task_family": task_family or decision.task_family,
        "task_kind": _normalize_token(assessment_payload.get("task_kind", "")),
        "phase": _normalize_token(assessment_payload.get("phase", "")),
        "prompt": _normalize_string(assessment_payload.get("prompt", "")),
        "needs_write": _normalize_bool(assessment_payload.get("needs_write", False)),
    }
    return f"legacy-{_canonical_hash(fallback_payload)}"


def _outcome_identity(decision: RoutingDecision, outcome: RouteOutcome, *, task_family: str) -> str:
    explicit = _normalize_string(outcome.outcome_id)
    decision_identity = _decision_identity(decision, task_family=task_family)
    labels = sorted(_outcome_labels(outcome))
    if explicit:
        return f"{decision_identity}::{explicit}"
    return f"{decision_identity}::{_canonical_hash({'labels': labels, 'task_family': task_family})}"


def _remember_outcome_key(state: TuningState, *, outcome_key: str, seen_at: str) -> bool:
    if outcome_key in state.applied_outcome_keys:
        return False
    ledger = dict(state.applied_outcome_keys)
    ledger[outcome_key] = seen_at
    while len(ledger) > _OUTCOME_LEDGER_LIMIT:
        stale_key = next(iter(ledger))
        ledger.pop(stale_key, None)
    state.applied_outcome_keys = ledger
    return True


def _classify_task_family(
    *,
    task_kind: str,
    needs_write: bool,
    correctness_critical: bool,
    feature_implementation: bool,
    mixed_phase: bool,
    ambiguity: int,
    blast_radius: int,
    reversibility_risk: int,
    mechanicalness: int,
    coordination_cost: int,
) -> str:
    if coordination_cost >= 4 or (mixed_phase and needs_write and coordination_cost >= 4):
        return "coordination_heavy"
    if correctness_critical or max(blast_radius, reversibility_risk) >= 3:
        return "critical_change" if needs_write else "analysis_review"
    if not needs_write:
        return "analysis_review"
    if feature_implementation:
        return "bounded_feature"
    if task_kind == "bugfix":
        return "bounded_bugfix"
    if mechanicalness >= 3 and ambiguity <= 1 and blast_radius <= 1:
        return "mechanical_patch"
    return "bounded_bugfix"


def assess_request(request: RouteRequest) -> TaskAssessment:
    return subagent_router_assessment_runtime.assess_request(request)


def _allow_xhigh_by_gate(assessment: TaskAssessment) -> bool:
    if assessment.correctness_critical and assessment.feature_implementation and max(
        assessment.ambiguity,
        assessment.blast_radius,
        assessment.reversibility_risk,
    ) >= 3:
        return True
    if (
        assessment.task_family in {"bounded_feature", "critical_change"}
        and assessment.accuracy_preference in {"max_accuracy", "maximum_accuracy"}
        and assessment.requested_depth >= 3
        and max(
            assessment.ambiguity,
            assessment.blast_radius,
            assessment.context_breadth,
            assessment.reversibility_risk,
        ) >= 3
    ):
        return True
    if (
        assessment.feature_implementation
        and assessment.accuracy_preference in {"max_accuracy", "maximum_accuracy"}
        and assessment.requested_depth >= 3
        and assessment.base_confidence <= 1
    ):
        return True
    if assessment.reversibility_risk >= 4 and assessment.requested_depth >= 3:
        return True
    if assessment.blast_radius >= 4 and assessment.context_breadth >= 3 and assessment.requested_depth >= 3:
        return True
    return False


def _reliability_bias(counts: Mapping[str, int]) -> float:
    successes = int(counts.get("accepted", 0) or 0)
    failures = sum(
        int(counts.get(label, 0) or 0)
        for label in ("blocked", "ambiguous", "artifact_missing", "quality_too_weak", "broader_coordination")
    )
    total = successes + failures
    if total < 3:
        return 0.0
    return max(-0.25, min(0.25, ((successes - failures) / total) * 0.25))


def _count_total_labels(counts: Mapping[str, int], labels: Sequence[str]) -> int:
    return sum(int(counts.get(label, 0) or 0) for label in labels)


def _combined_counts(*rows: Mapping[str, int]) -> dict[str, int]:
    combined: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        for key, value in row.items():
            token = _normalize_token(key)
            if not token:
                continue
            combined[token] = int(combined.get(token, 0) or 0) + max(0, int(value or 0))
    return combined


def _profile_reliability_summary(profile: RouterProfile, assessment: TaskAssessment, tuning: TuningState) -> dict[str, Any]:
    global_counts = dict(tuning.outcome_counts.get(profile.value, {}))
    family_counts = dict(tuning.family_outcome_counts.get(assessment.task_family, {}).get(profile.value, {}))
    family_total = _count_total_labels(
        family_counts,
        (
            "accepted",
            "blocked",
            "ambiguous",
            "artifact_missing",
            "quality_too_weak",
            "broader_coordination",
            "escalated",
            "token_efficient",
        ),
    )
    counts = family_counts if family_total >= 2 else _combined_counts(global_counts, family_counts)
    accepted = int(counts.get("accepted", 0) or 0)
    blocked = int(counts.get("blocked", 0) or 0)
    ambiguous = int(counts.get("ambiguous", 0) or 0)
    artifact_missing = int(counts.get("artifact_missing", 0) or 0)
    quality_too_weak = int(counts.get("quality_too_weak", 0) or 0)
    broader_coordination = int(counts.get("broader_coordination", 0) or 0)
    token_efficient = int(counts.get("token_efficient", 0) or 0)
    failures = blocked + ambiguous + artifact_missing + quality_too_weak + broader_coordination
    severe_failures = blocked + ambiguous + quality_too_weak
    total = accepted + failures
    if total < 2:
        posture = "unknown"
    elif failures == 0 and accepted >= 3:
        posture = "strong"
    elif severe_failures >= 2 or failures > accepted:
        posture = "weak"
    else:
        posture = "mixed"
    return {
        "source": "family" if family_total >= 2 else "combined",
        "posture": posture,
        "accepted": accepted,
        "failures": failures,
        "severe_failures": severe_failures,
        "token_efficient": token_efficient,
        "total": total,
    }


def _tuning_bias_for_profile(profile: RouterProfile, assessment: TaskAssessment, tuning: TuningState) -> float:
    profile_bias = float(tuning.profile_bias.get(profile.value, 0.0) or 0.0)
    family_bias = float(
        tuning.family_profile_bias.get(assessment.task_family, {}).get(profile.value, 0.0) or 0.0
    )
    return (
        profile_bias
        + family_bias
        + _reliability_bias(tuning.outcome_counts.get(profile.value, {}))
        + _reliability_bias(tuning.family_outcome_counts.get(assessment.task_family, {}).get(profile.value, {}))
    )


def _score_profile(profile: RouterProfile, assessment: TaskAssessment, tuning: TuningState) -> float:
    return subagent_router_runtime_policy._score_profile(profile=profile, assessment=assessment, tuning=tuning)



def _score_margin(selected: RouterProfile, scorecard: Mapping[str, float]) -> float:
    return subagent_router_runtime_policy._score_margin(selected=selected, scorecard=scorecard)



def _routing_confidence(selected: RouterProfile, assessment: TaskAssessment, scorecard: Mapping[str, float]) -> int:
    return subagent_router_runtime_policy._routing_confidence(selected=selected, assessment=assessment, scorecard=scorecard)



def _apply_accuracy_backstop(
    *,
    selected: RouterProfile,
    assessment: TaskAssessment,
    scorecard: Mapping[str, float],
) -> tuple[RouterProfile, int, list[str]]:
    return subagent_router_runtime_policy._apply_accuracy_backstop(selected=selected, assessment=assessment, scorecard=scorecard)



def _next_stronger_profile(profile: RouterProfile, assessment: TaskAssessment) -> RouterProfile:
    return subagent_router_runtime_policy._next_stronger_profile(profile=profile, assessment=assessment)



def _apply_reliability_backstop(
    *,
    selected: RouterProfile,
    assessment: TaskAssessment,
    tuning: TuningState,
    routing_confidence: int,
) -> tuple[RouterProfile, int, list[str]]:
    return subagent_router_runtime_policy._apply_reliability_backstop(selected=selected, assessment=assessment, tuning=tuning, routing_confidence=routing_confidence)



def _apply_odylith_execution_alignment(
    *,
    selected: RouterProfile,
    assessment: TaskAssessment,
    scorecard: Mapping[str, float],
    routing_confidence: int,
    allow_xhigh: bool,
) -> tuple[RouterProfile, int, list[str]]:
    return subagent_router_runtime_policy._apply_odylith_execution_alignment(selected=selected, assessment=assessment, scorecard=scorecard, routing_confidence=routing_confidence, allow_xhigh=allow_xhigh)



def _top_score_lines(
    *,
    selected: RouterProfile,
    scorecard: Mapping[str, float],
    assessment: TaskAssessment,
    task_class_policy_lines: Sequence[str],
    allow_xhigh: bool,
    routing_confidence: int,
    score_margin: float,
    backstop_lines: Sequence[str],
) -> list[str]:
    return subagent_router_runtime_policy._top_score_lines(selected=selected, scorecard=scorecard, assessment=assessment, task_class_policy_lines=task_class_policy_lines, allow_xhigh=allow_xhigh, routing_confidence=routing_confidence, score_margin=score_margin, backstop_lines=backstop_lines)



def _select_profile(
    *,
    assessment: TaskAssessment,
    tuning: TuningState,
    allow_xhigh: bool,
) -> tuple[RouterProfile, dict[str, float]]:
    if not assessment.needs_write and assessment.task_family == "analysis_review":
        candidates = [
            RouterProfile.MINI_MEDIUM,
            RouterProfile.MINI_HIGH,
            RouterProfile.GPT54_HIGH,
        ]
    else:
        candidates = [
            RouterProfile.MINI_MEDIUM,
            RouterProfile.MINI_HIGH,
            RouterProfile.SPARK_MEDIUM,
            RouterProfile.CODEX_MEDIUM,
            RouterProfile.CODEX_HIGH,
            RouterProfile.GPT54_HIGH,
        ]
    if allow_xhigh:
        candidates.append(RouterProfile.GPT54_XHIGH)
    scorecard = {profile.value: round(_score_profile(profile, assessment, tuning), 3) for profile in candidates}
    selected = max(
        candidates,
        key=lambda profile: (scorecard[profile.value], _PROFILE_PRIORITY.get(profile.value, 0)),
    )
    return selected, scorecard


def _next_profile_for_escalation(
    decision: RoutingDecision,
    assessment: TaskAssessment,
    outcome: RouteOutcome,
) -> RouterProfile | None:
    profile = _validated_profile(decision)
    if profile is RouterProfile.MAIN_THREAD or profile is RouterProfile.GPT54_XHIGH:
        return None
    if not (outcome.blocked or outcome.ambiguous or outcome.artifact_missing or outcome.quality_too_weak or outcome.broader_coordination):
        return None
    if profile is RouterProfile.MINI_MEDIUM:
        if assessment.needs_write:
            return RouterProfile.CODEX_MEDIUM
        return RouterProfile.MINI_HIGH
    if profile is RouterProfile.MINI_HIGH:
        return RouterProfile.GPT54_HIGH
    if profile is RouterProfile.SPARK_MEDIUM:
        return RouterProfile.CODEX_MEDIUM
    if profile is RouterProfile.CODEX_MEDIUM:
        if assessment.task_family == "critical_change" or assessment.correctness_critical:
            return RouterProfile.GPT54_HIGH
        return RouterProfile.CODEX_HIGH
    if profile is RouterProfile.CODEX_HIGH:
        return RouterProfile.GPT54_HIGH
    if profile is RouterProfile.GPT54_HIGH and (
        outcome.quality_too_weak
        or (outcome.blocked and _allow_xhigh_by_gate(assessment))
        or (outcome.ambiguous and _allow_xhigh_by_gate(assessment))
        or _allow_xhigh_by_gate(assessment)
    ):
        return RouterProfile.GPT54_XHIGH
    return None


def _escalation_refusal_reason(decision: RoutingDecision, assessment: TaskAssessment, outcome: RouteOutcome) -> str:
    profile = _validated_profile(decision)
    if not (outcome.blocked or outcome.ambiguous or outcome.artifact_missing or outcome.quality_too_weak or outcome.broader_coordination):
        return "no escalation trigger was present"
    if profile is RouterProfile.MAIN_THREAD:
        return "the slice is already kept in the main thread"
    if profile is RouterProfile.GPT54_XHIGH:
        return "the strongest available profile has already been used"
    if outcome.broader_coordination:
        return "the first pass exposed broader coordination or merge work that should be split locally before any retry"
    if outcome.ambiguous and assessment.needs_write and assessment.write_scope_clarity <= 2:
        return "write ownership is still too unclear to justify another delegated retry"
    if outcome.blocked and assessment.needs_write and assessment.acceptance_clarity <= 1:
        return "the acceptance contract is too weak; tighten the bounded slice locally before retrying"
    if outcome.blocked and assessment.evolving_context_required and not assessment.evidence_cone_grounded:
        return "the task depends on evolving local context and should stay in the main thread"
    return ""


def _prompt_wrapper_delta(*, outcome: RouteOutcome, assessment: TaskAssessment) -> list[str]:
    lines: list[str] = []
    if outcome.blocked:
        lines.append("Call out the exact blocker and the expected unblock artifact in the respawn prompt.")
    if outcome.blocked and assessment.acceptance_clarity <= 1:
        lines.append("Strengthen the acceptance criteria with owned paths, deliverables, and success conditions before retrying.")
    if outcome.ambiguous:
        lines.append("Pin the missing decision points, owned paths, or interfaces before delegating again.")
    if outcome.ambiguous and assessment.write_scope_clarity <= 2:
        lines.append("Clarify the exact owned write paths locally; do not respawn until ownership is bounded.")
    if outcome.artifact_missing:
        lines.append("List required deliverables and validation artifacts explicitly in acceptance criteria.")
    if outcome.artifact_missing and assessment.validation_clarity == 0 and assessment.needs_write:
        lines.append("Add explicit validation commands or test expectations so the next pass knows how success is proven.")
    if outcome.quality_too_weak:
        lines.append("Ask for a deeper edge-case sweep, tradeoff analysis, and correctness review.")
    if outcome.broader_coordination:
        lines.append("Split broad coordination or integration work away from the bounded implementation slice before respawn.")
    if assessment.feature_implementation and assessment.accuracy_preference in {"max_accuracy", "maximum_accuracy"}:
        lines.append("Restate the accuracy-first bias so the next pass optimizes for correctness over speed.")
    return lines

subagent_router_runtime_policy.bind(sys.modules[__name__])


def route_request(
    request: RouteRequest,
    *,
    repo_root: Path | None = None,
) -> RoutingDecision:
    _ensure_valid_route_request(request)
    request = subagent_router_assessment_runtime.request_with_consumer_write_policy(
        request,
        repo_root=Path(repo_root).resolve() if repo_root is not None else None,
    )
    decision_id = _new_decision_id()
    assessment = assess_request(request)
    task_class_policy = _task_class_policy_for(assessment)
    task_class_policy_lines = _task_class_policy_lines(task_class_policy)
    if assessment.hard_gate_hits:
        why = f"kept local because {', '.join(assessment.hard_gate_hits)}"
        return RoutingDecision(
            delegate=False,
            profile=RouterProfile.MAIN_THREAD.value,
            model="",
            reasoning_effort="",
            agent_role="",
            close_after_result=False,
            idle_timeout_minutes=0,
            reuse_window="",
            waiting_policy="",
            decision_id=decision_id,
            task_family=assessment.task_family,
            refusal_stage="assessment_hard_gate",
            routing_confidence=assessment.base_confidence,
            manual_review_recommended=True,
            rescope_required=True,
            why=why,
            escalation_profile="",
            hard_gate_hits=list(assessment.hard_gate_hits),
            score_margin=0.0,
            failure_signals=[],
            prompt_wrapper_delta=[],
            spawn_contract_lines=[],
            spawn_overrides={},
            spawn_agent_overrides={},
            close_agent_overrides={},
            host_tool_contract={},
            runtime_banner_lines=[],
            spawn_task_message="",
            native_spawn_payload={},
            task_class_profile=task_class_policy.default_profile.value,
            task_class_model=task_class_policy.default_profile.model,
            task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
            task_class_policy_lines=task_class_policy_lines,
            explanation_lines=[
                f"task_family={assessment.task_family}",
                *task_class_policy_lines,
                "hard safety gates beat weighted scoring for this slice",
                why,
            ],
            scorecard={},
            assessment=assessment.as_dict(),
            odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessment),
        )

    odylith_guard_reason = _odylith_execution_guard_reason(assessment)
    if odylith_guard_reason:
        why = f"kept local because {odylith_guard_reason}"
        return RoutingDecision(
            delegate=False,
            profile=RouterProfile.MAIN_THREAD.value,
            model="",
            reasoning_effort="",
            agent_role="",
            close_after_result=False,
            idle_timeout_minutes=0,
            reuse_window="",
            waiting_policy="",
            decision_id=decision_id,
            task_family=assessment.task_family,
            refusal_stage="odylith_execution_guard",
            routing_confidence=max(
                assessment.base_confidence,
                _clamp_score(assessment.context_signal_summary.get("odylith_execution_confidence_score", 0) or 0),
            ),
            manual_review_recommended=True,
            rescope_required=True,
            why=why,
            escalation_profile="",
            hard_gate_hits=[],
            score_margin=0.0,
            failure_signals=[],
            prompt_wrapper_delta=[],
            spawn_contract_lines=[],
            spawn_overrides={},
            spawn_agent_overrides={},
            close_agent_overrides={},
            host_tool_contract={},
            runtime_banner_lines=[],
            spawn_task_message="",
            native_spawn_payload={},
            task_class_profile=task_class_policy.default_profile.value,
            task_class_model=task_class_policy.default_profile.model,
            task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
            task_class_policy_lines=task_class_policy_lines,
            explanation_lines=[
                f"task_family={assessment.task_family}",
                *task_class_policy_lines,
                "the runtime guard beat weighted scoring for this slice",
                why,
            ],
            scorecard={},
            assessment=assessment.as_dict(),
            odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessment),
        )

    tuning = load_tuning_state(repo_root=Path(repo_root).resolve()) if repo_root is not None else TuningState()
    allow_xhigh = _allow_xhigh_by_gate(assessment)
    selected, scorecard = _select_profile(assessment=assessment, tuning=tuning, allow_xhigh=allow_xhigh)
    scorecard, odylith_prior_lines = _apply_odylith_execution_priors(
        scorecard=scorecard,
        assessment=assessment,
        allow_xhigh=allow_xhigh,
    )
    selected = max(
        [RouterProfile(profile) for profile in scorecard],
        key=lambda profile: (scorecard[profile.value], _PROFILE_PRIORITY.get(profile.value, 0)),
    )
    selected, routing_confidence, backstop_lines = _apply_accuracy_backstop(
        selected=selected,
        assessment=assessment,
        scorecard=scorecard,
    )
    selected, routing_confidence, reliability_lines = _apply_reliability_backstop(
        selected=selected,
        assessment=assessment,
        tuning=tuning,
        routing_confidence=routing_confidence,
    )
    selected, routing_confidence, odylith_lines = _apply_odylith_execution_alignment(
        selected=selected,
        assessment=assessment,
        scorecard=scorecard,
        routing_confidence=routing_confidence,
        allow_xhigh=allow_xhigh,
    )
    selected, task_class_policy_lines = _apply_task_class_policy_floor(selected=selected, policy=task_class_policy)
    score_margin = _score_margin(selected, scorecard)
    selected_score = float(scorecard.get(selected.value, 0.0) or 0.0)
    lifecycle = _delegated_leaf_lifecycle_payload(profile=selected, assessment=assessment)
    agent_role = lifecycle.agent_role
    spawn_overrides = lifecycle.spawn_overrides
    spawn_agent_overrides = lifecycle.spawn_agent_overrides
    close_agent_overrides = lifecycle.close_agent_overrides
    host_tool_contract = lifecycle.host_tool_contract
    runtime_banner_lines = lifecycle.runtime_banner_lines
    termination_expectation = str(lifecycle.termination_expectation)
    spawn_task_message = _spawn_task_message(
        request=request,
        profile=selected,
        assessment=assessment,
        termination_expectation=termination_expectation,
    )
    native_spawn_payload = _native_spawn_payload(
        profile=selected,
        assessment=assessment,
        message=spawn_task_message,
    )
    why = (
        f"delegated to `{selected.value}` ({selected.model} / {selected.reasoning_effort}) "
        f"with raw score {selected_score}"
    )
    next_profile = _next_profile_for_escalation(
        RoutingDecision(
            delegate=True,
            profile=selected.value,
            model=selected.model,
            reasoning_effort=selected.reasoning_effort,
            agent_role=agent_role,
            close_after_result=True,
            idle_timeout_minutes=_DEFAULT_IDLE_TIMEOUT_MINUTES,
            reuse_window=_DEFAULT_REUSE_WINDOW,
            waiting_policy=_DEFAULT_WAITING_POLICY,
            decision_id=decision_id,
            task_family=assessment.task_family,
            refusal_stage="delegated",
            routing_confidence=routing_confidence,
            manual_review_recommended=routing_confidence <= 1 or selected is RouterProfile.GPT54_XHIGH,
            rescope_required=False,
            why=why,
            escalation_profile="",
            hard_gate_hits=[],
            prequeue_same_scope_reuse_claim_minutes=_DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES,
            score_margin=score_margin,
            failure_signals=[],
            prompt_wrapper_delta=[],
            spawn_overrides=spawn_overrides,
            spawn_agent_overrides=spawn_agent_overrides,
            close_agent_overrides=close_agent_overrides,
            host_tool_contract=host_tool_contract,
            runtime_banner_lines=runtime_banner_lines,
            spawn_task_message=spawn_task_message,
            native_spawn_payload=native_spawn_payload,
            spawn_contract_lines=_spawn_contract_lines(profile=selected, assessment=assessment),
            idle_timeout_action=_DEFAULT_IDLE_TIMEOUT_ACTION,
            idle_timeout_escalation=_DEFAULT_IDLE_TIMEOUT_ESCALATION,
            termination_expectation=termination_expectation,
            task_class_profile=task_class_policy.default_profile.value,
            task_class_model=task_class_policy.default_profile.model,
            task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
            task_class_policy_lines=list(task_class_policy_lines),
            odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessment, selected=selected),
        ),
        assessment,
        RouteOutcome(blocked=True),
    )
    return RoutingDecision(
        delegate=True,
        profile=selected.value,
        model=selected.model,
        reasoning_effort=selected.reasoning_effort,
        agent_role=agent_role,
        close_after_result=True,
        idle_timeout_minutes=_DEFAULT_IDLE_TIMEOUT_MINUTES,
        reuse_window=_DEFAULT_REUSE_WINDOW,
        waiting_policy=_DEFAULT_WAITING_POLICY,
        decision_id=decision_id,
        task_family=assessment.task_family,
        refusal_stage="delegated",
        routing_confidence=routing_confidence,
        manual_review_recommended=routing_confidence <= 1 or selected is RouterProfile.GPT54_XHIGH,
        rescope_required=False,
        why=why,
        escalation_profile=next_profile.value if next_profile is not None else "",
        hard_gate_hits=[],
        prequeue_same_scope_reuse_claim_minutes=_DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES,
        score_margin=score_margin,
        failure_signals=[],
        prompt_wrapper_delta=[],
        spawn_overrides=spawn_overrides,
        spawn_agent_overrides=spawn_agent_overrides,
        close_agent_overrides=close_agent_overrides,
        host_tool_contract=host_tool_contract,
        runtime_banner_lines=runtime_banner_lines,
        spawn_task_message=spawn_task_message,
        native_spawn_payload=native_spawn_payload,
        spawn_contract_lines=_spawn_contract_lines(profile=selected, assessment=assessment),
        idle_timeout_action=_DEFAULT_IDLE_TIMEOUT_ACTION,
        idle_timeout_escalation=_DEFAULT_IDLE_TIMEOUT_ESCALATION,
        termination_expectation=termination_expectation,
        task_class_profile=task_class_policy.default_profile.value,
        task_class_model=task_class_policy.default_profile.model,
        task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
        task_class_policy_lines=list(task_class_policy_lines),
            explanation_lines=_top_score_lines(
                selected=selected,
                scorecard=scorecard,
                assessment=assessment,
                task_class_policy_lines=task_class_policy_lines,
                allow_xhigh=allow_xhigh,
                routing_confidence=routing_confidence,
                score_margin=score_margin,
                backstop_lines=[*odylith_prior_lines, *backstop_lines, *reliability_lines, *odylith_lines],
            ),
            scorecard=scorecard,
            assessment=assessment.as_dict(),
            odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessment, selected=selected),
        )


def escalate_routing_decision(
    *,
    decision: RoutingDecision,
    outcome: RouteOutcome,
    request: RouteRequest | None = None,
    assessment: TaskAssessment | None = None,
) -> RoutingDecision | None:
    assessed = _assessment_for_followup(
        decision=decision,
        request=request,
        assessment=assessment,
        code="invalid_escalation_context",
    )
    task_class_policy = _task_class_policy_for(assessed)
    task_class_policy_lines = _task_class_policy_lines(task_class_policy)
    refusal_reason = _escalation_refusal_reason(decision, assessed, outcome)
    if refusal_reason:
        why = f"kept local after `{decision.profile}` because {refusal_reason}"
        prompt_delta = _prompt_wrapper_delta(outcome=outcome, assessment=assessed)
        return RoutingDecision(
            delegate=False,
            profile=RouterProfile.MAIN_THREAD.value,
            model="",
            reasoning_effort="",
            agent_role="",
            close_after_result=False,
            idle_timeout_minutes=0,
            reuse_window="",
            waiting_policy="",
            decision_id=_new_decision_id(),
            task_family=assessed.task_family,
            refusal_stage="escalation_refusal",
            routing_confidence=assessed.base_confidence,
            manual_review_recommended=True,
            rescope_required=True,
            why=why,
            escalation_profile="",
            hard_gate_hits=[],
            prequeue_same_scope_reuse_claim_minutes=0,
            score_margin=0.0,
            failure_signals=_outcome_labels(outcome),
            prompt_wrapper_delta=prompt_delta,
            spawn_contract_lines=[],
            spawn_overrides={},
            spawn_agent_overrides={},
            close_agent_overrides={},
            host_tool_contract={},
            runtime_banner_lines=[],
            spawn_task_message="",
            native_spawn_payload={},
            task_class_profile=task_class_policy.default_profile.value,
            task_class_model=task_class_policy.default_profile.model,
            task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
            task_class_policy_lines=task_class_policy_lines,
            explanation_lines=[why, *prompt_delta],
            scorecard={},
            assessment=assessed.as_dict(),
            odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessed),
        )
    next_profile = _next_profile_for_escalation(decision, assessed, outcome)
    if next_profile is None:
        return None
    why = (
        f"escalated from `{decision.profile}` to `{next_profile.value}` "
        f"because the first pass reported {', '.join(_outcome_labels(outcome))}"
    )
    prompt_delta = _prompt_wrapper_delta(outcome=outcome, assessment=assessed)
    next_lifecycle = _delegated_leaf_lifecycle_payload(profile=next_profile, assessment=assessed)
    next_agent_role = next_lifecycle.agent_role
    termination_expectation = next_lifecycle.termination_expectation
    next_spawn_overrides = next_lifecycle.spawn_overrides
    next_spawn_agent_overrides = next_lifecycle.spawn_agent_overrides
    next_close_agent_overrides = next_lifecycle.close_agent_overrides
    next_host_tool_contract = next_lifecycle.host_tool_contract
    next_runtime_banner_lines = next_lifecycle.runtime_banner_lines
    next_spawn_task_message = (
        _spawn_task_message(
            request=request,
            profile=next_profile,
            assessment=assessed,
            termination_expectation=termination_expectation,
        )
        if request is not None
        else ""
    )
    next_native_spawn_payload = (
        _native_spawn_payload(profile=next_profile, assessment=assessed, message=next_spawn_task_message)
        if request is not None
        else {}
    )
    next_step = _next_profile_for_escalation(
        RoutingDecision(
            delegate=True,
            profile=next_profile.value,
            model=next_profile.model,
            reasoning_effort=next_profile.reasoning_effort,
            agent_role=next_agent_role,
            close_after_result=True,
            idle_timeout_minutes=_DEFAULT_IDLE_TIMEOUT_MINUTES,
            reuse_window=_DEFAULT_REUSE_WINDOW,
            waiting_policy=_DEFAULT_WAITING_POLICY,
            decision_id=_new_decision_id(),
            task_family=assessed.task_family,
            refusal_stage="delegated",
            routing_confidence=assessed.base_confidence,
            manual_review_recommended=next_profile is RouterProfile.GPT54_XHIGH,
            rescope_required=False,
            why=why,
            escalation_profile="",
            hard_gate_hits=[],
            prequeue_same_scope_reuse_claim_minutes=_DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES,
            score_margin=0.0,
            failure_signals=[],
            prompt_wrapper_delta=[],
            spawn_contract_lines=_spawn_contract_lines(profile=next_profile, assessment=assessed),
            spawn_overrides=next_spawn_overrides,
            spawn_agent_overrides=next_spawn_agent_overrides,
            close_agent_overrides=next_close_agent_overrides,
            host_tool_contract=next_host_tool_contract,
            runtime_banner_lines=next_runtime_banner_lines,
            spawn_task_message=next_spawn_task_message,
            native_spawn_payload=next_native_spawn_payload,
            idle_timeout_action=_DEFAULT_IDLE_TIMEOUT_ACTION,
            idle_timeout_escalation=_DEFAULT_IDLE_TIMEOUT_ESCALATION,
            termination_expectation=termination_expectation,
            task_class_profile=task_class_policy.default_profile.value,
            task_class_model=task_class_policy.default_profile.model,
            task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
            task_class_policy_lines=task_class_policy_lines,
            assessment=assessed.as_dict(),
            odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessed, selected=next_profile),
        ),
        assessed,
        outcome,
    )
    return RoutingDecision(
        delegate=True,
        profile=next_profile.value,
        model=next_profile.model,
        reasoning_effort=next_profile.reasoning_effort,
        agent_role=next_agent_role,
        close_after_result=True,
        idle_timeout_minutes=_DEFAULT_IDLE_TIMEOUT_MINUTES,
        reuse_window=_DEFAULT_REUSE_WINDOW,
        waiting_policy=_DEFAULT_WAITING_POLICY,
        decision_id=_new_decision_id(),
        task_family=assessed.task_family,
        refusal_stage="delegated",
        routing_confidence=assessed.base_confidence,
        manual_review_recommended=next_profile is RouterProfile.GPT54_XHIGH,
        rescope_required=False,
        why=why,
        escalation_profile=next_step.value if next_step is not None else "",
        hard_gate_hits=[],
        prequeue_same_scope_reuse_claim_minutes=_DEFAULT_PREQUEUE_SAME_SCOPE_REUSE_CLAIM_MINUTES,
        score_margin=0.0,
        failure_signals=_outcome_labels(outcome),
        prompt_wrapper_delta=prompt_delta,
        spawn_contract_lines=_spawn_contract_lines(profile=next_profile, assessment=assessed),
        spawn_overrides=next_spawn_overrides,
        spawn_agent_overrides=next_spawn_agent_overrides,
        close_agent_overrides=next_close_agent_overrides,
        host_tool_contract=next_host_tool_contract,
        runtime_banner_lines=next_runtime_banner_lines,
        spawn_task_message=next_spawn_task_message,
        native_spawn_payload=next_native_spawn_payload,
        idle_timeout_action=_DEFAULT_IDLE_TIMEOUT_ACTION,
        idle_timeout_escalation=_DEFAULT_IDLE_TIMEOUT_ESCALATION,
        termination_expectation=termination_expectation,
        task_class_profile=task_class_policy.default_profile.value,
        task_class_model=task_class_policy.default_profile.model,
        task_class_reasoning_effort=task_class_policy.default_profile.reasoning_effort,
        task_class_policy_lines=task_class_policy_lines,
        explanation_lines=[
            why,
            *prompt_delta,
        ],
        scorecard={},
        assessment=assessed.as_dict(),
        odylith_execution_profile=_decision_odylith_execution_profile(assessment=assessed, selected=next_profile),
    )


def _outcome_labels(outcome: RouteOutcome) -> list[str]:
    labels: list[str] = []
    if outcome.accepted:
        labels.append("accepted")
    if outcome.blocked:
        labels.append("blocked")
    if outcome.ambiguous:
        labels.append("ambiguous")
    if outcome.artifact_missing:
        labels.append("artifact_missing")
    if outcome.quality_too_weak:
        labels.append("quality_too_weak")
    if outcome.escalated:
        labels.append("escalated")
    if outcome.broader_coordination:
        labels.append("broader_coordination")
    return labels or ["no_outcome_flags"]


def record_outcome(
    *,
    repo_root: Path,
    decision: RoutingDecision,
    outcome: RouteOutcome,
    request: RouteRequest | None = None,
) -> dict[str, Any]:
    _validated_profile(decision)
    state = load_tuning_state(repo_root=repo_root)
    profile = decision.profile
    assessed = _task_assessment_from_mapping(decision.assessment if isinstance(decision.assessment, Mapping) else None)
    if assessed is None and request is not None and not _route_request_validation_errors(request):
        assessed = assess_request(request)
    task_family = (
        assessed.task_family
        if assessed is not None
        else _task_family_key(
            decision.task_family
            or (dict(decision.assessment).get("task_family", "") if isinstance(decision.assessment, Mapping) else "")
        )
    )
    labels = _outcome_labels(outcome)
    recorded_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    outcome_key = _outcome_identity(decision, outcome, task_family=task_family)
    if not _remember_outcome_key(state, outcome_key=outcome_key, seen_at=recorded_at):
        state.updated_at = recorded_at
        path = save_tuning_state(repo_root=repo_root, state=state)
        return {
            "profile": profile,
            "task_family": task_family,
            "labels": labels,
            "replayed": True,
            "outcome_key": outcome_key,
            "bias_delta": 0.0,
            "bias_after": round(float(state.profile_bias.get(profile, 0.0) or 0.0), 3),
            "family_bias_delta": 0.0,
            "family_bias_after": round(float(state.family_profile_bias.get(task_family, {}).get(profile, 0.0) or 0.0), 3),
            "successor_family_bias_delta": 0.0,
            "tuning_path": str(path),
            "state": state.as_dict(),
        }
    counts = dict(state.outcome_counts.get(profile, {}))
    for label in labels:
        counts[label] = int(counts.get(label, 0) or 0) + 1
    state.outcome_counts[profile] = counts
    state.family_profile_bias.setdefault(task_family, _default_profile_bias_map())
    state.family_outcome_counts.setdefault(task_family, _default_outcome_counts_map())
    family_counts = dict(state.family_outcome_counts[task_family].get(profile, {}))
    for label in labels:
        family_counts[label] = int(family_counts.get(label, 0) or 0) + 1
    state.family_outcome_counts[task_family][profile] = family_counts

    bias_delta = 0.0
    family_bias_delta = 0.0
    successor_family_bias_delta = 0.0
    if profile in state.profile_bias:
        if outcome.accepted and not any((outcome.blocked, outcome.ambiguous, outcome.artifact_missing, outcome.quality_too_weak)):
            bias_delta = _DEFAULT_BIAS_DELTA
            family_bias_delta = _DEFAULT_FAMILY_BIAS_DELTA
        elif outcome.blocked or outcome.ambiguous or outcome.artifact_missing or outcome.quality_too_weak:
            bias_delta = -_DEFAULT_BIAS_DELTA
            family_bias_delta = -_DEFAULT_FAMILY_BIAS_DELTA
        if outcome.broader_coordination:
            bias_delta = min(bias_delta, -0.04)
            family_bias_delta = min(family_bias_delta, -0.1)
        state.profile_bias[profile] = _clamp_bias(float(state.profile_bias.get(profile, 0.0) or 0.0) + bias_delta)
        state.family_profile_bias[task_family][profile] = _clamp_bias(
            float(state.family_profile_bias[task_family].get(profile, 0.0) or 0.0) + family_bias_delta
        )
        if family_bias_delta < 0 and assessed is not None:
            successor = _next_profile_for_escalation(decision, assessed, outcome)
            if successor is not None:
                successor_family_bias_delta = round(abs(family_bias_delta) / 2.0, 3)
                state.family_profile_bias[task_family][successor.value] = _clamp_bias(
                    float(state.family_profile_bias[task_family].get(successor.value, 0.0) or 0.0)
                    + successor_family_bias_delta
                )

    state.updated_at = recorded_at
    path = save_tuning_state(repo_root=repo_root, state=state)
    odylith_evaluation_ledger.append_event(
        repo_root=repo_root,
        event_type="router_outcome",
        event_id=outcome_key,
        payload=odylith_evaluation_ledger.router_outcome_event_payload(
            decision=decision.as_dict(),
            outcome=outcome.as_dict(),
            request=request.as_dict() if request is not None else None,
        ),
        recorded_at=recorded_at,
    )
    return {
        "profile": profile,
        "task_family": task_family,
        "labels": labels,
        "replayed": False,
        "outcome_key": outcome_key,
        "bias_delta": round(bias_delta, 3),
        "bias_after": round(float(state.profile_bias.get(profile, 0.0) or 0.0), 3),
        "family_bias_delta": round(family_bias_delta, 3),
        "family_bias_after": round(float(state.family_profile_bias[task_family].get(profile, 0.0) or 0.0), 3),
        "successor_family_bias_delta": round(successor_family_bias_delta, 3),
        "tuning_path": str(path),
        "state": state.as_dict(),
    }


def append_route_audit(
    *,
    repo_root: Path,
    request: RouteRequest,
    decision: RoutingDecision,
    outcome: RouteOutcome | None = None,
    stream_path: Path | None = None,
) -> dict[str, Any]:
    stream = stream_path or (Path(repo_root).resolve() / DEFAULT_STREAM_PATH).resolve()
    artifacts = list(request.artifacts or request.allowed_paths or [])
    if not artifacts:
        artifacts = ["src/odylith/runtime/orchestration/subagent_router.py"]
    components = list(request.components or [DEFAULT_COMPONENT_ID])
    if outcome is None:
        summary = (
            f"Subagent router {'delegated' if decision.delegate else 'kept local'} "
            f"with profile {decision.profile or 'main_thread'} for family {decision.task_family or 'unknown'}."
        )
        kind = "decision"
    else:
        summary = (
            f"Subagent router recorded outcome {', '.join(_outcome_labels(outcome))} "
            f"for {decision.profile or 'main_thread'} in family {decision.task_family or 'unknown'}."
        )
        kind = "implementation"
    return compass_timeline.append_event(
        repo_root=repo_root,
        stream_path=stream,
        kind=kind,
        summary=summary,
        workstream_values=request.workstreams,
        artifact_values=artifacts,
        component_values=components,
    )


def _route_decision_from_mapping(payload: Mapping[str, Any]) -> RoutingDecision:
    assessment_payload = dict(payload.get("assessment", {})) if isinstance(payload.get("assessment", {}), Mapping) else {}
    raw_spawn_overrides = payload.get("spawn_overrides", {})
    raw_spawn_agent_overrides = payload.get("spawn_agent_overrides", {})
    raw_close_agent_overrides = payload.get("close_agent_overrides", {})
    raw_host_tool_contract = payload.get("host_tool_contract", {})
    return RoutingDecision(
        delegate=_normalize_bool(payload.get("delegate", False)),
        profile=_normalize_token(payload.get("profile", "")) or RouterProfile.MAIN_THREAD.value,
        model=_normalize_string(payload.get("model", "")),
        reasoning_effort=_normalize_token(payload.get("reasoning_effort", "")),
        agent_role=_normalize_token(payload.get("agent_role", "")),
        close_after_result=_normalize_bool(payload.get("close_after_result", False)),
        idle_timeout_minutes=max(0, int(payload.get("idle_timeout_minutes", 0) or 0)),
        reuse_window=_normalize_token(payload.get("reuse_window", "")),
        waiting_policy=_normalize_token(payload.get("waiting_policy", "")),
        decision_id=_normalize_string(payload.get("decision_id", "")),
        task_family=_normalize_token(payload.get("task_family", "")) or _task_family_key(assessment_payload.get("task_family", "")),
        refusal_stage=_normalize_token(payload.get("refusal_stage", "")),
        routing_confidence=_clamp_score(payload.get("routing_confidence", 0) or 0),
        manual_review_recommended=_normalize_bool(payload.get("manual_review_recommended", False)),
        rescope_required=_normalize_bool(payload.get("rescope_required", False)),
        why=_normalize_string(payload.get("why", "")),
        escalation_profile=_normalize_token(payload.get("escalation_profile", "")),
        hard_gate_hits=_normalize_list(payload.get("hard_gate_hits", [])),
        prequeue_same_scope_reuse_claim_minutes=max(
            0,
            int(payload.get("prequeue_same_scope_reuse_claim_minutes", 0) or 0),
        ),
        score_margin=round(float(payload.get("score_margin", 0.0) or 0.0), 3),
        failure_signals=_normalize_list(payload.get("failure_signals", [])),
        prompt_wrapper_delta=_normalize_list(payload.get("prompt_wrapper_delta", [])),
        spawn_overrides={
            _normalize_token(key): value
            for key, value in dict(raw_spawn_overrides).items()
            if _normalize_token(key)
        }
        if isinstance(raw_spawn_overrides, Mapping)
        else {},
        spawn_agent_overrides={
            _normalize_token(key): value
            for key, value in dict(raw_spawn_agent_overrides).items()
            if _normalize_token(key)
        }
        if isinstance(raw_spawn_agent_overrides, Mapping)
        else {},
        close_agent_overrides={
            _normalize_token(key): value
            for key, value in dict(raw_close_agent_overrides).items()
            if _normalize_token(key)
        }
        if isinstance(raw_close_agent_overrides, Mapping)
        else {},
        host_tool_contract={
            _normalize_token(key): value
            for key, value in dict(raw_host_tool_contract).items()
            if _normalize_token(key)
        }
        if isinstance(raw_host_tool_contract, Mapping)
        else {},
        runtime_banner_lines=_normalize_list(payload.get("runtime_banner_lines", [])),
        spawn_task_message=_normalize_multiline_string(payload.get("spawn_task_message", "")),
        native_spawn_payload={
            _normalize_token(key): value
            for key, value in dict(payload.get("native_spawn_payload", {})).items()
            if _normalize_token(key)
        }
        if isinstance(payload.get("native_spawn_payload", {}), Mapping)
        else {},
        spawn_contract_lines=_normalize_list(payload.get("spawn_contract_lines", [])),
        idle_timeout_action=_normalize_token(payload.get("idle_timeout_action", "")),
        idle_timeout_escalation=_normalize_token(payload.get("idle_timeout_escalation", "")),
        termination_expectation=_normalize_string(payload.get("termination_expectation", "")),
        task_class_profile=_normalize_token(payload.get("task_class_profile", "")),
        task_class_model=_normalize_string(payload.get("task_class_model", "")),
        task_class_reasoning_effort=_normalize_token(payload.get("task_class_reasoning_effort", "")),
        task_class_policy_lines=_normalize_list(payload.get("task_class_policy_lines", [])),
        explanation_lines=_normalize_list(payload.get("explanation_lines", [])),
        scorecard={
            _normalize_token(key): round(float(value or 0.0), 3)
            for key, value in dict(payload.get("scorecard", {})).items()
            if _normalize_token(key)
        }
        if isinstance(payload.get("scorecard", {}), Mapping)
        else {},
        assessment=assessment_payload,
        odylith_execution_profile={
            _normalize_token(key): value
            for key, value in dict(payload.get("odylith_execution_profile", {})).items()
            if _normalize_token(key)
        }
        if isinstance(payload.get("odylith_execution_profile", {}), Mapping)
        else {},
    )


def _load_json_input(*, inline_value: str, file_value: str, name: str) -> dict[str, Any]:
    if _normalize_string(file_value):
        path = Path(_normalize_string(file_value)).expanduser().resolve()
        if not path.is_file():
            raise RouterInputError(
                code="missing_input_file",
                message=f"{name} file was not found",
                details=[str(path)],
            )
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RouterInputError(
                code="unreadable_input_file",
                message=f"{name} file could not be read",
                details=[str(path), str(exc)],
            ) from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RouterInputError(
                code="invalid_json",
                message=f"{name} file did not contain valid JSON",
                details=[str(path), f"line {exc.lineno} column {exc.colno}: {exc.msg}"],
            ) from exc
        if not isinstance(payload, Mapping):
            raise RouterInputError(
                code="invalid_payload_type",
                message=f"{name} must be a JSON object",
                details=[str(path)],
            )
        return dict(payload)
    token = str(inline_value or "").strip()
    if not token:
        return {}
    if token == "-":
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RouterInputError(
                code="invalid_json",
                message=f"{name} stdin did not contain valid JSON",
                details=[f"line {exc.lineno} column {exc.colno}: {exc.msg}"],
            ) from exc
        if not isinstance(payload, Mapping):
            raise RouterInputError(
                code="invalid_payload_type",
                message=f"{name} must be a JSON object",
            )
        return dict(payload)
    try:
        payload = json.loads(token)
    except json.JSONDecodeError as exc:
        raise RouterInputError(
            code="invalid_json",
            message=f"{name} inline JSON was invalid",
            details=[f"line {exc.lineno} column {exc.colno}: {exc.msg}"],
        ) from exc
    if not isinstance(payload, Mapping):
        raise RouterInputError(
            code="invalid_payload_type",
            message=f"{name} must be a JSON object",
        )
    return dict(payload)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _emit_payload(payload: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print("subagent router")
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"- {key}: {json.dumps(value, sort_keys=True)}")
        else:
            print(f"- {key}: {value}")


def _emit_error(error: RouterInputError, *, as_json: bool) -> None:
    payload = error.as_payload()
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print("subagent router error")
    print(f"- error_code: {payload['error_code']}")
    print(f"- message: {payload['message']}")
    for detail in payload["details"]:
        print(f"- detail: {detail}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith subagent-router",
        description="Route bounded Codex subtasks to the right subagent profile.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Assess a bounded task and choose the route profile.")
    route.add_argument("--repo-root", default=".")
    route.add_argument("--input-json", default="")
    route.add_argument("--input-file", default="")
    route.add_argument("--json", action="store_true")
    route.add_argument("--log-compass", action="store_true")
    route.add_argument("--stream", default=DEFAULT_STREAM_PATH)

    escalate = sub.add_parser("escalate", help="Choose the next profile after an explicit failure signal.")
    escalate.add_argument("--repo-root", default=".")
    escalate.add_argument("--decision-json", default="")
    escalate.add_argument("--decision-file", default="")
    escalate.add_argument("--outcome-json", default="")
    escalate.add_argument("--outcome-file", default="")
    escalate.add_argument("--json", action="store_true")
    escalate.add_argument("--log-compass", action="store_true")
    escalate.add_argument("--request-json", default="")
    escalate.add_argument("--request-file", default="")
    escalate.add_argument("--stream", default=DEFAULT_STREAM_PATH)

    record = sub.add_parser("record-outcome", help="Persist adaptive tuning from a delegated outcome.")
    record.add_argument("--repo-root", default=".")
    record.add_argument("--decision-json", default="")
    record.add_argument("--decision-file", default="")
    record.add_argument("--outcome-json", default="")
    record.add_argument("--outcome-file", default="")
    record.add_argument("--json", action="store_true")
    record.add_argument("--log-compass", action="store_true")
    record.add_argument("--request-json", default="")
    record.add_argument("--request-file", default="")
    record.add_argument("--stream", default=DEFAULT_STREAM_PATH)

    show = sub.add_parser("show-tuning", help="Show local adaptive tuning state.")
    show.add_argument("--repo-root", default=".")
    show.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    try:
        if args.command == "route":
            request_payload = _load_json_input(
                inline_value=str(args.input_json),
                file_value=str(args.input_file),
                name="route request",
            )
            request = route_request_from_mapping(request_payload)
            decision = route_request(request, repo_root=repo_root)
            if args.log_compass:
                append_route_audit(
                    repo_root=repo_root,
                    request=request,
                    decision=decision,
                    stream_path=_resolve(repo_root, str(args.stream)),
                )
            _emit_payload(decision.as_dict(), as_json=bool(args.json))
            return 0

        if args.command == "escalate":
            decision_payload = _load_json_input(
                inline_value=str(args.decision_json),
                file_value=str(args.decision_file),
                name="decision payload",
            )
            outcome_payload = _load_json_input(
                inline_value=str(args.outcome_json),
                file_value=str(args.outcome_file),
                name="outcome payload",
            )
            request_payload = _load_json_input(
                inline_value=str(args.request_json),
                file_value=str(args.request_file),
                name="request payload",
            )
            decision = _route_decision_from_mapping(decision_payload)
            outcome = route_outcome_from_mapping(outcome_payload)
            request = route_request_from_mapping(request_payload) if request_payload else None
            escalated = escalate_routing_decision(
                decision=decision,
                outcome=outcome,
                request=request,
            )
            payload: Mapping[str, Any] = (
                escalated.as_dict() if escalated is not None else {"delegate": False, "profile": "", "why": "no escalation available"}
            )
            if args.log_compass and escalated is not None:
                append_route_audit(
                    repo_root=repo_root,
                    request=request or RouteRequest(prompt=decision.why or "subagent-router-followup"),
                    decision=escalated,
                    outcome=RouteOutcome(escalated=True, notes=outcome.notes),
                    stream_path=_resolve(repo_root, str(args.stream)),
                )
            _emit_payload(payload, as_json=bool(args.json))
            return 0

        if args.command == "record-outcome":
            decision_payload = _load_json_input(
                inline_value=str(args.decision_json),
                file_value=str(args.decision_file),
                name="decision payload",
            )
            outcome_payload = _load_json_input(
                inline_value=str(args.outcome_json),
                file_value=str(args.outcome_file),
                name="outcome payload",
            )
            request_payload = _load_json_input(
                inline_value=str(args.request_json),
                file_value=str(args.request_file),
                name="request payload",
            )
            decision = _route_decision_from_mapping(decision_payload)
            outcome = route_outcome_from_mapping(outcome_payload)
            request = route_request_from_mapping(request_payload) if request_payload else None
            payload = record_outcome(repo_root=repo_root, decision=decision, outcome=outcome, request=request)
            if args.log_compass:
                append_route_audit(
                    repo_root=repo_root,
                    request=request or RouteRequest(prompt=decision.why or "subagent-router-outcome"),
                    decision=decision,
                    outcome=outcome,
                    stream_path=_resolve(repo_root, str(args.stream)),
                )
            _emit_payload(payload, as_json=bool(args.json))
            return 0

        if args.command == "show-tuning":
            state = load_tuning_state(repo_root=repo_root)
            _emit_payload(state.as_dict(), as_json=bool(args.json))
            return 0
    except RouterInputError as error:
        _emit_error(error, as_json=bool(getattr(args, "json", False)))
        return error.exit_code

    return 2


__all__ = [
    "DEFAULT_STREAM_PATH",
    "DEFAULT_TUNING_PATH",
    "RouteOutcome",
    "RouteRequest",
    "RouterProfile",
    "RouterInputError",
    "RoutingDecision",
    "TaskAssessment",
    "TuningState",
    "append_route_audit",
    "assess_request",
    "escalate_routing_decision",
    "infer_explicit_paths",
    "load_tuning_state",
    "record_outcome",
    "route_outcome_from_mapping",
    "route_request",
    "route_request_from_mapping",
    "save_tuning_state",
    "tuning_state_path",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
