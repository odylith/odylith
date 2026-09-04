from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_release_artifacts import begin_retained_case_evidence
from greenfield_matrix_release_artifacts import finalize_retained_case_evidence
from greenfield_matrix_release_artifacts import prepare_retained_evidence_output_dir
from greenfield_matrix_release_artifacts import record_retained_case_bytes
from greenfield_matrix_release_artifacts import record_retained_case_json
from greenfield_matrix_release_artifacts import record_retained_case_text
from greenfield_matrix_release_artifacts import retained_case_evidence_fd
from greenfield_matrix_release_artifacts import retained_evidence_manifest_issues
from greenfield_matrix_release_artifacts import seal_interrupted_retained_evidence
from greenfield_matrix_release_artifacts import write_retained_evidence_manifest


def test_retained_evidence_survives_temp_cleanup_and_detects_tampering(tmp_path: Path) -> None:
    temp_parent = tmp_path / "temp"
    temp_parent.mkdir()
    repo = temp_parent / "sim"
    transaction_hash = "a" * 64
    transaction = repo / ".odylith/runtime/greenfield/pending" / transaction_hash / "product-create-transaction.v1.json"
    receipt = transaction.with_name(transaction.name + ".compiler-receipt.v1.json")
    generation = repo / ".odylith/runtime/greenfield/generations" / transaction_hash
    _write(transaction, '{"transaction_hash":"' + transaction_hash + '"}\n')
    _write(receipt, '{"version":"receipt"}\n')
    _write(generation / "generation-manifest.v1.json", '{"version":"generation"}\n')
    _write(generation / "repository/odylith/radar/source/ideas/workstream.md", "# Workstream\n")
    _write(generation / "repository/odylith/atlas/source/system.mmd", "flowchart LR\nA --- B\n")
    _write(generation / "repository/odylith/atlas/source/system.svg", "<svg></svg>\n")
    _write(repo / ".odylith/runtime/greenfield/active-generation.v1.json", '{}\n')

    evidence_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=evidence_root, case_id="GFH-001")
    for name in ("propose.stdout", "propose.stderr", "create.stdout", "create.stderr"):
        record_retained_case_text(case, f"commands/{name}", f"{name}\n")
    record_retained_case_json(case, "semantic/proposal-payload.v1.json", {"mode": "product_create_transaction"})
    record_retained_case_json(case, "semantic/dry-run-receipt.v2.json", {"status": "compiled"})
    record_retained_case_json(case, "semantic/create-payload.v1.json", {"status": "passed"})
    record_retained_case_text(case, "browser/project-desktop.png", "png")
    result = {
        "status": "passed",
        "evidence": {
            "preconfirm_dry_run": {
                "status": "compiled",
                "transaction_hash": transaction_hash,
                "transaction_file": str(transaction.relative_to(repo)),
                "compiler_receipt_file": str(receipt.relative_to(repo)),
            },
            "browser_surface_proof": {"required": True, "attempted": True},
        },
    }
    finalize_retained_case_evidence(case=case, repo_root=repo, result_payload=result)
    manifest = write_retained_evidence_manifest(root=evidence_root, expected_case_ids=("GFH-001",))

    shutil.rmtree(repo)
    assert retained_evidence_manifest_issues(manifest, expected_case_ids=("GFH-001",)) == ()
    retained_atlas = evidence_root / "gfh-001/generated/odylith/atlas/source/system.svg"
    assert retained_atlas.read_text(encoding="utf-8") == "<svg></svg>\n"

    retained_atlas.write_text("tampered\n", encoding="utf-8")
    assert "retained case evidence hash changed" in " ".join(retained_evidence_manifest_issues(manifest))


def test_retained_case_descriptor_accepts_child_style_bytes_without_exposing_a_path(
    tmp_path: Path,
) -> None:
    temp_parent = tmp_path / "temp"
    temp_parent.mkdir()
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=root, case_id="GFH-model")

    with retained_case_evidence_fd(
        case, "semantic/model-authoring-observation.v1.json"
    ) as descriptor:
        assert descriptor > 2
        os.write(descriptor, b'{"status":"captured"}\n')

    assert (
        case.staging_root / "semantic/model-authoring-observation.v1.json"
    ).read_bytes() == b'{"status":"captured"}\n'


def test_retained_evidence_output_rejects_temp_overlap_and_symlink_escape(tmp_path: Path) -> None:
    temp_parent = tmp_path / "temp"
    temp_parent.mkdir()
    with pytest.raises(RuntimeError, match="outside and disjoint"):
        prepare_retained_evidence_output_dir(
            output_dir=temp_parent / "evidence",
            temp_parent=temp_parent,
        )

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(RuntimeError, match="crosses a symlink"):
        prepare_retained_evidence_output_dir(
            output_dir=link / "evidence",
            temp_parent=temp_parent,
        )


