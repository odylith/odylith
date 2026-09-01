"""Versioned, structurally enforced support boundary for Greenfield authoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    greenfield_model_profile_observation_issues,
    supported_greenfield_model_profile_ids,
)


GREENFIELD_OPERATING_ENVELOPE_VERSION = "odylith.greenfield-operating-envelope.v3"
GREENFIELD_OPERATING_PROFILE = "single-product-governance-onboarding"

# These are the only source formats accepted by the public authored path. The
# custody formats are accepted only by already-typed internal construction and
# are deliberately not advertised as user evidence inputs.
PUBLIC_EVIDENCE_FORMATS = (
    "operator_prompt",
    "operator_prompt_with_edit_evidence",
)
SUPPORTED_PUBLIC_INPUT_FORMATS = PUBLIC_EVIDENCE_FORMATS
INTERNAL_CUSTODY_FORMATS = (
    "compiled_proposal_intent",
    "in_memory_confirmed_intent",
    "json",
    "legacy_json",
    "markdown",
    "typed_envelope_json",
)
SUPPORTED_EVIDENCE_FORMATS = frozenset(PUBLIC_EVIDENCE_FORMATS)
SUPPORTED_INTERNAL_CUSTODY_FORMATS = frozenset(INTERNAL_CUSTODY_FORMATS)
SUPPORTED_EVIDENCE_LANGUAGES = ("en",)
SUPPORTED_CONFIRMATION_HOSTS = ("codex", "claude")
SUPPORTED_COMPLEXITY_BANDS = ("bounded", "moderate", "high")

# 64 KiB is an enforceable model-input bound, including Odylith's evidence
# framing. It leaves the structured schema and response ample room in the
# pinned profile context windows and is checked before provider discovery.
MAX_EVIDENCE_BYTES = 64 * 1024
MAX_EVIDENCE_DOCUMENTS = 2

# One shared authored-shape contract. Model validation imports these values;
# the receipt publishes the same values rather than maintaining a second set.
MAX_AUTHORED_FIELD_VALUE_CHARS = 2_400
MAX_AUTHORED_LIST_ITEMS = 32
MAX_AUTHORED_CITATIONS = 256
AUTHORED_LIST_FIELDS = (
    "success_metrics",
    "evidence_requirements",
    "operational_constraints",
    "component_responsibilities",
    "human_actors",
    "external_systems",
    "internal_systems",
    "assumptions",
    "ambiguities",
    "non_goals",
)
MAX_ACTORS = MAX_AUTHORED_LIST_ITEMS
MAX_STATE_OBJECTS = 1
MAX_FIRST_RELEASE_PATHS = 1
MAX_SYSTEMS_PER_BOUNDARY = MAX_AUTHORED_LIST_ITEMS
MAX_CONTRADICTIONS = 0
MAX_AMBIGUITIES = MAX_AUTHORED_LIST_ITEMS
MAX_SAFETY_BOUNDARIES = MAX_AUTHORED_LIST_ITEMS

LANGUAGE_ASSURANCE = "explicit_operator_contract_not_content_detection"
INTERNAL_LANGUAGE_ASSURANCE = "typed_internal_custody_not_language_admission"

_COMPLEXITY_LIMITS = {
    "list_items_per_field": MAX_AUTHORED_LIST_ITEMS,
    "actors": MAX_ACTORS,
    "state_objects": MAX_STATE_OBJECTS,
    "paths": MAX_FIRST_RELEASE_PATHS,
    "external_systems": MAX_SYSTEMS_PER_BOUNDARY,
    "internal_systems": MAX_SYSTEMS_PER_BOUNDARY,
    "contradictions": MAX_CONTRADICTIONS,
    "ambiguities": MAX_AMBIGUITIES,
    "safety_boundaries": MAX_SAFETY_BOUNDARIES,
}
_SCOPE_CONTRACT = {
    "product_count": 1,
    "first_release_path_count": 1,
    "write_boundary": "repo_local_governance_package",
    "external_side_effects": "none",
}
_FILESYSTEM_CONTRACT = {
    "repository": "single_local_writable_repository",
    "locking": "exclusive_advisory_file_lock",
    "durability": "same_filesystem_atomic_replace_and_fsync",
    "path_safety": "relative_owned_paths_without_symlink_traversal",
    "package_visibility": "journaled_recovery_not_atomic_generation_pointer",
}
_HOST_CONTRACT = {
    "confirmation_hosts": SUPPORTED_CONFIRMATION_HOSTS,
    "other_hosts": "proposal_only_unless_deterministic_callback_proven",
}
_MODEL_AUTHORITY = "candidate_hypothesis_only"
_LOWER_CAPABILITY_BEHAVIOR = "clarify_or_fail_safe_without_invention"


class GreenfieldOperatingEnvelopeError(ValueError):
    """The evidence cannot enter the supported Greenfield authoring path."""


def admit_greenfield_public_evidence(
    *,
    evidence_text: str,
    source_format: str,
    source_document_count: int,
    source_language: str = "en",
) -> dict[str, Any]:
    """Pure structural admission run before provider discovery or invocation.

    This function deliberately does not infer language from words, characters,
    or tokens. ``source_language`` is the explicit operator/API contract.
    """

    source_bytes = str(evidence_text or "").encode("utf-8")
    observed = _evidence_observation(
        source_format=source_format,
        source_size_bytes=len(source_bytes),
        source_document_count=source_document_count,
        source_language=source_language,
    )
    issues = _evidence_issues(observed, public_only=True)
    if issues:
        raise GreenfieldOperatingEnvelopeError(
            "Greenfield evidence is outside the declared operating envelope: " + ", ".join(issues)
        )
    return observed


def greenfield_operating_envelope_receipt(
    *,
    facts: Mapping[str, Any],
    source_format: str,
    source_size_bytes: int,
    source_document_count: int = 1,
    source_language: str = "en",
    model_authoring: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the enforceable support receipt sealed with Product Intent."""

    observed_evidence = _evidence_observation(
        source_format=source_format,
        source_size_bytes=source_size_bytes,
        source_document_count=source_document_count,
        source_language=source_language,
    )
    issues = _evidence_issues(observed_evidence, public_only=False)
    dimensions = _complexity_dimensions(
        facts,
        evidence_bytes=observed_evidence["bytes"],
        documents=observed_evidence["documents"],
    )
    issues.extend(_dimension_issues(dimensions))

    observed_model = _model_authoring_observation(model_authoring)
    if observed_evidence["source_kind"] == "public_evidence":
        if observed_model is None:
            issues.append("missing_model_authoring_observation")
        elif greenfield_model_profile_observation_issues(
            profile_id=observed_model["profile_id"],
            provider=observed_model["provider"],
            model=observed_model["model"],
            reasoning_effort=observed_model["reasoning_effort"],
            effective_timeout_seconds=observed_model["effective_timeout_seconds"],
        ):
            issues.append("model_authoring_observation_mismatch")
        elif get_greenfield_model_profile(observed_model["profile_id"]).repair_tier != observed_model["authoring_tier"]:
            issues.append("model_authoring_tier_mismatch")

    supported_profiles = supported_greenfield_model_profile_ids()
    return {
        "version": GREENFIELD_OPERATING_ENVELOPE_VERSION,
        "profile": GREENFIELD_OPERATING_PROFILE,
        "status": "supported" if not issues else "unsupported",
        "evidence_format": observed_evidence["format"],
        "issues": issues,
        "evidence_contract": {
            "public_input_formats": list(PUBLIC_EVIDENCE_FORMATS),
            "internal_custody_formats": list(INTERNAL_CUSTODY_FORMATS),
            "languages": list(SUPPORTED_EVIDENCE_LANGUAGES),
            "language_assurance": LANGUAGE_ASSURANCE,
            "minimum_bytes": 1,
            "maximum_bytes": MAX_EVIDENCE_BYTES,
            "maximum_documents": MAX_EVIDENCE_DOCUMENTS,
            "observed": observed_evidence,
        },
        "complexity": {
            "band": greenfield_complexity_band(dimensions),
            "dimensions": dimensions,
            "limits": dict(_COMPLEXITY_LIMITS),
        },
        "scope": dict(_SCOPE_CONTRACT),
        "filesystem_contract": dict(_FILESYSTEM_CONTRACT),
        "host_contract": _host_contract_receipt(),
        "model_contract": {
            "profiles": list(supported_profiles),
            "authority": _MODEL_AUTHORITY,
            "lower_capability_behavior": _LOWER_CAPABILITY_BEHAVIOR,
            "observed": observed_model,
        },
    }


