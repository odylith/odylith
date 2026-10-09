"""The installed driver dispatches only phase-specific candidate data."""

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
)
from odylith.runtime.domain_intelligence import greenfield_host_flow as host_module
from odylith.runtime.domain_intelligence.greenfield_authority_gate import greenfield_authority_gate_contract
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID, RESCUE_PROFILE_ID, get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    preflight_greenfield_source_duty_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import source_duty_entailment_task
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
from tests.unit.runtime.test_greenfield_host_candidate_transport import _accepted_request


@pytest.mark.parametrize("edit", [False, True])
@pytest.mark.parametrize("profile_id", [STANDARD_PROFILE_ID, RESCUE_PROFILE_ID])
@pytest.mark.parametrize("outcome", ["authored", "timeout", "invalid_json"])
def test_four_phase_flow_keeps_complete_receipt_external_and_measures_request(
    tmp_path, monkeypatch, edit, profile_id, outcome,
):
    flow, host_run, _installed, host_calls, _proposals, _repo = _flow(
        tmp_path, contract={}, candidate={"result": {"status": "authored"}},
    )
    source, contract, receipt, admission = _accepted_request(edit=edit)
    context = contract["source_ledger"].get("edit_preservation")
    correction = context["correction"] if edit else flow.edit_evidence
    contract["authority_gate"] = greenfield_authority_gate_contract(
        prompt=source, edit_evidence=correction, evidence_source=source,
    )
    contract_before = json.dumps(contract, sort_keys=True)
    preflight = preflight_greenfield_source_duty_ledger(receipt["ledger"], evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    compact_ledger = compact_source_duty_view(receipt["ledger"])
    profile = get_greenfield_model_profile(profile_id)
    argv = list(flow.host_argv)
    argv[argv.index("--model") + 1] = profile.model
    retained, delivered_schema, full_receipts = {}, [], []
    original_propose = flow.invoke_propose

    def installed(command, timeout):
        if "authority-check" in command:
            assert json.loads(Path(command[command.index("--gate-file") + 1]).read_text()) == admission["gate"]
            payload = admission
        elif "source-ledger-check" in command:
            assert json.loads(Path(command[command.index("--ledger-file") + 1]).read_text()) == compact_ledger
            if "--decision-file" in command:
                assert json.loads(Path(command[command.index("--decision-file") + 1]).read_text()) == receipt["decision_set"]
                payload = {"mode": "source_duty_admitted", "receipt": receipt}
            else:
                payload = {"mode": "source_duty_preflight", "preflight": preflight, "decision_task": task}
        else:
            assert "candidate-contract" in command
            payload = contract
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    def host(command, **kwargs):
        host_run(command, **kwargs)
        path = Path(command[command.index("--output-schema") + 1])
        payload = {"authority-gate-schema.json": admission["gate"],
                   "source-ledger-schema.json": compact_ledger,
                   "source-duty-decision-schema.json": receipt["decision_set"]}.get(path.name)
        if path.name == "candidate-schema.json":
            delivered_schema.append(path.read_bytes())
            if outcome == "timeout":
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            return subprocess.CompletedProcess(command, 0,
                stdout="not JSON" if outcome == "invalid_json" else '{"result":{"status":"authored"}}', stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    def propose(candidate_path, gate_path, ledger_path, timeout):
        full_receipts.append(json.loads(ledger_path.read_text()))
        return original_propose(candidate_path, gate_path, ledger_path, timeout)

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "prompt": source,
        "edit_evidence": correction, "transaction_hash": context["transaction_hash"] if edit else "",
        "host_argv": tuple(argv), "expected_model": profile.model,
        "env": {**flow.env, "ODYLITH_GREENFIELD_MODEL_PROFILE": profile_id},
        "invoke_installed": installed, "invoke_propose": propose,
        "retain_diagnostic_bytes": lambda name, value: retained.update({name: value})})
    monkeypatch.setattr(host_module, "_invoke_host", host)
    if outcome == "authored":
        assert host_module.run_host_candidate_flow(flow).returncode == 0
        assert full_receipts == [receipt]
    else:
        with pytest.raises(host_module.HostCandidateFlowError):
            host_module.run_host_candidate_flow(flow)
        assert full_receipts == _proposals == []
    assert len(host_calls) == 4
    text = host_calls[3][1]
    phase = json.loads(text)
    assert not {"authority_gate", "source_ledger", "accepted_source_duty_receipt", "candidate_schema"} & phase.keys()
    for key in ("version", "candidate_version", "canonical_version", "task", "requirements", "request"):
        assert phase[key] == contract[key]
    assert "supplied candidate response JSON Schema" in phase["task"]
    assert phase["request"] == json.loads(host_calls[1][1])["request"]
    assert phase["accepted_source_duty_inventory"] == compact_ledger
    assert phase["authority_admission"] == admission
    assert phase["source_duty_custody"] == {
        key: receipt[key] for key in ("version", "source_sha256", "ledger_sha256",
                                     "verifier_task_sha256", "decision_set_sha256")
    }
    schema_bytes = (json.dumps(contract["candidate_schema"], ensure_ascii=False,
        sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    assert delivered_schema == [schema_bytes] == [retained["candidate-schema.json"]]
    assert text.encode("utf-8") == retained["candidate.stdin.json"]
    assert flow.observation_sink["candidate_schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
    assert flow.observation_sink["host_request"]["model"] == profile.model
    assert flow.observation_sink["host_request"]["output_schema_present"] is True
    assert flow.observation_sink["candidate_host_invocations"] == 1
    assert flow.observation_sink["proposal_command_invocations"] == (outcome == "authored")
    assert flow.observation_sink["post_receipt_provider_invocations"] == 0
    assert json.dumps(contract, sort_keys=True) == contract_before
    assert phase["transport_version"] == HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION
    assert flow.observation_sink["candidate_transport_version"] == HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION
    assert flow.observation_sink["candidate_request_bytes"] == len(text.encode("utf-8"))
    assert flow.observation_sink["candidate_request_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
