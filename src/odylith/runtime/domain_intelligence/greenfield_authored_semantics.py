"""Closed source-grounded semantic relations from Greenfield model authoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    event_target_is_source_bound,
    intent_terminal_result_values,
    intent_text_at_path,
    intent_text_rows,
)
from odylith.runtime.governance.artifact_tribunal import _bind_verified_source_custody

AUTHORED_SEMANTICS_KEY = "authored_semantics"
AUTHORED_SEMANTICS_VERSION = "odylith.greenfield.authored-semantics.v12"
AUTHORED_RELATION_SET_SHA256_KEY = "authored_relation_set_sha256"
AUTHORED_PROJECTION_ORIGIN = "model_authored_typed_intent"
AUTHORED_SEMANTIC_ROOT = f"intent.{AUTHORED_SEMANTICS_KEY}"
GREENFIELD_PRECONFIRM_STAGING_MARKER = "<!-- odylith:preconfirm-staging -->"
ATOMIC_FACT_CATEGORIES = (
    "actors",
    "actions",
    "states",
    "outputs",
    "constraints",
    "dependencies",
    "assumptions",
    "ambiguities",
    "non_goals",
)
ATOMIC_POLARITIES = ("affirmed", "required", "prohibited")
AUTHORED_RELATION_ROLES = (
    "actor_quote",
    "action_verb_quote",
    "target_quote",
    "visible_result_quote",
)
FIRST_PATH_RELATION_FIELDS = frozenset(
    {
        "order",
        "source_start_byte",
        "source_end_byte",
        "event_start_byte",
        "event_end_byte",
        "actor_kind",
        "actor_quote",
        "actor_is_carried",
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
FIRST_PATH_CONTEXT_RELATION_FIELDS = frozenset(
    {
        "context_kind",
        "fact_path",
        "fact_quote",
        "source_start_byte",
        "source_end_byte",
        "first_path_event_order",
    }
)
COMPONENT_RESPONSIBILITY_RELATION_FIELDS = frozenset(
    {
        "responsibility_path",
        "responsibility_quote",
        "owner_system_path",
        "owner_system_quote",
        "first_path_event_order",
        "responsibility_source",
    }
)
FIRST_PATH_ACTOR_KINDS = ("human", "product", "external_system")
FIRST_PATH_CONTEXT_KINDS = (
    "state_object",
    "external_system",
    "operational_constraint",
)
COMPONENT_RESPONSIBILITY_SOURCES = ("accepted_fact", "terminal_visible_result")
MAX_FIRST_PATH_RELATIONS = 24
MAX_COMPONENT_RESPONSIBILITY_RELATIONS = 32
FIRST_PATH_ACTOR_BINDING_FIELDS = (
    "actor_kind", "actor_fact_path", "actor_fact_quote",
    "owner_system_path", "owner_system_quote",
)


class GreenfieldAuthoredSemanticsError(ValueError):
    """The model's typed relations are not grounded in accepted source facts."""


