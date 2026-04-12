from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import sync_session
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import workstream_inference


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


def _idea_text(*, idea_id: str, title: str, promoted_to_plan: str) -> str:
    sections = "\n\n".join([f"## {name}\nBody." for name in _SECTIONS])
    return (
        "status: planning\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-03-03\n\n"
        "priority: P0\n\n"
        "commercial_value: 5\n\n"
        "product_impact: 5\n\n"
        "market_value: 5\n\n"
        "impacted_parts: traceability\n\n"
        "sizing: M\n\n"
        "complexity: High\n\n"
        "ordering_score: 90\n\n"
        "ordering_rationale: test\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        "workstream_type: standalone\n\n"
        "workstream_parent: \n\n"
        "workstream_children: \n\n"
        "workstream_depends_on: \n\n"
        "workstream_blocks: \n\n"
        "related_diagram_ids: \n\n"
        "workstream_reopens: \n\n"
        "workstream_reopened_by: \n\n"
        "workstream_split_from: \n\n"
        "workstream_split_into: \n\n"
        "workstream_merged_into: \n\n"
        "workstream_merged_from: \n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{sections}\n"
    )


def test_map_paths_to_workstreams_skips_generated_and_global_paths() -> None:
    index = {
        "B-001": {"src/odylith/runtime/surfaces/render_compass_dashboard.py", "odylith/technical-plans/in-progress/2026-03-03-sample.md"},
    }

    rows = workstream_inference.map_paths_to_workstreams(
        [
            "src/odylith/runtime/surfaces/render_compass_dashboard.py",
            "odylith/compass/compass.html",
            "odylith/atlas/source/diagram.svg",
            "odylith/radar/radar.html",
        ],
        index,
    )

    assert rows == ["B-001"]


def test_is_generated_or_global_path_treats_canonical_surface_html_as_generated() -> None:
    assert workstream_inference.is_generated_or_global_path("odylith/radar/radar.html") is True
    assert workstream_inference.is_generated_or_global_path("odylith/atlas/atlas.html") is True
    assert workstream_inference.is_generated_or_global_path("odylith/compass/compass.html") is True
    assert workstream_inference.is_generated_or_global_path("odylith/registry/registry.html") is True
    assert workstream_inference.is_generated_or_global_path("odylith/casebook/casebook.html") is True


def test_is_generated_or_global_path_treats_dashboard_shards_as_generated() -> None:
    assert workstream_inference.is_generated_or_global_path("odylith/radar/backlog-detail-shard-001.v1.js") is True
    assert workstream_inference.is_generated_or_global_path("odylith/radar/backlog-document-shard-001.v1.js") is True
    assert workstream_inference.is_generated_or_global_path("odylith/registry/registry-detail-shard-001.v1.js") is True
    assert workstream_inference.is_generated_or_global_path("odylith/tooling-payload.v1.js") is True
    assert workstream_inference.is_generated_or_global_path(
        "odylith/runtime/source/optimization-evaluation-corpus.v1.json"
    ) is True


def test_is_generated_or_global_path_applies_canonical_policy_to_bundle_source_mirrors() -> None:
    assert (
        workstream_inference.is_generated_or_global_path(
            "src/odylith/bundle/assets/odylith/atlas/source/catalog/diagrams.v1.json"
        )
        is True
    )
    assert (
        workstream_inference.is_generated_or_global_path(
            "src/odylith/bundle/assets/odylith/radar/source/INDEX.md"
        )
        is True
    )
    assert (
        workstream_inference.is_generated_or_global_path(
            "src/odylith/bundle/assets/odylith/runtime/odylith-tribunal-and-remediation-design.md"
        )
        is False
    )


def test_normalize_changed_paths_expands_bundle_source_mirrors_to_canonical_paths(tmp_path: Path) -> None:
    rows = governance.normalize_changed_paths(
        repo_root=tmp_path,
        values=[
            "src/odylith/bundle/assets/odylith/FAQ.md",
            "src/odylith/bundle/assets/project-root/.claude/settings.json",
        ],
    )

    assert "src/odylith/bundle/assets/odylith/FAQ.md" in rows
    assert "odylith/FAQ.md" in rows
    assert "src/odylith/bundle/assets/project-root/.claude/settings.json" in rows
    assert ".claude/settings.json" in rows


def test_map_paths_to_workstreams_accepts_bundle_source_mirror_aliases(tmp_path: Path) -> None:
    changed_paths = governance.normalize_changed_paths(
        repo_root=tmp_path,
        values=["src/odylith/bundle/assets/odylith/FAQ.md"],
    )

    rows = workstream_inference.map_paths_to_workstreams(
        changed_paths,
        {"B-083": {"odylith/FAQ.md"}},
    )

    assert rows == ["B-083"]


