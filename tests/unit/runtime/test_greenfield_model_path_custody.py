"""Byte-exact custody proofs for model-authored Greenfield paths."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_semantics_mapping,
    validate_first_path_relations,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
    model_event_rows,
)

_TEXT_FIELDS = {
    "title": "Harbor Desk",
    "product_story": "Dock attendants need clear berth placement",
    "state_object": "berth occupancy",
    "first_path": "Dock attendant Ivo enters a vessel tag and the product records berth occupancy before the berth map shows the placement",
    "proof_boundary": "Verify the placement and retention receipt",
    "problem": "Berth placement is hard to track",
    "customer": "Dock attendants",
    "opportunity": "One reviewable berth workflow",
    "product_view": "Harbor Desk gives dock attendants a berth workflow",
}
_LIST_FIELDS = {
    "success_metrics": ["The berth map shows the placement"],
    "evidence_requirements": ["Source evidence preserves berth history"],
    "operational_constraints": ["Retain source notes for seven years"],
    "component_responsibilities": ["Record berth occupancy"],
    "human_actors": ["Dock attendant Ivo"],
    "external_systems": ["Harbor Ledger"],
    "internal_systems": ["Berth map"],
    "assumptions": [],
    "ambiguities": [],
    "non_goals": ["Do not manage vessel scheduling"],
}
_AUTHORED_FIRST_PATH = "\n".join(
    (
        "Dock attendant Ivo enters a vessel tag",
        "the product records berth occupancy",
        "the berth map shows the placement",
    )
)


def _source() -> str:
    return ". ".join(
        [*_TEXT_FIELDS.values(), *(item for rows in _LIST_FIELDS.values() for item in rows)]
    ) + "."


def _response(source: str) -> dict[str, object]:
    assert source
    response = authored_response(
        {**_TEXT_FIELDS, **_LIST_FIELDS},
        evidence_text=source,
        component_responsibility_owners=["Berth map"],
        first_path_relations=[
            {
                "order": 1,
                "actor_kind": "human",
                "actor_quote": "Dock attendant Ivo",
                "event_quote": "Dock attendant Ivo enters a vessel tag",
                "action_verb_quote": "enters",
                "target_quote": "a vessel tag",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "order": 2,
                "actor_kind": "product",
                "actor_quote": "the product",
                "owner_system_quote": "Berth map",
                "event_quote": "the product records berth occupancy",
                "action_verb_quote": "records",
                "target_quote": "berth occupancy",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "order": 3,
                "actor_kind": "product",
                "actor_quote": "the berth map",
                "owner_system_quote": "Berth map",
                "event_quote": "the berth map shows the placement",
                "action_verb_quote": "shows",
                "target_quote": "the placement",
                "visible_result_quote": "the berth map shows the placement",
                "recovery_path": False,
            },
        ],
    )
    return response


def _carried_human_actor_response() -> tuple[str, dict[str, Any], dict[str, Any]]:
    first_path = (
        "A dock attendant Ivo enters a vessel tag; the attendant checks its status "
        "and sees the berth placement"
    )
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "first_path": first_path,
        "human_actors": ["dock attendant Ivo", "Mara"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Berth map"],
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "A dock attendant Ivo",
                "actor_fact_quote": "dock attendant Ivo",
                "event_quote": "A dock attendant Ivo enters a vessel tag",
                "action_verb_quote": "enters",
                "target_quote": "a vessel tag",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "the attendant",
                "actor_fact_quote": "dock attendant Ivo",
                "event_quote": "the attendant checks its status",
                "action_verb_quote": "checks",
                "target_quote": "its status",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "human",
                "actor_quote": "the attendant",
                "actor_fact_quote": "dock attendant Ivo",
                "event_quote": "sees the berth placement",
                "action_verb_quote": "sees",
                "target_quote": "the berth placement",
                "visible_result_quote": "the berth placement",
                "recovery_path": False,
            },
        ],
    )
    return source, response, intent


def test_authoring_accepts_only_byte_verified_source_citations() -> None:
    source = _source()
    provider = StructuredAuthoringProvider(_response(source))
    ticks = iter((0.0, 4.0))

    result = author_greenfield_intent(
        evidence_text=source,
        provider=provider,
        timeout_seconds=84,
        model_profile_id=RESCUE_PROFILE_ID,
        clock=lambda: next(ticks),
    )

    assert result.intent["first_path"] == _AUTHORED_FIRST_PATH
    assert result.first_path_relations[0]["actor_quote"] == "Dock attendant Ivo"
    assert result.first_path_relations[1]["owner_system_path"] == "/internal_systems/0"
    assert result.first_path_relations[-1]["visible_result_quote"] == "the berth map shows the placement"
    assert result.component_responsibility_relations == (
        {
            "responsibility_path": "/component_responsibilities/0",
            "responsibility_quote": "Record berth occupancy",
            "owner_system_path": "/internal_systems/0",
            "owner_system_quote": "Berth map",
            "first_path_event_order": 0,
            "responsibility_source": "accepted_fact",
        },
    )
    assert result.tier == "rescue"
    assert len(result.source_spans) == 19
    assert provider.calls == 1


def test_product_led_path_keeps_review_recipient_without_inventing_human_event() -> None:
    event = "The berth map prepares release readiness proof"
    proof = "release readiness proof for Engineering reviewer Mara"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "product_story": event,
        "first_path": event,
        "proof_boundary": proof,
        "human_actors": ["Engineering reviewer Mara"],
        "internal_systems": ["Berth map"],
        "success_metrics": ["release readiness proof"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Berth map"],
        first_path_relations=[
            {
                "actor_kind": "product",
                "actor_quote": "The berth map",
                "owner_system_quote": "Berth map",
                "event_quote": event,
                "target_quote": "release readiness proof",
                "visible_result_quote": "release readiness proof",
                "recovery_path": False,
            },
        ],
    )

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert [row["actor_kind"] for row in result.first_path_relations] == ["product"]
    assert [row["event_quote"] for row in result.first_path_relations] == [event]
    assert result.intent["human_actors"] == ["Engineering reviewer Mara"]
    assert result.intent["proof_boundary"] == proof
    assert result.intent["assumptions"] == []


def test_event_rejects_target_that_is_only_adjacent_in_a_selected_fact() -> None:
    event = (
        "coordinates referral intake, guardian consent, therapist assignment, "
        "care-plan readiness, visit evidence, and exception review"
    )
    target = "children served across multiple schools"
    product_story = f"A pediatric therapy agency practice workspace {event} for {target}"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "pediatric therapy agency practice workspace",
        "product_story": product_story,
        "first_path": event,
        "customer": target,
        "human_actors": ["therapy agency staff"],
        "internal_systems": [],
        "component_responsibilities": [],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    response = authored_response(
        intent,
        evidence_text=source,
        terminal_component_owner=str(intent["title"]),
        first_path_relations=[
            {
                "actor_kind": "product",
                "actor_quote": str(intent["title"]),
                "owner_system_quote": str(intent["title"]),
                "event_quote": event,
                "target_quote": target,
                "visible_result_quote": "visit evidence",
                "recovery_path": False,
            }
        ],
    )

    with pytest.raises(GreenfieldModelAuthoringError, match="ungrounded first-path event"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_event_target_stays_fail_closed_after_ordered_event_simplification() -> None:
    source = _source()
    response = _response(source)
    model_event_rows(response)[0]["target_quote"] = "release readiness proof"

    with pytest.raises(GreenfieldModelAuthoringError, match="ungrounded first-path event"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_selected_target_without_event_co_containment_stays_fail_closed() -> None:
    source = _source()
    response = _response(source)
    model_event_rows(response)[0]["target_quote"] = (
        "Source evidence preserves berth history"
    )

    with pytest.raises(GreenfieldModelAuthoringError, match="ungrounded first-path event"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_coordinated_events_derive_actor_presence_from_one_typed_fact_edge() -> None:
    source, response, intent = _carried_human_actor_response()

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert [row["actor_is_carried"] for row in result.first_path_relations] == [
        False,
        True,
        True,
    ]
    assert validate_first_path_relations(
        result.first_path_relations,
        first_path=str(result.intent["first_path"]),
        human_actors=intent["human_actors"],
        external_systems=intent["external_systems"],
        internal_systems=intent["internal_systems"],
        product_title=str(intent["title"]),
    ) == result.first_path_relations

    tampered = [dict(row) for row in result.first_path_relations]
    tampered[2]["actor_is_carried"] = False
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="ungrounded first-path relations"):
        validate_first_path_relations(
            tampered,
            first_path=str(result.intent["first_path"]),
            human_actors=intent["human_actors"],
            external_systems=intent["external_systems"],
            internal_systems=intent["internal_systems"],
            product_title=str(intent["title"]),
        )


@pytest.mark.parametrize("relation_index", [0, 1])
def test_typed_actor_fact_is_authoritative_without_event_surface_reparsing(
    relation_index: int,
) -> None:
    source, response, intent = _carried_human_actor_response()
    relation = model_event_rows(response)[relation_index]
    relation["actor_fact_quote"] = "Mara"

    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
        clock=lambda: 0.0,
    )

    assert result.first_path_relations[relation_index]["actor_quote"] == "Mara"
    assert result.first_path_relations[relation_index]["actor_fact_quote"] == "Mara"
    assert result.first_path_relations[relation_index]["actor_is_carried"] is True
    assert validate_first_path_relations(
        result.first_path_relations,
        first_path=str(result.intent["first_path"]),
        human_actors=intent["human_actors"],
        external_systems=intent["external_systems"],
        internal_systems=intent["internal_systems"],
        product_title=str(intent["title"]),
    ) == result.first_path_relations


def test_materialization_preserves_exact_event_fact_bytes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    source = _source()
    response = _response(source)
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(response),
        authoring_timeout_seconds=84,
        authoring_profile_id=RESCUE_PROFILE_ID,
    )

    assert candidate["first_path"] == _AUTHORED_FIRST_PATH
    for relation in candidate["authored_semantics"]["first_path_relations"]:
        start = relation["event_start_byte"]
        end = relation["event_end_byte"]
        assert _AUTHORED_FIRST_PATH.encode("utf-8")[start:end] == relation["event_quote"].encode("utf-8")


def test_verified_authoring_spans_become_the_product_intent_custody_source() -> None:
    source = _source()
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_response(source)),
        clock=lambda: 0.0,
    )
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
        source_text=source,
        source_format="operator_prompt",
        authored_source_spans=result.source_spans,
        authored_atomic_claims=result.atomic_claims,
        authored_source_sha256=result.source_sha256,
    )
    authority = product_intent_authority_from_envelope(envelope)

    assert authority["material_fields"]["first_path"]["source_span_ids"] == [
        "authoring:first_path:1:4",
        "authoring:first_path:2:5",
        "authoring:first_path:3:6",
    ]
    assert authority["atomic_facts"]
    action_values = {
        row["normalized_value"]
        for row in authority["atomic_facts"]
        if any(
            link["relation_role"] == "action_verb_quote"
            for link in row["projection_links"]
        )
    }
    assert action_values == set(_AUTHORED_FIRST_PATH.splitlines())
    first_event = _AUTHORED_FIRST_PATH.splitlines()[0]
    action_atom = next(
        row
        for row in authority["atomic_facts"]
        if row["normalized_value"] == first_event
        and any(
            link["relation_role"] == "action_verb_quote"
            for link in row["projection_links"]
        )
    )
    assert action_atom["categories"] == ["actions"]
    assert action_atom["polarity"] == "affirmed"
    assert action_atom["entailment_relationship"] == "exact_source_span"
    assert action_atom["source_span_refs"][0]["source_start_byte"] >= 0
    assert {
        "field": "first_path",
        "path": "/first_path",
        "value_sha256": hashlib.sha256(_AUTHORED_FIRST_PATH.encode("utf-8")).hexdigest(),
        "projection_start_byte": 0,
        "projection_end_byte": len(first_event.encode("utf-8")),
        "relation_order": 1,
        "relation_role": "action_verb_quote",
    } in action_atom["projection_links"]


def test_envelope_rejects_relation_rebound_to_a_duplicate_source_occurrence() -> None:
    event = "Dock attendant Ivo enters a vessel tag"
    source = f"{_source()} {event}."
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(_response(source)),
        clock=lambda: 0.0,
    )
    relations = [dict(row) for row in result.first_path_relations]
    duplicate_start = source.encode("utf-8").rfind(event.encode("utf-8"))
    relations[0]["source_start_byte"] = duplicate_start
    relations[0]["source_end_byte"] = duplicate_start + len(event.encode("utf-8"))
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }

    with pytest.raises(ValueError, match="relation source custody does not match"):
        build_product_intent_envelope(
            sealed_intent,
            source_text=source,
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )


def test_authored_custody_preserves_exact_unicode_markdown_and_deferred_actor_bytes() -> None:
    actor = "deferred café operator or dock steward"
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "**Harbor Café**",
        "first_path": (
            f"{actor} enters `berth-7` and the product records berth occupancy before "
            "the berth map shows the placement"
        ),
        "human_actors": [actor],
        "internal_systems": ["`berth-map`"],
    }
    source = ". ".join(
        [
            *(str(value) for key, value in intent.items() if key in _TEXT_FIELDS),
            *(str(row) for key, rows in intent.items() if key in _LIST_FIELDS for row in rows),
        ]
    ) + "."
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                component_responsibility_owners=["`berth-map`"],
            )
        ),
        clock=lambda: 0.0,
    )

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
        source_text=source,
        source_format="operator_prompt",
        authored_source_spans=result.source_spans,
        authored_atomic_claims=result.atomic_claims,
        authored_source_sha256=result.source_sha256,
    )

    actor_span = next(span for span in result.source_spans if span["section_key"] == "human_actors")
    expected_actor_bytes = actor.encode("utf-8")
    expected_actor_start = source.encode("utf-8").find(expected_actor_bytes)
    assert envelope["product_facts"]["title"] == "**Harbor Café**"
    assert envelope["product_facts"]["human_actors"] == [actor]
    assert "`berth-7`" in envelope["product_facts"]["first_path"]
    assert actor_span["source_start_byte"] == expected_actor_start
    assert actor_span["source_end_byte"] == expected_actor_start + len(expected_actor_bytes)
    assert actor_span["quote_sha256"] == hashlib.sha256(expected_actor_bytes).hexdigest()
    sealed_actor_span = next(
        span
        for span in envelope["source_evidence"]["spans"]
        if span["span_id"] == actor_span["span_id"]
    )
    assert sealed_actor_span["text"] == actor
    assert sealed_actor_span["text_sha256"] == hashlib.sha256(expected_actor_bytes).hexdigest()
