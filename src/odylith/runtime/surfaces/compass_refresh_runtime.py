"""Shared Compass refresh runtime with request-state tracking and wait/status support."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
from typing import Any, Iterator, Mapping, Sequence

from odylith.install.fs import atomic_write_text
from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.command_surface import display_command
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_refresh_contract

REFRESH_STATE_SCHEMA_VERSION = "odylith_compass_refresh_state.v1"
REFRESH_STATE_FILENAME = "refresh-state.v1.json"
_ACTIVE_STATUSES = frozenset({"queued", "running"})
_POLL_INTERVAL_SECONDS = 0.5
_SHELL_SAFE_TIMEOUT_SECONDS = 600.0
_DEFAULT_MAX_REVIEW_AGE_DAYS = 21
_DEFAULT_ACTIVE_WINDOW_MINUTES = 15
_STAGE_LABELS = {
    "input_resolution": "input resolution",
    "projection_inputs_loaded": "projection inputs loaded",
    "activity_events_collected": "activity events collected",
    "projection_memory_ready": "projection/memory ready",
    "execution_projection_built": "execution projection built",
    "window_facts_prepared": "window facts prepared",
    "standup_briefs_built": "standup briefs built",
    "runtime_payload_built": "runtime payload built",
    "runtime_snapshots_written": "runtime snapshots written",
    "shell_bundle_written": "shell bundle written",
    "complete": "complete",
}


class CompassRefreshError(RuntimeError):
    """Raised when a Compass refresh request cannot be started or completed."""


class CompassRefreshTimeout(TimeoutError):
    """Raised when a Compass refresh exceeds its request budget."""


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith compass refresh",
        description="Refresh Compass runtime artifacts with status/wait support.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Resolve the Compass refresh runtime once up front.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the active or newly started Compass refresh request to reach a terminal state.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Read the local Compass refresh state only without mutating it.",
    )
    parser.add_argument(
        "--run-request",
        default="",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_utc(value: str) -> dt.datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _elapsed_ms(*, started_utc: str, completed_utc: str) -> float | None:
    started = _parse_utc(started_utc)
    completed = _parse_utc(completed_utc)
    if started is None or completed is None:
        return None
    return round(max(0.0, (completed - started).total_seconds() * 1000.0), 3)


def _status_command() -> str:
    return display_command("compass", "refresh", "--repo-root", ".", "--status")


def _wait_command(*, requested_runtime_mode: str) -> str:
    argv = ["compass", "refresh", "--repo-root", ".", "--wait"]
    runtime_mode = _normalize_runtime_mode(requested_runtime_mode)
    if runtime_mode != "auto":
        argv.extend(["--runtime-mode", runtime_mode])
    return display_command(*argv)


def runtime_dir(*, repo_root: Path) -> Path:
    return Path(repo_root).resolve() / "odylith" / "compass" / "runtime"


def refresh_state_path(*, repo_root: Path) -> Path:
    return runtime_dir(repo_root=repo_root) / REFRESH_STATE_FILENAME


def _lock_path(*, repo_root: Path) -> Path:
    return Path(repo_root).resolve() / ".odylith" / "locks" / "compass-refresh.lock"


@contextlib.contextmanager
def _refresh_lock(*, repo_root: Path) -> Iterator[None]:
    path = _lock_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        try:
            yield
        finally:
            handle.seek(0)
            handle.truncate()
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _normalize_refresh_profile(value: str) -> str:
    return compass_refresh_contract.normalize_refresh_profile(value, default=compass_refresh_contract.DEFAULT_REFRESH_PROFILE)


def _normalize_runtime_mode(value: str) -> str:
    token = str(value or "").strip().lower() or "auto"
    if token not in {"auto", "standalone", "daemon"}:
        return "auto"
    return token


def _context_engine_store():
    from odylith.runtime.context_engine import odylith_context_engine_store

    return odylith_context_engine_store


def _render_compass_dashboard():
    from odylith.runtime.surfaces import render_compass_dashboard

    return render_compass_dashboard


def _refresh_wait_settlement():
    from odylith.runtime.surfaces import compass_refresh_wait_settlement

    return compass_refresh_wait_settlement


def _load_state(*, repo_root: Path) -> dict[str, Any]:
    payload = odylith_context_cache.read_json_object(refresh_state_path(repo_root=repo_root))
    return _normalize_state(payload)


def _normalize_state(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    state = dict(payload) if isinstance(payload, Mapping) else {}
    stage_timings = state.get("stage_timings")
    normalized_timings: dict[str, dict[str, Any]] = {}
    if isinstance(stage_timings, Mapping):
        for key, value in stage_timings.items():
            if not isinstance(value, Mapping):
                continue
            token = str(key or "").strip()
            if not token:
                continue
            normalized_timings[token] = {
                "started_utc": str(value.get("started_utc", "")).strip(),
                "completed_utc": str(value.get("completed_utc", "")).strip(),
                "elapsed_ms": float(value.get("elapsed_ms", 0.0) or 0.0),
                "detail": str(value.get("detail", "")).strip(),
            }
    return {
        "schema_version": str(state.get("schema_version", "")).strip(),
        "request_id": str(state.get("request_id", "")).strip(),
        "requested_profile": _normalize_refresh_profile(str(state.get("requested_profile", ""))),
        "requested_runtime_mode": _normalize_runtime_mode(str(state.get("requested_runtime_mode", ""))),
        "resolved_runtime_mode": _normalize_runtime_mode(str(state.get("resolved_runtime_mode", ""))),
        "status": str(state.get("status", "")).strip().lower(),
        "requested_utc": str(state.get("requested_utc", "")).strip(),
        "started_utc": str(state.get("started_utc", "")).strip(),
        "completed_utc": str(state.get("completed_utc", "")).strip(),
        "current_stage": str(state.get("current_stage", "")).strip(),
        "current_stage_detail": str(state.get("current_stage_detail", "")).strip(),
        "stage_timings": normalized_timings,
        "pid": int(state.get("pid", 0) or 0),
        "terminal_reason": str(state.get("terminal_reason", "")).strip().lower(),
        "terminal_detail": str(state.get("terminal_detail", "")).strip(),
        "rc": int(state.get("rc", 0) or 0),
        "next_command": str(state.get("next_command", "")).strip(),
    }


def _write_state(*, repo_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path = refresh_state_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_state(payload)
    normalized["schema_version"] = REFRESH_STATE_SCHEMA_VERSION
    atomic_write_text(path, json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return normalized


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _is_active_state(state: Mapping[str, Any]) -> bool:
    status = str(state.get("status", "")).strip().lower()
    if status not in _ACTIVE_STATUSES:
        return False
    pid = int(state.get("pid", 0) or 0)
    if pid <= 0:
        return True
    return _pid_alive(pid)


def _matching_shell_safe_request(
    state: Mapping[str, Any],
    *,
    requested_profile: str,
    requested_runtime_mode: str,
) -> bool:
    return (
        str(state.get("status", "")).strip().lower() in _ACTIVE_STATUSES
        and str(state.get("requested_profile", "")).strip().lower() == "shell-safe"
        and str(state.get("requested_profile", "")).strip().lower() == str(requested_profile).strip().lower()
        and str(state.get("requested_runtime_mode", "")).strip().lower() == str(requested_runtime_mode).strip().lower()
    )


def _matching_request(
    state: Mapping[str, Any],
    *,
    requested_profile: str,
    requested_runtime_mode: str,
) -> bool:
    return (
        str(state.get("status", "")).strip().lower() in _ACTIVE_STATUSES
        and str(state.get("requested_profile", "")).strip().lower() == str(requested_profile).strip().lower()
        and str(state.get("requested_runtime_mode", "")).strip().lower() == str(requested_runtime_mode).strip().lower()
    )


def _fresh_request_id() -> str:
    return f"compass-{uuid.uuid4().hex[:12]}"


def _empty_state() -> dict[str, Any]:
    return _normalize_state({})


def _base_state(
    *,
    request_id: str,
    requested_profile: str,
    requested_runtime_mode: str,
    status: str,
) -> dict[str, Any]:
    return {
        "schema_version": REFRESH_STATE_SCHEMA_VERSION,
        "request_id": request_id,
        "requested_profile": requested_profile,
        "requested_runtime_mode": requested_runtime_mode,
        "resolved_runtime_mode": "",
        "status": status,
        "requested_utc": _now_utc_iso(),
        "started_utc": "",
        "completed_utc": "",
        "current_stage": "",
        "current_stage_detail": "",
        "stage_timings": {},
        "pid": 0,
        "terminal_reason": "",
        "terminal_detail": "",
        "rc": 0,
        "next_command": _status_command(),
    }


def _finish_stage_entry(entry: Mapping[str, Any], *, completed_utc: str) -> dict[str, Any]:
    updated = dict(entry)
    updated["completed_utc"] = completed_utc
    elapsed_ms = _elapsed_ms(
        started_utc=str(updated.get("started_utc", "")).strip(),
        completed_utc=completed_utc,
    )
    if elapsed_ms is not None:
        updated["elapsed_ms"] = elapsed_ms
    return updated


def _advance_stage(
    state: Mapping[str, Any],
    *,
    stage: str,
    at_utc: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    updated = dict(state)
    stage_token = str(stage).strip()
    if not stage_token:
        return updated
    now_utc = str(at_utc or _now_utc_iso()).strip()
    timings = {
        str(key): dict(value)
        for key, value in dict(updated.get("stage_timings", {})).items()
        if str(key).strip()
    }
    current_stage = str(updated.get("current_stage", "")).strip()
    if current_stage and current_stage != stage_token:
        prior_entry = dict(timings.get(current_stage, {}))
        if prior_entry and not str(prior_entry.get("completed_utc", "")).strip():
            timings[current_stage] = _finish_stage_entry(prior_entry, completed_utc=now_utc)
    entry = dict(timings.get(stage_token, {}))
    if not str(entry.get("started_utc", "")).strip():
        entry["started_utc"] = now_utc
    if detail is None:
        detail_token = str(entry.get("detail", "")).strip() if current_stage == stage_token else ""
    else:
        detail_token = str(detail).strip()
    entry["detail"] = detail_token
    timings[stage_token] = entry
    updated["current_stage"] = stage_token
    updated["current_stage_detail"] = detail_token
    updated["stage_timings"] = timings
    return updated


def _finalize_state(
    state: Mapping[str, Any],
    *,
    status: str,
    rc: int,
    terminal_reason: str,
    terminal_detail: str = "",
    next_command: str = "",
    at_utc: str | None = None,
) -> dict[str, Any]:
    updated = dict(state)
    now_utc = str(at_utc or _now_utc_iso()).strip()
    current_stage = str(updated.get("current_stage", "")).strip()
    if status == "passed":
        updated = _advance_stage(updated, stage="complete", at_utc=now_utc)
        current_stage = "complete"
    timings = {
        str(key): dict(value)
        for key, value in dict(updated.get("stage_timings", {})).items()
        if str(key).strip()
    }
    if current_stage:
        entry = dict(timings.get(current_stage, {}))
        if entry and not str(entry.get("completed_utc", "")).strip():
            timings[current_stage] = _finish_stage_entry(entry, completed_utc=now_utc)
    updated["status"] = str(status).strip().lower()
    updated["completed_utc"] = now_utc
    updated["terminal_reason"] = str(terminal_reason or "").strip().lower()
    updated["terminal_detail"] = str(terminal_detail or "").strip()
    updated["pid"] = 0
    updated["rc"] = int(rc)
    updated["stage_timings"] = timings
    updated["next_command"] = str(next_command).strip()
    return updated


def _resolve_runtime_mode(*, repo_root: Path, requested_runtime_mode: str) -> str:
    normalized = _normalize_runtime_mode(requested_runtime_mode)
    daemon_available = _context_engine_store().runtime_daemon_transport(repo_root=repo_root) is not None
    if normalized == "auto":
        return "daemon" if daemon_available else "standalone"
    if normalized == "daemon" and not daemon_available:
        raise CompassRefreshError("Compass refresh requires daemon runtime mode, but the local runtime daemon is unavailable.")
    return normalized


@contextlib.contextmanager
def _refresh_timeout(*, seconds: float) -> Iterator[None]:
    timeout_seconds = max(0.0, float(seconds))
    if timeout_seconds <= 0.0 or not hasattr(signal, "setitimer"):
        yield
        return

    def _handle_timeout(_signum: int, _frame: Any) -> None:
        raise CompassRefreshTimeout(f"Compass refresh exceeded {timeout_seconds:.1f}s.")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handle_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, previous_handler)


def _timeout_seconds(*, requested_profile: str) -> float:
    del requested_profile
    return _SHELL_SAFE_TIMEOUT_SECONDS


def _record_failed_live_payload(
    *,
    repo_root: Path,
    requested_profile: str,
    runtime_mode: str,
    reason: str,
) -> None:
    _render_compass_dashboard().record_failed_refresh_attempt(
        repo_root=repo_root,
        runtime_dir=runtime_dir(repo_root=repo_root),
        requested_profile=requested_profile,
        runtime_mode=runtime_mode,
        reason=reason,
        fallback_used=False,
    )


def _stage_timing_lines(state: Mapping[str, Any]) -> list[str]:
    stage_timings = state.get("stage_timings")
    if not isinstance(stage_timings, Mapping):
        return []
    lines: list[str] = []
    for stage in _STAGE_LABELS:
        entry = stage_timings.get(stage)
        if not isinstance(entry, Mapping):
            continue
        elapsed_ms = float(entry.get("elapsed_ms", 0.0) or 0.0)
        if elapsed_ms <= 0.0:
            continue
        label = _STAGE_LABELS.get(stage, stage.replace("_", " "))
        detail = str(entry.get("detail", "")).strip()
        suffix = f" ({detail})" if detail else ""
        elapsed_seconds = elapsed_ms / 1000.0
        if elapsed_seconds >= 1.0:
            elapsed_label = f"{elapsed_seconds:.1f}s"
        else:
            elapsed_label = f"{elapsed_seconds:.3f}s"
        lines.append(f"- stage_timing.{label}: {elapsed_label}{suffix}")
    return lines


def _progress_detail_summary(detail: Mapping[str, Any] | None) -> str:
    if not isinstance(detail, Mapping):
        return ""
    message = str(detail.get("message", "")).strip()
    if message:
        return message
    parts: list[str] = []
    for key in sorted(detail):
        value = detail.get(key)
        if isinstance(value, bool):
            value_token = "true" if value else "false"
        elif isinstance(value, int | float):
            value_token = str(value)
        else:
            value_token = str(value or "").strip()
        if not value_token:
            continue
        parts.append(f"{key}={value_token}")
    return ", ".join(parts[:6])[:240]


def _progress_callback_for_request(*, repo_root: Path, request_id: str) -> Any:
    def _callback(stage: str, detail: Mapping[str, Any] | None = None) -> None:
        detail_summary = _progress_detail_summary(detail)
        with _refresh_lock(repo_root=repo_root):
            state = _load_state(repo_root=repo_root)
            if str(state.get("request_id", "")).strip() != request_id:
                return
            updated = _advance_stage(state, stage=stage, detail=detail_summary)
            updated["status"] = "running"
            if not str(updated.get("started_utc", "")).strip():
                updated["started_utc"] = _now_utc_iso()
            _write_state(repo_root=repo_root, payload=updated)

    return _callback


def _render_request(
    *,
    repo_root: Path,
    request_id: str,
    requested_profile: str,
    resolved_runtime_mode: str,
) -> None:
    render_compass_dashboard = _render_compass_dashboard()
    render_compass_dashboard.render_compass_artifacts(
        repo_root=repo_root,
        output_path=repo_root / "odylith" / "compass" / "compass.html",
        runtime_dir=runtime_dir(repo_root=repo_root),
        backlog_index_path=repo_root / "odylith" / "radar" / "source" / "INDEX.md",
        plan_index_path=repo_root / "odylith" / "technical-plans" / "INDEX.md",
        bugs_index_path=repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md",
        traceability_graph_path=repo_root / "odylith" / "radar" / "traceability-graph.v1.json",
        mermaid_catalog_path=repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json",
        codex_stream_path=repo_root / agent_runtime_contract.AGENT_STREAM_PATH,
        retention_days=render_compass_dashboard.DEFAULT_HISTORY_RETENTION_DAYS,
        max_review_age_days=_DEFAULT_MAX_REVIEW_AGE_DAYS,
        active_window_minutes=_DEFAULT_ACTIVE_WINDOW_MINUTES,
        runtime_mode=resolved_runtime_mode,
        refresh_profile=requested_profile,
        progress_callback=_progress_callback_for_request(repo_root=repo_root, request_id=request_id),
    )


def _settle_standup_wait_contract(
    *,
    repo_root: Path,
    request_id: str,
    requested_runtime_mode: str,
) -> dict[str, Any]:
    settlement_runtime = _refresh_wait_settlement()
    try:
        settlement = settlement_runtime.settle_standup_maintenance(repo_root=repo_root)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}".strip().replace("\n", " ")
        with _refresh_lock(repo_root=repo_root):
            state = _load_state(repo_root=repo_root)
            if str(state.get("request_id", "")).strip() == request_id:
                failed_state = _finalize_state(
                    state,
                    status="failed",
                    rc=1,
                    terminal_reason="standup_brief_maintenance_failed",
                    terminal_detail=detail,
                    next_command=_wait_command(requested_runtime_mode=requested_runtime_mode),
                )
                _write_state(repo_root=repo_root, payload=failed_state)
        return {"rc": 1, "detail": detail, "settlement": {"status": "failed"}}

    deferred_windows = settlement_runtime.provider_deferred_global_windows(repo_root=repo_root)
    if deferred_windows:
        detail = (
            "Compass refresh finished before the live global standup brief settled for "
            + ", ".join(deferred_windows)
            + "."
        )
        with _refresh_lock(repo_root=repo_root):
            state = _load_state(repo_root=repo_root)
            if str(state.get("request_id", "")).strip() == request_id:
                failed_state = _finalize_state(
                    state,
                    status="failed",
                    rc=1,
                    terminal_reason="standup_brief_unsettled",
                    terminal_detail=detail,
                    next_command=_wait_command(requested_runtime_mode=requested_runtime_mode),
                )
                _write_state(repo_root=repo_root, payload=failed_state)
        return {"rc": 1, "detail": detail, "settlement": settlement}
    return {"rc": 0, "detail": "", "settlement": settlement}


def _execute_request(*, repo_root: Path, request_id: str) -> int:
    with _refresh_lock(repo_root=repo_root):
        state = _load_state(repo_root=repo_root)
        if str(state.get("request_id", "")).strip() != request_id:
            raise CompassRefreshError(f"Compass refresh request `{request_id}` is no longer active.")
        requested_profile = _normalize_refresh_profile(str(state.get("requested_profile", "")))
        requested_runtime_mode = _normalize_runtime_mode(str(state.get("requested_runtime_mode", "")))
        resolved_runtime_mode = str(state.get("resolved_runtime_mode", "")).strip()
        if not resolved_runtime_mode:
            resolved_runtime_mode = _resolve_runtime_mode(
                repo_root=repo_root,
                requested_runtime_mode=requested_runtime_mode,
            )
        running_state = _advance_stage(
            {
                **state,
                "status": "running",
                "started_utc": str(state.get("started_utc", "")).strip() or _now_utc_iso(),
                "resolved_runtime_mode": resolved_runtime_mode,
                "pid": os.getpid(),
                "next_command": _status_command(),
            },
            stage="input_resolution",
        )
        _write_state(repo_root=repo_root, payload=running_state)

    reason = ""
    detail = ""
    rc = 0
    try:
        with _refresh_timeout(seconds=_timeout_seconds(requested_profile=requested_profile)):
            _render_request(
                repo_root=repo_root,
                request_id=request_id,
                requested_profile=requested_profile,
                resolved_runtime_mode=resolved_runtime_mode,
            )
    except CompassRefreshTimeout:
        rc = 124
        reason = "timeout"
    except Exception as exc:
        rc = 1
        reason = "render_failed"
        detail = f"{type(exc).__name__}: {exc}".strip().replace("\n", " ")
    else:
        reason = ""
        detail = ""

    with _refresh_lock(repo_root=repo_root):
        state = _load_state(repo_root=repo_root)
        if str(state.get("request_id", "")).strip() != request_id:
            return rc
        if rc == 0:
            terminal_state = _finalize_state(
                state,
                status="passed",
                rc=0,
                terminal_reason="",
                terminal_detail="",
                next_command="",
            )
        else:
            _record_failed_live_payload(
                repo_root=repo_root,
                requested_profile=requested_profile,
                runtime_mode=str(state.get("resolved_runtime_mode", "")).strip() or resolved_runtime_mode,
                reason=reason,
            )
            terminal_state = _finalize_state(
                state,
                status="failed",
                rc=rc,
                terminal_reason=reason,
                terminal_detail=detail,
                next_command=_wait_command(requested_runtime_mode=requested_runtime_mode),
            )
        _write_state(repo_root=repo_root, payload=terminal_state)
    return rc


def _spawn_worker(*, repo_root: Path, request_id: str) -> subprocess.Popen[Any]:
    command = [
        str(Path(sys.executable).resolve()),
        "-m",
        "odylith.runtime.surfaces.compass_refresh_runtime",
        "--repo-root",
        str(repo_root),
        "--run-request",
        request_id,
    ]
    return subprocess.Popen(
        command,
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def _coalesce_or_conflict(
    *,
    state: Mapping[str, Any],
    requested_profile: str,
    requested_runtime_mode: str,
    wait: bool,
) -> dict[str, Any] | None:
    if not _is_active_state(state):
        return None
    if wait and _matching_request(
        state,
        requested_profile=requested_profile,
        requested_runtime_mode=requested_runtime_mode,
    ):
        return {
            "rc": 0,
            "status": str(state.get("status", "")).strip() or "running",
            "request_id": str(state.get("request_id", "")).strip(),
            "state": dict(state),
            "coalesced": False,
            "message": "Compass refresh request already active; waiting for terminal state.",
        }
    if wait:
        return {
            "rc": 1,
            "status": "failed",
            "request_id": str(state.get("request_id", "")).strip(),
            "state": dict(state),
            "coalesced": False,
            "message": "Another Compass refresh request is already active with different settings. Check status before starting a new one.",
        }
    if _matching_shell_safe_request(
        state,
        requested_profile=requested_profile,
        requested_runtime_mode=requested_runtime_mode,
    ):
        return {
            "rc": 0,
            "status": str(state.get("status", "")).strip() or "queued",
            "request_id": str(state.get("request_id", "")).strip(),
            "state": dict(state),
            "coalesced": True,
            "message": "Matching shell-safe Compass refresh already active; reusing that request.",
        }
    return {
        "rc": 1,
        "status": "failed",
        "request_id": str(state.get("request_id", "")).strip(),
        "state": dict(state),
        "coalesced": False,
        "message": "Another Compass refresh request is already active. Check status before starting a new one.",
    }


def _repair_stale_active_state(
    *,
    repo_root: Path,
    state: Mapping[str, Any],
    persist: bool = True,
) -> dict[str, Any]:
    request_id = str(state.get("request_id", "")).strip()
    if not request_id or not str(state.get("status", "")).strip().lower() in _ACTIVE_STATUSES:
        return dict(state)
    pid = int(state.get("pid", 0) or 0)
    if pid > 0 and _pid_alive(pid):
        return dict(state)
    terminal_reason = "worker_missing" if pid <= 0 else "worker_exited"
    terminal_detail = (
        "Compass refresh worker pid was never recorded for this active request."
        if pid <= 0
        else f"Compass refresh worker pid {pid} is no longer running."
    )
    updated = _finalize_state(
        state,
        status="failed",
        rc=1,
        terminal_reason=terminal_reason,
        terminal_detail=terminal_detail,
        next_command=_wait_command(
            requested_runtime_mode=_normalize_runtime_mode(str(state.get("requested_runtime_mode", ""))),
        ),
    )
    if persist:
        _write_state(repo_root=repo_root, payload=updated)
        _record_failed_live_payload(
            repo_root=repo_root,
            requested_profile=_normalize_refresh_profile(str(updated.get("requested_profile", ""))),
            runtime_mode=str(updated.get("resolved_runtime_mode", "")).strip()
            or _normalize_runtime_mode(str(updated.get("requested_runtime_mode", ""))),
            reason=terminal_reason,
        )
    return updated


def _failed_start_result(
    *,
    repo_root: Path,
    request_id: str,
    requested_profile: str,
    requested_runtime_mode: str,
    terminal_reason: str,
    message: str,
) -> dict[str, Any]:
    failed_state = _write_state(
        repo_root=repo_root,
        payload=_finalize_state(
            _base_state(
                request_id=request_id,
                requested_profile=requested_profile,
                requested_runtime_mode=requested_runtime_mode,
                status="queued",
            ),
            status="failed",
            rc=1,
            terminal_reason=terminal_reason,
            next_command=_wait_command(requested_runtime_mode=requested_runtime_mode),
        ),
    )
    _record_failed_live_payload(
        repo_root=repo_root,
        requested_profile=requested_profile,
        runtime_mode=str(failed_state.get("resolved_runtime_mode", "")).strip() or requested_runtime_mode,
        reason=terminal_reason,
    )
    return {
        "rc": 1,
        "status": "failed",
        "request_id": request_id,
        "state": failed_state,
        "coalesced": False,
        "message": message,
    }


def _enqueue_request(
    *,
    repo_root: Path,
    requested_profile: str,
    requested_runtime_mode: str,
) -> dict[str, Any]:
    with _refresh_lock(repo_root=repo_root):
        current = _repair_stale_active_state(repo_root=repo_root, state=_load_state(repo_root=repo_root))
        existing = _coalesce_or_conflict(
            state=current,
            requested_profile=requested_profile,
            requested_runtime_mode=requested_runtime_mode,
            wait=False,
        )
        if existing is not None:
            return existing
        request_id = _fresh_request_id()
        try:
            resolved_runtime_mode = _resolve_runtime_mode(
                repo_root=repo_root,
                requested_runtime_mode=requested_runtime_mode,
            )
        except CompassRefreshError as exc:
            return _failed_start_result(
                repo_root=repo_root,
                request_id=request_id,
                requested_profile=requested_profile,
                requested_runtime_mode=requested_runtime_mode,
                terminal_reason="mode_resolution_failed",
                message=str(exc),
            )
        queued_state = _write_state(
            repo_root=repo_root,
            payload={
                **_base_state(
                    request_id=request_id,
                    requested_profile=requested_profile,
                    requested_runtime_mode=requested_runtime_mode,
                    status="queued",
                ),
                "resolved_runtime_mode": resolved_runtime_mode,
            },
        )

    try:
        worker = _spawn_worker(repo_root=repo_root, request_id=request_id)
    except Exception:
        with _refresh_lock(repo_root=repo_root):
            failed_state = _finalize_state(
                queued_state,
                status="failed",
                rc=1,
                terminal_reason="worker_spawn_failed",
                next_command=_wait_command(requested_runtime_mode=requested_runtime_mode),
            )
            _write_state(repo_root=repo_root, payload=failed_state)
        _record_failed_live_payload(
            repo_root=repo_root,
            requested_profile=requested_profile,
            runtime_mode=str(queued_state.get("resolved_runtime_mode", "")).strip() or requested_runtime_mode,
            reason="worker_spawn_failed",
        )
        return {
            "rc": 1,
            "status": "failed",
            "request_id": request_id,
            "state": failed_state,
            "coalesced": False,
            "message": "Compass refresh worker failed to start.",
        }

    with _refresh_lock(repo_root=repo_root):
        active_state = _load_state(repo_root=repo_root)
        if str(active_state.get("request_id", "")).strip() == request_id:
            active_state = {
                **active_state,
                "pid": int(worker.pid or 0),
                "next_command": _status_command(),
            }
            active_state = _write_state(repo_root=repo_root, payload=active_state)
        else:
            active_state = _load_state(repo_root=repo_root)
    return {
        "rc": 0,
        "status": str(active_state.get("status", "")).strip() or "queued",
        "request_id": request_id,
        "state": active_state,
        "coalesced": False,
        "message": "Compass refresh queued.",
    }


def _run_foreground_request(
    *,
    repo_root: Path,
    requested_profile: str,
    requested_runtime_mode: str,
    settle_standup_maintenance: bool = False,
) -> dict[str, Any]:
    with _refresh_lock(repo_root=repo_root):
        current = _repair_stale_active_state(repo_root=repo_root, state=_load_state(repo_root=repo_root))
        existing = _coalesce_or_conflict(
            state=current,
            requested_profile=requested_profile,
            requested_runtime_mode=requested_runtime_mode,
            wait=False,
        )
        if existing is not None:
            return existing
        request_id = _fresh_request_id()
        try:
            resolved_runtime_mode = _resolve_runtime_mode(
                repo_root=repo_root,
                requested_runtime_mode=requested_runtime_mode,
            )
        except CompassRefreshError as exc:
            return _failed_start_result(
                repo_root=repo_root,
                request_id=request_id,
                requested_profile=requested_profile,
                requested_runtime_mode=requested_runtime_mode,
                terminal_reason="mode_resolution_failed",
                message=str(exc),
            )
        pending_state = _write_state(
            repo_root=repo_root,
            payload={
                **_base_state(
                    request_id=request_id,
                    requested_profile=requested_profile,
                    requested_runtime_mode=requested_runtime_mode,
                    status="queued",
                ),
                "resolved_runtime_mode": resolved_runtime_mode,
            },
        )
        pending_state = {
            **pending_state,
            "pid": os.getpid(),
        }
        _write_state(repo_root=repo_root, payload=pending_state)

    rc = _execute_request(repo_root=repo_root, request_id=request_id)
    settlement: dict[str, Any] = {}
    if rc == 0 and settle_standup_maintenance:
        settlement_result = _settle_standup_wait_contract(
            repo_root=repo_root,
            request_id=request_id,
            requested_runtime_mode=requested_runtime_mode,
        )
        settlement = dict(settlement_result.get("settlement", {}))
        rc = int(settlement_result.get("rc", rc) or rc)
    state = _load_state(repo_root=repo_root)
    return {
        "rc": rc,
        "status": str(state.get("status", "")).strip() or ("passed" if rc == 0 else "failed"),
        "request_id": request_id,
        "state": state,
        "coalesced": False,
        "message": "Compass refresh completed." if rc == 0 else "Compass refresh failed.",
        "standup_maintenance": settlement,
    }


def _format_elapsed_seconds(state: Mapping[str, Any]) -> str:
    started = _parse_utc(str(state.get("started_utc", "")).strip() or str(state.get("requested_utc", "")).strip())
    completed = _parse_utc(str(state.get("completed_utc", "")).strip())
    if started is None:
        return ""
    end = completed or dt.datetime.now(dt.timezone.utc)
    return f"{max(0.0, (end - started).total_seconds()):.1f}"


def _wait_for_terminal(
    *,
    repo_root: Path,
    request_id: str,
    settle_standup_maintenance: bool = False,
) -> dict[str, Any]:
    print("compass refresh waiting")
    print(f"- request_id: {request_id}")
    last_status = ""
    last_stage = ""
    last_stage_detail = ""
    while True:
        with _refresh_lock(repo_root=repo_root):
            state = _repair_stale_active_state(repo_root=repo_root, state=_load_state(repo_root=repo_root))
        state_request_id = str(state.get("request_id", "")).strip()
        status = str(state.get("status", "")).strip().lower()
        if state_request_id != request_id:
            raise CompassRefreshError("Compass refresh request changed while waiting.")
        if status and status != last_status:
            print(f"- status: {status}")
            last_status = status
        current_stage = str(state.get("current_stage", "")).strip()
        if current_stage and current_stage != last_stage:
            print(f"- stage: {_STAGE_LABELS.get(current_stage, current_stage.replace('_', ' '))}")
            last_stage = current_stage
            last_stage_detail = ""
        current_stage_detail = str(state.get("current_stage_detail", "")).strip()
        if current_stage_detail and current_stage_detail != last_stage_detail:
            print(f"- detail: {current_stage_detail}")
            last_stage_detail = current_stage_detail
        if status not in _ACTIVE_STATUSES:
            rc = int(state.get("rc", 0) or 0)
            settlement: dict[str, Any] = {}
            if rc == 0 and settle_standup_maintenance:
                settlement_result = _settle_standup_wait_contract(
                    repo_root=repo_root,
                    request_id=request_id,
                    requested_runtime_mode=str(state.get("requested_runtime_mode", "")).strip() or "auto",
                )
                settlement = dict(settlement_result.get("settlement", {}))
                state = _load_state(repo_root=repo_root)
                status = str(state.get("status", "")).strip().lower()
                rc = int(state.get("rc", 0) or 0)
            print(f"- outcome: {status or ('passed' if rc == 0 else 'failed')}")
            elapsed_seconds = _format_elapsed_seconds(state)
            if elapsed_seconds:
                print(f"- elapsed_seconds: {elapsed_seconds}")
            resolved_runtime_mode = str(state.get("resolved_runtime_mode", "")).strip()
            if resolved_runtime_mode:
                print(f"- resolved_runtime_mode: {resolved_runtime_mode}")
            settlement_status = str(settlement.get("status", "")).strip()
            if settlement_status:
                print(f"- standup_brief_settlement: {settlement_status}")
            reason = str(state.get("terminal_reason", "")).strip()
            if reason:
                print(f"- reason: {reason}")
            for line in _stage_timing_lines(state):
                print(line)
            next_command = str(state.get("next_command", "")).strip()
            if next_command:
                print(f"- next: {next_command}")
            return {
                "rc": rc,
                "status": status or ("passed" if rc == 0 else "failed"),
                "request_id": request_id,
                "state": state,
                "coalesced": False,
                "message": "",
                "standup_maintenance": settlement,
            }
        time.sleep(_POLL_INTERVAL_SECONDS)


def _print_status(*, repo_root: Path) -> dict[str, Any]:
    with _refresh_lock(repo_root=repo_root):
        state = _repair_stale_active_state(
            repo_root=repo_root,
            state=_load_state(repo_root=repo_root),
            persist=False,
        )
    if not str(state.get("request_id", "")).strip():
        print("compass refresh status")
        print("- status: idle")
        print("- next: " + display_command("compass", "refresh", "--repo-root", "."))
        return {
            "rc": 0,
            "status": "idle",
            "request_id": "",
            "state": state,
            "coalesced": False,
            "message": "",
        }
    print("compass refresh status")
    print(f"- request_id: {state.get('request_id', '')}")
    print(f"- status: {state.get('status', '')}")
    print(f"- requested_profile: {state.get('requested_profile', '')}")
    print(f"- requested_runtime_mode: {state.get('requested_runtime_mode', '')}")
    resolved_runtime_mode = str(state.get("resolved_runtime_mode", "")).strip()
    if resolved_runtime_mode:
        print(f"- resolved_runtime_mode: {resolved_runtime_mode}")
    current_stage = str(state.get("current_stage", "")).strip()
    if current_stage:
        print(f"- current_stage: {_STAGE_LABELS.get(current_stage, current_stage.replace('_', ' '))}")
    current_stage_detail = str(state.get("current_stage_detail", "")).strip()
    if current_stage_detail:
        print(f"- current_stage_detail: {current_stage_detail}")
    started_utc = str(state.get("started_utc", "")).strip()
    if started_utc:
        print(f"- started_utc: {started_utc}")
    completed_utc = str(state.get("completed_utc", "")).strip()
    if completed_utc:
        print(f"- completed_utc: {completed_utc}")
    terminal_reason = str(state.get("terminal_reason", "")).strip()
    if terminal_reason:
        print(f"- terminal_reason: {terminal_reason}")
    terminal_detail = str(state.get("terminal_detail", "")).strip()
    if terminal_detail:
        print(f"- terminal_detail: {terminal_detail}")
    for line in _stage_timing_lines(state):
        print(line)
    next_command = str(state.get("next_command", "")).strip()
    if next_command:
        print(f"- next: {next_command}")
    return {
        "rc": 0,
        "status": str(state.get("status", "")).strip() or "idle",
        "request_id": str(state.get("request_id", "")).strip(),
        "state": state,
        "coalesced": False,
        "message": "",
    }


def _print_start_result(result: Mapping[str, Any]) -> None:
    status = str(result.get("status", "")).strip().lower()
    state = dict(result.get("state", {})) if isinstance(result.get("state"), Mapping) else {}
    request_id = str(result.get("request_id", "")).strip()
    title = "queued" if status in {"queued", "running"} else "failed"
    print(f"compass refresh {title}")
    if request_id:
        print(f"- request_id: {request_id}")
    if status:
        print(f"- status: {status}")
    message = str(result.get("message", "")).strip()
    if message:
        print(f"- detail: {message}")
    print(f"- requested_profile: {state.get('requested_profile', '') or compass_refresh_contract.DEFAULT_REFRESH_PROFILE}")
    print(f"- requested_runtime_mode: {state.get('requested_runtime_mode', '') or 'auto'}")
    print("- next: " + _status_command())
    wait_command = _wait_command(
        requested_runtime_mode=str(state.get("requested_runtime_mode", "")).strip() or "auto",
    )
    print(f"- wait: {wait_command}")


def _print_terminal_result(result: Mapping[str, Any]) -> None:
    state = dict(result.get("state", {})) if isinstance(result.get("state"), Mapping) else {}
    settlement = (
        dict(result.get("standup_maintenance", {}))
        if isinstance(result.get("standup_maintenance"), Mapping)
        else {}
    )
    rc = int(result.get("rc", 0) or 0)
    request_id = str(result.get("request_id", "")).strip()
    if rc == 0:
        print("compass refresh passed")
        if request_id:
            print(f"- request_id: {request_id}")
        resolved_runtime_mode = str(state.get("resolved_runtime_mode", "")).strip()
        if resolved_runtime_mode:
            print(f"- resolved_runtime_mode: {resolved_runtime_mode}")
        print(f"- elapsed_seconds: {_format_elapsed_seconds(state)}")
        settlement_status = str(settlement.get("status", "")).strip()
        if settlement_status:
            print(f"- standup_brief_settlement: {settlement_status}")
        for line in _stage_timing_lines(state):
            print(line)
        return

    print("compass refresh FAILED")
    if request_id:
        print(f"- request_id: {request_id}")
    print(f"- reason: {state.get('terminal_reason', '')}")
    detail = str(state.get("terminal_detail", "")).strip()
    if detail:
        print(f"- detail: {detail}")
    resolved_runtime_mode = str(state.get("resolved_runtime_mode", "")).strip()
    if resolved_runtime_mode:
        print(f"- resolved_runtime_mode: {resolved_runtime_mode}")
    for line in _stage_timing_lines(state):
        print(line)
    next_command = str(state.get("next_command", "")).strip()
    if next_command:
        print(f"- next: {next_command}")


def run_refresh(
    *,
    repo_root: Path,
    requested_profile: str,
    requested_runtime_mode: str,
    wait: bool,
    status_only: bool,
    emit_output: bool = True,
) -> dict[str, Any]:
    normalized_profile = _normalize_refresh_profile(requested_profile)
    normalized_runtime_mode = _normalize_runtime_mode(requested_runtime_mode)
    root = Path(repo_root).resolve()

    if status_only:
        if emit_output:
            return _print_status(repo_root=root)
        with _refresh_lock(repo_root=root):
            state = _repair_stale_active_state(
                repo_root=root,
                state=_load_state(repo_root=root),
                persist=False,
            )
        return {
            "rc": 0,
            "status": str(state.get("status", "")).strip() or "idle",
            "request_id": str(state.get("request_id", "")).strip(),
            "state": state,
            "coalesced": False,
            "message": "",
        }

    if wait:
        with _refresh_lock(repo_root=root):
            current = _repair_stale_active_state(repo_root=root, state=_load_state(repo_root=root))
            existing = _coalesce_or_conflict(
                state=current,
                requested_profile=normalized_profile,
                requested_runtime_mode=normalized_runtime_mode,
                wait=True,
            )
        if existing is not None and int(existing.get("rc", 0) or 0) != 0:
            if emit_output:
                _print_start_result(existing)
            return existing
        if existing is None:
            result = _run_foreground_request(
                repo_root=root,
                requested_profile=normalized_profile,
                requested_runtime_mode=normalized_runtime_mode,
                settle_standup_maintenance=True,
            )
            if emit_output:
                _print_terminal_result(result)
            return result
        return _wait_for_terminal(
            repo_root=root,
            request_id=str(existing.get("request_id", "")).strip(),
            settle_standup_maintenance=True,
        )

    result = _enqueue_request(
        repo_root=root,
        requested_profile=normalized_profile,
        requested_runtime_mode=normalized_runtime_mode,
    )
    if emit_output:
        _print_start_result(result)
    return result


def _run_request_main(*, repo_root: Path, request_id: str) -> int:
    try:
        return _execute_request(repo_root=repo_root, request_id=request_id)
    except Exception as exc:
        with _refresh_lock(repo_root=repo_root):
            state = _load_state(repo_root=repo_root)
            if str(state.get("request_id", "")).strip() == request_id:
                requested_profile = _normalize_refresh_profile(str(state.get("requested_profile", "")))
                requested_runtime_mode = _normalize_runtime_mode(str(state.get("requested_runtime_mode", "")))
                reason = "mode_resolution_failed" if not str(state.get("started_utc", "")).strip() else "render_failed"
                failed_state = _finalize_state(
                    state,
                    status="failed",
                    rc=1,
                    terminal_reason=reason,
                    terminal_detail=f"{type(exc).__name__}: {exc}".strip().replace("\n", " "),
                    next_command=_wait_command(requested_runtime_mode=requested_runtime_mode),
                )
                _write_state(repo_root=repo_root, payload=failed_state)
                _record_failed_live_payload(
                    repo_root=repo_root,
                    requested_profile=requested_profile,
                    runtime_mode=str(failed_state.get("resolved_runtime_mode", "")).strip() or requested_runtime_mode,
                    reason=reason,
                )
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if str(args.run_request).strip():
        return _run_request_main(repo_root=repo_root, request_id=str(args.run_request).strip())
    result = run_refresh(
        repo_root=repo_root,
        requested_profile=compass_refresh_contract.DEFAULT_REFRESH_PROFILE,
        requested_runtime_mode=str(args.runtime_mode),
        wait=bool(args.wait),
        status_only=bool(args.status),
        emit_output=True,
    )
    return int(result.get("rc", 0) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
