"""Run one explicit host-native Greenfield candidate through the installed CLI."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HOST_NATIVE_MATRIX_OBSERVATION_VERSION = (
    "odylith.greenfield.host-native-matrix-observation.v3"
)
HOST_NATIVE_ARGV_RECEIPT_VERSION = "odylith.greenfield.host-argv-receipt.v1"


class HostCandidateFlowError(RuntimeError):
    """A host-native candidate flow failed closed before publication."""

    def __init__(self, message: str, *, observation: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.observation = dict(observation)


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
    invoke_propose: Callable[[Path, float], Any]
    installed_command: tuple[str, ...] = ("./.odylith/bin/odylith",)
    observe: Callable[[Mapping[str, Any]], None] | None = None


def run_host_candidate_flow(flow: HostCandidateFlow) -> Any:
    """Obtain a contract, invoke exactly one configured host, and propose its candidate.

    The callback for ``invoke_propose`` receives a temporary candidate path. The
    path is always removed before this function returns or raises. Every stage
    receives only the remaining portion of one total timeout window.
    """

    host_argv, _ = qualify_host_candidate_argv(
        flow.host_argv,
        trusted_codex_executable=flow.trusted_codex_executable,
        expected_model=flow.expected_model,
        expected_reasoning_effort=flow.expected_reasoning_effort,
        expected_output_schema="{candidate_schema}",
        path_value=str(flow.env.get("PATH") or os.environ.get("PATH") or ""),
    )
    timeout = _positive_timeout(flow.timeout)
    repo_root = Path(flow.repo_root).expanduser().resolve()
    temp_parent = Path(flow.temp_parent).expanduser().resolve()
    _require_temp_parent_outside_repo(temp_parent=temp_parent, repo_root=repo_root)
    temp_parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    observation: dict[str, Any] = {
        "version": HOST_NATIVE_MATRIX_OBSERVATION_VERSION,
        "status": "running",
        "host_invocations": 0,
        "contract_command_invocations": 0,
        "proposal_command_invocations": 0,
        "model_profile_id": str(
            flow.env.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or ""
        ).strip(),
        "candidate_temp_cleaned": False,
        "host_workspace_cleaned": False,
    }
    candidate_path: Path | None = None
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
            observation["host_invocations"] = 1
            observation["stage"] = "host"
            host_result = _invoke_host(
                resolved_host_argv,
                contract_text=contract_text,
                cwd=host_workspace,
                env=flow.env,
                timeout=_remaining(started, timeout),
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
            candidate = _single_json_object(candidate_text, label="host candidate")
            result = candidate.get("result")
            response_kind = (
                str(result.get("status") or "").strip()
                if isinstance(result, Mapping)
                else ""
            )
            if response_kind not in {"authored", "clarification_required"}:
                _fail(
                    "host-native candidate has an unsupported response kind",
                    observation=observation,
                    stage="host",
                )
            observation["response_kind"] = response_kind
            observation["candidate_sha256"] = hashlib.sha256(
                json.dumps(
                    candidate,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()

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
                _remaining(started, timeout),
            )
        observation["candidate_temp_cleaned"] = not candidate_path.exists()
        observation["host_workspace_cleaned"] = not host_workspace.exists()
        if not observation["candidate_temp_cleaned"]:
            _fail(
                "host-native candidate temporary file was not cleaned",
                observation=observation,
                stage="candidate-cleanup",
            )
        observation["status"] = "passed"
        observation["elapsed_seconds"] = round(time.monotonic() - started, 3)
        _emit_observation(flow.observe, observation)
        return proposal
    except HostCandidateFlowError:
        raise
    except (OSError, TypeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        _fail(
            f"host-native candidate flow failed closed: {type(exc).__name__}",
            observation=observation,
            stage=str(observation.get("stage") or "flow"),
        )
    finally:
        observation.setdefault("elapsed_seconds", round(time.monotonic() - started, 3))
        if observation.get("status") == "running":
            observation["status"] = "failed"
        if candidate_path is not None:
            observation["candidate_temp_cleaned"] = not candidate_path.exists()
        if host_workspace is not None:
            observation["host_workspace_cleaned"] = not host_workspace.exists()
        if observation.get("status") != "passed":
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
    expected_tokens = (
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        expected_model,
        "--config",
        f"model_reasoning_effort={expected_reasoning_effort}",
        "--output-schema",
        expected_output_schema,
        "-",
    )
    if tokens != expected_tokens:
        raise ValueError(
            "host-native candidate command does not match the canonical release argv contract"
        )
    canonical_argv = (str(trusted), *tokens)
    receipt = {
        "version": HOST_NATIVE_ARGV_RECEIPT_VERSION,
        "executable_sha256": _sha256_file(trusted),
        "argument_count": len(canonical_argv),
        "model": expected_model,
        "reasoning_effort": expected_reasoning_effort,
        "output_schema_present": True,
        "argv_shape_sha256": hashlib.sha256(
            json.dumps(
                (
                    "exec", "ephemeral", "ignore-user-config", "skip-git-repo-check",
                    "sandbox:read-only", "model", "config:model_reasoning_effort",
                    "output-schema", "stdin",
                ),
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
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
    "HOST_NATIVE_MATRIX_OBSERVATION_VERSION",
    "HOST_NATIVE_ARGV_RECEIPT_VERSION",
    "HostCandidateFlow",
    "HostCandidateFlowError",
    "qualify_host_candidate_argv",
    "resolve_trusted_codex_executable",
    "run_host_candidate_flow",
]
