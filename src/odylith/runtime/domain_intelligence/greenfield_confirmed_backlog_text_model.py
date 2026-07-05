"""Text model helpers for confirmed greenfield Radar workstreams."""

from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import gerund_action_verb
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import drop_adjacent_duplicate_words
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import has_problem_tension
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import looks_mechanical_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import proof_claim_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import proof_focus_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import rationale_deferred_focus
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import rationale_lines
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import rationale_proof_focus
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import rationale_release_basis
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import rationale_scope_focus
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import result_content_words
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import result_terms_covered
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import semantic_words
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import sentence_fragment
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import shares_product_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_repeated_phrase_units
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_text import imperative_action_with_copula_words

_DEFERRED_ACTOR_MARKERS = (
    "deferred",
    "fast-follow",
    "future",
    "later",
    "not first path",
    "not in the first path",
    "optional",
    "read-only",
    "separate release",
)
_SHORT_ACTOR_ROLE_WORDS = frozenset(
    {
        "actor",
        "admin",
        "administrator",
        "applicant",
        "coordinator",
        "customer",
        "editor",
        "lead",
        "manager",
        "operator",
        "owner",
        "participant",
        "reviewer",
        "user",
    }
)
_ACTOR_LABEL_CLAUSE_BOUNDARIES = frozenset({"after", "before", "once", "until", "when", "while", "without"})
_ACTOR_LABEL_EVENT_TAILS = frozenset(
    {
        "approval",
        "approvals",
        "decision",
        "decisions",
        "evidence",
        "handoff",
        "handoffs",
        "proof",
        "readiness",
        "report",
        "reports",
        "review",
        "reviews",
        "signoff",
        "signoffs",
        "status",
    }
)
_STATE_BOUNDARY_FOCUS_WORDS = frozenset(
    {
        "approval",
        "assessment",
        "check",
        "comparison",
        "decision",
        "eligibility",
        "evaluation",
        "quality",
        "review",
        "risk",
        "rule",
        "scoring",
        "validation",
    }
)
_STATE_BOUNDARY_GENERIC_NEIGHBORS = frozenset(
    {"app", "component", "platform", "product", "service", "system", "tool", "workspace"}
)


def join_actor_labels(values: list[str] | None, *, limit: int = 5) -> str:
    labels: list[str] = []
    for value in values or []:
        if is_deferred_actor(str(value)):
            continue
        label = _label_head(str(value))
        if label and label.casefold() not in {"other accepted items"}:
            labels.append(label)
    selected = list(dict.fromkeys(labels))[:limit]
    if not selected:
        return ""
    return ", ".join(selected)


def first_release_actor_rows(values: list[str] | None) -> list[str]:
    rows = [str(value) for value in values or [] if str(value).strip()]
    first_release = [value for value in rows if not is_deferred_actor(value)]
    return first_release or rows


def first_release_problem_summary(value: str, human_actors: list[str]) -> str:
    if not value:
        return ""
    deferred_labels = [
        actor_label(actor)
        for actor in human_actors
        if is_deferred_actor(actor) and actor_label(actor)
    ]
    if _mentions_actor_label(value, deferred_labels):
        return ""
    return value


def _mentions_actor_label(value: str, labels: list[str]) -> bool:
    text = str(value or "").casefold()
    for label in labels:
        normalized = str(label or "").strip(" .").casefold()
        if normalized and normalized in text:
            return True
    return False


def is_deferred_actor(value: str) -> bool:
    text = _compact_text(value).casefold()
    return bool(text and any(marker in text for marker in _DEFERRED_ACTOR_MARKERS))


def actor_label(value: str) -> str:
    return role_label_fragment(_actor_title_head(value))


def actor_from_action(value: str) -> str:
    actor, _action = actor_action_parts(value)
    return actor


def generic_title_outcome(value: str) -> bool:
    text = sentence_fragment(value).casefold()
    return bool(
        not text
        or text in {"next action", "next step", "what happens next", "a visible result", "a visible, useful result"}
        or re.fullmatch(r"(?:a|an|the)?\s*(?:result|outcome|summary|view|status)", text)
        or word_count(text) > 7
        or text.startswith(("whether ", "the tracked metrics ", "tracked metrics "))
    )


