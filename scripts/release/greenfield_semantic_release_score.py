"""Structural Greenfield release scoring over sealed model-authored custody."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    atomic_fact_ledger_hash,
)
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    require_atomic_fact_ledger,
)

from greenfield_matrix_statistics import RELEASE_SLICE_DIMENSIONS
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_statistics import release_slice_coverage_issues
from greenfield_matrix_statistics import release_slice_evidence
from greenfield_matrix_statistics import release_slice_minimum_sample_contract
from greenfield_matrix_statistics import release_slice_minimum_sample_contract_issues
from greenfield_matrix_statistics import release_statistical_confidence_contract_issues
from greenfield_matrix_statistics import threshold_check
from greenfield_matrix_statistics import wilson_interval
from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_case_file import load_case_file
from greenfield_relation_fidelity import RELATION_FAMILIES


from greenfield_semantic_case_score import (
    score_native_commit, mapping_rows, mapping_value, semantic_finding, empty_relation_counts, is_sequence,
    load_source_predicate_evidence, score_source_predicates, PUBLIC_SOURCE_MODE,
    PUBLIC_EDIT_SOURCE_MODE, PUBLIC_COMPOSITION_MODE,
)

SEMANTIC_RELEASE_SCORE_VERSION = "odylith.greenfield.semantic-release-score.v7"


def evaluate_semantic_release(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
    release_required_slices: Mapping[str, Sequence[str]] | None = None,
    source_predicate_evidence: Mapping[str, Any] | None = None,
    retained_evidence_manifest: Path | None = None,
    _include_model_profiles: bool = True,
    _allow_not_applicable_metrics: bool = False,
) -> dict[str, Any]:
    """Apply frozen release floors to native identities or audited source coverage.

    Source mode requires a separately retained independent audit of exact actual
    evidence.  It cannot authorize consumer transactions or protected access.
    """

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    source_bindings: dict[str, Mapping[str, Any]] = {}
    source_manifests: dict[str, Path] = {}
    evaluation_mode = source_predicate_evidence.get("mode") if source_predicate_evidence else SEMANTIC_RELEASE_SCORE_VERSION
    if source_predicate_evidence is not None:
        source_annotations, source_bindings, source_manifests, source_issues = _source_release_inputs(
            configuration=source_predicate_evidence, cases=cases, results=results)
        selected = {case_id: source_annotations[case_id] for case_id in case_ids if case_id in source_annotations}
        if annotations and dict(annotations) != selected:
            source_issues = (*source_issues, "public mode annotations differ from unchanged frozen source predicates")
        if source_issues:
            report = _incomplete_semantic_release_report(selected_case_count=len(cases),
                missing_case_ids=[], duplicate_case_ids=duplicate_case_ids,
                duplicate_result_ids=duplicate_result_ids, annotations_match=False, floors=floors,
                release_required_slices=release_required_slices)
            report.update(version=evaluation_mode, evaluation_mode=evaluation_mode)
            report["issues"] = list(source_issues)
            return report
        annotations = selected
        _allow_not_applicable_metrics = False
    results_by_id = {
        case_id: result
        for case_id, result in zip(result_ids, results, strict=False)
        if case_id
    }
    missing_case_ids = list(
        dict.fromkeys(
            case_id
            for case_id in case_ids
            if case_id not in annotations or case_id not in results_by_id
        )
    )
    if (
        missing_case_ids
        or set(annotations) != set(case_ids)
        or duplicate_case_ids
        or duplicate_result_ids
    ):
        return _incomplete_semantic_release_report(
            selected_case_count=len(cases),
            missing_case_ids=missing_case_ids,
            duplicate_case_ids=duplicate_case_ids,
            duplicate_result_ids=duplicate_result_ids,
            annotations_match=set(annotations) == set(case_ids),
            floors=floors,
            release_required_slices=release_required_slices,
        )
    metric_counts: dict[str, list[int]] = {
        "atomic_semantic_fidelity": [0, 0],
        "relation_fidelity": [0, 0],
        "clarification_identity": [0, 0],
        "unnecessary_question_rate": [0, 0],
    }
    case_outcomes: list[dict[str, Any]] = []
    p0_findings: list[dict[str, str]] = []
    p1_findings: list[dict[str, str]] = []
    for case in cases:
        case_id = _case_id(case)
        annotation = annotations.get(case_id)
        result = results_by_id.get(case_id)
        if annotation is None or result is None:  # pragma: no cover - completeness preflight
            raise AssertionError("semantic release completeness changed during scoring")
        outcome = _score_case(
            case=case,
            case_id=case_id,
            annotation=annotation,
            result=result,
            metric_counts=metric_counts,
            source_binding=source_bindings.get(case_id),
            retained_evidence_manifest=source_manifests.get(case_id, retained_evidence_manifest),
        )
        case_outcomes.append(outcome)
        p0_findings.extend(outcome["p0_findings"])
        p1_findings.extend(outcome["p1_findings"])

    metrics = {name: _metric(name, *counts) for name, counts in metric_counts.items()}
    relation_metric = metrics["relation_fidelity"]
    relation_metric["sample_count"] = relation_metric["denominator"]
    relation_metric["correct_count"] = relation_metric["numerator"]
    relation_metric["incorrect_count"] = relation_metric["denominator"] - relation_metric["numerator"]
    relation_metric["point_estimate"] = relation_metric["rate"]
    if not relation_metric["denominator"]:
        relation_metric["evidence"] = "no commit relation samples were selected"
    passed_count = sum(1 for outcome in case_outcomes if outcome["passed"])
    sample_count = len(case_outcomes)
    overall = _metric("overall_case_success", passed_count, sample_count)
    slices = _slice_rows(cases=cases, outcomes=case_outcomes)
    worst_slice = min(
        slices,
        key=lambda row: (
            float(row["point_estimate"]),
            float(row["confidence_interval_95"]["lower"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    least_confident_slice = min(
        slices,
        key=lambda row: (
            float(row["confidence_interval_95"]["lower"]),
            float(row["point_estimate"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    relation_slices = _relation_slice_rows(cases=cases, outcomes=case_outcomes)
    worst_relation_slice = min(
        relation_slices,
        key=lambda row: (
            float(row["point_estimate"]),
            float(row["confidence_interval_95"]["lower"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    least_confident_relation_slice = min(
        relation_slices,
        key=lambda row: (
            float(row["confidence_interval_95"]["lower"]),
            float(row["point_estimate"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default={},
    )
    relation_family_metrics = _relation_family_metrics(case_outcomes)
    acceptance_checks = _acceptance_checks(
        floors=floors,
        metrics=metrics,
        overall=overall,
        worst_slice=worst_slice,
        worst_relation_slice=worst_relation_slice,
        p0_findings=p0_findings,
        p1_findings=p1_findings,
        allow_not_applicable_metrics=_allow_not_applicable_metrics,
    )
    confidence_contract = mapping_value(floors.get("statistical_confidence"))
    confidence_contract_issues = release_statistical_confidence_contract_issues(
        confidence_contract,
        minimum_samples=mapping_value(floors.get("release_slice_minimum_samples")),
    )
    confidence_checks = _confidence_checks(
        confidence=confidence_contract,
        metrics=metrics,
        relation_family_metrics=relation_family_metrics,
        overall=overall,
        least_confident_slice=least_confident_slice,
        least_confident_relation_slice=least_confident_relation_slice,
        allow_not_applicable_metrics=_allow_not_applicable_metrics,
    )
    issues = [
        str(check["issue"])
        for check in (*acceptance_checks, *confidence_checks)
        if check["status"] in {"failed", "unproven"}
        and str(check.get("issue") or "").strip()
    ]
    issues.extend(confidence_contract_issues)
    if missing_case_ids:
        issues.append("semantic release results are incomplete")
    if set(annotations) != set(case_ids):
        issues.append("semantic release annotations do not exactly match selected cases")
    if duplicate_case_ids:
        issues.append("semantic release cases contain duplicate IDs")
    if duplicate_result_ids:
        issues.append("semantic release results contain duplicate IDs")
    release_evidence_issues = [
        f"case `{outcome['case_id']}` {issue}"
        for outcome in case_outcomes
        for issue in outcome["release_evidence_issues"]
    ]
    issues.extend(release_evidence_issues)
    relation_evidence_issues = [
        f"case `{outcome['case_id']}` {issue}"
        for outcome in case_outcomes
        for issue in outcome["relation_evidence_issues"]
    ]
    issues.extend(relation_evidence_issues)
    required_slices = _required_release_slices(release_required_slices)
    release_minimum_samples = release_slice_minimum_sample_contract()
    if release_required_slices is not None and (
        set(release_required_slices) != set(RELEASE_SLICE_DIMENSIONS)
        or required_slices != release_slice_contract()
    ):
        issues.append("semantic release slice contract does not match the published operating envelope")
    minimum_sample_contract_issues = (
        release_slice_minimum_sample_contract_issues(
            floors.get("release_slice_minimum_samples")
        )
        if release_required_slices is not None
        else []
    )
    issues.extend(minimum_sample_contract_issues)
    coverage_issues = (
        release_slice_coverage_issues(
            slices=slices,
            required=required_slices,
            minimum_samples=release_minimum_samples,
        )
        if release_required_slices is not None
        else []
    )
    issues.extend(coverage_issues)
    model_profiles = (
        _model_profile_reports(
            cases=cases,
            annotations=annotations,
            results=results,
            floors=floors,
            case_outcomes=case_outcomes,
            source_predicate_evidence=source_predicate_evidence,
            retained_evidence_manifest=retained_evidence_manifest,
        )
        if _include_model_profiles
        else []
    )
    for profile in model_profiles:
        if profile["status"] != "passed":
            issues.append(f"model profile `{profile['profile']}` failed the semantic release floors")
    normalized_semantic_digests = {
        str(row["case_id"]): str(row["normalized_semantic_digest"])
        for row in case_outcomes if str(row.get("normalized_semantic_digest") or "")
    }
    report = {
        "version": evaluation_mode,
        "status": "passed" if not issues else "failed",
        "scoring_status": "scored",
        "passed": not issues,
        "sample_count": sample_count,
        "selected_case_count": len(cases),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "metrics": metrics,
        "relation_sample_count": int(relation_metric["sample_count"]),
        "relation_fidelity_by_family": relation_family_metrics,
        "relation_slices": relation_slices,
        "worst_relation_slice": worst_relation_slice,
        "least_confident_relation_slice": least_confident_relation_slice,
        "overall_case_success": overall,
        "worst_slice": worst_slice,
        "least_confident_slice": least_confident_slice,
        "slices": slices,
        "p0_count": len(p0_findings),
        "p0_findings": p0_findings,
        "p1_count": len(p1_findings),
        "p1_findings": p1_findings,
        "acceptance_checks": acceptance_checks,
        "confidence_contract": confidence_contract,
        "confidence_contract_issues": confidence_contract_issues,
        "confidence_checks": confidence_checks,
        "issues": list(dict.fromkeys(issues)),
        "release_required_slices": required_slices,
        "release_minimum_samples": (
            release_minimum_samples if release_required_slices is not None else {}
        ),
        "release_minimum_sample_contract_issues": minimum_sample_contract_issues,
        "release_evidence_issues": release_evidence_issues,
        "relation_evidence_issues": relation_evidence_issues,
        "normalized_semantic_digests": normalized_semantic_digests,
        "release_coverage_issues": coverage_issues,
        "model_profiles": model_profiles,
        "case_outcomes": [
            {
                "case_id": row["case_id"],
                "passed": row["passed"],
                "expected_outcome": row["expected_outcome"],
                "observed_outcome": row["observed_outcome"],
                "failed_dimensions": row["failed_dimensions"],
                "release_slices": row["release_slices"],
                "relation_counts": row["relation_counts"],
                "normalized_semantic_digest": row["normalized_semantic_digest"],
            }
            for row in case_outcomes
        ],
    }
    if source_predicate_evidence is not None:
        report["evaluation_mode"] = evaluation_mode
        report["scoring_units"] = {
            "atomic_semantic_fidelity": "one unique frozen scored commit source predicate ID",
            "relation_fidelity": "one unique frozen source relation identity",
            "clarification_identity": "exact frozen field/question/outcome per clarification case",
            "reverse_semantic_support": "complete independently reviewed observed universe; hard failure guard",
        }
        report["source_predicate_evidence"] = dict(source_predicate_evidence)
    return report


def _source_release_inputs(
    *, configuration: Mapping[str, Any], cases: Sequence[Any], results: Sequence[Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], tuple[str, ...]]:
    """Authenticate both unchanged families even when a nested profile selects a subset."""
    if configuration.get("mode") != PUBLIC_COMPOSITION_MODE:
        annotations, bindings, issues = load_source_predicate_evidence(
            configuration=configuration, cases=cases, results=results)
        return annotations, bindings, {}, issues
    annotations, bindings, manifests, issues = {}, {}, {}, []
    if set(configuration) != {"mode", "primary", "high"}:
        return {}, {}, {}, ("composed source mode requires exact primary/high evidence",)
    try:
        all_ids: set[str] = set()
        for name, mode, count in (("primary", PUBLIC_SOURCE_MODE, 40), ("high", PUBLIC_EDIT_SOURCE_MODE, 4)):
            family = configuration[name]
            source_cases = load_case_file(Path(family["source_cases"]["path"]))
            ids = {case.case_id for case in source_cases}
            if family.get("mode") != mode or len(source_cases) != count or ids & all_ids:
                raise ValueError("composed source families have changed versions, membership or counts")
            all_ids.update(ids)
            selected_cases = [case for case in cases if _case_id(case) in ids]
            selected_results = [result for result in results if _result_case_id(result) in ids]
            found, mapped, family_issues = load_source_predicate_evidence(
                configuration=family, cases=selected_cases, results=selected_results)
            annotations.update(found)
            bindings.update(mapped)
            issues.extend(f"{name}: {issue}" for issue in family_issues)
            manifests.update({case_id: Path(family["retained_manifest"]["path"]) for case_id in ids})
        if any(_case_id(case) not in all_ids for case in cases):
            issues.append("composed selection contains a case outside its frozen families")
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        issues.append(f"composed source evidence is incomplete: {exc}")
    return annotations, bindings, manifests, tuple(issues)


def _incomplete_semantic_release_report(
    *,
    selected_case_count: int,
    missing_case_ids: Sequence[str],
    duplicate_case_ids: Sequence[str],
    duplicate_result_ids: Sequence[str],
    annotations_match: bool,
    floors: Mapping[str, Any],
    release_required_slices: Mapping[str, Sequence[str]] | None,
) -> dict[str, Any]:
    """Fail closed without assigning semantic severity to partial evidence."""

    metrics = {
        name: _metric(name, 0, 0)
        for name in (
            "atomic_semantic_fidelity",
            "relation_fidelity",
            "clarification_identity",
            "unnecessary_question_rate",
        )
    }
    relation_metric = metrics["relation_fidelity"]
    relation_metric.update(
        {
            "sample_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "point_estimate": None,
            "evidence": "semantic scoring is unscored until the campaign is complete",
        }
    )
    overall = _metric("overall_case_success", 0, 0)
    required_slices = _required_release_slices(release_required_slices)
    release_minimum_samples = release_slice_minimum_sample_contract()
    confidence_contract = mapping_value(floors.get("statistical_confidence"))
    confidence_contract_issues = release_statistical_confidence_contract_issues(
        confidence_contract,
        minimum_samples=mapping_value(floors.get("release_slice_minimum_samples")),
    )
    minimum_sample_contract_issues = (
        release_slice_minimum_sample_contract_issues(
            floors.get("release_slice_minimum_samples")
        )
        if release_required_slices is not None
        else []
    )
    issues: list[str] = []
    if missing_case_ids:
        issues.append("semantic release results are incomplete")
    if not annotations_match:
        issues.append("semantic release annotations do not exactly match selected cases")
    if duplicate_case_ids:
        issues.append("semantic release cases contain duplicate IDs")
    if duplicate_result_ids:
        issues.append("semantic release results contain duplicate IDs")
    if release_required_slices is not None and (
        set(release_required_slices) != set(RELEASE_SLICE_DIMENSIONS)
        or required_slices != release_slice_contract()
    ):
        issues.append(
            "semantic release slice contract does not match the published operating envelope"
        )
    issues.extend(minimum_sample_contract_issues)
    issues.extend(confidence_contract_issues)
    return {
        "version": SEMANTIC_RELEASE_SCORE_VERSION,
        "status": "incomplete",
        "scoring_status": "unscored",
        "passed": False,
        "sample_count": 0,
        "selected_case_count": selected_case_count,
        "missing_case_ids": list(missing_case_ids),
        "duplicate_case_ids": list(duplicate_case_ids),
        "duplicate_result_ids": list(duplicate_result_ids),
        "metrics": metrics,
        "relation_sample_count": 0,
        "relation_fidelity_by_family": _relation_family_metrics(()),
        "relation_slices": [],
        "worst_relation_slice": {},
        "least_confident_relation_slice": {},
        "overall_case_success": overall,
        "worst_slice": {},
        "least_confident_slice": {},
        "slices": [],
        "p0_count": 0,
        "p0_findings": [],
        "p1_count": 0,
        "p1_findings": [],
        "acceptance_checks": [],
        "confidence_contract": confidence_contract,
        "confidence_contract_issues": confidence_contract_issues,
        "confidence_checks": [],
        "issues": list(dict.fromkeys(issues)),
        "release_required_slices": required_slices,
        "release_minimum_samples": (
            release_minimum_samples if release_required_slices is not None else {}
        ),
        "release_minimum_sample_contract_issues": minimum_sample_contract_issues,
        "release_evidence_issues": [],
        "relation_evidence_issues": [],
        "normalized_semantic_digests": {},
        "release_coverage_issues": [],
        "model_profiles": [],
        "case_outcomes": [],
    }


def _score_case(
    *,
    case: Any,
    case_id: str,
    annotation: Mapping[str, Any],
    result: GreenfieldMatrixResult,
    metric_counts: Mapping[str, list[int]],
    source_binding: Mapping[str, Any] | None = None,
    retained_evidence_manifest: Path | None = None,
) -> dict[str, Any]:
    expected = str(annotation.get("expected_outcome") or "")
    evidence = mapping_value(result.evidence)
    clarification = mapping_value(evidence.get("clarification"))
    receipt = mapping_value(evidence.get("preconfirm_dry_run"))
    snapshot = mapping_value(receipt.get("semantic_snapshot"))
    clarification_required = clarification.get("mode") == "clarification_required"
    stop_boundary_crossed = clarification_required and bool(evidence.get("preconfirm_dry_run"))
    if stop_boundary_crossed:
        observed = "failed"
    elif clarification_required:
        observed = "clarify"
    else:
        observed = "commit" if snapshot else "failed"
    failed_dimensions: list[str] = []
    p0: list[dict[str, str]] = []
    p1: list[dict[str, str]] = []
    relation_counts = empty_relation_counts()
    relation_evidence_issues: list[str] = []
    normalized_semantic_digest = ""
    if expected != observed or result.status != "passed" or not result.quality.passed:
        failed_dimensions.append("outcome")
    if stop_boundary_crossed:
        failed_dimensions.append("clarification_stop_boundary")
        p0.append(semantic_finding(case_id, "clarification_stop_boundary_crossed"))
    if expected == "clarify" and observed == "commit":
        p0.append(semantic_finding(case_id, "material_ambiguity_ignored"))

    if expected == "commit":
        metric_counts["unnecessary_question_rate"][1] += 1
        if observed == "clarify":
            metric_counts["unnecessary_question_rate"][0] += 1
        if snapshot and not stop_boundary_crossed:
            if source_binding is not None:
                relation_counts, relation_evidence_issues, normalized_semantic_digest = score_source_predicates(
                    case_id=case_id, annotation=annotation, binding=source_binding,
                    metric_counts=metric_counts, failed_dimensions=failed_dimensions, p0=p0, p1=p1)
            else:
                relation_counts, relation_evidence_issues, normalized_semantic_digest = score_native_commit(
                    case=case,
                    case_id=case_id,
                    annotation=annotation,
                    snapshot=snapshot,
                    actual_rows=_validated_atomic_facts(snapshot),
                    metric_counts=metric_counts,
                    failed_dimensions=failed_dimensions,
                    p0=p0,
                    p1=p1,
                )
    elif expected == "clarify":
        metric_counts["clarification_identity"][1] += 1
        expected_clarification = mapping_value(annotation.get("expected_clarification"))
        observed_fields = clarification.get("required_fields")
        exact_identity = (
            observed == "clarify"
            and isinstance(observed_fields, Sequence)
            and not isinstance(observed_fields, (str, bytes, bytearray))
            and list(observed_fields) == [expected_clarification.get("field")]
            and clarification.get("question") == expected_clarification.get("question")
        )
        if exact_identity:
            metric_counts["clarification_identity"][0] += 1
        else:
            failed_dimensions.append("clarification_identity")
        if source_binding is not None and observed == "clarify":
            relation_counts, relation_evidence_issues, normalized_semantic_digest = score_source_predicates(
                case_id=case_id, annotation=annotation, binding=source_binding, count_atomic=False,
                metric_counts=metric_counts, failed_dimensions=failed_dimensions, p0=p0, p1=p1)

    release_slices, release_evidence_issues = release_slice_evidence(
        case=case,
        result=result,
        annotated_complexity=mapping_value(annotation.get("complexity_dimensions" if source_binding is not None else "complexity")),
        source_predicate_complexity=mapping_value(annotation.get("complexity_dimensions")) if source_binding is not None else None,
        allow_unsealed_clarification=expected == "clarify" and observed == "clarify",
        retained_evidence_manifest=retained_evidence_manifest,
    )
    if release_evidence_issues:
        failed_dimensions.append("release_evidence")

    return {
        "case_id": case_id,
        "expected_outcome": expected,
        "observed_outcome": observed,
        "passed": not failed_dimensions and not p0,
        "failed_dimensions": list(dict.fromkeys(failed_dimensions)),
        "p0_findings": p0,
        "p1_findings": p1,
        "relation_counts": relation_counts,
        "relation_evidence_issues": relation_evidence_issues,
        "normalized_semantic_digest": normalized_semantic_digest,
        "release_slices": release_slices,
        "release_evidence_issues": list(release_evidence_issues),
    }


def _validated_atomic_facts(
    snapshot: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...] | None:
    """Keep native atomic custody at the input boundary of the moved case phase.

    Public source inputs enter through the complete canonical R1 snapshot reader
    before audited coverage reaches that same scoring phase.
    """
    value = snapshot.get("atomic_facts")
    try:
        require_atomic_fact_ledger(value, facts=mapping_value(snapshot.get("facts")))
    except ValueError:
        return None
    rows = mapping_rows(value)
    if str(snapshot.get("atomic_custody_sha256") or "") != atomic_fact_ledger_hash(rows):
        return None
    return rows


def _acceptance_checks(
    *,
    floors: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Any]],
    overall: Mapping[str, Any],
    worst_slice: Mapping[str, Any],
    worst_relation_slice: Mapping[str, Any],
    p0_findings: Sequence[Mapping[str, str]],
    p1_findings: Sequence[Mapping[str, str]],
    allow_not_applicable_metrics: bool,
) -> list[dict[str, Any]]:
    checks = [
        _check("no_observed_p0_contradiction", not p0_findings, "observed P0 semantic contradiction"),
        _check(
            "no_observed_p1_relation_defect",
            not p1_findings,
            "observed P1 typed-relation defect",
        ),
    ]
    for name in ("atomic_semantic_fidelity", "relation_fidelity", "clarification_identity"):
        checks.append(
            _acceptance_metric_floor_check(
                name,
                metrics[name],
                floors.get(name),
                allow_not_applicable=(
                    allow_not_applicable_metrics and name != "relation_fidelity"
                ),
            )
        )
    checks.append(
        _acceptance_metric_ceiling_check(
            "unnecessary_question_rate",
            metrics["unnecessary_question_rate"],
            floors.get("unnecessary_question_rate_ceiling"),
            allow_not_applicable=allow_not_applicable_metrics,
        )
    )
    checks.append(
        _acceptance_metric_floor_check(
            "overall_case_success",
            overall,
            floors.get("overall_case_success"),
        )
    )
    checks.append(
        threshold_check(
            "worst_slice_success",
            observed=(
                worst_slice.get("point_estimate")
                if worst_slice
                else None
            ),
            expected=floors.get("worst_slice_success"),
            direction="floor",
        )
    )
    checks.append(
        threshold_check(
            "worst_relation_slice_fidelity",
            observed=(
                worst_relation_slice.get("point_estimate")
                if worst_relation_slice
                else None
            ),
            expected=floors.get("relation_fidelity"),
            direction="floor",
        )
    )
    return checks


def _confidence_checks(
    *,
    confidence: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Any]],
    relation_family_metrics: Mapping[str, Mapping[str, Any]],
    overall: Mapping[str, Any],
    least_confident_slice: Mapping[str, Any],
    least_confident_relation_slice: Mapping[str, Any],
    allow_not_applicable_metrics: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name in ("atomic_semantic_fidelity", "relation_fidelity", "clarification_identity"):
        checks.append(
            _confidence_metric_floor_check(
                name,
                metrics[name],
                confidence.get(name),
                allow_not_applicable=(
                    allow_not_applicable_metrics and name != "relation_fidelity"
                ),
            )
        )
    checks.append(
        _confidence_metric_ceiling_check(
            "unnecessary_question_rate",
            metrics["unnecessary_question_rate"],
            confidence.get("unnecessary_question_rate_ceiling"),
            allow_not_applicable=allow_not_applicable_metrics,
        )
    )
    checks.append(
        _confidence_metric_floor_check(
            "overall_case_success",
            overall,
            confidence.get("overall_case_success"),
        )
    )
    checks.append(
        threshold_check(
            "worst_slice_success",
            observed=(
                mapping_value(least_confident_slice.get("confidence_interval_95")).get("lower")
                if least_confident_slice
                else None
            ),
            expected=confidence.get("worst_slice_success"),
            direction="floor",
        )
    )
    checks.append(
        threshold_check(
            "worst_relation_slice_fidelity",
            observed=(
                mapping_value(least_confident_relation_slice.get("confidence_interval_95")).get("lower")
                if least_confident_relation_slice
                else None
            ),
            expected=confidence.get("relation_fidelity"),
            direction="floor",
        )
    )
    for family, metric in sorted(relation_family_metrics.items()):
        checks.append(
            _confidence_metric_floor_check(
                f"relation_fidelity:{family}",
                metric,
                confidence.get("relation_fidelity"),
                allow_not_applicable=True,
            )
        )
    return checks


def _model_profile_reports(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
    case_outcomes: Sequence[Mapping[str, Any]],
    source_predicate_evidence: Mapping[str, Any] | None = None,
    retained_evidence_manifest: Path | None = None,
) -> list[dict[str, Any]]:
    profile_by_case = {
        str(outcome.get("case_id") or ""): str(
            mapping_value(outcome.get("release_slices")).get("model_profile") or ""
        )
        for outcome in case_outcomes
    }
    grouped: dict[str, list[Any]] = defaultdict(list)
    for case in cases:
        profile = profile_by_case.get(_case_id(case), "")
        if profile:
            grouped[profile].append(case)
    results_by_id = {_result_case_id(result): result for result in results}
    reports: list[dict[str, Any]] = []
    for profile, profile_cases in sorted(grouped.items()):
        case_ids = {_case_id(case) for case in profile_cases}
        report = evaluate_semantic_release(
            cases=profile_cases,
            annotations={case_id: annotations[case_id] for case_id in case_ids if case_id in annotations},
            results=[results_by_id[case_id] for case_id in case_ids if case_id in results_by_id],
            floors=floors,
            release_required_slices=None,
            source_predicate_evidence=source_predicate_evidence,
            retained_evidence_manifest=retained_evidence_manifest,
            _include_model_profiles=False,
            _allow_not_applicable_metrics=True,
        )
        reports.append(
            {
                "profile": profile,
                "status": report["status"],
                "passed": report["passed"],
                "sample_count": report["sample_count"],
                "metrics": report["metrics"],
                "overall_case_success": report["overall_case_success"],
                "worst_slice": report["worst_slice"],
                "least_confident_slice": report["least_confident_slice"],
                "worst_relation_slice": report["worst_relation_slice"],
                "least_confident_relation_slice": report[
                    "least_confident_relation_slice"
                ],
                "relation_slices": report["relation_slices"],
                "p0_count": report["p0_count"],
                "p1_count": report["p1_count"],
                "acceptance_checks": report["acceptance_checks"],
                "confidence_contract": report["confidence_contract"],
                "confidence_contract_issues": report[
                    "confidence_contract_issues"
                ],
                "confidence_checks": report["confidence_checks"],
                "issues": report["issues"],
            }
        )
    return reports


def _acceptance_metric_floor_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return threshold_check(name, observed=observed, expected=expected, direction="floor")


def _acceptance_metric_ceiling_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return threshold_check(name, observed=observed, expected=expected, direction="ceiling")


def _confidence_metric_floor_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = (
        mapping_value(metric.get("confidence_interval_95")).get("lower")
        if metric.get("status") == "measured"
        else None
    )
    return threshold_check(name, observed=observed, expected=expected, direction="floor")


def _confidence_metric_ceiling_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = (
        mapping_value(metric.get("confidence_interval_95")).get("upper")
        if metric.get("status") == "measured"
        else None
    )
    return threshold_check(name, observed=observed, expected=expected, direction="ceiling")


def _not_applicable_check(name: str, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "not_applicable",
        "observed": None,
        "expected": expected,
        "issue": "",
    }


def _check(name: str, passed: bool, issue: str) -> dict[str, Any]:
    return {"name": name, "status": "passed" if passed else "failed", "issue": "" if passed else issue}


def _metric(name: str, numerator: int, denominator: int) -> dict[str, Any]:
    metric = {
        "name": name,
        "status": "measured" if denominator else "not_applicable",
        "numerator": int(numerator),
        "denominator": int(denominator),
        "rate": round(numerator / denominator, 6) if denominator else None,
    }
    if denominator:
        lower, upper = wilson_interval(numerator, denominator)
        metric["confidence_interval_95"] = _interval_payload(lower, upper)
    else:
        metric["confidence_interval_95"] = None
    return metric


def _slice_rows(*, cases: Sequence[Any], outcomes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    outcome_by_id = {str(row["case_id"]): bool(row["passed"]) for row in outcomes}
    release_slices_by_id = {
        str(row.get("case_id") or ""): mapping_value(row.get("release_slices"))
        for row in outcomes
    }
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for case in cases:
        case_id = _case_id(case)
        if case_id not in outcome_by_id:
            continue
        release_slices = release_slices_by_id.get(case_id, {})
        for dimension, value in (
            *_case_slices(case),
            *((dimension, str(release_slices.get(dimension) or "")) for dimension in RELEASE_SLICE_DIMENSIONS),
        ):
            if not value:
                continue
            grouped[(dimension, value)].append(outcome_by_id[case_id])
    rows: list[dict[str, Any]] = []
    for (dimension, value), values in sorted(grouped.items()):
        passed = sum(values)
        total = len(values)
        lower, upper = wilson_interval(passed, total)
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "sample_count": total,
                "passed_count": passed,
                "failed_count": total - passed,
                "point_estimate": round(passed / total, 6),
                "confidence_interval_95": _interval_payload(lower, upper),
            }
        )
    return rows


def _relation_slice_rows(
    *,
    cases: Sequence[Any],
    outcomes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    counts_by_id = {
        str(row.get("case_id") or ""): mapping_value(row.get("relation_counts"))
        for row in outcomes
    }
    release_slices_by_id = {
        str(row.get("case_id") or ""): mapping_value(row.get("release_slices"))
        for row in outcomes
    }
    grouped: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for case in cases:
        case_id = _case_id(case)
        counts = counts_by_id.get(case_id, {})
        sample_count = int(counts.get("sample_count", 0) or 0)
        if sample_count <= 0:
            continue
        matched = int(counts.get("matched", 0) or 0)
        release_slices = release_slices_by_id.get(case_id, {})
        for dimension, value in (
            *_case_slices(case),
            *((dimension, str(release_slices.get(dimension) or "")) for dimension in RELEASE_SLICE_DIMENSIONS),
        ):
            if not value:
                continue
            grouped[(dimension, value)][0] += matched
            grouped[(dimension, value)][1] += sample_count
    rows: list[dict[str, Any]] = []
    for (dimension, value), (matched, sample_count) in sorted(grouped.items()):
        lower, upper = wilson_interval(matched, sample_count)
        rows.append(
            {
                "dimension": dimension,
                "value": value,
                "sample_count": sample_count,
                "correct_count": matched,
                "incorrect_count": sample_count - matched,
                "point_estimate": round(matched / sample_count, 6),
                "confidence_interval_95": _interval_payload(lower, upper),
            }
        )
    return rows


def _relation_family_metrics(
    outcomes: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    totals = {family: [0, 0] for family in RELATION_FAMILIES}
    for outcome in outcomes:
        families = mapping_value(mapping_value(outcome.get("relation_counts")).get("families"))
        for family in RELATION_FAMILIES:
            counts = mapping_value(families.get(family))
            totals[family][0] += int(counts.get("matched", 0) or 0)
            totals[family][1] += int(counts.get("sample_count", 0) or 0)
    metrics: dict[str, dict[str, Any]] = {}
    for family, (matched, sample_count) in totals.items():
        metric = _metric(family, matched, sample_count)
        metric["sample_count"] = sample_count
        metric["correct_count"] = matched
        metric["incorrect_count"] = sample_count - matched
        metric["point_estimate"] = metric["rate"]
        if not sample_count:
            metric["evidence"] = "no relation samples for this family"
        metrics[family] = metric
    return metrics


def _case_slices(case: Any) -> tuple[tuple[str, str], ...]:
    provenance = getattr(case, "provenance", None)
    rows = [
        ("input_style", str(getattr(case, "input_style", "") or "unspecified")),
        ("expectation", str(getattr(case, "expectation", "") or "transaction_committed")),
        ("source_family", str(getattr(provenance, "source_family", "") or "unspecified")),
    ]
    return tuple(dict.fromkeys(rows))


def _required_release_slices(
    value: Mapping[str, Sequence[str]] | None,
) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    normalized: dict[str, tuple[str, ...]] = {}
    for dimension in RELEASE_SLICE_DIMENSIONS:
        rows = value.get(dimension)
        if not is_sequence(rows):
            normalized[dimension] = ()
            continue
        normalized[dimension] = tuple(
            dict.fromkeys(str(item or "").strip() for item in rows if str(item or "").strip())
        )
    return normalized


def _duplicates(values: Sequence[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _interval_payload(lower: float, upper: float) -> dict[str, Any]:
    return {
        "method": "wilson",
        "lower": lower,
        "upper": upper,
        "inference_scope": "descriptive fixed-corpus score interval; not a population user-utility claim",
    }


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    case = mapping_value(mapping_value(result.evidence).get("case"))
    return str(case.get("id") or "").strip()

__all__ = ["SEMANTIC_RELEASE_SCORE_VERSION", "evaluate_semantic_release"]
