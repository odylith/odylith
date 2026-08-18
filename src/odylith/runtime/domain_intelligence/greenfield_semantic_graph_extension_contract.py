"""Parser-free contract for node-owned Semantic Intent graph extensions."""

from __future__ import annotations

from typing import Any


SEMANTIC_GRAPH_EXTENSION_VERSION = "odylith.greenfield.semantic-graph-extension.v2"
SEMANTIC_GRAPH_EXTENSION_OUTGOING_EDGE_KINDS = (
    "depends_on",
    "implements",
    "constrained_by",
    "excludes",
)


def semantic_graph_extension_contract() -> dict[str, Any]:
    """Expose the node-owned boundary that the author schema enforces."""

    return {
        "version": SEMANTIC_GRAPH_EXTENSION_VERSION,
        "node_ownership": (
            "each bounded fact is authored once; only bounded internal-system nodes "
            "may own outgoing architecture edges"
        ),
        "outgoing_edges": {
            kind: "subject_is_the_enclosing_internal_system_fact"
            for kind in SEMANTIC_GRAPH_EXTENSION_OUTGOING_EDGE_KINDS
        },
        "incoming_changes": (
            "only a bounded state node may receive a typed change edge from a source workflow"
        ),
        "deterministic_projection": [
            "relation_kind_from_edge_collection",
            "outgoing_subject_from_enclosing_node",
            "incoming_change_object_from_enclosing_state_node",
            "bounded_interpretation_custody",
        ],
        "forbidden": [
            "top_level_relation_list",
            "author_supplied_outgoing_subject",
            "author_supplied_relation_kind",
            "author_supplied_relation_custody",
        ],
    }


__all__ = [
    "SEMANTIC_GRAPH_EXTENSION_OUTGOING_EDGE_KINDS",
    "SEMANTIC_GRAPH_EXTENSION_VERSION",
    "semantic_graph_extension_contract",
]
