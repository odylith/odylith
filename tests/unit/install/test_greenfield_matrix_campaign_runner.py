from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.greenfield_matrix_campaign_test_support import REPO_ROOT
from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
from tests.greenfield_matrix_campaign_test_support import command_arg as _arg
from tests.greenfield_matrix_campaign_test_support import load_module
from tests.greenfield_matrix_campaign_test_support import write_case_file as _write_case_file
from tests.greenfield_matrix_campaign_test_support import write_payload as _write_payload
from tests.greenfield_matrix_campaign_test_support import write_semantic_release_fixture

def _module():
    return load_module(
        SCRIPTS_ROOT / "greenfield_matrix_campaign_runner.py",
        "greenfield_matrix_campaign_runner_test",
    )


def _shards_module():
    return load_module(
        SCRIPTS_ROOT / "greenfield_matrix_shards.py",
        "greenfield_matrix_shards_runner_test",
    )


def _shard_runner_module():
    return load_module(
        SCRIPTS_ROOT / "greenfield_matrix_campaign_shard_runner.py",
        "greenfield_matrix_campaign_shard_runner_test",
    )


def test_campaign_stops_before_later_tiers_after_failed_subset_failure(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    calls: list[list[str]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        calls.append(command)
        _write_payload(Path(_arg(command, "--output-json")), status="failed", cluster="scores.copy")
        return subprocess.CompletedProcess(command, 1, "failed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        failed_case_files=(tmp_path / "failed-01.json", tmp_path / "failed-02.json"),
        regression_case_files=(tmp_path / "regression-01.json",),
        discovery_max_workers=1,
        stop_after_failures=1,
        stop_after_cluster_failures=1,
    )

    assert payload["status"] == "failed"
    assert payload["stopped_reason"].startswith("failed-subset:")
    assert payload["release_proof_completed"] is False
    assert payload["release_readiness_status"] == "not-proven"
    assert len(calls) == 1
    assert _arg(calls[0], "--campaign-phase") == "failed-subset"
    assert payload["tiers"][0]["completed_shard_count"] == 1
    assert payload["tiers"][0]["selected_shard_count"] == 2
    assert payload["tiers"][0]["stopped_early"] is True


def test_campaign_isolates_concurrent_shard_temp_cleanup_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    calls: list[list[str]] = []
    shard_temp_parents: list[Path] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        calls.append(command)
        shard_temp_parent = Path(_arg(command, "--temp-parent"))
        shard_temp_parents.append(shard_temp_parent)
        (shard_temp_parent / "odylith-greenfield-matrix-active-sibling").mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(tmp_path / "regression-01.json", tmp_path / "regression-02.json"),
        discovery_max_workers=2,
    )

    assert payload["status"] == "discovery-passed"
    assert payload["execution_status"] == "passed"
    assert len(calls) == 2
    assert len(set(shard_temp_parents)) == 2
    assert all(path.parent == tmp_path / "tmp" / "60-case-regression" for path in shard_temp_parents)
    assert all(not path.exists() for path in shard_temp_parents)


def test_campaign_fails_when_shard_temp_scope_cleanup_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    shards = _shards_module()
    real_cleanup = module._cleanup_shard_temp_parent  # noqa: SLF001
    cleanup_calls = 0
    case_file = tmp_path / "regression-01.json"
    _write_case_file(case_file, name="cleanup replay case", stressors=("latency-pressure",))

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    def flaky_cleanup(path):  # noqa: ANN001
        nonlocal cleanup_calls
        cleanup_calls += 1
        if cleanup_calls == 1:
            return real_cleanup(path)
        raise RuntimeError("forced shard cleanup failure")

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)
    monkeypatch.setattr(module, "_cleanup_shard_temp_parent", flaky_cleanup)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(case_file,),
        discovery_max_workers=1,
    )

    shard = payload["tiers"][0]["shards"][0]
    failed_payload = json.loads(Path(shard["output_json"]).read_text(encoding="utf-8"))
    replay = shards.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "replay",
        failed_result_jsons=(Path(shard["output_json"]),),
        shard_size=30,
        regression_size=1,
        volume_size=1,
        deep_volume_size=1,
        release_size=1,
    )

    assert payload["status"] == "failed"
    assert shard["status"] == "failed"
    assert shard["stop_reason"] == "shard-temp-cleanup-failed"
    assert shard["failure_clusters"][0]["cluster"] == "campaign.shard-temp-cleanup-failed"
    assert failed_payload["synthetic"] is True
    assert failed_payload["replayable"] is True
    assert failed_payload["campaign"]["failure_clusters"][0]["cluster"] == "campaign.shard-temp-cleanup-failed"
    assert failed_payload["results"][0]["evidence"]["case"]["id"] == "cleanup-replay-case"
    assert replay["tiers"]["failed-subset"]["case_count"] == 1
    assert "forced shard cleanup failure" in shard["stderr_excerpt"]


