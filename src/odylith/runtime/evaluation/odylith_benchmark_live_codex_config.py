"""Codex-home and execution-contract helpers for live benchmark runs."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import tomllib
from typing import Any, Mapping

from odylith.runtime.reasoning import odylith_reasoning


_CODEX_REASONING_EFFORT_VALUES = frozenset({"low", "medium", "high", "xhigh"})


def normalize_codex_cli_reasoning_effort(value: Any, *, default: str = "high") -> str:
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


def codex_home_candidates(*, environ: Mapping[str, str] | None = None) -> list[Path]:
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


def user_codex_home(*, environ: Mapping[str, str] | None = None) -> Path:
    env = dict(os.environ if environ is None else environ)
    for candidate in codex_home_candidates(environ=env):
        if candidate.is_dir():
            return candidate
    candidates = codex_home_candidates(environ=env)
    if candidates:
        return candidates[0]
    return (Path.home() / ".codex").resolve()


def codex_auth_source(*, environ: Mapping[str, str] | None = None) -> Path | None:
    for codex_home in codex_home_candidates(environ=environ):
        auth_path = (codex_home / "auth.json").resolve()
        if auth_path.is_file():
            return auth_path
    return None


def repo_reasoning_payload(*, repo_root: Path) -> dict[str, Any]:
    return _read_json_mapping((Path(repo_root).resolve() / odylith_reasoning.DEFAULT_REASONING_CONFIG_PATH).resolve())


def user_codex_config(*, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    return _read_toml_mapping((user_codex_home(environ=environ) / "config.toml").resolve())


def resolved_live_execution_contract(
    *,
    repo_root: Path,
    config: odylith_reasoning.ReasoningConfig,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if environ is None else environ)
    repo_payload = repo_reasoning_payload(repo_root=repo_root)
    model = (
        str(env.get("ODYLITH_REASONING_MODEL", "")).strip()
        or str(repo_payload.get("model", "")).strip()
        or str(config.model or "").strip()
    )
    reasoning_effort = normalize_codex_cli_reasoning_effort(
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


def minimal_codex_config_text(*, execution_contract: Mapping[str, str]) -> str:
    lines: list[str] = []
    model = str(execution_contract.get("model", "")).strip()
    if model:
        lines.append(f'model = {json.dumps(model)}')
    reasoning_effort = normalize_codex_cli_reasoning_effort(
        execution_contract.get("reasoning_effort", "high"),
    )
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
