from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    ATOMIC_SOURCE_CANDIDATES_VERSION,
    atomic_source_candidates_without_discarded,
)


def test_discarded_subspan_removes_its_containing_atomic_candidate() -> None:
    prompt = "Build the board. Exclude the retired label Velvet Sprocket."
    candidates = {
        "version": ATOMIC_SOURCE_CANDIDATES_VERSION,
        "candidates": [
            {
                "candidate_id": "candidate.0",
                "source_ref": {
                    "source_id": "operator_prompt", "quote": "Build the board.",
                    "occurrence": 1,
                },
            },
            {
                "candidate_id": "candidate.1",
                "source_ref": {
                    "source_id": "operator_prompt",
                    "quote": "Exclude the retired label Velvet Sprocket.",
                    "occurrence": 1,
                },
            },
        ],
    }

    result = atomic_source_candidates_without_discarded(
        candidates,
        discarded_source_refs=[{
            "source_id": "operator_prompt", "quote": "Velvet Sprocket",
            "occurrence": 1,
        }],
        evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
    )

    assert [row["candidate_id"] for row in result["candidates"]] == ["candidate.0"]