def require_supported_greenfield_operating_envelope(value: Mapping[str, Any]) -> None:
    """Fail before confirmation when a sealed request exceeds the envelope."""

    if not isinstance(value, Mapping):
        raise ValueError("Greenfield operating envelope is missing")
    if set(value) != {
        "version",
        "profile",
        "status",
        "evidence_format",
        "issues",
        "evidence_contract",
        "complexity",
        "scope",
        "filesystem_contract",
        "host_contract",
        "model_contract",
    }:
        raise ValueError("Greenfield operating envelope fields are unsupported")
    if value.get("version") != GREENFIELD_OPERATING_ENVELOPE_VERSION:
        raise ValueError("Greenfield operating envelope version is unsupported")
    if value.get("profile") != GREENFIELD_OPERATING_PROFILE:
        raise ValueError("Greenfield operating envelope profile is unsupported")
    if value.get("status") != "supported" or value.get("issues") != []:
        raise ValueError("Greenfield request is outside the declared operating envelope")

    evidence = value.get("evidence_contract")
    if not isinstance(evidence, Mapping) or set(evidence) != {
        "public_input_formats",
        "internal_custody_formats",
        "languages",
        "language_assurance",
        "minimum_bytes",
        "maximum_bytes",
        "maximum_documents",
        "observed",
    }:
        raise ValueError("Greenfield operating envelope evidence contract is unsupported")
    if evidence.get("public_input_formats") != list(PUBLIC_EVIDENCE_FORMATS):
        raise ValueError("Greenfield operating envelope public evidence contract is unsupported")
    if evidence.get("internal_custody_formats") != list(INTERNAL_CUSTODY_FORMATS):
        raise ValueError("Greenfield operating envelope custody format contract is unsupported")
    if evidence.get("languages") != list(SUPPORTED_EVIDENCE_LANGUAGES):
        raise ValueError("Greenfield operating envelope language contract is unsupported")
    if evidence.get("language_assurance") != LANGUAGE_ASSURANCE:
        raise ValueError("Greenfield operating envelope language assurance is unsupported")
    if (
        evidence.get("minimum_bytes") != 1
        or evidence.get("maximum_bytes") != MAX_EVIDENCE_BYTES
        or evidence.get("maximum_documents") != MAX_EVIDENCE_DOCUMENTS
    ):
        raise ValueError("Greenfield operating envelope evidence limits are unsupported")
    observed_evidence = evidence.get("observed")
    if not isinstance(observed_evidence, Mapping) or set(observed_evidence) != {
        "format",
        "source_kind",
        "bytes",
        "documents",
        "language",
        "language_assurance",
    }:
        raise ValueError("Greenfield operating envelope observed evidence is unsupported")
    normalized_evidence = _evidence_observation(
        source_format=str(observed_evidence.get("format") or ""),
        source_size_bytes=observed_evidence.get("bytes"),
        source_document_count=observed_evidence.get("documents"),
        source_language=str(observed_evidence.get("language") or ""),
    )
    if normalized_evidence != observed_evidence or _evidence_issues(observed_evidence, public_only=False):
        raise ValueError("Greenfield operating envelope observed evidence is unsupported")
    if value.get("evidence_format") != observed_evidence.get("format"):
        raise ValueError("Greenfield operating envelope evidence format custody is invalid")

    complexity = value.get("complexity")
    dimensions = complexity.get("dimensions") if isinstance(complexity, Mapping) else None
    if not isinstance(complexity, Mapping) or set(complexity) != {"band", "dimensions", "limits"}:
        raise ValueError("Greenfield operating envelope complexity contract is unsupported")
    if complexity.get("limits") != _COMPLEXITY_LIMITS:
        raise ValueError("Greenfield operating envelope complexity limits are unsupported")
    if not _valid_dimensions(dimensions):
        raise ValueError("Greenfield operating envelope complexity dimensions are missing")
    if (
        dimensions.get("evidence_bytes") != observed_evidence.get("bytes")
        or dimensions.get("documents") != observed_evidence.get("documents")
    ):
        raise ValueError("Greenfield operating envelope evidence dimensions are inconsistent")
    if complexity.get("band") != greenfield_complexity_band(dimensions):
        raise ValueError("Greenfield operating envelope complexity band is invalid")
    if _dimension_issues(dimensions):
        raise ValueError("Greenfield operating envelope complexity exceeds its limits")

    if value.get("scope") != _SCOPE_CONTRACT:
        raise ValueError("Greenfield operating envelope scope contract is unsupported")
    host = value.get("host_contract")
    if host != _host_contract_receipt():
        raise ValueError("Greenfield operating envelope host contract is unsupported")
    model = value.get("model_contract")
    if not isinstance(model, Mapping) or set(model) != {
        "profiles",
        "authority",
        "lower_capability_behavior",
        "observed",
    }:
        raise ValueError("Greenfield operating envelope model contract is unsupported")
    if (
        model.get("profiles") != list(supported_greenfield_model_profile_ids())
        or model.get("authority") != _MODEL_AUTHORITY
        or model.get("lower_capability_behavior") != _LOWER_CAPABILITY_BEHAVIOR
    ):
        raise ValueError("Greenfield operating envelope model contract is unsupported")
    observed_model = model.get("observed")
    if observed_evidence.get("source_kind") == "public_evidence":
        normalized_model = _model_authoring_observation(observed_model if isinstance(observed_model, Mapping) else None)
        if normalized_model is None or normalized_model != observed_model:
            raise ValueError("Greenfield operating envelope model observation is malformed")
        if greenfield_model_profile_observation_issues(
            profile_id=normalized_model["profile_id"],
            provider=normalized_model["provider"],
            model=normalized_model["model"],
            reasoning_effort=normalized_model["reasoning_effort"],
            effective_timeout_seconds=normalized_model["effective_timeout_seconds"],
        ):
            raise ValueError("Greenfield operating envelope model observation is unsupported")
        if (
            get_greenfield_model_profile(normalized_model["profile_id"]).repair_tier
            != normalized_model["authoring_tier"]
        ):
            raise ValueError("Greenfield operating envelope model tier is unsupported")
    elif observed_model is not None:
        raise ValueError("Greenfield internal custody envelope cannot claim a model observation")

    filesystem = value.get("filesystem_contract")
    if filesystem != _FILESYSTEM_CONTRACT:
        raise ValueError("Greenfield operating envelope filesystem contract is unsupported")


