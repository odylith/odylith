from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    build_semantic_projection_plan,
    semantic_projection_plan_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    select_atomic_source_claims,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    STATE_EVIDENCE,
    semantic_intent_packet,
    semantic_ref,
)


SOURCE = Path(
    "src/odylith/runtime/domain_intelligence/greenfield_semantic_source_claims.py"
)


def test_atomic_spans_carry_no_semantic_authority_and_author_claims_lock_source_rows() -> None:
    packet = semantic_intent_packet()
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)
    candidates = verified.materiality_assessment["source_candidates"]
    claims = verified.source_claims

    assert all(
        set(row) == {"candidate_id", "source_ref"}
        for row in candidates["candidates"]
    )

    assert {row["fact"]["fact_id"] for row in claims["facts"]} == {
        "identity.0",
        "actor.0",
        "step.0",
        "step.1",
        "state.0",
        "output.0",
        "dependency.0",
        "constraint.0",
        "non-goal.0",
    }
    assert {row["relation"]["relation_id"] for row in claims["relations"]} == {
        "relation.owned_by.0",
        "relation.owned_by.1",
        "relation.changes.0",
        "relation.produces.0",
        "relation.depends_on.0",
        "relation.excludes.0",
    }
    owned_by = next(
        row
        for row in claims["relations"]
        if row["relation"]["relation_id"] == "relation.owned_by.0"
    )
    assert owned_by["fields"] == ["role", "first_path"]
    assert all(
        row["custody"] == "bounded_interpretation"
        for row in verified.semantic_intent["facts"]
        if row["kind"] == "internal_system"
    )
    assert all(
        row["relation"]["kind"] != "implements"
        for row in claims["relations"]
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("fact_text", "source facts differ from locked source claims"),
        ("extra_source_fact", "source facts differ from locked source claims"),
        ("relation_custody", "source relations differ from locked source claims"),
        ("relation_citation", "source relations differ from locked source claims"),
    ],
)
def test_graph_author_cannot_change_or_add_source_authority(
    mutation: str,
    message: str,
) -> None:
    packet = copy.deepcopy(semantic_intent_packet())
    graph = packet["semantic_intent"]
    if mutation == "fact_text":
        graph["facts"][0]["statement"] = "A different product identity"
    elif mutation == "extra_source_fact":
        system = next(row for row in graph["facts"] if row["fact_id"] == "system.0")
        system["custody"] = "source_fact"
    elif mutation == "relation_custody":
        graph["relations"][0]["custody"] = "bounded_interpretation"
    else:
        graph["relations"][0]["source_refs"] = [semantic_ref(STATE_EVIDENCE)]

    with pytest.raises(ValueError, match=message):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_source_claim_citation_must_resolve_exactly_to_prompt_evidence() -> None:
    packet = copy.deepcopy(semantic_intent_packet())
    actor_claim = next(
        row
        for row in packet["source_candidate_adjudication"]["source_claims"]["facts"]
        if row["fact"]["fact_id"] == "actor.0"
    )
    actor_claim["fact"]["source_refs"][0]["quote"] = "An invented actor claim."

    with pytest.raises(ValueError, match="does not match exact evidence bytes"):
        require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)


def test_source_claim_cannot_reference_an_unsettled_field() -> None:
    packet = semantic_intent_packet()
    assessment = packet["materiality_assessment"]
    settled = {
        row["field"]: row
        for row in assessment["fields"]
        if row["field"] != "role"
    }

    with pytest.raises(ValueError, match="unresolved field"):
        select_atomic_source_claims(
            assessment["source_candidates"],
            packet["source_candidate_adjudication"],
            evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
            settled_fields=settled,
        )


def test_relation_custody_survives_the_single_projection_plan() -> None:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    plan = build_semantic_projection_plan(
        verified.semantic_intent,
        project_slug="claim-desk",
    )
    persisted = semantic_projection_plan_mapping(plan)

    custody = {row["relation_id"]: row["custody_state"] for row in persisted["edges"]}
    assert custody["relation.owned_by.0"] == "source_fact"
    assert custody["relation.implements.0"] == "bounded_interpretation"


def test_source_claim_owners_have_no_regex_fuzzy_or_model_authority() -> None:
    banned_imports = {
        "re",
        "regex",
        "difflib",
        "rapidfuzz",
        "nltk",
        "spacy",
        "tokenize",
    }
    for source in (
        SOURCE,
        SOURCE.with_name("greenfield_semantic_atomic_source_custody.py"),
    ):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert imports.isdisjoint(banned_imports)
        assert not {"search", "match", "fullmatch", "findall", "model_call"} & calls
