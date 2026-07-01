"""Apply formal artifact-plan PatchSet operations to sanctioned projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import ARTIFACT_PLAN_DICT_ROOTS
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import ARTIFACT_PLAN_LIST_ROOTS
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import ARTIFACT_PLAN_ROW_ROOTS
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_canonical_root
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_is_immutable_field
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_projection_for_path
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_row_root_for_projection
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_projection_id
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_ARTIFACT_PLAN_LAYER = "artifact_plan"
_LEDGER_KEY = "artifact_plan_patch_ledger"
_ROW_TEXT_PATCH_FIELD = {
    "backlog": "product_view",
    "components": "responsibility",
    "diagrams": "summary",
}
_ROW_ALIAS_FIELDS = {
    "backlog": ("workstream_id", "idea_id", "id", "title"),
    "components": ("component_id", "id", "label", "name"),
    "diagrams": ("slug", "id", "title"),
}
_COMPACT_PATCH_META_KEYS = frozenset({"path", "target_path", "value"})
_COMPONENT_CONTRACT_TEXT_FIELD = "produced_outputs"
_SEMANTIC_COMPONENT_CONTRACT_FIELDS = frozenset({"owned_state", "accepted_inputs", "produced_outputs"})


def apply_artifact_plan_patch_operations(
    proposal: dict[str, Any],
    operations: Sequence[Mapping[str, Any]],
) -> bool:
    """Apply host-authored plan replacement facts before artifact rerender."""

    changed = False
    ledger_entries: list[dict[str, Any]] = []
    for operation in operations:
        if normalize_token(operation.get("target_layer")) != _ARTIFACT_PLAN_LAYER:
            continue
        applied_paths = _apply_artifact_plan_operation(proposal, operation)
        if not applied_paths:
            continue
        changed = True
        ledger_entries.append(_ledger_entry(operation, applied_paths=applied_paths))
    if ledger_entries:
        ledger = proposal.setdefault(_LEDGER_KEY, [])
        if isinstance(ledger, list):
            ledger.extend(ledger_entries)
        else:
            proposal[_LEDGER_KEY] = ledger_entries
    return changed


def _apply_artifact_plan_operation(proposal: dict[str, Any], operation: Mapping[str, Any]) -> tuple[str, ...]:
    replacement = operation.get("replacement_fact")
    if not isinstance(replacement, Mapping):
        return ()
    paths: list[str] = []
    paths.extend(_apply_path_value_patch(proposal, replacement))
    for raw_root, patch_value in replacement.items():
        root = artifact_plan_canonical_root(raw_root)
        if root in ARTIFACT_PLAN_DICT_ROOTS and isinstance(patch_value, Mapping):
            paths.extend(_apply_dict_root_patch(proposal, root, patch_value))
        elif root in ARTIFACT_PLAN_LIST_ROOTS:
            paths.extend(_apply_list_root_patch(proposal, root, patch_value))
        elif root in ARTIFACT_PLAN_ROW_ROOTS:
            paths.extend(_apply_row_root_patch(proposal, root, patch_value, operation))
    paths.extend(_apply_compact_row_keyed_patch(proposal, replacement, operation))
    paths.extend(_sync_semantic_model_component_fields(proposal, paths))
    return tuple(dict.fromkeys(paths))


def _apply_path_value_patch(proposal: dict[str, Any], replacement: Mapping[str, Any]) -> tuple[str, ...]:
    path = normalize_string(replacement.get("path") or replacement.get("target_path"))
    if not path or "value" not in replacement:
        return ()
    root, tail = _split_root_path(path)
    if not root or not tail:
        return ()
    if root in ARTIFACT_PLAN_DICT_ROOTS:
        return _set_dict_path(_ensure_dict_root(proposal, root), tail, replacement.get("value"), prefix=root)
    if root in ARTIFACT_PLAN_ROW_ROOTS:
        row_patch = {
            "index": _row_index_from_path(path),
            "fields": {_tail_without_row_index(tail): replacement.get("value")},
        }
        return _apply_row_root_patch(proposal, root, row_patch, {})
    if root in ARTIFACT_PLAN_LIST_ROOTS and len(tail) == 1:
        return _apply_list_root_patch(proposal, root, replacement.get("value"))
    return ()


def _apply_dict_root_patch(proposal: dict[str, Any], root: str, patch: Mapping[str, Any]) -> tuple[str, ...]:
    target = _ensure_dict_root(proposal, root)
    paths: list[str] = []
    for raw_field, value in patch.items():
        field = normalize_string(raw_field)
        if not field or field in {"path", "target_path", "value"} or artifact_plan_is_immutable_field(field):
            continue
        if isinstance(value, Mapping) and isinstance(target.get(field), dict):
            paths.extend(_merge_mapping(target[field], value, prefix=f"{root}.{field}"))
            continue
        if _set_if_changed(target, field, value):
            paths.append(f"{root}.{field}")
    return tuple(paths)


def _apply_list_root_patch(proposal: dict[str, Any], root: str, value: Any) -> tuple[str, ...]:
    rows = [normalize_string(item) for item in text_values(value) if normalize_string(item)]
    if not rows:
        return ()
    if proposal.get(root) == rows:
        return ()
    proposal[root] = rows
    return (root,)


def _apply_row_root_patch(
    proposal: dict[str, Any],
    root: str,
    patch_value: Any,
    operation: Mapping[str, Any],
) -> tuple[str, ...]:
    rows = _ensure_row_root(proposal, root)
    patches = _row_patches(patch_value)
    paths: list[str] = []
    for patch in patches:
        row = _select_row(rows, root=root, patch=patch, operation=operation)
        if row is None:
            continue
        fields = patch.get("fields") if isinstance(patch.get("fields"), Mapping) else patch
        row_index = rows.index(row)
        for raw_field, value in fields.items():
            field = normalize_string(raw_field)
            if (
                not field
                or field in {"fields", "index", "match", "selector"}
                or artifact_plan_is_immutable_field(field)
            ):
                continue
            paths.extend(_set_row_field(row, root=root, row_index=row_index, field=field, value=value))
    return tuple(paths)


def _apply_compact_row_keyed_patch(
    proposal: dict[str, Any],
    replacement: Mapping[str, Any],
    operation: Mapping[str, Any],
) -> tuple[str, ...]:
    root = _operation_row_root(operation)
    if not root:
        return ()
    rows = _ensure_row_root(proposal, root)
    paths: list[str] = []
    for raw_key, patch_value in replacement.items():
        key = normalize_string(raw_key)
        if not key or _compact_key_is_reserved(key):
            continue
        row = _select_compact_row(rows, root=root, key=key)
        if row is None:
            continue
        row_index = rows.index(row)
        paths.extend(_apply_compact_row_value(row, root=root, row_index=row_index, value=patch_value))
    return tuple(paths)


def _operation_row_root(operation: Mapping[str, Any]) -> str:
    projections: list[Any] = []
    affected = operation.get("affected_projections")
    if isinstance(affected, Sequence) and not isinstance(affected, (str, bytes, bytearray)):
        projections.extend(affected)
    projections.extend(
        (
            operation.get("projection_kind"),
            operation.get("surface"),
            artifact_plan_projection_for_path(operation.get("target_path")),
            artifact_plan_projection_for_path(operation.get("semantic_node_id")),
        )
    )
    for raw_projection in projections:
        projection = artifact_projection_id(raw_projection)
        root = artifact_plan_row_root_for_projection(projection)
        if root:
            return root
    return ""


def _compact_key_is_reserved(value: str) -> bool:
    token = normalize_token(value)
    return (
        token in _COMPACT_PATCH_META_KEYS
        or artifact_plan_canonical_root(token) in ARTIFACT_PLAN_DICT_ROOTS
        or artifact_plan_canonical_root(token) in ARTIFACT_PLAN_LIST_ROOTS
        or artifact_plan_canonical_root(token) in ARTIFACT_PLAN_ROW_ROOTS
    )


def _select_compact_row(rows: Sequence[dict[str, Any]], *, root: str, key: str) -> dict[str, Any] | None:
    matches = [
        row
        for row in rows
        if any(_row_alias_matches(row.get(field), key) for field in _ROW_ALIAS_FIELDS.get(root, ()))
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _row_alias_matches(value: Any, key: str) -> bool:
    text = normalize_string(value)
    return bool(text and normalize_token(text) == normalize_token(key))


def _apply_compact_row_value(
    row: dict[str, Any],
    *,
    root: str,
    row_index: int,
    value: Any,
) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        fields = value.get("fields") if isinstance(value.get("fields"), Mapping) else value
        return _apply_compact_row_fields(row, root=root, row_index=row_index, fields=fields)
    text = normalize_string(value)
    if not text:
        return ()
    field = _ROW_TEXT_PATCH_FIELD.get(root)
    if not field:
        return ()
    paths: list[str] = []
    if _set_if_changed(row, field, text):
        paths.append(f"{root}[{row_index}].{field}")
    if root == "components":
        paths.extend(_apply_component_contract_text_patch(row, row_index=row_index, text=text))
    return tuple(paths)


def _apply_compact_row_fields(
    row: dict[str, Any],
    *,
    root: str,
    row_index: int,
    fields: Mapping[str, Any],
) -> tuple[str, ...]:
    paths: list[str] = []
    for raw_field, value in fields.items():
        field = normalize_string(raw_field)
        if (
            not field
            or field in {"fields", "index", "match", "selector"}
            or artifact_plan_is_immutable_field(field)
        ):
            continue
        if isinstance(value, Mapping) and isinstance(row.get(field), dict):
            paths.extend(_merge_mapping(row[field], value, prefix=f"{root}[{row_index}].{field}"))
            continue
        paths.extend(_set_row_field(row, root=root, row_index=row_index, field=field, value=value))
    return tuple(paths)


def _apply_component_contract_text_patch(row: dict[str, Any], *, row_index: int, text: str) -> tuple[str, ...]:
    contract = row.get("component_contract")
    if not isinstance(contract, dict):
        return ()
    contract_text = _component_contract_patch_text(text)
    if not contract_text:
        return ()
    path = f"components[{row_index}].component_contract.{_COMPONENT_CONTRACT_TEXT_FIELD}"
    return (path,) if _set_if_changed(contract, _COMPONENT_CONTRACT_TEXT_FIELD, contract_text) else ()


def _component_contract_patch_text(value: str) -> str:
    text = normalize_string(value).strip(" .")
    if not text:
        return ""
    suffix = "blocked-state detail, reviewer explanation, next-step context, and handoff context"
    if suffix in text.casefold():
        return text
    return f"{text}, {suffix}"


def _sync_semantic_model_component_fields(proposal: dict[str, Any], applied_paths: Sequence[str]) -> tuple[str, ...]:
    semantic = proposal.get("semantic_model")
    if not isinstance(semantic, dict):
        return ()
    model_components = semantic.get("components")
    proposal_components = proposal.get("components")
    if not isinstance(model_components, list) or not isinstance(proposal_components, list):
        return ()
    paths: list[str] = []
    for path in applied_paths:
        sync_path = normalize_string(path)
        if not sync_path.startswith("components[") or ".component_contract." not in sync_path:
            continue
        field = sync_path.split(".component_contract.", 1)[1].split(".", 1)[0]
        if field not in _SEMANTIC_COMPONENT_CONTRACT_FIELDS:
            continue
        component_index = _row_index_from_path(sync_path)
        if component_index is None or component_index < 0 or component_index >= len(proposal_components):
            continue
        proposal_row = proposal_components[component_index]
        if not isinstance(proposal_row, Mapping):
            continue
        component_id = normalize_string(proposal_row.get("component_id"))
        contract = proposal_row.get("component_contract")
        if not component_id or not isinstance(contract, Mapping):
            continue
        value = contract.get(field)
        model_index, model_row = _semantic_component_row(model_components, component_id=component_id)
        if model_row is None:
            continue
        if _set_if_changed(model_row, field, value):
            paths.append(f"semantic_model.components[{model_index}].{field}")
    return tuple(paths)


def _semantic_component_row(rows: Sequence[Any], *, component_id: str) -> tuple[int, dict[str, Any] | None]:
    for index, row in enumerate(rows):
        if isinstance(row, dict) and normalize_string(row.get("component_id")) == component_id:
            return index, row
    return -1, None


def _row_patches(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        rows = value.get("rows")
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
            return tuple(row for row in rows if isinstance(row, Mapping))
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(row for row in value if isinstance(row, Mapping))
    return ()


def _select_row(
    rows: list[dict[str, Any]],
    *,
    root: str,
    patch: Mapping[str, Any],
    operation: Mapping[str, Any],
) -> dict[str, Any] | None:
    index = _int_or_none(patch.get("index"))
    if index is None:
        index = _row_index_from_path(normalize_string(operation.get("target_path")))
    if index is not None and 0 <= index < len(rows):
        return rows[index]
    matcher = patch.get("match") if isinstance(patch.get("match"), Mapping) else patch.get("selector")
    if isinstance(matcher, Mapping):
        matched = _find_matching_row(rows, matcher)
        if matched is not None:
            return matched
    target = normalize_string(operation.get("target_path"))
    if target:
        matched = _find_matching_row(rows, _target_matcher(root, target))
        if matched is not None:
            return matched
    return None


def _find_matching_row(rows: Sequence[dict[str, Any]], matcher: Mapping[str, Any]) -> dict[str, Any] | None:
    for row in rows:
        if all(
            normalize_string(row.get(key)) == normalize_string(value)
            for key, value in matcher.items()
            if normalize_string(key) and normalize_string(value)
        ):
            return row
    return None


def _target_matcher(root: str, target_path: str) -> dict[str, str]:
    token = normalize_token(target_path)
    keys = {
        "backlog": ("workstream_id", "title"),
        "components": ("component_id", "label"),
        "diagrams": ("slug", "title"),
    }.get(root, ())
    for key in keys:
        prefix = f"{key}_"
        if prefix in token:
            return {key: token.split(prefix, 1)[1]}
    return {}


def _merge_mapping(target: dict[str, Any], patch: Mapping[str, Any], *, prefix: str) -> tuple[str, ...]:
    paths: list[str] = []
    for raw_field, value in patch.items():
        field = normalize_string(raw_field)
        if not field or artifact_plan_is_immutable_field(field):
            continue
        if isinstance(value, Mapping) and isinstance(target.get(field), dict):
            paths.extend(_merge_mapping(target[field], value, prefix=f"{prefix}.{field}"))
            continue
        if _set_if_changed(target, field, value):
            paths.append(f"{prefix}.{field}")
    return tuple(paths)


def _set_row_field(
    row: dict[str, Any],
    *,
    root: str,
    row_index: int,
    field: str,
    value: Any,
) -> tuple[str, ...]:
    parts = tuple(part for part in field.split(".") if part)
    if len(parts) < 2:
        return (f"{root}[{row_index}].{field}",) if _set_if_changed(row, field, value) else ()
    if any(artifact_plan_is_immutable_field(part) for part in parts):
        return ()
    current = row
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    leaf = parts[-1]
    return (f"{root}[{row_index}].{'.'.join(parts)}",) if _set_if_changed(current, leaf, value) else ()


def _set_dict_path(target: dict[str, Any], path: Sequence[str], value: Any, *, prefix: str) -> tuple[str, ...]:
    if not path:
        return ()
    current = target
    for field in path[:-1]:
        if artifact_plan_is_immutable_field(field):
            return ()
        child = current.get(field)
        if not isinstance(child, dict):
            child = {}
            current[field] = child
        current = child
    field = path[-1]
    if artifact_plan_is_immutable_field(field):
        return ()
    return (f"{prefix}.{'.'.join(path)}",) if _set_if_changed(current, field, value) else ()


def _set_if_changed(target: dict[str, Any], field: str, value: Any) -> bool:
    next_value = deepcopy(value)
    if target.get(field) == next_value:
        return False
    target[field] = next_value
    return True


def _ensure_dict_root(proposal: dict[str, Any], root: str) -> dict[str, Any]:
    value = proposal.get(root)
    if not isinstance(value, dict):
        value = {}
        proposal[root] = value
    return value


def _ensure_row_root(proposal: dict[str, Any], root: str) -> list[dict[str, Any]]:
    value = proposal.get(root)
    if not isinstance(value, list):
        value = []
        proposal[root] = value
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(item)
    if len(rows) != len(value):
        proposal[root] = rows
    return rows


def _split_root_path(path: str) -> tuple[str, tuple[str, ...]]:
    cleaned = normalize_string(path).replace("[", ".").replace("]", "")
    parts = tuple(part for part in cleaned.split(".") if part)
    if not parts:
        return "", ()
    root = artifact_plan_canonical_root(parts[0])
    return root, tuple(part for part in parts[1:] if not part.isdigit())


def _tail_without_row_index(path: Sequence[str]) -> str:
    return ".".join(part for part in path if not part.isdigit())


def _row_index_from_path(path: str) -> int | None:
    marker = "["
    if marker not in path:
        return None
    tail = path.split(marker, 1)[1].split("]", 1)[0]
    return _int_or_none(tail)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ledger_entry(operation: Mapping[str, Any], *, applied_paths: Sequence[str]) -> dict[str, Any]:
    entry = operation.get("decision_ledger_entry")
    base = dict(entry) if isinstance(entry, Mapping) else {}
    base.update(
        {
            "applied_paths": tuple(applied_paths),
            "operation_id": normalize_string(operation.get("operation_id")),
            "target_path": normalize_string(operation.get("target_path")),
            "semantic_node_id": normalize_string(operation.get("semantic_node_id")),
            "issue_code": normalize_token(operation.get("issue_code")),
            "rejected_interpretation": normalize_string(operation.get("rejected_interpretation")),
            "confidence": _confidence(operation.get("confidence")),
        }
    )
    return {key: value for key, value in base.items() if value not in ("", (), [], None)}


def _confidence(value: Any) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0


__all__ = ["apply_artifact_plan_patch_operations"]
