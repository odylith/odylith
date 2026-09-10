"""Statistical release evidence for Greenfield matrix outcomes."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from math import sqrt
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    require_greenfield_model_profile_observation,
    supported_greenfield_model_profile_ids,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    SUPPORTED_COMPLEXITY_BANDS,
    SUPPORTED_PUBLIC_INPUT_FORMATS,
    greenfield_complexity_band,
    require_supported_greenfield_operating_envelope,
)

from greenfield_matrix_types import GreenfieldMatrixResult


STATISTICS_VERSION = "odylith.greenfield.matrix.statistics.v3"
STATISTICAL_CONFIDENCE_VERSION = "odylith.greenfield.statistical-confidence.v1"
_Z_95 = 1.959963984540054
_MINIMUM_RELEASE_SLICE_SAMPLES = 4
_CONFIDENCE_THRESHOLD_KEYS = frozenset(
    {
        "atomic_semantic_fidelity",
        "relation_fidelity",
        "clarification_identity",
        "unnecessary_question_rate_ceiling",
        "overall_case_success",
        "worst_slice_success",
    }
)
RELEASE_SLICE_DIMENSIONS = (
    "complexity_band",
    "evidence_format",
    "model_profile",
)
_DISCOVERY_TAG_SLICE_DIMENSIONS = frozenset(
    {"complexity", "model_profile", "host_profile"}
)


def outcome_statistics(
    *,
    cases: Sequence[Any],
    results: Sequence[GreenfieldMatrixResult],
    release: bool = False,
    required_slices: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Report point estimates, intervals, and evidence-bound release slices.

    Discovery retains the historic descriptive tag slices.  Release reports
    instead classify the support-critical axes from each sealed transaction;
    case tags cannot manufacture coverage.
    """

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    results_by_id = {case_id: result for case_id, result in zip(result_ids, results, strict=False) if case_id}
    rows: list[dict[str, Any]] = []
    slice_members: dict[tuple[str, str], list[bool]] = defaultdict(list)
    missing_case_ids: list[str] = []
    evidence_issues: list[str] = []
    for case in cases:
        case_id = _case_id(case)
        result = results_by_id.get(case_id)
        if result is None:
            missing_case_ids.append(case_id)
            continue
        passed = result.status == "passed" and result.quality.passed
        rows.append({"case_id": case_id, "passed": passed})
        slices = _case_slices(case)
        if release:
            sealed_slices, sealed_issues = release_slice_evidence(
                case=case,
                result=result,
            )
            evidence_issues.extend(
                f"case `{case_id}` {issue}"
                for issue in sealed_issues
            )
            slices = (
                *(
                    row
                    for row in slices
                    if row[0] not in _DISCOVERY_TAG_SLICE_DIMENSIONS
                ),
                *sealed_slices.items(),
            )
        for dimension, value in slices:
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
    least_confident = min(
        completed_slices,
        key=lambda row: (
            float(row["confidence_interval_95"]["lower"]),
            float(row["point_estimate"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default=None,
    )
    lower, upper = wilson_interval(passed_count, sample_count)
    supplied_release_contract = (
        required_slices if required_slices is not None else release_slice_contract()
    )
    release_contract = _normalized_slice_contract(supplied_release_contract) if release else {}
    release_contract_issues = (
        _release_slice_contract_issues(
            supplied=supplied_release_contract,
            normalized=release_contract,
        )
        if release
        else []
    )
    release_minimum_samples = release_slice_minimum_sample_contract() if release else {}
    coverage_issues = (
        release_slice_coverage_issues(
            slices=slices,
            required=release_contract,
            minimum_samples=release_minimum_samples,
        )
        if release
        else []
    )
    failing_release_slices = [
        row
        for row in slices
        if row["dimension"] in release_contract and int(row["failed_count"]) > 0
    ]
    complete = not (
        missing_case_ids
        or duplicate_case_ids
        or duplicate_result_ids
        or evidence_issues
        or release_contract_issues
        or coverage_issues
    )
    confidence_contract = release_statistical_confidence_contract() if release else {}
    acceptance_checks = (
        [
            threshold_check(
                "overall_case_success",
                observed=_rate(passed_count, sample_count) if sample_count else None,
                expected=1.0,
                direction="floor",
            ),
            threshold_check(
                "worst_slice_success",
                observed=worst.get("point_estimate") if worst else None,
                expected=1.0,
                direction="floor",
            ),
        ]
        if release
        else []
    )
    confidence_checks = (
        [
            threshold_check(
                "overall_case_success",
                observed=lower if sample_count else None,
                expected=confidence_contract.get("overall_case_success"),
                direction="floor",
            ),
            threshold_check(
                "worst_slice_success",
                observed=(
                    _mapping(least_confident.get("confidence_interval_95")).get("lower")
                    if least_confident
                    else None
                ),
                expected=confidence_contract.get("worst_slice_success"),
                direction="floor",
            ),
        ]
        if release
        else []
    )
    acceptance_passed = all(row["status"] == "passed" for row in acceptance_checks)
    confidence_passed = all(row["status"] == "passed" for row in confidence_checks)
    passed = (
        complete
        and not failing_release_slices
        and acceptance_passed
        and confidence_passed
    )
    return {
        "version": STATISTICS_VERSION,
        "status": (
            "passed" if release and passed
            else "failed" if release
            else "complete" if complete
            else "incomplete"
        ),
        "passed": passed if release else complete,
        "selected_case_count": len(cases),
        "sample_count": sample_count,
        "passed_count": passed_count,
        "failed_count": sample_count - passed_count,
        "point_estimate": _rate(passed_count, sample_count),
        "confidence_interval_95": _interval_payload(lower, upper),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "release_required_slices": release_contract,
        "release_minimum_samples": release_minimum_samples,
        "release_contract_issues": release_contract_issues,
        "release_evidence_issues": list(dict.fromkeys(evidence_issues)),
        "release_coverage_issues": coverage_issues,
        "failing_release_slices": failing_release_slices,
        "worst_slice": worst or {},
        "least_confident_slice": least_confident or {},
        "acceptance_passed": acceptance_passed if release else None,
        "acceptance_checks": acceptance_checks,
        "confidence_passed": confidence_passed if release else None,
        "confidence_contract": confidence_contract,
        "confidence_checks": confidence_checks,
        "slices": slices,
    }


def release_slice_contract() -> dict[str, tuple[str, ...]]:
    """Return every published release slice that needs observed coverage."""

    return {
        "complexity_band": tuple(SUPPORTED_COMPLEXITY_BANDS),
        "evidence_format": tuple(SUPPORTED_PUBLIC_INPUT_FORMATS),
        "model_profile": supported_greenfield_model_profile_ids(),
    }


def release_slice_minimum_sample_contract() -> dict[str, dict[str, int]]:
    """Return the frozen evidence count required for every release slice.

    Four is the smallest perfect binomial sample whose 95% Wilson lower bound
    exceeds one half; smaller slices cannot support even a majority claim.
    """

    return {
        dimension: {
            value: _MINIMUM_RELEASE_SLICE_SAMPLES
            for value in values
        }
        for dimension, values in release_slice_contract().items()
    }


def release_slice_minimum_sample_contract_issues(value: Any) -> list[str]:
    """Reject absent, narrowed, or operator-softened release sample minima."""

    if not isinstance(value, Mapping):
        return ["release slice minimum samples must match the published contract"]
    normalized: dict[str, dict[str, int]] = {}
    for dimension, required_values in release_slice_contract().items():
        rows = value.get(dimension)
        if not isinstance(rows, Mapping):
            normalized[dimension] = {}
            continue
        normalized[dimension] = {
            str(slice_value): int(sample_count)
            for slice_value, sample_count in rows.items()
            if (
                str(slice_value).strip()
                and isinstance(sample_count, int)
                and not isinstance(sample_count, bool)
                and sample_count > 0
            )
        }
        if set(rows) != set(required_values):
            continue
    if (
        set(value) != set(RELEASE_SLICE_DIMENSIONS)
        or normalized != release_slice_minimum_sample_contract()
    ):
        return ["release slice minimum samples must match the published contract"]
    return []


def release_statistical_confidence_contract() -> dict[str, Any]:
    """Return confidence gates that are achievable at frozen release minima.

    A perfect four-observation sample has a 95% Wilson lower bound of
    0.510109, while a zero-failure sample has an upper bound of 0.489891.
    The uniform 0.5 confidence gate is therefore the strongest simple
    threshold supported by the published minimum. Product acceptance remains
    separately fixed at exact 1.0 success and 0.0 unnecessary questions.
    """

    return {
        "version": STATISTICAL_CONFIDENCE_VERSION,
        "method": "wilson",
        "confidence_level": 0.95,
        "atomic_semantic_fidelity": 0.5,
        "relation_fidelity": 0.5,
        "clarification_identity": 0.5,
        "unnecessary_question_rate_ceiling": 0.5,
        "overall_case_success": 0.5,
        "worst_slice_success": 0.5,
    }


def release_statistical_confidence_contract_issues(
    value: Any,
    *,
    minimum_samples: Mapping[str, Mapping[str, int]] | None = None,
) -> list[str]:
    """Validate confidence schema and feasibility at declared sample minima."""

    expected_keys = {
        "version",
        "method",
        "confidence_level",
        *_CONFIDENCE_THRESHOLD_KEYS,
    }
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        return ["statistical confidence must use only the v1 confidence fields"]
    issues: list[str] = []
    if value.get("version") != STATISTICAL_CONFIDENCE_VERSION:
        issues.append(
            f"statistical confidence must declare {STATISTICAL_CONFIDENCE_VERSION}"
        )
    if value.get("method") != "wilson" or value.get("confidence_level") != 0.95:
        issues.append("statistical confidence must use the 95% Wilson interval")
    for name in sorted(_CONFIDENCE_THRESHOLD_KEYS):
        threshold = value.get(name)
        if (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not 0.0 <= float(threshold) <= 1.0
        ):
            issues.append(
                f"statistical confidence `{name}` must be a number from 0 through 1"
            )
    if issues:
        return issues
    sample_contract = (
        minimum_samples
        if minimum_samples is not None
        else release_slice_minimum_sample_contract()
    )
    minimum = release_statistical_confidence_sample_minimum(sample_contract)
    if minimum <= 0:
        return ["statistical confidence has no positive declared sample minimum"]
    perfect_lower, _perfect_upper = wilson_interval(minimum, minimum)
    _zero_lower, zero_upper = wilson_interval(0, minimum)
    for name in sorted(_CONFIDENCE_THRESHOLD_KEYS - {"unnecessary_question_rate_ceiling"}):
        if float(value[name]) > perfect_lower:
            issues.append(
                f"statistical confidence `{name}` cannot reach {float(value[name]):.6f} "
                f"at the declared minimum of {minimum}; perfect evidence reaches {perfect_lower:.6f}"
            )
    ceiling = float(value["unnecessary_question_rate_ceiling"])
    if ceiling < zero_upper:
        issues.append(
            "statistical confidence `unnecessary_question_rate_ceiling` cannot reach "
            f"{ceiling:.6f} at the declared minimum of {minimum}; "
            f"zero failures reach {zero_upper:.6f}"
        )
    return issues


def release_statistical_confidence_sample_minimum(
    minimum_samples: Mapping[str, Mapping[str, int]] | None = None,
) -> int:
    """Return the smallest positive denominator promised by release preflight."""

    sample_contract = (
        minimum_samples
        if minimum_samples is not None
        else release_slice_minimum_sample_contract()
    )
    declared_minima = [
        int(sample_count)
        for rows in sample_contract.values()
        if isinstance(rows, Mapping)
        for sample_count in rows.values()
        if isinstance(sample_count, int)
        and not isinstance(sample_count, bool)
        and sample_count > 0
    ]
    return min(declared_minima, default=0)


def expected_case_evidence_format(case: Any) -> str:
    """Return the public format actually sent through Greenfield authoring."""

    return (
        "operator_prompt_with_edit_evidence"
        if str(getattr(case, "confirmed_intent_markdown", "") or "").strip()
        else "operator_prompt"
    )


def expected_case_source_complexity(case: Any) -> dict[str, int]:
    """Return source dimensions independently knowable from frozen case bytes."""

    edit_evidence = str(getattr(case, "confirmed_intent_markdown", "") or "").strip()
    evidence_source = combined_prompt_evidence_source(
        prompt=str(getattr(case, "prompt", "") or ""),
        edit_evidence=edit_evidence,
    )
    return {
        "evidence_bytes": len(evidence_source.encode("utf-8")),
        "documents": 2 if edit_evidence else 1,
    }


def release_slice_evidence(
    *,
    case: Any,
    result: GreenfieldMatrixResult,
    annotated_complexity: Mapping[str, Any] | None = None,
    allow_unsealed_clarification: bool = False,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return support slices from sealed evidence, never from mutable case tags."""

    issues: list[str] = []
    evidence = _mapping(result.evidence)
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    snapshot = _mapping(receipt.get("semantic_snapshot"))
    envelope = _mapping(snapshot.get("operating_envelope"))
    expected_format = expected_case_evidence_format(case)
    annotated = dict(annotated_complexity) if isinstance(annotated_complexity, Mapping) else {}
    source_dimensions = expected_case_source_complexity(case)
    for dimension, expected in source_dimensions.items():
        if annotated and annotated.get(dimension) != expected:
            issues.append(f"annotated complexity `{dimension}` does not match frozen source evidence")

    sealed_profile = ""
    if envelope:
        try:
            require_supported_greenfield_operating_envelope(envelope)
        except ValueError:
            issues.append("has an invalid sealed operating-envelope receipt")
        complexity = _mapping(envelope.get("complexity"))
        dimensions = _mapping(complexity.get("dimensions"))
        if annotated and dimensions != annotated:
            issues.append("annotated complexity does not match the sealed operating-envelope dimensions")
        complexity_band = str(complexity.get("band") or "").strip()
        evidence_format = str(envelope.get("evidence_format") or "").strip()
        observed_model = _mapping(_mapping(envelope.get("model_contract")).get("observed"))
        sealed_profile = str(observed_model.get("profile_id") or "").strip()
    elif allow_unsealed_clarification and annotated:
        complexity_band = greenfield_complexity_band(annotated)
        evidence_format = expected_format
    else:
        complexity_band = ""
        evidence_format = ""
        issues.append("lacks a sealed operating-envelope receipt")

    if evidence_format != expected_format:
        issues.append("sealed evidence format does not match the frozen case input")
    model_evidence = _mapping(evidence.get("model_profile"))
    observed_profile = str(model_evidence.get("profile_id") or "").strip()
    if not observed_profile:
        issues.append("lacks an observed model profile")
    elif observed_profile not in supported_greenfield_model_profile_ids():
        issues.append("claims an unknown model profile")
    if sealed_profile and sealed_profile != observed_profile:
        issues.append("observed model profile does not match the sealed operating envelope")
    if not sealed_profile and observed_profile:
        observed = _mapping(model_evidence.get("observed"))
        try:
            require_greenfield_model_profile_observation(
                profile_id=observed_profile,
                provider=str(observed.get("provider") or ""),
                model=str(observed.get("model") or ""),
                reasoning_effort=str(observed.get("reasoning_effort") or ""),
                effective_timeout_seconds=observed.get("effective_timeout_seconds"),
            )
        except ValueError:
            issues.append("has invalid unsealed model-profile observation evidence")
        if model_evidence.get("status") != "passed" or model_evidence.get("issues") != []:
            issues.append("has unproven model-profile result evidence")

    slices = {
        "complexity_band": complexity_band,
        "evidence_format": evidence_format,
        "model_profile": sealed_profile or observed_profile,
    }
    for dimension, value in slices.items():
        if not value:
            issues.append(f"lacks release slice `{dimension}`")
    return slices, tuple(dict.fromkeys(issues))


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


def threshold_check(
    name: str,
    *,
    observed: Any,
    expected: Any,
    direction: str,
) -> dict[str, Any]:
    """Return one fail-closed numeric floor or ceiling decision."""

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


def _normalized_slice_contract(
    value: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    contract: dict[str, tuple[str, ...]] = {}
    for dimension in RELEASE_SLICE_DIMENSIONS:
        rows = value.get(dimension)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
            contract[dimension] = ()
            continue
        contract[dimension] = tuple(
            dict.fromkeys(str(item or "").strip() for item in rows if str(item or "").strip())
        )
    return contract


def _release_slice_contract_issues(
    *,
    supplied: Mapping[str, Sequence[str]],
    normalized: Mapping[str, Sequence[str]],
) -> list[str]:
    if set(supplied) != set(RELEASE_SLICE_DIMENSIONS):
        return ["release slice contract must declare only every published slice dimension"]
    if dict(normalized) != release_slice_contract():
        return ["release slice contract does not match the published operating envelope"]
    return []


def release_slice_coverage_issues(
    *,
    slices: Sequence[Mapping[str, Any]],
    required: Mapping[str, Sequence[str]],
    minimum_samples: Mapping[str, Mapping[str, int]] | None = None,
) -> list[str]:
    issues: list[str] = []
    observed: dict[str, set[str]] = defaultdict(set)
    sample_counts: dict[tuple[str, str], int] = {}
    for row in slices:
        dimension = str(row.get("dimension") or "")
        value = str(row.get("value") or "")
        if dimension in required and value:
            observed[dimension].add(value)
            sample_counts[(dimension, value)] = int(row.get("sample_count", 0) or 0)
    for dimension, required_values in required.items():
        required_set = set(required_values)
        dimension_minimums = _mapping(_mapping(minimum_samples).get(dimension))
        missing = sorted(required_set - observed[dimension])
        unknown = sorted(observed[dimension] - required_set)
        if missing:
            issues.append(f"release evidence lacks {dimension} coverage: " + ", ".join(missing))
        if unknown:
            issues.append(f"release evidence has unknown {dimension} slices: " + ", ".join(unknown))
        for value in sorted(required_set & observed[dimension]):
            minimum = int(dimension_minimums.get(value, 0) or 0)
            observed_count = sample_counts.get((dimension, value), 0)
            if minimum > 0 and observed_count < minimum:
                issues.append(
                    f"release evidence has {observed_count} sample(s) for {dimension} `{value}`; "
                    f"requires at least {minimum}"
                )
    return issues


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
    case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
    return str(case.get("id") or "").strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


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


__all__ = [
    "RELEASE_SLICE_DIMENSIONS",
    "STATISTICS_VERSION",
    "STATISTICAL_CONFIDENCE_VERSION",
    "expected_case_evidence_format",
    "expected_case_source_complexity",
    "outcome_statistics",
    "release_slice_contract",
    "release_slice_coverage_issues",
    "release_slice_evidence",
    "release_slice_minimum_sample_contract",
    "release_slice_minimum_sample_contract_issues",
    "release_statistical_confidence_contract",
    "release_statistical_confidence_contract_issues",
    "release_statistical_confidence_sample_minimum",
    "threshold_check",
    "wilson_interval",
]
