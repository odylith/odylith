"""Helpers for grouped benchmark summaries and deltas."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def grouped_summaries(
    *,
    modes: Sequence[str],
    mode_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    group_field: str,
    row_kind: str = "",
    summarize: Callable[..., dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    normalized_kind = str(row_kind or "").strip()
    field_name = str(group_field or "").strip()
    if not field_name:
        return {}
    for mode in modes:
        for row in mode_rows.get(mode, []):
            if not isinstance(row, Mapping):
                continue
            if normalized_kind and str(row.get("kind", "")).strip() != normalized_kind:
                continue
            group_value = str(row.get(field_name, "")).strip()
            if not group_value:
                continue
            grouped.setdefault(group_value, {}).setdefault(str(mode).strip(), []).append(dict(row))
    summaries: dict[str, dict[str, dict[str, Any]]] = {}
    for group_value in sorted(grouped):
        mode_summary: dict[str, dict[str, Any]] = {}
        for mode in modes:
            rows = list(grouped[group_value].get(str(mode).strip(), []))
            if rows:
                mode_summary[str(mode).strip()] = summarize(mode=str(mode).strip(), scenario_rows=rows)
        if mode_summary:
            summaries[group_value] = mode_summary
    return summaries


def grouped_deltas(
    *,
    candidate_mode: str,
    baseline_mode: str,
    grouped_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]],
    compare: Callable[..., dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    deltas: dict[str, dict[str, Any]] = {}
    for group_value, summaries in grouped_summaries.items():
        if not isinstance(summaries, Mapping):
            continue
        deltas[str(group_value).strip()] = compare(
            candidate_mode=candidate_mode,
            baseline_mode=baseline_mode,
            mode_summaries=summaries,
        )
    return deltas


__all__ = ["grouped_deltas", "grouped_summaries"]
