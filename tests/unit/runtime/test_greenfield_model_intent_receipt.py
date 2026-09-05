"""Receipt custody for bounded Greenfield semantic authoring calls."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    build_product_create_transaction,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
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
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
    approved_authored_quality_manifest_fixture,
    compiled_greenfield_package_fixture,
)


def test_authoring_receipt_preserves_the_validated_intent_call_count() -> None:
    authored = SimpleNamespace(
        provider={
            "provider": "codex",
            "model": "gpt-5.6-terra",
            "reasoning_effort": "medium",
        },
        profile_id="greenfield-standard-terra-medium-v1",
        effective_timeout_seconds=55.0,
        tier="standard",
        elapsed_seconds=42.0,
        consistency_status="consistent",
        source_spans=(),
        semantic_model_call_count=2,
    )

    assert _authoring_receipt(authored)["semantic_model_call_count"] == 2


def test_clarification_receipt_defaults_to_the_single_observed_call() -> None:
    clarification = GreenfieldAuthoringClarification(
        required_fields=("first_path",),
        elapsed_seconds=12.0,
        tier="standard",
        provider={
            "provider": "codex",
            "model": "gpt-5.6-terra",
            "reasoning_effort": "medium",
        },
        profile_id="greenfield-standard-terra-medium-v1",
        effective_timeout_seconds=55.0,
        consistency_status="material_ambiguity",
        consistency_source_spans=(),
    )

    assert _authoring_receipt(clarification)["semantic_model_call_count"] == 1


def _approved_model_authoring(
    profile_id: str,
    *,
    elapsed_seconds: float,
    semantic_model_call_count: int = 1,
) -> dict[str, Any]:
    profile = get_greenfield_model_profile(profile_id)
    return {
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": semantic_model_call_count,
        "tier": profile.repair_tier,
        "elapsed_seconds": elapsed_seconds,
        "model_profile": {
            "profile_id": profile.profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
    }


@pytest.mark.parametrize("semantic_model_call_count", (1, 2))
def test_quality_approval_accepts_bounded_model_calls_and_zero_reinterpretation(
    semantic_model_call_count: int,
) -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        approved_authored_quality_manifest_fixture(
            model_authoring=_approved_model_authoring(
                STANDARD_PROFILE_ID,
                elapsed_seconds=12.0,
                semantic_model_call_count=semantic_model_call_count,
            )
        )
    )


@pytest.mark.parametrize("invalid_count", (True, 0, 3))
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
    semantic_compiler["version"] = "odylith.greenfield.authored-semantic-validation.v1"

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
    ),
)
def test_quality_approval_rejects_retired_model_authoring_versions(
    retired_version: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="pre-confirm ProductCreateTransaction quality manifest is not approved",
    ):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            approved_authored_quality_manifest_fixture(
                model_authoring={
                    "authoring_version": retired_version,
                    "semantic_model_call_count": 1,
                    "tier": "standard",
                    "elapsed_seconds": 12.0,
                }
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
