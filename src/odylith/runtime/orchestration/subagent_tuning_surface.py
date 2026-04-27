"""Presentation helpers for subagent tuning and live adoption status."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping


_ADOPTION_KEYS: tuple[str, ...] = (
    "status",
    "sample_size",
    "latest_recorded_at",
    "packet_present_rate",
    "auto_grounded_rate",
    "route_ready_rate",
    "native_spawn_ready_rate",
    "requires_widening_rate",
    "grounded_delegate_rate",
    "workspace_daemon_reused_rate",
    "session_namespaced_rate",
    "evidence_source",
)


def _has_recorded_feedback(payload: Mapping[str, Any], *, applied_key: str) -> bool:
    if isinstance(payload.get(applied_key), Mapping) and payload.get(applied_key):
        return True
    for bucket_key in ("outcome_counts", "family_outcome_counts"):
        bucket = payload.get(bucket_key)
        if not isinstance(bucket, Mapping):
            continue
        if _mapping_has_count(bucket):
            return True
    return False


def _mapping_has_count(value: Mapping[str, Any]) -> bool:
    for row in value.values():
        if isinstance(row, Mapping):
            if _mapping_has_count(row):
                return True
            continue
        try:
            if int(row or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _live_adoption_snapshot(repo_root: Path) -> dict[str, Any]:
    from odylith.runtime.context_engine import odylith_context_engine_store as context_store

    snapshot = context_store.load_orchestration_adoption_snapshot(repo_root=repo_root)
    return {key: snapshot.get(key) for key in _ADOPTION_KEYS if key in snapshot}


def build_tuning_surface(
    *,
    repo_root: Path,
    state_payload: Mapping[str, Any],
    component_id: str,
    applied_key: str,
) -> dict[str, Any]:
    """Annotate adaptive tuning output with its scope and live adoption proof."""

    payload = dict(state_payload)
    has_feedback = _has_recorded_feedback(payload, applied_key=applied_key)
    payload["component_id"] = component_id
    payload["tuning_scope"] = "adaptive_feedback_only"
    payload["tuning_state"] = "feedback_recorded" if has_feedback else "no_feedback_recorded"
    payload["tuning_note"] = (
        "Bias and outcome maps only reflect explicit record-outcome or record-feedback calls; "
        "empty maps are not proof that routing, planning, or host spawning is inactive."
    )
    payload["live_orchestration_adoption"] = _live_adoption_snapshot(repo_root)
    return payload


def router_surface(*, repo_root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    return build_tuning_surface(
        repo_root=repo_root,
        state_payload=state,
        component_id="subagent-router",
        applied_key="applied_outcome_keys",
    )


def orchestrator_surface(*, repo_root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    return build_tuning_surface(
        repo_root=repo_root,
        state_payload=state,
        component_id="subagent-orchestrator",
        applied_key="applied_feedback_keys",
    )
