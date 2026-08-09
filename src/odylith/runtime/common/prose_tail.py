"""Shared detection and repair for clipped generated-prose tails."""

from __future__ import annotations

from collections.abc import Sequence


DEFAULT_DANGLING_TAIL_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "before",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "or",
        "so",
        "the",
        "to",
        "until",
        "with",
    }
)
TERMINAL_MODIFIER_WORDS = frozenset(
    {
        "accepted",
        "actionable",
        "appropriate",
        "bad",
        "blocked",
        "clear",
        "complete",
        "concrete",
        "configured",
        "corrected",
        "daily",
        "expected",
        "failed",
        "final",
        "first",
        "incomplete",
        "invalid",
        "missing",
        "relevant",
        "required",
        "reviewable",
        "runnable",
        "specific",
        "supported",
        "trusted",
        "valid",
        "validated",
        "visible",
    }
)
TERMINAL_MODIFIER_PRECEDERS = frozenset({"a", "an", "one", "the", "this", "that"})
TERMINAL_FINAL_STATE_WORDS = frozenset({"case", "decision", "match", "record", "result", "review", "score", "status"})
INCOMPLETE_PUBLIC_TAIL_WORDS = frozenset(
    {
        "display",
        "displays",
        "include",
        "includes",
        "keep",
        "keeps",
        "produce",
        "produces",
        "provide",
        "provides",
        "publish",
        "publishes",
        "receive",
        "receives",
        "remain",
        "remains",
        "return",
        "returns",
        "see",
        "sees",
        "show",
        "shows",
        "with",
    }
)
_CLAUSE_COORDINATORS = frozenset({"and", "but", "or", "then", "while"})
_CLAUSE_BOUNDARY_PUNCTUATION = (".", "!", "?", ";", ",")
_BASE_FORM_INCOMPLETE_TAIL_WORDS = frozenset(
    {"display", "include", "keep", "produce", "provide", "publish", "receive", "remain", "return", "see", "show"}
)
_BASE_FORM_ACTION_PRECEDERS = frozenset(
    {
        "and",
        "but",
        "can",
        "could",
        "he",
        "it",
        "may",
        "might",
        "must",
        "or",
        "she",
        "should",
        "then",
        "they",
        "to",
        "we",
        "will",
        "would",
        "you",
    }
)
_TERMINAL_NOUN_DETERMINERS = frozenset(
    {"a", "an", "another", "any", "each", "every", "one", "the", "these", "this", "those"}
)


def strip_dangling_word_tail(
    value: str,
    *,
    dangling_words: set[str] | frozenset[str] | tuple[str, ...] | list[str],
    rstrip_chars: str = " ,;:.",
) -> str:
    """Trim incomplete connector tails after word-boundary clipping."""

    words = str(value or "").rstrip(rstrip_chars).split()
    dangling = {str(word or "").casefold().strip(".,;:") for word in dangling_words}
    dangling.discard("")
    while words and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).rstrip(rstrip_chars)


def strip_clipped_terminal_fragment(value: str, *, rstrip_chars: str = " ,;:.") -> str:
    """Trim clipped article/modifier tails while preserving valid state phrases."""

    text = str(value or "").rstrip(rstrip_chars)
    while True:
        words = text.split()
        if len(words) >= 2:
            previous = words[-2].casefold().strip(".,;:'")
            tail = words[-1].casefold().strip(".,;:'")
            if previous in TERMINAL_MODIFIER_PRECEDERS and tail in TERMINAL_MODIFIER_WORDS:
                text = " ".join(words[:-2]).rstrip(rstrip_chars)
                continue
        if words and words[-1].casefold().strip(".,;:'") == "final" and not _allows_terminal_final(words):
            text = " ".join(words[:-1]).rstrip(rstrip_chars)
            continue
        return text


def has_clipped_terminal_modifier(tokens: Sequence[str]) -> bool:
    """Return true when a determiner ends with a modifier but no owned noun."""

    if len(tokens) < 2:
        return False
    tail = str(tokens[-1]).casefold().strip(".,;:'")
    previous = str(tokens[-2]).casefold().strip(".,;:'")
    return tail in TERMINAL_MODIFIER_WORDS and previous in TERMINAL_MODIFIER_PRECEDERS


