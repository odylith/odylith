from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_backlog_projection import (
    semantic_backlog_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_component_package import (
    semantic_component_authoring_inputs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_diagrams import (
    semantic_diagrams,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    build_semantic_projection_plan,
    semantic_projection_plan_mapping,
    semantic_release_plan,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_proposal import (
    build_verified_semantic_proposal,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    PATH_EVIDENCE,
    SEMANTIC_PROMPT,
    semantic_intent_packet,
    semantic_relation,
    stateless_semantic_intent_packet as _stateless_packet,
)


def test_actorless_stateless_two_output_plan_stays_single_policy_slice() -> None:
    packet, prompt = _stateless_packet()
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    authority = semantic_intent_authority(verified, prompt=prompt)
    proposal = build_verified_semantic_proposal(
        authority=authority,
        observed_source={},
    )
    graph = packet["semantic_intent"]
    plan = build_semantic_projection_plan(graph, project_slug="signal-view")
    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)

    assert plan.state_fact_ids == ()
    assert plan.visible_output_fact_ids == ("output.0", "output.1")
    assert len(plan.components) == 1
    assert [(row.kind, row.component_ids) for row in plan.workstream_plans] == [
        ("product", ("signal-view-first-path",)),
    ]
    assert [row.title for row in plan.diagram_plans] == ["First Path"]
    assert len(backlog) == 1
    assert backlog[0]["component_focus"] == ["signal-view-first-path"]
    assert len(diagrams) == 1
    # Both outputs are nested under the source workflow step, so the projection
    # retains their exact production and audience edges without adding topology.
    assert diagrams[0]["semantic_relation_ids"] == [
        "produces.0",
        "produces.1",
        "output-of.0",
        "output-of.1",
        "visible-to.0",
        "visible-to.1",
    ]
    assert diagrams[0]["projection_view_edge_ids"] == []
    assert diagrams[0]["mermaid_source"].count(" -->|") == 6
    assert "-.->|then|" not in diagrams[0]["mermaid_source"]
    assert len(proposal["components"]) == 1
    assert len(proposal["backlog"]) == 1
    assert len(proposal["diagrams"]) == 1
    contract = proposal["components"][0]["component_contract"]
    assert contract["schema_version"] == (
            "odylith.greenfield.semantic-component-contract.v9"
    )
    assert contract["component_role"] == "result_implementing"
    assert contract["workflow_fact_ids"] == ["step.0"]
    assert contract["workflow_labels"] == [
        "present a signal chart and signal summary"
    ]
    assert contract["state_objects"] == []
    assert contract["visible_outputs"] == ["Signal chart", "Signal summary"]
    assert {"owned_state", "produced_outputs", "states_or_transitions"}.isdisjoint(
        contract
    )
    assert proposal["components"][0]["validation"] == [
        "Prove every covered workflow step and declared effect from exact typed facts."
    ]
    assert all(
        "replay" not in row.casefold()
        for row in proposal["components"][0]["validation"]
    )
    assert "semantic_model" not in proposal
    authoring_contract = semantic_component_authoring_inputs(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={
            "created": [
                {"idea_id": "B-001", "title": proposal["backlog"][0]["title"]}
            ]
        },
        diagram_ids=("D-001",),
    )[0]["component_contract"]
    assert authoring_contract["state_objects"] == ()
    assert authoring_contract["visible_outputs"] == (
        "Signal chart",
        "Signal summary",
    )
    assert authoring_contract["component_role"] == "result_implementing"
    assert authoring_contract["local_proof"] == (
        "Prove every covered workflow step and declared effect from exact typed facts.",
    )


def test_component_interfaces_render_typed_step_labels_not_raw_source_copy() -> None:
    graph = _stateless_graph()
    raw_envelope = '{"product_intent":{"first_path":"present both outputs"}}'
    workflow = next(row for row in graph["facts"] if row["kind"] == "workflow_step")
    workflow["statement"] = raw_envelope

    plan = build_semantic_projection_plan(graph, project_slug="signal-view")
    interfaces = plan.components[0]["interfaces"]

    assert raw_envelope not in " ".join(interfaces)
    assert interfaces.count("Covers the “Present signal” workflow step.") == 1


def test_semantic_artifact_ids_transliterate_copy_without_changing_copy() -> None:
    assert semantic_artifact_identifier("Café Résumé Board") == "cafe-resume-board"
    fallback = semantic_artifact_identifier("審査盤", fallback="project")
    assert fallback.startswith("project-")
    assert fallback.isascii()


def test_diagram_boxes_disambiguate_equal_labels_by_typed_role() -> None:
    graph = _stateless_graph()
    workflow = next(row for row in graph["facts"] if row["fact_id"] == "step.0")
    output = next(row for row in graph["facts"] if row["fact_id"] == "output.0")
    workflow["label"] = "Signal View"
    output["label"] = "Signal View"
    plan = build_semantic_projection_plan(graph, project_slug="signal-view")

    diagrams = semantic_diagrams(plan=plan, backlog=_backlog(plan))
    labels = [
        box["label"]
        for diagram in diagrams
        for box in diagram["diagram_boxes"]
    ]

    assert "Signal View — Workflow step" in labels
    assert "Signal View — Visible output" in labels
    assert len({label.casefold() for label in labels}) == len(labels)


def test_state_object_without_endpoint_pair_stays_stateful_without_invented_transition() -> None:
    graph = _stateless_graph()
    graph["facts"].extend(
        [
            _fact(
                "entity.3",
                "entity",
                "Signal record",
                "The signal record.",
                3,
                attributes={},
            ),
            _fact(
                "state.0",
                "state_object",
                "Signal record",
                "The signal record is durable.",
                0,
                attributes={"object": "Signal record", "entity_id": "entity.3"},
            ),
        ]
    )
    graph["relations"].extend(
        [
            _relation(
                "relation.target_entity.0",
                "target_entity",
                "step.0",
                "entity.3",
                0,
            ),
            _relation("relation.changes.0", "changes", "step.0", "state.0", 0),
            _relation("relation.state_of.0", "state_of", "state.0", "entity.3", 0),
        ]
    )
    plan = build_semantic_projection_plan(graph, project_slug="signal-view")
    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)
    proposal = {
        "projection_plan": semantic_projection_plan_mapping(plan),
        "components": list(plan.components),
        "backlog": backlog,
        "diagrams": diagrams,
        "risks": [],
    }
    contract = semantic_component_authoring_inputs(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={"created": [{"idea_id": "B-001", "title": backlog[0]["title"]}]},
        diagram_ids=tuple(f"D-{index:03d}" for index in range(1, len(diagrams) + 1)),
    )[0]["component_contract"]

    assert contract["state_objects"] == ("Signal record",)
    assert contract["state_transitions"] == ()
    assert contract["stateful"] is True


def test_dependency_and_policy_facts_do_not_create_synthetic_components() -> None:
    graph = _supporting_boundary_graph()
    plan, inputs = _component_inputs(graph)

    assert len(plan.components) == 1
    assert len(plan.workstream_plans) == 1
    assert len(inputs) == 1
    component = plan.components[0]
    assert component["implementation_policy_id"] == "implementation-policy.0"
    assert component["component_role"] == "result_implementing"
    assert component["custody_state"] == "system_policy"
    assert component["dependencies"] == ["Depends on Signal Source."]
    assert "external.0" in component["projection_basis_fact_ids"]
    assert all(row.kind != "internal_system" for row in plan.nodes)


def test_graph_lane_source_has_no_synthetic_result_fallback() -> None:
    source_root = (
        Path(__file__).parents[3]
        / "src/odylith/runtime/domain_intelligence"
    )
    offenders = [
        path.name
        for path in source_root.glob("greenfield_semantic_*.py")
        if "a reviewable first-path result" in path.read_text(
            encoding="utf-8"
        ).casefold()
    ]

    assert offenders == []


def test_two_state_two_output_plan_stays_one_component_and_preserves_every_edge() -> None:
    graph = _two_state_graph()
    plan = build_semantic_projection_plan(graph, project_slug="review-flow")
    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)

    assert plan.state_fact_ids == ("state.0", "state.1")
    assert plan.visible_output_fact_ids == ("output.0", "output.1")
    assert len(plan.components) == 1
    assert [row.kind for row in plan.workstream_plans] == ["product"]
    assert len(backlog) == 1
    assert backlog[0]["component_focus"] == ["review-flow-first-path"]
    assert [row.key for row in plan.diagram_plans] == [
        "first_path",
    ]
    assert len(diagrams) == 1
    first_path = diagrams[0]
    assert first_path["semantic_relation_ids"] == [
        "relation.target_entity.0",
        "relation.target_entity.1",
        "relation.produces.0",
        "relation.produces.1",
        "relation.output_of.0",
        "relation.output_of.1",
        "relation.changes.0",
        "relation.changes.1",
        "relation.state_of.0",
        "relation.state_of.1",
    ]
    assert first_path["projection_view_edge_ids"] == ["workflow-sequence-0"]
    assert first_path["mermaid_source"].count(" -->|") == 10
    assert first_path["mermaid_source"].count(" -.->|then|") == 1
    contract = plan.components[0]["component_contract"]
    assert contract["workflow_fact_ids"] == ["step.0", "step.1"]
    assert contract["state_objects"] == ["Intake record", "Decision record"]
    assert contract["visible_outputs"] == ["Intake receipt", "Decision notice"]
    assert plan.components[0]["covered_fact_ids"] == [
        "step.0",
        "step.1",
        "state.0",
        "state.1",
        "output.0",
        "output.1",
    ]


