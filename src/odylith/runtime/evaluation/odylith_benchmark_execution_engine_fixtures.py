"""Fixture helpers for execution-engine benchmark packet truth."""

from __future__ import annotations

from typing import Any, Mapping


def _token(value: Any) -> str:
    return str(value or "").strip()


def _first_expected_value(expect: Mapping[str, Any], field_name: str, default: str = "") -> str:
    value = expect.get(field_name)
    if isinstance(value, list):
        for token in value:
            normalized = _token(token)
            if normalized:
                return normalized
        return default
    return _token(value) or default


def _expectation_has_execution_engine_fields(expect: Mapping[str, Any]) -> bool:
    return any(str(key).startswith("execution_engine_") for key in expect)


def _scenario_fixture_expectations(scenario: Mapping[str, Any]) -> tuple[Mapping[str, Any], dict[str, Any]]:
    fixture = scenario.get("packet_fixture", {})
    if not isinstance(fixture, Mapping) or not fixture:
        return {}, {}
    expect = dict(scenario.get("expect", {})) if isinstance(scenario.get("expect"), Mapping) else {}
    if not _expectation_has_execution_engine_fields(expect):
        return {}, {}
    return fixture, expect


def host_family_from_fixture(scenario: Mapping[str, Any], expect: Mapping[str, Any]) -> str:
    fixture = scenario.get("packet_fixture", {})
    host_candidates = (
        fixture.get("host_candidates", [])
        if isinstance(fixture, Mapping) and isinstance(fixture.get("host_candidates"), list)
        else []
    )
    for candidate in host_candidates:
        token = _token(candidate).lower()
        if "claude" in token:
            return "claude"
        if "codex" in token:
            return "codex"
    return _first_expected_value(expect, "execution_engine_host_family")


def execution_snapshot_from_fixture(
    *,
    scenario: Mapping[str, Any],
    target_component: str,
    expected_target_status: str,
    canonical_component_id: str,
) -> dict[str, Any]:
    fixture, expect = _scenario_fixture_expectations(scenario)
    if not fixture or not expect:
        return {}
    proof_state = {}
    if isinstance(fixture.get("proof_state"), Mapping):
        proof_state = dict(fixture["proof_state"])
    phase = _token(proof_state.get("frontier_phase")) or "verify"
    mode = _first_expected_value(expect, "execution_engine_mode", phase)
    return {
        "present": bool(expect.get("execution_engine_present", True)),
        "objective": f"execute benchmark fixture for {target_component}",
        "authoritative_lane": _first_expected_value(
            expect,
            "execution_engine_authoritative_lane",
            "context_engine.governance_slice.authoritative",
        ),
        "outcome": _first_expected_value(expect, "execution_engine_outcome", "admit"),
        "requires_reanchor": bool(expect.get("execution_engine_requires_reanchor", False)),
        "mode": mode,
        "next_move": _first_expected_value(
            expect,
            "execution_engine_next_move",
            f"{mode}.selected_matrix",
        ),
        "current_phase": _first_expected_value(expect, "execution_engine_current_phase", mode),
        "last_successful_phase": mode,
        "closure": _first_expected_value(expect, "execution_engine_closure", "incomplete"),
        "resume_token": _first_expected_value(
            expect,
            "execution_engine_resume_token",
            "resume:governance_slice",
        ),
        "validation_archetype": _first_expected_value(
            expect,
            "execution_engine_validation_archetype",
            mode,
        ),
        "host_family": host_family_from_fixture(scenario, expect),
        "component_id": canonical_component_id,
        "canonical_component_id": canonical_component_id,
        "identity_status": "canonical",
        "target_component_id": target_component,
        "target_component_ids": [target_component],
        "target_component_status": expected_target_status,
        "snapshot_reuse_status": "built",
        "runtime_built_from": "benchmark_fixture",
    }


def summary_fields_from_fixture(scenario: Mapping[str, Any]) -> dict[str, Any]:
    _fixture, expect = _scenario_fixture_expectations(scenario)
    if not expect:
        return {}
    summary: dict[str, Any] = {}
    for field_name in (
        "packet_kind",
        "selection_state",
        "packet_state",
        "workstream",
        "execution_engine_outcome",
        "execution_engine_mode",
        "execution_engine_next_move",
        "execution_engine_current_phase",
        "execution_engine_last_successful_phase",
        "execution_engine_closure",
        "execution_engine_wait_status",
        "execution_engine_resume_token",
        "execution_engine_validation_archetype",
        "execution_engine_authoritative_lane",
        "execution_engine_target_lane",
        "execution_engine_host_family",
        "execution_engine_model_family",
        "execution_engine_component_id",
        "execution_engine_canonical_component_id",
        "execution_engine_identity_status",
        "execution_engine_target_component_status",
        "execution_engine_snapshot_reuse_status",
    ):
        value = _first_expected_value(expect, field_name)
        if value:
            summary[field_name] = value
    for field_name in (
        "within_budget",
        "route_ready",
        "native_spawn_ready",
        "narrowing_required",
        "execution_engine_present",
        "execution_engine_requires_reanchor",
    ):
        if field_name in expect:
            summary[field_name] = bool(expect.get(field_name))
    return summary
