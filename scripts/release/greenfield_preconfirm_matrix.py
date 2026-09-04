"""Run installed Greenfield pre-confirm and commit-only simulations."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass, replace
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
from greenfield_browser_proof_summary import browser_proof_summary  # noqa: E402
from greenfield_browser_surface_proof import (  # noqa: E402
    BROWSER_SURFACE_PROOF_SCOPE,
    browser_runtime_preflight_issues,
    browser_surface_proof_issues,
)
from greenfield_surface_health import INDEX_SHELL_TAB_CONTRACTS  # noqa: E402
from greenfield_surface_health import REQUIRED_RENDERED_SURFACES  # noqa: E402
from greenfield_surface_health import atlas_rendered_asset_count  # noqa: E402
from greenfield_surface_health import rendered_surface_health_issues  # noqa: E402
from greenfield_surface_health import rendered_surface_payload_count  # noqa: E402
from greenfield_matrix_leakage import case_generated_leakage_terms as _case_generated_leakage_terms  # noqa: E402
from greenfield_matrix_leakage import platform_baseline_required_terms as _platform_baseline_required_terms  # noqa: E402
from greenfield_matrix_leakage import source_evidence_custody_issues as _source_evidence_custody_issues  # noqa: E402
from greenfield_matrix_leakage import term_present as _term_present  # noqa: E402
from greenfield_matrix_leakage import with_platform_leakage_issues as _with_platform_leakage_issues  # noqa: E402
from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_matrix_case_file import ungrounded_required_terms  # noqa: E402
from greenfield_matrix_clarification import clarification_contract_issues, clarification_quality_verdict, run_expected_clarification  # noqa: E402
from greenfield_matrix_write_audit import begin_installed_write_audit  # noqa: E402
from greenfield_matrix_corpus_provenance import GreenfieldReleaseAudit  # noqa: E402
from greenfield_matrix_corpus_provenance import discovery_corpus_summary  # noqa: E402
from greenfield_matrix_corpus_provenance import evaluate_release_corpus  # noqa: E402
from greenfield_matrix_corpus_provenance import load_release_audit_file  # noqa: E402
from greenfield_evaluation_contract import evaluate_frozen_evaluation_contract  # noqa: E402
from greenfield_evaluation_contract import validate_atomic_annotations  # noqa: E402
from greenfield_final_holdout_guard import bind_final_holdout_inputs  # noqa: E402
from greenfield_final_holdout_guard import claim_final_holdout_run  # noqa: E402
from greenfield_final_holdout_guard import complete_final_holdout_run  # noqa: E402
from greenfield_distribution_provenance import verify_distribution_provenance  # noqa: E402
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
from greenfield_matrix_attempt_ledger import MatrixAttemptLedger  # noqa: E402
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs  # noqa: E402
from greenfield_model_profiles import assign_model_profiles  # noqa: E402
from greenfield_model_profiles import case_model_profile  # noqa: E402
from greenfield_model_profiles import model_profile_environment  # noqa: E402
from greenfield_model_profiles import model_profile_evidence  # noqa: E402
from greenfield_model_profiles import profile_counts  # noqa: E402
from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE  # noqa: E402
from greenfield_model_profile_proof import model_profile_release_proof  # noqa: E402
from greenfield_model_profile_proof import sealed_model_profile_observation  # noqa: E402
from greenfield_model_profile_proof import unavailable_provider_proof_issues  # noqa: E402
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard  # noqa: E402
from greenfield_matrix_preflight import matrix_preflight_failures  # noqa: E402
from greenfield_matrix_package_evidence import package_evidence_findings  # noqa: E402
from greenfield_matrix_proof_scope import commit_manifest_summary  # noqa: E402
from greenfield_matrix_proof_scope import temp_cleanup_proof  # noqa: E402
from greenfield_matrix_release_artifacts import RetainedEvidenceCase  # noqa: E402
from greenfield_matrix_release_artifacts import begin_retained_case_evidence  # noqa: E402
from greenfield_matrix_release_artifacts import finalize_retained_case_evidence  # noqa: E402
from greenfield_matrix_release_artifacts import prepare_retained_evidence_output_dir  # noqa: E402
from greenfield_matrix_release_artifacts import record_retained_case_json  # noqa: E402
from greenfield_matrix_release_artifacts import record_retained_case_text  # noqa: E402
from greenfield_matrix_release_artifacts import retained_case_evidence_fd  # noqa: E402
from greenfield_matrix_release_artifacts import retained_evidence_manifest_path  # noqa: E402
from greenfield_matrix_release_artifacts import retained_evidence_manifest_issues  # noqa: E402
from greenfield_matrix_release_artifacts import validate_retained_evidence_output_dir  # noqa: E402
from greenfield_matrix_release_artifacts import write_retained_evidence_manifest  # noqa: E402
from greenfield_matrix_run_lease import acquire_matrix_run_lease  # noqa: E402
from greenfield_matrix_run_lease import write_matrix_payload  # noqa: E402
from greenfield_semantic_release_score import evaluate_semantic_release  # noqa: E402
from greenfield_commit_recovery_proof import GreenfieldInstalledCommitRecoveryProof  # noqa: E402
from greenfield_commit_recovery_proof import PROOF_SCOPE as COMMIT_RECOVERY_PROOF_SCOPE  # noqa: E402
from greenfield_commit_recovery_proof import run_installed_commit_recovery_proof  # noqa: E402
from greenfield_commit_recovery_cases import select_recovery_case  # noqa: E402
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase  # noqa: E402
from greenfield_preconfirm_matrix_cases import CLARIFICATION_REQUIRED_EXPECTATION  # noqa: E402
from greenfield_preconfirm_matrix_cases import VALID_CASE_EXPECTATIONS  # noqa: E402
from greenfield_preconfirm_matrix_cases import case_evidence  # noqa: E402
from greenfield_preconfirm_matrix_cases import case_expectation  # noqa: E402
from greenfield_preconfirm_matrix_cases import default_cases  # noqa: E402
from greenfield_process import CommandLifecycleObserverError  # noqa: E402
from greenfield_process import command_lifecycle_observer  # noqa: E402

GREENFIELD_MODEL_PROOF_FD_ENV = "ODYLITH_GREENFIELD_MODEL_PROOF_FD"
from greenfield_process import run_command_with_group_timeout as _run  # noqa: E402
from greenfield_matrix_types import GreenfieldArtifactCounts  # noqa: E402
from greenfield_matrix_types import GreenfieldMatrixResult  # noqa: E402
from greenfield_matrix_types import GreenfieldQualityVerdict  # noqa: E402
from greenfield_matrix_transaction_evidence import CompiledCreateExecution  # noqa: E402
from greenfield_matrix_transaction_evidence import commit_precompiled_transaction  # noqa: E402
from greenfield_matrix_transaction_evidence import confirmation_preview_issues  # noqa: E402
from greenfield_matrix_transaction_evidence import dry_run_commit_issues  # noqa: E402
from greenfield_matrix_transaction_evidence import post_confirm_navigation_issues  # noqa: E402
from greenfield_matrix_governed_readback import collect_governed_readback  # noqa: E402
from greenfield_matrix_governed_readback import compass_record_count  # noqa: E402
from greenfield_matrix_governed_readback import program_record_count  # noqa: E402
from greenfield_matrix_governed_readback import release_record_count  # noqa: E402
from greenfield_matrix_quality_scoring import PRECONFIRM_BUDGET_SECONDS  # noqa: E402
from greenfield_matrix_quality_scoring import QUALITY_SCORE_DIMENSIONS  # noqa: E402
from greenfield_matrix_quality_scoring import build_quality_verdict  # noqa: E402
from greenfield_matrix_quality_scoring import command_excerpt  # noqa: E402
from greenfield_tooling_payload_reader import read_tooling_payload_js  # noqa: E402
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (  # noqa: E402
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (  # noqa: E402
    model_profile_id_for_repair_tier,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values  # noqa: E402
import platform_domain_leakage_check as platform_domain_leakage  # noqa: E402


COMMAND_TIMEOUT_SECONDS = 300
QUALITY_MATRIX_VERSION = "greenfield-preconfirm-installed-matrix-v1"
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


@dataclass
class _FinalHoldoutRun:
    ledger_path: Path
    holdout_path: Path
    evaluation_manifest_path: Path
    case_paths: tuple[Path, ...]
    implementation_revision: str
    distribution_provenance_sha256: str
    claimed: bool = False
    run_id: str = ""

    def claim(self) -> None:
        claimed = claim_final_holdout_run(
            ledger_path=self.ledger_path,
            implementation_revision=self.implementation_revision,
            distribution_provenance_sha256=self.distribution_provenance_sha256,
        )
        self.run_id = str(claimed["run_id"])
        self.claimed = True
        bind_final_holdout_inputs(
            ledger_path=self.ledger_path,
            protected_inputs={
                "final_holdout": self.holdout_path,
                "evaluation_manifest": self.evaluation_manifest_path,
                **{
                    f"case_file_{index:03d}": path
                    for index, path in enumerate(self.case_paths, start=1)
                },
            },
        )

    def complete(
        self,
        *,
        result_path: Path,
        outcome: str,
        retained_evidence_manifest: Path | None = None,
    ) -> None:
        if self.claimed:
            complete_final_holdout_run(
                ledger_path=self.ledger_path,
                result_path=result_path,
                outcome=outcome,
                retained_evidence_manifest=retained_evidence_manifest,
            )
            self.claimed = False


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
    proof_tier: str = "discovery",
    stop_after_failures: int = 0,
    stop_after_cluster_failures: int = 0,
    required_stressors: Sequence[str] = (),
    incremental_output_json: Path | None = None,
    attempt_ledger_jsonl: Path | None = None,
    allow_partial_stressor_coverage: bool = False,
    release_audits: Sequence[GreenfieldReleaseAudit] = (),
    release_audit_repo_root: Path | None = None,
    semantic_annotations_file: str = "",
    evaluation_split_manifest: str = "",
    evidence_output_dir: Path | None = None,
    retained_evidence_run_id: str = "",
    before_product_execution: Callable[[], None] | None = None,
) -> tuple[GreenfieldMatrixResult, ...]:
    """Run the real installed greenfield create path for each matrix case."""

    selected_cases = assign_model_profiles(tuple(cases) or default_cases())
    semantic_release_requested = bool(
        str(semantic_annotations_file or "").strip()
        or str(evaluation_split_manifest or "").strip()
    )
    _raise_for_unsupported_case_expectations(selected_cases)
    install_mode = _validated_install_mode(install_mode)
    campaign_config = MatrixCampaignConfig(
        phase=campaign_phase_from_value(campaign_phase),
        proof_tier=proof_tier_from_value(proof_tier),
        telemetry_jsonl=Path(telemetry_jsonl).expanduser().resolve() if telemetry_jsonl else None,
        stop_after_failures=positive_int(stop_after_failures),
        stop_after_cluster_failures=positive_int(stop_after_cluster_failures),
        required_stressors=tuple(required_stressors),
    )
    _raise_for_invalid_campaign_policy(
        config=campaign_config,
        install_mode=install_mode,
        include_browser_proof=include_browser_proof,
        # run_matrix is the per-case inner loop; main owns the one-per-run installed recovery proof.
        include_commit_recovery_proof=True,
        allow_skipped_browser_proof=False,
        allow_partial_stressor_coverage=allow_partial_stressor_coverage,
        release_corpus_issues=(
            evaluate_release_corpus(
                selected_cases,
                release_audits,
                repo_root=release_audit_repo_root,
            ).issues
            if campaign_config.proof_tier == "release" and not semantic_annotations_file
            else ()
        ),
        semantic_annotations_file=semantic_annotations_file,
        evaluation_split_manifest=evaluation_split_manifest,
    )
    if campaign_config.proof_tier == "release" and evidence_output_dir is None:
        raise RuntimeError("release proof requires --evidence-output-dir")
    retained_evidence_root = (
        prepare_retained_evidence_output_dir(
            output_dir=Path(evidence_output_dir),
            temp_parent=Path(temp_parent),
        )
        if evidence_output_dir is not None
        else None
    )
    telemetry = MatrixTelemetryWriter(campaign_config.telemetry_jsonl)
    attempt_ledger = MatrixAttemptLedger(attempt_ledger_jsonl)
    attempt_ledger.ensure_planned(selected_cases)
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
            "model_profile_counts": profile_counts(selected_cases),
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
        include_browser_proof=include_browser_proof,
        enforce_required_stressors=not allow_partial_stressor_coverage,
        enforce_lexical_controls=not semantic_release_requested,
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
        _retain_unexecuted_results(
            evidence_root=retained_evidence_root,
            cases=selected_cases,
            results=results,
            repo_root=Path(temp_parent),
            run_id=retained_evidence_run_id,
        )
        return tuple(results)
    if before_product_execution is not None:
        before_product_execution()
    platform_baseline_terms = (
        ()
        if semantic_release_requested
        else _platform_baseline_required_terms(
            repo_root=REPO_ROOT,
            release_dir=release_dir,
            cases=selected_cases,
        )
    )
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-matrix-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    stopped_reason = ""
    try:
        seed_repo = None
        if install_mode == "seeded":
            seed_repo = run_root / f"odylith-seed-install-{uuid.uuid4().hex[:8]}"
            with command_lifecycle_observer(_matrix_command_observer(telemetry)):
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
                for result in results:
                    attempt_ledger.record_completed(result)
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
                _retain_unexecuted_results(
                    evidence_root=retained_evidence_root,
                    cases=selected_cases,
                    results=results,
                    repo_root=seed_repo,
                    run_id=retained_evidence_run_id,
                )
                return tuple(results)
        for index, case in enumerate(selected_cases, start=1):
            telemetry.emit("case_started", case_started_event(case=case, index=index, total=len(selected_cases)))
            attempt_ledger.record_started(case=case, index=index, total=len(selected_cases))
            repo_root = run_root / f"odylith-sim-{case.slug}-{uuid.uuid4().hex[:8]}"
            retained_case = (
                begin_retained_case_evidence(
                    evidence_root=retained_evidence_root,
                    case_id=_retained_case_id(case),
                )
                if retained_evidence_root is not None
                else None
            )
            try:
                if seed_repo is not None:
                    with command_lifecycle_observer(_matrix_command_observer(telemetry)):
                        _clone_seed_repo(seed_repo=seed_repo, repo_root=repo_root, version=version)
                with command_lifecycle_observer(_matrix_command_observer(telemetry)):
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
                        require_write_audit=True,
                        include_lexical_custody_proof=not semantic_release_requested,
                        retained_case=retained_case,
                    )
                if not semantic_release_requested:
                    result = _with_case_platform_leakage_issues(result=result, release_dir=release_dir)
                reason = stop_reason((*results, result), campaign_config)
            except CommandLifecycleObserverError as exc:
                result = _failed_case(
                    case,
                    repo_root,
                    "command-lifecycle-telemetry-failed",
                    exc.returncode,
                    f"{exc}; command_kind={exc.command_kind}; terminal_state={exc.state}",
                )
                reason = "command-lifecycle-telemetry-failed"
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
            if retained_case is not None:
                try:
                    finalize_retained_case_evidence(
                        case=retained_case,
                        repo_root=repo_root,
                        result_payload=result.to_dict(),
                    )
                except RuntimeError as exc:
                    result = _result_with_retained_evidence_issue(result, str(exc))
                    results[-1] = result
                    reason = "retained-evidence-failed"
                    _flush_incremental_matrix_payload(
                        output_json=incremental_output_json,
                        cases=selected_cases,
                        results=results,
                        config=campaign_config,
                        status="failed",
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
            attempt_ledger.record_completed(result)
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
    if retained_evidence_root is not None:
        write_retained_evidence_manifest(
            root=retained_evidence_root,
            expected_case_ids=tuple(_retained_case_id(case) for case in selected_cases[: len(results)]),
            run_id=retained_evidence_run_id,
        )
    return tuple(results)


def _matrix_command_observer(telemetry: MatrixTelemetryWriter):
    if not telemetry.enabled:
        return None

    def observe(event: Mapping[str, object]) -> None:
        state = str(event.get("state") or "unknown")
        telemetry.emit(f"command_{state}", event)

    return observe


def _matrix_preflight_results(
    *,
    release_dir: Path,
    cases: Sequence[GreenfieldMatrixCase],
    required_stressors: Sequence[str],
    temp_parent: Path,
    include_browser_proof: bool = False,
    enforce_required_stressors: bool = True,
    enforce_lexical_controls: bool = True,
) -> tuple[GreenfieldMatrixResult, ...]:
    failures = matrix_preflight_failures(
        repo_root=REPO_ROOT,
        release_dir=release_dir,
        cases=cases,
        required_stressors=required_stressors,
        enforce_required_stressors=enforce_required_stressors,
        enforce_lexical_controls=enforce_lexical_controls,
    )
    browser_issues = browser_runtime_preflight_issues() if include_browser_proof else ()
    if not failures and not browser_issues:
        return ()
    preflight_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-preflight-{uuid.uuid4().hex[:8]}"
    results = [
        _failed_case(
            failure.case,
            preflight_root,
            "preflight_failed",
            1,
            failure.detail,
        )
        for failure in failures
    ]
    if browser_issues:
        results.append(
            _failed_case(
                cases[0],
                preflight_root,
                "preflight_failed",
                1,
                "; ".join(browser_issues),
            )
        )
    return tuple(results)


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


def _raise_for_unsupported_case_expectations(cases: Sequence[GreenfieldMatrixCase]) -> None:
    unsupported = [
        f"{case.name}: {case_expectation(case)}"
        for case in cases
        if case_expectation(case) not in VALID_CASE_EXPECTATIONS
    ]
    if unsupported:
        supported = ", ".join(sorted(VALID_CASE_EXPECTATIONS))
        raise RuntimeError("unsupported greenfield matrix case expectation; expected one of: " + supported + "; " + "; ".join(unsupported))


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


def _result_with_retained_evidence_issue(result: GreenfieldMatrixResult, detail: str) -> GreenfieldMatrixResult:
    issue = f"retained evidence failed before temp cleanup: {command_excerpt(detail, limit=800)}"
    quality = replace(
        result.quality,
        passed=False,
        issues=tuple(dict.fromkeys((*result.quality.issues, issue))),
        score=0,
        score_explanation=("release evidence was not durably retained",),
    )
    return replace(
        result,
        status="failed",
        quality=quality,
        failure_detail=command_excerpt(detail, limit=1200),
    )


def _record_retained_execution(
    *,
    retained_case: RetainedEvidenceCase,
    proposal_payload: Mapping[str, Any],
    dry_run_receipt: Mapping[str, Any],
    create_payload: Mapping[str, Any],
    raw_streams: Mapping[str, str],
) -> None:
    for name in (
        "input.prompt",
        "input.edit-evidence",
        "propose.stdout",
        "propose.stderr",
        "create.stdout",
        "create.stderr",
    ):
        record_retained_case_text(
            retained_case,
            f"commands/{name}",
            str(raw_streams.get(name) or ""),
        )
    record_retained_case_json(retained_case, "semantic/proposal-payload.v1.json", dict(proposal_payload))
    if dry_run_receipt:
        record_retained_case_json(retained_case, "semantic/dry-run-receipt.v2.json", dict(dry_run_receipt))
    if create_payload:
        record_retained_case_json(retained_case, "semantic/create-payload.v1.json", dict(create_payload))


def _retained_case_id(case: GreenfieldMatrixCase) -> str:
    return str(case.case_id or case.slug).strip()


def _retain_unexecuted_results(
    *,
    evidence_root: Path | None,
    cases: Sequence[GreenfieldMatrixCase],
    results: Sequence[GreenfieldMatrixResult],
    repo_root: Path,
    run_id: str = "",
) -> None:
    if evidence_root is None:
        return
    case_ids: list[str] = []
    seen: dict[str, int] = {}
    for index, result in enumerate(results):
        case = cases[min(index, len(cases) - 1)]
        base = _retained_case_id(case)
        seen[base] = seen.get(base, 0) + 1
        case_id = base if seen[base] == 1 else f"{base}-{seen[base]}"
        retained_case = begin_retained_case_evidence(evidence_root=evidence_root, case_id=case_id)
        finalize_retained_case_evidence(
            case=retained_case,
            repo_root=repo_root,
            result_payload=result.to_dict(),
        )
        case_ids.append(case_id)
    write_retained_evidence_manifest(
        root=evidence_root,
        expected_case_ids=case_ids,
        run_id=run_id,
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
    metamorphic_output = evaluate_metamorphic_outputs(cases=cases, results=results)
    return "passed" if all(result.quality.passed for result in results) and metamorphic_output["passed"] else "failed"


def _raise_for_invalid_campaign_policy(
    *,
    config: MatrixCampaignConfig,
    install_mode: str,
    include_browser_proof: bool,
    include_commit_recovery_proof: bool = False,
    allow_skipped_browser_proof: bool,
    allow_partial_stressor_coverage: bool = False,
    release_corpus_issues: Sequence[str] = (),
    semantic_annotations_file: str = "",
    evaluation_split_manifest: str = "",
) -> None:
    if config.proof_tier != "release":
        return
    violations: list[str] = []
    if install_mode != "full":
        violations.append("release proof must use full install mode")
    if not include_browser_proof:
        violations.append("release proof must include browser proof")
    if not include_commit_recovery_proof:
        violations.append("release proof must include installed commit recovery proof")
    if allow_skipped_browser_proof:
        violations.append("release proof cannot allow skipped browser proof")
    if allow_partial_stressor_coverage:
        violations.append("release proof cannot allow partial stressor coverage")
    if config.stop_after_failures:
        violations.append("release proof cannot stop after a failure threshold")
    if config.stop_after_cluster_failures:
        violations.append("release proof cannot stop after a cluster threshold")
    if not str(semantic_annotations_file or "").strip():
        violations.append("release proof requires blinded semantic annotations")
    if not str(evaluation_split_manifest or "").strip():
        violations.append("release proof requires a frozen evaluation split manifest")
    violations.extend(str(issue) for issue in release_corpus_issues if str(issue).strip())
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


def run_unavailable_provider_proof(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    case: GreenfieldMatrixCase,
) -> dict[str, Any]:
    """Prove installed model authoring fails closed when its provider is absent."""

    release_dir = Path(dist_dir).expanduser().resolve()
    install_script = release_dir / "install.sh"
    if not install_script.is_file():
        raise FileNotFoundError(f"missing local release install script: {install_script}")
    run_root = Path(temp_parent).expanduser().resolve() / f"odylith-greenfield-unavailable-{uuid.uuid4().hex[:8]}"
    run_root.mkdir(parents=True, exist_ok=False)
    server, base_url = _serve_directory(release_dir)
    try:
        repo_root = run_root / "consumer-repo"
        repo_root.mkdir()
        base_env = _local_release_env(base_url=base_url, version=version)
        env = model_profile_environment(
            UNAVAILABLE_PROVIDER_PROFILE,
            base_env,
            unavailable_provider_bin=str(run_root / "missing-codex-provider"),
        )
        _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
        install = _run(
            cwd=repo_root,
            env=env,
            command=["bash", str(install_script)],
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
        if install.returncode != 0:
            return {
                "version": "odylith.greenfield.unavailable-provider-proof.v1",
                "status": "failed",
                "profile_id": UNAVAILABLE_PROVIDER_PROFILE,
                "proposal_seconds": 0.0,
                "returncode": install.returncode,
                "no_write": {},
                "issues": [f"install_failed: {command_excerpt(install.stderr or install.stdout, limit=800)}"],
            }
        audit = begin_installed_write_audit(repo_root=repo_root)
        attempt: dict[str, Any] = {}

        def invoke() -> Any:
            completed = _run_greenfield_propose(
                repo_root=repo_root,
                env={**env, **audit.environment()},
                prompt=case.prompt,
                edit_evidence=str(case.confirmed_intent_markdown or ""),
                timeout=90,
                repair_tier="rescue",
                command=audit.command(
                    runtime_python=repo_root / ".odylith/runtime/current/bin/python",
                    arguments=(),
                ),
                pass_fds=audit.pass_fds,
            )
            attempt["completed"] = completed
            return completed

        try:
            execution = run_expected_clarification(
                repo_root=repo_root,
                invoke=invoke,
                parse_payload=_parse_json_object,
            )
        finally:
            audit_evidence = audit.finish()
        completed = attempt.get("completed")
        detail = str(getattr(completed, "stderr", "") or getattr(completed, "stdout", "") or "")
        issues = unavailable_provider_proof_issues(
            returncode=execution.returncode,
            proposal_seconds=execution.seconds,
            detail=detail,
            write_audit_active=audit_evidence.active,
            write_audit_error=audit_evidence.error,
            write_attempts=audit_evidence.write_attempts,
            subprocess_attempts=audit_evidence.subprocess_attempts,
            changed_records=execution.changed_records,
            staged_transaction_present=execution.staged_transaction_present,
        )
        return {
            "version": "odylith.greenfield.unavailable-provider-proof.v1",
            "status": "passed" if not issues else "failed",
            "profile_id": UNAVAILABLE_PROVIDER_PROFILE,
            "model_profile": model_profile_evidence(UNAVAILABLE_PROVIDER_PROFILE, env),
            "proposal_seconds": execution.seconds,
            "returncode": execution.returncode,
            "failure_detail": command_excerpt(detail, limit=800),
            "no_write": {
                "before_record_count": execution.before_record_count,
                "after_record_count": execution.after_record_count,
                "changed_records": list(execution.changed_records),
                "staged_transaction_present": execution.staged_transaction_present,
                "write_audit_active": audit_evidence.active,
                "write_attempts": list(audit_evidence.write_attempts),
                "subprocess_attempts": list(audit_evidence.subprocess_attempts),
                "write_audit_error": audit_evidence.error,
            },
            "issues": list(issues),
        }
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
    require_write_audit: bool = True,
    include_lexical_custody_proof: bool = True,
    retained_case: RetainedEvidenceCase | None = None,
) -> GreenfieldMatrixResult:
    case = assign_model_profiles((case,))[0]
    profile = case_model_profile(case)
    profile_contract = get_greenfield_model_profile(profile)
    env = model_profile_environment(
        profile,
        _local_release_env(base_url=base_url, version=version),
    )
    if not skip_install:
        repo_root.mkdir(parents=True)
        _run(cwd=repo_root, env=env, command=["git", "init"], timeout=60)
        install = _run(cwd=repo_root, env=env, command=["bash", str(install_script)], timeout=COMMAND_TIMEOUT_SECONDS)
        if install.returncode != 0:
            return _failed_case(case, repo_root, "install_failed", install.returncode, install.stderr or install.stdout)
    elif not (repo_root / ".odylith/bin/odylith").is_file():
        return _failed_case(case, repo_root, "seed_clone_failed", 1, "seeded repo clone is missing .odylith/bin/odylith")
    if case_expectation(case) == CLARIFICATION_REQUIRED_EXPECTATION:
        if not require_write_audit:
            raise ValueError("clarification matrix cases require the installed write audit")
        result = _run_expected_clarification_case(
            case=case,
            repo_root=repo_root,
            env=env,
            timeout=int(profile_contract.consumer_budget_seconds),
            repair_tier=profile_contract.repair_tier,
            install_script=install_script,
            version=version,
            install_mode=install_mode,
            retained_case=retained_case,
        )
        return replace(
            result,
            evidence=dict(result.evidence),
        )
    raw_streams: dict[str, str] = {}
    raw_streams["input.prompt"] = case.prompt
    raw_streams["input.edit-evidence"] = str(case.confirmed_intent_markdown or "")
    execution = _run_compiled_greenfield_create_with_receipt(
        repo_root=repo_root,
        env=env,
        prompt=case.prompt,
        edit_evidence=str(case.confirmed_intent_markdown or ""),
        repair_tier=profile_contract.repair_tier,
        raw_streams=raw_streams,
        retained_case=retained_case,
    )
    create = execution.create
    proposal_seconds = execution.proposal_seconds
    create_seconds = execution.create_seconds
    payload = _parse_json_object(create.stdout)
    manifest = _as_mapping(payload.get("commit_manifest"))
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    profile_evidence = model_profile_evidence(
        profile,
        env,
        observed=sealed_model_profile_observation(
            proposal=_as_mapping(getattr(package, "proposal", None)),
            create_payload=payload,
        ),
    )
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    surface_issues = rendered_surface_health_issues(repo_root=repo_root)
    generated_text = _generated_text(repo_root=repo_root, package=package)
    leakage_terms = (
        _case_generated_leakage_terms(
            case=case,
            generated_text=generated_text,
            platform_baseline_terms=platform_baseline_terms,
        )
        if include_lexical_custody_proof
        else ()
    )
    source_custody_issues = (
        (
            *_source_evidence_custody_issues(case=case, generated_text=generated_text),
            *_source_evidence_content_custody_issues(case=case, generated_text=generated_text),
        )
        if include_lexical_custody_proof
        else ()
    )
    browser_surface_proof_attempted = bool(include_browser_proof and create.returncode == 0)
    browser_surface_issues = (
        browser_surface_proof_issues(
            repo_root=repo_root,
            screenshot_output_dir=(retained_case.staging_root / "browser" if retained_case else None),
        )
        if browser_surface_proof_attempted
        else ()
    )
    receipt_issues = dry_run_commit_issues(
        receipt=execution.dry_run_receipt,
        create_payload=payload,
        repo_root=repo_root,
    )
    decision_rail_issues = confirmation_preview_issues(proposal_payload=execution.proposal_payload)
    navigation_issues = post_confirm_navigation_issues(
        create_payload=payload,
        repo_root=repo_root,
        transaction_hash=str(execution.dry_run_receipt.get("transaction_hash") or ""),
    )
    quality = build_quality_verdict(
        create_payload=payload,
        package=package,
        counts=counts,
        surface_issues=surface_issues,
        browser_surface_issues=browser_surface_issues,
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        browser_surface_proof_required=include_browser_proof,
        confirmation_ux_issues=(*decision_rail_issues, *navigation_issues),
        create_returncode=create.returncode,
        proposal_seconds=proposal_seconds,
        create_seconds=create_seconds,
        create_detail=create.stderr or create.stdout,
        external_issues=(
            *receipt_issues,
            *decision_rail_issues,
            *navigation_issues,
            *source_custody_issues,
            *(str(issue) for issue in profile_evidence.get("issues", ())),
        ),
    )
    evidence = dict(
        _case_evidence_manifest(
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
        )
    )
    evidence["preconfirm_dry_run"] = dict(execution.dry_run_receipt)
    evidence["confirmation_contract"] = {
        "status": "passed" if not decision_rail_issues and not navigation_issues else "failed",
        "decision_rail_issues": list(decision_rail_issues),
        "post_confirm_navigation_issues": list(navigation_issues),
    }
    evidence["model_profile"] = profile_evidence
    if retained_case is not None:
        _record_retained_execution(
            retained_case=retained_case,
            proposal_payload=execution.proposal_payload,
            dry_run_receipt=execution.dry_run_receipt,
            create_payload=payload,
            raw_streams=raw_streams,
        )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed" if quality.passed else "failed",
        create_seconds=create_seconds,
        proposal_seconds=proposal_seconds,
        counts=counts,
        quality=quality,
        browser_surface_issues=browser_surface_issues,
        browser_surface_proof_attempted=browser_surface_proof_attempted,
        create_returncode=create.returncode,
        failure_detail=command_excerpt(create.stderr or create.stdout) if create.returncode else "",
        create_stdout_excerpt=command_excerpt(create.stdout) if create.returncode else "",
        create_stderr_excerpt=command_excerpt(create.stderr) if create.returncode else "",
        platform_leakage_terms=leakage_terms,
        commit_manifest_summary=commit_manifest_summary(manifest),
        evidence=evidence,
    )


def _source_evidence_content_custody_issues(
    *,
    case: GreenfieldMatrixCase,
    generated_text: str,
) -> tuple[str, ...]:
    """Reject a retained multi-word source excerpt copied into product artifacts."""

    provenance = getattr(case, "provenance", None)
    if str(getattr(provenance, "corpus_tier", "") or "").strip() != "source_provenanced":
        return ()
    excerpt = " ".join(str(getattr(provenance, "source_excerpt", "") or "").split())
    if len(excerpt.split()) < 3 or not _term_present(generated_text, excerpt):
        return ()
    return ("source evidence text leaked into product artifacts",)


def _run_expected_clarification_case(
    *,
    case: GreenfieldMatrixCase,
    repo_root: Path,
    env: Mapping[str, str],
    timeout: int,
    repair_tier: str,
    install_script: Path,
    version: str,
    install_mode: str,
    retained_case: RetainedEvidenceCase | None = None,
) -> GreenfieldMatrixResult:
    audit = begin_installed_write_audit(repo_root=repo_root)
    raw_streams: dict[str, str] = {}
    raw_streams["input.prompt"] = case.prompt
    raw_streams["input.edit-evidence"] = str(case.confirmed_intent_markdown or "")

    def invoke_proposal() -> Any:
        proposed = _run_greenfield_propose(
            repo_root=repo_root,
            env={**env, **audit.environment()},
            prompt=case.prompt,
            edit_evidence=str(case.confirmed_intent_markdown or ""),
            timeout=timeout,
            repair_tier=repair_tier,
            command=(
                audit.command(
                    runtime_python=repo_root / ".odylith/runtime/current/bin/python",
                    arguments=(),
                )
            ),
            pass_fds=audit.pass_fds,
            retained_case=retained_case,
        )
        raw_streams["propose.stdout"] = str(getattr(proposed, "stdout", "") or "")
        raw_streams["propose.stderr"] = str(getattr(proposed, "stderr", "") or "")
        return proposed

    try:
        execution = run_expected_clarification(
            repo_root=repo_root,
            invoke=invoke_proposal,
            parse_payload=_parse_json_object,
        )
    finally:
        audit_evidence = audit.finish()
    execution = replace(
        execution,
        write_audit_active=audit_evidence.active,
        write_attempts=audit_evidence.write_attempts,
        subprocess_attempts=audit_evidence.subprocess_attempts,
        write_audit_error=audit_evidence.error,
    )
    payload = execution.payload
    issues = list(clarification_contract_issues(
        execution,
        expected_fields=(
            (str(getattr(case, "expected_clarification_field", "") or "").strip(),)
            if str(getattr(case, "expected_clarification_field", "") or "").strip()
            else ()
        ),
        expected_question=str(
            getattr(case, "expected_clarification_question", "") or ""
        ).strip(),
        expected_model_profile_id=model_profile_id_for_repair_tier(repair_tier),
    ))
    package = collect_artifact_package(repo_root=repo_root, create_payload=payload)
    counts = collect_artifact_counts(repo_root=repo_root, package=package, required_terms=case.required_terms)
    profile_id = model_profile_id_for_repair_tier(repair_tier)
    profile_evidence = model_profile_evidence(
        profile_id,
        env,
        observed=sealed_model_profile_observation(create_payload=payload),
    )
    issues.extend(str(issue) for issue in profile_evidence.get("issues", ()))
    quality = clarification_quality_verdict(issues)
    evidence = dict(
        _case_evidence_manifest(
            case=case,
            repo_root=repo_root,
            package=package,
            create_payload=payload,
            quality=quality,
            install_script=install_script,
            version=version,
            install_mode=install_mode,
            browser_surface_proof_attempted=False,
            browser_surface_proof_required=False,
            browser_surface_issues=(),
        )
    )
    clarification = _as_mapping(payload.get("clarification"))
    evidence["clarification"] = {
        "mode": str(payload.get("mode") or "").strip(),
        "question": str(clarification.get("question") or "").strip(),
        "required_fields": list(clarification.get("required_fields") or ()),
        "returncode": execution.returncode,
    }
    evidence["no_write"] = {
        "before_record_count": execution.before_record_count,
        "after_record_count": execution.after_record_count,
        "changed_records": list(execution.changed_records),
        "staged_transaction_present": execution.staged_transaction_present,
        "write_audit_active": execution.write_audit_active,
        "write_attempts": list(execution.write_attempts),
        "subprocess_attempts": list(execution.subprocess_attempts),
        "write_audit_error": execution.write_audit_error,
    }
    evidence["model_profile"] = profile_evidence
    if retained_case is not None:
        _record_retained_execution(
            retained_case=retained_case,
            proposal_payload=payload,
            dry_run_receipt={},
            create_payload={},
            raw_streams=raw_streams,
        )
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed" if quality.passed else "failed",
        create_seconds=execution.seconds,
        proposal_seconds=execution.seconds,
        counts=counts,
        quality=quality,
        create_returncode=execution.returncode,
        failure_detail="clarification-required no-write contract failed" if not quality.passed else "",
        create_stdout_excerpt="",
        create_stderr_excerpt="",
        commit_manifest_summary={},
        evidence=evidence,
    )


def _run_compiled_greenfield_create(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    prompt: str,
    edit_evidence: str = "",
    repair_tier: str = "auto",
) -> tuple[Any, float, float]:
    execution = _run_compiled_greenfield_create_with_receipt(
        repo_root=repo_root,
        env=env,
        prompt=prompt,
        edit_evidence=edit_evidence,
        repair_tier=repair_tier,
    )
    return execution.create, execution.proposal_seconds, execution.create_seconds


def _run_compiled_greenfield_create_with_receipt(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    prompt: str,
    edit_evidence: str = "",
    repair_tier: str = "auto",
    raw_streams: dict[str, str] | None = None,
    retained_case: RetainedEvidenceCase | None = None,
) -> CompiledCreateExecution:
    profile_id = model_profile_id_for_repair_tier(repair_tier)
    configured_profile_id = str(env.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or "").strip()
    if configured_profile_id != profile_id:
        raise ValueError("release proof repair tier does not match its configured model profile")
    proposal_timeout = int(get_greenfield_model_profile(profile_id).consumer_budget_seconds)
    proposal_started = time.perf_counter()
    proposed = _run_greenfield_propose(
        repo_root=repo_root,
        env=env,
        prompt=prompt,
        edit_evidence=edit_evidence,
        timeout=proposal_timeout,
        repair_tier=repair_tier,
        retained_case=retained_case,
    )
    if raw_streams is not None:
        raw_streams["propose.stdout"] = str(getattr(proposed, "stdout", "") or "")
        raw_streams["propose.stderr"] = str(getattr(proposed, "stderr", "") or "")
    proposal_seconds = round(time.perf_counter() - proposal_started, 3)
    execution = commit_precompiled_transaction(
        repo_root=repo_root,
        proposed=proposed,
        proposal_seconds=proposal_seconds,
        invoke_create=lambda command: _run(
            cwd=repo_root,
            env=env,
            command=list(command),
            timeout=60,
        ),
    )
    if raw_streams is not None:
        raw_streams["create.stdout"] = str(getattr(execution.create, "stdout", "") or "")
        raw_streams["create.stderr"] = str(getattr(execution.create, "stderr", "") or "")
    return execution


def _run_greenfield_propose(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    prompt: str,
    timeout: int,
    edit_evidence: str = "",
    repair_tier: str = "",
    command: Sequence[str] | None = None,
    pass_fds: tuple[int, ...] = (),
    retained_case: RetainedEvidenceCase | None = None,
) -> Any:
    propose_command = list(command) if command is not None else ["./.odylith/bin/odylith"]
    propose_command.extend(
        _greenfield_propose_arguments(
            prompt=prompt,
            edit_evidence=edit_evidence,
            repair_tier=repair_tier,
        )
    )
    capture = (
        retained_case_evidence_fd(
            retained_case,
            "semantic/model-authoring-observation.v1.json",
        )
        if retained_case is not None
        else nullcontext(None)
    )
    with capture as proof_fd:
        proposal_env = dict(env)
        inherited_fds = pass_fds
        if proof_fd is not None:
            proposal_env[GREENFIELD_MODEL_PROOF_FD_ENV] = str(proof_fd)
            inherited_fds = (*pass_fds, proof_fd)
        run_kwargs: dict[str, Any] = {
            "cwd": repo_root,
            "env": proposal_env,
            "command": propose_command,
            "timeout": timeout,
        }
        if inherited_fds:
            run_kwargs["pass_fds"] = inherited_fds
        return _run(**run_kwargs)


def _greenfield_propose_arguments(
    *,
    prompt: str,
    edit_evidence: str = "",
    repair_tier: str = "",
) -> list[str]:
    arguments = [
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
        arguments.extend(["--edit", edit_evidence])
    if repair_tier:
        arguments.extend(["--repair-tier", repair_tier])
    return arguments


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
    manifest = _as_mapping(create_payload.get("commit_manifest"))
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
        "commit_manifest_summary": commit_manifest_summary(manifest),
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
    return case_evidence(case)


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
    proposal = _as_mapping(getattr(package, "proposal", None))
    expected_registry_components = len(
        [
            row
            for row in _mapping_rows(proposal.get("components"))
            if str(row.get("status") or "active").strip().casefold() not in {"disabled", "removed"}
        ]
    )
    return GreenfieldArtifactCounts(
        radar_workstreams=len(_as_mapping(package.backlog_result.get("idea_files"))),
        registry_component_specs=len(_as_mapping(package.rendered_component_specs)),
        expected_registry_components=expected_registry_components,
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
        score_explanation=("commit-only create did not complete a governed write transaction",),
    )
    return GreenfieldMatrixResult(
        name=case.name,
        status=status,
        create_seconds=0.0,
        counts=counts,
        quality=quality,
        create_returncode=returncode,
        failure_detail=command_excerpt(detail),
        commit_manifest_summary={},
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
    print(f"greenfield installed pre-confirm and commit-only matrix: {QUALITY_MATRIX_VERSION}")
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
    parser = argparse.ArgumentParser(description="Run installed greenfield pre-confirm and commit-only release simulations.")
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
        "--include-commit-recovery-proof",
        action="store_true",
        help="Prove installed SIGKILL recovery, exact same-hash retry, and fsync rollback.",
    )
    parser.add_argument(
        "--skip-commit-recovery-proof",
        action="store_false",
        dest="include_commit_recovery_proof",
        help="Skip installed commit recovery proof for local debugging only; this is not release proof.",
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
        "--attempt-ledger-jsonl",
        default="",
        help="Persist redacted per-case attempt identities for exact interrupted-case replay.",
    )
    parser.add_argument(
        "--campaign-phase",
        default="single-matrix",
        help="Operator-facing campaign phase label such as failed-subset, 60-case-regression, volume-discovery, or 240-case-discovery.",
    )
    parser.add_argument(
        "--proof-tier",
        choices=("discovery", "release"),
        default="discovery",
        help="Separate high-volume discovery proof from release-grade proof in the persisted matrix payload.",
    )
    parser.add_argument(
        "--release-audit-file",
        default="",
        help="Hash-bound audit JSON required with --proof-tier release; ignored for discovery.",
    )
    parser.add_argument(
        "--release-audit-repo-root",
        default="",
        help="Repository root used to resolve the sealed release audit trail.",
    )
    parser.add_argument(
        "--sealed-release-input-root",
        default="",
        help="Campaign-created input root required for release-tier proof.",
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
    parser.add_argument(
        "--evidence-output-dir",
        default="",
        help="External immutable evidence directory required for release proof; it must be outside --temp-parent.",
    )
    parser.add_argument(
        "--semantic-annotations-file",
        default="",
        help="Optional blinded atomic-annotation file for deterministic semantic release scoring.",
    )
    parser.add_argument(
        "--evaluation-split-manifest",
        default="",
        help="Frozen split and floor manifest required with --semantic-annotations-file.",
    )
    parser.add_argument(
        "--final-holdout-run-ledger",
        default="",
        help="Exclusive one-shot disclosure ledger required for release-tier semantic proof.",
    )
    parser.add_argument(
        "--implementation-revision",
        default="",
        help="Full 40-character Git revision of the implementation under final holdout proof.",
    )
    parser.add_argument(
        "--distribution-provenance-file",
        default="",
        help="Exact verified distribution provenance; it is never copied into protected input custody.",
    )
    return parser.parse_args(argv)


def _release_path_without_symlink_segments(value: str | Path, *, label: str) -> Path:
    path = Path(value).expanduser()
    absolute_path = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute_path.anchor)
    for part in absolute_path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RuntimeError(f"release proof {label} crosses a symlink: {current}")
    return absolute_path


def _require_sealed_release_input_root(
    *,
    proof_tier: str,
    case_files: Sequence[str],
    release_audit_file: str,
    release_audit_repo_root: Path,
    sealed_root: str,
    semantic_annotations_file: str,
    evaluation_split_manifest: str,
) -> None:
    if proof_tier_from_value(proof_tier) != "release":
        return
    if not sealed_root.strip():
        raise RuntimeError("release proof requires --sealed-release-input-root")
    unresolved_root = _release_path_without_symlink_segments(
        sealed_root,
        label="sealed input root",
    )
    root = unresolved_root.resolve()
    if not root.is_dir():
        raise RuntimeError("release proof sealed input root does not exist")
    values = (*case_files, semantic_annotations_file, evaluation_split_manifest)
    if not all(str(value or "").strip() for value in values):
        raise RuntimeError("release proof requires sealed case, annotation, and evaluation-manifest inputs")
    for value in values:
        unresolved_path = _release_path_without_symlink_segments(
            str(value),
            label="sealed input",
        )
        path = unresolved_path.resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("release proof inputs must live under the sealed input root") from exc
        if not path.is_file():
            raise RuntimeError(f"release proof sealed input is missing or unsafe: {path.name}")
    if release_audit_file:
        unresolved_audit_root = _release_path_without_symlink_segments(
            release_audit_repo_root,
            label="audit root",
        )
        if unresolved_audit_root.resolve() != root:
            raise RuntimeError("release proof audit root must equal the sealed input root")
        audit_path = _release_path_without_symlink_segments(
            release_audit_file,
            label="audit input",
        ).resolve()
        try:
            audit_path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("release proof audit input must live under the sealed input root") from exc


def _final_holdout_run_from_args(
    args: argparse.Namespace,
    *,
    sealed_input_root: str,
) -> _FinalHoldoutRun | None:
    if proof_tier_from_value(str(args.proof_tier)) != "release":
        return None
    ledger_token = str(getattr(args, "final_holdout_run_ledger", "") or "").strip()
    revision = str(getattr(args, "implementation_revision", "") or "").strip().casefold()
    output_token = str(getattr(args, "output_json", "") or "").strip()
    if not ledger_token:
        raise RuntimeError("release proof requires --final-holdout-run-ledger")
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise RuntimeError("release proof requires a full --implementation-revision")
    if not output_token:
        raise RuntimeError("release proof requires --output-json for terminal holdout evidence")
    provenance_token = str(getattr(args, "distribution_provenance_file", "") or "").strip()
    if not provenance_token:
        raise RuntimeError("release proof requires --distribution-provenance-file")
    ledger_path = _release_path_without_symlink_segments(
        ledger_token,
        label="final holdout run ledger",
    ).resolve()
    if ledger_path.exists():
        raise RuntimeError("final holdout run ledger already exists; the holdout cannot be rerun")
    sealed_root = Path(sealed_input_root).expanduser().resolve()
    provenance_path = _release_path_without_symlink_segments(
        provenance_token,
        label="distribution provenance",
    )
    provenance = verify_distribution_provenance(
        provenance_path=provenance_path,
        implementation_revision=revision,
    )
    try:
        ledger_path.relative_to(sealed_root)
    except ValueError:
        pass
    else:
        raise RuntimeError("final holdout run ledger must live outside the sealed input root")
    return _FinalHoldoutRun(
        ledger_path=ledger_path,
        holdout_path=Path(str(args.semantic_annotations_file)).expanduser().resolve(),
        evaluation_manifest_path=Path(str(args.evaluation_split_manifest)).expanduser().resolve(),
        case_paths=tuple(
            Path(str(value)).expanduser().resolve()
            for value in (getattr(args, "case_file", ()) or ())
        ),
        implementation_revision=revision,
        distribution_provenance_sha256=str(provenance["sha256"]),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    evidence_output_token = str(getattr(args, "evidence_output_dir", "") or "").strip()
    release_audit_repo_root = (
        Path(str(args.release_audit_repo_root)).expanduser()
        if str(args.release_audit_repo_root or "").strip()
        else REPO_ROOT
    )
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
    sealed_input_root = str(args.sealed_release_input_root or "").strip()
    if not sealed_input_root:
        # Missing proof flags are actionable before a caller has named sealed inputs.
        _raise_for_invalid_campaign_policy(
            config=campaign_config,
            install_mode=str(args.install_mode),
            include_browser_proof=bool(args.include_browser_proof),
            include_commit_recovery_proof=bool(args.include_commit_recovery_proof),
            allow_skipped_browser_proof=bool(args.allow_skipped_browser_proof),
            allow_partial_stressor_coverage=bool(args.allow_partial_stressor_coverage),
            semantic_annotations_file=str(args.semantic_annotations_file or ""),
            evaluation_split_manifest=str(args.evaluation_split_manifest or ""),
        )
    _require_sealed_release_input_root(
        proof_tier=str(args.proof_tier),
        case_files=args.case_file or (),
        release_audit_file=str(args.release_audit_file or ""),
        release_audit_repo_root=release_audit_repo_root,
        sealed_root=sealed_input_root,
        semantic_annotations_file=str(args.semantic_annotations_file or ""),
        evaluation_split_manifest=str(args.evaluation_split_manifest or ""),
    )
    release_audit_repo_root = release_audit_repo_root.resolve()
    _raise_for_invalid_campaign_policy(
        config=campaign_config,
        install_mode=str(args.install_mode),
        include_browser_proof=bool(args.include_browser_proof),
        include_commit_recovery_proof=bool(args.include_commit_recovery_proof),
        allow_skipped_browser_proof=bool(args.allow_skipped_browser_proof),
        allow_partial_stressor_coverage=bool(args.allow_partial_stressor_coverage),
        semantic_annotations_file=str(args.semantic_annotations_file or ""),
        evaluation_split_manifest=str(args.evaluation_split_manifest or ""),
    )
    if campaign_config.proof_tier == "release" and not evidence_output_token:
        raise RuntimeError("release proof requires --evidence-output-dir")
    if evidence_output_token:
        validate_retained_evidence_output_dir(
            output_dir=Path(evidence_output_token),
            temp_parent=Path(args.temp_parent),
        )
    final_holdout_run = _final_holdout_run_from_args(args, sealed_input_root=sealed_input_root)
    if final_holdout_run is not None:
        install_script = Path(args.dist_dir).expanduser().resolve() / "install.sh"
        if not install_script.is_file():
            raise RuntimeError("final holdout preflight requires the exact release distribution")
        browser_issues = browser_runtime_preflight_issues() if bool(args.include_browser_proof) else ()
        if browser_issues:
            raise RuntimeError("final holdout browser preflight failed: " + "; ".join(browser_issues))
    output_path = (
        Path(str(args.output_json)).expanduser().resolve()
        if str(args.output_json or "").strip()
        else None
    )
    lease = acquire_matrix_run_lease(
        temp_parent=Path(args.temp_parent),
        output_path=output_path,
    )
    try:
        try:
            if final_holdout_run is not None:
                final_holdout_run.claim()
            selected_cases = _load_cli_case_files(
                args.case_file or (),
                enforce_lexical_controls=final_holdout_run is None,
            )
            planned_cases = selected_cases or default_cases()
            release_audits = (
                load_release_audit_file(
                    Path(str(args.release_audit_file)),
                    repo_root=release_audit_repo_root,
                )
                if str(args.release_audit_file or "").strip()
                else ()
            )
            if campaign_config.proof_tier == "release":
                corpus_provenance = evaluate_frozen_evaluation_contract(
                    repo_root=Path(sealed_input_root),
                    manifest_path=Path(str(args.evaluation_split_manifest)),
                    final_holdout_path=Path(str(args.semantic_annotations_file)),
                )
            else:
                corpus_provenance = discovery_corpus_summary(planned_cases)
            _raise_for_invalid_campaign_policy(
                config=campaign_config,
                install_mode=str(args.install_mode),
                include_browser_proof=bool(args.include_browser_proof),
                include_commit_recovery_proof=bool(args.include_commit_recovery_proof),
                allow_skipped_browser_proof=bool(args.allow_skipped_browser_proof),
                allow_partial_stressor_coverage=bool(args.allow_partial_stressor_coverage),
                release_corpus_issues=(
                    tuple(corpus_provenance.get("issues") or ())
                    if campaign_config.proof_tier == "release" and isinstance(corpus_provenance, Mapping)
                    else ()
                ),
                semantic_annotations_file=str(args.semantic_annotations_file or ""),
                evaluation_split_manifest=str(args.evaluation_split_manifest or ""),
            )
            return_code = _execute_matrix_campaign(
                args=args,
                selected_cases=selected_cases,
                planned_cases=planned_cases,
                release_audits=release_audits,
                release_audit_repo_root=release_audit_repo_root,
                campaign_config=campaign_config,
                corpus_provenance=corpus_provenance,
                output_path=output_path,
                lease=lease,
                finalize_lease=True,
                retained_evidence_run_id=(
                    final_holdout_run.run_id if final_holdout_run is not None else ""
                ),
            )
            if final_holdout_run is not None and final_holdout_run.claimed:
                if output_path is None or not output_path.is_file():
                    raise RuntimeError("final holdout execution did not persist its result payload")
                final_holdout_run.complete(
                    result_path=output_path,
                    outcome="passed" if return_code == 0 else "failed",
                    retained_evidence_manifest=retained_evidence_manifest_path(
                        Path(evidence_output_token)
                    ),
                )
            return return_code
        except BaseException as error:
            if final_holdout_run is not None and final_holdout_run.claimed:
                interrupted = lease.temp_namespace / "final-holdout-interrupted-result.v2.json"
                write_matrix_payload(
                    output_path=interrupted,
                    payload={
                        "version": QUALITY_MATRIX_VERSION,
                        "status": "interrupted",
                        "error_type": type(error).__name__,
                    },
                )
                retained_manifest = retained_evidence_manifest_path(Path(evidence_output_token))
                if retained_manifest.is_file():
                    final_holdout_run.complete(
                        result_path=interrupted,
                        outcome="interrupted",
                        retained_evidence_manifest=retained_manifest,
                    )
            raise
    finally:
        if not lease.released:
            lease.release()


def _execute_matrix_campaign(
    *,
    args: argparse.Namespace,
    selected_cases: tuple[GreenfieldMatrixCase, ...],
    planned_cases: tuple[GreenfieldMatrixCase, ...],
    release_audits: Sequence[Mapping[str, Any]],
    release_audit_repo_root: Path = REPO_ROOT,
    campaign_config: MatrixCampaignConfig,
    corpus_provenance: Any,
    output_path: Path | None,
    lease: Any,
    finalize_lease: bool = False,
    before_product_execution: Callable[[], None] | None = None,
    retained_evidence_run_id: str = "",
) -> int:
    """Run one fully isolated proof campaign under its output lease."""

    temp_parent = lease.temp_namespace
    profiled_cases = assign_model_profiles(selected_cases or planned_cases)
    telemetry = MatrixTelemetryWriter(campaign_config.telemetry_jsonl)
    provenance_summary = getattr(corpus_provenance, "summary", {})
    approved_audit_bindings = (
        provenance_summary.get("approved_audit_bindings")
        if isinstance(provenance_summary, Mapping)
        and isinstance(provenance_summary.get("approved_audit_bindings"), Mapping)
        else {}
    )
    require_recovery_release_binding = (
        campaign_config.proof_tier == "release"
        and not str(getattr(args, "semantic_annotations_file", "") or "").strip()
    )
    recovery_case = (
        select_recovery_case(
            planned_cases,
            proof_tier=campaign_config.proof_tier,
            approved_audit_bindings=approved_audit_bindings,
            require_release_binding=require_recovery_release_binding,
        )
        if bool(args.include_commit_recovery_proof)
        else None
    )
    with command_lifecycle_observer(_matrix_command_observer(telemetry)):
        results = run_matrix(
            dist_dir=Path(args.dist_dir),
            version=str(args.version),
            temp_parent=temp_parent,
            cases=profiled_cases,
            include_browser_proof=bool(args.include_browser_proof),
            install_mode=str(args.install_mode),
            telemetry_jsonl=campaign_config.telemetry_jsonl,
            campaign_phase=campaign_config.phase,
            proof_tier=campaign_config.proof_tier,
            stop_after_failures=campaign_config.stop_after_failures,
            stop_after_cluster_failures=campaign_config.stop_after_cluster_failures,
            required_stressors=campaign_config.required_stressors,
            incremental_output_json=output_path,
            attempt_ledger_jsonl=(
                Path(str(args.attempt_ledger_jsonl)).expanduser().resolve()
                if str(args.attempt_ledger_jsonl or "").strip()
                else None
            ),
            allow_partial_stressor_coverage=bool(args.allow_partial_stressor_coverage),
            release_audits=release_audits,
            release_audit_repo_root=release_audit_repo_root,
            semantic_annotations_file=str(getattr(args, "semantic_annotations_file", "") or ""),
            evaluation_split_manifest=str(getattr(args, "evaluation_split_manifest", "") or ""),
            evidence_output_dir=(
                Path(str(getattr(args, "evidence_output_dir", ""))).expanduser().resolve()
                if str(getattr(args, "evidence_output_dir", "") or "").strip()
                else None
            ),
            retained_evidence_run_id=retained_evidence_run_id,
            before_product_execution=before_product_execution,
        )
        commit_recovery = (
            run_installed_commit_recovery_proof(
                dist_dir=Path(args.dist_dir),
                version=str(args.version),
                temp_parent=temp_parent,
                recovery_case=recovery_case,
                require_release_binding=require_recovery_release_binding,
                release_audit_binding=(
                    approved_audit_bindings.get(recovery_case.case_id)
                    if recovery_case is not None
                    and isinstance(approved_audit_bindings.get(recovery_case.case_id), Mapping)
                    else None
                ),
            )
            if bool(args.include_commit_recovery_proof)
            else None
        )
        unavailable_provider = (
            run_unavailable_provider_proof(
                dist_dir=Path(args.dist_dir),
                version=str(args.version),
                temp_parent=temp_parent,
                case=next(
                    (
                        case
                        for case in profiled_cases
                        if case_expectation(case) != CLARIFICATION_REQUIRED_EXPECTATION
                    ),
                    profiled_cases[0],
                ),
            )
            if campaign_config.proof_tier == "release"
            else {"status": "not_requested", "issues": []}
        )
    evidence_output_token = str(getattr(args, "evidence_output_dir", "") or "").strip()
    retained_evidence_required = campaign_config.proof_tier == "release" and hasattr(args, "evidence_output_dir")
    retained_manifest = (
        retained_evidence_manifest_path(Path(evidence_output_token))
        if evidence_output_token
        else None
    )
    retained_issues = (
        retained_evidence_manifest_issues(
            retained_manifest,
            expected_case_ids=tuple(_retained_case_id(case) for case in profiled_cases),
            expected_run_id=retained_evidence_run_id,
        )
        if retained_manifest is not None
        else ("release proof did not retain external evidence",)
        if retained_evidence_required
        else ()
    )
    retained_evidence = {
        "status": "passed" if retained_manifest is not None and not retained_issues else "not_requested"
        if retained_manifest is None and not retained_evidence_required
        else "failed",
        "manifest": str(retained_manifest) if retained_manifest is not None else "",
        "manifest_sha256": _sha256_file(retained_manifest) if retained_manifest is not None else "",
        "issues": list(retained_issues),
    }
    browser_proof = browser_proof_summary(results, include_browser_proof=bool(args.include_browser_proof))
    platform_leakage_proof = _platform_leakage_proof_summary(results)
    cleanup_proof = temp_cleanup_proof(temp_parent)
    if finalize_lease:
        try:
            lease.release()
        except RuntimeError as exc:
            cleanup_proof = {
                **cleanup_proof,
                "status": "failed",
                "run_namespace_cleanup": "failed",
                "run_namespace_cleanup_error": str(exc),
            }
        else:
            cleanup_proof = {
                **cleanup_proof,
                "run_namespace_cleanup": "passed",
            }
    profile_proof = model_profile_release_proof(
        results,
        require_complete=campaign_config.proof_tier == "release",
    )
    browser_status = str(browser_proof.get("status") or "").strip()
    browser_passed = browser_status == "passed" or (
        browser_status == "skipped"
        and campaign_config.proof_tier == "discovery"
    )
    platform_leakage_passed = str(platform_leakage_proof.get("status") or "").strip() == "passed"
    cleanup_passed = str(cleanup_proof.get("status") or "").strip() == "passed"
    semantic_release = _semantic_release_report(
        args=args,
        cases=profiled_cases,
        results=results,
    )
    semantic_digests = _as_mapping(semantic_release.get("normalized_semantic_digests"))
    metamorphic_output = evaluate_metamorphic_outputs(
        cases=profiled_cases,
        results=results,
        semantic_digests=semantic_digests,
    )
    onboarding_quality_scorecard = build_onboarding_quality_scorecard(
        results=results,
        browser_proof=browser_proof,
        platform_leakage_proof=platform_leakage_proof,
        metamorphic_output=metamorphic_output,
        model_profile_proof=profile_proof,
        unavailable_provider_proof=unavailable_provider,
        commit_recovery_proof=commit_recovery,
    )
    semantic_release_passed = semantic_release.get("status") in {"not_requested", "passed"}
    passed = (
        all(result.quality.passed for result in results)
        and profile_proof.get("status") == "passed"
        and unavailable_provider.get("status") in {"not_requested", "passed"}
        and (commit_recovery is None or commit_recovery.passed)
        and browser_passed
        and platform_leakage_passed
        and cleanup_passed
        and bool(metamorphic_output.get("passed"))
        and semantic_release_passed
        and (
            not retained_evidence_required
            or retained_evidence.get("status") == "passed"
        )
        and (
            campaign_config.proof_tier != "release"
            or onboarding_quality_scorecard.get("status") == "passed"
        )
    )
    payload = {
        "version": QUALITY_MATRIX_VERSION,
        "status": (
            "passed"
            if passed and campaign_config.proof_tier == "release"
            else "discovery-passed"
            if passed
            else "failed"
        ),
        "proof_scope": {
            "model_profiles": "real_installed_source_cited_authored_preconfirm_cases",
            "timing_tiers": "strict_standard_under_60_rescue_under_90_deep_under_120",
            "lower_capability_model": "real_installed_gpt-5.6-luna-medium_authored_preconfirm",
            "unavailable_provider": (
                "real_installed_fail_closed_no_write"
                if unavailable_provider.get("status") == "passed"
                else "not_requested"
                if unavailable_provider.get("status") == "not_requested"
                else "failed"
            ),
            "commit_recovery_path": (
                COMMIT_RECOVERY_PROOF_SCOPE if commit_recovery is not None else "not_requested"
            ),
            "browser_surface_proof": (
                BROWSER_SURFACE_PROOF_SCOPE if bool(args.include_browser_proof) else "not_requested"
            ),
        },
        "corpus_provenance": (
            corpus_provenance.to_dict()
            if hasattr(corpus_provenance, "to_dict")
            else dict(corpus_provenance)
            if isinstance(corpus_provenance, Mapping)
            else corpus_provenance
        ),
        "results": [result.to_dict() for result in results],
        "campaign": campaign_summary(
            cases=planned_cases,
            results=results,
            config=campaign_config,
            stopped_reason=stop_reason(results, campaign_config),
            semantic_digests=semantic_digests,
        ),
        "metamorphic_output": metamorphic_output,
        "browser_surface_proof": browser_proof,
        "platform_domain_leakage_proof": platform_leakage_proof,
        "temp_cleanup_proof": cleanup_proof,
        "onboarding_quality_scorecard": onboarding_quality_scorecard,
        "model_profile_proof": profile_proof,
        "unavailable_provider_proof": unavailable_provider,
        "semantic_release": semantic_release,
        "retained_evidence": retained_evidence,
        "proof_run": lease.to_dict(),
    }
    if commit_recovery is not None:
        payload["commit_recovery_proof"] = commit_recovery.to_dict()
    write_matrix_payload(output_path=output_path, payload=payload)
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human_summary(results)
    return 0 if payload["status"] in {"passed", "discovery-passed"} else 1


def _semantic_release_report(
    *,
    args: argparse.Namespace,
    cases: Sequence[GreenfieldMatrixCase],
    results: Sequence[GreenfieldMatrixResult],
) -> dict[str, Any]:
    annotations_token = str(getattr(args, "semantic_annotations_file", "") or "").strip()
    manifest_token = str(getattr(args, "evaluation_split_manifest", "") or "").strip()
    if not annotations_token and not manifest_token:
        return {"status": "not_requested", "passed": True}
    if not annotations_token or not manifest_token:
        return {
            "status": "failed",
            "passed": False,
            "issues": ["semantic release scoring requires both annotations and a frozen split manifest"],
        }
    annotations_path = Path(annotations_token).expanduser().resolve()
    manifest_path = Path(manifest_token).expanduser().resolve()
    try:
        contract = evaluate_frozen_evaluation_contract(
            repo_root=Path(str(args.sealed_release_input_root)).expanduser().resolve()
            if str(args.sealed_release_input_root or "").strip()
            else REPO_ROOT,
            manifest_path=manifest_path,
            final_holdout_path=annotations_path,
        )
        payload = _parse_json_object(annotations_path.read_text(encoding="utf-8"))
        annotation_rows = payload.get("annotations")
        selected_case_ids = {str(case.case_id or case.slug).strip() for case in cases}
        annotation_case_ids = (
            {
                str(row.get("case_id") or "").strip()
                for row in annotation_rows
                if isinstance(row, Mapping)
            }
            if isinstance(annotation_rows, Sequence)
            and not isinstance(annotation_rows, (str, bytes, bytearray))
            else set()
        )
        if selected_case_ids != annotation_case_ids:
            return {
                "status": "failed",
                "passed": False,
                "evaluation_contract": contract,
                "issues": ["semantic release case set does not exactly match the frozen holdout"],
            }
        annotations, annotation_issues = validate_atomic_annotations(
            cases=cases,
            rows=annotation_rows,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        return {
            "status": "failed",
            "passed": False,
            "issues": [f"semantic release inputs are invalid: {type(error).__name__}"],
        }
    if not contract.get("passed") or annotation_issues:
        return {
            "status": "failed",
            "passed": False,
            "evaluation_contract": contract,
            "issues": list(
                dict.fromkeys(
                    [
                        "frozen evaluation contract failed"
                        if not contract.get("passed")
                        else "atomic annotations failed validation"
                    ]
                )
            ),
        }
    report = evaluate_semantic_release(
        cases=cases,
        annotations=annotations,
        results=results,
        floors=_as_mapping(contract.get("frozen_floors")),
        release_required_slices=_as_mapping(contract.get("required_release_slices")),
    )
    report["evaluation_contract"] = contract
    return report


def _load_cli_case_files(
    case_files: Sequence[str],
    *,
    enforce_lexical_controls: bool = True,
) -> tuple[GreenfieldMatrixCase, ...]:
    cases: list[GreenfieldMatrixCase] = []
    for case_file in case_files:
        token = str(case_file or "").strip()
        if token:
            cases.extend(
                load_case_file(
                    Path(token),
                    enforce_lexical_controls=enforce_lexical_controls,
                )
            )
    return tuple(cases)


if __name__ == "__main__":
    raise SystemExit(main())
