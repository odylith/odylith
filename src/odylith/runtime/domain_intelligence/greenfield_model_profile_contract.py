"""Pinned model profiles for the supported Greenfield operating envelope.

Profiles bind real author/reviewer requests to one end-to-end consumer deadline. The
unavailable-provider profile is deliberately outside the supported-success set;
it exists only to prove fail-closed, no-write behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION = "odylith.greenfield.model-profile-contract.v10"

STANDARD_PROFILE_ID = "greenfield-standard-terra-low-sol-medium-review-v10"
RESCUE_PROFILE_ID = "greenfield-rescue-terra-medium-sol-high-review-v8"
DEEP_PROFILE_ID = "greenfield-deep-sol-high-v8"
UNAVAILABLE_PROVIDER_PROFILE_ID = "greenfield-unavailable-provider-no-write-v1"


@dataclass(frozen=True, slots=True)
class GreenfieldModelProfile:
    """Pinned author/reviewer roles inside one shared consumer time budget."""

    profile_id: str
    repair_tier: str
    provider: str
    model: str
    reasoning_effort: str
    source_review_model: str
    source_review_reasoning_effort: str
    consumer_budget_seconds: float
    model_timeout_seconds: float
    # Relative capability of the initial semantic author, not every role in a composite.
    lower_capability: bool = False
    supported_success: bool = True
    source_review_reserve_seconds: float = 0.0


_PROFILES = MappingProxyType(
    {
        STANDARD_PROFILE_ID: GreenfieldModelProfile(
            profile_id=STANDARD_PROFILE_ID,
            repair_tier="standard",
            provider="codex-cli",
            model="gpt-5.6-terra",
            reasoning_effort="low",
            source_review_model="gpt-5.6-sol",
            source_review_reasoning_effort="medium",
            consumer_budget_seconds=60.0,
            model_timeout_seconds=55.0,
            lower_capability=True,
            source_review_reserve_seconds=25.0,
        ),
        RESCUE_PROFILE_ID: GreenfieldModelProfile(
            profile_id=RESCUE_PROFILE_ID,
            repair_tier="rescue",
            provider="codex-cli",
            model="gpt-5.6-terra",
            reasoning_effort="medium",
            source_review_model="gpt-5.6-sol",
            source_review_reasoning_effort="high",
            consumer_budget_seconds=90.0,
            model_timeout_seconds=80.0,
            lower_capability=True,
            source_review_reserve_seconds=20.0,
        ),
        DEEP_PROFILE_ID: GreenfieldModelProfile(
            profile_id=DEEP_PROFILE_ID,
            repair_tier="deep",
            provider="codex-cli",
            model="gpt-5.6-sol",
            reasoning_effort="high",
            source_review_model="gpt-5.6-sol",
            source_review_reasoning_effort="high",
            consumer_budget_seconds=120.0,
            model_timeout_seconds=105.0,
            source_review_reserve_seconds=20.0,
        ),
        UNAVAILABLE_PROVIDER_PROFILE_ID: GreenfieldModelProfile(
            profile_id=UNAVAILABLE_PROVIDER_PROFILE_ID,
            repair_tier="rescue",
            provider="codex-cli",
            model="gpt-5.4-mini",
            reasoning_effort="high",
            source_review_model="gpt-5.4-mini",
            source_review_reasoning_effort="high",
            consumer_budget_seconds=90.0,
            model_timeout_seconds=1.0,
            supported_success=False,
        ),
    }
)

_SUPPORTED_PROFILE_IDS = (
    STANDARD_PROFILE_ID,
    RESCUE_PROFILE_ID,
    DEEP_PROFILE_ID,
)


def get_greenfield_model_profile(profile_id: str) -> GreenfieldModelProfile:
    """Return one pinned profile or reject an undeclared execution posture."""

    normalized = str(profile_id or "").strip()
    try:
        return _PROFILES[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported Greenfield model profile: {normalized or '<empty>'}") from exc


def supported_greenfield_model_profile_ids() -> tuple[str, ...]:
    """Return profiles allowed to support successful operating-envelope claims."""

    return _SUPPORTED_PROFILE_IDS


def supported_greenfield_model_repair_tiers() -> tuple[str, ...]:
    """Return the distinct authored tiers backed by supported real profiles."""

    return tuple(dict.fromkeys(_PROFILES[profile_id].repair_tier for profile_id in _SUPPORTED_PROFILE_IDS))


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
    """Select the pre-call profile from the requested repair tier.

    The unqualified consumer path is the pinned standard request. Rescue and
    deep are explicit pre-call choices; elapsed time never relabels the
    provider request after execution.
    """

    normalized = normalize_greenfield_model_repair_tier(repair_tier)
    if normalized in {"auto", "standard"}:
        return STANDARD_PROFILE_ID
    if normalized == "rescue":
        return RESCUE_PROFILE_ID
    if normalized == "deep":
        return DEEP_PROFILE_ID
    raise ValueError(f"unsupported Greenfield repair tier: {repair_tier}")


def greenfield_model_profile_observation_issues(
    *,
    profile_id: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    effective_timeout_seconds: float,
    authoring_tier: str = "",
    request_role: str = "initial_authoring",
) -> tuple[str, ...]:
    """Compare observed request metadata with the pinned pre-call profile."""

    profile = get_greenfield_model_profile(profile_id)
    if request_role not in {"initial_authoring", "source_review"}:
        raise ValueError(f"unsupported Greenfield model request role: {request_role}")
    observations = {
        "provider": str(provider or "").strip().casefold(),
        "model": str(model or "").strip(),
        "reasoning_effort": str(reasoning_effort or "").strip().casefold(),
    }
    expected = {
        "provider": profile.provider,
        "model": profile.source_review_model if request_role == "source_review" else profile.model,
        "reasoning_effort": (
            profile.source_review_reasoning_effort if request_role == "source_review"
            else profile.reasoning_effort
        ),
    }
    issues = [
        f"observed {field} does not match pinned Greenfield model profile"
        for field, value in observations.items()
        if value != expected[field]
    ]
    try:
        timeout_seconds = float(effective_timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 0.0
    if not 0.0 < timeout_seconds <= profile.model_timeout_seconds:
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
    request_role: str = "initial_authoring",
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
    "GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION",
    "GreenfieldModelProfile",
    "RESCUE_PROFILE_ID",
    "STANDARD_PROFILE_ID",
    "UNAVAILABLE_PROVIDER_PROFILE_ID",
    "greenfield_model_profile_observation_issues",
    "get_greenfield_model_profile",
    "model_profile_id_for_repair_tier",
    "normalize_greenfield_model_repair_tier",
    "require_greenfield_model_profile_observation",
    "supported_greenfield_model_profile_ids",
    "supported_greenfield_model_repair_tiers",
]
