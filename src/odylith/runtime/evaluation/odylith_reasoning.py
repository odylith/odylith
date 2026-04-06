"""Odylith reasoning adapter.

Odylith now owns the primary deep-reasoning contract. This module keeps
only the backend-agnostic configuration and optional provider wiring needed to
hand delivery dossiers into Tribunal. Tribunal remains the source of case
selection, actor adjudication, maintainer-brief generation, and packet
compilation.

The optional provider path stays bounded and advisory:
- deterministic Tribunal reasoning remains useful when no provider is present;
- provider configuration is backend-agnostic;
- provider output is intended to enrich selected case reasoning, never to
  mutate tracked files, approvals, or lifecycle state directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol, Sequence

from odylith.runtime.evaluation import tribunal_engine


DEFAULT_REASONING_PATH = tribunal_engine.DEFAULT_REASONING_PATH
DEFAULT_REASONING_CONFIG_PATH = ".odylith/reasoning.config.v1.json"
_REASONING_CONFIG_VERSION = "v1"
_KNOWN_REASONING_ENV_KEYS: tuple[str, ...] = (
    "ODYLITH_REASONING_MODE",
    "ODYLITH_REASONING_PROVIDER",
    "ODYLITH_REASONING_MODEL",
    "ODYLITH_REASONING_BASE_URL",
    "ODYLITH_REASONING_API_KEY",
    "ODYLITH_REASONING_API_KEY_ENV",
    "ODYLITH_REASONING_SCOPE_CAP",
    "ODYLITH_REASONING_TIMEOUT_SECONDS",
    "ODYLITH_REASONING_CODEX_BIN",
    "ODYLITH_REASONING_CODEX_REASONING_EFFORT",
    "ODYLITH_REASONING_CLAUDE_BIN",
    "ODYLITH_REASONING_CLAUDE_REASONING_EFFORT",
)
_DEFAULT_CODEX_BIN_CANDIDATES: tuple[Path, ...] = (
    Path("/Applications/Codex.app/Contents/Resources/codex"),
    Path("~/Applications/Codex.app/Contents/Resources/codex").expanduser(),
)
_DEFAULT_CLAUDE_BIN_CANDIDATES: tuple[Path, ...] = ()
_RELEASE_LANE_ENV_PREFIX = "ODYLITH_RELEASE_"
_LEGACY_CODEX_MODEL_ALIASES: frozenset[str] = frozenset(
    {
        "codex-spark 5.3",
        "codex spark 5.3",
    }
)


class ReasoningProvider(Protocol):
    """Provider-neutral structured-case enrichment interface."""

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Return a bounded case-enrichment payload or ``None`` when unavailable."""

    def generate_structured(self, *, request: "StructuredReasoningRequest") -> Mapping[str, Any] | None:
        """Return a bounded schema-constrained payload or ``None`` when unavailable."""


@dataclass(frozen=True)
class ReasoningConfig:
    """Environment-backed configuration for optional AI-assisted Tribunal passes."""

    mode: str
    provider: str
    model: str
    base_url: str
    api_key: str
    scope_cap: int
    timeout_seconds: float
    codex_bin: str = "codex"
    codex_reasoning_effort: str = "high"
    claude_bin: str = "claude"
    claude_reasoning_effort: str = "high"
    api_key_env: str = ""
    config_source: str = "defaults"
    config_path: str = ""


@dataclass(frozen=True)
class StructuredReasoningRequest:
    """Provider-neutral structured-output contract for bounded local narration."""

    system_prompt: str
    schema_name: str
    output_schema: Mapping[str, Any]
    prompt_payload: Mapping[str, Any]
    reasoning_effort: str = ""
    timeout_seconds: float = 0.0


def reasoning_config_path(*, repo_root: Path) -> Path:
    """Return the local-only persisted Odylith reasoning config path."""

    return (Path(repo_root).resolve() / DEFAULT_REASONING_CONFIG_PATH).resolve()


def _normalize_mode(value: Any) -> str:
    token = str(value or "auto").strip().lower()
    return token if token in {"disabled", "auto"} else "auto"


