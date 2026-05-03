"""Shared parsing helpers for Radar backlog metadata fields."""

from __future__ import annotations


def split_metadata_ids(raw: str) -> list[str]:
    values: list[str] = []
    for token in str(raw or "").replace(";", ",").split(","):
        normalized = token.strip().upper()
        if not normalized:
            continue
        values.append(normalized)
    return values