def has_incomplete_public_tail(tokens: Sequence[str]) -> bool:
    """Return true when bounded copy ends on an action that still needs its object."""

    lowered = tuple(str(token or "").casefold().strip(".,;:'") for token in tokens)
    if len(lowered) < 2:
        return False
    if len(lowered) == 2:
        return lowered[0] not in {"a", "an", "the"} and _tail_needs_object(lowered)
    if len(lowered) >= 5 and lowered[-1] in {"remain", "remains"}:
        return not any(token in {"what", "which"} for token in lowered[-8:-1])
    if len(lowered) >= 5 and lowered[-1] in {"return", "returns"}:
        return _tail_needs_object(lowered) or not _terminal_tail_is_noun_phrase(lowered)
    if lowered[-1] in {"include", "includes", "keeps", "with"}:
        return True
    if len(lowered) < 5:
        return False
    if lowered[-1] in INCOMPLETE_PUBLIC_TAIL_WORDS and any(
        token in {"what", "which"} for token in lowered[-8:-1]
    ):
        return False
    return _tail_needs_object(lowered)


def strip_incomplete_public_tail(
    value: str,
    *,
    preserve_subject: bool = False,
    rstrip_chars: str = " ,;:.",
) -> str:
    """Remove an incomplete public-copy tail at a known clipping boundary."""

    text = str(value or "").rstrip(rstrip_chars)
    while _clipped_tail_needs_object(text.split()):
        tokens = text.split()
        clause_start = _incomplete_clause_start(tokens)
        if clause_start is None:
            clause_start = len(tokens) - 1 if preserve_subject else 0
        text = " ".join(tokens[:clause_start]).rstrip(rstrip_chars)
    return text


def _incomplete_clause_start(tokens: Sequence[str]) -> int | None:
    """Return the start of the trailing clause whose final verb lost its object."""

    for index in range(len(tokens) - 2, -1, -1):
        token = str(tokens[index] or "")
        if token.casefold().strip(".,;:'") in _CLAUSE_COORDINATORS:
            return index
        if token.endswith(_CLAUSE_BOUNDARY_PUNCTUATION):
            return index + 1
    return None


def _clipped_tail_needs_object(tokens: Sequence[str]) -> bool:
    lowered = tuple(str(token or "").casefold().strip(".,;:'") for token in tokens)
    if not lowered:
        return False
    if len(lowered) >= 5 and lowered[-1] in {"remain", "remains"}:
        return not any(token in {"what", "which"} for token in lowered[-8:-1])
    if len(lowered) >= 5 and lowered[-1] in {"return", "returns"}:
        return _tail_needs_object(lowered) or not _terminal_tail_is_noun_phrase(lowered)
    return _tail_needs_object(lowered)


def _tail_needs_object(tokens: Sequence[str]) -> bool:
    tail = tokens[-1] if tokens else ""
    if tail not in INCOMPLETE_PUBLIC_TAIL_WORDS:
        return False
    if tail not in _BASE_FORM_INCOMPLETE_TAIL_WORDS:
        return True
    return len(tokens) >= 2 and tokens[-2] in _BASE_FORM_ACTION_PRECEDERS


def _terminal_tail_is_noun_phrase(tokens: Sequence[str]) -> bool:
    return any(token in _TERMINAL_NOUN_DETERMINERS for token in tokens[-5:-1])


def _allows_terminal_final(words: list[str]) -> bool:
    lowered = [word.casefold().strip(".,;:'") for word in words if word.strip(".,;:'")]
    if len(lowered) < 2 or lowered[-1] != "final":
        return False
    previous = lowered[-2]
    if previous in TERMINAL_FINAL_STATE_WORDS:
        return True
    if previous in {"is", "becomes", "became"} and any(token in TERMINAL_FINAL_STATE_WORDS for token in lowered[:-2]):
        return True
    return any(
        token in {"finalize", "finalizes", "finalized", "finalizing", "mark", "marked", "marks"}
        for token in lowered[:-1]
    )


__all__ = [
    "DEFAULT_DANGLING_TAIL_WORDS",
    "has_clipped_terminal_modifier",
    "has_incomplete_public_tail",
    "strip_clipped_terminal_fragment",
    "strip_dangling_word_tail",
    "strip_incomplete_public_tail",
]
