"""Cited source excerpts are not promoted into standalone authored prose."""

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import preview_project_dashboard_payload
from odylith.runtime.domain_intelligence.greenfield_authored_atlas_view import _product_boundary_projection
from odylith.runtime.domain_intelligence.greenfield_authored_memory import render_authored_project_brief_lines
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import render_candidate_intent_markdown
from tests.unit.runtime.test_greenfield_authored_project_dashboard import (
    _accepted_preview,
    _proposal,
    _source_launch_context,
)


@pytest.mark.parametrize("excerpt", [
    "lets coordinators preserve review evidence",
    "A café ledger preserves Ω receipts.",
    "for café evidence\nand exact APIv7 receipts",
])
def test_source_excerpt_labels_cover_all_product_story_views(
    tmp_path: Path, excerpt: str,
) -> None:
    intent = deepcopy(_proposal()["intent"])
    intent["product_story"] = excerpt
    before = deepcopy(intent)
    proposal = build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1", confirmed_intent=intent,
    )
    preview = render_candidate_intent_markdown(intent)
    assert f"## Source excerpt\n“{excerpt}”\n" in preview
    assert "## Product story\n" not in preview

    brief = "\n".join(render_authored_project_brief_lines(proposal["project_brief"]))
    assert f"- Source excerpt: “{excerpt}”" in brief
    assert f"- principle: {excerpt}" not in brief
    assert f"- Product outcome: {excerpt}" not in brief
    sections = proposal["project_brief"]["blueprint_sections"]
    assert sections[0]["section"] == "Source excerpt"
    assert sections[0]["must_capture"] == excerpt

    _, boxes, _ = _product_boundary_projection(
        title=intent["title"], product_story=excerpt, components=[],
    )
    assert boxes[0]["role"] == "Source excerpt"
    assert boxes[0]["description"] == f"Source excerpt: “{excerpt}”"

    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal,
        accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    display = f"Source excerpt: “{excerpt}”"
    assert payload["intro"] == display
    assert display in payload["known"]
    assert payload["product_story"]["paragraphs"][0] == display
    assert payload["product_story_title"] == "Project overview"
    assert next(row for row in payload["claim_evidence"] if row["claim"] == "Source excerpt")["value"] == excerpt
    assert proposal["project_intelligence"]["purpose"] == display
    assert display in proposal["project_intelligence"]["intent"]

    assert intent == before
    assert proposal["intent"]["product_story"] == excerpt
    assert payload["authored_facts"]["product_story"] == excerpt
    assert proposal["intent"]["authored_semantics"] == before["authored_semantics"]
