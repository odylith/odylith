"""Actor and external-boundary completion for accepted greenfield Product Intent."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_confirmed_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import completed_external_boundary_rows
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def complete_external_boundary(intent: dict[str, Any]) -> None:
    """Complete external-system rows and record unresolved boundary questions."""

    rows, ambiguities = completed_external_boundary_rows(intent)
    if rows:
        intent["external_systems"] = rows
    if ambiguities:
        intent["ambiguities"] = list(unique_text([*confirmed_text_values(intent.get("ambiguities")), *ambiguities]))


def normalize_confirmed_actor_context(intent: dict[str, Any], *, title: str) -> None:
    """Localize accepted actor rows and the first path to the confirmed project."""

    actor_rows = confirmed_text_values(intent.get("human_actors"))
    first_path = _clean(intent.get("first_path"))
    if actor_rows:
        intent["human_actors"] = [
            row
            if _row_is_explicit_first_path_actor(row, first_path)
            else normalized
            for row in actor_rows
            if (normalized := project_specific_actor_row(row, project_focus=title))
        ]
    if first_path:
        intent["first_path"] = _sentence(
            localize_leading_actor_reference(
                first_path,
                actor_rows=confirmed_text_values(intent.get("human_actors")),
                project_focus=title,
                fallback=f"{_focus_label(title)} user",
            )
        )


def _row_is_explicit_first_path_actor(row: str, first_path: str) -> bool:
    label = _clean(str(row).split(":", 1)[0])
    path = _clean(first_path)
    if not label or not path:
        return False
    return bool(re.match(rf"^(?:(?:a|an|the)\s+)?{re.escape(label)}\b", path, flags=re.IGNORECASE))
