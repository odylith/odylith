"""Owned workspace-daemon request routing and usage accounting for context engine slices."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import socket
import time
from typing import Any, Callable, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_runtime_artifacts
from odylith.runtime.context_engine import odylith_context_engine_runtime_support
from odylith.runtime.governance import agent_governance_intelligence as governance


def workspace_daemon_key(*, repo_root: Path) -> str:
    """Return the stable workspace key used to group daemon reuse and usage."""
    return odylith_context_cache.fingerprint_payload(str(Path(repo_root).resolve()))[:16]


def runtime_request_namespace(
    *,
    repo_root: Path,
    command: str = "",
    changed_paths: Sequence[str] = (),
    session_id: str = "",
    claimed_paths: Sequence[str] = (),
    working_tree_scope: str = "repo",
) -> dict[str, Any]:
    """Return the stable namespace metadata for one workspace-daemon request."""
    root = Path(repo_root).resolve()
    scope_token = str(working_tree_scope or "repo").strip().lower() or "repo"
    normalized_changed = governance.normalize_changed_paths(repo_root=root, values=changed_paths)
    normalized_claimed = governance.normalize_changed_paths(repo_root=root, values=claimed_paths)
    normalized_session = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "").strip()).strip("-")
    namespace_payload = {
        "command": str(command or "").strip().lower(),
        "working_tree_scope": scope_token,
        "session_id": normalized_session,
        "changed_paths": normalized_changed,
        "claimed_paths": normalized_claimed,
    }
    request_namespace = odylith_context_cache.fingerprint_payload(namespace_payload)[:16]
    session_namespaced = bool(normalized_session or normalized_claimed or scope_token == "session")
    return {
        "workspace_key": workspace_daemon_key(repo_root=root),
        "request_namespace": request_namespace,
        "session_namespaced": session_namespaced,
        "session_namespace": request_namespace if session_namespaced else "",
        "working_tree_scope": scope_token,
        "session_id_present": bool(normalized_session),
        "claim_path_count": len(normalized_claimed),
        "changed_path_count": len(normalized_changed),
    }


def runtime_request_namespace_from_payload(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive request namespace metadata from one workspace-daemon payload."""
    return runtime_request_namespace(
        repo_root=repo_root,
        command=command,
        changed_paths=payload.get("paths", []) if isinstance(payload.get("paths"), list) else (),
        session_id=str(payload.get("session_id", "")).strip(),
        claimed_paths=payload.get("claim_paths", []) if isinstance(payload.get("claim_paths"), list) else (),
        working_tree_scope=str(payload.get("working_tree_scope", "repo")).strip() or "repo",
    )


def runtime_daemon_pid(*, repo_root: Path) -> int:
    """Return the active daemon PID from the pidfile when available."""
    path = odylith_context_engine_runtime_artifacts.pid_path(repo_root=repo_root)
    if not path.is_file():
        return 0
    try:
        return max(0, int(path.read_text(encoding="utf-8").strip() or 0))
    except (OSError, ValueError):
        return 0


def read_runtime_daemon_metadata(*, repo_root: Path) -> dict[str, Any]:
    """Load the workspace-daemon metadata payload."""
    path = odylith_context_engine_runtime_artifacts.daemon_metadata_path(repo_root=repo_root)
    payload = odylith_context_cache.read_json_object(path)
    if not payload:
        return {}
    try:
        pid = max(0, int(payload.get("pid", 0) or 0))
    except (TypeError, ValueError):
        pid = 0
    return {
        "pid": pid,
        "auth_token": str(payload.get("auth_token", "")).strip(),
        "spawn_reason": str(payload.get("spawn_reason", "")).strip(),
        "started_utc": str(payload.get("started_utc", "")).strip(),
    }


