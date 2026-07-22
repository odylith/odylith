from __future__ import annotations

from dataclasses import replace
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_campaign import MatrixCampaignConfig
from greenfield_matrix_campaign import campaign_summary
from greenfield_matrix_clarification import FOCUSED_FIRST_PATH_QUESTION
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs
from greenfield_matrix_types import GreenfieldArtifactCounts
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_types import GreenfieldQualityVerdict
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_evidence


HASH = "c" * 64
SOURCE_HASH = "d" * 64


def test_metamorphic_output_requires_same_sealed_commit_behavior() -> None:
    cases = _cases()

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=tuple(_result(case) for case in cases))

    assert evaluation["status"] == "passed"
    assert evaluation["complete_group_count"] == 1


def test_metamorphic_output_rejects_changed_readback_hash() -> None:
    cases = _cases()
    results = (_result(cases[0]), _result(cases[1], committed_hash="e" * 64))

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=results)

    assert evaluation["status"] == "failed"
    assert "changed the sealed transaction hash" in evaluation["issues"][0]


def test_metamorphic_output_accepts_required_clarification_without_a_transaction() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(_result(committed_case), _clarification_result(clarification_case)),
    )

    assert evaluation["status"] == "passed"
    assert evaluation["complete_group_count"] == 1


def test_metamorphic_output_rejects_clarification_that_stages_a_transaction() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, staged_transaction_present=True),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("staged a transaction before clarification" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_noncanonical_clarification() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, question="Choose the first task", required_fields=("target_user",)),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("did not ask the focused first-path question" in issue for issue in evaluation["issues"])
    assert any("did not require only first_path" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_with_changed_record_count() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, after_record_count=136),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("did not prove unchanged governed record counts" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_with_write_artifacts() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(
                clarification_case,
                changed_records=("odylith/radar/source/workstreams.v1.json",),
                preconfirm_dry_run=True,
                commit_manifest=True,
            ),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("changed governed records before clarification" in issue for issue in evaluation["issues"])
    assert any("created a dry-run receipt before clarification" in issue for issue in evaluation["issues"])
    assert any("produced a commit manifest before clarification" in issue for issue in evaluation["issues"])


def test_metamorphic_output_rejects_clarification_without_installed_write_audit() -> None:
    committed_case, clarification_case = _clarification_pair_cases()

    evaluation = evaluate_metamorphic_outputs(
        cases=(committed_case, clarification_case),
        results=(
            _result(committed_case),
            _clarification_result(clarification_case, write_audit_active=False, write_audit_error="trace unavailable"),
        ),
    )

    assert evaluation["status"] == "failed"
    assert any("did not activate the installed write audit" in issue for issue in evaluation["issues"])
    assert any("hit an installed write-audit error" in issue for issue in evaluation["issues"])


def test_metamorphic_output_is_pending_until_all_declared_variants_finish() -> None:
    cases = _cases()

    evaluation = evaluate_metamorphic_outputs(cases=cases, results=(_result(cases[0]),))

    assert evaluation["status"] == "pending"
    assert evaluation["pending_groups"] == ["source-001"]


def test_metamorphic_output_skips_single_member_group_after_filtered_replay() -> None:
    case = _cases()[0]

    evaluation = evaluate_metamorphic_outputs(cases=(case,), results=(_result(case),))

    assert evaluation["status"] == "passed"
    assert evaluation["skipped_groups"] == ["source-001"]
    assert evaluation["complete_group_count"] == 0


def test_campaign_summary_exposes_metamorphic_commit_hash_failure() -> None:
    cases = _cases()

    summary = campaign_summary(
        cases=cases,
        results=(_result(cases[0]), _result(cases[1], committed_hash="e" * 64)),
        config=MatrixCampaignConfig(proof_tier="release"),
        stopped_reason="",
    )

    assert summary["metamorphic_output"]["status"] == "failed"
    assert "changed the sealed transaction hash" in summary["metamorphic_output"]["issues"][0]


def _cases() -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    provenance = GreenfieldCaseProvenance(source_id="source-001", source_artifact_sha256=SOURCE_HASH)
    return (
        GreenfieldMatrixCase(
            case_id="source-001-description",
            name="description variant",
            prompt="Create an evidence workspace.",
            required_terms=("evidence",),
            provenance=provenance,
            metamorphic_group="source-001",
            metamorphic_transform="description_evidence",
        ),
        GreenfieldMatrixCase(
            case_id="source-001-topic",
            name="topic variant",
            prompt="Create an evidence workspace from a topic.",
            required_terms=("evidence",),
            provenance=provenance,
            metamorphic_group="source-001",
            metamorphic_transform="topic_evidence",
        ),
    )


def _clarification_pair_cases() -> tuple[GreenfieldMatrixCase, GreenfieldMatrixCase]:
    committed_case, topic_case = _cases()
    return committed_case, replace(topic_case, expectation="clarification_required")


def _result(case: GreenfieldMatrixCase, *, committed_hash: str = HASH) -> GreenfieldMatrixResult:
    summary = {
        "write_transaction": {
            "commit_only": True,
            "prewrite_clean_before_commit": True,
            "product_create_transaction_hash": committed_hash,
        },
        "product_create_transaction": {"transaction_hash": committed_hash},
    }
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        commit_manifest_summary=summary,
        evidence={
            "case": case_evidence(case),
            "preconfirm_dry_run": {"status": "compiled", "transaction_hash": HASH},
        },
    )


def _clarification_result(
    case: GreenfieldMatrixCase,
    *,
    question: str = FOCUSED_FIRST_PATH_QUESTION,
    required_fields: tuple[str, ...] = ("first_path",),
    staged_transaction_present: bool = False,
    before_record_count: int = 135,
    after_record_count: int = 135,
    changed_records: tuple[str, ...] = (),
    preconfirm_dry_run: bool = False,
    commit_manifest: bool = False,
    write_audit_active: bool = True,
    write_attempts: tuple[str, ...] = (),
    subprocess_attempts: tuple[str, ...] = (),
    write_audit_error: str = "",
) -> GreenfieldMatrixResult:
    evidence = {
        "case": case_evidence(case),
        "clarification": {
            "mode": "clarification_required",
            "question": question,
            "required_fields": list(required_fields),
            "returncode": 0,
        },
        "no_write": {
            "before_record_count": before_record_count,
            "after_record_count": after_record_count,
            "changed_records": list(changed_records),
            "staged_transaction_present": staged_transaction_present,
            "write_audit_active": write_audit_active,
            "write_attempts": list(write_attempts),
            "subprocess_attempts": list(subprocess_attempts),
            "write_audit_error": write_audit_error,
        },
    }
    if preconfirm_dry_run:
        evidence["preconfirm_dry_run"] = {"status": "compiled", "transaction_hash": HASH}
    return GreenfieldMatrixResult(
        name=case.name,
        status="passed",
        create_seconds=1.0,
        counts=GreenfieldArtifactCounts(),
        quality=GreenfieldQualityVerdict(True, (), {}, {}, 10, ()),
        commit_manifest_summary={"unexpected": "manifest"} if commit_manifest else {},
        evidence=evidence,
    )
