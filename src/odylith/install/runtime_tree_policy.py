from __future__ import annotations

from pathlib import Path

from odylith.install.fs import remove_path

_IGNORED_RUNTIME_METADATA_FILENAMES = frozenset({".DS_Store"})
def is_ignored_runtime_tree_entry(*, version_root: Path, candidate: Path) -> bool:
    try:
        relative_path = candidate.relative_to(version_root)
    except ValueError:
        return False
    name = relative_path.name.strip()
    if not name:
        return False
    return name in _IGNORED_RUNTIME_METADATA_FILENAMES or name.startswith("._")


def scrub_runtime_tree_metadata(version_root: Path) -> tuple[str, ...]:
    if not version_root.is_dir():
        return ()
    removed: list[str] = []
    for candidate in sorted(version_root.rglob("*")):
        if candidate.is_dir() and not candidate.is_symlink():
            continue
        if not is_ignored_runtime_tree_entry(version_root=version_root, candidate=candidate):
            continue
        if not candidate.exists() and not candidate.is_symlink():
            continue
        remove_path(candidate)
        removed.append(str(candidate))
    return tuple(removed)


def cleanup_runtime_versions_residue(versions_dir: Path, *, version: str) -> tuple[str, ...]:
    if not versions_dir.is_dir():
        return ()
    normalized_version = str(version or "").strip()
    if not normalized_version:
        return ()
    removed: list[str] = []
    for pattern in (f".{normalized_version}.backup-*", f".{normalized_version}.stage-*"):
        for candidate in sorted(versions_dir.glob(pattern)):
            if not candidate.exists() and not candidate.is_symlink():
                continue
            remove_path(candidate)
            removed.append(str(candidate))
    return tuple(removed)
