"""Model-response relations for source-bound Greenfield path authoring.

The provider selects exact facts, event quotes, and occurrences. This module
derives source and composite-projection coordinates and owns the closed model
schemas; sealed relation validation remains in ``greenfield_authored_semantics``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    FIRST_PATH_ACTOR_KINDS,
    MAX_COMPONENT_RESPONSIBILITY_RELATIONS,
    MAX_FIRST_PATH_RELATIONS,
    GreenfieldAuthoredSemanticsError,
    first_path_actor_binding_identity,
    overlapping_first_path_event_orders,
    require_first_path_actor_binding,
)


MODEL_FIRST_PATH_RELATION_FIELDS = frozenset(
    {
        "order",
        "fact_quote",
        "event_quote",
        "event_occurrence",
        "actor_kind",
        "actor_quote",
        "actor_occurrence",
        "actor_fact_quote",
        "owner_system_fact_quote",
        "action_verb_quote",
        "action_verb_occurrence",
        "target_quote",
        "target_occurrence",
        "visible_result_quote",
        "visible_result_occurrence",
        "recovery_path",
    }
)
MODEL_COMPONENT_RESPONSIBILITY_RELATION_FIELDS = frozenset(
    {
        "responsibility_fact_quote",
        "independent_owner_fact_quote",
        "first_path_event_order",
    }
)
MODEL_FIRST_PATH_CONTEXT_RELATION_FIELDS = frozenset(
    {"fact_field", "fact_quote", "first_path_event_order"}
)
_CONTEXT_KIND_BY_FIELD = {
    "state_object": "state_object",
    "external_systems": "external_system",
    "operational_constraints": "operational_constraint",
}
_CONTEXT_FIELD_ORDER = ("state_object", "external_systems", "operational_constraints")


def derive_model_first_path_relations(
    value: Any,
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path: str,
) -> tuple[dict[str, Any], ...]:
    """Resolve model-selected events against exact source path segments."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or len(value) > MAX_FIRST_PATH_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    path_facts = tuple(
        row for row in selected_facts if str(row.get("field") or "") == "first_path"
    )
    if not path_facts or "\n".join(str(row.get("quote") or "") for row in path_facts) != first_path:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned first-path segments outside the canonical projection"
        )
    path_fact_indexes = {int(row["fact_index"]) for row in path_facts}
    owner_values = _selected_owner_projection_values(selected_facts)
    actor_values = _selected_actor_projection_values(selected_facts)
    rows: list[dict[str, Any]] = []
    covered_path_facts: set[int] = set()
    cursor = 0
    human_seen = False
    visible_seen = False
    seen_source_events: set[tuple[int, int]] = set()
    seen_projection_events: set[tuple[int, int]] = set()
    for expected_order, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping) or set(raw) != MODEL_FIRST_PATH_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path relations"
            )
        fact_quote = _required_quote(raw.get("fact_quote"))
        event_quote = _required_quote(raw.get("event_quote"))
        matching_path_facts = tuple(
            fact
            for fact in path_facts
            if str(fact.get("quote") or "") == fact_quote
        )
        located_candidates: list[tuple[int, int, Mapping[str, Any], int]] = []
        for fact in matching_path_facts:
            segment_bytes = str(fact.get("quote") or "").encode("utf-8")
            try:
                local_start = _exact_occurrence_start(
                    segment_bytes,
                    event_quote,
                    raw.get("event_occurrence"),
                )
            except GreenfieldAuthoredSemanticsError:
                continue
            projection_start = _nonnegative_int(fact.get("projection_start_byte"))
            candidate_start = projection_start + local_start
            located_candidates.append(
                (
                    candidate_start,
                    _positive_index(fact.get("fact_index")),
                    fact,
                    local_start,
                )
            )
        grounded_candidates = [
            candidate for candidate in located_candidates if candidate[0] >= cursor
        ]
        if located_candidates and not grounded_candidates:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path relations"
            )
        grounded_candidates.sort(key=lambda item: (item[0], item[1]))
        selected = grounded_candidates[0] if grounded_candidates else None
        selected_fact = selected[2] if selected else None
        fact_index = _positive_index(selected_fact.get("fact_index")) if selected_fact else 0
        order = raw.get("order")
        if (
            not isinstance(order, int)
            or isinstance(order, bool)
            or order != expected_order
            or selected_fact is None
            or str(selected_fact.get("field") or "") != "first_path"
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path relation"
            )
        segment = str(selected_fact.get("quote") or "")
        local_event_start = selected[3]
        event_length = len(event_quote.encode("utf-8"))
        projection_base = _nonnegative_int(selected_fact.get("projection_start_byte"))
        source_base = _nonnegative_int(selected_fact.get("source_start_byte"))
        event_start = projection_base + local_event_start
        event_end = event_start + event_length
        source_start = source_base + local_event_start
        source_end = source_start + event_length
        actor_kind = str(raw.get("actor_kind") or "")
        actor_quote = _required_quote(raw.get("actor_quote"))
        action_verb_quote = _required_quote(raw.get("action_verb_quote"))
        target_quote = _optional_quote(raw.get("target_quote"), raw.get("target_occurrence"))
        visible_result_quote = _optional_quote(
            raw.get("visible_result_quote"),
            raw.get("visible_result_occurrence"),
        )
        recovery_path = raw.get("recovery_path")
        if (
            event_start < cursor
            or any(
                source_start < seen_end and seen_start < source_end
                for seen_start, seen_end in seen_source_events
            )
            or actor_kind not in FIRST_PATH_ACTOR_KINDS
            or not isinstance(recovery_path, bool)
            or (event_start, event_end) in seen_projection_events
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path relations"
            )
        owner_system_path, owner_system_quote = _event_owner(
            actor_kind=actor_kind,
            owner_system_fact_quote=raw.get("owner_system_fact_quote"),
            selected_facts=selected_facts,
            owner_values=owner_values,
        )
        actor_fact_path, actor_fact_quote = _event_actor_fact(
            actor_kind=actor_kind,
            actor_fact_quote=raw.get("actor_fact_quote"),
            selected_facts=selected_facts,
        )
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
        event_bytes = event_quote.encode("utf-8")
        actor_is_explicit = actor_quote in event_quote
        previous_event = rows[-1] if rows else None
        actor_binding = {
            "actor_kind": actor_kind,
            "actor_quote": actor_quote,
            "actor_fact_path": actor_fact_path,
            "actor_fact_quote": actor_fact_quote,
            "owner_system_path": owner_system_path,
            "owner_system_quote": owner_system_quote,
        }
        continues_previous_actor = bool(
            previous_event is not None
            and first_path_actor_binding_identity(previous_event)
            == first_path_actor_binding_identity(actor_binding)
        )
        if actor_is_explicit:
            _exact_occurrence_start(event_bytes, actor_quote, raw.get("actor_occurrence"))
        elif not continues_previous_actor:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path actor"
            )
        elif raw.get("actor_occurrence") != 0:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid carried first-path actor"
            )
        _exact_occurrence_start(
            event_bytes,
            action_verb_quote,
            raw.get("action_verb_occurrence"),
        )
        if target_quote:
            _exact_occurrence_start(event_bytes, target_quote, raw.get("target_occurrence"))
        if visible_result_quote:
            _exact_occurrence_start(
                event_bytes,
                visible_result_quote,
                raw.get("visible_result_occurrence"),
            )
        if actor_kind == "human":
            human_seen = True
        if visible_result_quote:
            if visible_seen or expected_order != len(value):
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring returned an invalid terminal visible result"
                )
            visible_seen = True
        rows.append(
            {
                "order": expected_order,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": event_start,
                "event_end_byte": event_end,
                **actor_binding,
                "actor_is_carried": not actor_is_explicit,
                "event_quote": event_quote,
                "action_verb_quote": action_verb_quote,
                "target_quote": target_quote,
                "visible_result_quote": visible_result_quote,
                "recovery_path": recovery_path,
            }
        )
        covered_path_facts.add(fact_index)
        seen_source_events.add((source_start, source_end))
        seen_projection_events.add((event_start, event_end))
        cursor = event_end
    if covered_path_facts != path_fact_indexes:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring left a first-path source segment without a typed event"
        )
    if rows[0]["actor_kind"] != "human" or not human_seen or not visible_seen:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring did not type a human path with a visible result"
        )
    return tuple(rows)


