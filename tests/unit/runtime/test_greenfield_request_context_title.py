from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_request_context_title import contextual_product_title


def test_contextual_title_preserves_shared_laundry_room_for_generic_utility_request() -> None:
    prompt = (
        "Build a tenant utility for a shared laundry room where residents can see washer status, join a dryer queue, "
        "and report a water leak without calling the property desk."
    )

    assert contextual_product_title(prompt) == "shared laundry room utility"
    assert prompt_intent_source(prompt).title == "shared laundry room utility"


def test_contextual_title_keeps_explicit_command_titles() -> None:
    prompts = {
        "Build a volunteer scheduling tool for a neighborhood library where staff can assign shifts.": (
            "volunteer scheduling tool"
        ),
        "Create a medication inventory system for a neighborhood clinic where nurses can log stock.": (
            "medication inventory system"
        ),
        "Build a field repair workspace for a transit station where technicians can pick jobs.": "field repair workspace",
    }

    for prompt, expected_title in prompts.items():
        assert contextual_product_title(prompt) == ""
        assert prompt_intent_source(prompt).title == expected_title


def test_contextual_title_does_not_discard_domain_nouns_that_resemble_roles() -> None:
    prompts = {
        "Build a weather utility for a mountain station where rangers can see forecasts.": "weather utility",
        "Build a washer utility for a shared laundry room where residents can see machine availability.": "washer utility",
    }

    for prompt, expected_title in prompts.items():
        assert contextual_product_title(prompt) == ""
        assert prompt_intent_source(prompt).title == expected_title
