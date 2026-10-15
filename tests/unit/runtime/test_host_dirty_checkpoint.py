from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
import time
import uuid

import pytest

from odylith.runtime.surfaces import host_dirty_checkpoint as ledger


def _event(**values):
    return {
        "kind": "implementation", "summary": "Retained complete work and its evidence.",
        "author": "assistant", "source": "assistant", "session_id": "native-session",
        "host_family": "codex", **values,
    }


def _record(repo, **values):
    event_id = ledger.record_compass_event(repo_root=repo, event=_event(**values))
    return event_id, ledger.read_compass_events(repo_root=repo)[-1]


def test_canonical_event_is_retained_without_semantic_rewriting(tmp_path):
    supplied = _event(
        kind="decision", summary="  Complete café narrative.\nSecond sentence.  ",
        ts_iso="2026-10-14T12:34:56-07:00", workstreams=["B-142"],
        intervention={"signals": [True, 1, 1.0], "claim": "unverified"},
    )
    event_id = ledger.record_compass_event(repo_root=tmp_path, event=supplied)
    row = ledger.read_compass_events(repo_root=tmp_path)[0]
    assert uuid.UUID(hex=event_id).hex == event_id
    assert row["event"] == {**supplied, "transaction_id": "host-event-" + event_id}
    assert row["session_id"] == supplied["session_id"] and row["host_family"] == "codex"
    assert row["version"] == 1 and row["source"] == "compass_event"
    assert datetime.fromisoformat(row["recorded_utc"]).tzinfo is not None
    assert "transaction_id" not in supplied
    assert ledger.read_dirty_events(repo_root=tmp_path) == []
    assert ledger.clear_dirty_events(repo_root=tmp_path, event_ids=[event_id]) is False
    assert ledger.read_compass_events(repo_root=tmp_path) == [row]


def test_stop_capture_retains_actual_session_and_full_summary(tmp_path):
    summary = "Implemented a complete statement. " + "Useful retained evidence. " * 20
    assert ledger.capture_stop_summary(
        repo_root=tmp_path, host_family="claude", session_id="actual-session",
        summary=summary, workstreams=["B-001", "B-002", "B-003", "B-004", "B-005"],
    ) is True
    row = ledger.read_compass_events(repo_root=tmp_path)[0]
    assert row["event"] == {
        "kind": "implementation", "summary": summary, "author": "assistant", "source": "assistant",
        "host_family": "claude", "session_id": "actual-session", "artifacts": [],
        "workstreams": ["B-001", "B-002", "B-003", "B-004"],
        "transaction_id": "host-event-" + row["id"], "ts_iso": row["event"]["ts_iso"],
    }
    assert datetime.fromisoformat(row["event"]["ts_iso"]).tzinfo is not None
    assert ledger.capture_stop_summary(
        repo_root=tmp_path, host_family="claude", session_id="actual-session", summary=" \n",
    ) is False
    assert ledger.read_compass_events(repo_root=tmp_path) == [row]


def test_transaction_identity_cannot_be_replaced_by_the_caller(tmp_path, monkeypatch):
    identity = uuid.UUID("1" * 32)
    monkeypatch.setattr(ledger.uuid, "uuid4", lambda: identity)
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.record_compass_event(repo_root=tmp_path, event=_event(transaction_id="different-event"))
    assert ledger.read_compass_events(repo_root=tmp_path) == []
    event_id = ledger.record_compass_event(
        repo_root=tmp_path, event=_event(transaction_id="host-event-" + identity.hex),
    )
    assert event_id == identity.hex


def test_success_is_after_exact_event_file_and_directory_fsync(tmp_path, monkeypatch):
    observed = []
    real_fsync = os.fsync

    def sync(descriptor):
        metadata = os.fstat(descriptor)
        if stat.S_ISREG(metadata.st_mode):
            row = json.loads(ledger.event_store_path(tmp_path).read_bytes())
            assert row["event"]["transaction_id"] == "host-event-" + row["id"]
            observed.append("event")
        else:
            observed.append("directory")
        real_fsync(descriptor)

    monkeypatch.setattr(ledger.os, "fsync", sync)
    _record(tmp_path)
    assert observed[-2:] == ["event", "directory"]


