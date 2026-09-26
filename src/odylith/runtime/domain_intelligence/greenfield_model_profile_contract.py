"""Pinned success, control, and diagnostic Greenfield model profiles.

The Astra profile is the sole release-success route. Luna is a release-harness
clarification/no-write control, Sol is an unsupported diagnostic, and the
unavailable-provider profile proves fail-closed no-write behavior.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType

GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION = "odylith.greenfield.model-profile-contract.v23"
GREENFIELD_NORMAL_CASE_TARGET_SECONDS = 90.0
GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS = 180.0
# The shared model window leaves finite headroom for compilation, sealing and staging.
_COMPLETION_RESERVE_SECONDS = 15.0

STANDARD_PROFILE_ID = "greenfield-standard-participant-first-astra-medium-v19"
RESCUE_PROFILE_ID = "greenfield-rescue-participant-first-luna-medium-v19"
DEEP_PROFILE_ID = "greenfield-deep-participant-first-sol-high-v18"
UNAVAILABLE_PROVIDER_PROFILE_ID = "greenfield-unavailable-provider-no-write-v1"


@dataclass(frozen=True, slots=True)
class GreenfieldModelProfile:
    """Pinned participant, remaining-author and review roles in one shared budget."""

    profile_id: str
    repair_tier: str
    provider: str
    model: str
    reasoning_effort: str
    performance_target_seconds: float
    operational_timeout_seconds: float
    model_timeout_seconds: float
    lower_capability: bool = False
    supported_success: bool = True
    participant_model: str = "gpt-6-astra"
    participant_reasoning_effort: str = "medium"
    review_model: str = "gpt-6-astra"
    review_reasoning_effort: str = "medium"


_PROFILES = MappingProxyType(
    {
        STANDARD_PROFILE_ID: GreenfieldModelProfile(
            profile_id=STANDARD_PROFILE_ID,
            repair_tier="standard",
            provider="codex-cli",
            model="gpt-6-astra",
            reasoning_effort="medium",
            performance_target_seconds=90.0,
            operational_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS,
            model_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS - _COMPLETION_RESERVE_SECONDS,
        ),
        RESCUE_PROFILE_ID: GreenfieldModelProfile(
            profile_id=RESCUE_PROFILE_ID,
            repair_tier="rescue",
            provider="codex-cli",
            model="gpt-5.6-luna",
            reasoning_effort="medium",
            performance_target_seconds=120.0,
            operational_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS,
            model_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS - _COMPLETION_RESERVE_SECONDS,
            lower_capability=True,
            supported_success=False,
        ),
        DEEP_PROFILE_ID: GreenfieldModelProfile(
            profile_id=DEEP_PROFILE_ID,
            repair_tier="deep",
            provider="codex-cli",
            model="gpt-5.6-sol",
            reasoning_effort="high",
            performance_target_seconds=150.0,
            operational_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS,
            model_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS - _COMPLETION_RESERVE_SECONDS,
            supported_success=False,
        ),
        UNAVAILABLE_PROVIDER_PROFILE_ID: GreenfieldModelProfile(
            profile_id=UNAVAILABLE_PROVIDER_PROFILE_ID,
            repair_tier="rescue",
            provider="codex-cli",
            model="gpt-5.4-mini",
            reasoning_effort="high",
            performance_target_seconds=120.0,
            operational_timeout_seconds=GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS,
            model_timeout_seconds=1.0,
            supported_success=False,
            participant_model="gpt-5.4-mini",
            participant_reasoning_effort="high",
        ),
    }
)

GREENFIELD_DECLARED_PROFILE_IDS = (
    STANDARD_PROFILE_ID,
    RESCUE_PROFILE_ID,
    DEEP_PROFILE_ID,
)
GREENFIELD_RELEASE_SUCCESS_PROFILE_IDS = (
    STANDARD_PROFILE_ID,
)
GREENFIELD_LOWER_CAPABILITY_CONTROL_PROFILE_IDS = (
    RESCUE_PROFILE_ID,
)


def get_greenfield_model_profile(profile_id: str) -> GreenfieldModelProfile:
    """Return one pinned profile or reject an undeclared execution posture."""

    normalized = str(profile_id or "").strip()
    try:
        return _PROFILES[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported Greenfield model profile: {normalized or '<empty>'}") from exc


def declared_greenfield_model_profile_ids() -> tuple[str, ...]:
    """Return pinned real-model profiles, including controls and diagnostics."""

    return GREENFIELD_DECLARED_PROFILE_IDS


def release_success_greenfield_model_profile_ids() -> tuple[str, ...]:
    """Return profiles qualified to support a successful consumer release claim."""

    return GREENFIELD_RELEASE_SUCCESS_PROFILE_IDS


def lower_capability_control_greenfield_model_profile_ids() -> tuple[str, ...]:
    """Return declared lower-capability clarification/no-write controls."""

    return GREENFIELD_LOWER_CAPABILITY_CONTROL_PROFILE_IDS


def supported_greenfield_model_profile_ids() -> tuple[str, ...]:
    """Return profiles allowed to support successful operating-envelope claims."""

    return GREENFIELD_RELEASE_SUCCESS_PROFILE_IDS


def supported_greenfield_model_repair_tiers() -> tuple[str, ...]:
    """Return the distinct authored tiers backed by supported real profiles."""

    return tuple(
        dict.fromkeys(
            _PROFILES[profile_id].repair_tier
            for profile_id in GREENFIELD_RELEASE_SUCCESS_PROFILE_IDS
        )
    )


def normalize_greenfield_model_repair_tier(repair_tier: str) -> str:
    """Return the canonical pre-call tier or reject an undeclared route."""

    normalized = str(repair_tier or "auto").strip().casefold().replace("_", "-")
    aliases = {
        "": "auto",
        "default": "auto",
        "premium": "deep",
        "deep-repair": "deep",
        "ci": "deep",
        "ci-simulation": "deep",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"auto", "standard", "rescue", "deep"}:
        raise ValueError(f"unsupported Greenfield repair tier: {repair_tier}")
    return normalized


def model_profile_id_for_repair_tier(repair_tier: str) -> str:
    """Select the sole qualified success profile or reject control tiers.

    The unqualified consumer path is the pinned standard request. Rescue and
    deep remain declared for harness control/diagnostic evidence only and
    cannot select a successful consumer execution route.
    """

    normalized = normalize_greenfield_model_repair_tier(repair_tier)
    profile_ids_by_tier = {
        "auto": STANDARD_PROFILE_ID,
        "standard": STANDARD_PROFILE_ID,
        "rescue": RESCUE_PROFILE_ID,
        "deep": DEEP_PROFILE_ID,
    }
    profile_id = profile_ids_by_tier[normalized]
    if profile_id not in GREENFIELD_RELEASE_SUCCESS_PROFILE_IDS:
        raise ValueError(
            "Greenfield repair tier is not release-qualified for successful execution: "
            f"{normalized}"
        )
    return profile_id


def greenfield_model_profile_observation_issues(
    *,
    profile_id: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    effective_timeout_seconds: float,
    authoring_tier: str = "",
    request_role: str = "remaining_candidate_authoring",
) -> tuple[str, ...]:
    """Compare observed request metadata with the pinned pre-call profile."""

    profile = get_greenfield_model_profile(profile_id)
    if request_role == "participant_selection":
        expected_model = profile.participant_model
        expected_effort = profile.participant_reasoning_effort
        role_cap = profile.model_timeout_seconds
    elif request_role in {"remaining_candidate_authoring", "candidate_revision"}:
        expected_model = profile.model
        expected_effort = profile.reasoning_effort
        role_cap = profile.model_timeout_seconds
    elif request_role == "candidate_review":
        expected_model = profile.review_model
        expected_effort = profile.review_reasoning_effort
        role_cap = profile.model_timeout_seconds
    else:
        raise ValueError(f"unsupported Greenfield model request role: {request_role}")
    observations = {
        "provider": str(provider or "").strip().casefold(),
        "model": str(model or "").strip(),
        "reasoning_effort": str(reasoning_effort or "").strip().casefold(),
    }
    expected = {
        "provider": profile.provider,
        "model": expected_model,
        "reasoning_effort": expected_effort,
    }
    issues = [
        f"observed {field} does not match pinned Greenfield model profile"
        for field, value in observations.items()
        if value != expected[field]
    ]
    try:
        timeout_seconds = (
            float(effective_timeout_seconds)
            if type(effective_timeout_seconds) in (int, float)
            else 0.0
        )
    except (TypeError, ValueError, OverflowError):
        timeout_seconds = 0.0
    if not math.isfinite(timeout_seconds) or not 0.0 < timeout_seconds <= role_cap:
        issues.append("observed effective timeout exceeds or omits the pinned Greenfield model window")
    normalized_tier = str(authoring_tier or "").strip().casefold()
    if normalized_tier and normalized_tier != profile.repair_tier:
        issues.append("observed authoring tier does not match pinned Greenfield model profile")
    return tuple(issues)


def require_greenfield_model_profile_observation(
    *,
    profile_id: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    effective_timeout_seconds: float,
    authoring_tier: str = "",
    request_role: str = "remaining_candidate_authoring",
) -> GreenfieldModelProfile:
    """Fail closed unless observed request metadata matches its profile."""

    issues = greenfield_model_profile_observation_issues(
        profile_id=profile_id,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        effective_timeout_seconds=effective_timeout_seconds,
        authoring_tier=authoring_tier,
        request_role=request_role,
    )
    if issues:
        raise ValueError("; ".join(issues))
    return get_greenfield_model_profile(profile_id)


__all__ = [
    "DEEP_PROFILE_ID",
    "GREENFIELD_DECLARED_PROFILE_IDS",
    "GREENFIELD_LOWER_CAPABILITY_CONTROL_PROFILE_IDS",
    "GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION",
    "GREENFIELD_NORMAL_CASE_TARGET_SECONDS",
    "GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS",
    "GREENFIELD_RELEASE_SUCCESS_PROFILE_IDS",
    "RESCUE_PROFILE_ID",
    "STANDARD_PROFILE_ID",
    "UNAVAILABLE_PROVIDER_PROFILE_ID",
    "GreenfieldModelProfile",
    "declared_greenfield_model_profile_ids",
    "get_greenfield_model_profile",
    "greenfield_model_profile_observation_issues",
    "lower_capability_control_greenfield_model_profile_ids",
    "model_profile_id_for_repair_tier",
    "normalize_greenfield_model_repair_tier",
    "release_success_greenfield_model_profile_ids",
    "require_greenfield_model_profile_observation",
    "supported_greenfield_model_profile_ids",
    "supported_greenfield_model_repair_tiers",
]
