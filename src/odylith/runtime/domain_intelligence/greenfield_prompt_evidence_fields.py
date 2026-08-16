"""Recover typed field values from structured or compact operator evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


PROMPT_FIELD_NAMES = (
    "acceptance",
    "action",
    "actor",
    "actors",
    "access boundary",
    "assumption",
    "assumptions",
    "constraint",
    "constraints",
    "confirmed request",
    "data source",
    "data sources",
    "dependency",
    "dependencies",
    "domain",
    "domain label",
    "edited request",
    "external system",
    "external systems",
    "first complete path",
    "first action",
    "first path",
    "first path is fixed",
    "first user",
    "gate",
    "goal",
    "need",
    "non-goal",
    "non-goals",
    "objective",
    "operator",
    "operator role",
    "output",
    "owner",
    "path",
    "product",
    "product name",
    "proof boundary",
    "result",
    "request",
    "role",
    "roles",
    "rule",
    "safety",
    "safety boundary",
    "source",
    "sources",
    "state",
    "state change",
    "state model",
    "system",
    "systems",
    "task",
    "the first path is fixed",
    "title",
    "upstream system",
    "upstream systems",
    "user",
    "user task",
    "user role",
    "users",
    "visible result",
    "workflow",
    "boundary",
)
_PROMPT_FIELD_ALIASES = {
    "access boundary": "constraint",
    "boundary": "constraint",
    "first action": "action",
    "owner": "actor",
    "state change": "state",
}
_INLINE_FIELD_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:\*\*)?(?P<key>"
    + "|".join(re.escape(field) for field in sorted(PROMPT_FIELD_NAMES, key=len, reverse=True))
    + r")(?:\*\*)?\s*:\s*",
    flags=re.IGNORECASE,
)


def prompt_field_mapping(value: Any) -> dict[str, Any]:
    """Return normalized explicit fields without interpreting their product meaning."""

    text = str(value or "").strip()
    if not text:
        return {}
    structured, trailing_text, is_json = _json_payload(text)
    if is_json:
        fields: dict[str, Any] = {}
        _collect_json_fields(structured, fields)
        _merge_text_fields(trailing_text, fields)
        return fields
    fields = _markdown_field_mapping(text)
    for key, item in _inline_field_mapping(text).items():
        fields.setdefault(key, item)
    return fields


def prompt_field_values(value: Any, *, names: Sequence[str]) -> tuple[str, ...]:
    """Return flattened values for the requested typed evidence fields."""

    mapping = prompt_field_mapping(value)
    rows: list[str] = []
    seen: set[str] = set()
    for name in names:
        item = mapping.get(prompt_field_key(name))
        for raw in _scalar_values(item):
            text = clean_markdown_text(raw).strip(" /\n\t.;")
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                rows.append(text)
    return tuple(rows)


def prompt_field_key(value: Any) -> str:
    key = " ".join(str(value or "").casefold().replace("_", " ").split())
    return _PROMPT_FIELD_ALIASES.get(key, key)


def _json_payload(value: str) -> tuple[Any, str, bool]:
    if not value.startswith(("{", "[")):
        return None, value, False
    try:
        payload, end = json.JSONDecoder().raw_decode(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None, value, False
    structured = isinstance(payload, (Mapping, list, tuple))
    return payload, value[end:].strip(), structured


def _merge_text_fields(value: str, fields: dict[str, Any]) -> None:
    if not value:
        return
    trailing_fields = _markdown_field_mapping(value)
    for key, item in _inline_field_mapping(value).items():
        trailing_fields.setdefault(key, item)
    for key, item in trailing_fields.items():
        _merge_field_value(fields, key=key, value=item)


def _collect_json_fields(value: Any, fields: dict[str, Any]) -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = prompt_field_key(raw_key)
            if key in PROMPT_FIELD_NAMES:
                _merge_field_value(fields, key=key, value=item)
            _collect_json_fields(item, fields)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _collect_json_fields(item, fields)


def _merge_field_value(fields: dict[str, Any], *, key: str, value: Any) -> None:
    if key not in fields:
        fields[key] = value
        return
    fields[key] = [*_scalar_values(fields[key]), *_scalar_values(value)]


def _scalar_values(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(item for row in value for item in _scalar_values(row))
    if isinstance(value, Mapping):
        return ()
    return (value,)


def _markdown_field_mapping(value: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for raw_row in value.splitlines():
        row = raw_row.strip()
        if not row:
            continue
        if len(tuple(_INLINE_FIELD_RE.finditer(raw_row))) > 1:
            continue
        if row.startswith("|") and row.endswith("|"):
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            if len(cells) >= 2 and not all(set(cell) <= {"-", ":", " "} for cell in cells):
                key = prompt_field_key(cells[0])
                if key not in {"field", "key"}:
                    fields[key] = cells[1]
            continue
        match = re.match(
            r"^\s*(?:[-*]\s*)?(?:\*\*)?(?P<key>[A-Za-z][A-Za-z ]{1,40})(?:\*\*)?\s*:\s*(?P<value>.+)$",
            raw_row,
        )
        if match:
            fields[prompt_field_key(match.group("key"))] = match.group("value").strip()
    return fields


def _inline_field_mapping(value: str) -> dict[str, Any]:
    matches = list(_INLINE_FIELD_RE.finditer(value))
    fields: dict[str, Any] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
        field_value = clean_markdown_text(value[match.end() : end]).strip(" */#-\n\t.;")
        if field_value:
            fields[prompt_field_key(match.group("key"))] = field_value
    return fields


__all__ = ["PROMPT_FIELD_NAMES", "prompt_field_key", "prompt_field_mapping", "prompt_field_values"]