def test_campaign_launch_failure_writes_replayable_failed_subset_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    shards = _shards_module()
    case_file = tmp_path / "regression-01.json"
    _write_case_file(case_file, name="launch replay case", stressors=("registry-contract-pressure",))

    def fake_run(**_kwargs):  # noqa: ANN001
        raise OSError("forced shard launch failure")

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(case_file,),
        discovery_max_workers=1,
    )

    shard = payload["tiers"][0]["shards"][0]
    failed_payload = json.loads(Path(shard["output_json"]).read_text(encoding="utf-8"))
    replay = shards.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "replay",
        failed_result_jsons=(Path(shard["output_json"]),),
        shard_size=30,
        regression_size=1,
        volume_size=1,
        deep_volume_size=1,
        release_size=1,
    )

    assert payload["status"] == "failed"
    assert shard["failure_clusters"][0]["cluster"] == "campaign.shard-launch-failed"
    assert failed_payload["synthetic"] is True
    assert failed_payload["replayable"] is True
    assert failed_payload["campaign"]["failure_clusters"][0]["cluster"] == "campaign.shard-launch-failed"
    assert failed_payload["results"][0]["evidence"]["case"]["id"] == "launch-replay-case"
    assert replay["tiers"]["failed-subset"]["case_count"] == 1


def test_campaign_clusters_pre_result_shard_process_failures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        return subprocess.CompletedProcess(
            command,
            1,
            "",
            "traceback prelude " * 200
            + "RuntimeError: greenfield matrix required_terms must be grounded",
        ), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(tmp_path / "volume-01.json",),
        discovery_max_workers=1,
        stop_after_failures=1,
        stop_after_cluster_failures=1,
    )

    tier = payload["tiers"][0]
    shard = tier["shards"][0]
    snapshot = json.loads(Path(payload["progress_json"]).read_text(encoding="utf-8"))

    assert payload["status"] == "failed"
    assert tier["cluster_counts"] == {"campaign.shard-process-failed": 1}
    assert payload["failure_clusters"][0]["cluster"] == "campaign.shard-process-failed"
    assert "required_terms must be grounded" in payload["failure_clusters"][0]["example_issue"]
    assert shard["failed_case_count"] == 1
    assert shard["failure_clusters"][0]["cluster"] == "campaign.shard-process-failed"
    assert "required_terms must be grounded" in shard["failure_clusters"][0]["example_issue"]
    assert shard["failure_clusters"][0]["example_issue"].startswith("...")
    assert snapshot["cluster_counts"] == {"campaign.shard-process-failed": 1}


def test_campaign_preflights_existing_invalid_case_files_before_launching_shards(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    invalid_case_file = tmp_path / "volume-01.json"
    invalid_case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "restaurant health reinspection",
                        "prompt": (
                            "Create a greenfield proposal for restaurant health reinspection where "
                            "an inspector records a follow-up decision."
                        ),
                        "required_terms": ("inspection",),
                        "leakage_terms": ("restaurant health reinspection",),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_run(**kwargs):  # noqa: ANN001
        raise AssertionError("invalid case files must stop before shard process launch")

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(invalid_case_file, tmp_path / "volume-02.json"),
        discovery_max_workers=2,
        stop_after_failures=1,
    )

    tier = payload["tiers"][0]
    shard = tier["shards"][0]
    assert payload["status"] == "failed"
    assert tier["completed_shard_count"] == 0
    assert tier["cluster_counts"] == {"campaign.case-file-invalid": 1}
    assert shard["status"] == "failed"
    assert shard["payload_status"] == "case-file-invalid"
    assert shard["case_file"] == str(invalid_case_file)
    assert "ungrounded required_terms: inspection" in shard["stderr_excerpt"]
    assert payload["failure_response"]["shard_replay_case_files"] == [str(invalid_case_file)]


def test_stopped_sibling_shard_without_failed_cases_does_not_inflate_failure_count() -> None:
    module = _module()
    result = module.ShardRunResult(
        tier="volume-discovery",
        name="volume-discovery-sibling",
        case_file="/tmp/cases.json",
        status="stopped",
        returncode=130,
        seconds=0.5,
        output_json="/tmp/out.json",
        telemetry_jsonl="/tmp/out.jsonl",
        temp_parent="/tmp/temp",
        payload_status="running",
        completed_case_count=0,
        failed_case_count=0,
        failure_clusters=(),
        stdout_excerpt="",
        stderr_excerpt="",
        stop_reason="cluster-threshold:manifest.generated-copy-quality.atlas:1:live-telemetry",
    )

    assert module._shard_runner._failed_case_count_increment(result) == 0  # noqa: SLF001


def test_pre_result_shard_failure_writes_replayable_failed_subset_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    shards = _shards_module()
    case_file = tmp_path / "volume-01.json"
    _write_case_file(case_file, name="replayable crash case", stressors=("registry-contract-pressure",))

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        return subprocess.CompletedProcess(
            command,
            1,
            "",
            "RuntimeError: process died before result payload",
        ), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(case_file,),
        discovery_max_workers=1,
        stop_after_failures=1,
    )

    failed_json = Path(payload["failure_response"]["failed_result_jsons"][0])
    failed_payload = json.loads(failed_json.read_text(encoding="utf-8"))
    failed_case = failed_payload["results"][0]["evidence"]["case"]
    replay = shards.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "replay",
        failed_result_jsons=(failed_json,),
        shard_size=30,
        regression_size=1,
        volume_size=1,
        deep_volume_size=1,
        release_size=1,
    )

    assert failed_payload["synthetic"] is True
    assert failed_payload["replayable"] is True
    assert failed_payload["exact_failed_subset_available"] is True
    assert failed_payload["replay_scope"] == "exact-failed-cases"
    assert failed_case["prompt_sha256"]
    assert replay["tiers"]["failed-subset"]["case_count"] == 1


