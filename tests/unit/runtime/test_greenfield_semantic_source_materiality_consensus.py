from __future__ import annotations

from copy import deepcopy

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    PARALLEL_MATERIALITY_DECISION_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_hypothesis_comparison import (
    independent_source_materiality_observation,
    independently_confirmed_material_ambiguity,
)


REF = {
    "source_id": "operator_prompt",
    "quote": "Create the requested project.",
    "occurrence": 1,
}


def test_two_sources_challenge_an_authorized_but_absent_visible_result() -> None:
    observation = independent_source_materiality_observation(
        [_candidate(outputs=0), _candidate(outputs=0)],
        decision=_decision(),
    )

    assert observation == {
        "status": "critic_authorization_disputed",
        "materiality_field": "visible_result",
        "source_axis_presence": [False, False],
        "source_hypothesis_count": 2,
    }


def test_one_source_ambiguity_cannot_hide_two_source_axis_absence() -> None:
    ambiguous = _candidate(outputs=0)
    ambiguous["source"]["boundary"]["ambiguities"] = [
        {
            "materiality_field": "visible_result",
            "question": "What visible result should the workflow produce?",
            "source_refs": [REF],
        }
    ]

    observation = independent_source_materiality_observation(
        [ambiguous, _candidate(outputs=0)],
        decision=_decision(),
    )

    assert observation == {
        "status": "critic_authorization_disputed",
        "materiality_field": "visible_result",
        "source_axis_presence": [False, False],
        "source_hypothesis_count": 2,
    }


def test_two_sources_challenge_an_authorized_but_absent_human_role() -> None:
    decision = _decision()
    decision["fields"]["visible_result"]["status"] = "explicit"

    observation = independent_source_materiality_observation(
        [_candidate(actors=0, outputs=1), _candidate(actors=0, outputs=1)],
        decision=decision,
    )

    assert observation == {
        "status": "critic_authorization_disputed",
        "materiality_field": "role",
        "source_axis_presence": [False, False],
        "source_hypothesis_count": 2,
    }


def test_two_sources_dispute_a_role_question_when_both_name_an_actor() -> None:
    observation = independent_source_materiality_observation(
        [_candidate(actors=1), _candidate(actors=1)],
        decision=_decision(clarification="role"),
    )

    assert observation == {
        "status": "critic_clarification_disputed",
        "materiality_field": "role",
        "source_axis_presence": [True, True],
        "source_hypothesis_count": 2,
    }


def test_one_source_disagreement_routes_to_adjudication_without_overriding() -> None:
    decision = _decision(clarification="role")
    assert independent_source_materiality_observation(
        [_candidate(actors=1), _candidate(actors=0)],
        decision=decision,
    ) == {
        "status": "source_axis_disagreement",
        "materiality_field": "role",
        "source_axis_presence": [True, False],
        "source_hypothesis_count": 2,
    }


def test_one_source_ambiguity_is_not_authority_but_two_matching_fields_are() -> None:
    decision = _decision(clarification="role")
    role = {
        "materiality_field": "role",
        "question": "Who owns the action?",
        "source_refs": [REF],
    }
    assert independently_confirmed_material_ambiguity(None, role) is None
    assert independently_confirmed_material_ambiguity(
        {**role, "question": "Which role owns the action?"}, role
    ) == role
    ambiguous = _candidate(actors=1)
    ambiguous["source"]["boundary"]["ambiguities"] = [
        {
            "materiality_field": "role",
            "question": "Who owns the action?",
            "source_refs": [REF],
        }
    ]
    assert independent_source_materiality_observation(
        [ambiguous, _candidate(actors=1)],
        decision=decision,
    ) == {
        "status": "critic_clarification_disputed",
        "materiality_field": "role",
        "source_axis_presence": [True, True],
        "source_hypothesis_count": 2,
    }


def _candidate(*, actors: int = 1, outputs: int = 0) -> dict:
    return {
        "source": {
            "path": {
                "identities": [{}],
                "actors": [{}] * actors,
                "workflow_steps": [{}],
                "state_objects": [],
                "visible_outputs": [{}] * outputs,
            },
            "boundary": {
                "external_systems": [],
                "policies": [],
                "ambiguities": [],
            },
        }
    }


def _decision(*, clarification: str = "") -> dict:
    fields = {
        field: {
            "status": "source_entailable",
            "source_refs": [deepcopy(REF)],
            "alternatives": [],
        }
        for field in SEMANTIC_CLARIFICATION_FIELDS
    }
    if clarification:
        outcome = {
            "decision": "clarification_required",
            "clarification": {
                "field": clarification,
                "question": "Who owns the requested action?",
                "source_refs": [deepcopy(REF)],
                "alternatives": [],
            },
        }
    else:
        outcome = {
            "decision": "authorize_graph",
            "clarification": {
                "field": "",
                "question": "",
                "source_refs": [],
                "alternatives": [],
            },
        }
    return {
        "version": PARALLEL_MATERIALITY_DECISION_VERSION,
        "outcome": outcome,
        "fields": fields,
    }
