from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.orchestration import subagent_orchestrator as orchestrator
from odylith.runtime.orchestration import subagent_router as router


def _packet_quality(*, mode: str = "bounded_write") -> dict[str, object]:
    return {
        "evidence_quality": {"score": 4, "level": "high"},
        "actionability": {"score": 4, "level": "high"},
        "context_density": {"score": 3, "level": "high"},
        "reasoning_readiness": {
            "score": 3,
            "level": "high",
            "mode": mode,
            "deep_reasoning_ready": True,
        },
        "evidence_diversity": {"score": 3, "level": "high"},
        "utility_profile": {
            "score": 86,
            "level": "high",
            "token_efficiency": {"score": 3, "level": "high"},
        },
        "native_spawn_ready": True,
    }


def _routing_handoff(
    *,
    profile: str = "",
    model: str = "",
    reasoning_effort: str = "",
    host_runtime: str = "codex_cli",
    selection_mode: str = "bounded_write",
    delegate_preference: str = "delegate",
    confidence_score: int = 4,
    spawn_worthiness: int = 4,
    support_leaf: bool = False,
    source: str = "",
    route_ready: bool = True,
    narrowing_required: bool = False,
    native_spawn_ready: bool = True,
) -> dict[str, object]:
    execution_profile = {
        key: value
        for key, value in {
            "profile": profile,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "host_runtime": host_runtime,
            "selection_mode": selection_mode,
            "delegate_preference": delegate_preference,
            "source": source,
            "confidence": {"score": confidence_score, "level": "high"},
            "constraints": {
                "route_ready": route_ready,
                "narrowing_required": narrowing_required,
                "spawn_worthiness": spawn_worthiness,
                "merge_burden": 1,
            },
        }.items()
        if value not in ("", [], {}, None)
    }
    payload: dict[str, object] = {
        "grounding": {"grounded": True, "score": 4},
        "routing_confidence": "high",
        "route_ready": route_ready,
        "narrowing_required": narrowing_required,
        "packet_quality": {
            **_packet_quality(mode=selection_mode),
            "native_spawn_ready": native_spawn_ready,
        },
        "odylith_execution_profile": execution_profile,
    }
    if support_leaf:
        payload["orchestration"] = {"support_leaf": True}
    return payload


def _route_request(
    *,
    prompt: str,
    task_kind: str,
    needs_write: bool,
    routing_handoff: dict[str, object],
    allowed_paths: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    validation_commands: list[str] | None = None,
    extra_context_signals: dict[str, object] | None = None,
) -> router.RouteRequest:
    return router.route_request_from_mapping(
        {
            "prompt": prompt,
            "task_kind": task_kind,
            "needs_write": needs_write,
            "evidence_cone_grounded": True,
            "allowed_paths": allowed_paths or [],
            "acceptance_criteria": acceptance_criteria or [],
            "validation_commands": validation_commands or [],
            "context_signals": {
                "routing_handoff": routing_handoff,
                **(extra_context_signals or {}),
            },
        }
    )


def _assessment(*, needs_write: bool, task_family: str, context_signal_summary: dict[str, object], **overrides: object) -> router.TaskAssessment:
    payload = {
        "prompt": "Test the reasoning ladder.",
        "task_kind": "implementation" if needs_write else "analysis",
        "task_family": task_family,
        "phase": "implementation" if needs_write else "analysis",
        "needs_write": needs_write,
        "correctness_critical": False,
        "feature_implementation": False,
        "mixed_phase": False,
        "requires_multi_agent_adjudication": False,
        "evolving_context_required": False,
        "evidence_cone_grounded": True,
        "ambiguity": 1,
        "blast_radius": 1,
        "context_breadth": 2,
        "coordination_cost": 1,
        "reversibility_risk": 1,
        "mechanicalness": 0,
        "write_scope_clarity": 3 if needs_write else 0,
        "acceptance_clarity": 2,
        "artifact_specificity": 2,
        "validation_clarity": 2,
        "latency_pressure": 0,
        "requested_depth": 2,
        "accuracy_bias": 2 if needs_write else 1,
        "earned_depth": 2,
        "delegation_readiness": 2,
        "base_confidence": 2,
        "accuracy_preference": "balanced",
        "context_signal_summary": context_signal_summary,
    }
    payload.update(overrides)
    return router.TaskAssessment(**payload)


def _routing_decision(*, profile: router.RouterProfile, task_family: str, needs_write: bool) -> router.RoutingDecision:
    return router.RoutingDecision(
        delegate=True,
        profile=profile.value,
        model=profile.model,
        reasoning_effort=profile.reasoning_effort,
        agent_role="worker" if needs_write else "explorer",
        close_after_result=True,
        idle_timeout_minutes=10,
        reuse_window="explicit_same_scope_followup_queued_only",
        waiting_policy="send_input_or_close",
        why="test route",
        escalation_profile="",
        hard_gate_hits=[],
        task_family=task_family,
    )


def _context_packet_for_synthesis(
    *,
    family: str,
    routing_confidence: str = "high",
    tests: int = 0,
    commands: int = 0,
    guidance: int = 0,
    governance: dict[str, object] | None = None,
    route_ready: bool = True,
    narrowing_required: bool = False,
) -> dict[str, object]:
    return {
        "route": {
            "route_ready": route_ready,
            "narrowing_required": narrowing_required,
            "governance": governance or {},
        },
        "packet_quality": {
            "intent_family": family,
            "routing_confidence": routing_confidence,
        },
        "retrieval_plan": {
            "selected_counts": {
                "tests": tests,
                "commands": commands,
                "guidance": guidance,
            }
        },
    }


def _subtask_execution_profile(
    *,
    request_needs_write: bool = True,
    task_family: str = "bounded_bugfix",
    subtask_scope_role: str = "implementation",
    execution_group_kind: str = "primary",
    subtask_correctness_critical: bool = False,
    intent_profile: dict[str, object] | None = None,
    architecture_audit: dict[str, object] | None = None,
    base_root: dict[str, object] | None = None,
    base_context_packet: dict[str, object] | None = None,
    base_optimization_snapshot: dict[str, object] | None = None,
    route_ready: bool = True,
    narrowing_required: bool = False,
    validation_pressure: int = 2,
    utility_score: int = 60,
    token_efficiency_score: int = 2,
    routing_confidence_score: int = 3,
    spawn_worthiness: int = 3,
    merge_burden: int = 1,
) -> dict[str, object]:
    request = orchestrator.OrchestrationRequest(
        prompt="Exercise the reasoning ladder.",
        acceptance_criteria=["Keep the bounded slice coherent."],
        candidate_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        task_kind="implementation" if request_needs_write else "analysis",
        phase="implementation" if request_needs_write else "analysis",
        needs_write=request_needs_write,
        evidence_cone_grounded=True,
    )
    assessment = _assessment(
        needs_write=request_needs_write,
        task_family=task_family,
        context_signal_summary={},
        correctness_critical=subtask_correctness_critical,
    )
    subtask = orchestrator.SubtaskSlice(
        id="slice-01",
        prompt="Exercise the bounded slice.",
        route_prompt="Exercise the bounded slice.",
        execution_group_kind=execution_group_kind,
        scope_role=subtask_scope_role,
        task_kind=request.task_kind,
        phase=request.phase,
        correctness_critical=subtask_correctness_critical,
        owned_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
    )
    return orchestrator._subtask_odylith_execution_profile(  # noqa: SLF001
        request=request,
        assessment=assessment,
        subtask=subtask,
        intent_profile=intent_profile or {"family": "implementation", "mode": "write_execution"},
        architecture_audit=architecture_audit or {},
        base_root=base_root or {},
        base_context_packet=base_context_packet or {},
        base_optimization_snapshot=base_optimization_snapshot or {},
        route_ready=route_ready,
        narrowing_required=narrowing_required,
        validation_pressure=validation_pressure,
        utility_score=utility_score,
        token_efficiency_score=token_efficiency_score,
        routing_confidence_score=routing_confidence_score,
        spawn_worthiness=spawn_worthiness,
        merge_burden=merge_burden,
    )


