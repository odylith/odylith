"""Render Compass executive dashboard assets.

Compass is an executive steering surface layered on top of existing backlog/odylith/technical-plans/
mermaid traceability contracts. The facade in this module preserves the original
CLI/import surface while delegating the implementation to extracted Compass
support modules.
"""

from __future__ import annotations

import argparse
import datetime as dt
from importlib import import_module
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import derivation_provenance
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine.surface_projection_fingerprint import default_surface_projection_input_fingerprint
from odylith.runtime.surfaces import compass_refresh_contract
from odylith.runtime.surfaces import compass_standup_brief_maintenance
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_standup_brief_voice_validation
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import source_bundle_mirror

DEFAULT_HISTORY_RETENTION_DAYS = 15
_DEFAULT_ACTIVE_WINDOW_MINUTES = 15
_COMPASS_TZ = ZoneInfo("America/Los_Angeles")
_RUNTIME_CONTRACT_VERSION = "v1"
_DEFAULT_REFRESH_PROFILE = compass_refresh_contract.DEFAULT_REFRESH_PROFILE
_EXPORT_MODULES = (
    "odylith.runtime.surfaces.compass_dashboard_base",
    "odylith.runtime.surfaces.compass_dashboard_runtime",
)
CompassProgressCallback = Callable[[str, Mapping[str, Any] | None], None]


def _resolve(repo_root: Path, value: str) -> Path:
    token = str(value or "").strip()
    path = Path(token)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _as_href(output_path: Path, target: Path) -> str:
    rel = os.path.relpath(str(target), start=str(output_path.parent))
    return Path(rel).as_posix()


def _file_version_token(path: Path) -> str:
    if not path.exists():
        return ""
    return str(path.stat().st_mtime_ns)


def _versioned_href(*, output_path: Path, target: Path) -> str:
    href = _as_href(output_path, target)
    return dashboard_surface_bundle.append_query_param(
        href=href,
        name="v",
        value=_file_version_token(target),
    )


def _load_runtime_impl():
    return import_module("odylith.runtime.surfaces.compass_dashboard_runtime")


def _remove_empty_dirs(path: Path, *, stop_at: Path) -> None:
    current = path
    stop = stop_at.resolve()
    while current.exists() and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            return
        if current.resolve() == stop:
            return
        current = current.parent


def _sync_runtime_bundle_mirror(*, repo_root: Path, runtime_paths: tuple[Path, Path, Path, Path, Path]) -> None:
    """Keep local Compass runtime state out of the shipped install bundle."""
    if not source_bundle_mirror.source_bundle_root(repo_root=repo_root).is_dir():
        return
    current_json_path = runtime_paths[0]
    mirror_runtime_dir = source_bundle_mirror.bundle_mirror_dir(
        repo_root=repo_root,
        live_dir=current_json_path.parent,
    )
    for name in (
        "agent-stream.v1.jsonl",
        "codex-stream.v1.jsonl",
        "current.v1.js",
        "current.v1.json",
        "refresh-state.v1.json",
    ):
        stale_path = mirror_runtime_dir / name
        if stale_path.is_file():
            stale_path.unlink()
    history_dir = mirror_runtime_dir / "history"
    if history_dir.is_dir():
        for stale_path in sorted(history_dir.rglob("*"), reverse=True):
            if stale_path.is_file():
                stale_path.unlink()
            elif stale_path.is_dir():
                _remove_empty_dirs(stale_path, stop_at=history_dir)
        _remove_empty_dirs(history_dir, stop_at=mirror_runtime_dir)


def _normalize_refresh_profile(value: str) -> str:
    return compass_refresh_contract.normalize_refresh_profile(value, default=_DEFAULT_REFRESH_PROFILE)


def _now_utc_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _emit_progress(
    progress_callback: CompassProgressCallback | None,
    *,
    stage: str,
    detail: Mapping[str, Any] | None = None,
) -> None:
    if progress_callback is None:
        return
    progress_callback(str(stage).strip(), dict(detail or {}))


def _runtime_daemon_available(*, repo_root: Path) -> bool:
    from odylith.runtime.context_engine import odylith_context_engine_store

    return odylith_context_engine_store.runtime_daemon_transport(repo_root=repo_root) is not None


def _load_daemon_cached_runtime_payload(
    *,
    repo_root: Path,
    input_fingerprint: str,
    refresh_profile: str,
) -> dict[str, Any] | None:
    from odylith.runtime.context_engine import odylith_context_engine_store

    result = odylith_context_engine_store.request_runtime_daemon(
        repo_root=repo_root,
        command="compass-runtime-get",
        payload={
            "input_fingerprint": str(input_fingerprint).strip(),
            "refresh_profile": _normalize_refresh_profile(refresh_profile),
        },
        required=False,
        timeout_seconds=2.0,
    )
    if result is None:
        return None
    payload, _runtime_execution = result
    if not isinstance(payload, Mapping) or not bool(payload.get("hit")):
        return None
    cached_payload = payload.get("payload")
    return dict(cached_payload) if isinstance(cached_payload, Mapping) else None


