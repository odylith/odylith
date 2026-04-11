from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

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


def _guard_fields(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "present": bool(summary.get("execution_governance_present")),
        "outcome": _token(summary.get("execution_governance_outcome")),
        "requires_reanchor": _bool(summary.get("execution_governance_requires_reanchor")),
        "mode": _token(summary.get("execution_governance_mode")),
        "next_move": _text(summary.get("execution_governance_next_move")),
        "blocker": _text(summary.get("execution_governance_blocker")),
        "closure": _token(summary.get("execution_governance_closure")),
        "wait_status": _token(summary.get("execution_governance_wait_status")),
        "wait_detail": _text(summary.get("execution_governance_wait_detail")),
        "contradiction_count": _int(summary.get("execution_governance_contradiction_count")),
        "history_rule_count": _int(summary.get("execution_governance_history_rule_count")),
        "host_family": _token(summary.get("execution_governance_host_family")),
        "model_family": _token(summary.get("execution_governance_model_family")),
        "host_supports_native_spawn_present": "execution_governance_host_supports_native_spawn" in summary,
        "host_supports_native_spawn": _bool(summary.get("execution_governance_host_supports_native_spawn")),
        "target_lane": _token(summary.get("execution_governance_target_lane")),
        "has_writable_targets": _bool(summary.get("execution_governance_has_writable_targets")),
        "requires_more_consumer_context": _bool(
            summary.get("execution_governance_requires_more_consumer_context")
        ),
        "consumer_failover": _text(summary.get("execution_governance_consumer_failover")),
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
    return (
        f"the detected host keeps this slice on local or serial follow-through because "
        f"{host_label} does not expose native delegated {action_label}"
    )


def _action_guard(summary: Mapping[str, Any], *, action_label: str) -> LaneGovernanceGuard:
    fields = _guard_fields(summary)
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
            fields["host_family"],
        )
    ):
        return LaneGovernanceGuard(blocked=False)

    if fields["requires_reanchor"]:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-reanchor",
            reason=f"the slice needs a fresh re-anchor before any new {action_label}",
        )

    if fields["contradiction_count"] > 0:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-contradiction",
            reason=f"the slice has live contradictions that need local resolution before any new {action_label}",
        )

    if fields["wait_status"] in _ACTIVE_WAIT_STATUSES:
        detail = fields["wait_detail"]
        detail_suffix = f" ({detail})" if detail else ""
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-wait",
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
            code="execution-governance-consumer-fence",
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
            code="execution-governance-critical-path",
            reason=f"the slice is on a {fields['mode']}-first critical path, so {action_label} should wait{blocker_suffix}",
        )

    if fields["closure"] == "destructive":
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-destructive-closure",
            reason=f"the current scope is destructive relative to the active system state, so keep coordination local before any new {action_label}",
        )

    if fields["closure"] == "incomplete":
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-incomplete-closure",
            reason=f"the current scope is not closed under its dependencies, so keep coordination local before any new {action_label}",
        )

    host_reason = _host_serial_reason(action_label=action_label, fields=fields)
    if host_reason:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-host-serial",
            reason=host_reason,
        )

    if fields["outcome"] == "deny":
        next_move = fields["next_move"]
        if next_move:
            return LaneGovernanceGuard(
                blocked=True,
                code="execution-governance-deny",
                reason=f"the current contract does not admit new {action_label}; the truthful next move is `{next_move}`",
            )
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-deny",
            reason=f"the current contract does not admit new {action_label}",
        )

    if fields["outcome"] == "defer":
        next_move = fields["next_move"]
        if next_move:
            return LaneGovernanceGuard(
                blocked=True,
                code="execution-governance-defer",
                reason=f"the truthful next move is `{next_move}` before any new {action_label}",
            )
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-defer",
            reason=f"the current slice needs local follow-through before any new {action_label}",
        )

    if fields["history_rule_count"] > 0 and fields["closure"] in _UNSAFE_CLOSURE_CLASSES:
        return LaneGovernanceGuard(
            blocked=True,
            code="execution-governance-history-rule",
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
