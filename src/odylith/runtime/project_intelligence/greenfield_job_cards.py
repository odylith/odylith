"""Job card helpers for greenfield Project dashboards."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.project_intelligence.greenfield_participant_cards import _repeat_key
from odylith.runtime.project_intelligence.greenfield_project_text import _capitalize_first
from odylith.runtime.project_intelligence.greenfield_project_text import _looks_path_echo
from odylith.runtime.project_intelligence.job_cards import job_card_summary
from odylith.runtime.project_intelligence.job_cards import job_status_label
from odylith.runtime.project_intelligence.job_cards import low_information_job_body
from odylith.runtime.project_intelligence.product_story import summarize_first_path
from odylith.runtime.project_intelligence.utils import dict_value, list_value, sentence, short

def _jobs(
    *,
    backlog: Sequence[Mapping[str, Any]],
    program: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]] = (),
    first_path: str = "",
    project_title: str = "",
    accepted: Mapping[str, Any] | None = None,
) -> list[tuple[str, str, str, str]]:
    rows = []
    component_summaries = _component_summary_map(components)
    created_workstreams = _created_workstream_rows(dict_value(accepted))
    seen_body_keys: set[str] = set()
    for index, item in enumerate(backlog[:6]):
        title = sentence(item.get("title"), "Proposed product slice")
        body = _job_body_text(item=item, title=title, first_path=first_path, component_summaries=component_summaries)
        if _looks_path_echo(body, first_path=first_path) or _repeat_key(body) in seen_body_keys:
            body = _job_fallback_body(title)
        seen_body_keys.add(_repeat_key(body))
        status = job_status_label(item.get("evidence_tier"))
        rows.append(
            (
                short(_project_job_heading(title=title, project_title=project_title), limit=78),
                _bounded_job_body(body=body, title=title),
                status,
                _workstream_reference(item=item, created=created_workstreams[index] if index < len(created_workstreams) else {}),
            )
        )
    if rows:
        return rows
    return [
        (
            short(
                _project_job_heading(
                    title=sentence(row.get("label"), "Proposed release step"),
                    project_title=project_title,
                ),
                limit=78,
            ),
            short(sentence(row.get("goal"), "Proposed delivery step."), limit=145),
            "Proposed",
            _workstream_reference(item=row, created={}),
        )
        for row in [dict(value) for value in list_value(program.get("waves")) if isinstance(value, Mapping)][:6]
    ]


def _project_job_heading(*, title: str, project_title: str) -> str:
    heading = _polish_heading(title)
    project = _polish_heading(project_title)
    if not project:
        return heading
    compact = re.sub(rf"\b{re.escape(project)}\b", "", heading, flags=re.IGNORECASE)
    compact = re.sub(r"\s+", " ", compact).strip(" -:;,.")
    compact = _polish_heading(compact)
    if compact and compact.casefold() != heading.casefold():
        return compact
    return heading


def _created_workstream_rows(accepted: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    created = dict_value(accepted.get("created"))
    return [dict(row) for row in list_value(created.get("workstreams")) if isinstance(row, Mapping)]


def _workstream_reference(*, item: Mapping[str, Any], created: Mapping[str, Any]) -> str:
    for value in (
        item.get("idea_id"),
        item.get("workstream_id"),
        item.get("backlog_id"),
        item.get("id"),
        created.get("idea_id"),
        created.get("workstream_id"),
        created.get("backlog_id"),
        created.get("id"),
    ):
        token = sentence(value).upper()
        if re.fullmatch(r"B-\d+", token):
            return token
    return ""


def _job_body_text(
    *,
    item: Mapping[str, Any],
    title: str,
    first_path: str,
    component_summaries: Mapping[str, str],
) -> str:
    if _is_program_workstream(title):
        return "Keeps the first release centered on one complete user outcome, with explicit limits and proof before source work starts."
    for value in (item.get("product_view"), item.get("problem"), item.get("recommended_first_slice")):
        text = sentence(value)
        if not text or _looks_path_echo(text, first_path=first_path):
            continue
        text = job_card_summary(text)
        if low_information_job_body(text):
            continue
        if re.search(r"\b\d+[.)]\s+[A-Z]", text):
            compact = summarize_first_path(text)
            if compact and not _looks_path_echo(compact, first_path=first_path):
                return compact
        text = re.sub(r"\bShow how The\b", "Show how the", text)
        text = re.sub(r"\bmaps the first path, The\b", "maps the first path, the", text)
        if _looks_clipped_job_body(text):
            continue
        return text
    component_body = _matched_component_summary(title=title, component_summaries=component_summaries)
    component_body = job_card_summary(component_body)
    if component_body and not low_information_job_body(component_body) and not _looks_clipped_job_body(component_body):
        return component_body
    first_path_body = _job_first_path_body(first_path)
    if first_path_body:
        return first_path_body
    if title.casefold().startswith("prove "):
        return _job_fallback_body(title)
    if " boundary" in title.casefold():
        return _job_fallback_body(title)
    if " proof" in title.casefold():
        return _job_fallback_body(title)
    return _job_fallback_body(title)


def _job_first_path_body(first_path: str) -> str:
    action = first_path_action_phrase(first_path, fallback="", limit=90, max_fragments=1)
    outcome = first_path_outcome_phrase(first_path, fallback="", limit=90)
    if action and outcome:
        return f"Focuses the slice on {action} so the user receives {outcome}."
    if outcome:
        return f"Focuses the slice on producing {outcome} with enough context for review."
    return ""


def _bounded_job_body(*, body: str, title: str) -> str:
    text = short(body, limit=145)
    if low_information_job_body(text) or _looks_clipped_job_body(text):
        text = short(_job_fallback_body(title), limit=145)
    return text


def _looks_clipped_job_body(value: object) -> bool:
    lowered = sentence(value).casefold().strip()
    return bool(
        re.search(r"\b(?:asks?|checks?|current|validation|contact|missing)\s*[.]$", lowered)
        or re.search(r"\bthe user\s+[A-Z]", sentence(value))
        or ".." in lowered
    )


def _job_fallback_body(title: str) -> str:
    clean_title = sentence(title, "This product slice")
    subject = re.sub(r"^(?:prove|define|prepare|establish|govern|shape|guide)\s+", "", clean_title, flags=re.IGNORECASE)
    subject = re.sub(r"\s+(?:boundary|release proof|program)$", "", subject, flags=re.IGNORECASE).strip(" .")
    if not subject:
        subject = clean_title
    lowered = clean_title.casefold()
    if _is_program_workstream(clean_title):
        return "Keeps the first release centered on one complete user outcome, with explicit limits and proof before source work starts."
    if " proof" in lowered:
        return f"Packages reviewer-visible proof for {subject} before the release can move forward."
    if " boundary" in lowered:
        return f"Defines what {subject} owns, receives, produces, and must prove for the first release."
    if lowered.startswith("prove "):
        return f"Turns {subject} into a specific release capability with reviewer-visible evidence."
    return f"Turns {subject} into a concrete product slice with a visible result, a blocked path, and a reviewable explanation."


def _polish_heading(value: str) -> str:
    minor_words = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    words = sentence(value).split()
    polished: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()[]{}.,;:")
        if index > 0 and core.casefold() in minor_words:
            polished.append(word.replace(core, core.lower(), 1))
        else:
            polished.append(word)
    return " ".join(polished)


def _is_program_workstream(title: str) -> bool:
    lowered = sentence(title).casefold()
    return lowered.startswith(("establish ", "govern ", "guide ", "shape ")) and "program" in lowered


def _component_summary_map(components: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for component in components:
        label = sentence(component.get("label") or component.get("name") or component.get("component_id"))
        body = _component_summary(component)
        if label and body:
            rows[_repeat_key(label)] = body
    return rows


def _matched_component_summary(*, title: str, component_summaries: Mapping[str, str]) -> str:
    title_key = _repeat_key(title)
    for label_key, body in component_summaries.items():
        if label_key and label_key in title_key:
            return body
    return ""


def _component_summary(component: Mapping[str, Any]) -> str:
    text = sentence(component.get("responsibility") or component.get("boundary") or component.get("summary"))
    if not text:
        return ""
    head, sep, tail = text.partition(" owns ")
    if sep and tail.strip():
        owned = tail.strip(" .")
        for prefix in ("performs ", "estimates ", "engraves ", "writes ", "renders ", "captures ", "stores ", "produces "):
            if owned.casefold().startswith(prefix):
                return _capitalize_first(owned).rstrip(".") + "."
        return f"Owns {owned.rstrip('.')}."
    text = re.sub(r"\bShow how The\b", "Show how the", text)
    text = re.sub(r"\bmaps the first path, The\b", "maps the first path, the", text)
    return text
