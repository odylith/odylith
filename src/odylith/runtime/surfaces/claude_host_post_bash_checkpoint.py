"""Claude Code PostToolUse checkpoint for edit-like Bash tool calls.

Claude's direct Write/Edit/MultiEdit tools already route through
``claude post-edit-checkpoint``. This companion hook covers Bash calls that
write files through shell commands, inline scripts, or apply-patch style
payloads so governed surface refresh still happens. Successful checkpoint
refreshes stay silent because Claude Code renders hook output inline with the
transcript.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint
from odylith.runtime.surfaces import codex_host_shared


def command_from_payload(payload: dict[str, Any]) -> str:
    """Return the shell command represented by a Claude Bash hook payload."""

    return codex_host_shared.command_from_hook_payload(payload)


def should_checkpoint(command: str) -> bool:
    return codex_host_post_bash_checkpoint.should_checkpoint(command)


def command_scoped_governed_paths(*, project_dir: Path | str, command: str) -> list[str]:
    return codex_host_post_bash_checkpoint.command_scoped_governed_paths(
        project_dir=project_dir,
        command=command,
    )


def refresh_governance(*, project_dir: Path | str, paths: list[str]) -> dict[str, str] | None:
    return codex_host_post_bash_checkpoint.refresh_governance(
        project_dir=project_dir,
        paths=paths,
    )


def inferred_command_paths(*, project_dir: Path | str, command: str) -> list[str]:
    return codex_host_post_bash_checkpoint.inferred_command_paths(
        project_dir=project_dir,
        command=command,
    )


def should_run_checkpoint_grounding(*, project_dir: Path | str, command: str) -> bool:
    """Return whether Claude should pay the startup/checkpoint cost for Bash.

    If the command parser can see exact targets and none are governed
    source-of-truth paths, there is no governance refresh to settle. Commands
    with no exact targets still take the conservative path because they may
    mutate governed files indirectly.
    """

    paths = inferred_command_paths(project_dir=project_dir, command=command)
    if not paths:
        return True
    return any(claude_host_shared.should_refresh_governed_edit(path) for path in paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude post-bash-checkpoint",
        description="Nudge Odylith checkpointing after edit-like Claude Bash tool calls.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith governance refresh.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude PostToolUse Bash payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    command = command_from_payload(payload)
    if not should_checkpoint(command):
        return 0
    if not should_run_checkpoint_grounding(project_dir=repo_root, command=command):
        return 0

    claude_host_shared.run_odylith(
        project_dir=repo_root,
        args=["start", "--repo-root", "."],
        timeout=20,
    )

    changed = command_scoped_governed_paths(project_dir=repo_root, command=command)
    governance_message = refresh_governance(project_dir=repo_root, paths=changed)
    governance_status = str((governance_message or {}).get("systemMessage", "")).strip()
    if governance_status and any(token in governance_status.lower() for token in ("failed", "skipped")):
        sys.stdout.write(json.dumps({"systemMessage": governance_status}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
