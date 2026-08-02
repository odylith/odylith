"""Compatibility normalization for confirmed greenfield proposals.

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
from odylith.runtime.common import mermaid_text
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_text_list
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_project_brief import normalize_project_brief
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import normalize_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import enrich_backlog_rows
from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings

DEFAULT_GREENFIELD_RELEASE_SELECTOR = greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR


_VALID_QUALIFICATIONS = {"candidate", "curated"}
_VALID_MODES = {"host_reasoned_greenfield_proposal", "host_reasoned_proposal"}
_BACKLOG_TEXT_LIST_FIELDS = (
    "success_metrics",
    "dependencies",
    "depends_on",
    "interfaces",
    "interface_changes",
    "validation",
    "test_strategy",
)
_BACKLOG_REF_LIST_FIELDS = (
    "component_focus",
    "components",
    "component_ids",
    "related_components",
    "related_component_ids",
    "related_diagram_slugs",
    "related_diagrams",
    "diagram_slugs",
)
_COMPONENT_TEXT_LIST_FIELDS = (
    "dependencies",
    "depends_on",
    "interfaces",
    "interface_changes",
    "proof_expectations",
    "validation",
    "test_strategy",
)
_WORKSTREAM_REF_LIST_FIELDS = (
    "workstreams",
    "workstream_ids",
    "workstream_titles",
    "target_workstreams",
    "target_workstream_ids",
    "target_workstream_titles",
    "related_workstreams",
    "backlog_titles",
    "primary_workstreams",
    "first_target_workstreams",
)
_WORKSTREAM_TITLE_LIST_FIELDS = (
    "workstream_titles",
    "target_workstream_titles",
    "related_workstream_titles",
    "backlog_titles",
)
_WORKSTREAM_SCALAR_REF_LIST_FIELDS = tuple(
    field for field in _WORKSTREAM_REF_LIST_FIELDS if field not in _WORKSTREAM_TITLE_LIST_FIELDS
)


def normalize_host_reasoned_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return a strict-schema proposal from a reasonable confirmed shape."""

    normalized = copy.deepcopy(dict(proposal))
    if str(normalized.get("mode", "")).strip() not in _VALID_MODES:
        normalized["mode"] = "host_reasoned_greenfield_proposal"
    intent = _proposal_object(normalized.get("intent"))
    title = clean_text(intent.get("title")) or clean_text(intent.get("name")) or "Greenfield Project"
    project_slug = slugify(clean_text(intent.get("project_slug")) or title)
    intent.setdefault("title", title)
    intent.setdefault("project_slug", project_slug)
    normalized["intent"] = intent

    for key in ("assumptions", "open_questions", "risks"):
        normalized[key] = _proposal_sequence(normalized.get(key))
    normalized["validation_strategy"] = _normalize_validation_strategy(normalized.get("validation_strategy"))
    normalized["release_plan"] = _normalize_release_plan(normalized.get("release_plan"))
    normalized["project_brief"] = normalize_project_brief(
        normalized.get("project_brief"),
        intent=normalized["intent"],
        release_selector=clean_text(normalized["release_plan"].get("selector")) or DEFAULT_GREENFIELD_RELEASE_SELECTOR,
    )
    releases = _release_rows(normalized["release_plan"])
    slug_map = _diagram_slug_map(normalized.get("diagrams"), project_slug=project_slug)
    normalized.pop("program", None)
    normalized["backlog"] = _normalize_backlog(normalized.get("backlog"), release_rows=releases, slug_map=slug_map)
    normalized["components"] = _normalize_components(normalized.get("components"))
    normalized["diagrams"] = _normalize_diagrams(
        normalized.get("diagrams"),
        components=normalized["components"],
        slug_map=slug_map,
    )
    normalized["project_intelligence"] = normalize_project_intelligence(
        normalized.get("project_intelligence"),
        intent=normalized["intent"],
        release_selector=clean_text(normalized["release_plan"].get("selector")) or DEFAULT_GREENFIELD_RELEASE_SELECTOR,
        project_brief=normalized["project_brief"],
        release_plan=normalized["release_plan"],
        components=normalized["components"],
        diagrams=normalized["diagrams"],
        observed_source=normalized.get("observed_source") if isinstance(normalized.get("observed_source"), Mapping) else {},
    )
    normalized["backlog"] = enrich_backlog_rows(
        normalized["backlog"],
        intent=normalized["intent"],
        release_plan=normalized["release_plan"],
        validation_strategy=normalized["validation_strategy"],
        security_compliance=normalized.get("security_compliance"),
        components=normalized["components"],
        diagrams=normalized["diagrams"],
    )
    return attach_project_intelligence_bindings(normalized)