@pytest.mark.parametrize("failure", ["file", "directory"])
def test_durability_failure_is_visible_and_never_discards_written_event(tmp_path, monkeypatch, failure):
    real_fsync = os.fsync
    wrote_file = False

    def sync(descriptor):
        nonlocal wrote_file
        regular = stat.S_ISREG(os.fstat(descriptor).st_mode)
        if regular:
            wrote_file = True
        if (failure == "file" and regular) or (failure == "directory" and wrote_file and not regular):
            raise OSError("controlled durability failure")
        real_fsync(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(ledger.os, "fsync", sync)
        with pytest.raises(ledger.HostDirtyCheckpointError):
            ledger.capture_stop_summary(
                repo_root=tmp_path, host_family="codex", session_id="native", summary="Complete summary.",
            )
    rows = ledger.read_compass_events(repo_root=tmp_path)
    assert len(rows) == 1 and rows[0]["event"]["summary"] == "Complete summary."


def test_dirty_clear_preserves_compass_and_malformed_bytes_and_tightens_privacy(tmp_path, monkeypatch):
    dirty_id = ledger.record_dirty_event(
        repo_root=tmp_path, host_family=" CODEX ", session_id=" session ", source="checkpoint",
        paths=["src/a.py", "src/a.py"], governed_paths=["odylith/registry/source/example.md"],
    )
    event_id, row = _record(tmp_path)
    path = ledger.event_store_path(tmp_path)
    malformed = b'{"unfinished":\xff\n\n'
    path.write_bytes(path.read_bytes() + malformed)
    path.chmod(0o640)
    changes = []
    real_replace, real_fsync = os.replace, os.fsync

    def sync(descriptor):
        changes.append("file" if stat.S_ISREG(os.fstat(descriptor).st_mode) else "directory")
        real_fsync(descriptor)

    def replace(*args, **kwargs):
        changes.append("replace")
        return real_replace(*args, **kwargs)

    monkeypatch.setattr(ledger.os, "fsync", sync)
    monkeypatch.setattr(ledger.os, "replace", replace)
    assert [r["id"] for r in ledger.read_dirty_events(
        repo_root=tmp_path, host_family="codex", session_id="session",
    )] == [dirty_id]
    assert ledger.clear_dirty_events(repo_root=tmp_path, event_ids=[dirty_id, event_id]) is True
    assert path.read_bytes() == ledger._json_bytes(row) + b"\n" + malformed
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert changes == ["file", "replace", "directory"]
    with pytest.raises(ledger.HostDirtyCheckpointError, match="Malformed"):
        ledger.read_compass_events(repo_root=tmp_path)


@pytest.mark.parametrize("malformed", [
    b"not-json\n", b"[]\n", b'{"source":"compass_event","id":"missing"}\n',
    b'{"id":"unknown-schema"}\n', b'{"number":NaN}\n', b"\xff\n",
])
def test_strict_reader_refuses_malformed_rows_without_legacy_cleanup_erasing_them(tmp_path, malformed):
    dirty = ledger.record_dirty_event(repo_root=tmp_path, host_family="codex", source="test")
    _, row = _record(tmp_path)
    path = ledger.event_store_path(tmp_path)
    path.write_bytes(path.read_bytes() + malformed)
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.read_compass_events(repo_root=tmp_path)
    assert ledger.clear_dirty_events(repo_root=tmp_path, event_ids=[dirty, "missing", "unknown-schema"]) is True
    assert path.read_bytes() == ledger._json_bytes(row) + b"\n" + malformed


def test_acknowledgement_compares_exact_payload_and_cannot_remove_same_id_replacement(tmp_path):
    event_id, row = _record(tmp_path, details={"value": 1})
    replacement = {**row, "event": {**row["event"], "details": {"value": True}}}
    path = ledger.event_store_path(tmp_path)
    path.write_bytes(ledger._json_bytes(replacement) + b"\n")
    assert ledger.acknowledge_compass_event(repo_root=tmp_path, event_id=event_id, event=row["event"]) is False
    assert ledger.read_compass_events(repo_root=tmp_path) == [replacement]
    assert ledger.acknowledge_compass_event(repo_root=tmp_path, event_id=event_id, event=replacement["event"]) is True
    assert path.read_bytes() == b""
    assert ledger.acknowledge_compass_event(repo_root=tmp_path, event_id=event_id, event=replacement["event"]) is False


def test_duplicate_compass_id_is_retained_and_not_acknowledged(tmp_path):
    event_id, row = _record(tmp_path)
    path = ledger.event_store_path(tmp_path)
    data = path.read_bytes() * 2
    path.write_bytes(data)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="Duplicate"):
        ledger.read_compass_events(repo_root=tmp_path)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="Duplicate"):
        ledger.acknowledge_compass_event(repo_root=tmp_path, event_id=event_id, event=row["event"])
    assert path.read_bytes() == data