def derive_model_first_path_context_relations(
    value: Any,
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path_relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Adjudicate every selected state, external system, and constraint fact."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path context relations"
        )
    expected = tuple(
        row
        for field in _CONTEXT_FIELD_ORDER
        for row in selected_facts
        if str(row.get("field") or "") == field
    )
    if len(value) != len(expected):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring left first-path context facts unadjudicated"
        )
    facts_by_identity = {
        (str(row.get("field") or ""), str(row.get("quote") or "")): row
        for row in expected
    }
    if len(facts_by_identity) != len(expected):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned ambiguous first-path context facts"
        )
    events_by_order = {int(row["order"]): row for row in first_path_relations}
    rows_by_fact: dict[int, dict[str, Any]] = {}
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != MODEL_FIRST_PATH_CONTEXT_RELATION_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path context relations"
            )
        fact_field = str(raw.get("fact_field") or "")
        fact_quote = str(raw.get("fact_quote") or "")
        event_order = raw.get("first_path_event_order")
        fact = facts_by_identity.get((fact_field, fact_quote))
        fact_index = _positive_index(fact.get("fact_index")) if fact else 0
        if (
            fact is None
            or fact_index in rows_by_fact
            or not isinstance(event_order, int)
            or isinstance(event_order, bool)
            or event_order < 0
            or (event_order and event_order not in events_by_order)
            or (str(fact.get("field") or "") == "state_object" and not event_order)
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid first-path context link"
            )
        field = str(fact.get("field") or "")
        overlapping_orders = overlapping_first_path_event_orders(
            source_start=fact.get("source_start_byte"),
            source_end=fact.get("source_end_byte"),
            first_path_relations=first_path_relations,
        )
        if len(overlapping_orders) > 1 or (
            overlapping_orders and event_order not in overlapping_orders
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid first-path context link"
            )
        rows_by_fact[fact_index] = {
            "context_kind": _CONTEXT_KIND_BY_FIELD[field],
            "fact_path": str(fact.get("projection_path") or ""),
            "fact_quote": str(fact.get("quote") or ""),
            "source_start_byte": _nonnegative_int(fact.get("source_start_byte")),
            "source_end_byte": _positive_int(fact.get("source_end_byte")),
            "first_path_event_order": event_order,
        }
    if set(rows_by_fact) != {
        _positive_index(fact.get("fact_index")) for fact in expected
    }:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring left first-path context facts unadjudicated"
        )
    return tuple(rows_by_fact[int(fact["fact_index"])] for fact in expected)


