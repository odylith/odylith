"""CLI backend for `odylith component register` — create a component entry and scaffold its spec.

Creates an entry in `component_registry.v1.json` and a starter `CURRENT_SPEC.md`
under `components/<id>/`.
"""

from __future__ import annotations

import argparse
import datetime as dt
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


def _sentence_fragment(value: str) -> str:
    text = " ".join(str(value or "").strip().split()).rstrip(".")
    return text


def _bullet_lines(values: Sequence[str]) -> str:
    lines = [str(item).strip().rstrip(".") for item in values if str(item).strip()]
    return "\n".join(f"- {line}." for line in lines)


def _build_registry_entry(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    category: str,
    qualification: str,
    owner: str,
    status: str,
    product_layer: str,
    sources: Sequence[str],
    workstreams: Sequence[str],
    diagrams: Sequence[str],
    responsibility: str = "",
) -> dict[str, Any]:
    anchor_phrase = f" with `{path}` as its initial evidence anchor" if path else ""
    normalized_sources = [str(item).strip() for item in sources if str(item).strip()]
    evidence_phrase = (
        "user-stated intent"
        if "user_intent" in normalized_sources
        else "the initial evidence anchor"
    )
    responsibility_text = _sentence_fragment(responsibility)
    what_it_is = (
        f"{label} is a `{kind}` component responsible for {responsibility_text}{anchor_phrase}."
        if responsibility_text
        else f"Logical component registered through `odylith component register`{anchor_phrase}."
    )
    return {
        "component_id": component_id,
        "name": label,
        "kind": kind,
        "category": category,
        "qualification": qualification,
        "aliases": [],
        "path_prefixes": [path] if path else [],
        "workstreams": [str(item).strip() for item in workstreams if str(item).strip()],
        "diagrams": [str(item).strip() for item in diagrams if str(item).strip()],
        "owner": owner,
        "status": status,
        "what_it_is": what_it_is,
        "why_tracked": (
            f"Registered so agent sessions can see {label} as a named ownership boundary from {evidence_phrase}; "
            "path prefixes seed the intended boundary and can be tightened as the contract becomes clearer."
        ),
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": normalized_sources or ["manifest"],
        "subcomponents": [],
        "product_layer": product_layer,
    }


def _build_spec_template(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    status: str,
    sources: Sequence[str],
    workstreams: Sequence[str],
    diagrams: Sequence[str] = (),
    responsibility: str = "",
    boundary: str = "",
    dependencies: Sequence[str] = (),
    interfaces: Sequence[str] = (),
    validation: Sequence[str] = (),
    risks: Sequence[str] = (),
) -> str:
    normalized_sources = [str(item).strip() for item in sources if str(item).strip()]
    if "user_intent" in normalized_sources:
        overview_anchor = (
            f"It is planned from user-stated intent with `{path}` as the intended first source path. "
            "No source-backed claim is made yet."
            if path
            else "It is planned from user-stated intent and does not claim source evidence yet."
        )
    else:
        overview_anchor = (
            f"It is initially anchored by `{path}`."
            if path
            else "It is initially anchored by maintainer review."
        )
    history_date = dt.date.today().isoformat()
    workstream_ids = [str(item).strip().upper() for item in workstreams if str(item).strip()]
    first_workstream = workstream_ids[0] if workstream_ids else ""
    plan_route = (
        f" (Plan: [{first_workstream}](odylith/radar/radar.html?view=plan&workstream={first_workstream}))"
        if first_workstream
        else ""
    )
    diagram_ids = [str(item).strip().upper() for item in diagrams if str(item).strip()]
    responsibility_text = _sentence_fragment(responsibility)
    boundary_text = _sentence_fragment(boundary) or responsibility_text
    interface_lines = _bullet_lines(interfaces) or "- Candidate interfaces are not source-backed yet; the first technical plan must define runtime contracts."
    dependency_lines = _bullet_lines(dependencies) or "- No upstream or downstream runtime dependency is source-backed yet."
    validation_lines = _bullet_lines(validation) or "- First implementation must add focused contract or smoke proof before this candidate becomes active."
    risk_lines = _bullet_lines(risks) or "- Candidate boundary may change once source evidence and implementation plans exist."
    related_workstreams = ", ".join(workstream_ids) if workstream_ids else "none"
    related_diagrams = ", ".join(diagram_ids) if diagram_ids else "none"
    return f"""# {label}

## Overview

{label} is a `{kind}` component registered through `odylith component register`.
{overview_anchor}
{f"Planned responsibility: {responsibility_text}." if responsibility_text else ""}

## Boundary

- **Logical boundary**: {boundary_text or "TBD - define the runtime contract, public API, or ownership rule."}
- **Evidence anchor**: `{path}`
- **Kind**: {kind}
- **Status**: {status}
- **Evidence tier**: {", ".join(normalized_sources) if normalized_sources else "manifest"}
- **Related workstreams**: {related_workstreams}
- **Related diagrams**: {related_diagrams}

## Feature History

- {history_date}: Registered `{component_id}` through `odylith component register`.{plan_route}

## Contract

{responsibility_text or "TBD - define the runtime contract, public API, or ownership boundary for this component."}

### Candidate Interfaces

{interface_lines}

## Dependencies

{dependency_lines}

## Test Coverage

{validation_lines}

## Risks And Open Questions

{risk_lines}
"""


