from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

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


def test_parse_args_defaults_to_shell_safe_refresh_profile() -> None:
    args = render_compass_dashboard._parse_args([])  # noqa: SLF001

    assert args.refresh_profile == "shell-safe"


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

    def _unexpected_runtime_impl() -> object:
        raise AssertionError("runtime implementation should not load on fresh fast path")

    monkeypatch.setattr(render_compass_dashboard, "_load_runtime_impl", _unexpected_runtime_impl)

    reused_payload, paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert reused_payload["version"] == payload["version"]
    assert reused_payload["generated_utc"] == payload["generated_utc"]
    assert reused_payload["runtime_contract"]["input_fingerprint"] == "matching-fingerprint"
    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["status"] == "passed"
    assert reused_payload["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "shell-safe"
    assert paths == (current_json_path, current_js_path, daily_path, history_index_path, history_js_path)


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


def test_refresh_runtime_artifacts_rebuilds_when_matching_runtime_payload_is_too_old(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    stale_generated = (
        dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(seconds=render_compass_dashboard._RUNTIME_REUSE_MAX_AGE_SECONDS + 5)  # noqa: SLF001
    ).replace(microsecond=0)
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

    payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(**_refresh_kwargs(repo_root, runtime_dir))

    assert calls["build"]
    assert calls["write"]
    assert payload["runtime_contract"]["input_fingerprint"] == "matching-fingerprint"


def test_refresh_runtime_artifacts_shell_safe_rebuilds_stale_snapshot_in_bounded_mode(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    runtime_dir = repo_root / "odylith/compass/runtime"
    runtime_dir.mkdir(parents=True)
    current_json_path, current_js_path, daily_path, history_index_path, history_js_path = _runtime_paths(runtime_dir)
    history_index_path.parent.mkdir(parents=True, exist_ok=True)

    stale_generated = (
        dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(seconds=render_compass_dashboard._RUNTIME_REUSE_MAX_AGE_SECONDS + 30)  # noqa: SLF001
    ).replace(microsecond=0)
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
        requested_profile="full",
        runtime_mode="auto",
        reason="timeout",
        fallback_used=True,
    )

    updated = json.loads(current_json_path.read_text(encoding="utf-8"))

    assert marked is True
    assert "Requested Compass full refresh did not finish before the dashboard timeout." in updated["warning"]
    assert updated["runtime_contract"]["last_refresh_attempt"]["status"] == "failed"
    assert updated["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "full"
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
        "warning": "Requested Compass full refresh did not finish before the dashboard timeout.",
        "runtime_contract": {
            "version": "v1",
            "refresh_profile": "shell-safe",
            "standup_brief_schema_version": render_compass_dashboard.compass_standup_brief_narrator.STANDUP_BRIEF_SCHEMA_VERSION,
            "input_fingerprint": "matching-fingerprint",
            "last_refresh_attempt": {
                "status": "failed",
                "requested_profile": "full",
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
    monkeypatch.setattr(
        render_compass_dashboard,
        "_load_runtime_impl",
        lambda: (_ for _ in ()).throw(AssertionError("runtime implementation should not load on fast-path reuse")),
    )

    refreshed_payload, _paths = render_compass_dashboard.refresh_runtime_artifacts(
        **_refresh_kwargs(repo_root, runtime_dir),
        refresh_profile="shell-safe",
    )

    assert "warning" not in refreshed_payload
    assert refreshed_payload["runtime_contract"]["last_refresh_attempt"]["status"] == "passed"
    assert refreshed_payload["runtime_contract"]["last_refresh_attempt"]["requested_profile"] == "shell-safe"
