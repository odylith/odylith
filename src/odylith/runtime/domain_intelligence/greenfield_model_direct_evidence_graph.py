"""Compile one compact model-authored Greenfield evidence graph.

The model selects source facts, typed path events, the terminal result, and
component owners once. This module adds only deterministic custody: exact
coordinates, stable actor paths, and links that follow directly from source
overlap. It never infers product meaning from words or repairs model output.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
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
from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    TERMINAL_RESULT_FACT_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
)


MODEL_EVENT_FIELDS = frozenset(
    {
        "actor_fact_quote",
        "actor_quote",
        "action_quote",
        "target_quote",
        "recovery_path",
    }
)
MODEL_TERMINAL_FIELDS = frozenset(
    {"event_order", "result_quote", "result_occurrence"}
)
MODEL_COMPONENT_FIELDS = frozenset(
    {"responsibility_fact_quote", "owner_fact_quote"}
)
_CONTEXT_KIND_BY_FIELD = {
    "state_object": "state_object",
    "external_systems": "external_system",
    "operational_constraints": "operational_constraint",
}
_CONTEXT_FIELD_ORDER = tuple(_CONTEXT_KIND_BY_FIELD)


@dataclass(frozen=True)
class DerivedModelRelations:
    """Verified sealed relations plus the exact terminal-result source fact."""

    first_path_relations: tuple[dict[str, Any], ...]
    first_path_context_relations: tuple[dict[str, Any], ...]
    component_responsibility_relations: tuple[dict[str, Any], ...]
    terminal_result_fact: dict[str, Any]


def derive_model_relations(
    *,
    events: Any,
    terminal: Any,
    components: Any,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path: str,
    evidence_text: str,
) -> DerivedModelRelations:
    """Compile the compact graph without adding a second semantic author."""

    path_relations, terminal_fact = _derive_events(
        events,
        terminal=terminal,
        selected_facts=selected_facts,
        first_path=first_path,
        evidence_text=evidence_text,
    )
    return DerivedModelRelations(
        first_path_relations=path_relations,
        first_path_context_relations=_derive_context_relations(
            selected_facts=selected_facts,
            first_path_relations=path_relations,
        ),
        component_responsibility_relations=_derive_component_relations(
            components,
            selected_facts=selected_facts,
            first_path_relations=path_relations,
            terminal_result_fact=terminal_fact,
        ),
        terminal_result_fact=terminal_fact,
    )


def _derive_events(
    value: Any,
    *,
    terminal: Any,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path: str,
    evidence_text: str,
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or len(value) > MAX_FIRST_PATH_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid first-path events"
        )
    path_facts = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") == "first_path"
    )
    if (
        not path_facts
        or len(path_facts) != len(value)
        or "\n".join(str(fact.get("quote") or "") for fact in path_facts)
        != first_path
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring must select exactly one first-path fact per event"
        )
    actor_values = _selected_actor_projection_values(selected_facts)
    owner_values = _selected_owner_projection_values(selected_facts)
    rows: list[dict[str, Any]] = []
    seen_source_events: set[tuple[int, int]] = set()
    human_seen = False
    for expected_order, (raw, selected_fact) in enumerate(
        zip(value, path_facts, strict=True), start=1
    ):
        if not isinstance(raw, Mapping) or set(raw) != MODEL_EVENT_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid first-path events"
            )
        event_quote = _required_quote(selected_fact.get("quote"))
        event_length = len(event_quote.encode("utf-8"))
        event_start = _nonnegative_int(selected_fact.get("projection_start_byte"))
        event_end = _positive_int(selected_fact.get("projection_end_byte"))
        source_start = _nonnegative_int(selected_fact.get("source_start_byte"))
        source_end = _positive_int(selected_fact.get("source_end_byte"))
        if event_end - event_start != event_length or source_end - source_start != event_length:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid source custody"
            )
        if any(
            source_start < seen_end and seen_start < source_end
            for seen_start, seen_end in seen_source_events
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned overlapping first-path events"
            )

        actor_quote = _required_quote(raw.get("actor_quote"))
        actor_kind, actor_fact_path, actor_fact_quote = _event_actor_fact(
            actor_fact_quote=raw.get("actor_fact_quote"),
            selected_facts=selected_facts,
        )
        if actor_kind == "product":
            owner_system_path = actor_fact_path
            owner_system_quote = actor_fact_quote
        else:
            owner_system_path = ""
            owner_system_quote = ""
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
        actor_explicit = actor_quote in event_quote
        actor_carried = not actor_explicit
        actor_binding = {
            "actor_kind": actor_kind,
            "actor_quote": actor_quote,
            "actor_fact_path": actor_fact_path,
            "actor_fact_quote": actor_fact_quote,
            "owner_system_path": owner_system_path,
            "owner_system_quote": owner_system_quote,
        }
        previous_binding = rows[-1] if rows else None
        if (
            actor_carried
            and (
                previous_binding is None
                or first_path_actor_binding_identity(previous_binding)
                != first_path_actor_binding_identity(actor_binding)
            )
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path actor"
            )
        action_quote = _required_quote(raw.get("action_quote"))
        target_quote = _optional_quote(raw.get("target_quote"))
        recovery_path = raw.get("recovery_path")
        if (
            actor_kind not in FIRST_PATH_ACTOR_KINDS
            or action_quote not in event_quote
            or (target_quote and target_quote not in event_quote)
            or not isinstance(recovery_path, bool)
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path event"
            )
        human_seen = human_seen or actor_kind == "human"
        rows.append(
            {
                "order": expected_order,
                "source_start_byte": source_start,
                "source_end_byte": source_end,
                "event_start_byte": event_start,
                "event_end_byte": event_end,
                **actor_binding,
                "actor_is_carried": actor_carried,
                "event_quote": event_quote,
                "action_verb_quote": action_quote,
                "target_quote": target_quote,
                "visible_result_quote": "",
                "recovery_path": recovery_path,
            }
        )
        seen_source_events.add((source_start, source_end))
    if (
        not human_seen
        or rows[0]["actor_kind"] != "human"
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring did not type one complete human-first path"
        )
    terminal_fact = _terminal_result_fact(
        terminal,
        selected_facts=selected_facts,
        evidence_text=evidence_text,
        event_count=len(rows),
    )
    rows[-1]["visible_result_quote"] = terminal_fact["terminal_result_quote"]
    return tuple(rows), terminal_fact


def _terminal_result_fact(
    value: Any,
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    evidence_text: str,
    event_count: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != MODEL_TERMINAL_FIELDS:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid terminal result"
    )
    result_quote = _required_quote(value.get("result_quote"))
    result_occurrence = value.get("result_occurrence")
    if (
        value.get("event_order") != event_count
        or not _positive_index(result_occurrence)
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid terminal result"
        )
    evidence = evidence_text.encode("utf-8")
    result_start = _exact_occurrence_start(
        evidence,
        result_quote.encode("utf-8"),
        result_occurrence,
    )
    result_end = result_start + len(result_quote.encode("utf-8"))
    containing_facts = [
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") in TERMINAL_RESULT_FACT_FIELDS
        and _nonnegative_int(fact.get("source_start_byte")) <= result_start
        and result_end <= _positive_int(fact.get("source_end_byte"))
    ]
    exact_facts = [
        fact
        for fact in containing_facts
        if str(fact.get("quote") or "") == result_quote
    ]
    candidates = exact_facts or containing_facts
    if not candidates:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned a terminal result outside its selected facts"
        )
    result_fact = min(
        candidates,
        key=lambda fact: (
            _positive_int(fact.get("source_end_byte"))
            - _nonnegative_int(fact.get("source_start_byte")),
            _positive_int(fact.get("fact_index")),
        ),
    )
    local_start = result_start - _nonnegative_int(
        result_fact.get("source_start_byte")
    )
    projection_start = (
        _nonnegative_int(result_fact.get("projection_start_byte")) + local_start
    )
    return {
        **dict(result_fact),
        "terminal_result_quote": result_quote,
        "terminal_result_source_start_byte": result_start,
        "terminal_result_source_end_byte": result_end,
        "terminal_result_projection_start_byte": projection_start,
        "terminal_result_projection_end_byte": projection_start
        + len(result_quote.encode("utf-8")),
    }


def _derive_context_relations(
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path_relations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for field in _CONTEXT_FIELD_ORDER:
        for fact in selected_facts:
            if str(fact.get("field") or "") != field:
                continue
            overlaps = overlapping_first_path_event_orders(
                source_start=fact.get("source_start_byte"),
                source_end=fact.get("source_end_byte"),
                first_path_relations=first_path_relations,
            )
            rows.append(
                {
                    "context_kind": _CONTEXT_KIND_BY_FIELD[field],
                    "fact_path": str(fact.get("projection_path") or ""),
                    "fact_quote": str(fact.get("quote") or ""),
                    "source_start_byte": _nonnegative_int(
                        fact.get("source_start_byte")
                    ),
                    "source_end_byte": _positive_int(
                        fact.get("source_end_byte")
                    ),
                    "first_path_event_order": next(iter(overlaps))
                    if len(overlaps) == 1
                    else 0,
                }
            )
    return tuple(rows)


def _derive_component_relations(
    value: Any,
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    first_path_relations: Sequence[Mapping[str, Any]],
    terminal_result_fact: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or len(value) > MAX_COMPONENT_RESPONSIBILITY_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid component ownership"
        )
    owner_facts = _unique_facts_by_quote(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") in {"title", "internal_systems"}
    )
    responsibility_facts = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") == "component_responsibilities"
    )
    responsibilities = _unique_facts_by_quote(responsibility_facts)
    rows_by_fact_index: dict[int, dict[str, Any]] = {}
    terminal_rows: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != MODEL_COMPONENT_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid component ownership"
            )
        owner_fact = owner_facts.get(str(raw.get("owner_fact_quote") or ""))
        responsibility_quote = str(raw.get("responsibility_fact_quote") or "")
        responsibility_fact = responsibilities.get(responsibility_quote)
        if owner_fact is None:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an unbound component owner"
            )
        owner_path = str(owner_fact.get("projection_path") or "")
        owner_quote = str(owner_fact.get("quote") or "")
        if not responsibility_quote:
            if responsibility_facts:
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring omitted a selected component responsibility"
                )
            terminal_rows.append(
                {
                    "responsibility_path": str(
                        terminal_result_fact.get("projection_path") or ""
                    ),
                    "responsibility_quote": str(
                        terminal_result_fact.get("terminal_result_quote") or ""
                    ),
                    "owner_system_path": owner_path,
                    "owner_system_quote": owner_quote,
                    "first_path_event_order": len(first_path_relations),
                    "responsibility_source": "terminal_visible_result",
                }
            )
            continue
        if responsibility_fact is None:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an unbound component responsibility"
            )
        fact_index = _positive_index(responsibility_fact.get("fact_index"))
        if fact_index in rows_by_fact_index:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring duplicated component ownership"
            )
        overlaps = overlapping_first_path_event_orders(
            source_start=responsibility_fact.get("source_start_byte"),
            source_end=responsibility_fact.get("source_end_byte"),
            first_path_relations=first_path_relations,
        )
        event_order = next(iter(overlaps)) if len(overlaps) == 1 else 0
        linked_event = (
            first_path_relations[event_order - 1] if event_order else None
        )
        if (
            linked_event is not None
            and str(linked_event.get("actor_kind") or "") == "product"
            and str(linked_event.get("owner_system_path") or "") != owner_path
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring assigned contradictory component owners"
            )
        rows_by_fact_index[fact_index] = {
            "responsibility_path": str(
                responsibility_fact.get("projection_path") or ""
            ),
            "responsibility_quote": responsibility_quote,
            "owner_system_path": owner_path,
            "owner_system_quote": owner_quote,
            "first_path_event_order": event_order,
            "responsibility_source": "accepted_fact",
        }
    expected_indexes = {
        _positive_index(fact.get("fact_index")) for fact in responsibility_facts
    }
    if responsibility_facts:
        if terminal_rows or set(rows_by_fact_index) != expected_indexes:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring left component responsibilities without owners"
            )
        return tuple(
            rows_by_fact_index[index] for index in sorted(expected_indexes)
        )
    if len(terminal_rows) != 1 or rows_by_fact_index:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring did not establish one viable component owner"
        )
    return tuple(terminal_rows)


def _event_actor_fact(
    *,
    actor_fact_quote: Any,
    selected_facts: Sequence[Mapping[str, Any]],
) -> tuple[str, str, str]:
    actor_kind_by_field = {
        "human_actors": "human",
        "external_systems": "external_system",
        "title": "product",
        "internal_systems": "product",
    }
    quote = str(actor_fact_quote or "")
    matches = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") in actor_kind_by_field
        and str(fact.get("quote") or "") == quote
    )
    if len(matches) != 1:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound first-path actor fact"
        )
    fact = matches[0]
    path = str(fact.get("projection_path") or "")
    if not _canonical_actor_path(
        field=str(fact.get("field") or ""), path=path
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid first-path actor fact"
        )
    return actor_kind_by_field[str(fact.get("field") or "")], path, quote


def _selected_actor_projection_values(
    selected_facts: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[str, str]]:
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
        if (
            not _canonical_actor_path(field=field, path=path)
            or not quote
            or path in values
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an invalid actor identity"
            )
        values[path] = (kind, quote)
    return values


def _selected_owner_projection_values(
    selected_facts: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    values: dict[str, str] = {}
    quotes: set[str] = set()
    for fact in selected_facts:
        field = str(fact.get("field") or "")
        if field not in {"title", "internal_systems"}:
            continue
        path = str(fact.get("projection_path") or "")
        quote = str(fact.get("quote") or "")
        if (
            not _canonical_actor_path(field=field, path=path)
            or not quote
            or path in values
            or quote in quotes
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ambiguous product owner"
            )
        values[path] = quote
        quotes.add(quote)
    return values


def _unique_facts_by_quote(
    facts: Iterable[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for fact in facts:
        quote = str(fact.get("quote") or "")
        if not quote or quote in result:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned ambiguous exact fact labels"
            )
        result[quote] = fact
    return result


def _canonical_actor_path(*, field: str, path: str) -> bool:
    if field == "title":
        return path == "/title"
    if field not in {"human_actors", "external_systems", "internal_systems"}:
        return False
    prefix = f"/{field}/"
    index_text = path.removeprefix(prefix) if path.startswith(prefix) else ""
    return bool(index_text.isdigit() and path == f"{prefix}{int(index_text)}")


def _occurrence_starts(haystack: bytes, needle: bytes) -> tuple[int, ...]:
    if not needle:
        return ()
    rows: list[int] = []
    cursor = 0
    while True:
        found = haystack.find(needle, cursor)
        if found < 0:
            return tuple(rows)
        rows.append(found)
        cursor = found + 1


def _exact_occurrence_start(
    haystack: bytes, needle: bytes, occurrence: Any
) -> int:
    index = _positive_index(occurrence)
    starts = _occurrence_starts(haystack, needle)
    if not starts or index == 0:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an ungrounded exact quote"
        )
    if index <= len(starts):
        return starts[index - 1]
    if len(starts) == 1:
        return starts[0]
    raise GreenfieldAuthoredSemanticsError(
        "Greenfield authoring cited an absent quote occurrence"
    )


def _required_quote(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_AUTHORED_FIELD_VALUE_CHARS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid exact quote"
        )
    return value


def _optional_quote(value: Any) -> str:
    if not isinstance(value, str) or len(value) > MAX_AUTHORED_FIELD_VALUE_CHARS:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid exact quote"
        )
    return value


def _positive_index(value: Any) -> int:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 1
        else 0
    )


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


def _array_schema(
    items: Mapping[str, Any], *, maximum: int
) -> dict[str, Any]:
    return {"type": "array", "maxItems": maximum, "items": dict(items)}


def _quote_schema(*, required: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "string",
        "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
    }
    if required:
        schema["minLength"] = 1
    return schema


MODEL_EVENT_SCHEMA: dict[str, Any] = _array_schema(
    {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(MODEL_EVENT_FIELDS),
        "properties": {
            "actor_fact_quote": _quote_schema(required=True),
            "actor_quote": _quote_schema(required=True),
            "action_quote": _quote_schema(required=True),
            "target_quote": _quote_schema(),
            "recovery_path": {"type": "boolean"},
        },
    },
    maximum=MAX_FIRST_PATH_RELATIONS,
)

MODEL_TERMINAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(MODEL_TERMINAL_FIELDS),
    "properties": {
        "event_order": {"type": "integer", "minimum": 0},
        "result_quote": _quote_schema(),
        "result_occurrence": {"type": "integer", "minimum": 0},
    },
}

MODEL_COMPONENT_SCHEMA: dict[str, Any] = _array_schema(
    {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(MODEL_COMPONENT_FIELDS),
        "properties": {
            "responsibility_fact_quote": _quote_schema(),
            "owner_fact_quote": _quote_schema(required=True),
        },
    },
    maximum=MAX_COMPONENT_RESPONSIBILITY_RELATIONS,
)


__all__ = [
    "MODEL_COMPONENT_SCHEMA",
    "MODEL_EVENT_SCHEMA",
    "MODEL_TERMINAL_SCHEMA",
    "DerivedModelRelations",
    "derive_model_relations",
]
