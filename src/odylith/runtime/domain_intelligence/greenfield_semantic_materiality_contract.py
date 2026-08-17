"""Prompt-only materiality gate for Greenfield semantic graph authoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import hmac
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_graph_contract import (
    SEMANTIC_CLARIFICATION_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    require_semantic_source_refs,
    semantic_source_ref_schema,
)


SEMANTIC_MATERIALITY_ASSESSMENT_VERSION = (
    "odylith.greenfield.semantic-materiality-assessment.v1"
)
SEMANTIC_REASONING_CAPABILITY_PROFILE = "frontier_semantic_reasoning"
SEMANTIC_MATERIALITY_ASSESSMENT_BASIS = "prompt_only_pre_graph"
SEMANTIC_MATERIALITY_STATUSES = (
    "explicit",
    "source_entailable",
    "nonmaterial_assumption",
    "materially_unresolved",
)


def semantic_materiality_assessment_schema() -> dict[str, Any]:
    """Return the provider schema for the independent prompt-only gate."""

    source_ref = semantic_source_ref_schema()
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "evidence_sha256",
            "authoring_contract_sha256",
            "assessment_basis",
            "decision",
            "clarification",
            "fields",
        ],
        "properties": {
            "version": {
                "type": "string",
                "enum": [SEMANTIC_MATERIALITY_ASSESSMENT_VERSION],
            },
            "evidence_sha256": {"type": "string", "minLength": 64, "maxLength": 64},
            "authoring_contract_sha256": {
                "type": "string",
                "minLength": 64,
                "maxLength": 64,
            },
            "assessment_basis": {
                "type": "string",
                "enum": [SEMANTIC_MATERIALITY_ASSESSMENT_BASIS],
            },
            "decision": {
                "type": "string",
                "enum": ["authorize_graph", "clarification_required"],
            },
            "clarification": _materiality_clarification_schema(),
            "fields": {
                "type": "array",
                "minItems": len(SEMANTIC_CLARIFICATION_FIELDS),
                "maxItems": len(SEMANTIC_CLARIFICATION_FIELDS),
                "items": _materiality_field_schema(source_ref),
            },
        },
    }


def _materiality_clarification_schema() -> dict[str, Any]:
    return {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "question"],
                "properties": {
                    "field": {"type": "string", "enum": [""]},
                    "question": {"type": "string", "enum": [""]},
                },
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "question"],
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": list(SEMANTIC_CLARIFICATION_FIELDS),
                    },
                    "question": {"type": "string", "minLength": 1, "maxLength": 600},
                },
            },
        ]
    }


def _materiality_field_schema(source_ref: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "anyOf": [
            _materiality_field_variant_schema(
                source_ref=source_ref,
                statuses=("explicit", "source_entailable"),
                source_ref_minimum=1,
                alternative_minimum=0,
                alternative_maximum=0,
            ),
            _materiality_field_variant_schema(
                source_ref=source_ref,
                statuses=("nonmaterial_assumption",),
                source_ref_minimum=0,
                source_ref_maximum=0,
                alternative_minimum=0,
                alternative_maximum=0,
            ),
            _materiality_field_variant_schema(
                source_ref=source_ref,
                statuses=("materially_unresolved",),
                source_ref_minimum=1,
                alternative_minimum=2,
                alternative_maximum=8,
            ),
        ]
    }


def _materiality_field_variant_schema(
    *,
    source_ref: Mapping[str, Any],
    statuses: tuple[str, ...],
    source_ref_minimum: int,
    source_ref_maximum: int = 8,
    alternative_minimum: int,
    alternative_maximum: int,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["field", "status", "source_refs", "alternatives"],
        "properties": {
            "field": {
                "type": "string",
                "enum": list(SEMANTIC_CLARIFICATION_FIELDS),
            },
            "status": {"type": "string", "enum": list(statuses)},
            "source_refs": {
                "type": "array",
                "minItems": source_ref_minimum,
                "maxItems": source_ref_maximum,
                "items": dict(source_ref),
            },
            "alternatives": {
                "type": "array",
                "minItems": alternative_minimum,
                "maxItems": alternative_maximum,
                "items": {"type": "string", "minLength": 1, "maxLength": 600},
            },
        },
    }


def semantic_materiality_critic_schema() -> dict[str, Any]:
    """Return the required independent critic capability receipt schema."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "capability_profile",
            "critic_run_id",
            "host_profile",
            "independent_context",
        ],
        "properties": {
            "capability_profile": {
                "type": "string",
                "enum": [SEMANTIC_REASONING_CAPABILITY_PROFILE],
            },
            "critic_run_id": {"type": "string", "minLength": 1, "maxLength": 200},
            "host_profile": {"type": "string", "minLength": 1, "maxLength": 100},
            "independent_context": {"type": "boolean", "enum": [True]},
        },
    }