def test_projection_plan_hard_cuts_synthetic_system_authority() -> None:
    plan = build_semantic_projection_plan(
        _two_state_graph(),
        project_slug="review-flow",
    )
    persisted = semantic_projection_plan_mapping(plan)
    release = semantic_release_plan(plan=plan, release="0.0.1")

    assert persisted["axes"]["implementation_policy_ids"] == [
        "implementation-policy.0"
    ]
    assert "component_fact_ids" not in persisted["axes"]
    assert persisted["components"] == [
        {
            "component_id": "review-flow-first-path",
            "implementation_policy_id": "implementation-policy.0",
            "release_scope": "first_path_required",
            "component_role": "result_implementing",
            "covered_fact_ids": [
                "step.0",
                "step.1",
                "state.0",
                "state.1",
                "output.0",
                "output.1",
            ],
            "projection_basis_fact_ids": [
                node.fact_id for node in plan.nodes
            ],
        }
    ]
    assert all(node.kind != "internal_system" for node in plan.nodes)
    assert all(edge.kind != "implements" for edge in plan.edges)
    assert release["release_component_policy_ids"] == [
        "implementation-policy.0"
    ]
    assert {
        "release_component_fact_ids",
        "result_component_fact_ids",
        "supporting_component_fact_ids",
        "deferred_component_fact_ids",
    }.isdisjoint(release)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("policy_as_fact", "must not masquerade"),
        ("missing_coverage", "coverage drifted"),
    ],
)
def test_component_package_rejects_policy_or_coverage_drift(
    mutation: str,
    message: str,
) -> None:
    plan = build_semantic_projection_plan(
        _stateless_graph(),
        project_slug="signal-view",
    )
    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)
    proposal = {
        "projection_plan": semantic_projection_plan_mapping(plan),
        "components": copy.deepcopy(list(plan.components)),
        "backlog": backlog,
        "diagrams": diagrams,
        "risks": [],
    }
    component_plan = proposal["projection_plan"]["components"][0]
    component = proposal["components"][0]
    if mutation == "policy_as_fact":
        component_plan["implementation_policy_id"] = "step.0"
        component["implementation_policy_id"] = "step.0"
        component["component_contract"]["implementation_policy_id"] = "step.0"
        proposal["projection_plan"]["axes"]["implementation_policy_ids"] = [
            "step.0"
        ]
    else:
        component_plan["covered_fact_ids"] = ["step.0", "output.0"]
        component["covered_fact_ids"] = ["step.0", "output.0"]
        component["component_contract"]["covered_fact_ids"] = [
            "step.0",
            "output.0",
        ]

    with pytest.raises(ValueError, match=message):
        semantic_component_authoring_inputs(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result={
                "created": [{"idea_id": "B-001", "title": backlog[0]["title"]}]
            },
            diagram_ids=tuple(
                f"D-{index:03d}" for index in range(1, len(diagrams) + 1)
            ),
        )


