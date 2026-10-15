"""Durable host checkpoints and Compass events with separate replacement ownership."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import fcntl
import json
import os
from pathlib import Path
import stat
import uuid
from typing import Any, Iterable, Iterator, Mapping


DIRTY_EVENTS_RELATIVE = Path(".odylith/runtime/host-hooks/dirty-events.v1.jsonl")
COMPASS_EVENTS_RELATIVE = DIRTY_EVENTS_RELATIVE.with_name("compass-events.v1.jsonl")
COMPASS_EVENT_SOURCE = "compass_event"
MAX_COMPASS_EVENT_BYTES = 1024 * 1024
MAX_LEDGER_BYTES = 16 * 1024 * 1024
_LOG_EVENT_KINDS = frozenset({"decision", "implementation", "statement", "update"})


class HostDirtyCheckpointError(RuntimeError):
    """The host ledger cannot safely retain or identify pending evidence."""


def event_store_path(repo_root: Path | str) -> Path:
    """Return the repo-local dirty-event ledger path."""

    return Path(repo_root).expanduser().resolve() / DIRTY_EVENTS_RELATIVE


def compass_event_store_path(repo_root: Path | str) -> Path:
    """Return the private Compass journal, outside old checkpoint replacement."""

    return event_store_path(repo_root).with_name(COMPASS_EVENTS_RELATIVE.name)


@contextmanager
def _locked_store(
    repo_root: Path | str, *, create: bool = False, name: str = DIRTY_EVENTS_RELATIVE.name,
) -> Iterator[int | None]:
    descriptors: list[int] = []
    try:
        root = Path(repo_root).expanduser().resolve()
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        descriptors.append(directory)
        for part in DIRTY_EVENTS_RELATIVE.parts[:-1]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
                else:
                    os.fsync(directory)
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            except FileNotFoundError:
                if create:
                    raise
                yield None
                return
            descriptors.append(child)
            directory = child
        lock_name = Path(name).with_suffix(".lock").name
        lock = _open_regular(directory, lock_name, os.O_RDWR | os.O_CREAT)
        descriptors.append(lock)
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = os.stat(lock_name, dir_fd=directory, follow_symlinks=False)
        owned = os.fstat(lock)
        if (current.st_dev, current.st_ino) != (owned.st_dev, owned.st_ino):
            raise HostDirtyCheckpointError("Host ledger lock changed during admission")
        yield directory
    except OSError as exc:
        raise HostDirtyCheckpointError("Host ledger is unavailable or has an unsafe owner path") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _open_regular(directory: int, name: str, flags: int, *, mode: int = 0o600) -> int:
    descriptor = os.open(name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, mode, dir_fd=directory)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        os.close(descriptor)
        raise HostDirtyCheckpointError("Host ledger objects must be single-link regular files")
    return descriptor


def _read_bytes(directory: int, *, name: str = DIRTY_EVENTS_RELATIVE.name) -> bytes:
    try:
        descriptor = _open_regular(directory, name, os.O_RDONLY)
    except FileNotFoundError:
        return b""
    with os.fdopen(descriptor, "rb") as handle:
        if os.fstat(handle.fileno()).st_size > MAX_LEDGER_BYTES:
            raise HostDirtyCheckpointError("Host ledger exceeds its read bound; ledger retained")
        data = handle.read(MAX_LEDGER_BYTES + 1)
        if len(data) > MAX_LEDGER_BYTES:
            raise HostDirtyCheckpointError("Host ledger exceeds its read bound; ledger retained")
        return data


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise HostDirtyCheckpointError("Host event must contain JSON values") from exc


def _append_record(
    repo_root: Path | str, record: Mapping[str, Any], *, name: str = DIRTY_EVENTS_RELATIVE.name,
) -> None:
    data = _json_bytes(record) + b"\n"
    with _locked_store(repo_root, create=True, name=name) as directory:
        assert directory is not None
        previous = _read_bytes(directory, name=name)
        if _is_compass_row(record):
            if any(row["id"] == record["id"] for row in _compass_rows(previous)):
                raise HostDirtyCheckpointError("Pending Compass identity already exists; ledger retained")
        separator = b"\n" if previous and not previous.endswith(b"\n") else b""
        if len(previous) + len(separator) + len(data) > MAX_LEDGER_BYTES:
            raise HostDirtyCheckpointError("Host ledger would exceed its write bound; ledger retained")
        descriptor = _open_regular(directory, name, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        with os.fdopen(descriptor, "ab") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(separator)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.fsync(directory)


def _rewrite(directory: int, data: bytes, *, name: str = DIRTY_EVENTS_RELATIVE.name) -> None:
    metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise HostDirtyCheckpointError("Host ledger changed before acknowledgement")
    temporary = f".{name}-{uuid.uuid4().hex}.tmp"
    descriptor = _open_regular(directory, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


def _parse_line(line: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
        _json_bytes(value)
    except (ValueError, UnicodeError, HostDirtyCheckpointError):
        return None
    return dict(value) if isinstance(value, dict) else None


def _is_compass_row(row: Mapping[str, Any]) -> bool:
    return row.get("source") == COMPASS_EVENT_SOURCE or "event" in row


def _is_dirty_row(row: Mapping[str, Any]) -> bool:
    return (
        not _is_compass_row(row) and type(row.get("version")) is int and row["version"] == 1
        and all(isinstance(row.get(key), str) for key in ("id", "recorded_utc", "host_family", "session_id", "source"))
        and bool(row["id"])
        and all(isinstance(row.get(key), list) and all(isinstance(value, str) for value in row[key])
                for key in ("paths", "governed_paths"))
    )


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def _require_compass_row(row: Mapping[str, Any]) -> None:
    from odylith.runtime.intervention_engine.stream_state import _INTERVENTION_EVENT_KINDS

    event = row.get("event")
    event_id = row.get("id")
    try:
        valid_id = isinstance(event_id, str) and uuid.UUID(hex=event_id).hex == event_id
    except ValueError:
        valid_id = False
    if (
        type(row.get("version")) is not int or row["version"] != 1
        or row.get("source") != COMPASS_EVENT_SOURCE or not valid_id
        or not all(isinstance(row.get(key), str) for key in ("recorded_utc", "host_family", "session_id"))
        or not _valid_timestamp(row.get("recorded_utc"))
        or not isinstance(event, dict)
        or not all(isinstance(event.get(key), str) and event[key].strip() for key in ("kind", "ts_iso"))
        or not isinstance(event.get("summary"), str)
        or (not event["summary"].strip() and event.get("kind") != "subagent_stop")
        or event.get("kind") not in _LOG_EVENT_KINDS | _INTERVENTION_EVENT_KINDS | {"subagent_stop"}
        or not _valid_timestamp(event.get("ts_iso"))
        or not isinstance(event.get("session_id"), str) or not event["session_id"].strip()
        or not isinstance(event.get("host_family"), str) or event["host_family"] not in {"codex", "claude"}
        or event.get("transaction_id") != "host-event-" + str(event_id)
        or any(key in event and not isinstance(event[key], str) for key in ("author", "source", "session_id", "host_family"))
        or any(key in event and (not isinstance(event[key], list)
               or any(not isinstance(value, str) for value in event[key]))
               for key in ("workstreams", "artifacts", "components", "action_surfaces", "semantic_signature"))
        or any(key in event and not isinstance(event[key], dict) for key in ("metadata", "deployment_truth"))
        or event.get("session_id", "") != row.get("session_id")
        or event.get("host_family", "") != row.get("host_family")
    ):
        raise HostDirtyCheckpointError("Malformed pending Compass event; ledger retained")
    if len(_json_bytes(event)) > MAX_COMPASS_EVENT_BYTES:
        raise HostDirtyCheckpointError("Pending Compass event exceeds its size bound; ledger retained")


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
    paths: Iterable[str] = (),
    governed_paths: Iterable[str] = (),
) -> str:
    """Persist affected paths, not shell input, and return the event id."""

    event_id = uuid.uuid4().hex
    record = {
        "version": 1,
        "id": event_id,
        "recorded_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "host_family": str(host_family or "").strip().casefold(),
        "session_id": str(session_id or "").strip(),
        "source": str(source or "").strip(),
        "paths": _dedupe_strings(paths),
        "governed_paths": _dedupe_strings(governed_paths),
    }
    try:
        _append_record(repo_root, record)
    except HostDirtyCheckpointError:
        return ""
    return event_id


def read_dirty_events(
    *,
    repo_root: Path | str,
    host_family: str = "",
    session_id: str = "",
) -> list[dict[str, Any]]:
    """Read pending dirty events filtered by host family and session when supplied."""

    host_filter = str(host_family or "").strip().casefold()
    session_filter = str(session_id or "").strip()
    rows: list[dict[str, Any]] = []
    try:
        with _locked_store(repo_root) as directory:
            data = _read_bytes(directory) if directory is not None else b""
    except HostDirtyCheckpointError:
        return []
    for line in data.splitlines():
        event = _parse_line(line)
        if event is None or not _is_dirty_row(event):
            continue
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
    try:
        with _locked_store(repo_root) as directory:
            if directory is None:
                return False
            lines = _read_bytes(directory).splitlines(keepends=True)
            retained = []
            for line in lines:
                row = _parse_line(line)
                if row is None or not _is_dirty_row(row) or row["id"] not in ids:
                    retained.append(line)
            if len(retained) == len(lines):
                return False
            _rewrite(directory, b"".join(retained))
            return True
    except HostDirtyCheckpointError:
        return False


def record_compass_event(*, repo_root: Path | str, event: Mapping[str, Any]) -> str:
    """Durably retain one canonical event before any governed stream append."""

    if not isinstance(event, Mapping):
        raise HostDirtyCheckpointError("Pending Compass event must be a mapping")
    event_id = uuid.uuid4().hex
    payload = json.loads(_json_bytes(dict(event)))
    payload.setdefault("transaction_id", "host-event-" + event_id)
    payload.setdefault("ts_iso", datetime.now(UTC).isoformat())
    row = {
        "version": 1, "id": event_id, "source": COMPASS_EVENT_SOURCE,
        "recorded_utc": datetime.now(UTC).isoformat(),
        "host_family": payload.get("host_family", ""),
        "session_id": payload.get("session_id", ""), "event": payload,
    }
    _require_compass_row(row)
    _append_record(repo_root, row, name=COMPASS_EVENTS_RELATIVE.name)
    return event_id


def capture_stop_summary(
    *, repo_root: Path | str, host_family: str, session_id: str,
    summary: str, workstreams: Iterable[str] = (),
) -> bool:
    """Keep a meaningful Stop summary without starting canonical publication."""

    if not summary.strip():
        return False
    record_compass_event(repo_root=repo_root, event={
        "kind": "implementation", "summary": summary,
        "ts_iso": datetime.now(UTC).isoformat(), "author": "assistant", "source": "assistant",
        "host_family": host_family, "session_id": session_id,
        "workstreams": list(workstreams)[:4], "artifacts": [],
    })
    return True


def _compass_rows(data: bytes) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for line_number, line in enumerate(data.splitlines(), 1):
        if not line.strip():
            continue
        row = _parse_line(line)
        if row is None:
            raise HostDirtyCheckpointError(f"Malformed host ledger row {line_number}; ledger retained")
        _require_compass_row(row)
        if row["id"] in ids:
            raise HostDirtyCheckpointError("Duplicate pending Compass identity; ledger retained")
        ids.add(row["id"])
        rows.append(row)
    return rows


def read_compass_events(*, repo_root: Path | str) -> list[dict[str, Any]]:
    """Read exact pending events, refusing corruption instead of losing memory."""

    with _locked_store(repo_root, name=COMPASS_EVENTS_RELATIVE.name) as directory:
        return _compass_rows(_read_bytes(directory, name=COMPASS_EVENTS_RELATIVE.name)) if directory is not None else []


def acknowledge_compass_event(*, repo_root: Path | str, event_id: str, event: Mapping[str, Any]) -> bool:
    """Remove only the unchanged event whose canonical publication completed."""

    expected = _json_bytes(dict(event))
    with _locked_store(repo_root, name=COMPASS_EVENTS_RELATIVE.name) as directory:
        if directory is None:
            return False
        data = _read_bytes(directory, name=COMPASS_EVENTS_RELATIVE.name)
        rows = _compass_rows(data)
        matched = next((row for row in rows if row["id"] == event_id), None)
        if matched is None or _json_bytes(matched["event"]) != expected:
            return False
        retained = [line for line in data.splitlines(keepends=True)
                    if (row := _parse_line(line)) is None
                    or not _is_compass_row(row) or row.get("id") != event_id]
        _rewrite(directory, b"".join(retained), name=COMPASS_EVENTS_RELATIVE.name)
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
