from __future__ import annotations

from odylith.runtime.orchestration import subagent_router_execution_engine_runtime as runtime


def test_router_execution_engine_fields_prefer_summary_then_context_fallbacks() -> None:
    fields = runtime.router_execution_engine_fields(
        context_signals={
            "execution_engine_outcome": "recover",
            "latest_execution_engine_wait_status": "blocked",
            "latest_execution_engine_target_component_ids": ["alpha", "beta", "gamma", "delta", "epsilon"],
            "latest_execution_engine_pressure_signals": ["merge risk", "latency pressure", "merge risk"],
        },
        root={
            "execution_engine_present": True,
            "execution_engine_target_lane": "serial",
            "execution_engine_has_writable_targets": True,
        },
        execution_engine_summary={
            "execution_engine_present": False,
            "execution_engine_outcome": "admit",
            "execution_engine_mode": "implement",
            "execution_engine_validation_minimum_pass_count": "3",
            "execution_engine_target_lane": "parallel",
        },
    )

    assert fields["execution_engine_present"] is False
    assert fields["execution_engine_outcome"] == "admit"
    assert fields["execution_engine_mode"] == "implement"
    assert fields["execution_engine_validation_minimum_pass_count"] == 3
    assert fields["execution_engine_target_lane"] == "parallel"
    assert fields["execution_engine_wait_status"] == "blocked"
    assert fields["execution_engine_has_writable_targets"] is True
    assert fields["execution_engine_target_component_ids"] == ["alpha", "beta", "gamma", "delta"]
    assert fields["execution_engine_pressure_signals"] == ["merge risk", "latency pressure"]


def test_router_execution_engine_fields_normalize_invalid_scalars_to_safe_defaults() -> None:
    fields = runtime.router_execution_engine_fields(
        context_signals={
            "latest_execution_engine_present": "",
            "latest_execution_engine_requires_reanchor": "no",
            "latest_execution_engine_validation_minimum_pass_count": "bad",
            "latest_execution_engine_history_rule_hits": "  one-hit  ",
        },
        root={},
        execution_engine_summary={},
    )

    assert fields["execution_engine_present"] is False
    assert fields["execution_engine_requires_reanchor"] is False
    assert fields["execution_engine_validation_minimum_pass_count"] == 0
    assert fields["execution_engine_history_rule_hits"] == ["one-hit"]
