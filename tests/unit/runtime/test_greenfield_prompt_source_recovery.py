from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import confirmation_from_operator_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_project_title_source


def test_prompt_source_strips_greenfield_project_for_wrapper_without_losing_real_project_titles() -> None:
    assert (
        prompt_project_title_source(
            "Create a greenfield project for a wildfire evacuation resource allocator that tracks shelter capacity."
        )
        == "wildfire evacuation resource allocator"
    )
    assert (
        prompt_project_title_source("Create a project management dashboard where leads assign tasks.")
        == "project management dashboard"
    )


def test_recovered_confirmation_from_greenfield_project_wrapper_validates_internal_systems() -> None:
    prompts = (
        (
            "Create a greenfield project for a wildfire evacuation resource allocator that tracks shelter capacity, "
            "road closures, household needs, responder assignments, scenario assumptions, and supervisor decisions "
            "during one simulated evacuation wave."
        ),
        (
            "Create a greenfield project for a robotics fleet incident-replay console that correlates robot telemetry, "
            "operator commands, safety envelopes, obstacle detections, replay timelines, and engineering review "
            "outcomes before a fix is approved."
        ),
    )

    for prompt in prompts:
        confirmation = confirmation_from_operator_intent(prompt, prefer_product_title=True)
        first_line = confirmation.splitlines()[0]
        intent = parse_confirmed_intent_text(confirmation, prompt=prompt)

        assert "Project For" not in first_line
        assert len(intent["internal_systems"]) >= 2
        assert all("Project for" not in row for row in intent["internal_systems"])
