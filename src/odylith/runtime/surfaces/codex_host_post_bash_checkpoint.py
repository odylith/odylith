"""Codex PostToolUse Bash checkpoint for edit-like shell commands.

When Codex finishes an edit-like Bash command (``apply_patch``, ``cp``,
``mv``, ``sed -i``, etc. — see
``codex_host_shared.edit_like_bash``), this hook nudges Odylith in two
narrow steps:

1. Run ``odylith start --repo-root .`` so the session stays grounded in
   the same way a fresh turn would be.
2. If the edit touched any repo-relative path under the Odylith
   governed source-of-truth subtrees, run
   ``odylith sync --impact-mode selective <paths>`` so the derived
   dashboards stay aligned.

The second step is Bash-checkpoint parity with Claude's
``post-edit-checkpoint`` hook
(``claude_host_post_edit_checkpoint.refresh_governance``). It is
*not* a universal host-edit parity: any future non-Bash edit surface
in Codex would need its own hook module.

The hook never blocks the bash command. It always exits 0; on failure
it emits a fail-soft ``systemMessage`` describing what went wrong so
the operator can recover manually if needed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import codex_host_shared


def should_checkpoint(command: str) -> bool:
    return codex_host_shared.edit_like_bash(command)


def governed_changed_paths(*, project_dir: Path | str) -> list[str]:
    """Return repo-relative governed paths with uncommitted changes.

    Uses ``git status --porcelain -z`` rooted at the project dir,
    filters through
    ``claude_host_shared.should_refresh_governed_edit``, and returns
    the list in the order git reports. Fails soft to an empty list if
    git is unavailable or errors.
    """
    project = Path(project_dir).expanduser().resolve()
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain", "-z"],
            cwd=str(project),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []

    paths: list[str] = []
    records = completed.stdout.split("\x00")
    if records and records[-1] == "":
        records.pop()
    index = 0
    while index < len(records):
        record = records[index]
        if len(record) < 3:
            index += 1
            continue
        status_xy = record[:2]
        path = record[3:]
        if claude_host_shared.should_refresh_governed_edit(path):
            paths.append(path)
        # For rename/copy entries `git status --porcelain -z` emits the
        # old path as a separate null-terminated record immediately
        # after; skip it so we do not double-count.
        if "R" in status_xy or "C" in status_xy:
            index += 2
        else:
            index += 1
    return paths


def _changed_paths_preview(paths: list[str]) -> str:
    preview = ", ".join(paths[:3])
    if len(paths) > 3:
        preview = f"{preview}, +{len(paths) - 3} more"
    return preview


def refresh_governance(*, project_dir: Path | str, paths: list[str]) -> dict[str, str] | None:
    """Run ``odylith sync --impact-mode selective <paths>`` and return the systemMessage.

    Returns ``None`` when there are no governed changed paths to refresh.
    """
    if not paths:
        return None
    project = Path(project_dir).expanduser().resolve()
    completed = codex_host_shared.run_odylith(
        project_dir=project,
        args=[
            "sync",
            "--repo-root",
            str(project),
            "--impact-mode",
            "selective",
            *paths,
        ],
        timeout=180,
    )
    preview = _changed_paths_preview(paths)
    if completed is None:
        return {
            "systemMessage": (
                f"Odylith governance refresh skipped after edit-like Bash command "
                f"touched {preview}: the repo-local launcher was not available."
            )
        }
    if completed.returncode == 0:
        return {
            "systemMessage": (
                f"Odylith governance refresh completed after edit-like Bash command "
                f"touched {preview}."
            )
        }
    detail = "\n".join(
        line.strip()
        for line in (completed.stderr or completed.stdout or "").splitlines()[-8:]
        if line.strip()
    )
    if not detail:
        detail = f"exit code {completed.returncode}"
    return {
        "systemMessage": (
            f"Odylith governance refresh failed after edit-like Bash command "
            f"touched {preview}: {detail}"
        )
    }


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

    # Keep grounding as the baseline behavior for every edit-like Bash
    # command, even if nothing governed changed.
    codex_host_shared.run_odylith(
        project_dir=args.repo_root,
        args=["start", "--repo-root", "."],
        timeout=20,
    )

    # If the edit-like Bash command touched any governed source-of-truth
    # subtree, refresh the derived dashboards via selective sync. This
    # is Bash-checkpoint parity with Claude's post-edit lane; non-Bash
    # edit surfaces would need their own hook.
    project_dir = claude_host_shared.resolve_repo_root(args.repo_root)
    changed = governed_changed_paths(project_dir=project_dir)
    message = refresh_governance(project_dir=project_dir, paths=changed)
    if message:
        sys.stdout.write(json.dumps(message))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
