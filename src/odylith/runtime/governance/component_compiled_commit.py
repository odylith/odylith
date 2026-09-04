"""Commit already compiled Registry components without semantic interpretation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.governance import owned_surface_refresh


_REGISTRY_PATH_RELATIVE = Path("odylith/registry/source/component_registry.v1.json")


@dataclass(frozen=True)
class CreatedComponent:
    component_id: str
    label: str
    path: str
    registry_path: Path
    spec_path: Path
    tribunal: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "component_id": self.component_id,
            "label": self.label,
            "path": self.path,
            "registry_path": str(self.registry_path),
            "spec_path": str(self.spec_path),
        }
        if self.tribunal is not None:
            payload["validation_gate"] = self.tribunal
        return payload


def _load_registry(registry_path: Path) -> dict[str, Any]:
    if not registry_path.is_file():
        return {"version": "v1", "components": []}
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": "v1", "components": []}
    if not isinstance(data, dict):
        return {"version": "v1", "components": []}
    return data


def _component_index(registry: dict[str, Any], component_id: str) -> int | None:
    components = registry.get("components", [])
    if not isinstance(components, list):
        return None
    for index, entry in enumerate(components):
        if isinstance(entry, dict) and str(entry.get("component_id", "")).strip() == component_id:
            return index
    return None


def materialize_compiled_component(
    *,
    repo_root: Path,
    registry_entry: Mapping[str, Any],
    spec_text: str,
    validation_gate: Mapping[str, Any] | None = None,
    update_existing: bool = True,
    refresh: bool = True,
) -> CreatedComponent:
    """Commit an already compiled Registry entry and spec without rendering them again."""

    registry_path = (repo_root / _REGISTRY_PATH_RELATIVE).resolve()
    entry = _compiled_registry_entry(registry_entry)
    component_id = str(entry.get("component_id", "")).strip()
    label = str(entry.get("name", "")).strip()
    if not component_id or not label:
        raise ValueError("compiled component registry entry must include component_id and name")
    expected_spec_ref = f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md"
    spec_ref = str(entry.get("spec_ref", "")).strip()
    if spec_ref != expected_spec_ref:
        raise ValueError(
            f"compiled component registry entry spec_ref must be {expected_spec_ref}, got {spec_ref or '<empty>'}"
        )
    rendered_spec = str(spec_text or "").rstrip()
    if not rendered_spec:
        raise ValueError(f"compiled component spec is empty for {component_id}")

    registry = _load_registry(registry_path)
    existing_index = _component_index(registry, component_id)
    if existing_index is not None and not update_existing:
        raise ValueError(f"Component `{component_id}` already exists in the registry")
    components = registry.get("components", [])
    if not isinstance(components, list):
        components = []
    if existing_index is None:
        components.append(entry)
    else:
        components[existing_index] = entry
    registry["components"] = components

    spec_path = (repo_root / spec_ref).resolve()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(f"{rendered_spec}\n", encoding="utf-8")
    if refresh:
        owned_surface_refresh.raise_for_failed_refresh(
            repo_root=repo_root,
            surface="registry",
            operation_label="Compiled component register",
        )
    path_prefixes = entry.get("path_prefixes")
    path = ""
    if isinstance(path_prefixes, list) and path_prefixes:
        path = str(path_prefixes[0]).strip()
    return CreatedComponent(
        component_id=component_id,
        label=label,
        path=path,
        registry_path=registry_path,
        spec_path=spec_path,
        tribunal=dict(validation_gate or {}),
    )


def _compiled_registry_entry(registry_entry: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "component_id",
        "name",
        "kind",
        "category",
        "qualification",
        "aliases",
        "path_prefixes",
        "workstreams",
        "diagrams",
        "owner",
        "status",
        "what_it_is",
        "why_tracked",
        "spec_ref",
        "sources",
        "subcomponents",
        "product_layer",
    }
    entry = {key: _json_ready(value) for key, value in registry_entry.items() if str(key) in allowed}
    for key in ("aliases", "path_prefixes", "workstreams", "diagrams", "sources", "subcomponents"):
        value = entry.get(key)
        entry[key] = [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
    return entry


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


__all__ = ["CreatedComponent", "materialize_compiled_component"]
