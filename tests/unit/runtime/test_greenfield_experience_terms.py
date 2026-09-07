from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_experience import (
    _implementation_prompt,
    build_next_steps,
)
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
)


def test_implementation_handoff_preserves_exact_authored_release_requirements(
    tmp_path: Path,
) -> None:
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    created = [
        {"idea_id": f"B-{index:03d}", "title": str(row["title"]),
         "idea_path": str(tmp_path / f"workstream-{index}.md")}
        for index, row in enumerate(proposal["backlog"], start=1)
    ]
    workstream_ids = [str(row["idea_id"]) for row in created]

    next_steps = build_next_steps(
        proposal=proposal,
        backlog_result={"created": created},
        first_release_workstreams=workstream_ids,
        release_selector="0.0.1",
    )

    prompt = next_steps["implementation_prompt"]
    assert proposal["intent"]["first_path"] in prompt
    assert proposal["intent"]["proof_boundary"] in prompt
    assert "first_wave" not in next_steps
    assert "program" not in " ".join(next_steps["operator_sequence"]).casefold()
    assert "wave" not in " ".join(next_steps["operator_sequence"]).casefold()


@pytest.mark.parametrize("proof", ["Ω-Receipt", "Ω-Receipt with the operator signature"])
def test_implementation_handoff_preserves_proof_under_separate_scope_labels(proof: str) -> None:
    first_path = "The operator records Ω-Receipt"
    prompt = _implementation_prompt(
        target={"workstream_id": "B-701", "workstream_title": "Receipt capture",
                "deliverable": "Record Ω-Receipt", "verification": "Read Ω-Receipt"},
        first_path=first_path, release_requirements=proof,
    )
    assert first_path in prompt
    assert proof in prompt
    assert f"Release proof boundary:\n{proof}" in prompt
    assert "Selected workstream deliverable:\nRecord Ω-Receipt" in prompt
