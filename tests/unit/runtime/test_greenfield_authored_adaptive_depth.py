"""Source fidelity across required structural provisional-design projections."""

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
                "actor_fact_quote": "Dock attendant",
                "event_quote": "Dock attendant enters a berth request",
                "action_verb_quote": "enters",
                "target_quote": "berth request",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Intake Board",
                "owner_system_quote": "Intake Board",
                "event_quote": "Intake Board records the berth request",
                "action_verb_quote": "records",
                "target_quote": "berth request",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Intake Board",
                "owner_system_quote": "Intake Board",
                "event_quote": "Intake Board shows a signed berth receipt",
                "action_verb_quote": "shows",
                "target_quote": "signed berth receipt",
                "visible_result_quote": "signed berth receipt",
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
                "actor_fact_quote": "Dock attendant",
                "event_quote": "Dock attendant submits a cargo request",
                "action_verb_quote": "submits",
                "target_quote": "cargo request",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Intake Router",
                "owner_system_quote": "Intake Router",
                "event_quote": "Intake Router records the cargo request",
                "action_verb_quote": "records",
                "target_quote": "cargo request",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "human",
                "actor_fact_quote": "Harbor reviewer",
                "event_quote": "Harbor reviewer approves the cargo request",
                "action_verb_quote": "approves",
                "target_quote": "cargo request",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Receipt Ledger",
                "owner_system_quote": "Receipt Ledger",
                "event_quote": "Receipt Ledger publishes a signed cargo receipt",
                "action_verb_quote": "publishes",
                "target_quote": "signed cargo receipt",
                "visible_result_quote": "signed cargo receipt",
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


def _assert_structural_design_projection_preserves_source(proposal: dict[str, Any]) -> None:
    """Characterize structural fixture custody, not proposed-design usefulness."""

    intent = proposal["intent"]
    semantics = intent["authored_semantics"]
    relations = semantics["first_path_relations"]
    design = semantics["provisional_design"]
    visible_package = str({
        field: proposal[field]
        for field in (
            "assumptions",
            "project_brief",
            "project_intelligence",
            "release_plan",
            "backlog",
            "components",
            "semantic_model",
            "diagrams",
        )
    })
    for field in (
        "title",
        "product_story",
        "problem",
        "customer",
        "opportunity",
        "product_view",
        "state_object",
        "proof_boundary",
    ):
        if intent.get(field):
            assert intent[field] in visible_package
    assert all(row["event_quote"] in visible_package for row in relations)
    for field in (
        "success_metrics",
        "component_responsibilities",
        "human_actors",
        "external_systems",
        "internal_systems",
        "non_goals",
        "evidence_requirements",
        "operational_constraints",
    ):
        assert all(value in visible_package for value in intent.get(field, []))
    assert all(
        row["statement"] in visible_package for row in intent.get("assumptions", [])
    )
    assert proposal["semantic_model"]["provisional_design"] == design
    assert [row["label"] for row in proposal["components"]] == [
        row["name"] for row in design["components"]
    ]
    assert [row["title"] for row in proposal["backlog"]] == [
        row["title"] for row in design["workstreams"]
    ]
    supported_events: list[dict[str, Any]] = []
    for index, (projected, canonical) in enumerate(
        zip(proposal["components"], design["components"], strict=True)
    ):
        contract = projected["component_contract"]
        assert projected["authority_kind"] == "provisional_design"
        assert contract["authority_kind"] == "provisional_design"
        assert contract["design_ref"] == f"/authored_semantics/provisional_design/components/{index}"
        assert contract["provisional_component"] == canonical
        assert contract["supporting_events"] == [
            relations[order - 1] for order in canonical["supported_event_orders"]
        ]
        supported_events.extend(contract["supporting_events"])
    assert all(relation in supported_events for relation in relations)
    titles_by_key = {row["key"]: row["title"] for row in design["workstreams"]}
    for index, (projected, canonical) in enumerate(
        zip(proposal["backlog"], design["workstreams"], strict=True)
    ):
        contract = projected["provisional_workstream_contract"]
        assert projected["authority_kind"] == projected["workstream_role"] == "provisional_design"
        assert projected["component_focus"] == canonical["component_keys"]
        assert contract["design_ref"] == f"/authored_semantics/provisional_design/workstreams/{index}"
        assert contract["provisional_workstream"] == canonical
        assert projected["dependencies"] == [
            titles_by_key[key] for key in canonical["depends_on"]
        ]
        assert "actor's ownership" in projected["radar_sections"]["Design Authority"]


