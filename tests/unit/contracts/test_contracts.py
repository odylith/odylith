from odylith.contracts import AgentHostAdapter, AgentPlanStep, AgentPlanV1, AgentRouteV1


def test_agent_host_adapter_payload_round_trip_shape() -> None:
    adapter = AgentHostAdapter(
        adapter_id="desktop",
        host_family="codex",
        model_family="codex",
        delegation_style="routed_spawn",
        supports_native_spawn=True,
        supports_interrupt=True,
        supports_artifact_paths=True,
        supports_local_structured_reasoning=True,
        supports_explicit_model_selection=True,
    )
    payload = adapter.to_payload()
    assert payload["adapter_id"] == "desktop"
    assert payload["supports_native_spawn"] is True
    assert payload["model_family"] == "codex"
    assert payload["delegation_style"] == "routed_spawn"
    assert payload["supports_local_structured_reasoning"] is True


def test_agent_route_v1_payload_includes_schema() -> None:
    route = AgentRouteV1(
        route_id="route-1",
        execution_mode="parallel",
        ownership=["surface-a", "surface-b"],
        validation_commands=["pytest -q"],
        closeout_surfaces=["docs/spec.md"],
        reasons_to_stay_local=["shared write ownership"],
    )
    payload = route.to_payload()
    assert payload["schema"] == "agent_route.v1"
    assert payload["ownership"] == ["surface-a", "surface-b"]


def test_agent_plan_v1_payload_includes_steps() -> None:
    plan = AgentPlanV1(
        plan_id="plan-1",
        route_id="route-1",
        delegation_recommendation="delegate",
        steps=[
            AgentPlanStep(
                step_id="step-1",
                summary="Update the installed guidance",
                owner="worker-a",
                stop_condition="Guidance tree materialized",
            )
        ],
    )
    payload = plan.to_payload()
    assert payload["schema"] == "agent_plan.v1"
    assert payload["steps"][0]["owner"] == "worker-a"
