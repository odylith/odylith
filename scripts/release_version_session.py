"""Resolve and manage sticky Odylith release version sessions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts import release_semver
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    import release_semver


DEFAULT_SESSION_FILE = Path(".odylith/locks/release-session.json")
TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


@dataclass(frozen=True)
class ReleaseSession:
    version: str
    tag: str
    source: str
    initialized_by_target: str
    created_at: str
    last_target: str
    last_resolved_at: str
    head_sha: str

    def to_payload(self) -> dict[str, str]:
        return {
            "version": self.version,
            "tag": self.tag,
            "source": self.source,
            "initialized_by_target": self.initialized_by_target,
            "created_at": self.created_at,
            "last_target": self.last_target,
            "last_resolved_at": self.last_resolved_at,
            "head_sha": self.head_sha,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_bool(value: str, *, field_name: str) -> bool:
    raw = str(value).strip().lower()
    if raw in TRUE_VALUES:
        return True
    if raw in FALSE_VALUES:
        return False
    raise ValueError(f"{field_name} must be one of {sorted(TRUE_VALUES | FALSE_VALUES)}")


def _load_session(path: Path) -> ReleaseSession | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid release session payload: {path}")
    version = release_semver.normalize_stable_semver(str(payload.get("version", "")).strip())
    tag = str(payload.get("tag", "")).strip() or f"v{version}"
    source = str(payload.get("source", "")).strip() or "unknown"
    initialized_by_target = str(payload.get("initialized_by_target", "")).strip() or "unknown"
    created_at = str(payload.get("created_at", "")).strip() or "unknown"
    last_target = str(payload.get("last_target", "")).strip() or initialized_by_target
    last_resolved_at = str(payload.get("last_resolved_at", "")).strip() or created_at
    head_sha = str(payload.get("head_sha", "")).strip()
    if not head_sha:
        raise ValueError(f"release session missing head_sha: {path}")
    return ReleaseSession(
        version=version,
        tag=tag,
        source=source,
        initialized_by_target=initialized_by_target,
        created_at=created_at,
        last_target=last_target,
        last_resolved_at=last_resolved_at,
        head_sha=head_sha,
    )


def _write_session(path: Path, session: ReleaseSession) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(session.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def _clear_stale_session(*, path: Path, session: ReleaseSession, current_head: str) -> str:
    if path.is_file():
        path.unlink()
    return (
        "active release session was invalidated because HEAD changed: "
        f"session_head={session.head_sha} current_head={current_head}. "
        "Start a new release lane on the current commit."
    )


def _requested_explicit_version(candidate: str) -> str:
    token = str(candidate or "").strip()
    if not token:
        return ""
    return release_semver.normalize_stable_semver(token)


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


def _assert_session_matches_current_head(*, session: ReleaseSession) -> None:
    current_head = release_semver.current_head_sha()
    if session.head_sha != current_head:
        raise ValueError(
            "active release session is bound to a different commit: "
            f"session_head={session.head_sha} current_head={current_head}. "
            "Clear the session intentionally and start a new release lane on the current commit."
        )


def _assert_tag_matches_head(*, tag: str, head_sha: str, remote: str) -> None:
    release_semver.fetch_remote_tags(remote)
    if not release_semver.tag_exists(tag):
        raise ValueError(f"release tag `{tag}` is missing after remote tag sync")
    commit = release_semver.tag_commit(tag)
    if commit != head_sha:
        raise ValueError(
            f"release tag `{tag}` is bound to commit {commit}, not the expected release commit {head_sha}"
        )


def _rewrite_unpublished_tag_to_head(*, tag: str, head_sha: str, remote: str) -> None:
    release_semver.run_git("tag", "-fa", tag, head_sha, "-m", tag, capture_output=True)
    pushed = release_semver.run_git(
        "push",
        "--force",
        remote,
        f"refs/tags/{tag}",
        check=False,
        capture_output=True,
    )
    if pushed.returncode != 0:
        release_semver.fetch_remote_tags(remote)
        raise ValueError(
            f"failed to rebind unpublished release tag `{tag}` to commit {head_sha}: "
            f"{(pushed.stderr or pushed.stdout or '').strip()}"
        )
    _assert_tag_matches_head(tag=tag, head_sha=head_sha, remote=remote)


def _push_tag_or_reuse_existing(*, tag: str, head_sha: str, remote: str, max_attempts: int) -> None:
    if max_attempts < 1:
        raise ValueError("--max-attempts must be >= 1")

    release_semver.fetch_remote_tags(remote)
    if release_semver.tag_exists(tag):
        current_commit = release_semver.tag_commit(tag)
        if current_commit == head_sha:
            return
        published = release_semver.published_release_exists(remote=remote, tag=tag)
        if published is True:
            _assert_tag_matches_head(tag=tag, head_sha=head_sha, remote=remote)
        if published is False:
            _rewrite_unpublished_tag_to_head(tag=tag, head_sha=head_sha, remote=remote)
            return
        raise ValueError(
            f"release tag `{tag}` is already bound to commit {current_commit} and publication state "
            "could not be resolved; refusing to move the tag automatically."
        )

    last_error = ""
    for _ in range(max_attempts):
        release_semver.run_git("tag", "-a", tag, "-m", tag)
        pushed = release_semver.run_git(
            "push",
            remote,
            f"refs/tags/{tag}",
            check=False,
            capture_output=True,
        )
        if pushed.returncode == 0:
            _assert_tag_matches_head(tag=tag, head_sha=head_sha, remote=remote)
            return

        release_semver.delete_local_tag(tag)
        details = ((pushed.stderr or "") + "\n" + (pushed.stdout or "")).lower()
        last_error = (
            f"failed to push tag {tag!r} to {remote!r}: "
            f"{(pushed.stderr or pushed.stdout or '').strip()}"
        )
        if "already exists" in details or "cannot lock ref" in details:
            release_semver.fetch_remote_tags(remote)
            if release_semver.tag_exists(tag):
                _push_tag_or_reuse_existing(tag=tag, head_sha=head_sha, remote=remote, max_attempts=1)
                return
            continue
        raise ValueError(last_error)

    if last_error:
        raise ValueError(last_error)
    raise ValueError(f"unable to create or push tag `{tag}` after retries")


def _auto_tag_next_version(*, remote: str, start_at: int, max_attempts: int) -> tuple[str, str]:
    if max_attempts < 1:
        raise ValueError("--max-attempts must be >= 1")

    last_error = ""
    head_sha = release_semver.current_head_sha()
    for _ in range(max_attempts):
        next_tag, next_version, _highest = release_semver.preview_next_patch_release(
            remote=remote,
            tag_pattern=release_semver.DEFAULT_RELEASE_TAG_PATTERN,
            tag_prefix=release_semver.DEFAULT_RELEASE_TAG_PREFIX,
            start_at=start_at,
        )
        next_version = _apply_source_version_floor(next_version)
        next_tag = f"v{next_version}"
        if release_semver.tag_exists(next_tag):
            _push_tag_or_reuse_existing(
                tag=next_tag,
                head_sha=head_sha,
                remote=remote,
                max_attempts=1,
            )
            return next_tag, next_version
        release_semver.run_git("tag", "-a", next_tag, "-m", next_tag)
        pushed = release_semver.run_git(
            "push",
            remote,
            f"refs/tags/{next_tag}",
            check=False,
            capture_output=True,
        )
        if pushed.returncode == 0:
            _assert_tag_matches_head(tag=next_tag, head_sha=head_sha, remote=remote)
            return next_tag, next_version

        release_semver.delete_local_tag(next_tag)
        details = ((pushed.stderr or "") + "\n" + (pushed.stdout or "")).lower()
        last_error = (
            f"failed to push tag {next_tag!r} to {remote!r}: "
            f"{(pushed.stderr or pushed.stdout or '').strip()}"
        )
        if "already exists" in details or "cannot lock ref" in details:
            release_semver.fetch_remote_tags(remote)
            continue
        raise ValueError(last_error)

    if last_error:
        raise ValueError(last_error)
    raise ValueError("unable to create/push next release tag after retries; check git remote state")


def _cmd_resolve(args: argparse.Namespace) -> int:
    session_file = Path(args.session_file).expanduser().resolve()
    target = str(args.target or "").strip()
    if not target:
        raise ValueError("--target must be non-empty")

    allow_session_init = _parse_bool(args.allow_session_init, field_name="--allow-session-init")
    auto_tag_if_unset = _parse_bool(args.auto_tag_if_unset, field_name="--auto-tag-if-unset")
    remote = str(args.remote).strip()
    head_sha = release_semver.current_head_sha()
    requested_explicit = _requested_explicit_version(args.requested_version)
    active = _load_session(session_file)
    now = _utc_now()

    if active is not None:
        if active.head_sha != head_sha:
            reason = _clear_stale_session(path=session_file, session=active, current_head=head_sha)
            if not allow_session_init:
                raise ValueError(reason)
            active = None
        if active is not None:
            _assert_tag_matches_head(tag=active.tag, head_sha=active.head_sha, remote=remote)
            if requested_explicit and requested_explicit != active.version:
                raise ValueError(
                    "explicit VERSION conflicts with the active release session: "
                    f"requested={requested_explicit!r} active={active.version!r}. "
                    "Use `make release-session-show` to inspect or `make release-session-clear` to reset intentionally."
                )
            _write_session(
                session_file,
                ReleaseSession(
                    version=active.version,
                    tag=active.tag,
                    source=active.source,
                    initialized_by_target=active.initialized_by_target,
                    created_at=active.created_at,
                    last_target=target,
                    last_resolved_at=now,
                    head_sha=active.head_sha,
                ),
            )
            print(active.version)
            return 0

    if not allow_session_init:
        raise ValueError(
            "no active release session and this target cannot initialize one. "
            f"target={target!r} session_file={session_file}"
        )

    if requested_explicit:
        highest = release_semver.resolve_highest_release_anchor(remote=remote)
        highest_version = str(highest[1]) if highest is not None else None
        release_semver.ensure_not_lower_than_highest(
            requested_version=requested_explicit,
            highest_version=highest_version,
        )
        resolved_version = requested_explicit
        tag = f"v{resolved_version}"
        _push_tag_or_reuse_existing(
            tag=tag,
            head_sha=head_sha,
            remote=remote,
            max_attempts=int(args.max_attempts),
        )
        source = f"explicit-tag:{tag}"
    else:
        if not auto_tag_if_unset:
            raise ValueError("VERSION is not explicit and auto-tag is disabled")
        tag, resolved_version = _auto_tag_next_version(
            remote=remote,
            start_at=int(args.start_at),
            max_attempts=int(args.max_attempts),
        )
        source = f"auto-tag:{tag}"

    _write_session(
        session_file,
        ReleaseSession(
            version=resolved_version,
            tag=tag,
            source=source,
            initialized_by_target=target,
            created_at=now,
            last_target=target,
            last_resolved_at=now,
            head_sha=head_sha,
        ),
    )
    print(resolved_version)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    session_file = Path(args.session_file).expanduser().resolve()
    active = _load_session(session_file)
    current_head = release_semver.current_head_sha()
    if active is not None and active.head_sha != current_head:
        reason = _clear_stale_session(path=session_file, session=active, current_head=current_head)
        print(f"session_file: {session_file}")
        print("active: no")
        print("stale_cleared: yes")
        print(f"stale_reason: {reason}")
        return 0
    if active is None:
        print(f"session_file: {session_file}")
        print("active: no")
        return 0
    print(f"session_file: {session_file}")
    print("active: yes")
    print(f"version: {active.version}")
    print(f"tag: {active.tag}")
    print(f"source: {active.source}")
    print(f"initialized_by_target: {active.initialized_by_target}")
    print(f"created_at: {active.created_at}")
    print(f"last_target: {active.last_target}")
    print(f"last_resolved_at: {active.last_resolved_at}")
    print(f"head_sha: {active.head_sha}")
    return 0


def _cmd_clear(args: argparse.Namespace) -> int:
    session_file = Path(args.session_file).expanduser().resolve()
    if not session_file.exists():
        print(f"no active release session at {session_file}")
        return 0
    if not session_file.is_file():
        raise ValueError(f"release session path is not a file: {session_file}")
    session_file.unlink()
    print(f"cleared release session at {session_file}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage sticky Odylith release version sessions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE)
    common.add_argument("--remote", default="origin")

    resolve = subparsers.add_parser(
        "resolve",
        parents=[common],
        help="Resolve the effective release version and initialize or reuse the local session.",
    )
    resolve.add_argument("--target", required=True)
    resolve.add_argument("--requested-version", default="")
    resolve.add_argument("--allow-session-init", default="true")
    resolve.add_argument("--auto-tag-if-unset", default="true")
    resolve.add_argument("--start-at", type=int, default=1)
    resolve.add_argument("--max-attempts", type=int, default=5)

    subparsers.add_parser("show", parents=[common], help="Show the current release session.")
    subparsers.add_parser("clear", parents=[common], help="Clear the current release session.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "resolve":
            return _cmd_resolve(args)
        if args.command == "show":
            return _cmd_show(args)
        if args.command == "clear":
            return _cmd_clear(args)
        raise ValueError(f"unsupported command: {args.command}")
    except (ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
