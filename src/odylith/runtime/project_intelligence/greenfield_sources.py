"""Proposal source helpers for greenfield Project dashboards."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.artifact_graph import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import restore_source_acronym_number_tokens
from odylith.runtime.project_intelligence.utils import dict_value, list_value, sentence


def _accepted_proposal(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    mode = str(value.get("mode", "")).strip()
    schema = str(value.get("schema_version", "")).strip()
    if (
        isinstance(value.get("project_intelligence"), Mapping)
        and (
            "greenfield" in mode
            or schema == "odylith.greenfield.proposal.v1"
            or mode in {"host_reasoned_proposal", "host_reasoned_greenfield_proposal"}
        )
    ):
        return dict(value)
    for key in ("greenfield_proposal", "accepted_proposal", "proposal"):
        nested = value.get(key)
        proposal = _accepted_proposal(nested)
        if proposal:
            return proposal
    return {}


def _proposal_from_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, Mapping):
        return {}
    proposal = _accepted_proposal(raw.get("proposal"))
    if not proposal:
        proposal = _accepted_proposal(raw)
    if not proposal:
        return {}
    if raw.get("schema_version") == "odylith.accepted_project.v1":
        enriched = dict(proposal)
        enriched["_accepted_project"] = {
            "accepted_at": sentence(raw.get("accepted_at")),
            "origin": sentence(raw.get("origin"), "greenfield"),
            "evidence_tier": sentence(raw.get("evidence_tier"), "user_intent"),
            "created": dict_value(raw.get("created")),
            "source_path": str(path),
            "validation_gate": dict_value(raw.get("validation_gate") or raw.get("tribunal")),
        }
        enriched["_source_launch"] = dict_value(raw.get("source_launch"))
        return enriched
    return proposal


def _text_rows(value: object, *, keys: Sequence[str] = ("statement", "question", "risk", "validation", "goal")) -> list[str]:
    rows: list[str] = []
    for item in list_value(value):
        if isinstance(item, Mapping):
            text = next((sentence(item.get(key)) for key in keys if sentence(item.get(key))), "")
        else:
            text = sentence(item)
        if text and text not in rows:
            rows.append(text)
    return rows


def _governance_titles(
    *,
    backlog: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    accepted: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    titles: dict[str, str] = {}
    created = dict_value((accepted or {}).get("created"))
    created_workstreams = [dict(row) for row in list_value(created.get("workstreams")) if isinstance(row, Mapping)]
    created_diagrams = list_value(created.get("diagrams"))

    def add(reference: object, title: object) -> None:
        ref = sentence(reference).upper()
        label = sentence(title)
        if ref and label and re.fullmatch(r"(?:B|D)-\d+", ref):
            titles[ref] = label

    for index, row in enumerate(backlog):
        created_row = created_workstreams[index] if index < len(created_workstreams) else {}
        add(row.get("idea_id") or row.get("id") or created_row.get("idea_id"), row.get("title") or row.get("name") or created_row.get("title"))
    for index, row in enumerate(diagrams):
        created_row = created_diagrams[index] if index < len(created_diagrams) else {}
        if isinstance(created_row, Mapping):
            ref = created_row.get("diagram_id") or created_row.get("id")
            label = created_row.get("title") or created_row.get("name")
        else:
            ref = created_row
            label = ""
        add(
            row.get("diagram_id") or row.get("id") or ref,
            row.get("title") or row.get("name") or row.get("slug") or label,
        )
    return titles


def _lens(*, proposal: Mapping[str, Any], backlog: Sequence[Mapping[str, Any]], components: Sequence[Mapping[str, Any]]) -> str:
    classification = dict_value(proposal.get("classification"))
    for key in ("primary_lens", "domain_lens", "family"):
        token = sentence(classification.get(key))
        if token:
            return _lens_label(token, proposal=proposal)
    for row in backlog:
        intelligence = row.get("domain_intelligence")
        if not isinstance(intelligence, Mapping):
            continue
        graph = domain_graph_from_workstream(intelligence, row=row, proposal=proposal)
        if graph.primary_lens:
            return _lens_label(graph.primary_lens, proposal=proposal)
    for component in components:
        token = sentence(component.get("kind") or component.get("label"))
        if token:
            return _lens_label(token, proposal=proposal)
    return "greenfield"


def _lens_label(value: str, *, proposal: Mapping[str, Any]) -> str:
    text = sentence(value).lower()
    source = ""
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        source = sentence(intent.get("title"))
    if not source:
        source = sentence(proposal.get("title"))
    return restore_source_acronym_number_tokens(text, source)


def _first_path(
    *,
    release_plan: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    validation: Sequence[str] = (),
) -> str:
    validation_first_path = _first_slice_from_validation(validation)
    if validation_first_path:
        return validation_first_path
    for item in backlog:
        title = sentence(item.get("title"))
        if title.lower().startswith("govern "):
            continue
        first_slice = sentence(item.get("recommended_first_slice"))
        if first_slice and not _is_meta_first_path(title=title, first_slice=first_slice):
            return first_slice
    stages = [dict(row) for row in list_value(release_plan.get("release_stages")) if isinstance(row, Mapping)]
    if stages:
        stage = stages[0]
        return sentence(stage.get("release_gate") or stage.get("label"), "First release gate")
    if backlog:
        return sentence(backlog[0].get("recommended_first_slice") or backlog[0].get("title"), "First proposed workstream")
    return "One accepted path moves from proposal intent to validated first slice."


def _first_slice_from_validation(rows: Sequence[str]) -> str:
    for row in rows:
        label, body = _labeled_text_parts(row)
        normalized = label.replace("_", " ").replace("-", " ").casefold()
        if body and normalized in {
            "first slice proof",
            "first path proof",
            "first slice",
            "first path",
        }:
            return body
    return ""


def _labeled_text_parts(value: object) -> tuple[str, str]:
    text = sentence(value)
    label, sep, body = text.partition(":")
    if not sep:
        return "", text
    return sentence(label), sentence(body)


def _clean_labeled_text(value: object) -> str:
    label, body = _labeled_text_parts(value)
    normalized = label.replace("_", " ").replace("-", " ").casefold()
    if body and normalized in {
        "first slice proof",
        "first path proof",
        "proof",
        "validation",
        "success condition",
    }:
        return body
    return sentence(value)


def _is_meta_first_path(*, title: str, first_slice: str) -> bool:
    text = f"{title} {first_slice}".casefold()
    if not text.strip():
        return False
    if sentence(title).casefold().startswith(("guide ", "shape ", "govern ")):
        return True
    return any(
        marker in text
        for marker in (
            "accept or revise",
            "accept the",
            "component boundaries",
            "proof gates",
            "before implementation planning",
            "coding-readiness",
            "project shape",
            "project direction",
            "proposal review",
        )
    )
