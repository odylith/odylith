"""Versioned support boundary for Greenfield Product Intent compilation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


GREENFIELD_OPERATING_ENVELOPE_VERSION = "odylith.greenfield-operating-envelope.v2"
GREENFIELD_OPERATING_PROFILE = "single-product-governance-onboarding"

SUPPORTED_EVIDENCE_FORMATS = frozenset(
    {
        "compiled_proposal_intent",
        "in_memory_confirmed_intent",
        "json",
        "legacy_json",
        "markdown",
        "operator_prompt",
        "operator_prompt_with_edit_evidence",
        "typed_envelope_json",
    }
)
SUPPORTED_EVIDENCE_LANGUAGES = ("en",)
SUPPORTED_CONFIRMATION_HOSTS = ("codex", "claude")
SUPPORTED_MODEL_PROFILES = (
    "provider-free-standard-v1",
    "bounded-reasoning-standard-v1",
    "lower-capability-safe-v1",
)

MAX_EVIDENCE_BYTES = 8 * 1024 * 1024
MAX_EVIDENCE_DOCUMENTS = 2
MAX_ACTORS = 64
MAX_STATE_OBJECTS = 16
MAX_FIRST_RELEASE_PATHS = 1
MAX_SYSTEMS_PER_BOUNDARY = 128
MAX_CONTRADICTIONS = 16
MAX_AMBIGUITIES = 32
MAX_SAFETY_BOUNDARIES = 32


def greenfield_operating_envelope_receipt(
    *,
    facts: Mapping[str, Any],
    source_format: str,
    source_size_bytes: int,
    source_document_count: int = 1,
) -> dict[str, Any]:
    """Return the enforceable support receipt sealed with Product Intent."""

    evidence_format = str(source_format or "unknown").strip()
    dimensions = _complexity_dimensions(
        facts,
        evidence_bytes=source_size_bytes,
        documents=source_document_count,
    )
    issues: list[str] = []
    if evidence_format not in SUPPORTED_EVIDENCE_FORMATS:
        issues.append("unsupported_evidence_format")
    if source_size_bytes <= 0:
        issues.append("empty_evidence")
    elif source_size_bytes > MAX_EVIDENCE_BYTES:
        issues.append("evidence_too_large")
    _append_limit_issue(issues, dimensions, "documents", MAX_EVIDENCE_DOCUMENTS, "too_many_evidence_documents")
    _append_limit_issue(issues, dimensions, "actors", MAX_ACTORS, "too_many_human_actors")
    _append_limit_issue(issues, dimensions, "state_objects", MAX_STATE_OBJECTS, "too_many_state_objects")
    _append_limit_issue(issues, dimensions, "paths", MAX_FIRST_RELEASE_PATHS, "too_many_first_release_paths")
    _append_limit_issue(issues, dimensions, "external_systems", MAX_SYSTEMS_PER_BOUNDARY, "too_many_external_systems")
    _append_limit_issue(issues, dimensions, "internal_systems", MAX_SYSTEMS_PER_BOUNDARY, "too_many_internal_systems")
    _append_limit_issue(issues, dimensions, "contradictions", MAX_CONTRADICTIONS, "too_many_contradictions")
    _append_limit_issue(issues, dimensions, "ambiguities", MAX_AMBIGUITIES, "too_many_ambiguities")
    _append_limit_issue(issues, dimensions, "safety_boundaries", MAX_SAFETY_BOUNDARIES, "too_many_safety_boundaries")

    return {
        "version": GREENFIELD_OPERATING_ENVELOPE_VERSION,
        "profile": GREENFIELD_OPERATING_PROFILE,
        "status": "supported" if not issues else "unsupported",
        "evidence_format": evidence_format,
        "issues": issues,
        "evidence_contract": {
            "formats": sorted(SUPPORTED_EVIDENCE_FORMATS),
            "languages": list(SUPPORTED_EVIDENCE_LANGUAGES),
            "language_verification": "english_required_operator_and_evaluation_contract",
            "minimum_bytes": 1,
            "maximum_bytes": MAX_EVIDENCE_BYTES,
            "maximum_documents": MAX_EVIDENCE_DOCUMENTS,
        },
        "complexity": {
            "band": _complexity_band(dimensions),
            "dimensions": dimensions,
            "limits": {
                "actors": MAX_ACTORS,
                "state_objects": MAX_STATE_OBJECTS,
                "paths": MAX_FIRST_RELEASE_PATHS,
                "external_systems": MAX_SYSTEMS_PER_BOUNDARY,
                "internal_systems": MAX_SYSTEMS_PER_BOUNDARY,
                "contradictions": MAX_CONTRADICTIONS,
                "ambiguities": MAX_AMBIGUITIES,
                "safety_boundaries": MAX_SAFETY_BOUNDARIES,
            },
        },
        "scope": {
            "product_count": 1,
            "first_release_path_count": 1,
            "write_boundary": "repo_local_governance_package",
            "external_side_effects": "none",
        },
        "filesystem_contract": {
            "repository": "single_local_writable_repository",
            "locking": "exclusive_advisory_file_lock",
            "durability": "same_filesystem_atomic_replace_and_fsync",
            "path_safety": "relative_owned_paths_without_symlink_traversal",
            "package_visibility": "journaled_recovery_not_atomic_generation_pointer",
        },
        "host_contract": {
            "confirmation_hosts": list(SUPPORTED_CONFIRMATION_HOSTS),
            "other_hosts": "proposal_only_unless_deterministic_callback_proven",
        },
        "model_contract": {
            "profiles": list(SUPPORTED_MODEL_PROFILES),
            "authority": "candidate_hypothesis_only",
            "lower_capability_behavior": "clarify_or_fail_safe_without_invention",
        },
    }


def require_supported_greenfield_operating_envelope(value: Mapping[str, Any]) -> None:
    """Fail before confirmation when the request exceeds the declared envelope."""

    if not isinstance(value, Mapping):
        raise ValueError("Greenfield operating envelope is missing")
    if value.get("version") != GREENFIELD_OPERATING_ENVELOPE_VERSION:
        raise ValueError("Greenfield operating envelope version is unsupported")
    if value.get("profile") != GREENFIELD_OPERATING_PROFILE:
        raise ValueError("Greenfield operating envelope profile is unsupported")
    if value.get("status") != "supported" or value.get("issues") != []:
        raise ValueError("Greenfield request is outside the declared operating envelope")
    if value.get("evidence_format") not in SUPPORTED_EVIDENCE_FORMATS:
        raise ValueError("Greenfield operating envelope evidence format is unsupported")
    evidence = value.get("evidence_contract")
    if not isinstance(evidence, Mapping) or evidence.get("languages") != list(SUPPORTED_EVIDENCE_LANGUAGES):
        raise ValueError("Greenfield operating envelope language contract is unsupported")
    host = value.get("host_contract")
    if not isinstance(host, Mapping) or host.get("confirmation_hosts") != list(SUPPORTED_CONFIRMATION_HOSTS):
        raise ValueError("Greenfield operating envelope host contract is unsupported")
    model = value.get("model_contract")
    if not isinstance(model, Mapping) or model.get("profiles") != list(SUPPORTED_MODEL_PROFILES):
        raise ValueError("Greenfield operating envelope model contract is unsupported")
    filesystem = value.get("filesystem_contract")
    if not isinstance(filesystem, Mapping) or filesystem.get("package_visibility") != (
        "journaled_recovery_not_atomic_generation_pointer"
    ):
        raise ValueError("Greenfield operating envelope filesystem contract is unsupported")


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
    }


def _complexity_band(dimensions: Mapping[str, int]) -> str:
    score = 0
    score += _tiered_score(dimensions["evidence_bytes"], moderate=64 * 1024, high=1024 * 1024)
    score += 1 if dimensions["documents"] > 1 else 0
    score += _tiered_score(dimensions["actors"], moderate=4, high=16)
    score += _tiered_score(dimensions["state_objects"], moderate=2, high=8)
    score += _tiered_score(
        dimensions["external_systems"] + dimensions["internal_systems"],
        moderate=4,
        high=16,
    )
    score += _tiered_score(dimensions["contradictions"], moderate=0, high=4)
    score += _tiered_score(dimensions["ambiguities"], moderate=2, high=8)
    score += _tiered_score(dimensions["safety_boundaries"], moderate=2, high=8)
    return "high" if score >= 7 else "moderate" if score >= 3 else "bounded"


def _tiered_score(value: int, *, moderate: int, high: int) -> int:
    return 2 if value > high else 1 if value > moderate else 0


def _append_limit_issue(
    issues: list[str],
    dimensions: Mapping[str, int],
    key: str,
    limit: int,
    issue: str,
) -> None:
    if dimensions[key] > limit:
        issues.append(issue)


def _declared_count(value: Any, *, fallback: Any) -> int:
    count = _count(value)
    if count:
        return count
    return 1 if str(fallback or "").strip() else 0


def _count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


__all__ = [
    "GREENFIELD_OPERATING_ENVELOPE_VERSION",
    "GREENFIELD_OPERATING_PROFILE",
    "SUPPORTED_CONFIRMATION_HOSTS",
    "SUPPORTED_EVIDENCE_FORMATS",
    "SUPPORTED_EVIDENCE_LANGUAGES",
    "SUPPORTED_MODEL_PROFILES",
    "greenfield_operating_envelope_receipt",
    "require_supported_greenfield_operating_envelope",
]
