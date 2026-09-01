"""Authored-only Greenfield proposal and projection contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_validation import validate_host_reasoned_proposal
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
)


def _proposal(repo_root: Path) -> dict[str, object]:
    return _canonical_model_authored_greenfield_fixture(repo_root)


def _created_backlog(proposal: dict[str, object], repo_root: Path) -> list[dict[str, str]]:
    rows = proposal.get("backlog")
    assert isinstance(rows, list)
    return [
        {
            "idea_id": f"B-{index:03d}",
            "title": str(row["title"]),
            "idea_path": str(repo_root / f"odylith/radar/source/ideas/B-{index:03d}.md"),
        }
        for index, row in enumerate(rows, start=1)
        if isinstance(row, dict)
    ]


def test_authored_proposal_passes_exact_validation_and_tribunal(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    validate_host_reasoned_proposal(proposal)
    decision = run_greenfield_tribunal(proposal)

    assert proposal["projection_origin"] == AUTHORED_PROJECTION_ORIGIN
    assert decision.passed
    assert decision.issues == ()
    assert set(decision.dimensions) == {
        "typed_intent",
        "artifact_topology",
        "semantic_projection",
        "provenance",
    }


def test_authored_proposal_tampering_fails_exact_projection_parity(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog = [dict(row) for row in proposal["backlog"]]  # type: ignore[index]
    backlog[0]["title"] = "Tampered title"
    drifted = {**proposal, "backlog": backlog}

    with pytest.raises(ValueError, match="projection drifted from sealed typed intent"):
        validate_host_reasoned_proposal(drifted)
    decision = run_greenfield_tribunal(drifted)
    assert not decision.passed
    assert any("exactly match" in issue for issue in decision.issues)


def test_non_authored_proposals_fail_closed_at_each_semantic_boundary(tmp_path: Path) -> None:
    proposal = {"mode": "host_reasoned_greenfield_proposal", "intent": {}}

    with pytest.raises(ValueError, match="sealed authored projection"):
        validate_host_reasoned_proposal(proposal)
    with pytest.raises(ValueError, match="sealed authored projection"):
        run_greenfield_tribunal(proposal)
    with pytest.raises(ValueError, match="sealed authored projection"):
        greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=(),
            diagram_ids=(),
        )
    with pytest.raises(ValueError, match="sealed authored projection"):
        build_greenfield_payload(proposal=proposal, repo_root=tmp_path)


def test_traceability_uses_only_exact_authored_references(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    diagrams = proposal["diagrams"]
    assert isinstance(diagrams, list)
    diagram_ids = tuple(f"D-{index:03d}" for index in range(1, len(diagrams) + 1))

    plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=_created_backlog(proposal, tmp_path),
        diagram_ids=diagram_ids,
    )

    assert len(plan.workstreams) == len(proposal["backlog"])  # type: ignore[arg-type]
    assert tuple(link.diagram_id for link in plan.diagram_links) == diagram_ids
    assert all(link.related_workstream_ids for link in plan.diagram_links)
    assert all(link.related_backlog_paths for link in plan.diagram_links)
    assert all(plan.component_workstreams.values())


def test_authored_project_dashboard_preserves_the_sealed_product_view(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    payload = build_greenfield_payload(proposal=proposal, repo_root=tmp_path)

    intent = proposal["intent"]
    assert isinstance(intent, dict)
    assert payload["title"] == intent["title"]
    assert payload["projection"]["origin"] == AUTHORED_PROJECTION_ORIGIN
    assert payload["product_story"]
