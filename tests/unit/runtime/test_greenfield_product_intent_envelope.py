"""Authored-only Product Intent envelope and authority contracts."""

from __future__ import annotations

import copy
import hashlib
import inspect
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
    AUTHORED_SEMANTICS_KEY,
    authored_relation_set_sha256,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoredIntent,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_FACTS_HASH_KEY,
    PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
    build_product_intent_envelope,
    is_product_intent_envelope,
    product_facts_from_envelope,
    product_facts_hash,
    product_facts_payload,
    product_intent_authority_from_envelope,
    rebind_authoritative_product_facts,
    require_product_intent_authority,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


_INTENT: dict[str, Any] = {
    "title": "Harbor Desk",
    "product_story": "Dock attendants need clear berth placement",
    "state_object": "berth occupancy",
    "first_path": (
        "Dock attendant Ivo enters a vessel tag and Berth map records berth occupancy "
        "before Berth map shows the placement"
    ),
    "proof_boundary": "Verify the placement and retention receipt",
    "problem": "Berth placement is hard to track",
    "customer": "Dock attendants",
    "opportunity": "One reviewable berth workflow",
    "product_view": "Harbor Desk gives dock attendants a berth workflow",
    "success_metrics": ["Berth map shows the placement"],
    "component_responsibilities": ["Record berth occupancy"],
    "human_actors": ["Dock attendant Ivo"],
    "external_systems": ["Harbor Ledger"],
    "internal_systems": ["Berth map"],
    "assumptions": [],
    "ambiguities": [],
    "non_goals": ["Do not manage vessel scheduling"],
    "evidence_requirements": ["Source evidence preserves berth history"],
    "operational_constraints": ["Retain source notes for seven years"],
}

_RELATIONS = (
    {
        "actor_kind": "human",
        "actor_fact_quote": "Dock attendant Ivo",
        "event_quote": "Dock attendant Ivo enters a vessel tag",
        "action_verb_quote": "enters",
        "target_quote": "a vessel tag",
        "visible_result_quote": "",
    },
    {
        "actor_kind": "product",
        "actor_fact_quote": "Berth map",
        "owner_system_quote": "Berth map",
        "event_quote": "Berth map records berth occupancy",
        "action_verb_quote": "records",
        "target_quote": "berth occupancy",
        "visible_result_quote": "",
    },
    {
        "actor_kind": "product",
        "actor_fact_quote": "Berth map",
        "owner_system_quote": "Berth map",
        "event_quote": "Berth map shows the placement",
        "action_verb_quote": "shows",
        "target_quote": "the placement",
        "visible_result_quote": "Berth map shows the placement",
    },
)


def _source() -> str:
    return ". ".join(
        str(row)
        for value in _INTENT.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."


def _authored_result(source: str) -> GreenfieldModelAuthoredIntent:
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                _INTENT,
                evidence_text=source,
                first_path_relations=_RELATIONS,
                component_responsibility_owners=["Berth map"],
            )
        ),
        model_profile_id=STANDARD_PROFILE_ID,
        clock=lambda: 0.0,
    )
    assert isinstance(result, GreenfieldModelAuthoredIntent)
    return result


def _authored_inputs() -> tuple[str, GreenfieldModelAuthoredIntent, dict[str, Any]]:
    source = _source()
    result = _authored_result(source)
    intent = {
        **result.intent,
        AUTHORED_SEMANTICS_KEY: authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }
    return source, result, intent


