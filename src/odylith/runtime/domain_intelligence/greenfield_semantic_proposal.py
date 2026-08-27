"""Project a complete Greenfield proposal from one verified semantic graph.

This module is intentionally interpretation-free.  The host supplies source-cited
meaning; this projector follows typed facts and relations and never reparses prose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_release_contract import DEFAULT_GREENFIELD_RELEASE_SELECTOR
from odylith.runtime.domain_intelligence.greenfield_semantic_backlog_projection import (
    semantic_backlog_rows,
    semantic_policy_boundary_summaries,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_evidence_tier,
    semantic_fact_custody_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_diagrams import semantic_diagrams
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    require_semantic_intent_ir,
    semantic_intent_meaning_sha256,
    semantic_intent_product_facts,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import semantic_artifact_identifier
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    SemanticProjectionPlan,
    build_semantic_projection_plan,
    semantic_projection_plan_mapping,
    semantic_release_plan,
    semantic_security_compliance,
    semantic_validation_strategy,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_binding import (
    PRODUCT_INTENT_REVIEW_BINDING_KEY,
    product_intent_review_binding,
)


def build_verified_semantic_proposal(
    *,
    authority: Mapping[str, Any],
    observed_source: Mapping[str, Any],
    release_selector: str = "",
) -> dict[str, Any]:
    """Return one deterministic proposal from validated Semantic Intent authority."""

    review_binding = product_intent_review_binding(authority)
    if authority.get("origin") != "verified_semantic_intent_packet":
        raise ValueError("verified semantic proposal requires source-cited Semantic Intent authority")
    evidence_sources = authority.get("evidence_sources")
    if not isinstance(evidence_sources, Mapping):
        raise ValueError("verified semantic proposal lacks evidence sources")
    graph = require_semantic_intent_ir(
        authority.get("semantic_intent"),
        evidence_sources=evidence_sources,
    )
    product_facts = semantic_intent_product_facts(graph)
    release = str(release_selector or "").strip() or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    title = str(graph["presentation"]["title"])
    project_slug = semantic_artifact_identifier(
        f"{semantic_artifact_identifier(observed_source.get('repo_name'), fallback='greenfield-project')}-{semantic_intent_meaning_sha256(graph)[:12]}",
        fallback="greenfield-project",
    )
    projection_plan = build_semantic_projection_plan(
        graph,
        project_slug=project_slug,
    )
    presentation_facts = _presentation_product_facts(
        product_facts=product_facts,
        plan=projection_plan,
    )
    security_compliance = semantic_security_compliance(
        plan=projection_plan,
        proof_boundary=str(product_facts["proof_boundary"]),
    )
    security_compliance["policy_boundaries"] = _sentence_list(
        _policy_boundary_summaries(product_facts),
        fallback="None asserted",
    )
    components = list(projection_plan.components)
    backlog = semantic_backlog_rows(
        plan=projection_plan,
        problem=str(presentation_facts["problem"]),
        customer=str(presentation_facts["customer"]),
        opportunity=str(presentation_facts["opportunity"]),
        product_view=str(presentation_facts["product_view"]),
        success_metrics=_strings(product_facts.get("success_metrics")),
        proof_boundary=str(product_facts["proof_boundary"]),
    )
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.proposal.v11",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": _intent(
            product_facts,
            graph=graph,
            project_slug=project_slug,
            release=release,
            title=projection_plan.title,
            presentation=projection_plan.presentation,
            components=components,
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
        "open_questions": [],
        "risks": _risks(components),
        "security_compliance": security_compliance,
        "validation_strategy": semantic_validation_strategy(
            plan=projection_plan,
            success_metrics=_strings(product_facts.get("success_metrics")),
            proof_boundary=str(product_facts["proof_boundary"]),
        ),
        "project_brief": _project_brief(
            product_facts=presentation_facts,
            graph=graph,
            plan=projection_plan,
            components=components,
            release=release,
        ),
        "release_plan": semantic_release_plan(
            release=release,
            plan=projection_plan,
        ),
        "backlog": backlog,
        "components": components,
        "projection_plan": semantic_projection_plan_mapping(projection_plan),
        "diagrams": semantic_diagrams(
            plan=projection_plan,
            backlog=backlog,
        ),
        "apply_commands": [
            "odylith greenfield semantic-intent-request --prompt <request>",
            "odylith greenfield propose --repo-root . --prompt <request> --semantic-intent-file <semantic-intent.json>",
            "# CONFIRM commits the exact hash-bound transaction; EDIT rebuilds from new evidence.",
        ],
        PRODUCT_INTENT_REVIEW_BINDING_KEY: review_binding,
    }
    return proposal


def _intent(
    product_facts: Mapping[str, Any],
    *,
    graph: Mapping[str, Any],
    project_slug: str,
    release: str,
    title: str,
    presentation: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    result = dict(product_facts)
    result.update(
        {
            "title": title,
            "presentation": dict(presentation),
            "owned_capabilities": [
                f"{component['label']}: {component['responsibility']}"
                for component in components
            ],
            "prompt": "",
            "project_slug": project_slug,
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
            "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
            "semantic_fact_custody": semantic_fact_custody_rows(graph["facts"]),
            "summary": f"{product_facts['product_story']} Release {release} is limited to the sealed path.",
        }
    )
    return result


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
    policy_boundaries = _policy_boundary_summaries(product_facts)
    step_phrases = [_attributes(row)["action_phrase"] for row in _facts(graph, "workflow_step")]
    state_summary = _sentence_list(plan.state_labels)
    output_summary = _sentence_list(plan.visible_output_labels)
    blueprint = [
        _brief_section(
            "Consumer outcome",
            str(product_facts["product_story"]),
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
                f"{product_facts['proof_boundary']} "
                f"Policy boundaries: {_sentence_list(_fragments(policy_boundaries), fallback='none asserted')}."
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
        "schema_version": "odylith.greenfield.project_brief.v4",
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(SEMANTIC_SYSTEM_POLICY_CUSTODY),
        "semantic_fact_custody": semantic_fact_custody_rows(graph["facts"]),
        "purpose": str(product_facts["product_story"]),
        "operating_principle": f"Release {release} implements only the sealed graph and its source citations.",
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
            f"Policy boundaries remain enforced: {_sentence_list(_fragments(policy_boundaries), fallback='none asserted')}.",
        ],
        "policy_boundaries": policy_boundaries,
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


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(row).strip() for row in value if str(row).strip()]


def _policy_boundary_summaries(product_facts: Mapping[str, Any]) -> list[str]:
    value = product_facts.get("policy_boundaries")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError("verified policy boundary projection is malformed")
    return list(semantic_policy_boundary_summaries(value))


def _presentation_product_facts(
    *, product_facts: Mapping[str, Any], plan: SemanticProjectionPlan
) -> dict[str, Any]:
    """Render typed facts as standalone clauses without repairing authored prose."""

    result = dict(product_facts)
    result["title"] = plan.title
    ordered_path = " ".join(
        f"Step {index} — {action}."
        for index, action in enumerate(
            _fragments(
                plan.node_by_id[fact_id].label
                for fact_id in plan.workflow_step_fact_ids
            ),
            1,
        )
    )
    owner_summary = _sentence_list(
        plan.human_action_owner_labels,
        fallback="none declared",
    )
    boundary_summary = _sentence_list(
        (
            *_strings(product_facts.get("product_boundaries")),
            *_policy_boundary_summaries(product_facts),
        ),
        fallback="none asserted",
    )
    result["problem"] = (
        f"{plan.title} needs a governed first path. Participants: {owner_summary}. "
        f"Required path: {ordered_path} Boundaries: {boundary_summary}."
    )
    result["product_view"] = (
        f"First path: {ordered_path} "
        f"Visible results: {_sentence_list(plan.visible_output_labels)}. "
        f"State: {_sentence_list(plan.state_labels, fallback='no durable state declared')}. "
        f"Dependencies: {_sentence_list(product_facts.get('external_systems'), fallback='none declared')}. "
        f"Boundaries: {boundary_summary}."
    )
    return result


def _ordered_unique(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if token and token not in result:
            result.append(token)
    return result


def _fragments(values: Any) -> list[str]:
    return [
        str(value).strip().rstrip(" .!?")
        for value in values
        if str(value).strip().rstrip(" .!?")
    ]


def _sentence_list(values: Any, *, fallback: str = "") -> str:
    rows = _ordered_unique(_fragments(values))
    if not rows:
        return fallback
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


__all__ = ["build_verified_semantic_proposal"]
