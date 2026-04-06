"""Compiler-owned projection snapshot for the Odylith Context Engine.

This snapshot is the structured local read model for Odylith. It stores the
full local projection tables as JSON so runtime readers can consume one
deterministic compiler output without requiring a relational store.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.context_engine import odylith_context_cache

SNAPSHOT_VERSION = "v1"
SNAPSHOT_FILENAME = "projection-snapshot.v1.json"


def runtime_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime").resolve()


def compiler_root(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / "odylith-compiler").resolve()


def snapshot_path(*, repo_root: Path) -> Path:
    return (compiler_root(repo_root=repo_root) / SNAPSHOT_FILENAME).resolve()


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_snapshot(
    *,
    repo_root: Path,
    projection_fingerprint: str,
    projection_scope: str,
    input_fingerprint: str,
    tables: Mapping[str, Any],
    projection_state: Mapping[str, Any],
    updated_projections: list[str],
    source: str = "projection_compile",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    compiler = compiler_root(repo_root=root)
    compiler.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SNAPSHOT_VERSION,
        "compiled_utc": _utc_now(),
        "ready": True,
        "source": str(source).strip() or "projection_compile",
        "projection_fingerprint": str(projection_fingerprint).strip(),
        "projection_scope": str(projection_scope).strip().lower() or "default",
        "input_fingerprint": str(input_fingerprint).strip(),
        "updated_projections": [str(token).strip() for token in updated_projections if str(token).strip()],
        "tables": dict(tables),
        "projection_state": dict(projection_state),
    }
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=snapshot_path(repo_root=root),
        payload=payload,
        lock_key=str(snapshot_path(repo_root=root)),
    )
    return payload


def load_snapshot(*, repo_root: Path) -> dict[str, Any]:
    return odylith_context_cache.read_json_object(snapshot_path(repo_root=repo_root))


__all__ = [
    "SNAPSHOT_FILENAME",
    "SNAPSHOT_VERSION",
    "compiler_root",
    "load_snapshot",
    "runtime_root",
    "snapshot_path",
    "write_snapshot",
]
