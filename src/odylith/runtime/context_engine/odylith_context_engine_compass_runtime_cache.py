"""In-process Compass runtime payload cache for daemon-backed hot reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import threading
from typing import Any, Mapping


@dataclass
class _CompassRuntimeCacheEntry:
    condition: threading.Condition = field(default_factory=threading.Condition)
    input_fingerprint: str = ""
    refresh_profile: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, _CompassRuntimeCacheEntry] = {}


def _entry(repo_root: Path) -> _CompassRuntimeCacheEntry:
    key = str(Path(repo_root).resolve())
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            entry = _CompassRuntimeCacheEntry()
            _CACHE[key] = entry
        return entry


def load_runtime_payload(
    *,
    repo_root: Path,
    input_fingerprint: str,
    refresh_profile: str,
) -> dict[str, Any] | None:
    entry = _entry(repo_root)
    requested_fingerprint = str(input_fingerprint or "").strip()
    requested_profile = str(refresh_profile or "").strip().lower()
    with entry.condition:
        if not requested_fingerprint or entry.input_fingerprint != requested_fingerprint:
            return None
        if requested_profile and entry.refresh_profile != requested_profile:
            return None
        if not isinstance(entry.payload, dict) or not entry.payload:
            return None
        return json.loads(json.dumps(entry.payload))


def record_runtime_payload(
    *,
    repo_root: Path,
    input_fingerprint: str,
    refresh_profile: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    entry = _entry(repo_root)
    with entry.condition:
        entry.input_fingerprint = str(input_fingerprint or "").strip()
        entry.refresh_profile = str(refresh_profile or "").strip().lower()
        entry.payload = json.loads(json.dumps(dict(payload)))
        entry.condition.notify_all()
        return {
            "recorded": True,
            "input_fingerprint": entry.input_fingerprint,
            "refresh_profile": entry.refresh_profile,
        }


__all__ = [
    "load_runtime_payload",
    "record_runtime_payload",
]
