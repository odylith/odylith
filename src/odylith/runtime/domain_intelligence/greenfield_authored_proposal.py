"""Project verified model-authored Greenfield meaning without reparsing prose.

The authoring boundary already owns semantic selection and source custody. This
module only maps that closed contract into existing proposal surfaces. It may
create stable identifiers and presentation copy, but it never classifies words,
infers missing product facts, or repairs model-authored meaning.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_artifact_depth import (
    plan_greenfield_artifact_depth,
)
from odylith.runtime.domain_intelligence.greenfield_authored_atlas_view import (
    build_authored_atlas_diagrams,
)
from odylith.runtime.domain_intelligence.greenfield_authored_backlog import (
    build_authored_backlog,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    AUTHORED_SEMANTICS_KEY,
    authored_component_relation_facts,
    authored_semantics_mapping,
    authored_visible_result,
    component_responsibility_relations_from_intent,
    first_path_context_relations_from_intent,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote
from odylith.runtime.domain_intelligence.greenfield_intent_shaping_prompt import (
    accepted_intent_shaping_prompt,
)
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    assumption_rows,
    decision_copy,
)
from odylith.runtime.domain_intelligence.project_intelligence_binding import (
    PROJECT_INTELLIGENCE_BINDING_KEY,
)


_AUTHORED_PROJECTION_FIELDS = (
    "classification",
    "greenfield_ux",
    "assumptions",
    "open_questions",
    "risks",
    "security_compliance",
    "validation_strategy",
    "project_brief",
    "project_intelligence",
    "release_plan",
    "backlog",
    "components",
    "semantic_model",
    "diagrams",
    "apply_commands",
)


def build_authored_greenfield_proposal(
    *,
    observed_source: Mapping[str, Any],
    release_selector: str,
    confirmed_intent: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the complete proposal view of one verified authored intent."""

    relations = first_path_relations_from_intent(confirmed_intent)
    if not relations:
        raise ValueError("model-authored Greenfield projection requires verified first-path relations")
    component_responsibility_relations = component_responsibility_relations_from_intent(
        confirmed_intent
    )
    first_path_context_relations = first_path_context_relations_from_intent(confirmed_intent)
    release = str(release_selector or "").strip() or greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR
    title = _required_text(confirmed_intent, "title")
    command_prompt = accepted_intent_shaping_prompt(
        confirmed_intent,
        fallback_title=title,
    )
    product_slug = slugify(title) or "greenfield-project"
    first_path = _required_text(confirmed_intent, "first_path")
    state_object = _required_text(confirmed_intent, "state_object")
    proof_boundary = _required_text(confirmed_intent, "proof_boundary")
    product_story = _required_text(confirmed_intent, "product_story")
    human_actors = _strings(confirmed_intent.get("human_actors"))
    internal_systems = _strings(confirmed_intent.get("internal_systems"))
    external_systems = _strings(confirmed_intent.get("external_systems"))
    non_goals = _strings(confirmed_intent.get("non_goals"))
    assumptions = assumption_rows(confirmed_intent.get("assumptions", []))
    ambiguities = _strings(confirmed_intent.get("ambiguities"))
    operational_constraints = _strings(confirmed_intent.get("operational_constraints"))
    evidence_requirements = _strings(confirmed_intent.get("evidence_requirements"))
    success_metrics = _strings(confirmed_intent.get("success_metrics"))
    artifact_depth = plan_greenfield_artifact_depth(
        actor_count=len(_unique(human_actors)),
        event_count=len(relations),
        internal_system_count=len(_unique(internal_systems)),
        external_system_count=len(_unique(external_systems)),
        ambiguity_count=len(_unique(ambiguities)),
        non_goal_count=len(_unique(non_goals)),
        evidence_requirement_count=len(_unique(evidence_requirements)),
        operational_constraint_count=len(_unique(operational_constraints)),
    )
    visible_result = authored_visible_result(relations)
    components = _components(
        title=title,
        product_slug=product_slug,
        internal_systems=internal_systems,
        relations=relations,
        component_responsibility_relations=component_responsibility_relations,
        first_path_context_relations=first_path_context_relations,
    )
    all_diagram_slugs = {
        "context": f"{product_slug}-system-context",
        "sequence": f"{product_slug}-first-path",
        "state_evidence": f"{product_slug}-state-evidence",
        "component_boundaries": f"{product_slug}-component-boundaries",
    }
    backlog = build_authored_backlog(
        title=title,
        first_path=first_path,
        product_story=product_story,
        problem=_text(confirmed_intent.get("problem")),
        customer=_text(confirmed_intent.get("customer")),
        opportunity=_text(confirmed_intent.get("opportunity")),
        product_view=_text(confirmed_intent.get("product_view")),
        state_object=state_object,
        human_actors=human_actors,
        internal_systems=internal_systems,
        success_metrics=success_metrics,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        external_systems=external_systems,
        evidence_requirements=evidence_requirements,
        non_goals=non_goals,
        operational_constraints=operational_constraints,
        assumptions=assumptions,
        ambiguities=ambiguities,
        components=components,
        relations=relations,
        context_relations=first_path_context_relations,
        component_responsibility_relations=component_responsibility_relations,
        diagram_slugs={
            role: all_diagram_slugs[role]
            for role in artifact_depth.diagram_roles
        },
        workstream_roles=artifact_depth.workstream_roles,
    )
    diagram_roles = artifact_depth.diagram_roles
    diagram_slugs = {role: all_diagram_slugs[role] for role in diagram_roles}
    semantic_model = _semantic_model(
        title=title,
        state_object=state_object,
        first_path=first_path,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
        operational_constraints=operational_constraints,
        components=components,
        backlog=backlog,
        relations=relations,
    )
    diagrams = build_authored_atlas_diagrams(
        title=title,
        diagram_slugs=diagram_slugs,
        human_actors=human_actors,
        external_systems=external_systems,
        non_goals=non_goals,
        state_object=state_object,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        components=components,
        backlog=backlog,
        relations=relations,
        context_relations=first_path_context_relations,
        diagram_roles=diagram_roles,
    )
    intent = _intent_copy(confirmed_intent)
    intent.update(
        {
            "prompt": "",
            "project_slug": product_slug,
            "reasoning_mode": "model_authored_typed_intent",
            "evidence_tier": "user_intent",
            "summary": product_story,
            AUTHORED_SEMANTICS_KEY: authored_semantics_mapping(
                relations,
                component_responsibility_relations,
                first_path_context_relations=first_path_context_relations,
            ),
        }
    )
    validation_strategy = _unique([*success_metrics, proof_boundary, *evidence_requirements])
    proposal = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "confirmed_intent_before_confirmed_create",
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": intent,
        "observed_source": dict(observed_source),
        "classification": {
            "method": "model_authored_typed_intent",
            "fit_policy": "Project only verified source-cited facts and typed relations.",
            "provider_calls": 0,
        },
        "greenfield_ux": {
            "mode": "consumer_greenfield_confirmed_path",
            "write_guardrail": "No product records are written until CONFIRM publishes the sealed transaction.",
            "next_best_action": "Review the sealed project package and choose CONFIRM, EDIT, or REJECT.",
        },
        "assumptions": _assumption_rows([
            *assumptions,
            *({"applies_to": "general", "statement": value} for value in ambiguities),
        ]),
        "open_questions": [],
        "risks": [],
        "security_compliance": {},
        "validation_strategy": validation_strategy,
        "project_brief": _project_brief(
            title=title,
            product_story=product_story,
            problem=decision_copy(confirmed_intent, "problem"),
            first_path=first_path,
            visible_result=visible_result,
            proof_boundary=proof_boundary,
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
            operational_constraints=operational_constraints,
            evidence_requirements=evidence_requirements,
            command_prompt=command_prompt,
        ),
        "project_intelligence": _project_intelligence(
            title=title,
            product_story=product_story,
            problem=_text(confirmed_intent.get("problem")),
            customer=_text(confirmed_intent.get("customer")),
            opportunity=_text(confirmed_intent.get("opportunity")),
            product_view=_text(confirmed_intent.get("product_view")),
            first_path=first_path,
            state_object=state_object,
            visible_result=visible_result,
            proof_boundary=proof_boundary,
            relations=relations,
            internal_systems=internal_systems,
            external_systems=external_systems,
            operational_constraints=operational_constraints,
            evidence_requirements=evidence_requirements,
            success_metrics=success_metrics,
        ),
        "release_plan": _release_plan(
            title=title,
            product_slug=product_slug,
            release=release,
            proof_boundary=proof_boundary,
            success_metrics=success_metrics,
            backlog=backlog,
        ),
        "backlog": backlog,
        "components": components,
        "semantic_model": semantic_model,
        "diagrams": diagrams,
        "apply_commands": [
            f"odylith greenfield propose --repo-root . --prompt {shell_quote(command_prompt)}",
            "# CONFIRM publishes the exact sealed transaction; EDIT rebuilds from new evidence; REJECT writes nothing.",
        ],
    }
    return proposal