def _wrong_runtime_for_profile(profile: router.RouterProfile) -> tuple[str, str]:
    wrong_model = "gpt-5.4-mini" if profile.model != "gpt-5.4-mini" else "gpt-5.4"
    wrong_reasoning = "medium" if profile.reasoning_effort != "medium" else "high"
    return wrong_model, wrong_reasoning


def test_execution_profile_mapping_canonicalizes_explicit_profile_runtime_fields() -> None:
    execution_profile = router._execution_profile_mapping(  # noqa: SLF001
        root={
            "odylith_execution_profile": {
                "profile": router.RouterProfile.GPT54_HIGH.value,
                "model": "gpt-5.4-mini",
                "reasoning_effort": "medium",
            }
        },
        context_packet={},
        evidence_pack={},
        optimization_snapshot={},
    )

    assert execution_profile["profile"] == router.RouterProfile.GPT54_HIGH.value
    assert execution_profile["model"] == router.RouterProfile.GPT54_HIGH.model
    assert execution_profile["reasoning_effort"] == router.RouterProfile.GPT54_HIGH.reasoning_effort


@pytest.mark.parametrize(
    "profile",
    [
        router.RouterProfile.MINI_MEDIUM,
        router.RouterProfile.MINI_HIGH,
        router.RouterProfile.SPARK_MEDIUM,
        router.RouterProfile.CODEX_MEDIUM,
        router.RouterProfile.CODEX_HIGH,
        router.RouterProfile.GPT54_HIGH,
        router.RouterProfile.GPT54_XHIGH,
    ],
)
def test_orchestrator_execution_profile_mapping_infers_profile_from_runtime_fields(
    profile: router.RouterProfile,
) -> None:
    execution_profile = orchestrator._execution_profile_mapping(  # noqa: SLF001
        {
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
        }
    )

    assert execution_profile["profile"] == profile.value
    assert execution_profile["model"] == profile.model
    assert execution_profile["reasoning_effort"] == profile.reasoning_effort


@pytest.mark.parametrize(
    "profile",
    [
        router.RouterProfile.MAIN_THREAD,
        router.RouterProfile.MINI_MEDIUM,
        router.RouterProfile.MINI_HIGH,
        router.RouterProfile.SPARK_MEDIUM,
        router.RouterProfile.CODEX_MEDIUM,
        router.RouterProfile.CODEX_HIGH,
        router.RouterProfile.GPT54_HIGH,
        router.RouterProfile.GPT54_XHIGH,
    ],
)
def test_orchestrator_execution_profile_mapping_canonicalizes_conflicting_runtime_fields(
    profile: router.RouterProfile,
) -> None:
    wrong_model, wrong_reasoning = _wrong_runtime_for_profile(profile)

    execution_profile = orchestrator._execution_profile_mapping(  # noqa: SLF001
        {
            "profile": profile.value,
            "model": wrong_model,
            "reasoning_effort": wrong_reasoning,
        }
    )

    assert execution_profile["profile"] == profile.value
    assert execution_profile["model"] == profile.model
    assert execution_profile["reasoning_effort"] == profile.reasoning_effort


def test_route_request_keeps_recommended_runtime_fields_consistent_with_explicit_profile(tmp_path: Path) -> None:
    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation", "Keep validation green"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.GPT54_HIGH.value,
            model="gpt-5.4-mini",
            reasoning_effort="medium",
            selection_mode="implementation_primary",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)
    summary = decision.assessment["context_signal_summary"]

    assert summary["odylith_execution_profile"] == router.RouterProfile.GPT54_HIGH.value
    assert summary["odylith_execution_model"] == router.RouterProfile.GPT54_HIGH.model
    assert summary["odylith_execution_reasoning_effort"] == router.RouterProfile.GPT54_HIGH.reasoning_effort
    assert decision.odylith_execution_profile["recommended_profile"] == router.RouterProfile.GPT54_HIGH.value
    assert decision.odylith_execution_profile["recommended_model"] == router.RouterProfile.GPT54_HIGH.model
    assert (
        decision.odylith_execution_profile["recommended_reasoning_effort"]
        == router.RouterProfile.GPT54_HIGH.reasoning_effort
    )


def test_synthesized_execution_profile_candidate_requires_route_ready() -> None:
    profile = router._synthesized_execution_profile_candidate(  # noqa: SLF001
        context_packet=_context_packet_for_synthesis(
            family="implementation",
            route_ready=False,
        )
    )

    assert profile == {}


def test_synthesized_execution_profile_candidate_promotes_governed_implementation_to_deep_validation() -> None:
    profile = router._synthesized_execution_profile_candidate(  # noqa: SLF001
        context_packet=_context_packet_for_synthesis(
            family="implementation",
            tests=1,
            commands=1,
            governance={"strict_gate_command_count": 1, "plan_binding_required": True},
        )
    )

    assert profile["profile"] == router.RouterProfile.GPT54_HIGH.value
    assert profile["model"] == router.RouterProfile.GPT54_HIGH.model
    assert profile["reasoning_effort"] == router.RouterProfile.GPT54_HIGH.reasoning_effort
    assert profile["selection_mode"] == "deep_validation"
    assert profile["agent_role"] == "worker"


def test_synthesized_execution_profile_candidate_routes_governance_support_to_spark() -> None:
    profile = router._synthesized_execution_profile_candidate(  # noqa: SLF001
        context_packet=_context_packet_for_synthesis(
            family="governance",
            governance={"closeout_doc_count": 2, "governed_surface_sync_required": True},
        )
    )

    assert profile["profile"] == router.RouterProfile.SPARK_MEDIUM.value
    assert profile["model"] == router.RouterProfile.SPARK_MEDIUM.model
    assert profile["reasoning_effort"] == router.RouterProfile.SPARK_MEDIUM.reasoning_effort
    assert profile["selection_mode"] == "support_fast_lane"


def test_synthesized_execution_profile_candidate_omits_explicit_model_on_claude_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE", "1")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SHELL", raising=False)

    profile = router._synthesized_execution_profile_candidate(  # noqa: SLF001
        context_packet=_context_packet_for_synthesis(
            family="implementation",
            tests=1,
            commands=1,
        )
    )

    assert profile["profile"] == router.RouterProfile.CODEX_HIGH.value
    assert profile["model"] == ""
    assert profile["reasoning_effort"] == router.RouterProfile.CODEX_HIGH.reasoning_effort


