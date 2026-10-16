"""Assessment projections preserve unknown judgments and authored dependencies."""

from pathlib import Path

import pytest

from odylith.runtime.governance import backlog_assessment
from odylith.runtime.surfaces import backlog_detail_pages
from odylith.runtime.surfaces import render_backlog_ui_payload_runtime as payload_runtime
from tests.unit.runtime.test_render_backlog_ui import _seed_backlog_render_repo


DEPENDENCY_REASON = (
    "The review workstream depends on the record workstream because reviewers need the original "
    "custody references, the failed-run observations, and the complete exception history before "
    "they can decide whether a submission contains sufficient evidence; a dependency does not "
    "mean the submission has passed qualification."
)


def assessment_entry(root: Path, *, unassessed: bool = True, rank: str = "1") -> dict[str, object]:
    _seed_backlog_render_repo(root)
    idea = root / "odylith/radar/source/ideas/2026-04/2026-04-11-cached-render.md"
    fields = {
        "priority": "P1", "ordering_score": "88", "commercial_value": "4",
        "product_impact": "4", "market_value": "4", "sizing": "M", "complexity": "Medium",
    }
    source = idea.read_text()
    if unassessed:
        for key, value in backlog_assessment.UNASSESSED_BACKLOG_METADATA.items():
            rendered = backlog_assessment.markdown_value(value)
            source = "\n".join(line for line in source.splitlines() if not line.startswith(key + ":"))
            source = f"{key}: {rendered}\n\n" + source
            if key in fields:
                fields[key] = rendered
    source = source.replace("prove cached radar render reuse", DEPENDENCY_REASON)
    idea.write_text(source)
    errors = []
    entry = payload_runtime._build_entry(
        repo_root=root, output_path=root / "odylith/radar/radar.html", section="active",
        payload={**fields, "idea_id": "B-777", "rank": rank, "title": "Review complete source evidence",
                 "status": "queued", "link": f"[spec]({idea})"},
        rationale_map={"B-777": [DEPENDENCY_REASON]}, errors=errors,
    )
    assert not errors
    assert entry is not None
    return entry


@pytest.mark.parametrize("unassessed", [True, False])
def test_payload_and_standalone_spec_preserve_assessment(tmp_path: Path, unassessed: bool) -> None:
    entry = assessment_entry(tmp_path, unassessed=unassessed)
    for projection in (entry, payload_runtime._build_backlog_summary_entry(entry),
                       payload_runtime._build_backlog_detail_entry(entry)):
        assert projection["ordering_score"] == (None if unassessed else 88)
        assert projection["rank_num"] == (None if unassessed else 1)
        for key in ("commercial_value", "product_impact", "market_value"):
            assert projection[key] == (None if unassessed else 4)
        assert projection["assessment_status"] == ("unassessed" if unassessed else "assessed")
    assert entry["ordering_rationale"] == DEPENDENCY_REASON
    assert entry["rationale_bullets"] == [DEPENDENCY_REASON]
    html = backlog_detail_pages._render_idea_spec_html(
        repo_root=tmp_path, index_output_path=tmp_path / "odylith/radar/radar.html", entry=entry,
    )
    assert DEPENDENCY_REASON in html
    if unassessed:
        assert "Provisional Greenfield design" in html
        assert html.count("Not assessed") >= 7
        assert "Score None" not in html
        assert entry["rank"] == "unassessed"
    else:
        assert "Score 88" in html
        assert "Not assessed" not in html


def test_execution_ordinal_can_remain_absent(tmp_path: Path) -> None:
    assert assessment_entry(tmp_path, unassessed=False, rank="-")["rank_num"] is None
