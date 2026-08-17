"""General Product Story projection for the Project tab."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.project_intelligence.focus import backlog_rows_by_id
from odylith.runtime.project_intelligence.narration import evidence_boundary_phrase
from odylith.runtime.project_intelligence.summary import action_sentence, concise_text
from odylith.runtime.project_intelligence.utils import (
    capitalize_sentence_start,
    dict_value,
    display_text,
    list_value,
    sanitize_actor_body,
    sentence,
    short,
    strings,
)


def build_source_product_story(
    *,
    project_title: str,
    project_intro: str,
    release_label: str,
    current_focus: str,
    next_title: str,
    next_action_text: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    atlas: Mapping[str, Any],
    evidence_sources: Sequence[str],
    blockers: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    """Build source-backed story prose for existing projects and operations."""

    title = sentence(project_title, "Project")
    headline = _source_headline(
        title=title,
        project_intro=project_intro,
        current_focus=current_focus,
        active_workstreams=active_workstreams,
        backlog=backlog,
    )
    narrative = _source_narrative_paragraphs(
        title=title,
        project_intro=project_intro,
        release_label=release_label,
        current_focus=current_focus,
        active_workstreams=active_workstreams,
        backlog=backlog,
        next_action_text=next_action_text,
        blockers=blockers,
    )
    artifact = _source_artifact_paragraph(
        active_workstreams=active_workstreams,
        backlog=backlog,
        components=components,
        atlas=atlas,
        evidence_sources=evidence_sources,
    )
    supporting_records = _source_supporting_records(
        active_workstreams=active_workstreams,
        backlog=backlog,
        components=components,
        atlas=atlas,
        evidence_sources=evidence_sources,
    )
    paragraphs = [*narrative, *([artifact] if artifact else [])]
    return {
        "headline": headline,
        "standfirst": "",
        "paragraphs": paragraphs,
        "supporting_records": supporting_records,
        "actors": [],
    }


def _source_headline(
    *,
    title: str,
    project_intro: str,
    current_focus: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
) -> str:
    intro_headline = _headline_from_intro(title=title, intro=project_intro)
    if intro_headline:
        return intro_headline
    work = _workstream_names(active_workstreams=active_workstreams, backlog=backlog)
    focus = concise_text(current_focus, limit=92)
    if focus:
        return focus
    if work:
        return f"{title} is centered on {work}"
    return f"{title} has one current project story"


def _headline_from_intro(*, title: str, intro: str) -> str:
    text = sentence(intro).rstrip(".")
    if not text or _is_component_inventory_line(text):
        return ""
    lowered = text.casefold()
    title_lower = title.casefold()
    for marker in (" helps ", " enables ", " lets "):
        if marker.strip() not in lowered:
            continue
        before, sep, after = text.partition(marker)
        if sep and before.strip().casefold() == title_lower and after.strip():
            return short(f"How {title} {marker.strip()} {after.strip()}", limit=92)
    if lowered.startswith(f"{title_lower} turns "):
        return short(text, limit=92)
    if lowered.startswith(f"{title_lower} is "):
        return short(text, limit=92)
    return ""


def _source_narrative_paragraphs(
    *,
    title: str,
    project_intro: str,
    release_label: str,
    current_focus: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    next_action_text: str,
    blockers: Sequence[tuple[str, str, str]],
) -> list[str]:
    intro = _source_product_intro(title=title, project_intro=project_intro)
    workflow = _source_workflow_paragraph(
        release_label=release_label,
        current_focus=current_focus,
        active_workstreams=active_workstreams,
        backlog=backlog,
        next_action_text=next_action_text,
    )
    proof = _source_proof_paragraph(release_label=release_label, blockers=blockers)
    return [row for row in (intro, workflow, proof) if row]


def _source_product_intro(*, title: str, project_intro: str) -> str:
    intro = sentence(project_intro).rstrip(".")
    if intro and not _is_component_inventory_line(intro):
        return f"{intro}."
    return (
        f"{title} is a product with a source-backed governance view, but its product story still needs "
        "a clearer user, problem, workflow, and proof boundary before implementation claims move forward."
    )


def _source_workflow_paragraph(
    *,
    release_label: str,
    current_focus: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    next_action_text: str,
) -> str:
    release = sentence(release_label, "current release")
    workflow = _source_workflow_phrase(active_workstreams=active_workstreams, backlog=backlog)
    focus = concise_text(current_focus, limit=120)
    if _is_acceptance_headline(focus):
        focus = ""
    next_move = _lower_first(action_sentence(next_action_text).rstrip("."))
    if workflow:
        body = f"The first usable workflow for {release} is {workflow}."
    elif focus:
        body = f"The first usable workflow for {release} is the current focus: {_lower_first(focus).rstrip('.')}."
    else:
        body = f"The first usable workflow for {release} still needs to be named in source records."
    if next_move:
        body += f" The next move is to {next_move.removeprefix('to ')}."
    return body


def _source_proof_paragraph(*, release_label: str, blockers: Sequence[tuple[str, str, str]]) -> str:
    release = sentence(release_label, "current release")
    body = (
        f"Release {release} is coherent when the product workflow, owned boundaries, topology, "
        "and validation evidence agree before implementation readiness is claimed."
    )
    risk = _risk_sentence(blockers)
    if risk:
        body += f" {risk}"
    return body


def _source_workflow_phrase(*, active_workstreams: Sequence[str], backlog: Mapping[str, Any]) -> str:
    rows_by_id = backlog_rows_by_id(backlog)
    titles: list[str] = []
    for workstream_id in active_workstreams:
        token = sentence(workstream_id)
        row = rows_by_id.get(token, {})
        title = sentence(row.get("title"))
        if not title or _is_meta_record_title(title):
            continue
        titles.append(_lower_first(title).rstrip("."))
        if len(titles) >= 2:
            break
    if not titles:
        for row in list(backlog.get("execution", []))[:3] + list(backlog.get("queued", []))[:2]:
            if not isinstance(row, Mapping):
                continue
            title = sentence(row.get("title") or row.get("idea_id"))
            if not title or _is_meta_record_title(title):
                continue
            titles.append(_lower_first(title).rstrip("."))
            if len(titles) >= 2:
                break
    return _join(titles)


def _is_acceptance_headline(value: str) -> bool:
    text = sentence(value).casefold()
    return text.startswith(("greenfield proposal accepted for ", "accepted greenfield proposal for "))


def _is_component_inventory_line(value: str) -> bool:
    text = sentence(value).casefold()
    if not text:
        return False
    return (
        (" component responsible for " in text)
        or (" component that " in text and "initial evidence anchor" in text)
        or (" with `" in text and " as its initial" in text)
        or ("responsible for own " in text)
    )


def _source_artifact_paragraph(
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    atlas: Mapping[str, Any],
    evidence_sources: Sequence[str],
) -> str:
    work = _workstream_names(active_workstreams=active_workstreams, backlog=backlog)
    component_text = _component_names(components)
    diagram_text = _diagram_names(atlas)
    proof = evidence_boundary_phrase(evidence_sources)
    clauses: list[str] = []
    if work:
        clauses.append(f"Workstream records carry {work}")
    if component_text:
        clauses.append(f"Component records name the owned boundaries as {component_text}")
    if diagram_text:
        clauses.append(f"Diagram records give reviewers {diagram_text}")
    if proof:
        clauses.append(f"the proof boundary is {proof}")
    if not clauses:
        return "The story is still thin: source records exist, but no connected workstream, component, diagram, or proof boundary is strong enough to narrate yet."
    parts: list[str] = []
    if work:
        parts.append(f"After the product story is clear, Radar turns the active work into {work}.")
    if component_text:
        parts.append(f"Registry records anchor that work in {component_text}.")
    if diagram_text:
        parts.append(f"Atlas records give reviewers {diagram_text}.")
    if proof:
        parts.append(f"Evidence stays bounded to {proof}, so the story does not outrun the source records.")
    return " ".join(parts)


def _source_supporting_records(
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    atlas: Mapping[str, Any],
    evidence_sources: Sequence[str],
) -> list[str]:
    work = _workstream_names(active_workstreams=active_workstreams, backlog=backlog)
    component_text = _component_names(components)
    diagram_text = _diagram_names(atlas)
    proof = evidence_boundary_phrase(evidence_sources)
    rows: list[str] = []
    if work:
        rows.append(f"Radar carries {work}.")
    if component_text:
        rows.append(f"Registry names the owned boundaries as {component_text}.")
    if diagram_text:
        rows.append(f"Atlas gives reviewers {diagram_text}.")
    if proof:
        rows.append(f"Evidence is bounded by {proof}.")
    return rows


def _risk_sentence(blockers: Sequence[tuple[str, str, str]]) -> str:
    if not blockers:
        return ""
    title, detail, owner = blockers[0]
    clean_title = concise_text(title, limit=95)
    if not clean_title or clean_title.lower() == "evidence gap":
        return ""
    owner_text = sentence(owner)
    detail_text = sentence(detail)
    suffix = f" from {owner_text}" if owner_text else ""
    if detail_text:
        return f"The first open risk is {clean_title}{suffix}: {detail_text}."
    return f"The first open risk is {clean_title}{suffix}."


def _workstream_names(*, active_workstreams: Sequence[str], backlog: Mapping[str, Any]) -> str:
    rows_by_id = backlog_rows_by_id(backlog)
    names: list[str] = []
    for workstream_id in active_workstreams[:3]:
        token = sentence(workstream_id)
        row = rows_by_id.get(token, {})
        title = sentence(row.get("title"), token)
        names.append(f"{token} {title}" if token and title and title != token else title or token)
    if not names:
        for row in list(backlog.get("execution", []))[:3] + list(backlog.get("queued", []))[:2]:
            if isinstance(row, Mapping):
                title = sentence(row.get("title") or row.get("idea_id"))
                if title:
                    names.append(title)
    return _join(names)


def _component_names(components: Sequence[Mapping[str, Any]]) -> str:
    names = [
        sentence(component.get("name") or component.get("label") or component.get("component_id"))
        for component in components
    ]
    return _join(_dedupe([name for name in names if name])[:4])


def _diagram_names(atlas: Mapping[str, Any]) -> str:
    active = [row for row in list_value(atlas.get("active")) if isinstance(row, Mapping)]
    rows = active or [row for row in list_value(atlas.get("diagrams")) if isinstance(row, Mapping)]
    names = [
        sentence(row.get("title") or row.get("name") or row.get("diagram_id") or row.get("slug"))
        for row in rows
    ]
    return _join(_dedupe([name for name in names if name])[:3])


def _lower_first(value: str) -> str:
    text = sentence(value).strip()
    return f"{text[:1].lower()}{text[1:]}" if text else ""


def _is_meta_record_title(value: str) -> bool:
    text = sentence(value).casefold()
    return text.startswith(("govern project direction", "guide ", "shape ")) or any(
        marker in text
        for marker in (
            "project spine",
            "project direction",
            "project shape",
            "program boundary",
        )
    )


def _join(values: Sequence[str]) -> str:
    rows = [sentence(value) for value in values if sentence(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _dedupe(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(value)
    return rows
