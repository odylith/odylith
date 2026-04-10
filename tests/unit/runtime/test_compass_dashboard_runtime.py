from __future__ import annotations

import datetime as dt
import gzip
import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_dashboard_runtime as runtime
from odylith.runtime.surfaces import compass_runtime_payload_runtime
from odylith.runtime.surfaces import compass_standup_brief_narrator
from odylith.runtime.surfaces import compass_standup_runtime_reuse


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


def test_workstream_window_activity_detects_recent_completion_without_git_activity() -> None:
    assert compass_runtime_payload_runtime._workstream_has_window_activity(  # noqa: SLF001
        ws_id="B-003",
        recent_completed=[{"backlog": "B-003", "plan": "plan.md"}],
        window_events=[],
        window_transactions=[],
    )


def test_workstream_window_activity_detects_events_and_transactions() -> None:
    assert compass_runtime_payload_runtime._workstream_has_window_activity(  # noqa: SLF001
        ws_id="B-003",
        recent_completed=[],
        window_events=[{"workstreams": ["B-003"]}],
        window_transactions=[],
    )
    assert compass_runtime_payload_runtime._workstream_has_window_activity(  # noqa: SLF001
        ws_id="B-003",
        recent_completed=[],
        window_events=[],
        window_transactions=[{"workstreams": ["B-003"]}],
    )
    assert not compass_runtime_payload_runtime._workstream_has_window_activity(  # noqa: SLF001
        ws_id="B-003",
        recent_completed=[],
        window_events=[],
        window_transactions=[],
    )


def test_row_is_governance_only_local_change_rejects_scoped_verification() -> None:
    row = {
        "kind": "local_change",
        "workstreams": ["B-040"],
        "files": [
            "odylith/radar/source/ideas/2026-04/2026-04-01-odylith-runtime-integrity-supply-chain-hardening-and-security-posture.md",
        ],
    }

    assert compass_runtime_payload_runtime._row_is_governance_only_local_change(row)  # noqa: SLF001
    assert not compass_runtime_payload_runtime._row_is_verified_scoped_signal(row)  # noqa: SLF001


def test_row_is_verified_scoped_signal_rejects_broad_fanout_transaction() -> None:
    row = {
        "workstreams": ["B-001", "B-002", "B-003", "B-004", "B-005"],
        "files": [
            "odylith/radar/source/ideas/2026-03/example.md",
        ],
        "events": [{"kind": "local_change"}],
    }

    assert not compass_runtime_payload_runtime._row_is_verified_scoped_signal(row)  # noqa: SLF001


def test_verified_scoped_window_ids_require_verified_rows_or_recent_completion() -> None:
    verified = compass_runtime_payload_runtime._verified_scoped_window_ids(  # noqa: SLF001
        known_ids={"B-040", "B-064"},
        recent_completed=[{"backlog": "B-064"}],
        window_events=[
            {
                "kind": "local_change",
                "workstreams": ["B-040"],
                "files": [
                    "odylith/radar/source/ideas/2026-04/2026-04-01-odylith-runtime-integrity-supply-chain-hardening-and-security-posture.md",
                ],
            }
        ],
        window_transactions=[
            {
                "workstreams": ["B-064"],
                "files": ["odylith/technical-plans/in-progress/example.md"],
                "events": [{"kind": "plan_update"}],
            }
        ],
    )

    assert verified == {"B-064"}


def test_scoped_packets_match_for_cross_window_ignores_window_only_fields() -> None:
    packet_24h = {
        "window": "24h",
        "scope": {"mode": "scoped", "idea_id": "B-025"},
        "summary": {"window_hours": 24, "storyline": {"proof": "Latest proof stayed concrete."}},
        "facts": [{"id": "F-001", "text": "Latest proof stayed concrete."}],
    }
    packet_48h = {
        "window": "48h",
        "scope": {"mode": "scoped", "idea_id": "B-025"},
        "summary": {"window_hours": 48, "storyline": {"proof": "Latest proof stayed concrete."}},
        "facts": [{"id": "F-001", "text": "Latest proof stayed concrete."}],
    }

    assert compass_runtime_payload_runtime._scoped_packets_match_for_cross_window(  # noqa: SLF001
        left=packet_24h,
        right=packet_48h,
    )


