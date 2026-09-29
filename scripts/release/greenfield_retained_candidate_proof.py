"""Reconstruct the sealed Greenfield candidate from retained reviewer custody."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_json import (
    encode_greenfield_model_value,
)
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

    evidence = retained_admitted_candidate_hash_evidence(
        review_input_candidate=review_input_candidate,
        receipt=receipt,
        evidence_text=evidence_text,
    )
    return tuple(str(issue) for issue in evidence["issues"])


def retained_admitted_candidate_hash_evidence(
    *,
    review_input_candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    evidence_text: str,
) -> dict[str, Any]:
    """Return privacy-safe proof of distinct review-input and projected-final custody."""

    candidate = dict(review_input_candidate)
    summary: dict[str, Any] = {
        "review_input_candidate_sha256": "",
        "final_candidate_sha256": "",
        "review_input_source_precedence_present": "source_precedence" in candidate,
        "source_precedence_custody_count": 0,
        "source_precedence_custody_sha256": "",
        "source_precedence_projected": False,
        "hashes_are_distinct": False,
    }
    if not candidate:
        return {
            **summary,
            "status": "failed",
            "issues": ["retained host-native reviewer input candidate is missing"],
        }
    issues: list[str] = []
    try:
        review_input_sha256 = candidate_review_sha256(candidate)
    except (RuntimeError, TypeError, ValueError):
        return {
            **summary,
            "status": "failed",
            "issues": ["retained host-native reviewer input candidate is invalid"],
        }
    summary["review_input_candidate_sha256"] = review_input_sha256
    if receipt.get("review_input_candidate_sha256") != review_input_sha256:
        issues.append("retained reviewer input does not match the sealed review-input hash")
    witness = receipt.get("admission_witness")
    witness = dict(witness) if isinstance(witness, Mapping) else {}
    precedence_custody = witness.get("source_precedence_custody")
    if isinstance(precedence_custody, list):
        summary["source_precedence_custody_count"] = len(precedence_custody)
        try:
            summary["source_precedence_custody_sha256"] = hashlib.sha256(
                encode_greenfield_model_value(precedence_custody)
            ).hexdigest()
        except (TypeError, ValueError):
            pass
    try:
        projected = project_reviewed_custody(
            candidate,
            component_custody=witness.get("component_custody"),
            source_precedence_custody=witness.get("source_precedence_custody"),
            constraint_custody=witness.get("constraint_custody"),
            evidence_text=evidence_text,
        )
        final_sha256 = candidate_review_sha256(projected)
    except (RuntimeError, TypeError, ValueError):
        issues.append("retained reviewer custody cannot produce a valid final candidate")
    else:
        summary["source_precedence_projected"] = (
            projected.get("source_precedence") == precedence_custody
        )
        summary["final_candidate_sha256"] = final_sha256
        summary["hashes_are_distinct"] = final_sha256 != review_input_sha256
        if not summary["source_precedence_projected"]:
            issues.append("retained reviewer precedence custody was not projected exactly")
        if not summary["hashes_are_distinct"]:
            issues.append("review-input and projected final candidate hashes are not distinct")
        if receipt.get("candidate_sha256") != final_sha256:
            issues.append("sealed final candidate hash does not match retained reviewer custody")
    issues = list(dict.fromkeys(issues))
    return {
        **summary,
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


__all__ = [
    "retained_admitted_candidate_hash_evidence",
    "retained_admitted_candidate_hash_issues",
]
