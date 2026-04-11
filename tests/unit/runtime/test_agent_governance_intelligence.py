from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import agent_governance_intelligence as governance


def test_build_dashboard_impact_selective_mixed_surfaces(tmp_path: Path) -> None:
    impact = governance.build_dashboard_impact(
        repo_root=tmp_path,
        changed_paths=("odylith/radar/source/INDEX.md", "odylith/atlas/source/workstream-dependency-map.mmd"),
        force=False,
        impact_mode="selective",
    )
    assert impact.radar is True
    assert impact.atlas is True
    assert impact.compass is False
    assert impact.tooling_shell is True


def test_build_dashboard_impact_marks_registry_surface(tmp_path: Path) -> None:
    impact = governance.build_dashboard_impact(
        repo_root=tmp_path,
        changed_paths=("odylith/registry/source/component_registry.v1.json",),
        force=False,
        impact_mode="selective",
    )
    assert impact.registry is True
    assert impact.tooling_shell is True


def test_build_dashboard_impact_marks_casebook_surface(tmp_path: Path) -> None:
    impact = governance.build_dashboard_impact(
        repo_root=tmp_path,
        changed_paths=("odylith/casebook/bugs/INDEX.md",),
        force=False,
        impact_mode="selective",
    )
    assert impact.casebook is True
    assert impact.radar is False
    assert impact.tooling_shell is True


def test_build_dashboard_impact_marks_tooling_surface(tmp_path: Path) -> None:
    impact = governance.build_dashboard_impact(
        repo_root=tmp_path,
        changed_paths=("src/odylith/runtime/surfaces/render_tooling_dashboard.py",),
        force=False,
        impact_mode="selective",
    )
    assert impact.tooling_shell is True


def test_build_dashboard_impact_marks_registry_for_shared_component_intelligence(tmp_path: Path) -> None:
    impact = governance.build_dashboard_impact(
        repo_root=tmp_path,
        changed_paths=("src/odylith/runtime/governance/component_registry_intelligence.py",),
        force=False,
        impact_mode="selective",
    )
    assert impact.registry is True
    assert impact.tooling_shell is True


def test_collect_implementation_evidence_paths_filters_governance_noise(tmp_path: Path) -> None:
    paths = governance.collect_implementation_evidence_paths(
        repo_root=tmp_path,
        changed_paths=(
            "odylith/technical-plans/INDEX.md",
            "odylith/radar/source/INDEX.md",
            "AGENTS.md",
            "odylith/compass/compass.html",
            "odylith/casebook/casebook.html",
            "src/odylith/runtime/governance/reconcile_plan_workstream_binding.py",
            "src/odylith/runtime/governance/agent_governance_intelligence.py",
        ),
        include_git=False,
    )
    assert sorted(paths) == [
        "src/odylith/runtime/governance/agent_governance_intelligence.py",
        "src/odylith/runtime/governance/reconcile_plan_workstream_binding.py",
    ]
    assert governance.has_implementation_evidence(
        repo_root=tmp_path,
        changed_paths=tuple(paths),
        include_git=False,
    )


def test_collect_meaningful_activity_evidence_ignores_generated_only_events(tmp_path: Path) -> None:
    ideas_root = tmp_path / "odylith" / "radar" / "source" / "ideas"
    ideas_root.mkdir(parents=True, exist_ok=True)
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        {
            "version": "v1",
            "kind": "statement",
            "summary": "Generated shell refresh.",
            "artifacts": ["odylith/radar/radar.html"],
            "workstreams": ["B-101"],
        },
        {
            "version": "v1",
            "kind": "implementation",
            "summary": "Implemented orchestration path.",
            "artifacts": ["src/odylith/runtime/governance/sync_workstream_artifacts.py"],
            "workstreams": ["B-101"],
        },
        {
            "version": "v1",
            "kind": "statement",
            "summary": "Updated docs context.",
            "artifacts": ["consumer-runbooks/compass.md"],
            "workstreams": [],
        },
    ]
    stream_path.write_text(
        "\n".join(json.dumps(row) for row in lines) + "\n",
        encoding="utf-8",
    )

    evidence = governance.collect_meaningful_activity_evidence(
        repo_root=tmp_path,
        stream_path=stream_path,
    )
    assert evidence.linked_meaningful_event_count == 1
    assert evidence.unlinked_meaningful_event_count == 1
    assert evidence.linked_workstreams == ["B-101"]


