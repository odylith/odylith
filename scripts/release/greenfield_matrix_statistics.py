"""Statistical release evidence for Greenfield matrix outcomes."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import sqrt
from typing import Any

from greenfield_matrix_types import GreenfieldMatrixResult


STATISTICS_VERSION = "odylith.greenfield.matrix.statistics.v1"
_Z_95 = 1.959963984540054


def outcome_statistics(
    *,
    cases: Sequence[Any],
    results: Sequence[GreenfieldMatrixResult],
) -> dict[str, Any]:
    """Report point estimates, Wilson intervals, and worst observed slices."""

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    results_by_id = {case_id: result for case_id, result in zip(result_ids, results, strict=False) if case_id}
    rows: list[dict[str, Any]] = []
    slice_members: dict[tuple[str, str], list[bool]] = defaultdict(list)
    missing_case_ids: list[str] = []
    for case in cases:
        case_id = _case_id(case)
        result = results_by_id.get(case_id)
        if result is None:
            missing_case_ids.append(case_id)
            continue
        passed = result.status == "passed" and result.quality.passed
        rows.append({"case_id": case_id, "passed": passed})
        for dimension, value in _case_slices(case):
            slice_members[(dimension, value)].append(passed)

    passed_count = sum(1 for row in rows if row["passed"])
    sample_count = len(rows)
    slices = [
        _slice_row(dimension=dimension, value=value, outcomes=outcomes)
        for (dimension, value), outcomes in sorted(slice_members.items())
    ]
    completed_slices = [row for row in slices if int(row["sample_count"]) > 0]
    worst = min(
        completed_slices,
        key=lambda row: (
            float(row["point_estimate"]),
            float(row["confidence_interval_95"]["lower"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default=None,
    )
    lower, upper = wilson_interval(passed_count, sample_count)
    complete = not missing_case_ids and not duplicate_case_ids and not duplicate_result_ids
    return {
        "version": STATISTICS_VERSION,
        "status": "complete" if complete else "incomplete",
        "selected_case_count": len(cases),
        "sample_count": sample_count,
        "passed_count": passed_count,
        "failed_count": sample_count - passed_count,
        "point_estimate": _rate(passed_count, sample_count),
        "confidence_interval_95": _interval_payload(lower, upper),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "worst_slice": worst or {},
        "slices": slices,
    }


def wilson_interval(successes: int, sample_count: int) -> tuple[float, float]:
    """Return a bounded 95% Wilson score interval for a binomial rate."""

    if sample_count <= 0:
        return 0.0, 1.0
    successes = max(0, min(int(successes), int(sample_count)))
    n = float(sample_count)
    estimate = successes / n
    z2 = _Z_95 * _Z_95
    denominator = 1.0 + z2 / n
    center = (estimate + z2 / (2.0 * n)) / denominator
    margin = (_Z_95 / denominator) * sqrt((estimate * (1.0 - estimate) / n) + (z2 / (4.0 * n * n)))
    return round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)


def _slice_row(*, dimension: str, value: str, outcomes: Sequence[bool]) -> dict[str, Any]:
    passed = sum(1 for outcome in outcomes if outcome)
    total = len(outcomes)
    lower, upper = wilson_interval(passed, total)
    return {
        "dimension": dimension,
        "value": value,
        "sample_count": total,
        "passed_count": passed,
        "failed_count": total - passed,
        "point_estimate": _rate(passed, total),
        "confidence_interval_95": _interval_payload(lower, upper),
    }


def _case_slices(case: Any) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    input_style = str(getattr(case, "input_style", "") or "unspecified").strip()
    values.append(("input_style", input_style))
    expectation = str(getattr(case, "expectation", "") or "transaction_committed").strip()
    values.append(("expectation", expectation))
    provenance = getattr(case, "provenance", None)
    source_family = str(getattr(provenance, "source_family", "") or "unspecified").strip()
    values.append(("source_family", source_family))
    for stressor in getattr(case, "stressors", ()) or ():
        token = str(stressor or "").strip()
        if token:
            values.append(("stressor", token))
    for tag in getattr(case, "tags", ()) or ():
        token = str(tag or "").strip()
        if token.startswith("complexity:"):
            values.append(("complexity", token.partition(":")[2] or "unspecified"))
        elif token.startswith("model-profile:"):
            values.append(("model_profile", token.partition(":")[2] or "unspecified"))
        elif token.startswith("host-profile:"):
            values.append(("host_profile", token.partition(":")[2] or "unspecified"))
    return tuple(dict.fromkeys(values))


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
    case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
    return str(case.get("id") or "").strip()


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _rate(successes: int, sample_count: int) -> float:
    return round(successes / sample_count, 6) if sample_count else 0.0


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


__all__ = ["STATISTICS_VERSION", "outcome_statistics", "wilson_interval"]
