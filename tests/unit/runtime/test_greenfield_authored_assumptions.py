"""Decision copy remains useful without promoting assumptions to accepted facts."""

from __future__ import annotations

import copy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    assumption_rows,
    decision_copy,
    require_decision_assumptions,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import authored_semantics_mapping
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import render_candidate_intent_markdown
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import author_greenfield_intent
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    build_product_intent_envelope,
    product_facts_hash,
    product_facts_payload,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import StructuredAuthoringProvider
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


_DECISIONS = [
    {"applies_to": "problem", "statement": "Dock attendants need to keep vessel placement and berth occupancy consistent."},
    {"applies_to": "customer", "statement": "Marine operations leaders are the primary beneficiaries of the berth record."},
    {"applies_to": "opportunity", "statement": "A reviewable berth record can connect each placement to its retention receipt."},
    {"applies_to": "product_view", "statement": "The workspace should carry a vessel entry through occupancy recording to the visible berth map."},
]


def _authored():
    source = _source()
    response = _response(source)
    for row in _DECISIONS:
        response["result"]["facts"][row["applies_to"]] = None
    response["result"]["assumptions"] = copy.deepcopy(_DECISIONS)
    authored = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(response),
    )
    return source, authored


def test_decision_assumptions_keep_their_type_and_custody() -> None:
    source, authored = _authored()
    intent = dict(authored.intent)
    intent["authored_semantics"] = authored_semantics_mapping(
        authored.first_path_relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
    )
    assert intent["problem"] == intent["opportunity"] == intent["product_view"] == ""
    assert intent["assumptions"] == _DECISIONS
    envelope = build_product_intent_envelope(
        intent,
        source_text=source,
        source_path="evidence.txt",
        authored_source_spans=authored.source_spans,
        authored_atomic_claims=authored.atomic_claims,
        authored_source_sha256=authored.source_sha256,
    )
    assert envelope["product_facts"]["assumptions"] == _DECISIONS
    custody = envelope["custody_ledger"]["fields"]["assumptions"]
    assert custody["custody_state"] == "assumption"
    assert custody["product_claim_span_ids"] == []
    assert not any(row["projection_path"].startswith("/assumptions/") for row in authored.atomic_claims)
    assert all(row["section_key"] != "assumptions" for row in authored.source_spans)
    assert "Assumption" in decision_copy(intent, "problem")
    preview = render_candidate_intent_markdown(intent)
    for row in _DECISIONS:
        label = row["applies_to"].replace("_", " ").capitalize()
        assert f"{label} assumption — {row['statement']}" in preview
    assert "'applies_to'" not in preview
    changed = copy.deepcopy(intent)
    changed["assumptions"][0]["applies_to"] = "opportunity"
    changed["assumptions"][2]["applies_to"] = "problem"
    assert product_facts_hash(intent) != product_facts_hash(changed)
    assert render_candidate_intent_markdown(changed) != preview


def test_radar_required_decisions_point_to_assumptions_not_missing_facts() -> None:
    _, authored = _authored()
    intent = dict(authored.intent)
    intent["authored_semantics"] = authored_semantics_mapping(
        authored.first_path_relations,
        authored.component_responsibility_relations,
        first_path_context_relations=authored.first_path_context_relations,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={}, release_selector="0.0.1", confirmed_intent=intent,
    )
    project = next(row for row in proposal["backlog"] if row["workstream_role"] == "project")
    refs = project["authored_workstream_semantics"]["rendered_field_refs"]
    for index, decision in enumerate(_DECISIONS):
        field = decision["applies_to"]
        assert refs[field] == [f"/assumptions/{index}"]
        assert "Assumption" in project[field]
        assert decision["statement"] in project[field]
        assert decision["statement"] not in project["radar_sections"]["Assumptions"]
    assert project["radar_sections"]["Assumptions"] == "- No additional assumptions."
    assert "Validate this gap" not in str(proposal)
    assert proposal["project_brief"]["purpose"] == decision_copy(intent, "problem")
    customer_index = next(
        index
        for index, decision in enumerate(_DECISIONS)
        if decision["applies_to"] == "customer"
    )
    customer_ref = f"/assumptions/{customer_index}"
    child_rows = [
        row for row in proposal["backlog"] if row["workstream_role"] != "project"
    ]
    assert child_rows
    for row in child_rows:
        semantics = row["authored_workstream_semantics"]
        assert semantics["rendered_field_refs"]["customer"] == [customer_ref]
        assert customer_ref in semantics["shared_fact_refs"]
        assert row["customer"] == (
            "Assumption — Marine operations leaders are the primary beneficiaries "
            "of the berth record."
        )
        assert row["customer"] != "Dock attendant Ivo"


@pytest.mark.parametrize("rows", [
    ["untyped legacy assumption"],
    [{"applies_to": "authority", "statement": "Grant authority."}],
    [{"applies_to": "problem", "statement": ""}],
    [_DECISIONS[0], _DECISIONS[0]],
])
def test_invalid_or_competing_assumptions_fail_closed(rows) -> None:
    with pytest.raises(ValueError):
        assumption_rows(rows)


def test_decision_cannot_claim_both_fact_and_assumption() -> None:
    with pytest.raises(ValueError, match="one fact or one assumption"):
        require_decision_assumptions({"problem": "A cited problem", "assumptions": _DECISIONS})
    with pytest.raises(ValueError, match="one fact or one assumption"):
        require_decision_assumptions({"assumptions": []})
    assert product_facts_payload({"assumptions": _DECISIONS})["assumptions"] == _DECISIONS


def test_customer_decision_requires_exactly_one_fact_or_targeted_assumption() -> None:
    decisions = {
        "problem": "A durable receipt is needed.",
        "customer": "",
        "opportunity": "A receipt makes the result reviewable.",
        "product_view": "The product exposes the receipt.",
    }
    customer_assumption = {
        "applies_to": "customer",
        "statement": "Service owners are the primary beneficiaries.",
    }

    with pytest.raises(ValueError, match="customer requires one fact or one assumption"):
        require_decision_assumptions({**decisions, "assumptions": []})

    require_decision_assumptions(
        {**decisions, "assumptions": [customer_assumption]}
    )

    with pytest.raises(ValueError, match="customer requires one fact or one assumption"):
        require_decision_assumptions(
            {
                **decisions,
                "customer": "Service owners",
                "assumptions": [customer_assumption],
            }
        )


def test_confirmation_exposes_source_stated_decision_roles() -> None:
    decisions = {
        "problem": "Reviewers lose the connection between a batch and its decision.",
        "customer": "Reviewers",
        "opportunity": "Keep a decision traceable to its batch.",
        "product_view": "Reviewers see a batch and its decision together.",
    }
    preview = render_candidate_intent_markdown(decisions)
    for field, value in decisions.items():
        label = field.replace("_", " ").capitalize()
        assert f"- {label}: {value}" in preview
        changed = {**decisions, field: f"Changed {value}"}
        assert render_candidate_intent_markdown(changed) != preview
