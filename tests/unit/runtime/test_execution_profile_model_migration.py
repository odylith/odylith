"""Current execution defaults keep distinct roles and historical packet meaning."""
from __future__ import annotations

import pytest

from odylith.runtime.common import agent_runtime_contract as contract
from odylith.runtime.orchestration import subagent_router_context_support as context
from odylith.runtime.orchestration import subagent_router_profile_support as profiles


CURRENT = (
    ("analysis_medium", "gpt-5.6-luna", "medium"),
    ("analysis_high", "gpt-5.6-luna", "high"),
    ("fast_worker", "gpt-5.3-codex-spark", "medium"),
    ("write_medium", "gpt-5.6-terra", "medium"),
    ("write_high", "gpt-5.6-terra", "high"),
    ("frontier_high", "gpt-5.6-sol", "high"),
    ("frontier_xhigh", "gpt-5.6-sol", "xhigh"),
)
LEGACY = (
    ("analysis_medium", "gpt-5.4-mini", "medium"),
    ("analysis_high", "gpt-5.4-mini", "high"),
    ("write_medium", "gpt-5.3-codex", "medium"),
    ("write_high", "gpt-5.3-codex", "high"),
    ("frontier_high", "gpt-5.4", "high"),
    ("frontier_xhigh", "gpt-5.4", "xhigh"),
)


@pytest.mark.parametrize("profile,model,effort", CURRENT)
def test_current_role_tuple_round_trip(profile: str, model: str, effort: str) -> None:
    assert contract.execution_profile_runtime_fields(profile, host_runtime="codex_cli") == (model, effort)
    assert profiles.router_profile_from_runtime(model, effort).value == profile


def test_current_codex_roles_have_unique_runtime_tuples() -> None:
    tuples = [
        contract.execution_profile_runtime_fields(profile, host_runtime="codex_cli")
        for profile in contract.CANONICAL_EXECUTION_PROFILES
    ]
    assert len(tuples) == len(set(tuples)) == 7


@pytest.mark.parametrize("profile,model,effort", LEGACY)
def test_historical_runtime_tuple_keeps_its_role(profile: str, model: str, effort: str) -> None:
    assert profiles.router_profile_from_runtime(model, effort).value == profile


@pytest.mark.parametrize("profile,model,effort", CURRENT + LEGACY)
def test_packet_inference_resolves_role_to_current_default(profile: str, model: str, effort: str) -> None:
    packet = {
        "odylith_execution_model": model,
        "odylith_execution_reasoning_effort": effort,
        "host_runtime": "codex_cli",
    }
    result = context._execution_profile_mapping(
        root={}, context_packet={}, evidence_pack={}, optimization_snapshot={"latest_packet": packet}
    )
    assert result["profile"] == profile
    assert (result["model"], result["reasoning_effort"]) == contract.execution_profile_runtime_fields(
        profile, host_runtime="codex_cli"
    )
    assert packet["odylith_execution_model"] == model


@pytest.mark.parametrize("profile,model,effort", CURRENT)
def test_explicit_profile_wins_over_conflicting_model(profile: str, model: str, effort: str) -> None:
    packet = {
        "odylith_execution_profile": profile,
        "odylith_execution_model": "gpt-5.4",
        "odylith_execution_reasoning_effort": "xhigh",
        "host_runtime": "codex_cli",
    }
    result = context._execution_profile_mapping(
        root={}, context_packet={}, evidence_pack={}, optimization_snapshot={"latest_packet": packet}
    )
    assert result["profile"] == profile
    assert (result["model"], result["reasoning_effort"]) == (model, effort)


@pytest.mark.parametrize(
    "model,effort",
    (
        ("gpt-5.6-luna", "xhigh"),
        ("gpt-5.6-terra", "xhigh"),
        ("gpt-5.6-sol", "medium"),
        ("gpt-5.3-codex-spark", "high"),
        ("unrecognized", "high"),
    ),
)
def test_unassigned_runtime_tuple_is_not_guessed(model: str, effort: str) -> None:
    assert profiles.router_profile_from_runtime(model, effort) is None
