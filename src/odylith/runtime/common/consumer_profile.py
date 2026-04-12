from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text
from odylith.runtime.common.guidance_paths import has_project_guidance


PROFILE_VERSION = "v1"
_SCRIPT_PREFIX = "scr" + "ipts/"
_TEST_SCRIPT_PREFIX = "tests/" + "scr" + "ipts/"
PUBLIC_PRODUCT_COMPONENT_SPECS_ROOT = "odylith/registry/source/components"
LEGACY_PRODUCT_SPEC_PATH_ALIASES: dict[str, str] = {
    "odylith/SPEC.md": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith/atlas/SPEC.md": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "odylith/casebook/SPEC.md": "odylith/registry/source/components/casebook/CURRENT_SPEC.md",
    "odylith/compass/SPEC.md": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "odylith/radar/SPEC.md": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "odylith/registry/SPEC.md": "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    "odylith/surfaces/DASHBOARD_SPEC.md": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "odylith/runtime/CONTEXT_ENGINE_SPEC.md": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith/runtime/REMEDIATOR_SPEC.md": "odylith/registry/source/components/remediator/CURRENT_SPEC.md",
    "odylith/runtime/SUBAGENT_ORCHESTRATOR_SPEC.md": "odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md",
    "odylith/runtime/SUBAGENT_ROUTER_SPEC.md": "odylith/registry/source/components/subagent-router/CURRENT_SPEC.md",
    "odylith/runtime/TRIBUNAL_SPEC.md": "odylith/registry/source/components/tribunal/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/SPEC.md": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/atlas/SPEC.md": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/casebook/SPEC.md": "odylith/registry/source/components/casebook/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/compass/SPEC.md": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/radar/SPEC.md": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/registry/SPEC.md": "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/surfaces/DASHBOARD_SPEC.md": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/runtime/CONTEXT_ENGINE_SPEC.md": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/runtime/REMEDIATOR_SPEC.md": "odylith/registry/source/components/remediator/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/runtime/SUBAGENT_ORCHESTRATOR_SPEC.md": "odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/runtime/SUBAGENT_ROUTER_SPEC.md": "odylith/registry/source/components/subagent-router/CURRENT_SPEC.md",
    "src/odylith/bundle/assets/odylith/runtime/TRIBUNAL_SPEC.md": "odylith/registry/source/components/tribunal/CURRENT_SPEC.md",
}
PUBLIC_PRODUCT_RUNBOOK_PATHS: frozenset[str] = frozenset(
    {
        "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
        "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
        "odylith/runtime/SUBAGENT_OPERATIONS.md",
        "odylith/runtime/TRIBUNAL_AND_REMEDIATION.md",
    }
)
LEGACY_PRODUCT_MODULE_TARGETS: dict[str, str] = {
    "agent_governance_intelligence": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "auto_promote_workstream_phase": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "auto_update_mermaid_diagrams": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "backfill_workstream_traceability": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "build_traceability_graph": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "compass_dashboard_base": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "compass_dashboard_runtime": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "compass_dashboard_shell": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "compass_standup_brief_narrator": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "component_registry_intelligence": "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    "dashboard_shell_links": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "dashboard_surface_bundle": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "dashboard_template_runtime": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "dashboard_time": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "dashboard_ui_primitives": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "dashboard_ui_runtime_primitives": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "delivery_intelligence_engine": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "delivery_intelligence_narrator": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "execution_wave_contract": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "execution_wave_ui_runtime_primitives": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "execution_wave_view_model": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "generated_surface_cleanup": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "install_mermaid_autosync_hook": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "log_compass_timeline_event": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "normalize_plan_risk_mitigation": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "odylith_ablation": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith_architecture_mode": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "odylith_benchmark_runner": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith_context_cache": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_context_engine": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_context_engine_store": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_control_state": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith_evaluation_ledger": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith_memory_backend": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_projection_bundle": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_projection_snapshot": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_reasoning": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "odylith_remote_retrieval": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith_runtime_surface_summary": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "operator_readout": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "plan_progress": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "reconcile_plan_workstream_binding": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "remediator": "odylith/registry/source/components/remediator/CURRENT_SPEC.md",
    "render_backlog_ui": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "render_casebook_dashboard": "odylith/registry/source/components/casebook/CURRENT_SPEC.md",
    "render_compass_dashboard": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "render_mermaid_catalog": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "render_registry_dashboard": "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    "render_tooling_dashboard": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "release_semver": "odylith/registry/source/components/release/CURRENT_SPEC.md",
    "release_version_session": "odylith/registry/source/components/release/CURRENT_SPEC.md",
    "audit_third_party_licenses": "odylith/registry/source/components/release/CURRENT_SPEC.md",
    "publish_release_assets": "odylith/registry/source/components/release/CURRENT_SPEC.md",
    "local_release_smoke": "odylith/registry/source/components/release/CURRENT_SPEC.md",
    "scaffold_mermaid_diagram": "odylith/registry/source/components/atlas/CURRENT_SPEC.md",
    "stable_generated_utc": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "subagent_orchestrator": "odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md",
    "subagent_router": "odylith/registry/source/components/subagent-router/CURRENT_SPEC.md",
    "sync_component_spec_requirements": "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    "sync_workstream_artifacts": "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
    "tooling_context_budgeting": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "tooling_context_packet_builder": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "tooling_context_quality": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "tooling_context_retrieval": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "tooling_context_routing": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "tooling_dashboard_frontend_contract": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "tooling_dashboard_shell_presenter": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "tooling_guidance_catalog": "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
    "tooling_memory_contracts": "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "traceability_ui_lookup": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "tribunal_engine": "odylith/registry/source/components/tribunal/CURRENT_SPEC.md",
    "update_compass": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "validate_backlog_contract": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "validate_component_registry_contract": "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    "validate_plan_risk_mitigation_contract": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "validate_plan_traceability_contract": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "validate_plan_workstream_binding": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
    "watch_prompt_transactions": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "workstream_inference": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
}
LEGACY_PRODUCT_PREFIX_TARGETS: tuple[tuple[str, str], ...] = (
    ("release/", "odylith/registry/source/components/release/CURRENT_SPEC.md"),
    ("templates/tooling_dashboard/", "odylith/registry/source/components/dashboard/CURRENT_SPEC.md"),
    ("contracts/specs/skills", "odylith/registry/source/components/dashboard/CURRENT_SPEC.md"),
)
_PROCESS_CONSUMER_PROFILE_CACHE: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}


