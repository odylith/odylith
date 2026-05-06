"""Compatibility normalization for host-authored greenfield proposals.

Host models are expected to author the project reasoning, but they should not
need to rediscover every internal Odylith field spelling. This module accepts
common proposal shapes and normalizes them into the strict apply schema before
validation and Tribunal review.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR


_VALID_QUALIFICATIONS = {"candidate", "curated"}
_VALID_MODES = {"host_reasoned_greenfield_proposal", "host_reasoned_proposal"}


def normalize_host_reasoned_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return a strict-schema proposal from a reasonable host-authored shape."""

    normalized = copy.deepcopy(dict(proposal))
    if str(normalized.get("mode", "")).strip() not in _VALID_MODES:
        normalized["mode"] = "host_reasoned_greenfield_proposal"
    intent = _proposal_object(normalized.get("intent"))
    title = _text(intent.get("title")) or _text(intent.get("name")) or "Greenfield Project"
    project_slug = slugify(_text(intent.get("project_slug")) or title)
    intent.setdefault("title", title)
    intent.setdefault("project_slug", project_slug)
    normalized["intent"] = intent

    for key in ("assumptions", "open_questions", "risks"):
        normalized[key] = _proposal_sequence(normalized.get(key))
    normalized["validation_strategy"] = _normalize_validation_strategy(normalized.get("validation_strategy"))
    normalized["release_plan"] = _normalize_release_plan(normalized.get("release_plan"))
    releases = _release_rows(normalized["release_plan"])
    slug_map = _diagram_slug_map(normalized.get("diagrams"), project_slug=project_slug)
    normalized["program"] = _normalize_program(normalized.get("program"), release_rows=releases)
    normalized["backlog"] = _normalize_backlog(normalized.get("backlog"), release_rows=releases, slug_map=slug_map)
    normalized["components"] = _normalize_components(normalized.get("components"))
    normalized["diagrams"] = _normalize_diagrams(
        normalized.get("diagrams"),
        components=normalized["components"],
        slug_map=slug_map,
    )
    return normalized


def _proposal_object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _proposal_sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Mapping):
        rows: list[Any] = []
        for key, nested in value.items():
            if isinstance(nested, list):
                rows.extend(nested)
            elif isinstance(nested, Mapping):
                row = dict(nested)
                row.setdefault("scope", str(key))
                rows.append(row)
            elif _text(nested):
                rows.append(f"{key}: {_text(nested)}")
        return rows
    return [_text(value)] if _text(value) else []


def _normalize_validation_strategy(value: Any) -> list[Any]:
    rows = _proposal_sequence(value)
    if rows:
        return rows
    return [
        "Define focused behavior proof for each first-slice workstream before implementation starts.",
        "Render Radar, Registry, Atlas, and Compass after proposal acceptance.",
    ]


