from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from threading import Event


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(
        SCRIPTS_ROOT / "greenfield_matrix_campaign_runner.py",
        "greenfield_matrix_campaign_stale_telemetry_test",
    )


def _payload(status: str, *, name: str) -> dict[str, object]:
    return {
        "status": status,
        "campaign": {
            "completed_case_count": 1,
            "failed_case_count": 0 if status == "passed" else 1,
            "failure_clusters": [] if status == "passed" else [{"cluster": "stale", "count": 1}],
        },
        "results": [{"name": name, "status": status}],
    }


def test_shard_run_resets_stale_result_and_telemetry_files(tmp_path: Path) -> None:
    module = _module()
    shard = module.CampaignShard(
        tier="60-case-regression",
        case_file=tmp_path / "case-file.json",
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
    output_json = tmp_path / "out" / "60-case-regression-case-file.result.v1.json"
    telemetry_jsonl = tmp_path / "telemetry" / "60-case-regression-case-file.telemetry.v1.jsonl"
    output_json.parent.mkdir(parents=True)
    telemetry_jsonl.parent.mkdir(parents=True)
    output_json.write_text(json.dumps(_payload("failed", name="stale case")), encoding="utf-8")
    telemetry_jsonl.write_text(
        json.dumps(
            {
                "event": "case_completed",
                "result": {"name": "stale case", "status": "failed", "quality_passed": False},
                "failure_cluster": "stale.cluster",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    progress = module.CampaignProgressWriter(
        jsonl_path=tmp_path / "merged.jsonl",
        snapshot_path=tmp_path / "snapshot.json",
    )

    def fake_command_runner(**kwargs):  # noqa: ANN001
        assert not output_json.exists()
        assert not telemetry_jsonl.exists()
        output_json.write_text(json.dumps(_payload("passed", name="fresh case")), encoding="utf-8")
        command = kwargs["command"]
        return subprocess.CompletedProcess(command, 0, "fresh", ""), ""

    result = module._shard_runner._run_shard(  # noqa: SLF001
        shard=shard,
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        stop_event=Event(),
        progress=progress,
        command_runner=fake_command_runner,
        telemetry_forwarder=module._forward_shard_telemetry,  # noqa: SLF001
        temp_parent_cleaner=module._cleanup_shard_temp_parent,  # noqa: SLF001
    )

    assert result.passed
    assert result.completed_case_count == 1
    assert result.failed_case_count == 0
    assert result.failure_clusters == ()
    assert json.loads(output_json.read_text(encoding="utf-8"))["results"][0]["name"] == "fresh case"


def test_campaign_progress_jsonl_is_truncated_for_each_run(tmp_path: Path) -> None:
    module = _module()
    progress_jsonl = tmp_path / "progress.jsonl"
    progress_jsonl.write_text("stale event\n", encoding="utf-8")

    progress = module.CampaignProgressWriter(
        jsonl_path=progress_jsonl,
        snapshot_path=tmp_path / "snapshot.json",
    )
    progress.emit("campaign_started", {"selected_shard_count": 1})

    rows = progress_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["event"] == "campaign_started"
