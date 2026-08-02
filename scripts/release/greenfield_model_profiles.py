"""Frozen behavior profiles for model-agnostic Greenfield release proof."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
import shutil
from typing import Any

from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_expectation


MODEL_PROFILE_ASSIGNMENT_VERSION = "case-id-balanced-sha256-v1"
MODEL_PROFILE_ASSIGNMENT_SEED = "f1e5a66a5cce578b0bd9f56d96f08887358632627231769667c432933b9dfe6f"
MODEL_PROFILES = (
    "provider-free-standard-v1",
    "bounded-reasoning-standard-v1",
    "lower-capability-safe-v1",
)
_TAG_PREFIX = "model-profile:"
_PROFILE_ENV_KEYS = (
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


def model_profile_environment(profile: str, environ: Mapping[str, str]) -> dict[str, str]:
    """Return an isolated provider posture for one release behavior profile."""

    if profile not in MODEL_PROFILES:
        raise ValueError(f"unsupported Greenfield model profile: {profile}")
    values = dict(environ)
    for key in _PROFILE_ENV_KEYS:
        values.pop(key, None)
    values["ODYLITH_GREENFIELD_MODEL_PROFILE"] = profile
    if profile == "provider-free-standard-v1":
        values["ODYLITH_REASONING_MODE"] = "disabled"
    elif profile == "bounded-reasoning-standard-v1":
        values.update(
            {
                "ODYLITH_REASONING_MODE": "auto",
                "ODYLITH_REASONING_PROVIDER": "codex-cli",
                "ODYLITH_REASONING_SCOPE_CAP": "1",
                "ODYLITH_REASONING_TIMEOUT_SECONDS": "12",
                "ODYLITH_REASONING_CODEX_REASONING_EFFORT": "low",
            }
        )
    else:
        unavailable_provider = shutil.which("false") or "/usr/bin/false"
        values.update(
            {
                "ODYLITH_REASONING_MODE": "auto",
                "ODYLITH_REASONING_PROVIDER": "codex-cli",
                "ODYLITH_REASONING_SCOPE_CAP": "1",
                "ODYLITH_REASONING_TIMEOUT_SECONDS": "1",
                "ODYLITH_REASONING_CODEX_BIN": unavailable_provider,
                "ODYLITH_REASONING_CODEX_REASONING_EFFORT": "low",
            }
        )
    return values


def model_profile_evidence(profile: str, environ: Mapping[str, str]) -> dict[str, Any]:
    """Describe the configured posture without claiming unobserved provider behavior."""

    return {
        "assignment_version": MODEL_PROFILE_ASSIGNMENT_VERSION,
        "profile": profile,
        "semantic_authority": "typed_evidence_and_preconfirm_tribunal",
        "provider_mode": str(environ.get("ODYLITH_REASONING_MODE") or ""),
        "provider": str(environ.get("ODYLITH_REASONING_PROVIDER") or "none"),
        "provider_unavailability_configured": profile == "lower-capability-safe-v1",
        "provider_failure_observed": False,
        "safe_fallback_observed": False,
        "expected_failure_behavior": (
            "source-anchored repair or fail closed without invented facts"
            if profile == "lower-capability-safe-v1"
            else "not_applicable"
        ),
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


__all__ = [
    "MODEL_PROFILES",
    "MODEL_PROFILE_ASSIGNMENT_SEED",
    "MODEL_PROFILE_ASSIGNMENT_VERSION",
    "assign_model_profiles",
    "case_model_profile",
    "model_profile_environment",
    "model_profile_evidence",
    "profile_coverage",
    "profile_counts",
]
