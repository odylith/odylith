"""Maintainer Lane Status helpers for the Odylith governance layer."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.install.manager import (
    PINNED_RELEASE_POSTURE,
    PINNED_RUNTIME_SOURCE,
    PRODUCT_REPO_ROLE,
    product_repo_role,
    version_status,
)
from odylith.runtime.evaluation import benchmark_compare
from odylith.runtime.governance import version_truth

_RELEASE_SESSION_PATH = Path(".odylith/locks/release-session.json")


def _git_stdout(*, repo_root: Path, args: list[str]) -> str:
    """Run a git command and return trimmed stdout on success."""
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return str(completed.stdout or "").strip()


def _current_branch(repo_root: Path) -> str:
    """Return the current git branch name, or an empty string if detached."""
    return _git_stdout(repo_root=repo_root, args=["branch", "--show-current"])


def _current_head(repo_root: Path) -> str:
    """Return the current HEAD object id."""
    return _git_stdout(repo_root=repo_root, args=["rev-parse", "HEAD"])


def _worktree_clean(repo_root: Path) -> bool:
    """Return whether tracked and staged git state is clean."""
    tracked = subprocess.run(
        ["git", "diff", "--quiet", "--ignore-submodules", "HEAD", "--"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
    )
    staged = subprocess.run(
        ["git", "diff", "--quiet", "--ignore-submodules", "--cached", "--"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
    )
    return tracked.returncode == 0 and staged.returncode == 0


def _load_release_session(*, repo_root: Path) -> dict[str, Any]:
    """Load the current release-session lock file and classify its state."""
    path = repo_root / _RELEASE_SESSION_PATH
    if not path.is_file():
        return {"state": "inactive", "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "invalid", "path": str(path)}
    if not isinstance(payload, Mapping):
        return {"state": "invalid", "path": str(path)}
    head_sha = str(payload.get("head_sha") or "").strip()
    current_head = _current_head(repo_root)
    if head_sha and current_head and head_sha != current_head:
        return {
            "state": "stale",
            "path": str(path),
            "version": str(payload.get("version") or "").strip(),
            "tag": str(payload.get("tag") or "").strip(),
            "head_sha": head_sha,
            "current_head": current_head,
        }
    return {
        "state": "active",
        "path": str(path),
        "version": str(payload.get("version") or "").strip(),
        "tag": str(payload.get("tag") or "").strip(),
        "head_sha": head_sha,
        "last_target": str(payload.get("last_target") or "").strip(),
        "created_at": str(payload.get("created_at") or "").strip(),
    }


def _main_branch_authoring_block(*, repo_root: Path, branch: str) -> dict[str, Any]:
    """Return the maintainer-lane main-branch authoring block state."""
    blocked = product_repo_role(repo_root=repo_root) == PRODUCT_REPO_ROLE and str(branch).strip() == "main"
    return {
        "blocked": blocked,
        "reason": (
            "Maintainer authoring on `main` is forbidden; create and switch to a release work branch first."
            if blocked
            else ""
        ),
    }


def _default_branch_command() -> str:
    """Return the default branch-creation command for maintainer work."""
    year = datetime.now(UTC).year
    return f"git switch -c {year}/freedom/<tag>"


def _next_command(
    *,
    repo_root: Path,
    branch: str,
    clean_worktree: bool,
    repo_role: str,
    posture: str,
    runtime_source: str,
    session: Mapping[str, Any],
    version_truth_errors: Sequence[str],
    benchmark_status: str,
) -> str:
    """Choose the next maintainer-lane command from current repo posture."""
    if repo_role != PRODUCT_REPO_ROLE:
        return "./.odylith/bin/odylith start --repo-root ."
    if branch == "main":
        return _default_branch_command()
    if posture != PINNED_RELEASE_POSTURE or runtime_source != PINNED_RUNTIME_SOURCE:
        return "make dogfood-activate"
    if not clean_worktree:
        return "make dev-validate"
    if version_truth_errors:
        return "./.odylith/bin/odylith validate version-truth --repo-root . sync"
    session_state = str(session.get("state") or "").strip()
    if session_state == "stale":
        return "make release-preflight"
    if session_state == "active":
        return "make release-dispatch"
    if benchmark_status in {"fail", "unavailable"}:
        return "./.odylith/bin/odylith benchmark compare --repo-root . --baseline last-shipped"
    return "make release-candidate"


def _mapping_payload(value: Any) -> dict[str, Any]:
    """Return a plain dict when the value is mapping-like."""
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    """Return a cleaned list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def lane_status_payload(*, repo_root: str | Path) -> dict[str, Any]:
    """Build the maintainer-lane status payload for the current repo root."""
    root = Path(repo_root).expanduser().resolve()
    status = version_status(repo_root=root)
    branch = _current_branch(root)
    clean_worktree = _worktree_clean(root)
    session = _load_release_session(repo_root=root)
    version_payload = version_truth.render_version_truth(repo_root=root)
    benchmark_payload = benchmark_compare.compare_latest_to_baseline(repo_root=root, baseline="last-shipped").as_dict()
    main_block = _main_branch_authoring_block(repo_root=root, branch=branch)
    next_command = _next_command(
        repo_root=root,
        branch=branch,
        clean_worktree=clean_worktree,
        repo_role=status.repo_role,
        posture=status.posture,
        runtime_source=status.runtime_source,
        session=session,
        version_truth_errors=[str(item) for item in version_payload.get("errors", [])],
        benchmark_status=str(benchmark_payload.get("status") or "").strip(),
    )
    return {
        "repo_root": str(root),
        "branch": branch,
        "clean_worktree": clean_worktree,
        "repo_role": status.repo_role,
        "posture": status.posture,
        "runtime_source": status.runtime_source,
        "release_eligible": status.release_eligible,
        "main_branch_authoring_block": main_block,
        "release_session": session,
        "version_truth": version_payload,
        "benchmark_compare": benchmark_payload,
        "next_command": next_command,
    }


