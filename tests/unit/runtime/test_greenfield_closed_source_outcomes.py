"""Closed source outcomes and truthful human projections, without host inference."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator, ValidationError
import pytest

from odylith.runtime.domain_intelligence import greenfield_host_flow as host
from odylith.runtime.domain_intelligence.greenfield_authored_first_run import authored_first_path_text, authored_first_run_text
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_host_candidate import greenfield_host_candidate_contract
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence, render_product_intent_preview
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import SOURCE_DUTY_COMPACT_VERSION, expand_compact_source_duty_ledger, greenfield_compact_source_duty_ledger_schema
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import source_duty_entailment_task
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import GreenfieldSourceDutyLedgerError, preflight_greenfield_source_duty_ledger, validate_greenfield_source_duty_ledger
from odylith.runtime.domain_intelligence.proposal_memory import build_project_brief_source_markdown
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
from tests.unit.runtime.greenfield_model_authoring_fixtures import host_candidate_response, synthetic_source_duty_receipt
from tests.unit.runtime.test_greenfield_model_path_custody import _source, _response
from tests.unit.runtime.test_greenfield_source_duty_compact import _compact
from tests.unit.runtime.test_greenfield_source_duty_ledger import _ledger, _yes_decisions, EVIDENCE


def _clarification():
    return {"version": SOURCE_DUTY_COMPACT_VERSION,
            "result": {"status": "clarification_required", "question": "Which system owns the history safeguard?"}}


@pytest.mark.parametrize("field", ["product_identity", "citations", "evidence_controls", "first_path_actions", "system_duties"])
def test_actual_provider_schema_and_compiler_refuse_mixed_clarification(field):
    schema = greenfield_compact_source_duty_ledger_schema()
    Draft202012Validator.check_schema(schema)
    mixed = _clarification()
    mixed["result"][field] = _compact()["result"][field]
    before = deepcopy(mixed)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(mixed)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="closed result branch"):
        expand_compact_source_duty_ledger(mixed)
    assert mixed == before


def test_closed_inventory_and_question_are_disjoint_with_exact_passive_compact_readback():
    schema = greenfield_compact_source_duty_ledger_schema()
    for outcome in (_compact(), _clarification()):
        Draft202012Validator(schema).validate(outcome)
    clarification = expand_compact_source_duty_ledger(_clarification())
    assert clarification["product_identity"] is None
    assert not any(value for key, value in clarification.items()
                   if key not in {"version", "status", "question"})
    preflight = preflight_greenfield_source_duty_ledger(clarification, evidence_text=EVIDENCE)
    assert preflight["claims"] == []
    with pytest.raises(ValueError, match="clarification cannot request a verifier"):
        source_duty_entailment_task(preflight, evidence_text=EVIDENCE)
    for question in ("", " " * 2401):
        bad = _clarification()
        bad["result"]["question"] = question
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(bad)
    passive = {"version": "odylith.greenfield.source-duty-compact.v6", **_compact()["result"]}
    Draft202012Validator(greenfield_compact_source_duty_ledger_schema(_passive=True)).validate(passive)
    assert expand_compact_source_duty_ledger(passive, _passive=True)["version"].endswith(".v8")
    with pytest.raises(GreenfieldSourceDutyLedgerError):
        expand_compact_source_duty_ledger(passive)


def test_source_question_reaches_operator_without_verifier_candidate_or_repo_writes(tmp_path, monkeypatch):
    flow, original_host, original_installed, calls, proposals, repo = _flow(tmp_path, contract={}, candidate={})
    original_installed = flow.invoke_installed
    question = _clarification()

    def invoke_host(command, **kwargs):
        if Path(command[command.index("--output-schema") + 1]).name == "source-ledger-schema.json":
            calls.append((list(command), kwargs["contract_text"], kwargs["timeout"], kwargs["cwd"]))
            Draft202012Validator(json.loads(Path(command[command.index("--output-schema") + 1]).read_text())).validate(question)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(question), stderr="")
        return original_host(command, **kwargs)

    def installed(command, timeout):
        if "source-ledger-check" in command:
            assert "--decision-file" not in command
            raw = json.loads(Path(command[command.index("--ledger-file") + 1]).read_text())
            ledger = expand_compact_source_duty_ledger(raw, evidence_text=flow.prompt)
            preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=flow.prompt)
            assert preflight["claims"] == []
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"mode": "clarification_required", "clarification": {"question": ledger["question"]}}), stderr="")
        return original_installed(command, timeout)

    flow = host.HostCandidateFlow(**{**flow.__dict__, "invoke_installed": installed})
    monkeypatch.setattr(host, "_invoke_host", invoke_host)
    result = host.run_host_candidate_flow(flow)
    assert json.loads(result.stdout)["clarification"]["question"] == question["result"]["question"]
    assert len(calls) == 2  # Authority, then one inventory outcome.
    assert proposals == [] and list(repo.iterdir()) == []
    assert flow.observation_sink["source_duty_verifier_host_invocations"] == 0
    assert flow.observation_sink["candidate_host_invocations"] == 0
    assert flow.observation_sink["source_ledger_temp_cleaned"] is True


def test_passive_mixed_clarification_still_reaches_strict_preflight_refusal():
    passive = {"version": "odylith.greenfield.source-duty-compact.v6", **_compact()["result"]}
    passive.update(status="clarification_required", question="Which system acts?")
    for key, value in passive.items():
        if isinstance(value, list) and key != "citations":
            passive[key] = []
    schema = greenfield_compact_source_duty_ledger_schema(_passive=True)
    Draft202012Validator(schema).validate(passive)
    source = "First Complete Path: A reviewer defines scope. Status records approval. Reference notes."
    ledger = expand_compact_source_duty_ledger(passive, evidence_text=source, _passive=True)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="clarification must carry no inventory"):
        preflight_greenfield_source_duty_ledger(ledger, evidence_text=source,
            _passive_source_version="odylith.greenfield.source-duty-ledger.v8")


@pytest.mark.parametrize("role,verdict,expected", [
    ("product_wide", "yes", "/product_identity"),
    ("internal_system", "yes", "/internal_systems/0"),
    ("product_wide", "uncertain", None),
    ("product_wide", "no", None),
])
def test_whole_product_and_subsystem_references_keep_typed_identity_and_uncertainty_refuses(role, verdict, expected):
    scope = ("Before any status change, the system preserves the review history."
             if role == "product_wide" else
             "The portal is also called the system. The system preserves the review history.")
    source = EVIDENCE + " " + scope
    ledger = _ledger()
    duty = ledger["system_duties"][0]
    actor = "the system" if role == "product_wide" else "portal"
    duty.update(performer_role=role, execution_kind="recurring_invariant", source_refs=[],
                statement=f"{actor} preserves the review history", action="preserves", target="the review history",
                event_ref={"quote": scope, "context": scope}, actor_ref={"quote": actor, "context": scope},
                role_refs=[{"quote": scope, "context": scope}])
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source)
    authoring = greenfield_host_candidate_contract(source)
    roles = authoring["source_ledger"]["source_ledger_schema"]["properties"]["result"]["anyOf"][0]["properties"]["system_duties"]["items"]["properties"]["performer_role"]["enum"]
    assert roles == ["internal_system", "external_system", "product_wide"]
    assert ", ".join(roles) in authoring["source_ledger"]["task"]
    assert "Named subsystems alone do not make a cross-cutting product safeguard ambiguous" in authoring["source_ledger"]["task"]
    assert "Explicit subsystem aliases retain that subsystem performer" in task["task"]
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions["decisions"]["S1"]["verdict"] = verdict
    if expected is None:
        with pytest.raises(ValueError, match="entail|affirm|yes|uncertain"):
            validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions)
    else:
        receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions)
        catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
        assert catalog["events"][-1]["actor_fact_path"] == expected
        assert receipt["ledger"]["product_identity"] == ledger["product_identity"]


def test_declared_path_and_execution_closure_have_separate_narrative_and_exact_evidence(tmp_path):
    source = _source()
    prepared = prepare_model_authoring_evidence(prompt=source)
    response = _response(prepared.evidence_source)
    response["result"]["facts"]["operational_constraints"].append({
        "quote": "the product records berth occupancy before the berth map shows the placement", "occurrence": 1})
    response["result"]["source_precedence"] = [{"before_event": 2, "after_event": 3, "constraint_index": 2}]
    response["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3]
    candidate = host_candidate_response(response, evidence_text=prepared.evidence_source)
    receipt = synthetic_source_duty_receipt(candidate, evidence_text=prepared.evidence_source)
    candidate["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3, 2]
    summary = "Berth map helps dock attendants record vessel placement and see current occupancy."
    candidate["result"]["provisional_design"]["project_summary"] = summary
    intent = materialize_host_authored_intent(prompt=source, repo_root=tmp_path, host_candidate=candidate,
        source_duty_receipt=receipt, prepared_evidence=prepared)
    before = deepcopy(intent)
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)
    path, walk = authored_first_path_text(intent), authored_first_run_text(intent)
    assert path == intent["first_path"] and "records berth occupancy" not in path
    assert "records berth occupancy" in walk and not any(label in walk for label in ("Event ", "Actor:", "Source event:"))
    assert path in render_product_intent_preview(intent)
    brief = proposal["project_brief"]
    sections = {row["section"]: row["must_capture"] for row in brief["blueprint_sections"]}
    assert sections["First path"] == path
    assert sections["Proposed walkthrough"].startswith(walk)
    assert sections["Accepted evidence excerpt"] == intent["product_story"]
    assert proposal["intent"]["summary"] == brief["summary"] == summary
    text = build_project_brief_source_markdown(proposal=proposal, backlog_items=[], component_items=[],
        diagram_ids=[], release_selector="0.0.1", release_id="", accepted_at="exact-acceptance-time")
    default = text.split("<details>", 1)[0]
    assert text.count(summary) == 1
    assert f"### First path\n\n{path}" in default
    assert "### Proposed walkthrough" in default
    assert not any(label in default for label in ("Accepted evidence excerpt", "- schema:", "Event ", "Actor:", "Source event:", "Why:"))
    assert "<summary>Evidence and assumptions</summary>" in text and "## Project Design Board" in text
    assert "<summary>Record metadata</summary>" in text and "- accepted_at: exact-acceptance-time" in text
    context, sequence = proposal["diagrams"][:2]
    assert "first-path interaction" not in context["mermaid_source"] and "product interaction" in context["mermaid_source"]
    assert "First-path actions" not in json.dumps(context["diagram_boxes"])
    assert sequence["slug"].endswith("-first-run")
    assert "Source action 3" in sequence["mermaid_source"]
    assert proposal["semantic_model"]["provisional_design"]["first_run"]["event_orders"] == [1, 3, 2]
    assert [row["source_event_order"] for row in proposal["semantic_model"]["first_path_contract"]["events"]] == [1, 2]
    assert intent == before and intent["authored_semantics"]["source_duty"]["ledger_receipt"] == receipt
