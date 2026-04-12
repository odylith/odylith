from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import render_compass_dashboard


def _runtime_paths(runtime_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    history_dir = runtime_dir / "history"
    today = dt.datetime.now(tz=render_compass_dashboard._COMPASS_TZ).date().isoformat()  # noqa: SLF001
    return (
        runtime_dir / "current.v1.json",
        runtime_dir / "current.v1.js",
        history_dir / f"{today}.v1.json",
        history_dir / "index.v1.json",
        history_dir / "embedded.v1.js",
    )


def _refresh_kwargs(repo_root: Path, runtime_dir: Path) -> dict[str, object]:
    return {
        "repo_root": repo_root,
        "runtime_dir": runtime_dir,
        "backlog_index_path": repo_root / "odylith/radar/source/INDEX.md",
        "plan_index_path": repo_root / "odylith/technical-plans/INDEX.md",
        "bugs_index_path": repo_root / "odylith/casebook/bugs/INDEX.md",
        "traceability_graph_path": repo_root / "odylith/radar/traceability-graph.v1.json",
        "mermaid_catalog_path": repo_root / "odylith/atlas/source/catalog/diagrams.v1.json",
        "codex_stream_path": repo_root / "odylith/compass/runtime/codex-stream.v1.jsonl",
        "retention_days": 15,
        "max_review_age_days": 21,
        "active_window_minutes": 15,
        "runtime_mode": "auto",
    }


def _brief(*, source: str) -> dict[str, object]:
    return {
        "schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "status": "ready",
        "source": source,
        "fingerprint": f"{source}-fingerprint",
        "substrate_fingerprint": f"{source}-fingerprint",
        "bundle_fingerprint": "",
        "provider_decision": "cache_reuse" if source == "cache" else "provider_called",
        "last_successful_narration_fingerprint": f"{source}-fingerprint",
        "generated_utc": "2026-04-08T00:00:00Z",
        "sections": [],
        "evidence_lookup": {},
    }


def _seed_runtime_paths(runtime_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)
    current_json_path.write_text("{}\n", encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")
    return current_json_path, current_js_path, daily_path, history_index_path, history_js_path


def _seed_required_render_inputs(repo_root: Path) -> None:
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "technical-plans").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "atlas" / "source" / "catalog").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Radar\n", encoding="utf-8")
    (repo_root / "odylith" / "technical-plans" / "INDEX.md").write_text("# Plans\n", encoding="utf-8")
    (repo_root / "odylith" / "casebook" / "bugs" / "INDEX.md").write_text("# Bugs\n", encoding="utf-8")
    (repo_root / "odylith" / "radar" / "traceability-graph.v1.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json").write_text(
        json.dumps({"version": "v1", "diagrams": []}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_parse_args_defaults_refresh_profile_to_shell_safe() -> None:
    args = render_compass_dashboard._parse_args([])  # noqa: SLF001

    assert args.refresh_profile == "shell-safe"


def test_parse_args_rejects_removed_refresh_profile_flag() -> None:
    with pytest.raises(SystemExit):
        render_compass_dashboard._parse_args(["--refresh-profile", "full"])  # noqa: SLF001


def test_refresh_runtime_artifacts_reuses_matching_runtime_payload(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
        },
    }
    current_json_path.write_text(json.dumps(payload), encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )

    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    reused_payload, paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert reused_payload["version"] == payload["version"]
    assert reused_payload["generated_utc"] == payload["generated_utc"]
    assert reused_payload["runtime_contract"]["input_fingerprint"] == "matching-fingerprint"
    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["status"] == "passed"
    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "shell-safe"
    assert calls["write"]
    assert paths == (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)


def test_existing_runtime_payload_rejects_generation_mismatch_during_active_sync(tmp_path: Path) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _seed_runtime_paths(runtime_dir)

    current_json_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": "2026-04-12T00:00:00Z",
                "runtime_contract": {
                    "version": "v1",
                    "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                    "input_fingerprint": "matching-fingerprint",
                    "generation": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    from odylith.runtime.governance import sync_session as governed_sync_session

    with governed_sync_session.activate_sync_session(governed_sync_session.GovernedSyncSession(repo_root=repo_root)):
        active = governed_sync_session.active_sync_session()
        assert active is not None
        active.bump_generation(
            step_label="refresh delivery truth",
            mutation_classes=("repo_owned_truth",),
            invalidated_namespaces=("runtime_warm",),
            paths=("odylith/runtime/delivery_intelligence.v4.json",),
        )
        payload = render_compass_dashboard._existing_runtime_payload_if_fresh(  # noqa: SLF001
            repo_root=repo_root,
            current_json_path=current_json_path,
            input_fingerprint="matching-fingerprint",
            runtime_paths=(current_json_path, current_js_path, daily_path, history_index_path, history_js_path),
        )

    assert payload is None


def test_refresh_runtime_artifacts_rebuilds_when_brief_contract_metadata_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    stale_payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "standup_brief": {
            "24h": {
                "status": "unavailable",
                "source": "unavailable",
                "fingerprint": "stale-brief-fingerprint",
                "generated_utc": "2026-04-08T00:00:00Z",
                "sections": [],
                "diagnostics": {"reason": "provider_error"},
                "evidence_lookup": {},
            }
        },
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
        },
    }
    current_json_path.write_text(json.dumps(stale_payload), encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )
    monkeypatch.setattr(render_compass_dashboard, "_runtime_daemon_available", lambda **_kwargs: False)
    monkeypatch.setattr(
        render_compass_dashboard,
        "_existing_runtime_payload_if_fresh",
        lambda **_kwargs: stale_payload,
    )

    built_payload = {
        "version": "v1",
        "generated_utc": "2026-04-10T00:00:00Z",
        "standup_brief": {"24h": _brief(source="cache")},
        "standup_brief_scoped": {},
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
        },
    }
    monkeypatch.setattr(
        render_compass_dashboard,
        "_load_runtime_impl",
        lambda: type(
            "_FakeRuntimeImpl",
            (),
            {
                "_build_runtime_payload": staticmethod(lambda **_kwargs: built_payload),
                "_write_runtime_snapshots": staticmethod(
                    lambda **_kwargs: (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)
                ),
            },
        )(),
    )

    refreshed_payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir)
    )

    assert refreshed_payload["generated_utc"] == "2026-04-10T00:00:00Z"
    assert refreshed_payload["standup_brief"]["24h"]["schema_version"] == render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION


