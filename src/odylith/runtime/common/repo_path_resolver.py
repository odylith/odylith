"""Memoized repo-root path normalization helpers."""

from __future__ import annotations

import os
from pathlib import Path


class RepoPathResolver:
    """Resolve repo-local paths once and reuse derived render-friendly forms."""

    __slots__ = (
        "repo_root",
        "output_path",
        "_href_cache",
        "_repo_path_cache",
        "_resolved_cache",
    )

    def __init__(self, *, repo_root: Path, output_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.output_path = Path(output_path).expanduser().resolve() if output_path is not None else None
        self._resolved_cache: dict[str, Path] = {}
        self._repo_path_cache: dict[str, str] = {}
        self._href_cache: dict[str, str] = {}

    def resolve(self, value: str | Path) -> Path:
        token = str(value or "").strip()
        cached = self._resolved_cache.get(token)
        if cached is not None:
            return cached
        raw = Path(token)
        target = raw.resolve() if raw.is_absolute() else (self.repo_root / raw).resolve()
        self._resolved_cache[token] = target
        return target

    def repo_path(self, value: str | Path) -> str:
        target = self.resolve(value)
        cache_key = str(target)
        cached = self._repo_path_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            repo_path = target.relative_to(self.repo_root).as_posix()
        except ValueError:
            repo_path = str(target)
        self._repo_path_cache[cache_key] = repo_path
        return repo_path

    def href(self, value: str | Path) -> str:
        if self.output_path is None:
            raise ValueError("output_path is required to build hrefs")
        target = self.resolve(value)
        cache_key = str(target)
        cached = self._href_cache.get(cache_key)
        if cached is not None:
            return cached
        rel = os.path.relpath(str(target), start=str(self.output_path.parent))
        href = Path(rel).as_posix()
        self._href_cache[cache_key] = href
        return href


__all__ = ["RepoPathResolver"]
