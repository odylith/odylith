"""Bounded source-only decisions for Greenfield material duty claims.

This module checks verdict custody and completeness. The semantic yes/no judgment
belongs to the independent verifier; a digest cannot prove that judgment true.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
    MAX_EVIDENCE_BYTES,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
)

from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    ACTION_SECTIONS as _ACTION_SECTIONS,
    DUTY_SECTIONS as _CLAIM_SECTIONS,
    MAX_DERIVED_REFS,
    MAX_COMPACT_CITATIONS,
    compact_source_duty_view,
    duty_references,
)


SOURCE_DUTY_DECISION_SET_VERSION = "odylith.greenfield.source-duty-decisions.v4"
EDIT_SOURCE_DUTY_DECISION_SET_VERSION = "odylith.greenfield.source-duty-decisions.v5"
EDIT_PRESERVATION_VERSION = "odylith.greenfield.edit-lifecycle-preservation.v1"
_LIFECYCLE_SECTIONS = tuple(
    section for section, _ in _CLAIM_SECTIONS if section not in _ACTION_SECTIONS
)


class GreenfieldSourceDutyEntailmentError(ValueError):
    """The source-only material duty decisions cannot admit the ledger."""


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def greenfield_edit_preservation_context(
    *, transaction_hash: str, prior_lifecycle: Mapping[str, Any],
    correction: str, evidence_text: str,
) -> dict[str, Any]:
    """Bind the prior verified seal as a checklist, never as current authority.

    The CLI derives this input only after resolving the pending transaction with
    its delivered completion receipt and validating its compiler receipt.
    """
    if (not isinstance(transaction_hash, str) or len(transaction_hash) != 64
            or any(char not in "0123456789abcdef" for char in transaction_hash)
            or not isinstance(correction, str) or not correction.strip()
            or not evidence_text.endswith(correction + "\n")):
        raise GreenfieldSourceDutyEntailmentError("EDIT preservation custody is invalid")
    expected_fields = {"version", "source_sha256", "ledger_sha256", "binding_sha256",
                       "lifecycle_sha256", *_LIFECYCLE_SECTIONS}
    if (not isinstance(prior_lifecycle, Mapping)
            or set(prior_lifecycle) != expected_fields
            or prior_lifecycle.get("version") != "odylith.greenfield.source-lifecycle.v2"
            or prior_lifecycle.get("lifecycle_sha256") != _canonical_sha256({
                key: value for key, value in prior_lifecycle.items()
                if key != "lifecycle_sha256"
            })):
        raise GreenfieldSourceDutyEntailmentError("EDIT prior lifecycle is invalid")
    identities: set[str] = set()
    for section in _LIFECYCLE_SECTIONS:
        rows = prior_lifecycle[section]
        if not isinstance(rows, list) or len(rows) > 32:
            raise GreenfieldSourceDutyEntailmentError("EDIT prior lifecycle exceeds its bound")
        for row in rows:
            duty_id = row.get("duty_id") if isinstance(row, Mapping) else None
            if (not isinstance(duty_id, str) or not duty_id.strip()
                    or len(duty_id) > 200 or duty_id in identities):
                raise GreenfieldSourceDutyEntailmentError("EDIT prior duty identity is invalid")
            identities.add(duty_id)
    return {
        "version": EDIT_PRESERVATION_VERSION,
        "transaction_hash": transaction_hash,
        "prior_lifecycle": deepcopy(dict(prior_lifecycle)),
        "correction": correction,
        "correction_sha256": hashlib.sha256(correction.encode("utf-8")).hexdigest(),
        "source_sha256": hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
    }


def _validate_edit_context(context: Mapping[str, Any], *, evidence_text: str) -> None:
    if not isinstance(context, Mapping) or set(context) != {
        "version", "transaction_hash", "prior_lifecycle", "correction",
        "correction_sha256", "source_sha256",
    }:
        raise GreenfieldSourceDutyEntailmentError("EDIT preservation context is malformed")
    expected = greenfield_edit_preservation_context(
        transaction_hash=context["transaction_hash"], prior_lifecycle=context["prior_lifecycle"],
        correction=context["correction"], evidence_text=evidence_text,
    )
    if dict(context) != expected:
        raise GreenfieldSourceDutyEntailmentError("EDIT preservation context hash is invalid")


def _prior_duties(context: Mapping[str, Any]):
    for section in _LIFECYCLE_SECTIONS:
        for row in context["prior_lifecycle"][section]:
            yield section, f"{section}/{row['duty_id']}", row


def greenfield_edit_preservation_view(context: Mapping[str, Any]) -> dict[str, Any]:
    """Keep semantic fields and exact prior citations; omit unrelated design ownership."""
    lifecycle = context["prior_lifecycle"]
    return {
        "version": context["version"], "transaction_hash": context["transaction_hash"],
        "correction": context["correction"], "correction_sha256": context["correction_sha256"],
        "prior_lifecycle": {
            "version": lifecycle["version"], "lifecycle_sha256": lifecycle["lifecycle_sha256"],
            **{section: [{key: deepcopy(value) for key, value in row.items()
                         if key not in {"component_key", "workstream_key"}}
                        for row in lifecycle[section]] for section in _LIFECYCLE_SECTIONS},
        },
    }


def source_duty_claims(
    ledger: Mapping[str, Any], *, source_sha256: str
) -> list[dict[str, Any]]:
    """Produce ordered, hash-bound semantic claims from structurally checked rows."""

    claims: list[dict[str, Any]] = []
    for section, typed_role in _CLAIM_SECTIONS:
        for row in ledger[section]:
            support_refs, role_refs = duty_references(section, row)
            claim = {
                "duty_id": row["id"],
                "section": section,
                "typed_role": typed_role,
                "material_row": deepcopy(row),
                "source_refs": deepcopy(support_refs),
                "role_refs": deepcopy(role_refs),
                "source_sha256": source_sha256,
            }
            if section in _ACTION_SECTIONS:
                claim.update(
                    {
                        "performer_role": (
                            row["performer_role"]
                            if section == "first_path_actions"
                            else ""
                        ),
                        "statement": row["statement"],
                        "event_ref": deepcopy(row["event_ref"]),
                        "actor_ref": deepcopy(row["actor_ref"]),
                        "action": row["action"],
                        "target": row["target"],
                    }
                )
            claim["claim_sha256"] = _canonical_sha256(claim)
            claims.append(claim)
    return claims


def greenfield_source_duty_decision_set_schema(
    claims: list[Mapping[str, Any]] | None = None,
    *, edit_preservation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a closed table keyed by exactly the compiler-owned duty identities."""

    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    indexes = {
        "type": "array",
        "maxItems": MAX_DERIVED_REFS,
        "items": {"type": "integer", "minimum": 0, "maximum": MAX_DERIVED_REFS - 1},
    }
    decision = {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdict", "support_ref_indexes", "role_ref_indexes"],
        "properties": {
            "verdict": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "support_ref_indexes": indexes,
            "role_ref_indexes": indexes,
        },
    }
    citation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["quote", "context"],
        "properties": {
            "quote": {"type": "string", "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
            "context": {"type": "string", "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
        },
    }
    omission = {
        "type": "object",
        "additionalProperties": False,
        "required": ["omission_id", "typed_role", "source_ref"],
        "properties": {
            "omission_id": {"type": "string", "maxLength": 200},
            "typed_role": {
                "type": "string",
                "enum": [typed_role for _, typed_role in _CLAIM_SECTIONS],
            },
            "source_ref": citation,
        },
    }
    completeness = {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdict", "omissions"],
        "properties": {
            "verdict": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "omissions": {"type": "array", "maxItems": 32, "items": omission},
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "verifier_task_sha256",
            "decisions",
            "source_completeness",
        ],
        "properties": {
            "version": {"type": "string", "enum": [
                EDIT_SOURCE_DUTY_DECISION_SET_VERSION if edit_preservation is not None
                else SOURCE_DUTY_DECISION_SET_VERSION]},
            "verifier_task_sha256": digest,
            "decisions": {
                "type": "object",
                "additionalProperties": False,
                "required": [claim["duty_id"] for claim in claims or []],
                "properties": {
                    claim["duty_id"]: deepcopy(decision) for claim in claims or []
                },
            },
            "source_completeness": completeness,
        },
    }
    if edit_preservation is not None:
        preservation = {}
        for section, key, _ in _prior_duties(edit_preservation):
            preservation[key] = {
                "type": "object", "additionalProperties": False,
                "required": ["verdict", "current_duty_id", "correction_ref_indexes"],
                "properties": {
                    "verdict": {"type": "string", "enum": [
                        "preserved", "changed", "removed", "missing", "uncertain"]},
                    "current_duty_id": {"type": "string", "enum": ["", *[
                        claim["duty_id"] for claim in claims or []
                        if claim["section"] == section]]},
                    "correction_ref_indexes": {**indexes, "items": {
                        "type": "integer", "minimum": 0,
                        "maximum": MAX_COMPACT_CITATIONS - 1}},
                },
            }
        schema["required"].extend(("edit_preservation", "edit_correction_refs"))
        schema["properties"].update({
            "edit_preservation": {"type": "object", "additionalProperties": False,
                                  "required": list(preservation), "properties": preservation},
            "edit_correction_refs": {"type": "array", "maxItems": MAX_COMPACT_CITATIONS,
                                     "items": citation},
        })
    return schema


def source_duty_entailment_task(
    preflight: Mapping[str, Any], *, evidence_text: str,
    edit_preservation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Package the bounded full authority source for one verifier pass."""

    if not isinstance(evidence_text, str) or not evidence_text.strip():
        raise GreenfieldSourceDutyEntailmentError(
            "source duty authority source is empty"
        )
    evidence = evidence_text.encode("utf-8")
    if len(evidence) > MAX_EVIDENCE_BYTES:
        raise GreenfieldSourceDutyEntailmentError(
            "source duty authority source exceeds its bound"
        )
    if hashlib.sha256(evidence).hexdigest() != preflight.get("source_sha256"):
        raise GreenfieldSourceDutyEntailmentError(
            "source duty authority source hash is invalid"
        )

    if edit_preservation is not None:
        _validate_edit_context(edit_preservation, evidence_text=evidence_text)
    view = compact_source_duty_view(preflight["ledger"])
    if len(view["citations"]) > MAX_COMPACT_CITATIONS:
        raise GreenfieldSourceDutyEntailmentError(
            "source duty verifier citation bank exceeds its bound"
        )
    task = {
        "task": (
            "Judge every material duty row against the complete authority source, "
            "including hierarchy, reference-only controls, and contradictions outside "
            "its cited excerpt. Assess every source-asserted field in each ledger row "
            "and its typed section/role. For actions, the cited event and "
            "typed role must support the full actor, action, target, and normalized "
            "statement; a shared verb can support distinct targets. A yes action "
            "decision must affirm that actor_ref names exactly ONE action performer "
            "of the asserted typed role. Reject an actor quote containing a whole "
            "action sentence, additional performers, or whole duty or paragraph "
            "context, even when its bytes are source-cited. Event and role refs "
            "carry that wider context separately. An identity from explicit role "
            "context may resolve a pronoun or inherited verb; judge that performer "
            "assignment against the complete source. Check that repeated actor "
            "citations identify the same performer across actions and supporting "
            "duties while distinct source performers retain distinct identities. "
            "The identity quote must be "
            "retained literally in the normalized statement, but containment alone "
            "proves custody, not semantic atomicity or performer entailment. "
            "For state fields, "
            "transitions, guards, boundaries, and proof duties, verify the meaning of "
            "every field against the exact source refs. A transition observable_check "
            "may express a consistent check of its cited effect without literal source "
            "wording. Do not promote reference context into a product duty. Return "
            "one decision per material row, keyed by its exact duty ID. The compiler "
            "owns claim hashes and canonical order; do not return or invent hashes. A yes "
            "decision must cite indexes of exact source and role references; use no "
            "or uncertain otherwise. Then scan the complete authority source from "
            "start to end for material actions, state fields, off-path transitions, "
            "guards, boundaries, and proof duties missing from the inventory. Return "
            "one source_completeness verdict: yes with no omissions only if every "
            "material source duty is represented; no or uncertain with at least one "
            "omission_id, typed_role, and exact source quote/context otherwise. "
            "Reference-only material is not a product duty. Do not author a "
            "candidate, add or omit row decisions, or give a second global pass."
        ),
        "authority_source": evidence_text,
        "source_duty_ledger": view,
        "reference_index_order": (
            "Resolve citation IDs through the citation bank. For action rows, support "
            "references are event_ref followed by source_refs; role references are "
            "actor_ref followed by role_refs. Deduplicate identical quote/context pairs "
            "in each list, preserving first occurrence. For other rows, both lists "
            "equal source_refs with identical-pair deduplication. Return zero-based "
            "indexes of those derived lists. A yes action must select its event, actor, "
            "and every authored role context. Judge every normalized statement, action, "
            "target and role semantically against the full source; substring placement "
            "in a normalized statement does not prove entailment. Object key order "
            "cannot change workflow order. Return compact JSON only."
        ),
        "decision_set_schema": greenfield_source_duty_decision_set_schema(
            preflight["claims"], edit_preservation=edit_preservation,
        ),
    }
    if edit_preservation is not None:
        task["edit_preservation"] = greenfield_edit_preservation_view(edit_preservation)
        task["edit_preservation_task"] = (
            "Give one decision for every compiler-owned prior lifecycle key. The prior seal "
            "is a coverage checklist, not current truth; do not copy it or let it override "
            "the explicit correction. Compare each prior condition, actor, target, scope, "
            "timing, effect and consequence with a current duty in the SAME typed section. "
            "Prose, another section or an unrelated current duty cannot preserve it. "
            "Select preserved only for equivalent meaning with an ordinary yes decision; "
            "changed requires a current same-section yes duty and exact correction evidence "
            "explicitly changing that prior duty; removed requires exact correction evidence "
            "explicitly withdrawing it and an empty current_duty_id. Original source and "
            "general preservation statements cannot authorize change or removal. Return "
            "missing or uncertain when unsupported. A compound current duty may carry "
            "multiple prior duties; compare each prior meaning independently and require "
            "exact correction evidence for every changed duty. Put distinct correction-only "
            "quote/context pairs in "
            "edit_correction_refs and cite their zero-based indexes; context locates, never "
            "adds meaning. preserved/missing/uncertain use no correction indexes. This is "
            "part of this same source-only pass; do not author a candidate or another review."
        )
    task["verifier_task_sha256"] = _canonical_sha256(task)
    return task


def _valid_indexes(value: Any, *, limit: int, allow_empty: bool) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and len(value) <= MAX_DERIVED_REFS
        and all(type(index) is int and 0 <= index < limit for index in value)
        and value == sorted(set(value))
    )


def _validate_source_completeness(value: Any, *, evidence_text: str) -> None:
    if not isinstance(value, Mapping) or set(value) != {"verdict", "omissions"}:
        raise GreenfieldSourceDutyEntailmentError(
            "source completeness verdict is malformed"
        )
    verdict = value["verdict"]
    omissions = value["omissions"]
    if verdict not in ("yes", "no", "uncertain"):
        raise GreenfieldSourceDutyEntailmentError(
            "source completeness verdict is invalid"
        )
    if not isinstance(omissions, list) or len(omissions) > 32:
        raise GreenfieldSourceDutyEntailmentError(
            "source completeness omissions are invalid"
        )
    if (verdict == "yes" and omissions) or (verdict != "yes" and not omissions):
        raise GreenfieldSourceDutyEntailmentError(
            "source completeness verdict and omissions disagree"
        )
    roles = {typed_role for _, typed_role in _CLAIM_SECTIONS}
    seen_ids: set[str] = set()
    evidence = evidence_text.encode("utf-8")
    for index, omission in enumerate(omissions):
        if not isinstance(omission, Mapping) or set(omission) != {
            "omission_id",
            "typed_role",
            "source_ref",
        }:
            raise GreenfieldSourceDutyEntailmentError(
                f"source completeness omission {index} is malformed"
            )
        omission_id = omission["omission_id"]
        if (
            not isinstance(omission_id, str)
            or not omission_id.strip()
            or len(omission_id) > 200
            or omission_id in seen_ids
            or omission["typed_role"] not in roles
        ):
            raise GreenfieldSourceDutyEntailmentError(
                f"source completeness omission {index} has invalid identity"
            )
        seen_ids.add(omission_id)
        source_ref = omission["source_ref"]
        if (
            not isinstance(source_ref, Mapping)
            or set(source_ref) != {"quote", "context"}
            or any(
                not isinstance(source_ref[field], str)
                or not source_ref[field].strip()
                or len(source_ref[field]) > MAX_AUTHORED_FIELD_VALUE_CHARS
                for field in ("quote", "context")
            )
        ):
            raise GreenfieldSourceDutyEntailmentError(
                f"source completeness omission {index} has invalid source citation"
            )
        try:
            canonical_citation_from_host_selection(evidence, source_ref)
        except GreenfieldModelAuthoringError as exc:
            raise GreenfieldSourceDutyEntailmentError(
                f"source completeness omission {index} has invalid source citation"
            ) from exc
    if verdict != "yes":
        raise GreenfieldSourceDutyEntailmentError(
            f"source completeness is not affirmative: {omissions[0]['omission_id']}"
        )


def _validate_edit_preservation(
    decision_set: Mapping[str, Any], *, context: Mapping[str, Any],
    claims: list[Mapping[str, Any]], evidence_text: str,
) -> None:
    _validate_edit_context(context, evidence_text=evidence_text)
    table, refs = decision_set["edit_preservation"], decision_set["edit_correction_refs"]
    prior = list(_prior_duties(context))
    if (not isinstance(table, Mapping) or set(table) != {key for _, key, _ in prior}
            or not isinstance(refs, list) or len(refs) > MAX_COMPACT_CITATIONS):
        raise GreenfieldSourceDutyEntailmentError("EDIT preservation decisions are incomplete")
    correction_bytes = context["correction"].encode("utf-8")
    seen_refs = set()
    for ref in refs:
        try:
            canonical_citation_from_host_selection(correction_bytes, ref)
        except GreenfieldModelAuthoringError as exc:
            raise GreenfieldSourceDutyEntailmentError(
                "EDIT override citation is outside the exact correction"
            ) from exc
        pair = (ref["quote"], ref["context"])
        if pair in seen_refs:
            raise GreenfieldSourceDutyEntailmentError("EDIT correction citation is duplicated")
        seen_refs.add(pair)
    current = {claim["duty_id"]: claim for claim in claims}
    used_refs = set()
    for section, key, _ in prior:
        decision = table[key]
        if not isinstance(decision, Mapping) or set(decision) != {
            "verdict", "current_duty_id", "correction_ref_indexes",
        }:
            raise GreenfieldSourceDutyEntailmentError(f"EDIT preservation {key} is malformed")
        verdict, carrier, indexes = (
            decision["verdict"], decision["current_duty_id"], decision["correction_ref_indexes"]
        )
        if verdict not in ("preserved", "changed", "removed"):
            raise GreenfieldSourceDutyEntailmentError(f"EDIT preservation {key} is not affirmative")
        if (not isinstance(carrier, str)
                or not _valid_indexes(indexes, limit=len(refs), allow_empty=verdict == "preserved")
                or (verdict == "preserved" and indexes)):
            raise GreenfieldSourceDutyEntailmentError(f"EDIT preservation {key} has invalid override")
        if verdict == "removed":
            if carrier:
                raise GreenfieldSourceDutyEntailmentError(f"EDIT removed duty {key} has a current carrier")
        elif (carrier not in current or current[carrier]["section"] != section
                or decision_set["decisions"][carrier]["verdict"] != "yes"):
            raise GreenfieldSourceDutyEntailmentError(f"EDIT preservation {key} has invalid typed carrier")
        used_refs.update(indexes)
    if used_refs != set(range(len(refs))):
        raise GreenfieldSourceDutyEntailmentError("EDIT correction citation bank has unused references")


def validate_source_duty_decision_set(
    decision_set: Mapping[str, Any],
    *,
    claims: list[Mapping[str, Any]],
    source_sha256: str,
    verifier_task_sha256: str,
    evidence_text: str,
    edit_preservation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Require a complete affirmative decision for every fixed material duty."""

    fields = {
        "version",
        "verifier_task_sha256",
        "decisions",
        "source_completeness",
    }
    if edit_preservation is not None:
        fields.update(("edit_preservation", "edit_correction_refs"))
    if not isinstance(decision_set, Mapping) or set(decision_set) != fields:
        raise GreenfieldSourceDutyEntailmentError(
            "source duty decision set is malformed"
        )
    if (
        decision_set["version"] != (EDIT_SOURCE_DUTY_DECISION_SET_VERSION
                                    if edit_preservation is not None else SOURCE_DUTY_DECISION_SET_VERSION)
        or decision_set["verifier_task_sha256"] != verifier_task_sha256
        or any(claim["source_sha256"] != source_sha256 for claim in claims)
    ):
        raise GreenfieldSourceDutyEntailmentError(
            "source duty decision binding is invalid"
        )
    decisions = decision_set["decisions"]
    expected_ids = [claim["duty_id"] for claim in claims]
    if (
        not isinstance(decisions, Mapping)
        or set(decisions) != set(expected_ids)
        or len(expected_ids) != len(set(expected_ids))
    ):
        raise GreenfieldSourceDutyEntailmentError(
            "source duty decisions are incomplete or contain unexpected IDs"
        )
    canonical_decisions: dict[str, Any] = {}
    for index, claim in enumerate(claims):
        decision = decisions[claim["duty_id"]]
        if not isinstance(decision, Mapping) or set(decision) != {
            "verdict",
            "support_ref_indexes",
            "role_ref_indexes",
        }:
            raise GreenfieldSourceDutyEntailmentError(
                f"source duty decision {index} is malformed"
            )
        if decision["verdict"] not in ("yes", "no", "uncertain"):
            raise GreenfieldSourceDutyEntailmentError(
                f"source duty decision {index} has invalid verdict"
            )
        support_indexes = decision["support_ref_indexes"]
        role_indexes = decision["role_ref_indexes"]
        affirmative = decision["verdict"] == "yes"
        if not _valid_indexes(
            support_indexes,
            limit=len(claim["source_refs"]),
            allow_empty=not affirmative,
        ):
            raise GreenfieldSourceDutyEntailmentError(
                f"source duty decision {index} has invalid support indexes"
            )
        if not _valid_indexes(
            role_indexes, limit=len(claim["role_refs"]), allow_empty=not affirmative
        ):
            raise GreenfieldSourceDutyEntailmentError(
                f"source duty decision {index} has invalid role indexes"
            )
        if affirmative:
            cited = [claim["source_refs"][i] for i in support_indexes]
            if "event_ref" in claim and claim["event_ref"] not in cited:
                raise GreenfieldSourceDutyEntailmentError(
                    f"source duty decision {index} omits its event reference"
                )
            roles = [claim["role_refs"][i] for i in role_indexes]
            if "actor_ref" in claim and (
                claim["actor_ref"] not in roles
                or any(ref not in roles for ref in claim["material_row"]["role_refs"])
            ):
                raise GreenfieldSourceDutyEntailmentError(
                    f"source duty decision {index} omits actor or role context"
                )
            if "event_ref" not in claim and len(support_indexes) != len(
                claim["source_refs"]
            ):
                raise GreenfieldSourceDutyEntailmentError(
                    f"source duty decision {index} omits a material source reference"
                )
        if decision["verdict"] != "yes":
            raise GreenfieldSourceDutyEntailmentError(
                f"source duty decision {index} is not affirmative"
            )
        canonical_decisions[claim["duty_id"]] = deepcopy(dict(decision))
    if edit_preservation is not None:
        _validate_edit_preservation(
            decision_set, context=edit_preservation, claims=claims, evidence_text=evidence_text,
        )
    _validate_source_completeness(
        decision_set["source_completeness"], evidence_text=evidence_text
    )
    return {**deepcopy(dict(decision_set)), "decisions": canonical_decisions}


__all__ = [
    "EDIT_SOURCE_DUTY_DECISION_SET_VERSION",
    "EDIT_PRESERVATION_VERSION",
    "GreenfieldSourceDutyEntailmentError",
    "SOURCE_DUTY_DECISION_SET_VERSION",
    "greenfield_edit_preservation_context",
    "greenfield_edit_preservation_view",
    "greenfield_source_duty_decision_set_schema",
    "source_duty_claims",
    "source_duty_entailment_task",
    "validate_source_duty_decision_set",
]
