"""Bind a source-duty ledger to one authored Greenfield candidate.

This gate checks custody, coverage, and references. It does not decide whether
an event or state field expresses the cited duty's meaning; that judgment must
be made before a candidate is sealed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_event_ordering import validate_first_run
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    canonical_citation_from_source_span,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    SOURCE_DUTY_LEDGER_VERSION,
    resolve_greenfield_transition_state_fields,
    verify_greenfield_source_duty_ledger_receipt,
)

SOURCE_DUTY_BINDING_VERSION = "odylith.greenfield.source-duty-binding.v3"
HOST_SOURCE_DUTY_BINDING_VERSION = "odylith.greenfield.source-duty-binding.v4"
_ACTION_SECTIONS = ("first_path_actions", "supporting_human_actions", "system_duties")
_FIRST_PATH_PERFORMER_FIELDS = {
    "human_actor": "human_actors",
    "internal_system": "internal_systems",
    "external_system": "external_systems",
    "product_title": "title",
    "product_wide": "product_identity",
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


def greenfield_source_duty_binding_schema(*, host: bool = False) -> dict[str, Any]:
    """Closed host shape for references into one validated ledger and candidate."""

    duty_id = {"type": "string", "minLength": 1, "maxLength": 4000}
    key = {"type": "string", "minLength": 1, "maxLength": 80}
    event_order = {"type": "integer", "minimum": 1, "maximum": 32}
    effect_index = {"type": "integer", "minimum": 1, "maximum": 8}
    digest = {"type": "string", "minLength": 64, "maxLength": 64}
    schema = _object(
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
    if host:
        schema["properties"]["version"]["const"] = HOST_SOURCE_DUTY_BINDING_VERSION
        for section in _ACTION_SECTIONS:
            schema["properties"].pop(section)
            schema["required"].remove(section)
    return schema


def project_greenfield_source_event_catalog(
    receipt: Mapping[str, Any], *, evidence_text: str, _passive: bool = False,
) -> dict[str, Any]:
    """Freeze every verified action ID and exact performer before candidate authoring."""
    verified = verify_greenfield_source_duty_ledger_receipt(
        receipt, evidence_text=evidence_text, allow_legacy_edit=(_passive or receipt.get("version") in {
            "odylith.greenfield.source-duty-ledger-receipt.v16", "odylith.greenfield.source-duty-ledger-receipt.v17"}),
    )
    evidence = evidence_text.encode("utf-8")
    facts: dict[str, Any] = {"human_actors": [], "internal_systems": [], "external_systems": [], "title": None}
    independent_identity = verified["ledger"]["version"] in {SOURCE_DUTY_LEDGER_VERSION, "odylith.greenfield.source-duty-ledger.v7", "odylith.greenfield.source-duty-ledger.v8"}
    if independent_identity:
        facts["title"] = deepcopy(verified["ledger"]["product_identity"]["source_ref"])
    identity_span = _source_span(evidence, facts["title"]) if independent_identity else None
    performers: list[dict[str, Any]] = []
    identities: dict[tuple[str, int, int], dict[str, Any]] = {}
    kinds_by_span: dict[tuple[int, int], set[str]] = {}
    events: list[dict[str, Any]] = []
    actions: dict[int, dict[str, Any]] = {}
    bindings: dict[str, list[dict[str, Any]]] = {section: [] for section in _ACTION_SECTIONS}
    for section in _ACTION_SECTIONS:
        for duty in verified["ledger"][section]:
            role = "human_actor" if section == "supporting_human_actions" else duty["performer_role"]
            if independent_identity and role == "product_title":
                raise GreenfieldSourceDutyBindingError("product identity cannot own an action performer")
            field = _FIRST_PATH_PERFORMER_FIELDS[role]
            start, end = _source_span(evidence, duty["actor_ref"])
            if independent_identity and role not in {"internal_system", "product_wide"} and (start, end) == identity_span:
                raise GreenfieldSourceDutyBindingError("product identity has an incompatible source performer kind")
            roles = kinds_by_span.setdefault((start, end), set())
            if roles and role not in roles and (independent_identity or roles | {role} != {"internal_system", "product_title"}):
                raise GreenfieldSourceDutyBindingError("source performer has conflicting verified kinds")
            roles.add(role)
            identity = (role, start, end)
            actor = identities.get(identity)
            if actor is None:
                if field == "product_identity":
                    row = 1
                elif field == "title":
                    if facts["title"] is not None:
                        raise GreenfieldSourceDutyBindingError("source duties name distinct product-title performers")
                    facts["title"] = deepcopy(duty["actor_ref"])
                    row = 1
                else:
                    facts[field].append(deepcopy(duty["actor_ref"]))
                    row = len(facts[field])
                actor = {
                    "field": field, "row": row,
                    "path": f"/{field}" if field in {"title", "product_identity"} else f"/{field}/{row - 1}",
                    "performer_role": role, "duty_id": duty["id"],
                    "quote": duty["actor_ref"]["quote"],
                    "source_start_byte": start, "source_end_byte": end,
                }
                identities[identity] = actor
                performers.append(actor)
            order = len(events) + 1
            if order > 32:
                raise GreenfieldSourceDutyBindingError("source action duties exceed the existing event bound")
            events.append({
                "event_order": order, "binding_role": section, "duty_id": duty["id"],
                "actor_fact": {"field": field, "row": actor["row"]},
                "actor_fact_path": actor["path"], "performer_role": role,
                "actor_start_byte": start, "actor_end_byte": end,
            })
            actions[order] = {**deepcopy(dict(duty)), **events[-1]}
            bindings[section].append({"duty_id": duty["id"], "event_order": order})
    # The declared title/internal-system alias is one exact source identity.
    for event in events:
        if not independent_identity and event["performer_role"] == "product_title":
            alias = identities.get(("internal_system", event["actor_start_byte"], event["actor_end_byte"]))
            if alias is not None:
                event["actor_fact_path"] = alias["path"]
                actions[event["event_order"]]["actor_fact_path"] = alias["path"]
    return {"facts": facts, "independent_product_identity": independent_identity, "performers": performers, "events": events, "actions": actions,
            "action_bindings": bindings}


def source_owned_greenfield_actor_facts(
    catalog: Mapping[str, Any], *, supplemental: Mapping[str, Any], evidence_text: str,
    ledger_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Keep source performers first; supplemental facts cannot select an event actor."""
    facts = deepcopy(dict(supplemental))
    evidence = evidence_text.encode("utf-8")
    context = ledger_receipt.get("edit_preservation") if ledger_receipt is not None else None
    conserved = isinstance(context, Mapping) and context.get("version") == "odylith.greenfield.edit-lifecycle-preservation.v4"
    if conserved:
        from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import mapped_prior_source_span, UNSUPPORTED_SYSTEM_MUTATION
        for field, atoms in context["prior_system_facts"].items():
            prior_spans = {mapped_prior_source_span(context, atom["source_span_refs"][0], evidence_text=evidence_text) for atom in atoms}
            for other in {"internal_systems", "external_systems"} - {field}:
                if any(_source_span(evidence, citation) in prior_spans for citation in catalog["facts"][other]):
                    raise GreenfieldSourceDutyBindingError(UNSUPPORTED_SYSTEM_MUTATION)
    for field, prefix in catalog["facts"].items():
        raw = supplemental.get(field)
        if field == "title":
            if field in supplemental:
                raise GreenfieldSourceDutyBindingError("candidate must not author the source-owned product identity")
            facts[field] = deepcopy(prefix)
            continue
        rows = _rows(raw, minimum=0, maximum=32, path=f"supplemental {field}")
        facts[field] = deepcopy(prefix)
        seen = {_source_span(evidence, row) for row in prefix}
        prior = []
        if conserved and field in {"internal_systems", "external_systems"}:
            from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import mapped_prior_source_span, UNSUPPORTED_SYSTEM_MUTATION
            for atom in context["prior_system_facts"][field]:
                for link in atom["projection_links"]:
                    if link["field"] == field and link["relation_order"] == 0:
                        start, end = mapped_prior_source_span(context, atom["source_span_refs"][0], evidence_text=evidence_text)
                        prior.append((link["path"], (start, end), canonical_citation_from_source_span(evidence, start=start, end=end)))
            prior.sort(key=lambda row: int(row[0].rsplit("/", 1)[1]))
        for citation in rows:
            span = _source_span(evidence, citation)
            if conserved and field in {"internal_systems", "external_systems"}:
                if span not in seen and span not in {row[1] for row in prior}:
                    raise GreenfieldSourceDutyBindingError(UNSUPPORTED_SYSTEM_MUTATION)
                continue
            existing = [actor for actor in catalog["performers"]
                        if (actor["source_start_byte"], actor["source_end_byte"]) == span]
            if existing and not any(actor["field"] == field for actor in existing):
                raise GreenfieldSourceDutyBindingError("supplemental actor has an incompatible source performer kind")
            if span not in seen:
                facts[field].append(deepcopy(citation))
                seen.add(span)
        for _, span, citation in prior:
            if span not in seen:
                facts[field].append(citation)
                seen.add(span)
        if len(facts[field]) > 32:
            raise GreenfieldSourceDutyBindingError("source and supplemental actors exceed the existing bound")
    return facts


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
    fresh = receipt["ledger"]["version"] == SOURCE_DUTY_LEDGER_VERSION
    host = isinstance(binding, Mapping) and binding.get("version") == HOST_SOURCE_DUTY_BINDING_VERSION
    binding = _closed(binding, set(greenfield_source_duty_binding_schema(host=host)["required"]), "source duty binding")
    if binding["version"] != (HOST_SOURCE_DUTY_BINDING_VERSION if host else SOURCE_DUTY_BINDING_VERSION) or (host and not fresh):
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
    if fresh:
        if "events" in candidate_result:
            raise GreenfieldSourceDutyBindingError("fresh candidate must not author source events or actors")
        catalog = project_greenfield_source_event_catalog(receipt, evidence_text=evidence_text)
        events = catalog["events"]
        if not host and any(binding[section] != rows for section, rows in catalog["action_bindings"].items()):
            raise GreenfieldSourceDutyBindingError("canonical action bindings differ from the source-owned event catalog")
        binding = {**binding, "version": SOURCE_DUTY_BINDING_VERSION, **catalog["action_bindings"]}
        expected_run, supporting_orders, system_orders = (
            [row["event_order"] for row in binding[section]] for section in _ACTION_SECTIONS
        )
    else:
        events = _rows(candidate_result.get("events"), minimum=1, maximum=32, path="candidate events")
        expected_run = _ordered_bindings(
            binding["first_path_actions"], duties=ledger["first_path_actions"], events=events,
            evidence=evidence_text.encode("utf-8"), facts=facts,
        )
        supporting_orders = _role_event_orders(
            binding["supporting_human_actions"], duties=ledger["supporting_human_actions"], events=events,
            evidence=evidence_text.encode("utf-8"), facts=facts,
            role="supporting_human_actions", actor_fields={"human_actors"},
        )
        system_orders = _role_event_orders(
            binding["system_duties"], duties=ledger["system_duties"], events=events,
            evidence=evidence_text.encode("utf-8"), facts=facts,
            role="system_duties", actor_fields={"internal_systems", "external_systems", "title"},
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
    try:
        validate_first_run(
            first_run,
            event_orders=tuple(range(1, len(events) + 1)),
            source_precedence=candidate_result.get("source_precedence", ()),
            result_event_order=None,
            first_path_event_orders=expected_run,
            recurring_event_orders=recurring_source_event_orders(ledger, binding),
        )
    except ValueError as exc:
        raise GreenfieldSourceDutyBindingError(
            "candidate first run must preserve ledger workflow order and contain each "
            "bound first-path event and its cited source prerequisites exactly once: "
            f"{exc}"
        ) from exc
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
        binding, ledger=ledger, provisional_design=design, ledger_receipt=receipt,
    )
    return deepcopy(dict(binding))


