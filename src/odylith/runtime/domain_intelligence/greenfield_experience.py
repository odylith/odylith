"""Operator-facing greenfield implementation handoff helpers.

This module owns the text and ID shaping that turns an accepted proposal into
the next coding move. Greenfield apply writes governance truth elsewhere; this
owner keeps the human handoff, component runways, and first-wave proof language
consistent across CLI output and candidate component specs.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_cover_article_language
from odylith.runtime.domain_intelligence.greenfield_text import strip_dangling_word_tail
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import CONFIRMED_DANGLING_WORDS

_HANDOFF_MATCH_STOPWORDS = frozenset(
    {
        "adapter",
        "build",
        "component",
        "first",
        "handoffs",
        "implement",
        "path",
        "proof",
        "review",
        "service",
        "state",
        "surface",
        "system",
    }
)
_PREVIEW_TERMINAL_MODIFIERS = frozenset(
    {
        "accepted",
        "actionable",
        "clear",
        "complete",
        "concrete",
        "first",
        "reviewable",
        "specific",
        "trusted",
        "visible",
    }
)
_PREVIEW_DANGLING_WORDS = frozenset((CONFIRMED_DANGLING_WORDS - {"final"}) | {"around", "from"})
_PREVIEW_TERMINAL_FINAL_STATE_WORDS = frozenset(
    {"case", "decision", "match", "record", "result", "review", "score", "status"}
)


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
    created = mapping_rows(backlog_result.get("created"))
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
            "Do not start source edits from this closeout; treat the applied records as the project review board.",
            f"Open the project program view for `{umbrella_id or start_id}` and review the project brief, direction choices, non-goals, diagrams, and proof gates.",
            f"Open the progress view and verify the active wave `{wave_label}` plus release `{release_selector or '0.0.1'}` match the accepted project shape.",
            "Answer or explicitly accept the choices that materially change runtime, data posture, architecture, validation, release ambition, or first user.",
            f"Only after the coding-readiness gates are accepted, open `{start_id}` and author the first technical plan before source writes.",
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
    created = mapping_rows(backlog_result.get("created"))
    by_id = _created_by_id(created)
    umbrella_id = _umbrella_id(program_result)
    first_release_ids = [str(item).strip().upper() for item in first_release_workstreams if str(item).strip()]
    handoffs: dict[str, dict[str, Any]] = {}
    components = mapping_rows(proposal.get("components"))
    project_context = _project_context(proposal)
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
        release_focused_ids = [item for item in focused_child_ids if item in first_release_ids]
        release_child_ids = [item for item in child_ids if item in first_release_ids]
        start_id = (
            release_focused_ids
            or focused_child_ids
            or release_child_ids
            or child_ids
            or [umbrella_id]
        )[0]
        proposal_row = _proposal_row_for_created_id(proposal=proposal, created=created, created_id=start_id)
        wave = _wave_for_workstream(program_result=program_result, workstream_id=start_id)
        title = str(by_id.get(start_id, {}).get("title", "")).strip()
        first_slice = _first_slice_text(proposal_row)
        first_slice = _component_local_first_slice(row, fallback=first_slice)
        handoffs[key] = {
            **project_context,
            "workstream_id": start_id,
            "workstream_title": title,
            "wave_id": str(wave.get("wave_id", "")).strip(),
            "wave_label": _wave_label(wave),
            "wave_status": str(wave.get("status", "")).strip(),
            "release_selector": release_selector,
            "first_slice": first_slice,
            "validation_gates": list(_validation_items(row=proposal_row, wave=wave)[:6]),
            "verification_commands": verification_commands(start_id),
        }
    return handoffs


def _project_context(proposal: Mapping[str, Any]) -> dict[str, str]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    project_brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    validation = proposal.get("validation_strategy") if isinstance(proposal.get("validation_strategy"), Mapping) else {}
    return {
        "project_title": str(intent.get("title", "") or "").strip(),
        "project_purpose": str(
            project_brief.get("purpose")
            or project_brief.get("summary")
            or project_brief.get("operator_value")
            or ""
        ).strip(),
        "project_outcome": str(
            project_brief.get("project_outcome")
            or validation.get("first_slice_proof")
            or ""
        ).strip(),
    }


def verification_commands(start_workstream_id: str) -> list[str]:
    start_id = str(start_workstream_id or "").strip() or "<first-workstream-id>"
    return [
        f"./.odylith/bin/odylith context --repo-root . {start_id}",
        "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
        "./.odylith/bin/odylith validate plan-traceability --repo-root .",
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
    rows = mapping_rows(proposal.get("backlog"))
    scored: list[tuple[int, int, str]] = []
    for index, row in enumerate(rows):
        if index >= len(created):
            break
        idea_id = str(created[index].get("idea_id", "")).strip().upper()
        if not idea_id or idea_id == umbrella_id:
            continue
        score = _component_focus_score(component_aliases=aliases, row=row)
        if score > 0:
            scored.append((score, -index, idea_id))
    return list(unique_text(idea_id for _score, _neg_index, idea_id in sorted(scored, reverse=True)))


def _component_focus_score(*, component_aliases: set[str], row: Mapping[str, Any]) -> int:
    focus_aliases = _focus_aliases(row)
    if not (component_aliases & focus_aliases):
        return 0
    score = 10
    if len(focus_aliases) == 1:
        score += 8
    haystack_aliases = _slug_aliases(
        [
            row.get("title"),
            row.get("problem"),
            row.get("product_view"),
            row.get("recommended_first_slice"),
        ]
    )
    if component_aliases & haystack_aliases:
        score += 4
    return score


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
    proposal_rows = mapping_rows(proposal.get("backlog"))
    target = str(created_id or "").strip().upper()
    for index, created_row in enumerate(created):
        idea_id = str(created_row.get("idea_id", "")).strip().upper()
        if idea_id == target and index < len(proposal_rows):
            return proposal_rows[index]
    return {}


def _first_wave(program_result: Mapping[str, Any]) -> Mapping[str, Any]:
    waves = mapping_rows(program_result.get("waves"))
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
    return _preview_safe_fragment(
        " ".join(row_text_tuple(row, "recommended_first_slice", "first_slice_proof")).strip()
        or "Implement the smallest source-backed slice for this workstream and prove it with the listed proof checks.",
        limit=420,
    )


def _component_local_first_slice(row: Mapping[str, Any], *, fallback: str) -> str:
    label = str(row.get("label", "") or row.get("component_id", "") or "component").strip()
    contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
    inputs = _short_contract_text(contract.get("accepted_inputs") if isinstance(contract, Mapping) else "")
    outputs = _short_contract_text(contract.get("produced_outputs") if isinstance(contract, Mapping) else "")
    proof = _short_contract_text(
        _first_contract_text(contract.get("local_proof")) if isinstance(contract, Mapping) else "",
        limit=260,
    )
    responsibility = _short_contract_text(row.get("responsibility") or row.get("boundary"))
    validation = _short_contract_text(_first_contract_text(row_text_tuple(row, "validation", "test_strategy")))
    if label and proof:
        return (
            f"Implement {label} local proof: {proof}. When {label} receives missing or invalid input, keep the "
            "result, explanation, and recovery path reviewable."
        )
    if label and inputs and outputs:
        return f"Implement {label} local contract: accept {inputs}, produce {outputs}, and block invalid or missing state."
    if label and responsibility and validation:
        return f"Implement {label} inside this boundary: {responsibility}. Prove it with {validation}."
    if label and validation:
        return f"Implement {label} so its local validation can show: {validation}."
    if label and responsibility:
        return f"Implement {label} inside this boundary: {responsibility}."
    return fallback


def _first_contract_text(value: Any) -> str:
    for item in text_values(value):
        text = " ".join(str(item or "").split()).strip(" .")
        if text:
            return text
    return ""


def _short_contract_text(value: Any, *, limit: int = 180) -> str:
    return clip_text_at_word_boundary(
        value,
        limit=limit,
        strip_edges=" .",
        dangling_words=_PREVIEW_DANGLING_WORDS,
    ).strip(" ,;:")


def _workstream_title_matches_component(title: str, row: Mapping[str, Any]) -> bool:
    title_terms = set(
        ordered_terms(
            title,
            minimum=4,
            stopwords=_HANDOFF_MATCH_STOPWORDS,
        )
    )
    label_terms = set(
        ordered_terms(
            str(row.get("label", "") or row.get("component_id", "")),
            minimum=4,
            stopwords=_HANDOFF_MATCH_STOPWORDS,
        )
    )
    if not title_terms or not label_terms:
        return False
    return len(title_terms & label_terms) >= min(2, len(label_terms))


def _validation_items(*, row: Mapping[str, Any], wave: Mapping[str, Any]) -> tuple[str, ...]:
    return unique_text(
        [
            cleaned
            for item in [
                *row_text_tuple(row, "validation", "test_strategy"),
                *row_text_tuple(row, "success_metrics"),
                *_wave_validation_items(wave),
            ]
            if (cleaned := _preview_safe_validation_item(item))
        ]
    )


def _preview_safe_validation_item(value: Any) -> str:
    return _preview_safe_fragment(normalize_cover_article_language(value), limit=220)


def _preview_safe_fragment(value: Any, *, limit: int) -> str:
    text = clip_text_at_word_boundary(
        value,
        limit=limit,
        strip_edges=" .",
        dangling_words=_PREVIEW_DANGLING_WORDS,
        rstrip_chars=" ,;:.",
    )
    return _trim_preview_terminal_fragment(text).strip(" ,;:")


def _trim_preview_terminal_fragment(value: str) -> str:
    text = str(value or "").strip(" ,;:.")
    words = text.split()
    if len(words) >= 2:
        previous = words[-2].casefold().strip(".,;:")
        tail = words[-1].casefold().strip(".,;:")
        if previous in {"a", "an", "one", "the", "this", "that"} and tail in _PREVIEW_TERMINAL_MODIFIERS:
            text = " ".join(words[:-2]).strip(" ,;:.")
        elif tail == "final" and not _preview_allows_terminal_final(words):
            text = " ".join(words[:-1]).strip(" ,;:.")
    return strip_dangling_word_tail(text, dangling_words=_PREVIEW_DANGLING_WORDS)


def _preview_allows_terminal_final(words: Sequence[str]) -> bool:
    lowered = [word.casefold().strip(".,;:'") for word in words if word.strip(".,;:'")]
    if len(lowered) < 2 or lowered[-1] != "final":
        return False
    previous = lowered[-2]
    if previous in _PREVIEW_TERMINAL_FINAL_STATE_WORDS:
        return True
    if previous in {"is", "becomes", "became"} and any(
        token in _PREVIEW_TERMINAL_FINAL_STATE_WORDS for token in lowered[:-2]
    ):
        return True
    return any(
        token in {"finalize", "finalizes", "finalized", "finalizing", "mark", "marked", "marks"}
        for token in lowered[:-1]
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
    return result[:8]


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
            "After the project-first scope is accepted, select the first targeted child workstream, write a technical "
            "plan, implement the smallest source-backed slice, then run its listed proof checks."
        )
    title_text = title or "the first targeted workstream"
    first_slice_text = str(first_slice or "").strip()
    if first_slice_text and first_slice_text[-1] not in ".!?":
        first_slice_text = f"{first_slice_text}."
    scope_sentence = f"{first_slice_text} " if first_slice_text else ""
    return (
        f"After project-first scope is accepted, start {start_id}: {scope_sentence}Treat `{title_text}` as the first "
        "coding scope and do not advance waves until success, blocked-input, replay, and handoff evidence is written and reviewed."
    )
