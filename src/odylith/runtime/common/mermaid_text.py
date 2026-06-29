"""Text normalization for Mermaid sources rendered into Odylith surfaces."""

from __future__ import annotations

import re
from typing import Sequence

from odylith.runtime.common import display_text

_FIRST_CONTENT_RE = re.compile(r"^\s*(?!%%)(\S+)", re.MULTILINE)
_PARTICIPANT_RE = re.compile(r"^(\s*participant\s+\S+\s+as\s+)(.+?)\s*$", re.IGNORECASE)
_NOTE_RE = re.compile(r"^(\s*Note\s+(?:over|right of|left of)\s+[^:]+:\s*)(.+?)\s*$", re.IGNORECASE)
_NUMBERED_FLOWCHART_NODE_RE = re.compile(
    r"(?<![\w-])(?P<prefix>[A-Za-z]+)(?P<number>\d+)\s*\[\""
)
_LABEL_HEADER_TEXTS = frozenset(
    {
        "blocked or corrected",
        "deferred scope",
        "domain state",
        "evidence record",
        "external input",
        "first action",
        "outside release",
        "proof check",
        "proof checkpoint",
        "proof result",
        "release claim",
        "release decision",
        "release proof",
        "state object",
        "visible result",
    }
)
_DANGLING_LINE_TAILS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "because",
        "by",
        "for",
        "from",
        "if",
        "in",
        "into",
        "of",
        "on",
        "or",
        "the",
        "to",
        "when",
        "while",
        "with",
        "without",
    }
)


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
    lines = _rebalance_connector_line_breaks(lines, width=width)
    lines = _rebalance_dangling_line_breaks(lines, width=width)
    if truncated and lines:
        lines[-1] = _append_ellipsis(lines[-1], width=width)
    return "<br/>".join(lines)


def _rebalance_connector_line_breaks(lines: list[str], *, width: int) -> list[str]:
    rebalanced = list(lines)
    for index in range(len(rebalanced) - 1):
        words = rebalanced[index].split()
        if not words or words[-1].casefold().strip(".,;:") not in {"and", "or"}:
            continue
        connector = words[-1]
        next_line = f"{connector} {rebalanced[index + 1]}".strip()
        previous_line = " ".join(words[:-1]).strip()
        if len(words[:-1]) >= 3 and len(rebalanced[index + 1].split()) == 1 and previous_line and len(next_line) <= width:
            rebalanced[index] = previous_line
            rebalanced[index + 1] = next_line
    return rebalanced


def _rebalance_dangling_line_breaks(lines: list[str], *, width: int) -> list[str]:
    """Move stranded connector words to the following visual line."""

    rebalanced = list(lines)
    for index in range(len(rebalanced) - 1):
        words = rebalanced[index].split()
        if len(words) < 2:
            continue
        tail = words[-1].casefold().strip(".,;:")
        if tail not in _DANGLING_LINE_TAILS:
            continue
        head = " ".join(words[:-1]).strip(" ,;:")
        if not head:
            continue
        next_line = f"{words[-1]} {rebalanced[index + 1]}".strip()
        if len(next_line) > max(width + 12, len(rebalanced[index + 1])):
            continue
        rebalanced[index] = head
        rebalanced[index + 1] = next_line
    return rebalanced


def wrap_sequence_participant(value: object) -> str:
    """Wrap sequence participant aliases tightly enough for Mermaid actor boxes."""

    return wrap_mermaid_label(value, width=24, max_lines=3, limit=72) or "Participant"


def wrap_sequence_message(value: object) -> str:
    """Keep sequence arrow labels readable without stretching the diagram."""

    return wrap_mermaid_label(value, width=30, max_lines=3, limit=110)


def wrap_sequence_note(value: object) -> str:
    """Keep sequence notes compact; notes should orient the path, not restate the whole story."""

    return wrap_mermaid_label(value, width=34, max_lines=3, limit=120)


def normalize_mermaid_source(source: str) -> str:
    """Normalize consumer-visible Mermaid text without changing diagram topology."""

    first = _first_content_line(source)
    if first != "sequenceDiagram":
        return source
    return "\n".join(_normalize_sequence_lines(source.splitlines()))


def visible_mermaid_label_texts(source: object) -> tuple[str, ...]:
    """Return human-visible labels from Mermaid source without graph syntax."""

    return tuple(clean_mermaid_text(label.replace("<br/>", " ").replace("<br>", " ")) for label in _raw_visible_labels(source) if clean_mermaid_text(label))