def authored_projection_parity_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return exact typed-projection drift without interpreting rendered prose."""

    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        return ["Greenfield proposal is not a model-authored typed projection"]
    intent = proposal.get("intent")
    observed_source = proposal.get("observed_source")
    release_plan = proposal.get("release_plan")
    if not isinstance(intent, Mapping):
        return ["model-authored Greenfield proposal is missing typed Product Intent"]
    if not isinstance(observed_source, Mapping):
        return ["model-authored Greenfield proposal is missing source-evidence posture"]
    if not isinstance(release_plan, Mapping):
        return ["model-authored Greenfield proposal is missing its release projection"]
    try:
        expected = build_authored_greenfield_proposal(
            observed_source=observed_source,
            release_selector=_text(release_plan.get("selector")),
            confirmed_intent=intent,
        )
    except ValueError as exc:
        return [str(exc)]

    issues: list[str] = []
    for field in _AUTHORED_PROJECTION_FIELDS:
        actual_value = _without_binding(field, proposal.get(field))
        if actual_value != expected.get(field):
            issues.append(
                f"model-authored Greenfield `{field}` projection drifted from sealed typed intent"
            )
    return issues


def _without_binding(field: str, value: Any) -> Any:
    value = copy.deepcopy(value)
    if field == "release_plan" and isinstance(value, dict):
        value.pop(PROJECT_INTELLIGENCE_BINDING_KEY, None)
    elif field in {"backlog", "components", "diagrams"} and isinstance(value, list):
        for row in value:
            if isinstance(row, dict):
                row.pop(PROJECT_INTELLIGENCE_BINDING_KEY, None)
    return value


def _components(
    *,
    title: str,
    product_slug: str,
    internal_systems: Sequence[str],
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
    first_path_context_relations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    relation_contracts = authored_component_relation_facts(
        title=title,
        internal_systems=internal_systems,
        relations=relations,
        component_responsibility_relations=component_responsibility_relations,
    )
    context_by_owner = _component_context_by_owner(
        title=title,
        internal_systems=internal_systems,
        relations=relations,
        component_responsibility_relations=component_responsibility_relations,
        context_relations=first_path_context_relations,
    )
    for contract in relation_contracts:
        label = str(contract["owner_system"])
        context = context_by_owner.get(label, _empty_component_context())
        contract = {**dict(contract), **context}
        responsibilities = list(contract["responsibility_facts"])
        responsibility = "; ".join(responsibilities)
        component_id = _unique_id(slugify(label) or f"{product_slug}-component", rows)
        rows.append(
            {
                "component_id": component_id,
                "label": label,
                "kind": "component",
                "intended_path": f"src/{product_slug}/{component_id}",
                "responsibility": responsibility,
                "boundary": "",
                "dependencies": list(context["external_dependencies"]),
                "interfaces": [],
                "validation": list(context["operational_constraints"]),
                "status": "planned",
                "qualification": "candidate",
                "evidence_tier": "user_intent",
                "release_scope": "first_release",
                "source_system_description": responsibility,
                "projection_origin": AUTHORED_PROJECTION_ORIGIN,
                "component_contract": dict(contract),
            }
        )
    return rows


def _component_context_by_owner(
    *,
    title: str,
    internal_systems: Sequence[str],
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, list[str]]]:
    """Join exact context facts to exact event/component owner relations."""

    owner_by_path = {"/title": title}
    owner_by_path.update(
        {f"/internal_systems/{index}": value for index, value in enumerate(internal_systems)}
    )
    owner_paths_by_event: dict[int, list[str]] = {}
    component_owner_paths: list[str] = []
    for relation in relations:
        if relation.get("actor_kind") != "product":
            continue
        order = relation.get("order")
        owner_path = str(relation.get("owner_system_path") or "")
        if isinstance(order, int) and not isinstance(order, bool) and owner_path in owner_by_path:
            owner_paths_by_event.setdefault(order, []).append(owner_path)
            if owner_path not in component_owner_paths:
                component_owner_paths.append(owner_path)
    for relation in component_responsibility_relations:
        order = relation.get("first_path_event_order")
        owner_path = str(relation.get("owner_system_path") or "")
        if owner_path in owner_by_path and owner_path not in component_owner_paths:
            component_owner_paths.append(owner_path)
        if (
            isinstance(order, int)
            and not isinstance(order, bool)
            and order > 0
            and owner_path in owner_by_path
        ):
            owner_paths_by_event.setdefault(order, []).append(owner_path)

    field_by_kind = {
        "state_object": "state_context",
        "external_system": "external_dependencies",
        "operational_constraint": "operational_constraints",
    }
    grouped: dict[str, dict[str, list[str]]] = {}
    for relation in context_relations:
        order = relation.get("first_path_event_order")
        field = field_by_kind.get(str(relation.get("context_kind") or ""))
        quote = str(relation.get("fact_quote") or "")
        if not field or not quote or not isinstance(order, int) or isinstance(order, bool) or order < 0:
            continue
        if order == 0:
            owner_paths = component_owner_paths if len(component_owner_paths) == 1 else ()
        else:
            owner_paths = owner_paths_by_event.get(order, ())
        for owner_path in dict.fromkeys(owner_paths):
            owner = owner_by_path[owner_path]
            target = grouped.setdefault(owner, _empty_component_context())
            if quote not in target[field]:
                target[field].append(quote)
    return grouped


def _empty_component_context() -> dict[str, list[str]]:
    return {
        "state_context": [],
        "external_dependencies": [],
        "operational_constraints": [],
    }


def _semantic_model(
    *,
    title: str,
    state_object: str,
    first_path: str,
    visible_result: str,
    proof_boundary: str,
    human_actors: Sequence[str],
    internal_systems: Sequence[str],
    external_systems: Sequence[str],
    non_goals: Sequence[str],
    operational_constraints: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    backlog: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    events = [
        {
            "index": index,
            "actor": _text(row.get("actor_fact_quote")),
            "owner_system": _text(row.get("owner_system_quote")),
            "action": _text(row.get("action_verb_quote")),
            "target_entity": _text(row.get("target_quote")),
            "mutation": _text(row.get("event_quote")),
            "visible_result": bool(_text(row.get("visible_result_quote"))),
            "text": _text(row.get("event_quote")),
            "source_kind": "accepted_first_path",
        }
        for index, row in enumerate(relations, start=1)
    ]
    first_event = relations[0]
    component_refs = []
    for component in components:
        contract = component.get("component_contract") if isinstance(component.get("component_contract"), Mapping) else {}
        component_id = str(component.get("component_id") or "")
        component_refs.append(
            {
                "component_id": component_id,
                "label": str(component.get("label") or ""),
                "semantic_axis": "authored",
                "release_scope": str(component.get("release_scope") or "first_release"),
                "owner_system": _text(contract.get("owner_system")),
                "responsibility_facts": _strings(contract.get("responsibility_facts")),
                "owner_bound_events": _strings(contract.get("owner_bound_events")),
                "event_targets": _strings(contract.get("event_targets")),
                "visible_results": _strings(contract.get("visible_results")),
            }
        )
    workstreams = [
        {
            "title": str(row.get("title") or ""),
            "component_ids": _strings(row.get("component_focus")),
            "local_problem": str(row.get("problem") or ""),
            "first_slice": str(row.get("recommended_first_slice") or ""),
            "proof": " ".join(_strings(row.get("validation"))),
        }
        for row in backlog
    ]
    return {
        "schema_version": "odylith.greenfield.semantic_model.v3",
        "first_path_contract": {
            "actor": _text(first_event.get("actor_fact_quote")),
            "action": _text(first_event.get("action_verb_quote")),
            "entity": state_object,
            "mutation": "",
            "required_fields": [],
            "persistence": "",
            "visible_result": visible_result,
            "deferred_scope": [],
            "capability": first_path,
            "raw_path": first_path,
            "events": events,
        },
        "domain_ontology": {
            "product_title": title,
            "state_object": state_object,
            "proof_boundary": proof_boundary,
            "human_actors": list(human_actors),
            "internal_systems": list(internal_systems),
            "external_systems": list(external_systems),
            "non_goals": list(non_goals),
            "operational_constraints": list(operational_constraints),
            "domain_terms": [],
        },
        "components": component_refs,
        "workstreams": workstreams,
        "diagram_event_graph": {
            "events": events,
            "component_sequence": [str(row.get("component_id") or "") for row in components],
            "proof_checkpoint": proof_boundary,
        },
        "proof_obligations": [
            {"key": "first_path_contract", "claim": first_path, "required_evidence": proof_boundary},
            {"key": "release_boundary", "claim": proof_boundary, "required_evidence": proof_boundary},
        ],
        "evaluation_semantics": None,
    }


def _project_brief(
    *,
    title: str,
    product_story: str,
    problem: str,
    first_path: str,
    visible_result: str,
    proof_boundary: str,
    human_actors: Sequence[str],
    internal_systems: Sequence[str],
    external_systems: Sequence[str],
    non_goals: Sequence[str],
    operational_constraints: Sequence[str],
    evidence_requirements: Sequence[str],
    command_prompt: str,
) -> dict[str, Any]:
    problem_statement = problem
    sections = [
        _brief_section("Product outcome", product_story, "The accepted product outcome."),
        _brief_section(
            "User problem",
            problem_statement,
            "The source-stated need or an explicitly provisional decision assumption.",
        ),
        _brief_section("First path", first_path, "The accepted first complete user path."),
        _brief_section("Visible result", visible_result, "The terminal result typed in the first-path relation."),
        _brief_section("Proof", proof_boundary, "The accepted release proof boundary."),
    ]
    if operational_constraints:
        sections.append(
            _brief_section("Operational constraints", "; ".join(operational_constraints), "Source-stated operating limits.")
        )
    if non_goals:
        sections.append(_brief_section("Non-goals", "; ".join(non_goals), "Explicitly excluded scope."))
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "operational_constraints": list(operational_constraints),
        "purpose": problem_statement,
        "operating_principle": product_story,
        "project_outcome": visible_result,
        "blueprint_sections": sections,
        "customization_options": [],
        "customization_prompts": [],
        "pre_coding_checkpoints": [],
        "coding_readiness_gates": _unique([proof_boundary, *evidence_requirements]),
        "host_independent_paths": [
            {
                "path": "Review the creation-ready transaction",
                "command": f"odylith greenfield propose --repo-root . --prompt {shell_quote(command_prompt)}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Review the sealed package before choosing CONFIRM, EDIT, or REJECT.",
            }
        ],
        "actors": list(human_actors),
        "internal_systems": list(internal_systems),
        "external_systems": list(external_systems),
        "project_name": title,
    }


def _project_intelligence(
    *,
    title: str,
    product_story: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    first_path: str,
    state_object: str,
    visible_result: str,
    proof_boundary: str,
    relations: Sequence[Mapping[str, Any]],
    internal_systems: Sequence[str],
    external_systems: Sequence[str],
    operational_constraints: Sequence[str],
    evidence_requirements: Sequence[str],
    success_metrics: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": "odylith.greenfield.project_intelligence.v1",
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "project_name": title,
        "purpose": product_story,
        "coding_posture": "",
        "control_surface_summary": _unique(
            [problem, customer, opportunity, product_view, first_path, visible_result]
        ),
        "customization_flow": [],
        "intent": _unique([product_story, problem, customer, opportunity, product_view]),
        "scope": [first_path],
        "ontology": _unique([title, state_object, *internal_systems, *external_systems]),
        "state": [state_object],
        "operators": _unique([
            _required_text(row, "actor_fact_quote")
            for row in relations if row.get("actor_kind") == "human"
        ]),
        "constraints": list(operational_constraints),
        "source_of_truth_map": [],
        "evidence": _unique([proof_boundary, *evidence_requirements]),
        "assumptions": [],
        "topology": _unique([*internal_systems, *external_systems]),
        "validation_obligations": _unique([proof_boundary, *success_metrics]),
        "metrics": list(success_metrics),
    }


def _release_plan(
    *,
    title: str,
    product_slug: str,
    release: str,
    proof_boundary: str,
    success_metrics: Sequence[str],
    backlog: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    titles = [str(row.get("title") or "") for row in backlog]
    return {
        "selector": release,
        "label": f"{title} {release}",
        "provisional_release_id": f"release-{product_slug}-{slugify(release)}",
        "strategy": proof_boundary,
        "target_workstream_titles": titles,
        "release_stages": [
            {
                "stage": "first-path",
                "label": f"{title} first path",
                "release_gate": proof_boundary,
                "workstream_titles": titles,
            }
        ],
        "milestones": [{"name": f"{title} proof accepted", "exit_criteria": proof_boundary}],
        "promotion_criteria": _unique([*success_metrics, proof_boundary]),
        "evidence_tier": "user_intent",
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
    }


def _assumption_rows(values: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "id": f"A-{index:03d}",
            "assumption": value["statement"],
            "applies_to": value["applies_to"],
            "impact": "Advisory only; it is not accepted product truth.",
            "validate_with": "Additional source evidence is required before acceptance.",
        }
        for index, value in enumerate(assumption_rows(values), start=1)
    ]


def _brief_section(section: str, value: str, why: str) -> dict[str, str]:
    return {"section": section, "must_capture": value, "why_it_matters": why}


def _intent_copy(intent: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): list(value) if isinstance(value, list) else value
        for key, value in intent.items()
        if key != AUTHORED_SEMANTICS_KEY
    }


def _required_text(value: Mapping[str, Any], key: str) -> str:
    text = _text(value.get(key))
    if not text:
        raise ValueError(f"model-authored Greenfield intent is missing `{key}`")
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


def _unique_id(candidate: str, rows: Sequence[Mapping[str, Any]]) -> str:
    used = {str(row.get("component_id") or "") for row in rows}
    if candidate not in used:
        return candidate
    index = 2
    while f"{candidate}-{index}" in used:
        index += 1
    return f"{candidate}-{index}"


__all__ = ["authored_projection_parity_issues", "build_authored_greenfield_proposal"]
