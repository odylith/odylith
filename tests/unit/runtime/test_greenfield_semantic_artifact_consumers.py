from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_semantic_backlog_projection import (
    semantic_backlog_rows,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_component_package import (
    render_semantic_component_specs,
    semantic_component_authoring_inputs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_diagrams import (
    semantic_diagrams,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_memory import (
    semantic_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    build_semantic_projection_plan,
    semantic_projection_plan_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_traceability import (
    build_semantic_traceability_plan,
)
from tests.unit.runtime.test_greenfield_semantic_projection_plan import (
    _two_state_graph,
)


def test_artifact_consumers_preserve_every_planned_state_and_output(
    tmp_path: Path,
) -> None:
    plan = build_semantic_projection_plan(
        _two_state_graph(),
        project_slug="review-flow",
    )
    backlog = semantic_backlog_rows(
        plan=plan,
        problem="A typed review flow needs delivery.",
        customer="The review operator.",
        opportunity="Deliver the accepted intake and decision flow.",
        product_view="A graph-native review flow.",
        success_metrics=("Both accepted outputs are visible.",),
        proof_boundary="Both accepted states and outputs retain exact custody.",
    )
    diagrams = semantic_diagrams(plan=plan, backlog=backlog)
    proposal = {
        "projection_plan": semantic_projection_plan_mapping(plan),
        "components": list(plan.components),
        "backlog": backlog,
        "diagrams": diagrams,
        "risks": [],
    }
    created = [
        {
            **row,
            "idea_id": f"B-{index:03d}",
            "idea_path": str(tmp_path / f"B-{index:03d}.md"),
        }
        for index, row in enumerate(backlog, 1)
    ]
    reversed_created = list(reversed(created))
    diagram_ids = tuple(f"D-{index:03d}" for index in range(1, len(diagrams) + 1))

    authoring_inputs = semantic_component_authoring_inputs(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={"created": reversed_created},
        diagram_ids=diagram_ids,
    )
    rendered_specs = render_semantic_component_specs(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={"created": reversed_created},
        diagram_ids=diagram_ids,
    )
    traceability = build_semantic_traceability_plan(
        proposal=proposal,
        created_backlog=reversed_created,
        diagram_ids=diagram_ids,
    )
    dashboard = semantic_project_dashboard_payload(
        proposal=proposal,
        accepted_project={
            "accepted_at": "prewrite",
            "created": {"workstreams": reversed_created},
        },
        source_launch={"start_workstream_title": backlog[1]["title"]},
    )

    contracts = {
        row["component_id"]: row["component_contract"]
        for row in authoring_inputs
    }
    assert contracts["intake-service"]["state_objects"] == ("Intake record",)
    assert contracts["intake-service"]["visible_outputs"] == ("Intake receipt",)
    assert contracts["decision-service"]["state_objects"] == ("Decision record",)
    assert contracts["decision-service"]["visible_outputs"] == ("Decision notice",)
    assert all(
        {
            "owned_state",
            "produced_outputs",
            "states_or_transitions",
            "state_object",
            "visible_output",
        }.isdisjoint(contract)
        for contract in contracts.values()
    )
    assert all(
        {"wave_label", "wave_status"}.isdisjoint(row["implementation_handoff"])
        for row in authoring_inputs
    )

    rendered = "\n".join(rendered_specs.values())
    for label in (
        "Intake record",
        "Decision record",
        "Intake receipt",
        "Decision notice",
    ):
        assert label in rendered
    for row in authoring_inputs:
        workstream_id = row["implementation_handoff"]["workstream_id"]
        assert (
            f"(Plan: [{workstream_id}]"
            f"(odylith/radar/radar.html?view=plan&workstream={workstream_id}))"
        ) in rendered_specs[row["label"]]
    cards = {
        row["label"]: row["body"]
        for row in dashboard["product_story"]["release_contract"]
    }
    assert cards["State Objects"] == "Intake record; Decision record"
    assert cards["Visible Outputs"] == "Intake receipt; Decision notice"
    assert dashboard["artifact_depth"] == {
        "workstreams": 3,
        "components": 2,
        "diagrams": 3,
        "state_objects": 2,
        "visible_outputs": 2,
    }
    assert [row.title for row in traceability.workstreams] == [
        row["title"] for row in backlog
    ]
    assert len(traceability.workstreams) == len(plan.workstream_plans) == 3
