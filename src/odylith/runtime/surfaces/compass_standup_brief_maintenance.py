"""Maintained narrated-cache warming for Compass standup briefs.

This module keeps refresh-time Compass cheap by moving narrated cache warming
into a deduped sidecar lane. Refresh writes one local-only packet request
containing any missing global windows plus any missing verified scoped briefs
for that same runtime fingerprint, then a cheap provider-neutral worker warms
that packet bundle and patches the current runtime snapshot only if it still
matches the same input fingerprint.
"""

from __future__ import annotations

from dataclasses import replace
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_batch
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_standup_brief_telemetry

_REQUEST_VERSION = "v1"
_STATE_VERSION = "v1"
_REQUEST_PATH = ".odylith/compass/standup-brief-maintenance-request.v1.json"
_STATE_PATH = ".odylith/compass/standup-brief-maintenance-state.v1.json"
_RUNTIME_CURRENT_JSON = "odylith/compass/runtime/current.v1.json"
_RUNTIME_CURRENT_JS = "odylith/compass/runtime/current.v1.js"
_FAILED_RETRY_BASE_SECONDS = 300
_FAILED_RETRY_MAX_SECONDS = 3600
_INVALID_BATCH_RETRY_BASE_SECONDS = 1800
_INVALID_BATCH_RETRY_MAX_SECONDS = 21600
_PROVIDER_UNAVAILABLE_RETRY_BASE_SECONDS = 1800
_PROVIDER_UNAVAILABLE_RETRY_MAX_SECONDS = 21600
_RETRY_POLL_INTERVAL_SECONDS = 5
_MAX_SCOPED_REQUESTS_PER_WINDOW = 4
_WORKER_EPOCH_RELATIVE_PATHS = (
    "src/odylith/runtime/surfaces/compass_standup_brief_maintenance.py",
    "src/odylith/runtime/surfaces/compass_standup_brief_batch.py",
    "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
    "src/odylith/runtime/surfaces/compass_standup_brief_substrate.py",
    "src/odylith/runtime/surfaces/compass_standup_brief_telemetry.py",
)
def maintenance_request_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / _REQUEST_PATH).resolve()


def maintenance_state_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / _STATE_PATH).resolve()


def _now_utc_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = odylith_context_cache.read_json_object(path)
    return dict(payload) if isinstance(payload, Mapping) else {}


def _write_json(*, repo_root: Path, path: Path, payload: Mapping[str, Any]) -> None:
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(path),
    )


def _load_state(*, repo_root: Path) -> dict[str, Any]:
    state = _load_json(maintenance_state_path(repo_root=repo_root))
    entries = state.get("entries")
    return {
        "version": _STATE_VERSION,
        "active_pid": int(state.get("active_pid", 0) or 0),
        "last_run_utc": str(state.get("last_run_utc", "")).strip(),
        "worker_epoch": str(state.get("worker_epoch", "")).strip(),
        "worker_python_bin": str(state.get("worker_python_bin", "")).strip(),
        "entries": dict(entries) if isinstance(entries, Mapping) else {},
    }


def _write_state(*, repo_root: Path, state: Mapping[str, Any]) -> None:
    _write_json(
        repo_root=repo_root,
        path=maintenance_state_path(repo_root=repo_root),
        payload={
            "version": _STATE_VERSION,
            "active_pid": int(state.get("active_pid", 0) or 0),
            "last_run_utc": str(state.get("last_run_utc", "")).strip(),
            "worker_epoch": str(state.get("worker_epoch", "")).strip(),
            "worker_python_bin": str(state.get("worker_python_bin", "")).strip(),
            "entries": dict(state.get("entries", {})) if isinstance(state.get("entries"), Mapping) else {},
        },
    )


def _pid_alive(pid: int) -> bool:
    if int(pid) <= 0:
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _worker_python_bin() -> str:
    return str(Path(sys.executable).resolve()) if str(sys.executable).strip() else "python3"


def _worker_epoch(*, repo_root: Path) -> str:
    root = Path(repo_root).resolve()
    return odylith_context_cache.fingerprint_payload(
        {
            "state_version": _STATE_VERSION,
            "request_version": _REQUEST_VERSION,
            "standup_brief_schema_version": compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "paths": {
                relative_path: odylith_context_cache.path_signature(root / relative_path)
                for relative_path in _WORKER_EPOCH_RELATIVE_PATHS
            },
        }
    )


def _worker_matches_current(*, repo_root: Path, state: Mapping[str, Any], python_bin: str) -> bool:
    return (
        str(state.get("worker_epoch", "")).strip() == _worker_epoch(repo_root=repo_root)
        and str(state.get("worker_python_bin", "")).strip() == str(python_bin).strip()
    )


