"""Typed final relation and architecture adjudication over source candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_NONMATERIAL_ASSUMPTION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_completion_partitions import (
    apply_semantic_implementation_assignments,
    require_semantic_dependency_architecture,
    semantic_architecture_edge_object_ids,
    semantic_graph_completion_schema,
    semantic_unassigned_source_dependency_ids,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_source_refs_overlap,
)


SEMANTIC_FINAL_ADJUDICATION_VERSION = (
    "odylith.greenfield.semantic-final-adjudication.v7"
)


def clarification_from_source_ambiguity(
    decision: Mapping[str, Any], *, ambiguity: Mapping[str, Any]
) -> dict[str, Any]:
    """Promote one source-authored material ambiguity into the sole question."""

    field = ambiguity.get("materiality_field")
    question = ambiguity.get("question")
    refs = ambiguity.get("source_refs")
    if (
        field not in SEMANTIC_CLARIFICATION_FIELDS
        or not isinstance(question, str)
        or not question.strip()
        or not isinstance(refs, list)
        or not refs
        or any(not isinstance(ref, Mapping) for ref in refs)
    ):
        raise ValueError("source-authored material ambiguity is malformed")
    result = deepcopy(dict(decision))
    result["outcome"] = {
        "decision": "clarification_required",
        "clarification": {
            "field": field,
            "question": question.strip(),
            "source_refs": deepcopy(refs),
            "alternatives": [],
        },
    }
    return result


def semantic_final_adjudication_schema(
    *, source: Mapping[str, Any], source_citation_ids: Sequence[str],
    source_ref_schema: Mapping[str, Any],
    edge_object_ids: Mapping[str, Sequence[str]], topology_mode: str,
    clarification_only: bool = False,
) -> dict[str, Any]:
    """Constrain final authority to typed candidate IDs and exact citations."""

    facts = _facts(source)
    fact_ids = [str(row["fact_id"]) for row in facts]
    relation_ids = list(semantic_candidate_relation_catalog(source))
    completion = semantic_graph_completion_schema(
        source_citation_ids=source_citation_ids,
        edge_object_ids=edge_object_ids,
        topology_mode=topology_mode,
    )
    definitions = completion.pop("$defs")
    source_finding_challenges = [
        challenge
        for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
        if challenge != "evidence_status_misclassification"
    ]
    finding = {
        "type": "object",
        "additionalProperties": False,
        "required": ["challenge", "source_object_ids", "source_citation_ids", "rationale"],
        "properties": {
            "challenge": {
                "type": "string",
                "enum": source_finding_challenges,
            },
            "source_object_ids": {
                "type": "array",
                "items": {"type": "string", "enum": fact_ids},
                "maxItems": len(fact_ids),
            },
            "source_citation_ids": {"$ref": "#/$defs/source_citation_ids"},
            "rationale": {"type": "string", "maxLength": 600},
        },
    }
    root_properties: dict[str, Any] = {
        "version": {
            "type": "string", "enum": [SEMANTIC_FINAL_ADJUDICATION_VERSION]
        },
        "discarded_source_refs": {
            "type": "array",
            "items": source_ref_schema,
            "maxItems": 32,
        },
    }
    resolution = _materiality_resolution_schema()
    if clarification_only:
        return {
            **_strict_object(
                {
                    "version": root_properties["version"],
                    "result": _strict_object(
                        {"materiality_resolution": resolution}
                    ),
                }
            ),
            "$defs": definitions,
        }
    result_properties = {
        "source_status": {
            "type": "string",
            "enum": ["approved", "rejected", "not_applicable"],
        },
        "findings": {"type": "array", "items": finding, "maxItems": 16},
        "admitted_fact_ids": {
            "type": "array",
            "items": {"type": "string", "enum": fact_ids},
            "maxItems": len(fact_ids),
        },
        "admitted_relation_ids": {
            "type": "array",
            "items": {"type": "string", "enum": relation_ids},
            "maxItems": len(relation_ids),
        },
        "completion": {"anyOf": [completion, {"type": "null"}]},
    }
    graph_properties = {
        **result_properties,
        "materiality_resolution": resolution,
        "source_status": {"type": "string", "enum": ["approved", "rejected"]},
    }
    root_properties["result"] = _strict_object(graph_properties)
    return {**_strict_object(root_properties), "$defs": definitions}


def _strict_object(properties: Mapping[str, Any]) -> dict[str, Any]:
    """Return one complete provider-valid strict object variant."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": dict(properties),
    }


