"""Run one explicit host-native Greenfield candidate through the installed CLI."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
)

HOST_NATIVE_MATRIX_OBSERVATION_VERSION = (
    "odylith.greenfield.host-native-matrix-observation.v7"
)
HOST_NATIVE_ARGV_RECEIPT_VERSION = "odylith.greenfield.host-argv-receipt.v1"


def _canonical_host_candidate_tokens(
    *, model: str, reasoning_effort: str, output_schema: str
) -> tuple[str, ...]:
    """Return the exact direct-Codex token contract used by release authoring."""

    return (
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        model,
        "--config",
        f"model_reasoning_effort={reasoning_effort}",
        "--output-schema",
        output_schema,
        "-",
    )


def canonical_host_candidate_argv_template() -> tuple[str, ...]:
    """Return the one placeholder argv accepted by Greenfield release proof."""

    return (
        "codex",
        *_canonical_host_candidate_tokens(
            model="{model}",
            reasoning_effort="{reasoning_effort}",
            output_schema="{candidate_schema}",
        ),
    )


def post_receipt_runtime_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Disable every runtime provider route after host-candidate receipt."""

    values = dict(environ)
    values.update(
        {
            "ODYLITH_REASONING_MODE": "disabled",
            "ODYLITH_REASONING_PROVIDER": "auto-local",
            "ODYLITH_REASONING_TIMEOUT_SECONDS": "1",
            "ODYLITH_REASONING_CODEX_BIN": "/usr/bin/false",
            "ODYLITH_REASONING_CLAUDE_BIN": "/usr/bin/false",
        }
    )
    return values


