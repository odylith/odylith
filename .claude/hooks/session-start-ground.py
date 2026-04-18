#!/usr/bin/env python3
"""Claude session-start hook that grounds Odylith context."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from odylith_claude_support import load_runtime_snapshot
from odylith_claude_support import run_odylith
from odylith_claude_support import write_project_memory


def _summary_from_output(output: str) -> str:
    text = str(output or "").strip()
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    prefix: list[str] = []
    payload_text = ""
    for line in lines:
        if line.startswith("{"):
            payload_text = "\n".join(lines[lines.index(line) :])
            break
        prefix.append(line)
    summary: list[str] = []
    if prefix:
        summary.append(" ".join(prefix[:2]))
    if payload_text:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            selection_reason = str(payload.get("selection_reason", "")).strip()
            if selection_reason:
                summary.append(f"selection: {selection_reason}")
            docs = payload.get("relevant_docs")
            if isinstance(docs, list) and docs:
                summary.append(f"relevant doc: {docs[0]}")
            commands = payload.get("recommended_commands")
            if isinstance(commands, list) and commands:
                summary.append(f"next command: {commands[0]}")
    return "\n".join(f"Odylith startup: {line}" for line in summary if line).strip()


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    completed = run_odylith(project_dir=project_dir, args=["start", "--repo-root", "."], timeout=20)
    if completed is None:
        return 0
    summary = _summary_from_output(completed.stdout)
    write_project_memory(
        project_dir=project_dir,
        snapshot=load_runtime_snapshot(project_dir),
        start_output=summary,
    )
    if summary:
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
