"""Apply formal semantic PatchSet operations to proposal source facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import first_path_has_action_signal
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_SEMANTIC_LAYER = "semantic_model"
_LEDGER_KEY = "semantic_patch_ledger"


def apply_semantic_patch_operations(
    proposal: dict[str, Any],
    operations: Sequence[Mapping[str, Any]],
) -> bool:
    """Apply host-authored semantic replacement facts before projection rerender."""

    changed = False
    applied_entries: list[dict[str, Any]] = []
    for operation in operations:
        if normalize_token(operation.get("target_layer")) != _SEMANTIC_LAYER:
            continue
        applied_field = _apply_semantic_operation(proposal, operation)
        if not applied_field:
            continue
        changed = True
        applied_entries.append(_ledger_entry(operation, applied_field=applied_field))
    if applied_entries:
        ledger = proposal.setdefault(_LEDGER_KEY, [])
        if isinstance(ledger, list):
            ledger.extend(applied_entries)
        else:
            proposal[_LEDGER_KEY] = applied_entries
    return changed


def _apply_semantic_operation(proposal: dict[str, Any], operation: Mapping[str, Any]) -> str:
    target = _semantic_target(operation)
    replacement = operation.get("replacement_fact")
    if target == "first_path":
        return _set_intent_text(
            proposal,
            "first_path",
            _replacement_text(replacement, _FIRST_PATH_KEYS),
            require_action=True,
        )
    if target == "proof_boundary":
        return _set_intent_text(proposal, "proof_boundary", _replacement_text(replacement, _PROOF_BOUNDARY_KEYS))
    if target == "state_object":
        return _set_intent_text(proposal, "state_object", _replacement_text(replacement, _STATE_OBJECT_KEYS))
    if target == "human_actors":
        return _set_intent_list(proposal, "human_actors", _replacement_list(replacement, _ACTOR_KEYS))
    if target == "external_systems":
        return _set_intent_list(proposal, "external_systems", _replacement_list(replacement, _EXTERNAL_SYSTEM_KEYS))
    if target == "internal_systems":
        return _set_intent_list(proposal, "internal_systems", _replacement_list(replacement, _INTERNAL_SYSTEM_KEYS))
    return ""


def _semantic_target(operation: Mapping[str, Any]) -> str:
    tokens = _semantic_route_tokens(operation)
    if tokens & {"first_path_contract", "first_path"}:
        return "first_path"
    if tokens & {"proof_boundary", "release_boundary"}:
        return "proof_boundary"
    if tokens & {"state_object", "domain_ontology_state"}:
        return "state_object"
    if tokens & {"external_systems", "external_system"}:
        return "external_systems"
    if tokens & {"internal_systems", "internal_system"}:
        return "internal_systems"
    if tokens & {"human_actors", "human_actor", "actors", "actor"}:
        return "human_actors"
    return ""


def _semantic_route_tokens(operation: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in ("target_path", "semantic_node_id"):
        value = normalize_token(operation.get(key))
        if not value:
            continue
        tokens.add(value)
        tokens.update(part for part in value.replace("[", ".").replace("]", ".").split(".") if part)
    return tokens


def _set_intent_text(
    proposal: dict[str, Any],
    key: str,
    value: str,
    *,
    require_action: bool = False,
) -> str:
    text = normalize_string(value)
    if not text:
        return ""
    if require_action and not first_path_has_action_signal(text):
        return ""
    intent = _intent_dict(proposal)
    if normalize_string(intent.get(key)) == text:
        return ""
    intent[key] = text
    proposal.pop("semantic_model", None)
    return f"intent.{key}"


def _set_intent_list(proposal: dict[str, Any], key: str, values: Sequence[str]) -> str:
    rows = [normalize_string(value) for value in values if normalize_string(value)]
    if not rows:
        return ""
    intent = _intent_dict(proposal)
    current = [normalize_string(value) for value in text_values(intent.get(key))]
    if current == rows:
        return ""
    intent[key] = rows
    proposal.pop("semantic_model", None)
    return f"intent.{key}"


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


def _replacement_list(value: Any, keys: Sequence[str]) -> list[str]:
    if isinstance(value, Mapping):
        for key in keys:
            rows = [normalize_string(row) for row in text_values(value.get(key)) if normalize_string(row)]
            if rows:
                return rows
        return []
    return [normalize_string(row) for row in text_values(value) if normalize_string(row)]


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


__all__ = ["apply_semantic_patch_operations"]
