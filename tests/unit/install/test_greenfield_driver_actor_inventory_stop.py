"""Real source-local CLI preflight stops broad actor custody before verification."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import subprocess

import pytest

from odylith.runtime.domain_intelligence import greenfield_host_flow as host
from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
from tests.unit.runtime.test_greenfield_source_duty_ledger import _material_duty_case


@pytest.mark.parametrize("scope", ["whole_action", "workflow_paragraph"])
def test_real_driver_and_fresh_cli_stop_actor_inventory_before_any_later_call(tmp_path, monkeypatch, scope):
    prompt, ledger = _material_duty_case()
    first = ledger["first_path_actions"][0]
    if scope == "whole_action":
        first["actor_ref"] = deepcopy(first["event_ref"])
        first["statement"] = first["actor_ref"]["quote"]
    else:
        paragraph = "A reviewer defines scope and audience. Human Actors: The reviewer checks a submission. Product Systems: A portal records the submission."
        first["actor_ref"] = {"quote": paragraph, "context": paragraph}
        first["role_refs"].append(deepcopy(first["actor_ref"]))
    compact = compact_source_duty_view(ledger)
    gate = {"decision": "admit", "required_fields": [], "owner_quote": "reviewer",
            "task_quote": "defines scope", "result_quote": "scope", "question": ""}
    repo = tmp_path / "consumer"
    repo.mkdir()
    executable = tmp_path / "trusted/bin/codex"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    installed_calls, host_calls, retained = [], [], {}

    def installed_cli(command, timeout):
        assert timeout > 0
        installed_calls.append(list(command))
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = cli.main(command[2:])
        return subprocess.CompletedProcess(command, returncode, stdout=stdout.getvalue(), stderr=stderr.getvalue())

    def author_gate_and_inventory(command, **kwargs):
        phase = Path(command[command.index("--output-schema") + 1]).name
        host_calls.append(phase)
        assert phase in {"authority-gate-schema.json", "source-ledger-schema.json"}
        payload = gate if phase == "authority-gate-schema.json" else compact
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    def forbid_proposal(*args):
        pytest.fail("actor inventory failure must not invoke propose")

    monkeypatch.setattr(host, "_invoke_host", author_gate_and_inventory)
    flow = host.HostCandidateFlow(
        repo_root=repo, temp_parent=tmp_path / "outside-evidence",
        host_argv=(str(executable), "exec", "--ephemeral", "--ignore-user-config",
                   "--skip-git-repo-check", "--sandbox", "read-only", "--model",
                   "gpt-6-astra", "--config", "model_reasoning_effort=medium",
                   "--output-schema", "{candidate_schema}", "-"),
        prompt=prompt, edit_evidence="", timeout=315.0,
        env={"PATH": str(executable.parent), "ODYLITH_GREENFIELD_MODEL_PROFILE": STANDARD_PROFILE_ID},
        trusted_codex_executable=str(executable), expected_model="gpt-6-astra",
        expected_reasoning_effort="medium", invoke_installed=installed_cli,
        invoke_propose=forbid_proposal,
        retain_authority_gate_bytes=lambda value: retained.__setitem__("gate", value),
        retain_source_ledger_bytes=lambda value: retained.__setitem__("inventory", value),
        retain_source_ledger_preflight_bytes=lambda value: retained.__setitem__("preflight", value),
    )
    with pytest.raises(host.HostCandidateFlowError, match="source ledger preflight returned nonzero"):
        host.run_host_candidate_flow(flow)

    assert host_calls == ["authority-gate-schema.json", "source-ledger-schema.json"]
    assert [command[2] for command in installed_calls] == ["candidate-contract", "authority-check", "source-ledger-check"]
    assert all("--decision-file" not in command for command in installed_calls)
    assert json.loads(retained["gate"]) == gate
    assert json.loads(retained["inventory"]) == compact
    assert "actor identity" in json.dumps(json.loads(retained["preflight"]))
    stage = flow.observation_sink
    assert stage["status"] == "failed" and stage["stage"] == "source-ledger-preflight"
    assert stage["authority_gate_returncode"] == stage["authority_check_returncode"] == 0
    assert stage["source_ledger_preflight_returncode"] == 2
    assert stage["host_invocations"] == 2
    assert stage["authority_gate_host_invocations"] == stage["source_ledger_host_invocations"] == 1
    for key in ("source_duty_verifier_host_invocations", "candidate_host_invocations",
                "proposal_command_invocations", "runtime_semantic_model_call_count",
                "post_receipt_provider_invocations"):
        assert stage[key] == 0
    assert "source_duty_verifier_task_sha256" not in stage
    for key in ("candidate_temp_cleaned", "authority_gate_temp_cleaned", "source_ledger_temp_cleaned",
                "source_duty_decision_temp_cleaned", "host_workspace_cleaned"):
        assert stage[key] is True
    assert list(repo.iterdir()) == []
    assert prompt not in str(stage) and prompt not in str(json.loads(retained["preflight"]))