def first_path_actor_binding_identity(value: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the exact typed entity and owner binding carried between events."""
    return tuple(str(value.get(field) or "") for field in FIRST_PATH_ACTOR_BINDING_FIELDS)


def combined_prompt_evidence_source(*, prompt: str, edit_evidence: str) -> str:
    """Return the exact, versioned byte frame presented to model authoring."""

    rows = [GREENFIELD_PRECONFIRM_STAGING_MARKER, "", "# Operator prompt evidence", "", prompt.strip()]
    if edit_evidence:
        rows.extend(("", "# Operator edit evidence", "", edit_evidence.strip()))
    return "\n".join(rows).rstrip() + "\n"


def validate_first_path_relations(
    value: Any,
    *,
    first_path: str,
    human_actors: Sequence[str],
    external_systems: Sequence[str] = (),
    internal_systems: Sequence[str] = (),
    product_title: str = "",
    terminal_result_facts: Sequence[str] = (),
) -> tuple[dict[str, Any], ...]:
    """Return ordered relations whose quoted parts are exact first-path bytes."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or len(value) > MAX_FIRST_PATH_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned invalid first-path relations")
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
    cursor = 0
    visible_seen = False
    seen_source_events: set[tuple[int, int]] = set()
    seen_projection_events: set[tuple[int, int]] = set()
    for expected_order, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping) or set(raw) != FIRST_PATH_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned invalid first-path relations")
        order = raw.get("order")
        source_start = raw.get("source_start_byte")
        source_end = raw.get("source_end_byte")
        event_start = raw.get("event_start_byte")
        event_end = raw.get("event_end_byte")
        actor_kind = str(raw.get("actor_kind") or "")
        actor_quote = str(raw.get("actor_quote") or "")
        actor_is_carried = raw.get("actor_is_carried")
        actor_fact_path = str(raw.get("actor_fact_path") or "")
        actor_fact_quote = str(raw.get("actor_fact_quote") or "")
        owner_system_path = str(raw.get("owner_system_path") or "")
        owner_system_quote = str(raw.get("owner_system_quote") or "")
        event_quote = str(raw.get("event_quote") or "")
        action_verb_quote = str(raw.get("action_verb_quote") or "")
        target_quote = str(raw.get("target_quote") or "")
        visible_result_quote = str(raw.get("visible_result_quote") or "")
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
            or event_start < cursor
            or event_end <= event_start
            or event_end > len(path_bytes)
            or actor_kind not in FIRST_PATH_ACTOR_KINDS
            or not actor_quote
            or not isinstance(actor_is_carried, bool)
            or not event_quote
            or any(
                source_start < seen_end and seen_start < source_end
                for seen_start, seen_end in seen_source_events
            )
            or (event_start, event_end) in seen_projection_events
            or not action_verb_quote
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned invalid first-path relations")
        require_first_path_actor_binding(
            actor_kind=actor_kind,
            actor_quote=actor_quote,
            actor_fact_path=actor_fact_path,
            actor_fact_quote=actor_fact_quote,
            owner_system_path=owner_system_path,
            owner_system_quote=owner_system_quote,
            actor_values=actor_values,
            owner_values=owner_values,
        )
        actor_is_surface_explicit = actor_quote in event_quote
        if (
            path_bytes[event_start:event_end] != event_quote.encode("utf-8")
            or actor_is_carried == actor_is_surface_explicit
            or (
                actor_is_carried
                and actor_quote != actor_fact_quote
            )
            or action_verb_quote not in event_quote
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned ungrounded first-path relations")
        previous_binding = rows[-1] if rows else None
        if (
            actor_is_carried
            and (
                previous_binding is None
                or first_path_actor_binding_identity(previous_binding)
                != first_path_actor_binding_identity(raw)
            )
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path actor"
            )
        if not event_target_is_source_bound(
            event_quote=event_quote,
            target_quote=target_quote,
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned ungrounded first-path relations")
        if visible_result_quote and not any(
            visible_result_quote in fact for fact in visible_result_facts if fact
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned ungrounded first-path relations")
        if visible_result_quote:
            if visible_seen or expected_order != len(value):
                raise GreenfieldAuthoredSemanticsError("Greenfield authoring returned an invalid terminal visible result")
            visible_seen = True
        seen_source_events.add((source_start, source_end))
        seen_projection_events.add((event_start, event_end))
        cursor = event_end
        rows.append(
            {
                "order": order,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": event_start,
                "event_end_byte": event_end,
                "actor_kind": actor_kind,
                "actor_quote": actor_quote,
                "actor_is_carried": actor_is_carried,
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
    if not visible_seen:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring did not type a path with a visible result"
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
    owner_rows = [(f"/internal_systems/{index}", str(value)) for index, value in enumerate(internal_systems)]
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


def _actor_projection_values(
    *,
    title: str,
    human_actors: Sequence[str],
    external_systems: Sequence[str],
    internal_systems: Sequence[str],
) -> dict[str, tuple[str, str]]:
    """Return the exact typed entity facts that an event actor may reference."""

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


def require_first_path_actor_binding(
    *,
    actor_kind: str,
    actor_quote: str,
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


def overlapping_first_path_event_orders(
    *,
    source_start: Any,
    source_end: Any,
    first_path_relations: Sequence[Mapping[str, Any]],
) -> frozenset[int]:
    """Return event orders whose exact source ranges overlap one accepted fact."""

    if (
        not isinstance(source_start, int)
        or isinstance(source_start, bool)
        or not isinstance(source_end, int)
        or isinstance(source_end, bool)
        or source_start < 0
        or source_end <= source_start
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored relation source custody is malformed"
        )
    orders: set[int] = set()
    for relation in first_path_relations:
        order = relation.get("order")
        event_start = relation.get("source_start_byte")
        event_end = relation.get("source_end_byte")
        if (
            not isinstance(order, int)
            or isinstance(order, bool)
            or order < 1
            or not isinstance(event_start, int)
            or isinstance(event_start, bool)
            or not isinstance(event_end, int)
            or isinstance(event_end, bool)
            or event_start < 0
            or event_end <= event_start
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored relation source custody is malformed"
            )
        if source_start < event_end and event_start < source_end:
            orders.add(order)
    return frozenset(orders)


def expected_first_path_context_event_order(
    *, source_start: Any, source_end: Any, first_path_relations: Sequence[Mapping[str, Any]]
) -> int:
    orders = overlapping_first_path_event_orders(
        source_start=source_start, source_end=source_end, first_path_relations=first_path_relations
    )
    return next(iter(orders)) if len(orders) == 1 else 0


def _canonical_owner_path(path: str) -> bool:
    if path == "/title":
        return True
    prefix = "/internal_systems/"
    index_text = path.removeprefix(prefix) if path.startswith(prefix) else ""
    if not index_text.isdigit():
        return False
    index = int(index_text)
    return path == f"{prefix}{index}"


def _positive_index(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else 0


def authored_semantics_mapping(
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]] = (),
    *,
    first_path_context_relations: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Serialize verified relations beside, but never instead of, source facts."""

    return {
        "version": AUTHORED_SEMANTICS_VERSION,
        "first_path_relations": [dict(row) for row in relations],
        "first_path_context_relations": [
            dict(row) for row in first_path_context_relations
        ],
        "component_responsibility_relations": [
            dict(row) for row in component_responsibility_relations
        ],
    }


def authored_component_relation_facts(
    *,
    title: str,
    internal_systems: Sequence[str],
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Group exact product-event relations into the sole authored component contract."""

    owner_values = canonical_product_owner_projection_values(
        title=title,
        internal_systems=internal_systems,
    )
    grouped_events: dict[str, list[Mapping[str, Any]]] = {}
    grouped_responsibilities: dict[str, list[str]] = {}
    events_by_order = {
        _positive_index(relation.get("order")): relation
        for relation in relations
        if _positive_index(relation.get("order"))
    }
    for relation in component_responsibility_relations:
        owner_path = str(relation.get("owner_system_path") or "")
        owner = str(relation.get("owner_system_quote") or "")
        responsibility = str(relation.get("responsibility_quote") or "")
        event_order = relation.get("first_path_event_order")
        if (
            not owner
            or owner_values.get(owner_path) != owner
            or not responsibility
            or not isinstance(event_order, int)
            or isinstance(event_order, bool)
            or event_order < 0
        ):
            raise GreenfieldAuthoredSemanticsError(
                "model-authored component responsibility is missing its typed owner"
            )
        linked_event = events_by_order.get(event_order) if event_order else None
        if event_order and linked_event is None:
            raise GreenfieldAuthoredSemanticsError(
                "model-authored component responsibility references an unknown first-path event"
            )
        if linked_event is not None and str(linked_event.get("actor_kind") or "") == "product":
            if str(linked_event.get("owner_system_path") or "") != owner_path:
                raise GreenfieldAuthoredSemanticsError(
                    "model-authored component responsibility contradicts its product event owner"
                )
        grouped_responsibilities.setdefault(owner_path, []).append(responsibility)
    for relation in relations:
        if str(relation.get("actor_kind") or "") != "product":
            continue
        owner_path = str(relation.get("owner_system_path") or "")
        owner = str(relation.get("owner_system_quote") or "")
        if not owner or owner_values.get(owner_path) != owner:
            raise GreenfieldAuthoredSemanticsError(
                "model-authored product event is missing its typed component owner"
            )
        grouped_events.setdefault(owner_path, []).append(relation)
    referenced_owners = set(grouped_responsibilities) | set(grouped_events)
    ordered_owners: list[str] = []
    for owner_path in owner_values:
        if owner_path in referenced_owners:
            ordered_owners.append(owner_path)
    if referenced_owners != set(ordered_owners):
        raise GreenfieldAuthoredSemanticsError(
            "model-authored component relation references an unselected owner"
        )
    if not ordered_owners:
        raise GreenfieldAuthoredSemanticsError(
            "model-authored intent did not establish a viable component projection"
        )

    rows: list[dict[str, Any]] = []
    for owner_path in ordered_owners:
        owner = owner_values[owner_path]
        events = grouped_events.get(owner_path, [])
        event_text = list(
            dict.fromkeys(
                str(event.get("event_quote") or "")
                for event in events
                if str(event.get("event_quote") or "")
            )
        )
        responsibilities = list(grouped_responsibilities.get(owner_path, ())) or event_text
        if not responsibilities:
            raise GreenfieldAuthoredSemanticsError(
                f"model-authored component `{owner or title}` is missing an owner-bound responsibility"
            )
        rows.append(
            {
                "owner_system": owner or title,
                "responsibility_facts": responsibilities,
                "owner_bound_events": event_text,
                "event_targets": list(
                    dict.fromkeys(
                        str(event.get("target_quote") or "")
                        for event in events
                        if str(event.get("target_quote") or "")
                    )
                ),
                "visible_results": list(
                    dict.fromkeys(
                        str(event.get("visible_result_quote") or "")
                        for event in events
                        if str(event.get("visible_result_quote") or "")
                    )
                ),
            }
        )
    return tuple(rows)


def validate_first_path_context_relations(
    value: Any,
    *,
    intent: Mapping[str, Any],
    first_path_relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Require one explicit path adjudication for every selected context fact."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored first-path context relations are malformed"
        )
    expected: list[tuple[str, str, str]] = []
    state_object = intent.get("state_object")
    if isinstance(state_object, str) and state_object:
        expected.append(("state_object", "/state_object", state_object))
    for field, kind in (
        ("external_systems", "external_system"),
        ("operational_constraints", "operational_constraint"),
    ):
        rows = intent.get(field)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
            if rows in (None, ()):
                continue
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored first-path context facts are malformed"
            )
        expected.extend(
            (kind, f"/{field}/{index}", row)
            for index, row in enumerate(rows)
            if isinstance(row, str) and row
        )
    if len(value) != len(expected):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored semantics left first-path context facts unadjudicated"
        )
    sealed: list[dict[str, Any]] = []
    for raw, (expected_kind, expected_path, expected_quote) in zip(value, expected, strict=True):
        if not isinstance(raw, Mapping) or set(raw) != FIRST_PATH_CONTEXT_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored first-path context relations are malformed"
            )
        source_start = raw.get("source_start_byte")
        source_end = raw.get("source_end_byte")
        event_order = raw.get("first_path_event_order")
        expected_event_order = expected_first_path_context_event_order(
            source_start=source_start,
            source_end=source_end,
            first_path_relations=first_path_relations,
        )
        if (
            raw.get("context_kind") != expected_kind
            or raw.get("fact_path") != expected_path
            or raw.get("fact_quote") != expected_quote
            or not isinstance(source_start, int)
            or isinstance(source_start, bool)
            or not isinstance(source_end, int)
            or isinstance(source_end, bool)
            or source_start < 0
            or source_end <= source_start
            or not isinstance(event_order, int)
            or isinstance(event_order, bool)
            or event_order < 0
            or event_order != expected_event_order
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored first-path context relation does not match its accepted fact"
            )
        sealed.append(dict(raw))
    return tuple(sealed)


def require_authored_relation_source_custody(
    relations: Sequence[Mapping[str, Any]],
    *,
    context_relations: Sequence[Mapping[str, Any]],
    source_bytes: bytes,
    source_spans: Sequence[Mapping[str, Any]],
) -> None:
    """Bind sealed event projections to their exact selected source segments."""

    path_spans = sorted(
        (
            span
            for span in source_spans
            if span.get("classification") == "product_claim"
            and span.get("section_key") == "first_path"
        ),
        key=lambda span: int(span.get("row_index") or 0),
    )
    if not path_spans:
        raise GreenfieldAuthoredSemanticsError(
            "model-authored Product Intent relation source custody is missing first-path segments"
        )
    projection_cursor = 0
    for expected_row, span in enumerate(path_spans, start=1):
        text = str(span.get("text") or "")
        projection_start = span.get("projection_start_byte")
        projection_end = span.get("projection_end_byte")
        if (
            span.get("row_index") != expected_row
            or span.get("projection_path") != "/first_path"
            or projection_start != projection_cursor
            or not isinstance(projection_end, int)
            or isinstance(projection_end, bool)
            or projection_end != projection_start + len(text.encode("utf-8"))
        ):
            raise GreenfieldAuthoredSemanticsError(
                "model-authored Product Intent first-path segment projection custody is malformed"
            )
        projection_cursor = projection_end + 1

    covered_rows: set[int] = set()
    for relation in relations:
        source_start = relation.get("source_start_byte")
        source_end = relation.get("source_end_byte")
        event_start = relation.get("event_start_byte")
        event_end = relation.get("event_end_byte")
        quote = str(relation.get("event_quote") or "")
        if not _valid_source_range(source_start, source_end, limit=len(source_bytes)):
            raise GreenfieldAuthoredSemanticsError(
                "model-authored Product Intent relation source custody does not match the exact envelope source"
            )
        matching_segments = [
            span
            for span in path_spans
            if isinstance(event_start, int)
            and not isinstance(event_start, bool)
            and isinstance(event_end, int)
            and not isinstance(event_end, bool)
            and span["projection_start_byte"] <= event_start
            and event_end <= span["projection_end_byte"]
        ]
        if len(matching_segments) != 1:
            raise GreenfieldAuthoredSemanticsError(
                "model-authored Product Intent relation projection is not owned by one selected source segment"
            )
        segment = matching_segments[0]
        local_start = event_start - int(segment["projection_start_byte"])
        expected_source_start = int(segment["source_start_byte"]) + local_start
        quote_bytes = quote.encode("utf-8")
        if (
            not quote
            or source_start != expected_source_start
            or source_end != expected_source_start + len(quote_bytes)
            or source_bytes[source_start:source_end] != quote_bytes
        ):
            raise GreenfieldAuthoredSemanticsError(
                "model-authored Product Intent relation source custody does not match the exact envelope source"
            )
        covered_rows.add(int(segment["row_index"]))
    if covered_rows != set(range(1, len(path_spans) + 1)):
        raise GreenfieldAuthoredSemanticsError(
            "model-authored Product Intent left a selected first-path segment without event custody"
        )

    span_identity = {
        (
            str(span.get("section_key") or ""),
            int(span.get("row_index") or 0),
            str(span.get("text") or ""),
            span.get("source_start_byte"),
            span.get("source_end_byte"),
        )
        for span in source_spans
        if span.get("classification") == "product_claim"
    }
    field_by_kind = {
        "state_object": "state_object",
        "external_system": "external_systems",
        "operational_constraint": "operational_constraints",
    }
    for relation in context_relations:
        kind = str(relation.get("context_kind") or "")
        path = str(relation.get("fact_path") or "")
        quote = str(relation.get("fact_quote") or "")
        source_start = relation.get("source_start_byte")
        source_end = relation.get("source_end_byte")
        field = field_by_kind.get(kind, "")
        if path == f"/{field}":
            row_index = 1
        else:
            prefix = f"/{field}/"
            index_text = path.removeprefix(prefix) if path.startswith(prefix) else ""
            row_index = int(index_text) + 1 if index_text.isdigit() else 0
        if (
            not field
            or not row_index
            or not quote
            or not _valid_source_range(source_start, source_end, limit=len(source_bytes))
            or source_bytes[source_start:source_end] != quote.encode("utf-8")
            or (field, row_index, quote, source_start, source_end) not in span_identity
        ):
            raise GreenfieldAuthoredSemanticsError(
                "model-authored Product Intent context source custody does not match the exact envelope source"
            )


def _valid_source_range(start: Any, end: Any, *, limit: int) -> bool:
    return bool(
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start < end <= limit
    )


def _authored_relations_from_intent(
    intent: Mapping[str, Any] | None,
) -> tuple[
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    """Read and validate the complete closed authoring relation contract."""

    if not isinstance(intent, Mapping):
        return (), (), ()
    semantics = intent.get(AUTHORED_SEMANTICS_KEY)
    if semantics is None:
        return (), (), ()
    if (
        not isinstance(semantics, Mapping)
        or semantics.get("version") != AUTHORED_SEMANTICS_VERSION
        or set(semantics)
        != {
            "version",
            "first_path_relations",
            "first_path_context_relations",
            "component_responsibility_relations",
        }
    ):
        raise GreenfieldAuthoredSemanticsError("Greenfield authored semantics are malformed")
    relations = semantics.get("first_path_relations")
    if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError("Greenfield authored semantics are malformed")
    actor_values = intent.get("human_actors", ())
    if not isinstance(actor_values, Sequence) or isinstance(actor_values, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError("Greenfield authored semantics are missing typed human actors")
    first_path_relations = validate_first_path_relations(
        relations,
        first_path=str(intent.get("first_path") or ""),
        human_actors=tuple(str(row) for row in actor_values if str(row)),
        external_systems=intent_text_rows(intent.get("external_systems")),
        internal_systems=intent_text_rows(intent.get("internal_systems")),
        product_title=str(intent.get("title") or ""),
        terminal_result_facts=intent_terminal_result_values(intent),
    )
    context_relations = validate_first_path_context_relations(
        semantics.get("first_path_context_relations"),
        intent=intent,
        first_path_relations=first_path_relations,
    )
    component_relations = validate_component_responsibility_relations(
        semantics.get("component_responsibility_relations"),
        intent=intent,
        first_path_relations=first_path_relations,
    )
    return first_path_relations, context_relations, component_relations


def first_path_relations_from_intent(intent: Mapping[str, Any] | None) -> tuple[dict[str, Any], ...]:
    """Return first-path relations only after validating all authored relations."""

    relations, _context_relations, _component_relations = _authored_relations_from_intent(intent)
    return relations


def first_path_context_relations_from_intent(
    intent: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Return the exact path-context adjudications after full contract validation."""

    _relations, context_relations, _component_relations = _authored_relations_from_intent(intent)
    return context_relations


def component_responsibility_relations_from_intent(
    intent: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Return exact owner bindings for all selected component responsibilities."""

    _relations, _context_relations, component_relations = _authored_relations_from_intent(intent)
    return component_relations


def validate_component_responsibility_relations(
    value: Any,
    *,
    intent: Mapping[str, Any],
    first_path_relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Require exact paths and quotes for every accepted responsibility fact."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > MAX_COMPONENT_RESPONSIBILITY_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored component-responsibility relations are malformed"
        )
    responsibility_values = intent.get("component_responsibilities")
    if responsibility_values is None:
        responsibilities: tuple[str, ...] = ()
    elif (
        isinstance(responsibility_values, Sequence)
        and not isinstance(responsibility_values, (str, bytes, bytearray))
        and all(isinstance(row, str) and row for row in responsibility_values)
    ):
        responsibilities = tuple(responsibility_values)
    else:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored component-responsibility facts are malformed"
        )
    expected_paths = tuple(
        f"/component_responsibilities/{index}" for index in range(len(responsibilities))
    )
    if expected_paths and len(value) != len(expected_paths):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored semantics left component responsibilities without typed owners"
        )
    if not expected_paths and len(value) != 1:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authored semantics do not establish a viable component projection"
        )
    systems_value = intent.get("internal_systems")
    systems = (
        tuple(str(row) for row in systems_value)
        if isinstance(systems_value, Sequence)
        and not isinstance(systems_value, (str, bytes, bytearray))
        else ()
    )
    owner_values = canonical_product_owner_projection_values(
        title=str(intent.get("title") or ""),
        internal_systems=systems,
    )
    events_by_order = {
        _positive_index(row.get("order")): row
        for row in first_path_relations
        if _positive_index(row.get("order"))
    }
    rows: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, raw in enumerate(value):
        if (
            not isinstance(raw, Mapping)
            or set(raw) != COMPONENT_RESPONSIBILITY_RELATION_FIELDS
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored component-responsibility relations are malformed"
            )
        responsibility_path = str(raw.get("responsibility_path") or "")
        owner_path = str(raw.get("owner_system_path") or "")
        owner_quote = str(raw.get("owner_system_quote") or "")
        event_order = raw.get("first_path_event_order")
        responsibility_source = str(raw.get("responsibility_source") or "")
        if not _canonical_owner_path(owner_path):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored component responsibility has an invalid system owner"
            )
        if (
            not isinstance(event_order, int)
            or isinstance(event_order, bool)
            or event_order < 0
            or responsibility_source not in COMPONENT_RESPONSIBILITY_SOURCES
            or owner_values.get(owner_path) != owner_quote
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored component-responsibility relations do not match accepted facts"
            )
        linked_event = events_by_order.get(event_order) if event_order else None
        if event_order and linked_event is None:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored component responsibility references an unknown first-path event"
            )
        if linked_event is not None and str(linked_event.get("actor_kind") or "") == "product":
            if str(linked_event.get("owner_system_path") or "") != owner_path:
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authored semantics assign contradictory owners to one product event"
                )
        if responsibility_source == "terminal_visible_result":
            responsibility_quote = str(raw.get("responsibility_quote") or "")
            responsibility_fact = intent_text_at_path(intent, responsibility_path)
            if (
                expected_paths
                or linked_event is None
                or event_order != len(events_by_order)
                or not str(linked_event.get("visible_result_quote") or "")
                or responsibility_quote
                != str(linked_event.get("visible_result_quote") or "")
                or not responsibility_fact
                or responsibility_quote not in responsibility_fact
            ):
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authored terminal component responsibility is malformed"
                )
            rows.append(dict(raw))
            continue
        expected_path = expected_paths[index] if index < len(expected_paths) else ""
        responsibility = responsibilities[index] if index < len(responsibilities) else ""
        if (
            responsibility_path != expected_path
            or responsibility_path in seen_paths
            or str(raw.get("responsibility_quote") or "") != responsibility
            or responsibility_source != "accepted_fact"
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authored component-responsibility relations do not match accepted facts"
            )
        seen_paths.add(responsibility_path)
        rows.append(dict(raw))
    return tuple(rows)


