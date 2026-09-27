#!/usr/bin/env python3
"""Finalize independent Greenfield onboarding review from immutable evidence.

This module is deliberately post-run and provider-free.  It validates a review
package against an exact matrix result and its retained evidence, then writes a
detached sidecar.  It never edits the matrix result or executes Greenfield.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date
import json
import os
from pathlib import Path
from typing import Any

from greenfield_matrix_release_artifacts import (
    is_sha256,
    repo_artifact_path,
    retained_evidence_manifest_issues,
    sha256_file,
)
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard


ONBOARDING_REVIEW_PACKAGE_VERSION = "odylith.greenfield.onboarding-review-package.v1"
ONBOARDING_REVIEW_SIDECAR_VERSION = "odylith.greenfield.onboarding-review-sidecar.v1"
ONBOARDING_REVIEW_LENSES = (
    "product_manager",
    "architect",
    "engineer",
    "domain_expert",
)
_REVIEWABLE_ARTIFACT_KINDS = {
    "generated_artifact",
    "rendered_atlas_asset",
    "retained_navigation",
    "semantic_receipt",
}
_PASSING_GATE_STATUSES = {"passed", "not_requested"}
_REVIEWER_FIELDS = {
    "identity",
    "role",
    "qualification",
    "reviewer_kind",
    "model",
    "model_profile",
    "reasoning_effort",
    "review_context_id",
    "context",
    "method",
    "reviewed_on",
    "rationale",
    "independence",
}
_INDEPENDENCE_FIELDS = {
    "execution_participation",
    "separate_context",
    "evidence_scope",
}
_QUALIFIED_REVIEWER_KINDS = {"host_model", "human"}
_STRONG_REASONING_EFFORTS = {"high", "xhigh", "max", "ultra"}
_ASTRA_REASONING_EFFORTS = {"medium", *_STRONG_REASONING_EFFORTS}
_QUALIFIED_HOST_REVIEW_MODELS = {
    "gpt-6-astra": _ASTRA_REASONING_EFFORTS,
    "gpt-6-sol": _STRONG_REASONING_EFFORTS,
    "gpt-5.6-sol": _STRONG_REASONING_EFFORTS,
}
_INDEPENDENT_REVIEW_ROLE = "independent_release_adjudicator"
_STRONG_REVIEW_QUALIFICATION = "strong_semantic_review"
_STRONG_REVIEW_PROFILE = "independent_strong_review"


def build_onboarding_review_sidecar(
    *,
    base_result_path: Path,
    retained_manifest_path: Path,
    review_package: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a hash-bound final review sidecar without changing its inputs."""

    base_path = Path(base_result_path).expanduser().resolve()
    retained_path = Path(retained_manifest_path).expanduser().resolve()
    base = _read_json_object(base_path, label="base matrix result")
    retained = _read_json_object(retained_path, label="retained evidence manifest")
    base_sha256 = sha256_file(base_path)
    retained_sha256 = sha256_file(retained_path)

    results = base.get("results")
    result_rows = results if isinstance(results, list) else []
    all_case_ids, committed = _base_case_inventory(result_rows)
    committed_case_ids = tuple(committed)

    custody_issues = list(
        retained_evidence_manifest_issues(
            retained_path,
            expected_case_ids=all_case_ids,
            require_passed_cases=True,
        )
    )
    base_retained = _mapping(base.get("retained_evidence"))
    if str(base_retained.get("manifest_sha256") or "") != retained_sha256:
        custody_issues.append("base result retained evidence manifest hash does not match")
    if str(base_retained.get("status") or "") != "passed":
        custody_issues.append("base result retained evidence gate did not pass")

    automated_issues = _automated_gate_issues(base, result_rows)
    review, review_issues, awaiting = _validate_review_package(
        review_package=review_package,
        base_sha256=base_sha256,
        retained_sha256=retained_sha256,
        retained_path=retained_path,
        retained=retained,
        committed=committed,
    )

    blocking_issues = tuple(dict.fromkeys((*custody_issues, *review_issues)))
    awaiting_issues = tuple(dict.fromkeys(awaiting))
    if blocking_issues:
        review_status = "failed"
    elif awaiting_issues:
        review_status = "awaiting_review"
    else:
        review_status = "passed"
    validated_lenses = _validated_lens_statuses(
        review,
        custody_issues=custody_issues,
        review_issues=review_issues,
        awaiting_issues=awaiting_issues,
    )
    finalized_scorecard = _finalized_onboarding_quality_scorecard(
        base=base,
        validated_lenses=validated_lenses,
    )
    scorecard_status = str(finalized_scorecard.get("status") or "")
    if (
        custody_issues
        or automated_issues
        or review_status == "failed"
        or scorecard_status == "failed"
    ):
        status = "failed"
    elif review_status != "passed" or scorecard_status != "passed":
        status = "awaiting_review"
    else:
        status = "passed"

    return {
        "version": ONBOARDING_REVIEW_SIDECAR_VERSION,
        "status": status,
        "base_result": {
            "path": str(base_path),
            "sha256": base_sha256,
        },
        "retained_evidence": {
            "manifest": str(retained_path),
            "manifest_sha256": retained_sha256,
            "status": "passed" if not custody_issues else "failed",
            "issues": list(dict.fromkeys(custody_issues)),
        },
        "automated_release_gates": {
            "status": "passed" if not automated_issues else "failed",
            "issues": list(automated_issues),
        },
        "finalized_onboarding_quality_scorecard": finalized_scorecard,
        "independent_review": {
            "status": review_status,
            "expected_case_ids": list(committed_case_ids),
            "reviewed_case_ids": [row["case_id"] for row in review],
            "reviewer": _normalized_reviewer(review_package),
            "cases": review,
            "issues": list(blocking_issues),
            "awaiting": list(awaiting_issues),
        },
    }


