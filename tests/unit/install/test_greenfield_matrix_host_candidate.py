from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from odylith.runtime.domain_intelligence import greenfield_host_flow as host_module
from odylith.runtime.domain_intelligence import greenfield_host_transport as transport_module
from scripts.release import greenfield_model_profiles as profile_module
from scripts.release import greenfield_preconfirm_matrix as matrix_module
from greenfield_matrix_release_artifacts import RetainedEvidenceCase
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import expand_compact_source_duty_ledger
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import source_duty_entailment_task
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_VERSION, preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
from odylith.runtime.domain_intelligence.greenfield_host_candidate import greenfield_host_candidate_contract
from odylith.runtime.domain_intelligence.greenfield_authority_gate import greenfield_authority_gate_contract
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import (
    PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS,
    WHOLE_JOURNEY_ELAPSED_SCOPE,
    WholeJourneyDeadline,
    whole_journey_observation_issues,
)


def _completed(argv: list[str], *, stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


def _fixture_host_ledger() -> dict:
    event = {"quote": "A reviewer creates a reviewable plan.",
             "context": "A reviewer creates a reviewable plan."}
    return compact_source_duty_view({
        "version": SOURCE_DUTY_LEDGER_VERSION, "status": "inventory", "question": "",
        "evidence_controls": [{"quote": "Notes are background only.",
                               "context": "Notes are background only.",
                               "handling": "reference_context"}],
        "first_path_actions": [{
            "id": "d1", "source_refs": [event], "performer_role": "human_actor",
            "observable_result": "A reviewable plan exists.",
            "statement": "reviewer creates a reviewable plan", "event_ref": event,
            "actor_ref": {"quote": "reviewer", "context": event["context"]},
            "role_refs": [{"quote": "First Complete Path:", "context": "First Complete Path:"}],
            "action": "creates", "target": "a reviewable plan",
        }],
        "supporting_human_actions": [], "system_duties": [], "state_fields": [],
        "off_path_transitions": [], "conditional_guards": [], "boundaries": [], "proof_duties": [],
    })


def _flow(tmp_path: Path, *, candidate: object, contract: object, gate_decision: str = "admit"):
    repo = tmp_path / "consumer"
    repo.mkdir()
    temp_parent = tmp_path / "evidence"
    trusted_codex = tmp_path / "trusted/bin/codex"
    trusted_codex.parent.mkdir(parents=True)
    trusted_codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    trusted_codex.chmod(0o755)
    installed_calls: list[tuple[list[str], float]] = []
    host_calls: list[tuple[list[str], str, float, Path]] = []
    proposal_paths: list[Path] = []
    source = contract.get("request", {}).get("evidence", "First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only.")
    contract_payload = greenfield_host_candidate_contract(source)
    contract_payload["authority_gate"] = greenfield_authority_gate_contract(
        prompt=source, edit_evidence="Keep the source path.", evidence_source=source,
    )
    contract_payload.update(contract)
    gate = {
        "decision": gate_decision,
        "required_fields": ["first_path"] if gate_decision == "clarify" else [],
        "owner_quote": "" if gate_decision == "clarify" else "reviewer",
        "task_quote": "" if gate_decision == "clarify" else "creates a reviewable plan",
        "result_quote": "" if gate_decision == "clarify" else "a reviewable plan",
        "question": "What first path?" if gate_decision == "clarify" else "",
    }
    ledger = _fixture_host_ledger()
    expanded = expand_compact_source_duty_ledger(ledger, evidence_text=source)
    preflight = preflight_greenfield_source_duty_ledger(expanded, evidence_text=source)
    decision_task = source_duty_entailment_task(preflight, evidence_text=source)
    decision_set = {
        "version": host_module.SOURCE_DUTY_DECISION_SET_VERSION,
        "verifier_task_sha256": decision_task["verifier_task_sha256"],
        "decisions": {"d1": {"verdict": "yes",
                       "support_ref_indexes": [0], "role_ref_indexes": [0, 1]}},
        "source_completeness": {"verdict": "yes", "omissions": []},
    }
    ledger_receipt = validate_greenfield_source_duty_ledger(
        expanded, evidence_text=source, decision_set=decision_set,
    )

    def installed(command, timeout):
        installed_calls.append((list(command), timeout))
        if "authority-check" in command:
            gate_path = Path(command[command.index("--gate-file") + 1])
            assert gate_path.is_file()
            assert json.loads(gate_path.read_text(encoding="utf-8")) == gate
            mode = "clarification_required" if gate_decision == "clarify" else "authority_admitted"
            result = {"mode": mode}
            if gate_decision == "admit":
                result["gate"] = gate
            return _completed(list(command), stdout=json.dumps(result))
        if "source-ledger-check" in command:
            ledger_path = Path(command[command.index("--ledger-file") + 1])
            assert ledger_path.is_file()
            assert json.loads(ledger_path.read_text(encoding="utf-8")) == ledger
            if "--decision-file" not in command:
                return _completed(list(command), stdout=json.dumps({
                    "mode": "source_duty_preflight",
                    "preflight": preflight,
                    "decision_task": decision_task,
                }))
            decision_path = Path(command[command.index("--decision-file") + 1])
            assert json.loads(decision_path.read_text(encoding="utf-8")) == decision_set
            return _completed(list(command), stdout=json.dumps({
                "mode": "source_duty_admitted", "receipt": ledger_receipt,
            }))
        return _completed(list(command), stdout=json.dumps(contract_payload))

    def host_run(command, **kwargs):
        host_calls.append(
            (
                list(command),
                str(kwargs["contract_text"]),
                float(kwargs["timeout"]),
                Path(kwargs["cwd"]),
            )
        )
        schema_path = Path(command[command.index("--output-schema") + 1])
        assert schema_path.is_file()
        assert schema_path.parent == Path(kwargs["cwd"])
        if schema_path.name == "authority-gate-schema.json":
            return _completed(list(command), stdout=json.dumps(gate))
        if schema_path.name == "source-ledger-schema.json":
            return _completed(list(command), stdout=json.dumps(ledger))
        if schema_path.name == "source-duty-decision-schema.json":
            return _completed(list(command), stdout=json.dumps(decision_set))
        return _completed(list(command), stdout=json.dumps(candidate))

    def propose(path: Path, gate_path: Path, ledger_path: Path, timeout: float):
        proposal_paths.append(path)
        assert path.is_file()
        assert gate_path.is_file()
        assert ledger_path.is_file()
        assert json.loads(path.read_text(encoding="utf-8")) == candidate
        return _completed(
            ["odylith", "greenfield", "propose"],
            stdout=json.dumps({"mode": "product_create_transaction"}),
        )

    return (
        host_module.HostCandidateFlow(
            repo_root=repo,
            temp_parent=temp_parent,
            host_argv=(
                str(trusted_codex),
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                "gpt-6-astra",
                "--config",
                "model_reasoning_effort=medium",
                "--output-schema",
                "{candidate_schema}",
                "-",
            ),
            prompt="First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only.",
            edit_evidence="Keep the source path.",
            timeout=5.0,
            env={
                "PATH": str(trusted_codex.parent),
                "ODYLITH_GREENFIELD_MODEL_PROFILE": STANDARD_PROFILE_ID,
            },
            trusted_codex_executable=str(trusted_codex),
            expected_model="gpt-6-astra",
            expected_reasoning_effort="medium",
            invoke_installed=installed,
            invoke_propose=propose,
        ),
        host_run,
        installed_calls,
        host_calls,
        proposal_paths,
        repo,
    )


def test_host_candidate_happy_path_is_one_shot_and_cleans_candidate_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, installed_calls, host_calls, proposal_paths, repo = _flow(
        tmp_path,
        contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "observe": observations.append})

    result = host_module.run_host_candidate_flow(flow)

    assert result.returncode == 0
    assert len(installed_calls) == 4
    assert installed_calls[0][0] == [
        "./.odylith/bin/odylith",
        "greenfield",
        "candidate-contract",
        "--repo-root",
        ".",
        "--prompt",
        "First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only.",
        "--edit",
        "Keep the source path.",
    ]
    assert len(host_calls) == 4
    assert host_calls[3][0][:4] == [
        str((tmp_path / "trusted/bin/codex").resolve()),
        "exec",
        "--ephemeral",
        "--ignore-user-config",
    ]
    assert "{candidate_schema}" not in host_calls[3][0]
    assert "authority_gate" not in json.loads(host_calls[3][1])
    assert json.loads(host_calls[3][1])["accepted_source_duty_inventory"] == _fixture_host_ledger()
    assert len(proposal_paths) == 1
    assert not proposal_paths[0].exists()
    assert not any(path == repo or repo in path.parents for path in proposal_paths)
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["status"] == "passed"
    assert flow.observation_sink["host_invocations"] == 4
    assert flow.observation_sink["authority_gate_host_invocations"] == 1
    assert flow.observation_sink["candidate_host_invocations"] == 1
    assert flow.observation_sink["source_ledger_host_invocations"] == 1
    assert flow.observation_sink["source_duty_verifier_host_invocations"] == 1
    assert flow.observation_sink["source_ledger_check_command_invocations"] == 2
    assert flow.observation_sink["source_duty_decision_set_sha256"] == (
        json.loads(host_calls[3][1])["source_duty_custody"]["decision_set_sha256"]
    )
    assert flow.observation_sink["source_completeness_verdict"] == "yes"
    assert flow.observation_sink["source_completeness_omission_count"] == 0
    assert flow.observation_sink["authority_check_command_invocations"] == 1
    assert flow.observation_sink["authority_gate_request"] == flow.observation_sink["host_request"]
    assert flow.observation_sink["source_ledger_request"] == flow.observation_sink["host_request"]
    assert flow.observation_sink["whole_journey_seconds"] >= flow.observation_sink["elapsed_seconds"]
    assert flow.observation_sink["model_profile_id"] == STANDARD_PROFILE_ID
    assert flow.observation_sink["source_sha256"] == hashlib.sha256(
        b"First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only."
    ).hexdigest()
    assert flow.observation_sink["response_kind"] == "authored"
    request = flow.observation_sink["host_request"]
    assert set(request) == {
        "version", "executable_sha256", "argument_count", "model",
        "reasoning_effort", "output_schema_present", "argv_shape_sha256",
    }
    assert request["model"] == "gpt-6-astra"
    assert request["reasoning_effort"] == "medium"
    assert request["output_schema_present"] is True
    assert "host_argv" not in flow.observation_sink
    assert flow.observation_sink["candidate_temp_cleaned"] is True
    assert flow.observation_sink["authority_gate_temp_cleaned"] is True
    assert flow.observation_sink["source_ledger_temp_cleaned"] is True
    assert flow.observation_sink["source_duty_decision_temp_cleaned"] is True
    assert flow.observation_sink["host_workspace_cleaned"] is True
    assert flow.observation_sink["raw_candidate_sha256"] == hashlib.sha256(
        json.dumps(
            {"version": "candidate", "result": {"status": "authored"}},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    raw_candidate = json.dumps(
        {"version": "candidate", "result": {"status": "authored"}},
    ).encode("utf-8")
    assert flow.observation_sink["host_output_sha256"] == hashlib.sha256(raw_candidate).hexdigest()
    assert flow.observation_sink["host_output_bytes"] == len(raw_candidate)
    assert flow.observation_sink["proposal_returncode"] == 0
    assert flow.observation_sink["proposal_mode"] == "product_create_transaction"
    assert flow.observation_sink["runtime_semantic_model_call_count"] == 0
    assert flow.observation_sink["post_receipt_provider_invocations"] == 0
    assert not host_calls[0][3].exists()
    assert "candidate" not in flow.observation_sink


def test_real_compiler_task_traverses_verifier_receipt_and_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate={"result": {"status": "authored"}},
    )
    retained_preflight: list[bytes] = []
    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "retain_source_ledger_preflight_bytes": retained_preflight.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    assert host_module.run_host_candidate_flow(flow).returncode == 0
    compiler_payload = json.loads(retained_preflight[0])
    source = json.loads(host_calls[1][1])["request"]["evidence"]
    expected = source_duty_entailment_task(compiler_payload["preflight"], evidence_text=source)
    assert json.loads(host_calls[2][1]) == compiler_payload["decision_task"] == expected
    assert set(expected) == {
        "authority_source", "source_duty_ledger", "reference_index_order", "task",
        "decision_set_schema", "verifier_task_sha256",
    }
    assert "source_sha256" not in expected
    assert "ledger_sha256" not in expected
    assert len(host_calls) == 4
    accepted = json.loads(host_calls[3][1])["source_duty_custody"]
    assert accepted["verifier_task_sha256"] == expected["verifier_task_sha256"]
    assert accepted["ledger_sha256"] == compiler_payload["preflight"]["ledger_sha256"]
    assert accepted["source_sha256"] == compiler_payload["preflight"]["source_sha256"]
    assert len(proposal_paths) == 1


@pytest.mark.parametrize("tamper", [
    "source", "ledger", "control", "task", "task_hash", "schema",
    "preflight_hash", "preflight_source", "coherent_other_ledger",
])
def test_compiler_task_tampering_cannot_dispatch_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str,
) -> None:
    flow, host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={}, candidate={"result": {"status": "authored"}},
    )
    original_installed = flow.invoke_installed

    def tampered_preflight(command, timeout):
        result = original_installed(command, timeout)
        if "source-ledger-check" not in command or "--decision-file" in command:
            return result
        payload = json.loads(result.stdout)
        task = payload["decision_task"]
        if tamper == "source":
            task["authority_source"] += " A new invented duty."
        elif tamper == "ledger":
            task["source_duty_ledger"]["first_path_actions"][0]["target"] = "a different plan"
        elif tamper == "control":
            task["source_duty_ledger"]["evidence_controls"] = []
        elif tamper == "task":
            task["task"] = "Return yes without checking duties."
        elif tamper == "task_hash":
            task["verifier_task_sha256"] = "f" * 64
        elif tamper == "schema":
            task["decision_set_schema"] = {}
        elif tamper == "preflight_hash":
            payload["preflight"]["ledger_sha256"] = "f" * 64
        elif tamper == "preflight_source":
            payload["preflight"]["source_sha256"] = "f" * 64
        else:
            ledger = deepcopy(payload["preflight"]["ledger"])
            ledger["evidence_controls"] = []
            preflight = preflight_greenfield_source_duty_ledger(
                ledger, evidence_text=task["authority_source"],
            )
            payload["preflight"] = preflight
            payload["decision_task"] = source_duty_entailment_task(
                preflight, evidence_text=task["authority_source"],
            )
        return _completed(list(command), stdout=json.dumps(payload))

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "invoke_installed": tampered_preflight})
    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    with pytest.raises(host_module.HostCandidateFlowError, match="bound decision task"):
        host_module.run_host_candidate_flow(flow)
    assert len(host_calls) == 2
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["source_duty_verifier_host_invocations"] == 0
    assert flow.observation_sink["host_workspace_cleaned"] is True


