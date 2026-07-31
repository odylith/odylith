"""Mermaid label cleanup helpers for greenfield sequence and flow diagrams."""

from __future__ import annotations

import re

from odylith.runtime.common import mermaid_text
from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary


_BASE_ACTION_VERB_PATTERN = action_base_verb_pattern()
_LEADING_LABEL_ARTICLES = frozenset({"a", "an", "the"})


def flow_label(value: str, *, width: int, max_lines: int, limit: int) -> str:
    text = collapse_adjacent_duplicate_terms(normalize_final_state_modifier(trim(value, limit)))
    wrapped = mermaid_text.wrap_mermaid_label(text, width=width, max_lines=max_lines, limit=limit)
    if wrapped_label_has_dangling_tail(wrapped):
        expanded = mermaid_text.wrap_mermaid_label(
            normalize_final_state_modifier(compact_text(value)),
            width=width,
            max_lines=max_lines + 1,
            limit=limit + 80,
        )
        if expanded and not wrapped_label_has_dangling_tail(expanded):
            wrapped = expanded
    return without_ellipsis(strip_wrapped_dangling_tail(wrapped))


def header_body_label(header: str, body: str) -> str:
    """Return a node-body label that does not restate the fixed header tail."""

    header_tail = _label_word_key(_last_label_word(header))
    body_text = compact_text(body).strip(" .")
    if not header_tail or not body_text:
        return body_text
    words = body_text.split()
    if not words:
        return body_text
    first_index = 1 if len(words) > 1 and _label_word_key(words[0]) in _LEADING_LABEL_ARTICLES else 0
    if first_index >= len(words) or _label_word_key(words[first_index]) != header_tail:
        return body_text
    trimmed_words = words[first_index + 1 :]
    if trimmed_words and _label_word_key(trimmed_words[0]) == "as":
        trimmed_words = trimmed_words[1:]
    return " ".join(trimmed_words).strip(" .") or body_text


def wrapped_label_has_dangling_tail(value: str) -> bool:
    parts = [compact_text(part).strip(" ,;:.") for part in carry_wrapped_final_modifier(str(value or "").split("<br/>"))]
    parts = [part for part in parts if part]
    if not parts:
        return False
    final = parts[-1]
    return bool(final and strip_dangling_tail(final) != final)


def normalize_final_state_modifier(value: str) -> str:
    text = compact_text(value)
    return re.sub(
        r"\band\s+(final\s+[A-Za-z0-9 /&'()-]{0,48}?\b(?:state|status|decision|outcome|result|record|submission))\b",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )


def strip_wrapped_dangling_tail(value: str) -> str:
    parts = [compact_text(part).strip(" ,;:.") for part in carry_wrapped_final_modifier(str(value or "").split("<br/>"))]
    cleaned: list[str] = []
    last_index = len(parts) - 1
    for index, part in enumerate(parts):
        text = strip_dangling_tail(part) if index == last_index else strip_clipped_terminal_action(part)
        if text:
            cleaned.append(text)
    return "<br/>".join(cleaned)


def carry_wrapped_final_modifier(parts: list[str]) -> list[str]:
    repaired = list(parts)
    for index in range(len(repaired) - 1):
        current = compact_text(repaired[index]).strip(" ,;:.")
        if not re.search(r"\bfinal$", current, flags=re.IGNORECASE):
            continue
        head = re.sub(r"(?:,\s*)?(?:and\s+)?final$", "", current, flags=re.IGNORECASE).strip(" ,;:.")
        nxt = compact_text(repaired[index + 1]).strip(" ,;:.")
        if not nxt:
            continue
        repaired[index] = head
        repaired[index + 1] = f"final {nxt}"
    return repaired


def without_ellipsis(value: str) -> str:
    return str(value or "").replace("…", "").replace("...", "").rstrip(" ,;:")


def trim(value: str, limit: int) -> str:
    text = compact_text(value)
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return balance_label(strip_dangling_tail(clipped))


def balance_label(value: str) -> str:
    text = compact_text(value).strip(" ,;:.")
    if text.count("(") > text.count(")"):
        text = text.rsplit("(", 1)[0].rstrip(" ,;:.")
    if text.count("[") > text.count("]"):
        text = text.rsplit("[", 1)[0].rstrip(" ,;:.")
    return text


def strip_dangling_tail(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    while True:
        text = strip_clipped_terminal_action(text)
        if re.search(r"\b(?:readiness|result|state|record|status)\s+reviewable$", text, flags=re.IGNORECASE):
            return text
        cleaned = re.sub(
            r"\b(?:a|accepted|actionable|an|and|as|at|because|by|can|capturing|clear|comparing|complete|concrete|daily|final|first|for|from|if|in|into|lets|must|of|on|one|or|receiving|reviewable|safety|should|specific|that|the|through|tied|to|trusted|until|visible|warning|when|while|with|without|alongside)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        cleaned = strip_clipped_terminal_action(cleaned)
        if cleaned == text:
            return cleaned
        text = cleaned


def strip_clipped_terminal_action(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    if "," not in text:
        return text
    head, tail = text.rsplit(",", 1)
    token = tail.strip(" ,;:.").casefold()
    if not token or " " in token:
        return text
    if token.endswith("ing") and len(token) > 5:
        return head.rstrip(" ,;:.")
    if re.fullmatch(_BASE_ACTION_VERB_PATTERN, token, flags=re.IGNORECASE):
        return head.rstrip(" ,;:.")
    return text


def compact_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _last_label_word(value: str) -> str:
    for word in reversed(compact_text(value).split()):
        cleaned = word.strip(".,:;()[]{}\"'")
        if cleaned:
            return cleaned
    return ""


def _label_word_key(value: str) -> str:
    token = str(value or "").casefold().strip(".,:;()[]{}\"'")
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


def node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


__all__ = [
    "compact_text",
    "flow_label",
    "header_body_label",
    "node_id",
    "strip_dangling_tail",
    "trim",
    "without_ellipsis",
]
