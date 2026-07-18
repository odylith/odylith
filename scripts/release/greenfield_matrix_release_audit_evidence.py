"""Structured evidence contract for independent automated Greenfield audits."""

from __future__ import annotations

from datetime import date
import json
from typing import Any
from urllib.parse import urlparse


RELEASE_AUDIT_EVIDENCE_VERSION = "odylith.greenfield.matrix.release-audit-evidence.v4"
AUTOMATED_ADVERSARIAL_REVIEWER_KIND = "automated_adversarial"


def audit_evidence_issues(
    audit: Any,
    evidence_text: str,
    source_family: str,
) -> tuple[str, ...]:
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
        "source_id": _text(getattr(audit, "source_id", "")),
        "source_uri": _text(getattr(audit, "source_uri", "")),
        "source_verification_method": _text(getattr(audit, "source_verification_method", "")),
        "source_verification_uri": _text(getattr(audit, "source_verification_uri", "")),
        "source_verified_on": _text(getattr(audit, "source_verified_on", "")),
        "source_verification_path": _text(getattr(audit, "source_verification_path", "")),
        "source_verification_sha256": _text(getattr(audit, "source_verification_sha256", "")),
        "source_family": _text(source_family),
        "reviewer_id": _text(getattr(audit, "reviewer_id", "")),
        "reviewer_kind": AUTOMATED_ADVERSARIAL_REVIEWER_KIND,
        "review_method": _text(getattr(audit, "review_method", "")),
        "reviewed_on": _text(getattr(audit, "reviewed_on", "")),
        "review_status": "approved",
        "independent": True,
        "source_binding": "verified",
        "source_family_assessment": "approved",
        "derivation_assessment": "approved",
    }
    for field, value in expected.items():
        if evidence.get(field) != value:
            owner = "case provenance" if field == "source_family" else "audit record"
            issues.append(f"review evidence {field} does not match the {owner}")
    if not _text(evidence.get("rationale")):
        issues.append("review evidence must include a non-empty rationale")
    return tuple(issues)


def audit_source_verification_issues(audit: Any, provenance: Any) -> tuple[str, ...]:
    """Verify that an independent audit binds its checked remote source identity."""

    if _text(getattr(audit, "source_id", "")) != _text(getattr(provenance, "source_id", "")):
        return ("does not match source_id",)
    if _text(getattr(audit, "source_uri", "")) != _text(getattr(provenance, "source_uri", "")):
        return ("does not match source_uri",)
    if not _text(getattr(audit, "source_verification_method", "")):
        return ("must name a source_verification_method",)
    verification_uri = urlparse(_text(getattr(audit, "source_verification_uri", "")))
    if verification_uri.scheme not in {"http", "https"} or not verification_uri.netloc:
        return ("must use an absolute source_verification_uri",)
    github_repository_id = _github_repository_id(getattr(audit, "source_id", ""))
    if github_repository_id is not None:
        expected_uri = f"https://api.github.com/repositories/{github_repository_id}"
        if _normalized_uri(getattr(audit, "source_verification_uri", "")) != expected_uri:
            return ("must use the canonical GitHub repository verification endpoint",)
    try:
        date.fromisoformat(_text(getattr(audit, "source_verified_on", "")))
    except ValueError:
        return ("must use an ISO source_verified_on date",)
    return ()


def source_verification_payload_issues(audit: Any, verification_text: str) -> tuple[str, ...]:
    """Verify that retained verification bytes identify the audited remote source."""

    try:
        payload = json.loads(verification_text)
    except json.JSONDecodeError:
        return ("source verification response must be valid JSON",)
    if not isinstance(payload, dict):
        return ("source verification response must be a JSON object",)

    source_id = _text(getattr(audit, "source_id", ""))
    source_uri = _normalized_uri(getattr(audit, "source_uri", ""))
    github_repository_id = _github_repository_id(source_id)
    if github_repository_id is not None:
        if payload.get("id") != github_repository_id:
            return ("source verification response does not match the GitHub repository ID",)
        if _normalized_uri(payload.get("html_url")) != source_uri:
            return ("source verification response does not match source_uri",)
        return ()
    if _text(payload.get("source_id")) != source_id:
        return ("source verification response does not match source_id",)
    if _normalized_uri(payload.get("source_uri")) != source_uri:
        return ("source verification response does not match source_uri",)
    return ()


def _github_repository_id(value: Any) -> int | None:
    source_id = _text(value)
    prefix = "github-repository:"
    if not source_id.startswith(prefix):
        return None
    identifier = source_id.removeprefix(prefix)
    if not identifier.isdigit() or int(identifier) <= 0:
        return None
    return int(identifier)


def _normalized_uri(value: Any) -> str:
    return _text(value).rstrip("/")


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


__all__ = [
    "AUTOMATED_ADVERSARIAL_REVIEWER_KIND",
    "RELEASE_AUDIT_EVIDENCE_VERSION",
    "audit_evidence_issues",
    "audit_source_verification_issues",
    "source_verification_payload_issues",
]