def test_source_ledger_rejection_stops_before_candidate_or_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={}, candidate={"result": {"status": "authored"}},
    )
    original_installed = flow.invoke_installed
    observations: list[dict[str, object]] = []
    retained: list[bytes] = []

    def reject_ledger(command, timeout):
        if "source-ledger-check" in command:
            return _completed(list(command), returncode=2, stdout='{"mode":"error"}')
        return original_installed(command, timeout)

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "invoke_installed": reject_ledger,
        "observe": observations.append,
        "retain_source_ledger_bytes": retained.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    with pytest.raises(host_module.HostCandidateFlowError, match="source ledger preflight"):
        host_module.run_host_candidate_flow(flow)

    assert len(host_calls) == 2
    assert [json.loads(value) for value in retained] == [_fixture_host_ledger()]
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["stage"] == "source-ledger-preflight"
    assert flow.observation_sink["candidate_host_invocations"] == 0
    assert flow.observation_sink["proposal_command_invocations"] == 0
    assert flow.observation_sink["source_ledger_temp_cleaned"] is True
    assert flow.observation_sink["whole_journey_seconds"] >= flow.observation_sink["elapsed_seconds"]


def test_source_ledger_clarification_is_no_write_and_skips_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={}, candidate={"result": {"status": "authored"}},
    )
    original_installed = flow.invoke_installed
    observations: list[dict[str, object]] = []

    def clarify_ledger(command, timeout):
        if "source-ledger-check" in command:
            return _completed(list(command), stdout=json.dumps({
                "mode": "clarification_required",
                "clarification": {"question": "Which actor owns the first result?"},
            }))
        return original_installed(command, timeout)

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "invoke_installed": clarify_ledger,
        "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    completed = host_module.run_host_candidate_flow(flow)
    assert json.loads(completed.stdout)["mode"] == "clarification_required"
    assert len(host_calls) == 2
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    stage = flow.observation_sink
    assert stage["status"] == "passed"
    assert stage["source_ledger_preflight_mode"] == "clarification_required"
    assert stage["candidate_host_invocations"] == 0
    assert stage["source_ledger_temp_cleaned"] is True


