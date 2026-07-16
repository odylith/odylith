"""Phrase and label model for confirmed greenfield completion repairs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import text_needs_repair
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import object_reference_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_restates_label_with_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import project_specific_actor_labels
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_view import first_path_semantic_view
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_system_generated_action
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import modal_actor_action_parts
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_repeated_phrase_units
from odylith.runtime.domain_intelligence.greenfield_text import imperative_action_with_copula_words
from odylith.runtime.domain_intelligence.greenfield_text import normalize_confirmed_proof_boundary_sentence
from odylith.runtime.domain_intelligence.greenfield_text import normalize_reviewed_result_nouns
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_LABEL_FOCUS_STOPWORDS = {
    "adapter",
    "component",
    "engine",
    "service",
    "surface",
    "system",
    "view",
    "workspace",
}

_VISIBLE_RESULT_OBJECT_HINTS = {
    "blocker",
    "blockers",
    "card",
    "decision",
    "evidence",
    "event",
    "note",
    "notice",
    "option",
    "outcome",
    "plan",
    "record",
    "readout",
    "recommendation",
    "report",
    "result",
    "schedule",
    "summary",
    "timeline",
    "view",
}
_VISIBLE_SEE_RESULT_HINTS = {
    "card",
    "consequence",
    "date",
    "deadline",
    "event",
    "history",
    "notice",
    "outcome",
    "recap",
    "readout",
    "reflection",
    "report",
    "result",
    "slot",
    "state",
    "status",
    "summary",
    "timeline",
    "trend",
    "view",
    "viewable",
    "window",
    "saved",
}
_FINITE_ACTION_PATTERN = action_verb_pattern(include_base=False, include_finite=True)


def capability_phrase(proposal: Mapping[str, Any]) -> str:
    return first_path_capability_phrase(first_path(proposal), fallback="complete the first product path", limit=220)


def proof_capability_phrase(proposal: Mapping[str, Any]) -> str:
    return first_path_capability_phrase(
        first_path(proposal),
        fallback=capability_phrase(proposal),
        limit=220,
        gerund=True,
    )


def action_phrase(proposal: Mapping[str, Any]) -> str:
    """Return the material user-side action without folding in the final result."""

    path = first_path(proposal)
    action = first_path_action_phrase(
        path,
        fallback="complete the first product action",
        max_fragments=1,
    )
    return _base_user_action_phrase(action) or "complete the first product action"


def _first_system_material_action_after_human_setup(value: str) -> str:
    view = first_path_semantic_view(first_path_model(value))
    saw_human_setup = False
    for step in view.steps:
        if step.is_trivial_start or step.is_dash_detail or step.is_system_generated or step.is_visible_result:
            continue
        actor = step.actor_signature.casefold()
        if actor and not _system_action_actor(actor):
            saw_human_setup = True
            continue
        if not actor and _human_setup_without_signature(step.text):
            saw_human_setup = True
            continue
        if saw_human_setup and step.is_material_action and step.fragment:
            return step.fragment
    return ""


def _system_action_actor(value: str) -> bool:
    terms = set(re.findall(r"[a-z][a-z0-9'-]*", str(value or "").casefold()))
    return bool(terms & {"app", "application", "controller", "engine", "product", "service", "system", "workspace"})


def _human_setup_without_signature(value: str) -> bool:
    text = _clean(value).casefold().strip(" .")
    return bool(re.match(r"^(?:home\s+cook)\s+(?:picks?|chooses?|selects?)\b", text))


def _base_user_action_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    if looks_like_action_clause(text):
        return base_action_clause(text, force_leading_finite=True)
    actor_action = _actor_led_base_action_phrase(text)
    if actor_action:
        return actor_action
    subject_action = _subject_led_finite_action_phrase(text)
    if subject_action:
        return subject_action
    return base_action_clause(text)


def _actor_led_base_action_phrase(value: str) -> str:
    _actor, action = _actor_led_base_action_parts(value)
    return action


def _subject_led_finite_action_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    match = re.search(
        rf"(?<![A-Za-z0-9_-])(?:{_FINITE_ACTION_PATTERN})(?![A-Za-z0-9_-])",
        text,
        flags=re.IGNORECASE,
    )
    if not match or match.start() <= 0:
        return ""
    subject = text[: match.start()].strip(" ,")
    if not 1 <= len(subject.split()) <= 5:
        return ""
    if re.search(
        r"\b(?:decision|evidence|proof|recommendation|record|report|result|status|summary|view)\b",
        subject,
        flags=re.IGNORECASE,
    ):
        return ""
    action = text[match.start() :].strip(" .")
    return base_action_clause(action, force_leading_finite=True) if looks_like_action_clause(action) else ""


def _actor_led_base_action_parts(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    if not text:
        return "", ""
    actor, action = actor_led_action_parts(text)
    if actor and action:
        words = text.split()
        index = len(actor.split())
        if imperative_action_with_copula_words(words, index):
            return "", ""
        return actor, action
    return "", ""


def outcome_phrase(proposal: Mapping[str, Any]) -> str:
    semantic = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    contract = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    semantic_visible = _clean(contract.get("visible_result")).strip(" .")
    if len(semantic_visible.split()) >= 2:
        return semantic_visible
    return first_path_outcome_phrase(
        first_path(proposal),
        proof_boundary=proof_boundary(proposal),
        fallback="the promised user-visible result",
    )


def outcome_action_phrase(outcome: str) -> str:
    text = _reviewable_result_object(_clean(outcome).rstrip(" .") or "the product result")
    predicate_object = _predicate_result_object(text)
    if predicate_object:
        return _modal_safe_outcome_action(f"review {predicate_object}")
    actor_review = _actor_led_outcome_review_action(text)
    if actor_review:
        return _modal_safe_outcome_action(actor_review)
    words = {word.strip(".,:;").casefold() for word in text.replace("-", " ").split()}
    if words & {"explanation", "explanations", "recommendation", "recommendations"}:
        return _modal_safe_outcome_action(f"review {_object_phrase(text)}")
    actor, actor_action = _actor_led_base_action_parts(
        re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    )
    if actor_action and (
        not words & {"proof", "proven", "verified", "evidence", "audit", "result", "status"}
        or _looks_like_human_actor_prefix(actor)
    ):
        return _modal_safe_outcome_action(actor_action)
    if looks_like_action_clause(text):
        return _modal_safe_outcome_action(base_action_clause(text, force_leading_finite=True))
    if words & {"proof", "proven", "verified", "evidence", "audit", "ledger", "ledgers"}:
        return _modal_safe_outcome_action(f"review {_object_phrase(text)}")
    if _looks_like_coordinated_result_object(text):
        return _modal_safe_outcome_action(f"see {_object_phrase(text)}")
    system_action = _system_generated_outcome_action(text)
    if system_action:
        return _modal_safe_outcome_action(system_action)
    if _looks_like_past_result_noun(text):
        return _modal_safe_outcome_action(f"see {_object_phrase(text)}")
    if _looks_like_question_result(text):
        return _modal_safe_outcome_action(f"see {text}")
    if _looks_like_predicate_result(text):
        return _modal_safe_outcome_action(f"see that {text}")
    object_text = _object_phrase(text)
    if "status" in words and "visible" in words:
        return _modal_safe_outcome_action(f"see {object_text}")
    if "readiness" in words:
        return _modal_safe_outcome_action(f"see {object_text}")
    if "status" in words and words & {"tracking", "lifecycle"}:
        return _modal_safe_outcome_action(f"see {object_text}")
    if words & _VISIBLE_SEE_RESULT_HINTS:
        return _modal_safe_outcome_action(f"see {object_text}")
    if words & _VISIBLE_RESULT_OBJECT_HINTS:
        return _modal_safe_outcome_action(f"use {object_text}")
    return _modal_safe_outcome_action(f"reach {object_text}")


def _looks_like_coordinated_result_object(value: str) -> bool:
    words = [word.strip(".,:;()[]{}").casefold() for word in _clean(value).replace("-", " ").split()]
    words = [word for word in words if word]
    if not 3 <= len(words) <= 8 or not {"and", "or"} & set(words):
        return False
    result_tail_terms = {
        "approval",
        "approvals",
        "clearance",
        "clearances",
        "decision",
        "decisions",
        "evidence",
        "proof",
        "readiness",
        "report",
        "reports",
        "status",
        "summary",
    }
    return words[-1] in result_tail_terms


def _modal_safe_outcome_action(value: str) -> str:
    text = _clean(value).strip(" .")
    if looks_like_action_clause(text):
        return base_action_clause(text, force_leading_finite=True) or text
    return text


def _looks_like_human_actor_prefix(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if has_actor_role_word(text):
        return True
    words = [word.strip(".,:;()[]{}").casefold() for word in text.split() if word.strip(".,:;()[]{}")]
    return bool(words and words[-1].endswith(("ant", "ent", "er", "ian", "ist", "or", "owner")))


def _system_generated_outcome_action(value: str) -> str:
    """Return a modal-safe user action for result text that describes system work."""

    text = _clean(value).strip(" .")
    if not text or not is_system_generated_action(text):
        return ""
    action = action_chain_fragment(text)
    action_words = action.split()
    if len(action_words) < 2:
        return ""
    result_object = " ".join(action_words[1:]).strip(" .,")
    if not result_object:
        return ""
    normalized = _object_phrase(result_object)
    words = {word.strip(".,:;").casefold() for word in result_object.replace("-", " ").split()}
    if words & {"proof", "evidence", "audit", "report", "reports", "record", "records", "readiness", "state", "status"}:
        return f"review {normalized}"
    return f"see {normalized}"


def _reviewable_result_object(value: str) -> str:
    """Normalize result nouns before composing review/use/see actions."""

    return normalize_reviewed_result_nouns(_clean(value)).strip(" .")


def _looks_like_past_result_noun(value: str) -> bool:
    words = [word.strip(".,:;").casefold() for word in _clean(value).replace("-", " ").split() if word.strip(".,:;")]
    return bool(words and words[0] in {"approved", "confirmed", "generated", "published", "recorded", "saved", "verified"} and set(words) & (_VISIBLE_RESULT_OBJECT_HINTS | _VISIBLE_SEE_RESULT_HINTS))


def _actor_led_outcome_review_action(value: str) -> str:
    actor_action = _actor_led_base_action_phrase(re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE))
    if not actor_action:
        return ""
    decision_object = _decision_pair_result_object(actor_action)
    if decision_object:
        return f"review {decision_object}"
    if _looks_like_coordinated_result_object(actor_action):
        return f"see {_object_phrase(actor_action)}"
    return ""


def _decision_pair_result_object(value: str) -> str:
    text = _clean(value).strip(" .")
    pairs = {
        ("accept", "reject"): ("acceptance", "rejection"),
        ("approve", "reject"): ("approval", "rejection"),
    }
    for (left, right), (left_noun, right_noun) in pairs.items():
        match = re.match(rf"^{left}\s+or\s+{right}\s+(?P<object>.+)$", text, flags=re.IGNORECASE)
        if not match:
            continue
        result_object = _clean(match.group("object")).strip(" .")
        if result_object:
            return f"the {left_noun} or {right_noun} of {result_object}"
    return ""


def _object_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "the product result"
    lowered = lower_first(text)
    words = lowered.split(maxsplit=1)
    first = words[0].strip(".,:;").casefold() if words else ""
    if first in {"a", "an", "the", "this", "that", "one", "my", "your", "their", "his", "her", "our", "its"}:
        return lowered
    return f"the {lowered}"


def inline_result_phrase(value: str) -> str:
    text = _reviewable_result_object(_clean(value).rstrip(" .") or "the product result")
    return _predicate_result_object(text) or lower_first(text)


def _predicate_result_object(value: str) -> str:
    """Return a noun phrase for bare predicate outcomes such as `it delivers X`."""

    text = _clean(value).strip(" .")
    if not text:
        return ""
    match = re.match(
        r"^(?:(?:it|this|that|they|both|each|all)\s+)?"
        r"(?P<verb>delivers?|powers?)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    result_object = _clean(match.group("object")).strip(" .")
    if not result_object:
        return ""
    noun = "delivery" if match.group("verb").casefold().startswith("deliver") else "proof"
    return f"{noun} of {lower_first(result_object)}"


def _looks_like_question_result(value: str) -> bool:
    return bool(re.match(r"^(?:if|whether|why|when|where)\b", _clean(value), flags=re.IGNORECASE))


def _looks_like_predicate_result(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    return bool(
        re.match(
            r"^(?:the|a|an|one|this|that)\s+"
            r"(?:[A-Za-z0-9][A-Za-z0-9'/-]*\s+){0,8}?"
            r"(?:"
            r"changed|decreased|failed|improved|increased|met|moved|passed|reduced|succeeded|"
            r"violated|was|were"
            r")\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def workstream_subject(row: Mapping[str, Any], *, fallback: str, components: Sequence[Mapping[str, Any]] = ()) -> str:
    component = _clean(next(iter(text_values(row.get("component_focus"))), ""))
    if component:
        label = _component_label_for_id(component, components)
        if label:
            return label
        return human_label(component)
    return "This workstream"


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
        f"{label} matters because users do not get value from {action} until the visible result is reviewable: {outcome}. "
        f"{state} must remain understandable when something is missing or corrected.",
        limit=520,
    )


def workstream_opportunity(*, label: str, actor: str, action: str, outcome: str) -> str:
    return _sentence(
        f"Build the narrow behavior in {label} that lets {actor} {action} and {outcome_action_phrase(outcome)}.",
        limit=420,
    )


def workstream_product_view(*, label: str, action: str, outcome: str) -> str:
    outcome_action = outcome_action_phrase(outcome)
    path_parts = [_capability_action_statement(action)]
    if outcome_action:
        path_parts.append(outcome_action)
    path_parts.append("recover cleanly from a bad or incomplete attempt")
    return _sentence(
        f"{label} is complete when {_join_path_actions(path_parts)}.",
        limit=520,
    )


def _capability_action_statement(action: str) -> str:
    text = _clean(action).strip(" .")
    modal_actor, modal_action = modal_actor_action_parts(text)
    if modal_actor and modal_action:
        return f"{_actor_subject_phrase(modal_actor)} can {base_action_clause(modal_action)}"
    actor, actor_action = _actor_led_base_action_parts(text)
    if actor and actor_action:
        return f"{_actor_subject_phrase(actor)} can {actor_action}"
    action_text = _base_user_action_phrase(text) or "complete the first product action"
    return f"the user can {action_text}"


def _actor_subject_phrase(actor: str) -> str:
    text = _clean(actor).strip(" .")
    if not text:
        return "the user"
    if re.match(r"^(?:a|an|the|one)\s+", text, flags=re.IGNORECASE):
        return text[:1].lower() + text[1:]
    lowered = text[:1].lower() + text[1:]
    last = lowered.split()[-1].casefold().strip(".,:;") if lowered.split() else ""
    if last.endswith("s") and not last.endswith(("ics", "ss", "us")):
        return lowered
    return f"the {lowered}"


def _join_path_actions(values: Sequence[str]) -> str:
    rows = [_clean(value).strip(" .") for value in values if _clean(value).strip(" .")]
    if not rows:
        return "the user can complete the first product action"
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def workstream_risk(*, label: str, outcome: str, state: str) -> str:
    state_focus = sentence_label(domain_object_label(state, fallback="the accepted state"))
    role = _workstream_risk_role(label)
    outcome_text = inline_result_phrase(outcome)
    if role == "proof":
        return _sentence(
            f"Risk: {label} can make evidence look trustworthy before {state_focus} is complete or replayable.",
            limit=420,
        )
    if role == "review":
        return _sentence(
            f"Risk: {label} can present {outcome_text} if {state_focus} is incomplete or correction context is unclear.",
            limit=420,
        )
    if role == "release":
        return _sentence(
            f"Risk: {label} can mark the release ready before {state_focus} has success, blocked-input, and replay proof.",
            limit=420,
        )
    return _sentence(
        f"Risk: {label} can accept incomplete input and make {outcome_text} look safer than the evidence supports.",
        limit=420,
    )


def _workstream_risk_role(label: str) -> str:
    text = _clean(label).casefold()
    if any(term in text for term in ("review", "clear", "result", "outcome", "decision", "publisher")):
        return "review"
    if any(term in text for term in ("intake", "register", "submit", "enter", "capture", "record")):
        return "input"
    if any(term in text for term in ("complete", "release", "path")):
        return "release"
    if any(term in text for term in ("proof", "trust", "evidence", "ledger")):
        return "proof"
    return "input"


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
            collapse_repeated_phrase_units(_clean(label).replace("_", " ")),
            stopwords=_LABEL_FOCUS_STOPWORDS,
        )
    ]
    focus = _trim_terminal_connector(" ".join(words[:6]).strip())
    focus = collapse_adjacent_duplicate_terms(focus)
    return collapse_repeated_phrase_units(focus)


def _trim_terminal_connector(value: str) -> str:
    words = value.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "for", "of", "or", "plus", "to", "with"}:
        words.pop()
    return " ".join(words).strip()


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
    return (
        "proof" in text
        or "release evidence" in text
        or "release readiness" in text
        or "can be trusted" in text
        or ("trusted" in text and any(token in text for token in ("evidence", "release", "validation")))
    )


def keywords(values: Sequence[Any]) -> set[str]:
    text = " ".join(str(value or "").replace("_", " ").replace("-", " ") for value in values)
    return set(ordered_terms(text, minimum=4))


def component_label(row: Mapping[str, Any], index: int) -> str:
    label = collapse_repeated_phrase_units(_clean(row.get("label")))
    return label or _clean(row.get("component_id")) or f"Component {index}"


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
    raw = intent.get("proof_boundary") if isinstance(intent, Mapping) else ""
    return _sentence(normalize_confirmed_proof_boundary_sentence(raw), fallback="the promised user-visible result")


def state_object(proposal: Mapping[str, Any]) -> str:
    raw_state = _state_object_source(proposal)
    if raw_state:
        return compact_domain_object_label(raw_state, fallback="the accepted state")
    return "the accepted state"


def state_reference(proposal: Mapping[str, Any]) -> str:
    label = state_object(proposal)
    raw_state = _state_object_source(proposal)
    if raw_state:
        detail = _state_reference_detail(raw_state, state_label=label)
        if detail:
            return sentence_label(detail)
    return sentence_label(label)


def _state_reference_detail(raw_state: str, *, state_label: str) -> str:
    text = _clean(raw_state)
    if not text or ":" in text:
        return ""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(sentences) > 1:
        return ""
    detail = state_detail_summary(text, state_label=state_label, limit=220)
    if not detail or detail.casefold().endswith((" and", " for", " of", " through", " with")):
        return ""
    if state_detail_restates_label_with_finite_action(detail, state_label=state_label):
        return ""
    return detail


def _state_object_source(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    if isinstance(intent, Mapping) and _clean(intent.get("state_object")):
        return _clean(intent.get("state_object"))
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for value in text_values(intelligence.get("ontology")):
            if "state object:" in value.casefold():
                return _clean(value.split(":", 1)[1])
    return ""


def actor_summary(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        labels = project_specific_actor_labels(intent)
        if labels:
            return _sentence("; ".join(labels[:3]), limit=280)
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        actors = [value for value in text_values(intelligence.get("operators")) if not text_needs_repair(value)][:2]
        if actors:
            return _sentence("; ".join(actors), limit=280)
    return f"{project_title(proposal)} users, reviewers, owners, and release decision makers"


def primary_actor_phrase(proposal: Mapping[str, Any]) -> str:
    """Return the named first-path actor as a readable sentence subject."""

    path_model = first_path_model(first_path(proposal))
    actor = first_path_semantic_view(path_model).primary_actor_signature
    if actor:
        return _actor_subject_phrase(actor)
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        labels = project_specific_actor_labels(intent)
        if labels:
            return _actor_subject_phrase(labels[0])
    return "the first user"


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
    "inline_result_phrase",
    "keywords",
    "lower_first",
    "outcome_action_phrase",
    "outcome_phrase",
    "object_reference_phrase",
    "primary_actor_phrase",
    "primary_component_for_backlog",
    "project_title",
    "proof_capability_phrase",
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
