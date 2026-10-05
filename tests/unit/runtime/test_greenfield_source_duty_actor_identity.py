"""Source-owned performer identities survive custody and canonical binding."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    GreenfieldSourceDutyBindingError,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
    expand_compact_source_duty_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    compact_source_duty_view,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    authored_response,
    host_candidate_response,
    synthetic_source_duty_receipt,
    synthetic_source_duty_receipt_for_ledger,
)
from tests.unit.runtime.test_greenfield_source_duty_ledger import (
    EVIDENCE, _citation, _ledger, _yes_decisions,
)


@pytest.mark.parametrize("section", [
    "first_path_actions", "supporting_human_actions", "system_duties",
])
@pytest.mark.parametrize("failure", ["whole_statement", "outside_statement"])
def test_actor_identity_uses_one_shared_owner_in_preflight_and_compact(section, failure):
    ledger = _ledger()
    row = ledger[section][0]
    row["actor_ref"] = deepcopy(row["event_ref"])
    if failure == "whole_statement":
        row["statement"] = row["actor_ref"]["quote"]
    for check in (
        lambda: preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE),
        lambda: expand_compact_source_duty_ledger(
            compact_source_duty_view(ledger), evidence_text=EVIDENCE,
        ),
    ):
        with pytest.raises(GreenfieldSourceDutyLedgerError, match="actor identity"):
            check()


def test_containment_is_custody_and_semantic_actor_refusal_is_still_required():
    ledger = _ledger()
    first = ledger["first_path_actions"][0]
    first["actor_ref"] = deepcopy(first["event_ref"])
    first["statement"] = first["actor_ref"]["quote"] + "; scope is defined"
    # A whole sentence can be a proper substring. It remains the existing
    # independent verifier's job to refuse that semantic identity claim.
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    task = source_duty_entailment_task(preflight, evidence_text=EVIDENCE)
    assert "exactly ONE action performer" in task["task"]
    assert "whole action sentence" in task["task"]
    assert "additional performers" in task["task"]
    assert "not semantic atomicity" in task["task"]
    decisions = _yes_decisions(preflight)
    decisions["decisions"]["A1"]["verdict"] = "no"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="not affirmative"):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=EVIDENCE, decision_set=decisions,
        )


def test_role_context_resolves_pronoun_and_inherited_verb_without_microspans():
    evidence = "Human Actors: Dana is the reviewer. First Complete Path: She defines scope and audience."
    ledger = _ledger()
    ledger["evidence_controls"] = []
    ledger["system_duties"] = []
    event = _citation("She defines scope and audience")
    actor = _citation("Dana")
    role = _citation("Dana is the reviewer")
    for section, target in (("first_path_actions", "scope"), ("supporting_human_actions", "audience")):
        ledger[section][0].update({
            "event_ref": event, "actor_ref": actor, "role_refs": [role],
            "source_refs": [], "action": "defines", "target": target,
            "statement": f"Dana defines {target}",
        })
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=evidence)
    assert preflight["claims"][0]["actor_ref"] == preflight["claims"][1]["actor_ref"]
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=evidence,
        decision_set=_yes_decisions(preflight, evidence_text=evidence),
    )
    assert verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=evidence) == receipt


def test_pre_v47_actual_verifier_task_hash_cannot_receive_or_revalidate_credit():
    ledger = _ledger()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    decisions = _yes_decisions(preflight)
    receipt = validate_greenfield_source_duty_ledger(
        ledger, evidence_text=EVIDENCE, decision_set=decisions,
    )
    # Frozen from the real pre-v47 owner at immutable commit 9dc042dee,
    # using this exact valid ledger and authority source.
    old_task_hash = "efb7d64d8b4d1d9f4d9951f05388304dfd896801690f282ce5521a8a10857ef6"
    assert decisions["verifier_task_sha256"] != old_task_hash
    old = deepcopy(decisions)
    old["verifier_task_sha256"] = old_task_hash
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
        validate_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE, decision_set=old)
    receipt["decision_set"]["verifier_task_sha256"] = old_task_hash
    receipt["verifier_task_sha256"] = old_task_hash
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=EVIDENCE)


def five_actor_candidate():
    actors = ["resident contributor", "community facilitator", "moderation reviewer", "civic analyst", "publication editor"]
    steps = [
        (1, "opens", "a participation dossier"),
        (1, "publishes", "the participation prompt"),
        (0, "submits", "an opinion and publication choice"),
        (2, "records", "the moderation disposition"),
        (3, "records", "an aggregate insight"),
        (4, "verifies", "the review evidence"),
        (4, "publishes", "the approved insight"),
    ]
    events = [f"The {actors[index]} {verb} {target}" for index, verb, target in steps]
    intent = {
        "title": "Participation workspace",
        "product_story": "The team needs traceable participation insights",
        "state_object": "participation dossier",
        "first_path": ". ".join(events),
        "proof_boundary": "The approved insight is visible",
        "problem": "Participation evidence is hard to review",
        "customer": "The participation team",
        "opportunity": "One reviewable publication workflow",
        "product_view": "The workspace connects contribution and publication",
        "human_actors": actors,
        "success_metrics": [events[-1]],
        "operational_constraints": [], "evidence_requirements": [],
        "component_responsibilities": [], "internal_systems": [],
        "external_systems": [], "non_goals": [], "assumptions": [], "ambiguities": [],
    }
    source = "Participants: " + ", ".join(actors) + ". " + ". ".join(
        value for value in intent.values() if isinstance(value, str)
    ) + "."
    response = authored_response(
        intent, evidence_text=source, first_path_relations=[{
            "actor_kind": "human", "actor_fact_quote": actors[index],
            "event_quote": event, "action_verb_quote": verb, "target_quote": target,
            "visible_result_quote": event if order == 7 else "",
        } for order, ((index, verb, target), event) in enumerate(zip(steps, events), 1)],
    )
    candidate = host_candidate_response(response, evidence_text=source)
    return source, candidate, [actors[index] for index, _, _ in steps]


def test_five_performers_bind_seven_actions_and_repeated_citations_alias_only_themselves():
    source, candidate, expected = five_actor_candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    # A duplicate fact address for the same source actor remains a valid alias.
    candidate["result"]["facts"]["human_actors"].append(
        deepcopy(candidate["result"]["facts"]["human_actors"][1])
    )
    candidate["result"]["events"][0]["actor_fact"]["row"] = 6
    authored, _ = admit_greenfield_host_candidate(
        candidate, evidence_text=source, source_duty_receipt=receipt,
    )
    assert len(authored.intent["human_actors"]) == 5
    assert [row["actor_fact_quote"] for row in authored.first_path_relations] == expected
    paths = [row["actor_fact_path"] for row in authored.first_path_relations]
    assert paths[0] == paths[1] and paths[5] == paths[6]
    assert len(set(paths)) == 5
    actor_claims = [row for row in authored.atomic_claims if row["field"] == "human_actors"]
    assert {row["quote"] for row in actor_claims} == set(expected)
    action_actor_claims = [row for row in actor_claims if row["relation_role"] == "actor_fact_quote"]
    assert [row["quote"] for row in action_actor_claims] == expected
    assert [row["relation_order"] for row in action_actor_claims] == list(range(1, 8))
    assert [row["actor_ref"]["quote"] for row in receipt["ledger"]["first_path_actions"]] == expected


@pytest.mark.parametrize("mutation", ["wrong_actor", "paragraph", "human_as_system"])
def test_candidate_cannot_substitute_an_actor_paragraph_or_performer_role(mutation):
    source, candidate, _ = five_actor_candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    result = candidate["result"]
    if mutation == "wrong_actor":
        result["events"][0]["actor_fact"]["row"] = 1
    elif mutation == "paragraph":
        paragraph = ". ".join(row["statement"] for row in receipt["ledger"]["first_path_actions"])
        result["facts"]["human_actors"][1] = _citation(paragraph)
    else:
        result["facts"]["internal_systems"] = [deepcopy(result["facts"]["human_actors"][1])]
        result["events"][0]["actor_fact"] = {"field": "internal_systems", "row": 1}
    with pytest.raises(GreenfieldSourceDutyBindingError, match="source actor|incompatible event actor"):
        admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)


def test_actor_receipt_mutation_reenters_shared_identity_owner():
    source, candidate, _ = five_actor_candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    row = receipt["ledger"]["first_path_actions"][0]
    row["actor_ref"] = deepcopy(row["event_ref"])
    row["statement"] = row["actor_ref"]["quote"]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="actor identity"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source)


def test_atomic_actor_custody_preserves_six_fields_nine_safety_duties_and_both_withdrawal_effects():
    source, candidate, expected_actors = five_actor_candidate()
    ledger = synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"]
    fields = ["participation prompt", "consent state", "moderation disposition",
              "aggregate analysis", "editor approval", "final publication status"]
    rules = [
        "Only submissions with an affirmative publication choice may enter aggregate inputs",
        "Only the moderation reviewer may record the moderation disposition",
        "Only the publication editor may publish an approved insight",
        "Never publish a contributor identity alongside an opinion",
        "Retain the original participation prompt with aggregate evidence",
        "Use supplied demographics only for the participation purpose",
        "Keep moderation notes private",
        "The workspace does not issue official government decisions",
        "The workflow uses only supplied evidence and adds no external integration",
    ]
    field_statements = [f"The participation dossier retains {field}" for field in fields]
    withdrawal = "Withdrawal excludes the submission from future aggregate inputs and invalidates affected unpublished analysis"
    source += " " + ". ".join([*field_statements, *rules, withdrawal]) + "."
    ledger["state_fields"] = [{
        "id": f"F{index}", "source_refs": [_citation(statement)],
        "state_object": "participation dossier", "field": field, "meaning": field,
    } for index, (field, statement) in enumerate(zip(fields, field_statements), 1)]
    ledger["conditional_guards"] = [{
        "id": f"G{index}", "source_refs": [_citation(rule)],
        "trigger": "before the protected action", "protected_action": "aggregate or publish evidence", "rule": rule,
    } for index, rule in enumerate(rules[:3], 1)]
    ledger["boundaries"] = [{
        "id": f"B{index}", "source_refs": [_citation(rule)], "kind": "scope", "rule": rule,
    } for index, rule in enumerate(rules[3:], 1)]
    ledger["off_path_transitions"] = [{
        "id": "T1", "source_refs": [_citation(withdrawal)],
        "trigger": "withdrawal", "governed_object": "participation dossier", "effects": [
            {"field": "aggregate analysis", "change": "exclude the submission from future aggregate inputs", "observable_check": "future aggregate inputs omit the withdrawn submission"},
            {"field": "aggregate analysis", "change": "invalidate affected unpublished analysis", "observable_check": "affected unpublished analysis is invalid"},
        ],
    }]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    expanded = expand_compact_source_duty_ledger(compact_source_duty_view(ledger), evidence_text=source)
    assert expanded == ledger == receipt["ledger"]
    assert len(receipt["ledger"]["state_fields"]) == 6
    assert len(receipt["ledger"]["conditional_guards"]) + len(receipt["ledger"]["boundaries"]) == 9
    assert [row["actor_ref"]["quote"] for row in receipt["ledger"]["first_path_actions"]] == expected_actors
    assert verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source) == receipt


def test_contract_exposes_identity_custody_and_stable_source_actor_reuse():
    source, _, _ = five_actor_candidate()
    contract = greenfield_host_candidate_contract(source)
    assert contract["version"] == "odylith.greenfield.host-candidate-contract.v53"
    task = contract["source_ledger"]["task"]
    assert "only ONE source-owned performer identity" in task
    assert "proper literal substring of statement" in task
    assert "Reuse one canonical actor citation" in task
