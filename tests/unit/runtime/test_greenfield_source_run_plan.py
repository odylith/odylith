"""Source-owned complete runs preserve typed facts and exact canonical custody."""

from copy import deepcopy
import hashlib
import json

from jsonschema import Draft202012Validator
import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate, greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    canonical_greenfield_host_candidate, greenfield_host_candidate_schema,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import source_event_relations_from_intent
from odylith.runtime.domain_intelligence.greenfield_authored_first_run import authored_first_run_relations, authored_checkpoint_text
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_VERSION, preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger, verify_greenfield_source_duty_ledger_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_source_run_plan import project_source_run_plan
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import GreenfieldModelAuthoringError
from odylith.runtime.domain_intelligence.greenfield_source_duty_authoring import decode_source_duty_inventory
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    affirmative_source_plan_fixture, host_candidate_response, synthetic_source_duty_receipt,
    synthetic_source_duty_receipt_for_ledger, source_duty_authoring_fixture,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _source, _response


def _carrier_case(field, *, source=None):
    source = source or _source()
    response = _response(source)
    result = response["result"]
    if field != "first_path":
        selected = result["facts"][field]
        quote = selected[0]["quote"] if isinstance(selected, list) else selected["quote"]
        result["terminal"].update(result_fact={"field": field, "row": 1},
                                  result_quote=quote, result_occurrence=1)
    candidate = host_candidate_response(response, evidence_text=source)
    return source, candidate, synthetic_source_duty_receipt(candidate, evidence_text=source)


def _transaction_for_intent(intent, root):
    """Exercise the real compiler/readback boundary with a synthetic test package."""
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        build_product_create_transaction, product_create_transaction_to_dict,
        product_create_transaction_from_dict,
    )
    from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
    from tests.unit.runtime.test_greenfield_create_transaction import _package, _seal_test_package
    from tests.unit.runtime.greenfield_authored_proposal_fixtures import approved_authored_quality_manifest_fixture
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)
    from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings
    proposal = attach_project_intelligence_bindings(proposal)
    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    package = _seal_test_package(_package(proposal, repo_root=root), repo_root=root)
    transaction = build_product_create_transaction(proposal=proposal, release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []}, prewrite_package=package,
        backlog_result=package.backlog_result or {}, intent_authority=authority, repo_root=root,
        quality_manifest=approved_authored_quality_manifest_fixture(intent_authority=authority, proposal=proposal))
    assert product_create_transaction_from_dict(product_create_transaction_to_dict(transaction)).transaction_hash == transaction.transaction_hash
    return transaction


@pytest.mark.parametrize("field", ["first_path", "product_story", "opportunity", "product_view", "success_metrics", "proof_boundary"])
def test_every_existing_result_carrier_keeps_independent_proof_and_canonical_identity(tmp_path, field):
    prompt = _source()
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source, candidate, receipt = _carrier_case(field, source=prepared.evidence_source)
    Draft202012Validator(greenfield_host_candidate_schema()).validate(candidate)
    before = json.dumps(candidate, sort_keys=True)
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    assert canonical["version"].endswith(".v80")
    assert canonical["result"]["terminal"]["result_fact"] == {"field": field, "row": 3 if field == "first_path" else 1}
    assert authored.intent["proof_boundary"] == "Verify the placement and retention receipt"
    if field != "proof_boundary":
        assert canonical["result"]["terminal"]["result_quote"] != authored.intent["proof_boundary"]
    if field in {"product_story", "opportunity", "product_view"}:
        assert candidate["result"]["facts"][field] is None
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    assert source_event_relations_from_intent(json.loads(json.dumps(intent)))[2]["visible_result_quote"] == canonical["result"]["terminal"]["result_quote"]
    _transaction_for_intent(intent, tmp_path)
    assert json.dumps(candidate, sort_keys=True) == before


@pytest.mark.parametrize("field", ["product_story", "opportunity", "product_view"])
def test_reserved_singleton_requires_explicit_null_and_rejects_competing_assumption(field):
    source, candidate, receipt = _carrier_case(field)
    competing = deepcopy(candidate)
    competing["result"]["facts"][field] = deepcopy(receipt["ledger"]["terminal"]["result_fact"]["source_ref"])
    with pytest.raises(ValueError, match="explicitly abstain"):
        admit_greenfield_host_candidate(competing, evidence_text=source, source_duty_receipt=receipt)
    del competing["result"]["facts"][field]
    with pytest.raises(ValueError):
        admit_greenfield_host_candidate(competing, evidence_text=source, source_duty_receipt=receipt)
    if field != "product_story":
        candidate["result"]["assumptions"].append({"applies_to": field, "statement": "Proposed competing field meaning."})
        with pytest.raises((ValueError, GreenfieldModelAuthoringError), match="assumption|source fact"):
            admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)


