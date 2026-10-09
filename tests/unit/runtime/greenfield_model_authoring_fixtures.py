"""Shared complete-host-candidate fixtures for Greenfield authoring tests."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_intent_fact_values import (
    TERMINAL_RESULT_FACT_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    _REPEATED_SOURCE_FIELDS,
    _SINGULAR_SOURCE_FIELDS,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
    HOST_SOURCE_DUTY_BINDING_FIELD,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    prepare_model_authoring_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
    resolve_source_citation,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    HOST_SOURCE_DUTY_BINDING_VERSION,
    validate_greenfield_source_duty_binding,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_VERSION,
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    SOURCE_DUTY_DECISION_SET_VERSION,
    source_duty_entailment_task,
)


class _FixtureHostCandidate(dict):
    """Keep test source atoms beside, never inside, the public candidate JSON."""

    source_action_atoms: list[dict[str, Any]]


_SERIALIZED_FIXTURE_ATOMS: dict[str, list[dict[str, Any]]] = {}


def _fixture_candidate_key(candidate: Mapping[str, Any]) -> str:
    return json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fixture_actor_ref(facts: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, str]:
    address = event["actor_fact"]
    field = address["field"]
    value = facts.get(field)
    if field == "title" and isinstance(value, Mapping):
        return copy.deepcopy(value)
    if (
        isinstance(value, list)
        and type(address.get("row")) is int
        and 1 <= address["row"] <= len(value)
    ):
        return copy.deepcopy(value[address["row"] - 1])
    # Keep malformed actor addresses in the candidate so admission owns the
    # expected denial; a test ledger still needs one valid source citation.
    return copy.deepcopy(facts["title"])


def _fixture_action_refs(atom: Mapping[str, Any]) -> list[dict[str, str]]:
    if atom["actor_ref"] != atom["event_ref"]:
        return [copy.deepcopy(atom["actor_ref"])]
    return []


def _fixture_action_atom(atom: Mapping[str, Any]) -> dict[str, Any]:
    statement = atom["projection_ref"]["quote"]
    identity = atom["actor_ref"]["quote"]
    if identity not in statement:
        # Source role context already declares this identity; retain it while
        # normalizing the fixture's explicitly declared action and target.
        statement = f"{identity}: {statement}"
    return {
        "statement": statement,
        "event_ref": copy.deepcopy(atom["event_ref"]),
        "actor_ref": copy.deepcopy(atom["actor_ref"]),
        "action": atom["action_quote"],
        "target": atom["target_quote"],
        "role_refs": [copy.deepcopy(atom["projection_ref"])],
    }


def declared_source_action_fixture(
    *, duty_id: str, actor_quote: str, event_quote: str, statement: str,
    action: str, target: str, performer_role: str, observable_result: str,
) -> dict[str, Any]:
    """Declare a test action whose exact performer occurs in its event context.

    Every meaning-bearing value comes from the caller. This builds citation
    custody for boundary tests; it does not interpret or qualify source meaning.
    """
    event_ref = {"quote": event_quote, "context": event_quote}
    return {
        "id": duty_id, "source_refs": [], "performer_role": performer_role,
        "observable_result": observable_result, "statement": statement,
        "event_ref": event_ref,
        "actor_ref": {"quote": actor_quote, "context": event_quote},
        "action": action, "target": target, "role_refs": [copy.deepcopy(event_ref)],
    }


def synthetic_source_duty_receipt(
    host_candidate: Mapping[str, Any], *, evidence_text: str,
    declared_actions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Make a test-only exact-cited ledger; this does not prove semantic roles.

    Legacy fixture cases already declare their intended first run. This helper
    supplies custody for that declared sequence without interpreting the source.
    Public semantic qualification must use a separately authored source ledger.
    """

    if declared_actions is not None:
        ledger = {
            "version": SOURCE_DUTY_LEDGER_VERSION, "status": "inventory", "question": "",
            "evidence_controls": [], "first_path_actions": copy.deepcopy(list(declared_actions)),
            "supporting_human_actions": [], "system_duties": [], "state_fields": [],
            "off_path_transitions": [], "conditional_guards": [], "boundaries": [], "proof_duties": [],
        }
        return synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence_text)
    result = host_candidate.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("synthetic source duties require a fixture result")
    if result.get("status") == "clarification_required":
        raise ValueError(
            "clarification fixture requires a separately declared source duty receipt"
        )
    elif result.get("status") == "authored":
        atoms = getattr(host_candidate, "source_action_atoms", None)
        if atoms is None:
            atoms = _SERIALIZED_FIXTURE_ATOMS.get(_fixture_candidate_key(host_candidate))
        if atoms is None:
            raise ValueError("test host candidate has no declared source action atoms")
    else:
        raise ValueError("synthetic source duties require a known fixture result")
    ledger = {
        "version": SOURCE_DUTY_LEDGER_VERSION, "status": "inventory", "question": "",
        "evidence_controls": [], "state_fields": [], "off_path_transitions": [],
        "conditional_guards": [], "boundaries": [], "proof_duties": [],
    }
    roles = {"human_actors": "human_actor", "internal_systems": "internal_system",
             "external_systems": "external_system", "title": "product_title"}
    for section in ("first_path_actions", "supporting_human_actions", "system_duties"):
        rows = []
        for atom in atoms:
            if atom["source_role"] != section:
                continue
            row = {"id": atom["duty_id"], "source_refs": _fixture_action_refs(atom),
                   **_fixture_action_atom(atom)}
            if section != "supporting_human_actions":
                row["performer_role"] = roles[atom["performer_field"]]
            if section == "first_path_actions":
                row["observable_result"] = "fixture-declared result"
            rows.append(row)
        ledger[section] = rows
    return synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence_text)