def test_multi_case_pre_result_failure_does_not_replay_unstarted_planned_cases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    case_file = tmp_path / "volume-01.json"
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "crash-001",
                        "name": "crash replay one",
                        "prompt": "Create a greenfield proposal for crash replay one.",
                        "required_terms": ("crash", "replay"),
                        "leakage_terms": ("crash replay one",),
                        "stressors": ("registry-contract-pressure",),
                    },
                    {
                        "case_id": "crash-002",
                        "name": "crash replay two",
                        "prompt": "Create a greenfield proposal for crash replay two.",
                        "required_terms": ("crash", "replay"),
                        "leakage_terms": ("crash replay two",),
                        "stressors": ("atlas-label-pressure",),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_run(**kwargs):  # noqa: ANN001
        return subprocess.CompletedProcess(
            kwargs["command"],
            1,
            "",
            "RuntimeError: process died before result payload",
        ), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(case_file,),
        discovery_max_workers=1,
        stop_after_failures=1,
    )

    failed_response = payload["failure_response"]
    shard = payload["tiers"][0]["shards"][0]
    shard_payload = json.loads(Path(shard["output_json"]).read_text(encoding="utf-8"))
    attempt_ledger = Path(shard["attempt_ledger_jsonl"])

    assert shard_payload["synthetic"] is True
    assert shard_payload["replay_scope"] == "source-shard"
    assert shard_payload["exact_failed_subset_available"] is False
    assert shard_payload["results"] == []
    assert shard_payload["attempt_ledger_jsonl"] == str(attempt_ledger)
    assert attempt_ledger.is_file()
    assert "Create a greenfield proposal" not in attempt_ledger.read_text(encoding="utf-8")
    assert failed_response["exact_failed_subset_available"] is False
    assert failed_response["failed_result_jsons"] == []
    assert failed_response["shard_replay_case_files"] == [str(case_file)]
    assert "shard_replay_case_files" in failed_response["operator_loop"][2]


def test_live_stop_origin_shard_writes_replayable_failed_subset_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    shards = _shards_module()
    case_file = tmp_path / "volume-01.json"
    prompt = "Create a greenfield proposal for live stop replay with governed records."
    case_file.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "live-stop-001",
                        "name": "live stop replay",
                        "prompt": prompt,
                        "required_terms": ("live", "replay"),
                        "leakage_terms": ("live stop replay",),
                        "stressors": ("atlas-label-pressure",),
                    },
                    {
                        "case_id": "sibling-002",
                        "name": "sibling should not replay",
                        "prompt": "Create a greenfield proposal for sibling should not replay.",
                        "required_terms": ("sibling", "replay"),
                        "leakage_terms": ("sibling should not replay",),
                        "stressors": ("registry-contract-pressure",),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_run(**kwargs):  # noqa: ANN001
        shard = kwargs["shard"]
        progress = kwargs["progress"]
        progress.forward_shard_telemetry(
            shard=shard,
            row={
                "event": "case_completed",
                "result": {
                    "name": "live stop replay",
                    "case": {
                        "id": "live-stop-001",
                        "name": "live stop replay",
                        "slug": "live-stop-replay",
                        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "stressors": ["atlas-label-pressure"],
                    },
                    "status": "failed",
                    "quality_passed": False,
                },
                "failure_cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
            },
        )
        return subprocess.CompletedProcess(kwargs["command"], 130, "", ""), (
            "cluster-threshold:manifest.generated-copy-quality.atlas-renderer.atlas:1:live-telemetry"
        )

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(case_file,),
        discovery_max_workers=1,
        stop_after_cluster_failures=1,
    )

    failed_json = Path(payload["failure_response"]["failed_result_jsons"][0])
    failed_payload = json.loads(failed_json.read_text(encoding="utf-8"))
    replay = shards.build_shards(
        case_files=(case_file,),
        output_dir=tmp_path / "replay",
        failed_result_jsons=(failed_json,),
        shard_size=30,
        regression_size=2,
        volume_size=2,
        deep_volume_size=2,
        release_size=2,
    )

    assert failed_payload["synthetic"] is True
    assert failed_payload["replayable"] is True
    assert failed_payload["campaign"]["failed_case_count"] == 1
    assert failed_payload["campaign"]["failure_clusters"][0]["case_ids"] == ["live-stop-001"]
    assert replay["tiers"]["failed-subset"]["case_count"] == 1
    replay_case = shards.load_case_file(Path(replay["tiers"]["failed-subset"]["files"][0]))[0]
    assert replay_case.case_id == "live-stop-001"


def test_campaign_uses_tier_default_worker_profile_when_no_override(tmp_path: Path, monkeypatch) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        failed_case_files=(tmp_path / "failed-01.json",),
        regression_case_files=(tmp_path / "regression-01.json",),
        volume_case_files=(tmp_path / "volume-01.json",),
        deep_volume_case_files=(tmp_path / "deep-volume-01.json",),
    )

    assert payload["default_discovery_workers_by_tier"] == {
        "failed-subset": 1,
        "60-case-regression": 2,
        "volume-discovery": 2,
        "240-case-discovery": 2,
    }
    assert [tier["max_workers"] for tier in payload["tiers"][:4]] == [1, 2, 2, 2]


