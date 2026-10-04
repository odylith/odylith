"""One-pass host-candidate authority contracts."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
    admit_greenfield_host_candidate,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    HOST_CANDIDATE_FORMAT_VERSION,
    canonical_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    prepare_model_authoring_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    SOURCE_DUTY_DECISION_SET_VERSION,
    source_duty_entailment_task,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    clarification_response,
    host_candidate_response,
    materialize_complete_host_candidate,
    synthetic_source_duty_receipt,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _candidate() -> tuple[str, dict[str, object]]:
    source = _source()
    return source, host_candidate_response(_response(source), evidence_text=source)


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _accepted_ledger(ledger: dict, *, evidence_text: str) -> dict:
    preflight = preflight_greenfield_source_duty_ledger(
        ledger,
        evidence_text=evidence_text,
    )
    task = source_duty_entailment_task(preflight, evidence_text=evidence_text)
    decision_set = {
        "version": SOURCE_DUTY_DECISION_SET_VERSION,
        "verifier_task_sha256": task["verifier_task_sha256"],
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
        ledger,
        evidence_text=evidence_text,
        decision_set=decision_set,
    )


def _admit(source: str, candidate: dict[str, object]):
    return admit_greenfield_host_candidate(
        candidate,
        evidence_text=source,
        source_duty_receipt=synthetic_source_duty_receipt(
            candidate, evidence_text=source
        ),
    )


def test_contract_requires_one_complete_host_candidate() -> None:
    source, _ = _candidate()
    contract = greenfield_host_candidate_contract(source)
    authored = contract["candidate_schema"]["properties"]["result"]["anyOf"][0]

    assert contract["version"] == HOST_CANDIDATE_CONTRACT_VERSION
    assert contract["candidate_version"] == HOST_CANDIDATE_FORMAT_VERSION
    assert {"components", "source_precedence", "source_duty_binding"} <= set(
        authored["required"]
    )
    event = authored["properties"]["events"]["items"]
    assert event["required"] == ["actor_fact"]
    assert set(event["properties"]) == {"actor_fact"}
    assert "source_ledger_schema" in contract["source_ledger"]
    assert "Do not call a CLI, read or write files" in contract["source_ledger"]["task"]
    assert (
        "c must be a contiguous source excerpt containing q"
        in contract["source_ledger"]["task"]
    )
    assert (
        "contains only extra support; the compiler derives the event support"
        in contract["source_ledger"]["task"]
    )
    assert "Return candidate JSON only; do not call a CLI" in contract["task"]
    assert (
        "external controller has already inventoried source duties"
        in contract["requirements"][0]
    )
    assert "source-ledger-check" not in contract["requirements"][0]
    assert "review" not in contract["task"].casefold()
    assert contract["task"].endswith(
        "Emit compact JSON with no indentation or optional whitespace outside strings."
    )


def test_admission_validates_once_and_seals_raw_and_canonical_hashes() -> None:
    source, candidate = _candidate()
    canonical = canonical_greenfield_host_candidate(
        candidate,
        evidence_text=source,
        source_duty_receipt=synthetic_source_duty_receipt(
            candidate, evidence_text=source
        ),
    )

    authored, receipt = _admit(source, candidate)
    duty_receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)

    assert receipt == {
        "version": HOST_CANDIDATE_RECEIPT_VERSION,
        "contract_version": HOST_CANDIDATE_CONTRACT_VERSION,
        "canonical_version": GREENFIELD_INTENT_AUTHORING_VERSION,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "raw_candidate_sha256": _sha256(candidate),
        "canonical_candidate_sha256": _sha256(canonical),
        "source_duty_ledger_sha256": duty_receipt["ledger_sha256"],
        "source_duty_verifier_task_sha256": duty_receipt["verifier_task_sha256"],
        "source_duty_decision_set_sha256": duty_receipt["decision_set_sha256"],
        "source_duty_binding_sha256": _sha256(
            candidate["result"]["source_duty_binding"]
        ),
    }
    assert authored.semantic_model_call_count == 0
    assert [row["order"] for row in authored.first_path_relations] == [1, 2, 3]
    assert authored.source_precedence == ()
    assert authored.component_responsibility_relations


def test_source_binding_separates_first_path_from_supporting_event_custody(
    tmp_path,
) -> None:
    source = _source()
    response = _response(source)
    response["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3]
    candidate = host_candidate_response(response, evidence_text=source)

    authored, _receipt = _admit(source, candidate)

    assert authored.intent["first_path"] == (
        "Dock attendant Ivo enters a vessel tag\n" "the berth map shows the placement"
    )
    assert authored.intent["supporting_events"] == [
        "the product records berth occupancy"
    ]
    assert [row["order"] for row in authored.first_path_relations] == [1, 2, 3]
    assert any(
        row["field"] == "supporting_events" and row["relation_order"] == 2
        for row in authored.atomic_claims
    )

    materialized = materialize_complete_host_candidate(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=candidate,
    )
    assert materialized["first_path"] == authored.intent["first_path"]
    assert materialized["supporting_events"] == authored.intent["supporting_events"]

    polluted = copy.deepcopy(materialized)
    polluted["first_path"] = "\n".join(
        [polluted["first_path"], *polluted["supporting_events"]]
    )
    polluted["supporting_events"] = []
    with pytest.raises(ValueError):
        first_path_relations_from_intent(polluted)


def test_passive_timing_does_not_invent_a_precedence_edge() -> None:
    source, candidate = _candidate()
    candidate["result"]["source_precedence"] = []

    authored, _ = _admit(source, candidate)

    assert authored.source_precedence == ()


def test_candidate_tampering_fails_closed() -> None:
    source, candidate = _candidate()
    candidate["result"]["events"][0]["actor_fact"]["field"] = "not_a_source_actor"

    with pytest.raises((GreenfieldModelAuthoringError, ValueError)):
        _admit(source, candidate)


def test_ledger_owns_two_actions_with_one_complete_joined_citation() -> None:
    source, candidate = _candidate()
    ledger = copy.deepcopy(
        synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"]
    )
    joined = (
        "Dock attendant Ivo enters a vessel tag and the product records berth occupancy"
    )
    citation = {"quote": joined, "context": joined}
    for row in ledger["first_path_actions"][:2]:
        row["event_ref"] = citation
        row["source_refs"] = [citation, row["actor_ref"]]
    receipt = _accepted_ledger(ledger, evidence_text=source)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt[
        "ledger_sha256"
    ]

    authored, _ = admit_greenfield_host_candidate(
        candidate, evidence_text=source, source_duty_receipt=receipt
    )
    assert [row["action_verb_quote"] for row in authored.first_path_relations[:2]] == [
        "enters",
        "records",
    ]
    assert [row["event_quote"] for row in authored.first_path_relations[:2]] == [
        "Dock attendant Ivo enters a vessel tag",
        "the product records berth occupancy",
    ]
    assert joined not in authored.intent["first_path"]
    assert set(candidate["result"]["events"][0]) == {"actor_fact"}

    candidate["result"]["events"][0]["action_quote"] = "invented"
    with pytest.raises(ValueError, match="bound event is malformed"):
        admit_greenfield_host_candidate(
            candidate, evidence_text=source, source_duty_receipt=receipt
        )


def test_joined_source_clause_stages_once_with_both_action_relations(tmp_path) -> None:
    source = _source()
    prepared = prepare_model_authoring_evidence(prompt=source)
    evidence = prepared.evidence_source
    candidate = host_candidate_response(_response(evidence), evidence_text=evidence)
    ledger = copy.deepcopy(
        synthetic_source_duty_receipt(candidate, evidence_text=evidence)["ledger"]
    )
    joined = (
        "Dock attendant Ivo enters a vessel tag and the product records berth occupancy"
    )
    citation = {"quote": joined, "context": joined}
    for row in ledger["first_path_actions"][:2]:
        row["event_ref"] = citation
        row["source_refs"] = [citation, row["actor_ref"]]
    receipt = _accepted_ledger(ledger, evidence_text=evidence)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt[
        "ledger_sha256"
    ]

    materialized = materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=candidate,
        source_duty_receipt=receipt,
        prepared_evidence=prepared,
    )
    relations = materialized["authored_semantics"]["first_path_relations"]
    assert joined not in materialized["first_path"]
    assert "Dock attendant Ivo enters a vessel tag" in materialized["first_path"]
    assert "the product records berth occupancy" in materialized["first_path"]
    assert [row["action_verb_quote"] for row in relations[:2]] == ["enters", "records"]


def test_cross_role_joined_clause_keeps_first_path_and_system_duty_separate(
    tmp_path,
) -> None:
    source = _source()
    prepared = prepare_model_authoring_evidence(prompt=source)
    evidence = prepared.evidence_source
    response = _response(evidence)
    response["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3]
    candidate = host_candidate_response(response, evidence_text=evidence)
    ledger = copy.deepcopy(
        synthetic_source_duty_receipt(candidate, evidence_text=evidence)["ledger"]
    )
    joined = (
        "Dock attendant Ivo enters a vessel tag and the product records berth occupancy"
    )
    full_ref = {"quote": joined, "context": joined}
    path = ledger["first_path_actions"][0]
    system = ledger["system_duties"][0]
    for row in (path, system):
        local_event_ref = row["event_ref"]
        row["event_ref"] = full_ref
        row["source_refs"] = [full_ref, local_event_ref, row["actor_ref"]]
    receipt = _accepted_ledger(ledger, evidence_text=evidence)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt[
        "ledger_sha256"
    ]

    materialized = materialize_host_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=candidate,
        source_duty_receipt=receipt,
        prepared_evidence=prepared,
    )
    assert materialized["first_path"] == (
        "Dock attendant Ivo enters a vessel tag\n" "the berth map shows the placement"
    )
    assert materialized["supporting_events"] == ["the product records berth occupancy"]
    relations = materialized["authored_semantics"]["first_path_relations"]
    assert [row["action_verb_quote"] for row in relations] == [
        "enters",
        "records",
        "shows",
    ]


def test_unbound_legacy_candidate_is_rejected() -> None:
    source, candidate = _candidate()
    duty_receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    candidate["version"] = "odylith.greenfield.host-candidate-format.v18"
    candidate["result"].pop("source_duty_binding")

    with pytest.raises(ValueError):
        admit_greenfield_host_candidate(
            candidate,
            evidence_text=source,
            source_duty_receipt=duty_receipt,
        )


def test_material_ambiguity_asks_once_and_writes_nothing(tmp_path) -> None:
    source = (
        "Build a useful product, but the first task and visible result are unspecified."
    )
    response = clarification_response(
        question="Which task and result should the product prove first?",
        material_dimension="first_path",
        evidence_quotes=(),
        consistency_status="material_ambiguity",
    )
    candidate = host_candidate_response(response, evidence_text=source)
    prepared = prepare_model_authoring_evidence(prompt=source)

    with pytest.raises(GreenfieldClarificationRequired) as raised:
        materialize_host_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            host_candidate=candidate,
            source_duty_receipt=synthetic_source_duty_receipt(
                candidate, evidence_text=prepared.evidence_source
            ),
            prepared_evidence=prepared,
        )

    assert raised.value.required_fields == ("first_path",)
    assert not (tmp_path / ".odylith").exists()
    assert not (tmp_path / "odylith").exists()


def test_partial_component_constraint_overlap_is_rejected() -> None:
    source, candidate = _candidate()
    constraint = candidate["result"]["facts"]["operational_constraints"][0]
    quote = constraint["quote"]
    if len(quote) < 2:
        pytest.skip("fixture constraint is too short for a partial-overlap control")
    candidate["result"]["components"][0]["responsibilities"][0] = {
        "quote": quote[:-1],
        "occurrence": 1,
    }

    with pytest.raises(GreenfieldModelAuthoringError, match="overlap only"):
        _admit(source, candidate)


def test_exact_component_constraint_dual_role_is_retained() -> None:
    source, candidate = _candidate()
    constraint = candidate["result"]["facts"]["operational_constraints"][0]
    candidate["result"]["components"][0]["responsibilities"][0] = {
        "quote": constraint["quote"],
        "occurrence": 1,
    }

    authored, _ = _admit(source, candidate)

    exact = [
        row
        for row in authored.component_responsibility_relations
        if row["responsibility_quote"] == constraint["quote"]
    ]
    assert len(exact) == 1
    assert exact[0]["owner_system_quote"] == "Berth map"


def test_multisource_receipt_preserves_exact_combined_evidence_and_citations(
    tmp_path,
) -> None:
    prompt = _source()
    edit_evidence = (
        "Keep the accepted Harbor Desk scope; record this correction as evidence."
    )
    prepared = prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    candidate = host_candidate_response(
        _response(prepared.evidence_source),
        evidence_text=prepared.evidence_source,
    )
    authored, receipt = _admit(prepared.evidence_source, candidate)

    materialized = materialize_host_authored_intent(
        prompt=prompt,
        edit_evidence=edit_evidence,
        repo_root=tmp_path,
        host_candidate=candidate,
        source_duty_receipt=synthetic_source_duty_receipt(
            candidate, evidence_text=prepared.evidence_source
        ),
        prepared_evidence=prepared,
    )

    authority = materialized[PRODUCT_INTENT_AUTHORITY_KEY]
    assert prepared.source_document_count == 2
    assert (
        authority["operating_envelope"]["evidence_contract"]["observed"]["documents"]
        == 2
    )
    assert (
        receipt["source_sha256"]
        == hashlib.sha256(prepared.evidence_source.encode("utf-8")).hexdigest()
    )
    assert authority["markdown_source_sha256"] == receipt["source_sha256"]
    evidence_bytes = prepared.evidence_source.encode("utf-8")
    for span in authored.source_spans:
        exact = evidence_bytes[
            span["source_start_byte"] : span["source_end_byte"]
        ].decode("utf-8")
        assert exact == span["text"]


def test_canonical_candidate_hash_changes_on_semantic_tamper() -> None:
    source, candidate = _candidate()
    _, receipt = _admit(source, candidate)
    tampered = copy.deepcopy(candidate)
    tampered["result"]["ambiguities"] = ["A new unsealed ambiguity"]

    _, tampered_receipt = _admit(source, tampered)

    assert (
        tampered_receipt["canonical_candidate_sha256"]
        != receipt["canonical_candidate_sha256"]
    )
