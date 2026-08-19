from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_graph import (
    SEMANTIC_AUTHORING_GRAPH_VERSION,
    compile_semantic_authoring_graph,
    semantic_authoring_graph_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


def test_small_authoring_graph_compiles_to_the_exact_full_production_packet() -> None:
    expected = semantic_intent_packet()
    assessment = expected["materiality_assessment"]
    authoring_graph = _authoring_graph(expected)

    author_output = compile_semantic_authoring_graph(
        authoring_graph,
        assessment=assessment,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )
    packet = build_semantic_intent_packet(
        assessment,
        author_output,
        prompt=SEMANTIC_PROMPT,
        critic_run_id="small-graph-critic",
        author_run_id="small-graph-author",
        critic_host_profile="codex",
    )

    assert packet["semantic_intent"] == expected["semantic_intent"]
    assert packet["source_candidate_adjudication"] == expected[
        "source_candidate_adjudication"
    ]


def test_authoring_graph_schema_is_small_and_has_no_repeated_source_ref_variants() -> None:
    assessment = semantic_intent_packet()["materiality_assessment"]
    encoded = json.dumps(
        semantic_authoring_graph_schema(assessment),
        separators=(",", ":"),
        sort_keys=True,
    )

    assert len(encoded) < 25_000
    assert encoded.count('"anyOf"') == 1
    assert "source_refs" not in encoded


def test_authoring_graph_owner_has_no_regex_fuzzy_or_token_authority() -> None:
    source = Path(
        "src/odylith/runtime/domain_intelligence/greenfield_semantic_authoring_graph.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint(
        {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    )


def _authoring_graph(packet: dict) -> dict:
    assessment = packet["materiality_assessment"]
    candidate_ids = {
        (
            row["source_ref"]["source_id"],
            row["source_ref"]["quote"],
            row["source_ref"]["occurrence"],
        ): row["candidate_id"]
        for row in assessment["source_candidates"]["candidates"]
    }

    def ids(row: dict) -> list[str]:
        return list(dict.fromkeys(
            candidate_ids[(ref["source_id"], ref["quote"], ref["occurrence"])]
            for ref in row["source_refs"]
        ))

    collections = {
        "identity": "identities",
        "actor": "actors",
        "workflow_step": "workflow_steps",
        "state_object": "state_objects",
        "visible_output": "visible_outputs",
        "external_system": "external_systems",
        "internal_system": "internal_systems",
        "component_responsibility": "component_responsibilities",
        "operational_constraint": "operational_constraints",
        "non_goal": "non_goals",
        "assumption": "assumptions",
        "ambiguity": "ambiguities",
    }
    facts = {collection: [] for collection in collections.values()}
    for raw in packet["semantic_intent"]["facts"]:
        row = deepcopy(raw)
        refs = ids(row)
        row.pop("source_refs")
        kind = row.pop("kind")
        if kind != "workflow_step":
            row.pop("owner_kind")
        row["candidate_ids"] = refs
        facts[collections[kind]].append(row)
    relations = {
        kind: []
        for kind in (
            "owned_by", "produces", "changes", "depends_on", "implements",
            "constrained_by", "excludes",
        )
    }
    for raw in packet["semantic_intent"]["relations"]:
        row = deepcopy(raw)
        refs = ids(row)
        row.pop("source_refs")
        kind = row.pop("kind")
        row["candidate_ids"] = refs
        relations[kind].append(row)
    narratives = []
    for raw in packet["semantic_intent"]["narratives"]:
        row = deepcopy(raw)
        refs = ids(row)
        row.pop("source_refs")
        row["candidate_ids"] = refs
        narratives.append(row)
    return {
        "version": SEMANTIC_AUTHORING_GRAPH_VERSION,
        "status": "complete",
        "clarification": {"question": "", "fields": [], "candidate_ids": []},
        "candidate_decisions": [
            {"candidate_id": row["candidate_id"], "decision": "retain"}
            for row in assessment["source_candidates"]["candidates"]
        ],
        "facts": facts,
        "fact_sequence": [row["fact_id"] for row in packet["semantic_intent"]["facts"]],
        "relations": relations,
        "relation_sequence": [
            row["relation_id"] for row in packet["semantic_intent"]["relations"]
        ],
        "narratives": narratives,
        "self_challenge": [
            {"challenge": challenge, "status": "passed"}
            for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
        ],
    }