def _record_daemon_cached_runtime_payload(
    *,
    repo_root: Path,
    input_fingerprint: str,
    refresh_profile: str,
    runtime_payload: Mapping[str, Any],
) -> None:
    from odylith.runtime.context_engine import odylith_context_engine_store

    odylith_context_engine_store.request_runtime_daemon(
        repo_root=repo_root,
        command="compass-runtime-put",
        payload={
            "input_fingerprint": str(input_fingerprint).strip(),
            "refresh_profile": _normalize_refresh_profile(refresh_profile),
            "runtime_payload": dict(runtime_payload),
        },
        required=False,
        timeout_seconds=2.0,
    )


def _stamp_surface_runtime_contract(
    *,
    payload: Mapping[str, Any],
    repo_root: Path,
    runtime_mode: str,
    built_from: str,
    cache_hit: bool,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_contract = (
        dict(payload.get("runtime_contract", {}))
        if isinstance(payload.get("runtime_contract"), Mapping)
        else {}
    )
    runtime_contract.update(
        derivation_provenance.build_surface_runtime_contract(
            repo_root=repo_root,
            surface="compass",
            runtime_mode=runtime_mode,
            built_from=built_from,
            cache_hit=cache_hit,
            extra=extra,
        )
    )
    updated = {**dict(payload), "runtime_contract": runtime_contract}
    from odylith.runtime.governance import sync_session as governed_sync_session

    session = governed_sync_session.active_sync_session()
    if session is not None and session.repo_root == Path(repo_root).resolve():
        session.record_surface_decision(
            surface="compass",
            cache_hit=cache_hit,
            built_from=built_from,
            details={
                "input_fingerprint": str(runtime_contract.get("input_fingerprint", "")).strip(),
                "generation": int(runtime_contract.get("generation", 0) or 0),
            },
        )
    return updated


def _brief_contract_fields_present(*, brief: Mapping[str, Any]) -> bool:
    status = str(brief.get("status", "")).strip().lower()
    if not status:
        return True
    if str(brief.get("schema_version", "")).strip() != compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION:
        return False
    if not str(brief.get("substrate_fingerprint", "")).strip():
        return False
    if not str(brief.get("provider_decision", "")).strip():
        return False
    return all(
        key in brief
        for key in (
            "bundle_fingerprint",
            "last_successful_narration_fingerprint",
        )
    )


def _write_current_runtime_payload(
    *,
    repo_root: Path,
    current_json_path: Path,
    current_js_path: Path,
    payload: Mapping[str, Any],
) -> None:
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_json_path,
        content=json.dumps(payload, indent=2) + "\n",
        lock_key=str(current_json_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=current_js_path,
        content="window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        lock_key=str(current_js_path),
    )


def _compact_source_truth_payload(*, runtime_payload: Mapping[str, Any]) -> dict[str, Any]:
    def _mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, Mapping) else {}

    def _mapping_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return []
        return [dict(item) for item in value if isinstance(item, Mapping)]

    return {
        "version": "v1",
        "generated_utc": str(runtime_payload.get("generated_utc", "")).strip(),
        "release_summary": {
            "catalog": _mapping_list(_mapping(runtime_payload.get("release_summary")).get("catalog")),
            "current_release": _mapping(_mapping(runtime_payload.get("release_summary")).get("current_release")),
            "next_release": _mapping(_mapping(runtime_payload.get("release_summary")).get("next_release")),
            "summary": _mapping(_mapping(runtime_payload.get("release_summary")).get("summary")),
        },
        "current_workstreams_by_window": {
            "24h": _mapping_list(_mapping(runtime_payload.get("current_workstreams_by_window")).get("24h")),
            "48h": _mapping_list(_mapping(runtime_payload.get("current_workstreams_by_window")).get("48h")),
        },
        "current_workstreams": _mapping_list(runtime_payload.get("current_workstreams")),
        "workstream_catalog": _mapping_list(runtime_payload.get("workstream_catalog")),
        "verified_scoped_workstreams": _mapping(runtime_payload.get("verified_scoped_workstreams")),
        "promoted_scoped_workstreams": _mapping(runtime_payload.get("promoted_scoped_workstreams")),
        "window_scope_signals": _mapping(runtime_payload.get("window_scope_signals")),
    }


def _refresh_failure_warning(
    *,
    requested_profile: str,
    applied_profile: str,
    reason: str,
    generated_utc: str,
) -> str:
    snapshot_label = str(generated_utc).strip() or "the last successful render"
    reason_token = str(reason or "").strip().lower()
    requested_label = _normalize_refresh_profile(requested_profile)
    reason_label = (
        f"Requested Compass {requested_label} refresh did not finish before the dashboard timeout."
        if reason_token == "timeout"
        else f"Requested Compass {requested_label} refresh failed before a fresh runtime payload was written."
    )
    return (
        f"{reason_label} "
        f"Showing the last successful {_normalize_refresh_profile(applied_profile)} runtime snapshot from {snapshot_label}."
    )