def test_unreserved_product_story_cannot_borrow_reserved_slot_nullability():
    source, candidate, receipt = _carrier_case("first_path")
    candidate["result"]["facts"]["product_story"] = None
    with pytest.raises(ValueError, match="unreserved"):
        admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)


@pytest.mark.parametrize("field", ["source_precedence", "terminal", "proof_boundary", "event_orders"])
def test_candidate_cannot_reauthor_source_plan_fields(field):
    source, candidate, receipt = _carrier_case("first_path")
    if field == "proof_boundary":
        candidate["result"]["facts"][field] = deepcopy(receipt["ledger"]["terminal"][field])
    elif field == "event_orders":
        candidate["result"]["provisional_design"]["first_run"][field] = [1, 2, 3]
    else:
        candidate["result"][field] = [] if field == "source_precedence" else {"event_order": 3}
    with pytest.raises(ValueError):
        admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)


def system_result_case(*, source=None):
    """Explicit fixture: human opening plus two separate discrete system duties."""
    source = source or _source()
    response = _response(source)
    response["result"]["terminal"].update(result_fact={"field": "success_metrics", "row": 1},
        result_quote="placement", result_occurrence=1)
    candidate = host_candidate_response(response, evidence_text=source,
        first_path_event_orders=(1,), source_run_event_orders=(1, 2, 3))
    return source, candidate, synthetic_source_duty_receipt(candidate, evidence_text=source)


