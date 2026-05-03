"""Deferred dirty-event storage for host checkpoint hooks."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import uuid
from typing import Any, Iterable, Mapping

from odylith.install.fs import atomic_write_text


DIRTY_EVENTS_RELATIVE = Path(".odylith/runtime/host-hooks/dirty-events.v1.jsonl")


def event_store_path(repo_root: Path | str) -> Path:
    """Return the repo-local dirty-event ledger path."""

    return Path(repo_root).expanduser().resolve() / DIRTY_EVENTS_RELATIVE


def _dedupe_strings(values: Iterable[Any]) -> list[str]:
    rows: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if token and token not in rows:
            rows.append(token)
    return rows


def record_dirty_event(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str = "",
    source: str,
    command: str = "",
    paths: Iterable[str] = (),
    governed_paths: Iterable[str] = (),
) -> str:
    """Append one dirty-event record and return its stable event id."""

    event_id = uuid.uuid4().hex
    record = {
        "version": 1,
        "id": event_id,
        "recorded_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "host_family": str(host_family or "").strip().casefold(),
        "session_id": str(session_id or "").strip(),
        "source": str(source or "").strip(),
        "command": str(command or "").strip(),
        "paths": _dedupe_strings(paths),
        "governed_paths": _dedupe_strings(governed_paths),
    }
    path = event_store_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError:
        return ""
    return event_id


def read_dirty_events(
    *,
    repo_root: Path | str,
    host_family: str = "",
    session_id: str = "",
) -> list[dict[str, Any]]:
    """Read pending dirty events filtered by host family and session when supplied."""

    path = event_store_path(repo_root)
    if not path.is_file():
        return []
    host_filter = str(host_family or "").strip().casefold()
    session_filter = str(session_id or "").strip()
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, Mapping):
            continue
        event = dict(parsed)
        if host_filter and str(event.get("host_family") or "").strip().casefold() != host_filter:
            continue
        if session_filter and str(event.get("session_id") or "").strip() != session_filter:
            continue
        rows.append(event)
    return rows


def clear_dirty_events(*, repo_root: Path | str, event_ids: Iterable[str]) -> bool:
    """Remove dirty events with ids in ``event_ids`` from the ledger."""

    ids = {str(value or "").strip() for value in event_ids if str(value or "").strip()}
    if not ids:
        return False
    path = event_store_path(repo_root)
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    retained: list[str] = []
    changed = False
    for line in lines:
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            retained.append(line)
            continue
        if isinstance(parsed, Mapping) and str(parsed.get("id") or "").strip() in ids:
            changed = True
            continue
        retained.append(line)
    if not changed:
        return False
    rendered = "\n".join(retained)
    if rendered:
        rendered += "\n"
    atomic_write_text(path, rendered, encoding="utf-8")
    return True


def deduped_governed_paths(events: Iterable[Mapping[str, Any]]) -> list[str]:
    """Return deduped governed paths from dirty events in event order."""

    paths: list[str] = []
    for event in events:
        values = event.get("governed_paths") if isinstance(event, Mapping) else None
        if not isinstance(values, list):
            continue
        paths.extend(str(path or "").strip() for path in values)
    return _dedupe_strings(paths)
