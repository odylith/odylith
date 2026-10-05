"""Verified action display and exact source custody may differ without losing either."""

from __future__ import annotations

import copy

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import canonical_greenfield_host_candidate
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import validate_greenfield_authoring_response, GreenfieldModelAuthoringError
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import _verify_authored_atomic_claim_source, require_verified_source_action_relations
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    prepare_model_authoring_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import GreenfieldSourceDutyBindingError
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    authored_response,
    host_candidate_response,
    structural_design_fixture,
    synthetic_source_duty_receipt,
    synthetic_source_duty_receipt_for_ledger,
)


def _shared_clause_candidate() -> tuple[str, object, dict, dict]:
    intent = {
        "title": "Review Desk",
        "product_story": "Reviewers need a view of two definitions",
        "state_object": "scope and audience",
        "first_path": "A reviewer defines scope and audience. The Review Desk shows both definitions",
        "proof_boundary": "Verify both definitions",
        "problem": "Definitions are hard to review",
        "customer": "Reviewers",
        "opportunity": "A reviewable definition path",
        "product_view": "Review Desk shows both definitions",
        "success_metrics": ["The Review Desk shows both definitions"],
        "evidence_requirements": ["Keep definition history"],
        "operational_constraints": ["Keep source notes"],
        "component_responsibilities": [],
        "human_actors": ["A reviewer"],
        "external_systems": [],
        "internal_systems": ["Review Desk"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not publish definitions"],
    }
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    prepared = prepare_model_authoring_evidence(prompt=source)
    evidence = prepared.evidence_source
    clause = "A reviewer defines scope and audience"
    visible = "The Review Desk shows both definitions"
    response = authored_response(
        intent,
        evidence_text=evidence,
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_fact_quote": "A reviewer",
                "event_quote": clause,
                "action_verb_quote": "defines",
                "target_quote": "scope",
                "visible_result_quote": "",
            },
            {
                "actor_kind": "product",
                "actor_fact_quote": "Review Desk",
                "owner_system_quote": "Review Desk",
                "event_quote": visible,
                "action_verb_quote": "shows",
                "target_quote": "both definitions",
                "visible_result_quote": "both definitions",
            },
        ],
    )
    result = response["result"]
    result["facts"]["first_path"].insert(1, copy.deepcopy(result["facts"]["first_path"][0]))
    second_event = copy.deepcopy(result["events"][0])
    second_event["target_quote"] = "audience"
    result["events"].insert(1, second_event)
    result["terminal"]["event_order"] = 3
    result["terminal"]["result_fact"]["row"] = 3
    result["provisional_design"] = structural_design_fixture([1, 2, 3])
    candidate = host_candidate_response(response, evidence_text=evidence)
    ledger = copy.deepcopy(synthetic_source_duty_receipt(candidate, evidence_text=evidence)["ledger"])
    ledger["first_path_actions"][0]["statement"] = "A reviewer defines scope"
    ledger["first_path_actions"][1]["statement"] = "A reviewer defines audience"
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt["ledger_sha256"]
    return source, prepared, candidate, receipt


def test_shared_clause_stages_distinct_normalized_actions_with_exact_custody(tmp_path) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    materialized = materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=candidate,
        source_duty_receipt=receipt,
        prepared_evidence=prepared,
    )

    assert materialized["first_path"].splitlines()[:2] == [
        "A reviewer defines scope",
        "A reviewer defines audience",
    ]
    relations = materialized["authored_semantics"]["first_path_relations"]
    assert [(row["action_verb_quote"], row["target_quote"]) for row in relations[:2]] == [
        ("defines", "scope"),
        ("defines", "audience"),
    ]
    assert (relations[0]["source_start_byte"], relations[0]["source_end_byte"]) == (
        relations[1]["source_start_byte"], relations[1]["source_end_byte"]
    )


def test_tampered_normalized_statement_loses_accepted_receipt(tmp_path) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    receipt["ledger"]["first_path_actions"][1]["statement"] = "A reviewer approves audience"
    with pytest.raises(GreenfieldSourceDutyLedgerError):
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=candidate,
            source_duty_receipt=receipt,
            prepared_evidence=prepared,
        )


def test_inherited_verb_projects_verified_action_with_full_fragment_support(tmp_path) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    evidence = prepared.evidence_source
    ledger = copy.deepcopy(receipt["ledger"])
    ledger["first_path_actions"][0]["event_ref"]["quote"] = "A reviewer defines scope"
    action = ledger["first_path_actions"][1]
    action["event_ref"] = {"quote": "and audience", "context": ledger["first_path_actions"][1]["event_ref"]["context"]}
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=evidence)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt["ledger_sha256"]
    materialized = materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=candidate,
        source_duty_receipt=receipt,
        prepared_evidence=prepared,
    )
    assert materialized["first_path"].splitlines()[1] == "A reviewer defines audience"
    relation = materialized["authored_semantics"]["first_path_relations"][1]
    assert relation["action_verb_quote"] == "defines"
    assert evidence.encode()[relation["source_start_byte"]:relation["source_end_byte"]] == b"and audience"
    assert "defines" not in "and audience"


@pytest.mark.parametrize("field", ["action", "target", "actor_ref"])
def test_tampered_verified_action_atom_loses_receipt(tmp_path, field) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    atom = receipt["ledger"]["first_path_actions"][1]
    atom[field] = {"quote": "Review Desk", "context": "Review Desk"} if field == "actor_ref" else "approves"
    with pytest.raises(GreenfieldSourceDutyLedgerError):
        materialize_host_authored_intent(
            prompt=source, repo_root=tmp_path, host_candidate=candidate,
            source_duty_receipt=receipt, prepared_evidence=prepared,
        )


