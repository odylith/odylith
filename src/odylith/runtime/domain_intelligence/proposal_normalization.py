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
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_text_list
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_project_brief import normalize_project_brief
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import normalize_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import enrich_backlog_rows

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


def normalize_host_reasoned_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return a strict-schema proposal from a reasonable host-authored shape."""

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
    normalized["program"] = _normalize_program(normalized.get("program"), release_rows=releases)
    normalized["backlog"] = _normalize_backlog(normalized.get("backlog"), release_rows=releases, slug_map=slug_map)
    normalized["backlog"] = _ensure_program_parent(
        normalized["backlog"],
        intent=intent,
        program=normalized["program"],
        release_plan=normalized["release_plan"],
        validation_strategy=normalized["validation_strategy"],
        security_compliance=normalized.get("security_compliance"),
    )
    normalized["components"] = _normalize_components(normalized.get("components"))
    normalized["backlog"] = _enrich_backlog_expectations(normalized["backlog"], normalized["components"])
    normalized["components"] = _enrich_component_expectations(normalized["components"])
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
        program=normalized["program"],
        release_plan=normalized["release_plan"],
        components=normalized["components"],
        diagrams=normalized["diagrams"],
        observed_source=normalized.get("observed_source") if isinstance(normalized.get("observed_source"), Mapping) else {},
    )
    normalized["backlog"] = enrich_backlog_rows(
        normalized["backlog"],
        intent=normalized["intent"],
        program=normalized["program"],
        release_plan=normalized["release_plan"],
        validation_strategy=normalized["validation_strategy"],
        security_compliance=normalized.get("security_compliance"),
        components=normalized["components"],
        diagrams=normalized["diagrams"],
    )
    return normalized


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
        for row in rows:
            _normalize_list_fields(row, _WORKSTREAM_REF_LIST_FIELDS, split_commas=True)
        first = rows[0] if rows else {}
        selector = clean_text(first.get("release")) or DEFAULT_GREENFIELD_RELEASE_SELECTOR
        target_workstreams = first.get("first_target_workstreams") or first.get("target_workstreams") or []
        label = greenfield_programs.compact_release_target_label(selector)
        return {
            "selector": selector,
            "label": label,
            "provisional_release_id": clean_text(first.get("provisional_release_id")) or f"release-{slugify(selector)}",
            "strategy": clean_text(first.get("strategy"))
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
    for row in stage_rows:
        _normalize_list_fields(row, _WORKSTREAM_REF_LIST_FIELDS, split_commas=True)
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
    _normalize_list_fields(plan, _WORKSTREAM_REF_LIST_FIELDS, split_commas=True)
    _normalize_list_fields(plan, ("milestones", "promotion_criteria"))
    plan.setdefault("strategy", "Promote accepted greenfield work through explicit release gates.")
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
    return milestones or ["Proposal accepted and first release target reviewed."]


def _release_promotion_criteria(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    criteria = [
        join_sentence_text(row.get("exit_criteria")) or join_sentence_text(row.get("release_gate"))
        for row in rows
    ]
    return [item for item in criteria if item] or ["First-wave validation gates are satisfied."]


def _release_gate_for(value: Any, *, release_rows: Sequence[Mapping[str, Any]]) -> str:
    selector = clean_text(value)
    for row in release_rows:
        if selector and clean_text(row.get("release")) == selector:
            return join_sentence_text(row.get("exit_criteria")) or join_sentence_text(row.get("release_gate"))
    return ""


def _normalize_program(value: Any, *, release_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    program = _proposal_object(value)
    waves = []
    for index, raw in enumerate(_proposal_sequence(program.get("waves")), start=1):
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        _normalize_list_fields(row, _WORKSTREAM_REF_LIST_FIELDS, split_commas=True)
        row.setdefault("wave_id", clean_text(row.get("id")) or clean_text(row.get("wave")) or f"W{index}")
        row.setdefault("label", clean_text(row.get("title")) or clean_text(row.get("name")) or str(row["wave_id"]))
        row.setdefault("goal", join_sentence_text(row.get("summary")) or f"Deliver {row['label']}.")
        gate = (
            join_sentence_text(row.get("validation_gate"))
            or join_sentence_text(row.get("validation"))
            or join_sentence_text(row.get("exit_gate"))
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
        first_slice = clean_text(row.get("recommended_first_slice")) or clean_text(row.get("first_slice_proof"))
        if not first_slice:
            first_slice = join_sentence_text(row.get("validation")) or _release_gate_for(
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


def _ensure_program_parent(
    rows: list[Any],
    *,
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    validation_strategy: Sequence[Any],
    security_compliance: Any,
) -> list[Any]:
    mapping_rows = [row for row in rows if isinstance(row, Mapping)]
    waves = [row for row in program.get("waves", []) if isinstance(row, Mapping)] if isinstance(program, Mapping) else []
    if len(mapping_rows) < 2 or not waves:
        return rows
    first = mapping_rows[0]
    if _looks_like_program_parent(first, intent=intent, program=program, waves=waves):
        return rows

    parent = _synthesized_program_parent(
        child_rows=mapping_rows,
        intent=intent,
        program=program,
        release_plan=release_plan,
        validation_strategy=validation_strategy,
        security_compliance=security_compliance,
    )
    return [parent, *rows]


def _looks_like_program_parent(
    row: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    waves: Sequence[Mapping[str, Any]],
) -> bool:
    explicit_type = clean_text(row.get("workstream_type")).casefold()
    if explicit_type in {"umbrella", "program", "parent", "program_parent"}:
        return True
    row_refs = {slugify(value) for value in _row_ref_values(row)}
    wave_refs = {slugify(value) for wave in waves for value in _workstream_ref_values(wave)}
    if row_refs & wave_refs:
        return False
    title = clean_text(row.get("title"))
    title_slug = slugify(title)
    program_title = (
        clean_text(program.get("name"))
        or clean_text(program.get("title"))
        or clean_text(intent.get("title"))
        or clean_text(intent.get("name"))
    )
    if title_slug and title_slug == slugify(program_title):
        return True
    if title_slug and title_slug == slugify(f"{program_title} program"):
        return True
    if title.casefold().startswith(("govern ", "program ", "launch ")):
        return True
    title_tokens = {token for token in title_slug.split("-") if len(token) >= 4}
    program_tokens = {token for token in slugify(program_title).split("-") if len(token) >= 4}
    return bool(title_tokens and program_tokens and program_tokens.issubset(title_tokens))


def _synthesized_program_parent(
    *,
    child_rows: Sequence[Mapping[str, Any]],
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    validation_strategy: Sequence[Any],
    security_compliance: Any,
) -> dict[str, Any]:
    title = clean_text(intent.get("title")) or clean_text(intent.get("name")) or "Greenfield Project"
    parent_title = clean_text(program.get("parent_workstream")) or clean_text(program.get("program_workstream")) or f"Govern {title}"
    first_wave = _first_wave(program)
    first_wave_label = (
        clean_text(first_wave.get("label"))
        or clean_text(first_wave.get("name"))
        or clean_text(first_wave.get("wave_id"))
        or "first wave"
    )
    release_selector = clean_text(release_plan.get("selector")) or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    component_focus = list(unique_text(
        [
            first_wave.get("component_focus"),
            first_wave.get("components"),
            *[row.get("component_focus") for row in child_rows],
            *[row.get("related_components") for row in child_rows],
        ]
    ))
    diagram_refs = list(unique_text(
        [
            *[row.get("related_diagram_slugs") for row in child_rows],
            *[row.get("diagram_slugs") for row in child_rows],
            *[row.get("related_diagrams") for row in child_rows],
        ]
    ))
    validation = list(text_values(first_wave.get("validation_gate")) or text_values(first_wave.get("validation")))
    validation.extend(text_values(release_plan.get("promotion_criteria")))
    validation.extend(text_values(validation_strategy)[:3])
    return {
        "id": "WS-00",
        "title": parent_title,
        "workstream_type": "umbrella",
        "problem": (
            f"{title} has only proposal-level intent so far; it needs one governed program parent before "
            "implementation starts, otherwise child workstreams, waves, release targeting, and component specs "
            "fragment into disconnected tickets."
        ),
        "customer": (
            "Project operator, implementation agents, reviewers, and future maintainers who need one readable "
            "place to understand the greenfield program before code is written."
        ),
        "opportunity": (
            "Turn the confirmed greenfield intent into an execution spine: child workstreams, candidate Registry "
            "components, Atlas topology, Compass waves, release target, and proof gates all tied to the same parent."
        ),
        "product_view": (
            f"Umbrella program for {title}: start implementation with `{first_wave_label}`, keep `{release_selector}` "
            "as the first governed release target, and promote only after the listed validation gates pass."
        ),
        "recommended_first_slice": (
            f"Start coding with the first active wave `{first_wave_label}`; pick the first targeted child workstream, "
            "write its technical plan, implement the smallest source-backed slice, then run the repository test suite "
            "plus Odylith surface refresh and release-target validation before expanding to later waves."
        ),
        "success_metrics": [
            "Program coherence: Compass shows this umbrella as the program parent, and every child workstream belongs to an explicit wave rather than being mistaken for the program itself.",
            "Coding readiness: the first active wave names the implementation-start workstreams, component boundaries, dependencies, interfaces, and validation gates before source edits begin.",
            "Release traceability: Radar, Registry, Atlas, Compass, and the provisional release target all point at the same first-wave workstreams with no orphaned governance objects.",
            "Verification clarity: the applied proposal names the behavior tests, component contract tests, dashboard refresh, and release validation needed before claiming the first slice is complete.",
        ],
        "component_focus": component_focus,
        "related_diagram_slugs": diagram_refs,
        "dependencies": [
            "Child workstreams must remain children of this umbrella program and must not be promoted independently without updating the execution-wave document.",
            "First-wave implementation depends on confirming the release target, component boundaries, interfaces, and validation gates captured by the accepted proposal.",
        ],
        "interfaces": [
            "Compass program view exposes the umbrella, active wave, child workstreams, progress, and exit gate.",
            "Radar child workstreams expose first-slice proof, dependencies, interface expectations, validation, and impacted components.",
            "Registry candidate specs expose component-specific ownership, collaborators, interfaces, failure modes, proof, and implementation kickoff steps.",
        ],
        "validation": validation
        or [
            "Greenfield apply Tribunal passes before writes.",
            "Radar, Registry, Atlas, and Compass refresh after confirmed writes.",
        ],
        "domain_risk": _domain_posture_text(security_compliance)
        or "Greenfield governance can mislead implementation if the program parent, release target, validation gates, or component boundaries are ambiguous.",
        "security_posture": _domain_posture_text(security_compliance)
        or "Security and compliance posture must stay explicit on the project brief and child workstreams, while each candidate component spec carries only that component's own boundary, collaborators, failure modes, and proof.",
        "priority": "P1",
        "sizing": "L",
        "complexity": "High",
        "evidence_tier": "user_intent",
    }


def _first_wave(program: Mapping[str, Any]) -> Mapping[str, Any]:
    waves = program.get("waves", []) if isinstance(program.get("waves"), list) else []
    return next((row for row in waves if isinstance(row, Mapping)), {})


def _row_ref_values(row: Mapping[str, Any]) -> list[str]:
    return list(unique_text([row.get("id"), row.get("workstream_id"), row.get("idea_id"), row.get("title")]))


def _workstream_ref_values(row: Mapping[str, Any]) -> list[str]:
    values: list[Any] = []
    for key in (
        "workstreams",
        "workstream_ids",
        "workstream_titles",
        "target_workstreams",
        "target_workstream_ids",
        "target_workstream_titles",
        "related_workstreams",
        "related_workstream_ids",
        "related_workstream_titles",
        "backlog_titles",
        "primary_workstreams",
    ):
        values.append(row.get(key))
    return list(unique_text(values))


def _domain_posture_text(value: Any) -> str:
    return " ".join(text_values(value)).strip()


def _normalize_components(value: Any) -> list[Any]:
    rows: list[Any] = []
    for raw in _proposal_sequence(value):
        if not isinstance(raw, Mapping):
            rows.append(raw)
            continue
        row = dict(raw)
        row.setdefault("component_id", clean_text(row.get("id")) or clean_text(row.get("name")) or clean_text(row.get("label")))
        row.setdefault("label", clean_text(row.get("name")) or clean_text(row.get("component_id")))
        row.setdefault("kind", clean_text(row.get("type")) or "service")
        row.setdefault("intended_path", clean_text(row.get("path")) or f"src/{slugify(row.get('component_id'))}")
        row.setdefault("status", "planned")
        qualification = clean_text(row.get("qualification")).casefold()
        row["qualification"] = qualification if qualification in _VALID_QUALIFICATIONS else "candidate"
        if "proof_expectations" in row and "validation" not in row:
            row["validation"] = row.get("proof_expectations")
        _normalize_list_fields(row, _COMPONENT_TEXT_LIST_FIELDS)
        row.setdefault("evidence_tier", "user_intent")
        rows.append(row)
    return rows


def _enrich_backlog_expectations(rows: Sequence[Any], components: Sequence[Any]) -> list[Any]:
    component_ids = [
        clean_text(row.get("component_id")) or clean_text(row.get("label"))
        for row in components
        if isinstance(row, Mapping)
    ]
    component_text = ", ".join(item for item in component_ids if item) or "planned Registry components"
    enriched: list[Any] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            enriched.append(raw)
            continue
        row = dict(raw)
        if index > 0 and not row.get("dependencies") and not row.get("depends_on") and not row.get("interfaces") and not row.get("interface_changes"):
            focus_text = ", ".join(text_values(row.get("component_focus"))) or component_text
            row["dependencies"] = [
                f"Depends on confirming the planned boundary and release gate for {focus_text} before source implementation starts."
            ]
            row["interfaces"] = [
                f"Defines the first-slice contract consumed or exposed by {focus_text}; exact API, CLI, UI, or file surface is confirmed in the technical plan."
            ]
        enriched.append(row)
    return enriched


def _enrich_component_expectations(rows: Sequence[Any]) -> list[Any]:
    enriched: list[Any] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            enriched.append(raw)
            continue
        row = dict(raw)
        component_id = clean_text(row.get("component_id")) or clean_text(row.get("label")) or "component"
        if not row.get("dependencies") and not row.get("depends_on"):
            row["dependencies"] = [
                f"No upstream component dependency is claimed for {component_id} until source evidence exists; first implementation planning must confirm runtime, storage, and provider boundaries."
            ]
        if not clean_text(row.get("boundary")) and clean_text(row.get("responsibility")):
            row["boundary"] = f"Owns the planned responsibility: {clean_text(row.get('responsibility'))}"
        enriched.append(row)
    return enriched


def _component_descriptions(components: Sequence[Any]) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for row in components:
        if not isinstance(row, Mapping):
            continue
        for key in (clean_text(row.get("component_id")), clean_text(row.get("label")), clean_text(row.get("name"))):
            slug = slugify(key)
            if slug:
                descriptions[slug] = clean_text(row.get("responsibility")) or f"Planned component {key}."
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
        original_slug = slugify(clean_text(row.get("slug")) or clean_text(row.get("title")))
        if original_slug in slug_map:
            row["slug"] = slug_map[original_slug]
        row.setdefault("kind", clean_text(row.get("type")) or "flowchart")
        source = row.get("mermaid_source") or row.get("source")
        if clean_text(source):
            row["mermaid_source"] = _normalize_mermaid_source(str(source))
        row.setdefault("link_state", clean_text(row.get("status")) or "atlas_first_draft")
        row.setdefault("evidence_tier", "user_intent")
        related = row.get("related_components")
        if "components" not in row and related:
            component_rows = []
            for item in _proposal_sequence(related):
                name = clean_text(item)
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
