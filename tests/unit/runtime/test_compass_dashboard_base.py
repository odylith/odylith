from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces import compass_dashboard_base as renderer


def test_collect_git_local_changes_skips_deleted_deindexed_casebook_bug(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    bug_dir = tmp_path / "odylith" / "casebook" / "bugs"
    bug_dir.mkdir(parents=True, exist_ok=True)
    (bug_dir / "INDEX.md").write_text(
        "# Bug Index\n\n"
        "## Open Bugs\n\n"
        "| Date | Title | Severity | Components | Status | Link |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 2026-03-26 | Consumer bug | P1 | tooling | Open | [keep.md](keep.md) |\n",
        encoding="utf-8",
    )

    def _fake_run_git(repo_root: Path, args: list[str]):  # noqa: ANN001, ANN202
        _ = repo_root, args
        return (
            0,
            " D odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md\n"
            " M src/odylith/cli.py\n",
        )

    monkeypatch.setattr(renderer, "_run_git", _fake_run_git)
    rows = renderer._collect_git_local_changes(tmp_path)  # noqa: SLF001
    assert rows == [{"status": "M", "path": "src/odylith/cli.py"}]


def test_collect_git_local_changes_skips_deleted_legacy_bug_and_runtime_rollback(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    bug_dir = tmp_path / "odylith" / "casebook" / "bugs"
    bug_dir.mkdir(parents=True, exist_ok=True)
    (bug_dir / "INDEX.md").write_text(
        "# Bug Index\n\n"
        "## Open Bugs\n\n"
        "| Date | Title | Severity | Components | Status | Link |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 2026-03-26 | Consumer bug | P1 | tooling | Open | [keep.md](keep.md) |\n",
        encoding="utf-8",
    )

    def _fake_run_git(repo_root: Path, args: list[str]):  # noqa: ANN001, ANN202
        _ = repo_root, args
        return (
            0,
            " D bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md\n"
            "?? .odylith/.rollback/odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md\n"
            " M src/odylith/runtime/surfaces/compass_dashboard_base.py\n",
        )

    monkeypatch.setattr(renderer, "_run_git", _fake_run_git)
    rows = renderer._collect_git_local_changes(tmp_path)  # noqa: SLF001
    assert rows == [{"status": "M", "path": "src/odylith/runtime/surfaces/compass_dashboard_base.py"}]
