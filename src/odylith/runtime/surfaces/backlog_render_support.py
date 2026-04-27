"""Shared backlog render helpers for Radar page and payload builders.

This module owns the low-level path, section, and metadata helpers shared by
the main Radar renderer, standalone detail pages, and the client payload
builder so those extracted files do not tunnel back through the renderer.
"""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import quote

from odylith.runtime.common import repo_path_resolver
from odylith.runtime.surfaces import backlog_rich_text
from odylith.runtime.surfaces import render_backlog_ui_html_runtime
from odylith.runtime.surfaces import surface_path_helpers

_DATE_TOKEN_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PLAN_UPDATED_RE = re.compile(r"(?im)^Updated:\s*(\d{4}-\d{2}-\d{2})\s*$")
_PLAN_CREATED_RE = re.compile(r"(?im)^Created:\s*(\d{4}-\d{2}-\d{2})\s*$")
_PLAN_FILENAME_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_IDEA_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_BACKLOG_SUMMARY_HEAVY_FIELDS = frozenset(
    {
        "idea_file",
        "idea_ui_file",
        "promoted_to_plan_file",
        "promoted_to_plan_ui_file",
    }
)
_TRACEABILITY_INDEX_EDGE_TYPES = frozenset(
    {
        "parent_child",
        "depends_on",
        "blocks",
        "reopens",
        "split",
        "merged",
    }
)


def _resolve_path(*, repo_root: Path, value: str) -> Path:
    """Resolve one repo-relative token against the current repo root."""

    return surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=value)


def _as_relative_href(*, output_path: Path, target: Path) -> str:
    """Render a relative href from one generated output to another path."""

    return surface_path_helpers.relative_href(output_path=output_path, target=target)


def _as_portable_relative_href(*, output_path: Path, target: Path) -> str:
    """Render a portable relative href for generated Radar standalone pages."""

    return surface_path_helpers.portable_relative_href(output_path=output_path, token=str(target))


def _as_repo_path(*, repo_root: Path, target: Path) -> str:
    """Render a stable repo-relative display path."""

    return repo_path_resolver.display_repo_path(repo_root=repo_root, value=target)


def _radar_route_href(
    *,
    source_output_path: Path,
    target_output_path: Path,
    workstream_id: str,
    view: str | None = None,
) -> str:
    """Build a Radar shell route into the generated backlog surface."""

    base_href = _as_portable_relative_href(output_path=source_output_path, target=target_output_path)
    workstream = str(workstream_id or "").strip()
    if not workstream:
        return base_href
    query_bits = [f"workstream={quote(workstream, safe='')}"]
    if view:
        query_bits.insert(0, f"view={quote(str(view).strip(), safe='')}")
    return f"{base_href}?{'&'.join(query_bits)}"


def _extract_sections_with_body(path: Path) -> list[tuple[str, list[str]]]:
    """Parse markdown `##` sections into ordered title/body pairs."""

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = line[3:].strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, current_lines))
    return sections


def _extract_sections_from_markdown(path: Path) -> dict[str, str]:
    """Flatten markdown `##` sections into one summary string per heading."""

    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        sections[current].append(line)

    normalized: dict[str, str] = {}
    for key, raw_lines in sections.items():
        merged = " ".join(token.strip() for token in raw_lines if token.strip())
        normalized[key] = merged.strip()
    return normalized


def _split_metadata_ids(*, value: str, pattern: re.Pattern[str]) -> list[str]:
    """Parse comma or semicolon separated metadata ids with contract filtering."""

    values: list[str] = []
    for raw in str(value or "").replace(";", ",").split(","):
        token = raw.strip()
        if not token or not pattern.fullmatch(token):
            continue
        values.append(token)
    return sorted(set(values))


def _extract_plan_dates(plan_path: Path) -> tuple[str, str, str]:
    """Return `(created_date, updated_date, filename_date)` from plan metadata."""

    filename_date = ""
    filename_match = _PLAN_FILENAME_DATE_RE.search(plan_path.name)
    if filename_match is not None:
        token = str(filename_match.group(1)).strip()
        if _DATE_TOKEN_RE.fullmatch(token):
            filename_date = token

    if not plan_path.is_file():
        return "", "", filename_date

    content = plan_path.read_text(encoding="utf-8")
    created = ""
    created_match = _PLAN_CREATED_RE.search(content)
    if created_match is not None:
        token = str(created_match.group(1)).strip()
        if _DATE_TOKEN_RE.fullmatch(token):
            created = token

    updated_match = _PLAN_UPDATED_RE.search(content)
    if updated_match is not None:
        updated = str(updated_match.group(1)).strip()
        if _DATE_TOKEN_RE.fullmatch(updated):
            return created, updated, filename_date

    return created, "", filename_date


def _rewrite_section_text(*, repo_root: Path, text: str) -> str:
    """Normalize inline repo references in standalone Radar content blocks."""

    return backlog_rich_text._rewrite_section_text(repo_root=repo_root, text=text)


def _render_section_body(*, repo_root: Path, lines: list[str]) -> str:
    """Render markdown body lines through the shared backlog HTML formatter."""

    return render_backlog_ui_html_runtime._render_section_body(repo_root=repo_root, lines=lines)
