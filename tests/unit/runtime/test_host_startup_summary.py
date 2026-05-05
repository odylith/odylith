from __future__ import annotations

import json

from odylith.runtime.surfaces import host_startup_summary


def test_startup_output_needs_narrowing_for_legacy_fallback_packet() -> None:
    output = """
odylith start
- lane: fallback
{
  "context_packet": {
    "packet_state": "gated_ambiguous"
  }
}
"""

    assert host_startup_summary.startup_output_needs_narrowing(output) is True


def test_startup_output_does_not_treat_advisory_reason_as_narrowing() -> None:
    output = (
        "odylith start\n"
        "- lane: bootstrap\n"
        + json.dumps(
            {
                "packet_kind": "bootstrap_session",
                "narrowing_guidance": {"reason": "Need one code path."},
                "context_packet": {
                    "packet_state": "compact",
                    "route": {"route_ready": True},
                },
            }
        )
    )

    assert host_startup_summary.startup_output_needs_narrowing(output) is False


def test_startup_output_needs_narrowing_when_required_flag_is_set() -> None:
    output = json.dumps(
        {
            "packet_kind": "bootstrap_session",
            "narrowing_guidance": {
                "required": True,
                "reason": "Need one code path.",
            },
        }
    )

    assert host_startup_summary.startup_output_needs_narrowing(output) is True
