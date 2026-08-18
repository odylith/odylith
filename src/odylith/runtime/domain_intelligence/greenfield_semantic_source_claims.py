"""Locked prompt-only source claims for Greenfield semantic authoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    require_semantic_source_refs,
)


SEMANTIC_SOURCE_CLAIMS_VERSION = "odylith.greenfield.semantic-source-claims.v2"
SEMANTIC_SOURCE_CANDIDATES_VERSION = (
    "odylith.greenfield.semantic-source-candidates.v1"
)
_FACT_KEYS = {
    "fact_id",
    "kind",
    "label",
    "statement",
    "order",
    "owner_kind",
    "custody",
    "attributes",
    "source_refs",
}
_RELATION_KEYS = {
    "relation_id",
    "kind",
    "subject_id",
    "object_id",
    "order",
    "custody",
    "source_refs",
}


def require_semantic_source_claims(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    settled_fields: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate the deterministically selected source-claim projection."""

    return _require_semantic_source_graph(
        value,
        expected_version=SEMANTIC_SOURCE_CLAIMS_VERSION,
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
        label="claims",
    )


def require_semantic_source_candidates(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    settled_fields: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate critic-owned source candidates before author adjudication."""

    return _require_semantic_source_graph(
        value,
        expected_version=SEMANTIC_SOURCE_CANDIDATES_VERSION,
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
        label="candidates",
    )


def _require_semantic_source_graph(
    value: Any,
    *,
    expected_version: str,
    evidence_sources: Mapping[str, str],
    settled_fields: Mapping[str, Mapping[str, Any]],
    label: str,
) -> dict[str, Any]:
    """Validate one exact source-row set without interpreting evidence prose."""

    claims = _mapping(value, f"Semantic source {label}")
    _exact_keys(claims, {"version", "facts", "relations"}, f"Semantic source {label}")
    if claims.get("version") != expected_version:
        raise ValueError(f"Semantic source {label} use an unsupported version")
    facts = _claim_rows(
        claims.get("facts"),
        item_key="fact",
        field_key="field",
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
    )
    relations = _claim_rows(
        claims.get("relations"),
        item_key="relation",
        field_key="fields",
        evidence_sources=evidence_sources,
        settled_fields=settled_fields,
    )
    fact_ids: set[str] = set()
    normalized_facts: list[dict[str, Any]] = []
    for row in facts:
        fact = _mapping(row["fact"], "Semantic source claim fact")
        expected = _FACT_KEYS | ({"transition"} if fact.get("kind") == "state_object" else set())
        _exact_keys(fact, expected, "Semantic source claim fact")
        fact_id = _identifier(fact.get("fact_id"), "source claim fact id")
        if fact_id in fact_ids:
            raise ValueError("Semantic source claim fact ids are not unique")
        fact_ids.add(fact_id)
        if fact.get("custody") != "source_fact":
            raise ValueError("Semantic source claim fact is not source-owned")
        normalized_facts.append({"field": row["field"], "fact": dict(fact)})
    relation_ids: set[str] = set()
    normalized_relations: list[dict[str, Any]] = []
    for row in relations:
        relation = _mapping(row["relation"], "Semantic source claim relation")
        _exact_keys(relation, _RELATION_KEYS, "Semantic source claim relation")
        relation_id = _identifier(
            relation.get("relation_id"), "source claim relation id"
        )
        if relation_id in relation_ids:
            raise ValueError("Semantic source claim relation ids are not unique")
        relation_ids.add(relation_id)
        if relation.get("custody") != "source_fact":
            raise ValueError("Semantic source claim relation is not source-owned")
        if relation.get("subject_id") not in fact_ids or relation.get("object_id") not in fact_ids:
            raise ValueError("Semantic source claim relation leaves the locked source graph")
        relation_fields = tuple(str(field) for field in row["fields"])
        normalized_relations.append(
            {"fields": list(relation_fields), "relation": dict(relation)}
        )
    return {
        "version": expected_version,
        "facts": normalized_facts,
        "relations": normalized_relations,
    }


def require_source_claim_projection(
    source_claims: Mapping[str, Any],
    *,
    facts: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> None:
    """Require every source-owned graph row to equal one locked source claim."""

    claimed_facts = {
        str(row["fact"]["fact_id"]): row["fact"]
        for row in source_claims.get("facts", ())
        if isinstance(row, Mapping) and isinstance(row.get("fact"), Mapping)
    }
    claimed_relations = {
        str(row["relation"]["relation_id"]): row["relation"]
        for row in source_claims.get("relations", ())
        if isinstance(row, Mapping) and isinstance(row.get("relation"), Mapping)
    }
    projected_facts = {
        str(row["fact_id"]): row for row in facts if row.get("custody") == "source_fact"
    }
    projected_relations = {
        str(row["relation_id"]): row
        for row in relations
        if row.get("custody") == "source_fact"
    }
    if projected_facts != claimed_facts:
        raise ValueError("Semantic Intent source facts differ from locked source claims")
    if projected_relations != claimed_relations:
        raise ValueError("Semantic Intent source relations differ from locked source claims")


def _claim_rows(
    value: Any,
    *,
    item_key: str,
    field_key: str,
    evidence_sources: Mapping[str, str],
    settled_fields: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = _sequence(value, 256, f"source claim {item_key}s")
    result: list[dict[str, Any]] = []
    for raw in rows:
        row = _mapping(raw, f"Semantic source claim {item_key}")
        _exact_keys(row, {field_key, item_key}, f"Semantic source claim {item_key}")
        if field_key == "field":
            fields = [row.get("field")]
        else:
            fields = _sequence(row.get("fields"), 9, "source claim relation fields")
            if not fields or len(set(fields)) != len(fields):
                raise ValueError("Semantic source claim relation fields are invalid")
        if any(
            field not in SEMANTIC_CLARIFICATION_FIELDS or field not in settled_fields
            for field in fields
        ):
            raise ValueError("Semantic source claim references an unresolved field")
        payload = _mapping(row.get(item_key), f"Semantic source claim {item_key}")
        require_semantic_source_refs(
            payload.get("source_refs"), evidence_sources=evidence_sources
        )
        result.append(
            {
                field_key: str(fields[0]) if field_key == "field" else list(fields),
                item_key: dict(payload),
            }
        )
    return result


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 100:
        raise ValueError(f"Semantic {label} is malformed")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _sequence(value: Any, maximum: int, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"Semantic {label} is malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError(f"Semantic {label} exceeds its operating limit")
    return rows


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} has unsupported or missing fields")


__all__ = [
    "SEMANTIC_SOURCE_CANDIDATES_VERSION",
    "SEMANTIC_SOURCE_CLAIMS_VERSION",
    "require_semantic_source_candidates",
    "require_semantic_source_claims",
    "require_source_claim_projection",
]
