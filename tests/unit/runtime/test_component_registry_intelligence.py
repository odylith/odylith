from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.governance import sync_session


def _seed_registry_repo(root: Path) -> None:
    profile_path = root / ".odylith" / "consumer-profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "consumer_id": root.name,
                "truth_roots": {
                    "casebook_bugs": "odylith/casebook/bugs",
                    "component_registry": "odylith/registry/source/component_registry.v1.json",
                    "component_specs": "odylith/registry/source/components",
                    "radar_source": "odylith/radar/source",
                    "runbooks": "docs/runbooks",
                    "technical_plans": "odylith/technical-plans",
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

    manifest_path = root / "odylith" / "registry" / "source" / "component_registry.v1.json"
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
                        "product_layer": "evidence_surface",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    spec_path = root / "odylith" / "registry" / "source" / "components" / "radar" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        (
            "# Radar Component Spec\n\n"
            "Last updated: 2026-04-12\n\n"
            "## Feature History\n"
            "- 2026-04-12: Seeded radar registry fixture. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )

    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "diagrams": [
                    {
                        "diagram_id": "D-100",
                        "title": "Radar Example",
                        "components": [{"name": "Radar", "description": "Dashboard"}],
                        "related_workstreams": ["B-901"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    idea_path = root / "odylith" / "radar" / "source" / "ideas" / "2026-04" / "2026-04-12-example.md"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(
        (
            "status: planning\n\n"
            "idea_id: B-901\n\n"
            "title: Registry Example\n\n"
            "date: 2026-04-12\n\n"
            "priority: P0\n\n"
            "commercial_value: 5\n\n"
            "product_impact: 5\n\n"
            "market_value: 5\n\n"
            "impacted_parts: registry\n\n"
            "sizing: M\n\n"
            "complexity: High\n\n"
            "ordering_score: 100\n\n"
            "ordering_rationale: fixture\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan: odylith/technical-plans/in-progress/2026-04-12-example.md\n\n"
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
            "## Problem\nComponent registry fixtures need meaningful Radar detail for validation.\n\n"
            "## Customer\nMaintainers depend on these fixtures to model real registry governance.\n\n"
            "## Opportunity\nMeaningful fixture prose keeps component validation aligned with Radar truth.\n\n"
            "## Proposed Solution\nBody\n\n"
            "## Scope\nBody\n\n"
            "## Non-Goals\nBody\n\n"
            "## Risks\nBody\n\n"
            "## Dependencies\nBody\n\n"
            "## Success Metrics\n- Registry fixtures validate without placeholder detail.\n- Component mapping remains testable.\n\n"
            "## Validation\nBody\n\n"
            "## Rollout\nBody\n\n"
            "## Why Now\nBody\n\n"
            "## Product View\nThe registry intelligence path should reject weak ideas without breaking valid fixtures.\n\n"
            "## Impacted Components\nBody\n\n"
            "## Interface Changes\nBody\n\n"
            "## Migration/Compatibility\nBody\n\n"
            "## Test Strategy\nBody\n\n"
            "## Open Questions\nBody\n"
        ),
        encoding="utf-8",
    )

    stream_path = root / ".odylith" / "state" / "agent-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text("", encoding="utf-8")


def test_build_component_registry_report_reuses_active_sync_session(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _seed_registry_repo(tmp_path)
    build_calls = 0
    original = registry._build_component_registry_report_from_fingerprint  # noqa: SLF001

    def _counted_build(**kwargs):  # noqa: ANN202
        nonlocal build_calls
        build_calls += 1
        return original(**kwargs)

    monkeypatch.setattr(registry, "_build_component_registry_report_from_fingerprint", _counted_build)

    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    with sync_session.activate_sync_session(session):
        first = registry.build_component_registry_report(repo_root=tmp_path)
        second = registry.build_component_registry_report(repo_root=tmp_path)

    assert first.components.keys() == second.components.keys()
    assert build_calls == 1


def test_component_index_fingerprint_tracks_radar_idea_contract_version(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _seed_registry_repo(tmp_path)
    repo_root = tmp_path.resolve()
    manifest = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    ideas = repo_root / "odylith" / "radar" / "source" / "ideas"

    assert registry.backlog_contract.IDEA_SPEC_CACHE_VERSION in registry._RADAR_IDEA_CONTRACT_VERSION  # noqa: SLF001
    _cache_path, baseline = registry._cached_component_index_payload(  # noqa: SLF001
        repo_root=repo_root,
        manifest_path=manifest,
        catalog_path=catalog,
        ideas_root=ideas,
        include_idea_candidates=False,
    )
    monkeypatch.setattr(
        registry,
        "_RADAR_IDEA_CONTRACT_VERSION",
        f"{registry._RADAR_IDEA_CONTRACT_VERSION}:next",  # noqa: SLF001
    )
    _cache_path, changed = registry._cached_component_index_payload(  # noqa: SLF001
        repo_root=repo_root,
        manifest_path=manifest,
        catalog_path=catalog,
        ideas_root=ideas,
        include_idea_candidates=False,
    )

    assert changed != baseline


def test_match_by_artifact_uses_nested_path_prefixes_and_spec_refs() -> None:
    components = {
        "radar": registry.ComponentEntry(
            component_id="radar",
            name="Radar",
            kind="composite",
            category="governance_surface",
            qualification="curated",
            aliases=[],
            path_prefixes=["src/odylith/runtime/surfaces/render_backlog_ui.py"],
            workstreams=[],
            diagrams=[],
            owner="platform",
            status="active",
            what_it_is="Backlog radar surface.",
            why_tracked="Tracks backlog rendering.",
            spec_ref="odylith/registry/source/components/radar/CURRENT_SPEC.md",
            sources=["manifest"],
        ),
        "registry": registry.ComponentEntry(
            component_id="registry",
            name="Registry",
            kind="composite",
            category="governance_surface",
            qualification="curated",
            aliases=[],
            path_prefixes=["src/odylith/runtime/surfaces/render_registry_dashboard.py"],
            workstreams=[],
            diagrams=[],
            owner="platform",
            status="active",
            what_it_is="Registry surface.",
            why_tracked="Tracks component registry rendering.",
            spec_ref="odylith/registry/source/components/registry/CURRENT_SPEC.md",
            sources=["manifest"],
        ),
    }

    matched = registry._match_by_artifact(  # noqa: SLF001
        artifacts=[
            "src/odylith/runtime/surfaces/render_backlog_ui.py",
            "odylith/registry/source/components/registry/CURRENT_SPEC.md",
        ],
        components=components,
    )

    assert matched == {"radar", "registry"}


def test_normalize_workspace_activity_path_preserves_raw_bundle_source_mirror_tokens(tmp_path: Path) -> None:
    normalized = registry._normalize_workspace_activity_path(  # noqa: SLF001
        repo_root=tmp_path,
        token="src/odylith/bundle/assets/odylith/radar/source/INDEX.md",
    )

    assert normalized == "src/odylith/bundle/assets/odylith/radar/source/INDEX.md"


def test_collect_recent_workspace_paths_dedupes_bundle_source_mirror_aliases(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    changed_path = tmp_path / "odylith" / "radar" / "source" / "INDEX.md"
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("# Radar\n", encoding="utf-8")

    monkeypatch.setattr(
        registry,
        "is_meaningful_workspace_artifact",
        lambda token, *, repo_root=None: str(token) == "odylith/radar/source/INDEX.md",
    )
    monkeypatch.setattr(
        "odylith.runtime.governance.agent_governance_intelligence.collect_git_changed_paths",
        lambda *, repo_root: [
            "src/odylith/bundle/assets/odylith/radar/source/INDEX.md",
            "odylith/radar/source/INDEX.md",
        ],
    )

    rows = registry._collect_recent_workspace_paths(  # noqa: SLF001
        repo_root=tmp_path,
        window_hours=48,
        now=dt.datetime.now().astimezone(),
    )

    assert len(rows) == 1
    assert rows[0][0] == "odylith/radar/source/INDEX.md"
