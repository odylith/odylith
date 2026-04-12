"""Claude Code PostToolUse hook: governance refresh after Write/Edit/MultiEdit.

When Claude Code finishes a ``Write``, ``Edit``, or ``MultiEdit`` tool
call, the ``PostToolUse`` hook fires with the file path that was
edited. This baked module mirrors the legacy
``.claude/hooks/refresh-governance-after-edit.py`` script. If the edited
path is inside one of the governed Odylith source-of-truth subtrees
(``odylith/radar/source/``, ``odylith/technical-plans/``,
``odylith/casebook/bugs/``, ``odylith/registry/source/``,
``odylith/atlas/source/``), it runs ``odylith sync --impact-mode
selective <path>`` to keep the derived dashboards aligned and emits a
``systemMessage`` payload describing the result.

The hook never blocks the edit. It always exits 0; on failure it emits
a fail-soft ``systemMessage`` describing the exit code so the operator
can recover manually if needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from odylith.runtime.surfaces import claude_host_shared


_GOVERNANCE_PREFIXES: tuple[str, ...] = (
    "odylith/radar/source/",
    "odylith/technical-plans/",
    "odylith/casebook/bugs/",
    "odylith/registry/source/",
    "odylith/atlas/source/",
)
_IGNORED_BASENAMES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md"})


def edited_path(*, payload: dict, project_dir: Path | str) -> str:
    """Return the path-relative-to-project of the edited file, or ``""``."""
    if not isinstance(payload, dict):
        return ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    raw = str(tool_input.get("file_path", "")).strip()
    if not raw:
        return ""
    project = Path(project_dir).expanduser().resolve()
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (project / candidate).resolve()
    try:
        return resolved.relative_to(project).as_posix()
    except ValueError:
        return ""


def should_refresh(path_token: str) -> bool:
    """Return True if the edited path is inside a governed Odylith subtree."""
    if not path_token:
        return False
    path = Path(path_token)
    if path.name in _IGNORED_BASENAMES:
        return False
    normalized = path.as_posix()
    return any(normalized.startswith(prefix) for prefix in _GOVERNANCE_PREFIXES)


def refresh_governance(*, project_dir: Path | str, path_token: str) -> dict[str, str]:
    """Run ``odylith sync --impact-mode selective <path>`` and return the systemMessage."""
    project = Path(project_dir).expanduser().resolve()
    completed = claude_host_shared.run_odylith(
        project_dir=project,
        args=[
            "sync",
            "--repo-root",
            str(project),
            "--impact-mode",
            "selective",
            path_token,
        ],
        timeout=180,
    )
    if completed is None:
        return {
            "systemMessage": (
                f"Odylith governance refresh skipped after editing {path_token}: "
                "the repo-local launcher was not available."
            )
        }
    if completed.returncode == 0:
        return {"systemMessage": f"Odylith governance refresh completed after editing {path_token}."}
    detail = "\n".join(
        line.strip()
        for line in (completed.stderr or completed.stdout or "").splitlines()[-8:]
        if line.strip()
    )
    if not detail:
        detail = f"exit code {completed.returncode}"
    return {"systemMessage": f"Odylith governance refresh failed after editing {path_token}: {detail}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude post-edit-checkpoint",
        description="Refresh Odylith governance dashboards after a Claude Write/Edit/MultiEdit tool call.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith governance refresh.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude PostToolUse payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    path_token = edited_path(payload=payload, project_dir=repo_root)
    if not should_refresh(path_token):
        return 0
    result = refresh_governance(project_dir=repo_root, path_token=path_token)
    if result:
        sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
