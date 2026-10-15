from __future__ import annotations

import io
import json
from pathlib import Path
import stat

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.surfaces import claude_host_shared, claude_host_subagent_stop, host_dirty_checkpoint
from tests.unit.runtime.test_compass_log_continuation import _publish_prefix
from tests.unit.runtime.test_greenfield_managed_mutation_boundary import _active_repository


def test_build_event_extracts_workstreams_and_summary() -> None:
    payload = {
        "agent_id": "agent-123",
        "agent_type": "odylith-workstream",
        "session_id": "session-456",
        "last_assistant_message": (
            "Updated the scoped CLAUDE companions and validated the focused bundle "
            "and install tests for B-083."
        ),
    }

    event = claude_host_subagent_stop.build_event(payload=payload)

    assert event["kind"] == "subagent_stop"
    assert event["host_family"] == "claude"
    assert event["agent_type"] == "odylith-workstream"
    assert event["agent_id"] == "agent-123"
    assert event["session_id"] == "session-456"
    assert event["workstreams"] == ["B-083"]
    assert "validated the focused bundle" in event["summary"]
    assert event["ts_iso"]


def test_build_event_handles_question_shaped_messages_gracefully() -> None:
    payload = {
        "agent_type": "odylith-workstream",
        "last_assistant_message": "Would you like me to continue with the next slice?",
    }

    event = claude_host_subagent_stop.build_event(payload=payload)

    assert event["kind"] == "subagent_stop"
    assert event["summary"] == ""
    assert event["workstreams"] == []


def test_main_appends_event_to_agent_stream(monkeypatch, tmp_path: Path) -> None:
    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "agent_id": "agent-123",
                    "agent_type": "odylith-workstream",
                    "session_id": "session-456",
                    "last_assistant_message": (
                        "Updated the scoped CLAUDE companions and validated the focused bundle "
                        "and install tests for B-083."
                    ),
                }
            )
        ),
    )

    exit_code = claude_host_subagent_stop.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    stream_path = runtime_dir / "agent-stream.v1.jsonl"
    rows = [
        json.loads(line)
        for line in stream_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    event = rows[0]
    assert event["kind"] == "subagent_stop"
    assert event["agent_type"] == "odylith-workstream"
    assert event["workstreams"] == ["B-083"]


@pytest.fixture
def active_publication(tmp_path: Path):
    repo, _ = _active_repository(tmp_path)
    _publish_prefix(repo)
    generation = generations.require_greenfield_working_generation(repo)
    return repo, generation


def _files(directory: Path) -> dict[str, tuple[bytes, int]]:
    return {str(path.relative_to(directory)): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("message", [
    "Updated the scoped CLAUDE companions and validated the focused bundle and install tests for B-083.",
    "Would you like me to continue with B-083?",
], ids=["meaningful-summary", "blank-summary"])
def test_native_subagent_stop_retains_exact_event_without_changing_active_publication(
    monkeypatch, capsys, active_publication, message: str,
) -> None:
    repo, generation = active_publication
    canonical_before = _files(repo / "odylith")
    published_before = _files(generation.repository_root)
    payload = {
        "hook_event_name": "SubagentStop", "cwd": str(repo),
        "session_id": "native-parent-session", "agent_id": "native-subagent-123",
        "agent_type": "odylith-workstream", "agent_name": "bounded-worker",
        "transcript_path": str(repo / "parent.jsonl"),
        "agent_transcript_path": str(repo / "subagent.jsonl"),
        "stop_reason": "end_turn", "last_assistant_message": message,
    }
    monkeypatch.setattr(claude_host_shared, "utc_now_iso", lambda: "2026-10-14T22:00:00Z")
    expected = claude_host_subagent_stop.build_event(payload=payload)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))

    assert claude_host_subagent_stop.main(["--repo-root", str(repo)]) == 0

    records = host_dirty_checkpoint.read_compass_events(repo_root=repo)
    assert len(records) == 1
    record = records[0]
    assert record["host_family"] == "claude" and record["session_id"] == "native-parent-session"
    assert record["event"] == {**expected, "transaction_id": "host-event-" + record["id"]}
    assert record["event"]["source"] == "claude_hook"
    assert record["event"]["agent_id"] == "native-subagent-123"
    assert record["event"]["stop_reason"] == "end_turn"
    assert record["event"]["workstreams"] == ["B-083"]
    if message.startswith("Would"):
        assert record["event"]["summary"] == ""
    else:
        assert record["event"]["summary"] == message
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == records
    assert _files(repo / "odylith") == canonical_before
    assert _files(generation.repository_root) == published_before
    assert generations.require_greenfield_working_generation(repo).write_set_hash == generation.write_set_hash
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_native_subagent_stop_reports_capture_refusal_without_claiming_saved_event(
    monkeypatch, capsys, active_publication,
) -> None:
    repo, generation = active_publication
    canonical_before = _files(repo / "odylith")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({
        "session_id": "native-parent-session", "agent_id": "native-subagent-123",
        "last_assistant_message": "Updated the subagent completion capture and validated the focused tests.",
    })))
    monkeypatch.setattr(host_dirty_checkpoint, "record_compass_event", lambda **kwargs: (
        _ for _ in ()).throw(host_dirty_checkpoint.HostDirtyCheckpointError("fsync refused")))

    assert claude_host_subagent_stop.main(["--repo-root", str(repo)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Odylith could not save this subagent's completion event.\n"
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == []
    assert _files(repo / "odylith") == canonical_before
    assert generations.require_greenfield_working_generation(repo).write_set_hash == generation.write_set_hash


@pytest.mark.parametrize("damage, expected_error", [
    ("corrupt-envelope", ValueError), ("missing-entry", RuntimeError),
])
def test_native_subagent_stop_refuses_broken_publication_without_append_fallback(
    monkeypatch, capsys, active_publication, damage: str, expected_error: type[Exception],
) -> None:
    repo, generation = active_publication
    payload = {
        "session_id": "native-parent-session", "agent_id": "native-subagent-123",
        "last_assistant_message": "Updated the subagent completion capture and validated the focused tests.",
    }
    host_dirty_checkpoint.record_compass_event(
        repo_root=repo, event=claude_host_subagent_stop.build_event(payload=payload),
    )
    ledger = host_dirty_checkpoint.compass_event_store_path(repo)
    pending_before = ledger.read_bytes()
    entry = repo / "odylith/index.html"
    if damage == "corrupt-envelope":
        entry.write_text("<!doctype html>odylith-publication: invalid envelope")
    else:
        entry.unlink()
    with pytest.raises(expected_error):
        publication.read_active_publication(repo)
    canonical_before = _files(repo / "odylith")
    published_before = _files(generation.repository_root)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))

    assert claude_host_subagent_stop.main(["--repo-root", str(repo)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Odylith could not save this subagent's completion event.\n"
    assert ledger.read_bytes() == pending_before
    assert _files(repo / "odylith") == canonical_before
    assert _files(generation.repository_root) == published_before
