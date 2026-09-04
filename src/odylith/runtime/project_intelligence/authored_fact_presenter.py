"""Render validated Greenfield facts as structured Project-surface nodes."""

from __future__ import annotations

import html
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


RenderText = Callable[[object], str]


@dataclass(frozen=True)
class AuthoredEvent:
    order: int
    text: str
    actor_kind: str
    actor: str


@dataclass(frozen=True)
class AuthoredCapability:
    owner: str
    responsibility: str


@dataclass(frozen=True)
class AuthoredBoundaryGroup:
    key: str
    label: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class AuthoredFactView:
    events: tuple[AuthoredEvent, ...]
    capabilities: tuple[AuthoredCapability, ...]
    boundary_groups: tuple[AuthoredBoundaryGroup, ...]


def authored_fact_view(project: Mapping[str, Any]) -> AuthoredFactView | None:
    """Read only validated, already-typed Project facts; never interpret prose."""

    raw_facts = project.get("authored_facts")
    if not isinstance(raw_facts, Mapping):
        return None

    raw_events = raw_facts.get("first_path_relations")
    if not isinstance(raw_events, Sequence) or isinstance(raw_events, (str, bytes, bytearray)):
        return None
    events: list[AuthoredEvent] = []
    for expected_order, raw_event in enumerate(raw_events, start=1):
        if not isinstance(raw_event, Mapping):
            return None
        order = raw_event.get("order")
        text = raw_event.get("event_quote")
        actor_kind = raw_event.get("actor_kind")
        actor = raw_event.get("actor_fact_quote") or raw_event.get("actor_quote")
        if order != expected_order or not all(
            isinstance(value, str) and value.strip() for value in (text, actor_kind, actor)
        ):
            return None
        events.append(
            AuthoredEvent(
                order=expected_order,
                text=text.strip(),
                actor_kind=actor_kind.strip(),
                actor=actor.strip(),
            )
        )
    if not events:
        return None

    capabilities: list[AuthoredCapability] = []
    raw_capabilities = raw_facts.get("component_responsibility_relations")
    capability_rows = (
        raw_capabilities
        if isinstance(raw_capabilities, Sequence)
        and not isinstance(raw_capabilities, (str, bytes, bytearray))
        else ()
    )
    for raw_capability in capability_rows:
        if not isinstance(raw_capability, Mapping):
            continue
        owner = raw_capability.get("owner_system_quote")
        responsibility = raw_capability.get("responsibility_quote")
        if isinstance(owner, str) and owner.strip() and isinstance(responsibility, str) and responsibility.strip():
            capabilities.append(
                AuthoredCapability(
                    owner=owner.strip(),
                    responsibility=responsibility.strip(),
                )
            )

    product_owners = _authored_text_items(raw_facts.get("internal_systems"))
    external_systems = _authored_text_items(raw_facts.get("external_systems"))
    non_goals = _authored_text_items(raw_facts.get("non_goals"))
    boundary_groups = tuple(
        row
        for row in (
            AuthoredBoundaryGroup("product_owned_systems", "Product-owned systems", product_owners),
            AuthoredBoundaryGroup("external_systems", "External systems", external_systems),
            AuthoredBoundaryGroup("non_goals", "Excluded from the first release", non_goals),
        )
        if row.items
    )
    return AuthoredFactView(
        events=tuple(events),
        capabilities=tuple(capabilities),
        boundary_groups=boundary_groups,
    )


def render_authored_focus(project: Mapping[str, Any], *, render_text: RenderText) -> str:
    view = authored_fact_view(project)
    if view is None:
        return f"<h2>{render_text(project.get('focus'))}</h2>"
    items = "<br aria-hidden=\"true\">".join(
        f'<span data-authored-fact-item data-event-order="{event.order}">{render_text(event.text)}</span>'
        for event in view.events
    )
    return f'<h2 data-authored-fact-list="focus">{items}</h2>'


