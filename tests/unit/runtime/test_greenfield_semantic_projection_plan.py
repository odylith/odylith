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
    SEMANTIC_PROMPT,
    semantic_intent_packet,
    stateless_semantic_intent_packet as _stateless_packet,
)


def test_actorless_stateless_one_system_two_output_plan_stays_single_slice() -> None:
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
        ("product", ("signal-service",)),
    ]
    assert [row.title for row in plan.diagram_plans] == ["First Path"]
    assert len(backlog) == 1
    assert backlog[0]["component_focus"] == ["signal-service"]
    assert len(diagrams) == 1
    assert diagrams[0]["semantic_relation_ids"] == [
        "relation.produces.0",
        "relation.produces.1",
    ]
    assert diagrams[0]["projection_view_edge_ids"] == []
    assert diagrams[0]["mermaid_source"].count(" -->|") == 2
    assert "-.->|then|" not in diagrams[0]["mermaid_source"]
    assert len(proposal["components"]) == 1
    assert len(proposal["backlog"]) == 1
    assert len(proposal["diagrams"]) == 1
    contract = proposal["components"][0]["component_contract"]
    assert contract["schema_version"] == (
        "odylith.greenfield.semantic-component-contract.v3"
    )
    assert contract["component_role"] == "result_implementing"
    assert contract["workflow_fact_ids"] == ["step.0"]
    assert contract["workflow_labels"] == ["Present signal"]
    assert contract["state_objects"] == []
    assert contract["visible_outputs"] == ["Signal chart", "Signal summary"]
    assert {"owned_state", "produced_outputs", "states_or_transitions"}.isdisjoint(
        contract
    )
    assert proposal["components"][0]["validation"] == [
        "Prove that both accepted outputs are visible without durable state."
    ]
    assert all(
        "replay" not in row.casefold()
        for row in proposal["components"][0]["validation"]
    )
    semantic_model = proposal["semantic_model"]
    assert semantic_model["schema_version"] == "odylith.greenfield.semantic_model.v4"
    first_path = semantic_model["first_path_contract"]
    assert first_path["workflow_fact_ids"] == ["step.0"]
    assert first_path["visible_outputs"] == ["Signal chart", "Signal summary"]
    assert {"state_objects", "persistence", "recovery_path"}.isdisjoint(first_path)
    assert all(
        "state" not in row["required_evidence"].casefold()
        and "replay" not in row["required_evidence"].casefold()
        for row in semantic_model["proof_obligations"][:2]
    )
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
        "Prove that both accepted outputs are visible without durable state.",
    )


