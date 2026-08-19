from __future__ import annotations

import json
from pathlib import Path

import pytest

import greenfield_semantic_development_runner as runner
from greenfield_semantic_pipeline_evidence import prepare_active_evidence_plan


def test_development_runner_binds_every_assignment_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus, plan = _inputs(tmp_path)
    calls: list[tuple[str, str, dict]] = []

    def fake_standard_pipeline(**kwargs: object) -> dict:
        case_id = str(kwargs["case_id"])
        assignment = dict(kwargs["_evidence_assignment"])  # type: ignore[arg-type]
        calls.append((case_id, str(kwargs["host_profile"]), assignment))
        receipt = {
            "case_id": case_id,
            "status": "completed",
            "outcome": "commit",
            "wall_ms": 59_999,
            "model_call_count": 4,
            "restart_count": 0,
        }
        Path(kwargs["output_path"]).write_text(json.dumps(receipt), encoding="utf-8")
        return receipt

    monkeypatch.setattr(runner, "run_standard_pipeline", fake_standard_pipeline)
    output = tmp_path / "run"
    manifest = runner.run_development_standard_cohort(
        corpus_path=corpus,
        active_evidence_plan_path=plan,
        output_directory=output,
    )

    assert manifest["status"] == "completed"
    assert manifest["standard_success_count"] == 2
    assert manifest["model_call_count"] == 8
    assert manifest["restart_count"] == 0
    assert [case for case, _, _ in calls] == ["case-001", "case-002"]
    assert all(host == assignment["host_profile"] for _, host, assignment in calls)
    assert all(assignment["case_id"] == case for case, _, assignment in calls)
    assert {path.name for path in output.iterdir()} == {
        "case-001.standard.json",
        "case-002.standard.json",
        "manifest.json",
    }


def test_development_runner_records_typed_failure_without_rescue_or_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus, plan = _inputs(tmp_path)
    calls = 0

    def fake_standard_pipeline(**kwargs: object) -> dict:
        nonlocal calls
        calls += 1
        case_id = str(kwargs["case_id"])
        outcome = "typed_standard_failure" if case_id == "case-001" else "commit"
        receipt = {
            "case_id": case_id,
            "status": "rescue_required" if outcome != "commit" else "completed",
            "outcome": outcome,
            "wall_ms": 40_000,
            "model_call_count": 4,
            "restart_count": 0,
        }
        Path(kwargs["output_path"]).write_text(json.dumps(receipt), encoding="utf-8")
        return receipt

    monkeypatch.setattr(runner, "run_standard_pipeline", fake_standard_pipeline)
    manifest = runner.run_development_standard_cohort(
        corpus_path=corpus,
        active_evidence_plan_path=plan,
        output_directory=tmp_path / "run",
    )

    assert manifest["status"] == "incomplete"
    assert manifest["typed_rescue_required_count"] == 1
    assert manifest["standard_success_count"] == 1
    assert calls == 2


def test_development_runner_refuses_to_overwrite_evidence_directory(
    tmp_path: Path,
) -> None:
    corpus, plan = _inputs(tmp_path)
    output = tmp_path / "run"
    output.mkdir()
    with pytest.raises(RuntimeError, match="already exists"):
        runner.run_development_standard_cohort(
            corpus_path=corpus,
            active_evidence_plan_path=plan,
            output_directory=output,
        )


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        json.dumps(
            {
                "cases": [
                    {"case_id": "case-002", "prompt": "Second prompt."},
                    {"case_id": "case-001", "prompt": "First prompt."},
                ]
            }
        ),
        encoding="utf-8",
    )
    plan = tmp_path / "plan.json"
    prepare_active_evidence_plan(
        corpus_path=corpus,
        host_profiles=["codex"],
        output_path=plan,
    )
    return corpus, plan
