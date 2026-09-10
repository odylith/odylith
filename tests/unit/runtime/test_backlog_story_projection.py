"""Radar previews project authored blocks without rewriting their claims."""

import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import render_backlog_ui_html_runtime as html_runtime
from odylith.runtime.surfaces import render_backlog_ui_payload_runtime as payload_runtime
from tests.unit.runtime.test_render_backlog_ui import _seed_backlog_render_repo


def story_entry(
    root: Path, sections: dict[str, str], *, prose_metadata: dict[str, str] | None = None,
    rationale: list[str] | None = None,
) -> dict[str, object]:
    _seed_backlog_render_repo(root)
    idea = root / "odylith/radar/source/ideas/2026-04/2026-04-11-cached-render.md"
    metadata = idea.read_text(encoding="utf-8").split("## Problem", 1)[0]
    for key, value in (prose_metadata or {}).items():
        metadata = "\n".join(line for line in metadata.splitlines() if not line.startswith(key + ":")) + f"\n{key}: {value}\n\n"
    idea.write_text(metadata + "\n\n".join(f"## {title}\n{body}" for title, body in sections.items()), encoding="utf-8")
    errors: list[str] = []
    entry = payload_runtime._build_entry(
        repo_root=root, output_path=root / "odylith/radar/radar.html", section="active",
        payload={
            "idea_id": "B-777", "rank": "1", "title": "Cached Radar Render", "priority": "P1",
            "ordering_score": "88", "commercial_value": "4", "product_impact": "4", "market_value": "4",
            "sizing": "M", "complexity": "Medium", "status": "queued", "link": f"[spec]({idea})",
        },
        rationale_map={"B-777": rationale or []}, errors=errors,
    )
    assert not errors
    assert entry is not None
    return entry


@pytest.mark.parametrize("solution", [
    "Proposed deliverable — Record the sample's initial custody entry.",
    "Proposed deliverable — Present the lot's failed stress-run evidence.",
])
def test_story_uses_workstream_deliverable_before_repeated_project_fields(tmp_path: Path, solution: str) -> None:
    entry = story_entry(tmp_path, {
        "Problem": "Assumption — One reviewable project record.",
        "Opportunity": "Assumption — Bring the project records together.",
        "Proposed Solution": solution,
    })
    assert entry["story_source"] == "Proposed Solution"
    assert entry["story_text"] == solution
    assert payload_runtime._build_backlog_summary_entry(entry)["story_text"] == solution
    assert payload_runtime._build_backlog_detail_entry(entry)["problem"] == "Assumption — One reviewable project record."


LONG_CONDITIONAL = (
    "Proposed deliverable — Keep the U.S. lab's 2.75-hour exposure record, its original custody references, "
    "and the complete failed-run observations visible to the reviewer alongside the associated sample, "
    "without treating a linked record as evidence that the sample has passed qualification, "
    "unless the review identifies missing evidence; then preserve that condition in the result."
)
AUTHORED_BLOCK = LONG_CONDITIONAL + "\n\n1. Keep the original entry.\n2. Record the exception; do not replace it\n\nNo approval is asserted"


def test_story_preserves_complete_conditional_decimal_acronym_and_list_blocks(tmp_path: Path) -> None:
    entry = story_entry(tmp_path, {"Proposed Solution": AUTHORED_BLOCK})
    assert entry["story_text"] == AUTHORED_BLOCK
    assert not str(entry["story_text"]).endswith(".")


@pytest.mark.parametrize("sections, source, text", [
    ({"Problem": "Source — A record is missing; preserve that fact"}, "Problem", "Source — A record is missing; preserve that fact"),
    ({"Proposed Solution": " \n ", "Scope": "- Inspect the lot\n- Preserve the custody trail"}, "Scope", "- Inspect the lot\n- Preserve the custody trail"),
    ({"Opportunity": "An authored opportunity, without a synthesized title"}, "Opportunity", "An authored opportunity, without a synthesized title"),
    ({}, "", ""),
])
def test_story_fallback_uses_complete_present_source_or_explicit_absence(
    tmp_path: Path, sections: dict[str, str], source: str, text: str,
) -> None:
    entry = story_entry(tmp_path, sections)
    assert entry["story_source"] == source
    assert entry["story_text"] == text


def test_story_recomposition_phase_is_removed() -> None:
    html = html_runtime._render_html(payload={"entries": []})
    for obsolete in (
        "firstUsefulSentence", "ROW_STORY_MAX", "LOW_VALUE_STORY_PATTERNS", "workstreamStoryParagraph",
        "workstreamStoryLines", "storySentence", "titleNarrativeSentence", "normalizeNarrativeSentence",
        "compactNarrativeForDetail", "shortenAtReadableBoundary", "shortenAtWordBoundary", "compactPlainText",
    ):
        assert obsolete not in html


def test_embedded_story_cannot_end_its_json_script() -> None:
    attack = '</script><script>window.__storyInjected = true</script><img src=x onerror="window.__storyInjected=true">'
    html = html_runtime._render_html(payload={"entries": [{"story_source": "Proposed Solution", "story_text": attack}]})
    embedded = html.split('<script id="backlogData" type="application/json">', 1)[1].split("</script>", 1)[0]
    assert json.loads(embedded)["entries"][0]["story_text"] == attack
    assert '<script>window.__storyInjected' not in html


def test_prose_metadata_reaches_shared_markdown_without_display_normalization(tmp_path: Path) -> None:
    source = "**Proposed result** — Keep `__sample_id__` and `1. first 2. second`, unless review finds an exception."
    entry = story_entry(tmp_path, {"Proposed Solution": source}, prose_metadata={
        "implemented_summary": source, "ordering_rationale": source,
    }, rationale=[source])
    assert entry["implemented_summary"] == source
    assert entry["ordering_rationale"] == source
    assert entry["rationale_bullets"] == [source]
    for field in ("implemented_summary_html", "rationale_html", "ordering_rationale_html", "story_html"):
        assert "<code>__sample_id__</code>" in entry[field]
        assert "<code>1. first 2. second</code>" in entry[field]


def test_section_projection_preserves_fenced_headings_and_raw_markup(tmp_path: Path) -> None:
    source = "**Original** `__sample_id__`\n\n```text\n## Not a section\n```\n\nUnless review finds an exception"
    entry = story_entry(tmp_path, {"Proposed Solution": source, "Problem": source})
    assert entry["story_text"] == source
    assert entry["problem"] == source
    assert "## Not a section" in entry["story_html"]
