"""Phrase and label model for confirmed greenfield completion repairs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import text_needs_repair
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_LABEL_FOCUS_STOPWORDS = {
    "adapter",
    "component",
    "engine",
    "service",
    "surface",
    "system",
    "view",
}


def capability_phrase(proposal: Mapping[str, Any]) -> str:
    return first_path_capability_phrase(first_path(proposal), fallback="complete the first product path", limit=220)


def action_phrase(proposal: Mapping[str, Any]) -> str:
    """Return the material user-side action without folding in the final result."""

    action = first_path_action_phrase(first_path(proposal), fallback="complete the first product action", max_fragments=1)
    return _base_user_action_phrase(action) or "complete the first product action"


def _base_user_action_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    words = text.split()
    for index in range(1, min(len(words), 6)):
        candidate = " ".join(words[index:]).strip(" .")
        if looks_like_finite_action(candidate):
            return base_action_clause(candidate)
    return base_action_clause(text)


def outcome_phrase(proposal: Mapping[str, Any]) -> str:
    return first_path_outcome_phrase(
        first_path(proposal),
        proof_boundary=proof_boundary(proposal),
        fallback="the promised user-visible result",
    )


def outcome_action_phrase(outcome: str) -> str:
    text = _clean(outcome).rstrip(" .") or "the product result"
    if re.search(r"\b(?:plan|readout|recommendation|report|schedule|view)\b", text, flags=re.IGNORECASE):
        return f"use {text}"
    return f"reach {text}"


def workstream_subject(row: Mapping[str, Any], *, fallback: str, components: Sequence[Mapping[str, Any]] = ()) -> str:
    component = _clean(next(iter(text_values(row.get("component_focus"))), ""))
    title = _clean(row.get("title")) or fallback
    if component:
        label = _component_label_for_id(component, components)
        if label:
            return label
        return human_label(component)
    return re.sub(r"^(?:make|build|show|keep|let)\s+", "", title, flags=re.I).strip(" .") or title


def _component_label_for_id(component_id: str, components: Sequence[Mapping[str, Any]]) -> str:
    key = _slug_key(component_id)
    if not key:
        return ""
    for component in components:
        candidate_ids = [
            component.get("component_id"),
            component.get("id"),
            component.get("slug"),
        ]
        if any(_slug_key(value) == key for value in candidate_ids):
            return _clean(component.get("label") or component.get("name"))
    return ""


def _slug_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _clean(value).casefold()).strip("-")


def human_label(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    if "-" in text or "_" in text:
        words = [word for word in re.split(r"[-_\s]+", text) if word]
        dropped_prefix: list[str] = []
        while words and len(words) > 4 and words[0].casefold() not in {"owner", "user", "admin", "reviewer", "operator"}:
            dropped_prefix.append(words.pop(0))
            if len(dropped_prefix) >= 3:
                break
        text = " ".join(words or dropped_prefix)
    return " ".join(word[:1].upper() + word[1:] if not word.isupper() else word for word in text.split())


def workstream_problem(*, label: str, action: str, outcome: str, state: str) -> str:
    return _sentence(
        f"{label} matters because users do not get value from {action} until it produces {outcome} and leaves {state} understandable when something is missing or corrected.",
        limit=520,
    )


def workstream_opportunity(*, label: str, action: str, outcome: str) -> str:
    return _sentence(
        f"Build the narrow behavior in {label} that lets one representative user {action} and {outcome_action_phrase(outcome)}.",
        limit=420,
    )


def workstream_product_view(*, label: str, action: str, outcome: str) -> str:
    return _sentence(
        f"{label} is complete when the user can {action}, understand {outcome}, and recover cleanly from a bad or incomplete attempt.",
        limit=520,
    )


def workstream_risk(*, label: str, outcome: str, state: str) -> str:
    return _sentence(
        f"Risk: {label} can create false confidence if {outcome} is shown while {state} is incomplete, stale, or hard to explain.",
        limit=420,
    )


def has_connector_clipped_risk_subject(value: str) -> bool:
    text = _clean(value).strip()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    first = text.split(maxsplit=1)[0].casefold() if text.split() else ""
    return first in {"and", "or"}


def component_focus_phrase(*, label: str, contract: Mapping[str, Any], fallback: str) -> str:
    if label_focus := _label_focus_phrase(label):
        return label_focus
    label_terms = keywords([label])
    blocked_terms = {
        *label_terms,
        "actor",
        "boundary",
        "blocker",
        "component",
        "downstream",
        "evidence",
        "handoff",
        "input",
        "local",
        "output",
        "proof",
        "release",
        "service",
        "sibling",
        "source",
        "state",
        "upstream",
        "validation",
    }
    candidates: list[str] = []
    for value in text_values(contract.get("owned_state")):
        for part in _owned_state_phrases(value):
            phrase = _clean(part).strip(" .")
            terms = keywords([phrase])
            if not phrase or len(phrase.split()) > 5 or not terms or terms <= blocked_terms:
                continue
            candidates.append(phrase)
    if candidates:
        return _sentence("; ".join(candidates[:2]), fallback=fallback, limit=120).rstrip(".")
    return _sentence(fallback, fallback="component state", limit=120).rstrip(".")


def _owned_state_phrases(value: str) -> list[str]:
    text = _clean(value)
    rows: list[str] = []
    for segment in text.replace(";", ",").split(","):
        phrase = segment.strip(" .")
        if phrase:
            rows.append(phrase)
    return rows or ([text] if text else [])


def _label_focus_phrase(label: str) -> str:
    words = [
        word.casefold()
        for word in label_terms(
            _clean(label).replace("_", " "),
            stopwords=_LABEL_FOCUS_STOPWORDS,
        )
    ]
    return " ".join(words[:5]).strip()


def primary_component_for_backlog(
    row: Mapping[str, Any],
    *,
    components: Sequence[dict[str, Any]],
    by_id: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for ref in text_values(row.get("component_focus")):
        if component := by_id.get(_clean(ref)):
            return component
    title_terms = keywords([row.get("title")])
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, component in enumerate(components):
        score = len(title_terms & keywords([component.get("label"), component.get("component_id")]))
        if score:
            scored.append((score, -index, component))
    scored.sort(reverse=True)
    return scored[0][2] if scored else None


def row_drifted_from_component(row: Mapping[str, Any], component: Mapping[str, Any]) -> bool:
    label_terms = keywords([component.get("label"), component.get("component_id")])
    row_terms = keywords([row.get("title"), row.get("product_view"), row.get("recommended_first_slice")])
    if not label_terms:
        return False
    return len(label_terms & row_terms) < min(2, len(label_terms))


def row_is_release_proof(row: Mapping[str, Any]) -> bool:
    text = " ".join(text_values([row.get("title"), row.get("product_view"), row.get("recommended_first_slice")])).casefold()
    return "proof" in text or "release evidence" in text or "release readiness" in text


def keywords(values: Sequence[Any]) -> set[str]:
    text = " ".join(str(value or "").replace("_", " ").replace("-", " ") for value in values)
    return set(ordered_terms(text, minimum=4))


def component_label(row: Mapping[str, Any], index: int) -> str:
    return _clean(row.get("label")) or _clean(row.get("component_id")) or f"Component {index}"


def project_title(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _clean(intent.get("title")) if isinstance(intent, Mapping) else "Confirmed Project"


def slug_title(proposal: Mapping[str, Any]) -> str:
    return "-".join(word for word in project_title(proposal).casefold().replace("_", " ").split() if word) or "confirmed-project"


def diagram_title(row: Mapping[str, Any], *, proposal: Mapping[str, Any], index: int) -> str:
    slug = _clean(row.get("slug"))
    project_slug = slug_title(proposal)
    suffix = slug
    if slug.startswith(f"{project_slug}-"):
        suffix = slug[len(project_slug) + 1 :]
    words = [word for word in re.split(r"[-_\s]+", suffix) if word]
    if words:
        title = " ".join(word[:1].upper() + word[1:] for word in words)
        lowered = title.casefold()
        if not any(token in lowered for token in ("view", "diagram", "sequence", "context", "proof", "flow")):
            title = f"{title} View"
        return title
    return f"Architecture View {index}"


def first_path(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(
        intent.get("first_path") if isinstance(intent, Mapping) else "",
        fallback="the accepted first path",
        limit=900,
    )


def proof_boundary(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(intent.get("proof_boundary") if isinstance(intent, Mapping) else "", fallback="the promised user-visible result")


def state_object(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    if isinstance(intent, Mapping) and _clean(intent.get("state_object")):
        return domain_object_label(_clean(intent.get("state_object")), fallback="the accepted state")
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for value in text_values(intelligence.get("ontology")):
            if "state object:" in value.casefold():
                return domain_object_label(value.split(":", 1)[1], fallback="the accepted state")
    return "the accepted state"


def actor_summary(proposal: Mapping[str, Any]) -> str:
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        actors = [value for value in text_values(intelligence.get("operators")) if not text_needs_repair(value)][:2]
        if actors:
            return _sentence("; ".join(actors), limit=280)
    return f"{project_title(proposal)} users, reviewers, owners, and release decision makers"


def lower_first(value: str) -> str:
    text = _clean(value).strip()
    if not text:
        return ""
    if text[:2].isupper():
        return text
    return text[:1].lower() + text[1:]


__all__ = [
    "action_phrase",
    "actor_summary",
    "capability_phrase",
    "component_focus_phrase",
    "component_label",
    "diagram_title",
    "first_path",
    "human_label",
    "has_connector_clipped_risk_subject",
    "keywords",
    "lower_first",
    "outcome_action_phrase",
    "outcome_phrase",
    "primary_component_for_backlog",
    "project_title",
    "proof_boundary",
    "row_drifted_from_component",
    "row_is_release_proof",
    "slug_title",
    "state_object",
    "workstream_opportunity",
    "workstream_problem",
    "workstream_product_view",
    "workstream_risk",
    "workstream_subject",
]
