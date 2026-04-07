"""Render the centralized delivery-governance intelligence shell.

The shell is a lightweight parent surface that preserves underlying governance
UIs by embedding each page in an iframe and switching via query-driven tabs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.install import version_status
from odylith.install.state import load_install_state, load_version_pin
from odylith.runtime.common import stable_generated_utc
from odylith.runtime.common.product_assets import resolve_product_path
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.evaluation import benchmark_compare
from odylith.runtime.governance import agent_governance_intelligence
from odylith.runtime.governance import workstream_inference as ws_inference
from odylith.runtime.surfaces import brand_assets
from odylith.runtime.surfaces import dashboard_shell_links
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import shell_onboarding
from odylith.runtime.surfaces import tooling_dashboard_runtime_builder
from odylith.runtime.surfaces import tooling_dashboard_shell_presenter

_shell_href = dashboard_shell_links.shell_href
_scope_lookup = dashboard_shell_links.scope_lookup
_scope_href = dashboard_shell_links.scope_href
_surface_href = dashboard_shell_links.surface_href
_linkify_shell_text = dashboard_shell_links.linkify_shell_text
_proof_href = dashboard_shell_links.proof_href
_render_proof_refs_html = dashboard_shell_links.render_proof_refs_html
_shell_case_preview_rows = tooling_dashboard_shell_presenter.shell_case_preview_rows
_SHELL_SOURCE_PATH = Path("odylith/runtime/source/tooling_shell.v1.json")
_LIVE_REFRESH_POLICY_BALANCED = "balanced"
_LIVE_REFRESH_POLICY_FULL_DEV = "full_dev"
_LIVE_REFRESH_POLICY_PROOF_FROZEN = "proof_frozen"
_LIVE_REFRESH_POLICY_ALIASES = {
    "balanced": _LIVE_REFRESH_POLICY_BALANCED,
    "full-dev": _LIVE_REFRESH_POLICY_FULL_DEV,
    "full_dev": _LIVE_REFRESH_POLICY_FULL_DEV,
    "proof": _LIVE_REFRESH_POLICY_PROOF_FROZEN,
    "proof_frozen": _LIVE_REFRESH_POLICY_PROOF_FROZEN,
}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Render odylith/index.html as the centralized delivery-governance intelligence shell.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--output", default="odylith/index.html", help="Rendered dashboard output path")
    parser.add_argument("--radar", default="odylith/radar/radar.html", help="Backlog Radar HTML path")
    parser.add_argument("--atlas", default="odylith/atlas/atlas.html", help="Atlas HTML path")
    parser.add_argument("--compass", default="odylith/compass/compass.html", help="Compass HTML path")
    parser.add_argument("--registry", default="odylith/registry/registry.html", help="Registry HTML path")
    parser.add_argument("--casebook", default="odylith/casebook/casebook.html", help="Casebook HTML path")
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local Odylith compiler snapshot and runtime surfaces when available for delivery-intelligence slices.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, value: str) -> Path:
    raw = str(value or "").strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _as_href(output_path: Path, target: Path) -> str:
    rel = os.path.relpath(str(target), start=str(output_path.parent))
    return Path(rel).as_posix()


def _humanize_repo_name(name: str) -> str:
    token = str(name or "").strip().replace("-", " ").replace("_", " ").replace(".", " ")
    parts = [part for part in token.split() if part]
    if not parts:
        return "Repository"
    return " ".join(part[:1].upper() + part[1:] for part in parts)


def _format_shell_version_label(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if token[0].isdigit():
        return f"v{token}"
    return token


def _prune_release_note_pages(*, output_path: Path) -> None:
    release_notes_root = output_path.parent / "release-notes"
    if release_notes_root.is_dir():
        shutil.rmtree(release_notes_root)
        return
    if release_notes_root.exists():
        release_notes_root.unlink()


def _is_public_odylith_repo(repo_root: Path) -> bool:
    root = Path(repo_root).resolve()
    return (
        (root / "src" / "odylith").is_dir()
        and (root / "odylith").is_dir()
        and (root / "pyproject.toml").is_file()
    )


def _load_tooling_shell_source(*, repo_root: Path) -> dict[str, Any]:
    source_path = (Path(repo_root).resolve() / _SHELL_SOURCE_PATH).resolve()
    if not source_path.exists() and _is_public_odylith_repo(repo_root):
        source_path = resolve_product_path(repo_root=repo_root, relative_path=_SHELL_SOURCE_PATH)
    if not source_path.is_file():
        return {}
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _build_shell_source_payload(*, repo_root: Path) -> dict[str, Any]:
    payload = _load_tooling_shell_source(repo_root=repo_root)
    shell_repo_label = str(payload.get("shell_repo_label", "")).strip() or f"Repo · {_humanize_repo_name(repo_root.name)}"
    raw_notes = payload.get("maintainer_notes")
    maintainer_notes = raw_notes if isinstance(raw_notes, list) else []
    raw_cheatsheet = payload.get("agent_cheatsheet")
    agent_cheatsheet = dict(raw_cheatsheet) if isinstance(raw_cheatsheet, Mapping) else {}
    live_refresh_policy = _normalize_live_refresh_policy(payload.get("live_refresh_policy"))
    return {
        "shell_repo_label": shell_repo_label,
        "maintainer_notes": maintainer_notes,
        "agent_cheatsheet": agent_cheatsheet,
        "live_refresh_policy": live_refresh_policy,
    }


def _build_self_host_payload(*, repo_root: Path) -> dict[str, Any]:
    try:
        status = version_status(repo_root=repo_root)
    except Exception:
        return {}
    return {
        "repo_role": status.repo_role,
        "posture": status.posture,
        "runtime_source": status.runtime_source,
        "release_eligible": status.release_eligible,
        "pinned_version": status.pinned_version,
        "active_version": status.active_version,
        "detached": status.detached,
        "diverged_from_pin": status.diverged_from_pin,
    }


def _resolve_shell_version_label(
    *,
    repo_root: Path,
    self_host_payload: Mapping[str, Any],
    release_spotlight: Mapping[str, Any],
) -> str:
    active_version = str(self_host_payload.get("active_version", "")).strip()
    pinned_version = str(self_host_payload.get("pinned_version", "")).strip()
    if active_version or pinned_version:
        return _format_shell_version_label(active_version or pinned_version)

    try:
        install_state = load_install_state(repo_root=repo_root)
    except Exception:
        install_state = {}
    install_active_version = (
        str(install_state.get("active_version", "")).strip()
        if isinstance(install_state, Mapping)
        else ""
    )
    if install_active_version:
        return _format_shell_version_label(install_active_version)

    try:
        pin = load_version_pin(repo_root=repo_root, fallback_version="")
    except Exception:
        pin = None
    pin_version = str(pin.odylith_version if pin else "").strip()
    if pin_version:
        return _format_shell_version_label(pin_version)

    release_version = str(release_spotlight.get("to_version", "")).strip()
    if release_version:
        return _format_shell_version_label(release_version)
    return ""


def _build_live_refresh_worktree_payload(*, repo_root: Path) -> dict[str, Any]:
    changed_paths = agent_governance_intelligence.collect_git_changed_paths(repo_root=repo_root)
    meaningful_paths = [
        token for token in changed_paths if not ws_inference.is_generated_or_global_path(token)
    ]
    generated_paths = [
        token for token in changed_paths if ws_inference.is_generated_or_global_path(token)
    ]
    if meaningful_paths and generated_paths:
        status = "mixed"
    elif meaningful_paths:
        status = "meaningful_only"
    elif generated_paths:
        status = "generated_only"
    else:
        status = "clean"
    return {
        "status": status,
        "meaningful_changed_count": len(meaningful_paths),
        "generated_changed_count": len(generated_paths),
        "meaningful_examples": meaningful_paths[:3],
        "generated_examples": generated_paths[:3],
    }


def _normalize_live_refresh_policy(value: object) -> str:
    token = str(value or "").strip().lower()
    return _LIVE_REFRESH_POLICY_ALIASES.get(token, "")


def _live_refresh_policy_override(*, shell_source_payload: Mapping[str, Any] | None = None) -> str:
    env_override = _normalize_live_refresh_policy(os.environ.get("ODYLITH_LIVE_REFRESH_POLICY"))
    if env_override:
        return env_override
    if isinstance(shell_source_payload, Mapping):
        source_override = _normalize_live_refresh_policy(shell_source_payload.get("live_refresh_policy"))
        if source_override:
            return source_override
    return ""


def _surface_refresh_policies(*, policy_id: str) -> dict[str, dict[str, Any]]:
    atlas_auto_reload = str(policy_id).strip() == _LIVE_REFRESH_POLICY_FULL_DEV
    return {
        "radar": {
            "label": "Radar",
            "kind": "runtime_backed",
            "auto_reload": True,
            "projection_keys": ["workstreams", "plans", "traceability", "delivery"],
        },
        "registry": {
            "label": "Registry",
            "kind": "runtime_backed",
            "auto_reload": True,
            "projection_keys": ["components"],
        },
        "compass": {
            "label": "Compass",
            "kind": "runtime_backed",
            "auto_reload": True,
            "projection_keys": [
                "codex_events",
                "workstreams",
                "plans",
                "bugs",
                "diagrams",
                "components",
                "traceability",
                "delivery",
            ],
            "provider_refresh": "manual_only",
        },
        "casebook": {
            "label": "Casebook",
            "kind": "runtime_backed",
            "auto_reload": True,
            "projection_keys": ["bugs"],
        },
        "atlas": {
            "label": "Atlas",
            "kind": "explicit_sync" if not atlas_auto_reload else "read_only_auto_reload",
            "auto_reload": atlas_auto_reload,
            "projection_keys": ["diagrams"],
            "next_command": "odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync",
            "note": (
                "Atlas sync can mutate tracked diagram metadata; balanced mode keeps that refresh explicit."
                if not atlas_auto_reload
                else "Atlas auto-reloads only when refreshed outputs already exist; it still never runs background sync."
            ),
        },
    }


def _reloadable_tabs_from_surface_policies(surface_policies: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return [
        str(tab).strip()
        for tab, policy in surface_policies.items()
        if isinstance(policy, Mapping) and bool(policy.get("auto_reload"))
    ]


def _resolve_live_refresh_policy(
    *,
    self_host_payload: Mapping[str, Any],
    shell_source_payload: Mapping[str, Any] | None = None,
) -> str:
    override = _live_refresh_policy_override(shell_source_payload=shell_source_payload)
    if override:
        return override
    repo_role = str(self_host_payload.get("repo_role", "")).strip()
    posture = str(self_host_payload.get("posture", "")).strip()
    if repo_role == "product_repo" and posture != "detached_source_local":
        return _LIVE_REFRESH_POLICY_PROOF_FROZEN
    return _LIVE_REFRESH_POLICY_BALANCED


def _build_live_refresh_payload(
    *,
    repo_root: Path,
    output_path: Path,
    self_host_payload: Mapping[str, Any],
    shell_source_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_id = _resolve_live_refresh_policy(
        self_host_payload=self_host_payload,
        shell_source_payload=shell_source_payload,
    )
    if policy_id == _LIVE_REFRESH_POLICY_PROOF_FROZEN:
        return {
            "enabled": False,
            "mode": "disabled",
            "policy_id": _LIVE_REFRESH_POLICY_PROOF_FROZEN,
            "disabled_reason": "benchmark_frozen_product_repo",
            "note": "Product-repo shell stays frozen so maintainer benchmark and proof lanes are not skewed by passive refresh behavior.",
        }
    surface_policies = _surface_refresh_policies(policy_id=policy_id)
    reloadable_tabs = _reloadable_tabs_from_surface_policies(surface_policies)
    poll_interval_ms = 12000 if policy_id == _LIVE_REFRESH_POLICY_FULL_DEV else 20000
    note = (
        "Balanced live-refresh keeps Compass, Radar, Registry, and Casebook current through read-only reloads while Atlas stays explicit. "
        "Never runs sync, never starts provider-backed brief generation, and never mutates tracked Odylith truth."
        if policy_id == _LIVE_REFRESH_POLICY_BALANCED
        else "Full-dev live-refresh uses the same read-only runtime probe with a faster cadence and allows Atlas to auto-reload only when refreshed outputs already exist. "
        "It still never runs sync, never starts provider-backed brief generation, and never mutates tracked Odylith truth."
    )
    return {
        "enabled": True,
        "mode": "passive_runtime_probe",
        "policy_id": policy_id,
        "state_href": _as_href(
            output_path=output_path,
            target=odylith_context_engine_store.state_js_path(repo_root=repo_root),
        ),
        "state_global_name": odylith_context_engine_store.STATE_JS_GLOBAL_NAME,
        "poll_interval_ms": poll_interval_ms,
        "auto_reload_idle_debounce_ms": 3000,
        "auto_reload_min_interval_ms": 45000,
        "reloadable_tabs": reloadable_tabs,
        "surface_policies": surface_policies,
        "credit_guard": {
            "provider_backed_refresh": "manual_only",
            "tracked_truth_background_writes": False,
            "benchmark_safe": True,
        },
        "note": note,
        "worktree": _build_live_refresh_worktree_payload(repo_root=repo_root),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_path = _resolve(repo_root, args.output)
    radar_path = _resolve(repo_root, args.radar)
    atlas_path = _resolve(repo_root, args.atlas)
    compass_path = _resolve(repo_root, args.compass)
    registry_path = _resolve(repo_root, args.registry)
    casebook_path = _resolve(repo_root, args.casebook)
    surface_paths = tooling_dashboard_runtime_builder.ToolingDashboardSurfacePaths(
        output_path=output_path,
        radar_path=radar_path,
        atlas_path=atlas_path,
        compass_path=compass_path,
        registry_path=registry_path,
        casebook_path=casebook_path,
    )

    errors = tooling_dashboard_runtime_builder.validate_surface_paths(surface_paths)
    if errors:
        print("tooling dashboard render FAILED")
        for err in errors:
            print(f"- {err}")
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    release_spotlight = shell_onboarding.build_release_spotlight(repo_root=repo_root)
    version_story = shell_onboarding.build_version_story(repo_root=repo_root)
    main_brand_payload = brand_assets.tooling_shell_brand_payload(repo_root=repo_root, output_path=output_path)
    self_host_payload = _build_self_host_payload(repo_root=repo_root)
    shell_source_payload = _build_shell_source_payload(repo_root=repo_root)
    benchmark_story = (
        benchmark_compare.build_benchmark_story(repo_root=repo_root)
        if str(self_host_payload.get("repo_role", "")).strip() == "product_repo"
        else {}
    )
    shell_payload = odylith_context_engine_store.load_delivery_surface_payload(
        repo_root=repo_root,
        surface="shell",
        runtime_mode=args.runtime_mode,
        include_shell_snapshots=True,
    )
    build_result = tooling_dashboard_runtime_builder.build_runtime_payload(
        repo_root=repo_root,
        surface_paths=surface_paths,
        shell_payload=dict(shell_payload) if isinstance(shell_payload, dict) else {},
        welcome_state=shell_onboarding.build_welcome_state(repo_root=repo_root),
        release_spotlight=release_spotlight,
        version_story=version_story,
        benchmark_story=benchmark_story,
        shell_source_payload=shell_source_payload,
        self_host_payload=self_host_payload,
        brand_payload=main_brand_payload,
        shell_version_label=_resolve_shell_version_label(
            repo_root=repo_root,
            self_host_payload=self_host_payload,
            release_spotlight=release_spotlight,
        ),
    )
    runtime_payload = dict(build_result.runtime_payload)
    runtime_payload["live_refresh"] = _build_live_refresh_payload(
        repo_root=repo_root,
        output_path=output_path,
        self_host_payload=self_host_payload,
        shell_source_payload=shell_source_payload,
    )
    if bool(runtime_payload["live_refresh"].get("enabled")):
        odylith_context_engine_store.ensure_state_js_probe_asset(repo_root=repo_root)
    _prune_release_note_pages(output_path=output_path)
    runtime_payload["odylith_drawer"] = tooling_dashboard_shell_presenter.build_odylith_drawer_payload(runtime_payload)
    bundle_paths = dashboard_surface_bundle.build_paths(output_path=output_path, asset_prefix="tooling")
    runtime_payload["generated_utc"] = stable_generated_utc.resolve_for_js_assignment_file(
        output_path=bundle_paths.payload_js_path,
        global_name="__ODYLITH_TOOLING_DATA__",
        payload=runtime_payload,
    )
    payload: dict[str, Any] = {
        **runtime_payload,
    }

    bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
        html_text=tooling_dashboard_shell_presenter.render_html(payload),
        payload=runtime_payload,
        paths=bundle_paths,
        spec=dashboard_surface_bundle.standard_surface_bundle_spec(
            asset_prefix="tooling",
            payload_global_name="__ODYLITH_TOOLING_DATA__",
            embedded_json_script_id="toolingDashboardData",
            bootstrap_binding_name="payload",
        ),
    )
    output_path.write_text(bundled_html, encoding="utf-8")
    bundle_paths.payload_js_path.write_text(payload_js, encoding="utf-8")
    bundle_paths.control_js_path.write_text(control_js, encoding="utf-8")
    print("tooling dashboard render passed")
    print(f"- output: {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
