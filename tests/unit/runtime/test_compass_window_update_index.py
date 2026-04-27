from __future__ import annotations

import datetime as dt

from odylith.runtime.surfaces import compass_dashboard_runtime as runtime
from odylith.runtime.surfaces import compass_window_update_index


def test_build_execution_update_index_matches_existing_global_and_scoped_helpers() -> None:
    window_events = [
        {
            "kind": "implementation",
            "summary": "Pinned the shell-safe refresh path to the cheap local runtime flow.",
            "workstreams": ["B-025"],
            "files": ["src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py"],
            "source": "codex",
            "ts": dt.datetime(2026, 4, 9, 9, 0, 0, tzinfo=dt.timezone.utc),
        },
        {
            "kind": "decision",
            "summary": "Kept provider-backed narration as the explicit full-refresh path only.",
            "workstreams": ["B-025", "B-063"],
            "files": ["odylith/technical-plans/in-progress/example.md"],
            "source": "codex",
            "ts": dt.datetime(2026, 4, 9, 8, 30, 0, tzinfo=dt.timezone.utc),
        },
    ]

    index = compass_window_update_index.build_execution_update_index(window_events, max_items=3)

    assert index["global"] == runtime._collect_window_execution_updates(window_events, max_items=3)  # noqa: SLF001
    assert index["by_workstream"]["B-025"] == runtime._collect_window_execution_updates(  # noqa: SLF001
        window_events,
        ws_id="B-025",
        max_items=3,
    )


def test_build_transaction_update_index_matches_existing_global_and_scoped_helpers() -> None:
    window_transactions = [
        {
            "id": "txn-1",
            "transaction_id": "txn-1",
            "context": "Stopped the shell-safe path from paying provider cost for every active scope.",
            "headline": "",
            "workstreams": ["B-025"],
            "files": [
                "src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py",
                "src/odylith/runtime/surfaces/compass_standup_brief_batch.py",
            ],
            "event_count": 3,
            "end_ts_iso": "2026-04-09T09:10:00Z",
            "events": [
                {
                    "kind": "implementation",
                    "summary": "Stopped shell-safe from paying provider cost for every active scope.",
                    "source": "codex",
                }
            ],
        },
        {
            "id": "txn-2",
            "transaction_id": "txn-2",
            "context": "Wired the shared window-update index into the timeline and standup hot path.",
            "headline": "",
            "workstreams": ["B-025", "B-063"],
            "files": [
                "src/odylith/runtime/surfaces/compass_window_update_index.py",
            ],
            "event_count": 2,
            "end_ts_iso": "2026-04-09T09:12:00Z",
            "events": [
                {
                    "kind": "implementation",
                    "summary": "Wired the shared window-update index into the timeline and standup hot path.",
                    "source": "codex",
                }
            ],
        },
    ]

    index = compass_window_update_index.build_transaction_update_index(window_transactions, max_items=3)

    assert index["global"] == runtime._collect_window_transaction_updates(window_transactions, max_items=3)  # noqa: SLF001
    assert index["by_workstream"]["B-025"] == runtime._collect_window_transaction_updates(  # noqa: SLF001
        window_transactions,
        ws_id="B-025",
        max_items=3,
    )
