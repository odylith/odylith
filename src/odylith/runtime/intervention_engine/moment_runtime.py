from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine.contract import GovernanceFact
from odylith.runtime.intervention_engine.contract import ObservationEnvelope


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _has_refs(fact: GovernanceFact) -> bool:
    return bool(fact.refs)


def _fact_kind(fact: GovernanceFact) -> str:
    return _normalize_token(fact.kind)


def _clamp(value: int, *, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def _continuity_score(*, lookup: Mapping[str, Any]) -> int:
    score = 0
    if lookup.get("workstream_ids"):
        score += 34
    if lookup.get("component_ids"):
        score += 26
    if lookup.get("diagram_refs"):
        score += 18
    if lookup.get("bug_ids"):
        score += 22
    return _clamp(score)


def _governance_readiness(
    *,
    observation: ObservationEnvelope,
    signal_profile: Mapping[str, Any],
    evidence_classes: Sequence[str],
    continuity: int,
) -> int:
    score = continuity
    score += min(len(evidence_classes), 4) * 11
    if signal_profile.get("has_direct_refs"):
        score += 18
    if observation.changed_paths:
        score += 18
    if signal_profile.get("has_governance_hints"):
        score += 10
    if signal_profile.get("has_topology_hints"):
        score += 8
    if signal_profile.get("has_bug_hints"):
        score += 6
    return _clamp(score)


def _novelty_score(
    *,
    fact: GovernanceFact,
    continuity: int,
    signal_profile: Mapping[str, Any],
    observation: ObservationEnvelope,
) -> int:
    kind = _fact_kind(fact)
    score = 32 if continuity <= 0 else 16
    if kind == "capture_opportunity":
        score += 18
    if kind == "topology":
        score += 12
    if kind == "invariant":
        score += 10
    if observation.changed_paths:
        score += 6
    if signal_profile.get("has_direct_refs"):
        score -= 8
    return _clamp(score)


def _urgency_score(*, fact: GovernanceFact, signal_profile: Mapping[str, Any]) -> int:
    kind = _fact_kind(fact)
    score = 38
    if kind == "invariant":
        score += 42
    elif kind == "history":
        score += 26
    elif kind == "topology":
        score += 22
    elif kind == "governance_truth":
        score += 18
    elif kind == "capture_opportunity":
        score += 14
    if signal_profile.get("has_bug_hints") and kind in {"history", "invariant"}:
        score += 12
    return _clamp(score)


def _fact_score(
    *,
    fact: GovernanceFact,
    observation: ObservationEnvelope,
    signal_profile: Mapping[str, Any],
    lookup: Mapping[str, Any],
    evidence_classes: Sequence[str],
    session_memory: Mapping[str, Any],
) -> int:
    kind = _fact_kind(fact)
    continuity = _continuity_score(lookup=lookup)
    score = int(fact.priority)
    score += min(len(evidence_classes), 4) * 7
    if _has_refs(fact):
        score += 10
    if _normalize_string(fact.detail):
        score += 4
    if observation.changed_paths and _has_refs(fact):
        score += 8
    if observation.assistant_summary:
        score += 4
    if kind == "invariant":
        score += 18
    if kind == "history" and signal_profile.get("has_bug_hints"):
        score += 16
    if kind == "topology" and signal_profile.get("has_topology_hints"):
        score += 14
    if kind == "governance_truth" and continuity > 0:
        score += 16
    if kind == "capture_opportunity":
        score += 8 if continuity <= 0 else -10
    score += _urgency_score(fact=fact, signal_profile=signal_profile) // 6
    score += _novelty_score(
        fact=fact,
        continuity=continuity,
        signal_profile=signal_profile,
        observation=observation,
    ) // 8
    score += int(signal_profile.get("session_escalation_bonus") or 0)
    score -= int(signal_profile.get("session_repeat_penalty") or 0)
    if kind in {
        _normalize_token(token)
        for token in session_memory.get("recent_moment_kinds", [])
        if _normalize_string(token)
    }:
        score -= 4
    return _clamp(score)


def _support_score(
    *,
    fact: GovernanceFact,
    primary: GovernanceFact,
    observation: ObservationEnvelope,
    signal_profile: Mapping[str, Any],
    lookup: Mapping[str, Any],
    evidence_classes: Sequence[str],
    session_memory: Mapping[str, Any],
) -> int:
    if _fact_kind(fact) == _fact_kind(primary):
        return -1
    score = _fact_score(
        fact=fact,
        observation=observation,
        signal_profile=signal_profile,
        lookup=lookup,
        evidence_classes=evidence_classes,
        session_memory=session_memory,
    )
    if _fact_kind(primary) == "governance_truth" and _fact_kind(fact) in {"topology", "history", "invariant"}:
        score += 12
    if _fact_kind(primary) == "topology" and _fact_kind(fact) == "governance_truth":
        score += 10
    if _fact_kind(primary) == "history" and _fact_kind(fact) == "governance_truth":
        score += 8
    return _clamp(score)


def _moment_kind(*, primary: GovernanceFact, signal_profile: Mapping[str, Any], lookup: Mapping[str, Any]) -> str:
    kind = _fact_kind(primary)
    if kind == "invariant":
        return "guardrail"
    if kind == "history":
        return "recovery"
    if kind == "topology":
        return "boundary"
    if kind == "governance_truth":
        if lookup.get("workstream_ids") or lookup.get("component_ids"):
            return "continuation"
        return "ownership"
    if kind == "capture_opportunity":
        if signal_profile.get("has_topology_hints"):
            return "boundary"
        return "capture"
    return "insight"


def _ambient_label_kind(*, moment_kind: str, primary: GovernanceFact) -> str:
    if moment_kind == "guardrail":
        return "risks"
    if moment_kind == "recovery":
        return "history"
    if _fact_kind(primary) == "invariant":
        return "risks"
    if _fact_kind(primary) == "history":
        return "history"
    return "insight"


def select_moment(
    *,
    observation: ObservationEnvelope,
    facts: Sequence[GovernanceFact],
    signal_profile: Mapping[str, Any],
    lookup: Mapping[str, Any],
    evidence_classes: Sequence[str],
    session_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    memory = _mapping(session_memory)
    if not facts:
        return {
            "kind": "silent",
            "score": 0,
            "urgency": 0,
            "novelty": 0,
            "continuity": _continuity_score(lookup=lookup),
            "governance_readiness": 0,
            "proposal_readiness": 0,
            "primary_fact": {},
            "supporting_fact": {},
            "ambient_label_kind": "insight",
        }
    scored = sorted(
        (
            (
                _fact_score(
                    fact=fact,
                    observation=observation,
                    signal_profile=signal_profile,
                    lookup=lookup,
                    evidence_classes=evidence_classes,
                    session_memory=memory,
                ),
                fact,
            )
            for fact in facts
        ),
        key=lambda row: row[0],
        reverse=True,
    )
    primary_score, primary = scored[0]
    supporting_score = -1
    supporting: GovernanceFact | None = None
    for _score, fact in scored[1:]:
        score = _support_score(
            fact=fact,
            primary=primary,
            observation=observation,
            signal_profile=signal_profile,
            lookup=lookup,
            evidence_classes=evidence_classes,
            session_memory=memory,
        )
        if score > supporting_score:
            supporting_score = score
            supporting = fact
    continuity = _continuity_score(lookup=lookup)
    governance_readiness = _governance_readiness(
        observation=observation,
        signal_profile=signal_profile,
        evidence_classes=evidence_classes,
        continuity=continuity,
    )
    novelty = _novelty_score(
        fact=primary,
        continuity=continuity,
        signal_profile=signal_profile,
        observation=observation,
    )
    urgency = _urgency_score(fact=primary, signal_profile=signal_profile)
    kind = _moment_kind(primary=primary, signal_profile=signal_profile, lookup=lookup)
    support_bonus = 6 if supporting is not None and supporting_score >= 78 else 0
    score = _clamp(primary_score + support_bonus + (governance_readiness // 8))
    proposal_readiness = _clamp(
        governance_readiness
        + (14 if observation.changed_paths else 0)
        + (10 if continuity >= 40 else 0)
        + (8 if signal_profile.get("has_direct_refs") else 0)
        + int(signal_profile.get("session_escalation_bonus") or 0)
        - max(0, int(signal_profile.get("session_repeat_penalty") or 0) - 8)
        - (18 if observation.turn_phase in {"prompt_submit", "userpromptsubmit"} else 0)
    )
    return {
        "kind": kind,
        "score": score,
        "urgency": urgency,
        "novelty": novelty,
        "continuity": continuity,
        "governance_readiness": governance_readiness,
        "proposal_readiness": proposal_readiness,
        "primary_fact": primary.as_dict(),
        "supporting_fact": supporting.as_dict() if supporting is not None and supporting_score >= 78 else {},
        "ambient_label_kind": _ambient_label_kind(moment_kind=kind, primary=primary),
    }


def candidate_stage_without_dedupe(
    *,
    observation: ObservationEnvelope,
    evidence_classes: Sequence[str],
    facts: Sequence[GovernanceFact],
    moment: Mapping[str, Any],
) -> str:
    if not facts:
        return "silent"
    score = int(moment.get("score") or 0)
    readiness = int(moment.get("governance_readiness") or 0)
    urgency = int(moment.get("urgency") or 0)
    evidence_count = len(list(evidence_classes))
    phase = _normalize_token(observation.turn_phase)
    if score < 56:
        return "silent"
    if phase in {"prompt_submit", "userpromptsubmit"}:
        return "teaser"
    if evidence_count >= 2 and (score >= 82 or (urgency >= 80 and readiness >= 66)):
        return "card"
    if score >= 62:
        return "teaser"
    return "silent"
