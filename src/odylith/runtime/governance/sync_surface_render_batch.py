"""Run the sync-only governance surface render batch."""

from __future__ import annotations

import concurrent.futures
from contextvars import copy_context
from dataclasses import dataclass
import io
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class SyncSurfaceBatchRuntime:
    normalize_dashboard_surfaces: Callable[[Sequence[str]], list[str]]
    surface_render_outputs: Callable[[str], tuple[str, ...]]
    dashboard_surface_steps: Callable[..., Sequence[Any]]
    execute_dashboard_refresh_surface: Callable[..., dict[str, Any]]
    use_runtime_fast_path: Callable[[str], bool]
    runtime_fast_path_prerequisites_met: Callable[[Path], bool]
    run_command: Callable[..., int]
    run_command_in_process_direct: Callable[..., int]
    skip_generated_refresh_guard_env: str


class _ThreadCapturePrint:
    def __init__(self, *, real_stdout: Any, capture_state: threading.local) -> None:
        self._real_stdout = real_stdout
        self._capture_state = capture_state

    def _target(self) -> Any:
        buffer = getattr(self._capture_state, "buf", None)
        return buffer if buffer is not None else self._real_stdout

    def write(self, text: str) -> int:
        return self._target().write(text)

    def flush(self) -> None:
        self._target().flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_stdout, name)


_SYNC_SURFACE_THREAD_CAPTURE: threading.local = threading.local()


def sync_surface_batch_outputs(
    *,
    surfaces: Sequence[str],
    surface_render_outputs: Callable[[str], tuple[str, ...]],
) -> tuple[str, ...]:
    outputs: list[str] = []
    seen: set[str] = set()
    for surface in surfaces:
        for output in surface_render_outputs(surface):
            if output not in seen:
                seen.add(output)
                outputs.append(output)
    return tuple(outputs)


def _sync_surface_steps(
    *,
    runtime: SyncSurfaceBatchRuntime,
    repo_root: Path,
    surface: str,
    runtime_mode: str,
) -> list[Any]:
    steps = runtime.dashboard_surface_steps(
        repo_root=repo_root,
        surface=surface,
        runtime_mode=runtime_mode,
        atlas_sync=False,
    )
    return [
        step
        for step in steps
        if not step.label.startswith("Refresh delivery intelligence inputs")
        and not step.label.startswith("Normalize and validate Casebook bugs")
    ]


def _run_sync_surface_worker(
    *,
    runtime: SyncSurfaceBatchRuntime,
    repo_root: Path,
    surface: str,
    runtime_mode: str,
    run_impl: Callable[..., int],
) -> tuple[str, dict[str, Any]]:
    capture = io.StringIO()
    _SYNC_SURFACE_THREAD_CAPTURE.buf = capture
    try:
        steps = _sync_surface_steps(
            runtime=runtime,
            repo_root=repo_root,
            surface=surface,
            runtime_mode=runtime_mode,
        )
        result = runtime.execute_dashboard_refresh_surface(
            repo_root=repo_root,
            surface=surface,
            steps=steps,
            runtime_mode=runtime_mode,
            run_impl=run_impl,
        )
    finally:
        _SYNC_SURFACE_THREAD_CAPTURE.buf = None
    return capture.getvalue(), result


def _refresh_sync_surfaces_parallel(
    *,
    runtime: SyncSurfaceBatchRuntime,
    repo_root: Path,
    selected: Sequence[str],
    runtime_mode: str,
    run_impl: Callable[..., int],
) -> list[dict[str, Any]]:
    future_map: dict[concurrent.futures.Future[tuple[str, dict[str, Any]]], str] = {}
    real_stdout = sys.stdout
    sys.stdout = _ThreadCapturePrint(  # type: ignore[assignment]
        real_stdout=real_stdout,
        capture_state=_SYNC_SURFACE_THREAD_CAPTURE,
    )
    try:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(selected),
            thread_name_prefix="sync_surface",
        ) as executor:
            for surface in selected:
                worker_context = copy_context()
                future = executor.submit(
                    worker_context.run,
                    _run_sync_surface_worker,
                    runtime=runtime,
                    repo_root=repo_root,
                    surface=surface,
                    runtime_mode=runtime_mode,
                    run_impl=run_impl,
                )
                future_map[future] = surface
    finally:
        sys.stdout = real_stdout
    results_by_surface: dict[str, tuple[str, dict[str, Any]]] = {}
    for future, surface in future_map.items():
        output, result = future.result()
        results_by_surface[surface] = (output, result)
    ordered_results: list[dict[str, Any]] = []
    for surface in selected:
        output, result = results_by_surface[surface]
        if output:
            sys.stdout.write(output)
            if not output.endswith("\n"):
                sys.stdout.write("\n")
        ordered_results.append(result)
    return ordered_results


