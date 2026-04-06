"""Resolve and persist the local Odylith ablation switch."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.context_engine import odylith_context_cache

_SWITCH_FILENAME = "odylith-switch.v1.json"
_ENV_MODE_KEYS = ("ODYLITH_MODE", "ODYLITH_MODE")
_ENV_ENABLED_KEYS = ("ODYLITH_ENABLED", "ODYLITH_ENABLED")
_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_FALSY = {"0", "false", "no", "off", "disabled"}


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def switch_path(*, repo_root: Path) -> Path:
    root = Path(repo_root).resolve()
    return (root / ".odylith" / "runtime" / _SWITCH_FILENAME).resolve()


def _parse_enabled_token(value: Any) -> bool | None:
    token = str(value or "").strip().lower()
    if not token:
        return None
    if token in _TRUTHY:
        return True
    if token in _FALSY:
        return False
    return None


def _read_switch_payload(*, repo_root: Path) -> dict[str, Any]:
    path = switch_path(repo_root=repo_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def resolve_odylith_switch(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    for key in _ENV_MODE_KEYS:
        token = str(os.environ.get(key, "")).strip().lower()
        if token in {"on", "enabled"}:
            return {
                "enabled": True,
                "source": f"env:{key}",
                "mode": token,
                "path": str(switch_path(repo_root=root)),
            }
        if token in {"off", "disabled"}:
            return {
                "enabled": False,
                "source": f"env:{key}",
                "mode": token,
                "path": str(switch_path(repo_root=root)),
            }
    for key in _ENV_ENABLED_KEYS:
        parsed = _parse_enabled_token(os.environ.get(key, ""))
        if parsed is None:
            continue
        return {
            "enabled": parsed,
            "source": f"env:{key}",
            "mode": "enabled" if parsed else "disabled",
            "path": str(switch_path(repo_root=root)),
        }

    payload = _read_switch_payload(repo_root=root)
    if payload:
        enabled = bool(payload.get("enabled", True))
        return {
            "enabled": enabled,
            "source": "local_file",
            "mode": "enabled" if enabled else "disabled",
            "path": str(switch_path(repo_root=root)),
            "updated_utc": str(payload.get("updated_utc", "")).strip(),
            "note": str(payload.get("note", "")).strip(),
        }

    return {
        "enabled": True,
        "source": "default",
        "mode": "enabled",
        "path": str(switch_path(repo_root=root)),
    }


def build_odylith_switch_snapshot(*, repo_root: Path) -> dict[str, Any]:
    resolved = resolve_odylith_switch(repo_root=repo_root)
    enabled = bool(resolved.get("enabled", True))
    source = str(resolved.get("source", "")).strip() or "default"
    return {
        "contract": "odylith_switch.v1",
        "version": "v1",
        "scope": "odylith_platform",
        "enabled": enabled,
        "status": "enabled" if enabled else "disabled",
        "mode": str(resolved.get("mode", "")).strip() or ("enabled" if enabled else "disabled"),
        "source": source,
        "env_override_active": source.startswith("env:"),
        "path": str(resolved.get("path", "")).strip() or str(switch_path(repo_root=Path(repo_root).resolve())),
        "updated_utc": str(resolved.get("updated_utc", "")).strip(),
        "note": str(resolved.get("note", "")).strip(),
        "ablation_active": not enabled,
    }


def write_odylith_switch(
    *,
    repo_root: Path,
    enabled: bool,
    note: str = "",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = switch_path(repo_root=root)
    payload = {
        "version": "v1",
        "enabled": bool(enabled),
        "updated_utc": _utc_now(),
        "note": str(note or "").strip(),
    }
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=path,
        payload=payload,
        lock_key=str(path),
    )
    return resolve_odylith_switch(repo_root=root)


def clear_odylith_switch(*, repo_root: Path) -> None:
    path = switch_path(repo_root=repo_root)
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=str(path)):
        if path.exists():
            path.unlink()


__all__ = [
    "build_odylith_switch_snapshot",
    "clear_odylith_switch",
    "resolve_odylith_switch",
    "switch_path",
    "write_odylith_switch",
]
