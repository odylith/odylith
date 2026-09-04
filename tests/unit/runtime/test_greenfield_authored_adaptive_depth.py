"""Adaptive artifact depth on the sealed model-authored proposal route."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


def _source(intent: dict[str, Any]) -> str:
    return ". ".join(
        str(item)
        for value in intent.values()
        for item in (value if isinstance(value, list) else [value])
        if str(item)
    )


def _proposal(
    tmp_path: Path,
    *,
    intent: dict[str, Any],
    relations: list[dict[str, Any]],
    responsibility_owners: list[str],
) -> dict[str, Any]:
    source = _source(intent)
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                first_path_relations=relations,
                component_responsibility_owners=responsibility_owners,
            )
        ),
        authoring_timeout_seconds=54,
        authoring_profile_id=STANDARD_PROFILE_ID,
    )
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=source,
        release_selector="0.0.1",
        confirmed_intent=candidate,
        require_completion_ready=False,
    )


def _simple_proposal(tmp_path: Path) -> dict[str, Any]:
    first_path = (
        "Dock attendant enters a berth request. "
        "Intake Board records the berth request. "
        "Intake Board shows a signed berth receipt."
    )
    intent = {
        "title": "Harbor Desk",
        "product_story": "Dock attendants receive a reviewable berth receipt.",
        "state_object": "berth request",
        "first_path": first_path,
        "proof_boundary": "Verify the signed berth receipt and retained berth request.",
        "problem": "Berth requests are hard to review.",
        "customer": "Dock attendants",
        "opportunity": "Provide one reviewable berth request path.",
        "product_view": "Harbor Desk records one berth request and shows its receipt.",
        "success_metrics": ["A dock attendant sees a signed berth receipt."],
        "evidence_requirements": ["Retain the berth request with its receipt."],
        "operational_constraints": ["Keep the berth request reviewable."],
        "component_responsibilities": ["Record the berth request and show its receipt."],
        "human_actors": ["Dock attendant"],
        "external_systems": [],
        "internal_systems": ["Intake Board"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
    }
    return _proposal(
        tmp_path,
        intent=intent,
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Dock attendant",
                "event_quote": "Dock attendant enters a berth request",
                "action_verb_quote": "enters",
                "target_quote": "berth request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Intake Board",
                "owner_system_quote": "Intake Board",
                "event_quote": "Intake Board records the berth request",
                "action_verb_quote": "records",
                "target_quote": "berth request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Intake Board",
                "owner_system_quote": "Intake Board",
                "event_quote": "Intake Board shows a signed berth receipt",
                "action_verb_quote": "shows",
                "target_quote": "signed berth receipt",
                "visible_result_quote": "signed berth receipt",
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Intake Board"],
    )


def _structured_proposal(tmp_path: Path) -> dict[str, Any]:
    first_path = (
        "Dock attendant submits a cargo request. "
        "Intake Router records the cargo request. "
        "Harbor reviewer approves the cargo request. "
        "Receipt Ledger publishes a signed cargo receipt."
    )
    intent = {
        "title": "Cargo Relay",
        "product_story": "Harbor teams receive a reviewable cargo receipt.",
        "state_object": "cargo request",
        "first_path": first_path,
        "proof_boundary": "Replay the approved cargo request and verify its signed receipt.",
        "problem": "Cargo requests cross ownership boundaries without reviewable proof.",
        "customer": "Dock attendants and harbor reviewers",
        "opportunity": "Keep one multi-owner cargo path reviewable.",
        "product_view": "Cargo Relay records approval and publishes a signed receipt.",
        "success_metrics": [
            "A reviewer sees the approved cargo request.",
            "A dock attendant sees the signed cargo receipt.",
        ],
        "evidence_requirements": [
            "Retain the approved cargo request.",
            "Retain the signed cargo receipt.",
        ],
        "operational_constraints": [
            "Preserve approval custody.",
            "Preserve receipt custody.",
        ],
        "component_responsibilities": [
            "Record the cargo request.",
            "Publish the signed cargo receipt.",
        ],
        "human_actors": ["Dock attendant", "Harbor reviewer"],
        "external_systems": ["Vessel Registry", "Archive Vault"],
        "internal_systems": ["Intake Router", "Receipt Ledger"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not schedule vessels.", "Do not calculate harbor fees."],
    }
    return _proposal(
        tmp_path,
        intent=intent,
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Dock attendant",
                "event_quote": "Dock attendant submits a cargo request",
                "action_verb_quote": "submits",
                "target_quote": "cargo request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Intake Router",
                "owner_system_quote": "Intake Router",
                "event_quote": "Intake Router records the cargo request",
                "action_verb_quote": "records",
                "target_quote": "cargo request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Harbor reviewer",
                "event_quote": "Harbor reviewer approves the cargo request",
                "action_verb_quote": "approves",
                "target_quote": "cargo request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Receipt Ledger",
                "owner_system_quote": "Receipt Ledger",
                "event_quote": "Receipt Ledger publishes a signed cargo receipt",
                "action_verb_quote": "publishes",
                "target_quote": "signed cargo receipt",
                "visible_result_quote": "signed cargo receipt",
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Intake Router", "Receipt Ledger"],
    )


def _sparse_proposal(
    tmp_path: Path,
    *,
    internal_systems: list[str],
    external_systems: list[str],
    evidence_requirements: list[str],
    operational_constraints: list[str],
    component_responsibilities: list[str],
    relations: list[dict[str, Any]],
    responsibility_owners: list[str],
) -> dict[str, Any]:
    first_path = ". ".join(row["event_quote"] for row in relations) + "."
    intent = {
        "title": "Sparse Relay",
        "product_story": "Dock attendants receive a reviewable request receipt.",
        "state_object": "request",
        "first_path": first_path,
        "proof_boundary": "Replay the request and verify its signed receipt.",
        "problem": "Requests need one reviewable delivery path.",
        "customer": "Dock attendants",
        "opportunity": "Keep request delivery reviewable.",
        "product_view": "Sparse Relay records a request and publishes its receipt.",
        "success_metrics": ["A dock attendant sees the signed request receipt."],
        "evidence_requirements": evidence_requirements,
        "operational_constraints": operational_constraints,
        "component_responsibilities": component_responsibilities,
        "human_actors": ["Dock attendant"],
        "external_systems": external_systems,
        "internal_systems": internal_systems,
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
    }
    return _proposal(
        tmp_path,
        intent=intent,
        relations=relations,
        responsibility_owners=responsibility_owners,
    )


def _semantic_values(proposal: dict[str, Any]) -> dict[str, str]:
    intent = proposal["intent"]
    values = {
        f"/{field}": intent[field]
        for field in (
            "title",
            "product_story",
            "problem",
            "customer",
            "opportunity",
            "product_view",
            "state_object",
            "first_path",
            "proof_boundary",
        )
        if intent.get(field)
    }
    for field in (
        "human_actors",
        "internal_systems",
        "external_systems",
        "success_metrics",
        "evidence_requirements",
        "non_goals",
        "operational_constraints",
        "component_responsibilities",
    ):
        values.update(
            {
                f"/{field}/{index}": value
                for index, value in enumerate(intent.get(field, []))
            }
        )
    semantics = intent["authored_semantics"]
    for field, quote_field in (
        ("first_path_relations", "event_quote"),
        ("first_path_context_relations", "fact_quote"),
        ("component_responsibility_relations", "responsibility_quote"),
    ):
        values.update(
            {
                f"/authored_semantics/{field}/{index}": row[quote_field]
                for index, row in enumerate(semantics[field])
            }
        )
    return values


def _assert_owned_rendering(proposal: dict[str, Any]) -> None:
    source_values = _semantic_values(proposal)
    for row in proposal["backlog"]:
        assert len({row["problem"], row["opportunity"], row["product_view"]}) == 3
        contract = row["authored_workstream_semantics"]
        owned_refs = (
            set(contract["fact_refs"])
            | set(contract["relation_refs"])
            | set(contract["shared_fact_refs"])
        )
        rendered_text = {
            "title": row["title"],
            "problem": row["problem"],
            "customer": row["customer"],
            "opportunity": row["opportunity"],
            "product_view": row["product_view"],
            "success_metrics": "\n".join(row["success_metrics"]),
            "recommended_first_slice": row["recommended_first_slice"],
            "dependencies": "\n".join(row["dependencies"]),
            "validation": "\n".join(row["validation"]),
            "deferred_scope": "\n".join(row["ordering_decision"]["deferred_scope"]),
            "scope": row["radar_sections"]["Scope"],
            "ordering_why_now": row["ordering_decision"]["why_now"],
            "ordering_expected_outcome": row["ordering_decision"]["expected_outcome"],
            **{
                f"radar_sections.{section}": body
                for section, body in row["radar_sections"].items()
            },
        }
        for field, refs in contract["rendered_field_refs"].items():
            assert set(refs) <= owned_refs
            assert all(source_values[ref] in rendered_text[field] for ref in refs)
        component_refs = contract["rendered_field_refs"][
            "radar_sections.Impacted Components"
        ]
        rendered_components = {
            line.removeprefix("- ")
            for line in row["radar_sections"]["Impacted Components"].splitlines()
            if line.startswith("- ")
        }
        assert {source_values[ref] for ref in component_refs} == rendered_components


def _assert_component_ownership_is_source_exact(proposal: dict[str, Any]) -> None:
    intent = proposal["intent"]
    assert {row["label"] for row in proposal["components"]} == set(
        intent["internal_systems"]
    )
    assert {row["responsibility"] for row in proposal["components"]} == set(
        intent["component_responsibilities"]
    )
    assert all(
        row["component_contract"]["owner_system"] == row["label"]
        for row in proposal["components"]
    )


def test_boundary_free_authored_project_keeps_one_complete_row_and_three_views(
    tmp_path: Path,
) -> None:
    proposal = _simple_proposal(tmp_path)

    assert [row["workstream_role"] for row in proposal["backlog"]] == ["project"]
    assert [row["title"] for row in proposal["diagrams"]] == [
        "System Context View",
        "First Path Sequence",
        "State and Evidence View",
    ]
    project = proposal["backlog"][0]
    semantics = project["authored_workstream_semantics"]
    assert semantics["role"] == "project"
    assert "/product_story" in semantics["fact_refs"]
    assert "/first_path" in semantics["fact_refs"]
    assert "Berth requests are hard to review." in project["problem"]
    assert "Dock attendants receive a reviewable berth receipt." in project["radar_sections"]["Scope"]
    assert "Harbor Desk records one berth request and shows its receipt." in project["product_view"]
    assert any("signed berth receipt" in metric for metric in project["success_metrics"])
    _assert_owned_rendering(proposal)
    assert all(
        row["related_workstream_titles"] == ["Deliver Harbor Desk"]
        for row in proposal["diagrams"]
    )


def test_structured_authored_project_adds_only_distinct_typed_workstream_roles(
    tmp_path: Path,
) -> None:
    proposal = _structured_proposal(tmp_path)
    backlog = proposal["backlog"]

    assert [row["workstream_role"] for row in backlog] == [
        "project",
        "workflow",
        "boundary",
        "proof",
    ]
    assert len({row["title"] for row in backlog}) == 4
    assert backlog[-1]["component_focus"] == ["receipt-ledger"]
    semantics = {
        row["workstream_role"]: row["authored_workstream_semantics"]
        for row in backlog
    }
    assert semantics["workflow"]["fact_refs"] == [
        "/first_path",
        "/opportunity",
        "/human_actors/0",
        "/human_actors/1",
    ]
    assert semantics["workflow"]["relation_refs"] == [
        "/authored_semantics/first_path_relations/0",
        "/authored_semantics/first_path_relations/1",
        "/authored_semantics/first_path_relations/2",
        "/authored_semantics/first_path_relations/3",
    ]
    assert set(semantics["boundary"]["fact_refs"]) == {
        "/external_systems/0",
        "/external_systems/1",
        "/non_goals/0",
        "/non_goals/1",
        "/internal_systems/0",
        "/internal_systems/1",
        "/component_responsibilities/0",
        "/component_responsibilities/1",
    }
    assert semantics["proof"]["fact_refs"] == [
        "/proof_boundary",
        "/success_metrics/0",
        "/success_metrics/1",
        "/evidence_requirements/0",
        "/evidence_requirements/1",
        "/operational_constraints/0",
        "/operational_constraints/1",
    ]
    claimed_fact_refs = [
        ref
        for contract in semantics.values()
        for ref in contract["fact_refs"]
    ]
    claimed_relation_refs = [
        ref
        for contract in semantics.values()
        for ref in contract["relation_refs"]
    ]
    assert len(claimed_fact_refs) == len(set(claimed_fact_refs))
    assert len(claimed_relation_refs) == len(set(claimed_relation_refs))
    assert "Harbor reviewer approves the cargo request" in backlog[1]["product_view"]
    assert "Keep one multi-owner cargo path reviewable." in backlog[1]["opportunity"]
    assert "Archive Vault" in backlog[2]["opportunity"]
    assert "A dock attendant sees the signed cargo receipt." in backlog[3]["success_metrics"]
    _assert_owned_rendering(proposal)
    specialized_fact_refs = {
        ref
        for role in ("workflow", "boundary", "proof")
        for ref in semantics[role]["fact_refs"]
    }
    assert set(semantics["project"]["shared_fact_refs"]) == specialized_fact_refs
    assert not set(semantics["project"]["shared_fact_refs"]) & set(
        semantics["project"]["fact_refs"]
    )
    assert semantics["workflow"]["shared_fact_refs"] == [
        "/title",
        "/customer",
        "/internal_systems/0",
        "/internal_systems/1",
    ]
    assert semantics["boundary"]["shared_fact_refs"] == ["/title", "/customer"]
    assert semantics["proof"]["shared_fact_refs"] == [
        "/title",
        "/customer",
        "/internal_systems/1",
    ]
    for row in backlog[1:]:
        contract = row["authored_workstream_semantics"]
        assert {"/title", "/customer"} <= set(contract["shared_fact_refs"])
        assert not set(contract["shared_fact_refs"]) & set(contract["fact_refs"])
        rendered_refs = {
            ref
            for refs in contract["rendered_field_refs"].values()
            for ref in refs
        }
        assert set(contract["shared_fact_refs"]) <= rendered_refs
        assert row["customer"] == proposal["intent"]["customer"]
    proof_boundary = proposal["intent"]["proof_boundary"]
    for row in backlog[1:3]:
        assert proof_boundary not in str(row["success_metrics"])
        assert proof_boundary not in str(row["validation"])
        assert proof_boundary not in str(row["ordering_decision"])
        assert proof_boundary not in row["radar_sections"]["Rollout"]
    assert all(
        row["recommended_first_slice"] in row["radar_sections"]["Rollout"]
        for row in backlog
    )
    not_applicable = [
        body
        for row in backlog
        for body in row["radar_sections"].values()
        if body.startswith("- Not applicable")
    ]
    assert len(not_applicable) == len(set(not_applicable))
    assert all(row["workstream_role"] in "\n".join(row["radar_sections"].values()) for row in backlog)
    assert "No source-stated" not in "\n".join(
        body for row in backlog for body in row["radar_sections"].values()
    )

    diagrams = {row["title"]: row for row in proposal["diagrams"]}
    assert set(diagrams) == {
        "System Context View",
        "First Path Sequence",
        "State and Evidence View",
        "Component Boundary View",
    }
    assert diagrams["System Context View"]["related_workstream_titles"] == [
        "Deliver Cargo Relay",
        "Run Cargo Relay first path",
        "Define Cargo Relay boundaries",
    ]
    assert diagrams["State and Evidence View"]["related_workstream_titles"] == [
        "Deliver Cargo Relay",
        "Prove Cargo Relay release",
    ]
    assert all("Ownership and Proof" not in title for title in diagrams)
    assert all("Release Proof Review" not in title for title in diagrams)


def test_direct_evidence_graph_material_facts_compile_complete_project_and_workflow(
    tmp_path: Path,
) -> None:
    first_path = (
        "Donor registers a batch. "
        "Volunteer inspects the batch. "
        "Supervisor releases the batch."
    )
    product_story = "Create a governed community exchange."
    proof_boundary = "Supervisor releases the batch."
    intent = {
        "title": "Community Exchange",
        "product_story": product_story,
        "state_object": "batch",
        "first_path": first_path,
        "proof_boundary": proof_boundary,
        "problem": "",
        "customer": "",
        "opportunity": "",
        "product_view": "",
        "success_metrics": [],
        "evidence_requirements": [
            "Supervisor releases the batch.",
            "Retain the release receipt.",
        ],
        "operational_constraints": [
            "Preserve the release decision.",
            "Keep inspection evidence reviewable.",
        ],
        "component_responsibilities": ["Preserve the release decision."],
        "human_actors": ["Donor", "Volunteer", "Supervisor"],
        "external_systems": ["Safety Registry"],
        "internal_systems": [],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not override a safety hold."],
    }
    proposal = _proposal(
        tmp_path,
        intent=intent,
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Donor",
                "event_quote": "Donor registers a batch",
                "action_verb_quote": "registers",
                "target_quote": "a batch",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Volunteer",
                "event_quote": "Volunteer inspects the batch",
                "action_verb_quote": "inspects",
                "target_quote": "the batch",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Supervisor",
                "event_quote": "Supervisor releases the batch",
                "action_verb_quote": "releases",
                "target_quote": "the batch",
                "visible_result_quote": "releases the batch",
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Community Exchange"],
    )

    backlog = {
        row["workstream_role"]: row
        for row in proposal["backlog"]
    }
    assert list(backlog) == [
        "project",
        "workflow",
        "boundary",
        "proof",
    ]
    project = backlog["project"]
    workflow = backlog["workflow"]
    assert project["recommended_first_slice"] == "\n".join(
        (
            "Donor registers a batch",
            "Volunteer inspects the batch",
            "Supervisor releases the batch",
        )
    )
    assert project["problem"] == (
        "The source does not state the user problem. "
        "Validate this gap before implementation."
    )
    assert project["customer"] == "Donor"
    assert project["opportunity"] == (
        "The source does not state an opportunity. "
        "Validate this gap before implementation."
    )
    assert project["product_view"] == (
        "The source does not state a distinct product view. "
        "Validate this gap before implementation."
    )
    assert project["authored_workstream_semantics"]["evidence_gaps"] == [
        "problem",
        "opportunity",
        "product_view",
    ]
    assert not project["authored_workstream_semantics"]["rendered_field_refs"][
        "problem"
    ]
    brief_sections = {
        section["section"]: section["must_capture"]
        for section in proposal["project_brief"]["blueprint_sections"]
    }
    assert brief_sections["User problem"] == (
        "The source does not state the user problem. "
        "Validate this gap before implementation."
    )
    assert project["success_metrics"] == [proof_boundary]
    assert workflow["customer"] == "Donor"
    assert workflow["opportunity"] == (
        "The source does not state a workflow-specific opportunity. "
        "Validate this gap before implementation."
    )
    assert workflow["authored_workstream_semantics"]["evidence_gaps"] == [
        "opportunity"
    ]
    assert backlog["boundary"]["customer"] == "Donor"
    assert backlog["proof"]["customer"] == "Donor"
    project_semantics = project["authored_workstream_semantics"]
    assert {
        "/first_path",
        "/proof_boundary",
        "/human_actors/0",
        "/external_systems/0",
    } <= set(project_semantics["shared_fact_refs"])
    _assert_owned_rendering(proposal)


def test_authored_service_readiness_keeps_nonapproval_as_a_safety_boundary(
    tmp_path: Path,
) -> None:
    first_path = (
        "Coordinator records service capacity evidence. "
        "Readiness Ledger records review status. "
        "Readiness Board shows a reviewable readiness report."
    )
    safety_boundary = "The product must not grant automatic operational approval."
    proposal = _proposal(
        tmp_path,
        intent={
            "title": "Service Readiness Review",
            "product_story": "Coordinators need traceable evidence about service readiness.",
            "problem": "Readiness decisions lack reviewable capacity evidence.",
            "customer": "Service coordinators",
            "opportunity": "Give coordinators one reviewable readiness report.",
            "product_view": "Service Readiness Review records evidence and shows readiness status.",
            "state_object": "service readiness report",
            "first_path": first_path,
            "proof_boundary": (
                "Release proof requires retained capacity evidence and a reviewable status; "
                "it does not grant automatic operational approval."
            ),
            "success_metrics": ["A coordinator sees a reviewable readiness report."],
            "evidence_requirements": ["Retain capacity evidence with review status."],
            "operational_constraints": [safety_boundary],
            "component_responsibilities": [
                "Record capacity evidence and review status.",
                "Show the reviewable readiness report.",
            ],
            "human_actors": ["Coordinator"],
            "external_systems": [],
            "internal_systems": ["Readiness Ledger", "Readiness Board"],
            "assumptions": [],
            "ambiguities": [],
            "non_goals": ["Automatic operational approval is outside the first release."],
        },
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Coordinator",
                "event_quote": "Coordinator records service capacity evidence",
                "action_verb_quote": "records",
                "target_quote": "service capacity evidence",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Readiness Ledger",
                "owner_system_quote": "Readiness Ledger",
                "event_quote": "Readiness Ledger records review status",
                "action_verb_quote": "records",
                "target_quote": "review status",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Readiness Board",
                "owner_system_quote": "Readiness Board",
                "event_quote": "Readiness Board shows a reviewable readiness report",
                "action_verb_quote": "shows",
                "target_quote": "reviewable readiness report",
                "visible_result_quote": "reviewable readiness report",
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Readiness Ledger", "Readiness Board"],
    )

    assert proposal["intent"]["operational_constraints"] == [safety_boundary]
    assert proposal["intent"]["non_goals"] == [
        "Automatic operational approval is outside the first release."
    ]
    first_path_contract = proposal["semantic_model"]["first_path_contract"]
    assert first_path_contract["raw_path"] == "\n".join(
        (
            "Coordinator records service capacity evidence",
            "Readiness Ledger records review status",
            "Readiness Board shows a reviewable readiness report",
        )
    )
    assert first_path_contract["visible_result"] == "reviewable readiness report"
    assert "automatic operational approval" not in str(first_path_contract).casefold()


def test_authored_solar_path_keeps_user_outcome_distinct_from_meta_proof(
    tmp_path: Path,
) -> None:
    visible_result = "today's dispatch plan with projected savings versus no optimization"
    first_path = (
        "Homeowner connects a solar inverter and battery. "
        "Forecast Engine computes a forecast-driven dispatch schedule. "
        f"Plan Board shows {visible_result}."
    )
    proof_boundary = (
        "Release proof succeeds when one connected site retains a forecast-driven schedule "
        "with defensible savings; full closed-loop automation remains outside the release."
    )
    proposal = _proposal(
        tmp_path,
        intent={
            "title": "Sun Ledger",
            "product_story": "Homeowners need a clear plan for using and storing solar energy.",
            "problem": "Solar generation and household demand change at different times.",
            "customer": "Homeowners with solar generation and battery storage",
            "opportunity": "Show one dispatch plan and its projected savings.",
            "product_view": "Sun Ledger forecasts energy and shows the household dispatch plan.",
            "state_object": "site energy plan",
            "first_path": first_path,
            "proof_boundary": proof_boundary,
            "success_metrics": [f"A homeowner sees {visible_result}."],
            "evidence_requirements": ["Retain the forecast and projected savings inputs."],
            "operational_constraints": ["Keep the homeowner in control of overrides."],
            "component_responsibilities": [
                "Compute the forecast-driven dispatch schedule.",
                "Show the dispatch plan and projected savings.",
            ],
            "human_actors": ["Homeowner"],
            "external_systems": ["solar inverter and battery"],
            "internal_systems": ["Forecast Engine", "Plan Board"],
            "assumptions": [],
            "ambiguities": [],
            "non_goals": ["Full closed-loop automation is outside the first release."],
        },
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Homeowner",
                "event_quote": "Homeowner connects a solar inverter and battery",
                "action_verb_quote": "connects",
                "target_quote": "solar inverter and battery",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Forecast Engine",
                "owner_system_quote": "Forecast Engine",
                "event_quote": "Forecast Engine computes a forecast-driven dispatch schedule",
                "action_verb_quote": "computes",
                "target_quote": "forecast-driven dispatch schedule",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Plan Board",
                "owner_system_quote": "Plan Board",
                "event_quote": f"Plan Board shows {visible_result}",
                "action_verb_quote": "shows",
                "target_quote": visible_result,
                "visible_result_quote": visible_result,
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Forecast Engine", "Plan Board"],
    )

    first_path_contract = proposal["semantic_model"]["first_path_contract"]
    assert first_path_contract["raw_path"] == "\n".join(
        (
            "Homeowner connects a solar inverter and battery",
            "Forecast Engine computes a forecast-driven dispatch schedule",
            f"Plan Board shows {visible_result}",
        )
    )
    assert first_path_contract["visible_result"] == visible_result
    assert proof_boundary == proposal["intent"]["proof_boundary"]
    assert "Release proof succeeds" not in first_path_contract["raw_path"]
    assert "Release proof succeeds" not in first_path_contract["visible_result"]


def test_authored_ocean_reproducibility_stays_proof_not_component_identity(
    tmp_path: Path,
) -> None:
    proof_boundary = (
        "A data steward can reproduce the accepted or rejected correction from the "
        "sensor reading, reference sample, drift estimate, correction decision, and reviewer note."
    )
    proposal = _proposal(
        tmp_path,
        intent={
            "title": "Ocean Sensor Calibration",
            "product_story": "Marine scientists need reviewable sensor drift corrections.",
            "problem": "Sensor corrections are hard to reproduce before publication.",
            "customer": "Marine scientists and data stewards",
            "opportunity": "Keep one calibration decision and its evidence reviewable.",
            "product_view": "Ocean Sensor Calibration records drift decisions and exports calibrated data.",
            "state_object": "calibration review case",
            "first_path": (
                "Marine scientist creates a calibration review case. "
                "Calibration Ledger records the drift estimate and correction decision. "
                "Publication Gate exports a calibrated data packet."
            ),
            "proof_boundary": proof_boundary,
            "success_metrics": ["A data steward can replay one correction decision."],
            "evidence_requirements": ["Retain the reading, sample, estimate, decision, and reviewer note."],
            "operational_constraints": ["Do not publish a correction without its retained evidence."],
            "component_responsibilities": [
                "Record the drift estimate and correction decision.",
                "Export the calibrated data packet.",
            ],
            "human_actors": ["Marine scientist", "Data steward"],
            "external_systems": ["Sensor data file", "Reference sample registry"],
            "internal_systems": ["Calibration Ledger", "Publication Gate"],
            "assumptions": [],
            "ambiguities": [],
            "non_goals": [],
        },
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Marine scientist",
                "event_quote": "Marine scientist creates a calibration review case",
                "action_verb_quote": "creates",
                "target_quote": "calibration review case",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Calibration Ledger",
                "owner_system_quote": "Calibration Ledger",
                "event_quote": "Calibration Ledger records the drift estimate and correction decision",
                "action_verb_quote": "records",
                "target_quote": "drift estimate and correction decision",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Publication Gate",
                "owner_system_quote": "Publication Gate",
                "event_quote": "Publication Gate exports a calibrated data packet",
                "action_verb_quote": "exports",
                "target_quote": "calibrated data packet",
                "visible_result_quote": "calibrated data packet",
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Calibration Ledger", "Publication Gate"],
    )

    _assert_component_ownership_is_source_exact(proposal)
    assert all(proof_boundary not in str(row) for row in proposal["components"])
    assert proposal["release_plan"]["strategy"] == proof_boundary
    assert proof_boundary in proposal["project_brief"]["coding_readiness_gates"]


def test_authored_health_tracking_retains_safety_and_first_path_outcome(
    tmp_path: Path,
) -> None:
    safety_boundary = "The product must not diagnose, prescribe, or approve treatment."
    visible_result = "reviewable symptom trend and safety status"
    proposal = _proposal(
        tmp_path,
        intent={
            "title": "Health Episode Journal",
            "product_story": "People need a private record of symptoms, relief attempts, and changes over time.",
            "problem": "Episode history is hard to review without one consistent timeline.",
            "customer": "People tracking their own health episodes",
            "opportunity": "Show one reviewable symptom trend without clinical approval claims.",
            "product_view": "Health Episode Journal records episodes and shows a reviewable trend.",
            "state_object": "health episode timeline",
            "first_path": (
                "Journal user records a health episode. "
                "Episode Ledger records symptoms and relief attempts. "
                f"Trend Board shows a {visible_result}."
            ),
            "proof_boundary": (
                "One user can replay an episode and its trend with retained safety status; "
                "the result is not a diagnosis or treatment approval."
            ),
            "success_metrics": [f"A journal user sees a {visible_result}."],
            "evidence_requirements": ["Retain episode details and correction history."],
            "operational_constraints": [safety_boundary],
            "component_responsibilities": [
                "Record symptoms and relief attempts.",
                "Show the symptom trend and safety status.",
            ],
            "human_actors": ["Journal user"],
            "external_systems": [],
            "internal_systems": ["Episode Ledger", "Trend Board"],
            "assumptions": [],
            "ambiguities": [],
            "non_goals": ["Clinical diagnosis and treatment approval are outside the release."],
        },
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Journal user",
                "event_quote": "Journal user records a health episode",
                "action_verb_quote": "records",
                "target_quote": "health episode",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Episode Ledger",
                "owner_system_quote": "Episode Ledger",
                "event_quote": "Episode Ledger records symptoms and relief attempts",
                "action_verb_quote": "records",
                "target_quote": "symptoms and relief attempts",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Trend Board",
                "owner_system_quote": "Trend Board",
                "event_quote": f"Trend Board shows a {visible_result}",
                "action_verb_quote": "shows",
                "target_quote": visible_result,
                "visible_result_quote": visible_result,
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Episode Ledger", "Trend Board"],
    )

    _assert_component_ownership_is_source_exact(proposal)
    assert proposal["semantic_model"]["first_path_contract"]["visible_result"] == visible_result
    assert proposal["intent"]["operational_constraints"] == [safety_boundary]
    assert safety_boundary in proposal["project_brief"]["operational_constraints"]
    assert "not a diagnosis or treatment approval" in proposal["release_plan"]["strategy"]


def test_authored_robotic_safety_projects_the_reviewed_recovery_status(
    tmp_path: Path,
) -> None:
    visible_result = "reviewed recovery status with unsafe states still visible"
    proof_boundary = (
        "One blocked aisle incident stops automation, retains corrective action, and shows "
        f"{visible_result} before resume."
    )
    proposal = _proposal(
        tmp_path,
        intent={
            "title": "Robotic Warehouse Safety Stop",
            "product_story": "Warehouse operators need unsafe robot states visible before automation resumes.",
            "problem": "Blocked aisles can lose safety and recovery evidence across handoffs.",
            "customer": "Warehouse operators and safety reviewers",
            "opportunity": "Keep stop decisions and recovery status reviewable.",
            "product_view": "Robotic Warehouse Safety Stop records decisions and shows recovery status.",
            "state_object": "robotics exception record",
            "first_path": (
                "Floor operator reports a blocked aisle. "
                "Safety Ledger records the stop decision and corrective action. "
                f"Recovery Board shows {visible_result}."
            ),
            "proof_boundary": proof_boundary,
            "success_metrics": [f"A safety reviewer sees {visible_result}."],
            "evidence_requirements": ["Retain the blocker, stop decision, and corrective action."],
            "operational_constraints": ["Unsafe states must block resume until recovery evidence is reviewed."],
            "component_responsibilities": [
                "Record the stop decision and corrective action.",
                "Show reviewed recovery status before resume.",
            ],
            "human_actors": ["Floor operator", "Safety reviewer"],
            "external_systems": ["Warehouse robot control system"],
            "internal_systems": ["Safety Ledger", "Recovery Board"],
            "assumptions": [],
            "ambiguities": [],
            "non_goals": ["Bypassing physical safety interlocks is outside the release."],
        },
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Floor operator",
                "event_quote": "Floor operator reports a blocked aisle",
                "action_verb_quote": "reports",
                "target_quote": "blocked aisle",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Safety Ledger",
                "owner_system_quote": "Safety Ledger",
                "event_quote": "Safety Ledger records the stop decision and corrective action",
                "action_verb_quote": "records",
                "target_quote": "stop decision and corrective action",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Recovery Board",
                "owner_system_quote": "Recovery Board",
                "event_quote": f"Recovery Board shows {visible_result}",
                "action_verb_quote": "shows",
                "target_quote": visible_result,
                "visible_result_quote": visible_result,
                "recovery_path": True,
            },
        ],
        responsibility_owners=["Safety Ledger", "Recovery Board"],
    )

    assert proposal["semantic_model"]["first_path_contract"]["visible_result"] == visible_result
    assert proposal["release_plan"]["strategy"] == proof_boundary
    assert any(
        visible_result in criterion
        for criterion in proposal["release_plan"]["promotion_criteria"]
    )


def test_authored_service_goal_components_cannot_acquire_cross_domain_templates(
    tmp_path: Path,
) -> None:
    proposal = _proposal(
        tmp_path,
        intent={
            "title": "Service Goal Planner",
            "product_story": "Service coordinators need a plan that responds to recorded progress.",
            "problem": "Progress updates do not consistently change the next plan target.",
            "customer": "Service coordinators",
            "opportunity": "Keep one goal, progress history, and follow-up reminder reviewable.",
            "product_view": "Service Goal Planner updates a plan target from recorded progress.",
            "state_object": "service goal plan",
            "first_path": (
                "Coordinator completes onboarding and acknowledgement. "
                "Goal Planner records a starting plan target. "
                "Progress Ledger records seven days of progress. "
                "Reminder Board shows an adjusted plan target and one follow-up reminder."
            ),
            "proof_boundary": "Replay the progress history, adjusted target, and follow-up reminder.",
            "success_metrics": ["A coordinator sees an adjusted target and follow-up reminder."],
            "evidence_requirements": ["Retain onboarding, progress, target, and reminder evidence."],
            "operational_constraints": ["Keep export and deletion behavior reviewable."],
            "component_responsibilities": [
                "Record the starting plan target.",
                "Record seven days of progress.",
                "Show the adjusted target and follow-up reminder.",
            ],
            "human_actors": ["Coordinator"],
            "external_systems": [],
            "internal_systems": ["Goal Planner", "Progress Ledger", "Reminder Board"],
            "assumptions": [],
            "ambiguities": [],
            "non_goals": [],
        },
        relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Coordinator",
                "event_quote": "Coordinator completes onboarding and acknowledgement",
                "action_verb_quote": "completes",
                "target_quote": "onboarding and acknowledgement",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Goal Planner",
                "owner_system_quote": "Goal Planner",
                "event_quote": "Goal Planner records a starting plan target",
                "action_verb_quote": "records",
                "target_quote": "starting plan target",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Progress Ledger",
                "owner_system_quote": "Progress Ledger",
                "event_quote": "Progress Ledger records seven days of progress",
                "action_verb_quote": "records",
                "target_quote": "seven days of progress",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Reminder Board",
                "owner_system_quote": "Reminder Board",
                "event_quote": "Reminder Board shows an adjusted plan target and one follow-up reminder",
                "action_verb_quote": "shows",
                "target_quote": "adjusted plan target and one follow-up reminder",
                "visible_result_quote": "adjusted plan target and one follow-up reminder",
                "recovery_path": False,
            },
        ],
        responsibility_owners=["Goal Planner", "Progress Ledger", "Reminder Board"],
    )

    _assert_component_ownership_is_source_exact(proposal)
    _assert_owned_rendering(proposal)
    authored_facts = set(proposal["intent"]["component_responsibilities"])
    assert all(row["source_system_description"] in authored_facts for row in proposal["components"])


def test_sparse_depth_keeps_facts_in_project_without_filler_rows(tmp_path: Path) -> None:
    human_event = {
        "actor_kind": "human",
        "actor_quote": "Dock attendant",
        "event_quote": "Dock attendant submits a request",
        "action_verb_quote": "submits",
        "target_quote": "request",
        "visible_result_quote": "",
        "recovery_path": False,
    }
    intake_event = {
        "actor_kind": "product",
        "actor_quote": "Intake Board",
        "owner_system_quote": "Intake Board",
        "event_quote": "Intake Board records the request",
        "action_verb_quote": "records",
        "target_quote": "request",
        "visible_result_quote": "",
        "recovery_path": False,
    }
    receipt_event = {
        "actor_kind": "product",
        "actor_quote": "Receipt Ledger",
        "owner_system_quote": "Receipt Ledger",
        "event_quote": "Receipt Ledger publishes a signed request receipt",
        "action_verb_quote": "publishes",
        "target_quote": "signed request receipt",
        "visible_result_quote": "signed request receipt",
        "recovery_path": False,
    }
    intake_result_event = {
        **receipt_event,
        "actor_quote": "Intake Board",
        "owner_system_quote": "Intake Board",
        "event_quote": "Intake Board publishes a signed request receipt",
    }
    cases = (
        (
            "external-only",
            {
                "internal_systems": ["Intake Board"],
                "external_systems": ["Vessel Registry"],
                "evidence_requirements": ["Retain the request receipt."],
                "operational_constraints": ["Keep the receipt reviewable."],
                "component_responsibilities": ["Record the request and publish its receipt."],
                "relations": [human_event, intake_event, intake_result_event],
                "responsibility_owners": ["Intake Board"],
            },
            "/external_systems/0",
            4,
        ),
        (
            "multi-owner-only",
            {
                "internal_systems": ["Intake Board", "Receipt Ledger"],
                "external_systems": [],
                "evidence_requirements": ["Retain the request receipt."],
                "operational_constraints": ["Keep the receipt reviewable."],
                "component_responsibilities": [
                    "Record the request.",
                    "Publish the signed request receipt.",
                ],
                "relations": [human_event, intake_event, receipt_event],
                "responsibility_owners": ["Intake Board", "Receipt Ledger"],
            },
            "/component_responsibilities/1",
            4,
        ),
        (
            "proof-only",
            {
                "internal_systems": ["Intake Board"],
                "external_systems": [],
                "evidence_requirements": [
                    "Retain the request.",
                    "Retain the signed request receipt.",
                ],
                "operational_constraints": [],
                "component_responsibilities": ["Record the request and publish its receipt."],
                "relations": [human_event, intake_event, intake_result_event],
                "responsibility_owners": ["Intake Board"],
            },
            "/evidence_requirements/1",
            3,
        ),
    )
    for name, arguments, retained_ref, expected_diagram_count in cases:
        case_root = tmp_path / name
        case_root.mkdir()
        proposal = _sparse_proposal(case_root, **arguments)
        assert [row["workstream_role"] for row in proposal["backlog"]] == ["project"]
        assert retained_ref in proposal["backlog"][0]["authored_workstream_semantics"]["fact_refs"]
        assert len(proposal["diagrams"]) == expected_diagram_count
        visible_copy = "\n".join(
            str(proposal["backlog"][0][field])
            for field in ("problem", "customer", "opportunity", "product_view")
        ).lower()
        assert "none accepted" not in visible_copy
        assert "reviewers" not in visible_copy
        _assert_owned_rendering(proposal)
