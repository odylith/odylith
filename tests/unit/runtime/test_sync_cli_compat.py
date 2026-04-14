from pathlib import Path
import time
from types import SimpleNamespace

from odylith.runtime.context_engine import odylith_context_engine
from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import sync_session
from odylith.runtime.governance import sync_workstream_artifacts
from odylith.runtime.surfaces import compass_dashboard_runtime
from odylith.runtime.surfaces import render_backlog_ui

_SECTIONS = (
    "Problem",
    "Customer",
    "Opportunity",
    "Proposed Solution",
    "Scope",
    "Non-Goals",
    "Risks",
    "Dependencies",
    "Success Metrics",
    "Validation",
    "Rollout",
    "Why Now",
    "Product View",
    "Impacted Components",
    "Interface Changes",
    "Migration/Compatibility",
    "Test Strategy",
    "Open Questions",
)


def _idea_text(
    *,
    idea_id: str,
    title: str,
    date: str,
    status: str,
    founder_override: str,
    promoted_to_plan: str,
) -> str:
    body_sections = "\n\n".join([f"## {section}\nDetails." for section in _SECTIONS])
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        f"date: {date}\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_lanes: both\n\n"
        "impacted_parts: odylith\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: sync fixture\n\n"
        "confidence: high\n\n"
        f"founder_override: {founder_override}\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        "workstream_type: standalone\n\n"
        "workstream_parent:\n\n"
        "workstream_children:\n\n"
        "workstream_depends_on:\n\n"
        "workstream_blocks:\n\n"
        "related_diagram_ids:\n\n"
        "workstream_reopens:\n\n"
        "workstream_reopened_by:\n\n"
        "workstream_split_from:\n\n"
        "workstream_split_into:\n\n"
        "workstream_merged_into:\n\n"
        "workstream_merged_from:\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{body_sections}\n"
    )


def _seed_sync_repo_with_legacy_backlog(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "consumer_repo.yaml").write_text("repo: odylith\n", encoding="utf-8")
    idea_dir = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    idea_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)

    queued_path = idea_dir / "2026-04-06-legacy-sync-fix.md"
    queued_path.write_text(
        _idea_text(
            idea_id="B-101",
            title="Legacy Sync Fix",
            date="2026-04-06",
            status="queued",
            founder_override="no",
            promoted_to_plan="",
        ),
        encoding="utf-8",
    )
    implementation_path = idea_dir / "2026-04-06-active-plan.md"
    implementation_path.write_text(
        _idea_text(
            idea_id="B-102",
            title="Active Plan",
            date="2026-04-06",
            status="implementation",
            founder_override="no",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-04-06-active-plan.md",
        ),
        encoding="utf-8",
    )
    plan_path = repo_root / "odylith" / "technical-plans" / "in-progress" / "2026-04-06-active-plan.md"
    plan_path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-04-06\n\n"
            "Updated: 2026-04-06\n\n"
            "Goal: prove sync normalization.\n\n"
            "Assumptions: fixture is minimal but valid.\n\n"
            "Constraints: none.\n\n"
            "Reversibility: safe.\n\n"
            "Boundary Conditions: local fixture only.\n\n"
            "## Context/Problem Statement\n- [ ] exercise sync preflight\n"
        ),
        encoding="utf-8",
    )
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-04-06\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 1 | B-101 | Legacy Sync Fix | P1 | 100 | 4 | 4 | 4 | M | Medium | both | queued | [idea](odylith/radar/source/ideas/2026-04/2026-04-06-legacy-sync-fix.md) |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| - | B-102 | Active Plan | P1 | 100 | 4 | 4 | 4 | M | Medium | both | implementation | [idea](odylith/radar/source/ideas/2026-04/2026-04-06-active-plan.md) |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-101 (rank 1)\n"
            "- why now: preserve the operator-provided note.\n"
        ),
        encoding="utf-8",
    )
    (repo_root / "odylith" / "technical-plans" / "INDEX.md").write_text(
        (
            "# Plan Index\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| `odylith/technical-plans/in-progress/2026-04-06-active-plan.md` | In progress | 2026-04-06 | 2026-04-06 | `B-102` |\n"
        ),
        encoding="utf-8",
    )
    return repo_root


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


def test_print_execution_plan_condenses_dirty_overlap_without_verbose(capsys) -> None:  # noqa: ANN001
    plan = sync_workstream_artifacts.ExecutionPlan(
        headline="preview",
        steps=(),
        dirty_overlap=("M one", "M two", "M three", "M four", "M five"),
        notes=(),
    )

    sync_workstream_artifacts._print_execution_plan("workstream sync", plan, dry_run=True, verbose=False)  # noqa: SLF001
    output = capsys.readouterr().out

    assert "5 local worktree entries overlap this mutation plan." in output
    assert "By area: other=5." in output
    assert "M five" not in output
    assert "hidden; rerun with --verbose to show the full set." in output


def test_print_execution_plan_verbose_shows_full_dirty_overlap(capsys) -> None:  # noqa: ANN001
    plan = sync_workstream_artifacts.ExecutionPlan(
        headline="preview",
        steps=(),
        dirty_overlap=("M one", "M two", "M three", "M four", "M five"),
        notes=(),
    )

    sync_workstream_artifacts._print_execution_plan("workstream sync", plan, dry_run=True, verbose=True)  # noqa: SLF001
    output = capsys.readouterr().out

    assert "M five" in output
    assert "hidden; rerun with --verbose" not in output


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


