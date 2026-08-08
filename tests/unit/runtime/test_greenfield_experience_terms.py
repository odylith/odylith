from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_experience import (
    _trim_preview_terminal_fragment,
    build_next_steps,
)


def test_experience_preview_trims_incomplete_subordinate_tail() -> None:
    assert _trim_preview_terminal_fragment(  # noqa: SLF001
        "Give clear correction guidance when required information"
    ) == "Give clear correction guidance"
    assert _trim_preview_terminal_fragment(  # noqa: SLF001
        "Give clear correction guidance when required information is missing"
    ) == "Give clear correction guidance when required information is missing"


def test_implementation_handoff_preserves_explicit_first_release_requirements() -> None:
    next_steps = build_next_steps(
        proposal={
            "intent": {
                "title": "Release Notes Workspace",
                "first_path": "Extension publishers assemble release notes and see a reviewable release brief.",
            },
            "apply_semantic_input": {
                "first_path": "Extension publishers assemble release notes and see a reviewable release brief.",
            },
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": (
                        "Release succeeds when the release brief is reviewable. The first release includes one "
                        "workspace per extension, a review queue, and an exportable release brief."
                    )
                }
            },
            "backlog": [
                {"title": "Prove One Complete Release Notes Path"},
                {"title": "Let Extension Publishers Assemble Release Notes", "recommended_first_slice": "Assemble one release brief."},
            ],
            "project_brief": {"coding_readiness_gates": ["The first implementation lane is ready."]},
        },
        backlog_result={
            "created": [
                {"idea_id": "B-001", "title": "Prove One Complete Release Notes Path"},
                {"idea_id": "B-002", "title": "Let Extension Publishers Assemble Release Notes"},
            ]
        },
        first_release_workstreams=["B-001", "B-002"],
        release_selector="0.0.1",
    )

    prompt = next_steps["implementation_prompt"].casefold()

    assert "first_wave" not in next_steps
    assert "program" not in " ".join(next_steps["operator_sequence"]).casefold()
    assert "wave" not in " ".join(next_steps["operator_sequence"]).casefold()
    assert "one workspace per extension, a review queue, and an exportable release brief" in prompt
    assert "marketplace publishing" not in prompt
    assert "telemetry" not in prompt
    assert "code scanning" not in prompt
