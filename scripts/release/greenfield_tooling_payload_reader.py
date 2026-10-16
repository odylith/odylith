"""Read externalized tooling dashboard payloads for release proof."""

from __future__ import annotations

from collections.abc import Mapping
import json


def read_tooling_payload_js(text: str, global_name: str = "__ODYLITH_TOOLING_DATA__") -> Mapping[str, object]:
    payload = _extract_js_payload_assignment(str(text or ""), global_name)
    return payload if isinstance(payload, Mapping) else {}


def _extract_js_payload_assignment(text: str, global_name: str) -> Mapping[str, object]:
    global_index = text.find(global_name)
    if global_index < 0:
        return {}
    equals = text.find("=", global_index)
    if equals < 0:
        return {}
    value_start = _skip_js_whitespace(text, equals + 1)
    if value_start >= len(text):
        return {}
    if text[value_start] == "{":
        return _decode_json_object_at(text, value_start)
    identifier = _read_js_identifier(text, value_start)
    if not identifier:
        return {}
    binding_start = _find_js_object_binding(text[:global_index], identifier)
    return _decode_json_object_at(text, binding_start) if binding_start >= 0 else {}


def _decode_json_object_at(text: str, json_start: int) -> Mapping[str, object]:
    try:
        payload, _end = json.JSONDecoder().raw_decode(text[json_start:])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _find_js_object_binding(text: str, identifier: str) -> int:
    cursor = 0
    while cursor < len(text):
        found = _find_next_identifier(text, identifier, cursor)
        if found < 0:
            return -1
        equals = text.find("=", found + len(identifier))
        if equals < 0:
            return -1
        prefix = text[max(0, found - 12) : found]
        if not any(keyword in prefix.split()[-2:] for keyword in ("const", "let", "var")):
            cursor = found + len(identifier)
            continue
        value_start = _skip_js_whitespace(text, equals + 1)
        if value_start < len(text) and text[value_start] == "{":
            return value_start
        cursor = found + len(identifier)
    return -1


def _find_next_identifier(text: str, identifier: str, start: int) -> int:
    cursor = max(0, int(start))
    while True:
        found = text.find(identifier, cursor)
        if found < 0:
            return -1
        before = text[found - 1] if found > 0 else " "
        after_index = found + len(identifier)
        after = text[after_index] if after_index < len(text) else " "
        if not (_is_js_identifier_char(before) or _is_js_identifier_char(after)):
            return found
        cursor = found + len(identifier)


def _read_js_identifier(text: str, start: int) -> str:
    cursor = max(0, int(start))
    if cursor >= len(text):
        return ""
    first = text[cursor]
    if not (first.isalpha() or first in {"_", "$"}):
        return ""
    chars = [first]
    cursor += 1
    while cursor < len(text) and _is_js_identifier_char(text[cursor]):
        chars.append(text[cursor])
        cursor += 1
    return "".join(chars)


def _skip_js_whitespace(text: str, start: int) -> int:
    cursor = max(0, int(start))
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def _is_js_identifier_char(char: str) -> bool:
    return bool(char) and (char.isalnum() or char in {"_", "$"})


__all__ = ["read_tooling_payload_js"]
