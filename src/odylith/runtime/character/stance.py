from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.character.contract import STANCE_FACETS


def infer_stance_vector(
    *,
    pressure: Mapping[str, Any],
    hard_law_results: Sequence[Mapping[str, Any]],
    lane: str = "",
) -> dict[str, float]:
    features = dict(pressure.get("features", {})) if isinstance(pressure.get("features"), Mapping) else {}
    violations = {str(row.get("law_id", "")).strip() for row in hard_law_results if row.get("status") == "violated"}
    vector = {facet: 0.2 for facet in STANCE_FACETS}
    if features.get("ambiguity"):
        vector["attention"] += 0.55
    if violations:
        vector["restraint"] += 0.55
        vector["accountability"] += 0.35
    if features.get("proof_risk") or "fresh_proof_completion" in violations:
        vector["honesty"] += 0.6
    if features.get("delegation_risk") or "bounded_delegation" in violations:
        vector["coordination"] += 0.55
    if features.get("recurrence"):
        vector["memory"] += 0.55
        vector["judgment"] += 0.35
    if features.get("visibility_risk"):
        vector["voice"] += 0.45
    if features.get("benchmark_claim_risk"):
        vector["accountability"] += 0.45
    if features.get("systemic_integration_risk"):
        vector["attention"] += 0.25
        vector["judgment"] += 0.3
        vector["accountability"] += 0.25
    if features.get("voice_template_risk"):
        vector["voice"] += 0.35
        vector["judgment"] += 0.15
    if features.get("learning_feedback_risk"):
        vector["memory"] += 0.3
        vector["judgment"] += 0.2
    if str(lane).strip() == "consumer" or features.get("lane_boundary_risk"):
        vector["restraint"] += 0.25
    if not violations and pressure.get("uncertainty", 1.0) < 0.7:
        vector["agency"] += 0.55
    if features.get("urgency"):
        vector["agency"] += 0.2
        vector["attention"] += 0.15
    return {key: round(min(1.0, max(0.0, value)), 2) for key, value in vector.items()}
