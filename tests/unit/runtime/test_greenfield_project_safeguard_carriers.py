from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_apply_components
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
    StructuredAuthoringProvider,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


SAFEGUARD_ASSUMPTION = (
    "Sensitive household information should be visible only to assigned intake staff."
)
COMPONENT_VERIFICATION = "Read back the exact test value assigned to boundary 1."
WORKSTREAM_VERIFICATION = "An independent read returns the test value from boundary 1."


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
    assert WORKSTREAM_VERIFICATION in first_workstream["radar_sections"]["Test Strategy"]
    assert SAFEGUARD_ASSUMPTION in first_workstream["radar_sections"]["Assumptions"]
    assert COMPONENT_VERIFICATION in rendered_specs["Structural test boundary 1"]
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

    assert proposal["risks"] == []
    assert proposal["security_compliance"] == {}
    assert SAFEGUARD_ASSUMPTION not in proposal["intent"]["operational_constraints"]
    assert SAFEGUARD_ASSUMPTION not in proposal["intent"]["evidence_requirements"]


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


def _proposal(tmp_path: Path, *, include_assumption: bool = True) -> dict[str, object]:
    source = _source()
    response = _response(source)
    response["result"]["assumptions"] = (
        [{"applies_to": "general", "statement": SAFEGUARD_ASSUMPTION}]
        if include_assumption
        else []
    )
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(response),
        authoring_timeout_seconds=60,
        authoring_profile_id=STANDARD_PROFILE_ID,
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
