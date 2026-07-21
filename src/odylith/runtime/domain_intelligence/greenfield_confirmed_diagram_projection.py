"""Refresh confirmed greenfield diagram projections from semantic facts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_evidence_record_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_text import text_values


def refresh_confirmed_diagram_projection(proposal: dict[str, Any], rows: list[Any]) -> bool:
    """Rerender stale diagram rows from the current SemanticModelIR projection."""

    semantic_model = proposal.get("semantic_model")
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    if not isinstance(semantic_model, Mapping) or not isinstance(intent, Mapping):
        return False
    label = completion_text.project_title(proposal)
    components = [dict(row) for row in proposal.get("components", []) if isinstance(row, Mapping)]
    if not label or not components:
        return False
    first_path = completion_text.first_path(proposal)
    proof_boundary = completion_text.proof_boundary(proposal)
    internal_systems = text_values(intent.get("internal_systems"))
    regenerated = confirmed_diagrams(
        label=label,
        components=components,
        diagram_slugs=_diagram_slugs(rows=rows, label=label),
        workstream_titles=_diagram_workstream_titles(rows=rows, proposal=proposal),
        product_story=_clean(intent.get("product_story")),
        first_path=first_path,
        proof_boundary=proof_boundary,
        state_object=_clean(intent.get("state_object")) or completion_text.state_reference(proposal),
        evidence_record=confirmed_evidence_record_label(
            label=label,
            proof_boundary=proof_boundary,
            internal_systems=internal_systems,
        ),
        human_actors=text_values(intent.get("human_actors")),
        external_systems=text_values(intent.get("external_systems")),
        internal_systems=internal_systems,
        non_goals=text_values(proposal.get("non_goals") or intent.get("non_goals")),
        semantic_model=semantic_model,
    )
    changed = False
    for index, generated in enumerate(regenerated):
        if index >= len(rows):
            rows.append(dict(generated))
            changed = True
            continue
        row = rows[index]
        if not isinstance(row, dict):
            rows[index] = dict(generated)
            changed = True
            continue
        for key in (
            "slug",
            "title",
            "kind",
            "summary",
            "read_guide",
            "owner",
            "status",
            "link_state",
            "components",
            "related_workstream_titles",
            "related_components",
            "evidence_tier",
            "mermaid_source",
        ):
            value = generated.get(key)
            if row.get(key) != value:
                row[key] = value
                changed = True
    return changed


def _diagram_slugs(*, rows: list[Any], label: str) -> dict[str, str]:
    label_slug = completion_text.slug_title({"intent": {"title": label}})
    keys = ("context", "sequence", "state_evidence", "component_boundaries", "ownership", "proof_review")
    defaults = {
        "context": f"{label_slug}-system-context",
        "sequence": f"{label_slug}-first-path",
        "state_evidence": f"{label_slug}-state-evidence",
        "component_boundaries": f"{label_slug}-component-boundaries",
        "ownership": f"{label_slug}-ownership-proof",
        "proof_review": f"{label_slug}-release-proof-review",
    }
    result = dict(defaults)
    for key, row in zip(keys, rows, strict=False):
        if isinstance(row, Mapping) and _clean(row.get("slug")):
            result[key] = _clean(row.get("slug"))
    return result


def _diagram_workstream_titles(*, rows: list[Any], proposal: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for index, row in enumerate(rows[:6]):
        if not isinstance(row, Mapping):
            continue
        related = text_values(row.get("related_workstream_titles"))
        if index == 0 and len(related) >= 3:
            result.setdefault("program", related[0])
            result.setdefault("workflow", related[1])
            result.setdefault("boundary", related[2])
        elif index == 1 and len(related) >= 2:
            result.setdefault("workflow", related[0])
            result.setdefault("boundary", related[1])
        elif index == 2 and len(related) >= 3:
            result.setdefault("workflow", related[0])
            result.setdefault("boundary", related[1])
            result.setdefault("proof", related[2])
        elif index == 3 and related:
            result.setdefault("boundary", related[0])
        elif index == 4 and len(related) >= 2:
            result.setdefault("boundary", related[0])
            result.setdefault("proof", related[1])
        elif index == 5 and related:
            result.setdefault("proof", related[0])
    backlog_titles = [
        _clean(row.get("title"))
        for row in proposal.get("backlog", [])
        if isinstance(row, Mapping) and _clean(row.get("title"))
    ]
    for key, title in zip(("program", "workflow", "boundary", "proof"), backlog_titles, strict=False):
        result[key] = title
    return result


__all__ = ["refresh_confirmed_diagram_projection"]