def seven_action_system_result_case():
    """Synthetic source plan matching the diagnosed role/path topology, not live output."""
    from tests.unit.runtime.greenfield_model_authoring_fixtures import authored_response
    actions = [
        ("registrar", "starts", "a dossier"),
        ("registrar", "records", "the loan revision"),
        ("registrar", "associates", "the versioned object list"),
        ("conservator", "records", "the condition disposition"),
        ("packing technician", "records", "the crate manifest and seals"),
        ("coordinator", "checks", "the exact reviewed evidence"),
        ("coordinator", "records", "the manual handoff reference"),
        ("conservator", "replaces", "hold with ready"),
        ("Loan workspace", "retains", "version history at every change"),
        ("Loan workspace", "initializes", "a draft dossier"),
        ("Loan workspace", "enforces", "packing readiness at each packing attempt"),
        ("Loan workspace", "enforces", "review readiness at each review attempt"),
        ("Loan workspace", "releases", "the dossier"),
        ("Loan workspace", "presents", "the released dossier on every read"),
    ]
    constraints = [
        "After review checks, the coordinator records the manual handoff reference.",
        "Recording the reference moves the dossier to released.",
        "The final release write atomically rechecks the exact reviewed revisions and readiness together; changed evidence refuses release.",
    ]
    intent = {
        "title": "Loan workspace", "product_story": "Museum registrars need reviewable dossier release.",
        "state_object": "dossier", "first_path": ". ".join(" ".join(row) for row in actions),
        "proof_boundary": "Verify one complete dossier can be released and read back.",
        "problem": "Reviewed evidence can drift before release.", "customer": "Museum registrars",
        "opportunity": "Prove one release from exact reviewed evidence.",
        "product_view": "The workspace keeps revision review and release visible together.",
        "success_metrics": ["One complete dossier reaches released and remains readable."],
        "evidence_requirements": ["Retain the reviewed revisions and handoff reference."],
        "operational_constraints": constraints, "component_responsibilities": [],
        "human_actors": ["registrar", "conservator", "packing technician", "coordinator"],
        "internal_systems": ["Loan workspace"], "external_systems": [],
        "assumptions": [], "ambiguities": [], "non_goals": ["Do not grant carrier authority."],
    }
    state = "Dossier status records readiness."
    transition = "After a hold is replaced, dossier status becomes ready."
    boundary = "Carrier authority stays outside this workflow."
    # All source values are declared here; no arbitrary source parsing is involved.
    fragments = ["dossier", *intent["human_actors"], intent["title"]]
    fragments += [value for key, value in intent.items() if isinstance(value, str) and key not in {"state_object", "title"}]
    fragments += [value for key in ("success_metrics", "evidence_requirements", "operational_constraints", "non_goals") for value in intent[key]]
    prompt = ". ".join(fragments) + ". " + " ".join((state, transition, boundary))
    source = prepare_model_authoring_evidence(prompt=prompt).evidence_source
    relations = [{"actor_kind": "human" if index <= 8 else "product",
                  "actor_fact_quote": actor if index <= 8 else "Loan workspace",
                  **({"owner_system_quote": "Loan workspace"} if index > 8 else {}),
                  "event_quote": f"{actor} {action} {target}", "action_verb_quote": action,
                  "target_quote": target, "visible_result_quote": "released" if index == 13 else ""}
                 for index, (actor, action, target) in enumerate(actions, 1)]
    response = authored_response(intent, evidence_text=source, first_path_relations=relations,
        source_precedence=[{"before_event": before, "after_event": after, "constraint_index": constraint}
                           for before, after, constraint in ((6, 7, 1), (7, 13, 2), (6, 13, 3))])
    response["result"]["terminal"].update(result_fact={"field": "success_metrics", "row": 1})
    candidate = host_candidate_response(response, evidence_text=source,
        first_path_event_orders=tuple(range(1, 8)), source_run_event_orders=(*range(1, 8), 13))
    ledger = deepcopy(synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"])
    for index, duty in enumerate(ledger["system_duties"], 9):
        duty.update(performer_role="product_wide", execution_kind=("discrete_action" if index in (10, 13) else "recurring_invariant"))
    cite = lambda text: {"quote": text, "context": text}
    ledger["state_fields"] = [{"id": "status", "source_refs": [cite(state)], "state_object": "dossier", "field": "status", "meaning": "readiness"}]
    ledger["off_path_transitions"] = [{"id": "hold-ready", "source_refs": [cite(transition)], "trigger": "hold replacement", "governed_object": "dossier",
        "effects": [{"field": "status", "change": "ready", "observable_check": "status is ready"}]}]
    ledger["conditional_guards"] = [{"id": "atomic-release", "source_refs": [cite(constraints[2])], "trigger": "final release write", "protected_action": "release", "rule": constraints[2]}]
    ledger["boundaries"] = [{"id": "outside-authority", "source_refs": [cite(boundary)], "kind": "authority", "rule": boundary}]
    ledger["proof_duties"] = [{"id": "released-proof", "source_refs": [cite(intent["proof_boundary"])], "dossier_or_artifact": "complete dossier", "must_show": "released and readable"}]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    binding = candidate["result"]["source_duty_binding"]
    binding.update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    owner = {"component_key": "test-boundary-1", "workstream_key": "test-work-1"}
    for section in ("conditional_guards", "boundaries", "proof_duties"):
        binding[section] = [{"duty_id": row["id"], **owner} for row in ledger[section]]
    binding["off_path_transitions"] = [{"duty_id": "hold-ready", **owner, "effects": [{"effect_index": 1, "state_field_id": "status"}]}]
    return prompt, source, candidate, receipt


def test_seven_declared_human_actions_keep_separate_required_atomic_system_release(tmp_path):
    prompt, source, candidate, receipt = seven_action_system_result_case()
    ledger = receipt["ledger"]
    assert len(ledger["first_path_actions"]) == 7
    assert all(row["performer_role"] == "human_actor" for row in ledger["first_path_actions"])
    assert len(ledger["supporting_human_actions"]) == 1 and len(ledger["system_duties"]) == 6
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path, host_candidate=candidate,
        source_duty_receipt=receipt, prepared_evidence=prepare_model_authoring_evidence(prompt=prompt))
    assert [row["order"] for row in authored_first_run_relations(intent)] == [1, 2, 3, 4, 5, 6, 7, 13]
    assert intent["authored_semantics"]["source_event_relations"][12]["actor_kind"] == "product_wide"
    assert "releases the dossier" not in intent["first_path"]
    assert authored_checkpoint_text(intent) == "released"
    transaction = _transaction_for_intent(intent, tmp_path)
    context = next(row for row in transaction.proposal["diagrams"]
                   if row["authored_atlas_view_authority"]["node_order"][-1] == "product_actions")
    actions = next(row for row in context["diagram_boxes"] if row["node_id"] == "product_actions")
    assert actions["details"] == [{"label": "Performer", "text": "Loan workspace"},
                                  {"label": "Performer kind", "text": "product_wide"}]
    assert context["components"] == []
    assert transaction.proposal["intent"]["authored_semantics"]["source_duty"]["lifecycle"]["conditional_guards"][0]["rule"] == ledger["conditional_guards"][0]["rule"]
    import os
    from pathlib import Path
    if directory := os.environ.get("ODYLITH_MENTION_TEST_EVIDENCE_DIR"):
        from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
        destination = Path(directory) / "complete-run"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "seven-actions.json").write_text(json.dumps({
            "kind": "synthetic fixture; exact source/plan/compiler/serialized transaction; no model or live qualification",
            "prompt": prompt, "source": source, "candidate": candidate, "receipt": receipt,
            "wire": source_duty_authoring_fixture(ledger, evidence_text=source),
            "canonical_candidate": canonical_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt),
            "transaction": product_create_transaction_to_dict(transaction),
        }, ensure_ascii=False, sort_keys=True, indent=2))


