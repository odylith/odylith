"""Helpers for deterministic `generated_utc` values in generated artifacts."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
from typing import Any, Mapping

_DERIVED_GENERATED_KEYS = {
    "generated_utc",
    "generated_local_date",
    "generated_local_time",
}


def _now_utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%SZ")


def _without_generated_utc(payload: Mapping[str, Any]) -> dict[str, Any]:
    clone = dict(payload)
    for key in _DERIVED_GENERATED_KEYS:
        clone.pop(key, None)
    return clone


def _load_json_dict(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _load_js_assignment_dict(*, path: Path, global_name: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    pattern = re.compile(
        rf"window\[{re.escape(json.dumps(global_name, ensure_ascii=False))}\]\s*=\s*(\{{.*\}});\s*$",
        re.DOTALL,
    )
    match = pattern.search(text.strip())
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def resolve_for_json_file(*, output_path: Path, payload: Mapping[str, Any]) -> str:
    """Return stable `generated_utc` for JSON payload writes.

    Reuses the existing file timestamp when only `generated_utc` differs.
    """

    existing = _load_json_dict(output_path)
    if not existing:
        return _now_utc()

    previous = str(existing.get("generated_utc", "")).strip()
    if not previous:
        return _now_utc()

    if _without_generated_utc(existing) == _without_generated_utc(payload):
        return previous
    return _now_utc()


def resolve_for_js_assignment_file(
    *,
    output_path: Path,
    global_name: str,
    payload: Mapping[str, Any],
) -> str:
    """Return stable `generated_utc` for JS wrapper files that assign a payload to `window`."""

    existing = _load_js_assignment_dict(path=output_path, global_name=global_name)
    if not existing:
        return _now_utc()

    previous = str(existing.get("generated_utc", "")).strip()
    if not previous:
        return _now_utc()

    if _without_generated_utc(existing) == _without_generated_utc(payload):
        return previous
    return _now_utc()


def _load_embedded_json(*, html_path: Path, script_id: str) -> dict[str, Any] | None:
    if not html_path.is_file():
        return None
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError:
        return None

    pattern = re.compile(
        rf'<script id="{re.escape(script_id)}" type="application/json">(.*?)</script>',
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def resolve_for_embedded_json_html(
    *,
    html_path: Path,
    script_id: str,
    payload: Mapping[str, Any],
) -> str:
    """Return stable `generated_utc` for HTML files with embedded JSON payloads."""

    existing = _load_embedded_json(html_path=html_path, script_id=script_id)
    if not existing:
        return _now_utc()

    previous = str(existing.get("generated_utc", "")).strip()
    if not previous:
        return _now_utc()

    if _without_generated_utc(existing) == _without_generated_utc(payload):
        return previous
    return _now_utc()
