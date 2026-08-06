from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_transaction_evidence import commit_precompiled_transaction
from greenfield_matrix_transaction_evidence import confirmation_preview_issues
from greenfield_matrix_transaction_evidence import dry_run_commit_issues
from greenfield_matrix_transaction_evidence import post_confirm_navigation_issues


HASH = "a" * 64
TRANSACTION_FILE = f".odylith/runtime/greenfield/pending/{HASH}/product-create-transaction.v1.json"


def test_commit_precompiled_transaction_validates_receipt_before_invoking_create(tmp_path: Path) -> None:
    _transaction_path, transaction_hash = _write_transaction(tmp_path)
    calls: list[tuple[str, ...]] = []
    proposed = _proposal(transaction_hash)

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=proposed,
        invoke_create=lambda command: calls.append(tuple(command))
        or SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )

    assert execution.dry_run_receipt["status"] == "compiled"
    assert execution.dry_run_receipt["transaction_hash"] == transaction_hash
    assert execution.dry_run_receipt["semantic_snapshot"]["facts"]["first_path"] == (
        "An operator records one decision and reviews the accepted receipt."
    )
    assert execution.dry_run_receipt["semantic_snapshot"]["atomic_facts"][0]["normalized_value"] == "Operator"
    assert execution.dry_run_receipt["semantic_snapshot"]["atomic_custody_sha256"] == "d" * 64
    assert len(execution.dry_run_receipt["semantic_snapshot_sha256"]) == 64
    assert calls and calls[0][1:3] == ("greenfield", "create")


def test_commit_precompiled_transaction_rejects_mismatched_receipt_without_create(tmp_path: Path) -> None:
    _transaction_path, transaction_hash = _write_transaction(tmp_path, receipt_hash="b" * 64)
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert "compiler receipt hash does not match" in execution.create.stdout
    assert not calls


def test_commit_precompiled_transaction_does_not_invoke_create_for_material_clarification(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"mode": "clarification_required"}),
            stderr="",
        ),
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert execution.dry_run_receipt["status"] == "clarification_required"
    assert not calls