def test_campaign_validates_stressors_across_the_whole_tier(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    first = tmp_path / "regression-01.json"
    second = tmp_path / "regression-02.json"
    _write_case_file(first, name="case one", stressors=("modal-expert-lens",))
    _write_case_file(second, name="case two", stressors=("registry-contract-pressure",))
    calls: list[list[str]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        calls.append(command)
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(first, second),
        discovery_max_workers=1,
        require_high_variance_stressors=False,
        required_stressors=("modal-expert-lens", "registry-contract-pressure"),
    )

    assert payload["status"] == "discovery-passed"
    assert payload["execution_status"] == "passed"
    assert len(calls) == 2
    assert all("--require-high-variance-stressors" not in command for command in calls)
    assert all("--required-stressor" in command for command in calls)
    assert all("--allow-partial-stressor-coverage" in command for command in calls)


def test_campaign_fails_before_running_shards_when_tier_stressor_coverage_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    case_file = tmp_path / "regression-01.json"
    _write_case_file(case_file, name="case one", stressors=("modal-expert-lens",))

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        raise AssertionError(f"shard should not run when tier coverage is missing: {command}")

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(case_file,),
        discovery_max_workers=1,
        require_high_variance_stressors=False,
        required_stressors=("modal-expert-lens", "registry-contract-pressure"),
    )

    tier = payload["tiers"][0]
    assert payload["status"] == "failed"
    assert tier["completed_shard_count"] == 0
    assert tier["stop_reason"] == "tier-stressor-coverage-missing:registry-contract-pressure"


def test_campaign_high_variance_flag_expands_required_stressor_taxonomy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    case_file = tmp_path / "regression-01.json"
    _write_case_file(case_file, name="case one", stressors=("modal-expert-lens",))

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        raise AssertionError(f"shard should not run when high-variance coverage is missing: {command}")

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(case_file,),
        discovery_max_workers=1,
        require_high_variance_stressors=True,
    )

    assert payload["status"] == "failed"
    assert payload["tiers"][0]["completed_shard_count"] == 0
    assert "path-grant" in payload["tiers"][0]["stop_reason"]


def test_campaign_enforces_explicit_required_stressors_without_high_variance_flag(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    case_file = tmp_path / "regression-01.json"
    _write_case_file(case_file, name="case one", stressors=("modal-expert-lens",))

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        raise AssertionError(f"shard should not run when explicit stressor coverage is missing: {command}")

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(case_file,),
        discovery_max_workers=1,
        require_high_variance_stressors=False,
        required_stressors=("modal-expert-lens", "registry-contract-pressure"),
    )

    assert payload["status"] == "failed"
    assert payload["tiers"][0]["stop_reason"] == "tier-stressor-coverage-missing:registry-contract-pressure"


def test_campaign_fails_release_proof_when_required_stressors_are_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    release_case_file = tmp_path / "release.json"
    _write_case_file(release_case_file, name="release easy case", stressors=("modal-expert-lens",))
    calls: list[list[str]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        calls.append(list(kwargs["command"]))
        return subprocess.CompletedProcess(kwargs["command"], 0, "", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        release_case_files=(release_case_file,),
        discovery_max_workers=1,
        require_high_variance_stressors=False,
        required_stressors=("modal-expert-lens", "registry-contract-pressure"),
    )

    assert calls == []
    assert payload["status"] == "failed"
    assert payload["tiers"][0]["tier"] == "release-proof"
    assert payload["tiers"][0]["stop_reason"].startswith("tier-release-corpus-invalid:")
    assert payload["release_proof_completed"] is False
    assert payload["release_proof_status"] == "failed-preflight"
    assert payload["release_readiness_status"] == "failed"


def test_discovery_only_campaign_passes_without_claiming_release_readiness(tmp_path: Path, monkeypatch) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(tmp_path / "volume-01.json",),
    )

    assert payload["status"] == "discovery-passed"
    assert payload["execution_status"] == "passed"
    assert payload["release_proof_completed"] is False
    assert payload["release_proof_status"] == "not-run"
    assert payload["release_readiness_status"] == "not-proven"


