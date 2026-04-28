"""Shared Git ignore rules for Odylith install-owned local state."""

from __future__ import annotations

from pathlib import Path

from odylith.install.fs import atomic_write_text

ODYLITH_GITIGNORE_ENTRY = "/.odylith/"
COMPASS_REFRESH_STATE_GITIGNORE_ENTRY = "/odylith/compass/runtime/refresh-state.v1.json"
ODYLITH_GITIGNORE_PATTERNS = {
    ".odylith",
    ".odylith/",
    "/.odylith",
    "/.odylith/",
}
COMPASS_REFRESH_STATE_GITIGNORE_PATTERNS = {
    "odylith/compass/runtime/refresh-state.v1.json",
    "/odylith/compass/runtime/refresh-state.v1.json",
}
ODYLITH_GITIGNORE_ENTRIES = (
    ODYLITH_GITIGNORE_ENTRY,
    COMPASS_REFRESH_STATE_GITIGNORE_ENTRY,
)


def ensure_odylith_gitignore_entry(*, repo_root: Path, git_repo_present: bool | None = None) -> bool:
    """Ensure repo-local Odylith runtime state stays out of Git."""
    root = Path(repo_root).resolve()
    del git_repo_present
    path = root / ".gitignore"
    if path.exists() and not path.is_file():
        return False
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    normalized_lines = {line.strip() for line in existing.splitlines()}
    missing_entries: list[str] = []
    if not normalized_lines.intersection(ODYLITH_GITIGNORE_PATTERNS):
        missing_entries.append(ODYLITH_GITIGNORE_ENTRY)
    if not normalized_lines.intersection(COMPASS_REFRESH_STATE_GITIGNORE_PATTERNS):
        missing_entries.append(COMPASS_REFRESH_STATE_GITIGNORE_ENTRY)
    if not missing_entries:
        return False
    updated = existing
    if updated and not updated.endswith("\n"):
        updated += "\n"
    for entry in missing_entries:
        updated += f"{entry}\n"
    atomic_write_text(path, updated, encoding="utf-8")
    return True


def rewrite_legacy_gitignore_entries(*, repo_root: Path) -> None:
    """Rewrite legacy Odyssey ignore entries to Odylith equivalents."""
    path = Path(repo_root).resolve() / ".gitignore"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    updated = text.replace("/.odyssey/", ODYLITH_GITIGNORE_ENTRY).replace("/.odyssey", "/.odylith")
    if updated != text:
        atomic_write_text(path, updated, encoding="utf-8")
