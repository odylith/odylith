"""Expand the fresh typed source-duty inventory without changing material rows."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
    MAX_EVIDENCE_BYTES,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    SOURCE_DUTY_LEDGER_VERSION,
    _validate_shape,
    _check_citation,
    greenfield_source_duty_ledger_schema,
    resolve_greenfield_action_actor_identity,
    resolve_greenfield_transition_state_fields,
)

from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    ACTION_SECTIONS as _ACTION_SECTIONS,
    MAX_COMPACT_CITATIONS,
    SOURCE_DUTY_COMPACT_VERSION,
)

_ACTION_CITATION_FIELDS = ("event_ref", "actor_ref")


def _citation_id_schema() -> dict[str, Any]:
    return {"type": "string", "maxLength": 32}


def _closed_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def greenfield_compact_source_duty_ledger_schema() -> dict[str, Any]:
    """Return the closed compact schema whose citations are interned by ID."""

    schema = deepcopy(greenfield_source_duty_ledger_schema())
    properties = schema["properties"]
    properties["version"] = {
        "type": "string",
        "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
        "enum": [SOURCE_DUTY_COMPACT_VERSION],
    }
    properties["citations"] = {
        "type": "array",
        "maxItems": MAX_COMPACT_CITATIONS,
        "items": _closed_object(
            {
                "id": _citation_id_schema(),
                "q": {"type": "string", "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
                "c": {"type": "string", "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
            }
        ),
    }
    control = properties["evidence_controls"]["items"]
    control["properties"].pop("quote")
    control["properties"].pop("context")
    control["properties"]["ref"] = _citation_id_schema()
    control["required"] = ["ref", "handling"]
    for section, section_schema in properties.items():
        if section not in {
            "first_path_actions",
            "supporting_human_actions",
            "system_duties",
            "state_fields",
            "off_path_transitions",
            "conditional_guards",
            "boundaries",
            "proof_duties",
        }:
            continue
        row = section_schema["items"]
        row["properties"]["source_refs"]["items"] = _citation_id_schema()
        if section in _ACTION_SECTIONS:
            for field in _ACTION_CITATION_FIELDS:
                row["properties"][field] = _citation_id_schema()
            row["properties"]["role_refs"]["items"] = _citation_id_schema()
    schema["required"] = ["citations", *schema["required"]]
    return schema


def expand_compact_source_duty_ledger(
    value: Mapping[str, Any],
    *,
    evidence_text: str | None = None,
) -> dict[str, Any]:
    """Expand material rows; discard unused bank storage only after exact source checks."""

    _validate_shape(value, greenfield_compact_source_duty_ledger_schema(), "ledger")
    evidence: bytes | None = None
    if evidence_text is not None:
        if not isinstance(evidence_text, str) or not evidence_text.strip():
            raise GreenfieldSourceDutyLedgerError("compact source evidence is empty")
        evidence = evidence_text.encode("utf-8")
        if len(evidence) > MAX_EVIDENCE_BYTES:
            raise GreenfieldSourceDutyLedgerError(
                "compact source evidence exceeds its bound"
            )
    citations: dict[str, dict[str, str]] = {}
    pairs: set[tuple[str, str]] = set()
    for index, entry in enumerate(value["citations"]):
        citation_id, quote, context = entry["id"], entry["q"], entry["c"]
        if not citation_id or not quote or not context:
            raise GreenfieldSourceDutyLedgerError(
                f"citations[{index}]: citation fields are empty"
            )
        if citation_id in citations:
            raise GreenfieldSourceDutyLedgerError(
                "compact citation IDs must be distinct"
            )
        if (quote, context) in pairs:
            raise GreenfieldSourceDutyLedgerError(
                "compact citation quote/context pairs must be distinct"
            )
        citation = {"quote": quote, "context": context}
        if evidence is not None:
            _check_citation(evidence, citation, f"citations[{index}]")
        citations[citation_id] = citation
        pairs.add((quote, context))

    used: set[str] = set()

    def resolve(ref: str, path: str) -> dict[str, str]:
        if ref not in citations:
            raise GreenfieldSourceDutyLedgerError(
                f"{path}: compact citation reference is unknown"
            )
        used.add(ref)
        return deepcopy(citations[ref])

    expanded = deepcopy(dict(value))
    expanded.pop("citations")
    expanded["version"] = SOURCE_DUTY_LEDGER_VERSION
    expanded["evidence_controls"] = []
    for index, control in enumerate(value["evidence_controls"]):
        citation = resolve(control["ref"], f"evidence_controls[{index}].ref")
        expanded["evidence_controls"].append(
            {**citation, "handling": control["handling"]}
        )
    for section in (
        "first_path_actions",
        "supporting_human_actions",
        "system_duties",
        "state_fields",
        "off_path_transitions",
        "conditional_guards",
        "boundaries",
        "proof_duties",
    ):
        expanded_rows: list[dict[str, Any]] = []
        for row_index, compact_row in enumerate(value[section]):
            row = deepcopy(compact_row)
            row["source_refs"] = [
                resolve(ref, f"{section}[{row_index}].source_refs[{ref_index}]")
                for ref_index, ref in enumerate(compact_row["source_refs"])
            ]
            if section in _ACTION_SECTIONS:
                for field in _ACTION_CITATION_FIELDS:
                    ref = compact_row[field]
                    row[field] = resolve(ref, f"{section}[{row_index}].{field}")
                row["role_refs"] = [
                    resolve(ref, f"{section}[{row_index}].role_refs[{ref_index}]")
                    for ref_index, ref in enumerate(compact_row["role_refs"])
                ]
                resolve_greenfield_action_actor_identity(
                    row, path=f"{section}[{row_index}]"
                )
            expanded_rows.append(row)
        expanded[section] = expanded_rows
    unused = set(citations) - used
    if unused and evidence is None:
        raise GreenfieldSourceDutyLedgerError(
            "compact citations must all be referenced"
        )
    resolve_greenfield_transition_state_fields(expanded)
    return expanded


__all__ = [
    "MAX_COMPACT_CITATIONS",
    "SOURCE_DUTY_COMPACT_VERSION",
    "expand_compact_source_duty_ledger",
    "greenfield_compact_source_duty_ledger_schema",
]