def test_commit_precompiled_transaction_does_not_invoke_create_for_path_escape(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(HASH, transaction_file="../escape.json"),
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert "path escapes" in execution.create.stdout
    assert not calls


@pytest.mark.parametrize("missing", ("transaction", "receipt"))
def test_commit_precompiled_transaction_does_not_invoke_create_without_compiled_files(
    tmp_path: Path,
    missing: str,
) -> None:
    transaction_path, transaction_hash = _write_transaction(tmp_path)
    target = transaction_path if missing == "transaction" else transaction_path.with_name(
        transaction_path.name + ".compiler-receipt.v1.json"
    )
    target.unlink()
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert "receipt is unavailable" in execution.create.stdout
    assert not calls


def test_commit_precompiled_transaction_rejects_tampered_body_with_matching_local_receipt(tmp_path: Path) -> None:
    transaction_path, transaction_hash = _write_transaction(tmp_path)
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    transaction["proposal"]["intent"]["first_path"] = "A forged path replaces the compiled path."
    encoded = json.dumps(transaction, sort_keys=True).encode("utf-8")
    transaction_path.write_bytes(encoded)
    receipt_path = transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json")
    receipt_path.write_text(
        json.dumps(
            {
                "transaction_hash": transaction_hash,
                "transaction_file_sha256": hashlib.sha256(encoded).hexdigest(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert "transaction body does not match" in execution.create.stdout
    assert not calls


def test_dry_run_commit_issues_detects_changed_commit_hash() -> None:
    receipt = {"status": "compiled", "transaction_hash": HASH}
    payload = {
        "commit_manifest": {
            "write_transaction": {"product_create_transaction_hash": "b" * 64},
            "product_create_transaction": {"transaction_hash": HASH},
        }
    }

    assert dry_run_commit_issues(receipt=receipt, create_payload=payload) == (
        "commit readback does not match the pre-confirm transaction hash",
    )


def test_confirmation_preview_requires_the_hash_bound_decision_rail() -> None:
    payload = _proposal_payload(HASH)

    assert confirmation_preview_issues(proposal_payload=payload) == ()

    payload["confirmation"]["choices"][1]["description"] = "Change it later."

    assert confirmation_preview_issues(proposal_payload=payload) == (
        "EDIT does not explain that corrections are rebuilt as new evidence",
    )


def test_post_confirm_navigation_requires_the_reviewed_generation_workspace(tmp_path: Path) -> None:
    dashboard = (
        tmp_path
        / ".odylith/runtime/greenfield/generations"
        / HASH
        / "repository/odylith/index.html"
    ).resolve()
    dashboard.parent.mkdir(parents=True)
    dashboard.write_text("<html></html>", encoding="utf-8")
    compatibility_dashboard = (tmp_path / "odylith/index.html").resolve()
    compatibility_dashboard.parent.mkdir(parents=True)
    compatibility_dashboard.write_text("<html></html>", encoding="utf-8")
    payload = {
        "post_confirm_navigation": {
            "project": "odylith/index.html?tab=project",
            "radar": "odylith/index.html?tab=radar",
            "registry": "odylith/index.html?tab=registry",
            "atlas": "odylith/index.html?tab=atlas",
            "compass": "odylith/index.html?tab=compass&date=live",
            "dashboard_path": str(dashboard),
            "project_url": f"{dashboard.as_uri()}?tab=project",
            "view_status": "reviewed_generation",
            "compatibility_dashboard_path": str(compatibility_dashboard),
            "generation_transaction_hash": HASH,
        }
    }

    assert post_confirm_navigation_issues(
        create_payload=payload,
        repo_root=tmp_path,
        transaction_hash=HASH,
    ) == ()

    payload["post_confirm_navigation"]["project_url"] = "file:///wrong/index.html?tab=project"

    assert post_confirm_navigation_issues(
        create_payload=payload,
        repo_root=tmp_path,
        transaction_hash=HASH,
    ) == (
        "post-confirm response does not expose the reviewed generation workspace routes: project_url",
    )


def _proposal(transaction_hash: str, *, transaction_file: str = TRANSACTION_FILE) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=0,
        stdout=json.dumps(
            {
                "mode": "product_create_transaction",
                "transaction_file": transaction_file,
                "product_create_transaction": {"transaction_hash": transaction_hash},
            }
        ),
        stderr="",
    )


def _proposal_payload(transaction_hash: str) -> dict[str, object]:
    return {
        "mode": "product_create_transaction",
        "transaction_file": TRANSACTION_FILE,
        "product_create_transaction": {"transaction_hash": transaction_hash},
        "confirmation": {
            "command_rule": "Use exactly one hash-bound command: CONFIRM, EDIT, or REJECT.",
            "post_confirm_contract": (
                "CONFIRM commits only this hash-bound transaction; commit-only create verifies the hash, "
                "compiler receipt, and repo preconditions, writes only sealed bytes under the rollback "
                "guard, validates readback, and reports success or environment/IO failure."
            ),
            "choices": [
                {
                    "command": f"CONFIRM {transaction_hash}",
                    "description": "Commit this exact validated package now.",
                    "commit_command": (
                        "odylith greenfield create --repo-root . "
                        f"--transaction-file {TRANSACTION_FILE} --transaction-hash {transaction_hash} --confirm"
                    ),
                },
                {
                    "command": f"EDIT {transaction_hash} <corrections>",
                    "description": "Do not commit. Treat corrections as new evidence and rebuild the package.",
                },
                {
                    "command": f"REJECT {transaction_hash}",
                    "description": "Stop. No governed records are written.",
                },
            ],
        },
    }


def _write_transaction(
    repo_root: Path,
    *,
    receipt_hash: str | None = None,
) -> tuple[Path, str]:
    path = repo_root / TRANSACTION_FILE
    transaction = {
        "quality_manifest": {"status": "passed", "validation_status": "passed"},
        "proposal": {
            "intent": {
                "product_story": "Decision Workspace helps an operator review one governed outcome.",
                "state_object": "A decision record tracks its evidence, status, and accepted receipt.",
                "first_path": "An operator records one decision and reviews the accepted receipt.",
                "proof_boundary": "The first release proves one accepted decision with readback.",
                "human_actors": ["Operator: records and reviews the decision."],
                "external_systems": [],
            }
        },
        "intent_authority": {
            "product_facts_sha256": "c" * 64,
            "atomic_custody_sha256": "d" * 64,
            "atomic_facts": [
                {
                    "atom_id": "AF-operator",
                    "categories": ["actors"],
                    "normalized_value": "Operator",
                    "polarity": "affirmed",
                    "custody_state": "accepted_fact",
                    "entailment_relationship": "ordered_source_entailment",
                    "source_span_ids": ["human_actors:1"],
                    "source_span_refs": [],
                    "projection_links": [
                        {
                            "field": "human_actors",
                            "path": "/human_actors/0",
                            "value_sha256": "e" * 64,
                        }
                    ],
                }
            ],
            "material_fields": {
                "first_path": {
                    "custody_state": "accepted_fact",
                    "entailment_relationship": "direct_product_claim",
                }
            },
        },
    }
    transaction_hash = hashlib.sha256(
        json.dumps(transaction, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    ).hexdigest()
    transaction["transaction_hash"] = transaction_hash
    encoded = json.dumps(transaction, sort_keys=True).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    path.with_name(path.name + ".compiler-receipt.v1.json").write_text(
        json.dumps(
            {
                "transaction_hash": receipt_hash or transaction_hash,
                "transaction_file_sha256": hashlib.sha256(encoded).hexdigest(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path, transaction_hash
