"""Actual Git lifecycle proof for durable Delivery and live Registry evidence."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from odylith.runtime.governance import component_registry_intelligence as registry
from odylith.runtime.governance import delivery_intelligence_engine as delivery
from odylith.runtime.governance import delivery_intelligence_refresh as refresh
from odylith.runtime.governance import sync_session
from odylith.runtime.context_engine import odylith_context_engine_registry_detail_runtime as detail


_SOURCE = "src/project_delivery.py"
_SPEC = "odylith/registry/source/components/project-delivery/CURRENT_SPEC.md"


def _write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


@pytest.fixture
def activity_repo(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("Git is required to prove dirty-source commit stability")
    _write(tmp_path, ".gitignore", ".odylith/\n")
    _write(tmp_path, ".odylith/consumer-profile.json", json.dumps({
        "version": "v1", "consumer_id": "delivery-boundary",
        "truth_roots": {"component_registry": registry.DEFAULT_MANIFEST_PATH},
        "surface_roots": {"product_root": "odylith", "runtime_root": ".odylith"},
    }))
    _write(tmp_path, _SOURCE, '"""Project delivery fixture."""\n')
    _write(tmp_path, _SPEC, "# Project Delivery\n\n## Feature History\n"
           "- 2026-09-08: Recorded initial contract. "
           "(Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))\n")
    _write(tmp_path, registry.DEFAULT_MANIFEST_PATH, json.dumps({
        "version": "v1",
        "components": [{
            "component_id": "project-delivery", "name": "Project Delivery",
            "kind": "runtime", "category": "governance_engine",
            "qualification": "curated", "aliases": [],
            "path_prefixes": [_SOURCE, _SPEC], "workstreams": ["B-001"],
            "diagrams": ["D-001"], "owner": "product", "status": "active",
            "what_it_is": "Project publication owner.",
            "why_tracked": "Owns publication and recovery evidence.", "spec_ref": _SPEC,
        }],
    }))
    _write(tmp_path, registry.DEFAULT_CATALOG_PATH, json.dumps({
        "version": "1.0", "diagrams": [{
            "diagram_id": "D-001", "title": "Project publication",
            "components": [{"name": "Project Delivery"}],
            "related_workstreams": ["B-001"],
        }],
    }))
    _write(tmp_path, registry.DEFAULT_TRACEABILITY_GRAPH_PATH, json.dumps({
        "workstreams": [{"idea_id": "B-001", "status": "implementation"}],
    }))
    _write(tmp_path, registry.DEFAULT_STREAM_PATH, json.dumps({
        "ts_iso": "2026-09-08T00:00:00Z", "kind": "implementation",
        "summary": "Recorded project publication implementation.",
        "components": ["project-delivery"], "artifacts": [_SOURCE], "workstreams": ["B-001"],
    }) + "\n")
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    _commit(tmp_path, "Record initial project evidence")
    return tmp_path


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
    subprocess.run([
        "git", "-C", str(root), "-c", "user.name=freedom-research",
        "-c", "user.email=freedom@freedompreetham.org", "commit", "-m", message,
    ], check=True, capture_output=True)


@pytest.mark.parametrize("changed_path", [_SOURCE, _SPEC], ids=["source", "spec"])
@pytest.mark.parametrize("entrypoint", [delivery.main, refresh.main], ids=["engine", "sync-wrapper"])
def test_delivery_survives_dirty_source_sync_and_commit(activity_repo: Path, changed_path: str, entrypoint) -> None:
    root = activity_repo
    target = root / changed_path
    target.write_text(target.read_text(encoding="utf-8") + "\n# Revised contract\n", encoding="utf-8")
    live = registry.build_component_registry_report(repo_root=root)
    assert "project-delivery" in live.components, "\n".join(live.diagnostics)
    assert any(event.kind == "workspace_activity" for event in live.mapped_events)
    assert live.forensic_coverage["project-delivery"].recent_path_match_count == 1
    assert live.forensic_coverage["project-delivery"].explicit_event_count == 1

    args = ["--repo-root", str(root)]
    assert entrypoint(args) == 0
    output = root / delivery.DEFAULT_OUTPUT_PATH
    before_commit = output.read_bytes()
    scopes = json.loads(before_commit)["scopes"]
    assert {"component", "workstream", "diagram", "surface", "grid"} <= {row["scope_type"] for row in scopes}
    assert any(row["diagnostics"].get("explicit_count", 0) > 0 for row in scopes)
    _commit(root, "Commit source and its synchronized Delivery snapshot together")
    clean = registry.build_component_registry_report(repo_root=root)
    assert not any(event.kind == "workspace_activity" for event in clean.mapped_events)

    assert entrypoint([*args, "--check-only"]) == 0
    assert output.read_bytes() == before_commit
    assert all(row["diagnostics"].get("synthetic_count", 0) == 0 for row in scopes)
    assert entrypoint(args) == 0
    assert output.read_bytes() == before_commit

    # A real new recorded decision must still invalidate both refresh paths.
    stream = root / registry.DEFAULT_STREAM_PATH
    with stream.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "ts_iso": "2026-09-08T01:00:00Z", "kind": "decision",
            "summary": "Require publication readback before reporting completion.",
            "components": ["project-delivery"], "artifacts": [_SOURCE],
        }) + "\n")
    assert entrypoint([*args, "--check-only"]) == 2
    assert output.read_bytes() == before_commit
    assert entrypoint(args) == 0
    assert output.read_bytes() != before_commit
    changed = json.loads(output.read_bytes())
    component = next(row for row in changed["scopes"] if row["scope_key"] == "component:project-delivery")
    assert component["diagnostics"]["explicit_count"] == 2
    assert component["diagnostics"]["decision_count"] == 1
    assert entrypoint([*args, "--check-only"]) == 0


@pytest.mark.parametrize("first_live", [True, False], ids=["live-first", "recorded-first"])
def test_registry_views_keep_cache_and_coverage_separate(activity_repo: Path, first_live: bool) -> None:
    root = activity_repo
    _write(root, _SOURCE, '"""Revised project publication."""\n')
    session = sync_session.GovernedSyncSession(repo_root=root)
    with sync_session.activate_sync_session(session):
        reports = {}
        for live in (first_live, not first_live):
            reports[live] = registry.build_component_registry_report(repo_root=root, include_workspace_activity=live)
        for live in (first_live, not first_live):
            assert registry.build_component_registry_report(repo_root=root, include_workspace_activity=live) is reports[live]

    # Outside the session, both on-disk caches must retain the same evidence mode.
    for live in (not first_live, first_live):
        cached = registry.build_component_registry_report(repo_root=root, include_workspace_activity=live)
        assert cached.as_dict() == reports[live].as_dict()
        assert cached.forensic_coverage["project-delivery"].recent_path_match_count == int(live)
        assert cached.forensic_coverage["project-delivery"].explicit_event_count == 1
    context = detail.build_registry_detail(snapshot={"report": reports[True]}, component_id="project-delivery")
    assert context is not None
    assert context["forensic_coverage"]["recent_path_match_count"] == 1
    assert any(event.kind == "workspace_activity" for event in context["timeline"])


@pytest.mark.parametrize("invalid_output", [False, True], ids=["missing", "invalid"])
def test_delivery_live_fallback_retains_workspace_observation(activity_repo: Path, invalid_output: bool) -> None:
    root = activity_repo
    _write(root, _SOURCE, '"""Revised project publication."""\n')
    if invalid_output:
        _write(root, delivery.DEFAULT_OUTPUT_PATH, "{}\n")
    live = delivery.load_delivery_intelligence_artifact(repo_root=root)
    component = next(row for row in live["scopes"] if row["scope_key"] == "component:project-delivery")
    assert component["diagnostics"]["synthetic_count"] == 1
    assert delivery.main(["--repo-root", str(root)]) == 0
    recorded = delivery.load_delivery_intelligence_artifact(repo_root=root)
    assert all(row["diagnostics"].get("synthetic_count", 0) == 0 for row in recorded["scopes"])
    assert registry.build_component_registry_report(repo_root=root).forensic_coverage["project-delivery"].recent_path_match_count == 1


@pytest.mark.parametrize("kind", ["workspace_activity", "WORKSPACE_ACTIVITY", " Workspace_Activity "])
def test_recorded_registry_omits_replayed_workspace_events_without_scanning(activity_repo: Path, monkeypatch, kind: str) -> None:
    stream = activity_repo / registry.DEFAULT_STREAM_PATH
    with stream.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "ts_iso": "2026-09-08T02:00:00Z", "kind": kind,
            "summary": "Previously observed local work.",
            "components": ["project-delivery"], "artifacts": [_SOURCE],
        }) + "\n")

    def unexpected_scan(**_):
        raise AssertionError("Persisted evidence must not scan volatile worktree state")

    monkeypatch.setattr("odylith.runtime.governance.agent_governance_intelligence.collect_git_changed_paths", unexpected_scan)
    monkeypatch.setattr(registry, "build_workspace_activity_events", unexpected_scan)
    recorded = registry.build_component_registry_report(repo_root=activity_repo, include_workspace_activity=False)
    assert [event.kind for event in recorded.mapped_events] == ["implementation"]
    assert recorded.forensic_coverage["project-delivery"].recent_path_match_count == 0


def test_component_serialization_preserves_all_fields_and_list_isolation(activity_repo: Path) -> None:
    report = registry.build_component_registry_report(repo_root=activity_repo)
    entry = report.components["project-delivery"]
    canonical = entry.as_dict()
    assert canonical == {name: getattr(entry, name) for name in entry.__dataclass_fields__}
    for name in ("aliases", "path_prefixes", "workstreams", "diagrams", "sources", "subcomponents"):
        canonical[name].append("only-in-copy")
        assert "only-in-copy" not in getattr(entry, name)
