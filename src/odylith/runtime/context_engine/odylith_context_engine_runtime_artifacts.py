"""Owned runtime-artifact paths and proof/state persistence for context engine slices."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_runtime_support
from odylith.runtime.context_engine import odylith_control_state
from odylith.runtime.memory import odylith_memory_backend
from odylith.runtime.memory import odylith_projection_snapshot

PID_FILENAME = "odylith-context-engine.pid"
STOP_FILENAME = "odylith-context-engine.stop"
SOCKET_FILENAME = "odylith-context-engine.sock"
DAEMON_METADATA_FILENAME = "odylith-context-engine-daemon.json"
DAEMON_USAGE_FILENAME = "odylith-context-engine-daemon-usage.v1.json"
PROOF_SURFACES_FILENAME = "odylith-proof-surfaces.v1.json"
SESSIONS_DIRNAME = "sessions"
BOOTSTRAPS_DIRNAME = "bootstraps"
JUDGMENT_MEMORY_FILENAME = "odylith-judgment-memory.v1.json"
_PROOF_SURFACES_CONTRACT = "odylith_proof_surfaces.v1"
_PROOF_SURFACES_VERSION = "v1"


def runtime_root(*, repo_root: Path) -> Path:
    """Return the repo-local runtime root that owns mutable context-engine state."""
    return odylith_control_state.runtime_root(repo_root=repo_root)


def projection_snapshot_path(*, repo_root: Path) -> Path:
    """Return the compiled projection snapshot path for one repo root."""
    return odylith_projection_snapshot.snapshot_path(repo_root=repo_root)


def state_path(*, repo_root: Path) -> Path:
    """Return the main runtime state JSON path."""
    return odylith_control_state.state_path(repo_root=repo_root)


def state_js_path(*, repo_root: Path) -> Path:
    """Return the JS mirror path for the runtime state payload."""
    return odylith_control_state.state_js_path(repo_root=repo_root)


def ensure_state_js_probe_asset(*, repo_root: Path) -> Path | None:
    """Materialize the state-JS probe asset when the dashboard needs it."""
    return odylith_control_state.ensure_state_js_probe_asset(repo_root=repo_root)


def events_path(*, repo_root: Path) -> Path:
    """Return the JSONL events ledger path."""
    return odylith_control_state.events_path(repo_root=repo_root)


def timings_path(*, repo_root: Path) -> Path:
    """Return the JSONL timings ledger path."""
    return odylith_control_state.timings_path(repo_root=repo_root)


def pid_path(*, repo_root: Path) -> Path:
    """Return the daemon PID file path."""
    return (runtime_root(repo_root=repo_root) / PID_FILENAME).resolve()


def daemon_metadata_path(*, repo_root: Path) -> Path:
    """Return the workspace-daemon metadata path."""
    return (runtime_root(repo_root=repo_root) / DAEMON_METADATA_FILENAME).resolve()


def stop_path(*, repo_root: Path) -> Path:
    """Return the daemon stop-signal file path."""
    return (runtime_root(repo_root=repo_root) / STOP_FILENAME).resolve()


def socket_path(*, repo_root: Path) -> Path:
    """Return the daemon transport path, shortening long unix-socket paths."""
    preferred = (runtime_root(repo_root=repo_root) / SOCKET_FILENAME).resolve()
    if len(str(preferred)) < 100:
        return preferred
    token = odylith_context_cache.fingerprint_payload(str(Path(repo_root).resolve()))[:16]
    return (Path(tempfile.gettempdir()) / f"odylith-tooling-{token}.sock").resolve()


def daemon_usage_path(*, repo_root: Path) -> Path:
    """Return the workspace-daemon usage ledger path."""
    return (runtime_root(repo_root=repo_root) / DAEMON_USAGE_FILENAME).resolve()


def proof_surfaces_path(*, repo_root: Path) -> Path:
    """Return the runtime proof-surfaces JSON path."""
    return (runtime_root(repo_root=repo_root) / PROOF_SURFACES_FILENAME).resolve()


def sessions_root(*, repo_root: Path) -> Path:
    """Return the runtime session-packet directory."""
    return (runtime_root(repo_root=repo_root) / SESSIONS_DIRNAME).resolve()


def bootstraps_root(*, repo_root: Path) -> Path:
    """Return the runtime bootstrap-packet directory."""
    return (runtime_root(repo_root=repo_root) / BOOTSTRAPS_DIRNAME).resolve()


def judgment_memory_path(*, repo_root: Path) -> Path:
    """Return the local judgment-memory snapshot path."""
    return (odylith_memory_backend.local_backend_root(repo_root=repo_root) / JUDGMENT_MEMORY_FILENAME).resolve()


def read_runtime_state(*, repo_root: Path) -> dict[str, Any]:
    """Read the main runtime state payload."""
    return odylith_control_state.read_state(repo_root=repo_root)


def write_runtime_state(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    """Persist the main runtime state payload."""
    odylith_control_state.write_state(repo_root=repo_root, payload=payload)


def append_runtime_event(*, repo_root: Path, event_type: str, payload: Mapping[str, Any]) -> None:
    """Append one structured runtime event with the canonical schema version."""
    odylith_control_state.append_event(
        repo_root=repo_root,
        event_type=str(event_type).strip() or "projection_update",
        payload=dict(payload),
        version=odylith_context_engine_runtime_support.SCHEMA_VERSION,
        ts_iso=odylith_context_engine_runtime_support.utc_now(),
    )


def load_runtime_proof_surfaces(*, repo_root: Path) -> dict[str, Any]:
    """Load the runtime proof-surfaces document when present."""
    payload = odylith_context_cache.read_json_object(proof_surfaces_path(repo_root=repo_root))
    return dict(payload) if isinstance(payload, Mapping) else {}


def runtime_proof_section(*, repo_root: Path, section: str) -> dict[str, Any]:
    """Return one proof-surfaces section as a shallow mutable mapping."""
    payload = load_runtime_proof_surfaces(repo_root=repo_root)
    value = payload.get(section)
    return dict(value) if isinstance(value, Mapping) else {}


def persist_runtime_proof_section(
    *,
    repo_root: Path,
    section: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist one proof-surfaces section while preserving the rest of the document."""
    root = Path(repo_root).resolve()
    existing = load_runtime_proof_surfaces(repo_root=root)
    document = {
        "contract": _PROOF_SURFACES_CONTRACT,
        "version": _PROOF_SURFACES_VERSION,
        "updated_utc": odylith_context_engine_runtime_support.utc_now(),
    }
    for key, value in existing.items():
        if key in {"contract", "version", "updated_utc"}:
            continue
        if isinstance(value, Mapping):
            document[key] = dict(value)
    section_payload = dict(payload)
    section_payload.setdefault("recorded_utc", odylith_context_engine_runtime_support.utc_now())
    document[section] = section_payload
    target = proof_surfaces_path(repo_root=root)
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=target,
        payload=document,
        lock_key=str(target),
    )
    return section_payload


__all__ = [
    "BOOTSTRAPS_DIRNAME",
    "DAEMON_METADATA_FILENAME",
    "DAEMON_USAGE_FILENAME",
    "JUDGMENT_MEMORY_FILENAME",
    "PID_FILENAME",
    "PROOF_SURFACES_FILENAME",
    "SESSIONS_DIRNAME",
    "SOCKET_FILENAME",
    "STOP_FILENAME",
    "append_runtime_event",
    "bootstraps_root",
    "daemon_metadata_path",
    "daemon_usage_path",
    "ensure_state_js_probe_asset",
    "events_path",
    "judgment_memory_path",
    "load_runtime_proof_surfaces",
    "persist_runtime_proof_section",
    "pid_path",
    "projection_snapshot_path",
    "proof_surfaces_path",
    "read_runtime_state",
    "runtime_proof_section",
    "runtime_root",
    "sessions_root",
    "socket_path",
    "state_js_path",
    "state_path",
    "stop_path",
    "timings_path",
    "write_runtime_state",
]