def derive_model_component_responsibility_relations(
    value: Any,
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path_relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Bind every component responsibility to an exact selected product owner."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > MAX_COMPONENT_RESPONSIBILITY_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid component-responsibility relations"
        )
    owner_values = _selected_owner_projection_values(selected_facts)
    owner_facts_by_quote = {
        str(row.get("quote") or ""): row
        for row in selected_facts
        if str(row.get("field") or "") in {"internal_systems", "title"}
    }
    events_by_order = {int(row["order"]): row for row in first_path_relations}
    responsibility_facts = tuple(
        row
        for row in selected_facts
        if str(row.get("field") or "") == "component_responsibilities"
    )
    expected = tuple(int(row["fact_index"]) for row in responsibility_facts)
    responsibility_facts_by_quote = {
        str(row.get("quote") or ""): row for row in responsibility_facts
    }
    if (
        len(owner_facts_by_quote)
        != sum(
            1
            for row in selected_facts
            if str(row.get("field") or "") in {"internal_systems", "title"}
        )
        or len(responsibility_facts_by_quote) != len(responsibility_facts)
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned ambiguous component ownership facts"
        )
    rows_by_fact_index: dict[int, dict[str, Any]] = {}
    terminal_rows: list[dict[str, Any]] = []
    for raw in value:
        if (
            not isinstance(raw, Mapping)
            or set(raw) != MODEL_COMPONENT_RESPONSIBILITY_RELATION_FIELDS
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid component-responsibility relations"
            )
        responsibility_quote = str(raw.get("responsibility_fact_quote") or "")
        responsibility_fact = responsibility_facts_by_quote.get(responsibility_quote)
        responsibility_index = (
            _positive_index(responsibility_fact.get("fact_index"))
            if responsibility_fact is not None
            else 0
        )
        independent_owner_quote = str(raw.get("independent_owner_fact_quote") or "")
        event_order = raw.get("first_path_event_order")
        if (
            not isinstance(event_order, int)
            or isinstance(event_order, bool)
            or event_order < 0
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid component-responsibility relations"
            )
        linked_event = events_by_order.get(event_order) if event_order else None
        if event_order and linked_event is None:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring linked a component responsibility to an unknown first-path event"
            )
        if responsibility_index == 0:
            if expected or linked_event is None or not str(linked_event.get("visible_result_quote") or ""):
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring returned an invalid terminal component responsibility"
                )
            if str(linked_event.get("actor_kind") or "") != "product":
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring assigned a terminal component responsibility "
                    "without a typed product event owner"
                )
        if linked_event is not None and str(linked_event.get("actor_kind") or "") == "product":
            if independent_owner_quote:
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring repeated an owner that must inherit from its typed product event"
                )
            owner_path = str(linked_event.get("owner_system_path") or "")
            owner_quote = str(linked_event.get("owner_system_quote") or "")
        else:
            owner_fact = owner_facts_by_quote.get(independent_owner_quote)
            if owner_fact is None:
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring returned an unbound component responsibility owner"
                )
            owner_path = str(owner_fact.get("projection_path") or "")
            owner_quote = str(owner_fact.get("quote") or "")
        if owner_values.get(owner_path) != owner_quote:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an unbound component responsibility owner"
            )
        if responsibility_index == 0:
            terminal_rows.append(
                {
                    "responsibility_path": "/first_path",
                    "responsibility_quote": str(linked_event.get("visible_result_quote") or ""),
                    "owner_system_path": owner_path,
                    "owner_system_quote": owner_quote,
                    "first_path_event_order": event_order,
                    "responsibility_source": "terminal_visible_result",
                }
            )
            continue
        if responsibility_fact is None:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an unbound component responsibility owner"
            )
        if responsibility_index in rows_by_fact_index:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring duplicated a component responsibility owner"
            )
        overlapping_event_orders = _overlapping_source_event_orders(
            responsibility_fact=responsibility_fact,
            events=first_path_relations,
        )
        if overlapping_event_orders and event_order not in overlapping_event_orders:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring omitted the typed link for an overlapping product event"
            )
        rows_by_fact_index[responsibility_index] = {
            "responsibility_path": str(responsibility_fact.get("projection_path") or ""),
            "responsibility_quote": str(responsibility_fact.get("quote") or ""),
            "owner_system_path": owner_path,
            "owner_system_quote": owner_quote,
            "first_path_event_order": event_order,
            "responsibility_source": "accepted_fact",
        }
    if expected and terminal_rows:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring mixed accepted and terminal component responsibilities"
        )
    if set(rows_by_fact_index) != set(expected) or len(rows_by_fact_index) != len(expected):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring left component responsibilities without typed owners"
        )
    if not expected:
        if len(terminal_rows) != 1:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring did not establish a viable component projection"
            )
        return tuple(terminal_rows)
    return tuple(rows_by_fact_index[index] for index in expected)


