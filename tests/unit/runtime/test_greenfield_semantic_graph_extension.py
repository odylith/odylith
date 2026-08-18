from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_extension import (
    SEMANTIC_GRAPH_EXTENSION_VERSION,
    assemble_semantic_intent_from_extension,
    semantic_graph_extension_schema_for_materiality,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_candidate_adjudication import (
    selected_semantic_source_claims,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


SOURCE = Path(
    "src/odylith/runtime/domain_intelligence/greenfield_semantic_graph_extension.py"
)


def _extension(packet: dict[str, object]) -> dict[str, object]:
    graph = packet["semantic_intent"]
    assert isinstance(graph, dict)
    return {
        "version": SEMANTIC_GRAPH_EXTENSION_VERSION,
        "status": graph["status"],
        "clarification": copy.deepcopy(graph["clarification"]),
        "facts": [
            copy.deepcopy(row)
            for row in graph["facts"]
            if row["custody"] == "bounded_interpretation"
        ],
        "relations": [
            copy.deepcopy(row)
            for row in graph["relations"]
            if row["custody"] == "bounded_interpretation"
        ],
        "narratives": copy.deepcopy(graph["narratives"]),
    }


def _source_claims(packet: dict[str, object]) -> dict[str, object]:
    assessment = packet["materiality_assessment"]
    assert isinstance(assessment, dict)
    return selected_semantic_source_claims(
        assessment,
        packet["source_candidate_adjudication"],
    )


def test_graph_extension_assembles_the_exact_intent_without_source_row_repetition() -> None:
    packet = semantic_intent_packet()
    assessment = packet["materiality_assessment"]
    graph = packet["semantic_intent"]
    assembled = assemble_semantic_intent_from_extension(
        _extension(packet),
        assessment=assessment,
        source_claims=_source_claims(packet),
    )

    assert assembled == graph
    assert all(
        row["custody"] == "bounded_interpretation"
        for row in _extension(packet)["facts"]
    )
    assert all(
        row["fact"]["custody"] == "source_fact"
        for row in assessment["source_candidates"]["facts"]
    )


def test_provider_schema_cannot_express_source_semantics_in_the_extension() -> None:
    packet = semantic_intent_packet()
    assessment = packet["materiality_assessment"]
    schema = semantic_graph_extension_schema_for_materiality(
        assessment,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )

    assert schema["properties"]["version"]["enum"] == [
        SEMANTIC_GRAPH_EXTENSION_VERSION
    ]
    variants = schema["properties"]["facts"]["items"]["anyOf"]
    assert {
        variant["properties"]["kind"]["enum"][0]
        for variant in variants
    }.isdisjoint({"actor", "workflow_step", "visible_output"})
    assert all(
        variant["properties"]["custody"]["enum"] == ["bounded_interpretation"]
        for variant in variants
    )
    relation = schema["properties"]["relations"]["items"]["properties"]
    assert relation["custody"]["enum"] == ["bounded_interpretation"]
    assert set(relation["kind"]["enum"]).isdisjoint({"owned_by", "produces"})


def test_extension_rejects_source_rows_and_relations_between_locked_source_facts() -> None:
    packet = semantic_intent_packet()
    assessment = packet["materiality_assessment"]
    source_fact = _extension(packet)
    source_fact["facts"].append(
        copy.deepcopy(assessment["source_candidates"]["facts"][0]["fact"])
    )
    with pytest.raises(ValueError, match="non-bounded fact authority"):
        assemble_semantic_intent_from_extension(
            source_fact,
            assessment=assessment,
            source_claims=_source_claims(packet),
        )

    source_relation = _extension(packet)
    relation = copy.deepcopy(
        assessment["source_candidates"]["relations"][4]["relation"]
    )
    relation["relation_id"] = "bounded.but-source-semantic"
    relation["custody"] = "bounded_interpretation"
    source_relation["relations"].append(relation)
    with pytest.raises(ValueError, match="boundary relation lacks a bounded subject"):
        assemble_semantic_intent_from_extension(
            source_relation,
            assessment=assessment,
            source_claims=_source_claims(packet),
        )


def test_graph_extension_owner_has_no_regex_fuzzy_or_model_authority() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    prohibited = {
        "re",
        "regex",
        "difflib",
        "rapidfuzz",
        "nltk",
        "spacy",
        "tokenize",
    }
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert imports.isdisjoint(prohibited)
