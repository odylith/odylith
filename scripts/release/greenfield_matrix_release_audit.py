"""Release-audit adjudication for source-provenanced Greenfield case corpora."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from greenfield_matrix_release_artifacts import is_iso_date
from greenfield_matrix_release_artifacts import is_sha256
from greenfield_matrix_release_artifacts import repo_artifact_path
from greenfield_matrix_release_artifacts import sha256_file
from greenfield_matrix_release_artifacts import sha256_text
from greenfield_matrix_release_audit_evidence import AUTOMATED_ADVERSARIAL_REVIEWER_KIND
from greenfield_matrix_release_audit_evidence import audit_evidence_issues
from greenfield_matrix_release_audit_evidence import audit_source_verification_issues
from greenfield_matrix_release_audit_evidence import source_verification_payload_issues
from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS


@dataclass(frozen=True)
class GreenfieldReleaseAudit:
    case_id: str
    prompt_sha256: str
    source_artifact_sha256: str
    source_excerpt_sha256: str
    source_id: str
    source_uri: str
    source_verification_method: str
    source_verification_uri: str
    source_verified_on: str
    source_verification_path: str
    source_verification_sha256: str
    reviewer_id: str
    reviewer_kind: str
    review_method: str
    reviewed_on: str
    review_status: str
    independent: bool
    review_evidence_path: str
    review_evidence_sha256: str


def evaluate_release_audits(
    *,
    cases_by_id: Mapping[str, Any],
    audits: Sequence[GreenfieldReleaseAudit],
    policy: Any,
    root: Path,
) -> tuple[list[str], set[str]]:
    """Return audit failures and the case IDs that satisfy the independent-review contract."""

    issues: list[str] = []
    approved: set[str] = set()
    seen: set[str] = set()
    verification_hashes: dict[Path, str] = {}
    review_hashes: dict[Path, str] = {}
    for audit in audits:
        if audit.case_id in seen:
            issues.append(f"release audit duplicates case_id `{audit.case_id}`")
            continue
        seen.add(audit.case_id)
        case = cases_by_id.get(audit.case_id)
        if case is None:
            issues.append(f"release audit references unknown case_id `{audit.case_id}`")
            continue
        provenance = getattr(case, "provenance", None)
        if provenance is None:
            issues.append(f"release audit `{audit.case_id}` has no source provenance")
            continue
        expected_prompt_hash = sha256_text(str(getattr(case, "prompt", "") or ""))
        if audit.prompt_sha256 != expected_prompt_hash:
            issues.append(f"release audit `{audit.case_id}` does not match prompt_sha256")
            continue
        if audit.source_artifact_sha256 != getattr(provenance, "source_artifact_sha256", ""):
            issues.append(f"release audit `{audit.case_id}` does not match source_artifact_sha256")
            continue
        if audit.source_excerpt_sha256 != getattr(provenance, "source_excerpt_sha256", ""):
            issues.append(f"release audit `{audit.case_id}` does not match source_excerpt_sha256")
            continue
        verification_issues = audit_source_verification_issues(audit, provenance)
        if verification_issues:
            issues.extend(f"release audit `{audit.case_id}` {issue}" for issue in verification_issues)
            continue
        verification_text = _verified_file_text(
            audit=audit,
            field="source_verification",
            root=root,
            hashes=verification_hashes,
            issues=issues,
        )
        if verification_text is None:
            continue
        payload_issues = source_verification_payload_issues(audit, verification_text)
        if payload_issues:
            issues.extend(f"release audit `{audit.case_id}` {issue}" for issue in payload_issues)
            continue
        if audit.review_status != "approved":
            issues.append(f"release audit `{audit.case_id}` is not approved")
            continue
        if audit.reviewer_kind != AUTOMATED_ADVERSARIAL_REVIEWER_KIND:
            issues.append(
                f"release audit `{audit.case_id}` must declare reviewer_kind "
                f"`{AUTOMATED_ADVERSARIAL_REVIEWER_KIND}`"
            )
            continue
        if not audit.review_method:
            issues.append(f"release audit `{audit.case_id}` must name an automated review_method")
            continue
        if audit.review_method == getattr(provenance, "derivation_method", ""):
            issues.append(
                f"release audit `{audit.case_id}` must use a review_method distinct from derivation_method"
            )
            continue
        if type(audit.independent) is not bool:
            issues.append(f"release audit `{audit.case_id}` must define independent as a boolean")
            continue
        if not audit.independent:
            issues.append(f"release audit `{audit.case_id}` is not independent")
            continue
        if not audit.reviewer_id or audit.reviewer_id == getattr(provenance, "derivation_author", ""):
            issues.append(f"release audit `{audit.case_id}` must name an independent reviewer")
            continue
        if not is_iso_date(audit.reviewed_on):
            issues.append(f"release audit `{audit.case_id}` must use an ISO reviewed_on date")
            continue
        evidence_text = _verified_file_text(
            audit=audit,
            field="review_evidence",
            root=root,
            hashes=review_hashes,
            issues=issues,
        )
        if evidence_text is None:
            continue
        evidence_issues = audit_evidence_issues(
            audit,
            evidence_text,
            str(getattr(provenance, "source_family", "") or ""),
        )
        if evidence_issues:
            issues.extend(f"release audit `{audit.case_id}` {issue}" for issue in evidence_issues)
            continue
        approved.add(audit.case_id)
    _coverage_issues(cases_by_id, approved, policy, issues)
    return issues, approved


def _verified_file_text(
    *,
    audit: GreenfieldReleaseAudit,
    field: str,
    root: Path,
    hashes: dict[Path, str],
    issues: list[str],
) -> str | None:
    path_value = str(getattr(audit, f"{field}_path", "") or "")
    expected_hash = str(getattr(audit, f"{field}_sha256", "") or "")
    if not is_sha256(expected_hash):
        issues.append(f"release audit `{audit.case_id}` must include {field}_sha256")
        return None
    artifact_path = repo_artifact_path(root, path_value)
    if artifact_path is None:
        issues.append(f"release audit `{audit.case_id}` must use a repository-relative {field}_path")
        return None
    if not artifact_path.is_file():
        issues.append(f"release audit `{audit.case_id}` {field}_path does not exist: {path_value}")
        return None
    actual_hash = hashes.setdefault(artifact_path, sha256_file(artifact_path))
    if actual_hash != expected_hash:
        issues.append(f"release audit `{audit.case_id}` {field}_sha256 does not match {field}_path")
        return None
    try:
        return artifact_path.read_text(encoding="utf-8")
    except OSError as exc:
        issues.append(f"release audit `{audit.case_id}` {field} cannot be read: {exc}")
        return None


def _coverage_issues(
    cases_by_id: Mapping[str, Any],
    approved: set[str],
    policy: Any,
    issues: list[str],
) -> None:
    required_audits = policy.minimum_audit_count(len(cases_by_id))
    if len(approved) < required_audits:
        issues.append(
            "release proof requires at least "
            f"{required_audits} approved independent automated audits; received {len(approved)}"
        )
    audited_cases = [cases_by_id[case_id] for case_id in approved if case_id in cases_by_id]
    audited_families = {
        str(getattr(getattr(case, "provenance", None), "source_family", "") or "")
        for case in audited_cases
    }
    all_families = {
        str(getattr(getattr(case, "provenance", None), "source_family", "") or "")
        for case in cases_by_id.values()
    }
    missing_families = sorted(family for family in all_families if family and family not in audited_families)
    if missing_families:
        issues.append("release audit is not stratified across source families: " + ", ".join(missing_families))
    audited_stressors = {stressor for case in audited_cases for stressor in _case_stressors(case)}
    missing_stressors = [stressor for stressor in DEFAULT_HIGH_VARIANCE_STRESSORS if stressor not in audited_stressors]
    if missing_stressors:
        issues.append("release audit is not stratified across stressors: " + ", ".join(missing_stressors))


def _case_stressors(case: Any) -> tuple[str, ...]:
    stressors = getattr(case, "stressors", ())
    if not isinstance(stressors, Sequence) or isinstance(stressors, (str, bytes, bytearray)):
        return ()
    return tuple(str(stressor).strip() for stressor in stressors if str(stressor).strip())
