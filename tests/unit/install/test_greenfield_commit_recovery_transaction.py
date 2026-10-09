"""Recovery compilation traverses the real driver and accepted source receipt."""

import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import greenfield_commit_recovery_transaction as recovery
from greenfield_matrix_release_artifacts import begin_retained_case_evidence
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import whole_journey_observation_issues
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import verify_greenfield_source_duty_ledger_receipt
from odylith.runtime.domain_intelligence import greenfield_host_flow as host_module
from odylith.runtime.domain_intelligence.greenfield_authority_gate import greenfield_authority_gate_contract
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
from tests.unit.install.test_greenfield_commit_recovery_proof import _module, HOST_CANDIDATE_ARGV


@pytest.mark.parametrize("tampered_receipt", [False, True])
def test_recovery_caller_uses_real_driver_budget_fresh_ledger_and_final_proof(
    tmp_path, monkeypatch, tampered_receipt,
):
    prompt = "First Complete Path: A reviewer creates a reviewable plan. Reference: Notes are background only."
    source = recovery.combined_prompt_evidence_source(prompt=prompt, edit_evidence="")
    flow, host_run, installed_calls, host_calls, _proposals, repo = _flow(
        tmp_path,
        candidate={"version": "candidate", "result": {"status": "authored"}},
        contract={"request": {"evidence": source}, "authority_gate": greenfield_authority_gate_contract(
            prompt=prompt, edit_evidence="", evidence_source=source,
        )},
    )
    (tmp_path / "retained").mkdir()
    evidence = begin_retained_case_evidence(evidence_root=tmp_path / "retained", case_id="proposal")
    now = [0.0]
    captured = {}
    raw_receipts = []
    original_record_bytes = recovery.recovery_evidence.record_retained_case_bytes
    real_flow = recovery.run_host_candidate_flow
    monkeypatch.setattr(host_module.time, "monotonic", lambda: now[0])

    def capture_actual_flow(current):
        captured["flow"] = current
        return real_flow(current)

    def timed_host(command, **kwargs):
        result = host_run(command, **kwargs)
        schema = Path(command[command.index("--output-schema") + 1]).name
        now[0] += {"authority-gate-schema.json": 2.0, "source-ledger-schema.json": 3.0,
                   "source-duty-decision-schema.json": 4.0, "candidate-schema.json": 5.0}[schema]
        return result

    def retain_bytes(case, name, value):
        if name == "semantic/host-source-ledger-check.raw.v1.json":
            raw_receipts.append(json.loads(value)["receipt"])
            now[0] += 7.0
        elif name == "semantic/product-create-transaction.v1.json":
            now[0] += 8.0
        return original_record_bytes(case, name, value)

    def runner(*, cwd, env, command, timeout):
        assert cwd == repo
        if "propose" not in command:
            result = flow.invoke_installed(command, timeout)
            if tampered_receipt and "--decision-file" in command:
                payload = json.loads(result.stdout)
                payload["receipt"]["source_sha256"] = "0" * 64
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")
            return result
        assert not tampered_receipt
        ledger_path = Path(command[command.index("--ledger-file") + 1])
        candidate_path = Path(command[command.index("--candidate-file") + 1])
        gate_path = Path(command[command.index("--gate-file") + 1])
        assert candidate_path.is_file() and gate_path.is_file() and ledger_path.is_file()
        receipt = json.loads(ledger_path.read_text())
        assert receipt == raw_receipts[-1]
        assert verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source) == receipt
        assert receipt["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
        assert env["ODYLITH_REASONING_CODEX_BIN"] == "/usr/bin/false"
        captured.update(proposal_command=command, proposal_timeout=timeout, ledger_path=ledger_path)
        transaction = repo / "sealed.json"
        transaction.write_text(json.dumps({
            "transaction_hash": "a" * 64,
            "intent_authority": {"source_format": "operator_prompt", "product_facts_sha256": "c" * 64,
                                 "markdown_source_sha256": hashlib.sha256(source.encode()).hexdigest()},
            "prewrite_package": {"repository_write_set": {"write_set_hash": "b" * 64}},
        }))
        now[0] += 6.0
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
            "mode": "product_create_transaction",
            "product_create_transaction": {"transaction_hash": "a" * 64, "product_facts_sha256": "c" * 64},
            "transaction_file": str(transaction),
        }), stderr="")

    monkeypatch.setattr(recovery, "run_host_candidate_flow", capture_actual_flow)
    monkeypatch.setattr(recovery, "_run", runner)
    monkeypatch.setattr(host_module, "_invoke_host", timed_host)
    monkeypatch.setattr(recovery, "resolve_trusted_codex_executable", lambda **_kwargs: flow.trusted_codex_executable)
    monkeypatch.setattr(recovery.recovery_evidence, "record_retained_case_bytes", retain_bytes)
    env = {**flow.env, "ODYLITH_GREENFIELD_MODEL_PROFILE": STANDARD_PROFILE_ID,
           "ODYLITH_REASONING_MODEL": "gpt-6-astra", "ODYLITH_REASONING_CODEX_REASONING_EFFORT": "medium"}
    arguments = dict(repo_root=repo, env=env,
                     case=recovery.GreenfieldMatrixCase(name="recovery", prompt=prompt, required_terms=()),
                     evidence=evidence, host_candidate_argv=flow.host_argv)
    if tampered_receipt:
        with pytest.raises(host_module.HostCandidateFlowError, match="did not admit"):
            recovery.compile_transaction(**arguments)
    else:
        assert recovery.compile_transaction(**arguments).transaction_hash == "a" * 64

    stage = json.loads((evidence.staging_root / "semantic/host-authoring-observation.v1.json").read_text())
    assert stage == captured["flow"].observation_sink
    assert captured["flow"].observe is None
    assert recovery.COMMAND_TIMEOUT_SECONDS == captured["flow"].timeout == 315.0
    assert installed_calls[0][1] == 315.0
    assert stage["model_window_seconds"] == 300.0
    assert stage["operational_timeout_seconds"] == 315.0
    assert stage["host_workspace_cleaned"] is True
    assert stage["source_ledger_temp_cleaned"] is True
    if tampered_receipt:
        assert len(host_calls) == 3
        assert stage["status"] == "failed"
        assert "proposal_command" not in captured
    else:
        assert [call[2] for call in host_calls] == [300.0, 300.0, 120.0, 298.0]
        assert captured["proposal_timeout"] == 308.0
        assert not captured["ledger_path"].exists()
        assert stage["whole_journey_seconds"] == 35.0
        assert stage["proposal_phase_elapsed_seconds"] == 21.0
        assert stage["source_duty_verifier_elapsed_seconds"] == 11.0
        assert not whole_journey_observation_issues(stage)


