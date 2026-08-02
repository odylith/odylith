"""Greenfield first-release targeting helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import text_values

DEFAULT_GREENFIELD_RELEASE_SELECTOR = "0.0.1"

_IDEA_ID_RE = re.compile(r"^B-\d{3,}$", re.IGNORECASE)
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
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
) -> list[str]:
    created_ids = [
        str(item.get("idea_id", "")).strip().upper()
        for item in created_backlog
        if str(item.get("idea_id", "")).strip()
    ]
    if not created_ids:
        return []
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    proposal_backlog = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    explicit = _resolve_workstream_refs(
        _workstream_refs(release_plan),
        created_backlog=created_backlog,
        proposal_backlog=proposal_backlog,
    )
    selected = [created_ids[0]]
    if explicit:
        selected.extend(item for item in explicit if item not in selected)
    else:
        selected.extend(item for item in created_ids[1:4] if item not in selected)
    return [item for item in selected if item in created_ids]


def _created_title_map(
    created_backlog: Sequence[Mapping[str, Any]],
    proposal_backlog: Sequence[Mapping[str, Any]] = (),
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index, item in enumerate(created_backlog):
        idea_id = str(item.get("idea_id", "")).strip().upper()
        title = str(item.get("title", "")).strip()
        if not idea_id:
            continue
        _add_ref_mapping(mapping, idea_id=idea_id, value=idea_id)
        _add_ref_mapping(mapping, idea_id=idea_id, value=title)
        raw = proposal_backlog[index] if index < len(proposal_backlog) else {}
        if isinstance(raw, Mapping):
            for key in (
                "id",
                "idea_id",
                "workstream_id",
                "slug",
                "title",
                "name",
                "label",
            ):
                _add_ref_mapping(mapping, idea_id=idea_id, value=raw.get(key))
    return mapping


def _add_ref_mapping(mapping: dict[str, str], *, idea_id: str, value: Any) -> None:
    token = str(value or "").strip()
    if not token:
        return
    mapping[token.casefold()] = idea_id
    mapping[token.upper()] = idea_id
    slug = slugify(token)
    if slug:
        mapping[slug] = idea_id


def _workstream_refs(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "workstreams",
        "workstream_ids",
        "workstream_titles",
        "target_workstreams",
        "target_workstream_ids",
        "target_workstream_titles",
        "related_workstreams",
        "backlog_titles",
        "primary_workstreams",
    ):
        if key in row:
            values.extend(text_values(row.get(key)))
    return values


def _resolve_workstream_refs(
    refs: Sequence[str],
    *,
    created_backlog: Sequence[Mapping[str, Any]],
    proposal_backlog: Sequence[Mapping[str, Any]] = (),
) -> list[str]:
    title_map = _created_title_map(created_backlog, proposal_backlog)
    created_ids = {str(item.get("idea_id", "")).strip().upper() for item in created_backlog}
    resolved: list[str] = []
    for raw in refs:
        token = str(raw or "").strip()
        if not token:
            continue
        candidate = token.upper()
        if _IDEA_ID_RE.fullmatch(candidate) and candidate in created_ids and candidate not in resolved:
            resolved.append(candidate)
            continue
        for key in (candidate, token.casefold(), slugify(token)):
            mapped = title_map.get(key)
            if mapped and mapped not in resolved:
                resolved.append(mapped)
                break
    return resolved
