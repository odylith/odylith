"""Validate a source-cited duty inventory before Greenfield candidate authoring."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    GreenfieldSourceDutyEntailmentError,
    source_duty_claims,
    source_duty_entailment_task,
    validate_source_duty_decision_set,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_FIELD_VALUE_CHARS,
    MAX_EVIDENCE_BYTES,
)

SOURCE_DUTY_LEDGER_VERSION = "odylith.greenfield.source-duty-ledger.v5"
SOURCE_DUTY_LEDGER_PREFLIGHT_VERSION = "odylith.greenfield.source-duty-preflight.v4"
SOURCE_DUTY_LEDGER_RECEIPT_VERSION = "odylith.greenfield.source-duty-ledger-receipt.v7"
MAX_SOURCE_DUTY_LEDGER_FILE_BYTES = 512 * 1024

_DUTY_SECTIONS: dict[str, tuple[int, tuple[str, ...]]] = {
    "first_path_actions": (24, ("action", "observable_result")),
    "supporting_human_actions": (24, ("action",)),
    "system_duties": (32, ("action",)),
    "state_fields": (32, ("state_object", "field", "meaning")),
    "off_path_transitions": (24, ("trigger", "governed_object", "effects")),
    "conditional_guards": (32, ("trigger", "protected_action", "rule")),
    "boundaries": (32, ("kind", "rule")),
    "proof_duties": (32, ("dossier_or_artifact", "must_show")),
}
_BOUNDARY_KINDS = ("authority", "scope", "privacy", "data_use")
_CONTROL_HANDLING = ("authoring_instruction", "reference_context")
_FIRST_PATH_PERFORMER_ROLES = (
    "human_actor",
    "internal_system",
    "external_system",
    "product_title",
)


class GreenfieldSourceDutyLedgerError(ValueError):
    """The inventory is malformed or cannot be bound to its evidence."""


def _text_schema(*, choices: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "string",
        "maxLength": MAX_AUTHORED_FIELD_VALUE_CHARS,
    }
    if choices:
        schema["enum"] = list(choices)
    return schema


def _object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def _array_schema(items: dict[str, Any], *, limit: int) -> dict[str, Any]:
    return {"type": "array", "maxItems": limit, "items": items}


def greenfield_source_duty_ledger_schema() -> dict[str, Any]:
    """Return the bounded, closed host schema for one source duty inventory."""

    citation = _object_schema({"quote": _text_schema(), "context": _text_schema()})
    source_refs = _array_schema(citation, limit=4)
    effects = _array_schema(
        _object_schema(
            {field: _text_schema() for field in ("field", "change", "observable_check")}
        ),
        limit=8,
    )
    properties: dict[str, Any] = {
        "version": _text_schema(choices=(SOURCE_DUTY_LEDGER_VERSION,)),
        "status": _text_schema(choices=("inventory", "clarification_required")),
        "question": _text_schema(),
        "evidence_controls": _array_schema(
            _object_schema(
                {
                    **citation["properties"],
                    "handling": _text_schema(choices=_CONTROL_HANDLING),
                }
            ),
            limit=16,
        ),
    }
    for section, (limit, fields) in _DUTY_SECTIONS.items():
        row = {"id": {"type": "string", "maxLength": 200}, "source_refs": source_refs}
        row.update(
            {
                field: effects if field == "effects" else _text_schema()
                for field in fields
            }
        )
        if section in {
            "first_path_actions",
            "supporting_human_actions",
            "system_duties",
        }:
            row.update(
                {
                    "statement": _text_schema(),
                    "event_ref": citation,
                    "actor_ref": citation,
                    "target": _text_schema(),
                    "role_refs": source_refs,
                }
            )
        if section == "first_path_actions":
            row["performer_role"] = _text_schema(choices=_FIRST_PATH_PERFORMER_ROLES)
        if section == "boundaries":
            row["kind"] = _text_schema(choices=_BOUNDARY_KINDS)
        properties[section] = _array_schema(_object_schema(row), limit=limit)
    return _object_schema(properties)


def _validate_shape(value: Any, schema: Mapping[str, Any], path: str) -> None:
    if "anyOf" in schema:
        if value is None:
            return
        _validate_shape(value, schema["anyOf"][0], path)
        return
    kind = schema["type"]
    if kind == "object":
        properties = schema["properties"]
        if not isinstance(value, dict) or set(value) != set(properties):
            raise GreenfieldSourceDutyLedgerError(f"{path}: object fields are invalid")
        for name, child in properties.items():
            _validate_shape(value[name], child, f"{path}.{name}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) > schema["maxItems"]:
            raise GreenfieldSourceDutyLedgerError(
                f"{path}: array is invalid or too large"
            )
        for index, child in enumerate(value):
            _validate_shape(child, schema["items"], f"{path}[{index}]")
    elif (
        not isinstance(value, str)
        or len(value) > schema["maxLength"]
        or ("enum" in schema and value not in schema["enum"])
    ):
        raise GreenfieldSourceDutyLedgerError(f"{path}: text is invalid")


def _require_text(value: str, path: str) -> None:
    if not value.strip():
        raise GreenfieldSourceDutyLedgerError(f"{path}: text is empty")


def _check_citation(evidence: bytes, citation: Mapping[str, str], path: str) -> None:
    _require_text(citation["quote"], f"{path}.quote")
    _require_text(citation["context"], f"{path}.context")
    try:
        canonical_citation_from_host_selection(
            evidence,
            {"quote": citation["quote"], "context": citation["context"]},
        )
    except GreenfieldModelAuthoringError as exc:
        raise GreenfieldSourceDutyLedgerError(
            f"{path}: source citation is invalid"
        ) from exc


def _citation_span(evidence: bytes, citation: Mapping[str, str]) -> tuple[int, int]:
    canonical = canonical_citation_from_host_selection(evidence, citation)
    quote, start = resolve_source_citation(evidence, canonical)
    return start, start + len(quote.encode("utf-8"))


def _within_cited_span(
    evidence: bytes, start: int, end: int, citations: list[Mapping[str, str]]
) -> bool:
    return any(
        ref_start <= start < end <= ref_end
        for ref_start, ref_end in (
            _citation_span(evidence, citation) for citation in citations
        )
    )


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_greenfield_action_actor_identity(
    row: Mapping[str, Any], *, path: str
) -> str:
    """Retain the source identity inside its normalized action statement.

    Literal containment establishes custody, not that the quote names one
    performer. The source-only verifier owns that semantic judgment.
    """
    actor = row["actor_ref"]["quote"]
    statement = row["statement"]
    if not actor.strip() or actor == statement or actor not in statement:
        raise GreenfieldSourceDutyLedgerError(
            f"{path}: actor identity must be a proper exact statement slice"
        )
    return actor


def resolve_greenfield_transition_state_fields(
    ledger: Mapping[str, Any],
) -> dict[str, tuple[Mapping[str, Any], ...]]:
    """Resolve each ordered effect by its exact object and canonical field label."""
    by_identity: dict[tuple[str, str], Mapping[str, Any]] = {}
    for field in ledger["state_fields"]:
        identity = (field["state_object"], field["field"])
        if identity in by_identity:
            raise GreenfieldSourceDutyLedgerError("state-field object and field identities must be unique")
        by_identity[identity] = field
    resolved: dict[str, tuple[Mapping[str, Any], ...]] = {}
    for transition_index, transition in enumerate(ledger["off_path_transitions"]):
        fields: list[Mapping[str, Any]] = []
        for index, effect in enumerate(transition["effects"], start=1):
            identity = (transition["governed_object"], effect["field"])
            if identity not in by_identity:
                raise GreenfieldSourceDutyLedgerError(
                    f"off_path_transitions[{transition_index}].effects[{index - 1}]: no declared state-field identity"
                )
            fields.append(by_identity[identity])
        resolved[transition["id"]] = tuple(fields)
    return resolved


def preflight_greenfield_source_duty_ledger(
    ledger: Mapping[str, Any], *, evidence_text: str
) -> dict[str, Any]:
    """Bind exact citations without claiming semantic admission.

    The returned claims are inputs to an independent source-only action verifier.
    Citation and hash checks cannot establish that an action is entailed.
    """

    if not isinstance(evidence_text, str) or not evidence_text.strip():
        raise GreenfieldSourceDutyLedgerError("source evidence is empty")
    evidence = evidence_text.encode("utf-8")
    if len(evidence) > MAX_EVIDENCE_BYTES:
        raise GreenfieldSourceDutyLedgerError(
            "source evidence exceeds the declared bound"
        )
    _validate_shape(ledger, greenfield_source_duty_ledger_schema(), "ledger")

    seen_ids: set[str] = set()
    seen_action_atoms: set[tuple[int, int, int, int, str, str]] = set()
    reference_spans: list[tuple[int, int]] = []
    for index, control in enumerate(ledger["evidence_controls"]):
        _check_citation(evidence, control, f"evidence_controls[{index}]")
        if control["handling"] == "reference_context":
            reference_spans.append(
                _citation_span(
                    evidence, {"quote": control["quote"], "context": control["context"]}
                )
            )
    for section, (_, fields) in _DUTY_SECTIONS.items():
        for index, row in enumerate(ledger[section]):
            path = f"{section}[{index}]"
            _require_text(row["id"], f"{path}.id")
            if row["id"] in seen_ids:
                raise GreenfieldSourceDutyLedgerError(
                    "source duty IDs must be distinct"
                )
            seen_ids.add(row["id"])
            if (
                section
                not in {
                    "first_path_actions",
                    "supporting_human_actions",
                    "system_duties",
                }
                and not row["source_refs"]
            ):
                raise GreenfieldSourceDutyLedgerError(
                    f"{path}: source citations are empty"
                )
            for ref_index, citation in enumerate(row["source_refs"]):
                _check_citation(evidence, citation, f"{path}.source_refs[{ref_index}]")
            if section in {
                "first_path_actions",
                "supporting_human_actions",
                "system_duties",
            }:
                _require_text(row["statement"], f"{path}.statement")
                for ref_field in ("event_ref", "actor_ref"):
                    _check_citation(evidence, row[ref_field], f"{path}.{ref_field}")
                if not row["role_refs"]:
                    raise GreenfieldSourceDutyLedgerError(
                        f"{path}: role citations are empty"
                    )
                for ref_index, citation in enumerate(row["role_refs"]):
                    _check_citation(
                        evidence, citation, f"{path}.role_refs[{ref_index}]"
                    )
                event_start, event_end = _citation_span(evidence, row["event_ref"])
                if any(
                    event_start < reference_end and reference_start < event_end
                    for reference_start, reference_end in reference_spans
                ):
                    raise GreenfieldSourceDutyLedgerError(
                        f"{path}: source event overlaps reference-only context"
                    )
                actor_start, actor_end = _citation_span(evidence, row["actor_ref"])
                if not event_start <= actor_start < actor_end <= event_end:
                    if not _within_cited_span(
                        evidence,
                        actor_start,
                        actor_end,
                        row["source_refs"] + row["role_refs"],
                    ):
                        raise GreenfieldSourceDutyLedgerError(
                            f"{path}: external actor citation must be a duty or role reference"
                        )
                    if any(
                        actor_start < reference_end and reference_start < actor_end
                        for reference_start, reference_end in reference_spans
                    ):
                        raise GreenfieldSourceDutyLedgerError(
                            f"{path}: actor citation overlaps reference-only context"
                        )
                _require_text(row["action"], f"{path}.action")
                resolve_greenfield_action_actor_identity(row, path=path)
                for field in ("action", "target"):
                    if row[field] and row[field] not in row["statement"]:
                        raise GreenfieldSourceDutyLedgerError(
                            f"{path}: normalized {field} must be an exact statement slice"
                        )
                atom = (
                    event_start,
                    event_end,
                    actor_start,
                    actor_end,
                    row["action"],
                    row["target"],
                )
                if atom in seen_action_atoms:
                    raise GreenfieldSourceDutyLedgerError(
                        f"{path}: source action atom is duplicated"
                    )
                seen_action_atoms.add(atom)
            for field in fields:
                if field != "effects":
                    _require_text(row[field], f"{path}.{field}")
            if section == "off_path_transitions":
                if not row["effects"]:
                    raise GreenfieldSourceDutyLedgerError(f"{path}: effects are empty")
                for effect_index, effect in enumerate(row["effects"]):
                    for field, value in effect.items():
                        _require_text(value, f"{path}.effects[{effect_index}].{field}")

    if ledger["status"] == "clarification_required":
        _require_text(ledger["question"], "ledger.question")
        if seen_ids or ledger["evidence_controls"]:
            raise GreenfieldSourceDutyLedgerError(
                "clarification must carry no inventory"
            )
    elif ledger["question"].strip() or not ledger["first_path_actions"]:
        raise GreenfieldSourceDutyLedgerError(
            "inventory requires first-path actions and no question"
        )

    resolve_greenfield_transition_state_fields(ledger)
    accepted = deepcopy(dict(ledger))
    source_sha256 = hashlib.sha256(evidence).hexdigest()
    return {
        "version": SOURCE_DUTY_LEDGER_PREFLIGHT_VERSION,
        "source_sha256": source_sha256,
        "ledger_sha256": _canonical_sha256(accepted),
        "claims": source_duty_claims(accepted, source_sha256=source_sha256),
        "ledger": accepted,
    }


def validate_greenfield_source_duty_ledger(
    ledger: Mapping[str, Any], *, evidence_text: str, decision_set: Mapping[str, Any]
) -> dict[str, Any]:
    """Admit only complete, source-bound affirmative action decisions."""

    preflight = preflight_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence_text
    )
    if ledger["status"] != "inventory":
        raise GreenfieldSourceDutyLedgerError(
            "clarification cannot receive an admission receipt"
        )
    verifier_task_sha256 = source_duty_entailment_task(
        preflight, evidence_text=evidence_text
    )["verifier_task_sha256"]
    try:
        accepted_decisions = validate_source_duty_decision_set(
            decision_set,
            claims=preflight["claims"],
            source_sha256=preflight["source_sha256"],
            verifier_task_sha256=verifier_task_sha256,
            evidence_text=evidence_text,
        )
    except GreenfieldSourceDutyEntailmentError as exc:
        raise GreenfieldSourceDutyLedgerError(str(exc)) from exc
    return {
        "version": SOURCE_DUTY_LEDGER_RECEIPT_VERSION,
        "source_sha256": preflight["source_sha256"],
        "ledger_sha256": preflight["ledger_sha256"],
        "verifier_task_sha256": verifier_task_sha256,
        "decision_set_sha256": _canonical_sha256(accepted_decisions),
        "ledger": preflight["ledger"],
        "decision_set": accepted_decisions,
    }


def verify_greenfield_source_duty_ledger_receipt(
    receipt: Mapping[str, Any], *, evidence_text: str
) -> dict[str, Any]:
    """Revalidate custody when a prior ledger receipt enters admission."""

    if not isinstance(receipt, Mapping) or set(receipt) != {
        "version",
        "source_sha256",
        "ledger_sha256",
        "verifier_task_sha256",
        "decision_set_sha256",
        "ledger",
        "decision_set",
    }:
        raise GreenfieldSourceDutyLedgerError("source duty ledger receipt is malformed")
    if receipt["version"] != SOURCE_DUTY_LEDGER_RECEIPT_VERSION:
        raise GreenfieldSourceDutyLedgerError(
            "source duty ledger receipt version is invalid"
        )
    if (
        not isinstance(evidence_text, str)
        or receipt["source_sha256"]
        != hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
    ):
        raise GreenfieldSourceDutyLedgerError(
            "source duty ledger receipt hash is invalid"
        )
    expected = validate_greenfield_source_duty_ledger(
        receipt["ledger"],
        evidence_text=evidence_text,
        decision_set=receipt["decision_set"],
    )
    if dict(receipt) != expected:
        raise GreenfieldSourceDutyLedgerError(
            "source duty ledger receipt hash is invalid"
        )
    return expected


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise GreenfieldSourceDutyLedgerError(
                "source duty JSON contains duplicate object keys"
            )
        value[key] = item
    return value


def load_greenfield_source_duty_file(path: Path) -> dict[str, Any]:
    """Load one bounded untrusted ledger or receipt JSON file."""

    try:
        with Path(path).expanduser().open("rb") as handle:
            payload = handle.read(MAX_SOURCE_DUTY_LEDGER_FILE_BYTES + 1)
    except OSError as exc:
        raise RuntimeError(
            "environment/IO failure while reading source duty ledger"
        ) from exc
    if len(payload) > MAX_SOURCE_DUTY_LEDGER_FILE_BYTES:
        raise GreenfieldSourceDutyLedgerError(
            "source duty ledger exceeds its input bound"
        )
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique_json_object
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GreenfieldSourceDutyLedgerError(
            "source duty ledger must be UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise GreenfieldSourceDutyLedgerError(
            "source duty ledger must be a JSON object"
        )
    return value


__all__ = [
    "GreenfieldSourceDutyLedgerError",
    "SOURCE_DUTY_LEDGER_PREFLIGHT_VERSION",
    "SOURCE_DUTY_LEDGER_RECEIPT_VERSION",
    "SOURCE_DUTY_LEDGER_VERSION",
    "MAX_SOURCE_DUTY_LEDGER_FILE_BYTES",
    "greenfield_source_duty_ledger_schema",
    "load_greenfield_source_duty_file",
    "preflight_greenfield_source_duty_ledger",
    "resolve_greenfield_action_actor_identity",
    "resolve_greenfield_transition_state_fields",
    "validate_greenfield_source_duty_ledger",
    "verify_greenfield_source_duty_ledger_receipt",
]
