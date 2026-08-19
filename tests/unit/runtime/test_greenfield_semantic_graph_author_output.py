from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_graph_author_output import (
    require_semantic_graph_author_output,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
    require_semantic_intent_packet,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_source_ref_catalog,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_graph_extension_from_intent,
    semantic_intent_packet,
)


def test_graph_author_output_builds_the_full_production_packet() -> None:
    expected = semantic_intent_packet()
    assessment = expected["materiality_assessment"]
    extension = _citation_handles(
        semantic_graph_extension_from_intent(expected["semantic_intent"]),
        assessment=assessment,
    )
    author_output = {
        "source_candidate_adjudication": deepcopy(
            expected["source_candidate_adjudication"]
        ),
        "semantic_extension": extension,
        "self_challenge": [
            {"challenge": challenge, "status": "passed"}
            for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
        ],
    }

    packet = build_semantic_intent_packet(
        assessment,
        author_output,
        prompt=SEMANTIC_PROMPT,
        critic_run_id="production-critic-run",
        author_run_id="production-author-run",
        critic_host_profile="codex",
    )
    verified = require_semantic_intent_packet(packet, prompt=SEMANTIC_PROMPT)

    assert packet["semantic_intent"] == expected["semantic_intent"]
    assert packet["source_candidate_adjudication"] == expected[
        "source_candidate_adjudication"
    ]
    assert verified.product_facts is not None


def test_graph_author_output_fails_when_a_mandatory_challenge_fails() -> None:
    rows = [
        {"challenge": challenge, "status": "passed"}
        for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
    ]
    rows[0]["status"] = "failed"

    with pytest.raises(ValueError, match="failed mandatory challenge"):
        require_semantic_graph_author_output({
            "source_candidate_adjudication": {},
            "semantic_extension": {},
            "self_challenge": rows,
        })


def test_graph_author_output_owner_has_no_regex_or_token_authority() -> None:
    source = Path(
        "src/odylith/runtime/domain_intelligence/greenfield_semantic_graph_author_output.py"
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


def _citation_handles(extension: dict, *, assessment: dict) -> dict:
    result = deepcopy(extension)
    catalog = semantic_materiality_source_ref_catalog(
        assessment,
        evidence_sources={"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""},
    )
    ids = {
        (row["source_id"], row["quote"], row["occurrence"]): row["ref_id"]
        for row in catalog
    }
    owners = [result["clarification"], *result["narratives"]]
    for node in result["nodes"]:
        owners.append(node["fact"])
        for kind in (
            "depends_on",
            "implements",
            "constrained_by",
            "excludes",
            "incoming_changes",
        ):
            owners.extend(node[kind])
    for owner in owners:
        owner["source_refs"] = [
            {"ref_id": ids[(row["source_id"], row["quote"], row["occurrence"])]}
            for row in owner["source_refs"]
        ]
    return result