@pytest.mark.parametrize("verdict", ["no", "uncertain", None])
def test_source_duty_verifier_denial_stops_before_candidate_or_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verdict: str | None,
) -> None:
    flow, original_host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={},
        candidate={"result": {"status": "authored"}},
    )
    original_installed = flow.invoke_installed
    observations: list[dict[str, object]] = []

    def verifier_host(command, **kwargs):
        schema = Path(command[command.index("--output-schema") + 1]).name
        if schema != "source-duty-decision-schema.json":
            return original_host_run(command, **kwargs)
        result = original_host_run(command, **kwargs)
        payload = json.loads(result.stdout)
        if verdict is None:
            payload["decisions"] = {}
        else:
            payload["decisions"]["d1"]["verdict"] = verdict
        return _completed(list(command), stdout=json.dumps(payload))

    def deny_decision(command, timeout):
        if "source-ledger-check" in command and "--decision-file" in command:
            return _completed(list(command), returncode=2,
                              stdout='{"mode":"source_duty_denied"}')
        return original_installed(command, timeout)

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "invoke_installed": deny_decision,
        "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", verifier_host)

    with pytest.raises(host_module.HostCandidateFlowError, match="decision check"):
        host_module.run_host_candidate_flow(flow)

    assert len(host_calls) == 3
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["source_duty_verifier_host_invocations"] == 1
    assert flow.observation_sink["candidate_host_invocations"] == 0
    assert flow.observation_sink["source_duty_decision_temp_cleaned"] is True


def test_source_duty_receipt_must_bind_the_exact_verifier_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={},
        candidate={"result": {"status": "authored"}},
    )
    original_installed = flow.invoke_installed
    observations: list[dict[str, object]] = []

    def swap_task_hash(command, timeout):
        result = original_installed(command, timeout)
        if "source-ledger-check" in command and "--decision-file" in command:
            payload = json.loads(result.stdout)
            payload["receipt"]["verifier_task_sha256"] = "f" * 64
            return _completed(list(command), stdout=json.dumps(payload))
        return result

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "invoke_installed": swap_task_hash,
        "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    with pytest.raises(host_module.HostCandidateFlowError, match="did not admit"):
        host_module.run_host_candidate_flow(flow)

    assert len(host_calls) == 3
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["candidate_host_invocations"] == 0


