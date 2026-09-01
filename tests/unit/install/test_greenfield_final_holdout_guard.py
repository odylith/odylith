from __future__ import annotations

import hashlib
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

    assert claimed["status"] == "claimed"
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
            implementation_revision="short",
            distribution_provenance_sha256="d" * 64,
        )
    claim_final_holdout_run(
        ledger_path=ledger,
        implementation_revision="b" * 40,
        distribution_provenance_sha256="d" * 64,
    )
    bind_final_holdout_inputs(
        ledger_path=ledger,
        protected_inputs={"final_holdout": holdout, "evaluation_manifest": manifest},
    )
    complete_final_holdout_run(ledger_path=ledger, result_path=result, outcome="failed")

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


def _write(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path
