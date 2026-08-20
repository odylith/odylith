from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import greenfield_semantic_source_pair_adjudicator as source_pair
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    PARALLEL_MATERIALITY_DECISION_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_hypothesis_comparison import (
    independent_source_materiality_observation,
)


PROMPT = "Create the requested project."
REF = {"source_id": "operator_prompt", "quote": PROMPT, "occurrence": 1}


def test_fourth_call_turns_a_two_source_visible_result_gap_into_one_question(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    decision = _decision()
    candidates = [_candidate(outputs=0), _candidate(outputs=0)]
    source = _handoff(candidates, decision=decision)
    calls: list[dict] = []
    monkeypatch.setattr(
        source_pair,
        "run_structured_host",
        lambda **kwargs: (
            calls.append(dict(kwargs))
            or (
                {
                    "version": source_pair.MATERIALITY_PAIR_ADJUDICATION_VERSION,
                    "decision": "clarification_required",
                    "clarification": {
                        "question": "What observable result should be visible?",
                        "fields": ["visible_result"],
                        "source_refs": [deepcopy(REF)],
                    },
                },
                {"input_tokens": 10},
                4_000,
            )
        ),
    )

    receipt = source_pair.run_source_pair_adjudication(
        corpus_path=_corpus(tmp_path),
        case_id="case",
        critic={"decision": decision},
        source_receipt=source,
        host_profile="codex",
        model="gpt-5.6-sol",
        reasoning_effort="low",
        budget_seconds=26,
    )

    assert receipt["source_status"] == "not_applicable"
    assert receipt["candidate"] is None
    assert receipt["materiality_decision"]["outcome"]["clarification"][
        "field"
    ] == "visible_result"
    assert len(calls) == 1
    assert "Do not author, merge, or repair a graph" in calls[0]["prompt"]
    assert calls[0]["schema"]["properties"]["decision"]["enum"] == [
        "clarification_required"
    ]


def test_fourth_call_can_reject_a_false_role_question_and_admit_existing_graph(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    decision = _decision(clarification="role")
    candidates = [_candidate(actors=1, outputs=1), _candidate(actors=1, outputs=1)]
    source = _handoff(candidates, decision=decision)
    calls: list[dict] = []
    monkeypatch.setattr(
        source_pair,
        "run_structured_host",
        lambda **kwargs: (
            calls.append(dict(kwargs))
            or (
                {
                    "version": source_pair.MATERIALITY_PAIR_ADJUDICATION_VERSION,
                    "decision": "authorize_graph",
                    "clarification": {
                        "question": "",
                        "fields": [],
                        "source_refs": [],
                    },
                },
                {},
                3_000,
            )
        ),
    )
    admitted = candidates[1]
    monkeypatch.setattr(
        source_pair,
        "admit_partitioned_candidate",
        lambda candidate, **_: (
            admitted,
            {"facts": [{"fact_id": "actor.0"}], "relations": []},
            [],
            {"typed_graph": True},
        ),
    )
    monkeypatch.setattr(source_pair, "source_candidate_discarded_refs", lambda _: [])

    receipt = source_pair.run_source_pair_adjudication(
        corpus_path=_corpus(tmp_path),
        case_id="case",
        critic={"decision": decision},
        source_receipt=source,
        host_profile="codex",
        model="gpt-5.6-sol",
        reasoning_effort="low",
        budget_seconds=26,
    )

    assert receipt["source_status"] == "approved"
    assert receipt["compiled_author_output"] == {"typed_graph": True}
    assert receipt["materiality_decision"]["outcome"]["decision"] == (
        "authorize_graph"
    )
    assert len(calls) == 1
    assert calls[0]["schema"]["properties"]["decision"]["enum"] == [
        "authorize_graph",
        "clarification_required",
    ]


def _handoff(candidates: list[dict], *, decision: dict) -> dict:
    observation = independent_source_materiality_observation(
        candidates, decision=decision
    )
    assert observation is not None
    return {
        "source_pair_dispute": "materiality",
        "materiality_observation": observation,
        "hypothesis_candidates": [
            {
                "run_index": index,
                "hypothesis_mode": "full_graph" if index == 0 else "source_only",
                "candidate": candidate,
            }
            for index, candidate in enumerate(candidates)
        ],
    }


def _candidate(*, actors: int = 1, outputs: int = 0) -> dict:
    return {
        "version": "test.partitioned",
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
                "discarded_evidence": [],
            },
        },
        "completion": {},
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
    outcome = {
        "decision": "clarification_required" if clarification else "authorize_graph",
        "clarification": {
            "field": clarification,
            "question": "Who owns the action?" if clarification else "",
            "source_refs": [deepcopy(REF)] if clarification else [],
            "alternatives": [],
        },
    }
    return {
        "version": PARALLEL_MATERIALITY_DECISION_VERSION,
        "outcome": outcome,
        "fields": fields,
    }


def _corpus(tmp_path: Path) -> Path:
    path = tmp_path / "corpus.json"
    path.write_text(
        json.dumps({"cases": [{"case_id": "case", "prompt": PROMPT}]}),
        encoding="utf-8",
    )
    return path