def test_discovery_tier_accepts_discovery_passed_matrix_payload(tmp_path: Path, monkeypatch) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        output_json = Path(_arg(command, "--output-json"))
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps(
                {
                    "status": "discovery-passed",
                    "campaign": {
                        "completed_case_count": 1,
                        "failed_case_count": 0,
                        "failure_clusters": [],
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(tmp_path / "volume-01.json",),
        discovery_max_workers=1,
        stop_after_failures=1,
        stop_after_cluster_failures=1,
    )

    tier = payload["tiers"][0]
    shard = tier["shards"][0]
    assert payload["status"] == "discovery-passed"
    assert payload["execution_status"] == "passed"
    assert tier["status"] == "passed"
    assert tier["stop_reason"] == ""
    assert shard["status"] == "passed"
    assert shard["payload_status"] == "discovery-passed"
    assert shard["stop_reason"] == ""


def test_discovery_passed_payload_requires_zero_failed_cases_and_clusters() -> None:
    module = _shard_runner_module()

    assert module._successful_matrix_payload(  # noqa: SLF001
        payload_status="discovery-passed",
        campaign={"failed_case_count": 0, "failure_clusters": []},
        proof_tier="discovery",
    )
    assert not module._successful_matrix_payload(  # noqa: SLF001
        payload_status="discovery-passed",
        campaign={"failed_case_count": 1, "failure_clusters": []},
        proof_tier="discovery",
    )
    assert not module._successful_matrix_payload(  # noqa: SLF001
        payload_status="discovery-passed",
        campaign={"failed_case_count": 0, "failure_clusters": [{"cluster": "scores.copy"}]},
        proof_tier="discovery",
    )
    assert not module._successful_matrix_payload(  # noqa: SLF001
        payload_status="discovery-passed",
        campaign={"failed_case_count": 0, "failure_clusters": []},
        proof_tier="release",
    )


def test_campaign_can_require_release_readiness_for_release_claims(tmp_path: Path, monkeypatch) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(tmp_path / "volume-01.json",),
        require_release_readiness=True,
    )

    assert payload["status"] == "failed"
    assert payload["stopped_reason"] == "release-readiness-required:not-proven"
    assert payload["release_readiness_required"] is True
    assert payload["release_readiness_status"] == "not-proven"


def test_release_proof_input_manifest_rejects_post_preflight_mutation(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "release.json"
    audit_file = tmp_path / "audit.json"
    case_file.write_text('{"cases": []}\n', encoding="utf-8")
    audit_file.write_text('{"audits": []}\n', encoding="utf-8")

    references = module._release_proof_input_manifest(  # noqa: SLF001
        case_files=(case_file,),
        release_audit_file=audit_file,
    )

    assert module._release_proof_input_drift_issues(references) == ()  # noqa: SLF001
    audit_file.write_text('{"audits": ["changed"]}\n', encoding="utf-8")

    assert module._release_proof_input_drift_issues(references) == (  # noqa: SLF001
        "release-audit-file changed after release-proof preflight",
    )


def test_campaign_refuses_release_execution_when_inputs_cannot_be_sealed(tmp_path: Path) -> None:
    module = _module()
    case_file = tmp_path / "release.json"
    audit_file = tmp_path / "audit.json"
    case_file.write_text('{"cases": []}\n', encoding="utf-8")
    audit_file.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="release proof inputs could not be sealed"):
        module.run_campaign(
            dist_dir=tmp_path / "dist",
            version="0.1.15",
            temp_parent=tmp_path / "tmp",
            output_dir=tmp_path / "out",
            telemetry_dir=tmp_path / "telemetry",
            release_case_files=(case_file,),
            release_audit_file=audit_file,
        )


def test_semantic_release_inputs_are_sealed_and_forwarded_as_one_holdout(tmp_path: Path) -> None:
    module = _module()
    repo_root = tmp_path / "repo"
    holdout_path, manifest_path = write_semantic_release_fixture(
        repo_root=repo_root,
        temp_root=tmp_path,
    )

    snapshot = module._seal_release_proof_inputs(  # noqa: SLF001
        case_files=(holdout_path,),
        release_audit_file=None,
        semantic_annotations_file=holdout_path,
        evaluation_split_manifest=manifest_path,
        repo_root=repo_root,
        temp_parent=tmp_path / "snapshots",
    )

    assert snapshot is not None
    assert snapshot.case_files == (snapshot.semantic_annotations_file,)
    shard = module._release_tier(  # noqa: SLF001
        "release-proof",
        snapshot.case_files,
        require_high_variance_stressors=False,
        required_stressors=(),
        release_input_snapshot_root=snapshot.root,
        semantic_annotations_file=snapshot.semantic_annotations_file,
        evaluation_split_manifest=snapshot.evaluation_split_manifest,
        final_holdout_run_ledger=tmp_path / "final-holdout-run-ledger.json",
        implementation_revision="a" * 40,
    )[0]
    command = module._matrix_command(  # noqa: SLF001
        shard=shard,
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "matrix",
        output_json=tmp_path / "result.json",
        telemetry_jsonl=tmp_path / "telemetry.jsonl",
    )
    assert _arg(command, "--semantic-annotations-file") == str(snapshot.semantic_annotations_file)
    assert _arg(command, "--evaluation-split-manifest") == str(snapshot.evaluation_split_manifest)
    assert _arg(command, "--final-holdout-run-ledger") == str(tmp_path / "final-holdout-run-ledger.json")
    assert _arg(command, "--implementation-revision") == "a" * 40
    shutil.rmtree(snapshot.root)


def test_campaign_requires_one_shot_guard_for_semantic_release(tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(RuntimeError, match="one-shot final holdout run ledger"):
        module.run_campaign(
            dist_dir=tmp_path / "dist",
            version="0.1.15",
            temp_parent=tmp_path / "tmp",
            output_dir=tmp_path / "out",
            telemetry_dir=tmp_path / "telemetry",
            semantic_annotations_file=tmp_path / "holdout.json",
        )


def test_release_proof_input_manifest_binds_transitive_audit_trail(tmp_path: Path) -> None:
    module = _module()
    fixture_root = REPO_ROOT / "tests/fixtures/greenfield-release-corpus"
    copied_root = tmp_path / "repo/tests/fixtures/greenfield-release-corpus"
    copied_root.mkdir(parents=True)
    for name in (
        "greenfield-release-source-provenanced.v3.json",
        "greenfield-release-audit-requests.v7.json",
        "greenfield-release-review-results.v9-2026-07-20.json",
        "audit-source-verifications-v8-2026-07-20",
        "audit-evidence-v15",
        "sources",
    ):
        source = fixture_root / name
        destination = copied_root / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    case_file = copied_root / "greenfield-release-source-provenanced.v3.json"
    audit_file = copied_root / "audit-evidence-v15/greenfield-release-audit.v9.json"

    references = module._release_proof_input_manifest(  # noqa: SLF001
        case_files=(case_file,),
        release_audit_file=audit_file,
        repo_root=tmp_path / "repo",
    )

    assert {reference["kind"] for reference in references} >= {
        "release-case-file",
        "release-audit-file",
        "release-audit-request-plan",
        "release-audit-source-verifications",
        "release-audit-review-results",
    }
    assert any(reference["kind"].startswith("release-source-artifact:") for reference in references)
    snapshot = module._seal_release_proof_inputs(  # noqa: SLF001
        case_files=(case_file,),
        release_audit_file=audit_file,
        repo_root=tmp_path / "repo",
        temp_parent=tmp_path / "snapshots",
    )
    assert snapshot is not None
    snapshot_manifest = json.loads(snapshot.manifest_path.read_text(encoding="utf-8"))
    assert snapshot_manifest["snapshot_root"] == str(snapshot.root)
    assert snapshot_manifest["case_files"] == [
        "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
    ]
    assert snapshot_manifest["audit_file"] == (
        "tests/fixtures/greenfield-release-corpus/audit-evidence-v15/greenfield-release-audit.v9.json"
    )
    assert snapshot_manifest["input_references"]
    source_case = json.loads(case_file.read_text(encoding="utf-8"))["cases"][0]
    source_artifact = (tmp_path / "repo") / source_case["provenance"]["source_artifact_path"]
    snapshot_artifact = snapshot.root / source_case["provenance"]["source_artifact_path"]
    snapshot_review = snapshot.root / "tests/fixtures/greenfield-release-corpus/greenfield-release-review-results.v9-2026-07-20.json"
    review_snapshot_bytes = snapshot_review.read_bytes()
    artifact_snapshot_bytes = snapshot_artifact.read_bytes()
    review_result = copied_root / "greenfield-release-review-results.v9-2026-07-20.json"
    review_result.write_text(review_result.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    source_artifact.write_text(source_artifact.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    assert set(module._release_proof_input_drift_issues(references)) == {  # noqa: SLF001
        "release-audit-review-results changed after release-proof preflight",
        "release-source-artifact:release-accessibility-001-description changed after release-proof preflight",
    }
    assert module._release_proof_input_drift_issues(snapshot.input_references) == ()  # noqa: SLF001
    assert snapshot_review.read_bytes() == review_snapshot_bytes
    assert snapshot_artifact.read_bytes() == artifact_snapshot_bytes
    shutil.rmtree(snapshot.root)


def test_campaign_builds_failed_subset_replays_from_sealed_release_cases(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    case_file = REPO_ROOT / "tests/fixtures/greenfield-release-corpus/greenfield-release-source-provenanced.v3.json"
    audit_file = (
        REPO_ROOT / "tests/fixtures/greenfield-release-corpus/audit-evidence-v15/greenfield-release-audit.v9.json"
    )
    captured: dict[str, object] = {}

    def fake_run_tier(**kwargs):  # noqa: ANN001
        shard = kwargs["shards"][0]
        return {
            "tier": shard.tier,
            "status": "failed",
            "completed_shard_count": 1,
            "selected_shard_count": 1,
            "stop_reason": "forced-release-failure",
            "cluster_counts": {},
            "shards": [],
        }

    def fake_replay(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {"status": "not-required"}

    monkeypatch.setattr(module, "_run_tier", fake_run_tier)
    monkeypatch.setattr(module, "_failed_subset_replay_artifacts", fake_replay)

    module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        release_case_files=(case_file,),
        release_audit_file=audit_file,
    )

    replay_sources = tuple(captured["source_case_files"])
    assert replay_sources
    assert replay_sources[0] != case_file
    assert replay_sources[0].is_relative_to(tmp_path / "tmp")
    assert not list((tmp_path / "tmp").glob("odylith-release-inputs-*"))


def test_campaign_writes_merged_case_progress_files(tmp_path: Path, monkeypatch) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        shard = kwargs["shard"]
        progress = kwargs["progress"]
        _write_payload(Path(_arg(command, "--output-json")), status="passed")
        progress.forward_shard_telemetry(
            shard=shard,
            row={
                "event": "case_completed",
                "result": {
                    "name": "case one",
                    "status": "passed",
                    "quality_passed": True,
                    "score": 10,
                    "create_seconds": 18.0,
                    "create_returncode": 0,
                    "issue_count": 0,
                    "first_issue": "",
                },
                "failure_cluster": "",
            },
        )
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(tmp_path / "regression-01.json",),
        discovery_max_workers=1,
    )

    progress_jsonl = Path(payload["progress_jsonl"])
    progress_json = Path(payload["progress_json"])
    rows = [json.loads(line) for line in progress_jsonl.read_text(encoding="utf-8").splitlines()]
    snapshot = json.loads(progress_json.read_text(encoding="utf-8"))
    assert any(row["event"] == "case_completed" for row in rows)
    assert snapshot["completed_case_count"] == 1
    assert snapshot["passed_case_count"] == 1
    assert snapshot["status"] == "discovery-passed"


def test_campaign_progress_counts_shard_completed_failure_when_case_telemetry_stopped(
    tmp_path: Path,
) -> None:
    module = _module()
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )
    shard = module.CampaignShard(
        tier="volume-discovery",
        case_file=tmp_path / "case.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=1,
        stop_after_cluster_failures=1,
        require_high_variance_stressors=False,
        required_stressors=(),
    )

    progress.emit("tier_started", {"tier": shard.tier, "selected_shard_count": 1, "max_workers": 1})
    progress.emit(
        "shard_completed",
        {
            "tier": shard.tier,
            "shard": shard.name,
            "status": "failed",
            "returncode": 1,
            "completed_case_count": 1,
            "failed_case_count": 1,
            "failure_clusters": [
                {"cluster": "forced.matrix.case.explosion", "count": 1, "cases": ["case one"]}
            ],
        },
    )

    snapshot = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    tier = snapshot["tiers"]["volume-discovery"]
    assert snapshot["completed_case_count"] == 1
    assert snapshot["failed_case_count"] == 1
    assert snapshot["cluster_counts"] == {"forced.matrix.case.explosion": 1}
    assert tier["failed_case_count"] == 1
    assert tier["cluster_counts"] == {"forced.matrix.case.explosion": 1}


def test_progress_snapshot_tracks_running_cases_until_completion(tmp_path: Path) -> None:
    module = _module()
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )
    shard = module.CampaignShard(
        tier="60-case-regression",
        case_file=tmp_path / "case.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=1,
        stop_after_cluster_failures=1,
        require_high_variance_stressors=False,
        required_stressors=(),
    )

    progress.forward_shard_telemetry(
        shard=shard,
        row={
            "event": "case_started",
            "index": 1,
            "total": 2,
            "case": {
                "id": "case-001",
                "name": "case one",
                "slug": "case-one",
                "stressors": ["atlas-label-pressure"],
            },
        },
    )
    started = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    progress.forward_shard_telemetry(
        shard=shard,
        row={
            "event": "case_completed",
            "result": {
                "name": "case one",
                "case": {"id": "case-001", "name": "case one", "slug": "case-one"},
                "status": "passed",
                "quality_passed": True,
            },
            "failure_cluster": "",
        },
    )
    completed = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))

    assert started["started_case_count"] == 1
    assert started["running_cases"][0]["case_id"] == "case-001"
    assert started["running_cases"][0]["stressors"] == ["atlas-label-pressure"]
    assert completed["completed_case_count"] == 1
    assert completed["running_cases"] == []


