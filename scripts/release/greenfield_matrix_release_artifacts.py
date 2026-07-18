"""Shared filesystem and digest checks for release-corpus evidence artifacts."""

from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re


_SAFE_ARTIFACT_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,127}\Z")


def is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_sha256(value: str) -> bool:
    return bool(value) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def safe_artifact_identifier(value: str) -> str | None:
    """Return a portable identifier that is safe to use in an artifact filename."""

    candidate = str(value or "").strip()
    return candidate if _SAFE_ARTIFACT_IDENTIFIER.fullmatch(candidate) else None


def repo_artifact_path(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    if not value or candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
