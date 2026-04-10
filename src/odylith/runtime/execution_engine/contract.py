from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal
from typing import Mapping

from odylith.runtime.common import host_runtime as host_runtime_contract

ExecutionMode = Literal["explore", "implement", "verify", "recover"]
DecisionOutcome = Literal["admit", "deny", "defer"]
ResourceClosureClass = Literal["safe", "incomplete", "destructive"]

VALID_EXECUTION_MODES: tuple[ExecutionMode, ...] = ("explore", "implement", "verify", "recover")
VALID_DECISION_OUTCOMES: tuple[DecisionOutcome, ...] = ("admit", "deny", "defer")
VALID_RESOURCE_CLOSURE_CLASSES: tuple[ResourceClosureClass, ...] = ("safe", "incomplete", "destructive")


def _dedupe(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values or ():
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return tuple(ordered)


@dataclass(frozen=True)
class ExecutionHostProfile:
    host_family: str
    host_display_name: str
    model_family: str
    model_name: str
    supports_native_spawn: bool
    supports_local_structured_reasoning: bool
    supports_explicit_model_selection: bool
    execution_hints: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def detected(
        cls,
        *,
        host_family: str,
        model_name: str = "",
        model_family: str = "",
    ) -> "ExecutionHostProfile":
        normalized_host = str(host_family or "").strip().lower() or "unknown"
        normalized_model_name = str(model_name or "").strip()
        normalized_model_family = str(model_family or "").strip().lower()
        if not normalized_model_family:
            if normalized_host == "codex":
                normalized_model_family = "codex"
            elif normalized_host == "claude":
                normalized_model_family = "claude"
            else:
                normalized_model_family = "generic"

        if normalized_host == "codex":
            return cls(
                host_family="codex",
                host_display_name="Codex",
                model_family=normalized_model_family,
                model_name=normalized_model_name or "gpt-5.4",
                supports_native_spawn=True,
                supports_local_structured_reasoning=True,
                supports_explicit_model_selection=True,
                execution_hints=(
                    "native_spawn_available",
                    "prefer_parallel_workers_for_disjoint_write_sets",
                ),
            )
        if normalized_host == "claude":
            return cls(
                host_family="claude",
                host_display_name="Claude Code",
                model_family=normalized_model_family,
                model_name=normalized_model_name or "claude",
                supports_native_spawn=False,
                supports_local_structured_reasoning=True,
                supports_explicit_model_selection=False,
                execution_hints=(
                    "keep_shared_contract_host_general",
                    "prefer_local_or_serial_followthrough_when_spawn_unavailable",
                ),
            )
        return cls(
            host_family=normalized_host,
            host_display_name=normalized_host.title() or "Unknown Host",
            model_family=normalized_model_family,
            model_name=normalized_model_name,
            supports_native_spawn=False,
            supports_local_structured_reasoning=False,
            supports_explicit_model_selection=False,
            execution_hints=("unknown_host_fail_closed",),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_capabilities(
        cls,
        capabilities: Mapping[str, Any],
        *,
        model_name: str = "",
    ) -> "ExecutionHostProfile":
        return cls(
            host_family=str(capabilities.get("host_family", "")).strip(),
            model_name=str(model_name or "").strip(),
            model_family=str(capabilities.get("model_family", "")).strip(),
            supports_native_spawn=bool(capabilities.get("supports_native_spawn")),
            supports_local_structured_reasoning=bool(
                capabilities.get("supports_local_structured_reasoning")
            ),
            supports_explicit_model_selection=bool(
                capabilities.get("supports_explicit_model_selection")
            ),
            host_display_name=str(capabilities.get("host_family", "")).strip().title() or "Unknown Host",
            execution_hints=tuple(
                hint
                for hint in (
                    "native_spawn_available" if bool(capabilities.get("supports_native_spawn")) else "",
                    (
                        "prefer_parallel_workers_for_disjoint_write_sets"
                        if bool(capabilities.get("supports_native_spawn"))
                        else "prefer_local_or_serial_followthrough_when_spawn_unavailable"
                    ),
                    (
                        "explicit_model_selection_available"
                        if bool(capabilities.get("supports_explicit_model_selection"))
                        else ""
                    ),
                )
                if hint
            ),
        )


@dataclass(frozen=True)
class HardConstraint:
    constraint_id: str
    source: str
    label: str
    required_lane: str = ""
    required_scope: tuple[str, ...] = field(default_factory=tuple)
    forbidden_moves: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "source": self.source,
            "label": self.label,
            "required_lane": self.required_lane,
            "required_scope": list(self.required_scope),
            "forbidden_moves": list(self.forbidden_moves),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ExecutionEvent:
    event_id: str
    event_type: str
    phase: str = ""
    successful: bool = False
    blocker: str = ""
    next_move: str = ""
    execution_mode: str = ""
    external_state: "ExternalDependencyState | None" = None
    receipt: "SemanticReceipt | None" = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "phase": self.phase,
            "successful": self.successful,
            "blocker": self.blocker,
            "next_move": self.next_move,
            "execution_mode": self.execution_mode,
        }
        if self.external_state is not None:
            payload["external_state"] = self.external_state.to_dict()
        if self.receipt is not None:
            payload["receipt"] = self.receipt.to_dict()
        return payload


@dataclass(frozen=True)
class TurnContext:
    intent: str = ""
    surfaces: tuple[str, ...] = field(default_factory=tuple)
    visible_text: tuple[str, ...] = field(default_factory=tuple)
    active_tab: str = ""
    user_turn_id: str = ""
    supersedes_turn_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "intent": self.intent,
                "surfaces": list(self.surfaces),
                "visible_text": list(self.visible_text),
                "active_tab": self.active_tab,
                "user_turn_id": self.user_turn_id,
                "supersedes_turn_id": self.supersedes_turn_id,
            }.items()
            if value not in ("", [], {}, None)
        }


