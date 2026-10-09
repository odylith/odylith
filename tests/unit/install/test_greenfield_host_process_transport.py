"""Real stdin, process-group cleanup, and failed host-stream custody."""

import contextlib
import json
import hashlib
import os
from pathlib import Path
import signal
import sys
import time

import pytest

from odylith.runtime.domain_intelligence import greenfield_host_flow as host
from odylith.runtime.domain_intelligence.greenfield_process import command_lifecycle_observer, run_command_with_group_timeout
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow


PROCESS_TREE = '''import json, os, signal, subprocess, sys, time
ready_path = os.environ.get("ODYLITH_TEST_PROCESS_READY")
if not ready_path:
    sys.stdin.buffer.read()
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
print(json.dumps({"parent": os.getpid(), "child": child.pid}), flush=True)
print("private partial stdout", flush=True)
print("private provider stderr", file=sys.stderr, flush=True)
def stop(signum, frame):
    child.terminate()
    child.wait(timeout=3)
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
if ready_path:
    with open(ready_path, "x") as marker:
        marker.write("process tree and output ready")
    sys.stdin.buffer.read()
time.sleep(60)
'''


def _assert_tree_gone(output):
    pids = json.loads(output.splitlines()[0])
    for pid in pids.values():
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def _cleanup_tree(output):
    if not output:
        return
    with contextlib.suppress(ValueError, json.JSONDecodeError):
        for pid in json.loads(output.splitlines()[0]).values():
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)


def test_shared_group_runner_supplies_exact_stdin_bytes(tmp_path):
    text = "private ∆ source\r\nsecond line\n"
    result = run_command_with_group_timeout(
        cwd=tmp_path, env=os.environ, timeout=5,
        command=[sys.executable, "-c", "import sys; print(sys.stdin.buffer.read().hex(), end='')"],
        stdin_text=text,
    )
    assert result.returncode == 0
    assert bytes.fromhex(result.stdout) == text.encode("utf-8")


def test_shared_group_timeout_terminates_parent_and_descendant_with_partial_streams(tmp_path):
    result = run_command_with_group_timeout(
        cwd=tmp_path, env=os.environ, timeout=0.5,
        command=[sys.executable, "-c", PROCESS_TREE], stdin_text="exact input",
    )
    try:
        assert result.returncode == 124
        assert "private partial stdout" in result.stdout
        assert "private provider stderr" in result.stderr
        assert result.termination_observation == "output_pipes_closed_after_sigterm"
        _assert_tree_gone(result.stdout)
    finally:
        _cleanup_tree(result.stdout)


def test_real_gate_timeout_retains_streams_and_failed_sink_before_any_later_stage(tmp_path):
    flow, _host_stub, installed, _hosts, proposals, repo = _flow(
        tmp_path, contract={}, candidate={},
    )
    executable = Path(flow.trusted_codex_executable)
    executable.write_text(f"#!{sys.executable}\n" + PROCESS_TREE)
    stdout, stderr = [], []
    ready_path = tmp_path / "gate-output-ready"
    flow = host.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 0.5, "retain_authority_gate_bytes": stdout.append,
        "env": {**flow.env, "ODYLITH_TEST_PROCESS_READY": str(ready_path)},
        "retain_host_stderr_bytes": lambda stage, value: stderr.append((stage, value)),
    })

    def observe_start(event):
        if event["state"] != "started":
            return
        # Establish partial-output custody before the unchanged communicate timeout.
        # Startup remains measured; this cleanup test does not prove flow latency.
        deadline = time.monotonic() + 5.0
        while not ready_path.is_file():
            if time.monotonic() >= deadline:
                raise AssertionError("gate stub did not establish output custody")
            time.sleep(0.005)

    try:
        with command_lifecycle_observer(observe_start), pytest.raises(host.HostCandidateFlowError, match="gate command returned nonzero") as caught:
            host.run_host_candidate_flow(flow)
        _assert_tree_gone(stdout[0].decode())
        assert len(installed) == 1 and proposals == []
        assert "private partial stdout" in stdout[0].decode()
        assert stderr[0][0] == "authority-gate"
        assert "private provider stderr" in stderr[0][1].decode()
        stage = flow.observation_sink
        assert stage["status"] == "failed"
        assert stage["authority_gate_returncode"] == 124
        assert stage["host_invocations"] == 1
        assert stage["source_ledger_host_invocations"] == 0
        assert stage["source_duty_verifier_host_invocations"] == 0
        assert stage["candidate_host_invocations"] == 0
        assert stage["proposal_command_invocations"] == 0
        assert stage["host_workspace_cleaned"] is True
        assert stage["candidate_temp_cleaned"] is True
        assert stage["authority_gate_temp_cleaned"] is True
        assert list(repo.iterdir()) == []
        diagnostic = stage["host_command_diagnostic"]
        assert diagnostic == {
            "stage": "authority-gate", "returncode": 124,
            "stdout_bytes": len(stdout[0]), "stderr_bytes": len(stderr[0][1]),
            "stderr_sha256": hashlib.sha256(stderr[0][1]).hexdigest(),
            "stderr_retention_status": "within_bound",
            "termination_observation": "output_pipes_closed_after_sigterm",
        }
        assert "private" not in json.dumps(stage)
        assert "private" not in str(caught.value)
    finally:
        _cleanup_tree(stdout[0].decode() if stdout else "")


