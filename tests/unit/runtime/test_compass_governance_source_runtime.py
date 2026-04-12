from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import release_planning_contract
from odylith.runtime.governance import sync_session
from odylith.runtime.surfaces import compass_governance_source_runtime


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
    status: str,
    promoted_to_plan: str = "",
    execution_model: str = "standard",
    workstream_type: str = "standalone",
    workstream_parent: str = "",
    workstream_children: str = "",
) -> str:
    body_sections = "\n\n".join([f"## {section}\nDetails." for section in _SECTIONS])
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-04-09\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_parts: compass\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: compass governance test fixture\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        f"promoted_to_plan: {promoted_to_plan}\n\n"
        f"execution_model: {execution_model}\n\n"
        f"workstream_type: {workstream_type}\n\n"
        f"workstream_parent: {workstream_parent}\n\n"
        f"workstream_children: {workstream_children}\n\n"
        "workstream_depends_on:\n\n"
        "workstream_blocks:\n\n"
        "related_diagram_ids: D-030\n\n"
        "workstream_reopens:\n\n"
        "workstream_reopened_by:\n\n"
        "workstream_split_from:\n\n"
        "workstream_split_into:\n\n"
        "workstream_merged_into:\n\n"
        "workstream_merged_from:\n\n"
        "supersedes:\n\n"
        "superseded_by:\n\n"
        f"{body_sections}\n"
    )


def _write_plan(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "Status: In progress\n\n"
            "Created: 2026-04-09\n\n"
            "Updated: 2026-04-09\n\n"
            "Backlog: B-072\n\n"
            "Goal: test\n\n"
            "Assumptions: test\n\n"
            "Constraints: test\n\n"
            "Reversibility: test\n\n"
            "Boundary Conditions: test\n\n"
            "Related Bugs:\n- no related bug found\n\n"
            "## Context/Problem Statement\n- [ ] test\n"
        ),
        encoding="utf-8",
    )


