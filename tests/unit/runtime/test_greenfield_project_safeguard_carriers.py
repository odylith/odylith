from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import (
    greenfield_apply_components, greenfield_authored_component_spec, proposal_tribunal,
)
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import (
    preview_accepted_project_memory,
    preview_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_experience import build_next_steps
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.proposal_memory import (
    build_project_brief_source_markdown,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    RemainingCandidateProvider,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


SAFEGUARD_ASSUMPTION = (
    "Sensitive household information should be visible only to assigned intake staff."
)
COMPONENT_VERIFICATION = "Read back the exact test value assigned to boundary 1."
WORKSTREAM_VERIFICATION = "An independent read returns the test value from boundary 1."
RISK_STATEMENT = "Sensitive household information could be exposed outside assigned intake staff."
RISK_VERIFICATION = "Verify unassigned users cannot read the household record."


def test_project_carriers_preserve_advisory_safeguards_without_source_promotion(
    tmp_path: Path,
) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _backlog_result(proposal)
    next_steps = build_next_steps(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=[row["idea_id"] for row in backlog_result["created"]],
        release_selector="0.0.1",
    )
    accepted_project = preview_accepted_project_memory(
        root=tmp_path,
        target_root=tmp_path,
        proposal=proposal,
        backlog_result=backlog_result,
        component_items=proposal["components"],
        release_selector="0.0.1",
        release_target_result=None,
        release_assignment_result=None,
        validation_gate=None,
        source_launch_context=next_steps,
    )
    dashboard = preview_project_dashboard_payload(
        root=tmp_path,
        proposal=proposal,
        accepted_project_preview=accepted_project,
        source_launch_context=next_steps,
    )
    brief = build_project_brief_source_markdown(
        proposal=proposal,
        backlog_items=backlog_result["created"],
        component_items=proposal["components"],
        diagram_ids=[row["slug"] for row in proposal["diagrams"]],
        release_selector="0.0.1",
        release_id="0.0.1",
    )
    rendered_specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=backlog_result,
    )

    preview = f"General assumption — {SAFEGUARD_ASSUMPTION}"
    assumption_section = next(
        row
        for row in proposal["project_brief"]["blueprint_sections"]
        if row["section"] == "Proposed assumptions"
    )
    assert dashboard["open"] == [SAFEGUARD_ASSUMPTION]
    assert assumption_section["must_capture"] == preview
    assert "Advisory and unverified" in assumption_section["why_it_matters"]
    assert proposal["project_intelligence"]["assumptions"] == [preview]
    assert SAFEGUARD_ASSUMPTION in brief
    assert not any(
        SAFEGUARD_ASSUMPTION in gate
        for gate in proposal["project_brief"]["coding_readiness_gates"]
    )
    assert proposal["project_intelligence"]["source_of_truth_map"] == []
    assert SAFEGUARD_ASSUMPTION not in json.dumps(proposal[PRODUCT_INTENT_AUTHORITY_KEY])

    first_workstream = proposal["backlog"][0]
    assert WORKSTREAM_VERIFICATION in first_workstream["radar_sections"]["Validation"]
    assert COMPONENT_VERIFICATION in first_workstream["radar_sections"]["Test Strategy"]
    assert first_workstream["radar_sections"]["Test Strategy"] != (
        first_workstream["radar_sections"]["Validation"]
    )
    assert "Assumptions" not in first_workstream["radar_sections"]
    assert SAFEGUARD_ASSUMPTION not in json.dumps(first_workstream)
    assert RISK_STATEMENT in first_workstream["radar_sections"]["Risks"]
    assert COMPONENT_VERIFICATION in rendered_specs["Structural test boundary 1"]
    assert RISK_STATEMENT in rendered_specs["Structural test boundary 1"]
    assert WORKSTREAM_VERIFICATION in next_steps["implementation_prompt"]
    assert any(
        row["title"] == "Proposed Delivery Dependencies and Acceptance"
        and WORKSTREAM_VERIFICATION in json.dumps(row["diagram_boxes"])
        for row in proposal["diagrams"]
    )
    assert any(
        row["title"] == "Proposed Capability Support and Source Facts"
        and COMPONENT_VERIFICATION in json.dumps(row["diagram_boxes"])
        for row in proposal["diagrams"]
    )

    response_risk = proposal["intent"]["authored_semantics"]["provisional_design"][
        "risk_posture"
    ]["items"][0]
    assert set(response_risk) == {
        "key", "category", "statement", "trigger", "mitigation", "verification",
        "scope_paths",
    }
    assert proposal["risks"] == [response_risk]
    assert response_risk["statement"] == RISK_STATEMENT
    allocation = proposal["components"][0]["component_contract"]["risk_allocations"][0]
    assert set(allocation) == {"risk_ref", "risk_item"}
    assert allocation["risk_item"] == response_risk
    assert all(
        not row["component_contract"]["risk_allocations"]
        for row in proposal["components"][1:]
    )
    assert all(
        RISK_STATEMENT not in row["radar_sections"]["Risks"]
        for row in proposal["backlog"][1:]
    )
    assert all(
        RISK_STATEMENT not in rendered_specs[row["label"]]
        for row in proposal["components"][1:]
    )
    assert proposal["security_compliance"] == {
        "authority_kind": "provisional_design",
        "status": "material_risks_identified",
        "rationale": "The proposed household-data path has a material access boundary.",
        "risk_refs": [
            "/authored_semantics/provisional_design/risk_posture/items/0"
        ],
    }
    assert dashboard["risk_items"] == [{
        "risk": "Privacy risk",
        "meaning": (
            f"{RISK_STATEMENT}\nCategory: privacy\n"
            "Trigger: A user without an intake assignment requests the record.\n"
            "Mitigation: Require assignment-scoped authorization before disclosure.\n"
            f"Verification: {RISK_VERIFICATION}\nScope: Components: test-boundary-1; "
            "workstreams: test-work-1; source events: 1."
        ),
        "status": "material_risks_identified",
        "category": "privacy",
        "trigger": "A user without an intake assignment requests the record.",
        "mitigation": "Require assignment-scoped authorization before disclosure.",
        "verification": RISK_VERIFICATION,
        "scope": (
            "Components: test-boundary-1; workstreams: test-work-1; source events: 1."
        ),
    }]
    assert SAFEGUARD_ASSUMPTION not in proposal["intent"]["operational_constraints"]
    assert SAFEGUARD_ASSUMPTION not in proposal["intent"]["evidence_requirements"]


def test_component_spec_recomputes_risk_scope_and_rejects_synchronized_tampering(
    tmp_path: Path,
) -> None:
    proposal = _proposal(tmp_path)
    rows = greenfield_authored_component_spec.build_authored_component_authoring_inputs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(proposal),
    )
    forged = deepcopy(rows[0])
    forged_path = forged["component_contract"]["risk_allocations"][0]["risk_item"][
        "scope_paths"
    ][0]
    forged_path["event_order"] = 32
    forged_path["workstream_key"] = "invented-work"
    forged["risks"] = tuple(
        risk.replace("workstreams [test-work-1]", "workstreams [invented-work]").replace(
            "source events [1]", "source events [32]"
        )
        for risk in forged["risks"]
    )

    with pytest.raises(ValueError, match="risk differs from its canonical design row"):
        greenfield_authored_component_spec.build_authored_component_spec(forged)