def test_reuse_scoped_brief_for_window_rekeys_fingerprint_without_notice() -> None:
    packet = {
        "window": "48h",
        "scope": {"mode": "scoped", "idea_id": "B-025"},
        "summary": {"window_hours": 48},
        "facts": [{"id": "F-001", "text": "Latest proof stayed concrete."}],
    }
    brief = {
        "status": "ready",
        "source": "provider",
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [{"text": "Latest proof stayed concrete.", "fact_ids": ["F-001"]}],
            }
        ],
    }

    reused = compass_runtime_payload_runtime._reuse_scoped_brief_for_window(  # noqa: SLF001
        brief=brief,
        fact_packet=packet,
        generated_utc="2026-04-08T21:00:00Z",
    )

    assert reused["status"] == "ready"
    assert reused["source"] == "provider"
    assert "notice" not in reused
    assert reused["fingerprint"] == compass_standup_brief_narrator.standup_brief_fingerprint(fact_packet=packet)


def test_compose_global_fact_packet_from_scoped_briefs_uses_scoped_narration_and_coverage() -> None:
    base_packet = {
        "version": "v1",
        "window": "24h",
        "scope": {"mode": "global", "label": "Global"},
        "summary": {"window_hours": 24},
        "sections": [
            {"key": "completed", "label": "Completed in this window", "facts": []},
            {
                "key": "current_execution",
                "label": "Current execution",
                "facts": [
                    {
                        "id": "F-010",
                        "text": "Work moved across 3 workstreams: B-025, B-061, and B-063.",
                        "kind": "window_coverage",
                        "source": "portfolio",
                        "workstreams": ["B-025", "B-061", "B-063"],
                    }
                ],
            },
            {"key": "next_planned", "label": "Next planned", "facts": []},
            {"key": "risks_to_watch", "label": "Risks to watch", "facts": []},
        ],
    }
    scoped_briefs = {
        "B-025": {
            "status": "ready",
            "sections": [
                {"key": "completed", "bullets": [{"text": "Closed the refresh retry loop."}]},
                {"key": "current_execution", "bullets": [{"text": "Compass refresh is now working through cheaper scoped packs."}]},
                {"key": "next_planned", "bullets": [{"text": "Land the next round of provider hardening."}]},
                {"key": "risks_to_watch", "bullets": [{"text": "Global narration can still drift if coverage gets dropped."}]},
            ],
        }
    }

    packet = compass_runtime_payload_runtime._compose_global_fact_packet_from_scoped_briefs(  # noqa: SLF001
        base_fact_packet=base_packet,
        scoped_briefs_by_scope=scoped_briefs,
        ordered_scope_ids=["B-025", "B-061", "B-063"],
    )

    current_execution = next(section for section in packet["sections"] if section["key"] == "current_execution")
    texts = [fact["text"] for fact in current_execution["facts"]]
    assert "Compass refresh is now working through cheaper scoped packs." in texts
    assert "Work moved across 3 workstreams: B-025, B-061, and B-063." in texts


def test_inactive_scoped_brief_uses_quiet_window_copy() -> None:
    brief = compass_runtime_payload_runtime._inactive_scoped_standup_brief(  # noqa: SLF001
        ws_id="B-003",
        window_hours=24,
        generated_utc="2026-04-08T23:00:00Z",
    )

    assert brief["status"] == "unavailable"
    assert brief["diagnostics"]["reason"] == "scoped_window_inactive"
    assert brief["diagnostics"]["title"] == "Nothing moved in this window"
    assert "B-003 was quiet in the last 24 hours" in brief["diagnostics"]["message"]


