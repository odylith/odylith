"""Run honest live benchmark scenarios through the local host CLI.

This module executes the same benchmark task through the same host CLI in a
disposable git worktree for both public comparison lanes:

- ``odylith_on``: the task prompt plus the declared full-product Odylith
  assistance stack
- ``odylith_off`` / ``raw_agent_baseline``: the same host CLI with Odylith
  assistance disabled

The runner neutralizes repo-local guidance in two places:

- the disposable workspace strips auto-consumed instruction entrypoints such as
  ``AGENTS.md``, ``CLAUDE.md``, ``.cursor/``, ``.windsurf/``, and
  ``.codex/`` while preserving truth-bearing repo docs for explicit reads; and
- the host CLI runs from a temporary ``HOME`` that keeps auth plus the pinned
  model/reasoning contract while dropping user-authored guidance config,
  plugins, MCP config, and project-doc fallback.

The public comparison is the full Odylith assistance stack versus the raw host
CLI lane on the same task. The lane contract must make any Odylith-only
affordance explicit instead of silently widening the benchmark story.
"""

from __future__ import annotations

import atexit
import contextlib
import errno
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterator, Mapping, Sequence

from odylith.runtime.evaluation import odylith_benchmark_live_artifacts
from odylith.runtime.evaluation import odylith_benchmark_live_diagnostics
from odylith.runtime.evaluation import odylith_benchmark_live_host_config
from odylith.runtime.evaluation import odylith_benchmark_isolation
from odylith.runtime.evaluation import odylith_benchmark_live_process
from odylith.runtime.evaluation import odylith_benchmark_mode
from odylith.runtime.evaluation import odylith_benchmark_live_prompt
from odylith.runtime.reasoning import odylith_reasoning


_STATUS_VALUES = {"completed", "blocked", "failed"}
_LEADING_ENV_AND_ODYLITH_COMMAND = re.compile(
    r"^(?P<prefix>(?:[A-Za-z_][A-Za-z0-9_]*=(?:'[^']*'|\"[^\"]*\"|[^\s]+)\s+)*)odylith(?P<suffix>(?:\s|$).*)$"
)
_LIVE_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": sorted(_STATUS_VALUES),
        },
        "summary": {"type": "string"},
        "changed_files": {
            "type": "array",
            "items": {"type": "string"},
        },
        "validation_commands_run": {
            "type": "array",
            "items": {"type": "string"},
        },
        "validation_summary": {"type": "string"},
        "notes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "status",
        "summary",
        "changed_files",
        "validation_commands_run",
        "validation_summary",
        "notes",
    ],
    "additionalProperties": False,
}


_normalize_mode = odylith_benchmark_mode.normalize_public_mode


def _is_public_live_mode(mode: str) -> bool:
    return _normalize_mode(mode) in {"odylith_on", "raw_agent_baseline"}


_DEFAULT_LIVE_TIMEOUT_SECONDS = odylith_benchmark_live_process._DEFAULT_LIVE_TIMEOUT_SECONDS
_default_live_timeout_policy = odylith_benchmark_live_process._default_live_timeout_policy
_resolved_live_timeout_budget = odylith_benchmark_live_process._resolved_live_timeout_budget
_run_subprocess_capture = odylith_benchmark_live_process._run_subprocess_capture
_validator_timeout_seconds = odylith_benchmark_live_process._validator_timeout_seconds
_temporary_worktree = odylith_benchmark_isolation.temporary_workspace_checkout
_apply_strip_paths = odylith_benchmark_isolation.apply_workspace_strip_paths
_BENCHMARK_TEMP_CLEANUP_RETRYABLE_ERRNOS = frozenset({errno.ENOTEMPTY, errno.EBUSY, errno.EPERM})
_BENCHMARK_TEMP_CLEANUP_RETRY_COUNT = 4
_BENCHMARK_TEMP_CLEANUP_RETRY_DELAY_SECONDS = 0.05
_claude_auth_sources = odylith_benchmark_live_host_config.claude_auth_sources
_claude_home_candidates = odylith_benchmark_live_host_config.claude_home_candidates
_codex_auth_source = odylith_benchmark_live_host_config.codex_auth_source
_codex_home_candidates = odylith_benchmark_live_host_config.codex_home_candidates
_minimal_claude_settings = odylith_benchmark_live_host_config.minimal_claude_settings
_minimal_codex_config_text = odylith_benchmark_live_host_config.minimal_codex_config_text
_normalize_claude_cli_reasoning_effort = odylith_benchmark_live_host_config.normalize_claude_cli_reasoning_effort
_normalize_codex_cli_reasoning_effort = odylith_benchmark_live_host_config.normalize_codex_cli_reasoning_effort
_normalize_live_cli_reasoning_effort = odylith_benchmark_live_host_config.normalize_live_cli_reasoning_effort
_resolved_live_execution_contract = odylith_benchmark_live_host_config.resolved_live_execution_contract
_user_claude_config = odylith_benchmark_live_host_config.user_claude_config

_CLAUDE_ALLOWED_TOOLS = "Bash,Edit,Glob,Grep,Read,Write"
_LIVE_HOST_CLI = "live_host_cli"
_RAW_HOST_CLI = "raw_host_cli"
_CODEX_AUTH_SNAPSHOT_DIR: Path | None = None
_CODEX_AUTH_SNAPSHOT_PATH: Path | None = None
_CODEX_AUTH_SNAPSHOT_CANDIDATES: tuple[str, ...] = ()

_dedupe_strings = odylith_benchmark_live_artifacts._dedupe_strings
_parse_json_lines = odylith_benchmark_live_artifacts._parse_json_lines
_structured_output_from_events = odylith_benchmark_live_artifacts._structured_output_from_events
_normalized_structured_output_payload = odylith_benchmark_live_artifacts._normalized_structured_output_payload
_usage_from_events = odylith_benchmark_live_artifacts._usage_from_events
_command_events = odylith_benchmark_live_artifacts._command_events
_candidate_write_paths = odylith_benchmark_live_artifacts._candidate_write_paths
_resolve_workspace_file = odylith_benchmark_live_artifacts._resolve_workspace_file
_workspace_state_changed_paths = odylith_benchmark_live_artifacts._workspace_state_changed_paths
_workspace_file_fingerprint = odylith_benchmark_live_artifacts._workspace_file_fingerprint
_workspace_git_status_snapshot = odylith_benchmark_live_artifacts._workspace_git_status_snapshot
_workspace_state_delta_paths = odylith_benchmark_live_artifacts._workspace_state_delta_paths
_meaningful_candidate_write_paths = odylith_benchmark_live_artifacts._meaningful_candidate_write_paths
_observed_paths_from_events = odylith_benchmark_live_artifacts._observed_paths_from_events
_observed_path_details_from_events = odylith_benchmark_live_artifacts._observed_path_details_from_events
_prompt_supplied_paths_from_commands = odylith_benchmark_live_artifacts._prompt_supplied_paths_from_commands
_meaningful_preflight_command_paths = odylith_benchmark_live_artifacts._meaningful_preflight_command_paths
_path_recall = odylith_benchmark_live_artifacts._path_recall
_scenario_supporting_paths = odylith_benchmark_live_artifacts._scenario_supporting_paths
_scenario_expected_write_paths = odylith_benchmark_live_artifacts._scenario_expected_write_paths
_precision_metrics = odylith_benchmark_live_artifacts._precision_metrics


def _cleanup_codex_auth_snapshot() -> None:
    global _CODEX_AUTH_SNAPSHOT_CANDIDATES, _CODEX_AUTH_SNAPSHOT_DIR, _CODEX_AUTH_SNAPSHOT_PATH
    snapshot_dir = _CODEX_AUTH_SNAPSHOT_DIR
    _CODEX_AUTH_SNAPSHOT_DIR = None
    _CODEX_AUTH_SNAPSHOT_PATH = None
    _CODEX_AUTH_SNAPSHOT_CANDIDATES = ()
    if snapshot_dir is not None:
        _cleanup_benchmark_temp_dir(snapshot_dir)


atexit.register(_cleanup_codex_auth_snapshot)


def _call_with_supported_kwargs(function: Any, /, **kwargs: Any) -> Any:
    try:
        supported = inspect.signature(function)
    except (TypeError, ValueError):
        return function(**kwargs)
    accepted = {
        key: value
        for key, value in kwargs.items()
        if key in supported.parameters
    }
    return function(**accepted)


def _execution_provider(execution_contract: Mapping[str, str]) -> str:
    provider = str(execution_contract.get("provider", "")).strip().lower()
    if provider in {"codex-cli", "claude-cli"}:
        return provider
    if str(execution_contract.get("host_family", "")).strip().lower() == "claude":
        return "claude-cli"
    return "codex-cli"


