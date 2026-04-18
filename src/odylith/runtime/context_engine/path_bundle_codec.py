"""Path Bundle Codec helpers for the Odylith context engine layer."""

from __future__ import annotations

from typing import Any
from typing import Sequence


def _string_rows(value: Any) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return rows
    for item in value:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _candidate_prefix(path: str, prefix_segments: int) -> str:
    parts = [part for part in str(path or "").strip().split("/") if part]
    if len(parts) <= prefix_segments:
        return ""
    return "/".join(parts[:prefix_segments]) + "/"


def _encode_bundle(prefix: str, rows: Sequence[str]) -> str:
    suffixes = [str(row).strip()[len(prefix):] for row in rows if str(row).strip().startswith(prefix)]
    return f"{prefix}{{{','.join(suffixes)}}}" if prefix and suffixes else ""


def compact_path_rows(rows: Sequence[str]) -> list[str]:
    normalized = _string_rows(rows)
    if len(normalized) < 2:
        return normalized
    remaining = set(normalized)
    compacted: list[str] = []
    for row in normalized:
        if row not in remaining:
            continue
        bundled = False
        for prefix_segments in range(5, 1, -1):
            prefix = _candidate_prefix(row, prefix_segments)
            if len(prefix) < 12:
                continue
            group = [item for item in normalized if item in remaining and item.startswith(prefix)]
            if len(group) < 2:
                continue
            encoded = _encode_bundle(prefix, group)
            plain_length = sum(len(item) for item in group) + max(0, len(group) - 1)
            if not encoded or len(encoded) >= plain_length:
                continue
            compacted.append(encoded)
            for item in group:
                remaining.discard(item)
            bundled = True
            break
        if not bundled:
            compacted.append(row)
            remaining.discard(row)
    return compacted


def expand_path_rows(value: Any) -> list[str]:
    expanded: list[str] = []
    for token in _string_rows(value):
        if "{" not in token or not token.endswith("}"):
            expanded.append(token)
            continue
        prefix, _, suffix_block = token.partition("{")
        suffixes = [part.strip() for part in suffix_block[:-1].split(",") if part.strip()]
        if not prefix or not suffixes:
            expanded.append(token)
            continue
        expanded.extend(f"{prefix}{suffix}" for suffix in suffixes)
    return _string_rows(expanded)


__all__ = [
    "compact_path_rows",
    "expand_path_rows",
]