def test_route_request_infers_profile_from_model_and_reasoning_only(tmp_path: Path) -> None:
    request = _route_request(
        prompt="Review the bounded analysis slice.",
        task_kind="analysis",
        needs_write=False,
        routing_handoff=_routing_handoff(
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            selection_mode="analysis_synthesis",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)
    summary = decision.assessment["context_signal_summary"]

    assert summary["odylith_execution_profile"] == router.RouterProfile.CODEX_HIGH.value
    assert summary["odylith_execution_model"] == router.RouterProfile.CODEX_HIGH.model
    assert summary["odylith_execution_reasoning_effort"] == router.RouterProfile.CODEX_HIGH.reasoning_effort


def test_execution_profile_mapping_infers_profile_from_optimization_latest_packet_runtime_fields() -> None:
    execution_profile = router._execution_profile_mapping(  # noqa: SLF001
        root={},
        context_packet={},
        evidence_pack={},
        optimization_snapshot={
            "latest_packet": {
                "odylith_execution_model": router.RouterProfile.CODEX_HIGH.model,
                "odylith_execution_reasoning_effort": router.RouterProfile.CODEX_HIGH.reasoning_effort,
            }
        },
    )

    assert execution_profile["profile"] == router.RouterProfile.CODEX_HIGH.value
    assert execution_profile["model"] == router.RouterProfile.CODEX_HIGH.model
    assert execution_profile["reasoning_effort"] == router.RouterProfile.CODEX_HIGH.reasoning_effort


def test_route_request_keeps_local_when_runtime_packet_explicitly_recommends_main_thread(tmp_path: Path) -> None:
    request = _route_request(
        prompt="Review the bounded analysis slice.",
        task_kind="analysis",
        needs_write=False,
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.MAIN_THREAD.value,
            selection_mode="narrow_first",
            delegate_preference="hold_local",
            source="odylith_runtime_packet",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is False
    assert decision.refusal_stage == "odylith_execution_guard"
    assert decision.profile == router.RouterProfile.MAIN_THREAD.value
    assert decision.spawn_agent_overrides == {}
    assert "main thread" in decision.why


def test_route_request_keeps_local_when_runtime_requires_local_narrowing(tmp_path: Path) -> None:
    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            selection_mode="guarded_narrowing",
            delegate_preference="hold_local",
            source="odylith_runtime_packet",
            route_ready=True,
            narrowing_required=True,
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is False
    assert decision.refusal_stage == "odylith_execution_guard"
    assert "local narrowing" in decision.why


def test_route_request_keeps_consumer_odylith_write_fix_local(tmp_path: Path) -> None:
    request = _route_request(
        prompt="Fix the bounded Atlas search issue in odylith/atlas/mermaid-app.v1.js.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["odylith/atlas/mermaid-app.v1.js"],
        acceptance_criteria=["Keep Atlas id search working for short tokens."],
        validation_commands=["odylith dashboard refresh --repo-root . --surfaces atlas"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            selection_mode="bounded_write",
            source="odylith_runtime_packet",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is False
    assert decision.refusal_stage == "assessment_hard_gate"
    assert decision.hard_gate_hits == ["consumer-odylith-diagnosis-and-handoff-only"]
    assert "consumer-odylith-diagnosis-and-handoff-only" in decision.why


def test_route_request_spawn_payloads_never_inherit_parent_defaults(tmp_path: Path) -> None:
    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation", "Keep validation green"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            host_runtime="codex_cli",
            selection_mode="bounded_write",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is True
    assert decision.spawn_overrides["apply_parent_defaults"] is False
    assert decision.spawn_overrides["model"] == decision.model
    assert decision.spawn_overrides["reasoning_effort"] == decision.reasoning_effort
    assert decision.spawn_agent_overrides["model"] == decision.model
    assert decision.spawn_agent_overrides["reasoning_effort"] == decision.reasoning_effort
    assert decision.native_spawn_payload["model"] == decision.model
    assert decision.native_spawn_payload["reasoning_effort"] == decision.reasoning_effort
    assert decision.native_spawn_payload["message"] == decision.spawn_task_message
    assert any("do not inherit the parent thread model or reasoning weight" in line for line in decision.spawn_contract_lines)


def test_route_request_emits_task_tool_payloads_for_claude_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE", "1")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SHELL", raising=False)

    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation", "Keep validation green"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            host_runtime="",
            selection_mode="bounded_write",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is True
    assert decision.spawn_overrides["subagent_type"] == "general-purpose"
    assert decision.spawn_overrides["preferred_project_subagent"] == "odylith-workstream"
    assert decision.spawn_agent_overrides == {}
    assert decision.close_agent_overrides == {}
    assert decision.native_spawn_payload["tool_name"] == "Task"
    assert decision.native_spawn_payload["subagent_type"] == "general-purpose"
    assert decision.native_spawn_payload["preferred_project_subagent"] == "odylith-workstream"
    assert decision.native_spawn_payload["isolation"] == "worktree"
    assert decision.host_tool_contract["host_runtime"] == "claude_cli"
    assert decision.host_tool_contract["native_spawn_supported"] is True
    assert decision.host_tool_contract["delegation_style"] == "task_tool_subagents"
    assert decision.host_tool_contract["tool_name"] == "Task"
    assert any("Claude Code `Task`" in line for line in decision.spawn_contract_lines)


def test_route_request_omits_native_spawn_payloads_for_unknown_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE", raising=False)
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SHELL", raising=False)
    monkeypatch.delenv("__CFBundleIdentifier", raising=False)

    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation", "Keep validation green"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            host_runtime="",
            selection_mode="bounded_write",
        ),
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is True
    assert decision.spawn_overrides == {}
    assert decision.spawn_agent_overrides == {}
    assert decision.close_agent_overrides == {}
    assert decision.native_spawn_payload == {}
    assert decision.host_tool_contract["host_runtime"] == "unknown"
    assert decision.host_tool_contract["native_spawn_supported"] is False
    assert decision.host_tool_contract["local_guidance_only"] is True


def test_route_request_provider_only_codex_hint_does_not_enable_native_spawn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("CLAUDE_CODE", raising=False)
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SHELL", raising=False)
    monkeypatch.delenv("__CFBundleIdentifier", raising=False)

    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation", "Keep validation green"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            host_runtime="",
            selection_mode="bounded_write",
        ),
        extra_context_signals={"provider": "codex"},
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.delegate is True
    assert decision.host_tool_contract["host_runtime"] == "unknown"
    assert decision.host_tool_contract["native_spawn_supported"] is False
    assert decision.spawn_agent_overrides == {}
    assert decision.native_spawn_payload == {}


def test_apply_odylith_execution_priors_rewards_grounded_runtime_backed_depth() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.GPT54_HIGH.value,
            "odylith_execution_confidence_score": 3,
            "odylith_execution_selection_mode": "implementation_primary",
            "odylith_execution_delegate_preference": "delegate",
            "route_ready": True,
            "odylith_execution_route_ready": True,
            "narrowing_required": False,
            "odylith_execution_narrowing_required": False,
            "native_spawn_ready": True,
            "spawn_worthiness_score": 4,
            "odylith_execution_spawn_worthiness": 4,
            "reasoning_readiness_score": 3,
            "context_density_score": 3,
            "evidence_diversity_score": 3,
            "expected_delegation_value_score": 4,
            "earned_depth": 3,
            "delegation_readiness": 3,
            "optimization_within_budget_rate": 0.9,
            "optimization_route_ready_rate": 0.8,
            "optimization_native_spawn_ready_rate": 0.8,
            "optimization_deep_reasoning_ready_rate": 0.8,
            "optimization_runtime_backed_execution_rate": 0.8,
            "optimization_high_execution_confidence_rate": 0.8,
            "optimization_avg_effective_yield_score": 0.82,
            "optimization_high_yield_rate": 0.75,
            "optimization_packet_alignment_rate": 0.8,
            "optimization_reliable_packet_alignment_rate": 0.8,
            "control_advisory_confidence_score": 3,
            "control_advisory_evidence_strength_score": 3,
            "control_advisory_freshness_bucket": "fresh",
            "control_advisory_reasoning_mode": "earn_depth",
            "control_advisory_depth": "promote_when_grounded",
            "control_advisory_delegation": "runtime_backed_delegate",
        },
        earned_depth=3,
        delegation_readiness=3,
    )

    adjusted, lines = router._apply_odylith_execution_priors(  # noqa: SLF001
        scorecard={
            router.RouterProfile.CODEX_HIGH.value: 10.0,
            router.RouterProfile.GPT54_HIGH.value: 9.0,
        },
        assessment=assessment,
        allow_xhigh=False,
    )

    assert adjusted[router.RouterProfile.GPT54_HIGH.value] > 9.0
    assert any("Measured execution guidance adjusted tier scoring" in line for line in lines)
    assert all("runtime-backed" not in line for line in lines)


