"""Codex SessionStart hook renderer for the active Odylith slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import codex_host_shared
from odylith.runtime.surfaces import session_brief_refresh_queue

_BRIEF_STALENESS_THRESHOLD_SECONDS = 4 * 60 * 60  # 4 hours
_CURRENT_RUNTIME_PATH = "odylith/compass/runtime/current.v1.json"


def render_codex_session_brief(
    repo_root: Path | str = ".",
    *,
    payload_override: Mapping[str, Any] | None = None,
    start_summary_override: str = "",
) -> str:
    payload = payload_override if payload_override is not None else codex_host_shared.load_compass_runtime(repo_root)
    lines: list[str] = ["Odylith grounded brief for this Codex session."]
    headline = codex_host_shared.active_workstream_headline(payload)
    if headline:
        lines.append(f"Headline: {headline}")
    active = codex_host_shared.active_workstreams(payload)
    if active:
        lines.append(f"Active workstreams: {', '.join(active)}")
    else:
        lines.append("Active workstreams: (not present in Compass runtime snapshot)")
    lines.append(f"Brief freshness: {codex_host_shared.freshness_label(payload)}")
    next_actions = codex_host_shared.next_action_lines(payload)
    if next_actions:
        lines.append("Next actions:")
        lines.extend(next_actions)
    risks = codex_host_shared.risk_lines(payload)
    if risks:
        lines.append("Risks:")
        lines.extend(risks)
    startup = codex_host_shared.collapse_whitespace(
        start_summary_override or codex_host_shared.start_summary(project_dir=repo_root),
        limit=240,
    )
    if startup:
        lines.append(f"Startup: {startup}")
    return "\n".join(lines).rstrip()


def _queue_refresh_if_briefs_stale(*, repo_root: Path) -> None:
    """Check if the global standup briefs are older than 4 hours and queue one background refresh."""
    session_brief_refresh_queue.queue_refresh_if_briefs_stale(
        repo_root=repo_root,
        threshold_seconds=_BRIEF_STALENESS_THRESHOLD_SECONDS,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex session-start-ground",
        description="Render the Odylith-grounded SessionStart hook output for Codex.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass runtime resolution.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = Path(args.repo_root).expanduser().resolve()
    summary = render_codex_session_brief(repo_root)
    _queue_refresh_if_briefs_stale(repo_root=repo_root)
    if not summary:
        return 0
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": summary,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
