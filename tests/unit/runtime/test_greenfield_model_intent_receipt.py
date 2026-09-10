"""Receipt custody for bounded Greenfield semantic authoring calls."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    build_product_create_transaction,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    _authoring_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
    approved_authored_quality_manifest_fixture,
)
from tests.unit.runtime.greenfield_proposal_fixtures import (
    compiled_greenfield_package_fixture,
)


@pytest.mark.parametrize("call_count", [1, 2])
def test_authoring_receipt_preserves_observed_count_without_authenticating_it(call_count) -> None:
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    review = _approved_model_authoring(STANDARD_PROFILE_ID, elapsed_seconds=42.0)["candidate_review"]
    authored = GreenfieldModelAuthoredIntent(
        intent={}, first_path_relations=(), first_path_context_relations=(),
        component_responsibility_relations=(), atomic_claims=(),
        source_sha256=review["source_sha256"], provisional_design={}, source_precedence=(),
        provider={
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        },
        profile_id=profile.profile_id,
        effective_timeout_seconds=profile.model_timeout_seconds,
        tier="standard",
        elapsed_seconds=42.0,
        consistency_status="consistent",
        source_spans=(),
        semantic_model_call_count=call_count,
        initial_authoring_elapsed_seconds=41.0,
        candidate_review=review,
    )

    receipt = _authoring_receipt(authored)
    assert receipt["semantic_model_call_count"] == call_count
    assert receipt["candidate_review"] == review
    assert receipt["candidate_review"] is not review
    assert receipt["candidate_review"]["model_profile"] is not review["model_profile"]
    assert receipt["initial_authoring_elapsed_seconds"] == 41.0
    manifest = approved_authored_quality_manifest_fixture(model_authoring=receipt)
    if call_count != 2:
        with pytest.raises(ValueError, match="quality manifest is not approved"):
            greenfield_create_transaction.require_product_create_transaction_quality_approved(manifest)
    else:
        greenfield_create_transaction.require_product_create_transaction_quality_approved(manifest)


@pytest.mark.parametrize("call_count", [1, 2])
def test_clarification_receipt_preserves_the_observed_call_count(call_count) -> None:
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    clarification = GreenfieldAuthoringClarification(
        required_fields=("first_path",),
        elapsed_seconds=12.0,
        tier="standard",
        provider={
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        },
        profile_id=profile.profile_id,
        effective_timeout_seconds=profile.model_timeout_seconds,
        consistency_status="material_ambiguity",
        consistency_source_spans=(),
        semantic_model_call_count=call_count,
    )

    receipt = _authoring_receipt(clarification)
    assert receipt["semantic_model_call_count"] == call_count
    assert "candidate_review" not in receipt
    # Clarification observations never authorize a complete transaction.
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(model_authoring=receipt)
        )


def _approved_model_authoring(
    profile_id: str,
    *,
    elapsed_seconds: float,
    semantic_model_call_count: int = 2,
    intent_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    profile = get_greenfield_model_profile(profile_id)
    receipt = approved_authored_quality_manifest_fixture(intent_authority=intent_authority)["model_authoring"]
    receipt.update(
        semantic_model_call_count=semantic_model_call_count,
        tier=profile.repair_tier, elapsed_seconds=elapsed_seconds,
        initial_authoring_elapsed_seconds=elapsed_seconds - 1.0,
        model_profile={
            "profile_id": profile.profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
    )
    receipt["candidate_review"].update(
        elapsed_seconds=1.0,
        model_profile={
            **receipt["model_profile"], "model": profile.review_model,
            "reasoning_effort": profile.review_reasoning_effort,
            "effective_timeout_seconds": profile.review_timeout_seconds,
        },
    )
    return receipt


def test_quality_approval_accepts_two_model_calls_and_one_candidate_review() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        approved_authored_quality_manifest_fixture(
            model_authoring=_approved_model_authoring(
                STANDARD_PROFILE_ID,
                elapsed_seconds=12.0,
                semantic_model_call_count=2,
            )
        )
    )


@pytest.mark.parametrize("call_count", [1, 2])
def test_call_count_claim_without_review_never_approves_a_transaction(call_count: int) -> None:
    receipt = _approved_model_authoring(
        STANDARD_PROFILE_ID, elapsed_seconds=12.0, semantic_model_call_count=call_count,
    )
    receipt.pop("candidate_review")
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(model_authoring=receipt)
        )


@pytest.mark.parametrize("replayed_field", [None, "source_sha256", "product_facts_sha256"])
def test_native_receipt_must_bind_both_source_and_product_facts(
    tmp_path: Path, replayed_field: str | None,
) -> None:
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    authority = proposal[PRODUCT_INTENT_AUTHORITY_KEY]
    package = compiled_greenfield_package_fixture(proposal, repo_root=tmp_path)
    receipt = _approved_model_authoring(
        STANDARD_PROFILE_ID, elapsed_seconds=12.0, intent_authority=authority,
    )
    if replayed_field:
        receipt["candidate_review"][replayed_field] = "0" * 64
    manifest = approved_authored_quality_manifest_fixture(
        intent_authority=authority, model_authoring=receipt, elapsed_seconds=13.0,
    )
    greenfield_create_transaction.require_product_create_transaction_quality_approved(manifest)
    arguments = {
        "proposal": proposal, "release_selector": "0.0.1",
        "validation_gate": {"status": "passed", "issues": []},
        "prewrite_package": package, "backlog_result": package.backlog_result or {},
        "intent_authority": authority, "quality_manifest": manifest, "repo_root": tmp_path,
    }
    if replayed_field:
        with pytest.raises(ValueError, match="candidate review does not match its sealed Product Intent authority"):
            build_product_create_transaction(**arguments)
    else:
        transaction = build_product_create_transaction(**arguments)
        assert transaction.verified
        persisted = greenfield_create_transaction.product_create_transaction_to_dict(transaction)
        reviewed = persisted["quality_manifest"]["model_authoring"]["candidate_review"]
        assert reviewed["source_sha256"] == authority["markdown_source_sha256"]
        assert reviewed["product_facts_sha256"] == authority["product_facts_sha256"]
        assert persisted["quality_manifest"]["model_authoring"]["semantic_model_call_count"] == 2


@pytest.mark.parametrize("invalid_count", (True, False, 0, 1, 3, 2.0, "2"))
def test_quality_approval_rejects_invalid_semantic_model_call_counts(
    invalid_count: object,
) -> None:
    receipt = _approved_model_authoring(STANDARD_PROFILE_ID, elapsed_seconds=12.0)
    receipt["semantic_model_call_count"] = invalid_count

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(model_authoring=receipt)
        )


def test_quality_approval_rejects_retired_semantic_validation_version() -> None:
    manifest = approved_authored_quality_manifest_fixture()
    semantic_compiler = manifest["semantic_compiler"]
    assert isinstance(semantic_compiler, dict)
    semantic_compiler["version"] = "odylith.greenfield.authored-semantic-validation.v3"

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            manifest
        )


def test_quality_approval_accepts_explicit_deep_profile() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        approved_authored_quality_manifest_fixture(
            requested_repair_tier="deep",
            repair_tier="deep",
            budget_seconds=120.0,
            elapsed_seconds=101.0,
            model_authoring=_approved_model_authoring(
                DEEP_PROFILE_ID,
                elapsed_seconds=100.0,
            ),
        )
    )


def test_quality_approval_accepts_explicit_rescue_profile() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        approved_authored_quality_manifest_fixture(
            requested_repair_tier="rescue",
            repair_tier="rescue",
            budget_seconds=90.0,
            elapsed_seconds=81.0,
            model_authoring=_approved_model_authoring(
                RESCUE_PROFILE_ID,
                elapsed_seconds=80.0,
            ),
        )
    )


def test_quality_approval_rejects_default_route_relabelled_as_rescue() -> None:
    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(
                requested_repair_tier="auto",
                repair_tier="rescue",
                budget_seconds=90.0,
                model_authoring=_approved_model_authoring(
                    RESCUE_PROFILE_ID,
                    elapsed_seconds=50.0,
                ),
            )
        )


def test_quality_approval_rejects_profile_tier_relabeling() -> None:
    receipt = _approved_model_authoring(DEEP_PROFILE_ID, elapsed_seconds=12.0)
    receipt["tier"] = "standard"

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(
                requested_repair_tier="deep",
                repair_tier="deep",
                budget_seconds=120.0,
                model_authoring=receipt,
            )
        )


@pytest.mark.parametrize(
    "retired_version",
    (
        "odylith.greenfield.model-intent-authoring.v1",
        "odylith.greenfield.intent-authoring.v4",
        "odylith.greenfield.intent-authoring.v5",
        "odylith.greenfield.intent-authoring.v52",
    ),
)
def test_quality_approval_rejects_retired_model_authoring_versions(
    retired_version: str,
) -> None:
    receipt = _approved_model_authoring(STANDARD_PROFILE_ID, elapsed_seconds=12.0)
    receipt["authoring_version"] = retired_version
    with pytest.raises(
        ValueError,
        match="pre-confirm ProductCreateTransaction quality manifest is not approved",
    ):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(
                model_authoring=receipt,
            ),
            authored_projection_verified=True,
        )


@pytest.mark.parametrize(
    "quality_manifest",
    (
        {"status": "failed", "validation_status": "passed", "issue_count": 0},
        {"status": "passed", "validation_status": "failed", "issue_count": 0},
        {
            "status": "passed",
            "validation_status": "passed",
            "issue_count": 0,
            "hard_blocker": "component spec",
        },
        {"status": "passed", "validation_status": "passed", "issue_count": 1},
        approved_authored_quality_manifest_fixture(version=""),
        approved_authored_quality_manifest_fixture(engine=""),
        approved_authored_quality_manifest_fixture(
            write_transaction={"status": "committed", "rollback_guard": "enabled"}
        ),
        approved_authored_quality_manifest_fixture(
            write_transaction={
                "status": "not_started",
                "rollback_guard": "disabled",
                "prewrite_clean_before_commit": True,
            }
        ),
        approved_authored_quality_manifest_fixture(
            write_transaction={
                "status": "not_started",
                "rollback_guard": "enabled",
                "prewrite_clean_before_commit": False,
            }
        ),
        approved_authored_quality_manifest_fixture(
            write_transaction={
                "status": "not_started",
                "rollback_guard": "enabled",
                "prewrite_clean_before_commit": True,
                "commit_only": True,
            }
        ),
        approved_authored_quality_manifest_fixture(elapsed_seconds=60.0),
        approved_authored_quality_manifest_fixture(budget_seconds=90.0),
        approved_authored_quality_manifest_fixture(
            requested_repair_tier="auto",
            repair_tier="rescue",
            budget_seconds=90.0,
        ),
        approved_authored_quality_manifest_fixture(
            requested_repair_tier="auto",
            repair_tier="deep",
            budget_seconds=120.0,
        ),
        approved_authored_quality_manifest_fixture(
            semantic_compiler={
                "semantic_owner": "validated_model_authored_intent",
                "post_authoring_interpretation_calls": 0,
            }
        ),
        approved_authored_quality_manifest_fixture(
            model_authoring={
                "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
                "semantic_model_call_count": 1,
                "tier": "standard",
            }
        ),
        approved_authored_quality_manifest_fixture(
            model_authoring={
                "authoring_version": "odylith.greenfield.intent-authoring.v4",
                "semantic_model_call_count": 1,
                "tier": "standard",
            }
        ),
    ),
)
def test_build_product_create_transaction_rejects_unapproved_manifest_before_confirmation(
    tmp_path: Path,
    quality_manifest: Mapping[str, Any],
) -> None:
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    package = compiled_greenfield_package_fixture(proposal, repo_root=tmp_path)

    with pytest.raises(
        ValueError,
        match="pre-confirm ProductCreateTransaction quality manifest is not approved",
    ):
        build_product_create_transaction(
            proposal=proposal,
            release_selector="0.0.1",
            validation_gate={"status": "passed", "issues": []},
            prewrite_package=package,
            backlog_result=package.backlog_result or {},
            intent_authority=proposal[PRODUCT_INTENT_AUTHORITY_KEY],
            quality_manifest=quality_manifest,
            repo_root=tmp_path,
        )