def synthetic_source_duty_receipt_for_ledger(
    ledger: Mapping[str, Any], *, evidence_text: str,
) -> dict[str, Any]:
    """Approve a fixture-only ledger; production must obtain an independent verdict."""

    passive = ledger["version"] == "odylith.greenfield.source-duty-ledger.v5"
    preflight = preflight_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence_text, _passive_source=passive,
    )
    decision_task = source_duty_entailment_task(
        preflight, evidence_text=evidence_text
    )
    decision_set = {
        "version": SOURCE_DUTY_DECISION_SET_VERSION,
        "verifier_task_sha256": decision_task["verifier_task_sha256"],
        "source_completeness": {"verdict": "yes", "omissions": []},
        "decisions": {
            claim["duty_id"]: {
                "verdict": "yes",
                "support_ref_indexes": list(range(len(claim["source_refs"]))),
                "role_ref_indexes": list(range(len(claim["role_refs"]))),
            }
            for claim in preflight["claims"]
        },
    }
    return validate_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence_text, decision_set=decision_set, _passive_source=passive,
    )


def _fixture_source_duty_binding(
    host_candidate: Mapping[str, Any], *, evidence_text: str,
) -> dict[str, Any]:
    receipt = synthetic_source_duty_receipt(
        host_candidate, evidence_text=evidence_text
    )
    return {
        "version": HOST_SOURCE_DUTY_BINDING_VERSION,
        "source_sha256": receipt["source_sha256"], "ledger_sha256": receipt["ledger_sha256"],
        "off_path_transitions": [], "conditional_guards": [], "boundaries": [], "proof_duties": [],
    }


def source_duty_fixture(
    host_candidate: Mapping[str, Any], *, evidence_text: str,
) -> dict[str, Any]:
    """Retain the declared fixture receipt, binding, and lifecycle together."""
    from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import (
        project_greenfield_source_lifecycle,
    )

    receipt = synthetic_source_duty_receipt(host_candidate, evidence_text=evidence_text)
    binding = validate_greenfield_source_duty_binding(
        host_candidate["result"][HOST_SOURCE_DUTY_BINDING_FIELD], ledger_receipt=receipt,
        candidate_result=host_candidate["result"], evidence_text=evidence_text,
    )
    return {
        "ledger_receipt": receipt, "binding": copy.deepcopy(binding),
        "lifecycle": project_greenfield_source_lifecycle(
            ledger_receipt=receipt, binding=binding,
            candidate_result=host_candidate["result"], evidence_text=evidence_text,
        ),
    }


