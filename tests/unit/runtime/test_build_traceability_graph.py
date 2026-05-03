from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import build_traceability_graph as graph_builder
from odylith.runtime.governance import topology_integrity


_SECTIONS = (
    "Problem",
    "Customer",
    "Opportunity",
    "Proposed Solution",
    "Scope",
    "Non-Goals",
    "Risks",
    "Dependencies",
    "Success Metrics",
    "Validation",
    "Rollout",
    "Why Now",
    "Product View",
    "Impacted Components",
    "Interface Changes",
    "Migration/Compatibility",
    "Test Strategy",
    "Open Questions",
)


def _idea_text(
    *,
    idea_id: str,
    title: str,
    execution_model: str = "standard",
    parent: str = "",
    children: str = "",
    depends: str = "",
    diagrams: str = "",
    reopens: str = "",
    reopened_by: str = "",
    split_from: str = "",
    split_into: str = "",
    merged_into: str = "",
    merged_from: str = "",
) -> str:
    sections = "\n\n".join([f"## {name}\nBody." for name in _SECTIONS])
    return (
        "status: planning\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-03-01\n\n"
        "priority: P0\n\n"
        "commercial_value: 5\n\n"
        "product_impact: 5\n\n"
        "market_value: 5\n\n"
        "impacted_parts: control grid\n\n"
        "sizing: L\n\n"
        "complexity: VeryHigh\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: x\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: odylith/technical-plans/in-progress/2026-03-01-{idea_id.lower()}.md\n\n"
        f"execution_model: {execution_model}\n\n"
        f"workstream_type: {'umbrella' if children else ('child' if parent else 'standalone')}\n\n"
        f"workstream_parent: {parent}\n\n"
        f"workstream_children: {children}\n\n"
        f"workstream_depends_on: {depends}\n\n"
        "workstream_blocks: \n\n"
        f"related_diagram_ids: {diagrams}\n\n"
        f"workstream_reopens: {reopens}\n\n"
        f"workstream_reopened_by: {reopened_by}\n\n"
        f"workstream_split_from: {split_from}\n\n"
        f"workstream_split_into: {split_into}\n\n"
        f"workstream_merged_into: {merged_into}\n\n"
        f"workstream_merged_from: {merged_from}\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{sections}\n"
    )