def _execution_host_family(execution_contract: Mapping[str, str]) -> str:
    token = str(execution_contract.get("host_family", "")).strip().lower()
    if token in {"codex", "claude"}:
        return token
    return "claude" if _execution_provider(execution_contract) == "claude-cli" else "codex"


def _execution_bin(execution_contract: Mapping[str, str]) -> str:
    provider = _execution_provider(execution_contract)
    if provider == "claude-cli":
        return str(
            execution_contract.get("bin")
            or execution_contract.get("claude_bin")
            or "claude"
        ).strip()
    return str(
        execution_contract.get("bin")
        or execution_contract.get("codex_bin")
        or "codex"
    ).strip()


def _execution_runner(execution_contract: Mapping[str, str]) -> str:
    token = str(execution_contract.get("runner", "")).strip()
    return token or _LIVE_HOST_CLI


def _execution_transport(execution_contract: Mapping[str, str]) -> str:
    return "claude_stream_json" if _execution_provider(execution_contract) == "claude-cli" else "codex_exec_jsonl"


def _host_binary_available(binary: str) -> bool:
    token = str(binary or "").strip()
    if not token:
        return False
    if shutil.which(token):
        return True
    if "/" in token or token.startswith("."):
        candidate = Path(token).expanduser()
        return candidate.is_file() and os.access(candidate, os.X_OK)
    return False


def _claude_env_auth_available(environ: Mapping[str, str]) -> bool:
    return any(
        str(environ.get(key, "")).strip()
        for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    )


def _codex_auth_snapshot_source(*, environ: Mapping[str, str]) -> Path | None:
    global _CODEX_AUTH_SNAPSHOT_CANDIDATES, _CODEX_AUTH_SNAPSHOT_DIR, _CODEX_AUTH_SNAPSHOT_PATH
    candidate_tokens = tuple(candidate.as_posix() for candidate in _codex_home_candidates(environ=environ))
    if (
        _CODEX_AUTH_SNAPSHOT_PATH is not None
        and _CODEX_AUTH_SNAPSHOT_PATH.is_file()
        and _CODEX_AUTH_SNAPSHOT_CANDIDATES == candidate_tokens
    ):
        return _CODEX_AUTH_SNAPSHOT_PATH
    auth_source = _codex_auth_source(environ=environ)
    if auth_source is None:
        return None
    try:
        snapshot_dir = Path(tempfile.mkdtemp(prefix="odylith-benchmark-codex-auth-")).resolve()
        snapshot_path = snapshot_dir / "auth.json"
        shutil.copy2(auth_source, snapshot_path)
        with contextlib.suppress(OSError):
            snapshot_path.chmod(0o600)
    except OSError:
        return auth_source if auth_source.is_file() else None
    _CODEX_AUTH_SNAPSHOT_DIR = snapshot_dir
    _CODEX_AUTH_SNAPSHOT_PATH = snapshot_path
    _CODEX_AUTH_SNAPSHOT_CANDIDATES = candidate_tokens
    return snapshot_path


@contextlib.contextmanager
def _temporary_codex_home(
    *,
    execution_contract: Mapping[str, str],
    repo_root: Path,
    environ: Mapping[str, str] | None = None,
) -> Iterator[Path]:
    env = dict(os.environ if environ is None else environ)
    if _execution_provider(execution_contract) == "claude-cli":
        with _temporary_claude_home(
            execution_contract=execution_contract,
            repo_root=repo_root,
            environ=env,
        ) as home_root:
            yield home_root
        return
    auth_source = _codex_auth_snapshot_source(environ=env)
    if auth_source is None:
        checked = ", ".join((candidate / "auth.json").as_posix() for candidate in _codex_home_candidates(environ=env))
        raise RuntimeError(
            "Codex CLI auth is unavailable; checked "
            f"{checked or '`~/.codex/auth.json`'} and cannot run live benchmark scenarios."
        )
    with _temporary_benchmark_temp_dir(
        repo_root=repo_root,
        prefix="odylith-benchmark-codex-home-",
    ) as home_root:
        codex_home = (home_root / ".codex").resolve()
        codex_home.mkdir(parents=True, exist_ok=True)
        shutil.copy2(auth_source, codex_home / "auth.json")
        (codex_home / "config.toml").write_text(
            _minimal_codex_config_text(execution_contract=execution_contract),
            encoding="utf-8",
        )
        yield home_root


