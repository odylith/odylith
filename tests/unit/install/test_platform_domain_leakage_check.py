from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.release import platform_domain_leakage_check as leakage


def test_domain_leakage_terms_use_distinctive_matrix_vocabulary() -> None:
    terms = set(leakage.domain_leakage_terms())

    assert {"quantum", "qber", "chsh", "wafer", "tariff", "pediatric"} <= terms
    assert "source" not in terms
    assert "security" not in terms
    assert "evidence" not in terms


def test_scan_repo_blocks_fixture_terms_in_platform_code(tmp_path: Path) -> None:
    platform_file = tmp_path / "src" / "odylith" / "runtime" / "example.py"
    platform_file.parent.mkdir(parents=True)
    platform_file.write_text('PROMPT = "quantum onboarding should never live here"\\n', encoding="utf-8")

    findings = leakage.scan_repo(tmp_path, terms=("quantum",))

    assert findings == (
        leakage.LeakageFinding(location="src/odylith/runtime/example.py", term="quantum", line=1),
    )


def test_scan_repo_allows_fixture_terms_in_governance_evidence(tmp_path: Path) -> None:
    evidence_file = tmp_path / "odylith" / "casebook" / "bugs" / "repro.md"
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text("quantum failure reproduced here\\n", encoding="utf-8")

    assert leakage.scan_repo(tmp_path, terms=("quantum",)) == ()


def test_scan_dist_blocks_fixture_terms_inside_runtime_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "odylith-0.1.15-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("odylith/runtime/example.py", 'VALUE = "wafer custody"\\n')
        zf.writestr("tests/test_fixture.py", 'VALUE = "wafer custody"\\n')

    findings = leakage.scan_dist(tmp_path, terms=("wafer",))

    assert findings == (
        leakage.LeakageFinding(
            location="wheel:odylith-0.1.15-py3-none-any.whl:odylith/runtime/example.py",
            term="wafer",
            line=1,
        ),
    )


def test_scan_dist_allows_matrix_proof_json_as_evidence(tmp_path: Path) -> None:
    proof = tmp_path / "greenfield-post-confirm-matrix-20260629.v1.json"
    proof.write_text('{"case": "quantum communication lab"}\\n', encoding="utf-8")

    assert leakage.scan_dist(tmp_path, terms=("quantum",)) == ()


def test_main_returns_failed_status_for_platform_leak(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    platform_file = tmp_path / "src" / "odylith" / "runtime" / "example.py"
    platform_file.parent.mkdir(parents=True)
    platform_file.write_text('PROMPT = "qber must not be hardcoded"\\n', encoding="utf-8")

    exit_code = leakage.main(["--repo-root", str(tmp_path)])

    assert exit_code == 1
    assert "platform domain leakage check failed" in capsys.readouterr().err