def _consumer_profile_cache_signature(*, repo_root: Path) -> tuple[Any, ...]:
    root = Path(repo_root).resolve()
    path = consumer_profile_path(repo_root=root)
    if path.is_file():
        try:
            stat = path.stat()
        except OSError:
            return ("profile_error", str(path))
        return ("profile", stat.st_mtime_ns, stat.st_size)
    runbooks_root = root / "docs" / "runbooks"
    repo_name = root.name.strip()
    runbook_candidates = []
    if repo_name:
        runbook_candidates.append(runbooks_root / repo_name)
        suffix = repo_name.rsplit("-", 1)[-1].strip()
        if suffix and suffix != repo_name:
            runbook_candidates.append(runbooks_root / suffix)
    return (
        "default",
        _is_public_odylith_repo(repo_root=root),
        runbooks_root.is_dir(),
        tuple(candidate.is_dir() for candidate in runbook_candidates),
    )


def _copy_consumer_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": str(profile.get("version", "")).strip(),
        "consumer_id": str(profile.get("consumer_id", "")).strip(),
        "truth_roots": (
            {str(key): str(value) for key, value in profile.get("truth_roots", {}).items()}
            if isinstance(profile.get("truth_roots"), Mapping)
            else {}
        ),
        "surface_roots": (
            {str(key): str(value) for key, value in profile.get("surface_roots", {}).items()}
            if isinstance(profile.get("surface_roots"), Mapping)
            else {}
        ),
        "odylith_write_policy": (
            {
                "odylith_fix_mode": str(profile.get("odylith_write_policy", {}).get("odylith_fix_mode", "")).strip(),
                "allow_odylith_mutations": bool(profile.get("odylith_write_policy", {}).get("allow_odylith_mutations")),
                "protected_roots": [
                    str(token)
                    for token in profile.get("odylith_write_policy", {}).get("protected_roots", [])
                    if str(token).strip()
                ],
            }
            if isinstance(profile.get("odylith_write_policy"), Mapping)
            else {}
        ),
    }


def _clear_consumer_profile_cache(*, repo_root: Path | None = None) -> None:
    if repo_root is None:
        _PROCESS_CONSUMER_PROFILE_CACHE.clear()
        return
    _PROCESS_CONSUMER_PROFILE_CACHE.pop(str(Path(repo_root).resolve()), None)


def consumer_profile_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "consumer-profile.json").resolve()