def test_refresh_runtime_artifacts_reuses_initial_input_fingerprint_for_fresh_build(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    _seed_required_render_inputs(repo_root)

    fingerprint_calls = {"count": 0}

    def _fingerprint(**_kwargs):  # noqa: ANN001
        fingerprint_calls["count"] += 1
        return "fresh-build-fingerprint"

    monkeypatch.setattr(render_compass_dashboard, "_compass_runtime_input_fingerprint", _fingerprint)
    monkeypatch.setattr(render_compass_dashboard, "_runtime_daemon_available", lambda **_kwargs: False)
    monkeypatch.setattr(
        render_compass_dashboard,
        "_load_runtime_impl",
        lambda: type(
            "_FakeRuntimeImpl",
            (),
            {
                "_build_runtime_payload": staticmethod(
                    lambda **_kwargs: {
                        "generated_utc": "2026-04-11T00:00:00Z",
                        "runtime_contract": {},
                        "standup_brief": {"24h": _brief(source="cache")},
                    }
                ),
                "_write_runtime_snapshots": staticmethod(lambda **_kwargs: _runtime_paths(runtime_dir)),
            },
        )(),
    )
    monkeypatch.setattr(
        render_compass_dashboard.compass_standup_brief_maintenance,
        "stamp_request_runtime_input_fingerprint",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        render_compass_dashboard.compass_standup_brief_maintenance,
        "maybe_spawn_background",
        lambda **_kwargs: None,
    )

    payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert fingerprint_calls["count"] == 1
    assert payload["runtime_contract"]["input_fingerprint"] == "fresh-build-fingerprint"


def test_refresh_runtime_artifacts_prefers_matching_daemon_cached_payload(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    daemon_payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "current_workstreams": [{"idea_id": "B-101"}],
        "standup_brief": {"24h": _brief(source="cache"), "48h": _brief(source="cache")},
        "standup_brief_scoped": {"24h": {"B-101": _brief(source="cache")}, "48h": {"B-101": _brief(source="cache")}},
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "daemon-fingerprint",
        },
    }

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "daemon-fingerprint",
    )
    monkeypatch.setattr(render_compass_dashboard, "_runtime_daemon_available", lambda **_kwargs: True)
    monkeypatch.setattr(
        render_compass_dashboard,
        "_load_daemon_cached_runtime_payload",
        lambda **_kwargs: daemon_payload,
    )
    daemon_records: list[dict[str, object]] = []
    monkeypatch.setattr(
        render_compass_dashboard,
        "_record_daemon_cached_runtime_payload",
        lambda **kwargs: daemon_records.append(dict(kwargs)),
    )
    monkeypatch.setattr(
        render_compass_dashboard,
        "_existing_runtime_payload_if_fresh",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("disk snapshot reuse should not run after daemon hit")),
    )

    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    reused_payload, paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert reused_payload["runtime_contract"]["input_fingerprint"] == "daemon-fingerprint"
    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["status"] == "passed"
    assert calls["write"]
    assert daemon_records and daemon_records[-1]["input_fingerprint"] == "daemon-fingerprint"
    assert paths == (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)


