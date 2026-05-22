"""Text normalization helpers for confirmed greenfield proposal records."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def compact_text(value: str) -> str:
    text = str(value or "").strip()
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return " ".join(text.split())


def domain_object_label(value: str, *, fallback: str) -> str:
    text = compact_text(value)
    if not text:
        return fallback
    first_clause = re.split(r"[.;\n]", text, maxsplit=1)[0].strip(" :.-")
    dash_head = re.split(r"\s+[—-]\s+", first_clause, maxsplit=1)[0].strip(" :.-")
    patterns = (
        r"\b(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?(?:domain\s+)?object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?proof\s+record\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"^(?:a|an|the)\s+(?P<label>[A-Za-z][A-Za-z0-9 _-]{1,80}?)\s+"
        r"(?:tracks|records|stores|captures|moves|starts|changes)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, dash_head, flags=re.IGNORECASE)
        if match:
            candidate = match.group("label").strip(" :.-")
            return title_label(candidate) or fallback
    if dash_head and not re.search(
        r"\b(is|are|starts?|moves?|changes?|tracks?|records?|captures?|produces?)\b",
        dash_head,
        re.IGNORECASE,
    ):
        return title_label(dash_head) or fallback
    words = text.split()
    if len(words) <= 7:
        return title_label(text) or fallback
    return fallback


def short_summary(value: str, *, limit: int = 280) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:state object|first path|proof boundary|product story)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected: list[str] = []
    total = ""
    for sentence in sentences:
        candidate = " ".join([*selected, sentence]).strip()
        if len(candidate) > limit and selected:
            break
        selected.append(sentence)
        total = candidate
        if len(total) >= limit * 0.55:
            break
    if total:
        return total.strip(" .")
    clipped = text[: max(0, limit - 1)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    clipped = strip_dangling_tail(clipped)
    return clipped


def strip_dangling_tail(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|for|from|if|in|into|of|on|or|the|to|when|while|with|without)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


def problem_text(*, label: str, problem: str, product_story: str, first_path: str) -> str:
    explicit = short_summary(problem, limit=360)
    if explicit:
        return explicit
    story = short_summary(product_story, limit=240)
    path = short_summary(first_path, limit=180)
    if story and path:
        return (
            f"Without a clear first path, users cannot trust whether {label.lower()} solves the accepted problem: "
            f"{story} The proof path is {path}."
        )
    if story:
        return (
            f"Without source-backed proof, users cannot trust whether {label.lower()} solves the accepted problem: {story}."
        )
    return (
        f"Without an explicit problem, first path, and proof boundary, {label.lower()} cannot be trusted as "
        "implementation-ready."
    )


def state_detail_summary(value: str, *, state_label: str, limit: int = 280) -> str:
    summary = short_summary(value, limit=limit)
    if not summary:
        return ""
    label_pattern = re.escape(state_label).replace(r"\ ", r"\s+")
    summary = re.sub(
        rf"^(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?{label_pattern}\.?\s*",
        "",
        summary,
        flags=re.IGNORECASE,
    ).strip(" .")
    if summary.casefold() == state_label.casefold():
        return ""
    return summary


def join_system_labels(items: list[str] | None, *, limit: int = 4) -> str:
    values: list[str] = []
    for item in items or []:
        text = compact_text(item)
        if not text:
            continue
        values.append(domain_object_label(text, fallback=text.split("—", 1)[0].split(":", 1)[0].strip()))
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else "; additional accepted systems remain in the intent"
    return ", ".join(selected) + suffix


def title_label(value: str) -> str:
    words = []
    for index, word in enumerate(compact_text(value).strip(" .").split()):
        lower = word.casefold()
        if index == 0 and lower in {"a", "an", "the"}:
            continue
        if lower in {"and", "or", "of", "the", "to", "for", "in", "on", "with"} and words:
            words.append(lower)
            continue
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}:
            words.append(lower.upper())
            continue
        words.append(word[:1].upper() + word[1:])
    return " ".join(words).strip()


def join_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [str(item).strip().rstrip(".") for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else "; additional accepted items remain in the intent"
    return ", ".join(selected) + suffix


def join_brief_items(items: list[str] | None, *, limit: int = 3, item_limit: int = 120) -> str:
    values = [
        re.sub(r"\s+[-*]\s+", " ", short_summary(str(item), limit=item_limit)).strip(" ;")
        for item in (items or [])
        if str(item).strip()
    ]
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else "; additional accepted items remain in the intent"
    return "; ".join(selected) + suffix


def clean_generated_text(value: Any) -> str:
    return compact_text(str(value or ""))


def sentence_text(value: Any, *, fallback: str = "", limit: int = 320) -> str:
    text = clean_generated_text(value) or fallback
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
        text = strip_dangling_tail(text)
        text = text.rstrip(" ,;:")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def set_sentence_text(row: dict[str, Any], key: str, value: str, *, limit: int = 700) -> bool:
    text = sentence_text(value, limit=limit)
    if clean_generated_text(row.get(key)) == text:
        return False
    row[key] = text
    return True


def set_sentence_list(row: dict[str, Any], key: str, values: Sequence[str], *, limit: int = 700) -> bool:
    cleaned = [sentence_text(value, limit=limit) for value in values if clean_generated_text(value)]
    cleaned = list(unique_text(cleaned))
    if text_values(row.get(key)) == tuple(cleaned):
        return False
    row[key] = cleaned
    return True
