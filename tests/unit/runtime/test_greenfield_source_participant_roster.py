"""Source-owned optional participant custody across the existing four host stages."""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator, ValidationError
import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    greenfield_host_candidate_authoring_request, greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import (
    canonical_greenfield_host_candidate, greenfield_host_candidate_schema,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_authoring import (
    SOURCE_DUTY_AUTHORING_VERSION, decode_source_duty_inventory,
    greenfield_source_duty_authoring_schema,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    project_greenfield_source_event_catalog, source_owned_greenfield_actor_facts,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    preflight_greenfield_source_duty_ledger, validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import (
    PARTICIPANT_FIELDS, PARTICIPANT_JUDGMENTS, compact_source_duty_view,
)
from tests.unit.runtime.test_greenfield_source_duty_ledger import (
    EVIDENCE, _citation, _ledger, _material_duty_case, _yes_decisions,
)


def _participant(quote, context=None, ordinal=1):
    return {**_citation(quote, context), "mention_ordinal": ordinal}


def roster_case():
    source, ledger = _material_duty_case()
    source += (
        " Named nonperformers: observer Zoë is an optional beneficiary. "
        "Internal Archive is an optional internal catalog. External Archive is an optional carrier; Archive remains outside the workspace. "
        "The carrier and catalog are outside optional context, not workspace actions or authorities."
    )
    ledger["nonperforming_participants"] = {
        "human_actors": [_participant("Zoë")],
        "internal_systems": [_participant("Archive", "Internal Archive is an optional internal catalog.")],
        "external_systems": [_participant("Archive", "External Archive is an optional carrier; Archive remains outside the workspace.", 2)],
    }
    return source, ledger


def receipt_for(source, ledger):
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    return validate_greenfield_source_duty_ledger(ledger, evidence_text=source,
        decision_set=_yes_decisions(preflight, evidence_text=source))


def projected(source, receipt):
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    return catalog, source_owned_greenfield_actor_facts(catalog, supplemental={},
        evidence_text=source, ledger_receipt=receipt)


def test_inline_roster_is_required_closed_and_uses_exact_ledger_citation_schema():
    source, ledger = roster_case()
    wire = {"version": SOURCE_DUTY_AUTHORING_VERSION,
            "result": {k: v for k, v in ledger.items() if k != "version"}}
    schema = greenfield_source_duty_authoring_schema()
    Draft202012Validator(schema).validate(wire)
    assert decode_source_duty_inventory(json.loads(json.dumps(wire)), evidence_text=source) == ledger
    roster = schema["properties"]["result"]["anyOf"][0]["properties"]["nonperforming_participants"]
    assert roster["required"] == list(PARTICIPANT_FIELDS)
    assert roster["properties"]["human_actors"]["items"]["properties"]["quote"] == schema["properties"]["result"]["anyOf"][0]["properties"]["first_path_actions"]["items"]["properties"]["actor_ref"]["properties"]["quote"]
    for field in PARTICIPANT_FIELDS:
        damaged = deepcopy(wire)
        del damaged["result"]["nonperforming_participants"][field]
        with pytest.raises((ValueError, ValidationError)):
            decode_source_duty_inventory(damaged, evidence_text=source)


def test_exact_utf8_roster_order_and_equal_labels_keep_distinct_typed_addresses():
    source, ledger = roster_case()
    receipt = receipt_for(source, ledger)
    assert verify_greenfield_source_duty_ledger_receipt(json.loads(json.dumps(receipt)), evidence_text=source) == receipt
    catalog, facts = projected(source, receipt)
    for field in PARTICIPANT_FIELDS:
        assert facts[field] == [*catalog["facts"][field], *ledger["nonperforming_participants"][field]]
    assert len(catalog["events"]) == 3
    assert all(actor["quote"] not in {"Zoë", "Archive"} for actor in catalog["performers"])
    from odylith.runtime.domain_intelligence.greenfield_model_source_citations import canonical_citation_from_host_selection, resolve_source_citation
    addresses = []
    for field in ("internal_systems", "external_systems"):
        quote, start = resolve_source_citation(source.encode(), canonical_citation_from_host_selection(source.encode(), facts[field][-1], mention_selection=True))
        assert quote == "Archive" and source.encode()[start:start + len(quote.encode())] == quote.encode()
        addresses.append(start)
    assert addresses[0] != addresses[1]
    compact = compact_source_duty_view(ledger)
    assert compact["version"].endswith(".v9")
    assert decode_source_duty_inventory(compact, evidence_text=source) == ledger
    assert len(compact["result"]["citations"]) == len({(r["q"], r["c"], r.get("mention_ordinal")) for r in compact["result"]["citations"]})


@pytest.mark.parametrize("field", PARTICIPANT_FIELDS)
def test_candidate_participant_fields_are_absent_and_rejected(field):
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt
    source, candidate = _candidate()
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    schema = greenfield_host_candidate_schema()
    assert not set(PARTICIPANT_FIELDS) & set(schema["properties"]["result"]["anyOf"][0]["properties"]["facts"]["properties"])
    Draft202012Validator(schema).validate(candidate)
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    assert set(PARTICIPANT_FIELDS) <= set(canonical["result"]["facts"])
    candidate["result"]["facts"][field] = []
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(candidate)
    with pytest.raises(ValueError, match="source-owned"):
        canonical_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)


@pytest.mark.parametrize("judgment", PARTICIPANT_JUDGMENTS)
@pytest.mark.parametrize("verdict", ["no", "uncertain", None])
def test_every_roster_semantic_obligation_is_closed_and_required(judgment, verdict):
    source, ledger = roster_case()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source)
    assert set(task["participant_claims"]) == {f"/{field}/0" for field in PARTICIPANT_FIELDS}
    decisions = _yes_decisions(preflight, evidence_text=source)
    row = decisions["participant_decisions"]["/external_systems/0"]
    if verdict is None:
        del row[judgment]
    else:
        row[judgment] = verdict
    with pytest.raises(ValueError, match="participant decision"):
        validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_version", "omit_source_participant"])
