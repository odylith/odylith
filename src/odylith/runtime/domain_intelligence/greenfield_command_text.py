"""Command text helpers for greenfield operator handoffs."""

from __future__ import annotations


def shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


__all__ = ["shell_quote"]
