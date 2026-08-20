from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_semantic_policy_edge_alignment import (
    align_completion_policy_edges,
)


PROMPT = "Never reassign a card automatically."
REF = {"source_id": "operator_prompt", "quote": PROMPT, "occurrence": 1}


def test_completion_policy_edge_follows_settled_source_kind() -> None:
    completion = {
        "internal_systems": [{
            "constrained_by": [{"object_id": "constraint.0", "source_refs": [REF]}],
            "excludes": [],
        }]
    }
    provisional = {
        "facts": [{
            "fact_id": "constraint.0", "kind": "operational_constraint",
            "source_refs": [REF],
        }]
    }
    settled = {
        "facts": [{
            "fact_id": "non-goal.0", "kind": "non_goal", "source_refs": [REF],
        }]
    }

    result = align_completion_policy_edges(
        completion,
        provisional_source=provisional,
        settled_source=settled,
        evidence_sources={"operator_prompt": PROMPT, "operator_edit": ""},
    )

    system = result["internal_systems"][0]
    assert system["constrained_by"] == []
    assert system["excludes"] == [{"object_id": "non-goal.0", "source_refs": [REF]}]


def test_compact_single_system_leaves_policy_binding_to_compiler() -> None:
    completion = {
        "internal_systems": [{
            "label": "Claim service",
            "responsibility": "Own the accepted claim path.",
        }]
    }
    source = {
        "facts": [{
            "fact_id": "constraint.0",
            "kind": "operational_constraint",
            "source_refs": [REF],
        }]
    }

    assert align_completion_policy_edges(
        completion,
        provisional_source=source,
        settled_source=source,
        evidence_sources={"operator_prompt": PROMPT, "operator_edit": ""},
    ) == completion
