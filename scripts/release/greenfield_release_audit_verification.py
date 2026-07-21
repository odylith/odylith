"""Retain and validate remote source records for Greenfield audit requests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from greenfield_matrix_release_audit_evidence import github_repository_verification_uri
from greenfield_matrix_release_audit_evidence import request_hash_matches
from greenfield_matrix_release_audit_evidence import source_custody_fingerprint
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_matrix_release_artifacts import safe_artifact_identifier
from greenfield_matrix_release_artifacts import repo_artifact_path
from greenfield_release_source_capture import FetchJson
from greenfield_release_source_capture import fetch_github_json
from greenfield_release_source_capture import json_text
from greenfield_release_source_capture import load_json_object
from greenfield_release_source_capture import normalize_fetch_result
from greenfield_release_source_capture import now_timestamp
from greenfield_release_source_capture import release_output_lock
from greenfield_release_source_capture import repo_relative
from greenfield_release_source_capture import reserve_output_lock
from greenfield_release_source_capture import sha256_bytes
from greenfield_release_source_capture import single_line
from greenfield_release_source_capture import sync_directory
from greenfield_release_source_capture import sync_file
from greenfield_release_source_capture import validated_timestamp


AUDIT_REQUEST_PLAN_VERSION = "odylith.greenfield.matrix.audit-request-plan.v3"
AUDIT_SOURCE_VERIFICATION_VERSION = "odylith.greenfield.matrix.audit-source-verification.v2"
AUDIT_SOURCE_VERIFICATION_MANIFEST = "source-verifications.v2.json"


def capture_audit_source_verifications(
    *,
    audit_request_plan: Path,
    output_root: Path,
    repo_root: Path,
    captured_at: str | None = None,
    fetch_json: FetchJson | None = None,
) -> dict[str, Any]:
    """Capture remote source records for audit requests without creating review approvals."""

    root = Path(repo_root).expanduser().resolve()
    plan_path = Path(audit_request_plan).expanduser().resolve()
    plan = load_json_object(plan_path)
    requests = _audit_requests(plan)
    output = Path(output_root).expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"audit verification output already exists: {output}")
    captured = validated_timestamp(captured_at or now_timestamp())
    fetch = fetch_json or fetch_github_json
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path, lock_fd = reserve_output_lock(output)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        records_dir = staging / "records"
        records_dir.mkdir(parents=True)
        records: list[dict[str, Any]] = []
        for request in requests:
            case_id = single_line(request.get("case_id"))
            source_id = single_line(request.get("source_id"))
            source_uri = single_line(request.get("source_uri"))
            verification_uri = single_line(request.get("source_verification_uri"))
            expected_uri = github_repository_verification_uri(source_id)
            if not case_id or not source_uri or expected_uri is None or verification_uri != expected_uri:
                raise RuntimeError(f"audit request has invalid GitHub source verification: {case_id or source_id}")
            fetched = normalize_fetch_result(fetch(verification_uri))
            _verify_repository_payload(fetched.payload, source_id, source_uri, case_id)
            relative_path = (Path("records") / f"{case_id}.json").as_posix()
            record_path = records_dir / f"{case_id}.json"
            record_path.write_bytes(fetched.body)
            sync_file(record_path)
            records.append(
                {
                    "case_id": case_id,
                    "audit_request_sha256": single_line(request.get("audit_request_sha256")),
                    "source_id": source_id,
                    "source_uri": source_uri,
                    "source_verification_method": single_line(request.get("source_verification_method")),
                    "source_verification_uri": verification_uri,
                    "source_custody_sha256": source_custody_fingerprint(request),
                    "source_verified_on": captured[:10],
                    "source_verification_path": relative_path,
                    "source_verification_sha256": sha256_bytes(fetched.body),
                    "response_headers": dict(sorted(fetched.headers.items())),
                }
            )
        manifest = {
            "version": AUDIT_SOURCE_VERIFICATION_VERSION,
            "claim_class": "source-verification-only",
            "audit_request_plan": repo_relative(plan_path, root),
            "captured_at": captured,
            "record_count": len(records),
            "records": records,
        }
        manifest_path = staging / AUDIT_SOURCE_VERIFICATION_MANIFEST
        manifest_path.write_text(json_text(manifest), encoding="utf-8")
        sync_file(manifest_path)
        sync_directory(staging)
        if output.exists():
            raise RuntimeError(f"audit verification output appeared during capture: {output}")
        staging.replace(output)
        sync_directory(output.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        release_output_lock(lock_path, lock_fd)
    return manifest


def rebind_audit_source_verifications(
    *,
    audit_request_plan: Path,
    source_verification_root: Path,
    expected_source_verification_sha256: str,
    output_root: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Rebind retained verified source responses to an equivalent new request plan.

    A request-plan change can alter prompt hashes without changing the remote source
    identity that the retained response proves. This operation never refetches or
    reinterprets source evidence: it copies the verified bytes only after every
    source identity and verification contract matches the new request exactly.
    """

    root = Path(repo_root).expanduser().resolve()
    plan_path = Path(audit_request_plan).expanduser().resolve()
    requests = _audit_requests(load_json_object(plan_path))
    previous_root = Path(source_verification_root).expanduser().resolve()
    previous_manifest_path = previous_root / AUDIT_SOURCE_VERIFICATION_MANIFEST
    expected_manifest_sha256 = single_line(expected_source_verification_sha256).casefold()
    if not is_sha256(expected_manifest_sha256):
        raise RuntimeError("source verification rebind requires an expected prior manifest SHA-256")
    try:
        previous_manifest_bytes = previous_manifest_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"source verification manifest is unreadable: {previous_manifest_path}") from exc
    if sha256_bytes(previous_manifest_bytes) != expected_manifest_sha256:
        raise RuntimeError("source verification rebind prior manifest SHA-256 does not match")
    previous_manifest = _verification_manifest(previous_manifest_bytes)
    previous_records = _verification_records(previous_manifest)
    previous_plan_relative = single_line(previous_manifest.get("audit_request_plan"))
    previous_plan_path = repo_artifact_path(root, previous_plan_relative)
    if previous_plan_path is None or not previous_plan_path.is_file():
        raise RuntimeError("source verification rebind prior audit request plan is missing")
    previous_requests = _audit_requests(load_json_object(previous_plan_path))
    previous_requests_by_case = {single_line(request.get("case_id")): request for request in previous_requests}
    output = Path(output_root).expanduser().resolve()
    if output.exists():
        raise RuntimeError(f"audit verification output already exists: {output}")
    request_ids = {single_line(request.get("case_id")) for request in requests}
    if set(previous_records) != request_ids or set(previous_requests_by_case) != request_ids:
        raise RuntimeError("source verification records must cover exactly the audit request case IDs")

    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path, lock_fd = reserve_output_lock(output)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        records_dir = staging / "records"
        records_dir.mkdir(parents=True)
        records: list[dict[str, Any]] = []
        for request in requests:
            case_id = single_line(request.get("case_id"))
            previous = previous_records[case_id]
            previous_request = previous_requests_by_case[case_id]
            _validate_rebind_source_contract(case_id, request, previous_request, previous)
            response_relative = single_line(previous.get("source_verification_path"))
            response_path = repo_artifact_path(previous_root, response_relative)
            if response_path is None or not response_path.is_file():
                raise RuntimeError(f"source verification response is missing: {case_id}")
            response_body = response_path.read_bytes()
            response_sha256 = sha256_bytes(response_body)
            if response_sha256 != single_line(previous.get("source_verification_sha256")):
                raise RuntimeError(f"source verification response hash does not match: {case_id}")
            _verify_repository_payload(
                _verification_payload(response_body, case_id),
                single_line(request.get("source_id")),
                single_line(request.get("source_uri")),
                case_id,
            )
            new_relative = (Path("records") / f"{case_id}.json").as_posix()
            new_path = records_dir / f"{case_id}.json"
            new_path.write_bytes(response_body)
            sync_file(new_path)
            records.append(
                {
                    "case_id": case_id,
                    "audit_request_sha256": single_line(request.get("audit_request_sha256")),
                    "source_id": single_line(request.get("source_id")),
                    "source_uri": single_line(request.get("source_uri")),
                    "source_verification_method": single_line(request.get("source_verification_method")),
                    "source_verification_uri": single_line(request.get("source_verification_uri")),
                    "source_custody_sha256": source_custody_fingerprint(request),
                    "source_verified_on": single_line(previous.get("source_verified_on")),
                    "source_verification_path": new_relative,
                    "source_verification_sha256": response_sha256,
                    "response_headers": _response_headers(previous.get("response_headers")),
                }
            )
        manifest = {
            "version": AUDIT_SOURCE_VERIFICATION_VERSION,
            "claim_class": "source-verification-only",
            "audit_request_plan": repo_relative(plan_path, root),
            "rebound_from": repo_relative(previous_root / AUDIT_SOURCE_VERIFICATION_MANIFEST, root),
            "rebound_from_sha256": expected_manifest_sha256,
            "record_count": len(records),
            "records": records,
        }
        manifest_path = staging / AUDIT_SOURCE_VERIFICATION_MANIFEST
        manifest_path.write_text(json_text(manifest), encoding="utf-8")
        sync_file(manifest_path)
        sync_directory(staging)
        if output.exists():
            raise RuntimeError(f"audit verification output appeared during rebind: {output}")
        staging.replace(output)
        sync_directory(output.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        release_output_lock(lock_path, lock_fd)
    return manifest


def _audit_requests(plan: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    if single_line(plan.get("version")) != AUDIT_REQUEST_PLAN_VERSION:
        raise RuntimeError("unsupported Greenfield audit request plan")
    if single_line(plan.get("claim_class")) != "audit-requests-only":
        raise RuntimeError("audit verification requires requests-only input")
    rows = plan.get("requests")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)) or not rows:
        raise RuntimeError("audit request plan must define requests")
    requests = tuple(row for row in rows if isinstance(row, Mapping))
    if len(requests) != len(rows):
        raise RuntimeError("audit request plan contains an invalid request")
    case_ids = [single_line(row.get("case_id")) for row in requests]
    if any(safe_artifact_identifier(case_id) is None for case_id in case_ids):
        raise RuntimeError("audit request plan must use safe case IDs")
    if len(set(case_ids)) != len(case_ids):
        raise RuntimeError("audit request plan must use unique case IDs")
    if any(not request_hash_matches(row) for row in requests):
        raise RuntimeError("audit request plan contains an invalid audit_request_sha256")
    return requests