@pytest.mark.parametrize("completeness", [
    {"verdict": "no", "omissions": [{"omission_id": "o1"}]},
    {"verdict": "uncertain", "omissions": [{"omission_id": "o1"}]},
    None,
])
def test_nonaffirmative_source_completeness_cannot_start_a_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    completeness: dict[str, object] | None,
) -> None:
    flow, original_host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={},
        candidate={"result": {"status": "authored"}},
    )
    original_installed = flow.invoke_installed
    observations: list[dict[str, object]] = []

    def incomplete_host(command, **kwargs):
        result = original_host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1]).name
        if schema != "source-duty-decision-schema.json":
            return result
        decision_set = json.loads(result.stdout)
        if completeness is None:
            decision_set.pop("source_completeness")
        else:
            decision_set["source_completeness"] = completeness
        return _completed(list(command), stdout=json.dumps(decision_set))

    def falsely_admit(command, timeout):
        if "source-ledger-check" in command and "--decision-file" in command:
            decision_file = Path(command[command.index("--decision-file") + 1])
            decision_set = json.loads(decision_file.read_text(encoding="utf-8"))
            receipt = {
                "version": "odylith.greenfield.source-duty-ledger-receipt.v6",
                "source_sha256": hashlib.sha256(b"First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only.").hexdigest(),
                "ledger_sha256": "a" * 64,
                "verifier_task_sha256": "d" * 64,
                "decision_set_sha256": "b" * 64,
                "decision_set": decision_set,
            }
            return _completed(list(command), stdout=json.dumps({
                "mode": "source_duty_admitted", "receipt": receipt,
            }))
        return original_installed(command, timeout)

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "invoke_installed": falsely_admit,
        "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", incomplete_host)

    with pytest.raises(host_module.HostCandidateFlowError, match="did not admit"):
        host_module.run_host_candidate_flow(flow)

    assert len(host_calls) == 3
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["candidate_host_invocations"] == 0
    assert flow.observation_sink["source_completeness_verdict"] == (
        "missing" if completeness is None else completeness["verdict"]
    )
    assert flow.observation_sink["source_completeness_omission_count"] == (
        -1 if completeness is None else 1
    )


def test_source_ledger_has_separate_provisional_cap_and_journey_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, installed_calls, host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    clock = [0.0]
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1]).name
        clock[0] += 80.0 if schema == "source-ledger-schema.json" else 10.0
        return result

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 315.0, "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", timed_host)

    assert host_module.run_host_candidate_flow(flow).returncode == 0
    assert [call[2] for call in host_calls] == [300.0, 300.0, 120.0, 290.0]
    assert installed_calls[2][1] == 30.0
    assert installed_calls[3][1] == 30.0
    stage = flow.observation_sink
    assert stage["source_ledger_elapsed_seconds"] == 80.0
    assert stage["source_duty_verifier_elapsed_seconds"] == 10.0
    assert stage["source_duty_verifier_diagnostic_cap_seconds"] == 120.0
    assert stage["elapsed_seconds"] == 20.0
    assert stage["whole_journey_seconds"] == 110.0
    assert stage["source_ledger_diagnostic_cap_seconds"] == 300.0
    assert stage["proposal_phase_elapsed_seconds"] == stage["elapsed_seconds"]
    assert stage["whole_journey_diagnostic_cap_seconds"] == 660.0
    assert stage["whole_journey_bound_status"] == "diagnostic_unqualified"
    assert stage["whole_journey_deadline_status"] == "within"
    assert whole_journey_observation_issues(stage) == []


def test_whole_journey_deadline_never_replenishes_between_source_phases() -> None:
    clock = [0.0]
    budget = WholeJourneyDeadline(0.0, lambda: clock[0])
    assert budget.request_timeout(180.0) == 180.0
    clock[0] += 300.0  # Source ledger consumes the same fixed budget.
    assert budget.remaining() == 360.0
    clock[0] += 120.0  # The source-only verifier also consumes it.
    assert budget.remaining() == 240.0
    clock[0] = 650.0
    assert budget.request_timeout(30.0) == 10.0
    clock[0] = PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS
    with pytest.raises(TimeoutError, match="deadline expired"):
        budget.request_timeout(30.0)


def test_whole_journey_clamps_local_check_and_verifier_then_stops_before_next_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, installed_calls, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    clock = [0.0]
    observations: list[dict[str, object]] = []
    original_installed = flow.invoke_installed
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1]).name
        if schema == "source-ledger-schema.json":
            clock[0] += 295.0
        elif schema == "source-duty-decision-schema.json":
            clock[0] += 1.0
        return result

    def timed_installed(command, timeout):
        result = original_installed(command, timeout)
        if "source-ledger-check" in command:
            clock[0] += 4.0
        return result

    def retain_ledger(_value):
        clock[0] += 360.0

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 315.0, "observe": observations.append,
        "invoke_installed": timed_installed,
        "retain_source_ledger_bytes": retain_ledger,
    })
    monkeypatch.setattr(host_module, "_invoke_host", timed_host)

    with pytest.raises(host_module.HostCandidateFlowError, match="deadline expired"):
        host_module.run_host_candidate_flow(flow)

    assert installed_calls[2][1] == 5.0
    assert len(installed_calls) == 3  # No post-verdict source check.
    assert host_calls[2][2] == 1.0
    assert len(host_calls) == 3  # No candidate authoring.
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    stage = flow.observation_sink
    assert stage["whole_journey_seconds"] == 660.0
    assert stage["whole_journey_deadline_status"] == "expired"
    assert stage["status"] == "failed"
    assert stage["host_workspace_cleaned"] is True