def test_new_compass_write_refuses_corrupt_ledger_without_mutation(tmp_path):
    _record(tmp_path)
    path = ledger.event_store_path(tmp_path)
    corrupted = path.read_bytes() + b"unfinished"
    path.write_bytes(corrupted)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="Malformed"):
        ledger.record_compass_event(repo_root=tmp_path, event=_event(summary="New event"))
    assert path.read_bytes() == corrupted


def test_duplicate_generated_identity_cannot_append_a_second_record(tmp_path, monkeypatch):
    identity = uuid.UUID("2" * 32)
    monkeypatch.setattr(ledger.uuid, "uuid4", lambda: identity)
    _, first = _record(tmp_path)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="already exists"):
        ledger.record_compass_event(repo_root=tmp_path, event=_event(summary="Different event"))
    assert ledger.read_compass_events(repo_root=tmp_path) == [first]


@pytest.mark.parametrize("part", [".odylith", "runtime", "host-hooks", "ledger", "lock"])
def test_symlink_owner_paths_are_refused_without_touching_external_target(tmp_path, part):
    external = tmp_path / "external"
    external.mkdir()
    target = external / "untouched"
    target.write_bytes(b"preserve\n")
    path = ledger.event_store_path(tmp_path)
    if part in {"ledger", "lock"}:
        path.parent.mkdir(parents=True)
        link = path if part == "ledger" else path.parent / ledger._LOCK_NAME
        link.symlink_to(target)
    else:
        parents = list(ledger.DIRTY_EVENTS_RELATIVE.parts[:-1])
        link = tmp_path.joinpath(*parents[:parents.index(part) + 1])
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(external, target_is_directory=True)
    before = {p.name: p.read_bytes() for p in external.iterdir()}
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.record_compass_event(repo_root=tmp_path, event=_event())
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.read_compass_events(repo_root=tmp_path)
    assert ledger.record_dirty_event(repo_root=tmp_path, host_family="codex", source="test") == ""
    assert ledger.read_dirty_events(repo_root=tmp_path) == []
    assert ledger.clear_dirty_events(repo_root=tmp_path, event_ids=["any"]) is False
    assert {p.name: p.read_bytes() for p in external.iterdir()} == before


def test_append_waits_for_acknowledgement_and_neither_event_is_lost(tmp_path, monkeypatch):
    old_id, old = _record(tmp_path)
    inside_rewrite, release, append_attempted = threading.Event(), threading.Event(), threading.Event()
    real_rewrite, real_lock = ledger._rewrite, ledger.fcntl.flock

    def rewrite(directory, data):
        inside_rewrite.set()
        assert release.wait(5), "acknowledgement was not released"
        real_rewrite(directory, data)

    def lock(descriptor, mode):
        if threading.current_thread().name.endswith("_1"):
            append_attempted.set()
        return real_lock(descriptor, mode)

    monkeypatch.setattr(ledger, "_rewrite", rewrite)
    monkeypatch.setattr(ledger.fcntl, "flock", lock)
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="ledger") as pool:
        ack = pool.submit(ledger.acknowledge_compass_event, repo_root=tmp_path, event_id=old_id, event=old["event"])
        try:
            assert inside_rewrite.wait(5)
            append = pool.submit(ledger.record_compass_event, repo_root=tmp_path, event=_event(summary="Concurrent event"))
            assert append_attempted.wait(5)
            assert not append.done()
        finally:
            release.set()
        assert ack.result(timeout=5) is True
        new_id = append.result(timeout=5)
    remaining = ledger.read_compass_events(repo_root=tmp_path)
    assert [row["id"] for row in remaining] == [new_id]
    assert remaining[0]["event"]["summary"] == "Concurrent event"


