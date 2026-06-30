"""Run installed greenfield post-confirm simulations against a local release."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import uuid
from types import SimpleNamespace
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from local_release_smoke import _cleanup_smoke_temp_root, _local_release_env, _serve_directory  # noqa: E402
from greenfield_rescue_smoke import POST_CONFIRM_RESCUE_BUDGET_SECONDS  # noqa: E402
from greenfield_rescue_smoke import installed_auto_rescue_env  # noqa: E402
from greenfield_rescue_smoke import rescue_cli_issues  # noqa: E402
from greenfield_browser_proof_summary import browser_proof_summary  # noqa: E402
from greenfield_browser_surface_proof import BROWSER_SURFACE_PROOF_SCOPE, browser_surface_proof_issues  # noqa: E402
from greenfield_surface_health import INDEX_SHELL_TAB_CONTRACTS  # noqa: E402
from greenfield_surface_health import REQUIRED_RENDERED_SURFACES  # noqa: E402
from greenfield_surface_health import atlas_rendered_asset_count  # noqa: E402
from greenfield_surface_health import rendered_surface_health_issues  # noqa: E402
from greenfield_surface_health import rendered_surface_payload_count  # noqa: E402
from greenfield_matrix_leakage import case_generated_leakage_terms as _case_generated_leakage_terms  # noqa: E402
from greenfield_matrix_leakage import case_preflight_leakage_terms as _case_preflight_leakage_terms  # noqa: E402
from greenfield_matrix_leakage import platform_baseline_required_terms as _platform_baseline_required_terms  # noqa: E402
from greenfield_matrix_leakage import term_present as _term_present  # noqa: E402
from greenfield_matrix_leakage import with_platform_leakage_issues as _with_platform_leakage_issues  # noqa: E402
from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_matrix_proof_scope import natural_rescue_quality_proven  # noqa: E402
from greenfield_matrix_proof_scope import post_confirm_manifest_summary  # noqa: E402
from greenfield_matrix_proof_scope import temp_cleanup_proof  # noqa: E402
from greenfield_post_confirm_matrix_cases import GreenfieldMatrixCase  # noqa: E402
from greenfield_post_confirm_matrix_cases import default_cases  # noqa: E402
from greenfield_post_confirm_matrix_cases import rescue_smoke_case  # noqa: E402
from greenfield_process import run_command_with_group_timeout as _run  # noqa: E402
from greenfield_matrix_types import GreenfieldArtifactCounts  # noqa: E402
from greenfield_matrix_types import GreenfieldMatrixResult  # noqa: E402
from greenfield_matrix_types import GreenfieldQualityVerdict  # noqa: E402
from greenfield_matrix_types import GreenfieldRescueSmokeResult  # noqa: E402
from greenfield_matrix_governed_readback import collect_governed_readback  # noqa: E402
from greenfield_matrix_governed_readback import compass_record_count  # noqa: E402
from greenfield_matrix_governed_readback import program_record_count  # noqa: E402
from greenfield_matrix_governed_readback import release_record_count  # noqa: E402
from greenfield_matrix_quality_scoring import POST_CONFIRM_BUDGET_SECONDS  # noqa: E402
from greenfield_matrix_quality_scoring import QUALITY_SCORE_DIMENSIONS  # noqa: E402
from greenfield_matrix_quality_scoring import build_quality_verdict  # noqa: E402
from greenfield_matrix_quality_scoring import command_excerpt  # noqa: E402
from greenfield_matrix_quality_scoring import count_key  # noqa: E402
from greenfield_matrix_quality_scoring import required_count_minimums  # noqa: E402
from greenfield_matrix_quality_scoring import write_committed  # noqa: E402
import platform_domain_leakage_check as platform_domain_leakage  # noqa: E402
from odylith.runtime.domain_intelligence.greenfield_post_confirm_rescue_probe import RESCUE_PROBE_CODE  # noqa: E402
from odylith.runtime.domain_intelligence.greenfield_post_confirm_structured_rescue_proof import (  # noqa: E402
    STRUCTURED_RESCUE_PROOF_CODE,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_structured_rescue_proof import (  # noqa: E402
    structured_rescue_proof_env,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values  # noqa: E402
from odylith.runtime.artifact_quality.greenfield_package_quality import (  # noqa: E402
    greenfield_rendered_package_quality_issues,
)


COMMAND_TIMEOUT_SECONDS = 300
QUALITY_MATRIX_VERSION = "greenfield-post-confirm-installed-matrix-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
NON_ARTIFACT_MARKDOWN_FILES = {"AGENTS.md", "CLAUDE.md", "INDEX.md", "README.md"}


def run_matrix(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    cases: Sequence[GreenfieldMatrixCase] = (),
    include_browser_proof: bool = False,
) -> tuple[GreenfieldMatrixResult, ...]:
    """Run the real installed greenfield create path for each matrix case."""

    selected_cases = tuple(cases) or default_cases()
    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    _raise_for_ungrounded_required_terms(selected_cases)
    _raise_for_platform_domain_leakage(release_dir, selected_cases)
    platform_baseline_terms = _platform_baseline_required_terms(
        repo_root=REPO_ROOT,
        release_dir=release_dir,
        cases=selected_cases,
    )
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-matrix-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    results: list[GreenfieldMatrixResult] = []
    try:
        for case in selected_cases:
            repo_root = run_root / f"odylith-sim-{case.slug}-{uuid.uuid4().hex[:8]}"
            result = _run_case(
                case=case,
                repo_root=repo_root,
                install_script=install_script,
                base_url=base_url,
                version=version,
                include_browser_proof=include_browser_proof,
                platform_baseline_terms=platform_baseline_terms,
            )
            results.append(result)
            _cleanup_repo_before_next(repo_root)
        results = list(
            _with_platform_leakage_issues(
                repo_root=REPO_ROOT,
                results=results,
                release_dir=release_dir,
            )
        )
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_run_root(run_root)
    return tuple(results)


def _raise_for_platform_domain_leakage(release_dir: Path, cases: Sequence[GreenfieldMatrixCase]) -> None:
    missing_cases = tuple(
        str(getattr(case, "name", "unnamed case")).strip() or "unnamed case"
        for case in cases
        if not _case_preflight_leakage_terms(case)
    )
    if missing_cases:
        names = ", ".join(missing_cases)
        raise RuntimeError(
            "platform domain leakage check cannot prove selected greenfield matrix case vocabulary; "
            f"declare leakage_terms for: {names}"
        )
    terms = tuple(
        sorted(
            {
                term
                for case in cases
                for term in _case_preflight_leakage_terms(case)
            }
        )
    )
    if not terms:
        return
    findings = platform_domain_leakage.scan_platform_custody(
        repo_root=REPO_ROOT,
        dist_dir=release_dir,
        terms=terms,
    )
    if not findings:
        return
    preview = "\n".join(
        f"- {finding.location}:{finding.line}: leaked `{finding.term}`" for finding in findings[:20]
    )
    remaining = len(findings) - 20
    suffix = f"\n- ... {remaining} additional finding(s)" if remaining > 0 else ""
    raise RuntimeError(
        "platform domain leakage check failed for selected greenfield matrix case vocabulary\n"
        f"{preview}{suffix}"
    )


def _raise_for_ungrounded_required_terms(cases: Sequence[GreenfieldMatrixCase]) -> None:
    ungrounded: list[str] = []
    for case in cases:
        source_text = "\n".join(
            str(item or "") for item in (case.prompt, getattr(case, "confirmed_intent_markdown", ""))
        )
        missing = tuple(
            str(term).strip()
            for term in getattr(case, "required_terms", ())
            if str(term).strip() and not _term_present(source_text, str(term))
        )
        if missing:
            ungrounded.append(f"{case.name}: {', '.join(missing)}")
    if ungrounded:
        preview = "\n".join(f"- {row}" for row in ungrounded[:10])
        remaining = len(ungrounded) - 10
        suffix = f"\n- ... {remaining} additional case(s)" if remaining > 0 else ""
        raise RuntimeError(
            "greenfield matrix required_terms must be grounded in the case prompt or confirmed intent\n"
            f"{preview}{suffix}"
        )


def run_rescue_smoke(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
) -> GreenfieldRescueSmokeResult:
    """Prove installed rescue-tier writes and auto-rescue engine escalation."""

    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-rescue-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    try:
        repo_root = run_root / f"odylith-sim-rescue-{uuid.uuid4().hex[:8]}"
        result = _run_rescue_smoke_case(
            repo_root=repo_root,
            install_script=install_script,
            base_url=base_url,
            version=version,
        )
        _cleanup_repo_before_next(repo_root)
        return result
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_run_root(run_root)


def run_natural_rescue_proof(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
) -> GreenfieldRescueSmokeResult:
    """Prove installed host-planned structured rescue repair."""

    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-natural-rescue-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    try:
        repo_root = run_root / f"odylith-sim-natural-rescue-{uuid.uuid4().hex[:8]}"
        result = _run_natural_rescue_case(
            repo_root=repo_root,
            install_script=install_script,
            base_url=base_url,
            version=version,
        )
        _cleanup_repo_before_next(repo_root)
        return result
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_run_root(run_root)


def _run_case(
    *,
    case: GreenfieldMatrixCase,
    repo_root: Path,
    install_script: Path,
    base_url: str,
    version: str,
    include_browser_proof: bool = False,
    platform_baseline_terms: Sequence[str] = (),
) -> GreenfieldMatrixResult:
    repo_root.mkdir(parents=True)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
    install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
    if install.returncode != 0:
        return _failed_case(case, repo_root, "install_failed", install.returncode, install.stderr or install.stdout)
    confirmed_intent = str(case.confirmed_intent_markdown or "").strip()
    if not confirmed_intent:
        propose = _run(
            cwd=repo_root,
            env=env,
            command=["./.odylith/bin/odylith", "greenfield", "propose", "--repo-root", ".", "--prompt", case.prompt],
            timeout=120,
        )
        if propose.returncode != 0:
            return _failed_case(case, repo_root, "propose_failed", propose.returncode, propose.stderr or propose.stdout)
        confirmed_intent = propose.stdout
    intent_path = repo_root / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(confirmed_intent, encoding="utf-8")
    started = time.perf_counter()
    create = _run(
        cwd=repo_root,
        env=env,
        command=[
            "./.odylith/bin/odylith",
            "greenfield",
            "create",
            "--repo-root",
            ".",
            "--prompt",
            case.prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--release",
            "0.0.1",
            "--json",
        ],
        timeout=120,
    )
    create_seconds = round(time.perf_counter() - started, 3)
    payload = _parse_json_object(create.stdout)
    manifest = _as_mapping(payload.get("post_confirm_quality_manifest"))
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    surface_issues = rendered_surface_health_issues(repo_root=repo_root)
    leakage_terms = _case_generated_leakage_terms(
        case=case,
        generated_text=_generated_text(repo_root=repo_root, package=package),
        platform_baseline_terms=platform_baseline_terms,
    )
    browser_surface_proof_attempted = bool(include_browser_proof and create.returncode == 0)
    browser_surface_issues = (
        browser_surface_proof_issues(repo_root=repo_root) if browser_surface_proof_attempted else ()
    )
    quality = build_quality_verdict(
        create_payload=payload,
        package=package,
        counts=counts,
        surface_issues=(*surface_issues, *browser_surface_issues),
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        create_returncode=create.returncode,
        create_seconds=create_seconds,
        create_detail=create.stderr or create.stdout,
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed" if quality.passed else "failed",
        create_seconds=create_seconds,
        counts=counts,
        quality=quality,
        browser_surface_issues=browser_surface_issues,
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        create_returncode=create.returncode,
        failure_detail=command_excerpt(create.stderr or create.stdout) if create.returncode else "",
        create_stdout_excerpt=command_excerpt(create.stdout) if create.returncode else "",
        create_stderr_excerpt=command_excerpt(create.stderr) if create.returncode else "",
        platform_leakage_terms=leakage_terms,
        post_confirm_manifest_summary=post_confirm_manifest_summary(manifest),
    )


def _run_rescue_smoke_case(
    *,
    repo_root: Path,
    install_script: Path,
    base_url: str,
    version: str,
) -> GreenfieldRescueSmokeResult:
    case = rescue_smoke_case()
    repo_root.mkdir(parents=True)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
    install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
    if install.returncode != 0:
        return _rescue_smoke_result(
            create_payload={},
            counts=GreenfieldArtifactCounts(),
            issues=(f"install_failed: {(install.stderr or install.stdout).strip()[:800]}",),
            create_returncode=install.returncode,
        )
    propose = _run(
        cwd=repo_root,
        env=env,
        command=["./.odylith/bin/odylith", "greenfield", "propose", "--repo-root", ".", "--prompt", case.prompt],
        timeout=120,
    )
    if propose.returncode != 0:
        return _rescue_smoke_result(
            create_payload={},
            counts=GreenfieldArtifactCounts(),
            issues=(f"propose_failed: {(propose.stderr or propose.stdout).strip()[:800]}",),
            create_returncode=propose.returncode,
        )
    intent_path = repo_root / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(propose.stdout, encoding="utf-8")
    started = time.perf_counter()
    create = _run(
        cwd=repo_root,
        env=installed_auto_rescue_env(env),
        command=[
            "./.odylith/bin/odylith",
            "greenfield",
            "create",
            "--repo-root",
            ".",
            "--prompt",
            case.prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--release",
            "0.0.1",
            "--repair-tier",
            "auto",
            "--json",
        ],
        timeout=150,
    )
    create_seconds = round(time.perf_counter() - started, 3)
    payload = _parse_json_object(create.stdout)
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    surface_issues = rendered_surface_health_issues(repo_root=repo_root)
    issues = list(
        rescue_cli_issues(
            manifest=_as_mapping(payload.get("post_confirm_quality_manifest")),
            package=package,
            counts=counts,
            count_minimums=required_count_minimums(),
            count_key=count_key,
            write_committed=write_committed,
            as_mapping=_as_mapping,
            package_quality_issues=greenfield_rendered_package_quality_issues,
            create_returncode=create.returncode,
            create_seconds=create_seconds,
            detail=create.stderr or create.stdout,
            expected_requested_tier="auto",
        )
    )
    issues.extend(surface_issues)
    return _rescue_smoke_result(
        create_payload=payload,
        counts=counts,
        issues=tuple(issues),
        create_returncode=create.returncode,
        cli_create_seconds=create_seconds,
    )


def _run_natural_rescue_case(
    *,
    repo_root: Path,
    install_script: Path,
    base_url: str,
    version: str,
) -> GreenfieldRescueSmokeResult:
    case = rescue_smoke_case()
    repo_root.mkdir(parents=True)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
    install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
    if install.returncode != 0:
        return _rescue_smoke_result(
            create_payload={},
            counts=GreenfieldArtifactCounts(),
            issues=(f"install_failed: {(install.stderr or install.stdout).strip()[:800]}",),
            create_returncode=install.returncode,
            proof_scope="real_installed_structured_patch_plan_case",
        )
    propose = _run(
        cwd=repo_root,
        env=env,
        command=["./.odylith/bin/odylith", "greenfield", "propose", "--repo-root", ".", "--prompt", case.prompt],
        timeout=120,
    )
    if propose.returncode != 0:
        return _rescue_smoke_result(
            create_payload={},
            counts=GreenfieldArtifactCounts(),
            issues=(f"propose_failed: {(propose.stderr or propose.stdout).strip()[:800]}",),
            create_returncode=propose.returncode,
            proof_scope="real_installed_structured_patch_plan_case",
        )
    intent_path = repo_root / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(propose.stdout, encoding="utf-8")
    started = time.perf_counter()
    create = _run(
        cwd=repo_root,
        env=_installed_structured_rescue_env(env),
        command=[
            "./.odylith/bin/odylith",
            "greenfield",
            "create",
            "--repo-root",
            ".",
            "--prompt",
            case.prompt,
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--release",
            "0.0.1",
            "--repair-tier",
            "auto",
            "--json",
        ],
        timeout=150,
    )
    create_seconds = round(time.perf_counter() - started, 3)
    payload = _parse_json_object(create.stdout)
    manifest = _as_mapping(payload.get("post_confirm_quality_manifest"))
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    surface_issues = rendered_surface_health_issues(repo_root=repo_root)
    issues = list(
        rescue_cli_issues(
            manifest=manifest,
            package=package,
            counts=counts,
            count_minimums=required_count_minimums(),
            count_key=count_key,
            write_committed=write_committed,
            as_mapping=_as_mapping,
            package_quality_issues=greenfield_rendered_package_quality_issues,
            create_returncode=create.returncode,
            create_seconds=create_seconds,
            detail=create.stderr or create.stdout,
            expected_requested_tier="auto",
            expected_repaired_issue_code=STRUCTURED_RESCUE_PROOF_CODE,
            forbidden_repaired_issue_codes=(RESCUE_PROBE_CODE,),
        )
    )
    issues.extend(_natural_rescue_manifest_issues(manifest))
    issues.extend(surface_issues)
    return _rescue_smoke_result(
        create_payload=payload,
        counts=counts,
        issues=tuple(issues),
        create_returncode=create.returncode,
        cli_create_seconds=create_seconds,
        proof_scope="real_installed_structured_patch_plan_case",
        natural_rescue_quality_proven=not issues,
    )


def _rescue_smoke_result(
    *,
    create_payload: Mapping[str, Any],
    counts: GreenfieldArtifactCounts,
    issues: Sequence[str],
    create_returncode: int,
    cli_create_seconds: float = 0.0,
    proof_scope: str = "synthetic_typed_probe_wiring_only",
    natural_rescue_quality_proven: bool = False,
) -> GreenfieldRescueSmokeResult:
    cleaned_issues = tuple(dict.fromkeys(issue for issue in issues if str(issue).strip()))
    return GreenfieldRescueSmokeResult(
        status="passed" if not cleaned_issues else "failed",
        cli_create_seconds=cli_create_seconds,
        counts=counts,
        issues=cleaned_issues,
        manifest=_as_mapping(create_payload.get("post_confirm_quality_manifest")),
        proof_scope=proof_scope,
        natural_rescue_quality_proven=bool(natural_rescue_quality_proven and not cleaned_issues),
        create_returncode=create_returncode,
    )


def _installed_structured_rescue_env(env: Mapping[str, str]) -> dict[str, str]:
    values = structured_rescue_proof_env(env)
    values["ODYLITH_REASONING_MODE"] = os.environ.get("ODYLITH_REASONING_MODE", "auto")
    values["ODYLITH_REASONING_PROVIDER"] = _structured_rescue_provider()
    values["ODYLITH_REASONING_TIMEOUT_SECONDS"] = os.environ.get("ODYLITH_REASONING_TIMEOUT_SECONDS", "35")
    for key in (
        "ODYLITH_REASONING_MODEL",
        "ODYLITH_REASONING_CODEX_BIN",
        "ODYLITH_REASONING_CODEX_REASONING_EFFORT",
        "ODYLITH_REASONING_CLAUDE_BIN",
        "ODYLITH_REASONING_CLAUDE_REASONING_EFFORT",
    ):
        if key in os.environ:
            values[key] = os.environ[key]
        else:
            values.pop(key, None)
    return values


def _structured_rescue_provider() -> str:
    provider = os.environ.get("ODYLITH_STRUCTURED_RESCUE_PROVIDER") or os.environ.get("ODYLITH_REASONING_PROVIDER")
    provider = str(provider or "").strip()
    if provider and provider != "auto-local":
        return provider
    return "codex-cli"


def _natural_rescue_manifest_issues(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    summary = post_confirm_manifest_summary(manifest)
    issues: list[str] = []
    if summary.get("patchset_summary_source") != "last_repair_patchset_request":
        issues.append("natural rescue proof did not preserve the last repair PatchSet in the final manifest")
    if summary.get("tribunal_patch_plan_status") != "planned":
        issues.append("natural rescue proof did not record a planned Tribunal structured patch plan")
    if int(summary.get("tribunal_patch_plan_operation_count") or 0) <= 0:
        issues.append("natural rescue proof did not record provider-authored patch operations")
    if not str(summary.get("tribunal_patch_plan_provider") or "").strip():
        issues.append("natural rescue proof did not record the structured patch provider")
    if RESCUE_PROBE_CODE in set(summary.get("repaired_issue_codes") or ()):
        issues.append("natural rescue proof used the deterministic rescue probe")
    if STRUCTURED_RESCUE_PROOF_CODE not in set(summary.get("repaired_issue_codes") or ()):
        issues.append(f"natural rescue proof did not repair `{STRUCTURED_RESCUE_PROOF_CODE}`")
    return tuple(issues)


def collect_artifact_package(*, repo_root: Path, create_payload: Mapping[str, Any]) -> Any:
    """Collect generated records in the shape understood by artifact quality gates."""

    accepted_project = _read_json_mapping(repo_root / "odylith/runtime/source/accepted-project.v1.json")
    confirmed_intent = _read_json_mapping(repo_root / ".odylith/runtime/greenfield/confirmed-intent.json")
    proposal = _as_mapping(accepted_project.get("proposal")) or _as_mapping(create_payload.get("proposal")) or confirmed_intent
    source_launch_readback = _as_mapping(accepted_project.get("source_launch"))
    governed_readback = collect_governed_readback(repo_root)
    backlog_result = {
        "idea_files": _read_radar_workstreams(repo_root),
        "backlog_index_text": _read_text(repo_root / "odylith/radar/source/INDEX.md"),
        "validation_gate": _as_mapping(create_payload.get("validation_gate")),
    }
    return SimpleNamespace(
        proposal=proposal,
        release_selector="0.0.1",
        rendered_component_specs=_read_component_specs(repo_root),
        rendered_atlas_sources=_read_atlas_sources(repo_root),
        component_registry_preview=tuple(_mapping_rows(create_payload.get("components"))),
        project_brief_preview=_as_mapping(proposal.get("project_brief")) if isinstance(proposal, Mapping) else {},
        project_brief_record_text=_read_text(repo_root / "odylith/runtime/source/project-brief.v1.md"),
        accepted_project_preview=accepted_project,
        source_launch_readback=source_launch_readback,
        project_dashboard_preview=_read_project_dashboard_payload(repo_root),
        compass_memory_preview=_as_mapping(_as_mapping(create_payload.get("memory")).get("event")),
        governed_readback=governed_readback,
        next_steps_preview=_as_mapping(create_payload.get("next_steps")),
        backlog_result=backlog_result,
        program_result=_as_mapping(create_payload.get("program")),
        prewrite_safety_preview=_as_mapping(create_payload.get("prewrite_safety")),
        release_target_result=_as_mapping(create_payload.get("release_bootstrap")),
        release_assignment_result=_as_mapping(create_payload.get("release_target")),
        release_workstream_ids=tuple(
            _release_workstream_ids(create_payload)
            or _workstream_ids_from_idea_files(_as_mapping(backlog_result.get("idea_files")))
        ),
    )
def collect_artifact_counts(
    *,
    repo_root: Path,
    package: Any,
    required_terms: Sequence[str],
) -> GreenfieldArtifactCounts:
    trace = _read_json_mapping(repo_root / "odylith/radar/traceability-graph.v1.json")
    rendered_text = _generated_text(repo_root=repo_root, package=package)
    return GreenfieldArtifactCounts(
        radar_workstreams=len(_as_mapping(package.backlog_result.get("idea_files"))),
        registry_component_specs=len(_as_mapping(package.rendered_component_specs)),
        atlas_mermaid_sources=len(_as_mapping(package.rendered_atlas_sources)),
        compass_records=compass_record_count(package.governed_readback),
        release_records=release_record_count(package.governed_readback),
        program_records=program_record_count(package.governed_readback),
        project_brief_records=_project_brief_record_count(repo_root=repo_root, package=package),
        trace_nodes=len(trace.get("nodes") or []) if isinstance(trace.get("nodes"), list) else 0,
        trace_workstreams=len(trace.get("workstreams") or []) if isinstance(trace.get("workstreams"), list) else 0,
        rendered_surfaces=sum(1 for path in REQUIRED_RENDERED_SURFACES if _nonempty(repo_root / path)),
        rendered_surface_payloads=rendered_surface_payload_count(repo_root),
        atlas_rendered_assets=atlas_rendered_asset_count(repo_root),
        domain_term_hits=sum(1 for term in required_terms if _term_present(rendered_text, term)),
        required_domain_terms=len(tuple(dict.fromkeys(term.casefold() for term in required_terms if str(term).strip()))),
        project_implementation_prompts=len(
            _mapping_rows(_as_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts"))
        ),
    )

def _failed_case(
    case: GreenfieldMatrixCase,
    repo_root: Path,
    status: str,
    returncode: int,
    detail: str,
) -> GreenfieldMatrixResult:
    package = collect_artifact_package(repo_root=repo_root, create_payload={})
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    quality = GreenfieldQualityVerdict(
        passed=False,
        issues=(f"{status}: {detail.strip()[:800]}",),
        lenses={lens: False for lens in ("product_manager", "architect", "engineer", "domain_expert")},
        scores={dimension: 0 for dimension in QUALITY_SCORE_DIMENSIONS},
        score=0,
        score_explanation=("post-confirm did not complete a governed write transaction",),
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status=status,
        create_seconds=0.0,
        counts=counts,
        quality=quality,
        create_returncode=returncode,
        failure_detail=command_excerpt(detail),
        post_confirm_manifest_summary={},
    )


def _cleanup_repo_before_next(repo_root: Path) -> None:
    _cleanup_smoke_temp_root(repo_root)
    if repo_root.exists():
        shutil.rmtree(repo_root, ignore_errors=True)
    if repo_root.exists():
        raise RuntimeError(f"temporary greenfield simulation repo was not removed: {repo_root}")


def _cleanup_run_root(run_root: Path) -> None:
    _cleanup_smoke_temp_root(run_root)
    if run_root.exists():
        shutil.rmtree(run_root, ignore_errors=True)
    if run_root.exists():
        raise RuntimeError(f"temporary greenfield matrix root was not removed: {run_root}")


def _read_radar_workstreams(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/radar/source"
    if not source.is_dir():
        return {}
    records: dict[str, str] = {}
    for path in sorted(source.rglob("*.md")):
        if path.name in NON_ARTIFACT_MARKDOWN_FILES:
            continue
        records[str(path.relative_to(repo_root))] = _read_text(path)
    return records


def _read_component_specs(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/registry/source/components"
    if not source.is_dir():
        return {}
    specs: dict[str, str] = {}
    for path in sorted(source.rglob("CURRENT_SPEC.md")):
        specs[str(path.relative_to(repo_root))] = _read_text(path)
    return specs


def _read_atlas_sources(repo_root: Path) -> dict[str, str]:
    source = repo_root / "odylith/atlas/source"
    if not source.is_dir():
        return {}
    return {
        str(path.relative_to(repo_root)): _read_text(path)
        for path in sorted(source.glob("*.mmd"))
    }


def _project_brief_record_count(*, repo_root: Path, package: Any) -> int:
    text = _read_text(repo_root / "odylith/runtime/source/project-brief.v1.md")
    if not text:
        text = str(getattr(package, "project_brief_record_text", "") or "")
    required_markers = ("## Brief", "## Project Design Board", "## Governance Package")
    return 1 if text and all(marker in text for marker in required_markers) else 0


def _generated_text(*, repo_root: Path, package: Any) -> str:
    del repo_root
    chunks: list[str] = []
    chunks.extend(_as_mapping(package.backlog_result.get("idea_files")).values())
    chunks.append(str(package.backlog_result.get("backlog_index_text") or ""))
    chunks.extend(_as_mapping(package.rendered_component_specs).values())
    chunks.extend(_as_mapping(package.rendered_atlas_sources).values())
    chunks.append(str(getattr(package, "project_brief_record_text", "") or ""))
    chunks.extend(text_values(getattr(package, "source_launch_readback", None)))
    for row in _mapping_rows(_as_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts")):
        chunks.extend(text_values(row))
    return "\n".join(str(item) for item in chunks).casefold()


def _read_project_dashboard_payload(repo_root: Path) -> Mapping[str, Any]:
    shell_payload = _read_tooling_payload(repo_root)
    project = shell_payload.get("project_intelligence")
    return project if isinstance(project, Mapping) else {}


def _read_tooling_payload(repo_root: Path) -> Mapping[str, Any]:
    payload_path = repo_root / "odylith/tooling-payload.v1.js"
    text = _read_text(payload_path).strip()
    if not text or "__ODYLITH_TOOLING_DATA__" not in text:
        return {}
    json_start = text.find("{")
    if json_start < 0:
        return {}
    try:
        payload, _end = json.JSONDecoder().raw_decode(text[json_start:])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _release_workstream_ids(payload: Mapping[str, Any]) -> tuple[str, ...]:
    release_target = _as_mapping(payload.get("release_target"))
    workstreams: list[str] = []
    for event in _mapping_rows(release_target.get("events")):
        token = str(event.get("workstream_id", "")).strip()
        if token:
            workstreams.append(token)
    return tuple(dict.fromkeys(workstreams))


def _workstream_ids_from_idea_files(files: Mapping[Any, Any]) -> tuple[str, ...]:
    ids: list[str] = []
    for token in files:
        stem = Path(str(token)).stem.strip().upper()
        if stem.startswith("B-") and len(stem) > 2:
            ids.append(stem)
    return tuple(dict.fromkeys(ids))


def _nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _parse_json_object(value: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    return tuple(row for row in value if isinstance(row, Mapping)) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _version_from_pyproject() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return "0.1.15"


def _default_temp_parent() -> Path:
    mock = Path("/Users/freedom/mock")
    if mock.is_dir():
        return mock
    return Path(tempfile.gettempdir())


def _print_human_summary(results: Sequence[GreenfieldMatrixResult]) -> None:
    print(f"greenfield post-confirm installed matrix: {QUALITY_MATRIX_VERSION}")
    for result in results:
        print(
            " - {name}: {status}, score={score}/10, {seconds:.3f}s, issues={issues}, "
            "radar={radar}, registry={registry}, atlas={atlas}, trace_nodes={trace_nodes}".format(
                name=result.name,
                status=result.status,
                score=result.quality.score,
                seconds=result.create_seconds,
                issues=len(result.quality.issues),
                radar=result.counts.radar_workstreams,
                registry=result.counts.registry_component_specs,
                atlas=result.counts.atlas_mermaid_sources,
                trace_nodes=result.counts.trace_nodes,
            )
        )
        if result.quality.issues:
            for issue in result.quality.issues:
                print(f"   issue: {issue}")
        for explanation in result.quality.score_explanation:
            print(f"   score: {explanation}")


def _print_rescue_summary(rescue: GreenfieldRescueSmokeResult | None) -> None:
    if rescue is None:
        return
    print(
        " - rescue smoke ({scope}): {status}, cli_auto_rescue={cli:.3f}s, issues={issues}, "
        "radar={radar}, registry={registry}, atlas={atlas}, trace_nodes={trace_nodes}".format(
            scope=rescue.proof_scope,
            status=rescue.status,
            cli=rescue.cli_create_seconds,
            issues=len(rescue.issues),
            radar=rescue.counts.radar_workstreams,
            registry=rescue.counts.registry_component_specs,
            atlas=rescue.counts.atlas_mermaid_sources,
            trace_nodes=rescue.counts.trace_nodes,
        )
    )
    for issue in rescue.issues:
        print(f"   issue: {issue}")


def _platform_leakage_proof_summary(results: Sequence[GreenfieldMatrixResult]) -> dict[str, Any]:
    terms = sorted(
        {
            str(term).strip()
            for result in results
            for term in result.platform_leakage_terms
            if str(term).strip()
        }
    )
    issues = tuple(
        dict.fromkeys(
            issue
            for result in results
            for issue in result.platform_leakage_issues
            if str(issue).strip()
        )
    )
    return {
        "status": "passed" if not issues else "failed",
        "scope": "generated_artifact_readback_terms_against_platform_source_and_dist",
        "term_count": len(terms),
        "terms": terms,
        "issues": list(issues),
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run installed greenfield post-confirm release simulations.")
    parser.add_argument("--dist-dir", required=True, help="Local release asset directory containing install.sh.")
    parser.add_argument("--version", default=_version_from_pyproject())
    parser.add_argument("--temp-parent", default=str(_default_temp_parent()))
    parser.add_argument(
        "--case-file",
        action="append",
        default=None,
        help=(
            "JSON file containing fresh high-variance GreenfieldMatrixCase records. "
            "Repeatable; when present, these cases replace the maintained default catalog."
        ),
    )
    parser.add_argument(
        "--include-rescue-smoke",
        action="store_true",
        default=True,
        help="Prove installed CLI auto-rescue governed writes. Enabled by default.",
    )
    parser.add_argument(
        "--skip-rescue-smoke",
        action="store_false",
        dest="include_rescue_smoke",
        help="Skip rescue smoke for local debugging only; this is not release proof.",
    )
    parser.add_argument(
        "--include-natural-rescue-proof",
        action="store_true",
        help="Prove installed host-planned structured semantic rescue.",
    )
    parser.add_argument(
        "--skip-natural-rescue-proof",
        action="store_false",
        dest="include_natural_rescue_proof",
        help="Skip host-planned rescue proof for local debugging only; this is not release proof.",
    )
    parser.add_argument(
        "--include-browser-proof",
        action="store_true",
        help="Run headless generated browser state proof against every generated matrix repo.",
    )
    parser.add_argument(
        "--allow-skipped-browser-proof",
        action="store_true",
        help="Allow omitted browser proof for local debugging only; this is not release proof.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path where the full matrix proof payload should be persisted.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    selected_cases = _load_cli_case_files(args.case_file or ())
    results = run_matrix(
        dist_dir=Path(args.dist_dir),
        version=str(args.version),
        temp_parent=Path(args.temp_parent),
        cases=selected_cases,
        include_browser_proof=bool(args.include_browser_proof),
    )
    rescue = (
        run_rescue_smoke(
            dist_dir=Path(args.dist_dir),
            version=str(args.version),
            temp_parent=Path(args.temp_parent),
        )
        if bool(args.include_rescue_smoke)
        else None
    )
    natural_rescue = (
        run_natural_rescue_proof(
            dist_dir=Path(args.dist_dir),
            version=str(args.version),
            temp_parent=Path(args.temp_parent),
        )
        if bool(args.include_natural_rescue_proof)
        else None
    )
    browser_proof = browser_proof_summary(results, include_browser_proof=bool(args.include_browser_proof))
    platform_leakage_proof = _platform_leakage_proof_summary(results)
    cleanup_proof = temp_cleanup_proof(Path(args.temp_parent))
    natural_rescue_proven = natural_rescue_quality_proven(results) or bool(
        natural_rescue and natural_rescue.natural_rescue_quality_proven
    )
    browser_status = str(browser_proof.get("status") or "").strip()
    browser_passed = browser_status == "passed" or (
        browser_status == "skipped" and bool(args.allow_skipped_browser_proof)
    )
    platform_leakage_passed = str(platform_leakage_proof.get("status") or "").strip() == "passed"
    cleanup_passed = str(cleanup_proof.get("status") or "").strip() == "passed"
    passed = (
        all(result.quality.passed for result in results)
        and (rescue is None or rescue.passed)
        and (natural_rescue is None or natural_rescue.passed)
        and browser_passed
        and platform_leakage_passed
        and cleanup_passed
    )
    payload = {
        "version": QUALITY_MATRIX_VERSION,
        "status": "passed" if passed else "failed",
        "proof_scope": {
            "standard_path": "real_installed_greenfield_post_confirm_quality_matrix",
            "rescue_path": "synthetic_typed_probe_wiring_only",
            "natural_rescue_path": (
                "real_installed_structured_patch_plan_case"
                if natural_rescue_proven
                else "not_proven"
            ),
            "natural_rescue_quality_proven": natural_rescue_proven,
            "browser_surface_proof": (
                BROWSER_SURFACE_PROOF_SCOPE if bool(args.include_browser_proof) else "not_requested"
            ),
        },
        "results": [result.to_dict() for result in results],
        "browser_surface_proof": browser_proof,
        "platform_domain_leakage_proof": platform_leakage_proof,
        "temp_cleanup_proof": cleanup_proof,
    }
    if rescue is not None:
        payload["rescue_smoke"] = rescue.to_dict()
    if natural_rescue is not None:
        payload["natural_rescue_proof"] = natural_rescue.to_dict()
    if str(args.output_json or "").strip():
        output_path = Path(str(args.output_json)).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human_summary(results)
        _print_rescue_summary(rescue)
        _print_rescue_summary(natural_rescue)
    return 0 if payload["status"] == "passed" else 1


def _load_cli_case_files(case_files: Sequence[str]) -> tuple[GreenfieldMatrixCase, ...]:
    cases: list[GreenfieldMatrixCase] = []
    for case_file in case_files:
        token = str(case_file or "").strip()
        if token:
            cases.extend(load_case_file(Path(token)))
    return tuple(cases)


if __name__ == "__main__":
    raise SystemExit(main())