def _write_release_planning_truth(repo_root: Path) -> None:
    releases_dir = repo_root / "odylith" / "radar" / "source" / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    (releases_dir / "releases.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "updated_utc": "2026-03-01",
                "aliases": {
                    "current": "release-0-1-11",
                    "next": "release-next",
                },
                "releases": [
                    {
                        "release_id": "release-0-1-11",
                        "status": "active",
                        "version": "0.1.11",
                        "tag": "",
                        "name": "Launch Title",
                        "notes": "",
                        "created_utc": "2026-03-01",
                        "shipped_utc": "",
                        "closed_utc": "",
                    },
                    {
                        "release_id": "release-next",
                        "status": "planning",
                        "version": "",
                        "tag": "",
                        "name": "Next Cut",
                        "notes": "",
                        "created_utc": "2026-03-01",
                        "shipped_utc": "",
                        "closed_utc": "",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (releases_dir / "release-assignment-events.v1.jsonl").write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "action": "add",
                        "workstream_id": "B-033",
                        "release_id": "release-0-1-11",
                        "recorded_at": "2026-03-01T00:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "action": "move",
                        "workstream_id": "B-033",
                        "from_release_id": "release-0-1-11",
                        "to_release_id": "release-next",
                        "recorded_at": "2026-03-02T00:00:00Z",
                    }
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _write_registry_manifest(repo_root: Path) -> None:
    spec_path = repo_root / "odylith" / "registry" / "source" / "components" / "runtime-core" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "radar.html").write_text("<html></html>\n", encoding="utf-8")
    spec_path.write_text(
        (
            "# Runtime Core\n\n"
            "## Feature History\n"
            "- 2026-03-01: Connected runtime core topology. "
            "(Plan: [B-033](odylith/radar/radar.html?view=plan&workstream=B-033))\n"
        ),
        encoding="utf-8",
    )
    manifest_path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "runtime-core",
                        "name": "runtime-core",
                        "kind": "service",
                        "category": "governance_engine",
                        "qualification": "curated",
                        "aliases": ["runtime core"],
                        "path_prefixes": ["src/runtime_core"],
                        "workstreams": ["B-033"],
                        "diagrams": ["D-003"],
                        "owner": "platform",
                        "status": "active",
                        "what_it_is": "Runtime core component.",
                        "why_tracked": "Owns the runtime topology spine in this fixture.",
                        "spec_ref": "odylith/registry/source/components/runtime-core/CURRENT_SPEC.md",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_traceability_graph_outputs_expected_nodes_edges(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar" / "traceability-autofix-report.v1.json").write_text(
        json.dumps(
            {
                "generated_utc": "2026-03-01T00:00:00Z",
                "conflicts_skipped": [
                    {
                        "idea_id": "B-033",
                        "field": "workstream_split_into",
                        "current": "B-038,B-039",
                        "candidate": "B-038,B-039,B-041",
                        "reason": "reciprocal lineage inferred from `workstream_split_from`",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    idea_umbrella = ideas_dir / "2026-03-01-b-021.md"
    idea_umbrella.write_text(
        _idea_text(idea_id="B-021", title="Umbrella", children="B-033", diagrams="D-003"),
        encoding="utf-8",
    )
    idea_child = ideas_dir / "2026-03-01-b-033.md"
    idea_child.write_text(
        _idea_text(
            idea_id="B-033",
            title="Child",
            parent="B-021",
            depends="B-021",
            diagrams="D-003",
            reopens="B-021",
            split_from="B-021",
            merged_into="B-021",
        ),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    for plan in [
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-021.md",
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-033.md",
    ]:
        plan.write_text(
            (
                "Status: In progress\n\n"
                "Created: 2026-03-01\n\n"
                "Updated: 2026-03-01\n\n"
                "Goal: test\n\n"
                "Assumptions: test\n\n"
                "Constraints: test\n\n"
                "Reversibility: test\n\n"
                "Boundary Conditions: test\n\n"
                "## Traceability\n\n"
                "### Runbooks\n\n"
                "- [x] `consumer-runbooks/account-lifecycle.md`\n\n"
                "### Developer Docs\n\n"
                "- [x] `docs/platform-maintainer-guide.md`\n\n"
                "### Code References\n\n"
                "- [x] `src/odylith/runtime/governance/sync_workstream_artifacts.py`\n"
            ),
            encoding="utf-8",
        )

    (tmp_path / "consumer-runbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "consumer-runbooks" / "account-lifecycle.md").write_text("# runbook\n", encoding="utf-8")
    doc_path = tmp_path / "docs" / "platform-maintainer-guide.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("# doc\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "sync_workstream_artifacts.py").write_text("# code\n", encoding="utf-8")

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "diagrams": [
                    {
                        "diagram_id": "D-003",
                        "slug": "dep",
                        "title": "dep map",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "platform",
                        "last_reviewed_utc": "2026-03-01",
                        "source_mmd": "odylith/atlas/source/workstream-dependency-map.mmd",
                        "source_svg": "odylith/atlas/source/workstream-dependency-map.svg",
                        "source_png": "odylith/atlas/source/workstream-dependency-map.png",
                        "change_watch_paths": ["odylith/radar/source/ideas/2026-03"],
                        "summary": "s",
                        "components": [{"name": "c", "description": "d"}],
                        "related_backlog": [str(idea_child)],
                        "related_workstreams": ["B-021"],
                        "related_plans": ["odylith/technical-plans/in-progress/2026-03-01-b-021.md"],
                        "related_docs": ["docs/platform-maintainer-guide.md"],
                        "related_code": ["src/odylith/runtime/governance/sync_workstream_artifacts.py"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0

    payload = json.loads((tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert payload["summary"]["workstream_count"] == 2
    edge_types = {edge["edge_type"] for edge in payload["edges"]}
    assert "parent_child" in edge_types
    assert "depends_on" in edge_types
    assert "diagram_linkage" in edge_types
    assert "promoted_to_plan" in edge_types
    assert "reopens" in edge_types
    assert "split" in edge_types
    assert "merge" in edge_types
    assert payload["coverage"]["B-033"]["runbook_count"] == 1
    assert isinstance(payload.get("warning_items"), list)
    conflict = next(
        row
        for row in payload["warning_items"]
        if row.get("idea_id") == "B-033" and row.get("category") == "topology_conflict"
    )
    assert conflict["severity"] == "info"
    assert conflict["audience"] == "maintainer"
    assert conflict["surface_visibility"] == "diagnostics"
    ws_b033 = next(row for row in payload["workstreams"] if row["idea_id"] == "B-033")
    assert ws_b033["workstream_reopens"] == "B-021"
    assert ws_b033["workstream_split_from"] == "B-021"
    assert ws_b033["workstream_merged_into"] == "B-021"


def test_build_traceability_graph_adds_registry_program_release_spine_and_quality(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    ideas_dir.joinpath("2026-03-01-b-021.md").write_text(
        _idea_text(
            idea_id="B-021",
            title="Umbrella",
            execution_model="umbrella_waves",
            children="B-033",
            diagrams="D-003",
        ),
        encoding="utf-8",
    )
    ideas_dir.joinpath("2026-03-01-b-033.md").write_text(
        _idea_text(
            idea_id="B-033",
            title="Child",
            parent="B-021",
            diagrams="D-003",
        ),
        encoding="utf-8",
    )

    programs_dir = tmp_path / "odylith" / "radar" / "source" / "programs"
    programs_dir.mkdir(parents=True, exist_ok=True)
    programs_dir.joinpath("B-021.execution-waves.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "umbrella_id": "B-021",
                "waves": [
                    {
                        "wave_id": "W1",
                        "label": "First wave",
                        "status": "active",
                        "summary": "Fixture wave.",
                        "depends_on": [],
                        "primary_workstreams": ["B-033"],
                        "carried_workstreams": [],
                        "in_band_workstreams": [],
                        "gate_refs": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_release_planning_truth(tmp_path)
    _write_registry_manifest(tmp_path)

    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "diagrams": [
                    {
                        "diagram_id": "D-003",
                        "slug": "runtime",
                        "title": "Runtime topology",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "platform",
                        "last_reviewed_utc": "2026-03-01",
                        "source_mmd": "odylith/atlas/source/runtime.mmd",
                        "components": [{"name": "runtime-core", "description": "Runtime core"}],
                        "related_workstreams": ["B-021"],
                        "related_backlog": ["odylith/radar/source/ideas/2026-03/2026-03-01-b-033.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0

    payload = json.loads((tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    nodes = {row["id"]: row for row in payload["nodes"]}
    edges = {(row["source"], row["target"], row["edge_type"]) for row in payload["edges"]}
    assert "component:runtime-core" in nodes
    assert "program:B-021" in nodes
    assert "wave:B-021:W1" in nodes
    assert ("B-033", "component:runtime-core", "component_linkage") in edges
    assert ("component:runtime-core", "diagram:D-003", "component_diagram") in edges
    assert ("B-021", "program:B-021", "execution_program") in edges
    assert ("program:B-021", "wave:B-021:W1", "execution_wave") in edges
    assert ("wave:B-021:W1", "B-033", "wave_membership") in edges
    assert payload["summary"]["component_count"] == 1
    assert payload["summary"]["topology_quality"] == "pass"
    assert payload["topology_integrity"]["algorithm"] == "multipartite-spine-v1"
    assert payload["topology_integrity"]["connectivity"]["structural_edge_count"] >= 6


def test_topology_integrity_reports_dangling_edges_and_unresolved_components() -> None:
    graph = {
        "nodes": [
            {
                "id": "B-033",
                "type": "workstream",
                "status": "implementation",
                "workstream_type": "child",
            },
            {
                "id": "diagram:D-003",
                "type": "diagram",
                "status": "active",
                "related_workstreams": ["B-033"],
                "related_component_ids": ["unknown-component"],
            },
        ],
        "edges": [
            {"source": "B-033", "target": "diagram:D-003", "edge_type": "diagram_linkage"},
            {"source": "B-033", "target": "component:missing", "edge_type": "component_linkage"},
        ],
        "workstreams": [{"idea_id": "B-033", "related_diagram_ids": ["D-003"]}],
    }

    report = topology_integrity.evaluate_topology_integrity(graph)

    assert report["quality"] == "fail"
    categories = {row["category"] for row in report["findings"]}
    assert "dangling_edge_target" in categories
    assert "unresolved_diagram_component_id" in categories


def test_build_traceability_graph_includes_release_catalog_and_active_release_edges(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    ideas_dir.joinpath("2026-03-01-b-033.md").write_text(
        _idea_text(idea_id="B-033", title="Child", execution_model="standard"),
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "1.0", "diagrams": []}),
        encoding="utf-8",
    )
    _write_release_planning_truth(tmp_path)

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0

    payload = json.loads((tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert payload["summary"]["release_count"] == 2
    assert payload["summary"]["active_release_assignment_count"] == 1
    assert payload["current_release"]["release_id"] == "release-0-1-11"
    assert payload["next_release"]["release_id"] == "release-next"
    assert payload["release_aliases"]["current"]["release_id"] == "release-0-1-11"
    assert payload["release_aliases"]["next"]["release_id"] == "release-next"
    assert [row["release_id"] for row in payload["releases"]] == ["release-0-1-11", "release-next"]

    release_edge = next(edge for edge in payload["edges"] if edge["edge_type"] == "active_release")
    assert release_edge == {
        "source": "B-033",
        "target": "release:release-next",
        "edge_type": "active_release",
    }

    release_node = next(node for node in payload["nodes"] if node["id"] == "release:release-next")
    assert release_node["type"] == "release"
    assert release_node["label"] == "Next Cut"
    assert release_node["aliases"] == ["next"]

    workstream = next(row for row in payload["workstreams"] if row["idea_id"] == "B-033")
    assert workstream["active_release_id"] == "release-next"
    assert workstream["active_release"]["display_label"] == "Next Cut"
    assert len(workstream["release_history"]) == 2
    assert "Latest move: Launch Title -> Next Cut" in workstream["release_history_summary"]


def test_build_traceability_graph_keeps_generated_utc_stable_on_repeat_runs(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    ideas_dir.joinpath("2026-03-01-b-021.md").write_text(
        _idea_text(idea_id="B-021", title="Umbrella", children="B-033", diagrams="D-003"),
        encoding="utf-8",
    )
    ideas_dir.joinpath("2026-03-01-b-033.md").write_text(
        _idea_text(idea_id="B-033", title="Child", parent="B-021", depends="B-021", diagrams="D-003"),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    for plan in [
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-021.md",
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-033.md",
    ]:
        plan.write_text(
            (
                "Status: In progress\n\n"
                "Created: 2026-03-01\n\n"
                "Updated: 2026-03-01\n\n"
                "Goal: test\n\n"
                "Assumptions: test\n\n"
                "Constraints: test\n\n"
                "Reversibility: test\n\n"
                "Boundary Conditions: test\n\n"
                "## Traceability\n\n"
                "### Runbooks\n\n"
                "- [x] `consumer-runbooks/account-lifecycle.md`\n\n"
                "### Developer Docs\n\n"
                "- [x] `docs/platform-maintainer-guide.md`\n\n"
                "### Code References\n\n"
                "- [x] `src/odylith/runtime/governance/sync_workstream_artifacts.py`\n"
            ),
            encoding="utf-8",
        )

    (tmp_path / "consumer-runbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "consumer-runbooks" / "account-lifecycle.md").write_text("# runbook\n", encoding="utf-8")
    doc_path = tmp_path / "docs" / "platform-maintainer-guide.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("# doc\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "sync_workstream_artifacts.py").write_text("# code\n", encoding="utf-8")

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "diagrams": [
                    {
                        "diagram_id": "D-003",
                        "slug": "dep",
                        "title": "dep map",
                        "kind": "flowchart",
                        "status": "active",
                        "owner": "platform",
                        "last_reviewed_utc": "2026-03-01",
                        "source_mmd": "odylith/atlas/source/workstream-dependency-map.mmd",
                        "source_svg": "odylith/atlas/source/workstream-dependency-map.svg",
                        "source_png": "odylith/atlas/source/workstream-dependency-map.png",
                        "change_watch_paths": ["odylith/radar/source/ideas/2026-03"],
                        "summary": "s",
                        "components": [{"name": "c", "description": "d"}],
                        "related_backlog": ["odylith/radar/source/ideas/2026-03/2026-03-01-b-033.md"],
                        "related_workstreams": ["B-021"],
                        "related_plans": ["odylith/technical-plans/in-progress/2026-03-01-b-021.md"],
                        "related_docs": ["docs/platform-maintainer-guide.md"],
                        "related_code": ["src/odylith/runtime/governance/sync_workstream_artifacts.py"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "odylith" / "radar" / "traceability-graph.v1.json"
    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0
    first = json.loads(output.read_text(encoding="utf-8"))

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0
    second = json.loads(output.read_text(encoding="utf-8"))

    assert first["generated_utc"] == second["generated_utc"]


def test_build_traceability_graph_writes_only_canonical_odylith_graph(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    ideas_dir.joinpath("2026-03-01-b-021.md").write_text(
        _idea_text(idea_id="B-021", title="Umbrella"),
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-021.md").write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-03-01\n\n"
            "Updated: 2026-03-01\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Traceability\n\n"
            "### Runbooks\n\n"
            "- [x] `consumer-runbooks/account-lifecycle.md`\n"
        ),
        encoding="utf-8",
    )
    output = tmp_path / "odylith" / "radar" / "traceability-graph.v1.json"
    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0
    assert output.exists()
    assert not (tmp_path / "backlog").exists()
    (tmp_path / "consumer-runbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "consumer-runbooks" / "account-lifecycle.md").write_text("# runbook\n", encoding="utf-8")
    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "1.0", "diagrams": []}) + "\n",
        encoding="utf-8",
    )

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0
    assert (tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").exists()
    assert not (tmp_path / "backlog").exists()


def test_build_traceability_graph_emits_execution_programs_and_workstream_wave_refs(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar" / "source" / "programs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    ideas_dir.joinpath("2026-03-01-b-021.md").write_text(
        _idea_text(
            idea_id="B-021",
            title="Umbrella",
            execution_model="umbrella_waves",
            children="B-022",
        ),
        encoding="utf-8",
    )
    ideas_dir.joinpath("2026-03-01-b-022.md").write_text(
        _idea_text(idea_id="B-022", title="Child", parent="B-021", depends="B-021"),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    for plan in [
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-021.md",
        tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-022.md",
    ]:
        plan.write_text(
            (
                "Status: In progress\n\n"
                "Created: 2026-03-01\n\n"
                "Updated: 2026-03-01\n\n"
                "Goal: test\n\n"
                "Assumptions: test\n\n"
                "Constraints: test\n\n"
                "Reversibility: test\n\n"
                "Boundary Conditions: test\n\n"
                "## Traceability\n\n"
                "### Runbooks\n\n"
                "- [x] `consumer-runbooks/account-lifecycle.md`\n\n"
                "### Developer Docs\n\n"
                "- [x] `docs/platform-maintainer-guide.md`\n\n"
                "### Code References\n\n"
                "- [x] `src/odylith/runtime/governance/sync_workstream_artifacts.py`\n"
            ),
            encoding="utf-8",
        )

    (tmp_path / "consumer-runbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "consumer-runbooks" / "account-lifecycle.md").write_text("# runbook\n", encoding="utf-8")
    doc_path = tmp_path / "docs" / "platform-maintainer-guide.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("# doc\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "sync_workstream_artifacts.py").write_text("# code\n", encoding="utf-8")

    (tmp_path / "odylith" / "radar" / "source" / "programs" / "B-021.execution-waves.v1.json").write_text(
        (
            "{\n"
            '  "umbrella_id": "B-021",\n'
            '  "version": "v1",\n'
            '  "waves": [\n'
            "    {\n"
            '      "wave_id": "W1",\n'
            '      "label": "Wave 1",\n'
            '      "status": "active",\n'
            '      "summary": "summary",\n'
            '      "depends_on": [],\n'
            '      "primary_workstreams": ["B-022"],\n'
            '      "carried_workstreams": [],\n'
            '      "in_band_workstreams": [],\n'
            '      "gate_refs": [\n'
            "        {\n"
            '          "workstream_id": "B-022",\n'
            '          "plan_path": "odylith/technical-plans/in-progress/2026-03-01-b-022.md",\n'
            '          "label": "gate"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "1.0", "diagrams": []}) + "\n",
        encoding="utf-8",
    )

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0

    payload = json.loads((tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert payload["summary"]["execution_program_count"] == 1
    assert payload["summary"]["execution_wave_count"] == 1
    assert payload["execution_programs"][0]["umbrella_id"] == "B-021"
    member = next(row for row in payload["workstreams"] if row["idea_id"] == "B-022")
    assert member["execution_wave_refs"] == [
        {
            "umbrella_id": "B-021",
            "wave_id": "W1",
            "wave_label": "Wave 1",
            "wave_status": "active",
            "role": "primary",
            "source_file": "odylith/radar/source/programs/B-021.execution-waves.v1.json",
        }
    ]
    assert all(node["type"] != "execution_wave" for node in payload["nodes"])


def test_build_traceability_graph_preserves_explicit_consumer_truth_root_paths(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    (tmp_path / ".odylith").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".odylith" / "consumer-profile.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": "consumer-repo",
                "truth_roots": {
                    "component_specs": "consumer-registry/source/components",
                    "runbooks": "consumer-runbooks/platform",
                },
                "surface_roots": {
                    "product_root": "odylith",
                    "runtime_root": ".odylith",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "compass").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "compass" / "SPEC.md").write_text("# Compass\n", encoding="utf-8")
    (tmp_path / "odylith" / "runtime" / "CONTEXT_ENGINE_OPERATIONS.md").write_text("# Ops\n", encoding="utf-8")

    idea_path = ideas_dir / "2026-03-01-b-321.md"
    idea_path.write_text(_idea_text(idea_id="B-321", title="Canonical"), encoding="utf-8")
    plan_path = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-321.md"
    plan_path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-03-01\n\n"
            "Updated: 2026-03-01\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Traceability\n\n"
            "### Runbooks\n\n"
                "- [x] `consumer-runbooks/platform/odylith-context-engine-operations.md`\n\n"
            "### Developer Docs\n\n"
            "- [x] `consumer-registry/source/components/compass/CURRENT_SPEC.md`\n\n"
            "### Code References\n\n"
            "- [x] `src/odylith/runtime/surfaces/compass_dashboard_shell.py`\n"
        ),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "1.0", "diagrams": []}) + "\n",
        encoding="utf-8",
    )

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0

    payload = json.loads((tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    row = next(item for item in payload["workstreams"] if item["idea_id"] == "B-321")
    assert row["plan_traceability"]["developer_docs"] == ["consumer-registry/source/components/compass/CURRENT_SPEC.md"]
    assert row["plan_traceability"]["runbooks"] == ["consumer-runbooks/platform/odylith-context-engine-operations.md"]


def test_build_traceability_graph_uses_repo_bounded_plan_traceability_parser(tmp_path: Path) -> None:
    (tmp_path / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)

    idea_path = ideas_dir / "2026-03-01-b-322.md"
    idea_path.write_text(_idea_text(idea_id="B-322", title="Trace Parser"), encoding="utf-8")

    (tmp_path / "docs" / "runbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "runbooks" / "repair.md").write_text("# Repair\n", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    absolute_inside = tmp_path / "src" / "app.py"
    absolute_outside = tmp_path.parent / f"{tmp_path.name}-outside.md"

    plan_path = tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-01-b-322.md"
    plan_path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-03-01\n\n"
            "Updated: 2026-03-01\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Traceability:\n\n"
            "### runbooks:\n\n"
            "* [Repair](<docs/runbooks/repair.md#operator-flow>)\n"
            "* [Outside](../outside.md)\n\n"
            "### developer docs:\n\n"
            "* [Guide](docs/../docs/guide.md?draft=true)\n"
            f"* `{absolute_outside}`\n\n"
            "### code references:\n\n"
            f"* `{absolute_inside}:42:7`\n"
            "* `<bad>`\n"
        ),
        encoding="utf-8",
    )

    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "1.0", "diagrams": []}) + "\n",
        encoding="utf-8",
    )

    rc = graph_builder.main(["--repo-root", str(tmp_path), "--output", "odylith/radar/traceability-graph.v1.json"])
    assert rc == 0

    payload = json.loads((tmp_path / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    row = next(item for item in payload["workstreams"] if item["idea_id"] == "B-322")
    assert row["plan_traceability"] == {
        "runbooks": ["docs/runbooks/repair.md"],
        "developer_docs": ["docs/guide.md"],
        "code_references": ["src/app.py"],
    }
    artifact_files = {
        node["file"]
        for node in payload["nodes"]
        if node.get("type") == "artifact"
    }
    assert artifact_files == {"docs/runbooks/repair.md", "docs/guide.md", "src/app.py"}
    assert all("outside" not in value and "<bad>" not in value for value in artifact_files)
