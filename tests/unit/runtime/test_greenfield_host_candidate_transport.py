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


def _accepted_request(*, edit=False):
    source, ledger = _material_duty_case()
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    context = None
    if edit:
        from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case, _admit

        case = _edit_case(correction="Show the approval status. Keep all earlier safeguards. ∆\r\nPreserve the record.")
        source, ledger, context, _, _ = case
        receipt = _admit(case)
    contract = greenfield_host_candidate_contract(source, edit_preservation=context)
    contract["authority_gate"] = {"task": "Completed authority producer task"}
    action = ledger["first_path_actions"][0]
    admission = {"mode": "authority_admitted", "gate": {
        "decision": "admit", "required_fields": [], "owner_quote": action["actor_ref"]["quote"],
        "task_quote": action["action"], "result_quote": action["target"], "question": "",
    }}
    return source, contract, receipt, admission


@pytest.mark.parametrize("edit", [False, True])
def test_candidate_phase_preserves_every_material_row_and_control_losslessly(edit) -> None:
    source, contract, receipt, admission = _accepted_request(edit=edit)
    before = deepcopy((contract, receipt, admission))
    request = greenfield_host_candidate_authoring_request(
        contract, source_duty_receipt=receipt, authority_admission=admission,
    )
    assert request["transport_version"] == HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION
    assert HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION == "odylith.greenfield.host-candidate-authoring-transport.v3"
    for key in ("version", "candidate_version", "canonical_version", "task",
                "requirements", "request"):
        assert request[key] == contract[key]
    assert "candidate_schema" not in request
    assert contract["candidate_schema"]["properties"]["result"]["anyOf"][0]["required"]
    assert "supplied candidate response JSON Schema" in request["task"]
    assert request["authority_admission"] == admission
    assert expand_compact_source_duty_ledger(
        request["accepted_source_duty_inventory"], evidence_text=source,
    ) == receipt["ledger"]
    for section in ("first_path_actions", "supporting_human_actions", "system_duties",
                    "state_fields", "off_path_transitions", "conditional_guards",
                    "boundaries", "proof_duties", "evidence_controls"):
        if not edit:
            assert receipt["ledger"][section], f"fixture must exercise {section}"
        assert len(request["accepted_source_duty_inventory"][section]) == len(receipt["ledger"][section])
    assert request["source_duty_custody"] == {
        key: receipt[key] for key in ("version", "source_sha256", "ledger_sha256",
                                     "verifier_task_sha256", "decision_set_sha256")
    }
    assert not {"authority_gate", "source_ledger", "accepted_source_duty_receipt", "decision_set"} & request.keys()
    assert "source_event_catalog freezes every performer" in request["citation_resolution"]
    assert len(request["source_event_catalog"]["events"]) == sum(len(receipt["ledger"][section])
        for section in ("first_path_actions", "supporting_human_actions", "system_duties"))
    assert "Do not reverify source duties" in request["citation_resolution"]
    assert (contract, receipt, admission) == before
    request["request"]["evidence"] = "changed after transport"
    request["accepted_source_duty_inventory"]["first_path_actions"][0]["statement"] = "changed"
    assert (contract, receipt, admission) == before


