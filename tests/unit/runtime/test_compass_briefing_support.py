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
