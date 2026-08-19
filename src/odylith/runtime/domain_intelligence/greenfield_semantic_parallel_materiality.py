"""Assemble independent materiality and atomic-span evidence before graph authoring."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    require_atomic_source_candidates,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_MATERIALITY_ASSESSMENT_BASIS,
    SEMANTIC_MATERIALITY_ASSESSMENT_VERSION,
    require_semantic_materiality_assessment,
    semantic_materiality_assessment_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolve_semantic_source_ref,
)


PARALLEL_MATERIALITY_DECISION_VERSION = (
    "odylith.greenfield.parallel-materiality-decision.v3"
)
SEMANTIC_SOURCE_ADMISSION_VERSION = "odylith.greenfield.semantic-source-admission.v1"


def parallel_materiality_decision_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return the screen schema without atomic-span or graph authority."""

    assessment = semantic_materiality_assessment_schema(
        source_ref_schema=source_ref_schema
    )
    properties = assessment["properties"]
    field_variants = properties["fields"]["items"]["anyOf"]
    clarification_variants = properties["clarification"]["anyOf"]
    field_names = tuple(SEMANTIC_CLARIFICATION_FIELDS)
    fields = {
        field: {
            "anyOf": _field_decision_variants(field, variants=field_variants),
        }
        for field in field_names
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "outcome", "fields"],
        "properties": {
            "version": {
                "type": "string",
                "enum": [PARALLEL_MATERIALITY_DECISION_VERSION],
            },
            "outcome": {
                "anyOf": [
                    _outcome_variant(
                        decision="authorize_graph",
                        clarification=clarification_variants[0],
                    ),
                    _outcome_variant(
                        decision="clarification_required",
                        clarification=clarification_variants[1],
                    ),
                ]
            },
            "fields": {
                "type": "object",
                "additionalProperties": False,
                "required": list(field_names),
                "properties": fields,
            },
        },
    }


def _outcome_variant(
    *,
    decision: str,
    clarification: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one decision to its only structurally valid terminal outcome."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "clarification"],
        "properties": {
            "decision": {"type": "string", "enum": [decision]},
            "clarification": deepcopy(clarification),
        },
    }


