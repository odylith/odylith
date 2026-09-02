"""Project typed model-authored intent into an adaptive Radar backlog.

Artifact depth is selected before this module runs.  Each selected role gets a
different view of accepted typed facts; this module does not classify prose or
invent product meaning.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_artifact_depth import (
    diagram_roles_for_workstream_roles,
)
from odylith.runtime.domain_intelligence.greenfield_authored_radar_ordering import (
    build_authored_ordering_decision,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)


AUTHORED_WORKSTREAM_ROLES = ("project", "workflow", "boundary", "proof")
AUTHORED_WORKSTREAM_SEMANTICS_KEY = "authored_workstream_semantics"
AUTHORED_WORKSTREAM_SEMANTICS_VERSION = "odylith.greenfield.authored-workstream-semantics.v4"
_DIAGRAM_ROLES_BY_WORKSTREAM = {
    "project": ("context", "sequence", "state_evidence", "component_boundaries"),
    "workflow": ("context", "sequence"),
    "boundary": ("context", "component_boundaries"),
    "proof": ("sequence", "state_evidence"),
}


def build_authored_backlog(
    *,
    title: str,
    first_path: str,
    product_story: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    state_object: str,
    human_actors: Sequence[str],
    internal_systems: Sequence[str],
    success_metrics: Sequence[str],
    visible_result: str,
    proof_boundary: str,
    external_systems: Sequence[str],
    evidence_requirements: Sequence[str],
    non_goals: Sequence[str],
    operational_constraints: Sequence[str],
    assumptions: Sequence[str],
    ambiguities: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
    diagram_slugs: Mapping[str, str],
    workstream_roles: Sequence[str],
) -> list[dict[str, Any]]:
    """Return one exact, role-specific Radar row for every selected role."""

    candidate_roles = _validated_roles(workstream_roles)
    component_ids = _component_values(components, "component_id")
    component_labels = _component_values(components, "label")
    if not component_ids or len(component_ids) != len(components):
        raise ValueError("model-authored backlog requires typed component identifiers")

    fact_values = _fact_values(
        title=title,
        product_story=product_story,
        problem=problem,
        customer=customer,
        opportunity=opportunity,
        product_view=product_view,
        state_object=state_object,
        first_path=first_path,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        success_metrics=success_metrics,
        evidence_requirements=evidence_requirements,
        non_goals=non_goals,
        operational_constraints=operational_constraints,
        assumptions=assumptions,
        ambiguities=ambiguities,
        component_responsibility_relations=component_responsibility_relations,
    )
    relation_values = _relation_values(
        relations=relations,
        context_relations=context_relations,
        component_responsibility_relations=component_responsibility_relations,
    )
    workflow_components = _components_with_contract_values(
        components,
        fields=("owner_bound_events",),
    ) or component_ids
    proof_components = _components_with_contract_values(
        components,
        fields=("visible_results", "recovery_events"),
    ) or component_ids
    component_focus_by_role = {
        "project": component_ids,
        "workflow": workflow_components,
        "boundary": component_ids,
        "proof": proof_components,
    }
    component_fact_refs_by_role = {
        role: _component_fact_refs(
            fact_values=fact_values,
            component_ids=component_ids,
            component_labels=component_labels,
            component_focus=component_focus_by_role[role],
        )
        for role in candidate_roles
    }
    contracts = _workstream_semantic_contracts(
        candidate_roles=candidate_roles,
        fact_values=fact_values,
        relation_values=relation_values,
        relations=relations,
        context_relations=context_relations,
        component_responsibility_relations=component_responsibility_relations,
        component_fact_refs_by_role=component_fact_refs_by_role,
        evidence_requirement_count=len(evidence_requirements),
        operational_constraint_count=len(operational_constraints),
    )
    roles = tuple(contracts)
    selected_diagram_roles = diagram_roles_for_workstream_roles(candidate_roles)
    selected_diagram_slugs = {
        role: _required_text(diagram_slugs.get(role), f"{role} diagram slug")
        for role in selected_diagram_roles
    }
    shared = {
        "title": title,
        "component_ids": component_ids,
        "component_labels": component_labels,
        "fact_values": fact_values,
        "relation_values": relation_values,
        "workflow_components": workflow_components,
        "proof_components": proof_components,
    }
    return [
        _backlog_row(
            role=role,
            facts=shared,
            semantic_contract=contracts[role],
            diagram_slugs=_diagram_slugs_for_role(
                role=role,
                diagram_slugs=selected_diagram_slugs,
            ),
        )
        for role in roles
    ]


def _backlog_row(
    *,
    role: str,
    facts: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
    diagram_slugs: list[str],
) -> dict[str, Any]:
    projection = _role_projection(
        role=role,
        facts=facts,
        semantic_contract=semantic_contract,
    )
    projection["field_refs"] = _radar_rendered_field_refs(
        projection=projection,
        facts=facts,
        semantic_contract=semantic_contract,
    )
    rendered_field_refs = _validated_rendered_field_refs(
        projection=projection,
        semantic_contract=semantic_contract,
    )
    component_focus = _strings(projection["component_focus"])
    dependencies = _strings(projection["dependencies"])
    interfaces = _strings(projection["interfaces"])
    validation = _strings(projection["validation"])
    metrics = _strings(projection["success_metrics"])
    first_slice = _required_text(projection.get("recommended_first_slice"), "first slice")
    ordering_decision = build_authored_ordering_decision(
        why_now=_required_text(projection.get("ordering_why_now"), "ordering rationale"),
        expected_outcome=_required_text(
            projection.get("ordering_expected_outcome"),
            "ordering outcome",
        ),
        deferred_scope=_strings(projection["deferred_scope"]),
        ranking_basis=first_slice,
    )
    semantic_record = dict(semantic_contract)
    semantic_record["rendered_field_refs"] = rendered_field_refs
    row = {
        "title": _required_text(projection.get("title"), "workstream title"),
        "workstream_type": "standalone",
        "workstream_role": role,
        "problem": _required_text(projection.get("problem"), "workstream problem"),
        "customer": _required_text(projection.get("customer"), "workstream customer"),
        "opportunity": _required_text(projection.get("opportunity"), "workstream opportunity"),
        "product_view": _required_text(projection.get("product_view"), "workstream product view"),
        "success_metrics": metrics,
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "recommended_first_slice": first_slice,
        "component_focus": component_focus,
        "related_diagram_slugs": diagram_slugs,
        "dependencies": dependencies,
        "interfaces": interfaces,
        "validation": validation,
        "evidence_tier": "user_intent",
        "ordering_decision": ordering_decision,
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        AUTHORED_WORKSTREAM_SEMANTICS_KEY: semantic_record,
    }
    owned_fact_values = facts.get("fact_values")
    fact_values = owned_fact_values if isinstance(owned_fact_values, Mapping) else {}
    owned_refs = _unique(
        [
            *_strings(semantic_contract.get("fact_refs")),
            *_strings(semantic_contract.get("shared_fact_refs")),
        ]
    )
    row["radar_sections"] = _radar_sections(
        row=row,
        scope=_strings(projection["scope"]),
        non_goals=_values_for_prefix(fact_values, owned_refs, "/non_goals/"),
        assumptions=_values_for_prefix(fact_values, owned_refs, "/assumptions/"),
        ambiguities=_values_for_prefix(fact_values, owned_refs, "/ambiguities/"),
        operational_constraints=_values_for_prefix(
            fact_values,
            owned_refs,
            "/operational_constraints/",
        ),
        component_labels=_focused_component_labels(
            facts=facts,
            component_focus=component_focus,
        ),
    )
    return row


def _role_projection(
    *,
    role: str,
    facts: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
) -> dict[str, Any]:
    title = _required_text(facts.get("title"), "product title")
    component_ids = _strings(facts["component_ids"])
    raw_fact_values = facts.get("fact_values")
    fact_values = raw_fact_values if isinstance(raw_fact_values, Mapping) else {}
    raw_relation_values = facts.get("relation_values")
    relation_values = raw_relation_values if isinstance(raw_relation_values, Mapping) else {}
    fact_refs = _strings(semantic_contract.get("fact_refs"))
    relation_refs = _strings(semantic_contract.get("relation_refs"))
    shared_fact_refs = _strings(semantic_contract.get("shared_fact_refs"))
    visible_fact_refs = _unique([*fact_refs, *shared_fact_refs])
    title_refs = _exact_refs(visible_fact_refs, "/title")
    customer_context_refs = _exact_refs(visible_fact_refs, "/customer") or _prefix_refs(
        visible_fact_refs,
        "/human_actors/",
    )[:1]

    if role == "project":
        story_refs = _exact_refs(visible_fact_refs, "/product_story")
        problem_refs = _exact_refs(visible_fact_refs, "/problem") or story_refs
        customer_refs = customer_context_refs
        opportunity_refs = _exact_refs(visible_fact_refs, "/opportunity") or story_refs
        view_refs = _exact_refs(
            visible_fact_refs,
            "/product_view",
            "/state_object",
            "/first_path",
        )
        outcome_refs = _exact_refs(visible_fact_refs, "/product_view") or view_refs
        metric_refs = [
            *_prefix_refs(visible_fact_refs, "/success_metrics/"),
            *_exact_refs(visible_fact_refs, "/proof_boundary"),
        ] or story_refs
        evidence_refs = _prefix_refs(
            visible_fact_refs,
            "/evidence_requirements/",
            "/operational_constraints/",
        )
        validation_refs = _unique([*metric_refs, *evidence_refs]) or view_refs
        dependency_refs = _prefix_refs(visible_fact_refs, "/external_systems/")
        deferred_refs = _prefix_refs(visible_fact_refs, "/non_goals/")
        scope_refs = _exact_refs(
            visible_fact_refs,
            "/product_story",
            "/state_object",
            "/first_path",
        )
        first_slice_refs = _exact_refs(visible_fact_refs, "/first_path") or _exact_refs(
            visible_fact_refs,
            "/product_view",
        )
        first_slice = _required_text(
            _first_value(fact_values, first_slice_refs),
            "project first slice",
        )
        return {
            "title": f"Deliver {title}",
            "problem": _labeled_values("Problem", fact_values, problem_refs),
            "customer": _first_value(fact_values, customer_refs),
            "opportunity": _labeled_values("Opportunity", fact_values, opportunity_refs),
            "product_view": _labeled_values("Product view", fact_values, view_refs),
            "success_metrics": _values_for_refs(fact_values, metric_refs),
            "recommended_first_slice": first_slice,
            "component_focus": component_ids,
            "dependencies": _values_for_refs(fact_values, dependency_refs),
            "interfaces": [],
            "validation": _values_for_refs(fact_values, validation_refs),
            "deferred_scope": _values_for_refs(fact_values, deferred_refs),
            "scope": _values_for_refs(fact_values, scope_refs),
            "ordering_why_now": _joined_values(fact_values, opportunity_refs),
            "ordering_expected_outcome": _joined_values(
                fact_values,
                outcome_refs,
            ),
            "field_refs": {
                "title": title_refs,
                "problem": problem_refs,
                "customer": customer_refs,
                "opportunity": opportunity_refs,
                "product_view": view_refs,
                "success_metrics": metric_refs,
                "recommended_first_slice": first_slice_refs,
                "dependencies": dependency_refs,
                "validation": validation_refs,
                "deferred_scope": deferred_refs,
                "scope": scope_refs,
                "ordering_why_now": opportunity_refs,
                "ordering_expected_outcome": outcome_refs,
            },
        }
    if role == "workflow":
        actor_refs = _prefix_refs(fact_refs, "/human_actors/")
        path_refs = _exact_refs(fact_refs, "/first_path")
        opportunity_refs = _exact_refs(fact_refs, "/opportunity") or _exact_refs(
            visible_fact_refs,
            "/product_story",
        )
        event_refs = _prefix_refs(relation_refs, "/authored_semantics/first_path_relations/")
        events = _values_for_refs(relation_values, event_refs)
        final_event_refs = event_refs[-1:]
        return {
            "title": f"Run {title} first path",
            "problem": _labeled_values("Handoff participants", fact_values, actor_refs),
            "customer": _first_value(fact_values, customer_context_refs),
            "opportunity": _labeled_values(
                "Workflow opportunity",
                fact_values,
                opportunity_refs,
            ),
            "product_view": _labeled_values("Ordered workflow events", relation_values, event_refs),
            "success_metrics": _values_for_refs(relation_values, final_event_refs),
            "recommended_first_slice": _first_value(fact_values, path_refs),
            "component_focus": _strings(facts["workflow_components"]),
            "dependencies": [],
            "interfaces": [],
            "validation": events,
            "deferred_scope": [],
            "scope": events,
            "ordering_why_now": _joined_values(fact_values, opportunity_refs),
            "ordering_expected_outcome": _joined_values(relation_values, final_event_refs),
            "field_refs": {
                "title": title_refs,
                "problem": actor_refs,
                "customer": customer_context_refs,
                "opportunity": opportunity_refs,
                "product_view": event_refs,
                "success_metrics": final_event_refs,
                "recommended_first_slice": path_refs,
                "dependencies": [],
                "validation": event_refs,
                "deferred_scope": [],
                "scope": event_refs,
                "ordering_why_now": opportunity_refs,
                "ordering_expected_outcome": final_event_refs,
            },
        }
    if role == "boundary":
        external_refs = _prefix_refs(fact_refs, "/external_systems/")
        exclusion_refs = _prefix_refs(fact_refs, "/non_goals/", "/ambiguities/")
        ownership_refs = _prefix_refs(
            fact_refs,
            "/internal_systems/",
            "/component_responsibilities/",
        )
        gate_refs = fact_refs[:1] or relation_refs[:1]
        validation_refs = relation_refs or fact_refs
        return {
            "title": f"Define {title} boundaries",
            "problem": _labeled_values(
                "Boundary exclusions and questions",
                fact_values,
                exclusion_refs,
            ),
            "customer": _first_value(fact_values, customer_context_refs),
            "opportunity": _labeled_values(
                "External boundary dependencies",
                fact_values,
                external_refs,
            ),
            "product_view": _labeled_values(
                "Product-owned boundary responsibilities",
                fact_values,
                ownership_refs,
            ),
            "success_metrics": _values_for_refs(
                relation_values if relation_refs else fact_values,
                validation_refs,
            ),
            "recommended_first_slice": _first_value(
                fact_values if fact_refs else relation_values,
                gate_refs,
            ),
            "component_focus": component_ids,
            "dependencies": _values_for_refs(fact_values, external_refs),
            "interfaces": [],
            "validation": _values_for_refs(
                relation_values if relation_refs else fact_values,
                validation_refs,
            ),
            "deferred_scope": _values_for_refs(
                fact_values,
                _prefix_refs(fact_refs, "/non_goals/"),
            ),
            "scope": _values_for_refs(fact_values, fact_refs),
            "ordering_why_now": _joined_values(
                fact_values,
                external_refs or exclusion_refs or ownership_refs,
            ),
            "ordering_expected_outcome": _joined_values(
                fact_values if fact_refs else relation_values,
                gate_refs,
            ),
            "field_refs": {
                "title": title_refs,
                "problem": exclusion_refs,
                "customer": customer_context_refs,
                "opportunity": external_refs,
                "product_view": ownership_refs,
                "success_metrics": validation_refs,
                "recommended_first_slice": gate_refs,
                "dependencies": external_refs,
                "validation": validation_refs,
                "deferred_scope": _prefix_refs(fact_refs, "/non_goals/"),
                "scope": fact_refs,
                "ordering_why_now": external_refs or exclusion_refs or ownership_refs,
                "ordering_expected_outcome": gate_refs,
            },
        }
    if role == "proof":
        boundary_refs = _exact_refs(fact_refs, "/proof_boundary")
        metric_refs = _prefix_refs(fact_refs, "/success_metrics/")
        evidence_refs = _prefix_refs(fact_refs, "/evidence_requirements/")
        constraint_refs = _prefix_refs(fact_refs, "/operational_constraints/")
        validation_refs = relation_refs or fact_refs
        emitted_metric_refs = metric_refs or evidence_refs or boundary_refs
        return {
            "title": f"Prove {title} release",
            "problem": _labeled_values(
                "Operational proof constraints",
                fact_values,
                constraint_refs,
            ),
            "customer": _first_value(fact_values, customer_context_refs),
            "opportunity": _labeled_values(
                "Required release evidence",
                fact_values,
                evidence_refs,
            ),
            "product_view": _labeled_values("Proof boundary", fact_values, boundary_refs),
            "success_metrics": _values_for_refs(fact_values, emitted_metric_refs),
            "recommended_first_slice": _first_value(fact_values, boundary_refs),
            "component_focus": _strings(facts["proof_components"]),
            "dependencies": [],
            "interfaces": [],
            "validation": _values_for_refs(
                relation_values if relation_refs else fact_values,
                validation_refs,
            ),
            "deferred_scope": [],
            "scope": _values_for_refs(fact_values, [*evidence_refs, *constraint_refs]),
            "ordering_why_now": _joined_values(
                fact_values,
                evidence_refs or boundary_refs,
            ),
            "ordering_expected_outcome": _joined_values(fact_values, boundary_refs),
            "field_refs": {
                "title": title_refs,
                "problem": constraint_refs,
                "customer": customer_context_refs,
                "opportunity": evidence_refs,
                "product_view": boundary_refs,
                "success_metrics": emitted_metric_refs,
                "recommended_first_slice": boundary_refs,
                "dependencies": [],
                "validation": validation_refs,
                "deferred_scope": [],
                "scope": [*evidence_refs, *constraint_refs],
                "ordering_why_now": evidence_refs or boundary_refs,
                "ordering_expected_outcome": boundary_refs,
            },
        }
    raise ValueError(f"unsupported model-authored workstream role `{role}`")


def _radar_rendered_field_refs(
    *,
    projection: Mapping[str, Any],
    facts: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
) -> dict[str, list[str]]:
    raw = projection.get("field_refs")
    if not isinstance(raw, Mapping):
        raise ValueError("model-authored workstream projection is missing rendered refs")
    refs = {str(field): _strings(values) for field, values in raw.items()}
    fact_values_raw = facts.get("fact_values")
    fact_values = fact_values_raw if isinstance(fact_values_raw, Mapping) else {}
    fact_refs = _strings(semantic_contract.get("fact_refs"))
    component_refs = _component_fact_refs(
        fact_values=fact_values,
        component_ids=_strings(facts.get("component_ids")),
        component_labels=_strings(facts.get("component_labels")),
        component_focus=_strings(projection.get("component_focus")),
    )
    refs.update(
        {
            "radar_sections.Proposed Solution": refs.get("product_view", []),
            "radar_sections.Scope": refs.get("scope", []),
            "radar_sections.Non-Goals": _prefix_refs(fact_refs, "/non_goals/"),
            "radar_sections.Dependencies": refs.get("dependencies", []),
            "radar_sections.Validation": refs.get("validation", []),
            "radar_sections.Rollout": refs.get("recommended_first_slice", []),
            "radar_sections.Why Now": refs.get("opportunity", []),
            "radar_sections.Impacted Components": component_refs,
            "radar_sections.Test Strategy": refs.get("validation", []),
            "radar_sections.Open Questions": _prefix_refs(fact_refs, "/ambiguities/"),
            "radar_sections.Assumptions": _prefix_refs(fact_refs, "/assumptions/"),
            "radar_sections.Operational Constraints": _prefix_refs(
                fact_refs,
                "/operational_constraints/",
            ),
        }
    )
    return refs


def _validated_rendered_field_refs(
    *,
    projection: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
) -> dict[str, list[str]]:
    raw = projection.get("field_refs")
    if not isinstance(raw, Mapping):
        raise ValueError("model-authored workstream projection is missing rendered refs")
    allowed = set(_strings(semantic_contract.get("fact_refs"))) | set(
        _strings(semantic_contract.get("relation_refs"))
    ) | set(
        _strings(semantic_contract.get("shared_fact_refs"))
    )
    rendered: dict[str, list[str]] = {}
    for field, refs in raw.items():
        values = _strings(refs)
        if not isinstance(field, str) or len(values) != len(refs) or not set(values) <= allowed:
            raise ValueError("model-authored workstream rendered an unowned semantic ref")
        rendered[field] = values
    required_fields = (
        "title",
        "problem",
        "customer",
        "opportunity",
        "product_view",
        "success_metrics",
        "recommended_first_slice",
        "validation",
        "radar_sections.Impacted Components",
    )
    missing_fields = [field for field in required_fields if not rendered.get(field)]
    if missing_fields:
        role = _text(semantic_contract.get("role")) or "unknown"
        raise ValueError(
            f"model-authored {role} workstream has uncited required fields: "
            + ", ".join(missing_fields)
        )
    return rendered


def _radar_sections(
    *,
    row: Mapping[str, Any],
    scope: Sequence[str],
    non_goals: Sequence[str],
    assumptions: Sequence[str],
    ambiguities: Sequence[str],
    operational_constraints: Sequence[str],
    component_labels: Sequence[str],
) -> dict[str, str]:
    role = _required_text(row.get("workstream_role"), "workstream role")
    return {
        "Proposed Solution": _text(row.get("product_view")),
        "Scope": _bullet_block(scope),
        "Non-Goals": _bullet_block(
            non_goals,
            empty=_not_applicable_section(role, "accepted non-goal"),
        ),
        "Risks": _not_applicable_section(role, "accepted risk"),
        "Dependencies": _bullet_block(
            _strings(row.get("dependencies")),
            empty=_not_applicable_section(role, "accepted external dependency"),
        ),
        "Validation": _bullet_block(_strings(row.get("validation"))),
        "Rollout": _fact_block(
            ("Workstream gate", _text(row.get("recommended_first_slice")))
        ),
        "Why Now": _text(row.get("opportunity")),
        "Impacted Components": _bullet_block(component_labels),
        "Interface Changes": _bullet_block(
            _strings(row.get("interfaces")),
            empty=_not_applicable_section(role, "accepted interface change"),
        ),
        "Migration/Compatibility": _not_applicable_section(
            role,
            "accepted migration or compatibility requirement",
        ),
        "Test Strategy": _bullet_block(_strings(row.get("validation"))),
        "Open Questions": _bullet_block(
            ambiguities,
            empty=_not_applicable_section(role, "unresolved material ambiguity"),
        ),
        "Assumptions": _bullet_block(
            assumptions,
            empty=_not_applicable_section(role, "explicit assumption"),
        ),
        "Operational Constraints": _bullet_block(
            operational_constraints,
            empty=_not_applicable_section(role, "accepted operational constraint"),
        ),
    }


def _not_applicable_section(role: str, subject: str) -> str:
    return f"Not applicable — the {role} workstream owns no {subject}."


def _fact_values(
    *,
    title: str,
    product_story: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    state_object: str,
    first_path: str,
    proof_boundary: str,
    human_actors: Sequence[str],
    internal_systems: Sequence[str],
    external_systems: Sequence[str],
    success_metrics: Sequence[str],
    evidence_requirements: Sequence[str],
    non_goals: Sequence[str],
    operational_constraints: Sequence[str],
    assumptions: Sequence[str],
    ambiguities: Sequence[str],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field, value in (
        ("title", title),
        ("product_story", product_story),
        ("problem", problem),
        ("customer", customer),
        ("opportunity", opportunity),
        ("product_view", product_view),
        ("state_object", state_object),
        ("first_path", first_path),
        ("proof_boundary", proof_boundary),
    ):
        if value:
            values[f"/{field}"] = value
    for field, rows in (
        ("human_actors", human_actors),
        ("internal_systems", internal_systems),
        ("external_systems", external_systems),
        ("success_metrics", success_metrics),
        ("evidence_requirements", evidence_requirements),
        ("non_goals", non_goals),
        ("operational_constraints", operational_constraints),
        ("assumptions", assumptions),
        ("ambiguities", ambiguities),
    ):
        for index, value in enumerate(rows):
            if value:
                values[f"/{field}/{index}"] = value
    for relation in component_responsibility_relations:
        if relation.get("responsibility_source") != "accepted_fact":
            continue
        path = _text(relation.get("responsibility_path"))
        quote = _text(relation.get("responsibility_quote"))
        if not path or not quote:
            continue
        if path in values and values[path] != quote:
            raise ValueError("model-authored backlog found contradictory accepted fact custody")
        values[path] = quote
    return values


def _relation_values(
    *,
    relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field, rows, quote_field in (
        ("first_path_relations", relations, "event_quote"),
        ("first_path_context_relations", context_relations, "fact_quote"),
        (
            "component_responsibility_relations",
            component_responsibility_relations,
            "responsibility_quote",
        ),
    ):
        for index, row in enumerate(rows):
            quote = _required_text(row.get(quote_field), f"{field} quote")
            values[f"/authored_semantics/{field}/{index}"] = quote
    return values


def _workstream_semantic_contracts(
    *,
    candidate_roles: Sequence[str],
    fact_values: Mapping[str, str],
    relation_values: Mapping[str, str],
    relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
    component_fact_refs_by_role: Mapping[str, Sequence[str]],
    evidence_requirement_count: int,
    operational_constraint_count: int,
) -> dict[str, dict[str, Any]]:
    role_refs: dict[str, tuple[list[str], list[str]]] = {}

    if "workflow" in candidate_roles:
        human_rows = [
            (index, _text(row.get("actor_fact_path")))
            for index, row in enumerate(relations)
            if row.get("actor_kind") == "human" and _text(row.get("actor_fact_path"))
        ]
        human_paths = _unique(path for _, path in human_rows)
        if len(human_paths) > 1:
            role_refs["workflow"] = (
                _known_refs(["/first_path", "/opportunity", *human_paths], fact_values),
                _known_refs(
                    [
                        f"/authored_semantics/first_path_relations/{index}"
                        for index in range(len(relations))
                    ],
                    relation_values,
                ),
            )

    if "boundary" in candidate_roles:
        external_facts = [
            path
            for path in fact_values
            if path.startswith("/external_systems/")
        ]
        exclusion_facts = [
            path
            for path in fact_values
            if path.startswith(("/non_goals/", "/ambiguities/"))
        ]
        owner_paths = _unique(
            _text(row.get("owner_system_path"))
            for row in component_responsibility_relations
        )
        ownership_facts: list[str] = []
        boundary_relations: list[str] = []
        if owner_paths:
            ownership_facts.extend(owner_paths)
            ownership_facts.extend(
                _text(row.get("responsibility_path"))
                for row in component_responsibility_relations
                if row.get("responsibility_source") == "accepted_fact"
            )
            boundary_relations.extend(
                f"/authored_semantics/component_responsibility_relations/{index}"
                for index in range(len(component_responsibility_relations))
            )
        external_facts = _known_refs(external_facts, fact_values)
        exclusion_facts = _known_refs(exclusion_facts, fact_values)
        ownership_facts = _known_refs(ownership_facts, fact_values)
        boundary_facts = [*external_facts, *exclusion_facts, *ownership_facts]
        boundary_facts = _known_refs(boundary_facts, fact_values)
        boundary_fact_set = set(boundary_facts)
        boundary_relations.extend(
            f"/authored_semantics/first_path_context_relations/{index}"
            for index, row in enumerate(context_relations)
            if _text(row.get("fact_path")) in boundary_fact_set
        )
        if external_facts and exclusion_facts and ownership_facts:
            role_refs["boundary"] = (
                boundary_facts,
                _known_refs(boundary_relations, relation_values),
            )

    if "proof" in candidate_roles and (
        evidence_requirement_count > 1 or operational_constraint_count > 1
    ):
        proof_facts = [
            path
            for path in fact_values
            if path == "/proof_boundary"
            or path.startswith(
                (
                    "/success_metrics/",
                    "/evidence_requirements/",
                    "/operational_constraints/",
                )
            )
        ]
        proof_fact_set = set(proof_facts)
        proof_relations = [
            f"/authored_semantics/first_path_context_relations/{index}"
            for index, row in enumerate(context_relations)
            if _text(row.get("fact_path")) in proof_fact_set
        ]
        proof_boundary_refs = _exact_refs(proof_facts, "/proof_boundary")
        evidence_refs = _prefix_refs(proof_facts, "/evidence_requirements/")
        constraint_refs = _prefix_refs(proof_facts, "/operational_constraints/")
        if proof_boundary_refs and evidence_refs and constraint_refs:
            role_refs["proof"] = (
                proof_facts,
                _known_refs(proof_relations, relation_values),
            )

    assigned_fact_refs = {
        ref for fact_refs, _ in role_refs.values() for ref in fact_refs
    }
    assigned_relation_refs = {
        ref for _, relation_refs in role_refs.values() for ref in relation_refs
    }
    project_refs = (
        [ref for ref in fact_values if ref not in assigned_fact_refs],
        [ref for ref in relation_values if ref not in assigned_relation_refs],
    )
    role_refs["project"] = project_refs

    contracts: dict[str, dict[str, Any]] = {}
    claimed_facts: set[str] = set()
    claimed_relations: set[str] = set()
    for role in candidate_roles:
        refs = role_refs.get(role)
        if refs is None:
            continue
        fact_refs, relation_refs = refs
        if role != "project" and not fact_refs and not relation_refs:
            continue
        if claimed_facts.intersection(fact_refs) or claimed_relations.intersection(relation_refs):
            raise ValueError("model-authored workstream semantic ownership overlaps")
        claimed_facts.update(fact_refs)
        claimed_relations.update(relation_refs)
        shared_fact_refs = [
            ref
            for ref in component_fact_refs_by_role.get(role, ())
            if ref not in fact_refs
        ]
        if role == "project":
            # The project row integrates the canonical facts owned by its
            # specialized child workstreams. Sharing permits citation without
            # introducing a second semantic owner or recomposing source prose.
            shared_fact_refs.extend(
                ref for ref in fact_values if ref not in fact_refs
            )
        else:
            customer_refs = _exact_refs(fact_values, "/customer") or _prefix_refs(
                fact_values,
                "/human_actors/",
            )[:1]
            shared_fact_refs = [
                "/title",
                *customer_refs,
                *shared_fact_refs,
            ]
            if role == "workflow" and not _exact_refs(fact_refs, "/opportunity"):
                shared_fact_refs.extend(_exact_refs(fact_values, "/product_story"))
        contracts[role] = {
            "version": AUTHORED_WORKSTREAM_SEMANTICS_VERSION,
            "role": role,
            "fact_refs": list(fact_refs),
            "relation_refs": list(relation_refs),
            "shared_fact_refs": _known_refs(_unique(shared_fact_refs), fact_values),
        }
    if claimed_facts != set(fact_values) or claimed_relations != set(relation_values):
        raise ValueError("model-authored workstream semantics left typed evidence unowned")
    return contracts


def _known_refs(values: Sequence[str] | Any, known: Mapping[str, str]) -> list[str]:
    return _unique(ref for ref in values if isinstance(ref, str) and ref in known)


def _exact_refs(refs: Sequence[str], *paths: str) -> list[str]:
    selected = set(paths)
    return [ref for ref in refs if ref in selected]


def _prefix_refs(refs: Sequence[str], *prefixes: str) -> list[str]:
    return [ref for ref in refs if ref.startswith(prefixes)]


def _first_value(values: Mapping[str, str], refs: Sequence[str]) -> str:
    rows = _values_for_refs(values, refs)
    return rows[0] if rows else ""


def _joined_values(values: Mapping[str, str], refs: Sequence[str]) -> str:
    return "; ".join(_values_for_refs(values, refs))


def _labeled_values(
    label: str,
    values: Mapping[str, str],
    refs: Sequence[str],
    *,
    empty: str = "",
) -> str:
    rows = _values_for_refs(values, refs)
    return _fact_block((label, "; ".join(rows))) if rows else empty


def _values_for_refs(values: Mapping[str, str], refs: Any) -> list[str]:
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes, bytearray)):
        return []
    return _unique(values.get(ref, "") for ref in refs if isinstance(ref, str))


def _values_for_prefix(
    values: Mapping[str, str],
    refs: Any,
    prefix: str,
) -> list[str]:
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes, bytearray)):
        return []
    return _unique(
        values.get(ref, "")
        for ref in refs
        if isinstance(ref, str) and ref.startswith(prefix)
    )


def _validated_roles(values: Sequence[str]) -> tuple[str, ...]:
    roles = tuple(values)
    if not roles or roles[0] != "project" or len(roles) != len(set(roles)):
        raise ValueError("model-authored backlog requires one ordered project role")
    unknown = [role for role in roles if role not in AUTHORED_WORKSTREAM_ROLES]
    if unknown:
        raise ValueError(f"unsupported model-authored workstream role `{unknown[0]}`")
    return roles


def _diagram_slugs_for_role(
    *,
    role: str,
    diagram_slugs: Mapping[str, str],
) -> list[str]:
    selected = [
        _required_text(diagram_slugs.get(diagram_role), f"{diagram_role} diagram slug")
        for diagram_role in _DIAGRAM_ROLES_BY_WORKSTREAM[role]
        if diagram_role in diagram_slugs
    ]
    if not selected:
        raise ValueError(f"model-authored `{role}` workstream has no selected Atlas view")
    return selected


def _component_values(
    components: Sequence[Mapping[str, Any]],
    field: str,
) -> list[str]:
    return _unique(_text(component.get(field)) for component in components)


def _focused_component_labels(
    *,
    facts: Mapping[str, Any],
    component_focus: Sequence[str],
) -> list[str]:
    component_ids = _strings(facts["component_ids"])
    component_labels = _strings(facts["component_labels"])
    labels_by_id = dict(zip(component_ids, component_labels, strict=True))
    return [labels_by_id[component_id] for component_id in component_focus]


def _component_fact_refs(
    *,
    fact_values: Mapping[str, Any],
    component_ids: Sequence[str],
    component_labels: Sequence[str],
    component_focus: Sequence[str],
) -> list[str]:
    labels_by_id = dict(zip(component_ids, component_labels, strict=True))
    refs: list[str] = []
    for component_id in component_focus:
        if component_id not in labels_by_id:
            raise ValueError("model-authored workstream has an unknown impacted component")
        label = labels_by_id[component_id]
        matching = [
            ref
            for ref, value in fact_values.items()
            if isinstance(ref, str)
            and (ref == "/title" or ref.startswith("/internal_systems/"))
            and value == label
        ]
        if len(matching) != 1:
            raise ValueError("model-authored workstream has an uncited impacted component")
        refs.extend(matching)
    return _unique(refs)


def _components_with_contract_values(
    components: Sequence[Mapping[str, Any]],
    *,
    fields: Sequence[str],
) -> list[str]:
    rows: list[str] = []
    for component in components:
        contract = component.get("component_contract")
        if not isinstance(contract, Mapping):
            continue
        if not any(_strings(contract.get(field)) for field in fields):
            continue
        component_id = _text(component.get("component_id"))
        if component_id and component_id not in rows:
            rows.append(component_id)
    return rows


def _fact_block(*rows: tuple[str, str]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for label, value in rows:
        if value and value not in seen:
            lines.append(f"{label}: {value}")
            seen.add(value)
    return "\n".join(lines)


def _bullet_block(values: Sequence[str], *, empty: str = "") -> str:
    rows = _unique(values)
    if not rows:
        rows = [empty] if empty else []
    return "\n".join(f"- {row}" for row in rows)


def _required_text(value: Any, label: str) -> str:
    text = _text(value)
    if not text:
        raise ValueError(f"model-authored backlog is missing {label}")
    return text


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [row for row in value if isinstance(row, str) and row]


def _unique(values: Sequence[str] | Any) -> list[str]:
    rows: list[str] = []
    for value in values:
        if isinstance(value, str) and value and value not in rows:
            rows.append(value)
    return rows


__all__ = [
    "AUTHORED_WORKSTREAM_ROLES",
    "AUTHORED_WORKSTREAM_SEMANTICS_KEY",
    "AUTHORED_WORKSTREAM_SEMANTICS_VERSION",
    "build_authored_backlog",
]
