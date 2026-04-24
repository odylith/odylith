"""Sync live checked-in surfaces into the source-owned bundle mirror.

The Odylith product repo tracks two copies of governed dashboard assets:
- live checked-in surfaces under ``odylith/...``
- source-owned install mirrors under ``src/odylith/bundle/assets/odylith/...``

When renderers refresh reusable frontend assets, install-time contract tests
need the shipped copies to stay fresh. Maintainer-only governance payloads are
not reusable frontend assets, so this module also owns the fail-closed filter
that keeps product-repo truth out of the shipped consumer bundle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

_SCOPED_GUIDANCE_FILENAMES = frozenset({"AGENTS.md", "CLAUDE.md"})
_MAINTAINER_TRUTH_PREFIXES = (
    "atlas/source/",
    "casebook/bugs/",
    "compass/runtime/",
    "radar/source/",
    "registry/source/",
    "technical-plans/",
)
_MAINTAINER_GENERATED_EXACT = frozenset(
    {
        "atlas/mermaid-payload.v1.js",
        "casebook/casebook-payload.v1.js",
        "compass/compass-payload.v1.js",
        "compass/compass-runtime-truth.v1.js",
        "compass/compass-source-truth.v1.json",
        "radar/backlog-payload.v1.js",
        "radar/standalone-pages.v1.js",
        "radar/traceability-graph.v1.json",
        "registry/registry-payload.v1.js",
        "tooling-payload.v1.js",
    }
)
_MAINTAINER_GENERATED_PREFIXES = (
    "casebook/casebook-detail-shard-",
    "radar/backlog-detail-shard-",
    "radar/backlog-document-shard-",
    "registry/registry-detail-shard-",
)
_SHIP_SAFE_RADAR_SOURCE_EXACT = frozenset({"radar/source/programs/B-096.execution-waves.v1.json"})


def _live_surface_root(*, repo_root: Path) -> Path:
    """Return the checked-in live surface root in the product repo."""
    return (Path(repo_root).resolve() / "odylith").resolve()


def source_bundle_root(*, repo_root: Path) -> Path:
    """Return the source-owned bundle mirror root."""
    return (
        Path(repo_root).resolve()
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
    ).resolve()


def _bundle_mirror_enabled(*, repo_root: Path) -> bool:
    """Return whether the source bundle mirror exists in this repo layout."""
    return source_bundle_root(repo_root=repo_root).is_dir()


def _normalize_relative_token(path: Path | str) -> str:
    return Path(path).as_posix().lstrip("./")


def _is_scoped_guidance(token: str) -> bool:
    return Path(token).name in _SCOPED_GUIDANCE_FILENAMES


def _is_ship_safe_registry_truth(token: str) -> bool:
    return token == "registry/source/component_registry.v1.json" or (
        token.startswith("registry/source/components/")
        and token.endswith("/CURRENT_SPEC.md")
    )


def is_consumer_safe_bundle_relative_path(path: Path | str) -> bool:
    """Return whether a bundle asset is safe to ship into consumer installs.

    The source bundle may carry reusable product code, static frontend assets,
    managed guidance, skills, brand assets, release notes, and runtime corpora.
    It must never carry Odylith product-repo governance truth as consumer seed
    data. Scoped AGENTS/CLAUDE companions are the only files allowed inside
    otherwise maintainer-owned truth roots.
    """
    token = _normalize_relative_token(path)
    if not token or Path(token).name == ".DS_Store":
        return False
    if token in _MAINTAINER_GENERATED_EXACT:
        return False
    if any(token.startswith(prefix) for prefix in _MAINTAINER_GENERATED_PREFIXES):
        return False
    if _is_ship_safe_registry_truth(token) or token in _SHIP_SAFE_RADAR_SOURCE_EXACT:
        return True
    if any(token.startswith(prefix) for prefix in _MAINTAINER_TRUTH_PREFIXES):
        return _is_scoped_guidance(token)
    return True


def _live_relative_path(*, repo_root: Path, live_path: Path) -> Path:
    """Return the live path relative to the checked-in surface root."""
    live_root = _live_surface_root(repo_root=repo_root)
    resolved_live = Path(live_path).resolve()
    try:
        return resolved_live.relative_to(live_root)
    except ValueError as exc:  # pragma: no cover - defensive guard
        message = f"{resolved_live} is not under the live odylith surface root {live_root}"
        raise ValueError(message) from exc


def bundle_mirror_path(*, repo_root: Path, live_path: Path) -> Path:
    """Return the mirrored bundle path for one live surface file."""
    return (
        source_bundle_root(repo_root=repo_root)
        / _live_relative_path(repo_root=repo_root, live_path=live_path)
    ).resolve()


def should_mirror_live_path(*, repo_root: Path, live_path: Path) -> bool:
    """Return whether a live product-repo path may be mirrored into the bundle."""
    return is_consumer_safe_bundle_relative_path(
        _live_relative_path(repo_root=repo_root, live_path=live_path)
    )


def bundle_mirror_dir(*, repo_root: Path, live_dir: Path) -> Path:
    """Return the mirrored bundle directory for one live surface directory."""
    return (
        source_bundle_root(repo_root=repo_root)
        / _live_relative_path(repo_root=repo_root, live_path=live_dir)
    ).resolve()


def _write_bytes_if_changed(target: Path, content: bytes) -> None:
    """Write a file only when the bytes actually changed."""
    if target.is_file() and target.read_bytes() == content:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def sync_live_paths(*, repo_root: Path, live_paths: Iterable[Path]) -> tuple[Path, ...]:
    """Mirror the given live files into the source bundle when enabled."""
    root = Path(repo_root).resolve()
    if not _bundle_mirror_enabled(repo_root=root):
        return ()
    mirrored: list[Path] = []
    for live_path in live_paths:
        resolved_live = Path(live_path).resolve()
        if not resolved_live.is_file():
            continue
        mirror_path = bundle_mirror_path(repo_root=root, live_path=resolved_live)
        if not should_mirror_live_path(repo_root=root, live_path=resolved_live):
            if mirror_path.is_file():
                mirror_path.unlink()
            continue
        _write_bytes_if_changed(mirror_path, resolved_live.read_bytes())
        mirrored.append(mirror_path)
    return tuple(mirrored)


def sync_live_glob(*, repo_root: Path, live_dir: Path, pattern: str) -> tuple[Path, ...]:
    """Mirror a glob of live files and prune stale mirrored siblings."""
    root = Path(repo_root).resolve()
    if not _bundle_mirror_enabled(repo_root=root):
        return ()
    live_parent = Path(live_dir).resolve()
    mirror_dir = bundle_mirror_dir(repo_root=root, live_dir=live_parent)
    live_matches = sorted(
        path
        for path in live_parent.glob(pattern)
        if path.is_file() and should_mirror_live_path(repo_root=root, live_path=path.resolve())
    )
    mirrored = sync_live_paths(repo_root=root, live_paths=live_matches)
    live_names = {path.name for path in live_matches}
    if mirror_dir.is_dir():
        for stale_path in mirror_dir.glob(pattern):
            if stale_path.name in live_names:
                continue
            if stale_path.is_file():
                stale_path.unlink()
        if not any(mirror_dir.iterdir()):
            mirror_dir.rmdir()
    return mirrored


def prune_unsafe_bundle_paths(*, repo_root: Path) -> tuple[Path, ...]:
    """Remove existing bundle files that violate the consumer-safe boundary."""
    root = source_bundle_root(repo_root=Path(repo_root).resolve())
    if not root.is_dir():
        return ()
    removed: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: len(candidate.parts), reverse=True):
        if path.is_file() and not is_consumer_safe_bundle_relative_path(path.relative_to(root)):
            path.unlink()
            removed.append(path.resolve())
            continue
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    return tuple(reversed(removed))
