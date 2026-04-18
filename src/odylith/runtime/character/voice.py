from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.character.contract import VISIBLE_INTERVENTION_LAWS


def intervention_candidate_for_decision(
    *,
    decision: str,
    pressure: Mapping[str, Any],
    violations: Sequence[Mapping[str, Any]],
    affordances: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    law_ids = [
        str(row.get("law_id", "")).strip()
        for row in violations
        if str(row.get("law_id", "")).strip()
    ]
    first_affordance = dict(affordances[0]) if affordances and isinstance(affordances[0], Mapping) else {}
    recovery_action = str(first_affordance.get("action", "")).strip()
    reason = str(first_affordance.get("reason", "")).strip()
    pressure_observations = [
        str(item).strip()
        for item in pressure.get("pressure_observations", [])
        if str(item).strip()
    ] if isinstance(pressure.get("pressure_observations"), list) else []
    high_signal = bool(recovery_action) and bool(set(law_ids) & VISIBLE_INTERVENTION_LAWS)
    visible = bool(high_signal and decision in {"block", "defer"})
    if not visible:
        return {
            "visible": False,
            "visibility": "silent",
            "style": "silent",
            "surface_owner": "intervention_engine",
            "render_policy": "passing_or_low_signal_checks_stay_quiet",
            "reason": "",
            "evidence": [],
            "recovery_action": recovery_action,
            "copy": "",
        }
    visibility = "blocker" if decision == "block" else "recovery_cue"
    return {
        "visible": True,
        "visibility": visibility,
        "style": "evidence_recovery",
        "surface_owner": "intervention_engine",
        "render_policy": "evidence_shaped_no_scripted_copy",
        "reason": reason,
        "evidence": [*law_ids[:4], *pressure_observations[:4]],
        "recovery_action": recovery_action,
        "requires_visible_proof": "visible_intervention_proof" in law_ids,
        "copy": "",
    }
