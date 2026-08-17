from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]
PROOF_RAIL = REPO_ROOT / "bin" / "greenfield-graph-release-proof"


def test_graph_release_proof_keeps_recovery_evidence_outside_distribution() -> None:
    source = PROOF_RAIL.read_text(encoding="utf-8")

    assert 'recovery_output="${RECOVERY_OUTPUT:-${dist_dir%/}-greenfield-transaction-recovery.v1.json}"' in source
    assert '"$dist_dir"|"$dist_dir"/*)' in source
    assert '--output-json "$recovery_output"' in source
    assert '--output-json "$dist_dir/' not in source
    assert source.count("scripts/release/platform_domain_leakage_check.py") == 2


def test_graph_release_proof_keeps_final_holdout_inert_without_explicit_final_mode() -> None:
    source = PROOF_RAIL.read_text(encoding="utf-8")

    assert 'GREENFIELD_FINAL_RELEASE_MODE:-preflight' in source
    assert 'GREENFIELD_FINAL_HOLDOUT_ACTION:-' in source
    assert '[[ -z "$action" ]]' in source
    assert "GREENFIELD_FINAL_RELEASE_MODE=final" in source
    assert "final release mode requires GREENFIELD_FINAL_HOLDOUT_ACTION=prepare or score" in source
    assert "greenfield_final_holdout_run.py prepare" in source
    assert "greenfield_final_holdout_run.py score" in source
    assert "--review \"$GREENFIELD_FINAL_HOLDOUT_REVIEW_A\"" in source
    assert "--review \"$GREENFIELD_FINAL_HOLDOUT_REVIEW_B\"" in source
    assert "odylith-greenfield-final-holdout" not in source
    assert "evaluation-splits-v2-independent" not in source


def test_graph_release_proof_shell_is_well_formed() -> None:
    completed = subprocess.run(
        ["bash", "-n", str(PROOF_RAIL)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
