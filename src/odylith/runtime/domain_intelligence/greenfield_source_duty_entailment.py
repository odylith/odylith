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


class GreenfieldSourceDutyEntailmentError(ValueError):
    """The source-only material duty decisions cannot admit the ledger."""


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "verifier_task_sha256",
            "decisions",
            "source_completeness",
        ],
        "properties": {
            "version": {"type": "string", "enum": [SOURCE_DUTY_DECISION_SET_VERSION]},
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


def source_duty_entailment_task(
    preflight: Mapping[str, Any], *, evidence_text: str
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
            "statement; a shared verb can support distinct targets. For state fields, "
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
            preflight["claims"]
        ),
    }
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


def validate_source_duty_decision_set(
    decision_set: Mapping[str, Any],
    *,
    claims: list[Mapping[str, Any]],
    source_sha256: str,
    verifier_task_sha256: str,
    evidence_text: str,
) -> dict[str, Any]:
    """Require a complete affirmative decision for every fixed material duty."""

    if not isinstance(decision_set, Mapping) or set(decision_set) != {
        "version",
        "verifier_task_sha256",
        "decisions",
        "source_completeness",
    }:
        raise GreenfieldSourceDutyEntailmentError(
            "source duty decision set is malformed"
        )
    if (
        decision_set["version"] != SOURCE_DUTY_DECISION_SET_VERSION
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
    _validate_source_completeness(
        decision_set["source_completeness"], evidence_text=evidence_text
    )
    return {**deepcopy(dict(decision_set)), "decisions": canonical_decisions}


__all__ = [
    "GreenfieldSourceDutyEntailmentError",
    "SOURCE_DUTY_DECISION_SET_VERSION",
    "greenfield_source_duty_decision_set_schema",
    "source_duty_claims",
    "source_duty_entailment_task",
    "validate_source_duty_decision_set",
]