def _proposal_object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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
            elif clean_text(nested):
                rows.append(f"{key}: {clean_text(nested)}")
        return rows
    token = clean_text(value)
    return [token] if token else []


def _normalize_list_fields(row: dict[str, Any], fields: Sequence[str], *, split_commas: bool = False) -> None:
    for key in fields:
        if key in row:
            row[key] = normalize_text_list(row.get(key), split_commas=split_commas)


def _normalize_workstream_ref_fields(row: dict[str, Any]) -> None:
    for key in _WORKSTREAM_TITLE_LIST_FIELDS:
        if key in row:
            row[key] = _normalize_workstream_title_refs(row.get(key))
    _normalize_list_fields(row, _WORKSTREAM_SCALAR_REF_LIST_FIELDS, split_commas=True)


def _normalize_workstream_title_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested in value.values():
            values.extend(_normalize_workstream_title_refs(nested))
        return list(unique_text(values))
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested in value:
            values.extend(_normalize_workstream_title_refs(nested))
        return list(unique_text(values))
    raw = str(value or "").strip()
    if not raw:
        return []
    if "\n" not in raw and "\r" not in raw:
        token = clean_text(raw)
        return [token] if token else []
    rows: list[str] = []
    for line in raw.splitlines():
        token = clean_text(line).lstrip("-*").strip()
        if token:
            rows.append(token)
    return list(unique_text(rows))


def _normalize_validation_strategy(value: Any) -> list[Any]:
    return _proposal_sequence(value)