def test_owner_lock_serializes_a_separate_process(tmp_path):
    _record(tmp_path)
    attempted, completed = tmp_path / "attempted", tmp_path / "completed"
    source = Path(__file__).resolve().parents[3] / "src"
    script = (
        "import sys\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(source)!r})\n"
        "from odylith.runtime.surfaces import host_dirty_checkpoint as ledger\n"
        "real = ledger.fcntl.flock\n"
        f"def lock(fd, mode):\n    Path({str(attempted)!r}).write_text('attempt')\n    return real(fd, mode)\n"
        "ledger.fcntl.flock = lock\n"
        f"event_id = ledger.record_compass_event(repo_root={str(tmp_path)!r}, "
        "event={'kind':'decision','summary':'Child event','host_family':'codex','session_id':'child-session'})\n"
        f"Path({str(completed)!r}).write_text(event_id)\n"
    )
    process = None
    try:
        with ledger._locked_store(tmp_path):
            process = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            until = time.monotonic() + 5
            while not attempted.exists() and time.monotonic() < until:
                time.sleep(0.01)
            assert attempted.exists(), "child never reached the real lock"
            assert process.poll() is None and not completed.exists()
        _, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        assert completed.read_text() in {row["id"] for row in ledger.read_compass_events(repo_root=tmp_path)}
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_append_tightens_existing_ledger_before_durable_success(tmp_path, monkeypatch):
    dirty_id = ledger.record_dirty_event(repo_root=tmp_path, host_family="codex", source="checkpoint")
    path = ledger.event_store_path(tmp_path)
    previous = path.read_bytes()
    path.chmod(0o644)
    real_fsync = os.fsync
    seen_private = []

    def sync(descriptor):
        metadata = os.fstat(descriptor)
        if stat.S_ISREG(metadata.st_mode):
            seen_private.append(stat.S_IMODE(metadata.st_mode))
        real_fsync(descriptor)

    monkeypatch.setattr(ledger.os, "fsync", sync)
    _record(tmp_path)
    assert seen_private == [0o600]
    assert path.read_bytes().startswith(previous)
    assert [row["id"] for row in ledger.read_dirty_events(repo_root=tmp_path)] == [dirty_id]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize("field,value", [
    ("kind", "unknown_event"), ("kind", ["implementation"]),
    ("summary", "  "), ("ts_iso", "not-a-time"), ("ts_iso", "2026-10-14T12:00:00"),
    ("session_id", ""), ("session_id", "  "), ("session_id", 1),
    ("host_family", "other"), ("host_family", ["codex"]),
    ("workstreams", "B-001"), ("workstreams", [1]), ("artifacts", {}),
    ("components", [None]), ("action_surfaces", "chat"), ("semantic_signature", [False]),
    ("metadata", []), ("deployment_truth", "unknown"), ("author", {}), ("source", 1),
])
def test_invalid_canonical_fields_are_refused_on_write_and_read_without_loss(tmp_path, field, value):
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.record_compass_event(repo_root=tmp_path, event=_event(**{field: value}))
    assert not ledger.event_store_path(tmp_path).exists()
    _, row = _record(tmp_path)
    row["event"][field] = value
    data = ledger._json_bytes(row) + b"\n"
    path = ledger.event_store_path(tmp_path)
    path.write_bytes(data)
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.read_compass_events(repo_root=tmp_path)
    assert path.read_bytes() == data


@pytest.mark.parametrize("recorded_utc", ["invalid", "2026-10-14T12:00:00", None])
def test_malformed_persistence_timestamp_is_retained_and_reported(tmp_path, recorded_utc):
    _, row = _record(tmp_path)
    row["recorded_utc"] = recorded_utc
    path = ledger.event_store_path(tmp_path)
    data = ledger._json_bytes(row) + b"\n"
    path.write_bytes(data)
    with pytest.raises(ledger.HostDirtyCheckpointError):
        ledger.read_compass_events(repo_root=tmp_path)
    assert path.read_bytes() == data