def test_apply_odylith_execution_alignment_caps_high_tiers_when_packet_alignment_drifts() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.GPT54_HIGH.value,
            "odylith_execution_confidence_score": 3,
            "optimization_packet_alignment_state": "drifting",
        },
    )

    selected, routing_confidence, lines = router._apply_odylith_execution_alignment(  # noqa: SLF001
        selected=router.RouterProfile.GPT54_HIGH,
        assessment=assessment,
        scorecard={
            router.RouterProfile.GPT54_HIGH.value: 11.0,
            router.RouterProfile.CODEX_HIGH.value: 10.0,
            router.RouterProfile.CODEX_MEDIUM.value: 9.0,
        },
        routing_confidence=3,
        allow_xhigh=False,
    )

    assert selected is router.RouterProfile.CODEX_HIGH
    assert routing_confidence <= 3
    assert any("execution fit is still unstable" in line for line in lines)
    assert all("packetizer alignment" not in line for line in lines)


def test_apply_odylith_execution_alignment_caps_high_tiers_when_yield_is_wasteful() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.GPT54_HIGH.value,
            "odylith_execution_confidence_score": 3,
            "optimization_yield_state": "wasteful",
        },
    )

    selected, _, lines = router._apply_odylith_execution_alignment(  # noqa: SLF001
        selected=router.RouterProfile.GPT54_HIGH,
        assessment=assessment,
        scorecard={
            router.RouterProfile.GPT54_HIGH.value: 11.0,
            router.RouterProfile.CODEX_HIGH.value: 10.0,
            router.RouterProfile.MINI_HIGH.value: 9.0,
        },
        routing_confidence=3,
        allow_xhigh=False,
    )

    assert selected is router.RouterProfile.CODEX_HIGH
    assert any("low-yield on comparable slices" in line for line in lines)


def test_apply_odylith_execution_alignment_can_raise_the_routed_tier() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.GPT54_HIGH.value,
            "odylith_execution_confidence_score": 3,
            "odylith_execution_selection_mode": "implementation_primary",
            "odylith_execution_route_ready": True,
            "odylith_execution_narrowing_required": False,
            "odylith_execution_spawn_worthiness": 4,
            "optimization_within_budget_rate": 0.9,
            "optimization_deep_reasoning_ready_rate": 0.8,
            "route_ready": True,
            "narrowing_required": False,
        },
        delegation_readiness=3,
        earned_depth=3,
    )

    selected, routing_confidence, lines = router._apply_odylith_execution_alignment(  # noqa: SLF001
        selected=router.RouterProfile.CODEX_HIGH,
        assessment=assessment,
        scorecard={
            router.RouterProfile.CODEX_HIGH.value: 10.0,
            router.RouterProfile.GPT54_HIGH.value: 9.5,
        },
        routing_confidence=2,
        allow_xhigh=False,
    )

    assert selected is router.RouterProfile.GPT54_HIGH
    assert routing_confidence >= 2
    assert any("raised the routed tier" in line for line in lines)


def test_apply_odylith_execution_alignment_can_lower_support_lane_spend() -> None:
    assessment = _assessment(
        needs_write=False,
        task_family="analysis_review",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.MINI_HIGH.value,
            "odylith_execution_confidence_score": 3,
            "odylith_execution_selection_mode": "support_fast_lane",
            "odylith_execution_spawn_worthiness": 2,
            "support_leaf": True,
        },
        delegation_readiness=1,
    )

    selected, routing_confidence, lines = router._apply_odylith_execution_alignment(  # noqa: SLF001
        selected=router.RouterProfile.GPT54_HIGH,
        assessment=assessment,
        scorecard={
            router.RouterProfile.GPT54_HIGH.value: 11.0,
            router.RouterProfile.MINI_HIGH.value: 10.0,
        },
        routing_confidence=3,
        allow_xhigh=False,
    )

    assert selected is router.RouterProfile.MINI_HIGH
    assert routing_confidence >= 3
    assert any("lowered the routed tier" in line for line in lines)


@pytest.mark.parametrize(
    "profile",
    [
        router.RouterProfile.MINI_MEDIUM,
        router.RouterProfile.MINI_HIGH,
        router.RouterProfile.SPARK_MEDIUM,
        router.RouterProfile.CODEX_MEDIUM,
        router.RouterProfile.CODEX_HIGH,
        router.RouterProfile.GPT54_HIGH,
        router.RouterProfile.GPT54_XHIGH,
    ],
)
def test_lifecycle_and_native_spawn_payloads_match_for_every_profile(profile: router.RouterProfile) -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={"host_runtime": "codex_cli"},
    )

    lifecycle = router._delegated_leaf_lifecycle_payload(profile=profile, assessment=assessment)  # noqa: SLF001
    native_payload = router._native_spawn_payload(  # noqa: SLF001
        profile=profile,
        assessment=assessment,
        message="bounded delegated leaf",
    )

    assert lifecycle.spawn_overrides["apply_parent_defaults"] is False
    assert lifecycle.spawn_overrides["model"] == profile.model
    assert lifecycle.spawn_overrides["reasoning_effort"] == profile.reasoning_effort
    assert lifecycle.spawn_agent_overrides["model"] == profile.model
    assert lifecycle.spawn_agent_overrides["reasoning_effort"] == profile.reasoning_effort
    assert native_payload["model"] == profile.model
    assert native_payload["reasoning_effort"] == profile.reasoning_effort
    assert native_payload["message"] == "bounded delegated leaf"


