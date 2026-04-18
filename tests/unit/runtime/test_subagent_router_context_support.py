from __future__ import annotations

from odylith.runtime.orchestration import subagent_router_context_support as support


def test_mapping_value_accepts_router_alias_tokens() -> None:
    payload = {"rc": "high", "ic": "medium", "cp": True}

    assert support._mapping_value(payload, "routing_confidence") == "high"  # noqa: SLF001
    assert support._mapping_value(payload, "intent_confidence") == "medium"  # noqa: SLF001
    assert support._mapping_value(payload, "intent_critical_path") is True  # noqa: SLF001


def test_validation_bundle_from_context_falls_back_to_embedded_governance_signal() -> None:
    context_packet = {
        "route": {
            "governance": {
                "recommended_command_count": 2,
                "strict_gate_command_count": 1,
                "plan_binding_required": True,
                "governed_surface_sync_required": False,
            }
        }
    }

    bundle = support._validation_bundle_from_context({}, context_packet=context_packet)  # noqa: SLF001

    assert bundle == {
        "recommended_command_count": 2,
        "strict_gate_command_count": 1,
        "plan_binding_required": True,
    }


def test_governance_obligations_and_surface_refs_fall_back_to_embedded_signal() -> None:
    context_packet = {
        "route": {
            "governance": {
                "touched_workstream_count": 2,
                "primary_workstream_id": "B-099",
                "surface_count": 3,
                "reason_group_count": 2,
            }
        }
    }

    obligations = support._governance_obligations_from_context({}, context_packet=context_packet)  # noqa: SLF001
    surface_refs = support._surface_refs_from_context({}, context_packet=context_packet)  # noqa: SLF001

    assert obligations == {
        "touched_workstream_count": 2,
        "primary_workstream_id": "B-099",
    }
    assert surface_refs == {
        "surface_count": 3,
        "reason_group_count": 2,
    }


def test_normalized_rate_and_latency_pressure_handle_scaled_inputs() -> None:
    assert support._normalized_rate(True) == 1.0  # noqa: SLF001
    assert support._normalized_rate(75) == 0.75  # noqa: SLF001
    assert support._latency_pressure_signal(900) == 0  # noqa: SLF001
    assert support._latency_pressure_signal(2500) == 2  # noqa: SLF001
    assert support._latency_pressure_signal(12000) == 4  # noqa: SLF001
