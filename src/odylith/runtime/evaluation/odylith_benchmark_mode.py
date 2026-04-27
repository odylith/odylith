"""Shared public benchmark-mode normalization for evaluation surfaces."""

from __future__ import annotations

_PUBLIC_MODE_ALIASES = {
    "odylith_off": "raw_agent_baseline",
}


def normalize_public_mode(mode: str) -> str:
    """Normalize public benchmark mode labels onto the stable contract."""
    token = str(mode or "").strip()
    return _PUBLIC_MODE_ALIASES.get(token, token)
