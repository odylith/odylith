"""Component Registry commit helpers for confirmed greenfield writes."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.governance import component_authoring


def precompiled_component_handoffs(
    prewrite_package: GreenfieldCompletionPackage | None,
) -> dict[str, dict[str, Any]]:
    if prewrite_package is None:
        return {}
    handoffs: dict[str, dict[str, Any]] = {}
    for row in prewrite_package.component_registry_preview:
        if not isinstance(row, Mapping):
            continue
        handoff = row.get("implementation_handoff")
        if not isinstance(handoff, Mapping) or not handoff:
            continue
        key = greenfield_traceability.component_key(row)
        if key:
            handoffs[key] = dict(handoff)
    return handoffs


def precompiled_component_previews(
    prewrite_package: GreenfieldCompletionPackage | None,
) -> dict[str, dict[str, Any]]:
    if prewrite_package is None:
        return {}
    previews: dict[str, dict[str, Any]] = {}
    for row in prewrite_package.component_registry_preview:
        if not isinstance(row, Mapping):
            continue
        authoring_input = row.get("authoring_input") if isinstance(row.get("authoring_input"), Mapping) else row
        key = greenfield_traceability.component_key(authoring_input)
        if key:
            previews[key] = dict(row)
    return previews


def compiled_component_previews_for_rows(
    prewrite_package: GreenfieldCompletionPackage | None,
    component_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    component_keys = {greenfield_traceability.component_key(row) for row in component_rows if isinstance(row, Mapping)}
    return {
        key: preview
        for key, preview in precompiled_component_previews(prewrite_package).items()
        if key in component_keys
    }


def precompiled_component_authoring_inputs(
    prewrite_package: GreenfieldCompletionPackage | None,
) -> dict[str, dict[str, Any]]:
    if prewrite_package is None:
        return {}
    inputs: dict[str, dict[str, Any]] = {}
    for row in prewrite_package.component_registry_preview:
        if not isinstance(row, Mapping):
            continue
        authoring_input = row.get("authoring_input")
        if not isinstance(authoring_input, Mapping) or not authoring_input:
            continue
        key = greenfield_traceability.component_key(authoring_input)
        if key:
            inputs[key] = dict(authoring_input)
    return inputs


def compiled_component_registry_entry_issues(*, key: str, preview: Mapping[str, Any]) -> list[str]:
    authoring_input = preview.get("authoring_input")
    registry_entry = preview.get("registry_entry")
    if not isinstance(authoring_input, Mapping) or not authoring_input:
        return [f"{key}: missing compiled component authoring input"]
    if not isinstance(registry_entry, Mapping) or not registry_entry:
        return [f"{key}: missing compiled component registry_entry"]
    component_id = str(authoring_input.get("component_id", "")).strip()
    label = str(authoring_input.get("label", "")).strip()
    path = str(authoring_input.get("path", "")).strip()
    issues: list[str] = []
    expected_scalars = {
        "component_id": component_id,
        "name": label,
        "kind": str(authoring_input.get("kind", "service")).strip() or "service",
        "category": str(authoring_input.get("category", "application")).strip() or "application",
        "qualification": str(authoring_input.get("qualification", "candidate")).strip() or "candidate",
        "owner": str(authoring_input.get("owner", "repo")).strip() or "repo",
        "status": str(authoring_input.get("status", "planned")).strip() or "planned",
        "product_layer": str(authoring_input.get("product_layer", "application")).strip() or "application",
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
    }
    for field, expected in expected_scalars.items():
        if str(registry_entry.get(field, "")).strip() != expected:
            issues.append(f"{key}: compiled component registry_entry {field} does not match authoring_input")
    expected_sequences = {
        "path_prefixes": (path,) if path else (),
        "workstreams": string_tuple(authoring_input.get("workstreams")),
        "diagrams": string_tuple(authoring_input.get("diagrams")),
        "sources": string_tuple(authoring_input.get("sources")) or ("user_intent",),
    }
    for field, expected in expected_sequences.items():
        if string_tuple(registry_entry.get(field)) != expected:
            issues.append(f"{key}: compiled component registry_entry {field} does not match authoring_input")
    for field in ("what_it_is", "why_tracked"):
        if not str(registry_entry.get(field, "")).strip():
            issues.append(f"{key}: compiled component registry_entry missing {field}")
    return issues


def register_component_from_authoring_input(
    *,
    root: Path,
    authoring_input: Mapping[str, Any],
) -> Any:
    return component_authoring.register_component(
        repo_root=root,
        component_id=str(authoring_input.get("component_id", "")).strip(),
        label=str(authoring_input.get("label", "")).strip(),
        path=str(authoring_input.get("path", "")).strip(),
        kind=str(authoring_input.get("kind", "service")).strip() or "service",
        category=str(authoring_input.get("category", "application")).strip() or "application",
        qualification=str(authoring_input.get("qualification", "candidate")).strip() or "candidate",
        owner=str(authoring_input.get("owner", "repo")).strip() or "repo",
        status=str(authoring_input.get("status", "planned")).strip() or "planned",
        product_layer=str(authoring_input.get("product_layer", "application")).strip() or "application",
        sources=string_tuple(authoring_input.get("sources")) or ("user_intent",),
        workstreams=string_tuple(authoring_input.get("workstreams")),
        diagrams=string_tuple(authoring_input.get("diagrams")),
        responsibility=str(authoring_input.get("responsibility", "")).strip(),
        boundary=str(authoring_input.get("boundary", "")).strip(),
        dependencies=string_tuple(authoring_input.get("dependencies")),
        interfaces=string_tuple(authoring_input.get("interfaces")),
        validation=string_tuple(authoring_input.get("validation")),
        risks=string_tuple(authoring_input.get("risks")),
        implementation_handoff=authoring_input.get("implementation_handoff")
        if isinstance(authoring_input.get("implementation_handoff"), Mapping)
        else None,
        component_contract=authoring_input.get("component_contract")
        if isinstance(authoring_input.get("component_contract"), Mapping)
        else None,
        dry_run=False,
        update_existing=True,
        refresh=False,
    )


def materialize_compiled_component_from_preview(
    *,
    root: Path,
    preview: Mapping[str, Any],
    rendered_component_specs: Mapping[str, str],
) -> Any:
    authoring_input = preview.get("authoring_input")
    registry_entry = preview.get("registry_entry")
    if not isinstance(authoring_input, Mapping) or not isinstance(registry_entry, Mapping):
        raise ValueError("compiled component preview must include authoring_input and registry_entry")
    label = str(authoring_input.get("label", "") or preview.get("label", "")).strip()
    rendered = str(rendered_component_specs.get(label, "")).rstrip()
    if not rendered:
        component_id = str(authoring_input.get("component_id", "")).strip() or label or "<unknown component>"
        raise ValueError(f"compiled component spec missing for {component_id}")
    validation_gate = preview.get("validation_gate") if isinstance(preview.get("validation_gate"), Mapping) else None
    return component_authoring.materialize_compiled_component(
        repo_root=root,
        registry_entry=registry_entry,
        spec_text=rendered,
        validation_gate=validation_gate,
        update_existing=True,
        refresh=False,
    )


def raise_for_compiled_component_registry_readback(
    *,
    root: Path,
    previews: Mapping[str, Mapping[str, Any]],
    rendered_component_specs: Mapping[str, str],
) -> None:
    registry = _read_json_mapping(root / "odylith/registry/source/component_registry.v1.json")
    rows = registry.get("components") if isinstance(registry.get("components"), list) else []
    by_id = {
        str(row.get("component_id", "")).strip(): row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("component_id", "")).strip()
    }
    issues: list[str] = []
    for key, preview in previews.items():
        authoring_input = preview.get("authoring_input")
        registry_entry = preview.get("registry_entry")
        if not isinstance(authoring_input, Mapping) or not isinstance(registry_entry, Mapping):
            issues.append(f"{key}: compiled component preview missing authoring_input or registry_entry")
            continue
        component_id = str(authoring_input.get("component_id", "")).strip()
        label = str(authoring_input.get("label", "")).strip()
        expected_entry = json_ready_mapping(registry_entry)
        if by_id.get(component_id) != expected_entry:
            issues.append(f"{key}: committed Registry entry does not match compiled transaction entry")
        spec_ref = str(expected_entry.get("spec_ref", "")).strip()
        expected_spec = str(rendered_component_specs.get(label, "")).rstrip()
        spec_path = root / spec_ref
        if not expected_spec:
            issues.append(f"{key}: compiled component spec missing for readback")
        elif not spec_path.is_file():
            issues.append(f"{key}: committed component spec missing at {spec_ref}")
        elif spec_path.read_text(encoding="utf-8") != f"{expected_spec}\n":
            issues.append(f"{key}: committed component spec does not match compiled transaction spec")
    if issues:
        detail = "\n".join(f"- {issue}" for issue in dedupe_strings(issues))
        raise ValueError(f"greenfield commit-only Registry readback failed with {len(issues)} issue(s):\n{detail}")


def write_repaired_component_spec(
    *,
    root: Path,
    created: Mapping[str, Any],
    rendered_component_specs: Mapping[str, str],
) -> None:
    label = str(created.get("label", "")).strip()
    rendered = str(rendered_component_specs.get(label, "")).rstrip()
    if not rendered:
        return
    spec_path = Path(str(created.get("spec_path", "")))
    if not spec_path.is_absolute():
        spec_path = root / spec_path
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(f"{rendered}\n", encoding="utf-8")


def string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = ()
    return tuple(str(item).strip() for item in values if str(item).strip())


def json_ready_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, nested in value.items():
        if isinstance(nested, Mapping):
            result[str(key)] = json_ready_mapping(nested)
        elif isinstance(nested, (list, tuple, set)):
            result[str(key)] = [
                json_ready_mapping(item) if isinstance(item, Mapping) else str(item) if isinstance(item, Path) else item
                for item in nested
            ]
        elif isinstance(nested, Path):
            result[str(key)] = str(nested)
        else:
            result[str(key)] = nested
    return result


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


__all__ = [
    "compiled_component_previews_for_rows",
    "compiled_component_registry_entry_issues",
    "json_ready_mapping",
    "legacy_component_authoring_input",
    "materialize_compiled_component_from_preview",
    "precompiled_component_authoring_inputs",
    "precompiled_component_handoffs",
    "precompiled_component_previews",
    "raise_for_compiled_component_registry_readback",
    "register_component_from_authoring_input",
    "string_tuple",
    "write_repaired_component_spec",
]
