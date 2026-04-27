"""Value Engine Types helpers for the Odylith intervention engine layer."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine import visibility_contract


VALUE_ENGINE_VERSION = "intervention-value-engine.v1"
RUNTIME_POSTURE = "deterministic_utility_v1"
CORPUS_PATH = Path("odylith/runtime/source/intervention-value-adjudication-corpus.v1.json")
VISIBLE_LABELS: tuple[str, ...] = ("risks", "history", "insight", "observation", "proposal")
POSITIVE_VALUE_WEIGHTS = {
    "materiality": 0.30,
    "actionability": 0.22,
    "novelty": 0.14,
    "timing_relevance": 0.14,
    "user_need": 0.12,
    "visibility_need": 0.08,
}
SELECTION_FLOOR = 0.62
URGENT_RISK_FLOOR = 0.54
MAX_ENUMERATED_OPTIONS = 12
MAX_LIVE_BLOCKS = 4
MAX_AMBIENT_BLOCKS = 3
MIN_PUBLISHABLE_NON_SYNTHETIC_CASES = 120
MIN_PUBLISHABLE_POSITIVE_PER_LABEL = 15
MIN_PUBLISHABLE_NO_OUTPUT_CASES = 30
MIN_PUBLISHABLE_DUPLICATE_CASES = 20
MIN_PUBLISHABLE_VISIBILITY_CASES = 10


_normalize_string = visibility_contract.normalize_string
_normalize_block_string = visibility_contract.normalize_block_string
_normalize_token = visibility_contract.normalize_token


def _normalize_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float, *, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


_mapping = visibility_contract.mapping_copy


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _string_list(value: Any) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for item in _sequence(value):
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    token = _normalize_string(value) if not rows and isinstance(value, str) else ""
    return [token] if token else rows


def _fingerprint(value: Any) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        encoded = repr(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    return f"{prefix}:{_fingerprint(payload)}"


@dataclass(frozen=True)
class SignalEvidence:
    source_kind: str
    source_id: str = ""
    source_path: str = ""
    source_fingerprint: str = ""
    freshness: str = "current"
    confidence: float = 0.0
    excerpt: str = ""
    evidence_class: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_kind": _normalize_token(self.source_kind),
            "source_id": _normalize_string(self.source_id),
            "source_path": _normalize_string(self.source_path),
            "source_fingerprint": _normalize_string(self.source_fingerprint),
            "freshness": _normalize_token(self.freshness) or "current",
            "confidence": round(_clamp(self.confidence), 4),
            "excerpt": _normalize_block_string(self.excerpt),
            "evidence_class": _normalize_token(self.evidence_class),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "SignalEvidence":
        payload = _mapping(value)
        return cls(
            source_kind=_normalize_token(payload.get("source_kind")) or "runtime",
            source_id=_normalize_string(payload.get("source_id")),
            source_path=_normalize_string(payload.get("source_path")),
            source_fingerprint=_normalize_string(payload.get("source_fingerprint")),
            freshness=_normalize_token(payload.get("freshness")) or "current",
            confidence=_clamp(_normalize_float(payload.get("confidence"))),
            excerpt=_normalize_block_string(payload.get("excerpt")),
            evidence_class=_normalize_token(payload.get("evidence_class")),
        )


@dataclass(frozen=True)
class SignalProposition:
    proposition_id: str
    claim_text: str
    proposition_kind: str
    support_state: str = "supported"
    anchor_refs: tuple[dict[str, str], ...] = ()
    semantic_signature: tuple[str, ...] = ()
    duplicate_key: str = ""
    freshness_state: str = "current"
    evidence: tuple[SignalEvidence, ...] = ()
    source_fingerprints: dict[str, str] | None = None

    def normalized_kind(self) -> str:
        return _normalize_token(self.proposition_kind)

    def normalized_support_state(self) -> str:
        return _normalize_token(self.support_state) or "supported"

    def duplicate_group(self) -> str:
        if self.duplicate_key:
            return _normalize_string(self.duplicate_key)
        if self.semantic_signature:
            return "semantic:" + "|".join(self.semantic_signature[:6])
        return _stable_id("proposition", {"claim": self.claim_text, "kind": self.proposition_kind})

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposition_id": _normalize_string(self.proposition_id),
            "claim_text": _normalize_block_string(self.claim_text),
            "proposition_kind": self.normalized_kind(),
            "support_state": self.normalized_support_state(),
            "anchor_refs": [dict(row) for row in self.anchor_refs],
            "semantic_signature": list(self.semantic_signature),
            "duplicate_key": self.duplicate_group(),
            "freshness_state": _normalize_token(self.freshness_state) or "current",
            "evidence": [row.as_dict() for row in self.evidence],
            "source_fingerprints": dict(self.source_fingerprints or {}),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "SignalProposition":
        payload = _mapping(value)
        evidence = tuple(
            SignalEvidence.from_mapping(row)
            for row in _sequence(payload.get("evidence"))
            if isinstance(row, Mapping)
        )
        anchor_refs = tuple(
            {
                "kind": _normalize_token(_mapping(row).get("kind")),
                "id": _normalize_string(_mapping(row).get("id")),
                "path": _normalize_string(_mapping(row).get("path")),
                "label": _normalize_string(_mapping(row).get("label")),
            }
            for row in _sequence(payload.get("anchor_refs"))
            if isinstance(row, Mapping)
        )
        claim = _normalize_block_string(payload.get("claim_text"))
        kind = _normalize_token(payload.get("proposition_kind")) or _normalize_token(payload.get("kind")) or "insight"
        proposition_id = _normalize_string(payload.get("proposition_id")) or _stable_id(
            "proposition",
            {"claim": claim, "kind": kind, "anchors": anchor_refs},
        )
        return cls(
            proposition_id=proposition_id,
            claim_text=claim,
            proposition_kind=kind,
            support_state=_normalize_token(payload.get("support_state")) or "supported",
            anchor_refs=anchor_refs,
            semantic_signature=tuple(_string_list(payload.get("semantic_signature"))),
            duplicate_key=_normalize_string(payload.get("duplicate_key")),
            freshness_state=_normalize_token(payload.get("freshness_state")) or "current",
            evidence=evidence,
            source_fingerprints=_mapping(payload.get("source_fingerprints")),
        )


@dataclass(frozen=True)
class InterventionValueFeatures:
    correctness_confidence: float = 0.0
    materiality: float = 0.0
    actionability: float = 0.0
    novelty: float = 0.0
    timing_relevance: float = 0.0
    user_need: float = 0.0
    visibility_need: float = 0.0
    interruption_cost: float = 0.0
    redundancy_cost: float = 0.0
    uncertainty_penalty: float = 0.0
    brand_risk: float = 0.0

    def normalized(self) -> "InterventionValueFeatures":
        return InterventionValueFeatures(
            correctness_confidence=_clamp(self.correctness_confidence),
            materiality=_clamp(self.materiality),
            actionability=_clamp(self.actionability),
            novelty=_clamp(self.novelty),
            timing_relevance=_clamp(self.timing_relevance),
            user_need=_clamp(self.user_need),
            visibility_need=_clamp(self.visibility_need),
            interruption_cost=_clamp(self.interruption_cost),
            redundancy_cost=_clamp(self.redundancy_cost),
            uncertainty_penalty=_clamp(self.uncertainty_penalty),
            brand_risk=_clamp(self.brand_risk),
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "correctness_confidence": round(_clamp(self.correctness_confidence), 4),
            "materiality": round(_clamp(self.materiality), 4),
            "actionability": round(_clamp(self.actionability), 4),
            "novelty": round(_clamp(self.novelty), 4),
            "timing_relevance": round(_clamp(self.timing_relevance), 4),
            "user_need": round(_clamp(self.user_need), 4),
            "visibility_need": round(_clamp(self.visibility_need), 4),
            "interruption_cost": round(_clamp(self.interruption_cost), 4),
            "redundancy_cost": round(_clamp(self.redundancy_cost), 4),
            "uncertainty_penalty": round(_clamp(self.uncertainty_penalty), 4),
            "brand_risk": round(_clamp(self.brand_risk), 4),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "InterventionValueFeatures":
        payload = _mapping(value)
        if "base_score" in payload or "evidence_quality" in payload:
            return cls(
                correctness_confidence=max(
                    _normalize_float(payload.get("evidence_quality")),
                    _normalize_float(payload.get("base_score")),
                ),
                materiality=_normalize_float(payload.get("fact_priority")),
                actionability=_normalize_float(payload.get("actionability")),
                novelty=_normalize_float(payload.get("novelty")),
                timing_relevance=max(
                    _normalize_float(payload.get("anchor_strength")),
                    _normalize_float(payload.get("base_score")),
                ),
                user_need=_normalize_float(payload.get("fact_priority")),
                visibility_need=_normalize_float(payload.get("visibility_need")),
                interruption_cost=0.08,
                redundancy_cost=0.0,
                uncertainty_penalty=max(0.0, 1.0 - _normalize_float(payload.get("evidence_quality"))) * 0.12,
                brand_risk=max(0.0, 1.0 - _normalize_float(payload.get("evidence_quality"))) * 0.08,
            ).normalized()
        return cls(
            correctness_confidence=_normalize_float(payload.get("correctness_confidence")),
            materiality=_normalize_float(payload.get("materiality")),
            actionability=_normalize_float(payload.get("actionability")),
            novelty=_normalize_float(payload.get("novelty")),
            timing_relevance=_normalize_float(payload.get("timing_relevance")),
            user_need=_normalize_float(payload.get("user_need")),
            visibility_need=_normalize_float(payload.get("visibility_need")),
            interruption_cost=_normalize_float(payload.get("interruption_cost")),
            redundancy_cost=_normalize_float(payload.get("redundancy_cost")),
            uncertainty_penalty=_normalize_float(payload.get("uncertainty_penalty")),
            brand_risk=_normalize_float(payload.get("brand_risk")),
        ).normalized()


@dataclass(frozen=True)
class VisibleInterventionOption:
    option_id: str
    proposition: SignalProposition
    proposed_label: str
    block_kind: str
    markdown_text: str
    plain_text: str = ""
    proof_required: bool = False
    action_payload: dict[str, Any] | None = None
    features: InterventionValueFeatures = InterventionValueFeatures()
    metadata: dict[str, Any] | None = None

    def normalized_label(self) -> str:
        return _normalize_token(self.proposed_label)

    def normalized_kind(self) -> str:
        return _normalize_token(self.block_kind) or "ambient"

    def text(self) -> str:
        return _normalize_block_string(self.plain_text or self.markdown_text)

    def duplicate_group(self) -> str:
        return self.proposition.duplicate_group()

    def with_value(
        self,
        *,
        selected_block_set_id: str = "",
        suppressed_reason: str = "",
        net_value: float | None = None,
    ) -> dict[str, Any]:
        value = option_net_value(self) if net_value is None else net_value
        label = self.normalized_label()
        kind = self.normalized_kind()
        duplicate = self.duplicate_group()
        support_state = self.proposition.normalized_support_state()
        feature_payload = self.features.normalized().as_dict()
        return {
            "option_id": self.option_id,
            "candidate_id": self.option_id,
            "proposition_id": self.proposition.proposition_id,
            "label": label,
            "proposed_label": label,
            "block_kind": kind,
            "markdown_text": _normalize_block_string(self.markdown_text),
            "plain_text": _normalize_block_string(self.plain_text),
            "duplicate_group": duplicate,
            "supported": support_state == "supported",
            "support_state": support_state,
            "freshness_state": _normalize_token(self.proposition.freshness_state) or "current",
            "proof_required": bool(self.proof_required),
            "action_payload": dict(self.action_payload or {}),
            "proposition": self.proposition.as_dict(),
            "value_features": feature_payload,
            "feature_vector": feature_payload,
            "metadata": dict(self.metadata or {}),
            "net_value": round(value, 4),
            "usefulness_score": round(value, 4),
            "visibility_priority": round(feature_payload["visibility_need"], 4),
            "value_engine_version": VALUE_ENGINE_VERSION,
            "runtime_posture": RUNTIME_POSTURE,
            "selected_block_set_id": selected_block_set_id,
            "suppressed_reason": suppressed_reason,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "VisibleInterventionOption":
        payload = _mapping(value)
        label = _normalize_token(payload.get("proposed_label") or payload.get("label")) or "insight"
        proposition_payload = _mapping(payload.get("proposition"))
        if not proposition_payload:
            proposition_payload = {
                "proposition_id": _normalize_string(payload.get("proposition_id"))
                or _normalize_string(payload.get("candidate_id")),
                "claim_text": _normalize_block_string(payload.get("plain_text") or payload.get("markdown_text")),
                "proposition_kind": label,
                "support_state": "supported" if bool(payload.get("supported", True)) else "unsupported",
                "duplicate_key": _normalize_string(payload.get("duplicate_group")),
                "semantic_signature": _string_list(payload.get("semantic_signature")),
                "anchor_refs": _sequence(payload.get("anchor_refs") or payload.get("refs")),
            }
        proposition = SignalProposition.from_mapping(proposition_payload)
        option_id = _normalize_string(payload.get("option_id")) or _normalize_string(payload.get("candidate_id")) or _stable_id(
            "option",
            {"label": label, "proposition": proposition.as_dict()},
        )
        features = InterventionValueFeatures.from_mapping(
            _mapping(payload.get("value_features")) or _mapping(payload.get("feature_vector"))
        )
        return cls(
            option_id=option_id,
            proposition=proposition,
            proposed_label=label,
            block_kind=_normalize_token(payload.get("block_kind")) or "ambient",
            markdown_text=_normalize_block_string(payload.get("markdown_text")),
            plain_text=_normalize_block_string(payload.get("plain_text")),
            proof_required=bool(payload.get("proof_required", False)),
            action_payload=_mapping(payload.get("action_payload")),
            features=features,
            metadata=_mapping(payload.get("metadata")),
        )


@dataclass(frozen=True)
class VisibleSignalSelectionDecision:
    selected_candidates: list[dict[str, Any]]
    suppressed_candidates: list[dict[str, Any]]
    no_output_reason: str
    selected_block_set_id: str
    value_engine_version: str
    runtime_posture: str
    metric_summary: dict[str, Any]
    decision_log: dict[str, Any] | None = None

    def selected_ids(self) -> set[str]:
        return {
            _normalize_string(row.get("candidate_id") or row.get("option_id"))
            for row in self.selected_candidates
            if _normalize_string(row.get("candidate_id") or row.get("option_id"))
        }

    def selected_labels(self) -> list[str]:
        return [
            _normalize_token(row.get("label") or row.get("proposed_label"))
            for row in self.selected_candidates
            if _normalize_token(row.get("label") or row.get("proposed_label"))
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_candidates": [dict(row) for row in self.selected_candidates],
            "suppressed_candidates": [dict(row) for row in self.suppressed_candidates],
            "no_output_reason": self.no_output_reason,
            "selected_block_set_id": self.selected_block_set_id,
            "value_engine_version": self.value_engine_version,
            "runtime_posture": self.runtime_posture,
            "metric_summary": dict(self.metric_summary),
            "decision_log": dict(self.decision_log or {}),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "VisibleSignalSelectionDecision":
        payload = _mapping(value)
        return cls(
            selected_candidates=[
                dict(row)
                for row in _sequence(payload.get("selected_candidates"))
                if isinstance(row, Mapping)
            ],
            suppressed_candidates=[
                dict(row)
                for row in _sequence(payload.get("suppressed_candidates"))
                if isinstance(row, Mapping)
            ],
            no_output_reason=_normalize_string(payload.get("no_output_reason")),
            selected_block_set_id=_normalize_string(payload.get("selected_block_set_id")),
            value_engine_version=_normalize_string(payload.get("value_engine_version")) or VALUE_ENGINE_VERSION,
            runtime_posture=_normalize_string(payload.get("runtime_posture")) or RUNTIME_POSTURE,
            metric_summary=_mapping(payload.get("metric_summary")),
            decision_log=_mapping(payload.get("decision_log")),
        )


def weighted_positive_value(features: InterventionValueFeatures) -> float:
    row = features.normalized()
    return _clamp(
        (POSITIVE_VALUE_WEIGHTS["materiality"] * row.materiality)
        + (POSITIVE_VALUE_WEIGHTS["actionability"] * row.actionability)
        + (POSITIVE_VALUE_WEIGHTS["novelty"] * row.novelty)
        + (POSITIVE_VALUE_WEIGHTS["timing_relevance"] * row.timing_relevance)
        + (POSITIVE_VALUE_WEIGHTS["user_need"] * row.user_need)
        + (POSITIVE_VALUE_WEIGHTS["visibility_need"] * row.visibility_need)
    )


def proposition_evidence_confidence(proposition: SignalProposition) -> float:
    current_freshnesses = {"", "current", "fresh", "live"}
    confidence = max(
        (
            _clamp(row.confidence)
            for row in proposition.evidence
            if (_normalize_token(row.freshness) or "current") in current_freshnesses
        ),
        default=0.0,
    )
    has_anchor_ref = any(
        _normalize_string(row.get("id") or row.get("path") or row.get("label"))
        for row in proposition.anchor_refs
    )
    has_source_fingerprint = any(
        _normalize_string(key) and _normalize_string(value)
        for key, value in (proposition.source_fingerprints or {}).items()
    )
    if has_anchor_ref:
        confidence = max(confidence, 0.90)
    if has_source_fingerprint:
        confidence = max(confidence, 0.86)
    return _clamp(confidence)


def option_net_value(option: VisibleInterventionOption) -> float:
    features = option.features.normalized()
    positive = weighted_positive_value(features)
    correctness_confidence = features.correctness_confidence
    evidence_confidence = proposition_evidence_confidence(option.proposition)
    if evidence_confidence:
        correctness_confidence = min(correctness_confidence, _clamp(evidence_confidence + 0.08))
    else:
        correctness_confidence = 0.0
    value = (
        correctness_confidence * positive
        - features.interruption_cost
        - features.redundancy_cost
        - features.uncertainty_penalty
        - features.brand_risk
    )
    return _clamp(value)
