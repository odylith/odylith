from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import derived_title
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import title_needs_repair
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import recovered_title
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import intent_title


def test_generic_container_title_repairs_from_canonical_state_object() -> None:
    intent = {
        "title": "Admin Console",
        "state_object": "The primary state object is an arrhythmia episode record.",
        "product_story": "Clinicians need a reviewable arrhythmia episode decision.",
        "first_path": "A clinician reviews an arrhythmia episode and records a decision.",
        "proof_boundary": "The episode decision and evidence are reviewable.",
        "internal_systems": [
            "Episode Intake — captures one arrhythmia episode",
            "Decision Review — records the clinical decision",
        ],
    }

    assert title_needs_repair("Admin Console")
    assert derived_title(intent, fallback="Admin Console") == "Arrhythmia Episode Record Workspace"


def test_recovered_title_uses_the_result_object_without_action_or_status_debris() -> None:
    assert recovered_title("A permit review result") == "Permit Review Workspace"
    assert recovered_title("See a confirmed placement receipt") == "Placement Receipt Workspace"


@pytest.mark.parametrize(
    ("prompt", "expected_title"),
    (
        (
            "An AI assistant helps a permit clerk review one permit packet, record the current status, "
            "and see a permit review result.",
            "Permit Review Workspace",
        ),
        (
            "A coordinator reviews one request, records the placement, and sees a confirmed placement receipt.",
            "Placement Receipt Workspace",
        ),
    ),
)
def test_prompt_materialization_does_not_promote_result_sentences_to_product_titles(
    tmp_path, prompt: str, expected_title: str
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=intent_title(prompt),
    )

    assert intent["title"] == expected_title