def test_compile_transaction_uses_the_exact_case_prompt_and_confirmed_intent(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path = tmp_path / transaction_file
    transaction_path.parent.mkdir(parents=True)
    transaction_path.write_text(
        json.dumps(
            {
                "transaction_hash": "a" * 64,
                "intent_authority": {
                    "source_format": "operator_prompt_with_edit_evidence",
                    "product_facts_sha256": "c" * 64,
                    "markdown_source_sha256": module.hashlib.sha256(
                        module.recovery_transaction.combined_prompt_evidence_source(
                            prompt="Create the exact recovery-bound product.",
                            edit_evidence="# Confirmed Recovery Intent\n\n## State\nA durable record.",
                        ).encode("utf-8")
                    ).hexdigest(),
                },
                "prewrite_package": {"repository_write_set": {"write_set_hash": "b" * 64}},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        module.recovery_transaction,
        "_run",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "product_create_transaction": {
                        "transaction_hash": "a" * 64,
                        "product_facts_sha256": "c" * 64,
                    },
                    "transaction_file": transaction_file,
                }
            ),
            stderr="",
        ),
    )
    monkeypatch.setattr(
        module.recovery_transaction,
        "resolve_trusted_codex_executable",
        lambda **_kwargs: "/trusted/codex",
    )
    monkeypatch.setattr(
        module.recovery_transaction,
        "run_host_candidate_flow",
        lambda flow: flow.invoke_propose(
            tmp_path.parent / "candidate.json",
            tmp_path.parent / "authority-gate.json",
            tmp_path.parent / "source-duty-receipt.json",
            123.0,
        ),
    )
    case = module.GreenfieldMatrixCase(
        name="bound recovery case",
        prompt="Create the exact recovery-bound product.",
        required_terms=("recovery",),
        confirmed_intent_markdown="# Confirmed Recovery Intent\n\n## State\nA durable record.",
    )

    compiled = module.recovery_transaction.compile_transaction(
        repo_root=tmp_path,
        env={"PATH": "/usr/bin"},
        case=case,
        host_candidate_argv=HOST_CANDIDATE_ARGV,
    )
    assert compiled.transaction_hash == "a" * 64
    assert compiled.product_facts_hash == "c" * 64
    command = captured["command"]
    assert command[command.index("--prompt") + 1] == case.prompt
    assert command[command.index("--edit") + 1] == case.confirmed_intent_markdown
    assert command[command.index("--gate-file") + 1] == str(tmp_path.parent / "authority-gate.json")