def test_roster_table_and_source_completeness_refuse_closed_protocol_drift(mutation):
    source, ledger = roster_case()
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    decisions = _yes_decisions(preflight, evidence_text=source)
    if mutation == "missing":
        decisions["participant_decisions"].pop("/human_actors/0")
    elif mutation == "extra":
        decisions["participant_decisions"]["A1"] = decisions["participant_decisions"]["/human_actors/0"]
    elif mutation == "wrong_version":
        decisions["version"] = "odylith.greenfield.source-duty-decisions.v11"
    else:
        decisions["source_completeness"] = {"verdict": "no", "omissions": [{
            "omission_id": "optional-carrier", "typed_role": "external_systems",
            "source_ref": ledger["nonperforming_participants"]["external_systems"][0]}]}
    with pytest.raises(ValueError):
        validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions)


@pytest.mark.parametrize("damage", ["reference_only", "duplicate", "cross_type", "performer", "ambiguous", "invented"])
def test_source_preflight_refuses_invalid_nonperformer_custody(damage):
    source, ledger = roster_case()
    roster = ledger["nonperforming_participants"]
    if damage == "reference_only":
        roster["human_actors"] = [_participant("Reference notes", "Reference notes govern the template")]
    elif damage == "duplicate":
        roster["external_systems"] *= 2
    elif damage == "cross_type":
        roster["human_actors"] = deepcopy(roster["external_systems"])
    elif damage == "performer":
        roster["human_actors"] = [{**deepcopy(ledger["first_path_actions"][0]["actor_ref"]), "mention_ordinal": 1}]
    else:
        roster["external_systems"] = [_participant("Archive" if damage == "ambiguous" else "invented")]
    with pytest.raises(ValueError):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)