HOST_NATIVE_ARGV_ARGUMENT_COUNT = 1 + len(
    _canonical_host_candidate_tokens(model="", reasoning_effort="", output_schema="")
)
HOST_NATIVE_ARGV_SHAPE_SHA256 = hashlib.sha256(
    json.dumps(
        (
            "exec", "ephemeral", "ignore-user-config", "skip-git-repo-check",
            "sandbox:read-only", "model", "config:model_reasoning_effort",
            "output-schema", "stdin",
        ),
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


class HostCandidateFlowError(RuntimeError):
    """A host-native candidate flow failed closed before publication."""

    def __init__(self, message: str, *, observation: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.observation = dict(observation)

    def __str__(self) -> str:
        diagnostic_keys = (
            "stage",
            "host_returncode",
            "contract_sha256",
            "candidate_schema_sha256",
            "host_output_sha256",
            "host_output_bytes",
            "proposal_returncode",
            "proposal_mode",
            "proposal_stdout_sha256",
            "runtime_semantic_model_call_count",
            "post_receipt_provider_invocations",
            "elapsed_seconds",
        )
        diagnostic = {
            key: self.observation[key]
            for key in diagnostic_keys
            if key in self.observation
        }
        return (
            f"{super().__str__()}; diagnostic="
            f"{json.dumps(diagnostic, sort_keys=True, separators=(',', ':'))}"
        )


@dataclass(frozen=True)
class HostCandidateFlow:
    """Dependencies for one bounded host-native authoring flow."""

    repo_root: Path
    temp_parent: Path
    host_argv: tuple[str, ...]
    prompt: str
    edit_evidence: str
    timeout: float
    env: Mapping[str, str]
    trusted_codex_executable: str
    expected_model: str
    expected_reasoning_effort: str
    invoke_installed: Callable[[Sequence[str], float], Any]
    invoke_propose: Callable[[Path, Path, float], Any]
    installed_command: tuple[str, ...] = ("./.odylith/bin/odylith",)
    observe: Callable[[Mapping[str, Any]], None] | None = None
    retain_authority_gate_bytes: Callable[[bytes], None] | None = None
    retain_candidate_bytes: Callable[[bytes], None] | None = None
    retain_proposal_bytes: Callable[[str, bytes], None] | None = None


def run_host_candidate_flow(flow: HostCandidateFlow) -> Any:
    """Obtain a contract, invoke exactly one configured host, and propose its candidate.

    The callback for ``invoke_propose`` receives temporary candidate and gate
    paths. Both are removed before return. Host calls share the pinned model
    window; installed commands retain the separate operational timeout.
    """

    host_argv, _ = qualify_host_candidate_argv(
        flow.host_argv,
        trusted_codex_executable=flow.trusted_codex_executable,
        expected_model=flow.expected_model,
        expected_reasoning_effort=flow.expected_reasoning_effort,
        expected_output_schema="{candidate_schema}",
        path_value=str(flow.env.get("PATH") or os.environ.get("PATH") or ""),
    )
    profile_id = str(flow.env.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or "").strip()
    profile = get_greenfield_model_profile(profile_id)
    timeout = min(_positive_timeout(flow.timeout), profile.operational_timeout_seconds)
    model_timeout = min(timeout, profile.model_timeout_seconds)
    repo_root = Path(flow.repo_root).expanduser().resolve()
    temp_parent = Path(flow.temp_parent).expanduser().resolve()
    _require_temp_parent_outside_repo(temp_parent=temp_parent, repo_root=repo_root)
    temp_parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    observation: dict[str, Any] = {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "status": "running",
        "host_invocations": 0,
        "authority_gate_host_invocations": 0,
        "candidate_host_invocations": 0,
        "contract_command_invocations": 0,
        "authority_check_command_invocations": 0,
        "proposal_command_invocations": 0,
        "runtime_semantic_model_call_count": 0,
        "post_receipt_provider_invocations": 0,
        "model_profile_id": profile_id,
        "model_window_seconds": model_timeout,
        "operational_timeout_seconds": timeout,
        "candidate_temp_cleaned": False,
        "authority_gate_temp_cleaned": False,
        "host_workspace_cleaned": False,
    }
    candidate_path: Path | None = None
    gate_path: Path | None = None
    host_workspace: Path | None = None
    try:
        observation["contract_command_invocations"] = 1
        observation["stage"] = "contract"
        contract_result = _invoke_installed_contract(flow, remaining=_remaining(started, timeout))
        observation["contract_returncode"] = int(getattr(contract_result, "returncode", 1))
        if observation["contract_returncode"] != 0:
            _fail(
                "host-native candidate contract command failed",
                observation=observation,
                stage="contract",
                detail=_stream_excerpt(contract_result),
            )
        contract_text = _text_stream(getattr(contract_result, "stdout", ""))
        contract = _single_json_object(contract_text, label="candidate contract")
        observation["contract_sha256"] = _sha256_text(contract_text)
        request = contract.get("request")
        source = request.get("evidence") if isinstance(request, Mapping) else None
        if not isinstance(source, str) or not source.strip():
            _fail(
                "host-native candidate contract has no source evidence",
                observation=observation,
                stage="contract",
            )
        observation["source_sha256"] = _sha256_text(source)
        with tempfile.TemporaryDirectory(
            prefix="odylith-greenfield-host-candidate-",
            dir=str(temp_parent),
        ) as candidate_dir:
            host_workspace = Path(candidate_dir)
            gate_contract = contract.get("authority_gate")
            if not isinstance(gate_contract, Mapping) or set(gate_contract) != {
                "version", "task", "operator_request", "operator_edit", "response_schema",
            }:
                _fail(
                    "host-native candidate contract has no closed authority gate",
                    observation=observation,
                    stage="contract",
                )
            if not isinstance(gate_contract.get("response_schema"), Mapping):
                _fail(
                    "host-native authority gate has no response schema",
                    observation=observation,
                    stage="contract",
                )
            if (gate_contract.get("operator_request") != flow.prompt
                    or gate_contract.get("operator_edit") != flow.edit_evidence
                    or not str(gate_contract.get("task") or "").strip()):
                _fail("host-native authority gate is not bound to the operator request",
                      observation=observation, stage="contract")
            gate_schema_path = host_workspace / "authority-gate-schema.json"
            gate_schema_path.write_text(
                json.dumps(gate_contract["response_schema"], ensure_ascii=False,
                           sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            gate_argv, gate_request = qualify_host_candidate_argv(
                _resolved_host_argv(host_argv, candidate_schema_path=gate_schema_path),
                trusted_codex_executable=flow.trusted_codex_executable,
                expected_model=flow.expected_model,
                expected_reasoning_effort=flow.expected_reasoning_effort,
                expected_output_schema=str(gate_schema_path),
                path_value=str(flow.env.get("PATH") or os.environ.get("PATH") or ""),
            )
            observation["authority_gate_request"] = gate_request
            observation["authority_gate_schema_sha256"] = _sha256_text(
                gate_schema_path.read_text(encoding="utf-8")
            )
            observation["stage"] = "authority-gate"
            gate_timeout = _remaining(started, model_timeout)
            observation["host_invocations"] = 1
            observation["authority_gate_host_invocations"] = 1
            gate_result = _invoke_host(
                gate_argv,
                contract_text=json.dumps(dict(gate_contract), ensure_ascii=False,
                                         sort_keys=True, separators=(",", ":")),
                cwd=host_workspace,
                env=flow.env,
                timeout=gate_timeout,
            )
            observation["authority_gate_returncode"] = int(
                getattr(gate_result, "returncode", 1)
            )
            gate_text = _text_stream(getattr(gate_result, "stdout", ""))
            gate_bytes = gate_text.encode("utf-8")
            if flow.retain_authority_gate_bytes is not None:
                flow.retain_authority_gate_bytes(gate_bytes)
            observation["authority_gate_output_sha256"] = hashlib.sha256(gate_bytes).hexdigest()
            observation["authority_gate_output_bytes"] = len(gate_bytes)
            if observation["authority_gate_returncode"] != 0:
                _fail("host-native authority gate command returned nonzero",
                      observation=observation, stage="authority-gate")
            gate = _single_json_object(gate_text, label="authority gate")
            decision = gate.get("decision")
            if decision not in {"admit", "clarify"}:
                _fail("host-native authority gate decision is invalid",
                      observation=observation, stage="authority-gate")
            observation["authority_gate_decision"] = decision
            gate_path = host_workspace / "authority-gate.json"
            gate_path.write_text(
                json.dumps(gate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n", encoding="utf-8",
            )
            observation["authority_gate_temp_outside_repo"] = not _is_within(
                gate_path, repo_root
            )
            if not observation["authority_gate_temp_outside_repo"]:
                _fail("host-native authority gate path is inside the consumer repo",
                      observation=observation, stage="authority-gate-file")
            observation["authority_check_command_invocations"] = 1
            observation["stage"] = "authority-check"
            authority_check = _invoke_installed_authority_check(
                flow, gate_path=gate_path, remaining=_remaining(started, timeout)
            )
            observation["authority_check_returncode"] = int(
                getattr(authority_check, "returncode", 1)
            )
            check_stdout = _text_stream(getattr(authority_check, "stdout", ""))
            observation["authority_check_stdout_sha256"] = _sha256_text(check_stdout)
            observation["authority_check_stderr_sha256"] = _sha256_text(
                _text_stream(getattr(authority_check, "stderr", ""))
            )
            if observation["authority_check_returncode"] != 0:
                _fail("installed authority check returned nonzero",
                      observation=observation, stage="authority-check")
            check_payload = _single_json_object(check_stdout, label="authority check")
            check_mode = str(check_payload.get("mode") or "").strip()
            if decision == "clarify":
                if check_mode != "clarification_required":
                    _fail("installed authority check did not clarify",
                          observation=observation, stage="authority-check")
                observation["response_kind"] = "clarification_required"
                observation["proposal_mode"] = "clarification_required"
                observation["candidate_temp_cleaned"] = True
                observation["status"] = "passed"
                return authority_check
            else:
                if check_mode != "authority_admitted" or check_payload.get("gate") != gate:
                    _fail("installed authority check did not admit",
                          observation=observation, stage="authority-check")
            schema_path = host_workspace / "candidate-schema.json"
            candidate_schema = contract.get("candidate_schema")
            if not isinstance(candidate_schema, Mapping):
                _fail(
                    "host-native candidate contract has no object candidate schema",
                    observation=observation,
                    stage="contract",
                )
            schema_path.write_text(
                json.dumps(
                    dict(candidate_schema),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            resolved_host_argv = _resolved_host_argv(
                host_argv,
                candidate_schema_path=schema_path,
            )
            resolved_host_argv, host_request = qualify_host_candidate_argv(
                resolved_host_argv,
                trusted_codex_executable=flow.trusted_codex_executable,
                expected_model=flow.expected_model,
                expected_reasoning_effort=flow.expected_reasoning_effort,
                expected_output_schema=str(schema_path),
                path_value=str(flow.env.get("PATH") or os.environ.get("PATH") or ""),
            )
            observation["host_request"] = host_request
            observation["candidate_schema_sha256"] = _sha256_text(
                schema_path.read_text(encoding="utf-8")
            )
            observation["stage"] = "host"
            candidate_timeout = _remaining(started, model_timeout)
            observation["host_invocations"] = 2
            observation["candidate_host_invocations"] = 1
            host_result = _invoke_host(
                resolved_host_argv,
                contract_text=contract_text,
                cwd=host_workspace,
                env=flow.env,
                timeout=candidate_timeout,
            )
            observation["host_returncode"] = int(getattr(host_result, "returncode", 1))
            observation["host_stdout_bytes"] = len(
                _text_stream(getattr(host_result, "stdout", "")).encode("utf-8")
            )
            observation["host_stderr_bytes"] = len(
                _text_stream(getattr(host_result, "stderr", "")).encode("utf-8")
            )
            if observation["host_returncode"] != 0:
                _fail(
                    "host-native candidate command returned nonzero",
                    observation=observation,
                    stage="host",
                )
            candidate_text = _text_stream(getattr(host_result, "stdout", ""))
            candidate_bytes = candidate_text.encode("utf-8")
            if flow.retain_candidate_bytes is not None:
                flow.retain_candidate_bytes(candidate_bytes)
            candidate = _single_json_object(candidate_text, label="host candidate")
            result = candidate.get("result")
            response_kind = (
                str(result.get("status") or "").strip()
                if isinstance(result, Mapping)
                else ""
            )
            if response_kind != "authored":
                _fail(
                    "host-native candidate has an unsupported response kind",
                    observation=observation,
                    stage="host",
                )
            observation["response_kind"] = response_kind
            observation["raw_candidate_sha256"] = hashlib.sha256(
                json.dumps(
                    candidate,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            observation["host_output_sha256"] = hashlib.sha256(candidate_bytes).hexdigest()
            observation["host_output_bytes"] = len(candidate_bytes)

            candidate_path = Path(candidate_dir) / "candidate.json"
            candidate_path.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n",
                encoding="utf-8",
            )
            observation["candidate_temp_outside_repo"] = not _is_within(
                candidate_path, repo_root
            )
            if not observation["candidate_temp_outside_repo"]:
                _fail(
                    "host-native candidate temporary path is inside the consumer repo",
                    observation=observation,
                    stage="candidate-file",
                )
            observation["proposal_command_invocations"] = 1
            observation["stage"] = "propose"
            proposal = flow.invoke_propose(
                candidate_path,
                gate_path,
                _remaining(started, timeout),
            )
            proposal_stdout = _text_stream(getattr(proposal, "stdout", ""))
            proposal_stderr = _text_stream(getattr(proposal, "stderr", ""))
            if flow.retain_proposal_bytes is not None:
                flow.retain_proposal_bytes("stdout", proposal_stdout.encode("utf-8"))
                flow.retain_proposal_bytes("stderr", proposal_stderr.encode("utf-8"))
            observation["proposal_returncode"] = int(getattr(proposal, "returncode", 1))
            observation["proposal_stdout_sha256"] = _sha256_text(proposal_stdout)
            observation["proposal_stderr_sha256"] = _sha256_text(proposal_stderr)
            proposal_outcome = _proposal_outcome(proposal_stdout)
            observation.update(proposal_outcome)
            if observation["proposal_returncode"] != 0:
                _fail(
                    "host-native candidate proposal command returned nonzero",
                    observation=observation,
                    stage="propose",
                )
            if proposal_outcome["proposal_mode"] not in {
                "product_create_transaction",
                "clarification_required",
            }:
                _fail(
                    "host-native candidate proposal did not produce an admitted outcome",
                    observation=observation,
                    stage="propose",
                )
        observation["candidate_temp_cleaned"] = not candidate_path.exists()
        observation["authority_gate_temp_cleaned"] = not gate_path.exists()
        observation["host_workspace_cleaned"] = not host_workspace.exists()
        if not observation["candidate_temp_cleaned"]:
            _fail(
                "host-native candidate temporary file was not cleaned",
                observation=observation,
                stage="candidate-cleanup",
            )
        if not observation["authority_gate_temp_cleaned"]:
            _fail("host-native authority gate temporary file was not cleaned",
                  observation=observation, stage="authority-gate-cleanup")
        observation["status"] = "passed"
        observation["elapsed_seconds"] = round(time.monotonic() - started, 3)
        _emit_observation(flow.observe, observation)
        return proposal
    except HostCandidateFlowError:
        raise
    except (OSError, TypeError, ValueError, TimeoutError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        _fail(
            f"host-native candidate flow failed closed: {type(exc).__name__}",
            observation=observation,
            stage=str(observation.get("stage") or "flow"),
        )
    finally:
        observation.setdefault("elapsed_seconds", round(time.monotonic() - started, 3))
        if observation.get("status") == "running":
            observation["status"] = "failed"
        observation["candidate_temp_cleaned"] = candidate_path is None or not candidate_path.exists()
        observation["authority_gate_temp_cleaned"] = gate_path is None or not gate_path.exists()
        observation["host_workspace_cleaned"] = host_workspace is None or not host_workspace.exists()
        if observation.get("status") != "passed" or observation.get("response_kind") == "clarification_required":
            _emit_observation(flow.observe, observation)


def _invoke_installed_contract(flow: HostCandidateFlow, *, remaining: float) -> Any:
    command = [
        *flow.installed_command,
        "greenfield",
        "candidate-contract",
        "--repo-root",
        ".",
        "--prompt",
        flow.prompt,
    ]
    if flow.edit_evidence.strip():
        command.extend(("--edit", flow.edit_evidence))
    return flow.invoke_installed(command, remaining)


def _invoke_installed_authority_check(
    flow: HostCandidateFlow, *, gate_path: Path, remaining: float
) -> Any:
    command = [
        *flow.installed_command,
        "greenfield", "authority-check", "--repo-root", ".",
        "--prompt", flow.prompt,
    ]
    if flow.edit_evidence.strip():
        command.extend(("--edit", flow.edit_evidence))
    command.extend(("--gate-file", str(gate_path), "--format", "json"))
    return flow.invoke_installed(command, remaining)


def _invoke_host(
    host_argv: Sequence[str],
    *,
    contract_text: str,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(host_argv),
        cwd=str(cwd),
        env=dict(env),
        input=contract_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _single_json_object(value: str, *, label: str) -> dict[str, Any]:
    if not value.strip():
        raise ValueError(f"{label} output is empty")
    payload = json.loads(value)
    if not isinstance(payload, Mapping):
        raise TypeError(f"{label} output must be exactly one JSON object")
    return dict(payload)


def resolve_trusted_codex_executable(
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the one PATH-trusted Codex executable used by release proof."""

    values = dict(os.environ if environ is None else environ)
    path_value = str(values.get("PATH") or "")
    located = shutil.which("codex", path=path_value)
    if not located:
        raise ValueError("trusted Codex executable is unavailable")
    trusted = _resolved_executable(located, path_value=path_value)
    configured = str(values.get("ODYLITH_REASONING_CODEX_BIN") or "").strip()
    if configured:
        configured_path = _resolved_executable(configured, path_value=path_value)
        if configured_path != trusted:
            raise ValueError("configured Codex executable does not match the trusted Codex binary")
    return str(trusted)


def qualify_host_candidate_argv(
    value: Sequence[str],
    *,
    trusted_codex_executable: str,
    expected_model: str,
    expected_reasoning_effort: str,
    expected_output_schema: str,
    path_value: str = "",
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Validate one direct Codex argv and return only a safe derived receipt."""

    argv = tuple(str(argument) for argument in value)
    if not argv or any(not argument for argument in argv):
        raise ValueError("host-native candidate command requires a non-empty argv")
    trusted = _resolved_executable(
        trusted_codex_executable,
        path_value=path_value or str(os.environ.get("PATH") or ""),
    )
    executable = _resolved_executable(
        argv[0],
        path_value=path_value or str(os.environ.get("PATH") or ""),
    )
    if executable != trusted:
        raise ValueError("host-native candidate command must invoke the trusted Codex binary directly")
    tokens = argv[1:]
    expected_tokens = _canonical_host_candidate_tokens(
        model=expected_model,
        reasoning_effort=expected_reasoning_effort,
        output_schema=expected_output_schema,
    )
    if tokens != expected_tokens:
        raise ValueError(
            "host-native candidate command does not match the canonical release argv contract"
        )
    canonical_argv = (str(trusted), *tokens)
    receipt = {
        "version": HOST_NATIVE_ARGV_RECEIPT_VERSION,
        "executable_sha256": _sha256_file(trusted),
        "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
        "model": expected_model,
        "reasoning_effort": expected_reasoning_effort,
        "output_schema_present": True,
        "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
    }
    return canonical_argv, receipt


def _resolved_executable(value: str, *, path_value: str) -> Path:
    token = str(value or "").strip()
    candidate = Path(token).expanduser()
    located = (
        str(candidate)
        if candidate.is_absolute() or token != candidate.name
        else str(shutil.which(token, path=path_value) or "")
    )
    if not located:
        raise ValueError("host-native candidate executable is unavailable")
    resolved = Path(located).expanduser().resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError("host-native candidate executable is not executable")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolved_host_argv(
    argv: Sequence[str],
    *,
    candidate_schema_path: Path,
) -> tuple[str, ...]:
    return tuple(
        str(argument).replace("{candidate_schema}", str(candidate_schema_path))
        for argument in argv
    )


def _positive_timeout(value: float) -> float:
    timeout = float(value)
    if timeout <= 0 or not math.isfinite(timeout):
        raise ValueError("host-native candidate timeout must be positive and finite")
    return timeout


def _remaining(started: float, timeout: float) -> float:
    remaining = timeout - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError("host-native candidate flow exceeded its total timeout")
    return remaining


def _require_temp_parent_outside_repo(*, temp_parent: Path, repo_root: Path) -> None:
    if _is_within(temp_parent, repo_root):
        raise ValueError("host-native candidate temporary path must be outside the consumer repo")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _stream_excerpt(result: Any) -> str:
    return (
        _text_stream(getattr(result, "stderr", ""))
        or _text_stream(getattr(result, "stdout", ""))
    )[:800]


def _text_stream(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _proposal_outcome(value: str) -> dict[str, str]:
    """Return only the deterministic proposal mode from a proposal response."""

    try:
        payload = _single_json_object(value, label="proposal")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"proposal_mode": "invalid"}
    return {"proposal_mode": str(payload.get("mode") or "").strip() or "invalid"}


def _emit_observation(
    observe: Callable[[Mapping[str, Any]], None] | None,
    observation: Mapping[str, Any],
) -> None:
    if observe is not None:
        observe(dict(observation))


def _fail(
    message: str,
    *,
    observation: dict[str, Any],
    stage: str,
    detail: str = "",
) -> None:
    observation["stage"] = stage
    if detail:
        observation["detail"] = detail
    raise HostCandidateFlowError(message, observation=observation)


__all__ = [
    "HOST_NATIVE_ARGV_ARGUMENT_COUNT",
    "HOST_NATIVE_MATRIX_OBSERVATION_VERSION",
    "HOST_NATIVE_ARGV_RECEIPT_VERSION",
    "HOST_NATIVE_ARGV_SHAPE_SHA256",
    "HostCandidateFlow",
    "HostCandidateFlowError",
    "canonical_host_candidate_argv_template",
    "post_receipt_runtime_env",
    "qualify_host_candidate_argv",
    "resolve_trusted_codex_executable",
    "run_host_candidate_flow",
]


def _main(argv: Sequence[str]) -> int:
    """Expose the canonical template to maintained shell entrypoints."""

    if tuple(argv) != ("--print-argv-template",):
        raise SystemExit("usage: greenfield_matrix_host_candidate.py --print-argv-template")
    print("\n".join(canonical_host_candidate_argv_template()))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