@contextlib.contextmanager
def _temporary_claude_home(
    *,
    execution_contract: Mapping[str, str],
    repo_root: Path,
    environ: Mapping[str, str] | None = None,
) -> Iterator[Path]:
    env = dict(os.environ if environ is None else environ)
    auth_sources = _claude_auth_sources(environ=env)
    user_settings = _user_claude_config(environ=env)
    has_api_key_helper = bool(str(user_settings.get("apiKeyHelper", "")).strip())
    if not auth_sources and not has_api_key_helper and not _claude_env_auth_available(env):
        checked = ", ".join(candidate.as_posix() for candidate in _claude_home_candidates(environ=env))
        raise RuntimeError(
            "Claude CLI auth is unavailable; checked "
            f"{checked or '`~/.claude`, `~/.claude.json`, and `~/Library/Application Support/Claude/buddy-tokens.json`'} "
            "and cannot run live benchmark scenarios."
        )
    with _temporary_benchmark_temp_dir(
        repo_root=repo_root,
        prefix="odylith-benchmark-claude-home-",
    ) as home_root:
        claude_home = (home_root / ".claude").resolve()
        claude_home.mkdir(parents=True, exist_ok=True)
        auto_memory_directory = (home_root / "claude-auto-memory").resolve()
        auto_memory_directory.mkdir(parents=True, exist_ok=True)
        settings_path = (claude_home / "settings.json").resolve()
        settings_path.write_text(
            json.dumps(
                _minimal_claude_settings(
                    execution_contract=execution_contract,
                    auto_memory_directory=str(auto_memory_directory),
                    user_settings=user_settings,
                ),
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        claude_json = auth_sources.get("claude_json")
        if isinstance(claude_json, Path) and claude_json.is_file():
            target = (home_root / ".claude.json").resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(claude_json, target)
        buddy_tokens = auth_sources.get("buddy_tokens")
        if isinstance(buddy_tokens, Path) and buddy_tokens.is_file():
            target = (home_root / "Library" / "Application Support" / "Claude" / "buddy-tokens.json").resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(buddy_tokens, target)
        yield home_root
def _odylith_focus_lines(prompt_payload: Mapping[str, Any] | None) -> list[str]:
    return odylith_benchmark_live_prompt.odylith_focus_lines(prompt_payload)


def _sandbox_validation_command(*, repo_root: Path, command: str) -> str:
    token = str(command or "").strip()
    if not token:
        return ""
    tool_bin = str(odylith_benchmark_isolation.benchmark_tool_bin(repo_root=Path(repo_root).resolve()))
    token = re.sub(r"(?<!\S)(?:\./)?\.venv/bin/", f"{tool_bin}/", token)
    match = _LEADING_ENV_AND_ODYLITH_COMMAND.match(token)
    if match is not None:
        prefix = str(match.group("prefix") or "")
        if "PYTHONPATH=" not in prefix:
            prefix = f"{prefix}PYTHONPATH=src "
        token = f"{prefix}{tool_bin}/python src/odylith/cli.py{match.group('suffix')}"
    return token


def _sandbox_validation_commands(*, repo_root: Path, commands: Sequence[str]) -> list[str]:
    return _dedupe_strings(
        _sandbox_validation_command(repo_root=repo_root, command=str(token).strip())
        for token in commands
        if str(token).strip()
    )


def _agent_prompt(
    *,
    scenario: Mapping[str, Any],
    mode: str,
    prompt_payload: Mapping[str, Any],
    validation_commands: Sequence[str] | None = None,
) -> str:
    return odylith_benchmark_live_prompt.build_agent_prompt(
        scenario=scenario,
        mode=mode,
        prompt_payload=prompt_payload,
        validation_commands=validation_commands,
    )


def _estimated_initial_prompt_tokens(prompt: str) -> int:
    encoded = str(prompt or "").encode("utf-8")
    if not encoded:
        return 0
    return max(1, len(encoded) // 4)


def _codex_exec_command(
    *,
    execution_contract: Mapping[str, str],
    workspace_root: Path,
    schema_path: Path,
    output_path: Path,
) -> list[str]:
    if _execution_provider(execution_contract) == "claude-cli":
        return _claude_exec_command(
            execution_contract=execution_contract,
            workspace_root=workspace_root,
            schema_path=schema_path,
        )
    codex_bin = odylith_reasoning.resolve_codex_bin(execution_contract.get("codex_bin", "codex"))
    if not _host_binary_available(codex_bin):
        raise RuntimeError(f"Codex CLI binary `{codex_bin}` is not available.")
    command = [
        codex_bin,
        "exec",
        "--disable",
        "plugins",
        "--disable",
        "multi_agent",
        "--disable",
        "personality",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "never",
        "--json",
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
        "-C",
        str(workspace_root),
    ]
    model = str(execution_contract.get("model", "")).strip()
    if model:
        command.extend(["--model", model])
    reasoning_effort = _normalize_codex_cli_reasoning_effort(execution_contract.get("reasoning_effort", "high"))
    if reasoning_effort:
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
    command.append("-")
    return command


def _claude_exec_command(
    *,
    execution_contract: Mapping[str, str],
    workspace_root: Path,
    schema_path: Path,
) -> list[str]:
    claude_bin = odylith_reasoning.resolve_claude_bin(_execution_bin(execution_contract))
    if not _host_binary_available(claude_bin):
        raise RuntimeError(f"Claude CLI binary `{claude_bin}` is not available.")
    command = [
        claude_bin,
        "-p",
        (
            "Read the full benchmark task prompt from stdin. Work only inside the current repository. "
            "Use only the allowed local tools and return only JSON matching the provided schema."
        ),
        "--output-format",
        "stream-json",
        "--verbose",
        "--input-format",
        "text",
        "--permission-mode",
        "bypassPermissions",
        "--max-turns",
        "12",
        "--no-session-persistence",
        "--setting-sources",
        "user",
        "--tools",
        _CLAUDE_ALLOWED_TOOLS,
        "--json-schema",
        str(schema_path),
    ]
    model = str(execution_contract.get("model", "")).strip()
    if model:
        command.extend(["--model", model])
    reasoning_effort = _normalize_claude_cli_reasoning_effort(execution_contract.get("reasoning_effort", "high"))
    if reasoning_effort:
        command.extend(["--effort", reasoning_effort])
    return command


def _live_codex_sandbox(scenario: Mapping[str, Any]) -> str:
    requested = str(scenario.get("live_sandbox", "")).strip()
    if requested in {"read-only", "workspace-write"}:
        return requested
    # Live agents need writable temp/cache space even for analysis-only scenarios.
    # Unexpected repo edits are still measured through candidate_write_paths.
    return "workspace-write"


def _precision_metrics(
    *,
    required_paths: Sequence[str],
    supporting_paths: Sequence[str] = (),
    observed_paths: Sequence[str],
    expected_write_paths: Sequence[str],
    candidate_write_paths: Sequence[str],
) -> dict[str, Any]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    supporting = {str(token).strip() for token in supporting_paths if str(token).strip()}
    relevant = required.union(supporting)
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    expected_write = {str(token).strip() for token in expected_write_paths if str(token).strip()}
    candidate_write = {str(token).strip() for token in candidate_write_paths if str(token).strip()}

    observed_supporting = sorted(supporting.intersection(observed))
    observed_relevant = sorted(relevant.intersection(observed))
    hallucinated_surfaces = sorted(observed.difference(relevant))
    required_path_precision = (
        round(len(observed_relevant) / max(1, len(observed)), 3)
        if observed
        else 1.0
        if not relevant
        else 0.0
    )
    hallucinated_surface_rate = (
        round(len(hallucinated_surfaces) / max(1, len(observed)), 3)
        if observed
        else 0.0
    )

    matched_write_paths = sorted(expected_write.intersection(candidate_write))
    unnecessary_widening_paths = sorted(candidate_write.difference(expected_write))
    write_surface_precision = (
        round(len(matched_write_paths) / max(1, len(candidate_write)), 3)
        if candidate_write
        else 1.0
        if not expected_write
        else 0.0
    )
    unnecessary_widening_rate = (
        round(len(unnecessary_widening_paths) / max(1, len(candidate_write)), 3)
        if candidate_write
        else 0.0
    )

    return {
        "observed_path_count": len(observed),
        "supporting_path_count": len(supporting),
        "supporting_path_hits": observed_supporting,
        "required_path_precision_basis": "required_plus_supporting_paths" if supporting else "required_paths",
        "required_path_precision": required_path_precision,
        "hallucinated_surface_count": len(hallucinated_surfaces),
        "hallucinated_surface_rate": hallucinated_surface_rate,
        "hallucinated_surfaces": hallucinated_surfaces[:12],
        "expected_write_path_count": len(expected_write),
        "candidate_write_path_count": len(candidate_write),
        "candidate_write_paths": sorted(candidate_write)[:12],
        "write_surface_precision": write_surface_precision,
        "unnecessary_widening_count": len(unnecessary_widening_paths),
        "unnecessary_widening_rate": unnecessary_widening_rate,
        "unnecessary_widening_paths": unnecessary_widening_paths[:12],
    }


def _scenario_allows_noop_completion(*, scenario: Mapping[str, Any]) -> bool:
    return bool(scenario.get("allow_noop_completion"))


def _validator_result_passed(result: Mapping[str, Any]) -> bool:
    return str(result.get("status", "")).strip() in {"passed", "not_applicable"}


def _validator_short_circuit_result(*, status_basis: str, reason: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "status_basis": str(status_basis).strip() or "validator_short_circuit",
        "reason": str(reason).strip() or "validator_short_circuit",
        "duration_ms": 0.0,
        "results": [],
        "passed_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "timeout_count": 0,
    }


def _focused_checks_cover_validation_commands(*, scenario: Mapping[str, Any]) -> bool:
    focused_checks = _dedupe_strings(
        [str(token).strip() for token in scenario.get("focused_local_checks", []) if str(token).strip()]
        if isinstance(scenario.get("focused_local_checks"), list)
        else []
    )
    validation_commands = _dedupe_strings(
        [str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()]
        if isinstance(scenario.get("validation_commands"), list)
        else []
    )
    return bool(focused_checks) and focused_checks == validation_commands


def _failed_validator_command_signatures(result: Mapping[str, Any]) -> set[tuple[str, int]]:
    rows = result.get("results")
    if not isinstance(rows, list):
        return set()
    signatures: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("status", "")).strip() != "failed":
            continue
        command = str(row.get("command", "")).strip()
        if not command:
            continue
        try:
            exit_code = int(row.get("exit_code", 0) or 0)
        except (TypeError, ValueError):
            exit_code = 0
        signatures.add((command, exit_code))
    return signatures


def _focused_check_failure_matches_validator_failure(
    *,
    focused_check_result: Mapping[str, Any],
    validator_result: Mapping[str, Any],
) -> bool:
    if _validator_result_passed(focused_check_result) or _validator_result_passed(validator_result):
        return False
    focused_failures = _failed_validator_command_signatures(focused_check_result)
    validator_failures = _failed_validator_command_signatures(validator_result)
    return bool(focused_failures) and focused_failures.issubset(validator_failures)


def _focused_noop_validator_proxy_allowed(
    *,
    scenario: Mapping[str, Any],
    structured_output: Mapping[str, Any],
    candidate_write_paths: Sequence[str],
    required_path_misses: Sequence[str],
    focused_check_result: Mapping[str, Any],
    validator_result: Mapping[str, Any],
) -> bool:
    if not _scenario_allows_noop_completion(scenario=scenario):
        return False
    if not (
        _focused_checks_cover_validation_commands(scenario=scenario)
        or str(scenario.get("family", "")).strip() == "governed_surface_sync"
    ):
        return False
    if any(str(token).strip() for token in candidate_write_paths):
        return False
    if any(str(token).strip() for token in required_path_misses):
        return False
    if not (
        _validator_result_passed(focused_check_result)
        or _focused_check_failure_matches_validator_failure(
            focused_check_result=focused_check_result,
            validator_result=validator_result,
        )
    ):
        return False
    if _validator_result_passed(validator_result):
        return False
    explanation = _structured_output_text(structured_output).lower()
    validator_rows = validator_result.get("results")
    validator_text_parts: list[str] = []
    if isinstance(validator_rows, list):
        for row in validator_rows:
            if not isinstance(row, Mapping):
                continue
            validator_text_parts.extend(
                [
                    str(row.get("stdout_tail", "")).strip().lower(),
                    str(row.get("stderr_tail", "")).strip().lower(),
                ]
            )
    validator_text = " ".join(token for token in validator_text_parts if token)
    out_of_slice_markers = (
        "out-of-slice workspace drift",
        "outside the permitted writable slice",
        "outside the allowed edit slice",
        "outside the allowed working set",
        "outside this task slice",
        "outside the task slice",
        "outside the allowed bounded scope",
        "outside the bounded scope",
        "outside the allowed slice",
        "outside the grounded slice",
        "outside the slice",
        "benchmark boundary",
        "enforced slice boundary",
        "no minimal in-slice edit",
        "no minimal in slice edit",
    )
    drift_markers = (
        "pre-existing",
        "stale",
        "missing",
        "out-of-scope",
        "out of scope",
        "unrelated",
    )
    outside_boundary_matches = bool(
        explanation
        and "outside" in explanation
        and any(
            token in explanation
            for token in (
                "allowed",
                "permitted",
                "slice",
                "working set",
                "boundary",
                "file",
                "files",
            )
        )
    )
    summary_matches = explanation and (
        any(marker in explanation for marker in out_of_slice_markers) or outside_boundary_matches
    ) and any(marker in explanation for marker in drift_markers)
    validator_tail_matches = False
    if str(scenario.get("family", "")).strip() == "governed_surface_sync":
        validator_tail_matches = (
            "without rewriting governed truth" in validator_text
            and (
                "odylith/registry/source/components/" in validator_text
                or "odylith/technical-plans/in-progress/" in validator_text
            )
        )
    return bool(summary_matches or validator_tail_matches)


def _focused_noop_preflight_short_circuit_allowed(
    *,
    scenario: Mapping[str, Any],
    focused_check_result: Mapping[str, Any],
) -> bool:
    if not _scenario_allows_noop_completion(scenario=scenario):
        return False
    if not (
        _focused_checks_cover_validation_commands(scenario=scenario)
        or str(scenario.get("family", "")).strip() == "governed_surface_sync"
    ):
        return False
    return _validator_result_passed(focused_check_result)


def _focused_noop_short_circuit_output(
    *,
    scenario: Mapping[str, Any],
    focused_check_commands: Sequence[str],
) -> dict[str, Any]:
    family = str(scenario.get("family", "")).strip()
    summary = (
        "No file changes were needed. The declared focused validator evidence already proves the bounded contract on the current tree."
    )
    if family == "guidance_behavior":
        summary = (
            "No file changes were needed. The declared focused validator evidence already proves the grounded guidance contract on the current tree."
        )
    return {
        "status": "completed",
        "summary": summary,
        "changed_files": [],
        "validation_commands_run": [
            str(token).strip()
            for token in focused_check_commands
            if str(token).strip()
        ],
        "validation_summary": "focused_local_checks_passed_noop",
        "notes": [
            "Odylith treated the passing focused local checks as the valid no-op proof for this allow-noop slice.",
        ],
    }


def _write_expectation_satisfied(
    *,
    scenario: Mapping[str, Any],
    candidate_write_paths: Sequence[str],
    validators_passed: bool,
) -> bool:
    expected_write_paths = _scenario_expected_write_paths(scenario)
    if not expected_write_paths:
        return True
    if any(str(token).strip() for token in candidate_write_paths):
        return True
    return _scenario_allows_noop_completion(scenario=scenario) and validators_passed


def _successful_noop_precision_metrics(
    *,
    scenario: Mapping[str, Any],
    precision_metrics: Mapping[str, Any],
    candidate_write_paths: Sequence[str],
    validators_passed: bool,
) -> dict[str, Any]:
    if not _scenario_allows_noop_completion(scenario=scenario) or not validators_passed:
        return dict(precision_metrics)
    if any(str(token).strip() for token in candidate_write_paths):
        return dict(precision_metrics)
    rows = dict(precision_metrics)
    rows["expected_write_path_count"] = 0
    rows["candidate_write_path_count"] = 0
    rows["candidate_write_paths"] = []
    rows["write_surface_precision"] = 1.0
    rows["unnecessary_widening_count"] = 0
    rows["unnecessary_widening_rate"] = 0.0
    rows["unnecessary_widening_paths"] = []
    return rows


def _structured_output_text(structured_output: Mapping[str, Any]) -> str:
    rows = dict(structured_output or {})
    parts = [
        str(rows.get("summary", "")).strip(),
        str(rows.get("validation_summary", "")).strip(),
    ]
    notes = rows.get("notes")
    if isinstance(notes, list):
        parts.extend(str(token).strip() for token in notes if str(token).strip())
    return " ".join(token for token in parts if token).strip()


def _validator_backed_completion_satisfied(
    *,
    scenario: Mapping[str, Any],
    structured_output: Mapping[str, Any],
    status: str,
    candidate_write_paths: Sequence[str],
    validators_passed: bool,
    required_path_misses: Sequence[str],
) -> bool:
    if not validators_passed:
        return False
    if any(str(token).strip() for token in required_path_misses):
        return False
    normalized_status = str(status or "").strip().lower()
    if normalized_status == "completed":
        return True
    if normalized_status != "blocked":
        return False
    explanation = _structured_output_text(structured_output).lower()
    if not explanation:
        return False
    has_write_paths = any(str(token).strip() for token in candidate_write_paths)
    if has_write_paths:
        environment_noise_markers = (
            "sandbox",
            "permissionerror",
            "importerror",
            "import error",
            "workspace import",
            "missing in the workspace",
            "absent in the workspace",
            "temp root",
            "temp-root",
            "temp directory",
            "temp-directory",
            "cleanup failure",
            "cleanup failures",
            "benchmark harness",
        )
        out_of_slice_markers = (
            "outside the edited slice",
            "outside the slice",
            "outside this bounded slice",
            "outside the bounded slice",
            "outside the grounded slice",
            "outside the allowed slice",
            "outside the approved files",
            "appears unrelated",
            "left untouched",
            "unrelated modifications",
            "unrelated worktree changes",
        )
        return any(marker in explanation for marker in environment_noise_markers) and any(
            marker in explanation for marker in out_of_slice_markers
        )
    if not _scenario_allows_noop_completion(scenario=scenario):
        return False
    if str(scenario.get("family", "")).strip() == "release_publication":
        publication_noop_markers = (
            "already reflect the validated report",
            "already reflects the validated report",
            "publication docs already reflect",
            "copied artifacts already reflect",
            "no publication changes were needed",
            "no benchmark publication changes were needed",
            "no benchmark doc changes were needed",
            "no changes to the publication docs were needed",
        )
        if any(marker in explanation for marker in publication_noop_markers):
            return True
    benign_noop_markers = (
        "no file changes",
        "no files were changed",
        "no changes were needed",
        "already satisfies",
        "already match",
        "already matches",
        "already fixed",
        "already consistent",
        "current tree already satisfies",
        "grounded tree already satisfies",
        "preserve current truth",
        "bounded",
        "out of scope",
        "out-of-scope",
        "unrelated",
        "pre-existing",
        "stale",
    )
    return any(marker in explanation for marker in benign_noop_markers)


def _validator_is_recursive(cmd: str) -> bool:
    token = str(cmd or "").strip().lower()
    return "odylith benchmark" in token


def _run_validators(
    *,
    workspace_root: Path,
    commands: Sequence[str],
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    rows: list[dict[str, Any]] = []
    duration_ms = 0.0
    timeout_seconds = _validator_timeout_seconds(environ=environ)
    for raw in commands:
        command = str(raw or "").strip()
        if not command:
            continue
        if _validator_is_recursive(command):
            rows.append(
                {
                    "command": command,
                    "status": "skipped",
                    "reason": "recursive_benchmark_validator",
                    "exit_code": None,
                    "duration_ms": 0.0,
                    "stdout_tail": "",
                    "stderr_tail": "",
                }
            )
            continue
        if not workspace.is_dir():
            rows.append(
                {
                    "command": command,
                    "status": "failed",
                    "reason": "workspace_root_missing",
                    "exit_code": None,
                    "duration_ms": 0.0,
                    "stdout_tail": "",
                    "stderr_tail": f"Benchmark workspace is missing: {workspace}",
                }
            )
            continue
        started_at = time.perf_counter()
        reason = ""
        try:
            completed = _run_subprocess_capture(
                command=["/bin/bash", "-c", command],
                cwd=workspace,
                env=dict(environ or os.environ),
                timeout_seconds=timeout_seconds,
            )
            status = "passed" if int(completed.returncode or 0) == 0 else "failed"
            exit_code: int | None = int(completed.returncode or 0)
            stdout_tail = str(completed.stdout or "")[-4000:]
            stderr_tail = str(completed.stderr or "")[-4000:]
        except subprocess.TimeoutExpired as exc:
            status = "timeout"
            exit_code = None
            stdout_tail = str(getattr(exc, "stdout", "") or "")[-4000:]
            stderr_tail = str(getattr(exc, "stderr", "") or "")[-4000:]
        except FileNotFoundError as exc:
            status = "failed"
            reason = "workspace_root_missing"
            exit_code = None
            stdout_tail = ""
            stderr_tail = str(exc)[-4000:]
        duration = round((time.perf_counter() - started_at) * 1000.0, 3)
        duration_ms += duration
        row = {
            "command": command,
            "status": status,
            "exit_code": exit_code,
            "duration_ms": duration,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
        if reason:
            row["reason"] = reason
        rows.append(row)
    statuses = [str(row.get("status", "")).strip() for row in rows]
    blocking_statuses = [token for token in statuses if token != "skipped"]
    if not rows or not blocking_statuses:
        overall = "not_applicable"
    elif all(token == "passed" for token in blocking_statuses):
        overall = "passed"
    else:
        overall = "failed"
    return {
        "status": overall,
        "duration_ms": round(duration_ms, 3),
        "results": rows,
        "passed_count": sum(1 for token in statuses if token == "passed"),
        "failed_count": sum(1 for token in statuses if token == "failed"),
        "skipped_count": sum(1 for token in statuses if token == "skipped"),
        "timeout_count": sum(1 for token in statuses if token == "timeout"),
    }


def _structured_output(output_path: Path, *, stream_text: str = "") -> dict[str, Any]:
    if not output_path.is_file():
        payload = _structured_output_from_events(_parse_json_lines(stream_text))
        if payload is not None:
            return payload
        rows = _normalized_structured_output_payload(
            odylith_reasoning._parse_structured_mapping_text(stream_text)  # noqa: SLF001
        )
        if rows is not None:
            return rows
        return {
            "status": "failed",
            "summary": "Host CLI did not emit a schema-valid final JSON message.",
            "changed_files": [],
            "validation_commands_run": [],
            "validation_summary": "missing_schema_output",
            "notes": [],
        }
    rows = _normalized_structured_output_payload(
        odylith_reasoning._parse_structured_mapping_file(output_path)  # noqa: SLF001
    )
    if rows is not None:
        return rows
    payload = _structured_output_from_events(_parse_json_lines(stream_text))
    if payload is not None:
        return payload
    rows = _normalized_structured_output_payload(
        odylith_reasoning._parse_structured_mapping_text(stream_text)  # noqa: SLF001
    )
    if rows is not None:
        return rows
    return {
        "status": "failed",
        "summary": "Host CLI final JSON output was unreadable.",
        "changed_files": [],
        "validation_commands_run": [],
        "validation_summary": "invalid_schema_output",
        "notes": [],
    }


def _live_orchestration_summary(
    *,
    execution_contract: Mapping[str, str] | None = None,
    mode: str,
    packet_source: str,
    required_path_recall: float,
    precision_metrics: Mapping[str, Any],
    benchmark_session_namespace: str = "",
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    packet_present = normalized_mode == "odylith_on"
    requires_widening = float(precision_metrics.get("unnecessary_widening_rate", 0.0) or 0.0) > 0.0
    session_namespace = str(benchmark_session_namespace or "").strip()
    runner = _execution_runner(dict(execution_contract or {}))
    return {
        "native_mode": runner,
        "mode": runner,
        "delegate": False,
        "leaf_count": 0,
        "native_leaf_count": 0,
        "parallel_safety": "local_only",
        "manual_review_recommended": False,
        "clamped_no_fanout": False,
        "local_only_reasons": ["benchmark_live_host_cli"],
        "odylith_adoption": {
            "packet_present": packet_present,
            "auto_grounding_applied": packet_present,
            "requires_widening": requires_widening,
            "grounded": bool(required_path_recall > 0.0 or packet_present),
            "grounded_delegate": False,
            "workspace_daemon_reused": False,
            "session_namespace": session_namespace,
            "session_namespaced": bool(session_namespace),
            "mixed_local_fallback": False,
            "grounding_source": packet_source if packet_present else "none",
            "operation": runner,
            "runtime_source": "benchmark_live_runner",
            "runtime_transport": _execution_transport(dict(execution_contract or {})),
        },
    }


_provision_workspace_odylith_root = odylith_benchmark_isolation.provision_workspace_odylith_root
_overlay_workspace_repo_snapshot = odylith_benchmark_isolation.overlay_workspace_repo_snapshot
_capture_workspace_validator_truth = odylith_benchmark_isolation.capture_workspace_validator_truth
_restore_workspace_validator_truth = odylith_benchmark_isolation.restore_workspace_validator_truth
_sandbox_process_env = odylith_benchmark_isolation.sandbox_process_env
_scenario_workspace_self_reference_strip_paths = (
    odylith_benchmark_isolation.scenario_workspace_self_reference_strip_paths
)
_workspace_strip_paths = odylith_benchmark_isolation.workspace_strip_paths


def _live_workspace_preserve_paths(
    *,
    explicit_task_paths: Sequence[str],
    snapshot_paths: Sequence[str] | None,
) -> list[str]:
    return _dedupe_strings(
        [
            *[str(token).strip() for token in explicit_task_paths if str(token).strip()],
            *[str(token).strip() for token in (snapshot_paths or ()) if str(token).strip()],
        ]
    )


_BENCHMARK_RUNTIME_VALIDATOR_TEST_NAMES = frozenset(
    {
        "test_odylith_benchmark_completion_semantics.py",
        "test_odylith_benchmark_context_engine.py",
        "test_odylith_benchmark_corpus.py",
        "test_odylith_benchmark_execution_engine.py",
        "test_odylith_benchmark_graphs.py",
        "test_odylith_benchmark_isolation.py",
        "test_odylith_benchmark_live_diagnostics.py",
        "test_odylith_benchmark_live_execution.py",
        "test_odylith_benchmark_preflight.py",
        "test_odylith_benchmark_prompt_payloads.py",
        "test_odylith_benchmark_prompt_regressions.py",
        "test_odylith_benchmark_proof_discipline.py",
        "test_odylith_benchmark_publication.py",
        "test_odylith_benchmark_runner.py",
        "test_odylith_benchmark_runtime_posture_runtime.py",
        "test_odylith_benchmark_shard_merge.py",
        "test_execution_engine.py",
    }
)
_BENCHMARK_RUNTIME_VALIDATOR_SUPPORT_PATHS = (
    "src/odylith/__init__.py",
    "src/odylith/cli.py",
    "src/odylith/runtime",
)
_SESSION_BRIEF_VALIDATOR_SUPPORT_PATHS = (
    ".odylith/runtime/odylith-compiler/projection-snapshot.v1.json",
)
_VALIDATION_COMMAND_REPO_PATH = re.compile(
    r"(?P<path>(?:\.odylith|docs|odylith|src|tests)/[A-Za-z0-9_./{}@%+=:,~-]+)"
)


def _scenario_command_rows(scenario: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    for key in ("validation_commands", "focused_local_checks"):
        raw_rows = scenario.get(key, [])
        if not isinstance(raw_rows, list):
            continue
        rows.extend(str(token).strip() for token in raw_rows if str(token).strip())
    return _dedupe_strings(rows)


def _repo_paths_from_validation_commands(*, repo_root: Path, scenario: Mapping[str, Any]) -> list[str]:
    root = Path(repo_root).resolve()
    rows: list[str] = []
    for command in _scenario_command_rows(scenario):
        for match in _VALIDATION_COMMAND_REPO_PATH.finditer(command):
            token = str(match.group("path") or "").strip()
            if not token:
                continue
            token = token.split("::", 1)[0].rstrip(".,;:)]}'\"")
            if token and (root / token).exists():
                rows.append(token)
    return _dedupe_strings(rows)


def _benchmark_live_validator_support_paths(*, repo_root: Path, scenario: Mapping[str, Any]) -> list[str]:
    commands = _scenario_command_rows(scenario)
    root = Path(repo_root).resolve()
    rows: list[str] = []
    runtime_validator = any(
        test_name in command for command in commands for test_name in _BENCHMARK_RUNTIME_VALIDATOR_TEST_NAMES
    ) or any(
        "tests/unit/runtime/" in command for command in commands
    )
    if runtime_validator:
        rows.extend(_BENCHMARK_RUNTIME_VALIDATOR_SUPPORT_PATHS)
        rows.extend(_repo_paths_from_validation_commands(repo_root=root, scenario=scenario))
    if str(scenario.get("scenario_id", "")).strip() == "session-brief-runtime-path-ambiguity" or any(
        "session_brief_exact_path" in command for command in commands
    ):
        rows.extend(_SESSION_BRIEF_VALIDATOR_SUPPORT_PATHS)
    return [
        path
        for path in _dedupe_strings(rows)
        if (root / path).is_file() or (root / path).is_dir()
    ]


def _benchmark_temp_root(*, repo_root: Path) -> Path:
    root = (Path(repo_root).resolve() / ".odylith" / "runtime" / "odylith-benchmark-temp").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cleanup_benchmark_temp_dir(path: Path) -> None:
    target = Path(path)
    last_error: OSError | None = None
    for attempt in range(_BENCHMARK_TEMP_CLEANUP_RETRY_COUNT + 1):
        try:
            shutil.rmtree(target)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            if exc.errno not in _BENCHMARK_TEMP_CLEANUP_RETRYABLE_ERRNOS:
                break
            if attempt >= _BENCHMARK_TEMP_CLEANUP_RETRY_COUNT:
                break
            time.sleep(_BENCHMARK_TEMP_CLEANUP_RETRY_DELAY_SECONDS)
    if last_error is None:
        return
    with contextlib.suppress(OSError, FileNotFoundError):
        shutil.rmtree(target, ignore_errors=True)


@contextlib.contextmanager
def _temporary_benchmark_temp_dir(
    *,
    repo_root: Path,
    prefix: str,
) -> Iterator[Path]:
    temp_root = _benchmark_temp_root(repo_root=repo_root)
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(temp_root))).resolve()
    try:
        yield temp_dir
    finally:
        _cleanup_benchmark_temp_dir(temp_dir)


def _run_live_scenario_once(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
    benchmark_profile: str = "",
    benchmark_session_namespace: str = "",
    packet_source: str,
    prompt_payload: Mapping[str, Any] | None = None,
    packet_summary: Mapping[str, Any] | None = None,
    snapshot_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    if not _is_public_live_mode(normalized_mode):
        raise ValueError(f"Unsupported live benchmark mode: {mode}")
    resolved_repo_root = Path(repo_root).resolve()
    config = odylith_reasoning.reasoning_config_from_env(repo_root=resolved_repo_root)
    execution_contract = _resolved_live_execution_contract(repo_root=resolved_repo_root, config=config)
    execution_provider = _execution_provider(execution_contract)
    execution_host_family = _execution_host_family(execution_contract)
    resolved_host_bin = _execution_bin(execution_contract)
    reasoning_effort = _normalize_live_cli_reasoning_effort(
        execution_provider,
        execution_contract.get("reasoning_effort", "high"),
        default="high",
    )
    resolved_model = str(execution_contract.get("model", "")).strip()
    runner_name = _execution_runner(execution_contract)
    normalized_benchmark_profile = str(benchmark_profile or "").strip().lower()
    live_timeout_seconds, live_timeout_policy = _resolved_live_timeout_budget(
        scenario=scenario,
        benchmark_profile=normalized_benchmark_profile,
    )
    explicit_task_paths = [
        *[str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()],
        *[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
        *[str(token).strip() for token in scenario.get("supporting_paths", []) if str(token).strip()],
        *_benchmark_live_validator_support_paths(repo_root=resolved_repo_root, scenario=scenario),
    ]
    effective_snapshot_paths = _live_workspace_preserve_paths(
        explicit_task_paths=explicit_task_paths,
        snapshot_paths=snapshot_paths,
    )
    strip_paths = _workspace_strip_paths(repo_root=resolved_repo_root, preserve_paths=effective_snapshot_paths)
    strip_paths.extend(
        _scenario_workspace_self_reference_strip_paths(
            repo_root=resolved_repo_root,
            scenario=scenario,
            preserve_paths=effective_snapshot_paths,
        )
    )
    with _temporary_worktree(
        repo_root=repo_root,
        strip_paths=strip_paths,
        snapshot_paths=effective_snapshot_paths,
    ) as workspace_pair, _call_with_supported_kwargs(
        _temporary_codex_home,
        execution_contract=execution_contract,
        repo_root=resolved_repo_root,
    ) as host_home_root, _temporary_benchmark_temp_dir(
        repo_root=resolved_repo_root,
        prefix="odylith-benchmark-host-",
    ) as temp_root:
        workspace_root, validator_truth_root = workspace_pair
        sandbox_root = (temp_root / "sandbox").resolve()
        schema_path = temp_root / "schema.json"
        output_path = temp_root / "result.json"
        schema_path.write_text(json.dumps(_LIVE_RESULT_SCHEMA, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        sandbox_validation_commands = _sandbox_validation_commands(
            repo_root=repo_root,
            commands=[str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()],
        )
        command = _codex_exec_command(
            execution_contract=execution_contract,
            workspace_root=workspace_root,
            schema_path=schema_path,
            output_path=output_path,
        )
        sandbox = _live_codex_sandbox(scenario)
        if "--skip-git-repo-check" in command:
            command[command.index("--skip-git-repo-check")] = "--sandbox"
            command.insert(command.index("--sandbox") + 1, sandbox)
            command.insert(command.index("--sandbox") + 2, "--skip-git-repo-check")
        command_env = _sandbox_process_env(
            repo_root=repo_root,
            execution_contract=execution_contract,
            host_home_root=host_home_root,
            sandbox_root=sandbox_root,
        )
        started_at = time.perf_counter()
        focused_check_commands = _sandbox_validation_commands(
            repo_root=repo_root,
            commands=odylith_benchmark_live_diagnostics.focused_local_check_commands(
                focused_local_checks=[
                    str(token).strip()
                    for token in scenario.get("focused_local_checks", [])
                    if str(token).strip()
                ]
                if isinstance(scenario.get("focused_local_checks"), list)
                else []
            ),
        )
        focused_check_result: dict[str, Any] = {
            "status": "not_applicable",
            "duration_ms": 0.0,
            "results": [],
            "passed_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "timeout_count": 0,
        }
        preflight_evidence_mode = "none"
        preflight_evidence_commands: list[str] = []
        prompt_payload_rows = dict(prompt_payload or {})
        if normalized_mode == "odylith_on" and focused_check_commands:
            preflight_evidence_mode = "scenario_declared_focused_local_checks"
            preflight_evidence_commands = list(focused_check_commands)
            _restore_workspace_validator_truth(
                truth_root=validator_truth_root,
                workspace_root=workspace_root,
                strip_paths=strip_paths,
            )
            focused_check_result = _run_validators(
                workspace_root=workspace_root,
                commands=focused_check_commands,
                environ=command_env,
            )
            _apply_strip_paths(
                workspace_root=workspace_root,
                strip_paths=strip_paths,
            )
            focused_check_result_lines = odylith_benchmark_live_diagnostics.focused_local_check_result_lines(
                result=focused_check_result
            )
            if focused_check_result_lines:
                prompt_payload_rows["focused_local_check_results"] = focused_check_result_lines
        preflight_noop_short_circuit = bool(
            normalized_mode == "odylith_on"
            and _focused_noop_preflight_short_circuit_allowed(
                scenario=scenario,
                focused_check_result=focused_check_result,
            )
        )
        workspace_status_baseline = _workspace_git_status_snapshot(workspace_root=workspace_root)
        prompt = _agent_prompt(
            scenario=scenario,
            mode=normalized_mode,
            prompt_payload=prompt_payload_rows,
            validation_commands=sandbox_validation_commands,
        )
        live_timed_out = False
        if preflight_noop_short_circuit:
            completed = subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
            stderr_tail = ""
            agent_duration_ms = 0.0
            events = []
            usage = {}
            structured_output = _focused_noop_short_circuit_output(
                scenario=scenario,
                focused_check_commands=focused_check_commands,
            )
        else:
            try:
                completed = _run_subprocess_capture(
                    command=command,
                    cwd=workspace_root,
                    env=command_env,
                    input_text=prompt,
                    timeout_seconds=live_timeout_seconds,
                )
                stderr_tail = str(completed.stderr or "")[-4000:]
            except subprocess.TimeoutExpired as exc:
                live_timed_out = True
                completed = subprocess.CompletedProcess(
                    args=command,
                    returncode=124,
                    stdout=str(getattr(exc, "stdout", "") or ""),
                    stderr=str(getattr(exc, "stderr", "") or ""),
                )
                stderr_tail = str(getattr(exc, "stderr", "") or "")[-4000:]
            except OSError as exc:
                completed = subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="",
                    stderr=str(exc),
                )
                stderr_tail = str(exc)[-4000:]
            agent_duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
            events = _parse_json_lines(str(completed.stdout or ""))
            usage = _usage_from_events(events)
            structured_output = _structured_output(output_path, stream_text=str(completed.stdout or ""))
        required_paths = [str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()]
        prompt_supplied_paths = [
            token
            for token in _prompt_supplied_paths_from_commands(
                workspace_root=workspace_root,
                commands=[*sandbox_validation_commands, *focused_check_commands],
            )
            if token not in set(required_paths)
        ]
        raw_prompt_visible_paths = (
            odylith_benchmark_live_diagnostics.raw_prompt_visible_paths(
                repo_root=repo_root,
                raw_prompt={
                    "prompt": str(scenario.get("prompt", "")).strip(),
                    "acceptance_criteria": [
                        str(token).strip()
                        for token in scenario.get("acceptance_criteria", [])
                        if str(token).strip()
                    ],
                },
            )
            if normalized_mode != "odylith_on"
            else []
        )
        preflight_command_paths = _prompt_supplied_paths_from_commands(
            workspace_root=workspace_root,
            commands=[*sandbox_validation_commands, *focused_check_commands],
        )
        preflight_command_paths = _meaningful_preflight_command_paths(
            scenario=scenario,
            command_paths=preflight_command_paths,
        )
        observed_path_details = _observed_path_details_from_events(
            events=events,
            workspace_root=workspace_root,
            structured_output=structured_output,
            prompt_payload=prompt_payload_rows,
            raw_prompt_visible_paths=raw_prompt_visible_paths,
            excluded_commands=[*sandbox_validation_commands, *focused_check_commands],
            neutral_paths=prompt_supplied_paths,
        )
        observed_paths = list(observed_path_details.get("paths", []))
        observed_path_sources = [
            str(token).strip()
            for token in observed_path_details.get("sources", [])
            if str(token).strip()
        ]
        if preflight_noop_short_circuit:
            if preflight_command_paths:
                observed_paths = _dedupe_strings([*observed_paths, *preflight_command_paths])
                observed_path_sources = _dedupe_strings([*observed_path_sources, "command_text"])
        required_path_recall, required_path_misses = _path_recall(
            required_paths=required_paths,
            observed_paths=observed_paths,
        )
        _critical_recall, critical_path_misses = _path_recall(
            required_paths=[str(token).strip() for token in scenario.get("critical_paths", []) if str(token).strip()],
            observed_paths=observed_paths,
        )
        candidate_write_paths = _candidate_write_paths(
            events=events,
            workspace_root=workspace_root,
            structured_output=structured_output,
        )
        candidate_write_paths = _meaningful_candidate_write_paths(candidate_write_paths)
        expected_write_paths = _scenario_expected_write_paths(scenario)
        supporting_paths = _scenario_supporting_paths(scenario)
        if preflight_noop_short_circuit and preflight_command_paths:
            # Validator-backed no-op proof should treat the named local validator
            # anchors as supporting evidence, not as hallucinated surface drift.
            supporting_paths = _dedupe_strings([*supporting_paths, *preflight_command_paths])
        precision_metrics = _precision_metrics(
            required_paths=required_paths,
            supporting_paths=supporting_paths,
            observed_paths=observed_paths,
            expected_write_paths=expected_write_paths,
            candidate_write_paths=candidate_write_paths,
        )
        failure_tracked_paths = odylith_benchmark_live_diagnostics.failure_artifact_paths(
            scenario=scenario,
            effective_snapshot_paths=effective_snapshot_paths,
            observed_paths=observed_paths,
            candidate_write_paths=candidate_write_paths,
            structured_output=structured_output,
            strip_paths=strip_paths,
        )
        workspace_state_post_codex = odylith_benchmark_live_diagnostics.workspace_state_diff(
            repo_root=resolved_repo_root,
            workspace_root=workspace_root,
            tracked_paths=failure_tracked_paths,
        )
        candidate_write_paths = _dedupe_strings(
            [
                *candidate_write_paths,
                *_workspace_state_delta_paths(
                    baseline=workspace_status_baseline,
                    workspace_root=workspace_root,
                    workspace_state=workspace_state_post_codex,
                    ignored_paths=strip_paths,
                ),
            ]
        )
        candidate_write_paths = _meaningful_candidate_write_paths(candidate_write_paths)
        precision_metrics = _precision_metrics(
            required_paths=required_paths,
            supporting_paths=supporting_paths,
            observed_paths=observed_paths,
            expected_write_paths=expected_write_paths,
            candidate_write_paths=candidate_write_paths,
        )
        if preflight_noop_short_circuit:
            workspace_state_pre_validator = dict(workspace_state_post_codex)
            validator_result = dict(focused_check_result)
            validator_result["status"] = "passed"
            validator_result["status_basis"] = "focused_noop_short_circuit"
            validator_result["proxy_from"] = "focused_local_checks"
        elif live_timed_out:
            workspace_state_pre_validator = dict(workspace_state_post_codex)
            validator_result = _validator_short_circuit_result(
                status_basis="live_timeout_short_circuit",
                reason="skipped_due_to_live_timeout",
            )
        else:
            _restore_workspace_validator_truth(
                truth_root=validator_truth_root,
                workspace_root=workspace_root,
                strip_paths=strip_paths,
            )
            workspace_state_pre_validator = odylith_benchmark_live_diagnostics.workspace_state_diff(
                repo_root=resolved_repo_root,
                workspace_root=workspace_root,
                tracked_paths=failure_tracked_paths,
            )
            validator_result = _run_validators(
                workspace_root=workspace_root,
                commands=sandbox_validation_commands,
                environ=command_env,
            )
        effective_validator_result = dict(validator_result)
        if not preflight_noop_short_circuit and not live_timed_out and _focused_noop_validator_proxy_allowed(
            scenario=scenario,
            structured_output=structured_output,
            candidate_write_paths=candidate_write_paths,
            required_path_misses=required_path_misses,
            focused_check_result=focused_check_result,
            validator_result=validator_result,
        ):
            effective_validator_result = dict(validator_result)
            effective_validator_result["status"] = "passed"
            effective_validator_result["status_basis"] = "focused_noop_proxy"
            effective_validator_result["proxy_from"] = "focused_local_checks"
        status = str(structured_output.get("status", "")).strip().lower()
        if status not in _STATUS_VALUES:
            status = "failed"
        validators_passed = _validator_result_passed(effective_validator_result)
        precision_metrics = _successful_noop_precision_metrics(
            scenario=scenario,
            precision_metrics=precision_metrics,
            candidate_write_paths=candidate_write_paths,
            validators_passed=validators_passed,
        )
        validator_backed_completion = _validator_backed_completion_satisfied(
            scenario=scenario,
            structured_output=structured_output,
            status=status,
            candidate_write_paths=candidate_write_paths,
            validators_passed=validators_passed,
            required_path_misses=required_path_misses,
        )
        expectation_ok = bool(
            (status == "completed" or validator_backed_completion)
            and not required_path_misses
            and validators_passed
            and _write_expectation_satisfied(
                scenario=scenario,
                candidate_write_paths=candidate_write_paths,
                validators_passed=validators_passed,
            )
        )
        within_budget = float(precision_metrics.get("unnecessary_widening_rate", 0.0) or 0.0) == 0.0
        total_latency_ms = round(agent_duration_ms + float(effective_validator_result.get("duration_ms", 0.0) or 0.0), 3)
        timing_trace = {
            "operations": {
                "live_host_exec": {
                    "duration_ms": agent_duration_ms,
                    "stage_timings": {
                        "focused_local_checks": float(focused_check_result.get("duration_ms", 0.0) or 0.0),
                        "host_exec": agent_duration_ms,
                    },
                },
                "validators": {
                    "duration_ms": float(effective_validator_result.get("duration_ms", 0.0) or 0.0),
                    "stage_timings": {
                        "validators": float(effective_validator_result.get("duration_ms", 0.0) or 0.0),
                    },
                },
            }
        }
        prompt_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        total_tokens = prompt_tokens + output_tokens
        initial_prompt_tokens = _estimated_initial_prompt_tokens(prompt)
        selected_doc_paths = odylith_benchmark_live_diagnostics.prompt_payload_selected_docs(
            prompt_payload=prompt_payload_rows
        )
        token_basis = "host_exec_input_tokens"
        validator_status = str(effective_validator_result.get("status", "")).strip()
        live_execution_payload: dict[str, Any] = {
            "command": command,
            "exit_code": int(completed.returncode or 0),
            "structured_output": structured_output,
            "stdout_tail": str(completed.stdout or "")[-4000:],
            "stderr_tail": stderr_tail,
            "provider": execution_provider,
            "host_family": execution_host_family,
            "runner": runner_name,
            "bin": resolved_host_bin,
            "codex_bin": resolved_host_bin if execution_provider == "codex-cli" else "",
            "claude_bin": resolved_host_bin if execution_provider == "claude-cli" else "",
            "model": resolved_model,
            "reasoning_effort": reasoning_effort,
            "benchmark_profile": normalized_benchmark_profile,
            "sandbox": sandbox,
            "timeout_seconds": live_timeout_seconds,
            "timeout_policy": live_timeout_policy,
            "timed_out": live_timed_out,
            "latency_measurement_basis": "validated_task_cycle",
            "isolated_host_home": True,
            "isolated_codex_home": execution_provider == "codex-cli",
            "workspace_odylith_isolated": True,
            "workspace_venv_symlinked": False,
            "sandboxed_validation_commands": True,
            "sandboxed_cache_env": True,
            "project_doc_injection_disabled": True,
            "plugins_disabled": execution_provider == "codex-cli",
            "mcp_disabled": execution_provider == "codex-cli",
            "multi_agent_disabled": execution_provider == "codex-cli",
            "repo_guidance_removed": ["AGENTS.md", "CLAUDE.md", ".cursor/", ".windsurf/", ".codex/"],
            "effective_snapshot_paths": list(effective_snapshot_paths),
            "focused_local_checks": focused_check_result,
            "preflight_evidence_mode": preflight_evidence_mode,
            "preflight_evidence_commands": preflight_evidence_commands,
            "preflight_evidence_result_status": str(focused_check_result.get("status", "")).strip()
            or "not_applicable",
            "observed_path_sources": observed_path_sources,
            "validator_execution_mode": (
                "focused_noop_short_circuit"
                if preflight_noop_short_circuit
                else "skipped_due_to_live_timeout"
                if live_timed_out
                else "executed"
            ),
        }
        if status != "completed" or not validators_passed:
            live_execution_payload["failure_artifacts"] = {
                "tracked_paths": failure_tracked_paths,
                "workspace_state_post_codex": workspace_state_post_codex,
                "workspace_state_pre_validator": workspace_state_pre_validator,
            }
        packet = (
            {
                str(key).strip(): value
                for key, value in packet_summary.items()
                if str(key).strip()
            }
            if isinstance(packet_summary, Mapping)
            else {}
        )
        packet.update(
            {
                "within_budget": within_budget,
                "route_ready": expectation_ok,
                "live_status": status,
            }
        )
        return {
            "kind": str(scenario.get("kind", "")).strip() or "packet",
            "mode": normalized_mode,
            "packet_source": packet_source if normalized_mode == "odylith_on" else _RAW_HOST_CLI,
            "execution_contract": dict(execution_contract),
            "latency_ms": total_latency_ms,
            "instrumented_reasoning_duration_ms": agent_duration_ms,
            "uninstrumented_overhead_ms": float(validator_result.get("duration_ms", 0.0) or 0.0),
            "packet": packet,
            "expectation_ok": expectation_ok,
            "expectation_details": {
                "live_runner": True,
                "host_status": status,
                "codex_status": status,
                "validator_status": str(effective_validator_result.get("status", "")).strip() or "not_applicable",
                "validator_status_basis": str(effective_validator_result.get("status_basis", "")).strip()
                or "validator_result",
                "structured_summary": str(structured_output.get("summary", "")).strip(),
                "validator_backed_noop_completion": bool(
                    validator_backed_completion and not any(str(token).strip() for token in candidate_write_paths)
                ),
                "validator_backed_completion": validator_backed_completion,
            },
            "required_path_recall": required_path_recall,
            "required_path_misses": required_path_misses,
            "critical_path_misses": critical_path_misses,
            "observed_paths": observed_paths[:12],
            "observed_path_sources": observed_path_sources,
            "observed_path_count": int(precision_metrics.get("observed_path_count", 0) or 0),
            "required_path_precision": float(precision_metrics.get("required_path_precision", 0.0) or 0.0),
            "hallucinated_surface_count": int(precision_metrics.get("hallucinated_surface_count", 0) or 0),
            "hallucinated_surface_rate": float(precision_metrics.get("hallucinated_surface_rate", 0.0) or 0.0),
            "hallucinated_surfaces": list(precision_metrics.get("hallucinated_surfaces", [])),
            "expected_write_path_count": int(precision_metrics.get("expected_write_path_count", 0) or 0),
            "candidate_write_path_count": int(precision_metrics.get("candidate_write_path_count", 0) or 0),
            "candidate_write_paths": list(precision_metrics.get("candidate_write_paths", [])),
            "write_surface_precision": float(precision_metrics.get("write_surface_precision", 0.0) or 0.0),
            "unnecessary_widening_count": int(precision_metrics.get("unnecessary_widening_count", 0) or 0),
            "unnecessary_widening_rate": float(precision_metrics.get("unnecessary_widening_rate", 0.0) or 0.0),
            "unnecessary_widening_paths": list(precision_metrics.get("unnecessary_widening_paths", [])),
            "selected_doc_count": len(selected_doc_paths),
            "selected_test_count": 0,
            "selected_command_count": len(_command_events(events)),
            "strict_gate_command_count": len(
                [str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()]
            ),
            "effective_estimated_tokens": prompt_tokens,
            "effective_token_basis": token_basis,
            "initial_prompt_estimated_tokens": initial_prompt_tokens,
            "initial_prompt_token_basis": "utf8_bytes_div4",
            "host_prompt_estimated_tokens": prompt_tokens,
            "host_prompt_input_tokens": prompt_tokens,
            "host_cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
            "host_output_tokens": output_tokens,
            "codex_prompt_estimated_tokens": prompt_tokens,
            "codex_prompt_input_tokens": prompt_tokens,
            "codex_cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
            "codex_output_tokens": output_tokens,
            "total_payload_estimated_tokens": total_tokens,
            "total_model_tokens": total_tokens,
            "runtime_contract_estimated_tokens": 0,
            "operator_diag_estimated_tokens": 0,
            "prompt_artifact_tokens": {runner_name: prompt_tokens},
            "runtime_contract_artifact_tokens": {},
            "operator_diag_artifact_tokens": {},
            "selector_diagnostics": {},
            "adaptive_escalation": {
                "stage": runner_name,
                "initial_source": packet_source if normalized_mode == "odylith_on" else _RAW_HOST_CLI,
                "final_source": packet_source if normalized_mode == "odylith_on" else _RAW_HOST_CLI,
                "auto_escalated": False,
                "reasons": [],
            },
            "validation_success_proxy": 1.0 if validator_status in {"passed", "not_applicable"} else 0.0,
            "validation_results": effective_validator_result,
            "preflight_evidence_mode": preflight_evidence_mode,
            "preflight_evidence_commands": preflight_evidence_commands,
            "preflight_evidence_result_status": str(focused_check_result.get("status", "")).strip()
            or "not_applicable",
            "full_scan": {},
            "orchestration": _live_orchestration_summary(
                execution_contract=execution_contract,
                mode=normalized_mode,
                packet_source=packet_source,
                required_path_recall=required_path_recall,
                precision_metrics=precision_metrics,
                benchmark_session_namespace=benchmark_session_namespace,
            ),
            "timing_trace": timing_trace,
            "live_execution": live_execution_payload,
        }


def _retryable_live_host_interruption(result: Mapping[str, Any]) -> bool:
    live_execution = result.get("live_execution", {})
    if not isinstance(live_execution, Mapping):
        return False
    try:
        exit_code = int(live_execution.get("exit_code", 0) or 0)
    except (TypeError, ValueError):
        exit_code = 0
    if exit_code >= 0 or bool(live_execution.get("timed_out", False)):
        return False
    structured_output = live_execution.get("structured_output", {})
    validation_summary = (
        str(structured_output.get("validation_summary", "")).strip()
        if isinstance(structured_output, Mapping)
        else ""
    )
    try:
        candidate_write_path_count = int(result.get("candidate_write_path_count", 0) or 0)
    except (TypeError, ValueError):
        candidate_write_path_count = 0
    return validation_summary == "missing_schema_output" and candidate_write_path_count == 0


def run_live_scenario(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
    benchmark_profile: str = "",
    benchmark_session_namespace: str = "",
    packet_source: str,
    prompt_payload: Mapping[str, Any] | None = None,
    packet_summary: Mapping[str, Any] | None = None,
    snapshot_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    first_result = _run_live_scenario_once(
        repo_root=repo_root,
        scenario=scenario,
        mode=mode,
        benchmark_profile=benchmark_profile,
        benchmark_session_namespace=benchmark_session_namespace,
        packet_source=packet_source,
        prompt_payload=prompt_payload,
        packet_summary=packet_summary,
        snapshot_paths=snapshot_paths,
    )
    if not _retryable_live_host_interruption(first_result):
        return first_result

    retry_result = _run_live_scenario_once(
        repo_root=repo_root,
        scenario=scenario,
        mode=mode,
        benchmark_profile=benchmark_profile,
        benchmark_session_namespace=benchmark_session_namespace,
        packet_source=packet_source,
        prompt_payload=prompt_payload,
        packet_summary=packet_summary,
        snapshot_paths=snapshot_paths,
    )
    live_execution = retry_result.get("live_execution")
    if isinstance(live_execution, dict):
        replaced_live_execution = first_result.get("live_execution", {})
        live_execution["infra_retry_attempts"] = 1
        live_execution["infra_retry_reason"] = "negative_host_exit_missing_schema_output"
        if isinstance(replaced_live_execution, Mapping):
            live_execution["infra_retry_replaced_exit_code"] = replaced_live_execution.get("exit_code", 0)
            live_execution["infra_retry_replaced_timed_out"] = bool(replaced_live_execution.get("timed_out", False))
    return retry_result


__all__ = [
    "run_live_scenario",
]