def _finalized_onboarding_quality_scorecard(
    *,
    base: Mapping[str, Any],
    validated_lenses: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    primary = base.get("results")
    primary_results = (
        tuple(_unscored_independent_lenses(row) for row in primary)
        if isinstance(primary, list)
        else ()
    )
    control = _mapping(base.get("lower_capability_control_proof"))
    control_value = control.get("results")
    control_results = tuple(control_value) if isinstance(control_value, list) else ()
    return build_onboarding_quality_scorecard(
        results=(*primary_results, *control_results),
        browser_proof=_mapping(base.get("browser_surface_proof")),
        platform_leakage_proof=_mapping(base.get("platform_domain_leakage_proof")),
        metamorphic_output=_mapping(base.get("metamorphic_output")),
        model_profile_proof=_mapping(base.get("model_profile_proof")),
        unavailable_provider_proof=_mapping(base.get("unavailable_provider_proof")),
        commit_recovery_proof=base.get("commit_recovery_proof"),
        validated_independent_reviews=validated_lenses,
    )


def _unscored_independent_lenses(value: Any) -> Any:
    """Copy a serialized result while refusing execution-time lens assertions."""

    if not isinstance(value, Mapping):
        return value
    result = dict(value)
    quality = dict(_mapping(result.get("quality")))
    scores = dict(_mapping(quality.get("scores")))
    scores.update(
        {
            lens: (
                0
                if scores.get(lens) == 0
                and not isinstance(scores.get(lens), bool)
                else -1
            )
            for lens in ONBOARDING_REVIEW_LENSES
        }
    )
    quality["scores"] = scores
    result["quality"] = quality
    return result


def _validated_lens_statuses(
    cases: Sequence[Mapping[str, Any]],
    *,
    custody_issues: Sequence[str],
    review_issues: Sequence[str],
    awaiting_issues: Sequence[str],
) -> dict[str, dict[str, str]]:
    """Expose verdicts only after evidence bindings validate.

    Explicit failed verdicts and critical findings are adjudication outcomes,
    not custody failures, so the scorecard may consume the failed verdict.  A
    malformed or hash-mismatched review never receives override authority.
    """

    non_adjudication_issues = [
        issue
        for issue in review_issues
        if "failed independent review" not in issue
        and "finding blocks release" not in issue
    ]
    if custody_issues or awaiting_issues or non_adjudication_issues:
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for case in cases:
        case_id = str(case.get("case_id") or "")
        lenses = _mapping(case.get("lenses"))
        if not case_id or set(lenses) != set(ONBOARDING_REVIEW_LENSES):
            return {}
        normalized[case_id] = {
            lens: str(_mapping(lenses.get(lens)).get("status") or "")
            for lens in ONBOARDING_REVIEW_LENSES
        }
    return normalized


def finalize_onboarding_review(
    *,
    base_result_path: Path,
    retained_manifest_path: Path,
    review_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Validate a saved review package and create one immutable sidecar."""

    review_file = Path(review_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    retained_root = Path(retained_manifest_path).expanduser().resolve().parent
    protected = {
        Path(base_result_path).expanduser().resolve(),
        Path(retained_manifest_path).expanduser().resolve(),
        review_file,
    }
    if output in protected:
        raise RuntimeError("review sidecar output must be detached from all inputs")
    try:
        output.relative_to(retained_root)
    except ValueError:
        pass
    else:
        raise RuntimeError("review sidecar output must be outside retained evidence")
    sidecar = validate_independent_review_bundle(
        base_result_path=base_result_path,
        retained_manifest_path=retained_manifest_path,
        review_path=review_file,
    )
    _exclusive_write_json(output, sidecar)
    return sidecar


def validate_independent_review_bundle(
    *,
    base_result_path: Path,
    retained_manifest_path: Path,
    review_path: Path,
) -> dict[str, Any]:
    """Validate a saved review package and return its detached sidecar payload."""

    package = _read_json_object(
        Path(review_path).expanduser().resolve(),
        label="independent review package",
    )
    return build_onboarding_review_sidecar(
        base_result_path=base_result_path,
        retained_manifest_path=retained_manifest_path,
        review_package=package,
    )


def _base_case_inventory(
    result_rows: Sequence[Any],
) -> tuple[tuple[str, ...], dict[str, Mapping[str, Any]]]:
    all_ids: list[str] = []
    committed: dict[str, Mapping[str, Any]] = {}
    for row in result_rows:
        if not isinstance(row, Mapping):
            continue
        case = _mapping(_mapping(row.get("evidence")).get("case"))
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            continue
        all_ids.append(case_id)
        if str(case.get("expectation") or "transaction_committed") != "clarification_required":
            committed[case_id] = row
    return tuple(all_ids), committed


def _validate_review_package(
    *,
    review_package: Mapping[str, Any] | None,
    base_sha256: str,
    retained_sha256: str,
    retained_path: Path,
    retained: Mapping[str, Any],
    committed: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], tuple[str, ...], tuple[str, ...]]:
    issues: list[str] = []
    awaiting: list[str] = []
    normalized: list[dict[str, Any]] = []
    package = review_package if isinstance(review_package, Mapping) else {}
    if not package:
        return [], (), ("independent review package is missing",)
    if "version" not in package:
        awaiting.append("independent review package version is missing")
    elif package.get("version") != ONBOARDING_REVIEW_PACKAGE_VERSION:
        issues.append("independent review package has an unsupported version")
    _validate_hash_binding(
        package,
        key="base_result_sha256",
        expected=base_sha256,
        label="base result",
        issues=issues,
        awaiting=awaiting,
    )
    _validate_hash_binding(
        package,
        key="retained_evidence_manifest_sha256",
        expected=retained_sha256,
        label="retained evidence manifest",
        issues=issues,
        awaiting=awaiting,
    )
    _validate_reviewer(
        package.get("reviewer"),
        forbidden_context_ids={base_sha256, retained_sha256},
        issues=issues,
        awaiting=awaiting,
    )

    manifest_rows = retained.get("case_manifests")
    retained_cases = {
        str(row.get("case_id") or ""): row
        for row in manifest_rows
        if isinstance(row, Mapping) and str(row.get("case_id") or "")
    } if isinstance(manifest_rows, list) else {}
    cases = package.get("cases")
    if cases is None:
        cases = []
    if not isinstance(cases, list):
        issues.append("independent review cases must be a list")
        cases = []
    seen: set[str] = set()
    for index, raw in enumerate(cases):
        if not isinstance(raw, Mapping):
            issues.append(f"independent review case {index + 1} must be an object")
            continue
        case_id = str(raw.get("case_id") or "").strip()
        if not case_id:
            awaiting.append(f"independent review case {index + 1} is missing case_id")
            continue
        if case_id in seen:
            issues.append(f"independent review duplicates case `{case_id}`")
            continue
        seen.add(case_id)
        if case_id not in committed:
            issues.append(f"independent review names unknown or non-committed case `{case_id}`")
            continue
        retained_row = retained_cases.get(case_id)
        if retained_row is None:
            issues.append(f"retained evidence omits committed case `{case_id}`")
            continue
        normalized.append(
            _validate_case_review(
                case_id=case_id,
                raw=raw,
                base_row=committed[case_id],
                retained_root=retained_path.parent,
                retained_row=retained_row,
                issues=issues,
                awaiting=awaiting,
            )
        )
    for case_id in committed:
        if case_id not in seen:
            awaiting.append(f"independent review is missing committed case `{case_id}`")
    return normalized, tuple(dict.fromkeys(issues)), tuple(dict.fromkeys(awaiting))


def _validate_case_review(
    *,
    case_id: str,
    raw: Mapping[str, Any],
    base_row: Mapping[str, Any],
    retained_root: Path,
    retained_row: Mapping[str, Any],
    issues: list[str],
    awaiting: list[str],
) -> dict[str, Any]:
    case = _mapping(_mapping(base_row.get("evidence")).get("case"))
    provenance = _mapping(case.get("provenance"))
    source_expected = {
        "prompt_sha256": str(case.get("prompt_sha256") or ""),
        "confirmed_intent_sha256": str(case.get("confirmed_intent_sha256") or ""),
        "source_artifact_sha256": str(provenance.get("source_artifact_sha256") or ""),
    }
    source = _mapping(raw.get("source"))
    for key, expected in source_expected.items():
        if key not in source:
            awaiting.append(f"{case_id}: review source is missing {key}")
        elif str(source.get(key) or "") != expected:
            issues.append(f"{case_id}: review source {key} does not match the base result")
        if key != "confirmed_intent_sha256" and not is_sha256(expected):
            issues.append(f"{case_id}: base result has invalid {key}")
        if key == "confirmed_intent_sha256" and expected and not is_sha256(expected):
            issues.append(f"{case_id}: base result has invalid {key}")

    case_manifest_relative = str(retained_row.get("path") or "")
    case_manifest = repo_artifact_path(retained_root, case_manifest_relative)
    expected_manifest_sha = str(retained_row.get("sha256") or "")
    supplied_manifest_sha = str(raw.get("case_manifest_sha256") or "")
    if "case_manifest_sha256" not in raw:
        awaiting.append(f"{case_id}: review is missing case manifest hash")
    elif supplied_manifest_sha != expected_manifest_sha:
        issues.append(f"{case_id}: review case manifest hash does not match retained evidence")
    if case_manifest is None or not case_manifest.is_file():
        issues.append(f"{case_id}: retained case manifest is missing")
        case_payload: Mapping[str, Any] = {}
    else:
        if sha256_file(case_manifest) != expected_manifest_sha:
            issues.append(f"{case_id}: retained case manifest bytes changed")
        try:
            case_payload = _read_json_object(
                case_manifest,
                label=f"retained case manifest for {case_id}",
            )
        except RuntimeError:
            issues.append(f"{case_id}: retained case manifest is unreadable")
            case_payload = {}

    base_transaction = str(
        _mapping(_mapping(base_row.get("commit_manifest_summary")).get("product_create_transaction")).get(
            "transaction_hash"
        )
        or ""
    )
    retained_transaction = str(
        _mapping(_mapping(case_payload.get("semantic_bindings")).get("transaction")).get(
            "transaction_hash"
        )
        or ""
    )
    supplied_transaction = str(raw.get("transaction_hash") or "")
    if "transaction_hash" not in raw:
        awaiting.append(f"{case_id}: review is missing transaction hash")
    elif supplied_transaction != base_transaction or supplied_transaction != retained_transaction:
        issues.append(f"{case_id}: review transaction hash does not match retained committed evidence")
    if not is_sha256(base_transaction) or retained_transaction != base_transaction:
        issues.append(f"{case_id}: base and retained transaction identities differ")

    artifacts = case_payload.get("artifacts")
    artifact_index = {
        str(row.get("path") or ""): row
        for row in artifacts
        if isinstance(row, Mapping) and str(row.get("path") or "")
    } if isinstance(artifacts, list) else {}
    reviewed = _mapping(raw.get("reviewed"))
    reviewed_artifacts = _validate_reviewed_pairs(
        case_id=case_id,
        label="artifact",
        rows=reviewed.get("artifacts"),
        artifact_index=artifact_index,
        allowed_kinds=_REVIEWABLE_ARTIFACT_KINDS,
        issues=issues,
        awaiting=awaiting,
    )
    reviewed_screenshots = _validate_reviewed_pairs(
        case_id=case_id,
        label="screenshot",
        rows=reviewed.get("screenshots"),
        artifact_index=artifact_index,
        allowed_kinds={"browser_screenshot"},
        issues=issues,
        awaiting=awaiting,
    )

    case_rationale = str(raw.get("rationale") or "").strip()
    if not case_rationale:
        awaiting.append(f"{case_id}: review rationale is missing")
    lenses = _validate_lenses(
        case_id=case_id,
        rows=raw.get("lenses"),
        issues=issues,
        awaiting=awaiting,
    )
    findings = _validate_findings(
        case_id=case_id,
        rows=raw.get("findings", []),
        issues=issues,
        awaiting=awaiting,
    )
    return {
        "case_id": case_id,
        "source": source_expected,
        "case_manifest_sha256": expected_manifest_sha,
        "transaction_hash": base_transaction,
        "reviewed": {
            "artifacts": reviewed_artifacts,
            "screenshots": reviewed_screenshots,
        },
        "rationale": case_rationale,
        "lenses": lenses,
        "findings": findings,
    }


def _validate_reviewed_pairs(
    *,
    case_id: str,
    label: str,
    rows: Any,
    artifact_index: Mapping[str, Mapping[str, Any]],
    allowed_kinds: set[str],
    issues: list[str],
    awaiting: list[str],
) -> list[dict[str, str]]:
    expected_paths = {
        path
        for path, row in artifact_index.items()
        if str(row.get("kind") or "") in allowed_kinds
    }
    if rows is None:
        awaiting.append(f"{case_id}: reviewed {label} evidence is missing")
        return []
    if not isinstance(rows, list):
        issues.append(f"{case_id}: reviewed {label} evidence must be a list")
        return []
    if not rows:
        awaiting.append(f"{case_id}: reviewed {label} evidence is empty")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            issues.append(f"{case_id}: reviewed {label} {index + 1} must be an object")
            continue
        path = str(raw.get("path") or "")
        digest = str(raw.get("sha256") or "")
        if not path or not digest:
            awaiting.append(f"{case_id}: reviewed {label} {index + 1} is incomplete")
            continue
        if path in seen:
            issues.append(f"{case_id}: reviewed {label} path is duplicated: {path}")
            continue
        seen.add(path)
        retained_row = artifact_index.get(path)
        if retained_row is None or str(retained_row.get("kind") or "") not in allowed_kinds:
            issues.append(f"{case_id}: reviewed {label} path is not retained {label} evidence: {path}")
            continue
        if digest != str(retained_row.get("sha256") or ""):
            issues.append(f"{case_id}: reviewed {label} hash does not match retained evidence: {path}")
            continue
        normalized.append({"path": path, "sha256": digest})
    missing_paths = sorted(expected_paths - seen)
    if missing_paths:
        awaiting.append(
            f"{case_id}: reviewed {label} evidence omits retained paths: "
            + ", ".join(missing_paths)
        )
    return normalized


def _validate_lenses(
    *,
    case_id: str,
    rows: Any,
    issues: list[str],
    awaiting: list[str],
) -> dict[str, dict[str, Any]]:
    if rows is None:
        awaiting.append(f"{case_id}: independent lenses are missing")
        return {}
    if not isinstance(rows, list):
        issues.append(f"{case_id}: independent lenses must be a list")
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            issues.append(f"{case_id}: lens {index + 1} must be an object")
            continue
        lens = str(raw.get("lens") or "").strip()
        if lens not in ONBOARDING_REVIEW_LENSES:
            issues.append(f"{case_id}: independent review names unknown lens `{lens}`")
            continue
        if lens in normalized:
            issues.append(f"{case_id}: independent review duplicates lens `{lens}`")
            continue
        verdict = str(raw.get("verdict") or "").strip()
        rationale = str(raw.get("rationale") or "").strip()
        if verdict not in {"passed", "failed"}:
            if not verdict:
                awaiting.append(f"{case_id}: lens `{lens}` has no verdict")
            else:
                issues.append(f"{case_id}: lens `{lens}` has invalid verdict `{verdict}`")
        if not rationale:
            awaiting.append(f"{case_id}: lens `{lens}` rationale is missing")
        approved = verdict == "passed" and bool(rationale)
        if verdict == "failed":
            issues.append(f"{case_id}: lens `{lens}` failed independent review")
        normalized[lens] = {
            "approved": approved,
            "status": verdict or "awaiting_review",
            "score": 10 if approved else 0,
            "rationale": rationale,
        }
    for lens in ONBOARDING_REVIEW_LENSES:
        if lens not in normalized:
            awaiting.append(f"{case_id}: lens `{lens}` is missing")
    return normalized


def _validate_findings(
    *,
    case_id: str,
    rows: Any,
    issues: list[str],
    awaiting: list[str],
) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        issues.append(f"{case_id}: findings must be a list")
        return []
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            issues.append(f"{case_id}: finding {index + 1} must be an object")
            continue
        severity = str(raw.get("severity") or "").upper().strip()
        status = str(raw.get("status") or "").lower().strip()
        summary = str(raw.get("summary") or "").strip()
        if severity not in {"P0", "P1", "P2", "P3"} or status not in {"open", "closed"}:
            issues.append(f"{case_id}: finding {index + 1} has invalid severity or status")
            continue
        if not summary:
            awaiting.append(f"{case_id}: finding {index + 1} summary is missing")
        if severity in {"P0", "P1"} and status == "open":
            issues.append(f"{case_id}: open {severity} finding blocks release: {summary or 'unspecified'}")
        normalized.append({"severity": severity, "status": status, "summary": summary})
    return normalized


def _validate_reviewer(
    value: Any,
    *,
    forbidden_context_ids: set[str],
    issues: list[str],
    awaiting: list[str],
) -> None:
    if not isinstance(value, Mapping):
        awaiting.append("qualified independent reviewer evidence is missing")
        return
    if set(value) != _REVIEWER_FIELDS:
        issues.append("reviewer evidence must contain the exact qualified independent-review fields")
    for key in (
        "identity",
        "role",
        "qualification",
        "reviewer_kind",
        "model",
        "model_profile",
        "reasoning_effort",
        "review_context_id",
        "context",
        "method",
        "reviewed_on",
        "rationale",
    ):
        token = str(value.get(key) or "").strip()
        if not token:
            awaiting.append(f"reviewer {key} is missing")
        elif key == "reviewed_on":
            try:
                date.fromisoformat(token)
            except ValueError:
                issues.append("reviewer reviewed_on must be an ISO date")
    if value.get("role") != _INDEPENDENT_REVIEW_ROLE:
        issues.append("reviewer role is not an independent release adjudicator")
    if value.get("qualification") != _STRONG_REVIEW_QUALIFICATION:
        issues.append("reviewer does not declare the strong semantic-review qualification")
    reviewer_kind = str(value.get("reviewer_kind") or "").strip()
    if reviewer_kind not in _QUALIFIED_REVIEWER_KINDS:
        issues.append("reviewer kind must be host_model or human")
    model = str(value.get("model") or "").strip()
    model_profile = str(value.get("model_profile") or "").strip()
    reasoning_effort = str(value.get("reasoning_effort") or "").strip()
    if reviewer_kind == "host_model":
        accepted_efforts = _QUALIFIED_HOST_REVIEW_MODELS.get(model)
        if accepted_efforts is None:
            issues.append("host-model reviewer is not a supported strong-review model")
        elif reasoning_effort not in accepted_efforts:
            issues.append("host-model reviewer reasoning effort is below the strong-review floor")
        if model_profile != _STRONG_REVIEW_PROFILE:
            issues.append("host-model reviewer profile is not the independent strong-review profile")
    if reviewer_kind == "human" and (
        model != "not_applicable"
        or model_profile != "not_applicable"
        or reasoning_effort != "not_applicable"
    ):
        issues.append("human reviewer model fields must be not_applicable")
    review_context_id = str(value.get("review_context_id") or "")
    if not is_sha256(review_context_id):
        issues.append("reviewer review_context_id must be a SHA-256 context identity")
    elif review_context_id in forbidden_context_ids:
        issues.append("reviewer context identity must be distinct from execution evidence")
    independence = value.get("independence")
    if not isinstance(independence, Mapping) or set(independence) != _INDEPENDENCE_FIELDS:
        issues.append("reviewer independence evidence is missing or malformed")
        return
    if independence.get("execution_participation") != "none":
        issues.append("reviewer participated in release execution")
    if independence.get("separate_context") is not True:
        issues.append("reviewer did not use a separate review context")
    if independence.get("evidence_scope") != "immutable_retained_evidence_only":
        issues.append("reviewer did not limit adjudication to immutable retained evidence")


def _normalized_reviewer(review_package: Mapping[str, Any] | None) -> dict[str, Any]:
    reviewer = _mapping(review_package.get("reviewer")) if isinstance(review_package, Mapping) else {}
    normalized: dict[str, Any] = {
        key: str(reviewer.get(key) or "").strip()
        for key in _REVIEWER_FIELDS - {"independence"}
    }
    normalized["independence"] = dict(_mapping(reviewer.get("independence")))
    return normalized


def _validate_hash_binding(
    package: Mapping[str, Any],
    *,
    key: str,
    expected: str,
    label: str,
    issues: list[str],
    awaiting: list[str],
) -> None:
    if key not in package:
        awaiting.append(f"independent review is missing {label} hash")
        return
    supplied = str(package.get(key) or "")
    if not is_sha256(supplied) or supplied != expected:
        issues.append(f"independent review {label} hash does not match")


def _automated_gate_issues(base: Mapping[str, Any], results: Sequence[Any]) -> tuple[str, ...]:
    issues: list[str] = []
    if not results:
        issues.append("base result contains no matrix cases")
    for index, row in enumerate(results):
        if not isinstance(row, Mapping):
            issues.append(f"base matrix case {index + 1} is invalid")
            continue
        case_id = str(_mapping(_mapping(row.get("evidence")).get("case")).get("id") or index + 1)
        if str(row.get("status") or "") != "passed" or _mapping(row.get("quality")).get("passed") is not True:
            issues.append(f"base matrix case `{case_id}` did not pass automated quality")
    campaign = _mapping(base.get("campaign"))
    if campaign.get("failed_case_count") != 0:
        issues.append("campaign contains failed cases")
    if campaign.get("completed_case_count") != len(results):
        issues.append("campaign did not complete every selected case")
    if campaign.get("failure_clusters") not in ([], ()):
        issues.append("campaign contains failure clusters")
    statistics = _mapping(campaign.get("outcome_statistics"))
    if str(statistics.get("status") or "") != "passed" or statistics.get("passed") is not True:
        issues.append("campaign outcome statistics did not pass")
    required_statuses = {
        "corpus_provenance": {"passed"},
        "browser_surface_proof": {"passed"},
        "platform_domain_leakage_proof": {"passed"},
        "temp_cleanup_proof": {"passed"},
        "model_profile_proof": {"passed"},
        "lower_capability_control_proof": _PASSING_GATE_STATUSES,
        "unavailable_provider_proof": _PASSING_GATE_STATUSES,
        "semantic_release": _PASSING_GATE_STATUSES,
        "retained_evidence": {"passed"},
    }
    for key, accepted in required_statuses.items():
        if str(_mapping(base.get(key)).get("status") or "") not in accepted:
            issues.append(f"automated release gate `{key}` did not pass")
    if _mapping(base.get("metamorphic_output")).get("passed") is not True:
        issues.append("automated release gate `metamorphic_output` did not pass")
    if "commit_recovery_proof" in base and str(
        _mapping(base.get("commit_recovery_proof")).get("status") or ""
    ) != "passed":
        issues.append("automated release gate `commit_recovery_proof` did not pass")
    return tuple(dict.fromkeys(issues))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} is unreadable") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"{label} must be an object")
    return dict(payload)


def _exclusive_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    try:
        value = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        remaining = memoryview(value)
        while remaining:
            try:
                written = os.write(descriptor, remaining)
            except InterruptedError:
                continue
            if written <= 0:
                raise OSError("review sidecar write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-result", type=Path, required=True)
    parser.add_argument("--retained-manifest", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    sidecar = finalize_onboarding_review(
        base_result_path=args.base_result,
        retained_manifest_path=args.retained_manifest,
        review_path=args.review,
        output_path=args.output,
    )
    print(json.dumps(sidecar, indent=2, sort_keys=True))
    return 0 if sidecar["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ONBOARDING_REVIEW_LENSES",
    "ONBOARDING_REVIEW_PACKAGE_VERSION",
    "ONBOARDING_REVIEW_SIDECAR_VERSION",
    "build_onboarding_review_sidecar",
    "finalize_onboarding_review",
    "validate_independent_review_bundle",
]