def test_shard_telemetry_tail_does_not_duplicate_partial_json_line(tmp_path: Path) -> None:
    module = _module()
    telemetry = tmp_path / "progress.jsonl"
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )
    shard = module.CampaignShard(
        tier="60-case-regression",
        case_file=tmp_path / "case.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=1,
        stop_after_cluster_failures=1,
        require_high_variance_stressors=False,
        required_stressors=(),
    )
    complete = json.dumps(
        {
            "event": "case_completed",
            "result": {"name": "case one", "status": "passed", "quality_passed": True},
            "failure_cluster": "",
        }
    )
    partial = json.dumps({"event": "case_started", "case": {"name": "case two"}})
    telemetry.write_text(complete + "\n" + partial, encoding="utf-8")

    offset = module._forward_shard_telemetry(  # noqa: SLF001
        telemetry_jsonl=telemetry,
        offset=0,
        shard=shard,
        progress=progress,
    )
    telemetry.write_text(complete + "\n" + partial + "\n", encoding="utf-8")
    module._forward_shard_telemetry(  # noqa: SLF001
        telemetry_jsonl=telemetry,
        offset=offset,
        shard=shard,
        progress=progress,
    )

    rows = [json.loads(line) for line in (tmp_path / "merged.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == ["case_completed", "case_started"]


def test_progress_writer_recommends_live_tier_stop_from_merged_telemetry(tmp_path: Path) -> None:
    module = _module()
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )
    shard = module.CampaignShard(
        tier="60-case-regression",
        case_file=tmp_path / "case.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=0,
        stop_after_cluster_failures=2,
        require_high_variance_stressors=False,
        required_stressors=(),
    )
    progress.emit("tier_started", {"tier": shard.tier, "selected_shard_count": 2, "max_workers": 2})
    for name in ("case one", "case two"):
        progress.forward_shard_telemetry(
            shard=shard,
            row={
                "event": "case_completed",
                "result": {"name": name, "status": "failed", "quality_passed": False},
                "failure_cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
            },
        )

    decision = progress.tier_stop_decision(
        tier=shard.tier,
        current_shard=shard.name,
        stop_after_failures=0,
        stop_after_cluster_failures=2,
    )
    assert decision["reason"] == (
        "cluster-threshold:manifest.generated-copy-quality.atlas-renderer.atlas:2:live-telemetry"
    )
    assert progress.mark_tier_stop_emitted(shard.tier) is True
    assert progress.mark_tier_stop_emitted(shard.tier) is False


def test_progress_writer_uses_failure_emitting_shard_as_live_stop_origin(tmp_path: Path) -> None:
    module = _module()
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )
    shard_a = module.CampaignShard(
        tier="60-case-regression",
        case_file=tmp_path / "case-a.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=0,
        stop_after_cluster_failures=1,
        require_high_variance_stressors=False,
        required_stressors=(),
    )
    shard_b = module.CampaignShard(
        tier="60-case-regression",
        case_file=tmp_path / "case-b.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=0,
        stop_after_cluster_failures=1,
        require_high_variance_stressors=False,
        required_stressors=(),
    )
    progress.emit("tier_started", {"tier": shard_a.tier, "selected_shard_count": 2, "max_workers": 2})
    progress.forward_shard_telemetry(
        shard=shard_a,
        row={
            "event": "case_completed",
            "result": {"name": "case one", "status": "failed", "quality_passed": False},
            "failure_cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
        },
    )

    decision = progress.tier_stop_decision(
        tier=shard_a.tier,
        current_shard=shard_b.name,
        stop_after_failures=0,
        stop_after_cluster_failures=1,
    )

    assert decision["origin_shard"] == shard_a.name
    assert decision["reason"] == "cluster-threshold:manifest.generated-copy-quality.atlas-renderer.atlas:1:live-telemetry"