def test_projection_depth_changes_only_the_affected_adaptive_surfaces() -> None:
    baseline_graph = _stateless_graph()
    baseline = build_semantic_projection_plan(
        baseline_graph,
        project_slug="signal-view",
    )

    constrained_graph = copy.deepcopy(baseline_graph)
    constrained_graph["facts"].append(
        _fact(
            "policy-boundary.0",
            "policy_boundary",
            "Read-only input",
            "Input remains read-only.",
            0,
            attributes={
                "modality": "limited",
                "behavior": "read",
                "target": "input",
            },
        )
    )
    constrained_graph["relations"].append(
        _relation(
            "relation.applies_to.0",
            "applies_to",
            "policy-boundary.0",
            "step.0",
            0,
        )
    )
    constrained = build_semantic_projection_plan(
        constrained_graph,
        project_slug="signal-view",
    )

    assert len(constrained.nodes) == len(baseline.nodes) + 1
    assert len(constrained.edges) == len(baseline.edges) + 1
    assert len(constrained.diagram_plans) == len(baseline.diagram_plans)
    assert len(constrained.workstream_plans) == len(baseline.workstream_plans)
    assert constrained.diagram_plans[0].relation_ids == (
        baseline.diagram_plans[0].relation_ids
    )

    stateful_graph = copy.deepcopy(baseline_graph)
    stateful_graph["facts"].extend(
        [
            _fact(
                "entity.3",
                "entity",
                "Signal record",
                "The signal record.",
                3,
                attributes={},
            ),
            _fact(
                "state.0",
                "state_object",
                "Signal record",
                "The signal record moves from absent to ready.",
                0,
                attributes={"object": "Signal record", "entity_id": "entity.3"},
                transition={"from_state": "absent", "to_state": "ready"},
            ),
        ]
    )
    stateful_graph["relations"].extend(
        [
            _relation(
                "relation.target_entity.0",
                "target_entity",
                "step.0",
                "entity.3",
                0,
            ),
            _relation(
                "relation.changes.0",
                "changes",
                "step.0",
                "state.0",
                0,
            ),
            _relation(
                "relation.state_of.0",
                "state_of",
                "state.0",
                "entity.3",
                0,
            ),
        ]
    )
    stateful = build_semantic_projection_plan(
        stateful_graph,
        project_slug="signal-view",
    )

    assert len(stateful.nodes) == len(baseline.nodes) + 2
    assert len(stateful.edges) == len(baseline.edges) + 3
    assert [row.key for row in stateful.diagram_plans] == [
        "first_path",
    ]
    assert len(stateful.workstream_plans) == len(baseline.workstream_plans)

    context_graph = copy.deepcopy(baseline_graph)
    context_graph["facts"].append(
        _fact(
            "external.0",
            "external_system",
            "Signal source",
            "The signal source is read-only.",
            0,
            attributes={"access_mode": "read_only"},
        )
    )
    context_graph["relations"].append(
        _relation(
            "relation.depends_on.0",
            "depends_on",
            "step.0",
            "external.0",
            0,
        )
    )
    context = build_semantic_projection_plan(
        context_graph,
        project_slug="signal-view",
    )
    assert [row.key for row in context.diagram_plans] == [
        "first_path",
        "context",
    ]
    assert len(context.workstream_plans) == len(baseline.workstream_plans)

    assert len(context.components) == 1
    assert len(context.workstream_plans) == 1


