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
    SEMANTIC_NONMATERIAL_ASSUMPTION_FIELDS,
    require_semantic_materiality_assessment,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolve_semantic_source_ref,
    semantic_source_ref_schema,
)


PARALLEL_MATERIALITY_DECISION_VERSION = (
    "odylith.greenfield.parallel-materiality-decision.v3"
)
SEMANTIC_SOURCE_ADMISSION_VERSION = "odylith.greenfield.semantic-source-admission.v1"


def parallel_materiality_decision_schema(
    *, source_ref_schema: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return the screen schema without atomic-span or graph authority."""

    source_ref = dict(source_ref_schema or semantic_source_ref_schema())
    field_names = tuple(SEMANTIC_CLARIFICATION_FIELDS)
    fields = {
        field: {
            "anyOf": [
                {"$ref": "#/$defs/resolved_field"},
                *(
                    [{"$ref": "#/$defs/nonmaterial_field"}]
                    if field in SEMANTIC_NONMATERIAL_ASSUMPTION_FIELDS
                    else []
                ),
            ],
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
                        clarification={"$ref": "#/$defs/no_clarification"},
                    ),
                    _outcome_variant(
                        decision="clarification_required",
                        clarification={"$ref": "#/$defs/clarification"},
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
        "$defs": {
            "source_ref": source_ref,
            "resolved_field": _compact_field_schema(
                statuses=("explicit", "source_entailable"),
                source_ref_minimum=1,
            ),
            "nonmaterial_field": _compact_field_schema(
                statuses=("nonmaterial_assumption",),
                source_ref_minimum=0,
                source_ref_maximum=0,
            ),
            "no_clarification": _compact_clarification_schema(
                field_names=("",), source_ref_minimum=0, empty=True
            ),
            "clarification": _compact_clarification_schema(
                field_names=field_names, source_ref_minimum=1, empty=False
            ),
        },
    }


def _compact_field_schema(
    *, statuses: tuple[str, ...], source_ref_minimum: int,
    source_ref_maximum: int = 8,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "source_refs", "alternatives"],
        "properties": {
            "status": {"type": "string", "enum": list(statuses)},
            "source_refs": {
                "type": "array",
                "minItems": source_ref_minimum,
                "maxItems": source_ref_maximum,
                "items": {"$ref": "#/$defs/source_ref"},
            },
            "alternatives": {
                "type": "array", "minItems": 0, "maxItems": 0,
                "items": {"type": "string", "minLength": 1, "maxLength": 600},
            },
        },
    }


def _compact_clarification_schema(
    *, field_names: tuple[str, ...], source_ref_minimum: int, empty: bool,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["field", "question", "source_refs", "alternatives"],
        "properties": {
            "field": {"type": "string", "enum": list(field_names)},
            "question": (
                {"type": "string", "enum": [""]}
                if empty
                else {"type": "string", "minLength": 1, "maxLength": 600}
            ),
            "source_refs": {
                "type": "array", "minItems": source_ref_minimum,
                "maxItems": 0 if empty else 8,
                "items": {"$ref": "#/$defs/source_ref"},
            },
            "alternatives": {
                "type": "array", "minItems": 0, "maxItems": 0,
                "items": {"type": "string", "minLength": 1, "maxLength": 600},
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


def align_source_policy_kinds_to_materiality(
    source_value: Any, decision_value: Any
) -> dict[str, Any]:
    """Make final typed field custody authoritative for exact cited policy kinds."""

    canonical_parallel_materiality_decision(decision_value)
    if not isinstance(source_value, Mapping):
        raise ValueError("source policy alignment requires one source graph")
    source = deepcopy(dict(source_value))
    fields = decision_value.get("fields")
    if not isinstance(fields, Mapping):
        raise ValueError("source policy alignment requires keyed materiality fields")
    kind_refs: dict[str, set[tuple[str, str, int]]] = {}
    for field, policy_kind in (
        ("constraint", "operating_invariant"),
        ("non_goal", "excluded_capability"),
    ):
        row = fields.get(field)
        refs = row.get("source_refs") if isinstance(row, Mapping) else None
        if not isinstance(refs, list):
            raise ValueError("source policy alignment lacks materiality custody")
        kind_refs[policy_kind] = {_source_ref_key(ref) for ref in refs}
    boundary = source.get("boundary")
    policies = boundary.get("policies") if isinstance(boundary, Mapping) else None
    if not isinstance(policies, list) or any(
        not isinstance(policy, Mapping) for policy in policies
    ):
        raise ValueError("source policy alignment requires typed policies")
    aligned: list[dict[str, Any]] = []
    for raw in policies:
        policy = deepcopy(dict(raw))
        refs = policy.get("source_refs")
        if not isinstance(refs, list):
            raise ValueError("source policy alignment lacks policy custody")
        policy_refs = {_source_ref_key(ref) for ref in refs}
        assignments = [
            kind for kind, accepted in kind_refs.items() if policy_refs & accepted
        ]
        if len(assignments) > 1:
            aligned.extend(
                _split_policy_by_authoritative_citations(
                    policy, refs=refs, kind_refs=kind_refs
                )
            )
            continue
        if assignments:
            policy["policy_kind"] = assignments[0]
        aligned.append(policy)
    source["boundary"] = {**dict(boundary), "policies": aligned}
    return source


def materiality_policy_conflict_refs(value: Any) -> list[dict[str, Any]]:
    """Return exact citations that one critic assigned to both policy kinds."""

    canonical_parallel_materiality_decision(value)
    fields = value.get("fields")
    if not isinstance(fields, Mapping):
        raise ValueError("source policy alignment requires keyed materiality fields")
    rows = {
        field: fields[field].get("source_refs")
        for field in ("constraint", "non_goal")
        if isinstance(fields.get(field), Mapping)
    }
    if any(not isinstance(refs, list) for refs in rows.values()):
        raise ValueError("source policy alignment lacks materiality custody")
    non_goal_keys = {_source_ref_key(ref) for ref in rows["non_goal"]}
    return [
        deepcopy(dict(ref))
        for ref in rows["constraint"]
        if _source_ref_key(ref) in non_goal_keys
    ]


def settle_independently_confirmed_policy_kinds(
    value: Any,
    *,
    assignments: Mapping[tuple[str, str, int], str],
) -> dict[str, Any]:
    """Resolve a critic conflation only from matching independent source judgments."""

    result = deepcopy(dict(value))
    fields = result.get("fields")
    if not isinstance(fields, Mapping):
        raise ValueError("source policy alignment requires keyed materiality fields")
    for ref in materiality_policy_conflict_refs(result):
        key = _source_ref_key(ref)
        kind = assignments.get(key)
        if kind not in {"operating_invariant", "excluded_capability"}:
            raise ValueError("independent source policy kind is unresolved")
        losing_field = "non_goal" if kind == "operating_invariant" else "constraint"
        row = deepcopy(dict(fields[losing_field]))
        row["source_refs"] = [
            item
            for item in row.get("source_refs", [])
            if _source_ref_key(item) != key
        ]
        if not row["source_refs"]:
            row.update(
                status="nonmaterial_assumption",
                source_refs=[],
                alternatives=[],
            )
        fields[losing_field] = row
    result["fields"] = fields
    canonical_parallel_materiality_decision(result)
    return result


def policy_kind_disagreement_clarification(
    value: Any,
    *,
    source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ask whether a cited restriction excludes a capability or constrains it."""

    result = deepcopy(dict(value))
    result["outcome"] = {
        "decision": "clarification_required",
        "clarification": {
            "field": "non_goal",
            "question": (
                "Should the cited capability be entirely outside the product, or be "
                "included but constrained to deliberate operation?"
            ),
            "source_refs": deepcopy(source_refs),
            "alternatives": [],
        },
    }
    canonical_parallel_materiality_decision(result)
    return result


def _split_policy_by_authoritative_citations(
    policy: Mapping[str, Any],
    *,
    refs: list[Any],
    kind_refs: Mapping[str, set[tuple[str, str, int]]],
) -> list[dict[str, Any]]:
    """Partition a conflated policy without interpreting its source text."""

    result: list[dict[str, Any]] = []
    for raw_ref in refs:
        ref = deepcopy(raw_ref)
        key = _source_ref_key(ref)
        assignments = [kind for kind, accepted in kind_refs.items() if key in accepted]
        if len(assignments) > 1:
            raise ValueError("one source citation spans conflicting final semantic kinds")
        row = deepcopy(dict(policy))
        row["label"] = key[1]
        row["source_refs"] = [ref]
        if assignments:
            row["policy_kind"] = assignments[0]
        result.append(row)
    return result


def _source_ref_key(value: Any) -> tuple[str, str, int]:
    if not isinstance(value, Mapping):
        raise ValueError("source policy alignment citation is malformed")
    occurrence = value.get("occurrence")
    if isinstance(occurrence, bool) or not isinstance(occurrence, int):
        raise ValueError("source policy alignment citation occurrence is malformed")
    return (
        str(value.get("source_id") or ""),
        str(value.get("quote") or ""),
        occurrence,
    )


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
    """Require every critic-settled material axis to exist as a typed fact."""

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
    workflow_spans = tuple(
        span
        for field in ("first_path", "state_object", "visible_result", "dependency")
        for span in field_spans[field] or ()
    )
    rejections: list[dict[str, Any]] = []
    step_remap = _admit_workflow_steps(
        path,
        allowed_spans=workflow_spans,
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
        _nested_source_refs(row), evidence_sources=evidence_sources
    )
    return any(
        _spans_overlap(candidate, allowed)
        for candidate in candidate_spans
        for allowed in allowed_spans
    )


def _nested_source_refs(value: Any) -> list[Mapping[str, Any]]:
    """Return every typed citation carried by one candidate object."""

    refs: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key == "source_refs":
                if not isinstance(nested, list) or any(
                    not isinstance(row, Mapping) for row in nested
                ):
                    raise ValueError("Semantic source candidate citation is malformed")
                refs.extend(nested)
            else:
                refs.extend(_nested_source_refs(nested))
    elif isinstance(value, list):
        for nested in value:
            refs.extend(_nested_source_refs(nested))
    return refs


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


__all__ = [
    "PARALLEL_MATERIALITY_DECISION_VERSION",
    "SEMANTIC_SOURCE_ADMISSION_VERSION",
    "admit_source_candidates_by_materiality",
    "align_source_policy_kinds_to_materiality",
    "assemble_parallel_materiality_assessment",
    "authorized_source_assumption_fields",
    "canonical_parallel_materiality_decision",
    "materiality_policy_conflict_refs",
    "materiality_authorization_view",
    "policy_kind_disagreement_clarification",
    "require_materiality_source_coverage",
    "require_authorized_source_assumptions",
    "source_with_authorized_assumptions",
    "settle_independently_confirmed_policy_kinds",
    "parallel_materiality_decision_schema",
]
