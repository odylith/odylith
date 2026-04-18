from odylith.runtime.context_engine import tooling_context_routing as routing


def test_build_narrowing_guidance_prefers_odylith_context_for_anchor_followup() -> None:
    guidance = routing.build_narrowing_guidance(
        packet_kind="bootstrap_session",
        packet_state="gated_broad_scope",
        full_scan_recommended=True,
        full_scan_reason="broad shared scope",
        workstream_selection={},
        retrieval_plan={
            "selected_workstreams": [{"entity_id": "B-032"}],
            "selected_components": [],
            "selected_guidance_chunks": [],
            "miss_recovery": {},
        },
        final_payload={},
    )

    assert guidance["required"] is True
    assert guidance["next_fallback_command"] == "./.odylith/bin/odylith context --repo-root . B-032"
    assert guidance.get("next_fallback_followup", "") == ""


def test_build_narrowing_guidance_prints_scoped_rg_fallback_when_no_anchor_exists() -> None:
    guidance = routing.build_narrowing_guidance(
        packet_kind="bootstrap_session",
        packet_state="gated_broad_scope",
        full_scan_recommended=True,
        full_scan_reason="need narrower code evidence",
        workstream_selection={},
        retrieval_plan={
            "selected_workstreams": [],
            "selected_components": [],
            "selected_guidance_chunks": [],
            "miss_recovery": {},
            "anchor_paths": ["src/odylith/install/manager.py"],
        },
        final_payload={
            "fallback_scan": {
                "query": "launcher",
                "changed_paths": ["src/odylith/install/manager.py"],
            }
        },
    )

    assert guidance["required"] is True
    assert guidance["next_fallback_command"] == "rg -n --context 2 launcher -- src/odylith/install/manager.py"
    assert guidance["next_fallback_followup"] == "sed -n '1,200p' src/odylith/install/manager.py"


def test_build_narrowing_guidance_uses_concrete_repo_grounding_fallback_when_no_anchor_or_query_exists() -> None:
    guidance = routing.build_narrowing_guidance(
        packet_kind="bootstrap_session",
        packet_state="gated_ambiguous",
        full_scan_recommended=False,
        full_scan_reason="",
        workstream_selection={},
        retrieval_plan={
            "selected_workstreams": [],
            "selected_components": [],
            "selected_guidance_chunks": [],
            "miss_recovery": {},
            "anchor_paths": [],
        },
        final_payload={},
    )

    assert guidance["required"] is True
    assert guidance["next_fallback_command"] == r"rg --files | rg 'AGENTS\.md|CLAUDE\.md|odylith/(AGENTS|CLAUDE)\.md|pyproject\.toml'"
    assert guidance["next_fallback_followup"] == "if [ -f AGENTS.md ]; then sed -n '1,200p' AGENTS.md; else sed -n '1,200p' CLAUDE.md; fi"


def test_build_narrowing_guidance_keeps_working_tree_scope_degraded_task_first() -> None:
    guidance = routing.build_narrowing_guidance(
        packet_kind="impact",
        packet_state="gated_broad_scope",
        full_scan_recommended=True,
        full_scan_reason="working_tree_scope_degraded",
        workstream_selection={},
        retrieval_plan={
            "selected_workstreams": [],
            "selected_components": [],
            "selected_guidance_chunks": [],
            "miss_recovery": {},
            "anchor_paths": ["AGENTS.md"],
        },
        final_payload={
            "changed_paths": ["AGENTS.md"],
            "fallback_scan": {
                "query": "tenant boundary",
                "changed_paths": ["AGENTS.md"],
            },
        },
    )

    assert guidance["required"] is True
    assert guidance["reason"] == "Current shared/control-plane context still needs one concrete code, manifest, or contract anchor."
    assert guidance["next_fallback_command"] == ""
    assert guidance["next_fallback_followup"] == ""


