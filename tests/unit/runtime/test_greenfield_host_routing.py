from __future__ import annotations

from odylith.runtime.intervention_engine import prompt_signal_runtime
from odylith.runtime.surfaces import host_intervention_support


def test_greenfield_prompt_routes_without_live_observation_bundle() -> None:
    prompt = "Create a backlog for building an ecommerce site. Create all the component registry and atlas diagrams for it."

    assert prompt_signal_runtime.is_greenfield_governance_prompt(prompt)
    assert not prompt_signal_runtime.has_prompt_intervention_signal(prompt)
    assert not host_intervention_support.prompt_needs_live_bundle(prompt=prompt)
    assert not host_intervention_support.prompt_first_receipt_eligible(prompt)
