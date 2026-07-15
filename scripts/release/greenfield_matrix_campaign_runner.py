"""Tiered campaign runner for high-volume greenfield matrix proof."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
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
from greenfield_matrix_failure_response import campaign_failure_clusters  # noqa: E402
from greenfield_matrix_failure_response import failure_response_plan  # noqa: E402
from greenfield_matrix_stressors import required_stressors_from_values  # noqa: E402


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
    normalized_required_stressors = required_stressors_from_values(
        required_stressors,
        use_default=bool(require_high_variance_stressors),
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
            release_case_files,
            require_high_variance_stressors=require_high_variance_stressors,
            required_stressors=normalized_required_stressors,
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
    execution_status = "passed" if tier_results and all(row["status"] == "passed" for row in tier_results) else "failed"
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
            release_case_files=release_case_files,
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
