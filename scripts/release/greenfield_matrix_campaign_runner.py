"""Tiered campaign runner for high-volume greenfield matrix proof."""

from __future__ import annotations

import argparse
import atexit
from collections.abc import Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any
from typing import Mapping

SCRIPT_DIR = Path(__file__).resolve().parent
MATRIX_SCRIPT = SCRIPT_DIR / "greenfield_preconfirm_matrix.py"
CAMPAIGN_RUNNER_VERSION = "odylith.greenfield.matrix.tiered-campaign.v1"
DEFAULT_DISCOVERY_WORKERS_BY_TIER = {
    "failed-subset": 1,
    "60-case-regression": 2,
    "volume-discovery": 2,
    "240-case-discovery": 2,
}

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import greenfield_matrix_campaign_shard_runner as _shard_runner  # noqa: E402
import greenfield_matrix_shards as _matrix_shards  # noqa: E402
from greenfield_matrix_campaign_shard_runner import CampaignShard  # noqa: E402
from greenfield_matrix_campaign_shard_runner import ShardRunResult  # noqa: E402,F401
from greenfield_matrix_campaign_shard_runner import _cleanup_shard_temp_parent  # noqa: E402,F401
from greenfield_matrix_campaign_shard_runner import _forward_shard_telemetry  # noqa: E402,F401
from greenfield_matrix_campaign_shard_runner import _matrix_command  # noqa: E402,F401
from greenfield_matrix_campaign_shard_runner import _run_command_with_progress  # noqa: E402,F401
from greenfield_matrix_campaign_progress import CampaignProgressWriter  # noqa: E402
from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_evaluation_contract import evaluate_frozen_evaluation_contract  # noqa: E402
from greenfield_matrix_corpus_provenance import load_release_audit_file  # noqa: E402
from greenfield_matrix_failure_response import campaign_failure_clusters  # noqa: E402
from greenfield_matrix_failure_response import failure_response_plan  # noqa: E402
from greenfield_matrix_release_artifacts import repo_artifact_path  # noqa: E402
from greenfield_matrix_release_artifacts import sha256_file  # noqa: E402
from greenfield_matrix_release_artifacts import write_release_proof_input_snapshot_manifest  # noqa: E402
from greenfield_matrix_stressors import required_stressors_from_values  # noqa: E402
from greenfield_distribution_provenance import verify_distribution_provenance  # noqa: E402


REPO_ROOT = SCRIPT_DIR.parents[1]


@dataclass(frozen=True)
class ReleaseProofInputSnapshot:
    root: Path
    case_files: tuple[Path, ...]
    audit_file: Path | None
    manifest_path: Path
    input_references: tuple[dict[str, str], ...]
    semantic_annotations_file: Path | None = None
    evaluation_split_manifest: Path | None = None