def test_component_spec_rejects_valid_path_substitution_with_synchronized_text(
    tmp_path: Path,
) -> None:
    proposal = _proposal(tmp_path)
    rows = greenfield_authored_component_spec.build_authored_component_authoring_inputs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(proposal),
    )
    forged = deepcopy(rows[0])
    forged["component_contract"]["risk_allocations"][0]["risk_item"]["scope_paths"][0][
        "event_order"
    ] = 2
    forged["risks"] = tuple(
        risk.replace("source events [1]", "source events [2]") for risk in forged["risks"]
    )

    with pytest.raises(ValueError, match="risk differs from its canonical design row"):
        greenfield_authored_component_spec.build_authored_component_spec(forged)


def test_component_spec_rejects_out_of_range_canonical_risk_reference(
    tmp_path: Path,
) -> None:
    proposal = _proposal(tmp_path)
    rows = greenfield_authored_component_spec.build_authored_component_authoring_inputs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(proposal),
    )
    forged = deepcopy(rows[0])
    forged["component_contract"]["risk_allocations"][0]["risk_ref"] = (
        "/authored_semantics/provisional_design/risk_posture/items/99"
    )

    with pytest.raises(ValueError, match="risk reference is outside canonical design"):
        greenfield_authored_component_spec.build_authored_component_spec(forged)


