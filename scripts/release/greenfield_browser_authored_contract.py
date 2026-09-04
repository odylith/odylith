"""Browser contract for exact structured Greenfield authored facts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def story_rows_match_payload(
    rendered_rows: list[dict[str, Any]],
    payload_rows: list[dict[str, Any]],
    *,
    structured_slots: Iterable[str] = (),
) -> bool:
    """Compare rendered typed cards under browser whitespace rules."""

    if len(rendered_rows) != len(payload_rows):
        return False
    structured = {str(slot).strip() for slot in structured_slots if str(slot).strip()}
    for rendered, expected in zip(rendered_rows, payload_rows, strict=True):
        if str(rendered.get("label") or "").strip().casefold() != str(
            expected.get("label") or ""
        ).strip().casefold():
            return False
        if str(rendered.get("semantic_slot") or "").strip() != str(
            expected.get("semantic_slot") or ""
        ).strip():
            return False
        semantic_slot = str(expected.get("semantic_slot") or "").strip()
        if semantic_slot in structured:
            continue
        if _browser_visible_text(rendered.get("body")) != _browser_visible_text(expected.get("body")):
            return False
    return True


def _browser_visible_text(value: Any) -> str:
    """Apply only HTML-visible whitespace collapse; retain every content token."""

    return " ".join(str(value or "").split())


def authored_structure_issues(rendered: Any, authored_facts: Any) -> tuple[str, ...]:
    """Require rendered authored nodes to preserve typed fact count, order, and text."""

    if not isinstance(rendered, dict) or not isinstance(authored_facts, dict):
        return ("browser surface project authored fact structure is unavailable",)

    raw_events = authored_facts.get("first_path_relations")
    if not isinstance(raw_events, (list, tuple)):
        return ("browser surface project payload has no typed first-path relations",)
    event_rows = [row for row in raw_events if isinstance(row, dict)]
    expected_events = [
        {"order": row.get("order"), "text": str(row.get("event_quote") or "").strip()}
        for row in event_rows
    ]
    issues: list[str] = []
    for surface in ("focus", "first_path"):
        actual = rendered.get(surface)
        if actual != expected_events:
            issues.append(
                f"browser surface project {surface.replace('_', ' ')} does not preserve typed event nodes"
            )

    raw_human_actors = authored_facts.get("human_actors")
    human_actors = (
        [
            str(actor).strip()
            for actor in raw_human_actors
            if isinstance(actor, str) and actor.strip()
        ]
        if isinstance(raw_human_actors, (list, tuple))
        else []
    )
    expected_actors = []
    for actor in human_actors:
        actor_events = [
            expected
            for expected, source in zip(expected_events, event_rows, strict=True)
            if source.get("actor_kind") == "human"
            and (source.get("actor_fact_quote") or source.get("actor_quote")) == actor
        ]
        if actor_events:
            expected_actors.append({"actor": actor, "events": actor_events})
    if rendered.get("actors") != expected_actors:
        issues.append("browser surface project actor cards do not preserve typed human event nodes")

    raw_capabilities = authored_facts.get("component_responsibility_relations")
    capability_rows = (
        [row for row in raw_capabilities if isinstance(row, dict)]
        if isinstance(raw_capabilities, (list, tuple))
        else []
    )
    expected_capabilities = [
        {
            "owner": str(row.get("owner_system_quote") or "").strip(),
            "responsibility": str(row.get("responsibility_quote") or "").strip(),
        }
        for row in capability_rows
    ]
    if rendered.get("capabilities") != expected_capabilities:
        issues.append("browser surface project capability rows do not preserve typed responsibility nodes")

    expected_boundary_groups = []
    for key, values in (
        ("product_owned_systems", authored_facts.get("internal_systems", ())),
        ("external_systems", authored_facts.get("external_systems", ())),
        ("non_goals", authored_facts.get("non_goals", ())),
    ):
        items = (
            [
                str(value).strip()
                for value in values
                if isinstance(value, str) and value.strip()
            ]
            if isinstance(values, (list, tuple))
            else []
        )
        if items:
            expected_boundary_groups.append({"key": key, "items": items})
    if rendered.get("boundary_groups") != expected_boundary_groups:
        issues.append("browser surface project boundary groups do not preserve typed fact nodes")
    return tuple(issues)


__all__ = ["authored_structure_issues", "story_rows_match_payload"]
