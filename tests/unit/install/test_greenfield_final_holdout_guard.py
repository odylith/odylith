from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest

SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_final_holdout_guard import claim_final_holdout_run
from greenfield_final_holdout_guard import complete_final_holdout_run
from greenfield_final_holdout_guard import read_final_holdout_run


def test_final_holdout_guard_allows_exactly_one_claim_and_binds_result(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{"cases": []}\n')
    manifest = _write(tmp_path / "manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", '{"status": "passed"}\n')
    ledger = tmp_path / "run-ledger.json"

    claimed = claim_final_holdout_run(
        ledger_path=ledger,
        holdout_path=holdout,
        evaluation_manifest_path=manifest,
        implementation_revision="a" * 40,
        expected_holdout_sha256=_sha(holdout),
        expected_evaluation_manifest_sha256=_sha(manifest),
        evaluation_contract_sha256="e" * 64,
        authoring_contract_sha256="f" * 64,
    )

    assert claimed["status"] == "claimed"
    assert claimed["disclosed"] is True
    assert claimed["holdout_sha256"] == hashlib.sha256(holdout.read_bytes()).hexdigest()
    assert claimed["evaluation_contract_sha256"] == "e" * 64
    assert claimed["authoring_contract_sha256"] == "f" * 64
    with pytest.raises(RuntimeError, match="already claimed"):
        claim_final_holdout_run(
            ledger_path=ledger,
            holdout_path=holdout,
            evaluation_manifest_path=manifest,
            implementation_revision="a" * 40,
            expected_holdout_sha256=_sha(holdout),
            expected_evaluation_manifest_sha256=_sha(manifest),
            evaluation_contract_sha256="e" * 64,
            authoring_contract_sha256="f" * 64,
        )

    completed = complete_final_holdout_run(
        ledger_path=ledger,
        result_path=result,
        outcome="passed",
    )

    assert completed["status"] == "passed"
    assert completed["result_sha256"] == hashlib.sha256(result.read_bytes()).hexdigest()
    assert read_final_holdout_run(ledger) == completed


def test_final_holdout_guard_rejects_short_revision_or_second_completion(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    manifest = _write(tmp_path / "manifest.json", '{}\n')
    result = _write(tmp_path / "result.json", '{}\n')
    ledger = tmp_path / "run-ledger.json"

    with pytest.raises(RuntimeError, match="full implementation Git revision"):
        claim_final_holdout_run(
            ledger_path=ledger,
            holdout_path=holdout,
            evaluation_manifest_path=manifest,
            implementation_revision="short",
            expected_holdout_sha256=_sha(holdout),
            expected_evaluation_manifest_sha256=_sha(manifest),
            evaluation_contract_sha256="e" * 64,
            authoring_contract_sha256="f" * 64,
        )
    claim_final_holdout_run(
        ledger_path=ledger,
        holdout_path=holdout,
        evaluation_manifest_path=manifest,
        implementation_revision="b" * 40,
        expected_holdout_sha256=_sha(holdout),
        expected_evaluation_manifest_sha256=_sha(manifest),
        evaluation_contract_sha256="e" * 64,
        authoring_contract_sha256="f" * 64,
    )
    complete_final_holdout_run(ledger_path=ledger, result_path=result, outcome="failed")

    with pytest.raises(RuntimeError, match="not in its one terminalizable claimed state"):
        complete_final_holdout_run(ledger_path=ledger, result_path=result, outcome="passed")


def test_final_holdout_guard_rejects_symlinked_inputs(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    holdout_link = tmp_path / "holdout-link.json"
    holdout_link.symlink_to(holdout)
    manifest = _write(tmp_path / "manifest.json", '{}\n')

    ledger = tmp_path / "run-ledger.json"
    with pytest.raises(RuntimeError, match="missing or unsafe"):
        claim_final_holdout_run(
            ledger_path=ledger,
            holdout_path=holdout_link,
            evaluation_manifest_path=manifest,
            implementation_revision="c" * 40,
            expected_holdout_sha256=_sha(holdout),
            expected_evaluation_manifest_sha256=_sha(manifest),
            evaluation_contract_sha256="e" * 64,
            authoring_contract_sha256="f" * 64,
        )

    consumed = read_final_holdout_run(ledger)
    assert consumed["status"] == "failed"
    assert consumed["disclosed"] is True


def test_final_holdout_guard_consumes_run_before_hash_mismatch(tmp_path: Path) -> None:
    holdout = _write(tmp_path / "holdout.json", '{}\n')
    manifest = _write(tmp_path / "manifest.json", '{}\n')
    ledger = tmp_path / "run-ledger.json"

    with pytest.raises(RuntimeError, match="frozen expected hash"):
        claim_final_holdout_run(
            ledger_path=ledger,
            holdout_path=holdout,
            evaluation_manifest_path=manifest,
            implementation_revision="d" * 40,
            expected_holdout_sha256="0" * 64,
            expected_evaluation_manifest_sha256=_sha(manifest),
            evaluation_contract_sha256="e" * 64,
            authoring_contract_sha256="f" * 64,
        )

    assert read_final_holdout_run(ledger)["status"] == "failed"
    with pytest.raises(RuntimeError, match="already claimed"):
        claim_final_holdout_run(
            ledger_path=ledger,
            holdout_path=holdout,
            evaluation_manifest_path=manifest,
            implementation_revision="d" * 40,
            expected_holdout_sha256=_sha(holdout),
            expected_evaluation_manifest_sha256=_sha(manifest),
            evaluation_contract_sha256="e" * 64,
            authoring_contract_sha256="f" * 64,
        )


def _write(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
