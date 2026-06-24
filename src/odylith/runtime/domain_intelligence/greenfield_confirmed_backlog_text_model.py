"""Text model helpers for confirmed greenfield Radar workstreams."""

from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_item
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_occurrences
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import _has_mechanical_need_to_turn
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_text import imperative_action_with_copula_words

_BACKLOG_TERM_STOPWORDS = frozenset(
    {
        "and",
        "can",
        "for",
        "from",
        "into",
        "must",
        "that",
        "then",
        "the",
        "this",
        "when",
        "with",
        "without",
    }
)
_PRODUCT_SHARE_STOPWORDS = _BACKLOG_TERM_STOPWORDS | frozenset(
    {
        "accepted",
        "action",
        "complete",
        "first",
        "path",
        "product",
        "release",
        "result",
        "state",
        "their",
        "user",
    }
)
_RESULT_ACTION_WORDS = frozenset(
    {
        "act",
        "acts",
        "acting",
        "get",
        "gets",
        "getting",
        "reach",
        "reaches",
        "reaching",
        "read",
        "reads",
        "reading",
        "receive",
        "receives",
        "receiving",
        "see",
        "sees",
        "seeing",
        "use",
        "uses",
        "using",
        "view",
        "views",
        "viewing",
    }
)
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


def proof_claim_summary(value: str, *, limit: int = 260) -> str:
    raw_text = _compact_text(value).strip(" .")
    text = _strip_proof_claim_intro(raw_text)
    text = _drop_secondary_ranking_claims(text)
    text = _short_summary(text, limit=limit).strip(" .")
    text = _trim_incomplete_terminal_phrase(text)
    return text or _trim_incomplete_terminal_phrase(_short_summary(raw_text, limit=limit).strip(" ."))


def _strip_proof_claim_intro(value: str) -> str:
    text = _compact_text(value).strip(" .")
    patterns = (
        r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+",
        r"^(?:the\s+)?product\s+is\s+proven\s+when\s+",
        r"^(?:release\s+[0-9.]+\s+)?(?:is\s+)?proven\s+when\s+",
        r"^(?:the\s+)?proof\s+boundary\s+(?:is|means)\s*:?\s*",
        r"^(?:the\s+)?first\s+thing\s+(?:the\s+)?product\s+must\s+prove\s+(?:is\s+)?(?:that\s+)?",
        r"^(?:the\s+)?first\s+complete\s+path\s+(?:the\s+)?product\s+must\s+prove\s+(?:is\s+)?(?:that\s+)?",
        r"^(?:the\s+)?first\s+release\s+must\s+prove\s+(?:that\s+)?",
    )
    previous = ""
    while text and text != previous:
        previous = text
        for pattern in patterns:
            text = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip(" .")
    return text


