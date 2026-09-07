"""Greenfield first-release targeting helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_traceability import allocated_workstreams

DEFAULT_GREENFIELD_RELEASE_SELECTOR = "0.0.1"

_SEMVER_SELECTOR_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_RELEASE_TARGET_VERSION_RE = re.compile(r"\bv?(\d+(?:\.\d+){1,3})\b", re.IGNORECASE)
_MAX_RELEASE_TARGET_LABEL_CHARS = 18


def release_target_version_token(value: str) -> str:
    """Return the numeric release token embedded in an operator release target."""

    match = _RELEASE_TARGET_VERSION_RE.search(" ".join(str(value or "").split()))
    return match.group(1) if match else ""


def compact_release_target_label(value: str, *, fallback: str = DEFAULT_GREENFIELD_RELEASE_SELECTOR) -> str:
    """Return a dashboard-safe greenfield release target label.

    Greenfield first-release targets must display as plain numeric selectors
    such as ``0.0.1``. If an operator supplies a custom target with extra words,
    prefer the embedded numeric selector; otherwise keep a short trimmed label so
    KPI cards do not wrap or overflow.
    """

    text = " ".join(str(value or "").split()).strip()
    version_token = release_target_version_token(text)
    if version_token:
        return version_token
    label = text or str(fallback or "").strip() or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    if len(label) <= _MAX_RELEASE_TARGET_LABEL_CHARS:
        return label
    return label[: _MAX_RELEASE_TARGET_LABEL_CHARS - 3].rstrip() + "..."


def proposal_release_selector(proposal: Mapping[str, Any], explicit_selector: str = "") -> str:
    explicit = str(explicit_selector or "").strip()
    if explicit:
        return explicit
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    selector = str(release_plan.get("selector", "")).strip()
    return selector or DEFAULT_GREENFIELD_RELEASE_SELECTOR


def semver_release_metadata(*, selector: str, release_plan: Mapping[str, Any]) -> tuple[str, str]:
    version = str(release_plan.get("version", "")).strip()
    tag = str(release_plan.get("tag", "")).strip()
    version = release_target_version_token(version) or version
    selector_version = release_target_version_token(selector)
    if _SEMVER_SELECTOR_RE.fullmatch(selector) or selector_version:
        version = version or selector_version or selector
        tag = tag or f"v{version}"
    return version, tag


def first_release_workstream_ids(
    *, proposal: Mapping[str, Any], created_backlog: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Resolve only explicit release membership against validated canonical allocations."""

    workstreams = allocated_workstreams(proposal=proposal, created_backlog=created_backlog)
    release_plan = proposal.get("release_plan")
    titles = release_plan.get("target_workstream_titles") if isinstance(release_plan, Mapping) else None
    by_title = {row.title: row.idea_id for row in workstreams}
    if (
        not isinstance(titles, list) or not titles
        or any(not isinstance(title, str) or title not in by_title for title in titles)
        or len(set(titles)) != len(titles)
    ):
        raise ValueError("Greenfield first release requires exact, unique allocated workstream titles")
    return [by_title[title] for title in titles]
