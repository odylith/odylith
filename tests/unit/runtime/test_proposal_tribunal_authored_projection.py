"""Structural Tribunal coverage for model-authored Greenfield proposals."""

from __future__ import annotations

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence import proposal_tribunal
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    AUTHORED_SEMANTICS_KEY,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.project_intelligence_binding import (
    attach_project_intelligence_bindings,
)


def _authored_proposal() -> dict[str, object]:
    first_path = "Dock attendant records berth occupancy and sees receipt"
    relation = {
        "order": 1,
        "source_start_byte": 0,
        "source_end_byte": len(first_path.encode("utf-8")),
        "event_start_byte": 0,
        "event_end_byte": len(first_path.encode("utf-8")),
        "actor_kind": "human",
        "actor_quote": "Dock attendant",
        "actor_is_carried": False,
        "actor_fact_path": "/human_actors/0",
        "actor_fact_quote": "Dock attendant",
        "owner_system_path": "",
        "owner_system_quote": "",
        "event_quote": first_path,
        "action_verb_quote": "records",
        "target_quote": "berth occupancy",
        "visible_result_quote": "sees receipt",
        "recovery_path": False,
    }
    intent = {
        "title": "Harbor Desk",
        "product_story": "Dock attendants receive a reviewable berth receipt.",
        "state_object": "berth occupancy",
        "first_path": first_path,
        "proof_boundary": "Verify the receipt and retained berth occupancy.",
        "problem": "Berth occupancy is hard to review.",
        "customer": "Dock attendants",
        "opportunity": "Provide one reviewable berth workflow.",
        "product_view": "Harbor Desk records berth occupancy.",
        "success_metrics": ["The dock attendant sees a receipt."],
        "evidence_requirements": ["Retain berth occupancy evidence."],
        "operational_constraints": [],
        "component_responsibilities": ["Record berth occupancy."],
        "human_actors": ["Dock attendant"],
        "external_systems": [],
        "internal_systems": [],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
        AUTHORED_SEMANTICS_KEY: authored_semantics_mapping(
            (relation,),
            (
                {
                    "responsibility_path": "/component_responsibilities/0",
                    "responsibility_quote": "Record berth occupancy.",
                    "owner_system_path": "/title",
                    "owner_system_quote": "Harbor Desk",
                    "first_path_event_order": 0,
                    "responsibility_source": "accepted_fact",
                },
            ),
            first_path_context_relations=(
                {
                    "context_kind": "state_object",
                    "fact_path": "/state_object",
                    "fact_quote": "berth occupancy",
                    "source_start_byte": 0,
                    "source_end_byte": len("berth occupancy".encode("utf-8")),
                    "first_path_event_order": 1,
                },
            ),
        ),
    }
    return attach_project_intelligence_bindings(
        build_authored_greenfield_proposal(
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=intent,
        )
    )


def test_authored_typed_projection_passes_structural_tribunal() -> None:
    proposal = _authored_proposal()
    decision = proposal_tribunal.run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert decision.passed
    assert decision.issues == ()
    assert set(decision.dimensions) == {
        "typed_intent",
        "artifact_topology",
        "semantic_projection",
        "provenance",
    }
    assert all(value.startswith("checked ") for value in decision.dimensions.values())
    assert decision.visible_actors == (
        {
            "stable_role": "domain_operator",
            "visible_actor": "Dock attendant",
            "actor_source": "explicit_intent_actor",
            "responsibility": "Dock attendant records berth occupancy and sees receipt",
        },
    )
    assert proposal["security_compliance"] == {}
    component = proposal["components"][0]
    assert set(component["component_contract"]) == {
        "owner_system",
        "responsibility_facts",
        "owner_bound_events",
        "event_targets",
        "visible_results",
        "recovery_events",
        "state_context",
        "external_dependencies",
        "operational_constraints",
    }
    assert component["boundary"] == ""
    assert component["dependencies"] == []
    assert component["interfaces"] == []
    assert component["validation"] == []


@pytest.mark.parametrize(
    "mutate",
    (
        lambda proposal: proposal.update(
            {"security_compliance": {"security": "fabricated security posture"}}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"local_proof": ["fabricated component proof"]}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"owner_system": "Fabricated owner"}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"responsibility_facts": ["Fabricated responsibility"]}
        ) or proposal["components"][0].update(
            {"responsibility": "Fabricated responsibility"}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"owner_bound_events": ["Fabricated event"]}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"event_targets": ["Fabricated target"]}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"visible_results": ["Fabricated result"]}
        ),
        lambda proposal: proposal["components"][0]["component_contract"].update(
            {"recovery_events": ["Fabricated recovery"]}
        ),
        lambda proposal: proposal["backlog"].append(dict(proposal["backlog"][0])),
    ),
)
def test_authored_tribunal_rejects_downstream_semantic_ownership(mutate) -> None:
    proposal = deepcopy(_authored_proposal())
    mutate(proposal)

    decision = proposal_tribunal.run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert not decision.passed


