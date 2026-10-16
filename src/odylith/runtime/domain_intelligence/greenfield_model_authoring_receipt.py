"""Receipt projections for one complete host-authored Greenfield candidate."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
)


def host_authoring_receipt(
    authored: GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification,
    *,
    host_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    consistency_spans = (
        authored.consistency_source_spans
        if isinstance(authored, GreenfieldAuthoringClarification)
        else tuple(
            span
            for span in authored.source_spans
            if str(span.get("span_id") or "").startswith("authoring:consistency:")
        )
    )
    return {
        "authoring_origin": "host_native",
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "runtime_semantic_model_call_count": authored.semantic_model_call_count,
        "tier": authored.tier,
        "elapsed_seconds": authored.elapsed_seconds,
        "effective_model_window_seconds": authored.effective_model_window_seconds,
        "host_candidate": deepcopy(dict(host_candidate)),
        "consistency_assessment": {
            "status": authored.consistency_status,
            "source_spans": [dict(span) for span in consistency_spans],
            **(
                {"basis": authored.clarification_basis}
                if isinstance(authored, GreenfieldAuthoringClarification)
                and authored.clarification_basis
                else {}
            ),
        },
    }


def envelope_authoring_observation(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "origin": "host_native",
        "host_candidate": deepcopy(receipt.get("host_candidate")),
        "runtime_semantic_model_call_count": receipt.get(
            "runtime_semantic_model_call_count"
        ),
    }


__all__ = ["envelope_authoring_observation", "host_authoring_receipt"]