def state_changer_label(labels: Sequence[str], *, state_label: str) -> str:
    state_terms = semantic_words(state_label)
    for label in labels[1:3]:
        cleaned = sentence_fragment(label).strip(" .")
        if not cleaned:
            continue
        if re.search(r"\b(?:experience guide|product record|evidence log|release guardrail)\b", cleaned, re.IGNORECASE):
            continue
        if not re.search(
            r"\b(?:approval|assessment|check|comparison|decision|eligibility|evaluation|quality|review|risk|rule|scoring|validation)\b",
            cleaned,
            re.IGNORECASE,
        ):
            continue
        label_terms = semantic_words(cleaned)
        if state_terms and label_terms and len(state_terms & label_terms) / max(1, min(len(state_terms), len(label_terms))) >= 0.75:
            continue
        if re.search(r"\b(?:queue|view|dashboard|summary|report|export|display)\b", cleaned, re.IGNORECASE):
            continue
        return cleaned
    return ""


def state_boundary_focus(value: str) -> str:
    """Return a compact review/action focus for state-boundary workstream titles."""

    text = sentence_fragment(value).strip(" .")
    words = text.split()
    if len(words) <= 5:
        return text
    lowered = [word.casefold().strip(".,;:") for word in words]
    for index, token in enumerate(lowered):
        if token not in _STATE_BOUNDARY_FOCUS_WORDS:
            continue
        start = index
        if index > 0 and lowered[index - 1] not in _STATE_BOUNDARY_GENERIC_NEIGHBORS:
            start = index - 1
        focus = " ".join(words[start : index + 1]).strip(" .")
        return f"{focus} workflow" if len(focus.split()) == 1 else focus
    return text


