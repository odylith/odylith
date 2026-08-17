from __future__ import annotations

import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_delivery import (
    semantic_first_release_workstream_ids,
    semantic_next_steps,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_assessment_sha256,
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
    PATH_EVIDENCE,
    SEMANTIC_PROMPT,
    semantic_fact,
    semantic_intent_packet,
)
from tests.unit.runtime.test_greenfield_semantic_projection_plan import (
    _stateless_packet,
)


def test_release_membership_and_start_owner_follow_typed_scope_after_reorder() -> None:
    proposal = _proposal(_release_scope_packet(), prompt=SEMANTIC_PROMPT)

    assert [row["label"] for row in proposal["components"]] == [
        "Claim Receipt Delivery",
        "Card Claim Service",
    ]
    assert [row["release_scope"] for row in proposal["components"]] == [
        "supporting",
        "first_path_required",
    ]
    assert proposal["release_plan"]["required_component_fact_ids"] == ["system.0"]
    assert proposal["release_plan"]["supporting_component_fact_ids"] == ["system.1"]
    assert proposal["release_plan"]["deferred_component_fact_ids"] == ["system.2"]
    assert proposal["release_plan"]["target_workstream_titles"] == [
        "Deliver Claim Desk First Path",
        "Implement Claim Receipt Delivery",
        "Implement Card Claim Service",
    ]
    assert proposal["release_plan"]["start_workstream_title"] == (
        "Implement Card Claim Service"
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

    assert release_ids == ["B-001", "B-002", "B-003"]
    assert handoff["project_workstream_id"] == "B-001"
    assert handoff["start_workstream_id"] == "B-003"
    assert handoff["start_workstream_title"] == "Implement Card Claim Service"
    state_diagram = next(
        row for row in proposal["diagrams"]
        if row["slug"].endswith("state-evidence")
    )
    state_plan = next(
        row for row in proposal["projection_plan"]["diagrams"]
        if row["key"] == "state_evidence"
    )
    assert state_diagram["semantic_fact_ids"] == state_plan["fact_ids"]
    assert state_diagram["semantic_relation_ids"] == state_plan["relation_ids"]
    assert "state_object<br/>Card" in state_diagram["mermaid_source"]
    assert "visible_output<br/>Claim receipt" in state_diagram["mermaid_source"]


def test_release_rejects_deferred_ownership_of_required_path() -> None:
    packet = _release_scope_packet()
    receipt = _system(packet, "system.1")
    _set_attribute(receipt, "release_scope", "deferred")

    with pytest.raises(ValueError) as exc_info:
        _proposal(packet, prompt=SEMANTIC_PROMPT)
    assert str(exc_info.value) == (
        "complete Semantic Intent IR lacks active typed implementation coverage"
    )


def test_projected_records_preserve_graph_custody_and_classify_defaults() -> None:
    assumption = "Assume the coordinator is already authenticated."
    prompt = f"{SEMANTIC_PROMPT} {assumption}"
    packet = _release_scope_packet()
    evidence_sha256 = semantic_evidence_sha256(
        {"operator_prompt": prompt, "operator_edit": ""}
    )
    packet["evidence_sha256"] = evidence_sha256
    packet["materiality_assessment"]["evidence_sha256"] = evidence_sha256
    packet["materiality_assessment_sha256"] = (
        semantic_materiality_assessment_sha256(
            packet["materiality_assessment"]
        )
    )
    packet["semantic_intent"]["facts"].append(
        semantic_fact(
            "assumption.0",
            "assumption",
            "Authenticated coordinator",
            assumption,
            0,
            assumption,
            custody="visible_assumption",
        )
    )
    proposal = _proposal(packet, prompt=prompt)

    assert {
        (row["custody_state"], row["evidence_tier"])
        for row in proposal["components"]
    } == {("bounded_interpretation", "odylith_assumption")}
    assert all(row["evidence_tier"] != "user_intent" for row in proposal["backlog"])
    assert proposal["backlog"][0]["custody_state"] == "system_policy"
    assert proposal["backlog"][1]["custody_state"] == "bounded_interpretation"
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
    assert {
        "source_fact",
        "bounded_interpretation",
        "visible_assumption",
    } <= box_custody
    assert "system_policy" not in box_custody
    assert proposal["assumptions"][0]["custody_state"] == "visible_assumption"
    assert proposal["assumptions"][0]["tier"] == "odylith_assumption"
    assert proposal["assumptions"][1]["custody_state"] == "system_policy"
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
) -> None:
    packet, prompt = _stateless_packet()
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    proposal = build_verified_semantic_proposal_for_repo(
        repo_root=tmp_path,
        authority=semantic_intent_authority(verified, prompt=prompt),
        release_selector="0.0.1",
    )

    transaction = compile_verified_semantic_transaction(
        repo_root=tmp_path,
        proposal=proposal,
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

    spec = package.rendered_component_specs["Signal Service"]
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
    packet = copy.deepcopy(semantic_intent_packet())
    claim = _system(packet, "system.0")
    receipt = _system(packet, "system.1")
    claim["order"] = 1
    receipt["order"] = 0
    _set_attribute(receipt, "release_scope", "supporting")
    packet["semantic_intent"]["facts"].append(
        semantic_fact(
            "system.2",
            "internal_system",
            "Deferred Analytics",
            "Deferred Analytics remains outside the first release.",
            2,
            PATH_EVIDENCE,
            custody="bounded_interpretation",
            attributes={
                "responsibility": "Analyze claim history after the first release.",
                "component_kind": "worker",
                "boundary": "Own post-release claim analytics.",
                "outside_boundary": "Claim selection and receipt delivery.",
                "proof": "Prove analytics only after source-backed scope is accepted.",
                "risk": "Early analytics could widen the accepted release.",
                "release_scope": "deferred",
            },
        )
    )
    return packet


def _proposal(packet: dict[str, object], *, prompt: str) -> dict[str, object]:
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    authority = semantic_intent_authority(verified, prompt=prompt)
    return build_verified_semantic_proposal(
        authority=authority,
        observed_source={"evidence_tier": "observed_source"},
    )


def _system(packet: dict[str, object], fact_id: str) -> dict[str, object]:
    facts = packet["semantic_intent"]["facts"]
    return next(row for row in facts if row["fact_id"] == fact_id)


def _set_attribute(fact: dict[str, object], name: str, value: str) -> None:
    attribute = next(row for row in fact["attributes"] if row["name"] == name)
    attribute["value"] = value