@pytest.mark.parametrize("callback", ["source-ledger", "proposal", "cleanup", "observer"])
def test_late_callback_never_returns_an_admitted_result_and_cleans_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, callback: str,
) -> None:
    flow, host_run, _installed_calls, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    clock = [0.0]
    observations: list[dict[str, object]] = []
    original_propose = flow.invoke_propose
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    def expire(_value=None):
        clock[0] = 660.0

    def late_propose(*args):
        result = original_propose(*args)
        expire()
        return result

    def observe(value):
        observations.append(dict(value))
        if callback == "observer":
            expire()

    if callback == "cleanup":
        original_cleanup = host_module.tempfile.TemporaryDirectory.cleanup

        def late_cleanup(directory):
            original_cleanup(directory)
            expire()

        monkeypatch.setattr(host_module.tempfile.TemporaryDirectory, "cleanup", late_cleanup)
    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "observe": observe,
        "retain_source_ledger_bytes": expire if callback == "source-ledger" else None,
        "invoke_propose": late_propose if callback == "proposal" else original_propose,
    })

    with pytest.raises(host_module.HostCandidateFlowError) as error:
        host_module.run_host_candidate_flow(flow)

    assert error.value.observation["status"] == "failed"
    assert error.value.observation["whole_journey_deadline_status"] == "expired"
    assert error.value.observation["whole_journey_seconds"] == 660.0
    assert error.value.observation["host_workspace_cleaned"] is True
    assert flow.observation_sink["status"] == "failed"
    assert flow.observation_sink["whole_journey_deadline_status"] == "expired"
    assert list(repo.iterdir()) == []
    assert list(flow.temp_parent.iterdir()) == []
    if callback == "source-ledger":
        assert len(host_calls) == 2
        assert proposal_paths == []
    else:
        assert len(proposal_paths) == 1
        assert not proposal_paths[0].exists()


def test_successful_observer_work_is_measured_before_authoritative_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, _hosts, _proposals, _repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    clock = [0.0]
    provisional: list[dict[str, object]] = []
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    def observe(snapshot):
        provisional.append(dict(snapshot))
        clock[0] += 150.0

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "observe": observe, "timeout": 315.0})
    assert host_module.run_host_candidate_flow(flow).returncode == 0
    assert len(provisional) == 1
    assert provisional[0]["whole_journey_seconds"] == 0.0
    final = flow.observation_sink
    assert final["whole_journey_seconds"] == 150.0
    assert final["proposal_phase_elapsed_seconds"] == 150.0
    assert final["elapsed_seconds"] == 150.0
    assert final["whole_journey_deadline_status"] == "within"
    assert final["whole_journey_elapsed_scope"] == WHOLE_JOURNEY_ELAPSED_SCOPE
    assert whole_journey_observation_issues(final) == []


@pytest.mark.parametrize("observer_seconds", [150.0, 315.0, 660.0])
def test_preconfirm_retains_final_observer_timing_and_matching_stage_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, observer_seconds: float,
) -> None:
    flow, host_run, _installed, _hosts, _proposals, repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    retained_root = tmp_path / "retained"
    retained_root.mkdir()
    retained = RetainedEvidenceCase("test-case", retained_root, tmp_path / "final")
    clock = [0.0]
    stage: dict[str, object] = {}
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    monkeypatch.setattr(matrix_module, "_run", lambda **kw: flow.invoke_installed(
        kw["command"], kw["timeout"],
    ))
    monkeypatch.setattr(matrix_module, "_run_greenfield_propose", lambda **kw: flow.invoke_propose(
        Path(kw["candidate_file"]), Path(kw["gate_file"]), Path(kw["ledger_file"]), kw["timeout"],
    ))

    def observe(_snapshot):
        clock[0] += observer_seconds

    def invoke():
        return matrix_module._run_host_candidate_propose(
            repo_root=repo, env=flow.env, prompt=flow.prompt,
            edit_evidence=flow.edit_evidence, repair_tier="none", timeout=315.0,
            host_candidate_argv=flow.host_argv, retained_case=retained,
            observe_stage=observe, stage_observation=stage,
        )

    if observer_seconds < 315.0:
        assert invoke().returncode == 0
    else:
        message = "operational timeout" if observer_seconds < 660.0 else "deadline expired"
        with pytest.raises(matrix_module.HostCandidateFlowError, match=message):
            invoke()
    retained_snapshot = json.loads((
        retained_root / "semantic/host-authoring-observation.v1.json"
    ).read_text())
    assert retained_snapshot == stage
    assert retained_snapshot["whole_journey_seconds"] == observer_seconds
    assert retained_snapshot["elapsed_seconds"] == observer_seconds
    assert retained_snapshot["status"] == ("passed" if observer_seconds < 315.0 else "failed")
    assert retained_snapshot["whole_journey_elapsed_scope"] == WHOLE_JOURNEY_ELAPSED_SCOPE


def test_primary_failure_survives_late_failing_observer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, _hosts, _proposals, _repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    clock = [0.0]
    original_installed = flow.invoke_installed
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    def fail_contract(command, timeout):
        result = original_installed(command, timeout)
        result.returncode = 1
        return result

    def observe(_snapshot):
        clock[0] = 700.0
        raise RuntimeError("observer broke")

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "invoke_installed": fail_contract, "observe": observe,
    })
    with pytest.raises(host_module.HostCandidateFlowError, match="contract command failed") as error:
        host_module.run_host_candidate_flow(flow)
    assert error.value.observation == flow.observation_sink
    assert flow.observation_sink["whole_journey_seconds"] == 700.0
    assert flow.observation_sink["whole_journey_deadline_status"] == "expired"
    assert flow.observation_sink["observer_error"] == "RuntimeError"


@pytest.mark.parametrize("changed", [
    {"whole_journey_diagnostic_cap_seconds": 661.0},
    {"whole_journey_bound_status": "qualified"},
    {"whole_journey_deadline_status": "expired"},
    {"whole_journey_seconds": 660.0},
    {"whole_journey_seconds": float("nan")},
    {"whole_journey_seconds": -1.0},
    {"whole_journey_seconds": True},
    {"proposal_phase_elapsed_seconds": float("inf")},
    {"proposal_phase_elapsed_seconds": 19.0},
    {"elapsed_seconds": -1.0},
])
def test_retained_deadline_proof_rejects_false_success(changed) -> None:
    stage = {
        "whole_journey_diagnostic_cap_seconds": 660.0,
        "candidate_completion_reserve_seconds": 15.0,
        "whole_journey_route": "odylith-greenfield-prepare.v1",
        "whole_journey_supervision": {"version": "odylith.greenfield.journey-supervision.v1", "guardian_pid": 12345, "cancellation_grace_seconds": 2.0},
        "whole_journey_bound_status": "diagnostic_unqualified",
        "whole_journey_deadline_status": "within",
        "whole_journey_elapsed_scope": WHOLE_JOURNEY_ELAPSED_SCOPE,
        "whole_journey_seconds": 110.0,
        "proposal_phase_elapsed_seconds": 20.0,
        "elapsed_seconds": 20.0,
    }
    assert whole_journey_observation_issues({**stage, **changed})