def test_component_interfaces_render_typed_step_labels_not_raw_source_copy() -> None:
    graph = _stateless_graph()
    raw_envelope = '{"product_intent":{"first_path":"present both outputs"}}'
    workflow = next(row for row in graph["facts"] if row["kind"] == "workflow_step")
    workflow["statement"] = raw_envelope

    plan = build_semantic_projection_plan(graph, project_slug="signal-view")
    interfaces = plan.components[0]["interfaces"]

    assert raw_envelope not in " ".join(interfaces)
    assert interfaces.count("Implements the “Present signal” workflow step.") == 1


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
    graph["facts"].append(
        _fact(
            "state.0",
            "state_object",
            "Signal record",
            "The signal record is durable.",
            0,
            attributes={"object": "signal record"},
        )
    )
    graph["relations"].extend(
        [
            _relation("relation.changes.0", "changes", "step.0", "state.0", 0),
            _relation("relation.implements.3", "implements", "system.0", "state.0", 3),
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


def test_supporting_dependency_boundary_needs_no_invented_result_ownership() -> None:
    graph = _supporting_boundary_graph()
    plan, inputs = _component_inputs(graph)
    supporting = next(
        row for row in inputs if row["semantic_fact_id"] == "system.1"
    )

    assert plan.components[1]["release_scope"] == "first_path_required"
    assert plan.components[1]["component_role"] == "boundary_supporting"
    assert plan.components[1]["semantic_implements"] == []
    assert plan.components[1]["result_summary"] == ""
    assert plan.components[1]["interfaces"] == [
        "Signal Service depends on Signal Source Reader",
        "Signal Source Reader depends on Signal Source",
        "Signal Source Reader is constrained by Read-only source",
        "Signal Source Reader excludes Source mutation",
    ]
    assert supporting["component_contract"]["state_objects"] == ()
    assert supporting["component_contract"]["visible_outputs"] == ()
    assert supporting["component_contract"]["component_role"] == (
        "boundary_supporting"
    )
    assert supporting["interfaces"] == (
        "Signal Service depends on Signal Source Reader",
        "Signal Source Reader depends on Signal Source",
        "Signal Source Reader is constrained by Read-only source",
        "Signal Source Reader excludes Source mutation",
    )
    visible_copy = " ".join(
        (
            *supporting["interfaces"],
            *supporting["component_contract"]["local_proof"],
        )
    )
    assert "reviewable first-path result" not in visible_copy.casefold()
    assert "produces" not in visible_copy.casefold()
    assert "blocked-path" not in visible_copy.casefold()

    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)
    supporting_workstream = next(
        row
        for row in backlog
        if row["component_focus"] == ["signal-source-reader"]
    )
    assert {
        row["opportunity"] for row in backlog
    } == {"Deliver only the accepted graph."}
    assert supporting_workstream["recommended_first_slice"].endswith(
        "Read the source without mutating it."
    )
    supporting_descriptions = [
        component["description"]
        for diagram in diagrams
        for component in diagram["components"]
        if component["semantic_fact_id"] == "system.1"
    ]
    cross_surface_copy = " ".join(
        (
            *supporting_workstream["interfaces"],
            *supporting_workstream["validation"],
            *supporting_descriptions,
        )
    ).casefold()
    assert "reviewable first-path result" not in cross_surface_copy
    assert "produces" not in cross_surface_copy
    assert "blocked-path" not in cross_surface_copy


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


def test_release_membership_does_not_fabricate_result_ownership() -> None:
    graph = _supporting_boundary_graph()
    plan, _ = _component_inputs(graph)
    supporting = plan.components[1]

    assert supporting["release_scope"] == "first_path_required"
    assert supporting["component_role"] == "boundary_supporting"
    assert supporting["semantic_implements"] == []


def test_resultless_supporting_component_without_first_path_consumer_is_orphaned() -> None:
    graph = _supporting_boundary_graph()
    graph["relations"] = [
        row
        for row in graph["relations"]
        if not (
            row["kind"] == "depends_on"
            and row["subject_id"] == "system.0"
            and row["object_id"] == "system.1"
        )
    ]

    with pytest.raises(ValueError, match="supporting.*is orphaned"):
        _component_inputs(graph)


def test_components_with_identical_typed_roles_are_rejected() -> None:
    graph = _supporting_boundary_graph()
    graph["facts"].append(
        _supporting_system(
            "system.2",
            "Signal Source Reader Mirror",
            2,
        )
    )
    graph["relations"].extend(
        [
            _relation(
                "relation.depends_on.2",
                "depends_on",
                "system.0",
                "system.2",
                2,
            ),
            _relation(
                "relation.depends_on.3",
                "depends_on",
                "system.2",
                "external.0",
                3,
            ),
            _relation(
                "relation.constrained_by.1",
                "constrained_by",
                "system.2",
                "constraint.0",
                1,
            ),
            _relation(
                "relation.excludes.1",
                "excludes",
                "system.2",
                "non-goal.0",
                1,
            ),
        ]
    )

    with pytest.raises(ValueError, match="components are not differentiated"):
        _component_inputs(graph)


def test_two_state_two_output_two_system_plan_preserves_every_edge() -> None:
    graph = _two_state_graph()
    plan = build_semantic_projection_plan(graph, project_slug="review-flow")
    backlog = _backlog(plan)
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)

    assert plan.state_fact_ids == ("state.0", "state.1")
    assert plan.visible_output_fact_ids == ("output.0", "output.1")
    assert len(plan.components) == 2
    assert [row.kind for row in plan.workstream_plans] == [
        "product",
        "component",
        "component",
    ]
    assert len(backlog) == 3
    assert [row["component_focus"] for row in backlog] == [
        ["intake-service", "decision-service"],
        ["intake-service"],
        ["decision-service"],
    ]
    assert [row.key for row in plan.diagram_plans] == [
        "first_path",
        "state_evidence",
        "component_boundaries",
    ]
    assert len(diagrams) == 3
    first_path = diagrams[0]
    assert first_path["semantic_relation_ids"] == [
        "relation.produces.0",
        "relation.produces.1",
        "relation.changes.0",
        "relation.changes.1",
    ]
    assert first_path["projection_view_edge_ids"] == ["workflow-sequence-0"]
    assert first_path["mermaid_source"].count(" -->|") == 4
    assert first_path["mermaid_source"].count(" -.->|then|") == 1
    assert "system.0" not in first_path["semantic_fact_ids"]
    assert "system.1" not in first_path["semantic_fact_ids"]
    contracts = [row["component_contract"] for row in plan.components]
    assert [row["workflow_fact_ids"] for row in contracts] == [
        ["step.0"],
        ["step.1"],
    ]
    assert [row["state_objects"] for row in contracts] == [
        ["Intake record"],
        ["Decision record"],
    ]
    assert [row["visible_outputs"] for row in contracts] == [
        ["Intake receipt"],
        ["Decision notice"],
    ]
    assert all(
        {"owned_state", "produced_outputs", "states_or_transitions"}.isdisjoint(row)
        for row in contracts
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
            "constraint.0",
            "operational_constraint",
            "Read-only input",
            "Input remains read-only.",
            0,
        )
    )
    constrained_graph["relations"].append(
        _relation(
            "relation.constrained_by.0",
            "constrained_by",
            "identity.0",
            "constraint.0",
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
    stateful_graph["facts"].append(
        _fact(
            "state.0",
            "state_object",
            "Signal record",
            "The signal record moves from absent to ready.",
            0,
            attributes={"object": "signal record"},
            transition={"from_state": "absent", "to_state": "ready"},
        )
    )
    stateful_graph["relations"].extend(
        [
            _relation(
                "relation.changes.0",
                "changes",
                "step.0",
                "state.0",
                0,
            ),
            _relation(
                "relation.implements.3",
                "implements",
                "system.0",
                "state.0",
                3,
            ),
        ]
    )
    stateful = build_semantic_projection_plan(
        stateful_graph,
        project_slug="signal-view",
    )

    assert len(stateful.nodes) == len(baseline.nodes) + 1
    assert len(stateful.edges) == len(baseline.edges) + 2
    assert [row.key for row in stateful.diagram_plans] == [
        "first_path",
        "state_evidence",
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
            "identity.0",
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

    cross_boundary_graph = copy.deepcopy(context_graph)
    cross_boundary_graph["relations"][-1]["subject_id"] = "system.0"
    cross_boundary = build_semantic_projection_plan(
        cross_boundary_graph,
        project_slug="signal-view",
    )
    assert len(cross_boundary.nodes) == len(context.nodes)
    assert len(cross_boundary.edges) == len(context.edges)
    assert [row.key for row in cross_boundary.diagram_plans] == [
        "first_path",
        "context",
        "component_boundaries",
    ]


def test_verified_proposal_persists_and_consumes_one_projection_plan() -> None:
    packet = semantic_intent_packet()
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    authority = semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT)

    proposal = build_verified_semantic_proposal(
        authority=authority,
        observed_source={},
    )

    assert proposal["projection_plan"]["version"] == (
        "odylith.greenfield.semantic-projection-plan.v3"
    )
    assert "apply_semantic_input" not in proposal
    assert proposal["semantic_model"]["first_path_contract"]["state_objects"] == [
        "Card"
    ]
    assert proposal["semantic_model"]["first_path_contract"]["visible_outputs"] == [
        "Claim receipt"
    ]
    assert [row["title"] for row in proposal["backlog"]] == [
        "Deliver Claim Desk First Path",
        "Implement Card Claim Service",
        "Implement Claim Receipt Delivery",
    ]
    assert len(proposal["diagrams"]) == 4
    assert proposal["diagrams"][0]["semantic_relation_ids"] == [
        "relation.owned_by.0",
        "relation.owned_by.1",
        "relation.produces.0",
        "relation.changes.0",
    ]
    assert proposal["diagrams"][0]["projection_view_edge_ids"] == [
        "workflow-sequence-0"
    ]
    plan = build_semantic_projection_plan(
        packet["semantic_intent"],
        project_slug="claim-desk",
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


def test_verified_package_omits_fabricated_policy_and_repeated_review_copy() -> None:
    packet = semantic_intent_packet()
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    proposal = build_verified_semantic_proposal(
        authority=semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT),
        observed_source={},
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert proposal["security_compliance"] == {
        "release_boundary": "A shift coordinator can claim one ready card and receive a claim receipt.",
        "operating_constraints": "Read the local duty roster.",
        "excluded_scope": "Never reassign a card automatically.",
    }
    assert len(proposal["project_brief"]["blueprint_sections"]) == 5
    assert {
        "customization_prompts",
        "pre_coding_checkpoints",
        "host_independent_paths",
    }.isdisjoint(proposal["project_brief"])
    assert {
        "artifacts",
        "execution_memory",
        "metrics",
        "change_model",
        "invalidation_rules",
        "conflict_model",
        "transfer_priors",
    }.isdisjoint(proposal["project_intelligence"])
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
                "constraint.0",
                "operational_constraint",
                "Read-only source",
                "The signal source stays read-only.",
                0,
            ),
            _fact(
                "non-goal.0",
                "non_goal",
                "Source mutation",
                "The product does not mutate the signal source.",
                0,
            ),
            _supporting_system("system.1", "Signal Source Reader", 1),
        ]
    )
    graph["relations"].extend(
        [
            _relation(
                "relation.depends_on.0",
                "depends_on",
                "system.0",
                "system.1",
                0,
            ),
            _relation(
                "relation.depends_on.1",
                "depends_on",
                "system.1",
                "external.0",
                1,
            ),
            _relation(
                "relation.constrained_by.0",
                "constrained_by",
                "system.1",
                "constraint.0",
                0,
            ),
            _relation(
                "relation.excludes.0",
                "excludes",
                "system.1",
                "non-goal.0",
                0,
            ),
        ]
    )
    return graph


