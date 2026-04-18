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

from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.reasoning import tribunal_engine


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
_CLAUDE_CODE_APP_GLOB_PATTERNS: tuple[str, ...] = (
    "~/Library/Application Support/Claude/claude-code/*/claude.app/Contents/MacOS/claude",
    "~/Library/Application Support/Claude/claude-code-vm/*/claude",
)
_CLAUDE_CODE_STATIC_CANDIDATES: tuple[Path, ...] = (
    Path("/usr/local/bin/claude"),
    Path("~/.local/bin/claude").expanduser(),
)


def _discover_claude_bin_from_app_bundle() -> Path | None:
    """Find the latest Claude Code binary from versioned app bundle paths."""
    import glob as _glob

    for pattern in _CLAUDE_CODE_APP_GLOB_PATTERNS:
        expanded = str(Path(pattern).expanduser())
        matches = sorted(_glob.glob(expanded), reverse=True)
        for match in matches:
            candidate = Path(match)
            if candidate.is_file() and os.access(str(candidate), os.X_OK):
                return candidate.resolve()
    return None
_RELEASE_LANE_ENV_PREFIX = "ODYLITH_RELEASE_"
_LEGACY_CODEX_MODEL_ALIASES: frozenset[str] = frozenset(
    {
        "codex-spark 5.3",
        "codex spark 5.3",
    }
)
_CHEAP_STRUCTURED_CODEX_MODEL = "gpt-5.3-codex-spark"
_CHEAP_STRUCTURED_CODEX_MODEL_LADDER: tuple[str, ...] = (
    "gpt-5.3-codex-spark",
    "gpt-5.3-codex",
    "gpt-5.4-mini",
)
_CHEAP_STRUCTURED_CLAUDE_MODEL_LADDER: tuple[str, ...] = (
    "haiku",
    "sonnet",
)
_CHEAP_STRUCTURED_REASONING_EFFORT = "medium"
_CHEAP_STRUCTURED_LADDER_ADVANCE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "credits_exhausted",
        "rate_limited",
    }
)
_CHEAP_STRUCTURED_MODEL_UNAVAILABLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bswitch to another model\b", re.IGNORECASE),
    re.compile(r"\bunknown model\b", re.IGNORECASE),
    re.compile(r"\bmodel\b.*\bnot found\b", re.IGNORECASE),
    re.compile(r"\bmodel\b.*\bunavailable\b", re.IGNORECASE),
    re.compile(r"\bunsupported model\b", re.IGNORECASE),
)
_PROVIDER_RATE_LIMIT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brate[\s-]*limit", re.IGNORECASE),
    re.compile(r"\btoo many requests\b", re.IGNORECASE),
    re.compile(r"\b429\b"),
    re.compile(r"\bretry after\b", re.IGNORECASE),
)
_PROVIDER_CREDIT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\binsufficient[_\s-]*quota\b", re.IGNORECASE),
    re.compile(r"\binsufficient[_\s-]*credit", re.IGNORECASE),
    re.compile(r"\bout of credits?\b", re.IGNORECASE),
    re.compile(r"\bcredit limit\b", re.IGNORECASE),
    re.compile(r"\busage limit\b", re.IGNORECASE),
    re.compile(r"\bquota exceeded\b", re.IGNORECASE),
    re.compile(r"\bbilling (?:hard )?limit\b", re.IGNORECASE),
)
_PROVIDER_AUTH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bunauthorized\b", re.IGNORECASE),
    re.compile(r"\bauth(?:entication|orization)?\b", re.IGNORECASE),
    re.compile(r"\bapi key\b", re.IGNORECASE),
    re.compile(r"\bforbidden\b", re.IGNORECASE),
    re.compile(r"\b401\b"),
    re.compile(r"\b403\b"),
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
    model: str = ""
    reasoning_effort: str = ""
    timeout_seconds: float = 0.0


@dataclass(frozen=True)
class StructuredReasoningProfile:
    """Provider-aware model/effort overrides for bounded structured work."""

    provider: str
    model: str = ""
    reasoning_effort: str = ""


