"""Apply formal semantic PatchSet operations to proposal source facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.safe_ledger_text import safe_ledger_value
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import first_path_has_action_signal
from odylith.runtime.domain_intelligence.greenfield_patch_projection_scope import (
    patch_operation_explicit_affected_projections,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_targets import SemanticPatchTarget
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_targets import (
    semantic_patch_target_for_operation,
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
        target = semantic_patch_target_for_operation(operation)
        applied_field = _apply_semantic_operation(proposal, operation, target=target)
        if not applied_field:
            continue
        operation_id = normalize_string(operation.get("operation_id"))
        explicit_scope = patch_operation_explicit_affected_projections(operation)
        affected_scope = tuple(dict.fromkeys((*explicit_scope, *target.affected_projections)))
        changed = True
        applied_fields.append(applied_field)
        if operation_id:
            operation_ids.append(operation_id)
        affected_projections.extend(affected_scope)
        completion_required = completion_required or target.completion_required or not affected_scope
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


def _apply_semantic_operation(
    proposal: dict[str, Any],
    operation: Mapping[str, Any],
    *,
    target: SemanticPatchTarget | None = None,
) -> str:
    target = target or semantic_patch_target_for_operation(operation)
    if target is None:
        return ""
    replacement = operation.get("replacement_fact")
    record_noop = _records_host_adjudication(operation)
    if target.value_kind == "first_path":
        return _set_first_path_contract(
            proposal,
            _replacement_text(replacement, target.replacement_keys),
            require_action=True,
            record_noop=record_noop,
        )
    if target.value_kind == "text":
        return _set_domain_ontology_text(
            proposal,
            target.target_id,
            _replacement_text(replacement, target.replacement_keys),
            intent_key=target.intent_key,
            source_mirror_paths=target.source_mirror_paths,
            record_noop=record_noop,
        )
    if target.value_kind == "list":
        rows, explicit = _replacement_list_fact(replacement, target.replacement_keys)
        return _set_domain_ontology_list(
            proposal,
            target.target_id,
            rows,
            explicit_empty=explicit,
            intent_key=target.intent_key,
            source_mirror_paths=target.source_mirror_paths,
            record_noop=record_noop,
        )
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
    intent_key: str = "",
    source_mirror_paths: Sequence[str] = (),
    record_noop: bool = False,
) -> str:
    text = normalize_string(value)
    if not text:
        return ""
    ontology = _domain_ontology_dict(proposal)
    intent = _intent_dict(proposal)
    intent_key = intent_key or key
    current_ontology = normalize_string(ontology.get(key))
    current_intent = normalize_string(intent.get(intent_key))
    mirror_current = all(_path_text(proposal, path) == text for path in source_mirror_paths)
    if current_ontology == text and current_intent == text and mirror_current:
        return f"semantic_model.domain_ontology.{key}" if record_noop else ""
    ontology[key] = text
    intent[intent_key] = text
    _set_source_mirror_paths(proposal, source_mirror_paths, text)
    return f"semantic_model.domain_ontology.{key}"


def _set_domain_ontology_list(
    proposal: dict[str, Any],
    key: str,
    values: Sequence[str],
    *,
    explicit_empty: bool = False,
    intent_key: str = "",
    source_mirror_paths: Sequence[str] = (),
    record_noop: bool = False,
) -> str:
    rows = [normalize_string(value) for value in values if normalize_string(value)]
    if not rows and not explicit_empty:
        return ""
    ontology = _domain_ontology_dict(proposal)
    intent = _intent_dict(proposal)
    intent_key = intent_key or key
    ontology_current = [normalize_string(value) for value in text_values(ontology.get(key))]
    current = [normalize_string(value) for value in text_values(intent.get(intent_key))]
    mirror_current = all(_path_text_list(proposal, path) == rows for path in source_mirror_paths)
    if ontology_current == rows and current == rows and mirror_current:
        return f"semantic_model.domain_ontology.{key}" if record_noop else ""
    ontology[key] = rows
    intent[intent_key] = rows
    _set_source_mirror_paths(proposal, source_mirror_paths, list(rows))
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


def _set_source_mirror_paths(proposal: dict[str, Any], paths: Sequence[str], value: Any) -> None:
    for raw_path in paths:
        path = normalize_string(raw_path)
        if not path:
            continue
        current: dict[str, Any] = proposal
        parts = [part for part in path.split(".") if part]
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        if parts:
            current[parts[-1]] = value


def _path_text(proposal: Mapping[str, Any], path: str) -> str:
    return normalize_string(_path_value(proposal, path))


def _path_text_list(proposal: Mapping[str, Any], path: str) -> list[str]:
    return [normalize_string(value) for value in text_values(_path_value(proposal, path)) if normalize_string(value)]


def _path_value(proposal: Mapping[str, Any], path: str) -> Any:
    current: Any = proposal
    for part in (part for part in normalize_string(path).split(".") if part):
        if not isinstance(current, Mapping):
            return ""
        current = current.get(part)
    return current


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
    target = semantic_patch_target_for_operation(operation)
    if target and target.value_kind == "list":
        return _replacement_list_fact(replacement, target.replacement_keys)[1]
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
    entry = _ledger_value(operation.get("decision_ledger_entry"))
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
            "rejected_interpretation": _ledger_value(operation.get("rejected_interpretation")),
            "confidence": _confidence(operation.get("confidence")),
        }
    )
    return {key: value for key, value in base.items() if not _empty_ledger_value(value)}


def _ledger_value(value: Any) -> Any:
    return safe_ledger_value(value)


def _confidence(value: Any) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0


def _empty_ledger_value(value: Any) -> bool:
    return value is None or value == "" or value == []


__all__ = ["SemanticPatchApplication", "apply_semantic_patch_operations", "apply_semantic_patch_operations_detailed"]