@dataclass(frozen=True)
class TurnPresentationPolicy:
    commentary_mode: str = ""
    suppress_routing_receipts: bool = False
    surface_fast_lane: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "suppress_routing_receipts": self.suppress_routing_receipts,
            "surface_fast_lane": self.surface_fast_lane,
        }
        if self.commentary_mode:
            payload["commentary_mode"] = self.commentary_mode
        return payload


@dataclass(frozen=True)
class TargetCandidate:
    path: str
    source: str = ""
    reason: str = ""
    surface: str = ""
    writable: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "path": self.path,
            "writable": self.writable,
        }
        if self.source:
            payload["source"] = self.source
        if self.reason:
            payload["reason"] = self.reason
        if self.surface:
            payload["surface"] = self.surface
        return payload


@dataclass(frozen=True)
class DiagnosticAnchor:
    kind: str
    value: str
    label: str = ""
    path: str = ""
    surface: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "kind": self.kind,
                "value": self.value,
                "label": self.label,
                "path": self.path,
                "surface": self.surface,
                "source": self.source,
            }.items()
            if value not in ("", [], {}, None)
        }


@dataclass(frozen=True)
class TargetResolution:
    lane: str
    candidate_targets: tuple[TargetCandidate, ...] = field(default_factory=tuple)
    diagnostic_anchors: tuple[DiagnosticAnchor, ...] = field(default_factory=tuple)
    has_writable_targets: bool = False
    requires_more_consumer_context: bool = False
    consumer_failover: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "has_writable_targets": self.has_writable_targets,
            "requires_more_consumer_context": self.requires_more_consumer_context,
        }
        if self.lane:
            payload["lane"] = self.lane
        if self.candidate_targets:
            payload["candidate_targets"] = [row.to_dict() for row in self.candidate_targets]
        if self.diagnostic_anchors:
            payload["diagnostic_anchors"] = [row.to_dict() for row in self.diagnostic_anchors]
        if self.consumer_failover:
            payload["consumer_failover"] = self.consumer_failover
        return payload


@dataclass(frozen=True)
class ExecutionContract:
    objective: str
    authoritative_lane: str
    target_scope: tuple[str, ...]
    environment: str
    resource_set: tuple[str, ...]
    success_criteria: tuple[str, ...]
    validation_plan: tuple[str, ...]
    allowed_moves: tuple[str, ...]
    forbidden_moves: tuple[str, ...]
    external_dependencies: tuple[str, ...]
    critical_path: tuple[str, ...]
    hard_constraints: tuple[HardConstraint, ...] = field(default_factory=tuple)
    host_profile: ExecutionHostProfile | None = None
    turn_context: TurnContext | None = None
    target_resolution: TargetResolution | None = None
    presentation_policy: TurnPresentationPolicy | None = None
    execution_mode: ExecutionMode = "implement"

    def __post_init__(self) -> None:
        if self.execution_mode not in VALID_EXECUTION_MODES:
            raise ValueError(f"invalid execution mode `{self.execution_mode}`")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "objective": self.objective,
            "authoritative_lane": self.authoritative_lane,
            "target_scope": list(self.target_scope),
            "environment": self.environment,
            "resource_set": list(self.resource_set),
            "success_criteria": list(self.success_criteria),
            "validation_plan": list(self.validation_plan),
            "allowed_moves": list(self.allowed_moves),
            "forbidden_moves": list(self.forbidden_moves),
            "external_dependencies": list(self.external_dependencies),
            "critical_path": list(self.critical_path),
            "hard_constraints": [constraint.to_dict() for constraint in self.hard_constraints],
            "execution_mode": self.execution_mode,
        }
        if self.host_profile is not None:
            payload["host_profile"] = self.host_profile.to_dict()
        if self.turn_context is not None:
            payload["turn_context"] = self.turn_context.to_dict()
        if self.target_resolution is not None:
            payload["target_resolution"] = self.target_resolution.to_dict()
        if self.presentation_policy is not None:
            payload["presentation_policy"] = self.presentation_policy.to_dict()
        return payload

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        authoritative_lane: str,
        target_scope: tuple[str, ...] | list[str],
        environment: str,
        resource_set: tuple[str, ...] | list[str],
        success_criteria: tuple[str, ...] | list[str],
        validation_plan: tuple[str, ...] | list[str],
        allowed_moves: tuple[str, ...] | list[str],
        forbidden_moves: tuple[str, ...] | list[str],
        external_dependencies: tuple[str, ...] | list[str],
        critical_path: tuple[str, ...] | list[str],
        hard_constraints: tuple[HardConstraint, ...] | list[HardConstraint] | None = None,
        host_profile: ExecutionHostProfile | None = None,
        turn_context: TurnContext | None = None,
        target_resolution: TargetResolution | None = None,
        presentation_policy: TurnPresentationPolicy | None = None,
        execution_mode: ExecutionMode = "implement",
    ) -> "ExecutionContract":
        return cls(
            objective=str(objective or "").strip(),
            authoritative_lane=str(authoritative_lane or "").strip(),
            target_scope=_dedupe(list(target_scope)),
            environment=str(environment or "").strip(),
            resource_set=_dedupe(list(resource_set)),
            success_criteria=_dedupe(list(success_criteria)),
            validation_plan=_dedupe(list(validation_plan)),
            allowed_moves=_dedupe(list(allowed_moves)),
            forbidden_moves=_dedupe(list(forbidden_moves)),
            external_dependencies=_dedupe(list(external_dependencies)),
            critical_path=_dedupe(list(critical_path)),
            hard_constraints=tuple(hard_constraints or ()),
            host_profile=host_profile,
            turn_context=turn_context,
            target_resolution=target_resolution,
            presentation_policy=presentation_policy,
            execution_mode=execution_mode,
        )