def test_complete_roster_data_and_order_are_bound_to_both_receipt_and_task():
    source, ledger = roster_case()
    source += " Optional observer Ada is also a beneficiary."
    ledger["nonperforming_participants"]["human_actors"].append(_participant("Ada"))
    receipt = receipt_for(source, ledger)
    changed = deepcopy(ledger)
    changed["nonperforming_participants"]["human_actors"].reverse()
    next_receipt = receipt_for(source, changed)
    assert next_receipt["ledger_sha256"] != receipt["ledger_sha256"]
    assert next_receipt["verifier_task_sha256"] != receipt["verifier_task_sha256"]
    receipt["ledger"] = changed
    with pytest.raises(ValueError):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source)


def test_combined_32_field_bound_refuses_before_candidate_dispatch():
    source, ledger = roster_case()
    refs = []
    for index in range(32):
        name = f"Catalog{index:02d}"
        source += f" {name} is optional internal context."
        refs.append(_participant(name))
    ledger["nonperforming_participants"]["internal_systems"] = refs
    receipt = receipt_for(source, ledger)
    action = ledger["first_path_actions"][0]
    admission = {"mode": "authority_admitted", "gate": {
        "decision": "admit", "required_fields": [], "owner_quote": action["actor_ref"]["quote"],
        "task_quote": action["action"], "result_quote": action["target"], "question": ""}}
    with pytest.raises(ValueError, match="existing bound"):
        greenfield_host_candidate_authoring_request(greenfield_host_candidate_contract(source),
            source_duty_receipt=receipt, authority_admission=admission)
    ledger["nonperforming_participants"]["internal_systems"].pop()
    receipt = receipt_for(source, ledger)
    request = greenfield_host_candidate_authoring_request(greenfield_host_candidate_contract(source),
        source_duty_receipt=receipt, authority_admission=admission)
    assert len(request["source_owned_participant_facts"]["internal_systems"]) == 32
    ledger["nonperforming_participants"]["internal_systems"] = refs + [_participant("Zoë")]
    with pytest.raises(ValueError):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)


def test_ledger9_receipt18_keeps_exact_task_and_no_injected_roster():
    ledger = _ledger()
    ledger.pop("nonperforming_participants")
    ledger["version"] = "odylith.greenfield.source-duty-ledger.v9"
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE,
        _passive_source_version=ledger["version"])
    receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=EVIDENCE,
        decision_set=_yes_decisions(preflight), _passive_source_version=ledger["version"])
    assert receipt["version"].endswith(".v18")
    assert receipt["verifier_task_sha256"] == "f83c0c842074a57c6ae939796d5252d37bfc8ada14cb8bf6c3561605fcb3071d"
    assert receipt["ledger_sha256"] == "5f014d3553b61d5aa795ab4f4e8d4be93ef867412905435f4689c889c98cb52d"
    assert receipt["decision_set_sha256"] == "0cbeae8849a96f15fb734c677a03b949e8e56da7ce6c967afa59372067c36255"
    assert verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=EVIDENCE) == receipt
    assert "nonperforming_participants" not in receipt["ledger"]
    assert compact_source_duty_view(ledger)["version"].endswith(".v7")
    with pytest.raises(ValueError, match="receipt version"):
        greenfield_host_candidate_authoring_request(greenfield_host_candidate_contract(EVIDENCE),
            source_duty_receipt=receipt, authority_admission={})


