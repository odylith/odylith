"""Bind retained raw Greenfield output to its deterministic canonical projection."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    canonical_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_json import (
    encode_greenfield_model_value,
)


def retained_canonical_candidate_hash_issues(
    *,
    raw_candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    evidence_text: str,
) -> tuple[str, ...]:
    """Return fail-closed issues for one retained raw/canonical hash binding."""

    evidence = retained_canonical_candidate_hash_evidence(
        raw_candidate=raw_candidate,
        receipt=receipt,
        evidence_text=evidence_text,
    )
    return tuple(str(issue) for issue in evidence["issues"])


def retained_canonical_candidate_hash_evidence(
    *,
    raw_candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    evidence_text: str,
) -> dict[str, Any]:
    """Prove the runtime admitted exactly the retained host bytes after projection.

    Canonicalization may replace contextual host citations with exact source
    offsets, so raw and canonical hashes are independently bound. No additional
    semantic authority or mutable admission witness participates in this proof.
    """

    candidate = dict(raw_candidate)
    summary: dict[str, Any] = {
        "raw_candidate_sha256": "",
        "canonical_candidate_sha256": "",
        "canonical_projection_verified": False,
    }
    if not candidate:
        return {
            **summary,
            "status": "failed",
            "issues": ["retained raw host candidate is missing"],
        }

    issues: list[str] = []
    try:
        raw_sha256 = hashlib.sha256(
            encode_greenfield_model_value(candidate)
        ).hexdigest()
        canonical = canonical_greenfield_host_candidate(
            candidate,
            evidence_text=evidence_text,
        )
        canonical_sha256 = hashlib.sha256(
            encode_greenfield_model_value(canonical)
        ).hexdigest()
    except (RuntimeError, TypeError, ValueError):
        return {
            **summary,
            "status": "failed",
            "issues": ["retained raw host candidate cannot be canonically projected"],
        }

    summary.update(
        raw_candidate_sha256=raw_sha256,
        canonical_candidate_sha256=canonical_sha256,
        canonical_projection_verified=True,
    )
    expected_receipt_fields = {
        "version",
        "contract_version",
        "canonical_version",
        "source_sha256",
        "raw_candidate_sha256",
        "canonical_candidate_sha256",
    }
    if set(receipt) != expected_receipt_fields:
        issues.append("sealed host candidate receipt has missing or unsupported fields")
    if receipt.get("version") != HOST_CANDIDATE_RECEIPT_VERSION:
        issues.append("sealed host candidate receipt version is invalid")
    if receipt.get("contract_version") != HOST_CANDIDATE_CONTRACT_VERSION:
        issues.append("sealed host candidate contract version is invalid")
    if receipt.get("canonical_version") != GREENFIELD_INTENT_AUTHORING_VERSION:
        issues.append("sealed host candidate canonical version is invalid")
    expected_source_sha256 = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
    if receipt.get("source_sha256") != expected_source_sha256:
        issues.append("sealed host candidate source hash does not match retained evidence")
    if receipt.get("raw_candidate_sha256") != raw_sha256:
        issues.append("sealed raw candidate hash does not match retained host output")
    if receipt.get("canonical_candidate_sha256") != canonical_sha256:
        issues.append(
            "sealed canonical candidate hash does not match deterministic projection"
        )

    issues = list(dict.fromkeys(issues))
    return {
        **summary,
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


__all__ = [
    "retained_canonical_candidate_hash_evidence",
    "retained_canonical_candidate_hash_issues",
]
