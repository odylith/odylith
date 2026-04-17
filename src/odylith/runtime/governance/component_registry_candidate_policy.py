from __future__ import annotations

import re

_WORD_GAP_RE = re.compile(r"[^a-z0-9]+")

_RETIRED_COMPONENT_CANDIDATE_TOKENS: frozenset[str] = frozenset(
    {
        "execution-governance",
    }
)


def _normalize_component_candidate_token(value: object) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return ""
    return _WORD_GAP_RE.sub("-", token).strip("-")


def is_retired_component_candidate_token(value: object) -> bool:
    """Return true for hard-cut component names that must not re-enter Registry review."""

    return _normalize_component_candidate_token(value) in _RETIRED_COMPONENT_CANDIDATE_TOKENS


__all__ = ["is_retired_component_candidate_token"]
