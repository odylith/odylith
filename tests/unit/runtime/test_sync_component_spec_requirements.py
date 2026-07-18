from __future__ import annotations

import hashlib
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
            "## Problem\nComponent spec sync fixtures need realistic Radar detail.\n\n"
            "## Customer\nMaintainers validating component requirements across consumer registries.\n\n"
            "## Opportunity\nMeaningful fixture prose keeps spec sync aligned with Radar validation.\n\n"
            "## Proposed Solution\nBody\n\n"
            "## Scope\nBody\n\n"
            "## Non-Goals\nBody\n\n"
            "## Risks\nBody\n\n"
            "## Dependencies\nBody\n\n"
            "## Success Metrics\n- Component spec sync validates fixture Radar truth.\n- Forensics sidecars remain deterministic.\n\n"
            "## Validation\nBody\n\n"
            "## Rollout\nBody\n\n"
            "## Why Now\nBody\n\n"
            "## Product View\nSpec sync should reject weak ideas without breaking valid fixture repositories.\n\n"
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


def test_clean_requirement_summary_scrubs_consumer_repo_names() -> None:
    legacy_consumer_repo = "den" + "toai-" + "ori" + "on"

    assert sync._clean_requirement_summary(
        summary=f"CB-149 update measured 25.40s in {legacy_consumer_repo} before the fast path.",
        kind="implementation",
    ) == "CB-149 update measured 25.40s in a real consumer repo before the fast path."


def test_requirements_trace_projection_does_not_copy_scenario_terms() -> None:
    event = component_registry.MappedEvent(
        event_index=12,
        ts_iso="2026-07-03T01:47:31-07:00",
        kind="implementation",
        summary=(
            "Exact municipal stormwater plus tribal consultation source-local "
            "replays wrote clean governed records."
        ),
        workstreams=["B-142"],
        artifacts=[
            "/tmp/municipal-stormwater/proof.json",
            "/tmp/tribal-consultation/proof.json",
        ],
        explicit_components=["domain-intelligence"],
        mapped_components=["domain-intelligence"],
        confidence="high",
        meaningful=True,
    )

    rows = sync._build_generated_requirement_lines(
        events=[event],
        fallback_date="2026-07-03",
        max_events=6,
    )
    rendered = "\n".join(rows).lower()

    assert "implementation evidence linked this component to governed work" in rendered
    assert "2 verifiable artifact references" in rendered
    assert "sha256:" in rendered
    assert "municipal" not in rendered
    assert "stormwater" not in rendered
    assert "tribal" not in rendered
    assert "consultation" not in rendered


def test_forensics_payload_keeps_timeline_rows_scenario_neutral() -> None:
    entry = _component_entry(
        component_id="release",
        spec_ref="odylith/registry/source/components/release/CURRENT_SPEC.md",
    )
    coverage = component_registry.ComponentForensicCoverage(
        status="forensic_coverage_present",
        timeline_event_count=1,
        explicit_event_count=1,
        recent_path_match_count=0,
        mapped_workstream_evidence_count=1,
        spec_history_event_count=0,
        empty_reasons=[],
    )
    event = component_registry.MappedEvent(
        event_index=7,
        ts_iso="2026-06-30T12:00:00-07:00",
        kind="statement",
        summary="Quantum tunneling scenario passed while shelter capacity failed.",
        workstreams=["B-142"],
        artifacts=["/tmp/quantum-tunneling/proof.json"],
        explicit_components=["release"],
        mapped_components=["release"],
        confidence="high",
        meaningful=True,
    )

    payload = sync._forensics_payload(
        entry=entry,
        coverage=coverage,
        timeline=[event],
        traceability={"runbooks": [], "developer_docs": [], "code_references": []},
    )

    row = payload["timeline"][0]
    assert row["summary"] == (
        "Timeline evidence linked this component to governed work. "
        "workstream scope preserved; 1 verifiable artifact reference."
    )
    assert row["artifacts"] == [
        "sha256:" + hashlib.sha256(b"/tmp/quantum-tunneling/proof.json").hexdigest()
    ]
    assert "quantum" not in json.dumps(payload).lower()
    assert "shelter" not in json.dumps(payload).lower()