def runtime_daemon_pid_alive(pid: int) -> bool:
    """Return whether a daemon PID still exists on the local host."""
    if int(pid or 0) <= 0:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def runtime_daemon_owner_pid(*, repo_root: Path) -> int:
    """Return the best available daemon owner PID from pidfile or metadata."""
    pid = runtime_daemon_pid(repo_root=repo_root)
    if pid > 0:
        return pid
    metadata_pid = int(read_runtime_daemon_metadata(repo_root=repo_root).get("pid", 0) or 0)
    return metadata_pid if metadata_pid > 0 else 0


def normalize_loopback_host(value: Any) -> str:
    """Normalize loopback-only daemon hosts and reject non-loopback values."""
    token = str(value or "").strip().lower()
    if not token:
        return "127.0.0.1"
    if token in {"127.0.0.1", "localhost", "::1"}:
        return token
    return ""


def runtime_daemon_transport(*, repo_root: Path) -> dict[str, Any] | None:
    """Return the live daemon transport payload when the owner PID is healthy."""
    root = Path(repo_root).resolve()
    owner_pid = runtime_daemon_owner_pid(repo_root=root)
    if not runtime_daemon_pid_alive(owner_pid):
        return None
    runtime_socket = odylith_context_engine_runtime_artifacts.socket_path(repo_root=root)
    try:
        if runtime_socket.is_socket():
            return {
                "transport": "unix",
                "path": str(runtime_socket),
                "pid": owner_pid,
            }
    except OSError:
        return None
    payload = odylith_context_cache.read_json_object(runtime_socket)
    if not payload:
        return None
    transport = str(payload.get("transport", "")).strip().lower()
    if transport != "tcp":
        return None
    host = normalize_loopback_host(payload.get("host", ""))
    if not host:
        return None
    try:
        port = int(payload.get("port", 0) or 0)
    except (TypeError, ValueError):
        return None
    try:
        transport_pid = int(payload.get("pid", 0) or 0)
    except (TypeError, ValueError):
        transport_pid = 0
    if port <= 0:
        return None
    if transport_pid > 0 and transport_pid != owner_pid:
        return None
    return {
        "transport": "tcp",
        "host": host,
        "port": port,
        "pid": owner_pid,
    }