def admit_complete_host_candidate(
    *,
    evidence_text: str,
    host_candidate: Mapping[str, Any],
    model_profile_id: str = STANDARD_PROFILE_ID,
) -> Any:
    """Admit one complete public host candidate through the shipped boundary."""

    return admit_greenfield_host_candidate(
        host_candidate,
        evidence_text=evidence_text,
        source_duty_receipt=synthetic_source_duty_receipt(
            host_candidate, evidence_text=evidence_text
        ),
        profile_id=model_profile_id,
    )[0]


def materialize_complete_host_candidate(
    *,
    prompt: str,
    repo_root: Path,
    host_candidate: Mapping[str, Any],
    authoring_profile_id: str = STANDARD_PROFILE_ID,
    edit_evidence: str = "",
    authoring_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize one complete public host candidate through the shipped path."""

    prepared_evidence = prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    candidate = copy.deepcopy(host_candidate)
    result = candidate.get("result")
    if isinstance(result, dict) and result.get("status") == "authored":
        # The staging source adds custody headers to a raw prompt. Rebind only
        # this synthetic fixture's digest to the exact staged evidence bytes.
        result[HOST_SOURCE_DUTY_BINDING_FIELD] = _fixture_source_duty_binding(
            candidate, evidence_text=prepared_evidence.evidence_source
        )
    return materialize_host_authored_intent(
        prompt=prompt,
        repo_root=repo_root,
        edit_evidence=edit_evidence,
        host_candidate=candidate,
        source_duty_receipt=synthetic_source_duty_receipt(
            candidate, evidence_text=prepared_evidence.evidence_source
        ),
        authoring_profile_id=authoring_profile_id,
        authoring_receipt=authoring_receipt,
        prepared_evidence=prepared_evidence,
    )


def host_candidate_response(
    response: Mapping[str, Any],
    *,
    evidence_text: str,
) -> dict[str, Any]:
    """Project a canonical test response into the public host-candidate shape."""

    candidate = _FixtureHostCandidate(copy.deepcopy(dict(response)))
    candidate["version"] = HOST_CANDIDATE_FORMAT_VERSION
    result = candidate.get("result")
    if not isinstance(result, dict) or result.get("status") == "clarification_required":
        return candidate
    result.pop("components", None)
    design = result.get("provisional_design")
    if isinstance(design, dict) and "project_summary" not in design:
        # Explicit synthetic narrative; no source parsing or product-quality claim.
        design["project_summary"] = (
            "This structural fixture supports test authors checking exact source and design custody."
        )
    facts = result.get("facts")
    events = result.get("events")
    if not isinstance(facts, dict) or not isinstance(events, list):
        raise TypeError("canonical fixture cannot be projected to a host candidate")
    first_path = facts.pop("first_path")
    facts.pop("supporting_events", None)
    if not isinstance(first_path, list) or len(first_path) != len(events):
        raise ValueError("canonical fixture event citations are incomplete")
    for field, value in tuple(facts.items()):
        if isinstance(value, list):
            citations = [
                _unique_context_citation(evidence_text, row)
                for row in value
            ]
            facts[field] = citations
        elif isinstance(value, Mapping):
            facts[field] = _unique_context_citation(
                evidence_text,
                value,
                state_object=field == "state_object",
            )
    first_orders = result["provisional_design"]["first_run"]["event_orders"]
    sections = {order: ("first_path_actions" if order in first_orders else
                "supporting_human_actions" if event["actor_fact"]["field"] == "human_actors"
                else "system_duties") for order, event in enumerate(events, 1)}
    catalog_orders = [*first_orders, *[order for order in sections if sections[order] == "supporting_human_actions"],
                      *[order for order in sections if sections[order] == "system_duties"]]
    remap = {old: new for new, old in enumerate(catalog_orders, 1)}
    atoms = []
    for old in catalog_orders:
        event, citation = events[old - 1], first_path[old - 1]
        event_ref = _unique_context_citation(evidence_text, citation)
        section = sections[old]
        duty_id = (f"fixture-first-path-{first_orders.index(old) + 1}" if section == "first_path_actions"
                   else f"fixture-{'supporting' if section == 'supporting_human_actions' else 'system'}-{old}")
        atoms.append({
            "event_ref": event_ref, "projection_ref": copy.deepcopy(event_ref),
            "actor_ref": _fixture_actor_ref(facts, event), "action_quote": event["action_quote"],
            "target_quote": event["target_quote"], "performer_field": event["actor_fact"]["field"],
            "source_role": section, "duty_id": duty_id,
        })
    def remap_refs(value):
        if isinstance(value, list):
            for row in value:
                remap_refs(row)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key in {"event_order", "before_event", "after_event"} and type(child) is int:
                    value[key] = remap.get(child, child)
                elif key in {"event_orders", "supported_event_orders", "verification_event_orders"}:
                    value[key] = [remap.get(order, order) for order in child]
                else:
                    remap_refs(child)
    remap_refs(design)
    remap_refs(result["source_precedence"])
    if result["terminal"] is not None:
        remap_refs(result["terminal"])
        if result["terminal"]["result_fact"]["field"] == "first_path":
            old_row = result["terminal"]["result_fact"]["row"]
            result["terminal"]["result_fact"]["row"] = remap.get(old_row, old_row)
    result.pop("events")
    candidate.source_action_atoms = atoms
    result[HOST_SOURCE_DUTY_BINDING_FIELD] = _fixture_source_duty_binding(candidate, evidence_text=evidence_text)
    _SERIALIZED_FIXTURE_ATOMS[_fixture_candidate_key(candidate)] = copy.deepcopy(atoms)
    return candidate


def write_host_candidate_fixture(
    path: Path,
    response: Mapping[str, Any],
    *,
    evidence_text: str,
) -> Path:
    """Write one public host candidate fixture and return its path."""

    path.write_text(
        json.dumps(
            host_candidate_response(response, evidence_text=evidence_text)
        ),
        encoding="utf-8",
    )
    return path


def write_synthetic_source_duty_receipt(
    path: Path,
    host_candidate: Mapping[str, Any],
    *,
    evidence_text: str,
    declared_actions: Sequence[Mapping[str, Any]] | None = None,
) -> Path:
    """Write test-only source custody for public CLI fixture calls."""

    path.write_text(
        json.dumps(
            synthetic_source_duty_receipt(
                host_candidate, evidence_text=evidence_text,
                declared_actions=declared_actions,
            )
        ),
        encoding="utf-8",
    )
    return path


def _unique_context_citation(
    evidence_text: str,
    citation: Mapping[str, Any],
    *,
    state_object: bool = False,
) -> dict[str, str]:
    evidence = evidence_text.encode("utf-8")
    quote, start = resolve_source_citation(
        evidence,
        citation,
        state_object=state_object,
    )
    start_character = len(evidence[:start].decode("utf-8"))
    end_character = start_character + len(quote)
    for added in range(len(evidence_text) + 1):
        for before in range(added + 1):
            after = added - before
            left = max(0, start_character - before)
            right = min(len(evidence_text), end_character + after)
            context = evidence_text[left:right]
            if evidence_text.count(context) == 1 and context.count(quote) == 1:
                return {"quote": quote, "context": context}
    raise AssertionError("fixture could not derive unique citation context")


def authored_response(
    intent: Mapping[str, Any],
    *,
    evidence_text: str = "",
    first_path_segments: Sequence[str] | None = None,
    first_path_relations: Sequence[Mapping[str, Any]] | None = None,
    supporting_event_relations: Sequence[Mapping[str, Any]] = (),
    component_responsibility_owners: Sequence[str] | None = None,
    provisional_design: Mapping[str, Any] | None = None,
    source_precedence: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build model-shaped citations; fixture states retain their declared quote."""

    source_relations = tuple(
        first_path_relations or _default_first_path_relations(intent)
    )
    path_relations = source_relations
    source_relations += tuple(supporting_event_relations)
    path_segments = (
        [str(row).strip() for row in first_path_segments]
        if first_path_segments is not None
        else [str(row.get("event_quote") or "").strip() for row in source_relations]
    )
    facts: dict[str, Any] = {
        **{field: None for field in _SINGULAR_SOURCE_FIELDS},
        **{field: [] for field in _REPEATED_SOURCE_FIELDS},
    }
    selected_facts: list[dict[str, Any]] = []
    fact_indexes: dict[str, int] = {}
    first_path_fact_indexes: list[int] = []
    for field, value in intent.items():
        if field in {"assumptions", "ambiguities", "component_responsibilities"}:
            continue
        rows = (
            path_segments
            if field == "first_path"
            else value if isinstance(value, list) else [value]
        )
        for row_index, row in enumerate(rows):
            quote = str(row).strip()
            if not quote:
                continue
            fact_index = len(selected_facts) + 1
            projection_path = f"/{field}" if not isinstance(value, list) else f"/{field}/{row_index}"
            citation = {"quote": quote, "occurrence": 1}
            if field in _SINGULAR_SOURCE_FIELDS:
                facts[field] = citation
                source_field_row = 1
            else:
                facts[field].append(citation)
                source_field_row = len(facts[field])
            selected_facts.append({"field": field, "row": source_field_row, **citation})
            fact_indexes[projection_path] = fact_index
            if field == "first_path":
                first_path_fact_indexes.append(fact_index)

    state_citation = facts["state_object"]
    if state_citation is not None:
        facts["state_object"] = {
            "quote": state_citation["quote"],
            "prefix": "",
            "anchor_occurrence": state_citation["occurrence"],
        }

    relation_rows = _relation_rows(
        source_relations,
        first_path_segments=(
            path_segments
        ),
        first_path_fact_indexes=first_path_fact_indexes,
        fact_indexes=fact_indexes,
        intent=intent,
    )
    if not relation_rows:
        raise ValueError("authored fixture requires one event")
    terminal = _terminal_row(
        relations=path_relations,
        facts=selected_facts,
        evidence_text=evidence_text,
    )
    components = _component_responsibility_relation_rows(
        intent=intent,
        fact_indexes=fact_indexes,
        owners=component_responsibility_owners,
    )
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "result": {
            "status": "authored",
            "facts": facts,
            "events": relation_rows,
            "source_precedence": [dict(row) for row in source_precedence],
            "terminal": terminal,
            "components": components,
            "assumptions": list(intent.get("assumptions") or []),
            "ambiguities": list(intent.get("ambiguities") or []),
            "consistency": {"status": "consistent", "evidence_quotes": []},
            "provisional_design": copy.deepcopy(provisional_design) if provisional_design is not None
            else structural_design_fixture(
                range(1, len(relation_rows) + 1),
                first_run_event_orders=range(1, len(path_relations) + 1),
            ),
        },
    }


