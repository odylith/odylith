"""Compile a validated Greenfield source-meaning graph into Semantic Intent IR.

This module owns the deterministic graph-to-IR projection. It consumes only
typed entity identities, bindings, and effect edges accepted by the source
meaning validator; it does not interpret or repair source wording.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_narrative_projection import (
    project_semantic_narratives,
)


def compile_semantic_source_meaning(
    graph: Mapping[str, Any],
    *,
    semantic_intent_ir_version: str,
) -> dict[str, Any]:
    """Compile node-owned effects into causal Semantic Intent relations."""

    clarification = graph["clarification"]
    if clarification.get("required") is True:
        return {
            "version": semantic_intent_ir_version,
            "status": "clarification_required",
            "presentation": dict(graph["presentation"]),
            "clarification": {
                "question": str(clarification["question"]),
                "source_refs": list(clarification["source_refs"]),
            },
            "facts": [],
            "relations": [],
            "narratives": [],
        }
    facts, relations = _source_fact_graph(graph)
    narrative_facts = [
        {**row, "candidate_ids": ["source-meaning"]} for row in facts
    ]
    grouped_facts = {
        "audiences": _of_kind(narrative_facts, "audience"),
        "actors": _of_kind(narrative_facts, "actor"),
        "entities": _of_kind(narrative_facts, "entity"),
        "workflow_steps": _of_kind(narrative_facts, "workflow_step"),
        "state_objects": _of_kind(narrative_facts, "state_object"),
        "visible_outputs": _of_kind(narrative_facts, "visible_output"),
        "external_systems": _of_kind(narrative_facts, "external_system"),
        "product_boundaries": _of_kind(narrative_facts, "product_boundary"),
        "policy_boundaries": _of_kind(narrative_facts, "policy_boundary"),
    }
    grouped_relations = {
        kind: [row for row in relations if row["kind"] == kind]
        for kind in ("owned_by", "produces", "changes", "visible_to")
    }
    fact_index = {str(row["fact_id"]): row for row in facts}
    narratives = []
    for raw in project_semantic_narratives(grouped_facts, grouped_relations):
        refs = _ordered_refs(
            ref
            for fact_id in raw["fact_ids"]
            for ref in fact_index[str(fact_id)]["source_refs"]
        )[:8]
        narratives.append(
            {
                "field": raw["field"],
                "order": raw["order"],
                "text": raw["text"],
                "fact_ids": list(raw["fact_ids"]),
                "source_refs": refs,
            }
        )
    return {
        "version": semantic_intent_ir_version,
        "status": "complete",
        "presentation": dict(graph["presentation"]),
        "clarification": {"question": "", "source_refs": []},
        "facts": facts,
        "relations": relations,
        "narratives": narratives,
    }


def _source_fact_graph(
    graph: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audiences = list(graph["audiences"])
    actors = list(graph["actors"])
    entities = list(graph["entities"])
    workflow = list(graph["workflow"])
    facts: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for index, row in enumerate(audiences):
        facts.append(
            _fact(
                f"audience.{index}",
                "audience",
                str(row["label"]),
                str(row["label"]),
                index,
                "none",
                "source_fact",
                [("audience_kind", str(row["kind"]))],
                row["source_refs"],
            )
        )
    for index, row in enumerate(actors):
        facts.append(
            _fact(
                f"actor.{index}",
                "actor",
                str(row["canonical_label"]),
                str(row["canonical_label"]),
                index,
                "none",
                "source_fact",
                [],
                row["source_refs"],
            )
        )
    for index, row in enumerate(entities):
        facts.append(
            _fact(
                f"entity.{index}",
                "entity",
                str(row["label"]),
                str(row["label"]),
                index,
                "none",
                "source_fact",
                [],
                row["source_refs"],
            )
        )
    state_order = 0
    output_order = 0
    for step_index, row in enumerate(workflow):
        phrase = str(row["action"])
        owner_index = row["owner_actor_index"]
        step_id = f"step.{step_index}"
        facts.append(
            _fact(
                step_id,
                "workflow_step",
                phrase,
                phrase,
                step_index,
                "actor" if owner_index is not None else "product",
                "source_fact",
                [
                    ("action", str(row["action"])),
                    ("action_phrase", phrase),
                ],
                row["source_refs"],
            )
        )
        if owner_index is not None:
            _append_relation(
                relations,
                "owned_by",
                step_id,
                f"actor.{owner_index}",
                row["source_refs"],
            )
        explicit_target_entity_indexes = {
            int(effect["entity_index"])
            for effect in row["entity_effects"]
            if effect["kind"] == "target"
        }
        for effect in row["entity_effects"]:
            kind = str(effect["kind"])
            entity_index = int(effect["entity_index"])
            entity_id = f"entity.{entity_index}"
            if kind in {"input", "target"}:
                _append_relation(
                    relations,
                    f"{kind}_entity",
                    step_id,
                    entity_id,
                    effect["source_refs"],
                )
                continue
            if kind == "created":
                _append_relation(
                    relations,
                    "creates",
                    step_id,
                    entity_id,
                    _ordered_refs(
                        [*row["source_refs"], *effect["edge_source_refs"]]
                    ),
                )
                continue
            if kind == "visible_result":
                output_order = _append_visible_result(
                    facts=facts,
                    relations=relations,
                    actors=actors,
                    audiences=audiences,
                    entities=entities,
                    row=row,
                    step_id=step_id,
                    effect=effect,
                    output_order=output_order,
                )
                continue
            if kind not in {"changed", "stable"}:
                raise ValueError("Semantic source-meaning entity effect is unsupported")
            entity = entities[entity_index]
            if entity_index not in explicit_target_entity_indexes:
                _append_relation(
                    relations,
                    "target_entity",
                    step_id,
                    entity_id,
                    _ordered_refs(
                        [*effect["source_refs"], *effect["edge_source_refs"]]
                    ),
                )
            state_order = _append_state_effect(
                facts=facts,
                relations=relations,
                entity=entity,
                entity_id=entity_id,
                row=row,
                step_id=step_id,
                effect=effect,
                state_order=state_order,
            )
    for index, row in enumerate(graph["dependencies"]):
        facts.append(
            _fact(
                f"dependency.{index}",
                "external_system",
                str(row["label"]),
                str(row["label"]),
                index,
                "none",
                "source_fact",
                [("access_mode", str(row["access_mode"]))],
                row["source_refs"],
            )
        )
    for index, row in enumerate(graph["product_boundaries"]):
        statement = str(row["statement"])
        facts.append(
            _fact(
                f"product-boundary.{index}",
                "product_boundary",
                statement,
                statement,
                index,
                "none",
                "source_fact",
                [("statement", statement)],
                row["source_refs"],
            )
        )
    for index, row in enumerate(graph["policy_boundaries"]):
        statement = str(row["statement"])
        policy_id = f"policy-boundary.{index}"
        facts.append(
            _fact(
                policy_id,
                "policy_boundary",
                statement,
                statement,
                index,
                "none",
                "source_fact",
                [
                    ("modalities", ",".join(str(value) for value in row["modalities"])),
                    ("statement", statement),
                ],
                row["source_refs"],
            )
        )
        if "applies_to_dependency_index" in row:
            _append_relation(
                relations,
                "applies_to",
                policy_id,
                f"dependency.{int(row['applies_to_dependency_index'])}",
                row["attachment_source_refs"],
            )
    for index, row in enumerate(graph["non_material_gaps"]):
        statement = str(row["statement"])
        facts.append(
            _fact(
                f"assumption.{index}",
                "assumption",
                statement,
                statement,
                index,
                "none",
                "visible_assumption",
                [],
                row["source_refs"],
            )
        )
    return facts, relations


def _append_visible_result(
    *,
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    actors: Sequence[Mapping[str, Any]],
    audiences: Sequence[Mapping[str, Any]],
    entities: Sequence[Mapping[str, Any]],
    row: Mapping[str, Any],
    step_id: str,
    effect: Mapping[str, Any],
    output_order: int,
) -> int:
    """Project one typed visible-result effect without interpreting its wording."""

    entity_index = int(effect["entity_index"])
    entity = entities[entity_index]
    entity_id = f"entity.{entity_index}"
    output_id = f"output.{output_order}"
    facts.append(
        _fact(
            output_id,
            "visible_output",
            str(entity["label"]),
            str(entity["label"]),
            output_order,
            "none",
            "source_fact",
            [
                ("entity_id", entity_id),
            ],
            _ordered_refs([*entity["source_refs"], *effect["source_refs"]]),
        )
    )
    _append_relation(
        relations,
        "produces",
        step_id,
        output_id,
        _ordered_refs([*row["source_refs"], *effect["edge_source_refs"]]),
    )
    _append_relation(
        relations,
        "output_of",
        output_id,
        entity_id,
        _ordered_refs([*entity["source_refs"], *effect["source_refs"]]),
    )
    for recipient in effect["visible_to"]:
        recipient_kind = str(recipient["kind"])
        index = int(recipient["index"])
        if recipient_kind == "actor" and index >= len(actors):
            raise ValueError("Semantic source-meaning output actor is dangling")
        if recipient_kind == "audience" and index >= len(audiences):
            raise ValueError("Semantic source-meaning output audience is dangling")
        _append_relation(
            relations,
            "visible_to",
            output_id,
            f"{recipient_kind}.{index}",
            recipient["source_refs"],
        )
    return output_order + 1


def _append_state_effect(
    *,
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    entity: Mapping[str, Any],
    entity_id: str,
    row: Mapping[str, Any],
    step_id: str,
    effect: Mapping[str, Any],
    state_order: int,
) -> int:
    """Project one node-owned transition or stable-state effect."""

    stable = effect["kind"] == "stable"
    label = (
        f"{entity['label']} remains {effect['stable_state']}"
        if stable
        else str(entity["label"])
    )
    attributes = [("object", str(entity["label"])), ("entity_id", entity_id)]
    if stable:
        attributes.append(("stable_state", str(effect["stable_state"])))
    transition = None if stable else {
        "from_state": effect["from_state"],
        "to_state": effect["to_state"],
    }
    state_id = f"state.{state_order}"
    facts.append(
        _fact(
            state_id,
            "state_object",
            label,
            label,
            state_order,
            "none",
            "source_fact",
            attributes,
            _ordered_refs([*entity["source_refs"], *effect["source_refs"]]),
            transition=transition,
        )
    )
    _append_relation(
        relations,
        "maintains" if stable else "changes",
        step_id,
        state_id,
        _ordered_refs([*row["source_refs"], *effect["edge_source_refs"]]),
    )
    _append_relation(
        relations,
        "state_of",
        state_id,
        entity_id,
        _ordered_refs([*entity["source_refs"], *effect["source_refs"]]),
    )
    return state_order + 1


def _append_relation(
    rows: list[dict[str, Any]],
    kind: str,
    subject_id: str,
    object_id: str,
    source_refs: Sequence[Mapping[str, Any]],
    *,
    custody: str = "source_fact",
) -> None:
    order = sum(1 for row in rows if row["kind"] == kind)
    rows.append(
        {
            "relation_id": f"{kind.replace('_', '-')}.{order}",
            "kind": kind,
            "subject_id": subject_id,
            "object_id": object_id,
            "order": order,
            "custody": custody,
            "source_refs": [dict(ref) for ref in source_refs],
        }
    )


def _fact(
    fact_id: str,
    kind: str,
    label: str,
    statement: str,
    order: int,
    owner_kind: str,
    custody: str,
    attributes: Sequence[tuple[str, str]],
    source_refs: Sequence[Mapping[str, Any]],
    *,
    transition: Mapping[str, str | None] | None | object = ...,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "fact_id": fact_id,
        "kind": kind,
        "label": label,
        "statement": statement,
        "order": order,
        "owner_kind": owner_kind,
        "custody": custody,
        "attributes": [
            {"name": name, "value": value} for name, value in attributes if value
        ],
        "source_refs": [dict(ref) for ref in source_refs],
    }
    if transition is not ...:
        row["transition"] = transition
    return row


def _of_kind(rows: Sequence[Mapping[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if row.get("kind") == kind]


def _ordered_refs(values: Any) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for value in values:
        row = dict(value)
        key = (str(row["source_id"]), str(row["quote"]), int(row["occurrence"]))
        unique.setdefault(key, row)
    return list(unique.values())


__all__ = ["compile_semantic_source_meaning"]
