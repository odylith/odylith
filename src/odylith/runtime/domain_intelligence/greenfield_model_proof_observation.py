"""Write private Greenfield model proof only through a parent-granted FD."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    greenfield_authoring_payload,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)

GREENFIELD_MODEL_PROOF_FD_ENV = "ODYLITH_GREENFIELD_MODEL_PROOF_FD"
GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION = "odylith.greenfield.model-proof-observation.v4"


def emit_greenfield_model_proof_observation(
    *,
    evidence_text: str,
    semantic_model_call_count: int,
    participant_selection: Mapping[str, Any] | None,
    remaining_candidate_authoring: Mapping[str, Any] | None,
    rejected_candidate: Mapping[str, Any] | None,
    rejected_candidate_review: Mapping[str, Any] | None,
    candidate_revision: Mapping[str, Any] | None,
    joined_candidate: Mapping[str, Any] | None,
    candidate_review: Mapping[str, Any] | None,
    failure: Mapping[str, Any] | None,
    origin: str = "",
    host_candidate: Mapping[str, Any] | None = None,
) -> None:
    """Persist exact private stage evidence without a file path or fallback channel."""

    payload: dict[str, Any] = {
        "version": GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION,
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "request": greenfield_authoring_payload(evidence_text),
        "semantic_model_call_count": semantic_model_call_count,
    }
    if origin:
        payload["origin"] = origin
    for key, value in (
        ("host_candidate", host_candidate),
        ("participant_selection", participant_selection),
        ("remaining_candidate_authoring", remaining_candidate_authoring),
        ("rejected_candidate", rejected_candidate),
        ("rejected_candidate_review", rejected_candidate_review),
        ("candidate_revision", candidate_revision),
        ("candidate_review", candidate_review),
        ("joined_candidate", joined_candidate),
        ("failure", failure),
    ):
        if value is not None:
            payload[key] = deepcopy(dict(value))
    _write_parent_granted_observation(payload)


def _write_parent_granted_observation(payload: Mapping[str, Any]) -> None:
    """Use only the inherited descriptor; absent proof capture remains silent."""

    descriptor_text = str(os.environ.get(GREENFIELD_MODEL_PROOF_FD_ENV) or "").strip()
    if not descriptor_text:
        return
    try:
        descriptor = int(descriptor_text)
    except ValueError as exc:
        raise GreenfieldModelAuthoringError(
            "Greenfield release-proof evidence capture is invalid; no records were created."
        ) from exc
    if descriptor <= 2:
        raise GreenfieldModelAuthoringError(
            "Greenfield release-proof evidence capture is invalid; no records were created."
        )
    encoded = json.dumps(
        dict(payload), sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n"
    written = 0
    try:
        while written < len(encoded):
            count = os.write(descriptor, encoded[written:])
            if count <= 0:
                raise OSError("proof descriptor accepted no bytes")
            written += count
    except OSError as exc:
        raise GreenfieldModelAuthoringError(
            "Greenfield release-proof evidence capture failed; no records were created."
        ) from exc


__all__ = [
    "GREENFIELD_MODEL_PROOF_FD_ENV",
    "GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION",
    "emit_greenfield_model_proof_observation",
]
