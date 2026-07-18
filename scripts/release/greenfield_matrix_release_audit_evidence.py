"""Structured evidence contract for hash-bound automated Greenfield reviews."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import hashlib
import json
from typing import Any
from urllib.parse import urlparse


RELEASE_AUDIT_EVIDENCE_VERSION = "odylith.greenfield.matrix.release-audit-evidence.v8"
RELEASE_AUDIT_CLAIM_CLASS = "operator-supplied-hash-bound-review-evidence"
AUTOMATED_ADVERSARIAL_REVIEWER_KIND = "automated_adversarial"


def audit_request_sha256(request: Any) -> str:
    """Hash the exact review request that a reviewer was asked to assess."""

    payload = {
        "case_id": _text(_value(request, "case_id")),
        "prompt_sha256": _text(_value(request, "prompt_sha256")).casefold(),
        "source_artifact_sha256": _text(_value(request, "source_artifact_sha256")).casefold(),
        "source_excerpt_sha256": _text(_value(request, "source_excerpt_sha256")).casefold(),
        "source_id": _text(_value(request, "source_id")),
        "source_uri": _normalized_uri(_value(request, "source_uri")),
        "source_family": _text(_value(request, "source_family")),
        "stressors": _text_sequence(_value(request, "stressors")),
        "source_verification_method": _text(_value(request, "source_verification_method")),
        "source_verification_uri": _normalized_uri(_value(request, "source_verification_uri")),
        "required_assessments": {
            "derivation_assessment": _text(_mapping_value(request, "required_assessments", "derivation_assessment")),
            "source_binding": _text(_mapping_value(request, "required_assessments", "source_binding")),
            "source_family_assessment": _text(
                _mapping_value(request, "required_assessments", "source_family_assessment")
            ),
        },
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_request_for_case(
    case: Any,
    *,
    source_verification_method: Any,
    source_verification_uri: Any,
) -> dict[str, Any]:
    """Build the exact request an audit record must bind from current case facts."""

    provenance = getattr(case, "provenance", None)
    stressors = getattr(case, "stressors", ())
    return {
        "case_id": _text(getattr(case, "case_id", "")),
        "prompt_sha256": _text(getattr(provenance, "derived_prompt_sha256", "")),
        "source_artifact_sha256": _text(getattr(provenance, "source_artifact_sha256", "")),
        "source_excerpt_sha256": _text(getattr(provenance, "source_excerpt_sha256", "")),
        "source_id": _text(getattr(provenance, "source_id", "")),
        "source_uri": _text(getattr(provenance, "source_uri", "")),
        "source_family": _text(getattr(provenance, "source_family", "")),
        "stressors": list(_text_sequence(stressors)),
        "source_verification_method": _text(source_verification_method),
        "source_verification_uri": _text(source_verification_uri),
        "required_assessments": {
            "source_binding": "verified",
            "source_family_assessment": "approved",
            "derivation_assessment": "approved",
        },
    }


def request_hash_matches(request: Any) -> bool:
    """Return whether a supplied audit request carries its canonical binding hash."""

    return _text(_value(request, "audit_request_sha256")).casefold() == audit_request_sha256(request)


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
        "audit_request_sha256": _text(getattr(audit, "audit_request_sha256", "")),
        "source_id": _text(getattr(audit, "source_id", "")),
        "source_uri": _text(getattr(audit, "source_uri", "")),
        "source_verification_method": _text(getattr(audit, "source_verification_method", "")),
        "source_verification_uri": _text(getattr(audit, "source_verification_uri", "")),
        "source_verified_on": _text(getattr(audit, "source_verified_on", "")),
        "source_verification_path": _text(getattr(audit, "source_verification_path", "")),
        "source_verification_sha256": _text(getattr(audit, "source_verification_sha256", "")),
        "source_family": _text(source_family),
        "review_context_label": _text(getattr(audit, "review_context_label", "")),
        "reviewer_kind": AUTOMATED_ADVERSARIAL_REVIEWER_KIND,
        "review_method": _text(getattr(audit, "review_method", "")),
        "reviewed_on": _text(getattr(audit, "reviewed_on", "")),
        "review_status": "approved",
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
    """Verify that a review record binds its checked remote source identity."""

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
        expected_uri = github_repository_verification_uri(getattr(audit, "source_id", ""))
        assert expected_uri is not None
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


def github_repository_verification_uri(source_id: Any) -> str | None:
    repository_id = _github_repository_id(source_id)
    if repository_id is None:
        return None
    return f"https://api.github.com/repositories/{repository_id}"


def _normalized_uri(value: Any) -> str:
    return _text(value).rstrip("/")


def _value(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else ""


def _mapping_value(value: Any, key: str, nested_key: str) -> Any:
    nested = _value(value, key)
    return nested.get(nested_key) if isinstance(nested, Mapping) else ""


def _text_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


__all__ = [
    "AUTOMATED_ADVERSARIAL_REVIEWER_KIND",
    "RELEASE_AUDIT_CLAIM_CLASS",
    "RELEASE_AUDIT_EVIDENCE_VERSION",
    "audit_request_for_case",
    "audit_request_sha256",
    "audit_evidence_issues",
    "audit_source_verification_issues",
    "github_repository_verification_uri",
    "request_hash_matches",
    "source_verification_payload_issues",
]