def _normalize_release_plan(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        rows = [_proposal_object(row) for row in value if isinstance(row, Mapping)]
        first = rows[0] if rows else {}
        selector = _text(first.get("release")) or DEFAULT_GREENFIELD_RELEASE_SELECTOR
        target_workstreams = first.get("first_target_workstreams") or first.get("target_workstreams") or []
        label = greenfield_programs.compact_release_target_label(selector)
        return {
            "selector": selector,
            "label": label,
            "provisional_release_id": _text(first.get("provisional_release_id")) or f"release-{slugify(selector)}",
            "strategy": _text(first.get("strategy"))
            or "Promote the accepted first wave through explicit release gates.",
            "target_workstreams": target_workstreams,
            "release_stages": rows,
            "milestones": _release_milestones(rows),
            "promotion_criteria": _release_promotion_criteria(rows),
        }
    plan = _proposal_object(value)
    releases = plan.pop("releases", None)
    stages = plan.get("release_stages")
    if not isinstance(stages, list) or not stages:
        stages = releases if isinstance(releases, list) else []
    stage_rows = [_proposal_object(row) for row in stages if isinstance(row, Mapping)]
    first = stage_rows[0] if stage_rows else {}
    selector = (
        _text(plan.get("selector"))
        or _text(plan.get("default_release"))
        or _text(first.get("release"))
        or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    )
    plan["selector"] = selector
    plan["label"] = greenfield_programs.compact_release_target_label(selector)
    plan.setdefault("provisional_release_id", f"release-{slugify(selector)}")
    if "target_workstreams" not in plan and "target_workstream_titles" not in plan:
        targets = first.get("first_target_workstreams") or first.get("target_workstreams")
        if targets:
            plan["target_workstreams"] = targets
    plan["release_stages"] = stage_rows
    if not plan.get("milestones"):
        plan["milestones"] = _release_milestones(stage_rows)
    if not plan.get("promotion_criteria"):
        plan["promotion_criteria"] = _release_promotion_criteria(stage_rows)
    plan.setdefault("strategy", "Promote accepted greenfield work through explicit release gates.")
    return plan


def _release_rows(release_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [_proposal_object(row) for row in release_plan.get("release_stages", []) if isinstance(row, Mapping)]


def _release_milestones(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    milestones: list[str] = []
    for row in rows:
        release = _text(row.get("release")) or "release"
        gate = _text(row.get("exit_criteria")) or _text(row.get("release_gate"))
        if gate:
            milestones.append(f"{release}: {gate}")
    return milestones or ["Proposal accepted and first release target reviewed."]


def _release_promotion_criteria(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    criteria = [
        _text(row.get("exit_criteria")) or _text(row.get("release_gate"))
        for row in rows
    ]
    return [item for item in criteria if item] or ["First-wave validation gates are satisfied."]


def _release_gate_for(value: Any, *, release_rows: Sequence[Mapping[str, Any]]) -> str:
    selector = _text(value)
    for row in release_rows:
        if selector and _text(row.get("release")) == selector:
            return _text(row.get("exit_criteria")) or _text(row.get("release_gate"))
    return ""


def _normalize_program(value: Any, *, release_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    program = _proposal_object(value)
    waves = []
    for index, raw in enumerate(_proposal_sequence(program.get("waves")), start=1):
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        row.setdefault("wave_id", _text(row.get("id")) or _text(row.get("wave")) or f"W{index}")
        row.setdefault("label", _text(row.get("title")) or _text(row.get("name")) or str(row["wave_id"]))
        row.setdefault("goal", _text(row.get("summary")) or f"Deliver {row['label']}.")
        gate = (
            _text(row.get("validation_gate"))
            or _text(row.get("validation"))
            or _text(row.get("exit_gate"))
            or _release_gate_for(row.get("release"), release_rows=release_rows)
        )
        if gate:
            row.setdefault("validation_gate", gate)
        waves.append(row)
    program["waves"] = waves
    return program


def _diagram_slug_map(value: Any, *, project_slug: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            continue
        original = slugify(_text(raw.get("slug")) or _text(raw.get("title")))
        if not original:
            continue
        target = (
            original
            if _slug_already_project_scoped(original, project_slug=project_slug)
            else f"{project_slug}-{original}"
        )
        mapping[original] = target
    return mapping


def _slug_already_project_scoped(slug: str, *, project_slug: str) -> bool:
    if slug == project_slug or slug.startswith(f"{project_slug}-"):
        return True
    project_tokens = [token for token in project_slug.split("-") if len(token) >= 4]
    slug_tokens = {token for token in slug.split("-") if len(token) >= 4}
    if len(project_tokens) >= 2:
        return all(token in slug_tokens for token in project_tokens[:2])
    if len(project_tokens) == 1:
        return slug.startswith(f"{project_tokens[0]}-")
    return False


def _remap_diagram_refs(value: Any, slug_map: Mapping[str, str]) -> Any:
    if isinstance(value, list):
        return [_remap_diagram_refs(item, slug_map) for item in value]
    token = slugify(_text(value))
    return slug_map.get(token, value)


def _normalize_backlog(
    value: Any,
    *,
    release_rows: Sequence[Mapping[str, Any]],
    slug_map: Mapping[str, str],
) -> list[Any]:
    rows: list[Any] = []
    for index, raw in enumerate(_proposal_sequence(value), start=1):
        if not isinstance(raw, Mapping):
            rows.append(raw)
            continue
        row = dict(raw)
        row.setdefault("evidence_tier", "user_intent" if index == 1 else "odylith_assumption")
        first_slice = _text(row.get("recommended_first_slice")) or _text(row.get("first_slice_proof"))
        if not first_slice:
            first_slice = _text(row.get("validation")) or _release_gate_for(
                row.get("release"),
                release_rows=release_rows,
            )
        if first_slice:
            row["recommended_first_slice"] = first_slice
        if "related_components" in row and "component_focus" not in row:
            row["component_focus"] = row.get("related_components")
        if "related_diagram_slugs" in row:
            row["related_diagram_slugs"] = _remap_diagram_refs(row.get("related_diagram_slugs"), slug_map)
        rows.append(row)
    return rows


def _normalize_components(value: Any) -> list[Any]:
    rows: list[Any] = []
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            rows.append(raw)
            continue
        row = dict(raw)
        row.setdefault("component_id", _text(row.get("id")) or _text(row.get("name")) or _text(row.get("label")))
        row.setdefault("label", _text(row.get("name")) or _text(row.get("component_id")))
        row.setdefault("kind", _text(row.get("type")) or "service")
        row.setdefault("intended_path", _text(row.get("path")) or f"src/{slugify(row.get('component_id'))}")
        row.setdefault("status", "planned")
        qualification = _text(row.get("qualification")).casefold()
        row["qualification"] = qualification if qualification in _VALID_QUALIFICATIONS else "candidate"
        if "proof_expectations" in row and "validation" not in row:
            row["validation"] = row.get("proof_expectations")
        row.setdefault("evidence_tier", "user_intent")
        rows.append(row)
    return rows


def _component_descriptions(components: Sequence[Any]) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for row in components:
        if not isinstance(row, Mapping):
            continue
        for key in (_text(row.get("component_id")), _text(row.get("label")), _text(row.get("name"))):
            slug = slugify(key)
            if slug:
                descriptions[slug] = _text(row.get("responsibility")) or f"Planned component {key}."
    return descriptions


def _normalize_diagrams(
    value: Any,
    *,
    components: Sequence[Any],
    slug_map: Mapping[str, str],
) -> list[Any]:
    descriptions = _component_descriptions(components)
    rows: list[Any] = []
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            rows.append(raw)
            continue
        row = dict(raw)
        original_slug = slugify(_text(row.get("slug")) or _text(row.get("title")))
        if original_slug in slug_map:
            row["slug"] = slug_map[original_slug]
        row.setdefault("kind", _text(row.get("type")) or "flowchart")
        source = row.get("mermaid_source") or row.get("source")
        if _text(source):
            row["mermaid_source"] = _normalize_mermaid_source(str(source))
        row.setdefault("link_state", _text(row.get("status")) or "atlas_first_draft")
        row.setdefault("evidence_tier", "user_intent")
        related = row.get("related_components")
        if "components" not in row and related:
            component_rows = []
            for item in _proposal_sequence(related):
                name = _text(item)
                if not name:
                    continue
                component_rows.append(
                    {
                        "name": name,
                        "description": descriptions.get(slugify(name), f"Planned component {name}."),
                    }
                )
            row["components"] = component_rows
        rows.append(row)
    return rows


def _normalize_mermaid_source(source: str) -> str:
    first_line = next(
        (line.strip() for line in source.splitlines() if line.strip() and not line.strip().startswith("%%")),
        "",
    )
    if first_line != "sequenceDiagram":
        return source
    normalized_lines = []
    for line in source.splitlines():
        head, separator, message = line.partition(":")
        if separator and ";" in message:
            line = f"{head}:{message.replace(';', ' and')}"
        normalized_lines.append(line)
    return "\n".join(normalized_lines)


__all__ = ["normalize_host_reasoned_proposal"]
