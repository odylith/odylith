from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_final_holdout_guard import claim_final_holdout_run
from greenfield_final_holdout_guard import bind_final_holdout_inputs
from greenfield_final_holdout_guard import complete_final_holdout_run
from greenfield_final_holdout_guard import read_final_holdout_run
from greenfield_matrix_release_artifacts import begin_retained_case_evidence
from greenfield_matrix_release_artifacts import finalize_retained_case_evidence
from greenfield_matrix_release_artifacts import prepare_retained_evidence_output_dir
from greenfield_matrix_release_artifacts import record_retained_case_json
from greenfield_matrix_release_artifacts import record_retained_case_text
from greenfield_matrix_release_artifacts import write_retained_evidence_manifest


def test_final_holdout_guard_allows_exactly_one_claim_and_binds_result(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{"cases": []}\n')
    manifest = _write(tmp_path / "manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", '{"status": "passed"}\n')
    ledger = tmp_path / "run-ledger.json"

    claimed = claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="a" * 40,
        distribution_provenance_sha256="d" * 64,
    )
    retained = _retained_evidence(
        tmp_path,
        case_id="GFH-001",
        status="passed",
        run_id=claimed["run_id"],
    )

    assert claimed["status"] == "claimed"
    assert len(claimed["run_id"]) == 64
    assert claimed["disclosed"] is True
    assert claimed["protected_inputs_bound"] is False
    with pytest.raises(RuntimeError, match="already claimed"):
        claim_final_holdout_run(
            ledger_path=ledger,
            implementation_revision="a" * 40,
            distribution_provenance_sha256="d" * 64,
        )

    bound = bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={"final_holdout": holdout, "evaluation_manifest": manifest},
    )
    assert bound["protected_inputs_bound"] is True
    assert bound["protected_inputs"]["final_holdout"]["sha256"] == hashlib.sha256(holdout.read_bytes()).hexdigest()

    completed = complete_final_holdout_run(
        ledger_path=ledger,
        result_path=result,
        outcome="passed",
        retained_evidence_manifest=retained,
    )

    assert completed["status"] == "passed"
    assert completed["result_sha256"] == hashlib.sha256(result.read_bytes()).hexdigest()
    assert completed["retained_evidence"]["manifest_sha256"] == hashlib.sha256(retained.read_bytes()).hexdigest()
    assert read_final_holdout_run(ledger) == completed


def test_final_holdout_guard_rejects_short_revision_or_second_completion(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    manifest = _write(tmp_path / "manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", '{}\n')
    ledger = tmp_path / "run-ledger.json"

    with pytest.raises(RuntimeError, match="full implementation Git revision"):
        claim_final_holdout_run(
            ledger_path=ledger,
            implementation_revision="short",
            distribution_provenance_sha256="d" * 64,
        )
    claimed = claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="b" * 40,
        distribution_provenance_sha256="d" * 64,
    )
    bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={"final_holdout": holdout, "evaluation_manifest": manifest},
    )
    complete_final_holdout_run(
        ledger_path=ledger,
        result_path=result,
        outcome="failed",
        retained_evidence_manifest=_retained_evidence(
            tmp_path,
            case_id="GFH-002",
            status="failed",
            run_id=claimed["run_id"],
        ),
    )

    with pytest.raises(RuntimeError, match="not in its one terminalizable claimed state"):
        complete_final_holdout_run(ledger_path=ledger, result_path=result, outcome="passed")


def test_final_holdout_guard_claims_before_read_and_rejects_symlinked_inputs(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    holdout_link = tmp_path / "holdout-link.json"
    holdout_link.symlink_to(holdout)
    manifest = _write(tmp_path / "manifest.json", '{}\n')

    ledger = tmp_path / "run-ledger.json"
    claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="c" * 40,
        distribution_provenance_sha256="d" * 64,
    )
    assert read_final_holdout_run(ledger)["status"] == "claimed"
    with pytest.raises(RuntimeError, match="missing or unsafe"):
        bind_final_holdout_inputs(
            ledger_path=ledger,
            protected_inputs={"final_holdout": holdout_link, "evaluation_manifest": manifest},
        )


@pytest.mark.parametrize("outcome", ("passed", "failed", "interrupted"))
def test_final_holdout_guard_rejects_terminal_outcome_without_retained_evidence(
    tmp_path: Path,
    outcome: str,
) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    manifest = _write(tmp_path / "manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", '{}\n')
    ledger = tmp_path / "run-ledger.json"
    claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="e" * 40,
        distribution_provenance_sha256="f" * 64,
    )
    bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={"final_holdout": holdout, "evaluation_manifest": manifest},
    )

    with pytest.raises(RuntimeError, match="requires retained release evidence"):
        complete_final_holdout_run(ledger_path=ledger, result_path=result, outcome=outcome)
    assert read_final_holdout_run(ledger)["status"] == "claimed"