def test_source_ledger_preflight_keeps_local_budget_after_host_uses_its_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, installed_calls, _host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    clock = [0.0]
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1]).name
        clock[0] += 299.95 if schema == "source-ledger-schema.json" else 1.0
        return result

    monkeypatch.setattr(host_module, "_invoke_host", timed_host)
    assert host_module.run_host_candidate_flow(flow).returncode == 0
    assert installed_calls[2][1] == 30.0
    assert installed_calls[3][1] == 30.0


def test_host_candidate_qualification_rejects_renamed_wrapper_and_secret_config(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted/codex"
    wrapper = tmp_path / "wrapper/codex"
    for path in (trusted, wrapper):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    base = (
        str(trusted), "exec", "--ephemeral", "--ignore-user-config",
        "--skip-git-repo-check", "--sandbox", "read-only",
        "--model", "gpt-6-astra", "--config",
        "model_reasoning_effort=medium", "--output-schema", "{candidate_schema}", "-",
    )

    with pytest.raises(ValueError, match="trusted Codex binary directly"):
        transport_module.qualify_host_candidate_argv(
            (str(wrapper), *base[1:]),
            trusted_codex_executable=str(trusted),
            expected_model="gpt-6-astra",
            expected_reasoning_effort="medium",
            expected_output_schema="{candidate_schema}",
        )
    with pytest.raises(ValueError, match="configured Codex executable"):
        transport_module.resolve_trusted_codex_executable(
            environ={
                "PATH": str(trusted.parent),
                "ODYLITH_REASONING_CODEX_BIN": str(wrapper),
            }
        )

    secret = "sk-private-do-not-retain"
    contaminated = (*base[:-3], "--config", f"api_key={secret}", *base[-3:])
    with pytest.raises(ValueError) as raised:
        transport_module.qualify_host_candidate_argv(
            contaminated,
            trusted_codex_executable=str(trusted),
            expected_model="gpt-6-astra",
            expected_reasoning_effort="medium",
            expected_output_schema="{candidate_schema}",
        )
    assert "canonical release argv contract" in str(raised.value)
    assert secret not in str(raised.value)


@pytest.mark.parametrize(
    "mutation",
    (
        ("--profile", "override"),
        ("--sandbox", "workspace-write"),
        ("--dangerously-bypass-approvals-and-sandbox",),
        ("--oss",),
        ("--local-provider", "ollama"),
        ("--image", "/tmp/input.png"),
        ("--cd", "/tmp"),
        ("--add-dir", "/tmp"),
        ("--json",),
        ("--output-last-message", "/tmp/message"),
        ("--enable", "feature"),
        ("review",),
        ("extra-positional",),
        ("-",),
    ),
)
def test_host_candidate_qualification_rejects_every_noncanonical_token(
    tmp_path: Path,
    mutation: tuple[str, ...],
) -> None:
    trusted = tmp_path / "trusted/codex"
    trusted.parent.mkdir(parents=True)
    trusted.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    trusted.chmod(0o755)
    canonical = (
        str(trusted), "exec", "--ephemeral", "--ignore-user-config",
        "--skip-git-repo-check", "--sandbox", "read-only",
        "--model", "gpt-6-astra", "--config",
        "model_reasoning_effort=medium", "--output-schema", "{candidate_schema}", "-",
    )
    contaminated = (*canonical[:-1], *mutation, canonical[-1])

    with pytest.raises(ValueError, match="canonical release argv contract"):
        transport_module.qualify_host_candidate_argv(
            contaminated,
            trusted_codex_executable=str(trusted),
            expected_model="gpt-6-astra",
            expected_reasoning_effort="medium",
            expected_output_schema="{candidate_schema}",
        )


def test_authority_gate_clarification_skips_candidate_and_propose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"version": "candidate", "result": {"status": "authored"}}
    flow, host_run, _installed, host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate=candidate,
        gate_decision="clarify",
    )
    observations: list[dict[str, object]] = []
    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "observe": observations.append})
    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    result = host_module.run_host_candidate_flow(flow)

    assert result.returncode == 0
    assert json.loads(result.stdout)["mode"] == "clarification_required"
    assert len(host_calls) == 1
    assert len(proposal_paths) == 0
    assert flow.observation_sink["response_kind"] == "clarification_required"
    assert flow.observation_sink["proposal_command_invocations"] == 0
    assert flow.observation_sink["candidate_host_invocations"] == 0
    assert flow.observation_sink["host_invocations"] == 1
    assert "host_request" not in flow.observation_sink
    assert "raw_candidate_sha256" not in flow.observation_sink
    assert flow.observation_sink["authority_gate_temp_cleaned"] is True
    assert flow.observation_sink["candidate_temp_cleaned"] is True


def test_real_gate_only_observation_passes_closed_profile_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, host_run, _installed, _host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate={},
        gate_decision="clarify",
    )
    observations: list[dict[str, object]] = []
    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 315.0, "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    assert host_module.run_host_candidate_flow(flow).returncode == 0
    evidence = profile_module.model_profile_evidence(
        STANDARD_PROFILE_ID,
        profile_module.model_profile_environment(STANDARD_PROFILE_ID, flow.env),
        observed={}, stage_observation=flow.observation_sink, raw_candidate={},
        expected_source="First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only.",
    )
    assert evidence["status"] == "passed", evidence["issues"]


