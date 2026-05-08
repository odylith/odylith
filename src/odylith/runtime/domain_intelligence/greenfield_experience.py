"""Operator-facing greenfield implementation handoff helpers.

This module owns the text and ID shaping that turns an accepted proposal into
the next coding move. Greenfield apply writes governance truth elsewhere; this
owner keeps the human handoff, component runways, and first-wave proof language
consistent across CLI output and Registry candidate specs.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence import greenfield_traceability


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
    umbrella_row = by_id.get(umbrella_id, {})
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
    project_title = str(umbrella_row.get("title", "")).strip() or str(
        proposal.get("intent", {}).get("title", "the greenfield project")
        if isinstance(proposal.get("intent"), Mapping)
        else "the greenfield project"
    ).strip()
    project_brief = proposal.get("project_brief", {}) if isinstance(proposal.get("project_brief"), Mapping) else {}
    customization_options = _customization_options(project_brief)
    readiness_gates = _readiness_gates(project_brief)
    return {
        "project_workstream_id": umbrella_id,
        "project_workstream_title": project_title,
        "start_workstream_id": start_id,
        "start_workstream_title": title,
        "first_wave": wave_label,
        "release_selector": release_selector,
        "project_first_prompt": _project_first_prompt(
            project_id=umbrella_id,
            project_title=project_title,
            start_id=start_id,
            start_title=title,
        ),
        "implementation_prompt": _implementation_prompt(start_id=start_id, title=title, first_slice=first_slice),
        "customization_options": customization_options,
        "coding_readiness_gates": readiness_gates,
        "validation_gates": list(validation_items[:6]),
        "operator_sequence": [
            f"Open Compass and review the active wave `{wave_label}` plus release `{release_selector or '0.0.1'}`.",
            f"Open Radar program view for `{umbrella_id or start_id}` and review the project brief, decisions, non-goals, diagrams, and proof gates.",
            "Answer or explicitly accept the direction choices that materially change runtime, data posture, architecture, or validation.",
            f"Only after the coding-readiness gates are accepted, open `{start_id}` and author the first technical plan.",
            "Write source after that plan names paths, proof commands, degraded/error coverage, and refresh expectations.",
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
        focused_child_ids = _component_focused_child_ids(
            proposal=proposal,
            created=created,
            component_row=row,
            umbrella_id=umbrella_id,
        )
        component_workstreams = [
            str(item).strip().upper()
            for item in traceability_plan.component_workstreams.get(key, ())
            if str(item).strip()
        ]
        child_ids = [item for item in component_workstreams if item != umbrella_id]
        release_focused_ids = [item for item in first_release_ids if item in focused_child_ids]
        release_child_ids = [item for item in first_release_ids if item in child_ids]
        start_id = (
            release_focused_ids
            or focused_child_ids
            or release_child_ids
            or child_ids
            or [item for item in first_release_ids if item != umbrella_id]
            or [umbrella_id]
        )[0]
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


def _component_focused_child_ids(
    *,
    proposal: Mapping[str, Any],
    created: Sequence[Mapping[str, Any]],
    component_row: Mapping[str, Any],
    umbrella_id: str,
) -> list[str]:
    aliases = _component_aliases(component_row)
    if not aliases:
        return []
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    result: list[str] = []
    for index, row in enumerate(rows):
        if index >= len(created):
            break
        idea_id = str(created[index].get("idea_id", "")).strip().upper()
        if not idea_id or idea_id == umbrella_id:
            continue
        if aliases & _focus_aliases(row):
            result.append(idea_id)
    return list(unique_text(result))


def _component_aliases(row: Mapping[str, Any]) -> set[str]:
    return _slug_aliases([row.get("component_id"), row.get("id"), row.get("label"), row.get("name")])


def _focus_aliases(row: Mapping[str, Any]) -> set[str]:
    values: list[Any] = []
    for key in (
        "component_focus",
        "components",
        "component_ids",
        "related_components",
        "related_component_ids",
    ):
        values.extend(text_values(row.get(key)))
    return _slug_aliases(values)


def _slug_aliases(values: Sequence[Any]) -> set[str]:
    aliases: set[str] = set()
    for value in values:
        token = " ".join(str(value or "").split()).strip()
        if not token:
            continue
        slug = slugify(token)
        if slug:
            aliases.add(slug)
    return aliases


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
            *_wave_validation_items(wave),
        ]
    )


def _wave_validation_items(wave: Mapping[str, Any]) -> tuple[str, ...]:
    validation_items = text_values(wave.get("validation"))
    joined_validation = join_sentence_text(validation_items)
    items: list[str] = []
    for token in [*text_values(wave.get("exit_gate")), *text_values(wave.get("validation_gate"))]:
        if joined_validation and token.casefold() == joined_validation.casefold():
            continue
        items.append(token)
    items.extend(validation_items)
    return unique_text(items)


def _customization_options(project_brief: Mapping[str, Any]) -> list[str]:
    rows = project_brief.get("customization_options", []) if isinstance(project_brief, Mapping) else []
    result: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        decision = str(row.get("decision", "")).strip()
        recommended = str(row.get("recommended", "")).strip()
        if decision and recommended:
            result.append(f"{decision}: {recommended}")
    return result[:6]


def _readiness_gates(project_brief: Mapping[str, Any]) -> list[str]:
    gates = project_brief.get("coding_readiness_gates", []) if isinstance(project_brief, Mapping) else []
    return [str(item).strip() for item in gates if str(item).strip()] if isinstance(gates, list) else []


def _project_first_prompt(*, project_id: str, project_title: str, start_id: str, start_title: str) -> str:
    target = project_id or start_id or "<program-workstream-id>"
    next_lane = f"{start_id} {start_title}".strip() if start_id else "the first targeted child workstream"
    return (
        f"Deepen {target}: review `{project_title}`, choose or accept the project direction options, "
        f"confirm coding-readiness gates, then plan {next_lane} only after the project shape is accepted."
    )


def _implementation_prompt(*, start_id: str, title: str, first_slice: str) -> str:
    if not start_id:
        return (
            "After the project-first gates pass, select the first targeted child workstream, write a technical "
            "plan, implement the smallest source-backed slice, then run its listed validation gates."
        )
    title_text = title or "the first targeted workstream"
    return (
        f"After project-first gates pass, start {start_id}: {first_slice} Treat `{title_text}` as the first "
        "coding scope and do not advance waves until its validation gates pass."
    )
