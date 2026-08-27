from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

import pytest


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_final_holdout_guard import read_final_holdout_run
import greenfield_final_holdout_run as holdout_run
from greenfield_final_holdout_run import FINAL_HOLDOUT_WORK_VERSION
from greenfield_final_holdout_run import prepare_final_holdout_run
from greenfield_final_holdout_run import score_final_holdout_run
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)


def test_final_holdout_prepare_claims_then_assigns_frozen_profiles(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)

    work = prepare_final_holdout_run(**inputs)

    assert work["version"] == FINAL_HOLDOUT_WORK_VERSION
    assert work["status"] == "ready_for_blinded_authoring"
    assert [row["case_id"] for row in work["cases"]] == ["case-a", "case-b"]
    assert [row["host_profile"] for row in work["cases"]] == ["codex", "claude"]
    assert len({row["case_nonce"] for row in work["cases"]}) == 2
    assert work["active_evidence_plan_sha256"] == holdout_run.canonical_sha256(
        work["active_evidence_plan"]
    )
    ledger = read_final_holdout_run(inputs["ledger_path"])
    assert ledger["status"] == "claimed"
    assert ledger["evaluation_contract_sha256"] == _sha(inputs["evaluation_contract_path"])
    assert work["evaluation_contract_sha256"] == ledger["evaluation_contract_sha256"]
    assert work["authoring_contract_sha256"] == semantic_intent_authoring_contract_sha256()
    assert ledger["authoring_contract_sha256"] == work["authoring_contract_sha256"]


def test_final_holdout_prepare_rejects_malformed_contract_before_claim(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    _write_json(inputs["evaluation_contract_path"], {"required_model_profiles": []})
    inputs["holdout_path"].unlink()

    with pytest.raises(RuntimeError, match="evaluation contract is invalid"):
        prepare_final_holdout_run(**inputs)

    assert not inputs["ledger_path"].exists()
    assert not inputs["work_path"].exists()


def test_final_holdout_prepare_consumes_run_when_tracked_corpus_drifts(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    inputs["expected_corpus_sha256"] = "0" * 64

    with pytest.raises(RuntimeError, match="tracked evaluation corpus"):
        prepare_final_holdout_run(**inputs)

    ledger = read_final_holdout_run(inputs["ledger_path"])
    assert ledger["status"] == "failed"
    failure = json.loads(inputs["work_path"].read_text(encoding="utf-8"))
    assert failure["stage"] == "prepare"


def test_final_holdout_score_binds_the_prepared_contract_and_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path)
    prepare_final_holdout_run(**inputs)
    score_inputs = _score_inputs(tmp_path, inputs)
    observed: dict = {}

    def fake_evaluate(**kwargs: object) -> dict:
        observed.update(kwargs)
        return {"version": "test-report.v1", "status": "passed", "passed": True}

    monkeypatch.setattr(holdout_run, "evaluate_semantic_release", fake_evaluate)

    report = score_final_holdout_run(**score_inputs)

    assert report["passed"] is True
    assert observed["contract"] == json.loads(
        inputs["evaluation_contract_path"].read_text(encoding="utf-8")
    )
    assert observed["active_evidence_plan"] == json.loads(
        inputs["work_path"].read_text(encoding="utf-8")
    )["active_evidence_plan"]
    assert set(observed["auxiliary_reports"]) == {
        "host_parity",
        "lower_capability_safety",
    }
    assert json.loads(score_inputs["result_path"].read_text(encoding="utf-8")) == report
    ledger = read_final_holdout_run(inputs["ledger_path"])
    assert ledger["status"] == "passed"
    assert ledger["result_path"] == str(score_inputs["result_path"].resolve())
    assert ledger["result_sha256"] == _sha(score_inputs["result_path"])


def test_final_holdout_score_rejects_contract_drift_before_evaluator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path)
    prepare_final_holdout_run(**inputs)
    inputs["evaluation_contract_path"].write_text(
        inputs["evaluation_contract_path"].read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    score_inputs = _score_inputs(tmp_path, inputs)
    called = False

    def forbidden_evaluate(**_kwargs: object) -> dict:
        nonlocal called
        called = True
        raise AssertionError("evaluator must not run for a changed contract")

    monkeypatch.setattr(holdout_run, "evaluate_semantic_release", forbidden_evaluate)

    with pytest.raises(RuntimeError, match="contract bytes changed"):
        score_final_holdout_run(**score_inputs)

    assert called is False
    ledger = read_final_holdout_run(inputs["ledger_path"])
    assert ledger["status"] == "failed"
    failure_path = Path(ledger["result_path"])
    assert failure_path != score_inputs["result_path"]
    assert json.loads(failure_path.read_text(encoding="utf-8"))["stage"] == "score"


def test_final_holdout_score_rejects_work_assignment_drift_before_evaluator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path)
    prepare_final_holdout_run(**inputs)
    work = json.loads(inputs["work_path"].read_text(encoding="utf-8"))
    work["cases"][0]["case_nonce"] = "replaced-runner-nonce"
    _write_json(inputs["work_path"], work)
    score_inputs = _score_inputs(tmp_path, inputs)
    called = False

    def forbidden_evaluate(**_kwargs: object) -> dict:
        nonlocal called
        called = True
        raise AssertionError("evaluator must not run for changed work")

    monkeypatch.setattr(holdout_run, "evaluate_semantic_release", forbidden_evaluate)

    with pytest.raises(RuntimeError, match="work case changed after preparation"):
        score_final_holdout_run(**score_inputs)

    assert called is False
    assert read_final_holdout_run(inputs["ledger_path"])["status"] == "failed"