def _terminate_worker(pid: int) -> None:
    if not _pid_alive(pid):
        return
    try:
        os.kill(int(pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return


def _maintenance_worker_pids(*, repo_root: Path) -> list[int]:
    repo_root_token = str(Path(repo_root).resolve())
    try:
        completed = subprocess.run(  # noqa: S603
            ["ps", "-ax", "-o", "pid=,command="],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    pids: list[int] = []
    for raw_line in str(completed.stdout or "").splitlines():
        line = str(raw_line).strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pid_token, command = parts
        if (
            "odylith.runtime.surfaces.compass_standup_brief_maintenance" not in command
            or "--repo-root" not in command
            or repo_root_token not in command
        ):
            continue
        try:
            pid = int(pid_token)
        except ValueError:
            continue
        if pid > 0:
            pids.append(pid)
    return sorted(set(pids))
    deadline = time.time() + 1.0
    while time.time() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.05)
    try:
        os.kill(int(pid), signal.SIGKILL)
    except ProcessLookupError:
        return
    except PermissionError:
        return


def _candidate_key(*, window_key: str, scope_id: str = "") -> str:
    return f"global:{window_key}" if not str(scope_id).strip() else f"scoped:{window_key}:{str(scope_id).strip()}"


def _terminal_state_matches(
    *,
    state_entries: Mapping[str, Any],
    key: str,
    fingerprint: str,
) -> bool:
    entry = state_entries.get(key)
    if not isinstance(entry, Mapping):
        return False
    if str(entry.get("fingerprint", "")).strip() != str(fingerprint).strip():
        return False
    status = str(entry.get("status", "")).strip().lower()
    return status in {"ready", "skipped"}


def _provider_backoff_failure(code: str) -> bool:
    token = str(code or "").strip().lower()
    return token in {
        "rate_limited",
        "credits_exhausted",
        "timeout",
        "provider_unavailable",
        "transport_error",
        "auth_error",
        "provider_error",
    }


def _state_entry_is_nonready(entry: Mapping[str, Any] | None) -> bool:
    if not isinstance(entry, Mapping):
        return False
    status = str(entry.get("status", "")).strip().lower()
    return bool(status) and status not in {"ready", "skipped"}


def _scope_signal_priority(
    *,
    signal_entry: Mapping[str, Any] | None,
    state_entry: Mapping[str, Any] | None,
    fingerprint: str,
    scope_id: str,
) -> tuple[int, int, int, int, int, int, int, str]:
    signal_mapping = dict(signal_entry) if isinstance(signal_entry, Mapping) else {}
    feature_vector = (
        dict(signal_mapping.get("feature_vector"))
        if isinstance(signal_mapping.get("feature_vector"), Mapping)
        else {}
    )
    same_fingerprint_retry = int(
        _state_entry_is_nonready(state_entry)
        and str(state_entry.get("fingerprint", "")).strip() == str(fingerprint).strip()
    )
    rung_order = {
        "R4": 4,
        "R3": 3,
        "R2": 2,
        "R1": 1,
        "R0": 0,
    }
    return (
        same_fingerprint_retry,
        int(bool(feature_vector.get("verified_completion"))),
        int(bool(feature_vector.get("implementation_evidence"))),
        int(bool(feature_vector.get("decision_evidence"))),
        int(bool(feature_vector.get("meaningful_scope_activity"))),
        int(rung_order.get(str(signal_mapping.get("rung", "")).strip().upper(), 0)),
        int(signal_mapping.get("rank", 0) or 0),
        str(scope_id).strip(),
    )


def _retry_backoff_seconds(
    *,
    status: str,
    source: str,
    attempt_count: int,
    failure_code: str = "",
    failure_reason: str = "",
) -> int:
    status_token = str(status).strip().lower()
    source_token = str(source).strip().lower()
    reason_token = str(failure_reason).strip().lower()
    attempts = max(1, int(attempt_count))
    if reason_token == "invalid_batch":
        base = _INVALID_BATCH_RETRY_BASE_SECONDS
        cap = _INVALID_BATCH_RETRY_MAX_SECONDS
    elif status_token == "provider_unavailable" or source_token == "none" or _provider_backoff_failure(failure_code):
        base = _PROVIDER_UNAVAILABLE_RETRY_BASE_SECONDS
        cap = _PROVIDER_UNAVAILABLE_RETRY_MAX_SECONDS
    else:
        base = _FAILED_RETRY_BASE_SECONDS
        cap = _FAILED_RETRY_MAX_SECONDS
    return min(base * (2 ** (attempts - 1)), cap)


def _ready_narrated(brief: Mapping[str, Any] | None) -> bool:
    return (
        isinstance(brief, Mapping)
        and str(brief.get("status", "")).strip().lower() == "ready"
        and str(brief.get("source", "")).strip().lower() in {"provider", "cache"}
    )


def _normalized_entry_diagnostics(diagnostics: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(diagnostics, Mapping):
        return {}
    payload: dict[str, Any] = {}
    for key, value in diagnostics.items():
        token = str(key or "").strip()
        if not token:
            continue
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                payload[token] = cleaned
            continue
        if value is None:
            continue
        text = str(value).strip()
        if text:
            payload[token] = text
    return payload


def _requested_state_failure_context(
    *,
    state: Mapping[str, Any] | None,
    request: Mapping[str, Any] | None,
) -> dict[str, str]:
    state_entries = state.get("entries") if isinstance(state, Mapping) else {}
    if not isinstance(state_entries, Mapping) or not isinstance(request, Mapping):
        return {}

    winner_attempted_utc = ""
    winner: dict[str, str] = {}

    def _consider(*, key: str, fingerprint: str) -> None:
        nonlocal winner_attempted_utc, winner
        entry = state_entries.get(key)
        if not isinstance(entry, Mapping):
            return
        if str(entry.get("fingerprint", "")).strip() != str(fingerprint).strip():
            return
        diagnostics = entry.get("diagnostics")
        diagnostics_mapping = diagnostics if isinstance(diagnostics, Mapping) else {}
        failure_code = (
            str(diagnostics_mapping.get("provider_failure_code", "")).strip().lower()
            or str(diagnostics_mapping.get("reason", "")).strip().lower()
        )
        failure_detail = str(diagnostics_mapping.get("provider_failure_detail", "")).strip()
        attempted_model = str(diagnostics_mapping.get("provider_model", "")).strip()
        if not failure_code and not failure_detail:
            return
        attempted_utc = str(entry.get("attempted_utc", "")).strip()
        if attempted_utc < winner_attempted_utc:
            return
        winner_attempted_utc = attempted_utc
        winner = {
            "failure_code": failure_code,
            "failure_detail": failure_detail,
            "previous_model": attempted_model,
        }

    global_entries = request.get("global")
    if isinstance(global_entries, Mapping):
        for window_key, entry in global_entries.items():
            if isinstance(entry, Mapping):
                _consider(
                    key=_candidate_key(window_key=str(window_key).strip()),
                    fingerprint=str(entry.get("fingerprint", "")).strip(),
                )

    scoped_entries = request.get("scoped")
    if isinstance(scoped_entries, Mapping):
        for window_key, entries in scoped_entries.items():
            if not isinstance(entries, Mapping):
                continue
            for scope_id, entry in entries.items():
                if isinstance(entry, Mapping):
                    _consider(
                        key=_candidate_key(window_key=str(window_key).strip(), scope_id=str(scope_id).strip()),
                        fingerprint=str(entry.get("fingerprint", "")).strip(),
                    )
    return winner


def _requested_telemetry_failure_context(
    *,
    repo_root: Path,
    request: Mapping[str, Any] | None,
) -> dict[str, str]:
    if not isinstance(request, Mapping):
        return {}
    request_fingerprints: set[str] = set()

    global_entries = request.get("global")
    if isinstance(global_entries, Mapping):
        for entry in global_entries.values():
            if isinstance(entry, Mapping):
                fingerprint = str(entry.get("fingerprint", "")).strip()
                if fingerprint:
                    request_fingerprints.add(fingerprint)

    scoped_entries = request.get("scoped")
    if isinstance(scoped_entries, Mapping):
        for entries in scoped_entries.values():
            if not isinstance(entries, Mapping):
                continue
            for entry in entries.values():
                if isinstance(entry, Mapping):
                    fingerprint = str(entry.get("fingerprint", "")).strip()
                    if fingerprint:
                        request_fingerprints.add(fingerprint)

    if not request_fingerprints:
        return {}

    telemetry_payload = _load_json(compass_standup_brief_telemetry.telemetry_path(repo_root=repo_root))
    attempts = telemetry_payload.get("attempts")
    if not isinstance(attempts, Sequence):
        return {}

    winner_recorded_utc = ""
    winner: dict[str, str] = {}
    for attempt in attempts:
        if not isinstance(attempt, Mapping):
            continue
        substrate_fingerprints = attempt.get("substrate_fingerprints")
        if not isinstance(substrate_fingerprints, Mapping):
            continue
        attempt_fingerprints = {
            str(value).strip()
            for value in substrate_fingerprints.values()
            if str(value).strip()
        }
        if not request_fingerprints.intersection(attempt_fingerprints):
            continue
        recorded_utc = str(attempt.get("recorded_utc", "")).strip()
        if recorded_utc < winner_recorded_utc:
            continue
        winner_recorded_utc = recorded_utc
        winner = {
            "failure_code": (
                str(attempt.get("provider_code", "")).strip().lower()
                or str(attempt.get("failure_kind", "")).strip().lower()
            ),
            "failure_detail": str(attempt.get("provider_detail", "")).strip(),
            "previous_model": str(attempt.get("model", "")).strip(),
            "previous_reasoning_effort": str(attempt.get("reasoning_effort", "")).strip().lower(),
        }
    return winner


def _cheap_config(
    *,
    repo_root: Path,
    request: Mapping[str, Any] | None = None,
    state: Mapping[str, Any] | None = None,
) -> odylith_reasoning.ReasoningConfig:
    base_config = odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    retry_context = _requested_state_failure_context(state=state, request=request)
    telemetry_context = _requested_telemetry_failure_context(repo_root=repo_root, request=request)
    if not str(retry_context.get("previous_model", "")).strip() and str(
        telemetry_context.get("previous_model", "")
    ).strip():
        retry_context["previous_model"] = str(telemetry_context.get("previous_model", "")).strip()
    if not str(retry_context.get("failure_code", "")).strip() and str(
        telemetry_context.get("failure_code", "")
    ).strip():
        retry_context["failure_code"] = str(telemetry_context.get("failure_code", "")).strip()
    if not str(retry_context.get("failure_detail", "")).strip() and str(
        telemetry_context.get("failure_detail", "")
    ).strip():
        retry_context["failure_detail"] = str(telemetry_context.get("failure_detail", "")).strip()
    profile = odylith_reasoning.cheap_structured_reasoning_profile(
        base_config,
        previous_model=str(retry_context.get("previous_model", "")).strip(),
        failure_code=str(retry_context.get("failure_code", "")).strip(),
        failure_detail=str(retry_context.get("failure_detail", "")).strip(),
    )
    provider = str(profile.provider or base_config.provider).strip()
    updates: dict[str, Any] = {
        "provider": provider,
        "model": str(profile.model or base_config.model).strip(),
    }
    if provider == "codex-cli":
        updates["codex_reasoning_effort"] = str(profile.reasoning_effort or base_config.codex_reasoning_effort).strip()
    elif provider == "claude-cli":
        updates["claude_reasoning_effort"] = str(profile.reasoning_effort or base_config.claude_reasoning_effort).strip()
    return replace(base_config, **updates)


def _provider_for_cheap_config(
    *,
    repo_root: Path,
    config: odylith_reasoning.ReasoningConfig,
) -> odylith_reasoning.ReasoningProvider | None:
    return odylith_reasoning.provider_from_config(
        config,
        repo_root=repo_root,
        require_auto_mode=False,
        allow_implicit_local_provider=True,
    )


def enqueue_request(
    *,
    repo_root: Path,
    generated_utc: str,
    runtime_input_fingerprint: str,
    global_fact_packets: Mapping[str, Mapping[str, Any]],
    global_briefs: Mapping[str, Mapping[str, Any]],
    scoped_fact_packets: Mapping[str, Mapping[str, Mapping[str, Any]]],
    scoped_briefs: Mapping[str, Mapping[str, Mapping[str, Any]]],
    scope_signals: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    state = _load_state(repo_root=repo_root)
    state_entries = dict(state.get("entries", {}))
    payload: dict[str, Any] = {
        "version": _REQUEST_VERSION,
        "generated_utc": str(generated_utc).strip(),
        "runtime_input_fingerprint": str(runtime_input_fingerprint).strip(),
        "global": {},
        "scoped": {},
    }

    for window_key, fact_packet in global_fact_packets.items():
        if not isinstance(fact_packet, Mapping):
            continue
        brief = global_briefs.get(window_key, {}) if isinstance(global_briefs.get(window_key), Mapping) else {}
        if _ready_narrated(brief):
            continue
        if compass_standup_brief_narrator.has_reusable_cached_brief(repo_root=repo_root, fact_packet=fact_packet):
            continue
        fingerprint = compass_standup_brief_narrator.standup_brief_fingerprint(fact_packet=fact_packet)
        key = _candidate_key(window_key=window_key)
        if _terminal_state_matches(state_entries=state_entries, key=key, fingerprint=fingerprint):
            continue
        payload["global"][str(window_key).strip()] = {
            "fingerprint": fingerprint,
            "fact_packet": dict(fact_packet),
        }

    for window_key, packets in scoped_fact_packets.items():
        packet_map = packets if isinstance(packets, Mapping) else {}
        brief_map = scoped_briefs.get(window_key, {}) if isinstance(scoped_briefs.get(window_key), Mapping) else {}
        signal_map = scope_signals.get(window_key, {}) if isinstance(scope_signals.get(window_key), Mapping) else {}
        ranked_candidates: list[tuple[tuple[int, int, int, int, int, int, int, str], str, dict[str, Any]]] = []
        for scope_id, fact_packet in packet_map.items():
            scope_token = str(scope_id).strip()
            if not scope_token or not isinstance(fact_packet, Mapping):
                continue
            brief = brief_map.get(scope_token) if isinstance(brief_map.get(scope_token), Mapping) else {}
            key = _candidate_key(window_key=window_key, scope_id=scope_token)
            state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else None
            signal_entry = signal_map.get(scope_token) if isinstance(signal_map.get(scope_token), Mapping) else {}
            if _ready_narrated(brief):
                continue
            if compass_standup_brief_narrator.has_reusable_cached_brief(repo_root=repo_root, fact_packet=fact_packet):
                continue
            fingerprint = compass_standup_brief_narrator.standup_brief_fingerprint(fact_packet=fact_packet)
            if _terminal_state_matches(state_entries=state_entries, key=key, fingerprint=fingerprint):
                continue
            budget_class = str(signal_entry.get("budget_class", "")).strip().lower()
            if budget_class not in {"fast_simple"} and not (
                _state_entry_is_nonready(state_entry)
                and str(state_entry.get("fingerprint", "")).strip() == fingerprint
            ):
                continue
            ranked_candidates.append(
                (
                    _scope_signal_priority(
                        signal_entry=signal_entry,
                        state_entry=state_entry,
                        fingerprint=fingerprint,
                        scope_id=scope_token,
                    ),
                    scope_token,
                    {
                        "fingerprint": fingerprint,
                        "fact_packet": dict(fact_packet),
                    },
                )
            )
        if ranked_candidates:
            ranked_candidates.sort(
                key=lambda item: (
                    -item[0][0],
                    -item[0][1],
                    -item[0][2],
                    -item[0][3],
                    -item[0][4],
                    -item[0][5],
                    -item[0][6],
                    item[0][7],
                )
            )
            payload["scoped"][str(window_key).strip()] = {
                scope_token: candidate
                for _priority, scope_token, candidate in ranked_candidates[:_MAX_SCOPED_REQUESTS_PER_WINDOW]
            }

    if not payload["global"] and not payload["scoped"]:
        request_file = maintenance_request_path(repo_root=repo_root)
        try:
            request_file.unlink()
        except FileNotFoundError:
            pass
        return {}

    _write_json(
        repo_root=repo_root,
        path=maintenance_request_path(repo_root=repo_root),
        payload=payload,
    )
    return payload


def stamp_request_runtime_input_fingerprint(
    *,
    repo_root: Path,
    runtime_input_fingerprint: str,
) -> None:
    repo_root = Path(repo_root).resolve()
    request_path = maintenance_request_path(repo_root=repo_root)
    payload = _load_json(request_path)
    if not _request_has_entries(payload):
        return
    runtime_fingerprint = str(runtime_input_fingerprint).strip()
    if not runtime_fingerprint:
        return
    payload["runtime_input_fingerprint"] = runtime_fingerprint
    _write_json(repo_root=repo_root, path=request_path, payload=payload)
    state = _load_state(repo_root=repo_root)
    global_failures, scoped_failures = _failure_results_from_state(
        request=payload,
        state_entries=dict(state.get("entries", {})),
    )
    if global_failures or scoped_failures:
        _patch_current_runtime_payload(
            repo_root=repo_root,
            runtime_input_fingerprint=runtime_fingerprint,
            global_results={},
            scoped_results={},
            global_failures=global_failures,
            scoped_failures=scoped_failures,
        )


def maybe_spawn_background(*, repo_root: Path) -> int:
    repo_root = Path(repo_root).resolve()
    request_file = maintenance_request_path(repo_root=repo_root)
    request_payload = _load_json(request_file)
    if not _request_has_entries(request_payload):
        return 0
    state = _load_state(repo_root=repo_root)
    active_pid = int(state.get("active_pid", 0) or 0)
    python_bin = _worker_python_bin()
    live_worker_pids = [
        pid for pid in _maintenance_worker_pids(repo_root=repo_root) if int(pid) != int(os.getpid())
    ]
    if active_pid in live_worker_pids and _worker_matches_current(repo_root=repo_root, state=state, python_bin=python_bin):
        for pid in live_worker_pids:
            if pid != active_pid:
                _terminate_worker(pid)
        return active_pid
    for pid in live_worker_pids:
        _terminate_worker(pid)
    if _pid_alive(active_pid):
        _terminate_worker(active_pid)
    state["active_pid"] = 0
    worker = subprocess.Popen(  # noqa: S603
        [
            python_bin,
            "-m",
            "odylith.runtime.surfaces.compass_standup_brief_maintenance",
            "--repo-root",
            str(repo_root),
        ],
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    state["active_pid"] = int(worker.pid or 0)
    state["worker_epoch"] = _worker_epoch(repo_root=repo_root)
    state["worker_python_bin"] = python_bin
    _write_state(repo_root=repo_root, state=state)
    return int(worker.pid or 0)


def _record_result(
    *,
    state: dict[str, Any],
    window_key: str,
    fingerprint: str,
    status: str,
    scope_id: str = "",
    source: str = "",
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    entries = dict(state.get("entries", {}))
    key = _candidate_key(window_key=window_key, scope_id=scope_id)
    prior_entry = entries.get(key)
    prior_attempts = 0
    if isinstance(prior_entry, Mapping) and str(prior_entry.get("fingerprint", "")).strip() == str(fingerprint).strip():
        prior_attempts = int(prior_entry.get("attempt_count", 0) or 0)
    attempt_count = 1 if str(status).strip().lower() == "ready" else prior_attempts + 1
    payload = {
        "fingerprint": str(fingerprint).strip(),
        "status": str(status).strip().lower(),
        "source": str(source).strip().lower(),
        "attempted_utc": _now_utc_iso(),
        "attempt_count": attempt_count,
    }
    normalized_diagnostics = _normalized_entry_diagnostics(diagnostics)
    if (
        str(normalized_diagnostics.get("reason", "")).strip().lower() == "skipped_not_worth_calling"
        or str(normalized_diagnostics.get("provider_decision", "")).strip().lower() == "skipped_not_worth_calling"
    ):
        payload["status"] = "skipped"
    if normalized_diagnostics:
        payload["diagnostics"] = normalized_diagnostics
    if payload["status"] not in {"ready", "skipped"}:
        retry_at = dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(
            seconds=_retry_backoff_seconds(
                status=payload["status"],
                source=payload["source"],
                attempt_count=attempt_count,
                failure_code=str(normalized_diagnostics.get("provider_failure_code", "")).strip().lower(),
                failure_reason=str(normalized_diagnostics.get("reason", "")).strip().lower(),
            )
        )
        payload["next_retry_utc"] = retry_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entries[key] = payload
    state["entries"] = entries
    return payload


def _diagnostics_from_state_entry(state_entry: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = (
        dict(state_entry.get("diagnostics"))
        if isinstance(state_entry.get("diagnostics"), Mapping)
        else {}
    )
    next_retry_utc = str(state_entry.get("next_retry_utc", "")).strip()
    if next_retry_utc:
        diagnostics["next_retry_utc"] = next_retry_utc
    return diagnostics


def _failure_brief(
    *,
    fingerprint: str,
    generated_utc: str,
    provider: odylith_reasoning.ReasoningProvider | None,
    fallback_reason: str,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if provider is not None:
        return compass_standup_brief_narrator.unavailable_brief_for_provider_failure(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            provider=provider,
            fallback_reason=fallback_reason,
            diagnostics=diagnostics,
        )
    return compass_standup_brief_narrator._unavailable_ready_brief(  # noqa: SLF001
        fingerprint=fingerprint,
        generated_utc=generated_utc,
        reason=fallback_reason,
        diagnostics=diagnostics,
    )


def _request_has_entries(payload: Mapping[str, Any] | None) -> bool:
    def _valid_request_entry(entry: Any) -> bool:
        if not isinstance(entry, Mapping):
            return False
        if not str(entry.get("fingerprint", "")).strip():
            return False
        fact_packet = entry.get("fact_packet")
        return isinstance(fact_packet, Mapping) and bool(fact_packet)

    if not isinstance(payload, Mapping):
        return False
    global_entries = payload.get("global")
    if isinstance(global_entries, Mapping) and any(_valid_request_entry(entry) for entry in global_entries.values()):
        return True
    scoped_entries = payload.get("scoped")
    if not isinstance(scoped_entries, Mapping):
        return False
    for window_entries in scoped_entries.values():
        if isinstance(window_entries, Mapping) and any(_valid_request_entry(entry) for entry in window_entries.values()):
            return True
    return False


def _pending_request_payload(
    *,
    request: Mapping[str, Any],
    state_entries: Mapping[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": str(request.get("version", _REQUEST_VERSION)).strip() or _REQUEST_VERSION,
        "generated_utc": str(request.get("generated_utc", "")).strip(),
        "runtime_input_fingerprint": str(request.get("runtime_input_fingerprint", "")).strip(),
        "global": {},
        "scoped": {},
    }

    global_requests = request.get("global") if isinstance(request.get("global"), Mapping) else {}
    for window_key, entry in global_requests.items():
        if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
            continue
        key = _candidate_key(window_key=str(window_key).strip())
        state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else {}
        if str(state_entry.get("fingerprint", "")).strip() != str(entry.get("fingerprint", "")).strip():
            payload["global"][str(window_key).strip()] = dict(entry)
            continue
        if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
            continue
        payload["global"][str(window_key).strip()] = dict(entry)

    scoped_requests = request.get("scoped") if isinstance(request.get("scoped"), Mapping) else {}
    for window_key, entries in scoped_requests.items():
        if not isinstance(entries, Mapping):
            continue
        retained_window: dict[str, Any] = {}
        for scope_id, entry in entries.items():
            if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
                continue
            scope_token = str(scope_id).strip()
            key = _candidate_key(window_key=str(window_key).strip(), scope_id=scope_token)
            state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else {}
            if str(state_entry.get("fingerprint", "")).strip() != str(entry.get("fingerprint", "")).strip():
                retained_window[scope_token] = dict(entry)
                continue
            if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
                continue
            retained_window[scope_token] = dict(entry)
        if retained_window:
            payload["scoped"][str(window_key).strip()] = retained_window
    return payload


def _pending_request_delay_seconds(
    *,
    request: Mapping[str, Any],
    state_entries: Mapping[str, Any],
) -> float | None:
    if not _request_has_entries(request):
        return None
    now = dt.datetime.now(tz=dt.timezone.utc)
    min_delay: float | None = None

    def _consider_entry(*, key: str, entry: Mapping[str, Any]) -> None:
        nonlocal min_delay
        state_entry = state_entries.get(key) if isinstance(state_entries.get(key), Mapping) else {}
        if str(state_entry.get("fingerprint", "")).strip() != str(entry.get("fingerprint", "")).strip():
            min_delay = 0.0
            return
        if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
            return
        next_retry_dt = compass_standup_brief_narrator._parse_iso_datetime(  # noqa: SLF001
            str(state_entry.get("next_retry_utc", "")).strip()
        )
        if next_retry_dt is None:
            min_delay = 0.0
            return
        delay_seconds = max(0.0, (next_retry_dt - now).total_seconds())
        if min_delay is None or delay_seconds < min_delay:
            min_delay = delay_seconds

    global_requests = request.get("global") if isinstance(request.get("global"), Mapping) else {}
    for window_key, entry in global_requests.items():
        if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
            continue
        _consider_entry(key=_candidate_key(window_key=str(window_key).strip()), entry=entry)
        if min_delay == 0.0:
            return 0.0

    scoped_requests = request.get("scoped") if isinstance(request.get("scoped"), Mapping) else {}
    for window_key, entries in scoped_requests.items():
        if not isinstance(entries, Mapping):
            continue
        for scope_id, entry in entries.items():
            if not isinstance(entry, Mapping) or not str(entry.get("fingerprint", "")).strip():
                continue
            _consider_entry(
                key=_candidate_key(window_key=str(window_key).strip(), scope_id=str(scope_id).strip()),
                entry=entry,
            )
            if min_delay == 0.0:
                return 0.0
    return min_delay


def _failure_results_from_state(
    *,
    request: Mapping[str, Any],
    state_entries: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    generated_utc = str(request.get("generated_utc", "")).strip() or _now_utc_iso()
    global_failures: dict[str, dict[str, Any]] = {}
    scoped_failures: dict[str, dict[str, dict[str, Any]]] = {}

    global_requests = request.get("global") if isinstance(request.get("global"), Mapping) else {}
    for window_key, entry in global_requests.items():
        if not isinstance(entry, Mapping):
            continue
        window_token = str(window_key).strip()
        fingerprint = str(entry.get("fingerprint", "")).strip()
        if not window_token or not fingerprint:
            continue
        state_entry = state_entries.get(_candidate_key(window_key=window_token))
        if not isinstance(state_entry, Mapping):
            continue
        if str(state_entry.get("fingerprint", "")).strip() != fingerprint:
            continue
        if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
            continue
        diagnostics = _diagnostics_from_state_entry(state_entry)
        global_failures[window_token] = _failure_brief(
            fingerprint=fingerprint,
            generated_utc=generated_utc,
            provider=None,
            fallback_reason=str(diagnostics.get("reason", "")).strip().lower() or str(state_entry.get("status", "")).strip().lower() or "brief_unavailable",
            diagnostics=diagnostics,
        )

    scoped_requests = request.get("scoped") if isinstance(request.get("scoped"), Mapping) else {}
    for window_key, entries in scoped_requests.items():
        if not isinstance(entries, Mapping):
            continue
        window_token = str(window_key).strip()
        failed_window: dict[str, dict[str, Any]] = {}
        for scope_id, entry in entries.items():
            if not isinstance(entry, Mapping):
                continue
            scope_token = str(scope_id).strip()
            fingerprint = str(entry.get("fingerprint", "")).strip()
            if not window_token or not scope_token or not fingerprint:
                continue
            state_entry = state_entries.get(_candidate_key(window_key=window_token, scope_id=scope_token))
            if not isinstance(state_entry, Mapping):
                continue
            if str(state_entry.get("fingerprint", "")).strip() != fingerprint:
                continue
            if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
                continue
            diagnostics = _diagnostics_from_state_entry(state_entry)
            failed_window[scope_token] = _failure_brief(
                fingerprint=fingerprint,
                generated_utc=generated_utc,
                provider=None,
                fallback_reason=str(diagnostics.get("reason", "")).strip().lower() or str(state_entry.get("status", "")).strip().lower() or "brief_unavailable",
                diagnostics=diagnostics,
            )
        if failed_window:
            scoped_failures[window_token] = failed_window

    return global_failures, scoped_failures


def failure_brief_for_fact_packet(
    *,
    repo_root: Path,
    window_key: str,
    fact_packet: Mapping[str, Any],
    generated_utc: str,
    scope_id: str = "",
) -> dict[str, Any] | None:
    if not isinstance(fact_packet, Mapping):
        return None
    repo_root = Path(repo_root).resolve()
    fingerprint = compass_standup_brief_narrator.standup_brief_fingerprint(fact_packet=fact_packet)
    state = _load_state(repo_root=repo_root)
    state_entry = state.get("entries", {}).get(
        _candidate_key(window_key=str(window_key).strip(), scope_id=str(scope_id).strip())
    )
    if not isinstance(state_entry, Mapping):
        return None
    if str(state_entry.get("fingerprint", "")).strip() != fingerprint:
        return None
    if str(state_entry.get("status", "")).strip().lower() in {"ready", "skipped"}:
        return None
    diagnostics = _diagnostics_from_state_entry(state_entry)
    return _failure_brief(
        fingerprint=fingerprint,
        generated_utc=str(generated_utc).strip() or _now_utc_iso(),
        provider=None,
        fallback_reason=(
            str(diagnostics.get("reason", "")).strip().lower()
            or str(state_entry.get("status", "")).strip().lower()
            or "brief_unavailable"
        ),
        diagnostics=diagnostics,
    )


def _patch_current_runtime_payload(
    *,
    repo_root: Path,
    runtime_input_fingerprint: str,
    global_results: Mapping[str, Mapping[str, Any]],
    scoped_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
    global_failures: Mapping[str, Mapping[str, Any]] | None = None,
    scoped_failures: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> bool:
    current_json_path = (repo_root / _RUNTIME_CURRENT_JSON).resolve()
    current_js_path = (repo_root / _RUNTIME_CURRENT_JS).resolve()
    payload = _load_json(current_json_path)
    runtime_contract = payload.get("runtime_contract")
    if not isinstance(runtime_contract, Mapping):
        return False
    if str(runtime_contract.get("input_fingerprint", "")).strip() != str(runtime_input_fingerprint).strip():
        return False
    changed = False
    standup_brief = payload.get("standup_brief")
    digest = payload.get("digest")
    standup_brief_scoped = payload.get("standup_brief_scoped")
    digest_scoped = payload.get("digest_scoped")
    if not isinstance(standup_brief, Mapping):
        standup_brief = {}
    if not isinstance(digest, Mapping):
        digest = {}
    if not isinstance(standup_brief_scoped, Mapping):
        standup_brief_scoped = {}
    if not isinstance(digest_scoped, Mapping):
        digest_scoped = {}
    mutable_standup_brief = {str(key): value for key, value in standup_brief.items()}
    mutable_digest = {str(key): value for key, value in digest.items()}
    mutable_standup_brief_scoped = {
        str(key): dict(value) if isinstance(value, Mapping) else {}
        for key, value in standup_brief_scoped.items()
    }
    mutable_digest_scoped = {
        str(key): dict(value) if isinstance(value, Mapping) else {}
        for key, value in digest_scoped.items()
    }
    for window_key, brief in global_results.items():
        if not isinstance(brief, Mapping):
            continue
        mutable_standup_brief[str(window_key).strip()] = dict(brief)
        mutable_digest[str(window_key).strip()] = compass_standup_brief_narrator.brief_to_digest_lines(brief)
        changed = True
    for window_key, brief in (global_failures or {}).items():
        if not isinstance(brief, Mapping):
            continue
        window_token = str(window_key).strip()
        mutable_standup_brief[window_token] = dict(brief)
        mutable_digest[window_token] = compass_standup_brief_narrator.brief_to_digest_lines(brief)
        changed = True
    for window_key, window_results in scoped_results.items():
        if not isinstance(window_results, Mapping):
            continue
        scoped_window = dict(mutable_standup_brief_scoped.get(str(window_key).strip(), {}))
        digest_window = dict(mutable_digest_scoped.get(str(window_key).strip(), {}))
        for scope_id, brief in window_results.items():
            if not isinstance(brief, Mapping):
                continue
            scope_token = str(scope_id).strip()
            if not scope_token:
                continue
            scoped_window[scope_token] = dict(brief)
            digest_window[scope_token] = compass_standup_brief_narrator.brief_to_digest_lines(brief)
            changed = True
        mutable_standup_brief_scoped[str(window_key).strip()] = scoped_window
        mutable_digest_scoped[str(window_key).strip()] = digest_window
    for window_key, window_failures in (scoped_failures or {}).items():
        if not isinstance(window_failures, Mapping):
            continue
        window_token = str(window_key).strip()
        scoped_window = dict(mutable_standup_brief_scoped.get(window_token, {}))
        digest_window = dict(mutable_digest_scoped.get(window_token, {}))
        for scope_id, brief in window_failures.items():
            if not isinstance(brief, Mapping):
                continue
            scope_token = str(scope_id).strip()
            if not scope_token:
                continue
            scoped_window[scope_token] = dict(brief)
            digest_window[scope_token] = compass_standup_brief_narrator.brief_to_digest_lines(brief)
            changed = True
        mutable_standup_brief_scoped[window_token] = scoped_window
        mutable_digest_scoped[window_token] = digest_window
    if not changed:
        return False
    payload["standup_brief"] = mutable_standup_brief
    payload["digest"] = mutable_digest
    payload["standup_brief_scoped"] = mutable_standup_brief_scoped
    payload["digest_scoped"] = mutable_digest_scoped
    _write_json(repo_root=repo_root, path=current_json_path, payload=payload)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_js_path,
        content="window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        lock_key=str(current_js_path),
    )
    return True


def run_pending_request(
    *,
    repo_root: Path,
    emit_output: bool = False,
    keep_active_pid: bool = False,
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    request_path = maintenance_request_path(repo_root=repo_root)
    request = _load_json(request_path)
    state = _load_state(repo_root=repo_root)
    state["active_pid"] = int(os.getpid())
    state["worker_epoch"] = _worker_epoch(repo_root=repo_root)
    state["worker_python_bin"] = _worker_python_bin()
    _write_state(repo_root=repo_root, state=state)

    global_results: dict[str, dict[str, Any]] = {}
    global_failure_results: dict[str, dict[str, Any]] = {}
    scoped_results: dict[str, dict[str, dict[str, Any]]] = {}
    scoped_failure_results: dict[str, dict[str, dict[str, Any]]] = {}
    warmed = 0
    failed = 0
    pending_request: dict[str, Any] = {}
    pending_delay_seconds: float | None = None

    try:
        if not _request_has_entries(request):
            state["active_pid"] = int(os.getpid()) if keep_active_pid else 0
            state["last_run_utc"] = _now_utc_iso()
            _write_state(repo_root=repo_root, state=state)
            return {
                "warmed": 0,
                "failed": 0,
                "patched_current_runtime": False,
                "request_retained": False,
                "next_retry_utc": "",
                "next_retry_delay_seconds": None,
            }

        cheap_config = _cheap_config(repo_root=repo_root, request=request, state=state)
        provider = _provider_for_cheap_config(repo_root=repo_root, config=cheap_config)

        global_requests = request.get("global", {}) if isinstance(request.get("global"), Mapping) else {}
        scoped_requests = request.get("scoped", {}) if isinstance(request.get("scoped"), Mapping) else {}

        if provider is None:
            for window_key, entry in global_requests.items():
                if not isinstance(entry, Mapping):
                    continue
                recorded = _record_result(
                    state=state,
                    window_key=str(window_key).strip(),
                    fingerprint=str(entry.get("fingerprint", "")).strip(),
                    status="provider_unavailable",
                    source="none",
                    diagnostics={"provider_failure_code": "provider_unavailable"},
                )
                global_failure_results[str(window_key).strip()] = _failure_brief(
                    fingerprint=str(entry.get("fingerprint", "")).strip(),
                    generated_utc=str(request.get("generated_utc", "")).strip() or _now_utc_iso(),
                    provider=None,
                    fallback_reason="provider_unavailable",
                    diagnostics=_diagnostics_from_state_entry(recorded),
                )
                failed += 1
            for window_key, entries in scoped_requests.items():
                if not isinstance(entries, Mapping):
                    continue
                failed_window: dict[str, dict[str, Any]] = {}
                for scope_id, entry in entries.items():
                    if not isinstance(entry, Mapping):
                        continue
                    recorded = _record_result(
                        state=state,
                        window_key=str(window_key).strip(),
                        scope_id=str(scope_id).strip(),
                        fingerprint=str(entry.get("fingerprint", "")).strip(),
                        status="provider_unavailable",
                        source="none",
                        diagnostics={"provider_failure_code": "provider_unavailable"},
                    )
                    failed_window[str(scope_id).strip()] = _failure_brief(
                        fingerprint=str(entry.get("fingerprint", "")).strip(),
                        generated_utc=str(request.get("generated_utc", "")).strip() or _now_utc_iso(),
                        provider=None,
                        fallback_reason="provider_unavailable",
                        diagnostics=_diagnostics_from_state_entry(recorded),
                    )
                    failed += 1
                if failed_window:
                    scoped_failure_results[str(window_key).strip()] = failed_window
        else:
            generated_utc = str(request.get("generated_utc", "")).strip() or _now_utc_iso()
            global_packets = {
                str(window_key).strip(): dict(entry.get("fact_packet", {}))
                for window_key, entry in global_requests.items()
                if str(window_key).strip() and isinstance(entry, Mapping) and isinstance(entry.get("fact_packet"), Mapping)
            }
            scoped_packets = {
                str(window_key).strip(): {
                    str(scope_id).strip(): dict(entry.get("fact_packet", {}))
                    for scope_id, entry in entries.items()
                    if str(scope_id).strip() and isinstance(entry, Mapping) and isinstance(entry.get("fact_packet"), Mapping)
                }
                for window_key, entries in scoped_requests.items()
                if isinstance(entries, Mapping)
            }
            bundle_results = compass_standup_brief_batch.build_brief_bundle(
                repo_root=repo_root,
                global_fact_packets_by_window=global_packets,
                scoped_fact_packets_by_window=scoped_packets,
                generated_utc=generated_utc,
                runtime_packet_fingerprint=str(request.get("runtime_input_fingerprint", "")).strip(),
                config=cheap_config,
                provider=provider,
            )
            global_batch_results = (
                dict(bundle_results.get("global", {}))
                if isinstance(bundle_results.get("global"), Mapping)
                else {}
            )
            scoped_batch_results = (
                {
                    str(window_key).strip(): dict(window_results)
                    for window_key, window_results in bundle_results.get("scoped", {}).items()
                    if str(window_key).strip() and isinstance(window_results, Mapping)
                }
                if isinstance(bundle_results.get("scoped"), Mapping)
                else {}
            )
            for window_key, entry in global_requests.items():
                if not isinstance(entry, Mapping):
                    continue
                window_token = str(window_key).strip()
                fingerprint = str(entry.get("fingerprint", "")).strip()
                brief = global_batch_results.get(window_token, {})
                source = str(brief.get("source", "")).strip().lower()
                if str(brief.get("status", "")).strip().lower() == "ready" and source in {"provider", "cache"}:
                    global_results[window_token] = dict(brief)
                    _record_result(
                        state=state,
                        window_key=window_token,
                        fingerprint=fingerprint,
                        status="ready",
                        source=source,
                    )
                    warmed += 1
                else:
                    diagnostics = (
                        brief.get("diagnostics")
                        if isinstance(brief, Mapping) and isinstance(brief.get("diagnostics"), Mapping)
                        else {}
                    )
                    failure_reason = (
                        str(diagnostics.get("reason", "")).strip().lower()
                        or str(diagnostics.get("provider_decision", "")).strip().lower()
                        or "invalid_batch"
                    )
                    is_skipped = failure_reason == "skipped_not_worth_calling"
                    failed_brief = _failure_brief(
                        fingerprint=fingerprint,
                        generated_utc=generated_utc,
                        provider=provider,
                        fallback_reason=failure_reason,
                        diagnostics=diagnostics,
                    )
                    recorded = _record_result(
                        state=state,
                        window_key=window_token,
                        fingerprint=fingerprint,
                        status="skipped" if is_skipped else "failed",
                        source=source or str(failed_brief.get("source", "")).strip().lower(),
                        diagnostics=failed_brief.get("diagnostics"),
                    )
                    failed_brief = (
                        dict(brief)
                        if is_skipped and isinstance(brief, Mapping)
                        else _failure_brief(
                            fingerprint=fingerprint,
                            generated_utc=generated_utc,
                            provider=provider,
                            fallback_reason=(
                                str(_diagnostics_from_state_entry(recorded).get("reason", "")).strip().lower()
                                or failure_reason
                            ),
                            diagnostics=_diagnostics_from_state_entry(recorded),
                        )
                    )
                    global_failure_results[window_token] = failed_brief
                    if not is_skipped:
                        failed += 1

            for window_key, entries in scoped_requests.items():
                if not isinstance(entries, Mapping) or not entries:
                    continue
                batch_results = (
                    scoped_batch_results.get(str(window_key).strip(), {})
                    if isinstance(scoped_batch_results.get(str(window_key).strip(), {}), Mapping)
                    else {}
                )
                ready_window: dict[str, dict[str, Any]] = {}
                failed_window: dict[str, dict[str, Any]] = {}
                for scope_id, entry in entries.items():
                    if not isinstance(entry, Mapping):
                        continue
                    scope_token = str(scope_id).strip()
                    brief = batch_results.get(scope_token, {})
                    source = str(brief.get("source", "")).strip().lower()
                    fingerprint = str(entry.get("fingerprint", "")).strip()
                    if str(brief.get("status", "")).strip().lower() == "ready" and source in {"provider", "cache"}:
                        ready_window[scope_token] = dict(brief)
                        _record_result(
                            state=state,
                            window_key=str(window_key).strip(),
                            scope_id=scope_token,
                            fingerprint=fingerprint,
                            status="ready",
                            source=source,
                        )
                        warmed += 1
                    else:
                        diagnostics = (
                            brief.get("diagnostics")
                            if isinstance(brief, Mapping) and isinstance(brief.get("diagnostics"), Mapping)
                            else {}
                        )
                        failure_reason = (
                            str(diagnostics.get("reason", "")).strip().lower()
                            or str(diagnostics.get("provider_decision", "")).strip().lower()
                            or "invalid_batch"
                        )
                        is_skipped = failure_reason == "skipped_not_worth_calling"
                        failed_brief = _failure_brief(
                            fingerprint=fingerprint,
                            generated_utc=generated_utc,
                            provider=provider,
                            fallback_reason=failure_reason,
                            diagnostics=diagnostics,
                        )
                        recorded = _record_result(
                            state=state,
                            window_key=str(window_key).strip(),
                            scope_id=scope_token,
                            fingerprint=fingerprint,
                            status="skipped" if is_skipped else "failed",
                            source=source or str(failed_brief.get("source", "")).strip().lower(),
                            diagnostics=failed_brief.get("diagnostics"),
                        )
                        failed_brief = (
                            dict(brief)
                            if is_skipped and isinstance(brief, Mapping)
                            else _failure_brief(
                                fingerprint=fingerprint,
                                generated_utc=generated_utc,
                                provider=provider,
                                fallback_reason=(
                                    str(_diagnostics_from_state_entry(recorded).get("reason", "")).strip().lower()
                                    or failure_reason
                                ),
                                diagnostics=_diagnostics_from_state_entry(recorded),
                            )
                        )
                        failed_window[scope_token] = failed_brief
                        if not is_skipped:
                            failed += 1
                if ready_window:
                    scoped_results[str(window_key).strip()] = ready_window
                if failed_window:
                    scoped_failure_results[str(window_key).strip()] = failed_window

        patched_current_runtime = _patch_current_runtime_payload(
            repo_root=repo_root,
            runtime_input_fingerprint=str(request.get("runtime_input_fingerprint", "")).strip(),
            global_results=global_results,
            scoped_results=scoped_results,
            global_failures=global_failure_results,
            scoped_failures=scoped_failure_results,
        )
        pending_request = _pending_request_payload(
            request=request,
            state_entries=dict(state.get("entries", {})),
        )
        latest_request_payload = _load_json(request_path)
        latest_runtime_input_fingerprint = str(latest_request_payload.get("runtime_input_fingerprint", "")).strip()
        if latest_runtime_input_fingerprint and not str(pending_request.get("runtime_input_fingerprint", "")).strip():
            pending_request["runtime_input_fingerprint"] = latest_runtime_input_fingerprint
        pending_delay_seconds = _pending_request_delay_seconds(
            request=pending_request,
            state_entries=dict(state.get("entries", {})),
        )
        if _request_has_entries(pending_request):
            _write_json(
                repo_root=repo_root,
                path=request_path,
                payload=pending_request,
            )
    finally:
        retained_request = _request_has_entries(pending_request)
        state["active_pid"] = int(os.getpid()) if keep_active_pid and retained_request else 0
        state["last_run_utc"] = _now_utc_iso()
        _write_state(repo_root=repo_root, state=state)
        if not retained_request:
            try:
                request_path.unlink()
            except FileNotFoundError:
                pass

    next_retry_utc = ""
    if pending_delay_seconds is not None and _request_has_entries(pending_request):
        next_retry_dt = dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(seconds=pending_delay_seconds)
        next_retry_utc = next_retry_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    result = {
        "warmed": warmed,
        "failed": failed,
        "patched_current_runtime": patched_current_runtime,
        "globals": sorted(global_results),
        "scoped": {window: sorted(entries) for window, entries in scoped_results.items()},
        "request_retained": _request_has_entries(pending_request),
        "next_retry_utc": next_retry_utc,
        "next_retry_delay_seconds": pending_delay_seconds,
    }
    if emit_output:
        print("compass standup maintenance")
        print(f"- warmed: {warmed}")
        print(f"- failed: {failed}")
        print(f"- patched_current_runtime: {'yes' if patched_current_runtime else 'no'}")
        print(f"- request_retained: {'yes' if result['request_retained'] else 'no'}")
        if result["next_retry_utc"]:
            print(f"- next_retry_utc: {result['next_retry_utc']}")
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    repo_root = Path(".").resolve()
    emit_output = False
    idx = 0
    while idx < len(args):
        token = str(args[idx]).strip()
        if token == "--repo-root" and idx + 1 < len(args):
            repo_root = Path(args[idx + 1]).expanduser().resolve()
            idx += 2
            continue
        if token == "--emit-output":
            emit_output = True
            idx += 1
            continue
        idx += 1
    while True:
        request = _load_json(maintenance_request_path(repo_root=repo_root))
        if not _request_has_entries(request):
            state = _load_state(repo_root=repo_root)
            state["active_pid"] = 0
            state["last_run_utc"] = _now_utc_iso()
            _write_state(repo_root=repo_root, state=state)
            break
        state = _load_state(repo_root=repo_root)
        state["active_pid"] = int(os.getpid())
        _write_state(repo_root=repo_root, state=state)
        delay_seconds = _pending_request_delay_seconds(
            request=request,
            state_entries=dict(state.get("entries", {})),
        )
        if delay_seconds is not None and delay_seconds > 0:
            time.sleep(min(delay_seconds, float(_RETRY_POLL_INTERVAL_SECONDS)))
            continue
        result = run_pending_request(repo_root=repo_root, emit_output=emit_output, keep_active_pid=True)
        if not result.get("request_retained"):
            break
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
