from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_outcome_digest_runtime as outcome
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator
from odylith.runtime.surfaces import compass_standup_fact_packets as packets


def _scope_inputs() -> dict:
    return {
        "ws_rows": [],
        "ws_index": {},
        "active_ws_rows": [],
        "event_counts_by_ws": {},
        "next_actions": [],
        "recent_completed": [],
        "window_events": [],
        "window_transactions": [],
        "window_hours": 24,
    }


def _packet(**overrides: object) -> dict:
    inputs = {
        **_scope_inputs(),
        "risk_rows": {"bugs": [], "traceability": [], "stale_diagrams": []},
        "risk_summary": "Risk posture: no critical blockers are currently surfaced.",
        "kpis": {},
        "self_host_snapshot": {},
        "self_host_risks": [],
        "now": dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc),
        **overrides,
    }
    return packets._build_global_standup_fact_packet(**inputs)


def test_empty_scope_has_no_invented_workstream_or_forecast() -> None:
    packet = _packet()

    assert not {"direction", "timeline"}.intersection(fact["kind"] for fact in packet["facts"])
    for key in ("flagship_lane", "direction", "forcing_function"):
        assert packet["summary"]["storyline"][key] == ""
    next_facts = [fact for fact in packet["facts"] if fact["section_key"] == "next_planned"]
    assert any("Radar" in fact["text"] for fact in next_facts)


@pytest.mark.parametrize("overrides", [
    {},
    {"window_events": [{"ts_iso": "invalid timestamp", "workstreams": []}]},
    {"window_transactions": [{"end_ts_iso": "invalid timestamp", "workstreams": []}]},
])
def test_absent_workstream_and_evidence_do_not_create_stale_freshness(overrides: dict) -> None:
    packet = _packet(**overrides)

    assert packet["summary"]["freshness"] == {"bucket": "unknown", "latest_evidence_utc": "", "source": "none"}
    assert not any(fact["kind"] == "freshness" for fact in packet["facts"])
    visible = " ".join(fact["text"] for fact in packet["facts"])
    assert "Freshness signal" not in visible
    assert "this lane" not in visible
    assert "momentum claims" not in visible
    assert "No implementation lane is moving right now." in visible


@pytest.mark.parametrize("last_activity", ["", "2026-09-04T00:00:00Z"])
def test_real_workstream_without_recent_evidence_retains_stale_warning(last_activity: str) -> None:
    row = {"idea_id": "B-002", "title": "Reliable search", "status": "in-progress", "timeline": {"last_activity_iso": last_activity}}
    packet = _packet(ws_rows=[row], ws_index={"B-002": row}, active_ws_rows=[row])

    assert packet["summary"]["freshness"]["bucket"] == "stale"
    freshness = next(fact for fact in packet["facts"] if fact["kind"] == "freshness")
    assert "Reliable search" in freshness["text"]
    assert "Freshness signal is stale" in freshness["text"]


@pytest.mark.parametrize("source,overrides", [
    ("event", {"window_events": [{"ts_iso": "2026-09-04T00:00:00Z", "workstreams": []}]}),
    ("transaction", {"window_transactions": [{"end_ts_iso": "2026-09-04T00:00:00Z", "workstreams": []}]}),
])
def test_real_global_evidence_retains_freshness_without_inventing_a_lane(source: str, overrides: dict) -> None:
    packet = _packet(**overrides)

    assert packet["summary"]["freshness"]["bucket"] == "stale"
    assert packet["summary"]["freshness"]["source"] == source
    freshness = next(fact for fact in packet["facts"] if fact["kind"] == "freshness")
    assert "the repository" in freshness["text"]
    assert "this lane" not in freshness["text"]


