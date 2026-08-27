from __future__ import annotations

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
    semantic_source_meaning_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_VERSION,
    require_product_intent_authority_structure,
)
from tests.unit.runtime.test_greenfield_semantic_source_meaning import (
    PROMPT,
    _graph,
)


def _run(graph: dict[str, object]) -> dict[str, object]:
    digest = semantic_source_meaning_sha256(graph)
    return {
        "version": SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
        "capability_profile": "frontier_semantic_reasoning",
        "run_id": "standard:source-meaning-author:fixture",
        "host_profile": "codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "budget_seconds": 54,
        "wall_ms": 12000,
        "usage": {"input_tokens": 100, "output_tokens": 200},
        "graph_sha256": digest,
        "model_call_count": 1,
        "restart_count": 0,
    }


def test_packet_seals_one_author_graph_without_critic_or_candidate_residue() -> None:
    graph = _graph()
    packet = build_semantic_intent_packet(graph, prompt=PROMPT, author_run=_run(graph))
    verified = require_semantic_intent_packet(packet, prompt=PROMPT)
    authority = semantic_intent_authority(verified, prompt=PROMPT)
    require_product_intent_authority_structure(authority)

    assert packet["authoring_contract_sha256"] == (
        semantic_intent_authoring_contract_sha256()
    )
    assert authority["version"] == PRODUCT_INTENT_AUTHORITY_VERSION
    assert authority["fact_authority"] == "semantic_source_meaning_graph"
    legacy = {
        "materiality_assessment",
        "source_candidate_adjudication",
        "critic_run",
        "semantic_source_critic_run",
    }
    assert legacy.isdisjoint(packet)
    assert legacy.isdisjoint(authority)


@pytest.mark.parametrize(
    "mutator,match",
    [
        (
            lambda packet: packet.__setitem__("source_meaning_sha256", "0" * 64),
            "graph hash mismatch",
        ),
        (
            lambda packet: packet["author_run"].__setitem__("restart_count", 1),
            "retry or cascade",
        ),
        (
            lambda packet: packet["semantic_intent"].__setitem__("facts", []),
            "differs from deterministic",
        ),
    ],
)
def test_packet_rejects_rebound_or_noncanonical_bytes(mutator, match: str) -> None:
    graph = _graph()
    packet = build_semantic_intent_packet(graph, prompt=PROMPT, author_run=_run(graph))
    forged = deepcopy(packet)
    mutator(forged)
    with pytest.raises(ValueError, match=match):
        require_semantic_intent_packet(forged, prompt=PROMPT)


def test_packet_rejects_old_author_critic_shape() -> None:
    graph = _graph()
    packet = build_semantic_intent_packet(graph, prompt=PROMPT, author_run=_run(graph))
    packet["critic_run"] = {}
    with pytest.raises(ValueError, match="packet is malformed"):
        require_semantic_intent_packet(packet, prompt=PROMPT)


def test_clarification_packet_preserves_source_graph_without_sealable_authority() -> None:
    graph = _graph()
    graph["workflow"][0]["entity_effects"] = [
        {
            "kind": "input",
            "entity_index": 0,
            "source_refs": [
                {
                    "source_id": "operator_prompt",
                    "quote": "A shift coordinator claims one ready card.",
                    "occurrence": 1,
                }
            ],
        }
    ]
    graph["entities"] = graph["entities"][:1]
    graph["clarification"] = {
        "required": True,
        "question": "Which visible confirmation should the coordinator receive?",
        "source_refs": [
            {
                "source_id": "operator_prompt",
                "quote": "A shift coordinator claims one ready card.",
                "occurrence": 1,
            }
        ],
    }
    packet = build_semantic_intent_packet(graph, prompt=PROMPT, author_run=_run(graph))
    verified = require_semantic_intent_packet(packet, prompt=PROMPT)
    assert verified.semantic_intent["status"] == "clarification_required"
    assert verified.source_meaning_graph["workflow"]
    with pytest.raises(ValueError, match="clarification-bound"):
        semantic_intent_authority(verified, prompt=PROMPT)


def test_authority_preserves_original_unicode_markdown_citation_coordinates() -> None:
    prompt = f"# Café résumé\nUnrelated preface.\n{PROMPT}"
    graph = _graph()
    packet = build_semantic_intent_packet(
        graph, prompt=prompt, author_run=_run(graph)
    )
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    authority = semantic_intent_authority(verified, prompt=prompt)

    assert authority["evidence_sources"]["operator_prompt"] == prompt
    assert authority["accepted_evidence_sha256"] == authority["evidence_sha256"]
    require_product_intent_authority_structure(authority)