def register_component(
    *,
    repo_root: Path,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    category: str = "governance_engine",
    qualification: str = "candidate",
    owner: str = "product",
    status: str = "active",
    product_layer: str = "cli_bootstrap",
    sources: Sequence[str] = ("manifest",),
    workstreams: Sequence[str] = (),
    diagrams: Sequence[str] = (),
    responsibility: str = "",
    boundary: str = "",
    dependencies: Sequence[str] = (),
    interfaces: Sequence[str] = (),
    validation: Sequence[str] = (),
    risks: Sequence[str] = (),
    dry_run: bool = False,
    refresh: bool = True,
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
        category=str(category).strip() or "governance_engine",
        qualification=str(qualification).strip() or "candidate",
        owner=str(owner).strip() or "product",
        status=str(status).strip() or "active",
        product_layer=str(product_layer).strip() or "cli_bootstrap",
        sources=tuple(str(item).strip() for item in sources if str(item).strip()) or ("manifest",),
        workstreams=tuple(str(item).strip() for item in workstreams if str(item).strip()),
        diagrams=tuple(str(item).strip() for item in diagrams if str(item).strip()),
        responsibility=str(responsibility).strip(),
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
        status=str(status).strip() or "active",
        sources=tuple(str(item).strip() for item in sources if str(item).strip()) or ("manifest",),
        workstreams=tuple(str(item).strip() for item in workstreams if str(item).strip()),
        diagrams=tuple(str(item).strip() for item in diagrams if str(item).strip()),
        responsibility=str(responsibility).strip(),
        boundary=str(boundary).strip(),
        dependencies=tuple(str(item).strip() for item in dependencies if str(item).strip()),
        interfaces=tuple(str(item).strip() for item in interfaces if str(item).strip()),
        validation=tuple(str(item).strip() for item in validation if str(item).strip()),
        risks=tuple(str(item).strip() for item in risks if str(item).strip()),
    )

    if not dry_run:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(spec_text, encoding="utf-8")
        if refresh:
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
    parser.add_argument("--category", default="governance_engine", help="Component category.")
    parser.add_argument("--qualification", default="candidate", help="Component qualification token.")
    parser.add_argument("--owner", default="product", help="Declared component owner.")
    parser.add_argument("--status", default="active", help="Component lifecycle status.")
    parser.add_argument("--product-layer", default="cli_bootstrap", help="Product or application layer token.")
    parser.add_argument("--source", action="append", default=[], dest="sources", help="Evidence source token; repeatable.")
    parser.add_argument("--workstream", action="append", default=[], help="Related workstream id; repeatable.")
    parser.add_argument("--diagram", action="append", default=[], help="Related diagram id; repeatable.")
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
            category=str(args.category).strip(),
            qualification=str(args.qualification).strip(),
            owner=str(args.owner).strip(),
            status=str(args.status).strip(),
            product_layer=str(args.product_layer).strip(),
            sources=tuple(args.sources) if args.sources else ("manifest",),
            workstreams=tuple(args.workstream),
            diagrams=tuple(args.diagram),
            dry_run=bool(args.dry_run),
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 2 if isinstance(exc, ValueError) else 1

    mode = "dry-run" if args.dry_run else "registered"
    if args.as_json:
        print(
            json.dumps(
                {
                    "mode": mode,
                    **result.as_dict(),
                    "dashboard": ""
                    if args.dry_run
                    else owned_surface_refresh.dashboard_handoff(
                        surface="registry",
                        component=result.component_id,
                    ),
                },
                indent=2,
            )
        )
    else:
        print(f"odylith component register {mode}")
        print(f"  component_id: {result.component_id}")
        print(f"  label: {result.label}")
        print(f"  path: {result.path}")
        print(f"  registry: {result.registry_path}")
        print(f"  spec: {result.spec_path}")
        owned_surface_refresh.print_dashboard_handoff(
            surface="registry",
            component=result.component_id,
            dry_run=bool(args.dry_run),
        )
    return 0