@pytest.mark.parametrize("mutation", [None, "remove", "add", "retype", "reorder", "alternate_occurrence", "ordinal_only"])
def test_edit_keeps_verified_optional_system_values_order_and_exact_mapped_addresses(mutation):
    from tests.unit.runtime.test_greenfield_source_lifecycle import _case
    from tests.unit.runtime.greenfield_model_authoring_fixtures import (
        edit_action_context_fixture, preserved_edit_decisions_fixture,
        synthetic_source_duty_receipt_for_ledger, structural_design_fixture,
    )
    from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import project_greenfield_source_lifecycle
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import mapped_prior_source_span, UNSUPPORTED_SYSTEM_MUTATION
    prompt, prior, candidate, binding = _case("dossier")
    ledger = deepcopy(prior["ledger"])
    prompt += " Internal Archive is an optional catalog. External Archive is an optional carrier; Archive stays outside. Relay is optional outside context. A separate reference also names Archive."
    ledger["nonperforming_participants"] = {"human_actors": [],
        "internal_systems": [_participant("Archive", "Internal Archive is an optional catalog.")],
        "external_systems": [_participant("Archive", "External Archive is an optional carrier; Archive stays outside."), _participant("Relay")]}
    prior = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prompt)
    binding.update(source_sha256=prior["source_sha256"], ledger_sha256=prior["ledger_sha256"])
    lifecycle = project_greenfield_source_lifecycle(ledger_receipt=prior, binding=binding, candidate_result=candidate, evidence_text=prompt)
    candidate["provisional_design"] = structural_design_fixture([1, 2])
    correction = "Retain every accepted system, its type, order and exact source identity. Added Hub remains optional context."
    context = edit_action_context_fixture(prior_source=prompt, prior_receipt=prior, prior_lifecycle=lifecycle,
        design=candidate["provisional_design"], correction=correction)
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction).evidence_source
    roster = ledger["nonperforming_participants"]
    if mutation == "remove":
        roster["external_systems"].pop()
    elif mutation == "add":
        roster["external_systems"].append(_participant("Hub"))
    elif mutation == "retype":
        roster["internal_systems"].append(roster["external_systems"].pop())
    elif mutation == "reorder":
        roster["external_systems"].reverse()
    elif mutation == "ordinal_only":
        roster["external_systems"][0]["mention_ordinal"] = 2
    elif mutation == "alternate_occurrence":
        roster["external_systems"][0] = _participant("Archive", "A separate reference also names Archive.")
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=task["decision_set_schema"]["properties"]["version"]["enum"][0],
        verifier_task_sha256=task["verifier_task_sha256"],
        identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"},
        **preserved_edit_decisions_fixture(context))
    receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions, edit_preservation=context)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    if mutation is not None:
        with pytest.raises(ValueError, match=UNSUPPORTED_SYSTEM_MUTATION):
            source_owned_greenfield_actor_facts(catalog, supplemental={}, evidence_text=source, ledger_receipt=receipt)
    else:
        _, facts = projected(source, receipt)
        for field in ("internal_systems", "external_systems"):
            primary = [(int(link["path"].rsplit("/", 1)[1]), atom)
                       for atom in context["prior_system_facts"][field] for link in atom["projection_links"]
                       if link["field"] == field and link["relation_order"] == 0]
            for index, atom in sorted(primary):
                assert facts[field][index]["quote"] == atom["normalized_value"]
                start, end = mapped_prior_source_span(context, atom["source_span_refs"][0], evidence_text=source)
                assert source.encode()[start:end].decode() == facts[field][index]["quote"]


