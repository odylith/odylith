from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.context_engine import odylith_context_engine
from odylith.runtime.governance import sync_workstream_artifacts
from odylith.runtime.surfaces import compass_dashboard_runtime
from odylith.runtime.surfaces import render_backlog_ui


def test_sync_parser_accepts_legacy_shape_aliases(tmp_path: Path) -> None:
    args = sync_workstream_artifacts._parse_args(  # noqa: SLF001
        [
            "--repo-root",
            str(tmp_path),
            "--check-only",
            "--odylith-mode",
            "check",
            "--policy-mode",
            "enforce-critical",
            "--no-render",
            "--once",
            "--interval-seconds",
            "30",
            "--max-interval-seconds",
            "300",
        ]
    )
    assert args.repo_root == str(tmp_path)
    assert args.check_only is True
    assert args.registry_policy_mode == "enforce-critical"
    assert args.compass_refresh_profile == "shell-safe"


def test_context_engine_defaults_to_current_runtime_without_workspace_opt_in(tmp_path: Path, monkeypatch) -> None:
    candidate = tmp_path / ".venv" / "bin" / "python"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    candidate.chmod(0o755)
    monkeypatch.delenv("ODYLITH_CONTEXT_ENGINE_ALLOW_WORKSPACE_PYTHON", raising=False)
    preferred = odylith_context_engine._preferred_odylith_python(repo_root=tmp_path)  # noqa: SLF001
    assert Path(preferred).resolve() == Path(odylith_context_engine.sys.executable).resolve()


def test_run_command_absolutizes_pythonpath_for_cross_repo_sync(tmp_path: Path, monkeypatch) -> None:
    commands: dict[str, object] = {}

    def _fake_run(args, cwd, env, check):  # noqa: ANN001
        commands["args"] = list(args)
        commands["cwd"] = cwd
        commands["env"] = dict(env)
        commands["check"] = check

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setenv("PYTHONPATH", "src")
    monkeypatch.setattr(sync_workstream_artifacts.subprocess, "run", _fake_run)

    rc = sync_workstream_artifacts._run_command(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.governance.normalize_plan_risk_mitigation", "--repo-root", str(tmp_path)),
    )

    assert rc == 0
    assert commands["args"][0] == sync_workstream_artifacts.sys.executable
    assert commands["cwd"] == str(tmp_path)
    assert commands["check"] is False
    assert commands["env"]["PYTHONPATH"] == str((Path.cwd() / "src").resolve())


def test_governed_surface_closeout_path_truth_stays_normalized_across_runtime_readers() -> None:
    radar_index = Path("odylith/radar/source/INDEX.md").read_text(encoding="utf-8")
    governance_surfaces = Path("odylith/surfaces/GOVERNANCE_SURFACES.md").read_text(encoding="utf-8")
    context_engine_ops = Path("odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md").read_text(encoding="utf-8")
    delivery_intelligence = Path("odylith/runtime/delivery_intelligence.v4.json").read_text(encoding="utf-8")

    assert "## Finished (Linked to `odylith/technical-plans/done`)" in radar_index
    assert render_backlog_ui._FINISHED_SECTION_TITLE == "Finished (Linked to `odylith/technical-plans/done`)"  # noqa: SLF001
    assert "odylith/technical-plans/done/" in sync_workstream_artifacts._SYNC_PATH_PREFIXES  # noqa: SLF001
    assert 'line.startswith("| `odylith/technical-plans/done/")' in Path(compass_dashboard_runtime.__file__).read_text(
        encoding="utf-8"
    )
    assert "odylith/technical-plans/" in governance_surfaces
    assert "odylith sync --repo-root . --check-only" in context_engine_ops
    assert '"plan_path": "odylith/technical-plans/done/' in delivery_intelligence


