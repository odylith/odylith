"""Adversarial custody proofs for model-authored relation identity."""

from __future__ import annotations

import copy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoredIntent,
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
    model_event_rows,
)


def _harbor_case() -> tuple[str, dict[str, object], dict[str, object]]:
    prompt = (
        "Harbor Relay. Dock attendant Ivo submits a berth request. "
        + ("Reference custody note remains unchanged. " * 90)
    )
    edit_evidence = (
        "The Tide Authority API supplies clearance. "
        "Harbor Registry records approved berth state. "
        "Do not place a berth without clearance. "
        "The berth map shows the approved placement."
    )
    evidence = _combined_evidence(prompt=prompt, edit_evidence=edit_evidence)
    segments = [
        "Dock attendant Ivo submits a berth request",
        "The Tide Authority API supplies clearance",
        "Harbor Registry records approved berth state",
        "The berth map shows the approved placement",
    ]
    intent: dict[str, object] = {
        "title": "Harbor Relay",
        "product_story": segments[0],
        "opportunity": segments[3],
        "state_object": "approved berth state",
        "first_path": "\n".join(segments),
        "proof_boundary": segments[3],
        "success_metrics": [segments[3]],
        "operational_constraints": ["Do not place a berth without clearance"],
        "human_actors": ["Dock attendant Ivo"],
        "external_systems": ["Tide Authority API"],
        "internal_systems": ["Harbor Registry", "berth map"],
        "assumptions": [],
        "ambiguities": [],
    }
    response = authored_response(
        intent,
        first_path_segments=segments,
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Dock attendant Ivo",
                "event_quote": segments[0],
                "action_verb_quote": "submits",
                "target_quote": "a berth request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "external_system",
                "actor_quote": "Tide Authority API",
                "event_quote": segments[1],
                "action_verb_quote": "supplies",
                "target_quote": "clearance",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Harbor Registry",
                "owner_system_quote": "Harbor Registry",
                "event_quote": segments[2],
                "action_verb_quote": "records",
                "target_quote": "approved berth state",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "The berth map",
                "owner_system_quote": "berth map",
                "event_quote": segments[3],
                "action_verb_quote": "shows",
                "target_quote": "the approved placement",
                "visible_result_quote": segments[3],
                "recovery_path": False,
            },
        ],
        terminal_component_owner="berth map",
    )
    return evidence, intent, response


def _combined_evidence(*, prompt: str, edit_evidence: str) -> str:
    from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
        combined_prompt_evidence_source,
    )

    return combined_prompt_evidence_source(
        prompt=prompt,
        edit_evidence=edit_evidence,
    )


def _author(
    evidence: str,
    response: dict[str, object],
) -> GreenfieldModelAuthoredIntent:
    result = author_greenfield_intent(
        evidence_text=evidence,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )
    assert isinstance(result, GreenfieldModelAuthoredIntent)
    return result


def test_typed_product_owner_edge_is_authoritative_without_name_reparsing() -> None:
    evidence, _intent, response = _harbor_case()
    relations = model_event_rows(response)
    relations[2]["actor_fact_quote"] = "berth map"

    result = _author(evidence, response)

    assert result.first_path_relations[2]["actor_quote"] == "berth map"
    assert result.first_path_relations[2]["owner_system_quote"] == "berth map"


def test_named_product_event_accepts_its_exact_selected_owner() -> None:
    evidence, _intent, response = _harbor_case()

    result = _author(evidence, response)

    assert result.first_path_relations[2]["owner_system_path"] == "/internal_systems/0"
    assert result.first_path_relations[2]["owner_system_quote"] == "Harbor Registry"


def test_external_event_actor_must_reference_a_selected_external_fact() -> None:
    evidence, _intent, response = _harbor_case()
    relations = model_event_rows(response)
    relations[1]["actor_fact_quote"] = "Absent Harbor Relay"

    with pytest.raises(GreenfieldModelAuthoringError, match="actor fact"):
        _author(evidence, response)


def test_exact_external_actor_kind_is_derived_from_its_selected_fact() -> None:
    evidence, _intent, response = _harbor_case()

    result = _author(evidence, response)

    assert result.first_path_relations[1]["actor_kind"] == "external_system"


def test_product_pronoun_uses_an_explicit_selected_actor_fact() -> None:
    segments = [
        "Analyst Aya submits a case",
        "Review Engine receives it",
        "It shows a receipt",
    ]
    prompt = "Relay Console. " + ". ".join(segments) + "."
    intent: dict[str, object] = {
        "title": "Relay Console",
        "product_story": segments[0],
        "first_path": "\n".join(segments),
        "proof_boundary": segments[2],
        "success_metrics": [segments[2]],
        "human_actors": ["Analyst Aya"],
        "internal_systems": ["Review Engine"],
        "assumptions": [],
        "ambiguities": [],
    }
    response = authored_response(
        intent,
        first_path_segments=segments,
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Analyst Aya",
                "event_quote": segments[0],
                "action_verb_quote": "submits",
                "target_quote": "a case",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Review Engine",
                "owner_system_quote": "Review Engine",
                "event_quote": segments[1],
                "action_verb_quote": "receives",
                "target_quote": "it",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "It",
                "owner_system_quote": "Review Engine",
                "event_quote": segments[2],
                "action_verb_quote": "shows",
                "target_quote": "a receipt",
                "visible_result_quote": segments[2],
                "recovery_path": False,
            },
        ],
        terminal_component_owner="Review Engine",
    )

    result = _author(prompt, response)

    assert result.first_path_relations[2]["actor_quote"] == "Review Engine"
    assert result.first_path_relations[2]["actor_fact_path"] == "/internal_systems/0"
    assert result.first_path_relations[2]["actor_fact_quote"] == "Review Engine"


