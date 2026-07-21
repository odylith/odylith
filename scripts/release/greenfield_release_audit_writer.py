"""Materialize explicitly supplied Greenfield review results into audit evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_corpus_provenance import RELEASE_AUDIT_VERSION
from greenfield_matrix_release_artifacts import repo_artifact_path
from greenfield_matrix_release_artifacts import safe_artifact_identifier
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_matrix_release_artifacts import sha256_text
from greenfield_matrix_release_audit_evidence import AUTOMATED_ADVERSARIAL_REVIEWER_KIND
from greenfield_matrix_release_audit_evidence import RELEASE_AUDIT_CLAIM_CLASS
from greenfield_matrix_release_audit_evidence import RELEASE_AUDIT_EVIDENCE_VERSION
from greenfield_matrix_release_audit_evidence import audit_request_for_case
from greenfield_matrix_release_audit_evidence import audit_request_sha256
from greenfield_matrix_release_audit_evidence import case_confirmed_intent_sha256
from greenfield_matrix_release_audit_evidence import request_hash_matches
from greenfield_matrix_release_audit_evidence import source_custody_fingerprint
from greenfield_release_audit_verification import AUDIT_REQUEST_PLAN_VERSION
from greenfield_release_audit_verification import AUDIT_SOURCE_VERIFICATION_VERSION
from greenfield_release_source_capture import json_text
from greenfield_release_source_capture import load_json_object
from greenfield_release_source_capture import release_output_lock
from greenfield_release_source_capture import repo_relative
from greenfield_release_source_capture import reserve_output_lock
from greenfield_release_source_capture import single_line
from greenfield_release_source_capture import sync_directory
from greenfield_release_source_capture import sync_file


AUDIT_REVIEW_RESULTS_VERSION = "odylith.greenfield.matrix.audit-review-results.v3"
AUDIT_REVIEW_RESULTS_CLAIM_CLASS = "operator-supplied-hash-bound-review-results"
AUDIT_BUNDLE_FILENAME = "greenfield-release-audit.v9.json"


def write_release_audit_bundle(
    *,
    source_case_file: Path,
    audit_request_plan: Path,
    source_verification_root: Path,
    review_results_file: Path,
    output_root: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Write an audit bundle only when every supplied reviewer result is explicit and bound."""

    root = Path(repo_root).expanduser().resolve()
    cases = {case.case_id: case for case in load_case_file(Path(source_case_file).resolve())}
    requests = _requests(load_json_object(Path(audit_request_plan).resolve()))
    verification_root = Path(source_verification_root).expanduser().resolve()
    verifications = _verifications(load_json_object(verification_root / "source-verifications.v2.json"))
    results = _results(load_json_object(Path(review_results_file).resolve()))
    if set(results) != set(requests):
        raise RuntimeError("review results must cover exactly the audit request case IDs")
    output = Path(output_root).expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"audit bundle output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path, lock_fd = reserve_output_lock(output)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        evidence_dir = staging / "review-evidence"
        evidence_dir.mkdir(parents=True)
        audits: list[dict[str, Any]] = []
        for case_id in sorted(requests):
            case = cases.get(case_id)
            request = requests[case_id]
            verification = verifications.get(case_id)
            result = results[case_id]
            if case is None or verification is None:
                raise RuntimeError(f"audit bundle lacks case or verification record: {case_id}")
            _validate_result(result, case_id, request)
            provenance = case.provenance
            _validate_binding(case_id, case, request, verification)
            verification_path = repo_artifact_path(
                verification_root, single_line(verification.get("source_verification_path"))
            )
            if verification_path is None or not verification_path.is_file():
                raise RuntimeError(f"audit verification response is missing: {case_id}")
            if sha256_file(verification_path) != single_line(verification.get("source_verification_sha256")):
                raise RuntimeError(f"audit verification response hash does not match: {case_id}")
            verification_relative = repo_relative(verification_path, root)
            review_evidence = _review_evidence(
                case,
                verification,
                result,
                verification_relative,
            )
            staged_evidence = evidence_dir / f"{safe_artifact_identifier(case_id)}.json"
            evidence_text = json_text(review_evidence)
            staged_evidence.write_text(evidence_text, encoding="utf-8")
            sync_file(staged_evidence)
            audit = {
                "case_id": case_id,
                "prompt_sha256": provenance.derived_prompt_sha256,
                "confirmed_intent_sha256": case_confirmed_intent_sha256(case),
                "source_artifact_sha256": provenance.source_artifact_sha256,
                "source_excerpt_sha256": provenance.source_excerpt_sha256,
                "audit_request_sha256": request["audit_request_sha256"],
                "source_id": provenance.source_id,
                "source_uri": provenance.source_uri,
                "source_verification_method": verification["source_verification_method"],
                "source_verification_uri": verification["source_verification_uri"],
                "source_verified_on": verification["source_verified_on"],
                "source_verification_path": verification_relative,
                "source_verification_sha256": verification["source_verification_sha256"],
                "review_context_label": result["review_context_label"],
                "reviewer_kind": result["reviewer_kind"],
                "review_method": result["review_method"],
                "reviewed_on": result["reviewed_on"],
                "review_status": result["review_status"],
                "review_evidence_path": repo_relative(output / "review-evidence" / staged_evidence.name, root),
                "review_evidence_sha256": sha256_text(evidence_text),
            }
            audits.append(audit)
        bundle = {
            "version": RELEASE_AUDIT_VERSION,
            "claim_class": RELEASE_AUDIT_CLAIM_CLASS,
            "source_case_file": repo_relative(Path(source_case_file), root),
            "source_case_file_sha256": sha256_file(Path(source_case_file)),
            "audit_request_plan": repo_relative(Path(audit_request_plan), root),
            "audit_request_plan_sha256": sha256_file(Path(audit_request_plan)),
            "source_verifications": repo_relative(verification_root / "source-verifications.v2.json", root),
            "source_verifications_sha256": sha256_file(verification_root / "source-verifications.v2.json"),
            "review_results": repo_relative(Path(review_results_file), root),
            "review_results_sha256": sha256_file(Path(review_results_file)),
            "audits": audits,
        }
        bundle_path = staging / AUDIT_BUNDLE_FILENAME
        bundle_path.write_text(json_text(bundle), encoding="utf-8")
        sync_file(bundle_path)
        sync_directory(staging)
        if output.exists():
            raise RuntimeError(f"audit bundle output appeared during write: {output}")
        staging.replace(output)
        sync_directory(output.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        release_output_lock(lock_path, lock_fd)
    return bundle


def _requests(plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if single_line(plan.get("version")) != AUDIT_REQUEST_PLAN_VERSION:
        raise RuntimeError("unsupported Greenfield audit request plan")
    if single_line(plan.get("claim_class")) != "audit-requests-only":
        raise RuntimeError("audit request plan must declare the requests-only claim class")
    requests = _rows_by_case_id(plan.get("requests"), "audit request plan")
    if any(not request_hash_matches(request) for request in requests.values()):
        raise RuntimeError("audit request plan contains an invalid audit_request_sha256")
    return requests


def _verifications(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if single_line(manifest.get("version")) != AUDIT_SOURCE_VERIFICATION_VERSION:
        raise RuntimeError("unsupported Greenfield source verification manifest")
    if single_line(manifest.get("claim_class")) != "source-verification-only":
        raise RuntimeError("source verification manifest must declare the verification-only claim class")
    return _rows_by_case_id(manifest.get("records"), "source verification manifest")


def _results(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if single_line(payload.get("version")) != AUDIT_REVIEW_RESULTS_VERSION:
        raise RuntimeError("unsupported Greenfield audit review results")
    if single_line(payload.get("claim_class")) != AUDIT_REVIEW_RESULTS_CLAIM_CLASS:
        raise RuntimeError("audit review results must declare the operator-supplied hash-bound claim class")
    return _rows_by_case_id(payload.get("reviews"), "audit review results")


def _rows_by_case_id(value: Any, label: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or not value:
        raise RuntimeError(f"{label} must define non-empty rows")
    rows: dict[str, Mapping[str, Any]] = {}
    for row in value:
        if not isinstance(row, Mapping):
            raise RuntimeError(f"{label} contains an invalid row")
        case_id = single_line(row.get("case_id"))
        if safe_artifact_identifier(case_id) is None or case_id in rows:
            raise RuntimeError(f"{label} must use unique safe case IDs")
        rows[case_id] = row
    return rows


def _validate_result(result: Mapping[str, Any], case_id: str, request: Mapping[str, Any]) -> None:
    expected = {
        "reviewer_kind": AUTOMATED_ADVERSARIAL_REVIEWER_KIND,
        "review_status": "approved",
        "source_binding": "verified",
        "source_family_assessment": "approved",
        "derivation_assessment": "approved",
    }
    for field, value in expected.items():
        if single_line(result.get(field)).casefold() != value:
            raise RuntimeError(f"review result is not approved for {field}: {case_id}")
    for field in ("audit_request_sha256", "review_context_label", "review_method", "reviewed_on", "rationale"):
        if not single_line(result.get(field)):
            raise RuntimeError(f"review result lacks {field}: {case_id}")
    if single_line(result.get("audit_request_sha256")) != single_line(request.get("audit_request_sha256")):
        raise RuntimeError(f"review result does not bind the audit request: {case_id}")


def _validate_binding(
    case_id: str,
    case: Any,
    request: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> None:
    provenance = case.provenance
    provenance_values = {
        "prompt_sha256": provenance.derived_prompt_sha256,
        "confirmed_intent_sha256": case_confirmed_intent_sha256(case),
        "source_artifact_sha256": provenance.source_artifact_sha256,
        "source_excerpt_sha256": provenance.source_excerpt_sha256,
        "source_id": provenance.source_id,
        "source_uri": provenance.source_uri,
        "source_family": provenance.source_family,
    }
    for field, value in provenance_values.items():
        if single_line(request.get(field)) != single_line(value):
            raise RuntimeError(f"audit request and case provenance diverge on {field}: {case_id}")
    for field in (
        "source_verification_method",
        "source_verification_uri",
    ):
        if single_line(request.get(field)) != single_line(verification.get(field)):
            raise RuntimeError(f"audit request and verification diverge on {field}: {case_id}")
    if single_line(verification.get("audit_request_sha256")) != single_line(request.get("audit_request_sha256")):
        raise RuntimeError(f"audit request and verification diverge on audit_request_sha256: {case_id}")
    if single_line(verification.get("source_custody_sha256")) != source_custody_fingerprint(request):
        raise RuntimeError(f"audit request and verification diverge on source_custody_sha256: {case_id}")
    expected_request = audit_request_for_case(
        case,
        source_verification_method=verification.get("source_verification_method"),
        source_verification_uri=verification.get("source_verification_uri"),
    )
    if single_line(request.get("audit_request_sha256")) != audit_request_sha256(expected_request):
        raise RuntimeError(f"audit request does not bind current case semantics: {case_id}")


def _review_evidence(
    case: Any,
    verification: Mapping[str, Any],
    result: Mapping[str, Any],
    verification_path: str,
) -> dict[str, Any]:
    provenance = case.provenance
    return {
        "version": RELEASE_AUDIT_EVIDENCE_VERSION,
        "case_id": case.case_id,
        "prompt_sha256": provenance.derived_prompt_sha256,
        "confirmed_intent_sha256": case_confirmed_intent_sha256(case),
        "source_artifact_sha256": provenance.source_artifact_sha256,
        "source_excerpt_sha256": provenance.source_excerpt_sha256,
        "audit_request_sha256": result["audit_request_sha256"],
        "source_id": provenance.source_id,
        "source_uri": provenance.source_uri,
        "source_verification_method": verification["source_verification_method"],
        "source_verification_uri": verification["source_verification_uri"],
        "source_verified_on": verification["source_verified_on"],
        "source_verification_path": verification_path,
        "source_verification_sha256": verification["source_verification_sha256"],
        "source_family": provenance.source_family,
        "review_context_label": result["review_context_label"],
        "reviewer_kind": result["reviewer_kind"],
        "review_method": result["review_method"],
        "reviewed_on": result["reviewed_on"],
        "review_status": result["review_status"],
        "source_binding": result["source_binding"],
        "source_family_assessment": result["source_family_assessment"],
        "derivation_assessment": result["derivation_assessment"],
        "rationale": result["rationale"],
    }