def test_host_candidate_retains_raw_candidate_and_deterministic_failure_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"version": "candidate", "result": {"status": "authored"}}
    flow, host_run, _installed, _host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate=candidate,
    )
    retained: dict[str, bytes] = {}
    observations: list[dict[str, object]] = []
    def denied(_path: Path, _gate_path: Path, _ledger_path: Path, _timeout: float):
        return _completed(
            ["odylith", "greenfield", "propose"],
            stdout=json.dumps({"mode": "error", "error": "invalid candidate"}),
            returncode=2,
        )

    flow = host_module.HostCandidateFlow(
        **{
            **flow.__dict__,
            "invoke_propose": denied,
            "observe": observations.append,
            "retain_candidate_bytes": lambda value: retained.setdefault("candidate", value),
            "retain_proposal_bytes": lambda stream, value: retained.setdefault(stream, value),
        }
    )
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    with pytest.raises(
        host_module.HostCandidateFlowError,
        match="proposal command returned nonzero",
    ) as raised:
        host_module.run_host_candidate_flow(flow)

    assert proposal_paths == []
    assert retained["candidate"] == json.dumps(candidate).encode("utf-8")
    assert json.loads(retained["stdout"]) == {
        "mode": "error",
        "error": "invalid candidate",
    }
    assert retained["stderr"] == b""
    observation = flow.observation_sink
    assert observation["host_output_sha256"] == hashlib.sha256(retained["candidate"]).hexdigest()
    assert observation["proposal_returncode"] == 2
    assert observation["proposal_mode"] == "error"
    assert observation["runtime_semantic_model_call_count"] == 0
    assert observation["post_receipt_provider_invocations"] == 0
    assert observation["candidate_temp_cleaned"] is True
    diagnostic = str(raised.value)
    assert "invalid candidate" not in diagnostic


@pytest.mark.parametrize(
    ("host_behavior", "expected_fragment"),
    (
        ("unavailable", "failed closed"),
        ("timeout", "failed closed"),
        ("nonzero", "nonzero"),
        ("malformed", "JSON"),
    ),
)
def test_host_candidate_failures_are_fail_closed_and_do_not_propose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host_behavior: str,
    expected_fragment: str,
) -> None:
    flow, _host_run, _installed, host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate={"version": "candidate"},
    )
    proposal_calls: list[Path] = []
    flow = host_module.HostCandidateFlow(
        **{**flow.__dict__, "invoke_propose": lambda path, _gate_path, _ledger_path, _timeout: proposal_calls.append(path)},
    )

    def host_run(command, **kwargs):
        if host_behavior == "unavailable":
            raise FileNotFoundError("host-author")
        if host_behavior == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if host_behavior == "nonzero":
            return _completed(list(command), returncode=7, stderr="host rejected candidate")
        return _completed(list(command), stdout="not JSON")

    monkeypatch.setattr(host_module, "_invoke_host", host_run)
    with pytest.raises(host_module.HostCandidateFlowError) as raised:
        host_module.run_host_candidate_flow(flow)

    assert expected_fragment.casefold() in str(raised.value).casefold()
    assert len(host_calls) == 0
    assert proposal_calls == []
    assert proposal_paths == []


def test_malformed_host_output_is_retained_before_parse_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, original_host_run, _installed, _host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate={"version": "candidate"},
    )
    retained: list[bytes] = []
    malformed = b'{"first": true}\n{"second": true}\n'

    def host_run(command, **_kwargs):
        schema_path = Path(command[command.index("--output-schema") + 1])
        if schema_path.name == "authority-gate-schema.json":
            return original_host_run(command, **_kwargs)
        if schema_path.name == "source-ledger-schema.json":
            return _completed(list(command), stdout=json.dumps(_fixture_host_ledger()))
        if schema_path.name == "source-duty-decision-schema.json":
            return original_host_run(command, **_kwargs)
        return _completed(list(command), stdout=malformed.decode("utf-8"))

    flow = host_module.HostCandidateFlow(
        **{**flow.__dict__, "retain_candidate_bytes": retained.append}
    )
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    with pytest.raises(host_module.HostCandidateFlowError, match="failed closed") as raised:
        host_module.run_host_candidate_flow(flow)

    assert retained == [malformed]
    assert "candidate" not in raised.value.observation


def test_contract_command_failure_stops_before_host_invocation(tmp_path: Path) -> None:
    flow, _host_run, _installed, _host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate={"version": "candidate"},
    )
    installed_calls: list[list[str]] = []

    def failed_contract(command, _timeout):
        installed_calls.append(list(command))
        return _completed(list(command), returncode=2, stderr="contract unavailable")

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "invoke_installed": failed_contract})
    with pytest.raises(host_module.HostCandidateFlowError, match="contract command failed"):
        host_module.run_host_candidate_flow(flow)
    assert len(installed_calls) == 1


def test_host_timeout_budget_includes_contract_and_host_work(tmp_path: Path, monkeypatch) -> None:
    flow, host_run, installed_calls, host_calls, _proposal_paths, _repo = _flow(
        tmp_path,
        contract={},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    monkeypatch.setattr(host_module, "_invoke_host", host_run)

    original_installed = flow.invoke_installed

    def slow_contract(command, timeout):
        if "candidate-contract" in command:
            time.sleep(0.02)
        return original_installed(command, timeout)

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "invoke_installed": slow_contract})
    host_module.run_host_candidate_flow(flow)

    assert host_calls[0][2] < installed_calls[0][1]
    assert host_calls[0][2] > 0


def test_gate_and_candidate_share_pinned_model_window_with_operational_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"version": "candidate", "result": {"status": "authored"}}
    flow, host_run, _installed_calls, host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={}, candidate=candidate,
    )
    clock = [0.0]
    proposal_timeouts: list[float] = []
    observations: list[dict[str, object]] = []
    original_installed = flow.invoke_installed
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1])
        clock[0] += 100.0 if schema.name == "authority-gate-schema.json" else 10.0
        return result

    def timed_installed(command, timeout):
        result = original_installed(command, timeout)
        if "authority-check" in command:
            clock[0] += 20.0
        return result

    original_propose = flow.invoke_propose

    def timed_propose(candidate_path, gate_path, ledger_path, timeout):
        proposal_timeouts.append(timeout)
        return original_propose(candidate_path, gate_path, ledger_path, timeout)

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 315.0, "invoke_installed": timed_installed,
        "invoke_propose": timed_propose, "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", timed_host)

    assert host_module.run_host_candidate_flow(flow).returncode == 0
    assert [call[2] for call in host_calls] == [300.0, 300.0, 120.0, 180.0]
    assert proposal_timeouts == [185.0]
    assert flow.observation_sink["model_window_seconds"] == 300.0
    assert flow.observation_sink["operational_timeout_seconds"] == 315.0


