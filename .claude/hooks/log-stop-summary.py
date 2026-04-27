#!/usr/bin/env python3
"""Claude stop hook that records meaningful stop summaries."""

from __future__ import annotations

from pathlib import Path
import sys

from odylith_claude_support import extract_workstreams
from odylith_claude_support import load_payload
from odylith_claude_support import meaningful_stop_summary
from odylith_claude_support import run_compass_log


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    payload = load_payload()
    if bool(payload.get("stop_hook_active")):
        return 0
    summary = meaningful_stop_summary(str(payload.get("last_assistant_message", "")))
    if not summary:
        return 0
    run_compass_log(project_dir=project_dir, summary=summary, workstreams=extract_workstreams(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