@pytest.mark.parametrize("owner", [packets, outcome])
def test_empty_scope_never_estimates_an_absent_workstream(monkeypatch: pytest.MonkeyPatch, owner) -> None:
    def reject_estimate(_row):
        raise AssertionError("There is no workstream to estimate")

    monkeypatch.setattr(owner, "_estimate_remaining_days", reject_estimate)
    if owner is packets:
        _packet()
    else:
        outcome._build_outcome_digest_global(**_scope_inputs(), risks_summary="No critical risks.")


def test_no_active_scope_preserves_completed_work_and_actual_risks() -> None:
    historical = {"idea_id": "B-001", "title": "Verified import", "status": "done"}
    packet = _packet(
        ws_index={"B-001": historical},
        recent_completed=[{"backlog": "B-001", "plan": "verified-import.plan.md"}],
        risk_rows={"bugs": [{"severity": "P1", "title": "Readback failed"}]},
        self_host_risks=[{"severity": "error", "message": "Installed runtime is unavailable."}],
    )

    assert any("Verified import" in fact["text"] for fact in packet["facts"] if fact["section_key"] == "completed")
    risks = [fact for fact in packet["facts"] if fact["section_key"] == "risks_to_watch"]
    assert {"bug", "self_host_posture"}.issubset(fact["kind"] for fact in risks)
    assert not any(fact["kind"] == "timeline" for fact in packet["facts"])
    assert not any(fact["kind"] == "freshness" for fact in packet["facts"])


@pytest.mark.parametrize("active", [True, False])
def test_real_workstream_keeps_source_backed_direction_and_estimate(active: bool) -> None:
    row = {
        "idea_id": "B-002",
        "title": "Reliable search",
        "status": "in-progress" if active else "queued",
        "timeline": {"eta_days": 3, "eta_confidence": "medium"},
        "plan": {"progress_ratio": 0.5},
    }
    packet = _packet(ws_rows=[row], ws_index={"B-002": row}, active_ws_rows=[row] if active else [])

    current = [fact for fact in packet["facts"] if fact["section_key"] == "current_execution"]
    direction = next(fact for fact in current if fact["kind"] == "direction")
    timeline = next(fact for fact in current if fact["kind"] == "timeline")
    assert "Reliable search" in direction["text"]
    assert "3 days" in timeline["text"]
    assert "medium" in timeline["text"]


def test_deferred_narrator_does_not_claim_work_is_underway(tmp_path: Path) -> None:
    class ForbiddenProvider:
        def generate_structured(self, **_kwargs):
            raise AssertionError("No live narration is allowed")

    brief = narrator.build_standup_brief(
        repo_root=tmp_path,
        fact_packet=_packet(),
        generated_utc="2026-09-07T00:00:00Z",
        provider=ForbiddenProvider(),
        allow_provider=False,
    )

    assert brief["status"] == "unavailable"
    diagnostics = brief["diagnostics"]
    assert diagnostics["reason"] == "provider_deferred"
    assert diagnostics["title"] == "Local runtime facts"
    assert "being prepared" not in diagnostics["message"]
    assert "not available" in diagnostics["message"]
    digest = " ".join(diagnostics["fallback_digest"])
    assert "Radar" in digest
    assert "current priority lane" not in digest
    assert "heuristically" not in digest
    assert "forcing function" not in digest
    assert "Freshness signal" not in digest
    assert "momentum claims" not in digest


def test_empty_legacy_digest_retains_history_without_fabricating_current_work() -> None:
    digest = outcome._build_outcome_digest_global(
        **{
            **_scope_inputs(),
            "ws_index": {"B-001": {"idea_id": "B-001", "title": "Verified import"}},
            "recent_completed": [{"backlog": "B-001", "plan": "verified-import.plan.md"}],
        },
        risks_summary="Risk posture: readback is blocked.",
    )

    text = " ".join(digest)
    assert "Verified import" in text
    assert "readback is blocked" in text
    assert "Radar" in text
    assert "current priority lane" not in text
    assert "Implementation setup is active" not in text
    assert "Timeline:" not in text
    assert "Why this matters:" not in text
