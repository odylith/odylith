from __future__ import annotations

from pathlib import Path

from odylith.runtime.orchestration import odylith_chatter_runtime
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator


def _decision(*, mode: str = "local_only", delegated_leaf_count: int = 0) -> orchestrator.OrchestrationDecision:
    subtasks = [
        orchestrator.SubtaskSlice(
            id=f"slice-{index + 1}",
            prompt="Implement the bounded slice.",
            owned_paths=[f"src/example_{index}.py"],
        )
        for index in range(delegated_leaf_count)
    ]
    return orchestrator.OrchestrationDecision(
        mode=mode,
        decision_id="decision-01",
        delegate=delegated_leaf_count > 0,
        parallel_safety="local_only",
        task_family="bounded_bugfix",
        confidence=3,
        rationale="bounded test decision",
        refusal_stage="",
        manual_review_recommended=False,
        merge_owner="main_thread",
        subtasks=subtasks,
        request={},
    )


def test_closeout_assist_builds_shortest_safe_path_line() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Fix the grounded install slice.",
        candidate_paths=[
            "src/odylith/install/agents.py",
            "src/odylith/install/manager.py",
            "tests/unit/install/test_agents.py",
        ],
        validation_commands=[
            "pytest -q tests/unit/install/test_agents.py",
            "pytest -q tests/integration/install/test_manager.py",
        ],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    assist = odylith_chatter_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is True
    assert assist["style"] == "shortest_safe_path"
    assert assist["markdown_text"] == (
        "**Odylith assist:** kept this on the shortest safe path instead of an "
        "`odylith_off`-style broader repo sweep by grounding the work to 3 candidate paths, "
        "then finishing with 2 focused checks."
    )


def test_closeout_assist_builds_governed_lane_line() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Harden the chatter contract.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        validation_commands=["pytest -q tests/unit/runtime/test_odylith_assist_closeout.py"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    assist = odylith_chatter_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is True
    assert assist["style"] == "governed_lane"
    assert assist["markdown_text"] == (
        "**Odylith assist:** kept this change in the right governed lane instead of a broader "
        "unguided repo hunt by reusing 1 workstream and 1 component, then finishing with 1 focused check."
    )


def test_closeout_assist_builds_grounded_bounded_execution_line() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Finish the runtime chatter pass.",
        candidate_paths=[
            "src/odylith/runtime/orchestration/subagent_orchestrator.py",
            "src/odylith/runtime/orchestration/subagent_router.py",
            "tests/unit/runtime/test_subagent_reasoning_ladder.py",
            "tests/unit/runtime/test_odylith_assist_closeout.py",
        ],
        validation_commands=[
            "pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py",
            "pytest -q tests/unit/runtime/test_odylith_assist_closeout.py",
        ],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    assist = odylith_chatter_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(mode="parallel_batch", delegated_leaf_count=2),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": True,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is True
    assert assist["style"] == "grounded_bounded_execution"
    assert assist["markdown_text"] == (
        "**Odylith assist:** kept the work moving without the usual broader `odylith_off` hunt "
        "by keeping the slice to 4 candidate paths, routing 2 bounded leaves, and finishing "
        "with 2 focused checks."
    )


def test_closeout_assist_suppresses_when_delta_is_not_ready() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Investigate the ambiguous slice.",
        candidate_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        needs_write=False,
        evidence_cone_grounded=True,
    )

    assist = odylith_chatter_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": False,
            "grounded_delegate": False,
            "requires_widening": True,
        },
    )

    assert assist["eligible"] is False
    assert assist["suppressed_reason"] == "requires_widening"
    assert assist["markdown_text"] == ""


def test_orchestrator_threads_closeout_assist_into_odylith_adoption(tmp_path: Path) -> None:
    request = orchestrator.OrchestrationRequest(
        prompt=(
            "Patch src/odylith/install/agents.py and src/odylith/install/manager.py, "
            "then prove the bounded install slice."
        ),
        acceptance_criteria=[
            "Keep src/odylith/install/agents.py, src/odylith/install/manager.py, and "
            "tests/unit/install/test_agents.py aligned with the grounded install behavior."
        ],
        candidate_paths=[
            "src/odylith/install/agents.py",
            "src/odylith/install/manager.py",
            "tests/unit/install/test_agents.py",
        ],
        validation_commands=[
            "pytest -q tests/unit/install/test_agents.py",
            "pytest -q tests/integration/install/test_manager.py",
        ],
        task_kind="implementation",
        phase="implementation",
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "routing_handoff": {
                "grounding": {"grounded": True, "score": 4},
                "routing_confidence": "high",
                "route_ready": True,
                "native_spawn_ready": True,
                "narrowing_required": False,
                "packet_quality": {
                    "evidence_quality": {"score": 4, "level": "high"},
                    "actionability": {"score": 4, "level": "high"},
                    "validation_pressure": {"score": 3, "level": "high"},
                    "context_density": {"score": 3, "level": "high"},
                    "reasoning_readiness": {
                        "score": 3,
                        "level": "high",
                        "mode": "bounded_write",
                        "deep_reasoning_ready": True,
                    },
                    "utility_profile": {
                        "score": 86,
                        "level": "high",
                        "token_efficiency": {"score": 3, "level": "high"},
                    },
                    "native_spawn_ready": True,
                    "reasoning_bias": "accuracy_first",
                    "parallelism_hint": "serial_preferred",
                },
                "odylith_execution_profile": {
                    "profile": "codex_high",
                    "model": "gpt-5.3-codex",
                    "reasoning_effort": "high",
                    "agent_role": "worker",
                    "selection_mode": "bounded_write",
                    "delegate_preference": "delegate",
                    "confidence": {"score": 3, "level": "high"},
                    "constraints": {
                        "route_ready": True,
                        "narrowing_required": False,
                        "spawn_worthiness": 4,
                        "merge_burden": 1,
                    },
                },
            }
        },
    )

    decision = orchestrator.orchestrate_prompt(request, repo_root=tmp_path)

    assist = dict(decision.odylith_adoption["closeout_assist"])
    assert assist["eligible"] is True
    assert assist["markdown_text"].startswith("**Odylith assist:** kept this")
    assert "odylith_off" in assist["markdown_text"]
