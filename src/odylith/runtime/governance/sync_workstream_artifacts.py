"""Synchronize backlog workstream derived artifacts.

This command keeps rendered workstream views in sync with markdown source
artifacts whenever backlog/plan contracts change.

Behavior:
- always run governance and contract validators,
- selectively render impacted dashboard surfaces by default,
- support explicit `--impact-mode full` for deterministic full regeneration.
- support non-mutating check-only mode for pre-commit enforcement.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from odylith.runtime.common.command_surface import display_command, ensure_repo_root_args
from odylith.runtime.common.consumer_profile import surface_root_path, truth_root_path
from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import sync_casebook_bug_index


_SYNC_PATH_PREFIXES: tuple[str, ...] = (
    "AGENTS.md",
    "odylith/AGENTS.md",
    "odylith/radar/source/INDEX.md",
    "odylith/radar/source/ideas/",
    "odylith/radar/source/programs/",
    "odylith/radar/source/policy/",
    "odylith/radar/source/templates/",
    "odylith/radar/source/AGENTS.md",
    "odylith/technical-plans/INDEX.md",
    "odylith/technical-plans/AGENTS.md",
    "odylith/technical-plans/in-progress/",
    "odylith/technical-plans/parked/",
    "odylith/technical-plans/done/",
    "odylith/casebook/bugs/INDEX.md",
    "odylith/casebook/bugs/archive/",
    "odylith/agents-guidelines/",
    "odylith/skills/",
    "odylith/FAQ.md",
    "odylith/INSTALL.md",
    "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
    "odylith/OPERATING_MODEL.md",
    "odylith/PRODUCT_COMPONENTS.md",
    "odylith/registry/source/components/",
    "odylith/runtime/",
    "odylith/surfaces/",
    "odylith/registry/source/",
    "odylith/runtime/contracts/",
    "odylith/atlas/source/architecture-domains.v1.json",
    "odylith/atlas/source/catalog/",
    "odylith/atlas/source/",
    "odylith/compass/compass.html",
    "odylith/registry/registry.html",
    "odylith/casebook/casebook.html",
    "odylith/index.html",
)
_VALID_DASHBOARD_SURFACES: tuple[str, ...] = (
    "tooling_shell",
    "radar",
    "atlas",
    "compass",
    "registry",
    "casebook",
)
_SURFACE_RENDER_ORDER: tuple[str, ...] = (
    "compass",
    "radar",
    "atlas",
    "registry",
    "casebook",
    "tooling_shell",
)
_SURFACE_ALIASES: Mapping[str, str] = {
    "shell": "tooling_shell",
    "tooling-shell": "tooling_shell",
}
_SURFACE_DISPLAY_NAMES: Mapping[str, str] = {
    "tooling_shell": "tooling_shell",
    "radar": "radar",
    "compass": "compass",
    "atlas": "atlas",
    "registry": "registry",
    "casebook": "casebook",
}
_DEFAULT_COMPASS_REFRESH_PROFILE = "shell-safe"
_HEARTBEAT_INTERVAL_SECONDS = 10.0
_DASHBOARD_REFRESH_TIMEOUT_SECONDS = 45.0


def _context_engine_store():
    from odylith.runtime.context_engine import odylith_context_engine_store

    return odylith_context_engine_store


def _active_odylith_import_roots() -> tuple[str, ...]:
    roots: list[str] = []
    for candidate in (Path(__file__).resolve().parents[3],):
        token = str(candidate)
        if token not in roots:
            roots.append(token)
    return tuple(roots)


@dataclass(frozen=True)
class ExecutionStep:
    label: str
    surface: str = ""
    command: tuple[str, ...] = ()
    standalone_command: tuple[str, ...] = ()
    mutation_classes: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    next_command_on_failure: str = ""
    timeout_seconds: float | None = None
    action: Callable[[], int] | None = None


@dataclass(frozen=True)
class ExecutionPlan:
    headline: str
    steps: tuple[ExecutionStep, ...]
    dirty_overlap: tuple[str, ...]
    notes: tuple[str, ...] = ()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Sync backlog workstream validation + rendered UI artifacts.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--odylith-mode",
        default="",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run sync workflow even when changed paths are not matched.",
    )
    parser.add_argument(
        "--impact-mode",
        choices=("selective", "full"),
        default="selective",
        help="Dashboard rendering mode: selective impact render (default) or full render.",
    )
    clean_gate_group = parser.add_mutually_exclusive_group()
    clean_gate_group.add_argument(
        "--check-clean",
        action="store_true",
        help="Fail closed if generated workstream UI files remain dirty after sync, including staged changes.",
    )
    clean_gate_group.add_argument(
        "--check-commit-ready",
        action="store_true",
        help=(
            "Fail closed if generated workstream UI files do not match the staged commit payload. "
            "Staged-only generated outputs are allowed; unstaged and untracked drift is not."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help=(
            "Run non-mutating validation gates only (no reconcile/autofix/render writes). "
            "Intended for pre-commit enforcement."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the sync mutation plan and dirty-worktree overlap without writing files.",
    )
    parser.add_argument(
        "--no-traceability-autofix",
        action="store_true",
        help="Skip automatic traceability metadata backfill before validation/render.",
    )
    parser.add_argument(
        "--traceability-autofix-report",
        default="odylith/radar/traceability-autofix-report.v1.json",
        help="Output report path for traceability metadata autofix.",
    )
    parser.add_argument(
        "--policy-mode",
        choices=("advisory", "enforce-critical"),
        default="",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--registry-policy-mode",
        choices=("advisory", "enforce-critical"),
        default="enforce-critical",
        help="Policy mode used by component-registry validator.",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help=(
            "Execution mode for local upkeep commands. `auto` prefers the local runtime-backed "
            "fast path with standalone fallback, `standalone` preserves subprocess-only strict "
            "behavior, and `daemon` requires runtime-backed execution."
        ),
    )
    parser.add_argument(
        "--compass-refresh-profile",
        choices=("full", "shell-safe"),
        default=_DEFAULT_COMPASS_REFRESH_PROFILE,
        help=(
            "Compass refresh profile for sync/render steps. "
            "`shell-safe` defers live AI narration so sync stays bounded."
        ),
    )
    deep_skill_group = parser.add_mutually_exclusive_group()
    deep_skill_group.add_argument(
        "--enforce-deep-skills",
        dest="enforce_deep_skills",
        action="store_true",
        help="Fail closed on critical deep-skill policy findings in validator path.",
    )
    deep_skill_group.add_argument(
        "--no-enforce-deep-skills",
        dest="enforce_deep_skills",
        action="store_false",
        help="Disable critical deep-skill policy enforcement for ad-hoc local refreshes.",
    )
    parser.set_defaults(enforce_deep_skills=True)
    parser.add_argument(
        "--once",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max-interval-seconds",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "changed_paths",
        nargs="*",
        help="Changed paths (pre-commit passes these automatically).",
    )
    args = parser.parse_args(argv)
    if str(getattr(args, "policy_mode", "")).strip():
        args.registry_policy_mode = str(args.policy_mode).strip()
    return args


def _normalize_changed_paths(*, repo_root: Path, changed_paths: Sequence[str]) -> list[str]:
    return governance.normalize_changed_paths(repo_root=repo_root, values=changed_paths)


def _effective_changed_paths(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    force: bool,
) -> list[str]:
    normalized = _normalize_changed_paths(repo_root=repo_root, changed_paths=changed_paths)
    if normalized or force:
        return normalized
    return governance.collect_git_changed_paths(repo_root=repo_root)


def _requires_sync(*, repo_root: Path, changed_paths: Sequence[str], force: bool) -> bool:
    if force:
        return True
    normalized = _effective_changed_paths(
        repo_root=repo_root,
        changed_paths=changed_paths,
        force=force,
    )
    if not normalized:
        return False
    for token in normalized:
        if any(token == prefix or token.startswith(prefix) for prefix in _SYNC_PATH_PREFIXES):
            return True
    return False


def _execution_step(
    label: str,
    *,
    surface: str = "",
    command: Sequence[str] = (),
    standalone_command: Sequence[str] = (),
    mutation_classes: Sequence[str] = (),
    paths: Sequence[str] = (),
    next_command_on_failure: str = "",
    timeout_seconds: float | None = None,
    action: Callable[[], int] | None = None,
) -> ExecutionStep:
    return ExecutionStep(
        label=str(label).strip(),
        surface=str(surface).strip(),
        command=tuple(str(token).strip() for token in command if str(token).strip()),
        standalone_command=tuple(str(token).strip() for token in standalone_command if str(token).strip()),
        mutation_classes=tuple(str(token).strip() for token in mutation_classes if str(token).strip()),
        paths=tuple(str(token).strip() for token in paths if str(token).strip()),
        next_command_on_failure=str(next_command_on_failure).strip(),
        timeout_seconds=float(timeout_seconds) if timeout_seconds is not None else None,
        action=action,
    )


def _dirty_overlap_for_paths(*, repo_root: Path, paths: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(token).strip() for token in paths if str(token).strip()))
    if not normalized or not (repo_root / ".git").exists():
        return ()
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *normalized,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        return ()
    return tuple(line.rstrip() for line in str(completed.stdout or "").splitlines() if line.strip())


def _execution_plan(*, headline: str, steps: Sequence[ExecutionStep], notes: Sequence[str], repo_root: Path) -> ExecutionPlan:
    normalized_steps = tuple(steps)
    return ExecutionPlan(
        headline=str(headline).strip(),
        steps=normalized_steps,
        dirty_overlap=_dirty_overlap_for_paths(
            repo_root=repo_root,
            paths=[path for step in normalized_steps for path in step.paths],
        ),
        notes=tuple(str(token).strip() for token in notes if str(token).strip()),
    )


def _print_execution_plan(name: str, plan: ExecutionPlan, *, dry_run: bool) -> None:
    print(f"{name} {'dry-run' if dry_run else 'plan'}")
    if plan.headline:
        print(f"- summary: {plan.headline}")
    for index, step in enumerate(plan.steps, start=1):
        print(f"- step {index}/{len(plan.steps)}: {step.label}")
        if step.mutation_classes:
            print(f"  mutation_classes: {', '.join(step.mutation_classes)}")
        if step.paths:
            preview = ", ".join(step.paths[:4])
            suffix = "" if len(step.paths) <= 4 else f", +{len(step.paths) - 4} more"
            print(f"  paths: {preview}{suffix}")
    if plan.dirty_overlap:
        print("- dirty_overlap:")
        for line in plan.dirty_overlap:
            print(f"  {line}")
    if plan.notes:
        print("- notes:")
        for note in plan.notes:
            print(f"  {note}")
    if dry_run:
        print("dry-run mode: no files written")


def _run_command(
    *,
    repo_root: Path,
    args: Sequence[str],
    heartbeat_label: str = "",
    timeout_seconds: float | None = None,
) -> int:
    env = os.environ.copy()
    cwd = Path.cwd()
    pythonpath_tokens: list[str] = []
    for token in _active_odylith_import_roots():
        if token not in pythonpath_tokens:
            pythonpath_tokens.append(token)
    raw_pythonpath = str(env.get("PYTHONPATH", "")).strip()
    if raw_pythonpath:
        for token in raw_pythonpath.split(os.pathsep):
            normalized = str((cwd / token).resolve()) if token and not Path(token).is_absolute() else token
            if normalized and normalized not in pythonpath_tokens:
                pythonpath_tokens.append(normalized)
    if pythonpath_tokens:
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_tokens)
    tokens = [str(token) for token in args]
    if tokens and tokens[0] == "python":
        tokens[0] = sys.executable
    if heartbeat_label or timeout_seconds is not None:
        started_at = time.perf_counter()
        last_heartbeat = started_at
        popen_kwargs: dict[str, Any] = {
            "cwd": str(repo_root),
            "env": env,
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(tokens, **popen_kwargs)
        while True:
            rc = process.poll()
            if rc is not None:
                return int(rc)
            now = time.perf_counter()
            if timeout_seconds is not None and now - started_at >= float(timeout_seconds):
                print(
                    f"- timeout: {heartbeat_label or 'command'} exceeded "
                    f"{int(float(timeout_seconds))}s; terminating"
                )
                _terminate_process(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _kill_process(process)
                    process.wait(timeout=5)
                return 124
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL_SECONDS:
                print(f"- heartbeat: {heartbeat_label} still running ({int(now - started_at)}s)")
                last_heartbeat = now
            time.sleep(0.5)
    completed = subprocess.run(
        tokens,
        cwd=str(repo_root),
        env=env,
        check=False,
    )
    return int(completed.returncode)


def _terminate_process(process: subprocess.Popen[Any]) -> None:
    process_pid = int(getattr(process, "pid", 0) or 0)
    if os.name == "posix" and process_pid > 0:
        try:
            os.killpg(process_pid, signal.SIGTERM)
            return
        except (OSError, ProcessLookupError):
            pass
    process.terminate()


def _kill_process(process: subprocess.Popen[Any]) -> None:
    process_pid = int(getattr(process, "pid", 0) or 0)
    if os.name == "posix" and process_pid > 0:
        try:
            os.killpg(process_pid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    process.kill()


def _display_sync_step_command(*, repo_root: Path, command: Sequence[str]) -> str:
    tokens = [str(token) for token in command]
    if len(tokens) >= 3 and tokens[0] == "python" and tokens[1] == "-m":
        module = tokens[2]
        forwarded = ensure_repo_root_args(repo_root=repo_root, argv=tokens[3:])
        if module.startswith("odylith.runtime.governance.") or module.startswith("odylith.runtime.surfaces."):
            return display_command("sync", *forwarded)
    return " ".join(tokens)


def _run_command_in_process(
    *,
    repo_root: Path,
    args: Sequence[str],
    heartbeat_label: str = "",
    timeout_seconds: float | None = None,
) -> int:
    tokens = tuple(str(token) for token in args)
    if len(tokens) >= 3 and tokens[0] == "python" and tokens[1] == "-m":
        module = importlib.import_module(tokens[2])
        main = getattr(module, "main", None)
        if callable(main):
            return int(main(list(tokens[3:])))
    return _run_command(
        repo_root=repo_root,
        args=tokens,
        heartbeat_label=heartbeat_label,
        timeout_seconds=timeout_seconds,
    )


def _use_runtime_fast_path(runtime_mode: str) -> bool:
    return str(runtime_mode).strip().lower() != "standalone"


def _runtime_args(runtime_mode: str) -> tuple[str, ...]:
    normalized = str(runtime_mode).strip().lower()
    if normalized == "auto":
        return ()
    return ("--runtime-mode", normalized)


def _replace_runtime_mode_args(command: Sequence[str], *, runtime_mode: str) -> tuple[str, ...]:
    normalized_mode = str(runtime_mode).strip().lower()
    tokens = [str(token).strip() for token in command if str(token).strip()]
    result: list[str] = []
    skip_next = False
    for index, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if token == "--runtime-mode":
            skip_next = index + 1 < len(tokens)
            continue
        result.append(token)
    if normalized_mode != "auto":
        result.extend(["--runtime-mode", normalized_mode])
    return tuple(result)


def _runtime_fast_path_prerequisites_met(repo_root: Path) -> bool:
    product_root = surface_root_path(repo_root=repo_root, key="product_root")
    required_paths = (
        truth_root_path(repo_root=repo_root, key="radar_source") / "INDEX.md",
        truth_root_path(repo_root=repo_root, key="technical_plans") / "INDEX.md",
        truth_root_path(repo_root=repo_root, key="component_registry"),
        product_root / "atlas" / "source" / "catalog" / "diagrams.v1.json",
    )
    return all(path.is_file() for path in required_paths)


def _dashboard_impact_from_governance_packet(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    runtime_mode: str,
) -> tuple[governance.DashboardImpact | None, str]:
    try:
        packet = _context_engine_store().build_governance_slice(
            repo_root=repo_root,
            changed_paths=changed_paths,
            runtime_mode=runtime_mode,
            delivery_profile="full",
            family_hint="governed_surface_sync",
        )
    except Exception as exc:
        return None, f"runtime_error:{type(exc).__name__}"
    if not isinstance(packet, Mapping):
        return None, "invalid_packet"
    if bool(packet.get("full_scan_recommended")):
        return None, str(packet.get("full_scan_reason", "")).strip() or "full_scan_recommended"
    diagram_watch_gaps = packet.get("diagram_watch_gaps", [])
    if isinstance(diagram_watch_gaps, list) and diagram_watch_gaps:
        return None, "diagram_watch_gaps"
    surface_refs = dict(packet.get("surface_refs", {})) if isinstance(packet.get("surface_refs"), Mapping) else {}
    impacted_surfaces = (
        dict(surface_refs.get("impacted_surfaces", {}))
        if isinstance(surface_refs.get("impacted_surfaces"), Mapping)
        else {
            str(token).strip(): True
            for token in surface_refs.get("surfaces", [])
            if isinstance(surface_refs.get("surfaces"), list) and str(token).strip()
        }
        or {
            str(token).strip(): True
            for row in surface_refs.get("reason_groups", [])
            if isinstance(surface_refs.get("reason_groups"), list) and isinstance(row, Mapping)
            for token in row.get("surfaces", [])
            if isinstance(row.get("surfaces"), list) and str(token).strip()
        }
    )
    reasons = (
        {
            str(key): [str(token).strip() for token in value if str(token).strip()]
            for key, value in dict(surface_refs.get("reasons", {})).items()
            if isinstance(value, list)
        }
        if isinstance(surface_refs.get("reasons"), Mapping)
        else {
            str(surface).strip(): [str(row.get("reason", "")).strip()]
            for row in surface_refs.get("reason_groups", [])
            if isinstance(surface_refs.get("reason_groups"), list)
            and isinstance(row, Mapping)
            and str(row.get("reason", "")).strip()
            for surface in row.get("surfaces", [])
            if isinstance(row.get("surfaces"), list) and str(surface).strip()
        }
    )
    return (
        governance.DashboardImpact(
            radar=bool(impacted_surfaces.get("radar")),
            atlas=bool(impacted_surfaces.get("atlas")),
            compass=bool(impacted_surfaces.get("compass")),
            registry=bool(impacted_surfaces.get("registry")),
            casebook=bool(impacted_surfaces.get("casebook")),
            reasons=reasons,
        ),
        "",
    )


def _selected_atlas_diagram_ids(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    force: bool,
    impact_mode: str,
    runtime_mode: str,
) -> list[str]:
    if force or str(impact_mode).strip().lower() != "selective":
        return []
    if not changed_paths or not _use_runtime_fast_path(runtime_mode):
        return []
    if not _runtime_fast_path_prerequisites_met(repo_root):
        return []
    try:
        rows = _context_engine_store().select_impacted_diagrams(
            repo_root=repo_root,
            changed_paths=changed_paths,
            runtime_mode=runtime_mode,
        )
    except Exception:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for row in rows:
        diagram_id = str(row.get("diagram_id", "")).strip().upper()
        if diagram_id and diagram_id not in seen:
            seen.add(diagram_id)
            result.append(diagram_id)
    return result


def _atlas_render_command(
    *,
    repo_root: Path,
    check_only: bool,
    changed_paths: Sequence[str],
    force: bool,
    impact_mode: str,
    runtime_mode: str,
) -> tuple[str, ...]:
    command: list[str] = [
        "python",
        "-m",
        "odylith.runtime.surfaces.render_mermaid_catalog",
        "--repo-root",
        str(repo_root),
        "--fail-on-stale",
    ]
    if check_only:
        command.append("--check-only")
    command.extend(_runtime_args(runtime_mode))
    for diagram_id in _selected_atlas_diagram_ids(
        repo_root=repo_root,
        changed_paths=changed_paths,
        force=force,
        impact_mode=impact_mode,
        runtime_mode=runtime_mode,
    ):
        command.extend(["--diagram-id", diagram_id])
    return tuple(command)


def _atlas_auto_update_command(
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    force: bool,
    impact_mode: str,
    runtime_mode: str,
) -> tuple[str, ...]:
    command: list[str] = [
        "python",
        "-m",
        "odylith.runtime.surfaces.auto_update_mermaid_diagrams",
        "--repo-root",
        str(repo_root),
        "--skip-render-catalog",
    ]
    command.extend(_runtime_args(runtime_mode))
    for token in changed_paths:
        command.extend(["--changed-path", str(token)])
    if force or str(impact_mode).strip().lower() != "selective":
        command.append("--all-stale")
    return tuple(command)


def _delivery_intelligence_command(*, repo_root: Path, check_only: bool) -> tuple[str, ...]:
    command: list[str] = [
        "python",
        "-m",
        "odylith.runtime.governance.delivery_intelligence_engine",
        "--repo-root",
        str(repo_root),
    ]
    if check_only:
        command.append("--check-only")
    return tuple(command)


def _surface_render_outputs(surface: str) -> tuple[str, ...]:
    return {
        "tooling_shell": ("odylith/index.html", "odylith/tooling-payload.v1.js", "odylith/tooling-app.v1.js"),
        "radar": (
            "odylith/radar/radar.html",
            "odylith/radar/backlog-payload.v1.js",
            "odylith/radar/backlog-app.v1.js",
            "odylith/radar/traceability-graph.v1.json",
        ),
        "compass": (
            "odylith/compass/compass.html",
            "odylith/compass/compass-payload.v1.js",
            "odylith/compass/compass-app.v1.js",
            "odylith/compass/compass-style-base.v1.css",
            "odylith/compass/compass-style-execution-waves.v1.css",
            "odylith/compass/compass-style-surface.v1.css",
            "odylith/compass/compass-shared.v1.js",
            "odylith/compass/compass-state.v1.js",
            "odylith/compass/compass-summary.v1.js",
            "odylith/compass/compass-timeline.v1.js",
            "odylith/compass/compass-waves.v1.js",
            "odylith/compass/compass-workstreams.v1.js",
            "odylith/compass/compass-ui-runtime.v1.js",
        ),
        "atlas": ("odylith/atlas/atlas.html", "odylith/atlas/mermaid-payload.v1.js", "odylith/atlas/mermaid-app.v1.js"),
        "registry": ("odylith/registry/registry.html", "odylith/registry/registry-payload.v1.js", "odylith/registry/registry-app.v1.js"),
        "casebook": ("odylith/casebook/casebook.html", "odylith/casebook/casebook-payload.v1.js", "odylith/casebook/casebook-app.v1.js"),
    }.get(surface, ())


def _runtime_retry_command(command: Sequence[str]) -> tuple[str, ...]:
    return _replace_runtime_mode_args(command, runtime_mode="standalone")


def _dashboard_surface_steps(
    *,
    repo_root: Path,
    surface: str,
    runtime_mode: str,
    atlas_sync: bool,
    compass_refresh_profile: str,
) -> list[ExecutionStep]:
    normalized_runtime_mode = str(runtime_mode).strip().lower() or "auto"
    refresh_command = display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", surface)
    steps: list[ExecutionStep] = []
    if surface in {"atlas", "registry", "tooling_shell"}:
        command = _delivery_intelligence_command(repo_root=repo_root, check_only=False)
        steps.append(
            _execution_step(
                "Refresh delivery intelligence inputs for this shell-facing surface.",
                surface=surface,
                command=command,
                mutation_classes=("generated_surfaces",),
                paths=("odylith/runtime/delivery_intelligence.v4.json",),
                next_command_on_failure=refresh_command,
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
    if surface == "atlas" and atlas_sync:
        command = _atlas_auto_update_command(
            repo_root=repo_root,
            changed_paths=(),
            force=True,
            impact_mode="full",
            runtime_mode=normalized_runtime_mode,
        )
        steps.append(
            _execution_step(
                "Refresh stale Atlas Mermaid diagrams before rerendering the Atlas surface.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("repo_owned_truth", "generated_surfaces"),
                paths=(
                    "odylith/atlas/source/catalog/diagrams.v1.json",
                    "odylith/atlas/source/*.svg",
                    "odylith/atlas/source/*.png",
                ),
                next_command_on_failure=display_command("atlas", "auto-update", "--repo-root", ".", "--all-stale"),
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
    if surface == "compass":
        command = (
            "python",
            "-m",
            "odylith.runtime.surfaces.render_compass_dashboard",
            "--repo-root",
            str(repo_root),
            "--refresh-profile",
            str(compass_refresh_profile).strip().lower() or _DEFAULT_COMPASS_REFRESH_PROFILE,
            *_runtime_args(normalized_runtime_mode),
        )
        steps.append(
            _execution_step(
                "Render Compass in the selected refresh profile.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("compass"),
                next_command_on_failure=display_command("compass", "update", "--repo-root", "."),
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
        return steps
    if surface == "radar":
        command = (
            "python",
            "-m",
            "odylith.runtime.surfaces.render_backlog_ui",
            "--repo-root",
            str(repo_root),
            *_runtime_args(normalized_runtime_mode),
        )
        steps.append(
            _execution_step(
                "Render Radar without widening into the full governance sync pipeline.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("radar"),
                next_command_on_failure=refresh_command,
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
        return steps
    if surface == "atlas":
        command = _atlas_render_command(
            repo_root=repo_root,
            check_only=False,
            changed_paths=(),
            force=True,
            impact_mode="full",
            runtime_mode=normalized_runtime_mode,
        )
        steps.append(
            _execution_step(
                "Render Atlas from the current Mermaid catalog state.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("atlas"),
                next_command_on_failure=refresh_command,
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
        return steps
    if surface == "registry":
        command = (
            "python",
            "-m",
            "odylith.runtime.surfaces.render_registry_dashboard",
            "--repo-root",
            str(repo_root),
            *_runtime_args(normalized_runtime_mode),
        )
        steps.append(
            _execution_step(
                "Render Registry without re-running broader governance reconciliation.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("registry"),
                next_command_on_failure=refresh_command,
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
        return steps
    if surface == "casebook":
        steps.append(
            _execution_step(
                "Refresh the Casebook bug index before rerendering the Casebook dashboard.",
                surface=surface,
                mutation_classes=("repo_owned_truth",),
                paths=("odylith/casebook/bugs/INDEX.md",),
                action=lambda: (
                    sync_casebook_bug_index.sync_casebook_bug_index(
                        repo_root=repo_root,
                        migrate_bug_ids=True,
                    ),
                    0,
                )[1],
                next_command_on_failure=refresh_command,
            )
        )
        command = (
            "python",
            "-m",
            "odylith.runtime.surfaces.render_casebook_dashboard",
            "--repo-root",
            str(repo_root),
            *_runtime_args(normalized_runtime_mode),
        )
        steps.append(
            _execution_step(
                "Render Casebook for the updated bug index.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("casebook"),
                next_command_on_failure=refresh_command,
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
        return steps
    if surface == "tooling_shell":
        command = (
            "python",
            "-m",
            "odylith.runtime.surfaces.render_tooling_dashboard",
            "--repo-root",
            str(repo_root),
            *_runtime_args(normalized_runtime_mode),
        )
        steps.append(
            _execution_step(
                "Render the top-level Odylith shell frame and payload bundle.",
                surface=surface,
                command=command,
                standalone_command=_runtime_retry_command(command),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("tooling_shell"),
                next_command_on_failure=display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", "shell"),
                timeout_seconds=_DASHBOARD_REFRESH_TIMEOUT_SECONDS,
            )
        )
    return steps


def _build_dashboard_refresh_steps(
    *,
    repo_root: Path,
    selected: Sequence[str],
    runtime_mode: str,
    atlas_sync: bool,
    compass_refresh_profile: str,
) -> list[ExecutionStep]:
    steps: list[ExecutionStep] = []
    for surface in selected:
        steps.extend(
            _dashboard_surface_steps(
                repo_root=repo_root,
                surface=surface,
                runtime_mode=runtime_mode,
                atlas_sync=atlas_sync,
                compass_refresh_profile=compass_refresh_profile,
            )
        )
    return steps


def build_dashboard_refresh_plan(
    *,
    repo_root: Path,
    surfaces: Sequence[str],
    runtime_mode: str,
    atlas_sync: bool = False,
    compass_refresh_profile: str = _DEFAULT_COMPASS_REFRESH_PROFILE,
) -> ExecutionPlan:
    selected = normalize_dashboard_surfaces(surfaces)
    normalized_runtime_mode = str(runtime_mode).strip().lower() or "auto"
    notes = _dashboard_refresh_notes(
        repo_root=repo_root,
        selected=selected,
        atlas_sync=bool(atlas_sync),
    )
    return _execution_plan(
        headline=(
            f"Refresh {', '.join(selected)} with runtime mode `{normalized_runtime_mode}`."
        ),
        steps=_build_dashboard_refresh_steps(
            repo_root=repo_root,
            selected=selected,
            runtime_mode=normalized_runtime_mode,
            atlas_sync=atlas_sync,
            compass_refresh_profile=compass_refresh_profile,
        ),
        notes=notes,
        repo_root=repo_root,
    )


def _surface_display_name(surface: str) -> str:
    return str(_SURFACE_DISPLAY_NAMES.get(str(surface).strip(), str(surface).strip())).strip()


def _atlas_stale_diagram_count(*, repo_root: Path) -> int:
    try:
        from odylith.runtime.surfaces import auto_update_mermaid_diagrams as atlas_auto_update

        catalog_path = atlas_auto_update._resolve(  # noqa: SLF001
            repo_root,
            "odylith/atlas/source/catalog/diagrams.v1.json",
        )
        if not catalog_path.is_file():
            return 0
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        diagrams = payload.get("diagrams")
        if not isinstance(diagrams, list):
            return 0
        return len(
            atlas_auto_update._select_stale_diagram_indexes(  # noqa: SLF001
                repo_root=repo_root,
                diagrams=diagrams,
                max_review_age_days=21,
            )
        )
    except Exception:
        return 0


def _dashboard_refresh_notes(
    *,
    repo_root: Path,
    selected: Sequence[str],
    atlas_sync: bool,
) -> list[str]:
    selected_tokens = [str(token).strip() for token in selected if str(token).strip()]
    excluded = [surface for surface in _VALID_DASHBOARD_SURFACES if surface not in selected_tokens]
    notes = [
        "Dashboard refresh stays surface-scoped and does not run the full governance sync pipeline.",
        "Included surfaces: " + ", ".join(_surface_display_name(surface) for surface in selected_tokens) + ".",
    ]
    if excluded:
        notes.append(
            "Excluded surfaces: " + ", ".join(_surface_display_name(surface) for surface in excluded) + "."
        )
    if atlas_sync and "atlas" in selected_tokens:
        notes.append(
            "`--atlas-sync` mutates repo-owned Atlas truth by touching selected `.mmd` review markers and rewriting "
            "`odylith/atlas/source/catalog/diagrams.v1.json` before Atlas assets are rerendered."
        )
    elif atlas_sync:
        notes.append("`--atlas-sync` was provided, but Atlas is excluded from this run so no Atlas source sync will run.")
    else:
        notes.append("Atlas Mermaid source refresh stays opt-in behind `--atlas-sync`.")
    if "atlas" not in selected_tokens:
        atlas_stale_count = _atlas_stale_diagram_count(repo_root=repo_root)
        if atlas_stale_count > 0:
            notes.append(
                f"Atlas is excluded from this run and {atlas_stale_count} diagram(s) are currently stale. Next: "
                + display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", "atlas", "--atlas-sync")
            )
        else:
            notes.append(
                "Atlas is excluded from this run. Next: "
                + display_command("dashboard", "refresh", "--repo-root", ".", "--surfaces", "atlas", "--atlas-sync")
            )
    elif not atlas_sync:
        notes.append(
            "Atlas is selected without `--atlas-sync`, so this run rerenders the Atlas dashboard from current catalog truth only."
        )
    return notes


def normalize_dashboard_surfaces(values: Sequence[str]) -> list[str]:
    tokens: list[str] = []
    for raw in values:
        for token in str(raw or "").split(","):
            normalized = _SURFACE_ALIASES.get(str(token).strip().lower(), str(token).strip().lower())
            if normalized:
                tokens.append(normalized)
    if not tokens:
        raise ValueError(
            "dashboard refresh requires at least one surface; choose from "
            + ", ".join(_VALID_DASHBOARD_SURFACES)
        )
    result: list[str] = []
    seen: set[str] = set()
    invalid = [token for token in tokens if token not in _VALID_DASHBOARD_SURFACES]
    if invalid:
        raise ValueError(
            "unknown dashboard surface(s): "
            + ", ".join(sorted(dict.fromkeys(invalid)))
            + ". Choose from "
            + ", ".join(_VALID_DASHBOARD_SURFACES)
        )
    for token in tokens:
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result


def _run_dashboard_refresh_step(
    *,
    repo_root: Path,
    step: ExecutionStep,
    runtime_mode: str,
) -> tuple[int, bool]:
    if step.action is not None:
        return int(step.action()), False
    if not step.command:
        return 0, False
    heartbeat_label = _display_sync_step_command(repo_root=repo_root, command=step.command)
    command_kwargs: dict[str, Any] = {
        "repo_root": repo_root,
        "args": step.command,
        "heartbeat_label": heartbeat_label,
    }
    if step.timeout_seconds is not None:
        command_kwargs["timeout_seconds"] = step.timeout_seconds
    rc = _run_command(**command_kwargs)
    if rc == 0 or str(runtime_mode).strip().lower() != "auto" or not step.standalone_command:
        return rc, False
    print(f"- runtime_fallback: {step.surface or 'surface'} -> standalone")
    fallback_label = _display_sync_step_command(repo_root=repo_root, command=step.standalone_command)
    fallback_kwargs: dict[str, Any] = {
        "repo_root": repo_root,
        "args": step.standalone_command,
        "heartbeat_label": fallback_label,
    }
    if step.timeout_seconds is not None:
        fallback_kwargs["timeout_seconds"] = step.timeout_seconds
    fallback_rc = _run_command(**fallback_kwargs)
    return fallback_rc, True


def _execute_dashboard_refresh_surface(
    *,
    repo_root: Path,
    surface: str,
    steps: Sequence[ExecutionStep],
    runtime_mode: str,
) -> dict[str, Any]:
    fallback_used = False
    for index, step in enumerate(steps, start=1):
        print(f"- {surface} step {index}/{len(steps)}: {step.label}")
        rc, step_fallback = _run_dashboard_refresh_step(
            repo_root=repo_root,
            step=step,
            runtime_mode=runtime_mode,
        )
        fallback_used = fallback_used or step_fallback
        if rc != 0:
            next_command = step.next_command_on_failure
            if not next_command and step.command:
                next_command = _display_sync_step_command(repo_root=repo_root, command=step.command)
            return {
                "surface": surface,
                "status": "failed",
                "fallback_used": fallback_used,
                "rc": int(rc),
                "next_command": next_command,
                "failed_step": step.label,
            }
    return {
        "surface": surface,
        "status": "passed",
        "fallback_used": fallback_used,
        "rc": 0,
        "next_command": "",
        "failed_step": "",
    }


def refresh_dashboard_surfaces(
    *,
    repo_root: Path,
    surfaces: Sequence[str],
    runtime_mode: str,
    atlas_sync: bool = False,
    dry_run: bool = False,
    compass_refresh_profile: str = _DEFAULT_COMPASS_REFRESH_PROFILE,
) -> int:
    selected = normalize_dashboard_surfaces(surfaces)
    normalized_runtime_mode = str(runtime_mode).strip().lower() or "auto"
    plan = build_dashboard_refresh_plan(
        repo_root=repo_root,
        surfaces=selected,
        runtime_mode=normalized_runtime_mode,
        atlas_sync=atlas_sync,
        compass_refresh_profile=compass_refresh_profile,
    )
    _print_execution_plan("dashboard refresh", plan, dry_run=bool(dry_run))
    if dry_run:
        return 0
    started_at = time.perf_counter()
    surface_results: list[dict[str, Any]] = []
    runtime_fallback_used = False
    for surface in selected:
        steps = _dashboard_surface_steps(
            repo_root=repo_root,
            surface=surface,
            runtime_mode=normalized_runtime_mode,
            atlas_sync=atlas_sync,
            compass_refresh_profile=compass_refresh_profile,
        )
        result = _execute_dashboard_refresh_surface(
            repo_root=repo_root,
            surface=surface,
            steps=steps,
            runtime_mode=normalized_runtime_mode,
        )
        runtime_fallback_used = runtime_fallback_used or bool(result.get("fallback_used"))
        surface_results.append(result)
    elapsed = time.perf_counter() - started_at
    failures = [result for result in surface_results if result.get("status") != "passed"]
    print("dashboard refresh completed")
    print("- outcome: failed" if failures else "- outcome: passed")
    print(f"- elapsed_seconds: {elapsed:.1f}")
    print(f"- runtime_fallback_used: {'yes' if runtime_fallback_used else 'no'}")
    for result in surface_results:
        surface = str(result.get("surface", "")).strip()
        status = str(result.get("status", "")).strip() or "failed"
        suffix = " (standalone fallback used)" if bool(result.get("fallback_used")) else ""
        print(f"- {surface}: {status}{suffix}")
        if status != "passed":
            failed_step = str(result.get("failed_step", "")).strip()
            next_command = str(result.get("next_command", "")).strip()
            if failed_step:
                print(f"  failed_step: {failed_step}")
            if next_command:
                print(f"  next: {next_command}")
    if failures:
        return 2
    return 0


def generated_output_targets() -> tuple[str, ...]:
    return (
        "odylith/radar/radar.html",
        "odylith/radar/backlog-payload.v1.js",
        "odylith/radar/backlog-app.v1.js",
        "odylith/radar/backlog-detail-shard-*.v1.js",
        "odylith/radar/backlog-document-shard-*.v1.js",
        "odylith/radar/standalone-pages.v1.js",
        "odylith/radar/traceability-graph.v1.json",
        "odylith/radar/traceability-autofix-report.v1.json",
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/compass/compass.html",
        "odylith/compass/compass-payload.v1.js",
        "odylith/compass/compass-app.v1.js",
        "odylith/compass/compass-style-base.v1.css",
        "odylith/compass/compass-style-execution-waves.v1.css",
        "odylith/compass/compass-style-surface.v1.css",
        "odylith/compass/compass-shared.v1.js",
        "odylith/compass/compass-state.v1.js",
        "odylith/compass/compass-summary.v1.js",
        "odylith/compass/compass-timeline.v1.js",
        "odylith/compass/compass-waves.v1.js",
        "odylith/compass/compass-workstreams.v1.js",
        "odylith/compass/compass-ui-runtime.v1.js",
        "odylith/registry/registry.html",
        "odylith/registry/registry-payload.v1.js",
        "odylith/registry/registry-app.v1.js",
        "odylith/casebook/casebook.html",
        "odylith/casebook/casebook-payload.v1.js",
        "odylith/casebook/casebook-app.v1.js",
        "odylith/casebook/casebook-detail-shard-*.v1.js",
        "odylith/index.html",
        "odylith/tooling-payload.v1.js",
        "odylith/tooling-app.v1.js",
        "odylith/runtime/delivery_intelligence.v4.json",
        "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/atlas/source/*.svg",
        "odylith/atlas/source/*.png",
        "odylith/registry/registry-detail-shard-*.v1.js",
    )


def _git_status_generated_outputs(*, repo_root: Path) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *generated_output_targets(),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    raw = str(completed.stdout or "")
    return [line for line in raw.splitlines() if line]


def _git_dirty_generated_outputs(*, repo_root: Path) -> str:
    return "\n".join(_git_status_generated_outputs(repo_root=repo_root)).rstrip()


def _commit_ready_dirty_status_line(line: str) -> bool:
    status = line[:2]
    if status == "??":
        return True
    if len(status) < 2:
        return True
    return status[1] != " "


def _git_commit_ready_generated_outputs(*, repo_root: Path) -> str:
    lines = [
        line
        for line in _git_status_generated_outputs(repo_root=repo_root)
        if _commit_ready_dirty_status_line(line)
    ]
    return "\n".join(lines).rstrip()


def build_sync_execution_plan(
    *,
    repo_root: Path,
    args: argparse.Namespace,
    changed_paths: Sequence[str],
    impact: governance.DashboardImpact,
    impact_tooling_shell: bool,
    runtime_mode: str,
) -> ExecutionPlan:
    sync_failure_command = display_command(
        "sync",
        "--repo-root",
        ".",
        *("--check-only",) if bool(args.check_only) else ("--force", "--impact-mode", str(args.impact_mode)),
    )
    steps: list[ExecutionStep] = []
    if args.check_only:
        steps.extend(
            [
                _execution_step(
                    "Check Registry component spec requirements without rewriting governed truth.",
                    command=(
                        "python",
                        "-m",
                        "odylith.runtime.governance.sync_component_spec_requirements",
                        "--repo-root",
                        str(repo_root),
                        "--check-only",
                        *_runtime_args(runtime_mode),
                    ),
                    paths=("odylith/registry/source/components/",),
                    next_command_on_failure=sync_failure_command,
                ),
                _execution_step(
                    "Validate Registry contract and deep-skill policy bindings.",
                    command=(
                        "python",
                        "-m",
                        "odylith.runtime.governance.validate_component_registry_contract",
                        "--repo-root",
                        str(repo_root),
                        "--policy-mode",
                        str(args.registry_policy_mode),
                        *(("--enforce-deep-skills",) if args.enforce_deep_skills else ()),
                    ),
                    paths=("odylith/registry/source/component_registry.v1.json", "odylith/registry/source/components/"),
                    next_command_on_failure=sync_failure_command,
                ),
                _execution_step(
                    "Validate active-plan to workstream bindings for the current slice.",
                    command=(
                        "python",
                        "-m",
                        "odylith.runtime.governance.validate_plan_workstream_binding",
                        "--repo-root",
                        str(repo_root),
                        *changed_paths,
                    ),
                    paths=("odylith/technical-plans/in-progress/", "odylith/radar/source/"),
                    next_command_on_failure=sync_failure_command,
                ),
                _execution_step(
                    "Validate Radar backlog, traceability, and plan risk/mitigation contracts.",
                    command=("python", "-m", "odylith.runtime.governance.validate_backlog_contract", "--repo-root", str(repo_root)),
                    paths=("odylith/radar/source/",),
                    next_command_on_failure=sync_failure_command,
                ),
                _execution_step(
                    "Validate active-plan traceability and risk/mitigation closeout contracts.",
                    command=("python", "-m", "odylith.runtime.governance.validate_plan_traceability_contract", "--repo-root", str(repo_root)),
                    paths=("odylith/technical-plans/in-progress/",),
                    next_command_on_failure=sync_failure_command,
                ),
                _execution_step(
                    "Validate active-plan risk/mitigation structure.",
                    command=("python", "-m", "odylith.runtime.governance.validate_plan_risk_mitigation_contract", "--repo-root", str(repo_root)),
                    paths=("odylith/technical-plans/in-progress/",),
                    next_command_on_failure=sync_failure_command,
                ),
            ]
        )
        if bool(getattr(impact, "atlas", False)):
            steps.append(
                _execution_step(
                    "Check Atlas freshness for the impacted diagrams without rewriting outputs.",
                    command=_atlas_render_command(
                        repo_root=repo_root,
                        check_only=True,
                        changed_paths=changed_paths,
                        force=bool(args.force),
                        impact_mode=str(args.impact_mode),
                        runtime_mode=runtime_mode,
                    ),
                    paths=("odylith/atlas/source/catalog/diagrams.v1.json", "odylith/atlas/atlas.html"),
                    next_command_on_failure=sync_failure_command,
                )
            )
        steps.append(
            _execution_step(
                "Check delivery-intelligence freshness without mutating shell outputs.",
                command=_delivery_intelligence_command(repo_root=repo_root, check_only=True),
                paths=("odylith/runtime/delivery_intelligence.v4.json",),
                next_command_on_failure=sync_failure_command,
            )
        )
        notes = [
            "Check-only sync is non-mutating and proves the governed surfaces against current tracked truth.",
        ]
        return _execution_plan(
            headline=f"Validate the current sync slice in `{runtime_mode}` mode without writing files.",
            steps=steps,
            notes=notes,
            repo_root=repo_root,
        )

    steps.append(
        _execution_step(
            "Normalize active-plan risk/mitigation sections before validation and render.",
            command=("python", "-m", "odylith.runtime.governance.normalize_plan_risk_mitigation", "--repo-root", str(repo_root)),
            mutation_classes=("repo_owned_truth",),
            paths=("odylith/technical-plans/in-progress/",),
            next_command_on_failure=sync_failure_command,
        )
    )
    if not args.no_traceability_autofix:
        steps.append(
            _execution_step(
                "Backfill Radar traceability metadata and write the autofix report.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.governance.backfill_workstream_traceability",
                    "--repo-root",
                    str(repo_root),
                    "--report",
                    str(args.traceability_autofix_report),
                ),
                mutation_classes=("repo_owned_truth",),
                paths=("odylith/radar/source/ideas/", str(args.traceability_autofix_report)),
                next_command_on_failure=sync_failure_command,
            )
        )
    steps.extend(
        [
            _execution_step(
                "Reconcile the active plan to its Radar workstream bindings.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.governance.reconcile_plan_workstream_binding",
                    "--repo-root",
                    str(repo_root),
                    *changed_paths,
                ),
                mutation_classes=("repo_owned_truth",),
                paths=("odylith/technical-plans/in-progress/", "odylith/radar/source/"),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Validate plan/workstream bindings, backlog contract, and Registry contract.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.governance.validate_plan_workstream_binding",
                    "--repo-root",
                    str(repo_root),
                    *changed_paths,
                ),
                paths=("odylith/technical-plans/in-progress/", "odylith/radar/source/"),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Validate Radar backlog contract.",
                command=("python", "-m", "odylith.runtime.governance.validate_backlog_contract", "--repo-root", str(repo_root)),
                paths=("odylith/radar/source/",),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Validate Registry contract and deep-skill policy bindings.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.governance.validate_component_registry_contract",
                    "--repo-root",
                    str(repo_root),
                    "--policy-mode",
                    str(args.registry_policy_mode),
                    *(("--enforce-deep-skills",) if args.enforce_deep_skills else ()),
                ),
                paths=("odylith/registry/source/component_registry.v1.json", "odylith/registry/source/components/"),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Auto-promote workstream phase transitions and validate traceability/risk contracts.",
                command=("python", "-m", "odylith.runtime.governance.auto_promote_workstream_phase", "--repo-root", str(repo_root)),
                mutation_classes=("repo_owned_truth",),
                paths=("odylith/radar/source/ideas/",),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Validate plan traceability.",
                command=("python", "-m", "odylith.runtime.governance.validate_plan_traceability_contract", "--repo-root", str(repo_root)),
                paths=("odylith/technical-plans/in-progress/",),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Validate plan risk/mitigation structure.",
                command=("python", "-m", "odylith.runtime.governance.validate_plan_risk_mitigation_contract", "--repo-root", str(repo_root)),
                paths=("odylith/technical-plans/in-progress/",),
                next_command_on_failure=sync_failure_command,
            ),
            _execution_step(
                "Regenerate the Radar traceability graph used by the shell surfaces.",
                command=("python", "-m", "odylith.runtime.governance.build_traceability_graph", "--repo-root", str(repo_root)),
                mutation_classes=("generated_surfaces",),
                paths=("odylith/radar/traceability-graph.v1.json",),
                next_command_on_failure=sync_failure_command,
            ),
        ]
    )
    if bool(getattr(impact, "casebook", False)):
        steps.append(
            _execution_step(
                "Refresh the Casebook bug index before any shell-facing renders consume it.",
                mutation_classes=("repo_owned_truth",),
                paths=("odylith/casebook/bugs/INDEX.md",),
                action=lambda: (
                    sync_casebook_bug_index.sync_casebook_bug_index(
                        repo_root=repo_root,
                        migrate_bug_ids=True,
                    ),
                    0,
                )[1],
                next_command_on_failure=sync_failure_command,
            )
        )
    if bool(getattr(impact, "compass", False)):
        steps.append(
            _execution_step(
                "Render Compass before Radar so execution overlays see the latest runtime snapshot.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.surfaces.render_compass_dashboard",
                    "--repo-root",
                    str(repo_root),
                    "--refresh-profile",
                    str(getattr(args, "compass_refresh_profile", _DEFAULT_COMPASS_REFRESH_PROFILE)).strip().lower()
                    or _DEFAULT_COMPASS_REFRESH_PROFILE,
                    *_runtime_args(runtime_mode),
                ),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("compass"),
                next_command_on_failure=sync_failure_command,
            )
        )
    if bool(getattr(impact, "radar", False)):
        steps.append(
            _execution_step(
                "Render Radar for the impacted backlog slice.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.surfaces.render_backlog_ui",
                    "--repo-root",
                    str(repo_root),
                    *_runtime_args(runtime_mode),
                ),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("radar"),
                next_command_on_failure=sync_failure_command,
            )
        )
    if bool(getattr(impact, "atlas", False)):
        steps.extend(
            [
                _execution_step(
                    "Auto-refresh Atlas Mermaid diagrams selected by the impact planner.",
                    command=_atlas_auto_update_command(
                        repo_root=repo_root,
                        changed_paths=changed_paths,
                        force=bool(args.force),
                        impact_mode=str(args.impact_mode),
                        runtime_mode=runtime_mode,
                    ),
                    mutation_classes=("repo_owned_truth", "generated_surfaces"),
                    paths=("odylith/atlas/source/catalog/diagrams.v1.json", "odylith/atlas/source/*.svg", "odylith/atlas/source/*.png"),
                    next_command_on_failure=display_command("atlas", "auto-update", "--repo-root", ".", "--from-git-working-tree"),
                ),
                _execution_step(
                    "Render Atlas after Mermaid freshness settles.",
                    command=_atlas_render_command(
                        repo_root=repo_root,
                        check_only=False,
                        changed_paths=changed_paths,
                        force=bool(args.force),
                        impact_mode=str(args.impact_mode),
                        runtime_mode=runtime_mode,
                    ),
                    mutation_classes=("generated_surfaces",),
                    paths=_surface_render_outputs("atlas"),
                    next_command_on_failure=display_command("atlas", "render", "--repo-root", ".", "--fail-on-stale"),
                ),
            ]
        )
    steps.append(
        _execution_step(
            "Sync Registry component spec requirements after Atlas mutations settle.",
            command=(
                "python",
                "-m",
                "odylith.runtime.governance.sync_component_spec_requirements",
                "--repo-root",
                str(repo_root),
                *_runtime_args(runtime_mode),
            ),
            mutation_classes=("repo_owned_truth",),
            paths=("odylith/registry/source/components/",),
            next_command_on_failure=sync_failure_command,
        )
    )
    steps.append(
        _execution_step(
            "Refresh delivery intelligence after Atlas and Registry inputs settle.",
            command=_delivery_intelligence_command(repo_root=repo_root, check_only=False),
            mutation_classes=("generated_surfaces",),
            paths=("odylith/runtime/delivery_intelligence.v4.json",),
            next_command_on_failure=sync_failure_command,
        )
    )
    if bool(getattr(impact, "registry", False)):
        steps.append(
            _execution_step(
                "Render Registry for the impacted component view.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.surfaces.render_registry_dashboard",
                    "--repo-root",
                    str(repo_root),
                    *_runtime_args(runtime_mode),
                ),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("registry"),
                next_command_on_failure=sync_failure_command,
            )
        )
    if bool(getattr(impact, "casebook", False)):
        steps.append(
            _execution_step(
                "Render Casebook for the refreshed bug index.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.surfaces.render_casebook_dashboard",
                    "--repo-root",
                    str(repo_root),
                    *_runtime_args(runtime_mode),
                ),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("casebook"),
                next_command_on_failure=sync_failure_command,
            )
        )
    if bool(impact_tooling_shell):
        steps.append(
            _execution_step(
                "Render the top-level Odylith shell after the selected surfaces settle.",
                command=(
                    "python",
                    "-m",
                    "odylith.runtime.surfaces.render_tooling_dashboard",
                    "--repo-root",
                    str(repo_root),
                    *_runtime_args(runtime_mode),
                ),
                mutation_classes=("generated_surfaces",),
                paths=_surface_render_outputs("tooling_shell"),
                next_command_on_failure=sync_failure_command,
            )
        )
    notes = [
        "Dry-run previews the same step graph used for real sync execution so mutation scope cannot drift from runtime behavior.",
    ]
    return _execution_plan(
        headline=f"Sync the governed surfaces in `{runtime_mode}` mode for the current impact slice.",
        steps=steps,
        notes=notes,
        repo_root=repo_root,
    )


def _execute_plan(
    *,
    repo_root: Path,
    plan_name: str,
    plan: ExecutionPlan,
    run_impl: Callable[..., int],
    runtime_fallback_used: bool,
) -> int:
    started_at = time.perf_counter()
    for index, step in enumerate(plan.steps, start=1):
        print(f"- step {index}/{len(plan.steps)}: {step.label}")
        if step.action is not None:
            rc = int(step.action())
        elif step.command:
            heartbeat_label = _display_sync_step_command(repo_root=repo_root, command=step.command)
            command_kwargs: dict[str, Any] = {
                "repo_root": repo_root,
                "args": step.command,
                "heartbeat_label": heartbeat_label,
            }
            if step.timeout_seconds is not None:
                command_kwargs["timeout_seconds"] = step.timeout_seconds
            rc = run_impl(**command_kwargs)
        else:
            rc = 0
        if rc != 0:
            elapsed = time.perf_counter() - started_at
            print(f"{plan_name} failed")
            print("- outcome: failed")
            print(f"- elapsed_seconds: {elapsed:.1f}")
            print(f"- runtime_fallback_used: {'yes' if runtime_fallback_used else 'no'}")
            if step.next_command_on_failure:
                print(f"- next: {step.next_command_on_failure}")
            elif step.command:
                print(f"- next: {_display_sync_step_command(repo_root=repo_root, command=step.command)}")
            return rc
    elapsed = time.perf_counter() - started_at
    print(f"{plan_name} completed")
    print("- outcome: passed")
    print(f"- elapsed_seconds: {elapsed:.1f}")
    print(f"- runtime_fallback_used: {'yes' if runtime_fallback_used else 'no'}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    runtime_mode = str(args.runtime_mode).strip().lower()
    effective_runtime_mode = "standalone" if args.check_only else runtime_mode
    changed_paths = _effective_changed_paths(
        repo_root=repo_root,
        changed_paths=tuple(args.changed_paths),
        force=bool(args.force),
    )

    if not _requires_sync(
        repo_root=repo_root,
        changed_paths=changed_paths,
        force=bool(args.force),
    ):
        print("workstream sync skipped (no relevant artifact changes detected)")
        return 0

    impact = None
    governance_fallback_reason = ""
    if not args.check_only and _use_runtime_fast_path(effective_runtime_mode) and changed_paths:
        governance_started = time.perf_counter()
        impact, governance_fallback_reason = _dashboard_impact_from_governance_packet(
            repo_root=repo_root,
            changed_paths=changed_paths,
            runtime_mode=effective_runtime_mode,
        )
        _context_engine_store().record_runtime_timing(
            repo_root=repo_root,
            category="sync",
            operation="governance_runtime_first",
            duration_ms=(time.perf_counter() - governance_started) * 1000.0,
            metadata={
                "runtime_fast_path": True,
                "used_governance_packet": impact is not None,
                "fallback_applied": impact is None,
                "fallback_reason": governance_fallback_reason,
                "runtime_mode": effective_runtime_mode,
                "changed_path_count": len([str(token).strip() for token in changed_paths if str(token).strip()]),
            },
        )
        if impact is None:
            reason_suffix = f" ({governance_fallback_reason})" if governance_fallback_reason else ""
            print(f"- governance_packet_fallback: heuristic impact planner{reason_suffix}")
    if impact is None:
        impact = governance.build_dashboard_impact(
            repo_root=repo_root,
            changed_paths=changed_paths,
            force=bool(args.force),
            impact_mode=str(args.impact_mode),
        )
    impact_radar = bool(getattr(impact, "radar", False))
    impact_atlas = bool(getattr(impact, "atlas", False))
    impact_compass = bool(getattr(impact, "compass", False))
    impact_registry = bool(getattr(impact, "registry", False))
    impact_casebook = bool(getattr(impact, "casebook", False))
    impact_tooling_shell = bool(
        getattr(
            impact,
            "tooling_shell",
            impact_radar
            or impact_atlas
            or impact_compass
            or impact_registry
            or impact_casebook,
        )
    )
    print("workstream sync impact plan")
    print(f"- mode: {args.impact_mode}")
    print(f"- radar: {'yes' if impact_radar else 'no'}")
    print(f"- atlas: {'yes' if impact_atlas else 'no'}")
    print(f"- compass: {'yes' if impact_compass else 'no'}")
    print(f"- registry: {'yes' if impact_registry else 'no'}")
    print(f"- casebook: {'yes' if impact_casebook else 'no'}")
    print(f"- runtime_mode: {effective_runtime_mode}")
    meaningful = governance.collect_meaningful_activity_evidence(
        repo_root=repo_root,
        stream_path=repo_root / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl",
    ).as_dict()
    if meaningful:
        print(
            "- meaningful_events:"
            f" linked={int(meaningful.get('linked_meaningful_event_count', 0) or 0)}"
            f" unlinked={int(meaningful.get('unlinked_meaningful_event_count', 0) or 0)}"
        )

    run_impl = _run_command
    runtime_fallback_used = False
    if not args.check_only and _use_runtime_fast_path(effective_runtime_mode) and _runtime_fast_path_prerequisites_met(repo_root):
        try:
            _context_engine_store().warm_projections(
                repo_root=repo_root,
                reason="sync_workstream_artifacts",
            )
            run_impl = _run_command_in_process
        except Exception as exc:
            if effective_runtime_mode == "daemon":
                print(f"workstream sync failed: runtime warmup failed: {exc}")
                return 2
            print(f"- runtime_fallback: standalone ({exc})")
            runtime_fallback_used = True
    elif _use_runtime_fast_path(effective_runtime_mode):
        print("- runtime_fallback: standalone (runtime prerequisites missing)")
        runtime_fallback_used = True

    plan = build_sync_execution_plan(
        repo_root=repo_root,
        args=args,
        changed_paths=changed_paths,
        impact=impact,
        impact_tooling_shell=impact_tooling_shell,
        runtime_mode=effective_runtime_mode,
    )
    _print_execution_plan("workstream sync", plan, dry_run=bool(args.dry_run))
    if args.dry_run:
        return 0

    rc = _execute_plan(
        repo_root=repo_root,
        plan_name="workstream sync",
        plan=plan,
        run_impl=run_impl,
        runtime_fallback_used=runtime_fallback_used,
    )
    if rc != 0:
        return rc

    if args.check_clean or args.check_commit_ready:
        if args.check_clean:
            dirty = _git_dirty_generated_outputs(
                repo_root=repo_root,
            )
            if dirty:
                print("workstream sync failed: generated UI artifacts are dirty")
                print(dirty)
                print(f"if these outputs are stale, rerun `{display_command('sync', '--repo-root', '.', '--force')}`")
                print(
                    "if these outputs are already refreshed for the current change, stage/commit them or clean the worktree before rerunning `--check-clean`"
                )
                print(
                    f"for live staged validation use `{display_command('sync', '--repo-root', '.', '--check-only', '--check-commit-ready')}`"
                )
                print(
                    "for authoritative strict proof from a noisy worktree use the host-repo strict-sync entrypoint"
                )
                return 2
        if args.check_commit_ready:
            dirty = _git_commit_ready_generated_outputs(
                repo_root=repo_root,
            )
            if dirty:
                print("workstream sync failed: generated UI artifacts do not match the staged commit payload")
                print(dirty)
                print(f"run `{display_command('sync', '--repo-root', '.', '--force')}` and restage the generated outputs")
                return 2

    print("workstream sync passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