class _ProviderRequestStateMixin:
    """Track provider request metadata and the latest failure outcome."""

    last_failure_code: str
    last_failure_detail: str
    last_request_model: str
    last_request_reasoning_effort: str

    def _initialize_request_state(self) -> None:
        self.last_failure_code = ""
        self.last_failure_detail = ""
        self.last_request_model = ""
        self.last_request_reasoning_effort = ""

    def _clear_failure(self) -> None:
        self.last_failure_code = ""
        self.last_failure_detail = ""

    def _record_failure(self, code: str, detail: str) -> None:
        self.last_failure_code = str(code or "").strip()
        self.last_failure_detail = str(detail or "").strip()

    def _record_request(self, *, model: Any, reasoning_effort: Any) -> None:
        self.last_request_model = str(model or "").strip()
        self.last_request_reasoning_effort = str(reasoning_effort or "").strip().lower()


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


def _normalized_failure_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _normalized_failure_excerpt(text: Any, *, max_chars: int = 280) -> str:
    token = _normalized_failure_text(text)
    if not token:
        return ""
    if len(token) <= max_chars:
        return token
    head_chars = max(80, min(max_chars - 40, 140))
    tail_chars = max(40, max_chars - head_chars - 5)
    return f"{token[:head_chars].rstrip()} ... {token[-tail_chars:].lstrip()}"


def _match_failure_pattern(
    patterns: Sequence[re.Pattern[str]],
    *,
    haystack: str,
) -> bool:
    return any(pattern.search(haystack) for pattern in patterns)


def _classify_provider_failure(
    *,
    provider_label: str,
    detail_text: str,
    invalid_response_detail: str,
    returncode: int | None = None,
    status_code: int | None = None,
) -> tuple[str, str]:
    normalized_detail = _normalized_failure_text(detail_text)
    excerpt = _normalized_failure_excerpt(normalized_detail)
    haystack = normalized_detail.lower()

    if _match_failure_pattern(_PROVIDER_CREDIT_PATTERNS, haystack=haystack):
        detail = excerpt or f"{provider_label} reported a possible credit or budget limit."
        return "credits_exhausted", detail
    if status_code == 429 or _match_failure_pattern(_PROVIDER_RATE_LIMIT_PATTERNS, haystack=haystack):
        detail = excerpt or f"{provider_label} reported a rate-limit response."
        return "rate_limited", detail
    if status_code in {401, 403} or _match_failure_pattern(_PROVIDER_AUTH_PATTERNS, haystack=haystack):
        detail = excerpt or f"{provider_label} rejected the request because of authentication or permission configuration."
        return "auth_error", detail
    if status_code is not None and status_code >= 500:
        detail = excerpt or f"{provider_label} returned HTTP {status_code}."
        return "provider_error", detail
    if returncode not in (None, 0):
        if excerpt:
            return "provider_error", f"{provider_label} exited with status {returncode}. {excerpt}"
        return "provider_error", f"{provider_label} exited with status {returncode}."
    if excerpt:
        return "invalid_response", excerpt
    return "invalid_response", invalid_response_detail


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
    """Resolve a durable Claude Code CLI executable path when one is available.

    Discovery order:
    1. Explicit path from caller or environment variable
    2. ``which claude`` on PATH
    3. ``which claude-code`` on PATH
    4. Versioned Claude.app bundle glob (picks the latest installed version)
    5. Static fallback candidates (/usr/local/bin/claude, ~/.local/bin/claude)
    """

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
        bundle_bin = _discover_claude_bin_from_app_bundle()
        if bundle_bin is not None:
            return str(bundle_bin)
        for candidate_path in _CLAUDE_CODE_STATIC_CANDIDATES:
            if _is_executable_file(candidate_path):
                return str(candidate_path.resolve())
    return token