def _supporting_system(
    fact_id: str,
    label: str,
    order: int,
) -> dict[str, Any]:
    return _fact(
        fact_id,
        "internal_system",
        label,
        f"{label} owns the typed source boundary.",
        order,
        custody="bounded_interpretation",
        attributes={
            "responsibility": "Read the source without mutating it.",
            "component_kind": "adapter",
            "boundary": "Own read-only source access.",
            "outside_boundary": "Signal presentation and source mutation.",
            "proof": "Prove that source access remains read-only.",
            "risk": "Source access could mutate upstream truth.",
            "release_scope": "first_path_required",
        },
    )


def _stateless_graph() -> dict[str, Any]:
    facts = [
        _fact(
            "identity.0",
            "identity",
            "Signal View",
            "Signal View presents two visible outputs without durable state.",
            0,
            attributes={"source_title": "signal view"},
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
        ),
        _fact(
            "output.1",
            "visible_output",
            "Signal summary",
            "A signal summary is visible.",
            1,
        ),
        _system(
            "system.0",
            "Signal Service",
            "Own signal presentation.",
            0,
        ),
    ]
    relations = [
        _relation("relation.produces.0", "produces", "step.0", "output.0", 0),
        _relation("relation.produces.1", "produces", "step.0", "output.1", 1),
        _relation("relation.implements.0", "implements", "system.0", "step.0", 0),
        _relation("relation.implements.1", "implements", "system.0", "output.0", 1),
        _relation("relation.implements.2", "implements", "system.0", "output.1", 2),
    ]
    return {"facts": facts, "relations": relations, "narratives": []}


