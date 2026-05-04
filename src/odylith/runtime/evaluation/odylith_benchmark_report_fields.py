"""Small report-field aggregation helpers for benchmark report assembly."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def sorted_result_string_values(
    scenario_reports: Sequence[Mapping[str, Any]],
    field_name: str,
) -> list[str]:
    """Collect sorted string values from a scalar or list-valued result field."""
    values: set[str] = set()
    for scenario_report in scenario_reports:
        results = scenario_report.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, Mapping):
                continue
            rows = result.get(field_name, [])
            if rows in ("", [], {}, None):
                continue
            if isinstance(rows, list):
                values.update(str(token).strip() for token in rows if str(token).strip())
                continue
            value = str(rows).strip()
            if value:
                values.add(value)
    return sorted(values)


def sorted_mapping_string_values(payload: Mapping[str, Any], field_name: str) -> list[str]:
    """Collect sorted string values from a list-valued mapping field."""
    rows = payload.get(field_name, [])
    if not isinstance(rows, list):
        return []
    return sorted({str(token).strip() for token in rows if str(token).strip()})


def sorted_nested_result_string_values(
    scenario_reports: Sequence[Mapping[str, Any]],
    field_name: str,
    nested_field_name: str,
) -> list[str]:
    """Collect sorted string values from a mapping nested under each result."""
    values: set[str] = set()
    for scenario_report in scenario_reports:
        results = scenario_report.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, Mapping):
                continue
            nested = result.get(field_name, {})
            if not isinstance(nested, Mapping):
                continue
            value = str(nested.get(nested_field_name, "")).strip()
            if value:
                values.add(value)
    return sorted(values)