def test_actual_intervention_kind_and_payload_are_retained(tmp_path):
    from odylith.runtime.common.log_compass_timeline_event import _KIND_CHOICES
    from odylith.runtime.intervention_engine.stream_state import _INTERVENTION_EVENT_KINDS

    assert ledger._LOG_EVENT_KINDS == frozenset(_KIND_CHOICES)
    assert "capture_applied" in _INTERVENTION_EVENT_KINDS
    supplied = _event(
        kind="capture_applied", host_family="claude", ts_iso="2026-10-14T19:00:00Z",
        workstreams=["B-142"], artifacts=["src/evidence.py"], components=["odylith"],
        action_surfaces=["chat"], semantic_signature=["capture", "accepted"],
        metadata={"proposal_id": "proposal-123", "verified": False},
        delivery_channel="native_chat", display_markdown="**Useful decision**",
    )
    event_id = ledger.record_compass_event(repo_root=tmp_path, event=supplied)
    assert ledger.read_compass_events(repo_root=tmp_path)[0]["event"] == {
        **supplied, "transaction_id": "host-event-" + event_id,
    }


@pytest.mark.parametrize("kind", ["decision", "implementation", "statement", "update", "ambient_signal"])
def test_empty_summary_is_not_accepted_for_non_lifecycle_events(tmp_path, kind):
    with pytest.raises(ledger.HostDirtyCheckpointError, match="Malformed"):
        ledger.record_compass_event(repo_root=tmp_path, event=_event(kind=kind, summary=""))
    assert ledger.read_compass_events(repo_root=tmp_path) == []


def test_event_size_boundary_refuses_overflow_without_clipping_or_mutation(tmp_path, monkeypatch):
    assert ledger.MAX_COMPASS_EVENT_BYTES == 1024 * 1024
    identity = uuid.UUID("3" * 32)
    monkeypatch.setattr(ledger.uuid, "uuid4", lambda: identity)
    event = _event(ts_iso="2026-10-14T19:00:00Z", transaction_id="host-event-" + identity.hex)
    event["summary"] += "x" * (ledger.MAX_COMPASS_EVENT_BYTES - len(ledger._json_bytes(event)))
    assert len(ledger._json_bytes(event)) == ledger.MAX_COMPASS_EVENT_BYTES
    ledger.record_compass_event(repo_root=tmp_path, event=event)
    row = ledger.read_compass_events(repo_root=tmp_path)[0]
    assert row["event"] == event
    path = ledger.event_store_path(tmp_path)
    original = path.read_bytes()
    event["summary"] += "x"
    with pytest.raises(ledger.HostDirtyCheckpointError, match="size bound"):
        ledger.record_compass_event(repo_root=tmp_path, event=event)
    assert path.read_bytes() == original
    row["event"] = event
    oversized = ledger._json_bytes(row) + b"\n"
    path.write_bytes(oversized)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="size bound"):
        ledger.read_compass_events(repo_root=tmp_path)
    assert path.read_bytes() == oversized


def test_oversized_ledger_is_refused_explicitly_and_retained(tmp_path):
    assert ledger.MAX_LEDGER_BYTES == 16 * 1024 * 1024
    event_id, row = _record(tmp_path)
    path = ledger.event_store_path(tmp_path)
    with path.open("r+b") as handle:
        handle.truncate(ledger.MAX_LEDGER_BYTES + 1)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ledger.HostDirtyCheckpointError, match="read bound"):
        ledger.read_compass_events(repo_root=tmp_path)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="read bound"):
        ledger.record_compass_event(repo_root=tmp_path, event=_event())
    with pytest.raises(ledger.HostDirtyCheckpointError, match="read bound"):
        ledger.acknowledge_compass_event(repo_root=tmp_path, event_id=event_id, event=row["event"])
    assert ledger.clear_dirty_events(repo_root=tmp_path, event_ids=[event_id]) is False
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original


def test_append_cannot_cross_ledger_bound_or_lose_existing_event(tmp_path, monkeypatch):
    _, row = _record(tmp_path)
    path = ledger.event_store_path(tmp_path)
    original = path.read_bytes()
    monkeypatch.setattr(ledger, "MAX_LEDGER_BYTES", len(original) + 1)
    with pytest.raises(ledger.HostDirtyCheckpointError, match="write bound"):
        ledger.record_compass_event(repo_root=tmp_path, event=_event(summary="Second event"))
    assert path.read_bytes() == original
    assert ledger.read_compass_events(repo_root=tmp_path) == [row]
