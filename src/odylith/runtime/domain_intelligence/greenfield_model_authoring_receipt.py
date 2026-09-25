"""Receipt projections for admitted Greenfield semantic candidates."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
)


def model_authoring_receipt(
    authored: GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification,
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
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "semantic_model_call_count": authored.semantic_model_call_count,
        "tier": authored.tier,
        "elapsed_seconds": authored.elapsed_seconds,
        "effective_model_window_seconds": authored.effective_model_window_seconds,
        "participant_selection": deepcopy(authored.participant_selection),
        "remaining_candidate_authoring": deepcopy(authored.remaining_candidate_authoring),
        **(
            {
                "candidate_review": deepcopy(authored.candidate_review),
                **(
                    {
                        "candidate_revision": deepcopy(authored.candidate_revision),
                        "rejected_candidate_review": deepcopy(authored.rejected_candidate_review),
                    }
                    if authored.candidate_revision
                    else {}
                ),
            }
            if isinstance(authored, GreenfieldModelAuthoredIntent)
            else {}
        ),
        "consistency_assessment": {
            "status": authored.consistency_status,
            "source_spans": [dict(span) for span in consistency_spans],
        },
    }


def envelope_authoring_observation(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("authoring_origin") == "host_native":
        review = receipt.get("candidate_review")
        review_profile = review.get("model_profile") if isinstance(review, Mapping) else None
        return {
            "origin": "host_native",
            "host_candidate": deepcopy(receipt.get("host_candidate")),
            "candidate_review": deepcopy(review_profile),
        }
    return {
        role: deepcopy(receipt[role]["model_profile"])
        for role in ("participant_selection", "remaining_candidate_authoring")
    }


__all__ = ["envelope_authoring_observation", "model_authoring_receipt"]
