"""Authored Greenfield fixture ownership: source custody, A/R receipts, and proposals."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import (
    PRECONFIRM_ENGINE_VERSION,
    PRECONFIRM_QUALITY_MANIFEST_VERSION,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    StructuredAuthoringProvider,
    authored_response,
)


def approved_authored_quality_manifest_fixture(
    *, intent_authority: Mapping[str, Any] | None = None, **overrides: Any,
) -> dict[str, Any]:
    """Bind native transaction fixtures to their authority; standalone receipts use test hashes."""

    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    authority = intent_authority or {}
    manifest: dict[str, Any] = {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "status": "passed",
        "validation_status": "passed",
        "issue_count": 0,
        "hard_blocker": None,
        "requested_repair_tier": "auto",
        "repair_tier": profile.repair_tier,
        "budget_seconds": profile.consumer_budget_seconds,
        "elapsed_seconds": 1.0,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
        "semantic_compiler": {
            "version": "odylith.greenfield.authored-semantic-validation.v4",
            "status": "passed",
            "semantic_owner": "validated_model_authored_intent",
            "post_authoring_interpretation_calls": 1,
        },
        "model_authoring": {
            "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
            "semantic_model_call_count": 2,
            "tier": profile.repair_tier,
            "elapsed_seconds": 0.5,
            "initial_authoring_elapsed_seconds": 0.25,
            "candidate_review": {
                "version": "odylith.greenfield.candidate-review.v1",
                "status": "admitted",
                "source_sha256": authority.get("markdown_source_sha256", "0" * 64),
                "candidate_sha256": "1" * 64,
                "product_facts_sha256": authority.get("product_facts_sha256", "2" * 64),
                "elapsed_seconds": 0.25,
                "model_profile": {
                    "profile_id": profile.profile_id,
                    "provider": profile.provider,
                    "model": profile.review_model,
                    "reasoning_effort": profile.review_reasoning_effort,
                    "effective_timeout_seconds": profile.review_timeout_seconds,
                    "authoring_tier": profile.repair_tier,
                },
            },
            "model_profile": {
                "profile_id": profile.profile_id,
                "provider": profile.provider,
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
                "effective_timeout_seconds": profile.model_timeout_seconds,
                "authoring_tier": profile.repair_tier,
            },
        },
    }
    manifest.update(overrides)
    return manifest


def materialize_typed_intent_fixture(
    repo_root: Path,
    *,
    intent: Mapping[str, Any],
    first_path_relations: list[Mapping[str, Any]],
    component_responsibility_owners: list[str],
    authoring_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize explicit typed fixture data through the shipped custody path."""

    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    receipt = authoring_receipt if authoring_receipt is not None else {}
    return materialize_model_authored_intent(
        prompt=source,
        repo_root=repo_root,
        review_provider_factory=AdmittingReviewProvider,
        authoring_provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                first_path_relations=first_path_relations,
                component_responsibility_owners=component_responsibility_owners,
            )
        ),
        authoring_timeout_seconds=54,
        authoring_profile_id=STANDARD_PROFILE_ID,
        authoring_receipt=receipt,
    )


