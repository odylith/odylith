from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import derived_title
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import title_needs_repair


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