def test_verified_proposal_persists_and_consumes_one_projection_plan() -> None:
    packet = semantic_intent_packet()
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    authority = semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT)

    proposal = build_verified_semantic_proposal(
        authority=authority,
        observed_source={},
    )

    assert proposal["projection_plan"]["version"] == (
            "odylith.greenfield.semantic-projection-plan.v16"
    )
    assert "apply_semantic_input" not in proposal
    assert {
        "semantic_model",
        "project_intelligence",
        "artifact_derivation",
    }.isdisjoint(proposal)
    assert [row["title"] for row in proposal["backlog"]] == [
        "Deliver Claim Desk First Path",
    ]
    assert len(proposal["diagrams"]) == 2
    assert proposal["diagrams"][0]["semantic_relation_ids"] == [
        "owned-by.0",
        "target-entity.0",
        "produces.0",
        "output-of.0",
        "visible-to.0",
        "changes.0",
        "state-of.0",
    ]
    assert proposal["diagrams"][0]["projection_view_edge_ids"] == []
    plan = build_semantic_projection_plan(
        packet["semantic_intent"],
        project_slug="greenfield-project",
    )
    assert proposal["projection_plan"] == semantic_projection_plan_mapping(plan)
    release_plan = semantic_release_plan(
        plan=plan,
        release="0.0.1",
    )
    assert {
        key: proposal["release_plan"][key]
        for key in release_plan
    } == release_plan
    assert plan.human_action_owner_labels == ("Shift coordinator",)


