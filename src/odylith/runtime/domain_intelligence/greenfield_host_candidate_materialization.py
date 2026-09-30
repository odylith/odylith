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
    GreenfieldAuthoringClarification,
)
from odylith.runtime.domain_intelligence.greenfield_model_authoring_receipt import (
    host_authoring_receipt,
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
    edit_evidence: str = "",
    authoring_profile_id: str = STANDARD_PROFILE_ID,
    source_language: str = "en",
    prepared_evidence: GreenfieldPreparedAuthoringEvidence | None = None,
    authoring_receipt: dict[str, Any] | None = None,
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Stage one immutable host candidate after deterministic validation."""

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
        clock=clock,
    )
    receipt = host_authoring_receipt(authored, host_candidate=host_receipt)
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

__all__ = ["materialize_host_authored_intent"]
