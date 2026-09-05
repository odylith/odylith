"""Compile one compact model-authored Greenfield evidence graph.

The model selects source facts, typed path events, the terminal result, and
component owners once. This module adds only deterministic custody: exact
coordinates, stable actor paths, and links that follow directly from source
overlap. It never infers product meaning from words or repairs model output.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    FIRST_PATH_ACTOR_KINDS,
    MAX_COMPONENT_RESPONSIBILITY_RELATIONS,
    MAX_FIRST_PATH_RELATIONS,
    GreenfieldAuthoredSemanticsError,
    canonical_product_owner_projection_values,
    first_path_actor_binding_identity,
    overlapping_first_path_event_orders,
)
from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    TERMINAL_RESULT_FACT_FIELDS,
    event_target_is_source_bound,
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
    }
)
MODEL_TERMINAL_FIELDS = frozenset({"result_quote", "result_occurrence"})
MODEL_COMPONENT_FIELDS = frozenset({"owner_fact_quote", "responsibilities"})
MODEL_COMPONENT_RESPONSIBILITY_FIELDS = frozenset({"quote", "occurrence"})
_CONTEXT_KIND_BY_FIELD = {
    "state_object": "state_object",
    "external_systems": "external_system",
    "operational_constraints": "operational_constraint",
}
_CONTEXT_FIELD_ORDER = tuple(_CONTEXT_KIND_BY_FIELD)


class GreenfieldComponentOwnershipError(GreenfieldAuthoredSemanticsError):
    """A source-bound responsibility conflicts with its typed event owner."""


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


def model_component_responsibility_rows(value: Any) -> tuple[dict[str, Any], ...]:
    """Flatten structurally owner-bound model citations without changing meaning."""

    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not value
        or len(value) > MAX_COMPONENT_RESPONSIBILITY_RELATIONS
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid component ownership"
        )
    rows: list[dict[str, Any]] = []
    empty_group_count = 0
    owner_fact_quotes: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != MODEL_COMPONENT_FIELDS:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid component ownership"
            )
        owner_fact_quote = _required_quote(raw.get("owner_fact_quote"))
        if owner_fact_quote in owner_fact_quotes:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid component ownership"
            )
        owner_fact_quotes.add(owner_fact_quote)
        responsibilities = raw.get("responsibilities")
        if (
            not isinstance(responsibilities, Sequence)
            or isinstance(responsibilities, (str, bytes, bytearray))
            or len(responsibilities) > MAX_COMPONENT_RESPONSIBILITY_RELATIONS
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned invalid component ownership"
            )
        if not responsibilities:
            empty_group_count += 1
            rows.append(
                {
                    "owner_fact_quote": owner_fact_quote,
                    "responsibility_quote": "",
                    "responsibility_occurrence": 0,
                }
            )
            continue
        for responsibility in responsibilities:
            if (
                not isinstance(responsibility, Mapping)
                or set(responsibility) != MODEL_COMPONENT_RESPONSIBILITY_FIELDS
            ):
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring returned invalid component ownership"
                )
            rows.append(
                {
                    "owner_fact_quote": owner_fact_quote,
                    "responsibility_quote": _required_quote(
                        responsibility.get("quote")
                    ),
                    "responsibility_occurrence": _positive_index(
                        responsibility.get("occurrence")
                    ),
                }
            )
    responsibility_count = sum(
        bool(row["responsibility_quote"])
        for row in rows
    )
    if (
        len(rows) > MAX_COMPONENT_RESPONSIBILITY_RELATIONS
        or (responsibility_count and empty_group_count)
        or (not responsibility_count and (len(value) != 1 or len(rows) != 1))
        or any(
            row["responsibility_quote"] and not row["responsibility_occurrence"]
            for row in rows
        )
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned invalid component ownership"
        )
    return tuple(rows)


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
    event_rows = tuple(value)
    path_facts = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") == "first_path"
    )
    if (
        not path_facts
        or len(path_facts) != len(event_rows)
        or "\n".join(str(fact.get("quote") or "") for fact in path_facts)
        != first_path
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring must select exactly one first-path fact per event"
        )
    owner_facts = _selected_product_owner_facts(selected_facts)
    rows: list[dict[str, Any]] = []
    seen_source_events: set[tuple[int, int]] = set()
    for expected_order, (raw, selected_fact) in enumerate(
        zip(event_rows, path_facts, strict=True), start=1
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

        actor_kind, actor_fact_path, actor_fact_quote = _event_actor_fact(
            actor_fact_quote=raw.get("actor_fact_quote"),
            selected_facts=selected_facts,
            product_owner_facts=owner_facts,
        )
        if actor_kind == "product":
            owner_system_path = actor_fact_path
            owner_system_quote = actor_fact_quote
        else:
            owner_system_path = ""
            owner_system_quote = ""
        actor_quote = _required_quote(raw.get("actor_quote"))
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
                actor_quote != actor_fact_quote
                or previous_binding is None
                or first_path_actor_binding_identity(previous_binding)
                != first_path_actor_binding_identity(actor_binding)
            )
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path actor"
            )
        action_quote = _required_quote(raw.get("action_quote"))
        target_quote = _event_target_quote(
            raw.get("target_quote"),
            event_quote=event_quote,
            selected_facts=selected_facts,
        )
        if (
            actor_kind not in FIRST_PATH_ACTOR_KINDS
            or action_quote not in event_quote
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ungrounded first-path event"
            )
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
            }
        )
        seen_source_events.add((source_start, source_end))
    terminal_fact = _terminal_result_fact(
        terminal,
        selected_facts=selected_facts,
        evidence_text=evidence_text,
    )
    rows[-1]["visible_result_quote"] = terminal_fact["terminal_result_quote"]
    return tuple(rows), terminal_fact


def _terminal_result_fact(
    value: Any,
    *,
    selected_facts: Sequence[Mapping[str, Any]],
    evidence_text: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != MODEL_TERMINAL_FIELDS:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid terminal result"
    )
    result_quote = _required_quote(value.get("result_quote"))
    result_occurrence = value.get("result_occurrence")
    if not _positive_index(result_occurrence):
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
    model_rows = model_component_responsibility_rows(value)
    owner_facts = _selected_product_owner_facts(selected_facts)
    responsibility_facts = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") == "component_responsibilities"
    )
    if responsibility_facts and len(model_rows) != len(responsibility_facts):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring left component responsibilities without owners"
        )
    if not responsibility_facts and (
        len(model_rows) != 1 or model_rows[0]["responsibility_quote"]
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring did not establish one viable component owner"
        )
    rows: list[dict[str, Any]] = []
    aligned_facts: Sequence[Mapping[str, Any] | None] = (
        responsibility_facts if responsibility_facts else (None,)
    )
    for raw, responsibility_fact in zip(model_rows, aligned_facts, strict=True):
        owner_fact = owner_facts.get(str(raw.get("owner_fact_quote") or ""))
        if owner_fact is None:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an unbound component owner"
            )
        owner_path = str(owner_fact.get("projection_path") or "")
        owner_quote = str(owner_fact.get("quote") or "")
        if responsibility_fact is None:
            rows.append(
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
        responsibility_quote = str(responsibility_fact.get("quote") or "")
        if responsibility_quote != raw["responsibility_quote"]:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring left component responsibilities without owners"
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
        responsibility_start = _nonnegative_int(
            responsibility_fact.get("source_start_byte")
        )
        responsibility_end = _positive_int(
            responsibility_fact.get("source_end_byte")
        )
        responsibility_is_event_bound = (
            linked_event is not None
            and _nonnegative_int(linked_event.get("source_start_byte"))
            <= responsibility_start
            and responsibility_end
            <= _positive_int(linked_event.get("source_end_byte"))
        )
        if (
            responsibility_is_event_bound
            and str(linked_event.get("actor_kind") or "") != "product"
        ):
            raise GreenfieldComponentOwnershipError(
                "Greenfield authoring assigned a non-product event as a component responsibility"
            )
        if (
            linked_event is not None
            and str(linked_event.get("actor_kind") or "") == "product"
            and str(linked_event.get("owner_system_path") or "") != owner_path
        ):
            raise GreenfieldComponentOwnershipError(
                "Greenfield authoring assigned contradictory component owners"
            )
        rows.append(
            {
                "responsibility_path": str(
                    responsibility_fact.get("projection_path") or ""
                ),
                "responsibility_quote": responsibility_quote,
                "owner_system_path": owner_path,
                "owner_system_quote": owner_quote,
                "first_path_event_order": event_order,
                "responsibility_source": "accepted_fact",
            }
        )
    return tuple(rows)


def _event_actor_fact(
    *,
    actor_fact_quote: Any,
    selected_facts: Sequence[Mapping[str, Any]],
    product_owner_facts: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, str]:
    non_product_kind_by_field = {
        "human_actors": "human",
        "external_systems": "external_system",
    }
    quote = str(actor_fact_quote or "")
    non_product_matches = tuple(
        fact
        for fact in selected_facts
        if str(fact.get("field") or "") in non_product_kind_by_field
        and str(fact.get("quote") or "") == quote
    )
    product_fact = product_owner_facts.get(quote)
    if (product_fact is None and len(non_product_matches) != 1) or (
        product_fact is not None and non_product_matches
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an unbound first-path actor fact"
        )
    fact = product_fact or non_product_matches[0]
    field = str(fact.get("field") or "")
    path = str(fact.get("projection_path") or "")
    if not _canonical_actor_path(field=field, path=path):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an invalid first-path actor fact"
        )
    actor_kind = "product" if product_fact is not None else non_product_kind_by_field[field]
    return actor_kind, path, quote


def _event_target_quote(
    value: Any,
    *,
    event_quote: str,
    selected_facts: Sequence[Mapping[str, Any]],
) -> str:
    target_quote = _optional_quote(value)
    if not event_target_is_source_bound(
        event_quote=event_quote,
        target_quote=target_quote,
    ):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield authoring returned an ungrounded first-path event"
        )
    return target_quote


def _selected_product_owner_facts(
    selected_facts: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    facts_by_path: dict[str, Mapping[str, Any]] = {}
    title = ""
    internal_facts: list[Mapping[str, Any]] = []
    for fact in selected_facts:
        field = str(fact.get("field") or "")
        if field not in {"title", "internal_systems"}:
            continue
        path = str(fact.get("projection_path") or "")
        quote = str(fact.get("quote") or "")
        if (
            not _canonical_actor_path(field=field, path=path)
            or not quote
            or path in facts_by_path
        ):
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield authoring returned an ambiguous product owner"
            )
        facts_by_path[path] = fact
        if field == "title":
            title = quote
        else:
            expected_path = f"/internal_systems/{len(internal_facts)}"
            if path != expected_path:
                raise GreenfieldAuthoredSemanticsError(
                    "Greenfield authoring returned an ambiguous product owner"
                )
            internal_facts.append(fact)
    owner_values = canonical_product_owner_projection_values(
        title=title,
        internal_systems=tuple(str(fact.get("quote") or "") for fact in internal_facts),
    )
    return {
        quote: facts_by_path[path]
        for path, quote in owner_values.items()
    }


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


_EVENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(MODEL_EVENT_FIELDS),
    "properties": {
        "actor_fact_quote": _quote_schema(required=True),
        "actor_quote": _quote_schema(required=True),
        "action_quote": _quote_schema(required=True),
        "target_quote": _quote_schema(),
    },
}

MODEL_EVENT_SCHEMA: dict[str, Any] = {
    **_array_schema(_EVENT_SCHEMA, maximum=MAX_FIRST_PATH_RELATIONS),
    "minItems": 1,
}

MODEL_TERMINAL_SCHEMA: dict[str, Any] = {
    "anyOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(MODEL_TERMINAL_FIELDS),
            "properties": {
                "result_quote": {
                    **_quote_schema(required=True),
                    "description": (
                        "One exact source phrase naming the observable output or reviewable "
                        "state produced by the completed path. An action, workflow stage, "
                        "goal, or product label is not a result."
                    ),
                },
                "result_occurrence": {"type": "integer", "minimum": 1},
            },
        },
        {"type": "null"},
    ]
}

MODEL_COMPONENT_SCHEMA: dict[str, Any] = {
    **_array_schema(
        {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(MODEL_COMPONENT_FIELDS),
            "properties": {
                "owner_fact_quote": _quote_schema(required=True),
                "responsibilities": _array_schema(
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": sorted(MODEL_COMPONENT_RESPONSIBILITY_FIELDS),
                        "properties": {
                            "quote": _quote_schema(required=True),
                            "occurrence": {"type": "integer", "minimum": 1},
                        },
                    },
                    maximum=MAX_COMPONENT_RESPONSIBILITY_RELATIONS,
                ),
            },
        },
        maximum=MAX_COMPONENT_RESPONSIBILITY_RELATIONS,
    ),
    "minItems": 1,
}


__all__ = [
    "MODEL_COMPONENT_SCHEMA",
    "MODEL_EVENT_SCHEMA",
    "MODEL_TERMINAL_SCHEMA",
    "DerivedModelRelations",
    "GreenfieldComponentOwnershipError",
    "derive_model_relations",
    "model_component_responsibility_rows",
]
