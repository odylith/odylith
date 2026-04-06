from __future__ import annotations

from odylith.runtime.governance import execution_wave_view_model


def test_build_execution_wave_view_payload_builds_program_and_workstream_context() -> None:
    payload = execution_wave_view_model.build_execution_wave_view_payload(
        {
            "workstreams": [
                {"idea_id": "B-021", "title": "Control Grid", "status": "implementation"},
                {"idea_id": "B-022", "title": "Wave One", "status": "implementation"},
                {"idea_id": "B-023", "title": "Wave Two", "status": "implementation"},
                {"idea_id": "B-031", "title": "Docs", "status": "planning"},
            ],
            "execution_programs": [
                {
                    "umbrella_id": "B-021",
                    "version": "v1",
                    "source_file": "odylith/radar/source/programs/B-021.execution-waves.v1.json",
                    "waves": [
                        {
                            "wave_id": "W1",
                            "label": "Wave 1",
                            "status": "active",
                            "summary": "First wave.",
                            "depends_on": [],
                            "primary_workstreams": ["B-022"],
                            "carried_workstreams": [],
                            "in_band_workstreams": ["B-031"],
                            "gate_refs": [
                                {
                                    "workstream_id": "B-022",
                                    "plan_path": "odylith/technical-plans/in-progress/2026-03-01-wave-one.md",
                                    "label": "Wave one gate.",
                                }
                            ],
                        },
                        {
                            "wave_id": "W2",
                            "label": "Wave 2",
                            "status": "planned",
                            "summary": "Second wave.",
                            "depends_on": ["W1"],
                            "primary_workstreams": ["B-023"],
                            "carried_workstreams": [],
                            "in_band_workstreams": ["B-031"],
                            "gate_refs": [],
                        },
                    ],
                }
            ],
        }
    )

    assert payload["summary"] == {
        "program_count": 1,
        "wave_count": 2,
        "active_wave_count": 1,
        "blocked_wave_count": 0,
        "workstream_count": 3,
    }

    program = payload["programs"][0]
    assert program["umbrella_id"] == "B-021"
    assert program["umbrella_title"] == "Control Grid"
    assert program["active_wave_count"] == 1
    assert program["completion_label"] == ""
    assert program["current_wave"]["wave_id"] == "W1"
    assert program["next_wave"]["wave_id"] == "W2"
    assert program["waves"][0]["is_current_wave"] is True
    assert program["waves"][0]["is_active_tail_wave"] is False
    assert program["waves"][0]["primary_workstreams"][0]["title"] == "Wave One"
    assert program["waves"][0]["gate_refs"][0]["title"] == "Wave One"
    assert program["waves"][0]["depends_on_summary"] == "Starts here"
    assert program["waves"][0]["compact_summary_line"] == "1 of 2 · Starts here · 1 primary · 1 in band · 1 gate"
    assert program["waves"][0]["gate_preview_labels"] == ["Wave one gate."]
    assert program["waves"][0]["default_open"] is True
    assert program["waves"][1]["default_open"] is False
    assert program["waves"][1]["depends_on_labels"] == ["Wave 1"]

    wave_two_context = payload["workstreams"]["B-023"][0]
    assert wave_two_context["umbrella_id"] == "B-021"
    assert wave_two_context["wave_span_label"] == "W2"
    assert wave_two_context["role_label"] == "Primary"
    assert wave_two_context["has_next_wave"] is True
    assert wave_two_context["program_next_label"] == "Wave 2"


