#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


_GOVERNANCE_PREFIXES = (
    "odylith/radar/source/",
    "odylith/technical-plans/",
    "odylith/casebook/bugs/",
    "odylith/registry/source/",
    "odylith/atlas/source/",
)
_IGNORED_BASENAMES = {"AGENTS.md", "CLAUDE.md"}


def _project_dir() -> Path:
    token = str(sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if token:
        return Path(token).resolve()
    env_token = str(Path.cwd() if not str(Path.cwd()).strip() else Path.cwd())
    return Path(env_token).resolve()


def _load_payload() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _edited_path(*, payload: dict[str, object], project_dir: Path) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    raw = str(tool_input.get("file_path", "")).strip()
    if not raw:
        return ""
    path = Path(raw)
    resolved = path.resolve() if path.is_absolute() else (project_dir / path).resolve()
    try:
        return resolved.relative_to(project_dir).as_posix()
    except ValueError:
        return ""


def _should_refresh(path_token: str) -> bool:
    if not path_token:
        return False
    path = Path(path_token)
    if path.name in _IGNORED_BASENAMES:
        return False
    normalized = path.as_posix()
    return any(normalized.startswith(prefix) for prefix in _GOVERNANCE_PREFIXES)


def _refresh(*, project_dir: Path, path_token: str) -> dict[str, str]:
    launcher = project_dir / ".odylith" / "bin" / "odylith"
    if not launcher.is_file():
        return {}
    command = [
        str(launcher),
        "sync",
        "--repo-root",
        str(project_dir),
        "--impact-mode",
        "selective",
        path_token,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        cwd=project_dir,
        text=True,
        check=False,
    )
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


def main() -> int:
    project_dir = _project_dir()
    payload = _load_payload()
    path_token = _edited_path(payload=payload, project_dir=project_dir)
    if not _should_refresh(path_token):
        return 0
    result = _refresh(project_dir=project_dir, path_token=path_token)
    if result:
        sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