def test_build_narrowing_guidance_keeps_broad_shared_paths_task_first() -> None:
    guidance = routing.build_narrowing_guidance(
        packet_kind="impact",
        packet_state="gated_broad_scope",
        full_scan_recommended=True,
        full_scan_reason="broad_shared_paths",
        workstream_selection={},
        retrieval_plan={
            "selected_workstreams": [],
            "selected_components": [],
            "selected_guidance_chunks": [],
            "miss_recovery": {},
            "anchor_paths": ["odylith/AGENTS.md"],
        },
        final_payload={
            "changed_paths": ["odylith/AGENTS.md"],
            "fallback_scan": {
                "query": "tenant boundary",
                "changed_paths": ["odylith/AGENTS.md"],
            },
        },
    )

    assert guidance["required"] is True
    assert guidance["reason"] == "Current shared/control-plane context still needs one concrete code, manifest, or contract anchor."
    assert guidance["next_fallback_command"] == ""
    assert guidance["next_fallback_followup"] == ""


def test_native_spawn_execution_ready_succeeds_for_claude_host_when_all_gates_pass() -> None:
    assert routing.native_spawn_execution_ready(
        route_ready=True,
        full_scan_recommended=False,
        narrowing_required=False,
        within_budget=True,
        delegate_preference="delegate",
        model="claude-opus-4-6",
        reasoning_effort="high",
        agent_role="worker",
        selection_mode="bounded_write",
        selected_test_count=1,
        host_runtime="claude_cli",
    ) is True


def test_native_spawn_execution_ready_avoids_host_probe_when_delegate_gates_fail(monkeypatch) -> None:
    from odylith.runtime.common import host_runtime as host_runtime_contract

    def _unexpected_native_spawn_probe(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("host capability probe should not run before cheap delegate gates")

    monkeypatch.setattr(host_runtime_contract, "native_spawn_supported", _unexpected_native_spawn_probe)

    assert routing.native_spawn_execution_ready(
        route_ready=True,
        full_scan_recommended=False,
        narrowing_required=False,
        within_budget=True,
        delegate_preference="local",
        model="",
        reasoning_effort="",
        agent_role="",
        selection_mode="",
        selected_command_count=1,
        host_runtime="",
    ) is False


def test_build_routing_handoff_avoids_host_probe_when_delegate_gates_fail(monkeypatch) -> None:
    from odylith.runtime.common import host_runtime as host_runtime_contract

    def _unexpected_native_spawn_probe(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("routing handoff should not probe host capabilities for non-delegate packets")

    monkeypatch.setattr(host_runtime_contract, "native_spawn_supported", _unexpected_native_spawn_probe)

    handoff = routing.build_routing_handoff(
        packet_kind="impact",
        packet_state="gated_ambiguous",
        retrieval_plan={"anchor_paths": ["AGENTS.md"], "has_non_shared_anchor": True},
        packet_quality={
            "within_budget": True,
            "routing_confidence": "low",
            "ambiguity_class": "no_candidates",
            "guidance_coverage": "none",
            "intent_profile": {"family": "analysis"},
            "validation_pressure": {"score": 1},
            "actionability": {"score": 1},
            "evidence_quality": {"score": 1},
        },
        final_payload={
            "changed_paths": ["AGENTS.md"],
            "recommended_commands": ["odylith validate guidance-behavior --repo-root ."],
            "narrowing_guidance": {"required": True},
        },
    )

    assert handoff["packet_quality"]["native_spawn_supported"] is False
    assert handoff["packet_quality"]["native_spawn_ready"] is False


def test_native_spawn_execution_ready_fails_closed_for_unknown_host(monkeypatch) -> None:
    from odylith.runtime.common import host_runtime as host_runtime_contract

    monkeypatch.setattr(
        host_runtime_contract,
        "detect_host_runtime",
        lambda *, environ=None: "",
    )

    assert routing.native_spawn_execution_ready(
        route_ready=True,
        full_scan_recommended=False,
        narrowing_required=False,
        within_budget=True,
        delegate_preference="delegate",
        model="gpt-5.3-codex",
        reasoning_effort="high",
        agent_role="worker",
        selection_mode="bounded_write",
        selected_test_count=1,
        host_runtime="",
    ) is False
