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
    component_responsibility_owners: Sequence[str] | None = None,
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
    source_relations = tuple(
        first_path_relations or _default_first_path_relations(intent)
    )
    path_segments = (
        [str(row).strip() for row in first_path_segments]
        if first_path_segments is not None
        else [first_path]
    )
    relation_rows = _relation_rows(
        source_relations,
        first_path_segments=(
            path_segments
        ),
        first_path_fact_indexes=first_path_fact_indexes,
        fact_indexes=fact_indexes,
        intent=intent,
    )
    terminal = _terminal_row(
        relations=source_relations,
        facts=facts,
        evidence_text=evidence_text,
    )
    components = _component_responsibility_relation_rows(
        intent=intent,
        fact_indexes=fact_indexes,
        owners=component_responsibility_owners,
        terminal_owner=terminal_component_owner,
    )
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "status": "authored",
        "facts": facts,
        "events": relation_rows,
        "terminal": terminal,
        "components": components,
        "assumptions": list(intent.get("assumptions") or []),
        "ambiguities": list(intent.get("ambiguities") or []),
        "consistency": {"status": "consistent", "conflicting_quotes": []},
        "clarification": None,
    }


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
        "events": [],
        "terminal": {
            "event_order": 0,
            "result_quote": "",
            "result_occurrence": 0,
        },
        "components": [],
        "assumptions": [],
        "ambiguities": [],
        "consistency": {
            "status": consistency_status,
            "conflicting_quotes": [str(quote) for quote in conflicting_quotes],
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
                "event_quote": event_quote,
                "actor_kind": actor_kind,
                "actor_fact_quote": _actor_fact_quote(
                    relation,
                    actor_kind=actor_kind,
                    actor_quote=actor_quote,
                    fact_indexes=fact_indexes,
                    intent=intent,
                ),
                "actor_quote": actor_quote,
                "actor_carried": actor_quote not in event_quote,
                "action_quote": action_quote,
                "target_quote": target_quote,
                "recovery_path": bool(relation.get("recovery_path")),
            }
        )
    return rows


def _terminal_row(
    *,
    relations: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
    evidence_text: str,
) -> dict[str, Any]:
    visible_rows = [
        (order, str(relation.get("visible_result_quote") or ""))
        for order, relation in enumerate(relations, start=1)
        if str(relation.get("visible_result_quote") or "")
    ]
    if not visible_rows:
        raise ValueError("authored fixture requires one terminal visible result")
    event_order, result_quote = visible_rows[-1]
    proof_fact = next(
        (
            fact
            for fact in facts
            if result_quote in str(fact.get("quote") or "")
        ),
        None,
    )
    if proof_fact is None:
        raise ValueError(
            "authored fixture terminal result requires a selected proof fact"
        )
    result_occurrence = 1
    if evidence_text:
        evidence = evidence_text.encode("utf-8")
        proof_quote = str(proof_fact["quote"]).encode("utf-8")
        result = result_quote.encode("utf-8")
        fact_start = _nth_start(
            evidence,
            proof_quote,
            int(proof_fact["occurrence"]),
        )
        local_start = proof_quote.find(result)
        if local_start < 0:
            raise ValueError("authored fixture result is outside its proof fact")
        result_occurrence = _occurrence_at_offset(
            evidence,
            result,
            fact_start + local_start,
        )
    return {
        "event_order": event_order,
        "result_quote": result_quote,
        "result_occurrence": result_occurrence,
    }


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


def _component_responsibility_relation_rows(
    *,
    intent: Mapping[str, Any],
    fact_indexes: Mapping[str, int],
    owners: Sequence[str] | None,
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
        return [
            {
                "responsibility_fact_quote": "",
                "owner_fact_quote": _owner_fact_quote(
                    owner=terminal_owner,
                    intent=intent,
                    systems=systems,
                    fact_indexes=fact_indexes,
                ),
            }
        ]
    if owners is None:
        raise ValueError(
            "authored fixture must explicitly bind component_responsibility_owners"
        )
    owner_values = [str(owner) for owner in owners]
    if len(owner_values) != len(responsibilities):
        raise ValueError("authored fixture must bind every component responsibility exactly once")
    rows: list[dict[str, Any]] = []
    for index, owner in enumerate(owner_values):
        responsibility_fact_index = fact_indexes.get(
            f"/component_responsibilities/{index}",
            0,
        )
        owner_fact_quote = _owner_fact_quote(
            owner=owner,
            intent=intent,
            systems=systems,
            fact_indexes=fact_indexes,
        )
        if not responsibility_fact_index or not owner_fact_quote:
            raise ValueError("authored fixture component responsibility owner is not a selected fact")
        rows.append(
            {
                "responsibility_fact_quote": responsibilities[index],
                "owner_fact_quote": owner_fact_quote,
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


def _occurrence_at_offset(source: bytes, quote: bytes, offset: int) -> int:
    starts: list[int] = []
    cursor = 0
    while True:
        found = source.find(quote, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + 1
    try:
        return starts.index(offset) + 1
    except ValueError as exc:
        raise ValueError("authored fixture result offset is not source grounded") from exc