def test_retained_case_rejects_symlinked_generation_artifact(tmp_path: Path) -> None:
    temp_parent = tmp_path / "temp"
    repo = temp_parent / "sim"
    transaction_hash = "b" * 64
    generation = repo / ".odylith/runtime/greenfield/generations" / transaction_hash
    _write(generation / "generation-manifest.v1.json", '{}\n')
    repository = generation / "repository"
    repository.mkdir(parents=True)
    outside = _write(tmp_path / "outside.md", "outside\n")
    (repository / "escaped.md").symlink_to(outside)
    evidence_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=evidence_root, case_id="GFH-002")

    with pytest.raises(RuntimeError, match="contains a symlink"):
        finalize_retained_case_evidence(
            case=case,
            repo_root=repo,
            result_payload={
                "status": "failed",
                "evidence": {"preconfirm_dry_run": {"transaction_hash": transaction_hash}},
            },
        )


def test_case_manifest_is_readable_json_after_atomic_publication(tmp_path: Path) -> None:
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=tmp_path / "temp",
    )
    case = begin_retained_case_evidence(evidence_root=root, case_id="GFH-003")
    manifest = finalize_retained_case_evidence(
        case=case,
        repo_root=tmp_path / "missing",
        result_payload={"status": "failed", "evidence": {}},
    )

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["case_id"] == "GFH-003"
    assert not any(path.name.endswith(".staging") for path in root.iterdir())


def test_retained_case_bytes_preserve_partial_binary_evidence_exactly(tmp_path: Path) -> None:
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=tmp_path / "temp",
    )
    case = begin_retained_case_evidence(evidence_root=root, case_id="GFH-interrupted")
    payload = b"\x89PNG\r\n\x1a\n\x00\xffpartial"

    record_retained_case_bytes(case, "interrupted/partial-browser.png", payload)
    finalize_retained_case_evidence(
        case=case,
        repo_root=tmp_path / "missing",
        result_payload={"status": "interrupted", "evidence": {}},
    )
    manifest = write_retained_evidence_manifest(
        root=root,
        expected_case_ids=("GFH-interrupted",),
    )

    assert (root / "gfh-interrupted/interrupted/partial-browser.png").read_bytes() == payload
    assert retained_evidence_manifest_issues(manifest) == ()


def test_interruption_seal_captures_unfinalized_binary_evidence(tmp_path: Path) -> None:
    temp_parent = tmp_path / "temp"
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    partial = begin_retained_case_evidence(evidence_root=root, case_id="GFH-partial")
    payload = b"\x89PNG\r\n\x1a\n\x00\xffpartial"
    record_retained_case_bytes(partial, "browser/partial.png", payload)
    result = _write(tmp_path / "interrupted-result.json", '{"status":"interrupted"}\n')
    run_id = "a" * 64

    manifest = seal_interrupted_retained_evidence(
        output_dir=root,
        temp_parent=temp_parent,
        result_path=result,
        run_id=run_id,
    )

    captured = list((root / "final-holdout-interruption/interrupted").rglob("partial.png"))
    assert len(captured) == 1
    assert captured[0].read_bytes() == payload
    assert json.loads(manifest.read_text(encoding="utf-8"))["run_id"] == run_id
    assert retained_evidence_manifest_issues(manifest, expected_run_id=run_id) == ()
    assert not any(path.name.endswith(".staging") for path in root.iterdir())


def test_interruption_seal_rejects_manifest_from_a_different_run(tmp_path: Path) -> None:
    temp_parent = tmp_path / "temp"
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=root, case_id="GFH-stale")
    finalize_retained_case_evidence(
        case=case,
        repo_root=tmp_path / "missing",
        result_payload={"status": "interrupted", "evidence": {}},
    )
    stale = write_retained_evidence_manifest(
        root=root,
        expected_case_ids=("GFH-stale",),
        run_id="a" * 64,
    )
    stale_bytes = stale.read_bytes()
    result = _write(tmp_path / "interrupted-result.json", '{"status":"interrupted"}\n')

    with pytest.raises(RuntimeError, match="interruption evidence is invalid"):
        seal_interrupted_retained_evidence(
            output_dir=root,
            temp_parent=temp_parent,
            result_path=result,
            run_id="b" * 64,
        )

    assert stale.read_bytes() == stale_bytes


def test_passing_evidence_validation_rejects_empty_or_failed_case_packages(tmp_path: Path) -> None:
    empty_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "empty-evidence",
        temp_parent=tmp_path / "temp",
    )
    empty_manifest = write_retained_evidence_manifest(root=empty_root, expected_case_ids=())
    assert "must contain at least one case" in " ".join(
        retained_evidence_manifest_issues(empty_manifest, require_passed_cases=True)
    )

    failed_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "failed-evidence",
        temp_parent=tmp_path / "temp",
    )
    failed_case = begin_retained_case_evidence(evidence_root=failed_root, case_id="GFH-004")
    finalize_retained_case_evidence(
        case=failed_case,
        repo_root=tmp_path / "missing",
        result_payload={"status": "failed", "evidence": {}},
    )
    failed_manifest = write_retained_evidence_manifest(
        root=failed_root,
        expected_case_ids=("GFH-004",),
    )
    assert "is not passed" in " ".join(
        retained_evidence_manifest_issues(failed_manifest, require_passed_cases=True)
    )


def _write(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path