@pytest.mark.parametrize(
    ("profile", "needs_write", "task_family", "correctness_critical", "feature_implementation", "expected"),
    [
        (router.RouterProfile.MINI_MEDIUM, True, "bounded_bugfix", False, False, router.RouterProfile.CODEX_MEDIUM),
        (router.RouterProfile.MINI_MEDIUM, False, "analysis_review", False, False, router.RouterProfile.MINI_HIGH),
        (router.RouterProfile.MINI_HIGH, False, "analysis_review", False, False, router.RouterProfile.GPT54_HIGH),
        (router.RouterProfile.SPARK_MEDIUM, True, "mechanical_patch", False, False, router.RouterProfile.CODEX_MEDIUM),
        (router.RouterProfile.CODEX_MEDIUM, True, "bounded_bugfix", False, False, router.RouterProfile.CODEX_HIGH),
        (router.RouterProfile.CODEX_MEDIUM, True, "critical_change", True, True, router.RouterProfile.GPT54_HIGH),
        (router.RouterProfile.CODEX_HIGH, True, "bounded_feature", False, True, router.RouterProfile.GPT54_HIGH),
    ],
)
def test_escalation_ladder_uses_expected_next_profiles(
    profile: router.RouterProfile,
    needs_write: bool,
    task_family: str,
    correctness_critical: bool,
    feature_implementation: bool,
    expected: router.RouterProfile,
) -> None:
    assessment = _assessment(
        needs_write=needs_write,
        task_family=task_family,
        context_signal_summary={},
        correctness_critical=correctness_critical,
        feature_implementation=feature_implementation,
        ambiguity=3 if correctness_critical else 1,
        blast_radius=3 if correctness_critical else 1,
        reversibility_risk=3 if correctness_critical else 1,
        requested_depth=3 if correctness_critical else 2,
    )

    next_profile = router._next_profile_for_escalation(  # noqa: SLF001
        _routing_decision(profile=profile, task_family=task_family, needs_write=needs_write),
        assessment,
        router.RouteOutcome(blocked=True),
    )

    assert next_profile is expected


def test_escalation_ladder_can_reach_xhigh_for_gated_critical_work() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="critical_change",
        context_signal_summary={},
        correctness_critical=True,
        feature_implementation=True,
        ambiguity=3,
        blast_radius=3,
        reversibility_risk=3,
        requested_depth=3,
    )

    next_profile = router._next_profile_for_escalation(  # noqa: SLF001
        _routing_decision(
            profile=router.RouterProfile.GPT54_HIGH,
            task_family="critical_change",
            needs_write=True,
        ),
        assessment,
        router.RouteOutcome(blocked=True),
    )

    assert next_profile is router.RouterProfile.GPT54_XHIGH


def test_escalate_routing_decision_emits_coherent_retry_payload() -> None:
    request = _route_request(
        prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        task_kind="implementation",
        needs_write=True,
        allowed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        acceptance_criteria=["Update the implementation", "Keep validation green"],
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
        routing_handoff=_routing_handoff(
            profile=router.RouterProfile.CODEX_HIGH.value,
            model=router.RouterProfile.CODEX_HIGH.model,
            reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
            selection_mode="bounded_write",
        ),
    )
    initial = router.route_request(request, repo_root=Path("."))

    escalated = router.escalate_routing_decision(
        decision=initial,
        outcome=router.RouteOutcome(blocked=True),
        request=request,
    )

    assert escalated is not None
    assert escalated.delegate is True
    assert escalated.profile == router.RouterProfile.GPT54_HIGH.value
    assert escalated.spawn_agent_overrides["model"] == escalated.model
    assert escalated.spawn_agent_overrides["reasoning_effort"] == escalated.reasoning_effort
    assert escalated.native_spawn_payload["model"] == escalated.model
    assert escalated.native_spawn_payload["reasoning_effort"] == escalated.reasoning_effort
    assert escalated.native_spawn_payload["message"] == escalated.spawn_task_message


def test_escalate_routing_decision_refuses_after_xhigh() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="critical_change",
        context_signal_summary={},
        correctness_critical=True,
        feature_implementation=True,
        ambiguity=3,
        blast_radius=3,
        reversibility_risk=3,
        requested_depth=3,
    )
    decision = _routing_decision(
        profile=router.RouterProfile.GPT54_XHIGH,
        task_family="critical_change",
        needs_write=True,
    )
    decision.assessment = assessment.as_dict()

    escalated = router.escalate_routing_decision(
        decision=decision,
        outcome=router.RouteOutcome(blocked=True),
    )

    assert escalated is not None
    assert escalated.delegate is False
    assert escalated.refusal_stage == "escalation_refusal"
    assert "strongest available profile" in escalated.why
    assert escalated.spawn_agent_overrides == {}


def test_subtask_execution_profile_promotes_critical_validation_to_gpt54_high() -> None:
    profile = _subtask_execution_profile(
        subtask_scope_role="validation",
        subtask_correctness_critical=True,
        task_family="critical_change",
        validation_pressure=4,
    )

    assert profile["profile"] == router.RouterProfile.GPT54_HIGH.value
    assert profile["selection_mode"] == "deep_validation"
    assert profile["reasoning_effort"] == router.RouterProfile.GPT54_HIGH.reasoning_effort


def test_subtask_execution_profile_routes_support_docs_to_spark_fast_lane() -> None:
    profile = _subtask_execution_profile(
        subtask_scope_role="docs",
        execution_group_kind="support",
        utility_score=55,
        token_efficiency_score=3,
    )

    assert profile["profile"] == router.RouterProfile.SPARK_MEDIUM.value
    assert profile["selection_mode"] == "support_fast_lane"
    assert profile["reasoning_effort"] == router.RouterProfile.SPARK_MEDIUM.reasoning_effort


@pytest.mark.parametrize(
    "profile",
    [
        router.RouterProfile.CODEX_HIGH,
        router.RouterProfile.GPT54_HIGH,
        router.RouterProfile.GPT54_XHIGH,
    ],
)
def test_subtask_execution_profile_inherits_parent_profile_floor_for_primary_leaves(
    profile: router.RouterProfile,
) -> None:
    routed = _subtask_execution_profile(
        request_needs_write=False,
        subtask_scope_role="analysis",
        base_root={
            "odylith_execution_profile": {
                "model": profile.model,
                "reasoning_effort": profile.reasoning_effort,
            }
        },
    )

    assert routed["profile"] == profile.value
    assert routed["model"] == profile.model
    assert routed["reasoning_effort"] == profile.reasoning_effort


def test_subtask_execution_profile_inherits_parent_profile_from_context_packet() -> None:
    routed = _subtask_execution_profile(
        request_needs_write=False,
        subtask_scope_role="analysis",
        base_context_packet={
            "execution_profile": {
                "profile": router.RouterProfile.GPT54_HIGH.value,
            }
        },
    )

    assert routed["profile"] == router.RouterProfile.GPT54_HIGH.value
    assert routed["model"] == router.RouterProfile.GPT54_HIGH.model
    assert routed["reasoning_effort"] == router.RouterProfile.GPT54_HIGH.reasoning_effort


