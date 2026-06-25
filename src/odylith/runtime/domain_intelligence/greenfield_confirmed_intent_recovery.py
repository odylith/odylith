"""Synthetic Product Intent Confirmation recovery from host guidance envelopes."""

from __future__ import annotations

import re
from collections.abc import Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_first_path_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_project_title_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import nominal_visible_result_object
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import lower_plain_title_subject_fragment

_MODAL_MARKERS = frozenset({"can", "will", "must", "needs", "need"})
_LEADING_ARTICLES = frozenset({"a", "an", "the"})
_LEADING_CONNECTORS = frozenset({"and", "or", "then"})
_NON_HUMAN_ACTOR_TERMS = frozenset(
    {
        "api",
        "application",
        "board",
        "builder",
        "controller",
        "database",
        "device",
        "engine",
        "executor",
        "hardware",
        "ledger",
        "manager",
        "model",
        "monitor",
        "notebook",
        "platform",
        "policy",
        "product",
        "proof",
        "record",
        "register",
        "sensor",
        "service",
        "software",
        "system",
        "tool",
        "workbench",
        "workspace",
    }
)
_HUMAN_ACTOR_TERMS = frozenset(
    {
        "admin",
        "analyst",
        "approver",
        "coordinator",
        "customer",
        "designer",
        "employee",
        "guest",
        "manager",
        "member",
        "operator",
        "owner",
        "participant",
        "person",
        "planner",
        "reviewer",
        "staff",
        "supervisor",
        "user",
        "worker",
    }
)
_HUMAN_ROLE_SUFFIXES = ("ant", "ent", "er", "ian", "ist", "or", "ee", "owner")
_MATERIAL_FRAGMENT_ACTION_WORDS = frozenset(
    {
        "approval",
        "context",
        "decision",
        "design",
        "details",
        "documentation",
        "evidence",
        "paperwork",
        "plan",
        "readiness",
        "record",
        "report",
        "review",
        "status",
        "summary",
    }
)
_PRODUCT_CONTAINER_TERMS = frozenset(
    {
        "app",
        "application",
        "coach",
        "console",
        "controller",
        "board",
        "builder",
        "dashboard",
        "desk",
        "engine",
        "experience",
        "executor",
        "hub",
        "journal",
        "logbook",
        "manager",
        "monitor",
        "notebook",
        "platform",
        "planner",
        "portal",
        "product",
        "room",
        "service",
        "studio",
        "system",
        "tool",
        "tracker",
        "workbench",
        "workspace",
    }
)


