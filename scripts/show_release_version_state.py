"""Show or preview Odylith maintainer release version state."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

try:
    from scripts import release_semver
    from scripts import release_version_session
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    import release_semver
    import release_version_session


def _load_session(session_file: Path) -> release_version_session.ReleaseSession | None:
    if not session_file.exists():
        return None
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid release session payload: {session_file}")
    version = release_semver.normalize_stable_semver(str(payload.get("version", "")).strip())
    tag = str(payload.get("tag", "")).strip() or f"v{version}"
    source = str(payload.get("source", "")).strip() or "unknown"
    initialized_by_target = str(payload.get("initialized_by_target", "")).strip() or "unknown"
    created_at = str(payload.get("created_at", "")).strip() or "unknown"
    last_target = str(payload.get("last_target", "")).strip() or initialized_by_target
    last_resolved_at = str(payload.get("last_resolved_at", "")).strip() or created_at
    head_sha = str(payload.get("head_sha", "")).strip() or "<unknown>"
    return release_version_session.ReleaseSession(
        version=version,
        tag=tag,
        source=source,
        initialized_by_target=initialized_by_target,
        created_at=created_at,
        last_target=last_target,
        last_resolved_at=last_resolved_at,
        head_sha=head_sha,
    )


def _source_version_floor() -> str:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.is_file():
        return ""
    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    project = payload.get("project")
    if not isinstance(project, dict):
        return ""
    version = str(project.get("version", "")).strip()
    if not version:
        return ""
    try:
        return release_semver.normalize_stable_semver(version)
    except ValueError:
        return ""


def _apply_source_version_floor(version: str) -> str:
    floor = _source_version_floor()
    if not floor:
        return version
    candidate = release_semver.parse_stable_semver(version)
    floor_semver = release_semver.parse_stable_semver(floor)
    if floor_semver > candidate:
        return floor
    return version


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Show or preview Odylith release version state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--session-file", type=Path, default=release_version_session.DEFAULT_SESSION_FILE)
    common.add_argument("--remote", default="origin")
    common.add_argument("--start-at", type=int, default=1)

    subparsers.add_parser("preview", parents=[common], help="Print the next auto release version.")
    subparsers.add_parser("show", parents=[common], help="Show current session and semver state.")
    return parser


def _cmd_preview(args: argparse.Namespace) -> int:
    _tag, version, _highest = release_semver.preview_next_patch_release(
        remote=str(args.remote).strip(),
        start_at=int(args.start_at),
    )
    version = _apply_source_version_floor(version)
    print(version)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    session_file = Path(args.session_file).expanduser().resolve()
    session = _load_session(session_file)
    current_head = release_semver.current_head_sha()
    stale_cleared = False
    stale_reason = ""
    if session is not None and session.head_sha and current_head and session.head_sha != current_head:
        stale_reason = release_version_session._clear_stale_session(  # noqa: SLF001
            path=session_file,
            session=session,
            current_head=current_head,
        )
        stale_cleared = True
        session = None
    published = release_semver.resolve_highest_published_release_tag(remote=str(args.remote).strip())
    highest = release_semver.resolve_highest_semver_tag(remote=str(args.remote).strip())
    next_tag, next_version = release_semver.next_patch_from_highest(
        published if published is not None else highest,
        start_at=int(args.start_at),
    )
    next_version = _apply_source_version_floor(next_version)
    next_tag = f"v{next_version}"
    source_floor = _source_version_floor()
    print(f"session_file: {session_file}")
    print(f"active: {'yes' if session is not None else 'no'}")
    print(f"stale_cleared: {'yes' if stale_cleared else 'no'}")
    print(f"stale_reason: {stale_reason or '<none>'}")
    print(f"session_version: {session.version if session is not None else '<none>'}")
    print(f"session_tag: {session.tag if session is not None else '<none>'}")
    print(f"session_head_sha: {session.head_sha if session is not None else '<none>'}")
    print(f"highest_published_release_tag: {published[0] if published is not None else '<none>'}")
    print(
        f"highest_published_release_version: {str(published[1]) if published is not None else '<none>'}"
    )
    print(f"highest_semver_tag: {highest[0] if highest is not None else '<none>'}")
    print(f"highest_semver_version: {str(highest[1]) if highest is not None else '<none>'}")
    print(f"source_version_floor: {source_floor or '<none>'}")
    print(f"next_auto_anchor: {'published_release' if published is not None else 'highest_tag'}")
    print(f"next_auto_tag: {next_tag}")
    print(f"next_auto_version: {next_version}")
    print(f"effective_version: {session.version if session is not None else next_version}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            return _cmd_preview(args)
        if args.command == "show":
            return _cmd_show(args)
        raise ValueError(f"unsupported command: {args.command}")
    except (ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