def test_subtask_execution_profile_inherits_parent_profile_from_optimization_snapshot() -> None:
    routed = _subtask_execution_profile(
        request_needs_write=False,
        subtask_scope_role="analysis",
        base_optimization_snapshot={
            "execution_profile": {
                "profile": router.RouterProfile.CODEX_HIGH.value,
            }
        },
    )

    assert routed["profile"] == router.RouterProfile.CODEX_HIGH.value
    assert routed["model"] == router.RouterProfile.CODEX_HIGH.model
    assert routed["reasoning_effort"] == router.RouterProfile.CODEX_HIGH.reasoning_effort


def test_subtask_execution_profile_keeps_local_narrowing_even_with_strong_parent_profile() -> None:
    routed = _subtask_execution_profile(
        request_needs_write=False,
        subtask_scope_role="analysis",
        route_ready=False,
        narrowing_required=True,
        spawn_worthiness=1,
        base_root={
            "odylith_execution_profile": {
                "profile": router.RouterProfile.GPT54_HIGH.value,
            }
        },
        base_optimization_snapshot={
            "orchestration_posture": {
                "hold_local_rate": 0.9,
                "delegated_lane_rate": 0.1,
            }
        },
    )

    assert routed["profile"] == router.RouterProfile.MAIN_THREAD.value
    assert routed["delegate_preference"] == "hold_local"
    assert routed["selection_mode"] == "narrow_first"


def test_subtask_execution_profile_support_docs_can_stay_fast_lane_under_strong_parent_profile() -> None:
    routed = _subtask_execution_profile(
        subtask_scope_role="docs",
        execution_group_kind="support",
        utility_score=55,
        token_efficiency_score=3,
        base_root={
            "odylith_execution_profile": {
                "profile": router.RouterProfile.GPT54_HIGH.value,
            }
        },
    )

    assert routed["profile"] == router.RouterProfile.SPARK_MEDIUM.value
    assert routed["selection_mode"] == "support_fast_lane"


def test_subtask_execution_profile_applies_history_budget_guard() -> None:
    profile = _subtask_execution_profile(
        subtask_scope_role="implementation",
        utility_score=80,
        base_root={
            "packet_quality": _packet_quality(mode="implementation_primary"),
        },
        base_optimization_snapshot={
            "packet_posture": {"within_budget_rate": 0.2},
            "quality_posture": {
                "avg_context_density_score": 3,
                "avg_reasoning_readiness_score": 3,
                "deep_reasoning_ready_rate": 0.2,
            },
        },
    )

    assert profile["profile"] == router.RouterProfile.CODEX_HIGH.value
    assert profile["selection_mode"] == "history_budget_guard"


def test_subtask_execution_profile_keeps_leaf_local_when_history_prefers_hold_local() -> None:
    profile = _subtask_execution_profile(
        subtask_scope_role="implementation",
        route_ready=False,
        narrowing_required=True,
        spawn_worthiness=1,
        base_optimization_snapshot={
            "orchestration_posture": {
                "hold_local_rate": 0.8,
                "delegated_lane_rate": 0.1,
            }
        },
    )

    assert profile["profile"] == router.RouterProfile.MAIN_THREAD.value
    assert profile["selection_mode"] == "narrow_first"
    assert profile["delegate_preference"] == "hold_local"


def test_subtask_execution_profile_respects_high_risk_architecture_lane() -> None:
    profile = _subtask_execution_profile(
        subtask_scope_role="contract",
        intent_profile={"family": "architecture", "mode": "architecture_grounding"},
        architecture_audit={
            "execution_hint": {"mode": "bounded_analysis", "fanout": "bounded_single_leaf_only", "risk_tier": "high"},
            "coverage": {"confidence_tier": "high"},
        },
    )

    assert profile["profile"] == router.RouterProfile.GPT54_HIGH.value
    assert profile["selection_mode"] == "architecture_grounding"
    assert profile["reasoning_effort"] == router.RouterProfile.GPT54_HIGH.reasoning_effort


def test_orchestrator_leaf_payload_uses_routed_reasoning_without_parent_default_leakage(tmp_path: Path) -> None:
    request = orchestrator.orchestration_request_from_mapping(
        {
            "prompt": "Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Update the implementation", "Keep validation green"],
            "candidate_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
            "task_kind": "implementation",
            "phase": "implementation",
            "needs_write": True,
            "evidence_cone_grounded": True,
            "context_signals": {
                "routing_handoff": _routing_handoff(
                    profile=router.RouterProfile.GPT54_HIGH.value,
                    model="gpt-5.4-mini",
                    reasoning_effort="medium",
                    selection_mode="implementation_primary",
                )
            },
        }
    )
    assessment = router.assess_request(orchestrator._base_route_request(request))  # noqa: SLF001
    subtask = orchestrator.SubtaskSlice(
        id="slice-01",
        prompt="Update the bounded implementation.",
        route_prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        execution_group_kind="primary",
        scope_role="implementation",
        task_kind="implementation",
        phase="implementation",
        accuracy_preference="balanced",
        owned_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        deliverables=["Update the implementation", "Keep validation green"],
        owner="worker",
        goal="Update the bounded implementation",
        expected_output="Bounded patch handoff",
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
    )

    decision = orchestrator._route_leaf(  # noqa: SLF001
        request=request,
        assessment=assessment,
        subtask=subtask,
        all_subtasks=[subtask],
        mode=orchestrator.OrchestrationMode.SINGLE_LEAF,
        repo_root=tmp_path,
    )
    subtask = orchestrator._leaf_to_subtask(subtask, decision)  # noqa: SLF001

    assert subtask.route_spawn_overrides["apply_parent_defaults"] is False
    assert subtask.route_model == subtask.route_spawn_overrides["model"]
    assert subtask.route_model == subtask.route_spawn_agent_overrides["model"]
    assert subtask.route_model == subtask.route_native_spawn_payload["model"]
    assert subtask.route_reasoning_effort == subtask.route_spawn_overrides["reasoning_effort"]
    assert subtask.route_reasoning_effort == subtask.route_spawn_agent_overrides["reasoning_effort"]
    assert subtask.route_reasoning_effort == subtask.route_native_spawn_payload["reasoning_effort"]
    assert subtask.route_native_spawn_payload["message"] == subtask.spawn_task_message
    assert subtask.route_odylith_execution_profile["selected_profile"] == subtask.route_profile
    assert (
        subtask.route_odylith_execution_profile["selected_reasoning_effort"]
        == subtask.route_reasoning_effort
    )