def _author_verified_candidate(source, prepared, candidate, receipt):
    canonical = canonical_greenfield_host_candidate(
        candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt,
    )
    return canonical, {
        "evidence_text": prepared.evidence_source,
        "elapsed_seconds": 1.0,
        "provider": {"kind": "host_native", "host": "codex", "model": "fixture-model"},
        "profile_id": STANDARD_PROFILE_ID,
        "effective_timeout_seconds": 180.0,
        "semantic_model_call_count": 1,
        "event_citations_are_event_owned": True,
        "first_path_event_orders": [1, 2, 3],
        "accepted_source_duties": receipt,
        "accepted_source_duty_binding": candidate["result"]["source_duty_binding"],
    }


@pytest.mark.parametrize("field,value", [("action_quote", "audience"), ("target_quote", "reviewer")])
def test_direct_graph_rejects_canonical_action_override(field, value) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    canonical, kwargs = _author_verified_candidate(source, prepared, candidate, receipt)
    canonical["result"]["events"][1][field] = value
    with pytest.raises(GreenfieldModelAuthoringError, match="verified source action"):
        validate_greenfield_authoring_response(canonical, **kwargs)


@pytest.mark.parametrize("tamper", ["role_value", "whole_slice", "narrow_source", "projection_offset"])
def test_normalized_atomic_claim_keeps_exact_full_source_and_verified_slice(tamper) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    canonical, kwargs = _author_verified_candidate(source, prepared, candidate, receipt)
    result = validate_greenfield_authoring_response(canonical, **kwargs)
    claims = copy.deepcopy(result.atomic_claims)
    claim = next(row for row in claims if row["relation_role"] == "action_verb_quote")
    assert claim["quote"] == "A reviewer defines scope and audience"
    assert claim["projection_quote"] == "defines"
    if tamper == "role_value":
        claim["projection_quote"] = "scope"
    elif tamper == "whole_slice":
        claim = next(row for row in claims if row["field"] == "first_path" and not row["relation_role"])
        claim["projection_quote"] = "defines"
    elif tamper == "narrow_source":
        claim["quote"] = "defines"
        claim["source_start_byte"] += len("A reviewer ".encode())
        claim["source_end_byte"] = claim["source_start_byte"] + len(b"defines")
    else:
        claim["projection_start_byte"] += 1
        claim["projection_end_byte"] += 1
    with pytest.raises(ValueError, match="atomic source custody"):
        _verify_authored_atomic_claim_source(
            claims, source_bytes=prepared.evidence_source.encode(), source_spans=result.source_spans,
        )


@pytest.mark.parametrize("field,value", [("action_verb_quote", "audience"), ("target_quote", "reviewer")])
def test_sealed_relation_rejects_verified_role_override(field, value) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    canonical, kwargs = _author_verified_candidate(source, prepared, candidate, receipt)
    result = validate_greenfield_authoring_response(canonical, **kwargs)
    relations = copy.deepcopy(result.first_path_relations)
    relations[1][field] = value
    with pytest.raises(ValueError, match="verified source action"):
        require_verified_source_action_relations(
            relations, source_duty={"ledger_receipt": receipt, "binding": candidate["result"]["source_duty_binding"], "lifecycle": {}},
            source_text=prepared.evidence_source,
        )


def test_candidate_cannot_replace_verified_human_actor_with_system(tmp_path) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    candidate["result"]["events"][1]["actor_fact"] = {"field": "internal_systems", "row": 1}
    with pytest.raises(GreenfieldSourceDutyBindingError):
        materialize_host_authored_intent(
            prompt=source, repo_root=tmp_path, host_candidate=candidate,
            source_duty_receipt=receipt, prepared_evidence=prepared,
        )


def test_renumbered_citation_slots_preserve_proposed_workflow_and_envelope(tmp_path) -> None:
    source, prepared, candidate, receipt = _shared_clause_candidate()
    baseline = materialize_host_authored_intent(
        prompt=source, repo_root=tmp_path / "baseline", host_candidate=candidate,
        source_duty_receipt=receipt, prepared_evidence=prepared,
    )
    result = candidate["result"]
    result["events"][0], result["events"][1] = result["events"][1], result["events"][0]
    bindings = result["source_duty_binding"]["first_path_actions"]
    bindings[0]["event_order"], bindings[1]["event_order"] = 2, 1
    result["provisional_design"]["first_run"]["event_orders"] = [2, 1, 3]
    materialized = materialize_host_authored_intent(
        prompt=source, repo_root=tmp_path / "renumbered", host_candidate=candidate,
        source_duty_receipt=receipt, prepared_evidence=prepared,
    )
    from odylith.runtime.domain_intelligence.greenfield_authored_first_run import authored_first_run_relations
    assert [row["event_quote"] for row in authored_first_run_relations(materialized)] == [
        row["event_quote"] for row in authored_first_run_relations(baseline)
    ]
    relations = materialized["authored_semantics"]["first_path_relations"]
    assert relations[0]["event_quote"] == "A reviewer defines audience"
    assert relations[1]["event_quote"] == "A reviewer defines scope"
    assert materialized["first_path"] == "\n".join(row["event_quote"] for row in relations)
    assert relations[0]["event_start_byte"] == 0
    assert relations[1]["event_start_byte"] == len(b"A reviewer defines audience\n")
