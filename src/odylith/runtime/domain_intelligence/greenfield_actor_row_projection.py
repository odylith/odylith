"""Canonical Greenfield human-actor rows before Product Intent sealing."""

from __future__ import annotations

import re
from collections.abc import Iterable

from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_actor_labels import sentence_actor_reference


def canonical_human_actor_rows(
    *, project_label: str, rows: Iterable[object], first_path: object = "", state_object: object = ""
) -> list[str]:
    """Return the actor rows used by both typed intent and proposal projections."""

    focus = project_actor_focus_label(project_label)
    result: list[str] = []
    for row in rows:
        text = str(row or "").strip()
        if text:
            source_label = text.partition(":")[0].strip(" .")
            explicit_path_actor = bool(source_label and re.match(
                rf"^(?:(?:a|an|the)\s+)?{re.escape(source_label)}\b",
                str(first_path or "").strip(),
                flags=re.IGNORECASE,
            ))
            row_focus = _state_actor_focus(state_object) if explicit_path_actor else focus
            projected = project_specific_actor_row(text, project_focus=row_focus or focus) or text
            label, separator, description = projected.partition(":")
            label = sentence_actor_reference(label)
            result.append(f"{label}:{description}" if separator else label)
    return result


def _state_actor_focus(value: object) -> str:
    match = re.search(
        r"\bprimary\s+state\s+object\s+is\s+(?:(?:a|an|the|one)\s+)?(?P<label>.+?)(?:\s+that\b|[.;]|$)",
        str(value or ""),
        flags=re.IGNORECASE,
    )
    return project_actor_focus_label(match.group("label")) if match else ""


def canonical_first_path_actor_reference(
    *,
    project_label: str,
    first_path: object,
    actor_rows: Iterable[object],
    fallback: str,
) -> str:
    """Use the same first-path actor spelling before sealing and projection."""

    return localize_leading_actor_reference(
        str(first_path or "").strip(),
        actor_rows=[str(row or "").strip() for row in actor_rows if str(row or "").strip()],
        project_focus=project_actor_focus_label(project_label),
        fallback=fallback,
        sentence_context=True,
    )


def project_actor_focus_label(label: str) -> str:
    """Remove generic product-kind suffixes from an actor-label context."""

    text = re.sub(
        r"\b(?:workspace|tracker|platform|system|application|app|tool|service|product|program)\b",
        "",
        str(label or ""),
        flags=re.IGNORECASE,
    )
    text = " ".join(text.replace(":", " ").split()).strip(" -")
    return text or str(label or "Project").strip() or "Project"


__all__ = [
    "canonical_first_path_actor_reference",
    "canonical_human_actor_rows",
    "project_actor_focus_label",
]