def test_prior_runtime_state_rejects_mismatched_brief_schema() -> None:
    state = compass_standup_runtime_reuse.prior_runtime_state(
        payload={
            "runtime_contract": {
                "standup_brief_schema_version": "legacy",
            },
            "standup_runtime": {"24h": {"global_reuse_fingerprint": "x"}},
            "standup_brief": {"24h": {"status": "ready"}},
        }
    )

    assert state == {}


def test_reuse_ready_brief_returns_cache_ready_payload_without_notice() -> None:
    brief = {
        "status": "ready",
        "source": "provider",
        "sections": [
            {
                "key": "completed",
                "label": "Completed in this window",
                "bullets": [{"text": "Closed the loop."}],
            }
        ],
        "evidence_lookup": {"F-001": {"kind": "fact", "text": "Closed the loop."}},
    }

    reused = compass_standup_runtime_reuse.reuse_ready_brief(
        brief=brief,
        generated_utc="2026-04-09T17:00:00Z",
        fingerprint="salient:test",
    )

    assert reused["status"] == "ready"
    assert reused["source"] == "cache"
    assert reused["cache_mode"] == "fallback"
    assert reused["fingerprint"] == "salient:test"
    assert "notice" not in reused


def test_scoped_reuse_fingerprint_changes_when_activity_changes() -> None:
    base_row = {
        "idea_id": "B-025",
        "title": "Compass refresh hardening",
        "status": "implementation",
        "activity": {"24h": {"commit_count": 1, "local_change_count": 2, "file_touch_count": 3}},
        "plan": {"progress_ratio": 0.5, "done_tasks": 5, "total_tasks": 10, "next_tasks": ["Land the retry fix."]},
        "timeline": {"last_activity_iso": "2026-04-09T09:00:00Z", "eta_days": 3, "eta_confidence": "medium"},
    }

    left = compass_standup_runtime_reuse.scoped_reuse_fingerprint(
        row=base_row,
        window_hours=24,
        next_action_tokens=["Land the retry fix."],
        completed_deliverables=["plan-a.md"],
        execution_updates=[{"summary": "Shipped the retry hardening.", "kind": "implementation"}],
        transaction_updates=[],
        risk_summary="No critical blockers.",
        self_host_snapshot={"posture": "pinned_release", "active_version": "0.1.11"},
    )
    right = compass_standup_runtime_reuse.scoped_reuse_fingerprint(
        row={
            **base_row,
            "activity": {"24h": {"commit_count": 2, "local_change_count": 2, "file_touch_count": 3}},
        },
        window_hours=24,
        next_action_tokens=["Land the retry fix."],
        completed_deliverables=["plan-a.md"],
        execution_updates=[{"summary": "Shipped the retry hardening.", "kind": "implementation"}],
        transaction_updates=[],
        risk_summary="No critical blockers.",
        self_host_snapshot={"posture": "pinned_release", "active_version": "0.1.11"},
    )

    assert left != right


def test_scoped_reuse_fingerprint_changes_when_visible_progress_semantics_change() -> None:
    base_row = {
        "idea_id": "B-068",
        "title": "Context Engine Benchmark Family and Grounding Quality Gates",
        "status": "implementation",
        "activity": {"24h": {"commit_count": 0, "local_change_count": 2, "file_touch_count": 2}},
        "plan": {
            "progress_ratio": 0.0,
            "done_tasks": 0,
            "total_tasks": 15,
            "progress_classification": "active_untracked",
            "display_progress_label": "Checklist 0/15",
            "display_progress_state": "checklist_only",
            "next_tasks": ["Land the family acceptance checks."],
        },
        "timeline": {"last_activity_iso": "2026-04-09T20:00:00Z", "eta_days": None, "eta_confidence": "low"},
    }

    left = compass_standup_runtime_reuse.scoped_reuse_fingerprint(
        row=base_row,
        window_hours=24,
        next_action_tokens=["Land the family acceptance checks."],
        completed_deliverables=[],
        execution_updates=[],
        transaction_updates=[],
        risk_summary="No critical blockers.",
        self_host_snapshot={"posture": "pinned_release", "active_version": "0.1.11"},
    )
    right = compass_standup_runtime_reuse.scoped_reuse_fingerprint(
        row={
            **base_row,
            "plan": {
                **base_row["plan"],
                "progress_ratio": 0.7857,
                "done_tasks": 11,
                "total_tasks": 14,
                "progress_classification": "tracked",
                "display_progress_label": "79% progress",
                "display_progress_state": "percent",
            },
        },
        window_hours=24,
        next_action_tokens=["Land the family acceptance checks."],
        completed_deliverables=[],
        execution_updates=[],
        transaction_updates=[],
        risk_summary="No critical blockers.",
        self_host_snapshot={"posture": "pinned_release", "active_version": "0.1.11"},
    )

    assert left != right