def test_build_execution_wave_view_payload_preserves_cross_wave_role_context() -> None:
    payload = execution_wave_view_model.build_execution_wave_view_payload(
        {
            "workstreams": [
                {"idea_id": "B-021", "title": "Control Grid", "status": "implementation"},
                {"idea_id": "B-031", "title": "Docs", "status": "planning"},
            ],
            "execution_programs": [
                {
                    "umbrella_id": "B-021",
                    "version": "v1",
                    "source_file": "odylith/radar/source/programs/B-021.execution-waves.v1.json",
                    "waves": [
                        {
                            "wave_id": "W1",
                            "label": "Wave 1",
                            "status": "active",
                            "summary": "First wave.",
                            "depends_on": [],
                            "primary_workstreams": [],
                            "carried_workstreams": [],
                            "in_band_workstreams": ["B-031"],
                            "gate_refs": [],
                        },
                        {
                            "wave_id": "W2",
                            "label": "Wave 2",
                            "status": "planned",
                            "summary": "Second wave.",
                            "depends_on": ["W1"],
                            "primary_workstreams": ["B-031"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                    ],
                }
            ],
        }
    )

    context = payload["workstreams"]["B-031"][0]
    assert context["wave_span_label"] == "W1-W2"
    assert context["role_label"] == "In Band -> Primary"
    assert context["has_active_wave"] is True
    assert context["program_active_labels"] == ["Wave 1"]
    assert [row["role"] for row in context["refs"]] == ["in_band", "primary"]
    assert payload["programs"][0]["waves"][0]["default_open"] is True
    assert payload["programs"][0]["waves"][1]["default_open"] is False


def test_build_execution_wave_view_payload_spotlights_highest_sequence_active_wave() -> None:
    payload = execution_wave_view_model.build_execution_wave_view_payload(
        {
            "workstreams": [
                {"idea_id": "B-021", "title": "Control Grid", "status": "implementation"},
                {"idea_id": "B-022", "title": "Wave One", "status": "implementation"},
                {"idea_id": "B-023", "title": "Wave Two", "status": "implementation"},
            ],
            "execution_programs": [
                {
                    "umbrella_id": "B-021",
                    "version": "v1",
                    "source_file": "odylith/radar/source/programs/B-021.execution-waves.v1.json",
                    "waves": [
                        {
                            "wave_id": "W1",
                            "label": "Wave 1",
                            "status": "active",
                            "summary": "First wave.",
                            "depends_on": [],
                            "primary_workstreams": ["B-022"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                        {
                            "wave_id": "W2",
                            "label": "Wave 2",
                            "status": "active",
                            "summary": "Second wave.",
                            "depends_on": ["W1"],
                            "primary_workstreams": ["B-023"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                        {
                            "wave_id": "W3",
                            "label": "Wave 3",
                            "status": "planned",
                            "summary": "Third wave.",
                            "depends_on": ["W2"],
                            "primary_workstreams": [],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                    ],
                }
            ],
        }
    )

    program = payload["programs"][0]
    assert program["current_wave"]["wave_id"] == "W2"
    assert program["waves"][0]["is_current_wave"] is False
    assert program["waves"][0]["is_active_tail_wave"] is True
    assert program["waves"][1]["is_current_wave"] is True
    assert program["waves"][1]["is_active_tail_wave"] is False
    assert program["waves"][0]["default_open"] is False
    assert program["waves"][1]["default_open"] is True


def test_build_execution_wave_view_payload_handles_fully_closed_program() -> None:
    payload = execution_wave_view_model.build_execution_wave_view_payload(
        {
            "workstreams": [
                {"idea_id": "B-151", "title": "Skill Coverage", "status": "finished"},
                {"idea_id": "B-152", "title": "Wave One", "status": "finished"},
                {"idea_id": "B-176", "title": "Historical Replay Tracking", "status": "parked"},
            ],
            "execution_programs": [
                {
                    "umbrella_id": "B-151",
                    "version": "v1",
                    "source_file": "odylith/radar/source/programs/B-151.execution-waves.v1.json",
                    "waves": [
                        {
                            "wave_id": "W1",
                            "label": "Wave 1",
                            "status": "complete",
                            "summary": "Completed baseline wave.",
                            "depends_on": [],
                            "primary_workstreams": ["B-152"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                        {
                            "wave_id": "W6",
                            "label": "Wave 6",
                            "status": "complete",
                            "summary": "Historical tracking completed as a parked terminal lane.",
                            "depends_on": ["W1"],
                            "primary_workstreams": ["B-176"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                    ],
                }
            ],
        }
    )

    program = payload["programs"][0]
    assert program["active_wave_count"] == 0
    assert program["blocked_wave_count"] == 0
    assert program["complete_wave_count"] == 2
    assert program["completion_label"] == "All waves complete"
    assert program["current_wave"] is None
    assert program["next_wave"] is None
    assert program["waves"][0]["default_open"] is True
    assert program["waves"][1]["default_open"] is False


def test_build_execution_wave_view_payload_formats_partial_completion_label() -> None:
    payload = execution_wave_view_model.build_execution_wave_view_payload(
        {
            "workstreams": [
                {"idea_id": "B-021", "title": "Control Grid", "status": "implementation"},
                {"idea_id": "B-022", "title": "Wave One", "status": "finished"},
                {"idea_id": "B-023", "title": "Wave Two", "status": "implementation"},
            ],
            "execution_programs": [
                {
                    "umbrella_id": "B-021",
                    "version": "v1",
                    "source_file": "odylith/radar/source/programs/B-021.execution-waves.v1.json",
                    "waves": [
                        {
                            "wave_id": "W1",
                            "label": "Wave 1",
                            "status": "complete",
                            "summary": "Completed baseline wave.",
                            "depends_on": [],
                            "primary_workstreams": ["B-022"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                        {
                            "wave_id": "W2",
                            "label": "Wave 2",
                            "status": "active",
                            "summary": "Active follow-on wave.",
                            "depends_on": ["W1"],
                            "primary_workstreams": ["B-023"],
                            "carried_workstreams": [],
                            "in_band_workstreams": [],
                            "gate_refs": [],
                        },
                    ],
                }
            ],
        }
    )

    program = payload["programs"][0]
    assert program["complete_wave_count"] == 1
    assert program["completion_label"] == "Wave 1 complete"