def greenfield_complexity_band(dimensions: Mapping[str, Any]) -> str:
    """Return the shared structural complexity band for a sealed dimension set."""

    values = {key: _nonnegative_int(dimensions.get(key)) for key in _DIMENSION_KEYS}
    score = 0
    score += _tiered_score(values["evidence_bytes"], moderate=16 * 1024, high=48 * 1024)
    score += 1 if values["documents"] > 1 else 0
    score += _tiered_score(values["actors"], moderate=4, high=16)
    score += _tiered_score(values["state_objects"], moderate=0, high=1)
    score += _tiered_score(
        values["external_systems"] + values["internal_systems"],
        moderate=4,
        high=16,
    )
    score += _tiered_score(values["contradictions"], moderate=0, high=0)
    score += _tiered_score(values["ambiguities"], moderate=2, high=8)
    score += _tiered_score(values["safety_boundaries"], moderate=2, high=8)
    return "high" if score >= 7 else "moderate" if score >= 3 else "bounded"


_DIMENSION_KEYS = (
    "evidence_bytes",
    "documents",
    "actors",
    "state_objects",
    "paths",
    "external_systems",
    "internal_systems",
    "contradictions",
    "ambiguities",
    "safety_boundaries",
    "success_metrics",
    "evidence_requirements",
    "component_responsibilities",
    "assumptions",
    "non_goals",
)
SUPPORTED_COMPLEXITY_DIMENSIONS = _DIMENSION_KEYS


