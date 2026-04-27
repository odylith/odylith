"""Command-scoped read-session reuse and shared hot-path cache budgeting.

Odylith's hot commands often execute several tightly related runtime reads in
one Python process. This module provides two layers of reuse:

- one shared byte-budgeted process cache for compact hot-path facts; and
- one command-scoped runtime read session that keeps lightweight handles and
  fingerprints together for the duration of the current operation.

Both layers intentionally cap memory and prefer recompute over unbounded growth.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterator
from typing import MutableMapping
from typing import TypeVar

from odylith.runtime.common.cache_budget_policy import (
    ByteBudgetedSegmentedCache,
    CacheBudgetPolicy,
)


_T = TypeVar("_T")
_MISSING = object()
_CACHE_POLICY: CacheBudgetPolicy | None = None
_SHARED_PROCESS_HOT_CACHE: ByteBudgetedSegmentedCache | None = None
_ACTIVE_RUNTIME_READ_SESSION: ContextVar["RuntimeReadSession | None"] = ContextVar(
    "_ACTIVE_RUNTIME_READ_SESSION",
    default=None,
)


def runtime_cache_budget_policy() -> CacheBudgetPolicy:
    """Return the process-wide cache budget policy, detecting it once lazily."""
    global _CACHE_POLICY
    if _CACHE_POLICY is None:
        _CACHE_POLICY = CacheBudgetPolicy.detect()
    return _CACHE_POLICY


def shared_process_hot_cache() -> ByteBudgetedSegmentedCache:
    """Return the shared process-local hot-path cache."""
    global _SHARED_PROCESS_HOT_CACHE
    if _SHARED_PROCESS_HOT_CACHE is None:
        policy = runtime_cache_budget_policy()
        _SHARED_PROCESS_HOT_CACHE = ByteBudgetedSegmentedCache(
            name="odylith-hot-path-process-cache",
            max_bytes=policy.hot_path_budget_bytes,
        )
    return _SHARED_PROCESS_HOT_CACHE


class NamespacedCacheView(MutableMapping[Any, Any]):
    """Expose one namespace inside the shared process hot cache."""

    def __init__(self, *, namespace: str) -> None:
        self.namespace = str(namespace).strip() or "default"

    def _wrap(self, key: Any) -> tuple[str, Any]:
        """Attach this view's namespace to a cache key."""
        return (self.namespace, key)

    def __getitem__(self, key: Any) -> Any:
        return shared_process_hot_cache()[self._wrap(key)]

    def __setitem__(self, key: Any, value: Any) -> None:
        shared_process_hot_cache()[self._wrap(key)] = value

    def __delitem__(self, key: Any) -> None:
        del shared_process_hot_cache()[self._wrap(key)]

    def _matching_wrapped_keys(self) -> list[tuple[str, Any]]:
        """Return the wrapped keys currently owned by this namespace."""
        return [wrapped for wrapped in shared_process_hot_cache() if wrapped[0] == self.namespace]

    def __iter__(self) -> Iterator[Any]:
        """Iterate the unwrapped keys that belong to this namespace."""
        for _namespace, key in self._matching_wrapped_keys():
            yield key

    def __len__(self) -> int:
        """Return the number of cached entries in this namespace."""
        return len(self._matching_wrapped_keys())

    def get(self, key: Any, default: Any = None) -> Any:
        """Return a cached value from this namespace when present."""
        return shared_process_hot_cache().get(self._wrap(key), default)

    def pop(self, key: Any, default: Any = _MISSING) -> Any:
        """Remove one key from this namespace using normal mapping semantics."""
        wrapped = self._wrap(key)
        cache = shared_process_hot_cache()
        if default is _MISSING:
            return cache.pop(wrapped)
        return cache.pop(wrapped, default)

    def clear(self) -> None:
        """Remove every cached entry in this namespace only."""
        cache = shared_process_hot_cache()
        for wrapped in self._matching_wrapped_keys():
            cache.pop(wrapped, None)


def shared_process_cache_view(namespace: str) -> NamespacedCacheView:
    """Return a namespace-scoped facade over the shared process cache."""
    return NamespacedCacheView(namespace=namespace)


@dataclass(slots=True)
class RuntimeReadSession:
    """Command-scoped cache and fingerprint container for related runtime reads."""

    repo_root: Path
    requested_scope: str = "reasoning"
    cache_policy: CacheBudgetPolicy = field(default_factory=runtime_cache_budget_policy)
    projection_fingerprint: str = ""
    sync_generation: int = 0
    _cache: ByteBudgetedSegmentedCache = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize inputs and provision the session-local cache."""
        self.repo_root = Path(self.repo_root).resolve()
        scope = str(self.requested_scope or "reasoning").strip().lower() or "reasoning"
        self.requested_scope = scope
        self._cache = ByteBudgetedSegmentedCache(
            name=f"runtime-read-session:{scope}",
            max_bytes=self.cache_policy.hot_path_budget_bytes,
        )

    def matches_repo(self, repo_root: Path) -> bool:
        """Report whether the session is anchored to the given repository root."""
        return Path(repo_root).resolve() == self.repo_root

    def get_or_compute(
        self,
        *,
        namespace: str,
        key: str,
        builder: Callable[[], _T],
    ) -> _T:
        """Return a session-local cached value or build and store it."""
        composite_key = (str(namespace).strip(), str(key).strip())
        cached = self._cache.get(composite_key, _MISSING)
        if cached is not _MISSING:
            return cached
        value = builder()
        self._cache[composite_key] = value
        return value

    def clear(self) -> None:
        """Discard all session-local cached values."""
        self._cache.clear()


def active_runtime_read_session() -> RuntimeReadSession | None:
    """Return the currently active runtime read session, if one is bound."""
    return _ACTIVE_RUNTIME_READ_SESSION.get()


@contextmanager
def activate_runtime_read_session(
    *,
    repo_root: Path,
    requested_scope: str = "reasoning",
) -> Iterator[RuntimeReadSession]:
    """Bind a fresh runtime read session for the duration of a context block."""
    session = RuntimeReadSession(
        repo_root=repo_root,
        requested_scope=requested_scope,
    )
    token: Token[RuntimeReadSession | None] = _ACTIVE_RUNTIME_READ_SESSION.set(session)
    try:
        yield session
    finally:
        if session.cache_policy.low_ram:
            session.clear()
        _ACTIVE_RUNTIME_READ_SESSION.reset(token)


__all__ = [
    "NamespacedCacheView",
    "RuntimeReadSession",
    "activate_runtime_read_session",
    "active_runtime_read_session",
    "runtime_cache_budget_policy",
    "shared_process_cache_view",
    "shared_process_hot_cache",
]
