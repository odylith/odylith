from __future__ import annotations

from pathlib import Path

from odylith.runtime.intervention_engine import stream_state


class _OddObject:
    def __str__(self) -> str:
        return "odd-object"


def test_intervention_event_metadata_is_json_safe_and_cache_invalidates(tmp_path: Path) -> None:
    first = stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="First visible signal.",
        session_id="stream-meta",
        host_family="codex",
        display_markdown="**Odylith Insight:** First visible signal.",
        metadata={
            "set_payload": {"alpha", "beta"},
            "object_payload": _OddObject(),
            "nested": {"ok": True},
        },
    )
    rows_after_first = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="stream-meta",
    )
    second = stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Second visible signal.",
        session_id="stream-meta",
        host_family="codex",
        display_markdown="**Odylith Insight:** Second visible signal.",
        metadata={"sequence": 2},
    )
    rows_after_second = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="stream-meta",
    )

    assert first["metadata"]["object_payload"] == "odd-object"
    assert isinstance(first["metadata"]["set_payload"], str)
    assert first["metadata"]["nested"] == {"ok": True}
    assert second["metadata"] == {"sequence": 2}
    assert [row["summary"] for row in rows_after_first] == ["First visible signal."]
    assert [row["summary"] for row in rows_after_second] == [
        "First visible signal.",
        "Second visible signal.",
    ]


def test_intervention_event_rejects_unknown_kind_before_writing(tmp_path: Path) -> None:
    try:
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="debug_noise",
            summary="Should not write.",
        )
    except ValueError as exc:
        assert "unsupported intervention event kind" in str(exc)
    else:
        raise AssertionError("unsupported intervention event kind was accepted")

    assert stream_state.load_recent_intervention_events(repo_root=tmp_path) == []
