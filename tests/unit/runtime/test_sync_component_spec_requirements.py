from __future__ import annotations

import json
from pathlib import Path
import subprocess

from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import sync_component_spec_requirements as sync


def _write_spec(path: Path, *, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            f"# {title}\n"
            "Last updated: 2026-03-27\n\n"
            "## Current Capability Baseline\n"
            "Seed fixture.\n\n"
            "## Feature History\n"
            "- 2026-03-27: Seeded sync fixture. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )


def _write_registry_inputs(tmp_path: Path, *, components: list[dict[str, object]], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"version": "v1", "components": components}, indent=2) + "\n",
        encoding="utf-8",
    )
    catalog_path = tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps({"version": "1.0", "diagrams": []}, indent=2) + "\n", encoding="utf-8")
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_root.mkdir(parents=True, exist_ok=True)
    (ideas_root / "2026-03-27-example.md").write_text(
        (
            "status: planning\n\n"
            "idea_id: B-901\n\n"
            "title: Example\n\n"
            "date: 2026-03-27\n\n"
            "priority: P0\n\n"
            "commercial_value: 5\n\n"
            "product_impact: 5\n\n"
            "market_value: 5\n\n"
            "impacted_lanes: both\n\n"
            "impacted_parts: x\n\n"
            "sizing: S\n\n"
            "complexity: Low\n\n"
            "ordering_score: 100\n\n"
            "ordering_rationale: x\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan: odylith/technical-plans/in-progress/2026-03-27-example.md\n\n"
            "workstream_type: standalone\n\n"
            "workstream_parent:\n\n"
            "workstream_children:\n\n"
            "workstream_depends_on:\n\n"
            "workstream_blocks:\n\n"
            "related_diagram_ids:\n\n"
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
            "## Impacted Components\n`Transactional Runtime`\n`Service Auth`\n\n"
            "## Interface Changes\nBody\n\n"
            "## Migration/Compatibility\nBody\n\n"
            "## Test Strategy\nBody\n\n"
            "## Open Questions\nBody\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "radar" / "radar.html").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar" / "radar.html").write_text("<html></html>\n", encoding="utf-8")
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")


def _component_entry(*, component_id: str, spec_ref: str) -> component_registry.ComponentEntry:
    return component_registry.ComponentEntry(
        component_id=component_id,
        name=component_id.title(),
        kind="composite",
        category="governance_surface",
        qualification="curated",
        aliases=[],
        path_prefixes=[spec_ref],
        workstreams=["B-901"],
        diagrams=[],
        owner="platform",
        status="active",
        what_it_is="Fixture component.",
        why_tracked="Fixture coverage.",
        spec_ref=spec_ref,
        sources=[],
    )


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Codex"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True, text=True)


def test_resolve_forensics_path_keeps_product_dossier_layout(tmp_path: Path) -> None:
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "registry" / "CURRENT_SPEC.md"
    entry = _component_entry(
        component_id="registry",
        spec_ref="odylith/registry/source/components/registry/CURRENT_SPEC.md",
    )

    assert sync._resolve_forensics_path(entry=entry, spec_path=spec_path) == spec_path.parent / "FORENSICS.v1.json"


def test_sync_component_spec_requirements_consumer_specs_use_per_component_sidecars_and_prune_legacy_file(
    tmp_path: Path,
) -> None:
    specs_root = tmp_path / "consumer-registry" / "source" / "components"
    runtime_spec = specs_root / "transactional-runtime" / "CURRENT_SPEC.md"
    auth_spec = specs_root / "service-auth" / "CURRENT_SPEC.md"
    _write_spec(runtime_spec, title="Transactional Runtime")
    _write_spec(auth_spec, title="Service Auth")

    manifest_path = tmp_path / "consumer-registry" / "source" / "component_registry.v1.json"
    _write_registry_inputs(
        tmp_path,
        manifest_path=manifest_path,
        components=[
            {
                "component_id": "transactional-runtime",
                "name": "Transactional Runtime",
                "kind": "composite",
                "category": "governance_surface",
                "qualification": "curated",
                "aliases": [],
                "path_prefixes": ["consumer-registry/source/components/transactional-runtime/CURRENT_SPEC.md"],
                "workstreams": ["B-901"],
                "diagrams": [],
                "owner": "platform",
                "status": "active",
                "what_it_is": "Runtime surface.",
                "why_tracked": "Runtime fixture.",
                "spec_ref": "consumer-registry/source/components/transactional-runtime/CURRENT_SPEC.md",
            },
            {
                "component_id": "service-auth",
                "name": "Service Auth",
                "kind": "composite",
                "category": "governance_surface",
                "qualification": "curated",
                "aliases": [],
                "path_prefixes": ["consumer-registry/source/components/service-auth/CURRENT_SPEC.md"],
                "workstreams": ["B-901"],
                "diagrams": [],
                "owner": "platform",
                "status": "active",
                "what_it_is": "Auth surface.",
                "why_tracked": "Auth fixture.",
                "spec_ref": "consumer-registry/source/components/service-auth/CURRENT_SPEC.md",
            },
        ],
    )

    legacy_flat_forensics = specs_root / "FORENSICS.v1.json"
    legacy_flat_forensics.write_text('{"component_id":"poison"}\n', encoding="utf-8")

    base_argv = [
        "--repo-root",
        str(tmp_path),
        "--manifest",
        "consumer-registry/source/component_registry.v1.json",
        "--catalog",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "--ideas-root",
        "odylith/radar/source/ideas",
        "--stream",
        "odylith/compass/runtime/codex-stream.v1.jsonl",
    ]

    assert sync.main([*base_argv, "--check-only"]) == 2
    assert sync.main(base_argv) == 0

    runtime_forensics = specs_root / "transactional-runtime" / "FORENSICS.v1.json"
    auth_forensics = specs_root / "service-auth" / "FORENSICS.v1.json"
    assert runtime_forensics.is_file()
    assert auth_forensics.is_file()
    assert legacy_flat_forensics.exists() is False

    assert json.loads(runtime_forensics.read_text(encoding="utf-8"))["component_id"] == "transactional-runtime"
    assert json.loads(auth_forensics.read_text(encoding="utf-8"))["component_id"] == "service-auth"

    assert sync.main([*base_argv, "--check-only"]) == 0


def test_sync_component_spec_requirements_records_workspace_activity_from_source_owned_bundle_mirror(
    tmp_path: Path,
) -> None:
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "tribunal" / "CURRENT_SPEC.md"
    _write_spec(spec_path, title="Tribunal")
    canonical_doc = tmp_path / "odylith" / "runtime" / "odylith-tribunal-and-remediation-design.md"
    canonical_doc.parent.mkdir(parents=True, exist_ok=True)
    canonical_doc.write_text("# Tribunal Design\n\nCanonical source doc.\n", encoding="utf-8")
    mirror_doc = tmp_path / "src" / "odylith" / "bundle" / "assets" / "odylith" / "runtime" / "odylith-tribunal-and-remediation-design.md"
    mirror_doc.parent.mkdir(parents=True, exist_ok=True)
    mirror_doc.write_text("# Tribunal Design\n\nBundled source mirror.\n", encoding="utf-8")

    manifest_path = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    _write_registry_inputs(
        tmp_path,
        manifest_path=manifest_path,
        components=[
            {
                "component_id": "tribunal",
                "name": "Tribunal",
                "kind": "runtime",
                "category": "governance_engine",
                "qualification": "curated",
                "aliases": ["diagnosis-engine"],
                "path_prefixes": [
                    "src/odylith/runtime/reasoning/tribunal_engine.py",
                    "odylith/runtime/odylith-tribunal-and-remediation-design.md",
                ],
                "workstreams": ["B-901"],
                "diagrams": [],
                "owner": "product",
                "status": "active",
                "what_it_is": "Diagnosis engine.",
                "why_tracked": "Tribunal fixture.",
                "spec_ref": "odylith/registry/source/components/tribunal/CURRENT_SPEC.md",
            }
        ],
    )

    _init_git_repo(tmp_path)
    mirror_doc.write_text(
        mirror_doc.read_text(encoding="utf-8") + "\nMirror-only forensic activity.\n",
        encoding="utf-8",
    )

    base_argv = [
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

    assert sync.main(base_argv) == 0

    forensics_path = tmp_path / "odylith" / "registry" / "source" / "components" / "tribunal" / "FORENSICS.v1.json"
    payload = json.loads(forensics_path.read_text(encoding="utf-8"))
    assert payload["forensic_coverage"]["status"] == "forensic_coverage_present"
    assert payload["forensic_coverage"]["explicit_event_count"] == 0
    assert payload["forensic_coverage"]["recent_path_match_count"] == 1
    assert payload["timeline"][0]["kind"] == "workspace_activity"