def _overlapping_source_event_orders(
    *,
    responsibility_fact: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
) -> frozenset[int]:
    try:
        return overlapping_first_path_event_orders(
            source_start=responsibility_fact.get("source_start_byte"),
            source_end=responsibility_fact.get("source_end_byte"),
            first_path_relations=events,
        )
    except GreenfieldAuthoredSemanticsError as exc:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned component ownership without exact source custody"
        ) from exc


def _event_owner(
    *,
    actor_kind: str,
    owner_system_fact_quote: Any,
    selected_facts: Sequence[Mapping[str, Any]],
    owner_values: Mapping[str, str],
) -> tuple[str, str]:
    owner_quote = str(owner_system_fact_quote or "")
    if actor_kind != "product":
        if owner_quote:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid product event owner"
            )
        return "", ""
    matches = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") in {"internal_systems", "title"}
        and str(fact.get("quote") or "") == owner_quote
    )
    owner_fact = matches[0] if len(matches) == 1 else None
    if owner_fact is None:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound product event owner"
        )
    owner_path = str(owner_fact.get("projection_path") or "")
    if owner_values.get(owner_path) != owner_quote:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound product event owner"
        )
    return owner_path, owner_quote


def _event_actor_fact(
    *,
    actor_kind: str,
    actor_fact_quote: Any,
    selected_facts: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    """Resolve the model's actor reference to one exact selected entity fact."""

    expected_field = {
        "human": "human_actors",
        "external_system": "external_systems",
    }.get(actor_kind)
    selected_quote = str(actor_fact_quote or "")
    matches = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("quote") or "") == selected_quote
        and (
            str(fact.get("field") or "") in {"internal_systems", "title"}
            if actor_kind == "product"
            else str(fact.get("field") or "") == expected_field
        )
    )
    actor_fact = matches[0] if len(matches) == 1 else None
    field = str(actor_fact.get("field") or "") if actor_fact is not None else ""
    if actor_kind == "product":
        valid_field = field in {"internal_systems", "title"}
    else:
        valid_field = bool(expected_field and field == expected_field)
    actor_path = str(actor_fact.get("projection_path") or "") if actor_fact is not None else ""
    actor_quote = str(actor_fact.get("quote") or "") if actor_fact is not None else ""
    if (
        not valid_field
        or not _canonical_actor_path(field=field, path=actor_path)
        or not actor_quote
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound first-path actor fact"
        )
    return actor_path, actor_quote


