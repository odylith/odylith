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
    semantic_graph_extension_from_intent,
    semantic_intent_packet,
)


SOURCE = Path(
    "src/odylith/runtime/domain_intelligence/greenfield_semantic_graph_extension.py"
)


def _extension(packet: dict[str, object]) -> dict[str, object]:
    graph = packet["semantic_intent"]
    assert isinstance(graph, dict)
    return semantic_graph_extension_from_intent(graph)


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
        row["fact"]["custody"] == "bounded_interpretation"
        for row in _extension(packet)["nodes"]
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
    assert "relations" not in schema["properties"]
    variants = schema["properties"]["nodes"]["items"]["anyOf"]
    assert {
        variant["properties"]["fact"]["properties"]["kind"]["enum"][0]
        for variant in variants
    }.isdisjoint({"actor", "workflow_step", "visible_output"})
    assert all(
        variant["properties"]["fact"]["properties"]["custody"]["enum"]
        == ["bounded_interpretation"]
        for variant in variants
    )
    internal_system = next(
        variant
        for variant in variants
        if variant["properties"]["fact"]["properties"]["kind"]["enum"]
        == ["internal_system"]
    )
    for kind in ("depends_on", "implements", "constrained_by", "excludes"):
        edge = internal_system["properties"][kind]["items"]
        assert "subject_id" not in edge["properties"]
        assert "kind" not in edge["properties"]
        assert "custody" not in edge["properties"]


def test_extension_rejects_source_rows_and_relations_between_locked_source_facts() -> None:
    packet = semantic_intent_packet()
    assessment = packet["materiality_assessment"]
    source_fact = _extension(packet)
    source_fact["nodes"].append(
        {
            "fact": copy.deepcopy(
                assessment["source_candidates"]["facts"][0]["fact"]
            ),
            "depends_on": [],
            "implements": [],
            "constrained_by": [],
            "excludes": [],
            "incoming_changes": [],
        }
    )
    with pytest.raises(ValueError, match="non-bounded fact authority"):
        assemble_semantic_intent_from_extension(
            source_fact,
            assessment=assessment,
            source_claims=_source_claims(packet),
        )

    source_relation = _extension(packet)
    internal_node = next(
        row
        for row in source_relation["nodes"]
        if row["fact"]["kind"] == "internal_system" and row["implements"]
    )
    internal_node["implements"][0]["subject_id"] = "source.workflow"
    with pytest.raises(
        ValueError,
        match="Semantic implements edge has unsupported or missing fields",
    ):
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
