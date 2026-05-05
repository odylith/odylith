"""Codex SessionStart hook renderer for the active Odylith slice."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import codex_host_shared
from odylith.runtime.surfaces import host_startup_summary
from odylith.runtime.surfaces import host_intervention_support
from odylith.runtime.surfaces import session_brief_refresh_queue

_BRIEF_STALENESS_THRESHOLD_SECONDS = 4 * 60 * 60  # 4 hours
_CURRENT_RUNTIME_PATH = "odylith/compass/runtime/current.v1.json"


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().casefold() in {"1", "true", "yes", "on"}


def _startup_summary_for_chat(startup_source: str) -> str:
    text = str(startup_source or "").strip()
    if not text:
        return ""
    if host_startup_summary.startup_output_needs_narrowing(text):
        return host_startup_summary.narrowing_chat_summary()
    return codex_host_shared.collapse_whitespace(text, limit=480)


def render_codex_session_brief(
    repo_root: Path | str = ".",
    *,
    payload_override: Mapping[str, Any] | None = None,
    start_summary_override: str = "",
    eager_start: bool = False,
) -> str:
    payload = payload_override if payload_override is not None else codex_host_shared.load_compass_runtime(repo_root)
    lines: list[str] = ["Odylith grounded brief for this Codex session."]
    lines.append(
        "Interventions: Observation, Proposal, and Assist are armed through hook output plus assistant-visible recovery; run `odylith codex intervention-status` if chat stays quiet."
    )
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
    startup_source = start_summary_override
    if not startup_source and (eager_start or _env_truthy("ODYLITH_HOOK_EAGER_START")):
        startup_source = codex_host_shared.start_summary(project_dir=repo_root)
    if not startup_source:
        startup_source = host_intervention_support.session_start_substrate_context(
            repo_root=repo_root,
            host_family="codex",
        )
    startup = _startup_summary_for_chat(startup_source)
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
    parser.add_argument(
        "--eager-start",
        action="store_true",
        help="Run `odylith start` during SessionStart instead of the cached fast path.",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = Path(args.repo_root).expanduser().resolve()
    summary = render_codex_session_brief(repo_root, eager_start=bool(args.eager_start))
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