def _build_envelope(
    *,
    source: str | None = None,
    result: GreenfieldModelAuthoredIntent | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source is None or result is None or intent is None:
        source, result, intent = _authored_inputs()
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    return build_product_intent_envelope(
        intent,
        source_text=source,
        source_path=".odylith/runtime/greenfield/candidate-evidence.md",
        source_format="operator_prompt",
        model_authoring={
            "profile_id": profile.profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
        authored_source_spans=result.source_spans,
        authored_atomic_claims=result.atomic_claims,
        authored_source_sha256=result.source_sha256,
    )


def test_authored_envelope_preserves_exact_facts_spans_relations_and_authority() -> None:
    source, result, intent = _authored_inputs()
    envelope = _build_envelope(source=source, result=result, intent=intent)
    expected_relation_hash = authored_relation_set_sha256(
        result.first_path_relations,
        result.component_responsibility_relations,
        first_path_context_relations=result.first_path_context_relations,
    )

    assert envelope["schema_version"] == PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION
    assert envelope["product_facts"] == product_facts_payload(intent)
    assert envelope["decision_record"][PRODUCT_FACTS_HASH_KEY] == product_facts_hash(intent)
    assert envelope["custody_ledger"][AUTHORED_RELATION_SET_SHA256_KEY] == expected_relation_hash
    assert envelope["custody_ledger"]["atomic_facts"]
    assert envelope["materiality_gate"] == {
        "status": "passed",
        "blocked_fields": [],
        "clarification_policy": "block_only_material_unknowns",
    }
    for span in envelope["source_evidence"]["spans"]:
        start = span["source_start_byte"]
        end = span["source_end_byte"]
        assert source.encode("utf-8")[start:end] == span["text"].encode("utf-8")
        assert span["text_sha256"] == hashlib.sha256(span["text"].encode("utf-8")).hexdigest()

    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=".odylith/runtime/greenfield/candidate-intent.json",
        markdown_source_path=".odylith/runtime/greenfield/candidate-evidence.md",
    )
    require_product_intent_authority(authority)
    assert authority[AUTHORED_RELATION_SET_SHA256_KEY] == expected_relation_hash
    assert all(
        field["derivation"] == "exact_authored_projection"
        for field in authority["material_fields"].values()
    )
    assert product_facts_from_envelope(envelope, source_text=source) == envelope["product_facts"]


def test_envelope_construction_rejects_relation_free_input() -> None:
    with pytest.raises(ValueError, match="sealed model-authored semantics"):
        build_product_intent_envelope(
            _INTENT,
            source_text=_source(),
            source_format="operator_prompt",
        )


def test_envelope_rejects_source_digest_or_span_rebinding() -> None:
    source, result, intent = _authored_inputs()
    with pytest.raises(ValueError, match="evidence digest"):
        build_product_intent_envelope(
            intent,
            source_text=source + " changed",
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )

    rebound_spans = copy.deepcopy(list(result.source_spans))
    rebound_spans[0]["source_start_byte"] += 1
    with pytest.raises(ValueError, match="source custody is malformed"):
        build_product_intent_envelope(
            intent,
            source_text=source,
            source_format="operator_prompt",
            authored_source_spans=rebound_spans,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )

    rebound_projection = copy.deepcopy(list(result.source_spans))
    rebound_projection[0]["projection_path"] = "/product_story"
    with pytest.raises(ValueError, match="source custody is malformed"):
        build_product_intent_envelope(
            intent,
            source_text=source,
            source_format="operator_prompt",
            authored_source_spans=rebound_projection,
            authored_atomic_claims=result.atomic_claims,
            authored_source_sha256=result.source_sha256,
        )


def test_optional_human_fact_still_requires_exact_atomic_source_custody() -> None:
    source, result, intent = _authored_inputs()
    claims = copy.deepcopy(list(result.atomic_claims))
    human_claim = next(claim for claim in claims if claim["field"] == "human_actors")
    human_claim["source_start_byte"] += 1
    human_claim["source_end_byte"] += 1

    with pytest.raises(ValueError, match="atomic source custody does not match"):
        build_product_intent_envelope(
            intent,
            source_text=source,
            source_format="operator_prompt",
            authored_source_spans=result.source_spans,
            authored_atomic_claims=claims,
            authored_source_sha256=result.source_sha256,
        )


def test_envelope_rejects_relation_coordinates_rebound_after_authoring() -> None:
    source, result, intent = _authored_inputs()
    rebound = copy.deepcopy(intent)
    rebound[AUTHORED_SEMANTICS_KEY]["first_path_relations"][0]["event_start_byte"] += 1

    with pytest.raises(ValueError, match="ungrounded first-path relations"):
        _build_envelope(source=source, result=result, intent=rebound)


def test_source_and_authority_tampering_fail_closed() -> None:
    source, result, intent = _authored_inputs()
    envelope = _build_envelope(source=source, result=result, intent=intent)
    assert product_facts_from_envelope(envelope, source_text=source + " changed") is None

    altered = copy.deepcopy(envelope)
    altered["product_facts"]["state_object"] = "different state"
    assert product_facts_from_envelope(altered, source_text=source) is None
    with pytest.raises(ValueError, match="product facts hash mismatch"):
        product_intent_authority_from_envelope(altered)

    malformed = copy.deepcopy(envelope)
    malformed["product_facts"]["human_actors"] = ["Dock attendant Ivo", 7]
    assert product_facts_from_envelope(malformed, source_text=source) is None

    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path="candidate-intent.json",
        markdown_source_path="candidate-evidence.md",
    )
    authority[PRODUCT_FACTS_HASH_KEY] = "0" * 64
    with pytest.raises(ValueError, match="snapshot hash mismatch"):
        require_product_intent_authority(authority)


