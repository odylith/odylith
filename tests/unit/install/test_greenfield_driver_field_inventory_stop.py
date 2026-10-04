"""Real compiler preflight stops invalid field identities before verification."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import subprocess

import pytest

import greenfield_matrix_host_candidate as host
from greenfield_matrix_release_artifacts import begin_retained_case_evidence, record_retained_case_bytes
from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import combined_prompt_evidence_source
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
from tests.unit.runtime.test_greenfield_source_duty_ledger import _material_duty_case


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_actual_driver_real_cli_preflight_stops_invalid_exact_field_identity(tmp_path, monkeypatch, mutation):
    prompt, canonical = _material_duty_case()
    source = combined_prompt_evidence_source(prompt=prompt, edit_evidence="")
    # The same authentic inventory preflights before changing only its relationship.
    assert preflight_greenfield_source_duty_ledger(canonical, evidence_text=source)["claims"]
    if mutation == "missing":
        canonical["off_path_transitions"][0]["effects"][0]["field"] = "private absent access field"
    else:
        duplicate = deepcopy(canonical["state_fields"][0])
        duplicate["id"] = "F4"
        canonical["state_fields"].append(duplicate)
    compact = compact_source_duty_view(canonical)
    gate = {"decision": "admit", "required_fields": [], "owner_quote": "reviewer",
            "task_quote": "defines scope", "result_quote": "scope", "question": ""}
    flow, _host_stub, _installed_stub, _host_stub_calls, proposals, repo = _flow(
        tmp_path, contract={"version": "unused fixture"}, candidate={},
    )
    installed, host_calls, retained = [], [], {}
    evidence_root = tmp_path / "private-evidence"
    evidence_root.mkdir(mode=0o700)
    evidence = begin_retained_case_evidence(evidence_root=evidence_root, case_id=mutation)

    def installed_cli(command, timeout):
        assert timeout > 0
        installed.append(list(command))
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = cli.main(command[2:])
        return subprocess.CompletedProcess(command, returncode, stdout=stdout.getvalue(), stderr=stderr.getvalue())

    def author_inventory(command, **kwargs):
        name = Path(command[command.index("--output-schema") + 1]).name
        host_calls.append(name)
        assert name in {"authority-gate-schema.json", "source-ledger-schema.json"}, "no later model phase is authorized"
        payload = gate if name == "authority-gate-schema.json" else compact
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    def retain(name):
        def save(value):
            path = record_retained_case_bytes(evidence, f"semantic/{name}.raw.v1.json", value)
            assert path.stat().st_mode & 0o777 == 0o600
            assert not path.is_relative_to(repo)
            retained[name] = path.read_bytes()
        return save

    monkeypatch.setattr(host, "_invoke_host", author_inventory)
    flow = host.HostCandidateFlow(**{
        **flow.__dict__, "prompt": prompt, "edit_evidence": "", "timeout": 315.0,
        "env": {**flow.env, "ODYLITH_GREENFIELD_MODEL_PROFILE": STANDARD_PROFILE_ID},
        "invoke_installed": installed_cli,
        "retain_authority_gate_bytes": retain("gate"),
        "retain_source_ledger_bytes": retain("inventory"),
        "retain_source_ledger_preflight_bytes": retain("preflight"),
    })
    with pytest.raises(host.HostCandidateFlowError, match="source ledger preflight returned nonzero") as caught:
        host.run_host_candidate_flow(flow)

    assert host_calls == ["authority-gate-schema.json", "source-ledger-schema.json"]
    assert [command[2] for command in installed] == ["candidate-contract", "authority-check", "source-ledger-check"]
    assert all("--decision-file" not in command for command in installed)
    assert proposals == []
    assert json.loads(retained["gate"]) == gate
    assert json.loads(retained["inventory"]) == compact
    preflight_error = json.loads(retained["preflight"])
    assert "state-field" in json.dumps(preflight_error)
    stage = flow.observation_sink
    assert caught.value.observation == stage
    assert stage["version"].endswith(".v12")
    assert stage["status"] == "failed" and stage["stage"] == "source-ledger-preflight"
    assert stage["authority_gate_returncode"] == stage["authority_check_returncode"] == 0
    assert stage["source_ledger_preflight_returncode"] == 2
    assert stage["host_invocations"] == 2
    assert stage["authority_gate_host_invocations"] == stage["source_ledger_host_invocations"] == 1
    assert stage["source_ledger_check_command_invocations"] == 1
    for field in ("source_duty_verifier_host_invocations", "candidate_host_invocations",
                  "proposal_command_invocations", "runtime_semantic_model_call_count",
                  "post_receipt_provider_invocations"):
        assert stage[field] == 0
    assert "source_duty_verifier_task_sha256" not in stage
    assert not {"candidate_request_bytes", "candidate_request_sha256", "candidate_transport_version"} & stage.keys()
    assert "host_command_diagnostic" not in stage
    for field in ("candidate_temp_cleaned", "authority_gate_temp_cleaned", "source_ledger_temp_cleaned",
                  "source_duty_decision_temp_cleaned", "host_workspace_cleaned"):
        assert stage[field] is True
    assert list(repo.iterdir()) == []
    # Public diagnostics contain categorical failure, numeric indexes/counts and hashes.
    for public in (str(caught.value), json.dumps(stage)):
        assert prompt not in public
        assert "private absent access field" not in public
        assert "Consent access records access availability" not in public
        assert "Consent cache records the cached copy" not in public