def test_cached_governance_summary_for_shell_safe_reuses_current_payload(tmp_path: Path) -> None:
    current_path = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json"
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text('{"governance": {"changed_paths": ["src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py"]}}', encoding="utf-8")

    summary = compass_runtime_payload_runtime._cached_governance_summary_for_shell_safe(  # noqa: SLF001
        repo_root=tmp_path,
        refresh_profile="shell-safe",
    )

    assert summary == {
        "changed_paths": ["src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py"],
    }


def test_cached_governance_summary_reuses_current_payload_for_shell_safe(tmp_path: Path) -> None:
    current_path = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json"
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text('{"governance": {"changed_paths": ["shell-safe"]}}', encoding="utf-8")

    assert compass_runtime_payload_runtime._cached_governance_summary_for_shell_safe(  # noqa: SLF001
        repo_root=tmp_path,
        refresh_profile="shell-safe",
    ) == {"changed_paths": ["shell-safe"]}


def test_cached_odylith_runtime_summary_for_shell_safe_reuses_current_payload(tmp_path: Path) -> None:
    current_path = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json"
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text('{"odylith_runtime": {"memory_ready": true, "packet_count": 42}}', encoding="utf-8")

    summary = compass_runtime_payload_runtime._cached_odylith_runtime_summary_for_shell_safe(  # noqa: SLF001
        repo_root=tmp_path,
        refresh_profile="shell-safe",
    )

    assert summary == {
        "memory_ready": True,
        "packet_count": 42,
    }


def test_cached_odylith_runtime_summary_reuses_current_payload_for_shell_safe(tmp_path: Path) -> None:
    current_path = tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json"
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text('{"odylith_runtime": {"memory_ready": true}}', encoding="utf-8")

    assert compass_runtime_payload_runtime._cached_odylith_runtime_summary_for_shell_safe(  # noqa: SLF001
        repo_root=tmp_path,
        refresh_profile="shell-safe",
    ) == {"memory_ready": True}


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


def test_build_global_standup_fact_packet_marks_untracked_implementation_as_active_not_planning() -> None:
    packet = runtime._build_global_standup_fact_packet(
        ws_rows=[],
        ws_index={
            "B-068": {
                "idea_id": "B-068",
                "title": "Context Engine Benchmark Family and Grounding Quality Gates",
                "status": "implementation",
                "plan": {
                    "total_tasks": 15,
                    "done_tasks": 0,
                    "progress_ratio": 0.0,
                    "display_progress_label": "Checklist 0/15",
                },
            }
        },
        active_ws_rows=[
            {
                "idea_id": "B-068",
                "title": "Context Engine Benchmark Family and Grounding Quality Gates",
                "status": "implementation",
                "plan": {
                    "total_tasks": 15,
                    "done_tasks": 0,
                    "progress_ratio": 0.0,
                    "display_progress_label": "Checklist 0/15",
                },
            }
        ],
        event_counts_by_ws={},
        next_actions=[],
        recent_completed=[],
        window_events=[],
        window_transactions=[],
        window_hours=24,
        risk_rows={"bugs": [], "traceability": [], "stale_diagrams": []},
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
        kpis={"touched_workstreams": 1, "recent_completed_plans": 0, "critical_risks": 0},
        self_host_snapshot={},
        self_host_risks=[],
        now=dt.datetime(2026, 4, 9, 12, 0, 0, tzinfo=dt.timezone.utc),
    )

    current_execution = next(section for section in packet["sections"] if section["key"] == "current_execution")
    posture_facts = [fact for fact in current_execution["facts"] if fact["kind"] == "portfolio_posture"]
    assert posture_facts
    assert "implementation" in posture_facts[0]["text"].lower()
    assert "planning setup" not in posture_facts[0]["text"].lower()


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


