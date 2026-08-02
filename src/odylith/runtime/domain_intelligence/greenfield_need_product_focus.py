"""Recover product nouns from generic-container request framing."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import is_noncompleting_action_head
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_ACTOR_ROLE_SUFFIXES = (
    "ant",
    "ants",
    "ent",
    "ents",
    "er",
    "ers",
    "ian",
    "ians",
    "ist",
    "ists",
    "or",
    "ors",
    "owner",
    "owners",
)
_TITLE_STOP_WORDS = frozenset(
    {"after", "at", "before", "between", "by", "from", "in", "on", "through", "using", "when", "where", "while", "with"}
)
_REQUEST_CONTAINER_PATTERN = r"(?:app|application|product|service|system|tool)"
_REQUEST_CONTAINER_PHRASE_PATTERN = rf"(?:(?:greenfield|new|simple|small)\s+)?{_REQUEST_CONTAINER_PATTERN}"
_REQUEST_COMMAND_PATTERN = r"(?:build|create|design|draft|develop|make|plan|propose)"


def product_focus_after_command_sentence(value: str) -> str:
    """Return an action object when a command wraps a generic product container."""

    for sentence in _sentence_fragments(value):
        match = re.search(
            rf"\b{_REQUEST_COMMAND_PATTERN}\s+(?:a|an|the)\s+{_REQUEST_CONTAINER_PHRASE_PATTERN}\s+for\s+(?P<focus>.+)$",
            sentence,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        focus = match.group("focus")
        action_object = _action_object_focus(focus)
        if action_object:
            return action_object
        use_for_object = _use_for_object_focus(focus)
        if use_for_object:
            return use_for_object
    return ""


def product_focus_after_need_sentence(value: str) -> str:
    """Return a product noun, never the requester's internal framing."""

    for sentence in _sentence_fragments(value):
        match = re.search(
            rf"\bneeds?\s+(?:a|an|the)\s+{_REQUEST_CONTAINER_PHRASE_PATTERN}\s+for\s+(?P<focus>.+)$",
            sentence,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        focus = re.split(r"\s+\b(?:at|before|after|with|while|when)\b", match.group("focus"), maxsplit=1)[0]
        focus = re.sub(r"^(?:a|an|the)\s+", "", focus, flags=re.IGNORECASE).strip(" .")
        action_object = _action_object_focus(focus)
        if action_object:
            return action_object
        words = _request_words(focus)
        if 2 <= len(words) <= 6 and not _has_actor_action_infinitive(words) and not looks_like_action_clause(focus):
            return focus
    return ""


def need_product_actor_action(value: str) -> tuple[str, str]:
    """Return the actor and action from a request framed as a product need."""

    for sentence in _sentence_fragments(value):
        match = re.search(
            rf"\bneeds?\s+(?:a|an|the)\s+{_REQUEST_CONTAINER_PHRASE_PATTERN}\s+for\s+(?P<focus>.+)$",
            sentence,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        words = _request_words(match.group("focus"))
        for index, word in enumerate(words[:-1]):
            actor_words = words[:index]
            if _word_key(word) != "to" or not _looks_like_prompt_actor(actor_words):
                continue
            action = " ".join(part.strip(".,:;") for part in words[index + 1 :]).strip(" .")
            if action:
                return " ".join(actor_words).strip(" ."), action
    return "", ""


def is_requester_product_framing(value: str) -> bool:
    """Return whether text describes a request rather than a product noun."""

    return bool(
        re.search(
            rf"\b(?:needs?|requires?|wants?)\s+(?:a|an|the)\s+{_REQUEST_CONTAINER_PHRASE_PATTERN}\b",
            clean_markdown_text(value),
            flags=re.IGNORECASE,
        )
    )


def _action_object_focus(value: str) -> str:
    words = _request_words(value)
    for index, word in enumerate(words[:-2]):
        if _word_key(word) != "to" or not _looks_like_prompt_actor(words[:index]):
            continue
        action = _word_key(words[index + 1])
        if is_noncompleting_action_head(action) or not MATERIAL_ACTION_RE.fullmatch(action):
            continue
        candidate: list[str] = []
        for raw in words[index + 2 :]:
            if _word_key(raw) in _TITLE_STOP_WORDS:
                break
            candidate.append(raw.strip(".,:;"))
            if raw.rstrip().endswith((",", ";")):
                break
        while candidate and _word_key(candidate[0]) in {"a", "an", "the", "one"}:
            candidate.pop(0)
        title = " ".join(candidate).strip(" .")
        if 1 <= len(candidate) <= 6:
            # The preceding actor + material-action grammar establishes this
            # bounded span as the action object. A lexical verb heuristic is
            # weaker evidence and misreads nouns such as "release notes".
            return title
    return ""


def _use_for_object_focus(value: str) -> str:
    """Return a title object from a generic access request, never a first path."""

    words = _request_words(value)
    for index, word in enumerate(words[:-3]):
        if _word_key(word) != "to" or not _looks_like_prompt_actor(words[:index]):
            continue
        if _word_key(words[index + 1]) != "use" or _word_key(words[index + 2]) != "for":
            continue
        candidate: list[str] = []
        for raw in words[index + 3 :]:
            if _word_key(raw) in _TITLE_STOP_WORDS:
                break
            candidate.append(raw.strip(".,:;"))
        while candidate and _word_key(candidate[0]) in {"a", "an", "the", "one"}:
            candidate.pop(0)
        title = " ".join(candidate).strip(" .")
        if 1 <= len(candidate) <= 6:
            # `use for` establishes a noun-object slot. Reclassifying the
            # bounded object with an open-world verb heuristic turns valid
            # product nouns such as "release notes" into imperative actions.
            return title
    return ""


def _has_actor_action_infinitive(words: list[str]) -> bool:
    return any(
        index and index + 1 < len(words) and _word_key(word) == "to" and _looks_like_prompt_actor(words[:index])
        for index, word in enumerate(words)
    )


def _looks_like_prompt_actor(words: list[str]) -> bool:
    if not 1 <= len(words) <= 5:
        return False
    last = _word_key(words[-1])
    singular = last[:-1] if last.endswith("s") else last
    return word_has_actor_role_signal(last) or word_has_actor_role_signal(singular) or any(
        last.endswith(suffix) or singular.endswith(suffix) for suffix in _ACTOR_ROLE_SUFFIXES
    )


def _sentence_fragments(value: str) -> tuple[str, ...]:
    return tuple(
        fragment.strip(" .")
        for fragment in re.split(r"(?<=[.!?])\s+", clean_markdown_text(value).strip())
        if fragment.strip(" .")
    )


def _request_words(value: str) -> list[str]:
    return [
        word.strip("()[]{}\"'")
        for word in clean_markdown_text(value).replace("/", " ").split()
        if word.strip("()[]{}\"'")
    ]


def _word_key(value: str) -> str:
    return str(value or "").casefold().strip(".,:;")


__all__ = [
    "is_requester_product_framing",
    "need_product_actor_action",
    "product_focus_after_command_sentence",
    "product_focus_after_need_sentence",
]