@pytest.mark.parametrize("outcome", ("failed", "interrupted"))
def test_final_holdout_guard_binds_nonpassing_terminal_evidence(
    tmp_path: Path,
    outcome: str,
) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    evaluation_manifest = _write(tmp_path / "evaluation-manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", json.dumps({"status": outcome}) + "\n")
    ledger = tmp_path / "run-ledger.json"
    claimed = claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="e" * 40,
        distribution_provenance_sha256="f" * 64,
    )
    retained = _retained_evidence(
        tmp_path,
        case_id=f"GFH-{outcome}",
        status=outcome,
        run_id=claimed["run_id"],
    )
    bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={
            "final_holdout": holdout,
            "evaluation_manifest": evaluation_manifest,
        },
    )

    completed = complete_final_holdout_run(
        ledger_path=ledger,
        result_path=result,
        outcome=outcome,
        retained_evidence_manifest=retained,
    )

    assert completed["status"] == outcome
    assert completed["retained_evidence"] == {
        "manifest_path": str(retained),
        "manifest_sha256": hashlib.sha256(retained.read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize("outcome", ("failed", "interrupted"))
def test_final_holdout_guard_rejects_tampered_nonpassing_evidence(
    tmp_path: Path,
    outcome: str,
) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    evaluation_manifest = _write(tmp_path / "evaluation-manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", json.dumps({"status": outcome}) + "\n")
    ledger = tmp_path / "run-ledger.json"
    claimed = claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="e" * 40,
        distribution_provenance_sha256="f" * 64,
    )
    retained = _retained_evidence(
        tmp_path,
        case_id=f"GFH-{outcome}",
        status=outcome,
        run_id=claimed["run_id"],
    )
    evidence_case_root = retained.parent / f"gfh-{outcome}"
    (evidence_case_root / "case-result.v1.json").write_text("tampered\n", encoding="utf-8")
    bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={
            "final_holdout": holdout,
            "evaluation_manifest": evaluation_manifest,
        },
    )

    with pytest.raises(RuntimeError, match="retained release evidence is invalid"):
        complete_final_holdout_run(
            ledger_path=ledger,
            result_path=result,
            outcome=outcome,
            retained_evidence_manifest=retained,
        )
    assert read_final_holdout_run(ledger)["status"] == "claimed"


def test_final_holdout_guard_rejects_empty_terminal_evidence_manifest(tmp_path: Path) -> None:
    result = _write(tmp_path / "result.json", '{"status":"failed"}\n')
    ledger = tmp_path / "run-ledger.json"
    claimed = claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="e" * 40,
        distribution_provenance_sha256="f" * 64,
    )
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "retained-empty",
        temp_parent=tmp_path / "temp",
    )
    retained = write_retained_evidence_manifest(
        root=root,
        expected_case_ids=(),
        run_id=claimed["run_id"],
    )

    with pytest.raises(RuntimeError, match="terminal evidence contains no cases"):
        complete_final_holdout_run(
            ledger_path=ledger,
            result_path=result,
            outcome="failed",
            retained_evidence_manifest=retained,
        )

    assert read_final_holdout_run(ledger)["status"] == "claimed"


@pytest.mark.parametrize("outcome", ("passed", "failed", "interrupted"))
def test_final_holdout_guard_rejects_manifest_from_a_different_run(
    tmp_path: Path,
    outcome: str,
) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    evaluation_manifest = _write(tmp_path / "evaluation-manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", json.dumps({"status": outcome}) + "\n")
    stale = _retained_evidence(
        tmp_path,
        case_id=f"GFH-stale-{outcome}",
        status=outcome,
        run_id="a" * 64,
    )
    ledger = tmp_path / "run-ledger.json"
    claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="e" * 40,
        distribution_provenance_sha256="f" * 64,
    )
    bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={
            "final_holdout": holdout,
            "evaluation_manifest": evaluation_manifest,
        },
    )

    with pytest.raises(RuntimeError, match="belongs to a different final holdout run"):
        complete_final_holdout_run(
            ledger_path=ledger,
            result_path=result,
            outcome=outcome,
            retained_evidence_manifest=stale,
        )

    assert read_final_holdout_run(ledger)["status"] == "claimed"


def test_final_holdout_guard_preserves_legacy_v2_completion_without_new_evidence(
    tmp_path: Path,
) -> None:
    ledger = _write(
        tmp_path / "legacy-run-ledger.json",
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout-run.v2",
                "status": "claimed",
                "disclosed": True,
                "protected_inputs_bound": False,
                "protected_inputs": {},
            }
        )
        + "\n",
    )
    result = _write(tmp_path / "legacy-result.json", '{"status":"failed"}\n')

    completed = complete_final_holdout_run(
        ledger_path=ledger,
        result_path=result,
        outcome="failed",
    )

    assert completed["status"] == "failed"
    assert "retained_evidence" not in completed


def _retained_evidence(
    tmp_path: Path,
    *,
    case_id: str,
    status: str,
    run_id: str,
) -> Path:
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / f"retained-{status}",
        temp_parent=tmp_path / "temp",
    )
    case = begin_retained_case_evidence(evidence_root=root, case_id=case_id)
    for name in ("propose.stdout", "propose.stderr", "create.stdout", "create.stderr"):
        record_retained_case_text(case, f"commands/{name}", "")
    record_retained_case_json(case, "semantic/proposal-payload.v1.json", {"mode": "clarification_required"})
    finalize_retained_case_evidence(
        case=case,
        repo_root=tmp_path / "missing-repo",
        result_payload={"status": status, "evidence": {}},
    )
    return write_retained_evidence_manifest(
        root=root,
        expected_case_ids=(case_id,),
        run_id=run_id,
    )


def _write(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path
