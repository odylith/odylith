"""Shared severity tokens for governed Odylith contracts."""

from __future__ import annotations

VALID_SEVERITIES = frozenset(("critical", "high", "medium", "low"))


def render_valid_severities() -> str:
    """Return the stable operator-facing severity token list."""
    return ", ".join(sorted(VALID_SEVERITIES))
