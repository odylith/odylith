"""Materialize one immutable host-native Greenfield candidate."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from time import monotonic
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_material_clarification import (
    material_clarification_for_fields,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    GreenfieldPreparedAuthoringEvidence,
    prepare_model_authoring_evidence,
    stage_validated_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)


def materialize_host_authored_intent(
    *,
    prompt: str,
    repo_root: Path,
    host_candidate: Mapping[str, Any],
    review_provider_factory: Callable[[], Any] | None,
    edit_evidence: str = "",
    authoring_profile_id: str = STANDARD_PROFILE_ID,
    source_language: str = "en",
    prepared_evidence: GreenfieldPreparedAuthoringEvidence | None = None,
    authoring_receipt: dict[str, Any] | None = None,
    authoring_deadline: float | None = None,
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Stage one immutable host candidate after validation and review."""

    prepared = prepared_evidence or prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
        source_language=source_language,
    )
    if prepared.prompt != prompt:
        raise ValueError("prepared Greenfield evidence does not match the operator prompt")
    authored, host_receipt = admit_greenfield_host_candidate(
        host_candidate,
        evidence_text=prepared.evidence_source,
        profile_id=authoring_profile_id,
        review_provider_factory=review_provider_factory,
        deadline=authoring_deadline,
        clock=clock,
    )
    receipt = _host_authoring_receipt(authored, host_receipt=host_receipt)
    if isinstance(authored, GreenfieldAuthoringClarification):
        clarification = material_clarification_for_fields(
            authored.required_fields,
            consistency_status=authored.consistency_status,
        )
        if authoring_receipt is not None:
            authoring_receipt.clear()
            authoring_receipt.update(receipt)
        raise GreenfieldClarificationRequired(
            clarification.question,
            required_fields=clarification.required_fields,
            authoring_receipt=receipt,
        )
    return stage_validated_authored_intent(
        prompt=prompt,
        repo_root=repo_root,
        prepared=prepared,
        authored=authored,
        receipt=receipt,
        authoring_receipt=authoring_receipt,
        clarification_error=GreenfieldClarificationRequired,
    )


def _host_authoring_receipt(
    authored: GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification,
    *,
    host_receipt: Mapping[str, Any],
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
        "host_candidate": deepcopy(dict(host_receipt)),
        **(
            {"candidate_review": deepcopy(authored.candidate_review)}
            if authored.candidate_review
            else {}
        ),
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


__all__ = ["materialize_host_authored_intent"]
