"""Claude Code SubagentStop hook: append a Compass agent-stream event.

When a Claude Task-tool subagent finishes, the ``SubagentStop`` hook
fires with the subagent's transcript metadata. This baked module mirrors
the legacy ``.claude/hooks/log-subagent-stop.py`` script. It builds a
canonical agent-stream event (subagent id, type, stop reason, summary,
extracted workstreams) and appends it to
``odylith/compass/runtime/agent-stream.v1.jsonl`` so the Compass
timeline accumulates evidence about delegated work.

The hook never blocks the subagent's exit. All failures degrade to a
no-op return so a missing snapshot, missing runtime directory, or
unparseable payload never breaks the Task-tool dispatch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from odylith.runtime.surfaces import claude_host_shared


def build_event(*, payload: dict) -> dict:
    """Render the canonical Compass agent-stream event for a SubagentStop payload."""
    if not isinstance(payload, dict):
        payload = {}
    last_message = str(payload.get("last_assistant_message", ""))
    summary = claude_host_shared.meaningful_stop_summary(last_message)
    workstreams = claude_host_shared.extract_workstreams(summary or last_message)
    return {
        "ts_iso": claude_host_shared.utc_now_iso(),
        "kind": "subagent_stop",
        "source": "claude_hook",
        "hook_event_name": str(payload.get("hook_event_name", "")).strip() or "SubagentStop",
        "cwd": str(payload.get("cwd", "")).strip(),
        "session_id": str(payload.get("session_id", "")).strip(),
        "agent_id": str(payload.get("agent_id", "")).strip(),
        "agent_type": str(payload.get("agent_type", "")).strip(),
        "transcript_path": str(payload.get("transcript_path", "")).strip(),
        "agent_transcript_path": str(payload.get("agent_transcript_path", "")).strip(),
        "subagent_name": str(payload.get("agent_name", "")).strip()
        or str(payload.get("subagent_name", "")).strip(),
        "stop_reason": str(payload.get("stop_reason", "")).strip()
        or str(payload.get("reason", "")).strip(),
        "summary": summary,
        "workstreams": workstreams,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude subagent-stop",
        description="Append a Compass agent-stream event for a Claude SubagentStop hook payload.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for the Compass agent stream.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude SubagentStop payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    event = build_event(payload=payload)
    claude_host_shared.append_agent_stream_event(project_dir=repo_root, event=event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
