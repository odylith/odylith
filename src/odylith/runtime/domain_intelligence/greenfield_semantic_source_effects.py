"""Own source-authored state, output, and output-recipient effects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_schema import (
    array_schema as _array,
    object_schema as _object,
    string_schema as _string,
)


def semantic_source_step_effect_schemas(
    *, source_refs: Mapping[str, Any]
) -> dict[str, Any]:
    """Return node-owned change, output, and recipient transport schemas."""

    actor_recipient = _object(
        ["actor_index", "source_refs"],
        {
            "actor_index": {"type": "integer", "minimum": 0, "maximum": 63},
            "source_refs": dict(source_refs),
        },
    )
    return {
        "changes": _array(
            _object(
                [
                    "label",
                    "object",
                    "from_state",
                    "to_state",
                    "source_refs",
                    "edge_source_refs",
                ],
                {
                    "label": _string(300),
                    "object": _string(800),
                    "from_state": {"anyOf": [_string(800), {"type": "null"}]},
                    "to_state": {"anyOf": [_string(800), {"type": "null"}]},
                    "source_refs": dict(source_refs),
                    "edge_source_refs": dict(source_refs),
                },
            ),
            maximum=128,
        ),
        "produces": _array(
            _object(
                [
                    "label",
                    "condition",
                    "source_refs",
                    "edge_source_refs",
                    "visible_to",
                ],
                {
                    "label": _string(300),
                    "condition": {"anyOf": [_string(800), {"type": "null"}]},
                    "source_refs": dict(source_refs),
                    "edge_source_refs": dict(source_refs),
                    "visible_to": _array(actor_recipient, maximum=64),
                },
            ),
            maximum=128,
        ),
    }


def compile_source_step_effects(
    effects: tuple[list[dict[str, Any]], list[dict[str, Any]]],
    *,
    step_id: str,
    actor_count: int,
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
) -> None:
    """Compile lexical child effects and recipient indices into typed endpoints."""

    changes, produces = effects
    for raw in changes:
        if set(raw) != {
            "label",
            "object",
            "from_state",
            "to_state",
            "source_refs",
            "edge_source_refs",
        }:
            raise ValueError("Semantic workflow state change is malformed")
        change = dict(raw)
        before = change.pop("from_state")
        after = change.pop("to_state")
        if before is None and after is None:
            raise ValueError("Semantic workflow transition lacks a declared state")
        if before is not None and before == after:
            raise ValueError("Semantic workflow transition does not change state")
        edge_refs = change.pop("edge_source_refs")
        fact_id = f"state.{_kind_count(facts, 'state_object')}"
        facts.append(
            {
                **change,
                "transition": {"from_state": before, "to_state": after},
                "fact_id": fact_id,
                "kind": "state_object",
            }
        )
        relations.append(
            {
                "kind": "changes",
                "subject_id": step_id,
                "object_id": fact_id,
                "source_refs": list(edge_refs),
            }
        )
    for raw in produces:
        if set(raw) != {
            "label",
            "condition",
            "source_refs",
            "edge_source_refs",
            "visible_to",
        }:
            raise ValueError("Semantic workflow output is malformed")
        output = dict(raw)
        recipients = _actor_recipients(output.pop("visible_to"), actor_count=actor_count)
        edge_refs = output.pop("edge_source_refs")
        if output["condition"] is None:
            output.pop("condition")
        fact_id = f"output.{_kind_count(facts, 'visible_output')}"
        facts.append({**output, "fact_id": fact_id, "kind": "visible_output"})
        relations.append(
            {
                "kind": "produces",
                "subject_id": step_id,
                "object_id": fact_id,
                "source_refs": list(edge_refs),
            }
        )
        relations.extend(
            {
                "kind": "visible_to",
                "subject_id": fact_id,
                "object_id": f"actor.{recipient['actor_index']}",
                "source_refs": list(recipient["source_refs"]),
            }
            for recipient in recipients
        )


def _actor_recipients(value: Any, *, actor_count: int) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("Semantic workflow output recipients are malformed")
    recipients: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {"actor_index", "source_refs"}:
            raise ValueError("Semantic workflow output recipient is malformed")
        actor_index = raw.get("actor_index")
        if (
            isinstance(actor_index, bool)
            or not isinstance(actor_index, int)
            or not 0 <= actor_index < actor_count
            or actor_index in seen
        ):
            raise ValueError("Semantic workflow output recipient index is invalid")
        refs = raw.get("source_refs")
        if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes, bytearray)):
            raise ValueError("Semantic workflow output recipient custody is malformed")
        recipients.append({"actor_index": actor_index, "source_refs": list(refs)})
        seen.add(actor_index)
    return recipients


def _kind_count(facts: Sequence[Mapping[str, Any]], kind: str) -> int:
    return sum(row.get("kind") == kind for row in facts)


__all__ = [
    "compile_source_step_effects",
    "semantic_source_step_effect_schemas",
]
