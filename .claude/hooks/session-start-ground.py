#!/usr/bin/env python3
# ruff: noqa
"""Claude session-start hook that grounds Odylith context."""

from __future__ import annotations

import json
import os
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


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().casefold() in {"1", "true", "yes", "on"}


def _summary_from_snapshot(snapshot: dict) -> str:
    if not isinstance(snapshot, dict) or not snapshot:
        return ""
    summary: list[str] = []
    focus = snapshot.get("execution_focus")
    global_focus = focus.get("global") if isinstance(focus, dict) else {}
    headline = str(global_focus.get("headline") or "").strip() if isinstance(global_focus, dict) else ""
    if headline:
        summary.append(f"snapshot: {' '.join(headline.split())}")
    active = global_focus.get("workstreams") if isinstance(global_focus, dict) else []
    if isinstance(active, list):
        tokens = [str(token or "").strip().upper() for token in active if str(token or "").strip()]
        if tokens:
            summary.append(f"active: {', '.join(tokens[:3])}")
    if snapshot.get("generated_utc"):
        summary.append("freshness: cached")
    return "\n".join(f"Odylith startup: {line}" for line in summary if line).strip()


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    snapshot = load_runtime_snapshot(project_dir)
    if _env_truthy("ODYLITH_HOOK_EAGER_START"):
        completed = run_odylith(project_dir=project_dir, args=["start", "--repo-root", "."], timeout=20)
        if completed is None:
            return 0
        summary = _summary_from_output(completed.stdout)
    else:
        summary = _summary_from_snapshot(snapshot)
    write_project_memory(
        project_dir=project_dir,
        snapshot=snapshot,
        start_output=summary,
    )
    if summary and _env_truthy("ODYLITH_HOOK_SESSION_START_STDOUT"):
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
