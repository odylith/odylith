from __future__ import annotations

from odylith.runtime.surfaces import compass_current_workstreams_runtime


def _row(
    *,
    idea_id: str,
    status: str,
    current_release: bool = False,
    active_release: bool = False,
    active_wave: bool = False,
) -> dict[str, object]:
    aliases = ["current"] if current_release else []
    return {
        "idea_id": idea_id,
        "status": status,
        "execution_wave_programs": [{"has_active_wave": active_wave}] if active_wave else [],
        "release": {
            "status": "active" if active_release or current_release else "planning",
            "aliases": aliases,
        },
        "scope_signal": {},
    }


def test_select_current_workstream_rows_keeps_active_release_and_wave_members_visible() -> None:
    implementation_only = [
        _row(idea_id=f"B-{100 + index:03d}", status="implementation")
        for index in range(11)
    ]
    active_rows = [
        _row(idea_id="B-072", status="implementation", current_release=True, active_release=True, active_wave=True),
        _row(idea_id="B-073", status="queued", current_release=True, active_release=True, active_wave=True),
        _row(idea_id="B-079", status="queued", current_release=True, active_release=True, active_wave=True),
    ]

    selected = compass_current_workstreams_runtime.select_current_workstream_rows(
        all_rows=[*implementation_only, *active_rows],
        window_events_48h=[],
        recent_completed_rows_48h=[],
    )

    selected_ids = [str(row.get("idea_id", "")).strip() for row in selected]

    assert "B-072" in selected_ids
    assert "B-073" in selected_ids
    assert "B-079" in selected_ids
    assert len(selected_ids) == 14
    assert selected_ids[:3] == ["B-072", "B-073", "B-079"]