@dataclass(frozen=True)
class AdmissibilityDecision:
    outcome: DecisionOutcome
    action: str
    rationale: str
    violated_preconditions: tuple[str, ...] = field(default_factory=tuple)
    nearest_admissible_alternative: str = ""
    requires_reanchor: bool = False
    host_hints: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.outcome not in VALID_DECISION_OUTCOMES:
            raise ValueError(f"invalid admissibility outcome `{self.outcome}`")

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "action": self.action,
            "rationale": self.rationale,
            "violated_preconditions": list(self.violated_preconditions),
            "nearest_admissible_alternative": self.nearest_admissible_alternative,
            "requires_reanchor": self.requires_reanchor,
            "host_hints": list(self.host_hints),
        }


@dataclass(frozen=True)
class ResumeHandle:
    resume_token: str
    external_id: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "resume_token": self.resume_token,
            "external_id": self.external_id,
            "source": self.source,
        }


@dataclass(frozen=True)
class ExecutionFrontier:
    current_phase: str
    last_successful_phase: str
    active_blocker: str
    in_flight_external_ids: tuple[str, ...]
    resume_handles: tuple[ResumeHandle, ...]
    truthful_next_move: str
    execution_mode: ExecutionMode

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_phase": self.current_phase,
            "last_successful_phase": self.last_successful_phase,
            "active_blocker": self.active_blocker,
            "in_flight_external_ids": list(self.in_flight_external_ids),
            "resume_handles": [handle.to_dict() for handle in self.resume_handles],
            "truthful_next_move": self.truthful_next_move,
            "execution_mode": self.execution_mode,
        }


@dataclass(frozen=True)
class ResourceClosure:
    classification: ResourceClosureClass
    requested: tuple[str, ...]
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple)
    destructive_overlap: tuple[str, ...] = field(default_factory=tuple)
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.classification not in VALID_RESOURCE_CLOSURE_CLASSES:
            raise ValueError(f"invalid resource-closure class `{self.classification}`")

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "requested": list(self.requested),
            "missing_dependencies": list(self.missing_dependencies),
            "destructive_overlap": list(self.destructive_overlap),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ExternalDependencyState:
    source: str
    external_id: str
    semantic_status: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "semantic_status": self.semantic_status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SemanticReceipt:
    action: str
    scope_fingerprint: str
    causal_parent: str = ""
    resume_token: str = ""
    expected_next_states: tuple[str, ...] = field(default_factory=tuple)
    external_state: ExternalDependencyState | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "action": self.action,
            "scope_fingerprint": self.scope_fingerprint,
            "causal_parent": self.causal_parent,
            "resume_token": self.resume_token,
            "expected_next_states": list(self.expected_next_states),
        }
        if self.external_state is not None:
            payload["external_state"] = self.external_state.to_dict()
        return payload


@dataclass(frozen=True)
class ValidationMatrix:
    archetype: str
    checks: tuple[str, ...]
    minimum_pass_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "archetype": self.archetype,
            "checks": list(self.checks),
            "minimum_pass_count": self.minimum_pass_count,
        }


@dataclass(frozen=True)
class ContradictionRecord:
    source: str
    claim: str
    conflicting_evidence: str
    severity: str
    blocks_execution: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "claim": self.claim,
            "conflicting_evidence": self.conflicting_evidence,
            "severity": self.severity,
            "blocks_execution": self.blocks_execution,
        }


def detect_execution_host_profile(
    *candidates: Any,
    model_name: str = "",
    environ: Mapping[str, str] | None = None,
) -> ExecutionHostProfile:
    capabilities = host_runtime_contract.resolve_host_capabilities(*candidates, environ=environ)
    return ExecutionHostProfile.from_capabilities(capabilities, model_name=model_name)
