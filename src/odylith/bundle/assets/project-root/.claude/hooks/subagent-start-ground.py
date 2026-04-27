#!/usr/bin/env python3
"""Claude subagent-start hook that injects grounded context."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from odylith_claude_support import build_subagent_context
from odylith_claude_support import load_payload


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    payload = load_payload()
    agent_type = str(payload.get("agent_type", "")).strip()
    additional_context = build_subagent_context(project_dir=project_dir, agent_type=agent_type)
    if not additional_context:
        return 0
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": additional_context,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