def test_forensics_payload_preserves_safe_repo_artifact_paths() -> None:
    event = component_registry.MappedEvent(
        event_index=8,
        ts_iso="2026-07-18T08:42:07-07:00",
        kind="implementation",
        summary="Installed proof completed.",
        workstreams=[],
        artifacts=[
            "src/odylith/runtime/domain_intelligence/greenfield_create_commit.py",
            "scripts/release/greenfield_commit_recovery_proof.py",
        ],
        explicit_components=["domain-intelligence", "release"],
        mapped_components=["domain-intelligence", "release"],
        confidence="high",
        meaningful=True,
    )

    rows = sync._build_generated_requirement_lines(
        events=[event],
        fallback_date="2026-07-18",
        max_events=6,
    )
    payload = sync._forensics_payload(
        entry=_component_entry(
            component_id="domain-intelligence",
            spec_ref="odylith/registry/source/components/domain-intelligence/CURRENT_SPEC.md",
        ),
        coverage=component_registry.ComponentForensicCoverage(
            status="forensic_coverage_present",
            timeline_event_count=1,
            explicit_event_count=1,
            recent_path_match_count=0,
            mapped_workstream_evidence_count=1,
            spec_history_event_count=0,
            empty_reasons=[],
        ),
        timeline=[event],
        traceability={"runbooks": [], "developer_docs": [], "code_references": []},
    )

    rendered = "\n".join(rows)
    assert "`src/odylith/runtime/domain_intelligence/greenfield_create_commit.py`" in rendered
    assert "`scripts/release/greenfield_commit_recovery_proof.py`" in rendered
    assert "plus -" not in rendered
    assert payload["timeline"][0]["artifacts"] == event.artifacts


def test_artifact_evidence_reference_canonicalizes_and_hashes_unsafe_paths() -> None:
    safe_path = "src/odylith/runtime/governance/sync_component_spec_requirements.py"
    unsafe_hash = "sha256:" + hashlib.sha256(b"tmp/proof.json").hexdigest()
    traversed_hash = "sha256:" + hashlib.sha256(b"../tmp/tribal-consultation/proof.json").hexdigest()

    assert sync._artifact_evidence_reference(safe_path) == safe_path  # noqa: SLF001
    assert (
        sync._artifact_evidence_reference("src/../src/odylith/runtime/governance/sync_component_spec_requirements.py")
        == safe_path
    )  # noqa: SLF001
    assert sync._artifact_evidence_reference("./tmp/proof.json") == unsafe_hash  # noqa: SLF001
    assert sync._artifact_evidence_reference("tmp/proof.json") == unsafe_hash  # noqa: SLF001
    assert sync._artifact_evidence_reference(r"C:\tmp\proof.json") == sync._artifact_evidence_reference("C:/tmp/proof.json")  # noqa: SLF001
    assert sync._artifact_evidence_reference("src/../../tmp/tribal-consultation/proof.json") == traversed_hash  # noqa: SLF001
    assert sync._artifact_evidence_reference("scripts/../tmp/municipal-stormwater/proof.json").startswith("sha256:")  # noqa: SLF001
    assert sync._artifact_evidence_references(["", "   "]) == []  # noqa: SLF001


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


def test_sync_component_spec_requirements_excludes_workspace_activity_from_persisted_forensics(
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

    live_report = component_registry.build_component_registry_report(
        repo_root=tmp_path,
        manifest_path=manifest_path,
        catalog_path=tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json",
        ideas_root=tmp_path / "odylith" / "radar" / "source" / "ideas",
        stream_path=tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl",
    )
    live_timeline = component_registry.build_component_timelines(
        component_index=live_report.components,
        mapped_events=live_report.mapped_events,
    )["tribunal"]
    assert [event.kind for event in live_timeline] == ["workspace_activity"]
    assert live_report.forensic_coverage["tribunal"].recent_path_match_count == 1

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
    assert payload["forensic_coverage"]["status"] == "baseline_forensic_only"
    assert payload["forensic_coverage"]["explicit_event_count"] == 0
    assert payload["forensic_coverage"]["recent_path_match_count"] == 0
    assert payload["timeline"] == []

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "sync forensics"], cwd=tmp_path, check=True, capture_output=True, text=True)

    assert sync.main([*base_argv, "--check-only"]) == 0
