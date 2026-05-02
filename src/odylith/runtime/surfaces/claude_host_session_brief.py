"""Claude Code SessionStart hook: Odylith-grounded startup brief.

Claude Code fires the ``SessionStart`` hook when a project session begins
(or after a compact resume). This module mirrors the legacy
``.claude/hooks/session-start-ground.py`` script as a first-class baked
runtime entry, invoked through ``odylith claude session-start`` from
``.claude/settings.json``.

The baked module reads the live Compass runtime snapshot, adds a compact
substrate proof from already-local runtime summaries, and materializes the
auto-memory ``odylith-governed-brief.md`` note. Installed hooks pass
``--quiet`` so Claude does not receive the same brief twice; explicit CLI use
can still print the compact ``Odylith startup: ...`` summary. Failures degrade
to a no-op return so Claude Code's session start is never blocked by Odylith.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import host_intervention_support
from odylith.runtime.surfaces import session_brief_refresh_queue

_BRIEF_STALENESS_THRESHOLD_SECONDS = 4 * 60 * 60  # 4 hours
_CURRENT_RUNTIME_PATH = "odylith/compass/runtime/current.v1.json"


_STARTUP_PREFIX = "Odylith startup"


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().casefold() in {"1", "true", "yes", "on"}


def _summary_from_start_output(output: str) -> str:
    """Render a compact ``Odylith startup: ...`` summary from `odylith start`."""
    text = str(output or "").strip()
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    prefix: list[str] = []
    payload_text = ""
    for index, line in enumerate(lines):
        if line.startswith("{"):
            payload_text = "\n".join(lines[index:])
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
        if isinstance(payload, Mapping):
            selection_reason = str(payload.get("selection_reason", "")).strip()
            if selection_reason:
                summary.append(f"selection: {selection_reason}")
            docs = payload.get("relevant_docs")
            if isinstance(docs, list) and docs:
                summary.append(f"relevant doc: {docs[0]}")
            commands = payload.get("recommended_commands")
            if isinstance(commands, list) and commands:
                summary.append(f"next command: {commands[0]}")
    rendered = "\n".join(f"{_STARTUP_PREFIX}: {line}" for line in summary if line).strip()
    if rendered:
        return (
            f"{rendered}\n"
            f"{_STARTUP_PREFIX}: interventions armed for Observation, Proposal, and Assist; run `odylith claude intervention-status` if chat stays quiet."
        )
    return ""


def _summary_from_snapshot(
    snapshot: Mapping[str, Any] | None,
    *,
    substrate_context: str = "",
) -> str:
    """Render a compact startup summary without shelling out to `odylith start`."""
    substrate = str(substrate_context or "").strip()
    if not isinstance(snapshot, Mapping) or not snapshot:
        return substrate
    summary: list[str] = []
    headline = claude_host_shared.active_workstream_headline(snapshot)
    if headline:
        summary.append(f"snapshot: {headline}")
    active_lines = claude_host_shared.active_workstream_lines(snapshot)
    if active_lines:
        active = ", ".join(line.removeprefix("- ").strip() for line in active_lines[:3])
        summary.append(f"active: {active}")
    freshness = claude_host_shared.freshness_label(snapshot)
    if freshness:
        summary.append(f"freshness: {freshness}")
    rendered = "\n".join(f"{_STARTUP_PREFIX}: {line}" for line in summary if line).strip()
    if rendered:
        if substrate:
            rendered = f"{rendered}\n{substrate}"
        return rendered
    return ""


def render_session_brief(
    *,
    repo_root: Path | str = ".",
    snapshot_override: Mapping[str, Any] | None = None,
    start_output_override: str | None = None,
    eager_start: bool = False,
) -> str:
    """Pure renderer used by the live hook and by tests."""
    if start_output_override is not None:
        return _summary_from_start_output(start_output_override)
    if not eager_start and not _env_truthy("ODYLITH_HOOK_EAGER_START"):
        snapshot = snapshot_override if snapshot_override is not None else claude_host_shared.load_runtime_snapshot(repo_root)
        substrate = host_intervention_support.session_start_substrate_context(
            repo_root=repo_root,
            host_family="claude",
        )
        return _summary_from_snapshot(snapshot, substrate_context=substrate)
    completed = claude_host_shared.run_odylith(
        project_dir=repo_root,
        args=["start", "--repo-root", "."],
        timeout=20,
    )
    if completed is None:
        return ""
    return _summary_from_start_output(completed.stdout or "")


def _queue_refresh_if_briefs_stale(*, repo_root: Path) -> None:
    """Queue one background Compass refresh when the current brief is stale."""
    session_brief_refresh_queue.queue_refresh_if_briefs_stale(
        repo_root=repo_root,
        threshold_seconds=_BRIEF_STALENESS_THRESHOLD_SECONDS,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude session-start",
        description="Render the Odylith-grounded Claude SessionStart hook output.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass runtime resolution.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the printed summary even when one is computed.",
    )
    parser.add_argument(
        "--eager-start",
        action="store_true",
        help="Run `odylith start` during SessionStart instead of the cached fast path.",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    summary = render_session_brief(repo_root=repo_root, eager_start=bool(args.eager_start))
    snapshot = claude_host_shared.load_runtime_snapshot(repo_root)
    claude_host_shared.write_project_memory(
        project_dir=repo_root,
        snapshot=snapshot,
        start_output=summary,
    )
    _queue_refresh_if_briefs_stale(repo_root=repo_root)
    if summary and not args.quiet:
        sys.stdout.write(summary + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
