"""Sync Runtime Contract helpers for the Odylith execution engine layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance import sync_session as governed_sync_session

_CODE_FILES: tuple[str, ...] = (
    "src/odylith/runtime/execution_engine/contract.py",
    "src/odylith/runtime/execution_engine/policy.py",
    "src/odylith/runtime/execution_engine/runtime_surface_governance.py",
    "src/odylith/runtime/execution_engine/sync_runtime_contract.py",
)


def _repo_root(payload: Mapping[str, Any] | None = None) -> Path | None:
    session = governed_sync_session.active_sync_session()
    if session is not None:
        return Path(session.repo_root)
    if isinstance(payload, Mapping):
        for key in ("repo_root",):
            candidate = str(payload.get(key, "")).strip()
            if candidate:
                return Path(candidate).resolve()
    return None


def build_execution_engine_runtime_contract(
    *,
    payload: Mapping[str, Any] | None = None,
    snapshot: Mapping[str, Any],
    built_from: str,
) -> dict[str, Any]:
    session = governed_sync_session.active_sync_session()
    repo_root = _repo_root(payload)
    input_fingerprint = odylith_context_cache.fingerprint_payload(dict(snapshot))
    contract = {
        "version": "v1",
        "built_from": str(built_from or "").strip() or "runtime_packet",
        "input_fingerprint": input_fingerprint,
        "sync_generation": int(session.generation if session is not None else 0),
        "reuse_scope": "sync_scoped" if session is not None else "standalone",
        "settled_sync_session": bool(session is not None),
        "invalidated_by_step": str(session.last_invalidation_step).strip() if session is not None else "",
    }
    if repo_root is None:
        return contract
    projection_fingerprint = input_fingerprint
    code_version = derivation_provenance.fingerprint_source_files(repo_root / path for path in _CODE_FILES)
    contract["repo_root"] = str(repo_root)
    contract["provenance"] = derivation_provenance.build_derivation_provenance(
        repo_root=repo_root,
        projection_scope="execution_engine",
        projection_fingerprint=projection_fingerprint,
        sync_generation=int(session.generation if session is not None else 0),
        code_version=code_version,
        flags={
            "built_from": contract["built_from"],
            "reuse_scope": contract["reuse_scope"],
        },
    )
    return contract
