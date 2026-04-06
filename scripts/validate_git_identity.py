#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


EXPECTED_NAME = "freedom-research"
EXPECTED_EMAIL = "freedom@freedompreetham.org"
EXPECTED_LOCAL_CONFIG = {
    "user.name": EXPECTED_NAME,
    "user.email": EXPECTED_EMAIL,
    "user.useConfigOnly": "true",
}
IDENT_PATTERN = re.compile(r"^(?P<name>.+) <(?P<email>[^>]+)> \d+ [+-]\d{4}$")


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown git failure"
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout.strip()


def _get_local_config(repo_root: Path, key: str) -> str | None:
    completed = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    if completed.returncode == 1:
        return None
    stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown git failure"
    raise RuntimeError(f"git config --local --get {key} failed: {stderr}")


def _parse_ident(raw: str, *, label: str) -> tuple[str, str]:
    match = IDENT_PATTERN.match(raw.strip())
    if match is None:
        raise RuntimeError(f"could not parse {label}: {raw!r}")
    return match.group("name"), match.group("email")


def validate_local_identity(repo_root: Path) -> list[str]:
    failures: list[str] = []
    for key, expected in EXPECTED_LOCAL_CONFIG.items():
        value = _get_local_config(repo_root, key)
        if value is None:
            failures.append(f"missing local {key}; expected {expected!r}")
            continue
        if value != expected:
            failures.append(f"local {key} must be {expected!r} (found {value!r})")
    for role in ("AUTHOR", "COMMITTER"):
        ident = _run_git(repo_root, "var", f"GIT_{role}_IDENT")
        name, email = _parse_ident(ident, label=f"GIT_{role}_IDENT")
        if name != EXPECTED_NAME:
            failures.append(f"{role.lower()} name must be {EXPECTED_NAME!r} (found {name!r})")
        if email != EXPECTED_EMAIL:
            failures.append(f"{role.lower()} email must be {EXPECTED_EMAIL!r} (found {email!r})")
    return failures


def validate_commit_history(repo_root: Path, *, revisions: Sequence[str], include_all: bool) -> list[str]:
    log_args = [
        "log",
        "--no-show-signature",
        "--format=%H%x00%an%x00%ae%x00%cn%x00%ce",
    ]
    if include_all:
        log_args.append("--all")
    elif revisions:
        log_args.extend(revisions)
    else:
        log_args.append("HEAD")
    output = _run_git(repo_root, *log_args)
    if not output:
        return []

    failures: list[str] = []
    for line in output.splitlines():
        sha, author_name, author_email, committer_name, committer_email = line.split("\x00")
        if author_name != EXPECTED_NAME:
            failures.append(f"{sha}: author name must be {EXPECTED_NAME!r} (found {author_name!r})")
        if author_email != EXPECTED_EMAIL:
            failures.append(f"{sha}: author email must be {EXPECTED_EMAIL!r} (found {author_email!r})")
        if committer_name != EXPECTED_NAME:
            failures.append(f"{sha}: committer name must be {EXPECTED_NAME!r} (found {committer_name!r})")
        if committer_email != EXPECTED_EMAIL:
            failures.append(f"{sha}: committer email must be {EXPECTED_EMAIL!r} (found {committer_email!r})")
    return failures


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate that Odylith maintainer git identity stays pinned to freedom-research.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser(
        "config",
        help="Validate the local repo config and effective author/committer identity.",
    )
    config_parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root.")

    history_parser = subparsers.add_parser(
        "history",
        help="Validate author and committer identity for reachable commits.",
    )
    history_parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root.")
    history_parser.add_argument(
        "--all",
        action="store_true",
        help="Inspect every reachable commit instead of only the listed revisions.",
    )
    history_parser.add_argument(
        "revisions",
        nargs="*",
        help="Revision selectors for git log. Defaults to HEAD when omitted.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "config":
            failures = validate_local_identity(repo_root)
        else:
            failures = validate_commit_history(
                repo_root,
                revisions=args.revisions,
                include_all=args.all,
            )
    except RuntimeError as exc:
        print(f"identity guard: {exc}", file=sys.stderr)
        return 2

    if not failures:
        return 0

    for failure in failures:
        print(f"identity guard: {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
