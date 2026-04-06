from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance import validate_plan_risk_mitigation_contract as contract


def _write_plan(path: Path, *, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_validate_plan_risk_mitigation_contract_passes_for_normalized_file(tmp_path: Path) -> None:
    _write_plan(
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-02-28-normalized.md",
        text=(
            "Status: In progress\n\n"
            "## Risks & Mitigations\n\n"
            "- [x] Risk: deterministic normalization contract drifts.\n"
            "  - [x] Mitigation: enforce check in sync workflow.\n\n"
            "## Validation/Test Plan\n\n"
            "- [x] baseline.\n"
        ),
    )

    errors = contract.validate_plan_risk_mitigation_contract(repo_root=tmp_path)
    assert errors == []


def test_validate_plan_risk_mitigation_contract_fails_for_top_level_mitigation(tmp_path: Path) -> None:
    _write_plan(
        tmp_path / "odylith" / "technical-plans" / "done" / "2026-02" / "2026-02-28-legacy.md",
        text=(
            "Status: Done\n\n"
            "## Risks & Mitigations\n\n"
            "- [x] Risk: legacy formatting remains.\n"
            "- [x] Mitigation: normalize this section.\n"
        ),
    )

    errors = contract.validate_plan_risk_mitigation_contract(repo_root=tmp_path)
    assert any("invalid Risk -> Mitigation nesting" in item for item in errors)


def test_main_returns_2_when_contract_fails(
    tmp_path: Path,
    capsys,  # noqa: ANN001 - pytest fixture
) -> None:
    _write_plan(
        tmp_path / "odylith" / "technical-plans" / "done" / "legacy" / "legacy-plan.md",
        text=(
            "Status: Done\n\n"
            "## Risks & Mitigations\n\n"
            "- [x] Risk: drift.\n"
            "- [x] Mitigation: enforce.\n"
        ),
    )

    rc = contract.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "plan risk/mitigation contract FAILED" in out
