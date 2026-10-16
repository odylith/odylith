"""Shared metric math for benchmark family summaries and comparisons."""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

RELEASE_QUALITY_FIELDS = {
    "required_path_recall_delta": "required_path_recall_rate",
    "validation_success_delta": "validation_success_rate",
    "critical_required_path_recall_delta": "critical_required_path_recall_rate",
    "critical_validation_success_delta": "critical_validation_success_rate",
    "hallucinated_surface_rate_delta": "hallucinated_surface_rate",
    "unnecessary_widening_rate_delta": "unnecessary_widening_rate",
}
_RELEASE_QUALITY_CONTRACT = "odylith_release_quality_summary.v1"
_RELEASE_IDENTITY_FIELDS = (
    "report_id", "product_version", "git_commit", "source_posture", "generated_utc",
    "selection_fingerprint", "corpus_fingerprint",
)
_FULL_PROOF_COMPARISON = "full_product_assistance_vs_raw_agent"


def benchmark_report_completed(report: Mapping[str, Any]) -> bool:
    """Recognize evaluated terminal observations, including completed quality failures."""
    acceptance = report.get("acceptance")
    if not isinstance(acceptance, Mapping) or acceptance.get("status") not in ("provisional_pass", "hold"):
        return False
    checks = acceptance.get("checks")
    if isinstance(checks, Mapping) and "benchmark_run_completed" in checks and checks["benchmark_run_completed"] is not True:
        return False
    if "status" in report and report["status"] not in ("provisional_pass", "hold"):
        return False
    required_modes = {"odylith_on", "raw_agent_baseline"}
    for field in ("mode_summaries", "published_mode_summaries"):
        summaries = report.get(field)
        if not isinstance(summaries, Mapping) or any(
            not isinstance(summaries.get(mode), Mapping) or not summaries[mode] for mode in required_modes
        ):
            return False
    observations = report.get("published_scenarios")
    count = report.get("scenario_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        return False
    if not isinstance(observations, list) or len(observations) != count:
        return False
    for observation in observations:
        results = observation.get("results") if isinstance(observation, Mapping) else None
        if not isinstance(results, list) or not required_modes.issubset(
            {str(row.get("mode", "")) for row in results if isinstance(row, Mapping)}
        ):
            return False
    return True


def _valid_rate(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0 and isfinite(value)


def release_quality_summary_fields(report: Mapping[str, Any], *, cache_profiles: Sequence[str]) -> dict[str, Any]:
    """Extract versioned release authority from a completed conservative full proof."""
    unavailable = {"absolute_odylith_on_quality": {}, "release_quality_evidence": {}}
    selection = report.get("selection")
    if (
        not benchmark_report_completed(report)
        or report.get("benchmark_profile") != "proof"
        or report.get("comparison_contract") != _FULL_PROOF_COMPARISON
        or report.get("latest_eligible") is not True
        or not isinstance(selection, Mapping)
        or selection.get("full_corpus_selected") is not True
        or report.get("cache_profiles") != list(cache_profiles)
        or report.get("published_cache_profiles") != list(cache_profiles)
        or report.get("published_view_strategy") != "conservative_multi_profile"
        or any(not isinstance(report.get(field), str) or not report[field].strip() for field in _RELEASE_IDENTITY_FIELDS)
    ):
        return unavailable
    on_summary = report["published_mode_summaries"]["odylith_on"]
    quality = {
        field: float(on_summary[field])
        for field in RELEASE_QUALITY_FIELDS.values()
        if _valid_rate(on_summary.get(field))
    }
    if set(quality) != set(RELEASE_QUALITY_FIELDS.values()):
        return unavailable
    metadata = {field: report[field] for field in _RELEASE_IDENTITY_FIELDS}
    metadata.update(
        benchmark_profile="proof",
        comparison_contract=_FULL_PROOF_COMPARISON,
        status=report["acceptance"]["status"],
        scenario_count=report["scenario_count"],
        evaluated_mode_count=len(report["mode_summaries"]),
        published_view_strategy="conservative_multi_profile",
        published_cache_profiles=list(cache_profiles),
    )
    return {
        **metadata,
        "absolute_odylith_on_quality": quality,
        "release_quality_evidence": {
            **metadata,
            "contract": _RELEASE_QUALITY_CONTRACT,
            "full_corpus_selected": True,
            "cache_profiles": list(cache_profiles),
            "published_scenario_count": len(report["published_scenarios"]),
            "absolute_odylith_on_quality": dict(quality),
        },
    }


def release_quality_measurements(summary: Mapping[str, Any], *, cache_profiles: Sequence[str]) -> dict[str, float]:
    """Validate persisted producer provenance without reconstructing legacy measurements."""
    evidence = summary.get("release_quality_evidence")
    if not isinstance(evidence, Mapping) or evidence.get("contract") != _RELEASE_QUALITY_CONTRACT:
        return {}
    count = evidence.get("scenario_count")
    evaluated = evidence.get("evaluated_mode_count")
    matching_fields = (
        *_RELEASE_IDENTITY_FIELDS, "benchmark_profile", "comparison_contract", "status",
        "scenario_count", "evaluated_mode_count", "published_view_strategy", "published_cache_profiles",
    )
    if (
        any(not isinstance(evidence.get(field), str) or not evidence[field].strip() for field in _RELEASE_IDENTITY_FIELDS)
        or any(
            type(summary.get(field)) is not type(evidence.get(field)) or summary.get(field) != evidence.get(field)
            for field in matching_fields
        )
        or evidence.get("benchmark_profile") != "proof"
        or evidence.get("comparison_contract") != _FULL_PROOF_COMPARISON
        or evidence.get("status") not in ("provisional_pass", "hold")
        or evidence.get("full_corpus_selected") is not True
        or evidence.get("cache_profiles") != list(cache_profiles)
        or evidence.get("published_cache_profiles") != list(cache_profiles)
        or evidence.get("published_view_strategy") != "conservative_multi_profile"
        or not isinstance(count, int) or isinstance(count, bool) or count <= 0
        or type(evidence.get("published_scenario_count")) is not int or evidence["published_scenario_count"] != count
        or not isinstance(evaluated, int) or isinstance(evaluated, bool) or evaluated < 2
    ):
        return {}
    quality = summary.get("absolute_odylith_on_quality")
    bound_quality = evidence.get("absolute_odylith_on_quality")
    fields = set(RELEASE_QUALITY_FIELDS.values())
    if (
        not isinstance(quality, Mapping) or not isinstance(bound_quality, Mapping)
        or set(quality) != fields or set(bound_quality) != fields
        or any(
            type(quality[field]) is not type(bound_quality[field])
            or quality[field] != bound_quality[field] or not _valid_rate(quality[field])
            for field in fields
        )
    ):
        return {}
    return {field: float(quality[field]) for field in RELEASE_QUALITY_FIELDS.values()}


def numeric_value(
    row: Mapping[str, Any],
    field_name: str,
    *,
    fallback_fields: Sequence[str] = (),
) -> float:
    """Return one numeric field from a mapping, trying fallbacks when needed."""
    for candidate_name in (field_name, *fallback_fields):
        try:
            value = row.get(candidate_name)
        except AttributeError:
            return 0.0
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def boolean_rate(values: Sequence[bool]) -> float:
    """Return a rounded true-rate for a sequence of boolean outcomes."""
    rows = [1.0 if bool(value) else 0.0 for value in values]
    if not rows:
        return 0.0
    return round(sum(rows) / len(rows), 3)


def numeric_delta(
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    candidate_field: str,
    baseline_field: str | None = None,
    candidate_fallback_fields: Sequence[str] = (),
    baseline_fallback_fields: Sequence[str] = (),
) -> float:
    """Return a rounded delta between numeric fields on candidate and baseline rows."""
    return round(
        numeric_value(
            candidate,
            candidate_field,
            fallback_fields=candidate_fallback_fields,
        )
        - numeric_value(
            baseline,
            baseline_field or candidate_field,
            fallback_fields=baseline_fallback_fields,
        ),
        3,
    )


def summary_delta(candidate: Mapping[str, Any], baseline: Mapping[str, Any], field_name: str) -> float:
    """Return the rounded candidate-minus-baseline delta for one summary field."""
    return numeric_delta(candidate, baseline, candidate_field=field_name)


def summary_deltas(
    *,
    candidate: Mapping[str, Any],
    baseline: Mapping[str, Any],
    field_map: Mapping[str, str],
) -> dict[str, float]:
    """Return named summary deltas from a delta-name to source-field mapping."""
    return {
        delta_name: summary_delta(candidate, baseline, field_name)
        for delta_name, field_name in field_map.items()
    }
