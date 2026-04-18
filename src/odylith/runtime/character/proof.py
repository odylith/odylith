"""Proof helpers for the Odylith character layer."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


_PROOF_BY_LAW: dict[str, str] = {
    "cli_first_governed_truth": "governed_writer_required",
    "fresh_proof_completion": "fresh_validation_required",
    "visible_intervention_proof": "visible_intervention_proof_required",
    "queue_non_adoption": "operator_authorization_required",
    "bounded_delegation": "bounded_delegation_contract_required",
    "benchmark_public_claim": "matched_benchmark_proof_required",
    "consumer_mutation_guard": "operator_authorization_required",
    "explicit_model_credit": "zero_credit_hot_path_required",
    "supported_host_lane": "supported_host_lane_required",
}


_PRIORITY: tuple[str, ...] = (
    "benchmark_public_claim",
    "fresh_proof_completion",
    "visible_intervention_proof",
    "explicit_model_credit",
    "supported_host_lane",
    "consumer_mutation_guard",
    "bounded_delegation",
    "cli_first_governed_truth",
    "queue_non_adoption",
)


def proof_obligation_for_decision(
    *,
    violations: Sequence[Mapping[str, Any]],
    pressure: Mapping[str, Any],
) -> str:
    law_ids = {str(row.get("law_id", "")).strip() for row in violations if str(row.get("law_id", "")).strip()}
    for law_id in _PRIORITY:
        if law_id in law_ids:
            return _PROOF_BY_LAW[law_id]
    features = pressure.get("features")
    if isinstance(features, Mapping):
        if bool(features.get("proof_execution")):
            return "keep_claims_evidence_backed"
        if bool(features.get("benchmark_claim_risk")):
            return "matched_benchmark_proof_required"
        if bool(features.get("visibility_risk")):
            return "visible_intervention_proof_required"
        if bool(features.get("proof_risk")):
            return "fresh_validation_required"
        if bool(features.get("ambiguity")) and float(pressure.get("uncertainty", 1.0) or 1.0) >= 0.75:
            return "smallest_relevant_truth_required"
    return "keep_claims_evidence_backed"
