"""Codex PostToolUse Bash checkpoint for edit-like shell commands."""

from __future__ import annotations

import argparse
import sys

from odylith.runtime.surfaces import codex_host_shared


def should_checkpoint(command: str) -> bool:
    return codex_host_shared.edit_like_bash(command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex post-bash-checkpoint",
        description="Nudge Odylith checkpointing after edit-like Bash commands in Codex.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for launcher resolution.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    payload = codex_host_shared.load_payload()
    command = codex_host_shared.command_from_hook_payload(payload)
    if not should_checkpoint(command):
        return 0
    codex_host_shared.run_odylith(
        project_dir=args.repo_root,
        args=["start", "--repo-root", "."],
        timeout=20,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
