"""Plan traceability path extraction for generated Radar surfaces.

The Radar shell, standalone plan pages, and traceability payload builders all
need the same view of paths listed under a plan's ``## Traceability`` section.
Keeping that parser outside the HTML renderer prevents detail surfaces from
depending on the giant browser template just to understand repo path evidence.
"""

from __future__ import annotations

from pathlib import Path
import re

from odylith.runtime.surfaces import backlog_rich_text

TRACEABILITY_SECTION_NAME = "Traceability"
TRACEABILITY_BUCKETS: tuple[str, ...] = (
    "Runbooks",
    "Developer Docs",
    "Code References",
)

_PATH_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
_PATH_CODE_RE = re.compile(r"`([^`\n]+)`")
_CHECKBOX_PREFIX_RE = re.compile(r"^\[(?:x|X| )\]\s*")
_LINE_SUFFIX_RE = re.compile(r"^(?P<path>.+?):\d+(?::\d+)?$")
_BUCKET_LOOKUP = {label.casefold(): label for label in TRACEABILITY_BUCKETS}


def is_traceability_section(title: str) -> bool:
    """Return whether a markdown section title is the plan traceability block."""

    normalized = str(title or "").strip().rstrip(":").strip().lower()
    return normalized == TRACEABILITY_SECTION_NAME.lower()


def extract_path_tokens(text: str) -> list[str]:
    """Collect markdown link targets and inline-code path tokens from one line."""

    tokens: list[str] = []
    for match in _PATH_LINK_RE.finditer(str(text or "")):
        token = str(match.group(1)).strip()
        if token.startswith("<") and token.endswith(">"):
            token = token[1:-1].strip()
        if token:
            tokens.append(token)
    for match in _PATH_CODE_RE.finditer(str(text or "")):
        token = str(match.group(1)).strip()
        if token:
            tokens.append(token)
    return tokens


def _canonical_bucket(label: str) -> str:
    candidate = str(label or "").strip().rstrip(":").strip().casefold()
    return _BUCKET_LOOKUP.get(candidate, "")


def _strip_path_decorators(token: str) -> str:
    stripped = str(token or "").strip()
    for separator in ("#", "?"):
        stripped = stripped.split(separator, 1)[0].strip()
    line_match = _LINE_SUFFIX_RE.fullmatch(stripped)
    if line_match is not None:
        stripped = str(line_match.group("path") or "").strip()
    return stripped


def normalize_path(*, repo_root: Path, token: str) -> str:
    """Normalize one traceability path token into a repo-relative display path."""

    root = Path(repo_root).resolve()
    normalized = backlog_rich_text.normalize_inline_repo_token(
        repo_root=root,
        token=_strip_path_decorators(token),
    )
    if not normalized:
        return ""
    candidate = Path(normalized)
    if candidate.is_absolute():
        return ""
    try:
        relative = (root / normalized).resolve().relative_to(root)
    except ValueError:
        return ""
    collapsed = relative.as_posix().strip()
    if not collapsed or collapsed == ".":
        return ""
    return collapsed


def collect_plan_paths(
    *,
    repo_root: Path,
    sections: list[tuple[str, list[str]]],
) -> dict[str, list[str]]:
    """Collect normalized traceability paths grouped by supported bucket label."""

    raw_traceability_lines: list[str] = []
    for title, lines in sections:
        if is_traceability_section(title):
            raw_traceability_lines = lines
            break
    if not raw_traceability_lines:
        return {}

    bucket: str | None = None
    grouped: dict[str, list[str]] = {label: [] for label in TRACEABILITY_BUCKETS}
    for line in raw_traceability_lines:
        stripped = str(line or "").strip()
        if stripped.startswith("### "):
            candidate = stripped[4:].strip()
            bucket = _canonical_bucket(candidate) or None
            continue
        if bucket is None or not stripped:
            continue
        marker = stripped.lstrip()[:2]
        if marker not in {"- ", "* "}:
            continue
        body = stripped.lstrip()[2:].strip()
        body = _CHECKBOX_PREFIX_RE.sub("", body).strip()
        for token in extract_path_tokens(body):
            normalized = normalize_path(repo_root=repo_root, token=token)
            if normalized:
                grouped[bucket].append(normalized)

    collapsed: dict[str, list[str]] = {}
    for label, values in grouped.items():
        deduped = sorted(set(values))
        if deduped:
            collapsed[label] = deduped
    return collapsed
