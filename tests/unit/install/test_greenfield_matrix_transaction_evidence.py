from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_lifecycle
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_matrix_transaction_evidence as evidence_module
from greenfield_matrix_transaction_evidence import commit_precompiled_transaction
from greenfield_matrix_transaction_evidence import confirmation_preview_issues
from greenfield_matrix_transaction_evidence import dry_run_commit_issues
from greenfield_matrix_transaction_evidence import post_confirm_navigation_issues


HASH = "a" * 64
PRODUCT_FACTS_SHA256 = "c" * 64
ATOMIC_CUSTODY_SHA256 = "d" * 64
TRANSACTION_FILE = f".odylith/runtime/greenfield/pending/{HASH}/product-create-transaction.v1.json"


def test_commit_precompiled_transaction_validates_receipt_before_invoking_create(tmp_path: Path) -> None:
    _transaction_path, transaction_hash = _write_transaction(tmp_path)
    calls: list[tuple[str, ...]] = []
    proposed = _proposal(transaction_hash)

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=proposed,
        proposal_seconds=12.5,
        invoke_create=lambda command: calls.append(tuple(command))
        or SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )

    assert execution.dry_run_receipt["status"] == "compiled"
    assert execution.dry_run_receipt["transaction_hash"] == transaction_hash
    assert execution.dry_run_receipt["semantic_snapshot"]["facts"]["first_path"] == (
        "An operator records one decision and reviews the accepted receipt."
    )
    assert execution.dry_run_receipt["semantic_snapshot"]["atomic_facts"][0]["normalized_value"] == "Operator"
    assert execution.dry_run_receipt["semantic_snapshot"]["atomic_custody_sha256"] == ATOMIC_CUSTODY_SHA256
    assert execution.dry_run_receipt["product_facts_sha256"] == PRODUCT_FACTS_SHA256
    assert execution.dry_run_receipt["atomic_custody_sha256"] == ATOMIC_CUSTODY_SHA256
    assert execution.dry_run_receipt["transaction_body_sha256"] == transaction_hash
    assert len(execution.dry_run_receipt["transaction_file_sha256"]) == 64
    assert len(execution.dry_run_receipt["compiler_receipt_sha256"]) == 64
    assert len(execution.dry_run_receipt["repository_write_set_hash"]) == 64
    assert set(execution.dry_run_receipt["managed_after_fingerprints"]) == set(
        greenfield_repository_write_set.GREENFIELD_REPOSITORY_WRITE_PATHS
    )
    assert len(execution.dry_run_receipt["semantic_snapshot_sha256"]) == 64
    assert calls and calls[0][1:3] == ("greenfield", "create")


def test_commit_precompiled_transaction_carries_the_exact_sealed_operating_envelope(
    tmp_path: Path,
) -> None:
    sealed = {
        "version": "odylith.greenfield-operating-envelope.synthetic",
        "complexity": {"band": "moderate", "dimensions": {"evidence_bytes": 413}},
        "evidence_format": "operator_prompt",
        "model_contract": {"observed": {"profile_id": "synthetic-profile"}},
    }
    _transaction_path, transaction_hash = _write_transaction(
        tmp_path,
        operating_envelope=sealed,
    )

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        proposal_seconds=1.0,
        invoke_create=lambda _command: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )

    assert execution.dry_run_receipt["semantic_snapshot"]["operating_envelope"] == sealed


def test_preconfirm_snapshot_carries_sealed_authored_semantics_without_reconstruction(
    tmp_path: Path,
) -> None:
    sealed = {
        "version": "odylith.greenfield.authored-semantics.synthetic",
        "first_path_relations": [
            {
                "order": 1,
                "actor": {"kind": "human", "selected_fact_path": "/human_actors/0"},
                "literal_evidence": ["Operator", "accepted receipt"],
            }
        ],
        "first_path_context_relations": [],
        "component_responsibility_relations": [
            {"owner_system_path": "/title", "exact_value": "Decision Workspace"}
        ],
    }
    transaction_path, transaction_hash = _write_transaction(
        tmp_path,
        authored_semantics=sealed,
        authored_relation_set_sha256="e" * 64,
    )
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    sealed_mapping = transaction["proposal"]["intent"]["authored_semantics"]

    direct_snapshot = evidence_module._semantic_snapshot(transaction)
    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        proposal_seconds=1.0,
        invoke_create=lambda _command: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )
    receipt_snapshot = execution.dry_run_receipt["semantic_snapshot"]

    assert direct_snapshot["authored_semantics"] == sealed_mapping
    assert direct_snapshot["authored_semantics"] is not sealed_mapping
    assert receipt_snapshot["authored_semantics"] == sealed_mapping
    assert receipt_snapshot["authored_relation_set_sha256"] == "e" * 64
    assert json.dumps(
        receipt_snapshot["authored_semantics"],
        ensure_ascii=True,
        separators=(",", ":"),
    ) == json.dumps(sealed_mapping, ensure_ascii=True, separators=(",", ":"))
    direct_snapshot["authored_semantics"]["first_path_relations"][0]["order"] = 2
    assert sealed_mapping["first_path_relations"][0]["order"] == 1


