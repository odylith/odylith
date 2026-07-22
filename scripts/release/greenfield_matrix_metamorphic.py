"""Evaluate output-level invariants for declared Greenfield metamorphic case groups."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_preconfirm_matrix_cases import CLARIFICATION_REQUIRED_EXPECTATION
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_preconfirm_matrix_cases import case_expectation


METAMORPHIC_OUTPUT_VERSION = "odylith.greenfield.matrix.metamorphic-output.v1"


def evaluate_metamorphic_outputs(
    *,
    cases: Sequence[GreenfieldMatrixCase],
    results: Sequence[GreenfieldMatrixResult],
) -> dict[str, Any]:
    """Require equivalent-source variants to preserve their declared completion contract."""

    groups: dict[str, list[GreenfieldMatrixCase]] = {}
    for case in cases:
        group = str(getattr(case, "metamorphic_group", "") or "").strip()
        if group:
            groups.setdefault(group, []).append(case)
    if not groups:
        return _evaluation(status="not-required")
    results_by_case_id = {
        _result_case_id(result): result
        for result in results
        if _result_case_id(result)
    }
    issues: list[str] = []
    pending_groups: list[str] = []
    skipped_groups: list[str] = []
    complete_groups = 0
    for group, members in sorted(groups.items()):
        transforms = {
            str(getattr(case, "metamorphic_transform", "") or "").strip()
            for case in members
            if str(getattr(case, "metamorphic_transform", "") or "").strip()
        }
        if len(members) < 2:
            skipped_groups.append(group)
            continue
        if len(transforms) < 2:
            issues.append(f"metamorphic group {group} does not define two distinct transforms")
            continue
        missing = [_case_id(case) for case in members if _case_id(case) not in results_by_case_id]
        if missing:
            pending_groups.append(group)
            continue
        complete_groups += 1
        issues.extend(_group_issues(group=group, members=members, results_by_case_id=results_by_case_id))
    status = "failed" if issues else "pending" if pending_groups else "passed"
    return _evaluation(
        status=status,
        issues=issues,
        pending_groups=pending_groups,
        skipped_groups=skipped_groups,
        complete_group_count=complete_groups,
        group_count=len(groups),
    )


def _group_issues(
    *,
    group: str,
    members: Sequence[GreenfieldMatrixCase],
    results_by_case_id: Mapping[str, GreenfieldMatrixResult],
) -> list[str]:
    issues: list[str] = []
    expected_source_ids = {case.provenance.source_id for case in members}
    expected_artifact_hashes = {case.provenance.source_artifact_sha256 for case in members}
    if len(expected_source_ids) != 1 or "" in expected_source_ids:
        issues.append(f"metamorphic group {group} does not have one source identity")
    if len(expected_artifact_hashes) != 1 or "" in expected_artifact_hashes:
        issues.append(f"metamorphic group {group} does not have one source artifact hash")
    for case in members:
        case_id = _case_id(case)
        result = results_by_case_id[case_id]
        if result.status != "passed" or not result.quality.passed:
            issues.append(f"metamorphic group {group} case {case_id} did not pass")
            continue
        evidence = _mapping(result.evidence)
        provenance = _mapping(_mapping(evidence.get("case")).get("provenance"))
        if provenance.get("source_id") not in expected_source_ids:
            issues.append(f"metamorphic group {group} case {case_id} lost its source identity")
        if provenance.get("source_artifact_sha256") not in expected_artifact_hashes:
            issues.append(f"metamorphic group {group} case {case_id} lost its source artifact identity")
        issues.extend(
            _completion_invariant_issues(
                group=group,
                case=case,
                case_id=case_id,
                result=result,
                evidence=evidence,
            )
        )
    return issues


def _completion_invariant_issues(
    *,
    group: str,
    case: GreenfieldMatrixCase,
    case_id: str,
    result: GreenfieldMatrixResult,
    evidence: Mapping[str, Any],
) -> list[str]:
    if case_expectation(case) == CLARIFICATION_REQUIRED_EXPECTATION:
        return _clarification_invariant_issues(
            group=group,
            case_id=case_id,
            result=result,
            evidence=evidence,
        )
    return _commit_invariant_issues(group=group, case_id=case_id, result=result, evidence=evidence)


def _commit_invariant_issues(
    *,
    group: str,
    case_id: str,
    result: GreenfieldMatrixResult,
    evidence: Mapping[str, Any],
) -> list[str]:
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    summary = _mapping(result.commit_manifest_summary)
    write_transaction = _mapping(summary.get("write_transaction"))
    manifest_transaction = _mapping(summary.get("product_create_transaction"))
    expected_hash = str(receipt.get("transaction_hash") or "").strip()
    issues: list[str] = []
    if receipt.get("status") != "compiled" or not _is_sha256(expected_hash):
        issues.append(f"metamorphic group {group} case {case_id} lacks a sealed dry-run receipt")
        return issues
    if write_transaction.get("commit_only") is not True or write_transaction.get("prewrite_clean_before_commit") is not True:
        issues.append(f"metamorphic group {group} case {case_id} did not prove commit-only write custody")
    if str(write_transaction.get("product_create_transaction_hash") or "").strip() != expected_hash:
        issues.append(f"metamorphic group {group} case {case_id} changed the sealed transaction hash at commit")
    if str(manifest_transaction.get("transaction_hash") or "").strip() != expected_hash:
        issues.append(f"metamorphic group {group} case {case_id} read back a different transaction hash")
    return issues


def _clarification_invariant_issues(
    *,
    group: str,
    case_id: str,
    result: GreenfieldMatrixResult,
    evidence: Mapping[str, Any],
) -> list[str]:
    case = _mapping(evidence.get("case"))
    clarification = _mapping(evidence.get("clarification"))
    no_write = _mapping(evidence.get("no_write"))
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    required_fields = clarification.get("required_fields")
    before_record_count = no_write.get("before_record_count")
    after_record_count = no_write.get("after_record_count")
    issues: list[str] = []
    if str(case.get("expectation") or "").strip().casefold() != CLARIFICATION_REQUIRED_EXPECTATION:
        issues.append(f"metamorphic group {group} case {case_id} lost its clarification expectation")
    if str(clarification.get("mode") or "").strip().casefold() != CLARIFICATION_REQUIRED_EXPECTATION:
        issues.append(f"metamorphic group {group} case {case_id} did not return the required clarification mode")
    if not _plain_language_question(clarification.get("question")):
        issues.append(f"metamorphic group {group} case {case_id} did not ask exactly one plain-language clarification question")
    if required_fields != ["first_path"]:
        issues.append(f"metamorphic group {group} case {case_id} did not require only first_path")
    if clarification.get("returncode") != 0:
        issues.append(f"metamorphic group {group} case {case_id} did not complete clarification cleanly")
    if no_write.get("changed_records") != []:
        issues.append(f"metamorphic group {group} case {case_id} changed governed records before clarification")
    if not _matching_record_counts(before_record_count, after_record_count):
        issues.append(f"metamorphic group {group} case {case_id} did not prove unchanged governed record counts")
    if no_write.get("staged_transaction_present") is not False:
        issues.append(f"metamorphic group {group} case {case_id} staged a transaction before clarification")
    if receipt:
        issues.append(f"metamorphic group {group} case {case_id} created a dry-run receipt before clarification")
    if _mapping(result.commit_manifest_summary):
        issues.append(f"metamorphic group {group} case {case_id} produced a commit manifest before clarification")
    return issues


def _evaluation(
    *,
    status: str,
    issues: Sequence[str] = (),
    pending_groups: Sequence[str] = (),
    skipped_groups: Sequence[str] = (),
    complete_group_count: int = 0,
    group_count: int = 0,
) -> dict[str, Any]:
    return {
        "version": METAMORPHIC_OUTPUT_VERSION,
        "status": status,
        "passed": status in {"passed", "not-required"},
        "group_count": int(group_count),
        "complete_group_count": int(complete_group_count),
        "pending_groups": list(pending_groups),
        "skipped_groups": list(skipped_groups),
        "issues": list(dict.fromkeys(str(issue) for issue in issues if str(issue).strip())),
    }


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    evidence = _mapping(result.evidence)
    case = _mapping(evidence.get("case"))
    return str(case.get("id") or "").strip()


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _plain_language_question(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    question = value.strip()
    words = tuple(token for token in question.replace("?", " ").split() if any(character.isalpha() for character in token))
    return "\n" not in question and len(words) >= 3 and question.endswith("?") and question.count("?") == 1


def _matching_record_counts(before: Any, after: Any) -> bool:
    return (
        isinstance(before, int)
        and not isinstance(before, bool)
        and isinstance(after, int)
        and not isinstance(after, bool)
        and before == after
    )


__all__ = ["METAMORPHIC_OUTPUT_VERSION", "evaluate_metamorphic_outputs"]
