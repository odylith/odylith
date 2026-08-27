"""Cross-surface copy contracts for typed Greenfield projections."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_backlog_projection import (
    semantic_policy_boundary_summaries,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_delivery import (
    semantic_first_release_workstream_ids,
    semantic_next_steps,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_memory import (
    semantic_acceptance_event_preview,
    semantic_project_dashboard_payload,
    semantic_project_brief_markdown,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_proposal import (
    build_verified_semantic_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    semantic_source_meaning_sha256,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


def test_gfhi_001_policy_polarity_reaches_every_consumer_projection() -> None:
    proposal = _gfhi_001_like_proposal()
    handoff, dashboard = _handoff_and_dashboard(proposal)
    expected = "prohibited: Automatically reassign a card"
    consumer_copy = json.dumps(
        {
            "backlog": proposal["backlog"],
            "project_brief": proposal["project_brief"],
            "security_compliance": proposal["security_compliance"],
            "handoff": handoff,
            "dashboard": dashboard,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    assert expected in proposal["backlog"][0]["problem"]
    assert expected in proposal["backlog"][0]["product_view"]
    assert proposal["security_compliance"]["policy_boundaries"] == expected
    policy_card = next(
        row
        for row in dashboard["product_story"]["release_contract"]
        if row["semantic_slot"] == "policy_boundaries"
    )
    assert policy_card["body"] == expected
    assert dashboard["jobs"][0]["body"] == (
        proposal["backlog"][0]["recommended_first_slice"]
    )
    assert "uphold Automatically reassign a card" not in consumer_copy
    assert "Boundary: Automatically reassign a card" not in consumer_copy


def test_policy_renderer_preserves_each_typed_modality() -> None:
    assert semantic_policy_boundary_summaries(
        (
            {"modalities": ("prohibited",), "statement": "Export records."},
            {"modalities": ("required",), "statement": "Retain source custody."},
            {"modalities": ("limited",), "statement": "Share summary fields."},
        )
    ) == (
        "prohibited: Export records",
        "required: Retain source custody",
        "limited: Share summary fields",
    )


def test_release_proof_and_single_workstream_handoff_do_not_repeat_actions() -> None:
    proposal = _gfhi_001_like_proposal()
    handoff, dashboard = _handoff_and_dashboard(proposal)
    proof = proposal["intent"]["proof_boundary"]

    assert proof in proposal["project_brief"]["project_outcome"]
    assert "Release proof: Release proof:" not in json.dumps(
        proposal,
        ensure_ascii=False,
    )
    assert handoff["project_workstream_id"] == handoff["start_workstream_id"] == "B-001"
    assert handoff["project_first_prompt"].count("`B-001`") == 1
    assert "then open" not in handoff["project_first_prompt"].casefold()
    assert dashboard["recommendation"] == handoff["project_first_prompt"]
    assert dashboard["recommendation"].count("`B-001`") == 1


def test_terminal_punctuation_is_removed_before_typed_list_joining() -> None:
    packet = semantic_intent_packet()
    graph = copy.deepcopy(packet["source_meaning_graph"])
    graph["workflow"][0]["action"] = "claim one ready card."
    first_entity = graph["entities"][1]
    first_entity["label"] = "Claim receipt."
    second_entity = copy.deepcopy(first_entity)
    second_entity["label"] = "Audit notice."
    graph["entities"].append(second_entity)
    first_output = next(
        effect
        for effect in graph["workflow"][0]["entity_effects"]
        if effect["kind"] == "visible_result"
    )
    second_output = copy.deepcopy(first_output)
    second_output["entity_index"] = len(graph["entities"]) - 1
    graph["workflow"][0]["entity_effects"].append(second_output)
    proposal = _proposal_from_graph(graph)
    visible_section = next(
        row
        for row in proposal["project_brief"]["blueprint_sections"]
        if row["section"] == "State and visible outputs"
    )
    visible_copy = json.dumps(
        {
            "brief": visible_section,
            "backlog": proposal["backlog"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    assert "Claim receipt and Audit notice" in visible_copy
    assert ".," not in visible_copy
    assert ". and" not in visible_copy


@pytest.mark.parametrize(
    "action",
    (
        "Select one ready card.",
        "Selects one ready card.",
        "The coordinator selects one ready card.",
        "Show the claim receipt!",
    ),
)
def test_action_forms_remain_standalone_typed_clauses(action: str) -> None:
    proposal = _proposal_for_actions((action,), include_policy=False)
    expected_path = f"Step 1 — {action.rstrip(' .!?')}."
    problem = proposal["backlog"][0]["problem"]
    product_view = proposal["backlog"][0]["product_view"]

    assert f"Required path: {expected_path}" in problem
    assert f"First path: {expected_path}" in product_view
    assert "must deliver" not in problem
    assert "delivers " not in product_view
    assert " and exposes " not in product_view


def test_multiple_actions_preserve_order_as_independent_clauses() -> None:
    proposal = _proposal_for_actions(
        (
            "Select one ready card.",
            "The coordinator places it on the reviewed shelf.",
        ),
        include_policy=False,
    )
    expected = (
        "Step 1 — Select one ready card. "
        "Step 2 — The coordinator places it on the reviewed shelf."
    )

    assert f"Required path: {expected}" in proposal["backlog"][0]["problem"]
    assert f"First path: {expected}" in proposal["backlog"][0]["product_view"]


def test_output_producing_action_and_output_use_distinct_labeled_fields() -> None:
    proposal = _proposal_for_actions(
        ("Show the blue review badge.",),
        include_policy=False,
        output_label="Blue review badge",
    )
    problem = proposal["backlog"][0]["problem"]
    product_view = proposal["backlog"][0]["product_view"]

    assert "Visible results:" not in problem
    assert "State:" not in problem
    assert "Dependencies:" not in problem
    assert product_view.startswith(
        "First path: Step 1 — Show the blue review badge. "
        "Visible results: Blue review badge."
    )
    assert "Participants:" not in product_view
    assert "exposes" not in product_view


def test_policy_free_projects_still_use_structured_copy_and_product_boundary() -> None:
    graph = _graph_for_actions(("Select one ready card.",), include_policy=False)
    graph["product_boundaries"] = [
        {
            "statement": "repo-local",
            "source_refs": copy.deepcopy(graph["presentation"]["source_refs"]),
        }
    ]
    proposal = _proposal_from_graph(graph)
    problem = proposal["backlog"][0]["problem"]
    product_view = proposal["backlog"][0]["product_view"]

    assert problem == (
        "Claim Desk needs a governed first path. Participants: Shift coordinator. "
        "Required path: Step 1 — Select one ready card. Boundaries: repo-local."
    )
    assert product_view.endswith("Boundaries: repo-local.")
    assert proposal["schema_version"] == "odylith.greenfield.proposal.v10"
    assert proposal["intent"]["presentation"] == graph["presentation"]
    assert proposal["intent"]["owned_capabilities"] == [
        "Claim Desk First Path: Deliver the sealed first-path workflow: Select one ready card."
    ]
    assert {
        "semantic_model",
        "project_intelligence",
        "artifact_derivation",
    }.isdisjoint(proposal)
    assert "project_intelligence_binding" not in json.dumps(proposal, sort_keys=True)


def test_working_title_is_disclosed_but_does_not_control_durable_identity() -> None:
    graph = _graph_for_actions(("Select one ready card.",), include_policy=False)
    graph["presentation"] = {
        "title": "Claim Desk",
        "status": "working_assumption",
        "source_refs": [],
    }
    first = _proposal_from_graph(graph, observed_source={"repo_name": "consumer"})
    renamed_graph = copy.deepcopy(graph)
    renamed_graph["presentation"]["title"] = "Ready Card Review"
    second = _proposal_from_graph(
        renamed_graph,
        observed_source={"repo_name": "consumer"},
    )

    assert [row["component_id"] for row in first["components"]] == [
        row["component_id"] for row in second["components"]
    ] == ["consumer-first-path"]
    assert [row["intended_path"] for row in first["components"]] == [
        row["intended_path"] for row in second["components"]
    ]
    assert [row["slug"] for row in first["projection_plan"]["diagrams"]] == [
        row["slug"] for row in second["projection_plan"]["diagrams"]
    ]
    assert first["components"][0]["label"] != second["components"][0]["label"]

    created = [
        {**row, "idea_id": f"B-{index:03d}"}
        for index, row in enumerate(first["backlog"], 1)
    ]
    component_items = [
        {"component_id": row["component_id"]}
        for row in first["components"]
    ]
    diagram_ids = [
        f"D-{index:03d}"
        for index, _ in enumerate(first["diagrams"], 1)
    ]
    brief = semantic_project_brief_markdown(
        proposal=first,
        backlog_items=created,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector="0.0.1",
        release_id="release-consumer-0-0-1",
    )
    handoff, dashboard = _handoff_and_dashboard(first)
    event = semantic_acceptance_event_preview(
        proposal=first,
        backlog_items=created,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector="0.0.1",
        release_id="release-consumer-0-0-1",
    )

    assert "Working title (assumption): Claim Desk" in brief
    assert dashboard["eyebrow"].startswith("Working title (assumption) ·")
    assert "under the working title Claim Desk" in event["summary"]
    assert handoff["project_workstream_id"] == "B-001"


def test_source_declared_title_is_disclosed_without_assumption_copy() -> None:
    graph = _graph_for_actions(("Select one ready card.",), include_policy=False)
    graph["presentation"]["status"] = "source_declared"
    proposal = _proposal_from_graph(graph, observed_source={"repo_name": "consumer"})
    created = [
        {**row, "idea_id": f"B-{index:03d}"}
        for index, row in enumerate(proposal["backlog"], 1)
    ]
    component_items = [
        {"component_id": row["component_id"]}
        for row in proposal["components"]
    ]
    diagram_ids = [
        f"D-{index:03d}"
        for index, _ in enumerate(proposal["diagrams"], 1)
    ]

    brief = semantic_project_brief_markdown(
        proposal=proposal,
        backlog_items=created,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector="0.0.1",
        release_id="release-consumer-0-0-1",
    )
    _, dashboard = _handoff_and_dashboard(proposal)

    assert "Source-declared title: Claim Desk" in brief
    assert dashboard["eyebrow"].startswith("Source-declared title ·")
    assert "working title" not in brief.casefold()


def _gfhi_001_like_proposal() -> dict[str, Any]:
    packet = semantic_intent_packet()
    graph = copy.deepcopy(packet["source_meaning_graph"])
    graph["policy_boundaries"][0]["modalities"] = ["prohibited"]
    graph["policy_boundaries"][0]["statement"] = "Automatically reassign a card."
    return _proposal_from_graph(graph)


def _proposal_for_actions(
    actions: tuple[str, ...],
    *,
    include_policy: bool,
    output_label: str = "Claim receipt",
) -> dict[str, Any]:
    return _proposal_from_graph(
        _graph_for_actions(
            actions,
            include_policy=include_policy,
            output_label=output_label,
        )
    )


def _graph_for_actions(
    actions: tuple[str, ...],
    *,
    include_policy: bool,
    output_label: str = "Claim receipt",
) -> dict[str, Any]:
    packet = semantic_intent_packet()
    graph = copy.deepcopy(packet["source_meaning_graph"])
    final_step = graph["workflow"][0]
    steps = []
    for index, action in enumerate(actions):
        step = copy.deepcopy(final_step)
        step["action"] = action
        if index < len(actions) - 1:
            step["entity_effects"] = [
                effect
                for effect in step["entity_effects"]
                if effect["kind"] not in {"changed", "visible_result"}
            ]
        steps.append(step)
    graph["workflow"] = steps
    graph["entities"][1]["label"] = output_label
    if not include_policy:
        graph["policy_boundaries"] = []
    return graph


def _proposal_from_graph(
    graph: dict[str, Any],
    *,
    observed_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline = semantic_intent_packet()
    author_run = copy.deepcopy(baseline["author_run"])
    author_run["graph_sha256"] = semantic_source_meaning_sha256(graph)
    packet = build_semantic_intent_packet(
        graph,
        prompt=SEMANTIC_PROMPT,
        author_run=author_run,
    )
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    return build_verified_semantic_proposal(
        authority=semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT),
        observed_source=observed_source or {},
        release_selector="0.0.1",
    )


def _handoff_and_dashboard(
    proposal: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    created = [
        {**row, "idea_id": f"B-{index:03d}"}
        for index, row in enumerate(proposal["backlog"], 1)
    ]
    release_ids = semantic_first_release_workstream_ids(
        proposal=proposal,
        created_backlog=created,
    )
    handoff = semantic_next_steps(
        proposal=proposal,
        backlog_result={"created": created},
        first_release_workstreams=release_ids,
        release_selector="0.0.1",
    )
    dashboard = semantic_project_dashboard_payload(
        proposal=proposal,
        accepted_project={
            "accepted_at": "prewrite",
            "created": {"workstreams": created},
        },
        source_launch=handoff,
    )
    return handoff, dashboard
