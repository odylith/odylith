"""Assign and prove pinned one-authority Greenfield release profiles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
import math
from pathlib import Path
from typing import Any

from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_ARGUMENT_COUNT
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_RECEIPT_VERSION
from greenfield_matrix_host_candidate import HOST_NATIVE_ARGV_SHAPE_SHA256
from greenfield_matrix_host_candidate import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_expectation
from greenfield_retained_candidate_proof import (
    retained_canonical_candidate_hash_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_json import (
    encode_greenfield_model_value,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    UNAVAILABLE_PROVIDER_PROFILE_ID,
    declared_greenfield_model_profile_ids,
    get_greenfield_model_profile,
    lower_capability_control_greenfield_model_profile_ids,
    supported_greenfield_model_profile_ids,
)


MODEL_PROFILE_ASSIGNMENT_VERSION = "release-success-single-authority-v5"
MODEL_PROFILE_ASSIGNMENT_SEED = (
    "f1e5a66a5cce578b0bd9f56d96f08887358632627231769667c432933b9dfe6f"
)
MODEL_PROFILES = supported_greenfield_model_profile_ids()
LOWER_CAPABILITY_CONTROL_PROFILES = (
    lower_capability_control_greenfield_model_profile_ids()
)
DECLARED_MODEL_PROFILES = declared_greenfield_model_profile_ids()
UNAVAILABLE_PROVIDER_PROFILE = UNAVAILABLE_PROVIDER_PROFILE_ID
_ASSIGNABLE_PROFILE_IDS = (*MODEL_PROFILES, *LOWER_CAPABILITY_CONTROL_PROFILES)
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
_HOST_STAGE_FIELDS = frozenset(
    {
        "version",
        "status",
        "host_invocations",
        "contract_command_invocations",
        "proposal_command_invocations",
        "runtime_semantic_model_call_count",
        "post_receipt_provider_invocations",
        "model_profile_id",
        "host_request",
        "candidate_temp_cleaned",
        "host_workspace_cleaned",
        "stage",
        "contract_returncode",
        "contract_sha256",
        "source_sha256",
        "candidate_schema_sha256",
        "host_returncode",
        "host_stdout_bytes",
        "host_stderr_bytes",
        "response_kind",
        "raw_candidate_sha256",
        "host_output_sha256",
        "host_output_bytes",
        "candidate_temp_outside_repo",
        "proposal_returncode",
        "proposal_stdout_sha256",
        "proposal_stderr_sha256",
        "proposal_mode",
        "elapsed_seconds",
    }
)


def _is_exact_int(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def assign_model_profiles(
    cases: Sequence[GreenfieldMatrixCase],
) -> tuple[GreenfieldMatrixCase, ...]:
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
        if len(explicit) > 1 or (
            explicit and explicit[0] not in _ASSIGNABLE_PROFILE_IDS
        ):
            raise ValueError(
                f"Greenfield case `{_case_id(case)}` has an invalid model profile"
            )
        if explicit:
            selected = explicit[0]
            if (
                selected in LOWER_CAPABILITY_CONTROL_PROFILES
                and stratum != "clarification_required"
            ):
                raise ValueError(
                    f"Greenfield control case `{_case_id(case)}` must require clarification"
                )
            assignments[index] = selected
            if selected in MODEL_PROFILES:
                counts[selected] += 1
                stratum_counts[stratum][selected] += 1
                input_style_counts[input_style][selected] += 1
            continue
        identity = _case_id(case)
        digest = hashlib.sha256(
            f"{MODEL_PROFILE_ASSIGNMENT_SEED}:{identity}".encode("utf-8")
        ).hexdigest()
        pending[stratum].append((digest, index))

    for stratum, stratum_rows in sorted(pending.items()):
        for _digest, index in sorted(stratum_rows):
            input_style = str(rows[index].input_style or "unspecified")
            selected = min(
                MODEL_PROFILES,
                key=lambda item: (
                    stratum_counts[stratum][item],
                    input_style_counts[input_style][item],
                    counts[item],
                    MODEL_PROFILES.index(item),
                ),
            )
            assignments[index] = selected
            counts[selected] += 1
            stratum_counts[stratum][selected] += 1
            input_style_counts[input_style][selected] += 1
    return tuple(
        _with_profile(case, assignments[index])
        for index, case in enumerate(rows)
    )


def case_model_profile(case: GreenfieldMatrixCase) -> str:
    """Return the one validated profile assigned to a release case."""

    profiles = _explicit_profiles(case)
    if len(profiles) != 1 or profiles[0] not in _ASSIGNABLE_PROFILE_IDS:
        raise ValueError(
            f"Greenfield case `{_case_id(case)}` lacks one supported model profile"
        )
    if (
        profiles[0] in LOWER_CAPABILITY_CONTROL_PROFILES
        and case_expectation(case) != "clarification_required"
    ):
        raise ValueError(
            f"Greenfield control case `{_case_id(case)}` must require clarification"
        )
    return profiles[0]


def model_profile_environment(
    profile: str,
    environ: Mapping[str, str],
    *,
    unavailable_provider_bin: str = "",
) -> dict[str, str]:
    """Return the isolated host-authority configuration for one pinned profile."""

    if profile not in (*DECLARED_MODEL_PROFILES, UNAVAILABLE_PROVIDER_PROFILE):
        raise ValueError(f"unsupported Greenfield model profile: {profile}")
    contract = get_greenfield_model_profile(profile)
    values = dict(environ)
    for key in _PROFILE_ENV_KEYS:
        values.pop(key, None)
    values.update(
        {
            "ODYLITH_GREENFIELD_MODEL_PROFILE": profile,
            "ODYLITH_REASONING_MODE": "auto",
            "ODYLITH_REASONING_PROVIDER": contract.provider,
            "ODYLITH_REASONING_MODEL": contract.model,
            "ODYLITH_REASONING_SCOPE_CAP": "1",
            "ODYLITH_REASONING_TIMEOUT_SECONDS": _seconds_token(
                contract.model_timeout_seconds
            ),
            "ODYLITH_REASONING_CODEX_REASONING_EFFORT": contract.reasoning_effort,
        }
    )
    if profile == UNAVAILABLE_PROVIDER_PROFILE:
        missing = str(unavailable_provider_bin or "").strip()
        if not missing:
            missing = "/nonexistent/odylith-greenfield-codex-provider"
        missing_path = Path(missing).expanduser()
        if missing_path.exists():
            raise ValueError(
                "unavailable-provider proof requires a missing provider executable"
            )
        values["ODYLITH_REASONING_CODEX_BIN"] = str(missing_path)
    return values


def model_profile_evidence(
    profile: str,
    environ: Mapping[str, str],
    *,
    observed: Mapping[str, Any] | None = None,
    stage_observation: Mapping[str, Any] | None = None,
    raw_candidate: Mapping[str, Any] | None = None,
    expected_source: str = "",
) -> dict[str, Any]:
    """Bind one host argv, retained candidate and zero-call runtime receipt."""

    contract = get_greenfield_model_profile(profile)
    configured = {
        "provider": str(environ.get("ODYLITH_REASONING_PROVIDER") or ""),
        "model": str(environ.get("ODYLITH_REASONING_MODEL") or ""),
        "reasoning_effort": str(
            environ.get("ODYLITH_REASONING_CODEX_REASONING_EFFORT") or ""
        ),
        "maximum_model_timeout_seconds": _float_value(
            environ.get("ODYLITH_REASONING_TIMEOUT_SECONDS")
        ),
    }
    issues = _configured_profile_issues(
        profile=profile,
        environ=environ,
        configured=configured,
    )
    expected_source_sha256 = (
        hashlib.sha256(expected_source.encode("utf-8")).hexdigest()
        if expected_source
        else ""
    )
    stage_summary = _host_stage_evidence(
        profile,
        sealed_observation=_mapping(observed),
        stage_observation=_mapping(stage_observation),
        raw_candidate=_mapping(raw_candidate),
        expected_source=expected_source,
        expected_source_sha256=expected_source_sha256,
    )
    issues.extend(str(issue) for issue in stage_summary["issues"])
    issues = list(dict.fromkeys(issues))
    return {
        "contract_version": GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION,
        "assignment_version": MODEL_PROFILE_ASSIGNMENT_VERSION,
        "profile_id": profile,
        "repair_tier": contract.repair_tier,
        "performance_target_seconds": contract.performance_target_seconds,
        "operational_timeout_seconds": contract.operational_timeout_seconds,
        "lower_capability": contract.lower_capability,
        "semantic_authority": "active_host_single_authority",
        "sealed_request_roles": ["host_candidate"],
        "lower_capability_scope": (
            "host_candidate" if contract.lower_capability else "not_applicable"
        ),
        "host_semantic_model_calls": 1,
        "runtime_semantic_model_calls_after_candidate_receipt": 0,
        "post_receipt_provider_invocations": 0,
        "configured": configured,
        "expected_source_sha256": expected_source_sha256,
        "observed": dict(observed or {}),
        "stage_observation": dict(stage_observation or {}),
        "stage_observation_summary": stage_summary,
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


def _configured_profile_issues(
    *,
    profile: str,
    environ: Mapping[str, str],
    configured: Mapping[str, Any],
) -> list[str]:
    contract = get_greenfield_model_profile(profile)
    issues: list[str] = []
    if str(environ.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or "").strip() != profile:
        issues.append("configured profile identity does not match the assigned release profile")
    if str(configured.get("provider") or "").casefold() != contract.provider:
        issues.append("configured provider does not match the assigned release profile")
    if configured.get("model") != contract.model:
        issues.append("configured model does not match the assigned release profile")
    if str(configured.get("reasoning_effort") or "").casefold() != contract.reasoning_effort:
        issues.append("configured reasoning effort does not match the assigned release profile")
    if configured.get("maximum_model_timeout_seconds") != contract.model_timeout_seconds:
        issues.append("configured timeout does not match the assigned release profile")
    return issues


def _host_stage_evidence(
    profile: str,
    *,
    sealed_observation: Mapping[str, Any],
    stage_observation: Mapping[str, Any],
    raw_candidate: Mapping[str, Any],
    expected_source: str,
    expected_source_sha256: str,
) -> dict[str, Any]:
    issues: list[str] = []
    stage = _mapping(stage_observation)
    sealed = _mapping(sealed_observation)
    if set(stage) != _HOST_STAGE_FIELDS:
        issues.append("retained host stage has missing or unsupported fields")
    if stage.get("version") != HOST_NATIVE_MATRIX_OBSERVATION_VERSION:
        issues.append("retained host stage version is invalid")
    if stage.get("status") != "passed":
        issues.append("retained host stage did not pass")
    for field in (
        "host_invocations",
        "contract_command_invocations",
        "proposal_command_invocations",
    ):
        if not _is_exact_int(stage.get(field), 1):
            issues.append(f"retained host stage {field} must equal one")
    for field in (
        "runtime_semantic_model_call_count",
        "post_receipt_provider_invocations",
    ):
        if not _is_exact_int(stage.get(field), 0):
            issues.append(f"retained host stage {field} must equal zero")
    if stage.get("model_profile_id") != profile:
        issues.append("retained host stage identifies a different model profile")
    issues.extend(host_native_argv_receipt_issues(profile, stage.get("host_request")))
    if expected_source_sha256 and stage.get("source_sha256") != expected_source_sha256:
        issues.append("retained host stage source hash does not match evaluated source")
    for field in (
        "contract_sha256",
        "source_sha256",
        "candidate_schema_sha256",
        "raw_candidate_sha256",
        "host_output_sha256",
        "proposal_stdout_sha256",
        "proposal_stderr_sha256",
    ):
        if not _is_sha256(stage.get(field)):
            issues.append(f"retained host stage {field} is invalid")
    if stage.get("contract_returncode") != 0 or stage.get("host_returncode") != 0:
        issues.append("retained host stage has a failed prerequisite command")
    if stage.get("proposal_returncode") != 0:
        issues.append("retained host stage proposal return code is invalid")
    if stage.get("response_kind") not in {"authored", "clarification_required"}:
        issues.append("retained host stage response kind is invalid")
    if stage.get("proposal_mode") not in {
        "product_create_transaction",
        "clarification_required",
    }:
        issues.append("retained host stage proposal mode is invalid")
    if stage.get("candidate_temp_outside_repo") is not True:
        issues.append("retained host candidate path was not outside the repository")
    if stage.get("candidate_temp_cleaned") is not True:
        issues.append("retained host candidate file was not cleaned")
    if stage.get("host_workspace_cleaned") is not True:
        issues.append("retained host workspace was not cleaned")

    if stage.get("response_kind") == "clarification_required":
        if stage.get("proposal_mode") != "clarification_required":
            issues.append("retained host clarification proposal mode is invalid")
        if sealed:
            issues.append("clarification must not claim a sealed candidate receipt")
        if raw_candidate.get("version") != HOST_CANDIDATE_FORMAT_VERSION or _mapping(
            raw_candidate.get("result")
        ).get("status") != "clarification_required":
            issues.append("retained host clarification candidate is invalid")
        try:
            raw_sha256 = hashlib.sha256(
                encode_greenfield_model_value(raw_candidate)
            ).hexdigest()
        except (RuntimeError, TypeError, ValueError):
            raw_sha256 = ""
            issues.append("retained host clarification candidate cannot be encoded")
        if stage.get("raw_candidate_sha256") != raw_sha256:
            issues.append("retained host clarification hash does not match host output")
        retained_hash_summary = {
            "status": "passed" if raw_sha256 else "failed",
            "raw_candidate_sha256": raw_sha256,
            "canonical_projection_verified": False,
            "issues": [],
        }
    else:
        if stage.get("proposal_mode") != "product_create_transaction":
            issues.append("retained authored proposal mode is invalid")
        expected_sealed_fields = {
            "origin",
            "host_candidate",
            "runtime_semantic_model_call_count",
        }
        if set(sealed) != expected_sealed_fields:
            issues.append("sealed model observation has missing or unsupported fields")
        if sealed.get("origin") != "host_native":
            issues.append("sealed model observation does not identify host authority")
        if not _is_exact_int(sealed.get("runtime_semantic_model_call_count"), 0):
            issues.append("sealed runtime semantic model call count is not zero")
        receipt = _mapping(sealed.get("host_candidate"))
        if receipt.get("version") != HOST_CANDIDATE_RECEIPT_VERSION:
            issues.append("sealed host candidate receipt version is invalid")
        if receipt.get("contract_version") != HOST_CANDIDATE_CONTRACT_VERSION:
            issues.append("sealed host candidate contract version is invalid")
        if receipt.get("canonical_version") != GREENFIELD_INTENT_AUTHORING_VERSION:
            issues.append("sealed host candidate canonical version is invalid")
        if stage.get("raw_candidate_sha256") != receipt.get("raw_candidate_sha256"):
            issues.append("retained raw candidate does not match the sealed receipt")
        retained_hash_summary = retained_canonical_candidate_hash_evidence(
            raw_candidate=raw_candidate,
            receipt=receipt,
            evidence_text=expected_source,
        )
    issues.extend(str(issue) for issue in retained_hash_summary["issues"])
    return {
        "origin": "host_native",
        "response_kind": str(stage.get("response_kind") or ""),
        "request_roles": {
            "host_candidate": dict(_mapping(stage.get("host_request")))
        },
        "host_semantic_model_calls": 1,
        "runtime_semantic_model_calls_after_candidate_receipt": 0,
        "post_receipt_provider_invocations": 0,
        "retained_candidate_hash_summary": {
            key: value
            for key, value in retained_hash_summary.items()
            if key != "issues"
        },
        "status": "passed" if not issues else "failed",
        "issues": list(dict.fromkeys(issues)),
    }


def host_native_argv_receipt_issues(profile: str, value: Any) -> tuple[str, ...]:
    """Validate the privacy-safe receipt for the one direct host invocation."""

    receipt = _mapping(value)
    expected_fields = {
        "version",
        "executable_sha256",
        "argument_count",
        "model",
        "reasoning_effort",
        "output_schema_present",
        "argv_shape_sha256",
    }
    issues: list[str] = []
    if set(receipt) != expected_fields:
        issues.append("retained host argv receipt has missing or unsupported fields")
    if receipt.get("version") != HOST_NATIVE_ARGV_RECEIPT_VERSION:
        issues.append("retained host argv receipt version is invalid")
    if not _is_sha256(receipt.get("executable_sha256")):
        issues.append("retained host executable hash is invalid")
    if receipt.get("argument_count") != HOST_NATIVE_ARGV_ARGUMENT_COUNT:
        issues.append("retained host argv argument count is invalid")
    contract = get_greenfield_model_profile(profile)
    if receipt.get("model") != contract.model:
        issues.append("retained host model does not match the assigned profile")
    if str(receipt.get("reasoning_effort") or "").casefold() != contract.reasoning_effort:
        issues.append("retained host reasoning effort does not match the assigned profile")
    if receipt.get("output_schema_present") is not True:
        issues.append("retained host argv omitted the output schema")
    if receipt.get("argv_shape_sha256") != HOST_NATIVE_ARGV_SHAPE_SHA256:
        issues.append("retained host argv shape is invalid")
    return tuple(issues)


def host_native_clarification_stage_observation_issues(
    profile: str,
    *,
    stage_observation: Mapping[str, Any],
    expected_source_sha256: str,
) -> tuple[str, ...]:
    """Validate that a one-call host clarification reached deterministic admission."""

    stage = _mapping(stage_observation)
    issues: list[str] = []
    if stage.get("version") != HOST_NATIVE_MATRIX_OBSERVATION_VERSION:
        issues.append("retained host clarification stage version is invalid")
    if stage.get("response_kind") != "clarification_required":
        issues.append("retained host clarification response kind is invalid")
    if stage.get("proposal_mode") != "clarification_required":
        issues.append("retained host clarification proposal mode is invalid")
    if stage.get("source_sha256") != expected_source_sha256:
        issues.append("retained host clarification source hash is invalid")
    if not _is_exact_int(stage.get("host_invocations"), 1):
        issues.append("retained host clarification did not use exactly one host call")
    if not _is_exact_int(stage.get("runtime_semantic_model_call_count"), 0):
        issues.append("retained host clarification used a runtime semantic call")
    if not _is_exact_int(stage.get("post_receipt_provider_invocations"), 0):
        issues.append("retained host clarification used a post-receipt provider call")
    issues.extend(host_native_argv_receipt_issues(profile, stage.get("host_request")))
    return tuple(dict.fromkeys(issues))


def profile_counts(cases: Sequence[GreenfieldMatrixCase]) -> dict[str, int]:
    counts = {profile: 0 for profile in MODEL_PROFILES}
    for case in cases:
        profile = case_model_profile(case)
        counts[profile] = counts.get(profile, 0) + 1
    return counts


def profile_coverage(
    cases: Sequence[GreenfieldMatrixCase],
) -> dict[str, dict[str, dict[str, int]]]:
    coverage: dict[str, dict[str, dict[str, int]]] = {
        "expectation": {},
        "input_style": {},
    }
    for case in cases:
        profile = case_model_profile(case)
        for dimension, value in {
            "expectation": case_expectation(case),
            "input_style": str(case.input_style or "unspecified"),
        }.items():
            counts = coverage[dimension].setdefault(
                value,
                {item: 0 for item in MODEL_PROFILES},
            )
            counts[profile] = counts.get(profile, 0) + 1
    return coverage


def _with_profile(
    case: GreenfieldMatrixCase,
    profile: str,
) -> GreenfieldMatrixCase:
    tags = tuple(
        tag for tag in case.tags if not str(tag).startswith(_TAG_PREFIX)
    )
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
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_sha256(value: Any) -> bool:
    normalized = str(value or "").strip().casefold()
    return len(normalized) == 64 and all(
        character in "0123456789abcdef" for character in normalized
    )


__all__ = [
    "MODEL_PROFILES",
    "DECLARED_MODEL_PROFILES",
    "LOWER_CAPABILITY_CONTROL_PROFILES",
    "MODEL_PROFILE_ASSIGNMENT_SEED",
    "MODEL_PROFILE_ASSIGNMENT_VERSION",
    "DEEP_PROFILE_ID",
    "RESCUE_PROFILE_ID",
    "STANDARD_PROFILE_ID",
    "UNAVAILABLE_PROVIDER_PROFILE",
    "assign_model_profiles",
    "case_model_profile",
    "host_native_argv_receipt_issues",
    "host_native_clarification_stage_observation_issues",
    "model_profile_environment",
    "model_profile_evidence",
    "profile_coverage",
    "profile_counts",
]