def test_run_callable_with_heartbeat_preserves_active_sync_session(tmp_path: Path) -> None:
    seen_repo_roots: list[str] = []
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)

    with sync_session.activate_sync_session(session):
        rc = sync_workstream_artifacts._run_callable_with_heartbeat(  # noqa: SLF001
            label="sync-session-test",
            callable_=lambda: seen_repo_roots.append(
                str(sync_session.active_sync_session().repo_root)  # type: ignore[union-attr]
            )
            or 0,
        )

    assert rc == 0
    assert seen_repo_roots == [str(tmp_path.resolve())]


def test_generated_surface_steps_export_sync_forced_rebuild_env() -> None:
    step = sync_workstream_artifacts.ExecutionStep(
        label="Render Radar",
        command=("python", "-m", "odylith.runtime.surfaces.render_backlog_ui"),
        mutation_classes=("generated_surfaces",),
        paths=("odylith/radar/radar.html",),
    )

    env_updates = sync_workstream_artifacts._step_env_overrides(step)  # noqa: SLF001

    assert env_updates == {"ODYLITH_SYNC_SKIP_GENERATED_REFRESH_GUARD": "1"}


def test_generated_surface_only_step_does_not_invalidate_projection_caches(tmp_path: Path, monkeypatch) -> None:
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    session.get_or_compute(namespace="runtime_warm", key="default", builder=lambda: True)
    cleared_repo_roots: list[str] = []
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_context_engine_store",
        lambda: SimpleNamespace(
            clear_runtime_process_caches=lambda *, repo_root: cleared_repo_roots.append(str(repo_root))
        ),
    )

    step = sync_workstream_artifacts.ExecutionStep(
        label="Render shell",
        command=("python", "-m", "odylith.runtime.surfaces.render_tooling_dashboard"),
        mutation_classes=("generated_surfaces",),
        paths=("odylith/index.html", "odylith/tooling-payload.v1.js"),
    )

    with sync_session.activate_sync_session(session):
        sync_workstream_artifacts._invalidate_sync_runtime_caches(repo_root=tmp_path, step=step)  # noqa: SLF001

    assert cleared_repo_roots == []
    assert sync_session.active_sync_session() is None
    assert session.get_or_compute(namespace="runtime_warm", key="default", builder=lambda: False) is True


def test_traceability_refresh_invalidates_projection_caches(tmp_path: Path, monkeypatch) -> None:
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    session.get_or_compute(namespace="runtime_warm", key="default", builder=lambda: True)
    cleared_repo_roots: list[str] = []
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_context_engine_store",
        lambda: SimpleNamespace(
            clear_runtime_process_caches=lambda *, repo_root: cleared_repo_roots.append(str(repo_root))
        ),
    )

    step = sync_workstream_artifacts.ExecutionStep(
        label="Regenerate traceability graph",
        command=("python", "-m", "odylith.runtime.governance.build_traceability_graph"),
        mutation_classes=("generated_surfaces",),
        paths=("odylith/radar/traceability-graph.v1.json",),
    )

    with sync_session.activate_sync_session(session):
        sync_workstream_artifacts._invalidate_sync_runtime_caches(repo_root=tmp_path, step=step)  # noqa: SLF001

    assert cleared_repo_roots == [str(tmp_path.resolve())]
    assert session.get_or_compute(namespace="runtime_warm", key="default", builder=lambda: False) is False


def test_traceability_refresh_skips_projection_cache_invalidation_when_output_is_unchanged(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    session.get_or_compute(namespace="runtime_warm", key="default", builder=lambda: True)
    cleared_repo_roots: list[str] = []
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_context_engine_store",
        lambda: SimpleNamespace(
            clear_runtime_process_caches=lambda *, repo_root: cleared_repo_roots.append(str(repo_root))
        ),
    )

    step = sync_workstream_artifacts.ExecutionStep(
        label="Render Radar",
        command=("python", "-m", "odylith.runtime.surfaces.render_backlog_ui"),
        mutation_classes=("generated_surfaces",),
        paths=("odylith/radar/traceability-graph.v1.json",),
        change_watch_paths=("odylith/radar/traceability-graph.v1.json",),
    )

    with sync_session.activate_sync_session(session):
        sync_workstream_artifacts._invalidate_sync_runtime_caches(  # noqa: SLF001
            repo_root=tmp_path,
            step=step,
            step_changed=False,
        )

    assert cleared_repo_roots == []
    assert session.get_or_compute(namespace="runtime_warm", key="default", builder=lambda: False) is True


def test_sync_execution_plan_reruns_second_registry_spec_sync_after_shell_facing_steps(tmp_path: Path) -> None:
    impact = governance.DashboardImpact(
        radar=False,
        atlas=False,
        compass=False,
        registry=True,
        casebook=False,
        reasons={},
    )
    args = sync_workstream_artifacts._parse_args(  # noqa: SLF001
        [
            "--repo-root",
            str(tmp_path),
            "--force",
        ]
    )

    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=args,
        changed_paths=("src/odylith/runtime/surfaces/render_registry_dashboard.py",),
        impact=impact,
        impact_tooling_shell=True,
        runtime_mode="auto",
    )

    sync_steps = [
        step
        for step in plan.steps
        if "odylith.runtime.governance.sync_component_spec_requirements" in " ".join(step.command)
    ]
    assert len(sync_steps) == 2


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
    atlas_render_index = modules.index("odylith.runtime.surfaces.render_mermaid_catalog_refresh")
    registry_render_index = modules.index("odylith.runtime.surfaces.render_registry_dashboard")

    assert atlas_update_index < sync_index
    assert atlas_render_index < sync_index
    assert sync_index < registry_render_index


