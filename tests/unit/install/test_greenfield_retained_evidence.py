from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
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
from greenfield_matrix_release_artifacts import retained_evidence_result
from greenfield_matrix_release_artifacts import seal_interrupted_retained_evidence
from greenfield_matrix_release_artifacts import write_retained_evidence_manifest


@pytest.mark.parametrize(
    "tampered_relative",
    (
        "semantic/product-create-transaction.v1.json",
        "retained-navigation.v1.json",
        "generated/odylith/atlas/source/system.svg",
    ),
)
def test_retained_evidence_survives_temp_cleanup_and_detects_tampering(
    tmp_path: Path,
    tampered_relative: str,
) -> None:
    temp_parent = tmp_path / "temp"
    temp_parent.mkdir()
    repo = temp_parent / "sim"
    transaction_hash = "a" * 64
    receipt = _published_case(repo=repo, staged_root=temp_parent / "stage", transaction_hash=transaction_hash)
    write_set_hash = receipt["repository_write_set_hash"]
    _write(
        repo / ".odylith/runtime/greenfield/generations" / transaction_hash / "repository/wrong.txt",
        "obsolete transaction-addressed bytes\n",
    )

    evidence_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=evidence_root, case_id="GFH-001")
    for name in ("propose.stdout", "propose.stderr", "create.stdout", "create.stderr"):
        record_retained_case_text(case, f"commands/{name}", f"{name}\n")
    decide_stdout = (
        b"Published transaction. Open file:///private/tmp/release-proof/odylith/index.html?tab=project\n"
    )
    decide_sha256 = hashlib.sha256(decide_stdout).hexdigest()
    record_retained_case_bytes(case, "commands/decide.stdout", decide_stdout)
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
                "repository_write_set_hash": write_set_hash,
                **receipt,
            },
            "browser_surface_proof": {"required": True, "attempted": True},
        },
    }
    finalize_retained_case_evidence(case=case, repo_root=repo, result_payload=result)
    manifest = write_retained_evidence_manifest(root=evidence_root, expected_case_ids=("GFH-001",))

    shutil.rmtree(temp_parent)
    assert retained_evidence_manifest_issues(manifest, expected_case_ids=("GFH-001",)) == ()
    retained_atlas = evidence_root / "gfh-001/generated/odylith/atlas/source/system.svg"
    assert retained_atlas.read_text(encoding="utf-8") == "<svg></svg>\n"
    retained_navigation = json.loads(
        (evidence_root / "gfh-001/retained-navigation.v1.json").read_text(encoding="utf-8")
    )
    assert retained_navigation["open"] == "generated/odylith/index.html?tab=project"
    assert (evidence_root / "gfh-001" / retained_navigation["entrypoint"]).is_file()
    case_manifest = json.loads(
        (evidence_root / "gfh-001/case-evidence-manifest.v1.json").read_text(encoding="utf-8")
    )
    assert case_manifest["navigation"] == retained_navigation
    assert set(case_manifest["semantic_bindings"]) == {
        "transaction",
        "compiler_receipt",
        "active_generation",
        "generation_manifest",
    }
    top_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert top_manifest["project_navigation"] == [
        {
            "case_id": "GFH-001",
            "entrypoint": "gfh-001/generated/odylith/index.html",
            "route": "?tab=project",
            "open": "gfh-001/generated/odylith/index.html?tab=project",
        }
    ]
    operator_result = retained_evidence_result(manifest, expected_case_ids=("GFH-001",))
    assert operator_result["status"] == "passed"
    project_url = operator_result["project_navigation"][0]["open"]
    assert project_url.endswith(
        "/gfh-001/generated/odylith/index.html?tab=project"
    )
    handoff = operator_result["completion_handoffs"][0]
    assert handoff == {
        "case_id": "GFH-001",
        "transaction_hash": transaction_hash,
        "open": project_url,
        "visible_markdown": f"Published transaction `{transaction_hash}`. Review the committed governance package in the retained [Project dashboard]({project_url}).",
    }
    retained_decide = evidence_root / "gfh-001/commands/decide.stdout"
    assert retained_decide.read_bytes() == decide_stdout
    assert hashlib.sha256(retained_decide.read_bytes()).hexdigest() == decide_sha256
    assert not (evidence_root / "gfh-001/generated/wrong.txt").exists()

    (evidence_root / "gfh-001" / tampered_relative).write_text("tampered\n", encoding="utf-8")
    assert retained_evidence_manifest_issues(manifest)
    failed_result = retained_evidence_result(manifest, expected_case_ids=("GFH-001",))
    assert failed_result["status"] == "failed"
    assert failed_result["completion_handoffs"] == []


@pytest.mark.parametrize(
    "damage",
    (
        "missing-transaction",
        "missing-compiler-receipt",
        "swapped-semantic-files",
        "missing-active-generation",
        "missing-generation-manifest",
    ),
)
def test_passed_compiled_retention_requires_the_exact_semantic_custody_chain(
    tmp_path: Path,
    damage: str,
) -> None:
    temp_parent = tmp_path / "temp"
    repo = temp_parent / "sim"
    transaction_hash = "a" * 64
    receipt = _published_case(
        repo=repo,
        staged_root=temp_parent / "stage",
        transaction_hash=transaction_hash,
    )
    transaction = repo / receipt["transaction_file"]
    compiler_receipt = repo / receipt["compiler_receipt_file"]
    generation_manifest = (
        repo
        / ".odylith/runtime/greenfield/generations"
        / receipt["repository_write_set_hash"]
        / "generation-manifest.v1.json"
    )
    if damage == "missing-transaction":
        transaction.unlink()
    elif damage == "missing-compiler-receipt":
        compiler_receipt.unlink()
    elif damage == "swapped-semantic-files":
        transaction_bytes = transaction.read_bytes()
        transaction.write_bytes(compiler_receipt.read_bytes())
        compiler_receipt.write_bytes(transaction_bytes)
    elif damage == "missing-active-generation":
        (repo / "odylith/index.html").unlink()
    else:
        generation_manifest.unlink()

    evidence_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=evidence_root, case_id="GFH-exact")
    with pytest.raises(RuntimeError, match="passed compiled"):
        finalize_retained_case_evidence(
            case=case,
            repo_root=repo,
            result_payload={
                "status": "passed",
                "evidence": {"preconfirm_dry_run": receipt},
            },
        )