def test_force_sync_runs_component_spec_requirements_after_atlas_mutations(tmp_path: Path, monkeypatch) -> None:
    executed: list[tuple[str, ...]] = []

    class _Meaningful:
        def as_dict(self) -> dict[str, int]:
            return {
                "linked_meaningful_event_count": 0,
                "unlinked_meaningful_event_count": 0,
            }

    def _fake_run_command(*, repo_root: Path, args: tuple[str, ...], heartbeat_label: str = "") -> int:  # noqa: ARG001
        executed.append(tuple(args))
        return 0

    monkeypatch.setattr(sync_workstream_artifacts, "_effective_changed_paths", lambda **_: ("odylith/atlas/source/workstream-dependency-map.mmd",))
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: False)
    monkeypatch.setattr(sync_workstream_artifacts.governance, "build_dashboard_impact", lambda **_: SimpleNamespace(
        radar=False,
        atlas=True,
        compass=False,
        registry=True,
        casebook=False,
        tooling_shell=False,
    ))
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )
    monkeypatch.setattr(sync_workstream_artifacts, "_run_command", _fake_run_command)

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--force"])

    assert rc == 0
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    sync_index = modules.index("odylith.runtime.governance.sync_component_spec_requirements")
    atlas_update_index = modules.index("odylith.runtime.surfaces.auto_update_mermaid_diagrams")
    atlas_render_index = modules.index("odylith.runtime.surfaces.render_mermaid_catalog")
    registry_render_index = modules.index("odylith.runtime.surfaces.render_registry_dashboard")

    assert atlas_update_index < sync_index
    assert atlas_render_index < sync_index
    assert sync_index < registry_render_index


def test_check_only_sync_skips_runtime_fast_path_and_warmup(tmp_path: Path, monkeypatch) -> None:
    executed: list[tuple[str, ...]] = []

    class _Meaningful:
        def as_dict(self) -> dict[str, int]:
            return {
                "linked_meaningful_event_count": 0,
                "unlinked_meaningful_event_count": 0,
            }

    def _fake_run_command(*, repo_root: Path, args: tuple[str, ...], heartbeat_label: str = "") -> int:  # noqa: ARG001
        executed.append(tuple(args))
        return 0

    monkeypatch.setattr(sync_workstream_artifacts, "_effective_changed_paths", lambda **_: ("odylith/radar/source/INDEX.md",))
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_runtime_fast_path_prerequisites_met", lambda _repo_root: True)
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "build_dashboard_impact",
        lambda **_: SimpleNamespace(
            radar=True,
            atlas=False,
            compass=False,
            registry=False,
            casebook=False,
            tooling_shell=True,
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )
    monkeypatch.setattr(sync_workstream_artifacts, "_run_command", _fake_run_command)
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_context_engine_store",
        lambda: SimpleNamespace(
            build_governance_slice=lambda **kwargs: (_ for _ in ()).throw(AssertionError("runtime packet should not build")),
            record_runtime_timing=lambda **kwargs: (_ for _ in ()).throw(AssertionError("runtime timing should not record")),
            warm_projections=lambda **kwargs: (_ for _ in ()).throw(AssertionError("warm_projections should not run")),
            select_impacted_diagrams=lambda **kwargs: (_ for _ in ()).throw(AssertionError("diagram selection should not run")),
        ),
    )

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--force", "--check-only"])

    assert rc == 0
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    assert "odylith.runtime.governance.validate_component_registry_contract" in modules
    assert "odylith.runtime.surfaces.render_tooling_dashboard" not in modules
    component_sync = next(
        command
        for command in executed
        if len(command) >= 3 and command[:3] == ("python", "-m", "odylith.runtime.governance.sync_component_spec_requirements")
    )
    assert component_sync[-2:] == ("--runtime-mode", "standalone")


def test_dashboard_refresh_skips_component_spec_sync_for_shell_facing_refresh(tmp_path: Path, monkeypatch) -> None:
    executed: list[tuple[str, ...]] = []

    def _fake_run_command(
        *,
        repo_root: Path,
        args: tuple[str, ...],
        heartbeat_label: str = "",
        timeout_seconds: float | None = None,
    ) -> int:  # noqa: ARG001
        executed.append(tuple(args))
        return 0

    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: False)
    monkeypatch.setattr(sync_workstream_artifacts, "_run_command", _fake_run_command)

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("tooling_shell", "radar", "compass"),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert rc == 0
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    assert "odylith.runtime.governance.delivery_intelligence_engine" in modules
    assert "odylith.runtime.surfaces.render_backlog_ui" in modules
    assert "odylith.runtime.surfaces.render_compass_dashboard" in modules
    assert "odylith.runtime.surfaces.render_tooling_dashboard" in modules
    compass_commands = [command for command in executed if "odylith.runtime.surfaces.render_compass_dashboard" in command]
    assert compass_commands
    assert "--refresh-profile" in compass_commands[0]
    assert compass_commands[0][compass_commands[0].index("--refresh-profile") + 1] == "shell-safe"
    assert "odylith.runtime.governance.sync_component_spec_requirements" not in modules
    assert "odylith.runtime.surfaces.render_registry_dashboard" not in modules


