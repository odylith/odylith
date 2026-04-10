"""Maintained narrated-cache warming for Compass standup briefs.

This module keeps refresh-time Compass cheap by moving scoped/global narrated
cache warming into a deduped sidecar lane. Refresh writes a local-only request
containing active high-signal fact packets, then a cheap provider-neutral
worker warms only new fingerprints and patches the current runtime snapshot if
it still matches the same input fingerprint.
"""

from __future__ import annotations

from dataclasses import replace
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from typing import Mapping

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance.delivery import scope_signal_ladder
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_batch
from odylith.runtime.surfaces import compass_standup_brief_narrator

_REQUEST_VERSION = "v1"
_STATE_VERSION = "v1"
_REQUEST_PATH = ".odylith/compass/standup-brief-maintenance-request.v1.json"
_STATE_PATH = ".odylith/compass/standup-brief-maintenance-state.v1.json"
_TERMINAL_STATUSES = frozenset({"ready", "failed", "provider_unavailable"})
_RUNTIME_CURRENT_JSON = "odylith/compass/runtime/current.v1.json"
_RUNTIME_CURRENT_JS = "odylith/compass/runtime/current.v1.js"


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
    return str(entry.get("status", "")).strip().lower() in _TERMINAL_STATUSES


def _scoped_candidate_allowed(*, signal: Mapping[str, Any] | None) -> bool:
    return scope_signal_ladder.scope_signal_rank(signal or {}) >= 3 and scope_signal_ladder.budget_class_allows_reasoning(
        str((signal or {}).get("budget_class", "")).strip()
    )


def _ready_narrated(brief: Mapping[str, Any] | None) -> bool:
    return (
        isinstance(brief, Mapping)
        and str(brief.get("status", "")).strip().lower() == "ready"
        and str(brief.get("source", "")).strip().lower() in {"provider", "cache"}
    )


def _cheap_config(*, repo_root: Path) -> odylith_reasoning.ReasoningConfig:
    base_config = odylith_reasoning.reasoning_config_from_env(repo_root=repo_root)
    profile = odylith_reasoning.cheap_structured_reasoning_profile(base_config)
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
        window_candidates: dict[str, Any] = {}
        for scope_id, fact_packet in packet_map.items():
            scope_token = str(scope_id).strip()
            if not scope_token or not isinstance(fact_packet, Mapping):
                continue
            signal = signal_map.get(scope_token) if isinstance(signal_map.get(scope_token), Mapping) else {}
            if not _scoped_candidate_allowed(signal=signal):
                continue
            brief = brief_map.get(scope_token) if isinstance(brief_map.get(scope_token), Mapping) else {}
            if _ready_narrated(brief):
                continue
            if compass_standup_brief_narrator.has_reusable_cached_brief(repo_root=repo_root, fact_packet=fact_packet):
                continue
            fingerprint = compass_standup_brief_narrator.standup_brief_fingerprint(fact_packet=fact_packet)
            key = _candidate_key(window_key=window_key, scope_id=scope_token)
            if _terminal_state_matches(state_entries=state_entries, key=key, fingerprint=fingerprint):
                continue
            window_candidates[scope_token] = {
                "fingerprint": fingerprint,
                "fact_packet": dict(fact_packet),
                "scope_signal": dict(signal),
            }
        if window_candidates:
            payload["scoped"][str(window_key).strip()] = window_candidates

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
    if not payload:
        return
    payload["runtime_input_fingerprint"] = str(runtime_input_fingerprint).strip()
    _write_json(repo_root=repo_root, path=request_path, payload=payload)


def maybe_spawn_background(*, repo_root: Path) -> int:
    repo_root = Path(repo_root).resolve()
    request_file = maintenance_request_path(repo_root=repo_root)
    request_payload = _load_json(request_file)
    if not request_payload:
        return 0
    state = _load_state(repo_root=repo_root)
    active_pid = int(state.get("active_pid", 0) or 0)
    if _pid_alive(active_pid):
        return active_pid
    python_bin = str(Path(sys.executable).resolve()) if str(sys.executable).strip() else "python3"
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
) -> None:
    entries = dict(state.get("entries", {}))
    key = _candidate_key(window_key=window_key, scope_id=scope_id)
    entries[key] = {
        "fingerprint": str(fingerprint).strip(),
        "status": str(status).strip().lower(),
        "source": str(source).strip().lower(),
        "attempted_utc": _now_utc_iso(),
    }
    state["entries"] = entries


