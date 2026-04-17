from __future__ import annotations

from odylith.runtime.context_engine import execution_engine_handshake


def test_execution_engine_snapshot_helper_fail_closes_historical_identity_before_reuse() -> None:
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={
            "component": "execution-" + "governance",
            "execution_engine": {
                "present": True,
                "outcome": "admit",
                "mode": "verify",
                "next_move": "verify.selected_matrix",
            },
        },
        context_packet={
            "route": {"route_ready": True, "native_spawn_ready": True},
        },
    )

    assert compact["outcome"] == "deny"
    assert compact["requires_reanchor"] is True
    assert compact["mode"] == "recover"
    assert compact["next_move"] == "re_anchor.execution_engine_identity"
    assert compact["snapshot_reuse_status"] == "fail_closed_identity"
    assert compact["identity_status"] == "blocked_noncanonical_target"
    assert compact["target_component_status"] == "blocked_noncanonical_execution_engine"


def test_execution_engine_snapshot_helper_fail_closes_nested_stale_snapshot_identity() -> None:
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={
            "packet_kind": "governance_slice",
            "execution_engine": {
                "present": True,
                "outcome": "admit",
                "mode": "verify",
                "next_move": "verify.selected_matrix",
                "target_component_id": "execution-" + "governance",
            },
        },
        context_packet={
            "route": {"route_ready": True, "native_spawn_ready": True},
        },
    )

    assert compact["outcome"] == "deny"
    assert compact["requires_reanchor"] is True
    assert compact["mode"] == "recover"
    assert compact["target_component_id"] == "execution-" + "governance"
    assert compact["snapshot_reuse_status"] == "fail_closed_identity"
    assert compact["identity_status"] == "blocked_noncanonical_target"
    assert compact["target_component_status"] == "blocked_noncanonical_execution_engine"
