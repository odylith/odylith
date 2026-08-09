"""Text normalization and presentation projections for recovered confirmations."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.common.prose_grammar import ACTION_MODAL_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_project_title_source
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_repeated_phrase_units
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import lower_plain_title_subject_fragment

MODAL_MARKERS = ACTION_MODAL_WORDS | {"needs", "need"}
LEADING_ARTICLES = frozenset({"a", "an", "the"})
LEADING_CONNECTORS = frozenset({"and", "or", "then"})
PRODUCT_CONTAINER_TERMS = frozenset(
    {
        "app",
        "application",
        "coach",
        "console",
        "coordination",
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
        "ledger",
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
_RESULT_FOCUS_CONTAINER_TERMS = frozenset(
    {
        "app",
        "application",
        "console",
        "dashboard",
        "desk",
        "platform",
        "portal",
        "product",
        "room",
        "service",
        "studio",
        "system",
        "tool",
        "workbench",
        "workspace",
    }
)
_TITLE_OUTCOME_ACTIONS = frozenset(
    {
        "accept",
        "approve",
        "capture",
        "collect",
        "complete",
        "create",
        "display",
        "generate",
        "issue",
        "log",
        "prepare",
        "produce",
        "publish",
        "record",
        "return",
        "save",
        "see",
        "show",
        "submit",
        "surface",
        "verify",
    }
)
_TITLE_STATUS_MODIFIERS = frozenset(
    {"accepted", "approved", "complete", "completed", "confirmed", "final", "ready", "validated", "verified"}
)


def clean_text(value: object) -> str:
    """Return a normalized text value suitable for recovery projections."""

    return clean_markdown_text(value)


def words(value: str) -> list[str]:
    """Return normalized words without markdown or connector prefixes."""

    rows = [
        word.strip("()[]{}\"'.,:;")
        for word in clean_text(value).replace("/", " ").split()
        if word.strip("()[]{}\"'.,:;")
    ]
    while rows and rows[0].casefold() in LEADING_CONNECTORS:
        rows = rows[1:]
    return rows


def word_spans(value: str) -> list[tuple[str, int, int]]:
    """Return normalized word spans for source-preserving grammar repairs."""

    spans = [
        (match.group(0).strip("()[]{}\"'.,:;"), match.start(), match.end())
        for match in re.finditer(r"[A-Za-z][A-Za-z0-9'-]*", clean_text(value).replace("/", " "))
    ]
    rows = [(word, start, end) for word, start, end in spans if word]
    while rows and rows[0][0].casefold() in LEADING_CONNECTORS:
        rows = rows[1:]
    return rows


def strip_leading_articles(values: Sequence[str]) -> list[str]:
    """Drop articles from a normalized token sequence."""

    cleaned = [value for value in values if str(value).strip()]
    while cleaned and cleaned[0].casefold() in LEADING_ARTICLES:
        cleaned = cleaned[1:]
    return cleaned


def looks_plural(value: str) -> bool:
    """Return whether a token uses the simple plural form used by recovery copy."""

    token = str(value or "").casefold().strip(".,:;")
    return len(token) > 3 and token.endswith("s") and not token.endswith(("ous", "ss"))


def indefinite_phrase(value: str) -> str:
    """Prefix a phrase with the appropriate indefinite article when needed."""

    text = clean_text(value).strip(" .")
    if not text:
        return "a request"
    first = text.split(maxsplit=1)[0].casefold()
    if first in LEADING_ARTICLES:
        return text
    text = lower_article_body(text)
    consonant_vowel_prefix = re.match(r"^(?:ewe|euro|one|uni(?:form|que|t|vers)|use|user)", first)
    article = "an" if first[:1] in {"a", "e", "i", "o", "u"} and not consonant_vowel_prefix else "a"
    return f"{article} {text}"


def lower_article_body(value: str) -> str:
    """Lower the first character after an inserted article."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    first, _separator, _tail = text.partition(" ")
    if first.isupper() and len(first) <= 4:
        return text
    if first.casefold() in LEADING_ARTICLES:
        return text
    return f"{text[:1].casefold()}{text[1:]}"


def lower_leading_word(value: str) -> str:
    """Lower only the first character of a recovered clause."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    first = text.split(maxsplit=1)[0]
    if first.isupper() and len(first) <= 6 and first.casefold() not in LEADING_ARTICLES:
        return text
    return f"{text[:1].lower()}{text[1:]}"


def sentence_start(value: str) -> str:
    """Return a normalized sentence with an uppercase first character."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    return f"{text[:1].upper()}{text[1:]}"