def test_boundary_free_source_keeps_complete_structural_design_projection(
    tmp_path: Path,
) -> None:
    proposal = _simple_proposal(tmp_path)

    assert [row["workstream_role"] for row in proposal["backlog"]] == [
        "provisional_design"
    ] * 4
    assert [row["title"] for row in proposal["diagrams"]] == [
        "System Context View",
        "First Path Sequence",
        "Proposed Component Exchanges",
        "Proposed Delivery Dependencies and Acceptance",
        "Proposed Capability Support and Source Facts",
    ]
    project = proposal["backlog"][0]
    assert "Berth requests are hard to review." in project["problem"]
    assert proposal["intent"]["product_story"] == "Dock attendants receive a reviewable berth receipt."
    assert "Harbor Desk records one berth request and shows its receipt." in project["product_view"]
    assert "A dock attendant sees a signed berth receipt." in project["radar_sections"]["Source Success Metrics"]
    _assert_structural_design_projection_preserves_source(proposal)
    workstream_titles = [row["title"] for row in proposal["backlog"]]
    assert all(
        row["related_workstream_titles"] == workstream_titles
        for row in proposal["diagrams"]
    )


def test_one_typed_event_keeps_complete_structural_projection_without_extra_events(
    tmp_path: Path,
) -> None:
    proposal = _sparse_proposal(
        tmp_path,
        internal_systems=["Sparse Relay"],
        external_systems=[],
        evidence_requirements=["Retain the request receipt."],
        operational_constraints=["Keep the request reviewable."],
        component_responsibilities=["Record the request."],
        relations=[
            {
                "actor_kind": "human",
                "actor_fact_quote": "Dock attendant",
                "event_quote": "Dock attendant records a request",
                "action_verb_quote": "records",
                "target_quote": "request",
                "visible_result_quote": "request receipt",
            }
        ],
        responsibility_owners=["Sparse Relay"],
    )

    assert [row["title"] for row in proposal["diagrams"]] == [
        "System Context View",
        "First Path Sequence",
        "Proposed Component Exchanges",
        "Proposed Delivery Dependencies and Acceptance",
        "Proposed Capability Support and Source Facts",
    ]
    assert len(proposal["semantic_model"]["first_path_contract"]["events"]) == 1
    assert all(
        component["component_contract"]["supporting_events"][0]["event_quote"]
        == "Dock attendant records a request"
        for component in proposal["components"]
    )
    _assert_structural_design_projection_preserves_source(proposal)


def test_structured_source_projects_distinct_canonical_design_with_source_custody(
    tmp_path: Path,
) -> None:
    proposal = _structured_proposal(tmp_path)
    backlog = proposal["backlog"]
    intent = proposal["intent"]
    design = intent["authored_semantics"]["provisional_design"]

    assert [row["workstream_role"] for row in backlog] == ["provisional_design"] * 4
    assert len({row["title"] for row in backlog}) == 4
    assert [row["component_focus"] for row in backlog] == [
        row["component_keys"] for row in design["workstreams"]
    ]
    source_events = [
        row["event_quote"]
        for row in intent["authored_semantics"]["first_path_relations"]
    ]
    assert source_events == [
        "Dock attendant submits a cargo request",
        "Intake Router records the cargo request",
        "Harbor reviewer approves the cargo request",
        "Receipt Ledger publishes a signed cargo receipt",
    ]
    for row in backlog:
        assert row["problem"] == f"Source fact — {intent['problem']}"
        assert row["customer"] == f"Source fact — {intent['customer']}"
        assert row["opportunity"] == f"Source fact — {intent['opportunity']}"
        assert row["product_view"] == f"Source fact — {intent['product_view']}"
        assert all(value in row["radar_sections"]["Non-Goals"] for value in intent["non_goals"])
        assert all(
            value in row["radar_sections"]["Operational Constraints"]
            for value in intent["operational_constraints"]
        )
    rendered_support = "\n".join(
        row["radar_sections"]["Source Event Support"] for row in backlog
    )
    assert all(event in rendered_support for event in source_events)
    assert all(
        row["recommended_first_slice"] in row["radar_sections"]["Rollout"]
        for row in backlog
    )
    _assert_structural_design_projection_preserves_source(proposal)

    diagrams = {row["title"]: row for row in proposal["diagrams"]}
    assert set(diagrams) == {
        "System Context View",
        "First Path Sequence",
        "Proposed Component Exchanges",
        "Proposed Delivery Dependencies and Acceptance",
        "Proposed Capability Support and Source Facts",
    }
    assert [row["authority_kind"] for row in proposal["diagrams"]] == [
        "source_grounded",
        "source_grounded",
        "provisional_design",
        "provisional_design",
        "provisional_design",
    ]
    context_copy = str(diagrams["System Context View"])
    assert "Vessel Registry" in context_copy
    assert "Archive Vault" in context_copy