def test_orchestrator_leaf_payload_emits_task_tool_payload_for_claude_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CLAUDE_CODE", "1")
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CODEX_SHELL", raising=False)

    request = orchestrator.orchestration_request_from_mapping(
        {
            "prompt": "Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Update the implementation", "Keep validation green"],
            "candidate_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
            "task_kind": "implementation",
            "phase": "implementation",
            "needs_write": True,
            "evidence_cone_grounded": True,
            "context_signals": {
                "routing_handoff": _routing_handoff(
                    profile=router.RouterProfile.CODEX_HIGH.value,
                    model=router.RouterProfile.CODEX_HIGH.model,
                    reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
                    host_runtime="",
                    selection_mode="bounded_write",
                )
            },
        }
    )
    assessment = router.assess_request(orchestrator._base_route_request(request))  # noqa: SLF001
    subtask = orchestrator.SubtaskSlice(
        id="slice-01",
        prompt="Update the bounded implementation.",
        route_prompt="Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
        execution_group_kind="primary",
        scope_role="implementation",
        task_kind="implementation",
        phase="implementation",
        accuracy_preference="balanced",
        owned_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        deliverables=["Update the implementation", "Keep validation green"],
        owner="worker",
        goal="Update the bounded implementation",
        expected_output="Bounded patch handoff",
        validation_commands=["pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py"],
    )

    decision = orchestrator._route_leaf(  # noqa: SLF001
        request=request,
        assessment=assessment,
        subtask=subtask,
        all_subtasks=[subtask],
        mode=orchestrator.OrchestrationMode.SINGLE_LEAF,
        repo_root=tmp_path,
    )
    subtask = orchestrator._leaf_to_subtask(subtask, decision)  # noqa: SLF001

    assert decision.delegate is True
    assert decision.spawn_agent_overrides == {}
    assert decision.native_spawn_payload["tool_name"] == "Task"
    assert decision.native_spawn_payload["subagent_type"] == "general-purpose"
    assert subtask.route_spawn_agent_overrides == {}
    assert subtask.route_native_spawn_payload["tool_name"] == "Task"
    assert subtask.route_native_spawn_payload["isolation"] == "worktree"


def test_orchestrator_leaf_payload_infers_parent_runtime_from_model_and_reasoning_only(
    tmp_path: Path,
) -> None:
    request = orchestrator.orchestration_request_from_mapping(
        {
            "prompt": "Review the bounded analysis in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Review the bounded analysis", "Keep the slice grounded"],
            "candidate_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "task_kind": "analysis",
            "phase": "analysis",
            "needs_write": False,
            "evidence_cone_grounded": True,
            "context_signals": {
                "routing_handoff": _routing_handoff(
                    model=router.RouterProfile.CODEX_HIGH.model,
                    reasoning_effort=router.RouterProfile.CODEX_HIGH.reasoning_effort,
                    selection_mode="analysis_synthesis",
                )
            },
        }
    )
    assessment = router.assess_request(orchestrator._base_route_request(request))  # noqa: SLF001
    subtask = orchestrator.SubtaskSlice(
        id="slice-01",
        prompt="Review the bounded analysis.",
        route_prompt="Review the bounded analysis in src/odylith/runtime/orchestration/subagent_router.py.",
        execution_group_kind="primary",
        scope_role="analysis",
        task_kind="analysis",
        phase="analysis",
        accuracy_preference="balanced",
        owned_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        deliverables=["Review the bounded analysis", "Keep the slice grounded"],
        owner="explorer",
        goal="Review the bounded analysis",
        expected_output="Bounded analysis handoff",
    )

    decision = orchestrator._route_leaf(  # noqa: SLF001
        request=request,
        assessment=assessment,
        subtask=subtask,
        all_subtasks=[subtask],
        mode=orchestrator.OrchestrationMode.SINGLE_LEAF,
        repo_root=tmp_path,
    )

    assert decision.odylith_execution_profile["recommended_profile"] == router.RouterProfile.CODEX_HIGH.value
    assert decision.odylith_execution_profile["recommended_model"] == router.RouterProfile.CODEX_HIGH.model
    assert (
        decision.odylith_execution_profile["recommended_reasoning_effort"]
        == router.RouterProfile.CODEX_HIGH.reasoning_effort
    )
    assert decision.reasoning_effort in {"high", "xhigh"}


def test_orchestrator_leaf_payload_canonicalizes_conflicting_parent_runtime_fields_before_routing(
    tmp_path: Path,
) -> None:
    request = orchestrator.orchestration_request_from_mapping(
        {
            "prompt": "Review the bounded analysis in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Review the bounded analysis"],
            "candidate_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "task_kind": "analysis",
            "phase": "analysis",
            "needs_write": False,
            "evidence_cone_grounded": True,
            "context_signals": {
                "routing_handoff": _routing_handoff(
                    profile=router.RouterProfile.GPT54_HIGH.value,
                    model="gpt-5.4-mini",
                    reasoning_effort="medium",
                    selection_mode="analysis_synthesis",
                )
            },
        }
    )
    assessment = router.assess_request(orchestrator._base_route_request(request))  # noqa: SLF001
    subtask = orchestrator.SubtaskSlice(
        id="slice-01",
        prompt="Review the bounded analysis.",
        route_prompt="Review the bounded analysis in src/odylith/runtime/orchestration/subagent_router.py.",
        execution_group_kind="primary",
        scope_role="analysis",
        task_kind="analysis",
        phase="analysis",
        accuracy_preference="balanced",
        owned_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        deliverables=["Review the bounded analysis"],
        owner="explorer",
        goal="Review the bounded analysis",
        expected_output="Bounded analysis handoff",
    )

    decision = orchestrator._route_leaf(  # noqa: SLF001
        request=request,
        assessment=assessment,
        subtask=subtask,
        all_subtasks=[subtask],
        mode=orchestrator.OrchestrationMode.SINGLE_LEAF,
        repo_root=tmp_path,
    )

    assert decision.odylith_execution_profile["recommended_profile"] == router.RouterProfile.GPT54_HIGH.value
    assert decision.odylith_execution_profile["recommended_model"] == router.RouterProfile.GPT54_HIGH.model
    assert (
        decision.odylith_execution_profile["recommended_reasoning_effort"]
        == router.RouterProfile.GPT54_HIGH.reasoning_effort
    )


def test_router_runtime_guard_reason_stays_task_first() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.MAIN_THREAD.value,
            "odylith_execution_source": "odylith_runtime_packet",
            "odylith_execution_confidence_score": 3,
            "odylith_execution_delegate_preference": "hold_local",
            "odylith_execution_selection_mode": "narrow_first",
            "route_ready": False,
            "odylith_execution_route_ready": False,
            "native_spawn_ready": False,
            "narrowing_required": True,
            "odylith_execution_narrowing_required": True,
        },
    )

    reason = router._odylith_execution_guard_reason(assessment)  # noqa: SLF001

    assert "Odylith" not in reason
    assert "odylith runtime" not in reason
    assert "runtime handoff" not in reason
    assert "local narrowing" in reason or "main thread" in reason


def test_orchestrator_local_narrowing_notes_stay_task_first() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Review the bounded guidance slice.",
        candidate_paths=["AGENTS.md"],
        needs_write=False,
        evidence_cone_grounded=True,
    )
    assessment = _assessment(
        needs_write=False,
        task_family="analysis_review",
        context_signal_summary={
            "route_ready": False,
            "odylith_execution_route_ready": False,
            "native_spawn_ready": False,
            "odylith_execution_delegate_preference": "hold_local",
            "odylith_execution_selection_mode": "narrow_first",
            "narrowing_required": True,
            "odylith_execution_narrowing_required": True,
        },
        task_kind="analysis",
        phase="analysis",
        requested_depth=1,
        delegation_readiness=0,
        base_confidence=1,
    )

    reasons, notes = orchestrator._should_keep_local(request, assessment)  # noqa: SLF001

    assert "odylith-local-narrowing" in reasons
    assert "odylith-read-only-local-narrowing" in reasons
    assert all("Odylith" not in note for note in notes)
    assert all("runtime handoff" not in note for note in notes)
    assert all("retained context packet" not in note for note in notes)
    assert any("narrowing" in note for note in notes)


