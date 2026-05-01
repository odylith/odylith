"""Cheap host-hook payload parsing helpers."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Mapping


_PATCH_START_RE = re.compile(r"^\s*\*\*\* Begin Patch\b", re.MULTILINE)


def load_payload(raw: str | None = None) -> dict[str, Any]:
    """Load a hook JSON payload without importing host runtime modules."""

    text = raw if raw is not None else sys.stdin.read()
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def mapping_payload(value: Any) -> Mapping[str, Any]:
    """Return a mapping payload from host-native dict or JSON string values."""

    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        return {}
    token = value.strip()
    if not token.startswith("{"):
        return {}
    try:
        parsed = json.loads(token)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


def command_from_hook_payload(payload: Mapping[str, Any] | None) -> str:
    """Return the Bash/apply-patch command represented by a host hook payload."""

    if not isinstance(payload, Mapping):
        return ""
    tool_name = str(
        payload.get("tool_name")
        or payload.get("toolName")
        or payload.get("name")
        or ""
    ).strip()
    for tool_input in (
        mapping_payload(payload.get("tool_input")),
        mapping_payload(payload.get("arguments")),
    ):
        command = str(tool_input.get("command") or tool_input.get("cmd") or payload.get("command") or "").strip()
        if command:
            return command
        patch = str(tool_input.get("patch") or tool_input.get("input") or "").strip()
        if patch and (tool_name == "apply_patch" or _PATCH_START_RE.search(patch)):
            return f"apply_patch <<'PATCH'\n{patch}\nPATCH"
    patch = str(payload.get("patch") or payload.get("input") or "").strip()
    if patch and (tool_name == "apply_patch" or _PATCH_START_RE.search(patch)):
        return f"apply_patch <<'PATCH'\n{patch}\nPATCH"
    return str(payload.get("command") or "").strip()
