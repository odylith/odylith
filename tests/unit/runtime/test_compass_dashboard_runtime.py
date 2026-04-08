from __future__ import annotations

import datetime as dt
import gzip
import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_dashboard_runtime as runtime
from odylith.runtime.surfaces import compass_runtime_payload_runtime


def _fixed_now(monkeypatch, *, year: int, month: int, day: int) -> None:  # noqa: ANN001
    class _FixedDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls(year, month, day, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(runtime.dt, "datetime", _FixedDatetime)


def _payload(*, generated_utc: str) -> dict[str, object]:
    return {
        "generated_utc": generated_utc,
        "history": {
            "retention_days": 0,
            "dates": [],
        },
    }


def test_default_traceability_warning_filter_accepts_operator_warning() -> None:
    assert compass_runtime_payload_runtime._is_default_traceability_warning(  # noqa: SLF001
        {
            "severity": "warning",
            "audience": "operator",
            "surface_visibility": "default",
            "message": "Topology is incomplete.",
        }
    )


def test_default_traceability_warning_filter_rejects_maintainer_diagnostic() -> None:
    assert not compass_runtime_payload_runtime._is_default_traceability_warning(  # noqa: SLF001
        {
            "severity": "info",
            "audience": "maintainer",
            "surface_visibility": "diagnostics",
            "message": "Autofix skipped due to metadata conflict.",
        }
    )


def test_write_runtime_snapshots_archives_days_older_than_retention(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _fixed_now(monkeypatch, year=2026, month=3, day=20)
    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    history_dir = runtime_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    old_payload = json.dumps(_payload(generated_utc="2026-03-01T00:00:00Z"), indent=2) + "\n"
    (history_dir / "2026-03-01.v1.json").write_text(old_payload, encoding="utf-8")
    retained_payload = json.dumps(_payload(generated_utc="2026-03-05T00:00:00Z"), indent=2) + "\n"
    (history_dir / "2026-03-05.v1.json").write_text(retained_payload, encoding="utf-8")

    runtime._write_runtime_snapshots(
        repo_root=tmp_path,
        runtime_dir=runtime_dir,
        payload=_payload(generated_utc="2026-03-20T12:00:00Z"),
        retention_days=15,
    )

    index_payload = json.loads((history_dir / "index.v1.json").read_text(encoding="utf-8"))
    assert index_payload["retention_days"] == 15
    assert index_payload["dates"] == ["2026-03-20", "2026-03-05"]
    assert index_payload["restored_dates"] == []
    assert index_payload["archive"]["count"] == 1
    assert index_payload["archive"]["dates"] == ["2026-03-01"]

    archived_path = history_dir / "archive" / "2026-03-01.v1.json.gz"
    assert archived_path.is_file()
    assert not (history_dir / "2026-03-01.v1.json").exists()
    restored_payload = json.loads(gzip.decompress(archived_path.read_bytes()).decode("utf-8"))
    assert restored_payload["generated_utc"] == "2026-03-01T00:00:00Z"

    current_payload = json.loads((runtime_dir / "current.v1.json").read_text(encoding="utf-8"))
    assert current_payload["history"]["retention_days"] == 15
    assert current_payload["history"]["dates"] == ["2026-03-20", "2026-03-05"]
    assert current_payload["history"]["archive"]["count"] == 1

    embedded_raw = (history_dir / "embedded.v1.js").read_text(encoding="utf-8")
    embedded_payload = json.loads(
        embedded_raw.removeprefix("window.__ODYLITH_COMPASS_HISTORY__ = ").removesuffix(";\n")
    )
    assert embedded_payload["archive"]["dates"] == ["2026-03-01"]
    assert embedded_payload["snapshots"]["2026-03-01"]["generated_utc"] == "2026-03-01T00:00:00Z"
    assert embedded_payload["snapshots"]["2026-03-01"]["history"]["archive"]["count"] == 1


def test_restore_archived_history_dates_keeps_restored_day_active(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _fixed_now(monkeypatch, year=2026, month=3, day=20)
    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    history_dir = runtime_dir / "history"
    archive_dir = history_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_payload = json.dumps(_payload(generated_utc="2026-02-01T08:00:00Z"), indent=2) + "\n"
    (archive_dir / "2026-02-01.v1.json.gz").write_bytes(gzip.compress(archived_payload.encode("utf-8"), compresslevel=9))

    restored, already_active, pins_path = runtime.restore_archived_history_dates(
        repo_root=tmp_path,
        runtime_dir=runtime_dir,
        dates=["2026-02-01"],
    )
    assert restored == ["2026-02-01"]
    assert already_active == []
    assert (history_dir / "2026-02-01.v1.json").is_file()
    pins_payload = json.loads(pins_path.read_text(encoding="utf-8"))
    assert pins_payload["dates"] == ["2026-02-01"]

    runtime._write_runtime_snapshots(
        repo_root=tmp_path,
        runtime_dir=runtime_dir,
        payload=_payload(generated_utc="2026-03-20T12:00:00Z"),
        retention_days=15,
    )

    index_payload = json.loads((history_dir / "index.v1.json").read_text(encoding="utf-8"))
    assert "2026-02-01" in index_payload["dates"]
    assert index_payload["restored_dates"] == ["2026-02-01"]
    assert (history_dir / "2026-02-01.v1.json").is_file()


def test_self_host_risk_rows_surface_detached_source_local_product_repo() -> None:
    rows = runtime._self_host_risk_rows(
        snapshot={
            "repo_role": "product_repo",
            "posture": "detached_source_local",
            "runtime_source": "source_checkout",
            "release_eligible": False,
            "pinned_version": "0.1.0",
            "active_version": "source-local",
        },
        local_date="2026-03-27",
    )

    assert len(rows) == 1
    assert rows[0]["severity"] == "error"
    assert "detached source-local runtime" in str(rows[0]["message"])
    assert rows[0]["date"] == "2026-03-27"


def test_self_host_risk_rows_surface_unverified_wrapped_runtime() -> None:
    rows = runtime._self_host_risk_rows(
        snapshot={
            "repo_role": "product_repo",
            "posture": "pinned_release",
            "runtime_source": "wrapped_runtime",
            "release_eligible": False,
            "pinned_version": "0.1.0",
            "active_version": "0.1.0",
        },
        local_date="2026-03-27",
    )

    assert len(rows) == 1
    assert rows[0]["severity"] == "error"
    assert "local wrapped runtime" in str(rows[0]["message"])
    assert rows[0]["date"] == "2026-03-27"


def test_build_global_standup_fact_packet_includes_live_self_host_state() -> None:
    packet = runtime._build_global_standup_fact_packet(
        ws_rows=[],
        ws_index={},
        active_ws_rows=[],
        event_counts_by_ws={},
        next_actions=[],
        recent_completed=[],
        window_events=[],
        window_transactions=[],
        window_hours=24,
        risk_rows={"bugs": [], "traceability": [], "stale_diagrams": []},
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
        kpis={"touched_workstreams": 0, "recent_completed_plans": 0, "critical_risks": 0},
        self_host_snapshot={
            "repo_role": "product_repo",
            "posture": "pinned_release",
            "runtime_source": "pinned_runtime",
            "release_eligible": True,
            "pinned_version": "0.1.4",
            "active_version": "0.1.4",
            "launcher_present": True,
        },
        self_host_risks=[],
        now=dt.datetime(2026, 3, 30, 12, 0, 0, tzinfo=dt.timezone.utc),
    )

    assert packet["summary"]["self_host"]["active_version"] == "0.1.4"
    current_execution = next(section for section in packet["sections"] if section["key"] == "current_execution")
    assert any(fact["kind"] == "self_host_status" for fact in current_execution["facts"])


def test_build_scoped_standup_fact_packet_carries_live_self_host_summary_for_runtime_lane() -> None:
    packet = runtime._build_scoped_standup_fact_packet(
        row={
            "idea_id": "B-027",
            "title": "Odylith Lane Boundary, Runtime, and Toolchain Clarity",
            "status": "implementation",
            "why": {
                "why_now": (
                    "The current ambiguity shows up exactly where Odylith should be strongest: maintainer execution "
                    "in the product repo and consumer execution in repos with their own Python toolchains."
                ),
                "opportunity": "Make the supported lane model explicit and durable before changing mechanics.",
            },
            "plan": {
                "progress_ratio": 0.1,
                "done_tasks": 6,
                "total_tasks": 64,
            },
            "timeline": {
                "last_activity_iso": "2026-04-05T18:00:00Z",
            },
        },
        next_actions=[],
        recent_completed=[],
        window_events=[],
        window_transactions=[],
        window_hours=24,
        risk_rows={"bugs": [], "traceability": [], "stale_diagrams": []},
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
        self_host_snapshot={
            "repo_role": "product_repo",
            "posture": "detached_source_local",
            "runtime_source": "source_checkout",
            "release_eligible": False,
            "pinned_version": "0.1.7",
            "active_version": "source-local",
            "launcher_present": True,
        },
        now=dt.datetime(2026, 4, 5, 12, 0, 0, tzinfo=dt.timezone.utc),
    )

    assert packet["summary"]["self_host"]["posture"] == "detached_source_local"
    current_execution = next(section for section in packet["sections"] if section["key"] == "current_execution")
    assert any(fact["kind"] == "self_host_status" for fact in current_execution["facts"])


def test_build_global_standup_fact_packet_surfaces_live_self_host_risk() -> None:
    risks = runtime._self_host_risk_rows(
        snapshot={
            "repo_role": "product_repo",
            "posture": "diverged_verified_version",
            "runtime_source": "verified_runtime",
            "release_eligible": False,
            "pinned_version": "0.1.4",
            "active_version": "0.1.3",
            "launcher_present": True,
        },
        local_date="2026-03-30",
    )
    packet = runtime._build_global_standup_fact_packet(
        ws_rows=[],
        ws_index={},
        active_ws_rows=[],
        event_counts_by_ws={},
        next_actions=[],
        recent_completed=[],
        window_events=[],
        window_transactions=[],
        window_hours=24,
        risk_rows={"bugs": [], "traceability": [], "stale_diagrams": []},
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
        kpis={"touched_workstreams": 0, "recent_completed_plans": 0, "critical_risks": 0},
        self_host_snapshot={
            "repo_role": "product_repo",
            "posture": "diverged_verified_version",
            "runtime_source": "verified_runtime",
            "release_eligible": False,
            "pinned_version": "0.1.4",
            "active_version": "0.1.3",
            "launcher_present": True,
        },
        self_host_risks=risks,
        now=dt.datetime(2026, 3, 30, 12, 0, 0, tzinfo=dt.timezone.utc),
    )

    risks_to_watch = next(section for section in packet["sections"] if section["key"] == "risks_to_watch")
    assert any(fact["kind"] == "self_host_posture" for fact in risks_to_watch["facts"])


def test_compact_shadowed_auto_transactions_suppresses_shadowed_auto_global_row() -> None:
    payloads = [
        {
            "id": "txn:auto",
            "transaction_id": "txn:global:auto-global-0001",
            "session_id": "",
            "end_ts_iso": "2026-03-29T08:00:00Z",
            "files": [
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
                "odylith/technical-plans/in-progress/example.md",
            ],
            "workstreams": ["B-011"],
            "events": [
                {"kind": "implementation", "summary": "Updated Compass runtime"},
                {"kind": "plan_update", "summary": "Plan updated"},
            ],
        },
        {
            "id": "txn:explicit",
            "transaction_id": "custom-transaction",
            "session_id": "session-123",
            "end_ts_iso": "2026-03-29T08:05:00Z",
            "files": [
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            ],
            "workstreams": ["B-011"],
            "events": [
                {"kind": "implementation", "summary": "Updated Compass runtime"},
                {"kind": "decision", "summary": "Pinned the Compass render path"},
            ],
        },
    ]

    compacted = runtime._compact_shadowed_auto_transactions(payloads)

    assert [row["id"] for row in compacted] == ["txn:explicit"]


def test_compact_shadowed_auto_transactions_keeps_unrelated_auto_global_row() -> None:
    payloads = [
        {
            "id": "txn:auto",
            "transaction_id": "txn:global:auto-global-0001",
            "session_id": "",
            "end_ts_iso": "2026-03-29T08:00:00Z",
            "files": [
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
                "odylith/technical-plans/in-progress/example.md",
            ],
            "workstreams": ["B-011"],
            "events": [
                {"kind": "implementation", "summary": "Updated Compass runtime"},
                {"kind": "plan_update", "summary": "Plan updated"},
            ],
        },
        {
            "id": "txn:explicit",
            "transaction_id": "custom-transaction",
            "session_id": "session-123",
            "end_ts_iso": "2026-03-29T08:05:00Z",
            "files": [
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            ],
            "workstreams": ["B-010"],
            "events": [
                {"kind": "implementation", "summary": "Updated Compass runtime"},
                {"kind": "decision", "summary": "Pinned the Compass render path"},
            ],
        },
    ]

    compacted = runtime._compact_shadowed_auto_transactions(payloads)

    assert [row["id"] for row in compacted] == ["txn:auto", "txn:explicit"]


def test_generated_only_local_change_event_detection() -> None:
    assert runtime._is_generated_only_local_change_event(
        {
            "kind": "local_change",
            "files": [
                "odylith/compass/runtime/current.v1.json",
                "odylith/compass/runtime/current.v1.js",
            ],
        }
    )
    assert not runtime._is_generated_only_local_change_event(
        {
            "kind": "local_change",
            "files": [
                "odylith/compass/runtime/current.v1.json",
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            ],
        }
    )


def test_generated_only_transaction_detection() -> None:
    assert runtime._is_generated_only_transaction(
        {
            "files": [
                "odylith/compass/runtime/current.v1.json",
                "odylith/compass/runtime/current.v1.js",
            ]
        }
    )


def test_global_brief_should_use_provider_for_24h_even_with_cache(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime.compass_standup_brief_narrator,
        "has_reusable_cached_brief",
        lambda **_kwargs: True,
    )

    assert runtime._global_brief_should_use_provider(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
    )


def test_global_brief_should_use_provider_for_48h_even_with_cache(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime.compass_standup_brief_narrator,
        "has_reusable_cached_brief",
        lambda **_kwargs: True,
    )

    assert runtime._global_brief_should_use_provider(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "48h"},
        window_hours=48,
    )


def test_global_brief_should_use_provider_for_48h_cache_miss(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime.compass_standup_brief_narrator,
        "has_reusable_cached_brief",
        lambda **_kwargs: False,
    )

    assert runtime._global_brief_should_use_provider(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "48h"},
        window_hours=48,
    )


def test_global_brief_provider_allowed_uses_default_policy_for_shell_safe(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime,
        "_global_brief_should_use_provider",
        lambda **_kwargs: True,
    )

    assert runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
        refresh_profile="shell-safe",
    )


