"""Build traceability from exact v7 artifact bindings, never text overlap."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_traceability_contract import CreatedWorkstream
from odylith.runtime.domain_intelligence.greenfield_traceability_contract import DiagramLink
from odylith.runtime.domain_intelligence.greenfield_traceability_contract import GreenfieldTraceabilityPlan
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    SEMANTIC_PROJECTION_PLAN_VERSION,
)
from odylith.runtime.governance import backlog_authoring


def build_semantic_traceability_plan(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
) -> GreenfieldTraceabilityPlan:
    """Bind graph-projected artifacts by exact IDs and slugs."""

    projection_plan = require_persisted_semantic_projection_plan(proposal)
    backlog_rows = semantic_projection_workstream_rows(proposal)
    created_rows = tuple(row for row in created_backlog if isinstance(row, Mapping))
    if len(backlog_rows) != len(created_rows):
        raise ValueError("verified semantic Radar projection count drifted before traceability")
    created_by_title = _unique_rows(
        created_rows,
        key="title",
        label="created Radar workstream",
    )
    workstreams: list[CreatedWorkstream] = []
    for projected in backlog_rows:
        projected_title = _required_text(projected, "title")
        created = created_by_title.get(projected_title)
        if created is None:
            raise ValueError(
                f"verified semantic Radar workstream `{projected_title}` lacks created custody"
            )
        workstreams.append(
            CreatedWorkstream(
                idea_id=_required_text(created, "idea_id").upper(),
                title=projected_title,
                path=Path(_required_text(created, "idea_path")).expanduser().resolve(),
                row=projected,
            )
        )
    diagrams = semantic_projection_diagram_rows(proposal)
    if len(diagrams) != len(diagram_ids):
        raise ValueError("verified semantic Atlas projection count drifted before traceability")
    diagram_id_by_slug = {
        _required_text(row, "slug"): str(identifier).strip()
        for row, identifier in zip(diagrams, diagram_ids, strict=True)
    }
    workstream_by_title = {row.title: row for row in workstreams}
    component_workstreams: dict[str, tuple[str, ...]] = {}
    component_diagrams: dict[str, tuple[str, ...]] = {}
    workstream_plans = mapping_rows(projection_plan.get("workstreams"))
    product_plans = tuple(row for row in workstream_plans if row.get("kind") == "product")
    if len(product_plans) != 1:
        raise ValueError("persisted semantic projection plan lacks one product workstream")
    parent = workstream_by_title.get(_required_text(product_plans[0], "title"))
    if parent is None:
        raise ValueError("persisted semantic projection plan lacks created product custody")
    diagram_plan_by_key = {
        _required_text(row, "key"): row
        for row in mapping_rows(projection_plan.get("diagrams"))
    }
    for component in mapping_rows(projection_plan.get("components")):
        component_id = _required_text(component, "component_id")
        child_plans = tuple(
            row
            for row in workstream_plans
            if row.get("kind") == "component"
            and _strings(row.get("component_ids")) == (component_id,)
        )
        if len(workstream_plans) == 1:
            binding_plan = product_plans[0]
        elif len(child_plans) == 1:
            binding_plan = child_plans[0]
        else:
            raise ValueError(
                f"verified semantic component `{component_id}` lacks one planned Radar link"
            )
        workstream = workstream_by_title.get(_required_text(binding_plan, "title"))
        if workstream is None:
            raise ValueError(f"verified semantic component `{component_id}` lacks created Radar custody")
        component_workstreams[component_id] = tuple(
            dict.fromkeys((parent.idea_id, workstream.idea_id))
        )
        slugs = tuple(
            _required_text(diagram_plan_by_key[key], "slug")
            for key in _strings(binding_plan.get("diagram_keys"))
        )
        component_diagrams[component_id] = tuple(
            diagram_id_by_slug[slug] for slug in slugs if slug in diagram_id_by_slug
        )
        if not component_diagrams[component_id]:
            raise ValueError(f"verified semantic component `{component_id}` lacks exact Atlas custody")
    links: list[DiagramLink] = []
    backlog_diagrams: dict[str, list[str]] = {row.idea_id: [] for row in workstreams}
    for diagram, identifier in zip(diagrams, diagram_ids, strict=True):
        slug = _required_text(diagram, "slug")
        related = [
            workstream
            for workstream in workstreams
            if slug in _strings(workstream.row.get("related_diagram_slugs"))
        ]
        if workstreams and workstreams[0] not in related:
            related.insert(0, workstreams[0])
        if not related:
            raise ValueError(f"verified semantic Atlas diagram `{slug}` lacks Radar custody")
        diagram_id = str(identifier).strip()
        for workstream in related:
            backlog_diagrams[workstream.idea_id].append(diagram_id)
        links.append(
            DiagramLink(
                row=diagram,
                diagram_id=diagram_id,
                related_workstream_ids=tuple(row.idea_id for row in related),
                related_backlog_paths=tuple(str(row.path) for row in related),
            )
        )
    return GreenfieldTraceabilityPlan(
        workstreams=tuple(workstreams),
        component_workstreams=component_workstreams,
        component_diagrams=component_diagrams,
        diagram_links=tuple(links),
        backlog_diagrams={key: tuple(dict.fromkeys(values)) for key, values in backlog_diagrams.items()},
    )


def require_persisted_semantic_projection_plan(
    proposal: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Require the one persisted topology contract without rebuilding any axis."""

    plan = proposal.get("projection_plan")
    if not isinstance(plan, Mapping):
        raise ValueError("verified semantic proposal lacks its persisted projection plan")
    if plan.get("version") != SEMANTIC_PROJECTION_PLAN_VERSION:
        raise ValueError("verified semantic proposal uses an unsupported projection plan")
    nodes = mapping_rows(plan.get("nodes"))
    edges = mapping_rows(plan.get("edges"))
    view_edges = mapping_rows(plan.get("view_edges"))
    components = mapping_rows(plan.get("components"))
    workstreams = mapping_rows(plan.get("workstreams"))
    diagrams = mapping_rows(plan.get("diagrams"))
    axes = plan.get("axes")
    if not isinstance(axes, Mapping):
        raise ValueError("persisted semantic projection plan lacks typed axes")
    node_by_id = _unique_rows(nodes, key="fact_id", label="projection node")
    edge_by_id = _unique_rows(edges, key="relation_id", label="projection edge")
    view_edge_by_id = _unique_rows(
        view_edges,
        key="edge_id",
        label="projection view edge",
    )
    component_by_id = _unique_rows(
        components,
        key="component_id",
        label="projection component",
    )
    workstream_by_title = _unique_rows(
        workstreams,
        key="title",
        label="projection workstream",
    )
    diagram_by_key = _unique_rows(diagrams, key="key", label="projection diagram")
    if not node_by_id or not component_by_id or not workstream_by_title or not diagram_by_key:
        raise ValueError("persisted semantic projection plan is incomplete")
    for key in (
        "workflow_step_fact_ids",
        "state_fact_ids",
        "visible_output_fact_ids",
        "component_fact_ids",
    ):
        missing = [fact_id for fact_id in _strings(axes.get(key)) if fact_id not in node_by_id]
        if missing:
            raise ValueError(f"persisted semantic projection axis `{key}` references unknown facts")
    for component in components:
        if _required_text(component, "semantic_fact_id") not in node_by_id:
            raise ValueError("persisted semantic component references an unknown fact")
        if any(fact_id not in node_by_id for fact_id in _strings(component.get("implements"))):
            raise ValueError("persisted semantic component implements an unknown fact")
    for workstream in workstreams:
        if any(value not in component_by_id for value in _strings(workstream.get("component_ids"))):
            raise ValueError("persisted semantic workstream references an unknown component")
        if any(value not in diagram_by_key for value in _strings(workstream.get("diagram_keys"))):
            raise ValueError("persisted semantic workstream references an unknown diagram")
    for diagram in diagrams:
        if any(value not in node_by_id for value in _strings(diagram.get("fact_ids"))):
            raise ValueError("persisted semantic diagram references an unknown fact")
        if any(value not in edge_by_id for value in _strings(diagram.get("relation_ids"))):
            raise ValueError("persisted semantic diagram references an unknown relation")
        if any(
            value not in view_edge_by_id
            for value in _strings(diagram.get("view_edge_ids"))
        ):
            raise ValueError("persisted semantic diagram references an unknown view edge")
    for edge in view_edges:
        if (
            _required_text(edge, "kind") != "workflow_sequence"
            or _required_text(edge, "subject_id") not in node_by_id
            or _required_text(edge, "object_id") not in node_by_id
        ):
            raise ValueError("persisted semantic projection carries an invalid view edge")
    return plan


