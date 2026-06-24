"""Recover clean first-path source text from operator prompt wrappers."""

from __future__ import annotations

from dataclasses import dataclass

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
        "board",
        "builder",
        "dashboard",
        "desk",
        "experience",
        "console",
        "controller",
        "engine",
        "executor",
        "hub",
        "manager",
        "monitor",
        "notebook",
        "platform",
        "planner",
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
        "journal",
        "logbook",
        "workbench",
        "workspace",
    }
)
_REQUEST_HELPER_WORDS = frozenset({"allow", "allows", "enable", "enables", "help", "helps", "let", "lets"})
_REQUEST_LEAD_CONNECTORS = ("where", "that", "so", "for", "to")
_DIRECT_TITLE_BOUNDARY_CONNECTORS = frozenset({"where", "that", "so"})
_RELEASE_PROOF_ACTION_WORDS = frozenset(
    {
        "complete",
        "completes",
        "completed",
        "pass",
        "passes",
        "prove",
        "proves",
        "proved",
        "succeed",
        "succeeds",
        "succeeded",
    }
)


@dataclass(frozen=True)
class PromptIntentSource:
    """Operator prompt interpretation before confirmed-intent recovery."""

    title: str
    first_path: str
    command_led: bool


def prompt_first_path_source(value: str) -> str:
    """Return product-path text without a host command or product wrapper."""

    return prompt_intent_source(value).first_path


def prompt_project_title_source(value: str) -> str:
    """Return the product noun phrase from an operator request."""

    return prompt_intent_source(value).title


def prompt_intent_source(value: str) -> PromptIntentSource:
    """Return shared title and first-path sources for thin prompt recovery."""

    text = clean_markdown_text(value).strip(" .")
    words = _request_words(text)
    start, command_led = _request_content_start(words)
    return PromptIntentSource(
        title=_project_title_source_from_words(words, start=start, command_led=command_led),
        first_path=_first_path_source_from_text(text),
        command_led=command_led,
    )


def _first_path_source_from_text(value: str) -> str:
    text = _strip_operator_request_wrapper(clean_markdown_text(value).strip(" ."))
    for marker in ("where", "that"):
        candidate = _tail_after_word(text, marker)
        if not candidate:
            continue
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return _strip_release_proof_tail(candidate)
    if _looks_like_recoverable_first_path(text):
        return _strip_release_proof_tail(text)
    for marker in ("so",):
        candidate = _tail_after_word(text, marker)
        if not candidate:
            continue
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return _strip_release_proof_tail(candidate)
    return _strip_release_proof_tail(text)


def _request_content_start(words: list[str]) -> tuple[int, bool]:
    command_led = len(words) >= 3 and words[0].casefold() in _REQUEST_COMMAND_WORDS
    start = 1 if command_led else 0
    if start < len(words) and words[start].casefold() in {"a", "an", "the"}:
        start += 1
    if command_led:
        start = _skip_proposal_wrapper(words, start)
    return start, command_led


def _project_title_source_from_words(words: list[str], *, start: int, command_led: bool) -> str:
    if start >= len(words):
        return ""
    lowered = [word.casefold().strip(",:;") for word in words]
    for index in range(start + 1, len(words)):
        connector = lowered[index]
        if connector not in _REQUEST_LEAD_CONNECTORS:
            continue
        if not command_led and connector not in _DIRECT_TITLE_BOUNDARY_CONNECTORS:
            tail = " ".join(words[index + 1 :]).strip(" .")
            if not _looks_like_recoverable_first_path(tail):
                continue
        lead = words[start:index]
        if _looks_like_product_title_phrase(lead):
            return " ".join(lead).strip(" .")
    lead = words[start:]
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


def _strip_release_proof_tail(value: str) -> str:
    words = _request_words(value)
    if len(words) < 5:
        return clean_markdown_text(value).strip(" .")
    lowered = [_word_key(word) for word in words]
    for index, word in enumerate(lowered[:-2]):
        if word not in {"before", "until", "when"}:
            continue
        if lowered[index + 1] not in {"release", "version"}:
            continue
        action_index = index + 2
        if action_index < len(words) and _looks_like_release_selector(words[action_index]):
            action_index += 1
        if _release_proof_tail_starts(lowered[action_index:]):
            return " ".join(words[:index]).strip(" ,.;:")
    return clean_markdown_text(value).strip(" .")


def _release_proof_tail_starts(words: list[str]) -> bool:
    if not words:
        return False
    if words[0] in _RELEASE_PROOF_ACTION_WORDS:
        return True
    return len(words) >= 2 and words[0] == "is" and words[1] in {"complete", "completed", "ready"}


def _looks_like_release_selector(value: str) -> bool:
    token = str(value or "").strip(".,:;")
    return bool(token) and all(char.isalnum() or char in "._-" for char in token)


def _word_key(value: str) -> str:
    return str(value or "").casefold().strip(".,:;")


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


__all__ = ["PromptIntentSource", "prompt_first_path_source", "prompt_intent_source", "prompt_project_title_source"]
