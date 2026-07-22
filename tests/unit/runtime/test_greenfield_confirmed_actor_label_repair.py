from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_label_repair import (
    repair_generic_actor_labels,
)


def test_generic_actor_repair_preserves_untrusted_evidence_fields() -> None:
    proposal = {
        "intent": {
            "title": "Kitchen Robot Controller",
            "human_actors": ["Home cook: selects a recipe and starts a cook."],
            "prompt": "Operator selects a recipe in the untrusted user prompt.",
            "source_title": "Operator source title",
            "source_html": "Operator source evidence",
            "source_excerpt": "Operator source excerpt",
        },
        "host_instruction": "Operator must not become product truth.",
        "observed_source": "Operator source evidence remains untrusted.",
        "project_intelligence": {
            "control_surface_summary": ["Operator selects a recipe and reviews the safe finished state."]
        },
    }

    assert repair_generic_actor_labels(proposal) is True

    assert proposal["intent"]["prompt"] == "Operator selects a recipe in the untrusted user prompt."
    assert proposal["intent"]["source_title"] == "Operator source title"
    assert proposal["intent"]["source_html"] == "Operator source evidence"
    assert proposal["intent"]["source_excerpt"] == "Operator source excerpt"
    assert proposal["host_instruction"] == "Operator must not become product truth."
    assert proposal["observed_source"] == "Operator source evidence remains untrusted."
    assert proposal["project_intelligence"]["control_surface_summary"] == [
        "Home cook selects a recipe and reviews the safe finished state."
    ]
