from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import pytest

from scripts.release import greenfield_matrix_host_candidate as host_module
from scripts.release import greenfield_preconfirm_matrix as matrix_module


def _completed(argv: list[str], *, stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


def _flow(tmp_path: Path, *, candidate: object, contract: object):
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
    contract_payload = dict(contract)
    contract_payload.setdefault("candidate_schema", {})
    contract_payload.setdefault("request", {"evidence": "Create a reviewable plan."})

    def installed(command, timeout):
        installed_calls.append((list(command), timeout))
        return _completed(list(command), stdout=json.dumps(contract_payload))

    def host_run(command, **kwargs):
        host_calls.append(
            (
                list(command),
                str(kwargs["input"]),
                float(kwargs["timeout"]),
                Path(kwargs["cwd"]),
            )
        )
        schema_path = Path(command[command.index("--output-schema") + 1])
        assert schema_path.is_file()
        assert schema_path.parent == Path(kwargs["cwd"])
        return _completed(list(command), stdout=json.dumps(candidate))

    def propose(path: Path, timeout: float):
        proposal_paths.append(path)
        assert path.is_file()
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
            prompt="Create a reviewable plan.",
            edit_evidence="Keep the source path.",
            timeout=5.0,
            env={
                "PATH": str(trusted_codex.parent),
                "ODYLITH_GREENFIELD_MODEL_PROFILE": "greenfield-standard-v1",
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
    contract_text = json.dumps({
        "version": "contract",
        "candidate_schema": {},
        "request": {"evidence": "Create a reviewable plan."},
    })
    flow, host_run, installed_calls, host_calls, proposal_paths, repo = _flow(
        tmp_path,
        contract=json.loads(contract_text),
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(host_module.subprocess, "run", host_run)
    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "observe": observations.append})

    result = host_module.run_host_candidate_flow(flow)

    assert result.returncode == 0
    assert len(installed_calls) == 1
    assert installed_calls[0][0] == [
        "./.odylith/bin/odylith",
        "greenfield",
        "candidate-contract",
        "--repo-root",
        ".",
        "--prompt",
        "Create a reviewable plan.",
        "--edit",
        "Keep the source path.",
    ]
    assert len(host_calls) == 1
    assert host_calls[0][0][:4] == [
        str((tmp_path / "trusted/bin/codex").resolve()),
        "exec",
        "--ephemeral",
        "--ignore-user-config",
    ]
    assert "{candidate_schema}" not in host_calls[0][0]
    assert host_calls[0][1] == contract_text
    assert len(proposal_paths) == 1
    assert not proposal_paths[0].exists()
    assert not any(path == repo or repo in path.parents for path in proposal_paths)
    assert list(repo.iterdir()) == []
    assert observations[-1]["status"] == "passed"
    assert observations[-1]["host_invocations"] == 1
    assert observations[-1]["model_profile_id"] == "greenfield-standard-v1"
    assert observations[-1]["source_sha256"] == hashlib.sha256(
        b"Create a reviewable plan."
    ).hexdigest()
    assert observations[-1]["response_kind"] == "authored"
    request = observations[-1]["host_request"]
    assert set(request) == {
        "version", "executable_sha256", "argument_count", "model",
        "reasoning_effort", "output_schema_present", "argv_shape_sha256",
    }
    assert request["model"] == "gpt-6-astra"
    assert request["reasoning_effort"] == "medium"
    assert request["output_schema_present"] is True
    assert "host_argv" not in observations[-1]
    assert observations[-1]["candidate_temp_cleaned"] is True
    assert observations[-1]["host_workspace_cleaned"] is True
    assert observations[-1]["candidate_sha256"] == hashlib.sha256(
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
    assert observations[-1]["candidate_raw_sha256"] == hashlib.sha256(raw_candidate).hexdigest()
    assert observations[-1]["candidate_raw_bytes"] == len(raw_candidate)
    assert observations[-1]["proposal_returncode"] == 0
    assert observations[-1]["proposal_mode"] == "product_create_transaction"
    assert observations[-1]["candidate_review_status"] == "unreported"
    assert not host_calls[0][3].exists()
    assert "candidate" not in observations[-1]


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
        host_module.qualify_host_candidate_argv(
            (str(wrapper), *base[1:]),
            trusted_codex_executable=str(trusted),
            expected_model="gpt-6-astra",
            expected_reasoning_effort="medium",
            expected_output_schema="{candidate_schema}",
        )
    with pytest.raises(ValueError, match="configured Codex executable"):
        host_module.resolve_trusted_codex_executable(
            environ={
                "PATH": str(trusted.parent),
                "ODYLITH_REASONING_CODEX_BIN": str(wrapper),
            }
        )

    secret = "sk-private-do-not-retain"
    contaminated = (*base[:-3], "--config", f"api_key={secret}", *base[-3:])
    with pytest.raises(ValueError) as raised:
        host_module.qualify_host_candidate_argv(
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
        host_module.qualify_host_candidate_argv(
            contaminated,
            trusted_codex_executable=str(trusted),
            expected_model="gpt-6-astra",
            expected_reasoning_effort="medium",
            expected_output_schema="{candidate_schema}",
        )


def test_host_candidate_clarification_candidate_is_passed_unchanged_to_propose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "version": "candidate",
        "result": {
            "status": "clarification_required",
            "clarification": {"required_fields": ["first_path"]},
        },
    }
    flow, host_run, _installed, host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate=candidate,
    )
    observations: list[dict[str, object]] = []
    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "observe": observations.append})
    monkeypatch.setattr(host_module.subprocess, "run", host_run)
    result = host_module.run_host_candidate_flow(flow)

    assert result.returncode == 0
    assert len(host_calls) == 1
    assert len(proposal_paths) == 1
    assert observations[-1]["response_kind"] == "clarification_required"
    assert observations[-1]["candidate_temp_cleaned"] is True


