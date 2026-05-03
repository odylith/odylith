from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common import log_compass_timeline_event
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import validate_component_registry_contract
from odylith.runtime.surfaces import scaffold_mermaid_diagram


def _grounded_backlog_args() -> list[str]:
    return [
        "--problem",
        "Radar needs a real grounded workstream record.",
        "--customer",
        "Operators reviewing Radar detail before implementation begins.",
        "--opportunity",
        "Create the backlog item without generic boilerplate.",
        "--product-view",
        "The backlog should look like governed product truth on first render.",
        "--success-metrics",
        "- The record is grounded.\n- Radar refresh picks it up.",
    ]


def _seed_backlog_repo(root: Path) -> None:
    idea_dir = root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    idea_dir.mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "radar" / "source" / "INDEX.md").write_text(
        "\n".join(
            [
                "# Backlog Index",
                "",
                "Last updated (UTC): 2026-04-14",
                "",
                "## Ranked Active Backlog",
                "",
                "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)",
                "",
                "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## Finished (Linked to `odylith/technical-plans/done`)",
                "",
                "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                "",
                "## Reorder Rationale Log",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.11'\n", encoding="utf-8")
    (root / "src" / "odylith").mkdir(parents=True, exist_ok=True)


def _seed_compass_registry(root: Path) -> None:
    registry_root = root / "odylith" / "registry" / "source"
    registry_root.mkdir(parents=True, exist_ok=True)
    spec_path = root / "odylith" / "registry" / "source" / "components" / "compass" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        "\n".join(
            [
                "# Compass",
                "",
                "## Feature History",
                "- 2026-04-14: Seed Compass spec for authoring refresh tests. (Plan: [B-999](odylith/radar/radar.html?view=plan&workstream=B-999))",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (registry_root / "component_registry.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "compass",
                        "name": "Compass",
                        "kind": "surface",
                        "category": "governance_surface",
                        "qualification": "curated",
                        "aliases": ["compass"],
                        "path_prefixes": [],
                        "workstreams": [],
                        "diagrams": [],
                        "owner": "product",
                        "status": "active",
                        "what_it_is": "Compass surface.",
                        "why_tracked": "Tracked for tests.",
                        "spec_ref": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
                        "sources": ["curated"],
                        "subcomponents": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "v1", "diagrams": []}) + "\n",
        encoding="utf-8",
    )
    (root / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)


def test_owned_surface_refresh_hides_successful_refresh_internals(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    def fake_refresh_owned_surface(**_kwargs) -> int:
        print("dashboard refresh plan")
        print("- noisy internals")
        return 0

    monkeypatch.setattr(owned_surface_refresh, "refresh_owned_surface", fake_refresh_owned_surface)

    owned_surface_refresh.raise_for_failed_refresh(
        repo_root=tmp_path,
        surface="registry",
        operation_label="Component register",
    )

    assert capsys.readouterr().out == ""


def test_backlog_create_refreshes_radar_surface(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[dict[str, object]] = []
    _seed_backlog_repo(tmp_path)
    monkeypatch.setattr(
        backlog_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: calls.append(dict(kwargs)),
    )

    rc = backlog_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--title",
            "Fast Radar visibility lane",
            *_grounded_backlog_args(),
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "radar",
            "operation_label": "Backlog create",
        }
    ]
    assert "view: odylith/index.html?tab=radar&workstream=B-001 (refresh if already open)" in output


def test_component_register_refreshes_registry_surface(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[dict[str, object]] = []
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")
    (tmp_path / "odylith" / "radar" / "source" / "ideas").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: calls.append(dict(kwargs)),
    )

    rc = component_authoring.main(
        [
            "--repo-root",
            str(tmp_path),
            "--id",
            "registry-refresh",
            "--path",
            "src/odylith/runtime/governance",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "registry",
            "operation_label": "Component register",
        }
    ]
    assert (
        "view: odylith/index.html?tab=registry&component=registry-refresh "
        "(refresh if already open)"
    ) in output
    registry_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = registry["components"][0]
    assert entry["category"] == "governance_engine"
    assert entry["qualification"] == "candidate"
    assert entry["sources"] == ["manifest"]
    assert entry["what_it_is"] == (
        "Logical component registered through `odylith component register` "
        "with `src/odylith/runtime/governance` as its initial evidence anchor."
    )
    assert "path prefixes seed the intended boundary" in entry["why_tracked"]
    spec_path = (
        tmp_path
        / "odylith"
        / "registry"
        / "source"
        / "components"
        / "registry-refresh"
        / "CURRENT_SPEC.md"
    )
    spec_text = spec_path.read_text(encoding="utf-8")
    assert "**Logical boundary**" in spec_text
    assert "**Evidence anchor**: `src/odylith/runtime/governance`" in spec_text
    assert (
        validate_component_registry_contract.main(["--repo-root", str(tmp_path)])
        == 0
    )


def test_atlas_scaffold_refreshes_atlas_with_shared_lane(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[dict[str, object]] = []
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")
    for relative in (
        "odylith/radar/source/ideas/2026-04/example.md",
        "odylith/technical-plans/in-progress/2026-04/example.md",
        "docs/example.md",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("seed\n", encoding="utf-8")
    monkeypatch.setattr(
        scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: calls.append(dict(kwargs)),
    )

    rc = scaffold_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-999",
            "--slug",
            "fresh-atlas-lane",
            "--title",
            "Fresh Atlas Lane",
            "--kind",
            "flowchart",
            "--owner",
            "product",
            "--summary",
            "Atlas quick refresh path.",
            "--backlog",
            "odylith/radar/source/ideas/2026-04/example.md",
            "--plan",
            "odylith/technical-plans/in-progress/2026-04/example.md",
            "--doc",
            "docs/example.md",
            "--create-source-if-missing",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "atlas",
            "operation_label": "Atlas scaffold",
        }
    ]
    assert "view: odylith/index.html?tab=atlas&diagram=D-999 (refresh if already open)" in output


def test_atlas_scaffold_allows_atlas_first_draft_without_governance_links(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    calls: list[dict[str, object]] = []
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")
    code_path = tmp_path / "src" / "demo"
    code_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: calls.append(dict(kwargs)),
    )

    rc = scaffold_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-100",
            "--slug",
            "demo-boundary-map",
            "--title",
            "Demo Boundary Map",
            "--kind",
            "flowchart",
            "--owner",
            "product",
            "--summary",
            "Atlas-first boundary draft.",
            "--component",
            "Demo::Logical boundary for the demo package.",
            "--code",
            "src/demo",
        ]
    )

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    entry = payload["diagrams"][0]
    source_text = (tmp_path / "odylith" / "atlas" / "source" / "demo-boundary-map.mmd").read_text(
        encoding="utf-8"
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert entry["status"] == "draft"
    assert entry["link_state"] == "atlas_first_draft"
    assert entry["related_backlog"] == []
    assert entry["related_plans"] == []
    assert entry["related_docs"] == []
    assert entry["change_watch_paths"] == ["src/demo"]
    assert 'diagram["Demo Boundary Map"]' in source_text
    assert "Link Radar, plan, and docs as governance matures" in source_text
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "atlas",
            "operation_label": "Atlas scaffold",
        }
    ]
    assert "view: odylith/index.html?tab=atlas&diagram=D-100 (refresh if already open)" in output