def test_oversized_stderr_fails_closed_with_full_hash_and_no_clipping(tmp_path, monkeypatch):
    flow, _host_stub, installed, _hosts, proposals, _repo = _flow(
        tmp_path, contract={}, candidate={},
    )
    import subprocess
    raw_stderr = "x" * (256 * 1024 + 1)
    partial, diagnostic = [], []
    monkeypatch.setattr(host, "_invoke_host", lambda command, **kwargs:
        subprocess.CompletedProcess(command, 124, stdout="partial", stderr=raw_stderr))
    flow = host.HostCandidateFlow(**{
        **flow.__dict__, "retain_authority_gate_bytes": partial.append,
        "retain_host_stderr_bytes": lambda stage, value: diagnostic.append(value),
    })
    with pytest.raises(host.HostCandidateFlowError, match="failed closed"):
        host.run_host_candidate_flow(flow)
    proof = flow.observation_sink["host_command_diagnostic"]
    assert proof["stderr_bytes"] == len(raw_stderr)
    assert proof["stderr_sha256"] == hashlib.sha256(raw_stderr.encode()).hexdigest()
    assert proof["stderr_retention_status"] == "rejected_over_bound"
    assert partial == [b"partial"] and diagnostic == []
    assert len(installed) == 1 and proposals == []
    assert flow.observation_sink["status"] == "failed"