def test_component_spec_rejects_noncanonical_risk_reference_index(
    tmp_path: Path,
) -> None:
    proposal = _proposal(tmp_path)
    rows = greenfield_authored_component_spec.build_authored_component_authoring_inputs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(proposal),
    )
    forged = deepcopy(rows[0])
    forged["component_contract"]["risk_allocations"][0]["risk_ref"] = (
        "/authored_semantics/provisional_design/risk_posture/items/00"
    )

    with pytest.raises(ValueError, match="invalid proposed risk references"):
        greenfield_authored_component_spec.build_authored_component_spec(forged)


def test_synchronized_risk_scope_tampering_breaks_projection_parity(tmp_path: Path) -> None:
    proposal = deepcopy(_proposal(tmp_path))
    forged_path = proposal["components"][0]["component_contract"]["risk_allocations"][0][
        "risk_item"
    ]["scope_paths"][0]
    forged_path["event_order"] = 32
    forged_path["workstream_key"] = "invented-work"
    proposal["components"][0]["risks"] = [
        risk.replace("workstreams [test-work-1]", "workstreams [invented-work]").replace(
            "source events [1]", "source events [32]"
        )
        for risk in proposal["components"][0]["risks"]
    ]

    decision = proposal_tribunal.run_greenfield_tribunal(
        proposal, release_selector="0.0.1",
    )

    assert not decision.passed


def test_empty_assumptions_keep_project_carriers_empty(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path, include_assumption=False)

    assert proposal["assumptions"] == []
    assert proposal["project_intelligence"]["assumptions"] == []
    assert not any(
        row["section"] == "Proposed assumptions"
        for row in proposal["project_brief"]["blueprint_sections"]
    )
    assert not any(
        "assumption" in gate.lower()
        for gate in proposal["project_brief"]["coding_readiness_gates"]
    )


@pytest.mark.parametrize(
    "mutate",
    (
        lambda proposal: proposal["risks"].clear(),
        lambda proposal: proposal["security_compliance"]["risk_refs"].clear(),
        lambda proposal: proposal["components"][0]["component_contract"]["risk_allocations"].clear(),
        lambda proposal: proposal["backlog"][0]["radar_sections"].update(
            {"Risks": "No material risks were identified."}
        ),
    ),
)
def test_material_risk_projection_cannot_be_dropped_or_rewritten(
    tmp_path: Path, mutate,
) -> None:
    proposal = deepcopy(_proposal(tmp_path))
    mutate(proposal)

    decision = proposal_tribunal.run_greenfield_tribunal(
        proposal, release_selector="0.0.1",
    )

    assert not decision.passed


def _proposal(tmp_path: Path, *, include_assumption: bool = True) -> dict[str, object]:
    source = _source()
    response = _response(source)
    response["result"]["assumptions"] = (
        [{"applies_to": "general", "statement": SAFEGUARD_ASSUMPTION}]
        if include_assumption
        else []
    )
    response["result"]["provisional_design"]["risk_posture"] = {
        "status": "material_risks_identified",
        "rationale": "The proposed household-data path has a material access boundary.",
        "items": [
            {
                "key": "household-access",
                "category": "privacy",
                "statement": RISK_STATEMENT,
                "trigger": "A user without an intake assignment requests the record.",
                "mitigation": "Require assignment-scoped authorization before disclosure.",
                "verification": RISK_VERIFICATION,
                "scope_paths": [{
                    "event_order": 1,
                    "component_key": "test-boundary-1",
                    "workstream_key": "test-work-1",
                }],
            }
        ],
    }
    provider = RemainingCandidateProvider(response)
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=provider,
        authoring_timeout_seconds=60,
        authoring_profile_id=STANDARD_PROFILE_ID,
        participant_provider_factory=provider.participant_provider,
        review_provider_factory=AdmittingReviewProvider,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1",
        confirmed_intent=candidate,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = candidate[PRODUCT_INTENT_AUTHORITY_KEY]
    return proposal


def _backlog_result(proposal: dict[str, object]) -> dict[str, list[dict[str, str]]]:
    return {
        "created": [
            {
                "idea_id": f"B-{index:03d}",
                "title": row["title"],
                "idea_path": f"odylith/radar/source/B-{index:03d}.md",
            }
            for index, row in enumerate(proposal["backlog"], start=1)
        ]
    }