def test_retained_project_route_renders_after_temporary_workspace_deletion(tmp_path: Path) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    temp_parent = tmp_path / "temp"
    repo = temp_parent / "sim"
    receipt = _published_case(
        repo=repo,
        staged_root=temp_parent / "stage",
        transaction_hash="a" * 64,
    )
    evidence_root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "evidence",
        temp_parent=temp_parent,
    )
    case = begin_retained_case_evidence(evidence_root=evidence_root, case_id="GFH-render")
    for name in ("propose.stdout", "create.stdout"):
        record_retained_case_text(case, f"commands/{name}", name)
    record_retained_case_json(case, "semantic/dry-run-receipt.v2.json", receipt)
    record_retained_case_text(case, "browser/project-desktop.png", "png")
    result = {
        "status": "passed",
        "evidence": {
            "preconfirm_dry_run": receipt,
            "browser_surface_proof": {"required": True, "attempted": True},
        },
    }
    finalize_retained_case_evidence(case=case, repo_root=repo, result_payload=result)
    manifest = write_retained_evidence_manifest(
        root=evidence_root,
        expected_case_ids=("GFH-render",),
    )
    shutil.rmtree(temp_parent)
    operator_result = retained_evidence_result(manifest, expected_case_ids=("GFH-render",))
    handoff = operator_result["completion_handoffs"][0]
    assert handoff["transaction_hash"] == "a" * 64
    assert handoff["open"] in handoff["visible_markdown"]

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(handoff["open"])
            assert page.locator("#project").inner_text() == "Project dashboard"
            assert page.url.endswith("/gfh-render/generated/odylith/index.html?tab=project")
        finally:
            browser.close()


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

    linked_temp_parent = tmp_path / "linked-temp"
    linked_temp_parent.symlink_to(temp_parent, target_is_directory=True)
    with pytest.raises(RuntimeError, match="matrix temp parent crosses a symlink"):
        prepare_retained_evidence_output_dir(
            output_dir=tmp_path / "retained-evidence",
            temp_parent=linked_temp_parent,
        )


def test_retained_case_rejects_symlinked_generation_artifact(tmp_path: Path) -> None:
    temp_parent = tmp_path / "temp"
    repo = temp_parent / "sim"
    transaction_hash = "b" * 64
    write_set_hash = "d" * 64
    generation = repo / ".odylith/runtime/greenfield/generations" / write_set_hash
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
                "evidence": {"preconfirm_dry_run": {
                    "transaction_hash": transaction_hash,
                    "repository_write_set_hash": write_set_hash,
                }},
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
    assert retained_evidence_result(failed_manifest)["completion_handoffs"] == []


def _published_case(*, repo: Path, staged_root: Path, transaction_hash: str) -> dict[str, str]:
    _write(staged_root / "odylith/radar/source/ideas/workstream.md", "# Workstream\n")
    _write(staged_root / "odylith/atlas/source/system.mmd", "flowchart LR\nA --- B\n")
    _write(staged_root / "odylith/atlas/source/system.svg", "<svg></svg>\n")
    _write(
        staged_root / "odylith/index.html",
        '<main id="project">Project dashboard</main>\n',
    )
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=repo,
        staged_root=staged_root,
    )
    manifest_text = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo,
        write_set=write_set,
        manifest_text=manifest_text,
    )
    publication_text = greenfield_generation_state.compile_greenfield_publication_entry(
        write_set_hash=generation.write_set_hash,
        generation_manifest_sha256=generation.manifest_sha256,
    )
    _write(repo / "odylith/index.html", publication_text)

    transaction = (
        repo
        / ".odylith/runtime/greenfield/pending"
        / transaction_hash
        / "product-create-transaction.v1.json"
    )
    transaction_bytes = (
        json.dumps({"transaction_hash": transaction_hash}, sort_keys=True) + "\n"
    ).encode("utf-8")
    transaction.parent.mkdir(parents=True, exist_ok=True)
    transaction.write_bytes(transaction_bytes)
    transaction_sha256 = hashlib.sha256(transaction_bytes).hexdigest()
    compiler_receipt = transaction.with_name(transaction.name + ".compiler-receipt.v1.json")
    compiler_bytes = (
        json.dumps(
            {
                "transaction_file_sha256": transaction_sha256,
                "transaction_hash": transaction_hash,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    compiler_receipt.write_bytes(compiler_bytes)
    return {
        "status": "compiled",
        "transaction_hash": transaction_hash,
        "transaction_body_sha256": transaction_hash,
        "transaction_file": transaction.relative_to(repo).as_posix(),
        "transaction_file_sha256": transaction_sha256,
        "compiler_receipt_file": compiler_receipt.relative_to(repo).as_posix(),
        "compiler_receipt_sha256": hashlib.sha256(compiler_bytes).hexdigest(),
        "compiler_receipt_transaction_hash": transaction_hash,
        "repository_write_set_hash": generation.write_set_hash,
        "publication_sha256": hashlib.sha256(publication_text.encode("utf-8")).hexdigest(),
    }


def _write(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path
