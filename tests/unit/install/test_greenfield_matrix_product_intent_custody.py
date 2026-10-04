"""Product Intent custody checks for installed Greenfield matrix scoring."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.unit.runtime.greenfield_authored_proposal_fixtures import approved_authored_quality_manifest_fixture


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _scoring_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_quality_scoring")


def _transaction_summary() -> dict[str, str]:
    return {
        "transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }


def _manifest() -> dict[str, object]:
    return {
        "product_create_transaction": _transaction_summary(),
        "write_transaction": {
            "status": "committed",
            "commit_only": True,
            "prewrite_clean_before_commit": True,
            "rollback_guard": "enabled",
            "product_create_transaction_hash": "a" * 64,
            "product_facts_sha256": "c" * 64,
            "repository_write_set_hash": "b" * 64,
        },
    }


def _authored_structural_manifest() -> dict[str, object]:
    manifest = approved_authored_quality_manifest_fixture()
    manifest.update(_manifest())
    manifest.update(
        {
            "status": "passed",
            "validation_status": "passed",
            "issue_count": 0,
            "requested_repair_tier": "standard",
            "repair_tier": "standard",
            "quality_lenses": {
                "status": "not_applicable",
                "lenses": {},
                "reason": "typed_structural_validation",
            },
        }
    )
    manifest["model_authoring"]["canonical_authority"]["product_facts_sha256"] = "c" * 64
    return manifest


def test_write_transaction_custody_accepts_matching_product_intent_hashes() -> None:
    scoring = _scoring_module()

    assert scoring.write_transaction_custody_issues(
        _manifest(),
        product_create_transaction=_transaction_summary(),
    ) == ()


def test_write_transaction_custody_requires_a_product_intent_hash() -> None:
    scoring = _scoring_module()
    manifest = _manifest()
    write_transaction = manifest["write_transaction"]
    assert isinstance(write_transaction, dict)
    write_transaction.pop("product_facts_sha256")

    issues = scoring.write_transaction_custody_issues(
        manifest,
        product_create_transaction=_transaction_summary(),
    )

    assert "write transaction is missing a valid Product Intent facts hash" in issues


def test_write_transaction_custody_rejects_manifest_or_receipt_product_intent_drift() -> None:
    scoring = _scoring_module()
    manifest = _manifest()
    manifest_transaction = manifest["product_create_transaction"]
    assert isinstance(manifest_transaction, dict)
    manifest_transaction["product_facts_sha256"] = "d" * 64

    manifest_issues = scoring.write_transaction_custody_issues(
        manifest,
        product_create_transaction=_transaction_summary(),
    )

    assert "write transaction Product Intent facts hash does not match the manifest summary" in manifest_issues

    receipt = _transaction_summary()
    receipt["product_facts_sha256"] = "d" * 64
    receipt_issues = scoring.write_transaction_custody_issues(
        _manifest(),
        product_create_transaction=receipt,
    )

    assert "write transaction Product Intent facts hash does not match the create payload summary" in receipt_issues


def test_authored_structural_validation_requires_zero_post_receipt_calls() -> None:
    scoring = _scoring_module()
    manifest = _authored_structural_manifest()

    assert scoring._typed_structural_validation_passed(manifest) is True  # noqa: SLF001
    assert scoring._manifest_issues(manifest) == ()  # noqa: SLF001

    model_authoring = manifest["model_authoring"]
    assert isinstance(model_authoring, dict)
    model_authoring["runtime_semantic_model_call_count"] = 1

    assert scoring._typed_structural_validation_passed(manifest) is False  # noqa: SLF001
    assert "pre-confirm quality lens report did not pass" in scoring._manifest_issues(manifest)  # noqa: SLF001

    model_authoring["runtime_semantic_model_call_count"] = 0
    semantic_compiler = manifest["semantic_compiler"]
    assert isinstance(semantic_compiler, dict)
    semantic_compiler["post_candidate_receipt_semantic_calls"] = 1

    assert scoring._typed_structural_validation_passed(manifest) is False  # noqa: SLF001
    assert "pre-confirm quality lens report did not pass" in scoring._manifest_issues(  # noqa: SLF001
        manifest
    )


def test_authored_structural_validation_rejects_invalid_semantic_call_counts() -> None:
    scoring = _scoring_module()

    for invalid_count in (True, False, 1, 2, 0.0, "0"):
        manifest = _authored_structural_manifest()
        model_authoring = manifest["model_authoring"]
        assert isinstance(model_authoring, dict)
        model_authoring["runtime_semantic_model_call_count"] = invalid_count

        assert scoring._typed_structural_validation_passed(manifest) is False  # noqa: SLF001


def test_scoring_reuses_the_native_metadata_receipt_validator() -> None:
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        greenfield_model_authoring_receipt_approved,
    )

    assert _scoring_module().greenfield_model_authoring_receipt_approved is greenfield_model_authoring_receipt_approved


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("runtime_semantic_model_call_count",), 1),
        (("effective_model_window_seconds",), 300.001),
        (("elapsed_seconds",), 300.001),
        (("elapsed_seconds",), float("nan")),
        (("host_candidate", "source_sha256"), ""),
        (("host_candidate", "raw_candidate_sha256"), "g" * 64),
        (("host_candidate", "canonical_candidate_sha256"), None),
        (("canonical_authority", "canonical_candidate_sha256"), "d" * 64),
        (("canonical_authority", "source_sha256"), "d" * 64),
        (("canonical_authority", "product_facts_sha256"), None),
        (("canonical_authority", "authored_relation_set_sha256"), ""),
    ],
)
def test_authored_scoring_rejects_invalid_single_authority_timing_or_digest(
    path,
    value,
) -> None:
    scoring = _scoring_module()
    manifest = _authored_structural_manifest()
    target = manifest["model_authoring"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert scoring._typed_structural_validation_passed(manifest) is False  # noqa: SLF001
    assert "pre-confirm single-authority host receipt did not pass" in scoring._manifest_issues(manifest)  # noqa: SLF001


def test_canonical_authority_facts_must_match_the_committed_custody_summary() -> None:
    scoring = _scoring_module()
    manifest = _authored_structural_manifest()
    manifest["model_authoring"]["canonical_authority"]["product_facts_sha256"] = "d" * 64
    assert "canonical host Product Intent facts hash does not match the write transaction" in scoring._manifest_issues(manifest)  # noqa: SLF001
    assert scoring._semantic_manifest_score(manifest) == 0  # noqa: SLF001


def test_authored_structural_validation_does_not_promote_unproven_semantic_lenses() -> None:
    scoring = _scoring_module()
    manifest = _authored_structural_manifest()

    lenses = scoring._quality_lenses(  # noqa: SLF001
        manifest_lenses={},
        evidence_findings=(),
        counts=scoring.GreenfieldArtifactCounts(),
        manifest=manifest,
        create_returncode=0,
    )

    assert lenses == {
        "product_manager": False,
        "architect": False,
        "engineer": False,
        "domain_expert": False,
    }
    assert {
        lens: scoring._independent_lens_score(  # noqa: SLF001
            manifest_lenses={},
            lens=lens,
            passed=lenses[lens],
        )
        for lens in scoring.INDEPENDENT_SEMANTIC_LENS_DIMENSIONS
    } == {lens: scoring.UNSCORED_QUALITY_SCORE for lens in lenses}


def test_claimed_semantic_lens_failure_remains_a_failed_score() -> None:
    scoring = _scoring_module()
    manifest_lenses = {"product_manager": {"status": "passed"}}
    lenses = scoring._quality_lenses(  # noqa: SLF001
        manifest_lenses=manifest_lenses,
        evidence_findings=(
            SimpleNamespace(
                dimension="product_manager",
                message="independent review found a product utility defect",
            ),
        ),
        counts=scoring.GreenfieldArtifactCounts(),
        manifest=_authored_structural_manifest(),
        create_returncode=0,
    )

    assert scoring._independent_lens_score(  # noqa: SLF001
        manifest_lenses=manifest_lenses,
        lens="product_manager",
        passed=lenses["product_manager"],
    ) == 0
    assert scoring._quality_lens_issues(  # noqa: SLF001
        manifest_lenses=manifest_lenses,
        lenses=lenses,
    ) == ("product_manager release-matrix lens failed",)


def test_unscored_independent_lenses_do_not_claim_release_quality() -> None:
    scoring = _scoring_module()
    scores = {dimension: 10 for dimension in scoring.QUALITY_SCORE_DIMENSIONS}
    scores.update({lens: scoring.UNSCORED_QUALITY_SCORE for lens in scoring.INDEPENDENT_SEMANTIC_LENS_DIMENSIONS})

    assert scoring._automated_unscored_dimensions(scores) == ()  # noqa: SLF001
    assert scoring._score_basis(scores) == (  # noqa: SLF001
        "automated_contract_independent_semantic_review_required"
    )
    assert scoring._final_quality_score(  # noqa: SLF001
        scores=scores,
        manifest=_authored_structural_manifest(),
        create_returncode=0,
        rendered_issues=(),
        prompt_issues=(),
    ) == 10
    explanation = scoring._score_explanation(  # noqa: SLF001
        score=10,
        scores=scores,
        counts=scoring.GreenfieldArtifactCounts(),
        rendered_issues=(),
        prompt_issues=(),
        manifest=_authored_structural_manifest(),
        create_returncode=0,
        lenses={lens: False for lens in scoring.INDEPENDENT_SEMANTIC_LENS_DIMENSIONS},
    )
    assert explanation[0].startswith("automated contract passed; independent semantic review remains required")
    assert all("all release-quality dimensions" not in line for line in explanation)


def test_optional_discovery_browser_proof_remains_not_applicable() -> None:
    scoring = _scoring_module()
    scores = {dimension: 10 for dimension in scoring.QUALITY_SCORE_DIMENSIONS}
    scores["browser_surface_proof"] = scoring._browser_surface_proof_score(  # noqa: SLF001
        create_returncode=0,
        browser_surface_proof_attempted=False,
        browser_surface_proof_required=False,
    )

    assert scores["browser_surface_proof"] == scoring.UNSCORED_QUALITY_SCORE
    assert scoring._automated_unscored_dimensions(scores) == ()  # noqa: SLF001
    assert scoring._score_basis(scores) == "volume_discovery_without_browser_surface_proof"  # noqa: SLF001
    assert scoring._final_quality_score(  # noqa: SLF001
        scores=scores,
        manifest=_authored_structural_manifest(),
        create_returncode=0,
        rendered_issues=(),
        prompt_issues=(),
    ) == 10


def test_required_unattempted_browser_proof_still_fails_release_scoring() -> None:
    scoring = _scoring_module()
    scores = {dimension: 10 for dimension in scoring.QUALITY_SCORE_DIMENSIONS}
    scores["browser_surface_proof"] = scoring._browser_surface_proof_score(  # noqa: SLF001
        create_returncode=0,
        browser_surface_proof_attempted=False,
        browser_surface_proof_required=True,
    )

    assert scores["browser_surface_proof"] == 0
    assert scoring._browser_surface_proof_issues(  # noqa: SLF001
        create_returncode=0,
        browser_surface_proof_attempted=False,
        browser_surface_proof_required=True,
    ) == (
        "browser surface proof was not attempted; premium release scoring requires headless rendered-surface proof",
    )
    assert scoring._final_quality_score(  # noqa: SLF001
        scores=scores,
        manifest=_authored_structural_manifest(),
        create_returncode=0,
        rendered_issues=(),
        prompt_issues=(),
    ) == 0
