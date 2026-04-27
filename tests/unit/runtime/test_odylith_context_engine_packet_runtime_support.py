from __future__ import annotations

from odylith.runtime.context_engine import odylith_context_engine_packet_runtime_support as support


def test_payload_workstream_hint_prefers_packet_fields_before_selection_payloads() -> None:
    payload = {
        "workstream": "b-123",
        "context_packet": {
            "selection_state": "i:B-999",
            "selection": {"workstream_ids": ["B-777"]},
        },
        "workstream_selection": {
            "selected_workstream": {"entity_id": "B-555"},
        },
    }

    assert support.payload_workstream_hint(payload) == "B-123"


def test_payload_workstream_hint_falls_back_to_compact_selection_state() -> None:
    payload = {
        "context_packet": {
            "selection_state": "x:B-321",
            "selection": {"workstream_ids": ["B-777"]},
        }
    }

    assert support.payload_workstream_hint(payload) == "B-321"


def test_selected_count_codec_round_trips_compact_payloads() -> None:
    counts = {"commands": 3, "docs": 1, "tests": 0, "guidance": 2}

    encoded = support.encode_compact_selected_counts(counts)

    assert encoded == "c3d1g2"
    assert support.decode_compact_selected_counts(encoded) == {
        "commands": 3,
        "docs": 1,
        "guidance": 2,
    }


def test_repo_scan_degraded_reason_prefers_explicit_packet_reason() -> None:
    packet = {
        "repo_scan_degraded_reason": "working_tree_scope_degraded",
        "full_scan_reason": "runtime_unavailable",
        "route": {"full_scan_reason": "path_scope_missing"},
    }

    assert support.repo_scan_degraded_reason(packet) == "working_tree_scope_degraded"