def test_force_sync_reruns_final_component_spec_refresh_after_generated_surfaces_follow(
    tmp_path: Path,
    monkeypatch,
) -> None:
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
        tooling_shell=True,
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
    sync_indexes = [
        index
        for index, module in enumerate(modules)
        if module == "odylith.runtime.governance.sync_component_spec_requirements"
    ]
    registry_render_index = modules.index("odylith.runtime.surfaces.render_registry_dashboard")
    tooling_render_index = modules.index("odylith.runtime.surfaces.render_tooling_dashboard")

    assert len(sync_indexes) == 2
    assert sync_indexes[0] < registry_render_index
    assert registry_render_index < tooling_render_index
    assert tooling_render_index < sync_indexes[1]


def test_build_sync_execution_plan_defers_runtime_backed_renders_until_after_delivery_truth_settles(
    tmp_path: Path,
) -> None:
    impact = governance.DashboardImpact(
        radar=True,
        atlas=True,
        compass=True,
        registry=True,
        casebook=True,
        reasons={},
    )
    args = sync_workstream_artifacts._parse_args(  # noqa: SLF001
        [
            "--repo-root",
            str(tmp_path),
            "--force",
        ]
    )

    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=args,
        changed_paths=("odylith/atlas/source/odylith-product-governance-loop.mmd",),
        impact=impact,
        impact_tooling_shell=True,
        runtime_mode="auto",
    )

    modules = [
        command[2]
        for step in plan.steps
        if step.command is not None and len(step.command) >= 3 and step.command[:2] == ("python", "-m")
        for command in (step.command,)
    ]
    atlas_update_index = modules.index("odylith.runtime.surfaces.auto_update_mermaid_diagrams")
    atlas_render_index = modules.index("odylith.runtime.surfaces.render_mermaid_catalog_refresh")
    registry_sync_index = modules.index("odylith.runtime.governance.sync_component_spec_requirements")
    delivery_index = modules.index("odylith.runtime.governance.delivery_intelligence_refresh")
    compass_index = modules.index("odylith.runtime.surfaces.render_compass_dashboard")
    radar_index = modules.index("odylith.runtime.surfaces.render_backlog_ui")
    registry_render_index = modules.index("odylith.runtime.surfaces.render_registry_dashboard")
    casebook_render_index = modules.index("odylith.runtime.surfaces.render_casebook_dashboard")
    tooling_render_index = modules.index("odylith.runtime.surfaces.render_tooling_dashboard")

    assert atlas_update_index < atlas_render_index
    assert atlas_render_index < registry_sync_index
    assert registry_sync_index < delivery_index
    assert delivery_index < compass_index
    assert compass_index < radar_index
    assert radar_index < registry_render_index
    assert registry_render_index < casebook_render_index
    assert casebook_render_index < tooling_render_index


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


def test_full_mode_sync_skips_governance_runtime_packet_without_eager_default_runtime_warmup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    executed: list[tuple[str, ...]] = []

    class _Meaningful:
        def as_dict(self) -> dict[str, int]:
            return {
                "linked_meaningful_event_count": 0,
                "unlinked_meaningful_event_count": 0,
            }

    def _fake_run_command_in_process(*, repo_root: Path, args: tuple[str, ...], heartbeat_label: str = "") -> int:  # noqa: ARG001
        executed.append(tuple(args))
        return 0

    monkeypatch.setattr(sync_workstream_artifacts, "_effective_changed_paths", lambda **_: ("odylith/radar/source/INDEX.md",))
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_runtime_fast_path_prerequisites_met", lambda _repo_root: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_run_command_in_process", _fake_run_command_in_process)
    monkeypatch.setattr(sync_workstream_artifacts, "_sync_changed_source_truth_bundle_mirrors", lambda **_: 0)
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "build_dashboard_impact",
        lambda **_: SimpleNamespace(
            radar=False,
            atlas=False,
            compass=False,
            registry=False,
            casebook=False,
            tooling_shell=False,
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_context_engine_store",
        lambda: SimpleNamespace(
            build_governance_slice=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("full-mode sync should not build the governance runtime packet")
            ),
            record_runtime_timing=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("full-mode sync should not record governance packet timing")
            ),
            warm_projections=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("full-mode sync should not pay an eager runtime warmup before mutation steps settle")
            ),
            clear_runtime_process_caches=lambda **_kwargs: None,
        ),
    )

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--impact-mode", "full"])

    assert rc == 0
    assert executed


