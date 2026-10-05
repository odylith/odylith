"""Bind a source-duty ledger to one authored Greenfield candidate.

This gate checks custody, coverage, and references. It does not decide whether
an event or state field expresses the cited duty's meaning; that judgment must
be made before a candidate is sealed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    resolve_greenfield_transition_state_fields,
    verify_greenfield_source_duty_ledger_receipt,
)

SOURCE_DUTY_BINDING_VERSION = "odylith.greenfield.source-duty-binding.v3"
_FIRST_PATH_PERFORMER_FIELDS = {
    "human_actor": "human_actors",
    "internal_system": "internal_systems",
    "external_system": "external_systems",
    "product_title": "title",
}


class GreenfieldSourceDutyBindingError(ValueError):
    """A candidate has incomplete or invalid source-duty bindings."""


def _object(properties: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": deepcopy(dict(properties)),
    }


def greenfield_source_duty_binding_schema() -> dict[str, Any]:
    """Closed host shape for references into one validated ledger and candidate."""

    duty_id = {"type": "string", "minLength": 1, "maxLength": 4000}
    key = {"type": "string", "minLength": 1, "maxLength": 80}
    event_order = {"type": "integer", "minimum": 1, "maximum": 32}
    effect_index = {"type": "integer", "minimum": 1, "maximum": 8}
    digest = {"type": "string", "minLength": 64, "maxLength": 64}
    return _object(
        {
            "version": {"type": "string", "const": SOURCE_DUTY_BINDING_VERSION},
            "source_sha256": digest,
            "ledger_sha256": digest,
            "first_path_actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 24,
                "items": _object({"duty_id": duty_id, "event_order": event_order}),
            },
            "supporting_human_actions": {
                "type": "array",
                "maxItems": 24,
                "items": _object({"duty_id": duty_id, "event_order": event_order}),
            },
            "system_duties": {
                "type": "array",
                "maxItems": 32,
                "items": _object({"duty_id": duty_id, "event_order": event_order}),
            },
            "off_path_transitions": {
                "type": "array",
                "maxItems": 24,
                "items": _object(
                    {
                        "duty_id": duty_id,
                        "component_key": key,
                        "workstream_key": key,
                        "effects": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": _object(
                                {
                                    "effect_index": effect_index,
                                    "state_field_id": duty_id,
                                }
                            ),
                        },
                    }
                ),
            },
            **{
                role: {
                    "type": "array",
                    "maxItems": 32,
                    "items": _object(
                        {
                            "duty_id": duty_id,
                            "component_key": key,
                            "workstream_key": key,
                        }
                    ),
                }
                for role in ("conditional_guards", "boundaries", "proof_duties")
            },
        }
    )


def _closed(value: Any, fields: set[str], path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise GreenfieldSourceDutyBindingError(f"{path} has invalid fields")
    return value


def _rows(value: Any, *, maximum: int, minimum: int, path: str) -> Sequence[Any]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not minimum <= len(value) <= maximum
    ):
        raise GreenfieldSourceDutyBindingError(f"{path} has invalid rows")
    return value


def _text(value: Any, path: str, *, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise GreenfieldSourceDutyBindingError(f"{path} must be nonblank text")
    return value


def _event_order(value: Any, event_count: int) -> int:
    if type(value) is not int or not 1 <= value <= event_count:
        raise GreenfieldSourceDutyBindingError(
            "source duty references an unknown event"
        )
    return value


def _source_span(evidence: bytes, citation: Any) -> tuple[int, int]:
    try:
        canonical = canonical_citation_from_host_selection(evidence, citation)
        quote, start = resolve_source_citation(evidence, canonical)
    except GreenfieldModelAuthoringError as exc:
        raise GreenfieldSourceDutyBindingError(
            "bound event source citation is invalid"
        ) from exc
    return start, start + len(quote.encode("utf-8"))


def _role_event_orders(
    rows: Any,
    *,
    duties: Sequence[Mapping[str, Any]],
    events: Sequence[Any],
    evidence: bytes,
    facts: Mapping[str, Any],
    role: str,
    actor_fields: set[str],
) -> list[int]:
    rows = _rows(rows, minimum=len(duties), maximum=len(duties), path=role)
    orders: list[int] = []
    for row, duty in zip(rows, duties):
        row = _closed(row, {"duty_id", "event_order"}, f"{role} row")
        if row["duty_id"] != duty["id"]:
            raise GreenfieldSourceDutyBindingError(
                f"{role} bindings must cover the ledger in source order"
            )
        order = _event_order(row["event_order"], len(events))
        event = events[order - 1]
        if not isinstance(event, Mapping) or set(event) != {"actor_fact"}:
            raise GreenfieldSourceDutyBindingError("bound event is malformed")
        actor_fact = event.get("actor_fact")
        expected_actor_field = None
        if role == "first_path_actions":
            expected_actor_field = _FIRST_PATH_PERFORMER_FIELDS.get(
                duty.get("performer_role")
            )
        if (
            not isinstance(actor_fact, Mapping)
            or set(actor_fact) != {"field", "row"}
            or actor_fact.get("field") not in actor_fields
            or type(actor_fact.get("row")) is not int
            or (
                role == "first_path_actions"
                and actor_fact.get("field") != expected_actor_field
            )
        ):
            raise GreenfieldSourceDutyBindingError(
                f"{role} duty has an incompatible event actor"
            )
        actor_rows = facts.get(actor_fact["field"])
        if actor_fact["field"] == "title":
            actor_rows = [actor_rows]
        if (
            not isinstance(actor_rows, Sequence)
            or isinstance(actor_rows, (str, bytes, bytearray))
            or not 1 <= actor_fact["row"] <= len(actor_rows)
        ):
            raise GreenfieldSourceDutyBindingError(
                f"{role} duty references an unknown actor fact"
            )
        actor_start, actor_end = _source_span(
            evidence, actor_rows[actor_fact["row"] - 1]
        )
        duty_start, duty_end = _source_span(evidence, duty["actor_ref"])
        if actor_start != duty_start or actor_end != duty_end:
            raise GreenfieldSourceDutyBindingError(
                f"{role} duty actor differs from its source actor"
            )
        if order in orders:
            raise GreenfieldSourceDutyBindingError(
                f"{role} duties must bind distinct events"
            )
        orders.append(order)
    return orders


def _ordered_bindings(
    rows: Any,
    *,
    duties: Sequence[Mapping[str, Any]],
    events: Sequence[Any],
    evidence: bytes,
    facts: Mapping[str, Any],
) -> list[int]:
    orders = _role_event_orders(
        rows,
        duties=duties,
        events=events,
        evidence=evidence,
        facts=facts,
        role="first_path_actions",
        actor_fields={"human_actors", "internal_systems", "external_systems", "title"},
    )
    return orders


def _off_path_bindings(
    rows: Any,
    *,
    duties: Sequence[Mapping[str, Any]],
    field_ids: set[str],
    resolved_fields: Mapping[str, Sequence[Mapping[str, Any]]],
    components: Mapping[str, Any],
    workstreams: Mapping[str, Any],
) -> None:
    rows = _rows(
        rows, minimum=len(duties), maximum=len(duties), path="off_path_transitions"
    )
    for row, duty in zip(rows, duties):
        row = _closed(
            row,
            {"duty_id", "component_key", "workstream_key", "effects"},
            "off_path_transitions row",
        )
        if row["duty_id"] != duty["id"]:
            raise GreenfieldSourceDutyBindingError(
                "off-path bindings must cover the ledger in source order"
            )
        component = components.get(
            _text(row["component_key"], "component_key", maximum=80)
        )
        workstream = workstreams.get(
            _text(row["workstream_key"], "workstream_key", maximum=80)
        )
        if component is None or workstream is None:
            raise GreenfieldSourceDutyBindingError(
                "off-path duty has unknown design owner"
            )
        owner_keys = workstream.get("component_keys")
        if (
            not isinstance(owner_keys, Sequence)
            or isinstance(owner_keys, (str, bytes, bytearray))
            or component["key"] not in owner_keys
        ):
            raise GreenfieldSourceDutyBindingError(
                "off-path workstream does not own its component"
            )
        effects = _rows(
            row["effects"],
            minimum=len(duty["effects"]),
            maximum=len(duty["effects"]),
            path="off-path effects",
        )
        for index, effect in enumerate(effects, start=1):
            effect = _closed(
                effect, {"effect_index", "state_field_id"}, "effect binding"
            )
            if (
                type(effect["effect_index"]) is not int
                or effect["effect_index"] != index
            ):
                raise GreenfieldSourceDutyBindingError(
                    "off-path effects must cover the ledger in source order"
                )
            if effect["state_field_id"] not in field_ids:
                raise GreenfieldSourceDutyBindingError(
                    "off-path effect references an unknown state field"
                )
            if effect["state_field_id"] != resolved_fields[duty["id"]][index - 1]["id"]:
                raise GreenfieldSourceDutyBindingError(
                    "off-path effect is bound to a different state field"
                )


def _design_owner_bindings(
    rows: Any,
    *,
    duties: Sequence[Mapping[str, Any]],
    components: Mapping[str, Any],
    workstreams: Mapping[str, Any],
    role: str,
) -> None:
    """Require one typed design owner for every accepted source duty."""

    rows = _rows(rows, minimum=len(duties), maximum=len(duties), path=role)
    for row, duty in zip(rows, duties):
        row = _closed(
            row, {"duty_id", "component_key", "workstream_key"}, f"{role} row"
        )
        if row["duty_id"] != duty["id"]:
            raise GreenfieldSourceDutyBindingError(
                f"{role} bindings must cover the ledger in source order"
            )
        component_key = _text(row["component_key"], "component_key", maximum=80)
        workstream_key = _text(row["workstream_key"], "workstream_key", maximum=80)
        if component_key not in components or workstream_key not in workstreams:
            raise GreenfieldSourceDutyBindingError(
                f"{role} duty has unknown design owner"
            )
        owner_keys = workstreams[workstream_key].get("component_keys")
        if (
            not isinstance(owner_keys, Sequence)
            or isinstance(owner_keys, (str, bytes, bytearray))
            or component_key not in owner_keys
        ):
            raise GreenfieldSourceDutyBindingError(
                f"{role} workstream does not own its component"
            )


def validate_greenfield_source_duty_binding(
    binding: Mapping[str, Any],
    *,
    ledger_receipt: Mapping[str, Any],
    candidate_result: Mapping[str, Any],
    evidence_text: str,
) -> dict[str, Any]:
    """Return a detached binding after source custody and candidate checks pass."""

    try:
        receipt = verify_greenfield_source_duty_ledger_receipt(
            ledger_receipt, evidence_text=evidence_text
        )
    except GreenfieldSourceDutyLedgerError as exc:
        raise GreenfieldSourceDutyBindingError(
            "source duty receipt is invalid"
        ) from exc
    binding = _closed(
        binding,
        {
            "version",
            "source_sha256",
            "ledger_sha256",
            "first_path_actions",
            "supporting_human_actions",
            "system_duties",
            "off_path_transitions",
            "conditional_guards",
            "boundaries",
            "proof_duties",
        },
        "source duty binding",
    )
    if binding["version"] != SOURCE_DUTY_BINDING_VERSION:
        raise GreenfieldSourceDutyBindingError("source duty binding version is invalid")
    if (
        binding["source_sha256"] != receipt["source_sha256"]
        or binding["ledger_sha256"] != receipt["ledger_sha256"]
    ):
        raise GreenfieldSourceDutyBindingError("source duty binding digest mismatch")
    ledger = receipt["ledger"]
    if ledger["status"] != "inventory":
        raise GreenfieldSourceDutyBindingError("source duty inventory was not admitted")
    if (
        not isinstance(candidate_result, Mapping)
        or candidate_result.get("status") != "authored"
    ):
        raise GreenfieldSourceDutyBindingError(
            "source duty binding requires an authored candidate"
        )
    events = _rows(
        candidate_result.get("events"), minimum=1, maximum=32, path="candidate events"
    )
    facts = candidate_result.get("facts")
    if not isinstance(facts, Mapping):
        raise GreenfieldSourceDutyBindingError("candidate source facts are missing")
    design = candidate_result.get("provisional_design")
    if not isinstance(design, Mapping):
        raise GreenfieldSourceDutyBindingError(
            "candidate provisional design is missing"
        )
    first_run = design.get("first_run")
    if not isinstance(first_run, Mapping):
        raise GreenfieldSourceDutyBindingError("candidate first run is missing")
    expected_run = _ordered_bindings(
        binding["first_path_actions"],
        duties=ledger["first_path_actions"],
        events=events,
        evidence=evidence_text.encode("utf-8"),
        facts=facts,
    )
    supporting_orders = _role_event_orders(
        binding["supporting_human_actions"],
        duties=ledger["supporting_human_actions"],
        events=events,
        evidence=evidence_text.encode("utf-8"),
        facts=facts,
        role="supporting_human_actions",
        actor_fields={"human_actors"},
    )
    system_orders = _role_event_orders(
        binding["system_duties"],
        duties=ledger["system_duties"],
        events=events,
        evidence=evidence_text.encode("utf-8"),
        facts=facts,
        role="system_duties",
        actor_fields={"internal_systems", "external_systems", "title"},
    )
    role_orders = (set(expected_run), set(supporting_orders), set(system_orders))
    if any(
        left & right
        for index, left in enumerate(role_orders)
        for right in role_orders[index + 1 :]
    ) or set.union(*role_orders) != set(range(1, len(events) + 1)):
        raise GreenfieldSourceDutyBindingError(
            "candidate events must be covered by exactly one source-duty role"
        )
    first_run_orders = first_run.get("event_orders")
    if (
        not isinstance(first_run_orders, list)
        or any(type(order) is not int for order in first_run_orders)
        or first_run_orders != expected_run
    ):
        raise GreenfieldSourceDutyBindingError(
            "candidate first run must contain each bound first-path event exactly once in ledger workflow order"
        )
    terminal = candidate_result.get("terminal")
    if terminal is not None:
        if (
            not isinstance(terminal, Mapping)
            or type(terminal.get("event_order")) is not int
            or terminal["event_order"] not in expected_run
        ):
            raise GreenfieldSourceDutyBindingError(
                "candidate terminal is outside the first run"
            )
    validate_greenfield_source_duty_design_binding(
        binding, ledger=ledger, provisional_design=design,
    )
    return deepcopy(dict(binding))


def validate_greenfield_source_duty_design_binding(
    binding: Mapping[str, Any], *, ledger: Mapping[str, Any],
    provisional_design: Mapping[str, Any],
) -> None:
    """Validate passive duty identities and ownership against an accepted ledger.

    Raw candidate admission separately owns actor citations, event coverage and
    first-run selection. Exported lifecycle readback can reuse this design seam
    without constructing those omitted candidate records.
    """
    binding = _closed(
        binding, set(greenfield_source_duty_binding_schema()["required"]), "source duty binding",
    )
    if binding["version"] != SOURCE_DUTY_BINDING_VERSION:
        raise GreenfieldSourceDutyBindingError("source duty binding version is invalid")
    if not isinstance(provisional_design, Mapping):
        raise GreenfieldSourceDutyBindingError("candidate provisional design is missing")
    components = _rows(
        provisional_design.get("components"), minimum=1, maximum=5, path="components"
    )
    workstreams = _rows(
        provisional_design.get("workstreams"), minimum=1, maximum=5, path="workstreams"
    )
    if any(
        not isinstance(row, Mapping) or not isinstance(row.get("key"), str)
        for row in (*components, *workstreams)
    ):
        raise GreenfieldSourceDutyBindingError("candidate design owners are malformed")
    component_by_key = {row["key"]: row for row in components}
    workstream_by_key = {row["key"]: row for row in workstreams}
    if len(component_by_key) != len(components) or len(workstream_by_key) != len(
        workstreams
    ):
        raise GreenfieldSourceDutyBindingError(
            "candidate design owner keys are duplicated"
        )
    _off_path_bindings(
        binding["off_path_transitions"],
        duties=ledger["off_path_transitions"],
        field_ids={row["id"] for row in ledger["state_fields"]},
        resolved_fields=resolve_greenfield_transition_state_fields(ledger),
        components=component_by_key,
        workstreams=workstream_by_key,
    )
    for role in ("conditional_guards", "boundaries", "proof_duties"):
        _design_owner_bindings(
            binding[role],
            duties=ledger[role],
            components=component_by_key,
            workstreams=workstream_by_key,
            role=role,
        )


__all__ = [
    "GreenfieldSourceDutyBindingError",
    "SOURCE_DUTY_BINDING_VERSION",
    "greenfield_source_duty_binding_schema",
    "validate_greenfield_source_duty_binding",
    "validate_greenfield_source_duty_design_binding",
]
