"""Lossless candidate-phase presentation with compiler-owned receipt custody."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION,
    greenfield_host_candidate_authoring_request,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_authoring import (
    decode_source_duty_inventory,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    synthetic_source_duty_receipt_for_ledger,
)
from tests.unit.runtime.test_greenfield_source_duty_ledger import _material_duty_case
from tests.unit.runtime.test_greenfield_source_duty_compact import _inline


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
    assert HOST_CANDIDATE_AUTHORING_TRANSPORT_VERSION == "odylith.greenfield.host-candidate-authoring-transport.v7"
    for key in ("version", "candidate_version", "canonical_version", "task",
                "requirements", "request"):
        assert request[key] == contract[key]
    assert "candidate_schema" not in request
    assert contract["candidate_schema"]["properties"]["result"]["anyOf"][0]["required"]
    assert "supplied candidate response JSON Schema" in request["task"]
    assert request["authority_admission"] == admission
    assert decode_source_duty_inventory(
        request["accepted_source_duty_inventory"], evidence_text=source,
    ) == receipt["ledger"]
    for section in ("first_path_actions", "supporting_human_actions", "system_duties",
                    "state_fields", "off_path_transitions", "conditional_guards",
                    "boundaries", "proof_duties", "evidence_controls"):
        if not edit:
            assert receipt["ledger"][section], f"fixture must exercise {section}"
        assert len(request["accepted_source_duty_inventory"]["result"][section]) == len(receipt["ledger"][section])
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
    request["accepted_source_duty_inventory"]["result"]["first_path_actions"][0]["statement"] = "changed"
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
@pytest.mark.parametrize("failure", ["timeout", "invalid_shape", "historical_version"])
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
        malformed = (compact_source_duty_view(ledger) if failure == "historical_version"
                     else {**_inline(ledger), "unknown_field": "refuse"})
        return subprocess.CompletedProcess(command, 124 if failure == "timeout" else 0,
            stdout="" if failure == "timeout" else json.dumps(malformed), stderr="")

    def invoke_installed(command, timeout):
        installed.append(command)
        pytest.fail("invalid native authoring output must stop before installed preflight")

    flow = host.HostCandidateFlow(**{**flow.__dict__, "prompt": source,
        "transaction_hash": context["transaction_hash"] if context is not None else "",
        "invoke_installed": invoke_installed,
        "retain_diagnostic_bytes": lambda name, value: retained.update({name: value})})
    observation = {"source_duty_verifier_host_invocations": 0,
        "candidate_host_invocations": 0, "proposal_command_invocations": 0}
    with pytest.raises(host.HostCandidateFlowError, match=("command returned nonzero"
            if failure == "timeout" else "advertised authoring schema")):
        run_source_duty_phase(flow=flow, contract=contract, source=source,
            host_workspace=workspace, host_argv=flow.host_argv,
            deadline=WholeJourneyDeadline(time.monotonic(), time.monotonic),
            observation=observation, invoke_host=invoke_host, check_payload=admission)
    assert len(calls) == 1 and installed == []
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
    assert len(old_bytes) - len(actual) == len(schema_bytes.rstrip(b"\n")) + len(b'"source_ledger_schema":,')
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


@pytest.mark.parametrize("outcome", ["inventory", "clarification", "invalid_citation", "roster", "roster_no", "roster_uncertain", "roster_missing", "old_inline", "old_roster", "plan", "plan_no", "plan_uncertain", "plan_missing", "context", "context_no", "context_uncertain", "context_missing", "old_plan"])
def test_native_inline_response_is_retained_then_checked_by_installed_cli(tmp_path, outcome) -> None:
    from contextlib import redirect_stdout
    import hashlib
    from io import StringIO
    import json
    from pathlib import Path
    import subprocess
    import time

    from jsonschema import Draft202012Validator
    from odylith.runtime.domain_intelligence import greenfield_host_flow as host
    from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    from odylith.runtime.domain_intelligence.greenfield_host_source_phase import run_source_duty_phase
    from odylith.runtime.domain_intelligence.greenfield_source_duty_authoring import SOURCE_DUTY_AUTHORING_VERSION
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
    from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import WholeJourneyDeadline
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
    from tests.unit.runtime.test_greenfield_source_duty_compact import _complete_inline_case
    from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions

    prompt, ledger = _complete_inline_case()
    if outcome.startswith("roster"):
        from tests.unit.runtime.test_greenfield_source_participant_roster import roster_case
        prompt, ledger = roster_case()
    if outcome.startswith("plan"):
        from tests.unit.runtime.test_greenfield_source_run_plan import seven_action_system_result_case
        prompt, _, _, receipt = seven_action_system_result_case()
        ledger = receipt["ledger"]
    if outcome.startswith("context"):
        from tests.unit.runtime.test_greenfield_source_context_authority import context_case
        prompt, _, _, receipt = context_case()
        ledger = receipt["ledger"]
    inventory_outcome = outcome == "inventory" or outcome.startswith(("roster", "plan", "context"))
    source = prepare_model_authoring_evidence(prompt=prompt, source_language="en").evidence_source
    expected_preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    expected_compact = compact_source_duty_view(ledger)
    wire = _inline(ledger)
    if outcome == "clarification":
        wire = {"version": SOURCE_DUTY_AUTHORING_VERSION, "result": {
            "status": "clarification_required", "question": "Which action completes the first path?"}}
    elif outcome == "invalid_citation":
        wire["result"]["state_fields"][0]["source_refs"][0]["quote"] = "invented source"
    elif outcome == "old_roster":
        wire["version"] = "odylith.greenfield.source-duty-authoring.v2"
        for rows in wire["result"]["nonperforming_participants"].values():
            for ref in rows:
                ref.pop("mention_ordinal")
    elif outcome == "old_plan":
        wire["version"] = "odylith.greenfield.source-duty-authoring.v4"
    elif outcome == "old_inline":
        wire["version"] = "odylith.greenfield.source-duty-authoring.v1"
        wire["result"].pop("nonperforming_participants")
    raw = (json.dumps(wire, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    contract = greenfield_host_candidate_contract(source)
    flow, _, _, _, proposals, _ = _flow(tmp_path, contract={"version": "unused"}, candidate={})
    retained, host_calls, installed_calls, installed_results = {}, [], [], []
    workspace = tmp_path / "inline-workspace"
    workspace.mkdir()

    def invoke_host(command, **kwargs):
        schema_path = Path(command[command.index("--output-schema") + 1])
        schema = json.loads(schema_path.read_bytes())
        host_calls.append(schema_path.name)
        if schema_path.name == "source-ledger-schema.json":
            assert schema == contract["source_ledger"]["source_ledger_schema"]
            assert schema["properties"]["version"]["enum"] == [SOURCE_DUTY_AUTHORING_VERSION]
            if outcome not in {"old_inline", "old_roster", "old_plan"}:
                Draft202012Validator(schema).validate(wire)
            assert 0 < kwargs["timeout"] <= 300
            return subprocess.CompletedProcess(command, 0, stdout=raw.decode("utf-8"), stderr="")
        assert schema_path.name == "source-duty-decision-schema.json" and inventory_outcome
        assert 0 < kwargs["timeout"] <= 120
        task = json.loads(kwargs["contract_text"])
        assert task["source_duty_ledger"] == expected_compact
        decisions = _yes_decisions(expected_preflight, evidence_text=source)
        if outcome in {"roster_no", "roster_uncertain"}:
            decisions["participant_decisions"]["/external_systems/0"]["nonperformance"] = outcome.removeprefix("roster_")
        elif outcome == "roster_missing":
            decisions["participant_decisions"].pop("/external_systems/0")
        if outcome in {"context_no", "context_uncertain"}:
            decisions["participant_decisions"]["/external_systems/0"]["entity_name"] = outcome.removeprefix("context_")
        elif outcome == "context_missing":
            del decisions["participant_decisions"]["/external_systems/0"]["entity_name"]
        if outcome in {"plan_no", "plan_uncertain"}:
            decisions["source_plan"]["first_run"]["completeness"] = outcome.removeprefix("plan_")
        elif outcome == "plan_missing":
            del decisions["source_plan"]["terminal"]["producing_duty"]
        if outcome not in {"roster_missing", "plan_missing", "context_missing"}:
            Draft202012Validator(schema).validate(decisions)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(decisions), stderr="")

    def invoke_installed(command, timeout):
        installed_calls.append(list(command))
        assert "source-ledger-check" in command and 0 < timeout <= 30
        assert Path(command[command.index("--ledger-file") + 1]).read_bytes() == raw
        args = list(command[command.index("source-ledger-check"):])
        args[args.index("--repo-root") + 1] = str(flow.repo_root)
        output = StringIO()
        with redirect_stdout(output):
            code = cli.main(args)
        payload = json.loads(output.getvalue())
        installed_results.append({"returncode": code, "payload": payload})
        if inventory_outcome and "--decision-file" not in command:
            assert payload["preflight"] == expected_preflight
            assert payload["decision_task"]["source_duty_ledger"] == expected_compact
        return subprocess.CompletedProcess(command, code, stdout=output.getvalue(), stderr="")

    flow = host.HostCandidateFlow(**{**flow.__dict__, "prompt": prompt, "edit_evidence": "",
        "invoke_installed": invoke_installed,
        "retain_source_ledger_bytes": lambda value: retained.update(raw=value),
        "retain_diagnostic_bytes": lambda name, value: retained.update({name: value})})
    observation = {"source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "source_duty_verifier_host_invocations": 0, "candidate_host_invocations": 0,
        "proposal_command_invocations": 0}
    kwargs = dict(flow=flow, contract=contract, source=source, host_workspace=workspace,
        host_argv=flow.host_argv, deadline=WholeJourneyDeadline(time.monotonic(), time.monotonic),
        observation=observation, invoke_host=invoke_host, check_payload=_accepted_request()[3])
    if outcome in {"invalid_citation", "old_inline", "old_roster", "roster_no", "roster_uncertain", "roster_missing", "plan_no", "plan_uncertain", "plan_missing", "context_no", "context_uncertain", "context_missing", "old_plan"}:
        with pytest.raises(host.HostCandidateFlowError, match=("advertised authoring schema" if outcome in {"old_inline", "old_roster", "old_plan"} else "decision check returned nonzero" if outcome.startswith(("roster_", "plan_", "context_")) else "preflight returned nonzero")):
            run_source_duty_phase(**kwargs)
    else:
        result = run_source_duty_phase(**kwargs)
        if inventory_outcome:
            assert result.receipt["ledger"] == ledger
            assert compact_source_duty_view(result.receipt["ledger"]) == expected_compact
        else:
            assert result.receipt is None and result.decision_path is None
            assert json.loads(result.clarification.stdout)["clarification"]["question"] == wire["result"]["question"]
    assert retained["raw"] == raw
    assert observation["source_ledger_output_sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(host_calls) == (2 if inventory_outcome else 1)
    assert len(installed_calls) == (2 if inventory_outcome else 0 if outcome in {"old_inline", "old_roster", "old_plan"} else 1)
    assert observation["candidate_host_invocations"] == observation["proposal_command_invocations"] == 0
    assert proposals == []
    import os
    if directory := os.environ.get("ODYLITH_MENTION_TEST_EVIDENCE_DIR"):
        destination = Path(directory) / "native"
        destination.mkdir(parents=True, exist_ok=True)
        witness = {
            "kind": "synthetic mocked native host; real in-process CLI admission; no model call",
            "outcome": outcome, "source": source, "wire": wire, "raw_response": raw.decode("utf-8"),
            "schema": contract["source_ledger"]["source_ledger_schema"],
            "expected_preflight": expected_preflight, "expected_compact": expected_compact,
            "installed_results": installed_results, "observation": observation,
            "host_calls": host_calls, "installed_calls": installed_calls,
            "retained": {key: value.decode("utf-8") for key, value in retained.items()},
        }
        (destination / f"{outcome}.json").write_text(json.dumps(witness, ensure_ascii=False, sort_keys=True, indent=2))
