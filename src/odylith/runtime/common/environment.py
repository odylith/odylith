"""Shared environment flag semantics for Odylith runtime boundaries."""

from __future__ import annotations

import os


def env_flag_enabled(name: str) -> bool:
    """Return whether an environment flag is set to a non-false value."""

    token = str(os.environ.get(name) or "").strip().casefold()
    return token not in {"", "0", "false", "no", "off"}


__all__ = ["env_flag_enabled"]