def test_global_brief_provider_allowed_uses_default_policy_for_full_refresh(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime,
        "_global_brief_should_use_provider",
        lambda **_kwargs: False,
    )

    assert not runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "48h"},
        window_hours=48,
        refresh_profile="full",
    )

    monkeypatch.setattr(
        runtime,
        "_global_brief_should_use_provider",
        lambda **_kwargs: True,
    )

    assert runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
        refresh_profile="full",
    )


def test_scoped_brief_provider_allowed_disables_provider_for_shell_safe() -> None:
    assert not compass_runtime_payload_runtime._scoped_brief_provider_allowed(refresh_profile="shell-safe")  # noqa: SLF001


def test_scoped_brief_provider_allowed_uses_provider_for_full_refresh() -> None:
    assert compass_runtime_payload_runtime._scoped_brief_provider_allowed(refresh_profile="full")  # noqa: SLF001


def test_assert_full_refresh_brief_ready_accepts_ready_cache_without_notice() -> None:
    compass_runtime_payload_runtime._assert_full_refresh_brief_ready(  # noqa: SLF001
        brief={"status": "ready", "source": "cache"},
        window_hours=24,
        scope_label="global",
    )


def test_assert_full_refresh_brief_ready_rejects_non_clean_briefs() -> None:
    with pytest.raises(RuntimeError, match="global 24h window; got status=ready, source=deterministic"):
        compass_runtime_payload_runtime._assert_full_refresh_brief_ready(  # noqa: SLF001
            brief={"status": "ready", "source": "deterministic"},
            window_hours=24,
            scope_label="global",
        )

    with pytest.raises(RuntimeError, match="B-025 48h window; got status=ready, source=cache"):
        compass_runtime_payload_runtime._assert_full_refresh_brief_ready(  # noqa: SLF001
            brief={
                "status": "ready",
                "source": "cache",
                "notice": {"reason": "provider_timeout"},
            },
            window_hours=48,
            scope_label="B-025",
        )


def test_generated_only_transaction_detection_keeps_source_mixed_rows() -> None:
    assert not runtime._is_generated_only_transaction(
        {
            "files": [
                "odylith/compass/runtime/current.v1.json",
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            ]
        }
    )
