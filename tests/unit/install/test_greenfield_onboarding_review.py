from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
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
from greenfield_matrix_release_artifacts import record_retained_case_json
from greenfield_matrix_release_artifacts import record_retained_case_text
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_matrix_release_artifacts import write_retained_evidence_manifest
import greenfield_onboarding_review as onboarding_review
from greenfield_onboarding_review import ONBOARDING_REVIEW_LENSES
from greenfield_onboarding_review import ONBOARDING_REVIEW_PACKAGE_VERSION
from greenfield_onboarding_review import build_onboarding_review_sidecar
from greenfield_onboarding_review import finalize_onboarding_review
from greenfield_final_holdout_guard import FINAL_HOLDOUT_RUN_LEDGER_VERSION
from greenfield_release_qualification import verify_release_qualification
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
)


CASE_ID = "release-review-001"
PROMPT_SHA = "1" * 64
CONFIRMED_INTENT_SHA = "2" * 64
SOURCE_ARTIFACT_SHA = "3" * 64
TRANSACTION_HASH = "4" * 64
IMPLEMENTATION_REVISION = "a" * 40
RUN_ID = "9" * 64


@pytest.fixture
def evidence(tmp_path: Path) -> dict[str, object]:
    temp_parent = tmp_path / "temp"
    repo = temp_parent / "sim"
    receipt = _published_case(
        repo=repo,
        staged_root=temp_parent / "stage",
        transaction_hash=TRANSACTION_HASH,
    )
    root = prepare_retained_evidence_output_dir(
        output_dir=tmp_path / "retained-evidence",
        temp_parent=temp_parent,
    )
    retained_case = begin_retained_case_evidence(evidence_root=root, case_id=CASE_ID)
    record_retained_case_text(retained_case, "commands/propose.stdout", "proposed\n")
    record_retained_case_json(retained_case, "semantic/dry-run-receipt.v2.json", receipt)
    record_retained_case_text(retained_case, "browser/project-desktop.png", "png bytes")
    case_result = {
        "status": "passed",
        "evidence": {
            "preconfirm_dry_run": receipt,
            "browser_surface_proof": {"required": True, "attempted": True},
        },
    }
    case_manifest_path = finalize_retained_case_evidence(
        case=retained_case,
        repo_root=repo,
        result_payload=case_result,
    )
    retained_manifest_path = write_retained_evidence_manifest(
        root=root,
        expected_case_ids=(CASE_ID,),
        run_id=RUN_ID,
    )
    base = _base_result(
        retained_manifest_path=retained_manifest_path,
        transaction_hash=TRANSACTION_HASH,
    )
    base_path = _write_json(tmp_path / "matrix-result.v1.json", base)
    review = _review_package(
        base_path=base_path,
        retained_manifest_path=retained_manifest_path,
        case_manifest_path=case_manifest_path,
    )
    review_path = _write_json(tmp_path / "independent-review-package.v1.json", review)
    return {
        "base": base,
        "base_path": base_path,
        "retained_manifest_path": retained_manifest_path,
        "case_manifest_path": case_manifest_path,
        "review": review,
        "review_path": review_path,
    }


def test_valid_review_finalizes_detached_lens_approvals_without_mutating_inputs(
    evidence: dict[str, object], tmp_path: Path
) -> None:
    base_path = evidence["base_path"]
    retained_path = evidence["retained_manifest_path"]
    review_path = evidence["review_path"]
    assert isinstance(base_path, Path)
    assert isinstance(retained_path, Path)
    assert isinstance(review_path, Path)
    before = {path: path.read_bytes() for path in (base_path, retained_path, review_path)}

    sidecar = finalize_onboarding_review(
        base_result_path=base_path,
        retained_manifest_path=retained_path,
        review_path=review_path,
        output_path=tmp_path / "final-review.json",
    )

    assert sidecar["status"] == "passed"
    assert sidecar["automated_release_gates"] == {"status": "passed", "issues": []}
    assert sidecar["finalized_onboarding_quality_scorecard"]["status"] == "passed"
    assert sidecar["finalized_onboarding_quality_scorecard"]["score"] == 10
    case = sidecar["independent_review"]["cases"][0]
    assert tuple(case["lenses"]) == ONBOARDING_REVIEW_LENSES
    assert all(lens["approved"] and lens["score"] == 10 for lens in case["lenses"].values())
    assert all(path.read_bytes() == value for path, value in before.items())
    with pytest.raises(FileExistsError):
        finalize_onboarding_review(
            base_result_path=base_path,
            retained_manifest_path=retained_path,
            review_path=review_path,
            output_path=tmp_path / "final-review.json",
        )