def _selected_actor_projection_values(
    selected_facts: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str, str]]:
    """Return exact selected entity paths without interpreting their labels."""

    kind_by_field = {
        "human_actors": "human",
        "external_systems": "external_system",
        "internal_systems": "product",
        "title": "product",
    }
    values: dict[str, tuple[str, str]] = {}
    for fact in selected_facts:
        field = str(fact.get("field") or "")
        kind = kind_by_field.get(field)
        if kind is None:
            continue
        path = str(fact.get("projection_path") or "")
        quote = str(fact.get("quote") or "")
        if not _canonical_actor_path(field=field, path=path) or not quote or path in values:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid actor fact identity"
            )
        values[path] = (kind, quote)
    return values


def _selected_owner_projection_values(
    selected_facts: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    values: dict[str, str] = {}
    quote_paths: dict[str, str] = {}
    for fact in selected_facts:
        if str(fact.get("field") or "") not in {"internal_systems", "title"}:
            continue
        path = str(fact.get("projection_path") or "")
        quote = str(fact.get("quote") or "")
        if not _canonical_owner_path(path) or not quote:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid product owner identity"
            )
        existing_path = quote_paths.get(quote)
        if existing_path is not None and existing_path != path:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned duplicate labels for distinct product owners"
            )
        if path in values:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned a duplicate product owner identity"
            )
        quote_paths[quote] = path
        values[path] = quote
    return values


def _canonical_owner_path(path: str) -> bool:
    if path == "/title":
        return True
    prefix = "/internal_systems/"
    index_text = path.removeprefix(prefix) if path.startswith(prefix) else ""
    return bool(index_text.isdigit() and path == f"{prefix}{int(index_text)}")