@pytest.mark.parametrize("caller", ["matrix", "recovery"])
def test_callers_retain_private_gate_streams_and_authoritative_failed_snapshot(tmp_path, monkeypatch, caller):
    import greenfield_preconfirm_matrix as matrix
    import greenfield_commit_recovery_transaction as recovery
    from greenfield_matrix_release_artifacts import begin_retained_case_evidence
    from odylith.runtime.domain_intelligence.greenfield_process import GroupTimeoutCompletedProcess
    flow, _host_stub, installed, _hosts, proposals, repo = _flow(
        tmp_path, contract={}, candidate={},
    )
    root = tmp_path / "retained"
    root.mkdir(mode=0o700)
    evidence = begin_retained_case_evidence(evidence_root=root, case_id="failed-gate")
    external_diagnostics = {}
    monkeypatch.setattr(host, "_invoke_host", lambda command, **kwargs: GroupTimeoutCompletedProcess(
        list(command), 124, stdout="private partial stdout", stderr="private stderr",
        termination_observation="output_pipes_closed_after_sigterm",
    ))
    runner = lambda **kw: flow.invoke_installed(kw["command"], kw["timeout"])
    env = {**flow.env, "ODYLITH_REASONING_MODEL": "gpt-6-astra",
           "ODYLITH_REASONING_CODEX_REASONING_EFFORT": "medium"}
    with pytest.raises(host.HostCandidateFlowError, match="gate command returned nonzero") as caught:
        if caller == "matrix":
            monkeypatch.setattr(matrix, "_run", runner)
            matrix._run_host_candidate_propose(
                repo_root=repo, env=env, prompt=flow.prompt, edit_evidence=flow.edit_evidence,
                repair_tier="standard", timeout=315.0, host_candidate_argv=flow.host_argv,
                retained_case=evidence,
                retain_diagnostic_bytes=lambda stage, value: external_diagnostics.update({stage: value}),
            )
        else:
            monkeypatch.setattr(recovery, "_run", runner)
            recovery.compile_transaction(
                repo_root=repo, env=env, evidence=evidence, host_candidate_argv=flow.host_argv,
                case=recovery.GreenfieldMatrixCase(name="failure", prompt=flow.prompt, required_terms=(),
                                                  confirmed_intent_markdown=flow.edit_evidence),
            )
    stdout_path = evidence.staging_root / "semantic/host-authority-gate.raw.v1.json"
    stderr_path = evidence.staging_root / "semantic/host-authority-gate.stderr.raw.v1"
    assert stdout_path.read_bytes() == b"private partial stdout"
    assert stderr_path.read_bytes() == b"private stderr"
    assert stderr_path.stat().st_mode & 0o777 == 0o600
    assert evidence.staging_root.stat().st_mode & 0o777 == 0o700
    assert not stderr_path.is_relative_to(repo)
    stage = json.loads((evidence.staging_root / "semantic/host-authoring-observation.v1.json").read_text())
    assert stage["status"] == "failed" and stage["host_workspace_cleaned"] is True
    assert stage["authority_gate_returncode"] == 124
    assert stage["host_invocations"] == 1 and stage["candidate_host_invocations"] == 0
    assert len(installed) == 1 and proposals == []
    assert "private" not in str(caught.value)
    assert "private" not in json.dumps(stage)
    if caller == "matrix":
        assert external_diagnostics["authority-gate-stderr"] == b"private stderr"


