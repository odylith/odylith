"""Shared metric math for benchmark family summaries and comparisons."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


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