def test_dashboard_refresh_skips_component_spec_sync_for_shell_facing_refresh(tmp_path: Path, monkeypatch) -> None:
    executed: list[tuple[str, ...]] = []
    compass_calls: list[dict[str, object]] = []

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
    monkeypatch.setattr(
        sync_workstream_artifacts.compass_refresh_runtime,
        "run_refresh",
        lambda **kwargs: compass_calls.append(dict(kwargs))
        or {
            "rc": 0,
            "status": "queued",
            "request_id": "compass-1",
            "state": {"next_command": "odylith compass refresh --repo-root . --status"},
        },
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("tooling_shell", "radar", "compass"),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert rc == 0
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    assert "odylith.runtime.governance.delivery_intelligence_refresh" in modules
    assert "odylith.runtime.surfaces.render_backlog_ui" in modules
    assert "odylith.runtime.surfaces.render_tooling_dashboard" in modules
    assert compass_calls == [
        {
            "repo_root": tmp_path,
            "requested_profile": "shell-safe",
            "requested_runtime_mode": "auto",
            "wait": True,
            "status_only": False,
            "emit_output": True,
            "skip_settlement": True,
        }
    ]
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


def test_dashboard_refresh_uses_in_process_runtime_for_single_surface_fast_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    executed: list[tuple[str, ...]] = []

    def _fake_run_command_in_process(
        *,
        repo_root: Path,
        args: tuple[str, ...],
        heartbeat_label: str = "",
        timeout_seconds: float | None = None,
    ) -> int:  # noqa: ARG001
        executed.append(tuple(args))
        assert timeout_seconds is None
        return 0

    monkeypatch.setattr(sync_workstream_artifacts, "_runtime_fast_path_prerequisites_met", lambda _repo_root: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_run_command_in_process", _fake_run_command_in_process)
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_run_command",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("single-surface fast path should not shell out")),
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("radar",),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert rc == 0
    assert executed == [
        ("python", "-m", "odylith.runtime.surfaces.render_backlog_ui", "--repo-root", str(tmp_path))
    ]


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


def test_dashboard_refresh_plan_says_tooling_shell_does_not_rerender_compass(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(sync_workstream_artifacts, "_atlas_stale_diagram_count", lambda **kwargs: 0)

    plan = sync_workstream_artifacts.build_dashboard_refresh_plan(
        repo_root=tmp_path,
        surfaces=("tooling_shell",),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert any(
        note
        == (
            "`tooling_shell` refresh rerenders the parent shell wrapper only. "
            "It does not rewrite `odylith/compass/runtime/current.v1.json`; if the visible Compass brief is stale, run "
            "odylith compass refresh --repo-root ."
        )
        for note in plan.notes
    )


def test_check_only_sync_plan_reports_visible_compass_runtime_truth_drift(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        sync_workstream_artifacts.release_truth_runtime,
        "build_compass_runtime_truth_drift",
        lambda **_kwargs: {
            "warning": (
                "Release truth for 0.1.11 now targets B-068 and completes B-067, while the visible Compass snapshot "
                "targets B-067 and completes none. Run `odylith compass refresh --repo-root .` to refresh the Compass runtime snapshot."
            )
        },
    )
    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text("{}\n", encoding="utf-8")

    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=True,
            force=False,
            impact_mode="focused",
            registry_policy_mode="warn",
            enforce_deep_skills=False,
            no_traceability_autofix=False,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=(),
        impact=SimpleNamespace(atlas=False),
        impact_tooling_shell=False,
        runtime_mode="standalone",
    )

    assert any(note.startswith("Visible Compass runtime drift: Release truth for 0.1.11 now targets B-068") for note in plan.notes)


def test_sync_changed_source_truth_bundle_mirrors_updates_changed_docs(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    live_path = repo_root / "odylith" / "agents-guidelines" / "DELIVERY_AND_GOVERNANCE_SURFACES.md"
    mirror_path = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "agents-guidelines"
        / "DELIVERY_AND_GOVERNANCE_SURFACES.md"
    )
    live_path.parent.mkdir(parents=True, exist_ok=True)
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("change-driven watcher\n", encoding="utf-8")
    mirror_path.write_text("stale watcher\n", encoding="utf-8")

    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_git_changed_paths",
        lambda *, repo_root: ("odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md",),
    )

    rc = sync_workstream_artifacts._sync_changed_source_truth_bundle_mirrors(repo_root=repo_root)  # noqa: SLF001

    assert rc == 0
    assert mirror_path.read_text(encoding="utf-8") == "change-driven watcher\n"


def test_sync_changed_source_truth_bundle_mirrors_updates_runtime_source_corpus(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    live_path = repo_root / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    mirror_path = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "runtime"
        / "source"
        / "optimization-evaluation-corpus.v1.json"
    )
    live_path.parent.mkdir(parents=True, exist_ok=True)
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("{\"version\": \"v1\", \"scenarios\": [\"fresh\"]}\n", encoding="utf-8")
    mirror_path.write_text("{\"version\": \"v1\", \"scenarios\": [\"stale\"]}\n", encoding="utf-8")

    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_git_changed_paths",
        lambda *, repo_root: ("odylith/runtime/source/optimization-evaluation-corpus.v1.json",),
    )

    rc = sync_workstream_artifacts._sync_changed_source_truth_bundle_mirrors(repo_root=repo_root)  # noqa: SLF001

    assert rc == 0
    assert mirror_path.read_text(encoding="utf-8") == "{\"version\": \"v1\", \"scenarios\": [\"fresh\"]}\n"


def test_sync_changed_source_truth_bundle_mirrors_scopes_to_explicit_paths_without_git_scan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    live_path = repo_root / "odylith" / "casebook" / "bugs" / "2026-04-14-fast-path.md"
    mirror_path = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "casebook"
        / "bugs"
        / "2026-04-14-fast-path.md"
    )
    live_path.parent.mkdir(parents=True, exist_ok=True)
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text("fresh bug\n", encoding="utf-8")
    mirror_path.write_text("stale bug\n", encoding="utf-8")

    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_git_changed_paths",
        lambda **_: (_ for _ in ()).throw(AssertionError("explicit changed-path mirror sync should not rescan git")),
    )

    rc = sync_workstream_artifacts._sync_changed_source_truth_bundle_mirrors(  # noqa: SLF001
        repo_root=repo_root,
        changed_paths=("odylith/casebook/bugs/2026-04-14-fast-path.md",),
    )

    assert rc == 0
    assert mirror_path.read_text(encoding="utf-8") == "fresh bug\n"


