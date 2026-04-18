"""Pressure helpers for the Odylith character layer."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.character.signals import extract_intent_signals

_ARCHETYPE_BY_FEATURE: dict[str, str] = {
    "ambiguity": "ambiguous_scope",
    "governed_truth_risk": "governed_truth_shortcut",
    "completion_claim": "premature_completion_claim",
    "delegation_risk": "broad_delegation",
    "visibility_risk": "visibility_overclaim",
    "queue_risk": "queue_adoption",
    "recurrence": "repeated_failure",
    "lane_boundary_risk": "consumer_mutation_risk",
    "benchmark_claim_risk": "benchmark_claim_without_proof",
    "credit_risk": "host_model_credit_risk",
}


def observe_pressure(intent: str, *, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    signals = extract_intent_signals(intent, evidence=evidence)
    text = str(signals.get("text", "")).strip()
    features = dict(signals.get("features", {})) if isinstance(signals.get("features"), Mapping) else {}
    matches = [
        archetype
        for feature, archetype in _ARCHETYPE_BY_FEATURE.items()
        if features.get(feature)
    ]

    true_count = sum(1 for value in features.values() if value)
    unknown_features = {
        key: value
        for key, value in features.items()
        if value and key not in _ARCHETYPE_BY_FEATURE
    }
    uncertainty = 0.15 if matches else 0.55
    if unknown_features and matches:
        uncertainty = max(uncertainty, 0.35)
    if unknown_features and not matches:
        uncertainty = 0.65
    if features["ambiguity"] and true_count == 1 and len(text.split()) < 6:
        uncertainty = 0.8
    if true_count >= 4:
        uncertainty += 0.15
    if not text:
        uncertainty = 0.9
    uncertainty = min(0.95, round(uncertainty, 2))
    observations = [key for key, value in features.items() if value]
    return {
        "pressure_observations": observations,
        "known_archetype_matches": matches,
        "unknown_pressure_features": unknown_features,
        "features": features,
        "uncertainty": uncertainty,
    }
