from __future__ import annotations

import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_campaign import MatrixCampaignConfig
from greenfield_matrix_campaign import campaign_summary
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
