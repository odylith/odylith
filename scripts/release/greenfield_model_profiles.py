"""Assign and configure the pinned Greenfield release model profiles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
import math
from pathlib import Path
from typing import Any

from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_expectation
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    UNAVAILABLE_PROVIDER_PROFILE_ID,
    get_greenfield_model_profile,
    greenfield_model_profile_observation_issues,
    supported_greenfield_model_profile_ids,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)


MODEL_PROFILE_ASSIGNMENT_VERSION = "case-id-balanced-sha256-v1"
MODEL_PROFILE_ASSIGNMENT_SEED = "f1e5a66a5cce578b0bd9f56d96f08887358632627231769667c432933b9dfe6f"
MODEL_PROFILES = supported_greenfield_model_profile_ids()
UNAVAILABLE_PROVIDER_PROFILE = UNAVAILABLE_PROVIDER_PROFILE_ID
_TAG_PREFIX = "model-profile:"
_PROFILE_ENV_KEYS = (
    "ODYLITH_GREENFIELD_MODEL_PROFILE",
    "ODYLITH_REASONING_MODE",
    "ODYLITH_REASONING_PROVIDER",
    "ODYLITH_REASONING_MODEL",
    "ODYLITH_REASONING_BASE_URL",
    "ODYLITH_REASONING_API_KEY",
    "ODYLITH_REASONING_SCOPE_CAP",
    "ODYLITH_REASONING_TIMEOUT_SECONDS",
    "ODYLITH_REASONING_CODEX_BIN",
    "ODYLITH_REASONING_CODEX_REASONING_EFFORT",
    "ODYLITH_REASONING_CLAUDE_BIN",
    "ODYLITH_REASONING_CLAUDE_REASONING_EFFORT",
)
_TIME_TOLERANCE_SECONDS = 1e-6


def assign_model_profiles(cases: Sequence[GreenfieldMatrixCase]) -> tuple[GreenfieldMatrixCase, ...]:
    """Assign every case to one balanced profile without consulting prompt text."""

    rows = list(cases)
    assignments: dict[int, str] = {}
    counts = {profile: 0 for profile in MODEL_PROFILES}
    stratum_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {profile: 0 for profile in MODEL_PROFILES}
    )
    input_style_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {profile: 0 for profile in MODEL_PROFILES}
    )
    pending: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for index, case in enumerate(rows):
        stratum = case_expectation(case)
        input_style = str(case.input_style or "unspecified")
        explicit = _explicit_profiles(case)
        if len(explicit) > 1 or (explicit and explicit[0] not in MODEL_PROFILES):
            raise ValueError(f"Greenfield case `{_case_id(case)}` has an invalid model profile")
        if explicit:
            assignments[index] = explicit[0]
            counts[explicit[0]] += 1
            stratum_counts[stratum][explicit[0]] += 1
            input_style_counts[input_style][explicit[0]] += 1
            continue
        identity = _case_id(case)
        digest = hashlib.sha256(f"{MODEL_PROFILE_ASSIGNMENT_SEED}:{identity}".encode("utf-8")).hexdigest()
        pending[stratum].append((digest, index))
    for stratum, stratum_rows in sorted(pending.items()):
        for _digest, index in sorted(stratum_rows):
            input_style = str(rows[index].input_style or "unspecified")
            profile = min(
                MODEL_PROFILES,
                key=lambda item: (
                    stratum_counts[stratum][item],
                    input_style_counts[input_style][item],
                    counts[item],
                    MODEL_PROFILES.index(item),
                ),
            )
            assignments[index] = profile
            counts[profile] += 1
            stratum_counts[stratum][profile] += 1
            input_style_counts[input_style][profile] += 1
    return tuple(_with_profile(case, assignments[index]) for index, case in enumerate(rows))


def case_model_profile(case: GreenfieldMatrixCase) -> str:
    """Return the one validated profile assigned to a release case."""

    profiles = _explicit_profiles(case)
    if len(profiles) != 1 or profiles[0] not in MODEL_PROFILES:
        raise ValueError(f"Greenfield case `{_case_id(case)}` lacks one supported model profile")
    return profiles[0]


def model_profile_environment(
    profile: str,
    environ: Mapping[str, str],
    *,
    unavailable_provider_bin: str = "",
) -> dict[str, str]:
    """Return an isolated real provider request for one pinned profile."""

    if profile not in (*MODEL_PROFILES, UNAVAILABLE_PROVIDER_PROFILE):
        raise ValueError(f"unsupported Greenfield model profile: {profile}")
    contract = get_greenfield_model_profile(profile)
    values = dict(environ)
    for key in _PROFILE_ENV_KEYS:
        values.pop(key, None)
    values["ODYLITH_GREENFIELD_MODEL_PROFILE"] = profile
    values.update(
        {
            "ODYLITH_REASONING_MODE": "auto",
            "ODYLITH_REASONING_PROVIDER": contract.provider,
            "ODYLITH_REASONING_MODEL": contract.model,
            "ODYLITH_REASONING_SCOPE_CAP": "1",
            "ODYLITH_REASONING_TIMEOUT_SECONDS": _seconds_token(contract.model_timeout_seconds),
            "ODYLITH_REASONING_CODEX_REASONING_EFFORT": contract.reasoning_effort,
        }
    )
    if profile == UNAVAILABLE_PROVIDER_PROFILE:
        missing = str(unavailable_provider_bin or "").strip()
        if not missing:
            missing = "/nonexistent/odylith-greenfield-codex-provider"
        missing_path = Path(missing).expanduser()
        if missing_path.exists():
            raise ValueError("unavailable-provider proof requires a missing provider executable")
        values["ODYLITH_REASONING_CODEX_BIN"] = str(missing_path)
    return values


def model_profile_evidence(
    profile: str,
    environ: Mapping[str, str],
    *,
    observed: Mapping[str, Any] | None = None,
    stage_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind configured and retained request evidence to one composite profile."""

    contract = get_greenfield_model_profile(profile)
    configured = {
        "provider": str(environ.get("ODYLITH_REASONING_PROVIDER") or ""),
        "model": str(environ.get("ODYLITH_REASONING_MODEL") or ""),
        "reasoning_effort": str(environ.get("ODYLITH_REASONING_CODEX_REASONING_EFFORT") or ""),
        "maximum_model_timeout_seconds": _float_value(
            environ.get("ODYLITH_REASONING_TIMEOUT_SECONDS")
        ),
    }
    observation = dict(observed or {})
    issues: list[str] = []
    configured_profile_id = str(environ.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or "").strip()
    if configured_profile_id != profile:
        issues.append("configured profile identity does not match the assigned release profile")
    if configured["provider"].strip().casefold() != contract.provider:
        issues.append("configured provider does not match the assigned release profile")
    if configured["model"].strip() != contract.model:
        issues.append("configured model does not match the assigned release profile")
    if configured["reasoning_effort"].strip().casefold() != contract.reasoning_effort:
        issues.append("configured reasoning effort does not match the assigned release profile")
    if configured["maximum_model_timeout_seconds"] != contract.model_timeout_seconds:
        issues.append("configured timeout does not match the assigned release profile")
    if observation:
        if str(observation.get("profile_id") or "") != profile:
            issues.append("sealed profile identity does not match the assigned release profile")
        issues.extend(
            greenfield_model_profile_observation_issues(
                profile_id=profile,
                provider=str(observation.get("provider") or ""),
                model=str(observation.get("model") or ""),
                reasoning_effort=str(observation.get("reasoning_effort") or ""),
                effective_timeout_seconds=observation.get("effective_timeout_seconds"),
                authoring_tier=str(observation.get("authoring_tier") or ""),
            )
        )
    elif profile != UNAVAILABLE_PROVIDER_PROFILE:
        issues.append("sealed model profile observation is missing")
    stage_summary = (
        _model_stage_observation_evidence(
            profile,
            sealed_observation=observation,
            stage_observation=dict(stage_observation or {}),
        )
        if profile != UNAVAILABLE_PROVIDER_PROFILE
        else None
    )
    if stage_summary is not None:
        issues.extend(str(issue) for issue in stage_summary["issues"])
    return {
        "contract_version": GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION,
        "assignment_version": MODEL_PROFILE_ASSIGNMENT_VERSION,
        "profile_id": profile,
        "repair_tier": contract.repair_tier,
        "consumer_budget_seconds": contract.consumer_budget_seconds,
        "lower_capability": contract.lower_capability,
        "semantic_authority": "typed_evidence_and_preconfirm_tribunal",
        "sealed_request_role": "initial_authoring",
        "lower_capability_scope": (
            "initial_authoring" if contract.lower_capability else "not_applicable"
        ),
        "expected_source_review": {
            "provider": contract.provider,
            "model": contract.source_review_model,
            "reasoning_effort": contract.source_review_reasoning_effort,
        },
        "configured": configured,
        "observed": observation,
        "stage_observation": (
            dict(stage_observation or {})
            if profile != UNAVAILABLE_PROVIDER_PROFILE
            else None
        ),
        "stage_observation_summary": stage_summary,
        "status": (
            "passed"
            if observation and not issues
            else "unobserved"
            if profile == UNAVAILABLE_PROVIDER_PROFILE and not observation
            else "failed"
        ),
        "issues": issues,
        "provider_unavailability_configured": profile == UNAVAILABLE_PROVIDER_PROFILE,
        "expected_failure_behavior": (
            "fail closed without a staged transaction or governed writes"
            if profile == UNAVAILABLE_PROVIDER_PROFILE
            else "not_applicable"
        ),
    }


