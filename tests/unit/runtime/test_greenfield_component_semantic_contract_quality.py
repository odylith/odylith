from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues


def test_component_contract_removes_actor_and_handoff_verbs_from_artifact_nouns() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Visit Capture Service",
            "source_system_description": (
                "captures the service visit, equipment identity, observed condition, "
                "technician note, and correction history"
            ),
        },
        proposal={
            "intent": {
                "title": "Field Service Notebook",
                "first_path": (
                    "A technician opens a new service visit, selects the equipment, records the observed "
                    "condition and note, saves the visit, sees it on the equipment timeline, edits the note "
                    "when a mistake is found, and hands off one service visit with equipment identity, "
                    "condition, note, timestamp, timeline visibility, and follow-up evidence."
                ),
            }
        },
        sibling={"label": "Equipment Timeline Service"},
        previous_label="Equipment Directory",
        next_label="Equipment Timeline Service",
        state_label="Service Visit Record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "hand visit" not in rendered
    assert "technician open" not in rendered
    assert "service visit" in rendered
    assert not generated_semantic_slop_issues(contract)
