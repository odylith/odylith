"""Render validated Greenfield facts as structured Project-surface nodes."""

from __future__ import annotations

import html
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_first_run import (
    AuthoredEventPresentation,
    authored_event_presentation,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_event_ordering import (
    validate_source_precedence,
)
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    provisional_proof_assumption,
    require_provisional_proof_decision,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    validate_provisional_design,
)

RenderText = Callable[[object], str]


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
    events: tuple[AuthoredEventPresentation, ...]
    capabilities: tuple[AuthoredCapability, ...]
    boundary_groups: tuple[AuthoredBoundaryGroup, ...]


def authored_fact_view(project: Mapping[str, Any]) -> AuthoredFactView | None:
    """Read only validated, already-typed Project facts; never interpret prose."""

    if "authored_facts" not in project:
        return None
    raw_facts = project["authored_facts"]
    if not isinstance(raw_facts, Mapping):
        raise GreenfieldAuthoredSemanticsError("Project authored facts are malformed")

    fresh = raw_facts.get("authored_semantics_version") == "odylith.greenfield.authored-semantics.v19"
    raw_events = raw_facts.get("source_event_relations" if fresh else "first_path_relations")
    if not isinstance(raw_events, Sequence) or isinstance(raw_events, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError("Project authored event inventory is malformed")
    events: list[AuthoredEventPresentation] = []
    result_orders: list[int] = []
    for expected_order, raw_event in enumerate(raw_events, start=1):
        if not isinstance(raw_event, Mapping):
            raise GreenfieldAuthoredSemanticsError("Project authored event inventory is malformed")
        order = raw_event.get("order")
        text = raw_event.get("event_quote")
        actor_kind = raw_event.get("actor_kind")
        actor = raw_event.get("actor_fact_quote")
        result = raw_event.get("visible_result_quote")
        if type(order) is not int or order != expected_order or not isinstance(result, str) or not all(
            isinstance(value, str) and value.strip() for value in (text, actor_kind, actor)
        ):
            raise GreenfieldAuthoredSemanticsError("Project authored event inventory is malformed")
        if result:
            result_orders.append(order)
        try:
            events.append(authored_event_presentation(raw_event))
        except ValueError as exc:
            raise GreenfieldAuthoredSemanticsError(str(exc)) from exc
    if not events or len(result_orders) > 1:
        raise GreenfieldAuthoredSemanticsError(
            "Project authored events require at most one explicit source result"
        )
    try:
        proof_assumption = provisional_proof_assumption(raw_facts.get("assumptions", []))
    except ValueError as exc:
        raise GreenfieldAuthoredSemanticsError(str(exc)) from exc
    if result_orders and proof_assumption:
        raise GreenfieldAuthoredSemanticsError(
            "Project authored proof cannot mix a source result with a proof assumption"
        )
    if not result_orders:
        try:
            require_provisional_proof_decision(raw_facts)
        except ValueError as exc:
            raise GreenfieldAuthoredSemanticsError(str(exc)) from exc
        if raw_facts.get("proof_boundary") or not proof_assumption:
            raise GreenfieldAuthoredSemanticsError(
                "Project authored events without a source result require one proof assumption"
            )

    try:
        source_precedence = validate_source_precedence(
            raw_facts.get("source_precedence"),
            event_orders=tuple(event.order for event in events),
            operational_constraints=raw_facts.get("operational_constraints"),
        )
        design = validate_provisional_design(
            raw_facts.get("provisional_design"), event_orders=tuple(event.order for event in events),
            source_precedence=source_precedence,
            result_event_order=result_orders[0] if result_orders else None,
        )
    except ValueError as exc:
        raise GreenfieldAuthoredSemanticsError(str(exc)) from exc
    events_by_order = {event.order: event for event in events}
    capabilities = tuple(
        AuthoredCapability(owner=row["name"], responsibility=row["responsibility"])
        for row in design["components"]
    )
    proposed_components = tuple(row["name"] for row in design["components"])
    external_systems = _authored_text_items(raw_facts.get("external_systems"))
    non_goals = _authored_text_items(raw_facts.get("non_goals"))
    boundary_groups = tuple(
        row
        for row in (
            AuthoredBoundaryGroup(
                "provisional_components", "Proposed components",
                proposed_components,
            ),
            AuthoredBoundaryGroup(
                "source_product_systems", "Named systems",
                _authored_text_items(raw_facts.get("internal_systems")),
            ),
            AuthoredBoundaryGroup("external_systems", "External systems", external_systems),
            AuthoredBoundaryGroup("non_goals", "Scope limits", non_goals),
        )
        if row.items
    )
    return AuthoredFactView(
        events=tuple(events_by_order[order] for order in design["first_run"]["event_orders"]),
        capabilities=capabilities,
        boundary_groups=boundary_groups,
    )


def render_authored_risk_cards(items: object, *, render_text: RenderText) -> str:
    cards: list[str] = []
    for row in _sequence_items(items):
        if not isinstance(row, Mapping):
            continue
        statement = row.get("statement") or row.get("meaning")
        heading = "" if row.get("category") else f'<h3>{render_text(row.get("risk"))}</h3>'
        statement_tag = "h3" if row.get("category") else "p"
        mitigation = row.get("mitigation")
        mitigation_html = (
            '<div class="project-risk-mitigation"><h4>Mitigation</h4>'
            f'<p data-risk-mitigation>{render_text(mitigation)}</p></div>'
            if mitigation else ""
        )
        fields = (
            f'<dt>Proposed category</dt><dd>{render_text(row.get("risk"))}</dd>'
            if row.get("category") else ""
        ) + "".join(
            f'<dt>{label}</dt><dd>{render_text(row[key])}</dd>'
            for key, label in (("trigger", "When this applies"), ("verification", "Verification"),
                               ("scope", "Scope"))
            if row.get(key)
        )
        paths = "".join(
            '<li>' + render_text(
                f"Source event {path['event_order']} · Component {path['component_key']} · "
                f"Workstream {path['workstream_key']}"
            ) + '</li>'
            for path in _sequence_items(row.get("scope_paths"))
        )
        if paths:
            fields += f'<dt>Traceability</dt><dd><ul>{paths}</ul></dd>'
        details = (
            '<details class="project-risk-details"><summary>Risk details</summary>'
            f'<dl>{fields}</dl></details>' if fields else ""
        )
        cards.append(
            '<article class="project-risk-card" data-authority-kind="provisional_design" '
            f'data-risk-key="{html.escape(str(row.get("key") or ""), quote=True)}">'
            f'{heading}'
            f'<{statement_tag} class="project-risk-statement" data-risk-statement>{render_text(statement)}</{statement_tag}>'
            f'{mitigation_html}{details}</article>'
        )
    return "".join(cards)


def render_authored_actor_cards(
    items: object,
    *,
    project: Mapping[str, Any],
    render_text: RenderText,
) -> str | None:
    if authored_fact_view(project) is None:
        return None

    cards: list[str] = []
    for raw in _sequence_items(items):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        if len(item) < 2:
            continue
        title = item[1] if len(item) >= 3 else item[0]
        actor = str(title or "").strip()
        if actor:
            cards.append(
                f'<article class="project-actor-card project-actor-card-name" data-authored-actor="{html.escape(actor, quote=True)}">'
                f"<h3>{render_text(actor)}</h3></article>"
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
        heading_marker = " data-provisional-design-label" if view is not None and semantic_slot == "owned_capabilities" else ""
        cells.append(
            '<article class="project-story-contract-card" role="listitem" '
            f'data-semantic-slot="{html.escape(semantic_slot, quote=True)}">'
            f"<h3{heading_marker}>{render_text(label)}</h3>{body_html}</article>"
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
        return (
            '<div class="project-story-contract-body">'
            '<p data-proposed-first-run-label>Proposed first run:</p>'
            f'{_event_list(view.events, list_key="first_path", render_text=render_text)}</div>'
        )
    if semantic_slot == "owned_capabilities" and view.capabilities:
        rows = "".join(
            '<li data-authored-fact-item>'
            f'<strong data-authored-owner>{render_text(item.owner)}</strong>: '
            f'<span data-authored-responsibility>{render_text(item.responsibility)}</span>'
            "</li>"
            for item in view.capabilities
        )
        return (
            '<div class="project-story-contract-body">'
            '<ul class="project-story-records project-authored-fact-list" '
            'data-authored-fact-list="owned_capabilities" data-authority-kind="provisional_design">'
            f'{rows}</ul></div>'
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
    events: Sequence[AuthoredEventPresentation],
    *,
    list_key: str,
    render_text: RenderText,
) -> str:
    rows = "".join(
        f'<li data-authored-fact-item data-event-order="{event.order}">'
        f'<span data-authored-event-quote>{render_text(event.event_quote)}</span></li>'
        for event in events
    )
    evidence = "".join(
        f'<li data-authored-event-evidence data-event-order="{event.order}"><dl>'
        '<dt>Actor</dt>'
        f'<dd data-authored-event-actor-value>{render_text(event.actor_label)}</dd>'
        f'<dt>Actor kind</dt><dd>{render_text(event.actor_kind)}</dd>'
        f'<dt>Source event</dt><dd>{render_text(event.event_quote)}</dd>'
        '</dl></li>'
        for event in events
    )
    return (
        '<ol class="project-story-records project-authored-fact-list" '
        f'data-authored-fact-list="{html.escape(list_key, quote=True)}" '
        'data-authority-kind="provisional_design">'
        f'{rows}</ol><details data-authored-event-details>'
        '<summary>Supporting details</summary><ol class="project-story-records">'
        f'{evidence}</ol></details>'
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
    "AuthoredFactView",
    "authored_fact_view",
    "render_authored_actor_cards",
    "render_authored_risk_cards",
    "render_product_story_contract",
]
