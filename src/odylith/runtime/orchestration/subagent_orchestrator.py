"""Prompt-level orchestration for accuracy-first Codex delegation.

This module sits above the bounded Subagent Router and decides whether a
grounded repo-work prompt should stay local, run as one bounded leaf, or fan
out into a conservative serial or parallel batch. The orchestrator emits an
execution plan for the live agent to follow; it does not mutate the host chat
session or spawn subagents by itself.

Invariants:
- Non-repo-work or trivial direct-answer prompts stay local.
- Hard local-only gates always beat decomposition or fan-out.
- The Subagent Router remains the leaf-routing authority.
- Parallel fan-out is conservative and requires explicit owned-path clarity.
- Adaptive tuning is local-only under `.odylith/` and cannot override hard gates.
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
import sys
from typing import Any
from typing import Mapping
from typing import Sequence
import uuid

from odylith.runtime.common import log_compass_timeline_event as compass_timeline
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.context_engine import odylith_context_engine_store as odylith_store
from odylith.runtime.evaluation import odylith_evaluation_ledger
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.orchestration import subagent_router as leaf_router
from odylith.runtime.orchestration import subagent_orchestrator_runtime_signals
from odylith.runtime.orchestration import subagent_orchestrator_subtasks_runtime
from odylith.runtime.orchestration import subagent_orchestrator_odylith_runtime


DEFAULT_TUNING_PATH = ".odylith/subagent_orchestrator/tuning.v1.json"
DEFAULT_DECISION_LEDGER_DIR = ".odylith/subagent_orchestrator/decision-ledgers"
DEFAULT_STREAM_PATH = "odylith/compass/runtime/codex-stream.v1.jsonl"
DEFAULT_COMPONENT_ID = "subagent-orchestrator"
_TUNING_VERSION = "v1"
_DECISION_LEDGER_VERSION = "v1"
_BIAS_LIMIT = 0.75
_DEFAULT_BIAS_DELTA = 0.05
_DEFAULT_FAMILY_BIAS_DELTA = 0.07
_FEEDBACK_LEDGER_LIMIT = 512
_DECISION_LEDGER_EVENT_LIMIT = 128
_WRITE_PARALLEL_PREFIXES: frozenset[str] = frozenset({"scripts", "services", "app", "infra"})
_IMPLEMENTATION_ROLE_PREFIXES: frozenset[str] = frozenset({"bin", "infra", "app", "scripts", "services"})
_SAME_PREFIX_DISJOINT_PREFIXES: frozenset[str] = frozenset({"scripts", "services", "app"})
_COUPLED_WRITE_PREFIXES: frozenset[str] = frozenset(
    {
        "tests",
        "docs",
        "skills",
        "contracts",
        "odylith",
        "agents-guidelines",
    }
)
_TEST_PREFIXES: frozenset[str] = frozenset({"tests", "mocks"})
_DOC_PREFIXES: frozenset[str] = frozenset({"docs", "skills", "agents-guidelines"})
_GOVERNANCE_PREFIXES: frozenset[str] = frozenset()
_CONTRACT_PREFIXES: frozenset[str] = frozenset({"contracts"})
_KNOWN_MODES: tuple[str, ...] = ("local_only", "single_leaf", "serial_batch", "parallel_batch")
_KNOWN_TASK_FAMILIES: tuple[str, ...] = tuple(leaf_router._KNOWN_TASK_FAMILIES)  # noqa: SLF001
_KNOWN_FOLLOWUP_STATUSES: frozenset[str] = frozenset({"not_queued", "claimed", "queued", "sent", "running"})
_ACTIVE_FOLLOWUP_STATUSES: frozenset[str] = frozenset({"queued", "sent", "running"})
_DECOMPOSABLE_COORDINATION_GATES: frozenset[str] = frozenset({"coordination-cost-high", "mixed-phase-write-slice"})
_HOST_LOCAL_GOVERNANCE_PATH_PREFIXES: tuple[str, ...] = (
    "odylith/technical-plans/",
    "odylith/radar/source/",
    "odylith/casebook/bugs/",
    "odylith/registry/source/",
    "odylith/atlas/source/",
    "odylith/compass/runtime/",
    "odylith/runtime/source/",
)
_ODYLITH_CONTRACT_PATH_PREFIXES: tuple[str, ...] = (
    "odylith/skills/",
    "odylith/agents-guidelines/",
)
_ODYLITH_DOC_PATH_PREFIXES: tuple[str, ...] = (
    "odylith/maintainer/",
)
_ODYLITH_GOVERNANCE_PATH_PREFIXES: tuple[str, ...] = (
    "odylith/technical-plans/",
    "odylith/radar/source/",
    "odylith/casebook/bugs/",
    "odylith/registry/source/",
    "odylith/atlas/source/",
    "odylith/compass/runtime/",
    "odylith/runtime/source/",
)
_ODYLITH_IMPLEMENTATION_PATH_PREFIXES: tuple[str, ...] = (
    "odylith/index.html",
    "odylith/tooling-app.v1.js",
    "odylith/tooling-payload.v1.js",
    "odylith/radar/",
    "odylith/registry/",
    "odylith/casebook/",
    "odylith/atlas/",
    "odylith/compass/",
)
_KNOWN_ODYLITH_OPERATIONS: frozenset[str] = frozenset(
    {"auto", "impact", "architecture", "governance_slice", "session_brief", "bootstrap_session"}
)
_GOVERNANCE_GROUNDING_KEYWORDS: tuple[str, ...] = (
    "governance",
    "workstream",
    "backlog",
    "plan binding",
    "traceability",
    "closeout",
    "delivery truth",
    "registry",
    "compass",
    "radar",
    "sync_workstream_artifacts",
    "governed surface",
)
_ARCHITECTURE_GROUNDING_KEYWORDS: tuple[str, ...] = (
    "architecture",
    "topology",
    "control-plane",
    "shared-stack",
    "shared stack",
    "diagram",
    "mermaid",
    "authority chain",
    "blast radius",
    "ownership boundary",
    "tenant boundary",
)
_CODEX_HOT_PATH_PROFILE = "codex_hot_path"


class OrchestrationMode(str, Enum):
    LOCAL_ONLY = "local_only"
    SINGLE_LEAF = "single_leaf"
    SERIAL_BATCH = "serial_batch"
    PARALLEL_BATCH = "parallel_batch"


class ParallelSafetyClass(str, Enum):
    READ_ONLY_SAFE = "read_only_safe"
    DISJOINT_WRITE_SAFE = "disjoint_write_safe"
    SERIAL_ORDERED = "serial_ordered"
    LOCAL_ONLY = "local_only"


@dataclass
class OrchestrationRequest:
    """Grounded prompt-level request before orchestration."""

    prompt: str
    acceptance_criteria: list[str] = field(default_factory=list)
    candidate_paths: list[str] = field(default_factory=list)
    workstreams: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    accuracy_preference: str = "accuracy"
    repo_work: bool = True
    task_kind: str = ""
    phase: str = ""
    needs_write: bool = False
    latency_sensitive: bool = False
    correctness_critical: bool = False
    requires_multi_agent_adjudication: bool = False
    evolving_context_required: bool = False
    evidence_cone_grounded: bool = False
    use_working_tree: bool = False
    working_tree_scope: str = "repo"
    session_id: str = ""
    claimed_paths: list[str] = field(default_factory=list)
    intent: str = ""
    odylith_operation: str = "auto"
    odylith_auto_ground: bool = True
    context_signals: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SubtaskSlice:
    """One bounded leaf emitted by the orchestrator."""

    id: str
    prompt: str
    route_prompt: str = ""
    execution_group_kind: str = ""
    scope_role: str = ""
    task_kind: str = ""
    phase: str = ""
    correctness_critical: bool = False
    latency_sensitive: bool = False
    accuracy_preference: str = "accuracy"
    owned_paths: list[str] = field(default_factory=list)
    read_paths: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    owner: str = ""
    goal: str = ""
    expected_output: str = ""
    termination_condition: str = ""
    prompt_contract_lines: list[str] = field(default_factory=list)
    spawn_task_message: str = ""
    validation_commands: list[str] = field(default_factory=list)
    merge_owner: str = "main_thread"
    escalation_allowed: bool = True
    route_profile: str = ""
    route_model: str = ""
    route_reasoning_effort: str = ""
    route_task_class_profile: str = ""
    route_task_class_model: str = ""
    route_task_class_reasoning_effort: str = ""
    route_task_class_policy_lines: list[str] = field(default_factory=list)
    route_agent_role: str = ""
    route_close_after_result: bool = False
    route_idle_timeout_minutes: int = 0
    route_idle_timeout_action: str = ""
    route_idle_timeout_escalation: str = ""
    route_reuse_window: str = ""
    route_prequeue_same_scope_reuse_claim_minutes: int = 0
    route_waiting_policy: str = ""
    route_termination_expectation: str = ""
    route_spawn_contract_lines: list[str] = field(default_factory=list)
    route_spawn_overrides: dict[str, Any] = field(default_factory=dict)
    route_spawn_agent_overrides: dict[str, Any] = field(default_factory=dict)
    route_close_agent_overrides: dict[str, Any] = field(default_factory=dict)
    route_host_tool_contract: dict[str, Any] = field(default_factory=dict)
    route_runtime_banner_lines: list[str] = field(default_factory=list)
    route_native_spawn_payload: dict[str, Any] = field(default_factory=dict)
    route_task_family: str = ""
    route_confidence: int = 0
    route_manual_review_recommended: bool = False
    route_why: str = ""
    route_explanation_lines: list[str] = field(default_factory=list)
    route_odylith_execution_profile: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MainThreadFollowup:
    """One explicit main-thread-owned follow-up that should not be delegated."""

    id: str
    scope_role: str = "governance"
    paths: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    owner: str = "main_thread"
    goal: str = ""
    deliverables: list[str] = field(default_factory=list)
    why_local: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FollowupGroup:
    """Planned local follow-up retained outside delegated leaf fan-out."""

    paths: list[str] = field(default_factory=list)
    scope_role: str = "governance"
    why_local: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestrationDecision:
    """Top-level orchestration plan for the live agent."""

    mode: str
    decision_id: str
    delegate: bool
    parallel_safety: str
    task_family: str
    confidence: int
    rationale: str
    refusal_stage: str
    manual_review_recommended: bool
    merge_owner: str
    merge_barrier_notes: list[str] = field(default_factory=list)
    execution_contract_notes: list[str] = field(default_factory=list)
    completion_closeout_overrides: dict[str, Any] = field(default_factory=dict)
    inspection_artifacts: dict[str, Any] = field(default_factory=dict)
    odylith_adoption: dict[str, Any] = field(default_factory=dict)
    local_only_reasons: list[str] = field(default_factory=list)
    budget_notes: list[str] = field(default_factory=list)
    main_thread_followups: list[MainThreadFollowup] = field(default_factory=list)
    subtasks: list[SubtaskSlice] = field(default_factory=list)
    request: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.rationale = _sanitize_user_facing_text(self.rationale)
        self.merge_barrier_notes = _sanitize_user_facing_lines(self.merge_barrier_notes)
        self.execution_contract_notes = _sanitize_user_facing_lines(self.execution_contract_notes)
        self.local_only_reasons = _sanitize_user_facing_lines(self.local_only_reasons)
        self.budget_notes = _sanitize_user_facing_lines(self.budget_notes)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionFeedback:
    """Structured orchestration outcome used for local tuning."""

    accepted: bool = False
    merge_conflicts: int = 0
    rescope_required: bool = False
    false_parallelization: bool = False
    escalated_leaves: int = 0
    token_efficient: bool = False
    feedback_id: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TuningState:
    """Local-only orchestration tuning state."""

    version: str = _TUNING_VERSION
    updated_at: str = ""
    mode_bias: dict[str, float] = field(default_factory=lambda: {mode: 0.0 for mode in _KNOWN_MODES})
    outcome_counts: dict[str, dict[str, int]] = field(default_factory=lambda: {mode: {} for mode in _KNOWN_MODES})
    family_mode_bias: dict[str, dict[str, float]] = field(
        default_factory=lambda: {family: {mode: 0.0 for mode in _KNOWN_MODES} for family in _KNOWN_TASK_FAMILIES}
    )
    family_outcome_counts: dict[str, dict[str, dict[str, int]]] = field(
        default_factory=lambda: {family: {mode: {} for mode in _KNOWN_MODES} for family in _KNOWN_TASK_FAMILIES}
    )
    applied_feedback_keys: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _normalize_context_signals(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {_normalize_string(key): raw for key, raw in value.items() if _normalize_string(key)}


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


def _normalize_odylith_operation(value: Any) -> str:
    token = _normalize_token(value) or "auto"
    return token if token in _KNOWN_ODYLITH_OPERATIONS else "auto"


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        token = _normalize_string(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _sanitize_user_facing_text(value: Any) -> str:
    return leaf_router._sanitize_user_facing_text(value)  # noqa: SLF001


def _sanitize_user_facing_lines(values: Sequence[str]) -> list[str]:
    return leaf_router._sanitize_user_facing_lines(values)  # noqa: SLF001


def _mapping_lookup(payload: Mapping[str, Any], key: str) -> Any:
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


def _nested_mapping(payload: Mapping[str, Any], *path: str) -> dict[str, Any]:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return {}
        current = _mapping_lookup(current, key)
    return dict(current) if isinstance(current, Mapping) else {}


def _execution_profile_mapping(value: Any) -> dict[str, Any]:
    profile = tooling_memory_contracts.execution_profile_mapping(value)
    if not profile:
        return {}
    selected = leaf_router._preferred_router_profile_from_execution_profile(profile)  # noqa: SLF001
    if selected is None:
        return profile
    profile["profile"] = selected.value
    profile["model"] = selected.model
    profile["reasoning_effort"] = selected.reasoning_effort
    return profile


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _normalized_rate(value: Any) -> float:
    numeric = _float_value(value)
    if numeric > 1.0:
        numeric = numeric / 100.0 if numeric <= 100.0 else 1.0
    return max(0.0, min(1.0, numeric))


def _request_seed_paths(request: OrchestrationRequest) -> list[str]:
    return _dedupe_strings([*request.candidate_paths, *request.claimed_paths])


def _request_has_odylith_seeds(request: OrchestrationRequest) -> bool:
    return bool(
        _request_seed_paths(request)
        or request.workstreams
        or request.components
        or request.session_id
        or request.use_working_tree
    )


def _payload_context_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}


def _payload_routing_handoff(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("routing_handoff", {})) if isinstance(payload.get("routing_handoff"), Mapping) else {}


def _compact_selection_state_parts(value: Any) -> tuple[str, str]:
    token = _normalize_string(value)
    if not token:
        return "", ""
    if token.startswith("x:"):
        return "explicit", _normalize_string(token[2:])
    if token.startswith("i:"):
        return "inferred_confident", _normalize_string(token[2:])
    return token, ""


def _payload_packet_kind(payload: Mapping[str, Any], *, context_packet: Mapping[str, Any], routing_handoff: Mapping[str, Any]) -> str:
    packet_kind = _normalize_token(payload.get("packet_kind"))
    if packet_kind:
        return packet_kind
    packet_kind = _normalize_token(context_packet.get("packet_kind"))
    if packet_kind:
        return packet_kind
    packet_kind = _normalize_token(routing_handoff.get("packet_kind"))
    if packet_kind:
        return packet_kind
    route = _nested_mapping(context_packet, "route")
    if route.get("governance"):
        return "governance_slice"
    return "impact" if context_packet else ""


def _odylith_payload_full_scan_recommended(payload: Mapping[str, Any]) -> bool:
    context_packet = _payload_context_packet(payload)
    architecture_audit = dict(payload.get("architecture_audit", {})) if isinstance(payload.get("architecture_audit"), Mapping) else {}
    return bool(
        payload.get("full_scan_recommended")
        or context_packet.get("full_scan_recommended")
        or architecture_audit.get("full_scan_recommended")
    )


def _odylith_payload_route_ready(payload: Mapping[str, Any]) -> bool:
    context_packet = _payload_context_packet(payload)
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    routing_handoff = _payload_routing_handoff(payload)
    return bool(payload.get("route_ready") or route.get("route_ready") or routing_handoff.get("route_ready"))


def _odylith_payload_selection_state(payload: Mapping[str, Any]) -> str:
    context_packet = _payload_context_packet(payload)
    state, _ = _compact_selection_state_parts(payload.get("selection_state") or context_packet.get("selection_state"))
    return _normalize_token(state)


def _odylith_payload_routing_confidence(payload: Mapping[str, Any]) -> str:
    context_packet = _payload_context_packet(payload)
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    routing_handoff = _payload_routing_handoff(payload)
    return (
        _normalize_token(routing_handoff.get("routing_confidence"))
        or _normalize_token(packet_quality.get("routing_confidence"))
        or _normalize_token(payload.get("routing_confidence"))
    )


def _odylith_payload_diagram_watch_gap_count(payload: Mapping[str, Any]) -> int:
    gaps = payload.get("diagram_watch_gaps", [])
    return len(gaps) if isinstance(gaps, list) else 0


def _odylith_payload_component_ids(payload: Mapping[str, Any]) -> list[str]:
    component_rows = payload.get("components", [])
    if not isinstance(component_rows, list):
        return []
    return _dedupe_strings(
        str(row.get("entity_id", "")).strip()
        for row in component_rows
        if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    )


def _odylith_payload_workstreams(payload: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("inferred_workstream", "workstream", "ws"):
        token = _normalize_string(payload.get(key, ""))
        if token:
            values.append(token)
    context_packet = _payload_context_packet(payload)
    _, compact_workstream = _compact_selection_state_parts(context_packet.get("selection_state"))
    if compact_workstream:
        values.append(compact_workstream)
    primary = dict(payload.get("primary_workstream", {})) if isinstance(payload.get("primary_workstream"), Mapping) else {}
    primary_id = _normalize_string(primary.get("entity_id", ""))
    if primary_id:
        values.append(primary_id)
    workstream_selection = dict(payload.get("workstream_selection", {})) if isinstance(payload.get("workstream_selection"), Mapping) else {}
    selected = dict(workstream_selection.get("selected_workstream", {})) if isinstance(workstream_selection.get("selected_workstream"), Mapping) else {}
    selected_id = _normalize_string(selected.get("entity_id", ""))
    if selected_id:
        values.append(selected_id)
    candidate_rows = payload.get("candidate_workstreams", [])
    if isinstance(candidate_rows, list):
        values.extend(
            str(row.get("entity_id", "")).strip()
            for row in candidate_rows
            if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
        )
    return _dedupe_strings(values)


def _odylith_payload_paths(payload: Mapping[str, Any]) -> list[str]:
    context_packet = _payload_context_packet(payload)
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    values: list[str] = []
    for key in ("changed_paths", "explicit_paths"):
        raw = payload.get(key, [])
        if isinstance(raw, list):
            values.extend(str(token).strip() for token in raw if str(token).strip())
    anchor_paths = anchors.get("changed_paths", [])
    if isinstance(anchor_paths, list):
        values.extend(str(token).strip() for token in anchor_paths if str(token).strip())
    return _dedupe_strings(values)


def _architecture_context_signals(payload: Mapping[str, Any]) -> dict[str, Any]:
    return subagent_orchestrator_odylith_runtime._architecture_context_signals(payload=payload)



def _odylith_payload_grounded(payload: Mapping[str, Any]) -> bool:
    return subagent_orchestrator_odylith_runtime._odylith_payload_grounded(payload=payload)



def _request_odylith_adoption(request: OrchestrationRequest) -> dict[str, Any]:
    return subagent_orchestrator_odylith_runtime._request_odylith_adoption(request=request)



def _decision_odylith_adoption(
    *,
    repo_root: Path | None,
    request: OrchestrationRequest,
    decision: OrchestrationDecision,
    final_changed_paths: Sequence[str] | None = None,
    changed_path_source: str = "",
) -> dict[str, Any]:
    return subagent_orchestrator_odylith_runtime._decision_odylith_adoption(
        repo_root=repo_root,
        request=request,
        decision=decision,
        final_changed_paths=final_changed_paths,
        changed_path_source=changed_path_source,
    )



def _request_prefers_architecture_grounding(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> bool:
    return subagent_orchestrator_odylith_runtime._request_prefers_architecture_grounding(request=request, assessment=assessment)



def _request_prefers_governance_grounding(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> bool:
    return subagent_orchestrator_odylith_runtime._request_prefers_governance_grounding(request=request, assessment=assessment)



def _auto_odylith_operation(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> str:
    return subagent_orchestrator_odylith_runtime._auto_odylith_operation(request=request, assessment=assessment)



def _auto_ground_request_with_odylith(
    request: OrchestrationRequest,
    *,
    repo_root: Path,
    assessment: leaf_router.TaskAssessment,
) -> OrchestrationRequest:
    return subagent_orchestrator_odylith_runtime._auto_ground_request_with_odylith(request=request, repo_root=repo_root, assessment=assessment)



def _architecture_policy_context(request: OrchestrationRequest) -> dict[str, Any]:
    base = _normalize_context_signals(request.context_signals)
    routing_handoff = _nested_mapping(base, "routing_handoff")
    context_packet = _nested_mapping(base, "context_packet")
    evidence_pack = _nested_mapping(base, "evidence_pack")
    architecture_audit = (
        _nested_mapping(base, "architecture_audit")
        or _nested_mapping(routing_handoff, "architecture_audit")
        or _nested_mapping(context_packet, "architecture_audit")
        or _nested_mapping(evidence_pack, "architecture_audit")
    )
    execution_hint = _nested_mapping(architecture_audit, "execution_hint")
    coverage = _nested_mapping(architecture_audit, "coverage")
    authority_graph = _nested_mapping(architecture_audit, "authority_graph")
    return {
        "active": bool(architecture_audit),
        "audit": architecture_audit,
        "execution_hint": execution_hint,
        "coverage": coverage,
        "mode": _normalize_token(_mapping_lookup(execution_hint, "mode")),
        "fanout": _normalize_token(_mapping_lookup(execution_hint, "fanout")),
        "risk_tier": _normalize_token(_mapping_lookup(execution_hint, "risk_tier")),
        "confidence_tier": _normalize_token(_mapping_lookup(coverage, "confidence_tier")),
        "full_scan_recommended": bool(_mapping_lookup(architecture_audit, "full_scan_recommended")),
        "unresolved_edge_count": _int_value(_mapping_lookup(coverage, "unresolved_edge_count")),
        "authority_graph_edge_count": _int_value(_mapping_lookup(_nested_mapping(authority_graph, "counts"), "edges")),
    }


def _score_level(score: int) -> str:
    return subagent_orchestrator_odylith_runtime._score_level(score=score)



def _intent_confidence_score(value: Any) -> int:
    return subagent_orchestrator_odylith_runtime._intent_confidence_score(value=value)



def _profile_runtime_fields(profile_token: str) -> tuple[str, str, str]:
    return subagent_orchestrator_odylith_runtime._profile_runtime_fields(profile_token=profile_token)



def _subtask_odylith_execution_profile(
    *,
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    subtask: SubtaskSlice,
    intent_profile: Mapping[str, Any],
    architecture_audit: Mapping[str, Any],
    base_root: Mapping[str, Any],
    base_context_packet: Mapping[str, Any],
    base_optimization_snapshot: Mapping[str, Any],
    route_ready: bool,
    narrowing_required: bool,
    validation_pressure: int,
    utility_score: int,
    token_efficiency_score: int,
    routing_confidence_score: int,
    spawn_worthiness: int,
    merge_burden: int,
) -> dict[str, Any]:
    return subagent_orchestrator_odylith_runtime._subtask_odylith_execution_profile(request=request, assessment=assessment, subtask=subtask, intent_profile=intent_profile, architecture_audit=architecture_audit, base_root=base_root, base_context_packet=base_context_packet, base_optimization_snapshot=base_optimization_snapshot, route_ready=route_ready, narrowing_required=narrowing_required, validation_pressure=validation_pressure, utility_score=utility_score, token_efficiency_score=token_efficiency_score, routing_confidence_score=routing_confidence_score, spawn_worthiness=spawn_worthiness, merge_burden=merge_burden)



def _subtask_intent_profile(
    *,
    request: OrchestrationRequest,
    subtask: SubtaskSlice,
    all_subtasks: Sequence[SubtaskSlice],
    base_root: Mapping[str, Any],
    base_packet_quality: Mapping[str, Any],
) -> dict[str, Any]:
    base_intent = _nested_mapping(base_root, "intent") or _nested_mapping(base_packet_quality, "intent_profile")
    base_family = _normalize_token(_mapping_lookup(base_intent, "family"))
    base_mode = _normalize_token(_mapping_lookup(base_intent, "mode"))
    base_critical_path = _normalize_token(_mapping_lookup(base_intent, "critical_path"))
    base_confidence_score = _intent_confidence_score(_mapping_lookup(base_intent, "confidence"))
    base_explicit = bool(_mapping_lookup(base_intent, "explicit"))
    implementation_present = any(planned.scope_role in {"implementation", "contract"} for planned in all_subtasks)

    if subtask.scope_role == "implementation":
        family = "implementation"
        mode = "write_execution"
        critical_path = "implementation_first"
    elif subtask.scope_role == "validation":
        family = "validation"
        mode = "validation_proof"
        critical_path = "validation_after_write" if implementation_present else "validation_first"
    elif subtask.scope_role == "docs":
        family = "docs"
        mode = "docs_alignment"
        critical_path = "docs_after_write"
    elif subtask.scope_role == "governance":
        family = "governance"
        mode = "governance_closeout"
        critical_path = "governance_local"
    elif subtask.scope_role == "contract":
        family = "architecture" if base_family in {"architecture", "analysis", "review"} else "implementation"
        mode = "architecture_grounding" if family == "architecture" else "write_execution"
        critical_path = "implementation_first" if request.needs_write else "analysis_first"
    else:
        family = base_family or ("diagnosis" if subtask.correctness_critical else "analysis")
        mode = base_mode or ("failure_analysis" if family == "diagnosis" else "read_analysis")
        critical_path = base_critical_path or "analysis_first"

    confidence_score = max(
        base_confidence_score,
        4 if request.evidence_cone_grounded and subtask.execution_group_kind == "primary" else 2 if request.evidence_cone_grounded else 1,
    )
    if subtask.execution_group_kind == "support":
        confidence_score = max(2, confidence_score - 1)
    confidence = _score_level(confidence_score)
    specialized = bool(base_family and (base_family != family or base_mode != mode or base_critical_path != critical_path))
    source = "leaf_specialized" if specialized else "leaf_runtime"
    return {
        "family": family,
        "mode": mode,
        "critical_path": critical_path,
        "confidence": confidence,
        "explicit": base_explicit,
        "source": source,
        "specialized": specialized,
    }


def _score_from_level(value: Any) -> int:
    token = _normalize_token(value)
    if token in {"high", "strong", "grounded", "actionable", "deep_validation"}:
        return 4
    if token in {"medium", "moderate", "balanced", "accuracy_first", "bounded_parallel_candidate"}:
        return 3
    if token in {"low", "guarded_narrowing", "serial_preferred"}:
        return 2
    if token in {"minimal", "serial_guarded"}:
        return 1
    return 0


def _utility_level(score: int) -> str:
    clamped = max(0, min(100, int(score)))
    if clamped >= 75:
        return "high"
    if clamped >= 50:
        return "medium"
    if clamped >= 25:
        return "low"
    return "minimal"


def _merge_context_signals(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged = {str(key): value for key, value in dict(base).items()}
    for raw_key, raw_value in overlay.items():
        key = _normalize_string(raw_key)
        if not key:
            continue
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(raw_value, Mapping):
            merged[key] = _merge_context_signals(dict(existing), dict(raw_value))
        else:
            merged[key] = raw_value
    return merged


def _clamp_confidence(value: int | float) -> int:
    return max(0, min(4, int(round(float(value)))))


def _clamp_bias(value: float) -> float:
    return max(-_BIAS_LIMIT, min(_BIAS_LIMIT, float(value)))


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]


def _new_decision_id() -> str:
    return f"orchestrator-{uuid.uuid4().hex}"


def _new_slice_id(index: int) -> str:
    return f"slice-{index:02d}"


def _now_timestamp() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_timestamp(value: Any) -> dt.datetime | None:
    text = _normalize_string(value)
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
    return parsed


def _timestamp_within_minutes(*, value: Any, window_minutes: int, reference: dt.datetime | None = None) -> bool:
    if window_minutes <= 0:
        return False
    parsed = _parse_timestamp(value)
    if parsed is None:
        return False
    current = reference or dt.datetime.now().astimezone()
    age_seconds = (current - parsed).total_seconds()
    if age_seconds <= 0:
        return True
    return age_seconds <= window_minutes * 60


def _timestamp_after_minutes(*, value: Any, window_minutes: int) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None or window_minutes <= 0:
        return ""
    return (parsed + dt.timedelta(minutes=window_minutes)).isoformat(timespec="seconds")


def _timestamp_is_future(value: Any, *, reference: dt.datetime | None = None) -> bool:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return False
    current = reference or dt.datetime.now().astimezone()
    return parsed >= current


def _normalize_followup_status(value: Any) -> str:
    token = _normalize_token(value)
    if not token:
        return ""
    if token in {"none", "clear", "cleared", "done", "completed", "complete", "closed"}:
        return "not_queued"
    if token in _KNOWN_FOLLOWUP_STATUSES:
        return token
    return ""


def _load_json_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def tuning_state_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / DEFAULT_TUNING_PATH).resolve()


def decision_ledger_dir(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / DEFAULT_DECISION_LEDGER_DIR).resolve()


def decision_ledger_path(*, repo_root: Path, decision_id: str) -> Path:
    token = _normalize_token(decision_id) or "orchestration_decision"
    return (decision_ledger_dir(repo_root=repo_root) / f"{token}.json").resolve()


def _inspection_artifacts_for_decision(*, repo_root: Path, decision_id: str) -> dict[str, Any]:
    path = decision_ledger_path(repo_root=repo_root, decision_id=decision_id)
    return {
        "ledger_path": str(path),
        "ledger_version": _DECISION_LEDGER_VERSION,
        "persisted": path.is_file(),
        "inspection_mode": "close_aggressively_inspect_via_ledger",
    }


def _attach_inspection_artifacts(*, repo_root: Path, decision: OrchestrationDecision) -> OrchestrationDecision:
    decision_id = _normalize_string(decision.decision_id) or _new_decision_id()
    decision.decision_id = decision_id
    artifacts = _inspection_artifacts_for_decision(repo_root=repo_root, decision_id=decision_id)
    existing = dict(decision.inspection_artifacts)
    existing.update(artifacts)
    decision.inspection_artifacts = existing
    return decision


def _finalize_decision(
    *,
    repo_root: Path,
    request: OrchestrationRequest,
    decision: OrchestrationDecision,
) -> OrchestrationDecision:
    final_changed_paths = _request_seed_paths(request)
    decision.odylith_adoption = _decision_odylith_adoption(
        repo_root=repo_root,
        request=request,
        decision=decision,
        final_changed_paths=final_changed_paths,
        changed_path_source="request_seed_paths",
    )
    return _attach_inspection_artifacts(repo_root=repo_root, decision=decision)


def load_tuning_state(*, repo_root: Path) -> TuningState:
    payload = _load_json_mapping(tuning_state_path(repo_root=repo_root))
    state = TuningState()
    if str(payload.get("version", "")).strip() not in {"", _TUNING_VERSION}:
        return state
    for mode in _KNOWN_MODES:
        state.mode_bias[mode] = _clamp_bias(float(dict(payload.get("mode_bias", {})).get(mode, 0.0) or 0.0))
    outcome_payload = payload.get("outcome_counts", {})
    if isinstance(outcome_payload, Mapping):
        for mode in _KNOWN_MODES:
            row = outcome_payload.get(mode, {})
            if isinstance(row, Mapping):
                state.outcome_counts[mode] = {
                    _normalize_token(key): max(0, int(value or 0))
                    for key, value in row.items()
                    if _normalize_token(key)
                }
    family_bias_payload = payload.get("family_mode_bias", {})
    if isinstance(family_bias_payload, Mapping):
        for family, row in family_bias_payload.items():
            family_key = _normalize_token(family)
            if family_key not in state.family_mode_bias or not isinstance(row, Mapping):
                continue
            for mode in _KNOWN_MODES:
                state.family_mode_bias[family_key][mode] = _clamp_bias(float(row.get(mode, 0.0) or 0.0))
    family_counts_payload = payload.get("family_outcome_counts", {})
    if isinstance(family_counts_payload, Mapping):
        for family, family_row in family_counts_payload.items():
            family_key = _normalize_token(family)
            if family_key not in state.family_outcome_counts or not isinstance(family_row, Mapping):
                continue
            for mode in _KNOWN_MODES:
                row = family_row.get(mode, {})
                if isinstance(row, Mapping):
                    state.family_outcome_counts[family_key][mode] = {
                        _normalize_token(key): max(0, int(value or 0))
                        for key, value in row.items()
                        if _normalize_token(key)
                    }
    ledger_payload = payload.get("applied_feedback_keys", {})
    if isinstance(ledger_payload, Mapping):
        state.applied_feedback_keys = {
            _normalize_string(key): _normalize_string(value)
            for key, value in ledger_payload.items()
            if _normalize_string(key) and _normalize_string(value)
        }
    state.updated_at = _normalize_string(payload.get("updated_at", ""))
    return state


def save_tuning_state(*, repo_root: Path, state: TuningState) -> Path:
    path = tuning_state_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def orchestration_request_from_mapping(payload: Mapping[str, Any]) -> OrchestrationRequest:
    prompt = _normalize_string(payload.get("prompt", ""))
    acceptance_criteria = _normalize_list(payload.get("acceptance_criteria", []))
    candidate_paths = _normalize_list(payload.get("candidate_paths", []))
    claimed_paths = _normalize_list(payload.get("claimed_paths", payload.get("claim_paths", [])))
    claim_path = _normalize_string(payload.get("claim_path", ""))
    if claim_path:
        claimed_paths = _dedupe_strings([*claimed_paths, claim_path])
    if not candidate_paths and (prompt or acceptance_criteria):
        candidate_paths = leaf_router.infer_explicit_paths(" ".join([prompt, *acceptance_criteria]).strip())
    if not candidate_paths and claimed_paths:
        candidate_paths = list(claimed_paths)
    context_signals = _extract_context_signals_payload(payload)
    return OrchestrationRequest(
        prompt=prompt,
        acceptance_criteria=acceptance_criteria,
        candidate_paths=candidate_paths,
        workstreams=_normalize_list(payload.get("workstreams", [])),
        components=_normalize_list(payload.get("components", [])),
        validation_commands=_normalize_list(payload.get("validation_commands", [])),
        accuracy_preference=_normalize_token(payload.get("accuracy_preference", "accuracy")) or "accuracy",
        repo_work=_normalize_bool(payload.get("repo_work", True), default=True),
        task_kind=_normalize_token(payload.get("task_kind", "")),
        phase=_normalize_token(payload.get("phase", "")),
        needs_write=_normalize_bool(payload.get("needs_write", False)),
        latency_sensitive=_normalize_bool(payload.get("latency_sensitive", False)),
        correctness_critical=_normalize_bool(payload.get("correctness_critical", False)),
        requires_multi_agent_adjudication=_normalize_bool(payload.get("requires_multi_agent_adjudication", False)),
        evolving_context_required=_normalize_bool(payload.get("evolving_context_required", False)),
        evidence_cone_grounded=_normalize_bool(payload.get("evidence_cone_grounded", False)),
        use_working_tree=_normalize_bool(payload.get("use_working_tree", False)),
        working_tree_scope=_normalize_token(payload.get("working_tree_scope", "repo")) or "repo",
        session_id=_normalize_string(payload.get("session_id", "")),
        claimed_paths=claimed_paths,
        intent=_normalize_token(payload.get("intent", "")),
        odylith_operation=_normalize_odylith_operation(payload.get("odylith_operation", "auto")),
        odylith_auto_ground=_normalize_bool(payload.get("odylith_auto_ground", True), default=True),
        context_signals=_normalize_context_signals(context_signals),
    )


def execution_feedback_from_mapping(payload: Mapping[str, Any]) -> ExecutionFeedback:
    return ExecutionFeedback(
        accepted=_normalize_bool(payload.get("accepted", False)),
        merge_conflicts=max(0, int(payload.get("merge_conflicts", 0) or 0)),
        rescope_required=_normalize_bool(payload.get("rescope_required", False)),
        false_parallelization=_normalize_bool(payload.get("false_parallelization", False)),
        escalated_leaves=max(0, int(payload.get("escalated_leaves", 0) or 0)),
        token_efficient=_normalize_bool(payload.get("token_efficient", False)),
        feedback_id=_normalize_string(payload.get("feedback_id", "")),
        notes=_normalize_string(payload.get("notes", "")),
    )


def _request_validation_errors(request: OrchestrationRequest) -> list[str]:
    errors: list[str] = []
    if not request.prompt:
        errors.append("prompt is required")
    if request.needs_write and not request.candidate_paths:
        errors.append("candidate_paths are required for write orchestration")
    if request.needs_write and not request.acceptance_criteria:
        errors.append("acceptance_criteria are required for write orchestration")
    if request.correctness_critical and request.needs_write and not request.validation_commands:
        errors.append("validation_commands are required for correctness-critical write orchestration")
    return errors


def _implied_write_surface_errors(request: OrchestrationRequest) -> list[str]:
    declared_prefixes = {
        prefix
        for path in request.candidate_paths
        for prefix in leaf_router.surface_prefixes_for_path(path)
        if prefix
    }
    explicit_paths = {
        path
        for path in leaf_router.infer_explicit_paths(" ".join([request.prompt, *request.acceptance_criteria]).strip())
        if path
    }
    missing_paths = sorted(path for path in explicit_paths if path not in set(request.candidate_paths))
    errors: list[str] = []
    if missing_paths:
        errors.append(
            "prompt or acceptance criteria referenced paths outside candidate_paths: " + ", ".join(missing_paths[:4])
        )
    for rule in leaf_router.infer_implied_write_surfaces(request.prompt, request.acceptance_criteria):
        if not (declared_prefixes & set(rule.required_prefixes)):
            errors.append(f"prompt implies writes to {rule.label} but candidate_paths do not declare that surface")
    return errors


def _assessment_validation_errors(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> list[str]:
    errors: list[str] = []
    if assessment.needs_write and not request.candidate_paths:
        errors.append("candidate_paths are required when the prompt implies write orchestration")
    if assessment.needs_write and not request.acceptance_criteria:
        errors.append("acceptance_criteria are required when the prompt implies write orchestration")
    if assessment.correctness_critical and assessment.needs_write and not request.validation_commands:
        errors.append("validation_commands are required when the prompt implies a correctness-critical write slice")
    if assessment.needs_write and request.candidate_paths:
        errors.extend(_implied_write_surface_errors(request))
    return errors


def _ensure_valid_request(request: OrchestrationRequest) -> None:
    errors = _request_validation_errors(request)
    if errors:
        raise leaf_router.RouterInputError(
            code="invalid_orchestration_request",
            message="orchestration request did not satisfy the minimum contract",
            details=errors,
        )


def _base_route_request(request: OrchestrationRequest) -> leaf_router.RouteRequest:
    return leaf_router.route_request_from_mapping(
        {
            "prompt": request.prompt,
            "acceptance_criteria": list(request.acceptance_criteria),
            "allowed_paths": list(request.candidate_paths),
            "workstreams": list(request.workstreams),
            "components": list(request.components),
            "validation_commands": list(request.validation_commands),
            "task_kind": request.task_kind,
            "phase": request.phase,
            "needs_write": request.needs_write,
            "latency_sensitive": request.latency_sensitive,
            "correctness_critical": request.correctness_critical,
            "requires_multi_agent_adjudication": request.requires_multi_agent_adjudication,
            "evolving_context_required": request.evolving_context_required,
            "evidence_cone_grounded": request.evidence_cone_grounded,
            "accuracy_preference": request.accuracy_preference,
            "context_signals": request.context_signals,
        }
    )


def _is_trivial_local_prompt(
    request: OrchestrationRequest,
    *,
    assessment: leaf_router.TaskAssessment | None = None,
) -> bool:
    if not request.repo_work:
        return True
    if request.needs_write or request.candidate_paths or request.workstreams or request.components or request.validation_commands:
        return False
    semantic_signals = (
        assessment.semantic_signals
        if assessment is not None
        else leaf_router.infer_prompt_semantics(request.prompt, request.acceptance_criteria)
    )
    if len(request.prompt.split()) <= 10 and semantic_signals.get("trivial_explanation"):
        return True
    return False


def _path_prefix(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    return parts[0] if parts else ""


def _path_parts(path: str) -> list[str]:
    return [part for part in path.split("/") if part]


def _relative_directory_parts(path: str) -> list[str]:
    parts = _path_parts(path)
    if len(parts) <= 2:
        return []
    return parts[1:-1]


def _shared_relative_directory_depth(paths: Sequence[str]) -> int:
    realized = [_relative_directory_parts(path) for path in paths if path]
    if len(realized) < 2:
        return len(realized[0]) if realized else 0
    depth = 0
    for tokens in zip(*realized, strict=False):
        if len(set(tokens)) != 1:
            break
        depth += 1
    return depth


def _normalized_stem(path: str) -> str:
    token = Path(path).stem.lower()
    for prefix in ("test_", "spec_", "skill_", "app-"):
        if token.startswith(prefix):
            token = token[len(prefix) :]
    return token.replace("-", "_")


def _normalized_repo_path(path: str) -> str:
    return str(path or "").strip().lstrip("./")


def _odylith_path_role(path: str) -> str:
    normalized = _normalized_repo_path(path)
    if not normalized.startswith("odylith/"):
        return ""
    if normalized == "odylith/AGENTS.md":
        return "contract"
    if normalized.startswith(_ODYLITH_GOVERNANCE_PATH_PREFIXES):
        return "governance"
    if normalized.startswith(_ODYLITH_CONTRACT_PATH_PREFIXES):
        return "contract"
    if normalized.startswith("odylith/runtime/") and normalized.endswith(".md"):
        return "contract"
    if normalized.startswith(_ODYLITH_DOC_PATH_PREFIXES) or normalized.endswith(".md"):
        return "docs"
    if normalized.startswith(_ODYLITH_IMPLEMENTATION_PATH_PREFIXES):
        return "implementation"
    return ""


def _is_host_local_governance_path(path: str) -> bool:
    normalized = _normalized_repo_path(path)
    if _odylith_path_role(normalized) == "governance":
        return True
    return any(normalized.startswith(prefix) for prefix in _HOST_LOCAL_GOVERNANCE_PATH_PREFIXES)


def _scope_role(paths: Sequence[str], *, needs_write: bool) -> str:
    prefixes = {_path_prefix(path) for path in paths if _path_prefix(path)}
    odylith_roles = {_odylith_path_role(path) for path in paths if _odylith_path_role(path)}
    if not needs_write:
        return "analysis"
    if paths and all(path.endswith("AGENTS.md") or path == "AGENTS.md" for path in paths if path):
        return "docs"
    if odylith_roles and len(odylith_roles) == 1:
        return next(iter(odylith_roles))
    if prefixes and prefixes.issubset(_TEST_PREFIXES):
        return "validation"
    if prefixes and prefixes.issubset(_DOC_PREFIXES):
        return "docs"
    if prefixes and prefixes.issubset(_GOVERNANCE_PREFIXES):
        return "governance"
    if prefixes and prefixes.issubset(_CONTRACT_PREFIXES):
        return "contract"
    if prefixes and prefixes.issubset(_IMPLEMENTATION_ROLE_PREFIXES):
        return "implementation"
    return "mixed"


def _execution_group_kind(paths: Sequence[str], *, needs_write: bool) -> str:
    if not needs_write:
        return "analysis"
    role = _scope_role(paths, needs_write=needs_write)
    if role in {"implementation", "contract"}:
        return "primary"
    if role in {"validation", "docs", "governance"}:
        return "support"
    return "mixed"


def _support_stem_set(groups: Sequence[Sequence[str]]) -> set[str]:
    stems: set[str] = set()
    for group in groups:
        for path in group:
            stem = _normalized_stem(path)
            if stem:
                stems.add(stem)
    return stems


def _same_prefix_disjoint_primary_exception(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    primary_groups: Sequence[Sequence[str]],
    support_groups: Sequence[Sequence[str]] = (),
) -> bool:
    realized_groups = [list(group) for group in primary_groups if group]
    if len(realized_groups) != 2 or not request.evidence_cone_grounded:
        return False
    if assessment.correctness_critical or assessment.task_family == "critical_change":
        return False
    if assessment.write_scope_clarity < 3 or assessment.acceptance_clarity < 2 or assessment.validation_clarity < 1:
        return False
    first_paths = [group[0] for group in realized_groups if len(group) == 1]
    if len(first_paths) != len(realized_groups):
        return False
    prefixes = {_path_prefix(path) for path in first_paths}
    if len(prefixes) != 1:
        return False
    prefix = next(iter(prefixes), "")
    if prefix not in _SAME_PREFIX_DISJOINT_PREFIXES:
        return False
    if len({Path(path).name for path in first_paths}) != len(first_paths):
        return False
    if _shared_relative_directory_depth(first_paths) == 0:
        return True
    support_stems = _support_stem_set(support_groups)
    matched_support_count = sum(1 for path in first_paths if _normalized_stem(path) in support_stems)
    return matched_support_count >= len(first_paths) and _int_value(assessment.context_signal_summary.get("parallelism_score")) >= 3


def _docs_followup_candidate(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    group: Sequence[str],
    primary_group_count: int,
    total_group_count: int,
) -> bool:
    if not request.needs_write or not request.evidence_cone_grounded:
        return False
    if assessment.correctness_critical or assessment.task_family == "critical_change":
        return False
    if primary_group_count < 1 or total_group_count <= 1:
        return False
    if assessment.write_scope_clarity < 3 or assessment.acceptance_clarity < 2:
        return False
    realized = [path for path in group if path]
    if not realized or len(realized) > 2:
        return False
    return _scope_role(realized, needs_write=True) == "docs"


def _group_sort_key(paths: Sequence[str], *, needs_write: bool) -> tuple[int, str, str]:
    role = _scope_role(paths, needs_write=needs_write)
    role_priority = {
        "implementation": 0,
        "contract": 1,
        "validation": 2,
        "docs": 3,
        "governance": 4,
        "analysis": 0,
        "mixed": 5,
    }
    first_path = min((path for path in paths if path), default="")
    return (
        role_priority.get(role, 9),
        _path_prefix(first_path),
        _normalized_stem(first_path),
    )


def _group_paths(paths: Sequence[str], *, needs_write: bool) -> list[list[str]]:
    if not paths:
        return [[]]
    groups: dict[str, list[str]] = {}
    for path in paths:
        prefix = _path_prefix(path)
        if needs_write:
            key = f"{prefix}:{_normalized_stem(path)}"
        else:
            key = prefix or path
        groups.setdefault(key, []).append(path)
    ordered = [sorted(paths_for_key) for paths_for_key in groups.values()]
    return sorted(ordered, key=lambda group: _group_sort_key(group, needs_write=needs_write))


def _split_main_thread_followup_groups(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    groups: Sequence[Sequence[str]],
) -> tuple[list[list[str]], list[FollowupGroup], list[str]]:
    if not request.needs_write:
        return [list(group) for group in groups if group], [], []
    realized_groups = [list(group) for group in groups if group]
    if len(realized_groups) <= 1:
        return realized_groups, [], []
    delegate_groups: list[list[str]] = []
    followup_groups: list[FollowupGroup] = []
    notes: list[str] = []
    primary_group_count = sum(
        1 for group in realized_groups if _scope_role(group, needs_write=True) in {"implementation", "contract"}
    )
    total_group_count = len(realized_groups)
    for group in realized_groups:
        role = _scope_role(group, needs_write=True)
        governance_delegate_candidate = bool(
            role == "governance"
            and request.evidence_cone_grounded
            and assessment.delegation_readiness >= 3
            and assessment.earned_depth >= 3
            and assessment.write_scope_clarity >= 3
            and assessment.acceptance_clarity >= 2
            and len(group) <= 2
            and _int_value(assessment.context_signal_summary.get("merge_burden_score", 0)) <= 2
            and bool(assessment.context_signal_summary.get("route_ready"))
            and bool(assessment.context_signal_summary.get("native_spawn_ready"))
        )
        if role == "governance" and all(
            _is_host_local_governance_path(path) for path in group
        ) and not governance_delegate_candidate:
            followup_groups.append(
                FollowupGroup(
                    paths=list(group),
                    scope_role="governance",
                    why_local=(
                        "Governance closeout remains main-thread owned so lifecycle truth stays explicit "
                        "without polluting bounded worker routing."
                    ),
                )
            )
            continue
        if _docs_followup_candidate(
            request,
            assessment,
            group=group,
            primary_group_count=primary_group_count,
            total_group_count=total_group_count,
        ):
            followup_groups.append(
                FollowupGroup(
                    paths=list(group),
                    scope_role="docs",
                    why_local=(
                        "A small docs-alignment support slice behind an already-grounded implementation leaf is "
                        "cheaper and clearer as a main-thread follow-up than as a separate spawned support worker."
                    ),
                )
            )
            notes.append("small docs alignment support stayed local because its spawn value was lower than its merge overhead")
            continue
        delegate_groups.append(group)
    return delegate_groups, followup_groups, notes


def _parallel_safety(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> tuple[ParallelSafetyClass, list[str], list[list[str]]]:
    groups = _group_paths(request.candidate_paths, needs_write=request.needs_write)
    return _parallel_safety_for_groups(request, assessment, groups=groups)


def _parallel_safety_for_groups(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    groups: Sequence[Sequence[str]],
) -> tuple[ParallelSafetyClass, list[str], list[list[str]]]:
    realized_groups = [list(group) for group in groups if group]
    scoped_paths = [path for group in realized_groups for path in group]
    reasons: list[str] = []
    if assessment.hard_gate_hits:
        return ParallelSafetyClass.LOCAL_ONLY, [*assessment.hard_gate_hits], realized_groups
    if _is_trivial_local_prompt(request, assessment=assessment):
        return ParallelSafetyClass.LOCAL_ONLY, ["trivial-direct-answer"], realized_groups
    if not request.needs_write:
        if assessment.semantic_signals.get("synthesis_required"):
            reasons.append("read-only slice requires a synthesized conclusion and stays serial")
            return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
        if len(realized_groups) >= 2 and len(realized_groups) <= 4:
            return ParallelSafetyClass.READ_ONLY_SAFE, reasons, realized_groups
        if len(realized_groups) > 4:
            reasons.append("read-only fan-out exceeded conservative cap")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    roles_by_group = [_scope_role(group, needs_write=True) for group in realized_groups]
    primary_groups = [
        group for group, role in zip(realized_groups, roles_by_group) if role in {"implementation", "contract"}
    ]
    support_groups = [
        group for group, role in zip(realized_groups, roles_by_group) if role in {"validation", "docs"}
    ]
    other_groups = [
        group
        for group, role in zip(realized_groups, roles_by_group)
        if role not in {"implementation", "contract", "validation", "docs"}
    ]
    primary_paths = [path for group in primary_groups for path in group]
    prefixes = {_path_prefix(path) for path in primary_paths}
    if other_groups:
        reasons.append("write slice includes mixed, contract, or governed surfaces that stay ordered")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    if not prefixes or not prefixes.issubset(_WRITE_PARALLEL_PREFIXES):
        reasons.append("write slice spans ownership domains without safe parallel policy")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    if len(primary_groups) < 2:
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    if len(primary_groups) > 3 or len(support_groups) > 2:
        reasons.append("write fan-out exceeded conservative cap")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    if assessment.correctness_critical or assessment.task_family == "critical_change":
        reasons.append("critical writes stay serial or local")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    if assessment.write_scope_clarity < 3 or assessment.acceptance_clarity < 2 or assessment.validation_clarity < 1:
        reasons.append("write slice lacks the owned-path or validation clarity required for parallelism")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    if support_groups:
        reasons.append("support groups will stay ordered behind the primary implementation leaves")
    if len(prefixes) == 1:
        if _same_prefix_disjoint_primary_exception(
            request,
            assessment,
            primary_groups=primary_groups,
            support_groups=support_groups,
        ):
            reasons.append("same-prefix disjoint implementation leaves qualified for the narrow grounded exception")
            return ParallelSafetyClass.DISJOINT_WRITE_SAFE, reasons, realized_groups
        reasons.append("same-prefix code writes stay serial without explicit disjoint ownership metadata")
        return ParallelSafetyClass.SERIAL_ORDERED, reasons, realized_groups
    return ParallelSafetyClass.DISJOINT_WRITE_SAFE, reasons, realized_groups


def _tuning_bias(state: TuningState, *, mode: str, task_family: str) -> float:
    return float(state.mode_bias.get(mode, 0.0) or 0.0) + float(
        state.family_mode_bias.get(task_family, {}).get(mode, 0.0) or 0.0
    )


def _count_feedback_labels(counts: Mapping[str, int], labels: Sequence[str]) -> int:
    return sum(int(counts.get(label, 0) or 0) for label in labels)


def _combine_feedback_counts(*rows: Mapping[str, int]) -> dict[str, int]:
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


def _mode_reliability_summary(state: TuningState, *, mode: str, task_family: str) -> dict[str, Any]:
    global_counts = dict(state.outcome_counts.get(mode, {}))
    family_counts = dict(state.family_outcome_counts.get(task_family, {}).get(mode, {}))
    family_total = _count_feedback_labels(
        family_counts,
        ("accepted", "merge_conflicts", "rescope_required", "false_parallelization", "escalated", "token_efficient"),
    )
    counts = family_counts if family_total >= 2 else _combine_feedback_counts(global_counts, family_counts)
    accepted = int(counts.get("accepted", 0) or 0)
    merge_conflicts = int(counts.get("merge_conflicts", 0) or 0)
    rescope_required = int(counts.get("rescope_required", 0) or 0)
    false_parallelization = int(counts.get("false_parallelization", 0) or 0)
    escalated = int(counts.get("escalated", 0) or 0)
    token_efficient = int(counts.get("token_efficient", 0) or 0)
    failures = merge_conflicts + rescope_required + false_parallelization + escalated
    total = accepted + failures
    if total < 2:
        posture = "unknown"
    elif failures == 0 and accepted >= 3:
        posture = "strong"
    elif false_parallelization > 0 or rescope_required > 0 or merge_conflicts >= 2 or failures > accepted:
        posture = "weak"
    else:
        posture = "mixed"
    return {
        "source": "family" if family_total >= 2 else "combined",
        "posture": posture,
        "accepted": accepted,
        "merge_conflicts": merge_conflicts,
        "rescope_required": rescope_required,
        "false_parallelization": false_parallelization,
        "escalated": escalated,
        "token_efficient": token_efficient,
        "total": total,
    }


def _critical_path_posture(request: OrchestrationRequest, *, groups: Sequence[Sequence[str]]) -> str:
    realized_groups = [list(group) for group in groups if group]
    roles = [_scope_role(group, needs_write=request.needs_write) for group in realized_groups]
    if not request.needs_write:
        return "analysis_first"
    if any(role in {"implementation", "contract"} for role in roles):
        if any(role in {"validation", "docs"} for role in roles):
            return "implementation_first"
        return "implementation_only"
    if roles and all(role == "validation" for role in roles):
        return "validation_first"
    if roles and all(role == "docs" for role in roles):
        return "docs_first"
    return "serial_guarded"


def _merge_burden_estimate(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    groups: Sequence[Sequence[str]],
) -> int:
    realized_groups = [list(group) for group in groups if group]
    roles = [_scope_role(group, needs_write=request.needs_write) for group in realized_groups]
    burden = 1 if len(realized_groups) > 1 else 0
    if any(role in {"validation", "docs"} for role in roles):
        burden += 1
    if assessment.correctness_critical or assessment.task_family == "critical_change":
        burden += 1
    if len(realized_groups) > 2:
        burden += 1
    return min(4, burden)


def _adaptive_batch_mode(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    safety: ParallelSafetyClass,
    groups: Sequence[Sequence[str]],
    tuning: TuningState,
) -> tuple[OrchestrationMode, list[str]]:
    return subagent_orchestrator_runtime_signals._adaptive_batch_mode(
        request,
        assessment,
        safety=safety,
        groups=groups,
        tuning=tuning,
    )


def _can_decompose_coordination_heavy_write(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> bool:
    if not request.needs_write or not request.evidence_cone_grounded:
        return False
    if len(request.candidate_paths) < 2:
        return False
    if assessment.write_scope_clarity < 3 or assessment.acceptance_clarity < 2 or assessment.validation_clarity < 1:
        return False
    context_summary = dict(assessment.context_signal_summary or {})
    odylith_signal_present = any(
        key in context_summary
        for key in (
            "route_ready",
            "odylith_execution_route_ready",
            "narrowing_required",
            "odylith_execution_narrowing_required",
            "native_spawn_ready",
            "odylith_execution_selection_mode",
        )
    )
    odylith_route_ready = bool(context_summary.get("route_ready") or context_summary.get("odylith_execution_route_ready"))
    odylith_narrowing_required = bool(
        context_summary.get("narrowing_required") or context_summary.get("odylith_execution_narrowing_required")
    )
    odylith_native_spawn_ready = bool(context_summary.get("native_spawn_ready"))
    if odylith_signal_present and (odylith_narrowing_required or not odylith_route_ready or not odylith_native_spawn_ready):
        return False
    groups = _group_paths(request.candidate_paths, needs_write=True)
    return len(groups) >= 2


def _should_keep_local(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> tuple[list[str], list[str]]:
    reasons = list(assessment.hard_gate_hits)
    notes: list[str] = []
    architecture_policy = _architecture_policy_context(request)
    context_summary = dict(assessment.context_signal_summary or {})
    odylith_confidence = _clamp_confidence(context_summary.get("odylith_execution_confidence_score", 0) or 0)
    odylith_profile = _normalize_token(context_summary.get("odylith_execution_profile", ""))
    odylith_delegate_preference = _normalize_token(context_summary.get("odylith_execution_delegate_preference", ""))
    odylith_selection_mode = _normalize_token(context_summary.get("odylith_execution_selection_mode", ""))
    odylith_route_ready = bool(context_summary.get("route_ready") or context_summary.get("odylith_execution_route_ready"))
    odylith_narrowing_required = bool(
        context_summary.get("narrowing_required") or context_summary.get("odylith_execution_narrowing_required")
    )
    odylith_native_spawn_ready = bool(context_summary.get("native_spawn_ready"))
    odylith_signal_present = any(
        key in context_summary
        for key in (
            "route_ready",
            "odylith_execution_route_ready",
            "narrowing_required",
            "odylith_execution_narrowing_required",
            "native_spawn_ready",
            "odylith_execution_delegate_preference",
            "odylith_execution_selection_mode",
            "odylith_execution_profile",
        )
    )
    odylith_spawn_worthiness = max(
        _int_value(context_summary.get("spawn_worthiness_score", 0)),
        _int_value(context_summary.get("odylith_execution_spawn_worthiness", 0)),
    )
    if (
        odylith_signal_present
        and (odylith_profile == leaf_router.RouterProfile.MAIN_THREAD.value or odylith_delegate_preference == "hold_local")
        and (
            odylith_narrowing_required
            or not odylith_route_ready
            or not odylith_native_spawn_ready
            or odylith_spawn_worthiness <= 1
            or odylith_selection_mode in {"narrow_first", "guarded_narrowing"}
        )
    ):
        reasons.append("odylith-local-narrowing")
        notes.append(
            "The slice still needs local narrowing or local coordination before any bounded fan-out."
        )
    if (
        odylith_signal_present
        and odylith_narrowing_required
        and not odylith_route_ready
        and "odylith-local-narrowing" not in reasons
    ):
        reasons.append("odylith-local-narrowing")
        notes.append(
            "The slice is still in a narrowing-first posture, so delegation would add cost before the evidence is tight enough."
        )
    if (
        odylith_signal_present
        and not request.needs_write
        and not odylith_route_ready
        and not odylith_native_spawn_ready
        and "odylith-read-only-local-narrowing" not in reasons
    ):
        reasons.append("odylith-read-only-local-narrowing")
        notes.append(
            "The read-only slice stays local until the evidence cone narrows enough to delegate safely."
        )
    if architecture_policy["active"] and (
        architecture_policy["full_scan_recommended"]
        or architecture_policy["mode"] == "local_only"
        or (
            architecture_policy["risk_tier"] == "high"
            and architecture_policy["confidence_tier"] == "low"
        )
    ):
        reasons.append("architecture-local-grounding")
        notes.append(
            "Architecture dossier coverage is too weak or too risky for delegation; keep the slice local until the authority graph is grounded enough to trust."
        )
    if _can_decompose_coordination_heavy_write(request, assessment):
        relaxed = [reason for reason in reasons if reason in _DECOMPOSABLE_COORDINATION_GATES]
        if relaxed:
            reasons = [reason for reason in reasons if reason not in _DECOMPOSABLE_COORDINATION_GATES]
            notes.append(
                "The base prompt looked coordination-heavy, but grounded explicit owned paths let the orchestrator decompose it into bounded ordered leaves."
            )
    if _is_trivial_local_prompt(request, assessment=assessment):
        reasons.append("trivial-direct-answer")
    if not request.repo_work:
        reasons.append("non-repo-work-prompt")
    return reasons, _sanitize_user_facing_lines(notes)


def _slice_prompt(
    request: OrchestrationRequest,
    *,
    paths: Sequence[str],
    mode: OrchestrationMode,
    needs_write: bool,
    role: str,
    include_coordination: bool,
) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_prompt(
        request,
        paths=paths,
        mode=mode,
        needs_write=needs_write,
        role=role,
        include_coordination=include_coordination,
    )


def _slice_deliverables(
    request: OrchestrationRequest,
    *,
    paths: Sequence[str],
    needs_write: bool,
    role: str,
) -> list[str]:
    return subagent_orchestrator_subtasks_runtime._slice_deliverables(
        request,
        paths=paths,
        needs_write=needs_write,
        role=role,
    )


def _relevant_acceptance_criteria(
    criteria: Sequence[str],
    *,
    paths: Sequence[str],
    all_paths: Sequence[str] | None = None,
) -> list[str]:
    return subagent_orchestrator_subtasks_runtime._relevant_acceptance_criteria(
        criteria,
        paths=paths,
        all_paths=all_paths,
    )


def _slice_owner(*, paths: Sequence[str], needs_write: bool) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_owner(paths=paths, needs_write=needs_write)


def _slice_goal(
    request: OrchestrationRequest,
    *,
    paths: Sequence[str],
    role: str,
    needs_write: bool,
) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_goal(
        request,
        paths=paths,
        role=role,
        needs_write=needs_write,
    )


def _slice_expected_output(deliverables: Sequence[str]) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_expected_output(deliverables)


def _termination_condition_for_leaf(
    *,
    subtask: SubtaskSlice,
    decision: leaf_router.RoutingDecision,
) -> str:
    return subagent_orchestrator_subtasks_runtime._termination_condition_for_leaf(
        subtask=subtask,
        decision=decision,
    )


def _prompt_contract_lines(subtask: SubtaskSlice) -> list[str]:
    return subagent_orchestrator_subtasks_runtime._prompt_contract_lines(subtask)


def _spawn_task_message(subtask: SubtaskSlice, *, task_prompt: str) -> str:
    return subagent_orchestrator_subtasks_runtime._spawn_task_message(subtask, task_prompt=task_prompt)


def _completion_closeout_overrides(subtasks: Sequence[SubtaskSlice]) -> dict[str, Any]:
    return subagent_orchestrator_subtasks_runtime._completion_closeout_overrides(subtasks)


def _slice_task_kind(request: OrchestrationRequest, *, role: str) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_task_kind(request, role=role)


def _slice_phase(request: OrchestrationRequest, *, role: str) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_phase(request, role=role)


def _slice_correctness_critical(request: OrchestrationRequest, *, role: str) -> bool:
    return subagent_orchestrator_subtasks_runtime._slice_correctness_critical(request, role=role)


def _slice_latency_sensitive(request: OrchestrationRequest, *, role: str) -> bool:
    return subagent_orchestrator_subtasks_runtime._slice_latency_sensitive(request, role=role)


def _slice_accuracy_preference(request: OrchestrationRequest, *, role: str) -> str:
    return subagent_orchestrator_subtasks_runtime._slice_accuracy_preference(request, role=role)


def _slice_validation_commands(request: OrchestrationRequest, *, role: str) -> list[str]:
    return subagent_orchestrator_subtasks_runtime._slice_validation_commands(request, role=role)


def _build_subtasks(
    request: OrchestrationRequest,
    *,
    mode: OrchestrationMode,
    groups: Sequence[Sequence[str]],
) -> list[SubtaskSlice]:
    return subagent_orchestrator_subtasks_runtime._build_subtasks(
        request,
        mode=mode,
        groups=groups,
    )


def _same_prefix_exception_active(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    subtask: SubtaskSlice,
    mode: OrchestrationMode,
    all_subtasks: Sequence[SubtaskSlice],
) -> bool:
    if mode is not OrchestrationMode.PARALLEL_BATCH or subtask.execution_group_kind != "primary":
        return False
    primary_groups = [planned.owned_paths or planned.read_paths for planned in all_subtasks if planned.execution_group_kind == "primary"]
    support_groups = [planned.owned_paths or planned.read_paths for planned in all_subtasks if planned.execution_group_kind == "support"]
    return _same_prefix_disjoint_primary_exception(
        request,
        assessment,
        primary_groups=primary_groups,
        support_groups=support_groups,
    )


def _spawn_worthiness_score(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    subtask: SubtaskSlice,
    mode: OrchestrationMode,
    primary_count: int,
    merge_burden: int,
    same_prefix_disjoint_exception: bool,
) -> int:
    scope_size = len(subtask.owned_paths or subtask.read_paths)
    score = 0
    if not request.needs_write and subtask.execution_group_kind == "analysis":
        score += 2
    if request.evidence_cone_grounded:
        score += 1
    if subtask.execution_group_kind == "primary":
        score += 2
    if subtask.scope_role in {"implementation", "contract"}:
        score += 1
    if subtask.scope_role == "validation":
        score += 2 if (subtask.validation_commands or primary_count >= 2) else 1
    if scope_size >= 2:
        score += 1
    if subtask.correctness_critical or assessment.task_family == "critical_change":
        score += 1
    if subtask.execution_group_kind == "support" and subtask.scope_role != "validation":
        score -= 1
    if subtask.scope_role == "docs":
        score -= 1
    if subtask.scope_role == "governance":
        score -= 2
    if len(subtask.dependency_ids) >= 1 and subtask.scope_role != "validation":
        score -= 1
    if len(subtask.dependency_ids) >= 2 and subtask.scope_role != "validation":
        score -= 1
    if merge_burden >= 3 and subtask.scope_role != "validation":
        score -= 1
    if same_prefix_disjoint_exception:
        score -= 1
    if mode is OrchestrationMode.SERIAL_BATCH and subtask.execution_group_kind == "support":
        score -= 1
    return _clamp_confidence(score)


def _routing_confidence_for_subtask(
    request: OrchestrationRequest,
    *,
    subtask: SubtaskSlice,
    merge_burden: int,
    spawn_worthiness: int,
    same_prefix_disjoint_exception: bool,
) -> int:
    scope_size = len(subtask.owned_paths or subtask.read_paths)
    score = 0
    if not request.needs_write:
        score += 1
    if request.evidence_cone_grounded:
        score += 2
    if scope_size >= 1:
        score += 1
    if subtask.execution_group_kind == "primary":
        score += 1
    if subtask.execution_group_kind == "analysis":
        score += 1
    if subtask.scope_role == "validation" and subtask.validation_commands:
        score += 2
    if spawn_worthiness >= 3:
        score += 1
    if len(subtask.dependency_ids) >= 1:
        score -= 1
    if len(subtask.dependency_ids) >= 2:
        score -= 1
    if subtask.execution_group_kind == "support" and subtask.scope_role != "validation":
        score -= 1
    if merge_burden >= 3:
        score -= 1
    if same_prefix_disjoint_exception:
        score -= 1
    return _clamp_confidence(score)


def _subtask_context_signals(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    subtask: SubtaskSlice,
    mode: OrchestrationMode,
    all_subtasks: Sequence[SubtaskSlice],
) -> dict[str, Any]:
    return subagent_orchestrator_runtime_signals._subtask_context_signals(
        request,
        assessment,
        subtask=subtask,
        mode=mode,
        all_subtasks=all_subtasks,
    )


def _route_leaf(
    *,
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    subtask: SubtaskSlice,
    all_subtasks: Sequence[SubtaskSlice],
    mode: OrchestrationMode,
    repo_root: Path,
) -> leaf_router.RoutingDecision:
    routed_request = leaf_router.route_request_from_mapping(
        {
            "prompt": subtask.route_prompt or subtask.prompt,
            "acceptance_criteria": list(subtask.deliverables or request.acceptance_criteria),
            "allowed_paths": list(subtask.owned_paths or subtask.read_paths),
            "workstreams": list(request.workstreams),
            "components": list(request.components),
            "validation_commands": list(subtask.validation_commands),
            "task_kind": subtask.task_kind,
            "phase": subtask.phase,
            "needs_write": request.needs_write,
            "latency_sensitive": subtask.latency_sensitive,
            "correctness_critical": subtask.correctness_critical,
            "requires_multi_agent_adjudication": request.requires_multi_agent_adjudication,
            "evolving_context_required": request.evolving_context_required,
            "evidence_cone_grounded": request.evidence_cone_grounded,
            "accuracy_preference": subtask.accuracy_preference,
            "context_signals": _subtask_context_signals(
                request,
                assessment,
                subtask=subtask,
                mode=mode,
                all_subtasks=all_subtasks,
            ),
        }
    )
    return leaf_router.route_request(routed_request, repo_root=repo_root)


def _leaf_to_subtask(subtask: SubtaskSlice, decision: leaf_router.RoutingDecision) -> SubtaskSlice:
    subtask.route_profile = decision.profile
    subtask.route_model = decision.model
    subtask.route_reasoning_effort = decision.reasoning_effort
    subtask.route_task_class_profile = decision.task_class_profile
    subtask.route_task_class_model = decision.task_class_model
    subtask.route_task_class_reasoning_effort = decision.task_class_reasoning_effort
    subtask.route_task_class_policy_lines = list(decision.task_class_policy_lines)
    subtask.route_agent_role = decision.agent_role
    subtask.route_close_after_result = decision.close_after_result
    subtask.route_idle_timeout_minutes = decision.idle_timeout_minutes
    subtask.route_idle_timeout_action = decision.idle_timeout_action
    subtask.route_idle_timeout_escalation = decision.idle_timeout_escalation
    subtask.route_reuse_window = decision.reuse_window
    subtask.route_prequeue_same_scope_reuse_claim_minutes = decision.prequeue_same_scope_reuse_claim_minutes
    subtask.route_waiting_policy = decision.waiting_policy
    subtask.route_termination_expectation = decision.termination_expectation
    subtask.route_spawn_contract_lines = list(decision.spawn_contract_lines)
    subtask.route_spawn_overrides = dict(decision.spawn_overrides)
    subtask.route_spawn_agent_overrides = dict(decision.spawn_agent_overrides)
    subtask.route_close_agent_overrides = dict(decision.close_agent_overrides)
    subtask.route_host_tool_contract = dict(decision.host_tool_contract)
    subtask.route_runtime_banner_lines = list(decision.runtime_banner_lines)
    subtask.route_task_family = decision.task_family
    subtask.route_confidence = decision.routing_confidence
    subtask.route_manual_review_recommended = decision.manual_review_recommended
    subtask.route_why = decision.why
    subtask.route_explanation_lines = list(decision.explanation_lines)
    subtask.route_odylith_execution_profile = dict(decision.odylith_execution_profile)
    subtask.termination_condition = _termination_condition_for_leaf(subtask=subtask, decision=decision)
    subtask.prompt_contract_lines = _prompt_contract_lines(subtask)
    task_prompt = subtask.prompt
    subtask.spawn_task_message = _spawn_task_message(subtask, task_prompt=task_prompt)
    subtask.prompt = subtask.spawn_task_message
    subtask.route_native_spawn_payload = (
        {
            **dict(decision.native_spawn_payload),
            "message": subtask.spawn_task_message,
        }
        if decision.native_spawn_payload
        else {}
    )
    return subtask


def _decision_confidence(
    *,
    assessment: leaf_router.TaskAssessment,
    mode: OrchestrationMode,
    subtasks: Sequence[SubtaskSlice],
) -> int:
    confidence = assessment.base_confidence
    if mode is OrchestrationMode.PARALLEL_BATCH:
        confidence -= 1
    if mode is OrchestrationMode.SINGLE_LEAF:
        confidence += 1
    if subtasks:
        confidence = min(confidence, min(task.route_confidence for task in subtasks if task.route_confidence))
    return _clamp_confidence(confidence)


def _new_followup_id(index: int) -> str:
    return f"followup-{index:02d}"


def _build_main_thread_followups(
    request: OrchestrationRequest,
    *,
    followup_groups: Sequence[FollowupGroup],
    dependency_ids: Sequence[str],
) -> list[MainThreadFollowup]:
    followups: list[MainThreadFollowup] = []
    for index, followup in enumerate(followup_groups, start=1):
        realized_paths = list(followup.paths)
        scope_role = followup.scope_role or "governance"
        followups.append(
            MainThreadFollowup(
                id=_new_followup_id(index),
                scope_role=scope_role,
                paths=realized_paths,
                dependency_ids=list(dependency_ids),
                owner="main_thread",
                goal=(
                    f"Align the {scope_role} follow-up in {', '.join(realized_paths)} after delegated results are integrated."
                    if scope_role != "governance"
                    else f"Refresh the governed backlog, plan, or traceability surfaces in {', '.join(realized_paths)} "
                    "after delegated implementation results are integrated."
                ),
                deliverables=_slice_deliverables(
                    request,
                    paths=realized_paths,
                    needs_write=True,
                    role=scope_role,
                ),
                why_local=followup.why_local
                or (
                    "Governance closeout remains main-thread owned so lifecycle truth and traceability stay explicit "
                    "without poisoning bounded leaf routing."
                ),
            )
        )
    return followups


def _effective_request(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
) -> OrchestrationRequest:
    if (
        request.needs_write == assessment.needs_write
        and request.correctness_critical == assessment.correctness_critical
        and request.task_kind
        and request.phase
    ):
        return request
    return OrchestrationRequest(
        prompt=request.prompt,
        acceptance_criteria=list(request.acceptance_criteria),
        candidate_paths=list(request.candidate_paths),
        workstreams=list(request.workstreams),
        components=list(request.components),
        validation_commands=list(request.validation_commands),
        accuracy_preference=request.accuracy_preference,
        repo_work=request.repo_work,
        task_kind=request.task_kind or assessment.task_kind,
        phase=request.phase or assessment.phase,
        needs_write=request.needs_write or assessment.needs_write,
        latency_sensitive=request.latency_sensitive,
        correctness_critical=request.correctness_critical or assessment.correctness_critical,
        requires_multi_agent_adjudication=request.requires_multi_agent_adjudication,
        evolving_context_required=request.evolving_context_required,
        evidence_cone_grounded=request.evidence_cone_grounded,
        use_working_tree=request.use_working_tree,
        working_tree_scope=request.working_tree_scope,
        session_id=request.session_id,
        claimed_paths=list(request.claimed_paths),
        intent=request.intent,
        odylith_operation=request.odylith_operation,
        odylith_auto_ground=request.odylith_auto_ground,
        context_signals=dict(request.context_signals),
    )

subagent_orchestrator_odylith_runtime.bind(sys.modules[__name__])


def orchestrate_prompt(
    request: OrchestrationRequest,
    *,
    repo_root: Path,
) -> OrchestrationDecision:
    _ensure_valid_request(request)
    base_route_request = _base_route_request(request)
    assessment = leaf_router.assess_request(base_route_request)
    request = _auto_ground_request_with_odylith(request, repo_root=repo_root, assessment=assessment)
    if request.context_signals:
        base_route_request = _base_route_request(request)
        assessment = leaf_router.assess_request(base_route_request)
    assessment_errors = _assessment_validation_errors(request, assessment)
    if assessment_errors:
        raise leaf_router.RouterInputError(
            code="invalid_orchestration_request",
            message="orchestration request did not satisfy the minimum contract after prompt assessment",
            details=assessment_errors,
        )
    request = _effective_request(request, assessment)
    local_reasons, decomposition_notes = _should_keep_local(request, assessment)
    if local_reasons:
        execution_contract_notes = ["No delegated leaf is allowed for this prompt; keep execution in the main thread."]
        if "consumer-odylith-diagnosis-and-handoff-only" in local_reasons:
            execution_contract_notes.append(
                "Consumer Odylith issues stay diagnosis-and-handoff only: capture exact failing paths, commands, and symptoms for the maintainer instead of mutating `odylith/` or running autonomous repair, upgrade, sync, or dashboard-refresh flows."
            )
        if "evolving-context-required" in local_reasons:
            execution_contract_notes.append(
                "If the evidence cone becomes grounded locally, rerun orchestration with `evidence_cone_grounded=true` instead of forcing delegation against an evolving context."
            )
        return _finalize_decision(
            repo_root=repo_root,
            request=request,
            decision=OrchestrationDecision(
                mode=OrchestrationMode.LOCAL_ONLY.value,
                decision_id=_new_decision_id(),
                delegate=False,
                parallel_safety=ParallelSafetyClass.LOCAL_ONLY.value,
                task_family=assessment.task_family,
                confidence=assessment.base_confidence,
                rationale=f"kept local because {', '.join(local_reasons)}",
                refusal_stage="prompt_local_gate",
                manual_review_recommended=True,
                merge_owner="main_thread",
                merge_barrier_notes=["Ground the evidence cone locally before any bounded delegation retry."],
                execution_contract_notes=execution_contract_notes,
                completion_closeout_overrides={},
                local_only_reasons=local_reasons,
                budget_notes=["Automatic orchestration is skipped for trivial or unsafe slices.", *decomposition_notes],
                request=request.as_dict(),
            ),
        )

    tuning = load_tuning_state(repo_root=repo_root)
    architecture_policy = _architecture_policy_context(request)
    initial_groups = _group_paths(request.candidate_paths, needs_write=request.needs_write)
    groups, main_thread_followup_groups, followup_notes = _split_main_thread_followup_groups(
        request,
        assessment,
        groups=initial_groups,
    )
    if not groups and main_thread_followup_groups:
        main_thread_followups = _build_main_thread_followups(
            request,
            followup_groups=main_thread_followup_groups,
            dependency_ids=[],
        )
        return _finalize_decision(
            repo_root=repo_root,
            request=request,
            decision=OrchestrationDecision(
                mode=OrchestrationMode.LOCAL_ONLY.value,
                decision_id=_new_decision_id(),
                delegate=False,
                parallel_safety=ParallelSafetyClass.LOCAL_ONLY.value,
                task_family=assessment.task_family,
                confidence=assessment.base_confidence,
                rationale="kept local because the remaining owned scope is explicit main-thread follow-up work",
                refusal_stage="host_local_followups_only",
                manual_review_recommended=True,
                merge_owner="main_thread",
                merge_barrier_notes=["Explicit local follow-up work remains main-thread owned for this slice."],
                execution_contract_notes=["No delegated leaf is required because the remaining work is intentionally retained as main-thread follow-up scope."],
                completion_closeout_overrides={},
                local_only_reasons=["main-thread-followup-only"],
                budget_notes=["Follow-up-only scope stayed local by design.", *followup_notes],
                main_thread_followups=main_thread_followups,
                request=request.as_dict(),
            ),
        )
    safety, safety_reasons, groups = _parallel_safety_for_groups(request, assessment, groups=groups or initial_groups)
    mode = OrchestrationMode.SINGLE_LEAF
    budget_notes: list[str] = []
    if safety is ParallelSafetyClass.READ_ONLY_SAFE:
        mode, adaptive_notes = _adaptive_batch_mode(
            request,
            assessment,
            safety=safety,
            groups=groups,
            tuning=tuning,
        )
        budget_notes.extend(adaptive_notes)
    elif safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE:
        mode, adaptive_notes = _adaptive_batch_mode(
            request,
            assessment,
            safety=safety,
            groups=groups,
            tuning=tuning,
        )
        budget_notes.extend(adaptive_notes)
    elif len(groups) > 1:
        mode = OrchestrationMode.SERIAL_BATCH
    if architecture_policy["active"] and architecture_policy["fanout"] in {"no_fanout", "bounded_single_leaf_only"}:
        if mode is not OrchestrationMode.SINGLE_LEAF:
            mode = OrchestrationMode.SINGLE_LEAF
            budget_notes.append(
                "architecture dossier restricted fan-out to one bounded leaf because the slice is high-risk or structurally coupled"
            )
    elif architecture_policy["active"] and architecture_policy["mode"] == "bounded_analysis" and mode is OrchestrationMode.PARALLEL_BATCH:
        mode = OrchestrationMode.SINGLE_LEAF
        budget_notes.append(
            "architecture dossier favored a lighter single-leaf analysis path over multi-leaf fan-out because coverage is already strong"
        )
    delegate_paths = [path for group in groups for path in group]
    subtasks = _build_subtasks(
        request,
        mode=mode,
        groups=groups if mode is not OrchestrationMode.SINGLE_LEAF else [delegate_paths or request.candidate_paths],
    )
    if mode is OrchestrationMode.PARALLEL_BATCH:
        budget_notes.append("parallel fan-out stays conservative and requires a main-thread merge barrier")
    if request.needs_write and assessment.feature_implementation:
        budget_notes.append(
            "feature implementation remains accuracy-first and will bias leaves toward stronger coding-optimized or GPT-5.4 tiers"
        )
    budget_notes.extend(decomposition_notes)
    budget_notes.extend(followup_notes)
    if main_thread_followup_groups:
        budget_notes.append("main-thread follow-ups stay explicit so delegated worker routing remains bounded and high-value")

    local_fallback_reasons: list[str] = []
    routed_subtasks: list[SubtaskSlice] = []
    for subtask in subtasks:
        leaf_decision = _route_leaf(
            request=request,
            assessment=assessment,
            subtask=subtask,
            all_subtasks=subtasks,
            mode=mode,
            repo_root=repo_root,
        )
        if not leaf_decision.delegate:
            local_fallback_reasons.append(f"{subtask.id}:{leaf_decision.why}")
            continue
        routed_subtasks.append(_leaf_to_subtask(subtask, leaf_decision))
    main_thread_followups = _build_main_thread_followups(
        request,
        followup_groups=main_thread_followup_groups,
        dependency_ids=[subtask.id for subtask in routed_subtasks],
    )
    if local_fallback_reasons:
        return _finalize_decision(
            repo_root=repo_root,
            request=request,
            decision=OrchestrationDecision(
                mode=OrchestrationMode.LOCAL_ONLY.value,
                decision_id=_new_decision_id(),
                delegate=False,
                parallel_safety=ParallelSafetyClass.LOCAL_ONLY.value,
                task_family=assessment.task_family,
                confidence=assessment.base_confidence,
                rationale="kept local because at least one bounded leaf required local rescoping",
                refusal_stage="leaf_router_refusal",
                manual_review_recommended=True,
                merge_owner="main_thread",
                merge_barrier_notes=["Leaf router safety gates beat orchestration fan-out."],
                execution_contract_notes=["A routed leaf refused delegation; keep the slice local until it is re-scoped safely."],
                completion_closeout_overrides={},
                local_only_reasons=local_fallback_reasons,
                budget_notes=budget_notes,
                main_thread_followups=main_thread_followups,
                request=request.as_dict(),
            ),
        )
    if any(subtask.route_model == "gpt-5.4-mini" for subtask in routed_subtasks):
        budget_notes.append("lighter read-only leaves were routed toward GPT-5.4-mini when the bounded analysis did not justify a larger tier")
    if any(subtask.route_model == "gpt-5.3-codex-spark" for subtask in routed_subtasks):
        budget_notes.append("lighter mechanical support leaves were routed toward Spark to conserve token budget")
    if any(subtask.route_model == "gpt-5.3-codex" for subtask in routed_subtasks):
        budget_notes.append("mid-tier coding leaves were routed toward Codex profiles before escalating to GPT-5.4")

    rationale = {
        OrchestrationMode.SINGLE_LEAF: "delegated as one bounded leaf because the grounded scope did not justify decomposition",
        OrchestrationMode.SERIAL_BATCH: "split into ordered serial leaves because the scope is decomposable but not parallel-safe",
        OrchestrationMode.PARALLEL_BATCH: "split into conservative parallel-safe leaves with an explicit main-thread merge barrier",
        OrchestrationMode.LOCAL_ONLY: "kept local",
    }[mode]
    merge_barrier_notes = [
        "The main thread owns merge, validation, and any cross-leaf adjudication.",
        "Do not merge partial leaf outputs before all planned leaves report back.",
    ]
    execution_contract_notes = [
        "For native `spawn_agent` calls, pass each leaf's `spawn_task_message` verbatim as `message`; do not rebuild the runtime banner or task contract from fragments.",
        "Each delegated subtask now includes a ready-to-send `route_native_spawn_payload`; prefer it when issuing native host spawn calls.",
        "For native `spawn_agent` calls, prefer the structured `route_spawn_agent_overrides` payload; use `route_spawn_overrides` for the richer lifecycle and idle-policy contract.",
        "Persist and reuse the per-decision inspection ledger at `inspection_artifacts.ledger_path`; it is the durable source of truth for spawned leaf ids, routed spawn payloads, transcript pointers, result handoffs, and `completion_closeout_overrides`-driven closeout state after agents are closed.",
        "When a native payload is unavailable, explicitly pass route_model plus route_reasoning_effort instead of inheriting parent defaults.",
        "The current native host accepts only built-in `agent_type` values and may still render parent-thread controls in the subagent UI; treat the routed runtime banner inside the delegated prompt as the authoritative requested runtime.",
        "Respect the emitted task-class routing policy fields; they are the explicit per-family baseline for model and reasoning selection.",
        "Treat `waiting on instruction` as an idle state owned by the main thread: either queue the next bounded follow-up immediately or close the agent.",
        "If a delegated leaf stays `waiting on instruction` for its emitted `route_idle_timeout_minutes` threshold, follow `route_idle_timeout_action` and `route_idle_timeout_escalation` instead of leaving the stale leaf open.",
        "Close delegated agents after result integration unless an immediate same-scope follow-up is already queued.",
    ]
    if mode is OrchestrationMode.SERIAL_BATCH:
        merge_barrier_notes.append("Each leaf depends on the previous ordered slice and should not start early.")
    if mode is OrchestrationMode.PARALLEL_BATCH:
        merge_barrier_notes.append("Only disjoint owned paths are eligible for concurrent execution.")
    if main_thread_followups:
        merge_barrier_notes.append("Main-thread governance follow-ups run only after delegated leaves are integrated.")
        execution_contract_notes.append(
            "Any emitted `main_thread_followups` stay local by design; complete them after delegated results are integrated instead of routing them through worker leaves."
        )
    merge_barrier_notes.extend(f"safety-note: {reason}" for reason in safety_reasons)
    return _finalize_decision(
        repo_root=repo_root,
        request=request,
        decision=OrchestrationDecision(
            mode=mode.value,
            decision_id=_new_decision_id(),
            delegate=True,
            parallel_safety=safety.value,
            task_family=assessment.task_family,
            confidence=_decision_confidence(assessment=assessment, mode=mode, subtasks=routed_subtasks),
            rationale=rationale,
            refusal_stage="delegated",
            manual_review_recommended=mode is OrchestrationMode.PARALLEL_BATCH or any(
                subtask.route_manual_review_recommended for subtask in routed_subtasks
            ),
            merge_owner="main_thread",
            merge_barrier_notes=merge_barrier_notes,
            execution_contract_notes=execution_contract_notes,
            completion_closeout_overrides=_completion_closeout_overrides(routed_subtasks),
            local_only_reasons=[],
            budget_notes=budget_notes,
            main_thread_followups=main_thread_followups,
            subtasks=routed_subtasks,
            request=request.as_dict(),
        ),
    )


def _feedback_labels(feedback: ExecutionFeedback) -> list[str]:
    labels: list[str] = []
    if feedback.accepted:
        labels.append("accepted")
    if feedback.merge_conflicts:
        labels.append("merge_conflicts")
    if feedback.rescope_required:
        labels.append("rescope_required")
    if feedback.false_parallelization:
        labels.append("false_parallelization")
    if feedback.escalated_leaves:
        labels.append("escalated")
    if feedback.token_efficient:
        labels.append("token_efficient")
    return labels or ["no_feedback_flags"]


def _feedback_identity(decision: OrchestrationDecision, feedback: ExecutionFeedback) -> str:
    explicit = _normalize_string(feedback.feedback_id)
    if explicit:
        return f"{decision.decision_id}::{explicit}"
    return f"{decision.decision_id}::{_canonical_hash({'mode': decision.mode, 'labels': _feedback_labels(feedback)})}"


def _remember_feedback_key(state: TuningState, *, feedback_key: str, seen_at: str) -> bool:
    if feedback_key in state.applied_feedback_keys:
        return False
    ledger = dict(state.applied_feedback_keys)
    ledger[feedback_key] = seen_at
    while len(ledger) > _FEEDBACK_LEDGER_LIMIT:
        stale_key = next(iter(ledger))
        ledger.pop(stale_key, None)
    state.applied_feedback_keys = ledger
    return True


def record_feedback(
    *,
    repo_root: Path,
    decision: OrchestrationDecision,
    feedback: ExecutionFeedback,
) -> dict[str, Any]:
    state = load_tuning_state(repo_root=repo_root)
    task_family = _normalize_token(decision.task_family) or "analysis_review"
    mode = _normalize_token(decision.mode)
    recorded_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    feedback_key = _feedback_identity(decision, feedback)
    labels = _feedback_labels(feedback)
    if not _remember_feedback_key(state, feedback_key=feedback_key, seen_at=recorded_at):
        state.updated_at = recorded_at
        path = save_tuning_state(repo_root=repo_root, state=state)
        return {
            "mode": mode,
            "task_family": task_family,
            "labels": labels,
            "replayed": True,
            "feedback_key": feedback_key,
            "bias_delta": 0.0,
            "family_bias_delta": 0.0,
            "bias_after": round(float(state.mode_bias.get(mode, 0.0) or 0.0), 3),
            "family_bias_after": round(float(state.family_mode_bias.get(task_family, {}).get(mode, 0.0) or 0.0), 3),
            "tuning_path": str(path),
            "state": state.as_dict(),
        }
    counts = dict(state.outcome_counts.get(mode, {}))
    for label in labels:
        counts[label] = int(counts.get(label, 0) or 0) + 1
    state.outcome_counts[mode] = counts
    state.family_mode_bias.setdefault(task_family, {known_mode: 0.0 for known_mode in _KNOWN_MODES})
    state.family_outcome_counts.setdefault(task_family, {known_mode: {} for known_mode in _KNOWN_MODES})
    family_counts = dict(state.family_outcome_counts[task_family].get(mode, {}))
    for label in labels:
        family_counts[label] = int(family_counts.get(label, 0) or 0) + 1
    state.family_outcome_counts[task_family][mode] = family_counts

    bias_delta = 0.0
    family_bias_delta = 0.0
    if feedback.accepted and not (feedback.merge_conflicts or feedback.rescope_required or feedback.false_parallelization):
        bias_delta += _DEFAULT_BIAS_DELTA
        family_bias_delta += _DEFAULT_FAMILY_BIAS_DELTA
    if feedback.token_efficient:
        bias_delta += 0.02
        family_bias_delta += 0.02
    if feedback.merge_conflicts:
        penalty = min(0.12, 0.04 * feedback.merge_conflicts)
        bias_delta -= penalty
        family_bias_delta -= penalty
    if feedback.rescope_required:
        bias_delta -= 0.05
        family_bias_delta -= 0.07
    if feedback.false_parallelization and mode == OrchestrationMode.PARALLEL_BATCH.value:
        bias_delta -= 0.1
        family_bias_delta -= 0.12
    if feedback.escalated_leaves:
        bias_delta -= min(0.09, 0.03 * feedback.escalated_leaves)
        family_bias_delta -= min(0.12, 0.04 * feedback.escalated_leaves)
    state.mode_bias[mode] = _clamp_bias(float(state.mode_bias.get(mode, 0.0) or 0.0) + bias_delta)
    state.family_mode_bias[task_family][mode] = _clamp_bias(
        float(state.family_mode_bias[task_family].get(mode, 0.0) or 0.0) + family_bias_delta
    )
    state.updated_at = recorded_at
    path = save_tuning_state(repo_root=repo_root, state=state)
    decision_ledger: dict[str, Any] = {}
    try:
        decision_ledger = load_decision_ledger(repo_root=repo_root, decision_id=decision.decision_id)
    except leaf_router.RouterInputError:
        decision_ledger = {}
    odylith_evaluation_ledger.append_event(
        repo_root=repo_root,
        event_type="orchestration_feedback",
        event_id=feedback_key,
        payload=odylith_evaluation_ledger.orchestration_feedback_event_payload(
            decision=decision.as_dict(),
            feedback=feedback.as_dict(),
            decision_ledger=decision_ledger,
        ),
        recorded_at=recorded_at,
    )
    return {
        "mode": mode,
        "task_family": task_family,
        "labels": labels,
        "replayed": False,
        "feedback_key": feedback_key,
        "bias_delta": round(bias_delta, 3),
        "family_bias_delta": round(family_bias_delta, 3),
        "bias_after": round(float(state.mode_bias.get(mode, 0.0) or 0.0), 3),
        "family_bias_after": round(float(state.family_mode_bias[task_family].get(mode, 0.0) or 0.0), 3),
        "tuning_path": str(path),
        "state": state.as_dict(),
    }


def _default_result_handoff() -> dict[str, Any]:
    return {
        "status": "pending",
        "summary": "",
        "artifact_paths": [],
        "validation_commands": [],
        "notes": "",
    }


def _default_followup_state() -> dict[str, Any]:
    return {
        "status": "not_queued",
        "summary": "",
        "queued_at": "",
        "claimed_at": "",
        "claim_expires_at": "",
    }


def _default_closeout_state() -> dict[str, Any]:
    return {
        "status": "open",
        "closed_at": "",
        "reason": "",
    }


def _default_subtask_inspection_state() -> dict[str, Any]:
    return {
        "status": "planned",
        "agent_id": "",
        "host_thread_id": "",
        "spawned_at": "",
        "last_updated_at": "",
        "transcript_pointers": [],
        "result_handoff": _default_result_handoff(),
        "followup": _default_followup_state(),
        "closeout": _default_closeout_state(),
    }


def _merge_followup_state(
    *,
    existing: Mapping[str, Any] | None,
    update: Mapping[str, Any] | None,
    recorded_at: str,
    claim_grace_minutes: int,
) -> dict[str, Any]:
    followup = dict(existing or _default_followup_state())
    raw = dict(update or {})
    current_status = _normalize_followup_status(followup.get("status", "")) or "not_queued"
    next_status = current_status
    if "status" in raw:
        candidate = _normalize_followup_status(raw.get("status", ""))
        next_status = candidate or "not_queued"
    followup["status"] = next_status

    if "summary" in raw:
        followup["summary"] = _normalize_string(raw.get("summary", ""))
    else:
        followup["summary"] = _normalize_string(followup.get("summary", ""))

    if next_status in _ACTIVE_FOLLOWUP_STATUSES:
        if "queued_at" in raw:
            followup["queued_at"] = _normalize_string(raw.get("queued_at", ""))
        else:
            followup["queued_at"] = _normalize_string(followup.get("queued_at", ""))
        if not followup["queued_at"]:
            followup["queued_at"] = recorded_at
        followup["claimed_at"] = ""
        followup["claim_expires_at"] = ""
        return followup

    if next_status == "claimed":
        if "claimed_at" in raw:
            followup["claimed_at"] = _normalize_string(raw.get("claimed_at", ""))
        else:
            followup["claimed_at"] = _normalize_string(followup.get("claimed_at", ""))
        if not followup["claimed_at"]:
            followup["claimed_at"] = recorded_at
        if "claim_expires_at" in raw:
            followup["claim_expires_at"] = _normalize_string(raw.get("claim_expires_at", ""))
        else:
            followup["claim_expires_at"] = _normalize_string(followup.get("claim_expires_at", ""))
        if not followup["claim_expires_at"]:
            followup["claim_expires_at"] = _timestamp_after_minutes(
                value=followup["claimed_at"],
                window_minutes=claim_grace_minutes,
            )
        followup["queued_at"] = ""
        return followup

    followup["queued_at"] = ""
    followup["claimed_at"] = ""
    followup["claim_expires_at"] = ""
    if next_status == "not_queued" and "summary" not in raw:
        followup["summary"] = ""
    return followup


def _normalize_transcript_pointers(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        value = [value] if _normalize_string(value) else []
    pointers: list[dict[str, str]] = []
    for raw in value:
        if isinstance(raw, Mapping):
            pointer_value = _normalize_string(raw.get("value", ""))
            if not pointer_value:
                continue
            pointer = {
                "kind": _normalize_token(raw.get("kind", "")) or "opaque",
                "value": pointer_value,
            }
            label = _normalize_string(raw.get("label", ""))
            if label:
                pointer["label"] = label
            pointers.append(pointer)
            continue
        pointer_value = _normalize_string(raw)
        if pointer_value:
            pointers.append({"kind": "opaque", "value": pointer_value})
    return pointers


def _decision_ledger_status(decision: OrchestrationDecision) -> str:
    if not decision.delegate:
        return "local_only"
    if decision.mode == OrchestrationMode.SINGLE_LEAF.value:
        return "delegated_single_leaf"
    if decision.mode == OrchestrationMode.SERIAL_BATCH.value:
        return "delegated_serial_batch"
    if decision.mode == OrchestrationMode.PARALLEL_BATCH.value:
        return "delegated_parallel_batch"
    return "planned"


def _decision_ledger_event(*, kind: str, summary: str, recorded_at: str, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "kind": _normalize_token(kind) or "event",
        "summary": _normalize_string(summary),
        "recorded_at": _normalize_string(recorded_at) or _now_timestamp(),
    }
    if isinstance(details, Mapping):
        normalized_details = {
            _normalize_string(key): value for key, value in details.items() if _normalize_string(key)
        }
        if normalized_details:
            payload["details"] = normalized_details
    return payload


def _decision_summary(decision: OrchestrationDecision) -> dict[str, Any]:
    return {
        "mode": decision.mode,
        "delegate": decision.delegate,
        "parallel_safety": decision.parallel_safety,
        "task_family": decision.task_family,
        "confidence": decision.confidence,
        "rationale": decision.rationale,
        "refusal_stage": decision.refusal_stage,
        "manual_review_recommended": decision.manual_review_recommended,
        "merge_owner": decision.merge_owner,
        "odylith_adoption": dict(decision.odylith_adoption),
    }


def _request_summary(request: OrchestrationRequest) -> dict[str, Any]:
    return {
        "prompt": request.prompt,
        "acceptance_criteria": list(request.acceptance_criteria),
        "candidate_paths": list(request.candidate_paths),
        "workstreams": list(request.workstreams),
        "components": list(request.components),
        "validation_commands": list(request.validation_commands),
        "accuracy_preference": request.accuracy_preference,
        "task_kind": request.task_kind,
        "phase": request.phase,
        "needs_write": request.needs_write,
        "latency_sensitive": request.latency_sensitive,
        "correctness_critical": request.correctness_critical,
        "requires_multi_agent_adjudication": request.requires_multi_agent_adjudication,
        "evolving_context_required": request.evolving_context_required,
        "evidence_cone_grounded": request.evidence_cone_grounded,
    }


def _subtask_ledger_entry(subtask: SubtaskSlice) -> dict[str, Any]:
    return {
        "subtask_id": subtask.id,
        "execution_group_kind": subtask.execution_group_kind,
        "scope_role": subtask.scope_role,
        "task_kind": subtask.task_kind,
        "phase": subtask.phase,
        "owned_paths": list(subtask.owned_paths),
        "read_paths": list(subtask.read_paths),
        "dependency_ids": list(subtask.dependency_ids),
        "deliverables": list(subtask.deliverables),
        "owner": subtask.owner,
        "goal": subtask.goal,
        "expected_output": subtask.expected_output,
        "termination_condition": subtask.termination_condition,
        "validation_commands": list(subtask.validation_commands),
        "route_model": subtask.route_model,
        "route_profile": subtask.route_profile,
        "route_reasoning_effort": subtask.route_reasoning_effort,
        "route_agent_role": subtask.route_agent_role,
        "route_task_class_profile": subtask.route_task_class_profile,
        "route_task_class_model": subtask.route_task_class_model,
        "route_task_class_reasoning_effort": subtask.route_task_class_reasoning_effort,
        "route_task_family": subtask.route_task_family,
        "route_confidence": subtask.route_confidence,
        "route_close_after_result": subtask.route_close_after_result,
        "route_idle_timeout_minutes": subtask.route_idle_timeout_minutes,
        "route_idle_timeout_action": subtask.route_idle_timeout_action,
        "route_idle_timeout_escalation": subtask.route_idle_timeout_escalation,
        "route_reuse_window": subtask.route_reuse_window,
        "route_prequeue_same_scope_reuse_claim_minutes": subtask.route_prequeue_same_scope_reuse_claim_minutes,
        "route_waiting_policy": subtask.route_waiting_policy,
        "route_termination_expectation": subtask.route_termination_expectation,
        "route_native_spawn_payload": dict(subtask.route_native_spawn_payload),
        "route_spawn_agent_overrides": dict(subtask.route_spawn_agent_overrides),
        "route_close_agent_overrides": dict(subtask.route_close_agent_overrides),
        "route_odylith_execution_profile": dict(subtask.route_odylith_execution_profile),
        "spawn_task_message": subtask.spawn_task_message,
        "inspection_state": _default_subtask_inspection_state(),
    }


def _closeout_recommendation_for_subtask(entry: Mapping[str, Any]) -> dict[str, Any]:
    subtask_id = _normalize_string(entry.get("subtask_id", ""))
    state = dict(entry.get("inspection_state", {}))
    default_state = _default_subtask_inspection_state()
    for key, value in default_state.items():
        state.setdefault(key, value if not isinstance(value, dict) else dict(value))

    status = _normalize_token(state.get("status", "")) or "planned"
    agent_id = _normalize_string(state.get("agent_id", ""))
    result_handoff = dict(state.get("result_handoff", _default_result_handoff()))
    result_status = _normalize_token(result_handoff.get("status", "")) or "pending"
    followup = dict(state.get("followup", _default_followup_state()))
    followup_status = _normalize_followup_status(followup.get("status", "")) or "not_queued"
    claim_grace_minutes = max(
        0,
        int(dict(entry.get("route_close_agent_overrides", {})).get("prequeue_same_scope_reuse_claim_minutes", 0) or 0),
    )
    claim_expires_at = _normalize_string(followup.get("claim_expires_at", ""))
    claimed_at = _normalize_string(followup.get("claimed_at", "")) or _normalize_string(state.get("last_updated_at", ""))
    claim_still_fresh = False
    if followup_status == "claimed":
        if claim_expires_at:
            claim_still_fresh = _timestamp_is_future(claim_expires_at)
        else:
            claim_still_fresh = _timestamp_within_minutes(
                value=claimed_at,
                window_minutes=claim_grace_minutes,
            )
    closeout = dict(state.get("closeout", _default_closeout_state()))
    closeout_status = _normalize_token(closeout.get("status", "")) or "open"
    close_agent_payload = {
        key: value
        for key, value in dict(entry.get("route_close_agent_overrides", {})).items()
        if isinstance(key, str)
    }
    if agent_id:
        close_agent_payload["id"] = agent_id
    if subtask_id:
        close_agent_payload["subtask_id"] = subtask_id

    if closeout_status == "closed":
        return {
            "action": "already_closed",
            "reason": "delegated leaf is already marked closed in the inspection ledger",
            "agent_id": agent_id,
            "close_agent_payload": {},
        }
    if followup_status in _ACTIVE_FOLLOWUP_STATUSES and not agent_id:
        return {
            "action": "record_agent_id_then_keep_open",
            "reason": "a same-scope follow-up is active in the inspection ledger but the host ledger still needs the delegated agent id",
            "agent_id": "",
            "close_agent_payload": {},
        }
    if followup_status in _ACTIVE_FOLLOWUP_STATUSES:
        return {
            "action": "keep_open",
            "reason": "an explicit same-scope follow-up is queued in the inspection ledger",
            "agent_id": agent_id,
            "close_agent_payload": {},
        }
    if followup_status == "claimed" and claim_still_fresh and not agent_id:
        return {
            "action": "record_agent_id_then_keep_open",
            "reason": "a bounded immediate same-scope reuse claim is open but the host ledger still needs the delegated agent id",
            "agent_id": "",
            "close_agent_payload": {},
        }
    if claim_still_fresh:
        return {
            "action": "keep_open",
            "reason": "the main thread has a bounded immediate same-scope reuse claim open while the follow-up is being finalized",
            "agent_id": agent_id,
            "close_agent_payload": {},
        }
    if status in {"waiting_on_instruction", "waiting", "idle"} and agent_id:
        if followup_status == "claimed" and claim_grace_minutes > 0:
            return {
                "action": "close_now",
                "reason": "the bounded same-scope reuse claim expired before the follow-up was queued",
                "agent_id": agent_id,
                "close_agent_payload": close_agent_payload,
            }
        return {
            "action": "close_now",
            "reason": "delegated leaf is waiting on instruction with no explicit queued same-scope follow-up",
            "agent_id": agent_id,
            "close_agent_payload": close_agent_payload,
        }
    if result_status in {"reported", "integrated", "validated", "accepted"} and agent_id:
        if followup_status == "claimed" and claim_grace_minutes > 0:
            return {
                "action": "close_now",
                "reason": "the bounded same-scope reuse claim expired before the follow-up was queued",
                "agent_id": agent_id,
                "close_agent_payload": close_agent_payload,
            }
        return {
            "action": "close_now",
            "reason": "delegated result handoff is recorded and no explicit same-scope follow-up is queued",
            "agent_id": agent_id,
            "close_agent_payload": close_agent_payload,
        }
    if (status in {"waiting_on_instruction", "waiting", "idle"} or result_status in {"reported", "integrated", "validated", "accepted"}) and not agent_id:
        if followup_status == "claimed" and claim_grace_minutes > 0:
            return {
                "action": "record_agent_id_then_close",
                "reason": "the bounded same-scope reuse claim expired, but the host ledger still needs the delegated agent id before a native close can be issued",
                "agent_id": "",
                "close_agent_payload": {},
            }
        return {
            "action": "record_agent_id_then_close",
            "reason": "closeout is ready but the host ledger still needs the delegated agent id before a native close can be issued",
            "agent_id": "",
            "close_agent_payload": {},
        }
    if not agent_id:
        return {
            "action": "await_spawn",
            "reason": "delegated leaf has not been recorded as spawned in the inspection ledger yet",
            "agent_id": "",
            "close_agent_payload": {},
        }
    return {
        "action": "keep_open",
        "reason": "delegated leaf still appears active or no result handoff has been recorded yet",
        "agent_id": agent_id,
        "close_agent_payload": {},
    }


def _refresh_closeout_recommendations(ledger: dict[str, Any]) -> None:
    subtasks = ledger.get("subtasks", [])
    if not isinstance(subtasks, list):
        ledger["recommended_closeout_actions"] = []
        return
    recommended_actions: list[dict[str, Any]] = []
    for entry in subtasks:
        if not isinstance(entry, dict):
            continue
        recommendation = _closeout_recommendation_for_subtask(entry)
        entry["closeout_recommendation"] = recommendation
        if recommendation.get("action") != "close_now":
            continue
        recommended_actions.append(
            {
                "subtask_id": _normalize_string(entry.get("subtask_id", "")),
                "agent_id": _normalize_string(recommendation.get("agent_id", "")),
                "reason": _normalize_string(recommendation.get("reason", "")),
                "close_agent_payload": dict(recommendation.get("close_agent_payload", {})),
            }
        )
    ledger["recommended_closeout_actions"] = recommended_actions


def build_decision_ledger(
    *,
    repo_root: Path,
    request: OrchestrationRequest,
    decision: OrchestrationDecision,
) -> dict[str, Any]:
    decision = _attach_inspection_artifacts(repo_root=repo_root, decision=decision)
    recorded_at = _now_timestamp()
    inspection_artifacts = dict(decision.inspection_artifacts)
    inspection_artifacts.update(
        {
            "persisted": True,
            "recorded_at": recorded_at,
        }
    )
    ledger = {
        "version": _DECISION_LEDGER_VERSION,
        "decision_id": decision.decision_id,
        "recorded_at": recorded_at,
        "updated_at": recorded_at,
        "decision_status": _decision_ledger_status(decision),
        "decision_summary": _decision_summary(decision),
        "request_summary": _request_summary(request),
        "inspection_artifacts": inspection_artifacts,
        "merge_barrier_notes": list(decision.merge_barrier_notes),
        "execution_contract_notes": list(decision.execution_contract_notes),
        "completion_closeout_overrides": dict(decision.completion_closeout_overrides),
        "main_thread_followups": [followup.as_dict() for followup in decision.main_thread_followups],
        "subtasks": [_subtask_ledger_entry(subtask) for subtask in decision.subtasks],
        "events": [
            _decision_ledger_event(
                kind="planned",
                summary=(
                    f"Created orchestration ledger for {decision.mode} with {len(decision.subtasks)} delegated leaf slice(s)."
                ),
                recorded_at=recorded_at,
                details={
                    "delegate": decision.delegate,
                    "parallel_safety": decision.parallel_safety,
                },
            )
        ],
    }
    _refresh_closeout_recommendations(ledger)
    return ledger


def persist_decision_ledger(
    *,
    repo_root: Path,
    request: OrchestrationRequest,
    decision: OrchestrationDecision,
) -> dict[str, Any]:
    ledger = build_decision_ledger(repo_root=repo_root, request=request, decision=decision)
    inspection_artifacts = dict(ledger.get("inspection_artifacts", {}))
    ledger_path = Path(str(inspection_artifacts.get("ledger_path", ""))).expanduser().resolve()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision.inspection_artifacts = inspection_artifacts
    return ledger


def load_decision_ledger(*, repo_root: Path, decision_id: str) -> dict[str, Any]:
    path = decision_ledger_path(repo_root=repo_root, decision_id=decision_id)
    payload = _load_json_mapping(path)
    if not payload:
        raise leaf_router.RouterInputError(
            code="decision_ledger_not_found",
            message="no persisted orchestration decision ledger was found for the requested decision",
            details=[str(path)],
        )
    return payload


def _subtask_ledger_map(ledger: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    subtasks = ledger.get("subtasks", [])
    if not isinstance(subtasks, Sequence) or isinstance(subtasks, (str, bytes, bytearray)):
        return {}
    return {
        _normalize_string(entry.get("subtask_id", "")): entry
        for entry in subtasks
        if isinstance(entry, dict) and _normalize_string(entry.get("subtask_id", ""))
    }


def _merge_subtask_ledger_update(entry: dict[str, Any], update: Mapping[str, Any], *, recorded_at: str) -> None:
    state = dict(entry.get("inspection_state", {}))
    default_state = _default_subtask_inspection_state()
    for key, value in default_state.items():
        state.setdefault(key, value if not isinstance(value, dict) else dict(value))

    status = _normalize_token(update.get("status", ""))
    if status:
        state["status"] = status
    agent_id = _normalize_string(update.get("agent_id", ""))
    if agent_id:
        state["agent_id"] = agent_id
    host_thread_id = _normalize_string(update.get("host_thread_id", ""))
    if host_thread_id:
        state["host_thread_id"] = host_thread_id
    spawned_at = _normalize_string(update.get("spawned_at", ""))
    if spawned_at:
        state["spawned_at"] = spawned_at
    transcript_pointers = update.get("transcript_pointers", [])
    if "transcript_pointer" in update and not transcript_pointers:
        transcript_pointer = _normalize_string(update.get("transcript_pointer", ""))
        if transcript_pointer:
            transcript_pointers = [
                {
                    "kind": _normalize_token(update.get("transcript_pointer_kind", "")) or "opaque",
                    "value": transcript_pointer,
                }
            ]
    normalized_pointers = _normalize_transcript_pointers(transcript_pointers)
    if normalized_pointers:
        state["transcript_pointers"] = normalized_pointers

    result_handoff = dict(state.get("result_handoff", _default_result_handoff()))
    raw_result_handoff = update.get("result_handoff", {})
    if isinstance(raw_result_handoff, Mapping):
        handoff_status = _normalize_token(raw_result_handoff.get("status", ""))
        if handoff_status:
            result_handoff["status"] = handoff_status
        handoff_summary = _normalize_string(raw_result_handoff.get("summary", ""))
        if handoff_summary:
            result_handoff["summary"] = handoff_summary
        if "artifact_paths" in raw_result_handoff:
            result_handoff["artifact_paths"] = _normalize_list(raw_result_handoff.get("artifact_paths", []))
        if "validation_commands" in raw_result_handoff:
            result_handoff["validation_commands"] = _normalize_list(raw_result_handoff.get("validation_commands", []))
        handoff_notes = _normalize_string(raw_result_handoff.get("notes", ""))
        if handoff_notes:
            result_handoff["notes"] = handoff_notes
    state["result_handoff"] = result_handoff

    raw_followup = update.get("followup", {})
    claim_grace_minutes = max(
        0,
        int(dict(entry.get("route_close_agent_overrides", {})).get("prequeue_same_scope_reuse_claim_minutes", 0) or 0),
    )
    state["followup"] = _merge_followup_state(
        existing=state.get("followup", _default_followup_state()),
        update=raw_followup if isinstance(raw_followup, Mapping) else {},
        recorded_at=recorded_at,
        claim_grace_minutes=claim_grace_minutes,
    )

    closeout = dict(state.get("closeout", _default_closeout_state()))
    raw_closeout = update.get("closeout", {})
    if isinstance(raw_closeout, Mapping):
        close_status = _normalize_token(raw_closeout.get("status", ""))
        if close_status:
            closeout["status"] = close_status
        closed_at = _normalize_string(raw_closeout.get("closed_at", ""))
        if closed_at:
            closeout["closed_at"] = closed_at
        close_reason = _normalize_string(raw_closeout.get("reason", ""))
        if close_reason:
            closeout["reason"] = close_reason
    state["closeout"] = closeout
    state["last_updated_at"] = recorded_at
    entry["inspection_state"] = state


def _append_ledger_event(ledger: dict[str, Any], event: dict[str, Any]) -> None:
    events = ledger.get("events", [])
    if not isinstance(events, list):
        events = []
    events.append(event)
    while len(events) > _DECISION_LEDGER_EVENT_LIMIT:
        events.pop(0)
    ledger["events"] = events


def record_decision_ledger(
    *,
    repo_root: Path,
    decision_id: str,
    update: Mapping[str, Any],
) -> dict[str, Any]:
    ledger = load_decision_ledger(repo_root=repo_root, decision_id=decision_id)
    recorded_at = _now_timestamp()
    if _normalize_string(update.get("decision_id", "")) and _normalize_string(update.get("decision_id", "")) != _normalize_string(decision_id):
        raise leaf_router.RouterInputError(
            code="invalid_decision_ledger_update",
            message="decision ledger update referenced a different decision id than the selected ledger",
            details=[_normalize_string(update.get("decision_id", "")), _normalize_string(decision_id)],
        )
    decision_status = _normalize_token(update.get("decision_status", ""))
    if decision_status:
        ledger["decision_status"] = decision_status

    subtasks = _subtask_ledger_map(ledger)
    updated_subtasks: list[str] = []
    subtasks_payload = update.get("subtasks", [])
    if isinstance(subtasks_payload, Sequence) and not isinstance(subtasks_payload, (str, bytes, bytearray)):
        for raw in subtasks_payload:
            if not isinstance(raw, Mapping):
                continue
            subtask_id = _normalize_string(raw.get("subtask_id", raw.get("id", "")))
            if not subtask_id:
                continue
            entry = subtasks.get(subtask_id)
            if entry is None:
                raise leaf_router.RouterInputError(
                    code="invalid_decision_ledger_update",
                    message="decision ledger update referenced an unknown subtask id",
                    details=[subtask_id],
                )
            _merge_subtask_ledger_update(entry, raw, recorded_at=recorded_at)
            updated_subtasks.append(subtask_id)

    explicit_event = update.get("event", {})
    if isinstance(explicit_event, Mapping):
        kind = _normalize_token(explicit_event.get("kind", ""))
        summary = _normalize_string(explicit_event.get("summary", ""))
        if kind or summary:
            _append_ledger_event(
                ledger,
                _decision_ledger_event(
                    kind=kind or "update",
                    summary=summary or f"Recorded orchestration ledger update for {decision_id}.",
                    recorded_at=recorded_at,
                    details=explicit_event.get("details", {}),
                ),
            )
    elif updated_subtasks:
        _append_ledger_event(
            ledger,
            _decision_ledger_event(
                kind="subtask_update",
                summary="Updated orchestration ledger state for delegated leaf inspection.",
                recorded_at=recorded_at,
                details={"subtask_ids": updated_subtasks},
            ),
        )

    ledger["updated_at"] = recorded_at
    inspection_artifacts = dict(ledger.get("inspection_artifacts", {}))
    inspection_artifacts["persisted"] = True
    inspection_artifacts["last_recorded_at"] = recorded_at
    ledger["inspection_artifacts"] = inspection_artifacts
    _refresh_closeout_recommendations(ledger)
    ledger_path = Path(str(inspection_artifacts.get("ledger_path", ""))).expanduser().resolve()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "decision_id": _normalize_string(ledger.get("decision_id", "")),
        "ledger_path": str(ledger_path),
        "decision_status": _normalize_token(ledger.get("decision_status", "")),
        "updated_at": recorded_at,
        "updated_subtasks": updated_subtasks,
        "event_count": len(ledger.get("events", [])) if isinstance(ledger.get("events", []), list) else 0,
    }


def append_orchestration_audit(
    *,
    repo_root: Path,
    request: OrchestrationRequest,
    decision: OrchestrationDecision,
    feedback: ExecutionFeedback | None = None,
    stream_path: Path | None = None,
) -> dict[str, Any]:
    stream = stream_path or (Path(repo_root).resolve() / DEFAULT_STREAM_PATH).resolve()
    artifacts = list(request.candidate_paths or ["src/odylith/runtime/orchestration/subagent_orchestrator.py"])
    components = [DEFAULT_COMPONENT_ID, *request.components]
    summary = (
        f"Subagent orchestrator chose {decision.mode} with {len(decision.subtasks)} leaf slice(s) "
        f"for family {decision.task_family or 'unknown'}."
    )
    kind = "decision"
    if feedback is not None:
        summary = (
            f"Subagent orchestrator recorded {', '.join(_feedback_labels(feedback))} "
            f"for mode {decision.mode} in family {decision.task_family or 'unknown'}."
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


def _decision_from_mapping(payload: Mapping[str, Any]) -> OrchestrationDecision:
    subtasks_payload = payload.get("subtasks", [])
    subtasks: list[SubtaskSlice] = []
    if isinstance(subtasks_payload, Sequence) and not isinstance(subtasks_payload, (str, bytes, bytearray)):
        for raw in subtasks_payload:
            if not isinstance(raw, Mapping):
                continue
            subtasks.append(
                SubtaskSlice(
                    id=_normalize_string(raw.get("id", "")),
                    prompt=_normalize_multiline_string(raw.get("prompt", "")),
                    route_prompt=_normalize_multiline_string(raw.get("route_prompt", "")),
                    execution_group_kind=_normalize_token(raw.get("execution_group_kind", "")),
                    scope_role=_normalize_token(raw.get("scope_role", "")),
                    task_kind=_normalize_token(raw.get("task_kind", "")),
                    phase=_normalize_token(raw.get("phase", "")),
                    correctness_critical=_normalize_bool(raw.get("correctness_critical", False)),
                    latency_sensitive=_normalize_bool(raw.get("latency_sensitive", False)),
                    accuracy_preference=_normalize_token(raw.get("accuracy_preference", "accuracy")) or "accuracy",
                    owned_paths=_normalize_list(raw.get("owned_paths", [])),
                    read_paths=_normalize_list(raw.get("read_paths", [])),
                    dependency_ids=_normalize_list(raw.get("dependency_ids", [])),
                    deliverables=_normalize_list(raw.get("deliverables", [])),
                    owner=_normalize_string(raw.get("owner", "")),
                    goal=_normalize_string(raw.get("goal", "")),
                    expected_output=_normalize_string(raw.get("expected_output", "")),
                    termination_condition=_normalize_string(raw.get("termination_condition", "")),
                    prompt_contract_lines=_normalize_list(raw.get("prompt_contract_lines", [])),
                    spawn_task_message=_normalize_multiline_string(raw.get("spawn_task_message", "")),
                    validation_commands=_normalize_list(raw.get("validation_commands", [])),
                    merge_owner=_normalize_token(raw.get("merge_owner", "main_thread")) or "main_thread",
                    escalation_allowed=_normalize_bool(raw.get("escalation_allowed", True), default=True),
                    route_profile=_normalize_token(raw.get("route_profile", "")),
                    route_model=_normalize_string(raw.get("route_model", "")),
                    route_reasoning_effort=_normalize_token(raw.get("route_reasoning_effort", "")),
                    route_task_class_profile=_normalize_token(raw.get("route_task_class_profile", "")),
                    route_task_class_model=_normalize_string(raw.get("route_task_class_model", "")),
                    route_task_class_reasoning_effort=_normalize_token(raw.get("route_task_class_reasoning_effort", "")),
                    route_task_class_policy_lines=_normalize_list(raw.get("route_task_class_policy_lines", [])),
                    route_agent_role=_normalize_token(raw.get("route_agent_role", "")),
                    route_close_after_result=_normalize_bool(raw.get("route_close_after_result", False)),
                    route_idle_timeout_minutes=max(0, int(raw.get("route_idle_timeout_minutes", 0) or 0)),
                    route_idle_timeout_action=_normalize_token(raw.get("route_idle_timeout_action", "")),
                    route_idle_timeout_escalation=_normalize_token(raw.get("route_idle_timeout_escalation", "")),
                    route_reuse_window=_normalize_token(raw.get("route_reuse_window", "")),
                    route_prequeue_same_scope_reuse_claim_minutes=max(
                        0,
                        int(raw.get("route_prequeue_same_scope_reuse_claim_minutes", 0) or 0),
                    ),
                    route_waiting_policy=_normalize_token(raw.get("route_waiting_policy", "")),
                    route_termination_expectation=_normalize_string(raw.get("route_termination_expectation", "")),
                    route_spawn_contract_lines=_normalize_list(raw.get("route_spawn_contract_lines", [])),
                    route_spawn_overrides={
                        _normalize_token(key): value
                        for key, value in dict(raw.get("route_spawn_overrides", {})).items()
                        if _normalize_token(key)
                    }
                    if isinstance(raw.get("route_spawn_overrides", {}), Mapping)
                    else {},
                    route_spawn_agent_overrides={
                        _normalize_token(key): value
                        for key, value in dict(raw.get("route_spawn_agent_overrides", {})).items()
                        if _normalize_token(key)
                    }
                    if isinstance(raw.get("route_spawn_agent_overrides", {}), Mapping)
                    else {},
                    route_close_agent_overrides={
                        _normalize_token(key): value
                        for key, value in dict(raw.get("route_close_agent_overrides", {})).items()
                        if _normalize_token(key)
                    }
                    if isinstance(raw.get("route_close_agent_overrides", {}), Mapping)
                    else {},
                    route_host_tool_contract={
                        _normalize_token(key): value
                        for key, value in dict(raw.get("route_host_tool_contract", {})).items()
                        if _normalize_token(key)
                    }
                    if isinstance(raw.get("route_host_tool_contract", {}), Mapping)
                    else {},
                    route_runtime_banner_lines=_normalize_list(raw.get("route_runtime_banner_lines", [])),
                    route_native_spawn_payload={
                        _normalize_token(key): value
                        for key, value in dict(raw.get("route_native_spawn_payload", {})).items()
                        if _normalize_token(key)
                    }
                    if isinstance(raw.get("route_native_spawn_payload", {}), Mapping)
                    else {},
                    route_task_family=_normalize_token(raw.get("route_task_family", "")),
                    route_confidence=_clamp_confidence(raw.get("route_confidence", 0) or 0),
                    route_manual_review_recommended=_normalize_bool(raw.get("route_manual_review_recommended", False)),
                    route_why=_normalize_string(raw.get("route_why", "")),
                    route_explanation_lines=_normalize_list(raw.get("route_explanation_lines", [])),
                    route_odylith_execution_profile={
                        _normalize_token(key): value
                        for key, value in dict(raw.get("route_odylith_execution_profile", {})).items()
                        if _normalize_token(key)
                    }
                    if isinstance(raw.get("route_odylith_execution_profile", {}), Mapping)
                    else {},
                )
            )
    followups_payload = payload.get("main_thread_followups", [])
    main_thread_followups: list[MainThreadFollowup] = []
    if isinstance(followups_payload, Sequence) and not isinstance(followups_payload, (str, bytes, bytearray)):
        for raw in followups_payload:
            if not isinstance(raw, Mapping):
                continue
            main_thread_followups.append(
                MainThreadFollowup(
                    id=_normalize_string(raw.get("id", "")),
                    scope_role=_normalize_token(raw.get("scope_role", "governance")) or "governance",
                    paths=_normalize_list(raw.get("paths", [])),
                    dependency_ids=_normalize_list(raw.get("dependency_ids", [])),
                    owner=_normalize_token(raw.get("owner", "main_thread")) or "main_thread",
                    goal=_normalize_string(raw.get("goal", "")),
                    deliverables=_normalize_list(raw.get("deliverables", [])),
                    why_local=_normalize_string(raw.get("why_local", "")),
                )
            )
    request_payload = dict(payload.get("request", {})) if isinstance(payload.get("request", {}), Mapping) else {}
    return OrchestrationDecision(
        mode=_normalize_token(payload.get("mode", "")),
        decision_id=_normalize_string(payload.get("decision_id", "")),
        delegate=_normalize_bool(payload.get("delegate", False)),
        parallel_safety=_normalize_token(payload.get("parallel_safety", "")),
        task_family=_normalize_token(payload.get("task_family", "")),
        confidence=_clamp_confidence(payload.get("confidence", 0) or 0),
        rationale=_normalize_string(payload.get("rationale", "")),
        refusal_stage=_normalize_token(payload.get("refusal_stage", "")),
        manual_review_recommended=_normalize_bool(payload.get("manual_review_recommended", False)),
        merge_owner=_normalize_token(payload.get("merge_owner", "main_thread")) or "main_thread",
        merge_barrier_notes=_normalize_list(payload.get("merge_barrier_notes", [])),
        execution_contract_notes=_normalize_list(payload.get("execution_contract_notes", [])),
        completion_closeout_overrides={
            _normalize_token(key): value
            for key, value in dict(payload.get("completion_closeout_overrides", {})).items()
            if _normalize_token(key)
        }
        if isinstance(payload.get("completion_closeout_overrides", {}), Mapping)
        else {},
        inspection_artifacts={
            _normalize_token(key): value
            for key, value in dict(payload.get("inspection_artifacts", {})).items()
            if _normalize_token(key)
        }
        if isinstance(payload.get("inspection_artifacts", {}), Mapping)
        else {},
        odylith_adoption={
            _normalize_token(key): value
            for key, value in dict(payload.get("odylith_adoption", {})).items()
            if _normalize_token(key)
        }
        if isinstance(payload.get("odylith_adoption", {}), Mapping)
        else {},
        local_only_reasons=_normalize_list(payload.get("local_only_reasons", [])),
        budget_notes=_normalize_list(payload.get("budget_notes", [])),
        main_thread_followups=main_thread_followups,
        subtasks=subtasks,
        request=request_payload,
    )


def _load_json_input(*, inline_value: str, file_value: str, name: str) -> dict[str, Any]:
    return leaf_router._load_json_input(  # noqa: SLF001
        inline_value=inline_value,
        file_value=file_value,
        name=name,
    )


def _emit_payload(payload: Mapping[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print("subagent orchestrator")
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"- {key}: {json.dumps(value, sort_keys=True)}")
        else:
            print(f"- {key}: {value}")


def _emit_error(error: leaf_router.RouterInputError, *, as_json: bool) -> None:
    payload = error.as_payload()
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print("subagent orchestrator error")
    print(f"- error_code: {payload['error_code']}")
    print(f"- message: {payload['message']}")
    for detail in payload["details"]:
        print(f"- detail: {detail}")


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _load_decision_reference(
    *,
    decision_id: str,
    decision_json: str,
    decision_file: str,
) -> str:
    explicit = _normalize_string(decision_id)
    if explicit:
        return explicit
    if decision_json or decision_file:
        payload = _load_json_input(
            inline_value=decision_json,
            file_value=decision_file,
            name="orchestration decision",
        )
        decision = _decision_from_mapping(payload)
        if decision.decision_id:
            return decision.decision_id
    raise leaf_router.RouterInputError(
        code="missing_decision_reference",
        message="a decision id or orchestration decision payload is required",
        details=["provide --decision-id or --decision-json/--decision-file"],
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith subagent-orchestrator",
        description="Plan automatic prompt-level subagent orchestration for substantive grounded repo work across consumer and maintainer lanes.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Build an orchestration plan for a grounded prompt.")
    plan.add_argument("--repo-root", default=".")
    plan.add_argument("--input-json", default="")
    plan.add_argument("--input-file", default="")
    plan.add_argument("--json", action="store_true")
    plan.add_argument("--log-compass", action="store_true")
    plan.add_argument("--stream", default=DEFAULT_STREAM_PATH)

    record = sub.add_parser("record-feedback", help="Persist orchestration-local tuning feedback.")
    record.add_argument("--repo-root", default=".")
    record.add_argument("--decision-json", default="")
    record.add_argument("--decision-file", default="")
    record.add_argument("--feedback-json", default="")
    record.add_argument("--feedback-file", default="")
    record.add_argument("--json", action="store_true")
    record.add_argument("--log-compass", action="store_true")
    record.add_argument("--stream", default=DEFAULT_STREAM_PATH)

    show = sub.add_parser("show-tuning", help="Show orchestration-local tuning state.")
    show.add_argument("--repo-root", default=".")
    show.add_argument("--json", action="store_true")

    show_ledger = sub.add_parser("show-ledger", help="Show the persisted inspection ledger for one orchestration decision.")
    show_ledger.add_argument("--repo-root", default=".")
    show_ledger.add_argument("--decision-id", default="")
    show_ledger.add_argument("--decision-json", default="")
    show_ledger.add_argument("--decision-file", default="")
    show_ledger.add_argument("--json", action="store_true")

    record_ledger = sub.add_parser(
        "record-ledger",
        help="Persist transcript pointers, result handoffs, and closeout state for one orchestration decision.",
    )
    record_ledger.add_argument("--repo-root", default=".")
    record_ledger.add_argument("--decision-id", default="")
    record_ledger.add_argument("--decision-json", default="")
    record_ledger.add_argument("--decision-file", default="")
    record_ledger.add_argument("--update-json", default="")
    record_ledger.add_argument("--update-file", default="")
    record_ledger.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    try:
        if args.command == "plan":
            request_payload = _load_json_input(
                inline_value=str(args.input_json),
                file_value=str(args.input_file),
                name="orchestration request",
            )
            request = orchestration_request_from_mapping(request_payload)
            decision = orchestrate_prompt(request, repo_root=repo_root)
            persist_decision_ledger(repo_root=repo_root, request=request, decision=decision)
            if args.log_compass:
                append_orchestration_audit(
                    repo_root=repo_root,
                    request=request,
                    decision=decision,
                    stream_path=_resolve(repo_root, str(args.stream)),
                )
            _emit_payload(decision.as_dict(), as_json=bool(args.json))
            return 0
        if args.command == "record-feedback":
            decision_payload = _load_json_input(
                inline_value=str(args.decision_json),
                file_value=str(args.decision_file),
                name="orchestration decision",
            )
            feedback_payload = _load_json_input(
                inline_value=str(args.feedback_json),
                file_value=str(args.feedback_file),
                name="orchestration feedback",
            )
            decision = _decision_from_mapping(decision_payload)
            feedback = execution_feedback_from_mapping(feedback_payload)
            payload = record_feedback(repo_root=repo_root, decision=decision, feedback=feedback)
            if args.log_compass:
                request = orchestration_request_from_mapping(decision.request if isinstance(decision.request, Mapping) else {})
                append_orchestration_audit(
                    repo_root=repo_root,
                    request=request,
                    decision=decision,
                    feedback=feedback,
                    stream_path=_resolve(repo_root, str(args.stream)),
                )
            _emit_payload(payload, as_json=bool(args.json))
            return 0
        if args.command == "show-tuning":
            _emit_payload(load_tuning_state(repo_root=repo_root).as_dict(), as_json=bool(args.json))
            return 0
        if args.command == "show-ledger":
            selected_decision_id = _load_decision_reference(
                decision_id=str(args.decision_id),
                decision_json=str(args.decision_json),
                decision_file=str(args.decision_file),
            )
            _emit_payload(load_decision_ledger(repo_root=repo_root, decision_id=selected_decision_id), as_json=bool(args.json))
            return 0
        if args.command == "record-ledger":
            selected_decision_id = _load_decision_reference(
                decision_id=str(args.decision_id),
                decision_json=str(args.decision_json),
                decision_file=str(args.decision_file),
            )
            update_payload = _load_json_input(
                inline_value=str(args.update_json),
                file_value=str(args.update_file),
                name="decision ledger update",
            )
            _emit_payload(
                record_decision_ledger(
                    repo_root=repo_root,
                    decision_id=selected_decision_id,
                    update=update_payload,
                ),
                as_json=bool(args.json),
            )
            return 0
    except leaf_router.RouterInputError as error:
        _emit_error(error, as_json=bool(getattr(args, "json", False)))
        return error.exit_code
    return 2


__all__ = [
    "DEFAULT_COMPONENT_ID",
    "DEFAULT_DECISION_LEDGER_DIR",
    "DEFAULT_STREAM_PATH",
    "DEFAULT_TUNING_PATH",
    "ExecutionFeedback",
    "OrchestrationDecision",
    "OrchestrationMode",
    "OrchestrationRequest",
    "ParallelSafetyClass",
    "SubtaskSlice",
    "TuningState",
    "append_orchestration_audit",
    "build_decision_ledger",
    "decision_ledger_dir",
    "decision_ledger_path",
    "execution_feedback_from_mapping",
    "load_decision_ledger",
    "load_tuning_state",
    "orchestrate_prompt",
    "orchestration_request_from_mapping",
    "persist_decision_ledger",
    "record_decision_ledger",
    "record_feedback",
    "save_tuning_state",
    "tuning_state_path",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