def render_authored_actor_cards(
    items: object,
    *,
    project: Mapping[str, Any],
    render_text: RenderText,
) -> str | None:
    view = authored_fact_view(project)
    if view is None:
        return None

    cards: list[str] = []
    for raw in _sequence_items(items):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        if len(item) < 2:
            continue
        kicker, title, body = (item[:3] + [""] * 3)[:3] if len(item) >= 3 else ("", item[0], item[1])
        actor = str(title or "").strip()
        if not actor:
            continue
        actor_events = tuple(
            event for event in view.events if event.actor_kind == "human" and event.actor == actor
        )
        kicker_html = f"<p>{render_text(kicker)}</p>" if str(kicker or "").strip() else ""
        body_html = (
            _event_list(actor_events, list_key="actor")
            if actor_events
            else f"<span>{render_text(body)}</span>"
        )
        cards.append(
            f'<article class="project-actor-card" data-authored-actor="{html.escape(actor, quote=True)}">'
            f"{kicker_html}<h3>{render_text(actor)}</h3>{body_html}</article>"
        )
    return "".join(cards)


def render_product_story_contract(
    rows: Sequence[Mapping[str, Any]],
    *,
    project: Mapping[str, Any],
    render_text: RenderText,
) -> str:
    view = authored_fact_view(project)
    items = [
        (
            str(row.get("label") or "").strip(),
            str(row.get("body") or "").strip(),
            str(row.get("semantic_slot") or "").strip(),
        )
        for row in rows
        if str(row.get("label") or row.get("body") or "").strip()
    ]
    if not items:
        return ""

    cells: list[str] = []
    for label, body, semantic_slot in items:
        structured_body = _structured_story_body(
            semantic_slot=semantic_slot,
            view=view,
            render_text=render_text,
        )
        body_html = structured_body or f'<p class="project-story-contract-body">{render_text(body)}</p>'
        cells.append(
            '<article class="project-story-contract-card" role="listitem" '
            f'data-semantic-slot="{html.escape(semantic_slot, quote=True)}">'
            f"<h3>{render_text(label)}</h3>{body_html}</article>"
        )
    return f'<div class="project-story-contract" role="list">{"".join(cells)}</div>'


def _structured_story_body(
    *,
    semantic_slot: str,
    view: AuthoredFactView | None,
    render_text: RenderText,
) -> str:
    if view is None:
        return ""
    if semantic_slot == "first_path":
        return _event_list(view.events, list_key="first_path", contract_body=True)
    if semantic_slot == "owned_capabilities" and view.capabilities:
        rows = "".join(
            '<li data-authored-fact-item>'
            f'<strong data-authored-owner>{render_text(item.owner)}</strong>: '
            f'<span data-authored-responsibility>{render_text(item.responsibility)}</span>'
            "</li>"
            for item in view.capabilities
        )
        return (
            '<ul class="project-story-records project-story-contract-body project-authored-fact-list" '
            f'data-authored-fact-list="owned_capabilities">{rows}</ul>'
        )
    if semantic_slot == "product_boundary" and view.boundary_groups:
        groups = "".join(
            '<section data-authored-boundary-group '
            f'data-boundary-kind="{html.escape(group.key, quote=True)}">'
            f"<strong>{render_text(group.label)}:</strong>"
            '<ul class="project-story-records">'
            + "".join(f"<li data-authored-fact-item>{render_text(item)}</li>" for item in group.items)
            + "</ul></section>"
            for group in view.boundary_groups
        )
        return f'<div class="project-story-contract-body" data-authored-boundary>{groups}</div>'
    return ""


def _event_list(
    events: Sequence[AuthoredEvent],
    *,
    list_key: str,
    contract_body: bool = False,
) -> str:
    classes = ["project-story-records", "project-authored-fact-list"]
    if contract_body:
        classes.append("project-story-contract-body")
    rows = "".join(
        f'<li data-authored-fact-item data-event-order="{event.order}">{html.escape(event.text)}</li>'
        for event in events
    )
    return (
        f'<ol class="{" ".join(classes)}" data-authored-fact-list="{html.escape(list_key, quote=True)}">'
        f"{rows}</ol>"
    )


def _authored_text_items(value: object) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in _sequence_items(value)
        if isinstance(item, str) and item.strip()
    )


def _sequence_items(value: object) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else ()


__all__ = [
    "AuthoredBoundaryGroup",
    "AuthoredCapability",
    "AuthoredEvent",
    "AuthoredFactView",
    "authored_fact_view",
    "render_authored_actor_cards",
    "render_authored_focus",
    "render_product_story_contract",
]