def test_coordinated_clauses_preserve_carried_actors_and_every_action() -> None:
    first_path = (
        "Contractor Lina uploads a permit packet, reviews the extracted address, "
        "then Permit Relay stores the approved packet and shows Lina an accepted receipt"
    )
    events = (
        "Contractor Lina uploads a permit packet",
        "reviews the extracted address",
        "Permit Relay stores the approved packet",
        "shows Lina an accepted receipt",
    )
    evidence = f"Permit Relay. {first_path}."
    intent: dict[str, object] = {
        "title": "Permit Relay",
        "product_story": first_path,
        "state_object": "approved packet",
        "first_path": first_path,
        "proof_boundary": events[3],
        "problem": events[0],
        "customer": "Contractor Lina",
        "opportunity": events[3],
        "product_view": first_path,
        "success_metrics": [events[3]],
        "component_responsibilities": [events[2], events[3]],
        "human_actors": ["Contractor Lina"],
        "assumptions": [],
        "ambiguities": [],
    }
    response = authored_response(
        intent,
        evidence_text=evidence,
        first_path_segments=list(events),
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Contractor Lina",
                "event_quote": events[0],
                "action_verb_quote": "uploads",
                "target_quote": "a permit packet",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Contractor Lina",
                "event_quote": events[1],
                "action_verb_quote": "reviews",
                "target_quote": "the extracted address",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Permit Relay",
                "owner_system_quote": "Permit Relay",
                "event_quote": events[2],
                "action_verb_quote": "stores",
                "target_quote": "the approved packet",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Permit Relay",
                "owner_system_quote": "Permit Relay",
                "event_quote": events[3],
                "action_verb_quote": "shows",
                "target_quote": "an accepted receipt",
                "visible_result_quote": events[3],
                "recovery_path": False,
            },
        ],
        component_responsibility_owners=["Permit Relay", "Permit Relay"],
    )

    result = _author(evidence, response)

    assert [row["actor_quote"] for row in result.first_path_relations] == [
        "Contractor Lina",
        "Contractor Lina",
        "Permit Relay",
        "Permit Relay",
    ]
    assert [row["action_verb_quote"] for row in result.first_path_relations] == [
        *events,
    ]
    assert [
        row["quote"]
        for row in result.atomic_claims
        if row["relation_role"] == "action_verb_quote"
    ] == list(events)


def test_sealed_separate_source_context_rejects_an_unknown_event_order() -> None:
    evidence, _intent, response = _harbor_case()
    result = _author(evidence, response)
    context_relations = [copy.deepcopy(row) for row in result.first_path_context_relations]
    constraint = next(
        row
        for row in context_relations
        if row["context_kind"] == "operational_constraint"
    )
    constraint["first_path_event_order"] = 999
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=context_relations,
        ),
    }

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="context relation"):
        build_product_intent_envelope(
            sealed_intent,
            source_text=evidence,
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )


def test_overlapped_and_independent_context_orders_accept_exact_coordinates() -> None:
    evidence, _intent, response = _harbor_case()

    result = _author(evidence, response)

    assert [
        (row["context_kind"], row["first_path_event_order"])
        for row in result.first_path_context_relations
    ] == [
        ("state_object", 3),
        ("external_system", 2),
        ("operational_constraint", 0),
    ]


def _repeated_event_case() -> tuple[str, dict[str, object]]:
    repeated = "Operator Ada submits request"
    terminal = "Retry Console shows receipt"
    segments = [repeated, repeated, terminal]
    intent: dict[str, object] = {
        "title": "Retry Console",
        "product_story": "Retries preserve submitted work",
        "first_path": "\n".join(segments),
        "proof_boundary": terminal,
        "success_metrics": [terminal],
        "human_actors": ["Operator Ada"],
        "assumptions": [],
        "ambiguities": [],
    }
    prompt = (
        "Retry Console. Retries preserve submitted work. "
        f"{repeated}. {repeated}. {terminal}."
    )
    response = authored_response(
        intent,
        first_path_segments=segments,
        first_path_relations=[
            {
                "segment_index": 0,
                "actor_kind": "human",
                "actor_quote": "Operator Ada",
                "event_quote": repeated,
                "action_verb_quote": "submits",
                "target_quote": "request",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "segment_index": 1,
                "actor_kind": "human",
                "actor_quote": "Operator Ada",
                "event_quote": repeated,
                "action_verb_quote": "submits",
                "target_quote": "request",
                "visible_result_quote": "",
                "recovery_path": True,
            },
            {
                "segment_index": 2,
                "actor_kind": "product",
                "actor_quote": "Retry Console",
                "owner_system_quote": "Retry Console",
                "event_quote": terminal,
                "action_verb_quote": "shows",
                "target_quote": "receipt",
                "visible_result_quote": terminal,
                "recovery_path": False,
            },
        ],
        terminal_component_owner="Retry Console",
    )
    path_facts = response["result"]["facts"]["first_path"]
    path_facts[1]["occurrence"] = 2
    return prompt, response


