"""Structured evidence contract for independent automated Greenfield audits."""

from __future__ import annotations

import json
from typing import Any


RELEASE_AUDIT_EVIDENCE_VERSION = "odylith.greenfield.matrix.release-audit-evidence.v1"
AUTOMATED_ADVERSARIAL_REVIEWER_KIND = "automated_adversarial"


def audit_evidence_issues(audit: Any, evidence_text: str) -> tuple[str, ...]:
    """Verify that stored audit evidence identifies the reviewed case and reviewer."""

    try:
        evidence = json.loads(evidence_text)
    except json.JSONDecodeError:
        return ("review evidence must be valid JSON",)
    if not isinstance(evidence, dict):
        return ("review evidence must be a JSON object",)

    issues: list[str] = []
    expected = {
        "version": RELEASE_AUDIT_EVIDENCE_VERSION,
        "case_id": _text(getattr(audit, "case_id", "")),
        "prompt_sha256": _text(getattr(audit, "prompt_sha256", "")),
        "source_artifact_sha256": _text(getattr(audit, "source_artifact_sha256", "")),
        "source_excerpt_sha256": _text(getattr(audit, "source_excerpt_sha256", "")),
        "reviewer_id": _text(getattr(audit, "reviewer_id", "")),
        "reviewer_kind": AUTOMATED_ADVERSARIAL_REVIEWER_KIND,
        "review_method": _text(getattr(audit, "review_method", "")),
        "reviewed_on": _text(getattr(audit, "reviewed_on", "")),
        "review_status": "approved",
        "independent": True,
        "source_binding": "verified",
        "derivation_assessment": "approved",
    }
    for field, value in expected.items():
        if evidence.get(field) != value:
            issues.append(f"review evidence {field} does not match the audit record")
    if not _text(evidence.get("rationale")):
        issues.append("review evidence must include a non-empty rationale")
    return tuple(issues)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


__all__ = [
    "AUTOMATED_ADVERSARIAL_REVIEWER_KIND",
    "RELEASE_AUDIT_EVIDENCE_VERSION",
    "audit_evidence_issues",
]
