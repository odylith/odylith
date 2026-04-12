"""Sync-scoped shared read-model state for in-process governed sync.

The sync runner already has a runtime fast path where multiple governance and
surface commands execute inside one Python process. This module gives that path
one explicit session object so hot helpers can reuse the same repo-scoped facts
instead of repeatedly rediscovering them.
"""

from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, TypeVar


_T = TypeVar("_T")
_ACTIVE_SYNC_SESSION: ContextVar["GovernedSyncSession | None"] = ContextVar(
    "_ACTIVE_SYNC_SESSION",
    default=None,
)


@dataclass(slots=True)
class GovernedSyncSession:
    """Process-local shared read model for one sync execution."""

    repo_root: Path
    debug_cache: bool = False
    _cache: dict[tuple[str, str], Any] = field(default_factory=dict)
    generation: int = 0
    started_utc: str = field(default_factory=lambda: _utc_now())
    last_invalidation_step: str = ""
    invalidation_events: list[dict[str, Any]] = field(default_factory=list)
    cache_decisions: list[dict[str, Any]] = field(default_factory=list)
    surface_decisions: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).resolve()
        self._persist_debug_manifest()

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

    def bump_generation(
        self,
        *,
        step_label: str,
        mutation_classes: Iterable[str],
        invalidated_namespaces: Iterable[str],
        paths: Iterable[str],
    ) -> int:
        self.generation += 1
        self.last_invalidation_step = str(step_label).strip()
        self._append_debug_row(
            bucket=self.invalidation_events,
            row={
                "generation": int(self.generation),
                "step": self.last_invalidation_step,
                "mutation_classes": [
                    str(token).strip()
                    for token in mutation_classes
                    if str(token).strip()
                ],
                "invalidated_namespaces": [
                    str(token).strip()
                    for token in invalidated_namespaces
                    if str(token).strip()
                ],
                "paths": [str(token).strip() for token in paths if str(token).strip()],
                "recorded_utc": _utc_now(),
            },
        )
        self._emit_debug(
            f"- cache: generation={self.generation} invalidated_by={self.last_invalidation_step or 'unknown'}"
        )
        return self.generation

    def record_cache_decision(
        self,
        *,
        category: str,
        cache_hit: bool,
        built_from: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        row = {
            "generation": int(self.generation),
            "category": str(category).strip(),
            "cache_hit": bool(cache_hit),
            "built_from": str(built_from).strip(),
            "details": dict(details) if isinstance(details, Mapping) else {},
            "recorded_utc": _utc_now(),
        }
        self._append_debug_row(bucket=self.cache_decisions, row=row)
        self._emit_debug(
            f"- cache: {row['category']} {'hit' if cache_hit else 'miss'} built_from={row['built_from'] or 'unknown'}"
        )

    def record_surface_decision(
        self,
        *,
        surface: str,
        cache_hit: bool,
        built_from: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        row = {
            "generation": int(self.generation),
            "surface": str(surface).strip().lower(),
            "cache_hit": bool(cache_hit),
            "built_from": str(built_from).strip(),
            "invalidated_by_step": self.last_invalidation_step,
            "details": dict(details) if isinstance(details, Mapping) else {},
            "recorded_utc": _utc_now(),
        }
        self._append_debug_row(bucket=self.surface_decisions, row=row)
        self._emit_debug(
            f"- cache: surface={row['surface']} {'reused' if cache_hit else 'rebuilt'} via={row['built_from'] or 'unknown'}"
        )

    def repo_root_for_path(self, path: Path) -> Path | None:
        candidate = Path(path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError:
            return None
        return self.repo_root

    def _append_debug_row(self, *, bucket: list[dict[str, Any]], row: dict[str, Any]) -> None:
        bucket.append(row)
        if len(bucket) > 128:
            del bucket[:-128]
        self._persist_debug_manifest()

    def _persist_debug_manifest(self) -> None:
        from odylith.runtime.context_engine import odylith_context_cache

        target = odylith_context_cache.cache_path(
            repo_root=self.repo_root,
            namespace="debug",
            key="governed-sync-session",
        )
        payload = {
            "version": "v1",
            "repo_root": self.repo_root_token,
            "started_utc": self.started_utc,
            "generation": int(self.generation),
            "last_invalidation_step": self.last_invalidation_step,
            "invalidation_events": list(self.invalidation_events),
            "cache_decisions": list(self.cache_decisions),
            "surface_decisions": list(self.surface_decisions),
        }
        odylith_context_cache.write_json_if_changed(
            repo_root=self.repo_root,
            path=target,
            payload=payload,
        )

    def _emit_debug(self, message: str) -> None:
        if self.debug_cache:
            print(str(message).strip())


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
