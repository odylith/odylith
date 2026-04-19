"""Benchmark Snapshot Fallbacks helpers for the Odylith evaluation layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from odylith.common.json_objects import load_json_object_or_none

_TRACKED_LATEST_SUMMARY_PATH = Path("docs/benchmarks/latest-summary.v1.json")
_RELEASE_BASELINES_PATH = Path("docs/benchmarks/release-baselines.v1.json")


def _load_json(path: Path) -> dict[str, Any] | None:
    return load_json_object_or_none(path)


def load_tracked_latest_summary(*, repo_root: Path) -> dict[str, Any] | None:
    path = (Path(repo_root).resolve() / _TRACKED_LATEST_SUMMARY_PATH).resolve()
    payload = _load_json(path)
    if not payload:
        return None
    return payload


def load_release_baseline_summary(*, repo_root: Path, version: str) -> dict[str, Any] | None:
    path = (Path(repo_root).resolve() / _RELEASE_BASELINES_PATH).resolve()
    payload = _load_json(path)
    if not payload:
        return None
    version_payload = payload.get(str(version).strip())
    if not isinstance(version_payload, Mapping):
        return None
    return dict(version_payload)
