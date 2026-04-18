"""Regression coverage for Compass release-truth drift detection."""

from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.governance import release_truth_runtime


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


def _idea_text(*, idea_id: str, title: str, status: str) -> str:
    """Build a synthetic idea markdown fixture with all required sections."""
    sections = "\n\n".join(
        f"## {section}\nGrounded fixture coverage for {section.lower()} in this synthetic workstream."
        for section in _SECTIONS
    )
    return (
        f"status: {status}\n\n"
        f"idea_id: {idea_id}\n\n"
        f"title: {title}\n\n"
        "date: 2026-04-09\n\n"
        "priority: P1\n\n"
        "commercial_value: 4\n\n"
        "product_impact: 4\n\n"
        "market_value: 4\n\n"
        "impacted_parts: release truth\n\n"
        "sizing: M\n\n"
        "complexity: Medium\n\n"
        "ordering_score: 100\n\n"
        "ordering_rationale: test fixture\n\n"
        "confidence: high\n\n"
        "founder_override: no\n\n"
        "promoted_to_plan:\n\n"
        "execution_model: standard\n\n"
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
        f"{sections}\n"
    )


def _seed_release_truth_repo(repo_root: Path) -> None:
    """Seed a minimal release-truth fixture repo for drift tests."""
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.mkdir(parents=True, exist_ok=True)
    ideas_root.joinpath("2026-04-09-b-067.md").write_text(
        _idea_text(
            idea_id="B-067",
            title="Context Engine Module Decomposition and Boundary Hardening",
            status="finished",
        ),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-09-b-068.md").write_text(
        _idea_text(
            idea_id="B-068",
            title="Context Engine Benchmark Family and Grounding Quality Gates",
            status="implementation",
        ),
        encoding="utf-8",
    )
    releases_root = repo_root / "odylith" / "radar" / "source" / "releases"
    releases_root.mkdir(parents=True, exist_ok=True)
    (releases_root / "releases.v1.json").write_text(
        json.dumps(
            {
                "version": "v1",
                "updated_utc": "2026-04-09T16:00:00Z",
                "aliases": {"current": "release-0-1-11"},
                "releases": [
                    {
                        "release_id": "release-0-1-11",
                        "status": "active",
                        "version": "0.1.11",
                        "tag": "v0.1.11",
                        "name": "",
                        "notes": "",
                        "created_utc": "2026-04-08",
                        "shipped_utc": "",
                        "closed_utc": "",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (releases_root / "release-assignment-events.v1.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "action": "add",
                        "release_id": "release-0-1-11",
                        "workstream_id": "B-067",
                        "recorded_at": "2026-04-09T01:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "action": "add",
                        "release_id": "release-0-1-11",
                        "workstream_id": "B-068",
                        "recorded_at": "2026-04-09T02:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "action": "remove",
                        "release_id": "release-0-1-11",
                        "workstream_id": "B-067",
                        "recorded_at": "2026-04-09T03:00:00Z",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_traceability(
    repo_root: Path,
    *,
    active_workstreams: list[str],
    completed_workstreams: list[str],
    current_workstreams: list[dict[str, str]],
) -> None:
    """Write a traceability graph fixture with the requested release state."""
    traceability_path = repo_root / "odylith" / "radar" / "traceability-graph.v1.json"
    traceability_path.parent.mkdir(parents=True, exist_ok=True)
    traceability_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-09T16:30:00Z",
                "current_release": {
                    "release_id": "release-0-1-11",
                    "display_label": "0.1.11",
                    "active_workstreams": active_workstreams,
                    "completed_workstreams": completed_workstreams,
                },
                "workstreams": current_workstreams,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_compass_runtime_truth_drift_detects_release_membership_and_current_workstream_drift(
    tmp_path: Path,
) -> None:
    _seed_release_truth_repo(tmp_path)
    runtime_payload = {
        "release_summary": {
            "current_release": {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "active_workstreams": ["B-067"],
                "completed_workstreams": [],
            }
        },
        "current_workstreams": [
            {
                "idea_id": "B-067",
                "status": "implementation",
            }
        ],
    }

    drift = release_truth_runtime.build_compass_runtime_truth_drift(
        repo_root=tmp_path,
        runtime_payload=runtime_payload,
    )

    assert drift["reason_codes"] == [
        "active_release_membership",
        "completed_release_membership",
        "current_workstreams",
    ]
    assert drift["source_active_members"] == ["B-068"]
    assert drift["runtime_active_members"] == ["B-067"]
    assert drift["source_completed_members"] == ["B-067"]
    assert drift["source_current_workstreams"] == ["B-068"]
    assert "targets B-068 and completes B-067" in drift["warning"]
    assert "visible snapshot lists B-067" in drift["warning"]


def test_build_compass_runtime_truth_drift_is_empty_when_runtime_matches_source_truth(tmp_path: Path) -> None:
    _seed_release_truth_repo(tmp_path)
    runtime_payload = {
        "release_summary": {
            "current_release": {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "active_workstreams": ["B-068"],
                "completed_workstreams": ["B-067"],
            }
        },
        "current_workstreams": [
            {
                "idea_id": "B-068",
                "status": "implementation",
            }
        ],
    }

    drift = release_truth_runtime.build_compass_runtime_truth_drift(
        repo_root=tmp_path,
        runtime_payload=runtime_payload,
    )

    assert drift == {}


def test_build_compass_runtime_truth_drift_ignores_non_active_visible_current_rows(tmp_path: Path) -> None:
    _seed_release_truth_repo(tmp_path)
    runtime_payload = {
        "release_summary": {
            "current_release": {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "active_workstreams": ["B-068"],
                "completed_workstreams": ["B-067"],
            }
        },
        "current_workstreams": [
            {
                "idea_id": "B-068",
                "status": "implementation",
            },
            {
                "idea_id": "B-067",
                "status": "finished",
            },
            {
                "idea_id": "B-070",
                "status": "queued",
            },
        ],
    }

    drift = release_truth_runtime.build_compass_runtime_truth_drift(
        repo_root=tmp_path,
        runtime_payload=runtime_payload,
    )

    assert drift == {}


def test_build_compass_runtime_truth_drift_prefers_traceability_graph_for_compass_read_model(
    tmp_path: Path,
) -> None:
    _seed_release_truth_repo(tmp_path)
    _write_traceability(
        tmp_path,
        active_workstreams=["B-099"],
        completed_workstreams=["B-067"],
        current_workstreams=[{"idea_id": "B-099", "status": "implementation"}],
    )
    runtime_payload = {
        "release_summary": {
            "current_release": {
                "release_id": "release-0-1-11",
                "display_label": "0.1.11",
                "active_workstreams": ["B-067"],
                "completed_workstreams": [],
            }
        },
        "current_workstreams": [{"idea_id": "B-067", "status": "implementation"}],
    }

    drift = release_truth_runtime.build_compass_runtime_truth_drift(
        repo_root=tmp_path,
        runtime_payload=runtime_payload,
    )

    assert drift["truth_source"] == "traceability_graph"
    assert drift["source_active_members"] == ["B-099"]
    assert drift["source_current_workstreams"] == ["B-099"]
    assert "targets B-099 and completes B-067" in drift["warning"]