def test_preconfirm_snapshot_preserves_absent_authored_semantics_as_absent(
    tmp_path: Path,
) -> None:
    transaction_path, transaction_hash = _write_transaction(tmp_path)
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))

    direct_snapshot = evidence_module._semantic_snapshot(transaction)
    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        proposal_seconds=1.0,
        invoke_create=lambda _command: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )

    assert direct_snapshot["authored_semantics"] is None
    assert direct_snapshot["authored_relation_set_sha256"] is None
    assert execution.dry_run_receipt["semantic_snapshot"]["authored_semantics"] is None
    assert execution.dry_run_receipt["semantic_snapshot"]["authored_relation_set_sha256"] is None


def test_commit_precompiled_transaction_rejects_mismatched_receipt_without_create(tmp_path: Path) -> None:
    _transaction_path, transaction_hash = _write_transaction(tmp_path, receipt_hash="b" * 64)
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        proposal_seconds=12.5,
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
        proposal_seconds=12.5,
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
        proposal_seconds=12.5,
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
        proposal_seconds=12.5,
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
        proposal_seconds=12.5,
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert "transaction body does not match" in execution.create.stdout
    assert not calls


def test_commit_precompiled_transaction_rejects_changed_transaction_bytes(tmp_path: Path) -> None:
    transaction_path, transaction_hash = _write_transaction(tmp_path)
    transaction_path.write_bytes(transaction_path.read_bytes() + b"\n")
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        proposal_seconds=12.5,
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert "compiler receipt file digest does not match" in execution.create.stdout
    assert not calls


@pytest.mark.parametrize(
    ("identity", "expected_issue"),
    (
        ("product_facts", "missing a valid product facts hash"),
        ("atomic_custody", "missing a valid atomic custody hash"),
        ("write_set", "missing a valid repository write-set hash"),
        ("managed_after_state", "missing exact managed after-state fingerprints"),
    ),
)
def test_commit_precompiled_transaction_requires_every_sealed_identity(
    tmp_path: Path,
    identity: str,
    expected_issue: str,
) -> None:
    transaction_path, _transaction_hash = _write_transaction(tmp_path)
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    if identity == "product_facts":
        transaction["intent_authority"]["product_facts_sha256"] = ""
        transaction["commit_summary"]["product_facts_sha256"] = ""
    elif identity == "atomic_custody":
        transaction["intent_authority"]["atomic_custody_sha256"] = ""
    elif identity == "write_set":
        transaction["prewrite_package"]["repository_write_set"]["write_set_hash"] = ""
        transaction["commit_summary"]["repository_write_set_hash"] = ""
    else:
        first_path = greenfield_repository_write_set.GREENFIELD_REPOSITORY_WRITE_PATHS[0]
        transaction["prewrite_package"]["repository_write_set"]["after_fingerprints"].pop(first_path)
    transaction_hash = _seal_transaction(transaction_path, transaction)
    calls: list[tuple[str, ...]] = []

    execution = commit_precompiled_transaction(
        repo_root=tmp_path,
        proposed=_proposal(transaction_hash),
        proposal_seconds=12.5,
        invoke_create=lambda command: calls.append(tuple(command)),
    )

    assert execution.create.returncode == 2
    assert expected_issue in execution.create.stdout
    assert not calls


def test_dry_run_commit_issues_accepts_exact_closed_active_generation(tmp_path: Path) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=str(receipt["transaction_hash"]),
        write_set=write_set,
    )

    assert dry_run_commit_issues(
        receipt=receipt,
        create_payload=_create_payload(receipt),
        repo_root=tmp_path,
    ) == ()