@pytest.mark.parametrize("phase,returncode", [
    (phase, code) for phase in ("authority-gate", "source-ledger", "source-duty-verifier", "candidate")
    for code in (0, 7)
] + [("authority-gate", 124)])
def test_real_terminal_lifecycle_failure_preserves_primary_result_and_stream_custody(
    tmp_path, phase, returncode,
):
    from odylith.runtime.domain_intelligence.greenfield_process import command_lifecycle_observer
    from tests.unit.install.test_greenfield_matrix_host_candidate import _fixture_host_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import expand_compact_source_duty_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import source_duty_entailment_task, SOURCE_DUTY_DECISION_SET_VERSION
    flow, _host_stub, installed, _hosts, proposals, repo = _flow(
        tmp_path, contract={}, candidate={},
    )
    compact = _fixture_host_ledger()
    expanded = expand_compact_source_duty_ledger(compact, evidence_text=flow.prompt)
    preflight = preflight_greenfield_source_duty_ledger(expanded, evidence_text=flow.prompt)
    task = source_duty_entailment_task(preflight, evidence_text=flow.prompt)
    payloads = {
        "authority-gate-schema.json": {"decision": "admit", "required_fields": [],
            "owner_quote": "reviewer", "task_quote": "creates a reviewable plan",
            "result_quote": "a reviewable plan", "question": ""},
        "source-ledger-schema.json": compact,
        "source-duty-decision-schema.json": {"version": SOURCE_DUTY_DECISION_SET_VERSION,
            "verifier_task_sha256": task["verifier_task_sha256"],
            "product_identity": {"verdict": "yes"},
            "decisions": {"d1": {"verdict": "yes", "support_ref_indexes": [0], "role_ref_indexes": [0, 1]}},
            "source_completeness": {"verdict": "yes", "omissions": []}},
        "candidate-schema.json": {"version": "candidate", "result": {"status": "authored"}},
    }
    target = {"authority-gate": "authority-gate-schema.json", "source-ledger": "source-ledger-schema.json",
              "source-duty-verifier": "source-duty-decision-schema.json", "candidate": "candidate-schema.json"}[phase]
    output_ready = tmp_path / "terminal-host-output-ready"
    script = f'''import json, pathlib, sys, time
if {returncode} != 124:
    sys.stdin.buffer.read()
name = pathlib.Path(sys.argv[sys.argv.index("--output-schema") + 1]).name
payloads = json.loads({json.dumps(json.dumps(payloads))})
print(json.dumps(payloads[name]), flush=True)
print("private stderr " + name, file=sys.stderr, flush=True)
if name == {target!r}:
    if {returncode} == 124:
        with pathlib.Path({str(output_ready)!r}).open("x") as marker:
            marker.write("stdout and stderr flushed")
        sys.stdin.buffer.read()
        time.sleep(60)
    sys.exit({returncode})
'''
    Path(flow.trusted_codex_executable).write_text(f"#!{sys.executable}\n" + script)
    retained, diagnostic = {}, {}
    flow = host.HostCandidateFlow(**{
        **flow.__dict__, "timeout": 0.3 if returncode == 124 else 5.0,
        "retain_authority_gate_bytes": lambda value: retained.update({"authority-gate": value}),
        "retain_source_ledger_bytes": lambda value: retained.update({"source-ledger": value}),
        "retain_source_duty_decision_bytes": lambda value: retained.update({"source-duty-verifier": value}),
        "retain_candidate_bytes": lambda value: retained.update({"candidate": value}),
        "retain_host_stderr_bytes": lambda stage, value: diagnostic.update({stage: value}),
    })
    expected_calls = ["authority-gate", "source-ledger", "source-duty-verifier", "candidate"].index(phase) + 1
    terminals = []

    def failing_terminal_observer(event):
        if returncode == 124 and event["state"] == "started":
            # Establish output custody before the unchanged communicate timeout.
            # This startup wait is measured; this case does not prove flow latency.
            ready_deadline = time.monotonic() + 5.0
            while not output_ready.is_file():
                if time.monotonic() >= ready_deadline:
                    raise AssertionError("host stub did not flush output before readiness deadline")
                time.sleep(0.005)
        if event["state"] in {"completed", "timed_out"}:
            terminals.append(dict(event))
            if len(terminals) == expected_calls:
                raise OSError("private telemetry failure")

    match = "telemetry failed" if returncode == 0 else "returned nonzero"
    with command_lifecycle_observer(failing_terminal_observer), pytest.raises(host.HostCandidateFlowError, match=match) as caught:
        host.run_host_candidate_flow(flow)
    stage = flow.observation_sink
    field = {"authority-gate": "authority_gate_returncode", "source-ledger": "source_ledger_returncode",
             "source-duty-verifier": "source_duty_verifier_returncode", "candidate": "host_returncode"}[phase]
    assert stage[field] == returncode
    assert stage["status"] == "failed"
    assert stage["host_invocations"] == expected_calls
    assert stage["proposal_command_invocations"] == 0 and proposals == []
    assert len(terminals) == expected_calls
    assert json.loads(retained[phase]) == payloads[target]
    assert b"private stderr" in diagnostic[phase]
    proof = stage["host_command_diagnostic"]
    assert proof["returncode"] == returncode and proof["lifecycle_observer_error"] == "OSError"
    assert proof["termination_observation"] == ("output_pipes_closed_after_sigterm" if returncode == 124 else "not_requested")
    assert "private" not in str(caught.value) and "private" not in json.dumps(stage)
    if returncode:
        assert caught.value.__notes__ == ["Terminal command lifecycle telemetry also failed: OSError"]
        assert caught.value.__cause__.result.returncode == returncode
        assert caught.value.__cause__.result.stdout.encode() == retained[phase]
        assert caught.value.__cause__.result.stderr.encode() == diagnostic[phase]
        assert caught.value.__cause__.termination_observation == (
            "output_pipes_closed_after_sigterm" if returncode == 124 else None)
    else:
        assert caught.value.__cause__.result.returncode == 0
    assert stage["host_workspace_cleaned"] is True and list(repo.iterdir()) == []