def test_roster_addition_cannot_exceed_the_existing_256_compact_citation_bound():
    source, ledger = EVIDENCE, _ledger()
    initial = len(compact_source_duty_view(ledger)["result"]["citations"])
    needed = 256 - initial
    for index in range((needed + 3) // 4):
        refs = []
        for item in range(min(4, needed - index * 4)):
            quote = f"Proof token {index:02d}-{item} is visible."
            source += " " + quote
            refs.append(_citation(quote))
        section = "boundaries" if index < 32 else "proof_duties"
        row = {"id": f"bounded-{index}", "source_refs": refs}
        row.update({"kind": "scope", "rule": "Retain the source proof."} if section == "boundaries"
                   else {"dossier_or_artifact": "proof", "must_show": "source proof"})
        ledger[section].append(row)
    assert len(compact_source_duty_view(ledger)["result"]["citations"]) == 256
    preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    source += " Optional observer Zoë is a named beneficiary."
    ledger["nonperforming_participants"]["human_actors"] = [_participant("Zoë")]
    with pytest.raises(ValueError, match="citation bank exceeds"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)


@pytest.mark.parametrize("mutation", [None, "value", "order", "missing", "address", "type"])
def test_canonical_admission_retains_complete_roster_and_refuses_later_fact_mutation(mutation):
    from tests.unit.runtime.test_greenfield_host_candidate import _candidate
    from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt
    from odylith.runtime.domain_intelligence.greenfield_host_candidate import admit_greenfield_host_candidate
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import validate_greenfield_source_duty_binding
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import validate_greenfield_authoring_response, GreenfieldModelAuthoringError
    from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
    source, candidate = _candidate()
    source += " Zoë is an optional beneficiary. The Archive is an optional catalog outside this workspace. Relay is an optional carrier. A reference also names Archive."
    candidate.nonperforming_participants = {"human_actors": [_participant("Zoë")],
        "internal_systems": [], "external_systems": [_participant("Archive", "The Archive is an optional catalog outside this workspace."), _participant("Relay")]}
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=source)
    candidate["result"]["source_duty_binding"].update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    binding = validate_greenfield_source_duty_binding(candidate["result"]["source_duty_binding"],
        ledger_receipt=receipt, candidate_result=candidate["result"], evidence_text=source)
    if mutation is None:
        authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
        assert authored.intent["external_systems"] == ["Archive", "Relay"]
        assert authored.intent["human_actors"][-1] == "Zoë"
        assert all(event["actor_fact_path"] not in {"/external_systems/0", "/external_systems/1", "/human_actors/1"} for event in authored.source_event_relations)
        assert {row["projection_path"] for row in authored.atomic_claims if row["field"] == "external_systems"} >= {"/external_systems/0", "/external_systems/1"}
        return
    facts = canonical["result"]["facts"]
    if mutation == "value":
        facts["external_systems"][0] = deepcopy(facts["external_systems"][1])
    elif mutation == "order":
        facts["external_systems"].reverse()
    elif mutation == "missing":
        facts.pop("external_systems")
    elif mutation == "address":
        facts["external_systems"][0]["occurrence"] = 2
    else:
        facts["internal_systems"].append(facts["external_systems"].pop())
    with pytest.raises(GreenfieldModelAuthoringError, match="participants differ"):
        validate_greenfield_authoring_response(canonical, evidence_text=source, elapsed_seconds=0,
            provider={}, profile_id=STANDARD_PROFILE_ID, effective_timeout_seconds=300,
            semantic_model_call_count=0, allow_zero_semantic_calls=True,
            accepted_source_duties=receipt,
            accepted_source_duty_binding=binding)


@pytest.mark.parametrize("ordinal", [None, 0, -1, True, False, 1.0, "1", 2401, 2])
def test_native_material_schema_and_custom_integer_checker_require_exact_ordinal(ordinal):
    source, ledger = roster_case()
    row = ledger["nonperforming_participants"]["human_actors"][0]
    if ordinal is None:
        row.pop("mention_ordinal")
    else:
        row["mention_ordinal"] = ordinal
    wire = {"version": SOURCE_DUTY_AUTHORING_VERSION, "result": {k: v for k, v in ledger.items() if k != "version"}}
    if ordinal != 2 and type(ordinal) is not float:
        with pytest.raises(ValidationError):
            Draft202012Validator(greenfield_source_duty_authoring_schema()).validate(wire)
    with pytest.raises(ValueError):
        decode_source_duty_inventory(wire, evidence_text=source)
    with pytest.raises(ValueError):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)


