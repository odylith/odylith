"""Contract proof for canonical selected-slice and release-context handoffs."""

from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence.greenfield_authored_first_run import authored_first_run_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import GreenfieldAuthoredSemanticsError
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import render_coding_readiness_gates
from tests.unit.runtime.greenfield_authored_proposal_fixtures import _canonical_model_authored_greenfield_fixture


def test_authored_handoff_preserves_verified_fields_without_legacy_reconstruction(tmp_path: Path) -> None:
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    created = [
        {"idea_id": f"B-{index:03d}", "title": row["title"],
         "idea_path": str(tmp_path / f"workstream-{index}.md")}
        for index, row in enumerate(proposal["backlog"], 1)
    ]
    handoff = greenfield_experience.build_next_steps(
        proposal=proposal, backlog_result={"created": created},
        first_release_workstreams=tuple(row["idea_id"] for row in created),
        release_selector="0.0.1",
    )
    intent = proposal["intent"]
    selected = intent["authored_semantics"]["provisional_design"]["workstreams"][0]
    proposed_run = authored_first_run_text(intent)
    assert proposed_run in handoff["implementation_prompt"]
    assert intent["proof_boundary"] in handoff["implementation_prompt"]
    assert selected["deliverable"] in handoff["implementation_prompt"]
    assert selected["verification"] in handoff["implementation_prompt"]
    readiness = handoff["coding_readiness_contract"]
    assert readiness["source_facts"]["accepted_first_path"] == proposed_run
    assert readiness["source_facts"]["proof_boundary"] == intent["proof_boundary"]
    assert readiness["source_facts"]["evidence_requirements"] == tuple(intent["evidence_requirements"])
    assert handoff["coding_readiness_gates"] == render_coding_readiness_gates(readiness)
    assert selected["verification"] in handoff["validation_gates"]
    assert intent["proof_boundary"] in handoff["release_validation_gates"]
    assert handoff["project_title"] == intent["title"]
    assert handoff["start_workstream_id"] == "B-001"
    for name in (
        "_first_path_summary", "_first_release_requirement_sentence", "_preview_safe_fragment",
        "_semantic_anchor_gate", "build_component_handoffs", "_project_context",
        "_candidate_start_ids", "_project_first_prompt", "_proposal_row_for_created_id",
    ):
        assert not hasattr(greenfield_experience, name)


def test_authored_handoff_rejects_relation_free_proposals() -> None:
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        greenfield_experience.build_next_steps(
            proposal={"intent": {"title": "Legacy"}}, backlog_result={"created": []},
            first_release_workstreams=(), release_selector="0.0.1",
        )