def test_tier_result_preserves_live_cluster_counts_from_interrupted_shards(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        shard = kwargs["shard"]
        progress = kwargs["progress"]
        progress.forward_shard_telemetry(
            shard=shard,
            row={
                "event": "case_completed",
                "result": {"name": "case one", "status": "failed", "quality_passed": False},
                "failure_cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
            },
        )
        _write_payload(Path(_arg(command, "--output-json")), status="failed")
        return subprocess.CompletedProcess(command, 1, "failed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(tmp_path / "regression-01.json", tmp_path / "regression-02.json"),
        discovery_max_workers=2,
        stop_after_failures=1,
    )

    tier = payload["tiers"][0]
    assert tier["cluster_counts"] == {"manifest.generated-copy-quality.atlas-renderer.atlas": 2}
    assert payload["failure_clusters"][0]["cluster"] == "manifest.generated-copy-quality.atlas-renderer.atlas"
    assert payload["failure_clusters"][0]["count"] == 2


def test_failed_campaign_payload_includes_failure_response_for_casebook_and_replay(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    case_file = tmp_path / "volume-01.json"
    _write_case_file(
        case_file,
        name="case one",
        stressors=("registry-contract-pressure",),
        case_id="case-001",
    )

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        path = Path(_arg(command, "--output-json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "campaign": {
                        "completed_case_count": 1,
                        "failed_case_count": 1,
                        "failure_clusters": [
                            {
                                "cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
                                "count": 1,
                                "cases": ["case one"],
                                "case_ids": ["case-001"],
                                "case_fingerprints": ["a" * 64],
                                "example_issue": "Atlas repeated visible copy",
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 1, "failed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(case_file,),
        discovery_max_workers=1,
        stop_after_failures=1,
    )

    response = payload["failure_response"]
    assert response["status"] == "required"
    assert response["casebook_capture_required"] is True
    assert response["release_claim_allowed"] is False
    assert response["primary_cluster"] == "manifest.generated-copy-quality.atlas-renderer.atlas"
    assert response["failed_case_ids"] == ["case-001"]
    assert response["failed_case_fingerprints"] == ["a" * 64]
    assert response["failed_result_jsons"] == [payload["tiers"][0]["shards"][0]["output_json"]]
    assert "rerun the exact failed subset first" in " ".join(response["operator_loop"])


def test_failed_campaign_materializes_exact_failed_subset_replay_shard(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _module()
    shards = _shards_module()
    case_file = tmp_path / "volume-01.json"
    case_file.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.matrix.case-file.v1",
                "cases": [
                    {
                        "case_id": "case-001",
                        "name": "case one",
                        "prompt": (
                            "Create a greenfield proposal for case one with modal registry proof "
                            "and case one leakage phrase."
                        ),
                        "required_terms": ("modal", "registry"),
                        "leakage_terms": ("case one leakage phrase",),
                        "stressors": ("atlas-label-pressure", "registry-contract-pressure"),
                    },
                    {
                        "case_id": "case-002",
                        "name": "case two",
                        "prompt": (
                            "Create a greenfield proposal for case two with modal registry proof "
                            "and case two leakage phrase."
                        ),
                        "required_terms": ("modal", "registry"),
                        "leakage_terms": ("case two leakage phrase",),
                        "stressors": ("latency-pressure",),
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        path = Path(_arg(command, "--output-json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "campaign": {
                        "completed_case_count": 1,
                        "failed_case_count": 1,
                        "failure_clusters": [
                            {
                                "cluster": "manifest.generated-copy-quality.atlas-renderer.atlas",
                                "count": 1,
                                "cases": ["case one"],
                                "case_ids": ["case-001"],
                                "case_fingerprints": [],
                                "example_issue": "Atlas repeated visible copy",
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 1, "failed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        failed_subset_replay_dir=tmp_path / "failed-replay",
        volume_case_files=(case_file,),
        discovery_max_workers=1,
        stop_after_failures=1,
    )

    replay = payload["failure_response"]["failed_subset_replay"]
    replay_cases = shards.load_case_file(Path(replay["files"][0]))
    replay_summary = json.loads(Path(replay["summary_json"]).read_text(encoding="utf-8"))

    assert replay["status"] == "written"
    assert replay["case_count"] == 1
    assert replay["next_tier"] == "failed-subset"
    assert replay["summary_json"].endswith("greenfield-matrix-shards.v1.json")
    assert replay_summary["failed_subset_only"] is True
    assert list(replay_summary["tiers"]) == ["failed-subset"]
    assert replay_cases[0].case_id == "case-001"
    assert replay_cases[0].name == "case one"


def test_progress_snapshot_preserves_tier_completed_preflight_counts(tmp_path: Path) -> None:
    module = _module()
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )

    progress.emit(
        "tier_completed",
        {
            "tier": "volume-discovery",
            "status": "failed",
            "stop_reason": "tier-stressor-coverage-missing:modal-expert-lens",
            "selected_shard_count": 3,
            "completed_shard_count": 0,
            "cluster_counts": {"campaign.preflight.coverage": 1},
        },
    )

    snapshot = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    tier = snapshot["tiers"]["volume-discovery"]
    assert tier["status"] == "failed"
    assert tier["selected_shard_count"] == 3
    assert tier["completed_shard_count"] == 0
    assert tier["cluster_counts"] == {"campaign.preflight.coverage": 1}
