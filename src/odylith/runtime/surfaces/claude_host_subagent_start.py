"""Claude Code SubagentStart hook: inject Odylith grounding into delegated leaves.

Claude Code fires the ``SubagentStart`` hook just before a Task-tool
subagent runs. This baked module mirrors the legacy
``.claude/hooks/subagent-start-ground.py`` script as a first-class entry,
invoked through ``odylith claude subagent-start``. It reads the Claude
hook payload from stdin, derives the active Odylith slice from the
Compass runtime snapshot, and emits the canonical
``hookSpecificOutput.additionalContext`` payload so the spawned subagent
inherits live grounding instead of starting cold.

Failures degrade to a no-op return so a missing snapshot, missing
launcher, or unparseable payload never blocks the Task-tool spawn.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from odylith.runtime.surfaces import claude_host_shared


def render_subagent_payload(
    *,
    repo_root: Path | str = ".",
    agent_type: str = "",
) -> dict[str, dict[str, str]] | None:
    """Render the canonical SubagentStart hook JSON payload, or ``None``."""
    additional = claude_host_shared.build_subagent_context(
        project_dir=repo_root,
        agent_type=str(agent_type or "").strip(),
    )
    if not additional:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": additional,
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude subagent-start",
        description="Render the Odylith-grounded Claude SubagentStart hook output.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass runtime resolution.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude SubagentStart payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    agent_type = str(payload.get("agent_type", "")).strip()
    rendered = render_subagent_payload(repo_root=repo_root, agent_type=agent_type)
    if rendered is None:
        return 0
    sys.stdout.write(json.dumps(rendered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
