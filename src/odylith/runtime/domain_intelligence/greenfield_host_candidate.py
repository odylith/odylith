"""Admit and seal one complete host-authored Greenfield candidate.

The host candidate is an untrusted typed hypothesis. This boundary canonicalizes
source locators and runs deterministic validation once. It never invokes a model,
provider, reviewer, repair, retry, or fallback after candidate receipt.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from time import monotonic
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
    HOST_SOURCE_DUTY_BINDING_FIELD,
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
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_model_proof_observation import (
    emit_greenfield_model_proof_observation,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_invariants import (
    REFERENCE_PROVENANCE_ROLE_CONTRACT,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    HOST_SOURCE_DUTY_BINDING_VERSION,
    project_greenfield_source_event_catalog,
    validate_greenfield_source_duty_binding,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
    greenfield_compact_source_duty_ledger_schema,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    verify_greenfield_source_duty_ledger_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import greenfield_edit_preservation_view
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    compact_source_duty_view,
)
from odylith.runtime.domain_intelligence.greenfield_authority_gate import (
    validate_greenfield_authority_gate,
)

HOST_CANDIDATE_RECEIPT_VERSION = "odylith.greenfield.host-candidate.v7"
HOST_CANDIDATE_CONTRACT_VERSION = "odylith.greenfield.host-candidate-contract.v57"
PASSIVE_HOST_CANDIDATE_CONTRACT_VERSIONS = (
    "odylith.greenfield.host-candidate-contract.v56",
    "odylith.greenfield.host-candidate-contract.v55",
    "odylith.greenfield.host-candidate-contract.v54",
    "odylith.greenfield.host-candidate-contract.v53",
    "odylith.greenfield.host-candidate-contract.v52",
    "odylith.greenfield.host-candidate-contract.v51",
    "odylith.greenfield.host-candidate-contract.v50",
    "odylith.greenfield.host-candidate-contract.v49",
)
PREVIOUS_HOST_CANDIDATE_CONTRACT_VERSION = "odylith.greenfield.host-candidate-contract.v50"
LEGACY_HOST_CANDIDATE_CONTRACT_VERSION = "odylith.greenfield.host-candidate-contract.v49"
HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION = "odylith.greenfield.host-candidate-authoring-transport.v4"
MAX_HOST_CANDIDATE_BYTES = 512 * 1024


def greenfield_host_candidate_contract(
    evidence_text: str, *, edit_preservation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the public host reasoning contract for one exact evidence source."""

    return {
        "version": HOST_CANDIDATE_CONTRACT_VERSION,
        "candidate_version": HOST_CANDIDATE_FORMAT_VERSION,
        "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "task": (
            "After an admitted authority gate, source-duty preflight, one accepted "
            "source-only decision set, and accepted source-duty ledger receipt, reason over "
            "the complete source and return exactly one JSON value matching the supplied "
            "candidate response JSON Schema. The ledger owns source-duty roles and passive lifecycle "
            "meaning; this candidate binds those duties to one proposed product design. "
            "It remains an untrusted hypothesis; Odylith will deterministically revalidate its exact "
            "citations, typed relations, invariants, and hashes without another semantic call. "
            "Return candidate JSON only; do not call a CLI, read or write files, or run another "
            "source-duty verifier pass. "
            "Emit compact JSON with no indentation or optional whitespace outside strings."
        ),
        "requirements": [
            (
                "The external controller has already inventoried source duties, run structural "
                "preflight, obtained one source-only decision per claim and a source-wide "
                "completeness verdict, and checked the accepted receipt. Do not repeat those "
                "steps, call a CLI, or read or write files. Keep first-path human "
                "actions, supporting human actions, system duties, state fields, passive off-path "
                "transitions, guards, boundaries, proof duties, and evidence controls distinct. "
                "For each transition effect, reuse exactly the governed-object and field labels "
                "of its cited state-field duty so field binding stays unambiguous. "
                "Each accepted source action owns one normalized action, target, statement, "
                "exact event_ref, actor_ref, and role_refs. A joined clause "
                "may own several distinct action atoms with the same complete event_ref. "
                "The accepted ledger owns action meaning and role-local Product Intent text; "
                "first-path text must not include supporting human or system actions. "
                "Every source reference must be exact "
                "quote/context evidence. Stop on a material "
                "clarification before candidate authoring. The accepted ledger is source-role "
                "authority; this candidate may only bind its IDs, never redefine their meaning."
            ),
            (
                "The frozen source_event_catalog owns every accepted action's event ID and actor address. "
                "The proposed first_run must contain every bound first-path event and "
                "exactly its transitive prerequisites from the cited source_precedence graph. "
                "Keep the first-path events as an ordered subsequence in ledger order, and "
                "place every prerequisite before its dependent event. Supporting human and "
                "system prerequisites retain their source roles; exclude every unrelated "
                "supporting or system duty. Recurring_invariant duties remain supported lifecycle safeguards and "
                "cannot be selected as one-time first_run actions, even via a candidate precedence edge. "
                "Every unchanged lifecycle duty must retain its prior exact component_key/workstream_key pair; "
                "only changed duties with affirmative exact correction authorization may move. "
                "Event IDs are storage identifiers, never temporal edges. "
                "Do not emit events or action-duty remapping tables. Bind every passive off-path transition "
                "and its effects to governed state fields and owned design components without "
                "inventing an actor event."
            ),
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
                "The candidate must not author event IDs, citations, actors, actions, targets or "
                "action binding tables. Reference only frozen source_event_catalog IDs in design, "
                "first_run, terminal and cited source_precedence. Two actions "
                "in one joined clause remain two atoms and may share the same complete event_ref, "
                "while the accepted ledger statement carries distinct role-local meaning. "
                "The catalog inserts all performing source identities before supplemental facts. "
                "Keep source-supported nonperforming beneficiaries and dependencies in the facts arrays. "
                "Product identity is independently verified in the source ledger and inserted by the compiler; "
                "do not emit facts.title or select a title as an actor. "
                "Never narrow a cited event to an inherited fragment. Odylith derives each "
                "accepted product responsibility from its verified action duty and exact actor; "
                "do not author independent component responsibility citations."
            ),
            (
                "Keep every accepted operational constraint in facts.operational_constraints and "
                "supply the complete source_precedence relation between existing source-supported "
                "events. Passive or unowned timing creates no edge. Bind every verified guard, "
                "boundary and proof duty to its existing lifecycle component/workstream allocation. "
                "Preserve its complete meaning and references independently of action responsibilities."
            ),
            "Keep accepted source facts separate from assumptions and provisional design decisions.",
            (
                "Author provisional_design.project_summary in this same candidate: one or two concise "
                "sentences, at most 600 characters, directly describing the product and outcome. "
                "Do not begin with an imperative such as Propose an or recite actor inventory. Explain who it "
                "serves, and its source-supported value or visible outcome. Use only supplied source "
                "support and clearly proposed scope. Do not substitute a first-path workflow recital, "
                "invent implementation, actors, benefits or commitments, promote assumptions to "
                "accepted facts, or include host/model jargon. This is proposed narrative, not an "
                "accepted source fact or a substitute for any source-duty or proof obligation."
            ),
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
        "source_ledger": {
            **({"edit_preservation": deepcopy(dict(edit_preservation))}
               if edit_preservation is not None else {}),
            "task": (
                "Inventory only source-stated duties and evidence controls from the complete "
                "untrusted evidence. Independently identify the product requested by the operator in "
                "product_identity, using one exact source_ref and basis explicit_name or product_description. "
                "A useful source-cited descriptive identity is required when the description has no formal name. "
                "Do not use a generic product pronoun, background library, incidental heading or authority. "
                "Identity alone is not an action or performer. Named internal components belong to internal_systems. "
                "Use product_wide for an exact actor_ref mention affirmatively denoting the requested product "
                "as a whole, independently of product_identity; generic or competing unresolved referents "
                "require clarification. Never create an internal-system component for a whole-product pronoun. "
                "For each system duty select execution_kind discrete_action for one concrete occurrence or "
                "recurring_invariant for every applicable trigger. Citation overlap does not establish recurrence. For EDIT, extract identity afresh from the complete current source and "
                "correction; prior_identity is a preservation checklist, never a copied current citation. "
                "Before returning the inventory, account for every material source duty across the "
                "complete evidence in source order: actions and their performers, governed state "
                "fields, off-path transitions and each effect, conditional guards, boundaries, and "
                "proof obligations. Preserve their conditions, timing, scope, and required "
                "consequences. When the evidence includes an explicit operator EDIT, retain earlier "
                "duties except where that correction explicitly changes or removes them, and "
                "incorporate each added or refined duty. A statement that earlier requirements remain "
                "in force does not replace those requirements in the inventory. Prior lifecycle duties "
                "in edit_preservation.prior_lifecycle are a coverage checklist when present; "
                "compare them against the explicit correction before authoring current typed rows. "
                "Never copy historical truth or let it override the correction. Distinct obligations "
                "in one clause may belong to different typed sections and may reuse the same citation; "
                "do not collapse an action, its governing condition, or its required evidence into one "
                "incomplete meaning. Represent each obligation once in its appropriate existing "
                "section without duplicating an action atom, inventing a performer, or promoting "
                "reference-only context into product authority. "
                "Return exactly one compact JSON value matching "
                "source_ledger_schema, with no optional whitespace outside strings. Put each "
                "distinct source citation once in citations with a short stable id, q as the "
                "exact source quote, and c as an exact source context containing q; reuse that "
                "id in every row field that cites the same quote and context. The compiler "
                "checks every bank citation against the complete source and removes unused "
                "valid bank storage without changing any material duty. "
                "Set c to q when q occurs once; for a repeated q, extend c with nearby "
                "verbatim source text until the excerpt occurs once. c must be a contiguous "
                "source excerpt containing q, never a heading "
                "label or a description of its location. Each action row owns one normalized "
                "statement, action, and target, plus exact event_ref, actor_ref, and role_refs. "
                "action is nonblank and must be an exact substring of statement; target is "
                "empty or an exact substring of statement. Those substrings locate projection "
                "text only; the independent verifier judges their source meaning. Cite the "
                "complete event context supporting that actor/action/target meaning; inherited "
                "verbs may be normalized without inventing source microcitations. actor_ref "
                "must cite only ONE source-owned performer identity, excluding whole action "
                "sentences, extra performers, and whole duty or paragraph context. Its exact "
                "quote must be a proper literal substring of statement. Retain the identity "
                "quote when normalizing pronouns or inherited verbs; actor_ref may come from "
                "explicit role context. Reuse one canonical actor citation across that actor's "
                "actions and supporting duties. Repeated labels at distinct occurrences do not "
                "declare equivalence. Missing or uncertain canonical identity requires clarification. Literal containment proves "
                "custody only; the existing source-only verifier judges identity atomicity "
                "and performer entailment. role_refs supply nonempty exact source contexts "
                "supporting its typed duty role. actor_ref already owns the exact source "
                "identity occurrence; the compiler includes it first among role references. "
                "source_refs contains only extra support; the compiler derives the event "
                "support. Do not repeat event_ref or actor_ref as aliases. Distinct actions may "
                "share an event, but do not duplicate an atom under another section or "
                "redundant statement. first_path_actions carries performer_role and observable_result. "
                "system_duties also carries performer_role, restricted to internal_system, "
                "or external_system; supporting_human_actions always owns human_actor. "
                "The same source-only verifier must affirm each exact performer kind. "
                "Declare each state field once per exact state_object and "
                "field label. Every off-path effect must reuse that canonical field label "
                "exactly and its transition governed_object must equal the field's state_object. "
                "Several ordered effects may reference one parent field; preserve their distinct "
                "change and observable_check values without renaming the parent field. "
                "Do not call a CLI, read or write files, or produce a "
                "decision set or receipt. If a material duty is unresolved, return the schema's "
                "clarification_required result. The external controller performs structural "
                "preflight, obtains one source-only verifier decision set covering every claim "
                "and source-wide completeness, and checks the accepted receipt before candidate "
                "authoring. Do not author a candidate."
            ),
            "source_ledger_schema": greenfield_compact_source_duty_ledger_schema(),
        },
        "candidate_schema": greenfield_host_candidate_schema(),
    }


