"""Shared derivation provenance helpers for governed sync and runtime reuse."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence


PROVENANCE_VERSION = "v1"
SURFACE_RUNTIME_CONTRACT_VERSION = "v1"


def _normalize_scope(value: str) -> str:
    return str(value or "default").strip().lower() or "default"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


@lru_cache(maxsize=128)
def _fingerprint_source_files_cached(paths: tuple[str, ...]) -> str:
    rows: list[dict[str, str]] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            rows.append({"path": str(path), "sha256": "missing"})
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            digest = "unreadable"
        rows.append({"path": str(path.resolve()), "sha256": digest})
    rendered = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def fingerprint_source_files(paths: Sequence[Path | str]) -> str:
    normalized = tuple(
        sorted(
            str(Path(path).resolve())
            for path in paths
            if str(path).strip()
        )
    )
    return _fingerprint_source_files_cached(normalized)


def active_sync_generation(*, repo_root: Path) -> tuple[int, bool, str]:
    from odylith.runtime.governance import sync_session

    session = sync_session.active_sync_session()
    root = Path(repo_root).resolve()
    if session is None or session.repo_root != root:
        return (0, False, "")
    return (int(session.generation), True, str(session.last_invalidation_step).strip())


def build_derivation_provenance(
    *,
    repo_root: Path,
    projection_scope: str,
    projection_fingerprint: str,
    sync_generation: int,
    code_version: str,
    flags: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    return {
        "version": PROVENANCE_VERSION,
        "repo_root": str(root),
        "projection_scope": _normalize_scope(projection_scope),
        "projection_fingerprint": str(projection_fingerprint).strip(),
        "sync_generation": int(sync_generation),
        "code_version": str(code_version).strip(),
        "flags": _json_safe(flags or {}),
    }


def extract_provenance(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    provenance = payload.get("provenance")
    return dict(provenance) if isinstance(provenance, Mapping) else {}


def provenance_matches(
    *,
    actual: Mapping[str, Any] | None,
    expected: Mapping[str, Any],
    require_generation: bool,
) -> bool:
    actual_map = dict(actual) if isinstance(actual, Mapping) else {}
    expected_map = dict(expected)
    required_fields = (
        "version",
        "repo_root",
        "projection_scope",
        "projection_fingerprint",
        "code_version",
    )
    for field_name in required_fields:
        if str(actual_map.get(field_name, "")).strip() != str(expected_map.get(field_name, "")).strip():
            return False
    actual_flags = _json_safe(actual_map.get("flags", {}))
    expected_flags = _json_safe(expected_map.get("flags", {}))
    if actual_flags != expected_flags:
        return False
    if require_generation and int(actual_map.get("sync_generation", -1) or -1) != int(
        expected_map.get("sync_generation", -2) or -2
    ):
        return False
    return True


def build_surface_runtime_contract(
    *,
    repo_root: Path,
    surface: str,
    runtime_mode: str,
    built_from: str,
    cache_hit: bool,
    output_path: Path | None = None,
    invalidated_by_step: str = "",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from odylith.runtime.memory import odylith_memory_backend
    from odylith.runtime.memory import odylith_projection_bundle
    from odylith.runtime.memory import odylith_projection_snapshot

    root = Path(repo_root).resolve()
    bundle_manifest = odylith_projection_bundle.load_bundle_manifest(repo_root=root)
    snapshot_manifest = odylith_projection_snapshot.load_snapshot(repo_root=root)
    backend_manifest = odylith_memory_backend.load_manifest(repo_root=root)
    compiler_manifest = bundle_manifest if bundle_manifest else snapshot_manifest
    compiler_provenance = extract_provenance(compiler_manifest)
    generation, generation_required, session_invalidated_by_step = active_sync_generation(repo_root=root)
    effective_invalidated_by_step = (
        str(invalidated_by_step).strip() or str(session_invalidated_by_step).strip()
    )
    contract = {
        "surface_contract_version": SURFACE_RUNTIME_CONTRACT_VERSION,
        "surface": str(surface).strip().lower(),
        "runtime_mode": str(runtime_mode).strip().lower() or "auto",
        "projection_fingerprint": str(
            compiler_manifest.get("projection_fingerprint", "")
            or compiler_provenance.get("projection_fingerprint", "")
        ).strip(),
        "projection_scope": str(
            compiler_manifest.get("projection_scope", "")
            or compiler_provenance.get("projection_scope", "")
        ).strip(),
        "generation": int(generation if generation_required else compiler_provenance.get("sync_generation", 0) or 0),
        "cache_hit": bool(cache_hit),
        "built_from": str(built_from).strip(),
        "invalidated_by_step": effective_invalidated_by_step,
        "compiler_ready": bool(compiler_manifest.get("ready")),
        "backend_ready": bool(backend_manifest.get("ready")),
        "compiler_source": str(compiler_manifest.get("source", "")).strip(),
        "backend_status": str(backend_manifest.get("status", "")).strip(),
        "projection_provenance": compiler_provenance,
        "backend_provenance": extract_provenance(backend_manifest),
    }
    if output_path is not None:
        contract["output_path"] = str(Path(output_path).resolve())
    if extra:
        contract.update({str(key): _json_safe(value) for key, value in extra.items()})
    return contract


__all__ = [
    "PROVENANCE_VERSION",
    "SURFACE_RUNTIME_CONTRACT_VERSION",
    "active_sync_generation",
    "build_derivation_provenance",
    "build_surface_runtime_contract",
    "extract_provenance",
    "fingerprint_source_files",
    "provenance_matches",
]
