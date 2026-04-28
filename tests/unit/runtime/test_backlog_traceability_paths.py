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
        "Developer Docs": ["docs/guide.md"],
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


def test_collect_plan_paths_accepts_bucket_variants_and_path_decorators(tmp_path: Path) -> None:
    (tmp_path / "docs" / "runbooks").mkdir(parents=True)
    (tmp_path / "docs" / "runbooks" / "repair.md").write_text("# Repair\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    absolute_inside = tmp_path / "src" / "app.py"
    sections = [
        (
            "traceability",
            [
                "### runbooks:",
                "* [Repair](<docs/runbooks/repair.md#operator-flow>)",
                "### code references",
                f"* `{absolute_inside}:12`",
                "* `src/app.py?cache=bust`",
            ],
        ),
    ]

    paths = backlog_traceability_paths.collect_plan_paths(repo_root=tmp_path, sections=sections)

    assert paths == {
        "Runbooks": ["docs/runbooks/repair.md"],
        "Code References": ["src/app.py"],
    }


def test_collect_plan_paths_rejects_repo_escape_and_absolute_outside_paths(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    sections = [
        (
            "Traceability",
            [
                "### Runbooks",
                "- `../outside.md`",
                f"- `{outside}`",
                "- [Outside](../../outside.md)",
            ],
        ),
    ]

    assert backlog_traceability_paths.collect_plan_paths(repo_root=tmp_path, sections=sections) == {}


def test_is_traceability_section_is_case_and_space_tolerant() -> None:
    assert backlog_traceability_paths.is_traceability_section(" Traceability ")
    assert backlog_traceability_paths.is_traceability_section("traceability")
    assert backlog_traceability_paths.is_traceability_section("Traceability:")
    assert not backlog_traceability_paths.is_traceability_section("Traceability Notes")