def internal_system_rows_from_recovered_title(title: str) -> list[str]:
    """Return standard internal-system rows localized to the recovered title."""

    label = title_case_text(collapse_repeated_phrase_units(clean_text(title) or "Product"))
    return [
        (
            f"{_system_label_with_suffix(label, 'Intake Register')} — records source input, current status, owner, blocker, "
            "handoff, and version history for the first path"
        ),
        (
            f"{_system_label_with_suffix(label, 'Review Workspace')} — presents current state, missing input, user-facing confirmation, "
            "and the next useful action"
        ),
        (
            f"{_system_label_with_suffix(label, 'Proof Ledger')} — keeps validation results, release decisions, failure reasons, "
            "and replayable evidence for review"
        ),
    ]


def _system_label_with_suffix(label: str, suffix: str) -> str:
    head = title_case_text(collapse_repeated_phrase_units(clean_text(label) or "Product"))
    head_words = head.split()
    suffix_words = clean_text(suffix).split()
    head_keys = [word.casefold().strip(".,;:") for word in head_words]
    suffix_keys = [word.casefold().strip(".,;:") for word in suffix_words]
    if suffix_keys and head_keys[-len(suffix_keys) :] == suffix_keys:
        return head
    if len(suffix_keys) > 1 and head_keys and head_keys[-1] == suffix_keys[-1]:
        return title_case_text(collapse_repeated_phrase_units(" ".join([*head_words[:-1], *suffix_words]).strip()))
    return title_case_text(collapse_repeated_phrase_units(" ".join([head, *suffix_words]).strip()))


def stable_outcome_phrase(value: str, *, title: str) -> str:
    """Return a bounded, visible result phrase for the confirmation."""

    text = clean_text(value).strip(" .")
    lowered = text.casefold()
    first_word = lowered.split(maxsplit=1)[0] if lowered.split() else ""
    if (
        not text
        or first_word in LEADING_CONNECTORS
        or word_count(text) > 8
        or _looks_like_status_only_outcome(lowered)
        or _looks_like_generic_result_outcome(lowered)
        or any(f" {marker} " in f" {lowered} " for marker in MODAL_MARKERS)
    ):
        return f"{_title_result_focus(title)} result"
    return text


def _looks_like_status_only_outcome(value: str) -> bool:
    text = f" {clean_text(value).casefold()} "
    return " ready or blocked " in text or " ready or rejected " in text or " ready or accepted " in text


def _looks_like_generic_result_outcome(value: str) -> bool:
    value_words = [word.casefold() for word in words(value)]
    return bool(
        value_words
        and value_words[-1] == "result"
        and set(value_words[:-1]) <= {"a", "an", "the", "visible", "reviewable", "workspace"}
    )


def _title_result_focus(value: str) -> str:
    terms = [
        term.casefold()
        for term in label_terms(value)
        if term.casefold() not in _RESULT_FOCUS_CONTAINER_TERMS
    ]
    while terms and terms[0] in {"at", "by", "for", "from", "of", "on", "to", "with"}:
        terms.pop(0)
    return " ".join(terms).strip(" .") or lower_plain_title_subject_fragment(value, action_offset=0) or "accepted product"


def object_result_phrase(value: str) -> str:
    """Return a result phrase that reads naturally after a definite article."""

    text = clean_text(value).strip(" .")
    if not text:
        return "the first visible result"
    text = lower_plain_title_subject_fragment(text, action_offset=0)
    if text.split(maxsplit=1)[0].casefold() in LEADING_ARTICLES:
        return text
    if text[:2].isupper():
        return f"the {text}"
    return f"the {text[:1].casefold()}{text[1:]}"


def recovered_title(outcome: str) -> str:
    """Derive a product title from a visible outcome phrase."""

    title_source = _title_source_from_outcome(outcome)
    title_words = clean_text(title_source).split()
    if 1 <= len(title_words) <= 8 and title_source.casefold() != "the first visible result":
        title = title_case_text(title_source)
        if _has_product_container_title(title):
            return title
        return f"{title} Workspace"
    return "Recovered Product Workspace"


