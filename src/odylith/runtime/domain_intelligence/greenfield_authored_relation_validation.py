"""Validate source-bound Greenfield authored actors and events."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    event_target_is_source_bound,
    intent_text_at_path,
    intent_text_rows,
)


FIRST_PATH_RELATION_FIELDS = frozenset(
    {
        "order",
        "source_start_byte",
        "source_end_byte",
        "event_start_byte",
        "event_end_byte",
        "actor_kind",
        "actor_fact_path",
        "actor_fact_quote",
        "owner_system_path",
        "owner_system_quote",
        "event_quote",
        "action_verb_quote",
        "target_quote",
        "visible_result_quote",
    }
)
FIRST_PATH_ACTOR_KINDS = ("human", "product", "external_system", "product_wide")
MAX_FIRST_PATH_RELATIONS = 24
MAX_SOURCE_EVENT_RELATIONS = 32


class GreenfieldAuthoredSemanticsError(ValueError):
    """The model's typed relations are not grounded in accepted source facts."""


def validate_first_path_relations(
    value: Any,
    *,
    first_path: str,
    human_actors: Sequence[str],
    external_systems: Sequence[str] = (),
    internal_systems: Sequence[str] = (),
    product_title: str = "",
    terminal_result_facts: Sequence[str] = (),
    require_visible_result: bool = True,
    intent: Mapping[str, Any] | None = None,
    first_path_event_orders: Sequence[int] | None = None,
    source_event_graph: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Return stable source-event identities, not an inferred execution order."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or len(value) > (MAX_SOURCE_EVENT_RELATIONS if source_event_graph else MAX_FIRST_PATH_RELATIONS)
        or (source_event_graph and first_path_event_orders is None and len(value) > MAX_FIRST_PATH_RELATIONS)
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    path = str(first_path or "")
    visible_result_facts = (path, *map(str, terminal_result_facts))
    owner_values = canonical_product_owner_projection_values(
        title=product_title,
        internal_systems=internal_systems,
    )
    actor_values = _actor_projection_values(
        title=product_title,
        human_actors=human_actors,
        external_systems=external_systems,
        internal_systems=internal_systems,
    )
    rows: list[dict[str, Any]] = []
    path_bytes = path.encode("utf-8")
    selected_orders = (
        frozenset(first_path_event_orders)
        if first_path_event_orders is not None else None
    )
    if selected_orders is not None and (
        not selected_orders
        or len(selected_orders) > MAX_FIRST_PATH_RELATIONS
        or len(first_path_event_orders) != len(selected_orders)
        or any(type(order) is not int or not 1 <= order <= len(value)
               for order in selected_orders)
        or intent is None
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield first-path event role binding is malformed"
        )
    supporting_index = 0
    cursor = 0
    visible_seen = False
    seen_source_events: set[tuple[int, int]] = set()
    seen_projection_events: set[tuple[str, int, int]] = set()
    seen_typed_events: set[tuple[Any, ...]] = set()
    last_projection_event: tuple[int, int] | None = None
    for expected_order, raw in enumerate(value, start=1):
        if selected_orders is None or expected_order in selected_orders:
            projection_path = "/first_path"
            event_path_bytes = path_bytes
        else:
            projection_path = f"/supporting_events/{supporting_index}"
            supporting_index += 1
            event_path_bytes = intent_text_at_path(intent, projection_path).encode("utf-8")
        if not isinstance(raw, Mapping) or set(raw) != FIRST_PATH_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path relations"
            )
        order = raw.get("order")
        source_start = raw.get("source_start_byte")
        source_end = raw.get("source_end_byte")
        event_start = raw.get("event_start_byte")
        event_end = raw.get("event_end_byte")
        actor_kind = str(raw.get("actor_kind") or "")
        actor_fact_path = str(raw.get("actor_fact_path") or "")
        actor_fact_quote = str(raw.get("actor_fact_quote") or "")
        owner_system_path = str(raw.get("owner_system_path") or "")
        owner_system_quote = str(raw.get("owner_system_quote") or "")
        event_quote = str(raw.get("event_quote") or "")
        action_verb_quote = str(raw.get("action_verb_quote") or "")
        target_quote = str(raw.get("target_quote") or "")
        visible_result_quote = str(raw.get("visible_result_quote") or "")
        typed_event = (
            source_start,
            source_end,
            event_start,
            event_end,
            actor_kind,
            actor_fact_path,
            action_verb_quote,
            target_quote,
        )
        if (
            order != expected_order
            or not isinstance(source_start, int)
            or isinstance(source_start, bool)
            or not isinstance(source_end, int)
            or isinstance(source_end, bool)
            or source_start < 0
            or source_end <= source_start
            or not isinstance(event_start, int)
            or isinstance(event_start, bool)
            or not isinstance(event_end, int)
            or isinstance(event_end, bool)
            or (
                projection_path == "/first_path" and
                event_start < cursor
                and (event_start, event_end) != last_projection_event
            )
            or event_end <= event_start
            or event_end > len(event_path_bytes)
            or actor_kind not in FIRST_PATH_ACTOR_KINDS
            or not event_quote
            or _nonidentical_overlap(source_start, source_end, seen_source_events)
            or _nonidentical_overlap(
                event_start, event_end,
                {(start, end) for path_key, start, end in seen_projection_events
                 if path_key == projection_path},
            )
            or typed_event in seen_typed_events
            or not action_verb_quote
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path relations"
            )
        if actor_kind == "product_wide":
            # Full source-role/citation parity is verified against the authenticated
            # ledger by the shared authored reader, never inferred from a title.
            if intent is None or actor_fact_path != "/product_identity" or not actor_fact_quote or owner_system_path or owner_system_quote:
                raise GreenfieldAuthoredSemanticsError("invalid product-wide source performer binding")
        else:
            require_first_path_actor_binding(
                actor_kind=actor_kind,
                actor_fact_path=actor_fact_path,
                actor_fact_quote=actor_fact_quote,
                owner_system_path=owner_system_path,
                owner_system_quote=owner_system_quote,
                actor_values=actor_values,
                owner_values=owner_values,
            )
        if (
            event_path_bytes[event_start:event_end] != event_quote.encode("utf-8")
            or action_verb_quote not in event_quote
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned ungrounded first-path relations"
            )
        if not event_target_is_source_bound(
            event_quote=event_quote,
            target_quote=target_quote,
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned ungrounded first-path relations"
            )
        if visible_result_quote and not any(
            visible_result_quote in fact for fact in visible_result_facts if fact
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned ungrounded first-path relations"
            )
        if visible_result_quote:
            if visible_seen:
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring returned an invalid terminal visible result"
                )
            visible_seen = True
        seen_source_events.add((source_start, source_end))
        seen_projection_events.add((projection_path, event_start, event_end))
        seen_typed_events.add(typed_event)
        if projection_path == "/first_path":
            last_projection_event = (event_start, event_end)
            cursor = max(cursor, event_end)
        rows.append(
            {
                "order": order,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": event_start,
                "event_end_byte": event_end,
                "actor_kind": actor_kind,
                "actor_fact_path": actor_fact_path,
                "actor_fact_quote": actor_fact_quote,
                "owner_system_path": owner_system_path,
                "owner_system_quote": owner_system_quote,
                "event_quote": event_quote,
                "action_verb_quote": action_verb_quote,
                "target_quote": target_quote,
                "visible_result_quote": visible_result_quote,
            }
        )
    if require_visible_result and not visible_seen:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring did not type a path with a visible result"
        )
    if selected_orders is not None and supporting_index != len(intent_text_rows(intent.get("supporting_events"))):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield supporting events do not match source role bindings"
        )
    return tuple(rows)