def test_expired_shared_model_window_cannot_borrow_operational_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"version": "candidate", "result": {"status": "authored"}}
    flow, host_run, _installed, host_calls, proposal_paths, repo = _flow(
        tmp_path, contract={}, candidate=candidate,
    )
    clock = [0.0]
    observations: list[dict[str, object]] = []
    original_installed = flow.invoke_installed
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        clock[0] += 295.0
        return result

    def timed_installed(command, timeout):
        result = original_installed(command, timeout)
        if "authority-check" in command:
            clock[0] += 5.0
        return result

    flow = host_module.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 315.0, "invoke_installed": timed_installed,
        "observe": observations.append,
    })
    monkeypatch.setattr(host_module, "_invoke_host", timed_host)

    with pytest.raises(host_module.HostCandidateFlowError, match="failed closed"):
        host_module.run_host_candidate_flow(flow)

    assert len(host_calls) == 1
    assert host_calls[0][2] == 300.0
    assert proposal_paths == []
    assert list(repo.iterdir()) == []
    assert flow.observation_sink["stage"] == "authority-check"
    assert flow.observation_sink["source_ledger_host_invocations"] == 0
    assert flow.observation_sink["candidate_host_invocations"] == 0
    assert flow.observation_sink["proposal_command_invocations"] == 0
    assert flow.observation_sink["candidate_temp_cleaned"] is True
    assert flow.observation_sink["authority_gate_temp_cleaned"] is True


def test_propose_arguments_wire_exact_candidate_file_without_changing_legacy_default() -> None:
    legacy = matrix_module._greenfield_propose_arguments(prompt="Build it.")
    host = matrix_module._greenfield_propose_arguments(
        prompt="Build it.", candidate_file="/tmp/candidate.json",
        gate_file="/tmp/gate.json", ledger_file="/tmp/ledger.json",
    )

    assert "--candidate-file" not in legacy
    assert host[-6:] == [
        "--candidate-file", "/tmp/candidate.json",
        "--gate-file", "/tmp/gate.json",
        "--ledger-file", "/tmp/ledger.json",
    ]


def test_matrix_host_candidate_argv_is_explicit_and_repeatable(tmp_path: Path) -> None:
    args = matrix_module._parse_args(
        [
            "--dist-dir",
            str(tmp_path),
            "--host-candidate-arg",
            "host-author",
            "--host-candidate-arg=--json",
        ]
    )

    assert args.host_candidate_arg == ["host-author", "--json"]


def test_canonical_host_candidate_argv_template_is_the_exact_release_grammar() -> None:
    assert transport_module.canonical_host_candidate_argv_template() == (
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        "{model}",
        "--config",
        "model_reasoning_effort={reasoning_effort}",
        "--output-schema",
        "{candidate_schema}",
        "-",
    )
    assert transport_module.HOST_NATIVE_ARGV_ARGUMENT_COUNT == 14


@pytest.mark.parametrize("verdict", ["no", "uncertain", None, "over-bound"])
def test_checker_refusal_retains_exact_reason_and_untrusted_omission_without_new_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verdict: str | None,
) -> None:
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction

    flow, original_host, _installed, host_calls, proposals, repo = _flow(
        tmp_path, contract={}, candidate={},
    )
    old = pending.stage_pending_transaction(repo_root=repo, transaction=_transaction(repo))
    before = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in repo.rglob("*") if p.is_file()}
    omission = {"omission_id": "controlled-missing-proof", "typed_role": "proof_duty",
                "source_ref": {"quote": "A reviewer creates a reviewable plan.",
                               "context": "A reviewer creates a reviewable plan."}}
    if verdict == "over-bound":
        omission["source_ref"] = {"quote": "q" * 801, "context": "c" * 801}
    original_installed = flow.invoke_installed
    checker_output = []

    def verifier(command, **kwargs):
        result = original_host(command, **kwargs)
        if Path(command[command.index("--output-schema") + 1]).name != "source-duty-decision-schema.json":
            return result
        decision = json.loads(result.stdout)
        if verdict is None:
            decision.pop("source_completeness")
        else:
            decision["source_completeness"] = {"verdict": "no" if verdict == "over-bound" else verdict,
                                               "omissions": [omission]}
        return _completed(list(command), stdout=json.dumps(decision))

    def checker(command, timeout):
        if "source-ledger-check" not in command or "--decision-file" not in command:
            return original_installed(command, timeout)
        ledger = json.loads(Path(command[command.index("--ledger-file") + 1]).read_bytes())
        decision = json.loads(Path(command[command.index("--decision-file") + 1]).read_bytes())
        with pytest.raises(ValueError) as refused:
            validate_greenfield_source_duty_ledger(
                expand_compact_source_duty_ledger(ledger, evidence_text=flow.prompt),
                evidence_text=flow.prompt, decision_set=decision,
            )
        checker_output.append(json.dumps({"mode": "error", "error": str(refused.value)}))
        return _completed(list(command), stdout=checker_output[-1], returncode=2)

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "invoke_installed": checker})
    monkeypatch.setattr(host_module, "_invoke_host", verifier)
    with pytest.raises(host_module.HostCandidateFlowError) as failure:
        host_module.run_host_candidate_flow(flow)
    observed = failure.value.observation
    assert observed["detail"] == checker_output[0][:800]
    assert observed["source_ledger_check_stdout_sha256"] == hashlib.sha256(checker_output[0].encode()).hexdigest()
    if verdict is None:
        assert "decision set is malformed" in observed["detail"]
        assert "source_completeness_diagnostic" not in observed
    else:
        assert ("invalid source citation" in observed["detail"] if verdict == "over-bound" else
                "source completeness is not affirmative" in observed["detail"])
        diagnostic = observed["source_completeness_diagnostic"]
        assert diagnostic["origin"] == "untrusted_verifier_report" and diagnostic["authority"] == "none"
        assert diagnostic["selection"] == "first_omission"
        if verdict == "over-bound":
            assert diagnostic["omission"] == {**omission, "source_ref": {}}
            assert diagnostic["omitted_fields"] == ["source_ref.quote", "source_ref.context"]
        else:
            assert diagnostic["omission"] == omission and diagnostic["omitted_fields"] == []
    assert observed["source_completeness_verdict"] == (
        "missing" if verdict is None else "no" if verdict == "over-bound" else verdict)
    assert len(host_calls) == 3 and proposals == []
    assert observed["candidate_host_invocations"] == observed["proposal_command_invocations"] == 0
    assert observed["source_duty_decision_temp_cleaned"] and observed["host_workspace_cleaned"]
    assert flow.completion_receipt_sink == {} and old.is_file()
    assert {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in repo.rglob("*") if p.is_file()} == before