def render_lane_status(payload: Mapping[str, Any]) -> str:
    """Render the maintainer-lane status payload for human CLI consumption."""
    main_block = _mapping_payload(payload.get("main_branch_authoring_block"))
    session = _mapping_payload(payload.get("release_session"))
    version_payload = _mapping_payload(payload.get("version_truth"))
    benchmark_payload = _mapping_payload(payload.get("benchmark_compare"))
    errors = _string_list(version_payload.get("errors"))
    notes = _string_list(benchmark_payload.get("notes"))
    return "\n".join(
        [
            "odylith lane status",
            f"- branch: {str(payload.get('branch') or '<detached>')}",
            f"- clean_worktree: {'yes' if bool(payload.get('clean_worktree')) else 'no'}",
            f"- repo_role: {str(payload.get('repo_role') or '')}",
            f"- posture: {str(payload.get('posture') or '')}",
            f"- runtime_source: {str(payload.get('runtime_source') or '')}",
            f"- release_eligible: {str(payload.get('release_eligible') if payload.get('release_eligible') is not None else 'n/a')}",
            f"- main_branch_authoring_block: {'yes' if bool(main_block.get('blocked')) else 'no'}",
            f"- release_session: {str(session.get('state') or 'inactive')}",
            f"- version_truth: {'clean' if not errors else 'drift'}",
            f"- benchmark_compare: {str(benchmark_payload.get('status') or 'unavailable')}",
            f"- next: {str(payload.get('next_command') or '')}",
            *([f"- branch_note: {str(main_block.get('reason') or '').strip()}"] if str(main_block.get("reason") or "").strip() else []),
            *[f"- version_note: {item}" for item in errors],
            *[f"- benchmark_note: {item}" for item in notes[:3]],
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for maintainer-lane status inspection."""
    parser = argparse.ArgumentParser(prog="odylith lane status", description="Show Odylith maintainer lane posture and next action.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for maintainer-lane status rendering."""
    args = build_parser().parse_args(argv)
    payload = lane_status_payload(repo_root=args.repo_root)
    if args.as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_lane_status(payload))
    blocked = bool(_mapping_payload(payload.get("main_branch_authoring_block")).get("blocked"))
    benchmark_status = str(_mapping_payload(payload.get("benchmark_compare")).get("status") or "").strip()
    if blocked:
        return 1
    if benchmark_status == "fail":
        return 2
    if benchmark_status == "unavailable":
        return 1
    return 0
