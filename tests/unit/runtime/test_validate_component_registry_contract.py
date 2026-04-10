from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import validate_component_registry_contract as validator


def _write_idea(path: Path, *, idea_id: str, impacted_components: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "status: planning\n\n"
            f"idea_id: {idea_id}\n\n"
            "title: Example\n\n"
            "date: 2026-03-04\n\n"
            "priority: P0\n\n"
            "commercial_value: 5\n\n"
            "product_impact: 5\n\n"
            "market_value: 5\n\n"
            "impacted_parts: x\n\n"
            "sizing: L\n\n"
            "complexity: VeryHigh\n\n"
            "ordering_score: 100\n\n"
            "ordering_rationale: x\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan: odylith/technical-plans/in-progress/2026-03-04-example.md\n\n"
            "workstream_type: standalone\n\n"
            "workstream_parent:\n\n"
            "workstream_children:\n\n"
            "workstream_depends_on:\n\n"
            "workstream_blocks:\n\n"
            "related_diagram_ids: D-100\n\n"
            "workstream_reopens:\n\n"
            "workstream_reopened_by:\n\n"
            "workstream_split_from:\n\n"
            "workstream_split_into:\n\n"
            "workstream_merged_into:\n\n"
            "workstream_merged_from:\n\n"
            "supersedes:\n\n"
            "superseded_by:\n\n"
            "## Problem\nBody\n\n"
            "## Customer\nBody\n\n"
            "## Opportunity\nBody\n\n"
            "## Proposed Solution\nBody\n\n"
            "## Scope\nBody\n\n"
            "## Non-Goals\nBody\n\n"
            "## Risks\nBody\n\n"
            "## Dependencies\nBody\n\n"
            "## Success Metrics\nBody\n\n"
            "## Validation\nBody\n\n"
            "## Rollout\nBody\n\n"
            "## Why Now\nBody\n\n"
            "## Product View\nBody\n\n"
            f"## Impacted Components\n{impacted_components}\n\n"
            "## Interface Changes\nBody\n\n"
            "## Migration/Compatibility\nBody\n\n"
            "## Test Strategy\nBody\n\n"
            "## Open Questions\nBody\n"
        ),
        encoding="utf-8",
    )


def _write_catalog(tmp_path: Path, diagrams: list[dict[str, object]] | None = None) -> None:
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps({"version": "1.0", "diagrams": diagrams or []}, indent=2) + "\n",
        encoding="utf-8",
    )


