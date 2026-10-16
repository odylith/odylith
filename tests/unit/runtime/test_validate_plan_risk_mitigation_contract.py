from __future__ import annotations

from pathlib import Path

import pytest

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


@pytest.mark.parametrize('relative', [
    'in-progress/2026-09/legacy.md',
    'in-progress/legacy.md',
    'done/2026-02/2026-02-28-legacy.md',
])
def test_validate_plan_risk_mitigation_contract_fails_for_top_level_mitigation(tmp_path: Path, relative: str) -> None:
    _write_plan(
        tmp_path / "odylith" / "technical-plans" / relative,
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
    assert "plans validated: 1" in out


def test_empty_plan_scope_is_not_reported_as_passing(tmp_path: Path, capsys) -> None:
    (tmp_path / "odylith/technical-plans/in-progress").mkdir(parents=True)
    (tmp_path / "odylith/technical-plans/done").mkdir()

    assert contract.main(["--repo-root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "not applicable" in output
    assert "plans validated: 0" in output
    assert "passed" not in output


def test_missing_plan_scope_is_not_reported_as_empty(tmp_path: Path, capsys) -> None:
    assert contract.main(["--repo-root", str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert "FAILED" in output
    assert "missing" in output
    assert "not applicable" not in output
    assert "passed" not in output


def test_main_reports_the_same_inventory_it_validates(tmp_path: Path, capsys, monkeypatch) -> None:
    path = tmp_path / "odylith/technical-plans/in-progress/2026-09/plan.md"
    _write_plan(path, text=(
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a lock can expire.\n"
        "  - [ ] Mitigation: renew it.\n"
    ))
    selections = []

    def select(*, repo_root):
        selections.append(repo_root)
        assert len(selections) == 1
        return [path]

    monkeypatch.setattr(contract.normalizer, "_list_plan_files", select)
    assert contract.main(["--repo-root", str(tmp_path)]) == 0
    assert selections == [tmp_path]
    assert "plans validated: 1" in capsys.readouterr().out


@pytest.mark.parametrize("notes", ["<br>", "<img src='example.png'>", "<code>"])
def test_inline_html_cannot_hide_an_invalid_relationship(tmp_path: Path, notes: str) -> None:
    path = tmp_path / "odylith/technical-plans/in-progress/plan.md"
    source = (
        "## Risks & Mitigations\n\n"
        "- [x] Risk: a lease expires.\n"
        "- [ ] Mitigation: renew it.\n\n"
        f"Review notes {notes}\n"
    )
    _write_plan(path, text=source)
    errors = contract.validate_plan_risk_mitigation_contract(repo_root=tmp_path)
    assert len(errors) == 1
    assert "invalid Risk -> Mitigation nesting" in errors[0]
    assert path.read_text() == source
