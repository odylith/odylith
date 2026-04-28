from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import backlog_traceability_paths


def test_collect_plan_paths_groups_dedupes_and_normalizes_known_buckets(tmp_path: Path) -> None:
    (tmp_path / "docs" / "runbooks").mkdir(parents=True)
    (tmp_path / "docs" / "runbooks" / "repair.md").write_text("# Repair\n", encoding="utf-8")
    sections = [
        ("Problem", ["Not traceability."]),
        (
            "Traceability",
            [
                "### Runbooks",
                "- [x] [Repair Guide](docs/runbooks/repair.md)",
                "- `docs/runbooks/repair.md`",
                "",
                "### Developer Docs",
                "- [Docs](./docs/../docs/guide.md)",
                "### Code References",
                "- `src/odylith/runtime/surfaces/render_backlog_ui.py`,",
                "### Unsupported",
                "- `docs/ignored.md`",
            ],
        ),
    ]

    paths = backlog_traceability_paths.collect_plan_paths(repo_root=tmp_path, sections=sections)

    assert paths == {
        "Runbooks": ["docs/runbooks/repair.md"],
        "Developer Docs": ["docs/../docs/guide.md"],
        "Code References": ["src/odylith/runtime/surfaces/render_backlog_ui.py"],
    }


def test_collect_plan_paths_ignores_urls_freeform_text_and_unknown_sections(tmp_path: Path) -> None:
    sections = [
        (
            "Traceability",
            [
                "- `docs/outside-bucket.md`",
                "### Runbooks",
                "plain docs/runbooks/no-list.md",
                "- [External](https://example.com/runbook)",
                "- `two words.md`",
                "- `<bad>`",
            ],
        ),
    ]

    assert backlog_traceability_paths.collect_plan_paths(repo_root=tmp_path, sections=sections) == {}


def test_extract_path_tokens_reads_link_targets_before_inline_code() -> None:
    tokens = backlog_traceability_paths.extract_path_tokens(
        "See [runbook](docs/runbook.md) and `src/app.py`."
    )

    assert tokens == ["docs/runbook.md", "src/app.py"]


def test_is_traceability_section_is_case_and_space_tolerant() -> None:
    assert backlog_traceability_paths.is_traceability_section(" Traceability ")
    assert backlog_traceability_paths.is_traceability_section("traceability")
    assert not backlog_traceability_paths.is_traceability_section("Traceability Notes")
