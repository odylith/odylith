"""Fail-closed validation for Casebook markdown source records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.install.fs import display_path

CASEBOOK_BUGS_RELATIVE = Path("odylith/casebook/bugs")
REPRODUCIBILITY_HELP = (
    "one compact token such as High, Medium, Low, Always, Intermittent, or Consistent"
)

_SKIPPED_MARKDOWN_NAMES = frozenset({"AGENTS.md", "CLAUDE.md", "INDEX.md"})
_REPRODUCIBILITY_FIELD_RE = re.compile(r"^\s*-\s*Reproducibility:\s*(?P<value>.*)$")
_REPRODUCIBILITY_TOKEN_RE = re.compile(r"^[A-Za-z]{2,24}$")
_PLACEHOLDER_RE = re.compile(
    r"^(?:tbd|todo|unknown|n/?a|pending|to be determined|not yet known|not yet determined)(?:\b|[^A-Za-z0-9].*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CasebookSourceIssue:
    """One fail-closed validation issue found in a Casebook source record."""

    path: Path
    line: int
    field: str
    value: str
    message: str

    def as_dict(self, *, repo_root: Path) -> dict[str, Any]:
        """Return a JSON-serializable representation of the issue."""
        return {
            "path": display_path(repo_root=repo_root, path=self.path),
            "line": self.line,
            "field": self.field,
            "value": self.value,
            "message": self.message,
        }

    def render(self, *, repo_root: Path) -> str:
        """Render the issue in a CLI-friendly single-line format."""
        value_suffix = f" value={self.value!r}" if self.value else ""
        return (
            f"{display_path(repo_root=repo_root, path=self.path)}:{self.line}: "
            f"{self.field}: {self.message}{value_suffix}"
        )


@dataclass(frozen=True)
class CasebookSourceValidationResult:
    """Result payload for a full Casebook source validation pass."""

    repo_root: Path
    records_checked: int
    issues: tuple[CasebookSourceIssue, ...]

    @property
    def passed(self) -> bool:
        """Return whether the validation pass found no issues."""
        return not self.issues

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the validation result."""
        return {
            "passed": self.passed,
            "records_checked": self.records_checked,
            "issue_count": len(self.issues),
            "issues": [issue.as_dict(repo_root=self.repo_root) for issue in self.issues],
        }


def normalize_reproducibility_token(value: str | Sequence[str] | None) -> str:
    """Normalize a reproducibility field into the compact canonical token shape."""
    token = _normalize_scalar(value)
    if not token:
        return ""
    if token.isalpha():
        return token[:1].upper() + token[1:].lower()
    return token


def reproducibility_token_is_valid(value: str | Sequence[str] | None) -> bool:
    """Return whether the reproducibility field is a single accepted token."""
    token = _normalize_scalar(value)
    return bool(token) and _REPRODUCIBILITY_TOKEN_RE.fullmatch(token) is not None and not _looks_placeholder(token)


def iter_casebook_bug_markdown_paths(*, repo_root: Path) -> tuple[Path, ...]:
    """Return the Casebook markdown records that participate in source validation."""
    bugs_root = (Path(repo_root).resolve() / CASEBOOK_BUGS_RELATIVE).resolve()
    if not bugs_root.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in bugs_root.rglob("*.md")
            if path.name not in _SKIPPED_MARKDOWN_NAMES
        )
    )


def validate_casebook_sources(*, repo_root: Path) -> CasebookSourceValidationResult:
    """Validate every Casebook markdown record under the repo root."""
    root = Path(repo_root).resolve()
    paths = iter_casebook_bug_markdown_paths(repo_root=root)
    issues: list[CasebookSourceIssue] = []
    for path in paths:
        issues.extend(_validate_casebook_bug_file(path))
    return CasebookSourceValidationResult(
        repo_root=root,
        records_checked=len(paths),
        issues=tuple(issues),
    )


def print_casebook_source_validation_report(
    result: CasebookSourceValidationResult,
    *,
    stream: Any | None = None,
) -> None:
    """Render the validation result as a human-readable CLI report."""
    target = stream if stream is not None else sys.stdout
    if result.passed:
        print("casebook source validation passed", file=target)
        print(f"- records_checked: {result.records_checked}", file=target)
        return
    print("casebook source validation failed", file=target)
    print(f"- records_checked: {result.records_checked}", file=target)
    print(f"- issue_count: {len(result.issues)}", file=target)
    for issue in result.issues:
        print(f"- {issue.render(repo_root=result.repo_root)}", file=target)


def validate_or_report(*, repo_root: Path, stream: Any | None = None) -> int:
    """Validate Casebook records, print the report, and return the CLI exit code."""
    result = validate_casebook_sources(repo_root=repo_root)
    print_casebook_source_validation_report(result, stream=stream)
    return 0 if result.passed else 2


def _issue(*, path: Path, line: int, field: str, value: str, message: str) -> CasebookSourceIssue:
    """Build one validation issue with the canonical payload shape."""
    return CasebookSourceIssue(
        path=path,
        line=line,
        field=field,
        value=value,
        message=message,
    )


def _validate_casebook_bug_file(path: Path) -> list[CasebookSourceIssue]:
    """Validate one Casebook markdown record and return every issue found."""
    issues: list[CasebookSourceIssue] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [
            _issue(
                path=path,
                line=1,
                field="file",
                value="",
                message=f"could not read Casebook bug source: {exc}",
            )
        ]
    matches: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        match = _REPRODUCIBILITY_FIELD_RE.match(line)
        if match:
            matches.append((index, str(match.group("value") or "").strip()))
    if not matches:
        return [
            _issue(
                path=path,
                line=1,
                field="Reproducibility",
                value="",
                message="missing required Casebook bug field",
            )
        ]
    if len(matches) > 1:
        for line_number, value in matches[1:]:
            issues.append(
                _issue(
                    path=path,
                    line=line_number,
                    field="Reproducibility",
                    value=value,
                    message="duplicate Casebook bug field",
                )
            )
    line_number, value = matches[0]
    if not reproducibility_token_is_valid(value):
        issues.append(
            _issue(
                path=path,
                line=line_number,
                field="Reproducibility",
                value=value,
                message=f"must be {REPRODUCIBILITY_HELP}; put repro steps in evidence fields",
            )
        )
    return issues


def _looks_placeholder(value: str) -> bool:
    """Return whether a token is clearly placeholder text rather than evidence."""
    token = str(value or "").strip()
    return bool(token) and _PLACEHOLDER_RE.fullmatch(token) is not None


def _normalize_scalar(value: str | Sequence[str] | None) -> str:
    """Normalize scalar or list-like input into compact text for validation."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="ignore").strip()
    return "\n".join(str(item).strip() for item in value if str(item).strip()).strip()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Casebook source validation."""
    parser = argparse.ArgumentParser(
        prog="odylith casebook validate",
        description="Validate Casebook markdown source records before rendering.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Render the validation result as JSON.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for Casebook source validation."""
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()
    result = validate_casebook_sources(repo_root=repo_root)
    if bool(args.as_json):
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print_casebook_source_validation_report(result)
    return 0 if result.passed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
