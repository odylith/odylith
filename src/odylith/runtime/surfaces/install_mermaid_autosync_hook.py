"""Install a git pre-commit hook that auto-syncs Odylith governance artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import stat
import subprocess
from typing import Sequence

from odylith.runtime.governance.sync_workstream_artifacts import generated_output_targets


_HOOK_MARKER_BEGIN = "# >>> ODYLITH_MERMAID_AUTOSYNC_BEGIN"
_HOOK_MARKER_END = "# <<< ODYLITH_MERMAID_AUTOSYNC_END"
_STRICT_SYNC_ARGS = (
    "--repo-root . --force --registry-policy-mode enforce-critical --enforce-deep-skills"
)
_STAGE_OUTPUTS = " ".join(generated_output_targets())


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith atlas install-autosync-hook",
        description="Install Odylith Mermaid auto-sync pre-commit hook",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--force", action="store_true", help="Overwrite non-empty existing pre-commit hook")
    return parser.parse_args(argv)


def _git_dir(repo_root: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    path = Path(token)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def _snippet() -> str:
    return f"""{_HOOK_MARKER_BEGIN}
if ! git diff --quiet --ignore-submodules --; then
  echo "Skipping Odylith autosync: unstaged changes detected. Stage or stash them, then run odylith sync {_STRICT_SYNC_ARGS} before commit." >&2
  exit 0
fi

odylith sync {_STRICT_SYNC_ARGS}
git add {_STAGE_OUTPUTS} || true
"${{PRE_COMMIT:-pre-commit}}" run --hook-stage pre-commit
{_HOOK_MARKER_END}
"""


def _strip_existing_snippet(text: str) -> str:
    if _HOOK_MARKER_BEGIN not in text or _HOOK_MARKER_END not in text:
        return text
    start = text.find(_HOOK_MARKER_BEGIN)
    end = text.find(_HOOK_MARKER_END, start)
    if end == -1:
        return text
    end += len(_HOOK_MARKER_END)
    while end < len(text) and text[end] in ("\n", "\r"):
        end += 1
    return text[:start] + text[end:]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    git_dir = _git_dir(repo_root)
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    existing = hook_path.read_text(encoding="utf-8") if hook_path.exists() else ""
    existing = _strip_existing_snippet(existing)

    if existing.strip():
        if args.force:
            body = "#!/usr/bin/env bash\nset -euo pipefail\n\n" + _snippet()
        else:
            lines = existing.splitlines(keepends=True)
            insert_index = 1 if lines and lines[0].startswith("#!") else 0
            body = _snippet() if not lines else "".join(lines[:insert_index]) + _snippet() + "".join(lines[insert_index:])
    else:
        body = "#!/usr/bin/env bash\nset -euo pipefail\n\n" + _snippet()
    hook_path.write_text(body, encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed hook: {hook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