def _normalize_provider(value: Any) -> str:
    token = str(value or "auto-local").strip().lower()
    return token if token in {"auto-local", "openai-compatible", "codex-cli", "claude-cli"} else "auto-local"


def _normalize_string(value: Any, *, default: str = "") -> str:
    token = str(value or "").strip()
    return token if token else str(default or "").strip()


def _normalize_scope_cap(value: Any, *, default: int = 5) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return max(1, int(default))


def _normalize_timeout_seconds(value: Any, *, default: float = 20.0) -> float:
    try:
        return max(1.0, float(value))
    except (TypeError, ValueError):
        return max(1.0, float(default))


def _normalize_codex_reasoning_effort(value: Any) -> str:
    token = str(value or "high").strip().lower()
    return token if token in {"low", "medium", "high"} else "high"


def _normalize_claude_reasoning_effort(value: Any) -> str:
    token = str(value or "high").strip().lower()
    return token if token in {"low", "medium", "high", "max"} else "high"


def _normalize_local_provider_model(provider: str, value: Any) -> str:
    token = _normalize_string(value)
    normalized_provider = _normalize_provider(provider)
    if normalized_provider == "codex-cli" and token.strip().lower() in _LEGACY_CODEX_MODEL_ALIASES:
        return ""
    return token


def _is_executable_file(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def resolve_codex_bin(value: Any) -> str:
    """Resolve a durable Codex CLI executable path when one is available."""

    token = _normalize_string(value, default="codex")
    candidate = Path(token).expanduser()
    if token != candidate.name or candidate.is_absolute():
        if _is_executable_file(candidate):
            return str(candidate.resolve())
    located = shutil.which(token)
    if located:
        return str(Path(located).resolve())
    if token == "codex":
        for fallback in _DEFAULT_CODEX_BIN_CANDIDATES:
            if _is_executable_file(fallback):
                return str(fallback.resolve())
    return token


def resolve_claude_bin(value: Any) -> str:
    """Resolve a durable Claude Code CLI executable path when one is available."""

    token = _normalize_string(value, default="claude")
    candidate = Path(token).expanduser()
    if token != candidate.name or candidate.is_absolute():
        if _is_executable_file(candidate):
            return str(candidate.resolve())
    located = shutil.which(token)
    if located:
        return str(Path(located).resolve())
    if token == "claude":
        fallback = shutil.which("claude-code")
        if fallback:
            return str(Path(fallback).resolve())
        for candidate_path in _DEFAULT_CLAUDE_BIN_CANDIDATES:
            if _is_executable_file(candidate_path):
                return str(candidate_path.resolve())
    return token


def _is_truthy_env(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def _current_local_provider_hint(*, environ: Mapping[str, str]) -> str:
    bundle_id = str(environ.get("__CFBundleIdentifier", "")).strip().lower()
    if (
        any(str(environ.get(key, "")).strip() for key in ("CODEX_THREAD_ID", "CODEX_SHELL"))
        or "codex" in bundle_id
    ):
        return "codex-cli"
    if (
        any(key.startswith("CLAUDE_CODE") and _is_truthy_env(environ.get(key, "")) for key in environ)
        or "claude" in bundle_id
        or "anthropic" in bundle_id
    ):
        return "claude-cli"
    return ""


def _allow_implicit_local_provider(*, environ: Mapping[str, str]) -> bool:
    if any(
        key.startswith(_RELEASE_LANE_ENV_PREFIX) and str(environ.get(key, "")).strip()
        for key in environ
    ):
        return False
    if str(environ.get("PYTEST_CURRENT_TEST", "")).strip():
        return False
    if _is_truthy_env(environ.get("GITHUB_ACTIONS", "")):
        return False
    if _is_truthy_env(environ.get("CI", "")):
        return False
    return True


def _implicit_local_provider_name(
    *,
    environ: Mapping[str, str],
    codex_bin: str,
    claude_bin: str,
) -> str:
    resolved_codex_bin = resolve_codex_bin(codex_bin)
    resolved_claude_bin = resolve_claude_bin(claude_bin)
    has_codex = _is_executable_file(Path(resolved_codex_bin).expanduser())
    has_claude = _is_executable_file(Path(resolved_claude_bin).expanduser())
    hint = _current_local_provider_hint(environ=environ)
    if hint == "codex-cli" and has_codex:
        return "codex-cli"
    if hint == "claude-cli" and has_claude:
        return "claude-cli"
    if has_codex and not has_claude:
        return "codex-cli"
    if has_claude and not has_codex:
        return "claude-cli"
    if has_codex:
        return "codex-cli"
    return ""


def _read_reasoning_config_record(*, repo_root: Path) -> dict[str, Any]:
    path = reasoning_config_path(repo_root=repo_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    version = str(payload.get("version", "")).strip()
    if version and version != _REASONING_CONFIG_VERSION:
        return {}
    return dict(payload)


def _resolved_config_source(*, repo_payload: Mapping[str, Any], environ: Mapping[str, str]) -> str:
    has_repo = bool(repo_payload)
    explicit_env = any(str(environ.get(key, "")).strip() for key in _KNOWN_REASONING_ENV_KEYS if key in environ)
    if has_repo and explicit_env:
        return "repo-config+env-overrides"
    if has_repo:
        return "repo-config"
    if explicit_env:
        return "env-overrides"
    return "defaults"


def persisted_reasoning_config_payload(config: ReasoningConfig) -> dict[str, Any]:
    """Render a local-only persisted config payload without embedding secrets."""

    provider = _normalize_provider(config.provider)
    codex_bin = _normalize_string(config.codex_bin, default="codex")
    if provider == "codex-cli":
        codex_bin = resolve_codex_bin(codex_bin)
    claude_bin = _normalize_string(config.claude_bin, default="claude")
    if provider == "claude-cli":
        claude_bin = resolve_claude_bin(claude_bin)
    payload: dict[str, Any] = {
        "version": _REASONING_CONFIG_VERSION,
        "mode": _normalize_mode(config.mode),
        "provider": provider,
        "model": _normalize_local_provider_model(provider, config.model),
        "base_url": _normalize_string(config.base_url),
        "scope_cap": _normalize_scope_cap(config.scope_cap),
        "timeout_seconds": _normalize_timeout_seconds(config.timeout_seconds),
        "codex_bin": codex_bin,
        "codex_reasoning_effort": _normalize_codex_reasoning_effort(config.codex_reasoning_effort),
        "claude_bin": claude_bin,
        "claude_reasoning_effort": _normalize_claude_reasoning_effort(config.claude_reasoning_effort),
    }
    if str(config.api_key_env or "").strip():
        payload["api_key_env"] = str(config.api_key_env).strip()
    return payload


def _provider_system_prompt() -> str:
    return (
        "You are an expert reasoning editor assisting Tribunal. "
        "Refine one grounded maintainer case only. "
        "Do not invent evidence, do not propose file writes, and do not mutate approvals or lifecycle state. "
        "Every field must cite only the provided evidence ids."
    )


def _provider_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "leading_explanation",
            "strongest_rival",
            "risk_if_wrong",
            "discriminating_next_check",
            "maintainer_brief",
        ],
        "additionalProperties": False,
        "properties": {
            "leading_explanation": {"$ref": "#/$defs/citedField"},
            "strongest_rival": {"$ref": "#/$defs/citedField"},
            "risk_if_wrong": {"$ref": "#/$defs/citedField"},
            "discriminating_next_check": {"$ref": "#/$defs/citedField"},
            "maintainer_brief": {"$ref": "#/$defs/citedField"},
        },
        "$defs": {
            "citedField": {
                "type": "object",
                "required": ["text", "evidence_ids"],
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "evidence_ids": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                },
            }
        },
    }


