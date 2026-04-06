from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import update_compass as updater


def _write_workstream_spec(tmp_path: Path, *, idea_id: str, title: str) -> None:
    idea_dir = tmp_path / "odylith" / "radar" / "source" / "ideas" / "2026-03"
    idea_dir.mkdir(parents=True, exist_ok=True)
    slug = title.lower().replace(" ", "-")
    (idea_dir / f"2026-03-04-{slug}.md").write_text(
        (
            "status: implementation\n\n"
            f"idea_id: {idea_id}\n\n"
            f"title: {title}\n\n"
            "date: 2026-03-04\n\n"
            "priority: P1\n\n"
            "commercial_value: 4\n\n"
            "product_impact: 4\n\n"
            "market_value: 4\n\n"
            "impacted_lanes: both\n\n"
            "impacted_parts: compass\n\n"
            "sizing: M\n\n"
            "complexity: Medium\n\n"
            "ordering_score: 100\n\n"
            "ordering_rationale: fixture\n\n"
            "confidence: high\n\n"
            "founder_override: no\n\n"
            "promoted_to_plan:\n\n"
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


def _seed_component_registry(tmp_path: Path) -> None:
    spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "compass" / "CURRENT_SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "render_compass_dashboard.py").write_text("# fixture\n", encoding="utf-8")
    plan_page = tmp_path / "odylith" / "radar" / "radar.html"
    plan_page.parent.mkdir(parents=True, exist_ok=True)
    plan_page.write_text("<html><body>B-033</body></html>\n", encoding="utf-8")
    spec_path.write_text(
        (
            "Last updated: 2026-03-04\n\n"
            "## Feature History\n"
            "- 2026-03-04: Seed fixture. "
            "(Plan: [B-033](odylith/radar/radar.html?view=plan&workstream=B-033))\n"
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
                        "aliases": ["executive-compass"],
                        "path_prefixes": [
                            "src/odylith/runtime/surfaces/render_compass_dashboard.py",
                            "src/odylith/runtime/surfaces/update_compass.py",
                        ],
                        "workstreams": ["B-033"],
                        "diagrams": [],
                        "owner": "platform",
                        "status": "active",
                        "category": "governance_surface",
                        "qualification": "curated",
                        "what_it_is": "Execution and timeline audit dashboard surface.",
                        "why_tracked": "Captures codex stream narratives for governance audits.",
                        "spec_ref": "odylith/registry/source/components/compass/CURRENT_SPEC.md",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "1.0", "diagrams": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_workstream_spec(tmp_path, idea_id="B-033", title="Compass update fixture")


def _stream_lines(repo_root: Path) -> list[dict[str, object]]:
    stream_path = repo_root / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl"
    assert stream_path.is_file()
    return [
        json.loads(line)
        for line in stream_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_update_compass_appends_multiple_event_types_without_render(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    rc = updater.main(
        [
            "--repo-root",
            str(tmp_path),
            "--decision",
            "Decision: keep Compass updates additive and fail-closed.",
            "--implementation",
            "Implemented statement ingestion into standup brief rendering.",
            "--update",
            "Current focus includes Compass timeline narrative capture.",
            "--workstream",
            "b-033",
            "--artifact",
            "./src/odylith/runtime/surfaces/render_compass_dashboard.py",
            "--no-render",
        ]
    )
    assert rc == 0

    payloads = _stream_lines(tmp_path)
    assert [str(row.get("kind", "")) for row in payloads] == ["decision", "implementation", "statement"]
    assert payloads[0]["workstreams"] == ["B-033"]
    assert payloads[2]["artifacts"] == ["src/odylith/runtime/surfaces/render_compass_dashboard.py"]


def test_update_compass_fails_without_messages(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _seed_component_registry(tmp_path)
    rc = updater.main(["--repo-root", str(tmp_path), "--no-render"])
    assert rc == 2
    out = capsys.readouterr().out
    assert "provide at least one of" in out


def test_update_compass_renders_by_default(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_component_registry(tmp_path)
    calls: list[list[str]] = []

    def _fake_render(args: list[str]) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(updater.render_compass_dashboard, "main", _fake_render)
    rc = updater.main(
        [
            "--repo-root",
            str(tmp_path),
            "--statement",
            "Captured execution update for standup context.",
        ]
    )
    assert rc == 0
    assert calls
    assert "--repo-root" in calls[0]


def test_update_compass_uses_default_history_retention_for_refresh(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_component_registry(tmp_path)
    captured: dict[str, object] = {}

    def _fake_refresh_runtime_artifacts(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        dummy = tmp_path / "dummy"
        return {}, (dummy, dummy, dummy, dummy, dummy)

    monkeypatch.setattr(updater.render_compass_dashboard, "refresh_runtime_artifacts", _fake_refresh_runtime_artifacts)
    monkeypatch.setattr(updater.odylith_context_engine_store, "append_runtime_event", lambda **_: None)

    rc = updater.main(
        [
            "--repo-root",
            str(tmp_path),
            "--statement",
            "Captured execution update for retention coverage.",
        ]
    )

    assert rc == 0
    assert captured["retention_days"] == updater.render_compass_dashboard.DEFAULT_HISTORY_RETENTION_DAYS


def test_update_compass_passes_transaction_grouping_fields(tmp_path: Path) -> None:
    _seed_component_registry(tmp_path)
    rc = updater.main(
        [
            "--repo-root",
            str(tmp_path),
            "--decision",
            "Decision: group prompt transactions by explicit marker first.",
            "--implementation",
            "Implemented transaction card render with inline expansion.",
            "--workstream",
            "B-033",
            "--session-id",
            "session-a",
            "--transaction-id",
            "txn-9",
            "--transaction-seq-start",
            "10",
            "--context",
            "Consolidate file edits into one timeline transaction card.",
            "--headline-hint",
            "Hardened Compass headline inference",
            "--transaction-boundary",
            "start",
            "--no-render",
        ]
    )
    assert rc == 0

    payloads = _stream_lines(tmp_path)
    assert [int(row.get("transaction_seq", 0)) for row in payloads] == [10, 11]
    assert all(str(row.get("session_id", "")) == "session-a" for row in payloads)
    assert all(str(row.get("transaction_id", "")) == "txn-9" for row in payloads)
    assert all(str(row.get("context", "")) == "Consolidate file edits into one timeline transaction card." for row in payloads)
    assert all(str(row.get("headline_hint", "")) == "Hardened Compass headline inference" for row in payloads)
    assert payloads[0]["transaction_boundary"] == "start"
    assert "transaction_boundary" not in payloads[1]