def test_same_pair_distinct_ordinals_remain_independent_through_hashes_compact_and_projection():
    source, ledger = roster_case()
    context = "Internal Relay and external Relay are distinct optional systems."
    source += " " + context
    ledger["nonperforming_participants"]["internal_systems"] = [_participant("Relay", context, 1)]
    ledger["nonperforming_participants"]["external_systems"] = [_participant("Relay", context, 2)]
    receipt = receipt_for(source, ledger)
    compact = compact_source_duty_view(ledger)
    rows = [row for row in compact["result"]["citations"] if row["q"] == "Relay"]
    assert [row["mention_ordinal"] for row in rows] == [1, 2]
    assert len({row["id"] for row in rows}) == 2
    assert decode_source_duty_inventory(compact, evidence_text=source) == ledger
    _, facts = projected(source, receipt)
    from odylith.runtime.domain_intelligence.greenfield_model_source_citations import canonical_citation_from_host_selection, resolve_source_citation
    starts = [resolve_source_citation(source.encode(), canonical_citation_from_host_selection(source.encode(), facts[field][-1], mention_selection=True))[1]
              for field in ("internal_systems", "external_systems")]
    assert starts[0] != starts[1]
    changed = deepcopy(ledger)
    changed["nonperforming_participants"]["internal_systems"][0]["mention_ordinal"] = 2
    changed["nonperforming_participants"]["external_systems"] = []
    original = deepcopy(ledger)
    original["nonperforming_participants"]["external_systems"] = []
    first, second = receipt_for(source, original), receipt_for(source, changed)
    assert first["ledger_sha256"] != second["ledger_sha256"]
    assert first["verifier_task_sha256"] != second["verifier_task_sha256"]
    first["ledger"] = changed
    with pytest.raises(ValueError):
        verify_greenfield_source_duty_ledger_receipt(first, evidence_text=source)


@pytest.mark.parametrize("edit", [False, True])
def test_source10_fixture_receipts_keep_frozen_294_hashes_without_invented_ordinals(edit):
    if edit:
        from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case, _admit
        case = _edit_case(source_version="odylith.greenfield.source-duty-ledger.v10")
        source, receipt = case[0], _admit(case)
        expected = ("afc371ac3dc6c3cc7882745cfca17e9620ee2aa7999990e76e843e33ac94ac92",
                    "701ed21c655503cf606106e1117c2a794f2a65a4293caf1d606aa564af4e9859",
                    "56b6d960726d96836965670bdb4b05be2faaa482cd8b73923e04e75d910ac74c")
    else:
        source, ledger = EVIDENCE, _ledger()
        ledger["version"] = "odylith.greenfield.source-duty-ledger.v10"
        preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source, _passive_source_version=ledger["version"])
        receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=_yes_decisions(preflight), _passive_source_version=ledger["version"])
        expected = ("c6cc28d01e9f6d228200ae4ffd289504a204f87a5d45f627f4d5f8514d16f5a7",
                    "a3867c5da676c77f78e1357a0d22be2029f631c121632910b8ef0b5b9a77f113",
                    "f4f813d2d658adbef26e365ec732927e4851dfe9f5f12f3944feefc27174b018")
    assert tuple(receipt[k] for k in ("ledger_sha256", "verifier_task_sha256", "decision_set_sha256")) == expected
    assert receipt["version"].endswith(".v21" if edit else ".v20")
    assert "mention_ordinal" not in json.dumps(receipt)
    assert verify_greenfield_source_duty_ledger_receipt(json.loads(json.dumps(receipt)), evidence_text=source) == receipt
    with pytest.raises(ValueError, match="receipt version"):
        greenfield_host_candidate_authoring_request(greenfield_host_candidate_contract(source, edit_preservation=receipt.get("edit_preservation")), source_duty_receipt=receipt, authority_admission={})