def test_collect_governance_stream_actions_parses_plan_binding_and_successor(tmp_path: Path) -> None:
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        {
            "version": "v1",
            "kind": "decision",
            "summary": "Plan binding: advanced B-035 from queued to planning for odylith/technical-plans/in-progress/2026-03-03-agent-loop.md",
            "artifacts": ["odylith/technical-plans/in-progress/2026-03-03-agent-loop.md"],
            "workstreams": ["B-035"],
        },
        {
            "version": "v1",
            "kind": "implementation",
            "summary": "Phase advanced: Planning -> Implementation (Live)",
            "artifacts": ["src/odylith/runtime/governance/auto_promote_workstream_phase.py"],
            "workstreams": ["B-035"],
        },
        {
            "version": "v1",
            "kind": "decision",
            "summary": "Successor created: B-036 reopens B-034 for active plan binding",
            "artifacts": [
                "odylith/technical-plans/in-progress/2026-03-03-agent-loop.md",
                "odylith/radar/source/ideas/2026-03/2026-03-03-agent-loop-successor.md",
            ],
            "workstreams": ["B-036", "B-034"],
        },
    ]
    stream_path.write_text("\n".join(json.dumps(row) for row in lines) + "\n", encoding="utf-8")

    decisions, successors = governance.collect_governance_stream_actions(
        repo_root=tmp_path,
        stream_path=stream_path,
    )
    assert {row.action for row in decisions} == {"queued_to_planning", "planning_to_implementation"}
    assert len(successors) == 1
    assert successors[0].source_workstream == "B-034"
    assert successors[0].successor_workstream == "B-036"
    assert successors[0].linked_plan == "odylith/technical-plans/in-progress/2026-03-03-agent-loop.md"


