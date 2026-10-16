"""Safe text projection for host-authored governed ledger fields."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string

_QUOTE_TRANSLATION = str.maketrans(
    {
        '"': "",
        "`": "",
        "“": "",
        "”": "",
        "„": "",
        "‟": "",
        "‘": "'",
        "’": "'",
    }
)


def safe_ledger_text(value: Any) -> str:
    """Return plain ledger text safe for governed proposal custody.

    Host reasoning may explain a typed decision with quoted fragments. The typed
    replacement fact carries semantic authority; ledger prose is only evidence.
    Ledger text therefore strips quote delimiters while preserving ordinary
    apostrophes inside words.
    """

    text = normalize_string(value)
    if not text:
        return ""
    return normalize_string(_strip_standalone_apostrophes(text.translate(_QUOTE_TRANSLATION)))


def safe_ledger_value(value: Any) -> Any:
    """Recursively normalize host-authored ledger text without changing facts."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            clean_key = normalize_string(key)
            if not clean_key:
                continue
            clean_item = safe_ledger_value(item)
            if _empty_safe_value(clean_item):
                continue
            result[clean_key] = clean_item
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        rows = []
        for item in value:
            clean_item = safe_ledger_value(item)
            if not _empty_safe_value(clean_item):
                rows.append(clean_item)
        return rows
    if isinstance(value, str):
        return safe_ledger_text(value)
    return value


def _strip_standalone_apostrophes(value: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(value):
        if char != "'":
            chars.append(char)
            continue
        previous_char = value[index - 1] if index > 0 else ""
        next_char = value[index + 1] if index + 1 < len(value) else ""
        if previous_char.isalnum() and next_char.isalnum():
            chars.append(char)
    return "".join(chars)


def _empty_safe_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


__all__ = ["safe_ledger_text", "safe_ledger_value"]