def _apply_refresh_attempt_state(
    *,
    payload: dict[str, Any],
    requested_profile: str,
    applied_profile: str,
    runtime_mode: str,
    status: str,
    reason: str = "",
    fallback_used: bool = False,
    attempted_utc: str = "",
) -> dict[str, Any]:
    runtime_contract = payload.get("runtime_contract")
    normalized_contract = dict(runtime_contract) if isinstance(runtime_contract, Mapping) else {}
    attempted_token = str(attempted_utc or "").strip() or _now_utc_iso()
    applied_token = _normalize_refresh_profile(applied_profile)
    requested_token = _normalize_refresh_profile(requested_profile)
    status_token = "failed" if str(status).strip().lower() == "failed" else "passed"
    reason_token = str(reason or "").strip().lower()
    normalized_contract["last_refresh_attempt"] = {
        "status": status_token,
        "requested_profile": requested_token,
        "applied_profile": applied_token,
        "runtime_mode": str(runtime_mode or "").strip().lower() or "auto",
        "reason": reason_token,
        "attempted_utc": attempted_token,
        "fallback_used": bool(fallback_used),
    }
    if status_token == "failed":
        normalized_contract["last_successful_generated_utc"] = str(payload.get("generated_utc", "")).strip()
        payload["warning"] = _refresh_failure_warning(
            requested_profile=requested_token,
            applied_profile=applied_token,
            reason=reason_token,
            generated_utc=str(payload.get("generated_utc", "")).strip(),
        )
    else:
        payload.pop("warning", None)
    payload["runtime_contract"] = normalized_contract
    return payload


def record_failed_refresh_attempt(
    *,
    repo_root: Path,
    runtime_dir: Path,
    requested_profile: str,
    runtime_mode: str,
    reason: str,
    fallback_used: bool,
) -> bool:
    current_json_path = Path(runtime_dir) / "current.v1.json"
    current_js_path = Path(runtime_dir) / "current.v1.js"
    payload = odylith_context_cache.read_json_object(current_json_path)
    if not payload:
        return False
    runtime_contract = payload.get("runtime_contract")
    applied_profile = (
        _normalize_refresh_profile(str(runtime_contract.get("refresh_profile", _DEFAULT_REFRESH_PROFILE)))
        if isinstance(runtime_contract, Mapping)
        else _DEFAULT_REFRESH_PROFILE
    )
    updated_payload = _apply_refresh_attempt_state(
        payload=dict(payload),
        requested_profile=requested_profile,
        applied_profile=applied_profile,
        runtime_mode=runtime_mode,
        status="failed",
        reason=reason,
        fallback_used=fallback_used,
    )
    _write_current_runtime_payload(
        repo_root=Path(repo_root).resolve(),
        current_json_path=current_json_path,
        current_js_path=current_js_path,
        payload=updated_payload,
    )
    return True


def __getattr__(name: str) -> Any:
    for module_name in _EXPORT_MODULES:
        module = import_module(module_name)
        if hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    names = set(globals())
    for module_name in _EXPORT_MODULES:
        names.update(dir(import_module(module_name)))
    return sorted(names)


def _sync_runtime_monkeypatch_compat() -> None:
    # Tests and sibling callers historically patched private helpers on the
    # facade module itself. Keep that behavior while the implementation lives in
    # extracted runtime modules.
    _runtime_impl = _load_runtime_impl()
    _runtime_impl._normalize_repo_token = _normalize_repo_token