def test_compile_transaction_uses_host_native_candidate_when_configured(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path = tmp_path / transaction_file
    transaction_path.parent.mkdir(parents=True)
    case = module.GreenfieldMatrixCase(
        name="host-native recovery case",
        prompt="Create the exact host-native recovery product.",
        required_terms=("recovery",),
    )
    source_hash = module.hashlib.sha256(
        module.recovery_transaction.combined_prompt_evidence_source(
            prompt=case.prompt,
            edit_evidence="",
        ).encode("utf-8")
    ).hexdigest()
    transaction_path.write_text(
        json.dumps(
            {
                "transaction_hash": "a" * 64,
                "intent_authority": {
                    "source_format": "operator_prompt",
                    "product_facts_sha256": "c" * 64,
                    "markdown_source_sha256": source_hash,
                },
                "prewrite_package": {
                    "repository_write_set": {"write_set_hash": "b" * 64}
                },
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_host_flow(flow):  # noqa: ANN001
        captured["flow"] = flow
        candidate_path = tmp_path.parent / "candidate.json"
        candidate_path.write_text("{}\n", encoding="utf-8")
        return flow.invoke_propose(candidate_path, tmp_path.parent / "authority-gate.json",
                                   tmp_path.parent / "source-duty-receipt.json", 123.0)

    def fake_run(**kwargs):  # noqa: ANN003
        captured["command"] = kwargs["command"]
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "product_create_transaction": {
                        "transaction_hash": "a" * 64,
                        "product_facts_sha256": "c" * 64,
                    },
                    "transaction_file": transaction_file,
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(module.recovery_transaction, "run_host_candidate_flow", fake_host_flow)
    monkeypatch.setattr(
        module.recovery_transaction,
        "resolve_trusted_codex_executable",
        lambda **_kwargs: "/trusted/codex",
    )
    monkeypatch.setattr(module.recovery_transaction, "_run", fake_run)

    compiled = module.recovery_transaction.compile_transaction(
        repo_root=tmp_path,
        env={"PATH": "/usr/bin"},
        case=case,
        host_candidate_argv=(
            "/trusted/codex", "exec", "--ephemeral", "--ignore-user-config",
            "--skip-git-repo-check", "--sandbox", "read-only",
            "--model", "gpt-6-astra", "--config",
            "model_reasoning_effort=medium", "--output-schema",
            "{candidate_schema}", "-",
        ),
    )

    assert compiled.transaction_hash == "a" * 64
    flow = captured["flow"]
    assert flow.host_argv == (
        "/trusted/codex", "exec", "--ephemeral", "--ignore-user-config",
        "--skip-git-repo-check", "--sandbox", "read-only",
        "--model", "gpt-6-astra", "--config",
        "model_reasoning_effort=medium", "--output-schema",
        "{candidate_schema}", "-",
    )
    command = captured["command"]
    assert command[command.index("--candidate-file") + 1] == str(tmp_path.parent / "candidate.json")
    assert command[command.index("--gate-file") + 1] == str(tmp_path.parent / "authority-gate.json")


def test_compile_transaction_rejects_an_authority_that_does_not_bind_edit_evidence(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    transaction_file = ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    transaction_path = tmp_path / transaction_file
    transaction_path.parent.mkdir(parents=True)
    transaction_path.write_text(
        json.dumps(
            {
                "transaction_hash": "a" * 64,
                "intent_authority": {
                    "source_format": "operator_prompt_with_edit_evidence",
                    "product_facts_sha256": "c" * 64,
                    "markdown_source_sha256": "f" * 64,
                },
                "prewrite_package": {"repository_write_set": {"write_set_hash": "b" * 64}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module.recovery_transaction,
        "_run",
        lambda **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "product_create_transaction": {
                        "transaction_hash": "a" * 64,
                        "product_facts_sha256": "c" * 64,
                    },
                    "transaction_file": transaction_file,
                }
            ),
            stderr="",
        ),
    )
    monkeypatch.setattr(
        module.recovery_transaction,
        "resolve_trusted_codex_executable",
        lambda **_kwargs: "/trusted/codex",
    )
    monkeypatch.setattr(
        module.recovery_transaction,
        "run_host_candidate_flow",
        lambda flow: flow.invoke_propose(
            tmp_path.parent / "candidate.json",
            tmp_path.parent / "authority-gate.json",
            tmp_path.parent / "source-duty-receipt.json",
            123.0,
        ),
    )
    case = module.GreenfieldMatrixCase(
        name="bound recovery case",
        prompt="Create the exact recovery-bound product.",
        required_terms=("recovery",),
        confirmed_intent_markdown="# Confirmed Recovery Intent\n\n## State\nA durable record.",
    )

    try:
        module.recovery_transaction.compile_transaction(
            repo_root=tmp_path,
            env={"PATH": "/usr/bin"},
            case=case,
            host_candidate_argv=HOST_CANDIDATE_ARGV,
        )
    except RuntimeError as exc:
        assert "did not bind the exact prompt and edit evidence" in str(exc)
    else:
        raise AssertionError("unbound edit evidence should fail installed recovery compilation")