def _drop_secondary_ranking_claims(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    return re.split(
        r"\s+(?:A\s+close\s+second|Close\s+second|Second(?:arily)?|Next)\s+(?:is|would\s+be|should\s+be)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .")


_INCOMPLETE_TERMINAL_WORDS = frozenset(
    {
        "a",
        "against",
        "an",
        "and",
        "around",
        "as",
        "at",
        "because",
        "between",
        "for",
        "from",
        "into",
        "of",
        "or",
        "plus",
        "the",
        "this",
        "through",
        "to",
        "toward",
        "towards",
        "until",
        "via",
        "when",
        "while",
        "with",
        "without",
    }
)
_INCOMPLETE_TERMINAL_MODIFIERS = frozenset(
    {
        "actionable",
        "accepted",
        "clear",
        "complete",
        "concrete",
        "daily",
        "final",
        "first",
        "reviewable",
        "safe",
        "safety",
        "specific",
        "trusted",
        "visible",
    }
)
_OPEN_CONNECTOR_INTERRUPTER_RE = re.compile(
    r"\b(?:and|or),\s+(?:after|although|as|before|because|if|once|until|when|where|while)\b[^,.;]*$",
    re.IGNORECASE,
)


def _trim_incomplete_terminal_phrase(value: str) -> str:
    text = _compact_text(value).strip(" .,;:")
    words = text.split()
    while words:
        tail = words[-1].casefold().strip(".,;:'")
        if tail not in _INCOMPLETE_TERMINAL_WORDS and tail not in _INCOMPLETE_TERMINAL_MODIFIERS:
            break
        words.pop()
    text = " ".join(words).strip(" .,;:")
    while True:
        trimmed = _OPEN_CONNECTOR_INTERRUPTER_RE.sub("", text).strip(" .,;:")
        if trimmed == text:
            return text
        text = trimmed


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


def semantic_words(value: str) -> set[str]:
    return set(ordered_terms(value, minimum=3, stopwords=_BACKLOG_TERM_STOPWORDS))


def result_content_words(value: str) -> set[str]:
    """Return result terms without generic transition or perception verbs."""

    return semantic_words(value) - _RESULT_ACTION_WORDS


def result_terms_covered(needle: str, haystack: str) -> bool:
    needle_terms = result_content_words(needle)
    if not needle_terms:
        return False
    return needle_terms <= result_content_words(haystack)


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
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip(" .")
    words = text.split()
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


def _actor_title_word_limit(words: Sequence[str]) -> int:
    if len(words) <= 4:
        return len(words)
    lowered = [word.casefold().strip(".,;:") for word in words]
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
    return sentence_fragment(_drop_adjacent_duplicate_words(text))


def workstream_subject(value: str) -> str:
    text = _compact_text(value)
    text = re.sub(r"\s+(Service|Surface|Component|Boundary)$", "", text, flags=re.IGNORECASE).strip()
    return _drop_adjacent_duplicate_words(text) or value


def component_label_at(components: list[dict[str, Any]], index: int, *, fallback: str) -> str:
    if not components:
        return fallback
    bounded_index = min(max(index, 0), len(components) - 1)
    value = str(components[bounded_index].get("label", "")).strip()
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
        if _protected_role_label_after_first_token(text):
            return text
        return _lower_role_words(f"{first}{rest}")
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


def _protected_role_label_after_first_token(value: str) -> bool:
    words = [word.strip(".,;:()[]{}") for word in str(value or "").split() if word.strip(".,;:()[]{}")]
    if len(words) < 2 or not _protected_actor_label_token(words[0]):
        return False
    role_words = {
        "actor",
        "admin",
        "administrator",
        "applicant",
        "coordinator",
        "customer",
        "lead",
        "manager",
        "operator",
        "owner",
        "participant",
        "reviewer",
        "user",
    }
    return all(word.casefold() in role_words for word in words[1:])


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


def sentence_fragment(value: str) -> str:
    text = _drop_adjacent_duplicate_words(_short_summary(value, limit=260).strip(" ."))
    if not text:
        return ""
    if re.match(r"^[A-Z]{2,}\b", text):
        return text
    return text[:1].casefold() + text[1:]


def _drop_adjacent_duplicate_words(value: str) -> str:
    words = str(value or "").split()
    cleaned: list[str] = []
    previous = ""
    for word in words:
        normalized = re.sub(r"[^a-z0-9]+", "", word.casefold())
        if normalized and normalized == previous and len(normalized) >= 4:
            continue
        cleaned.append(word)
        previous = normalized
    return " ".join(cleaned)


def proof_focus_phrase(value: str, *, fallback: str) -> str:
    candidates: list[tuple[int, int, str]] = []
    for index, clause in enumerate(re.split(r"\s*,\s*|\s+\band\b\s+", sentence_fragment(value))):
        text = sentence_fragment(clause).strip(" .")
        if not text or word_count(text) > 6:
            continue
        if not re.search(r"\b(?:approval|decision|judgment|outcome|reason|rejection|signoff|status)\b", text, re.I):
            continue
        score = 3
        if re.search(
            r"\b(?:actor|admin|administrator|coordinator|customer|human|manager|operator|owner|reviewer|user)\b",
            text,
            re.I,
        ):
            score += 4
        if re.search(r"\b(?:final|release|review|trusted)\b", text, re.I):
            score += 1
        candidates.append((score, -index, text))
    if not candidates:
        return fallback
    candidates.sort(reverse=True)
    return candidates[0][2]


def rationale_lines(
    *,
    label: str,
    title: str,
    opportunity: str,
    first_slice: str,
    proof_boundary: str,
    deferred_scope: Sequence[str] = (),
) -> list[str]:
    why_now = _short_summary(opportunity, limit=180).strip(" .")
    expected_outcome = _short_summary(first_slice, limit=200).strip(" .")
    if looks_mechanical_summary(why_now):
        why_now = f"{title} proves a bounded part of the accepted {label} first path before adjacent scope expands"
    if looks_mechanical_summary(expected_outcome):
        expected_outcome = f"{title} produces reviewable state, blocker behavior, recovery evidence, and handoff proof"
    if not why_now:
        why_now = "Clarify the accepted product boundary before implementation starts"
    if not expected_outcome:
        expected_outcome = "Produce the first reviewable release outcome"
    scope_focus = rationale_scope_focus(first_slice, fallback=title)
    if _too_similar(why_now, expected_outcome):
        why_now = f"{title} gives release planning one complete, reviewable outcome before optional scope expands"
    if _too_similar(scope_focus, expected_outcome):
        scope_focus = _short_summary(title, limit=90).strip(" .") or _short_summary(label, limit=90).strip(" .") or "the accepted slice"
    deferred_focus = rationale_deferred_focus(
        value=proof_boundary,
        label=label,
        fallback=scope_focus,
        deferred_scope=deferred_scope,
    )
    proof_focus = rationale_proof_focus(proof_boundary, fallback=expected_outcome)
    release_basis = rationale_release_basis(title=title, label=label, first_slice=first_slice, proof_boundary=proof_boundary)
    deferred_rationale = _deferred_rationale_sentence(deferred_focus)
    lines = [
        f"- why now: {why_now}.",
        f"- expected outcome: {expected_outcome}.",
        f"- tradeoff: Keep this slice centered on {scope_focus} so implementation does not absorb unrelated release claims.",
        f"- deferred for now: {deferred_rationale}.",
        f"- ranking basis: {release_basis}.",
    ]
    return [collapse_adjacent_duplicate_terms(line) for line in lines]


def rationale_scope_focus(value: str, *, fallback: str) -> str:
    text = sentence_fragment(value)
    text = re.sub(r"^(?:deliver|implement|produce|start(?:\s+with)?|build)\s+(?:one\s+)?", "", text, flags=re.IGNORECASE)
    text = re.split(r"\s+without\s+|\s+and\s+explain\b|\s+and\s+see\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = _short_summary(text, limit=120).strip(" .")
    text = re.sub(r"^(?:with|where|when)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    return text or sentence_fragment(fallback) or "the accepted slice"


def rationale_proof_focus(value: str, *, fallback: str) -> str:
    text = proof_claim_summary(value, limit=160).strip(" .")
    text = re.split(r"\s+without\s+|\s+and\s+missing\b|\s+and\s+deferred\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    if word_count(text) > 14:
        text = _bounded_complete_proof_focus(text, max_words=18)
    return sentence_fragment(text or fallback) or "the proven first path"


def rationale_deferred_focus(*, value: str, label: str, fallback: str, deferred_scope: Sequence[str] = ()) -> str:
    """Return the explicit deferred scope without repeating the first-slice path."""

    for row in deferred_scope:
        selected = _deferred_focus_sentence(row) or boundary_clause_item(str(row), limit=120)
        if selected and not _too_similar(selected, fallback):
            return selected[:1].upper() + selected[1:]
    text = _compact_text(value).strip(" .")
    deferred: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        cleaned = _deferred_focus_sentence(sentence)
        if cleaned:
            deferred.append(cleaned)
    selected = _short_summary(deferred[0], limit=120).strip(" .") if deferred else ""
    if selected and not _too_similar(selected, fallback):
        return selected[:1].upper() + selected[1:]
    label_text = _short_summary(label, limit=90).strip(" .")
    return f"Adjacent {label_text or 'product'} workflows"


def _deferred_rationale_sentence(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return "Adjacent scope waits for a separate owner, acceptance gate, and proof path"
    if text.casefold().endswith("scope remains deferred") or text.casefold().startswith("scope question remains open"):
        return f"{text}; separate owner, acceptance gate, and proof path required"
    if re.match(r"^(?:avoid|do\s+not|don't|never)\b", text, flags=re.IGNORECASE):
        return f"{text}; separate owner, acceptance gate, and proof path required"
    deferred_focus = _deferred_focus_sentence(text)
    if deferred_focus:
        text = deferred_focus[:1].upper() + deferred_focus[1:]
    verb = "wait" if _deferred_focus_is_plural(text) else "waits"
    return f"{text} {verb} for a separate owner, acceptance gate, and proof path"


def _deferred_focus_is_plural(value: str) -> bool:
    text = _compact_text(value).strip(" .")
    lowered = text.casefold()
    if re.search(r"\b(?:and|or)\b", lowered) or "," in text:
        return True
    return bool(re.search(r"\b(?:integrations|roles|workflows|features|systems|services|exports|imports)\b", lowered))


def _deferred_focus_sentence(value: str) -> str:
    cleaned = _compact_text(value).strip(" .")
    if not cleaned:
        return ""
    lowered = cleaned.casefold()
    if not re.search(
        r"\b(?:out\s+of\s+scope|outside|deferred|future|later|not\s+included|not\s+required|"
        r"not\s+needed|not\s+necessary|must\s+not\s+claim|does\s+not\s+claim)\b",
        lowered,
    ):
        return ""
    scope_question = re.match(
        r"^(?:whether\s+)?(?:is|are|should|will|would|can|could|does|do)?\s*(?P<subject>.+?)\s+"
        r"(?:in\s+scope|included|part\s+of\s+(?:the\s+)?scope)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if scope_question:
        subject = _short_summary(scope_question.group("subject"), limit=90).strip(" .")
        if subject:
            return f"{subject[:1].upper()}{subject[1:]} scope remains deferred"
    not_required = re.match(
        r"^(?P<subject>.+?)\s+(?:is|are)\s+[^.]{0,120}?\bnot\s+(?:required|needed|necessary)\b",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not_required:
        subject = _short_summary(not_required.group("subject"), limit=90).strip(" .")
        if subject:
            return f"{subject[:1].upper()}{subject[1:]} scope remains deferred"
    cleaned = re.sub(
        r"\s+(?:are|is|stay|stays|remain|remains)\s+"
        r"(?:(?:explicitly|intentionally|currently)\s+)?"
        r"(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?(?:proof|release|scope))\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip(" .")
    cleaned = re.sub(r"^(?:outside\s+(?:the\s+)?(?:first\s+)?(?:proof|release|scope)\s*:?\s*)", "", cleaned, flags=re.IGNORECASE)
    return _short_summary(cleaned, limit=120).strip(" .")


def _bounded_complete_proof_focus(value: str, *, max_words: int) -> str:
    text = _compact_text(value).strip(" .")
    comma_segments = [segment.strip(" .") for segment in re.split(r"\s*,\s*", text) if segment.strip(" .")]
    if len(comma_segments) > 1:
        selected: list[str] = []
        for segment in comma_segments:
            selected.append(segment)
            candidate = _trim_incomplete_terminal_phrase(", ".join(selected))
            joined = ", ".join(selected).strip(" .,;:")
            if candidate and candidate == joined and word_count(candidate) >= 7:
                return candidate
    words = text.split()
    if len(words) <= max_words:
        return _trim_incomplete_terminal_phrase(text)
    return _trim_incomplete_terminal_phrase(" ".join(words[:max_words]))


def rationale_release_basis(*, title: str, label: str, first_slice: str, proof_boundary: str) -> str:
    title_text = _short_summary(title, limit=90).strip(" .") or sentence_fragment(title)
    slice_terms = semantic_words(first_slice)
    proof_terms = semantic_words(proof_boundary)
    shared = sorted((slice_terms & proof_terms) - {"can", "must", "release", "result", "state"})
    if shared:
        proof_focus = rationale_proof_focus(proof_boundary, fallback=first_slice)
        return f"{title_text} ranks before optional expansion because {label} must prove {proof_focus} in the same release story"
    return f"{title_text} ranks before optional expansion because it ties the accepted path to reviewable {label} release evidence"


def _too_similar(left: str, right: str) -> bool:
    left_terms = semantic_words(left)
    right_terms = semantic_words(right)
    if len(left_terms) < 4 or len(right_terms) < 4:
        return False
    overlap = len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms)))
    return overlap >= 0.65


def looks_mechanical_summary(value: str) -> bool:
    text = _compact_text(value)
    if not text:
        return False
    lowered = text.casefold()
    repeated_required = word_occurrences(text, "required")
    return bool(
        repeated_required >= 2
        or re.search(r"\bactor identity,\s+validation context,\s+and upstream handoff\b", lowered)
        or re.search(r"\bblocker signal,\s+review rationale,\s+and downstream handoff\b", lowered)
        or re.search(r"\b(?:accepted\s+first\s+path|accepted\s+proof\s+boundary|first\s+path\s+entry)\b", lowered)
        or re.search(r"\b(?:visible[- ]result\s+event|rendered\s+dashboard|dashboard\s+renders?\s+the\s+visible\s+result)\b", lowered)
        or re.search(r"\b(?:source\s+evidence,\s+visible\s+blockers|systems\s+that\s+own\s+the\s+handoff)\b", lowered)
        or re.search(r"\bis\s+not\s+trustworthy\s+when\b", lowered)
        or _has_mechanical_need_to_turn(text)
        or re.search(r"\bfirst\s+release\s+can\s+collect\s+activity\b", lowered)
        or re.search(r"^on\s+save\b", lowered)
    )


def has_problem_tension(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:without|risk|harm|danger|fails?|failure|cannot|missing|unclear|blocked|drift|stale|unsupported|untrusted|needs?|must|if|when|unless|because|otherwise|prevents?|reduces?|no)\b",
            _compact_text(value).casefold(),
        )
    )


def shares_product_terms(left: str, right: str) -> bool:
    left_terms = set(ordered_terms(left, minimum=4, stopwords=_PRODUCT_SHARE_STOPWORDS))
    right_terms = set(ordered_terms(right, minimum=4, stopwords=_PRODUCT_SHARE_STOPWORDS))
    if not left_terms or not right_terms:
        return False
    return len(left_terms & right_terms) >= min(3, len(right_terms))


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
    "inline_actor_subject",
    "join_actor_labels",
    "lead_actor_label",
    "looks_mechanical_summary",
    "normalize_action_clause",
    "problem_actor_subject",
    "program_problem",
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
    "state_changer_label",
    "strip_actor_prefix",
    "supporting_actor_label",
    "workstream_subject",
]