@pytest.mark.parametrize("tamper", [
    "source", "ledger", "controls", "decision", "source_sha256", "ledger_sha256",
    "verifier_task_sha256", "decision_set_sha256", "version", "authority_source",
    "authority_clarification", "authority_mode", "contract", "schema_shape",
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
    elif tamper == "schema_shape":
        contract["candidate_schema"] = None
    else:
        receipt[tamper] = "f" * 64
    with pytest.raises((ValueError, TypeError)):
        greenfield_host_candidate_authoring_request(
            contract, source_duty_receipt=receipt, authority_admission=admission,
        )


@pytest.mark.parametrize("edit", [False, True])
@pytest.mark.parametrize("failure", ["timeout", "invalid_shape"])
def test_inventory_stdin_omits_only_schema_with_initial_and_edit_custody(
    tmp_path, edit, failure,
) -> None:
    import hashlib
    import json
    from pathlib import Path
    import subprocess
    import time

    from odylith.runtime.domain_intelligence import greenfield_host_flow as host
    from odylith.runtime.domain_intelligence.greenfield_host_source_phase import run_source_duty_phase
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import greenfield_edit_preservation_view
    from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
    from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import WholeJourneyDeadline
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
    from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case

    source, ledger = _material_duty_case()
    context = None
    if edit:
        source, ledger, context, _, _ = _edit_case(
            correction="Show the approval status. Keep all earlier safeguards. ∆\r\nPreserve the record.",
        )
    contract = greenfield_host_candidate_contract(source, edit_preservation=context)
    before = deepcopy(contract)
    _, _, _, admission = _accepted_request()
    flow, _, _, _, proposals, _ = _flow(tmp_path, contract={"version": "unused"}, candidate={})
    retained, calls, installed = {}, [], []
    workspace = tmp_path / "inventory-workspace"
    workspace.mkdir()
    schema_bytes = (json.dumps(contract["source_ledger"]["source_ledger_schema"],
        ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

    def invoke_host(command, **kwargs):
        calls.append((command, kwargs))
        assert command == tuple(argument.replace("{candidate_schema}",
            str(workspace / "source-ledger-schema.json")) for argument in flow.host_argv)
        assert Path(command[command.index("--output-schema") + 1]).read_bytes() == schema_bytes
        assert 0 < kwargs["timeout"] <= 300
        malformed = {**compact_source_duty_view(ledger), "unknown_field": "refuse"}
        return subprocess.CompletedProcess(command, 124 if failure == "timeout" else 0,
            stdout="" if failure == "timeout" else json.dumps(malformed), stderr="")

    def invoke_installed(command, timeout):
        installed.append(command)
        assert "source-ledger-check" in command and "--decision-file" not in command
        raw = json.loads(Path(command[command.index("--ledger-file") + 1]).read_bytes())
        with pytest.raises(ValueError, match="object fields are invalid"):
            expand_compact_source_duty_ledger(raw, evidence_text=source)
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="invalid ledger shape")

    flow = host.HostCandidateFlow(**{**flow.__dict__, "prompt": source,
        "transaction_hash": context["transaction_hash"] if context is not None else "",
        "invoke_installed": invoke_installed,
        "retain_diagnostic_bytes": lambda name, value: retained.update({name: value})})
    observation = {"source_duty_verifier_host_invocations": 0,
        "candidate_host_invocations": 0, "proposal_command_invocations": 0}
    with pytest.raises(host.HostCandidateFlowError, match=("command returned nonzero"
            if failure == "timeout" else "preflight returned nonzero")):
        run_source_duty_phase(flow=flow, contract=contract, source=source,
            host_workspace=workspace, host_argv=flow.host_argv,
            deadline=WholeJourneyDeadline(time.monotonic(), time.monotonic),
            observation=observation, invoke_host=invoke_host, check_payload=admission)
    assert len(calls) == 1 and len(installed) == (failure == "invalid_shape")
    assert proposals == []
    assert all(observation[key] == 0 for key in (
        "source_duty_verifier_host_invocations", "candidate_host_invocations", "proposal_command_invocations"))
    old = {"source_ledger": {**contract["source_ledger"], **({
        "edit_preservation": greenfield_edit_preservation_view(context),
    } if context is not None else {})}, "request": contract["request"], "authority_admission": admission}
    old_bytes = json.dumps(old, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert old["source_ledger"].pop("source_ledger_schema") == json.loads(schema_bytes)
    expected = json.dumps(old, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual = calls[0][1]["contract_text"].encode("utf-8")
    assert actual == expected == retained["source-ledger.stdin.json"]
    assert len(old_bytes) - len(actual) == 5838
    assert retained["source-ledger-schema.json"] == schema_bytes
    assert observation["source_ledger_schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
    assert observation["source_ledger_request"]["output_schema_present"] is True
    assert (observation["source_ledger_request"]["model"],
        observation["source_ledger_request"]["reasoning_effort"]) == ("gpt-6-astra", "medium")
    assert contract == before


@pytest.mark.parametrize("tamper", ["missing_schema", "mismatched_schema"])
def test_inventory_schema_qualification_still_refuses_before_dispatch(tmp_path, tamper) -> None:
    import time

    from odylith.runtime.domain_intelligence.greenfield_host_source_phase import run_source_duty_phase
    from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import WholeJourneyDeadline
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow

    source, contract, _, admission = _accepted_request()
    flow, invoke_host, installed, calls, proposals, _ = _flow(
        tmp_path, contract={"version": "unused"}, candidate={},
    )
    argv = list(flow.host_argv)
    schema_index = argv.index("--output-schema")
    if tamper == "missing_schema":
        del argv[schema_index:schema_index + 2]
    else:
        argv[schema_index + 1] = str(tmp_path / "wrong-schema.json")
    workspace = tmp_path / "inventory-workspace"
    workspace.mkdir()
    with pytest.raises(ValueError, match="canonical release argv contract"):
        run_source_duty_phase(flow=flow, contract=contract, source=source,
            host_workspace=workspace, host_argv=argv,
            deadline=WholeJourneyDeadline(time.monotonic(), time.monotonic),
            observation={}, invoke_host=invoke_host, check_payload=admission)
    assert installed == calls == proposals == []