def lead_actor_label(values: list[str]) -> str:
    for value in values:
        text = _actor_title_head(str(value))
        text = re.split(r"\b(?:who|that|for|and)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
        if not text:
            continue
        return role_label_fragment(text)
    return "someone"


def supporting_actor_label(values: list[str]) -> str:
    for value in values[1:]:
        if is_deferred_actor(str(value)):
            continue
        text = _actor_title_head(str(value))
        text = re.split(r"\b(?:who|that|for|and)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
        if not text:
            continue
        return role_label_fragment(text)
    return ""


def _actor_title_head(value: str) -> str:
    text = _label_head(value)
    text, clipped_by_boundary = _trim_actor_context_tail(text)
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip(" .")
    words = text.split()
    if clipped_by_boundary:
        words = _drop_contextual_event_tail(words)
    for index, word in enumerate(words[1:], start=1):
        token = word.casefold().strip(".,;:")
        next_token = words[index + 1].casefold().strip(".,;:") if index + 1 < len(words) else ""
        if token.endswith("ing") and (len(words[:index]) >= 2 or next_token in {"a", "an", "the"}):
            words = words[:index]
            break
    if len(words) > 1 and words[-1].casefold() in {"person", "people", "individual"}:
        previous = words[-2].casefold()
        if previous in {"individual", "person", "people", "user", "customer", "owner"}:
            words = words[:-1]
    if len(words) > 4:
        words = words[:_actor_title_word_limit(words)]
    return " ".join(words).strip(" .")


def _trim_actor_context_tail(value: str) -> tuple[str, bool]:
    words = _compact_text(value).split()
    for index, word in enumerate(words[1:], start=1):
        token = word.casefold().strip(".,;:")
        if token in _ACTOR_LABEL_CLAUSE_BOUNDARIES:
            return " ".join(words[:index]).strip(" ."), True
    return " ".join(words).strip(" ."), False


def _drop_contextual_event_tail(words: Sequence[str]) -> list[str]:
    cleaned = list(words)
    while len(cleaned) > 1 and cleaned[-1].casefold().strip(".,;:") in _ACTOR_LABEL_EVENT_TAILS:
        cleaned.pop()
    return cleaned


def _actor_title_word_limit(words: Sequence[str]) -> int:
    if len(words) <= 4:
        return len(words)
    lowered = [word.casefold().strip(".,;:") for word in words]
    if lowered[-1] in _SHORT_ACTOR_ROLE_WORDS:
        return min(len(words), 6)
    if any(word in {"and", "or"} for word in lowered[:4]) and any(
        word in _SHORT_ACTOR_ROLE_WORDS for word in lowered[4:6]
    ):
        return min(len(words), 6)
    return 4


def _label_head(value: str) -> str:
    text = _compact_text(value)
    text = re.split(r"\s+[\u2013\u2014-]\s+", text, maxsplit=1)[0]
    return text.split(":", 1)[0].strip(" .")


def imperative_action_phrase(first_path: str) -> str:
    text = sentence_fragment(
        first_path_action_phrase(
            first_path,
            fallback=first_action_clause(first_path) or "complete the accepted path",
            max_fragments=1,
            limit=120,
        )
    ).strip(" .")
    if not text:
        return ""
    actor, action_without_actor = actor_action_parts(text)
    if actor and action_without_actor:
        return normalize_action_clause(action_without_actor)
    return capability_action_clause(text)


def base_title_verb(value: str) -> str:
    token = str(value or "").casefold()
    overrides = {
        "chooses": "choose",
        "does": "do",
        "goes": "go",
        "has": "have",
        "is": "be",
        "receives": "receive",
        "sees": "see",
        "uses": "use",
    }
    if token in overrides:
        return overrides[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def actor_action_parts(value: str) -> tuple[str, str]:
    text = re.sub(r"^(?:a|an|the)\s+", "", sentence_fragment(value), flags=re.IGNORECASE)
    words = text.split()
    for index in range(1, min(len(words), 6)):
        candidate = " ".join(words[index:]).strip(" .")
        if not looks_like_finite_action(candidate):
            continue
        verb = words[index].strip(".,;:")
        if imperative_action_with_copula_words(words, index):
            return "", ""
        base = base_title_verb(verb)
        if base != verb.casefold():
            actor = " ".join(words[:index]).strip(" .")
            tail = " ".join(words[index + 1 :]).strip(" .")
            action = " ".join(part for part in (base, tail) if part)
            return actor, action
    return "", ""


def strip_actor_prefix(value: str, actor: str) -> str:
    text = sentence_fragment(value)
    prefix = sentence_fragment(actor)
    for candidate in (prefix, f"a {prefix}", f"an {prefix}", f"the {prefix}"):
        cleaned = candidate.strip()
        if cleaned and text.casefold().startswith(cleaned.casefold()):
            text = text[len(cleaned) :].strip(" .")
            break
    return text


def base_leading_action(value: str) -> str:
    text = sentence_fragment(value)
    words = text.split()
    if not words:
        return text
    base = base_title_verb(words[0].strip(".,;:"))
    if base != words[0].casefold():
        words[0] = base
    return " ".join(words)


def proof_title_object(value: str) -> str:
    text = _short_summary(value, limit=120).strip(" .")
    text = re.sub(r"^release\s+\S+\s+succeeds\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^proof\s+(?:boundary|must\s+show|means)\s*:?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwithout\b.+$", "", text, flags=re.IGNORECASE).strip(" .,;:")
    if len(text.split()) > 9:
        text = " ".join(text.split()[:9])
    return sentence_fragment(drop_adjacent_duplicate_words(text))


def workstream_subject(value: str) -> str:
    text = collapse_repeated_phrase_units(_compact_text(value))
    text = re.sub(r"\s+(Service|Surface|Component|Boundary)$", "", text, flags=re.IGNORECASE).strip()
    return drop_adjacent_duplicate_words(text) or value


def component_label_at(components: list[dict[str, Any]], index: int, *, fallback: str) -> str:
    if not components:
        return fallback
    bounded_index = min(max(index, 0), len(components) - 1)
    value = collapse_repeated_phrase_units(str(components[bounded_index].get("label", "")).strip())
    return value or fallback


def first_clause(value: str) -> str:
    text = _short_summary(value, limit=220)
    parts = [part.strip(" .") for part in re.split(r"[.;]", text, maxsplit=1) if part.strip(" .")]
    return parts[0] if parts else text


def first_action_clause(value: str) -> str:
    text = first_clause(value)
    if not text:
        return text
    action_pattern = (
        r"the\s+product\s+(?:accepts?|assigns?|calculates?|completes?|estimates?|fetches?|highlights?|lets?|notifies?|preserves?|ranks?|records?|routes?|shows?|stores?|verifies?)|"
        r"(?:accepts?|assigns?|calculates?|chooses?|completes?|estimates?|fetches?|highlights?|lets?|logs?|notifies?|preserves?|ranks?|receives?|records?|reviews?|selects?|shows?|stores?|submits?|verifies?)\b"
    )
    return re.split(rf",\s+(?=(?:and\s+)?(?:{action_pattern}))", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")


def first_path_outcome(value: str, *, proof_boundary: str = "") -> str:
    return sentence_fragment(
        first_path_outcome_phrase(
            value,
            proof_boundary=proof_claim_summary(proof_boundary, limit=240),
            fallback="the promised user-visible result",
            limit=240,
        )
    )


def program_problem(
    *,
    label: str,
    actors: str,
    story: str,
    capability: str,
    outcome: str,
    fallback: str,
) -> str:
    for candidate in (fallback, story):
        text = _short_summary(candidate, limit=360)
        if text and not looks_mechanical_summary(text) and has_problem_tension(text):
            return text
    actor_text = problem_actor_subject(actors, fallback=f"{label} user")
    capability_text = capability or "complete the first product path"
    outcome_text = outcome or "the promised user-visible result"
    return (
        f"{actor_text} needs a clear way to {capability_text} and understand what to do next. "
        f"If {label} only captures activity, the product leaves that user with data but no trustworthy way to use {outcome_text}."
    )


def problem_actor_subject(actors: str, *, fallback: str) -> str:
    text = _compact_text(actors)
    if not text:
        text = _compact_text(fallback)
    text = re.split(r"\s*,\s*|\s*;\s*|\s+\band\b\s+", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
    text = re.sub(r"\s*\((?:primary|secondary|optional|supporting|deferred)\)\s*$", "", text, flags=re.IGNORECASE).strip(" .")
    if not text:
        text = "first user"
    lowered = text.casefold()
    article = re.match(r"^(?P<article>a|an|the|one|this|that|each)\s+(?P<body>.+)$", text, flags=re.IGNORECASE)
    if article:
        return f"{article.group('article').capitalize()} {_lower_actor_label_start(article.group('body'))}".strip()
    if re.match(r"^(?:people|users|customers|operators|reviewers)\b", lowered):
        return text[:1].upper() + text[1:]
    return f"The {_lower_actor_label_start(text)}"


def outcome_repeats_action(*, action: str, outcome: str, outcome_action: str) -> bool:
    return bool(
        (outcome and result_terms_covered(outcome, action))
        or (outcome_action and result_terms_covered(outcome_action, action))
        or (outcome and shares_product_terms(action, outcome))
        or (outcome_action and shares_product_terms(action, outcome_action))
    )


def inline_actor_subject(value: str, *, fallback: str = "the user") -> str:
    """Return an actor label in the form used inside a sentence."""

    text = _compact_text(value).strip(" .")
    if not text:
        text = _compact_text(fallback).strip(" .")
    if not text:
        return "the user"
    article = re.match(r"^(?P<article>a|an|the|one|this|that|each)\s+(?P<body>.+)$", text, flags=re.IGNORECASE)
    if article:
        return f"{article.group('article').casefold()} {_lower_actor_label_start(article.group('body'))}".strip()
    if re.match(r"^(?:people|users|customers|operators|reviewers)\b", text, flags=re.IGNORECASE):
        return text[:1].casefold() + text[1:]
    return f"the {_lower_actor_label_start(text)}"


def inline_actor_event_fragment(*, label: str, action: str) -> str:
    actor = inline_actor_subject(label, fallback="")
    action_text = sentence_fragment(action).strip(" .")
    if not actor or not action_text:
        return ""
    if re.match(r"^(?:can|cannot|could|may|might|must|should|will|would)\b", action_text, flags=re.IGNORECASE):
        return sentence_fragment(f"{actor} {action_text}")
    return sentence_fragment(f"{actor} can {action_text}")


def _lower_actor_label_start(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    words = text.split(maxsplit=1)
    first = words[0]
    rest = f" {words[1]}" if len(words) > 1 else ""
    if _all_plain_title_label_words(text):
        return text.casefold()
    if _protected_actor_label_token(first):
        return _lower_sentence_label_words(f"{first}{rest}")
    lowered = f"{first[:1].casefold()}{first[1:]}{rest}"
    return _lower_role_words(lowered)


def _all_plain_title_label_words(value: str) -> bool:
    words = [word.strip(".,;:()[]{}") for word in str(value or "").split() if word.strip(".,;:()[]{}")]
    if not words:
        return False
    if any(_protected_actor_label_token(word) for word in words):
        return False
    return any(word[:1].isupper() for word in words) and all(
        word[:1].isupper() or word.casefold() in {"and", "of", "on", "or", "for", "in", "to", "with"}
        for word in words
    )


def _protected_actor_label_token(value: str) -> bool:
    token = str(value or "").strip(".,;:()[]{}")
    if not token:
        return False
    return any(char.isdigit() for char in token) or (token.isupper() and len(token) > 1)


def _lower_sentence_label_words(value: str) -> str:
    words = str(value or "").split()
    lowered: list[str] = []
    for word in words:
        stripped = word.strip(".,;:()[]{}")
        if _protected_actor_label_token(stripped):
            lowered.append(word)
        else:
            lowered.append(word.casefold())
    return " ".join(lowered)


def _lower_role_words(value: str) -> str:
    return re.sub(
        r"\b(?:Actor|Admin|Administrator|Applicant|Coordinator|Customer|Lead|Manager|Operator|Owner|Participant|Reviewer|User)\b",
        lambda match: match.group(0).casefold(),
        value,
    )


def role_label_fragment(value: str) -> str:
    """Return a title label with mixed internal role words normalized."""

    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    if _all_plain_title_label_words(text):
        return text
    return _lower_role_words(text)


def capability_action_clause(value: str) -> str:
    text = sentence_fragment(value)
    if not text:
        return "complete the accepted path"
    _actor, actor_action = actor_action_parts(text)
    if actor_action:
        return normalize_action_clause(actor_action)
    converted = base_action_clause(text)
    return normalize_action_clause(converted or text)


def proof_action_subject(value: str) -> str:
    text = normalize_action_clause(value)
    _actor, actor_action = actor_action_parts(text)
    if actor_action:
        text = actor_action
    words = text.split()
    if not words:
        return ""
    rows: list[str] = []
    convert_next = True
    converted = False
    for word in words:
        token = word.strip(".,:;").casefold()
        gerund = gerund_action_verb(token) if convert_next and looks_like_base_action_token(token) else ""
        if gerund:
            rows.append(_replace_word_token(word, gerund))
            converted = True
            convert_next = False
            continue
        rows.append(word)
        convert_next = token in {"and", "or", "then"} or (converted and word.endswith((",", ";")))
    return re.sub(r"\s+", " ", " ".join(rows)).strip(" .") if converted else text


def _replace_word_token(value: str, replacement: str) -> str:
    suffix = ""
    while value and value[-1] in ".,:;":
        suffix = value[-1] + suffix
        value = value[:-1]
    return f"{replacement}{suffix}"


def normalize_action_clause(value: str) -> str:
    text = base_action_clause(sentence_fragment(value))
    text = _strip_leading_action_modal(text)
    text = re.sub(
        r"^(?:(?:a|an|the)\s+)?(?:user|owner|person|actor|customer|applicant|participant|operator)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    for inflected, base in {
        "adds": "add",
        "assigns": "assign",
        "asks": "ask",
        "logs": "log",
        "enters": "enter",
        "selects": "select",
        "submits": "submit",
        "saves": "save",
        "chooses": "choose",
        "clicks": "click",
        "accepts": "accept",
        "dismisses": "dismiss",
        "records": "record",
        "captures": "capture",
        "confirms": "confirm",
        "proves": "prove",
        "publishes": "publish",
        "reviews": "review",
        "updates": "update",
    }.items():
        text = re.sub(rf"^{re.escape(inflected)}\b", base, text, flags=re.IGNORECASE)
        text = re.sub(rf"\b(and|then)\s+{re.escape(inflected)}\b", rf"\1 {base}", text, flags=re.IGNORECASE)
        text = re.sub(rf"\b(and|then)\s+manually\s+{re.escape(inflected)}\b", rf"\1 manually {base}", text, flags=re.IGNORECASE)
    gerund_text = base_gerund_clause(text)
    if gerund_text:
        text = gerund_text
    return re.sub(r"\s+", " ", text).strip(" .") or "complete the accepted path"


def _strip_leading_action_modal(value: str) -> str:
    words = str(value or "").strip(" .").split()
    while words:
        token = words[0].casefold().strip(".,:;")
        if token in {"can", "could", "must", "should", "will", "would"}:
            words = words[1:]
            continue
        if len(words) >= 2 and token in {"need", "needs"} and words[1].casefold().strip(".,:;") == "to":
            words = words[2:]
            continue
        break
    return " ".join(words).strip(" .")


__all__ = [
    "actor_action_parts",
    "actor_from_action",
    "base_leading_action",
    "base_title_verb",
    "capability_action_clause",
    "component_label_at",
    "first_action_clause",
    "first_clause",
    "first_path_outcome",
    "generic_title_outcome",
    "has_problem_tension",
    "imperative_action_phrase",
    "inline_actor_event_fragment",
    "inline_actor_subject",
    "join_actor_labels",
    "lead_actor_label",
    "looks_mechanical_summary",
    "normalize_action_clause",
    "problem_actor_subject",
    "program_problem",
    "proof_action_subject",
    "proof_claim_summary",
    "proof_focus_phrase",
    "proof_title_object",
    "rationale_lines",
    "result_content_words",
    "result_terms_covered",
    "role_label_fragment",
    "semantic_words",
    "sentence_fragment",
    "shares_product_terms",
    "state_boundary_focus",
    "state_changer_label",
    "strip_actor_prefix",
    "supporting_actor_label",
    "workstream_subject",
]
