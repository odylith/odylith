"""Operator-facing greenfield implementation handoff helpers.

This module owns the text and ID shaping that turns an accepted proposal into
the next coding move. Greenfield apply writes governance truth elsewhere; this
owner keeps the human handoff, component runways, and first-wave proof language
consistent across CLI output and Registry candidate specs.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence import greenfield_traceability


def text_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested in value.values():
            values.extend(text_values(nested))
        return unique_text(values)
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(text_values(item))
        return unique_text(values)
    token = " ".join(str(value or "").split()).strip()
    return (token,) if token else ()


def unique_text(values: Sequence[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        token = " ".join(str(value or "").split()).strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(token)
    return tuple(result)


def row_text_tuple(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        values = text_values(row.get(key))
        if values:
            return values
    return ()


def proposal_posture_tuple(proposal: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    rows: list[str] = []
    for key in keys:
        rows.extend(text_values(proposal.get(key)))
    return unique_text(rows)


def build_next_steps(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    first_release_workstreams: Sequence[str],
    program_result: Mapping[str, Any],
    release_selector: str,
) -> dict[str, Any]:
    created = _created_rows(backlog_result)
    by_id = _created_by_id(created)
    umbrella_id = _umbrella_id(program_result)
    candidate_ids = _candidate_start_ids(
        first_release_workstreams=first_release_workstreams,
        program_result=program_result,
        umbrella_id=umbrella_id,
    )
    start_id = candidate_ids[0] if candidate_ids else (umbrella_id or (next(iter(by_id), "")))
    start_row = by_id.get(start_id, {})
    active_wave = _active_wave(program_result)
    wave_label = _wave_label(active_wave)
    proposal_row = _proposal_row_for_created_id(proposal=proposal, created=created, created_id=start_id)
    validation_items = _validation_items(row=proposal_row, wave=active_wave)
    first_slice = _first_slice_text(proposal_row)
    title = str(start_row.get("title", "")).strip()
    return {
        "start_workstream_id": start_id,
        "start_workstream_title": title,
        "first_wave": wave_label,
        "release_selector": release_selector,
        "implementation_prompt": _implementation_prompt(start_id=start_id, title=title, first_slice=first_slice),
        "validation_gates": list(validation_items[:6]),
        "operator_sequence": [
            f"Open Compass and start the active wave `{wave_label}`.",
            f"Open Radar plan view for `{start_id}` and turn the recommended first slice into the first implementation task.",
            "Write the source slice, then run the repo-native tests named by the workstream validation gates.",
            "Refresh Odylith surfaces and verify Compass/Radar/Registry/Atlas still agree before moving to the next wave.",
        ],
        "verification_commands": verification_commands(start_id),
    }


def build_component_handoffs(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    first_release_workstreams: Sequence[str],
    program_result: Mapping[str, Any],
    traceability_plan: greenfield_traceability.GreenfieldTraceabilityPlan,
    release_selector: str,
) -> dict[str, dict[str, Any]]:
    created = _created_rows(backlog_result)
    by_id = _created_by_id(created)
    umbrella_id = _umbrella_id(program_result)
    first_release_ids = [str(item).strip().upper() for item in first_release_workstreams if str(item).strip()]
    handoffs: dict[str, dict[str, Any]] = {}
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    for row in components:
        key = greenfield_traceability.component_key(row)
        component_workstreams = [
            str(item).strip().upper()
            for item in traceability_plan.component_workstreams.get(key, ())
            if str(item).strip()
        ]
        child_ids = [item for item in component_workstreams if item != umbrella_id]
        preferred_ids = [item for item in first_release_ids if item in child_ids]
        start_id = (preferred_ids or child_ids or [item for item in first_release_ids if item != umbrella_id] or [umbrella_id])[
            0
        ]
        proposal_row = _proposal_row_for_created_id(proposal=proposal, created=created, created_id=start_id)
        wave = _wave_for_workstream(program_result=program_result, workstream_id=start_id)
        title = str(by_id.get(start_id, {}).get("title", "")).strip()
        handoffs[key] = {
            "workstream_id": start_id,
            "workstream_title": title,
            "wave_id": str(wave.get("wave_id", "")).strip(),
            "wave_label": _wave_label(wave),
            "wave_status": str(wave.get("status", "")).strip(),
            "release_selector": release_selector,
            "first_slice": _first_slice_text(proposal_row),
            "validation_gates": list(_validation_items(row=proposal_row, wave=wave)[:6]),
            "verification_commands": verification_commands(start_id),
        }
    return handoffs


def verification_commands(start_workstream_id: str) -> list[str]:
    start_id = str(start_workstream_id or "").strip() or "<first-workstream-id>"
    return [
        f"./.odylith/bin/odylith context --repo-root . {start_id}",
        "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
        "./.odylith/bin/odylith validate plan-traceability --repo-root .",
        "run the repo-native test, lint, typecheck, build, and browser proof named by the first technical plan",
        "./.odylith/bin/odylith sync --repo-root . --impact-mode selective",
    ]


def _created_rows(backlog_result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [row for row in backlog_result.get("created", []) if isinstance(row, Mapping)]


def _created_by_id(created: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("idea_id", "")).strip().upper(): row
        for row in created
        if str(row.get("idea_id", "")).strip()
    }


def _umbrella_id(program_result: Mapping[str, Any]) -> str:
    return str(program_result.get("umbrella_id", "")).strip().upper() if isinstance(program_result, Mapping) else ""


def _candidate_start_ids(
    *,
    first_release_workstreams: Sequence[str],
    program_result: Mapping[str, Any],
    umbrella_id: str,
) -> list[str]:
    candidate_ids = [
        str(item).strip().upper()
        for item in first_release_workstreams
        if str(item).strip().upper() and str(item).strip().upper() != umbrella_id
    ]
    if candidate_ids or not isinstance(program_result, Mapping):
        return candidate_ids
    first_wave = _first_wave(program_result)
    for field in ("primary_workstreams", "carried_workstreams", "in_band_workstreams"):
        for item in first_wave.get(field, []) if isinstance(first_wave.get(field), list) else []:
            token = str(item).strip().upper()
            if token and token != umbrella_id and token not in candidate_ids:
                candidate_ids.append(token)
    return candidate_ids


def _proposal_row_for_created_id(
    *,
    proposal: Mapping[str, Any],
    created: Sequence[Mapping[str, Any]],
    created_id: str,
) -> Mapping[str, Any]:
    proposal_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    target = str(created_id or "").strip().upper()
    for index, created_row in enumerate(created):
        idea_id = str(created_row.get("idea_id", "")).strip().upper()
        if idea_id == target and index < len(proposal_rows):
            return proposal_rows[index]
    return {}


def _first_wave(program_result: Mapping[str, Any]) -> Mapping[str, Any]:
    waves = [row for row in program_result.get("waves", []) if isinstance(row, Mapping)]
    return waves[0] if waves else {}


def _active_wave(program_result: Mapping[str, Any]) -> Mapping[str, Any]:
    waves = [row for row in program_result.get("waves", []) if isinstance(row, Mapping)] if isinstance(program_result, Mapping) else []
    return next((row for row in waves if str(row.get("status", "")).strip().casefold() == "active"), waves[0] if waves else {})


def _wave_for_workstream(*, program_result: Mapping[str, Any], workstream_id: str) -> Mapping[str, Any]:
    token = str(workstream_id or "").strip().upper()
    waves = [row for row in program_result.get("waves", []) if isinstance(row, Mapping)] if isinstance(program_result, Mapping) else []
    for wave in waves:
        for field in ("primary_workstreams", "carried_workstreams", "in_band_workstreams"):
            values = wave.get(field, []) if isinstance(wave.get(field), list) else []
            if token in {str(item).strip().upper() for item in values}:
                return wave
    return _active_wave(program_result)


def _wave_label(wave: Mapping[str, Any]) -> str:
    return (
        str(wave.get("label", "")).strip()
        or str(wave.get("name", "")).strip()
        or str(wave.get("wave_id", "")).strip()
        or "first wave"
    )


def _first_slice_text(row: Mapping[str, Any]) -> str:
    return (
        " ".join(row_text_tuple(row, "recommended_first_slice", "first_slice_proof")).strip()
        or "Implement the smallest source-backed slice for this workstream and prove it with the listed validation gates."
    )


def _validation_items(*, row: Mapping[str, Any], wave: Mapping[str, Any]) -> tuple[str, ...]:
    return unique_text(
        [
            *row_text_tuple(row, "validation", "test_strategy"),
            *row_text_tuple(row, "success_metrics"),
            *text_values(wave.get("exit_gate")),
            *text_values(wave.get("validation_gate")),
            *text_values(wave.get("validation")),
        ]
    )


def _implementation_prompt(*, start_id: str, title: str, first_slice: str) -> str:
    if not start_id:
        return (
            "Select the first targeted child workstream, write a technical plan, implement the smallest "
            "source-backed slice, then run its listed validation gates."
        )
    title_text = title or "the first targeted workstream"
    return f"Start {start_id}: {first_slice} Treat `{title_text}` as the first coding scope and do not advance waves until its validation gates pass."