def _seed_repo(tmp_path: Path) -> None:
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path = tmp_path / "odylith" / "radar" / "radar.html"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("<html><body>B-901</body></html>\n", encoding="utf-8")
    spec_path.write_text(
        (
            "# Radar Component Spec\n\n"
            "Last updated: 2026-03-04\n\n"
            "## Purpose\nRadar surface.\n\n"
            "## Feature History\n"
            "- 2026-03-04: Added validator fixture baseline for component spec enforcement. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "radar",
                        "name": "Radar",
                        "kind": "composite",
                        "category": "governance_surface",
                        "qualification": "curated",
                        "aliases": ["backlog-radar"],
                        "path_prefixes": ["src/odylith/runtime/surfaces/render_backlog_ui.py"],
                        "workstreams": ["B-901"],
                        "diagrams": ["D-100"],
                        "owner": "platform",
                        "status": "active",
                        "what_it_is": "Backlog radar surface.",
                        "why_tracked": "Primary planning governance view.",
                        "spec_ref": "odylith/registry/source/components/radar/CURRENT_SPEC.md",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    _write_catalog(tmp_path)

    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    _write_idea(
        ideas_root / "2026-03-04-example.md",
        idea_id="B-901",
        impacted_components="`Radar`",
    )


def test_validate_component_registry_contract_passes_when_meaningful_events_are_mapped(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "kind": "implementation",
                "summary": "Updated radar rendering logic.",
                "workstreams": ["B-901"],
                "artifacts": ["src/odylith/runtime/surfaces/render_backlog_ui.py"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 0


def test_validate_component_registry_contract_warning_output_points_to_report(tmp_path: Path, capsys) -> None:
    _seed_repo(tmp_path)

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "component registry contract warnings" in output
    assert "- report: " in output
    assert "component-report" in output


def test_validate_component_registry_contract_ignores_catalog_labels_without_inventory_review_flag(
    tmp_path: Path,
    capsys,
) -> None:
    _seed_repo(tmp_path)
    _write_catalog(
        tmp_path,
        [
            {
                "diagram_id": "D-100",
                "title": "Fixture Diagram",
                "components": [
                    {
                        "name": "Bootstrap lane",
                        "description": "Diagram-local stage label.",
                    }
                ],
            }
        ],
    )

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "candidate components pending review" not in output
    assert "component registry contract warnings" not in output


def test_validate_component_registry_contract_surfaces_opt_in_catalog_inventory_candidates(
    tmp_path: Path,
    capsys,
) -> None:
    _seed_repo(tmp_path)
    _write_catalog(
        tmp_path,
        [
            {
                "diagram_id": "D-100",
                "title": "Fixture Diagram",
                "components": [
                    {
                        "name": "Bootstrap lane",
                        "description": "Diagram-local stage label.",
                        "inventory_candidate": True,
                    }
                ],
            }
        ],
    )

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "component registry contract warnings" in output
    assert "candidate components pending review: 1" in output


def test_validate_component_registry_contract_suppresses_missing_deep_skill_target_noise(
    tmp_path: Path,
    capsys,
) -> None:
    _seed_repo(tmp_path)

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "component policy warnings" not in output
    assert "deep-skill policy `kafka-topic`" not in output
    assert "deep-skill policy `msk`" not in output


def test_validate_component_registry_contract_accepts_odylith_chatter_component_inventory(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "odylith-chatter" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        (
            "# Odylith Chatter Component Spec\n\n"
            "Last updated: 2026-03-31\n\n"
            "## Feature History\n"
            "- 2026-03-31: Added the chatter contract component. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )

    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["components"].append(
        {
            "component_id": "odylith-chatter",
            "name": "Odylith Chatter",
            "kind": "runtime",
            "category": "governance_engine",
            "qualification": "curated",
            "aliases": ["commentary-contract"],
            "path_prefixes": ["AGENTS.md"],
            "workstreams": ["B-901"],
            "diagrams": [],
            "owner": "product",
            "status": "active",
            "what_it_is": "Narration policy.",
            "why_tracked": "Keeps commentary policy governed.",
            "spec_ref": "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md",
        }
    )
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "kind": "implementation",
                "summary": "Refined Odylith chatter policy.",
                "workstreams": ["B-901"],
                "artifacts": ["AGENTS.md"],
                "components": ["odylith-chatter"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 0


def test_validate_component_registry_contract_fails_on_unmapped_meaningful_events(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "kind": "implementation",
                "summary": "Implemented service handler updates.",
                "workstreams": ["B-999"],
                "artifacts": ["services/example/handler.py"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 2


def test_validate_component_registry_contract_fails_when_spec_ref_missing(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["components"][0].pop("spec_ref", None)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 2


def test_validate_component_registry_contract_fails_when_spec_history_missing(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.write_text("# Radar Component Spec\n\nLast updated: 2026-03-04\n", encoding="utf-8")

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 2


def test_validate_component_registry_contract_fails_when_feature_history_plan_link_missing(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.write_text(
        (
            "# Radar Component Spec\n\n"
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Added validator fixture baseline for component spec enforcement.\n"
        ),
        encoding="utf-8",
    )

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 2


def test_validate_component_registry_contract_allows_upstream_product_feature_history_without_local_plan_ref_in_consumer_repo(
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)
    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["components"][0]["owner"] = "product"
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.write_text(
        (
            "# Radar Component Spec\n\n"
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Added upstream product provenance for the installed component bundle.\n"
        ),
        encoding="utf-8",
    )

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 0


def test_validate_component_registry_contract_allows_feature_history_plan_route_without_rendered_plan_page(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    plan_path = tmp_path / "odylith" / "radar" / "radar.html"
    plan_path.unlink()

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
        ]
    )
    assert rc == 0


def test_validate_component_registry_contract_enforce_deep_skills_fails_for_required_component(
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)
    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["components"][0]["component_id"] = "kafka-topic"
    payload["components"][0]["name"] = "Kafka Topic"
    payload["components"][0]["aliases"] = ["kafka-topic"]
    payload["components"][0]["workstreams"] = ["B-901"]
    payload["components"][0]["spec_ref"] = "odylith/registry/source/components/radar/CURRENT_SPEC.md"
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")

    rc = validator.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "odylith/registry/source/component_registry.v1.json",
            "--catalog",
            "odylith/atlas/source/catalog/diagrams.v1.json",
            "--ideas-root",
            "odylith/radar/source/ideas",
            "--stream",
            "odylith/compass/runtime/codex-stream.v1.jsonl",
            "--policy-mode",
            "enforce-critical",
            "--enforce-deep-skills",
            "--deep-skill-components",
            "kafka-topic",
        ]
    )
    assert rc == 2
