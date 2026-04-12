from __future__ import annotations

from odylith.runtime.orchestration import subagent_orchestrator as orchestrator
from odylith.runtime.orchestration import subagent_router as router


def test_surface_prefixes_recognize_odylith_owned_guidance_paths() -> None:
    assert router.surface_prefixes_for_path("odylith/skills/odylith-subagent-router/SKILL.md") == frozenset(
        {"odylith", "skills", "docs"}
    )
    assert router.surface_prefixes_for_path("odylith/runtime/SUBAGENT_OPERATIONS.md") == frozenset(
        {"odylith", "docs"}
    )
    assert router.surface_prefixes_for_path(
        "src/odylith/bundle/assets/odylith/agents-guidelines/GROUNDING_AND_NARROWING.md"
    ) == frozenset({"src", "agents-guidelines", "docs"})


def test_implied_write_surface_validation_accepts_odylith_owned_guidance_paths() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Fix a validation-heavy router slice and refresh the matching skills guidance.",
        acceptance_criteria=[
            "Refresh the operator guidance.",
            "Keep the slice bounded to odylith/skills/odylith-subagent-router/SKILL.md and odylith/runtime/SUBAGENT_OPERATIONS.md.",
        ],
        candidate_paths=[
            "odylith/skills/odylith-subagent-router/SKILL.md",
            "odylith/runtime/SUBAGENT_OPERATIONS.md",
        ],
        task_kind="implementation",
        phase="implementation",
        needs_write=True,
        validation_commands=["odylith subagent-router --repo-root . --help"],
    )

    assert orchestrator._implied_write_surface_errors(request) == []  # noqa: SLF001


def test_implied_write_surface_validation_still_rejects_missing_docs_surface() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Fix the router bug and refresh the matching docs and skills guidance.",
        acceptance_criteria=["Update tests and operator guidance."],
        candidate_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        task_kind="implementation",
        phase="implementation",
        needs_write=True,
        validation_commands=["pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py"],
    )

    errors = orchestrator._implied_write_surface_errors(request)  # noqa: SLF001

    assert "prompt implies writes to docs/skills/agents-guidelines but candidate_paths do not declare that surface" in errors
