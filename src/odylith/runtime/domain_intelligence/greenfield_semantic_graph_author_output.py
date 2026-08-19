"""Single structured-output contract for Greenfield semantic graph authors."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_adjudication_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension import (
    semantic_graph_extension_schema_for_materiality,
)


def semantic_graph_author_output_schema(
    assessment: Mapping[str, Any],
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Return the sole author output schema for source truth and bounded graph rows."""

    challenges = list(SEMANTIC_INTENT_MANDATORY_CHALLENGES)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "source_candidate_adjudication",
            "semantic_extension",
            "self_challenge",
        ],
        "properties": {
            "source_candidate_adjudication": atomic_source_adjudication_schema(),
            "semantic_extension": semantic_graph_extension_schema_for_materiality(
                assessment,
                evidence_sources=evidence_sources,
            ),
            "self_challenge": {
                "type": "array",
                "minItems": len(challenges),
                "maxItems": len(challenges),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["challenge", "status"],
                    "properties": {
                        "challenge": {"type": "string", "enum": challenges},
                        "status": {"type": "string", "enum": ["passed", "failed"]},
                    },
                },
            },
        },
    }


def require_semantic_graph_author_output(value: Any) -> dict[str, Any]:
    """Require exact author sections and one passing result per mandatory challenge."""

    if not isinstance(value, Mapping) or set(value) != {
        "source_candidate_adjudication",
        "semantic_extension",
        "self_challenge",
    }:
        raise ValueError("Semantic graph author output is malformed")
    rows = value.get("self_challenge")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("Semantic graph author self-challenge is malformed")
    indexed: dict[str, str] = {}
    normalized_rows: list[dict[str, str]] = []
    for raw in rows:
        if not isinstance(raw, Mapping) or set(raw) != {"challenge", "status"}:
            raise ValueError("Semantic graph author challenge row is malformed")
        challenge = str(raw.get("challenge") or "")
        status = str(raw.get("status") or "")
        if challenge in indexed or challenge not in SEMANTIC_INTENT_MANDATORY_CHALLENGES:
            raise ValueError("Semantic graph author challenge coverage is invalid")
        if status not in {"passed", "failed"}:
            raise ValueError("Semantic graph author challenge status is invalid")
        indexed[challenge] = status
        normalized_rows.append({"challenge": challenge, "status": status})
    if set(indexed) != set(SEMANTIC_INTENT_MANDATORY_CHALLENGES):
        raise ValueError("Semantic graph author challenge coverage is incomplete")
    if any(status != "passed" for status in indexed.values()):
        raise ValueError("Semantic graph author reports a failed mandatory challenge")
    adjudication = value.get("source_candidate_adjudication")
    extension = value.get("semantic_extension")
    if not isinstance(adjudication, Mapping) or not isinstance(extension, Mapping):
        raise ValueError("Semantic graph author typed output is malformed")
    return {
        "source_candidate_adjudication": dict(adjudication),
        "semantic_extension": dict(extension),
        "self_challenge": normalized_rows,
    }


__all__ = [
    "require_semantic_graph_author_output",
    "semantic_graph_author_output_schema",
]