def _split_source_vs_generated_files_cached(files: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    _sync_runtime_monkeypatch_compat()
    return _load_runtime_impl()._split_source_vs_generated_files_cached(files)


def _clear_split_source_vs_generated_files_cached() -> None:
    _load_runtime_impl()._split_source_vs_generated_files_cached.cache_clear()


_split_source_vs_generated_files_cached.cache_clear = _clear_split_source_vs_generated_files_cached


def _split_source_vs_generated_files(files: Sequence[str]) -> tuple[list[str], list[str]]:
    _sync_runtime_monkeypatch_compat()
    return _load_runtime_impl()._split_source_vs_generated_files(files)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Render Compass executive dashboard shell and runtime snapshots.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--output", default="odylith/compass/compass.html", help="Compass shell output HTML")
    parser.add_argument(
        "--runtime-dir",
        default="odylith/compass/runtime",
        help="Compass runtime snapshot directory (local, high-churn).",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_HISTORY_RETENTION_DAYS,
        help="Daily history retention window in days.",
    )
    parser.add_argument(
        "--max-review-age-days",
        type=int,
        default=21,
        help="Stale threshold for Mermaid diagram review age.",
    )
    parser.add_argument(
        "--active-window-minutes",
        type=int,
        default=_DEFAULT_ACTIVE_WINDOW_MINUTES,
        help="Telemetry live/active freshness window in minutes.",
    )
    parser.add_argument(
        "--agent-stream",
        "--codex-stream",
        dest="agent_stream",
        default=agent_runtime_contract.AGENT_STREAM_PATH,
        help="Optional local JSONL stream of agent decision/implementation timeline events.",
    )
    parser.add_argument("--backlog-index", default="odylith/radar/source/INDEX.md")
    parser.add_argument("--plan-index", default="odylith/technical-plans/INDEX.md")
    parser.add_argument("--bugs-index", default="odylith/casebook/bugs/INDEX.md")
    parser.add_argument("--traceability-graph", default="odylith/radar/traceability-graph.v1.json")
    parser.add_argument("--mermaid-catalog", default="odylith/atlas/source/catalog/diagrams.v1.json")
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime projection store when available for fast local rendering.",
    )
    args = parser.parse_args(argv)
    args.refresh_profile = _DEFAULT_REFRESH_PROFILE
    return args


