"""Shared version normalization and ordering for install lifecycle code."""

from __future__ import annotations

import re

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(.*)$")


def normalize_version(value: object) -> str:
    """Normalize version tokens so callers may pass `v0.x.y` or `0.x.y`."""
    return str(value or "").strip().lstrip("v")


def version_key(value: object) -> tuple[int, int, int, str]:
    """Build a sortable key for Odylith release version comparisons."""
    token = normalize_version(value)
    match = _VERSION_RE.match(token)
    if match is None:
        return (-1, -1, -1, token)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4))


def is_at_least(value: object, baseline: object) -> bool:
    """Return whether one normalized version is at least the baseline."""
    return version_key(value) >= version_key(baseline)


def is_before(value: object, baseline: object) -> bool:
    """Return whether one normalized version is strictly before the baseline."""
    return bool(normalize_version(value)) and version_key(value) < version_key(baseline)
