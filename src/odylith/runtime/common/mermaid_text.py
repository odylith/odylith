"""Text normalization for Mermaid sources rendered into Odylith surfaces."""

from __future__ import annotations

import re
from typing import Sequence

from odylith.runtime.common import display_text

_FIRST_CONTENT_RE = re.compile(r"^\s*(?!%%)(\S+)", re.MULTILINE)
_PARTICIPANT_RE = re.compile(r"^(\s*participant\s+\S+\s+as\s+)(.+?)\s*$", re.IGNORECASE)
_NOTE_RE = re.compile(r"^(\s*Note\s+(?:over|right of|left of)\s+[^:]+:\s*)(.+?)\s*$", re.IGNORECASE)


def clean_mermaid_text(value: object) -> str:
    """Return plain text that is safe to place inside a Mermaid label."""

    text = display_text.strip_inline_markdown_emphasis(value)
    text = text.replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return " ".join(text.split())


def escape_mermaid_label(value: object) -> str:
    """Escape the small set of characters that commonly break quoted Mermaid labels."""

    return clean_mermaid_text(value).replace('"', "'").replace("\n", " ").strip()


def wrap_mermaid_label(value: object, *, width: int = 24, max_lines: int = 3, limit: int = 96) -> str:
    """Wrap a Mermaid label with ``<br/>`` so SVG text stays inside its box."""

    text = _trim_text(escape_mermaid_label(value), limit=limit)
    if not text:
        return ""
    if "<br" in text.casefold():
        return text
    words = text.split()
    lines: list[str] = []
    current = ""
    truncated = False
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                truncated = True
                break
        else:
            current = candidate
    if current and len(lines) < max_lines:
        lines.append(current)
    elif current:
        truncated = True
    if truncated and lines:
        lines[-1] = _append_ellipsis(lines[-1], width=width)
    return "<br/>".join(lines)


def wrap_sequence_participant(value: object) -> str:
    """Wrap sequence participant aliases tightly enough for Mermaid actor boxes."""

    return wrap_mermaid_label(value, width=24, max_lines=3, limit=72) or "Participant"


def wrap_sequence_message(value: object) -> str:
    """Keep sequence arrow labels readable without stretching the diagram."""

    return wrap_mermaid_label(value, width=30, max_lines=2, limit=80)


def wrap_sequence_note(value: object) -> str:
    """Keep sequence notes compact; notes should orient the path, not restate the whole story."""

    return wrap_mermaid_label(value, width=34, max_lines=3, limit=120)


def normalize_mermaid_source(source: str) -> str:
    """Normalize consumer-visible Mermaid text without changing diagram topology."""

    first = _first_content_line(source)
    if first != "sequenceDiagram":
        return source
    return "\n".join(_normalize_sequence_lines(source.splitlines()))


def _normalize_sequence_lines(lines: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for raw_line in lines:
        stripped = raw_line.lstrip()
        if not stripped:
            normalized.append(raw_line)
            continue
        if stripped.startswith("%%"):
            normalized.append(_normalize_sequence_comment(raw_line))
            continue
        line = _normalize_sequence_participant(raw_line)
        note_line = _normalize_sequence_note(line)
        if note_line != line:
            normalized.append(note_line)
            continue
        line = note_line
        line = _normalize_sequence_arrow(line)
        normalized.append(line)
    return normalized


def _normalize_sequence_participant(line: str) -> str:
    match = _PARTICIPANT_RE.match(line)
    if match is None:
        return line
    return f"{match.group(1)}{wrap_sequence_participant(match.group(2))}"


def _normalize_sequence_comment(line: str) -> str:
    indentation = line[: len(line) - len(line.lstrip())]
    comment = line.lstrip()[2:].strip()
    cleaned = clean_mermaid_text(comment)
    return f"{indentation}%% {cleaned}" if cleaned else f"{indentation}%%"


def _normalize_sequence_note(line: str) -> str:
    match = _NOTE_RE.match(line)
    if match is None:
        return line
    return f"{match.group(1)}{wrap_sequence_note(match.group(2))}"


def _normalize_sequence_arrow(line: str) -> str:
    head, separator, message = line.partition(":")
    if not separator:
        return line
    normalized = wrap_sequence_message(message.replace(";", ","))
    return f"{head}: {normalized}" if normalized else f"{head}:"


def _first_content_line(source: str) -> str:
    match = _FIRST_CONTENT_RE.search(source)
    return str(match.group(1)).strip() if match is not None else ""


def _trim_text(value: str, *, limit: int) -> str:
    text = clean_mermaid_text(value)
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 1)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}…"


def _append_ellipsis(value: str, *, width: int) -> str:
    text = value.rstrip(" …")
    if len(text) >= width:
        text = text[: max(1, width - 1)].rstrip(" ,;:")
    return f"{text}…"


__all__ = [
    "clean_mermaid_text",
    "escape_mermaid_label",
    "normalize_mermaid_source",
    "wrap_mermaid_label",
    "wrap_sequence_message",
    "wrap_sequence_note",
    "wrap_sequence_participant",
]
