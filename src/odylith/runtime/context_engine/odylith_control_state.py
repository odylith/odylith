"""Local JSON/JSONL control-state helpers for the Odylith Context Engine.

This module owns mutable local runtime state that should stay lightweight,
append-friendly, and independent from the compiled projection/read-model layer.
"""

from __future__ import annotations

import json
import contextlib
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache

STATE_FILENAME = "odylith-context-engine-state.v1.json"
STATE_JS_FILENAME = "odylith-context-engine-state.v1.js"
STATE_JS_GLOBAL_NAME = "__ODYLITH_CONTEXT_ENGINE_STATE__"
EVENTS_FILENAME = "odylith-context-engine-events.v1.jsonl"
TIMINGS_FILENAME = "odylith-context-engine-timings.v1.jsonl"
_TIMING_RETENTION_LIMIT = 512
_TIMING_COMPACT_EVERY = 64
_TIMING_SOFT_SIZE_BYTES = 512 * 1024
_PROCESS_TIMING_APPEND_COUNTS: dict[str, int] = {}


def runtime_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime").resolve()


def state_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / STATE_FILENAME).resolve()


def state_js_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / STATE_JS_FILENAME).resolve()


def events_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / EVENTS_FILENAME).resolve()


def timings_path(*, repo_root: Path) -> Path:
    return (runtime_root(repo_root=repo_root) / TIMINGS_FILENAME).resolve()


def read_state(*, repo_root: Path) -> dict[str, Any]:
    return odylith_context_cache.read_json_object(state_path(repo_root=repo_root))


def _render_state_js(*, payload: Mapping[str, Any]) -> str:
    return (
        f"window[{json.dumps(STATE_JS_GLOBAL_NAME, ensure_ascii=False)}] = "
        f"{json.dumps(dict(payload), sort_keys=True, ensure_ascii=False)};\n"
    )


def _should_write_state_js(*, repo_root: Path) -> bool:
    from odylith.install.manager import PRODUCT_REPO_ROLE, product_repo_role
    from odylith.install.state import load_install_state

    if product_repo_role(repo_root=repo_root) != PRODUCT_REPO_ROLE:
        return True
    state = load_install_state(repo_root=repo_root)
    active_version = str(state.get("active_version") or "").strip()
    detached = bool(state.get("detached"))
    return active_version == "source-local" or detached


def ensure_state_js_probe_asset(*, repo_root: Path) -> Path | None:
    resolved_root = Path(repo_root).resolve()
    js_path = state_js_path(repo_root=resolved_root)
    if not _should_write_state_js(repo_root=resolved_root):
        with odylith_context_cache.advisory_lock(repo_root=resolved_root, key=str(js_path)):
            with contextlib.suppress(OSError):
                js_path.unlink()
        return None
    payload = read_state(repo_root=resolved_root)
    odylith_context_cache.write_text_if_changed(
        repo_root=resolved_root,
        path=js_path,
        content=_render_state_js(payload=payload),
        lock_key=str(js_path),
    )
    return js_path


def write_state(*, repo_root: Path, payload: Mapping[str, Any]) -> None:
    resolved_root = Path(repo_root).resolve()
    resolved_payload = dict(payload)
    json_path = state_path(repo_root=resolved_root)
    odylith_context_cache.write_json_if_changed(
        repo_root=resolved_root,
        path=json_path,
        payload=resolved_payload,
        lock_key=str(json_path),
    )
    js_path = state_js_path(repo_root=resolved_root)
    if _should_write_state_js(repo_root=resolved_root):
        odylith_context_cache.write_text_if_changed(
            repo_root=resolved_root,
            path=js_path,
            content=_render_state_js(payload=resolved_payload),
            lock_key=str(js_path),
        )
        return
    with odylith_context_cache.advisory_lock(repo_root=resolved_root, key=str(js_path)):
        with contextlib.suppress(OSError):
            js_path.unlink()


def append_event(
    *,
    repo_root: Path,
    event_type: str,
    payload: Mapping[str, Any],
    version: str = "",
    ts_iso: str = "",
) -> None:
    target = events_path(repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "event_type": str(event_type).strip() or "runtime_event",
        "payload": dict(payload),
    }
    if str(version).strip():
        row["version"] = str(version).strip()
    if str(ts_iso).strip():
        row["ts_iso"] = str(ts_iso).strip()
    rendered = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=str(target)):
        with target.open("a", encoding="utf-8") as handle:
            handle.write(rendered)


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for raw in lines:
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