def _sync_surface_groups(selected: Sequence[str]) -> list[list[str]]:
    if "compass" in selected and len(selected) > 1:
        groups = [["compass"], [surface for surface in selected if surface not in {"compass", "tooling_shell"}]]
        if "tooling_shell" in selected:
            groups.append(["tooling_shell"])
        return groups
    if "tooling_shell" in selected and len(selected) > 1:
        return [[surface for surface in selected if surface != "tooling_shell"], ["tooling_shell"]]
    return [list(selected)]


def _emit_surface_output(output: str) -> None:
    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")


def _emit_sync_surface_batch_summary(
    *,
    selected: Sequence[str],
    surface_results: Sequence[dict[str, Any]],
    runtime_fallback_used: bool,
    elapsed_seconds: float,
) -> int:
    failures = [result for result in surface_results if str(result.get("status", "")).strip() == "failed"]
    queued = [result for result in surface_results if str(result.get("status", "")).strip() == "queued"]
    print("sync surface render batch completed")
    if failures:
        print("- outcome: failed")
    elif queued:
        print("- outcome: queued")
    else:
        print("- outcome: passed")
    print("- surfaces: " + ", ".join(selected))
    print(f"- elapsed_seconds: {elapsed_seconds:.1f}")
    print(f"- runtime_fallback_used: {'yes' if runtime_fallback_used else 'no'}")
    for result in surface_results:
        surface = str(result.get("surface", "")).strip()
        status = str(result.get("status", "")).strip() or "failed"
        suffix = " (standalone fallback used)" if bool(result.get("fallback_used")) else ""
        if bool(result.get("cache_hit")):
            suffix += " (fingerprint reuse)"
        print(f"- {surface}: {status}{suffix}")
        if status not in {"passed", "queued"}:
            failed_step = str(result.get("failed_step", "")).strip()
            next_command = str(result.get("next_command", "")).strip()
            if failed_step:
                print(f"  failed_step: {failed_step}")
            if next_command:
                print(f"  next: {next_command}")
        elif status == "queued":
            next_command = str(result.get("next_command", "")).strip()
            if next_command:
                print(f"  next: {next_command}")
    return 2 if failures else 0


def run_sync_surface_render_batch(
    *,
    runtime: SyncSurfaceBatchRuntime,
    repo_root: Path,
    surfaces: Sequence[str],
    runtime_mode: str,
) -> int:
    selected = runtime.normalize_dashboard_surfaces(surfaces)
    normalized_runtime_mode = str(runtime_mode).strip().lower() or "auto"
    run_impl = runtime.run_command
    runtime_fallback_used = False
    if runtime.use_runtime_fast_path(normalized_runtime_mode) and runtime.runtime_fast_path_prerequisites_met(repo_root):
        run_impl = runtime.run_command_in_process_direct
    elif runtime.use_runtime_fast_path(normalized_runtime_mode):
        print("- runtime_fallback: standalone (runtime prerequisites missing)")
        runtime_fallback_used = True

    started_at = time.perf_counter()
    surface_results: list[dict[str, Any]] = []
    previous_guard_skip = os.environ.get(runtime.skip_generated_refresh_guard_env)
    os.environ[runtime.skip_generated_refresh_guard_env] = "1"
    try:
        for surface_group in _sync_surface_groups(selected):
            if not surface_group:
                continue
            if len(surface_group) >= 2:
                surface_results.extend(
                    _refresh_sync_surfaces_parallel(
                        runtime=runtime,
                        repo_root=repo_root,
                        selected=surface_group,
                        runtime_mode=normalized_runtime_mode,
                        run_impl=run_impl,
                    )
                )
                continue
            output, result = _run_sync_surface_worker(
                runtime=runtime,
                repo_root=repo_root,
                surface=surface_group[0],
                runtime_mode=normalized_runtime_mode,
                run_impl=run_impl,
            )
            _emit_surface_output(output)
            surface_results.append(result)
    finally:
        if previous_guard_skip is None:
            os.environ.pop(runtime.skip_generated_refresh_guard_env, None)
        else:
            os.environ[runtime.skip_generated_refresh_guard_env] = previous_guard_skip

    for result in surface_results:
        runtime_fallback_used = runtime_fallback_used or bool(result.get("fallback_used"))
    return _emit_sync_surface_batch_summary(
        selected=selected,
        surface_results=surface_results,
        runtime_fallback_used=runtime_fallback_used,
        elapsed_seconds=time.perf_counter() - started_at,
    )