def test_host_candidate_retains_raw_candidate_and_denied_proposal_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {"version": "candidate", "result": {"status": "authored"}}
    flow, host_run, _installed, _host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate=candidate,
    )
    retained: dict[str, bytes] = {}
    observations: list[dict[str, object]] = []

    def denied(_path: Path, _timeout: float):
        return _completed(
            ["odylith", "greenfield", "propose"],
            stdout=json.dumps({"mode": "error", "candidate_review": {"status": "denied"}}),
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
    monkeypatch.setattr(host_module.subprocess, "run", host_run)

    with pytest.raises(host_module.HostCandidateFlowError, match="proposal command returned nonzero"):
        host_module.run_host_candidate_flow(flow)

    assert proposal_paths == []
    assert retained["candidate"] == json.dumps(candidate).encode("utf-8")
    assert json.loads(retained["stdout"]) == {
        "mode": "error", "candidate_review": {"status": "denied"},
    }
    assert retained["stderr"] == b""
    observation = observations[-1]
    assert observation["candidate_raw_sha256"] == hashlib.sha256(retained["candidate"]).hexdigest()
    assert observation["proposal_returncode"] == 2
    assert observation["proposal_mode"] == "error"
    assert observation["candidate_review_status"] == "denied"
    assert observation["candidate_temp_cleaned"] is True


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
        tmp_path, contract={"version": "contract"}, candidate={"version": "candidate"},
    )
    proposal_calls: list[Path] = []
    flow = host_module.HostCandidateFlow(
        **{**flow.__dict__, "invoke_propose": lambda path, _timeout: proposal_calls.append(path)},
    )

    def host_run(command, **kwargs):
        if host_behavior == "unavailable":
            raise FileNotFoundError("host-author")
        if host_behavior == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if host_behavior == "nonzero":
            return _completed(list(command), returncode=7, stderr="host rejected candidate")
        return _completed(list(command), stdout="not JSON")

    monkeypatch.setattr(host_module.subprocess, "run", host_run)
    with pytest.raises(host_module.HostCandidateFlowError) as raised:
        host_module.run_host_candidate_flow(flow)

    assert expected_fragment.casefold() in str(raised.value).casefold()
    assert len(host_calls) == 0
    assert proposal_calls == []
    assert proposal_paths == []


def test_malformed_host_output_is_retained_before_parse_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, _host_run, _installed, _host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate={"version": "candidate"},
    )
    retained: list[bytes] = []
    malformed = b'{"first": true}\n{"second": true}\n'

    def host_run(command, **_kwargs):
        return _completed(list(command), stdout=malformed.decode("utf-8"))

    flow = host_module.HostCandidateFlow(
        **{**flow.__dict__, "retain_candidate_bytes": retained.append}
    )
    monkeypatch.setattr(host_module.subprocess, "run", host_run)

    with pytest.raises(host_module.HostCandidateFlowError, match="failed closed") as raised:
        host_module.run_host_candidate_flow(flow)

    assert retained == [malformed]
    assert "candidate" not in raised.value.observation


def test_contract_command_failure_stops_before_host_invocation(tmp_path: Path) -> None:
    flow, _host_run, _installed, _host_calls, _proposal_paths, _repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate={"version": "candidate"},
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
        contract={"version": "contract"},
        candidate={"version": "candidate", "result": {"status": "authored"}},
    )
    monkeypatch.setattr(host_module.subprocess, "run", host_run)

    def slow_contract(command, timeout):
        installed_calls.append((list(command), timeout))
        time.sleep(0.02)
        return _completed(
            list(command),
            stdout=json.dumps({
                "version": "contract",
                "candidate_schema": {},
                "request": {"evidence": "Create a reviewable plan."},
            }),
        )

    flow = host_module.HostCandidateFlow(**{**flow.__dict__, "invoke_installed": slow_contract})
    host_module.run_host_candidate_flow(flow)

    assert host_calls[0][2] < installed_calls[0][1]
    assert host_calls[0][2] > 0


def test_propose_arguments_wire_exact_candidate_file_without_changing_legacy_default() -> None:
    legacy = matrix_module._greenfield_propose_arguments(prompt="Build it.")
    host = matrix_module._greenfield_propose_arguments(
        prompt="Build it.", candidate_file="/tmp/candidate.json",
    )

    assert "--candidate-file" not in legacy
    assert host[-2:] == ["--candidate-file", "/tmp/candidate.json"]


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
