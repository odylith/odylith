"""Reference parsing helpers for GitHub issue tokens."""

from __future__ import annotations

import re
from typing import Sequence

from odylith.runtime.governance.github_issue_models import DEFAULT_GITHUB_REPO
from odylith.runtime.governance.github_issue_models import IssueReference

ISSUE_TOKEN_RE = re.compile(r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(?P<number>\d+)")
_ISSUE_URL_RE = re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+)/issues/(?P<number>\d+)(?:[/?#].*)?$")
_ISSUE_URL_SCAN_RE = re.compile(r"https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)")


def parse_issue_reference(reference: str, *, default_repo: str = DEFAULT_GITHUB_REPO) -> IssueReference:
    token = str(reference or "").strip()
    if not token:
        raise ValueError("issue reference is required")
    url_match = _ISSUE_URL_RE.match(token)
    if url_match:
        return IssueReference(repo=url_match.group("repo"), number=int(url_match.group("number")))
    shorthand_match = ISSUE_TOKEN_RE.fullmatch(token)
    if shorthand_match:
        return IssueReference(repo=shorthand_match.group("repo"), number=int(shorthand_match.group("number")))
    if token.isdigit():
        if not default_repo:
            raise ValueError("numeric issue references require --repo")
        return IssueReference(repo=default_repo, number=int(token))
    raise ValueError(f"unsupported GitHub issue reference: {reference}")


def extract_issue_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        dedupe(
            [
                *(f"{match.group('repo')}#{match.group('number')}" for match in ISSUE_TOKEN_RE.finditer(value or "")),
                *(f"{match.group('repo')}#{match.group('number')}" for match in _ISSUE_URL_SCAN_RE.finditer(value or "")),
            ]
        )
    )


def format_issue_token(*, repo: str, number: int) -> str:
    return f"{repo}#{number}"


def format_issue_url(*, repo: str, number: int) -> str:
    return f"https://github.com/{repo}/issues/{number}"


def format_issue_markdown_link(*, repo: str, number: int) -> str:
    token = format_issue_token(repo=repo, number=number)
    return f"[{token}]({format_issue_url(repo=repo, number=number)})"


def normalize_version(value: str) -> str:
    return str(value or "").strip().lstrip("v")


def dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
