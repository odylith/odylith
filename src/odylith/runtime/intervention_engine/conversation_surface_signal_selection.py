"""Ambient signal and value-selection owners for conversation surfaces."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import value_engine
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine import voice
from odylith.runtime.intervention_engine.contract import ObservationEnvelope


AMBIENT_SIGNAL_SCORE_FLOOR = 62
AMBIENT_SIGNAL_STRENGTH_FLOOR = 78
AMBIENT_MAX_SELECTED_SIGNALS = 3
AMBIENT_MAX_CANDIDATE_PAYLOADS = 24
_AMBIENT_DUPLICATE_OVERLAP_FLOOR = 0.72
_AMBIENT_SIGNAL_ORDER: tuple[str, ...] = ("risks", "history", "insight")
_AMBIENT_DUPLICATE_SUPPRESSION_REASONS = frozenset({"duplicate_teaser", "duplicate_card"})
_MEANINGFUL_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}")
_AMBIENT_TOKEN_STOPWORDS = frozenset(
    {
        "and",
        "ambient",
        "because",
        "block",
        "chat",
        "conversation",
        "governance",
        "intervention",
        "insight",
        "history",
        "odylith",
        "observation",
        "proposal",
        "risk",
        "risks",
        "signal",
        "signals",
        "that",
        "the",
        "this",
        "truth",
        "visible",
        "with",
    }
)

_normalize_string = visibility_contract.normalize_string
_normalize_block_string = visibility_contract.normalize_block_string
_normalize_token = visibility_contract.normalize_token
_mapping = visibility_contract.mapping_copy


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _label(name: str, *, markdown: bool) -> str:
    token = _normalize_token(name)
    labels = {
        "insight": "Odylith Insight:",
        "history": "Odylith History:",
        "risks": "Odylith Risks:",
    }
    plain = labels.get(token, "Odylith Insight:")
    return f"**{plain}**" if markdown else plain


def empty_signal(name: str) -> dict[str, Any]:
    return {
        "eligible": False,
        "label": _label(name, markdown=False),
        "preferred_markdown_label": _label(name, markdown=True),
        "plain_text": "",
        "markdown_text": "",
        "render_hint": "silent",
        "signal_score": 0,
        "suppressed_reason": "not_selected",
    }


def intervention_payload(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(bundle.get("candidate"), Mapping) and isinstance(bundle.get("proposal"), Mapping):
        return dict(bundle)
    return _mapping(bundle.get("intervention_bundle"))


def _primary_fact(intervention: Mapping[str, Any]) -> dict[str, Any]:
    facts = intervention.get("facts")
    if not isinstance(facts, list):
        return {}
    for row in facts:
        if isinstance(row, Mapping):
            return dict(row)
    return {}


def _facts(intervention: Mapping[str, Any]) -> list[dict[str, Any]]:
    facts = intervention.get("facts")
    if not isinstance(facts, list):
        return []
    return [dict(row) for row in facts if isinstance(row, Mapping)]


def _fact_refs(fact: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs = fact.get("refs")
    if not isinstance(refs, list):
        return []
    return [dict(row) for row in refs if isinstance(row, Mapping)]


def _signal_name_for_fact(fact: Mapping[str, Any]) -> str:
    kind = _normalize_token(fact.get("kind"))
    if kind == "history":
        return "history"
    if kind == "invariant":
        return "risks"
    return "insight"


def _fact_ref_ids(fact: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for ref in _fact_refs(fact):
        kind = _normalize_token(ref.get("kind")) or "ref"
        ref_id = _normalize_string(ref.get("id"))
        if not ref_id:
            continue
        token = f"{kind}:{ref_id}"
        if token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _fact_duplicate_group(fact: Mapping[str, Any], *, fallback_label: str = "") -> str:
    kind = _normalize_token(fact.get("kind")) or _normalize_token(fallback_label) or "fact"
    ref_ids = _fact_ref_ids(fact)
    if kind == "history":
        bug_refs = [token for token in ref_ids if token.startswith("bug:")]
        if bug_refs:
            return bug_refs[0]
    if kind == "governance_truth" and ref_ids:
        return ref_ids[0]
    tokens = sorted(_meaningful_tokens(fact.get("headline"), fact.get("detail")))
    if tokens:
        return f"{kind}:{'-'.join(tokens[:5])}"
    return f"{kind}:{_normalize_token(fallback_label) or 'unknown'}"


def _fact_signal_strength(
    *,
    fact: Mapping[str, Any],
    intervention: Mapping[str, Any],
) -> int:
    priority = int(fact.get("priority") or 0)
    if priority <= 0:
        return 0
    kind = _normalize_token(fact.get("kind"))
    score = priority
    if _normalize_string(fact.get("headline")):
        score += 4
    if _normalize_string(fact.get("detail")):
        score += 4
    if _fact_refs(fact):
        score += 5
    if signal_score(intervention=intervention) >= 82:
        score += 4
    if kind in {"history", "invariant"}:
        score += 3
    return _clamp_score(score)


def _fact_has_accurate_support(*, fact: Mapping[str, Any], signal_name: str) -> bool:
    kind = _normalize_token(fact.get("kind"))
    if not _normalize_string(fact.get("headline")) or not _normalize_string(fact.get("detail")):
        return False
    refs = _fact_refs(fact)
    if signal_name == "history":
        return kind == "history" and any(_normalize_token(row.get("kind")) == "bug" for row in refs)
    if signal_name == "risks":
        return kind == "invariant"
    return kind in {"governance_truth", "topology", "capture_opportunity"}


def _ambient_moment_kind(*, fact: Mapping[str, Any], signal_name: str, fallback: Any) -> str:
    if signal_name == "risks":
        return "guardrail"
    if signal_name == "history":
        return "recovery"
    kind = _normalize_token(fact.get("kind"))
    if kind == "topology":
        return "boundary"
    if kind == "governance_truth":
        return "continuation"
    if kind == "capture_opportunity":
        return "capture"
    return _normalize_token(fallback) or "insight"


def _meaningful_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for match in _MEANINGFUL_TOKEN_RE.findall(_normalize_block_string(value)):
            token = match.casefold()
            if token in _AMBIENT_TOKEN_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _payload_tokens(payload: Mapping[str, Any]) -> set[str]:
    rows: list[Any] = [
        payload.get("plain_text"),
        payload.get("source_kind"),
    ]
    rows.extend(
        payload.get("semantic_signature", [])
        if isinstance(payload.get("semantic_signature"), list)
        else []
    )
    rows.extend(
        str(row.get("id", "")).strip()
        for row in payload.get("refs", []) or []
        if isinstance(row, Mapping)
    )
    return _meaningful_tokens(*rows)


def duplicates_existing_payload(payload: Mapping[str, Any], existing_payloads: list[dict[str, Any]]) -> bool:
    text = _normalize_block_string(payload.get("plain_text") or payload.get("markdown_text"))
    tokens = _payload_tokens(payload)
    for existing in existing_payloads:
        existing_text = _normalize_block_string(existing.get("plain_text") or existing.get("markdown_text"))
        if text and existing_text and text.casefold() == existing_text.casefold():
            return True
        existing_tokens = _payload_tokens(existing)
        if not tokens or not existing_tokens:
            continue
        overlap = len(tokens & existing_tokens) / max(1, min(len(tokens), len(existing_tokens)))
        if overlap >= _AMBIENT_DUPLICATE_OVERLAP_FLOOR and min(len(tokens), len(existing_tokens)) >= 4:
            return True
    return False


def signal_score(
    *,
    intervention: Mapping[str, Any],
) -> int:
    candidate = _mapping(intervention.get("candidate"))
    moment = _mapping(candidate.get("moment"))
    return max(0, min(100, int(moment.get("score") or 0)))


def _continuity_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    moment = _mapping(candidate.get("moment"))
    return _mapping(moment.get("continuity"))


def _has_proven_visible_delivery(continuity: Mapping[str, Any]) -> bool:
    if bool(continuity.get("latest_proven_visible_delivery")):
        return True
    return visibility_contract.delivery_is_visible(
        channel=continuity.get("latest_delivery_channel"),
        status=continuity.get("latest_delivery_status"),
    )


def _hidden_duplicate_suppression(*, suppressed_reason: str, continuity: Mapping[str, Any]) -> bool:
    return (
        _normalize_token(suppressed_reason) in _AMBIENT_DUPLICATE_SUPPRESSION_REASONS
        and not _has_proven_visible_delivery(continuity)
    )


def _ambient_payload(
    *,
    observation: ObservationEnvelope,
    intervention: Mapping[str, Any],
    fact: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _mapping(intervention.get("candidate"))
    stage = _normalize_token(candidate.get("stage"))
    suppressed_reason = _normalize_string(candidate.get("suppressed_reason"))
    continuity = _continuity_payload(candidate)
    hidden_duplicate = _hidden_duplicate_suppression(
        suppressed_reason=suppressed_reason,
        continuity=continuity,
    )
    signal_name = _signal_name_for_fact(fact)
    if _normalize_token(observation.turn_phase) in {"prompt_submit", "userpromptsubmit"}:
        return {}
    if stage == "card" and signal_name == "insight" and not hidden_duplicate:
        return {}
    if (
        stage == "silent"
        and _normalize_token(continuity.get("stage_floor")) == "card"
        and _has_proven_visible_delivery(continuity)
    ):
        return {}
    if suppressed_reason and not hidden_duplicate:
        return {}
    moment = _mapping(candidate.get("moment"))
    if not fact:
        return {}
    score = signal_score(intervention=intervention)
    if score < AMBIENT_SIGNAL_SCORE_FLOOR:
        return {}
    signal_strength = _fact_signal_strength(fact=fact, intervention=intervention)
    if signal_strength < AMBIENT_SIGNAL_STRENGTH_FLOOR:
        return {}
    if not _fact_has_accurate_support(fact=fact, signal_name=signal_name):
        return {}
    ambient_moment = dict(moment)
    ambient_moment["ambient_label_kind"] = signal_name
    ambient_moment["kind"] = _ambient_moment_kind(
        fact=fact,
        signal_name=signal_name,
        fallback=moment.get("kind"),
    )
    ambient_moment["primary_fact"] = dict(fact)
    ambient_moment["supporting_fact"] = {}
    signal_name, plain_text = voice.render_ambient_signal(
        moment=ambient_moment,
        facts=[fact],
        markdown=False,
        seed=_normalize_string(candidate.get("key")),
    )
    if not plain_text:
        return {}
    plain_label = _label(signal_name, markdown=False)
    markdown_label = _label(signal_name, markdown=True)
    body = plain_text
    if body.startswith(plain_label):
        body = body[len(plain_label):].strip()
    markdown_text = f"{markdown_label} {body}".strip()
    return {
        "eligible": True,
        "label": plain_label,
        "preferred_markdown_label": markdown_label,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "render_hint": "explicit_label",
        "signal_score": signal_strength,
        "signal_name": signal_name,
        "suppressed_reason": "",
        "source_kind": _normalize_string(moment.get("kind")) or _normalize_string(fact.get("kind")),
        "duplicate_group": _fact_duplicate_group(fact, fallback_label=signal_name),
        "value_features": _ambient_feature_vector(
            fact=fact,
            intervention=intervention,
            signal_name=signal_name,
            signal_strength=signal_strength,
            hidden_duplicate=hidden_duplicate,
        ).as_dict(),
        "semantic_signature": [
            token
            for token in _meaningful_tokens(
                signal_name,
                fact.get("kind"),
                fact.get("headline"),
                fact.get("detail"),
                *[row.get("id", "") for row in _fact_refs(fact)],
            )
        ][:10],
        "refs": _fact_refs(fact),
    }


def _ambient_feature_vector(
    *,
    fact: Mapping[str, Any],
    intervention: Mapping[str, Any],
    signal_name: str,
    signal_strength: int,
    hidden_duplicate: bool,
) -> value_engine.InterventionValueFeatures:
    refs = _fact_refs(fact)
    evidence_quality = 0.0
    if _normalize_string(fact.get("headline")):
        evidence_quality += 0.35
    if _normalize_string(fact.get("detail")):
        evidence_quality += 0.35
    if refs:
        evidence_quality += 0.25
    if _fact_has_accurate_support(fact=fact, signal_name=signal_name):
        evidence_quality += 0.05
    actionability = {
        "risks": 0.82,
        "history": 0.74,
        "insight": 0.68,
    }.get(_normalize_token(signal_name), 0.45)
    correctness_confidence = max(evidence_quality, 0.90)
    if refs:
        correctness_confidence = max(correctness_confidence, 0.94)
    return value_engine.InterventionValueFeatures(
        correctness_confidence=correctness_confidence,
        materiality=max(signal_strength / 100.0, int(fact.get("priority") or 0) / 100.0),
        actionability=actionability,
        novelty=0.72 if _normalize_token(fact.get("kind")) in {"invariant", "history"} else 0.65,
        timing_relevance=max(signal_score(intervention=intervention) / 100.0, min(1.0, len(refs) * 0.35)),
        user_need=0.88 if hidden_duplicate else 0.80,
        visibility_need=0.92 if hidden_duplicate else 0.72,
        interruption_cost=0.04,
        redundancy_cost=0.0,
        uncertainty_penalty=max(0.0, 0.82 - evidence_quality) * 0.06,
        brand_risk=max(0.0, 0.78 - evidence_quality) * 0.04,
    ).normalized()


def ambient_payload_candidates(
    *,
    observation: ObservationEnvelope,
    intervention: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    order = {label: index for index, label in enumerate(_AMBIENT_SIGNAL_ORDER)}
    eligible_facts: list[tuple[int, int, str, int, dict[str, Any]]] = []
    for index, fact in enumerate(_facts(intervention)):
        signal_name = _signal_name_for_fact(fact)
        if not _fact_has_accurate_support(fact=fact, signal_name=signal_name):
            continue
        signal_strength = _fact_signal_strength(fact=fact, intervention=intervention)
        if signal_strength < AMBIENT_SIGNAL_STRENGTH_FLOOR:
            continue
        eligible_facts.append(
            (
                order.get(signal_name, 99),
                -signal_strength,
                _fact_duplicate_group(fact, fallback_label=signal_name),
                index,
                fact,
            )
        )
    for _label_order, _signal_strength, _duplicate_group, _index, fact in sorted(eligible_facts)[
        :AMBIENT_MAX_CANDIDATE_PAYLOADS
    ]:
        payload = _ambient_payload(
            observation=observation,
            intervention=intervention,
            fact=fact,
        )
        if not payload:
            continue
        candidate_id = ambient_candidate_id(payload)
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        rows.append(payload)
    return sorted(
        rows,
        key=lambda payload: (
            order.get(_normalize_token(payload.get("signal_name")) or "insight", 99),
            -float(payload.get("signal_score") or 0.0),
            ambient_candidate_id(payload),
        ),
    )


def ambient_candidate_id(payload: Mapping[str, Any]) -> str:
    signal_name = _normalize_token(payload.get("signal_name")) or "insight"
    semantic_signature = payload.get("semantic_signature")
    semantic_tokens = semantic_signature if isinstance(semantic_signature, list) else []
    refs = payload.get("refs")
    ref_rows = refs if isinstance(refs, list) else []
    basis = "|".join(
        [
            signal_name,
            _normalize_string(payload.get("duplicate_group")),
            _normalize_block_string(payload.get("plain_text") or payload.get("markdown_text")),
            " ".join(str(token) for token in semantic_tokens),
            " ".join(
                _normalize_string(_mapping(ref).get("id") or _mapping(ref).get("path"))
                for ref in ref_rows
                if isinstance(ref, Mapping)
            ),
        ]
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
    return f"ambient:{signal_name}:{digest}"


def _evidence_from_fact(
    fact: Mapping[str, Any],
    *,
    source_kind: str,
    evidence_class: str,
) -> tuple[value_engine.SignalEvidence, ...]:
    refs = _fact_refs(fact)
    rows: list[value_engine.SignalEvidence] = [
        value_engine.SignalEvidence(
            source_kind=source_kind,
            source_id=_normalize_string(fact.get("kind")),
            freshness="current",
            confidence=0.92 if refs else 0.90,
            excerpt=_normalize_block_string(fact.get("detail") or fact.get("headline")),
            evidence_class=evidence_class,
        )
    ]
    for ref in refs[:4]:
        rows.append(
            value_engine.SignalEvidence(
                source_kind=_normalize_token(ref.get("kind")) or "anchor",
                source_id=_normalize_string(ref.get("id")),
                source_path=_normalize_string(ref.get("path")),
                freshness="current",
                confidence=0.96,
                excerpt=_normalize_string(ref.get("label")) or _normalize_string(ref.get("id")),
                evidence_class="governed_anchor",
            )
        )
    return tuple(rows)


def _anchor_refs_from_fact(fact: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "kind": _normalize_token(ref.get("kind")),
            "id": _normalize_string(ref.get("id")),
            "path": _normalize_string(ref.get("path")),
            "label": _normalize_string(ref.get("label")) or _normalize_string(ref.get("id")),
        }
        for ref in _fact_refs(fact)
    )


def _proposition_from_fact(
    fact: Mapping[str, Any],
    *,
    proposition_id: str,
    label: str,
    claim_text: str,
    duplicate_group: str,
    evidence_class: str,
    supported: bool | None = None,
) -> value_engine.SignalProposition:
    return value_engine.SignalProposition(
        proposition_id=proposition_id,
        claim_text=_normalize_block_string(claim_text),
        proposition_kind=_normalize_token(label),
        support_state=(
            "supported"
            if bool(supported)
            else "unsupported"
            if supported is not None
            else "supported"
            if _fact_has_accurate_support(fact=fact, signal_name=label)
            else "unsupported"
        ),
        anchor_refs=_anchor_refs_from_fact(fact),
        semantic_signature=tuple(
            token
            for token in _meaningful_tokens(
                label,
                fact.get("kind"),
                fact.get("headline"),
                fact.get("detail"),
                *[row.get("id", "") for row in _fact_refs(fact)],
            )
        )[:10],
        duplicate_key=duplicate_group,
        freshness_state="current",
        evidence=_evidence_from_fact(
            fact,
            source_kind=_normalize_token(fact.get("kind")) or "governance_fact",
            evidence_class=evidence_class,
        ),
    )


def _value_option_from_ambient(payload: Mapping[str, Any]) -> value_engine.VisibleInterventionOption:
    signal_name = _normalize_token(payload.get("signal_name")) or "insight"
    fact = {
        "kind": _normalize_string(payload.get("source_kind")),
        "headline": _normalize_block_string(payload.get("plain_text")),
        "detail": _normalize_block_string(payload.get("plain_text")),
        "refs": payload.get("refs") if isinstance(payload.get("refs"), list) else [],
    }
    duplicate_group = _normalize_string(payload.get("duplicate_group"))
    option_id = ambient_candidate_id(payload)
    return value_engine.VisibleInterventionOption(
        option_id=option_id,
        proposition=_proposition_from_fact(
            fact,
            proposition_id=f"proposition:{option_id}",
            label=signal_name,
            claim_text=_normalize_block_string(payload.get("plain_text") or payload.get("markdown_text")),
            duplicate_group=duplicate_group,
            evidence_class="ambient_signal",
            supported=bool(payload.get("eligible")),
        ),
        proposed_label=signal_name,
        block_kind="ambient",
        markdown_text=_normalize_block_string(payload.get("markdown_text")),
        plain_text=_normalize_block_string(payload.get("plain_text")),
        proof_required=False,
        action_payload={},
        features=value_engine.InterventionValueFeatures.from_mapping(
            _mapping(payload.get("value_features")) or _mapping(payload.get("feature_vector"))
        ),
        metadata={
            "source_kind": _normalize_string(payload.get("source_kind")),
            "signal_name": signal_name,
        },
    )


def _primary_fact_payload(intervention: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(intervention.get("candidate"))
    moment = _mapping(candidate.get("moment"))
    primary = _mapping(moment.get("primary_fact"))
    return primary or _primary_fact(intervention)


def _is_current_visibility_status_fact(fact: Mapping[str, Any]) -> bool:
    if _normalize_token(fact.get("kind")) != "governance_truth":
        return False
    has_intervention_component = any(
        _normalize_token(ref.get("kind")) == "component"
        and _normalize_token(ref.get("id")) == "governance_intervention_engine"
        for ref in _fact_refs(fact)
    )
    if not has_intervention_component:
        return False
    text = _normalize_block_string(f"{fact.get('headline', '')} {fact.get('detail', '')}").casefold()
    return bool(
        "chat visibility" in text
        or "chat-visible" in text
        or "odylith note has reached this chat" in text
        or "odylith note stated directly" in text
        or "visible odylith beat" in text
        or "clean odylith beat" in text
        or "visible odylith block" in text
        or "visible odylith moment" in text
        or "visibility proof" in text
    )


def _value_option_from_observation(intervention: Mapping[str, Any]) -> value_engine.VisibleInterventionOption | None:
    candidate = _mapping(intervention.get("candidate"))
    if _normalize_token(candidate.get("stage")) != "card":
        return None
    markdown_text = _normalize_block_string(candidate.get("markdown_text"))
    plain_text = _normalize_block_string(candidate.get("plain_text"))
    if not markdown_text and not plain_text:
        return None
    moment = _mapping(candidate.get("moment"))
    primary = _primary_fact_payload(intervention)
    refs = _fact_refs(primary)
    option_id = f"observation:{_normalize_string(candidate.get('key')) or 'live'}"
    current_visibility_status = _is_current_visibility_status_fact(primary)
    materiality = max(int(moment.get("score") or 0) / 100.0, int(primary.get("priority") or 0) / 100.0)
    timing_relevance = max(int(moment.get("governance_readiness") or 0) / 100.0, min(1.0, len(refs) * 0.35))
    return value_engine.VisibleInterventionOption(
        option_id=option_id,
        proposition=value_engine.SignalProposition(
            proposition_id=f"proposition:{option_id}",
            claim_text=plain_text or markdown_text,
            proposition_kind="observation",
            support_state="supported" if not bool(_normalize_string(candidate.get("suppressed_reason"))) else "unsupported",
            anchor_refs=_anchor_refs_from_fact(primary),
            semantic_signature=tuple(
                token
                for token in _meaningful_tokens(
                    "observation",
                    primary.get("kind"),
                    primary.get("headline"),
                    primary.get("detail"),
                    *[row.get("id", "") for row in refs],
                )
            )[:10],
            duplicate_key=_fact_duplicate_group(primary, fallback_label="observation"),
            freshness_state="current",
            evidence=_evidence_from_fact(
                primary,
                source_kind="observation_candidate",
                evidence_class="live_observation",
            ),
        ),
        proposed_label="observation",
        block_kind="observation",
        markdown_text=markdown_text,
        plain_text=plain_text,
        proof_required=True,
        action_payload={},
        features=value_engine.InterventionValueFeatures(
            correctness_confidence=0.94 if markdown_text else 0.0,
            materiality=max(materiality, 0.96) if current_visibility_status else materiality,
            actionability=0.68 if current_visibility_status else 0.82,
            novelty=max(int(moment.get("novelty") or 0) / 100.0, 0.72) if current_visibility_status else int(moment.get("novelty") or 0) / 100.0,
            timing_relevance=max(timing_relevance, 0.98) if current_visibility_status else timing_relevance,
            user_need=0.96 if current_visibility_status else 0.78,
            visibility_need=1.0 if current_visibility_status else 0.72,
            interruption_cost=0.05,
            uncertainty_penalty=0.02,
            brand_risk=0.02,
        ),
        metadata={
            "source_kind": _normalize_string(moment.get("kind")),
            "current_visibility_status": current_visibility_status,
        },
    )


def _proposal_duplicate_group(proposal: Mapping[str, Any]) -> str:
    actions = proposal.get("actions")
    tokens: list[str] = []
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, Mapping):
                continue
            surface = _normalize_token(action.get("surface"))
            target = _normalize_string(action.get("target_id")) or _normalize_string(action.get("target_kind"))
            if surface and target:
                tokens.append(f"{surface}:{target}")
    if tokens:
        return "proposal:" + "|".join(tokens[:4])
    return f"proposal:{_normalize_string(proposal.get('key')) or 'live'}"


def _value_option_from_proposal(intervention: Mapping[str, Any]) -> value_engine.VisibleInterventionOption | None:
    proposal = _mapping(intervention.get("proposal"))
    markdown_text = _normalize_block_string(proposal.get("markdown_text"))
    plain_text = _normalize_block_string(proposal.get("plain_text"))
    if not bool(proposal.get("eligible")) or (not markdown_text and not plain_text):
        return None
    actions = proposal.get("actions")
    action_count = len(actions) if isinstance(actions, list) else 0
    option_id = f"proposal:{_normalize_string(proposal.get('key')) or 'live'}"
    return value_engine.VisibleInterventionOption(
        option_id=option_id,
        proposition=value_engine.SignalProposition(
            proposition_id=f"proposition:{option_id}",
            claim_text=plain_text or markdown_text,
            proposition_kind="proposal",
            support_state="supported" if not bool(_normalize_string(proposal.get("suppressed_reason"))) else "unsupported",
            anchor_refs=(),
            semantic_signature=tuple(_meaningful_tokens("proposal", plain_text, markdown_text))[:10],
            duplicate_key=_proposal_duplicate_group(proposal),
            freshness_state="current",
            evidence=(
                value_engine.SignalEvidence(
                    source_kind="proposal_bundle",
                    source_id=_normalize_string(proposal.get("key")),
                    freshness="current",
                    confidence=0.92 if action_count else 0.68,
                    excerpt=plain_text or markdown_text,
                    evidence_class="actionable_proposal",
                ),
            ),
        ),
        proposed_label="proposal",
        block_kind="proposal",
        markdown_text=markdown_text,
        plain_text=plain_text,
        proof_required=True,
        action_payload={"actions": actions if isinstance(actions, list) else []} if action_count else {},
        features=value_engine.InterventionValueFeatures(
            correctness_confidence=0.92 if action_count else 0.55,
            materiality=0.88,
            actionability=1.0 if action_count else 0.2,
            novelty=0.62,
            timing_relevance=min(1.0, action_count * 0.22 + 0.55),
            user_need=0.78,
            visibility_need=0.68,
            interruption_cost=0.05,
            uncertainty_penalty=0.02 if action_count else 0.18,
            brand_risk=0.02 if action_count else 0.18,
        ),
        metadata={"action_count": action_count},
    )


def value_selection_decision(
    *,
    intervention: Mapping[str, Any],
    ambient_payloads: list[dict[str, Any]],
) -> value_engine.VisibleSignalSelectionDecision:
    candidates: list[value_engine.VisibleInterventionOption] = [
        _value_option_from_ambient(payload)
        for payload in ambient_payloads
    ]
    observation_candidate = _value_option_from_observation(intervention)
    if observation_candidate is not None:
        candidates.append(observation_candidate)
    proposal_candidate = _value_option_from_proposal(intervention)
    if proposal_candidate is not None:
        candidates.append(proposal_candidate)
    return value_engine.select_visible_signals(
        candidates,
        context={"explicit_diagnosis_or_planning": len(candidates) > 1},
    )


def value_payload_fields(candidate: Mapping[str, Any], *, selected: bool) -> dict[str, Any]:
    return {
        "usefulness_score": candidate.get("usefulness_score"),
        "net_value": candidate.get("net_value"),
        "visibility_priority": candidate.get("visibility_priority"),
        "duplicate_group": _normalize_string(candidate.get("duplicate_group")),
        "value_engine_version": _normalize_string(candidate.get("value_engine_version")),
        "runtime_posture": _normalize_string(candidate.get("runtime_posture")),
        "selected_block_set_id": _normalize_string(candidate.get("selected_block_set_id")),
        "suppressed_reason": "" if selected else _normalize_string(candidate.get("suppressed_reason")),
    }