def _two_state_graph() -> dict[str, Any]:
    facts = [
        _fact(
            "identity.0",
            "identity",
            "Review Flow",
            "Review Flow receives an intake and records a decision.",
            0,
            attributes={"source_title": "review flow"},
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
            attributes={"object": "intake record"},
            transition={"from_state": "absent", "to_state": "received"},
        ),
        _fact(
            "state.1",
            "state_object",
            "Decision record",
            "The decision record moves from pending to approved.",
            1,
            attributes={"object": "decision record"},
            transition={"from_state": "pending", "to_state": "approved"},
        ),
        _fact("output.0", "visible_output", "Intake receipt", "An intake receipt is visible.", 0),
        _fact("output.1", "visible_output", "Decision notice", "A decision notice is visible.", 1),
        _system("system.0", "Intake Service", "Own intake receipt and state.", 0),
        _system("system.1", "Decision Service", "Own decision notice and state.", 1),
    ]
    relations = [
        _relation("relation.produces.0", "produces", "step.0", "output.0", 0),
        _relation("relation.produces.1", "produces", "step.1", "output.1", 1),
        _relation("relation.changes.0", "changes", "step.0", "state.0", 0),
        _relation("relation.changes.1", "changes", "step.1", "state.1", 1),
        _relation("relation.depends_on.0", "depends_on", "system.1", "system.0", 0),
        _relation("relation.implements.0", "implements", "system.0", "step.0", 0),
        _relation("relation.implements.1", "implements", "system.0", "state.0", 1),
        _relation("relation.implements.2", "implements", "system.0", "output.0", 2),
        _relation("relation.implements.3", "implements", "system.1", "step.1", 3),
        _relation("relation.implements.4", "implements", "system.1", "state.1", 4),
        _relation("relation.implements.5", "implements", "system.1", "output.1", 5),
    ]
    return {"facts": facts, "relations": relations, "narratives": []}


def _system(
    fact_id: str,
    label: str,
    responsibility: str,
    order: int,
) -> dict[str, Any]:
    return _fact(
        fact_id,
        "internal_system",
        label,
        responsibility,
        order,
        custody="bounded_interpretation",
        attributes={
            "responsibility": responsibility,
            "component_kind": "service",
            "boundary": responsibility,
            "outside_boundary": "Behavior outside the typed graph.",
            "proof": f"Prove {responsibility}",
            "risk": f"Failure can violate: {responsibility}",
            "release_scope": "first_path_required",
        },
    )


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