def greenfield_host_candidate_authoring_request(
    contract: Mapping[str, Any],
    *,
    source_duty_receipt: Mapping[str, Any],
    authority_admission: Mapping[str, Any],
) -> dict[str, Any]:
    """Present accepted duties losslessly, leaving full admission receipts external."""

    request = contract.get("request")
    source = request.get("evidence") if isinstance(request, Mapping) else None
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Greenfield candidate authoring requires the complete authority source")
    edit_preservation = contract.get("source_ledger", {}).get("edit_preservation")
    if source_duty_receipt.get("edit_preservation") != edit_preservation:
        raise ValueError("Greenfield candidate source duties have a different EDIT baseline")
    receipt = verify_greenfield_source_duty_ledger_receipt(
        source_duty_receipt, evidence_text=source,
        edit_preservation=edit_preservation,
        allow_legacy_edit=False,
    )
    if receipt["ledger"]["status"] != "inventory":
        raise ValueError("Greenfield candidate authoring requires an accepted inventory")
    if (not isinstance(authority_admission, Mapping)
            or set(authority_admission) != {"mode", "gate"}
            or authority_admission["mode"] != "authority_admitted"):
        raise ValueError("Greenfield candidate authoring requires authority admission")
    gate = validate_greenfield_authority_gate(
        authority_admission["gate"], evidence_source=source,
    )
    if gate["decision"] != "admit":
        raise ValueError("Greenfield candidate authoring requires an admitted authority gate")
    retained_fields = (
        "version", "candidate_version", "canonical_version", "task", "requirements",
        "request",
    )
    if not set(retained_fields) <= set(contract) or not isinstance(
        contract.get("candidate_schema"), Mapping
    ):
        raise ValueError("Greenfield candidate authoring contract is incomplete")
    if (contract["version"] != HOST_CANDIDATE_CONTRACT_VERSION
            or contract["candidate_version"] != HOST_CANDIDATE_FORMAT_VERSION
            or contract["canonical_version"] != GREENFIELD_INTENT_AUTHORING_VERSION
            or contract["candidate_schema"] != greenfield_host_candidate_schema()):
        raise ValueError("Greenfield candidate authoring contract version or schema is invalid")
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    inventory = compact_source_duty_view(receipt["ledger"])
    duties = {row["id"]: row for section in (
        "first_path_actions", "supporting_human_actions", "system_duties",
    ) for row in inventory[section]}
    return {
        **{key: deepcopy(contract[key]) for key in retained_fields},
        "transport_version": HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
        "accepted_source_duty_inventory": inventory,
        **({"edit_preservation": greenfield_edit_preservation_view(receipt["edit_preservation"])}
           if "edit_preservation" in receipt else {}),
        "source_event_catalog": {
            "performers": [{"field": actor["field"], "row": actor["row"],
                            "actor_ref": duties[actor["duty_id"]]["actor_ref"]}
                           for actor in catalog["performers"]],
            "events": [{key: event[key] for key in (
                "event_order", "binding_role", "duty_id", "actor_fact",
            )} for event in catalog["events"]],
        },
        "source_duty_custody": {
            key: receipt[key] for key in (
                "version", "source_sha256", "ledger_sha256", "verifier_task_sha256",
                "decision_set_sha256",
            )
        },
        "authority_admission": {"mode": "authority_admitted", "gate": gate},
        "citation_resolution": (
            "accepted_source_duty_inventory is the lossless accepted ledger with citations "
            "interned by ID. Resolve each citation ID through citations: q is its exact quote "
            "and c its exact source context. source_event_catalog freezes every performer "
            "and event before candidate authoring; performer actor_ref IDs address this same "
            "citation bank. Do not redefine its identities or event IDs. Preserve all duty IDs, row order, roles, and evidence "
            "controls; bind source_duty_binding hashes from source_duty_custody. The external "
            "controller retains the complete verified receipt. Do not reverify source duties."
        ),
    }


