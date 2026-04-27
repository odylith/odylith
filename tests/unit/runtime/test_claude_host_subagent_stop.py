from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.surfaces import claude_host_subagent_stop


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