def test_dashboard_refresh_casebook_migrates_bug_ids_during_refresh(tmp_path: Path, monkeypatch) -> None:
    executed: list[tuple[str, ...]] = []
    casebook_sync_calls: list[bool] = []

    def _fake_run_command(
        *,
        repo_root: Path,
        args: tuple[str, ...],
        heartbeat_label: str = "",
        timeout_seconds: float | None = None,
    ) -> int:  # noqa: ARG001
        executed.append(tuple(args))
        return 0

    def _fake_sync_casebook_bug_index(*, repo_root: Path, migrate_bug_ids: bool = True) -> Path:
        casebook_sync_calls.append(bool(migrate_bug_ids))
        return repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md"

    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: False)
    monkeypatch.setattr(sync_workstream_artifacts, "_run_command", _fake_run_command)
    monkeypatch.setattr(
        sync_workstream_artifacts.sync_casebook_bug_index,
        "sync_casebook_bug_index",
        _fake_sync_casebook_bug_index,
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("casebook",),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert rc == 0
    assert casebook_sync_calls == [True]
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    assert modules == ["odylith.runtime.surfaces.render_casebook_dashboard"]


def test_dashboard_refresh_dry_run_accepts_shell_alias_without_running_commands(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: False)
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_run_command",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("dashboard refresh should not execute commands during --dry-run")),
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("shell", "radar"),
        runtime_mode="auto",
        dry_run=True,
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "dashboard refresh dry-run" in output
    assert "tooling_shell" in output


def test_dashboard_refresh_plan_reports_included_excluded_surfaces_and_atlas_follow_up(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(sync_workstream_artifacts, "_atlas_stale_diagram_count", lambda **kwargs: 2)

    plan = sync_workstream_artifacts.build_dashboard_refresh_plan(
        repo_root=tmp_path,
        surfaces=("tooling_shell", "radar", "compass"),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert "Included surfaces: tooling_shell, radar, compass." in plan.notes
    assert "Excluded surfaces: atlas, registry, casebook." in plan.notes
    assert any(
        note
        == (
            "Atlas is excluded from this run and 2 diagram(s) are currently stale. Next: "
            "odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync"
        )
        for note in plan.notes
    )


def test_dashboard_refresh_retries_auto_surface_with_standalone_fallback(tmp_path: Path, monkeypatch, capsys) -> None:
    executed: list[tuple[str, ...]] = []

    def _fake_run_command(*, repo_root: Path, args: tuple[str, ...], heartbeat_label: str = "", timeout_seconds: float | None = None) -> int:  # noqa: ARG001
        executed.append(tuple(args))
        return 124 if "--runtime-mode" not in args else 0

    monkeypatch.setattr(sync_workstream_artifacts, "_run_command", _fake_run_command)

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("radar",),
        runtime_mode="auto",
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert len(executed) == 2
    assert "--runtime-mode" not in executed[0]
    assert executed[1][-2:] == ("--runtime-mode", "standalone")
    assert "runtime_fallback: radar -> standalone" in output
    assert "- radar: passed (standalone fallback used)" in output


def test_dashboard_refresh_continues_after_surface_failure_and_returns_non_zero(tmp_path: Path, monkeypatch, capsys) -> None:
    executed: list[tuple[str, ...]] = []

    def _fake_run_command(*, repo_root: Path, args: tuple[str, ...], heartbeat_label: str = "", timeout_seconds: float | None = None) -> int:  # noqa: ARG001
        executed.append(tuple(args))
        if "odylith.runtime.surfaces.render_compass_dashboard" in args:
            return 1
        return 0

    monkeypatch.setattr(sync_workstream_artifacts, "_run_command", _fake_run_command)

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("compass", "radar", "tooling_shell"),
        runtime_mode="standalone",
    )
    output = capsys.readouterr().out

    assert rc == 2
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    assert "odylith.runtime.surfaces.render_compass_dashboard" in modules
    assert "odylith.runtime.surfaces.render_backlog_ui" in modules
    assert "odylith.runtime.surfaces.render_tooling_dashboard" in modules
    assert "- compass: failed" in output
    assert "- radar: passed" in output
    assert "- tooling_shell: passed" in output
    assert "next: odylith compass update --repo-root ." in output


def test_run_command_terminates_timed_out_child_process(tmp_path: Path, monkeypatch, capsys) -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.terminated = False
            self.killed = False
            self.wait_calls: list[int | None] = []

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: int | None = None) -> int:
            self.wait_calls.append(timeout)
            return 0

        def kill(self) -> None:
            self.killed = True

    process = _FakeProcess()
    perf_counter_values = iter([0.0, 0.0, 1.2])

    monkeypatch.setattr(sync_workstream_artifacts.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(sync_workstream_artifacts.time, "perf_counter", lambda: next(perf_counter_values))
    monkeypatch.setattr(sync_workstream_artifacts.time, "sleep", lambda _seconds: None)

    rc = sync_workstream_artifacts._run_command(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.surfaces.render_backlog_ui"),
        heartbeat_label="radar",
        timeout_seconds=1.0,
    )
    output = capsys.readouterr().out

    assert rc == 124
    assert process.terminated is True
    assert process.killed is False
    assert process.wait_calls == [5]
    assert "timeout: radar exceeded 1s; terminating" in output


def test_run_command_terminates_process_group_for_timed_out_child(tmp_path: Path, monkeypatch, capsys) -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.pid = 4321
            self.terminated = False
            self.killed = False
            self.wait_calls: list[int | None] = []

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: int | None = None) -> int:
            self.wait_calls.append(timeout)
            return 0

        def kill(self) -> None:
            self.killed = True

    process = _FakeProcess()
    perf_counter_values = iter([0.0, 0.0, 1.2])
    killed_groups: list[tuple[int, int]] = []

    monkeypatch.setattr(sync_workstream_artifacts.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(sync_workstream_artifacts.time, "perf_counter", lambda: next(perf_counter_values))
    monkeypatch.setattr(sync_workstream_artifacts.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(sync_workstream_artifacts.os, "killpg", lambda pid, sig: killed_groups.append((pid, int(sig))))

    rc = sync_workstream_artifacts._run_command(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.surfaces.render_backlog_ui"),
        heartbeat_label="radar",
        timeout_seconds=1.0,
    )
    output = capsys.readouterr().out

    assert rc == 124
    assert killed_groups == [(4321, int(sync_workstream_artifacts.signal.SIGTERM))]
    assert process.terminated is False
    assert process.killed is False
    assert process.wait_calls == [5]
    assert "timeout: radar exceeded 1s; terminating" in output


def test_sync_dry_run_prints_plan_without_running_commands(tmp_path: Path, monkeypatch, capsys) -> None:
    class _Meaningful:
        def as_dict(self) -> dict[str, int]:
            return {
                "linked_meaningful_event_count": 0,
                "unlinked_meaningful_event_count": 0,
            }

    monkeypatch.setattr(sync_workstream_artifacts, "_effective_changed_paths", lambda **_: ("odylith/radar/source/INDEX.md",))
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: False)
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "build_dashboard_impact",
        lambda **_: SimpleNamespace(
            radar=True,
            atlas=False,
            compass=True,
            registry=False,
            casebook=False,
            tooling_shell=True,
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_run_command",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("sync should not execute commands during --dry-run")),
    )

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--force", "--dry-run"])
    output = capsys.readouterr().out

    assert rc == 0
    assert "workstream sync dry-run" in output
    assert "Render Compass before Radar" in output