def _default_tribunal_request(*, prompt_payload: Mapping[str, Any]) -> StructuredReasoningRequest:
    return StructuredReasoningRequest(
        system_prompt=_provider_system_prompt(),
        schema_name="tribunal_case_enrichment",
        output_schema=_provider_output_schema(),
        prompt_payload=prompt_payload,
    )


def _parse_structured_mapping_text(raw_text: str) -> Mapping[str, Any] | None:
    text = str(raw_text or "").strip()
    if not text:
        return None
    candidates = [text]
    if "```" in text:
        fenced_segments = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        candidates.extend(segment.strip() for segment in fenced_segments if str(segment).strip())
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if 0 <= first_brace < last_brace:
        candidates.append(text[first_brace : last_brace + 1].strip())
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        try:
            result = json.loads(token)
        except json.JSONDecodeError:
            continue
        if isinstance(result, Mapping):
            return result
    return None


def _parse_structured_mapping_file(path: Path) -> Mapping[str, Any] | None:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return _parse_structured_mapping_text(raw_text)


def _parse_claude_structured_output(raw_text: str) -> Mapping[str, Any] | None:
    payload = _parse_structured_mapping_text(raw_text)
    if payload is None:
        return None
    if "result" in payload:
        result = payload.get("result")
        if isinstance(result, Mapping):
            return result
        if isinstance(result, str):
            return _parse_structured_mapping_text(result)
    return payload


