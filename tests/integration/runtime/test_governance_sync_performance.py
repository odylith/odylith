"""End-to-end performance guards for governed sync surfaces."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from odylith.runtime.governance import sync_workstream_artifacts


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
ALL_DASHBOARD_SURFACES = "tooling_shell,radar,atlas,compass,registry,casebook"
BACKLOG_TABLE_HEADER = (
    "| rank | idea_id | title | priority | ordering_score | commercial_value | "
    "product_impact | market_value | sizing | complexity | status | link |\n"
)
BACKLOG_TABLE_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"


@dataclass(frozen=True)
class CliPerfCase:
    name: str
    argv: tuple[str, ...]
    budget_seconds: float
    expected_output: tuple[str, ...]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_perf_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "consumer"
    repo_root.mkdir()
    _write(repo_root / "consumer_repo.yaml", "repo: governance-sync-perf\n")
    empty_backlog_table = BACKLOG_TABLE_HEADER + BACKLOG_TABLE_SEPARATOR
    _write(
        repo_root / "odylith" / "radar" / "source" / "INDEX.md",
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-05-02\n"
            "## Ranked Active Backlog\n\n"
            f"{empty_backlog_table}"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress` or an active parent wave)\n\n"
            f"{empty_backlog_table}"
            "## Parked (No Active Plan)\n\n"
            f"{empty_backlog_table}"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            f"{empty_backlog_table}"
            "## Reorder Rationale Log\n"
        ),
    )
    (repo_root / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)
    _write(
        repo_root / "odylith" / "technical-plans" / "INDEX.md",
        (
            "# Plan Index\n\n"
            "## Active Plans\n\n"
            "| Plan | Status | Created | Updated | Backlog |\n"
            "| --- | --- | --- | --- | --- |\n"
        ),
    )
    _write(
        repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json",
        '{"version":"v1","components":[]}\n',
    )
    (repo_root / "odylith" / "registry" / "source" / "components").mkdir(parents=True, exist_ok=True)
    _write(
        repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json",
        '{"version":"v1","diagrams":[]}\n',
    )
    _write(repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md", "# Casebook Index\n")
    _write(
        repo_root / "odylith" / "radar" / "traceability-graph.v1.json",
        '{"version":"v1","workstreams":[]}\n',
    )
    (repo_root / "odylith" / "compass" / "runtime").mkdir(parents=True, exist_ok=True)
    return repo_root


def _write_provider_tripwire(tmp_path: Path) -> tuple[Path, Path]:
    sentinel = tmp_path / "provider-tripwire.invoked"
    executable = tmp_path / "provider-tripwire.py"
    _write(
        executable,
        (
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "import os\n"
            "import sys\n"
            "target = os.environ.get('ODYLITH_PROVIDER_TRIPWIRE_PATH')\n"
            "if target:\n"
            "    Path(target).write_text('provider invoked: ' + ' '.join(sys.argv) + '\\n', encoding='utf-8')\n"
            "sys.exit(97)\n"
        ),
    )
    executable.chmod(0o755)
    return executable, sentinel


def _perf_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    tripwire, sentinel = _write_provider_tripwire(tmp_path)
    env = os.environ.copy()
    pythonpath = str(REPO_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    if existing_pythonpath:
        pythonpath = os.pathsep.join((pythonpath, existing_pythonpath))
    env.update(
        {
            "PYTHONPATH": pythonpath,
            "ODYLITH_REASONING_MODE": "auto",
            "ODYLITH_REASONING_PROVIDER": "codex-cli",
            "ODYLITH_REASONING_CODEX_BIN": str(tripwire),
            "ODYLITH_REASONING_CLAUDE_BIN": str(tripwire),
            "ODYLITH_REASONING_MODEL": "credit-tripwire",
            "ODYLITH_REASONING_TIMEOUT_SECONDS": "1",
            "ODYLITH_PROVIDER_TRIPWIRE_PATH": str(sentinel),
        }
    )
    return env, sentinel


def _scaled_budget(seconds: float) -> float:
    try:
        scale = float(os.environ.get("ODYLITH_E2E_PERF_BUDGET_SCALE", "1").strip() or "1")
    except ValueError:
        scale = 1.0
    return float(seconds) * max(1.0, scale)


def _run_cli_case(case: CliPerfCase, *, env: dict[str, str], sentinel: Path) -> float:
    started = time.perf_counter()
    completed = subprocess.run(
        [PYTHON, "-m", "odylith.cli", *case.argv],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=max(_scaled_budget(case.budget_seconds) + 10.0, 20.0),
    )
    elapsed = time.perf_counter() - started
    output = f"{completed.stdout}\n{completed.stderr}"

    assert completed.returncode == 0, f"{case.name} failed in {elapsed:.2f}s\n{output}"
    assert elapsed <= _scaled_budget(case.budget_seconds), (
        f"{case.name} exceeded latency budget: {elapsed:.2f}s > "
        f"{_scaled_budget(case.budget_seconds):.2f}s\n{output}"
    )
    for expected in case.expected_output:
        assert expected in output, f"{case.name} missed output `{expected}`\n{output}"
    assert not sentinel.exists(), (
        f"{case.name} invoked a provider-backed reasoning path:\n"
        f"{sentinel.read_text(encoding='utf-8') if sentinel.exists() else ''}\n{output}"
    )
    return elapsed


def test_governed_sync_operator_paths_stay_under_latency_budget_and_do_not_burn_credit(
    tmp_path: Path,
) -> None:
    repo_root = _seed_perf_repo(tmp_path)
    env, sentinel = _perf_env(tmp_path)
    cases = (
        CliPerfCase(
            name="full sync dry-run",
            argv=(
                "sync",
                "--repo-root",
                str(repo_root),
                "--dry-run",
                "--force",
                "--impact-mode",
                "full",
                "--runtime-mode",
                "auto",
            ),
            budget_seconds=8.0,
            expected_output=(
                "workstream sync impact plan",
                "workstream sync dry-run",
                "dry-run mode: no files written",
            ),
        ),
        CliPerfCase(
            name="all-surface dashboard refresh",
            argv=(
                "dashboard",
                "refresh",
                "--repo-root",
                str(repo_root),
                "--surfaces",
                ALL_DASHBOARD_SURFACES,
                "--runtime-mode",
                "auto",
            ),
            budget_seconds=20.0,
            expected_output=(
                "dashboard refresh completed",
                "- radar: passed",
                "- atlas: passed",
                "- compass: passed",
                "- registry: passed",
                "- casebook: passed",
                "- tooling_shell: passed",
            ),
        ),
        CliPerfCase(
            name="compass status refresh",
            argv=("compass", "refresh", "--repo-root", str(repo_root), "--status", "--runtime-mode", "auto"),
            budget_seconds=5.0,
            expected_output=("compass refresh status",),
        ),
        CliPerfCase(
            name="radar owned refresh dry-run",
            argv=("radar", "refresh", "--repo-root", str(repo_root), "--dry-run", "--runtime-mode", "auto"),
            budget_seconds=5.0,
            expected_output=("dashboard refresh dry-run", "radar"),
        ),
        CliPerfCase(
            name="atlas owned refresh dry-run",
            argv=("atlas", "refresh", "--repo-root", str(repo_root), "--dry-run", "--runtime-mode", "auto"),
            budget_seconds=5.0,
            expected_output=("dashboard refresh dry-run", "atlas"),
        ),
        CliPerfCase(
            name="registry owned refresh dry-run",
            argv=("registry", "refresh", "--repo-root", str(repo_root), "--dry-run", "--runtime-mode", "auto"),
            budget_seconds=5.0,
            expected_output=("dashboard refresh dry-run", "registry"),
        ),
        CliPerfCase(
            name="casebook owned refresh dry-run",
            argv=("casebook", "refresh", "--repo-root", str(repo_root), "--dry-run", "--runtime-mode", "auto"),
            budget_seconds=5.0,
            expected_output=("dashboard refresh dry-run", "casebook"),
        ),
    )

    elapsed_by_case = {case.name: _run_cli_case(case, env=env, sentinel=sentinel) for case in cases}

    assert sum(elapsed_by_case.values()) <= _scaled_budget(45.0), elapsed_by_case


def test_dashboard_refresh_plan_stays_model_free_for_local_surface_commands(tmp_path: Path) -> None:
    repo_root = _seed_perf_repo(tmp_path)
    plan = sync_workstream_artifacts.build_dashboard_refresh_plan(
        repo_root=repo_root,
        surfaces=ALL_DASHBOARD_SURFACES.split(","),
        runtime_mode="auto",
        atlas_sync=False,
    )

    command_text = "\n".join(" ".join(step.command) for step in plan.steps if step.command)
    forbidden_tokens = ("codex", "claude", "openai", "anthropic", "reasoning")

    assert plan.steps
    assert "odylith.runtime.surfaces.render_backlog_ui" in command_text
    assert "odylith.runtime.surfaces.render_registry_dashboard" in command_text
    assert "odylith.runtime.surfaces.render_tooling_dashboard" in command_text
    assert all(token not in command_text.lower() for token in forbidden_tokens)


def test_dashboard_refresh_keeps_multi_surface_work_parallel(tmp_path: Path, monkeypatch) -> None:
    repo_root = _seed_perf_repo(tmp_path)
    lock = threading.Lock()
    active_workers = 0
    max_active_workers = 0
    seen_surfaces: list[str] = []

    def fake_run_surface_worker(**kwargs):  # noqa: ANN003
        nonlocal active_workers, max_active_workers
        surface = str(kwargs["surface"])
        with lock:
            active_workers += 1
            max_active_workers = max(max_active_workers, active_workers)
        time.sleep(0.05)
        with lock:
            active_workers -= 1
            seen_surfaces.append(surface)
        return "", {"surface": surface, "status": "passed", "fallback_used": False}

    monkeypatch.setattr(sync_workstream_artifacts, "_run_surface_worker", fake_run_surface_worker)

    rc = sync_workstream_artifacts.refresh_dashboard_surfaces(
        repo_root=repo_root,
        surfaces=("radar", "atlas", "compass", "registry", "casebook"),
        runtime_mode="auto",
        atlas_sync=False,
    )

    assert rc == 0
    assert set(seen_surfaces) == {"radar", "atlas", "compass", "registry", "casebook"}
    assert max_active_workers >= 2