def _verification_records(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if single_line(manifest.get("version")) != AUDIT_SOURCE_VERIFICATION_VERSION:
        raise RuntimeError("unsupported Greenfield source verification manifest")
    if single_line(manifest.get("claim_class")) != "source-verification-only":
        raise RuntimeError("source verification manifest must declare the verification-only claim class")
    rows = manifest.get("records")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)) or not rows:
        raise RuntimeError("source verification manifest must define records")
    records: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError("source verification manifest contains an invalid record")
        case_id = single_line(row.get("case_id"))
        if safe_artifact_identifier(case_id) is None or case_id in records:
            raise RuntimeError("source verification manifest must use unique safe case IDs")
        records[case_id] = row
    record_count = manifest.get("record_count")
    if isinstance(record_count, bool) or not isinstance(record_count, int) or record_count != len(records):
        raise RuntimeError("source verification manifest record_count does not match records")
    return records


def _validate_rebind_source_contract(
    case_id: str,
    request: Mapping[str, Any],
    previous_request: Mapping[str, Any],
    previous: Mapping[str, Any],
) -> None:
    if single_line(previous.get("audit_request_sha256")) != single_line(previous_request.get("audit_request_sha256")):
        raise RuntimeError(f"source verification rebind prior request hash diverges: {case_id}")
    previous_fingerprint = source_custody_fingerprint(previous_request)
    if previous_fingerprint != source_custody_fingerprint(request):
        raise RuntimeError(f"source verification rebind source custody fingerprint diverges: {case_id}")
    recorded_fingerprint = single_line(previous.get("source_custody_sha256"))
    if recorded_fingerprint and recorded_fingerprint != previous_fingerprint:
        raise RuntimeError(f"source verification rebind prior source custody fingerprint diverges: {case_id}")
    for field in (
        "source_id",
        "source_uri",
        "source_verification_method",
        "source_verification_uri",
    ):
        if single_line(previous.get(field)) != single_line(request.get(field)):
            raise RuntimeError(f"source verification rebind diverges on {field}: {case_id}")
    try:
        date.fromisoformat(single_line(previous.get("source_verified_on")))
    except ValueError as exc:
        raise RuntimeError(f"source verification rebind uses an invalid source_verified_on date: {case_id}") from exc
    if not is_sha256(single_line(previous.get("source_verification_sha256")).casefold()):
        raise RuntimeError(f"source verification rebind lacks response hash: {case_id}")
    headers = previous.get("response_headers")
    if not isinstance(headers, Mapping) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in headers.items()):
        raise RuntimeError(f"source verification rebind has invalid response headers: {case_id}")


def _verification_manifest(value: bytes) -> Mapping[str, Any]:
    try:
        payload = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("source verification manifest must be valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError("source verification manifest must be a JSON object")
    return payload


def _verification_payload(value: bytes, case_id: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"source verification response is invalid JSON: {case_id}") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"source verification response must be a JSON object: {case_id}")
    return payload


def _response_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(item) for key, item in sorted(value.items())}


def _verify_repository_payload(
    payload: Mapping[str, Any], source_id: str, source_uri: str, case_id: str
) -> None:
    identifier = source_id.removeprefix("github-repository:")
    if not identifier.isdigit() or int(identifier) <= 0:
        raise RuntimeError(f"audit request has invalid source ID: {case_id}")
    if payload.get("id") != int(identifier):
        raise RuntimeError(f"GitHub verification response does not match source ID: {case_id}")
    if single_line(payload.get("html_url")).rstrip("/") != source_uri.rstrip("/"):
        raise RuntimeError(f"GitHub verification response does not match source URI: {case_id}")
