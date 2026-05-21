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
from typing import Any, Mapping, Sequence

from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.governance import artifact_tribunal
from odylith.runtime.governance import component_spec_rendering
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


def _component_exists(registry: dict[str, Any], component_id: str) -> bool:
    return _component_index(registry, component_id) is not None


def _component_index(registry: dict[str, Any], component_id: str) -> int | None:
    components = registry.get("components", [])
    if not isinstance(components, list):
        return None
    for index, entry in enumerate(components):
        if isinstance(entry, dict) and str(entry.get("component_id", "")).strip() == component_id:
            return index
    return None


def _clean_sequence(values: Sequence[str] | str) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values.strip(),) if values.strip() else ()
    return tuple(str(item).strip() for item in values if str(item).strip())


def _responsibility_clause(value: str) -> str:
    text = component_spec_rendering.sentence_fragment(value)
    if not text:
        return ""
    clauses = [
        _finite_responsibility_clause(part)
        for part in re.split(r"\s*;\s*", text)
        if part.strip()
    ]
    clauses = [clause for clause in clauses if clause]
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return f"{', '.join(clauses[:-1])}, and {clauses[-1]}"


def _finite_responsibility_clause(value: str) -> str:
    text = component_spec_rendering.sentence_fragment(value)
    if not text:
        return ""
    return finite_action_clause(text, default_verb="owns", default_single_token=False)


def _kind_article(kind: str) -> str:
    token = str(kind or "").strip().lower()
    return "an" if token[:1] in {"a", "e", "i", "o", "u"} else "a"


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
    normalized_sources = [str(item).strip() for item in sources if str(item).strip()]
    evidence_phrase = (
        "user-stated intent"
        if "user_intent" in normalized_sources
        else "the initial source boundary"
    )
    responsibility_text = _responsibility_clause(responsibility)
    article = _kind_article(kind)
    what_it_is = (
        f"{label} is planned as {article} {kind} boundary. It {responsibility_text}."
        if responsibility_text
        else f"{label} is planned as {article} {kind} boundary awaiting a concrete responsibility summary."
    )
    if path:
        what_it_is += f" Initial source boundary: {path}."
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
            f"Tracked from {evidence_phrase} as a named ownership boundary so implementation and review can see "
            "what it owns, what it depends on, which interfaces it exposes, and which proof promotes it."
        ),
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": normalized_sources or ["manifest"],
        "subcomponents": [],
        "product_layer": product_layer,
    }


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
    implementation_handoff: Mapping[str, Any] | None = None,
    component_contract: Mapping[str, Any] | None = None,
    dry_run: bool = False,
    refresh: bool = True,
    update_existing: bool = False,
) -> CreatedComponent:
    """Register a new component in the registry and scaffold its spec."""
    registry_path = (repo_root / _REGISTRY_PATH_RELATIVE).resolve()
    components_root = (repo_root / _COMPONENTS_ROOT_RELATIVE).resolve()

    registry = _load_registry(registry_path)
    existing_index = _component_index(registry, component_id)
    if existing_index is not None and not update_existing:
        raise ValueError(f"Component `{component_id}` already exists in the registry")
    sources = _clean_sequence(sources) or ("manifest",)
    workstreams = _clean_sequence(workstreams)
    diagrams = _clean_sequence(diagrams)
    dependencies = _clean_sequence(dependencies)
    interfaces = _clean_sequence(interfaces)
    validation = _clean_sequence(validation)
    risks = _clean_sequence(risks)

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
        sources=sources,
        workstreams=workstreams,
        diagrams=diagrams,
        responsibility=str(responsibility).strip(),
    )

    components = registry.get("components", [])
    if not isinstance(components, list):
        components = []
    if existing_index is None:
        components.append(entry)
    else:
        components[existing_index] = entry
    registry["components"] = components

    spec_dir = components_root / component_id
    spec_path = spec_dir / "CURRENT_SPEC.md"
    spec_text = component_spec_rendering.build_component_spec(
        component_id=component_id,
        label=label,
        path=path,
        kind=kind,
        status=str(status).strip() or "active",
        qualification=str(qualification).strip() or "candidate",
        sources=sources,
        workstreams=workstreams,
        diagrams=diagrams,
        responsibility=str(responsibility).strip(),
        boundary=str(boundary).strip(),
        dependencies=dependencies,
        interfaces=interfaces,
        validation=validation,
        risks=risks,
        implementation_handoff=implementation_handoff,
        component_contract=component_contract,
    )
    tribunal = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="component",
        payload={
            "component_id": component_id,
            "label": label,
            "path": path,
            "kind": kind,
            "responsibility": responsibility,
            "boundary": boundary,
            "interfaces": interfaces,
            "dependencies": dependencies,
            "validation": validation,
            "risks": risks,
            "implementation_handoff": dict(implementation_handoff or {}),
            "component_contract": dict(component_contract or {}),
        },
    )
    artifact_tribunal.raise_for_failed_artifact_tribunal(tribunal)

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
        tribunal=tribunal.to_dict(),
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
    parser.add_argument("--responsibility", required=True, help="Concrete responsibility and ownership summary.")
    parser.add_argument("--boundary", required=True, help="Runtime, data, or governance boundary this component owns.")
    parser.add_argument("--dependency", action="append", default=[], required=True, help="Dependency expectation; repeatable.")
    parser.add_argument("--interface", action="append", default=[], required=True, dest="interfaces", help="Interface contract; repeatable.")
    parser.add_argument("--validation", action="append", default=[], required=True, help="Proof expectation; repeatable.")
    parser.add_argument("--risk", action="append", default=[], required=True, dest="risks", help="Domain/security/compliance risk posture; repeatable.")
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
            responsibility=str(args.responsibility).strip(),
            boundary=str(args.boundary).strip(),
            dependencies=tuple(args.dependency),
            interfaces=tuple(args.interfaces),
            validation=tuple(args.validation),
            risks=tuple(args.risks),
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
        print(f"  validation gate: {(result.tribunal or {}).get('status', 'unknown')}")
        print(f"  registry: {result.registry_path}")
        print(f"  spec: {result.spec_path}")
        owned_surface_refresh.print_dashboard_handoff(
            surface="registry",
            component=result.component_id,
            dry_run=bool(args.dry_run),
        )
    return 0
