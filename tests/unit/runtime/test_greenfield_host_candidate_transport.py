"""Lossless candidate-phase presentation with compiler-owned receipt custody."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
    greenfield_host_candidate_authoring_request,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
    expand_compact_source_duty_ledger,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    synthetic_source_duty_receipt_for_ledger,
)
from tests.unit.runtime.test_greenfield_source_duty_ledger import _material_duty_case


def _accepted_request():
    source, ledger = _material_duty_case()
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    contract = greenfield_host_candidate_contract(source)
    contract["authority_gate"] = {"task": "Completed authority producer task"}
    admission = {"mode": "authority_admitted", "gate": {
        "decision": "admit", "required_fields": [], "owner_quote": "reviewer",
        "task_quote": "defines scope and audience", "result_quote": "scope", "question": "",
    }}
    return source, contract, receipt, admission


def test_candidate_phase_preserves_every_material_row_and_control_losslessly() -> None:
    source, contract, receipt, admission = _accepted_request()
    before = deepcopy((contract, receipt, admission))
    request = greenfield_host_candidate_authoring_request(
        contract, source_duty_receipt=receipt, authority_admission=admission,
    )
    assert request["transport_version"] == HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION
    for key in ("version", "candidate_version", "canonical_version", "task",
                "requirements", "request", "candidate_schema"):
        assert request[key] == contract[key]
    assert request["authority_admission"] == admission
    assert expand_compact_source_duty_ledger(
        request["accepted_source_duty_inventory"], evidence_text=source,
    ) == receipt["ledger"]
    for section in ("first_path_actions", "supporting_human_actions", "system_duties",
                    "state_fields", "off_path_transitions", "conditional_guards",
                    "boundaries", "proof_duties", "evidence_controls"):
        assert receipt["ledger"][section], f"fixture must exercise {section}"
        assert len(request["accepted_source_duty_inventory"][section]) == len(receipt["ledger"][section])
    assert request["source_duty_custody"] == {
        key: value for key, value in receipt.items() if key not in {"ledger", "decision_set"}
    }
    assert not {"authority_gate", "source_ledger", "accepted_source_duty_receipt", "decision_set"} & request.keys()
    assert "actor_ref q/c" in request["citation_resolution"]
    assert "Do not reverify source duties" in request["citation_resolution"]
    assert (contract, receipt, admission) == before
    request["request"]["evidence"] = "changed after transport"
    request["accepted_source_duty_inventory"]["first_path_actions"][0]["statement"] = "changed"
    assert (contract, receipt, admission) == before


@pytest.mark.parametrize("tamper", [
    "source", "ledger", "controls", "decision", "source_sha256", "ledger_sha256",
    "verifier_task_sha256", "decision_set_sha256", "version", "authority_source",
    "authority_clarification", "authority_mode", "contract",
])
def test_candidate_transport_rejects_invalid_source_and_receipt_custody(tamper: str) -> None:
    _source, contract, receipt, admission = _accepted_request()
    if tamper == "source":
        contract["request"]["evidence"] += " Invented duty."
    elif tamper == "ledger":
        receipt["ledger"]["first_path_actions"][0]["target"] = "an invented target"
    elif tamper == "controls":
        receipt["ledger"]["evidence_controls"] = []
    elif tamper == "decision":
        next(iter(receipt["decision_set"]["decisions"].values()))["verdict"] = "no"
    elif tamper == "authority_source":
        admission["gate"]["owner_quote"] = "Invented operator"
    elif tamper == "authority_clarification":
        admission["gate"].update({"decision": "clarify", "required_fields": ["first_path"],
                                  "question": "Who acts?", "owner_quote": "", "task_quote": "", "result_quote": ""})
    elif tamper == "authority_mode":
        admission["mode"] = "clarification_required"
    elif tamper == "contract":
        contract.pop("candidate_schema")
    else:
        receipt[tamper] = "f" * 64
    with pytest.raises((ValueError, TypeError)):
        greenfield_host_candidate_authoring_request(
            contract, source_duty_receipt=receipt, authority_admission=admission,
        )