def validate_greenfield_source_duty_design_binding(
    binding: Mapping[str, Any], *, ledger: Mapping[str, Any],
    provisional_design: Mapping[str, Any], ledger_receipt: Mapping[str, Any] | None = None,
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
    if ledger_receipt is not None:
        require_preserved_source_duty_owners(binding, ledger_receipt, provisional_design=provisional_design)
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


def recurring_source_event_orders(ledger: Mapping[str, Any], binding: Mapping[str, Any]) -> tuple[int, ...]:
    """Map source-owned recurrence to stable event identities, never infer it from text."""
    if ledger["version"] != SOURCE_DUTY_LEDGER_VERSION:
        return ()
    recurring = {row["id"] for row in ledger["system_duties"]
                 if row["execution_kind"] == "recurring_invariant"}
    return tuple(row["event_order"] for row in binding["system_duties"] if row["duty_id"] in recurring)


def require_preserved_source_duty_owners(binding: Mapping[str, Any], receipt: Mapping[str, Any], *, provisional_design: Mapping[str, Any] | None = None) -> None:
    """Preserved EDIT duties retain their authenticated allocation keys exactly."""
    context = receipt.get("edit_preservation")
    if not isinstance(context, Mapping) or context.get("version") not in {"odylith.greenfield.edit-lifecycle-preservation.v3", "odylith.greenfield.edit-lifecycle-preservation.v4"}:
        return
    decisions = receipt["decision_set"]["edit_preservation"]
    for role in ("off_path_transitions", "conditional_guards", "boundaries", "proof_duties"):
        for prior in context["prior_lifecycle"][role]:
            decision = decisions[f"{role}/{prior['duty_id']}"]
            if decision["verdict"] != "preserved":
                continue
            current = next((row for row in binding[role]
                            if row["duty_id"] == decision["current_duty_id"]), None)
            if current is None or any(current[key] != prior[key] for key in ("component_key", "workstream_key")):
                raise GreenfieldSourceDutyBindingError("preserved source duty must retain its prior component and workstream allocation")
    if context["version"] == "odylith.greenfield.edit-lifecycle-preservation.v4":
        if provisional_design is None:
            raise GreenfieldSourceDutyBindingError("EDIT action allocation requires the complete current design")
        for role in _ACTION_SECTIONS:
            current = {row["duty_id"]: row["event_order"] for row in binding[role]}
            for prior in context["prior_actions"][role]:
                decision = decisions[f"{role}/{prior['duty']['id']}"]
                if decision["verdict"] == "removed":
                    continue
                order = current.get(decision["current_duty_id"])
                if order is None or source_action_allocation_relations(provisional_design, order) != prior["allocation_relations"]:
                    raise GreenfieldSourceDutyBindingError("Surviving source actions must retain every prior component/workstream allocation relation; no project records were created.")


def source_action_allocation_relations(design: Mapping[str, Any], event_order: int) -> list[dict[str, Any]]:
    """Retain component support, workstream edges and both verification flags."""
    return sorted([
        {"component_key": component["key"], "workstream_key": workstream["key"],
         "component_verifies": event_order in component["verification_event_orders"],
         "workstream_verifies": event_order in workstream["verification_event_orders"]}
        for component in design["components"] if event_order in component["supported_event_orders"]
        for workstream in design["workstreams"] if component["key"] in workstream["component_keys"]
    ], key=lambda row: (row["component_key"], row["workstream_key"], row["component_verifies"], row["workstream_verifies"]))


__all__ = [
    "GreenfieldSourceDutyBindingError",
    "SOURCE_DUTY_BINDING_VERSION",
    "HOST_SOURCE_DUTY_BINDING_VERSION",
    "greenfield_source_duty_binding_schema",
    "project_greenfield_source_event_catalog",
    "source_owned_greenfield_actor_facts",
    "validate_greenfield_source_duty_binding",
    "validate_greenfield_source_duty_design_binding",
]