def _write_jsonl_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    rendered = "".join(json.dumps(dict(item), sort_keys=True, ensure_ascii=False) + "\n" for item in rows)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if existing == rendered:
        return
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        os.replace(temp_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(temp_name)
        raise


def append_timing(
    *,
    repo_root: Path,
    row: Mapping[str, Any],
    retention_limit: int = _TIMING_RETENTION_LIMIT,
) -> None:
    target = timings_path(repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_key = str(target)
    rendered = json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n"
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=lock_key):
        with target.open("a", encoding="utf-8") as handle:
            handle.write(rendered)
        cache_key = str(target.resolve())
        append_count = _PROCESS_TIMING_APPEND_COUNTS.get(cache_key, 0) + 1
        _PROCESS_TIMING_APPEND_COUNTS[cache_key] = append_count
        limit = max(1, int(retention_limit))
        try:
            current_size = int(target.stat().st_size)
        except OSError:
            current_size = len(rendered.encode("utf-8"))
        should_compact = current_size > _TIMING_SOFT_SIZE_BYTES or append_count % _TIMING_COMPACT_EVERY == 0
        if not should_compact:
            return
        rows = _load_jsonl_rows(target)
        if len(rows) <= limit and current_size <= _TIMING_SOFT_SIZE_BYTES:
            return
        _write_jsonl_rows(target, rows[-limit:])
        _PROCESS_TIMING_APPEND_COUNTS[cache_key] = 0


def load_timing_rows(
    *,
    repo_root: Path,
    limit: int = 24,
) -> list[dict[str, Any]]:
    rows = _load_jsonl_rows(timings_path(repo_root=repo_root))
    indexed = list(enumerate(rows))
    indexed.sort(
        key=lambda pair: (
            str(pair[1].get("ts_iso", "")).strip(),
            int(pair[0]),
        ),
        reverse=True,
    )
    return [dict(row) for _index, row in indexed[: max(1, int(limit))]]


def summarize_timings(
    *,
    repo_root: Path,
    limit: int = 24,
) -> dict[str, Any]:
    rows = load_timing_rows(repo_root=repo_root, limit=limit)
    aggregates: dict[tuple[str, str], dict[str, Any]] = {}
    recent: list[dict[str, Any]] = []
    for row in rows:
        recent.append(
            {
                "ts_iso": str(row.get("ts_iso", "")).strip(),
                "category": str(row.get("category", "")).strip(),
                "operation": str(row.get("operation", "")).strip(),
                "duration_ms": round(float(row.get("duration_ms", 0.0) or 0.0), 3),
                "metadata": dict(row.get("metadata", {}))
                if isinstance(row.get("metadata"), Mapping)
                else {},
            }
        )
        key = (str(row.get("category", "")).strip(), str(row.get("operation", "")).strip())
        bucket = aggregates.setdefault(
            key,
            {
                "category": key[0],
                "operation": key[1],
                "count": 0,
                "latest_utc": "",
                "latest_ms": 0.0,
                "max_ms": 0.0,
                "total_ms": 0.0,
            },
        )
        duration_ms = float(row.get("duration_ms", 0.0) or 0.0)
        bucket["count"] = int(bucket["count"]) + 1
        bucket["latest_utc"] = max(str(bucket["latest_utc"]), str(row.get("ts_iso", "")).strip())
        bucket["latest_ms"] = max(float(bucket["latest_ms"]), duration_ms)
        bucket["max_ms"] = max(float(bucket["max_ms"]), duration_ms)
        bucket["total_ms"] = float(bucket["total_ms"]) + duration_ms
    operations = [
        {
            **bucket,
            "avg_ms": round(float(bucket["total_ms"]) / max(1, int(bucket["count"])), 3),
            "latest_ms": round(float(bucket["latest_ms"]), 3),
            "max_ms": round(float(bucket["max_ms"]), 3),
        }
        for bucket in aggregates.values()
    ]
    operations.sort(
        key=lambda item: (
            str(item.get("latest_utc", "")).strip(),
            float(item.get("latest_ms", 0.0) or 0.0),
            str(item.get("operation", "")).strip(),
        ),
        reverse=True,
    )
    return {
        "recent": recent,
        "operations": operations,
    }


__all__ = [
    "EVENTS_FILENAME",
    "STATE_FILENAME",
    "STATE_JS_FILENAME",
    "STATE_JS_GLOBAL_NAME",
    "TIMINGS_FILENAME",
    "append_event",
    "append_timing",
    "ensure_state_js_probe_asset",
    "events_path",
    "load_timing_rows",
    "read_state",
    "runtime_root",
    "state_path",
    "state_js_path",
    "summarize_timings",
    "timings_path",
    "write_state",
]
