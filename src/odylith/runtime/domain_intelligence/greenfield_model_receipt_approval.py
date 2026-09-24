"""Fail-closed approval of retained Greenfield model-stage receipts."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    CANDIDATE_REVIEW_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    greenfield_model_profile_observation_issues,
    model_profile_id_for_repair_tier,
)


def greenfield_model_authoring_receipt_approved(
    *,
    model_authoring: Mapping[str, Any],
    semantic_compiler: Mapping[str, Any],
    requested_repair_tier: str,
) -> bool:
    """Validate observed author/reviewer metadata, not source authority or quality."""

    revised = model_authoring.get("semantic_model_call_count") == 5
    expected_fields = {
        "authoring_version",
        "semantic_model_call_count",
        "tier",
        "elapsed_seconds",
        "effective_model_window_seconds",
        "participant_selection",
        "remaining_candidate_authoring",
        "candidate_review",
    }
    if revised:
        expected_fields.update({"candidate_revision", "rejected_candidate_review"})
    return (
        set(model_authoring) == expected_fields
        and str(semantic_compiler.get("version", "")).strip()
        == "odylith.greenfield.authored-semantic-validation.v4"
        and str(semantic_compiler.get("status", "")).strip() == "passed"
        and str(semantic_compiler.get("semantic_owner", "")).strip()
        == "validated_model_authored_intent"
        and str(model_authoring.get("authoring_version", "")).strip()
        == GREENFIELD_INTENT_AUTHORING_VERSION
        and _semantic_model_call_count_approved(
            model_authoring.get("semantic_model_call_count")
        )
        and _authoring_role_approved(
            model_authoring,
            request_role="participant_selection",
            requested_repair_tier=requested_repair_tier,
        )
        and _authoring_role_approved(
            model_authoring,
            request_role="remaining_candidate_authoring",
            requested_repair_tier=requested_repair_tier,
        )
        and (
            not revised
            or _authoring_role_approved(
                model_authoring,
                request_role="candidate_revision",
                requested_repair_tier=requested_repair_tier,
            )
        )
        and (
            not revised
            or _rejected_candidate_review_approved(
                model_authoring,
                requested_repair_tier=requested_repair_tier,
            )
        )
        and _candidate_review_approved(
            model_authoring,
            requested_repair_tier=requested_repair_tier,
        )
        and type(semantic_compiler.get("post_authoring_interpretation_calls")) is int
        and semantic_compiler.get("post_authoring_interpretation_calls")
        == (2 if revised else 1)
    )


def _semantic_model_call_count_approved(value: Any) -> bool:
    return type(value) is int and value in {3, 5}


def _authoring_role_approved(
    model_authoring: Mapping[str, Any],
    *,
    requested_repair_tier: str,
    request_role: str,
    receipt_key: str = "",
) -> bool:
    receipt = model_authoring.get(receipt_key or request_role)
    if request_role != "candidate_review" and (
        not isinstance(receipt, Mapping)
        or set(receipt) != {"elapsed_seconds", "model_profile"}
    ):
        return False
    if not isinstance(receipt, Mapping):
        return False
    raw_observation = receipt.get("model_profile")
    observation = raw_observation if isinstance(raw_observation, Mapping) else {}
    if set(observation) != {
        "profile_id",
        "provider",
        "model",
        "reasoning_effort",
        "effective_timeout_seconds",
        "authoring_tier",
    }:
        return False
    timeout = observation.get("effective_timeout_seconds")
    if (
        type(timeout) not in (int, float)
        or (isinstance(timeout, float) and not math.isfinite(timeout))
        or timeout <= 0
    ):
        return False
    profile_id = str(observation.get("profile_id") or "").strip()
    authoring_tier = str(model_authoring.get("tier") or "").strip().casefold()
    if str(observation.get("authoring_tier") or "").strip().casefold() != authoring_tier:
        return False
    try:
        profile = get_greenfield_model_profile(profile_id)
        expected_profile_id = model_profile_id_for_repair_tier(requested_repair_tier)
        observation_issues = greenfield_model_profile_observation_issues(
            profile_id=profile_id,
            provider=str(observation.get("provider") or ""),
            model=str(observation.get("model") or ""),
            reasoning_effort=str(observation.get("reasoning_effort") or ""),
            effective_timeout_seconds=observation.get("effective_timeout_seconds"),
            authoring_tier=str(observation.get("authoring_tier") or ""),
            request_role=request_role,
        )
    except (TypeError, ValueError, OverflowError):
        return False
    return (
        profile_id == expected_profile_id
        and authoring_tier == profile.repair_tier
        and not observation_issues
    )


def _candidate_review_approved(
    model_authoring: Mapping[str, Any], *, requested_repair_tier: str,
) -> bool:
    review = model_authoring.get("candidate_review")
    if not isinstance(review, Mapping) or set(review) != {
        "version",
        "status",
        "source_sha256",
        "candidate_sha256",
        "product_facts_sha256",
        "elapsed_seconds",
        "model_profile",
    }:
        return False
    if review.get("version") != CANDIDATE_REVIEW_VERSION or review.get("status") != "admitted":
        return False
    for key in ("source_sha256", "candidate_sha256", "product_facts_sha256"):
        if not _is_sha256(review.get(key)):
            return False
    if not _authoring_role_approved(
        model_authoring,
        requested_repair_tier=requested_repair_tier,
        request_role="candidate_review",
    ):
        return False
    return _sequential_model_receipts_approved(model_authoring)


def _rejected_candidate_review_approved(
    model_authoring: Mapping[str, Any], *, requested_repair_tier: str,
) -> bool:
    review = model_authoring.get("rejected_candidate_review")
    if not isinstance(review, Mapping) or set(review) != {
        "version",
        "status",
        "source_sha256",
        "candidate_sha256",
        "elapsed_seconds",
        "model_profile",
        "issue",
    }:
        return False
    issue = review.get("issue")
    if (
        review.get("version") != CANDIDATE_REVIEW_VERSION
        or review.get("status") != "denied"
        or not isinstance(issue, Mapping)
        or set(issue) != {"path", "reason"}
        or any(not isinstance(issue[key], str) or not issue[key].strip() for key in issue)
        or not all(_is_sha256(review.get(key)) for key in ("source_sha256", "candidate_sha256"))
    ):
        return False
    return _authoring_role_approved(
        model_authoring,
        requested_repair_tier=requested_repair_tier,
        request_role="candidate_review",
        receipt_key="rejected_candidate_review",
    )


def _sequential_model_receipts_approved(model_authoring: Mapping[str, Any]) -> bool:
    role_keys = ["participant_selection", "remaining_candidate_authoring"]
    if model_authoring.get("semantic_model_call_count") == 5:
        role_keys.extend(["rejected_candidate_review", "candidate_revision"])
    role_keys.append("candidate_review")
    receipts = [model_authoring.get(key) for key in role_keys]
    if any(not isinstance(receipt, Mapping) for receipt in receipts):
        return False
    total = model_authoring.get("elapsed_seconds")
    shared_effective = model_authoring.get("effective_model_window_seconds")
    numeric = [total, shared_effective]
    for receipt in receipts:
        assert isinstance(receipt, Mapping)
        profile = receipt.get("model_profile")
        if not isinstance(profile, Mapping):
            return False
        numeric.extend(
            [receipt.get("elapsed_seconds"), profile.get("effective_timeout_seconds")]
        )
    if any(type(value) not in (int, float) or value < 0 for value in numeric):
        return False
    try:
        normalized = [float(value) for value in numeric]
    except (OverflowError, TypeError, ValueError):
        return False
    if any(not math.isfinite(value) for value in normalized):
        return False
    total_seconds, shared_effective_seconds = normalized[:2]
    first = receipts[0]
    assert isinstance(first, Mapping)
    profile = get_greenfield_model_profile(first["model_profile"]["profile_id"])
    elapsed = 0.0
    for receipt in receipts:
        assert isinstance(receipt, Mapping)
        stage_elapsed = float(receipt["elapsed_seconds"])
        stage_timeout = float(receipt["model_profile"]["effective_timeout_seconds"])
        if not stage_elapsed <= stage_timeout <= shared_effective_seconds - elapsed:
            return False
        elapsed += stage_elapsed
    return (
        total_seconds <= shared_effective_seconds <= profile.model_timeout_seconds
        and elapsed <= total_seconds
    )


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - set("0123456789abcdef")
    )


__all__ = ["greenfield_model_authoring_receipt_approved"]
