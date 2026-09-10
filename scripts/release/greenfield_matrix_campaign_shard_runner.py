"""Shard execution for tiered Greenfield matrix campaigns."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from collections.abc import Sequence
from concurrent.futures import FIRST_COMPLETED
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from dataclasses import dataclass
from dataclasses import replace
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time
from threading import Event
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
MATRIX_SCRIPT = SCRIPT_DIR / "greenfield_preconfirm_matrix.py"
_SUCCESSFUL_MATRIX_PAYLOAD_STATUSES = frozenset(("passed", "discovery-passed"))

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_matrix_campaign import missing_required_stressors  # noqa: E402
from greenfield_matrix_campaign_progress import CampaignProgressWriter  # noqa: E402
from greenfield_matrix_campaign_progress import first_cluster_at_threshold  # noqa: E402
from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_matrix_attempt_ledger import initialize_attempt_ledger  # noqa: E402
from greenfield_matrix_corpus_provenance import evaluate_release_corpus  # noqa: E402
from greenfield_matrix_corpus_provenance import load_release_audit_file  # noqa: E402
from greenfield_matrix_failure_response import write_synthetic_shard_payload  # noqa: E402
from greenfield_final_holdout_guard import complete_final_holdout_run  # noqa: E402
from greenfield_final_holdout_guard import read_final_holdout_run  # noqa: E402
from greenfield_matrix_release_artifacts import retained_evidence_manifest_issues  # noqa: E402
from greenfield_matrix_release_artifacts import seal_interrupted_retained_evidence  # noqa: E402
from greenfield_matrix_release_artifacts import sha256_file  # noqa: E402


@dataclass(frozen=True)
class CampaignShard:
    tier: str
    case_file: Path
    proof_tier: str
    install_mode: str
    include_browser_proof: bool
    stop_after_failures: int
    stop_after_cluster_failures: int
    require_high_variance_stressors: bool
    required_stressors: tuple[str, ...]
    release_audit_file: Path | None = None
    release_audit_repo_root: Path | None = None
    release_input_snapshot_root: Path | None = None
    semantic_annotations_file: Path | None = None
    evaluation_split_manifest: Path | None = None
    final_holdout_run_ledger: Path | None = None
    implementation_revision: str = ""
    distribution_provenance_file: Path | None = None
    evidence_output_dir: Path | None = None

    @property
    def name(self) -> str:
        return f"{self.tier}-{_slug(self.case_file.stem)}"


@dataclass(frozen=True)
class ShardRunResult:
    tier: str
    name: str
    case_file: str
    status: str
    returncode: int
    seconds: float
    output_json: str
    telemetry_jsonl: str
    temp_parent: str
    payload_status: str
    completed_case_count: int
    failed_case_count: int
    failure_clusters: tuple[dict[str, Any], ...]
    stdout_excerpt: str
    stderr_excerpt: str
    stop_reason: str = ""
    attempt_ledger_jsonl: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.returncode == 0
            and self.status == "passed"
            and self.payload_status in _SUCCESSFUL_MATRIX_PAYLOAD_STATUSES
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "name": self.name,
            "case_file": self.case_file,
            "status": self.status,
            "returncode": self.returncode,
            "seconds": self.seconds,
            "output_json": self.output_json,
            "telemetry_jsonl": self.telemetry_jsonl,
            "temp_parent": self.temp_parent,
            "payload_status": self.payload_status,
            "completed_case_count": self.completed_case_count,
            "failed_case_count": self.failed_case_count,
            "failure_clusters": list(self.failure_clusters),
            "stdout_excerpt": self.stdout_excerpt,
            "stderr_excerpt": self.stderr_excerpt,
            "stop_reason": self.stop_reason,
            "attempt_ledger_jsonl": self.attempt_ledger_jsonl,
        }


def run_tier(
    *,
    shards: Sequence[CampaignShard],
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    output_dir: Path,
    telemetry_dir: Path,
    max_workers: int,
    stop_after_failures: int,
    stop_after_cluster_failures: int,
    progress: CampaignProgressWriter,
    command_runner: Callable[..., tuple[subprocess.CompletedProcess[str], str]] | None = None,
    telemetry_forwarder: Callable[..., int] | None = None,
    temp_parent_cleaner: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    command_runner = command_runner or _run_command_with_progress
    telemetry_forwarder = telemetry_forwarder or _forward_shard_telemetry
    temp_parent_cleaner = temp_parent_cleaner or _cleanup_shard_temp_parent
    case_file_failure = _tier_case_file_preflight_failure(
        shards=shards,
        output_dir=output_dir,
        telemetry_dir=telemetry_dir,
        temp_parent=temp_parent,
    )
    if case_file_failure:
        invalid_release_corpus = case_file_failure.payload_status == "release-corpus-invalid"
        reason_prefix = "tier-release-corpus-invalid" if invalid_release_corpus else "tier-case-file-invalid"
        cluster = "campaign.release-corpus-invalid" if invalid_release_corpus else "campaign.case-file-invalid"
        result = {
            "tier": shards[0].tier,
            "status": "failed",
            "seconds": round(time.perf_counter() - started, 3),
            "selected_shard_count": len(shards),
            "completed_shard_count": 0,
            "stopped_early": True,
            "stop_reason": f"{reason_prefix}:{case_file_failure.name}",
            "max_workers": max(1, int(max_workers)),
            "cluster_counts": {cluster: 1},
            "shards": [case_file_failure.to_dict()],
        }
        progress.emit(
            "tier_completed",
            {
                "tier": shards[0].tier,
                "status": "failed",
                "stop_reason": result["stop_reason"],
                "selected_shard_count": len(shards),
                "completed_shard_count": 0,
                "cluster_counts": result["cluster_counts"],
            },
        )
        return result
    missing_stressors = _missing_tier_required_stressors(shards)
    if missing_stressors:
        result = {
            "tier": shards[0].tier,
            "status": "failed",
            "seconds": round(time.perf_counter() - started, 3),
            "selected_shard_count": len(shards),
            "completed_shard_count": 0,
            "stopped_early": True,
            "stop_reason": "tier-stressor-coverage-missing:" + ",".join(missing_stressors),
            "max_workers": max(1, int(max_workers)),
            "cluster_counts": {},
            "shards": [],
        }
        progress.emit(
            "tier_completed",
            {
                "tier": shards[0].tier,
                "status": "failed",
                "stop_reason": result["stop_reason"],
                "selected_shard_count": len(shards),
                "completed_shard_count": 0,
            },
        )
        return result
    max_workers = max(1, int(max_workers))
    results: list[ShardRunResult] = []
    pending = list(shards)
    running: set[Future[ShardRunResult]] = set()
    stop_reason = ""
    failed_case_count = 0
    cluster_counts: Counter[str] = Counter()
    stop_event = Event()
    progress.emit(
        "tier_started",
        {
            "tier": shards[0].tier,
            "selected_shard_count": len(shards),
            "max_workers": max_workers,
        },
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            while pending or running:
                while pending and not stop_reason and len(running) < max_workers:
                    shard = pending.pop(0)
                    future = executor.submit(
                        _run_shard,
                        shard=shard,
                        dist_dir=dist_dir,
                        version=version,
                        temp_parent=temp_parent,
                        output_dir=output_dir,
                        telemetry_dir=telemetry_dir,
                        stop_event=stop_event,
                        progress=progress,
                        command_runner=command_runner,
                        telemetry_forwarder=telemetry_forwarder,
                        temp_parent_cleaner=temp_parent_cleaner,
                    )
                    running.add(future)
                if not running:
                    break
                done, running = wait(running, return_when=FIRST_COMPLETED)
                for future in done:
                    result = future.result()
                    results.append(result)
                    if result.stop_reason and not stop_reason:
                        stop_reason = result.stop_reason
                        stop_event.set()
                    failed_case_count += _failed_case_count_increment(result)
                    for cluster in result.failure_clusters:
                        name = str(cluster.get("cluster") or "").strip()
                        if name:
                            cluster_counts[name] += int(cluster.get("count") or 1)
                    if stop_after_failures and failed_case_count >= stop_after_failures and not stop_reason:
                        stop_reason = f"failure-threshold:{stop_after_failures}:shard:{result.name}"
                        stop_event.set()
                    failed_case_count, cluster_counts = _merge_live_tier_failure_snapshot(
                        progress=progress,
                        tier=shards[0].tier,
                        failed_case_count=failed_case_count,
                        cluster_counts=cluster_counts,
                    )
                    if stop_after_cluster_failures and not stop_reason:
                        cluster, count = first_cluster_at_threshold(cluster_counts, stop_after_cluster_failures)
                        if cluster:
                            stop_reason = f"cluster-threshold:{cluster}:{count}"
                            stop_event.set()
                if stop_reason:
                    pending.clear()
        except (Exception, KeyboardInterrupt, SystemExit):
            stop_event.set()
            for future in running:
                future.cancel()
            raise
    failed_case_count, cluster_counts = _merge_live_tier_failure_snapshot(
        progress=progress,
        tier=shards[0].tier,
        failed_case_count=failed_case_count,
        cluster_counts=cluster_counts,
    )
    ordered = sorted(results, key=lambda row: (row.tier, row.name))
    status = "passed" if len(ordered) == len(shards) and all(row.passed for row in ordered) else "failed"
    payload = {
        "tier": shards[0].tier,
        "status": status,
        "seconds": round(time.perf_counter() - started, 3),
        "selected_shard_count": len(shards),
        "completed_shard_count": len(ordered),
        "stopped_early": len(ordered) < len(shards) or bool(stop_reason),
        "stop_reason": stop_reason,
        "max_workers": max_workers,
        "cluster_counts": dict(sorted(cluster_counts.items())),
        "shards": [row.to_dict() for row in ordered],
    }
    progress.emit(
        "tier_completed",
        {
            "tier": shards[0].tier,
            "status": status,
            "stop_reason": stop_reason,
            "selected_shard_count": len(shards),
            "completed_shard_count": len(ordered),
            "cluster_counts": dict(sorted(cluster_counts.items())),
        },
    )
    return payload


def _run_shard(
    *,
    shard: CampaignShard,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    output_dir: Path,
    telemetry_dir: Path,
    stop_event: Event,
    progress: CampaignProgressWriter,
    command_runner: Callable[..., tuple[subprocess.CompletedProcess[str], str]],
    telemetry_forwarder: Callable[..., int],
    temp_parent_cleaner: Callable[[Path], None],
) -> ShardRunResult:
    output_json = output_dir / f"{shard.name}.result.v1.json"
    telemetry_jsonl = telemetry_dir / f"{shard.name}.telemetry.v1.jsonl"
    attempt_ledger_jsonl = telemetry_dir / f"{shard.name}.attempts.v1.jsonl"
    _reset_shard_run_files(
        output_json=output_json,
        telemetry_jsonl=telemetry_jsonl,
        attempt_ledger_jsonl=attempt_ledger_jsonl,
    )
    if shard.case_file.is_file() and not _is_complete_semantic_release((shard,)):
        initialize_attempt_ledger(attempt_ledger_jsonl, load_case_file(shard.case_file))
    shard_temp_parent = _prepare_shard_temp_parent(
        base_temp_parent=temp_parent,
        shard=shard,
        temp_parent_cleaner=temp_parent_cleaner,
    )
    started = time.perf_counter()
    command = _matrix_command(
        shard=shard,
        dist_dir=dist_dir,
        version=version,
        temp_parent=shard_temp_parent,
        output_json=output_json,
        telemetry_jsonl=telemetry_jsonl,
        attempt_ledger_jsonl=attempt_ledger_jsonl,
    )
    progress.emit(
        "shard_started",
        {
            "tier": shard.tier,
            "shard": shard.name,
            "case_file": str(shard.case_file),
            "output_json": str(output_json),
            "telemetry_jsonl": str(telemetry_jsonl),
            "attempt_ledger_jsonl": str(attempt_ledger_jsonl),
            "temp_parent": str(shard_temp_parent),
        },
    )
    cleanup_error = ""
    try:
        completed, stop_reason = command_runner(
            command=command,
            telemetry_jsonl=telemetry_jsonl,
            shard=shard,
            stop_event=stop_event,
            progress=progress,
            telemetry_forwarder=telemetry_forwarder,
        )
        seconds = round(time.perf_counter() - started, 3)
        payload = _read_json(output_json)
        if not payload:
            payload = write_synthetic_shard_payload(
                output_json=output_json,
                shard=shard,
                completed=completed,
                stop_reason=stop_reason,
                live_failure_snapshot=progress.shard_failure_snapshot(shard=shard.name),
                attempt_ledger_jsonl=attempt_ledger_jsonl,
            )
        campaign = payload.get("campaign") if isinstance(payload.get("campaign"), dict) else {}
        clusters = tuple(
            cluster
            for cluster in campaign.get("failure_clusters", ())
            if isinstance(cluster, dict)
        )
        process_failure_cluster = _shard_process_failure_cluster(
            shard=shard,
            completed=completed,
            stop_reason=stop_reason,
            clusters=clusters,
            failed_case_count=int(campaign.get("failed_case_count") or 0),
        )
        if process_failure_cluster:
            clusters = (*clusters, process_failure_cluster)
        payload_status = str(payload.get("status") or "")
        result = ShardRunResult(
            tier=shard.tier,
            name=shard.name,
            case_file=str(shard.case_file),
            status=(
                "stopped"
                if stop_reason
                else "passed"
                if completed.returncode == 0 and _successful_matrix_payload(
                    payload_status=payload_status,
                    campaign=campaign,
                    proof_tier=shard.proof_tier,
                )
                else "failed"
            ),
            returncode=completed.returncode,
            seconds=seconds,
            output_json=str(output_json),
            telemetry_jsonl=str(telemetry_jsonl),
            temp_parent=str(shard_temp_parent),
            payload_status=payload_status,
            completed_case_count=int(campaign.get("completed_case_count") or 0),
            failed_case_count=max(
                int(campaign.get("failed_case_count") or 0),
                1 if process_failure_cluster else 0,
            ),
            failure_clusters=clusters,
            stdout_excerpt=_excerpt(completed.stdout),
            stderr_excerpt=_excerpt(completed.stderr),
            stop_reason=stop_reason,
            attempt_ledger_jsonl=str(attempt_ledger_jsonl),
        )
    except OSError as exc:
        result = ShardRunResult(
            tier=shard.tier,
            name=shard.name,
            case_file=str(shard.case_file),
            status="failed",
            returncode=127,
            seconds=round(time.perf_counter() - started, 3),
            output_json=str(output_json),
            telemetry_jsonl=str(telemetry_jsonl),
            temp_parent=str(shard_temp_parent),
            payload_status="",
            completed_case_count=0,
            failed_case_count=1,
            failure_clusters=(
                {
                    "cluster": "campaign.shard-launch-failed",
                    "count": 1,
                    "cases": [shard.name],
                    "example_issue": str(exc),
                },
            ),
            stdout_excerpt="",
            stderr_excerpt=_excerpt(str(exc)),
            stop_reason="shard-launch-failed",
            attempt_ledger_jsonl=str(attempt_ledger_jsonl),
        )
        result = _result_with_replayable_synthetic_payload(
            result=result,
            output_json=output_json,
            shard=shard,
            completed=subprocess.CompletedProcess(command, 127, "", str(exc)),
            progress=progress,
            forced_cluster="campaign.shard-launch-failed",
            detail=str(exc),
            failure_status="shard-launch-failed",
            attempt_ledger_jsonl=attempt_ledger_jsonl,
        )
    finally:
        _terminalize_reaped_semantic_child(
            shard=shard,
            result_path=telemetry_dir / f"{shard.name}.interrupted.v2.json",
            temp_parent=shard_temp_parent,
        )
        try:
            temp_parent_cleaner(shard_temp_parent)
        except RuntimeError as exc:
            cleanup_error = str(exc)
    if cleanup_error:
        result = _result_with_shard_cleanup_failure(result, cleanup_error)
        result = _result_with_replayable_synthetic_payload(
            result=result,
            output_json=output_json,
            shard=shard,
            completed=subprocess.CompletedProcess(
                command,
                result.returncode or 1,
                result.stdout_excerpt,
                result.stderr_excerpt,
            ),
            progress=progress,
            forced_cluster="campaign.shard-temp-cleanup-failed",
            detail=cleanup_error,
            failure_status="shard-temp-cleanup-failed",
            attempt_ledger_jsonl=attempt_ledger_jsonl,
        )
    lifecycle_issue = _semantic_holdout_lifecycle_issue(shard=shard, shard_passed=result.passed)
    if lifecycle_issue:
        result = replace(
            result,
            status="failed",
            returncode=result.returncode or 1,
            failed_case_count=max(1, result.failed_case_count),
            failure_clusters=(
                *result.failure_clusters,
                {
                    "cluster": "campaign.final-holdout-lifecycle-invalid",
                    "count": 1,
                    "cases": [shard.name],
                    "example_issue": lifecycle_issue,
                },
            ),
            stop_reason=result.stop_reason or "final-holdout-lifecycle-invalid",
        )
    progress.emit(
        "shard_completed",
        {
            "tier": shard.tier,
            "shard": shard.name,
            "status": result.status,
            "returncode": result.returncode,
            "seconds": result.seconds,
            "completed_case_count": result.completed_case_count,
            "failed_case_count": result.failed_case_count,
            "failure_clusters": list(result.failure_clusters),
            "stop_reason": result.stop_reason,
            "temp_parent": result.temp_parent,
        },
    )
    return result


def _successful_matrix_payload(
    *,
    payload_status: str,
    campaign: dict[str, Any],
    proof_tier: str,
) -> bool:
    if payload_status == "passed":
        return True
    if proof_tier != "discovery" or payload_status != "discovery-passed":
        return False
    return int(campaign.get("failed_case_count") or 0) == 0 and not campaign.get("failure_clusters")


def _reset_shard_run_files(
    *,
    output_json: Path,
    telemetry_jsonl: Path,
    attempt_ledger_jsonl: Path | None = None,
) -> None:
    """Remove prior shard result and telemetry before launching a new attempt."""

    paths = (
        output_json,
        telemetry_jsonl,
        telemetry_jsonl.with_suffix(telemetry_jsonl.suffix + ".stdout"),
        telemetry_jsonl.with_suffix(telemetry_jsonl.suffix + ".stderr"),
    )
    if attempt_ledger_jsonl is not None:
        paths = (*paths, attempt_ledger_jsonl)
    for path in paths:
        try:
            if path.exists() or path.is_symlink():
                path.unlink()
        except OSError as exc:
            raise RuntimeError(f"unable to reset shard run file {path}: {exc}") from exc


def _merge_live_tier_failure_snapshot(
    *,
    progress: CampaignProgressWriter,
    tier: str,
    failed_case_count: int,
    cluster_counts: Counter[str],
) -> tuple[int, Counter[str]]:
    snapshot = progress.tier_failure_snapshot(tier=tier)
    failed = max(int(failed_case_count), int(snapshot.get("failed_case_count") or 0))
    merged = Counter(cluster_counts)
    for cluster, count in _mapping(snapshot.get("cluster_counts")).items():
        name = str(cluster).strip()
        if name:
            merged[name] = max(int(merged.get(name) or 0), int(count or 0))
    return failed, merged


def _failed_case_count_increment(result: ShardRunResult) -> int:
    if result.passed:
        return 0
    if result.failed_case_count > 0:
        return result.failed_case_count
    if result.status == "stopped" and result.stop_reason:
        return 0
    return 1


def _result_with_replayable_synthetic_payload(
    *,
    result: ShardRunResult,
    output_json: Path,
    shard: CampaignShard,
    completed: subprocess.CompletedProcess[str],
    progress: CampaignProgressWriter,
    forced_cluster: str,
    detail: str,
    failure_status: str,
    attempt_ledger_jsonl: Path | None = None,
) -> ShardRunResult:
    payload = write_synthetic_shard_payload(
        output_json=output_json,
        shard=shard,
        completed=completed,
        stop_reason=result.stop_reason,
        live_failure_snapshot=progress.shard_failure_snapshot(shard=shard.name),
        force_failed=True,
        forced_cluster=forced_cluster,
        forced_detail=detail,
        failure_status=failure_status,
        attempt_ledger_jsonl=attempt_ledger_jsonl,
    )
    campaign = _mapping(payload.get("campaign"))
    clusters = tuple(_mapping_rows(campaign.get("failure_clusters"))) or result.failure_clusters
    return replace(
        result,
        payload_status=str(payload.get("status") or result.payload_status),
        completed_case_count=max(
            result.completed_case_count,
            int(campaign.get("completed_case_count") or 0),
        ),
        failed_case_count=max(
            result.failed_case_count,
            int(campaign.get("failed_case_count") or 0),
        ),
        failure_clusters=clusters,
    )


def _prepare_shard_temp_parent(
    *,
    base_temp_parent: Path,
    shard: CampaignShard,
    temp_parent_cleaner: Callable[[Path], None] | None = None,
) -> Path:
    """Give each concurrent shard an isolated cleanup-proof scope."""

    path = _shard_temp_parent(base_temp_parent=base_temp_parent, shard=shard)
    cleaner = temp_parent_cleaner or _cleanup_shard_temp_parent
    cleaner(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _shard_temp_parent(*, base_temp_parent: Path, shard: CampaignShard) -> Path:
    base = Path(base_temp_parent).expanduser().resolve()
    return base / _slug(shard.tier) / _slug(shard.name)


def _cleanup_shard_temp_parent(path: Path) -> None:
    target = Path(path).expanduser().resolve()
    try:
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
    except OSError as exc:
        raise RuntimeError(f"unable to remove shard temp parent {target}: {exc}") from exc
    if target.exists():
        raise RuntimeError(f"shard temp parent still exists after cleanup: {target}")


def _result_with_shard_cleanup_failure(result: ShardRunResult, detail: str) -> ShardRunResult:
    cluster = {
        "cluster": "campaign.shard-temp-cleanup-failed",
        "count": 1,
        "cases": [result.name],
        "example_issue": detail[:500],
    }
    return replace(
        result,
        status="failed",
        returncode=result.returncode if result.returncode else 1,
        failed_case_count=max(1, result.failed_case_count),
        failure_clusters=tuple((*result.failure_clusters, cluster)),
        stderr_excerpt=_excerpt(" ".join(item for item in (result.stderr_excerpt, detail) if item)),
        stop_reason=result.stop_reason or "shard-temp-cleanup-failed",
    )


def _shard_process_failure_cluster(
    *,
    shard: CampaignShard,
    completed: subprocess.CompletedProcess[str],
    stop_reason: str,
    clusters: Sequence[dict[str, Any]],
    failed_case_count: int,
) -> dict[str, Any]:
    if stop_reason or int(completed.returncode) == 0 or clusters or int(failed_case_count) > 0:
        return {}
    detail = _tail_excerpt(" ".join(item for item in (completed.stderr, completed.stdout) if item))
    return {
        "cluster": "campaign.shard-process-failed",
        "count": 1,
        "cases": [shard.name],
        "example_issue": detail or f"shard exited with return code {completed.returncode} before case telemetry completed",
    }


def _run_command_with_progress(
    *,
    command: Sequence[str],
    telemetry_jsonl: Path,
    shard: CampaignShard,
    stop_event: Event,
    progress: CampaignProgressWriter,
    telemetry_forwarder: Callable[..., int] | None = None,
) -> tuple[subprocess.CompletedProcess[str], str]:
    stdout_path = telemetry_jsonl.with_suffix(telemetry_jsonl.suffix + ".stdout")
    stderr_path = telemetry_jsonl.with_suffix(telemetry_jsonl.suffix + ".stderr")
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stop_reason = ""
    telemetry_offset = 0
    forward = telemetry_forwarder or _forward_shard_telemetry
    with stdout_path.open("w+", encoding="utf-8") as stdout_handle, stderr_path.open(
        "w+",
        encoding="utf-8",
    ) as stderr_handle:
        process = subprocess.Popen(
            list(command),
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=True,
        )
        stop_requested = False
        own_stop_grace_until = 0.0
        try:
            while process.poll() is None:
                telemetry_offset = forward(
                    telemetry_jsonl=telemetry_jsonl,
                    offset=telemetry_offset,
                    shard=shard,
                    progress=progress,
                )
                decision = progress.tier_stop_decision(
                    tier=shard.tier,
                    current_shard=shard.name,
                    stop_after_failures=shard.stop_after_failures,
                    stop_after_cluster_failures=shard.stop_after_cluster_failures,
                )
                if decision and not stop_event.is_set():
                    if progress.mark_tier_stop_emitted(shard.tier):
                        progress.emit(
                            "tier_stop_requested",
                            {
                                "tier": shard.tier,
                                "shard": shard.name,
                                "stop_reason": str(decision.get("reason") or ""),
                                "origin_shard": str(decision.get("origin_shard") or ""),
                                "failed_case_count": int(decision.get("failed_case_count") or 0),
                                "cluster_counts": dict(_mapping(decision.get("cluster_counts"))),
                            },
                        )
                    stop_event.set()
                    if str(decision.get("origin_shard") or "") == shard.name:
                        own_stop_grace_until = time.perf_counter() + 1.5
                if stop_event.is_set() and not stop_requested:
                    decision = progress.tier_stop_decision(
                        tier=shard.tier,
                        current_shard=shard.name,
                        stop_after_failures=shard.stop_after_failures,
                        stop_after_cluster_failures=shard.stop_after_cluster_failures,
                    )
                    if (
                        str(decision.get("origin_shard") or "") == shard.name
                        and own_stop_grace_until
                        and time.perf_counter() < own_stop_grace_until
                    ):
                        time.sleep(0.25)
                        continue
                    if process.poll() is None:
                        stop_reason = str(decision.get("reason") or "") or "aborted-after-tier-stop"
                        _interrupt_process(process)
                        stop_requested = True
                time.sleep(0.25)
            returncode = process.wait()
            _reap_process_group(process)
        except BaseException:
            _interrupt_process(process)
            raise
        forward(
            telemetry_jsonl=telemetry_jsonl,
            offset=telemetry_offset,
            shard=shard,
            progress=progress,
        )
        stdout_handle.seek(0)
        stderr_handle.seek(0)
        stdout = stdout_handle.read()
        stderr = stderr_handle.read()
    _unlink_quietly(stdout_path)
    _unlink_quietly(stderr_path)
    return subprocess.CompletedProcess(list(command), returncode, stdout, stderr), stop_reason


def _forward_shard_telemetry(
    *,
    telemetry_jsonl: Path,
    offset: int,
    shard: CampaignShard,
    progress: CampaignProgressWriter,
) -> int:
    if not telemetry_jsonl.is_file():
        return offset
    try:
        with telemetry_jsonl.open("r", encoding="utf-8") as handle:
            handle.seek(offset)
            while True:
                position = handle.tell()
                line = handle.readline()
                if not line:
                    return handle.tell()
                if not line.endswith("\n"):
                    return position
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    progress.forward_shard_telemetry(shard=shard, row=row)
    except OSError:
        return offset


def _interrupt_process(process: subprocess.Popen[str]) -> None:
    _signal_process_group(process, signal.SIGINT)
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        _signal_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _signal_process_group(process, signal.SIGKILL)
            process.wait()
    _reap_process_group(process)


def _reap_process_group(process: subprocess.Popen[str]) -> None:
    """Ensure no descendant from the shard session survives its leader."""

    if not hasattr(os, "killpg"):
        if process.poll() is None:
            process.wait()
        return
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return
    except PermissionError:
        return
    _signal_process_group(process, signal.SIGTERM)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            return
        time.sleep(0.05)
    _signal_process_group(process, signal.SIGKILL)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            return
        time.sleep(0.05)
    raise RuntimeError("shard process group could not be fully reaped")


def _signal_process_group(process: subprocess.Popen[str], requested_signal: int) -> None:
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, requested_signal)
        elif process.poll() is None:
            process.send_signal(requested_signal)
    except ProcessLookupError:
        return


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        return


def _matrix_command(
    *,
    shard: CampaignShard,
    dist_dir: Path,
    version: str,
    temp_parent: Path,
    output_json: Path,
    telemetry_jsonl: Path,
    attempt_ledger_jsonl: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(MATRIX_SCRIPT),
        "--dist-dir",
        str(Path(dist_dir).expanduser().resolve()),
        "--version",
        str(version),
        "--temp-parent",
        str(Path(temp_parent).expanduser().resolve()),
        "--case-file",
        str(shard.case_file),
        "--output-json",
        str(output_json),
        "--telemetry-jsonl",
        str(telemetry_jsonl),
        "--campaign-phase",
        shard.tier,
        "--proof-tier",
        shard.proof_tier,
        "--install-mode",
        shard.install_mode,
    ]
    if attempt_ledger_jsonl is not None:
        command.extend(["--attempt-ledger-jsonl", str(attempt_ledger_jsonl)])
    if shard.include_browser_proof:
        command.append("--include-browser-proof")
    else:
        command.append("--allow-skipped-browser-proof")
    command.append(
        "--include-commit-recovery-proof"
        if shard.proof_tier == "release"
        else "--skip-commit-recovery-proof"
    )
    if shard.stop_after_failures:
        command.extend(["--stop-after-failures", str(shard.stop_after_failures)])
    if shard.stop_after_cluster_failures:
        command.extend(["--stop-after-cluster-failures", str(shard.stop_after_cluster_failures)])
    for stressor in shard.required_stressors:
        token = str(stressor or "").strip()
        if token:
            command.extend(["--required-stressor", token])
    if shard.release_audit_file is not None:
        command.extend(["--release-audit-file", str(shard.release_audit_file)])
    if shard.release_audit_repo_root is not None:
        command.extend(["--release-audit-repo-root", str(shard.release_audit_repo_root)])
    if shard.release_input_snapshot_root is not None:
        command.extend(["--sealed-release-input-root", str(shard.release_input_snapshot_root)])
    if shard.semantic_annotations_file is not None:
        command.extend(["--semantic-annotations-file", str(shard.semantic_annotations_file)])
    if shard.evaluation_split_manifest is not None:
        command.extend(["--evaluation-split-manifest", str(shard.evaluation_split_manifest)])
    if shard.final_holdout_run_ledger is not None:
        command.extend(["--final-holdout-run-ledger", str(shard.final_holdout_run_ledger)])
    if shard.implementation_revision:
        command.extend(["--implementation-revision", shard.implementation_revision])
    if shard.distribution_provenance_file is not None:
        command.extend(["--distribution-provenance-file", str(shard.distribution_provenance_file)])
    if shard.evidence_output_dir is not None:
        command.extend(["--evidence-output-dir", str(shard.evidence_output_dir)])
    if shard.proof_tier == "discovery" and shard.required_stressors:
        command.append("--allow-partial-stressor-coverage")
    return command


def _tier_case_file_preflight_failure(
    *,
    shards: Sequence[CampaignShard],
    output_dir: Path,
    telemetry_dir: Path,
    temp_parent: Path,
) -> ShardRunResult | None:
    release_shards = tuple(shard for shard in shards if shard.proof_tier == "release")
    semantic_release = _is_complete_semantic_release(release_shards)
    if not semantic_release:
        for shard in shards:
            if not shard.case_file.exists():
                continue
            try:
                load_case_file(shard.case_file)
            except RuntimeError as exc:
                return ShardRunResult(
                    tier=shard.tier,
                    name=shard.name,
                    case_file=str(shard.case_file),
                    status="failed",
                    returncode=2,
                    seconds=0.0,
                    output_json=str(output_dir / f"{shard.name}.result.v1.json"),
                    telemetry_jsonl=str(telemetry_dir / f"{shard.name}.telemetry.v1.jsonl"),
                    temp_parent=str(_shard_temp_parent(base_temp_parent=temp_parent, shard=shard)),
                    payload_status="case-file-invalid",
                    completed_case_count=0,
                    failed_case_count=1,
                    failure_clusters=(
                        {
                            "cluster": "campaign.case-file-invalid",
                            "count": 1,
                            "cases": [shard.name],
                            "example_issue": _tail_excerpt(str(exc)),
                            "replay_scope": "source-shard",
                            "shard_replay_case_file": str(shard.case_file),
                        },
                    ),
                    stdout_excerpt="",
                    stderr_excerpt=_excerpt(str(exc)),
                    stop_reason="case-file-invalid",
                )
    if release_shards and not semantic_release:
        audit_file = release_shards[0].release_audit_file
        if audit_file is None:
            return _release_corpus_preflight_failure(
                shard=release_shards[0],
                output_dir=output_dir,
                telemetry_dir=telemetry_dir,
                temp_parent=temp_parent,
                detail="release proof requires --release-audit-file",
            )
        try:
            audit_repo_root = release_shards[0].release_audit_repo_root
            audits = (
                load_release_audit_file(audit_file, repo_root=audit_repo_root)
                if audit_repo_root is not None
                else load_release_audit_file(audit_file)
            )
            individual_failure: tuple[CampaignShard, Any] | None = None
            for shard in release_shards:
                shard_cases = load_case_file(shard.case_file)
                shard_case_ids = {case.case_id for case in shard_cases}
                shard_audits = tuple(audit for audit in audits if audit.case_id in shard_case_ids)
                evaluation = (
                    evaluate_release_corpus(shard_cases, shard_audits, repo_root=audit_repo_root)
                    if audit_repo_root is not None
                    else evaluate_release_corpus(shard_cases, shard_audits)
                )
                if not evaluation.passed and individual_failure is None:
                    individual_failure = (shard, evaluation)
            if individual_failure is not None:
                shard, evaluation = individual_failure
                return _release_corpus_preflight_failure(
                    shard=shard,
                    output_dir=output_dir,
                    telemetry_dir=telemetry_dir,
                    temp_parent=temp_parent,
                    detail="invalid greenfield release case file: " + "; ".join(evaluation.issues),
                )
            cases = tuple(case for shard in release_shards for case in load_case_file(shard.case_file))
            evaluation = (
                evaluate_release_corpus(cases, audits, repo_root=audit_repo_root)
                if audit_repo_root is not None
                else evaluate_release_corpus(cases, audits)
            )
        except RuntimeError as exc:
            return _release_corpus_preflight_failure(
                shard=release_shards[0],
                output_dir=output_dir,
                telemetry_dir=telemetry_dir,
                temp_parent=temp_parent,
                detail=str(exc),
            )
        if not evaluation.passed:
            return _release_corpus_preflight_failure(
                shard=release_shards[0],
                output_dir=output_dir,
                telemetry_dir=telemetry_dir,
                temp_parent=temp_parent,
                detail="invalid greenfield release corpus: " + "; ".join(evaluation.issues),
            )
    return None


def _is_complete_semantic_release(shards: Sequence[CampaignShard]) -> bool:
    """Keep semantic holdout proof distinct from audited source-corpus proof."""

    if len(shards) != 1:
        return False
    shard = shards[0]
    revision = str(shard.implementation_revision or "").strip().casefold()
    return bool(
        shard.semantic_annotations_file is not None
        and shard.case_file == shard.semantic_annotations_file
        and shard.evaluation_split_manifest is not None
        and shard.final_holdout_run_ledger is not None
        and shard.release_input_snapshot_root is not None
        and shard.distribution_provenance_file is not None
        and shard.evidence_output_dir is not None
        and len(revision) == 40
        and all(character in "0123456789abcdef" for character in revision)
    )


def _terminalize_reaped_semantic_child(
    *,
    shard: CampaignShard,
    result_path: Path,
    temp_parent: Path,
) -> bool:
    """Terminalize a claimed ledger only after the shard process has been reaped."""

    if not _is_complete_semantic_release((shard,)) or shard.final_holdout_run_ledger is None:
        return False
    try:
        ledger = read_final_holdout_run(shard.final_holdout_run_ledger)
    except RuntimeError:
        return False
    if ledger.get("status") != "claimed":
        return False
    path = Path(result_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout-parent-interruption.v1",
                "status": "interrupted",
                "reason": "release child exited after claim without a terminal outcome",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        if shard.evidence_output_dir is None:
            raise RuntimeError("semantic release interruption has no external evidence root")
        manifest = seal_interrupted_retained_evidence(
            output_dir=shard.evidence_output_dir,
            result_path=path,
            temp_parent=temp_parent,
            run_id=str(ledger.get("run_id") or ""),
        )
        complete_final_holdout_run(
            ledger_path=shard.final_holdout_run_ledger,
            result_path=path,
            outcome="interrupted",
            retained_evidence_manifest=manifest,
        )
    except (OSError, RuntimeError, json.JSONDecodeError, ValueError):
        return False
    return True


def _semantic_holdout_lifecycle_issue(*, shard: CampaignShard, shard_passed: bool) -> str:
    if not _is_complete_semantic_release((shard,)) or shard.final_holdout_run_ledger is None:
        return ""
    try:
        ledger = read_final_holdout_run(shard.final_holdout_run_ledger)
    except RuntimeError:
        return "semantic release child did not persist its exclusive final-holdout ledger"
    status = str(ledger.get("status") or "")
    if status not in {"passed", "failed", "interrupted"}:
        if status == "claimed":
            return "semantic release child could not terminalize because retained evidence was not safely sealed"
        return "semantic release child left a non-terminal final-holdout ledger"
    if shard_passed and status != "passed":
        return f"semantic release shard passed while its final-holdout outcome was {status}"
    retained = ledger.get("retained_evidence")
    retained = retained if isinstance(retained, dict) else {}
    manifest_path = Path(str(retained.get("manifest_path") or ""))
    expected_hash = str(retained.get("manifest_sha256") or "")
    if not manifest_path.is_file():
        return f"semantic release child {status} without intact retained evidence"
    retained_issues = retained_evidence_manifest_issues(
        manifest_path,
        require_passed_cases=status == "passed",
    )
    if (
        retained_issues
        or not _read_json(manifest_path).get("case_ids")
        or sha256_file(manifest_path) != expected_hash
    ):
        return f"semantic release child {status} without intact retained evidence"
    return ""


def _release_corpus_preflight_failure(
    *,
    shard: CampaignShard,
    output_dir: Path,
    telemetry_dir: Path,
    temp_parent: Path,
    detail: str,
) -> ShardRunResult:
    return ShardRunResult(
        tier=shard.tier,
        name=shard.name,
        case_file=str(shard.case_file),
        status="failed",
        returncode=2,
        seconds=0.0,
        output_json=str(output_dir / f"{shard.name}.result.v1.json"),
        telemetry_jsonl=str(telemetry_dir / f"{shard.name}.telemetry.v1.jsonl"),
        temp_parent=str(_shard_temp_parent(base_temp_parent=temp_parent, shard=shard)),
        payload_status="release-corpus-invalid",
        completed_case_count=0,
        failed_case_count=1,
        failure_clusters=(
            {
                "cluster": "campaign.release-corpus-invalid",
                "count": 1,
                "cases": [shard.name],
                "example_issue": _tail_excerpt(detail),
                "replay_scope": "release-corpus",
            },
        ),
        stdout_excerpt="",
        stderr_excerpt=_excerpt(detail),
        stop_reason="release-corpus-invalid",
    )


def _missing_tier_required_stressors(shards: Sequence[CampaignShard]) -> tuple[str, ...]:
    if not shards:
        return ()
    if _is_complete_semantic_release(shards):
        return ()
    required = tuple(
        dict.fromkeys(
            str(stressor).strip()
            for shard in shards
            for stressor in shard.required_stressors
            if str(stressor).strip()
        )
    )
    if not required:
        return ()
    cases = []
    for shard in shards:
        cases.extend(load_case_file(shard.case_file))
    return missing_required_stressors(tuple(cases), required)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _excerpt(value: str, *, limit: int = 1200) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _tail_excerpt(value: str, *, limit: int = 1200) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return "..." + text[-limit:].lstrip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _mapping_rows(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, dict))


def _slug(value: str) -> str:
    parts: list[str] = []
    last_dash = False
    for char in str(value or "").casefold():
        if char.isalnum():
            parts.append(char)
            last_dash = False
        elif not last_dash:
            parts.append("-")
            last_dash = True
    return "".join(parts).strip("-") or "shard"