def test_build_sync_execution_plan_appends_source_bundle_mirror_step(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="focused",
            registry_policy_mode="warn",
            enforce_deep_skills=False,
            no_traceability_autofix=True,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=("odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md",),
        impact=SimpleNamespace(atlas=False),
        impact_tooling_shell=False,
        runtime_mode="standalone",
    )

    mirror_steps = [
        step
        for step in plan.steps
        if step.label == "Mirror changed source-truth docs into the shipped bundle asset tree."
    ]
    assert len(mirror_steps) == 1
    assert mirror_steps[0].action is not None


def test_build_sync_execution_plan_runs_final_registry_reconcile_after_bundle_mirror(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="focused",
            registry_policy_mode="warn",
            enforce_deep_skills=False,
            no_traceability_autofix=True,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=("odylith/registry/source/components/odylith/CURRENT_SPEC.md",),
        impact=SimpleNamespace(
            atlas=False,
            radar=False,
            compass=False,
            registry=True,
            casebook=False,
        ),
        impact_tooling_shell=True,
        runtime_mode="standalone",
    )

    labels = [step.label for step in plan.steps]
    mirror_index = labels.index("Mirror changed source-truth docs into the shipped bundle asset tree.")
    final_registry_sync_index = labels.index(
        "Re-sync Registry component spec requirements after later shell-facing and mirror refresh steps settle."
    )

    assert mirror_index < final_registry_sync_index


def test_build_sync_execution_plan_uses_owned_surface_selective_lane_for_governance_memory_slice(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="selective",
            registry_policy_mode="advisory",
            enforce_deep_skills=False,
            no_traceability_autofix=False,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=(
            "odylith/casebook/bugs/2026-04-14-memory-bug.md",
            "odylith/technical-plans/in-progress/2026-04-14-memory-fix.md",
            "odylith/registry/source/components/compass/CURRENT_SPEC.md",
        ),
        impact=SimpleNamespace(
            atlas=False,
            radar=True,
            compass=False,
            registry=True,
            casebook=True,
        ),
        impact_tooling_shell=True,
        runtime_mode="standalone",
    )

    labels = [step.label for step in plan.steps]

    assert plan.headline == "Sync only the governed truth for the explicit selective slice in `standalone` mode."
    assert "Normalize legacy Radar backlog sections for the touched selective slice before validation." in labels
    assert "Refresh the Casebook bug index before rerendering the Casebook dashboard." in labels
    assert "Render Casebook for the updated bug index." in labels
    assert "Render Radar without widening into the full governance sync pipeline." in labels
    assert "Render Registry without re-running broader governance reconciliation." in labels
    assert "Mirror the touched source-truth docs into the shipped bundle asset tree." in labels
    assert "Validate Registry contract and deep-skill policy bindings." not in labels
    assert "Sync Registry component spec requirements after Atlas mutations settle." not in labels
    assert "Render the top-level Odylith shell after the selected surfaces settle." not in labels
    assert any(
        "Selective owned-surface sync keeps the projection compiler plus local LanceDB/Tantivy memory backend fresh"
        in note
        for note in plan.notes
    )


def test_requires_sync_treats_casebook_bug_markdown_as_sync_relevant(tmp_path: Path) -> None:
    assert sync_workstream_artifacts._requires_sync(
        repo_root=tmp_path,
        changed_paths=("odylith/casebook/bugs/2026-04-14-memory-bug.md",),
        force=False,
    )


def test_build_sync_execution_plan_refreshes_registry_for_spec_only_selective_slice(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="selective",
            registry_policy_mode="advisory",
            enforce_deep_skills=False,
            no_traceability_autofix=False,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=("odylith/registry/source/components/odylith/CURRENT_SPEC.md",),
        impact=SimpleNamespace(
            atlas=False,
            radar=False,
            compass=False,
            registry=True,
            casebook=False,
        ),
        impact_tooling_shell=True,
        runtime_mode="standalone",
    )

    labels = [step.label for step in plan.steps]

    assert "Refresh delivery intelligence inputs for this shell-facing surface." in labels
    assert "Render Registry without re-running broader governance reconciliation." in labels
    assert "Render the top-level Odylith shell after the selected surfaces settle." not in labels


def test_build_sync_execution_plan_refreshes_atlas_for_catalog_only_selective_slice(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="selective",
            registry_policy_mode="advisory",
            enforce_deep_skills=False,
            no_traceability_autofix=False,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=("odylith/atlas/source/catalog/diagrams.v1.json",),
        impact=SimpleNamespace(
            atlas=True,
            radar=False,
            compass=False,
            registry=False,
            casebook=False,
        ),
        impact_tooling_shell=False,
        runtime_mode="standalone",
    )

    labels = [step.label for step in plan.steps]

    assert "Refresh stale Atlas Mermaid diagrams before rerendering the Atlas surface." in labels
    assert "Render Atlas from the current Mermaid catalog state." in labels
    assert "Render the top-level Odylith shell after the selected surfaces settle." not in labels