def test_assessment_extracts_execution_governance_fields_from_context_packet() -> None:
    request = router.route_request_from_mapping(
        {
            "prompt": "Verify the active rollout before widening anything.",
            "task_kind": "analysis",
            "needs_write": False,
            "evidence_cone_grounded": True,
            "context_signals": {
                "context_packet": {
                    "route": {"route_ready": True},
                    "packet_quality": {"i": "analysis", "native_spawn_ready": True},
                    "execution_governance": {
                        "present": True,
                        "outcome": "defer",
                        "requires_reanchor": True,
                        "mode": "verify",
                        "next_move": "verify.selected_matrix",
                        "current_phase": "status_synthesis",
                        "last_successful_phase": "submit",
                        "blocker": "waiting for rollout evidence",
                        "closure": "incomplete",
                        "wait_status": "building",
                        "wait_detail": "deploying cell-01",
                        "resume_token": "resume:B-072",
                        "validation_archetype": "deploy",
                        "validation_minimum_pass_count": 6,
                        "contradiction_count": 1,
                        "history_rule_count": 2,
                        "authoritative_lane": "context_engine.governance_slice.authoritative",
                        "host_family": "codex",
                        "model_family": "codex",
                    },
                }
            },
        }
    )

    assessment = router.assess_request(request)
    summary = assessment.context_signal_summary

    assert summary["execution_governance_present"] is True
    assert summary["execution_governance_outcome"] == "defer"
    assert summary["execution_governance_requires_reanchor"] is True
    assert summary["execution_governance_mode"] == "verify"
    assert summary["execution_governance_next_move"] == "verify.selected_matrix"
    assert summary["execution_governance_closure"] == "incomplete"
    assert summary["execution_governance_wait_status"] == "building"
    assert summary["execution_governance_validation_archetype"] == "deploy"
    assert summary["execution_governance_contradiction_count"] == 1
    assert summary["execution_governance_history_rule_count"] == 2
    assert summary["execution_governance_host_family"] == "codex"


def test_router_execution_governance_reanchor_blocks_delegation() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "execution_governance_present": True,
            "execution_governance_requires_reanchor": True,
            "execution_governance_mode": "recover",
            "execution_governance_next_move": "recover.current_blocker",
            "execution_governance_host_family": "codex",
            "execution_governance_host_supports_native_spawn": True,
        },
    )

    reason = router._odylith_execution_guard_reason(assessment)  # noqa: SLF001

    assert "re-anchor" in reason
    assert "Odylith" not in reason
    assert "runtime handoff" not in reason


def test_orchestrator_parallel_fanout_stays_serial_while_waiting_on_verify_frontier() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Verify the active rollout before widening execution.",
        candidate_paths=["src/odylith/runtime/a.py", "src/odylith/runtime/b.py"],
        needs_write=True,
        evidence_cone_grounded=True,
    )
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        delegation_readiness=4,
        earned_depth=4,
        context_signal_summary={
            "route_ready": True,
            "odylith_execution_route_ready": True,
            "native_spawn_ready": True,
            "parallelism_hint": "bounded_parallel_candidate",
            "parallelism_score": 4,
            "spawn_worthiness_score": 4,
            "odylith_execution_confidence_score": 4,
            "execution_governance_present": True,
            "execution_governance_mode": "verify",
            "execution_governance_next_move": "resume.external_dependency",
            "execution_governance_wait_status": "building",
            "execution_governance_wait_detail": "deploying cell-01",
            "execution_governance_host_family": "codex",
            "execution_governance_host_supports_native_spawn": True,
        },
    )

    mode, notes = orchestrator._adaptive_batch_mode(  # noqa: SLF001
        request,
        assessment,
        safety=orchestrator.ParallelSafetyClass.DISJOINT_WRITE_SAFE,
        groups=[["src/odylith/runtime/a.py"], ["src/odylith/runtime/b.py"]],
        tuning=orchestrator.TuningState(),
    )

    assert mode == orchestrator.OrchestrationMode.SERIAL_BATCH
    assert any("resume the active external dependency" in note for note in notes)


def test_orchestrator_keeps_claude_host_local_when_worker_delegation_is_unavailable() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Implement the bounded runtime fix.",
        candidate_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        needs_write=True,
        evidence_cone_grounded=True,
    )
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "route_ready": True,
            "odylith_execution_route_ready": True,
            "native_spawn_ready": False,
            "execution_governance_present": True,
            "execution_governance_outcome": "admit",
            "execution_governance_mode": "implement",
            "execution_governance_host_family": "claude",
            "execution_governance_host_supports_native_spawn": False,
        },
    )

    reasons, notes = orchestrator._should_keep_local(request, assessment)  # noqa: SLF001

    assert "execution-governance-host-serial" in reasons
    assert any("Claude Code" in note for note in notes)


def test_orchestrator_keeps_consumer_odylith_fix_local_with_handoff_note(tmp_path: Path) -> None:
    request = orchestrator.orchestration_request_from_mapping(
        {
            "prompt": "Fix the Atlas search issue in odylith/atlas/mermaid-app.v1.js.",
            "candidate_paths": ["odylith/atlas/mermaid-app.v1.js"],
            "acceptance_criteria": ["Keep short diagram-id token search working."],
            "validation_commands": ["odylith dashboard refresh --repo-root . --surfaces atlas"],
            "task_kind": "implementation",
            "phase": "implementation",
            "needs_write": True,
            "evidence_cone_grounded": True,
        }
    )

    decision = orchestrator.orchestrate_prompt(request, repo_root=tmp_path)

    assert decision.mode == orchestrator.OrchestrationMode.LOCAL_ONLY.value
    assert decision.delegate is False
    assert any("diagnosis-and-handoff only" in note for note in decision.execution_contract_notes)


def test_top_score_lines_scrub_internal_runtime_chatter() -> None:
    assessment = _assessment(
        needs_write=True,
        task_family="bounded_bugfix",
        context_signal_summary={
            "odylith_execution_profile": router.RouterProfile.CODEX_HIGH.value,
            "odylith_execution_selection_mode": "bounded_write",
        },
    )
    assessment.feature_reasons = {
        "grounding": [
            "Control advisories currently prefer precision-first packets over spending depth on shallow evidence cones",
            "runtime handoff carried an implementation-first intent profile for this bounded write slice",
        ]
    }

    lines = router._top_score_lines(  # noqa: SLF001
        selected=router.RouterProfile.CODEX_HIGH,
        scorecard={
            router.RouterProfile.CODEX_HIGH.value: 10.0,
            router.RouterProfile.CODEX_MEDIUM.value: 8.5,
        },
        assessment=assessment,
        task_class_policy_lines=["bounded coding work keeps the leaf on a coding tier"],
        allow_xhigh=False,
        routing_confidence=3,
        score_margin=1.5,
        backstop_lines=[],
    )

    flattened = " ".join(lines)
    assert "Control advisories" not in flattened
    assert "runtime handoff" not in flattened
    assert "odylith_execution=" not in flattened
    assert "odylith_mode=" not in flattened
    assert "Recent execution evidence" in flattened
    assert "current slice" in flattened