def test_relationless_participant_never_becomes_a_human_action_owner() -> None:
    graph = copy.deepcopy(semantic_intent_packet()["semantic_intent"])
    extra_actor = copy.deepcopy(
        next(row for row in graph["facts"] if row["fact_id"] == "actor.0")
    )
    extra_actor.update(fact_id="actor.1", label="Observer", order=1)
    graph["facts"].append(extra_actor)

    plan = build_semantic_projection_plan(graph, project_slug="claim-desk")

    assert plan.human_action_owner_labels == ("Shift coordinator",)


def test_output_recipient_relation_survives_every_relevant_diagram_view() -> None:
    graph = copy.deepcopy(semantic_intent_packet()["semantic_intent"])
    graph["relations"].append(
        semantic_relation(
            "visible_to", "output.0", "actor.0", 0, PATH_EVIDENCE
        )
    )

    plan = build_semantic_projection_plan(graph, project_slug="claim-desk")
    diagram_relations = {
        diagram.key: set(diagram.relation_ids) for diagram in plan.diagram_plans
    }

    assert "relation.visible_to.0" in diagram_relations["first_path"]
    assert "relation.visible_to.0" in diagram_relations["context"]
    rendered = json.dumps(
        semantic_diagrams(plan=plan, backlog=_backlog(plan)), sort_keys=True
    )
    assert "visible to" in rendered


def test_verified_package_omits_fabricated_policy_and_repeated_review_copy() -> None:
    packet = semantic_intent_packet()
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    proposal = build_verified_semantic_proposal(
        authority=semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT),
        observed_source={},
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert proposal["security_compliance"] == {
        "release_boundary": (
            "Release proof: “Claim receipt” visible and Card changing from ready "
            "to claimed."
        ),
        "policy_boundaries": "prohibited: Never reassign a card automatically",
    }
    assert len(proposal["project_brief"]["blueprint_sections"]) == 5
    assert {
        "customization_prompts",
        "pre_coding_checkpoints",
        "host_independent_paths",
    }.isdisjoint(proposal["project_brief"])
    assert {
        "semantic_model",
        "project_intelligence",
        "artifact_derivation",
    }.isdisjoint(proposal)
    assert all(
        "project_intelligence_binding" not in row
        for key in ("backlog", "components", "diagrams")
        for row in proposal[key]
    )
    assert "project_intelligence_binding" not in proposal["release_plan"]
    assert all(len(row["risks"]) == 1 for row in proposal["components"])
    for retired in (
        "Blocked-path proof",
        "Security posture:",
        "Policy and privacy posture:",
        "Depends only on source-cited workflow facts",
        "product owner",
    ):
        assert retired not in rendered


