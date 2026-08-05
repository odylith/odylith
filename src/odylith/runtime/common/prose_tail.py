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
    {"include", "includes", "keep", "keeps", "remain", "remains", "with"}
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
    if len(lowered) < 3:
        return False
    if lowered[-1] in {"include", "includes", "keeps", "with"}:
        return True
    if len(lowered) < 5:
        return False
    if lowered[-1] in {"remain", "remains"} and any(token in {"what", "which"} for token in lowered[-8:-1]):
        return False
    return lowered[-1] in INCOMPLETE_PUBLIC_TAIL_WORDS


def strip_incomplete_public_tail(value: str, *, rstrip_chars: str = " ,;:.") -> str:
    """Remove an incomplete public-copy tail at a known clipping boundary."""

    text = str(value or "").rstrip(rstrip_chars)
    while _clipped_tail_needs_object(text.split()):
        text = " ".join(text.split()[:-1]).rstrip(rstrip_chars)
    return text


def _clipped_tail_needs_object(tokens: Sequence[str]) -> bool:
    lowered = tuple(str(token or "").casefold().strip(".,;:'") for token in tokens)
    if not lowered:
        return False
    if lowered[-1] in {"remain", "remains"} and any(token in {"what", "which"} for token in lowered[-8:-1]):
        return False
    return lowered[-1] in INCOMPLETE_PUBLIC_TAIL_WORDS


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