def visible_mermaid_label_quality_texts(source: object) -> tuple[str, ...]:
    """Return Mermaid labels as prose quality units without flattening label headers into payload text."""

    units: list[str] = []
    for label in _raw_visible_labels(source):
        chunks = [
            clean_mermaid_text(chunk)
            for chunk in re.split(r"(?i)<br\s*/?>", str(label or ""))
            if clean_mermaid_text(chunk)
        ]
        if not chunks:
            continue
        header = chunks[0].casefold().strip(" .:")
        if header in _LABEL_HEADER_TEXTS:
            units.extend(chunks[1:] or chunks)
            continue
        units.append(clean_mermaid_text(label.replace("<br/>", " ").replace("<br>", " ")))
    return tuple(unit for unit in dict.fromkeys(units) if unit)


def _raw_visible_labels(source: object) -> tuple[str, ...]:
    labels: list[str] = []
    for raw_line in str(source or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("%%", "classDef ", "class ", "style ")):
            continue
        labels.extend(_quoted_flowchart_labels(line))
        participant = _participant_visible_label(line)
        if participant:
            labels.append(participant)
        note = _note_visible_label(line)
        if note:
            labels.append(note)
        message = _sequence_message_label(line)
        if message:
            labels.append(message)
    return tuple(labels)


def numbered_flowchart_node_ids(source: object, *, prefix: str = "S") -> tuple[str, ...]:
    """Return unique numbered flowchart node IDs in first-seen order."""

    wanted_prefix = str(prefix or "").strip()
    if not wanted_prefix:
        return ()
    seen: set[str] = set()
    node_ids: list[str] = []
    for match in _NUMBERED_FLOWCHART_NODE_RE.finditer(str(source or "")):
        if match.group("prefix") != wanted_prefix:
            continue
        node_id = f"{match.group('prefix')}{match.group('number')}"
        if node_id in seen:
            continue
        seen.add(node_id)
        node_ids.append(node_id)
    return tuple(node_ids)


def numbered_flowchart_node_count(source: object, *, prefix: str = "S") -> int:
    """Count unique numbered flowchart nodes for a caller-owned prefix."""

    return len(numbered_flowchart_node_ids(source, prefix=prefix))


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


def _quoted_flowchart_labels(line: str) -> list[str]:
    labels: list[str] = []
    index = 0
    while index < len(line):
        start = line.find('["', index)
        if start < 0:
            break
        label_start = start + 2
        end = line.find('"]', label_start)
        if end < 0:
            labels.append(line[label_start:])
            break
        labels.append(line[label_start:end])
        index = end + 2
    return labels


def _participant_visible_label(line: str) -> str:
    match = _PARTICIPANT_RE.match(line)
    return clean_mermaid_text(match.group(2)) if match else ""


def _note_visible_label(line: str) -> str:
    match = _NOTE_RE.match(line)
    return clean_mermaid_text(match.group(2)) if match else ""


def _sequence_message_label(line: str) -> str:
    if '["' in line:
        return ""
    if ":" not in line or not any(operator in line for operator in ("->>", "-->>", "->", "-->")):
        return ""
    return clean_mermaid_text(line.split(":", 1)[1])


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
    return _strip_dangling_tail(clipped)


def _append_ellipsis(value: str, *, width: int) -> str:
    text = value.rstrip(" …")
    if len(text) >= width:
        text = text[: max(1, width - 1)].rstrip(" ,;:")
    return _strip_dangling_tail(text)


def _strip_dangling_tail(value: str) -> str:
    text = clean_mermaid_text(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|for|from|if|in|into|of|on|or|the|to|when|while|with|without)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return _strip_unbalanced_quote_tail(cleaned)
        text = cleaned


def _strip_unbalanced_quote_tail(value: str) -> str:
    text = clean_mermaid_text(value).rstrip(" ,;:.")
    if text.count('"') % 2:
        return text.rsplit('"', 1)[0].rstrip(" ,;:.")
    if re.search(r"(?:^|\s)'[A-Za-z][^']*$", text):
        return text.rsplit("'", 1)[0].rstrip(" ,;:.")
    return text


__all__ = [
    "clean_mermaid_text",
    "escape_mermaid_label",
    "normalize_mermaid_source",
    "numbered_flowchart_node_count",
    "numbered_flowchart_node_ids",
    "visible_mermaid_label_texts",
    "visible_mermaid_label_quality_texts",
    "wrap_mermaid_label",
    "wrap_sequence_message",
    "wrap_sequence_note",
    "wrap_sequence_participant",
]