def test_build_governance_summary_includes_component_registry_counts(tmp_path: Path) -> None:
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "compass" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    ideas_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "2026-03-04-compass-fixture.md").write_text(
        (
            "status: implementation\n\n"
            "idea_id: B-101\n\n"
            "title: Compass Fixture\n\n"
            "date: 2026-03-04\n\n"
            "priority: P1\n\n"
            "commercial_value: 4\n\n"
            "product_impact: 4\n\n"
            "market_value: 4\n\n"
            "impacted_parts: compass\n\n"
            "sizing: M\n\n"
            "complexity: Medium\n\n"
            "ordering_score: 80\n\n"
            "ordering_rationale: fixture\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan: odylith/technical-plans/in-progress/2026-03-04-compass-fixture.md\n\n"
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
            "## Problem\nBody.\n\n"
            "## Customer\nBody.\n\n"
            "## Opportunity\nBody.\n\n"
            "## Proposed Solution\nBody.\n\n"
            "## Scope\nBody.\n\n"
            "## Non-Goals\nBody.\n\n"
            "## Risks\nBody.\n\n"
            "## Dependencies\nBody.\n\n"
            "## Success Metrics\nBody.\n\n"
            "## Validation\nBody.\n\n"
            "## Rollout\nBody.\n\n"
            "## Why Now\nBody.\n\n"
            "## Product View\nBody.\n\n"
            "## Impacted Components\nBody.\n\n"
            "## Interface Changes\nBody.\n\n"
            "## Migration/Compatibility\nBody.\n\n"
            "## Test Strategy\nBody.\n\n"
            "## Open Questions\nBody.\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "technical-plans" / "in-progress").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "technical-plans" / "in-progress" / "2026-03-04-compass-fixture.md").write_text(
        "Status: In progress\n",
        encoding="utf-8",
    )
    rendered_plan = tmp_path / "odylith" / "radar" / "radar.html"
    rendered_plan.parent.mkdir(parents=True, exist_ok=True)
    rendered_plan.write_text("<html><body>B-101 rendered plan</body></html>\n", encoding="utf-8")
    spec_path.write_text(
        (
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Seed fixture. "
            "(Plan: [B-101](odylith/radar/radar.html?view=plan&workstream=B-101))\n"
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
                        "component_id": "compass",
                        "name": "Compass",
                        "kind": "composite",
                        "category": "governance_surface",
                        "qualification": "curated",
                        "aliases": ["compass"],
                        "path_prefixes": ["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
                        "workstreams": ["B-101"],
                        "diagrams": [],
                        "owner": "platform",
                        "status": "active",
                        "what_it_is": "Execution and timeline audit dashboard surface.",
                        "why_tracked": "Captures codex stream narratives for governance audits.",
                        "spec_ref": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stream_path = tmp_path / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "kind": "implementation",
                "summary": "Updated compass render wiring.",
                "workstreams": ["B-101"],
                "artifacts": ["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = governance.build_governance_summary(
        repo_root=tmp_path,
        changed_paths=("odylith/registry/source/component_registry.v1.json",),
        force=False,
        impact_mode="selective",
        stream_path=stream_path,
    )
    component_summary = payload.get("component_registry", {})
    assert isinstance(component_summary, dict)
    assert int(component_summary.get("component_count", 0) or 0) >= 1
    assert int(component_summary.get("mapped_meaningful_event_count", 0) or 0) >= 1
    assert "odylith" not in payload


def test_normalize_changed_paths_preserves_leading_dot_directories(tmp_path: Path) -> None:
    """``.claude/...`` and ``.codex/...`` must not be mangled to ``claude/...``.

    The previous ``.lstrip("./")`` idiom stripped every leading ``.`` and
    ``/`` character, which silently corrupted dotfile directories into
    broken aliases and fanned out duplicate changed-path entries.
    """

    inputs = (
        ".claude/worktrees/funny-leavitt",
        ".codex/config.toml",
        ".github/workflows/ci.yml",
        "./odylith/radar/source/INDEX.md",
    )
    normalized = governance.normalize_changed_paths(repo_root=tmp_path, values=inputs)

    assert ".claude/worktrees/funny-leavitt" in normalized
    assert ".codex/config.toml" in normalized
    assert ".github/workflows/ci.yml" in normalized
    assert "odylith/radar/source/INDEX.md" in normalized
    assert "claude/worktrees/funny-leavitt" not in normalized
    assert "codex/config.toml" not in normalized
    assert "github/workflows/ci.yml" not in normalized


def test_normalize_changed_paths_fans_out_bundle_mirror_aliases(tmp_path: Path) -> None:
    """Bundle-mirror inputs must alias to both bundle and source-of-truth forms
    without ever minting a broken dot-stripped variant."""

    inputs = (
        "src/odylith/bundle/assets/project-root/.claude/agents/test.md",
        "src/odylith/bundle/assets/odylith/radar/source/INDEX.md",
    )
    normalized = governance.normalize_changed_paths(repo_root=tmp_path, values=inputs)

    assert "src/odylith/bundle/assets/project-root/.claude/agents/test.md" in normalized
    assert ".claude/agents/test.md" in normalized
    assert "claude/agents/test.md" not in normalized
    assert "src/odylith/bundle/assets/odylith/radar/source/INDEX.md" in normalized
    assert "odylith/radar/source/INDEX.md" in normalized


def test_collect_git_changed_paths_skips_nested_worktree_copies(tmp_path: Path) -> None:
    """Paths whose ancestor carries a ``.git`` marker must be excluded.

    A bundled copy of a nested git worktree (for example
    ``src/odylith/bundle/assets/project-root/.claude/worktrees/<slug>``)
    used to pollute the changed-path set and fan out broken aliases for
    every file beneath it. The nested-worktree guard must skip that tree
    even when its ``.git`` marker is a file starting with ``gitdir:``.
    """

    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        check=True,
    )

    # Make the repo non-empty so porcelain output is well-formed.
    (tmp_path / "real.txt").write_text("real\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "real.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "seed"],
        check=True,
    )

    # Synthesize a bundled-worktree-copy tree whose root carries a
    # ``gitdir:`` marker, just like the checked-in bundle copy of a
    # registered worktree.
    nested_root = tmp_path / "src" / "odylith" / "bundle" / "assets" / "project-root" / ".claude" / "worktrees" / "nested"
    nested_root.mkdir(parents=True)
    (nested_root / ".git").write_text(
        "gitdir: /absolute/path/outside/repo/.git/worktrees/nested\n",
        encoding="utf-8",
    )
    (nested_root / "noise.md").write_text("pretend payload\n", encoding="utf-8")

    rows = governance.collect_git_changed_paths(repo_root=tmp_path)
    assert not any("worktrees/nested" in row for row in rows), rows
    assert not any("claude/worktrees/nested" in row for row in rows), rows
