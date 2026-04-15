from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import tooling_dashboard_surface_status


def _idea_text(*, idea_id: str, title: str, status: str) -> str:
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
        "sizing: S\n\n"
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
        "## Problem\nGrounded fixture coverage for problem in this synthetic workstream.\n"
    )


def _seed_release_truth(repo_root: Path) -> None:
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-04"
    ideas_root.mkdir(parents=True, exist_ok=True)
    ideas_root.joinpath("2026-04-09-b-067.md").write_text(
        _idea_text(idea_id="B-067", title="Old target", status="finished"),
        encoding="utf-8",
    )
    ideas_root.joinpath("2026-04-09-b-068.md").write_text(
        _idea_text(idea_id="B-068", title="New target", status="implementation"),
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
                json.dumps({"action": "add", "release_id": "release-0-1-11", "workstream_id": "B-067", "recorded_at": "2026-04-09T01:00:00Z"}),
                json.dumps({"action": "add", "release_id": "release-0-1-11", "workstream_id": "B-068", "recorded_at": "2026-04-09T02:00:00Z"}),
                json.dumps({"action": "remove", "release_id": "release-0-1-11", "workstream_id": "B-067", "recorded_at": "2026-04-09T03:00:00Z"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_surface_runtime_status_projects_release_truth_drift_when_compass_snapshot_lags(tmp_path: Path) -> None:
    _seed_release_truth(tmp_path)
    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(
            {
                "generated_utc": "2026-04-09T03:30:00Z",
                "release_summary": {
                    "current_release": {
                        "release_id": "release-0-1-11",
                        "display_label": "0.1.11",
                        "active_workstreams": ["B-067"],
                        "completed_workstreams": [],
                    }
                },
                "current_workstreams": [{"idea_id": "B-067", "status": "implementation"}],
                "runtime_contract": {"last_refresh_attempt": {"status": "passed", "requested_profile": "shell-safe"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    status = tooling_dashboard_surface_status.build_surface_runtime_status(
        repo_root=tmp_path,
        shell_rendered_utc="2026-04-09T04:00:00Z",
    )

    assert status == {}