def _patch_current_runtime_payload(
    *,
    repo_root: Path,
    runtime_input_fingerprint: str,
    global_results: Mapping[str, Mapping[str, Any]],
    scoped_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
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
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    request_path = maintenance_request_path(repo_root=repo_root)
    request = _load_json(request_path)
    state = _load_state(repo_root=repo_root)
    state["active_pid"] = int(os.getpid())
    _write_state(repo_root=repo_root, state=state)

    global_results: dict[str, dict[str, Any]] = {}
    scoped_results: dict[str, dict[str, dict[str, Any]]] = {}
    warmed = 0
    failed = 0

    try:
        if not request:
            state["active_pid"] = 0
            state["last_run_utc"] = _now_utc_iso()
            _write_state(repo_root=repo_root, state=state)
            return {"warmed": 0, "failed": 0, "patched_current_runtime": False}

        cheap_config = _cheap_config(repo_root=repo_root)
        provider = _provider_for_cheap_config(repo_root=repo_root, config=cheap_config)

        global_requests = request.get("global", {}) if isinstance(request.get("global"), Mapping) else {}
        scoped_requests = request.get("scoped", {}) if isinstance(request.get("scoped"), Mapping) else {}

        if provider is None:
            for window_key, entry in global_requests.items():
                if not isinstance(entry, Mapping):
                    continue
                _record_result(
                    state=state,
                    window_key=str(window_key).strip(),
                    fingerprint=str(entry.get("fingerprint", "")).strip(),
                    status="provider_unavailable",
                    source="none",
                )
                failed += 1
            for window_key, entries in scoped_requests.items():
                if not isinstance(entries, Mapping):
                    continue
                for scope_id, entry in entries.items():
                    if not isinstance(entry, Mapping):
                        continue
                    _record_result(
                        state=state,
                        window_key=str(window_key).strip(),
                        scope_id=str(scope_id).strip(),
                        fingerprint=str(entry.get("fingerprint", "")).strip(),
                        status="provider_unavailable",
                        source="none",
                    )
                    failed += 1
        else:
            for window_key, entry in global_requests.items():
                if not isinstance(entry, Mapping):
                    continue
                fact_packet = entry.get("fact_packet")
                fingerprint = str(entry.get("fingerprint", "")).strip()
                if not isinstance(fact_packet, Mapping):
                    _record_result(state=state, window_key=str(window_key).strip(), fingerprint=fingerprint, status="failed")
                    failed += 1
                    continue
                brief = compass_standup_brief_narrator.build_standup_brief(
                    repo_root=repo_root,
                    fact_packet=fact_packet,
                    generated_utc=str(request.get("generated_utc", "")).strip() or _now_utc_iso(),
                    config=cheap_config,
                    provider=provider,
                    allow_provider=True,
                    prefer_provider=True,
                    allow_cache_recovery=True,
                    allow_legacy_cache_recovery=False,
                    allow_deterministic_fallback=False,
                    allow_composed_fallback=False,
                )
                source = str(brief.get("source", "")).strip().lower()
                if str(brief.get("status", "")).strip().lower() == "ready" and source in {"provider", "cache"}:
                    global_results[str(window_key).strip()] = dict(brief)
                    _record_result(
                        state=state,
                        window_key=str(window_key).strip(),
                        fingerprint=fingerprint,
                        status="ready",
                        source=source,
                    )
                    warmed += 1
                else:
                    _record_result(state=state, window_key=str(window_key).strip(), fingerprint=fingerprint, status="failed", source=source)
                    failed += 1

            for window_key, entries in scoped_requests.items():
                if not isinstance(entries, Mapping) or not entries:
                    continue
                packets = {
                    str(scope_id).strip(): dict(entry.get("fact_packet", {}))
                    for scope_id, entry in entries.items()
                    if str(scope_id).strip() and isinstance(entry, Mapping) and isinstance(entry.get("fact_packet"), Mapping)
                }
                batch_results = compass_standup_brief_batch.build_scoped_briefs(
                    repo_root=repo_root,
                    fact_packets_by_scope=packets,
                    generated_utc=str(request.get("generated_utc", "")).strip() or _now_utc_iso(),
                    config=cheap_config,
                    provider=provider,
                )
                ready_window: dict[str, dict[str, Any]] = {}
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
                        _record_result(
                            state=state,
                            window_key=str(window_key).strip(),
                            scope_id=scope_token,
                            fingerprint=fingerprint,
                            status="failed",
                            source=source,
                        )
                        failed += 1
                if ready_window:
                    scoped_results[str(window_key).strip()] = ready_window

        patched_current_runtime = _patch_current_runtime_payload(
            repo_root=repo_root,
            runtime_input_fingerprint=str(request.get("runtime_input_fingerprint", "")).strip(),
            global_results=global_results,
            scoped_results=scoped_results,
        )
    finally:
        state["active_pid"] = 0
        state["last_run_utc"] = _now_utc_iso()
        _write_state(repo_root=repo_root, state=state)
        try:
            request_path.unlink()
        except FileNotFoundError:
            pass

    result = {
        "warmed": warmed,
        "failed": failed,
        "patched_current_runtime": patched_current_runtime,
        "globals": sorted(global_results),
        "scoped": {window: sorted(entries) for window, entries in scoped_results.items()},
    }
    if emit_output:
        print("compass standup maintenance")
        print(f"- warmed: {warmed}")
        print(f"- failed: {failed}")
        print(f"- patched_current_runtime: {'yes' if patched_current_runtime else 'no'}")
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
    run_pending_request(repo_root=repo_root, emit_output=emit_output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
