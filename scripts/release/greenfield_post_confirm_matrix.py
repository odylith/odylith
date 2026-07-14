"""Run installed greenfield post-confirm simulations against a local release."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
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
from greenfield_matrix_leakage import platform_baseline_required_terms as _platform_baseline_required_terms  # noqa: E402
from greenfield_matrix_leakage import term_present as _term_present  # noqa: E402
from greenfield_matrix_leakage import with_platform_leakage_issues as _with_platform_leakage_issues  # noqa: E402
from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_matrix_case_file import ungrounded_required_terms  # noqa: E402
from greenfield_matrix_campaign import MatrixCampaignConfig  # noqa: E402
from greenfield_matrix_campaign import MatrixTelemetryWriter  # noqa: E402
from greenfield_matrix_campaign import campaign_phase_from_value  # noqa: E402
from greenfield_matrix_campaign import campaign_summary  # noqa: E402
from greenfield_matrix_campaign import case_completed_event  # noqa: E402
from greenfield_matrix_campaign import case_started_event  # noqa: E402
from greenfield_matrix_campaign import positive_int  # noqa: E402
from greenfield_matrix_campaign import proof_tier_from_value  # noqa: E402
from greenfield_matrix_campaign import required_stressors_from_values  # noqa: E402
from greenfield_matrix_campaign import stop_reason  # noqa: E402
from greenfield_matrix_preflight import matrix_preflight_failures  # noqa: E402
from greenfield_matrix_package_evidence import package_evidence_findings  # noqa: E402
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
from greenfield_matrix_quality_scoring import write_transaction_custody_issues  # noqa: E402
from greenfield_tooling_payload_reader import read_tooling_payload_js  # noqa: E402
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
import platform_domain_leakage_check as platform_domain_leakage  # noqa: E402


COMMAND_TIMEOUT_SECONDS = 300
QUALITY_MATRIX_VERSION = "greenfield-post-confirm-installed-matrix-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
NON_ARTIFACT_MARKDOWN_FILES = {"AGENTS.md", "CLAUDE.md", "INDEX.md", "README.md"}
EVIDENCE_EXCERPT_CHARS = 280
EVIDENCE_ARTIFACT_LIMIT = 80
SCORED_REQUIRED_TERM_SURFACES = frozenset(
    {
        "Radar workstream",
        "Registry component spec",
        "Atlas Mermaid",
        "Project brief",
        "Accepted source launch",
        "Project implementation prompt",
    }
)
INSTALL_MODES = ("full", "seeded")


def run_matrix(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    cases: Sequence[GreenfieldMatrixCase] = (),
    include_browser_proof: bool = False,
    install_mode: str = "full",
    telemetry_jsonl: Path | None = None,
    campaign_phase: str = "single-matrix",
    proof_tier: str = "release",
    stop_after_failures: int = 0,
    stop_after_cluster_failures: int = 0,
    required_stressors: Sequence[str] = (),
    incremental_output_json: Path | None = None,
    allow_partial_stressor_coverage: bool = False,
) -> tuple[GreenfieldMatrixResult, ...]:
    """Run the real installed greenfield create path for each matrix case."""

    selected_cases = tuple(cases) or default_cases()
    install_mode = _validated_install_mode(install_mode)
    campaign_config = MatrixCampaignConfig(
        phase=campaign_phase_from_value(campaign_phase),
        proof_tier=proof_tier_from_value(proof_tier),
        telemetry_jsonl=Path(telemetry_jsonl).expanduser().resolve() if telemetry_jsonl else None,
        stop_after_failures=positive_int(stop_after_failures),
        stop_after_cluster_failures=positive_int(stop_after_cluster_failures),
        required_stressors=tuple(required_stressors),
    )
    telemetry = MatrixTelemetryWriter(campaign_config.telemetry_jsonl)
    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    results: list[GreenfieldMatrixResult] = []
    telemetry.emit(
        "run_started",
        {
            "phase": campaign_config.phase,
            "proof_tier": campaign_config.proof_tier,
            "case_count": len(selected_cases),
            "install_mode": install_mode,
            "include_browser_proof": bool(include_browser_proof),
            "stop_after_failures": campaign_config.stop_after_failures,
            "stop_after_cluster_failures": campaign_config.stop_after_cluster_failures,
            "required_stressors": list(campaign_config.required_stressors),
        },
    )
    _flush_incremental_matrix_payload(
        output_json=incremental_output_json,
        cases=selected_cases,
        results=results,
        config=campaign_config,
        status="running",
        stopped_reason="",
    )
    preflight_results = _matrix_preflight_results(
        release_dir=release_dir,
        cases=selected_cases,
        required_stressors=campaign_config.required_stressors,
        temp_parent=Path(temp_parent),
        enforce_required_stressors=not allow_partial_stressor_coverage,
    )
    if preflight_results:
        if telemetry_jsonl is None and incremental_output_json is None:
            raise RuntimeError(_preflight_failure_error(preflight_results))
        reason = "matrix-preflight-failed"
        results.extend(preflight_results)
        telemetry.emit(
            "preflight_failed",
            {
                "reason": reason,
                "failure_count": len(results),
                "cases": [
                    _case_evidence_manifest_case(result)
                    for result in results
                    if isinstance(result.evidence, Mapping)
                ],
            },
        )
        for index, result in enumerate(results, start=1):
            telemetry.emit("case_completed", case_completed_event(result=result, index=index, total=len(selected_cases)))
        telemetry.emit("run_stopped", {"reason": reason, "completed_case_count": len(results)})
        telemetry.emit(
            "run_finished",
            {
                "summary": campaign_summary(
                    cases=selected_cases,
                    results=results,
                    config=campaign_config,
                    stopped_reason=reason,
                )
            },
        )
        _flush_incremental_matrix_payload(
            output_json=incremental_output_json,
            cases=selected_cases,
            results=results,
            config=campaign_config,
            status="failed",
            stopped_reason=reason,
        )
        return tuple(results)
    platform_baseline_terms = _platform_baseline_required_terms(
        repo_root=REPO_ROOT,
        release_dir=release_dir,
        cases=selected_cases,
    )
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-matrix-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    stopped_reason = ""
    try:
        seed_repo = None
        if install_mode == "seeded":
            seed_repo = run_root / f"odylith-seed-install-{uuid.uuid4().hex[:8]}"
            seed_install = _prepare_seed_repo(
                seed_repo=seed_repo,
                install_script=install_script,
                base_url=base_url,
                version=version,
            )
            if seed_install.returncode != 0:
                results = [
                    _failed_case(
                        case,
                        seed_repo,
                        "seed_install_failed",
                        seed_install.returncode,
                        seed_install.stderr or seed_install.stdout,
                    )
                    for case in selected_cases
                ]
                telemetry.emit(
                    "run_stopped",
                    {"reason": "seed-install-failed", "completed_case_count": len(results)},
                )
                telemetry.emit(
                    "run_finished",
                    {
                        "summary": campaign_summary(
                            cases=selected_cases,
                            results=results,
                            config=campaign_config,
                            stopped_reason="seed-install-failed",
                        )
                    },
                )
                _flush_incremental_matrix_payload(
                    output_json=incremental_output_json,
                    cases=selected_cases,
                    results=results,
                    config=campaign_config,
                    status="failed",
                    stopped_reason="seed-install-failed",
                )
                return tuple(results)
        for index, case in enumerate(selected_cases, start=1):
            telemetry.emit("case_started", case_started_event(case=case, index=index, total=len(selected_cases)))
            repo_root = run_root / f"odylith-sim-{case.slug}-{uuid.uuid4().hex[:8]}"
            try:
                if seed_repo is not None:
                    _clone_seed_repo(seed_repo=seed_repo, repo_root=repo_root, version=version)
                result = _run_case(
                    case=case,
                    repo_root=repo_root,
                    install_script=install_script,
                    base_url=base_url,
                    version=version,
                    include_browser_proof=include_browser_proof,
                    platform_baseline_terms=platform_baseline_terms,
                    skip_install=seed_repo is not None,
                    install_mode=install_mode,
                )
                result = _with_case_platform_leakage_issues(result=result, release_dir=release_dir)
                reason = stop_reason((*results, result), campaign_config)
            except Exception as exc:
                result = _failed_case(
                    case,
                    repo_root,
                    "case-execution-exception",
                    1,
                    str(exc),
                )
                reason = "case-execution-exception"
            results.append(result)
            _flush_incremental_matrix_payload(
                output_json=incremental_output_json,
                cases=selected_cases,
                results=results,
                config=campaign_config,
                status="failed" if reason else "running",
                stopped_reason=reason,
            )
            try:
                _cleanup_repo_before_next(repo_root)
            except RuntimeError as exc:
                result = _result_with_cleanup_issue(result, str(exc))
                results[-1] = result
                reason = "temp-cleanup-failed"
                _flush_incremental_matrix_payload(
                    output_json=incremental_output_json,
                    cases=selected_cases,
                    results=results,
                    config=campaign_config,
                    status="failed",
                    stopped_reason=reason,
            )
            telemetry.emit("case_completed", case_completed_event(result=result, index=index, total=len(selected_cases)))
            if reason:
                stopped_reason = reason
                telemetry.emit("run_stopped", {"reason": reason, "completed_case_count": len(results)})
                break
        final_stop_reason = stopped_reason or stop_reason(results, campaign_config)
        telemetry.emit(
            "run_finished",
            {
                "summary": campaign_summary(
                    cases=selected_cases,
                    results=results,
                    config=campaign_config,
                    stopped_reason=final_stop_reason,
                )
            },
        )
        _flush_incremental_matrix_payload(
            output_json=incremental_output_json,
            cases=selected_cases,
            results=results,
            config=campaign_config,
            status=_incremental_matrix_status(results, selected_cases, campaign_config),
            stopped_reason=final_stop_reason,
        )
    finally:
        server.shutdown()
        server.server_close()
        _cleanup_run_root(run_root)
    return tuple(results)


def _matrix_preflight_results(
    *,
    release_dir: Path,
    cases: Sequence[GreenfieldMatrixCase],
    required_stressors: Sequence[str],
    temp_parent: Path,
    enforce_required_stressors: bool = True,
) -> tuple[GreenfieldMatrixResult, ...]:
    failures = matrix_preflight_failures(
        repo_root=REPO_ROOT,
        release_dir=release_dir,
        cases=cases,
        required_stressors=required_stressors,
        enforce_required_stressors=enforce_required_stressors,
    )
    if not failures:
        return ()
    preflight_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-preflight-{uuid.uuid4().hex[:8]}"
    return tuple(
        _failed_case(
            failure.case,
            preflight_root,
            "preflight_failed",
            1,
            failure.detail,
        )
        for failure in failures
    )


def _preflight_failure_error(results: Sequence[GreenfieldMatrixResult]) -> str:
    details = tuple(str(result.failure_detail or "").strip() for result in results if str(result.failure_detail or "").strip())
    joined = "; ".join(details)
    if "platform custody leaked selected case vocabulary" in joined:
        return "selected greenfield matrix case vocabulary leaked into platform custody: " + joined
    if "no platform-distinctive sentinel" in joined:
        return "selected greenfield matrix case vocabulary lacks platform-distinctive sentinels: " + joined
    if "leakage_terms are required" in joined:
        return "custom greenfield matrix cases must declare leakage_terms before platform leakage proof: " + joined
    if "required terms are not grounded" in joined:
        return "required_terms must be grounded in the case prompt or edit evidence: " + joined
    return "greenfield matrix preflight failed: " + joined


def _raise_for_ungrounded_required_terms(cases: Sequence[GreenfieldMatrixCase]) -> None:
    failures: list[str] = []
    for case in cases:
        missing = ungrounded_required_terms(
            prompt=case.prompt,
            confirmed_intent_markdown=str(getattr(case, "confirmed_intent_markdown", "") or ""),
            required_terms=tuple(getattr(case, "required_terms", ()) or ()),
        )
        if missing:
            failures.append(f"{case.name}: {', '.join(missing)}")
    if failures:
        raise RuntimeError("required terms are not grounded in the case prompt or edit evidence: " + "; ".join(failures))


def _case_evidence_manifest_case(result: GreenfieldMatrixResult) -> Mapping[str, Any]:
    evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
    case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
    return case


def _with_case_platform_leakage_issues(
    *,
    result: GreenfieldMatrixResult,
    release_dir: Path,
) -> GreenfieldMatrixResult:
    checked = _with_platform_leakage_issues(
        repo_root=REPO_ROOT,
        results=(result,),
        release_dir=release_dir,
    )
    return checked[0] if checked else result


def _result_with_cleanup_issue(result: GreenfieldMatrixResult, detail: str) -> GreenfieldMatrixResult:
    issue = f"temp cleanup failed before next greenfield simulation: {command_excerpt(detail, limit=800)}"
    quality = replace(
        result.quality,
        passed=False,
        issues=tuple(dict.fromkeys((*result.quality.issues, issue))),
        score=0,
        score_explanation=tuple(
            dict.fromkeys(
                (
                    "temporary simulation cleanup failed; release proof cannot pass with leaked temp roots",
                    *result.quality.score_explanation,
                )
            )
        ),
    )
    return replace(
        result,
        status="failed",
        quality=quality,
        failure_detail=command_excerpt(detail, limit=1200),
    )


def _flush_incremental_matrix_payload(
    *,
    output_json: Path | None,
    cases: Sequence[GreenfieldMatrixCase],
    results: Sequence[GreenfieldMatrixResult],
    config: MatrixCampaignConfig,
    status: str,
    stopped_reason: str,
) -> None:
    if output_json is None:
        return
    path = Path(output_json).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": QUALITY_MATRIX_VERSION,
        "status": str(status),
        "incremental": True,
        "results": [result.to_dict() for result in results],
        "campaign": campaign_summary(
            cases=cases,
            results=results,
            config=config,
            stopped_reason=stopped_reason,
        ),
        "release_readiness_boundary": (
            "incremental matrix payloads are live discovery/release telemetry; final proof is available only after main exits"
        ),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _incremental_matrix_status(
    results: Sequence[GreenfieldMatrixResult],
    cases: Sequence[GreenfieldMatrixCase],
    config: MatrixCampaignConfig,
) -> str:
    reason = stop_reason(results, config)
    if reason:
        return "failed"
    if len(results) < len(cases):
        return "running"
    return "passed" if all(result.quality.passed for result in results) else "failed"


def _raise_for_invalid_campaign_policy(
    *,
    config: MatrixCampaignConfig,
    install_mode: str,
    include_browser_proof: bool,
    include_rescue_smoke: bool,
    include_natural_rescue_proof: bool,
    allow_skipped_browser_proof: bool,
    allow_partial_stressor_coverage: bool = False,
) -> None:
    if config.proof_tier != "release":
        return
    violations: list[str] = []
    if install_mode != "full":
        violations.append("release proof must use full install mode")
    if not include_browser_proof:
        violations.append("release proof must include browser proof")
    if not include_rescue_smoke:
        violations.append("release proof must include installed rescue smoke")
    if not include_natural_rescue_proof:
        violations.append("release proof must include natural rescue proof")
    if allow_skipped_browser_proof:
        violations.append("release proof cannot allow skipped browser proof")
    if allow_partial_stressor_coverage:
        violations.append("release proof cannot allow partial stressor coverage")
    if config.stop_after_failures:
        violations.append("release proof cannot stop after a failure threshold")
    if config.stop_after_cluster_failures:
        violations.append("release proof cannot stop after a cluster threshold")
    if violations:
        raise RuntimeError("invalid greenfield release proof policy: " + "; ".join(violations))


def _validated_install_mode(value: str) -> str:
    mode = str(value or "full").strip().casefold()
    if mode not in INSTALL_MODES:
        allowed = ", ".join(INSTALL_MODES)
        raise RuntimeError(f"greenfield matrix install mode must be one of: {allowed}")
    return mode


def _prepare_seed_repo(
    *,
    seed_repo: Path,
    install_script: Path,
    base_url: str,
    version: str,
) -> Any:
    seed_repo.mkdir(parents=True, exist_ok=False)
    env = _local_release_env(base_url=base_url, version=version)
    _run(cwd=seed_repo, env=env, command=["git", "init"], timeout=60)
    return _run(cwd=seed_repo, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)


def _clone_seed_repo(*, seed_repo: Path, repo_root: Path, version: str) -> None:
    if repo_root.exists():
        raise RuntimeError(f"seeded greenfield matrix repo already exists: {repo_root}")
    shutil.copytree(seed_repo, repo_root, symlinks=True, ignore=_seed_clone_ignore)
    runtime_root = repo_root / ".odylith/runtime"
    versions_root = runtime_root / "versions"
    versions_root.mkdir(parents=True, exist_ok=True)
    seed_runtime = (seed_repo / f".odylith/runtime/versions/{version}").resolve()
    linked_runtime = versions_root / version
    if linked_runtime.exists() or linked_runtime.is_symlink():
        linked_runtime.unlink()
    linked_runtime.symlink_to(seed_runtime, target_is_directory=True)
    current = runtime_root / "current"
    if current.exists() or current.is_symlink():
        if current.is_dir() and not current.is_symlink():
            shutil.rmtree(current)
        else:
            current.unlink()
    current.symlink_to(Path("versions") / version, target_is_directory=True)
    _run(cwd=repo_root, env=dict(os.environ), command=["git", "init"], timeout=60)


def _seed_clone_ignore(directory: str, names: Sequence[str]) -> set[str]:
    path = Path(directory)
    blocked: set[str] = set()
    if path.name == ".git":
        return set(names)
    if ".git" in names:
        blocked.add(".git")
    if path.parts[-3:] == (".odylith", "runtime", "versions"):
        blocked.update(names)
    if path.parts[-2:] == (".odylith", "runtime"):
        blocked.add("current")
    return blocked


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
    skip_install: bool = False,
    install_mode: str = "full",
) -> GreenfieldMatrixResult:
    env = _local_release_env(base_url=base_url, version=version)
    if not skip_install:
        repo_root.mkdir(parents=True)
        _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
        install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
        if install.returncode != 0:
            return _failed_case(case, repo_root, "install_failed", install.returncode, install.stderr or install.stdout)
    elif not (repo_root / ".odylith/bin/odylith").is_file():
        return _failed_case(case, repo_root, "seed_clone_failed", 1, "seeded repo clone is missing .odylith/bin/odylith")
    create, create_seconds = _run_compiled_greenfield_create(
        repo_root=repo_root,
        env=env,
        prompt=case.prompt,
        edit_evidence=str(case.confirmed_intent_markdown or ""),
        timeout=120,
    )
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
        surface_issues=surface_issues,
        browser_surface_issues=browser_surface_issues,
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        browser_surface_proof_required=include_browser_proof,
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
        evidence=_case_evidence_manifest(
            case=case,
            repo_root=repo_root,
            package=package,
            create_payload=payload,
            quality=quality,
            install_script=install_script,
            version=version,
            install_mode=install_mode,
            browser_surface_proof_attempted=browser_surface_proof_attempted,
            browser_surface_proof_required=include_browser_proof,
            browser_surface_issues=browser_surface_issues,
        ),
    )


def _run_compiled_greenfield_create(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    prompt: str,
    timeout: int,
    edit_evidence: str = "",
) -> tuple[Any, float]:
    propose_command = [
        "./.odylith/bin/odylith",
        "greenfield",
        "propose",
        "--repo-root",
        ".",
        "--prompt",
        prompt,
        "--format",
        "json",
    ]
    if edit_evidence.strip():
        propose_command.extend(["--edit", edit_evidence])
    proposed = _run(cwd=repo_root, env=env, command=propose_command, timeout=timeout)
    if proposed.returncode != 0:
        return proposed, 0.0
    proposed_payload = _parse_json_object(proposed.stdout)
    transaction_summary = _as_mapping(proposed_payload.get("product_create_transaction"))
    transaction_hash = str(transaction_summary.get("transaction_hash") or "").strip()
    transaction_file = str(proposed_payload.get("transaction_file") or "").strip()
    proposal_mode = str(proposed_payload.get("mode") or "").strip()
    if not transaction_hash or (proposal_mode == "product_create_transaction" and not transaction_file):
        return (
            SimpleNamespace(
                returncode=2,
                stdout=json.dumps(
                    {
                        "mode": "error",
                        "error": "greenfield propose did not return a ProductCreateTransaction hash and transaction file",
                    },
                    sort_keys=True,
                ),
                stderr="",
            ),
            0.0,
        )
    if not transaction_file:
        transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
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
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
            "--json",
        ],
        timeout=timeout,
    )
    return create, round(time.perf_counter() - started, 3)


def _case_evidence_manifest(
    *,
    case: GreenfieldMatrixCase,
    repo_root: Path,
    package: Any,
    create_payload: Mapping[str, Any],
    quality: GreenfieldQualityVerdict,
    install_script: Path,
    version: str,
    install_mode: str,
    browser_surface_proof_attempted: bool,
    browser_surface_proof_required: bool,
    browser_surface_issues: Sequence[str],
) -> Mapping[str, Any]:
    manifest = _as_mapping(create_payload.get("post_confirm_quality_manifest"))
    artifact_texts = _artifact_text_inventory(package)
    artifacts = _artifact_inventory(artifact_texts)
    all_grounding = _required_term_grounding(case=case, artifacts=artifact_texts)
    scored_grounding = _required_term_grounding(
        case=case,
        artifacts=[
            artifact
            for artifact in artifact_texts
            if str(artifact.get("surface", "")) in SCORED_REQUIRED_TERM_SURFACES
        ],
    )
    return {
        "version": "odylith.greenfield.matrix.case_evidence.v1",
        "case": _case_evidence(case),
        "release": {
            "version": str(version),
            "install_mode": str(install_mode),
            "install_script_sha256": _sha256_file(install_script),
        },
        "artifacts": artifacts,
        "required_term_grounding": all_grounding,
        "required_term_scored_grounding": scored_grounding,
        "required_term_distribution_findings": _required_term_distribution_findings(
            all_grounding=all_grounding,
            scored_grounding=scored_grounding,
        ),
        "quality_findings": _quality_finding_evidence(
            package=package,
            quality=quality,
            browser_surface_issues=browser_surface_issues,
        ),
        "browser_surface_proof": {
            "required": bool(browser_surface_proof_required),
            "attempted": bool(browser_surface_proof_attempted),
            "issues": list(browser_surface_issues),
        },
        "post_confirm_manifest_summary": post_confirm_manifest_summary(manifest),
    }


def _failed_case_evidence_manifest(
    case: GreenfieldMatrixCase,
    status: str,
    returncode: int,
    detail: str,
) -> Mapping[str, Any]:
    return {
        "version": "odylith.greenfield.matrix.case_evidence.v1",
        "case": _case_evidence(case),
        "failure": {
            "status": str(status),
            "returncode": int(returncode),
            "detail_excerpt": command_excerpt(detail, limit=1200),
        },
    }


def _case_evidence(case: GreenfieldMatrixCase) -> Mapping[str, Any]:
    return {
        "id": str(getattr(case, "case_id", "") or case.slug),
        "name": case.name,
        "slug": case.slug,
        "source_file": str(getattr(case, "source_file", "") or ""),
        "tags": list(getattr(case, "tags", ()) or ()),
        "stressors": list(getattr(case, "stressors", ()) or ()),
        "prompt_sha256": _sha256_text(case.prompt),
        "edit_evidence_sha256": _sha256_text(getattr(case, "confirmed_intent_markdown", "") or ""),
        "required_terms": list(case.required_terms),
        "leakage_terms": list(getattr(case, "leakage_terms", ()) or ()),
    }


def _artifact_text_inventory(package: Any) -> list[Mapping[str, str]]:
    records: list[Mapping[str, str]] = []
    records.extend(
        _artifact_text_records(
            "Radar workstream",
            _as_mapping(package.backlog_result.get("idea_files")),
        )
    )
    records.extend(_artifact_text_records("Registry component spec", _as_mapping(package.rendered_component_specs)))
    records.extend(_artifact_text_records("Atlas Mermaid", _as_mapping(package.rendered_atlas_sources)))
    project_brief = str(getattr(package, "project_brief_record_text", "") or "").strip()
    if project_brief:
        records.append(
            _artifact_text_record(
                "Project brief",
                "odylith/runtime/source/project-brief.v1.md",
                project_brief,
            )
        )
    next_steps = _json_evidence_text(getattr(package, "next_steps_preview", None))
    if next_steps:
        records.append(_artifact_text_record("Operator next steps", "create_payload.next_steps", next_steps))
    accepted_project = _json_evidence_text(getattr(package, "accepted_project_preview", None))
    if accepted_project:
        records.append(
            _artifact_text_record(
                "Accepted project",
                "odylith/runtime/source/accepted-project.v1.json",
                accepted_project,
            )
        )
    source_launch = _json_evidence_text(getattr(package, "source_launch_readback", None))
    if source_launch:
        records.append(
            _artifact_text_record(
                "Accepted source launch",
                "odylith/runtime/source/accepted-project.v1.json#source_launch",
                source_launch,
            )
        )
    for index, row in enumerate(
        _mapping_rows(_as_mapping(getattr(package, "project_dashboard_preview", None)).get("host_handoff_prompts")),
        start=1,
    ):
        text = _json_evidence_text(row)
        if text:
            records.append(
                _artifact_text_record(
                    "Project implementation prompt",
                    f"odylith/tooling-payload.v1.js#host_handoff_prompts[{index}]",
                    text,
                )
            )
    return records[:EVIDENCE_ARTIFACT_LIMIT]


def _artifact_inventory(records: Sequence[Mapping[str, str]]) -> list[Mapping[str, Any]]:
    return [
        _artifact_record(str(row.get("surface", "")), str(row.get("path", "")), str(row.get("text", "")))
        for row in records[:EVIDENCE_ARTIFACT_LIMIT]
    ]


def _artifact_text_records(surface: str, records: Mapping[Any, Any]) -> list[Mapping[str, str]]:
    return [
        _artifact_text_record(surface, str(path), str(text or ""))
        for path, text in sorted(records.items(), key=lambda item: str(item[0]))
        if str(text or "").strip()
    ]


def _artifact_text_record(surface: str, path: str, text: str) -> Mapping[str, str]:
    return {"surface": surface, "path": path, "text": text}


def _artifact_record(surface: str, path: str, text: str) -> Mapping[str, Any]:
    return {
        "surface": surface,
        "path": path,
        "sha256": _sha256_text(text),
        "byte_count": len(text.encode("utf-8")),
        "excerpt": _excerpt(text),
    }


def _required_term_grounding(
    *,
    case: GreenfieldMatrixCase,
    artifacts: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    grounding: list[Mapping[str, Any]] = []
    for term in tuple(dict.fromkeys(str(item).strip() for item in case.required_terms if str(item).strip())):
        hits = [
            {
                "surface": str(artifact.get("surface", "")),
                "path": str(artifact.get("path", "")),
                "excerpt": _excerpt(str(artifact.get("text", "") or artifact.get("excerpt", ""))),
            }
            for artifact in artifacts
            if _term_present(str(artifact.get("text", "") or artifact.get("excerpt", "")), term)
        ]
        grounding.append(
            {
                "term": term,
                "present": bool(hits),
                "surfaces": list(dict.fromkeys(hit["surface"] for hit in hits if hit["surface"])),
                "hits": hits[:8],
            }
        )
    return grounding


def _required_term_distribution_findings(
    *,
    all_grounding: Sequence[Mapping[str, Any]],
    scored_grounding: Sequence[Mapping[str, Any]],
) -> list[str]:
    all_by_term = {str(row.get("term", "")).strip(): row for row in all_grounding if str(row.get("term", "")).strip()}
    scored_by_term = {str(row.get("term", "")).strip(): row for row in scored_grounding if str(row.get("term", "")).strip()}
    findings: list[str] = []
    for term, row in all_by_term.items():
        scored = scored_by_term.get(term, {})
        if row.get("present") and not scored.get("present"):
            surfaces = ", ".join(str(surface) for surface in row.get("surfaces", []) if str(surface).strip())
            findings.append(
                f"required term `{term}` appears only outside scored generated artifacts"
                + (f" ({surfaces})" if surfaces else "")
            )
    return findings


def _quality_finding_evidence(
    *,
    package: Any,
    quality: GreenfieldQualityVerdict,
    browser_surface_issues: Sequence[str],
) -> list[Mapping[str, str]]:
    findings: list[Mapping[str, str]] = [
        {"dimension": finding.dimension, "message": finding.message}
        for finding in package_evidence_findings(package)
    ]
    findings.extend({"dimension": "quality", "message": str(issue)} for issue in quality.issues[:50])
    findings.extend({"dimension": "browser_surface_proof", "message": str(issue)} for issue in browser_surface_issues)
    return list({(row["dimension"], row["message"]): row for row in findings if row["message"].strip()}.values())


def _json_evidence_text(value: Any) -> str:
    if not value:
        return ""
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    except TypeError:
        return str(value)


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _excerpt(value: str, limit: int = EVIDENCE_EXCERPT_CHARS) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


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
    create, create_seconds = _run_compiled_greenfield_create(
        repo_root=repo_root,
        env=installed_auto_rescue_env(env),
        prompt=case.prompt,
        timeout=150,
    )
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
            write_transaction_issues=write_transaction_custody_issues,
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
    create, create_seconds = _run_compiled_greenfield_create(
        repo_root=repo_root,
        env=_installed_structured_rescue_env(env),
        prompt=case.prompt,
        timeout=150,
    )
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
            write_transaction_issues=write_transaction_custody_issues,
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
    if not _natural_rescue_plan_or_fallback_proven(summary):
        issues.append(
            "natural rescue proof did not record a planned Tribunal structured patch plan "
            "or a source-anchored semantic fallback after provider failure"
        )
    if RESCUE_PROBE_CODE in set(summary.get("repaired_issue_codes") or ()):
        issues.append("natural rescue proof used the deterministic rescue probe")
    if STRUCTURED_RESCUE_PROOF_CODE not in set(summary.get("repaired_issue_codes") or ()):
        issues.append(f"natural rescue proof did not repair `{STRUCTURED_RESCUE_PROOF_CODE}`")
    return tuple(issues)


def _natural_rescue_plan_or_fallback_proven(summary: Mapping[str, Any]) -> bool:
    if (
        summary.get("tribunal_patch_plan_status") == "planned"
        and int(summary.get("tribunal_patch_plan_operation_count") or 0) > 0
        and str(summary.get("tribunal_patch_plan_provider") or "").strip()
    ):
        return True
    return (
        summary.get("structured_patch_fallback_status") == "applied"
        and summary.get("structured_patch_fallback_source") == "source_anchored_semantic_fact"
        and int(summary.get("structured_patch_fallback_operation_count") or 0) > 0
        and str(summary.get("structured_patch_fallback_provider") or "").strip()
        and str(summary.get("structured_patch_fallback_provider_failure_code") or "").strip()
    )


def collect_artifact_package(*, repo_root: Path, create_payload: Mapping[str, Any]) -> Any:
    """Collect generated records in the shape understood by artifact quality gates."""

    accepted_project = _read_json_mapping(repo_root / "odylith/runtime/source/accepted-project.v1.json")
    proposal = _as_mapping(accepted_project.get("proposal")) or _as_mapping(create_payload.get("proposal"))
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
        evidence=_failed_case_evidence_manifest(case, status, returncode, detail),
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
    payload = read_tooling_payload_js(text)
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
        "--install-mode",
        choices=INSTALL_MODES,
        default="full",
        help="Use full clean installs for release proof or a seeded install for high-volume discovery.",
    )
    parser.add_argument(
        "--telemetry-jsonl",
        default="",
        help="Append per-run and per-case campaign telemetry to this JSONL file.",
    )
    parser.add_argument(
        "--campaign-phase",
        default="single-matrix",
        help="Operator-facing campaign phase label such as failed-subset, 60-case-regression, volume-discovery, or 240-case-discovery.",
    )
    parser.add_argument(
        "--proof-tier",
        choices=("discovery", "release"),
        default="release",
        help="Separate high-volume discovery proof from release-grade proof in the persisted matrix payload.",
    )
    parser.add_argument(
        "--stop-after-failures",
        type=int,
        default=0,
        help="Stop the run after this many failed cases; 0 disables the global failure threshold.",
    )
    parser.add_argument(
        "--stop-after-cluster-failures",
        type=int,
        default=0,
        help="Stop the run after this many failures in the same diagnostic cluster; 0 disables cluster stopping.",
    )
    parser.add_argument(
        "--required-stressor",
        action="append",
        default=None,
        help="Require the selected case set to cover this stressor class. Repeatable.",
    )
    parser.add_argument(
        "--require-high-variance-stressors",
        action="store_true",
        help="Require the selected case set to cover the maintained high-variance stressor taxonomy.",
    )
    parser.add_argument(
        "--allow-skipped-browser-proof",
        action="store_true",
        help="Allow omitted browser proof for high-volume discovery only; this is not release proof.",
    )
    parser.add_argument(
        "--allow-partial-stressor-coverage",
        action="store_true",
        help=(
            "Allow a discovery shard to report tier-required stressors without failing preflight when this shard "
            "does not contain every required class. Release proof must not use this."
        ),
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
    planned_cases = selected_cases or default_cases()
    required_stressors = required_stressors_from_values(
        args.required_stressor or (),
        use_default=bool(args.require_high_variance_stressors),
    )
    campaign_config = MatrixCampaignConfig(
        phase=campaign_phase_from_value(str(args.campaign_phase)),
        proof_tier=proof_tier_from_value(str(args.proof_tier)),
        telemetry_jsonl=Path(str(args.telemetry_jsonl)).expanduser().resolve()
        if str(args.telemetry_jsonl or "").strip()
        else None,
        stop_after_failures=positive_int(args.stop_after_failures),
        stop_after_cluster_failures=positive_int(args.stop_after_cluster_failures),
        required_stressors=required_stressors,
    )
    _raise_for_invalid_campaign_policy(
        config=campaign_config,
        install_mode=str(args.install_mode),
        include_browser_proof=bool(args.include_browser_proof),
        include_rescue_smoke=bool(args.include_rescue_smoke),
        include_natural_rescue_proof=bool(args.include_natural_rescue_proof),
        allow_skipped_browser_proof=bool(args.allow_skipped_browser_proof),
        allow_partial_stressor_coverage=bool(args.allow_partial_stressor_coverage),
    )
    incremental_output_json = (
        Path(str(args.output_json)).expanduser().resolve()
        if str(args.output_json or "").strip()
        else None
    )
    results = run_matrix(
        dist_dir=Path(args.dist_dir),
        version=str(args.version),
        temp_parent=Path(args.temp_parent),
        cases=selected_cases,
        include_browser_proof=bool(args.include_browser_proof),
        install_mode=str(args.install_mode),
        telemetry_jsonl=campaign_config.telemetry_jsonl,
        campaign_phase=campaign_config.phase,
        proof_tier=campaign_config.proof_tier,
        stop_after_failures=campaign_config.stop_after_failures,
        stop_after_cluster_failures=campaign_config.stop_after_cluster_failures,
        required_stressors=campaign_config.required_stressors,
        incremental_output_json=incremental_output_json,
        allow_partial_stressor_coverage=bool(args.allow_partial_stressor_coverage),
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
        browser_status == "skipped"
        and bool(args.allow_skipped_browser_proof)
        and campaign_config.proof_tier == "discovery"
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
        "campaign": campaign_summary(
            cases=planned_cases,
            results=results,
            config=campaign_config,
            stopped_reason=stop_reason(results, campaign_config),
        ),
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