def test_build_sync_execution_plan_validates_radar_for_backlog_only_selective_slice(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="selective",
            registry_policy_mode="advisory",
            enforce_deep_skills=False,
            no_traceability_autofix=False,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=("odylith/radar/source/ideas/2026-04/2026-04-14-fast-lane.md",),
        impact=SimpleNamespace(
            atlas=False,
            radar=True,
            compass=False,
            registry=False,
            casebook=False,
        ),
        impact_tooling_shell=True,
        runtime_mode="standalone",
    )

    labels = [step.label for step in plan.steps]

    assert "Normalize legacy Radar backlog sections for the touched selective slice before validation." in labels
    assert "Validate Radar backlog contract for the touched selective slice." in labels
    assert "Render Radar without widening into the full governance sync pipeline." in labels


def test_build_sync_execution_plan_final_registry_reconcile_triggers_delivery_stabilization(tmp_path: Path) -> None:
    plan = sync_workstream_artifacts.build_sync_execution_plan(
        repo_root=tmp_path,
        args=SimpleNamespace(
            check_only=False,
            force=False,
            impact_mode="focused",
            registry_policy_mode="warn",
            enforce_deep_skills=False,
            no_traceability_autofix=True,
            proceed_with_overlap=False,
            dry_run=False,
        ),
        changed_paths=("odylith/registry/source/components/odylith/CURRENT_SPEC.md",),
        impact=SimpleNamespace(
            atlas=True,
            radar=True,
            compass=True,
            registry=True,
            casebook=False,
        ),
        impact_tooling_shell=True,
        runtime_mode="standalone",
    )

    final_registry_step = next(
        step
        for step in plan.steps
        if step.label == "Re-sync Registry component spec requirements after later shell-facing and mirror refresh steps settle."
    )

    assert final_registry_step.change_watch_paths == ("odylith/registry/source/components/",)
    assert final_registry_step.followup_steps_on_change
    assert final_registry_step.followup_steps_on_change[0].label == "Refresh delivery intelligence after final Registry truth settles."
    assert final_registry_step.followup_steps_on_change[0].followup_steps_on_change


def test_execute_plan_runs_change_followups_only_when_watched_inputs_mutate(tmp_path: Path) -> None:
    watched_path = tmp_path / "watched.txt"
    watched_path.write_text("before", encoding="utf-8")
    executed: list[str] = []

    def _mutate_watched() -> int:
        watched_path.write_text("after", encoding="utf-8")
        executed.append("primary")
        return 0

    def _record_followup() -> int:
        executed.append("followup")
        return 0

    plan = sync_workstream_artifacts.ExecutionPlan(
        headline="test",
        steps=(
            sync_workstream_artifacts.ExecutionStep(
                label="mutate watched input",
                action=_mutate_watched,
                change_watch_paths=("watched.txt",),
                followup_steps_on_change=(
                    sync_workstream_artifacts.ExecutionStep(
                        label="followup",
                        action=_record_followup,
                    ),
                ),
            ),
        ),
        dirty_overlap=(),
    )

    rc = sync_workstream_artifacts._execute_plan(  # noqa: SLF001
        repo_root=tmp_path,
        plan_name="workstream sync",
        plan=plan,
        run_impl=lambda **_: 0,
        runtime_fallback_used=False,
    )

    assert rc == 0
    assert executed == ["primary", "followup"]


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
    monkeypatch.setattr(
        sync_workstream_artifacts.compass_refresh_runtime,
        "run_refresh",
        lambda **kwargs: {
            "rc": 1,
            "status": "failed",
            "request_id": "compass-1",
            "state": {
                "next_command": "odylith dashboard refresh --repo-root . --surfaces compass"
            },
        },
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("compass", "radar", "tooling_shell"),
        runtime_mode="standalone",
    )
    output = capsys.readouterr().out

    assert rc == 2
    modules = [command[2] for command in executed if len(command) >= 3 and command[0] == "python" and command[1] == "-m"]
    assert "odylith.runtime.surfaces.render_backlog_ui" in modules
    assert "odylith.runtime.surfaces.render_tooling_dashboard" in modules
    assert "- compass: failed" in output
    assert "- radar: passed" in output
    assert "- tooling_shell: passed" in output
    assert "next: odylith dashboard refresh --repo-root . --surfaces compass" in output


def test_dashboard_refresh_compass_waits_for_shared_engine_and_reports_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    refresh_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_run_command",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Compass compatibility path should not shell out directly")),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.compass_refresh_runtime,
        "run_refresh",
        lambda **kwargs: refresh_calls.append(dict(kwargs))
        or {
            "rc": 124,
            "status": "failed",
            "request_id": "compass-refresh",
            "state": {
                "next_command": "odylith dashboard refresh --repo-root . --surfaces compass"
            },
        },
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("compass",),
        runtime_mode="standalone",
    )
    output = capsys.readouterr().out

    assert rc == 2
    assert refresh_calls == [
        {
            "repo_root": tmp_path,
            "requested_profile": "shell-safe",
            "requested_runtime_mode": "standalone",
            "wait": True,
            "status_only": False,
            "emit_output": True,
            "skip_settlement": True,
        }
    ]
    assert "next: odylith dashboard refresh --repo-root . --surfaces compass" in output


