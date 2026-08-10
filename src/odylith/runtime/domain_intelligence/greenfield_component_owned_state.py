"""Owned-state phrase contracts shared by Greenfield generation and validation."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase_identity_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import split_contract_clauses
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import ACTION_NOUNS
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import artifact_phrase_has_clause_shape
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import singularize_last_word
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words

_OWNED_ARTIFACT_TERMS = {
    "case", "choice", "decision", "entry", "event", "finding", "item", "measurement", "note",
    "outcome", "record", "request", "result", "signal", "snapshot", "summary", "view",
}
_OWNED_ENRICHMENT_SKIP_RE = re.compile(
    r"\b(?:blocked-state|command|correction\s+marker|handoff\s+record|prior\s+state|"
    r"replayable\s+change\s+evidence|reviewer\s+explanation|validation\s+context)\b",
    re.IGNORECASE,
)
_LIFECYCLE_MODIFIERS = {
    "active", "candidate", "current", "immutable", "recorded", "retained", "stored", "validated",
}


def owned_state_noun_phrase(value: str) -> bool:
    """Distinguish compact state nouns from verb-led or conditional clauses."""

    text = clean_artifact_text(value)
    words = tuple(word.casefold().strip(".,;:") for word in visible_words(text))
    if not words or artifact_phrase_has_clause_shape(value):
        return False
    core = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    core_words = tuple(word.casefold().strip(".,;:") for word in visible_words(core))
    actor_action_lead = bool(
        len(core_words) >= 3
        and looks_actor_term(core_words[0])
        and looks_like_base_action_token(core_words[1])
        and singularize_last_word(core_words[-1]) not in _OWNED_ARTIFACT_TERMS
    )
    if actor_action_lead:
        return False
    if not looks_like_action_clause(core):
        return True
    if set(core_words) & {"a", "an", "the", "to", "into", "onto"}:
        return False
    lead = singularize_last_word(core_words[0])
    second = singularize_last_word(core_words[1]) if len(core_words) > 1 else ""
    role_owned_decision = (
        len(core_words) >= 3
        and singularize_last_word(core_words[-1]) == "decision"
        and looks_actor_term(core_words[-2])
    )
    if role_owned_decision and lead in ARTIFACT_CARRIER_TERMS:
        return False
    trailing_carrier = any(
        singularize_last_word(word) in ARTIFACT_CARRIER_TERMS for word in core_words[1:]
    )
    finite_action_lead = looks_like_finite_action_token(core_words[0])
    return bool(
        len(core_words) >= 2
        and (
            (lead in ARTIFACT_CARRIER_TERMS and (not finite_action_lead or trailing_carrier))
            or (lead in ACTION_NOUNS and second in ARTIFACT_CARRIER_TERMS)
            or role_owned_decision
        )
    )


def owned_state_phrases(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(unique_text(value for value in values if owned_state_noun_phrase(value)))


def enrich_owned_state_from_io(
    owned_state: Any,
    fields: Mapping[str, Any],
    *,
    noise_terms: set[str],
) -> str:
    owned_clauses = split_contract_clauses(owned_state)
    owned_terms = set(domain_terms(" ".join(owned_clauses), noise_terms=noise_terms))
    additions: list[str] = []
    for key in ("accepted_inputs", "produced_outputs"):
        for clause in split_contract_clauses(fields.get(key)):
            raw_candidate = clean_artifact_text(
                re.sub(r"^(?:required|validated)\s+", "", clause, flags=re.IGNORECASE)
            ).strip(" .")
            candidate = clean_artifact_phrase(raw_candidate)
            if not candidate or _OWNED_ENRICHMENT_SKIP_RE.search(candidate) or not owned_state_noun_phrase(candidate):
                continue
            terms = domain_terms(candidate, noise_terms=noise_terms)
            if len(terms) < 2 or not (set(terms) & _OWNED_ARTIFACT_TERMS):
                continue
            if len(set(terms) - owned_terms) < 1:
                continue
            additions.append(candidate)
            owned_terms.update(terms)
            if len(additions) >= 2:
                break
        if len(additions) >= 2:
            break
    return phrase([*owned_clauses, *additions])


def lifecycle_identity_phrases(values: Sequence[str]) -> tuple[str, ...]:
    """Summarize a shared event/history identity as lifecycle state."""

    event_phrases = [value for value in values if "event" in phrase_identity_terms(value)]
    history_phrases = [value for value in values if "history" in phrase_identity_terms(value)]
    rows: list[str] = []
    for event_phrase in event_phrases:
        event_terms = content_terms(event_phrase)
        for history_phrase in history_phrases:
            if event_phrase.casefold() == history_phrase.casefold():
                continue
            history_terms = set(content_terms(history_phrase))
            shared = [
                term
                for term in event_terms
                if term in history_terms
                and term not in {"event", "history"} | _LIFECYCLE_MODIFIERS | ARTIFACT_CARRIER_TERMS
            ]
            if shared:
                rows.append(f"{' '.join(shared[:2])} lifecycle")
    return tuple(unique_text(rows))


__all__ = ["enrich_owned_state_from_io", "lifecycle_identity_phrases", "owned_state_noun_phrase", "owned_state_phrases"]
