from __future__ import annotations

from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import proposal_memory


def test_accepted_memory_and_handoff_strip_editorial_first_path_framing() -> None:
    raw_first_path = (
        "A person records one entry and sees a trend. That loop - log, repeat, see the pattern - is the smallest "
        "version of the whole product working end to end."
    )
    proposal = {
        "apply_semantic_input": {"first_path": raw_first_path},
        "intent": {"first_path": raw_first_path},
        "semantic_model": {},
    }

    accepted = proposal_memory._accepted_memory_proposal(proposal)

    assert "smallest version of the whole product" not in accepted["intent"]["first_path"]
    assert "smallest version of the whole product" not in greenfield_experience._first_path_summary(proposal)