def _backlog(plan: Any) -> list[dict[str, Any]]:
    return semantic_backlog_rows(
        plan=plan,
        problem="A typed workflow needs delivery.",
        customer="The product operator.",
        opportunity="Deliver only the accepted graph.",
        product_view="A graph-native product.",
        success_metrics=("Every output is visible.", "Every edge is retained."),
        proof_boundary="The accepted graph is delivered without semantic drift.",
    )


def _component_inputs(
    graph: dict[str, Any],
) -> tuple[Any, tuple[dict[str, Any], ...]]:
    plan = build_semantic_projection_plan(graph, project_slug="signal-view")
    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)
    proposal = {
        "projection_plan": semantic_projection_plan_mapping(plan),
        "components": list(plan.components),
        "backlog": backlog,
        "diagrams": diagrams,
        "risks": [],
    }
    inputs = semantic_component_authoring_inputs(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={
            "created": [
                {"idea_id": f"B-{index:03d}", "title": row["title"]}
                for index, row in enumerate(backlog, 1)
            ]
        },
        diagram_ids=tuple(
            f"D-{index:03d}" for index in range(1, len(diagrams) + 1)
        ),
    )
    return plan, inputs


def _supporting_boundary_graph() -> dict[str, Any]:
    graph = _stateless_graph()
    graph["facts"].extend(
        [
            _fact(
                "external.0",
                "external_system",
                "Signal Source",
                "The signal source is read-only.",
                0,
                attributes={"access_mode": "read-only"},
            ),
            _fact(
                "policy-boundary.0",
                "policy_boundary",
                "Read-only source",
                "The signal source stays read-only.",
                0,
                attributes={
                    "modality": "limited",
                    "behavior": "read",
                    "target": "signal source",
                },
            ),
            _fact(
                "policy-boundary.1",
                "policy_boundary",
                "Source mutation",
                "The product does not mutate the signal source.",
                0,
                attributes={
                    "modality": "prohibited",
                    "behavior": "mutate",
                    "target": "signal source",
                },
            ),
        ]
    )
    graph["relations"].extend(
        [
            _relation(
                "relation.depends_on.0",
                "depends_on",
                "step.0",
                "external.0",
                0,
            ),
            _relation(
                "relation.applies_to.0",
                "applies_to",
                "policy-boundary.0",
                "step.0",
                0,
            ),
            _relation(
                "relation.applies_to.1",
                "applies_to",
                "policy-boundary.1",
                "step.0",
                1,
            ),
        ]
    )
    return graph


def _stateless_graph() -> dict[str, Any]:
    facts = [
        _fact(
            "entity.0",
            "entity",
            "Signal view",
            "A signal view.",
            0,
            attributes={},
        ),
        _fact(
            "entity.1",
            "entity",
            "Signal chart",
            "A signal chart.",
            1,
            attributes={},
        ),
        _fact(
            "entity.2",
            "entity",
            "Signal summary",
            "A signal summary.",
            2,
            attributes={},
        ),
        _fact(
            "step.0",
            "workflow_step",
            "Present signal",
            "The product presents a chart and summary.",
            0,
            owner_kind="product",
            attributes={
                "action": "present",
                "action_phrase": "present a chart and summary",
            },
        ),
        _fact(
            "output.0",
            "visible_output",
            "Signal chart",
            "A signal chart is visible.",
            0,
            attributes={
                "entity_id": "entity.1",
            },
        ),
        _fact(
            "output.1",
            "visible_output",
            "Signal summary",
            "A signal summary is visible.",
            1,
            attributes={
                "entity_id": "entity.2",
            },
        ),
    ]
    relations = [
        _relation("relation.produces.0", "produces", "step.0", "output.0", 0),
        _relation("relation.produces.1", "produces", "step.0", "output.1", 1),
        _relation("relation.output_of.0", "output_of", "output.0", "entity.1", 0),
        _relation("relation.output_of.1", "output_of", "output.1", "entity.2", 1),
    ]
    return {
        "presentation": {
            "title": "Signal View",
            "status": "working_assumption",
            "source_refs": [],
        },
        "facts": facts,
        "relations": relations,
        "narratives": [],
    }


