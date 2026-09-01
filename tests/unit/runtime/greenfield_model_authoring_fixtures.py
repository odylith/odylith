"""Shared structured-provider fixtures for Greenfield model-authoring tests."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)


class StructuredAuthoringProvider:
    """Return a fixed model response without manufacturing custody coordinates."""

    provider_name = "codex-cli"

    def __init__(self, response: Mapping[str, Any] | None) -> None:
        self.response = response
        self.calls = 0

    def generate_structured(self, *, request: object) -> Mapping[str, Any] | None:
        self.last_request_model = str(getattr(request, "model", ""))
        self.last_request_reasoning_effort = str(getattr(request, "reasoning_effort", ""))
        self.calls += 1
        return copy.deepcopy(dict(self.response)) if self.response is not None else None


def authored_response(
    intent: Mapping[str, Any],
    *,
    evidence_text: str = "",
    first_path_segments: Sequence[str] | None = None,
    first_path_relations: Sequence[Mapping[str, Any]] | None = None,
    first_path_context_event_orders: Mapping[str, int] | None = None,
    component_responsibility_owners: Sequence[str] | None = None,
    component_responsibility_event_orders: Sequence[int] | None = None,
    terminal_component_owner: str | None = None,
) -> dict[str, Any]:
    """Build a model-shaped response using quotes and occurrence ordinals only."""

    facts: list[dict[str, Any]] = []
    fact_indexes: dict[str, int] = {}
    first_path_fact_indexes: list[int] = []
    for field, value in intent.items():
        if field in {"assumptions", "ambiguities"}:
            continue
        rows = (
            list(first_path_segments)
            if field == "first_path" and first_path_segments is not None
            else value if isinstance(value, list) else [value]
        )
        for row_index, row in enumerate(rows):
            quote = str(row).strip()
            if not quote:
                continue
            fact_index = len(facts) + 1
            projection_path = f"/{field}" if not isinstance(value, list) else f"/{field}/{row_index}"
            facts.append({"field": field, "quote": quote, "occurrence": 1})
            fact_indexes[projection_path] = fact_index
            if field == "first_path":
                first_path_fact_indexes.append(fact_index)

    first_path = str(intent.get("first_path") or "").strip()
    relation_rows = _relation_rows(
        first_path_relations or _default_first_path_relations(intent),
        first_path_segments=(
            [str(row).strip() for row in first_path_segments]
            if first_path_segments is not None
            else [first_path]
        ),
        first_path_fact_indexes=first_path_fact_indexes,
        fact_indexes=fact_indexes,
        intent=intent,
    )
    first_path_context_relations = _first_path_context_relation_rows(
        intent=intent,
        fact_indexes=fact_indexes,
        relations=relation_rows,
        event_orders=first_path_context_event_orders,
    )
    if evidence_text:
        _bind_context_fact_occurrences(
            evidence_text=evidence_text,
            facts=facts,
            relations=relation_rows,
            context_relations=first_path_context_relations,
        )
    component_responsibility_relations = _component_responsibility_relation_rows(
        intent=intent,
        fact_indexes=fact_indexes,
        owners=component_responsibility_owners,
        event_orders=component_responsibility_event_orders,
        relation_rows=relation_rows,
        terminal_owner=terminal_component_owner,
    )
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "status": "authored",
        "facts": facts,
        "first_path_relations": relation_rows,
        "first_path_context_relations": first_path_context_relations,
        "component_responsibility_relations": component_responsibility_relations,
        "assumptions": list(intent.get("assumptions") or []),
        "ambiguities": list(intent.get("ambiguities") or []),
        "consistency_assessment": {"status": "consistent", "conflicting_quotes": []},
        "clarification": None,
    }


def _bind_context_fact_occurrences(
    *,
    evidence_text: str,
    facts: Sequence[dict[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
) -> None:
    """Make linked fixture facts cite the exact occurrence inside their event."""

    evidence = evidence_text.encode("utf-8")
    relations_by_order = {int(row["order"]): row for row in relations}
    for context in context_relations:
        event_order = int(context["first_path_event_order"])
        if not event_order:
            continue
        fact = next(
            row
            for row in facts
            if row["field"] == context["fact_field"]
            and row["quote"] == context["fact_quote"]
        )
        relation = relations_by_order[event_order]
        path_fact = next(
            row
            for row in facts
            if row["field"] == "first_path"
            and row["quote"] == relation["fact_quote"]
        )
        path_quote = str(path_fact["quote"]).encode("utf-8")
        event_quote = str(relation["event_quote"]).encode("utf-8")
        fact_quote = str(fact["quote"]).encode("utf-8")
        path_start = _nth_start(evidence, path_quote, int(path_fact["occurrence"]))
        event_start = _nth_start(
            path_quote,
            event_quote,
            int(relation["event_occurrence"]),
        )
        fact_start = event_quote.find(fact_quote)
        if fact_start < 0:
            continue
        absolute_start = path_start + event_start + fact_start
        fact["occurrence"] = sum(
            1
            for offset in range(absolute_start + 1)
            if evidence.startswith(fact_quote, offset)
        )


def clarification_response(
    *,
    question: str,
    material_dimension: str,
    consistency_status: str = "consistent",
    conflicting_quotes: Sequence[str] = (),
) -> dict[str, Any]:
    """Return a clarification response; the question remains test-only metadata."""

    del question
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "status": "clarification_required",
        "facts": [],
        "first_path_relations": [],
        "first_path_context_relations": [],
        "component_responsibility_relations": [],
        "assumptions": [],
        "ambiguities": [],
        "consistency_assessment": {
            "status": consistency_status,
            "conflicting_quotes": [
                {"quote": str(quote), "occurrence": 1}
                for quote in conflicting_quotes
            ],
        },
        "clarification": {"material_dimension": material_dimension},
    }


def _relation_rows(
    relations: Sequence[Mapping[str, Any]],
    *,
    first_path_segments: Sequence[str],
    first_path_fact_indexes: Sequence[int],
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for order, relation in enumerate(relations, start=1):
        event_quote = str(relation.get("event_quote") or "")
        actor_quote = str(relation.get("actor_quote") or "")
        action_quote = str(relation.get("action_verb_quote") or "")
        target_quote = str(relation.get("target_quote") or "")
        visible_quote = str(relation.get("visible_result_quote") or "")
        actor_kind = str(relation.get("actor_kind") or "")
        segment_index = relation.get("segment_index")
        if isinstance(segment_index, int) and not isinstance(segment_index, bool):
            selected_segment_index = segment_index
        else:
            matches = [
                index
                for index, segment in enumerate(first_path_segments)
                if _occurrence(segment, event_quote)
            ]
            if len(matches) != 1:
                raise ValueError(
                    "authored fixture relation must identify exactly one first_path segment"
                )
            selected_segment_index = matches[0]
        if selected_segment_index < 0 or selected_segment_index >= len(first_path_fact_indexes):
            raise ValueError("authored fixture relation references an unknown first_path segment")
        selected_segment = str(first_path_segments[selected_segment_index])
        rows.append(
            {
                "order": order,
                "fact_quote": selected_segment,
                "event_quote": event_quote,
                "event_occurrence": _occurrence(selected_segment, event_quote),
                "actor_kind": actor_kind,
                "actor_quote": actor_quote,
                "actor_occurrence": _occurrence(event_quote, actor_quote),
                "actor_fact_quote": _actor_fact_quote(
                    relation,
                    actor_kind=actor_kind,
                    actor_quote=actor_quote,
                    fact_indexes=fact_indexes,
                    intent=intent,
                ),
                "owner_system_fact_quote": _owner_system_fact_quote(
                    relation,
                    actor_kind=actor_kind,
                    fact_indexes=fact_indexes,
                    intent=intent,
                ),
                "action_verb_quote": action_quote,
                "action_verb_occurrence": _occurrence(event_quote, action_quote),
                "target_quote": target_quote,
                "target_occurrence": _occurrence(event_quote, target_quote) if target_quote else 0,
                "visible_result_quote": visible_quote,
                "visible_result_occurrence": _occurrence(event_quote, visible_quote) if visible_quote else 0,
                "recovery_path": bool(relation.get("recovery_path")),
            }
        )
    return rows


def _actor_fact_quote(
    relation: Mapping[str, Any],
    *,
    actor_kind: str,
    actor_quote: str,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> str:
    if actor_kind == "product":
        return _owner_system_fact_quote(
            relation,
            actor_kind=actor_kind,
            fact_indexes=fact_indexes,
            intent=intent,
        )
    field = {
        "human": "human_actors",
        "external_system": "external_systems",
    }.get(actor_kind)
    if field is None:
        raise ValueError(f"unknown authored fixture actor_kind: {actor_kind}")
    selected_quote = str(relation.get("actor_fact_quote") or actor_quote)
    rows = [str(row) for row in intent.get(field, []) if str(row)]
    matches = [index for index, row in enumerate(rows) if row == selected_quote]
    if len(matches) != 1:
        raise ValueError("authored fixture actor must identify one exact selected entity fact")
    if not fact_indexes.get(f"/{field}/{matches[0]}", 0):
        raise ValueError("authored fixture actor fact is not selected")
    return selected_quote


def _owner_system_fact_quote(
    relation: Mapping[str, Any],
    *,
    actor_kind: str,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> str:
    if actor_kind != "product":
        return ""
    owner = str(relation.get("owner_system_quote") or "")
    systems = [str(row) for row in intent.get("internal_systems", []) if str(row)]
    if not owner:
        raise ValueError("authored fixture must explicitly bind every product event to owner_system_quote")
    if owner == str(intent.get("title") or ""):
        if fact_indexes.get("/title", 0):
            return owner
    for index, system in enumerate(systems):
        if owner == system and fact_indexes.get(f"/internal_systems/{index}", 0):
            return owner
    raise ValueError(f"unknown authored fixture owner_system_quote: {owner}")


def _first_path_context_relation_rows(
    *,
    intent: Mapping[str, Any],
    fact_indexes: Mapping[str, int],
    relations: Sequence[Mapping[str, Any]],
    event_orders: Mapping[str, int] | None,
) -> list[dict[str, Any]]:
    overrides = dict(event_orders or {})
    rows: list[dict[str, Any]] = []
    for field in ("state_object", "external_systems", "operational_constraints"):
        value = intent.get(field)
        values = value if isinstance(value, list) else [value]
        for index, raw in enumerate(values):
            quote = str(raw or "").strip()
            if not quote:
                continue
            path = f"/{field}/{index}" if isinstance(value, list) else f"/{field}"
            if path in overrides:
                event_order = overrides[path]
            else:
                matching_orders = [
                    int(relation["order"])
                    for relation in relations
                    if quote in str(relation.get("event_quote") or "")
                ]
                event_order = matching_orders[0] if matching_orders else (1 if field == "state_object" else 0)
            if not isinstance(event_order, int) or isinstance(event_order, bool) or event_order < 0:
                raise ValueError("authored fixture context event order is invalid")
            fact_index = fact_indexes.get(path, 0)
            if not fact_index:
                raise ValueError("authored fixture context fact is not selected")
            rows.append(
                {
                    "fact_field": field,
                    "fact_quote": quote,
                    "first_path_event_order": event_order,
                }
            )
    return rows


def _component_responsibility_relation_rows(
    *,
    intent: Mapping[str, Any],
    fact_indexes: Mapping[str, int],
    owners: Sequence[str] | None,
    event_orders: Sequence[int] | None,
    relation_rows: Sequence[Mapping[str, Any]],
    terminal_owner: str | None,
) -> list[dict[str, Any]]:
    responsibilities = [
        str(row)
        for row in intent.get("component_responsibilities", [])
        if str(row)
    ]
    systems = [str(row) for row in intent.get("internal_systems", []) if str(row)]
    if not responsibilities:
        if not terminal_owner:
            raise ValueError(
                "authored fixture must explicitly bind a terminal component owner when no responsibility fact exists"
            )
        terminal_order = next(
            (
                int(row["order"])
                for row in reversed(tuple(relation_rows))
                if str(row.get("visible_result_quote") or "")
            ),
            0,
        )
        if not terminal_order:
            raise ValueError("authored fixture terminal component owner requires a visible-result event")
        return [
            {
                "responsibility_fact_quote": "",
                "independent_owner_fact_quote": "",
                "first_path_event_order": terminal_order,
            }
        ]
    if owners is None:
        raise ValueError(
            "authored fixture must explicitly bind component_responsibility_owners"
        )
    owner_values = [str(owner) for owner in owners]
    if len(owner_values) != len(responsibilities):
        raise ValueError("authored fixture must bind every component responsibility exactly once")
    order_values = list(event_orders) if event_orders is not None else [0] * len(responsibilities)
    if (
        len(order_values) != len(responsibilities)
        or any(not isinstance(order, int) or isinstance(order, bool) or order < 0 for order in order_values)
    ):
        raise ValueError("authored fixture must bind each responsibility to one valid event order")
    rows: list[dict[str, Any]] = []
    for index, (owner, event_order) in enumerate(zip(owner_values, order_values, strict=True)):
        responsibility_fact_index = fact_indexes.get(
            f"/component_responsibilities/{index}",
            0,
        )
        linked_event = next(
            (row for row in relation_rows if int(row["order"]) == event_order),
            None,
        )
        inherits_product_owner = (
            linked_event is not None
            and str(linked_event.get("actor_kind") or "") == "product"
        )
        independent_owner_fact_quote = (
            ""
            if inherits_product_owner
            else _owner_fact_quote(
                owner=owner,
                intent=intent,
                systems=systems,
                fact_indexes=fact_indexes,
            )
        )
        if not responsibility_fact_index or (
            not inherits_product_owner and not independent_owner_fact_quote
        ):
            raise ValueError("authored fixture component responsibility owner is not a selected fact")
        rows.append(
            {
                "responsibility_fact_quote": responsibilities[index],
                "independent_owner_fact_quote": independent_owner_fact_quote,
                "first_path_event_order": event_order,
            }
        )
    return rows


def _owner_fact_quote(
    *,
    owner: str,
    intent: Mapping[str, Any],
    systems: Sequence[str],
    fact_indexes: Mapping[str, int],
) -> str:
    if owner == str(intent.get("title") or ""):
        path = "/title"
    else:
        try:
            path = f"/internal_systems/{systems.index(owner)}"
        except ValueError as exc:
            raise ValueError(
                f"unknown authored fixture component responsibility owner: {owner}"
            ) from exc
    fact_index = fact_indexes.get(path, 0)
    if not fact_index:
        raise ValueError("authored fixture component owner is not a selected fact")
    return owner


def _default_first_path_relations(intent: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    first_path = str(intent.get("first_path") or "").strip()
    actors = intent.get("human_actors") or []
    human_actor = str(actors[0]).strip() if actors else ""
    return (
        {
            "actor_kind": "human",
            "actor_quote": human_actor,
            "event_quote": first_path,
            "action_verb_quote": first_path,
            "target_quote": "",
            "visible_result_quote": first_path,
            "recovery_path": False,
        },
    )


def _occurrence(source: str, quote: str) -> int:
    return 1 if quote and source.encode("utf-8").find(quote.encode("utf-8")) >= 0 else 0


def _nth_start(source: bytes, quote: bytes, occurrence: int) -> int:
    cursor = 0
    found = -1
    for _ in range(occurrence):
        found = source.find(quote, cursor)
        if found < 0:
            raise ValueError("authored fixture quote occurrence is not present")
        cursor = found + 1
    return found