def test_release_qualification_binds_review_to_terminal_holdout_and_revision(
    evidence: dict[str, object], tmp_path: Path
) -> None:
    sidecar_path, ledger_path, provenance_path = _passing_release_qualification(evidence, tmp_path)

    result = verify_release_qualification(
        sidecar_path=sidecar_path,
        final_holdout_ledger_path=ledger_path,
        distribution_provenance_path=provenance_path,
        implementation_revision=IMPLEMENTATION_REVISION,
    )

    assert result["status"] == "passed"
    assert result["implementation_revision"] == IMPLEMENTATION_REVISION
    assert result["matrix_result_sha256"] == sha256_file(evidence["base_path"])


def test_release_qualification_rejects_stale_reviewed_evidence(
    evidence: dict[str, object], tmp_path: Path
) -> None:
    sidecar_path, ledger_path, provenance_path = _passing_release_qualification(evidence, tmp_path)
    base_path = evidence["base_path"]
    assert isinstance(base_path, Path)
    base_path.write_text(base_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="bytes changed after review"):
        verify_release_qualification(
            sidecar_path=sidecar_path,
            final_holdout_ledger_path=ledger_path,
            distribution_provenance_path=provenance_path,
            implementation_revision=IMPLEMENTATION_REVISION,
        )


def test_release_qualification_rejects_another_commit(
    evidence: dict[str, object], tmp_path: Path
) -> None:
    sidecar_path, ledger_path, provenance_path = _passing_release_qualification(evidence, tmp_path)

    with pytest.raises(RuntimeError, match="different implementation revision"):
        verify_release_qualification(
            sidecar_path=sidecar_path,
            final_holdout_ledger_path=ledger_path,
            distribution_provenance_path=provenance_path,
            implementation_revision="b" * 40,
        )


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        ("run_id", "different run IDs"),
        ("protected_inputs", "lacks protected-input custody"),
        ("provenance_hash", "distribution provenance differ"),
    ],
)
def test_release_qualification_rejects_broken_holdout_custody(
    evidence: dict[str, object],
    tmp_path: Path,
    mutation: str,
    failure: str,
) -> None:
    sidecar_path, ledger_path, provenance_path = _passing_release_qualification(evidence, tmp_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if mutation == "run_id":
        ledger["run_id"] = "8" * 64
    elif mutation == "protected_inputs":
        ledger["protected_inputs"].pop("lower_capability_control")
    else:
        ledger["distribution_provenance_sha256"] = "f" * 64
    _write_json(ledger_path, ledger)

    with pytest.raises(RuntimeError, match=failure):
        verify_release_qualification(
            sidecar_path=sidecar_path,
            final_holdout_ledger_path=ledger_path,
            distribution_provenance_path=provenance_path,
            implementation_revision=IMPLEMENTATION_REVISION,
        )


@pytest.mark.parametrize(
    ("field", "value", "expected_issue"),
    [
        ("semantic_release", {"status": "not_requested", "passed": True}, "semantic_release"),
        ("proof_tier", "discovery", "not terminal release proof"),
    ],
)
def test_independent_review_cannot_promote_nonterminal_matrix_evidence(
    evidence: dict[str, object],
    tmp_path: Path,
    field: str,
    value: object,
    expected_issue: str,
) -> None:
    base = deepcopy(evidence["base"])
    assert isinstance(base, dict)
    if field == "proof_tier":
        base["campaign"]["proof_tier"] = value
    else:
        base[field] = value
    base_path = _write_json(tmp_path / f"nonterminal-{field}.json", base)
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    review["base_result_sha256"] = sha256_file(base_path)

    sidecar = build_onboarding_review_sidecar(
        base_result_path=base_path,
        retained_manifest_path=evidence["retained_manifest_path"],
        review_package=review,
    )

    assert sidecar["status"] == "failed"
    assert expected_issue in " ".join(sidecar["automated_release_gates"]["issues"])


def test_missing_or_partial_review_stays_awaiting_and_unproven(
    evidence: dict[str, object], tmp_path: Path
) -> None:
    base = deepcopy(evidence["base"])
    assert isinstance(base, dict)
    for lens in ONBOARDING_REVIEW_LENSES:
        base["results"][0]["quality"]["scores"][lens] = 10
    base_path = _write_json(tmp_path / "self-asserted-lenses-result.json", base)
    sidecar = build_onboarding_review_sidecar(
        base_result_path=base_path,
        retained_manifest_path=evidence["retained_manifest_path"],
        review_package={"cases": []},
    )

    assert sidecar["status"] == "awaiting_review"
    assert sidecar["independent_review"]["status"] == "awaiting_review"
    assert (
        sidecar["finalized_onboarding_quality_scorecard"]["status"]
        == "awaiting-independent-review"
    )
    assert "independent review is missing committed case" in " ".join(
        sidecar["independent_review"]["awaiting"]
    )
    assert "package version is missing" in " ".join(sidecar["independent_review"]["awaiting"])


def test_valid_detached_review_cannot_erase_an_embedded_failed_lens(
    evidence: dict[str, object], tmp_path: Path
) -> None:
    base = deepcopy(evidence["base"])
    assert isinstance(base, dict)
    base["results"][0]["quality"]["scores"]["product_manager"] = 0
    base_path = _write_json(tmp_path / "failed-embedded-lens-result.json", base)
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    review["base_result_sha256"] = sha256_file(base_path)

    sidecar = build_onboarding_review_sidecar(
        base_result_path=base_path,
        retained_manifest_path=evidence["retained_manifest_path"],
        review_package=review,
    )

    assert sidecar["independent_review"]["status"] == "passed"
    assert sidecar["finalized_onboarding_quality_scorecard"]["status"] == "failed"
    assert sidecar["status"] == "failed"


def test_exclusive_writer_retries_partial_os_writes(
    evidence: dict[str, object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_path = evidence["base_path"]
    retained_path = evidence["retained_manifest_path"]
    review_path = evidence["review_path"]
    assert isinstance(base_path, Path)
    assert isinstance(retained_path, Path)
    assert isinstance(review_path, Path)
    actual_write = onboarding_review.os.write
    write_sizes: list[int] = []

    def short_write(descriptor: int, value: object) -> int:
        chunk = value[:17]
        write_sizes.append(len(chunk))
        return actual_write(descriptor, chunk)

    monkeypatch.setattr(onboarding_review.os, "write", short_write)
    output = tmp_path / "partial-write-sidecar.json"
    sidecar = finalize_onboarding_review(
        base_result_path=base_path,
        retained_manifest_path=retained_path,
        review_path=review_path,
        output_path=output,
    )

    assert len(write_sizes) > 1
    assert json.loads(output.read_text(encoding="utf-8")) == sidecar


def test_finalizer_rejects_output_inside_retained_evidence(
    evidence: dict[str, object],
) -> None:
    retained_path = evidence["retained_manifest_path"]
    assert isinstance(retained_path, Path)
    output = retained_path.parent / "independent-review-sidecar.json"

    with pytest.raises(RuntimeError, match="outside retained evidence"):
        finalize_onboarding_review(
            base_result_path=evidence["base_path"],
            retained_manifest_path=retained_path,
            review_path=evidence["review_path"],
            output_path=output,
        )

    assert not output.exists()


@pytest.mark.parametrize("blocker", ("failed_lens", "open_p0", "open_p1"))
def test_failed_lens_or_open_critical_finding_blocks_release(
    evidence: dict[str, object], blocker: str
) -> None:
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    case = review["cases"][0]
    if blocker == "failed_lens":
        case["lenses"][0]["verdict"] = "failed"
    else:
        case["findings"] = [
            {"severity": blocker.removeprefix("open_").upper(), "status": "open", "summary": "material defect"}
        ]

    sidecar = _build(evidence, review)

    assert sidecar["status"] == "failed"
    assert sidecar["independent_review"]["status"] == "failed"
    if blocker == "failed_lens":
        assert sidecar["finalized_onboarding_quality_scorecard"]["status"] == "failed"


@pytest.mark.parametrize(
    "damage",
    (
        "result_hash",
        "root_manifest_hash",
        "case_manifest_hash",
        "prompt_sha256",
        "confirmed_intent_sha256",
        "source_artifact_sha256",
        "artifact_hash",
        "screenshot_hash",
    ),
)
def test_review_rejects_bad_custody_hashes(
    evidence: dict[str, object], damage: str
) -> None:
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    case = review["cases"][0]
    if damage == "result_hash":
        review["base_result_sha256"] = "9" * 64
    elif damage == "root_manifest_hash":
        review["retained_evidence_manifest_sha256"] = "9" * 64
    elif damage == "case_manifest_hash":
        case["case_manifest_sha256"] = "9" * 64
    elif damage == "artifact_hash":
        case["reviewed"]["artifacts"][0]["sha256"] = "9" * 64
    elif damage == "screenshot_hash":
        case["reviewed"]["screenshots"][0]["sha256"] = "9" * 64
    else:
        case["source"][damage] = "9" * 64

    sidecar = _build(evidence, review)

    assert sidecar["status"] == "failed"
    assert sidecar["independent_review"]["status"] == "failed"


def test_mutated_retained_byte_is_detected_even_when_review_hashes_are_unchanged(
    evidence: dict[str, object]
) -> None:
    case_manifest_path = evidence["case_manifest_path"]
    assert isinstance(case_manifest_path, Path)
    case_manifest = json.loads(case_manifest_path.read_text(encoding="utf-8"))
    screenshot = next(row for row in case_manifest["artifacts"] if row["kind"] == "browser_screenshot")
    (case_manifest_path.parent / screenshot["path"]).write_text("tampered", encoding="utf-8")

    sidecar = _build(evidence, evidence["review"])

    assert sidecar["status"] == "failed"
    assert "retained case evidence hash changed" in " ".join(sidecar["retained_evidence"]["issues"])


@pytest.mark.parametrize("damage", ("duplicate_case", "unknown_case", "duplicate_lens", "unknown_lens"))
def test_review_rejects_duplicate_or_unknown_cases_and_lenses(
    evidence: dict[str, object], damage: str
) -> None:
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    if damage == "duplicate_case":
        review["cases"].append(deepcopy(review["cases"][0]))
    elif damage == "unknown_case":
        unknown = deepcopy(review["cases"][0])
        unknown["case_id"] = "unknown-case"
        review["cases"].append(unknown)
    elif damage == "duplicate_lens":
        review["cases"][0]["lenses"].append(deepcopy(review["cases"][0]["lenses"][0]))
    else:
        review["cases"][0]["lenses"][0]["lens"] = "copy_editor"

    sidecar = _build(evidence, review)

    assert sidecar["status"] == "failed"
    assert sidecar["independent_review"]["status"] == "failed"


@pytest.mark.parametrize("evidence_kind", ("artifacts", "screenshots"))
def test_review_requires_every_relevant_retained_artifact(
    evidence: dict[str, object], evidence_kind: str
) -> None:
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    reviewed = review["cases"][0]["reviewed"][evidence_kind]
    assert reviewed
    reviewed.pop()

    sidecar = _build(evidence, review)

    assert sidecar["status"] == "awaiting_review"
    assert "omits retained paths" in " ".join(sidecar["independent_review"]["awaiting"])


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    (
        ("identity", "exact qualified independent-review fields"),
        ("role", "not an independent release adjudicator"),
        ("qualification", "strong semantic-review qualification"),
        ("model", "supported strong-review model"),
        ("unknown_model", "supported strong-review model"),
        ("model_profile", "independent strong-review profile"),
        ("reasoning_effort", "below the strong-review floor"),
        ("review_context_id", "SHA-256 context identity"),
        ("reused_context_id", "distinct from execution evidence"),
        ("execution_participation", "participated in release execution"),
        ("separate_context", "separate review context"),
        ("evidence_scope", "immutable retained evidence"),
    ),
)
def test_review_requires_bound_strong_independent_reviewer_evidence(
    evidence: dict[str, object], mutation: str, expected_issue: str
) -> None:
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    reviewer = review["reviewer"]
    independence = reviewer["independence"]
    if mutation == "identity":
        reviewer.pop("identity")
    elif mutation == "role":
        reviewer["role"] = "release_executor"
    elif mutation == "qualification":
        reviewer["qualification"] = "routine_validation"
    elif mutation == "model":
        reviewer["model"] = "gpt-6-luna"
    elif mutation == "unknown_model":
        reviewer["model"] = "tiny-unknown-model"
    elif mutation == "model_profile":
        reviewer["model_profile"] = "routine_validation"
    elif mutation == "reasoning_effort":
        reviewer["reasoning_effort"] = "low"
    elif mutation == "review_context_id":
        reviewer["review_context_id"] = "review-context"
    elif mutation == "reused_context_id":
        base_path = evidence["base_path"]
        assert isinstance(base_path, Path)
        reviewer["review_context_id"] = sha256_file(base_path)
    elif mutation == "execution_participation":
        independence["execution_participation"] = "author"
    elif mutation == "separate_context":
        independence["separate_context"] = False
    else:
        independence["evidence_scope"] = "live_worktree"

    sidecar = _build(evidence, review)

    assert sidecar["status"] == "failed"
    assert expected_issue in " ".join(sidecar["independent_review"]["issues"])


@pytest.mark.parametrize(
    ("statistics_status", "statistics_passed"),
    (("failed", False), ("passed", False), ("passed", None)),
)
def test_scorecard_ten_cannot_override_unqualified_campaign_outcome_statistics(
    evidence: dict[str, object],
    tmp_path: Path,
    statistics_status: str,
    statistics_passed: object,
) -> None:
    base = deepcopy(evidence["base"])
    assert isinstance(base, dict)
    base["onboarding_quality_scorecard"] = {"status": "passed", "score": 10}
    base["campaign"]["outcome_statistics"] = {
        "status": statistics_status,
        "passed": statistics_passed,
    }
    base_path = _write_json(tmp_path / "failed-statistics-result.json", base)
    review = deepcopy(evidence["review"])
    assert isinstance(review, dict)
    review["base_result_sha256"] = sha256_file(base_path)

    sidecar = build_onboarding_review_sidecar(
        base_result_path=base_path,
        retained_manifest_path=evidence["retained_manifest_path"],
        review_package=review,
    )

    assert sidecar["independent_review"]["status"] == "passed"
    assert sidecar["finalized_onboarding_quality_scorecard"]["status"] == "passed"
    assert sidecar["finalized_onboarding_quality_scorecard"]["score"] == 10
    assert sidecar["automated_release_gates"]["status"] == "failed"
    assert sidecar["status"] == "failed"
    assert "campaign outcome statistics did not pass" in sidecar["automated_release_gates"]["issues"]


def test_finalizer_has_no_provider_or_matrix_execution_surface() -> None:
    source = (SCRIPTS_ROOT / "greenfield_onboarding_review.py").read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "execute_greenfield" not in source
    assert "codex-cli" not in source
    assert "provider" in source  # The contract is explicitly documented as provider-free.


def _build(evidence: dict[str, object], review: object) -> dict[str, object]:
    return build_onboarding_review_sidecar(
        base_result_path=evidence["base_path"],
        retained_manifest_path=evidence["retained_manifest_path"],
        review_package=review,
    )


def _base_result(*, retained_manifest_path: Path, transaction_hash: str) -> dict[str, object]:
    primary_scores = {
        "completion": 10,
        "semantic_manifest": 10,
        "copy_semantic_clarity": 10,
        "traceability": 10,
        "operator_usefulness": 10,
        "implementation_prompts": 10,
        "confirmation_ux": 10,
        **{lens: -1 for lens in ONBOARDING_REVIEW_LENSES},
    }
    return {
        "version": "greenfield-preconfirm-installed-matrix-v2",
        "status": "awaiting-independent-review",
        "results": [
            {
                "name": "review case",
                "status": "passed",
                "quality": {"passed": True, "scores": primary_scores},
                "evidence": {
                    "case": {
                        "id": CASE_ID,
                        "expectation": "transaction_committed",
                        "prompt_sha256": PROMPT_SHA,
                        "confirmed_intent_sha256": CONFIRMED_INTENT_SHA,
                        "provenance": {"source_artifact_sha256": SOURCE_ARTIFACT_SHA},
                    },
                    "model_profile": {"profile_id": STANDARD_PROFILE_ID},
                },
                "commit_manifest_summary": {
                    "product_create_transaction": {"transaction_hash": transaction_hash}
                },
            }
        ],
        "campaign": {
            "proof_tier": "release",
            "completed_case_count": 1,
            "failed_case_count": 0,
            "failure_clusters": [],
            "outcome_statistics": {"status": "passed", "passed": True},
        },
        "corpus_provenance": {"status": "passed"},
        "browser_surface_proof": {"status": "passed"},
        "platform_domain_leakage_proof": {"status": "passed"},
        "temp_cleanup_proof": {"status": "passed"},
        "model_profile_proof": {
            "status": "passed",
            "profiles": {
                STANDARD_PROFILE_ID: {"status": "passed"},
                RESCUE_PROFILE_ID: {"status": "passed"},
            },
        },
        "lower_capability_control_proof": {
            "status": "passed",
            "results": [
                {
                    "name": "rescue clarification",
                    "status": "passed",
                    "quality": {"passed": True, "scores": {}},
                    "evidence": {
                        "case": {
                            "id": "release-review-rescue-control",
                            "expectation": "clarification_required",
                        },
                        "model_profile": {"profile_id": RESCUE_PROFILE_ID},
                    },
                }
            ],
        },
        "unavailable_provider_proof": {"status": "passed"},
        "semantic_release": {"status": "passed", "passed": True},
        "metamorphic_output": {"status": "passed", "passed": True},
        "commit_recovery_proof": {"status": "passed"},
        "retained_evidence": {
            "status": "passed",
            "manifest": str(retained_manifest_path),
            "manifest_sha256": sha256_file(retained_manifest_path),
        },
        "onboarding_quality_scorecard": {"status": "awaiting-independent-review", "score": 0},
    }


def _review_package(
    *, base_path: Path, retained_manifest_path: Path, case_manifest_path: Path
) -> dict[str, object]:
    case_manifest = json.loads(case_manifest_path.read_text(encoding="utf-8"))
    artifacts = [
        row
        for row in case_manifest["artifacts"]
        if row["kind"] in {
            "generated_artifact",
            "rendered_atlas_asset",
            "retained_navigation",
            "semantic_receipt",
        }
    ]
    screenshots = [
        row
        for row in case_manifest["artifacts"]
        if row["kind"] == "browser_screenshot"
    ]
    return {
        "version": ONBOARDING_REVIEW_PACKAGE_VERSION,
        "base_result_sha256": sha256_file(base_path),
        "retained_evidence_manifest_sha256": sha256_file(retained_manifest_path),
        "reviewer": {
            "identity": "independent-review-agent-001",
            "role": "independent_release_adjudicator",
            "qualification": "strong_semantic_review",
            "reviewer_kind": "host_model",
            "model": "gpt-6-astra",
            "model_profile": "independent_strong_review",
            "reasoning_effort": "xhigh",
            "review_context_id": "8" * 64,
            "context": "independent post-run semantic and UX review",
            "method": "read exact retained source, package artifacts, and rendered screenshot",
            "reviewed_on": "2026-09-27",
            "rationale": "All four role-specific perspectives were applied independently of execution.",
            "independence": {
                "execution_participation": "none",
                "separate_context": True,
                "evidence_scope": "immutable_retained_evidence_only",
            },
        },
        "cases": [
            {
                "case_id": CASE_ID,
                "source": {
                    "prompt_sha256": PROMPT_SHA,
                    "confirmed_intent_sha256": CONFIRMED_INTENT_SHA,
                    "source_artifact_sha256": SOURCE_ARTIFACT_SHA,
                },
                "case_manifest_sha256": sha256_file(case_manifest_path),
                "transaction_hash": TRANSACTION_HASH,
                "reviewed": {
                    "artifacts": [
                        {"path": artifact["path"], "sha256": artifact["sha256"]}
                        for artifact in artifacts
                    ],
                    "screenshots": [
                        {"path": screenshot["path"], "sha256": screenshot["sha256"]}
                        for screenshot in screenshots
                    ],
                },
                "rationale": "The package preserves source intent and presents a coherent first path.",
                "lenses": [
                    {
                        "lens": lens,
                        "verdict": "passed",
                        "rationale": f"The retained package passes the {lens} review obligations.",
                    }
                    for lens in ONBOARDING_REVIEW_LENSES
                ],
                "findings": [],
            }
        ],
    }


def _published_case(*, repo: Path, staged_root: Path, transaction_hash: str) -> dict[str, str]:
    _write(staged_root / "odylith/radar/source/ideas/workstream.md", "# Workstream\n")
    _write(staged_root / "odylith/atlas/source/system.mmd", "flowchart LR\nA --- B\n")
    _write(staged_root / "odylith/atlas/source/system.svg", "<svg></svg>\n")
    _write(staged_root / "odylith/index.html", '<main id="project">Project dashboard</main>\n')
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
    transaction_bytes = (json.dumps({"transaction_hash": transaction_hash}, sort_keys=True) + "\n").encode()
    transaction.parent.mkdir(parents=True, exist_ok=True)
    transaction.write_bytes(transaction_bytes)
    transaction_sha256 = hashlib.sha256(transaction_bytes).hexdigest()
    compiler = transaction.with_name(transaction.name + ".compiler-receipt.v1.json")
    compiler_bytes = (
        json.dumps(
            {
                "transaction_file_sha256": transaction_sha256,
                "transaction_hash": transaction_hash,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    compiler.write_bytes(compiler_bytes)
    return {
        "status": "compiled",
        "transaction_hash": transaction_hash,
        "transaction_body_sha256": transaction_hash,
        "transaction_file": transaction.relative_to(repo).as_posix(),
        "transaction_file_sha256": transaction_sha256,
        "compiler_receipt_file": compiler.relative_to(repo).as_posix(),
        "compiler_receipt_sha256": hashlib.sha256(compiler_bytes).hexdigest(),
        "compiler_receipt_transaction_hash": transaction_hash,
        "repository_write_set_hash": generation.write_set_hash,
        "publication_sha256": hashlib.sha256(publication_text.encode()).hexdigest(),
    }


def _passing_release_qualification(
    evidence: dict[str, object], tmp_path: Path
) -> tuple[Path, Path, Path]:
    base_path = evidence["base_path"]
    retained_path = evidence["retained_manifest_path"]
    review_path = evidence["review_path"]
    assert isinstance(base_path, Path)
    assert isinstance(retained_path, Path)
    assert isinstance(review_path, Path)
    sidecar_path = tmp_path / "onboarding-review-sidecar.v2.json"
    finalize_onboarding_review(
        base_result_path=base_path,
        retained_manifest_path=retained_path,
        review_path=review_path,
        output_path=sidecar_path,
    )
    provenance_path = _write_json(
        tmp_path / "build-provenance.v1.json",
        {
            "version": "odylith-release-provenance.v1",
            "source_tree": {"head": IMPLEMENTATION_REVISION, "dirty": False},
            "workflow": {"sha": IMPLEMENTATION_REVISION},
        },
    )
    ledger_path = _write_json(
        tmp_path / "final-holdout-ledger.v3.json",
        {
            "version": FINAL_HOLDOUT_RUN_LEDGER_VERSION,
            "status": "passed",
            "disclosed": True,
            "protected_inputs_bound": True,
            "protected_inputs": {
                "final_holdout": {"filename": "holdout.json", "sha256": "e" * 64},
                "evaluation_manifest": {"filename": "splits.json", "sha256": "e" * 64},
                "case_file_001": {"filename": "cases.json", "sha256": "e" * 64},
                "lower_capability_control": {"filename": "control.json", "sha256": "e" * 64},
            },
            "run_id": RUN_ID,
            "implementation_revision": IMPLEMENTATION_REVISION,
            "distribution_provenance_sha256": sha256_file(provenance_path),
            "result_sha256": sha256_file(base_path),
            "retained_evidence": {
                "manifest_path": str(retained_path.resolve()),
                "manifest_sha256": sha256_file(retained_path),
            },
        },
    )
    return sidecar_path, ledger_path, provenance_path


def _write(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path


def _write_json(path: Path, payload: object) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