def structural_design_fixture(
    event_orders: Sequence[int], *, first_run_event_orders: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Synthetic design for custody/wiring tests, never product-quality evidence."""

    orders = list(event_orders)
    if not orders:
        raise ValueError("design fixture requires source events")
    components = [
        {
            "key": f"test-boundary-{index}",
            "name": f"Structural test boundary {index}",
            "responsibility": f"Retain the test value at boundary {index}.",
            "supported_event_orders": orders if index == 1 else [orders[(index - 1) % len(orders)]],
            "verification": f"Read back the exact test value assigned to boundary {index}.",
            "verification_event_orders": (
                orders if index == 1 else [orders[(index - 1) % len(orders)]]
            ),
        }
        for index in range(1, 5)
    ]
    return {
        "version": "odylith.greenfield.provisional-design.v6",
        "authority_kind": "provisional_design",
        "first_run": {
            "event_orders": list(first_run_event_orders) if first_run_event_orders is not None else orders,
            "rationale": "The fixture proposes this execution order; citation order does not establish chronology.",
        },
        "components": components,
        "workstreams": [
            {
                "key": f"test-work-{index}",
                "title": f"Implement structural test boundary {index}",
                "problem": f"Users cannot yet rely on the distinct test boundary {index}.",
                "component_keys": [row["key"]],
                "depends_on": [f"test-work-{index - 1}"] if index > 1 else [],
                "deliverable": f"Implement the exact-value boundary {index}.",
                "verification": f"An independent read returns the test value from boundary {index}.",
                "verification_event_orders": list(row["verification_event_orders"]),
            }
            for index, row in enumerate(components, 1)
        ],
        "exchanges": [
            {
                "from_component": components[index - 1]["key"],
                "to_component": components[index]["key"],
                "contract": f"The exact test value from boundary {index}.",
            }
            for index in range(1, 4)
        ],
        "risk_posture": {
            "status": "no_material_risks_identified",
            "rationale": "This structural fixture carries no product-domain risk claim.",
            "items": [],
        },
    }


def clarification_response(
    *,
    question: str,
    material_dimension: str,
    evidence_quotes: Sequence[str],
    consistency_status: str = "material_ambiguity",
) -> dict[str, Any]:
    """Return a clarification response; the question remains test-only metadata."""

    del question
    return {
        "version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "result": {
            "status": "clarification_required",
            "consistency": {
                "status": consistency_status,
                "evidence_quotes": [str(quote) for quote in evidence_quotes],
            },
            "clarification": {"material_dimension": material_dimension},
        },
    }


def model_event_rows(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return mutable fixture event rows in their authored order."""

    result = response.get("result")
    events = result.get("events") if isinstance(result, Mapping) else None
    if not isinstance(events, list) or not all(
        isinstance(row, dict) for row in events
    ):
        raise ValueError("authored fixture response has no event graph")
    return events


def _relation_rows(
    relations: Sequence[Mapping[str, Any]],
    *,
    first_path_segments: Sequence[str],
    first_path_fact_indexes: Sequence[int],
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relation in relations:
        event_quote = str(relation.get("event_quote") or "")
        # Legacy-looking surface text is accepted only as fixture ergonomics for
        # choosing an already-selected human/external fact; it is never emitted.
        test_surface_actor_quote = str(relation.get("actor_quote") or "")
        target_quote = str(relation.get("target_quote") or "")
        actor_kind = str(relation.get("actor_kind") or "")
        segment_index = relation.get("segment_index")
        if isinstance(segment_index, int) and not isinstance(segment_index, bool):
            selected_segment_index = segment_index
        else:
            matches = [
                index
                for index, segment in enumerate(first_path_segments)
                if _occurrence(segment, event_quote)
            ]
            if len(matches) != 1:
                raise ValueError(
                    "authored fixture relation must identify exactly one first_path segment"
                )
            selected_segment_index = matches[0]
        if selected_segment_index < 0 or selected_segment_index >= len(first_path_fact_indexes):
            raise ValueError("authored fixture relation references an unknown first_path segment")
        actor_fact = _actor_fact(
            relation,
            actor_kind=actor_kind,
            test_surface_actor_quote=test_surface_actor_quote,
            fact_indexes=fact_indexes,
            intent=intent,
        )
        rows.append(
            {
                "actor_fact": actor_fact,
                "action_quote": str(
                    relation.get("action_verb_quote") or event_quote
                ),
                "target_quote": target_quote,
            }
        )
    return rows


def _terminal_row(
    *,
    relations: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
    evidence_text: str,
) -> dict[str, Any]:
    visible_rows = [
        (order, str(relation.get("visible_result_quote") or ""))
        for order, relation in enumerate(relations, start=1)
        if str(relation.get("visible_result_quote") or "")
    ]
    if not visible_rows:
        raise ValueError("authored fixture requires one terminal visible result")
    event_order, result_quote = visible_rows[-1]
    proof_fact = next(
        (
            fact
            for fact in facts
            if fact["field"] in TERMINAL_RESULT_FACT_FIELDS
            and result_quote in str(fact.get("quote") or "")
        ),
        None,
    )
    if proof_fact is None:
        raise ValueError(
            "authored fixture terminal result requires a selected proof fact"
        )
    if evidence_text:
        _nth_start(
            evidence_text.encode("utf-8"),
            str(proof_fact["quote"]).encode("utf-8"),
            int(proof_fact["occurrence"]),
        )
    return {
        "event_order": event_order,
        "result_fact": {"field": proof_fact["field"], "row": proof_fact["row"]},
        "result_quote": result_quote,
        "result_occurrence": 1,
    }


def _actor_fact(
    relation: Mapping[str, Any],
    *,
    actor_kind: str,
    test_surface_actor_quote: str,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> dict[str, object]:
    explicit_path = relation.get("actor_fact_path")
    if explicit_path is not None:
        return _actor_fact_reference_for_path(
            explicit_path,
            actor_kind=actor_kind,
            relation=relation,
            test_surface_actor_quote=test_surface_actor_quote,
            fact_indexes=fact_indexes,
            intent=intent,
        )
    if actor_kind == "product":
        return _owner_system_fact_reference(
            relation,
            fact_indexes=fact_indexes,
            intent=intent,
        )
    field = {
        "human": "human_actors",
        "external_system": "external_systems",
    }.get(actor_kind)
    if field is None:
        raise ValueError(f"unknown authored fixture actor_kind: {actor_kind}")
    selected_quote = str(
        relation.get("actor_fact_quote") or test_surface_actor_quote
    )
    rows = [str(row) for row in intent.get(field, [])]
    matches = [index for index, row in enumerate(rows) if row == selected_quote]
    if len(matches) != 1:
        raise ValueError("authored fixture actor must identify one exact selected entity fact")
    if not fact_indexes.get(f"/{field}/{matches[0]}", 0):
        raise ValueError("authored fixture actor fact is not selected")
    return {"field": field, "row": matches[0] + 1}


def _actor_fact_reference_for_path(
    path: object,
    *,
    actor_kind: str,
    relation: Mapping[str, Any],
    test_surface_actor_quote: str,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> dict[str, object]:
    if not isinstance(path, str) or not fact_indexes.get(path, 0):
        raise ValueError("authored fixture actor path is not selected")
    field, separator, row_text = path.strip("/").partition("/")
    if not separator or not row_text.isdigit():
        if path == "/title" and actor_kind == "product":
            field, row_text = "title", "0"
        else:
            raise ValueError("authored fixture actor path is invalid")
    row_index = int(row_text)
    expected_fields = {
        "human": {"human_actors"},
        "external_system": {"external_systems"},
        "product": {"title", "internal_systems"},
    }.get(actor_kind)
    if expected_fields is None or field not in expected_fields:
        raise ValueError("authored fixture actor path conflicts with actor_kind")
    values = [str(value) for value in intent.get(field, [])] if field != "title" else [str(intent.get("title") or "")]
    if row_index < 0 or row_index >= len(values) or not values[row_index]:
        raise ValueError("authored fixture actor path is not selected")
    expected_quote = str(
        relation.get("owner_system_quote")
        if actor_kind == "product"
        else relation.get("actor_fact_quote") or test_surface_actor_quote
    )
    if expected_quote and expected_quote != values[row_index]:
        raise ValueError("authored fixture actor path conflicts with actor quote")
    return {"field": field, "row": row_index + 1}


def _owner_system_fact_reference(
    relation: Mapping[str, Any],
    *,
    fact_indexes: Mapping[str, int],
    intent: Mapping[str, Any],
) -> dict[str, object]:
    owner = str(relation.get("owner_system_quote") or "")
    systems = [str(row) for row in intent.get("internal_systems", [])]
    if not owner:
        raise ValueError("authored fixture must explicitly bind every product event to owner_system_quote")
    if owner == str(intent.get("title") or ""):
        if fact_indexes.get("/title", 0):
            return {"field": "title", "row": 1}
    for index, system in enumerate(systems):
        if owner == system and fact_indexes.get(f"/internal_systems/{index}", 0):
            return {"field": "internal_systems", "row": index + 1}
    raise ValueError(f"unknown authored fixture owner_system_quote: {owner}")


def _component_responsibility_relation_rows(
    *,
    intent: Mapping[str, Any],
    fact_indexes: Mapping[str, int],
    owners: Sequence[str] | None,
) -> list[dict[str, Any]]:
    responsibilities = [
        str(row)
        for row in intent.get("component_responsibilities", [])
        if str(row)
    ]
    systems = [str(row) for row in intent.get("internal_systems", []) if str(row)]
    if not responsibilities:
        return []
    if owners is None:
        raise ValueError(
            "authored fixture must explicitly bind component_responsibility_owners"
        )
    owner_values = [str(owner) for owner in owners]
    if len(owner_values) != len(responsibilities):
        raise ValueError("authored fixture must bind every component responsibility exactly once")
    rows: list[dict[str, Any]] = []
    for index, owner in enumerate(owner_values):
        owner_fact_quote = _owner_fact_quote(
            owner=owner,
            intent=intent,
            systems=systems,
            fact_indexes=fact_indexes,
        )
        if not owner_fact_quote:
            raise ValueError("authored fixture component responsibility owner is not a selected fact")
        group = next(
            (
                row
                for row in rows
                if row["owner_fact_quote"] == owner_fact_quote
            ),
            None,
        )
        if group is None:
            group = {
                "owner_fact_quote": owner_fact_quote,
                "responsibilities": [],
            }
            rows.append(group)
        group["responsibilities"].append(
            {"quote": responsibilities[index], "occurrence": 1}
        )
    return rows


def _owner_fact_quote(
    *,
    owner: str,
    intent: Mapping[str, Any],
    systems: Sequence[str],
    fact_indexes: Mapping[str, int],
) -> str:
    if owner == str(intent.get("title") or ""):
        path = "/title"
    else:
        try:
            path = f"/internal_systems/{systems.index(owner)}"
        except ValueError as exc:
            raise ValueError(
                f"unknown authored fixture component responsibility owner: {owner}"
            ) from exc
    fact_index = fact_indexes.get(path, 0)
    if not fact_index:
        raise ValueError("authored fixture component owner is not a selected fact")
    return owner


def _default_first_path_relations(intent: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    first_path = str(intent.get("first_path") or "").strip()
    actors = intent.get("human_actors") or []
    human_actor = str(actors[0]).strip() if actors else ""
    return (
        {
            "actor_kind": "human",
            "actor_fact_quote": human_actor,
            "event_quote": first_path,
            "action_verb_quote": first_path,
            "target_quote": "",
            "visible_result_quote": first_path,
        },
    )


def _occurrence(source: str, quote: str) -> int:
    return 1 if quote and source.encode("utf-8").find(quote.encode("utf-8")) >= 0 else 0


def _nth_start(source: bytes, quote: bytes, occurrence: int) -> int:
    cursor = 0
    found = -1
    for _ in range(occurrence):
        found = source.find(quote, cursor)
        if found < 0:
            raise ValueError("authored fixture quote occurrence is not present")
        cursor = found + 1
    return found
