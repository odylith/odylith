"""Greenfield program and first-release targeting helpers."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.governance import authoring_execution_policy
from odylith.runtime.governance import execution_wave_contract
from odylith.runtime.governance import program_wave_authoring
from odylith.runtime.governance import program_wave_execution_engine

DEFAULT_GREENFIELD_RELEASE_SELECTOR = "0.0.1"

_IDEA_ID_RE = re.compile(r"^B-\d{3,}$", re.IGNORECASE)
_SEMVER_SELECTOR_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_RELEASE_TARGET_VERSION_RE = re.compile(r"\bv?(\d+(?:\.\d+){1,3})\b", re.IGNORECASE)
_MAX_RELEASE_TARGET_LABEL_CHARS = 18
_STOP_WORDS = {
    "and",
    "for",
    "from",
    "into",
    "that",
    "the",
    "this",
    "with",
    "without",
}


def release_target_version_token(value: str) -> str:
    """Return the numeric release token embedded in an operator release target."""

    match = _RELEASE_TARGET_VERSION_RE.search(" ".join(str(value or "").split()))
    return match.group(1) if match else ""


def compact_release_target_label(value: str, *, fallback: str = DEFAULT_GREENFIELD_RELEASE_SELECTOR) -> str:
    """Return a dashboard-safe greenfield release target label.

    Greenfield first-release targets must display as plain numeric selectors
    such as ``0.0.1``. If an operator supplies a custom target with extra words,
    prefer the embedded numeric selector; otherwise keep a short trimmed label so
    KPI cards do not wrap or overflow.
    """

    text = " ".join(str(value or "").split()).strip()
    version_token = release_target_version_token(text)
    if version_token:
        return version_token
    label = text or str(fallback or "").strip() or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    if len(label) <= _MAX_RELEASE_TARGET_LABEL_CHARS:
        return label
    return label[: _MAX_RELEASE_TARGET_LABEL_CHARS - 3].rstrip() + "..."


def proposal_release_selector(proposal: Mapping[str, Any], explicit_selector: str = "") -> str:
    explicit = str(explicit_selector or "").strip()
    if explicit:
        return explicit
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    selector = str(release_plan.get("selector", "")).strip()
    return selector or DEFAULT_GREENFIELD_RELEASE_SELECTOR


def semver_release_metadata(*, selector: str, release_plan: Mapping[str, Any]) -> tuple[str, str]:
    version = str(release_plan.get("version", "")).strip()
    tag = str(release_plan.get("tag", "")).strip()
    version = release_target_version_token(version) or version
    selector_version = release_target_version_token(selector)
    if _SEMVER_SELECTOR_RE.fullmatch(selector) or selector_version:
        version = version or selector_version or selector
        tag = tag or f"v{version}"
    return version, tag


def create_greenfield_program(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
) -> dict[str, Any]:
    created = [row for row in backlog_result.get("created", []) if isinstance(row, Mapping)]
    if len(created) < 2:
        return {"created": False, "reason": "greenfield proposal did not create an umbrella with children"}
    umbrella = created[0]
    umbrella_id = str(umbrella.get("idea_id", "")).strip().upper()
    if not umbrella_id:
        return {"created": False, "reason": "missing umbrella workstream id"}
    waves = _assign_wave_members(proposal=proposal, created_backlog=created)
    if not waves:
        child_ids = [
            str(row.get("idea_id", "")).strip().upper()
            for row in created[1:]
            if str(row.get("idea_id", "")).strip()
        ]
        if not child_ids:
            return {"created": False, "reason": "greenfield proposal has no child workstreams for waves"}
        waves = [
            {
                "wave_id": "W1",
                "label": "First release slice",
                "status": "active",
                "summary": "Initial greenfield release slice.",
                "exit_gate": "First release slice exits only after the targeted child workstreams have source-backed proof and refreshed release evidence.",
                "validation": [],
                "depends_on": [],
                "primary_workstreams": child_ids,
                "carried_workstreams": [],
                "in_band_workstreams": [],
                "gate_refs": [],
            }
        ]
    document = {"umbrella_id": umbrella_id, "version": "v1", "waves": waves}
    idea_specs = backlog_result.get("_candidate_idea_specs", {})
    if not isinstance(idea_specs, Mapping) or umbrella_id not in idea_specs:
        raise ValueError(f"cannot create greenfield program for unknown umbrella `{umbrella_id}`")
    umbrella_spec = idea_specs[umbrella_id]
    args = argparse.Namespace(program_command="create", dry_run=False)
    governance = program_wave_execution_engine.program_governance_decision(
        repo_root=repo_root,
        umbrella_spec=umbrella_spec,
        document=document,
        args=args,
    )
    authoring_execution_policy.enforce_governed_authoring_action(governance)
    program_wave_authoring._update_idea_metadata(  # noqa: SLF001
        umbrella_spec.path,
        {"execution_model": execution_wave_contract.EXECUTION_MODEL_UMBRELLA_WAVES},
    )
    path = program_wave_authoring._write_program_document(repo_root, umbrella_id, document)  # noqa: SLF001
    mutable_specs = dict(idea_specs)
    updated_metadata = dict(umbrella_spec.metadata)
    updated_metadata["execution_model"] = execution_wave_contract.EXECUTION_MODEL_UMBRELLA_WAVES
    mutable_specs[umbrella_id] = type(umbrella_spec)(
        path=umbrella_spec.path,
        metadata=updated_metadata,
        sections=set(umbrella_spec.sections),
        section_bodies=dict(umbrella_spec.section_bodies),
    )
    programs, errors = execution_wave_contract.collect_execution_programs(
        repo_root=repo_root,
        idea_specs=mutable_specs,
    )
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "created": True,
        "umbrella_id": umbrella_id,
        "program_path": str(path),
        "waves": waves,
        "program_count": len(programs),
        "execution_engine": governance.to_dict(),
    }


def first_release_workstream_ids(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
    program_result: Mapping[str, Any] | None,
) -> list[str]:
    created_ids = [
        str(item.get("idea_id", "")).strip().upper()
        for item in created_backlog
        if str(item.get("idea_id", "")).strip()
    ]
    if not created_ids:
        return []
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    proposal_backlog = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    explicit = _resolve_workstream_refs(
        _workstream_refs(release_plan),
        created_backlog=created_backlog,
        proposal_backlog=proposal_backlog,
    )
    selected = [created_ids[0]]
    if explicit:
        selected.extend(item for item in explicit if item not in selected)
    else:
        waves = program_result.get("waves", []) if isinstance(program_result, Mapping) else []
        first_wave = next((row for row in waves if isinstance(row, Mapping)), None)
        if first_wave is not None:
            for field in ("primary_workstreams", "carried_workstreams", "in_band_workstreams"):
                for item in first_wave.get(field, []) if isinstance(first_wave.get(field), list) else []:
                    token = str(item or "").strip().upper()
                    if token and token not in selected:
                        selected.append(token)
        else:
            selected.extend(item for item in created_ids[1:4] if item not in selected)
    return [item for item in selected if item in created_ids]


def _assign_wave_members(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    program = proposal.get("program", {}) if isinstance(proposal.get("program"), Mapping) else {}
    wave_rows = [row for row in program.get("waves", []) if isinstance(row, Mapping)]
    child_backlog = [row for row in created_backlog[1:] if str(row.get("idea_id", "")).strip()]
    if not wave_rows or not child_backlog:
        return []
    proposal_backlog = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    proposal_by_created_id: dict[str, Mapping[str, Any]] = {}
    for created, raw in zip(created_backlog, proposal_backlog, strict=False):
        idea_id = str(created.get("idea_id", "")).strip().upper()
        if idea_id:
            proposal_by_created_id[idea_id] = raw
    child_ids = [str(row.get("idea_id", "")).strip().upper() for row in child_backlog]
    unassigned = [item for item in child_ids if item]
    raw_assignments: list[list[str]] = []
    for row in wave_rows:
        explicit = _resolve_workstream_refs(
            _workstream_refs(row),
            created_backlog=created_backlog,
            proposal_backlog=proposal_backlog,
        )
        members = [item for item in explicit if item in child_ids]
        if not members:
            wave_tokens = _wave_text(row)
            for child_id in child_ids:
                if child_id not in unassigned:
                    continue
                overlap = wave_tokens.intersection(_backlog_text(proposal_by_created_id.get(child_id, {})))
                if overlap:
                    members.append(child_id)
        if not members:
            if unassigned:
                members.append(unassigned[0])
            elif child_ids:
                fallback_index = min(len(raw_assignments), len(child_ids) - 1)
                members.append(child_ids[fallback_index])
        deduped = []
        for item in members:
            if item in child_ids and item not in deduped:
                deduped.append(item)
        for item in deduped:
            if item in unassigned:
                unassigned.remove(item)
        raw_assignments.append(deduped)
    index = 0
    while unassigned and raw_assignments:
        raw_assignments[index % len(raw_assignments)].append(unassigned.pop(0))
        index += 1

    waves: list[dict[str, Any]] = []
    previous_wave_id = ""
    used_wave_ids: set[str] = set()
    for index, (row, members) in enumerate(zip(wave_rows, raw_assignments, strict=False), start=1):
        wave_id = _wave_id_for_row(row, index)
        if wave_id in used_wave_ids:
            wave_id = f"W{index}"
        used_wave_ids.add(wave_id)
        status = str(row.get("status", "")).strip().lower()
        if status not in execution_wave_contract.VALID_WAVE_STATUSES:
            status = "active" if not waves else "planned"
        depends_on = list(text_values(row.get("depends_on")))
        if not depends_on and previous_wave_id:
            depends_on = [previous_wave_id]
        waves.append(
            {
                "wave_id": wave_id,
                "label": _wave_label(row, wave_id),
                "status": status,
                "summary": _wave_summary(row),
                "exit_gate": _wave_exit_gate(row),
                "validation": _wave_validation(row),
                "depends_on": depends_on,
                "primary_workstreams": members,
                "carried_workstreams": [],
                "in_band_workstreams": [],
                "gate_refs": [],
            }
        )
        previous_wave_id = wave_id
    return waves


def _created_title_map(
    created_backlog: Sequence[Mapping[str, Any]],
    proposal_backlog: Sequence[Mapping[str, Any]] = (),
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index, item in enumerate(created_backlog):
        idea_id = str(item.get("idea_id", "")).strip().upper()
        title = str(item.get("title", "")).strip()
        if not idea_id:
            continue
        _add_ref_mapping(mapping, idea_id=idea_id, value=idea_id)
        _add_ref_mapping(mapping, idea_id=idea_id, value=title)
        raw = proposal_backlog[index] if index < len(proposal_backlog) else {}
        if isinstance(raw, Mapping):
            for key in (
                "id",
                "idea_id",
                "workstream_id",
                "slug",
                "title",
                "name",
                "label",
            ):
                _add_ref_mapping(mapping, idea_id=idea_id, value=raw.get(key))
    return mapping


def _add_ref_mapping(mapping: dict[str, str], *, idea_id: str, value: Any) -> None:
    token = str(value or "").strip()
    if not token:
        return
    mapping[token.casefold()] = idea_id
    mapping[token.upper()] = idea_id
    slug = slugify(token)
    if slug:
        mapping[slug] = idea_id


def _workstream_refs(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "workstreams",
        "workstream_ids",
        "workstream_titles",
        "target_workstreams",
        "target_workstream_ids",
        "target_workstream_titles",
        "related_workstreams",
        "backlog_titles",
        "primary_workstreams",
    ):
        if key in row:
            values.extend(text_values(row.get(key)))
    return values


def _resolve_workstream_refs(
    refs: Sequence[str],
    *,
    created_backlog: Sequence[Mapping[str, Any]],
    proposal_backlog: Sequence[Mapping[str, Any]] = (),
) -> list[str]:
    title_map = _created_title_map(created_backlog, proposal_backlog)
    created_ids = {str(item.get("idea_id", "")).strip().upper() for item in created_backlog}
    resolved: list[str] = []
    for raw in refs:
        token = str(raw or "").strip()
        if not token:
            continue
        candidate = token.upper()
        if _IDEA_ID_RE.fullmatch(candidate) and candidate in created_ids and candidate not in resolved:
            resolved.append(candidate)
            continue
        for key in (candidate, token.casefold(), slugify(token)):
            mapped = title_map.get(key)
            if mapped and mapped not in resolved:
                resolved.append(mapped)
                break
    return resolved


def _row_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in text_values(values):
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", value.casefold()):
            if len(token) >= 3 and token not in _STOP_WORDS:
                tokens.add(token)
    return tokens


def _wave_text(row: Mapping[str, Any]) -> set[str]:
    return _row_tokens(
        row.get("wave"),
        row.get("wave_id"),
        row.get("label"),
        row.get("name"),
        row.get("goal"),
        row.get("summary"),
        row.get("validation"),
        row.get("validation_gate"),
        row.get("component_focus"),
        row.get("components"),
    )


def _backlog_text(row: Mapping[str, Any]) -> set[str]:
    return _row_tokens(
        row.get("title"),
        row.get("problem"),
        row.get("opportunity"),
        row.get("product_view"),
        row.get("recommended_first_slice"),
        row.get("component_focus"),
        row.get("related_component_ids"),
        row.get("related_diagram_slugs"),
    )


def _wave_id_for_row(row: Mapping[str, Any], index: int) -> str:
    for key in ("wave_id", "id", "wave"):
        token = str(row.get(key, "")).strip().upper()
        if not token:
            continue
        if token.startswith("W") and token[1:].isdigit() and int(token[1:]) >= 1:
            return token
        if token.isdigit() and int(token) >= 1:
            return f"W{int(token)}"
    return f"W{index}"


def _wave_label(row: Mapping[str, Any], wave_id: str) -> str:
    label = str(row.get("label", "") or row.get("name", "") or row.get("theme", "")).strip()
    return label or wave_id


def _wave_summary(row: Mapping[str, Any]) -> str:
    for key in ("summary", "goal", "validation_gate", "validation", "exit_gate"):
        token = join_sentence_text(row.get(key))
        if token:
            return token
    return "Confirmed greenfield execution wave."


def _wave_exit_gate(row: Mapping[str, Any]) -> str:
    for key in ("exit_gate", "validation_gate", "validation"):
        value = join_sentence_text(row.get(key))
        if value:
            return value
    return ""


def _wave_validation(row: Mapping[str, Any]) -> list[str]:
    values = list(unique_text(text_values(row.get("validation"))))
    joined_validation = join_sentence_text(values)
    for key in ("validation_gate", "exit_gate"):
        for token in text_values(row.get(key)):
            if joined_validation and token.casefold() == joined_validation.casefold():
                continue
            values.append(token)
    return list(unique_text(values))