def test_dashboard_refresh_compass_waits_for_terminal_success(tmp_path: Path, monkeypatch, capsys) -> None:
    refresh_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_run_command",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Compass compatibility path should not shell out directly")),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.compass_refresh_runtime,
        "run_refresh",
        lambda **kwargs: refresh_calls.append(dict(kwargs))
        or {
            "rc": 0,
            "status": "passed",
            "request_id": "compass-refresh",
            "state": {},
        },
    )

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=tmp_path,
        surfaces=("compass",),
        runtime_mode="auto",
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert refresh_calls == [
        {
            "repo_root": tmp_path,
            "requested_profile": "shell-safe",
            "requested_runtime_mode": "auto",
            "wait": True,
            "status_only": False,
            "emit_output": True,
            "skip_settlement": True,
        }
    ]
    assert "- compass: passed" in output
    assert "- compass: queued" not in output


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


def test_run_callable_with_heartbeat_reports_progress(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync_workstream_artifacts, "_HEARTBEAT_START_DELAY_SECONDS", 0.01)
    monkeypatch.setattr(sync_workstream_artifacts, "_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    rc = sync_workstream_artifacts._run_callable_with_heartbeat(  # noqa: SLF001
        label="slow-step",
        callable_=lambda: (time.sleep(0.03), 0)[1],
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "heartbeat: slow-step still running" in output


def test_run_callable_with_heartbeat_stays_quiet_for_fast_steps(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync_workstream_artifacts, "_HEARTBEAT_START_DELAY_SECONDS", 0.05)
    monkeypatch.setattr(sync_workstream_artifacts, "_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    rc = sync_workstream_artifacts._run_callable_with_heartbeat(  # noqa: SLF001
        label="fast-step",
        callable_=lambda: (time.sleep(0.01), 0)[1],
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "heartbeat: fast-step still running" not in output


def test_run_command_in_process_skips_heartbeat_for_fast_in_process_modules(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class _Module:
        @staticmethod
        def main(argv: list[str]) -> int:
            calls.append("main")
            assert argv == ["--repo-root", str(tmp_path)]
            return 0

    monkeypatch.setattr(
        sync_workstream_artifacts.importlib,
        "import_module",
        lambda name: _Module() if name == "odylith.runtime.governance.validate_backlog_contract" else None,
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_run_callable_with_heartbeat",
        lambda **_: (_ for _ in ()).throw(AssertionError("fast in-process modules should not use heartbeat wrapping")),
    )

    rc = sync_workstream_artifacts._run_command_in_process(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.governance.validate_backlog_contract", "--repo-root", str(tmp_path)),
        heartbeat_label="validate backlog",
    )

    assert rc == 0
    assert calls == ["main"]


def test_run_command_in_process_keeps_heartbeat_for_long_render_modules(monkeypatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    class _Module:
        @staticmethod
        def main(argv: list[str]) -> int:
            observed["argv"] = list(argv)
            return 0

    monkeypatch.setattr(
        sync_workstream_artifacts.importlib,
        "import_module",
        lambda name: _Module() if name == "odylith.runtime.surfaces.render_compass_dashboard" else None,
    )

    def _fake_run_callable_with_heartbeat(*, label: str, callable_):  # noqa: ANN001
        observed["label"] = label
        return int(callable_() or 0)

    monkeypatch.setattr(sync_workstream_artifacts, "_run_callable_with_heartbeat", _fake_run_callable_with_heartbeat)

    rc = sync_workstream_artifacts._run_command_in_process(  # noqa: SLF001
        repo_root=tmp_path,
        args=("python", "-m", "odylith.runtime.surfaces.render_compass_dashboard", "--repo-root", str(tmp_path)),
        heartbeat_label="render compass",
    )

    assert rc == 0
    assert observed["label"] == "render compass"
    assert observed["argv"] == ["--repo-root", str(tmp_path)]


def test_sync_blocks_large_dirty_overlap_without_explicit_ack(monkeypatch, tmp_path: Path, capsys) -> None:
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
            radar=False,
            atlas=False,
            compass=False,
            registry=False,
            casebook=False,
            tooling_shell=False,
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "build_sync_execution_plan",
        lambda **_: sync_workstream_artifacts.ExecutionPlan(
            headline="preview",
            steps=(),
            dirty_overlap=tuple(f"M path-{index}" for index in range(50)),
            notes=(),
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_execute_plan",
        lambda **_: (_ for _ in ()).throw(AssertionError("blocked sync should not execute plan")),
    )

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--force"])
    output = capsys.readouterr().out

    assert rc == 2
    assert "workstream sync blocked" in output
    assert "--proceed-with-overlap" in output


def test_sync_allows_large_dirty_overlap_with_explicit_ack(monkeypatch, tmp_path: Path) -> None:
    class _Meaningful:
        def as_dict(self) -> dict[str, int]:
            return {
                "linked_meaningful_event_count": 0,
                "unlinked_meaningful_event_count": 0,
            }

    executed = {"value": False}

    monkeypatch.setattr(sync_workstream_artifacts, "_effective_changed_paths", lambda **_: ("odylith/radar/source/INDEX.md",))
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_use_runtime_fast_path", lambda _mode: False)
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "build_dashboard_impact",
        lambda **_: SimpleNamespace(
            radar=False,
            atlas=False,
            compass=False,
            registry=False,
            casebook=False,
            tooling_shell=False,
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "build_sync_execution_plan",
        lambda **_: sync_workstream_artifacts.ExecutionPlan(
            headline="preview",
            steps=(),
            dirty_overlap=tuple(f"M path-{index}" for index in range(50)),
            notes=(),
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_execute_plan",
        lambda **_: executed.__setitem__("value", True) or 0,
    )

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--force", "--proceed-with-overlap"])

    assert rc == 0
    assert executed["value"] is True


def test_sync_preflight_summarizes_backlog_contract_blockers(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(sync_workstream_artifacts, "_effective_changed_paths", lambda **_: ("odylith/radar/source/INDEX.md",))
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_backlog_contract_preflight_ready", lambda _repo_root: True)
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "normalize_legacy_backlog_index",
        lambda **_: SimpleNamespace(
            changed=True,
            normalized_sections=("B-001", "B-002"),
            added_sections=("B-002",),
            normalized_idea_specs=(),
            normalized_table_sections=(),
            backlog_index=tmp_path / "odylith" / "radar" / "source" / "INDEX.md",
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "collect_backlog_contract_errors",
        lambda **_: (
            "odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`",
            "odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`",
            "odylith/radar/source/INDEX.md: priority override idea `B-002` missing `ranking basis` bullet",
        ),
    )

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--force"])
    output = capsys.readouterr().out

    assert rc == 2
    assert "workstream sync legacy normalization" in output
    assert "- added_sections: 1" in output
    assert "- source: odylith/radar/source/INDEX.md" in output
    assert "2x odylith/radar/source/INDEX.md: reorder rationale for `B-001` missing `- why now:`" in output
    assert "priority override idea `B-002` missing `ranking basis` bullet" in output
    assert "Finish the normalized rationale blocks in `odylith/radar/source/INDEX.md`" in output


def test_sync_auto_normalizes_legacy_backlog_before_continuing(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = _seed_sync_repo_with_legacy_backlog(tmp_path)

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
            radar=False,
            atlas=False,
            compass=False,
            registry=False,
            casebook=False,
            tooling_shell=False,
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

    rc = sync_workstream_artifacts.main(["--repo-root", str(repo_root), "--force", "--dry-run"])
    output = capsys.readouterr().out
    backlog_index = (repo_root / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")
    queued_idea = (
        repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-06-legacy-sync-fix.md"
    ).read_text(encoding="utf-8")

    assert rc == 0
    assert "workstream sync legacy normalization" in output
    assert "- added_sections: " in output
    assert "- idea_schema_updates: 2" in output
    assert "- table_schema_updates: 3" in output
    assert "- source: odylith/radar/source/INDEX.md" in output
    assert "odylith sync did not complete." not in output
    assert "workstream sync dry-run" in output
    assert "impacted_lanes" not in backlog_index
    assert "impacted_lanes" not in queued_idea
    assert "- expected outcome: clearer product truth and faster follow-on implementation planning." in backlog_index
    assert "- tradeoff: queued with sizing and complexity assumptions that should be validated when implementation begins." in backlog_index
    assert "- deferred for now: deeper scope decomposition waits until the implementation owner starts the workstream." in backlog_index
    assert "- ranking basis: score-based rank; no manual priority override." in backlog_index


def test_sync_truth_only_selective_slice_skips_broad_preflight_and_runtime_packet(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    class _Meaningful:
        def as_dict(self) -> dict[str, int]:
            return {
                "linked_meaningful_event_count": 0,
                "unlinked_meaningful_event_count": 0,
            }

    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_effective_changed_paths",
        lambda **_: (
            "odylith/casebook/bugs/2026-04-14-fast-bug.md",
            "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        ),
    )
    monkeypatch.setattr(sync_workstream_artifacts, "_requires_sync", lambda **_: True)
    monkeypatch.setattr(sync_workstream_artifacts, "_backlog_contract_preflight_ready", lambda _repo_root: True)
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "normalize_legacy_backlog_index",
        lambda **_: (_ for _ in ()).throw(AssertionError("narrow truth-only sync should skip backlog preflight normalization")),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "collect_backlog_contract_errors",
        lambda **_: (_ for _ in ()).throw(AssertionError("narrow truth-only sync should skip backlog preflight validation")),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts,
        "_context_engine_store",
        lambda: SimpleNamespace(
            build_governance_slice=lambda **_: (_ for _ in ()).throw(
                AssertionError("narrow truth-only sync should skip governance runtime packet build")
            ),
            record_runtime_timing=lambda **_: (_ for _ in ()).throw(
                AssertionError("narrow truth-only sync should skip governance runtime packet timing")
            ),
            clear_runtime_process_caches=lambda **_: None,
        ),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "build_dashboard_impact",
        lambda **_: (_ for _ in ()).throw(AssertionError("narrow truth-only sync should not use heuristic broad impact build")),
    )
    monkeypatch.setattr(
        sync_workstream_artifacts.governance,
        "collect_meaningful_activity_evidence",
        lambda **_: _Meaningful(),
    )

    def _capture_plan(**kwargs):  # noqa: ANN001
        captured["impact"] = kwargs["impact"]
        return sync_workstream_artifacts.ExecutionPlan(
            headline="preview",
            steps=(),
            dirty_overlap=(),
            notes=(),
        )

    monkeypatch.setattr(sync_workstream_artifacts, "build_sync_execution_plan", _capture_plan)

    rc = sync_workstream_artifacts.main(["--repo-root", str(tmp_path), "--impact-mode", "selective", "--dry-run"])

    assert rc == 0
    impact = captured["impact"]
    assert bool(getattr(impact, "casebook", False)) is True
    assert bool(getattr(impact, "registry", False)) is True
    assert bool(getattr(impact, "radar", False)) is False
    assert bool(getattr(impact, "atlas", False)) is False
