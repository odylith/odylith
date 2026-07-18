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
from greenfield_matrix_release_audit_evidence import case_confirmed_intent_sha256
from greenfield_matrix_release_audit_evidence import audit_request_for_case
from greenfield_matrix_release_audit_evidence import audit_request_sha256
from greenfield_matrix_release_audit_evidence import audit_source_verification_issues
from greenfield_matrix_release_audit_evidence import source_verification_payload_issues
from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS


@dataclass(frozen=True)
class GreenfieldReleaseAudit:
    case_id: str
    prompt_sha256: str
    source_artifact_sha256: str
    source_excerpt_sha256: str
    audit_request_sha256: str
    source_id: str
    source_uri: str
    source_verification_method: str
    source_verification_uri: str
    source_verified_on: str
    source_verification_path: str
    source_verification_sha256: str
    review_context_label: str
    reviewer_kind: str
    review_method: str
    reviewed_on: str
    review_status: str
    review_evidence_path: str
    review_evidence_sha256: str
    confirmed_intent_sha256: str = ""


def evaluate_release_audits(
    *,
    cases_by_id: Mapping[str, Any],
    audits: Sequence[GreenfieldReleaseAudit],
    policy: Any,
    root: Path,
) -> tuple[list[str], dict[str, GreenfieldReleaseAudit]]:
    """Return audit failures and evaluator-approved records keyed by case ID."""

    issues: list[str] = []
    approved: dict[str, GreenfieldReleaseAudit] = {}
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
        if audit.confirmed_intent_sha256 != case_confirmed_intent_sha256(case):
            issues.append(f"release audit `{audit.case_id}` does not match confirmed_intent_sha256")
            continue
        if audit.source_artifact_sha256 != getattr(provenance, "source_artifact_sha256", ""):
            issues.append(f"release audit `{audit.case_id}` does not match source_artifact_sha256")
            continue
        if audit.source_excerpt_sha256 != getattr(provenance, "source_excerpt_sha256", ""):
            issues.append(f"release audit `{audit.case_id}` does not match source_excerpt_sha256")
            continue
        if not is_sha256(audit.audit_request_sha256):
            issues.append(f"release audit `{audit.case_id}` must include audit_request_sha256")
            continue
        verification_issues = audit_source_verification_issues(audit, provenance)
        if verification_issues:
            issues.extend(f"release audit `{audit.case_id}` {issue}" for issue in verification_issues)
            continue
        expected_request = audit_request_for_case(
            case,
            source_verification_method=audit.source_verification_method,
            source_verification_uri=audit.source_verification_uri,
        )
        if audit.audit_request_sha256 != audit_request_sha256(expected_request):
            issues.append(f"release audit `{audit.case_id}` does not bind current case semantics")
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
        if not audit.review_context_label or audit.review_context_label == getattr(provenance, "derivation_author", ""):
            issues.append(
                f"release audit `{audit.case_id}` must name a review context distinct from the derivation author"
            )
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
        approved[audit.case_id] = audit
    _coverage_issues(cases_by_id, approved, policy, issues)
    return issues, approved


def select_release_audit_cases(cases: Sequence[Any], audit_count: int) -> tuple[Any, ...]:
    """Select a deterministic, source-distinct review set with complete coverage."""

    if audit_count <= 0:
        raise ValueError("audit_count must be positive")
    candidates: list[Any] = []
    for case in cases:
        provenance = getattr(case, "provenance", None)
        case_id = str(getattr(case, "case_id", "") or "").strip()
        source_artifact = str(getattr(provenance, "source_artifact_sha256", "") or "").strip()
        source_family = str(getattr(provenance, "source_family", "") or "").strip()
        if not case_id or not source_artifact or not source_family:
            raise ValueError("audit selection requires case ID, source artifact, and source family")
        candidates.append(case)
    if len({case.provenance.source_artifact_sha256 for case in candidates}) < audit_count:
        raise ValueError("audit selection requires at least audit_count distinct source artifacts")

    selected: list[Any] = []
    selected_artifacts: set[str] = set()
    covered_families: set[str] = set()
    covered_stressors: set[str] = set()
    family_counts: dict[str, int] = {}
    stressor_counts: dict[str, int] = {}
    while len(selected) < audit_count:
        remaining = [
            case
            for case in candidates
            if case.provenance.source_artifact_sha256 not in selected_artifacts
        ]
        if not remaining:
            raise ValueError("audit selection exhausted distinct source artifacts")

        def key(case: Any) -> tuple[int, int, int, int, str]:
            provenance = case.provenance
            family = provenance.source_family
            stressors = _case_stressors(case)
            return (
                0 if family not in covered_families else 1,
                -len(set(stressors) - covered_stressors),
                family_counts.get(family, 0),
                sum(stressor_counts.get(stressor, 0) for stressor in stressors),
                case.case_id,
            )

        chosen = min(remaining, key=key)
        selected.append(chosen)
        provenance = chosen.provenance
        selected_artifacts.add(provenance.source_artifact_sha256)
        covered_families.add(provenance.source_family)
        family_counts[provenance.source_family] = family_counts.get(provenance.source_family, 0) + 1
        for stressor in _case_stressors(chosen):
            covered_stressors.add(stressor)
            stressor_counts[stressor] = stressor_counts.get(stressor, 0) + 1

    missing_families = {case.provenance.source_family for case in candidates} - covered_families
    missing_stressors = set(DEFAULT_HIGH_VARIANCE_STRESSORS) - covered_stressors
    if missing_families or missing_stressors:
        missing = sorted(missing_families | missing_stressors)
        raise ValueError("audit selection does not cover: " + ", ".join(missing))
    return tuple(selected)


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
    approved: Mapping[str, GreenfieldReleaseAudit],
    policy: Any,
    issues: list[str],
) -> None:
    required_audits = policy.minimum_audit_count(len(cases_by_id))
    if len(approved) < required_audits:
        issues.append(
            "release audit requires at least "
            f"{required_audits} approved hash-bound automated reviews; received {len(approved)}"
        )
    review_context_counts: dict[str, int] = {}
    for audit in approved.values():
        label = audit.review_context_label
        review_context_counts[label] = review_context_counts.get(label, 0) + 1
    minimum_reviewer_count = int(getattr(policy, "minimum_distinct_review_context_labels", 1))
    if len(review_context_counts) < minimum_reviewer_count:
        issues.append(
            "release audit requires at least "
            f"{minimum_reviewer_count} distinct declared review context labels; received {len(review_context_counts)}"
        )
    maximum_reviews_per_reviewer = int(
        getattr(policy, "maximum_audits_per_review_context_label", required_audits)
    )
    overloaded_review_contexts = sorted(
        label for label, count in review_context_counts.items() if count > maximum_reviews_per_reviewer
    )
    if overloaded_review_contexts:
        issues.append(
            "release audit caps approved reviews per declared review context label at "
            f"{maximum_reviews_per_reviewer}: " + ", ".join(overloaded_review_contexts)
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
