from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import backlog_render_support


def test_split_metadata_ids_filters_and_dedupes() -> None:
    values = backlog_render_support._split_metadata_ids(  # noqa: SLF001
        value="B-010; B-011, invalid, B-010",
        pattern=backlog_render_support._IDEA_ID_RE,  # noqa: SLF001
    )

    assert values == ["B-010", "B-011"]


def test_extract_plan_dates_reads_front_matter_and_filename_date(tmp_path: Path) -> None:
    plan_path = tmp_path / "2026-04-18-example-plan.md"
    plan_path.write_text(
        "\n".join(
            [
                "# Example",
                "Created: 2026-04-16",
                "Updated: 2026-04-18",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    created, updated, filename_date = backlog_render_support._extract_plan_dates(plan_path)  # noqa: SLF001

    assert created == "2026-04-16"
    assert updated == "2026-04-18"
    assert filename_date == "2026-04-18"


def test_radar_route_href_keeps_relative_target_and_query_state(tmp_path: Path) -> None:
    source = tmp_path / "radar.html"
    target = tmp_path / "standalone-pages.v1.html"

    href = backlog_render_support._radar_route_href(  # noqa: SLF001
        source_output_path=source,
        target_output_path=target,
        workstream_id="B-073",
        view="plan",
    )

    assert href == "standalone-pages.v1.html?view=plan&workstream=B-073"


def test_extract_sections_from_markdown_flattens_section_copy(tmp_path: Path) -> None:
    path = tmp_path / "idea.md"
    path.write_text(
        "\n".join(
            [
                "# Title",
                "",
                "## Problem",
                "First line.",
                "Second line.",
                "",
                "## Success Metrics",
                "- one",
                "- two",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sections = backlog_render_support._extract_sections_from_markdown(path)  # noqa: SLF001

    assert sections == {
        "Problem": "First line. Second line.",
        "Success Metrics": "- one - two",
    }
