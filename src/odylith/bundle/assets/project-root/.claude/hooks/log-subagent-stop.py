#!/usr/bin/env python3
"""Claude stop hook that records bounded subagent closeout events."""

from __future__ import annotations

from pathlib import Path
import sys

from odylith_claude_support import append_agent_stream_event
from odylith_claude_support import extract_workstreams
from odylith_claude_support import load_payload
from odylith_claude_support import meaningful_stop_summary
from odylith_claude_support import utc_now_iso


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    payload = load_payload()
    last_message = str(payload.get("last_assistant_message", ""))
    summary = meaningful_stop_summary(last_message)
    event = {
        "ts_iso": utc_now_iso(),
        "kind": "subagent_stop",
        "source": "claude_hook",
        "hook_event_name": str(payload.get("hook_event_name", "")).strip() or "SubagentStop",
        "cwd": str(payload.get("cwd", "")).strip(),
        "session_id": str(payload.get("session_id", "")).strip(),
        "agent_id": str(payload.get("agent_id", "")).strip(),
        "agent_type": str(payload.get("agent_type", "")).strip(),
        "transcript_path": str(payload.get("transcript_path", "")).strip(),
        "agent_transcript_path": str(payload.get("agent_transcript_path", "")).strip(),
        "subagent_name": str(payload.get("agent_name", "")).strip() or str(payload.get("subagent_name", "")).strip(),
        "stop_reason": str(payload.get("stop_reason", "")).strip() or str(payload.get("reason", "")).strip(),
        "summary": summary,
        "workstreams": extract_workstreams(summary or last_message),
    }
    append_agent_stream_event(project_dir=project_dir, event=event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