def _resolved_request_timeout_seconds(value: Any, *, default: float) -> float:
    try:
        token = float(value)
    except (TypeError, ValueError):
        return float(default)
    if token <= 0:
        return float(default)
    return float(token)


class OpenAICompatibleReasoningProvider:
    """Call an OpenAI-compatible chat-completions endpoint using JSON schema output."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = str(base_url or "").rstrip("/")
        self._api_key = str(api_key or "").strip()
        self._model = str(model or "").strip()
        self._timeout_seconds = float(timeout_seconds)
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _clear_failure(self) -> None:
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _record_failure(self, code: str, detail: str) -> None:
        self.last_failure_code = str(code or "").strip()
        self.last_failure_detail = str(detail or "").strip()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        if not self._base_url or not self._api_key or not self._model:
            self._record_failure(
                "unavailable",
                "OpenAI-compatible provider is unconfigured for base_url, api_key, or model.",
            )
            return None
        timeout_seconds = _resolved_request_timeout_seconds(
            getattr(request, "timeout_seconds", 0.0),
            default=self._timeout_seconds,
        )
        request_payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": str(request.system_prompt or "").strip(),
                },
                {
                    "role": "user",
                    "content": json.dumps(request.prompt_payload, sort_keys=True, ensure_ascii=False),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": str(request.schema_name or "").strip() or "structured_output",
                    "schema": dict(request.output_schema),
                },
            },
        }
        request = urllib.request.Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except TimeoutError:
            self._record_failure("timeout", f"Provider request exceeded {timeout_seconds:.1f}s.")
            return None
        except urllib.error.URLError as exc:
            self._record_failure("transport_error", str(getattr(exc, "reason", exc)).strip())
            return None
        except (OSError, urllib.error.HTTPError) as exc:
            self._record_failure("transport_error", str(exc).strip())
            return None
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._record_failure("invalid_response", "Provider returned non-JSON response content.")
            return None
        choices = payload.get("choices", []) if isinstance(payload, Mapping) else []
        if not isinstance(choices, list) or not choices:
            self._record_failure("invalid_response", "Provider response did not include any choices.")
            return None
        message = choices[0].get("message", {}) if isinstance(choices[0], Mapping) else {}
        content = message.get("content")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "".join(
                str(item.get("text", ""))
                for item in content
                if isinstance(item, Mapping) and str(item.get("type", "")) == "text"
            )
        if not text.strip():
            self._record_failure("invalid_response", "Provider response did not include structured text content.")
            return None
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            self._record_failure("invalid_response", "Provider text content was not valid JSON.")
            return None
        if not isinstance(result, Mapping):
            self._record_failure("invalid_response", "Provider JSON payload was not an object.")
            return None
        self._clear_failure()
        return result

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return self.generate_structured(request=_default_tribunal_request(prompt_payload=prompt_payload))


class CodexCliReasoningProvider:
    """Call the local Codex CLI in non-interactive schema-constrained mode."""

    def __init__(
        self,
        *,
        repo_root: Path,
        codex_bin: str,
        model: str,
        timeout_seconds: float,
        reasoning_effort: str,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._codex_bin = str(codex_bin or "").strip() or "codex"
        self._model = str(model or "").strip()
        self._timeout_seconds = float(timeout_seconds)
        self._reasoning_effort = str(reasoning_effort or "").strip().lower() or "high"
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _clear_failure(self) -> None:
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _record_failure(self, code: str, detail: str) -> None:
        self.last_failure_code = str(code or "").strip()
        self.last_failure_detail = str(detail or "").strip()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        if not shutil.which(self._codex_bin):
            self._record_failure("unavailable", f"Codex CLI binary `{self._codex_bin}` is not available.")
            return None
        reasoning_effort = _normalize_codex_reasoning_effort(
            _normalize_string(getattr(request, "reasoning_effort", ""), default=self._reasoning_effort)
        )
        timeout_seconds = _resolved_request_timeout_seconds(
            getattr(request, "timeout_seconds", 0.0),
            default=self._timeout_seconds,
        )
        with tempfile.TemporaryDirectory(prefix="tribunal-codex-") as tmp_dir:
            temp_root = Path(tmp_dir)
            schema_path = temp_root / "schema.json"
            output_path = temp_root / "result.json"
            schema_path.write_text(
                json.dumps(request.output_schema, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
            prompt = (
                f"{str(request.system_prompt or '').strip()} "
                "Work only from the supplied JSON payload. "
                "Do not inspect the repository, do not run commands, and do not rely on hidden context. "
                "Return only JSON that matches the provided output schema.\n\n"
                f"{json.dumps(request.prompt_payload, sort_keys=True, ensure_ascii=False)}\n"
            )
            command = [
                self._codex_bin,
                "exec",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ephemeral",
                "--color",
                "never",
                "-c",
                f'model_reasoning_effort="{reasoning_effort}"',
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-C",
                str(self._repo_root),
            ]
            if self._model:
                command.extend(["--model", self._model])
            command.append("-")
            try:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    cwd=str(self._repo_root),
                    check=False,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                self._record_failure("timeout", f"Codex CLI exceeded {timeout_seconds:.1f}s.")
                return None
            except OSError as exc:
                self._record_failure("transport_error", str(exc).strip())
                return None
            # Prefer the explicit last-message file, but recover from Codex CLI
            # runs that leave that file missing or unreadable while still
            # echoing the same schema-valid JSON on stdout.
            if output_path.is_file():
                result = _parse_structured_mapping_file(output_path)
                if result is not None:
                    self._clear_failure()
                    return result
            result = _parse_structured_mapping_text(getattr(completed, "stdout", ""))
            if result is None:
                self._record_failure(
                    "invalid_response",
                    "Codex CLI did not return schema-valid structured JSON output.",
                )
                return None
            self._clear_failure()
            return result

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return self.generate_structured(request=_default_tribunal_request(prompt_payload=prompt_payload))


class ClaudeCliReasoningProvider:
    """Call the local Claude Code CLI in print-mode schema-constrained mode."""

    def __init__(
        self,
        *,
        repo_root: Path,
        claude_bin: str,
        model: str,
        timeout_seconds: float,
        reasoning_effort: str,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._claude_bin = str(claude_bin or "").strip() or "claude"
        self._model = str(model or "").strip()
        self._timeout_seconds = float(timeout_seconds)
        self._reasoning_effort = str(reasoning_effort or "").strip().lower() or "high"
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _clear_failure(self) -> None:
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _record_failure(self, code: str, detail: str) -> None:
        self.last_failure_code = str(code or "").strip()
        self.last_failure_detail = str(detail or "").strip()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        resolved_claude_bin = resolve_claude_bin(self._claude_bin)
        if not _is_executable_file(Path(resolved_claude_bin).expanduser()):
            self._record_failure("unavailable", f"Claude CLI binary `{resolved_claude_bin}` is not available.")
            return None
        reasoning_effort = _normalize_claude_reasoning_effort(
            _normalize_string(getattr(request, "reasoning_effort", ""), default=self._reasoning_effort)
        )
        timeout_seconds = _resolved_request_timeout_seconds(
            getattr(request, "timeout_seconds", 0.0),
            default=self._timeout_seconds,
        )
        command = [
            resolved_claude_bin,
            "-p",
            (
                "Work only from the JSON payload piped on stdin. "
                "Do not inspect the repository, do not run commands, do not use tools, "
                "and do not rely on hidden context. Return only JSON that matches the provided output schema."
            ),
            "--output-format",
            "json",
            "--input-format",
            "text",
            "--json-schema",
            json.dumps(request.output_schema, sort_keys=True, ensure_ascii=False),
            "--append-system-prompt",
            str(request.system_prompt or "").strip(),
            "--tools",
            "",
            "--permission-mode",
            "plan",
            "--max-turns",
            "1",
            "--no-session-persistence",
        ]
        if self._model:
            command.extend(["--model", self._model])
        if reasoning_effort:
            command.extend(["--effort", reasoning_effort])
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(request.prompt_payload, sort_keys=True, ensure_ascii=False),
                text=True,
                capture_output=True,
                cwd=str(self._repo_root),
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            self._record_failure("timeout", f"Claude CLI exceeded {timeout_seconds:.1f}s.")
            return None
        except OSError as exc:
            self._record_failure("transport_error", str(exc).strip())
            return None
        result = _parse_claude_structured_output(getattr(completed, "stdout", ""))
        if result is None:
            self._record_failure(
                "invalid_response",
                "Claude CLI did not return schema-valid structured JSON output.",
            )
            return None
        self._clear_failure()
        return result

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return self.generate_structured(request=_default_tribunal_request(prompt_payload=prompt_payload))


def reasoning_config_from_env(
    *,
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> ReasoningConfig:
    """Resolve optional Tribunal-provider configuration from local config plus env overrides."""

    env = dict(os.environ if environ is None else environ)
    repo_payload = _read_reasoning_config_record(repo_root=Path(repo_root).resolve()) if repo_root is not None else {}

    mode = _normalize_mode(repo_payload.get("mode", "auto"))
    if "ODYLITH_REASONING_MODE" in env:
        mode = _normalize_mode(env.get("ODYLITH_REASONING_MODE"))

    provider = _normalize_provider(repo_payload.get("provider", "auto-local"))
    if "ODYLITH_REASONING_PROVIDER" in env:
        provider = _normalize_provider(env.get("ODYLITH_REASONING_PROVIDER"))

    model = _normalize_string(repo_payload.get("model", ""))
    if "ODYLITH_REASONING_MODEL" in env:
        model = _normalize_string(env.get("ODYLITH_REASONING_MODEL"))
    base_url = _normalize_string(repo_payload.get("base_url", ""))
    if "ODYLITH_REASONING_BASE_URL" in env:
        base_url = _normalize_string(env.get("ODYLITH_REASONING_BASE_URL"))

    api_key_env = _normalize_string(repo_payload.get("api_key_env", ""))
    if "ODYLITH_REASONING_API_KEY_ENV" in env:
        api_key_env = _normalize_string(env.get("ODYLITH_REASONING_API_KEY_ENV"))

    api_key = _normalize_string(env.get("ODYLITH_REASONING_API_KEY", ""))
    if not api_key and api_key_env:
        api_key = _normalize_string(env.get(api_key_env, ""))

    codex_bin = _normalize_string(repo_payload.get("codex_bin", "codex"), default="codex")
    if "ODYLITH_REASONING_CODEX_BIN" in env:
        codex_bin = _normalize_string(env.get("ODYLITH_REASONING_CODEX_BIN"), default="codex")
    codex_bin = resolve_codex_bin(codex_bin)

    codex_reasoning_effort = _normalize_codex_reasoning_effort(repo_payload.get("codex_reasoning_effort", "high"))
    if "ODYLITH_REASONING_CODEX_REASONING_EFFORT" in env:
        codex_reasoning_effort = _normalize_codex_reasoning_effort(env.get("ODYLITH_REASONING_CODEX_REASONING_EFFORT"))

    claude_bin = _normalize_string(repo_payload.get("claude_bin", "claude"), default="claude")
    if "ODYLITH_REASONING_CLAUDE_BIN" in env:
        claude_bin = _normalize_string(env.get("ODYLITH_REASONING_CLAUDE_BIN"), default="claude")
    claude_bin = resolve_claude_bin(claude_bin)

    claude_reasoning_effort = _normalize_claude_reasoning_effort(repo_payload.get("claude_reasoning_effort", "high"))
    if "ODYLITH_REASONING_CLAUDE_REASONING_EFFORT" in env:
        claude_reasoning_effort = _normalize_claude_reasoning_effort(env.get("ODYLITH_REASONING_CLAUDE_REASONING_EFFORT"))

    scope_cap = _normalize_scope_cap(repo_payload.get("scope_cap", 5), default=5)
    if "ODYLITH_REASONING_SCOPE_CAP" in env:
        scope_cap = _normalize_scope_cap(env.get("ODYLITH_REASONING_SCOPE_CAP"), default=scope_cap)

    timeout_seconds = _normalize_timeout_seconds(repo_payload.get("timeout_seconds", 20.0), default=20.0)
    if "ODYLITH_REASONING_TIMEOUT_SECONDS" in env:
        timeout_seconds = _normalize_timeout_seconds(env.get("ODYLITH_REASONING_TIMEOUT_SECONDS"), default=timeout_seconds)

    if provider == "auto-local" and _allow_implicit_local_provider(environ=env):
        resolved_local_provider = _implicit_local_provider_name(
            environ=env,
            codex_bin=codex_bin,
            claude_bin=claude_bin,
        )
        if resolved_local_provider:
            provider = resolved_local_provider
    model = _normalize_local_provider_model(provider, model)

    config_path = str(reasoning_config_path(repo_root=Path(repo_root).resolve())) if repo_root is not None and repo_payload else ""
    return ReasoningConfig(
        mode=mode,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        scope_cap=scope_cap,
        timeout_seconds=timeout_seconds,
        codex_bin=codex_bin,
        codex_reasoning_effort=codex_reasoning_effort,
        claude_bin=claude_bin,
        claude_reasoning_effort=claude_reasoning_effort,
        api_key_env=api_key_env,
        config_source=_resolved_config_source(repo_payload=repo_payload, environ=env),
        config_path=config_path,
    )


def provider_from_config(
    config: ReasoningConfig,
    *,
    repo_root: Path | None = None,
    require_auto_mode: bool = True,
    allow_implicit_local_provider: bool = False,
) -> ReasoningProvider | None:
    """Build an optional provider for the resolved config.

    By default this helper preserves Odylith's existing contract that AI
    reasoning is only enabled when `mode=auto`. Callers with a different product
    contract may explicitly opt out of that gate while still reusing the shared
    provider configuration and adapter stack.
    """

    if require_auto_mode and config.mode != "auto":
        return None
    if config.provider == "auto-local":
        if repo_root is None or not allow_implicit_local_provider or not _allow_implicit_local_provider(environ=os.environ):
            return None
        implicit_provider = _implicit_local_provider_name(
            environ=os.environ,
            codex_bin=config.codex_bin,
            claude_bin=config.claude_bin,
        )
        if implicit_provider == "codex-cli":
            return CodexCliReasoningProvider(
                repo_root=repo_root,
                codex_bin=resolve_codex_bin(config.codex_bin),
                model=_normalize_local_provider_model(implicit_provider, config.model),
                timeout_seconds=config.timeout_seconds,
                reasoning_effort=config.codex_reasoning_effort,
            )
        if implicit_provider == "claude-cli":
            return ClaudeCliReasoningProvider(
                repo_root=repo_root,
                claude_bin=resolve_claude_bin(config.claude_bin),
                model=config.model,
                timeout_seconds=config.timeout_seconds,
                reasoning_effort=config.claude_reasoning_effort,
            )
        return None
    if config.provider == "openai-compatible":
        if not config.base_url or not config.api_key or not config.model:
            if repo_root is None or not allow_implicit_local_provider or not _allow_implicit_local_provider(environ=os.environ):
                return None
            implicit_provider = _implicit_local_provider_name(
                environ=os.environ,
                codex_bin=config.codex_bin,
                claude_bin=config.claude_bin,
            )
            if implicit_provider == "codex-cli":
                return CodexCliReasoningProvider(
                    repo_root=repo_root,
                    codex_bin=resolve_codex_bin(config.codex_bin),
                    model=_normalize_local_provider_model(implicit_provider, config.model),
                    timeout_seconds=config.timeout_seconds,
                    reasoning_effort=config.codex_reasoning_effort,
                )
            if implicit_provider == "claude-cli":
                return ClaudeCliReasoningProvider(
                    repo_root=repo_root,
                    claude_bin=resolve_claude_bin(config.claude_bin),
                    model=config.model,
                    timeout_seconds=config.timeout_seconds,
                    reasoning_effort=config.claude_reasoning_effort,
                )
            return None
        return OpenAICompatibleReasoningProvider(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
        )
    if config.provider == "codex-cli":
        resolved_codex_bin = resolve_codex_bin(config.codex_bin)
        if repo_root is None or not _is_executable_file(Path(resolved_codex_bin).expanduser()):
            return None
        return CodexCliReasoningProvider(
            repo_root=repo_root,
            codex_bin=resolved_codex_bin,
            model=_normalize_local_provider_model(config.provider, config.model),
            timeout_seconds=config.timeout_seconds,
            reasoning_effort=config.codex_reasoning_effort,
        )
    if config.provider == "claude-cli":
        resolved_claude_bin = resolve_claude_bin(config.claude_bin)
        if repo_root is None or not _is_executable_file(Path(resolved_claude_bin).expanduser()):
            return None
        return ClaudeCliReasoningProvider(
            repo_root=repo_root,
            claude_bin=resolved_claude_bin,
            model=_normalize_local_provider_model(config.provider, config.model),
            timeout_seconds=config.timeout_seconds,
            reasoning_effort=config.claude_reasoning_effort,
        )
    return None


def build_reasoning_payload(
    *,
    repo_root: Path,
    delivery_payload: Mapping[str, Any],
    posture: Mapping[str, Any],
    previous_payload: Mapping[str, Any] | None = None,
    config: ReasoningConfig | None = None,
    provider: ReasoningProvider | None = None,
) -> dict[str, Any]:
    """Build or refresh the persisted Tribunal reasoning artifact."""

    config = config or reasoning_config_from_env(repo_root=repo_root)
    payload = tribunal_engine.build_tribunal_payload(
        repo_root=repo_root,
        delivery_payload=delivery_payload,
        posture=posture,
        previous_payload=previous_payload,
        config=config,
        provider=provider
        or provider_from_config(
            config,
            repo_root=repo_root,
            allow_implicit_local_provider=True,
        ),
    )
    payload["config_source"] = str(getattr(config, "config_source", "defaults")).strip() or "defaults"
    payload["config_path"] = str(getattr(config, "config_path", "")).strip()
    return payload


__all__ = [
    "ClaudeCliReasoningProvider",
    "CodexCliReasoningProvider",
    "DEFAULT_REASONING_CONFIG_PATH",
    "DEFAULT_REASONING_PATH",
    "OpenAICompatibleReasoningProvider",
    "ReasoningConfig",
    "ReasoningProvider",
    "StructuredReasoningRequest",
    "build_reasoning_payload",
    "persisted_reasoning_config_payload",
    "provider_from_config",
    "resolve_claude_bin",
    "resolve_codex_bin",
    "reasoning_config_path",
    "reasoning_config_from_env",
]
