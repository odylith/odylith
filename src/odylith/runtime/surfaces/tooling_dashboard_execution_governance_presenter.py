"""Compact execution-governance packet presentation for the tooling shell."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any


def _string(value: Any) -> str:
    return str(value or "").strip()


def _strings(value: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _string(item)
        normalized = token.lower()
        if not token or normalized in seen:
            continue
        seen.add(normalized)
        rows.append(token)
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _humanize(value: Any, *, title_case: bool = False) -> str:
    token = _string(value).replace("_", " ")
    return token.title() if title_case and token else token


def _display_list_text(items: Sequence[str]) -> str:
    cleaned = [item.strip() for item in items if item.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def _governance_present(payload: Mapping[str, Any]) -> bool:
    if "execution_governance_present" in payload:
        return bool(payload.get("execution_governance_present"))
    return any(
        _string(payload.get(key))
        for key in (
            "execution_governance_outcome",
            "execution_governance_mode",
            "execution_governance_next_move",
            "execution_governance_authoritative_lane",
            "execution_governance_blocker",
            "execution_governance_resume_token",
        )
    )


def build_latest_packet_summary(latest_packet: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one latest packet snapshot for shell-owned execution-governance views."""

    payload = dict(latest_packet) if isinstance(latest_packet, Mapping) else {}
    host_supports_native_spawn_known = "execution_governance_host_supports_native_spawn" in payload
    requires_more_consumer_context_known = "execution_governance_requires_more_consumer_context" in payload
    has_writable_targets_known = "execution_governance_has_writable_targets" in payload
    return {
        "present": _governance_present(payload),
        "workstream": _string(payload.get("workstream")) or _string(payload.get("session_id")) or "unknown",
        "state": _humanize(_string(payload.get("packet_state")) or "unknown", title_case=True) or "Unknown",
        "execution": _humanize(_string(payload.get("odylith_execution_profile")) or "unknown", title_case=True) or "Unknown",
        "mode": _humanize(
            _string(payload.get("odylith_execution_selection_mode"))
            or _string(payload.get("intent_mode"))
            or "unknown",
            title_case=True,
        )
        or "Unknown",
        "governance": _humanize(_string(payload.get("execution_governance_outcome")) or "unknown", title_case=True) or "Unknown",
        "governance_mode": _humanize(
            _string(payload.get("execution_governance_mode")) or "unknown",
            title_case=True,
        )
        or "Unknown",
        "current_phase": _string(payload.get("execution_governance_current_phase")),
        "last_successful_phase": _string(payload.get("execution_governance_last_successful_phase")),
        "next_move": _string(payload.get("execution_governance_next_move")) or "unknown",
        "blocker": _string(payload.get("execution_governance_blocker")),
        "closure": _humanize(_string(payload.get("execution_governance_closure")) or "unknown", title_case=True) or "Unknown",
        "wait_status": _humanize(_string(payload.get("execution_governance_wait_status")) or "none", title_case=True) or "None",
        "wait_detail": _string(payload.get("execution_governance_wait_detail")),
        "resume_token": _string(payload.get("execution_governance_resume_token")),
        "validation": _humanize(
            _string(payload.get("execution_governance_validation_archetype")) or "unknown",
            title_case=True,
        )
        or "Unknown",
        "validation_minimum_pass_count": _int(payload.get("execution_governance_validation_minimum_pass_count")),
        "validation_derived_from": _strings(payload.get("execution_governance_validation_derived_from")),
        "contradiction_count": _int(payload.get("execution_governance_contradiction_count")),
        "history_rule_count": _int(payload.get("execution_governance_history_rule_count")),
        "history_rule_hits": _strings(payload.get("execution_governance_history_rule_hits")),
        "pressure_signals": _strings(payload.get("execution_governance_pressure_signals")),
        "nearby_denial_actions": _strings(payload.get("execution_governance_nearby_denial_actions")),
        "authoritative_lane": _string(payload.get("execution_governance_authoritative_lane")),
        "host_family": _humanize(_string(payload.get("execution_governance_host_family")) or "unknown", title_case=True) or "Unknown",
        "model_family": _string(payload.get("execution_governance_model_family")),
        "host_supports_native_spawn_known": host_supports_native_spawn_known,
        "host_supports_native_spawn": bool(payload.get("execution_governance_host_supports_native_spawn")),
        "target_lane": _string(payload.get("execution_governance_target_lane")),
        "candidate_target_count": _int(payload.get("execution_governance_candidate_target_count")),
        "diagnostic_anchor_count": _int(payload.get("execution_governance_diagnostic_anchor_count")),
        "has_writable_targets_known": has_writable_targets_known,
        "has_writable_targets": bool(payload.get("execution_governance_has_writable_targets")),
        "requires_more_consumer_context_known": requires_more_consumer_context_known,
        "requires_more_consumer_context": bool(payload.get("execution_governance_requires_more_consumer_context")),
        "consumer_failover": _string(payload.get("execution_governance_consumer_failover")),
        "commentary_mode": _string(payload.get("execution_governance_commentary_mode")),
        "suppress_routing_receipts": bool(payload.get("execution_governance_suppress_routing_receipts")),
        "surface_fast_lane": bool(payload.get("execution_governance_surface_fast_lane")),
        "runtime_invalidated_by_step": _string(payload.get("execution_governance_runtime_invalidated_by_step")),
        "tokens": _int(payload.get("estimated_tokens")),
        "packet_strategy": _humanize(_string(payload.get("packet_strategy")) or "balanced", title_case=True) or "Balanced",
        "budget_mode": _humanize(_string(payload.get("budget_mode")) or "balanced", title_case=True) or "Balanced",
        "retrieval_focus": _humanize(_string(payload.get("retrieval_focus")) or "balanced", title_case=True) or "Balanced",
        "speed_mode": _humanize(_string(payload.get("speed_mode")) or "balanced", title_case=True) or "Balanced",
        "reliability": _humanize(_string(payload.get("reliability")) or "unknown", title_case=True) or "Unknown",
        "requires_reanchor": bool(payload.get("execution_governance_requires_reanchor")),
        "yield_state": _humanize(_string(payload.get("advised_yield_state")) or "unknown", title_case=True) or "Unknown",
        "alignment_state": _humanize(_string(payload.get("packet_alignment_state")) or "unknown", title_case=True) or "Unknown",
    }


