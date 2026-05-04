"""Shared topology-spine construction helpers for traceability graph builds."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import Any
import re

from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import execution_wave_contract


Edge = tuple[str, str, str]

_IDEA_ID_RE = re.compile(r"^B-\d{3,}$")


def _string_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def build_component_context(
    *,
    repo_root: Path,
    manifest_path: Path,
    catalog_path: Path,
    ideas_root: Path,
) -> tuple[
    dict[str, component_registry.ComponentEntry],
    dict[str, list[str]],
    list[str],
]:
    """Return Registry components plus workstream lookup for graph assembly."""

    components_by_id, _component_aliases, component_warnings = component_registry.build_component_index(
        repo_root=repo_root,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        ideas_root=ideas_root,
    )
    components_by_workstream: dict[str, list[str]] = {}
    for component_id, entry in sorted(components_by_id.items()):
        for workstream_id in entry.workstreams:
            candidate = str(workstream_id or "").strip()
            if _IDEA_ID_RE.fullmatch(candidate):
                components_by_workstream.setdefault(candidate, []).append(component_id)
    return components_by_id, components_by_workstream, [str(entry) for entry in component_warnings]


def diagram_node_payloads(diagrams_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build diagram nodes while keeping catalog component labels non-promoting."""

    nodes: list[dict[str, Any]] = []
    for diagram_id, diagram in sorted(diagrams_by_id.items()):
        nodes.append(
            {
                "id": f"diagram:{diagram_id}",
                "type": "diagram",
                "label": diagram.get("title") or diagram_id,
                "diagram_id": diagram_id,
                "status": diagram.get("status", "active"),
                "owner": diagram.get("owner", ""),
                "file": diagram.get("file", ""),
                "related_workstreams": list(diagram.get("related_workstreams", [])),
                "component_names": list(diagram.get("component_names", [])),
                "related_component_ids": list(diagram.get("related_component_ids", [])),
            }
        )
    return nodes


def release_catalog_node_payloads(release_catalog: Sequence[Any]) -> list[dict[str, Any]]:
    """Build release nodes from the release-planning catalog."""

    nodes: list[dict[str, Any]] = []
    for raw_release in release_catalog:
        if not isinstance(raw_release, Mapping):
            continue
        release_id = str(raw_release.get("release_id", "")).strip()
        if not release_id:
            continue
        nodes.append(release_node_payload(release_id=release_id, release=raw_release))
    return nodes


def release_node_payload(*, release_id: str, release: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical graph payload for one release node."""

    aliases = _string_values(release.get("aliases"))
    return {
        "id": f"release:{release_id}",
        "type": "release",
        "label": str(release.get("display_label", "")).strip()
        or str(release.get("effective_name", "")).strip()
        or release_id,
        "release_id": release_id,
        "status": str(release.get("status", "")).strip(),
        "version": str(release.get("version", "")).strip(),
        "tag": str(release.get("tag", "")).strip(),
        "name": str(release.get("effective_name", "")).strip(),
        "aliases": aliases,
        "file": "odylith/radar/source/releases/releases.v1.json",
    }


def component_node_payloads(
    components_by_id: Mapping[str, component_registry.ComponentEntry],
) -> list[dict[str, Any]]:
    """Build Registry component nodes."""

    nodes: list[dict[str, Any]] = []
    for component_id, entry in sorted(components_by_id.items()):
        nodes.append(
            {
                "id": f"component:{component_id}",
                "type": "component",
                "label": entry.name or component_id,
                "component_id": component_id,
                "kind": entry.kind,
                "category": entry.category,
                "qualification": entry.qualification,
                "aliases": list(entry.aliases),
                "status": entry.status,
                "owner": entry.owner,
                "file": entry.spec_ref,
                "workstreams": list(entry.workstreams),
                "diagrams": list(entry.diagrams),
                "sources": list(entry.sources),
            }
        )
    return nodes


def workstream_component_edges(
    *, idea_id: str, components_by_workstream: Mapping[str, Sequence[str]]
) -> set[Edge]:
    """Return explicit workstream-to-component topology edges."""

    return {
        (idea_id, f"component:{component_id}", "component_linkage")
        for component_id in components_by_workstream.get(idea_id, [])
    }


def component_diagram_edges(
    *,
    diagrams_by_id: Mapping[str, Mapping[str, Any]],
    components_by_id: Mapping[str, component_registry.ComponentEntry],
    catalog_source: str,
) -> tuple[set[Edge], list[dict[str, str]]]:
    """Return Registry-component-to-Atlas-diagram edges plus repairable warnings."""

    edges: set[Edge] = set()
    warnings: list[dict[str, str]] = []
    for component_id, entry in sorted(components_by_id.items()):
        component_node = f"component:{component_id}"
        for diagram_id in entry.diagrams:
            if diagram_id in diagrams_by_id:
                edges.add((component_node, f"diagram:{diagram_id}", "component_diagram"))
                continue
            warnings.append(
                {
                    "message": f"{component_id}: component references missing diagram `{diagram_id}`",
                    "category": "component_diagram_missing",
                    "severity": "warning",
                    "audience": "maintainer",
                    "surface_visibility": "diagnostics",
                    "action": "Repair Registry/Atlas component diagram linkage.",
                    "source": entry.spec_ref or component_registry.DEFAULT_MANIFEST_PATH,
                }
            )

    for diagram_id, diagram in sorted(diagrams_by_id.items()):
        diagram_node = f"diagram:{diagram_id}"
        for component_id in diagram.get("related_component_ids", []):
            component_node = f"component:{component_id}"
            if component_id in components_by_id:
                edges.add((component_node, diagram_node, "component_diagram"))
                continue
            warnings.append(
                {
                    "message": f"{diagram_id}: related component `{component_id}` not found in Registry",
                    "category": "diagram_component_missing_registry",
                    "severity": "warning",
                    "action": "Register the component or remove the stale Atlas related_component_ids entry.",
                    "source": str(diagram.get("file", "")).strip() or catalog_source,
                }
            )
    return edges, warnings


def execution_program_nodes_and_edges(
    execution_programs: Sequence[execution_wave_contract.ExecutionProgram],
) -> tuple[list[dict[str, Any]], set[Edge]]:
    """Build execution-program and execution-wave graph payloads."""

    nodes: list[dict[str, Any]] = []
    edges: set[Edge] = set()
    for program in execution_programs:
        program_node = f"program:{program.umbrella_id}"
        nodes.append(
            {
                "id": program_node,
                "type": "program",
                "label": f"{program.umbrella_id} execution waves",
                "umbrella_id": program.umbrella_id,
                "version": program.version,
                "file": program.source_file,
            }
        )
        edges.add((program.umbrella_id, program_node, "execution_program"))
        for wave in program.waves:
            wave_node = f"wave:{program.umbrella_id}:{wave.wave_id}"
            nodes.append(
                {
                    "id": wave_node,
                    "type": "wave",
                    "label": wave.label or wave.wave_id,
                    "status": wave.status,
                    "umbrella_id": program.umbrella_id,
                    "wave_id": wave.wave_id,
                    "file": program.source_file,
                }
            )
            edges.add((program_node, wave_node, "execution_wave"))
            for dep in wave.depends_on:
                edges.add((f"wave:{program.umbrella_id}:{dep}", wave_node, "wave_dependency"))
            for workstream_id in wave.all_workstreams():
                edges.add((wave_node, workstream_id, "wave_membership"))
    return nodes, edges