def test_distinct_whole_product_mentions_keep_separate_atlas_groups_and_exact_readback(tmp_path):
    prompt, _, candidate, receipt = seven_action_system_result_case()
    prompt += " It releases the dossier."
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    ledger = deepcopy(receipt["ledger"])
    release = ledger["system_duties"][4]
    mention = {"quote": "It", "context": "It releases the dossier."}
    event = {"quote": "It releases the dossier", "context": "It releases the dossier."}
    release.update(actor_ref=mention, event_ref=event, role_refs=[event], statement="It releases the dossier")
    ledger["first_run"]["duty_ids"].insert(0, ledger["system_duties"][1]["id"])
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prepared.evidence_source)
    candidate["result"]["source_duty_binding"].update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    assert [(row["actor_fact_quote"], row["actor_kind"]) for row in authored_first_run_relations(intent)
            if row["actor_kind"] == "product_wide"] == [("Loan workspace", "product_wide"), ("It", "product_wide")]
    transaction = _transaction_for_intent(intent, tmp_path)
    context = transaction.proposal["diagrams"][0]
    groups = [row for row in context["diagram_boxes"] if row["node_id"].startswith("product_actions")]
    assert [row["node_id"] for row in groups] == ["product_actions", "product_actions2"]
    assert [row["details"] for row in groups] == [
        [{"label": "Performer", "text": quote}, {"label": "Performer kind", "text": "product_wide"}]
        for quote in ("Loan workspace", "It")]
    assert context["components"] == []


def test_required_system_result_survives_declared_path_run_proposal_and_dashboard_guards(tmp_path):
    from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import semantic_model_shape_issues
    from odylith.runtime.project_intelligence.greenfield_authored_dashboard import build_authored_greenfield_payload
    prompt = _source()
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source, candidate, receipt = system_result_case(source=prepared.evidence_source)
    assert len(receipt["ledger"]["first_path_actions"]) == 1
    assert len(receipt["ledger"]["system_duties"]) == 2
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    assert [row["order"] for row in authored_first_run_relations(intent)] == [1, 2, 3]
    assert authored_checkpoint_text(intent) == "placement"
    assert "berth occupancy" not in intent["first_path"]
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)
    assert semantic_model_shape_issues(proposal["semantic_model"], intent=intent) == []
    assert [row["source_event_order"] for row in proposal["semantic_model"]["first_path_contract"]["events"]] == [1]
    assert proposal["semantic_model"]["diagram_event_graph"]["events"][-1]["visible_result"] is True
    dashboard = build_authored_greenfield_payload(proposal=proposal, repo_root=tmp_path)
    assert dashboard["authored_facts"]["visible_result"] == "placement"


@pytest.mark.parametrize("decision", ["no", "uncertain", "missing"])
def test_plan_judgment_failure_stops_source_receipt_before_candidate(decision):
    source, _, receipt = system_result_case()
    decisions = deepcopy(receipt["decision_set"])
    if decision == "missing":
        del decisions["source_plan"]["first_run"]["completeness"]
    else:
        decisions["source_plan"]["first_run"]["completeness"] = decision
    with pytest.raises(ValueError, match="source plan"):
        validate_greenfield_source_duty_ledger(receipt["ledger"], evidence_text=source, decision_set=decisions)


@pytest.mark.parametrize("mutation", ["missing_result", "wrong_producer", "unknown", "repeat", "recurring", "cycle", "missing_prerequisite"])
def test_incoherent_source_plan_fails_structural_preflight(mutation):
    source, _, receipt = system_result_case()
    ledger = deepcopy(receipt["ledger"])
    ids = ledger["first_run"]["duty_ids"]
    if mutation == "missing_result":
        ids.pop()
    elif mutation == "wrong_producer":
        ledger["terminal"]["duty_id"] = "unknown"
    elif mutation == "unknown":
        ids.append("unknown")
    elif mutation == "repeat":
        ids.append(ids[0])
    elif mutation == "recurring":
        ledger["system_duties"][-1]["execution_kind"] = "recurring_invariant"
    else:
        cite = deepcopy(ledger["terminal"]["proof_boundary"])
        ledger["source_precedence"] = [{"before_duty_id": ids[1], "after_duty_id": ids[2], "constraint_ref": cite}]
        if mutation == "cycle":
            ledger["source_precedence"].append({"before_duty_id": ids[2], "after_duty_id": ids[1], "constraint_ref": cite})
        else:
            ids.remove(ids[1])
    with pytest.raises(ValueError):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)


