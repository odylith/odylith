from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import (
    structured_prompt_facts,
)


def test_parenthetical_example_does_not_become_a_named_human_actor() -> None:
    prompt = (
        "A signal source connects and pushes a stream of samples; the pipeline ingests them, applies a configured "
        "transform (for example a filter or FFT window), evaluates a detection rule, and emits a result event to a sink."
    )

    facts = structured_prompt_facts(prompt)

    assert facts.actor == ""
    assert facts.first_path == ""


def test_for_role_person_syntax_still_identifies_the_named_actor() -> None:
    facts = structured_prompt_facts(
        "Create a review console for quality lead Mina. Mina reviews a sample and sees a signed report."
    )

    assert facts.actor == "Mina, a quality lead"
