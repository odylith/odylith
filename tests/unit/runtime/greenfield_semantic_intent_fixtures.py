"""Reusable source-meaning fixtures for graph-authority tests."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
    SEMANTIC_SOURCE_MEANING_GRAPH_VERSION,
    semantic_source_meaning_sha256,
)


SEMANTIC_PROMPT = (
    "Build a claim desk. "
    "A shift coordinator claims one ready card and receives a claim receipt. "
    "The card moves from ready to claimed. "
    "Read the local duty roster. "
    "Never reassign a card automatically."
)
IDENTITY_EVIDENCE = "Build a claim desk."
PATH_EVIDENCE = "A shift coordinator claims one ready card and receives a claim receipt."
STATE_EVIDENCE = "The card moves from ready to claimed."
DEPENDENCY_EVIDENCE = "Read the local duty roster."
POLICY_EVIDENCE = "Never reassign a card automatically."
AUTHOR_RUN_ID = "fixture-semantic-source-meaning-author"


def semantic_ref(quote: str) -> dict[str, Any]:
    return {"source_id": "operator_prompt", "quote": quote, "occurrence": 1}


def semantic_fact(
    fact_id: str,
    kind: str,
    label: str,
    statement: str,
    order: int,
    quote: str | list[str],
    *,
    owner_kind: str = "none",
    custody: str = "source_fact",
    attributes: dict[str, str] | None = None,
    transition: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build one typed IR fact for focused projection-only tests."""

    result = {
        "fact_id": fact_id,
        "kind": kind,
        "label": label,
        "statement": statement,
        "order": order,
        "owner_kind": owner_kind,
        "custody": custody,
        "attributes": [
            {"name": name, "value": value}
            for name, value in (attributes or {}).items()
        ],
        "source_refs": [
            semantic_ref(value)
            for value in ([quote] if isinstance(quote, str) else quote)
        ],
    }
    if kind == "state_object":
        result["transition"] = transition
    return result


def semantic_relation(
    kind: str,
    subject_id: str,
    object_id: str,
    order: int,
    quote: str,
    *,
    custody: str = "source_fact",
) -> dict[str, Any]:
    """Build one typed IR relation for focused projection-only tests."""

    return {
        "relation_id": f"relation.{kind}.{order}",
        "kind": kind,
        "subject_id": subject_id,
        "object_id": object_id,
        "order": order,
        "custody": custody,
        "source_refs": [semantic_ref(quote)],
    }


def _source_meaning_author_run(graph: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
        "capability_profile": "frontier_semantic_reasoning",
        "run_id": AUTHOR_RUN_ID,
        "host_profile": "codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "budget_seconds": 54,
        "wall_ms": 12000,
        "usage": {"input_tokens": 100, "output_tokens": 200},
        "graph_sha256": semantic_source_meaning_sha256(graph),
        "model_call_count": 1,
        "restart_count": 0,
    }


def _claim_desk_source_meaning_graph() -> dict[str, Any]:
    return {
        "version": SEMANTIC_SOURCE_MEANING_GRAPH_VERSION,
        "presentation": {
            "title": "Claim Desk",
            "status": "source_declared",
            "source_refs": [semantic_ref(IDENTITY_EVIDENCE)],
        },
        "audiences": [],
        "actors": [
            {
                "canonical_label": "Shift coordinator",
                "source_refs": [semantic_ref(PATH_EVIDENCE)],
            }
        ],
        "entities": [
            {
                "label": "Card",
                "source_refs": [
                    semantic_ref(PATH_EVIDENCE),
                    semantic_ref(STATE_EVIDENCE),
                ],
            },
            {
                "label": "Claim receipt",
                "source_refs": [semantic_ref(PATH_EVIDENCE)],
            },
        ],
        "workflow": [
            {
                "action": "claim one ready card",
                "entity_effects": [
                    {
                        "kind": "changed",
                        "entity_index": 0,
                        "from_state": "ready",
                        "to_state": "claimed",
                        "source_refs": [semantic_ref(STATE_EVIDENCE)],
                        "edge_source_refs": [semantic_ref(STATE_EVIDENCE)],
                    },
                    {
                        "kind": "visible_result",
                        "entity_index": 1,
                        "visible_to": [
                            {
                                "kind": "actor",
                                "index": 0,
                                "source_refs": [semantic_ref(PATH_EVIDENCE)],
                            }
                        ],
                        "source_refs": [semantic_ref(PATH_EVIDENCE)],
                        "edge_source_refs": [semantic_ref(PATH_EVIDENCE)],
                    },
                ],
                "owner_actor_index": 0,
                "source_refs": [semantic_ref(PATH_EVIDENCE)],
            }
        ],
        "dependencies": [
            {
                "label": "Local duty roster",
                "access_mode": "read",
                "source_refs": [semantic_ref(DEPENDENCY_EVIDENCE)],
            }
        ],
        "product_boundaries": [],
        "policy_boundaries": [
            {
                "modalities": ["prohibited"],
                "statement": POLICY_EVIDENCE,
                "source_refs": [semantic_ref(POLICY_EVIDENCE)],
            }
        ],
        "non_material_gaps": [],
        "provenance_only": [],
        "clarification": {
            "required": False,
            "question": "",
            "source_refs": [],
        },
    }


