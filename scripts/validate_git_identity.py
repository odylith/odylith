#!/usr/bin/env python3
"""Validate local git identity and recent history against repo policy."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


EXPECTED_NAME = "freedom-research"
EXPECTED_EMAIL = "freedom@freedompreetham.org"
EXPECTED_GITHUB_LOGIN = EXPECTED_NAME
EXPECTED_GITHUB_REPOSITORY = "odylith/odylith"
EXPECTED_GITHUB_PERMISSIONS = frozenset({"ADMIN", "MAINTAIN", "WRITE"})
EXPECTED_HISTORY_AUTHOR_NAMES = frozenset({EXPECTED_NAME, "Freedom Preetham"})
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


def _run_command(repo_root: Path, args: Sequence[str]) -> str:
    completed = subprocess.run(
        list(args),
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown command failure"
        raise RuntimeError(f"{' '.join(args)} failed: {stderr}")
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


def _valid_direct_identity(name: str, email: str) -> bool:
    return name == EXPECTED_NAME and email == EXPECTED_EMAIL


def _valid_history_author_identity(name: str, email: str) -> bool:
    return name in EXPECTED_HISTORY_AUTHOR_NAMES and email == EXPECTED_EMAIL


def _history_identity_expectation() -> str:
    accepted_names = ", ".join(sorted(EXPECTED_HISTORY_AUTHOR_NAMES))
    return f"{{{accepted_names}}} / {EXPECTED_EMAIL!r} for canonical maintainer authorship"


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
    expectation = _history_identity_expectation()
    for line in output.splitlines():
        sha, author_name, author_email, committer_name, committer_email = line.split("\x00")
        if _valid_history_author_identity(author_name, author_email):
            continue
        failures.append(
            f"{sha}: author identity must stay within {expectation} "
            f"(found {author_name!r} / {author_email!r}; "
            f"committer was {committer_name!r} / {committer_email!r})"
        )
    return failures


def validate_github_identity(repo_root: Path) -> list[str]:
    if shutil.which("gh") is None:
        return ["GitHub CLI `gh` is required before pushing from this repository"]

    user_raw = _run_command(repo_root, ["gh", "api", "user"])
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh api user returned invalid JSON: {exc}") from exc

    failures: list[str] = []
    login = str(user.get("login") or "")
    email = str(user.get("email") or "")
    if login != EXPECTED_GITHUB_LOGIN:
        failures.append(f"GitHub login must be {EXPECTED_GITHUB_LOGIN!r} (found {login!r})")
    if email != EXPECTED_EMAIL:
        failures.append(f"GitHub email must be {EXPECTED_EMAIL!r} (found {email!r})")

    permission_raw = _run_command(
        repo_root,
        ["gh", "repo", "view", EXPECTED_GITHUB_REPOSITORY, "--json", "viewerPermission"],
    )
    try:
        permission_payload = json.loads(permission_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh repo view returned invalid JSON: {exc}") from exc
    permission = str(permission_payload.get("viewerPermission") or "")
    if permission not in EXPECTED_GITHUB_PERMISSIONS:
        expected = ", ".join(sorted(EXPECTED_GITHUB_PERMISSIONS))
        failures.append(
            f"GitHub permission for {EXPECTED_GITHUB_REPOSITORY} must be one of {{{expected}}} "
            f"(found {permission!r})"
        )
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

    github_parser = subparsers.add_parser(
        "github",
        help="Validate the authenticated GitHub CLI account before push operations.",
    )
    github_parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "config":
            failures = validate_local_identity(repo_root)
        elif args.command == "github":
            failures = validate_github_identity(repo_root)
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