def _resolve_token(*, repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (Path(repo_root).resolve() / path).resolve()


def _path_exists(*, repo_root: Path, token: str) -> bool:
    return _resolve_token(repo_root=repo_root, token=token).exists()


def _is_public_odylith_repo(*, repo_root: Path) -> bool:
    root = Path(repo_root).resolve()
    return (
        (root / "src" / "odylith").is_dir()
        and (root / "odylith").is_dir()
        and (root / "pyproject.toml").is_file()
    )


def _resolve_repo_root_for_profile(repo_root: Path | None = None) -> Path | None:
    if repo_root is not None:
        return Path(repo_root).resolve()
    cwd = Path.cwd().resolve()
    if not has_project_guidance(repo_root=cwd):
        return None
    if (cwd / ".odylith").exists() or (cwd / "odylith").exists() or (cwd / "src" / "odylith").is_dir():
        return cwd
    return None


def legacy_truth_aliases(*, repo_root: Path | None = None, profile: Mapping[str, Any] | None = None) -> dict[str, str]:
    return dict(LEGACY_PRODUCT_SPEC_PATH_ALIASES)


def _legacy_product_token_alias(token: str) -> str:
    normalized = str(token or "").strip().replace("\\", "/")
    # Strip exactly one leading ``./`` prefix. ``str.lstrip("./")`` is a
    # broken idiom that strips every leading ``.`` or ``/`` character and
    # silently mangles dotfile directories like ``.claude/…`` or
    # ``.codex/…`` into ``claude/…`` / ``codex/…``.
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return ""
    lower = normalized.lower()
    for prefix, target in LEGACY_PRODUCT_PREFIX_TARGETS:
        script_prefix = f"{_SCRIPT_PREFIX}{prefix}".lower()
        test_prefix = f"{_TEST_SCRIPT_PREFIX}{prefix}".lower()
        if lower.startswith(script_prefix) or lower.startswith(test_prefix):
            return target
    if not (lower.startswith(_SCRIPT_PREFIX) or lower.startswith(_TEST_SCRIPT_PREFIX)):
        return normalized
    module_name = Path(normalized).name
    if module_name.lower().endswith(".py"):
        module_name = module_name[:-3]
    if module_name.lower().startswith("test_"):
        module_name = module_name[5:]
    return LEGACY_PRODUCT_MODULE_TARGETS.get(module_name, normalized)


def canonical_truth_token(token: str, *, repo_root: Path | None = None) -> str:
    normalized = str(token or "").strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    aliases = legacy_truth_aliases(repo_root=repo_root)
    resolved = aliases.get(normalized, normalized)
    return _legacy_product_token_alias(resolved)


def truth_root_tokens(*, repo_root: Path) -> dict[str, str]:
    profile = load_consumer_profile(repo_root=repo_root)
    return {
        str(key): str(value).strip().strip("/")
        for key, value in dict(profile.get("truth_roots", {})).items()
        if str(key).strip() and str(value).strip()
    }


def truth_path_kind(
    token: str,
    *,
    repo_root: Path,
    truth_roots: Mapping[str, Any] | None = None,
) -> str:
    normalized = canonical_truth_token(token, repo_root=repo_root).strip().strip("/")
    if not normalized:
        return ""
    if normalized.startswith("odylith/registry/source/components/"):
        if normalized.endswith("/CURRENT_SPEC.md"):
            return "component_spec"
        if normalized.endswith("/FORENSICS.v1.json"):
            return "component_forensics"
    if normalized in PUBLIC_PRODUCT_RUNBOOK_PATHS:
        return "runbook"
    roots = (
        {
            str(key): str(value).strip().strip("/")
            for key, value in truth_roots.items()
            if str(key).strip() and str(value).strip()
        }
        if isinstance(truth_roots, Mapping)
        else truth_root_tokens(repo_root=repo_root)
    )
    specs_root = str(roots.get("component_specs", "")).strip().strip("/")
    if specs_root and specs_root != "odylith":
        if normalized == specs_root:
            return "component_spec"
        if normalized.startswith(f"{specs_root}/"):
            if normalized.endswith("/FORENSICS.v1.json") or normalized.lower().endswith(".forensics.v1.json"):
                return "component_forensics"
            if normalized.lower().endswith(".md"):
                return "component_spec"
    runbooks_root = str(roots.get("runbooks", "")).strip().strip("/")
    if runbooks_root and runbooks_root != "odylith":
        if normalized == runbooks_root or normalized.startswith(f"{runbooks_root}/"):
            return "runbook"
    return ""


def is_component_spec_path(token: str, *, repo_root: Path) -> bool:
    return truth_path_kind(token, repo_root=repo_root) == "component_spec"


def is_component_forensics_path(token: str, *, repo_root: Path) -> bool:
    return truth_path_kind(token, repo_root=repo_root) == "component_forensics"


def is_runbook_path(token: str, *, repo_root: Path) -> bool:
    return truth_path_kind(token, repo_root=repo_root) == "runbook"


def _default_runbooks_root(*, repo_root: Path) -> str:
    root = Path(repo_root).resolve()
    if _is_public_odylith_repo(repo_root=root):
        return "odylith"
    runbooks_root = root / "docs" / "runbooks"
    if not runbooks_root.is_dir():
        return "docs/runbooks"
    candidates: list[Path] = []
    repo_name = root.name.strip()
    if repo_name:
        candidates.append(runbooks_root / repo_name)
        suffix = repo_name.rsplit("-", 1)[-1].strip()
        if suffix and suffix != repo_name:
            candidates.append(runbooks_root / suffix)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.relative_to(root).as_posix()
    return "docs/runbooks"


def _normalize_policy_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _default_odylith_write_policy(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if _is_public_odylith_repo(repo_root=root):
        return {
            "odylith_fix_mode": "maintainer_authorized",
            "allow_odylith_mutations": True,
            "protected_roots": [],
        }
    return {
        "odylith_fix_mode": "feedback_only",
        "allow_odylith_mutations": False,
        "protected_roots": ["odylith", ".odylith"],
    }


def _normalize_odylith_write_policy(
    *,
    defaults: Mapping[str, Any],
    overrides: Mapping[str, Any] | None,
) -> dict[str, Any]:
    default_mode = str(defaults.get("odylith_fix_mode", "")).strip() or "feedback_only"
    raw_mode = (
        str(overrides.get("odylith_fix_mode", "")).strip()
        if isinstance(overrides, Mapping)
        else default_mode
    )
    mode = raw_mode.lower().replace("-", "_").replace(" ", "_") or default_mode
    if mode not in {"feedback_only", "maintainer_authorized"}:
        mode = default_mode
    allow_mutations = (
        _normalize_policy_bool(
            overrides.get("allow_odylith_mutations"),
            default=bool(defaults.get("allow_odylith_mutations")),
        )
        if isinstance(overrides, Mapping)
        else bool(defaults.get("allow_odylith_mutations"))
    )
    default_roots = [
        str(token).strip().strip("/")
        for token in defaults.get("protected_roots", [])
        if str(token).strip().strip("/")
    ]
    override_roots = (
        [
            str(token).strip().strip("/")
            for token in overrides.get("protected_roots", [])
            if str(token).strip().strip("/")
        ]
        if isinstance(overrides, Mapping) and isinstance(overrides.get("protected_roots"), list)
        else default_roots
    )
    protected_roots = override_roots or ([] if allow_mutations else default_roots or ["odylith"])
    return {
        "odylith_fix_mode": mode,
        "allow_odylith_mutations": allow_mutations,
        "protected_roots": protected_roots,
    }


def default_consumer_profile(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    return {
        "version": PROFILE_VERSION,
        "consumer_id": root.name,
        "truth_roots": {
            "radar_source": "odylith/radar/source",
            "casebook_bugs": "odylith/casebook/bugs",
            "technical_plans": "odylith/technical-plans",
            "component_specs": PUBLIC_PRODUCT_COMPONENT_SPECS_ROOT,
            "runbooks": _default_runbooks_root(repo_root=root),
            "component_registry": "odylith/registry/source/component_registry.v1.json",
        },
        "surface_roots": {
            "product_root": "odylith",
            "runtime_root": ".odylith",
        },
        "odylith_write_policy": _default_odylith_write_policy(repo_root=root),
    }


def _normalize_truth_roots(
    *,
    repo_root: Path,
    defaults: Mapping[str, Any],
    overrides: Mapping[str, Any] | None,
) -> dict[str, str]:
    merged = {str(key): str(value) for key, value in defaults.items() if str(value).strip()}
    if isinstance(overrides, Mapping):
        for key, value in overrides.items():
            token = str(value or "").strip()
            if token:
                merged[str(key)] = token
    for key, default_value in defaults.items():
        default_token = str(default_value or "").strip()
        current_token = str(merged.get(str(key), "")).strip()
        if not current_token:
            merged[str(key)] = default_token
            continue
        if not _path_exists(repo_root=repo_root, token=current_token) and _path_exists(
            repo_root=repo_root,
            token=default_token,
        ):
            merged[str(key)] = default_token
    return merged


def _load_consumer_profile_from_process_cache(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cache_key = str(root)
    signature = _consumer_profile_cache_signature(repo_root=root)
    cached = _PROCESS_CONSUMER_PROFILE_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return _copy_consumer_profile(cached[1])
    path = consumer_profile_path(repo_root=root)
    if not path.is_file():
        profile = default_consumer_profile(repo_root=root)
        _PROCESS_CONSUMER_PROFILE_CACHE[cache_key] = (signature, _copy_consumer_profile(profile))
        return _copy_consumer_profile(profile)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        profile = default_consumer_profile(repo_root=root)
        _PROCESS_CONSUMER_PROFILE_CACHE[cache_key] = (signature, _copy_consumer_profile(profile))
        return _copy_consumer_profile(profile)
    if not isinstance(payload, Mapping):
        profile = default_consumer_profile(repo_root=root)
        _PROCESS_CONSUMER_PROFILE_CACHE[cache_key] = (signature, _copy_consumer_profile(profile))
        return _copy_consumer_profile(profile)
    profile = default_consumer_profile(repo_root=root)
    profile.update({k: v for k, v in payload.items() if k in {"version", "consumer_id"}})
    defaults_truth_roots = dict(profile.get("truth_roots", {}))
    profile["truth_roots"] = _normalize_truth_roots(
        repo_root=root,
        defaults=defaults_truth_roots,
        overrides=payload.get("truth_roots") if isinstance(payload.get("truth_roots"), Mapping) else None,
    )
    if isinstance(payload.get("surface_roots"), Mapping):
        merged = dict(profile.get("surface_roots", {}))
        merged.update({str(k): str(v) for k, v in payload["surface_roots"].items() if str(v).strip()})
        profile["surface_roots"] = merged
    profile["odylith_write_policy"] = _normalize_odylith_write_policy(
        defaults=dict(profile.get("odylith_write_policy", {})),
        overrides=payload.get("odylith_write_policy") if isinstance(payload.get("odylith_write_policy"), Mapping) else None,
    )
    _PROCESS_CONSUMER_PROFILE_CACHE[cache_key] = (signature, _copy_consumer_profile(profile))
    return _copy_consumer_profile(profile)


def load_consumer_profile(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        from odylith.runtime.governance import sync_session as governed_sync_session
    except ImportError:  # pragma: no cover - defensive bootstrap fallback
        return _load_consumer_profile_from_process_cache(repo_root=root)

    session = governed_sync_session.active_sync_session()
    if session is not None and session.repo_root == root:
        cached = session.get_or_compute(
            namespace="consumer_profile",
            key=session.repo_root_token,
            builder=lambda: _load_consumer_profile_from_process_cache(repo_root=root),
        )
        return _copy_consumer_profile(cached)
    return _load_consumer_profile_from_process_cache(repo_root=root)


def write_consumer_profile(*, repo_root: Path, payload: Mapping[str, Any] | None = None) -> Path:
    root = Path(repo_root).resolve()
    profile = default_consumer_profile(repo_root=root)
    path = consumer_profile_path(repo_root=root)
    effective_payload: Mapping[str, Any] | None = payload
    if effective_payload is None and path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, Mapping):
            effective_payload = existing
    if isinstance(effective_payload, Mapping):
        for key in ("version", "consumer_id"):
            if str(effective_payload.get(key, "")).strip():
                profile[key] = str(effective_payload[key]).strip()
        profile["truth_roots"] = _normalize_truth_roots(
            repo_root=root,
            defaults=dict(profile.get("truth_roots", {})),
            overrides=effective_payload.get("truth_roots") if isinstance(effective_payload.get("truth_roots"), Mapping) else None,
        )
        if isinstance(effective_payload.get("surface_roots"), Mapping):
            merged = dict(profile.get("surface_roots", {}))
            merged.update({str(k): str(v) for k, v in effective_payload["surface_roots"].items() if str(v).strip()})
            profile["surface_roots"] = merged
        profile["odylith_write_policy"] = _normalize_odylith_write_policy(
            defaults=dict(profile.get("odylith_write_policy", {})),
            overrides=effective_payload.get("odylith_write_policy")
            if isinstance(effective_payload.get("odylith_write_policy"), Mapping)
            else None,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _clear_consumer_profile_cache(repo_root=root)
    return path


def truth_root_path(*, repo_root: Path, key: str) -> Path:
    profile = load_consumer_profile(repo_root=repo_root)
    token = str(dict(profile.get("truth_roots", {})).get(key, "")).strip()
    return ((Path(repo_root).resolve() / token) if token and not Path(token).is_absolute() else Path(token)).resolve()


def surface_root_path(*, repo_root: Path, key: str) -> Path:
    profile = load_consumer_profile(repo_root=repo_root)
    token = str(dict(profile.get("surface_roots", {})).get(key, "")).strip()
    return ((Path(repo_root).resolve() / token) if token and not Path(token).is_absolute() else Path(token)).resolve()