def test_direct_evidence_graph_material_facts_survive_structural_design_projection(
    tmp_path: Path,
) -> None:
    first_path = (
        "Donor registers a batch. "
        "Volunteer inspects the batch. "
        "Supervisor releases the batch."
    )
    product_story = "Create a governed community exchange."
    proof_boundary = "Supervisor releases the batch."
    decisions = {
        "problem": "Participants need to keep batch registration, inspection, and release connected.",
        "customer": "Community exchange participants are the primary beneficiaries of the batch history.",
        "opportunity": "A reviewable batch history can carry inspection evidence into the release decision.",
        "product_view": "Participants should follow each batch from donation through inspection to release.",
    }
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
        "assumptions": [
            {"applies_to": field, "statement": statement}
            for field, statement in decisions.items()
        ],
        "ambiguities": [],
        "non_goals": ["Do not override a safety hold."],
    }
    proposal = _proposal(
        tmp_path,
        intent=intent,
        relations=[
            {
                "actor_kind": "human",
                "actor_fact_quote": "Donor",
                "event_quote": "Donor registers a batch",
                "action_verb_quote": "registers",
                "target_quote": "a batch",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "human",
                "actor_fact_quote": "Volunteer",
                "event_quote": "Volunteer inspects the batch",
                "action_verb_quote": "inspects",
                "target_quote": "the batch",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "human",
                "actor_fact_quote": "Supervisor",
                "event_quote": "Supervisor releases the batch",
                "action_verb_quote": "releases",
                "target_quote": "the batch",
                "visible_result_quote": "releases the batch",
            },
        ],
        responsibility_owners=["Community Exchange"],
    )

    backlog = proposal["backlog"]
    assert [row["workstream_role"] for row in backlog] == ["provisional_design"] * 4
    for row in backlog:
        for index, (field, statement) in enumerate(decisions.items()):
            assert row[field] == f"Assumption — {statement}"
            assert row["provisional_workstream_contract"]["decision_refs"][field] == (
                f"/assumptions/{index}"
            )
        assert all(
            statement in row["radar_sections"]["Assumptions"]
            for statement in decisions.values()
        )
        assert "Do not override a safety hold." in row["radar_sections"]["Non-Goals"]
        assert "Preserve the release decision." in row["radar_sections"]["Operational Constraints"]
        assert "Keep inspection evidence reviewable." in row["radar_sections"]["Operational Constraints"]
    brief_sections = {
        section["section"]: section["must_capture"]
        for section in proposal["project_brief"]["blueprint_sections"]
    }
    assert brief_sections["User problem"] == f"Assumption — {decisions['problem']}"
    assert proposal["project_brief"]["external_systems"] == ["Safety Registry"]
    assert [
        row["actor_fact_quote"]
        for row in proposal["intent"]["authored_semantics"]["first_path_relations"]
    ] == ["Donor", "Volunteer", "Supervisor"]
    rendered_support = "\n".join(
        row["radar_sections"]["Source Event Support"] for row in backlog
    )
    assert all(
        event in rendered_support
        for event in (
            "Donor registers a batch",
            "Volunteer inspects the batch",
            "Supervisor releases the batch",
        )
    )
    assert proposal["release_plan"]["strategy"] == proof_boundary
    _assert_structural_design_projection_preserves_source(proposal)


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
                "actor_fact_quote": "Coordinator",
                "event_quote": "Coordinator records service capacity evidence",
                "action_verb_quote": "records",
                "target_quote": "service capacity evidence",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Readiness Ledger",
                "owner_system_quote": "Readiness Ledger",
                "event_quote": "Readiness Ledger records review status",
                "action_verb_quote": "records",
                "target_quote": "review status",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Readiness Board",
                "owner_system_quote": "Readiness Board",
                "event_quote": "Readiness Board shows a reviewable readiness report",
                "action_verb_quote": "shows",
                "target_quote": "reviewable readiness report",
                "visible_result_quote": "reviewable readiness report",
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
                "actor_fact_quote": "Homeowner",
                "event_quote": "Homeowner connects a solar inverter and battery",
                "action_verb_quote": "connects",
                "target_quote": "solar inverter and battery",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Forecast Engine",
                "owner_system_quote": "Forecast Engine",
                "event_quote": "Forecast Engine computes a forecast-driven dispatch schedule",
                "action_verb_quote": "computes",
                "target_quote": "forecast-driven dispatch schedule",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Plan Board",
                "owner_system_quote": "Plan Board",
                "event_quote": f"Plan Board shows {visible_result}",
                "action_verb_quote": "shows",
                "target_quote": visible_result,
                "visible_result_quote": visible_result,
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
    """Check source semantics; the synthetic design assertion covers custody only."""

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
                "actor_fact_quote": "Marine scientist",
                "event_quote": "Marine scientist creates a calibration review case",
                "action_verb_quote": "creates",
                "target_quote": "calibration review case",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Calibration Ledger",
                "owner_system_quote": "Calibration Ledger",
                "event_quote": "Calibration Ledger records the drift estimate and correction decision",
                "action_verb_quote": "records",
                "target_quote": "drift estimate and correction decision",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Publication Gate",
                "owner_system_quote": "Publication Gate",
                "event_quote": "Publication Gate exports a calibrated data packet",
                "action_verb_quote": "exports",
                "target_quote": "calibrated data packet",
                "visible_result_quote": "calibrated data packet",
            },
        ],
        responsibility_owners=["Calibration Ledger", "Publication Gate"],
    )

    _assert_structural_design_projection_preserves_source(proposal)
    assert all(proof_boundary not in str(row) for row in proposal["components"])
    assert proposal["release_plan"]["strategy"] == proof_boundary
    assert proof_boundary in proposal["project_brief"]["coding_readiness_gates"]