def authored_relation_set_sha256(
    relations: Sequence[Mapping[str, Any]],
    component_responsibility_relations: Sequence[Mapping[str, Any]] = (),
    *,
    first_path_context_relations: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Hash the complete ordered relation contract without interpreting its language."""

    if isinstance(relations, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
    first_path_payload: list[dict[str, Any]] = []
    for relation in relations:
        if not isinstance(relation, Mapping) or set(relation) != FIRST_PATH_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
        first_path_payload.append(dict(relation))
    component_payload: list[dict[str, Any]] = []
    for relation in component_responsibility_relations:
        if (
            not isinstance(relation, Mapping)
            or set(relation) != COMPONENT_RESPONSIBILITY_RELATION_FIELDS
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
        component_payload.append(dict(relation))
    context_payload: list[dict[str, Any]] = []
    for relation in first_path_context_relations:
        if (
            not isinstance(relation, Mapping)
            or set(relation) != FIRST_PATH_CONTEXT_RELATION_FIELDS
        ):
            raise GreenfieldAuthoredSemanticsError("Greenfield authored relation custody is malformed")
        context_payload.append(dict(relation))
    canonical = json.dumps(
        {
            "version": AUTHORED_SEMANTICS_VERSION,
            "first_path_relations": first_path_payload,
            "first_path_context_relations": context_payload,
            "component_responsibility_relations": component_payload,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def require_authored_relation_authority(
    intent: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Require exact authored relations to match the sealed Product Intent authority."""

    relations = require_relation_authority_parity(intent, authority)
    if not relations:
        raise GreenfieldAuthoredSemanticsError(
            "model-authored Greenfield custody is missing verified first-path relations"
        )
    return relations


def require_relation_authority_parity(
    intent: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Prevent authored relation custody from being added or removed as a route switch."""

    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        require_product_intent_authority_structure,
    )

    require_product_intent_authority_structure(authority)
    relations, context_relations, component_relations = _authored_relations_from_intent(intent)
    sealed_digest = authority.get(AUTHORED_RELATION_SET_SHA256_KEY)
    empty_digest = authored_relation_set_sha256((), (), first_path_context_relations=())
    if not relations:
        if AUTHORED_SEMANTICS_KEY in intent or sealed_digest != empty_digest:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoredness does not match sealed Product Intent relation authority"
            )
        return ()
    expected = authored_relation_set_sha256(
        relations,
        component_relations,
        first_path_context_relations=context_relations,
    )
    if sealed_digest != expected:
        raise GreenfieldAuthoredSemanticsError(
            "model-authored Greenfield relations do not match sealed Product Intent authority"
        )
    return relations


def authored_source_custody(
    *,
    intent: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> Mapping[str, str]:
    """Return an issued Tribunal receipt bound to verified authored relations."""

    relations = require_authored_relation_authority(intent, authority)
    context_relations = first_path_context_relations_from_intent(intent)
    component_relations = component_responsibility_relations_from_intent(intent)
    return _bind_verified_source_custody(
        projection_origin=AUTHORED_PROJECTION_ORIGIN,
        semantic_root=AUTHORED_SEMANTIC_ROOT,
        semantic_version=AUTHORED_SEMANTICS_VERSION,
        authored_relation_set_sha256=authored_relation_set_sha256(
            relations,
            component_relations,
            first_path_context_relations=context_relations,
        ),
    )


def authored_projection_relations(
    proposal: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], ...]:
    """Validate the authored projection marker without falling back to legacy meaning."""

    if not isinstance(proposal, Mapping) or proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        return ()
    intent = proposal.get("intent")
    relations = first_path_relations_from_intent(intent if isinstance(intent, Mapping) else None)
    if not relations:
        raise GreenfieldAuthoredSemanticsError(
            "model-authored Greenfield projection is missing verified first-path relations"
        )
    return relations


def authored_visible_result(relations: Sequence[Mapping[str, Any]]) -> str:
    """Return the terminal source-quoted result without interpreting proof prose."""

    for row in reversed(tuple(relations)):
        result = str(row.get("visible_result_quote") or "").strip()
        if result:
            return result
    return ""


FIRST_PATH_RELATION_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 0,
    "maxItems": MAX_FIRST_PATH_RELATIONS,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(FIRST_PATH_RELATION_FIELDS),
        "properties": {
            "order": {"type": "integer", "minimum": 1},
            "source_start_byte": {"type": "integer", "minimum": 0},
            "source_end_byte": {"type": "integer", "minimum": 1},
            "event_start_byte": {"type": "integer", "minimum": 0},
            "event_end_byte": {"type": "integer", "minimum": 1},
            "actor_kind": {"type": "string", "enum": list(FIRST_PATH_ACTOR_KINDS)},
            "actor_quote": {"type": "string"},
            "actor_is_carried": {"type": "boolean"},
            "actor_fact_path": {"type": "string"},
            "actor_fact_quote": {"type": "string"},
            "owner_system_path": {"type": "string"},
            "owner_system_quote": {"type": "string"},
            "event_quote": {"type": "string"},
            "action_verb_quote": {"type": "string"},
            "target_quote": {"type": "string"},
            "visible_result_quote": {"type": "string"},
        },
    },
}

FIRST_PATH_CONTEXT_RELATION_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 0,
    "maxItems": 96,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(FIRST_PATH_CONTEXT_RELATION_FIELDS),
        "properties": {
            "context_kind": {"type": "string", "enum": list(FIRST_PATH_CONTEXT_KINDS)},
            "fact_path": {"type": "string"},
            "fact_quote": {"type": "string"},
            "source_start_byte": {"type": "integer", "minimum": 0},
            "source_end_byte": {"type": "integer", "minimum": 1},
            "first_path_event_order": {"type": "integer", "minimum": 0},
        },
    },
}


__all__ = [
    "AUTHORED_PROJECTION_ORIGIN",
    "AUTHORED_RELATION_SET_SHA256_KEY",
    "AUTHORED_SEMANTICS_KEY",
    "AUTHORED_SEMANTIC_ROOT",
    "AUTHORED_SEMANTICS_VERSION",
    "ATOMIC_FACT_CATEGORIES",
    "ATOMIC_POLARITIES",
    "AUTHORED_RELATION_ROLES",
    "COMPONENT_RESPONSIBILITY_RELATION_FIELDS",
    "FIRST_PATH_CONTEXT_RELATION_FIELDS",
    "FIRST_PATH_CONTEXT_RELATION_SCHEMA",
    "FIRST_PATH_ACTOR_BINDING_FIELDS",
    "FIRST_PATH_RELATION_SCHEMA",
    "GREENFIELD_PRECONFIRM_STAGING_MARKER",
    "GreenfieldAuthoredSemanticsError",
    "authored_relation_set_sha256",
    "authored_component_relation_facts",
    "authored_semantics_mapping",
    "authored_source_custody",
    "authored_projection_relations",
    "authored_visible_result",
    "canonical_product_owner_projection_values",
    "combined_prompt_evidence_source",
    "component_responsibility_relations_from_intent",
    "expected_first_path_context_event_order",
    "first_path_context_relations_from_intent",
    "first_path_actor_binding_identity",
    "first_path_relations_from_intent",
    "overlapping_first_path_event_orders",
    "require_first_path_actor_binding",
    "require_authored_relation_authority",
    "require_authored_relation_source_custody",
    "require_relation_authority_parity",
    "validate_component_responsibility_relations",
    "validate_first_path_context_relations",
    "validate_first_path_relations",
]
