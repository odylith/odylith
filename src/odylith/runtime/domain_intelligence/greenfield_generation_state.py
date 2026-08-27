"""Authoritative active-generation state for Greenfield publication."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary
from odylith.runtime.domain_intelligence.greenfield_create_contract import is_sha256_digest


ACTIVE_GENERATION_STATE_VERSION = "odylith.greenfield.active-generation.v1"
ACTIVE = "active"
SUPERSEDED = "superseded"
NONE = "none"
_ACTIVE_STATE_TOKEN = ".odylith/runtime/greenfield/active-generation.v1.json"


def active_generation_state_path(repo_root: Path) -> Path:
    return Path(repo_root).expanduser().resolve() / _ACTIVE_STATE_TOKEN


def no_active_generation_identity() -> dict[str, str]:
    return {
        "status": NONE,
        "transaction_hash": "",
        "write_set_hash": "",
        "generation_manifest_sha256": "",
    }


def active_generation_identity(repo_root: Path) -> dict[str, str]:
    state = read_active_generation_state(repo_root)
    return _state_identity(state) if state is not None else no_active_generation_identity()


def active_generation_is(
    *,
    repo_root: Path,
    transaction_hash: str,
    write_set_hash: str = "",
    generation_manifest_sha256: str = "",
) -> bool:
    state = read_active_generation_state(repo_root)
    if state is None or str(state.get("status") or "") != ACTIVE:
        return False
    if str(state.get("transaction_hash") or "") != str(transaction_hash or "").strip():
        return False
    if write_set_hash and str(state.get("write_set_hash") or "") != str(write_set_hash).strip():
        return False
    if generation_manifest_sha256 and str(state.get("generation_manifest_sha256") or "") != str(
        generation_manifest_sha256
    ).strip():
        return False
    return True


def read_active_generation_state(repo_root: Path) -> dict[str, Any] | None:
    root = Path(repo_root).expanduser().resolve()
    if greenfield_transaction_path_boundary.path_kind(root, _ACTIVE_STATE_TOKEN) == "missing":
        return None
    if greenfield_transaction_path_boundary.path_kind(root, _ACTIVE_STATE_TOKEN) != "file":
        raise RuntimeError("Greenfield active-generation state is missing or unsafe")
    try:
        raw = greenfield_transaction_path_boundary.read_bytes(root, _ACTIVE_STATE_TOKEN)
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Greenfield active-generation state is unreadable") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError("Greenfield active-generation state must be an object")
    state = dict(payload)
    if raw != _canonical_state_bytes(state):
        raise RuntimeError("Greenfield active-generation state bytes are not canonical")
    _require_state(state)
    return state


def publish_active_generation_state(
    *,
    repo_root: Path,
    expected_identity: Mapping[str, Any],
    transaction_hash: str,
    write_set_hash: str,
    generation_manifest_sha256: str,
) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    expected = require_active_generation_identity(expected_identity)
    actual = active_generation_identity(root)
    if actual != expected:
        raise ValueError("Greenfield active generation changed after pre-confirm compilation")
    transaction = _require_digest(transaction_hash, label="transaction hash")
    write_set = _require_digest(write_set_hash, label="write-set hash")
    manifest = _require_digest(generation_manifest_sha256, label="generation manifest hash")
    state = {
        "version": ACTIVE_GENERATION_STATE_VERSION,
        "status": ACTIVE,
        "transaction_hash": transaction,
        "write_set_hash": write_set,
        "generation_manifest_sha256": manifest,
        "generation_path": f".odylith/runtime/greenfield/generations/{transaction}",
    }
    state["record_hash"] = _record_hash(state)
    greenfield_transaction_path_boundary.atomic_write_bytes(
        root,
        _ACTIVE_STATE_TOKEN,
        _canonical_state_bytes(state),
    )
    return state


def supersede_active_generation(*, repo_root: Path, expected_transaction_hash: str) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    state = read_active_generation_state(root)
    if state is None:
        return no_active_generation_identity()
    expected = _require_digest(expected_transaction_hash, label="transaction hash")
    if str(state["transaction_hash"]) != expected:
        raise ValueError("Greenfield active generation changed before supersession")
    if str(state["status"]) == SUPERSEDED:
        return state
    updated = {**state, "status": SUPERSEDED}
    updated.pop("record_hash", None)
    updated["record_hash"] = _record_hash(updated)
    greenfield_transaction_path_boundary.atomic_write_bytes(
        root,
        _ACTIVE_STATE_TOKEN,
        _canonical_state_bytes(updated),
    )
    return updated


def require_active_generation_identity(value: Mapping[str, Any] | object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("ProductCreateTransaction active-generation precondition is missing")
    identity = {
        "status": str(value.get("status") or "").strip(),
        "transaction_hash": str(value.get("transaction_hash") or "").strip(),
        "write_set_hash": str(value.get("write_set_hash") or "").strip(),
        "generation_manifest_sha256": str(value.get("generation_manifest_sha256") or "").strip(),
    }
    if identity["status"] == NONE:
        if identity != no_active_generation_identity():
            raise ValueError("ProductCreateTransaction empty active-generation precondition is invalid")
        return identity
    if identity["status"] not in {ACTIVE, SUPERSEDED}:
        raise ValueError("ProductCreateTransaction active-generation precondition has an invalid status")
    for key in ("transaction_hash", "write_set_hash", "generation_manifest_sha256"):
        _require_digest(identity[key], label=key.replace("_", " "))
    return identity


def _state_identity(state: Mapping[str, Any]) -> dict[str, str]:
    return require_active_generation_identity(state)


def _require_state(state: Mapping[str, Any]) -> None:
    if str(state.get("version") or "") != ACTIVE_GENERATION_STATE_VERSION:
        raise RuntimeError("Greenfield active-generation state version is unsupported")
    require_active_generation_identity(state)
    transaction = str(state.get("transaction_hash") or "")
    if str(state.get("generation_path") or "") != (
        f".odylith/runtime/greenfield/generations/{transaction}"
    ):
        raise RuntimeError("Greenfield active-generation path is invalid")
    digest = str(state.get("record_hash") or "")
    unsigned = {key: value for key, value in state.items() if key != "record_hash"}
    if digest != _record_hash(unsigned):
        raise RuntimeError("Greenfield active-generation state hash mismatch")


def _canonical_state_bytes(state: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(state), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _record_hash(state: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in state.items() if key != "record_hash"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_digest(value: Any, *, label: str) -> str:
    token = str(value or "").strip()
    if not is_sha256_digest(token):
        raise ValueError(f"Greenfield {label} must be a SHA-256 value")
    return token


__all__ = [
    "ACTIVE",
    "ACTIVE_GENERATION_STATE_VERSION",
    "NONE",
    "SUPERSEDED",
    "active_generation_identity",
    "active_generation_is",
    "active_generation_state_path",
    "no_active_generation_identity",
    "publish_active_generation_state",
    "read_active_generation_state",
    "require_active_generation_identity",
    "supersede_active_generation",
]