def test_final_holdout_score_never_binds_a_stale_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path)
    prepare_final_holdout_run(**inputs)
    score_inputs = _score_inputs(tmp_path, inputs)
    stale = _write_json(score_inputs["result_path"], {"status": "stale"})
    stale_hash = _sha(stale)
    monkeypatch.setattr(
        holdout_run,
        "evaluate_semantic_release",
        lambda **_kwargs: {"version": "test-report.v1", "status": "passed", "passed": True},
    )

    with pytest.raises(RuntimeError, match="output already exists"):
        score_final_holdout_run(**score_inputs)

    ledger = read_final_holdout_run(inputs["ledger_path"])
    failure_path = Path(ledger["result_path"])
    assert ledger["status"] == "failed"
    assert failure_path != stale
    assert ledger["result_sha256"] == _sha(failure_path)
    assert ledger["result_sha256"] != stale_hash
    assert json.loads(stale.read_text(encoding="utf-8")) == {"status": "stale"}


def test_final_holdout_score_rejects_authoring_contract_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _inputs(tmp_path)
    prepare_final_holdout_run(**inputs)
    score_inputs = _score_inputs(tmp_path, inputs)
    monkeypatch.setattr(
        holdout_run,
        "semantic_intent_authoring_contract_sha256",
        lambda: "f" * 64,
    )
    monkeypatch.setattr(
        holdout_run,
        "evaluate_semantic_release",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("evaluator must not run after authoring-contract drift")
        ),
    )

    with pytest.raises(RuntimeError, match="authoring contract changed"):
        score_final_holdout_run(**score_inputs)

    assert read_final_holdout_run(inputs["ledger_path"])["status"] == "failed"


def test_final_holdout_runner_contains_no_protected_path_or_prose_matcher() -> None:
    source = (SCRIPTS_ROOT / "greenfield_final_holdout_run.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "odylith-greenfield-final-holdout-20260809" not in source
    assert "evaluation-splits-v2-independent" not in source
    assert imported.isdisjoint({"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"})
    assert "similarity" not in source.casefold()


def _inputs(tmp_path: Path) -> dict:
    tracked = _write_json(tmp_path / "corpus.json", {"cases": []})
    tracked_sha = _sha(tracked)
    manifest = _write_json(
        tmp_path / "manifest.json",
        {"tracked_corpus": {"path": "corpus.json", "sha256": tracked_sha}},
    )
    holdout = _write_json(
        tmp_path / "holdout.json",
        {
            "cases": [
                {"case_id": "case-b", "prompt": "Build B."},
                {"case_id": "case-a", "prompt": "Build A."},
            ],
            "annotations": [{"case_id": "case-a"}, {"case_id": "case-b"}],
        },
    )
    contract = _write_json(
        tmp_path / "contract.json",
        json.loads(
            (
                SCRIPTS_ROOT
                / "fixtures"
                / "greenfield-semantic-release-evaluation-contract.v18.json"
            ).read_text(encoding="utf-8")
        ),
    )
    return {
        "repo_root": tmp_path,
        "ledger_path": tmp_path / "ledger.json",
        "holdout_path": holdout,
        "evaluation_manifest_path": manifest,
        "evaluation_contract_path": contract,
        "work_path": tmp_path / "work.json",
        "implementation_revision": "a" * 40,
        "expected_holdout_sha256": _sha(holdout),
        "expected_evaluation_manifest_sha256": _sha(manifest),
        "expected_corpus_sha256": tracked_sha,
    }


def _score_inputs(tmp_path: Path, prepare_inputs: dict) -> dict:
    candidates = _write_json(
        tmp_path / "candidates.json",
        {"implementation_revision": prepare_inputs["implementation_revision"]},
    )
    reviews = [
        _write_json(tmp_path / "review-a.json", {}),
        _write_json(tmp_path / "review-b.json", {}),
    ]
    adjudication = _write_json(tmp_path / "adjudication.json", {})
    deterministic_law_report = _write_json(tmp_path / "deterministic-laws.json", {})
    host_parity_report = _write_json(tmp_path / "host-parity.json", {})
    lower_capability_safety_report = _write_json(tmp_path / "lower-safety.json", {})
    return {
        "ledger_path": prepare_inputs["ledger_path"],
        "holdout_path": prepare_inputs["holdout_path"],
        "evaluation_contract_path": prepare_inputs["evaluation_contract_path"],
        "work_path": prepare_inputs["work_path"],
        "deterministic_law_report_path": deterministic_law_report,
        "candidates_path": candidates,
        "review_paths": reviews,
        "adjudication_path": adjudication,
        "host_parity_report_path": host_parity_report,
        "lower_capability_safety_report_path": lower_capability_safety_report,
        "result_path": tmp_path / "result.json",
    }


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
