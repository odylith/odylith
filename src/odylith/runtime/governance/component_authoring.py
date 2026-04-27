"""CLI backend for `odylith component register` — create a component entry and scaffold its spec.

Creates an entry in `component_registry.v1.json` and a starter `CURRENT_SPEC.md`
under `components/<id>/`.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from odylith.runtime.governance import owned_surface_refresh

_REGISTRY_PATH_RELATIVE = Path("odylith/registry/source/component_registry.v1.json")
_COMPONENTS_ROOT_RELATIVE = Path("odylith/registry/source/components")
_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    return _SLUGIFY_RE.sub("-", str(value or "").strip().lower()).strip("-") or "component"


@dataclass(frozen=True)
class CreatedComponent:
    component_id: str
    label: str
    path: str
    registry_path: Path
    spec_path: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "label": self.label,
            "path": self.path,
            "registry_path": str(self.registry_path),
            "spec_path": str(self.spec_path),
        }


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


def _component_exists(registry: dict[str, Any], component_id: str) -> bool:
    components = registry.get("components", [])
    if not isinstance(components, list):
        return False
    return any(
        isinstance(entry, dict) and str(entry.get("component_id", "")).strip() == component_id
        for entry in components
    )


def _build_registry_entry(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
) -> dict[str, Any]:
    anchor_phrase = f" with `{path}` as its initial evidence anchor" if path else ""
    return {
        "component_id": component_id,
        "name": label,
        "kind": kind,
        "category": "detected",
        "qualification": "detected",
        "aliases": [],
        "path_prefixes": [path] if path else [],
        "workstreams": [],
        "diagrams": [],
        "owner": "product",
        "status": "active",
        "what_it_is": (
            f"Logical component registered through `odylith component register`"
            f"{anchor_phrase}."
        ),
        "why_tracked": (
            f"Registered so agent sessions can see {label} as a named ownership boundary; "
            "path prefixes seed evidence and can be tightened as the contract becomes clearer."
        ),
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": ["detected"],
        "subcomponents": [],
    }


def _build_spec_template(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
) -> str:
    overview_anchor = (
        f"It is initially anchored by `{path}`."
        if path
        else "It is initially anchored by maintainer review."
    )
    return f"""# {label}

## Overview

{label} is a `{kind}` component registered through `odylith component register`.
{overview_anchor}

## Boundary

- **Logical boundary**: TBD - define the runtime contract, public API, or ownership rule.
- **Evidence anchor**: `{path}`
- **Kind**: {kind}
- **Status**: active

## Contract

TBD - define the runtime contract, public API, or ownership boundary for this component.

## Dependencies

TBD — list upstream and downstream dependencies.

## Test Coverage

TBD — describe how this component is tested.
"""


def register_component(
    *,
    repo_root: Path,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    dry_run: bool = False,
) -> CreatedComponent:
    """Register a new component in the registry and scaffold its spec."""
    registry_path = (repo_root / _REGISTRY_PATH_RELATIVE).resolve()
    components_root = (repo_root / _COMPONENTS_ROOT_RELATIVE).resolve()

    registry = _load_registry(registry_path)
    if _component_exists(registry, component_id):
        raise ValueError(f"Component `{component_id}` already exists in the registry")

    entry = _build_registry_entry(
        component_id=component_id,
        label=label,
        path=path,
        kind=kind,
    )

    components = registry.get("components", [])
    if not isinstance(components, list):
        components = []
    components.append(entry)
    registry["components"] = components

    spec_dir = components_root / component_id
    spec_path = spec_dir / "CURRENT_SPEC.md"
    spec_text = _build_spec_template(
        component_id=component_id,
        label=label,
        path=path,
        kind=kind,
    )

    if not dry_run:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(spec_text, encoding="utf-8")
        owned_surface_refresh.raise_for_failed_refresh(
            repo_root=repo_root,
            surface="registry",
            operation_label="Component register",
        )

    return CreatedComponent(
        component_id=component_id,
        label=label,
        path=path,
        registry_path=registry_path,
        spec_path=spec_path,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith component register",
        description="Register a new component in the Odylith registry and scaffold its CURRENT_SPEC.md.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--id", required=True, dest="component_id", help="Component ID (kebab-case slug).")
    parser.add_argument("--path", default="", help="Primary code path this component owns.")
    parser.add_argument("--label", default="", help="Human-readable component name.")
    parser.add_argument("--kind", default="service", help="Component kind (service, library, platform, etc.).")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).expanduser().resolve()

    component_id = _slugify(args.component_id)
    label = str(args.label or "").strip() or component_id.replace("-", " ").title()
    path = str(args.path or "").strip()

    try:
        result = register_component(
            repo_root=repo_root,
            component_id=component_id,
            label=label,
            path=path,
            kind=str(args.kind).strip(),
            dry_run=bool(args.dry_run),
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 2 if isinstance(exc, ValueError) else 1

    mode = "dry-run" if args.dry_run else "registered"
    if args.as_json:
        print(json.dumps({"mode": mode, **result.as_dict()}, indent=2))
    else:
        print(f"odylith component register {mode}")
        print(f"  component_id: {result.component_id}")
        print(f"  label: {result.label}")
        print(f"  path: {result.path}")
        print(f"  registry: {result.registry_path}")
        print(f"  spec: {result.spec_path}")
    return 0
