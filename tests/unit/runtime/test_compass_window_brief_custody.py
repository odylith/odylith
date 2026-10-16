"""Window assembly must not give prior prose a new narration identity."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator
from odylith.runtime.surfaces import compass_window_summary_support as windows


ORIGIN = "2026-09-07T12:00:00Z"
REFRESH = "2026-09-08T05:50:08Z"
SECTIONS = [{"key": "current_execution", "bullets": [{"text": "Original reviewed narrative."}]}]


def _context(tmp_path: Path) -> SimpleNamespace:
    rows = [{"idea_id": "B-001", "title": "Cache custody", "status": "implementation"}]
    return SimpleNamespace(
        repo_root=tmp_path, plan_index_path=tmp_path / "plans.md",
        now=dt.datetime(2026, 9, 8, 5, 50, tzinfo=dt.timezone.utc),
        all_ws_payloads=rows, ws_payloads=rows, active_ws_rows=rows,
        ws_index={row["idea_id"]: row for row in rows},
        events=[], timeline_transactions=[], next_actions=[], bug_items=[],
        traceability_risks=[], traceability_critical=[], stale_diagrams=[],
        self_host={}, self_host_risks=[], generated_utc=REFRESH,
        reasoning_config=None, delivery_workstreams={}, progress_callback=None,
        build_window_activity=lambda *_args, **_kwargs: [],
        filter_transactions_by_window=lambda *_args, **_kwargs: [],
        collect_recent_completed_plan_rows=lambda *_args, **_kwargs: [],
        build_window_event_counts=lambda _events: {},
        build_risk_posture_summary=lambda **_kwargs: "No recorded risks.",
        scope_risk_rows=lambda **_kwargs: {"bugs": [], "traceability": [], "stale_diagrams": []},
        build_global_standup_fact_packet=lambda **_kwargs: {"scope": "global", "winner": "current"},
        build_scoped_standup_fact_packet=lambda **_kwargs: {"scope": "B-001", "winner": "current"},
        brief_with_known_failure_state=lambda **kwargs: kwargs["brief"],
        inactive_scoped_standup_brief=lambda **_kwargs: {"status": "unavailable", "reason": "inactive"},
        verified_scoped_window_ids=lambda **_kwargs: {"B-001"},
        window_row_has_workstream=lambda **_kwargs: False,
        row_is_verified_scoped_signal=lambda _row: False,
        row_is_governance_only_local_change=lambda _row: False,
        window_row_workstreams=lambda _row: [],
        is_generated_only_local_change_event=lambda _row: False,
        is_generated_only_transaction=lambda _row: False,
        is_bug_date_within_window=lambda **_kwargs: False,
        scoped_verified_max_fanout=3, window_events_by_hours={},
        window_transactions_by_hours={}, recent_completed_rows_by_hours={},
        # Retained legacy snapshot input deliberately remains present after the
        # obsolete production fields are removed; it must gain no authority.
        prior_runtime_state={},
        reusable_brief_sections_for_fact_packet=lambda **_kwargs: copy.deepcopy(SECTIONS),
    )


@pytest.mark.parametrize("hours", [24, 48])
@pytest.mark.parametrize("exact_hit", [True, False], ids=["exact-hit", "changed-winner-miss"])
def test_window_uses_exact_owner_despite_matching_legacy_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hours: int, exact_hit: bool,
) -> None:
    context = _context(tmp_path)
    calls = []
    expected = {
        "status": "ready" if exact_hit else "unavailable",
        "source": "cache" if exact_hit else "unavailable",
        "fingerprint": "exact-current-substrate", "generated_utc": ORIGIN,
        "sections": copy.deepcopy(SECTIONS) if exact_hit else [],
    }

    def exact_owner(**kwargs):
        calls.append(kwargs)
        assert kwargs["allow_provider"] is False
        assert kwargs["prefer_provider"] is False
        assert kwargs["provider"] is None
        return copy.deepcopy(expected)

    monkeypatch.setattr(narrator, "build_standup_brief", exact_owner)
    first = windows.summarize_window(context=context, hours=hours)
    key = f"{hours}h"
    old = {"status": "ready", "source": "provider", "generated_utc": ORIGIN,
           "fingerprint": "older-substrate", "sections": copy.deepcopy(SECTIONS)}
    context.prior_runtime_state = {
        "runtime": {key: first.runtime_window}, "global": {key: old},
        "scoped": {key: {"B-001": old}},
    }
    if not exact_hit:
        context.build_global_standup_fact_packet = lambda **_kwargs: {"scope": "global", "winner": "changed"}
        context.build_scoped_standup_fact_packet = lambda **_kwargs: {"scope": "B-001", "winner": "changed"}
    calls.clear()
    for _ in range(2):
        result = windows.summarize_window(context=context, hours=hours)
        assert result.global_brief == expected
        assert result.scoped_briefs["B-001"] == expected
    assert [call["fact_packet"]["scope"] for call in calls] == ["global", "B-001"] * 2


def test_window_preserves_inactive_scope_and_known_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    context.verified_scoped_window_ids = lambda **_kwargs: set()
    failure = {"status": "unavailable", "source": "unavailable", "diagnostics": {"reason": "timeout"}}
    calls = []

    def exact_owner(**kwargs):
        calls.append(kwargs)
        assert kwargs["allow_provider"] is False
        return {"status": "unavailable", "source": "unavailable"}

    context.brief_with_known_failure_state = lambda **_kwargs: copy.deepcopy(failure)
    monkeypatch.setattr(narrator, "build_standup_brief", exact_owner)
    result = windows.summarize_window(context=context, hours=24)
    assert result.global_brief == failure
    assert result.scoped_briefs["B-001"] == {"status": "unavailable", "reason": "inactive"}
    assert len(calls) == 1