def run_campaign(
    *,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    output_dir: Path,
    telemetry_dir: Path,
    failed_case_files: Sequence[Path] = (),
    regression_case_files: Sequence[Path] = (),
    volume_case_files: Sequence[Path] = (),
    deep_volume_case_files: Sequence[Path] = (),
    release_case_files: Sequence[Path] = (),
    discovery_max_workers: int = 0,
    failed_subset_max_workers: int | None = None,
    regression_max_workers: int | None = None,
    volume_max_workers: int | None = None,
    deep_volume_max_workers: int | None = None,
    stop_after_failures: int = 1,
    stop_after_cluster_failures: int = 1,
    require_high_variance_stressors: bool = False,
    required_stressors: Sequence[str] = (),
    require_release_readiness: bool = False,
    release_audit_file: Path | None = None,
    semantic_annotations_file: Path | None = None,
    evaluation_split_manifest: Path | None = None,
    final_holdout_run_ledger: Path | None = None,
    implementation_revision: str = "",
    progress_jsonl: Path | None = None,
    progress_json: Path | None = None,
    failed_subset_replay_dir: Path | None = None,
    stream_progress: bool = False,
) -> dict[str, Any]:
    """Run campaign tiers in order and stop before later tiers after failure evidence."""

    started = time.perf_counter()
    output_dir = Path(output_dir).expanduser().resolve()
    telemetry_dir = Path(telemetry_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    distribution_provenance: dict[str, str] | None = None
    distribution_provenance_path: Path | None = None
    if semantic_annotations_file is not None:
        if final_holdout_run_ledger is None:
            raise RuntimeError("semantic release proof requires a one-shot final holdout run ledger")
        revision = str(implementation_revision or "").strip().casefold()
        if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
            raise RuntimeError("semantic release proof requires a full implementation revision")
        distribution_provenance_path = Path(dist_dir).expanduser().resolve() / "build-provenance.v1.json"
        verified_provenance = verify_distribution_provenance(
            provenance_path=distribution_provenance_path,
            implementation_revision=revision,
        )
        distribution_provenance = {
            "kind": "distribution-build-provenance",
            **verified_provenance,
        }
    normalized_required_stressors = required_stressors_from_values(
        required_stressors,
        use_default=bool(require_high_variance_stressors),
    )
    release_proof_inputs = _release_proof_input_manifest(
        case_files=release_case_files,
        release_audit_file=release_audit_file,
        semantic_annotations_file=semantic_annotations_file,
        evaluation_split_manifest=evaluation_split_manifest,
    )
    if distribution_provenance is not None:
        release_proof_inputs.append(distribution_provenance)
    release_snapshot = _seal_release_proof_inputs(
        case_files=release_case_files,
        release_audit_file=release_audit_file,
        semantic_annotations_file=semantic_annotations_file,
        evaluation_split_manifest=evaluation_split_manifest,
        repo_root=REPO_ROOT,
        temp_parent=temp_parent,
        distribution_provenance_file=distribution_provenance_path,
    )
    sealed_release_case_files = release_snapshot.case_files if release_snapshot is not None else release_case_files
    sealed_release_audit_file = release_snapshot.audit_file if release_snapshot is not None else release_audit_file
    sealed_release_audit_repo_root = release_snapshot.root if release_snapshot is not None else None
    sealed_semantic_annotations = (
        release_snapshot.semantic_annotations_file if release_snapshot is not None else semantic_annotations_file
    )
    sealed_evaluation_manifest = (
        release_snapshot.evaluation_split_manifest if release_snapshot is not None else evaluation_split_manifest
    )
    snapshot_exit_cleanup = (
        atexit.register(shutil.rmtree, release_snapshot.root, ignore_errors=True)
        if release_snapshot is not None
        else None
    )
    progress = CampaignProgressWriter(
        jsonl_path=progress_jsonl or telemetry_dir / "campaign-progress.v1.jsonl",
        snapshot_path=progress_json or output_dir / "campaign-progress.v1.json",
        stream_progress=stream_progress,
    )
    tiers = (
        _discovery_tier(
            "failed-subset",
            failed_case_files,
            stop_after_failures=stop_after_failures,
            stop_after_cluster_failures=stop_after_cluster_failures,
            require_high_variance_stressors=False,
            required_stressors=(),
        ),
        _discovery_tier(
            "60-case-regression",
            regression_case_files,
            stop_after_failures=stop_after_failures,
            stop_after_cluster_failures=stop_after_cluster_failures,
            require_high_variance_stressors=require_high_variance_stressors,
            required_stressors=normalized_required_stressors,
        ),
        _discovery_tier(
            "volume-discovery",
            volume_case_files,
            stop_after_failures=stop_after_failures,
            stop_after_cluster_failures=stop_after_cluster_failures,
            require_high_variance_stressors=require_high_variance_stressors,
            required_stressors=normalized_required_stressors,
        ),
        _discovery_tier(
            "240-case-discovery",
            deep_volume_case_files,
            stop_after_failures=stop_after_failures,
            stop_after_cluster_failures=stop_after_cluster_failures,
            require_high_variance_stressors=require_high_variance_stressors,
            required_stressors=normalized_required_stressors,
        ),
        _release_tier(
            "release-proof",
            sealed_release_case_files,
            require_high_variance_stressors=require_high_variance_stressors,
            required_stressors=normalized_required_stressors,
            release_audit_file=sealed_release_audit_file,
            release_audit_repo_root=sealed_release_audit_repo_root,
            release_input_snapshot_root=sealed_release_audit_repo_root,
            semantic_annotations_file=sealed_semantic_annotations,
            evaluation_split_manifest=sealed_evaluation_manifest,
            final_holdout_run_ledger=final_holdout_run_ledger,
            implementation_revision=implementation_revision,
        ),
    )
    selected_shard_count = sum(len(shards) for shards in tiers)
    progress.emit(
        "campaign_started",
        {
            "selected_shard_count": selected_shard_count,
            "dist_dir": str(Path(dist_dir).expanduser().resolve()),
            "temp_parent": str(Path(temp_parent).expanduser().resolve()),
            "release_readiness_boundary": (
                "release readiness requires the release-proof tier; discovery tiers are failure-discovery evidence only"
            ),
        },
    )
    tier_results: list[dict[str, Any]] = []
    stopped_reason = ""
    for shards in tiers:
        if not shards:
            continue
        tier_name = shards[0].tier
        max_workers = _tier_max_workers(
            tier=tier_name,
            proof_tier=shards[0].proof_tier,
            discovery_max_workers=discovery_max_workers,
            failed_subset_max_workers=failed_subset_max_workers,
            regression_max_workers=regression_max_workers,
            volume_max_workers=volume_max_workers,
            deep_volume_max_workers=deep_volume_max_workers,
        )
        result = _run_tier(
            shards=shards,
            dist_dir=dist_dir,
            version=version,
            temp_parent=temp_parent,
            output_dir=output_dir / tier_name,
            telemetry_dir=telemetry_dir / tier_name,
            max_workers=max_workers,
            stop_after_failures=stop_after_failures,
            stop_after_cluster_failures=stop_after_cluster_failures,
            progress=progress,
        )
        tier_results.append(result)
        if result["status"] != "passed":
            stopped_reason = f"{tier_name}:{result.get('stop_reason') or 'failed'}"
            break
    release_readiness = _release_readiness_posture(tier_results)
    release_proof_input_references = list(
        release_snapshot.input_references if release_snapshot is not None else release_proof_inputs
    )
    if distribution_provenance is not None and distribution_provenance not in release_proof_input_references:
        release_proof_input_references.append(distribution_provenance)
    release_proof_input_issues = _release_proof_input_drift_issues(release_proof_input_references)
    if release_readiness["readiness"] == "proven" and release_proof_input_issues:
        release_readiness = {"completed": True, "status": "failed", "readiness": "failed"}
        stopped_reason = "release-proof-input-drift"
    execution_status = "passed" if tier_results and all(row["status"] == "passed" for row in tier_results) else "failed"
    if release_proof_input_issues:
        execution_status = "failed"
    status = _campaign_status(execution_status=execution_status, release_readiness=release_readiness)
    if not tier_results:
        execution_status = "skipped"
        status = "skipped"
        stopped_reason = "no-case-files"
    if require_release_readiness and release_readiness["readiness"] != "proven":
        execution_status = "failed"
        status = "failed"
        if not stopped_reason:
            stopped_reason = f"release-readiness-required:{release_readiness['readiness']}"
    clusters = campaign_failure_clusters(tier_results)
    failure_response = failure_response_plan(
        tier_results=tier_results,
        failure_clusters=clusters,
        stopped_reason=stopped_reason,
        release_readiness_proven=release_readiness["readiness"] == "proven",
    )
    failure_response["failed_subset_replay"] = _failed_subset_replay_artifacts(
        source_case_files=_campaign_source_case_files(
            failed_case_files=failed_case_files,
            regression_case_files=regression_case_files,
            volume_case_files=volume_case_files,
            deep_volume_case_files=deep_volume_case_files,
            release_case_files=sealed_release_case_files,
        ),
        failed_result_jsons=tuple(Path(path) for path in failure_response.get("failed_result_jsons", ())),
        output_dir=failed_subset_replay_dir or output_dir / "failed-subset-replay",
    )
    payload = {
        "version": CAMPAIGN_RUNNER_VERSION,
        "status": status,
        "execution_status": execution_status,
        "seconds": round(time.perf_counter() - started, 3),
        "dist_dir": str(Path(dist_dir).expanduser().resolve()),
        "temp_parent": str(Path(temp_parent).expanduser().resolve()),
        "output_dir": str(output_dir),
        "telemetry_dir": str(telemetry_dir),
        "stopped_reason": stopped_reason,
        "tiers": tier_results,
        "release_proof_completed": release_readiness["completed"],
        "release_proof_status": release_readiness["status"],
        "release_readiness_status": release_readiness["readiness"],
        "release_readiness_required": bool(require_release_readiness),
        "release_readiness_boundary": (
            "release readiness requires the release-proof tier; discovery tiers are failure-discovery evidence only"
        ),
        "release_proof_inputs": release_proof_inputs,
        "release_proof_snapshot": {
            "status": "sealed" if release_snapshot is not None else "not-sealed",
            "input_count": len(release_snapshot.input_references) if release_snapshot is not None else 0,
            "input_hashes": [
                {"kind": reference["kind"], "sha256": reference["sha256"]}
                for reference in (release_snapshot.input_references if release_snapshot is not None else ())
            ],
        },
        "release_proof_input_issues": release_proof_input_issues,
        "progress_jsonl": str(progress.jsonl_path),
        "progress_json": str(progress.snapshot_path),
        "default_discovery_workers_by_tier": dict(DEFAULT_DISCOVERY_WORKERS_BY_TIER),
        "failure_clusters": clusters,
        "failure_response": failure_response,
    }
    progress.emit(
        "campaign_finished",
        {
            "status": status,
            "stopped_reason": stopped_reason,
            "tier_count": len(tier_results),
            "failure_clusters": payload["failure_clusters"],
        },
    )
    if release_snapshot is not None:
        shutil.rmtree(release_snapshot.root)
        if snapshot_exit_cleanup is not None:
            atexit.unregister(snapshot_exit_cleanup)
    return payload


def _run_tier(**kwargs: Any) -> dict[str, Any]:
    return _shard_runner.run_tier(
        **kwargs,
        command_runner=_run_command_with_progress,
        telemetry_forwarder=_forward_shard_telemetry,
        temp_parent_cleaner=_cleanup_shard_temp_parent,
    )


def _discovery_tier(
    name: str,
    case_files: Sequence[Path],
    *,
    stop_after_failures: int,
    stop_after_cluster_failures: int,
    require_high_variance_stressors: bool,
    required_stressors: Sequence[str],
) -> tuple[CampaignShard, ...]:
    return tuple(
        CampaignShard(
            tier=name,
            case_file=Path(case_file).expanduser().resolve(),
            proof_tier="discovery",
            install_mode="seeded",
            include_browser_proof=False,
            include_rescue_smoke=False,
            include_natural_rescue_proof=False,
            stop_after_failures=max(0, int(stop_after_failures)),
            stop_after_cluster_failures=max(0, int(stop_after_cluster_failures)),
            require_high_variance_stressors=bool(require_high_variance_stressors),
            required_stressors=tuple(required_stressors),
        )
        for case_file in case_files
    )


def _release_tier(
    name: str,
    case_files: Sequence[Path],
    *,
    require_high_variance_stressors: bool,
    required_stressors: Sequence[str],
    release_audit_file: Path | None = None,
    release_audit_repo_root: Path | None = None,
    release_input_snapshot_root: Path | None = None,
    semantic_annotations_file: Path | None = None,
    evaluation_split_manifest: Path | None = None,
    final_holdout_run_ledger: Path | None = None,
    implementation_revision: str = "",
) -> tuple[CampaignShard, ...]:
    return tuple(
        CampaignShard(
            tier=name,
            case_file=Path(case_file).expanduser().resolve(),
            proof_tier="release",
            install_mode="full",
            include_browser_proof=True,
            include_rescue_smoke=True,
            include_natural_rescue_proof=True,
            stop_after_failures=0,
            stop_after_cluster_failures=0,
            require_high_variance_stressors=bool(require_high_variance_stressors),
            required_stressors=tuple(required_stressors),
            release_audit_file=Path(release_audit_file).expanduser().resolve() if release_audit_file else None,
            release_audit_repo_root=(
                Path(release_audit_repo_root).expanduser().resolve() if release_audit_repo_root else None
            ),
            release_input_snapshot_root=(
                Path(release_input_snapshot_root).expanduser().resolve()
                if release_input_snapshot_root
                else None
            ),
            semantic_annotations_file=(
                Path(semantic_annotations_file).expanduser().resolve()
                if semantic_annotations_file
                else None
            ),
            evaluation_split_manifest=(
                Path(evaluation_split_manifest).expanduser().resolve()
                if evaluation_split_manifest
                else None
            ),
            final_holdout_run_ledger=(
                Path(final_holdout_run_ledger).expanduser().resolve()
                if final_holdout_run_ledger
                else None
            ),
            implementation_revision=str(implementation_revision or "").strip().casefold(),
        )
        for case_file in case_files
    )


def _tier_max_workers(
    *,
    tier: str,
    proof_tier: str,
    discovery_max_workers: int,
    failed_subset_max_workers: int | None,
    regression_max_workers: int | None,
    volume_max_workers: int | None,
    deep_volume_max_workers: int | None,
) -> int:
    if proof_tier == "release":
        return 1
    overrides = {
        "failed-subset": failed_subset_max_workers,
        "60-case-regression": regression_max_workers,
        "volume-discovery": volume_max_workers,
        "240-case-discovery": deep_volume_max_workers,
    }
    if overrides.get(tier):
        return max(1, int(overrides[tier] or 0))
    if int(discovery_max_workers or 0) > 0:
        return max(1, int(discovery_max_workers))
    return int(DEFAULT_DISCOVERY_WORKERS_BY_TIER.get(tier, 2))


def _release_readiness_posture(tier_results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    release_tiers = [row for row in tier_results if row.get("tier") == "release-proof"]
    if not release_tiers:
        return {"completed": False, "status": "not-run", "readiness": "not-proven"}
    if not any(int(row.get("completed_shard_count") or 0) > 0 for row in release_tiers):
        return {"completed": False, "status": "failed-preflight", "readiness": "failed"}
    if all(row.get("status") == "passed" for row in release_tiers):
        return {"completed": True, "status": "passed", "readiness": "proven"}
    return {"completed": True, "status": "failed", "readiness": "failed"}


def _release_proof_input_manifest(
    *,
    case_files: Sequence[Path],
    release_audit_file: Path | None,
    semantic_annotations_file: Path | None = None,
    evaluation_split_manifest: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, str]]:
    """Bind every release-proof input so a later mutation cannot retain a valid claim."""

    references: list[dict[str, str]] = []

    def append_reference(kind: str, path: Path) -> None:
        reference = _proof_input_reference(kind, path)
        if any(existing["path"] == reference["path"] for existing in references):
            return
        references.append(reference)

    for path in case_files:
        append_reference("release-case-file", Path(path))
    if release_audit_file is not None:
        audit_path = Path(release_audit_file)
        append_reference("release-audit-file", audit_path)
        for reference in _release_audit_transitive_input_manifest(
            audit_path=audit_path,
            repo_root=repo_root,
        ):
            if not any(existing["path"] == reference["path"] for existing in references):
                references.append(reference)
    if semantic_annotations_file is not None:
        append_reference("semantic-annotations-file", Path(semantic_annotations_file))
    if evaluation_split_manifest is not None:
        manifest_path = Path(evaluation_split_manifest)
        append_reference("evaluation-split-manifest", manifest_path)
        tracked_path = _tracked_corpus_path(manifest_path=manifest_path, repo_root=repo_root)
        append_reference("evaluation-tracked-corpus", tracked_path)
    return references


def _release_audit_transitive_input_manifest(
    *,
    audit_path: Path,
    repo_root: Path,
) -> tuple[dict[str, str], ...]:
    """Include the trail consumed by a valid audit bundle in the final drift check."""

    root = Path(repo_root).expanduser().resolve()
    try:
        bundle = load_release_audit_file(audit_path, repo_root=root)
    except RuntimeError:
        # The release tier performs the authoritative structured audit preflight.
        return ()
    paths = (
        ("release-audit-source-case-file", bundle.source_case_file),
        ("release-audit-request-plan", bundle.audit_request_plan),
        ("release-audit-source-verifications", bundle.source_verifications),
        ("release-audit-review-results", bundle.review_results),
        *(
            (f"release-audit-source-verification:{audit.case_id}", audit.source_verification_path)
            for audit in bundle
        ),
        *(
            (f"release-audit-review-evidence:{audit.case_id}", audit.review_evidence_path)
            for audit in bundle
        ),
    )
    references: list[dict[str, str]] = []
    for kind, path_value in paths:
        artifact_path = repo_artifact_path(root, path_value)
        if artifact_path is not None:
            references.append(_proof_input_reference(kind, artifact_path))
    source_case_path = repo_artifact_path(root, bundle.source_case_file)
    if source_case_path is not None:
        for case in load_case_file(source_case_path):
            artifact_path = repo_artifact_path(root, case.provenance.source_artifact_path)
            if artifact_path is not None:
                references.append(
                    _proof_input_reference(
                        f"release-source-artifact:{case.case_id}",
                        artifact_path,
                    )
                )
    return tuple(references)


def _seal_release_proof_inputs(
    *,
    case_files: Sequence[Path],
    release_audit_file: Path | None,
    semantic_annotations_file: Path | None = None,
    evaluation_split_manifest: Path | None = None,
    repo_root: Path,
    temp_parent: Path,
    distribution_provenance_file: Path | None = None,
) -> ReleaseProofInputSnapshot | None:
    """Copy stable release inputs before execution so proof cannot observe later mutations."""

    if semantic_annotations_file is not None or evaluation_split_manifest is not None:
        if semantic_annotations_file is None or evaluation_split_manifest is None:
            raise RuntimeError("semantic release proof requires both annotations and an evaluation manifest")
        if distribution_provenance_file is None:
            raise RuntimeError("semantic release proof requires distribution build provenance")
        return _seal_semantic_release_inputs(
            case_files=case_files,
            semantic_annotations_file=semantic_annotations_file,
            evaluation_split_manifest=evaluation_split_manifest,
            repo_root=repo_root,
            temp_parent=temp_parent,
            distribution_provenance_file=distribution_provenance_file,
        )
    if not case_files or release_audit_file is None:
        return None
    root = Path(repo_root).expanduser().resolve()
    audit_path = Path(release_audit_file).expanduser().resolve()
    try:
        bundle = load_release_audit_file(audit_path, repo_root=root)
    except RuntimeError as exc:
        raise RuntimeError(f"release proof inputs could not be sealed: {exc}") from exc
    references = tuple(
        _release_proof_input_manifest(
            case_files=case_files,
            release_audit_file=audit_path,
            repo_root=root,
        )
    )
    source_paths = tuple(Path(reference["path"]).resolve() for reference in references)
    if not source_paths or audit_path not in source_paths:
        raise RuntimeError("release proof snapshot could not bind the audit bundle")
    snapshot_parent = Path(temp_parent).expanduser().resolve()
    snapshot_parent.mkdir(parents=True, exist_ok=True)
    snapshot_root = Path(tempfile.mkdtemp(prefix="odylith-release-inputs-", dir=snapshot_parent))
    copied_paths: dict[Path, Path] = {}
    try:
        for source_path in source_paths:
            try:
                relative_path = source_path.relative_to(root)
            except ValueError as exc:
                raise RuntimeError(f"release proof input is outside the repository: {source_path}") from exc
            destination = snapshot_root / relative_path
            _copy_hash_bound_release_input(source_path, destination)
            copied_paths[source_path] = destination
        snapshot_audit = copied_paths[audit_path]
        snapshot_bundle = load_release_audit_file(snapshot_audit, repo_root=snapshot_root)
        snapshot_cases = tuple(copied_paths[Path(path).expanduser().resolve()] for path in case_files)
        source_case_path = repo_artifact_path(snapshot_root, snapshot_bundle.source_case_file)
        if source_case_path is None or source_case_path not in snapshot_cases:
            raise RuntimeError("release proof case files do not match the sealed audit bundle")
        snapshot_references = tuple(
            _proof_input_reference(reference["kind"], copied_paths[Path(reference["path"]).resolve()])
            for reference in references
        )
        return ReleaseProofInputSnapshot(
            root=snapshot_root,
            case_files=snapshot_cases,
            audit_file=snapshot_audit,
            manifest_path=write_release_proof_input_snapshot_manifest(
                root=snapshot_root,
                case_files=snapshot_cases,
                audit_file=snapshot_audit,
                input_references=snapshot_references,
            ),
            input_references=snapshot_references,
        )
    except BaseException:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        raise


def _seal_semantic_release_inputs(
    *,
    case_files: Sequence[Path],
    semantic_annotations_file: Path,
    evaluation_split_manifest: Path,
    repo_root: Path,
    temp_parent: Path,
    distribution_provenance_file: Path,
) -> ReleaseProofInputSnapshot:
    root = Path(repo_root).expanduser().resolve()
    annotations_path = Path(semantic_annotations_file).expanduser().resolve()
    manifest_path = Path(evaluation_split_manifest).expanduser().resolve()
    case_paths = tuple(Path(path).expanduser().resolve() for path in case_files)
    if case_paths != (annotations_path,):
        raise RuntimeError("semantic release proof must run the complete holdout as one unsharded case file")
    tracked_path = _tracked_corpus_path(manifest_path=manifest_path, repo_root=root)
    provenance_path = Path(distribution_provenance_file).expanduser().resolve()
    sources = (annotations_path, manifest_path, tracked_path, provenance_path)
    snapshot_parent = Path(temp_parent).expanduser().resolve()
    snapshot_parent.mkdir(parents=True, exist_ok=True)
    snapshot_root = Path(tempfile.mkdtemp(prefix="odylith-semantic-release-inputs-", dir=snapshot_parent))
    try:
        snapshot_annotations = snapshot_root / "private/final-holdout.v1.json"
        snapshot_manifest = snapshot_root / manifest_path.relative_to(root)
        snapshot_tracked = snapshot_root / tracked_path.relative_to(root)
        snapshot_provenance = snapshot_root / "private/build-provenance.v1.json"
        destinations = (snapshot_annotations, snapshot_manifest, snapshot_tracked, snapshot_provenance)
        for source, destination in zip(sources, destinations, strict=True):
            _copy_hash_bound_release_input(source, destination)
        contract = evaluate_frozen_evaluation_contract(
            repo_root=snapshot_root,
            manifest_path=snapshot_manifest,
            final_holdout_path=snapshot_annotations,
        )
        if not contract.get("passed"):
            raise RuntimeError(
                "semantic release proof inputs failed their frozen contract: "
                + "; ".join(str(issue) for issue in contract.get("issues") or ())
            )
        references = tuple(
            _proof_input_reference(kind, path)
            for kind, path in (
                ("semantic-annotations-file", snapshot_annotations),
                ("evaluation-split-manifest", snapshot_manifest),
                ("evaluation-tracked-corpus", snapshot_tracked),
                ("distribution-build-provenance", snapshot_provenance),
            )
        )
        seal_path = snapshot_root / "semantic-release-input-snapshot.v1.json"
        seal_path.write_text(
            json.dumps(
                {
                    "version": "odylith.greenfield.semantic-release-input-snapshot.v1",
                    "inputs": list(references),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        with seal_path.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        return ReleaseProofInputSnapshot(
            root=snapshot_root,
            case_files=(snapshot_annotations,),
            audit_file=None,
            manifest_path=seal_path,
            input_references=references,
            semantic_annotations_file=snapshot_annotations,
            evaluation_split_manifest=snapshot_manifest,
        )
    except BaseException:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        raise


def _tracked_corpus_path(*, manifest_path: Path, repo_root: Path) -> Path:
    path = Path(manifest_path).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"evaluation split manifest is unreadable: {error}") from error
    tracked = payload.get("tracked_corpus") if isinstance(payload, Mapping) else None
    token = str(tracked.get("path") or "").strip() if isinstance(tracked, Mapping) else ""
    root = Path(repo_root).expanduser().resolve()
    candidate = (root / token).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise RuntimeError("evaluation tracked corpus escapes the repository") from error
    if not token or not candidate.is_file() or candidate.is_symlink():
        raise RuntimeError("evaluation tracked corpus is missing or unsafe")
    return candidate


def _copy_hash_bound_release_input(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"release proof input is missing: {source}")
    expected_hash = sha256_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    with destination.open("r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    if sha256_file(source) != expected_hash or sha256_file(destination) != expected_hash:
        raise RuntimeError(f"release proof input changed while being sealed: {source}")


def _proof_input_reference(kind: str, path: Path) -> dict[str, str]:
    resolved = Path(path).expanduser().resolve()
    return {
        "kind": kind,
        "path": str(resolved),
        "sha256": sha256_file(resolved) if resolved.is_file() else "",
    }


def _release_proof_input_drift_issues(references: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    issues: list[str] = []
    for reference in references:
        kind = str(reference.get("kind") or "release-proof-input")
        path_value = str(reference.get("path") or "").strip()
        expected_hash = str(reference.get("sha256") or "").strip()
        path = Path(path_value).expanduser() if path_value else None
        if path is None or not path.is_file():
            issues.append(f"{kind} is missing")
        elif not expected_hash:
            issues.append(f"{kind} is not hash-bound")
        elif sha256_file(path) != expected_hash:
            issues.append(f"{kind} changed after release-proof preflight")
    return tuple(issues)


def _campaign_status(*, execution_status: str, release_readiness: Mapping[str, Any]) -> str:
    if execution_status != "passed":
        return str(execution_status or "failed")
    return "release-ready" if release_readiness.get("readiness") == "proven" else "discovery-passed"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a tiered greenfield matrix campaign.")
    parser.add_argument("--dist-dir", required=True, help="Local release asset directory containing install.sh.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--temp-parent", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--telemetry-dir", required=True)
    parser.add_argument("--failed-case-file", action="append", default=None)
    parser.add_argument("--regression-case-file", action="append", default=None)
    parser.add_argument("--volume-case-file", action="append", default=None)
    parser.add_argument("--deep-volume-case-file", action="append", default=None)
    parser.add_argument("--release-case-file", action="append", default=None)
    parser.add_argument("--release-audit-file", default="")
    parser.add_argument("--semantic-annotations-file", default="")
    parser.add_argument("--evaluation-split-manifest", default="")
    parser.add_argument("--final-holdout-run-ledger", default="")
    parser.add_argument("--implementation-revision", default="")
    parser.add_argument(
        "--discovery-max-workers",
        type=int,
        default=0,
        help="Override every discovery tier worker count. Defaults use the tier policy profile.",
    )
    parser.add_argument("--failed-subset-max-workers", type=int, default=0)
    parser.add_argument("--regression-max-workers", type=int, default=0)
    parser.add_argument("--volume-max-workers", type=int, default=0)
    parser.add_argument("--deep-volume-max-workers", type=int, default=0)
    parser.add_argument("--stop-after-failures", type=int, default=1)
    parser.add_argument("--stop-after-cluster-failures", type=int, default=1)
    parser.add_argument("--require-high-variance-stressors", action="store_true")
    parser.add_argument(
        "--require-release-readiness",
        action="store_true",
        help="Fail the campaign unless the strict release-proof tier completes and proves release readiness.",
    )
    parser.add_argument("--required-stressor", action="append", default=None)
    parser.add_argument(
        "--progress-jsonl",
        default="",
        help="Optional merged campaign progress JSONL path. Defaults under --telemetry-dir.",
    )
    parser.add_argument(
        "--progress-json",
        default="",
        help="Optional live campaign progress snapshot path. Defaults next to --output-json.",
    )
    parser.add_argument(
        "--failed-subset-replay-dir",
        default="",
        help="Optional directory for automatically generated failed-subset replay shards.",
    )
    parser.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Do not print compact live progress lines to stderr while the campaign runs.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_campaign(
        dist_dir=Path(args.dist_dir),
        version=str(args.version),
        temp_parent=Path(args.temp_parent),
        output_dir=Path(args.output_json).expanduser().resolve().parent,
        telemetry_dir=Path(args.telemetry_dir),
        failed_case_files=_paths(args.failed_case_file or ()),
        regression_case_files=_paths(args.regression_case_file or ()),
        volume_case_files=_paths(args.volume_case_file or ()),
        deep_volume_case_files=_paths(args.deep_volume_case_file or ()),
        release_case_files=_paths(args.release_case_file or ()),
        discovery_max_workers=max(0, int(args.discovery_max_workers)),
        failed_subset_max_workers=_optional_positive_int(args.failed_subset_max_workers),
        regression_max_workers=_optional_positive_int(args.regression_max_workers),
        volume_max_workers=_optional_positive_int(args.volume_max_workers),
        deep_volume_max_workers=_optional_positive_int(args.deep_volume_max_workers),
        stop_after_failures=max(0, int(args.stop_after_failures)),
        stop_after_cluster_failures=max(0, int(args.stop_after_cluster_failures)),
        require_high_variance_stressors=bool(args.require_high_variance_stressors),
        required_stressors=tuple(args.required_stressor or ()),
        require_release_readiness=bool(args.require_release_readiness),
        release_audit_file=Path(str(args.release_audit_file)).expanduser().resolve()
        if str(args.release_audit_file or "").strip()
        else None,
        semantic_annotations_file=Path(str(args.semantic_annotations_file)).expanduser().resolve()
        if str(args.semantic_annotations_file or "").strip()
        else None,
        evaluation_split_manifest=Path(str(args.evaluation_split_manifest)).expanduser().resolve()
        if str(args.evaluation_split_manifest or "").strip()
        else None,
        final_holdout_run_ledger=Path(str(args.final_holdout_run_ledger)).expanduser().resolve()
        if str(args.final_holdout_run_ledger or "").strip()
        else None,
        implementation_revision=str(args.implementation_revision or ""),
        progress_jsonl=Path(str(args.progress_jsonl)).expanduser().resolve()
        if str(args.progress_jsonl or "").strip()
        else None,
        progress_json=Path(str(args.progress_json)).expanduser().resolve()
        if str(args.progress_json or "").strip()
        else None,
        failed_subset_replay_dir=Path(str(args.failed_subset_replay_dir)).expanduser().resolve()
        if str(args.failed_subset_replay_dir or "").strip()
        else None,
        stream_progress=not bool(args.quiet_progress),
    )
    output_json = Path(args.output_json).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("execution_status") == "passed" else 1


def _paths(values: Sequence[str]) -> tuple[Path, ...]:
    return tuple(Path(value).expanduser().resolve() for value in values if str(value).strip())


def _optional_positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _campaign_source_case_files(
    *,
    failed_case_files: Sequence[Path],
    regression_case_files: Sequence[Path],
    volume_case_files: Sequence[Path],
    deep_volume_case_files: Sequence[Path],
    release_case_files: Sequence[Path],
) -> tuple[Path, ...]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in (
        *failed_case_files,
        *regression_case_files,
        *volume_case_files,
        *deep_volume_case_files,
        *release_case_files,
    ):
        candidate = Path(path).expanduser().resolve()
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(candidate)
    return tuple(ordered)


def _failed_subset_replay_artifacts(
    *,
    source_case_files: Sequence[Path],
    failed_result_jsons: Sequence[Path],
    output_dir: Path,
) -> dict[str, Any]:
    """Materialize exact failed-subset replay shards when stable identity exists."""

    existing_source_files = tuple(path for path in source_case_files if Path(path).is_file())
    existing_result_files = tuple(path for path in failed_result_jsons if Path(path).is_file())
    if not existing_result_files:
        return {
            "status": "not-required",
            "reason": "no-replayable-failed-result-jsons",
            "case_count": 0,
            "files": [],
        }
    if not existing_source_files:
        return {
            "status": "unavailable",
            "reason": "source-case-files-missing",
            "case_count": 0,
            "files": [],
            "missing_source_case_files": [str(Path(path).expanduser().resolve()) for path in source_case_files],
            "failed_result_jsons": [str(Path(path).expanduser().resolve()) for path in existing_result_files],
        }
    try:
        payload = _matrix_shards.build_shards(
            case_files=existing_source_files,
            output_dir=Path(output_dir).expanduser().resolve(),
            failed_result_jsons=existing_result_files,
            shard_size=_matrix_shards.DEFAULT_SHARD_SIZE,
            regression_size=0,
            volume_size=0,
            deep_volume_size=0,
            release_size=0,
            required_stressors=(),
            failed_subset_only=True,
        )
    except RuntimeError as exc:
        return {
            "status": "unavailable",
            "reason": "failed-subset-replay-build-failed",
            "error": str(exc),
            "case_count": 0,
            "files": [],
            "source_case_files": [str(Path(path).expanduser().resolve()) for path in existing_source_files],
            "failed_result_jsons": [str(Path(path).expanduser().resolve()) for path in existing_result_files],
        }
    failed_tier = payload.get("tiers", {}).get("failed-subset", {})
    files = [str(path) for path in failed_tier.get("files", ()) if str(path).strip()]
    case_count = int(failed_tier.get("case_count") or 0)
    if case_count <= 0 or not files:
        return {
            "status": "unavailable",
            "reason": "failed-identity-not-exactly-replayable",
            "case_count": case_count,
            "files": files,
            "summary_json": str(payload.get("summary_json") or ""),
            "failed_case_identity_classes": payload.get("failed_case_identity_classes", {}),
        }
    return {
        "status": "written",
        "reason": "",
        "case_count": case_count,
        "files": files,
        "summary_json": str(payload.get("summary_json") or ""),
        "source_case_files": [str(Path(path).expanduser().resolve()) for path in existing_source_files],
        "failed_result_jsons": [str(Path(path).expanduser().resolve()) for path in existing_result_files],
        "next_tier": "failed-subset",
    }


if __name__ == "__main__":
    raise SystemExit(main())
