"""Project-specific actor-label repair for confirmed greenfield artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import (
    project_specific_actor_labels,
    value_starts_with_generic_actor_label,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows


_EVIDENCE_KEYS = frozenset(
    {
        "host_instruction",
        "observed_source",
        "prompt",
        "source_html",
        "source_mmd",
        "source_png",
        "source_svg",
        "source_title",
    }
)


def _is_untrusted_evidence_key(key: Any) -> bool:
    normalized = str(key).casefold()
    return normalized in _EVIDENCE_KEYS or normalized.startswith("source_")


def repair_generic_actor_labels(proposal: dict[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    actor_rows = text_values(intent.get("human_actors")) if isinstance(intent, Mapping) else []
    labels = project_specific_actor_labels(intent if isinstance(intent, Mapping) else {})
    if not labels:
        labels = project_specific_actor_labels(
            {
                "title": completion_text.project_title(proposal),
                "human_actors": proposal.get("human_actors"),
            }
        )
    if not labels:
        return False
    actor_rows = actor_rows or labels
    fallback = labels[0]
    summary = "; ".join(labels[:2])
    changed = False
    project_focus = completion_text.project_title(proposal)
    for row in dict_rows(proposal.get("risks")):
        for key in ("statement", "mitigation"):
            value = row.get(key)
            repaired = localize_leading_actor_reference(
                str(value or ""),
                actor_rows=actor_rows,
                project_focus=project_focus,
                fallback=fallback,
                sentence_context=True,
            )
            if repaired and repaired != _clean(value):
                row[key] = repaired
                changed = True
    for row in dict_rows(proposal.get("backlog")):
        if value_starts_with_generic_actor_label(row.get("customer")):
            row["customer"] = summary
            changed = True
        intelligence = row.get("domain_intelligence")
        if not isinstance(intelligence, dict):
            continue
        actors = list(text_values(intelligence.get("actors")))
        if actors and any(value_starts_with_generic_actor_label(value) for value in actors):
            intelligence["actors"] = labels[:3]
            changed = True
        elif not actors:
            intelligence["actors"] = labels[:2]
            changed = True
    changed |= _repair_public_actor_references(
        proposal,
        actor_rows=actor_rows,
        project_focus=project_focus,
        fallback=fallback,
    )
    return changed


def _repair_public_actor_references(
    value: Any,
    *,
    actor_rows: Sequence[str],
    project_focus: str,
    fallback: str,
) -> bool:
    """Localize generic actor heads without rewriting the source-evidence record."""

    if isinstance(value, dict):
        changed = False
        for key, nested in value.items():
            if _is_untrusted_evidence_key(key):
                continue
            if isinstance(nested, str):
                repaired = localize_leading_actor_reference(
                    nested,
                    actor_rows=actor_rows,
                    project_focus=project_focus,
                    fallback=fallback,
                    sentence_context=True,
                )
                if repaired != _clean(nested):
                    value[key] = repaired
                    changed = True
                continue
            changed |= _repair_public_actor_references(
                nested,
                actor_rows=actor_rows,
                project_focus=project_focus,
                fallback=fallback,
            )
        return changed
    if isinstance(value, list):
        changed = False
        for index, nested in enumerate(value):
            if isinstance(nested, str):
                repaired = localize_leading_actor_reference(
                    nested,
                    actor_rows=actor_rows,
                    project_focus=project_focus,
                    fallback=fallback,
                    sentence_context=True,
                )
                if repaired != _clean(nested):
                    value[index] = repaired
                    changed = True
                continue
            changed |= _repair_public_actor_references(
                nested,
                actor_rows=actor_rows,
                project_focus=project_focus,
                fallback=fallback,
            )
        return changed
    return False


__all__ = ["repair_generic_actor_labels"]
