from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping
from typing import Sequence

_ACTIVE_WAIT_STATUSES: frozenset[str] = frozenset(
    {
        "queued",
        "building",
        "awaiting_callback",
        "deploying",
        "deploying_cell_01",
        "waiting_approval",
        "blocked_on_token_refresh",
        "running",
        "in_progress",
    }
)
_CRITICAL_PATH_MODES: frozenset[str] = frozenset({"verify", "recover"})
_UNSAFE_CLOSURE_CLASSES: frozenset[str] = frozenset({"incomplete", "destructive"})


@dataclass(frozen=True)
class LaneGovernanceGuard:
    blocked: bool
    code: str = ""
    reason: str = ""


def _token(value: Any) -> str:
    return " ".join(str(value or "").split()).strip().lower().replace("-", "_").replace(" ", "_")


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _token(value) in {"1", "true", "yes", "on"}


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple, set)):
        return ()
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _text(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return tuple(rows)


def _pressure_count(signals: Sequence[str], prefix: str) -> int:
    prefix_token = f"{_token(prefix)}:"
    for signal in signals:
        token = _token(signal)
        if not token.startswith(prefix_token):
            continue
        try:
            return int(token.split(":", 1)[1] or 0)
        except ValueError:
            return 0
    return 0


def _guard_fields(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "present": bool(summary.get("execution_engine_present")),
        "outcome": _token(summary.get("execution_engine_outcome")),
        "requires_reanchor": _bool(summary.get("execution_engine_requires_reanchor")),
        "mode": _token(summary.get("execution_engine_mode")),
        "next_move": _text(summary.get("execution_engine_next_move")),
        "blocker": _text(summary.get("execution_engine_blocker")),
        "closure": _token(summary.get("execution_engine_closure")),
        "wait_status": _token(summary.get("execution_engine_wait_status")),
        "wait_detail": _text(summary.get("execution_engine_wait_detail")),
        "contradiction_count": _int(summary.get("execution_engine_contradiction_count")),
        "history_rule_count": _int(summary.get("execution_engine_history_rule_count")),
        "validation_derived_from": _strings(summary.get("execution_engine_validation_derived_from")),
        "history_rule_hits": _strings(summary.get("execution_engine_history_rule_hits")),
        "pressure_signals": _strings(summary.get("execution_engine_pressure_signals")),
        "nearby_denial_actions": _strings(summary.get("execution_engine_nearby_denial_actions")),
        "event_count": _int(summary.get("execution_engine_event_count")),
        "host_family": _token(summary.get("execution_engine_host_family")),
        "model_family": _token(summary.get("execution_engine_model_family")),
        "host_supports_native_spawn_present": "execution_engine_host_supports_native_spawn" in summary,
        "host_supports_native_spawn": _bool(summary.get("execution_engine_host_supports_native_spawn")),
        "host_supports_artifact_paths_present": "execution_engine_host_supports_artifact_paths" in summary,
        "host_supports_artifact_paths": _bool(summary.get("execution_engine_host_supports_artifact_paths")),
        "target_lane": _token(summary.get("execution_engine_target_lane")),
        "has_writable_targets": _bool(summary.get("execution_engine_has_writable_targets")),
        "requires_more_consumer_context": _bool(
            summary.get("execution_engine_requires_more_consumer_context")
        ),
        "consumer_failover": _text(summary.get("execution_engine_consumer_failover")),
        "runtime_invalidated_by_step": _text(summary.get("execution_engine_runtime_invalidated_by_step")),
        "native_spawn_ready": _bool(summary.get("native_spawn_ready")),
    }


def _host_serial_reason(*, action_label: str, fields: Mapping[str, Any]) -> str:
    host_family = _token(fields.get("host_family"))
    if not bool(fields.get("host_supports_native_spawn_present")):
        return ""
    if bool(fields.get("host_supports_native_spawn")):
        return ""
    if host_family == "codex":
        host_label = "Codex"
    elif host_family == "claude":
        host_label = "Claude Code"
    elif host_family:
        host_label = host_family.replace("_", " ").title()
    else:
        host_label = "the detected host"
    action_surface = "delegated execution"
    if _token(action_label) == "parallel_fan_out":
        action_surface = "parallel fan-out"
    return (
        f"the detected host keeps this slice on local or serial follow-through because "
        f"{host_label} does not expose native {action_surface}"
    )


def _action_guard(summary: Mapping[str, Any], *, action_label: str) -> LaneGovernanceGuard:
    fields = _guard_fields(summary)
    history_rule_hits = {_token(token) for token in fields["history_rule_hits"]}
    pressure_signals = tuple(_text(token) for token in fields["pressure_signals"])
    nearby_denial_actions = tuple(_text(token) for token in fields["nearby_denial_actions"])
    if not any(
        (
            fields["present"],
            fields["outcome"],
            fields["requires_reanchor"],
            fields["mode"],
            fields["closure"],
            fields["wait_status"],
            fields["contradiction_count"] > 0,
            fields["history_rule_count"] > 0,
            bool(history_rule_hits),
            bool(pressure_signals),
            fields["host_family"],
        )
    ):
        return LaneGovernanceGuard(blocked=False)

    if fields["runtime_invalidated_by_step"]:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-runtime-invalidated",
            reason=(
                "the governed execution snapshot was invalidated by "
                f"`{fields['runtime_invalidated_by_step']}`, so re-anchor locally before any new {action_label}"
            ),
        )

    if fields["requires_reanchor"]:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-reanchor",
            reason=f"the slice needs a fresh re-anchor before any new {action_label}",
        )

    if fields["contradiction_count"] > 0:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-contradiction",
            reason=f"the slice has live contradictions that need local resolution before any new {action_label}",
        )

    if "user_correction_requires_promotion" in history_rule_hits:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-user-correction",
            reason=f"the slice still needs promoted hard user constraints before any new {action_label}",
        )

    if "contradiction_blocked_preflight" in history_rule_hits:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-history-contradiction",
            reason=f"the slice already matches a contradiction-blocked failure class, so re-anchor before any new {action_label}",
        )

    if "repeated_rediscovery_detected" in history_rule_hits:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-history-rediscovery",
            reason=f"the slice is drifting into repeated rediscovery, so keep {action_label} local until the frontier is re-anchored",
        )

    if "reanchor_triggered" in history_rule_hits or _pressure_count(pressure_signals, "denials") >= 2 or _pressure_count(
        pressure_signals, "off_contract"
    ) >= 2:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-reanchor-pressure",
            reason=f"recent denials or off-contract pressure require a fresh re-anchor before any new {action_label}",
        )

    if fields["wait_status"] in _ACTIVE_WAIT_STATUSES:
        detail = fields["wait_detail"]
        detail_suffix = f" ({detail})" if detail else ""
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-wait",
            reason=(
                f"the truthful next move is to resume the active external dependency{detail_suffix} "
                f"before any new {action_label}"
            ),
        )

    for signal in pressure_signals:
        token = _token(signal)
        if token.startswith("wait:"):
            detail = fields["wait_detail"]
            detail_suffix = f" ({detail})" if detail else ""
            return LaneGovernanceGuard(
                blocked=True,
                code="execution-engine-wait-pressure",
                reason=(
                    f"the truthful next move is to resume the active external dependency{detail_suffix} "
                    f"before any new {action_label}"
                ),
            )

    if fields["target_lane"] == "consumer" and not fields["has_writable_targets"]:
        failover = fields["consumer_failover"]
        failover_suffix = f" ({failover})" if failover else ""
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-consumer-fence",
            reason=(
                f"the consumer lane does not yet have writable consumer targets{failover_suffix}, "
                f"so keep {action_label} local until the slice narrows to admissible repo-owned paths"
            ),
        )

    if fields["mode"] in _CRITICAL_PATH_MODES:
        blocker = fields["blocker"]
        blocker_suffix = f" after `{blocker}` clears" if blocker else " until the frontier advances"
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-critical-path",
            reason=f"the slice is on a {fields['mode']}-first critical path, so {action_label} should wait{blocker_suffix}",
        )

    if (
        _token(action_label) == "parallel_fan_out"
        and bool(fields.get("host_supports_artifact_paths_present"))
        and not bool(fields.get("host_supports_artifact_paths"))
        and fields["closure"] in _UNSAFE_CLOSURE_CLASSES
    ):
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-no-artifact-paths",
            reason=(
                f"the detected host does not support artifact paths between workers; "
                f"keep scope coordination local before any new {action_label}"
            ),
        )

    if "destructive_subset_blocked" in history_rule_hits:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-history-destructive-closure",
            reason=f"the slice already matches a known destructive-subset failure class, so keep {action_label} local until scope is closure-safe",
        )

    if fields["closure"] == "destructive":
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-destructive-closure",
            reason=f"the current scope is destructive relative to the active system state, so keep coordination local before any new {action_label}",
        )

    if fields["closure"] == "incomplete":
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-incomplete-closure",
            reason=f"the current scope is not closed under its dependencies, so keep coordination local before any new {action_label}",
        )

    host_reason = _host_serial_reason(action_label=action_label, fields=fields)
    if host_reason:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-host-serial",
            reason=host_reason,
        )

    if fields["outcome"] == "deny":
        next_move = fields["next_move"]
        denial_suffix = (
            f"; nearby denied actions include `{nearby_denial_actions[0]}`"
            if nearby_denial_actions
            else ""
        )
        if next_move:
            return LaneGovernanceGuard(
                blocked=True,
                code="execution-engine-deny",
                reason=(
                    f"the current contract does not admit new {action_label}; "
                    f"the truthful next move is `{next_move}`{denial_suffix}"
                ),
            )
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-deny",
            reason=f"the current contract does not admit new {action_label}{denial_suffix}",
        )

    if fields["outcome"] == "defer":
        next_move = fields["next_move"]
        if next_move:
            return LaneGovernanceGuard(
                blocked=True,
                code="execution-engine-defer",
                reason=f"the truthful next move is `{next_move}` before any new {action_label}",
            )
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-defer",
            reason=f"the current slice needs local follow-through before any new {action_label}",
        )

    if fields["history_rule_count"] > 0 and fields["closure"] in _UNSAFE_CLOSURE_CLASSES:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-engine-history-rule",
            reason=f"the current scope already matches a known failure pattern, so keep coordination local before any new {action_label}",
        )

    return LaneGovernanceGuard(blocked=False)


def delegation_guard(summary: Mapping[str, Any]) -> LaneGovernanceGuard:
    return _action_guard(summary, action_label="delegation")


def parallelism_guard(summary: Mapping[str, Any]) -> LaneGovernanceGuard:
    return _action_guard(summary, action_label="parallel fan-out")


__all__ = [
    "LaneGovernanceGuard",
    "delegation_guard",
    "parallelism_guard",
]