@pytest.mark.parametrize(
    ("path_key", "expected_issue"),
    (
        ("transaction_file", "post-confirm transaction bytes do not match the pre-confirm receipt"),
        ("compiler_receipt_file", "post-confirm compiler receipt bytes do not match the pre-confirm receipt"),
    ),
)
def test_dry_run_commit_issues_rejects_changed_sealed_files(
    tmp_path: Path,
    path_key: str,
    expected_issue: str,
) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=str(receipt["transaction_hash"]),
        write_set=write_set,
    )
    target = tmp_path / str(receipt[path_key])
    target.write_bytes(target.read_bytes() + b"\n")

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=_create_payload(receipt),
        repo_root=tmp_path,
    )

    assert issues == (expected_issue,)


@pytest.mark.parametrize(
    ("identity", "expected_issue"),
    (
        ("transaction", "commit readback does not match the pre-confirm transaction hash"),
        ("product_facts", "commit readback does not match the pre-confirm product facts hash"),
        ("write_set", "commit readback does not match the pre-confirm repository write-set hash"),
    ),
)
def test_dry_run_commit_issues_rejects_changed_commit_identity(
    tmp_path: Path,
    identity: str,
    expected_issue: str,
) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=str(receipt["transaction_hash"]),
        write_set=write_set,
    )
    payload = _create_payload(receipt)
    if identity == "transaction":
        payload["commit_manifest"]["write_transaction"]["product_create_transaction_hash"] = "b" * 64
    elif identity == "product_facts":
        payload["product_create_transaction"]["product_facts_sha256"] = "b" * 64
    else:
        payload["repository_write_set"]["write_set_hash"] = "b" * 64

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=payload,
        repo_root=tmp_path,
    )

    assert issues == (expected_issue,)


@pytest.mark.parametrize(
    ("field", "value", "expected_issue"),
    (
        ("lifecycle_version", "unsupported", "commit readback does not expose the supported create lifecycle"),
        ("lifecycle_state", "PUBLISHED", "commit readback lifecycle is not CLOSED"),
    ),
)
def test_dry_run_commit_issues_requires_closed_lifecycle(
    tmp_path: Path,
    field: str,
    value: str,
    expected_issue: str,
) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=str(receipt["transaction_hash"]),
        write_set=write_set,
    )
    payload = _create_payload(receipt)
    payload["commit_manifest"]["write_transaction"][field] = value

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=payload,
        repo_root=tmp_path,
    )

    assert issues == (expected_issue,)


def test_dry_run_commit_issues_rejects_changed_generation_manifest(tmp_path: Path) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    transaction_hash = str(receipt["transaction_hash"])
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=transaction_hash,
        write_set=write_set,
    )
    manifest_path = (
        tmp_path
        / ".odylith/runtime/greenfield/generations"
        / transaction_hash
        / "generation-manifest.v1.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_path = greenfield_repository_write_set.GREENFIELD_REPOSITORY_WRITE_PATHS[0]
    manifest["after_fingerprints"][first_path] = "b" * 64
    manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=_create_payload(receipt),
        repo_root=tmp_path,
    )

    assert "active generation identity does not match the sealed transaction" in issues
    assert "immutable generation manifest does not match the sealed managed after-state" in issues


def test_dry_run_commit_issues_rejects_changed_active_generation_identity(tmp_path: Path) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    transaction_hash = str(receipt["transaction_hash"])
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=transaction_hash,
        write_set=write_set,
    )
    state_path = greenfield_generation_state.active_generation_state_path(tmp_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["write_set_hash"] = "b" * 64
    state.pop("record_hash")
    state["record_hash"] = _record_hash(state)
    state_path.write_text(_canonical_json(state), encoding="utf-8")

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=_create_payload(receipt),
        repo_root=tmp_path,
    )

    assert issues == ("active generation identity does not match the sealed transaction",)


def test_dry_run_commit_issues_rejects_changed_managed_repository_state(tmp_path: Path) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=str(receipt["transaction_hash"]),
        write_set=write_set,
    )
    (tmp_path / "odylith/index.html").write_text("changed after confirmation", encoding="utf-8")

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=_create_payload(receipt),
        repo_root=tmp_path,
    )

    assert issues == ("managed repository readback does not match the sealed after-state",)


