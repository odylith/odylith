from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.character.contract import HARD_LAW_RECOVERY_ACTIONS


_ADAPTIVE_AFFORDANCES: tuple[tuple[str, str, str], ...] = (
    (
        "systemic_integration_risk",
        "check_platform_integration_contracts",
        "Inspect the connected Context, Execution, Memory, Intervention, Benchmark, and surface contracts before widening edits.",
    ),
    (
        "voice_template_risk",
        "inspect_voice_surfaces_without_scripted_copy",
        "Keep voice evidence-shaped and surface-owned instead of introducing fixed posture copy.",
    ),
    (
        "learning_feedback_risk",
        "inspect_learning_feedback_loop",
        "Check how pressure, proof, benchmark, Tribunal, and memory signals feed the next run.",
    ),
    (
        "recurrence",
        "inspect_learning_feedback_loop",
        "A repeated pattern should be routed through learning or Tribunal before becoming doctrine.",
    ),
    (
        "urgency",
        "make_small_admissible_change_then_validate",
        "Move through the smallest admissible local change, then prove it with fresh validation.",
    ),
)


def _append_unique(
    rows: list[dict[str, Any]],
    *,
    action: str,
    reason: str,
    pressure_feature: str = "",
    law_id: str = "",
) -> None:
    if any(str(row.get("action", "")).strip() == action for row in rows):
        return
    payload: dict[str, Any] = {
        "action": action,
        "rank": len(rows) + 1,
        "reason": reason,
    }
    if pressure_feature:
        payload["pressure_feature"] = pressure_feature
    if law_id:
        payload["law_id"] = law_id
    rows.append(payload)


def rank_affordances(
    *,
    pressure: Mapping[str, Any],
    hard_law_results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for row in hard_law_results:
        if row.get("status") != "violated":
            continue
        law_id = str(row.get("law_id", "")).strip()
        action = HARD_LAW_RECOVERY_ACTIONS.get(law_id, "re_anchor")
        _append_unique(
            ranked,
            action=action,
            reason=str(row.get("recovery", "")).strip(),
            law_id=law_id,
        )
    if not ranked and float(pressure.get("uncertainty", 1.0) or 1.0) >= 0.7:
        _append_unique(
            ranked,
            action="narrow_context_first",
            reason="Pressure is uncertain; gather the smallest relevant local truth before acting.",
        )
    features = dict(pressure.get("features", {})) if isinstance(pressure.get("features"), Mapping) else {}
    if not any(row.get("law_id") for row in ranked):
        for feature, action, reason in _ADAPTIVE_AFFORDANCES:
            if features.get(feature):
                _append_unique(
                    ranked,
                    action=action,
                    reason=reason,
                    pressure_feature=feature,
                )
    if not ranked:
        _append_unique(
            ranked,
            action="act_with_proof_obligation",
            reason="No hard law is violated; proceed locally and keep proof obligations explicit.",
        )
    return ranked
