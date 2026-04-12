from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from odylith.runtime.governance import auto_promote_workstream_phase as promoter


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


def _seed_component_registry(root: Path) -> None:
    spec_dir = root / "odylith" / "registry" / "source" / "components" / "governance-engine"
    spec_dir.mkdir(parents=True, exist_ok=True)
    plan_page = root / "odylith" / "radar" / "radar.html"
    plan_page.parent.mkdir(parents=True, exist_ok=True)
    plan_page.write_text("<html><body>B-901</body></html>\n", encoding="utf-8")
    (spec_dir / "CURRENT_SPEC.md").write_text(
        (
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Seed fixture. "
            "(Plan: [B-901](odylith/radar/radar.html?view=plan&workstream=B-901))\n"
        ),
        encoding="utf-8",
    )
    contracts_dir = root / "odylith" / "registry" / "source"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    (contracts_dir / "component_registry.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "components": [
                    {
                        "component_id": "governance-engine",
                        "name": "Governance Engine",
                        "kind": "system",
                        "category": "governance_engine",
                        "qualification": "curated",
                        "aliases": ["governance", "plan-binding"],
                        "path_prefixes": [
                            "src/odylith/runtime/governance/auto_promote_workstream_phase.py",
                            "src/odylith/runtime/surfaces/render_compass_dashboard.py",
                            "odylith/radar/source/INDEX.md",
                            "odylith/technical-plans/",
                            "odylith/radar/source/ideas/",
                        ],
                        "workstreams": ["B-901"],
                        "diagrams": [],
                        "owner": "platform",
                        "status": "active",
                        "what_it_is": "Governance phase automation and binding control logic.",
                        "why_tracked": "Captures policy-driven workflow state transitions.",
                        "spec_ref": "odylith/registry/source/components/governance-engine/CURRENT_SPEC.md",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _idea_text(
    *,
    idea_id: str,
    title: str,
    status: str,
    promoted_to_plan: str,
) -> str:
    body_sections = "\n\n".join([f"## {section}\nDetails." for section in _SECTIONS])
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-03-03\n\n"
        "priority: P0\n\n"
        "commercial_value: 5\n\n"
        "product_impact: 5\n\n"
        "market_value: 5\n\n"
        "impacted_parts: workstream phase promotion\n\n"
        "sizing: L\n\n"
        "complexity: High\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: phase promotion test\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        "workstream_type: standalone\n\n"
        "workstream_parent: \n\n"
        "workstream_children: none\n\n"
        "workstream_depends_on: \n\n"
        "workstream_blocks: \n\n"
        "workstream_reopens: \n\n"
        "workstream_reopened_by: \n\n"
        "workstream_split_from: \n\n"
        "workstream_split_into: \n\n"
        "workstream_merged_into: \n\n"
        "workstream_merged_from: \n\n"
        "related_diagram_ids: \n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{body_sections}\n"
    )


def _seed_repo(*, root: Path, status: str) -> tuple[Path, Path, Path]:
    (root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    _seed_component_registry(root)
    ideas_dir = root / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    plan_dir = root / "odylith" / "technical-plans" / "in-progress"
    plan_dir.mkdir(parents=True, exist_ok=True)
    stream_path = root / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)

    plan_path = plan_dir / "2026-03-03-workstream-lineage.md"
    plan_path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-03-03\n\n"
            "Updated: 2026-03-03\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "## Context/Problem Statement\n- [ ] test\n"
        ),
        encoding="utf-8",
    )

    idea_path = ideas_dir / "2026-03-03-workstream-lineage.md"
    idea_path.write_text(
        _idea_text(
            idea_id="B-901",
            title="Lineage Promotion Test",
            status=status,
            promoted_to_plan="odylith/technical-plans/in-progress/2026-03-03-workstream-lineage.md",
        ),
        encoding="utf-8",
    )

    backlog_index = root / "odylith" / "radar" / "source" / "INDEX.md"
    backlog_index.parent.mkdir(parents=True, exist_ok=True)
    backlog_index.write_text(
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-03-03\n\n"
            "## Ranked Active Backlog\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| - | B-901 | Lineage Promotion Test | P0 | 100 | 5 | 5 | 5 | L | High | {status} | [lineage]({idea_path}) |\n\n"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
            "## Reorder Rationale Log\n\n"
            "### B-901 (rank -)\n"
            "- why now: test.\n"
            "- expected outcome: test.\n"
            "- tradeoff: test.\n"
            "- deferred for now: test.\n"
            "- ranking basis: test.\n"
        ),
        encoding="utf-8",
    )

    return idea_path, backlog_index, stream_path


def _append_stream_event(
    *,
    stream_path: Path,
    kind: str,
    summary: str,
    workstreams: list[str],
    artifacts: list[str],
    ts_iso: str,
) -> None:
    payload = {
        "version": "v1",
        "kind": kind,
        "summary": summary,
        "ts_iso": ts_iso,
        "author": "codex",
        "source": "codex",
        "workstreams": workstreams,
        "artifacts": artifacts,
    }
    with stream_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def test_auto_promote_promotes_planning_workstream_with_decision_signal(tmp_path: Path) -> None:
    idea_path, backlog_index, stream_path = _seed_repo(root=tmp_path, status="planning")
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    _append_stream_event(
        stream_path=stream_path,
        kind="decision",
        summary="Decision: begin implementation on lineage promotion.",
        workstreams=["B-901"],
        artifacts=["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
        ts_iso=now_iso,
    )

    rc = promoter.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    idea_text = idea_path.read_text(encoding="utf-8")
    assert "status: implementation" in idea_text

    index_text = backlog_index.read_text(encoding="utf-8")
    assert "| High | implementation |" in index_text

    rows = [json.loads(line) for line in stream_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[-1]["summary"] == "Phase advanced: Planning -> Implementation (Live)"
    assert rows[-1]["workstreams"] == ["B-901"]


def test_auto_promote_skips_generated_only_activity(tmp_path: Path) -> None:
    idea_path, backlog_index, stream_path = _seed_repo(root=tmp_path, status="planning")
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    _append_stream_event(
        stream_path=stream_path,
        kind="implementation",
        summary="Rendered generated dashboards only.",
        workstreams=["B-901"],
        artifacts=["odylith/compass/compass.html", "odylith/radar/radar.html"],
        ts_iso=now_iso,
    )

    rc = promoter.main(["--repo-root", str(tmp_path)])
    assert rc == 0

    idea_text = idea_path.read_text(encoding="utf-8")
    assert "status: planning" in idea_text
    index_text = backlog_index.read_text(encoding="utf-8")
    assert "| High | planning |" in index_text
    rows = [json.loads(line) for line in stream_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1


def test_auto_promote_never_demotes_existing_implementation(tmp_path: Path) -> None:
    idea_path, backlog_index, stream_path = _seed_repo(root=tmp_path, status="implementation")
    stale_iso = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).isoformat(timespec="seconds")
    _append_stream_event(
        stream_path=stream_path,
        kind="implementation",
        summary="Old implementation event outside active window.",
        workstreams=["B-901"],
        artifacts=["src/odylith/runtime/surfaces/render_compass_dashboard.py"],
        ts_iso=stale_iso,
    )

    rc = promoter.main(["--repo-root", str(tmp_path), "--active-window-minutes", "15"])
    assert rc == 0

    idea_text = idea_path.read_text(encoding="utf-8")
    assert "status: implementation" in idea_text
    index_text = backlog_index.read_text(encoding="utf-8")
    assert "| High | implementation |" in index_text
    rows = [json.loads(line) for line in stream_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
