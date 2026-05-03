"""Fast topology-spine integrity checks for Odylith governance surfaces."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common import repo_path_resolver


ALGORITHM_ID = "multipartite-spine-v1"
STRUCTURAL_EDGE_TYPES = frozenset(
    {
        "active_release",
        "blocks",
        "component_diagram",
        "component_linkage",
        "depends_on",
        "diagram_linkage",
        "execution_program",
        "execution_wave",
        "merge",
        "parent_child",
        "reopens",
        "split",
        "wave_dependency",
        "wave_membership",
    }
)
SPINE_NODE_TYPES = frozenset({"workstream", "diagram", "component", "release", "program", "wave"})
_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_COMPONENT_WORD_GAP_RE = re.compile(r"[^a-z0-9]+")
_TERMINAL_STATUSES = frozenset({"closed", "complete", "done", "finished", "shipped"})


@dataclass(frozen=True)
class TopologyFinding:
    severity: str
    category: str
    message: str
    node_id: str = ""
    source: str = ""
    target: str = ""
    action: str = ""

    def as_dict(self) -> dict[str, str]:
        return {key: value for key, value in asdict(self).items() if value}


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate topology-integrity",
        description="Validate the shared Radar/Registry/Atlas/Program/Release topology spine.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--traceability-graph",
        default="odylith/radar/traceability-graph.v1.json",
        help="Path to the generated shared traceability graph.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=90,
        help="Minimum quality score required for a passing report.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit the report as JSON.")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=token)


def _as_repo_path(repo_root: Path, path: Path) -> str:
    return repo_path_resolver.display_repo_path(repo_root=repo_root, value=path)


def _node_id(row: Mapping[str, Any]) -> str:
    return str(row.get("id", "")).strip()


def _node_type(row: Mapping[str, Any]) -> str:
    return str(row.get("type", "")).strip().lower()


def _edge_tuple(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("source", "")).strip(),
        str(row.get("target", "")).strip(),
        str(row.get("edge_type", "")).strip(),
    )


def _list_values(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item or "").strip() for item in value if str(item or "").strip()]


def _component_token(value: str) -> str:
    token = _COMPONENT_WORD_GAP_RE.sub("-", str(value or "").strip().lower()).strip("-")
    return token


def _component_lookup(nodes: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for node_id, node in nodes.items():
        if _node_type(node) != "component":
            continue
        for raw in (
            str(node.get("component_id", "")).strip(),
            str(node.get("label", "")).strip(),
            *_list_values(node.get("aliases")),
        ):
            token = _component_token(raw)
            if token:
                lookup.setdefault(token, node_id)
    return lookup


def _edge_index(edges: Sequence[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    return {_edge_tuple(edge) for edge in edges if any(_edge_tuple(edge))}


def _status_is_terminal(value: str) -> bool:
    return str(value or "").strip().lower() in _TERMINAL_STATUSES


def _spine_connectivity(
    *,
    nodes: Mapping[str, Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    spine_nodes = {
        node_id
        for node_id, node in nodes.items()
        if _node_type(node) in SPINE_NODE_TYPES
    }
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in spine_nodes}
    structural_edges = 0
    for edge in edges:
        source, target, edge_type = _edge_tuple(edge)
        if edge_type not in STRUCTURAL_EDGE_TYPES:
            continue
        if source not in spine_nodes or target not in spine_nodes:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)
        structural_edges += 1

    components: list[list[str]] = []
    visited: set[str] = set()
    for node_id in sorted(spine_nodes):
        if node_id in visited:
            continue
        queue: deque[str] = deque([node_id])
        visited.add(node_id)
        members: list[str] = []
        while queue:
            current = queue.popleft()
            members.append(current)
            for neighbor in sorted(adjacency.get(current, ())):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)
        components.append(sorted(members))

    isolated = sorted(node_id for node_id, neighbors in adjacency.items() if not neighbors)
    largest = max((len(members) for members in components), default=0)
    return {
        "spine_node_count": len(spine_nodes),
        "structural_edge_count": structural_edges,
        "connected_component_count": len(components),
        "largest_component_size": largest,
        "isolated_node_count": len(isolated),
        "isolated_nodes": isolated[:32],
    }


def _severity_counts(findings: Sequence[TopologyFinding]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in findings:
        severity = str(finding.severity or "warning").strip().lower()
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _quality_score(counts: Mapping[str, int]) -> int:
    score = 100
    score -= int(counts.get("error", 0) or 0) * 15
    score -= int(counts.get("warning", 0) or 0) * 4
    score -= int(counts.get("info", 0) or 0)
    return max(0, min(100, score))


def evaluate_topology_integrity(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic O(V+E) integrity report for the shared topology graph."""

    raw_nodes = graph.get("nodes", [])
    raw_edges = graph.get("edges", [])
    raw_workstreams = graph.get("workstreams", [])
    nodes = {
        _node_id(row): dict(row)
        for row in raw_nodes
        if isinstance(row, Mapping) and _node_id(row)
    } if isinstance(raw_nodes, list) else {}
    edges = [dict(row) for row in raw_edges if isinstance(row, Mapping)] if isinstance(raw_edges, list) else []
    workstreams = [
        dict(row)
        for row in raw_workstreams
        if isinstance(row, Mapping)
    ] if isinstance(raw_workstreams, list) else []

    findings: list[TopologyFinding] = []
    edge_keys = _edge_index(edges)

    for edge in edges:
        source, target, edge_type = _edge_tuple(edge)
        if not source or not target or not edge_type:
            findings.append(
                TopologyFinding(
                    severity="error",
                    category="malformed_edge",
                    message="Topology edge is missing source, target, or edge_type.",
                    source=source,
                    target=target,
                )
            )
            continue
        if source not in nodes:
            findings.append(
                TopologyFinding(
                    severity="error",
                    category="dangling_edge_source",
                    message=f"Topology edge `{edge_type}` references missing source node `{source}`.",
                    source=source,
                    target=target,
                    action="Rebuild the traceability graph from current source truth.",
                )
            )
        if target not in nodes:
            findings.append(
                TopologyFinding(
                    severity="error",
                    category="dangling_edge_target",
                    message=f"Topology edge `{edge_type}` references missing target node `{target}`.",
                    source=source,
                    target=target,
                    action="Rebuild the traceability graph from current source truth.",
                )
            )

    for row in workstreams:
        idea_id = str(row.get("idea_id", "")).strip()
        if not _WORKSTREAM_ID_RE.fullmatch(idea_id):
            continue
        for diagram_id in _list_values(row.get("related_diagram_ids")):
            if not _DIAGRAM_ID_RE.fullmatch(diagram_id):
                continue
            diagram_node = f"diagram:{diagram_id}"
            if diagram_node not in nodes:
                findings.append(
                    TopologyFinding(
                        severity="error",
                        category="missing_diagram_node",
                        message=f"Workstream `{idea_id}` links `{diagram_id}` but the diagram node is absent.",
                        node_id=idea_id,
                        target=diagram_node,
                    )
                )
            elif (idea_id, diagram_node, "diagram_linkage") not in edge_keys:
                findings.append(
                    TopologyFinding(
                        severity="error",
                        category="missing_diagram_edge",
                        message=f"Workstream `{idea_id}` links `{diagram_id}` but the graph lacks a diagram_linkage edge.",
                        node_id=idea_id,
                        target=diagram_node,
                    )
                )
        release_id = str(row.get("active_release_id", "")).strip()
        if release_id and (idea_id, f"release:{release_id}", "active_release") not in edge_keys:
            findings.append(
                TopologyFinding(
                    severity="error",
                    category="missing_release_edge",
                    message=f"Workstream `{idea_id}` has active release `{release_id}` but no active_release edge.",
                    node_id=idea_id,
                    target=f"release:{release_id}",
                )
            )
        for ref in row.get("execution_wave_refs", []) if isinstance(row.get("execution_wave_refs"), list) else []:
            if not isinstance(ref, Mapping):
                continue
            umbrella = str(ref.get("umbrella_id", "")).strip()
            wave_id = str(ref.get("wave_id", "")).strip()
            wave_node = f"wave:{umbrella}:{wave_id}"
            if umbrella and wave_id and (wave_node, idea_id, "wave_membership") not in edge_keys:
                findings.append(
                    TopologyFinding(
                        severity="error",
                        category="missing_wave_edge",
                        message=f"Workstream `{idea_id}` has execution wave `{umbrella}/{wave_id}` but no wave_membership edge.",
                        node_id=idea_id,
                        source=wave_node,
                    )
                )

    component_lookup = _component_lookup(nodes)
    for node_id, node in sorted(nodes.items()):
        node_type = _node_type(node)
        if node_type == "diagram":
            related_workstreams = _list_values(node.get("related_workstreams"))
            if str(node.get("status", "active")).strip().lower() == "active" and not related_workstreams:
                findings.append(
                    TopologyFinding(
                        severity="warning",
                        category="unlinked_diagram",
                        message=f"Active diagram `{node_id}` is not linked to any Radar workstream.",
                        node_id=node_id,
                        action="Add related_workstreams/related_backlog in Atlas or related_diagram_ids in Radar.",
                    )
                )
            for component_id in _list_values(node.get("related_component_ids")):
                component_node = component_lookup.get(_component_token(component_id))
                if not component_node:
                    findings.append(
                        TopologyFinding(
                            severity="warning",
                            category="unresolved_diagram_component_id",
                            message=f"Diagram `{node_id}` declares related component `{component_id}` but Registry has no matching component id, name, or alias.",
                            node_id=node_id,
                            action="Register or alias the component, or remove the stale Atlas related_component_ids entry.",
                        )
                    )
                    continue
                if (component_node, node_id, "component_diagram") not in edge_keys:
                    findings.append(
                        TopologyFinding(
                            severity="error",
                            category="missing_component_diagram_edge",
                            message=f"Diagram `{node_id}` resolves `{component_id}` to `{component_node}` but lacks a component_diagram edge.",
                            node_id=node_id,
                            source=component_node,
                            target=node_id,
                        )
                    )
        elif node_type == "component":
            workstreams = _list_values(node.get("workstreams"))
            diagrams = _list_values(node.get("diagrams"))
            if str(node.get("status", "active")).strip().lower() == "active" and not workstreams and not diagrams:
                findings.append(
                    TopologyFinding(
                        severity="warning",
                        category="unlinked_component",
                        message=f"Active component `{node_id}` has no Radar workstream or Atlas diagram linkage.",
                        node_id=node_id,
                        action="Connect the component through Registry workstreams, Atlas components, or Radar impacted components.",
                    )
                )
            for workstream_id in workstreams:
                if workstream_id not in nodes:
                    findings.append(
                        TopologyFinding(
                            severity="warning",
                            category="component_missing_workstream",
                            message=f"Component `{node_id}` references missing workstream `{workstream_id}`.",
                            node_id=node_id,
                            target=workstream_id,
                        )
                    )
                elif (workstream_id, node_id, "component_linkage") not in edge_keys:
                    findings.append(
                        TopologyFinding(
                            severity="error",
                            category="missing_component_workstream_edge",
                            message=f"Component `{node_id}` references `{workstream_id}` but lacks a component_linkage edge.",
                            node_id=node_id,
                            source=workstream_id,
                        )
                    )
            for diagram_id in diagrams:
                diagram_node = f"diagram:{diagram_id}"
                if diagram_node not in nodes:
                    findings.append(
                        TopologyFinding(
                            severity="warning",
                            category="component_missing_diagram",
                            message=f"Component `{node_id}` references missing diagram `{diagram_id}`.",
                            node_id=node_id,
                            target=diagram_node,
                        )
                    )
                elif (node_id, diagram_node, "component_diagram") not in edge_keys:
                    findings.append(
                        TopologyFinding(
                            severity="error",
                            category="missing_component_diagram_edge",
                            message=f"Component `{node_id}` references `{diagram_id}` but lacks a component_diagram edge.",
                            node_id=node_id,
                            target=diagram_node,
                        )
                    )

    connectivity = _spine_connectivity(nodes=nodes, edges=edges)
    for node_id in connectivity["isolated_nodes"]:
        node = nodes.get(node_id, {})
        node_type = _node_type(node)
        if node_type not in {"component", "diagram", "workstream"}:
            continue
        if node_type == "workstream" and _status_is_terminal(str(node.get("status", ""))):
            continue
        if node_type == "workstream" and str(node.get("workstream_type", "")).strip().lower() == "standalone":
            continue
        findings.append(
            TopologyFinding(
                severity="warning",
                category="isolated_spine_node",
                message=f"Topology spine node `{node_id}` is isolated from all structural graph edges.",
                node_id=node_id,
                action="Declare a topology rationale or link it to the relevant workstream, component, diagram, program, or release.",
            )
        )

    counts = _severity_counts(findings)
    score = _quality_score(counts)
    if counts.get("error", 0):
        quality = "fail"
    elif score < 90:
        quality = "attention"
    else:
        quality = "pass"
    return {
        "version": "v1",
        "algorithm": ALGORITHM_ID,
        "complexity": "O(V+E)",
        "quality": quality,
        "score": score,
        "severity_counts": counts,
        "connectivity": connectivity,
        "findings": [finding.as_dict() for finding in findings],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    graph_path = _resolve(repo_root, str(args.traceability_graph))
    if not graph_path.is_file():
        report = {
            "version": "v1",
            "algorithm": ALGORITHM_ID,
            "quality": "fail",
            "score": 0,
            "severity_counts": {"error": 1, "warning": 0, "info": 0},
            "findings": [
                {
                    "severity": "error",
                    "category": "missing_traceability_graph",
                    "message": f"Traceability graph not found: {_as_repo_path(repo_root, graph_path)}",
                    "action": "Run `odylith sync --repo-root .` or the owned Radar refresh before validating topology integrity.",
                }
            ],
        }
        if args.as_json:
            print(json.dumps(report, indent=2))
        else:
            print("topology integrity report FAILED")
            print(f"- graph: {_as_repo_path(repo_root, graph_path)}")
            print("- error: traceability graph not found")
        return 2

    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print("topology integrity report FAILED")
        print(f"- graph: {_as_repo_path(repo_root, graph_path)}")
        print(f"- error: invalid json ({exc})")
        return 2
    if not isinstance(payload, Mapping):
        print("topology integrity report FAILED")
        print(f"- graph: {_as_repo_path(repo_root, graph_path)}")
        print("- error: traceability graph root must be an object")
        return 2

    report = evaluate_topology_integrity(payload)
    min_score = max(0, min(100, int(args.min_score)))
    failed = bool(report.get("severity_counts", {}).get("error", 0)) or int(report.get("score", 0) or 0) < min_score
    if args.as_json:
        print(json.dumps(report, indent=2))
        return 2 if failed else 0

    print("topology integrity report")
    print(f"- graph: {_as_repo_path(repo_root, graph_path)}")
    print(f"- algorithm: {report['algorithm']} ({report['complexity']})")
    print(f"- quality: {report['quality']}")
    print(f"- score: {report['score']}/100 (min {min_score})")
    counts = report.get("severity_counts", {})
    print(
        "- findings: "
        f"{counts.get('error', 0)} error(s), {counts.get('warning', 0)} warning(s), {counts.get('info', 0)} info"
    )
    connectivity = report.get("connectivity", {})
    print(
        "- spine: "
        f"{connectivity.get('spine_node_count', 0)} nodes, "
        f"{connectivity.get('structural_edge_count', 0)} structural edges, "
        f"{connectivity.get('connected_component_count', 0)} connected component(s)"
    )
    for finding in report.get("findings", [])[:32]:
        if not isinstance(finding, Mapping):
            continue
        print(f"- {finding.get('severity', 'warning')}: {finding.get('message', '')}")
    if failed:
        print("topology integrity report FAILED")
        return 2
    print("topology integrity report passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
