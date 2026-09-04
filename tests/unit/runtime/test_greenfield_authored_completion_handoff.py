"""Contract proof for direct model-authored completion handoff projection."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    GreenfieldAuthoredSemanticsError,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    render_coding_readiness_gates,
)


def _typed_relation(
    *,
    path: str,
    event: str,
    order: int,
    actor_kind: str,
    actor_quote: str,
    action_verb_quote: str,
    target_quote: str,
    visible_result_quote: str = "",
) -> dict[str, object]:
    path_bytes = path.encode("utf-8")
    event_bytes = event.encode("utf-8")
    event_start = path_bytes.index(event_bytes)
    return {
        "order": order,
        "source_start_byte": event_start,
        "source_end_byte": event_start + len(event_bytes),
        "event_start_byte": event_start,
        "event_end_byte": event_start + len(event_bytes),
        "actor_kind": actor_kind,
        "actor_quote": actor_quote,
        "actor_is_carried": actor_quote not in event,
        "actor_fact_path": "/title" if actor_kind == "product" else "/human_actors/0",
        "actor_fact_quote": "Harbor Desk" if actor_kind == "product" else "Dock attendant Ivo",
        "owner_system_path": "/title" if actor_kind == "product" else "",
        "owner_system_quote": "Harbor Desk" if actor_kind == "product" else "",
        "event_quote": event,
        "action_verb_quote": action_verb_quote,
        "target_quote": target_quote,
        "visible_result_quote": visible_result_quote,
        "recovery_path": False,
    }


def test_authored_handoff_preserves_verified_fields_without_legacy_reconstruction(
) -> None:
    first_path = (
        "Dock attendant Ivo enters a vessel tag, the product records berth occupancy, "
        "and the berth map shows the placement with the complete source-owned retention receipt"
    )
    proof_boundary = "Verify the placement and retention receipt"
    success_metrics = [
        "Berth placement stays visible",
        "Retention receipt stays source-owned",
        "Replay preserves the accepted placement",
        "Missing tags remain blocked",
        "Invalid tags return a reviewable result",
        "Handoff evidence names the berth",
        "Operator review preserves **APIv7** exactly",
    ]
    relations = (
        _typed_relation(
            path=first_path,
            event="Dock attendant Ivo enters a vessel tag",
            order=1,
            actor_kind="human",
            actor_quote="Dock attendant Ivo",
            action_verb_quote="enters",
            target_quote="a vessel tag",
        ),
        _typed_relation(
            path=first_path,
            event="the product records berth occupancy",
            order=2,
            actor_kind="product",
            actor_quote="Harbor Desk",
            action_verb_quote="records",
            target_quote="berth occupancy",
        ),
        _typed_relation(
            path=first_path,
            event=(
                "the berth map shows the placement with the complete source-owned retention receipt"
            ),
            order=3,
            actor_kind="product",
            actor_quote="Harbor Desk",
            action_verb_quote="shows",
            target_quote="the placement",
            visible_result_quote=(
                "the placement with the complete source-owned retention receipt"
            ),
        ),
    )
    proposal = {
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "intent": {
            "title": "Harbor Desk",
            "first_path": first_path,
            "proof_boundary": proof_boundary,
            "human_actors": ["Dock attendant Ivo"],
            "internal_systems": [],
            "evidence_requirements": ["Source evidence preserves berth history"],
            "operational_constraints": [],
            "non_goals": [],
            "success_metrics": success_metrics,
            "authored_semantics": authored_semantics_mapping(
                relations,
                (
                    {
                        "responsibility_path": "/first_path",
                        "responsibility_quote": (
                            "the placement with the complete source-owned retention receipt"
                        ),
                        "owner_system_path": "/title",
                        "owner_system_quote": "Harbor Desk",
                        "first_path_event_order": 3,
                        "responsibility_source": "terminal_visible_result",
                    },
                ),
            ),
        },
        "project_brief": {
            "customization_options": [],
            "coding_readiness_gates": [proof_boundary, "Source evidence preserves berth history"],
        },
        "backlog": [
            {
                "title": "Deliver Harbor Desk",
                "recommended_first_slice": first_path,
                "validation": [proof_boundary],
                "success_metrics": ["The berth map shows the placement"],
            }
        ],
    }
    backlog_result = {
        "created": [{"idea_id": "B-001", "title": "Deliver Harbor Desk"}],
    }

    for name in (
        "_first_path_summary",
        "_first_release_requirement_sentence",
        "_preview_safe_fragment",
        "_semantic_anchor_gate",
    ):
        assert not hasattr(greenfield_experience, name)

    handoff = greenfield_experience.build_next_steps(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=("B-001",),
        release_selector="0.0.1",
    )

    assert first_path in handoff["implementation_prompt"]
    assert proof_boundary in handoff["implementation_prompt"]
    readiness_contract = handoff["coding_readiness_contract"]
    assert readiness_contract["source_facts"]["accepted_first_path"] == first_path
    assert readiness_contract["source_facts"]["proof_boundary"] == proof_boundary
    assert readiness_contract["source_facts"]["evidence_requirements"] == (
        "Source evidence preserves berth history",
    )
    assert handoff["coding_readiness_gates"] == render_coding_readiness_gates(
        readiness_contract
    )
    assert handoff["validation_gates"] == [
        proof_boundary,
        *success_metrics,
        "The berth map shows the placement",
    ]

    proposal["components"] = [
        {
            "component_id": "harbor-desk",
            "label": "Harbor Desk",
            "component_contract": {
                "owner_system": "Harbor Desk",
                "responsibility_facts": [
                    "the placement with the complete source-owned retention receipt"
                ],
            },
        }
    ]
    component_handoff = greenfield_experience.build_component_handoffs(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=("B-001",),
        traceability_plan=SimpleNamespace(
            component_workstreams={"harbor-desk": ("B-001",)}
        ),
        release_selector="0.0.1",
    )["harbor-desk"]
    assert component_handoff["accepted_first_path"] == first_path
    assert component_handoff["proof_boundary"] == proof_boundary
    assert component_handoff["first_slice"] == first_path
    assert component_handoff["success_metrics"] == success_metrics
    assert component_handoff["validation_gates"] == [
        proof_boundary,
        "The berth map shows the placement",
        *success_metrics,
    ]
    assert component_handoff["component_contract"] == proposal["components"][0][
        "component_contract"
    ]


def test_authored_handoff_rejects_relation_free_proposals() -> None:
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        greenfield_experience.build_next_steps(
            proposal={"intent": {"title": "Legacy"}},
            backlog_result={"created": []},
            first_release_workstreams=(),
            release_selector="0.0.1",
        )
