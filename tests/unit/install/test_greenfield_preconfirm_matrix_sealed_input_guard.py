from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_preconfirm_matrix as matrix  # noqa: E402


def _write(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    return path


def _require_release_inputs(*, root: Path, case_file: Path) -> None:
    matrix._require_sealed_release_input_root(  # noqa: SLF001
        proof_tier="release",
        case_files=(str(case_file),),
        release_audit_file="",
        release_audit_repo_root=root,
        sealed_root=str(root),
        semantic_annotations_file=str(_write(root / "final-holdout.json")),
        evaluation_split_manifest=str(_write(root / "evaluation-splits.json")),
    )


def _final_holdout_args(*, ledger: Path, provenance: Path, output: Path) -> SimpleNamespace:
    return SimpleNamespace(
        proof_tier="release",
        final_holdout_run_ledger=str(ledger),
        implementation_revision="a" * 40,
        output_json=str(output),
        distribution_provenance_file=str(provenance),
        semantic_annotations_file=str(output.parent / "final-holdout.json"),
        evaluation_split_manifest=str(output.parent / "evaluation-splits.json"),
        case_file=(),
    )


def test_sealed_release_input_rejects_a_symlinked_file_before_resolution(tmp_path: Path) -> None:
    root = tmp_path / "sealed-inputs"
    case_target = _write(root / "cases" / "case-target.json")
    case_link = root / "cases" / "case-link.json"
    case_link.symlink_to(case_target)

    with pytest.raises(RuntimeError, match="symlink"):
        _require_release_inputs(root=root, case_file=case_link)


def test_sealed_release_input_rejects_a_symlinked_parent_before_resolution(tmp_path: Path) -> None:
    root = tmp_path / "sealed-inputs"
    case_target = _write(root / "actual-cases" / "case.json")
    linked_parent = root / "linked-cases"
    linked_parent.symlink_to(case_target.parent, target_is_directory=True)

    with pytest.raises(RuntimeError, match="symlink"):
        _require_release_inputs(root=root, case_file=linked_parent / case_target.name)


def test_sealed_release_input_rejects_a_symlinked_root_before_resolution(tmp_path: Path) -> None:
    actual_root = tmp_path / "actual-sealed-inputs"
    case_file = _write(actual_root / "cases" / "case.json")
    linked_root = tmp_path / "linked-sealed-inputs"
    linked_root.symlink_to(actual_root, target_is_directory=True)

    with pytest.raises(RuntimeError, match="symlink"):
        _require_release_inputs(
            root=linked_root,
            case_file=linked_root / case_file.relative_to(actual_root),
        )


def test_final_holdout_rejects_a_dangling_symlinked_ledger_before_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sealed_root = tmp_path / "sealed-inputs"
    sealed_root.mkdir()
    ledger_link = tmp_path / "run-ledger-link.json"
    ledger_link.symlink_to(tmp_path / "missing-ledger-target.json")
    monkeypatch.setattr(matrix, "verify_distribution_provenance", lambda **_kwargs: {"sha256": "d" * 64})

    with pytest.raises(RuntimeError, match="final holdout run ledger.*symlink"):
        matrix._final_holdout_run_from_args(  # noqa: SLF001
            _final_holdout_args(
                ledger=ledger_link,
                provenance=tmp_path / "build-provenance.json",
                output=tmp_path / "result.json",
            ),
            sealed_input_root=str(sealed_root),
        )


def test_final_holdout_rejects_a_symlinked_ledger_parent_before_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sealed_root = tmp_path / "sealed-inputs"
    sealed_root.mkdir()
    actual_ledger_parent = tmp_path / "actual-ledgers"
    actual_ledger_parent.mkdir()
    linked_ledger_parent = tmp_path / "linked-ledgers"
    linked_ledger_parent.symlink_to(actual_ledger_parent, target_is_directory=True)
    monkeypatch.setattr(matrix, "verify_distribution_provenance", lambda **_kwargs: {"sha256": "d" * 64})

    with pytest.raises(RuntimeError, match="final holdout run ledger.*symlink"):
        matrix._final_holdout_run_from_args(  # noqa: SLF001
            _final_holdout_args(
                ledger=linked_ledger_parent / "run-ledger.json",
                provenance=tmp_path / "build-provenance.json",
                output=tmp_path / "result.json",
            ),
            sealed_input_root=str(sealed_root),
        )


def test_final_holdout_rejects_a_symlinked_distribution_provenance_before_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sealed_root = tmp_path / "sealed-inputs"
    sealed_root.mkdir()
    provenance_target = _write(tmp_path / "build-provenance-target.json")
    provenance_link = tmp_path / "build-provenance-link.json"
    provenance_link.symlink_to(provenance_target)

    def fail_if_verified(**_kwargs):
        raise AssertionError("distribution provenance was verified before unresolved-path validation")

    monkeypatch.setattr(matrix, "verify_distribution_provenance", fail_if_verified)

    with pytest.raises(RuntimeError, match="distribution provenance.*symlink"):
        matrix._final_holdout_run_from_args(  # noqa: SLF001
            _final_holdout_args(
                ledger=tmp_path / "run-ledger.json",
                provenance=provenance_link,
                output=tmp_path / "result.json",
            ),
            sealed_input_root=str(sealed_root),
        )