def test_atlas_scaffold_can_still_require_governance_links(tmp_path: Path, monkeypatch) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "v1", "diagrams": []}) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )

    rc = scaffold_mermaid_diagram.main(
        [
            "--repo-root",
            str(tmp_path),
            "--diagram-id",
            "D-101",
            "--slug",
            "strict-boundary-map",
            "--title",
            "Strict Boundary Map",
            "--kind",
            "flowchart",
            "--owner",
            "product",
            "--summary",
            "Strict boundary draft.",
            "--require-links",
        ]
    )

    assert rc == 2
    assert json.loads(catalog_path.read_text(encoding="utf-8"))["diagrams"] == []


def test_compass_log_refreshes_compass_surface(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[dict[str, object]] = []
    _seed_compass_registry(tmp_path)
    monkeypatch.setattr(
        log_compass_timeline_event.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **kwargs: calls.append(dict(kwargs)),
    )

    rc = log_compass_timeline_event.main(
        [
            "--repo-root",
            str(tmp_path),
            "--kind",
            "decision",
            "--summary",
            "Compass visibility should refresh immediately.",
            "--component",
            "compass",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surface": "compass",
            "operation_label": "Compass timeline append",
        }
    ]
    assert "view: odylith/index.html?tab=compass (refresh if already open)" in output