def refresh_runtime_artifacts(
    *,
    repo_root: Path,
    runtime_dir: Path,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    codex_stream_path: Path,
    retention_days: int,
    max_review_age_days: int,
    active_window_minutes: int,
    runtime_mode: str,
    refresh_profile: str = _DEFAULT_REFRESH_PROFILE,
    progress_callback: CompassProgressCallback | None = None,
) -> tuple[dict[str, Any], tuple[Path, Path, Path, Path, Path]]:
    current_json_path = runtime_dir / "current.v1.json"
    current_js_path = runtime_dir / "current.v1.js"
    history_dir = runtime_dir / "history"
    daily_path = history_dir / f"{dt.datetime.now(tz=_COMPASS_TZ).date().isoformat()}.v1.json"
    history_index_path = history_dir / "index.v1.json"
    history_js_path = history_dir / "embedded.v1.js"
    runtime_paths = (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)
    tracked_input_signatures = _compass_runtime_tracked_input_signatures(
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
    )

    input_fingerprint = _compass_runtime_input_fingerprint(
        repo_root=repo_root,
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
        max_review_age_days=max_review_age_days,
        active_window_minutes=active_window_minutes,
        runtime_mode=runtime_mode,
        retention_days=retention_days,
        refresh_profile=refresh_profile,
    )
    normalized_profile = _normalize_refresh_profile(refresh_profile)
    _emit_progress(
        progress_callback,
        stage="input_resolution",
        detail={
            "refresh_profile": normalized_profile,
            "runtime_mode": str(runtime_mode).strip().lower() or "auto",
        },
    )
    daemon_cached_payload = None
    if str(runtime_mode).strip().lower() != "standalone" and _runtime_daemon_available(repo_root=repo_root):
        daemon_cached_payload = _load_daemon_cached_runtime_payload(
            repo_root=repo_root,
            input_fingerprint=input_fingerprint,
            refresh_profile=normalized_profile,
        )
    if daemon_cached_payload is not None and _payload_satisfies_requested_refresh(
        payload=daemon_cached_payload,
        requested_profile=normalized_profile,
    ):
        daemon_cached_payload = _stamp_surface_runtime_contract(
            payload=daemon_cached_payload,
            repo_root=repo_root,
            runtime_mode=runtime_mode,
            built_from="daemon_cached_runtime_payload",
            cache_hit=True,
            extra={"refresh_profile": normalized_profile},
        )
        updated_daemon_payload = _apply_refresh_attempt_state(
            payload=daemon_cached_payload,
            requested_profile=normalized_profile,
            applied_profile=normalized_profile,
            runtime_mode=runtime_mode,
            status="passed",
        )
        daemon_runtime_paths = _load_runtime_impl()._write_runtime_snapshots(
            repo_root=repo_root,
            runtime_dir=runtime_dir,
            payload=updated_daemon_payload,
            retention_days=retention_days,
        )
        _emit_progress(
            progress_callback,
            stage="runtime_payload_built",
            detail={"message": "reused the daemon-held Compass runtime payload because the input fingerprint still matches"},
        )
        _emit_progress(
            progress_callback,
            stage="runtime_snapshots_written",
            detail={"message": "rewrote the current runtime snapshot from the daemon-held payload"},
        )
        _record_daemon_cached_runtime_payload(
            repo_root=repo_root,
            input_fingerprint=input_fingerprint,
            refresh_profile=normalized_profile,
            runtime_payload=updated_daemon_payload,
        )
        return updated_daemon_payload, daemon_runtime_paths
    existing_payload = _existing_runtime_payload_if_fresh(
        repo_root=repo_root,
        current_json_path=current_json_path,
        input_fingerprint=input_fingerprint,
        runtime_paths=runtime_paths,
    )
    if existing_payload is not None and _payload_satisfies_requested_refresh(
        payload=existing_payload,
        requested_profile=normalized_profile,
    ):
        existing_payload = _stamp_surface_runtime_contract(
            payload=existing_payload,
            repo_root=repo_root,
            runtime_mode=runtime_mode,
            built_from="existing_runtime_payload",
            cache_hit=True,
            extra={"refresh_profile": normalized_profile},
        )
        updated_existing_payload = _apply_refresh_attempt_state(
            payload=existing_payload,
            requested_profile=normalized_profile,
            applied_profile=normalized_profile,
            runtime_mode=runtime_mode,
            status="passed",
        )
        reused_runtime_paths = _load_runtime_impl()._write_runtime_snapshots(
            repo_root=repo_root,
            runtime_dir=runtime_dir,
            payload=updated_existing_payload,
            retention_days=retention_days,
        )
        _emit_progress(
            progress_callback,
            stage="runtime_payload_built",
            detail={"message": "reused the current runtime payload because the Compass inputs still match"},
        )
        _emit_progress(
            progress_callback,
            stage="runtime_snapshots_written",
            detail={"message": "rewrote the current runtime snapshot and daily history files from the reused payload"},
        )
        if str(runtime_mode).strip().lower() != "standalone" and _runtime_daemon_available(repo_root=repo_root):
            _record_daemon_cached_runtime_payload(
                repo_root=repo_root,
                input_fingerprint=input_fingerprint,
                refresh_profile=normalized_profile,
                runtime_payload=updated_existing_payload,
            )
        return updated_existing_payload, reused_runtime_paths

    runtime_impl = _load_runtime_impl()
    payload = runtime_impl._build_runtime_payload(
        repo_root=repo_root,
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
        max_review_age_days=max_review_age_days,
        active_window_minutes=active_window_minutes,
        runtime_mode=runtime_mode,
        refresh_profile=normalized_profile,
        progress_callback=progress_callback,
    )
    final_input_fingerprint = input_fingerprint
    postbuild_signatures = _compass_runtime_tracked_input_signatures(
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
    )
    if postbuild_signatures != tracked_input_signatures:
        final_input_fingerprint = _compass_runtime_input_fingerprint(
            repo_root=repo_root,
            backlog_index_path=backlog_index_path,
            plan_index_path=plan_index_path,
            bugs_index_path=bugs_index_path,
            traceability_graph_path=traceability_graph_path,
            mermaid_catalog_path=mermaid_catalog_path,
            codex_stream_path=codex_stream_path,
            max_review_age_days=max_review_age_days,
            active_window_minutes=active_window_minutes,
            runtime_mode=runtime_mode,
            retention_days=retention_days,
            refresh_profile=normalized_profile,
        )
    runtime_contract = payload.get("runtime_contract") if isinstance(payload.get("runtime_contract"), dict) else {}
    runtime_contract.update(
        {
            "version": _RUNTIME_CONTRACT_VERSION,
            "standup_brief_schema_version": compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": final_input_fingerprint,
            "retention_days": int(retention_days),
            "active_window_minutes": int(active_window_minutes),
            "max_review_age_days": int(max_review_age_days),
            "runtime_mode": str(runtime_mode).strip(),
            "refresh_profile": normalized_profile,
        }
    )
    payload["runtime_contract"] = runtime_contract
    payload = _stamp_surface_runtime_contract(
        payload=payload,
        repo_root=repo_root,
        runtime_mode=runtime_mode,
        built_from="fresh_runtime_payload",
        cache_hit=False,
        extra={
            "refresh_profile": normalized_profile,
            "postbuild_input_changed": bool(postbuild_signatures != tracked_input_signatures),
        },
    )
    if normalized_profile == compass_refresh_contract.DEFAULT_REFRESH_PROFILE:
        compass_standup_brief_maintenance.stamp_request_runtime_input_fingerprint(
            repo_root=repo_root,
            runtime_input_fingerprint=final_input_fingerprint,
        )
    _apply_refresh_attempt_state(
        payload=payload,
        requested_profile=normalized_profile,
        applied_profile=normalized_profile,
        runtime_mode=runtime_mode,
        status="passed",
        attempted_utc=str(payload.get("generated_utc", "")).strip(),
    )
    _emit_progress(
        progress_callback,
        stage="runtime_payload_built",
        detail={"message": "built a fresh Compass runtime payload"},
    )
    paths = runtime_impl._write_runtime_snapshots(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        payload=payload,
        retention_days=retention_days,
    )
    _emit_progress(
        progress_callback,
        stage="runtime_snapshots_written",
        detail={"message": "wrote the current runtime snapshot and history files"},
    )
    if normalized_profile == compass_refresh_contract.DEFAULT_REFRESH_PROFILE:
        compass_standup_brief_maintenance.maybe_spawn_background(repo_root=repo_root)
    if str(runtime_mode).strip().lower() != "standalone" and _runtime_daemon_available(repo_root=repo_root):
        _record_daemon_cached_runtime_payload(
            repo_root=repo_root,
            input_fingerprint=final_input_fingerprint,
            refresh_profile=normalized_profile,
            runtime_payload=payload,
        )
    return payload, paths


