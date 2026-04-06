"""Shared execution-wave UI projection helpers.

This module turns canonical traceability execution-wave data into a compact
view model that Radar and Compass can share without re-deriving portfolio
postures independently.

Invariants:
- source of truth stays the traceability graph and its embedded execution programs;
- non-wave workstreams produce empty-but-valid view payloads;
- wave ordering is deterministic by `W<n>` sequence;
- per-workstream contexts preserve cross-wave roles instead of collapsing them to
  a single scalar badge.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

_WAVE_ID_RE = re.compile(r"^W([1-9]\d*)$")
_ROLE_LABELS = {
    "primary": "Primary",
    "carried": "Carried",
    "in_band": "In Band",
}
_ROLE_ORDER = {
    "primary": 0,
    "carried": 1,
    "in_band": 2,
}
_STATUS_LABELS = {
    "active": "Active",
    "planned": "Planned",
    "blocked": "Blocked",
    "complete": "Complete",
}


def _join_with_and(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    suffix = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {suffix}"


def _wave_sort_key(value: str) -> tuple[int, str]:
    token = str(value or "").strip()
    match = _WAVE_ID_RE.fullmatch(token)
    if match is None:
        return (10_000, token)
    return (int(match.group(1)), token)


def _normalize_id_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _normalize_gate_refs(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    rows: list[dict[str, str]] = []
    for raw in values:
        if not isinstance(raw, Mapping):
            continue
        rows.append(
            {
                "workstream_id": str(raw.get("workstream_id", "")).strip(),
                "plan_path": str(raw.get("plan_path", "")).strip(),
                "label": str(raw.get("label", "")).strip(),
            }
        )
    return rows


def _workstream_lookup(traceability_graph: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    rows = traceability_graph.get("workstreams", [])
    lookup: dict[str, dict[str, str]] = {}
    if not isinstance(rows, list):
        return lookup
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        idea_id = str(raw.get("idea_id", "")).strip()
        if not idea_id:
            continue
        lookup[idea_id] = {
            "idea_id": idea_id,
            "title": str(raw.get("title", "")).strip() or idea_id,
            "status": str(raw.get("status", "")).strip(),
        }
    return lookup


def _status_label(status: str) -> str:
    token = str(status or "").strip().lower()
    return _STATUS_LABELS.get(token, token.title() or "Unknown")


def _role_label(role: str) -> str:
    token = str(role or "").strip().lower()
    return _ROLE_LABELS.get(token, token.replace("_", " ").title() or "Member")


def _status_tone(status: str) -> str:
    token = str(status or "").strip().lower()
    if token in {"active", "planned", "blocked", "complete"}:
        return f"wave-{token}"
    return "wave-other"


def _completion_label(
    complete_waves: list[Mapping[str, Any]],
    *,
    wave_count: int,
) -> str:
    if not complete_waves:
        return ""
    if wave_count > 0 and len(complete_waves) >= wave_count:
        return "All waves complete"
    if len(complete_waves) == 1:
        wave = complete_waves[0]
        wave_label = str(wave.get("label", "")).strip() or str(wave.get("wave_id", "")).strip()
        return f"{wave_label} complete" if wave_label else "Wave complete"
    return f"{len(complete_waves)} waves complete"


def _member_rows(
    *,
    workstream_lookup: Mapping[str, Mapping[str, str]],
    values: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for workstream_id in values:
        meta = workstream_lookup.get(workstream_id, {})
        rows.append(
            {
                "idea_id": workstream_id,
                "title": str(meta.get("title", "")).strip() or workstream_id,
                "status": str(meta.get("status", "")).strip(),
            }
        )
    return rows


def _member_mix_parts(*, primary_count: int, carried_count: int, in_band_count: int) -> list[str]:
    parts: list[str] = []
    if primary_count:
        parts.append(f"{primary_count} primary")
    if carried_count:
        parts.append(f"{carried_count} carried")
    if in_band_count:
        parts.append(f"{in_band_count} in band")
    return parts


def _depends_on_summary(depends_on_labels: list[str]) -> str:
    if not depends_on_labels:
        return "Starts here"
    return f"After {_join_with_and(depends_on_labels)}"


def _gate_preview_labels(gate_rows: list[Mapping[str, str]], *, limit: int = 2) -> list[str]:
    labels = [str(row.get("label", "")).strip() for row in gate_rows if str(row.get("label", "")).strip()]
    if len(labels) <= limit:
        return labels
    return [*labels[:limit], f"+{len(labels) - limit} more"]


def _default_open_wave_id(waves: list[Mapping[str, Any]]) -> str:
    current_wave_id = _current_wave_id(waves)
    if current_wave_id:
        return current_wave_id
    for status in ("active", "planned", "blocked", "complete"):
        for wave in waves:
            if str(wave.get("status", "")).strip() == status:
                return str(wave.get("wave_id", "")).strip()
    if waves:
        return str(waves[0].get("wave_id", "")).strip()
    return ""


def _current_wave_id(waves: list[Mapping[str, Any]]) -> str:
    active_waves = [
        wave
        for wave in waves
        if str(wave.get("status", "")).strip() == "active"
    ]
    if not active_waves:
        return ""
    lead_wave = max(
        active_waves,
        key=lambda row: (
            int(row.get("sequence", 0) or 0),
            _wave_sort_key(str(row.get("wave_id", ""))),
        ),
    )
    return str(lead_wave.get("wave_id", "")).strip()


def _compact_wave_span_label(refs: list[Mapping[str, Any]]) -> str:
    if not refs:
        return ""
    sorted_refs = sorted(refs, key=lambda row: (int(row.get("sequence", 10_000)), str(row.get("wave_id", ""))))
    unique_wave_ids: list[str] = []
    seen: set[str] = set()
    for row in sorted_refs:
        wave_id = str(row.get("wave_id", "")).strip()
        if not wave_id or wave_id in seen:
            continue
        seen.add(wave_id)
        unique_wave_ids.append(wave_id)
    if not unique_wave_ids:
        return ""
    if len(unique_wave_ids) == 1:
        return unique_wave_ids[0]
    numeric_ids: list[int] = []
    for wave_id in unique_wave_ids:
        match = _WAVE_ID_RE.fullmatch(wave_id)
        if match is None:
            return ", ".join(unique_wave_ids)
        numeric_ids.append(int(match.group(1)))
    first = numeric_ids[0]
    if numeric_ids == list(range(first, first + len(numeric_ids))):
        return f"{unique_wave_ids[0]}-{unique_wave_ids[-1]}"
    return ", ".join(unique_wave_ids)


def _role_summary_label(refs: list[Mapping[str, Any]]) -> str:
    labels: list[str] = []
    seen: set[str] = set()
    for row in sorted(refs, key=lambda item: (int(item.get("sequence", 10_000)), _ROLE_ORDER.get(str(item.get("role", "")).strip(), 99))):
        label = _role_label(str(row.get("role", "")).strip())
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return " -> ".join(labels)


def build_execution_wave_view_payload(traceability_graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a reusable execution-wave UI payload derived from traceability JSON."""

    workstream_lookup = _workstream_lookup(traceability_graph)
    raw_programs = traceability_graph.get("execution_programs", [])
    if not isinstance(raw_programs, list):
        raw_programs = []

    programs: list[dict[str, Any]] = []
    workstream_refs: dict[str, list[dict[str, Any]]] = {}

    for raw_program in raw_programs:
        if not isinstance(raw_program, Mapping):
            continue
        umbrella_id = str(raw_program.get("umbrella_id", "")).strip()
        if not umbrella_id:
            continue
        umbrella_meta = workstream_lookup.get(umbrella_id, {})
        raw_waves = raw_program.get("waves", [])
        if not isinstance(raw_waves, list):
            raw_waves = []
        sorted_raw_waves = sorted(
            [wave for wave in raw_waves if isinstance(wave, Mapping)],
            key=lambda row: _wave_sort_key(str(row.get("wave_id", ""))),
        )
        wave_label_lookup = {
            str(row.get("wave_id", "")).strip(): str(row.get("label", "")).strip() or str(row.get("wave_id", "")).strip()
            for row in sorted_raw_waves
            if str(row.get("wave_id", "")).strip()
        }

        wave_rows: list[dict[str, Any]] = []
        for index, raw_wave in enumerate(sorted_raw_waves, start=1):
            wave_id = str(raw_wave.get("wave_id", "")).strip()
            label = str(raw_wave.get("label", "")).strip() or wave_id
            status = str(raw_wave.get("status", "")).strip().lower()
            primary_ids = _normalize_id_list(raw_wave.get("primary_workstreams"))
            carried_ids = _normalize_id_list(raw_wave.get("carried_workstreams"))
            in_band_ids = _normalize_id_list(raw_wave.get("in_band_workstreams"))
            all_member_ids = _normalize_id_list([*primary_ids, *carried_ids, *in_band_ids])
            gate_refs = _normalize_gate_refs(raw_wave.get("gate_refs"))
            gate_rows: list[dict[str, str]] = []
            for gate in gate_refs:
                gate_workstream_id = str(gate.get("workstream_id", "")).strip()
                gate_meta = workstream_lookup.get(gate_workstream_id, {})
                gate_rows.append(
                    {
                        **gate,
                        "title": str(gate_meta.get("title", "")).strip() or gate_workstream_id,
                        "status": str(gate_meta.get("status", "")).strip(),
                    }
                )
            depends_on_ids = _normalize_id_list(raw_wave.get("depends_on"))
            depends_on_labels = [wave_label_lookup.get(token, token) for token in depends_on_ids]
            primary_count = len(primary_ids)
            carried_count = len(carried_ids)
            in_band_count = len(in_band_ids)
            gate_count = len(gate_rows)
            member_mix_parts = _member_mix_parts(
                primary_count=primary_count,
                carried_count=carried_count,
                in_band_count=in_band_count,
            )
            compact_summary_parts = [
                f"{index} of {len(sorted_raw_waves)}",
                _depends_on_summary(depends_on_labels),
                *member_mix_parts,
            ]
            if gate_count:
                compact_summary_parts.append(_pluralize(gate_count, "gate"))
            gate_preview_labels = _gate_preview_labels(gate_rows)

            wave_row = {
                "wave_id": wave_id,
                "label": label,
                "status": status,
                "status_label": _status_label(status),
                "status_tone": _status_tone(status),
                "summary": str(raw_wave.get("summary", "")).strip(),
                "sequence": index,
                "depends_on": depends_on_ids,
                "depends_on_labels": depends_on_labels,
                "depends_on_summary": _depends_on_summary(depends_on_labels),
                "member_count": len(all_member_ids),
                "primary_count": primary_count,
                "carried_count": carried_count,
                "in_band_count": in_band_count,
                "member_mix_parts": member_mix_parts,
                "member_mix_summary": " · ".join(member_mix_parts),
                "gate_count": gate_count,
                "gate_preview_labels": gate_preview_labels,
                "gate_preview_summary": "; ".join(gate_preview_labels),
                "compact_summary_parts": compact_summary_parts,
                "compact_summary_line": " · ".join(compact_summary_parts),
                "primary_workstreams": _member_rows(workstream_lookup=workstream_lookup, values=primary_ids),
                "carried_workstreams": _member_rows(workstream_lookup=workstream_lookup, values=carried_ids),
                "in_band_workstreams": _member_rows(workstream_lookup=workstream_lookup, values=in_band_ids),
                "all_workstreams": _member_rows(workstream_lookup=workstream_lookup, values=all_member_ids),
                "gate_refs": gate_rows,
            }
            wave_rows.append(wave_row)

        current_wave_id = _current_wave_id(wave_rows)
        default_open_wave_id = _default_open_wave_id(wave_rows)
        for wave_row in wave_rows:
            wave_row["is_active_wave"] = str(wave_row.get("status", "")).strip() == "active"
            wave_row["is_current_wave"] = str(wave_row.get("wave_id", "")).strip() == current_wave_id
            wave_row["is_active_tail_wave"] = bool(wave_row["is_active_wave"]) and not bool(wave_row["is_current_wave"])
            wave_row["default_open"] = str(wave_row.get("wave_id", "")).strip() == default_open_wave_id

        active_waves = [row for row in wave_rows if row["status"] == "active"]
        blocked_waves = [row for row in wave_rows if row["status"] == "blocked"]
        complete_waves = [row for row in wave_rows if row["status"] == "complete"]
        next_wave = next((row for row in wave_rows if row["status"] in {"planned", "blocked"}), None)
        current_wave = next(
            (
                row
                for row in wave_rows
                if str(row.get("wave_id", "")).strip() == current_wave_id
            ),
            None,
        )

        program_row = {
            "umbrella_id": umbrella_id,
            "umbrella_title": str(umbrella_meta.get("title", "")).strip() or umbrella_id,
            "umbrella_status": str(umbrella_meta.get("status", "")).strip(),
            "version": str(raw_program.get("version", "")).strip(),
            "source_file": str(raw_program.get("source_file", "")).strip(),
            "wave_count": len(wave_rows),
            "active_wave_count": len(active_waves),
            "blocked_wave_count": len(blocked_waves),
            "complete_wave_count": len(complete_waves),
            "active_waves": active_waves,
            "blocked_waves": blocked_waves,
            "complete_waves": complete_waves,
            "completion_label": _completion_label(complete_waves, wave_count=len(wave_rows)),
            "current_wave": current_wave,
            "next_wave": next_wave,
            "waves": wave_rows,
        }
        programs.append(program_row)

        for wave in wave_rows:
            for role_key, member_key in (
                ("primary", "primary_workstreams"),
                ("carried", "carried_workstreams"),
                ("in_band", "in_band_workstreams"),
            ):
                for member in wave[member_key]:
                    idea_id = str(member.get("idea_id", "")).strip()
                    if not idea_id:
                        continue
                    workstream_refs.setdefault(idea_id, []).append(
                        {
                            "umbrella_id": umbrella_id,
                            "umbrella_title": program_row["umbrella_title"],
                            "source_file": program_row["source_file"],
                            "wave_id": str(wave.get("wave_id", "")).strip(),
                            "wave_label": str(wave.get("label", "")).strip(),
                            "wave_status": str(wave.get("status", "")).strip(),
                            "wave_status_label": str(wave.get("status_label", "")).strip(),
                            "wave_status_tone": str(wave.get("status_tone", "")).strip(),
                            "sequence": int(wave.get("sequence", 0) or 0),
                            "role": role_key,
                            "role_label": _role_label(role_key),
                            "is_active_wave": str(wave.get("status", "")).strip() == "active",
                            "is_next_wave": (
                                next_wave is not None
                                and str(wave.get("wave_id", "")).strip() == str(next_wave.get("wave_id", "")).strip()
                            ),
                        }
                    )

    workstreams: dict[str, list[dict[str, Any]]] = {}
    for workstream_id, refs in sorted(workstream_refs.items()):
        umbrella_groups: dict[str, list[dict[str, Any]]] = {}
        for ref in refs:
            umbrella_groups.setdefault(str(ref.get("umbrella_id", "")).strip(), []).append(ref)
        contexts: list[dict[str, Any]] = []
        for umbrella_id, group_refs in sorted(umbrella_groups.items()):
            if not umbrella_id:
                continue
            group_refs_sorted = sorted(
                group_refs,
                key=lambda row: (int(row.get("sequence", 10_000)), _ROLE_ORDER.get(str(row.get("role", "")).strip(), 99)),
            )
            program_row = next((row for row in programs if str(row.get("umbrella_id", "")).strip() == umbrella_id), {})
            active_refs = [row for row in group_refs_sorted if bool(row.get("is_active_wave"))]
            next_refs = [row for row in group_refs_sorted if bool(row.get("is_next_wave"))]
            contexts.append(
                {
                    "umbrella_id": umbrella_id,
                    "umbrella_title": str(program_row.get("umbrella_title", "")).strip() or umbrella_id,
                    "source_file": str(program_row.get("source_file", "")).strip(),
                    "wave_count": len(group_refs_sorted),
                    "wave_span_label": _compact_wave_span_label(group_refs_sorted),
                    "role_label": _role_summary_label(group_refs_sorted),
                    "has_active_wave": len(active_refs) > 0,
                    "has_next_wave": len(next_refs) > 0,
                    "active_wave_labels": [str(row.get("wave_label", "")).strip() for row in active_refs],
                    "next_wave_labels": [str(row.get("wave_label", "")).strip() for row in next_refs],
                    "program_active_labels": [
                        str(row.get("label", "")).strip()
                        for row in (program_row.get("active_waves", []) if isinstance(program_row.get("active_waves"), list) else [])
                    ],
                    "program_next_label": (
                        str(program_row.get("next_wave", {}).get("label", "")).strip()
                        if isinstance(program_row.get("next_wave"), Mapping)
                        else ""
                    ),
                    "refs": group_refs_sorted,
                }
            )
        workstreams[workstream_id] = contexts

    return {
        "summary": {
            "program_count": len(programs),
            "wave_count": sum(int(row.get("wave_count", 0) or 0) for row in programs),
            "active_wave_count": sum(int(row.get("active_wave_count", 0) or 0) for row in programs),
            "blocked_wave_count": sum(int(row.get("blocked_wave_count", 0) or 0) for row in programs),
            "workstream_count": len(workstreams),
        },
        "programs": programs,
        "workstreams": workstreams,
    }
