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
import os
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine.surface_projection_fingerprint import default_surface_projection_input_fingerprint
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import dashboard_surface_bundle

DEFAULT_HISTORY_RETENTION_DAYS = 15
_DEFAULT_ACTIVE_WINDOW_MINUTES = 15
_COMPASS_TZ = ZoneInfo("America/Los_Angeles")
_RUNTIME_CONTRACT_VERSION = "v1"
_RUNTIME_REUSE_MAX_AGE_SECONDS = 5 * 60
_EXPORT_MODULES = (
    "odylith.runtime.surfaces.compass_dashboard_base",
    "odylith.runtime.surfaces.compass_dashboard_runtime",
)


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
        "--codex-stream",
        default="odylith/compass/runtime/codex-stream.v1.jsonl",
        help="Optional local JSONL stream of Codex decision/implementation timeline events.",
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
    parser.add_argument(
        "--refresh-profile",
        choices=("full", "shell-safe"),
        default="full",
        help="`shell-safe` rebuilds Compass in bounded mode by deferring live provider narration during refresh.",
    )
    return parser.parse_args(argv)


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
    refresh_profile: str = "full",
) -> tuple[dict[str, Any], tuple[Path, Path, Path, Path, Path]]:
    current_json_path = runtime_dir / "current.v1.json"
    current_js_path = runtime_dir / "current.v1.js"
    history_dir = runtime_dir / "history"
    daily_path = history_dir / f"{dt.datetime.now(tz=_COMPASS_TZ).date().isoformat()}.v1.json"
    history_index_path = history_dir / "index.v1.json"
    history_js_path = history_dir / "embedded.v1.js"
    runtime_paths = (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

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
    normalized_profile = str(refresh_profile or "full").strip().lower() or "full"
    existing_payload = _existing_runtime_payload_if_fresh(
        current_json_path=current_json_path,
        input_fingerprint=input_fingerprint,
        runtime_paths=runtime_paths,
    )
    if existing_payload is not None:
        return existing_payload, runtime_paths

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
    )
    runtime_contract = payload.get("runtime_contract") if isinstance(payload.get("runtime_contract"), dict) else {}
    runtime_contract.update(
        {
            "version": _RUNTIME_CONTRACT_VERSION,
            "standup_brief_schema_version": compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": input_fingerprint,
            "retention_days": int(retention_days),
            "active_window_minutes": int(active_window_minutes),
            "max_review_age_days": int(max_review_age_days),
            "runtime_mode": str(runtime_mode).strip(),
            "refresh_profile": normalized_profile,
        }
    )
    payload["runtime_contract"] = runtime_contract
    paths = runtime_impl._write_runtime_snapshots(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        payload=payload,
        retention_days=retention_days,
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
                "codex_stream": odylith_context_cache.path_signature(codex_stream_path),
            },
            "settings": {
                "retention_days": int(retention_days),
                "max_review_age_days": int(max_review_age_days),
                "active_window_minutes": int(active_window_minutes),
                "runtime_mode": str(runtime_mode).strip(),
                "refresh_profile": str(refresh_profile).strip().lower() or "full",
            },
        }
    )


def _existing_runtime_payload_if_fresh(
    *,
    current_json_path: Path,
    input_fingerprint: str,
    runtime_paths: tuple[Path, Path, Path, Path, Path],
) -> dict[str, Any] | None:
    if not all(path.is_file() for path in runtime_paths):
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
    if str(runtime_contract.get("input_fingerprint", "")).strip() != str(input_fingerprint).strip():
        return None
    generated_utc = _parse_generated_utc(payload)
    if generated_utc is None:
        return None
    age_seconds = (dt.datetime.now(tz=dt.timezone.utc) - generated_utc).total_seconds()
    if age_seconds < 0 or age_seconds > float(_RUNTIME_REUSE_MAX_AGE_SECONDS):
        return None
    return payload


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
    codex_stream_path = _resolve(repo_root, args.codex_stream)

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

    if int(args.retention_days) < 1:
        errors.append("retention-days must be >= 1")
    if int(args.max_review_age_days) < 1:
        errors.append("max-review-age-days must be >= 1")
    if int(args.active_window_minutes) < 1:
        errors.append("active-window-minutes must be >= 1")

    if errors:
        print("compass render FAILED")
        for err in errors:
            print(f"- {err}")
        return 2

    runtime_payload, runtime_paths = refresh_runtime_artifacts(
        repo_root=repo_root,
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    from odylith.runtime.common import stable_generated_utc
    from odylith.runtime.common.consumer_profile import load_consumer_profile
    from odylith.runtime.surfaces import compass_dashboard_frontend_contract
    from odylith.runtime.surfaces import brand_assets, dashboard_surface_bundle
    from odylith.runtime.surfaces.compass_dashboard_shell import _render_shell_html

    shell_asset_paths = _compass_shell_asset_paths(output_path=output_path)
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
        "state_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-state.v1.js"]),
        "summary_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-summary.v1.js"]),
        "timeline_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-timeline.v1.js"]),
        "waves_js_href": _versioned_href(output_path=output_path, target=shell_asset_paths["compass-waves.v1.js"]),
        "workstreams_js_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-workstreams.v1.js"],
        ),
        "ui_runtime_js_href": _versioned_href(
            output_path=output_path,
            target=shell_asset_paths["compass-ui-runtime.v1.js"],
        ),
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

    print("compass render passed")
    print(f"- shell: {output_path}")
    print(f"- runtime_json: {current_json_path}")
    print(f"- runtime_js: {current_js_path}")
    print(f"- daily_snapshot: {daily_path}")
    print(f"- history_index: {history_index_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