def remove_discarded_materiality_refs(
    decision: Mapping[str, Any], *, discarded_source_refs: Sequence[Mapping[str, Any]],
    evidence_sources: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Remove only final-declared discarded spans from accepted materiality custody."""

    return _without_discarded_materiality_refs(
        decision,
        discarded_source_refs=discarded_source_refs,
        evidence_sources=evidence_sources,
        allow_fully_discarded=False,
    )


def settle_independently_confirmed_discarded_materiality_refs(
    decision: Mapping[str, Any],
    *,
    discarded_source_refs: Sequence[Mapping[str, Any]],
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Downgrade optional axes only when two source authors agree they are provenance."""

    return _without_discarded_materiality_refs(
        decision,
        discarded_source_refs=discarded_source_refs,
        evidence_sources=evidence_sources,
        allow_fully_discarded=True,
    )


def _without_discarded_materiality_refs(
    decision: Mapping[str, Any],
    *,
    discarded_source_refs: Sequence[Mapping[str, Any]],
    evidence_sources: Mapping[str, str] | None,
    allow_fully_discarded: bool,
) -> dict[str, Any]:

    discarded = {_source_ref_key(row) for row in discarded_source_refs}
    if any(key is None for key in discarded):
        raise ValueError("Semantic final discarded evidence is malformed")
    result = deepcopy(dict(decision))
    def is_discarded(ref: Any) -> bool:
        if not isinstance(ref, Mapping):
            raise ValueError("Semantic final materiality field custody is malformed")
        if evidence_sources is None:
            return _source_ref_key(ref) in discarded
        return any(
            semantic_source_refs_overlap(
                ref, discarded_ref, evidence_sources=evidence_sources
            )
            for discarded_ref in discarded_source_refs
        )

    fields = _mapping(result.get("fields"), "Semantic final materiality fields")
    for name, raw in fields.items():
        row = _mapping(raw, f"Semantic final materiality field {name}")
        refs = row.get("source_refs")
        if not isinstance(refs, list):
            raise ValueError("Semantic final materiality field custody is malformed")
        row["source_refs"] = [ref for ref in refs if not is_discarded(ref)]
        if refs and not row["source_refs"]:
            if (
                not allow_fully_discarded
                or name not in SEMANTIC_NONMATERIAL_ASSUMPTION_FIELDS
            ):
                raise ValueError("discarded evidence was the only materiality custody")
            row.update(
                status="nonmaterial_assumption",
                source_refs=[],
                alternatives=[],
            )
        fields[name] = row
    result["fields"] = fields
    outcome = _mapping(result.get("outcome"), "Semantic final materiality outcome")
    clarification = _mapping(
        outcome.get("clarification"), "Semantic final clarification"
    )
    clarification_refs = clarification.get("source_refs")
    if not isinstance(clarification_refs, list):
        raise ValueError("Semantic final clarification custody is malformed")
    if any(is_discarded(ref) for ref in clarification_refs):
        raise ValueError("final clarification cites discarded evidence")
    return result


def resolve_final_materiality_decision(
    value: Any, *, hypothesis: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve one explicit final verdict with typed evidence-field authority."""

    row = _mapping(value, "Semantic final materiality resolution")
    verdict = row.get("verdict")
    if verdict == "accept_hypothesis" and set(row) == {"verdict"}:
        return deepcopy(dict(hypothesis))
    raise ValueError("Semantic final materiality resolution is malformed")


def _materiality_resolution_schema() -> dict[str, Any]:
    return _strict_object(
        {"verdict": {"type": "string", "enum": ["accept_hypothesis"]}}
    )


def apply_final_adjudication(
    value: Any, *, source: Mapping[str, Any],
    citation_registry: Mapping[str, Mapping[str, Any]],
    clarification_only: bool = False,
) -> dict[str, Any]:
    """Hydrate final relation citations and completion without prose inference."""

    row = _mapping(value, "Semantic final adjudication")
    if row.get("version") != SEMANTIC_FINAL_ADJUDICATION_VERSION:
        raise ValueError("Semantic final adjudication version is unsupported")
    result = _mapping(row.get("result"), "Semantic final adjudication result")
    if clarification_only:
        if set(result) != {"materiality_resolution"}:
            raise ValueError("Semantic final clarification carries graph authorship")
        if result.get("materiality_resolution") != {
            "verdict": "accept_hypothesis"
        }:
            raise ValueError("Semantic final clarification changes settled materiality")
        return {
            "source_status": "not_applicable",
            "findings": [],
            "discarded_source_refs": [],
        }
    discarded_source_refs = _source_refs(
        row.get("discarded_source_refs"), label="Semantic final discarded evidence"
    )
    resolution = _mapping(
        result.get("materiality_resolution"),
        "Semantic final materiality resolution",
    )
    if resolution.get("verdict") != "accept_hypothesis":
        raise ValueError("Semantic graph adjudication cannot reopen settled materiality")
    status = result.get("source_status")
    findings = result.get("findings")
    if status not in {"approved", "rejected"} or not isinstance(findings, list):
        raise ValueError("Semantic final source verdict is malformed")
    if (status == "approved" and findings) or (status == "rejected" and not findings):
        raise ValueError("Semantic final source verdict and findings disagree")
    if status != "approved":
        return {
            "source_status": status,
            "findings": deepcopy(findings),
            "discarded_source_refs": discarded_source_refs,
        }
    facts = _admitted_facts(result.get("admitted_fact_ids"), source=source)
    relations = _admitted_relations(
        result.get("admitted_relation_ids"),
        source=source,
        admitted_fact_ids={str(fact["fact_id"]) for fact in facts},
    )
    final_source = {
        "version": source["version"],
        "facts": facts,
        "relations": relations,
    }
    completion = apply_semantic_implementation_assignments(
        result.get("completion"),
        edge_object_ids=semantic_architecture_edge_object_ids(final_source),
        citation_registry=citation_registry,
    )
    require_semantic_dependency_architecture(
        completion,
        dependency_ids=semantic_unassigned_source_dependency_ids(final_source),
    )
    completion["clarification"] = {
        "question": "",
        "fields": [],
        "source_refs": [],
    }
    return {
        "source_status": status,
        "findings": [],
        "discarded_source_refs": discarded_source_refs,
        "source": final_source,
        "completion": completion,
    }


def semantic_candidate_relation_catalog(
    source: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Assign stable typed IDs to the source compiler's ordered relation candidates."""

    relations = source.get("relations")
    if not isinstance(relations, list) or any(
        not isinstance(row, Mapping) for row in relations
    ):
        raise ValueError("Semantic final source relations are malformed")
    orders: dict[str, int] = {}
    result: dict[str, dict[str, Any]] = {}
    for raw in relations:
        row = dict(raw)
        kind = str(row.get("kind") or "")
        order = orders.get(kind, 0)
        relation_id = f"relation.{kind}.{order}"
        result[relation_id] = row
        orders[kind] = order + 1
    return result


def _admitted_relations(
    value: Any,
    *,
    source: Mapping[str, Any],
    admitted_fact_ids: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError("Semantic final admitted relation ids are malformed")
    candidates = semantic_candidate_relation_catalog(source)
    if len(set(value)) != len(value) or any(item not in candidates for item in value):
        raise ValueError("Semantic final admitted relation ids are duplicated or unknown")
    admitted = set(value)
    result: list[dict[str, Any]] = []
    orders: dict[str, int] = {}
    for relation_id, raw in candidates.items():
        if relation_id not in admitted:
            continue
        row = deepcopy(raw)
        kind = str(row["kind"])
        subject_id = str(row.get("subject_id") or "")
        object_id = str(row.get("object_id") or "")
        if subject_id not in admitted_fact_ids or object_id not in admitted_fact_ids:
            raise ValueError("Semantic final relation references an omitted fact")
        order = orders.get(kind, 0)
        row["relation_id"] = f"relation.{kind}.{order}"
        row["order"] = order
        result.append(row)
        orders[kind] = order + 1
    return result


def _admitted_facts(value: Any, *, source: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) for item in value):
        raise ValueError("Semantic final admitted fact ids are malformed")
    candidates = {str(row["fact_id"]): row for row in _facts(source)}
    if len(set(value)) != len(value) or any(fact_id not in candidates for fact_id in value):
        raise ValueError("Semantic final admitted fact ids are duplicated or unknown")
    admitted = set(value)
    return [deepcopy(row) for row in _facts(source) if str(row["fact_id"]) in admitted]


def _source_ref_key(value: Any) -> tuple[str, str, int] | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("occurrence"), int):
        return None
    source_id = str(value.get("source_id") or "")
    quote = str(value.get("quote") or "")
    return (source_id, quote, int(value["occurrence"])) if source_id and quote else None


def _source_refs(value: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{label} is malformed")
    result = [deepcopy(dict(row)) for row in value]
    keys = {
        (row.get("source_id"), row.get("quote"), row.get("occurrence"))
        for row in result
    }
    if len(keys) != len(result):
        raise ValueError(f"{label} is duplicated")
    return result


def _facts(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    value = source.get("facts")
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError("Semantic final source facts are malformed")
    return [dict(row) for row in value]


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


__all__ = [
    "SEMANTIC_FINAL_ADJUDICATION_VERSION",
    "apply_final_adjudication",
    "clarification_from_source_ambiguity",
    "resolve_final_materiality_decision",
    "remove_discarded_materiality_refs",
    "settle_independently_confirmed_discarded_materiality_refs",
    "semantic_candidate_relation_catalog",
    "semantic_final_adjudication_schema",
]