def _evidence_observation(
    *,
    source_format: str,
    source_size_bytes: int,
    source_document_count: int,
    source_language: str,
) -> dict[str, Any]:
    evidence_format = str(source_format or "unknown").strip()
    if evidence_format in SUPPORTED_EVIDENCE_FORMATS:
        source_kind = "public_evidence"
        assurance = LANGUAGE_ASSURANCE
        language = str(source_language or "").strip().casefold()
    elif evidence_format in SUPPORTED_INTERNAL_CUSTODY_FORMATS:
        source_kind = "internal_custody"
        assurance = INTERNAL_LANGUAGE_ASSURANCE
        language = "not_applicable"
    else:
        source_kind = "unknown"
        assurance = LANGUAGE_ASSURANCE
        language = str(source_language or "").strip().casefold()
    return {
        "format": evidence_format,
        "source_kind": source_kind,
        "bytes": _nonnegative_int(source_size_bytes),
        "documents": _nonnegative_int(source_document_count),
        "language": language,
        "language_assurance": assurance,
    }


def _evidence_issues(observed: Mapping[str, Any], *, public_only: bool) -> list[str]:
    issues: list[str] = []
    evidence_format = str(observed.get("format") or "")
    source_kind = str(observed.get("source_kind") or "")
    source_bytes = _nonnegative_int(observed.get("bytes"))
    documents = _nonnegative_int(observed.get("documents"))
    if public_only and source_kind != "public_evidence":
        issues.append("unsupported_public_evidence_format")
    elif not public_only and source_kind not in {"public_evidence", "internal_custody"}:
        issues.append("unsupported_evidence_format")
    if source_bytes <= 0:
        issues.append("empty_evidence")
    elif source_bytes > MAX_EVIDENCE_BYTES:
        issues.append("evidence_too_large")
    if documents <= 0:
        issues.append("empty_evidence_documents")
    elif documents > MAX_EVIDENCE_DOCUMENTS:
        issues.append("too_many_evidence_documents")
    if source_kind == "public_evidence":
        expected_documents = 2 if evidence_format == "operator_prompt_with_edit_evidence" else 1
        if documents != expected_documents:
            issues.append("evidence_format_document_mismatch")
        if observed.get("language") not in SUPPORTED_EVIDENCE_LANGUAGES:
            issues.append("unsupported_evidence_language")
        if observed.get("language_assurance") != LANGUAGE_ASSURANCE:
            issues.append("unsupported_language_assurance")
    elif source_kind == "internal_custody":
        if (
            observed.get("language") != "not_applicable"
            or observed.get("language_assurance") != INTERNAL_LANGUAGE_ASSURANCE
        ):
            issues.append("invalid_internal_custody_language_claim")
    return issues