def _is_truthy_env(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token not in {"", "0", "false", "no", "off"}


def _current_local_provider_hint(*, environ: Mapping[str, str]) -> str:
    detected_host = host_runtime_contract.detect_host_runtime(environ=environ)
    if detected_host == "claude_cli":
        return "claude-cli"
    if detected_host == "codex_cli":
        return "codex-cli"
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
    if has_codex and has_claude:
        return hint or "claude-cli"
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


def cheap_structured_reasoning_profile(
    config: ReasoningConfig,
    *,
    environ: Mapping[str, str] | None = None,
    previous_model: str = "",
    failure_code: str = "",
    failure_detail: str = "",
) -> StructuredReasoningProfile:
    """Return the cheap provider-aware profile for bounded structured narration.

    This keeps lightweight structured update jobs fast and cheap across local
    providers. For local-host narration the ladder is fixed and medium-reasoning:
    pick the cheapest supported local model first, then step to the next cheap
    rung only after a provider-budget or model-availability failure.
    """

    env = dict(os.environ if environ is None else environ)
    provider = _normalize_provider(getattr(config, "provider", ""))
    if provider == "auto-local" and _allow_implicit_local_provider(environ=env):
        provider = _implicit_local_provider_name(
            environ=env,
            codex_bin=getattr(config, "codex_bin", "codex"),
            claude_bin=getattr(config, "claude_bin", "claude"),
        )
    elif provider == "openai-compatible":
        has_endpoint = all(
            str(token or "").strip()
            for token in (
                getattr(config, "base_url", ""),
                getattr(config, "api_key", ""),
                getattr(config, "model", ""),
            )
        )
        if not has_endpoint and _allow_implicit_local_provider(environ=env):
            implicit_provider = _implicit_local_provider_name(
                environ=env,
                codex_bin=getattr(config, "codex_bin", "codex"),
                claude_bin=getattr(config, "claude_bin", "claude"),
            )
            if implicit_provider:
                provider = implicit_provider
    model = _normalize_local_provider_model(provider, getattr(config, "model", ""))
    ladder: tuple[str, ...]
    if provider == "codex-cli":
        ladder = _CHEAP_STRUCTURED_CODEX_MODEL_LADDER
    elif provider == "claude-cli":
        ladder = _CHEAP_STRUCTURED_CLAUDE_MODEL_LADDER
    else:
        ladder = ()
    if ladder:
        prior_model = _normalize_local_provider_model(provider, previous_model)
        if not prior_model and failure_detail:
            haystack = _normalized_failure_text(failure_detail).lower()
            for candidate in ladder:
                if str(candidate).strip().lower() in haystack:
                    prior_model = candidate
                    break
        advance = str(failure_code or "").strip().lower() in _CHEAP_STRUCTURED_LADDER_ADVANCE_FAILURE_CODES
        if not advance and failure_detail:
            advance = _match_failure_pattern(
                _CHEAP_STRUCTURED_MODEL_UNAVAILABLE_PATTERNS,
                haystack=_normalized_failure_text(failure_detail),
            )
        selected_model = ladder[0]
        if advance and prior_model in ladder:
            selected_model = ladder[min(ladder.index(prior_model) + 1, len(ladder) - 1)]
        return StructuredReasoningProfile(
            provider=provider,
            model=selected_model,
            reasoning_effort=_CHEAP_STRUCTURED_REASONING_EFFORT,
        )
    if provider == "codex-cli":
        return StructuredReasoningProfile(
            provider=provider,
            model=model or _CHEAP_STRUCTURED_CODEX_MODEL,
            reasoning_effort=_CHEAP_STRUCTURED_REASONING_EFFORT,
        )
    if provider == "claude-cli":
        return StructuredReasoningProfile(
            provider=provider,
            model=model,
            reasoning_effort=_CHEAP_STRUCTURED_REASONING_EFFORT,
        )
    if provider == "openai-compatible":
        return StructuredReasoningProfile(provider=provider, model=model, reasoning_effort="")
    return StructuredReasoningProfile(provider=provider, model=model, reasoning_effort="")


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
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            candidates.append(line)
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


class OpenAICompatibleReasoningProvider(_ProviderRequestStateMixin):
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
        self._initialize_request_state()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        request_model = _normalize_string(getattr(request, "model", ""), default=self._model)
        self._record_request(
            model=request_model,
            reasoning_effort=getattr(request, "reasoning_effort", ""),
        )
        if not self._base_url or not self._api_key or not request_model:
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
            "model": request_model,
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
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="ignore")
            except OSError:
                body = ""
            code, detail = _classify_provider_failure(
                provider_label="OpenAI-compatible provider",
                detail_text=body or str(exc),
                invalid_response_detail="Provider returned an unsuccessful HTTP response.",
                status_code=int(getattr(exc, "code", 0) or 0),
            )
            self._record_failure(code, detail)
            return None
        except urllib.error.URLError as exc:
            self._record_failure("transport_error", str(getattr(exc, "reason", exc)).strip())
            return None
        except OSError as exc:
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