def assemble_parallel_materiality_assessment(
    decision_value: Any,
    source_candidates_value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Join two independent outputs and validate one production assessment."""

    decision = canonical_parallel_materiality_decision(decision_value)
    evidence = {key: str(value) for key, value in evidence_sources.items()}
    candidates = require_atomic_source_candidates(
        source_candidates_value,
        evidence_sources=evidence,
    )
    evidence_sha256 = semantic_evidence_sha256(evidence)
    contract_sha256 = semantic_intent_authoring_contract_sha256()
    assessment = {
        "version": SEMANTIC_MATERIALITY_ASSESSMENT_VERSION,
        "evidence_sha256": evidence_sha256,
        "authoring_contract_sha256": contract_sha256,
        "assessment_basis": SEMANTIC_MATERIALITY_ASSESSMENT_BASIS,
        "decision": decision["decision"],
        "clarification": decision["clarification"],
        "fields": decision["fields"],
        "source_candidates": candidates,
    }
    return require_semantic_materiality_assessment(
        assessment,
        evidence_sources=evidence,
        evidence_sha256=evidence_sha256,
        authoring_contract_sha256=contract_sha256,
    )


def canonical_parallel_materiality_decision(value: Any) -> dict[str, Any]:
    """Convert exact keyed field decisions to canonical ordered assessment rows."""

    if not isinstance(value, Mapping) or set(value) != {"version", "outcome", "fields"}:
        raise ValueError("parallel materiality decision is malformed")
    if value.get("version") != PARALLEL_MATERIALITY_DECISION_VERSION:
        raise ValueError("parallel materiality decision uses an unsupported version")
    fields = value.get("fields")
    field_names = tuple(SEMANTIC_CLARIFICATION_FIELDS)
    if (
        not isinstance(fields, Mapping)
        or set(fields) != set(field_names)
        or any(not isinstance(fields[field], Mapping) for field in field_names)
    ):
        raise ValueError("parallel materiality decision lacks exact field coverage")
    outcome = value.get("outcome")
    if not isinstance(outcome, Mapping) or set(outcome) != {"decision", "clarification"}:
        raise ValueError("parallel materiality outcome is malformed")
    clarification = outcome.get("clarification")
    if not isinstance(clarification, Mapping):
        raise ValueError("parallel materiality clarification is malformed")
    clarified_field = (
        str(clarification.get("field") or "")
        if outcome.get("decision") == "clarification_required" else ""
    )
    rows: list[dict[str, Any]] = []
    for field in field_names:
        row = dict(fields[field])
        if field == clarified_field:
            continue
        rows.append({"field": field, **row})
    return {
        "version": value["version"],
        "decision": outcome.get("decision"),
        "clarification": clarification,
        "fields": rows,
    }


def materiality_authorization_view(value: Any) -> dict[str, Any]:
    """Expose settlement authority without reusing evidence refs as ontology labels."""

    if value is None:
        return {}
    if (
        not isinstance(value, Mapping)
        or set(value) != {"version", "decision", "clarification", "fields"}
        or value.get("version") != PARALLEL_MATERIALITY_DECISION_VERSION
    ):
        raise ValueError("canonical materiality decision is malformed")
    fields = value.get("fields")
    if not isinstance(fields, list):
        raise ValueError("canonical materiality fields are malformed")
    authorization: dict[str, dict[str, Any]] = {}
    for raw in fields:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("field"), str):
            raise ValueError("canonical materiality field is malformed")
        field = str(raw["field"])
        if field in authorization:
            raise ValueError("canonical materiality field is duplicated")
        authorization[field] = {
            "status": raw.get("status"),
            "alternatives": deepcopy(list(raw.get("alternatives", []))),
        }
    return {"decision": value.get("decision"), "fields": authorization}


def require_materiality_source_coverage(
    decision_value: Any,
    source: Mapping[str, Any],
    *,
    evidence_sources: Mapping[str, str],
) -> None:
    """Require settled material axes to survive in the typed source graph."""

    canonical = canonical_parallel_materiality_decision(decision_value)
    authorization = materiality_authorization_view(canonical)
    facts = source.get("facts")
    if not isinstance(facts, list) or any(not isinstance(row, Mapping) for row in facts):
        raise ValueError("Semantic source facts are malformed")
    fact_kinds = {str(row.get("kind") or "") for row in facts}
    required_kinds = {
        "identity": "identity",
        "first_path": "workflow_step",
        "state_object": "state_object",
        "visible_result": "visible_output",
        "dependency": "external_system",
    }
    for field, kind in required_kinds.items():
        row = authorization["fields"].get(field, {})
        if row.get("status") in {"explicit", "source_entailable"} and kind not in fact_kinds:
            raise ValueError(
                f"Semantic source graph omits critic-settled `{field}` meaning"
            )
    field_rows = {str(row["field"]): row for row in canonical["fields"]}
    for field, kind in {
        "first_path": "workflow_step",
        "state_object": "state_object",
        "visible_result": "visible_output",
        "dependency": "external_system",
    }.items():
        field_row = field_rows.get(field, {})
        if field_row.get("status") not in {"explicit", "source_entailable"}:
            continue
        field_spans = _citation_spans(
            field_row.get("source_refs"), evidence_sources=evidence_sources
        )
        for fact in (row for row in facts if row.get("kind") == kind):
            fact_spans = _citation_spans(
                fact.get("source_refs"), evidence_sources=evidence_sources
            )
            if not any(
                _spans_overlap(left, right)
                for left in fact_spans
                for right in field_spans
            ):
                raise ValueError(
                    f"Semantic source `{kind}` fact is outside critic-settled `{field}` evidence"
                )


def admit_source_candidates_by_materiality(
    decision_value: Any,
    source_value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    """Admit typed source candidates supported by the settled field citations."""

    canonical = canonical_parallel_materiality_decision(decision_value)
    if not isinstance(source_value, Mapping) or set(source_value) != {
        "version", "path", "boundary",
    }:
        raise ValueError("Semantic source candidate graph is malformed")
    source = deepcopy(dict(source_value))
    path = source.get("path")
    boundary = source.get("boundary")
    if not isinstance(path, dict) or not isinstance(boundary, dict):
        raise ValueError("Semantic source candidate partitions are malformed")
    field_rows = {str(row["field"]): row for row in canonical["fields"]}
    field_spans = {
        field: _settled_field_spans(
            field_rows.get(field, {}), evidence_sources=evidence_sources
        )
        for field in ("first_path", "state_object", "visible_result", "dependency")
    }
    rejections: list[dict[str, Any]] = []
    step_remap = _admit_workflow_steps(
        path,
        allowed_spans=field_spans["first_path"],
        evidence_sources=evidence_sources,
        rejections=rejections,
    )
    path["state_objects"] = _admit_axis_rows(
        path.get("state_objects"),
        field="state_object",
        kind="state_object",
        allowed_spans=field_spans["state_object"],
        evidence_sources=evidence_sources,
        step_remap=step_remap,
        binding_key="transition",
        rejections=rejections,
    )
    path["visible_outputs"] = _admit_axis_rows(
        path.get("visible_outputs"),
        field="visible_result",
        kind="visible_output",
        allowed_spans=field_spans["visible_result"],
        evidence_sources=evidence_sources,
        step_remap=step_remap,
        binding_key="producer",
        rejections=rejections,
    )
    boundary["external_systems"] = _admit_dependencies(
        boundary.get("external_systems"),
        allowed_spans=field_spans["dependency"],
        evidence_sources=evidence_sources,
        step_remap=step_remap,
        rejections=rejections,
    )
    return {
        "version": SEMANTIC_SOURCE_ADMISSION_VERSION,
        "source": source,
        "rejected_candidates": rejections,
    }


def _admit_workflow_steps(
    path: dict[str, Any],
    *,
    allowed_spans: tuple[tuple[str, int, int], ...] | None,
    evidence_sources: Mapping[str, str],
    rejections: list[dict[str, Any]],
) -> dict[int, int]:
    groups = path.get("workflow_steps")
    if not isinstance(groups, list) or any(not isinstance(row, Mapping) for row in groups):
        raise ValueError("Semantic source workflow candidates are malformed")
    admitted_groups: list[dict[str, Any]] = []
    step_remap: dict[int, int] = {}
    old_index = 0
    next_index = 0
    for group in groups:
        steps = group.get("steps")
        if not isinstance(steps, list) or any(not isinstance(row, Mapping) for row in steps):
            raise ValueError("Semantic source workflow candidates are malformed")
        admitted_steps = []
        for raw_step in steps:
            step = dict(raw_step)
            if _candidate_supported(
                step,
                allowed_spans=allowed_spans,
                evidence_sources=evidence_sources,
            ):
                step_remap[old_index] = next_index
                next_index += 1
                admitted_steps.append(step)
            else:
                rejections.append(_rejection("first_path", "workflow_step", step))
            old_index += 1
        if admitted_steps:
            admitted_groups.append({**dict(group), "steps": admitted_steps})
    path["workflow_steps"] = admitted_groups
    return step_remap


def _admit_axis_rows(
    value: Any,
    *,
    field: str,
    kind: str,
    allowed_spans: tuple[tuple[str, int, int], ...] | None,
    evidence_sources: Mapping[str, str],
    step_remap: Mapping[int, int],
    binding_key: str,
    rejections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"Semantic source {kind} candidates are malformed")
    admitted = []
    for raw_row in value:
        row = deepcopy(dict(raw_row))
        if not _candidate_supported(
            row,
            allowed_spans=allowed_spans,
            evidence_sources=evidence_sources,
        ):
            rejections.append(_rejection(field, kind, row))
            continue
        binding = row.get(binding_key)
        if binding is not None:
            if not isinstance(binding, dict):
                raise ValueError(f"Semantic source {kind} binding is malformed")
            old_index = binding.get("step_index")
            if old_index not in step_remap:
                raise ValueError(
                    f"Semantic source {kind} binds a rejected workflow candidate"
                )
            binding["step_index"] = step_remap[int(old_index)]
        admitted.append(row)
    return admitted


def _admit_dependencies(
    value: Any,
    *,
    allowed_spans: tuple[tuple[str, int, int], ...] | None,
    evidence_sources: Mapping[str, str],
    step_remap: Mapping[int, int],
    rejections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError("Semantic source dependency candidates are malformed")
    admitted = []
    for raw_row in value:
        row = deepcopy(dict(raw_row))
        if not _candidate_supported(
            row,
            allowed_spans=allowed_spans,
            evidence_sources=evidence_sources,
        ):
            rejections.append(_rejection("dependency", "external_system", row))
            continue
        consumer = row.get("consumer")
        if isinstance(consumer, dict) and consumer.get("kind") == "workflow_step":
            old_index = consumer.get("step_index")
            if old_index in step_remap:
                consumer["step_index"] = step_remap[int(old_index)]
            else:
                row["consumer"] = None
                rejections.append(
                    _rejection("dependency", "depends_on", row, reason="rejected_subject")
                )
        admitted.append(row)
    return admitted


def _settled_field_spans(
    row: Mapping[str, Any],
    *,
    evidence_sources: Mapping[str, str],
) -> tuple[tuple[str, int, int], ...] | None:
    if row.get("status") not in {"explicit", "source_entailable"}:
        return None
    return _citation_spans(row.get("source_refs"), evidence_sources=evidence_sources)


def _candidate_supported(
    row: Mapping[str, Any],
    *,
    allowed_spans: tuple[tuple[str, int, int], ...] | None,
    evidence_sources: Mapping[str, str],
) -> bool:
    if allowed_spans is None:
        return True
    candidate_spans = _citation_spans(
        row.get("source_refs"), evidence_sources=evidence_sources
    )
    return any(
        _spans_overlap(candidate, allowed)
        for candidate in candidate_spans
        for allowed in allowed_spans
    )


def _rejection(
    field: str,
    kind: str,
    row: Mapping[str, Any],
    *,
    reason: str = "outside_settled_evidence",
) -> dict[str, Any]:
    return {
        "field": field,
        "kind": kind,
        "reason": reason,
        "source_refs": deepcopy(row.get("source_refs")),
    }


def _citation_spans(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> tuple[tuple[str, int, int], ...]:
    if not isinstance(value, list) or not value or any(
        not isinstance(row, Mapping) for row in value
    ):
        raise ValueError("Semantic materiality source citation is malformed")
    result = []
    for row in value:
        resolved = resolve_semantic_source_ref(row, evidence_sources=evidence_sources)
        result.append(
            (
                str(resolved["source_id"]),
                int(resolved["char_start"]),
                int(resolved["char_end"]),
            )
        )
    return tuple(result)


def _spans_overlap(
    left: tuple[str, int, int], right: tuple[str, int, int]
) -> bool:
    return left[0] == right[0] and max(left[1], right[1]) < min(left[2], right[2])


def require_authorized_source_assumptions(
    source: Mapping[str, Any], decision_value: Any,
) -> None:
    """Reject source assumptions outside independently authorized materiality fields."""

    if decision_value is None:
        return
    allowed = set(authorized_source_assumption_fields(decision_value))
    boundary = source.get("boundary")
    assumptions = boundary.get("assumptions", []) if isinstance(boundary, Mapping) else []
    if not isinstance(assumptions, list) or any(
        not isinstance(row, Mapping) or row.get("materiality_field") not in allowed
        for row in assumptions
    ):
        raise ValueError("Semantic source assumption lacks materiality authorization")


def authorized_source_assumption_fields(value: Any) -> tuple[str, ...]:
    """Return the only materiality fields a source author may assume."""

    if value is None:
        return tuple(SEMANTIC_CLARIFICATION_FIELDS)
    authorization = materiality_authorization_view(value)
    return tuple(
        field for field, row in authorization["fields"].items()
        if row["status"] == "nonmaterial_assumption"
    )


def source_with_authorized_assumptions(
    source: Mapping[str, Any], decision_value: Any,
) -> dict[str, Any]:
    """Admit only assumptions authorized by independent materiality custody."""

    admitted = deepcopy(dict(source))
    boundary = admitted.get("boundary")
    if not isinstance(boundary, dict) or not isinstance(boundary.get("assumptions"), list):
        raise ValueError("Semantic source assumptions are malformed")
    allowed = set(authorized_source_assumption_fields(decision_value))
    boundary["assumptions"] = [
        row for row in boundary["assumptions"]
        if isinstance(row, Mapping) and row.get("materiality_field") in allowed
    ]
    return admitted


def _field_decision_variants(
    field: str, *, variants: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    applicable: list[dict[str, Any]] = []
    for raw in variants:
        variant = deepcopy(raw)
        if field not in variant["properties"]["field"]["enum"]:
            continue
        variant["required"].remove("field")
        variant["properties"].pop("field")
        applicable.append(variant)
    if not applicable:
        raise RuntimeError("materiality field has no decision contract")
    return applicable


__all__ = [
    "PARALLEL_MATERIALITY_DECISION_VERSION",
    "SEMANTIC_SOURCE_ADMISSION_VERSION",
    "admit_source_candidates_by_materiality",
    "assemble_parallel_materiality_assessment",
    "authorized_source_assumption_fields",
    "canonical_parallel_materiality_decision",
    "materiality_authorization_view",
    "require_materiality_source_coverage",
    "require_authorized_source_assumptions",
    "source_with_authorized_assumptions",
    "parallel_materiality_decision_schema",
]