def test_authored_health_tracking_retains_safety_and_first_path_outcome(
    tmp_path: Path,
) -> None:
    """Check source safety; the synthetic design assertion covers custody only."""

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
                "actor_fact_quote": "Journal user",
                "event_quote": "Journal user records a health episode",
                "action_verb_quote": "records",
                "target_quote": "health episode",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Episode Ledger",
                "owner_system_quote": "Episode Ledger",
                "event_quote": "Episode Ledger records symptoms and relief attempts",
                "action_verb_quote": "records",
                "target_quote": "symptoms and relief attempts",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Trend Board",
                "owner_system_quote": "Trend Board",
                "event_quote": f"Trend Board shows a {visible_result}",
                "action_verb_quote": "shows",
                "target_quote": visible_result,
                "visible_result_quote": visible_result,
            },
        ],
        responsibility_owners=["Episode Ledger", "Trend Board"],
    )

    _assert_structural_design_projection_preserves_source(proposal)
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
                "actor_fact_quote": "Floor operator",
                "event_quote": "Floor operator reports a blocked aisle",
                "action_verb_quote": "reports",
                "target_quote": "blocked aisle",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Safety Ledger",
                "owner_system_quote": "Safety Ledger",
                "event_quote": "Safety Ledger records the stop decision and corrective action",
                "action_verb_quote": "records",
                "target_quote": "stop decision and corrective action",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Recovery Board",
                "owner_system_quote": "Recovery Board",
                "event_quote": f"Recovery Board shows {visible_result}",
                "action_verb_quote": "shows",
                "target_quote": visible_result,
                "visible_result_quote": visible_result,
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
    """Check source isolation; the synthetic design assertion covers custody only."""

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
                "actor_fact_quote": "Coordinator",
                "event_quote": "Coordinator completes onboarding and acknowledgement",
                "action_verb_quote": "completes",
                "target_quote": "onboarding and acknowledgement",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Goal Planner",
                "owner_system_quote": "Goal Planner",
                "event_quote": "Goal Planner records a starting plan target",
                "action_verb_quote": "records",
                "target_quote": "starting plan target",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Progress Ledger",
                "owner_system_quote": "Progress Ledger",
                "event_quote": "Progress Ledger records seven days of progress",
                "action_verb_quote": "records",
                "target_quote": "seven days of progress",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Reminder Board",
                "owner_system_quote": "Reminder Board",
                "event_quote": "Reminder Board shows an adjusted plan target and one follow-up reminder",
                "action_verb_quote": "shows",
                "target_quote": "adjusted plan target and one follow-up reminder",
                "visible_result_quote": "adjusted plan target and one follow-up reminder",
            },
        ],
        responsibility_owners=["Goal Planner", "Progress Ledger", "Reminder Board"],
    )

    _assert_structural_design_projection_preserves_source(proposal)
    assert [
        (row["actor_kind"], row["actor_fact_quote"])
        for row in proposal["intent"]["authored_semantics"]["first_path_relations"]
    ] == [
        ("human", "Coordinator"),
        ("product", "Goal Planner"),
        ("product", "Progress Ledger"),
        ("product", "Reminder Board"),
    ]
    rendered = str({
        "project_brief": proposal["project_brief"],
        "diagrams": proposal["diagrams"],
    })
    assert all(value in rendered for value in proposal["intent"]["component_responsibilities"])
    structural_design = str(
        proposal["intent"]["authored_semantics"]["provisional_design"]
    ).casefold()
    assert all(
        leaked not in structural_design
        for leaked in ("harbor", "berth", "cargo", "calibration", "symptom")
    )


