"""Browser contract for exact structured Greenfield authored facts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from odylith.runtime.domain_intelligence.greenfield_event_ordering import validate_source_precedence
from odylith.runtime.domain_intelligence.greenfield_provisional_design import validate_provisional_design


AUTHORED_STRUCTURE_EXPRESSION = """(node) => {
  const visibleText = (item) => item?.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})
    ? String(item.innerText || "").trim() : "";
  const eventRows = (selector) => Array.from(node.querySelectorAll(selector)).map((item) => ({
    order: Number(item.dataset.eventOrder || "0"), text: visibleText(item)
  }));
  const focus = node.querySelector('[data-authored-fact-list="focus"]');
  const firstPath = node.querySelector('[data-authored-fact-list="first_path"]');
  const capabilities = node.querySelector('[data-authored-fact-list="owned_capabilities"]');
  return {
    focus: eventRows('[data-authored-fact-list="focus"] [data-authored-fact-item]'),
    first_path: eventRows('[data-authored-fact-list="first_path"] [data-authored-fact-item]'),
    focus_authority: String(focus?.dataset.authorityKind || ""),
    focus_label: visibleText(focus?.querySelector('[data-proposed-first-run-label]')),
    first_path_authority: String(firstPath?.dataset.authorityKind || ""),
    first_path_label: visibleText(firstPath?.closest('[data-semantic-slot="first_path"]')
      ?.querySelector('[data-proposed-first-run-label]')),
    actors: Array.from(node.querySelectorAll("[data-authored-actor]")).map((card) => ({
      actor: String(card.dataset.authoredActor || "").trim(),
      events: Array.from(card.querySelectorAll('[data-authored-fact-list="actor"] [data-authored-fact-item]'))
        .map((item) => ({order: Number(item.dataset.eventOrder || "0"), text: visibleText(item)}))
    })).filter((row) => row.events.length),
    capabilities_authority: String(capabilities?.dataset.authorityKind || ""),
    capabilities_label: visibleText(node.querySelector('[data-provisional-design-label]')),
    capabilities: Array.from(capabilities?.querySelectorAll('[data-authored-fact-item]') || []).map((item) => ({
      owner: String(item.querySelector("[data-authored-owner]")?.innerText || "").trim(),
      responsibility: String(item.querySelector("[data-authored-responsibility]")?.innerText || "").trim()
    })),
    boundary_groups: Array.from(node.querySelectorAll("[data-authored-boundary-group]")).map((group) => ({
      key: String(group.dataset.boundaryKind || "").trim(),
      label: String(group.querySelector(":scope > strong")?.innerText || "").trim(),
      items: Array.from(group.querySelectorAll("[data-authored-fact-item]"))
        .map((item) => String(item.innerText || "").trim())
    })),
    deliveries: Array.from(node.querySelectorAll(".project-job-card")).map((card) => ({
      title: String(card.querySelector("h3")?.innerText || "").trim(),
      deliverable: String(card.querySelector(":scope > p")?.innerText || "").trim()
    }))
  };
}"""


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
    if not raw_events or any(
        not isinstance(row, dict)
        or not isinstance(row.get("event_quote"), str) or not row["event_quote"].strip()
        or not isinstance(row.get("visible_result_quote"), str)
        for row in raw_events
    ):
        return ("browser surface project has invalid canonical source events",)
    event_orders = tuple(row.get("order") for row in raw_events)
    result_orders = [row.get("order") for row in raw_events if row["visible_result_quote"]]
    if len(result_orders) != 1:
        return ("browser surface project has invalid canonical result-event binding",)
    try:
        source_precedence = validate_source_precedence(
            authored_facts.get("source_precedence"), event_orders=event_orders,
            operational_constraints=authored_facts.get("operational_constraints"),
        )
        design = validate_provisional_design(
            authored_facts.get("provisional_design"), event_orders=event_orders,
            source_precedence=source_precedence, result_event_order=result_orders[0],
        )
    except ValueError as exc:
        return (f"browser surface project has invalid canonical provisional design: {exc}",)
    events_by_order = {row["order"]: row for row in raw_events}
    event_rows = [events_by_order[order] for order in design["first_run"]["event_orders"]]
    expected_events = [
        {"order": row["order"], "text": _browser_visible_text(row["event_quote"])}
        for row in event_rows
    ]
    issues: list[str] = []
    for surface in ("focus", "first_path"):
        actual = rendered.get(surface)
        if actual != expected_events:
            issues.append(
                f"browser surface project {surface.replace('_', ' ')} does not preserve typed event nodes"
            )
        if (
            rendered.get(f"{surface}_authority") != "provisional_design"
            or rendered.get(f"{surface}_label") != "Proposed first run:"
        ):
            issues.append(
                f"browser surface project {surface.replace('_', ' ')} lost its explicit proposed-first-run marker"
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
            and source.get("actor_fact_quote") == actor
        ]
        if actor_events:
            expected_actors.append({"actor": actor, "events": actor_events})
    if rendered.get("actors") != expected_actors:
        issues.append("browser surface project actor cards do not preserve typed human event nodes")

    expected_capabilities = [
        {
            "owner": _browser_visible_text(row["name"]),
            "responsibility": _browser_visible_text(row["responsibility"]),
        }
        for row in design["components"]
    ]
    if rendered.get("capabilities") != expected_capabilities:
        issues.append("browser surface project capability rows do not preserve canonical proposed responsibilities")
    if (
        rendered.get("capabilities_authority") != "provisional_design"
        or rendered.get("capabilities_label") != "Proposed capabilities:"
    ):
        issues.append("browser surface project capabilities lost their explicit proposed-design marker")

    expected_boundary_groups = [{
        "key": "provisional_components",
        "label": "Proposed logical components (not deployment commitments):",
        "items": [_browser_visible_text(row["name"]) for row in design["components"]],
    }]
    for key, label, values in (
        ("source_product_systems", "Source-stated systems:", authored_facts.get("internal_systems", ())),
        ("external_systems", "External systems:", authored_facts.get("external_systems", ())),
        ("non_goals", "Excluded from the first release:", authored_facts.get("non_goals", ())),
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
            expected_boundary_groups.append({"key": key, "label": label, "items": items})
    if rendered.get("boundary_groups") != expected_boundary_groups:
        issues.append("browser surface project boundary groups conflate or alter proposed design and source context")
    expected_deliveries = [
        {"title": _browser_visible_text(row["title"]), "deliverable": _browser_visible_text(row["deliverable"])}
        for row in design["workstreams"]
    ]
    if rendered.get("deliveries") != expected_deliveries:
        issues.append("browser surface project delivery cards do not preserve canonical proposed deliverables")
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
    "AUTHORED_STRUCTURE_EXPRESSION",
    "atlas_degraded_state_assertion_issues",
    "atlas_diagram_coverage_issues",
    "atlas_error_state_assertion_issues",
    "atlas_state_assertion_issues",
    "authored_structure_issues",
    "story_rows_match_payload",
]
