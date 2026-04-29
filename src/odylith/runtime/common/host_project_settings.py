"""Additive host project settings helpers for Codex and Claude assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.install.fs import atomic_write_text


PREIMAGE_BACKUP_SUFFIX = ".odylith-preimage.bak"


def load_json_object_for_update(path: Path) -> dict[str, Any] | None:
    """Load a JSON object only when it is safe for an additive update."""
    if path.is_symlink():
        return None
    if not path.exists():
        return {}
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def write_preimage_backup_once(path: Path) -> Path | None:
    """Preserve the first pre-Odylith copy beside a user-owned settings file."""
    if path.is_symlink() or not path.is_file():
        return None
    backup = path.with_name(f"{path.name}{PREIMAGE_BACKUP_SUFFIX}")
    if backup.exists():
        return backup
    backup.write_bytes(path.read_bytes())
    return backup


def atomic_write_json_object(path: Path, payload: Mapping[str, Any]) -> Path:
    rendered = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return path
    write_preimage_backup_once(path)
    atomic_write_text(path, rendered, encoding="utf-8")
    return path


def merge_unique_strings(existing: object, additions: Sequence[str]) -> list[str] | object:
    if existing is not None and not isinstance(existing, list):
        return existing
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*(existing or []), *additions]:
        token = str(value or "").strip()
        if token and token not in seen:
            merged.append(token)
            seen.add(token)
    return merged


def merge_hook_entries(existing: object, additions: Sequence[Mapping[str, Any]]) -> list[Any] | object:
    if existing is not None and not isinstance(existing, list):
        return existing
    merged: list[Any] = list(existing or [])
    seen = {
        json.dumps(entry, sort_keys=True, separators=(",", ":"))
        for entry in merged
        if isinstance(entry, Mapping)
    }
    for entry in additions:
        key = json.dumps(dict(entry), sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        merged.append(dict(entry))
        seen.add(key)
    return merged


def merge_hook_map(existing: object, additions: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any] | object:
    if existing is not None and not isinstance(existing, Mapping):
        return existing
    merged: dict[str, Any] = dict(existing or {})
    for event_name, event_additions in additions.items():
        merged[event_name] = merge_hook_entries(merged.get(event_name), event_additions)
    return merged