def test_result_can_precede_required_later_work_without_sink_or_last_id_choice():
    source, _, receipt = system_result_case()
    ledger = deepcopy(receipt["ledger"])
    ledger["terminal"]["duty_id"] = ledger["system_duties"][0]["id"]
    result = project_source_run_plan(ledger, evidence_text=source)
    assert result["terminal"]["event_order"] == 2
    assert result["event_orders"] == [1, 2, 3]


@pytest.mark.parametrize("mutation", ["orders", "edge", "result", "proof", "metric"])
def test_passive_readback_refuses_changed_compiler_plan(mutation, tmp_path):
    prompt = _source()
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source, candidate, receipt = system_result_case(source=prepared.evidence_source)
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    semantic = intent["authored_semantics"]
    if mutation == "orders":
        semantic["provisional_design"]["first_run"]["event_orders"].reverse()
    elif mutation == "edge":
        semantic["source_precedence"] = [{"before_event": 1, "after_event": 2, "constraint_index": 1}]
    elif mutation == "result":
        semantic["source_event_relations"][2]["visible_result_quote"] = ""
        semantic["source_event_relations"][1]["visible_result_quote"] = "placement"
    elif mutation == "proof":
        intent["proof_boundary"] = intent["product_story"]
    else:
        intent["success_metrics"][0] = intent["product_story"]
    with pytest.raises(ValueError):
        source_event_relations_from_intent(intent)


@pytest.mark.parametrize("authoring,source_version", [(1, 9), (2, 10), (3, 11)])
def test_each_historical_inline_version_decodes_exact_ledger_without_invented_plan(authoring, source_version):
    from tests.unit.runtime.test_greenfield_source_lifecycle import _case
    source, receipt, _, _ = _case("dossier", source_version=f"odylith.greenfield.source-duty-ledger.v{source_version}")
    ledger = deepcopy(receipt["ledger"])
    if authoring == 1:
        # source9 predates the supplemental roster; the historical fixture's
        # empty transport annotation is removed before constructing its wire.
        ledger.pop("nonperforming_participants", None)
    wire = {"version": f"odylith.greenfield.source-duty-authoring.v{authoring}",
            "result": {key: value for key, value in ledger.items() if key != "version"}}
    assert decode_source_duty_inventory(json.loads(json.dumps(wire)), evidence_text=source) == ledger
    assert not {"source_precedence", "first_run", "terminal"} & set(ledger)


@pytest.mark.parametrize("edit", [False, True], ids=["synthetic22", "synthetic23"])
def test_source62_fixture_receipts_keep_the_exact_frozen_preedit_hashes(edit):
    if edit:
        from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case, _admit
        case = _edit_case(source_version="odylith.greenfield.source-duty-ledger.v11")
        source, receipt = case[0], _admit(case)
        expected = ("7be9577c2630440ed4f3fcfd82c44145b6171b03c450e776c2533126fefc50b1",
                    "8b431ffe2e7b3a74d17e2e626dbbdfedafefe439bf6e135f3ff8f06d7d2f0567",
                    "ed19c0ffb35632073c97ea11d56da420008efe6f1e6054bc3e3498b15aa71092")
    else:
        from tests.unit.runtime.test_greenfield_source_lifecycle import _case
        source, receipt, _, _ = _case("dossier", source_version="odylith.greenfield.source-duty-ledger.v11")
        expected = ("a737ea04d5fe1f29cf11de763dea1f2e3aae5626e0be51ad17d3b64151c8302c",
                    "fdd47d0caa5786b7067530fd4611d1b6a10dbd3ec007d8ac43a10e88da440d8b",
                    "42d09ccbe839f4710f2353b13b08b3e9e9fe34a89f4ff9fdebd88444cec5bd9e")
    assert tuple(receipt[key] for key in ("ledger_sha256", "verifier_task_sha256", "decision_set_sha256")) == expected
    assert receipt["version"].endswith(".v23" if edit else ".v22")
    assert verify_greenfield_source_duty_ledger_receipt(json.loads(json.dumps(receipt)), evidence_text=source) == receipt
    with pytest.raises(ValueError, match="receipt version"):
        admit_greenfield_host_candidate({}, evidence_text=source, source_duty_receipt=receipt)
