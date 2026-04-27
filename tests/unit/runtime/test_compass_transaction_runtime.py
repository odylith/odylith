from __future__ import annotations

import datetime as dt

from odylith.runtime.surfaces import compass_transaction_runtime


def _event(
    *,
    event_id: str,
    ts_iso: str,
    kind: str,
    summary: str,
    workstreams: list[str],
) -> dict[str, object]:
    ts = dt.datetime.fromisoformat(ts_iso)
    return {
        "id": event_id,
        "kind": kind,
        "summary": summary,
        "context": "",
        "ts": ts,
        "ts_iso": ts_iso,
        "author": "local",
        "files": ["src/odylith/runtime/surfaces/compass_transaction_runtime.py"],
        "workstreams": list(workstreams),
        "source": "local",
        "session_id": "",
        "transaction_id": "",
        "transaction_seq": 0,
        "transaction_boundary": "",
        "headline_hint": "",
    }


def test_build_prompt_transactions_infers_checkpoint_workstream_into_transaction_workstreams() -> None:
    events = [
        _event(
            event_id="evt-1",
            ts_iso="2026-04-09T18:48:00-07:00",
            kind="implementation",
            summary=(
                "Captured B-071 checkpoint: completed Compass quiet-scope failures "
                "were not just Compass bugs; they exposed a broader product problem."
            ),
            workstreams=["B-001", "B-003", "B-004", "B-025", "B-027"],
        )
    ]

    payloads = compass_transaction_runtime._build_prompt_transactions(events=events)

    assert len(payloads) == 1
    assert set(payloads[0]["workstreams"]) == {"B-001", "B-003", "B-004", "B-025", "B-027", "B-071"}
    assert payloads[0]["workstreams"][0] == "B-071"


def test_build_prompt_transactions_enriches_nested_event_workstreams_from_checkpoint_text() -> None:
    events = [
        _event(
            event_id="evt-1",
            ts_iso="2026-04-09T18:48:00-07:00",
            kind="implementation",
            summary=(
                "Captured B-071 checkpoint: completed Compass quiet-scope failures "
                "were not just Compass bugs; they exposed a broader product problem."
            ),
            workstreams=["B-001", "B-003", "B-004", "B-025", "B-027"],
        )
    ]

    payloads = compass_transaction_runtime._build_prompt_transactions(events=events)

    assert len(payloads) == 1
    nested_events = payloads[0]["events"]
    assert len(nested_events) == 1
    assert set(nested_events[0]["workstreams"]) == {"B-001", "B-003", "B-004", "B-025", "B-027", "B-071"}
    assert nested_events[0]["workstreams"][0] == "B-071"