def canonical_model_authored_intent_fixture(
    repo_root: Path,
    *,
    authoring_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return explicit typed Commerce intent authored from exact cited evidence."""

    first_path = (
        "Shopper opens Storefront and adds one product to the cart. "
        "Storefront sends the cart to Checkout Orchestrator. "
        "Checkout Orchestrator requests a sandbox payment from Payment Sandbox. "
        "Payment Sandbox returns a failed payment response. "
        "Shopper retries checkout. "
        "Checkout Orchestrator creates an order draft and shows recovery status."
    )
    intent: dict[str, Any] = {
        "title": "Commerce Launch System",
        "product_story": (
            "Commerce Launch System lets a shopper complete a reviewable browse-to-checkout "
            "journey and recover from a failed sandbox payment."
        ),
        "state_object": "order draft",
        "first_path": first_path,
        "proof_boundary": (
            "Verify the failed sandbox payment, retry, idempotent order draft, and visible "
            "recovery status without claiming production payment readiness."
        ),
        "problem": (
            "Shoppers and commerce builders cannot trust checkout until cart, payment, retry, "
            "and order-draft evidence stay connected."
        ),
        "customer": "Shoppers and commerce builders",
        "opportunity": "Prove one browse-to-checkout recovery path before production expansion.",
        "product_view": (
            "The product keeps browse, checkout recovery, order-draft state, and review evidence "
            "visible as one journey."
        ),
        "success_metrics": [
            "A shopper sees recovery status after retrying a failed sandbox payment.",
            "A reviewer can trace the idempotent order draft to the cart and payment evidence.",
        ],
        "evidence_requirements": [
            "Retain the failed payment response with the retry outcome.",
            "Retain the order draft with its cart and payment evidence.",
        ],
        "operational_constraints": [
            "Keep order creation idempotent under retry.",
            "Keep production payment readiness outside the first release claim.",
        ],
        "component_responsibilities": [
            "Own browse, cart entry, checkout entry, and user-facing errors.",
            "Own payment handoff, order draft, idempotency, and recovery boundaries.",
            "Own product facts, price snapshots, inventory visibility, and merchandising review.",
        ],
        "human_actors": ["Shopper"],
        "external_systems": ["Payment Sandbox"],
        "internal_systems": ["Storefront", "Checkout Orchestrator", "Catalog Boundary"],
        "assumptions": [
            {"applies_to": "general", "statement": "The first release uses a sandbox payment response."},
        ],
        "ambiguities": [],
        "non_goals": [
            "Do not claim production payment readiness.",
            "Do not automate merchandising decisions.",
        ],
    }
    relations = [
        {
            "actor_kind": "human",
            "actor_fact_quote": "Shopper",
            "event_quote": "Shopper opens Storefront and adds one product to the cart",
            "action_verb_quote": "opens",
            "target_quote": "Storefront",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_fact_quote": "Storefront",
            "owner_system_quote": "Storefront",
            "event_quote": "Storefront sends the cart to Checkout Orchestrator",
            "action_verb_quote": "sends",
            "target_quote": "the cart",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_fact_quote": "Checkout Orchestrator",
            "owner_system_quote": "Checkout Orchestrator",
            "event_quote": (
                "Checkout Orchestrator requests a sandbox payment from Payment Sandbox"
            ),
            "action_verb_quote": "requests",
            "target_quote": "a sandbox payment",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "external_system",
            "actor_fact_quote": "Payment Sandbox",
            "event_quote": "Payment Sandbox returns a failed payment response",
            "action_verb_quote": "returns",
            "target_quote": "a failed payment response",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "human",
            "actor_fact_quote": "Shopper",
            "event_quote": "Shopper retries checkout",
            "action_verb_quote": "retries",
            "target_quote": "checkout",
            "visible_result_quote": "",
        },
        {
            "actor_kind": "product",
            "actor_fact_quote": "Checkout Orchestrator",
            "owner_system_quote": "Checkout Orchestrator",
            "event_quote": (
                "Checkout Orchestrator creates an order draft and shows recovery status"
            ),
            "action_verb_quote": "creates",
            "target_quote": "an order draft",
            "visible_result_quote": "recovery status",
        },
    ]
    return materialize_typed_intent_fixture(
        repo_root,
        intent=intent,
        first_path_relations=relations,
        component_responsibility_owners=[
            "Storefront",
            "Checkout Orchestrator",
            "Catalog Boundary",
        ],
        authoring_receipt=authoring_receipt,
    )


def _canonical_model_authored_greenfield_fixture(repo_root: Path) -> dict[str, Any]:
    """Return one explicit typed Commerce proposal with sealed source custody."""

    authoring_receipt: dict[str, Any] = {}
    candidate = canonical_model_authored_intent_fixture(
        repo_root,
        authoring_receipt=authoring_receipt,
    )
    source = str(candidate["prompt"])
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=source,
        release_selector="0.0.1",
        confirmed_intent=candidate,
        require_completion_ready=False,
    )
    proposal["_test_model_authoring_receipt"] = authoring_receipt
    return proposal