def semantic_intent_author_schema() -> dict[str, Any]:
    """Return the required graph-author capability receipt schema."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["capability_profile", "author_run_id"],
        "properties": {
            "capability_profile": {
                "type": "string",
                "enum": [SEMANTIC_REASONING_CAPABILITY_PROFILE],
            },
            "author_run_id": {"type": "string", "minLength": 1, "maxLength": 200},
        },
    }


def require_semantic_materiality_assessment(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
    evidence_sha256: str,
    authoring_contract_sha256: str,
) -> dict[str, Any]:
    """Validate a pre-graph assessment without interpreting any source prose."""

    assessment = _mapping(value, "Semantic materiality assessment")
    _exact_keys(
        assessment,
        {
            "version",
            "evidence_sha256",
            "authoring_contract_sha256",
            "assessment_basis",
            "decision",
            "clarification",
            "fields",
        },
        "Semantic materiality assessment",
    )
    if assessment.get("version") != SEMANTIC_MATERIALITY_ASSESSMENT_VERSION:
        raise ValueError("Semantic materiality assessment uses an unsupported version")
    if not _matches_sha256(assessment.get("evidence_sha256"), evidence_sha256):
        raise ValueError("Semantic materiality assessment does not match source evidence")
    if not _matches_sha256(
        assessment.get("authoring_contract_sha256"),
        authoring_contract_sha256,
    ):
        raise ValueError("Semantic materiality assessment does not match the authoring contract")
    if assessment.get("assessment_basis") != SEMANTIC_MATERIALITY_ASSESSMENT_BASIS:
        raise ValueError("Semantic materiality assessment is not prompt-only and pre-graph")
    decision = _enum(
        assessment.get("decision"),
        {"authorize_graph", "clarification_required"},
        "materiality decision",
    )
    clarification = _materiality_clarification(assessment.get("clarification"))
    fields = _materiality_fields(
        assessment.get("fields"),
        evidence_sources=evidence_sources,
    )
    unresolved = [row for row in fields if row["status"] == "materially_unresolved"]
    if decision == "authorize_graph":
        if unresolved or clarification != {"field": "", "question": ""}:
            raise ValueError("authorize_graph materiality decision carries unresolved meaning")
    elif (
        len(unresolved) != 1
        or clarification["field"] != unresolved[0]["field"]
        or not clarification["question"]
    ):
        raise ValueError("clarification_required must name one unresolved canonical field")
    return {
        "version": assessment["version"],
        "evidence_sha256": assessment["evidence_sha256"],
        "authoring_contract_sha256": assessment["authoring_contract_sha256"],
        "assessment_basis": assessment["assessment_basis"],
        "decision": decision,
        "clarification": clarification,
        "fields": fields,
    }


def require_semantic_reasoning_runs(
    critic_value: Any,
    author_value: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate distinct frontier critic and author execution receipts."""

    critic = _mapping(critic_value, "Semantic materiality critic run")
    _exact_keys(
        critic,
        {"capability_profile", "critic_run_id", "host_profile", "independent_context"},
        "Semantic materiality critic run",
    )
    author = _mapping(author_value, "Semantic Intent author run")
    _exact_keys(
        author,
        {"capability_profile", "author_run_id"},
        "Semantic Intent author run",
    )
    if (
        critic.get("capability_profile") != SEMANTIC_REASONING_CAPABILITY_PROFILE
        or author.get("capability_profile") != SEMANTIC_REASONING_CAPABILITY_PROFILE
    ):
        raise ValueError("Greenfield semantic reasoning capability profile was downgraded")
    critic_run_id = _canonical_text(critic.get("critic_run_id"), 200, "critic run id")
    author_run_id = _canonical_text(author.get("author_run_id"), 200, "author run id")
    host_profile = _canonical_text(critic.get("host_profile"), 100, "critic host profile")
    if critic.get("independent_context") is not True:
        raise ValueError("Semantic materiality critic did not use independent context")
    if hmac.compare_digest(critic_run_id, author_run_id):
        raise ValueError("Semantic materiality critic and graph author runs are not distinct")
    return (
        {
            "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
            "critic_run_id": critic_run_id,
            "host_profile": host_profile,
            "independent_context": True,
        },
        {
            "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
            "author_run_id": author_run_id,
        },
    )