def _compass_runtime_input_fingerprint(
    *,
    repo_root: Path,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    codex_stream_path: Path,
    max_review_age_days: int,
    active_window_minutes: int,
    runtime_mode: str,
    retention_days: int,
    refresh_profile: str,
) -> str:
    root = Path(repo_root).resolve()
    return odylith_context_cache.fingerprint_payload(
        {
            "version": _RUNTIME_CONTRACT_VERSION,
            "standup_brief_schema_version": compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "projection_fingerprint": default_surface_projection_input_fingerprint(repo_root=root),
            "paths": {
                "backlog_index": odylith_context_cache.path_signature(backlog_index_path),
                "plan_index": odylith_context_cache.path_signature(plan_index_path),
                "bugs_index": odylith_context_cache.path_signature(bugs_index_path),
                "traceability_graph": odylith_context_cache.path_signature(traceability_graph_path),
                "mermaid_catalog": odylith_context_cache.path_signature(mermaid_catalog_path),
                "agent_stream": odylith_context_cache.path_signature(codex_stream_path),
                "codex_stream": odylith_context_cache.path_signature(codex_stream_path),
            },
            "settings": {
                "retention_days": int(retention_days),
                "max_review_age_days": int(max_review_age_days),
                "active_window_minutes": int(active_window_minutes),
                "runtime_mode": str(runtime_mode).strip(),
                "refresh_profile": _normalize_refresh_profile(refresh_profile),
            },
        }
    )


def _compass_runtime_tracked_input_signatures(
    *,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    codex_stream_path: Path,
) -> dict[str, tuple[bool, int, int]]:
    return {
        "backlog_index": odylith_context_cache.path_signature(backlog_index_path),
        "plan_index": odylith_context_cache.path_signature(plan_index_path),
        "bugs_index": odylith_context_cache.path_signature(bugs_index_path),
        "traceability_graph": odylith_context_cache.path_signature(traceability_graph_path),
        "mermaid_catalog": odylith_context_cache.path_signature(mermaid_catalog_path),
        "agent_stream": odylith_context_cache.path_signature(codex_stream_path),
        "codex_stream": odylith_context_cache.path_signature(codex_stream_path),
    }


def _existing_runtime_payload_if_fresh(
    *,
    repo_root: Path,
    current_json_path: Path,
    input_fingerprint: str,
    runtime_paths: tuple[Path, Path, Path, Path, Path],
) -> dict[str, Any] | None:
    current_js_path, _daily_path, history_index_path, history_js_path = runtime_paths[1:]
    if not current_json_path.is_file():
        return None
    if not current_js_path.is_file() or not history_index_path.is_file() or not history_js_path.is_file():
        return None
    payload = odylith_context_cache.read_json_object(current_json_path)
    if not payload:
        return None
    runtime_contract = payload.get("runtime_contract")
    if not isinstance(runtime_contract, dict):
        return None
    if str(runtime_contract.get("version", "")).strip() != _RUNTIME_CONTRACT_VERSION:
        return None
    if (
        str(runtime_contract.get("standup_brief_schema_version", "")).strip()
        != compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION
    ):
        return None
    generation, require_generation, _last_step = derivation_provenance.active_sync_generation(repo_root=repo_root)
    if require_generation and int(runtime_contract.get("generation", -1) or -1) != generation:
        return None
    if str(runtime_contract.get("input_fingerprint", "")).strip() != str(input_fingerprint).strip():
        return None
    return payload


def _payload_satisfies_requested_refresh(
    *,
    payload: Mapping[str, Any],
    requested_profile: str,
) -> bool:
    del requested_profile

    def _brief_rows(value: Any) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        if not isinstance(value, Mapping):
            return rows
        for brief in value.values():
            if isinstance(brief, Mapping):
                rows.append(brief)
        return rows

    ready_briefs = [
        * _brief_rows(payload.get("standup_brief")),
    ]
    scoped = payload.get("standup_brief_scoped")
    if isinstance(scoped, Mapping):
        for window_map in scoped.values():
            ready_briefs.extend(_brief_rows(window_map))
    for brief in ready_briefs:
        if not _brief_contract_fields_present(brief=brief):
            return False
        if str(brief.get("status", "")).strip().lower() != "ready":
            continue
        sections = brief.get("sections")
        if not isinstance(sections, Sequence):
            continue
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            bullets = section.get("bullets")
            if not isinstance(bullets, Sequence):
                continue
            for bullet in bullets:
                if not isinstance(bullet, Mapping):
                    continue
                if compass_standup_brief_voice_validation.contains_rejected_cached_phrase(
                    str(bullet.get("text", "")).strip()
                ):
                    return False
    return True


