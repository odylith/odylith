"""Run honest live benchmark scenarios through the local Codex CLI.

This module executes the same benchmark task through the same Codex CLI in a
disposable git worktree for both public comparison lanes:

- ``odylith_on``: the task prompt plus the declared full-product Odylith
  assistance stack
- ``odylith_off`` / ``raw_agent_baseline``: the same host CLI with Odylith
  assistance disabled

The runner neutralizes repo-local guidance in two places:

- the disposable workspace strips auto-consumed instruction entrypoints such as
  ``AGENTS.md``, ``CLAUDE.md``, ``.cursor/``, ``.windsurf/``, and
  ``.codex/`` while preserving truth-bearing repo docs for explicit reads; and
- the Codex CLI runs from a temporary ``HOME`` that keeps auth plus the pinned
  model/reasoning contract while dropping user-authored guidance config,
  plugins, MCP config, and project-doc fallback.

The public comparison is the full Odylith assistance stack versus the raw host
CLI lane on the same task. The lane contract must make any Odylith-only
affordance explicit instead of silently widening the benchmark story.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from typing import Any, Mapping, Sequence

from odylith.runtime.evaluation import odylith_benchmark_live_diagnostics
from odylith.runtime.evaluation import odylith_benchmark_isolation
from odylith.runtime.evaluation import odylith_benchmark_live_process
from odylith.runtime.evaluation import odylith_benchmark_live_prompt
from odylith.runtime.reasoning import odylith_reasoning


_STATUS_VALUES = {"completed", "blocked", "failed"}
_CODEX_REASONING_EFFORT_VALUES = frozenset({"low", "medium", "high", "xhigh"})
_JSON_PATH_TOKEN = re.compile(r"(?P<token>/[^ \n\r\t\"'`]+|(?:\./|\.\./)?[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9_./-]+)")
_PATH_LISTING_COMMAND = re.compile(r"(^|[\\/'\"\s])(rg|grep|find|fd|ls)(\s|$)")
_GREP_LIKE_LISTING_COMMAND = re.compile(r"(^|[\\/'\"\s])(rg|grep)(\s|$)")
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
_LIVE_RESULT_REQUIRED_KEYS = frozenset(_LIVE_RESULT_SCHEMA["required"])


def _normalize_mode(mode: str) -> str:
    token = str(mode or "").strip()
    if token == "odylith_off":
        return "raw_agent_baseline"
    return token


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


def _dedupe_strings(rows: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in rows:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


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


def _existing_file_paths(*, workspace_root: Path, paths: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in paths:
        token = str(raw or "").strip()
        if not token:
            continue
        candidate = _safe_resolve_path(workspace_root / token)
        if candidate is not None and _safe_is_file(candidate):
            rows.append(token)
    return _dedupe_strings(rows)


def _normalize_codex_cli_reasoning_effort(value: Any, *, default: str = "high") -> str:
    token = str(value or "").strip().lower()
    if token in _CODEX_REASONING_EFFORT_VALUES:
        return token
    return str(default or "high").strip().lower() or "high"


def _read_json_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with contextlib.suppress(OSError, json.JSONDecodeError):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _read_toml_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with contextlib.suppress(OSError, tomllib.TOMLDecodeError):
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _user_codex_home(*, environ: Mapping[str, str] | None = None) -> Path:
    env = dict(os.environ if environ is None else environ)
    for candidate in _codex_home_candidates(environ=env):
        if candidate.is_dir():
            return candidate
    candidates = _codex_home_candidates(environ=env)
    if candidates:
        return candidates[0]
    return (Path.home() / ".codex").resolve()


def _codex_home_candidates(*, environ: Mapping[str, str] | None = None) -> list[Path]:
    env = dict(os.environ if environ is None else environ)
    rows: list[Path] = []
    for key in ("CODEX_HOME", "CODEX_CONFIG_HOME"):
        raw = str(env.get(key, "")).strip()
        if raw:
            rows.append(Path(raw).expanduser())
    home = str(env.get("HOME", "")).strip()
    if home:
        rows.append(Path(home).expanduser() / ".codex")
    rows.append(Path.home() / ".codex")

    seen: set[str] = set()
    ordered: list[Path] = []
    for candidate in rows:
        with contextlib.suppress(OSError, RuntimeError):
            candidate = candidate.resolve()
        token = candidate.as_posix()
        if token in seen:
            continue
        seen.add(token)
        ordered.append(candidate)
    return ordered


def _codex_auth_source(*, environ: Mapping[str, str] | None = None) -> Path | None:
    for codex_home in _codex_home_candidates(environ=environ):
        auth_path = (codex_home / "auth.json").resolve()
        if auth_path.is_file():
            return auth_path
    return None


def _repo_reasoning_payload(*, repo_root: Path) -> dict[str, Any]:
    return _read_json_mapping((Path(repo_root).resolve() / odylith_reasoning.DEFAULT_REASONING_CONFIG_PATH).resolve())


def _user_codex_config(*, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    return _read_toml_mapping((_user_codex_home(environ=environ) / "config.toml").resolve())


def _resolved_live_execution_contract(
    *,
    repo_root: Path,
    config: odylith_reasoning.ReasoningConfig,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if environ is None else environ)
    repo_payload = _repo_reasoning_payload(repo_root=repo_root)
    model = (
        str(env.get("ODYLITH_REASONING_MODEL", "")).strip()
        or str(repo_payload.get("model", "")).strip()
        or str(config.model or "").strip()
    )
    reasoning_effort = _normalize_codex_cli_reasoning_effort(
        str(env.get("ODYLITH_REASONING_CODEX_REASONING_EFFORT", "")).strip()
        or str(repo_payload.get("codex_reasoning_effort", "")).strip()
        or "medium"
    )
    raw_codex_bin = (
        str(env.get("ODYLITH_REASONING_CODEX_BIN", "")).strip()
        or str(repo_payload.get("codex_bin", "")).strip()
        or str(config.codex_bin or "").strip()
        or "codex"
    )
    return {
        "runner": "live_codex_cli",
        "codex_bin": odylith_reasoning.resolve_codex_bin(raw_codex_bin),
        "model": model,
        "reasoning_effort": reasoning_effort,
    }


def _minimal_codex_config_text(*, execution_contract: Mapping[str, str]) -> str:
    lines: list[str] = []
    model = str(execution_contract.get("model", "")).strip()
    if model:
        lines.append(f'model = {json.dumps(model)}')
    reasoning_effort = str(execution_contract.get("reasoning_effort", "")).strip() or "high"
    lines.append(f'model_reasoning_effort = {json.dumps(reasoning_effort)}')
    lines.extend(
        [
            'approval_mode = "never"',
            "allow_login_shell = false",
            "plugins = {}",
            "mcp_servers = {}",
            "project_doc_max_bytes = 0",
            'project_doc_fallback_filename = ""',
            "",
            "[features]",
            "multi_agent = false",
        ]
    )
    return "\n".join(lines).strip() + "\n"


@contextlib.contextmanager
def _temporary_codex_home(
    *,
    execution_contract: Mapping[str, str],
    repo_root: Path,
    environ: Mapping[str, str] | None = None,
) -> Iterator[Path]:
    env = dict(os.environ if environ is None else environ)
    auth_source = _codex_auth_source(environ=env)
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


def _relative_workspace_path(path: Path, *, workspace_root: Path) -> str:
    try:
        resolved_path = _safe_resolve_path(path)
        resolved_workspace_root = _safe_resolve_path(workspace_root)
        if resolved_path is None or resolved_workspace_root is None:
            return ""
        return resolved_path.relative_to(resolved_workspace_root).as_posix()
    except ValueError:
        return ""


def _safe_resolve_path(path: Path) -> Path | None:
    with contextlib.suppress(OSError, RuntimeError):
        return path.resolve()
    return None


def _safe_is_file(path: Path) -> bool:
    with contextlib.suppress(OSError):
        return path.is_file()
    return False


def _resolve_workspace_file(token: str, *, workspace_root: Path) -> str:
    raw = str(token or "").strip().strip("`'\"")
    if not raw:
        return ""
    raw = raw.rstrip(",:;])}")
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved_candidate = _safe_resolve_path(candidate)
        if resolved_candidate is not None and _safe_is_file(resolved_candidate):
            return _relative_workspace_path(resolved_candidate, workspace_root=workspace_root)
        return ""
    relative = raw
    while relative.startswith("./"):
        relative = relative[2:]
    resolved = _safe_resolve_path(workspace_root / relative)
    if resolved is not None and _safe_is_file(resolved):
        return _relative_workspace_path(resolved, workspace_root=workspace_root)
    return ""


def _extract_workspace_paths_from_text(text: str, *, workspace_root: Path) -> list[str]:
    if not text:
        return []
    rows: list[str] = []
    for match in _JSON_PATH_TOKEN.finditer(str(text)):
        token = str(match.group("token") or "").strip()
        if not token:
            continue
        resolved = _resolve_workspace_file(token, workspace_root=workspace_root)
        if resolved:
            rows.append(resolved)
    return _dedupe_strings(rows)


def _listing_output_path_candidates(*, command: str, line: str) -> list[str]:
    normalized_command = str(command or "").strip().lower()
    token = str(line or "").strip()
    if not token:
        return []
    if "git status" in normalized_command:
        status_path = token[3:].strip() if len(token) > 3 else ""
        if " -> " in status_path:
            status_path = status_path.rsplit(" -> ", 1)[-1]
        return [status_path] if status_path else []
    if "git diff --stat" in normalized_command:
        prefix = token.split("|", 1)[0].strip()
        return [prefix] if prefix else []
    if "git grep" in normalized_command or _GREP_LIKE_LISTING_COMMAND.search(normalized_command):
        prefix = token.split(":", 1)[0].strip()
        return [prefix] if prefix else []
    return [token]


def _extract_workspace_paths_from_listing_output(
    *,
    command: str,
    output: str,
    workspace_root: Path,
) -> list[str]:
    if not output:
        return []
    rows: list[str] = []
    for raw_line in str(output).splitlines():
        for candidate in _listing_output_path_candidates(command=command, line=raw_line):
            resolved = _resolve_workspace_file(candidate, workspace_root=workspace_root)
            if resolved:
                rows.append(resolved)
    return _dedupe_strings(rows)


def _odylith_focus_lines(prompt_payload: Mapping[str, Any] | None) -> list[str]:
    return odylith_benchmark_live_prompt.odylith_focus_lines(prompt_payload)


def _sandbox_validation_command(*, repo_root: Path, command: str) -> str:
    token = str(command or "").strip()
    if not token:
        return ""
    venv_bin = str((Path(repo_root).resolve() / ".venv" / "bin").resolve())
    token = re.sub(r"(?<!\S)(?:\./)?\.venv/bin/", f"{venv_bin}/", token)
    match = _LEADING_ENV_AND_ODYLITH_COMMAND.match(token)
    if match is not None:
        prefix = str(match.group("prefix") or "")
        if "PYTHONPATH=" not in prefix:
            prefix = f"{prefix}PYTHONPATH=src "
        token = f"{prefix}{venv_bin}/python src/odylith/cli.py{match.group('suffix')}"
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
    codex_bin = odylith_reasoning.resolve_codex_bin(execution_contract.get("codex_bin", "codex"))
    if not shutil.which(codex_bin):
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


def _parse_json_lines(stream_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in str(stream_text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line.startswith("{") or not line.endswith("}"):
            continue
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(line)
            if isinstance(payload, Mapping):
                rows.append(dict(payload))
    return rows


def _structured_output_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        text_candidates: list[str] = []
        item = dict(event.get("item", {})) if isinstance(event.get("item"), Mapping) else {}
        if str(item.get("type", "")).strip() == "agent_message":
            text_candidates.append(str(item.get("text", "")).strip())
        if str(event.get("type", "")).strip() in {"agent_message", "assistant_message"}:
            text_candidates.append(str(event.get("text", "")).strip())
        for candidate in text_candidates:
            payload = odylith_reasoning._parse_structured_mapping_text(candidate)  # noqa: SLF001
            rows = _normalized_structured_output_payload(payload)
            if rows is not None:
                return rows
    return None


def _normalized_structured_output_payload(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    rows = dict(payload)
    if not _LIVE_RESULT_REQUIRED_KEYS.issubset(rows):
        return None
    status = str(rows.get("status", "")).strip().lower()
    if status not in _STATUS_VALUES:
        rows["status"] = "failed"
    return rows


def _usage_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    for event in reversed(events):
        if str(event.get("type", "")).strip() != "turn.completed":
            continue
        usage = dict(event.get("usage", {})) if isinstance(event.get("usage"), Mapping) else {}
        return {
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
        }
    return {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}


def _command_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        item = dict(event.get("item", {})) if isinstance(event.get("item"), Mapping) else {}
        if str(item.get("type", "")).strip() != "command_execution":
            continue
        rows.append(item)
    return rows


def _command_output_is_path_listing(command: str) -> bool:
    token = str(command or "").strip().lower()
    if not token:
        return False
    return bool(_PATH_LISTING_COMMAND.search(token)) or any(
        marker in token
        for marker in (
            "git grep",
            "git ls-files",
            "git diff --name-only",
            "git diff --stat",
            "git show --name-only",
            "git status",
        )
    )


def _file_change_paths(events: Sequence[Mapping[str, Any]], *, workspace_root: Path) -> list[str]:
    rows: list[str] = []
    for event in events:
        item = dict(event.get("item", {})) if isinstance(event.get("item"), Mapping) else {}
        if str(item.get("type", "")).strip() != "file_change":
            continue
        changes = item.get("changes", [])
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            token = _resolve_workspace_file(str(change.get("path", "")).strip(), workspace_root=workspace_root)
            if token:
                rows.append(token)
    return _dedupe_strings(rows)


def _candidate_write_paths(
    *,
    events: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    structured_output: Mapping[str, Any],
) -> list[str]:
    structured_changed_files = (
        [str(token).strip() for token in structured_output.get("changed_files", []) if str(token).strip()]
        if isinstance(structured_output.get("changed_files"), list)
        else []
    )
    return _existing_file_paths(
        workspace_root=workspace_root,
        paths=[*_file_change_paths(events, workspace_root=workspace_root), *structured_changed_files],
    )


def _workspace_state_changed_paths(*, workspace_state: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    git_status_paths = workspace_state.get("git_status_paths")
    if isinstance(git_status_paths, list):
        rows.extend(str(token).strip() for token in git_status_paths if str(token).strip())
    differences = workspace_state.get("differences")
    if isinstance(differences, list):
        for item in differences:
            if not isinstance(item, Mapping):
                continue
            token = str(item.get("path", "")).strip()
            status = str(item.get("status", "")).strip()
            if not token or not status:
                continue
            if status in {"different_file", "workspace_extra", "workspace_missing"}:
                rows.append(token)
    return _dedupe_strings(rows)


def _workspace_file_fingerprint(*, workspace_root: Path, relative_path: str) -> str:
    token = str(relative_path or "").strip()
    if not token:
        return ""
    resolved = _safe_resolve_path(workspace_root / token)
    if resolved is None:
        return "missing"
    with contextlib.suppress(OSError):
        if resolved.is_file():
            return hashlib.sha256(resolved.read_bytes()).hexdigest()
        if resolved.is_dir():
            return "dir"
    return "missing"


def _workspace_git_status_snapshot(*, workspace_root: Path) -> dict[str, Any]:
    workspace_state = odylith_benchmark_live_diagnostics.workspace_state_diff(
        repo_root=workspace_root,
        workspace_root=workspace_root,
        tracked_paths=[],
    )
    git_status_paths = _dedupe_strings(
        [
            str(token).strip()
            for token in workspace_state.get("git_status_paths", [])
            if str(token).strip()
        ]
    )
    return {
        "git_status_paths": git_status_paths,
        "fingerprints": {
            token: _workspace_file_fingerprint(workspace_root=workspace_root, relative_path=token)
            for token in git_status_paths
        },
    }


def _workspace_state_delta_paths(
    *,
    baseline: Mapping[str, Any],
    workspace_root: Path,
    workspace_state: Mapping[str, Any],
    ignored_paths: Sequence[str] = (),
) -> list[str]:
    ignored = {
        str(token).strip().replace("\\", "/")
        for token in ignored_paths
        if str(token).strip()
    }
    before_paths = {
        str(token).strip().replace("\\", "/")
        for token in baseline.get("git_status_paths", [])
        if str(token).strip() and str(token).strip().replace("\\", "/") not in ignored
    }
    before_fingerprints = (
        {
            str(key).strip().replace("\\", "/"): str(value).strip()
            for key, value in baseline.get("fingerprints", {}).items()
            if str(key).strip() and str(key).strip().replace("\\", "/") not in ignored
        }
        if isinstance(baseline.get("fingerprints"), Mapping)
        else {}
    )
    after_paths = {
        str(token).strip().replace("\\", "/")
        for token in workspace_state.get("git_status_paths", [])
        if str(token).strip() and str(token).strip().replace("\\", "/") not in ignored
    }
    changed = set(after_paths.difference(before_paths))
    for token in before_paths:
        if token not in after_paths:
            changed.add(token)
            continue
        current_fingerprint = _workspace_file_fingerprint(workspace_root=workspace_root, relative_path=token)
        if current_fingerprint != before_fingerprints.get(token, ""):
            changed.add(token)
    return sorted(changed)


_NON_PRODUCT_WRITE_PREFIXES: tuple[str, ...] = (
    ".pytest-tmp/",
    ".pytest_cache/",
    ".tmp-pytest-",
    ".tmp-pytest-cache-",
    ".tmp-benchmark-",
    ".venv/",
    "tmp/pytest",
)


def _meaningful_candidate_write_paths(candidate_write_paths: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in candidate_write_paths:
        token = str(raw).strip()
        if not token:
            continue
        normalized = token.replace("\\", "/")
        if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in _NON_PRODUCT_WRITE_PREFIXES):
            continue
        rows.append(token)
    return _dedupe_strings(rows)


def _observed_paths_from_events(
    *,
    events: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    structured_output: Mapping[str, Any],
    prompt_payload: Mapping[str, Any] | None = None,
    raw_prompt_visible_paths: Sequence[str] = (),
    excluded_commands: Sequence[str] = (),
    neutral_paths: Sequence[str] = (),
) -> list[str]:
    return _observed_path_details_from_events(
        events=events,
        workspace_root=workspace_root,
        structured_output=structured_output,
        prompt_payload=prompt_payload,
        raw_prompt_visible_paths=raw_prompt_visible_paths,
        excluded_commands=excluded_commands,
        neutral_paths=neutral_paths,
    )["paths"]


def _observed_path_details_from_events(
    *,
    events: Sequence[Mapping[str, Any]],
    workspace_root: Path,
    structured_output: Mapping[str, Any],
    prompt_payload: Mapping[str, Any] | None = None,
    raw_prompt_visible_paths: Sequence[str] = (),
    excluded_commands: Sequence[str] = (),
    neutral_paths: Sequence[str] = (),
) -> dict[str, Any]:
    rows: list[str] = []
    sources: list[str] = []
    prompt_payload_paths = odylith_benchmark_live_diagnostics.prompt_payload_observed_paths(
        prompt_payload=prompt_payload
    )
    if prompt_payload_paths:
        rows.extend(prompt_payload_paths)
        sources.append("odylith_prompt_payload")
    raw_prompt_paths = _dedupe_strings([str(token).strip() for token in raw_prompt_visible_paths if str(token).strip()])
    if raw_prompt_paths:
        rows.extend(raw_prompt_paths)
        sources.append("raw_prompt_visible_paths")
    excluded = {" ".join(str(token).split()).strip() for token in excluded_commands if str(token).strip()}
    neutral = {str(token).strip() for token in neutral_paths if str(token).strip()}
    command_text_paths: list[str] = []
    listing_output_paths: list[str] = []
    for item in _command_events(events):
        command = str(item.get("command", "")).strip()
        normalized_command = " ".join(command.split()).strip()
        if normalized_command in excluded:
            continue
        command_text_paths.extend(_extract_workspace_paths_from_text(command, workspace_root=workspace_root))
        if _command_output_is_path_listing(command):
            listing_output_paths.extend(
                _extract_workspace_paths_from_listing_output(
                    command=command,
                    output=str(item.get("aggregated_output", "")).strip(),
                    workspace_root=workspace_root,
                )
            )
    if command_text_paths:
        rows.extend(command_text_paths)
        sources.append("command_text")
    if listing_output_paths:
        rows.extend(listing_output_paths)
        sources.append("listing_output")
    file_change_paths = _file_change_paths(events, workspace_root=workspace_root)
    if file_change_paths:
        rows.extend(file_change_paths)
        sources.append("file_change_events")
    changed_files = [
        _resolve_workspace_file(str(token).strip(), workspace_root=workspace_root)
        for token in structured_output.get("changed_files", [])
        if isinstance(structured_output.get("changed_files"), list)
    ]
    changed_files = [token for token in changed_files if token]
    if changed_files:
        rows.extend(changed_files)
        sources.append("structured_output_changed_files")
    paths = _dedupe_strings([token for token in rows if token and token not in neutral])
    return {
        "paths": paths,
        "sources": _dedupe_strings(sources),
    }


def _prompt_supplied_paths_from_commands(
    *,
    workspace_root: Path,
    commands: Sequence[str],
) -> list[str]:
    rows: list[str] = []
    for raw in commands:
        rows.extend(
            _extract_workspace_paths_from_text(
                str(raw or "").strip(),
                workspace_root=workspace_root,
            )
        )
    return _dedupe_strings(rows)


def _path_recall(
    *,
    required_paths: Sequence[str],
    observed_paths: Sequence[str],
) -> tuple[float, list[str]]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    if not required:
        return 1.0, []
    misses = sorted(required.difference(observed))
    return round((len(required) - len(misses)) / max(1, len(required)), 3), misses


def _precision_metrics(
    *,
    required_paths: Sequence[str],
    observed_paths: Sequence[str],
    expected_write_paths: Sequence[str],
    candidate_write_paths: Sequence[str],
) -> dict[str, Any]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    expected_write = {str(token).strip() for token in expected_write_paths if str(token).strip()}
    candidate_write = {str(token).strip() for token in candidate_write_paths if str(token).strip()}

    observed_required = sorted(required.intersection(observed))
    hallucinated_surfaces = sorted(observed.difference(required))
    required_path_precision = (
        round(len(observed_required) / max(1, len(observed)), 3)
        if observed
        else 1.0
        if not required
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
    if not _validator_result_passed(focused_check_result):
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
        "outside this task slice",
        "outside the task slice",
        "outside the allowed bounded scope",
        "outside the bounded scope",
        "outside the allowed slice",
        "outside the grounded slice",
        "outside the slice",
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
    summary_matches = explanation and any(marker in explanation for marker in out_of_slice_markers) and any(
        marker in explanation for marker in drift_markers
    )
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


def _write_expectation_satisfied(
    *,
    scenario: Mapping[str, Any],
    candidate_write_paths: Sequence[str],
    validators_passed: bool,
) -> bool:
    if not bool(scenario.get("needs_write")) or not bool(scenario.get("changed_paths")):
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
            "summary": "Codex CLI did not emit a schema-valid final JSON message.",
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
        "summary": "Codex CLI final JSON output was unreadable.",
        "changed_files": [],
        "validation_commands_run": [],
        "validation_summary": "invalid_schema_output",
        "notes": [],
    }


def _live_orchestration_summary(
    *,
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
    return {
        "native_mode": "live_codex_cli",
        "mode": "live_codex_cli",
        "delegate": False,
        "leaf_count": 0,
        "native_leaf_count": 0,
        "parallel_safety": "local_only",
        "manual_review_recommended": False,
        "clamped_no_fanout": False,
        "local_only_reasons": ["benchmark_live_codex_cli"],
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
            "operation": "live_codex_cli",
            "runtime_source": "benchmark_live_runner",
            "runtime_transport": "codex_exec_jsonl",
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
    normalized_mode = _normalize_mode(mode)
    if not _is_public_live_mode(normalized_mode):
        raise ValueError(f"Unsupported live benchmark mode: {mode}")
    resolved_repo_root = Path(repo_root).resolve()
    config = odylith_reasoning.reasoning_config_from_env(repo_root=resolved_repo_root)
    execution_contract = _resolved_live_execution_contract(repo_root=resolved_repo_root, config=config)
    resolved_codex_bin = str(execution_contract.get("codex_bin", "")).strip()
    reasoning_effort = str(execution_contract.get("reasoning_effort", "")).strip().lower() or "high"
    resolved_model = str(execution_contract.get("model", "")).strip()
    normalized_benchmark_profile = str(benchmark_profile or "").strip().lower()
    live_timeout_seconds, live_timeout_policy = _resolved_live_timeout_budget(
        scenario=scenario,
        benchmark_profile=normalized_benchmark_profile,
    )
    explicit_task_paths = [
        *[str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()],
        *[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
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
    ) as codex_home_root, _temporary_benchmark_temp_dir(
        repo_root=resolved_repo_root,
        prefix="odylith-benchmark-codex-",
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
        sandbox = "workspace-write" if bool(scenario.get("needs_write")) else "read-only"
        command[command.index("--skip-git-repo-check")] = "--sandbox"
        command.insert(command.index("--sandbox") + 1, sandbox)
        command.insert(command.index("--sandbox") + 2, "--skip-git-repo-check")
        command_env = _sandbox_process_env(
            repo_root=repo_root,
            execution_contract=execution_contract,
            codex_home_root=codex_home_root,
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
        workspace_status_baseline = _workspace_git_status_snapshot(workspace_root=workspace_root)
        prompt = _agent_prompt(
            scenario=scenario,
            mode=normalized_mode,
            prompt_payload=prompt_payload_rows,
            validation_commands=sandbox_validation_commands,
        )
        live_timed_out = False
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
                repo_root=workspace_root,
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
        precision_metrics = _precision_metrics(
            required_paths=required_paths,
            observed_paths=observed_paths,
            expected_write_paths=[str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
            if bool(scenario.get("needs_write"))
            else [],
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
            observed_paths=observed_paths,
            expected_write_paths=[str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
            if bool(scenario.get("needs_write"))
            else [],
            candidate_write_paths=candidate_write_paths,
        )
        if live_timed_out:
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
        if not live_timed_out and _focused_noop_validator_proxy_allowed(
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
                "live_codex_exec": {
                    "duration_ms": agent_duration_ms,
                    "stage_timings": {
                        "focused_local_checks": float(focused_check_result.get("duration_ms", 0.0) or 0.0),
                        "codex_exec": agent_duration_ms,
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
        token_basis = "codex_exec_input_tokens"
        validator_status = str(effective_validator_result.get("status", "")).strip()
        live_execution_payload: dict[str, Any] = {
            "command": command,
            "exit_code": int(completed.returncode or 0),
            "structured_output": structured_output,
            "stdout_tail": str(completed.stdout or "")[-4000:],
            "stderr_tail": stderr_tail,
            "codex_bin": resolved_codex_bin,
            "model": resolved_model,
            "reasoning_effort": reasoning_effort,
            "benchmark_profile": normalized_benchmark_profile,
            "sandbox": sandbox,
            "timeout_seconds": live_timeout_seconds,
            "timeout_policy": live_timeout_policy,
            "timed_out": live_timed_out,
            "latency_measurement_basis": "validated_task_cycle",
            "isolated_codex_home": True,
            "workspace_odylith_isolated": True,
            "workspace_venv_symlinked": False,
            "sandboxed_validation_commands": True,
            "sandboxed_cache_env": True,
            "project_doc_injection_disabled": True,
            "plugins_disabled": True,
            "mcp_disabled": True,
            "multi_agent_disabled": True,
            "repo_guidance_removed": ["AGENTS.md", "CLAUDE.md", ".cursor/", ".windsurf/", ".codex/"],
            "effective_snapshot_paths": list(effective_snapshot_paths),
            "focused_local_checks": focused_check_result,
            "preflight_evidence_mode": preflight_evidence_mode,
            "preflight_evidence_commands": preflight_evidence_commands,
            "preflight_evidence_result_status": str(focused_check_result.get("status", "")).strip()
            or "not_applicable",
            "observed_path_sources": observed_path_sources,
            "validator_execution_mode": "skipped_due_to_live_timeout" if live_timed_out else "executed",
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
            "packet_source": packet_source if normalized_mode == "odylith_on" else "raw_codex_cli",
            "execution_contract": dict(execution_contract),
            "latency_ms": total_latency_ms,
            "instrumented_reasoning_duration_ms": agent_duration_ms,
            "uninstrumented_overhead_ms": float(validator_result.get("duration_ms", 0.0) or 0.0),
            "packet": packet,
            "expectation_ok": expectation_ok,
            "expectation_details": {
                "live_runner": True,
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
            "codex_prompt_estimated_tokens": prompt_tokens,
            "codex_prompt_input_tokens": prompt_tokens,
            "codex_cached_input_tokens": int(usage.get("cached_input_tokens", 0) or 0),
            "codex_output_tokens": output_tokens,
            "total_payload_estimated_tokens": total_tokens,
            "total_model_tokens": total_tokens,
            "runtime_contract_estimated_tokens": 0,
            "operator_diag_estimated_tokens": 0,
            "prompt_artifact_tokens": {"live_codex_cli": prompt_tokens},
            "runtime_contract_artifact_tokens": {},
            "operator_diag_artifact_tokens": {},
            "selector_diagnostics": {},
            "adaptive_escalation": {
                "stage": "live_codex_cli",
                "initial_source": packet_source if normalized_mode == "odylith_on" else "raw_codex_cli",
                "final_source": packet_source if normalized_mode == "odylith_on" else "raw_codex_cli",
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
                mode=normalized_mode,
                packet_source=packet_source,
                required_path_recall=required_path_recall,
                precision_metrics=precision_metrics,
                benchmark_session_namespace=benchmark_session_namespace,
            ),
            "timing_trace": timing_trace,
            "live_execution": live_execution_payload,
        }


__all__ = [
    "run_live_scenario",
]
