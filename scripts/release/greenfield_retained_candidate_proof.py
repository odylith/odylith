"""Reconstruct the sealed Greenfield candidate from retained reviewer custody."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_review_custody import (
    candidate_review_sha256,
    project_reviewed_custody,
)


def retained_admitted_candidate_hash_issues(
    *,
    review_input_candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    evidence_text: str,
) -> tuple[str, ...]:
    """Bind an admitted final hash to the one deterministic custody projection."""

    candidate = dict(review_input_candidate)
    if not candidate:
        return ("retained host-native reviewer input candidate is missing",)
    issues: list[str] = []
    try:
        review_input_sha256 = candidate_review_sha256(candidate)
    except (RuntimeError, TypeError, ValueError):
        return ("retained host-native reviewer input candidate is invalid",)
    if receipt.get("review_input_candidate_sha256") != review_input_sha256:
        issues.append("retained reviewer input does not match the sealed review-input hash")
    witness = receipt.get("admission_witness")
    witness = dict(witness) if isinstance(witness, Mapping) else {}
    try:
        projected = project_reviewed_custody(
            candidate,
            component_custody=witness.get("component_custody"),
            constraint_custody=witness.get("constraint_custody"),
            evidence_text=evidence_text,
        )
        final_sha256 = candidate_review_sha256(projected)
    except (RuntimeError, TypeError, ValueError):
        issues.append("retained reviewer custody cannot produce a valid final candidate")
    else:
        if receipt.get("candidate_sha256") != final_sha256:
            issues.append("sealed final candidate hash does not match retained reviewer custody")
    return tuple(dict.fromkeys(issues))


__all__ = ["retained_admitted_candidate_hash_issues"]
