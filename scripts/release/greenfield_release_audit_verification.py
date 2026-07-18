"""Retain and validate remote source records for Greenfield audit requests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from greenfield_matrix_release_audit_evidence import github_repository_verification_uri
from greenfield_matrix_release_audit_evidence import request_hash_matches
from greenfield_matrix_release_artifacts import safe_artifact_identifier
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


AUDIT_REQUEST_PLAN_VERSION = "odylith.greenfield.matrix.audit-request-plan.v2"
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