def test_render_compass_dashboard_emits_proof_resolution_ui_text(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    output_path = repo_root / "odylith" / "compass" / "compass.html"
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    _seed_required_render_inputs(repo_root)
    runtime_paths = _seed_runtime_paths(runtime_dir)

    monkeypatch.setattr(
        render_compass_dashboard,
        "refresh_runtime_artifacts",
        lambda **_kwargs: (
            {
                "version": "v1",
                "generated_utc": "2026-04-08T00:00:00Z",
            },
            runtime_paths,
        ),
    )

    rc = render_compass_dashboard.main(["--repo-root", str(repo_root), "--output", str(output_path)])

    assert rc == 0
    workstreams_js = (repo_root / "odylith" / "compass" / "compass-workstreams.v1.js").read_text(encoding="utf-8")
    assert "No dominant proof lane is resolved for this workstream yet." in workstreams_js
    assert "Ambiguous across" in workstreams_js


def test_render_compass_dashboard_emits_release_summary_and_workstream_release_ui(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    output_path = repo_root / "odylith" / "compass" / "compass.html"
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    _seed_required_render_inputs(repo_root)
    runtime_paths = _seed_runtime_paths(runtime_dir)

    monkeypatch.setattr(
        render_compass_dashboard,
        "refresh_runtime_artifacts",
        lambda **_kwargs: (
            {
                "version": "v1",
                "generated_utc": "2026-04-08T00:00:00Z",
            },
            runtime_paths,
        ),
    )

    rc = render_compass_dashboard.main(["--repo-root", str(repo_root), "--output", str(output_path)])

    assert rc == 0
    summary_js = (repo_root / "odylith" / "compass" / "compass-summary.v1.js").read_text(encoding="utf-8")
    releases_js = (repo_root / "odylith" / "compass" / "compass-releases.v1.js").read_text(encoding="utf-8")
    waves_js = (repo_root / "odylith" / "compass" / "compass-waves.v1.js").read_text(encoding="utf-8")
    workstreams_js = (repo_root / "odylith" / "compass" / "compass-workstreams.v1.js").read_text(encoding="utf-8")
    assert 'rows.push(["Target Release", currentReleaseLabel, "stat-release-only"])' in summary_js
    assert 'rows.push(["Active Waves"' not in summary_js
    assert 'rows.push(["Next Release"' not in summary_js
    assert 'class="stat${cardClass ? ` ${cardClass}` : ""}"' in summary_js
    assert "function releaseHeroLabel(release)" in summary_js
    assert 'const nameLabel = String(releaseRow.name || "").trim();' in summary_js
    assert 'const versionLabel = String(releaseRow.version || "").trim();' in summary_js
    assert 'const tagLabel = String(releaseRow.tag || "").trim();' in summary_js
    assert 'return /^v\\d/.test(tagLabel) ? tagLabel.slice(1) : tagLabel;' in summary_js
    assert 'return versionLabel.startsWith("v") ? versionLabel : `v${versionLabel}`;' not in summary_js
    assert "function renderReleaseGroups(payload, state)" in releases_js
    assert "Release Targets" in releases_js
    assert "<h2>Programs</h2>" in waves_js
    assert "Targeted Workstreams" in releases_js
    assert "Completed Workstreams" in releases_js
    assert 'group.status === "planned"' in releases_js
    assert 'group.status === "draft"' in releases_js
    assert 'return groups;' in releases_js
    assert 'const currentOnlyGroups = currentReleaseId' not in releases_js
    assert 'Target Release</span>' in releases_js
    assert "No targeted workstreams." in releases_js
    assert "execution-wave-focus-title" not in releases_js
    assert '<div class="execution-wave-section-title-row">' in releases_js
    assert '<div class="execution-wave-section-title-meta">' in releases_js
    assert '<div class="execution-wave-member-head">' in releases_js
    assert '<div class="execution-wave-member-title-chips">' in releases_js
    assert '<div class="execution-wave-title-row">' not in releases_js
    assert "Release-owned targeted workstreams for this release." not in releases_js
    assert "Release-owned targeted workstreams for this selection." not in releases_js
    assert "function compassReleaseDisplayName(release)" in releases_js
    assert "row.name || row.version || row.tag || row.display_label || row.effective_name" in releases_js
    assert 'const openAttr = scopedWorkstream ? " open" : "";' in releases_js
    assert 'group.is_current || groups.length === 1' not in releases_js
    assert "function compassWorkstreamReleaseLabel(release)" in workstreams_js
    assert "function compassGovernanceRepresentedWorkstreamIds(payload)" in workstreams_js
    assert "row.name || row.version || row.tag || row.display_label || row.effective_name" in workstreams_js
    assert "Release: ${escapeHtml(selected.releaseLabel)}" not in workstreams_js
    assert "Release ${item.releaseLabel}" not in workstreams_js
    assert "<strong>Release history:</strong>" in workstreams_js
    assert "All current workstreams are already represented in Programs or Release Targets." in workstreams_js
    assert "No active workstreams in this scope." in workstreams_js
    assert "const rows = scopedRows;" not in workstreams_js


def test_render_compass_dashboard_writes_source_truth_snapshot_and_shell_href(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    output_path = repo_root / "odylith" / "compass" / "compass.html"
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    _seed_required_render_inputs(repo_root)
    runtime_paths = _seed_runtime_paths(runtime_dir)

    monkeypatch.setattr(
        render_compass_dashboard,
        "refresh_runtime_artifacts",
        lambda **_kwargs: (
            {
                "version": "v1",
                "generated_utc": "2026-04-09T12:00:00Z",
                "release_summary": {
                    "catalog": [
                        {
                            "release_id": "release-0-1-11",
                            "display_label": "0.1.11",
                            "status": "active",
                            "aliases": ["current"],
                            "active_workstreams": ["B-072", "B-073", "B-079"],
                            "completed_workstreams": ["B-061"],
                        }
                    ],
                    "current_release": {
                        "release_id": "release-0-1-11",
                        "display_label": "0.1.11",
                        "status": "active",
                        "aliases": ["current"],
                        "active_workstreams": ["B-072", "B-073", "B-079"],
                        "completed_workstreams": ["B-061"],
                    },
                    "next_release": {},
                    "summary": {"active_assignment_count": 3},
                },
                "current_workstreams": [
                    {"idea_id": "B-072", "title": "Execution Governance Engine Program", "status": "implementation"},
                    {"idea_id": "B-073", "title": "Task Contract", "status": "queued"},
                    {"idea_id": "B-079", "title": "Program/Wave Authoring CLI and Agent Ergonomics", "status": "queued"},
                ],
                "workstream_catalog": [
                    {"idea_id": "B-072", "title": "Execution Governance Engine Program", "status": "implementation"},
                    {"idea_id": "B-073", "title": "Task Contract", "status": "queued"},
                    {"idea_id": "B-079", "title": "Program/Wave Authoring CLI and Agent Ergonomics", "status": "queued"},
                    {"idea_id": "B-061", "title": "Older lane", "status": "finished"},
                ],
            },
            runtime_paths,
        ),
    )

    rc = render_compass_dashboard.main(["--repo-root", str(repo_root), "--output", str(output_path)])

    assert rc == 0
    source_truth_path = repo_root / "odylith" / "compass" / "compass-source-truth.v1.json"
    source_truth = json.loads(source_truth_path.read_text(encoding="utf-8"))
    assert source_truth["release_summary"]["current_release"]["active_workstreams"] == ["B-072", "B-073", "B-079"]
    assert [row["idea_id"] for row in source_truth["current_workstreams"]] == ["B-072", "B-073", "B-079"]
    payload_js = (repo_root / "odylith" / "compass" / "compass-payload.v1.js").read_text(encoding="utf-8")
    assert "source_truth_href" in payload_js


def test_refresh_runtime_artifacts_reuses_matching_payload(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "current_workstreams": [{"idea_id": "B-101"}],
        "standup_brief": {"24h": _brief(source="provider"), "48h": _brief(source="cache")},
        "standup_brief_scoped": {"24h": {"B-101": _brief(source="provider")}, "48h": {"B-101": _brief(source="cache")}},
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
        },
    }
    current_json_path.write_text(json.dumps(payload), encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )
    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    reused_payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["status"] == "passed"
    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "shell-safe"
    assert calls["write"]


def test_payload_satisfies_requested_refresh_accepts_matching_payload_shape() -> None:
    payload = {
        "current_workstreams": [{"idea_id": "B-101"}],
        "standup_brief": {"24h": _brief(source="provider"), "48h": _brief(source="cache")},
        "standup_brief_scoped": {"24h": {"B-101": _brief(source="provider")}, "48h": {}},
    }

    assert render_compass_dashboard._payload_satisfies_requested_refresh(  # noqa: SLF001
        payload=payload,
        requested_profile="shell-safe",
    )


def test_payload_satisfies_requested_refresh_rejects_cached_stock_phrasing() -> None:
    payload = {
        "standup_brief": {
            "24h": {
                **_brief(source="cache"),
                "sections": [
                    {
                        "key": "current_execution",
                        "label": "Current execution",
                        "bullets": [
                            {
                                "text": "`B-071` is trying to stop each surface from guessing scope importance on its own. Compass already showed how expensive that gets.",
                                "fact_ids": ["F-001"],
                            }
                        ],
                    }
                ],
            }
        },
        "standup_brief_scoped": {"24h": {}, "48h": {}},
    }

    assert not render_compass_dashboard._payload_satisfies_requested_refresh(  # noqa: SLF001
        payload=payload,
        requested_profile="shell-safe",
    )


def test_payload_satisfies_requested_refresh_allows_empty_scoped_maps_when_no_current_workstreams() -> None:
    payload = {
        "current_workstreams": [],
        "standup_brief": {"24h": _brief(source="provider"), "48h": _brief(source="cache")},
        "standup_brief_scoped": {"24h": {}, "48h": {}},
    }

    assert render_compass_dashboard._payload_satisfies_requested_refresh(  # noqa: SLF001
        payload=payload,
        requested_profile="shell-safe",
    )


def test_refresh_runtime_artifacts_reuses_matching_payload_when_briefs_are_cache_backed(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "current_workstreams": [{"idea_id": "B-101"}],
        "standup_brief": {"24h": _brief(source="cache"), "48h": _brief(source="cache")},
        "standup_brief_scoped": {"24h": {"B-101": _brief(source="cache")}, "48h": {"B-101": _brief(source="cache")}},
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
        },
    }
    current_json_path.write_text(json.dumps(payload), encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )
    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert payload["runtime_contract"]["refresh_profile"] == "shell-safe"
    assert calls["write"]


def test_refresh_runtime_artifacts_rebuilds_when_cache_is_stale(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    expected_paths = _runtime_paths(runtime_dir)
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "fresh-fingerprint",
    )

    class _FakeRuntimeImpl:
        def _build_runtime_payload(self, **kwargs):  # noqa: ANN003
            calls["build"] = dict(kwargs)
            return {"version": "v1", "history": {}}

        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return expected_paths

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    payload, paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert calls["build"]
    assert calls["write"]
    assert payload["runtime_contract"]["standup_brief_schema_version"] == (
        render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION
    )
    assert payload["runtime_contract"]["input_fingerprint"] == "fresh-fingerprint"
    assert payload["runtime_contract"]["retention_days"] == 15
    assert payload["runtime_contract"]["active_window_minutes"] == 15
    assert payload["runtime_contract"]["max_review_age_days"] == 21
    assert payload["runtime_contract"]["runtime_mode"] == "auto"
    assert paths == expected_paths


def test_refresh_runtime_artifacts_persists_postbuild_input_fingerprint_when_build_mutates_tracked_inputs(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    backlog_index_path = repo_root / "odylith/radar/source/INDEX.md"
    backlog_index_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_index_path.write_text("# Radar\n", encoding="utf-8")
    expected_paths = _runtime_paths(runtime_dir)
    calls: dict[str, object] = {}
    fingerprints = iter(("prebuild-fingerprint", "postbuild-fingerprint"))

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: next(fingerprints),
    )

    class _FakeRuntimeImpl:
        def _build_runtime_payload(self, **kwargs):  # noqa: ANN003
            calls["build"] = dict(kwargs)
            backlog_index_path.write_text("# Radar\n\nmutated during build\n", encoding="utf-8")
            return {"version": "v1", "history": {}}

        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return expected_paths

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    payload, paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert calls["build"]
    assert calls["write"]
    assert payload["runtime_contract"]["input_fingerprint"] == "postbuild-fingerprint"
    assert paths == expected_paths


def test_refresh_runtime_artifacts_reuses_matching_runtime_payload_even_when_it_is_old(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    stale_generated = (dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(days=7)).replace(microsecond=0)
    current_json_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": stale_generated.isoformat().replace("+00:00", "Z"),
                "runtime_contract": {
                    "version": "v1",
                    "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                    "input_fingerprint": "matching-fingerprint",
                },
            }
        ),
        encoding="utf-8",
    )
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert payload["runtime_contract"]["input_fingerprint"] == "matching-fingerprint"