def _two_state_graph() -> dict[str, Any]:
    facts = [
        _fact(
            "entity.0",
            "entity",
            "Intake record",
            "The intake record.",
            0,
            attributes={},
        ),
        _fact(
            "entity.1",
            "entity",
            "Intake receipt",
            "An intake receipt.",
            1,
            attributes={},
        ),
        _fact(
            "entity.2",
            "entity",
            "Decision record",
            "The decision record.",
            2,
            attributes={},
        ),
        _fact(
            "entity.3",
            "entity",
            "Decision notice",
            "A decision notice.",
            3,
            attributes={},
        ),
        _fact(
            "step.0",
            "workflow_step",
            "Receive intake",
            "The product receives the intake.",
            0,
            owner_kind="product",
            attributes={"action": "receive", "action_phrase": "receive the intake"},
        ),
        _fact(
            "step.1",
            "workflow_step",
            "Record decision",
            "The product records the decision.",
            1,
            owner_kind="product",
            attributes={"action": "record", "action_phrase": "record the decision"},
        ),
        _fact(
            "state.0",
            "state_object",
            "Intake record",
            "The intake record moves from absent to received.",
            0,
            attributes={"object": "Intake record", "entity_id": "entity.0"},
            transition={"from_state": "absent", "to_state": "received"},
        ),
        _fact(
            "state.1",
            "state_object",
            "Decision record",
            "The decision record moves from pending to approved.",
            1,
            attributes={"object": "Decision record", "entity_id": "entity.2"},
            transition={"from_state": "pending", "to_state": "approved"},
        ),
        _fact(
            "output.0",
            "visible_output",
            "Intake receipt",
            "An intake receipt is visible.",
            0,
            attributes={
                "entity_id": "entity.1",
            },
        ),
        _fact(
            "output.1",
            "visible_output",
            "Decision notice",
            "A decision notice is visible.",
            1,
            attributes={
                "entity_id": "entity.3",
            },
        ),
    ]
    relations = [
        _relation("relation.target_entity.0", "target_entity", "step.0", "entity.0", 0),
        _relation("relation.target_entity.1", "target_entity", "step.1", "entity.2", 1),
        _relation("relation.produces.0", "produces", "step.0", "output.0", 0),
        _relation("relation.produces.1", "produces", "step.1", "output.1", 1),
        _relation("relation.output_of.0", "output_of", "output.0", "entity.1", 0),
        _relation("relation.output_of.1", "output_of", "output.1", "entity.3", 1),
        _relation("relation.changes.0", "changes", "step.0", "state.0", 0),
        _relation("relation.changes.1", "changes", "step.1", "state.1", 1),
        _relation("relation.state_of.0", "state_of", "state.0", "entity.0", 0),
        _relation("relation.state_of.1", "state_of", "state.1", "entity.2", 1),
    ]
    return {
        "presentation": {
            "title": "Review Flow",
            "status": "working_assumption",
            "source_refs": [],
        },
        "facts": facts,
        "relations": relations,
        "narratives": [],
    }


def _fact(
    fact_id: str,
    kind: str,
    label: str,
    statement: str,
    order: int,
    *,
    owner_kind: str = "none",
    custody: str = "source_fact",
    attributes: dict[str, str] | None = None,
    transition: dict[str, str] | None = None,
) -> dict[str, Any]:
    result = {
        "fact_id": fact_id,
        "kind": kind,
        "label": label,
        "statement": statement,
        "order": order,
        "owner_kind": owner_kind,
        "custody": custody,
        "attributes": [
            {"name": name, "value": value}
            for name, value in (attributes or {}).items()
        ],
        "source_refs": [],
    }
    if kind == "state_object":
        result["transition"] = transition
    return result


def _relation(
    relation_id: str,
    kind: str,
    subject_id: str,
    object_id: str,
    order: int,
    *,
    custody: str = "source_fact",
) -> dict[str, Any]:
    return {
        "relation_id": relation_id,
        "kind": kind,
        "subject_id": subject_id,
        "object_id": object_id,
        "order": order,
        "custody": custody,
        "source_refs": [],
    }
