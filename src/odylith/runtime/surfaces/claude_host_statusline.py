"""Claude Code statusline renderer for the Odylith-grounded posture.

Claude Code renders the statusline output inline and silently swallows any
error written to stderr. This module therefore must never raise from the
render path: every failure mode must degrade to a safe, clearly-marked
fallback string so the statusline never goes blank.

The module is invoked through ``odylith claude statusline`` from a one-line
``.claude/statusline.sh`` exec shim. It reads the Compass runtime snapshot,
picks the active workstream and brief freshness, and returns a compact
one-line string that shows the user the active Odylith slice and the host
family at a glance.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import claude_host_shared


SAFE_FALLBACK_STATUSLINE = "Odylith · grounding unavailable"


def _workstream_label(payload: Mapping[str, Any] | None) -> str:
    workstream = claude_host_shared.active_workstream_from_runtime(payload)
    if workstream:
        return workstream
    return "no active workstream"


def _compact_host_family() -> str:
    host = claude_host_shared.detect_host_family()
    return host or "unknown"


def render_claude_host_statusline(repo_root: Path | str = ".") -> str:
    """Return a compact Odylith-grounded Claude Code statusline string.

    This entry point must never raise. Every failure mode, including a
    missing Compass runtime snapshot, a malformed JSON payload, or an
    unresolvable repo root, degrades to :data:`SAFE_FALLBACK_STATUSLINE`.
    Claude Code swallows stderr, so the statusline must never go blank on
    a grounded repo.
    """
    try:
        payload = claude_host_shared.load_compass_runtime(repo_root)
        workstream = _workstream_label(payload)
        freshness = claude_host_shared.freshness_label(payload)
        host = _compact_host_family()
        return f"Odylith · {workstream} · brief {freshness} · host {host}"
    except Exception:  # pragma: no cover - defensive safety net
        return SAFE_FALLBACK_STATUSLINE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude statusline",
        description="Render the Odylith-grounded Claude Code statusline.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass runtime resolution.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    sys.stdout.write(render_claude_host_statusline(args.repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
