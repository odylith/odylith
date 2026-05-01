"""GitHub REST transport for the draft-first issue pipeline."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol, Sequence


class GitHubPipelineError(RuntimeError):
    """Raised when GitHub issue pipeline work cannot proceed safely."""


class GitHubTransport(Protocol):
    """Small GitHub transport contract used by CLI and tests."""

    def get_issue(self, *, repo: str, number: int) -> Mapping[str, Any]:
        ...

    def list_issues(self, *, repo: str, state: str) -> Sequence[Mapping[str, Any]]:
        ...

    def list_labels(self, *, repo: str) -> Sequence[Mapping[str, Any]]:
        ...

    def create_label(self, *, repo: str, name: str, description: str, color: str) -> None:
        ...

    def add_labels(self, *, repo: str, number: int, labels: Sequence[str]) -> None:
        ...

    def comment_issue(self, *, repo: str, number: int, body: str) -> None:
        ...

    def close_issue(self, *, repo: str, number: int) -> None:
        ...

    def get_release_by_tag(self, *, repo: str, tag: str) -> Mapping[str, Any] | None:
        ...


class GitHubRestTransport:
    """GitHub REST adapter for public reads and token-gated writes."""

    def __init__(self, *, token: str | None = None, api_root: str = "https://api.github.com") -> None:
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        self._api_root = api_root.rstrip("/")

    def get_issue(self, *, repo: str, number: int) -> Mapping[str, Any]:
        return self._request_json("GET", f"/repos/{repo}/issues/{number}")

    def list_issues(self, *, repo: str, state: str) -> Sequence[Mapping[str, Any]]:
        payload = self._request_json("GET", f"/repos/{repo}/issues?state={state}&per_page=100")
        return payload if isinstance(payload, list) else []

    def list_labels(self, *, repo: str) -> Sequence[Mapping[str, Any]]:
        payload = self._request_json("GET", f"/repos/{repo}/labels?per_page=100")
        return payload if isinstance(payload, list) else []

    def create_label(self, *, repo: str, name: str, description: str, color: str) -> None:
        self._require_token("create labels")
        self._request_json(
            "POST",
            f"/repos/{repo}/labels",
            {"name": name, "description": description, "color": color},
        )

    def add_labels(self, *, repo: str, number: int, labels: Sequence[str]) -> None:
        self._require_token("add labels")
        self._request_json("POST", f"/repos/{repo}/issues/{number}/labels", {"labels": list(labels)})

    def comment_issue(self, *, repo: str, number: int, body: str) -> None:
        self._require_token("comment on issues")
        self._request_json("POST", f"/repos/{repo}/issues/{number}/comments", {"body": body})

    def close_issue(self, *, repo: str, number: int) -> None:
        self._require_token("close issues")
        self._request_json("PATCH", f"/repos/{repo}/issues/{number}", {"state": "closed"})

    def get_release_by_tag(self, *, repo: str, tag: str) -> Mapping[str, Any] | None:
        try:
            return self._request_json("GET", f"/repos/{repo}/releases/tags/{tag}")
        except GitHubPipelineError as exc:
            if "404" in str(exc):
                return None
            raise

    def _require_token(self, action: str) -> None:
        if not self._token:
            raise GitHubPipelineError(f"GitHub token required to {action}; set GITHUB_TOKEN or GH_TOKEN.")

    def _request_json(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self._api_root}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "odylith-github-issue-pipeline",
                **({"Authorization": f"Bearer {self._token}"} if self._token else {}),
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubPipelineError(f"GitHub API {method} {path} failed with {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubPipelineError(f"GitHub API {method} {path} failed: {exc.reason}") from exc
        return json.loads(raw) if raw else {}


def build_transport() -> GitHubTransport:
    """Build the default GitHub transport."""
    return GitHubRestTransport()
