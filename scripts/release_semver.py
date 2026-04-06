"""Shared stable-semver utilities for Odylith maintainer release tooling."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable


DEFAULT_RELEASE_TAG_PATTERN = "v*.*.*"
DEFAULT_RELEASE_TAG_PREFIX = "v"
_STABLE_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

GitRunner = Callable[..., subprocess.CompletedProcess[str]]
GhRunner = Callable[..., subprocess.CompletedProcess[str]]
_GITHUB_REMOTE_RE = re.compile(
    r"^(?:https://(?:[^@/]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


@dataclass(frozen=True, order=True)
class StableSemVer:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_stable_semver(version: str) -> StableSemVer:
    candidate = str(version).strip()
    match = _STABLE_SEMVER_RE.fullmatch(candidate)
    if not match:
        raise ValueError(
            "release version must be stable semver X.Y.Z "
            "(for example: 0.1.0 or 1.2.3)"
        )
    return StableSemVer(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
    )


def normalize_stable_semver(version: str) -> str:
    return str(parse_stable_semver(version))


def semver_from_tag(tag: str, *, tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX) -> StableSemVer | None:
    raw = str(tag).strip()
    if not raw:
        return None

    normalized = raw
    if tag_prefix and normalized.startswith(tag_prefix):
        normalized = normalized[len(tag_prefix) :]
    elif normalized.startswith("v"):
        normalized = normalized[1:]

    try:
        return parse_stable_semver(normalized)
    except ValueError:
        return None


def select_highest_semver_tag(
    tags: list[str],
    *,
    tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX,
) -> tuple[str, StableSemVer] | None:
    best: tuple[str, StableSemVer] | None = None
    for raw in tags:
        parsed = semver_from_tag(raw, tag_prefix=tag_prefix)
        if parsed is None:
            continue
        if best is None or parsed > best[1]:
            best = (raw, parsed)
    return best


def next_patch_from_highest(
    highest: tuple[str, StableSemVer] | None,
    *,
    start_at: int = 1,
    tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX,
) -> tuple[str, str]:
    if start_at < 0:
        raise ValueError("start-at must be >= 0")
    if not str(tag_prefix).strip():
        raise ValueError("tag prefix is empty")

    if highest is None:
        next_version = StableSemVer(0, 0, int(start_at))
    else:
        current = highest[1]
        next_version = StableSemVer(current.major, current.minor, current.patch + 1)

    version = str(next_version)
    return f"{tag_prefix}{version}", version


def run_git(
    *args: str,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            check=check,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        raise ValueError("git is required for release semver resolution") from exc


def run_gh(
    *args: str,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", *args],
            check=check,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        raise ValueError("gh is required for GitHub release resolution") from exc


def is_tag_clobber_fetch_error(exc: subprocess.CalledProcessError) -> bool:
    details = ((exc.stderr or "") + "\n" + (exc.stdout or "")).lower()
    return "would clobber existing tag" in details


def fetch_remote_tags(remote: str, *, git_runner: GitRunner = run_git) -> None:
    remote_name = str(remote).strip()
    if not remote_name:
        raise ValueError("git remote is empty")

    try:
        git_runner("fetch", "--tags", remote_name, capture_output=True)
    except subprocess.CalledProcessError as exc:
        if not is_tag_clobber_fetch_error(exc):
            raise
        print(
            "warning: local tag state diverged from remote; forcing tag sync for release semver resolution.",
            file=sys.stderr,
        )
        git_runner("fetch", "--tags", "--force", remote_name, capture_output=True)


def remote_repository_full_name(
    remote: str,
    *,
    git_runner: GitRunner = run_git,
) -> str | None:
    remote_name = str(remote).strip()
    if not remote_name:
        raise ValueError("git remote is empty")
    remote_url = str(git_runner("remote", "get-url", remote_name, capture_output=True).stdout or "").strip()
    match = _GITHUB_REMOTE_RE.fullmatch(remote_url)
    if match is None:
        return None
    owner = match.group("owner").strip()
    repo = match.group("repo").strip()
    if not owner or not repo:
        return None
    return f"{owner}/{repo}"


def list_published_release_tags(
    *,
    remote: str,
    limit: int = 200,
    git_runner: GitRunner = run_git,
    gh_runner: GhRunner = run_gh,
) -> list[str] | None:
    repository_full_name = remote_repository_full_name(remote, git_runner=git_runner)
    if repository_full_name is None:
        return None
    if limit < 1:
        raise ValueError("release list limit must be >= 1")
    try:
        response = gh_runner(
            "release",
            "list",
            "--repo",
            repository_full_name,
            "--limit",
            str(limit),
            "--json",
            "tagName,isDraft",
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise ValueError(
            f"unable to resolve published GitHub releases for {repository_full_name}: {details or exc}"
        ) from exc

    try:
        payload = json.loads(response.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid gh release list payload while resolving published releases for {repository_full_name}"
        ) from exc
    if not isinstance(payload, list):
        raise ValueError(
            f"invalid gh release list payload while resolving published releases for {repository_full_name}"
        )
    tags: list[str] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        if bool(entry.get("isDraft")):
            continue
        tag = str(entry.get("tagName", "")).strip()
        if tag:
            tags.append(tag)
    return tags


def list_matching_tags(
    *,
    tag_pattern: str = DEFAULT_RELEASE_TAG_PATTERN,
    git_runner: GitRunner = run_git,
) -> list[str]:
    pattern = str(tag_pattern).strip()
    if not pattern:
        raise ValueError("tag pattern is empty")

    listed = git_runner(
        "tag",
        "-l",
        pattern,
        "--sort=-v:refname",
        capture_output=True,
    )
    tags: list[str] = []
    for line in (listed.stdout or "").splitlines():
        candidate = line.strip()
        if candidate:
            tags.append(candidate)
    return tags


def resolve_highest_semver_tag(
    *,
    remote: str,
    tag_pattern: str = DEFAULT_RELEASE_TAG_PATTERN,
    tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX,
    git_runner: GitRunner = run_git,
) -> tuple[str, StableSemVer] | None:
    fetch_remote_tags(remote, git_runner=git_runner)
    tags = list_matching_tags(tag_pattern=tag_pattern, git_runner=git_runner)
    return select_highest_semver_tag(tags, tag_prefix=tag_prefix)


def resolve_highest_published_release_tag(
    *,
    remote: str,
    tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX,
    git_runner: GitRunner = run_git,
    gh_runner: GhRunner = run_gh,
) -> tuple[str, StableSemVer] | None:
    tags = list_published_release_tags(
        remote=remote,
        git_runner=git_runner,
        gh_runner=gh_runner,
    )
    if tags is None:
        return None
    return select_highest_semver_tag(tags, tag_prefix=tag_prefix)


def resolve_highest_release_anchor(
    *,
    remote: str,
    tag_pattern: str = DEFAULT_RELEASE_TAG_PATTERN,
    tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX,
    git_runner: GitRunner = run_git,
    gh_runner: GhRunner = run_gh,
) -> tuple[str, StableSemVer] | None:
    published = resolve_highest_published_release_tag(
        remote=remote,
        tag_prefix=tag_prefix,
        git_runner=git_runner,
        gh_runner=gh_runner,
    )
    if published is not None:
        return published
    return resolve_highest_semver_tag(
        remote=remote,
        tag_pattern=tag_pattern,
        tag_prefix=tag_prefix,
        git_runner=git_runner,
    )


def published_release_exists(
    *,
    remote: str,
    tag: str,
    git_runner: GitRunner = run_git,
    gh_runner: GhRunner = run_gh,
) -> bool | None:
    tags = list_published_release_tags(
        remote=remote,
        git_runner=git_runner,
        gh_runner=gh_runner,
    )
    if tags is None:
        return None
    return str(tag).strip() in set(tags)


def preview_next_patch_release(
    *,
    remote: str,
    tag_pattern: str = DEFAULT_RELEASE_TAG_PATTERN,
    tag_prefix: str = DEFAULT_RELEASE_TAG_PREFIX,
    start_at: int = 1,
    git_runner: GitRunner = run_git,
) -> tuple[str, str, str | None]:
    highest = resolve_highest_release_anchor(
        remote=remote,
        tag_pattern=tag_pattern,
        tag_prefix=tag_prefix,
        git_runner=git_runner,
        gh_runner=run_gh,
    )
    next_tag, next_version = next_patch_from_highest(
        highest,
        start_at=start_at,
        tag_prefix=tag_prefix,
    )
    highest_version = str(highest[1]) if highest is not None else None
    return next_tag, next_version, highest_version


def ensure_not_lower_than_highest(
    *,
    requested_version: str,
    highest_version: str | None,
) -> None:
    if highest_version is None:
        return

    requested = parse_stable_semver(requested_version)
    highest = parse_stable_semver(highest_version)
    if requested < highest:
        raise ValueError(
            "requested release version is lower than highest existing semver tag: "
            f"requested={requested} highest={highest}. "
            "Use an explicit version >= highest or allow auto patch progression."
        )


def current_head_sha(*, git_runner: GitRunner = run_git) -> str:
    result = git_runner("rev-parse", "HEAD", capture_output=True)
    return str(result.stdout or "").strip()


def tag_exists(tag: str, *, git_runner: GitRunner = run_git) -> bool:
    result = git_runner("tag", "-l", str(tag).strip(), capture_output=True)
    return bool(str(result.stdout or "").strip())


def tag_commit(tag: str, *, git_runner: GitRunner = run_git) -> str:
    result = git_runner("rev-list", "-n", "1", f"{str(tag).strip()}^{{commit}}", capture_output=True)
    commit = str(result.stdout or "").strip()
    if not commit:
        raise ValueError(f"unable to resolve commit for tag `{tag}`")
    return commit


def delete_local_tag(tag: str, *, git_runner: GitRunner = run_git) -> None:
    git_runner("tag", "-d", str(tag).strip(), check=False, capture_output=True)