def load_greenfield_host_candidate_file(path: Path) -> dict[str, Any]:
    """Load one bounded JSON candidate without granting it source authority."""

    candidate_path = Path(path).expanduser()
    try:
        with candidate_path.open("rb") as handle:
            payload = handle.read(MAX_HOST_CANDIDATE_BYTES + 1)
    except OSError as exc:
        raise RuntimeError(
            "environment/IO failure while reading host candidate"
        ) from exc
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
    source_duty_receipt: Mapping[str, Any],
    profile_id: str = STANDARD_PROFILE_ID,
    clock: Callable[[], float] = monotonic,
) -> tuple[
    GreenfieldModelAuthoredIntent | GreenfieldAuthoringClarification,
    dict[str, Any],
]:
    """Canonicalize, validate once, and seal one immutable host candidate."""

    profile = get_greenfield_model_profile(profile_id)
    started = clock()
    verified_ledger = verify_greenfield_source_duty_ledger_receipt(
        source_duty_receipt, evidence_text=evidence_text, allow_legacy_edit=False
    )
    if verified_ledger["ledger"]["status"] != "inventory":
        raise ValueError("Greenfield source duties require one material clarification")
    raw_frozen = _canonical_candidate_bytes(response)
    raw_candidate_sha256 = hashlib.sha256(raw_frozen).hexdigest()
    raw_result = response.get("result")
    binding: dict[str, Any] | None = None
    if isinstance(raw_result, Mapping) and raw_result.get("status") == "authored":
        if not isinstance(raw_result.get(HOST_SOURCE_DUTY_BINDING_FIELD), Mapping) or raw_result[HOST_SOURCE_DUTY_BINDING_FIELD].get("version") != HOST_SOURCE_DUTY_BINDING_VERSION:
            raise ValueError("fresh Greenfield candidate requires lifecycle-only source duty binding")
        binding = validate_greenfield_source_duty_binding(
            raw_result.get(HOST_SOURCE_DUTY_BINDING_FIELD),
            ledger_receipt=verified_ledger,
            candidate_result=raw_result,
            evidence_text=evidence_text,
        )
    canonical_response = canonical_greenfield_host_candidate(
        response,
        evidence_text=evidence_text,
        source_duty_receipt=verified_ledger,
    )
    canonical_frozen = _canonical_candidate_bytes(canonical_response)
    canonical_candidate_sha256 = hashlib.sha256(canonical_frozen).hexdigest()
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
        effective_timeout_seconds=profile.model_timeout_seconds,
        semantic_model_call_count=0,
        allow_zero_semantic_calls=True,
        event_citations_are_event_owned=True,
        allow_exact_dual_role_constraints=True,
        first_path_event_orders=(
            tuple(
                dict.fromkeys(
                    row["event_order"] for row in binding["first_path_actions"]
                )
            )
            if binding is not None
            else None
        ),
        accepted_source_duties=verified_ledger if binding is not None else None,
        accepted_source_duty_binding=binding,
    )
    if _canonical_candidate_bytes(response) != raw_frozen:
        raise RuntimeError("Greenfield host-candidate validation changed the candidate")
    if _canonical_candidate_bytes(canonical_response) != canonical_frozen:
        raise RuntimeError(
            "Greenfield host-candidate validation changed the canonical projection"
        )

    receipt = {
        "version": HOST_CANDIDATE_RECEIPT_VERSION,
        "contract_version": HOST_CANDIDATE_CONTRACT_VERSION,
        "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "source_sha256": hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
        "raw_candidate_sha256": raw_candidate_sha256,
        "canonical_candidate_sha256": canonical_candidate_sha256,
        "source_duty_ledger_sha256": verified_ledger["ledger_sha256"],
        "source_duty_verifier_task_sha256": verified_ledger["verifier_task_sha256"],
        "source_duty_decision_set_sha256": verified_ledger["decision_set_sha256"],
        "source_duty_binding_sha256": (
            hashlib.sha256(_canonical_candidate_bytes(binding)).hexdigest()
            if binding is not None
            else None
        ),
    }
    if isinstance(authored, GreenfieldModelAuthoredIntent):
        authored = replace(
            authored,
            elapsed_seconds=max(0.0, clock() - started),
            effective_model_window_seconds=profile.model_timeout_seconds,
        )
    elif isinstance(authored, GreenfieldAuthoringClarification):
        authored = replace(
            authored,
            elapsed_seconds=max(0.0, clock() - started),
            effective_model_window_seconds=profile.model_timeout_seconds,
        )
    emit_greenfield_model_proof_observation(
        evidence_text=evidence_text,
        host_candidate=receipt,
    )
    return authored, receipt


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
        raise ValueError(
            "Greenfield host candidate must be canonical JSON data"
        ) from exc


__all__ = [
    "LEGACY_HOST_CANDIDATE_CONTRACT_VERSION",
    "PREVIOUS_HOST_CANDIDATE_CONTRACT_VERSION",
    "PASSIVE_HOST_CANDIDATE_CONTRACT_VERSIONS",
    "HOST_CANDIDATE_CONTRACT_VERSION",
    "HOST_CANDIDATE_RECEIPT_VERSION",
    "MAX_HOST_CANDIDATE_BYTES",
    "admit_greenfield_host_candidate",
    "greenfield_host_candidate_contract",
    "HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION",
    "greenfield_host_candidate_authoring_request",
    "load_greenfield_host_candidate_file",
]
