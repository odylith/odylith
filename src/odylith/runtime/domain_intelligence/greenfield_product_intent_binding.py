"""Parser-free Product Intent binding for graph-native transactions."""

from __future__ import annotations

from collections.abc import Mapping
import copy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_intent_product_facts,
)


PRODUCT_FACTS_HASH_KEY = "product_facts_sha256"


def require_product_intent_authority(authority: Mapping[str, Any]) -> None:
    """Verify the source-cited graph authority."""

    try:
        require_product_intent_authority_structure(authority)
    except ValueError as error:
        raise ValueError(
            str(error).replace("sealed Product Intent authority", "confirmed Product Intent authority")
        ) from error


def require_authoritative_intent_binding(
    intent: Mapping[str, Any], authority: Mapping[str, Any]
) -> None:
    """Require proposal facts to equal the facts sealed by their authority."""

    require_product_intent_authority(authority)
    expected = _semantic_product_facts(authority)
    if any(intent.get(key) != value for key, value in expected.items()):
        raise ValueError(
            "ProductCreateTransaction proposal facts do not match its sealed Product Intent authority; "
            "rebuild the transaction before showing CONFIRM"
        )


def rebind_authoritative_product_facts(
    intent: Mapping[str, Any],
    *,
    authoritative_intent: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Restore exact sealed facts after projection adds non-authoritative metadata."""

    require_product_intent_authority(authority)
    expected = _semantic_product_facts(authority)
    if any(authoritative_intent.get(key) != value for key, value in expected.items()):
        raise ValueError("authoritative Product Intent differs from its source-cited Semantic Intent graph")
    rebound = copy.deepcopy(dict(intent))
    rebound.update(copy.deepcopy(expected))
    return rebound


def _semantic_product_facts(authority: Mapping[str, Any]) -> dict[str, Any]:
    graph = authority.get("semantic_intent")
    if not isinstance(graph, Mapping):
        raise ValueError("confirmed Product Intent authority lacks Semantic Intent")
    return semantic_intent_product_facts(graph)


__all__ = [
    "PRODUCT_FACTS_HASH_KEY",
    "PRODUCT_INTENT_AUTHORITY_KEY",
    "rebind_authoritative_product_facts",
    "require_authoritative_intent_binding",
    "require_product_intent_authority",
]