def _seed_governance_repo(repo_root: Path) -> None:
    (repo_root / "consumer_repo.yaml").write_text("repo: consumer\n", encoding="utf-8")
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.mkdir(parents=True, exist_ok=True)
    programs_root = repo_root / "odylith" / "radar" / "source" / "programs"
    programs_root.mkdir(parents=True, exist_ok=True)

    umbrella_plan = "odylith/technical-plans/in-progress/2026-04/2026-04-09-b-072.md"
    _write_plan(repo_root / umbrella_plan)

    (ideas_root / "2026-04-09-b-072.md").write_text(
        _idea_text(
            idea_id="B-072",
            title="Execution Governance Engine Program",
            status="implementation",
            promoted_to_plan=umbrella_plan,
            execution_model="umbrella_waves",
            workstream_type="umbrella",
            workstream_children="B-073,B-079",
        ),
        encoding="utf-8",
    )
    (ideas_root / "2026-04-09-b-073.md").write_text(
        _idea_text(
            idea_id="B-073",
            title="Task Contract, Event Ledger, and Hard-Constraint Promotion",
            status="queued",
            workstream_type="child",
            workstream_parent="B-072",
        ),
        encoding="utf-8",
    )
    (ideas_root / "2026-04-09-b-079.md").write_text(
        _idea_text(
            idea_id="B-079",
            title="Program/Wave Authoring CLI and Agent Ergonomics",
            status="queued",
            workstream_type="child",
            workstream_parent="B-072",
        ),
        encoding="utf-8",
    )

    (programs_root / "B-072.execution-waves.v1.json").write_text(
        json.dumps(
            {
                "umbrella_id": "B-072",
                "version": "v1",
                "waves": [
                    {
                        "wave_id": "W1",
                        "label": "Wave 1",
                        "status": "active",
                        "summary": "Authoring wave.",
                        "depends_on": [],
                        "primary_workstreams": ["B-073"],
                        "carried_workstreams": [],
                        "in_band_workstreams": ["B-079"],
                        "gate_refs": [],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    releases_root = repo_root / "odylith" / "radar" / "source" / "releases"
    releases_root.mkdir(parents=True, exist_ok=True)
    registry_path = releases_root / "releases.v1.json"
    registry_path.write_text(
        release_planning_contract.render_registry_document(
            releases=[
                {
                    "release_id": "release-0-1-11",
                    "status": "active",
                    "version": "0.1.11",
                    "tag": "v0.1.11",
                    "name": "",
                    "notes": "",
                    "created_utc": "2026-04-09T00:00:00Z",
                    "shipped_utc": "",
                    "closed_utc": "",
                }
            ],
            aliases={"current": "release-0-1-11"},
            updated_utc="2026-04-09T00:00:00Z",
        ),
        encoding="utf-8",
    )
    events_path = releases_root / "release-assignment-events.v1.jsonl"
    events_path.write_text(
        "".join(
            [
                release_planning_contract.render_assignment_event(
                    {
                        "action": "add",
                        "release_id": "release-0-1-11",
                        "workstream_id": "B-072",
                        "recorded_at": "2026-04-09T00:00:00Z",
                    }
                ),
                release_planning_contract.render_assignment_event(
                    {
                        "action": "add",
                        "release_id": "release-0-1-11",
                        "workstream_id": "B-073",
                        "recorded_at": "2026-04-09T00:00:01Z",
                    }
                ),
                release_planning_contract.render_assignment_event(
                    {
                        "action": "add",
                        "release_id": "release-0-1-11",
                        "workstream_id": "B-079",
                        "recorded_at": "2026-04-09T00:00:02Z",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )


def test_build_live_governance_context_prefers_live_release_and_program_source_truth(
    tmp_path: Path,
) -> None:
    _seed_governance_repo(tmp_path)

    context = compass_governance_source_runtime.build_live_governance_context(
        repo_root=tmp_path,
        traceability_graph={
            "workstreams": [
                {
                    "idea_id": "B-010",
                    "title": "Stale row",
                    "status": "implementation",
                }
            ],
            "current_release": {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "status": "active",
                "aliases": ["current"],
                "active_workstreams": [],
            },
            "releases": [
                {
                    "release_id": "release-0-1-11",
                    "display_label": "0.1.11",
                    "status": "active",
                    "aliases": ["current"],
                    "active_workstreams": [],
                }
            ],
        },
    )

    current_release = context["release_summary"]["current_release"]
    assert current_release["release_id"] == "release-0-1-11"
    assert current_release["active_workstreams"] == ["B-072", "B-073", "B-079"]

    workstream_rows = {
        str(row.get("idea_id", "")).strip(): row
        for row in context["workstream_rows"]
    }
    assert set(workstream_rows) >= {"B-072", "B-073", "B-079"}
    assert workstream_rows["B-072"]["active_release_id"] == "release-0-1-11"
    assert workstream_rows["B-073"]["active_release_id"] == "release-0-1-11"
    assert workstream_rows["B-079"]["active_release_id"] == "release-0-1-11"
    assert workstream_rows["B-072"]["related_diagram_ids"] == ["D-030"]
    assert workstream_rows["B-073"]["execution_wave_refs"]
    assert workstream_rows["B-079"]["execution_wave_refs"]

    live_traceability = context["traceability_graph"]
    assert live_traceability["current_release"]["active_workstreams"] == ["B-072", "B-073", "B-079"]

    execution_programs = context["execution_waves"]["programs"]
    assert len(execution_programs) == 1
    assert execution_programs[0]["umbrella_id"] == "B-072"
    assert execution_programs[0]["active_wave_count"] == 1
    assert execution_programs[0]["current_wave"]["wave_id"] == "W1"


def test_build_live_governance_context_reuses_active_sync_session_snapshot(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_governance_repo(tmp_path)
    build_calls = 0
    original = compass_governance_source_runtime.release_planning_view_model.build_release_view_from_repo

    def _counted_build_release_view_from_repo(*args, **kwargs):  # noqa: ANN202
        nonlocal build_calls
        build_calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        compass_governance_source_runtime.release_planning_view_model,
        "build_release_view_from_repo",
        _counted_build_release_view_from_repo,
    )
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    traceability_graph = {
        "workstreams": [
            {
                "idea_id": "B-010",
                "title": "Stale row",
                "status": "implementation",
            }
        ],
    }

    with sync_session.activate_sync_session(session):
        first = compass_governance_source_runtime.build_live_governance_context(
            repo_root=tmp_path,
            traceability_graph=traceability_graph,
        )
        second = compass_governance_source_runtime.build_live_governance_context(
            repo_root=tmp_path,
            traceability_graph=traceability_graph,
        )

    assert build_calls == 1
    assert first == second
    assert first is not second


def test_build_live_governance_context_rebuilds_after_sync_generation_bump(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001 - pytest fixture
) -> None:
    _seed_governance_repo(tmp_path)
    build_calls = 0
    original = compass_governance_source_runtime.execution_wave_view_model.build_execution_wave_view_payload

    def _counted_build_execution_wave_view_payload(*args, **kwargs):  # noqa: ANN202
        nonlocal build_calls
        build_calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(
        compass_governance_source_runtime.execution_wave_view_model,
        "build_execution_wave_view_payload",
        _counted_build_execution_wave_view_payload,
    )
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    traceability_graph = {
        "workstreams": [
            {
                "idea_id": "B-010",
                "title": "Stale row",
                "status": "implementation",
            }
        ],
    }

    with sync_session.activate_sync_session(session):
        compass_governance_source_runtime.build_live_governance_context(
            repo_root=tmp_path,
            traceability_graph=traceability_graph,
        )
        session.bump_generation(
            step_label="mutating-step",
            mutation_classes=("governance",),
            invalidated_namespaces=("compass_governance_context",),
            paths=("odylith/radar/traceability-graph.v1.json",),
        )
        compass_governance_source_runtime.build_live_governance_context(
            repo_root=tmp_path,
            traceability_graph=traceability_graph,
        )

    assert build_calls == 2
