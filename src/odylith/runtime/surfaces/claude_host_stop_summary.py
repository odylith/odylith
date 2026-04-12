"""Claude Code Stop hook: meaningful stop-summary Compass log.

When a Claude Code turn ends, the ``Stop`` hook fires with the
assistant's last message. This baked module mirrors the legacy
``.claude/hooks/log-stop-summary.py`` script. It filters out trivial,
question-shaped, or offer-shaped stop messages and only logs a Compass
``implementation`` event when the message looks like a real action
summary (action verb present, length above the noise floor, no
``Would you like ...`` opening).

The hook never blocks the turn-ending event. All failures degrade to
a no-op return so a missing launcher, missing snapshot, or unparseable
payload never breaks Claude Code's stop dispatch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from odylith.runtime.surfaces import claude_host_shared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude stop-summary",
        description="Log meaningful Claude stop summaries to Compass.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass log dispatch.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude Stop payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    if bool(payload.get("stop_hook_active")):
        return 0
    summary = claude_host_shared.meaningful_stop_summary(
        str(payload.get("last_assistant_message", ""))
    )
    if not summary:
        return 0
    workstreams = claude_host_shared.extract_workstreams(summary)
    claude_host_shared.run_compass_log(
        project_dir=repo_root,
        summary=summary,
        workstreams=workstreams,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