def test_refresh_runtime_artifacts_reuses_matching_payload_when_todays_daily_history_file_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v1",
        "generated_utc": "2026-04-08T00:00:00Z",
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
        },
    }
    current_json_path.write_text(json.dumps(payload), encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )

    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    reused_payload, paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert reused_payload["runtime_contract"]["input_fingerprint"] == "matching-fingerprint"
    assert calls["write"]
    assert paths == (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)


def test_refresh_runtime_artifacts_shell_safe_rebuilds_stale_snapshot_in_bounded_mode(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    stale_generated = (dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(days=7)).replace(microsecond=0)
    current_json_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "generated_utc": stale_generated.isoformat().replace("+00:00", "Z"),
                "runtime_contract": {
                    "version": "v1",
                    "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
                    "input_fingerprint": "stale-fingerprint",
                },
            }
        ),
        encoding="utf-8",
    )
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "fresh-fingerprint",
    )
    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _build_runtime_payload(self, **kwargs):  # noqa: ANN003
            calls["build"] = dict(kwargs)
            return {
                "version": "v1",
                "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            }

        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    payload, paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert calls["build"]
    assert calls["build"]["refresh_profile"] == "shell-safe"
    assert calls["write"]
    assert payload["runtime_contract"]["refresh_profile"] == "shell-safe"
    assert paths == (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)


def test_refresh_runtime_artifacts_rebuilds_when_standup_brief_schema_version_changes(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "runtime_contract": {
            "version": "v1",
            "standup_brief_schema_version": "v6",
            "input_fingerprint": "matching-fingerprint",
        },
    }
    current_json_path.write_text(json.dumps(payload), encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )
    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _build_runtime_payload(self, **kwargs):  # noqa: ANN003
            calls["build"] = dict(kwargs)
            return {
                "version": "v1",
                "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            }

        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    refreshed_payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert calls["build"]
    assert calls["write"]
    assert refreshed_payload["runtime_contract"]["standup_brief_schema_version"] == (
        render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION
    )


def test_refresh_runtime_artifacts_shell_safe_builds_without_existing_snapshot(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    expected_paths = _runtime_paths(runtime_dir)
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "fresh-fingerprint",
    )
    class _FakeRuntimeImpl:
        def _build_runtime_payload(self, **kwargs):  # noqa: ANN003
            calls["build"] = dict(kwargs)
            return {"version": "v1"}

        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return expected_paths

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    payload, paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert calls["build"]
    assert calls["build"]["refresh_profile"] == "shell-safe"
    assert calls["write"]
    assert payload["runtime_contract"]["refresh_profile"] == "shell-safe"
    assert paths == expected_paths


def test_refresh_runtime_artifacts_shell_safe_stamps_and_spawns_narration_maintenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    expected_paths = _runtime_paths(runtime_dir)
    stamped: list[str] = []
    spawned: list[Path] = []

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "fresh-fingerprint",
    )

    class _FakeRuntimeImpl:
        def _build_runtime_payload(self, **_kwargs):  # noqa: ANN003
            return {"version": "v1"}

        def _write_runtime_snapshots(self, **_kwargs):  # noqa: ANN003
            return expected_paths

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())
    monkeypatch.setattr(
        render_compass_dashboard.compass_standup_brief_maintenance,
        "stamp_request_runtime_input_fingerprint",
        lambda **kwargs: stamped.append(str(kwargs["runtime_input_fingerprint"])),
    )
    monkeypatch.setattr(
        render_compass_dashboard.compass_standup_brief_maintenance,
        "maybe_spawn_background",
        lambda **kwargs: spawned.append(Path(kwargs["repo_root"]).resolve()) or 4321,
    )

    payload, paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert payload["runtime_contract"]["input_fingerprint"] == "fresh-fingerprint"
    assert stamped == ["fresh-fingerprint"]
    assert spawned == [repo_root.resolve()]
    assert paths == expected_paths