def test_repeated_event_text_at_distinct_source_and_projection_coordinates_seals() -> None:
    evidence, response = _repeated_event_case()

    result = _author(evidence, response)
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }
    envelope = build_product_intent_envelope(
        sealed_intent,
        source_text=evidence,
        source_format="operator_prompt",
        authored_source_spans=result.source_spans,
        authored_atomic_claims=result.atomic_claims,
        authored_source_sha256=result.source_sha256,
    )

    first, retry = result.first_path_relations[:2]
    assert first["event_quote"] == retry["event_quote"]
    assert (first["source_start_byte"], first["source_end_byte"]) != (
        retry["source_start_byte"],
        retry["source_end_byte"],
    )
    assert (first["event_start_byte"], first["event_end_byte"]) != (
        retry["event_start_byte"],
        retry["event_end_byte"],
    )
    assert envelope["product_facts"]["first_path"] == result.intent["first_path"]


def test_true_duplicate_event_coordinates_fail_sealed_validation() -> None:
    evidence, response = _repeated_event_case()
    result = _author(evidence, response)
    relations = [copy.deepcopy(row) for row in result.first_path_relations]
    for key in (
        "source_start_byte",
        "source_end_byte",
        "event_start_byte",
        "event_end_byte",
    ):
        relations[1][key] = relations[0][key]
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="invalid first-path relations"):
        build_product_intent_envelope(
            sealed_intent,
            source_text=evidence,
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )


def test_partially_overlapping_source_event_coordinates_fail_sealed_validation() -> None:
    evidence, response = _repeated_event_case()
    result = _author(evidence, response)
    relations = [copy.deepcopy(row) for row in result.first_path_relations]
    event_length = relations[1]["source_end_byte"] - relations[1]["source_start_byte"]
    relations[1]["source_start_byte"] = relations[0]["source_end_byte"] - 1
    relations[1]["source_end_byte"] = relations[1]["source_start_byte"] + event_length
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="invalid first-path relations"):
        build_product_intent_envelope(
            sealed_intent,
            source_text=evidence,
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )


def test_utf8_multiactor_path_preserves_meaning_when_source_order_differs() -> None:
    prompt = (
        "Café Relay. Analyst Zoë submits dossier. "
        "Reviewer Béla approves dossier."
    )
    edit = "The Æther API supplies attestation. Café Console shows réceipt."
    evidence = _combined_evidence(prompt=prompt, edit_evidence=edit)
    segments = [
        "Analyst Zoë submits dossier",
        "The Æther API supplies attestation",
        "Reviewer Béla approves dossier",
        "Café Console shows réceipt",
    ]
    intent: dict[str, object] = {
        "title": "Café Relay",
        "product_story": segments[0],
        "state_object": "dossier",
        "first_path": "\n".join(segments),
        "proof_boundary": segments[3],
        "success_metrics": [segments[3]],
        "human_actors": ["Analyst Zoë", "Reviewer Béla"],
        "external_systems": ["Æther API"],
        "internal_systems": ["Café Console"],
        "assumptions": [],
        "ambiguities": [],
    }
    response = authored_response(
        intent,
        first_path_segments=segments,
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Analyst Zoë",
                "event_quote": segments[0],
                "action_verb_quote": "submits",
                "target_quote": "dossier",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "external_system",
                "actor_quote": "Æther API",
                "event_quote": segments[1],
                "action_verb_quote": "supplies",
                "target_quote": "attestation",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "Reviewer Béla",
                "event_quote": segments[2],
                "action_verb_quote": "approves",
                "target_quote": "dossier",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Café Console",
                "owner_system_quote": "Café Console",
                "event_quote": segments[3],
                "action_verb_quote": "shows",
                "target_quote": "réceipt",
                "visible_result_quote": segments[3],
                "recovery_path": False,
            },
        ],
        terminal_component_owner="Café Console",
    )

    result = _author(evidence, response)

    assert result.intent["human_actors"] == ["Analyst Zoë", "Reviewer Béla"]
    assert result.first_path_relations[1]["actor_quote"] == "Æther API"
    assert result.first_path_relations[2]["source_start_byte"] < result.first_path_relations[1][
        "source_start_byte"
    ]
    source_bytes = evidence.encode("utf-8")
    for relation in result.first_path_relations:
        assert source_bytes[
            relation["source_start_byte"] : relation["source_end_byte"]
        ] == relation["event_quote"].encode("utf-8")
