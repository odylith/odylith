"""Casebook Bug Ids helpers for the Odylith common layer."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

BUG_ID_FIELD = "Bug ID"
CANONICAL_BUG_HEADERS = (BUG_ID_FIELD, "Date", "Title", "Severity", "Components", "Status", "Link")
LEGACY_BUG_HEADERS = ("Date", "Title", "Severity", "Components", "Status", "Link")
_AUTO_BUG_ID_PREFIX = "CBX-"
_BUG_ID_LINE_RE = re.compile(r"^-?\s*Bug ID:\s*(?P<value>.*)$", re.IGNORECASE)


def normalize_casebook_bug_id(value: str) -> str:
    return " ".join(str(value or "").strip().split()).upper()


def fallback_casebook_bug_id(*, seed: str) -> str:
    token = Path(str(seed or "").strip()).as_posix().strip().lower()
    if not token:
        token = "unknown"
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:8].upper()
    return f"{_AUTO_BUG_ID_PREFIX}{digest}"


def resolve_casebook_bug_id(*, explicit_bug_id: str, seed: str) -> str:
    normalized = normalize_casebook_bug_id(explicit_bug_id)
    if normalized:
        return normalized
    return fallback_casebook_bug_id(seed=seed)


def load_casebook_bug_id_from_markdown(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for raw in lines:
        match = _BUG_ID_LINE_RE.match(str(raw).strip())
        if match is None:
            continue
        return normalize_casebook_bug_id(str(match.group("value") or ""))
    return ""


__all__ = [
    "BUG_ID_FIELD",
    "CANONICAL_BUG_HEADERS",
    "LEGACY_BUG_HEADERS",
    "fallback_casebook_bug_id",
    "load_casebook_bug_id_from_markdown",
    "normalize_casebook_bug_id",
    "resolve_casebook_bug_id",
]