def _title_source_from_outcome(value: str) -> str:
    title_words = words(clean_text(value).strip(" ."))
    lowered = [word.casefold() for word in title_words]
    for index, token in enumerate(lowered[:12]):
        if token not in {"are", "is", "must", "need", "needs"}:
            continue
        start = index + 1
        if token in {"must", "need", "needs"} and start < len(lowered) and lowered[start] == "to":
            start += 1
        if start < len(lowered) and lowered[start].endswith("ing"):
            start += 1
        title_words = title_words[start:]
        lowered = lowered[start:]
        break
    action = lowered[0] if lowered else ""
    if action in _TITLE_OUTCOME_ACTIONS or (action.endswith("s") and action[:-1] in _TITLE_OUTCOME_ACTIONS):
        title_words = title_words[1:]
    while title_words and title_words[0].casefold() in {*LEADING_ARTICLES, "one"}:
        title_words = title_words[1:]
    while len(title_words) > 1 and title_words[0].casefold() in _TITLE_STATUS_MODIFIERS:
        title_words = title_words[1:]
    boundary = next(
        (
            index
            for index, word in enumerate(title_words)
            if word.casefold() in {"after", "before", "between", "through"}
        ),
        len(title_words),
    )
    title_words = title_words[:boundary]
    with_index = next(
        (index for index, word in enumerate(title_words) if word.casefold() == "with"),
        None,
    )
    if with_index is not None:
        head = title_words[:with_index]
        if len(head) >= 3 and head[-1].casefold() in {"decision", "packet", "record", "report", "summary"}:
            title_words = head
    if len(title_words) > 1 and title_words[-1].casefold() in {"outcome", "output", "result"}:
        title_words = title_words[:-1]
    return " ".join(title_words).strip(" .")


def _has_product_container_title(value: str) -> bool:
    terms = [term.casefold() for term in label_terms(value)]
    if terms and terms[-1] in PRODUCT_CONTAINER_TERMS:
        return True
    title_words = [word.casefold().strip(".,:;") for word in words(value)]
    return any(
        word in PRODUCT_CONTAINER_TERMS and title_words[index + 1] in {"for", "with"}
        for index, word in enumerate(title_words[:-1])
    )


def actor_reference(value: str) -> str:
    """Return a grammatical reference to a recovered human actor."""

    text = lower_plain_title_subject_fragment(value, action_offset=0).strip(" .")
    if not text:
        return "a product user"
    if len(text.split()) == 1 and not text.isupper():
        text = text.casefold()
    if text.split(maxsplit=1)[0].casefold() in LEADING_ARTICLES:
        return text
    if looks_plural(text.split()[-1]):
        return text
    return indefinite_phrase(text)


def actor_verb(value: str, *, singular: str, plural: str) -> str:
    """Choose a verb form that agrees with a recovered actor label."""

    value_words = words(value)
    if value_words and looks_plural(value_words[-1]):
        return plural
    return singular


def recovered_story_text(
    *,
    title: str,
    lead_actor_ref: str,
    first_path_inline: str,
    outcome_object: str,
) -> str:
    """Render recovered product-story copy from bounded confirmation facts."""

    first_path = sentence_start(first_path_inline)
    if "." in first_path_inline:
        opening = f"{title} helps {lead_actor_ref} complete this first path: {first_path}."
    else:
        opening = f"{title} helps {lead_actor_ref} complete a first path where {lower_leading_word(first_path_inline)}."
    return (
        f"{opening} It keeps {outcome_object} tied to source input, current state, blockers, handoffs, "
        "and proof evidence so the next step is clear."
    )


def recovered_proof_text(*, first_path_inline: str, outcome_object: str) -> str:
    """Render recovered proof-boundary copy from the first path and outcome."""

    if "." in first_path_inline:
        opening = "Release 0.0.1 succeeds when the accepted first path is complete, reviewable, and blocked when required."
    else:
        opening = f"Release 0.0.1 succeeds when {lower_leading_word(first_path_inline)}."
    return (
        f"{opening} The product shows {outcome_object}. It explains missing or invalid input with a clear blocker "
        "and keeps replayable evidence for review."
    )


def product_view_result_sentence(outcome_object: str, *, lead_action: str) -> str:
    """Return a result sentence only when it adds information beyond the lead action."""

    outcome = clean_text(outcome_object).strip(" .")
    if not outcome or word_count(outcome) < 3:
        return ""
    lead = clean_text(lead_action).casefold()
    if outcome.casefold() in lead and not (
        re.search(r"\binto\b", lead) and re.match(r"^(?:a|an|the)\s+final\b", outcome, flags=re.IGNORECASE)
    ):
        return ""
    return f"The visible result is {outcome}. "


def recover_title_source(source: str) -> str:
    """Recover a narrow product-title source before generic title completion."""

    title = prompt_project_title_source(source)
    if title:
        return title
    text = clean_text(source).strip(" .")
    source_words = words(text)
    if len(source_words) < 2 or len(source_words) > 8:
        return ""
    lowered = {word.casefold().strip(".,:;") for word in source_words}
    if lowered & {"confirm", "confirmation", "format", "intent", "needed", "original", "sectioned", "visible"}:
        return ""
    if lowered <= LEADING_ARTICLES or any(marker in lowered for marker in MODAL_MARKERS):
        return ""
    if looks_like_action_clause(text) or first_path_model(text).material_action:
        return ""
    return " ".join(source_words).strip(" .")
