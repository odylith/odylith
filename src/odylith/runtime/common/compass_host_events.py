"""Publish retained host memory only through foreground Compass transactions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing import Any

from odylith.runtime.common import compass_log_continuation as continuation
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.surfaces import host_dirty_checkpoint as inbox
from odylith.runtime.surfaces import host_hook_execution

_FOREGROUND_EVENT_LIMIT = 4


def event_bytes(event: dict[str, Any]) -> bytes:
    return (json.dumps(event, sort_keys=True) + "\n").encode("utf-8")


def retained_event(*, repo_root: Path, event_id: str) -> dict[str, Any] | None:
    return next((row["event"] for row in inbox.read_compass_events(repo_root=repo_root)
                 if row["id"] == event_id), None)


def published_event_bytes(*, repo_root: Path, transaction_id: str) -> bytes | None:
    if publication.read_active_publication(repo_root) is not None:
        root = generations.require_greenfield_working_generation(repo_root).repository_root
    else:
        root = repo_root
    path = root / continuation.STREAM_PATH
    if not path.exists():
        return None
    matched = []
    for line in path.read_bytes().splitlines(keepends=True):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("transaction_id") == transaction_id:
            matched.append(line)
    if len(matched) > 1:
        raise inbox.HostDirtyCheckpointError("Retained host event has duplicate published identities.")
    return matched[0] if matched else None


def event_is_published(*, repo_root: Path, event: dict[str, Any]) -> bool:
    matched = published_event_bytes(repo_root=repo_root, transaction_id=event["transaction_id"])
    if matched is not None and matched != event_bytes(event):
        raise inbox.HostDirtyCheckpointError("Retained host event differs from its published identity.")
    return matched is not None


def _acknowledge(*, repo_root: Path, record: dict[str, Any]) -> None:
    if not event_is_published(repo_root=repo_root, event=record["event"]):
        raise inbox.HostDirtyCheckpointError("Retained host event has no complete publication.")
    if not inbox.acknowledge_compass_event(
        repo_root=repo_root, event_id=record["id"], event=record["event"],
    ):
        # Another foreground consumer may have acknowledged the same exact event.
        if retained_event(repo_root=repo_root, event_id=record["id"]) is not None:
            raise inbox.HostDirtyCheckpointError("Retained host event changed before acknowledgment.")


def acknowledge_retained(*, repo_root: Path, event_id: str) -> None:
    record = next((row for row in inbox.read_compass_events(repo_root=repo_root) if row["id"] == event_id), None)
    if record is not None:
        _acknowledge(repo_root=repo_root, record=record)


def resume_pending(
    *, repo_root: Path, dispatch: Callable[[list[str]], int],
) -> int:
    """Complete only a receipt belonging to the same retained host event."""
    if host_hook_execution.in_host_hook_command():
        return 0
    pending = continuation.pending_event(repo_root=repo_root)
    if pending is None:
        return 0
    records = inbox.read_compass_events(repo_root=repo_root)
    record = next((row for row in records if row["event"] == pending), None)
    if record is None:
        raise continuation.CompassLogContinuationError(
            "RECOVERY_REQUIRED: an unrelated Compass log requires explicit completion; no writer ran."
        )
    result = dispatch(["compass", "log", "--repo-root", str(repo_root), "--complete"])
    if result == 0:
        _acknowledge(repo_root=repo_root, record=record)
    return result


def publish_pending(
    *, repo_root: Path, dispatch: Callable[[list[str]], int],
) -> int:
    """Acknowledge exact published bytes; retain failed and concurrent arrivals."""
    if host_hook_execution.in_host_hook_command():
        return 0
    for record in inbox.read_compass_events(repo_root=repo_root)[:_FOREGROUND_EVENT_LIMIT]:
        if event_is_published(repo_root=repo_root, event=record["event"]):
            if publication.read_active_publication(repo_root) is None:
                # Legacy installs have no immutable publication oracle. Finish
                # rendering an existing append rather than appending it twice.
                result = dispatch(["compass", "refresh", "--repo-root", str(repo_root)])
                if result:
                    return result
        else:
            result = dispatch([
                "compass", "log", "--repo-root", str(repo_root), "--host-event", record["id"],
            ])
            if result:
                return result
        _acknowledge(repo_root=repo_root, record=record)
    return 0


def finish_foreground(
    *, repo_root: Path, dispatch: Callable[[list[str]], int],
    dirty_records: Sequence[dict[str, Any]] = (), synced_paths: Sequence[str] = (),
) -> None:
    """Keep a completed authored writer successful if later memory upkeep fails."""
    output = io.StringIO()
    try:
        covered = set(synced_paths)
        ids = [row["id"] for row in dirty_records if set(row.get("governed_paths", ())) <= covered]
        if ids:
            inbox.clear_dirty_events(repo_root=repo_root, event_ids=ids)
        with redirect_stdout(output), redirect_stderr(output):
            result = publish_pending(repo_root=repo_root, dispatch=dispatch)
        if result:
            print("Requested change completed. Session history remains queued for publication.", file=sys.stderr)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Requested change completed. Session history remains pending: {exc}", file=sys.stderr)


def is_foreground_publication(tokens: list[str]) -> bool:
    if host_hook_execution.in_host_hook_command() or any(t in {"-h", "--help"} for t in tokens):
        return False
    if tokens[:1] == ["sync"]:
        return "--dry-run" not in tokens and "--check-only" not in tokens
    return tokens[:2] == ["compass", "log"] and not any(
        t in {"--host-event", "--complete", "--abandon-restored"}
        or t.startswith(("--host-event=", "--abandon-restored=")) for t in tokens
    )