def _parse_generated_utc(payload: Mapping[str, Any]) -> dt.datetime | None:
    token = str(payload.get("generated_utc", "")).strip()
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


def _compass_shell_asset_paths(*, output_path: Path) -> dict[str, Path]:
    from odylith.runtime.surfaces import compass_dashboard_frontend_contract

    output_dir = output_path.parent
    assets = (
        *compass_dashboard_frontend_contract.compass_shell_style_assets(),
        *compass_dashboard_frontend_contract.compass_shell_support_js_assets(),
    )
    return {
        asset.output_name: output_dir / asset.output_name
        for asset in assets
    }


def _validate_render_inputs(
    *,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    retention_days: int,
    max_review_age_days: int,
    active_window_minutes: int,
) -> list[str]:
    errors: list[str] = []
    for label, path in (
        ("backlog index", backlog_index_path),
        ("plan index", plan_index_path),
        ("bugs index", bugs_index_path),
        ("traceability graph", traceability_graph_path),
        ("mermaid catalog", mermaid_catalog_path),
    ):
        if not path.is_file():
            errors.append(f"missing {label}: {path}")

    if int(retention_days) < 1:
        errors.append("retention-days must be >= 1")
    if int(max_review_age_days) < 1:
        errors.append("max-review-age-days must be >= 1")
    if int(active_window_minutes) < 1:
        errors.append("active-window-minutes must be >= 1")
    return errors


