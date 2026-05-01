"""Local-only gate policy for prompt-level subagent orchestration."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.execution_engine import runtime_lane_policy
from odylith.runtime.orchestration import subagent_router as leaf_router
from odylith.runtime.orchestration.subagent_orchestrator_support import _sanitize_user_facing_lines


_ODYLITH_SIGNAL_KEYS: frozenset[str] = frozenset(
    {
        "route_ready",
        "odylith_execution_route_ready",
        "narrowing_required",
        "odylith_execution_narrowing_required",
        "native_spawn_ready",
        "odylith_execution_delegate_preference",
        "odylith_execution_selection_mode",
        "odylith_execution_profile",
    }
)


class OrchestrationGateRequest(Protocol):
    needs_write: bool
    evidence_cone_grounded: bool
    candidate_paths: Sequence[str]
    repo_work: bool


def can_decompose_coordination_heavy_write(
    request: OrchestrationGateRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    path_groups: Sequence[Sequence[str]],
) -> bool:
    if not request.needs_write or not request.evidence_cone_grounded:
        return False
    if len(request.candidate_paths) < 2:
        return False
    if assessment.write_scope_clarity < 3 or assessment.acceptance_clarity < 2 or assessment.validation_clarity < 1:
        return False
    context_summary = dict(assessment.context_signal_summary or {})
    odylith_signal_present = any(key in context_summary for key in _ODYLITH_SIGNAL_KEYS)
    odylith_route_ready = bool(context_summary.get("route_ready") or context_summary.get("odylith_execution_route_ready"))
    odylith_narrowing_required = bool(
        context_summary.get("narrowing_required") or context_summary.get("odylith_execution_narrowing_required")
    )
    odylith_native_spawn_ready = bool(context_summary.get("native_spawn_ready"))
    if odylith_signal_present and (odylith_narrowing_required or not odylith_route_ready or not odylith_native_spawn_ready):
        return False
    return len([list(group) for group in path_groups if group]) >= 2


def should_keep_local(
    request: OrchestrationGateRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    architecture_policy: Mapping[str, Any],
    path_groups: Sequence[Sequence[str]],
    decomposable_coordination_gates: frozenset[str],
    trivial_local_prompt: bool,
) -> tuple[list[str], list[str]]:
    reasons = list(assessment.hard_gate_hits)
    notes: list[str] = []
    context_summary = dict(assessment.context_signal_summary or {})
    governance_guard = runtime_lane_policy.delegation_guard(context_summary)
    if governance_guard.blocked and governance_guard.code not in reasons:
        reasons.append(governance_guard.code)
        notes.append(governance_guard.reason)

    odylith_profile = _normalize_token(context_summary.get("odylith_execution_profile", ""))
    odylith_delegate_preference = _normalize_token(context_summary.get("odylith_execution_delegate_preference", ""))
    odylith_selection_mode = _normalize_token(context_summary.get("odylith_execution_selection_mode", ""))
    odylith_route_ready = bool(context_summary.get("route_ready") or context_summary.get("odylith_execution_route_ready"))
    odylith_narrowing_required = bool(
        context_summary.get("narrowing_required") or context_summary.get("odylith_execution_narrowing_required")
    )
    odylith_native_spawn_ready = bool(context_summary.get("native_spawn_ready"))
    odylith_signal_present = any(key in context_summary for key in _ODYLITH_SIGNAL_KEYS)
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
        notes.append("The slice still needs local narrowing or local coordination before any bounded fan-out.")
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
        notes.append("The read-only slice stays local until the evidence cone narrows enough to delegate safely.")
    if architecture_policy.get("active") and (
        architecture_policy.get("full_scan_recommended")
        or architecture_policy.get("mode") == "local_only"
        or (architecture_policy.get("risk_tier") == "high" and architecture_policy.get("confidence_tier") == "low")
    ):
        reasons.append("architecture-local-grounding")
        notes.append(
            "Architecture dossier coverage is too weak or too risky for delegation; keep the slice local until the authority graph is grounded enough to trust."
        )
    if can_decompose_coordination_heavy_write(request, assessment, path_groups=path_groups):
        relaxed = [reason for reason in reasons if reason in decomposable_coordination_gates]
        if relaxed:
            reasons = [reason for reason in reasons if reason not in decomposable_coordination_gates]
            notes.append(
                "The base prompt looked coordination-heavy, but grounded explicit owned paths let the orchestrator decompose it into bounded ordered leaves."
            )
    if trivial_local_prompt:
        reasons.append("trivial-direct-answer")
    if not request.repo_work:
        reasons.append("non-repo-work-prompt")
    return reasons, _sanitize_user_facing_lines(notes)


__all__ = ["can_decompose_coordination_heavy_write", "should_keep_local"]