def test_collect_workstream_path_index_from_specs(tmp_path: Path) -> None:
    idea_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-03-sample.md"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(
        _idea_text(
            idea_id="B-777",
            title="Sample",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-03-sample.md",
        ),
        encoding="utf-8",
    )
    spec = backlog_contract._parse_idea_spec(idea_path)

    index = workstream_inference.collect_workstream_path_index_from_specs(
        repo_root=tmp_path,
        idea_specs={"B-777": spec},
    )

    assert "B-777" in index
    assert "odylith/radar/source/ideas/2026-03/2026-03-03-sample.md" in index["B-777"]
    assert "odylith/technical-plans/in-progress/2026-03-03-sample.md" in index["B-777"]


def test_collect_workstream_path_index_from_traceability_includes_mermaid_links(tmp_path: Path) -> None:
    idea_path = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-03-sample.md"
    idea_path.parent.mkdir(parents=True, exist_ok=True)
    idea_path.write_text(
        _idea_text(
            idea_id="B-778",
            title="Sample",
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-03-sample.md",
        ),
        encoding="utf-8",
    )

    traceability_graph = {
        "workstreams": [
            {
                "idea_id": "B-778",
                "idea_file": "odylith/radar/source/ideas/2026-03/2026-03-03-sample.md",
                "promoted_to_plan": "odylith/technical-plans/in-progress/2026-03-03-sample.md",
                "plan_traceability": {
                    "runbooks": ["consumer-runbooks/account-lifecycle.md"],
                    "developer_docs": ["docs/platform-maintainer-guide.md"],
                    "code_references": ["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
                },
            }
        ]
    }
    mermaid_catalog = {
        "diagrams": [
            {
                "diagram_id": "D-123",
                "source_mmd": "odylith/atlas/source/sample.mmd",
                "source_svg": "odylith/atlas/source/sample.svg",
                "source_png": "odylith/atlas/source/sample.png",
                "change_watch_paths": ["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
                "related_backlog": ["odylith/radar/source/ideas/2026-03/2026-03-03-sample.md"],
                "related_plans": ["odylith/technical-plans/in-progress/2026-03-03-sample.md"],
                "related_docs": ["docs/platform-maintainer-guide.md"],
                "related_code": ["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
            }
        ]
    }

    index = workstream_inference.collect_workstream_path_index_from_traceability(
        repo_root=tmp_path,
        traceability_graph=traceability_graph,
        mermaid_catalog=mermaid_catalog,
    )

    assert "B-778" in index
    refs = index["B-778"]
    assert "odylith/atlas/source/sample.mmd" in refs
    assert "docs/platform-maintainer-guide.md" in refs
    assert "src/odylith/runtime/surfaces/render_compass_dashboard.py" in refs


def test_normalize_repo_token_strips_dot_prefix() -> None:
    assert workstream_inference.normalize_repo_token("./src/odylith/runtime/surfaces/render_compass_dashboard.py") == "src/odylith/runtime/surfaces/render_compass_dashboard.py"


def test_normalize_repo_token_keeps_canonical_odylith_surface_paths() -> None:
    assert (
        workstream_inference.normalize_repo_token("odylith/radar/source/ideas/2026-03/example.md")
        == "odylith/radar/source/ideas/2026-03/example.md"
    )
    assert workstream_inference.normalize_repo_token("odylith/radar/radar.html") == "odylith/radar/radar.html"
    assert (
        workstream_inference.normalize_repo_token("odylith/atlas/source/catalog/diagrams.v1.json")
        == "odylith/atlas/source/catalog/diagrams.v1.json"
    )
    assert workstream_inference.normalize_repo_token("odylith/index.html") == "odylith/index.html"


def test_normalize_repo_token_preserves_explicit_consumer_truth_root_paths(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / ".odylith").mkdir()
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
    assert (
        workstream_inference.normalize_repo_token(
            "consumer-registry/source/components/compass/CURRENT_SPEC.md",
            repo_root=tmp_path,
        )
        == "consumer-registry/source/components/compass/CURRENT_SPEC.md"
    )
    assert (
        workstream_inference.normalize_repo_token(
            "consumer-runbooks/platform/odylith-context-engine-operations.md",
            repo_root=tmp_path,
        )
        == "consumer-runbooks/platform/odylith-context-engine-operations.md"
    )


def test_default_repo_root_token_for_cwd_accepts_claude_guidance(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / ".odylith").mkdir()

    assert workstream_inference._default_repo_root_token_for_cwd(str(tmp_path)) == str(tmp_path)  # noqa: SLF001


def test_default_repo_root_token_for_cwd_accepts_project_claude_guidance(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "CLAUDE.md").write_text("# root\n", encoding="utf-8")
    (tmp_path / ".odylith").mkdir()

    assert workstream_inference._default_repo_root_token_for_cwd(str(tmp_path)) == str(tmp_path)  # noqa: SLF001


def test_normalize_repo_token_uses_active_sync_session_repo_root_without_cwd_lookup(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)

    def _unexpected_getcwd() -> str:
        raise AssertionError("normalize_repo_token should reuse the active sync session repo root")

    monkeypatch.setattr(workstream_inference.os, "getcwd", _unexpected_getcwd)

    with sync_session.activate_sync_session(session):
        assert (
            workstream_inference.normalize_repo_token("src/odylith/runtime/governance/workstream_inference.py")
            == "src/odylith/runtime/governance/workstream_inference.py"
        )
