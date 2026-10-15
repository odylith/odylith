"""Own inline inventory authoring and exact historical transport readback."""

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
    INLINE_SOURCE_DUTY_LEDGER_VERSION,
    ROSTER_SOURCE_DUTY_LEDGER_VERSION,
    PRODUCT_WIDE_SOURCE_DUTY_LEDGER_VERSION,
    _validate_shape,
    _check_citation,
    greenfield_source_duty_ledger_schema,
    preflight_greenfield_source_duty_ledger,
    resolve_greenfield_action_actor_identity,
    resolve_greenfield_transition_state_fields,
)

from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    ACTION_SECTIONS as _ACTION_SECTIONS,
    DUTY_SECTIONS,
    MAX_COMPACT_CITATIONS,
    SOURCE_DUTY_COMPACT_VERSION,
    PARTICIPANT_FIELDS,
)

_ACTION_CITATION_FIELDS = ("event_ref", "actor_ref")
SOURCE_DUTY_AUTHORING_VERSION = "odylith.greenfield.source-duty-authoring.v3"


def _citation_id_schema() -> dict[str, Any]:
    return {"type": "string", "maxLength": 32}


def _closed_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def _historical_compact_schema(*, _passive: bool = False, _roster: bool = False, _source_version: str | None = None) -> dict[str, Any]:
    """Read compiler citation banks under their exact retained ledger protocol."""

    schema = deepcopy(greenfield_source_duty_ledger_schema(
        _passive_source_version=_source_version if _roster else PRODUCT_WIDE_SOURCE_DUTY_LEDGER_VERSION if _passive else INLINE_SOURCE_DUTY_LEDGER_VERSION))
    properties = schema["properties"]
    properties["version"] = {
        "type": "string",
        "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
        "enum": [("odylith.greenfield.source-duty-compact.v8" if _source_version == ROSTER_SOURCE_DUTY_LEDGER_VERSION else SOURCE_DUTY_COMPACT_VERSION) if _roster else "odylith.greenfield.source-duty-compact.v6" if _passive else "odylith.greenfield.source-duty-compact.v7"],
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
    if _roster and _source_version is None:
        ordinary = properties["citations"]["items"]
        selected = deepcopy(ordinary)
        selected["required"].append("mention_ordinal")
        selected["properties"]["mention_ordinal"] = {"type": "integer", "minimum": 1,
                                                       "maximum": MAX_AUTHORED_FIELD_VALUE_CHARS}
        properties["citations"]["items"] = {"anyOf": [ordinary, selected]}
    properties["product_identity"]["anyOf"][0]["properties"]["source_ref"] = _citation_id_schema()
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
    if _roster:
        for field in PARTICIPANT_FIELDS:
            properties["nonperforming_participants"]["properties"][field]["items"] = _citation_id_schema()
    schema["required"] = ["citations", *schema["required"]]
    if _passive:
        return schema
    version = properties.pop("version")
    properties["status"]["enum"] = ["inventory"]
    properties["question"]["enum"] = [""]
    properties["product_identity"] = properties["product_identity"]["anyOf"][0]
    inventory = _closed_object(properties)
    clarification = _closed_object({
        "status": {"type": "string", "maxLength": 32, "enum": ["clarification_required"]},
        "question": {"type": "string", "minLength": 1, "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS},
    })
    return _closed_object({"version": version, "result": {"anyOf": [inventory, clarification]}})


def _expand_historical_compact_inventory(
    value: Mapping[str, Any],
    *,
    evidence_text: str | None = None,
    _passive: bool = False, _roster: bool = False, _source_version: str | None = None,
) -> dict[str, Any]:
    """Expand material rows; discard unused bank storage only after exact source checks."""

    _validate_shape(value, _historical_compact_schema(_passive=_passive, _roster=_roster, _source_version=_source_version), "ledger")
    if not _passive:
        value = value["result"]
        if value["status"] == "clarification_required":
            return _clarification_ledger(value["question"], version=(_source_version or SOURCE_DUTY_LEDGER_VERSION) if _roster else INLINE_SOURCE_DUTY_LEDGER_VERSION)
    evidence: bytes | None = None
    if evidence_text is not None:
        if not isinstance(evidence_text, str) or not evidence_text.strip():
            raise GreenfieldSourceDutyLedgerError("compact source evidence is empty")
        evidence = evidence_text.encode("utf-8")
        if len(evidence) > MAX_EVIDENCE_BYTES:
            raise GreenfieldSourceDutyLedgerError(
                "compact source evidence exceeds its bound"
            )
    citations: dict[str, dict[str, Any]] = {}
    pairs: set[tuple] = set()
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
        pair = (quote, context, *((entry["mention_ordinal"],) if "mention_ordinal" in entry else ()))
        if pair in pairs:
            raise GreenfieldSourceDutyLedgerError(
                "compact citation quote/context pairs must be distinct"
            )
        citation = {"quote": quote, "context": context,
                    **({"mention_ordinal": entry["mention_ordinal"]} if "mention_ordinal" in entry else {})}
        if evidence is not None:
            _check_citation(evidence, citation, f"citations[{index}]", mention_selection="mention_ordinal" in citation)
        citations[citation_id] = citation
        pairs.add(pair)

    used: set[str] = set()

    def resolve(ref: str, path: str) -> dict[str, Any]:
        if ref not in citations:
            raise GreenfieldSourceDutyLedgerError(
                f"{path}: compact citation reference is unknown"
            )
        used.add(ref)
        return deepcopy(citations[ref])

    expanded = deepcopy(dict(value))
    expanded.pop("citations")
    expanded["version"] = (_source_version or SOURCE_DUTY_LEDGER_VERSION) if _roster else PRODUCT_WIDE_SOURCE_DUTY_LEDGER_VERSION if _passive else INLINE_SOURCE_DUTY_LEDGER_VERSION
    if value["product_identity"] is not None:
        expanded["product_identity"]["source_ref"] = resolve(
            value["product_identity"]["source_ref"], "product_identity.source_ref")
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
    if _roster:
        expanded["nonperforming_participants"] = {
            field: [resolve(ref, f"nonperforming_participants.{field}[{index}]")
                    for index, ref in enumerate(value["nonperforming_participants"][field])]
            for field in PARTICIPANT_FIELDS}
    unused = set(citations) - used
    if unused and evidence is None:
        raise GreenfieldSourceDutyLedgerError(
            "compact citations must all be referenced"
        )
    if _roster and _source_version is None:
        _validate_shape(expanded, greenfield_source_duty_ledger_schema(), "ledger")
    resolve_greenfield_transition_state_fields(expanded)
    return expanded


def greenfield_source_duty_authoring_schema(*, _passive: bool = False, _passive_source_version: str | None = None) -> dict[str, Any]:
    """Use the material ledger's inline citation schema in one closed authoring envelope."""
    if _passive_source_version not in (None, ROSTER_SOURCE_DUTY_LEDGER_VERSION):
        raise GreenfieldSourceDutyLedgerError("passive authoring source version is invalid")
    properties = deepcopy(greenfield_source_duty_ledger_schema(
        _passive_source_version=INLINE_SOURCE_DUTY_LEDGER_VERSION if _passive else _passive_source_version)["properties"])
    version = properties.pop("version")
    version["enum"] = ["odylith.greenfield.source-duty-authoring.v1" if _passive else "odylith.greenfield.source-duty-authoring.v2" if _passive_source_version else SOURCE_DUTY_AUTHORING_VERSION]
    question = deepcopy(properties["question"])
    question["minLength"] = 1
    properties["status"]["enum"] = ["inventory"]
    properties["question"]["enum"] = [""]
    properties["product_identity"] = properties["product_identity"]["anyOf"][0]
    return _closed_object({
        "version": version,
        "result": {"anyOf": [
            _closed_object(properties),
            _closed_object({
                "status": {"type": "string", "maxLength": 32, "enum": ["clarification_required"]},
                "question": question,
            }),
        ]},
    })


def _clarification_ledger(question: str, *, version: str = SOURCE_DUTY_LEDGER_VERSION) -> dict[str, Any]:
    return {
        "version": version,
        **({"nonperforming_participants": {field: [] for field in ("human_actors", "internal_systems", "external_systems")}}
           if version in {SOURCE_DUTY_LEDGER_VERSION, ROSTER_SOURCE_DUTY_LEDGER_VERSION} else {}),
        "status": "clarification_required", "question": question,
        "product_identity": None, "evidence_controls": [],
        **{section: [] for section, _ in DUTY_SECTIONS},
    }


def decode_source_duty_inventory(
    value: Mapping[str, Any], *, evidence_text: str | None = None, _passive: bool = False,
) -> dict[str, Any]:
    """Decode one explicit wire version, leaving citation semantics with the ledger owner."""
    version = value.get("version") if isinstance(value, Mapping) else None
    if version in {SOURCE_DUTY_AUTHORING_VERSION, "odylith.greenfield.source-duty-authoring.v1", "odylith.greenfield.source-duty-authoring.v2"} and not _passive:
        historical_inline = version == "odylith.greenfield.source-duty-authoring.v1"
        passive_version = INLINE_SOURCE_DUTY_LEDGER_VERSION if historical_inline else ROSTER_SOURCE_DUTY_LEDGER_VERSION if version == "odylith.greenfield.source-duty-authoring.v2" else None
        source_version = passive_version or SOURCE_DUTY_LEDGER_VERSION
        _validate_shape(value, greenfield_source_duty_authoring_schema(_passive=historical_inline, _passive_source_version=ROSTER_SOURCE_DUTY_LEDGER_VERSION if passive_version == ROSTER_SOURCE_DUTY_LEDGER_VERSION else None), "ledger")
        result = value["result"]
        ledger = (_clarification_ledger(result["question"], version=source_version) if result["status"] == "clarification_required"
                  else {"version": source_version, **deepcopy(result)})
        if evidence_text is not None:
            return preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence_text,
                _passive_source_version=passive_version)["ledger"]
        for section in _ACTION_SECTIONS:
            for index, row in enumerate(ledger[section]):
                resolve_greenfield_action_actor_identity(row, path=f"{section}[{index}]")
        resolve_greenfield_transition_state_fields(ledger)
        return ledger
    if version == SOURCE_DUTY_COMPACT_VERSION and not _passive:
        return _expand_historical_compact_inventory(value, evidence_text=evidence_text, _roster=True)
    if version == "odylith.greenfield.source-duty-compact.v8" and not _passive:
        return _expand_historical_compact_inventory(value, evidence_text=evidence_text, _roster=True, _source_version=ROSTER_SOURCE_DUTY_LEDGER_VERSION)
    historical = "odylith.greenfield.source-duty-compact.v6" if _passive else "odylith.greenfield.source-duty-compact.v7"
    if version == historical:
        return _expand_historical_compact_inventory(value, evidence_text=evidence_text, _passive=_passive)
    raise GreenfieldSourceDutyLedgerError("source duty authoring version is invalid")


__all__ = [
    "SOURCE_DUTY_AUTHORING_VERSION",
    "decode_source_duty_inventory",
    "greenfield_source_duty_authoring_schema",
]