class CodexCliReasoningProvider(_ProviderRequestStateMixin):
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
        self._initialize_request_state()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        if not shutil.which(self._codex_bin):
            self._record_failure("unavailable", f"Codex CLI binary `{self._codex_bin}` is not available.")
            return None
        reasoning_effort = _normalize_codex_reasoning_effort(
            _normalize_string(getattr(request, "reasoning_effort", ""), default=self._reasoning_effort)
        )
        request_model = _normalize_string(getattr(request, "model", ""), default=self._model)
        self._record_request(model=request_model, reasoning_effort=reasoning_effort)
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
            if request_model:
                command.extend(["--model", request_model])
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
                code, detail = _classify_provider_failure(
                    provider_label="Codex CLI",
                    detail_text="\n".join(
                        token
                        for token in (
                            getattr(completed, "stderr", ""),
                            getattr(completed, "stdout", ""),
                        )
                        if str(token or "").strip()
                    ),
                    invalid_response_detail="Codex CLI did not return schema-valid structured JSON output.",
                    returncode=int(getattr(completed, "returncode", 0) or 0),
                )
                self._record_failure(code, detail)
                return None
            self._clear_failure()
            return result

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return self.generate_structured(request=_default_tribunal_request(prompt_payload=prompt_payload))


class AnthropicDirectReasoningProvider(_ProviderRequestStateMixin):
    """Call the Anthropic Messages API directly via httpx — no CLI subprocess overhead."""

    _DEFAULT_MODEL = "claude-haiku-4-5"
    _DEFAULT_TIMEOUT = 25.0

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "",
        model: str = "",
        timeout_seconds: float = 0.0,
        reasoning_effort: str = "",
    ) -> None:
        self._api_key = str(api_key or "").strip()
        self._base_url = str(base_url or "").rstrip("/") or "https://api.anthropic.com"
        self._model = str(model or "").strip() or self._DEFAULT_MODEL
        self._timeout_seconds = float(timeout_seconds) if timeout_seconds and float(timeout_seconds) > 0 else self._DEFAULT_TIMEOUT
        self._reasoning_effort = str(reasoning_effort or "").strip().lower()
        self._initialize_request_state()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        try:
            import httpx
        except ImportError:
            self._record_failure("unavailable", "httpx is not installed.")
            return None
        if not self._api_key:
            self._record_failure("unavailable", "Anthropic API key is not configured.")
            return None
        request_model = _normalize_string(getattr(request, "model", ""), default=self._model)
        reasoning_effort = _normalize_string(
            getattr(request, "reasoning_effort", ""), default=self._reasoning_effort
        )
        self._record_request(model=request_model, reasoning_effort=reasoning_effort)
        timeout_seconds = _resolved_request_timeout_seconds(
            getattr(request, "timeout_seconds", 0.0),
            default=self._timeout_seconds,
        )
        messages = [
            {
                "role": "user",
                "content": json.dumps(request.prompt_payload, sort_keys=True, ensure_ascii=False),
            },
        ]
        body: dict[str, Any] = {
            "model": request_model,
            "max_tokens": 4096,
            "system": str(request.system_prompt or "").strip(),
            "messages": messages,
        }
        self._clear_failure()
        try:
            response = httpx.post(
                f"{self._base_url}/v1/messages",
                json=body,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException:
            self._record_failure("timeout", f"Anthropic API request exceeded {timeout_seconds:.1f}s.")
            return None
        except Exception as exc:
            self._record_failure("network_error", _normalized_failure_text(str(exc)))
            return None
        if response.status_code != 200:
            error_body = response.text[:500]
            if response.status_code == 429 or any(p.search(error_body) for p in _PROVIDER_CREDIT_PATTERNS):
                self._record_failure("credits_exhausted", error_body)
            elif any(p.search(error_body) for p in _PROVIDER_AUTH_PATTERNS):
                self._record_failure("auth_error", error_body)
            else:
                self._record_failure("provider_error", f"HTTP {response.status_code}: {error_body}")
            return None
        try:
            response_data = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            self._record_failure("parse_error", f"Invalid JSON response: {exc}")
            return None
        content_blocks = response_data.get("content", [])
        text = ""
        for block in content_blocks:
            if isinstance(block, Mapping) and block.get("type") == "text":
                text = str(block.get("text", "")).strip()
                break
        if not text:
            self._record_failure("empty_response", "Provider returned no text content.")
            return None
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
        try:
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            self._record_failure("parse_error", f"Provider response was not valid JSON: {text[:200]}")
            return None
        if isinstance(result, Mapping):
            return result
        self._record_failure("invalid_schema", f"Provider returned non-object JSON: {type(result).__name__}")
        return None

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return self.generate_structured(request=_default_tribunal_request(prompt_payload=prompt_payload))


class ClaudeCliReasoningProvider(_ProviderRequestStateMixin):
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
        self._initialize_request_state()

    def generate_structured(self, *, request: StructuredReasoningRequest) -> Mapping[str, Any] | None:
        resolved_claude_bin = resolve_claude_bin(self._claude_bin)
        if not _is_executable_file(Path(resolved_claude_bin).expanduser()):
            self._record_failure("unavailable", f"Claude CLI binary `{resolved_claude_bin}` is not available.")
            return None
        reasoning_effort = _normalize_claude_reasoning_effort(
            _normalize_string(getattr(request, "reasoning_effort", ""), default=self._reasoning_effort)
        )
        request_model = _normalize_string(getattr(request, "model", ""), default=self._model)
        self._record_request(model=request_model, reasoning_effort=reasoning_effort)
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
            "--append-system-prompt",
            (
                str(request.system_prompt or "").strip()
                + "\n\nReturn a JSON object matching this schema: "
                + json.dumps(request.output_schema, sort_keys=True, ensure_ascii=False)
            ),
            "--permission-mode",
            "plan",
            "--max-turns",
            "2",
            "--no-session-persistence",
            "--setting-sources",
            "",
        ]
        if request_model:
            command.extend(["--model", request_model])
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
            code, detail = _classify_provider_failure(
                provider_label="Claude CLI",
                detail_text="\n".join(
                    token
                    for token in (
                        getattr(completed, "stderr", ""),
                        getattr(completed, "stdout", ""),
                    )
                    if str(token or "").strip()
                ),
                invalid_response_detail="Claude CLI did not return schema-valid structured JSON output.",
                returncode=int(getattr(completed, "returncode", 0) or 0),
            )
            self._record_failure(code, detail)
            return None
        self._clear_failure()
        return result

    def generate_finding(self, *, prompt_payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        return self.generate_structured(request=_default_tribunal_request(prompt_payload=prompt_payload))


def provider_failure_metadata(provider: Any) -> dict[str, str]:
    if isinstance(provider, OpenAICompatibleReasoningProvider):
        provider_name = "openai-compatible"
    elif isinstance(provider, CodexCliReasoningProvider):
        provider_name = "codex-cli"
    elif isinstance(provider, ClaudeCliReasoningProvider):
        provider_name = "claude-cli"
    else:
        provider_name = str(getattr(provider, "provider_name", "")).strip() or type(provider).__name__
    return {
        "provider": provider_name,
        "code": str(getattr(provider, "last_failure_code", "")).strip().lower(),
        "detail": str(getattr(provider, "last_failure_detail", "")).strip(),
        "model": str(getattr(provider, "last_request_model", "")).strip(),
        "reasoning_effort": str(getattr(provider, "last_request_reasoning_effort", "")).strip().lower(),
    }


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
                repo_root=repo_root or Path(".").resolve(),
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
                return _build_claude_provider(config=config, repo_root=repo_root)
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
        if repo_root is None:
            return None
        return ClaudeCliReasoningProvider(
            repo_root=repo_root,
            claude_bin=resolve_claude_bin(config.claude_bin),
            model=config.model,
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
    "StructuredReasoningProfile",
    "StructuredReasoningRequest",
    "build_reasoning_payload",
    "cheap_structured_reasoning_profile",
    "persisted_reasoning_config_payload",
    "provider_failure_metadata",
    "provider_from_config",
    "resolve_claude_bin",
    "resolve_codex_bin",
    "reasoning_config_path",
    "reasoning_config_from_env",
]