def test_record_failed_refresh_attempt_marks_live_runtime_payload(tmp_path: Path) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, _daily_path, _history_index_path, _history_js_path = _runtime_paths(runtime_dir)

    payload = {
        "version": "v1",
        "generated_utc": "2026-04-08T00:06:12Z",
        "runtime_contract": {
            "version": "v1",
            "refresh_profile": "shell-safe",
        },
    }
    current_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")

    marked = render_compass_dashboard.record_failed_refresh_attempt(
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        requested_profile="shell-safe",
        runtime_mode="auto",
        reason="timeout",
        fallback_used=True,
    )

    updated = json.loads(current_json_path.read_text(encoding="utf-8"))

    assert marked is True
    assert "Requested Compass shell-safe refresh did not finish before the dashboard timeout." in updated["warning"]
    assert updated["runtime_contract"]["last_refresh_attempt"]["status"] == "failed"
    assert updated["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "shell-safe"
    assert updated["runtime_contract"]["last_refresh_attempt"]["applied_profile"] == "shell-safe"
    assert updated["runtime_contract"]["last_refresh_attempt"]["reason"] == "timeout"
    assert updated["runtime_contract"]["last_refresh_attempt"]["fallback_used"] is True


def test_refresh_runtime_artifacts_clears_failed_refresh_warning_when_reusing_matching_payload(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v1",
        "generated_utc": dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "warning": "Requested Compass shell-safe refresh did not finish before the dashboard timeout.",
        "runtime_contract": {
            "version": "v1",
            "refresh_profile": "shell-safe",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
            "last_refresh_attempt": {
                "status": "failed",
                "requested_profile": "shell-safe",
                "applied_profile": "shell-safe",
                "reason": "timeout",
                "attempted_utc": "2026-04-08T00:10:00Z",
                "fallback_used": True,
            },
        },
    }
    current_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    current_js_path.write_text("window.__ODYLITH_COMPASS_RUNTIME__ = {};\n", encoding="utf-8")
    daily_path.write_text("{}\n", encoding="utf-8")
    history_index_path.write_text("{}\n", encoding="utf-8")
    history_js_path.write_text("window.__ODYLITH_COMPASS_HISTORY__ = {};\n", encoding="utf-8")

    monkeypatch.setattr(
        render_compass_dashboard,
        "_compass_runtime_input_fingerprint",
        lambda **_kwargs: "matching-fingerprint",
    )
    calls: dict[str, object] = {}

    class _FakeRuntimeImpl:
        def _write_runtime_snapshots(self, **kwargs):  # noqa: ANN003
            calls["write"] = dict(kwargs)
            return (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", lambda: _FakeRuntimeImpl())

    refreshed_payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert "warning" not in refreshed_payload
    assert refreshed_payload["runtime_contract"]["last_refresh_attempt"]["status"] == "passed"
    assert refreshed_payload["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "shell-safe"
    assert calls["write"]