def _nonempty_system_prior(repo_root):
    from tests.unit.runtime.test_greenfield_model_path_custody import _source, _response
    from tests.unit.runtime.greenfield_model_authoring_fixtures import host_candidate_response, synthetic_source_duty_receipt
    from tests.unit.runtime.test_greenfield_create_transaction import _package, _seal_test_package
    from tests.unit.runtime.greenfield_authored_proposal_fixtures import approved_authored_quality_manifest_fixture
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
    from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
    from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
    prompt = _source() + " Archive is optional internal context. Relay is an optional outside carrier; Relay performs no workspace action."
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    candidate = host_candidate_response(_response(prepared.evidence_source), evidence_text=prepared.evidence_source)
    candidate.nonperforming_participants["internal_systems"].append(_participant("Archive"))
    candidate.nonperforming_participants["external_systems"].append(_participant("Relay", "Relay is an optional outside carrier; Relay performs no workspace action."))
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=prepared.evidence_source)
    candidate["result"]["source_duty_binding"].update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=repo_root, host_candidate=candidate,
        source_duty_receipt=receipt, prepared_evidence=prepared)
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)
    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    package = _seal_test_package(_package(proposal, repo_root=repo_root), repo_root=repo_root)
    return build_product_create_transaction(proposal=proposal, release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []}, prewrite_package=package,
        backlog_result=package.backlog_result or {}, intent_authority=authority, repo_root=repo_root,
        quality_manifest=approved_authored_quality_manifest_fixture(intent_authority=authority, proposal=proposal))