def _rename_backlog_projection_everywhere(proposal) -> None:
    replacement = "Deliver a different product"
    proposal["backlog"][0]["title"] = replacement
    proposal["release_plan"]["target_workstream_titles"] = [replacement]
    proposal["release_plan"]["release_stages"][0]["workstream_titles"] = [replacement]
    for diagram in proposal["diagrams"]:
        diagram["related_workstream_titles"] = [replacement]
    proposal["semantic_model"]["workstreams"][0]["title"] = replacement
    rebound = attach_project_intelligence_bindings(proposal)
    proposal.clear()
    proposal.update(rebound)


@pytest.mark.parametrize(
    "mutate",
    (
        pytest.param(
            lambda proposal: proposal["backlog"][0].update({"customer": "todo"}),
            id="backlog-customer",
        ),
        pytest.param(
            lambda proposal: proposal["backlog"][0]["radar_sections"].update(
                {"Validation": "todo"}
            ),
            id="backlog-native-section",
        ),
        pytest.param(
            lambda proposal: proposal["backlog"][0].update({"unexpected": "todo"}),
            id="backlog-extra-field",
        ),
        pytest.param(
            lambda proposal: proposal["diagrams"][0].update({"summary": "todo"}),
            id="atlas-summary",
        ),
        pytest.param(
            lambda proposal: proposal["diagrams"][0].update({"read_guide": "todo"}),
            id="atlas-read-guide",
        ),
        pytest.param(
            lambda proposal: proposal["diagrams"][0].update({"mermaid_source": "todo"}),
            id="atlas-source",
        ),
        pytest.param(
            lambda proposal: proposal["components"][0].update({"label": "todo"}),
            id="component-label",
        ),
        pytest.param(
            lambda proposal: proposal["release_plan"].update({"strategy": "todo"}),
            id="release-strategy",
        ),
        pytest.param(
            lambda proposal: proposal["project_intelligence"].update({"purpose": "todo"}),
            id="project-intelligence",
        ),
        pytest.param(
            lambda proposal: proposal["project_brief"].update({"purpose": "todo"}),
            id="project-brief",
        ),
        pytest.param(
            lambda proposal: proposal["semantic_model"]["domain_ontology"].update(
                {"proof_boundary": "todo"}
            ),
            id="semantic-model",
        ),
        pytest.param(
            lambda proposal: proposal["validation_strategy"].append("todo"),
            id="validation-strategy",
        ),
        pytest.param(
            lambda proposal: proposal["classification"].update({"fit_policy": "todo"}),
            id="classification",
        ),
        pytest.param(
            lambda proposal: proposal["greenfield_ux"].update({"next_best_action": "todo"}),
            id="greenfield-ux",
        ),
        pytest.param(
            lambda proposal: proposal["apply_commands"].__setitem__(0, "todo"),
            id="apply-command",
        ),
        pytest.param(_rename_backlog_projection_everywhere, id="coordinated-backlog-rename"),
    ),
)
def test_authored_tribunal_exactly_binds_deterministic_projection(mutate) -> None:
    proposal = deepcopy(_authored_proposal())
    mutate(proposal)

    decision = proposal_tribunal.run_greenfield_tribunal(
        proposal,
        release_selector="0.0.1",
    )

    assert not decision.passed
    assert any(
        issue.startswith(
            "authored proposal must exactly match the deterministic projection of its sealed typed intent"
        )
        for issue in decision.issues
    )


def test_authored_typed_projection_has_no_legacy_quality_or_semantic_gates() -> None:
    for name in (
        "greenfield_quality_issues",
        "tribunal_actor_projection",
        "check_confirmed_artifact_substance",
        "slugify",
        "_check_release_plan",
        "_check_backlog_topology",
        "_check_component_specs",
        "_check_diagram_traceability",
        "_check_domain_security_posture",
        "_check_visible_tribunal_actors",
        "greenfield_programs",
    ):
        assert not hasattr(proposal_tribunal, name)

    decision = proposal_tribunal.run_greenfield_tribunal(_authored_proposal())

    assert decision.passed
    assert set(decision.dimensions) == {
        "typed_intent",
        "artifact_topology",
        "semantic_projection",
        "provenance",
    }


def test_malformed_authored_projection_fails_closed_without_legacy_fallback(
) -> None:
    proposal = deepcopy(_authored_proposal())
    assert proposal["projection_origin"] == AUTHORED_PROJECTION_ORIGIN
    intent = proposal["intent"]
    assert isinstance(intent, dict)
    intent.pop(AUTHORED_SEMANTICS_KEY)

    assert not hasattr(proposal_tribunal, "greenfield_quality_issues")
    assert not hasattr(proposal_tribunal, "tribunal_actor_projection")

    decision = proposal_tribunal.run_greenfield_tribunal(proposal)

    assert not decision.passed
    assert "authored proposal must preserve valid first_path_relations" in decision.issues


def test_non_authored_proposal_is_rejected_without_a_legacy_fallback() -> None:
    with pytest.raises(ValueError, match="requires a sealed authored projection"):
        proposal_tribunal.run_greenfield_tribunal(
            {"intent": {}, "backlog": [], "components": [], "diagrams": [], "release_plan": {}}
        )