def test_current_schema_without_authored_relation_custody_is_not_an_envelope() -> None:
    source, result, intent = _authored_inputs()
    relation_free = _build_envelope(source=source, result=result, intent=intent)
    relation_free["custody_ledger"].pop(AUTHORED_RELATION_SET_SHA256_KEY)

    assert not is_product_intent_envelope(relation_free)
    assert product_facts_from_envelope(relation_free, source_text=source) is None
    with pytest.raises(ValueError, match="current authored-custody envelope"):
        product_intent_authority_from_envelope(relation_free)


def test_rebind_restores_only_exact_authored_facts() -> None:
    _, _, authored = _authored_inputs()
    rebound = rebind_authoritative_product_facts(
        {"title": "derived title", "quality_receipt": {"passed": True}},
        authoritative_intent=authored,
    )

    assert product_facts_payload(rebound) == product_facts_payload(authored)
    assert rebound["quality_receipt"] == {"passed": True}
    with pytest.raises(ValueError, match="sealed authored semantics"):
        rebind_authoritative_product_facts({}, authoritative_intent=_INTENT)


def test_product_fact_hash_preserves_exact_values_and_rejects_malformed_types() -> None:
    baseline = {"title": "Harbor Desk", "human_actors": ["Dock attendant Ivo"]}
    assert product_facts_hash(baseline) != product_facts_hash(
        {"title": " Harbor Desk", "human_actors": ["Dock attendant Ivo"]}
    )
    assert product_facts_hash(baseline) != product_facts_hash(
        {"title": "Harbor Desk", "human_actors": ["Dock attendant Ivo", "Reviewer"]}
    )
    with pytest.raises(ValueError, match="exact string list"):
        product_facts_payload({"human_actors": ["Dock attendant Ivo", 7]})
    with pytest.raises(ValueError, match="must be an exact string"):
        product_facts_payload({"title": {"text": "Harbor Desk"}})


def test_envelope_module_has_no_legacy_parser_or_regex_authority() -> None:
    source = inspect.getsource(greenfield_product_intent_envelope)
    forbidden_imports = (
        "greenfield_confirmed_intent_sections",
        "greenfield_confirmed_intent_completion",
        "greenfield_confirmed_backlog_text_model",
        "greenfield_confirmed_text",
        "greenfield_text",
    )
    assert all(name not in source for name in forbidden_imports)
    assert "import re" not in source
    for removed in (
        "is_legacy_product_intent_envelope",
        "product_facts_from_legacy_envelope",
        "canonical_product_facts_payload",
        "canonical_product_actor_rows",
        "product_intent_authority_from_intent",
    ):
        assert not hasattr(greenfield_product_intent_envelope, removed)
