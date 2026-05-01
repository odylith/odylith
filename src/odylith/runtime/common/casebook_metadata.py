"""Canonical compact metadata helpers for Casebook source and projections."""

from __future__ import annotations

import re
from collections.abc import Sequence

_COMPACT_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_NON_TOKEN_RE = re.compile(r"[^A-Za-z0-9]+")

_ACRONYMS = {
    "ai": "AI",
    "api": "API",
    "cli": "CLI",
    "db": "DB",
    "html": "HTML",
    "osw": "OSW",
    "ui": "UI",
    "ux": "UX",
}

_STATUS_ALIASES = {
    "closed": "Closed",
    "fixed": "Fixed",
    "fixed pending release": "FixedPendingRelease",
    "fixedpendingrelease": "FixedPendingRelease",
    "in progress": "InProgress",
    "inprogress": "InProgress",
    "mitigated": "Mitigated",
    "monitoring": "Monitoring",
    "open": "Open",
    "resolved": "Resolved",
}
_TERMINAL_STATUSES = frozenset({"closed", "fixed", "fixedpendingrelease", "resolved"})


def normalize_casebook_scalar(value: str | Sequence[str] | None) -> str:
    """Normalize scalar or list-like Casebook metadata into plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="ignore").strip()
    return "\n".join(str(item).strip() for item in value if str(item).strip()).strip()


def casebook_token_is_valid(value: str | Sequence[str] | None) -> bool:
    """Return whether the value is one compact Casebook metadata token."""
    token = normalize_casebook_scalar(value)
    return bool(token) and _COMPACT_TOKEN_RE.fullmatch(token) is not None


def compact_casebook_token(value: str | Sequence[str] | None) -> str:
    """Convert prose or separator-delimited metadata into one compact token."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    if casebook_token_is_valid(raw):
        return _preserve_known_acronym_token(raw)
    parts = [part for part in _NON_TOKEN_RE.split(raw) if part]
    return "".join(_compact_part(part) for part in parts)


def canonical_casebook_status(value: str | Sequence[str] | None) -> str:
    """Canonicalize Casebook Status to one display-safe token."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    folded = _fold_metadata_value(raw)
    if folded.startswith("mitigated"):
        return "Mitigated"
    if folded.startswith("open"):
        return "Open"
    if folded.startswith("closed"):
        return "Closed"
    alias = _STATUS_ALIASES.get(folded) or _STATUS_ALIASES.get(folded.replace(" ", ""))
    if alias:
        return alias
    return compact_casebook_token(raw)


def canonical_casebook_type(value: str | Sequence[str] | None) -> str:
    """Canonicalize Casebook Type to one display-safe token."""
    raw = normalize_casebook_scalar(value)
    if not raw:
        return ""
    return compact_casebook_token(raw)


def casebook_status_is_terminal(value: str | Sequence[str] | None) -> bool:
    """Return whether the compact Casebook status represents a closed bug."""
    status = canonical_casebook_status(value)
    return status.casefold() in _TERMINAL_STATUSES


def _compact_part(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    acronym = _ACRONYMS.get(token.casefold())
    if acronym:
        return acronym
    if token.isupper() and len(token) <= 6:
        return token
    return token[:1].upper() + token[1:].lower()


def _fold_metadata_value(value: str) -> str:
    return " ".join(part.casefold() for part in _NON_TOKEN_RE.split(str(value or "")) if part)


def _preserve_known_acronym_token(value: str) -> str:
    token = str(value or "").strip()
    return _ACRONYMS.get(token.casefold(), token)