def semantic_intent_packet() -> dict[str, Any]:
    graph = _claim_desk_source_meaning_graph()
    return build_semantic_intent_packet(
        graph,
        prompt=SEMANTIC_PROMPT,
        author_run=_source_meaning_author_run(graph),
    )


def semantic_clarification_packet() -> dict[str, Any]:
    graph = _claim_desk_source_meaning_graph()
    graph["workflow"][0]["entity_effects"] = []
    graph["entities"] = []
    graph["clarification"] = {
        "required": True,
        "question": "Which details must the claim receipt display?",
        "source_refs": [semantic_ref(PATH_EVIDENCE)],
    }
    return build_semantic_intent_packet(
        graph,
        prompt=SEMANTIC_PROMPT,
        author_run=_source_meaning_author_run(graph),
    )


def semantic_intent_with_authority() -> dict[str, Any]:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(), prompt=SEMANTIC_PROMPT
    )
    return {
        **verified.product_facts,
        "product_intent_authority": semantic_intent_authority(
            verified, prompt=SEMANTIC_PROMPT
        ),
    }


def stateless_semantic_intent_packet() -> tuple[dict[str, Any], str]:
    prompt = (
        "Build a signal view for a downstream signal processor. The product presents "
        "a signal chart and signal summary without durable state."
    )
    graph = {
        "version": SEMANTIC_SOURCE_MEANING_GRAPH_VERSION,
        "presentation": {
            "title": "Signal View",
            "status": "working_assumption",
            "source_refs": [],
        },
        "audiences": [
            {
                "kind": "explicit_nonhuman",
                "label": "Downstream signal processor",
                "source_refs": [semantic_ref(prompt)],
            }
        ],
        "actors": [],
        "entities": [
            {
                "label": "Signal chart",
                "source_refs": [semantic_ref(prompt)],
            },
            {
                "label": "Signal summary",
                "source_refs": [semantic_ref(prompt)],
            },
        ],
        "workflow": [
            {
                "action": "present a signal chart and signal summary",
                "entity_effects": [
                    {
                        "kind": "visible_result",
                        "entity_index": 0,
                        "visible_to": [
                            {
                                "kind": "audience",
                                "index": 0,
                                "source_refs": [semantic_ref(prompt)],
                            }
                        ],
                        "source_refs": [semantic_ref(prompt)],
                        "edge_source_refs": [semantic_ref(prompt)],
                    },
                    {
                        "kind": "visible_result",
                        "entity_index": 1,
                        "visible_to": [
                            {
                                "kind": "audience",
                                "index": 0,
                                "source_refs": [semantic_ref(prompt)],
                            }
                        ],
                        "source_refs": [semantic_ref(prompt)],
                        "edge_source_refs": [semantic_ref(prompt)],
                    },
                ],
                "owner_actor_index": None,
                "source_refs": [semantic_ref(prompt)],
            }
        ],
        "dependencies": [],
        "product_boundaries": [],
        "policy_boundaries": [
            {
                "modalities": ["prohibited"],
                "statement": "The product has no durable state.",
                "source_refs": [semantic_ref(prompt)],
            }
        ],
        "non_material_gaps": [],
        "provenance_only": [],
        "clarification": {
            "required": False,
            "question": "",
            "source_refs": [],
        },
    }
    return (
        build_semantic_intent_packet(
            graph,
            prompt=prompt,
            author_run=_source_meaning_author_run(graph),
        ),
        prompt,
    )


__all__ = [
    "AUTHOR_RUN_ID",
    "DEPENDENCY_EVIDENCE",
    "IDENTITY_EVIDENCE",
    "PATH_EVIDENCE",
    "POLICY_EVIDENCE",
    "SEMANTIC_PROMPT",
    "STATE_EVIDENCE",
    "semantic_clarification_packet",
    "semantic_fact",
    "semantic_intent_packet",
    "semantic_intent_with_authority",
    "semantic_ref",
    "semantic_relation",
    "stateless_semantic_intent_packet",
]
