"""Apply formal semantic PatchSet operations to proposal source facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import first_path_has_action_signal
from odylith.runtime.domain_intelligence.greenfield_patch_projection_scope import (
    patch_operation_explicit_affected_projections,
)
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_SEMANTIC_LAYER = "semantic_model"
_LEDGER_KEY = "semantic_patch_ledger"


@dataclass(frozen=True)
class SemanticPatchApplication:
    """Application summary for semantic PatchSet operations."""

    changed: bool
    operation_ids: tuple[str, ...]
    applied_fields: tuple[str, ...]
    affected_projections: tuple[str, ...]
    completion_required: bool


def apply_semantic_patch_operations(
    proposal: dict[str, Any],
    operations: Sequence[Mapping[str, Any]],
) -> bool:
    """Apply host-authored semantic replacement facts before projection rerender."""

    return apply_semantic_patch_operations_detailed(proposal, operations).changed


def apply_semantic_patch_operations_detailed(
    proposal: dict[str, Any],
    operations: Sequence[Mapping[str, Any]],
) -> SemanticPatchApplication:
    """Apply semantic repairs and return structured rerender custody details."""

    changed = False
    applied_entries: list[dict[str, Any]] = []
    applied_fields: list[str] = []
    operation_ids: list[str] = []
    affected_projections: list[str] = []
    completion_required = False
    for operation in operations:
        if normalize_token(operation.get("target_layer")) != _SEMANTIC_LAYER:
            continue
        target = _semantic_target(operation)
        applied_field = _apply_semantic_operation(proposal, operation, target=target)
        if not applied_field:
            continue
        operation_id = normalize_string(operation.get("operation_id"))
        explicit_scope = patch_operation_explicit_affected_projections(operation)
        changed = True
        applied_fields.append(applied_field)
        if operation_id:
            operation_ids.append(operation_id)
        affected_projections.extend(explicit_scope)
        completion_required = completion_required or target == "first_path" or not explicit_scope
        applied_entries.append(_ledger_entry(operation, applied_field=applied_field))
    if applied_entries:
        ledger = proposal.setdefault(_LEDGER_KEY, [])
        if isinstance(ledger, list):
            ledger.extend(applied_entries)
        else:
            proposal[_LEDGER_KEY] = applied_entries
    return SemanticPatchApplication(
        changed=changed,
        operation_ids=tuple(dict.fromkeys(operation_ids)),
        applied_fields=tuple(dict.fromkeys(applied_fields)),
        affected_projections=tuple(dict.fromkeys(affected_projections)),
        completion_required=bool(completion_required),
    )


def _apply_semantic_operation(proposal: dict[str, Any], operation: Mapping[str, Any], *, target: str = "") -> str:
    target = target or _semantic_target(operation)
    replacement = operation.get("replacement_fact")
    record_noop = _records_host_adjudication(operation)
    if target == "first_path":
        return _set_first_path_contract(
            proposal,
            _replacement_text(replacement, _FIRST_PATH_KEYS),
            require_action=True,
            record_noop=record_noop,
        )
    if target == "proof_boundary":
        return _set_domain_ontology_text(
            proposal,
            "proof_boundary",
            _replacement_text(replacement, _PROOF_BOUNDARY_KEYS),
            record_noop=record_noop,
        )
    if target == "state_object":
        return _set_domain_ontology_text(
            proposal,
            "state_object",
            _replacement_text(replacement, _STATE_OBJECT_KEYS),
            record_noop=record_noop,
        )
    if target == "human_actors":
        rows, explicit = _replacement_list_fact(replacement, _ACTOR_KEYS)
        return _set_domain_ontology_list(
            proposal,
            "human_actors",
            rows,
            explicit_empty=explicit,
            record_noop=record_noop,
        )
    if target == "external_systems":
        rows, explicit = _replacement_list_fact(replacement, _EXTERNAL_SYSTEM_KEYS)
        return _set_domain_ontology_list(
            proposal,
            "external_systems",
            rows,
            explicit_empty=explicit,
            record_noop=record_noop,
        )
    if target == "internal_systems":
        rows, explicit = _replacement_list_fact(replacement, _INTERNAL_SYSTEM_KEYS)
        return _set_domain_ontology_list(
            proposal,
            "internal_systems",
            rows,
            explicit_empty=explicit,
            record_noop=record_noop,
        )
    return ""


def _semantic_target(operation: Mapping[str, Any]) -> str:
    operation_kind = normalize_token(operation.get("operation_kind"))
    target = _TARGET_BY_OPERATION_KIND.get(operation_kind)
    if target:
        return target
    for key in ("target_path", "semantic_node_id"):
        target = _TARGET_BY_EXACT_PATH.get(normalize_token(operation.get(key)))
        if target:
            return target
    return ""


def _set_first_path_contract(
    proposal: dict[str, Any],
    value: str,
    *,
    require_action: bool = False,
    record_noop: bool = False,
) -> str:
    text = normalize_string(value)
    if not text:
        return ""
    if require_action and not first_path_has_action_signal(text):
        return ""
    semantic = _semantic_model_dict(proposal)
    contract = _child_dict(semantic, "first_path_contract")
    intent = _intent_dict(proposal)
    current_contract = normalize_string(contract.get("raw_path"))
    current_intent = normalize_string(intent.get("first_path"))
    if current_contract == text and current_intent == text:
        return "semantic_model.first_path_contract.raw_path" if record_noop else ""
    contract["raw_path"] = text
    capability = first_path_capability_phrase(text, fallback=text, gerund=True)
    if capability:
        contract["capability"] = capability
    intent["first_path"] = text
    return "semantic_model.first_path_contract.raw_path"


def _set_domain_ontology_text(
    proposal: dict[str, Any],
    key: str,
    value: str,
    *,
    record_noop: bool = False,
) -> str:
    text = normalize_string(value)
    if not text:
        return ""
    ontology = _domain_ontology_dict(proposal)
    intent = _intent_dict(proposal)
    current_ontology = normalize_string(ontology.get(key))
    current_intent = normalize_string(intent.get(key))
    if current_ontology == text and current_intent == text:
        return f"semantic_model.domain_ontology.{key}" if record_noop else ""
    ontology[key] = text
    intent[key] = text
    return f"semantic_model.domain_ontology.{key}"


def _set_domain_ontology_list(
    proposal: dict[str, Any],
    key: str,
    values: Sequence[str],
    *,
    explicit_empty: bool = False,
    record_noop: bool = False,
) -> str:
    rows = [normalize_string(value) for value in values if normalize_string(value)]
    if not rows and not explicit_empty:
        return ""
    ontology = _domain_ontology_dict(proposal)
    intent = _intent_dict(proposal)
    ontology_current = [normalize_string(value) for value in text_values(ontology.get(key))]
    current = [normalize_string(value) for value in text_values(intent.get(key))]
    if ontology_current == rows and current == rows:
        return f"semantic_model.domain_ontology.{key}" if record_noop else ""
    ontology[key] = rows
    intent[key] = rows
    return f"semantic_model.domain_ontology.{key}"


def _semantic_model_dict(proposal: dict[str, Any]) -> dict[str, Any]:
    semantic = proposal.get("semantic_model")
    if not isinstance(semantic, dict):
        semantic = {}
        proposal["semantic_model"] = semantic
    return semantic


def _domain_ontology_dict(proposal: dict[str, Any]) -> dict[str, Any]:
    return _child_dict(_semantic_model_dict(proposal), "domain_ontology")


def _child_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    child = parent.get(key)
    if not isinstance(child, dict):
        child = {}
        parent[key] = child
    return child


def _intent_dict(proposal: dict[str, Any]) -> dict[str, Any]:
    intent = proposal.get("intent")
    if not isinstance(intent, dict):
        intent = {}
        proposal["intent"] = intent
    return intent


def _replacement_text(value: Any, keys: Sequence[str]) -> str:
    if isinstance(value, Mapping):
        for key in keys:
            text = normalize_string(value.get(key))
            if text:
                return text
        return ""
    return normalize_string(value)


def _replacement_list_fact(value: Any, keys: Sequence[str]) -> tuple[list[str], bool]:
    if isinstance(value, Mapping):
        for key in keys:
            if key not in value:
                continue
            item = value.get(key)
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                return [normalize_string(row) for row in item if normalize_string(row)], True
            rows = [normalize_string(row) for row in text_values(value.get(key)) if normalize_string(row)]
            if rows:
                return rows, True
        return [], False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [normalize_string(row) for row in value if normalize_string(row)], True
    rows = [normalize_string(row) for row in text_values(value) if normalize_string(row)]
    return rows, bool(rows)


def _records_host_adjudication(operation: Mapping[str, Any]) -> bool:
    if not _operation_replacement_has_semantic_fact(operation):
        return False
    if not isinstance(operation.get("decision_ledger_entry"), Mapping):
        return False
    return _confidence(operation.get("confidence")) > 0.0


def _operation_replacement_has_semantic_fact(operation: Mapping[str, Any]) -> bool:
    replacement = operation.get("replacement_fact")
    target = _semantic_target(operation)
    if target == "human_actors":
        return _replacement_list_fact(replacement, _ACTOR_KEYS)[1]
    if target == "external_systems":
        return _replacement_list_fact(replacement, _EXTERNAL_SYSTEM_KEYS)[1]
    if target == "internal_systems":
        return _replacement_list_fact(replacement, _INTERNAL_SYSTEM_KEYS)[1]
    return _replacement_has_value(replacement)


def _replacement_has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(normalize_string(value))
    if isinstance(value, Mapping):
        return any(_replacement_has_value(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_replacement_has_value(item) for item in value)
    return True


def _ledger_entry(operation: Mapping[str, Any], *, applied_field: str) -> dict[str, Any]:
    entry = operation.get("decision_ledger_entry")
    base = dict(entry) if isinstance(entry, Mapping) else {}
    proof_delta = _ledger_value(operation.get("proof_obligation_delta"))
    if proof_delta:
        base["proof_obligation_delta"] = proof_delta
    base.update(
        {
            "applied_field": applied_field,
            "operation_id": normalize_string(operation.get("operation_id")),
            "target_path": normalize_string(operation.get("target_path")),
            "semantic_node_id": normalize_string(operation.get("semantic_node_id")),
            "issue_code": normalize_token(operation.get("issue_code")),
            "rejected_interpretation": normalize_string(operation.get("rejected_interpretation")),
            "confidence": _confidence(operation.get("confidence")),
        }
    )
    return {key: value for key, value in base.items() if not _empty_ledger_value(value)}


def _ledger_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {normalize_string(key): _ledger_value(item) for key, item in value.items() if normalize_string(key)}
    if isinstance(value, (list, tuple)):
        rows = []
        for item in value:
            ledger_item = _ledger_value(item)
            if not _empty_ledger_value(ledger_item):
                rows.append(ledger_item)
        return rows
    if isinstance(value, str):
        return normalize_string(value)
    return value


def _confidence(value: Any) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0


def _empty_ledger_value(value: Any) -> bool:
    return value is None or value == "" or value == []


_FIRST_PATH_KEYS = ("first_path", "raw_path", "corrected_interpretation", "replacement", "text")
_PROOF_BOUNDARY_KEYS = ("proof_boundary", "release_boundary", "corrected_interpretation", "replacement", "text")
_STATE_OBJECT_KEYS = ("state_object", "state", "corrected_interpretation", "replacement", "text")
_ACTOR_KEYS = ("human_actors", "actors", "actor", "corrected_interpretation", "replacement")
_INTERNAL_SYSTEM_KEYS = ("internal_systems", "systems", "system", "corrected_interpretation", "replacement")
_EXTERNAL_SYSTEM_KEYS = ("external_systems", "systems", "system", "corrected_interpretation", "replacement")
_TARGET_BY_OPERATION_KIND = {
    "semantic_external_systems": "external_systems",
    "semantic_first_path": "first_path",
    "semantic_human_actors": "human_actors",
    "semantic_internal_systems": "internal_systems",
    "semantic_proof_boundary": "proof_boundary",
    "semantic_state_object": "state_object",
}
_TARGET_BY_EXACT_PATH = {
    "proposal.semantic_model.domain_ontology.external_systems": "external_systems",
    "proposal.semantic_model.domain_ontology.human_actors": "human_actors",
    "proposal.semantic_model.domain_ontology.internal_systems": "internal_systems",
    "proposal.semantic_model.domain_ontology.proof_boundary": "proof_boundary",
    "proposal.semantic_model.domain_ontology.state_object": "state_object",
    "proposal.semantic_model.first_path_contract": "first_path",
    "semantic_model.domain_ontology.external_systems": "external_systems",
    "semantic_model.domain_ontology.human_actors": "human_actors",
    "semantic_model.domain_ontology.internal_systems": "internal_systems",
    "semantic_model.domain_ontology.proof_boundary": "proof_boundary",
    "semantic_model.domain_ontology.state_object": "state_object",
    "semantic_model.external_systems": "external_systems",
    "semantic_model.first_path_contract": "first_path",
    "semantic_model.first_path_contract.raw_path": "first_path",
    "semantic_model.human_actors": "human_actors",
    "semantic_model.internal_systems": "internal_systems",
    "semantic_model.proof_boundary": "proof_boundary",
    "semantic_model.state_object": "state_object",
    "semanticmodelir.domain_ontology.external_systems": "external_systems",
    "semanticmodelir.domain_ontology.human_actors": "human_actors",
    "semanticmodelir.domain_ontology.internal_systems": "internal_systems",
    "semanticmodelir.domain_ontology.proof_boundary": "proof_boundary",
    "semanticmodelir.domain_ontology.state_object": "state_object",
    "semanticmodelir.external_systems": "external_systems",
    "semanticmodelir.first_path_contract": "first_path",
    "semanticmodelir.first_path_contract.raw_path": "first_path",
    "semanticmodelir.human_actors": "human_actors",
    "semanticmodelir.internal_systems": "internal_systems",
    "semanticmodelir.proof_boundary": "proof_boundary",
    "semanticmodelir.state_object": "state_object",
}


__all__ = ["SemanticPatchApplication", "apply_semantic_patch_operations", "apply_semantic_patch_operations_detailed"]