def _normalize_release_plan(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        rows = [_proposal_object(row) for row in value if isinstance(row, Mapping)]
        for row in rows:
            _normalize_workstream_ref_fields(row)
        first = rows[0] if rows else {}
        selector = clean_text(first.get("release")) or DEFAULT_GREENFIELD_RELEASE_SELECTOR
        target_workstreams = first.get("first_target_workstreams") or first.get("target_workstreams") or []
        label = greenfield_programs.compact_release_target_label(selector)
        return {
            "selector": selector,
            "label": label,
            "provisional_release_id": clean_text(first.get("provisional_release_id")) or f"release-{slugify(selector)}",
            "strategy": clean_text(first.get("strategy"))
            or "Promote the accepted first path through explicit release gates.",
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
    for row in stage_rows:
        _normalize_workstream_ref_fields(row)
    first = stage_rows[0] if stage_rows else {}
    selector = (
        clean_text(plan.get("selector"))
        or clean_text(plan.get("default_release"))
        or clean_text(first.get("release"))
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
    _normalize_workstream_ref_fields(plan)
    _normalize_list_fields(plan, ("milestones", "promotion_criteria"))
    return plan


def _release_rows(release_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [_proposal_object(row) for row in release_plan.get("release_stages", []) if isinstance(row, Mapping)]


def _release_milestones(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    milestones: list[str] = []
    for row in rows:
        release = clean_text(row.get("release")) or "release"
        gate = join_sentence_text(row.get("exit_criteria")) or join_sentence_text(row.get("release_gate"))
        if gate:
            milestones.append(f"{release}: {gate}")
    return milestones


def _release_promotion_criteria(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    criteria = [
        join_sentence_text(row.get("exit_criteria")) or join_sentence_text(row.get("release_gate"))
        for row in rows
    ]
    return [item for item in criteria if item]


def _release_gate_for(value: Any, *, release_rows: Sequence[Mapping[str, Any]]) -> str:
    selector = clean_text(value)
    for row in release_rows:
        if selector and clean_text(row.get("release")) == selector:
            return join_sentence_text(row.get("exit_criteria")) or join_sentence_text(row.get("release_gate"))
    return ""


def _diagram_slug_map(value: Any, *, project_slug: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            continue
        original = slugify(clean_text(raw.get("slug")) or clean_text(raw.get("title")))
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
    token = slugify(clean_text(value))
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
        _normalize_list_fields(row, _BACKLOG_TEXT_LIST_FIELDS)
        _normalize_list_fields(row, _BACKLOG_REF_LIST_FIELDS, split_commas=True)
        row.setdefault("evidence_tier", "user_intent" if index == 1 else "odylith_assumption")
        first_slice = _recommended_first_slice(row, release_rows=release_rows)
        if first_slice:
            row["recommended_first_slice"] = first_slice
        if "related_components" in row and "component_focus" not in row:
            row["component_focus"] = row.get("related_components")
        if "related_diagram_slugs" in row:
            row["related_diagram_slugs"] = _remap_diagram_refs(row.get("related_diagram_slugs"), slug_map)
        rows.append(row)
    return rows


def _recommended_first_slice(row: Mapping[str, Any], *, release_rows: Sequence[Mapping[str, Any]]) -> str:
    explicit = clean_text(row.get("recommended_first_slice")) or clean_text(row.get("first_slice_proof"))
    if explicit:
        return explicit
    return _derived_first_slice(row, release_rows=release_rows)


def _derived_first_slice(row: Mapping[str, Any], *, release_rows: Sequence[Mapping[str, Any]]) -> str:
    title = _brief_fragment(row.get("title"), fallback="this workstream", limit=90)
    product_view = _brief_fragment(row.get("product_view"), limit=220)
    if product_view:
        return f"Start {title} with the smallest source-backed slice for this product view: {product_view}."
    opportunity = _brief_fragment(row.get("opportunity"), limit=220)
    if opportunity:
        return f"Start {title} with the smallest source-backed slice for this opportunity: {opportunity}."
    problem = _brief_fragment(row.get("problem"), limit=220)
    if problem:
        return f"Start {title} by proving the smallest behavior that addresses this problem: {problem}."
    release_gate = _brief_fragment(_release_gate_for(row.get("release"), release_rows=release_rows), limit=180)
    if release_gate:
        return f"Start {title} by defining the smallest source-backed behavior needed before this release gate: {release_gate}."
    return f"Start {title} by defining the smallest source-backed behavior, owned state, and proof gate."


def _brief_fragment(value: Any, *, fallback: str = "", limit: int = 220) -> str:
    text = clean_text(value) or fallback
    if not text:
        return ""
    return clip_text_at_word_boundary(text, limit=limit, strip_edges=" .").strip(" ,;:")


def _normalize_components(value: Any) -> list[Any]:
    rows: list[Any] = []
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            rows.append(raw)
            continue
        row = dict(raw)
        row.setdefault("component_id", clean_text(row.get("id")) or clean_text(row.get("name")) or clean_text(row.get("label")))
        row.setdefault("label", clean_text(row.get("name")) or clean_text(row.get("component_id")))
        if "kind" not in row and clean_text(row.get("type")):
            row["kind"] = clean_text(row.get("type"))
        if "intended_path" not in row and clean_text(row.get("path")):
            row["intended_path"] = clean_text(row.get("path"))
        row.setdefault("status", "planned")
        qualification = clean_text(row.get("qualification")).casefold()
        row["qualification"] = qualification if qualification in _VALID_QUALIFICATIONS else "candidate"
        if "proof_expectations" in row and "validation" not in row:
            row["validation"] = row.get("proof_expectations")
        _normalize_list_fields(row, _COMPONENT_TEXT_LIST_FIELDS)
        row.setdefault("evidence_tier", "user_intent")
        rows.append(row)
    return rows


def _normalize_diagrams(
    value: Any,
    *,
    components: Sequence[Any],
    slug_map: Mapping[str, str],
) -> list[Any]:
    rows: list[Any] = []
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            rows.append(raw)
            continue
        row = dict(raw)
        original_slug = slugify(clean_text(row.get("slug")) or clean_text(row.get("title")))
        if original_slug in slug_map:
            row["slug"] = slug_map[original_slug]
        if "kind" not in row and clean_text(row.get("type")):
            row["kind"] = clean_text(row.get("type"))
        source = row.get("mermaid_source") or row.get("source")
        if clean_text(source):
            row["mermaid_source"] = _normalize_mermaid_source(str(source))
        row.setdefault("link_state", clean_text(row.get("status")) or "architecture_first_draft")
        row.setdefault("evidence_tier", "user_intent")
        rows.append(row)
    return rows


def _normalize_mermaid_source(source: str) -> str:
    return mermaid_text.normalize_mermaid_source(source)


__all__ = ["normalize_host_reasoned_proposal"]