def canonical_product_owner_projection_values(
    *,
    title: str,
    internal_systems: Sequence[str],
) -> dict[str, str]:
    """Resolve a title alias to one system while rejecting duplicate systems."""

    values: dict[str, str] = {}
    quote_paths: dict[str, str] = {}
    owner_rows = [
        (f"/internal_systems/{index}", str(value))
        for index, value in enumerate(internal_systems)
    ]
    owner_rows.append(("/title", str(title or "")))
    for path, quote in owner_rows:
        if not quote:
            continue
        existing_path = quote_paths.get(quote)
        if existing_path is not None and existing_path != path:
            if path == "/title" and existing_path.startswith("/internal_systems/"):
                continue
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored semantics contain duplicate labels for distinct product owners"
            )
        quote_paths[quote] = path
        values[path] = quote
    return values


def require_first_path_actor_binding(
    *,
    actor_kind: str,
    actor_fact_path: str,
    actor_fact_quote: str,
    owner_system_path: str,
    owner_system_quote: str,
    actor_values: Mapping[str, tuple[str, str]],
    owner_values: Mapping[str, str],
) -> None:
    """Bind an event actor to one explicit selected entity fact."""

    if actor_values.get(actor_fact_path) != (actor_kind, actor_fact_quote):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound first-path actor fact"
        )
    if actor_kind != "product":
        if owner_system_path or owner_system_quote:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an owner for a non-product event"
            )
        return
    if (
        owner_system_path != actor_fact_path
        or owner_system_quote != actor_fact_quote
        or owner_values.get(owner_system_path) != owner_system_quote
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned a product event owner that does not match its typed actor"
        )


def _actor_projection_values(
    *,
    title: str,
    human_actors: Sequence[str],
    external_systems: Sequence[str],
    internal_systems: Sequence[str],
) -> dict[str, tuple[str, str]]:
    values: dict[str, tuple[str, str]] = {}
    for kind, field, rows in (
        ("human", "human_actors", human_actors),
        ("external_system", "external_systems", external_systems),
        ("product", "internal_systems", internal_systems),
    ):
        for index, value in enumerate(rows):
            quote = str(value)
            if quote:
                values[f"/{field}/{index}"] = (kind, quote)
    if title:
        values["/title"] = ("product", str(title))
    return values


def _nonidentical_overlap(
    start: int,
    end: int,
    accepted: set[tuple[int, int]],
) -> bool:
    return any(
        start < accepted_end
        and accepted_start < end
        and (start, end) != (accepted_start, accepted_end)
        for accepted_start, accepted_end in accepted
    )


__all__ = [
    "FIRST_PATH_ACTOR_KINDS",
    "FIRST_PATH_RELATION_FIELDS",
    "GreenfieldAuthoredSemanticsError",
    "MAX_FIRST_PATH_RELATIONS",
    "MAX_SOURCE_EVENT_RELATIONS",
    "canonical_product_owner_projection_values",
    "require_first_path_actor_binding",
    "validate_first_path_relations",
]