def confirmation_from_operator_intent(intent_text: str, *, prefer_product_title: bool = False) -> str:
    """Return a structured confirmation when the host passed guidance instead of the visible answer."""

    source = _clean(intent_text).strip(" .")
    recovered_first_path_source = prompt_first_path_source(source)
    title_source = _recover_title_source(source) if prefer_product_title else ""
    title = _recovered_title(title_source or first_path_outcome_phrase(recovered_first_path_source, fallback=""))
    first_path_source = _usable_first_path_source(recovered_first_path_source, title=title) or _generic_first_path_source(title)
    actor_rows = _human_actor_rows_from_first_path(first_path_source, title=title)
    lead_actor = _lead_actor_label(actor_rows) or _fallback_actor_label(title)
    lead_action = _lead_actor_action(actor_rows) or base_action_clause(first_path_source)
    outcome = _stable_outcome_phrase(
        first_path_outcome_phrase(first_path_source, fallback=""),
        title=title,
    )
    outcome_object = _object_result_phrase(outcome)
    lead_actor_ref = _actor_reference(lead_actor)
    lead_needs = _actor_verb(lead_actor, singular="needs", plural="need")
    first_path_inline = _embedded_first_path_clause(first_path_source.rstrip("."))
    first_path = _sentence_start(first_path_inline)
    story = _recovered_story_text(
        title=title,
        lead_actor_ref=lead_actor_ref,
        first_path_inline=first_path_inline,
        outcome_object=outcome_object,
    )
    state_subject = _state_record_subject(outcome)
    state = (
        f"{_sentence_start(_indefinite_phrase(state_subject))} record tracks the actor, source input, current status, owner, "
        "blocker, handoff, evidence, and version history for the first path."
    )
    proof = _recovered_proof_text(first_path_inline=first_path_inline, outcome_object=outcome_object)
    problem = (
        f"{lead_actor} {lead_needs} a dependable way to {lead_action.rstrip('.')} and trust the result without stitching "
        "together scattered context."
    )
    product_view = (
        f"{title} earns trust when {lead_actor_ref} can {lead_action.rstrip('.')} and the result remains "
        "visible, blocked when needed, and reviewable."
    )
    actor_lines = "\n".join(f"- {row}" for row in actor_rows)
    system_lines = "\n".join(f"- {row}" for row in _internal_system_rows_from_recovered_title(title))
    return "\n\n".join(
        (
            f"# {title} - Product Intent Confirmation",
            "Product story\n" + story,
            "State object\n" + state,
            "First complete path\n" + first_path.rstrip(".") + ".",
            "Human actors\n" + actor_lines,
            "External systems\n",
            "Internal product systems\n" + system_lines,
            "Problem\n" + problem,
            "Opportunity\n" + f"Prove the smallest complete {title.lower()} path before broader automation expands.",
            "Product view\n" + product_view,
            "Success metrics\n"
            + "\n".join(
                (
                    f"- {lead_actor} can {lead_action.rstrip('.')} and see the visible result.",
                    "- Missing or invalid input produces a clear blocker instead of a false success.",
                    f"- Review evidence backs {outcome_object} with replayable proof.",
                )
            ),
            "Critical assumptions\n- Release 0.0.1 proves the first path before broader automation or live integrations.",
            "Ambiguities\n- The exact exception policies, integration depth, and operational ownership can be refined after the first proof path is accepted.",
            "Proof boundary\n" + proof,
        )
    )


def _usable_first_path_source(value: str, *, title: str) -> str:
    text = _clean(value).strip(" .")
    if not text or _path_source_restates_title(text, title=title):
        return ""
    model = first_path_model(text)
    if len(model.steps) >= 2:
        if _preserve_one_line_capability_source(text):
            return text
        return _first_path_source_from_steps(model.steps) or text
    if word_count(text) >= 6 and (model.material_action or model.visible_outcome):
        return text
    return ""


def _first_path_source_from_steps(steps: Sequence[str]) -> str:
    rows = [_clean(step).strip(" .") for step in steps if _clean(step).strip(" .")]
    return ". ".join(rows)


