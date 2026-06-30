"""Term selection helpers for Atlas diagram-box explanations."""

from __future__ import annotations

import re


def tracked_object_phrase(corpus: str) -> str:
    """Return the domain object phrase Atlas box copy should discuss."""
    lowered = str(corpus or "").casefold()
    tokens = [_singular_token(match.group(0)) for match in re.finditer(r"\b[a-z][a-z-]{2,}\b", lowered)]
    blocked = {
        "accept",
        "accepted",
        "across",
        "allowed",
        "around",
        "before",
        "behind",
        "between",
        "block",
        "blocked",
        "change",
        "claim",
        "clear",
        "complete",
        "create",
        "created",
        "decision",
        "diagram",
        "downstream",
        "external",
        "first",
        "flow",
        "from",
        "governed",
        "handoff",
        "inside",
        "internal",
        "later",
        "missing",
        "own",
        "owns",
        "outside",
        "path",
        "proof",
        "ready",
        "recorded",
        "release",
        "review",
        "reviewer",
        "scope",
        "source",
        "stay",
        "system",
        "through",
        "until",
        "upstream",
        "user",
        "valid",
        "visible",
        "when",
        "with",
        "without",
    }
    generic_modifiers = {
        "active",
        "available",
        "current",
        "cloud",
        "derived",
        "external",
        "first",
        "known",
        "latest",
        "owned",
        "owns",
        "primary",
        "reviewed",
        "source",
        "stable",
        "the",
        "this",
        "trusted",
        "versioned",
        "view",
    }
    scores: dict[str, int] = {}
    for match in re.finditer(r"\b(?:one|a|an|the)\s+((?:[a-z][a-z-]{2,}\s+){0,2}[a-z][a-z-]{2,})\b", lowered):
        phrase = _phrase_candidate(
            match.group(1),
            blocked=blocked,
            generic_modifiers=generic_modifiers,
        )
        if phrase:
            scores[phrase] = scores.get(phrase, 0) + 8
    for match in re.finditer(r"\bowns?\s+((?:[a-z][a-z-]{2,}\s+){0,2}[a-z][a-z-]{2,})s?\b", lowered):
        phrase = _phrase_candidate(
            match.group(1),
            blocked=blocked,
            generic_modifiers=generic_modifiers,
        )
        if phrase:
            phrase = _expand_single_token_phrase(
                phrase,
                lowered=lowered,
                blocked=blocked,
                generic_modifiers=generic_modifiers,
            )
            scores[phrase] = scores.get(phrase, 0) + 10
    for left, right in zip(tokens, tokens[1:]):
        if left in blocked or right in blocked or left in generic_modifiers or right in generic_modifiers:
            continue
        if left == right or len(left) < 3 or len(right) < 3:
            continue
        phrase = f"{left} {right}"
        scores[phrase] = scores.get(phrase, 0) + 2
    for first, second, third in zip(tokens, tokens[1:], tokens[2:]):
        if any(token in blocked or token in generic_modifiers for token in (first, second, third)):
            continue
        if len({first, second, third}) < 3:
            continue
        phrase = f"{first} {second} {third}"
        scores[phrase] = scores.get(phrase, 0) + 3
    if scores:
        return sorted(scores.items(), key=lambda item: (-item[1], len(item[0]), item[0]))[0][0]
    for token in tokens:
        if token not in blocked and token not in generic_modifiers:
            return token
    return "tracked record"


def _phrase_candidate(
    value: str,
    *,
    blocked: set[str],
    generic_modifiers: set[str],
) -> str:
    words = [_singular_token(match.group(0)) for match in re.finditer(r"\b[a-z][a-z-]{2,}\b", value.casefold())]
    words = [word for word in words if word not in blocked and word not in generic_modifiers]
    if not words:
        return ""
    return " ".join(words[-2:])


def _expand_single_token_phrase(
    phrase: str,
    *,
    lowered: str,
    blocked: set[str],
    generic_modifiers: set[str],
) -> str:
    if " " in phrase:
        return phrase
    for match in re.finditer(rf"\b([a-z][a-z-]{{2,}})\s+{re.escape(phrase)}s?\b", lowered):
        modifier = _singular_token(match.group(1))
        if modifier not in blocked and modifier not in generic_modifiers and modifier != phrase:
            return f"{modifier} {phrase}"
    return phrase


def _singular_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("ses") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    return token