def test_dry_run_commit_issues_rejects_changed_generation_repository_state(tmp_path: Path) -> None:
    receipt, write_set = _compiled_receipt(tmp_path)
    transaction_hash = str(receipt["transaction_hash"])
    _publish_committed_generation(
        repo_root=tmp_path,
        transaction_hash=transaction_hash,
        write_set=write_set,
    )
    generation_index = (
        tmp_path
        / ".odylith/runtime/greenfield/generations"
        / transaction_hash
        / "repository/odylith/index.html"
    )
    generation_index.write_text("changed immutable generation", encoding="utf-8")

    issues = dry_run_commit_issues(
        receipt=receipt,
        create_payload=_create_payload(receipt),
        repo_root=tmp_path,
    )

    assert issues == ("immutable generation repository does not match the sealed managed after-state",)


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
    operating_envelope: dict[str, object] | None = None,
    authored_semantics: dict[str, object] | None = None,
    authored_relation_set_sha256: str = "",
) -> tuple[Path, str]:
    path = repo_root / TRANSACTION_FILE
    staged_root = repo_root / ".transaction-stage"
    staged_index = staged_root / "odylith/index.html"
    staged_index.parent.mkdir(parents=True, exist_ok=True)
    staged_index.write_text("<html><body>Decision Workspace</body></html>\n", encoding="utf-8")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=repo_root,
        staged_root=staged_root,
    )
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
                **(
                    {"authored_semantics": authored_semantics}
                    if authored_semantics is not None
                    else {}
                ),
            }
        },
        "intent_authority": {
            "product_facts_sha256": PRODUCT_FACTS_SHA256,
            "atomic_custody_sha256": ATOMIC_CUSTODY_SHA256,
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
            **(
                {"authored_relation_set_sha256": authored_relation_set_sha256}
                if authored_relation_set_sha256
                else {}
            ),
            **(
                {"operating_envelope": operating_envelope}
                if operating_envelope is not None
                else {}
            ),
        },
        "prewrite_package": {"repository_write_set": write_set},
        "commit_summary": {
            "product_facts_sha256": PRODUCT_FACTS_SHA256,
            "repository_write_set_hash": write_set["write_set_hash"],
        },
    }
    transaction_hash = _seal_transaction(path, transaction, receipt_hash=receipt_hash)
    return path, transaction_hash


def _seal_transaction(
    path: Path,
    transaction: dict[str, object],
    *,
    receipt_hash: str | None = None,
) -> str:
    transaction.pop("transaction_hash", None)
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
    return transaction_hash


def _compiled_receipt(repo_root: Path) -> tuple[dict[str, object], dict[str, object]]:
    transaction_path, transaction_hash = _write_transaction(repo_root)
    execution = commit_precompiled_transaction(
        repo_root=repo_root,
        proposed=_proposal(transaction_hash),
        proposal_seconds=12.5,
        invoke_create=lambda _command: SimpleNamespace(returncode=0, stdout="{}", stderr=""),
    )
    assert execution.dry_run_receipt["status"] == "compiled"
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    return (
        dict(execution.dry_run_receipt),
        dict(transaction["prewrite_package"]["repository_write_set"]),
    )


def _publish_committed_generation(
    *,
    repo_root: Path,
    transaction_hash: str,
    write_set: dict[str, object],
) -> None:
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=repo_root,
        transaction_hash=transaction_hash,
        write_set=write_set,
    )
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=repo_root,
        write_set=write_set,
    )
    greenfield_generation_store.publish_greenfield_generation(
        repo_root=repo_root,
        generation=generation,
        expected_active_identity=write_set["active_generation_precondition"],
    )


def _create_payload(receipt: dict[str, object]) -> dict[str, object]:
    transaction_hash = str(receipt["transaction_hash"])
    product_facts_hash = str(receipt["product_facts_sha256"])
    write_set_hash = str(receipt["repository_write_set_hash"])
    transaction = {
        "transaction_hash": transaction_hash,
        "product_facts_sha256": product_facts_hash,
        "repository_write_set_hash": write_set_hash,
    }
    return {
        "product_create_transaction": dict(transaction),
        "repository_write_set": {"write_set_hash": write_set_hash},
        "commit_manifest": {
            "product_create_transaction": dict(transaction),
            "write_transaction": {
                "product_create_transaction_hash": transaction_hash,
                "product_facts_sha256": product_facts_hash,
                "repository_write_set_hash": write_set_hash,
                "lifecycle_version": greenfield_create_lifecycle.CREATE_LIFECYCLE_VERSION,
                "lifecycle_state": greenfield_create_lifecycle.CLOSED,
            },
        },
    }


def _canonical_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _record_hash(state: dict[str, object]) -> str:
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
