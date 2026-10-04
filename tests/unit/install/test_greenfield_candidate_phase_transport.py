"""The installed driver dispatches only phase-specific candidate data."""

import hashlib
import json

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
)
import greenfield_matrix_host_candidate as host_module
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow


def test_four_phase_flow_keeps_complete_receipt_external_and_measures_request(tmp_path, monkeypatch):
    flow, host_run, _installed, host_calls, _proposals, _repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate={"result": {"status": "authored"}},
    )
    full_receipts = []
    original_propose = flow.invoke_propose

    def propose(candidate_path, gate_path, ledger_path, timeout):
        full_receipts.append(json.loads(ledger_path.read_text()))
        return original_propose(candidate_path, gate_path, ledger_path, timeout)

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "invoke_propose": propose})
    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    assert host_module.run_host_candidate_flow(flow).returncode == 0
    assert len(host_calls) == 4
    text = host_calls[3][1]
    phase = json.loads(text)
    assert not {"authority_gate", "source_ledger", "accepted_source_duty_receipt"} & phase.keys()
    assert phase["request"] == json.loads(host_calls[1][1])["request"]
    assert phase["source_duty_custody"] == {
        key: value for key, value in full_receipts[0].items() if key not in {"ledger", "decision_set"}
    }
    assert "decision_set" in full_receipts[0] and "ledger" in full_receipts[0]
    assert phase["transport_version"] == HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION
    assert flow.observation_sink["candidate_transport_version"] == HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION
    assert flow.observation_sink["candidate_request_bytes"] == len(text.encode("utf-8"))
    assert flow.observation_sink["candidate_request_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
