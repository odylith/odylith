"""Admit one host-authored Greenfield candidate without runtime re-authoring.

The host candidate is an untrusted typed hypothesis.  This boundary reuses the
canonical v68 validator and independent candidate reviewer; it does not repair,
revise, parse, or reinterpret the candidate.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from time import monotonic
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    review_greenfield_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
    canonical_greenfield_host_candidate,
    greenfield_host_candidate_schema,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldAuthoringClarification,
    GreenfieldModelAuthoredIntent,
    greenfield_authoring_payload,
    validate_greenfield_authoring_response,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelRuntimeError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)

HOST_CANDIDATE_RECEIPT_VERSION = "odylith.greenfield.host-candidate.v1"
HOST_CANDIDATE_CONTRACT_VERSION = "odylith.greenfield.host-candidate-contract.v17"
MAX_HOST_CANDIDATE_BYTES = 512 * 1024


def greenfield_host_candidate_contract(evidence_text: str) -> dict[str, Any]:
    """Return the public host reasoning contract for one exact evidence source."""

    return {
        "version": HOST_CANDIDATE_CONTRACT_VERSION,
        "candidate_version": HOST_CANDIDATE_FORMAT_VERSION,
        "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "task": (
            "Reason over the complete source and return exactly one JSON value matching "
            "candidate_schema. The candidate is an untrusted hypothesis; Odylith will "
            "revalidate every citation and run an independent semantic review."
        ),
        "requirements": [
            "Preserve every source-stated participant, action, visible result, constraint, and non-goal.",
            (
                "For every accepted source fact, supply its exact quote and locator context. "
                "When the quote occurs once, repeat the quote as context. When the quote occurs "
                "more than once, context must be an exact contiguous source excerpt that occurs "
                "once and contains the selected quote once. Context locates the quote but "
                "contributes no additional meaning."
            ),
            (
                "Bind every explicit ordering constraint to its source events. Different "
                "constraints may support the same directed edge; never repeat an identical "
                "before-event, after-event, and constraint-index binding."
            ),
            (
                "A typed event whose actor_fact selects title or internal_systems must supply one "
                "responsibility_citation that is an exact subspan of source_citation at the same "
                "source location and contains only that product-owned clause; use null for human "
                "or external events. When an event source citation contains several actors "
                "or product owners, give each differently owned event its own exact contiguous "
                "source clause; only events with the same product owner may share one source "
                "citation. Select the responsibility-specific clause separately. Do not repeat "
                "that exact citation in components.additional_"
                "responsibilities. Identity is exact: related wording, a shared target, or the "
                "same owner is still a separate responsibility. Put every other explicit source-"
                "stated product or component responsibility under its typed owner_fact there."
            ),
            "Keep accepted source facts separate from assumptions and provisional design decisions.",
            (
                "Use exactly one proof authority: when the source identifies both a visible result and "
                "its producing event, cite facts.proof_boundary and supply terminal without a "
                "proof_boundary assumption; otherwise set both facts.proof_boundary and terminal to "
                "null and supply exactly one conservative proof_boundary assumption."
            ),
            (
                "Propose 4-5 distinct useful components and 4-5 actionable workstreams without "
                "padding. Across component supported_event_orders, cover every source event, "
                "including human actions; support never transfers the actor's work to a component."
            ),
            "Return one material clarification when the usable path or product boundary is genuinely unresolved.",
            "Do not add a parser, regex extraction pass, repair attempt, fallback candidate, or hidden source interpretation.",
        ],
        "request": greenfield_authoring_payload(evidence_text),
        "candidate_schema": greenfield_host_candidate_schema(),
    }


def load_greenfield_host_candidate_file(path: Path) -> dict[str, Any]:
    """Load one bounded JSON candidate without granting it source authority."""

    candidate_path = Path(path).expanduser()
    try:
        with candidate_path.open("rb") as handle:
            payload = handle.read(MAX_HOST_CANDIDATE_BYTES + 1)
    except OSError as exc:
        raise RuntimeError("environment/IO failure while reading host candidate") from exc
    if len(payload) > MAX_HOST_CANDIDATE_BYTES:
        raise ValueError("Greenfield host candidate exceeds its declared input bound")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Greenfield host candidate must be valid UTF-8 JSON") from exc
    if not isinstance(value, Mapping):
        raise TypeError("Greenfield host candidate must be a JSON object")
    return dict(value)


def admit_greenfield_host_candidate(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
    profile_id: str = STANDARD_PROFILE_ID,
    review_provider_factory: Callable[[], Any] | None,
    deadline: float | None = None,
    clock: Callable[[], float] = monotonic,
) -> tuple[
    GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification,
    dict[str, Any],
]:
    """Validate and independently review one immutable host candidate."""

    profile = get_greenfield_model_profile(profile_id)
    started = clock()
    model_deadline = started + profile.model_timeout_seconds
    if deadline is not None:
        if not math.isfinite(deadline):
            raise ValueError("Greenfield received an invalid host-candidate deadline")
        model_deadline = min(model_deadline, deadline)
    effective_window = model_deadline - started
    if effective_window < 1.0:
        raise GreenfieldModelRuntimeError("timeout")

    frozen = _canonical_candidate_bytes(response)
    candidate_sha256 = hashlib.sha256(frozen).hexdigest()
    canonical_response = canonical_greenfield_host_candidate(
        response,
        evidence_text=evidence_text,
    )
    canonical_frozen = _canonical_candidate_bytes(canonical_response)
    authored = validate_greenfield_authoring_response(
        canonical_response,
        evidence_text=evidence_text,
        elapsed_seconds=0.0,
        provider={
            "provider": "host-native",
            "model": "outside-runtime-custody",
            "reasoning_effort": "not-observed",
        },
        profile_id=profile_id,
        effective_timeout_seconds=effective_window,
        semantic_model_call_count=0,
        allow_zero_semantic_calls=True,
        event_citations_are_event_owned=True,
    )
    if _canonical_candidate_bytes(response) != frozen:
        raise RuntimeError("Greenfield host-candidate validation changed the candidate")
    if _canonical_candidate_bytes(canonical_response) != canonical_frozen:
        raise RuntimeError("Greenfield host-candidate validation changed the canonical projection")

    base_receipt = {
        "version": HOST_CANDIDATE_RECEIPT_VERSION,
        "contract_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "source_sha256": hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
        "candidate_sha256": candidate_sha256,
    }
    if isinstance(authored, GreenfieldAuthoringClarification):
        return authored, base_receipt

    review = review_greenfield_candidate(
        evidence_text=evidence_text,
        candidate=canonical_response["result"],
        profile_id=profile_id,
        source_spans=authored.source_spans,
        provider_factory=review_provider_factory,
        deadline=model_deadline,
        clock=clock,
        observation={},
    )
    if _canonical_candidate_bytes(response) != frozen:
        raise RuntimeError("Greenfield host-candidate review changed the candidate")
    if _canonical_candidate_bytes(canonical_response) != canonical_frozen:
        raise RuntimeError("Greenfield host-candidate review changed the canonical projection")
    return (
        GreenfieldModelAuthoredIntent(
            intent=deepcopy(authored.intent),
            first_path_relations=deepcopy(authored.first_path_relations),
            first_path_context_relations=deepcopy(
                authored.first_path_context_relations
            ),
            component_responsibility_relations=deepcopy(
                authored.component_responsibility_relations
            ),
            atomic_claims=deepcopy(authored.atomic_claims),
            source_spans=deepcopy(authored.source_spans),
            source_sha256=authored.source_sha256,
            provisional_design=deepcopy(authored.provisional_design),
            source_precedence=deepcopy(authored.source_precedence),
            elapsed_seconds=max(0.0, clock() - started),
            tier=authored.tier,
            provider=deepcopy(authored.provider),
            profile_id=authored.profile_id,
            effective_timeout_seconds=authored.effective_timeout_seconds,
            consistency_status=authored.consistency_status,
            effective_model_window_seconds=effective_window,
            semantic_model_call_count=1,
            candidate_review=deepcopy(review),
        ),
        base_receipt,
    )


def _canonical_candidate_bytes(response: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            dict(response),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Greenfield host candidate must be canonical JSON data") from exc


__all__ = [
    "HOST_CANDIDATE_CONTRACT_VERSION",
    "HOST_CANDIDATE_RECEIPT_VERSION",
    "MAX_HOST_CANDIDATE_BYTES",
    "admit_greenfield_host_candidate",
    "greenfield_host_candidate_contract",
    "load_greenfield_host_candidate_file",
]
