"""Admit one host-authored Greenfield candidate without runtime re-authoring.

The host candidate is an untrusted typed hypothesis.  This boundary reuses the
canonical authoring validator and independent candidate reviewer; it does not
repair, revise, parse, or reinterpret the candidate.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import monotonic
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    GreenfieldCandidateClarificationRequired,
    GreenfieldCandidateRejected,
    REFERENCE_PROVENANCE_ROLE_CONTRACT,
    review_greenfield_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_review_custody import (
    candidate_for_pre_review_validation,
    finalize_admitted_review,
    project_reviewed_custody,
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
from odylith.runtime.domain_intelligence.greenfield_model_proof_observation import (
    emit_greenfield_model_proof_observation,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelRuntimeError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)

HOST_CANDIDATE_RECEIPT_VERSION = "odylith.greenfield.host-candidate.v1"
HOST_CANDIDATE_CONTRACT_VERSION = "odylith.greenfield.host-candidate-contract.v31"
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
            (
                "Preserve every source-stated participant, action, visible result, product-governing "
                "constraint, and non-goal. Instructions that govern the supplied source evidence, "
                "fixture or candidate as inputs to this authoring transaction—including their identity, "
                "metadata, handling or exclusion from product copy—are authoring controls, not product "
                "meaning: retain them only in the supplied evidence and do not cite, restate "
                "or paraphrase them as accepted facts, assumptions, components, workstreams, "
                "deliverables, acceptance, verification or exchanges. Do not apply that exclusion to "
                "a requested product workflow that manages evidence, provenance or source identity as "
                "domain data. Classify by the directive's actual governed system and outcome."
            ),
            REFERENCE_PROVENANCE_ROLE_CONTRACT,
            (
                "For every accepted source fact, copy quote and locator context byte-for-byte "
                "from the source; never normalize or rewrite either value. "
                "When the quote occurs once, repeat the quote as context. When the quote occurs "
                "more than once, context must be an exact contiguous source excerpt that occurs "
                "once and contains the selected quote once. Context locates the quote but "
                "contributes no additional meaning."
            ),
            (
                "Each action_quote must preserve the complete source action owned by its actor. "
                "When one source performer explicitly owns alternative verbs that govern separate "
                "outcomes, keep the full joined action phrase in one event instead of selecting "
                "only one branch verb or inventing separate performer actions; a truncated branch "
                "action is not admissible."
            ),
            (
                "Give every event its own distinct exact contiguous source_citation. Split a "
                "source sentence into non-overlapping event clauses even when one actor owns "
                "several actions; never reuse or partially overlap event citations. When the "
                "source expresses inseparable joined actions, preserve the complete joined action "
                "in one event. The independent reviewer owns all accepted component-responsibility "
                "custody."
            ),
            (
                "Keep every accepted operational constraint only in facts.operational_constraints; "
                "the independent reviewer owns its later typed custody and the complete accepted "
                "source precedence relation between existing source-supported events."
            ),
            "Keep accepted source facts separate from assumptions and provisional design decisions.",
            (
                "An authored candidate must bind one source-supported participant, beneficiary, "
                "or explicit product/system task owner; one usable task event; and one source-supported "
                "terminal result event. A product title cannot act as a fabricated user, but a source-"
                "supported product or internal system may own its bound task. Assumptions or provisional "
                "design cannot supply any missing witness part. Treat the audience for a request, brief, "
                "report, proposal, or other authoring deliverable as contextual unless the source "
                "separately states that audience's product participation or benefit; a direct workflow "
                "actor outranks a broader authoring audience. When the source lacks one of those facts, "
                "return clarification_required for first_path instead of authoring a package."
            ),
            (
                "Use exactly one proof authority: when the source identifies both a visible result and "
                "its producing event, cite facts.proof_boundary and supply terminal without a "
                "proof_boundary assumption. A proof_boundary assumption may describe a proposed "
                "checkpoint but cannot make an authored candidate admission-ready."
            ),
            (
                "In provisional_design, propose 4-5 distinct useful components and 4-5 actionable workstreams without "
                "padding. Across component supported_event_orders, cover every source event, "
                "including human actions; support never transfers the actor's work to a component."
            ),
            (
                "For each material risk, preserve its meaning in statement, trigger, mitigation and "
                "verification, then select one or more exact scope_paths already present in the "
                "provisional design graph. Each path binds one event_order to a component_key that "
                "supports it and a workstream_key that owns that component and verifies that event. "
                "Do not separately author component, workstream or event scope; Odylith derives "
                "those ordered unions from the selected paths."
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
    validation_response = deepcopy(canonical_response)
    if canonical_response["result"].get("status") == "authored":
        validation_response["result"] = candidate_for_pre_review_validation(
            canonical_response["result"]
        )
    authored = validate_greenfield_authoring_response(
        validation_response,
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

    review_observation: dict[str, Any] = {}
    try:
        review = review_greenfield_candidate(
            evidence_text=evidence_text,
            candidate=canonical_response["result"],
            profile_id=profile_id,
            source_spans=authored.source_spans,
            provider_factory=review_provider_factory,
            deadline=model_deadline,
            clock=clock,
            observation=review_observation,
        )
    except GreenfieldCandidateRejected as rejection:
        emit_greenfield_model_proof_observation(
            evidence_text=evidence_text,
            semantic_model_call_count=1,
            participant_selection=None,
            remaining_candidate_authoring=None,
            joined_candidate=None,
            candidate_review=rejection.receipt,
            failure=None,
            origin="host_native",
            host_candidate=base_receipt,
        )
        raise
    except GreenfieldCandidateClarificationRequired as clarification:
        emit_greenfield_model_proof_observation(
            evidence_text=evidence_text,
            semantic_model_call_count=1,
            participant_selection=None,
            remaining_candidate_authoring=None,
            joined_candidate=None,
            candidate_review=clarification.receipt,
            failure=None,
            origin="host_native",
            host_candidate=base_receipt,
        )
        return (
            GreenfieldAuthoringClarification(
                required_fields=(clarification.material_dimension,),
                elapsed_seconds=max(0.0, clock() - started),
                tier=authored.tier,
                provider=deepcopy(authored.provider),
                profile_id=authored.profile_id,
                effective_timeout_seconds=authored.effective_timeout_seconds,
                consistency_status="material_ambiguity",
                consistency_source_spans=(),
                clarification_basis="complete_source_missingness",
                effective_model_window_seconds=effective_window,
                candidate_review=deepcopy(dict(clarification.receipt)),
                semantic_model_call_count=1,
            ),
            base_receipt,
        )
    projected_response = deepcopy(canonical_response)
    projected_response["result"] = project_reviewed_custody(
        canonical_response["result"],
        component_custody=review["admission_witness"]["component_custody"],
        source_precedence_custody=review["admission_witness"][
            "source_precedence_custody"
        ],
        constraint_custody=review["admission_witness"]["constraint_custody"],
        evidence_text=evidence_text,
    )
    projected_frozen = _canonical_candidate_bytes(projected_response)
    projected_authored = validate_greenfield_authoring_response(
        projected_response,
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
        reviewer_projected_constraints=True,
    )
    if not isinstance(projected_authored, GreenfieldModelAuthoredIntent):
        raise RuntimeError("Greenfield admitted review produced no final candidate")
    if _canonical_candidate_bytes(projected_response) != projected_frozen:
        raise RuntimeError("Greenfield final validation changed the projected candidate")
    review = finalize_admitted_review(
        review,
        candidate=projected_response["result"],
    )
    emit_greenfield_model_proof_observation(
        evidence_text=evidence_text,
        semantic_model_call_count=1,
        participant_selection=None,
        remaining_candidate_authoring=None,
        joined_candidate=None,
        candidate_review=review,
        failure=None,
        origin="host_native",
        host_candidate=base_receipt,
    )
    if _canonical_candidate_bytes(response) != frozen:
        raise RuntimeError("Greenfield host-candidate review changed the candidate")
    if _canonical_candidate_bytes(canonical_response) != canonical_frozen:
        raise RuntimeError("Greenfield host-candidate review changed the canonical projection")
    return (
        replace(
            projected_authored,
            elapsed_seconds=max(0.0, clock() - started),
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
