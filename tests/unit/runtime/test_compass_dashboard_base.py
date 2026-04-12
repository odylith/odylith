from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.governance import sync_session
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


def test_load_component_index_runtime_reuses_sync_session_registry_report(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    sentinel = {
        "compass": registry.ComponentEntry(
            component_id="compass",
            name="Compass",
            kind="composite",
            category="governance_surface",
            qualification="curated",
            aliases=[],
            path_prefixes=[],
            workstreams=[],
            diagrams=[],
            owner="platform",
            status="active",
            what_it_is="Compass surface.",
            why_tracked="Tracks executive state.",
            spec_ref="odylith/registry/source/components/compass/CURRENT_SPEC.md",
            sources=["manifest"],
        )
    }

    class _Report:
        components = sentinel

    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_component_index",
        lambda **_: (_ for _ in ()).throw(AssertionError("projection runtime should not be used inside sync session")),
    )
    monkeypatch.setattr(registry, "build_component_registry_report", lambda **_: _Report())

    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    with sync_session.activate_sync_session(session):
        components = renderer._load_component_index_runtime(repo_root=tmp_path, runtime_mode="standalone")  # noqa: SLF001

    assert components is sentinel