def _model_authoring_observation(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != {
        "profile_id",
        "provider",
        "model",
        "reasoning_effort",
        "effective_timeout_seconds",
        "authoring_tier",
    }:
        return None
    try:
        timeout_seconds = float(value.get("effective_timeout_seconds"))
    except (TypeError, ValueError):
        return None
    tier = str(value.get("authoring_tier") or "").strip()
    if tier not in {"standard", "rescue", "deep"} or timeout_seconds <= 0.0:
        return None
    return {
        "profile_id": str(value.get("profile_id") or "").strip(),
        "provider": str(value.get("provider") or "").strip().casefold(),
        "model": str(value.get("model") or "").strip(),
        "reasoning_effort": str(value.get("reasoning_effort") or "").strip().casefold(),
        "effective_timeout_seconds": timeout_seconds,
        "authoring_tier": tier,
    }


def _host_contract_receipt() -> dict[str, Any]:
    return {
        "confirmation_hosts": list(_HOST_CONTRACT["confirmation_hosts"]),
        "other_hosts": _HOST_CONTRACT["other_hosts"],
    }


def _complexity_dimensions(
    facts: Mapping[str, Any],
    *,
    evidence_bytes: int,
    documents: int,
) -> dict[str, int]:
    return {
        "evidence_bytes": max(0, int(evidence_bytes)),
        "documents": max(0, int(documents)),
        "actors": _count(facts.get("human_actors")),
        "state_objects": _declared_count(facts.get("state_objects"), fallback=facts.get("state_object")),
        "paths": _declared_count(facts.get("first_paths"), fallback=facts.get("first_path")),
        "external_systems": _count(facts.get("external_systems")),
        "internal_systems": _count(facts.get("internal_systems")),
        "contradictions": _count(facts.get("contradictions")),
        "ambiguities": _count(facts.get("ambiguities")),
        "safety_boundaries": _count(facts.get("operational_constraints")),
        "success_metrics": _count(facts.get("success_metrics")),
        "evidence_requirements": _count(facts.get("evidence_requirements")),
        "component_responsibilities": _count(facts.get("component_responsibilities")),
        "assumptions": _count(facts.get("assumptions")),
        "non_goals": _count(facts.get("non_goals")),
    }


def _tiered_score(value: int, *, moderate: int, high: int) -> int:
    return 2 if value > high else 1 if value > moderate else 0


def _dimension_issues(dimensions: Mapping[str, int]) -> list[str]:
    checks = (
        ("actors", MAX_ACTORS, "too_many_human_actors"),
        ("state_objects", MAX_STATE_OBJECTS, "too_many_state_objects"),
        ("paths", MAX_FIRST_RELEASE_PATHS, "too_many_first_release_paths"),
        ("external_systems", MAX_SYSTEMS_PER_BOUNDARY, "too_many_external_systems"),
        ("internal_systems", MAX_SYSTEMS_PER_BOUNDARY, "too_many_internal_systems"),
        ("contradictions", MAX_CONTRADICTIONS, "contradictions_not_supported"),
        ("ambiguities", MAX_AMBIGUITIES, "too_many_ambiguities"),
        ("safety_boundaries", MAX_SAFETY_BOUNDARIES, "too_many_safety_boundaries"),
        ("success_metrics", MAX_AUTHORED_LIST_ITEMS, "too_many_success_metrics"),
        ("evidence_requirements", MAX_AUTHORED_LIST_ITEMS, "too_many_evidence_requirements"),
        (
            "component_responsibilities",
            MAX_AUTHORED_LIST_ITEMS,
            "too_many_component_responsibilities",
        ),
        ("assumptions", MAX_AUTHORED_LIST_ITEMS, "too_many_assumptions"),
        ("non_goals", MAX_AUTHORED_LIST_ITEMS, "too_many_non_goals"),
    )
    return [issue for key, limit, issue in checks if dimensions[key] > limit]


def _declared_count(value: Any, *, fallback: Any) -> int:
    count = _count(value)
    if count:
        return count
    return 1 if isinstance(fallback, str) and bool(fallback) else 0


def _count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


def _nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _valid_dimensions(value: Any) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == set(_DIMENSION_KEYS)
        and all(
            isinstance(value.get(key), int)
            and not isinstance(value.get(key), bool)
            and value.get(key) >= 0
            for key in _DIMENSION_KEYS
        )
    )


