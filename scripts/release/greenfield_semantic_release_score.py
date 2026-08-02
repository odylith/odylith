"""Deterministic semantic release scoring against blinded atomic annotations."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import re
from typing import Any

from greenfield_matrix_statistics import wilson_interval
from greenfield_matrix_types import GreenfieldMatrixResult


SEMANTIC_RELEASE_SCORE_VERSION = "odylith.greenfield.semantic-release-score.v1"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "before",
        "by",
        "can",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "one",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "with",
    }
)
_VALID_MATERIAL_CUSTODY = frozenset({"accepted_fact", "bounded_interpretation"})
_CATEGORY_FACT_FIELDS = {
    "actors": ("human_actors", "customer"),
    "actions": ("first_path", "component_responsibilities"),
    "states": ("state_object", "first_path"),
    "outputs": ("first_path", "success_metrics", "proof_boundary", "product_story"),
    "constraints": ("operational_constraints", "proof_boundary", "non_goals"),
    "dependencies": ("external_systems", "internal_systems", "component_responsibilities"),
    "assumptions": ("assumptions",),
    "ambiguities": ("ambiguities",),
    "non_goals": ("non_goals",),
}


def evaluate_semantic_release(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
    _include_model_profiles: bool = True,
    _allow_not_applicable_metrics: bool = False,
) -> dict[str, Any]:
    """Score result semantics without returning blinded evidence text."""

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    results_by_id = {case_id: result for case_id, result in zip(result_ids, results, strict=False) if case_id}
    metric_counts: dict[str, list[int]] = {
        "accepted_fact_custody": [0, 0],
        "critical_constraint_recall": [0, 0],
        "explicit_system_recall": [0, 0],
        "material_question_recall": [0, 0],
        "unnecessary_question_rate": [0, 0],
        "first_path_comprehension": [0, 0],
    }
    case_outcomes: list[dict[str, Any]] = []
    p0_findings: list[dict[str, str]] = []
    missing_case_ids: list[str] = []
    for case in cases:
        case_id = _case_id(case)
        annotation = annotations.get(case_id)
        result = results_by_id.get(case_id)
        if annotation is None or result is None:
            missing_case_ids.append(case_id)
            continue
        outcome = _score_case(
            case=case,
            annotation=annotation,
            result=result,
            metric_counts=metric_counts,
        )
        case_outcomes.append(outcome)
        p0_findings.extend(outcome["p0_findings"])

    metrics = {name: _metric(name, *counts) for name, counts in metric_counts.items()}
    passed_count = sum(1 for outcome in case_outcomes if outcome["passed"])
    sample_count = len(case_outcomes)
    overall = _metric("overall_case_success", passed_count, sample_count)
    lower, upper = wilson_interval(passed_count, sample_count)
    overall["confidence_interval_95"] = _interval_payload(lower, upper)
    slices = _slice_rows(cases=cases, outcomes=case_outcomes)
    worst_slice = min(
        slices,
        key=lambda row: (float(row["point_estimate"]), str(row["dimension"]), str(row["value"])),
        default={},
    )
    checks = _floor_checks(
        floors=floors,
        metrics=metrics,
        overall=overall,
        worst_slice=worst_slice,
        p0_findings=p0_findings,
        allow_not_applicable_metrics=_allow_not_applicable_metrics,
    )
    issues = [
        str(check["issue"])
        for check in checks
        if check["status"] in {"failed", "unproven"} and str(check.get("issue") or "").strip()
    ]
    if missing_case_ids:
        issues.append("semantic release results are incomplete")
    if duplicate_case_ids:
        issues.append("semantic release cases contain duplicate IDs")
    if duplicate_result_ids:
        issues.append("semantic release results contain duplicate IDs")
    model_profiles = (
        _model_profile_reports(
            cases=cases,
            annotations=annotations,
            results=results,
            floors=floors,
        )
        if _include_model_profiles
        else []
    )
    for profile in model_profiles:
        if profile["status"] != "passed":
            issues.append(f"model profile `{profile['profile']}` failed the semantic release floors")
    return {
        "version": SEMANTIC_RELEASE_SCORE_VERSION,
        "status": "passed" if not issues else "failed",
        "passed": not issues,
        "sample_count": sample_count,
        "selected_case_count": len(cases),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "metrics": metrics,
        "overall_case_success": overall,
        "worst_slice": worst_slice,
        "slices": slices,
        "p0_count": len(p0_findings),
        "p0_findings": p0_findings,
        "floor_checks": checks,
        "issues": list(dict.fromkeys(issues)),
        "model_profiles": model_profiles,
        "case_outcomes": [
            {
                "case_id": row["case_id"],
                "passed": row["passed"],
                "expected_outcome": row["expected_outcome"],
                "observed_outcome": row["observed_outcome"],
                "failed_dimensions": row["failed_dimensions"],
            }
            for row in case_outcomes
        ],
    }


def _model_profile_reports(
    *,
    cases: Sequence[Any],
    annotations: Mapping[str, Mapping[str, Any]],
    results: Sequence[GreenfieldMatrixResult],
    floors: Mapping[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for case in cases:
        profile = _model_profile(case)
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
                "p0_count": report["p0_count"],
                "floor_checks": report["floor_checks"],
                "issues": report["issues"],
            }
        )
    return reports


def _model_profile(case: Any) -> str:
    profiles = [
        str(tag).partition(":")[2]
        for tag in getattr(case, "tags", ()) or ()
        if str(tag).startswith("model-profile:")
    ]
    return profiles[0] if len(profiles) == 1 else ""


def _score_case(
    *,
    case: Any,
    annotation: Mapping[str, Any],
    result: GreenfieldMatrixResult,
    metric_counts: Mapping[str, list[int]],
) -> dict[str, Any]:
    case_id = _case_id(case)
    expected = str(annotation.get("expected_outcome") or "").strip()
    evidence = _mapping(result.evidence)
    clarification = _mapping(evidence.get("clarification"))
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    snapshot = _mapping(receipt.get("semantic_snapshot"))
    facts = _mapping(snapshot.get("facts"))
    if str(clarification.get("mode") or "") == "clarification_required":
        observed = "clarify"
    else:
        observed = "commit" if snapshot else "failed"
    failed_dimensions: list[str] = []
    p0: list[dict[str, str]] = []
    if expected != observed or result.status != "passed" or not result.quality.passed:
        failed_dimensions.append("outcome")
    if expected == "clarify" and observed == "commit":
        p0.append(_p0(case_id, "material_ambiguity_ignored"))

    if expected == "commit":
        metric_counts["unnecessary_question_rate"][1] += 1
        if observed == "clarify":
            metric_counts["unnecessary_question_rate"][0] += 1
        _score_commit_semantics(
            case_id=case_id,
            annotation=annotation,
            snapshot=snapshot,
            facts=facts,
            metric_counts=metric_counts,
            failed_dimensions=failed_dimensions,
            p0=p0,
        )
    elif expected == "clarify":
        metric_counts["material_question_recall"][1] += 1
        expected_fields = set(_strings(annotation.get("expected_question_fields")))
        observed_fields = set(_strings(clarification.get("required_fields")))
        question_recalled = observed == "clarify" and (not expected_fields or expected_fields <= observed_fields)
        if question_recalled:
            metric_counts["material_question_recall"][0] += 1
        else:
            failed_dimensions.append("material_question_recall")

    return {
        "case_id": case_id,
        "expected_outcome": expected,
        "observed_outcome": observed,
        "passed": not failed_dimensions and not p0,
        "failed_dimensions": list(dict.fromkeys(failed_dimensions)),
        "p0_findings": p0,
    }


def _score_commit_semantics(
    *,
    case_id: str,
    annotation: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    facts: Mapping[str, Any],
    metric_counts: Mapping[str, list[int]],
    failed_dimensions: list[str],
    p0: list[dict[str, str]],
) -> None:
    material_custody = _mapping(snapshot.get("material_custody"))
    for category in _atomic_categories():
        for item in _items(annotation.get(category)):
            if str(item.get("expected_custody") or "") != "accepted_fact":
                continue
            metric_counts["accepted_fact_custody"][1] += 1
            if _claim_has_custody(
                category=category,
                value=item.get("value"),
                expected_custody="accepted_fact",
                facts=facts,
                material_custody=material_custody,
            ):
                metric_counts["accepted_fact_custody"][0] += 1
            else:
                failed_dimensions.append("accepted_fact_custody")

    constraint_text = _flatten_text(
        {
            "operational_constraints": facts.get("operational_constraints"),
            "non_goals": facts.get("non_goals"),
            "proof_boundary": facts.get("proof_boundary"),
        }
    )
    for value in _expected_values(annotation.get("critical_constraints")):
        metric_counts["critical_constraint_recall"][1] += 1
        if _claim_recalled(value, constraint_text):
            metric_counts["critical_constraint_recall"][0] += 1
        else:
            failed_dimensions.append("critical_constraint_recall")
            p0.append(_p0(case_id, "critical_constraint_missing"))

    system_text = _flatten_text(
        {
            "external_systems": facts.get("external_systems"),
            "internal_systems": facts.get("internal_systems"),
            "dependencies": facts.get("component_responsibilities"),
        }
    )
    for value in _expected_values(annotation.get("explicit_systems")):
        metric_counts["explicit_system_recall"][1] += 1
        if _claim_recalled(value, system_text):
            metric_counts["explicit_system_recall"][0] += 1
        else:
            failed_dimensions.append("explicit_system_recall")
            p0.append(_p0(case_id, "explicit_system_missing"))

    first_path_text = _flatten_text(
        {
            "human_actors": facts.get("human_actors"),
            "state_object": facts.get("state_object"),
            "first_path": facts.get("first_path"),
            "proof_boundary": facts.get("proof_boundary"),
        }
    )
    first_path_items = [
        item
        for category in ("actors", "actions", "states", "outputs")
        for item in _items(annotation.get(category))
        if str(item.get("materiality") or "") == "material"
    ]
    for item in first_path_items:
        metric_counts["first_path_comprehension"][1] += 1
        if _claim_recalled(item.get("value"), first_path_text):
            metric_counts["first_path_comprehension"][0] += 1
        else:
            failed_dimensions.append("first_path_comprehension")


def _floor_checks(
    *,
    floors: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Any]],
    overall: Mapping[str, Any],
    worst_slice: Mapping[str, Any],
    p0_findings: Sequence[Mapping[str, str]],
    allow_not_applicable_metrics: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "no_observed_p0_contradiction",
            not p0_findings,
            "observed P0 semantic contradiction",
        )
    )
    for name in (
        "accepted_fact_custody",
        "critical_constraint_recall",
        "explicit_system_recall",
        "material_question_recall",
        "first_path_comprehension",
    ):
        checks.append(
            _metric_floor_check(
                name,
                metrics[name],
                floors.get(name),
                allow_not_applicable=allow_not_applicable_metrics,
            )
        )
    checks.append(
        _metric_ceiling_check(
            "unnecessary_question_rate",
            metrics["unnecessary_question_rate"],
            floors.get("unnecessary_question_rate_ceiling"),
            allow_not_applicable=allow_not_applicable_metrics,
        )
    )
    checks.append(
        _metric_floor_check(
            "overall_case_success",
            overall,
            floors.get("overall_case_success"),
            allow_not_applicable=False,
        )
    )
    worst_rate = worst_slice.get("point_estimate") if worst_slice else None
    checks.append(
        _check_threshold(
            "worst_slice_success",
            observed=worst_rate,
            expected=floors.get("worst_slice_success"),
            direction="floor",
        )
    )
    return checks


def _metric_floor_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return _check_threshold(name, observed=observed, expected=expected, direction="floor")


def _metric_ceiling_check(
    name: str,
    metric: Mapping[str, Any],
    expected: Any,
    *,
    allow_not_applicable: bool = False,
) -> dict[str, Any]:
    if allow_not_applicable and metric.get("status") == "not_applicable":
        return _not_applicable_check(name, expected)
    observed = metric.get("rate") if metric.get("status") == "measured" else None
    return _check_threshold(name, observed=observed, expected=expected, direction="ceiling")


def _not_applicable_check(name: str, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "not_applicable",
        "observed": None,
        "expected": expected,
        "issue": "",
    }


def _check_threshold(name: str, *, observed: Any, expected: Any, direction: str) -> dict[str, Any]:
    if not isinstance(expected, (int, float)) or isinstance(expected, bool):
        return {
            "name": name,
            "status": "unproven",
            "observed": observed,
            "expected": expected,
            "issue": f"{name} has no frozen threshold",
        }
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        return {
            "name": name,
            "status": "unproven",
            "observed": observed,
            "expected": expected,
            "issue": f"{name} is unproven (0 of 0 is not a pass)",
        }
    passed = observed >= expected if direction == "floor" else observed <= expected
    symbol = ">=" if direction == "floor" else "<="
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "observed": observed,
        "expected": expected,
        "issue": "" if passed else f"{name} {observed:.6f} does not satisfy {symbol} {expected:.6f}",
    }


def _check(name: str, passed: bool, issue: str) -> dict[str, Any]:
    return {"name": name, "status": "passed" if passed else "failed", "issue": "" if passed else issue}


def _metric(name: str, numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "name": name,
        "status": "measured" if denominator else "not_applicable",
        "numerator": int(numerator),
        "denominator": int(denominator),
        "rate": round(numerator / denominator, 6) if denominator else None,
    }


def _slice_rows(*, cases: Sequence[Any], outcomes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    outcome_by_id = {str(row["case_id"]): bool(row["passed"]) for row in outcomes}
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for case in cases:
        case_id = _case_id(case)
        if case_id not in outcome_by_id:
            continue
        for dimension, value in _case_slices(case):
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


def _case_slices(case: Any) -> tuple[tuple[str, str], ...]:
    rows = [
        ("input_style", str(getattr(case, "input_style", "") or "unspecified")),
        ("expectation", str(getattr(case, "expectation", "") or "transaction_committed")),
    ]
    for tag in getattr(case, "tags", ()) or ():
        token = str(tag or "").strip()
        if ":" in token:
            dimension, _, value = token.partition(":")
            if dimension in {"complexity", "model-profile", "host-profile", "slice"}:
                rows.append((dimension.replace("-", "_"), value or "unspecified"))
    return tuple(dict.fromkeys(rows))


def _claim_has_custody(
    *,
    category: str,
    value: Any,
    expected_custody: str,
    facts: Mapping[str, Any],
    material_custody: Mapping[str, Any],
) -> bool:
    for field in _CATEGORY_FACT_FIELDS.get(category, ()):
        if not _claim_recalled(value, _flatten_text(facts.get(field))):
            continue
        custody_state = str(_mapping(material_custody.get(field)).get("custody_state") or "")
        if custody_state == expected_custody and custody_state in _VALID_MATERIAL_CUSTODY:
            return True
    return False


def _claim_recalled(expected: Any, observed: str) -> bool:
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return False
    observed_tokens = _tokens(observed)
    return expected_tokens <= observed_tokens and _negation_signature(expected) == _negation_signature(observed)


def _negation_signature(value: Any) -> frozenset[str]:
    tokens = set(_TOKEN_RE.findall(str(value or "").casefold()))
    return frozenset(tokens & {"no", "not", "never", "without"})


def _tokens(value: Any) -> frozenset[str]:
    return frozenset(
        token
        for token in _TOKEN_RE.findall(str(value or "").casefold())
        if token not in _STOPWORDS
    )


def _flatten_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _items(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _expected_values(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            text = str(item.get("value") or "").strip() if isinstance(item, Mapping) else str(item or "").strip()
            if text:
                values.append(text)
    return tuple(values)


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item or "").strip() for item in value if str(item or "").strip())


def _atomic_categories() -> tuple[str, ...]:
    return (
        "actors",
        "actions",
        "states",
        "outputs",
        "constraints",
        "dependencies",
        "assumptions",
        "ambiguities",
        "non_goals",
    )


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


def _p0(case_id: str, category: str) -> dict[str, str]:
    return {"case_id": case_id, "category": category}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    case = _mapping(_mapping(result.evidence).get("case"))
    return str(case.get("id") or "").strip()


__all__ = ["SEMANTIC_RELEASE_SCORE_VERSION", "evaluate_semantic_release"]
