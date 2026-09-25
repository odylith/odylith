"""Assign and configure the pinned Greenfield release model profiles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_expectation
from greenfield_matrix_host_candidate import HOST_NATIVE_MATRIX_OBSERVATION_VERSION
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
    GreenfieldModelAuthoredIntent,
    GreenfieldModelAuthoringError,
    validate_greenfield_authoring_response,
)
from odylith.runtime.domain_intelligence.greenfield_participant_first_authoring import (
    GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION,
    join_frozen_greenfield_participants,
    resolve_greenfield_participant_selection,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    candidate_review_payload,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_revision import (
    candidate_revision_payload,
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
    """Bind configured and retained author/reviewer evidence to a pinned profile."""

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
    host_native = observation.get("origin") == "host_native"
    if host_native:
        stage_summary = _host_native_stage_observation_evidence(
            profile,
            sealed_observation=observation,
            stage_observation=dict(stage_observation or {}),
        )
        issues.extend(str(issue) for issue in stage_summary["issues"])
    elif observation:
        if set(observation) != {"participant_selection", "remaining_candidate_authoring"}:
            issues.append("sealed model observations have missing or unsupported roles")
        for request_role in ("participant_selection", "remaining_candidate_authoring"):
            role_observation = _mapping(observation.get(request_role))
            if str(role_observation.get("profile_id") or "") != profile:
                issues.append(
                    f"sealed {request_role} profile identity does not match the assigned release profile"
                )
                continue
            issues.extend(
                greenfield_model_profile_observation_issues(
                    profile_id=profile,
                    provider=str(role_observation.get("provider") or ""),
                    model=str(role_observation.get("model") or ""),
                    reasoning_effort=str(role_observation.get("reasoning_effort") or ""),
                    effective_timeout_seconds=role_observation.get("effective_timeout_seconds"),
                    authoring_tier=str(role_observation.get("authoring_tier") or ""),
                    request_role=request_role,
                )
            )
    elif profile != UNAVAILABLE_PROVIDER_PROFILE:
        issues.append("sealed model profile observation is missing")
    stage_summary = stage_summary if host_native else (
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
    issues = list(dict.fromkeys(issues))
    return {
        "contract_version": GREENFIELD_MODEL_PROFILE_CONTRACT_VERSION,
        "assignment_version": MODEL_PROFILE_ASSIGNMENT_VERSION,
        "profile_id": profile,
        "repair_tier": contract.repair_tier,
        "performance_target_seconds": contract.performance_target_seconds,
        "operational_timeout_seconds": contract.operational_timeout_seconds,
        "lower_capability": contract.lower_capability,
        "semantic_authority": (
            "host_native_candidate_and_preconfirm_tribunal"
            if host_native
            else "typed_evidence_and_preconfirm_tribunal"
        ),
        "sealed_request_roles": (
            ["host_candidate", "candidate_review"]
            if host_native
            else ["participant_selection", "remaining_candidate_authoring"]
        ),
        "lower_capability_scope": (
            ("candidate_review" if host_native else "remaining_candidate_authoring")
            if contract.lower_capability
            else "not_applicable"
        ),
        "maximum_semantic_model_calls": 1 if host_native else 5,
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


def host_native_model_stage_observation_issues(
    profile: str,
    *,
    observed: Mapping[str, Any],
    stage_observation: Mapping[str, Any],
) -> tuple[str, ...]:
    """Validate host-native custody without reviving retired runtime author roles."""

    return tuple(
        str(issue)
        for issue in _host_native_stage_observation_evidence(
            profile,
            sealed_observation=observed,
            stage_observation=stage_observation,
        )["issues"]
    )


def _host_native_stage_observation_evidence(
    profile: str,
    *,
    sealed_observation: Mapping[str, Any],
    stage_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one external host candidate and one runtime review to sealed custody."""

    contract = get_greenfield_model_profile(profile)
    observed = _mapping(sealed_observation)
    retained = _mapping(stage_observation)
    issues: list[str] = []
    if set(observed) != {"origin", "host_candidate", "candidate_review"}:
        issues.append("sealed host-native observation has missing or unsupported fields")
    if observed.get("origin") != "host_native":
        issues.append("sealed host-native observation has an invalid origin")

    candidate = _mapping(observed.get("host_candidate"))
    if set(candidate) != {
        "version", "contract_version", "source_sha256", "candidate_sha256",
    }:
        issues.append("sealed host candidate receipt has missing or unsupported fields")
    if candidate.get("version") != "odylith.greenfield.host-candidate.v1":
        issues.append("sealed host candidate receipt version is invalid")
    if candidate.get("contract_version") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("sealed host candidate canonical contract version is invalid")
    for field in ("source_sha256", "candidate_sha256"):
        if not _is_sha256(candidate.get(field)):
            issues.append(f"sealed host candidate {field} is invalid")

    review = _mapping(observed.get("candidate_review"))
    expected_review_fields = {
        "profile_id", "provider", "model", "reasoning_effort",
        "effective_timeout_seconds", "authoring_tier",
    }
    if set(review) != expected_review_fields:
        issues.append("sealed candidate_review lacks the stable six-field request observation")
    elif str(review.get("profile_id") or "").strip() != profile:
        issues.append("sealed candidate_review observation identifies a different profile")
    else:
        try:
            issues.extend(greenfield_model_profile_observation_issues(
                profile_id=profile,
                provider=str(review.get("provider") or ""),
                model=str(review.get("model") or ""),
                reasoning_effort=str(review.get("reasoning_effort") or ""),
                effective_timeout_seconds=review.get("effective_timeout_seconds"),
                authoring_tier=str(review.get("authoring_tier") or ""),
                request_role="candidate_review",
            ))
        except (TypeError, ValueError, OverflowError):
            issues.append("sealed candidate_review observation is invalid")

    expected_stage_fields = {
        "version", "status", "host_invocations", "contract_command_invocations",
        "proposal_command_invocations", "host_argv", "candidate_temp_cleaned",
        "host_workspace_cleaned", "stage", "contract_returncode", "contract_sha256",
        "candidate_schema_sha256", "host_returncode", "host_stdout_bytes",
        "host_stderr_bytes", "candidate_sha256", "candidate_temp_outside_repo",
        "elapsed_seconds",
    }
    if set(retained) != expected_stage_fields:
        issues.append("retained host-native observation has missing or unsupported fields")
    if retained.get("version") != HOST_NATIVE_MATRIX_OBSERVATION_VERSION:
        issues.append("retained host-native observation version is invalid")
    if retained.get("status") != "passed" or retained.get("stage") != "propose":
        issues.append("retained host-native flow did not finish proposal successfully")
    for field in (
        "host_invocations", "contract_command_invocations", "proposal_command_invocations",
    ):
        if retained.get(field) != 1:
            issues.append(f"retained host-native {field} must equal one")
    for field in ("contract_returncode", "host_returncode"):
        if retained.get(field) != 0:
            issues.append(f"retained host-native {field} is nonzero")
    for field in (
        "candidate_temp_cleaned", "host_workspace_cleaned", "candidate_temp_outside_repo",
    ):
        if retained.get(field) is not True:
            issues.append(f"retained host-native {field} is not true")
    for field in ("contract_sha256", "candidate_schema_sha256", "candidate_sha256"):
        if not _is_sha256(retained.get(field)):
            issues.append(f"retained host-native {field} is invalid")
    if (
        _is_sha256(candidate.get("candidate_sha256"))
        and retained.get("candidate_sha256") != candidate.get("candidate_sha256")
    ):
        issues.append("retained host candidate does not match the sealed receipt")
    host_argv = _mapping(retained.get("host_argv"))
    if (
        set(host_argv) != {"executable", "argument_count"}
        or not str(host_argv.get("executable") or "").strip()
        or type(host_argv.get("argument_count")) is not int
        or int(host_argv.get("argument_count") or 0) <= 0
    ):
        issues.append("retained host-native argv shape is invalid")
    for field in ("host_stdout_bytes", "host_stderr_bytes"):
        if type(retained.get(field)) is not int or int(retained.get(field) or 0) < 0:
            issues.append(f"retained host-native {field} is invalid")
    elapsed = _positive_float(retained.get("elapsed_seconds"))
    if elapsed is None or elapsed >= contract.operational_timeout_seconds:
        issues.append("retained host-native elapsed time lacks operational-timeout proof")

    return {
        "observation_version": str(retained.get("version") or ""),
        "origin": "host_native",
        "semantic_model_call_count": 1,
        "request_roles": {
            "host_candidate": {
                "external_host": str(host_argv.get("executable") or ""),
                "candidate_sha256": str(retained.get("candidate_sha256") or ""),
            },
            "candidate_review": dict(review),
        },
        "status": "passed" if not issues else "failed",
        "issues": list(dict.fromkeys(issues)),
    }


