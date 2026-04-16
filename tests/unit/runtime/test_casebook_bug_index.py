from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.common.casebook_bug_ids import fallback_casebook_bug_id
from odylith.runtime.governance import sync_casebook_bug_index


def _write_bug(path: Path, *, status: str, created: str, severity: str, components: str, bug_id: str = "") -> None:
    lines = []
    if bug_id:
        lines.extend([f"- Bug ID: {bug_id}", ""])
    lines.extend(
        [
            f"- Status: {status}",
            f"- Created: {created}",
            f"- Severity: {severity}",
            "- Reproducibility: High",
            f"- Components Affected: {components}",
            "",
            "- Description: Example bug.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def test_sync_casebook_bug_index_rebuilds_from_markdown_source(tmp_path: Path) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    _write_bug(
        bug_root / "2026-03-26-example-open-bug.md",
        bug_id="CB-001",
        status="Open",
        created="2026-03-26",
        severity="P1",
        components="tooling",
    )
    _write_bug(
        bug_root / "2026-03-25-example-closed-bug.md",
        bug_id="CB-002",
        status="Closed",
        created="2026-03-25",
        severity="P2",
        components="dashboard",
    )

    index_path = sync_casebook_bug_index.sync_casebook_bug_index(repo_root=tmp_path)
    text = index_path.read_text(encoding="utf-8")

    assert "## Open Bugs" in text
    assert "| CB-001 | 2026-03-26 | Example open bug | P1 | tooling | Open | [2026-03-26-example-open-bug.md](2026-03-26-example-open-bug.md) |" in text
    assert "## Closed Bugs" in text
    assert "| CB-002 | 2026-03-25 | Example closed bug | P2 | dashboard | Closed | [2026-03-25-example-closed-bug.md](2026-03-25-example-closed-bug.md) |" in text


def test_migrate_casebook_bug_ids_backfills_missing_bug_ids_after_existing_sequence(tmp_path: Path) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    retained = bug_root / "2026-03-25-existing-bug.md"
    missing = bug_root / "2026-03-26-missing-bug.md"
    _write_bug(
        retained,
        bug_id="CB-007",
        status="Closed",
        created="2026-03-25",
        severity="P2",
        components="dashboard",
    )
    _write_bug(
        missing,
        status="Open",
        created="2026-03-26",
        severity="P1",
        components="tooling",
    )

    updated = sync_casebook_bug_index.migrate_casebook_bug_ids(repo_root=tmp_path)

    assert updated == [missing]
    assert "- Bug ID: CB-007" in retained.read_text(encoding="utf-8")
    assert "- Bug ID: CB-008" in missing.read_text(encoding="utf-8")


def test_sync_casebook_bug_index_migrates_missing_bug_ids_by_default(tmp_path: Path) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    path = bug_root / "2026-03-26-example-open-bug.md"
    _write_bug(
        path,
        status="Open",
        created="2026-03-26",
        severity="P1",
        components="tooling",
    )

    sync_casebook_bug_index.sync_casebook_bug_index(repo_root=tmp_path)

    assert "- Bug ID: CB-001" in path.read_text(encoding="utf-8")
    index_text = (bug_root / "INDEX.md").read_text(encoding="utf-8")
    assert "| Bug ID | Date | Title | Severity | Components | Status | Link |" in index_text
    assert "| CB-001 | 2026-03-26 | Example open bug | P1 | tooling | Open | [2026-03-26-example-open-bug.md](2026-03-26-example-open-bug.md) |" in index_text


def test_load_bug_rows_skips_missing_stale_bug_targets(tmp_path: Path) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    _write_bug(
        bug_root / "2026-03-26-real-bug.md",
        bug_id="CB-009",
        status="Open",
        created="2026-03-26",
        severity="P1",
        components="tooling",
    )
    (bug_root / "INDEX.md").write_text(
        "\n".join(
            [
                "# Bug Index",
                "",
                "## Open Bugs",
                "",
                "| Date | Title | Severity | Components | Status | Link |",
                "| --- | --- | --- | --- | --- | --- |",
                "| 2026-03-26 | Real bug | P1 | tooling | Open | [2026-03-26-real-bug.md](2026-03-26-real-bug.md) |",
                "| 2026-03-24 | Stale moved bug | P0 | context-engine | Closed | [bug](odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md) |",
                "",
                "## Closed Bugs",
                "",
                "None.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rows = odylith_context_engine_store.load_bug_rows(repo_root=tmp_path, runtime_mode="standalone")

    assert len(rows) == 1
    assert rows[0]["Bug ID"] == "CB-009"
    assert rows[0]["Title"] == "Real bug"
    assert rows[0]["Link"] == "[bug](odylith/casebook/bugs/2026-03-26-real-bug.md)"


def test_load_bug_rows_assigns_stable_fallback_bug_id_for_legacy_bug_markdown(tmp_path: Path) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    bug_path = bug_root / "2026-03-26-real-bug.md"
    _write_bug(
        bug_path,
        status="Open",
        created="2026-03-26",
        severity="P1",
        components="tooling",
    )
    (bug_root / "INDEX.md").write_text(
        "\n".join(
            [
                "# Bug Index",
                "",
                "## Open Bugs",
                "",
                "| Date | Title | Severity | Components | Status | Link |",
                "| --- | --- | --- | --- | --- | --- |",
                "| 2026-03-26 | Real bug | P1 | tooling | Open | [2026-03-26-real-bug.md](2026-03-26-real-bug.md) |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rows = odylith_context_engine_store.load_bug_rows(repo_root=tmp_path, runtime_mode="standalone")

    assert rows == [
        {
            "Bug ID": fallback_casebook_bug_id(seed="odylith/casebook/bugs/2026-03-26-real-bug.md"),
            "Date": "2026-03-26",
            "Title": "Real bug",
            "Severity": "P1",
            "Components": "tooling",
            "Status": "Open",
            "Link": "[bug](odylith/casebook/bugs/2026-03-26-real-bug.md)",
            "IndexPath": "odylith/casebook/bugs/INDEX.md",
        }
    ]


def test_normalize_bug_link_target_keeps_repo_relative_bug_path_without_duplication(tmp_path: Path) -> None:
    bug_root = tmp_path / "odylith" / "casebook" / "bugs"
    bug_root.mkdir(parents=True, exist_ok=True)
    index_path = bug_root / "INDEX.md"
    index_path.write_text("# Bug Index\n", encoding="utf-8")

    normalized = odylith_context_engine_store._normalize_bug_link_target(  # noqa: SLF001
        repo_root=tmp_path,
        index_path=index_path,
        link_target="odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md",
    )

    assert normalized == "odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md"
