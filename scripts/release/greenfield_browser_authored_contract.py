"""Browser contract for exact structured Greenfield authored facts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse


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


def atlas_state_assertion_issues(
    *,
    diagram_count: int,
    stat_total_text: str,
    active_diagram: str,
    displayed_diagram: str,
    displayed_title: str,
    image_src: str,
    image_loaded: bool,
) -> tuple[str, ...]:
    """Require one selected Atlas item to be a loaded generated diagram."""

    issues: list[str] = []
    if diagram_count <= 0:
        issues.append("browser surface atlas rendered no generated diagram buttons")
    try:
        stat_total = max(0, int(str(stat_total_text or "").strip()))
    except ValueError:
        stat_total = 0
    if stat_total <= 0:
        issues.append("browser surface atlas rendered no generated diagram count")
    elif diagram_count > 0 and stat_total != diagram_count:
        issues.append("browser surface atlas generated diagram count disagrees with rendered list")
    active = str(active_diagram or "").strip()
    displayed = str(displayed_diagram or "").strip()
    if not active:
        issues.append("browser surface atlas has no active generated diagram")
    if not displayed:
        issues.append("browser surface atlas did not hydrate the selected diagram id")
    elif active and displayed.upper() != active.upper():
        issues.append("browser surface atlas selected diagram id disagrees with active list state")
    if len(str(displayed_title or "").strip().split()) < 2:
        issues.append("browser surface atlas did not hydrate a meaningful generated diagram title")
    parsed = urlparse(str(image_src or ""))
    if "/odylith/atlas/source/" not in (parsed.path or "") or not (parsed.path or "").endswith(
        (".svg", ".png")
    ):
        issues.append("browser surface atlas viewer did not load a generated diagram asset")
    if not image_loaded:
        issues.append("browser surface atlas generated diagram asset did not finish loading")
    return tuple(issues)


def atlas_diagram_coverage_issues(
    expected_diagrams: Iterable[str],
    visited_diagrams: Iterable[str],
) -> tuple[str, ...]:
    expected = tuple(str(value or "").strip() for value in expected_diagrams)
    visited = tuple(str(value or "").strip() for value in visited_diagrams)
    if expected and expected == visited and all(expected):
        return ()
    return ("browser surface atlas did not visit every emitted diagram in list order",)


def atlas_degraded_state_assertion_issues(
    *,
    image_src: str,
    image_loaded: bool,
    fallback_applied: bool,
) -> tuple[str, ...]:
    parsed = urlparse(str(image_src or ""))
    if (
        image_loaded
        and fallback_applied
        and "/odylith/atlas/source/" in (parsed.path or "")
        and (parsed.path or "").endswith(".png")
    ):
        return ()
    return ("browser surface atlas degraded SVG did not recover with its readable PNG asset",)


def atlas_error_state_assertion_issues(
    *,
    alert_text: str,
    alert_role: str,
    alert_visible: bool,
    image_hidden: bool,
) -> tuple[str, ...]:
    expected_actions = ("prev", "next", "summary", "source links")
    normalized = str(alert_text or "").strip().casefold()
    if (
        alert_visible
        and image_hidden
        and str(alert_role or "").strip().casefold() == "alert"
        and all(action in normalized for action in expected_actions)
    ):
        return ()
    return ("browser surface atlas asset failure does not expose accessible recovery guidance",)


__all__ = [
    "atlas_degraded_state_assertion_issues",
    "atlas_diagram_coverage_issues",
    "atlas_error_state_assertion_issues",
    "atlas_state_assertion_issues",
    "authored_structure_issues",
    "story_rows_match_payload",
]