__all__ = [
    "AUTHORED_LIST_FIELDS",
    "GREENFIELD_OPERATING_ENVELOPE_VERSION",
    "GREENFIELD_OPERATING_PROFILE",
    "GreenfieldOperatingEnvelopeError",
    "INTERNAL_CUSTODY_FORMATS",
    "LANGUAGE_ASSURANCE",
    "MAX_AUTHORED_CITATIONS",
    "MAX_AUTHORED_FIELD_VALUE_CHARS",
    "MAX_AUTHORED_LIST_ITEMS",
    "MAX_EVIDENCE_BYTES",
    "MAX_EVIDENCE_DOCUMENTS",
    "PUBLIC_EVIDENCE_FORMATS",
    "SUPPORTED_COMPLEXITY_BANDS",
    "SUPPORTED_COMPLEXITY_DIMENSIONS",
    "SUPPORTED_CONFIRMATION_HOSTS",
    "SUPPORTED_EVIDENCE_FORMATS",
    "SUPPORTED_EVIDENCE_LANGUAGES",
    "SUPPORTED_INTERNAL_CUSTODY_FORMATS",
    "SUPPORTED_PUBLIC_INPUT_FORMATS",
    "admit_greenfield_public_evidence",
    "greenfield_complexity_band",
    "greenfield_operating_envelope_receipt",
    "require_supported_greenfield_operating_envelope",
]