def render_compass_artifacts(
    *,
    repo_root: Path,
    output_path: Path,
    runtime_dir: Path,
    backlog_index_path: Path,
    plan_index_path: Path,
    bugs_index_path: Path,
    traceability_graph_path: Path,
    mermaid_catalog_path: Path,
    codex_stream_path: Path,
    retention_days: int,
    max_review_age_days: int,
    active_window_minutes: int,
    runtime_mode: str,
    refresh_profile: str = _DEFAULT_REFRESH_PROFILE,
    progress_callback: CompassProgressCallback | None = None,
) -> tuple[dict[str, Any], tuple[Path, Path, Path, Path, Path]]:
    errors = _validate_render_inputs(
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        retention_days=retention_days,
        max_review_age_days=max_review_age_days,
        active_window_minutes=active_window_minutes,
    )
    if errors:
        raise ValueError("\n".join(errors))

    runtime_payload, runtime_paths = refresh_runtime_artifacts(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
        retention_days=int(retention_days),
        max_review_age_days=int(max_review_age_days),
        active_window_minutes=int(active_window_minutes),
        runtime_mode=str(runtime_mode),
        refresh_profile=str(refresh_profile),
        progress_callback=progress_callback,
    )
    current_json_path, current_js_path, _daily_path, history_index_path, history_js_path = runtime_paths

    output_path.parent.mkdir(parents=True, exist_ok=True)
    from odylith.runtime.common import stable_generated_utc
    from odylith.runtime.common.consumer_profile import load_consumer_profile
    from odylith.runtime.surfaces import brand_assets, compass_dashboard_frontend_contract, dashboard_surface_bundle
    from odylith.runtime.surfaces.compass_dashboard_shell import _render_shell_html

    shell_asset_paths = _compass_shell_asset_paths(output_path=output_path)
    source_truth_path = output_path.parent / "compass-source-truth.v1.json"
    for asset in (
        *compass_dashboard_frontend_contract.compass_shell_style_assets(),
        *compass_dashboard_frontend_contract.compass_shell_support_js_assets(),
    ):
        asset_path = shell_asset_paths[asset.output_name]
        odylith_context_cache.write_text_if_changed(
            repo_root=repo_root,
            path=asset_path,
            content=compass_dashboard_frontend_contract.load_compass_shell_asset_text(
                asset.template_name,
            ),
            lock_key=str(asset_path),
        )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=source_truth_path,
        content=json.dumps(_compact_source_truth_payload(runtime_payload=runtime_payload), indent=2) + "\n",
        lock_key=str(source_truth_path),
    )

    shell_payload: dict[str, Any] = {
        "base_style_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-style-base.v1.css"]),
        "execution_wave_style_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-style-execution-waves.v1.css"],
        ),
        "surface_style_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-style-surface.v1.css"],
        ),
        "shared_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-shared.v1.js"]),
        "runtime_truth_js_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-runtime-truth.v1.js"],
        ),
        "state_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-state.v1.js"]),
        "summary_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-summary.v1.js"]),
        "timeline_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-timeline.v1.js"]),
        "waves_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-waves.v1.js"]),
        "releases_js_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-releases.v1.js"],
        ),
        "workstreams_js_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-workstreams.v1.js"],
        ),
        "ui_runtime_js_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-ui-runtime.v1.js"],
        ),
        "source_truth_href": _versioned_href(output_path=output_path, target=source_truth_path),
        "traceability_graph_href": _versioned_href(output_path=output_path, target=traceability_graph_path),
        "runtime_json_href": _versioned_href(output_path=output_path, target=current_json_path),
        "runtime_js_href": _versioned_href(output_path=output_path, target=current_js_path),
        "runtime_history_js_href": _versioned_href(output_path=output_path, target=history_js_path),
        "runtime_history_base_href": _as_href(output_path, history_index_path.parent),
        "history_index_href": _versioned_href(output_path=output_path, target=history_index_path),
        "consumer_truth_roots": dict(load_consumer_profile(repo_root=repo_root).get("truth_roots", {})),
        "brand_head_html": brand_assets.render_brand_head_html(repo_root=repo_root, output_path=output_path),
    }
    bundle_paths = dashboard_surface_bundle.build_paths(output_path=output_path, asset_prefix="compass")
    shell_payload["generated_utc"] = stable_generated_utc.resolve_for_js_assignment_file(
        output_path=bundle_paths.payload_js_path,
        global_name="__ODYLITH_COMPASS_SHELL_DATA__",
        payload=shell_payload,
    )

    html_text = _render_shell_html(payload=shell_payload)
    bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
        html_text=html_text,
        payload=shell_payload,
        paths=bundle_paths,
        spec=dashboard_surface_bundle.standard_surface_bundle_spec(
            asset_prefix="compass",
            payload_global_name="__ODYLITH_COMPASS_SHELL_DATA__",
            embedded_json_script_id="compassShellData",
            bootstrap_binding_name="SHELL",
            shell_tab="compass",
            shell_frame_id="frame-compass",
            query_passthrough=(
                ("scope", ("scope", "workstream")),
                ("window", ("window",)),
                ("date", ("date",)),
                ("audit_day", ("audit_day",)),
            ),
        ),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=output_path,
        content=bundled_html,
        lock_key=str(output_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=bundle_paths.payload_js_path,
        content=payload_js,
        lock_key=str(bundle_paths.payload_js_path),
    )
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=bundle_paths.control_js_path,
        content=control_js,
        lock_key=str(bundle_paths.control_js_path),
    )
    source_bundle_mirror.sync_live_paths(
        repo_root=repo_root,
        live_paths=(
            output_path,
            bundle_paths.payload_js_path,
            bundle_paths.control_js_path,
            source_truth_path,
            *shell_asset_paths.values(),
        ),
    )
    _sync_runtime_bundle_mirror(repo_root=repo_root, runtime_paths=runtime_paths)
    _emit_progress(
        progress_callback,
        stage="shell_bundle_written",
        detail={"message": f"wrote the Compass shell bundle to {output_path}"},
    )
    _emit_progress(
        progress_callback,
        stage="complete",
        detail={"message": f"Compass refresh complete at {output_path}"},
    )
    return runtime_payload, runtime_paths


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()

    output_path = _resolve(repo_root, args.output)
    runtime_dir = _resolve(repo_root, args.runtime_dir)
    backlog_index_path = _resolve(repo_root, args.backlog_index)
    plan_index_path = _resolve(repo_root, args.plan_index)
    bugs_index_path = _resolve(repo_root, args.bugs_index)
    traceability_graph_path = _resolve(repo_root, args.traceability_graph)
    mermaid_catalog_path = _resolve(repo_root, args.mermaid_catalog)
    codex_stream_path = _resolve(repo_root, args.agent_stream)

    errors = _validate_render_inputs(
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        retention_days=int(args.retention_days),
        max_review_age_days=int(args.max_review_age_days),
        active_window_minutes=int(args.active_window_minutes),
    )

    if errors:
        print("compass render FAILED")
        for err in errors:
            print(f"- {err}")
        return 2

    runtime_payload, runtime_paths = render_compass_artifacts(
        repo_root=repo_root,
        output_path=output_path,
        runtime_dir=runtime_dir,
        backlog_index_path=backlog_index_path,
        plan_index_path=plan_index_path,
        bugs_index_path=bugs_index_path,
        traceability_graph_path=traceability_graph_path,
        mermaid_catalog_path=mermaid_catalog_path,
        codex_stream_path=codex_stream_path,
        retention_days=int(args.retention_days),
        max_review_age_days=int(args.max_review_age_days),
        active_window_minutes=int(args.active_window_minutes),
        runtime_mode=str(args.runtime_mode),
        refresh_profile=str(args.refresh_profile),
    )
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = runtime_paths

    print("compass render passed")
    print(f"- shell: {output_path}")
    print(f"- runtime_json: {current_json_path}")
    print(f"- runtime_js: {current_js_path}")
    print(f"- daily_snapshot: {daily_path}")
    print(f"- history_index: {history_index_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
