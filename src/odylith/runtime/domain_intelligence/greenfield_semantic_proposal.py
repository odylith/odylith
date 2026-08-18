"""Project a complete Greenfield proposal from one verified semantic graph.

This module is intentionally interpretation-free.  The host supplies source-cited
meaning; this projector follows typed facts and relations and never reparses prose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_release_contract import (
    DEFAULT_GREENFIELD_RELEASE_SELECTOR,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_backlog_projection import (
    semantic_backlog_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_evidence_tier,
    semantic_fact_custody_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_diagrams import (
    semantic_diagrams,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    require_semantic_intent_ir,
    semantic_intent_product_facts,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    SemanticProjectionPlan,
    build_semantic_projection_plan,
    semantic_projection_plan_mapping,
    semantic_release_plan,
    semantic_security_compliance,
    semantic_validation_strategy,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_candidate_adjudication import (
    selected_semantic_source_claims,
)


_PI_VERSION = "odylith.greenfield.project_intelligence.v2"


def build_verified_semantic_proposal(
    *,
    authority: Mapping[str, Any],
    observed_source: Mapping[str, Any],
    release_selector: str = "",
) -> dict[str, Any]:
    """Return one deterministic proposal from validated Semantic Intent authority."""

    require_product_intent_authority_structure(authority)
    if authority.get("origin") != "verified_semantic_intent_packet":
        raise ValueError("verified semantic proposal requires source-cited Semantic Intent authority")
    evidence_sources = authority.get("evidence_sources")
    if not isinstance(evidence_sources, Mapping):
        raise ValueError("verified semantic proposal lacks evidence sources")
    assessment = authority.get("semantic_materiality_assessment")
    if not isinstance(assessment, Mapping):
        raise ValueError("verified semantic proposal lacks locked source claims")
    graph = require_semantic_intent_ir(
        authority.get("semantic_intent"),
        evidence_sources=evidence_sources,
        source_claims=selected_semantic_source_claims(
            assessment,
            authority.get("semantic_source_candidate_adjudication"),
        ),
    )
    product_facts = semantic_intent_product_facts(graph)
    release = str(release_selector or "").strip() or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    title = str(product_facts["title"])
    project_slug = semantic_artifact_identifier(title, fallback="greenfield-project")
    projection_plan = build_semantic_projection_plan(
        graph,
        project_slug=project_slug,
    )
    components = list(projection_plan.components)
    backlog = semantic_backlog_rows(
        plan=projection_plan,
        problem=str(product_facts["problem"]),
        customer=str(product_facts["customer"]),
        opportunity=str(product_facts["opportunity"]),
        product_view=str(product_facts["product_view"]),
        success_metrics=_strings(product_facts.get("success_metrics")),
        proof_boundary=str(product_facts["proof_boundary"]),
    )
    semantic_model = _semantic_model(
        graph=graph,
        product_facts=product_facts,
        plan=projection_plan,
        components=components,
        backlog=backlog,
    )
    project_intelligence = _project_intelligence(
        product_facts=product_facts,
        plan=projection_plan,
        components=components,
        release=release,
    )
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.proposal.v2",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": _intent(
            product_facts,
            graph=graph,
            project_slug=project_slug,
            release=release,
        ),
        "observed_source": dict(observed_source),
        "classification": {
            "method": "verified_source_cited_semantic_graph",
            "fit_policy": "Project only source-cited facts and explicit bounded interpretations.",
            "provider_calls": 0,
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        },
        "greenfield_ux": {
            "mode": "consumer_greenfield_verified_semantic_path",
            "write_guardrail": "No product records are written until confirmed create receives --confirm.",
            "next_best_action": f"Review the source-cited {title} transaction for release {release}.",
        },
        "assumptions": _assumptions(graph),
        "open_questions": _open_questions(graph),
        "risks": _risks(components),
        "security_compliance": semantic_security_compliance(
            plan=projection_plan,
            proof_boundary=str(product_facts["proof_boundary"]),
        ),
        "validation_strategy": semantic_validation_strategy(
            plan=projection_plan,
            success_metrics=_strings(product_facts.get("success_metrics")),
            proof_boundary=str(product_facts["proof_boundary"]),
        ),
        "project_brief": _project_brief(
            product_facts=product_facts,
            graph=graph,
            plan=projection_plan,
            components=components,
            release=release,
        ),
        "project_intelligence": project_intelligence,
        "release_plan": semantic_release_plan(
            release=release,
            plan=projection_plan,
        ),
        "backlog": backlog,
        "components": components,
        "projection_plan": semantic_projection_plan_mapping(projection_plan),
        "semantic_model": semantic_model,
        "diagrams": semantic_diagrams(
            plan=projection_plan,
            backlog=backlog,
        ),
        "apply_commands": [
            "odylith greenfield semantic-intent-request --prompt <request>",
            "odylith greenfield propose --repo-root . --prompt <request> --semantic-intent-file <semantic-intent.json>",
            "# CONFIRM commits the exact hash-bound transaction; EDIT rebuilds from new evidence.",
        ],
        PRODUCT_INTENT_AUTHORITY_KEY: dict(authority),
    }
    _bind_artifacts(proposal, project_slug=project_slug, title=title)
    return proposal


def _intent(
    product_facts: Mapping[str, Any],
    *,
    graph: Mapping[str, Any],
    project_slug: str,
    release: str,
) -> dict[str, Any]:
    result = dict(product_facts)
    result.update(
        {
            "prompt": "",
            "project_slug": project_slug,
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
            "semantic_fact_custody": semantic_fact_custody_rows(graph["facts"]),
            "summary": f"{product_facts['product_story']} Release {release} stays bounded to: {product_facts['first_path']}",
        }
    )
    return result


def _semantic_model(
    *,
    graph: Mapping[str, Any],
    product_facts: Mapping[str, Any],
    plan: SemanticProjectionPlan,
    components: Sequence[Mapping[str, Any]],
    backlog: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    facts = list(graph["facts"])
    relations = list(graph["relations"])
    by_id = {str(row["fact_id"]): row for row in facts}
    owners = {
        str(row["subject_id"]): row
        for row in relations
        if row["kind"] == "owned_by"
    }
    produces = _targets(relations, "produces")
    steps = sorted(
        (row for row in facts if row["kind"] == "workflow_step"),
        key=lambda row: int(row["order"]),
    )
    events: list[dict[str, Any]] = []
    for ordinal, step in enumerate(steps):
        attributes = _attributes(step)
        owner = owners.get(str(step["fact_id"]))
        actor = by_id.get(str(owner["object_id"]), {}) if owner else {}
        events.append(
            {
                "index": ordinal + 1,
                "actor": str(actor.get("label") or "") if step["owner_kind"] == "actor" else "",
                "action": attributes["action"],
                "target_entity": attributes.get("object", ""),
                "mutation": attributes["action_phrase"],
                "visible_result": bool(produces.get(str(step["fact_id"]))),
                "text": attributes["action_phrase"],
                "relation_id": str(owner["relation_id"]) if owner else None,
                "canonical_step_index": int(step["order"]),
                "canonical_action_index": 0,
                "canonical_action_ordinal": ordinal,
                "custody_state": str(step["custody"]),
                "evidence_tier": semantic_evidence_tier(str(step["custody"])),
            }
        )
    first = events[0]
    actor = first["actor"] or "The product"
    state_labels = plan.state_labels
    visible_output_labels = plan.visible_output_labels
    workflow_labels = tuple(
        plan.node_by_id[fact_id].label
        for fact_id in plan.workflow_step_fact_ids
    )
    state_summary = _sentence_list(state_labels)
    output_summary = _sentence_list(visible_output_labels)
    component_refs = [
        {
            "component_id": row["component_id"],
            "label": row["label"],
            "semantic_axis": f"sealed:{row['semantic_fact_id']}",
            "release_scope": row["release_scope"],
            "component_role": row["component_role"],
            "contract_schema_version": row["component_contract"]["schema_version"],
            "workflow_fact_ids": list(
                row["component_contract"]["workflow_fact_ids"]
            ),
            "workflow_labels": list(row["component_contract"]["workflow_labels"]),
            "state_objects": list(row["component_contract"]["state_objects"]),
            "visible_outputs": list(row["component_contract"]["visible_outputs"]),
            "accepted_inputs": row["component_contract"]["accepted_inputs"],
            "proof_obligations": list(row["validation"]),
            "custody_state": row["custody_state"],
            "evidence_tier": row["evidence_tier"],
            "semantic_fact_custody": list(row["semantic_fact_custody"]),
        }
        for row in components
    ]
    workstreams = [
        {
            "title": row["title"],
            "component_ids": list(row["component_focus"]),
            "local_problem": row["problem"],
            "first_slice": row["recommended_first_slice"],
            "proof": " ".join(row["validation"]),
            "custody_state": row["custody_state"],
            "evidence_tier": row["evidence_tier"],
            "semantic_fact_custody": list(row["semantic_fact_custody"]),
        }
        for row in backlog
    ]
    first_path_evidence = (
        f"Validate the ordered workflow, reconstruct {state_summary}, and show "
        f"every visible output ({output_summary})."
        if state_labels
        else f"Validate the ordered workflow and show every visible output ({output_summary})."
    )
    release_evidence = (
        "Release review links workflow, state objects, visible outputs, validation, and deferred scope."
        if state_labels
        else "Release review links workflow, visible outputs, validation, and deferred scope."
    )
    proof_obligations = [
        {
            "key": "first_path_contract",
            "claim": f"{actor} can complete {first['action']}: {first['text']}.",
            "required_evidence": first_path_evidence,
        },
        {
            "key": "release_boundary",
            "claim": str(product_facts["proof_boundary"]),
            "required_evidence": release_evidence,
        },
    ]
    proof_obligations.extend(
        {
            "key": f"component_{row['component_id']}",
            "claim": f"{row['label']} preserves its sealed responsibility.",
            "required_evidence": str(row["validation"][0]),
        }
        for row in components
    )
    return {
        "schema_version": "odylith.greenfield.semantic_model.v4",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "semantic_fact_custody": semantic_fact_custody_rows(facts),
        "first_path_contract": {
            "actor": first["actor"],
            "action": first["action"],
            "workflow_fact_ids": list(plan.workflow_step_fact_ids),
            "workflow_labels": list(workflow_labels),
            **({"state_objects": list(state_labels)} if state_labels else {}),
            "mutation": first["mutation"],
            "required_fields": [
                value
                for value in _ordered_unique(event["target_entity"] for event in events)
                if value
            ],
            "visible_outputs": list(visible_output_labels),
            "deferred_scope": _strings(product_facts.get("non_goals")),
            "capability": first["text"],
            "raw_path": str(product_facts["first_path"]),
            "events": events,
        },
        "domain_ontology": {
            "product_title": product_facts["title"],
            **({"state_objects": list(state_labels)} if state_labels else {}),
            "proof_boundary": product_facts["proof_boundary"],
            "human_actors": _strings(product_facts.get("human_actors")),
            "internal_systems": [str(row["label"]) for row in components],
            "external_systems": _strings(product_facts.get("external_systems")),
            "non_goals": _strings(product_facts.get("non_goals")),
            "operational_constraints": _strings(product_facts.get("operational_constraints")),
            "domain_terms": _ordered_unique(
                str(row["label"]) for row in facts if row["kind"] != "ambiguity"
            ),
        },
        "components": component_refs,
        "workstreams": workstreams,
        "diagram_event_graph": {
            "events": events,
            "component_sequence": [str(row["component_id"]) for row in components],
            "proof_checkpoint": f"Visible output proof: {output_summary}",
        },
        "proof_obligations": proof_obligations,
        "evaluation_semantics": None,
    }


def _project_brief(
    *,
    product_facts: Mapping[str, Any],
    graph: Mapping[str, Any],
    plan: SemanticProjectionPlan,
    components: Sequence[Mapping[str, Any]],
    release: str,
) -> dict[str, Any]:
    actor_labels = _fact_labels(graph, "actor")
    system_labels = [str(row["label"]) for row in components]
    external = _fact_labels(graph, "external_system")
    constraints = _strings(product_facts.get("operational_constraints"))
    non_goals = _strings(product_facts.get("non_goals"))
    step_phrases = [_attributes(row)["action_phrase"] for row in _facts(graph, "workflow_step")]
    state_summary = _sentence_list(plan.state_labels)
    output_summary = _sentence_list(plan.visible_output_labels)
    blueprint = [
        _brief_section(
            "Consumer outcome",
            f"{product_facts['product_story']} {product_facts['problem']}",
            "States who benefits and what becomes useful.",
        ),
        _brief_section(
            "Ordered first path",
            _sentence_list(step_phrases),
            "Preserves the accepted workflow order.",
        ),
        _brief_section(
            "Ownership and boundaries",
            (
                f"Actors: {_sentence_list(actor_labels, fallback='none')}. "
                f"Components: {_sentence_list(system_labels)}. "
                f"External systems: {_sentence_list(external, fallback='none')}."
            ),
            "Keeps people, product responsibilities, and dependencies distinct.",
        ),
        _brief_section(
            "State and visible outputs" if plan.state_labels else "Visible outputs",
            (
                f"State objects: {state_summary}. Visible outputs: {output_summary}."
                if plan.state_labels
                else f"Visible outputs: {output_summary}."
            ),
            "Names the product evidence without adding an undeclared state model.",
        ),
        _brief_section(
            "Release proof and limits",
            (
                f"Proof: {product_facts['proof_boundary']} "
                f"Constraints: {_sentence_list(_fragments(constraints), fallback='none asserted')}. "
                f"Excluded: {_sentence_list(_fragments(non_goals), fallback='none asserted')}."
            ),
            "Keeps promotion evidence and excluded scope reviewable together.",
        ),
    ]
    choices = ["accept graph", "revise source evidence", "defer from release"]
    options = [
        *(
            [_decision("D1", "Actors", f"Confirm accepted actors: {_sentence_list(actor_labels)}.", "Changes action ownership.", choices)]
            if actor_labels
            else []
        ),
        *(
            [_decision("D2", "State objects", f"Confirm the accepted state objects: {state_summary}.", "Changes transition proof.", choices)]
            if plan.state_labels
            else []
        ),
        _decision("D3", "Visible outputs", f"Confirm every visible output: {output_summary}.", "Changes the consumer outcomes.", choices),
        *(
            [_decision("D4", "External systems", f"Confirm dependency boundaries: {_sentence_list(external)}.", "Changes access and failure proof.", choices)]
            if external
            else []
        ),
        _decision("D5", "Release boundary", f"Keep release {release} bounded to: {product_facts['proof_boundary']}", "Changes validation and promotion scope.", choices),
    ]
    return {
        "schema_version": "odylith.greenfield.project_brief.v2",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "semantic_fact_custody": semantic_fact_custody_rows(graph["facts"]),
        "purpose": f"{product_facts['product_story']} Problem to solve: {product_facts['problem']}",
        "operating_principle": (
            f"Release {release} preserves the sealed workflow, state objects ({state_summary}), visible outputs ({output_summary}), component boundaries, and source citations."
            if plan.state_labels
            else f"Release {release} preserves the sealed workflow, visible outputs ({output_summary}), component boundaries, and source citations."
        ),
        "project_outcome": str(product_facts["proof_boundary"]),
        "blueprint_sections": blueprint,
        "customization_options": options,
        "coding_readiness_gates": [
            f"The implementation preserves {_sentence_list(step_phrases)} in graph order.",
            f"The component boundaries remain {_sentence_list(system_labels)}.",
            (
                f"Release {release} demonstrates {output_summary} and reconstructs {state_summary}."
                if plan.state_labels
                else f"Release {release} demonstrates every visible output: {output_summary}."
            ),
            f"Excluded scope remains excluded: {_sentence_list(_fragments(non_goals), fallback='no additional non-goals')}.",
        ],
        "operational_constraints": constraints,
    }


def _project_intelligence(
    *,
    product_facts: Mapping[str, Any],
    plan: SemanticProjectionPlan,
    components: Sequence[Mapping[str, Any]],
    release: str,
) -> dict[str, Any]:
    title = str(product_facts["title"])
    path = str(product_facts["first_path"])
    proof = str(product_facts["proof_boundary"])
    actor_rows = _strings(product_facts.get("human_actors"))
    actors = _sentence_list(actor_rows, fallback="none")
    systems = _sentence_list(str(row["label"]) for row in components)
    external_rows = _strings(product_facts.get("external_systems"))
    non_goal_rows = _strings(product_facts.get("non_goals"))
    constraint_rows = _strings(product_facts.get("operational_constraints"))
    assumption_rows = _strings(product_facts.get("assumptions"))
    evidence_rows = _ordered_unique(
        (
            *_strings(product_facts.get("evidence_requirements")),
            *(proof_row for component in components for proof_row in component["validation"]),
        )
    )
    risk_rows = _ordered_unique(
        component["component_contract"]["unique_failure"] for component in components
    )
    state_summary = _sentence_list(plan.state_labels)
    output_summary = _sentence_list(plan.visible_output_labels)
    rows = {
        "intent": [
            str(product_facts["product_story"]),
            str(product_facts["problem"]),
            str(product_facts["product_view"]),
        ],
        "scope": [
            f"In scope: {path}",
            f"Release boundary: {proof}",
            *(f"Excluded: {row}" for row in non_goal_rows),
        ],
        "ontology": [
            f"Product: {title}.",
            *([f"The accepted state objects are {state_summary}."] if plan.state_labels else []),
            f"Visible outputs: {output_summary}.",
        ],
        **(
            {
                "state": [
                    f"Accepted state objects: {state_summary}",
                    f"Validation must reconstruct {state_summary} without changing the sealed graph.",
                ]
            }
            if plan.state_labels
            else {}
        ),
        "operators": [
            *(f"Accepted actor: {row}" for row in actor_rows),
            f"Ordered workflow: {path}",
        ],
        "constraints": [
            *(f"Operational constraint: {row}" for row in constraint_rows),
            *(f"Excluded behavior: {row}" for row in non_goal_rows),
        ],
        "source_of_truth_map": [
            f"The sealed Semantic Intent graph owns product meaning for {title}.",
            f"Typed component contracts own implementation boundaries: {systems}.",
        ],
        "evidence": [f"Release proof: {proof}", *evidence_rows],
        "decisions": [
            f"Implement the workflow in sealed order: {path}",
            (
                f"Promote release {release} only after {output_summary} is visible and {state_summary} is reconstructed."
                if plan.state_labels
                else f"Promote release {release} only after {output_summary} is visible."
            ),
        ],
        "assumptions": list(assumption_rows),
        "topology": [
            f"Product systems: {systems}.",
            *(f"External system: {row}" for row in external_rows),
        ],
        "invariants": [
            "Rendered governance cannot change graph facts or relation ownership.",
            f"Every release claim remains linked to {output_summary} and source citations.",
        ],
        "risks": list(risk_rows),
        "validation_obligations": [
            f"Validate the complete success path: {path}",
            f"Validate the release boundary: {proof}",
            *(
                [f"Reconstruct every state object from exact typed facts: {state_summary}."]
                if plan.state_labels
                else []
            ),
            *_strings(product_facts.get("success_metrics")),
        ],
        "owners": [
            f"Human action owners: {actors}.",
            "Relationless system and output behavior remains product-owned.",
        ],
    }
    return {
        "schema_version": _PI_VERSION,
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "purpose": f"Preserve why {title} exists and how {output_summary} proves its consumer outcome.",
        "coding_posture": (
            f"Coding starts only after the sealed workflow, accepted state objects ({state_summary}), visible outputs ({output_summary}), component boundaries, and release evidence agree end to end."
            if plan.state_labels
            else f"Coding starts only after the sealed workflow, visible outputs ({output_summary}), component boundaries, and release evidence agree end to end."
        ),
        "control_surface_summary": [
            str(product_facts["product_story"]),
            str(product_facts["problem"]),
            str(product_facts["opportunity"]),
            f"First path: {path}",
            f"Release proof: {proof}",
        ],
        "customization_flow": [
            "Correct source evidence when a fact is wrong.",
            "Regenerate the Semantic Intent graph from the corrected evidence.",
            "Confirm only the exact hash-bound transaction that passed all gates.",
        ],
        **rows,
    }


def _risks(components: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "id": f"RISK-{index:03d}",
            "title": f"{row['label']} boundary failure",
            "severity": "high" if index == 1 else "medium",
            "statement": str(row["component_contract"]["unique_failure"]),
            "mitigation": str(row["validation"][0]),
            "custody_state": str(row["custody_state"]),
            "evidence_tier": str(row["evidence_tier"]),
        }
        for index, row in enumerate(components, 1)
    ]


def _bind_artifacts(proposal: dict[str, Any], *, project_slug: str, title: str) -> None:
    base = {
        "source": "project_intelligence",
        "schema_version": _PI_VERSION,
        "project_title": title,
        "project_slug": project_slug,
        "evidence_boundary": "derived_from_project_intelligence",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
    }
    proposal["artifact_derivation"] = {
        "root": "project_intelligence",
        "root_schema_version": _PI_VERSION,
        "project_title": title,
        "project_slug": project_slug,
        "derived_artifacts": ["release_plan", "backlog", "components", "diagrams"],
        "validation_gate": "greenfield-validation-gate-v1",
        "rule": "Generated artifacts preserve the sealed graph and project-intelligence proof boundary.",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
    }
    release = proposal["release_plan"]
    release["project_intelligence_binding"] = {
        **base,
        "artifact_kind": "release_plan",
        "artifact_id": release["provisional_release_id"],
    }
    for key, kind, identifier in (
        ("backlog", "radar_workstream", "title"),
        ("components", "registry_component", "component_id"),
        ("diagrams", "atlas_diagram", "slug"),
    ):
        for row in proposal[key]:
            row["project_intelligence_binding"] = {
                **base,
                "artifact_kind": kind,
                "artifact_id": semantic_artifact_identifier(str(row[identifier])),
            }


def _assumptions(graph: Mapping[str, Any]) -> list[dict[str, str]]:
    rows = _facts(graph, "assumption")
    return [
        {
            "id": f"ASM-{index:03d}",
            "tier": semantic_evidence_tier(str(row["custody"])),
            "custody_state": str(row["custody"]),
            "statement": str(row["statement"]),
            "confirm_when": "A source-cited correction changes this assumption.",
        }
        for index, row in enumerate(rows, 1)
    ]


def _open_questions(graph: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "id": f"OQ-{index:03d}",
            "question": str(row["statement"]),
            "impact": "Changes a material graph fact or relation.",
            "default_if_unanswered": "Block confirmation until the graph is corrected.",
            "custody_state": str(row["custody"]),
            "evidence_tier": semantic_evidence_tier(str(row["custody"])),
        }
        for index, row in enumerate(_facts(graph, "ambiguity"), 1)
    ]


def _brief_section(section: str, must_capture: str, why: str) -> dict[str, str]:
    return {"section": section, "must_capture": must_capture, "why_it_matters": why}


def _decision(
    identifier: str,
    decision: str,
    recommended: str,
    impact: str,
    choices: Sequence[str],
) -> dict[str, Any]:
    return {
        "id": identifier,
        "decision": decision,
        "recommended": recommended,
        "choices": list(choices),
        "impact": impact,
    }


def _facts(graph: Mapping[str, Any], kind: str) -> list[Mapping[str, Any]]:
    return sorted(
        (row for row in graph["facts"] if row["kind"] == kind),
        key=lambda row: int(row["order"]),
    )


def _fact_labels(graph: Mapping[str, Any], kind: str) -> list[str]:
    return [str(row["label"]) for row in _facts(graph, kind)]


def _attributes(fact: Mapping[str, Any]) -> dict[str, str]:
    return {str(row["name"]): str(row["value"]) for row in fact["attributes"]}


def _targets(relations: Sequence[Mapping[str, Any]], kind: str) -> dict[str, list[str]]:
    result: dict[str, list[tuple[int, str]]] = {}
    for row in relations:
        if row["kind"] == kind:
            result.setdefault(str(row["subject_id"]), []).append(
                (int(row["order"]), str(row["object_id"]))
            )
    return {key: [value for _, value in sorted(rows)] for key, rows in result.items()}


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(row).strip() for row in value if str(row).strip()]


def _ordered_unique(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if token and token not in result:
            result.append(token)
    return result


def _fragments(values: Any) -> list[str]:
    return [str(value).strip().rstrip(" .!?") for value in values if str(value).strip().rstrip(" .!?")]


def _sentence_list(values: Any, *, fallback: str = "") -> str:
    rows = _ordered_unique(values)
    if not rows:
        return fallback
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


__all__ = ["build_verified_semantic_proposal"]