def model_stage_observation_issues(
    profile: str,
    *,
    observed: Mapping[str, Any],
    stage_observation: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return fail-closed issues for one retained complete-author observation."""

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
    """Validate the exact participant-first proof against one shared model window."""

    contract = get_greenfield_model_profile(profile)
    retained = _mapping(stage_observation)
    issues: list[str] = []
    if not retained:
        issues.append("retained model authoring observation is missing")
    if str(retained.get("version") or "") != GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION:
        issues.append("retained model authoring observation version is invalid")
    if str(retained.get("authoring_version") or "") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("retained model authoring version is invalid")

    request = _mapping(retained.get("request"))
    source = request.get("evidence")
    if (
        set(request) != {"version", "evidence"}
        or request.get("version") != GREENFIELD_INTENT_AUTHORING_VERSION
        or not isinstance(source, str)
        or not source.strip()
    ):
        issues.append("retained author request lacks current source evidence")
        source = ""

    participant = _mapping(retained.get("participant_selection"))
    remainder = _mapping(retained.get("remaining_candidate_authoring"))
    remainder_response = _mapping(remainder.get("response"))
    response_kind = str(_mapping(remainder_response.get("result")).get("status") or "")
    if str(remainder_response.get("version") or "") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("retained model response version is invalid")
    if response_kind not in {"authored", "clarification_required"}:
        issues.append("retained model response kind is invalid")

    call_count = retained.get("semantic_model_call_count")
    if type(call_count) is not int:
        issues.append("retained semantic model call count is invalid")
        normalized_call_count = 0
    else:
        normalized_call_count = call_count

    revised = response_kind == "authored" and normalized_call_count == 5
    expected_fields = {
        "version", "authoring_version", "request", "semantic_model_call_count",
        "participant_selection", "remaining_candidate_authoring",
    }
    if response_kind == "authored":
        expected_fields.update({"joined_candidate", "candidate_review"})
    if revised:
        expected_fields.update({
            "rejected_candidate", "rejected_candidate_review", "candidate_revision",
        })
    if set(retained) != expected_fields:
        issues.append("retained model observation has missing or unsupported fields")

    sealed_roles = {
        role: _mapping(sealed_observation.get(role))
        for role in ("participant_selection", "remaining_candidate_authoring")
    }
    if set(sealed_observation) != set(sealed_roles):
        issues.append("sealed model observations have missing or unsupported roles")
    sealed_fields = {
        "profile_id", "provider", "model", "reasoning_effort",
        "effective_timeout_seconds", "authoring_tier",
    }
    for role, sealed in sealed_roles.items():
        if set(sealed) != sealed_fields:
            issues.append(f"sealed {role} observation has missing or unsupported fields")
        if sealed.get("profile_id") != profile:
            issues.append(f"sealed {role} profile identity does not match the assigned release profile")
        try:
            issues.extend(greenfield_model_profile_observation_issues(
                profile_id=profile, provider=sealed.get("provider"), model=sealed.get("model"),
                reasoning_effort=sealed.get("reasoning_effort"),
                effective_timeout_seconds=sealed.get("effective_timeout_seconds"),
                authoring_tier=sealed.get("authoring_tier"), request_role=role,
            ))
        except (TypeError, ValueError, OverflowError):
            issues.append(f"sealed {role} observation is invalid")

    shared_timeout = _positive_float(
        sealed_roles["participant_selection"].get("effective_timeout_seconds")
    )
    if shared_timeout is None:
        issues.append("sealed shared model window is invalid")
    elif shared_timeout > contract.model_timeout_seconds:
        issues.append("sealed shared model window exceeds its pinned profile")

    request_roles: dict[str, Any] = {}
    prior_elapsed = 0.0
    participant_citations: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    for role, observation in (
        ("participant_selection", participant),
        ("remaining_candidate_authoring", remainder),
    ):
        request_roles[role] = _request_role_summary(observation)
        expected_stage_fields = {
            "dispatched", "request_role", "profile_id", "timeout_seconds",
            "elapsed_seconds", "model", "reasoning_effort", "request", "response", "provider",
        }
        if role == "participant_selection":
            expected_stage_fields.add("resolved")
        if set(observation) != expected_stage_fields:
            issues.append(f"retained {role} observation has missing or unsupported fields")
        if observation.get("dispatched") is not True:
            issues.append(f"retained {role} was not dispatched")
        try:
            issues.extend(_request_role_issues(
                profile, request_role=role, observation=observation,
            ))
        except (TypeError, ValueError, OverflowError):
            issues.append(f"retained {role} request metadata is invalid")
        timeout = _positive_float(observation.get("timeout_seconds"))
        elapsed = _positive_float(observation.get("elapsed_seconds"))
        sealed_timeout = _positive_float(
            sealed_roles[role].get("effective_timeout_seconds")
        )
        if timeout is None:
            issues.append(f"retained {role} timeout is invalid")
        elif sealed_timeout is None or not _same_seconds(timeout, sealed_timeout):
            issues.append(f"retained {role} timeout does not match its sealed observation")
        if elapsed is None:
            issues.append(f"retained {role} elapsed time is invalid")
        elif timeout is not None and elapsed > timeout:
            issues.append(f"retained {role} elapsed time exceeds its timeout")
        if shared_timeout is not None and timeout is not None:
            if timeout > shared_timeout - prior_elapsed:
                issues.append(f"retained {role} timeout exceeds the remaining model window")
        if elapsed is not None:
            prior_elapsed += elapsed
    if shared_timeout is not None and prior_elapsed > shared_timeout:
        issues.append("retained authoring stages exceed the shared model window")

    authored = None
    rejected_authored = None
    expected_remainder_request: dict[str, Any] = {}
    if source:
        try:
            if _mapping(participant.get("request")) != {"source": source}:
                raise ValueError("participant request mismatch")
            participant_citations, resolved = resolve_greenfield_participant_selection(
                source, _mapping(participant.get("response")),
            )
            if participant.get("resolved") != resolved:
                raise ValueError("resolved participant mismatch")
            expected_remainder_request = dict(request)
            expected_remainder_request["frozen_human_actors"] = participant_citations
            if remainder.get("request") != expected_remainder_request:
                raise ValueError("remaining request mismatch")
            if response_kind == "authored":
                joined = join_frozen_greenfield_participants(
                    remainder_response, participant_citations,
                )
                retained_candidate_key = "rejected_candidate" if revised else "joined_candidate"
                if retained.get(retained_candidate_key) != joined:
                    raise ValueError("joined candidate mismatch")
                rejected_authored = validate_greenfield_authoring_response(
                    joined, evidence_text=source,
                    elapsed_seconds=_float_value(remainder.get("elapsed_seconds")),
                    provider=_mapping(remainder.get("provider")), profile_id=profile,
                    effective_timeout_seconds=_float_value(remainder.get("timeout_seconds")),
                    semantic_model_call_count=2,
                )
                if not revised:
                    authored = rejected_authored
            elif response_kind == "clarification_required":
                validate_greenfield_authoring_response(
                    remainder_response, evidence_text=source,
                    elapsed_seconds=_float_value(remainder.get("elapsed_seconds")),
                    provider=_mapping(remainder.get("provider")), profile_id=profile,
                    effective_timeout_seconds=_float_value(remainder.get("timeout_seconds")),
                    semantic_model_call_count=2,
                )
        except (GreenfieldModelAuthoringError, ValueError, TypeError, KeyError):
            issues.append("retained participant-first response fails canonical source-bound validation")

    if response_kind == "authored":
        if normalized_call_count not in {3, 5}:
            issues.append("authored response must record exactly three or five semantic calls")
        if revised:
            rejected_review = _mapping(retained.get("rejected_candidate_review"))
            request_roles["rejected_candidate_review"] = _request_role_summary(
                rejected_review
            )
            issues.extend(_candidate_review_observation_issues(
                profile, review=rejected_review, request=request,
                candidate=_mapping(_mapping(retained.get("rejected_candidate")).get("result")),
                shared_timeout=shared_timeout, prior_elapsed=prior_elapsed,
                source_spans=(
                    rejected_authored.source_spans
                    if isinstance(rejected_authored, GreenfieldModelAuthoredIntent)
                    else ()
                ),
                admissible=False,
            ))
            prior_elapsed += _float_value(rejected_review.get("elapsed_seconds"))

            revision = _mapping(retained.get("candidate_revision"))
            request_roles["candidate_revision"] = _request_role_summary(revision)
            expected_revision_fields = {
                "dispatched", "request_role", "profile_id", "timeout_seconds",
                "elapsed_seconds", "model", "reasoning_effort", "request", "response",
                "provider",
            }
            if set(revision) != expected_revision_fields:
                issues.append("retained candidate revision has missing or unsupported fields")
            if revision.get("dispatched") is not True:
                issues.append("retained candidate revision was not dispatched")
            try:
                issues.extend(_request_role_issues(
                    profile, request_role="candidate_revision", observation=revision,
                ))
            except (TypeError, ValueError, OverflowError):
                issues.append("retained candidate revision request metadata is invalid")
            revision_timeout = _positive_float(revision.get("timeout_seconds"))
            revision_elapsed = _positive_float(revision.get("elapsed_seconds"))
            remaining_window = (
                shared_timeout - prior_elapsed if shared_timeout is not None else None
            )
            if revision_timeout is None:
                issues.append("retained candidate revision timeout is invalid")
            elif remaining_window is None or revision_timeout > remaining_window:
                issues.append("retained candidate revision timeout exceeds the remaining model window")
            if revision_elapsed is None:
                issues.append("retained candidate revision elapsed time is invalid")
            elif revision_timeout is not None and revision_elapsed > revision_timeout:
                issues.append("retained candidate revision elapsed time exceeds its timeout")
            elif remaining_window is None or revision_elapsed > remaining_window:
                issues.append("retained candidate revision elapsed time exceeds the remaining model window")

            rejected_verdict = _mapping(rejected_review.get("response"))
            review_issues = rejected_verdict.get("issues")
            revision_response = _mapping(revision.get("response"))
            try:
                if not isinstance(review_issues, list) or len(review_issues) != 1:
                    raise ValueError("missing denial witness")
                expected_revision_request = candidate_revision_payload(
                    authoring_payload=expected_remainder_request,
                    rejected_candidate=remainder_response,
                    review_issue=_mapping(review_issues[0]),
                )
                if revision.get("request") != expected_revision_request:
                    raise ValueError("revision request mismatch")
                if (
                    revision_response.get("version") != GREENFIELD_INTENT_AUTHORING_VERSION
                    or _mapping(revision_response.get("result")).get("status") != "authored"
                ):
                    raise ValueError("revision response mismatch")
                revised_joined = join_frozen_greenfield_participants(
                    revision_response, participant_citations,
                )
                if retained.get("joined_candidate") != revised_joined:
                    raise ValueError("revised joined candidate mismatch")
                authored = validate_greenfield_authoring_response(
                    revised_joined, evidence_text=source,
                    elapsed_seconds=_float_value(revision.get("elapsed_seconds")),
                    provider=_mapping(revision.get("provider")), profile_id=profile,
                    effective_timeout_seconds=_float_value(revision.get("timeout_seconds")),
                    semantic_model_call_count=4,
                )
            except (GreenfieldModelAuthoringError, ValueError, TypeError, KeyError):
                issues.append("retained candidate revision fails source-bound replacement validation")
            prior_elapsed += _float_value(revision.get("elapsed_seconds"))

        review = _mapping(retained.get("candidate_review"))
        request_roles["candidate_review"] = _request_role_summary(review)
        issues.extend(_candidate_review_observation_issues(
            profile, review=review, request=request,
            candidate=_mapping(_mapping(retained.get("joined_candidate")).get("result")),
            shared_timeout=shared_timeout, prior_elapsed=prior_elapsed,
            source_spans=authored.source_spans if isinstance(authored, GreenfieldModelAuthoredIntent) else (),
            admissible=True,
        ))
    elif normalized_call_count != 2:
        issues.append("clarification response must record exactly two semantic calls")
    if any(
        field in retained
        for field in ("initial_authoring", "initial_response", "source_review", "response")
    ):
        issues.append("participant-first response must not record a legacy author path")

    return {
        "observation_version": str(retained.get("version") or ""),
        "authoring_version": str(retained.get("authoring_version") or ""),
        "response_kind": response_kind,
        "semantic_model_call_count": normalized_call_count,
        "request_roles": request_roles,
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


def _candidate_review_observation_issues(
    profile: str, *, review: Mapping[str, Any], request: Mapping[str, Any],
    candidate: Mapping[str, Any], shared_timeout: float | None,
    prior_elapsed: float, source_spans: Sequence[Mapping[str, Any]],
    admissible: bool,
) -> tuple[str, ...]:
    """Check the current binary observation, not a historical repair protocol.

    Native observations carry no protocol ID or sealed review receipt. Exact
    current payload equality binds both authorities without inventing either.
    Elapsed review time includes setup and must fit the actual retained request
    timeout as well as the shared window's remaining time.
    """
    issues = list(_request_role_issues(
        profile, request_role="candidate_review", observation=review,
    ))
    if set(review) != {
        "dispatched", "request_role", "profile_id", "timeout_seconds", "model",
        "reasoning_effort", "request", "response", "provider", "elapsed_seconds",
    }:
        issues.append("retained candidate review has missing or unsupported fields")
    if review.get("dispatched") is not True:
        issues.append("retained candidate review was not dispatched")
    verdict = _mapping(review.get("response"))
    expected_issue_count = 0 if admissible else 1
    if (set(verdict) != {"admissible", "issues"}
            or verdict.get("admissible") is not admissible
            or type(verdict.get("issues")) is not list
            or len(verdict["issues"]) != expected_issue_count
            or any(
                not isinstance(issue, Mapping)
                or set(issue) != {"path", "reason"}
                or any(not isinstance(issue[key], str) or not issue[key].strip() for key in issue)
                for issue in verdict.get("issues", ())
            )):
        outcome = "admitted" if admissible else "denied"
        issues.append(f"retained candidate review lacks a valid {outcome} binary verdict")
    source = request.get("evidence")
    try:
        if not isinstance(source, str) or not source.strip():
            raise ValueError("missing source")
        expected_payload = candidate_review_payload(source, candidate, source_spans=source_spans)
        actual = json.dumps(review.get("request"), sort_keys=True, ensure_ascii=False, allow_nan=False)
        expected = json.dumps(expected_payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if actual != expected:
            issues.append("retained candidate review does not bind the full source and candidate")
    except (ValueError, TypeError):
        issues.append("retained candidate review source/candidate payload is invalid")
    contract = get_greenfield_model_profile(profile)
    remaining = shared_timeout - prior_elapsed if shared_timeout is not None else None
    for field in ("timeout_seconds", "elapsed_seconds"):
        seconds = _positive_float(review.get(field))
        if seconds is None:
            issues.append(f"retained candidate review {field} is invalid")
        elif (seconds > contract.model_timeout_seconds
              or remaining is None or seconds > remaining):
            issues.append(f"retained candidate review {field} exceeds the remaining model window")
    review_timeout = _positive_float(review.get("timeout_seconds"))
    review_elapsed = _positive_float(review.get("elapsed_seconds"))
    if (
        review_timeout is not None
        and review_elapsed is not None
        and review_elapsed > review_timeout
    ):
        issues.append("retained candidate review elapsed time exceeds its timeout")
    return tuple(issues)


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
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _positive_float(value: Any) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def _is_sha256(value: Any) -> bool:
    normalized = str(value or "").strip().casefold()
    return len(normalized) == 64 and all(
        character in "0123456789abcdef" for character in normalized
    )


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
    if (set(provider) != {"provider", "model", "reasoning_effort", "code", "detail"}
            or any(not isinstance(value, str) for value in provider.values())):
        issues.append(f"retained {request_role} provider metadata is missing or malformed")
    if provider.get("code") or provider.get("detail"):
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
    "host_native_model_stage_observation_issues",
    "model_stage_observation_issues",
    "profile_coverage",
    "profile_counts",
]
