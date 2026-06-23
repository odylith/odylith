"""Recover clean first-path source text from operator prompt wrappers."""

from __future__ import annotations

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_REQUEST_COMMAND_WORDS = frozenset(
    {
        "build",
        "create",
        "design",
        "draft",
        "generate",
        "make",
        "propose",
        "scaffold",
        "write",
    }
)
_REQUEST_PRODUCT_WORDS = frozenset(
    {
        "app",
        "application",
        "dashboard",
        "desk",
        "experience",
        "console",
        "controller",
        "engine",
        "hub",
        "platform",
        "portal",
        "product",
        "project",
        "room",
        "service",
        "coach",
        "studio",
        "system",
        "tool",
        "tracker",
        "workspace",
    }
)
_REQUEST_HELPER_WORDS = frozenset({"allow", "allows", "enable", "enables", "help", "helps", "let", "lets"})
_REQUEST_LEAD_CONNECTORS = ("where", "that", "so", "for", "to")


def prompt_first_path_source(value: str) -> str:
    """Return product-path text without a host command or product wrapper."""

    text = _strip_operator_request_wrapper(clean_markdown_text(value).strip(" ."))
    for marker in ("where", "that", "so"):
        candidate = _tail_after_word(text, marker)
        if not candidate:
            continue
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return candidate
    return text


def prompt_project_title_source(value: str) -> str:
    """Return the product noun phrase from a command-shaped operator request."""

    words = _request_words(value)
    if len(words) < 3 or words[0].casefold() not in _REQUEST_COMMAND_WORDS:
        return ""
    start = 1
    if words[start].casefold() in {"a", "an", "the"}:
        start += 1
    start = _skip_proposal_wrapper(words, start)
    if start >= len(words):
        return ""
    lowered = [word.casefold().strip(",:;") for word in words]
    for index in range(start + 1, len(words)):
        if lowered[index] not in _REQUEST_LEAD_CONNECTORS:
            continue
        lead = words[start:index]
        if _looks_like_product_title_phrase(lead):
            return " ".join(lead).strip(" .")
    return ""


def _skip_proposal_wrapper(words: list[str], start: int) -> int:
    index = start
    while index < len(words) and words[index].casefold().strip(",:;") in {"greenfield", "product-first"}:
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") == "proposal":
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") == "for":
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") in {"a", "an", "the"}:
        index += 1
    return index


def _tail_after_word(value: str, marker: str) -> str:
    words = _request_words(value)
    for index, word in enumerate(words[:-1]):
        if word.casefold().strip(".,:;") != marker:
            continue
        return " ".join(words[index + 1 :]).strip(" .")
    return ""


def _strip_operator_request_wrapper(value: str) -> str:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return ""
    for candidate in _operator_request_tail_candidates(text):
        smoothed = _smooth_request_first_path_clause(_strip_leading_helper_word(candidate))
        if word_count(smoothed) >= 4 and _looks_like_recoverable_first_path(smoothed):
            return smoothed
    return _smooth_request_first_path_clause(_strip_leading_helper_word(text))


def _operator_request_tail_candidates(value: str) -> tuple[str, ...]:
    words = _request_words(value)
    if len(words) < 3:
        return ()
    lowered = [word.casefold() for word in words]
    start = 1 if lowered[0] in _REQUEST_COMMAND_WORDS else 0
    if start < len(lowered) and lowered[start] in {"a", "an", "the"}:
        start += 1
    if start >= len(words):
        return ()
    command_led = lowered[0] in _REQUEST_COMMAND_WORDS
    candidates: list[str] = []
    lead_words = lowered[start:]
    for index in range(start, len(words) - 1):
        connector = lowered[index].strip(",:;")
        if connector not in _REQUEST_LEAD_CONNECTORS:
            continue
        lead = lead_words[: max(0, index - start)]
        if not command_led and not (set(lead) & _REQUEST_PRODUCT_WORDS):
            continue
        tail = " ".join(words[index + 1 :]).strip(" ,.;:")
        if tail:
            candidates.append(tail)
    if command_led:
        candidates.append(" ".join(words[start:]))
    return tuple(dict.fromkeys(candidates))


def _strip_leading_helper_word(value: str) -> str:
    words = _request_words(value)
    if len(words) < 2:
        return clean_markdown_text(value).strip(" .")
    if words[0].casefold() not in _REQUEST_HELPER_WORDS:
        return clean_markdown_text(value).strip(" .")
    tail_words = words[1:]
    if tail_words and tail_words[0].casefold() == "to":
        tail_words = tail_words[1:]
    return " ".join(tail_words).strip(" .")


def _smooth_request_first_path_clause(value: str) -> str:
    words = _request_words(value)
    if not words:
        return ""
    while words and words[0].casefold() == "to":
        words = words[1:]
    if len(words) < 3:
        return " ".join(words).strip(" .")
    smoothed: list[str] = []
    for index, word in enumerate(words):
        token = word.casefold().strip(".,:;")
        next_word = words[index + 1] if index + 1 < len(words) else ""
        if token == "to" and smoothed and next_word and looks_like_action_clause(f"{next_word} result"):
            smoothed.append("can")
            continue
        smoothed.append(word)
    return " ".join(smoothed).strip(" .")


def _request_words(value: str) -> list[str]:
    return [
        word.strip("()[]{}\"'")
        for word in clean_markdown_text(value).replace("/", " ").split()
        if word.strip("()[]{}\"'")
    ]


def _looks_like_product_title_phrase(words: list[str]) -> bool:
    if not words or len(words) > 7:
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"} | _REQUEST_PRODUCT_WORDS:
        return False
    return bool(set(lowered) & _REQUEST_PRODUCT_WORDS) or any(word.isupper() and len(word) <= 6 for word in words)


def _looks_like_recoverable_first_path(value: str) -> bool:
    model = first_path_model(value)
    return len(model.steps) >= 2 or bool(model.material_action or model.visible_outcome)


__all__ = ["prompt_first_path_source", "prompt_project_title_source"]
