"""Source-owned performer identities survive custody and canonical binding."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
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
    evidence = "Review workspace. Human Actors: Dana is the reviewer. First Complete Path: She defines scope and audience."
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
    authored, _ = admit_greenfield_host_candidate(
        candidate, evidence_text=source, source_duty_receipt=receipt,
    )
    assert len(authored.intent["human_actors"]) == 5
    assert [row["actor_fact_quote"] for row in authored.source_event_relations] == expected
    paths = [row["actor_fact_path"] for row in authored.source_event_relations]
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
        result["events"] = [{"actor_fact": {"field": "human_actors", "row": 1}}]
    elif mutation == "paragraph":
        paragraph = ". ".join(row["statement"] for row in receipt["ledger"]["first_path_actions"])
        result["events"] = [{"actor_fact": {"field": "human_actors", "row": 2}}]
        result["facts"]["human_actors"][1] = _citation(paragraph)
    else:
        result["facts"]["internal_systems"] = [deepcopy(result["facts"]["human_actors"][1])]
        # Supplemental facts cannot change a source-owned performer kind.
    with pytest.raises(GreenfieldSourceDutyBindingError, match="must not author source events|incompatible source performer kind"):
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
    assert contract["version"] == "odylith.greenfield.host-candidate-contract.v57"
    task = contract["source_ledger"]["task"]
    assert "only ONE source-owned performer identity" in task
    assert "proper literal substring of statement" in task
    assert "Reuse one canonical actor citation" in task


def _thirteen_duty_catalog_case():
    source, candidate, _ = five_actor_candidate()
    ledger = synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"]
    ledger["product_identity"]["source_ref"]["context"] = "Participation workspace. The team needs traceable participation insights"
    facilitator = deepcopy(ledger["first_path_actions"][0]["actor_ref"])
    supporting = "The community facilitator checks the contribution evidence"
    system_names = ["Inbox processor", "Redaction service", "Insights renderer", "External archive", "Participation workspace"]
    role_context = "Duty systems: " + ", ".join(system_names) + "."
    system_events = [f"{name} retains evidence item {index}" for index, name in enumerate(system_names, 1)]
    source += " " + supporting + ". " + role_context + " " + ". ".join(system_events) + "."
    ledger["supporting_human_actions"] = [{
        "id": "h1", "source_refs": [], "statement": supporting,
        "event_ref": _citation(supporting), "actor_ref": facilitator,
        "role_refs": [_citation(supporting)], "action": "checks", "target": "the contribution evidence",
    }]
    ledger["system_duties"] = [{
        "execution_kind": "discrete_action",
        "id": f"d{index}", "source_refs": [], "statement": event,
        "event_ref": _citation(event), "actor_ref": _citation(name, role_context),
        "role_refs": [_citation(role_context)], "action": "retains", "target": f"evidence item {index}",
        "performer_role": "external_system" if index == 4 else "internal_system",
    } for index, (name, event) in enumerate(zip(system_names, system_events), 1)]
    return source, synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source), candidate


def test_source_catalog_owns_all_thirteen_events_and_five_human_identities():
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog
    source, receipt, _ = _thirteen_duty_catalog_case()
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    assert len(catalog["events"]) == 13
    assert len(catalog["facts"]["human_actors"]) == 5
    assert [event["event_order"] for event in catalog["events"]] == list(range(1, 14))
    assert len({event["duty_id"] for event in catalog["events"]}) == 13
    assert catalog["events"][0]["actor_fact"] == catalog["events"][1]["actor_fact"] == catalog["events"][7]["actor_fact"]
    assert catalog["events"][5]["actor_fact"] == catalog["events"][6]["actor_fact"]
    editor = catalog["events"][6]["actor_fact"]
    assert catalog["facts"][editor["field"]][editor["row"] - 1]["quote"] == "publication editor"
    assert [event["performer_role"] for event in catalog["events"][8:]] == [
        "internal_system", "internal_system", "internal_system", "external_system", "internal_system",
    ]


def test_catalog_keeps_exact_occurrence_identity_across_different_locator_contexts():
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog
    source, receipt, _ = _thirteen_duty_catalog_case()
    ledger = deepcopy(receipt["ledger"])
    row = ledger["supporting_human_actions"][0]
    original = row["actor_ref"]["context"]
    start = source.index(original)
    row["actor_ref"]["context"] = source[max(0, start - 4):start + len(original) + 4]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    assert catalog["events"][0]["actor_fact"] == catalog["events"][7]["actor_fact"]
    assert len(catalog["facts"]["human_actors"]) == 5


@pytest.mark.parametrize("damage", ["missing_system_kind", "human_system_kind", "conflicting_kind", "old_receipt", "source_hash"])
def test_fresh_catalog_refuses_missing_or_conflicting_typed_source_authority(damage):
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog
    source, receipt, _ = _thirteen_duty_catalog_case()
    ledger = deepcopy(receipt["ledger"])
    if damage == "missing_system_kind":
        del ledger["system_duties"][0]["performer_role"]
    elif damage == "human_system_kind":
        ledger["system_duties"][0]["performer_role"] = "human_actor"
    elif damage == "conflicting_kind":
        ledger["first_path_actions"][0]["performer_role"] = "internal_system"
    elif damage == "old_receipt":
        receipt["version"] = "odylith.greenfield.source-duty-ledger-receipt.v7"
    else:
        receipt["source_sha256"] = "0" * 64
    with pytest.raises((GreenfieldSourceDutyLedgerError, GreenfieldSourceDutyBindingError)):
        if damage in {"missing_system_kind", "human_system_kind", "conflicting_kind"}:
            receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
        project_greenfield_source_event_catalog(receipt, evidence_text=source)


def test_supplemental_beneficiary_survives_without_renumbering_source_performers():
    source, candidate, expected = five_actor_candidate()
    source += " A research observer receives the approved insight."
    candidate["result"]["facts"]["human_actors"] = [_citation("research observer")]
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    candidate["result"]["source_duty_binding"].update(
        source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"],
    )
    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    assert authored.intent["human_actors"][-1] == "research observer"
    assert len(authored.intent["human_actors"]) == 6
    assert [row["actor_fact_quote"] for row in authored.source_event_relations] == expected
    assert all(row["actor_fact_path"] != "/human_actors/5" for row in authored.source_event_relations)


@pytest.mark.parametrize("field", ["human_actors", "external_systems"])
def test_supplemental_title_cannot_promote_a_verified_nonproduct_performer(field):
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
        project_greenfield_source_event_catalog, source_owned_greenfield_actor_facts,
    )
    source, receipt, candidate = _thirteen_duty_catalog_case()
    ledger = deepcopy(receipt["ledger"])
    ledger["system_duties"].pop()  # This catalog has no product-title performer.
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    supplemental = deepcopy(candidate["result"]["facts"])
    supplemental["title"] = deepcopy(catalog["facts"][field][0])
    with pytest.raises(GreenfieldSourceDutyBindingError, match="must not author the source-owned product identity"):
        source_owned_greenfield_actor_facts(catalog, supplemental=supplemental, evidence_text=source)


@pytest.mark.parametrize("internal_alias", [False, True])
def test_fresh_candidate_cannot_supply_even_a_nonperformer_or_exact_internal_title(internal_alias):
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
        project_greenfield_source_event_catalog, source_owned_greenfield_actor_facts,
    )
    source, receipt, candidate = _thirteen_duty_catalog_case()
    ledger = deepcopy(receipt["ledger"])
    nonperforming_title = ledger["system_duties"].pop()["actor_ref"]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    events = deepcopy(catalog["events"])
    supplemental = deepcopy(candidate["result"]["facts"])
    supplemental["title"] = deepcopy(catalog["facts"]["internal_systems"][0] if internal_alias else nonperforming_title)
    with pytest.raises(GreenfieldSourceDutyBindingError, match="must not author the source-owned product identity"):
        source_owned_greenfield_actor_facts(catalog, supplemental=supplemental, evidence_text=source)
    assert catalog["events"] == events


def test_same_label_at_distinct_source_occurrences_is_not_interned_by_text():
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog
    source, receipt, _ = _thirteen_duty_catalog_case()
    ledger = deepcopy(receipt["ledger"])
    h1 = ledger["supporting_human_actions"][0]
    h1["actor_ref"] = _citation("community facilitator", h1["event_ref"]["quote"])
    # A synthetic affirmative decision only exercises the compiler identity key.
    # The real source-only verifier must refuse this inconsistent canonical pointer.
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    assert catalog["events"][0]["actor_fact"] != catalog["events"][7]["actor_fact"]
    assert len(catalog["facts"]["human_actors"]) == 6


def test_same_quote_at_another_actor_path_cannot_rebind_a_sealed_source_action():
    from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_verified_source_action_relations
    from tests.unit.runtime.greenfield_model_authoring_fixtures import source_duty_fixture
    source, candidate, _ = five_actor_candidate()
    other_identity = "Additional observer identity: community facilitator."
    source += " " + other_identity
    candidate["result"]["facts"]["human_actors"].append(_citation("community facilitator", other_identity))
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    candidate["result"]["source_duty_binding"].update(
        source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"],
    )
    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    custody = source_duty_fixture(candidate, evidence_text=source)
    relations = deepcopy(authored.source_event_relations)
    assert authored.intent["human_actors"][5] == relations[0]["actor_fact_quote"]
    relations[0]["actor_fact_path"] = "/human_actors/5"
    with pytest.raises(ValueError, match="actor path differs from its frozen source catalog"):
        require_verified_source_action_relations(relations, source_duty=custody, source_text=source)


@pytest.mark.parametrize("damage", ["actor_path", "source_occurrence", "missing_actor_atom"])
def test_full_transaction_catalog_guard_rejects_actor_path_and_source_custody_forgery(tmp_path, damage):
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import _require_host_candidate_authority_binding
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction
    transaction = _transaction(repo_root=tmp_path)
    authority = deepcopy(transaction.intent_authority)
    proposal = deepcopy(transaction.proposal)
    if damage == "actor_path":
        relation = proposal["intent"]["authored_semantics"]["source_event_relations"][0]
        relation["actor_fact_path"] = "/human_actors/99"
    else:
        actor_atoms = [atom for atom in authority["atomic_facts"] if any(
            link["path"] == "/human_actors/0" and link["relation_order"] == 0
            for link in atom["projection_links"])]
        assert len(actor_atoms) == 1
        if damage == "missing_actor_atom":
            authority["atomic_facts"].remove(actor_atoms[0])
        else:
            actor_atoms[0]["source_span_refs"][0]["source_start_byte"] += 1
            actor_atoms[0]["source_span_refs"][0]["source_end_byte"] += 1
    # This real compiled transaction's shared full readback guard must refuse
    # independently of outer transaction/atom hash checks.
    with pytest.raises(ValueError, match="source catalog|source performer custody|actor fact"):
        _require_host_candidate_authority_binding(
            transaction.quality_manifest, authority, proposal=proposal, passive=True,
        )


def test_independent_identity_and_internal_performer_keep_separate_addresses():
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    source, candidate = _candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    assert authored.intent["title"] == "Harbor Desk"
    assert authored.source_event_relations[1]["actor_fact_path"] == authored.source_event_relations[2]["actor_fact_path"] == "/internal_systems/0"
    assert authored.source_event_relations[1]["actor_kind"] == "product"


def test_candidate_title_cannot_redirect_a_performer_to_another_occurrence():
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    source, candidate = _candidate()
    context = "Harbor Ledger. Berth map. Do not manage vessel scheduling."
    for atom in candidate.source_action_atoms:
        if atom["actor_ref"]["quote"] == "Berth map":
            atom["actor_ref"]["context"] = context
    candidate["result"]["facts"]["internal_systems"][0]["context"] = context
    source += " Additional product label: Berth map."
    candidate["result"]["facts"]["title"] = _citation("Berth map", "Additional product label: Berth map.")
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    candidate["result"]["source_duty_binding"].update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    with pytest.raises(ValueError, match="source-owned identity"):
        admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)


def test_retired_product_title_performer_role_refuses_before_candidate():
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    source, candidate = _candidate()
    ledger = synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"]
    ledger["first_path_actions"][1]["performer_role"] = "product_title"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="performer_role"):
        synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)


@pytest.mark.parametrize("basis, phrase", [
    ("explicit_name", "Harbor Review"),
    ("product_description", "harbor berth-assignment workspace"),
])
def test_source_identity_is_independent_of_product_performing_an_event(basis, phrase):
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog
    source, candidate = _candidate()
    source = f"Build a {phrase}. " + source
    candidate.product_identity = {"basis": basis, "source_ref": _citation(phrase)}
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    candidate["result"]["source_duty_binding"].update(
        source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    assert authored.intent["title"] == phrase
    assert len(catalog["events"]) == len(candidate.source_action_atoms)
    assert all(event["actor_fact_path"] != "/title" for event in catalog["events"])
    assert not any(actor["quote"] == phrase for actor in catalog["performers"])
    assert "title" not in candidate["result"]["facts"]
    assert set(receipt["decision_set"]["decisions"]) == {row["id"] for row in receipt["ledger"]["first_path_actions"]}


@pytest.mark.parametrize("verdict", ["no", "uncertain"])
def test_source_verifier_can_refuse_generic_or_background_identity_without_candidate_work(verdict):
    ledger = _ledger()
    source = EVIDENCE + " Background repository: product."
    ledger["product_identity"] = {"basis": "explicit_name", "source_ref": _citation("product")}
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source)
    assert "background repository" in task["task"] and "generic 'product'" in task["task"]
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions["product_identity"]["verdict"] = verdict
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="identity decision is not affirmative"):
        validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions)


def test_source_identity_claim_cannot_collide_with_a_duty_id_or_escape_its_hash():
    ledger = _ledger()
    ledger["first_path_actions"][0]["id"] = "product_identity"
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE)
    receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE, decision_set=_yes_decisions(preflight))
    assert receipt["decision_set"]["product_identity"] == {"verdict": "yes"}
    assert "product_identity" in receipt["decision_set"]["decisions"]
    changed = deepcopy(ledger)
    changed["product_identity"]["basis"] = "product_description"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
        validate_greenfield_source_duty_ledger(changed, evidence_text=EVIDENCE, decision_set=receipt["decision_set"])


def test_sealed_readback_rejects_forged_independent_identity_span(tmp_path):
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import _require_host_candidate_authority_binding
    transaction = _transaction(repo_root=tmp_path)
    authority = deepcopy(transaction.intent_authority)
    identity = [atom for atom in authority["atomic_facts"] if any(
        link["path"] == "/title" and link["relation_order"] == 0
        for link in atom["projection_links"])]
    assert len(identity) == 1
    for ref in identity[0]["source_span_refs"]:
        ref["source_start_byte"] += 1
        ref["source_end_byte"] += 1
    with pytest.raises(ValueError, match="source performer custody"):
        _require_host_candidate_authority_binding(transaction.quality_manifest, authority,
                                                  proposal=transaction.proposal, passive=True)
