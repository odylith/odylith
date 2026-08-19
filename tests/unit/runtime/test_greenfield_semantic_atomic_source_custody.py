from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    ATOMIC_SOURCE_ADJUDICATION_VERSION,
    ATOMIC_SOURCE_CANDIDATES_VERSION,
    require_atomic_source_candidates,
    select_atomic_source_claims,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_claims import (
    SEMANTIC_SOURCE_CLAIMS_VERSION,
)


PROMPT = "A coordinator claims a card. Discard the old Lantern label."
ACTION_QUOTE = "A coordinator claims a card."
NOISE_QUOTE = "Discard the old Lantern label."


def test_atomic_candidates_bind_one_source_proposition_to_multiple_typed_rows() -> None:
    adjudication, claims = select_atomic_source_claims(
        _candidates(),
        _adjudication(),
        evidence_sources=_evidence(),
        settled_fields=_settled_fields(),
    )

    assert adjudication["candidate_decisions"][0] == {
        "candidate_id": "candidate.action",
        "decision": "retain",
        "fact_ids": ["actor.0", "step.0"],
        "relation_ids": ["relation.owned_by.0"],
    }
    assert adjudication["candidate_decisions"][1]["decision"] == "reject_noise"
    assert {row["fact"]["fact_id"] for row in claims["facts"]} == {
        "actor.0",
        "step.0",
    }
    assert claims["relations"][0]["relation"]["kind"] == "owned_by"


def test_atomic_candidate_cannot_bind_a_fact_with_a_different_citation() -> None:
    adjudication = _adjudication()
    adjudication["source_claims"]["facts"][0]["fact"]["source_refs"] = [
        _ref(NOISE_QUOTE)
    ]

    with pytest.raises(ValueError, match="changes its exact source citation"):
        select_atomic_source_claims(
            _candidates(),
            adjudication,
            evidence_sources=_evidence(),
            settled_fields=_settled_fields(),
        )


def test_selected_source_graph_cannot_carry_an_unbound_fact() -> None:
    adjudication = _adjudication()
    extra = deepcopy(adjudication["source_claims"]["facts"][0])
    extra["fact"]["fact_id"] = "actor.1"
    adjudication["source_claims"]["facts"].append(extra)

    with pytest.raises(ValueError, match="unbound fact or relation"):
        select_atomic_source_claims(
            _candidates(),
            adjudication,
            evidence_sources=_evidence(),
            settled_fields=_settled_fields(),
        )


def test_rejected_noise_candidate_cannot_bind_product_truth() -> None:
    adjudication = _adjudication()
    adjudication["candidate_decisions"][1] = {
        "candidate_id": "candidate.noise",
        "decision": "reject_noise",
        "fact_ids": ["actor.0"],
        "relation_ids": [],
    }

    with pytest.raises(ValueError, match="rejected atomic candidate still binds"):
        select_atomic_source_claims(
            _candidates(),
            adjudication,
            evidence_sources=_evidence(),
            settled_fields=_settled_fields(),
        )


def test_every_atomic_candidate_requires_one_author_decision() -> None:
    adjudication = _adjudication()
    adjudication["candidate_decisions"].pop()

    with pytest.raises(ValueError, match="do not cover every candidate"):
        select_atomic_source_claims(
            _candidates(),
            adjudication,
            evidence_sources=_evidence(),
            settled_fields=_settled_fields(),
        )


def test_duplicate_atomic_span_is_canonicalized_without_extra_coverage() -> None:
    candidates = _candidates()
    candidates["candidates"][1]["source_ref"] = _ref(ACTION_QUOTE)

    normalized = require_atomic_source_candidates(
        candidates,
        evidence_sources=_evidence(),
    )

    assert normalized["candidates"] == [candidates["candidates"][0]]


def test_atomic_source_custody_owner_has_no_regex_fuzzy_or_token_parser() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "src/odylith/runtime/domain_intelligence/greenfield_semantic_atomic_source_custody.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prohibited = {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert imports.isdisjoint(prohibited)


def _candidates() -> dict:
    return {
        "version": ATOMIC_SOURCE_CANDIDATES_VERSION,
        "candidates": [
            {
                "candidate_id": "candidate.action",
                "source_ref": _ref(ACTION_QUOTE),
            },
            {
                "candidate_id": "candidate.noise",
                "source_ref": _ref(NOISE_QUOTE),
            },
        ],
    }


def _adjudication() -> dict:
    source_ref = _ref(ACTION_QUOTE)
    return {
        "version": ATOMIC_SOURCE_ADJUDICATION_VERSION,
        "candidate_decisions": [
            {
                "candidate_id": "candidate.action",
                "decision": "retain",
                "fact_ids": ["actor.0", "step.0"],
                "relation_ids": ["relation.owned_by.0"],
            },
            {
                "candidate_id": "candidate.noise",
                "decision": "reject_noise",
                "fact_ids": [],
                "relation_ids": [],
            },
        ],
        "source_claims": {
            "version": SEMANTIC_SOURCE_CLAIMS_VERSION,
            "facts": [
                {
                    "field": "role",
                    "fact": {
                        "fact_id": "actor.0",
                        "kind": "actor",
                        "label": "Coordinator",
                        "statement": "A coordinator claims a card.",
                        "order": 0,
                        "owner_kind": "none",
                        "custody": "source_fact",
                        "attributes": [
                            {"name": "responsibility", "value": "claim a card"}
                        ],
                        "source_refs": [source_ref],
                    },
                },
                {
                    "field": "first_path",
                    "fact": {
                        "fact_id": "step.0",
                        "kind": "workflow_step",
                        "label": "Claim card",
                        "statement": "A coordinator claims a card.",
                        "order": 0,
                        "owner_kind": "actor",
                        "custody": "source_fact",
                        "attributes": [
                            {"name": "action", "value": "claim"},
                            {"name": "action_phrase", "value": "claim a card"},
                        ],
                        "source_refs": [source_ref],
                    },
                },
            ],
            "relations": [
                {
                    "fields": ["role", "first_path"],
                    "relation": {
                        "relation_id": "relation.owned_by.0",
                        "kind": "owned_by",
                        "subject_id": "step.0",
                        "object_id": "actor.0",
                        "order": 0,
                        "custody": "source_fact",
                        "source_refs": [source_ref],
                    },
                }
            ],
        },
    }


def _ref(quote: str) -> dict:
    return {"source_id": "operator_prompt", "quote": quote, "occurrence": 1}


def _evidence() -> dict[str, str]:
    return {"operator_prompt": PROMPT, "operator_edit": ""}


def _settled_fields() -> dict[str, dict]:
    return {
        "identity": {},
        "role": {},
        "first_path": {},
    }