def render_latest_packet_html(latest_packet: Mapping[str, Any]) -> str:
    """Render one bounded execution-governance status card for the shell drawer."""

    summary = dict(latest_packet) if isinstance(latest_packet, Mapping) else {}
    if not summary:
        return ""
    if not bool(summary.get("present")):
        return (
            '<article class="odylith-summary-card">'
            '<p class="odylith-command-card-kicker">Latest Governed Packet</p>'
            '<p class="odylith-command-card-title">No execution-governance packet posture recorded yet.</p>'
            '<p class="odylith-command-card-copy">The shell has no current admissibility, frontier, or resume signal to show for the latest routed slice.</p>'
            '</article>'
        )

    host_execution_label = "Unknown"
    if summary.get("host_supports_native_spawn_known"):
        host_execution_label = "Native spawn ready" if summary.get("host_supports_native_spawn") else "Serial host execution"
    consumer_scope_label = "Unknown"
    if summary.get("requires_more_consumer_context_known"):
        consumer_scope_label = (
            "More consumer context required"
            if summary.get("requires_more_consumer_context")
            else "Consumer scope grounded"
        )
    writable_label = "Unknown"
    if summary.get("has_writable_targets_known"):
        writable_label = "Writable targets present" if summary.get("has_writable_targets") else "No writable targets"

    why_this_move = [
        f"Authoritative lane `{summary['authoritative_lane']}`." if summary.get("authoritative_lane") else "",
        f"Current phase `{summary['current_phase']}`." if summary.get("current_phase") else "",
        (
            "Derived from "
            + _display_list_text([f"`{token}`" for token in summary.get("validation_derived_from", [])])
            + "."
        )
        if summary.get("validation_derived_from")
        else "",
        (
            f"Minimum validation pass count {summary['validation_minimum_pass_count']}."
            if summary.get("validation_minimum_pass_count")
            else ""
        ),
    ]
    pressure_rows = [
        f"Active blocker: {summary['blocker']}." if summary.get("blocker") else "",
        f"Waiting on {summary['wait_status']}." if summary.get("wait_status") not in {"", "None"} else "",
        f"Wait detail: {summary['wait_detail']}." if summary.get("wait_detail") else "",
        (
            f"Contradictions {summary['contradiction_count']}."
            if summary.get("contradiction_count")
            else ""
        ),
        (
            "History blockers: "
            + _display_list_text([f"`{token}`" for token in summary.get("history_rule_hits", [])])
            + "."
        )
        if summary.get("history_rule_hits")
        else "",
        (
            "Pressure signals: "
            + _display_list_text([f"`{token}`" for token in summary.get("pressure_signals", [])])
            + "."
        )
        if summary.get("pressure_signals")
        else "",
        (
            f"Runtime invalidated by `{summary['runtime_invalidated_by_step']}`."
            if summary.get("runtime_invalidated_by_step")
            else ""
        ),
    ]
    nearby_denials = [
        f"Prefer `{token}` only after the current frontier changes."
        for token in summary.get("nearby_denial_actions", [])
    ]
    consumer_rows = [
        f"Target lane `{summary['target_lane']}`." if summary.get("target_lane") else "",
        (
            f"Resume via `{summary['resume_token']}`."
            if summary.get("resume_token")
            else ""
        ),
        (
            f"Consumer failover `{summary['consumer_failover']}`."
            if summary.get("consumer_failover")
            else ""
        ),
        (
            f"Candidate targets {summary['candidate_target_count']} · anchors {summary['diagnostic_anchor_count']}."
            if summary.get("candidate_target_count") or summary.get("diagnostic_anchor_count")
            else ""
        ),
        f"{consumer_scope_label}.",
        f"{writable_label}.",
        (
            f"Commentary mode `{summary['commentary_mode']}`."
            if summary.get("commentary_mode")
            else ""
        ),
    ]
    chips = (
        ("Outcome", _string(summary.get("governance")) or "Unknown"),
        ("Mode", _string(summary.get("governance_mode")) or "Unknown"),
        ("Closure", _string(summary.get("closure")) or "Unknown"),
        ("Validation", _string(summary.get("validation")) or "Unknown"),
        ("Host", _string(summary.get("host_family")) or "Unknown"),
        ("Execution", host_execution_label),
        ("Wait", _string(summary.get("wait_status")) or "None"),
        ("Re-anchor", "Required" if summary.get("requires_reanchor") else "Not required"),
    )
    chip_html = "".join(
        (
            '<span class="odylith-inline-metric odylith-pair-chip">'
            f'<span class="odylith-pair-label">{html.escape(label)}</span>'
            f'<span class="odylith-pair-value">{html.escape(value)}</span>'
            '</span>'
        )
        for label, value in chips
        if value
    )

    def _list_html(items: Sequence[str], *, empty_text: str) -> str:
        rows = [item for item in items if _string(item)]
        if not rows:
            rows = [empty_text]
        return '<ul class="odylith-signal-list">' + "".join(f"<li>{html.escape(row)}</li>" for row in rows) + "</ul>"

    title = f"{summary.get('governance', 'Unknown')} · {summary.get('governance_mode', 'Unknown')}"
    copy = (
        f"Next move `{summary['next_move']}` for `{summary['workstream']}`."
        if summary.get("next_move")
        else f"Governed packet posture for `{summary['workstream']}`."
    )
    if summary.get("last_successful_phase"):
        copy += f" Last success `{summary['last_successful_phase']}`."
    return (
        '<article class="odylith-summary-card">'
        '<p class="odylith-command-card-kicker">Latest Governed Packet</p>'
        f'<p class="odylith-command-card-title">{html.escape(title)}</p>'
        f'<p class="odylith-command-card-copy">{html.escape(copy)}</p>'
        f'<div class="odylith-inline-metric-row">{chip_html}</div>'
        '<div class="odylith-summary-section">'
        '<p class="odylith-summary-section-title">Why This Move</p>'
        + _list_html(why_this_move, empty_text="No explicit derivation reasons were recorded.")
        + '</div>'
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Pressure And Blockers</p>'
        + _list_html(pressure_rows, empty_text="No execution pressure or blocker is currently recorded.")
        + '</div>'
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Nearby Denied Moves</p>'
        + _list_html(nearby_denials, empty_text="No nearby denied moves are currently recorded.")
        + '</div>'
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Targeting And Resume</p>'
        + _list_html(consumer_rows, empty_text="No target or resume metadata is currently recorded.")
        + '</div>'
        + '</article>'
    )