def request_runtime_daemon(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any] | None = None,
    required: bool = False,
    timeout_seconds: float = 5.0,
    transport_reader: Callable[..., dict[str, Any] | None] | None = None,
    metadata_reader: Callable[..., dict[str, Any]] | None = None,
    namespace_builder: Callable[..., dict[str, Any]] | None = None,
    timing_recorder: Callable[..., None] | None = None,
    socket_factory: Callable[..., socket.socket] | None = None,
    socket_path_resolver: Callable[..., Path] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Send one request to the workspace daemon and return payload plus execution metadata."""
    root = Path(repo_root).resolve()
    daemon_metadata_loader = metadata_reader or read_runtime_daemon_metadata
    transport_loader = transport_reader or runtime_daemon_transport
    request_namespace_builder = namespace_builder or runtime_request_namespace_from_payload
    runtime_timing_recorder = timing_recorder or odylith_context_engine_runtime_support.record_runtime_timing
    open_socket = socket_factory or socket.socket
    resolve_socket_path = socket_path_resolver or odylith_context_engine_runtime_artifacts.socket_path
    daemon_metadata = daemon_metadata_loader(repo_root=root)
    transport = transport_loader(repo_root=root)
    if transport is None:
        if required:
            raise RuntimeError("odylith context engine daemon unavailable")
        return None
    started_at = time.perf_counter()
    command_token = str(command or "").strip()
    request_payload = dict(payload or {})
    session_scope = request_namespace_builder(
        repo_root=root,
        command=command_token,
        payload=request_payload,
    )
    if str(transport.get("transport", "")).strip() == "tcp":
        sock = open_socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_target: Any = (
            str(transport.get("host", "")).strip() or "127.0.0.1",
            int(transport.get("port", 0) or 0),
        )
    else:
        sock = open_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connect_target = str(transport.get("path", "")).strip() or str(resolve_socket_path(repo_root=root))
    sock.settimeout(timeout_seconds)
    try:
        sock.connect(connect_target)
        rendered = json.dumps(
            {
                "command": command_token,
                "payload": request_payload,
                **(
                    {"auth_token": str(daemon_metadata.get("auth_token", "")).strip()}
                    if str(daemon_metadata.get("auth_token", "")).strip()
                    else {}
                ),
            },
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        sock.sendall(rendered)
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)
    except OSError as exc:
        if required:
            raise RuntimeError("odylith context engine daemon request failed") from exc
        return None
    finally:
        with contextlib.suppress(OSError):
            sock.close()
    if not chunks:
        if required:
            raise RuntimeError("odylith context engine daemon returned no response")
        return None
    try:
        response = json.loads(b"".join(chunks).decode("utf-8"))
    except json.JSONDecodeError as exc:
        if required:
            raise RuntimeError("odylith context engine daemon returned invalid JSON") from exc
        return None
    if not isinstance(response, Mapping):
        if required:
            raise RuntimeError("odylith context engine daemon returned an invalid payload")
        return None
    if not bool(response.get("ok", False)):
        message = str(response.get("error", "")).strip() or "odylith context engine daemon request failed"
        if required:
            raise RuntimeError(message)
        return None
    daemon_payload = response.get("payload", {})
    runtime_execution = {
        "source": "workspace_daemon",
        "transport": str(transport.get("transport", "")).strip() or "unknown",
        "workspace_daemon_reused": True,
        "workspace_key": str(session_scope.get("workspace_key", "")).strip(),
        "request_namespace": str(session_scope.get("request_namespace", "")).strip(),
        "session_namespaced": bool(session_scope.get("session_namespaced")),
        "session_namespace": str(session_scope.get("session_namespace", "")).strip(),
        "working_tree_scope": str(session_scope.get("working_tree_scope", "")).strip(),
        "session_id_present": bool(session_scope.get("session_id_present")),
        "claim_path_count": int(session_scope.get("claim_path_count", 0) or 0),
        "changed_path_count": int(session_scope.get("changed_path_count", 0) or 0),
    }
    runtime_timing_recorder(
        repo_root=root,
        category="daemon",
        operation=command_token or "request",
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        metadata={
            "required": bool(required),
            "transport": str(runtime_execution["transport"]),
            "authenticated": bool(str(daemon_metadata.get("auth_token", "")).strip()),
            "workspace_daemon_reused": True,
            "session_namespaced": bool(runtime_execution["session_namespaced"]),
            "session_namespace": str(runtime_execution["session_namespace"]),
            "request_namespace": str(runtime_execution["request_namespace"]),
        },
    )
    return (
        dict(daemon_payload) if isinstance(daemon_payload, Mapping) else {"value": daemon_payload},
        runtime_execution,
    )


def read_runtime_daemon_usage(*, repo_root: Path) -> dict[str, Any]:
    """Load the workspace-daemon usage ledger payload."""
    payload = odylith_context_cache.read_json_object(
        odylith_context_engine_runtime_artifacts.daemon_usage_path(repo_root=repo_root)
    )
    if not payload:
        return {}
    command_counts = (
        {
            str(key).strip(): int(value or 0)
            for key, value in dict(payload.get("command_counts", {})).items()
            if str(key).strip()
        }
        if isinstance(payload.get("command_counts"), Mapping)
        else {}
    )
    recent_namespaces = (
        [str(token).strip() for token in payload.get("recent_session_namespaces", []) if str(token).strip()]
        if isinstance(payload.get("recent_session_namespaces"), list)
        else []
    )
    seen_namespaces = (
        [str(token).strip() for token in payload.get("seen_session_namespaces", []) if str(token).strip()]
        if isinstance(payload.get("seen_session_namespaces"), list)
        else []
    )
    return {
        "workspace_key": str(payload.get("workspace_key", "")).strip(),
        "request_count": int(payload.get("request_count", 0) or 0),
        "session_scoped_request_count": int(payload.get("session_scoped_request_count", 0) or 0),
        "unique_session_namespace_count": int(payload.get("unique_session_namespace_count", 0) or 0),
        "last_command": str(payload.get("last_command", "")).strip(),
        "last_request_utc": str(payload.get("last_request_utc", "")).strip(),
        "last_session_namespace": str(payload.get("last_session_namespace", "")).strip(),
        "last_working_tree_scope": str(payload.get("last_working_tree_scope", "")).strip(),
        "recent_session_namespaces": recent_namespaces[:8],
        "seen_session_namespaces": seen_namespaces[:64],
        "command_counts": command_counts,
    }


def record_runtime_daemon_usage(
    *,
    repo_root: Path,
    command: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Update the workspace-daemon usage ledger for one handled request."""
    root = Path(repo_root).resolve()
    target = odylith_context_engine_runtime_artifacts.daemon_usage_path(repo_root=root)
    target.parent.mkdir(parents=True, exist_ok=True)
    scope = runtime_request_namespace_from_payload(
        repo_root=root,
        command=command,
        payload=payload,
    )
    with odylith_context_cache.advisory_lock(repo_root=root, key=str(target)):
        existing = read_runtime_daemon_usage(repo_root=root)
        command_counts = (
            dict(existing.get("command_counts", {}))
            if isinstance(existing.get("command_counts"), Mapping)
            else {}
        )
        command_token = str(command or "").strip() or "request"
        command_counts[command_token] = int(command_counts.get(command_token, 0) or 0) + 1
        recent_namespaces = (
            [token for token in existing.get("recent_session_namespaces", []) if str(token).strip()]
            if isinstance(existing.get("recent_session_namespaces"), list)
            else []
        )
        seen_namespaces = (
            [token for token in existing.get("seen_session_namespaces", []) if str(token).strip()]
            if isinstance(existing.get("seen_session_namespaces"), list)
            else []
        )
        session_namespace = str(scope.get("session_namespace", "")).strip()
        if session_namespace:
            recent_namespaces = [session_namespace, *[token for token in recent_namespaces if token != session_namespace]][
                :8
            ]
            if session_namespace not in seen_namespaces:
                seen_namespaces = [session_namespace, *seen_namespaces][:64]
        updated_payload = {
            "workspace_key": str(scope.get("workspace_key", "")).strip() or workspace_daemon_key(repo_root=root),
            "request_count": int(existing.get("request_count", 0) or 0) + 1,
            "session_scoped_request_count": int(existing.get("session_scoped_request_count", 0) or 0)
            + (1 if bool(scope.get("session_namespaced")) else 0),
            "unique_session_namespace_count": len(seen_namespaces),
            "last_command": command_token,
            "last_request_utc": odylith_context_engine_runtime_support.utc_now(),
            "last_session_namespace": session_namespace,
            "last_working_tree_scope": str(scope.get("working_tree_scope", "")).strip(),
            "recent_session_namespaces": recent_namespaces,
            "seen_session_namespaces": seen_namespaces,
            "command_counts": command_counts,
        }
        rendered = json.dumps(updated_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != rendered:
            target.write_text(rendered, encoding="utf-8")
    return updated_payload


__all__ = [
    "normalize_loopback_host",
    "read_runtime_daemon_metadata",
    "read_runtime_daemon_usage",
    "record_runtime_daemon_usage",
    "request_runtime_daemon",
    "runtime_daemon_owner_pid",
    "runtime_daemon_pid",
    "runtime_daemon_pid_alive",
    "runtime_daemon_transport",
    "runtime_request_namespace",
    "runtime_request_namespace_from_payload",
    "workspace_daemon_key",
]