def require_materiality_intent_alignment(
    assessment: Mapping[str, Any],
    semantic_intent: Mapping[str, Any],
) -> None:
    """Require the prompt-only decision and authored IR outcome to agree exactly."""

    decision = assessment.get("decision")
    status = semantic_intent.get("status")
    clarification = semantic_intent.get("clarification")
    if not isinstance(clarification, Mapping):
        raise ValueError("Semantic Intent clarification is malformed")
    if decision == "authorize_graph":
        if status != "complete" or clarification != {
            "question": "", "fields": [], "source_refs": [],
        }:
            raise ValueError("authorized materiality assessment does not bind a complete graph")
        return
    expected = assessment.get("clarification")
    if not isinstance(expected, Mapping):
        raise ValueError("Semantic materiality clarification is malformed")
    if (
        decision != "clarification_required"
        or status != "clarification_required"
        or clarification.get("fields") != [expected.get("field")]
        or clarification.get("question") != expected.get("question")
    ):
        raise ValueError("materiality clarification does not match the clarification IR")


def semantic_materiality_assessment_sha256(value: Mapping[str, Any]) -> str:
    """Hash the canonical prompt-only assessment bytes."""

    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _materiality_fields(
    value: Any,
    *,
    evidence_sources: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows = _sequence(value, len(SEMANTIC_CLARIFICATION_FIELDS), "materiality fields")
    if len(rows) != len(SEMANTIC_CLARIFICATION_FIELDS):
        raise ValueError("Semantic materiality assessment lacks exact canonical field coverage")
    result: list[dict[str, Any]] = []
    for position, expected_field in enumerate(SEMANTIC_CLARIFICATION_FIELDS):
        row = _mapping(rows[position], "Semantic materiality field")
        _exact_keys(
            row,
            {"field", "status", "source_refs", "alternatives"},
            "Semantic materiality field",
        )
        if row.get("field") != expected_field:
            raise ValueError("Semantic materiality fields are missing, duplicated, or reordered")
        status = _enum(
            row.get("status"),
            set(SEMANTIC_MATERIALITY_STATUSES),
            "materiality field status",
        )
        source_refs = require_semantic_source_refs(
            row.get("source_refs"),
            evidence_sources=evidence_sources,
            allow_empty=status == "nonmaterial_assumption",
        )
        if status == "nonmaterial_assumption" and source_refs:
            raise ValueError("nonmaterial assumption carries explicit source citations")
        alternatives = _unique_text_rows(
            row.get("alternatives"),
            8,
            "materiality alternatives",
        )
        if status == "materially_unresolved":
            if len(alternatives) < 2:
                raise ValueError("materially unresolved field needs at least two alternatives")
        elif alternatives:
            raise ValueError("resolved materiality field carries alternatives")
        result.append(
            {
                "field": expected_field,
                "status": status,
                "source_refs": source_refs,
                "alternatives": alternatives,
            }
        )
    return result


def _materiality_clarification(value: Any) -> dict[str, str]:
    row = _mapping(value, "Semantic materiality clarification")
    _exact_keys(row, {"field", "question"}, "Semantic materiality clarification")
    field = row.get("field")
    if not isinstance(field, str) or field not in {"", *SEMANTIC_CLARIFICATION_FIELDS}:
        raise ValueError("Semantic materiality clarification field is invalid")
    question = _canonical_text(
        row.get("question"),
        600,
        "materiality clarification question",
        allow_empty=True,
    )
    return {"field": field, "question": question}


def _unique_text_rows(value: Any, maximum: int, label: str) -> list[str]:
    result = [
        _canonical_text(row, 600, label)
        for row in _sequence(value, maximum, label)
    ]
    if len(set(result)) != len(result):
        raise ValueError(f"Semantic {label} are not unique")
    return result


def _canonical_text(
    value: Any,
    maximum: int,
    label: str,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) > maximum:
        raise ValueError(f"Semantic {label} is malformed")
    if not value and not allow_empty:
        raise ValueError(f"Semantic {label} is empty")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is malformed")
    return value


def _sequence(value: Any, maximum: int, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"Semantic {label} are malformed")
    rows = list(value)
    if len(rows) > maximum:
        raise ValueError(f"Semantic {label} exceed their operating limit")
    return rows


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} has an invalid structure")


def _enum(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"Semantic {label} is invalid")
    return value


def _matches_sha256(value: Any, expected: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
        and isinstance(expected, str)
        and hmac.compare_digest(value, expected)
    )


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


__all__ = [
    "SEMANTIC_MATERIALITY_ASSESSMENT_BASIS",
    "SEMANTIC_MATERIALITY_ASSESSMENT_VERSION",
    "SEMANTIC_MATERIALITY_STATUSES",
    "SEMANTIC_REASONING_CAPABILITY_PROFILE",
    "require_materiality_intent_alignment",
    "require_semantic_materiality_assessment",
    "require_semantic_reasoning_runs",
    "semantic_intent_author_schema",
    "semantic_materiality_assessment_schema",
    "semantic_materiality_assessment_sha256",
    "semantic_materiality_critic_schema",
]