def semantic_projection_component_rows(
    proposal: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    """Return component projections in persisted-plan order with exact bindings."""

    plan = require_persisted_semantic_projection_plan(proposal)
    projected = _unique_rows(
        mapping_rows(proposal.get("components")),
        key="component_id",
        label="projected component",
    )
    rows: list[Mapping[str, Any]] = []
    planned = mapping_rows(plan.get("components"))
    if len(projected) != len(planned):
        raise ValueError("verified semantic component depth differs from its projection plan")
    for binding in planned:
        component_id = _required_text(binding, "component_id")
        row = projected.get(component_id)
        if row is None:
            raise ValueError(f"verified semantic component `{component_id}` is missing")
        if (
            row.get("semantic_fact_id") != binding.get("semantic_fact_id")
            or row.get("release_scope") != binding.get("release_scope")
            or row.get("component_role") != binding.get("component_role")
            or _strings(row.get("semantic_implements")) != _strings(binding.get("implements"))
        ):
            raise ValueError(f"verified semantic component `{component_id}` drifted from its plan")
        rows.append(row)
    return tuple(rows)


def semantic_projection_workstream_rows(
    proposal: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    """Return Radar projections in persisted-plan order with exact topology."""

    plan = require_persisted_semantic_projection_plan(proposal)
    projected = _unique_rows(
        mapping_rows(proposal.get("backlog")),
        key="title",
        label="projected Radar workstream",
    )
    diagrams = {
        _required_text(row, "key"): _required_text(row, "slug")
        for row in mapping_rows(plan.get("diagrams"))
    }
    planned = mapping_rows(plan.get("workstreams"))
    if len(projected) != len(planned):
        raise ValueError("verified semantic workstream depth differs from its projection plan")
    rows: list[Mapping[str, Any]] = []
    for binding in planned:
        title = _required_text(binding, "title")
        row = projected.get(title)
        if row is None:
            raise ValueError(f"verified semantic workstream `{title}` is missing")
        expected_slugs = tuple(
            diagrams[key] for key in _strings(binding.get("diagram_keys"))
        )
        if (
            _strings(row.get("component_focus")) != _strings(binding.get("component_ids"))
            or _strings(row.get("related_diagram_slugs")) != expected_slugs
        ):
            raise ValueError(f"verified semantic workstream `{title}` drifted from its plan")
        rows.append(row)
    return tuple(rows)


def semantic_projection_diagram_rows(
    proposal: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    """Return Atlas projections in persisted-plan order with exact graph subsets."""

    plan = require_persisted_semantic_projection_plan(proposal)
    projected = _unique_rows(
        mapping_rows(proposal.get("diagrams")),
        key="slug",
        label="projected Atlas diagram",
    )
    planned = mapping_rows(plan.get("diagrams"))
    if len(projected) != len(planned):
        raise ValueError("verified semantic diagram depth differs from its projection plan")
    rows: list[Mapping[str, Any]] = []
    for binding in planned:
        slug = _required_text(binding, "slug")
        row = projected.get(slug)
        if row is None:
            raise ValueError(f"verified semantic diagram `{slug}` is missing")
        if (
            _strings(row.get("semantic_fact_ids")) != _strings(binding.get("fact_ids"))
            or _strings(row.get("semantic_relation_ids")) != _strings(binding.get("relation_ids"))
            or _strings(row.get("projection_view_edge_ids"))
            != _strings(binding.get("view_edge_ids"))
        ):
            raise ValueError(f"verified semantic diagram `{slug}` drifted from its plan")
        rows.append(row)
    return tuple(rows)


def apply_semantic_backlog_traceability(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    plan: GreenfieldTraceabilityPlan,
) -> list[str]:
    """Write only exact diagram IDs into already-rendered Radar records."""

    root = Path(repo_root).expanduser().resolve()
    projection_plan = require_persisted_semantic_projection_plan(proposal)
    axes = projection_plan.get("axes")
    if not isinstance(axes, Mapping):
        raise ValueError("persisted semantic projection plan lacks typed axes")
    stateful = bool(_strings(axes.get("state_fact_ids")))
    touched: list[str] = []
    for workstream in plan.workstreams:
        metadata, sections = backlog_authoring._parse_metadata_and_sections(workstream.path)
        diagrams = plan.backlog_diagrams.get(workstream.idea_id, ())
        metadata["related_diagram_ids"] = ", ".join(diagrams)
        sections.update(_semantic_sections(workstream, stateful=stateful))
        workstream.path.write_text(
            backlog_authoring._render_idea_text(metadata=metadata, sections=sections),
            encoding="utf-8",
        )
        try:
            touched.append(str(workstream.path.relative_to(root)))
        except ValueError:
            touched.append(str(workstream.path))
    return touched


def _semantic_sections(
    workstream: CreatedWorkstream,
    *,
    stateful: bool,
) -> dict[str, str]:
    row = workstream.row
    title = workstream.title
    metrics = _strings(row.get("success_metrics"))
    risks = _strings(row.get("risks"))
    dependencies = _strings(row.get("dependencies"))
    interfaces = _strings(row.get("interfaces"))
    validation = _strings(row.get("validation"))
    components = _strings(row.get("component_focus"))
    facts = _strings(row.get("semantic_fact_refs"))
    first_slice = _required_text(row, "recommended_first_slice")
    return {
        "Problem": _required_text(row, "problem"),
        "Customer": _required_text(row, "customer"),
        "Opportunity": _required_text(row, "opportunity"),
        "Proposed Solution": f"{title} delivers this graph-bounded slice: {first_slice}",
        "Scope": (
            f"{title} is limited to semantic facts {_csv(facts)} and components {_csv(components)}. "
            f"First slice: {first_slice}"
        ),
        "Non-Goals": f"{title} does not add behavior outside its cited Semantic Intent facts and relations.",
        "Risks": _bullets(risks),
        "Dependencies": _bullets(
            dependencies or (f"{title} depends on the sealed Semantic Intent authority.",)
        ),
        "Success Metrics": _bullets(metrics),
        "Validation": _bullets(validation or metrics),
        "Rollout": (
            f"Promote {title} only after its behavior, blocked-path, state reconstruction, and evidence checks pass."
            if stateful
            else f"Promote {title} only after its behavior, blocked-path, stateless-boundary, and evidence checks pass."
        ),
        "Why Now": (
            f"{title} is required now because its exact graph binding is part of the accepted first-release sequence."
        ),
        "Product View": _required_text(row, "product_view"),
        "Impacted Components": _bullets(components or ("No implementation component is assigned.",)),
        "Interface Changes": _bullets(
            interfaces or (f"{title} changes no interface outside its typed component boundary.",)
        ),
        "Migration/Compatibility": f"{title} introduces no compatibility claim beyond the sealed first release.",
        "Test Strategy": _bullets(validation or metrics),
        "Open Questions": f"Reopen {title} only when new source evidence changes a material graph fact or relation.",
    }


def _unique_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    key: str,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _required_text(row, key)
        if value in result:
            raise ValueError(f"verified semantic {label} `{key}` values are not unique")
        result[value] = row
    return result


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"verified semantic traceability lacks `{key}`")
    return value


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _bullets(values: Sequence[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def _csv(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "none"


__all__ = [
    "apply_semantic_backlog_traceability",
    "build_semantic_traceability_plan",
    "require_persisted_semantic_projection_plan",
    "semantic_projection_component_rows",
    "semantic_projection_diagram_rows",
    "semantic_projection_workstream_rows",
]
