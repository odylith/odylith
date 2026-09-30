"""Write private one-pass host-candidate proof through a parent-granted FD."""

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
GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION = (
    "odylith.greenfield.model-proof-observation.v5"
)


def emit_greenfield_model_proof_observation(
    *,
    evidence_text: str,
    host_candidate: Mapping[str, Any],
    failure: Mapping[str, Any] | None = None,
) -> None:
    """Persist immutable host receipt evidence with zero runtime semantic calls."""

    payload: dict[str, Any] = {
        "version": GREENFIELD_MODEL_PROOF_OBSERVATION_VERSION,
        "authoring_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "request": greenfield_authoring_payload(evidence_text),
        "origin": "host_native",
        "host_candidate": deepcopy(dict(host_candidate)),
        "runtime_semantic_model_call_count": 0,
    }
    if failure is not None:
        payload["failure"] = deepcopy(dict(failure))
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