@pytest.mark.parametrize("alternate", [False, True], ids=["preserved", "alternate-ordinal-refused"])
def test_native_edit_cli_preserves_nonempty_typed_roster_and_refuses_same_label_new_address(tmp_path, alternate):
    from contextlib import redirect_stdout
    from io import StringIO
    import os
    from pathlib import Path
    import subprocess
    import time
    from odylith.runtime.domain_intelligence import greenfield_host_flow as host, greenfield_proposals_cli as cli
    from odylith.runtime.domain_intelligence.greenfield_host_source_phase import run_source_duty_phase
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import WholeJourneyDeadline
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import validate_greenfield_source_duty_design_binding
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import UNSUPPORTED_SYSTEM_MUTATION
    from tests.unit.runtime.greenfield_model_authoring_fixtures import preserved_edit_decisions_fixture
    from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _stage_transaction_custody
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
    flow, _, _, _, proposals, _ = _flow(tmp_path, contract={"version": "unused"}, candidate={})
    prior = _nonempty_system_prior(flow.repo_root)
    prior_path, _ = _stage_transaction_custody(prior, repo_root=flow.repo_root, bounded=False)
    prompt = prior.proposal["intent"]["prompt"]
    correction = "Keep all accepted systems, types, values, order, source identities and action allocations."
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction).evidence_source
    context = cli._edit_preservation(prior, correction=correction, evidence_text=source)
    assert all(context["prior_system_facts"][field] for field in ("internal_systems", "external_systems"))
    ledger = deepcopy(prior.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"])
    selected = next(ref for ref in ledger["nonperforming_participants"]["external_systems"] if ref["quote"] == "Relay")
    if alternate:
        selected["mention_ordinal"] = 2
    wire = {"version": SOURCE_DUTY_AUTHORING_VERSION, "result": {k: v for k, v in ledger.items() if k != "version"}}
    raw = json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode()
    contract = greenfield_host_candidate_contract(source, edit_preservation=context)
    retained, installed_results, host_calls = {}, [], []
    workspace = tmp_path / "nonempty-edit-host"
    workspace.mkdir()
    def invoke_host(command, **kwargs):
        schema = json.loads(Path(command[command.index("--output-schema") + 1]).read_bytes())
        host_calls.append(Path(command[command.index("--output-schema") + 1]).name)
        if len(host_calls) == 1:
            Draft202012Validator(schema).validate(wire)
            return subprocess.CompletedProcess(command, 0, stdout=raw.decode(), stderr="")
        task = json.loads(kwargs["contract_text"])
        preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
        decisions = _yes_decisions(preflight, evidence_text=source)
        decisions.update(version=task["decision_set_schema"]["properties"]["version"]["enum"][0],
            verifier_task_sha256=task["verifier_task_sha256"],
            identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"},
            **preserved_edit_decisions_fixture(context))
        Draft202012Validator(schema).validate(decisions)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(decisions), stderr="")
    def installed(command, timeout):
        args = list(command[command.index("source-ledger-check"):])
        args[args.index("--repo-root") + 1] = str(flow.repo_root)
        output = StringIO()
        with redirect_stdout(output):
            code = cli.main(args)
        installed_results.append({"returncode": code, "payload": json.loads(output.getvalue())})
        return subprocess.CompletedProcess(command, code, stdout=output.getvalue(), stderr="")
    flow = host.HostCandidateFlow(**{**flow.__dict__, "prompt": prompt, "edit_evidence": correction,
        "transaction_hash": prior.transaction_hash, "completion_receipt": "", "invoke_installed": installed,
        "retain_source_ledger_bytes": lambda value: retained.update(raw=value)})
    import hashlib
    observation = {"source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "source_duty_verifier_host_invocations": 0, "candidate_host_invocations": 0, "proposal_command_invocations": 0}
    result = run_source_duty_phase(flow=flow, contract=contract, source=source, host_workspace=workspace,
        host_argv=flow.host_argv, deadline=WholeJourneyDeadline(time.monotonic(), time.monotonic),
        observation=observation, invoke_host=invoke_host, check_payload={"mode": "authority_admitted"})
    assert retained["raw"] == raw and [row["returncode"] for row in installed_results] == [0, 0]
    first = ledger["first_path_actions"][0]
    admission = {"mode": "authority_admitted", "gate": {"decision": "admit", "required_fields": [],
        "owner_quote": first["actor_ref"]["quote"], "task_quote": first["action"], "result_quote": first["target"], "question": ""}}
    request, error = None, ""
    if alternate:
        with pytest.raises(ValueError, match=UNSUPPORTED_SYSTEM_MUTATION) as refused:
            greenfield_host_candidate_authoring_request(contract, source_duty_receipt=result.receipt, authority_admission=admission)
        error = str(refused.value)
    else:
        request = greenfield_host_candidate_authoring_request(contract, source_duty_receipt=result.receipt, authority_admission=admission)
        for field in ("internal_systems", "external_systems"):
            assert [ref["quote"] for ref in request["source_owned_participant_facts"][field]] == prior.proposal["intent"][field]
        binding = deepcopy(prior.proposal["intent"]["authored_semantics"]["source_duty"]["binding"])
        binding.update(source_sha256=result.receipt["source_sha256"], ledger_sha256=result.receipt["ledger_sha256"])
        validate_greenfield_source_duty_design_binding(binding, ledger=ledger,
            provisional_design=prior.proposal["intent"]["authored_semantics"]["provisional_design"], ledger_receipt=result.receipt)
    assert len(host_calls) == 2 and observation["candidate_host_invocations"] == observation["proposal_command_invocations"] == 0 and proposals == []
    if directory := os.environ.get("ODYLITH_MENTION_TEST_EVIDENCE_DIR"):
        destination = Path(directory) / "nonempty-edit"
        destination.mkdir(parents=True, exist_ok=True)
        witness = {"kind": "synthetic compiler-sealed unbounded prior; mocked host; real CLI; no model or live EDIT",
            "alternate_ordinal": alternate, "prior_transaction": json.loads(prior_path.read_text()), "prior_source": prompt,
            "source": source, "context": context, "schema": contract["source_ledger"]["source_ledger_schema"],
            "wire": wire, "raw_response": raw.decode(), "installed_results": installed_results, "receipt": result.receipt,
            "candidate_request": request, "refusal": error, "observation": observation, "host_calls": host_calls}
        (destination / ("alternate-ordinal-refused.json" if alternate else "preserved.json")).write_text(json.dumps(witness, ensure_ascii=False, sort_keys=True, indent=2))
