"""Sync-scoped shared read-model state for in-process governed sync.

The sync runner already has a runtime fast path where multiple governance and
surface commands execute inside one Python process. This module gives that path
one explicit session object so hot helpers can reuse the same repo-scoped facts
instead of repeatedly rediscovering them.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, TypeVar


_T = TypeVar("_T")
_ACTIVE_SYNC_SESSION: ContextVar["GovernedSyncSession | None"] = ContextVar(
    "_ACTIVE_SYNC_SESSION",
    default=None,
)


@dataclass(slots=True)
class GovernedSyncSession:
    """Process-local shared read model for one sync execution."""

    repo_root: Path
    _cache: dict[tuple[str, str], Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).resolve()

    @property
    def repo_root_token(self) -> str:
        return str(self.repo_root)

    def get_or_compute(
        self,
        *,
        namespace: str,
        key: str,
        builder: Callable[[], _T],
    ) -> _T:
        cache_key = (str(namespace).strip(), str(key).strip())
        if cache_key not in self._cache:
            self._cache[cache_key] = builder()
        return self._cache[cache_key]

    def clear_namespaces(self, *namespaces: str) -> None:
        normalized = {str(namespace).strip() for namespace in namespaces if str(namespace).strip()}
        if not normalized:
            return
        for cache_key in [key for key in tuple(self._cache) if key[0] in normalized]:
            self._cache.pop(cache_key, None)

    def clear_namespace_group(self, namespaces: Iterable[str]) -> None:
        self.clear_namespaces(*(str(namespace).strip() for namespace in namespaces))

    def repo_root_for_path(self, path: Path) -> Path | None:
        candidate = Path(path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError:
            return None
        return self.repo_root


def active_sync_session() -> GovernedSyncSession | None:
    """Return the active governed sync session when one is installed."""

    return _ACTIVE_SYNC_SESSION.get()


@contextmanager
def activate_sync_session(session: GovernedSyncSession) -> Iterator[GovernedSyncSession]:
    """Install one sync session for the current execution context."""

    token: Token[GovernedSyncSession | None] = _ACTIVE_SYNC_SESSION.set(session)
    try:
        yield session
    finally:
        _ACTIVE_SYNC_SESSION.reset(token)


__all__ = [
    "GovernedSyncSession",
    "activate_sync_session",
    "active_sync_session",
]