def _canonical_actor_path(*, field: str, path: str) -> bool:
    if field == "title":
        return path == "/title"
    if field not in {"human_actors", "external_systems", "internal_systems"}:
        return False
    prefix = f"/{field}/"
    index_text = path.removeprefix(prefix) if path.startswith(prefix) else ""
    return bool(index_text.isdigit() and path == f"{prefix}{int(index_text)}")


def _positive_index(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else 0


def _nonnegative_int(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid source custody"
        )
    return value


def _positive_int(value: Any) -> int:
    result = _nonnegative_int(value)
    if result == 0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid source custody"
        )
    return result


def _required_quote(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    return value


def _optional_quote(value: Any, occurrence: Any) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    if text and _positive_index(occurrence) == 0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    if not text and occurrence not in (0, None):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    return text


def _exact_occurrence_start(haystack: bytes, quote: str, occurrence: Any) -> int:
    index = _positive_index(occurrence)
    needle = quote.encode("utf-8")
    if index == 0 or not needle:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path relations"
        )
    cursor = 0
    first = -1
    for _ in range(index):
        found = haystack.find(needle, cursor)
        if found < 0:
            if first >= 0 and haystack.find(needle, first + 1) < 0:
                return first
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned ungrounded first-path relations"
            )
        if first < 0:
            first = found
        cursor = found + 1
    return found


MODEL_FIRST_PATH_RELATION_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 0,
    "maxItems": MAX_FIRST_PATH_RELATIONS,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(MODEL_FIRST_PATH_RELATION_FIELDS),
        "properties": {
            "order": {"type": "integer", "minimum": 1},
            "fact_quote": {"type": "string"},
            "event_quote": {"type": "string"},
            "event_occurrence": {"type": "integer", "minimum": 1},
            "actor_kind": {"type": "string", "enum": list(FIRST_PATH_ACTOR_KINDS)},
            "actor_quote": {"type": "string"},
            "actor_occurrence": {"type": "integer", "minimum": 0},
            "actor_fact_quote": {"type": "string"},
            "owner_system_fact_quote": {"type": "string"},
            "action_verb_quote": {"type": "string"},
            "action_verb_occurrence": {"type": "integer", "minimum": 1},
            "target_quote": {"type": "string"},
            "target_occurrence": {"type": "integer", "minimum": 0},
            "visible_result_quote": {"type": "string"},
            "visible_result_occurrence": {"type": "integer", "minimum": 0},
            "recovery_path": {"type": "boolean"},
        },
    },
}

MODEL_FIRST_PATH_CONTEXT_RELATION_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 0,
    "maxItems": 96,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(MODEL_FIRST_PATH_CONTEXT_RELATION_FIELDS),
        "properties": {
            "fact_field": {"type": "string", "enum": list(_CONTEXT_FIELD_ORDER)},
            "fact_quote": {"type": "string"},
            "first_path_event_order": {"type": "integer", "minimum": 0},
        },
    },
}

MODEL_COMPONENT_RESPONSIBILITY_RELATION_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 0,
    "maxItems": MAX_COMPONENT_RESPONSIBILITY_RELATIONS,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(MODEL_COMPONENT_RESPONSIBILITY_RELATION_FIELDS),
        "properties": {
            "responsibility_fact_quote": {"type": "string"},
            "independent_owner_fact_quote": {"type": "string"},
            "first_path_event_order": {"type": "integer", "minimum": 0},
        },
    },
}


__all__ = [
    "MODEL_COMPONENT_RESPONSIBILITY_RELATION_SCHEMA",
    "MODEL_FIRST_PATH_CONTEXT_RELATION_SCHEMA",
    "MODEL_FIRST_PATH_RELATION_SCHEMA",
    "derive_model_component_responsibility_relations",
    "derive_model_first_path_context_relations",
    "derive_model_first_path_relations",
]
