from __future__ import annotations

import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_delivery import (
    semantic_first_release_workstream_ids,
    semantic_next_steps,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_memory import (
    semantic_acceptance_event_preview,
    semantic_accepted_project_payload,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_proposal import (
    build_verified_semantic_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    DEPENDENCY_EVIDENCE,
    SEMANTIC_PROMPT,
    semantic_intent_packet,
    stateless_semantic_intent_packet as _stateless_packet,
)


def test_release_membership_and_start_owner_follow_plan_local_policy() -> None:
    proposal = _proposal(_release_scope_packet(), prompt=SEMANTIC_PROMPT)

    assert [row["label"] for row in proposal["components"]] == [
        "Claim Desk First Path",
    ]
    assert [row["release_scope"] for row in proposal["components"]] == [
        "first_path_required",
    ]
    assert [row["component_role"] for row in proposal["components"]] == [
        "result_implementing",
    ]
    assert proposal["release_plan"]["release_component_policy_ids"] == [
        "implementation-policy.0",
    ]
    assert proposal["release_plan"]["result_component_policy_ids"] == [
        "implementation-policy.0",
    ]
    assert proposal["release_plan"]["supporting_component_policy_ids"] == []
    assert proposal["release_plan"]["target_workstream_titles"] == [
        "Deliver Claim Desk First Path",
    ]
    assert proposal["release_plan"]["start_workstream_title"] == (
        "Deliver Claim Desk First Path"
    )

    created = [
        {"idea_id": f"B-{index:03d}", "title": row["title"]}
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

    assert release_ids == ["B-001"]
    assert handoff["project_workstream_id"] == "B-001"
    assert handoff["start_workstream_id"] == "B-001"
    assert handoff["start_workstream_title"] == "Deliver Claim Desk First Path"
    first_path_diagram = next(
        row for row in proposal["diagrams"]
        if row["slug"].endswith("first-path")
    )
    first_path_plan = next(
        row for row in proposal["projection_plan"]["diagrams"]
        if row["key"] == "first_path"
    )
    assert first_path_diagram["semantic_fact_ids"] == first_path_plan["fact_ids"]
    assert first_path_diagram["semantic_relation_ids"] == first_path_plan["relation_ids"]
    assert "state_object<br/>Card" in first_path_diagram["mermaid_source"]
    assert "visible_output<br/>Claim receipt" in first_path_diagram["mermaid_source"]


def test_project_brief_formats_typed_policy_boundaries_without_duplicate_punctuation() -> None:
    proposal = _proposal(_release_scope_packet(), prompt=SEMANTIC_PROMPT)
    limits = next(
        row
        for row in proposal["project_brief"]["blueprint_sections"]
        if row["section"] == "Release proof and limits"
    )["must_capture"]

    assert ".." not in limits
    assert (
        "Policy boundaries: prohibited: Never reassign a card automatically."
        in limits
    )
    assert DEPENDENCY_EVIDENCE not in limits
    assert "Excluded:" not in limits


def test_projected_records_preserve_graph_custody_and_classify_defaults() -> None:
    packet = _release_scope_packet()
    proposal = _proposal(packet, prompt=SEMANTIC_PROMPT)

    assert {
        (row["custody_state"], row["evidence_tier"])
        for row in proposal["components"]
    } == {("system_policy", "odylith_assumption")}
    assert all(row["evidence_tier"] != "user_intent" for row in proposal["backlog"])
    assert proposal["backlog"][0]["custody_state"] == "system_policy"
    assert all(
        (row["custody_state"], row["evidence_tier"])
        == ("system_policy", "odylith_assumption")
        for row in proposal["diagrams"]
    )
    box_custody = {
        box["custody_state"]
        for diagram in proposal["diagrams"]
        for box in diagram["diagram_box_custody"]
    }
    assert box_custody == {"source_fact"}
    assert proposal["assumptions"] == []
    assert "product owner" not in str(proposal).casefold()
    assert proposal["release_plan"]["custody_state"] == "system_policy"

    backlog_items = [
        {**row, "idea_id": f"B-{index:03d}"}
        for index, row in enumerate(proposal["backlog"], 1)
    ]
    event = semantic_acceptance_event_preview(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=proposal["components"],
        diagram_ids=[row["slug"] for row in proposal["diagrams"]],
        release_selector="0.0.1",
        release_id="release-claim-desk-0-0-1",
    )
    accepted = semantic_accepted_project_payload(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=proposal["components"],
        diagram_ids=[row["slug"] for row in proposal["diagrams"]],
        release_selector="0.0.1",
        release_id="release-claim-desk-0-0-1",
        validation_gate={},
    )

    assert (event["custody_state"], event["evidence_tier"]) == (
        "system_policy",
        "odylith_assumption",
    )
    assert (accepted["custody_state"], accepted["evidence_tier"]) == (
        "system_policy",
        "odylith_assumption",
    )


def test_stateless_artifacts_use_one_plan_without_state_replay_or_wave_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from odylith.runtime.surfaces import compass_standup_brief_maintenance

    def fail_background_spawn(**_kwargs: object) -> int:
        raise AssertionError("sealed Greenfield pre-confirm spawned Compass narration")

    monkeypatch.setattr(
        compass_standup_brief_maintenance,
        "maybe_spawn_background",
        fail_background_spawn,
    )
    packet, prompt = _stateless_packet()
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    authority = semantic_intent_authority(verified, prompt=prompt)
    proposal = build_verified_semantic_proposal_for_repo(
        repo_root=tmp_path,
        authority=authority,
        release_selector="0.0.1",
    )

    transaction = compile_verified_semantic_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        intent_authority=authority,
        release_selector="0.0.1",
    )

    package = transaction.prewrite_package
    assert proposal["projection_plan"]["axes"]["state_fact_ids"] == []
    assert proposal["projection_plan"]["axes"]["visible_output_fact_ids"] == [
        "output.0",
        "output.1",
    ]
    assert len(package.backlog_result["created"]) == 1
    assert len(package.rendered_component_specs) == 1
    assert len(package.atlas_diagram_ids) == 1
    assert package.release_workstream_ids == ("B-001",)

    preview = package.component_registry_preview[0]
    authoring_input = preview["authoring_input"]
    contract = authoring_input["component_contract"]
    assert contract["state_objects"] == ()
    assert contract["visible_outputs"] == ("Signal chart", "Signal summary")
    assert contract["stateful"] is False
    assert {
        "owned_state",
        "produced_outputs",
        "states_or_transitions",
        "state_object",
        "visible_output",
    }.isdisjoint(contract)
    assert {"wave_label", "wave_status"}.isdisjoint(
        authoring_input["implementation_handoff"]
    )

    spec = package.rendered_component_specs["Signal View First Path"]
    assert "Signal chart" in spec and "Signal summary" in spec
    assert "### State objects" not in spec
    assert "### State transitions" not in spec
    assert "Replay" not in spec
    handoff_copy = " ".join(
        (
            package.next_steps_preview["implementation_prompt"],
            *package.next_steps_preview["validation_gates"],
        )
    )
    assert "replay" not in handoff_copy.casefold()
    assert "Signal chart" in handoff_copy and "Signal summary" in handoff_copy

    cards = package.project_dashboard_preview["product_story"]["release_contract"]
    assert [row["label"] for row in cards] == [
        "Workflow Facts",
        "Visible Outputs",
        "Component Boundaries",
        "Policy Boundaries",
    ]
    assert cards[1]["body"] == "Signal chart; Signal summary"
    assert package.project_dashboard_preview["artifact_depth"] == {
        "workstreams": 1,
        "components": 1,
        "diagrams": 1,
        "state_objects": 0,
        "visible_outputs": 2,
    }
    assert "## State Objects" not in package.project_brief_record_text
    assert "Replay" not in package.project_brief_record_text
    assert all(
        "replay" not in text.casefold()
        for text in package.backlog_result["idea_files"].values()
    )
    assert package.accepted_project_preview["proposal"]["projection_plan"] == (
        proposal["projection_plan"]
    )
    assert package.accepted_project_preview["project_dashboard"] == (
        package.project_dashboard_preview
    )


def _release_scope_packet() -> dict[str, object]:
    return copy.deepcopy(semantic_intent_packet())


def _proposal(packet: dict[str, object], *, prompt: str) -> dict[str, object]:
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    authority = semantic_intent_authority(verified, prompt=prompt)
    return build_verified_semantic_proposal(
        authority=authority,
        observed_source={"evidence_tier": "observed_source"},
    )
