"""Runtime version sidecar for stale tooling-shell detection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from odylith.install import version_status
from odylith.install.state import load_install_state, load_version_pin
from odylith.runtime.context_engine import odylith_context_cache

VERSION_STATE_FILENAME = "odylith-version-state.v1.json"
VERSION_STATE_JS_FILENAME = "odylith-version-state.v1.js"
VERSION_STATE_GLOBAL_NAME = "__ODYLITH_VERSION_STATE__"
VERSION_STATE_SCHEMA = "odylith.dashboard.version_state.v1"


def version_state_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / VERSION_STATE_FILENAME).resolve()


def version_state_js_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / VERSION_STATE_JS_FILENAME).resolve()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _display_version(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    return f"v{token}" if token[0].isdigit() else token


def _status_payload(*, repo_root: Path) -> dict[str, Any]:
    try:
        status = version_status(repo_root=repo_root)
    except Exception:
        return {}
    return {
        "repo_role": status.repo_role,
        "posture": status.posture,
        "runtime_source": status.runtime_source,
        "release_eligible": status.release_eligible,
        "pinned_version": status.pinned_version,
        "active_version": status.active_version,
        "detached": status.detached,
        "diverged_from_pin": status.diverged_from_pin,
    }


def _fallback_versions(*, repo_root: Path) -> dict[str, str]:
    active_version = ""
    pinned_version = ""
    try:
        install_state = load_install_state(repo_root=repo_root)
    except Exception:
        install_state = {}
    if isinstance(install_state, Mapping):
        active_version = str(install_state.get("active_version", "")).strip()
    try:
        pin = load_version_pin(repo_root=repo_root, fallback_version="")
    except Exception:
        pin = None
    if pin is not None:
        pinned_version = str(getattr(pin, "odylith_version", "") or "").strip()
    return {
        "active_version": active_version,
        "pinned_version": pinned_version,
    }


def build_version_state_payload(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    payload = _status_payload(repo_root=root)
    if not payload:
        payload = _fallback_versions(repo_root=root)
    active_version = str(payload.get("active_version", "")).strip()
    pinned_version = str(payload.get("pinned_version", "")).strip()
    authoritative_version = active_version or pinned_version
    return {
        "schema_version": VERSION_STATE_SCHEMA,
        "generated_utc": _utc_now(),
        "source": "odylith version",
        **payload,
        "authoritative_version": authoritative_version,
        "authoritative_label": _display_version(authoritative_version),
    }


def _render_version_state_js(*, payload: Mapping[str, Any]) -> str:
    return (
        f"window[{json.dumps(VERSION_STATE_GLOBAL_NAME, ensure_ascii=False)}] = "
        f"{json.dumps(dict(payload), sort_keys=True, ensure_ascii=False)};\n"
    )


def persist_version_state(*, repo_root: Path, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    resolved_payload = dict(payload) if isinstance(payload, Mapping) else build_version_state_payload(repo_root=root)
    json_path = version_state_path(repo_root=root)
    js_path = version_state_js_path(repo_root=root)
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=json_path,
        payload=resolved_payload,
        lock_key=str(json_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=root,
        path=js_path,
        content=_render_version_state_js(payload=resolved_payload),
        lock_key=str(js_path),
    )
    return resolved_payload


__all__ = [
    "VERSION_STATE_FILENAME",
    "VERSION_STATE_GLOBAL_NAME",
    "VERSION_STATE_JS_FILENAME",
    "VERSION_STATE_SCHEMA",
    "build_version_state_payload",
    "persist_version_state",
    "version_state_js_path",
    "version_state_path",
]
