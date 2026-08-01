"""Declared support boundary for Greenfield Product Intent compilation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


GREENFIELD_OPERATING_ENVELOPE_VERSION = "odylith.greenfield-operating-envelope.v1"
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
SUPPORTED_CONFIRMATION_HOSTS = ("codex", "claude")

MAX_EVIDENCE_BYTES = 8 * 1024 * 1024
MAX_ACTORS = 64
MAX_SYSTEMS_PER_BOUNDARY = 128


def greenfield_operating_envelope_receipt(
    *,
    facts: Mapping[str, Any],
    source_format: str,
    source_size_bytes: int,
) -> dict[str, Any]:
    """Return the enforceable support receipt sealed with Product Intent."""

    evidence_format = str(source_format or "unknown").strip()
    issues: list[str] = []
    if evidence_format not in SUPPORTED_EVIDENCE_FORMATS:
        issues.append("unsupported_evidence_format")
    if source_size_bytes <= 0:
        issues.append("empty_evidence")
    elif source_size_bytes > MAX_EVIDENCE_BYTES:
        issues.append("evidence_too_large")
    if _count(facts.get("human_actors")) > MAX_ACTORS:
        issues.append("too_many_human_actors")
    if _count(facts.get("external_systems")) > MAX_SYSTEMS_PER_BOUNDARY:
        issues.append("too_many_external_systems")
    if _count(facts.get("internal_systems")) > MAX_SYSTEMS_PER_BOUNDARY:
        issues.append("too_many_internal_systems")

    return {
        "version": GREENFIELD_OPERATING_ENVELOPE_VERSION,
        "profile": GREENFIELD_OPERATING_PROFILE,
        "status": "supported" if not issues else "unsupported",
        "evidence_format": evidence_format,
        "issues": issues,
        "scope": {
            "product_count": 1,
            "first_release_path_count": 1,
            "write_boundary": "repo_local_governance_package",
            "external_side_effects": "none",
        },
        "host_contract": {
            "confirmation_hosts": list(SUPPORTED_CONFIRMATION_HOSTS),
            "other_hosts": "read_only_unless_contract_proven",
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


def _count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


__all__ = [
    "GREENFIELD_OPERATING_ENVELOPE_VERSION",
    "GREENFIELD_OPERATING_PROFILE",
    "SUPPORTED_CONFIRMATION_HOSTS",
    "SUPPORTED_EVIDENCE_FORMATS",
    "greenfield_operating_envelope_receipt",
    "require_supported_greenfield_operating_envelope",
]
