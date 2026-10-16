import datetime as dt

from odylith.runtime.surfaces import compass_briefing_support as support


def test_normalize_action_task_rewrites_passive_voice() -> None:
    assert (
        support._normalize_action_task("Registry bindings are backfilled across dependent lanes.")
        == "backfill Registry bindings across dependent lanes"
    )


def test_latest_evidence_marker_prefers_transaction_signal() -> None:
    older = dt.datetime(2026, 4, 18, 9, 0, tzinfo=dt.timezone.utc)
    newer = dt.datetime(2026, 4, 18, 11, 0, tzinfo=dt.timezone.utc)

    latest, source = support._latest_evidence_marker(
        window_events=[
            {
                "workstreams": ["B-123"],
                "ts": older,
            }
        ],
        window_transactions=[
            {
                "workstreams": ["B-123"],
                "end_ts_iso": newer.isoformat(),
            }
        ],
        ws_id="B-123",
        fallback_last_activity_iso="2026-04-18T12:00:00+00:00",
    )

    assert latest == newer
    assert source == "transaction"


def test_latest_evidence_marker_uses_last_activity_fallback_when_needed() -> None:
    latest, source = support._latest_evidence_marker(
        window_events=[],
        window_transactions=[],
        ws_id="B-123",
        fallback_last_activity_iso="2026-04-18T12:00:00+00:00",
    )

    assert latest == dt.datetime(2026, 4, 18, 12, 0, tzinfo=dt.timezone.utc)
    assert source == "last_activity"


def test_missing_action_and_risk_omit_fabricated_next_and_watch() -> None:
    assert support._scoped_fallback_next_text(
        label="Reliable search", purpose="reviewers can trust results", status="planning",
        done_tasks=0, total_tasks=3, freshness_bucket="fresh",
    ) == ""
    assert support._global_fallback_next_text(
        primary_label="Reliable search", primary_purpose="reviewers can trust results",
        active_count=2, freshness_bucket="fresh",
    ) == ""
    assert support._scoped_fallback_risk_text(
        label="Reliable search", total_tasks=3, done_tasks=0, eta_days=0,
        eta_source="none", wave_context="Execution wave context: active lane",
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
        freshness_bucket="fresh", freshness_text="",
    ) == ""
    assert support._global_fallback_risk_text(
        active_ws_rows=[{"idea_id": "B-001", "title": "Reliable search"}],
        primary_label="Reliable search", eta_days=12, eta_source="heuristic",
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
        freshness_bucket="fresh", freshness_text="",
    ) == ""
    assert support._risk_facts(
        ws_id=None, risk_rows={"bugs": [], "traceability": [], "stale_diagrams": []},
        risk_summary="Risk posture: no critical blockers are currently surfaced.",
    ) == []


def test_recorded_risk_and_freshness_remain_visible() -> None:
    assert support._global_fallback_risk_text(
        active_ws_rows=[], primary_label="Reliable search", eta_days=0,
        eta_source="none", risk_summary="Risk posture: readback is blocked.",
        freshness_bucket="fresh", freshness_text="",
    ) == "Readback is blocked."
    assert support._scoped_fallback_risk_text(
        label="Reliable search", total_tasks=0, done_tasks=0, eta_days=0,
        eta_source="none", wave_context="", risk_summary="",
        freshness_bucket="stale", freshness_text="Freshness signal is stale: latest proof is aging.",
    ) == "Freshness signal is stale: latest proof is aging."
    facts = support._risk_facts(
        ws_id="B-001", risk_rows={"bugs": [{"severity": "P1", "title": "Readback failed"}]},
        risk_summary="",
    )
    assert len(facts) == 1 and facts[0]["kind"] == "bug"
    assert "Readback failed" in facts[0]["text"]
