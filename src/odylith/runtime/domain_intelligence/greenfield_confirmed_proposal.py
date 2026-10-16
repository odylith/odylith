"""Parser-free API for governed Greenfield proposal construction.

Supported proposals are projected only from verified typed relations.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def sealed_authored_projection(proposal: Mapping[str, Any]) -> bool:
    """Derive authoredness from sealed relation custody, never a caller flag."""

    from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
        AUTHORED_PROJECTION_ORIGIN,
        require_relation_authority_parity,
    )
    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        PRODUCT_INTENT_AUTHORITY_KEY,
    )

    intent = proposal.get("intent")
    proposal_envelope = isinstance(intent, Mapping)
    if not proposal_envelope:
        intent = proposal
    authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(authority, Mapping):
        authority = intent.get(PRODUCT_INTENT_AUTHORITY_KEY)
    marker = proposal.get("projection_origin")
    if not isinstance(authority, Mapping):
        if marker == AUTHORED_PROJECTION_ORIGIN:
            raise ValueError("model-authored Greenfield projection is missing sealed relation authority")
        return False
    authored = bool(require_relation_authority_parity(intent, authority))
    if (proposal_envelope or marker is not None) and (
        marker == AUTHORED_PROJECTION_ORIGIN
    ) != authored:
        raise ValueError("Greenfield projection origin does not match sealed relation authority")
    return authored


def build_confirmed_greenfield_proposal(
    *,
    prompt: str,
    title: str,
    observed_source: Mapping[str, Any],
    release_selector: str = "",
    confirmed_intent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project accepted intent through its sealed semantic contract."""

    if not isinstance(confirmed_intent, Mapping):
        raise ValueError("confirmed greenfield proposal requires accepted Product Intent Confirmation data.")
    if not sealed_authored_projection(confirmed_intent):
        raise ValueError(
            "confirmed Greenfield proposal requires sealed model-authored relation authority"
        )
    from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
        build_authored_greenfield_proposal,
    )

    return build_authored_greenfield_proposal(
        observed_source=observed_source,
        release_selector=release_selector,
        confirmed_intent=confirmed_intent,
    )


__all__ = ["build_confirmed_greenfield_proposal", "sealed_authored_projection"]
