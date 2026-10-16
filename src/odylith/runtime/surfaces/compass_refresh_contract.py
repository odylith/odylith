"""Compass Refresh Contract helpers for the Odylith surfaces layer."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

DEFAULT_REFRESH_PROFILE = "shell-safe"
DEFAULT_SCOPED_PROVIDER_MAX_WORKERS = 4

_TRANSIENT_ROOTS: Counter[Path] = Counter()
_TRANSIENT_ROOTS_LOCK = Lock()


@contextmanager
def transient_refresh_root(*, repo_root: Path) -> Iterator[None]:
    """Render a compiler-owned root without giving it detached job ownership.

    Surface refresh runs across threads, so this lifetime is shared by exact
    repository identity rather than by thread context or a process-wide switch.
    """

    root = Path(repo_root).resolve()
    with _TRANSIENT_ROOTS_LOCK:
        _TRANSIENT_ROOTS[root] += 1
    try:
        yield
    finally:
        with _TRANSIENT_ROOTS_LOCK:
            _TRANSIENT_ROOTS[root] -= 1
            if not _TRANSIENT_ROOTS[root]:
                del _TRANSIENT_ROOTS[root]


def background_maintenance_allowed(*, repo_root: Path) -> bool:
    """Only durable refresh roots may own asynchronous narration work."""

    root = Path(repo_root).resolve()
    with _TRANSIENT_ROOTS_LOCK:
        return root not in _TRANSIENT_ROOTS


def normalize_refresh_profile(value: str, *, default: str = DEFAULT_REFRESH_PROFILE) -> str:
    del value
    fallback = str(default).strip().lower()
    return DEFAULT_REFRESH_PROFILE if fallback != DEFAULT_REFRESH_PROFILE else fallback


def allow_global_provider(refresh_profile: str) -> bool:
    del refresh_profile
    return False


def prefer_live_provider(refresh_profile: str) -> bool:
    del refresh_profile
    return False


def scoped_provider_max_workers(refresh_profile: str, *, scoped_packets: int) -> int:
    del refresh_profile
    return max(1, min(int(DEFAULT_SCOPED_PROVIDER_MAX_WORKERS), int(scoped_packets)))