def test_sparse_source_facts_remain_visible_with_structural_design_projection(
    tmp_path: Path,
) -> None:
    human_event = {
        "actor_kind": "human",
        "actor_fact_quote": "Dock attendant",
        "event_quote": "Dock attendant submits a request",
        "action_verb_quote": "submits",
        "target_quote": "request",
        "visible_result_quote": "",
    }
    intake_event = {
        "actor_kind": "product",
        "actor_fact_quote": "Intake Board",
        "owner_system_quote": "Intake Board",
        "event_quote": "Intake Board records the request",
        "action_verb_quote": "records",
        "target_quote": "request",
        "visible_result_quote": "",
    }
    receipt_event = {
        "actor_kind": "product",
        "actor_fact_quote": "Receipt Ledger",
        "owner_system_quote": "Receipt Ledger",
        "event_quote": "Receipt Ledger publishes a signed request receipt",
        "action_verb_quote": "publishes",
        "target_quote": "signed request receipt",
        "visible_result_quote": "signed request receipt",
    }
    intake_result_event = {
        **receipt_event,
        "actor_fact_quote": "Intake Board",
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
            "Vessel Registry",
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
            "Publish the signed request receipt.",
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
            "Retain the signed request receipt.",
        ),
    )
    for name, arguments, retained_fact in cases:
        case_root = tmp_path / name
        case_root.mkdir()
        proposal = _sparse_proposal(case_root, **arguments)
        assert [row["workstream_role"] for row in proposal["backlog"]] == [
            "provisional_design"
        ] * 4
        assert len(proposal["diagrams"]) == 5
        visible_package = str({
            "project_brief": proposal["project_brief"],
            "diagrams": proposal["diagrams"],
            "semantic_model": proposal["semantic_model"],
        })
        assert retained_fact in visible_package
        visible_copy = "\n".join(
            str(proposal["backlog"][0][field])
            for field in ("problem", "customer", "opportunity", "product_view")
        ).lower()
        assert "none accepted" not in visible_copy
        assert "reviewers" not in visible_copy
        _assert_structural_design_projection_preserves_source(proposal)
