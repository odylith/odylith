from __future__ import annotations

from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine.value_engine_types import VisibleSignalSelectionDecision
from odylith.runtime.intervention_engine.value_engine_types import _mapping
from odylith.runtime.intervention_engine.value_engine_types import _normalize_string
from odylith.runtime.intervention_engine.value_engine_types import _normalize_token


def _compact_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    proposition = _mapping(candidate.get("proposition"))
    evidence_fingerprints: list[str] = []
    evidence_rows = proposition.get("evidence")
    if isinstance(evidence_rows, list):
        for evidence in evidence_rows:
            row = _mapping(evidence)
            fingerprint = (
                _normalize_string(row.get("source_fingerprint"))
                or _normalize_string(row.get("source_id"))
                or _normalize_string(row.get("source_path"))
            )
            if fingerprint and fingerprint not in evidence_fingerprints:
                evidence_fingerprints.append(fingerprint)
    for value in _mapping(proposition.get("source_fingerprints")).values():
        fingerprint = _normalize_string(value)
        if fingerprint and fingerprint not in evidence_fingerprints:
            evidence_fingerprints.append(fingerprint)
    return {
        "candidate_id": _normalize_string(candidate.get("candidate_id") or candidate.get("option_id")),
        "proposition_id": _normalize_string(candidate.get("proposition_id")),
        "label": _normalize_token(candidate.get("label") or candidate.get("proposed_label")),
        "block_kind": _normalize_token(candidate.get("block_kind")),
        "duplicate_group": _normalize_string(candidate.get("duplicate_group")),
        "semantic_signature": proposition.get("semantic_signature")
        if isinstance(proposition.get("semantic_signature"), list)
        else [],
        "evidence_fingerprints": evidence_fingerprints[:8],
        "feature_vector": _mapping(candidate.get("feature_vector") or candidate.get("value_features")),
        "net_value": candidate.get("net_value"),
        "suppressed_reason": _normalize_string(candidate.get("suppressed_reason")),
    }


def value_decision_event_metadata(
    *,
    decision: VisibleSignalSelectionDecision,
    delivery_channel: str,
    delivery_status: str,
    render_surface: str,
) -> dict[str, Any]:
    if not decision.selected_candidates and not decision.suppressed_candidates:
        return {}
    return {
        "value_engine_version": decision.value_engine_version,
        "runtime_posture": decision.runtime_posture,
        "selected_block_set_id": decision.selected_block_set_id,
        "value_decision": {
            "selected": [_compact_candidate(row) for row in decision.selected_candidates],
            "suppressed": [
                _compact_candidate(row)
                for row in decision.suppressed_candidates[:24]
            ],
            "no_output_reason": decision.no_output_reason,
            "metric_summary": dict(decision.metric_summary),
            "decision_log": dict(decision.decision_log or {}),
        },
        "visibility_proof": {
            "delivery_channel": _normalize_token(delivery_channel),
            "delivery_status": _normalize_token(delivery_status),
            "render_surface": _normalize_token(render_surface),
        },
    }


__all__ = ["value_decision_event_metadata"]