def _preserve_one_line_capability_source(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or any(mark in text for mark in ".!?"):
        return False
    return "can" in {word.casefold().strip(".,:;") for word in text.split()}


def _path_source_restates_title(value: str, *, title: str) -> bool:
    value_terms = _semantic_terms(value)
    title_terms = _semantic_terms(title)
    return bool(value_terms and title_terms and value_terms <= title_terms)


def _semantic_terms(value: str) -> set[str]:
    terms: set[str] = set()
    for term in label_terms(value):
        for token in str(term).casefold().replace("-", " ").replace("/", " ").split():
            if token not in _LEADING_ARTICLES:
                terms.add(token)
    return terms


def _generic_first_path_source(title: str) -> str:
    request = _indefinite_phrase(f"{lower_plain_title_subject_fragment(title, action_offset=0)} request")
    actor = _indefinite_phrase(f"{lower_plain_title_subject_fragment(title, action_offset=0)} user")
    return (
        f"{actor[:1].upper()}{actor[1:]} starts {request}, the product records required information, "
        "the product shows a reviewable result, and the product marks the request ready or blocked"
    )


def _embedded_first_path_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    clause = _lower_leading_word(text)
    if looks_like_action_clause(clause):
        clause = f"the product {clause}"
    return clause


def _recovered_story_text(
    *,
    title: str,
    lead_actor_ref: str,
    first_path_inline: str,
    outcome_object: str,
) -> str:
    first_path = _sentence_start(first_path_inline)
    if "." in first_path_inline:
        opening = f"{title} helps {lead_actor_ref} complete this first path: {first_path}."
    else:
        opening = f"{title} helps {lead_actor_ref} complete a first path where {first_path_inline}."
    return (
        f"{opening} It keeps {outcome_object} tied to source input, current state, blockers, handoffs, "
        "and proof evidence so the next step is clear."
    )


def _recovered_proof_text(*, first_path_inline: str, outcome_object: str) -> str:
    first_path = _sentence_start(first_path_inline)
    if "." in first_path_inline:
        opening = f"Release 0.0.1 succeeds when this first path is complete: {first_path}."
    else:
        opening = f"Release 0.0.1 succeeds when {first_path_inline}."
    return (
        f"{opening} The product shows {outcome_object}, handles missing or invalid input with a clear blocker, "
        "and keeps replayable evidence for review."
    )


def _recover_title_source(source: str) -> str:
    title = prompt_project_title_source(source)
    if title:
        return title
    return _direct_product_title_source(source)


def _direct_product_title_source(source: str) -> str:
    text = _clean(source).strip(" .")
    words = _words(text)
    if len(words) < 2 or len(words) > 8:
        return ""
    lowered = {word.casefold().strip(".,:;") for word in words}
    if lowered & {"confirm", "confirmation", "format", "intent", "needed", "original", "sectioned", "visible"}:
        return ""
    if lowered <= _LEADING_ARTICLES:
        return ""
    if any(marker in lowered for marker in _MODAL_MARKERS):
        return ""
    if looks_like_action_clause(text) or first_path_model(text).material_action:
        return ""
    return " ".join(words).strip(" .")


def _indefinite_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "a request"
    first = text.split(maxsplit=1)[0].casefold()
    if first in _LEADING_ARTICLES:
        return text
    text = _lower_article_body(text)
    first = text.split(maxsplit=1)[0].casefold()
    article = "an" if first[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def _lower_article_body(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    first, _separator, _tail = text.partition(" ")
    if first.isupper() and len(first) <= 4:
        return text
    if first.casefold() in _LEADING_ARTICLES:
        return text
    return f"{text[:1].casefold()}{text[1:]}"


def _lower_leading_word(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return f"{text[:1].lower()}{text[1:]}"


def _sentence_start(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return f"{text[:1].upper()}{text[1:]}"


def _human_actor_rows_from_first_path(value: str, *, title: str = "") -> list[str]:
    rows: list[str] = []
    seen_labels: set[str] = set()
    for clause in _first_path_actor_clauses(value):
        row = _human_actor_row_from_clause(clause, allow_subject_fallback=not rows)
        label = row.split(":", 1)[0].casefold() if row else ""
        if row and label not in seen_labels:
            seen_labels.add(label)
            rows.append(row)
    if rows:
        return rows[:3]
    return [f"{_fallback_actor_label(title)}: needs the product to complete the first path and keep the result visible and reviewable"]


def _fallback_actor_label(title: str) -> str:
    label = _clean(title).strip(" .") or "Product"
    return f"{label} User"


def _first_path_actor_clauses(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    clauses = _split_actor_candidate_clauses(text)
    model_steps = [_clean(step) for step in first_path_model(text).steps if _clean(step)]
    if model_steps:
        clauses.extend(model_steps)
    return _unique_clauses(clauses)


def _split_actor_candidate_clauses(text: str) -> list[str]:
    clauses: list[str] = []
    for part in re.split(r";\s+|,\s+|(?<=[.!?])\s+", text):
        part = _clean(part)
        if not part:
            continue
        for subpart in part.split(" and "):
            cleaned = _clean(subpart)
            clauses.extend(_purpose_split_actor_clauses(cleaned))
    return clauses


def _purpose_split_actor_clauses(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    parts = [part for part in re.split(r"\s+so\s+", text, maxsplit=1, flags=re.IGNORECASE) if _clean(part)]
    if len(parts) != 2:
        return [text]
    prefix, suffix = (_clean(parts[0]), _clean(parts[1]))
    suffix_words = _words(suffix)
    if _first_word_index(suffix_words, _MODAL_MARKERS) > 0:
        rows = []
        if prefix:
            rows.append(prefix)
        rows.append(suffix)
        return rows
    return [text]


def _unique_clauses(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


def _human_actor_row_from_clause(clause: str, *, allow_subject_fallback: bool) -> str:
    relative = re.match(
        r"^(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+(?:who|that)\s+(?P<action>.+)$",
        _clean(clause),
        flags=re.IGNORECASE,
    )
    if relative:
        row = _human_actor_row(relative.group("actor"), relative.group("action"))
        if row:
            return row
    words = _words(clause)
    if len(words) < 2:
        return ""
    if _starts_with_action_without_actor(clause):
        return ""
    marker_index = _first_word_index(words, _MODAL_MARKERS)
    if marker_index > 0 and marker_index + 1 < len(words):
        actor = " ".join(words[:marker_index])
        action = " ".join(words[marker_index + 1 :])
        return _human_actor_row(actor, action)
    action_index = _action_start_index(words)
    if action_index > 0:
        actor = " ".join(words[:action_index])
        action = " ".join(words[action_index:])
        if _looks_like_material_actor_fragment(words[:action_index], words[action_index:]):
            return ""
        return _human_actor_row(actor, action)
    fallback = _plural_subject_fallback(words, allow_single_subject=allow_subject_fallback)
    if fallback:
        actor, action = fallback
        return _human_actor_row(actor, action)
    return ""


def _looks_like_material_actor_fragment(actor_words: Sequence[str], action_words: Sequence[str]) -> bool:
    cleaned_actor = _strip_leading_articles(actor_words)
    if not cleaned_actor or not action_words:
        return False
    if len(cleaned_actor) != 1:
        return False
    raw_actor_has_article = bool(actor_words and actor_words[0].casefold() in _LEADING_ARTICLES)
    actor_token = cleaned_actor[0].casefold().strip(".,:;")
    action_token = action_words[0].casefold().strip(".,:;")
    if raw_actor_has_article or _looks_plural(actor_token):
        return False
    if _semantic_terms(actor_token) & _HUMAN_ACTOR_TERMS or _looks_like_human_actor_token(actor_token):
        return False
    return action_token in _MATERIAL_FRAGMENT_ACTION_WORDS


def _looks_like_human_actor_token(value: str) -> bool:
    token = str(value or "").casefold().strip(".,:;")
    return len(token) >= 5 and token.endswith(_HUMAN_ROLE_SUFFIXES)


def _starts_with_action_without_actor(clause: str) -> bool:
    text = re.sub(r"^(?:and|or|then)\s+", "", _clean(clause), flags=re.IGNORECASE)
    if not looks_like_action_clause(text):
        return False
    words = _strip_leading_articles(_words(text))
    if len(words) < 2:
        return False
    if _first_word_index(words, _MODAL_MARKERS) > 0:
        return False
    leading_terms = {term.casefold() for term in label_terms(words[0])}
    if leading_terms & _HUMAN_ACTOR_TERMS:
        return False
    if _looks_plural(words[0]) and not contains_finite_action(words[0]):
        return False
    return True


def _action_start_index(words: Sequence[str]) -> int:
    for index in range(1, max(1, len(words) - 1)):
        if looks_like_action_clause(" ".join(words[index:])):
            return index
    return -1


def _first_word_index(words: Sequence[str], targets: set[str] | frozenset[str]) -> int:
    for index, word in enumerate(words):
        if word.casefold() in targets:
            return index
    return -1


def _human_actor_row(actor: str, action: str) -> str:
    actor_words = _strip_leading_articles(_words(actor))
    actor_label = title_case_text(" ".join(actor_words))
    action_text = base_action_clause(_primary_actor_action_segment(action))
    if _starts_with_relation_word(actor_label) or _starts_with_relation_word(action_text):
        return ""
    if not actor_label or not action_text or _looks_like_non_human_actor(actor_label):
        return ""
    need_verb = _actor_verb(actor_label, singular="needs", plural="need")
    return f"{actor_label}: {need_verb} the product to {action_text} and keep the result visible and reviewable"


def _starts_with_relation_word(value: str) -> bool:
    words = _words(value)
    return bool(
        words
        and words[0].casefold()
        in {"and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "then", "to", "with", "without"}
    )


def _primary_actor_action_segment(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    return text.replace(";", ",").split(",", 1)[0].strip(" .")


def _looks_like_non_human_actor(value: str) -> bool:
    terms = {term.casefold() for term in label_terms(value)}
    role_terms = terms | {term[:-1] for term in terms if term.endswith("s")}
    if role_terms & _HUMAN_ACTOR_TERMS:
        return False
    return bool(terms & _NON_HUMAN_ACTOR_TERMS)


def _plural_subject_fallback(words: Sequence[str], *, allow_single_subject: bool) -> tuple[str, str]:
    cleaned = _strip_leading_articles(words)
    if len(cleaned) < 3:
        return ("", "")
    if len(cleaned) >= 4 and _looks_plural(cleaned[1]):
        return (" ".join(cleaned[:2]), " ".join(cleaned[2:]))
    if allow_single_subject and _looks_plural(cleaned[0]):
        return (cleaned[0], " ".join(cleaned[1:]))
    if _looks_plural(cleaned[0]) and len(cleaned) >= 3:
        return (cleaned[0], " ".join(cleaned[1:]))
    return ("", "")


def _looks_plural(value: str) -> bool:
    token = str(value or "").casefold().strip(".,:;")
    return len(token) > 3 and token.endswith("s") and not token.endswith("ss")


def _lead_actor_label(actor_rows: Sequence[str]) -> str:
    for row in actor_rows:
        label, _, _body = str(row).partition(":")
        label = _clean(label)
        if label:
            return label
    return ""


def _lead_actor_action(actor_rows: Sequence[str]) -> str:
    for row in actor_rows:
        _label, _separator, body = str(row).partition(":")
        for marker in ("needs the product to ", "need the product to "):
            if marker in body:
                return body.split(marker, 1)[1].split(" and keep ", 1)[0].strip(" .")
    return ""


def _internal_system_rows_from_recovered_title(title: str) -> list[str]:
    label = title_case_text(_clean(title) or "Product")
    return [
        (
            f"{label} Intake Register - records source input, current status, owner, blocker, "
            "handoff, and version history for the first path"
        ),
        (
            f"{label} Review Workspace - presents current state, missing input, user-facing confirmation, "
            "and the next useful action"
        ),
        (
            f"{label} Proof Ledger - keeps validation results, release decisions, failure reasons, "
            "and replayable evidence for review"
        ),
    ]


def _stable_outcome_phrase(value: str, *, title: str) -> str:
    text = _clean(value).strip(" .")
    lowered = text.casefold()
    first_word = lowered.split(maxsplit=1)[0] if lowered.split() else ""
    if (
        not text
        or first_word in _LEADING_CONNECTORS
        or word_count(text) > 8
        or _looks_like_status_only_outcome(lowered)
        or _looks_like_generic_result_outcome(lowered)
        or any(f" {marker} " in f" {lowered} " for marker in _MODAL_MARKERS)
    ):
        return f"{lower_plain_title_subject_fragment(title, action_offset=0)} result"
    return text


def _looks_like_status_only_outcome(value: str) -> bool:
    text = f" {_clean(value).casefold()} "
    return " ready or blocked " in text or " ready or rejected " in text or " ready or accepted " in text


def _looks_like_generic_result_outcome(value: str) -> bool:
    words = [word.casefold() for word in _words(value)]
    return bool(words and words[-1] == "result" and set(words[:-1]) <= {"a", "an", "the", "visible", "reviewable"})


def _object_result_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "the first visible result"
    text = lower_plain_title_subject_fragment(text, action_offset=0)
    if text.split(maxsplit=1)[0].casefold() in _LEADING_ARTICLES:
        return text
    if text[:2].isupper():
        return f"the {text}"
    return f"the {text[:1].casefold()}{text[1:]}"


def _state_record_subject(value: str) -> str:
    text = lower_plain_title_subject_fragment(_clean(value), action_offset=0).strip(" .")
    if not text:
        return "first visible result"
    action_object = _actor_action_object(text)
    if action_object:
        text = nominal_visible_result_object(action_object).strip(" .") or action_object
    words = _strip_leading_articles(_words(text))
    if len(words) >= 3 and words[0].casefold() == "only":
        words = words[1:]
    if words and words[-1].casefold() == "record":
        words = words[:-1]
    return " ".join(words).strip(" .") or "first visible result"


def _actor_action_object(value: str) -> str:
    words = _words(value)
    if len(words) < 3:
        return ""
    max_subject_words = min(4, len(words) - 2)
    for verb_index in range(1, max_subject_words + 1):
        verb = words[verb_index].casefold().strip(".,:;")
        if not (looks_like_base_action_token(verb) or looks_like_finite_action_token(verb)):
            continue
        subject = words[:verb_index]
        if not _looks_like_actor_subject(subject):
            continue
        obj = " ".join(words[verb_index + 1 :]).strip(" .")
        if obj.casefold().startswith("when "):
            obj = obj[5:].strip(" .")
        return obj
    return ""


def _looks_like_actor_subject(words: Sequence[str]) -> bool:
    cleaned = _strip_leading_articles(words)
    if not cleaned:
        return False
    last = cleaned[-1].casefold().strip(".,:;")
    singular = last[:-1] if last.endswith("s") else last
    if singular in _HUMAN_ACTOR_TERMS or last in _HUMAN_ACTOR_TERMS:
        return True
    if any(singular.endswith(suffix) or last.endswith(suffix) for suffix in _HUMAN_ROLE_SUFFIXES):
        return True
    return False


def _recovered_title(outcome: str) -> str:
    title_source = _title_source_from_outcome(outcome)
    words = _clean(title_source).split()
    if 1 <= len(words) <= 8 and title_source.casefold() != "the first visible result":
        title = title_case_text(title_source)
        if _has_product_container_title(title):
            return title
        return f"{title} Workspace"
    return "Recovered Product Workspace"


def _title_source_from_outcome(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(
        r"^(?:accept|approve|capture|collect|complete|create|display|generate|issue|log|prepare|produce|publish|record|return|save|show|submit|surface|verify)\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        text = re.sub(r"^(?:a|an|the|one)\s+", "", match.group("object").strip(" ."), flags=re.IGNORECASE)
    if " with " in f" {text.casefold()} ":
        parts = re.split(r"\s+with\s+", text, maxsplit=1, flags=re.IGNORECASE)
        head = parts[0].strip(" .")
        head_words = _words(head)
        if len(head_words) >= 3 and head_words[-1].casefold() in {"decision", "packet", "record", "report", "summary"}:
            text = head
    return text


def _has_product_container_title(value: str) -> bool:
    terms = [term.casefold() for term in label_terms(value)]
    if terms and terms[-1] in _PRODUCT_CONTAINER_TERMS:
        return True
    words = [word.casefold().strip(".,:;") for word in _words(value)]
    for index, word in enumerate(words[:-1]):
        if word in _PRODUCT_CONTAINER_TERMS and words[index + 1] in {"for", "with"}:
            return True
    return False


def _actor_reference(value: str) -> str:
    text = lower_plain_title_subject_fragment(value, action_offset=0).strip(" .")
    if not text:
        return "a product user"
    if len(text.split()) == 1 and not text.isupper():
        text = text.casefold()
    if text.split(maxsplit=1)[0].casefold() in _LEADING_ARTICLES:
        return text
    if _looks_plural(text.split()[-1]):
        return text
    return f"a {text}"


def _actor_verb(value: str, *, singular: str, plural: str) -> str:
    words = _words(value)
    if words and _looks_plural(words[-1]):
        return plural
    return singular


def _strip_leading_articles(words: Sequence[str]) -> list[str]:
    cleaned = [word for word in words if str(word).strip()]
    while cleaned and cleaned[0].casefold() in _LEADING_ARTICLES:
        cleaned = cleaned[1:]
    return cleaned


def _words(value: str) -> list[str]:
    words = [
        word.strip("()[]{}\"'.,:;")
        for word in _clean(value).replace("/", " ").split()
        if word.strip("()[]{}\"'.,:;")
    ]
    while words and words[0].casefold() in _LEADING_CONNECTORS:
        words = words[1:]
    return words


def _clean(value: object) -> str:
    return clean_markdown_text(value)


__all__ = ["confirmation_from_operator_intent"]