def test_global_brief_provider_is_disabled_for_bounded_refresh() -> None:
    assert not runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
        refresh_profile="shell-safe",
    )
    assert not runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "48h"},
        window_hours=48,
        refresh_profile="shell-safe",
    )


def test_global_brief_provider_allowed_uses_cache_for_shell_safe_when_reusable(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime.compass_standup_brief_narrator,
        "has_reusable_cached_brief",
        lambda **_kwargs: True,
    )

    assert not runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
        refresh_profile="shell-safe",
    )


def test_global_brief_provider_allowed_disables_provider_for_shell_safe_cache_miss(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime.compass_standup_brief_narrator,
        "has_reusable_cached_brief",
        lambda **_kwargs: False,
    )

    assert not runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
        refresh_profile="shell-safe",
    )


def test_global_brief_provider_allowed_stays_disabled_on_shell_safe_policy() -> None:
    assert not runtime._global_brief_provider_allowed(
        repo_root=Path("/tmp/repo"),
        fact_packet={"window": "24h"},
        window_hours=24,
        refresh_profile="shell-safe",
    )


def test_scoped_brief_provider_allowed_disables_provider_for_low_rung_scope() -> None:
    assert not compass_runtime_payload_runtime._scoped_brief_provider_allowed(  # noqa: SLF001
        refresh_profile="shell-safe",
        scope_signal={"budget_class": "cache_only"},
    )


def test_scoped_brief_provider_allowed_enables_provider_for_high_rung_scope() -> None:
    assert compass_runtime_payload_runtime._scoped_brief_provider_allowed(  # noqa: SLF001
        refresh_profile="shell-safe",
        scope_signal={"budget_class": "escalated_reasoning"},
    )


def test_reusable_brief_sections_for_fact_packet_requires_voice_valid_sections(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        compass_standup_brief_narrator,
        "_validated_cached_sections",
        lambda **_kwargs: None,
    )

    assert compass_runtime_payload_runtime._reusable_brief_sections_for_fact_packet(  # noqa: SLF001
        brief={
            "status": "ready",
            "source": "provider",
            "sections": [
                {
                    "key": "completed",
                    "label": "Completed in this window",
                    "bullets": [{"text": "Bad cached line.", "fact_ids": ["F-001"]}],
                }
            ],
        },
        fact_packet={"facts": [{"id": "F-001", "section_key": "completed", "text": "Good fact."}]},
    ) is None


def test_reusable_brief_sections_for_fact_packet_accepts_clean_ready_brief(monkeypatch) -> None:  # noqa: ANN001
    sections = [{"key": "completed", "label": "Completed in this window", "bullets": []}]
    monkeypatch.setattr(
        compass_standup_brief_narrator,
        "_validated_cached_sections",
        lambda **_kwargs: sections,
    )

    assert compass_runtime_payload_runtime._reusable_brief_sections_for_fact_packet(  # noqa: SLF001
        brief={
            "status": "ready",
            "source": "provider",
            "sections": [
                {
                    "key": "completed",
                    "label": "Completed in this window",
                    "bullets": [{"text": "Good cached line.", "fact_ids": ["F-001"]}],
                }
            ],
        },
        fact_packet={"facts": [{"id": "F-001", "section_key": "completed", "text": "Good fact."}]},
    ) == sections


def test_generated_only_transaction_detection_keeps_source_mixed_rows() -> None:
    assert not runtime._is_generated_only_transaction(
        {
            "files": [
                "odylith/compass/runtime/current.v1.json",
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
            ]
        }
    )