def model_stage_observation_issues(
    profile: str,
    *,
    observed: Mapping[str, Any],
    stage_observation: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return fail-closed issues for one retained composite request observation."""

    return tuple(
        str(issue)
        for issue in _model_stage_observation_evidence(
            profile,
            sealed_observation=observed,
            stage_observation=stage_observation,
        )["issues"]
    )


def _model_stage_observation_evidence(
    profile: str,
    *,
    sealed_observation: Mapping[str, Any],
    stage_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate sanitized per-call proof against one sealed shared model window."""

    contract = get_greenfield_model_profile(profile)
    retained = dict(stage_observation or {})
    issues: list[str] = []
    if not retained:
        issues.append("retained model authoring observation is missing")
    if str(retained.get("version") or "") != "odylith.greenfield.model-proof-observation.v2":
        issues.append("retained model authoring observation version is invalid")
    if str(retained.get("authoring_version") or "") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("retained model authoring version is invalid")

    response = _mapping(retained.get("response"))
    result = _mapping(response.get("result"))
    response_kind = str(result.get("status") or "")
    if str(response.get("version") or "") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("retained model response version is invalid")
    if response_kind not in {"authored", "clarification_required"}:
        issues.append("retained model response kind is invalid")

    call_count = retained.get("semantic_model_call_count")
    if type(call_count) is not int:  # bool is not an admissible call count.
        issues.append("retained semantic model call count is invalid")
        normalized_call_count = 0
    else:
        normalized_call_count = call_count

    sealed_timeout = _positive_float(sealed_observation.get("effective_timeout_seconds"))
    if sealed_timeout is None:
        issues.append("sealed shared model window is invalid")

    initial = _mapping(retained.get("initial_authoring"))
    if not initial:
        issues.append("retained initial authoring observation is missing")
    initial_summary = _request_role_summary(initial)
    issues.extend(
        _request_role_issues(
            profile,
            request_role="initial_authoring",
            observation=initial,
        )
    )
    initial_timeout = _positive_float(initial.get("timeout_seconds"))
    initial_elapsed = _positive_float(initial.get("elapsed_seconds"))
    if initial_timeout is None:
        issues.append("retained initial authoring timeout is invalid")
    if initial_elapsed is None:
        issues.append("retained initial authoring elapsed time is invalid")
    if sealed_timeout is not None and initial_timeout is not None:
        expected_initial_timeout = sealed_timeout - contract.source_review_reserve_seconds
        if expected_initial_timeout <= 0.0 or not _same_seconds(
            initial_timeout, expected_initial_timeout
        ):
            issues.append("retained initial authoring timeout does not preserve the review reserve")
    if (
        initial_timeout is not None
        and initial_elapsed is not None
        and initial_elapsed > initial_timeout + _TIME_TOLERANCE_SECONDS
    ):
        issues.append("retained initial authoring elapsed time exceeds its timeout")

    source_review = _mapping(retained.get("source_review"))
    request_roles: dict[str, Any] = {"initial_authoring": initial_summary}
    if response_kind == "authored":
        if normalized_call_count != 2:
            issues.append("authored model response must record exactly two semantic calls")
    elif response_kind == "clarification_required" and normalized_call_count not in {1, 2}:
        issues.append("clarification model response must record one or two semantic calls")

    has_review = response_kind == "authored" or normalized_call_count == 2
    if has_review:
        initial_response = _mapping(retained.get("initial_response"))
        initial_result = _mapping(initial_response.get("result"))
        if not initial_response:
            issues.append("reviewed model response is missing its initial candidate")
        elif (
            str(initial_response.get("version") or "")
            != GREENFIELD_INTENT_AUTHORING_VERSION
            or str(initial_result.get("status") or "") != "authored"
        ):
            issues.append("retained initial candidate is not an authored response")
        if not source_review:
            issues.append("reviewed model response is missing its source review")
        review_summary = _request_role_summary(source_review)
        request_roles["source_review"] = review_summary
        issues.extend(
            _request_role_issues(
                profile,
                request_role="source_review",
                observation=source_review,
            )
        )
        review_timeout = _positive_float(source_review.get("timeout_seconds"))
        review_elapsed = _positive_float(source_review.get("elapsed_seconds"))
        if review_timeout is None:
            issues.append("retained source review timeout is invalid")
        if review_elapsed is None:
            issues.append("retained source review elapsed time is invalid")
        if (
            review_timeout is not None
            and review_elapsed is not None
            and review_elapsed > review_timeout + _TIME_TOLERANCE_SECONDS
        ):
            issues.append("retained source review elapsed time exceeds its timeout")
        if sealed_timeout is not None and initial_elapsed is not None and review_timeout is not None:
            remaining = sealed_timeout - initial_elapsed
            if review_timeout > remaining + _TIME_TOLERANCE_SECONDS:
                issues.append("retained source review timeout exceeds the remaining shared window")
        if sealed_timeout is not None and initial_elapsed is not None and review_elapsed is not None:
            if initial_elapsed + review_elapsed > sealed_timeout + _TIME_TOLERANCE_SECONDS:
                issues.append("retained semantic calls exceed the sealed shared model window")

        review_response = _mapping(source_review.get("response"))
        review_result = _mapping(review_response.get("result"))
        if set(review_response) != {"result"} or not review_result:
            issues.append("retained source review decision is invalid")
        elif response_kind == "authored":
            if set(review_result) != {"corrections"} or not isinstance(
                review_result.get("corrections"), list
            ):
                issues.append("authored source review decision is invalid")
        elif review_result != result:
            issues.append("clarification source review decision does not match the final response")
    elif response_kind == "clarification_required" and normalized_call_count == 1:
        if "source_review" in retained:
            issues.append("one-call clarification must not record a source review")
        if "initial_response" in retained:
            issues.append("one-call clarification must not record an intermediate candidate")

    return {
        "observation_version": str(retained.get("version") or ""),
        "authoring_version": str(retained.get("authoring_version") or ""),
        "response_kind": response_kind,
        "semantic_model_call_count": normalized_call_count,
        "request_roles": request_roles,
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


def profile_counts(cases: Sequence[GreenfieldMatrixCase]) -> dict[str, int]:
    counts = {profile: 0 for profile in MODEL_PROFILES}
    for case in cases:
        counts[case_model_profile(case)] += 1
    return counts


def profile_coverage(cases: Sequence[GreenfieldMatrixCase]) -> dict[str, dict[str, dict[str, int]]]:
    coverage: dict[str, dict[str, dict[str, int]]] = {
        "expectation": {},
        "input_style": {},
    }
    for case in cases:
        profile = case_model_profile(case)
        values = {
            "expectation": case_expectation(case),
            "input_style": str(case.input_style or "unspecified"),
        }
        for dimension, value in values.items():
            counts = coverage[dimension].setdefault(
                value,
                {item: 0 for item in MODEL_PROFILES},
            )
            counts[profile] += 1
    return coverage


def _with_profile(case: GreenfieldMatrixCase, profile: str) -> GreenfieldMatrixCase:
    tags = tuple(tag for tag in case.tags if not str(tag).startswith(_TAG_PREFIX))
    return replace(case, tags=(*tags, f"{_TAG_PREFIX}{profile}"))


def _explicit_profiles(case: GreenfieldMatrixCase) -> tuple[str, ...]:
    return tuple(
        str(tag).partition(":")[2]
        for tag in case.tags
        if str(tag).startswith(_TAG_PREFIX)
    )


def _case_id(case: GreenfieldMatrixCase) -> str:
    return str(case.case_id or case.slug).strip()


def _seconds_token(value: float) -> str:
    token = float(value)
    return str(int(token)) if token.is_integer() else str(token)


def _float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _positive_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def _same_seconds(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=0.0,
        abs_tol=_TIME_TOLERANCE_SECONDS,
    )


def _request_role_issues(
    profile: str,
    *,
    request_role: str,
    observation: Mapping[str, Any],
) -> tuple[str, ...]:
    issues: list[str] = []
    if str(observation.get("profile_id") or "") != profile:
        issues.append(f"retained {request_role} profile identity is invalid")
    if str(observation.get("request_role") or "") != request_role:
        issues.append(f"retained {request_role} request role is invalid")
    provider = _mapping(observation.get("provider"))
    if not provider:
        issues.append(f"retained {request_role} provider metadata is missing")
    if str(provider.get("code") or "").strip():
        issues.append(f"retained {request_role} provider metadata records a failure")
    model = str(observation.get("model") or "")
    effort = str(observation.get("reasoning_effort") or "")
    if model != str(provider.get("model") or ""):
        issues.append(f"retained {request_role} model conflicts with provider metadata")
    if effort.casefold() != str(provider.get("reasoning_effort") or "").casefold():
        issues.append(
            f"retained {request_role} reasoning effort conflicts with provider metadata"
        )
    issues.extend(
        greenfield_model_profile_observation_issues(
            profile_id=profile,
            provider=str(provider.get("provider") or ""),
            model=model,
            reasoning_effort=effort,
            effective_timeout_seconds=observation.get("timeout_seconds"),
            request_role=request_role,
        )
    )
    return tuple(issues)


def _request_role_summary(observation: Mapping[str, Any]) -> dict[str, Any]:
    provider = _mapping(observation.get("provider"))
    return {
        "profile_id": str(observation.get("profile_id") or ""),
        "request_role": str(observation.get("request_role") or ""),
        "provider": str(provider.get("provider") or ""),
        "model": str(observation.get("model") or ""),
        "reasoning_effort": str(observation.get("reasoning_effort") or ""),
        "timeout_seconds": _float_value(observation.get("timeout_seconds")),
        "elapsed_seconds": _float_value(observation.get("elapsed_seconds")),
    }


__all__ = [
    "MODEL_PROFILES",
    "MODEL_PROFILE_ASSIGNMENT_SEED",
    "MODEL_PROFILE_ASSIGNMENT_VERSION",
    "DEEP_PROFILE_ID",
    "RESCUE_PROFILE_ID",
    "STANDARD_PROFILE_ID",
    "UNAVAILABLE_PROVIDER_PROFILE",
    "assign_model_profiles",
    "case_model_profile",
    "model_profile_environment",
    "model_profile_evidence",
    "model_stage_observation_issues",
    "profile_coverage",
    "profile_counts",
]
