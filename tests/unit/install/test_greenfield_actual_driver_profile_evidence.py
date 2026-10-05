"""Actual driver observations must cross the retained release-profile boundary."""

from copy import deepcopy
import json
import subprocess

import pytest

from odylith.runtime.domain_intelligence import greenfield_host_flow as host_module
from greenfield_model_profiles import model_profile_environment, model_profile_evidence
from odylith.runtime.domain_intelligence.greenfield_authority_gate import (
    greenfield_authority_gate_contract, validate_greenfield_authority_gate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate, greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import source_duty_entailment_task
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    host_candidate_response, synthetic_source_duty_receipt,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _driver_evidence(tmp_path, monkeypatch, *, outcome="authored"):
    source = _source()
    raw = host_candidate_response(_response(source), evidence_text=source)
    source_receipt = synthetic_source_duty_receipt(raw, evidence_text=source)
    ledger = deepcopy(source_receipt["ledger"])
    if outcome == "inventory_clarification":
        for key, value in ledger.items():
            if isinstance(value, list):
                ledger[key] = []
        ledger.update(status="clarification_required", question="Who owns the first task?")
    compact = compact_source_duty_view(ledger)
    contract = greenfield_host_candidate_contract(source)
    contract["authority_gate"] = greenfield_authority_gate_contract(
        prompt=source, edit_evidence="", evidence_source=source,
    )
    gate = {"decision": "admit", "required_fields": [], "owner_quote": "Dock attendant Ivo",
            "task_quote": "enters a vessel tag", "result_quote": "berth map shows the placement", "question": ""}
    if outcome == "gate_clarification":
        gate.update(decision="clarify", required_fields=["first_path"], owner_quote="",
                    task_quote="", result_quote="", question="Who owns the first task?")
    flow, _host, _installed, _hosts, _proposals, _repo = _flow(
        tmp_path, contract={"version": "fixture"}, candidate={},
    )
    env = model_profile_environment(STANDARD_PROFILE_ID, flow.env)
    sealed = {}
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source) if outcome == "authored" else None

    def completed(command, payload):
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    def installed(command, _timeout):
        if "candidate-contract" in command:
            return completed(command, contract)
        if "authority-check" in command:
            checked = validate_greenfield_authority_gate(gate, evidence_source=source)
            return completed(command, {"mode": "clarification_required"} if checked["decision"] == "clarify"
                             else {"mode": "authority_admitted", "gate": checked})
        if outcome == "inventory_clarification":
            return completed(command, {"mode": "clarification_required", "clarification": {"question": ledger["question"]}})
        if "--decision-file" not in command:
            return completed(command, {"mode": "source_duty_preflight", "preflight": preflight, "decision_task": task})
        return completed(command, {"mode": "source_duty_admitted", "receipt": source_receipt})

    def host(command, **kwargs):
        name = command[command.index("--output-schema") + 1].split("/")[-1]
        payload = {"authority-gate-schema.json": gate, "source-ledger-schema.json": compact,
                   "source-duty-decision-schema.json": source_receipt["decision_set"], "candidate-schema.json": raw}[name]
        return completed(command, payload)

    def propose(candidate_path, _gate_path, ledger_path, _timeout):
        candidate = json.loads(candidate_path.read_text())
        retained_receipt = json.loads(ledger_path.read_text())
        _authored, receipt = admit_greenfield_host_candidate(
            candidate, evidence_text=source, source_duty_receipt=retained_receipt,
        )
        sealed.update(origin="host_native", host_candidate=receipt, runtime_semantic_model_call_count=0)
        return completed([], {"mode": "product_create_transaction"})

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "prompt": source, "edit_evidence": "", "env": env, "timeout": 315.0,
        "invoke_installed": installed, "invoke_propose": propose,
    })
    monkeypatch.setattr(host_module, "_invoke_host", host)
    assert host_module.run_host_candidate_flow(flow).returncode == 0

    def evaluate(stage=None):
        return model_profile_evidence(
            STANDARD_PROFILE_ID, env, observed=sealed,
            stage_observation=flow.observation_sink if stage is None else stage,
            raw_candidate=raw if outcome == "authored" else {},
            source_duty_receipt=source_receipt if outcome == "authored" else {}, expected_source=source,
        )

    return flow.observation_sink, evaluate


def test_actual_authored_driver_observation_passes_profile_evidence(tmp_path, monkeypatch):
    stage, evaluate = _driver_evidence(tmp_path, monkeypatch)
    evidence = evaluate()
    assert evidence["status"] == "passed", evidence["issues"]
    assert evidence["stage_observation"] == stage
    assert stage["version"].endswith(".v17")
    assert stage["model_window_seconds"] == 300.0
    assert stage["operational_timeout_seconds"] == 315.0
    assert stage["candidate_completion_reserve_seconds"] == 15.0
    assert evidence["stage_observation_summary"]["candidate_request"] == {
        key: stage[key] for key in ("candidate_request_bytes", "candidate_request_sha256", "candidate_transport_version")
    }


@pytest.mark.parametrize("outcome", ["gate_clarification", "inventory_clarification"])
def test_actual_clarification_has_no_candidate_transport_proof(tmp_path, monkeypatch, outcome):
    stage, evaluate = _driver_evidence(tmp_path, monkeypatch, outcome=outcome)
    assert not {"candidate_request_bytes", "candidate_request_sha256", "candidate_transport_version"} & stage.keys()
    evidence = evaluate()
    assert evidence["status"] == "passed", evidence["issues"]
    assert evidence["stage_observation_summary"]["candidate_request"] == {}
    assert stage["candidate_completion_reserve_seconds"] == 15.0
    changed = {**stage, "candidate_completion_reserve_seconds": 0}
    assert evaluate(changed)["status"] == "failed"


@pytest.mark.parametrize("field,value", [
    ("candidate_request_bytes", 0), ("candidate_request_bytes", -1),
    ("candidate_request_bytes", 1.5), ("candidate_request_bytes", True),
    ("candidate_request_bytes", "2000"), ("candidate_request_sha256", "not-a-hash"),
    ("candidate_transport_version", "other-transport"),
    ("candidate_completion_reserve_seconds", 0),
    ("candidate_completion_reserve_seconds", 16),
    ("candidate_completion_reserve_seconds", "15"),
])
def test_actual_authored_observation_rejects_tampered_transport_fields(tmp_path, monkeypatch, field, value):
    stage, evaluate = _driver_evidence(tmp_path, monkeypatch)
    changed = deepcopy(stage)
    changed[field] = value
    assert evaluate(changed)["status"] == "failed"


@pytest.mark.parametrize("field", ["candidate_request_bytes", "candidate_request_sha256", "candidate_transport_version", "candidate_completion_reserve_seconds"])
def test_actual_authored_observation_requires_transport_fields(tmp_path, monkeypatch, field):
    stage, evaluate = _driver_evidence(tmp_path, monkeypatch)
    changed = deepcopy(stage)
    changed.pop(field)
    assert evaluate(changed)["status"] == "failed"
