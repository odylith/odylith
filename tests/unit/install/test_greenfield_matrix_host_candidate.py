from __future__ import annotations

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
    installed_calls: list[tuple[list[str], float]] = []
    host_calls: list[tuple[list[str], str, float, Path]] = []
    proposal_paths: list[Path] = []
    contract_payload = dict(contract)
    contract_payload.setdefault("candidate_schema", {})

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
        schema_path = Path(command[command.index("--schema") + 1])
        assert schema_path.is_file()
        assert schema_path.parent == Path(kwargs["cwd"])
        return _completed(list(command), stdout=json.dumps(candidate))

    def propose(path: Path, timeout: float):
        proposal_paths.append(path)
        assert path.is_file()
        assert json.loads(path.read_text(encoding="utf-8")) == candidate
        return _completed(["odylith", "greenfield", "propose"])

    return (
        host_module.HostCandidateFlow(
            repo_root=repo,
            temp_parent=temp_parent,
            host_argv=(
                "host-author",
                "--json",
                "--schema",
                "{candidate_schema}",
            ),
            prompt="Create a reviewable plan.",
            edit_evidence="Keep the source path.",
            timeout=5.0,
            env={"PATH": "/usr/bin"},
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
    contract_text = json.dumps({"version": "contract", "candidate_schema": {}})
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
    assert host_calls[0][0][:3] == ["host-author", "--json", "--schema"]
    assert "{candidate_schema}" not in host_calls[0][0]
    assert host_calls[0][1] == contract_text
    assert len(proposal_paths) == 1
    assert not proposal_paths[0].exists()
    assert not any(path == repo or repo in path.parents for path in proposal_paths)
    assert list(repo.iterdir()) == []
    assert observations[-1]["status"] == "passed"
    assert observations[-1]["host_invocations"] == 1
    assert observations[-1]["candidate_temp_cleaned"] is True
    assert observations[-1]["host_workspace_cleaned"] is True
    assert not host_calls[0][3].exists()


def test_host_candidate_clarification_candidate_is_passed_unchanged_to_propose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "mode": "clarification_required",
        "clarification": {"required_fields": ["first_path"]},
    }
    flow, host_run, _installed, host_calls, proposal_paths, _repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate=candidate,
    )
    monkeypatch.setattr(host_module.subprocess, "run", host_run)
    result = host_module.run_host_candidate_flow(flow)

    assert result.returncode == 0
    assert len(host_calls) == 1
    assert len(proposal_paths) == 1


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
        tmp_path, contract={"version": "contract"}, candidate={"version": "candidate"},
    )
    monkeypatch.setattr(host_module.subprocess, "run", host_run)

    def slow_contract(command, timeout):
        installed_calls.append((list(command), timeout))
        time.sleep(0.02)
        return _completed(
            list(command),
            stdout=json.dumps({"version": "contract", "candidate_schema": {}}),
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
