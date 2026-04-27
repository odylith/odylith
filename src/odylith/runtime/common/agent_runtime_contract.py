"""Shared host-neutral runtime contract helpers for agent execution surfaces."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import re
from typing import Any
from typing import Iterator
from typing import Mapping

from odylith.runtime.common import host_runtime as host_runtime_contract


AGENT_STREAM_PATH = "odylith/compass/runtime/agent-stream.v1.jsonl"
LEGACY_AGENT_STREAM_PATHS: tuple[str, ...] = ("odylith/compass/runtime/codex-stream.v1.jsonl",)
AGENT_EVENT_KEY = "recent_agent_events"
LEGACY_AGENT_EVENT_KEYS: tuple[str, ...] = ("recent_codex_events",)
AGENT_HOT_PATH_PROFILE = "agent_hot_path"
LEGACY_AGENT_HOT_PATH_PROFILES: tuple[str, ...] = ("codex_hot_path",)
DEFAULT_AGENT_EVENT_PREFIX = "agent"
DEFAULT_AGENT_AUTHOR = "assistant"
DEFAULT_AGENT_SOURCE = "assistant"
_DEFAULT_SESSION_TOKEN_PREFIX = "agent"
_SESSION_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")
_HOST_SESSION_ENV_KEYS: tuple[str, ...] = (
    "CODEX_THREAD_ID",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_SESSION_ID",
)
_HOST_SESSION_ENV_KEYS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "codex": ("CODEX_THREAD_ID",),
    "claude": ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"),
}

ANALYSIS_MEDIUM_PROFILE = "analysis_medium"
ANALYSIS_HIGH_PROFILE = "analysis_high"
FAST_WORKER_PROFILE = "fast_worker"
WRITE_MEDIUM_PROFILE = "write_medium"
WRITE_HIGH_PROFILE = "write_high"
FRONTIER_HIGH_PROFILE = "frontier_high"
FRONTIER_XHIGH_PROFILE = "frontier_xhigh"

CANONICAL_EXECUTION_PROFILES: tuple[str, ...] = (
    ANALYSIS_MEDIUM_PROFILE,
    ANALYSIS_HIGH_PROFILE,
    FAST_WORKER_PROFILE,
    WRITE_MEDIUM_PROFILE,
    WRITE_HIGH_PROFILE,
    FRONTIER_HIGH_PROFILE,
    FRONTIER_XHIGH_PROFILE,
)

_EXECUTION_PROFILE_ALIASES: dict[str, tuple[str, ...]] = {
    ANALYSIS_MEDIUM_PROFILE: ("mini_medium",),
    ANALYSIS_HIGH_PROFILE: ("mini_high",),
    FAST_WORKER_PROFILE: ("spark_medium",),
    WRITE_MEDIUM_PROFILE: ("codex_medium",),
    WRITE_HIGH_PROFILE: ("codex_high",),
    FRONTIER_HIGH_PROFILE: ("gpt54_high",),
    FRONTIER_XHIGH_PROFILE: ("gpt54_xhigh",),
}

_ALIASED_EXECUTION_PROFILES: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _EXECUTION_PROFILE_ALIASES.items()
    for alias in aliases
}

_ALIASED_STREAM_PATHS: dict[str, str] = {
    AGENT_STREAM_PATH: AGENT_STREAM_PATH,
    **{legacy: AGENT_STREAM_PATH for legacy in LEGACY_AGENT_STREAM_PATHS},
}

_CODEX_HOST_FAMILY = "codex"
_CLAUDE_HOST_FAMILY = "claude"

# Host-family axis for the canonical execution profile ladder. Every validated
# host family must return a non-empty model for every canonical profile; unknown
# hosts fall through to an empty model via `execution_profile_runtime_fields`.
_EXECUTION_PROFILE_RUNTIME_FIELDS_BY_HOST: dict[str, dict[str, tuple[str, str]]] = {
    _CODEX_HOST_FAMILY: {
        ANALYSIS_MEDIUM_PROFILE: ("gpt-5.4-mini", "medium"),
        ANALYSIS_HIGH_PROFILE: ("gpt-5.4-mini", "high"),
        FAST_WORKER_PROFILE: ("gpt-5.3-codex-spark", "medium"),
        WRITE_MEDIUM_PROFILE: ("gpt-5.3-codex", "medium"),
        WRITE_HIGH_PROFILE: ("gpt-5.3-codex", "high"),
        FRONTIER_HIGH_PROFILE: ("gpt-5.4", "high"),
        FRONTIER_XHIGH_PROFILE: ("gpt-5.4", "xhigh"),
    },
    _CLAUDE_HOST_FAMILY: {
        ANALYSIS_MEDIUM_PROFILE: ("claude-haiku-4-5", "medium"),
        ANALYSIS_HIGH_PROFILE: ("claude-haiku-4-5", "high"),
        FAST_WORKER_PROFILE: ("claude-haiku-4-5", "medium"),
        WRITE_MEDIUM_PROFILE: ("claude-sonnet-4-6", "medium"),
        WRITE_HIGH_PROFILE: ("claude-sonnet-4-6", "high"),
        FRONTIER_HIGH_PROFILE: ("claude-opus-4-6", "high"),
        FRONTIER_XHIGH_PROFILE: ("claude-opus-4-6", "xhigh"),
    },
}


def normalize_token(value: Any) -> str:
    """Normalize free-form text into the contract's canonical token shape."""
    return " ".join(str(value or "").split()).strip().lower().replace("-", "_").replace(" ", "_")


def canonical_execution_profile(value: Any) -> str:
    """Resolve canonical execution-profile names and their legacy aliases."""
    token = normalize_token(value)
    if not token:
        return ""
    if token in CANONICAL_EXECUTION_PROFILES:
        return token
    return _ALIASED_EXECUTION_PROFILES.get(token, token)


def execution_profile_aliases(value: Any) -> tuple[str, ...]:
    """Return the legacy aliases that map onto the canonical profile."""
    canonical = canonical_execution_profile(value)
    if not canonical:
        return ()
    return _EXECUTION_PROFILE_ALIASES.get(canonical, ())


def execution_profile_runtime_fields(
    value: Any,
    *,
    host_runtime: Any = "",
    host_capabilities: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """Resolve the model and reasoning tier for a profile on the active host."""
    canonical = canonical_execution_profile(value)
    if not canonical:
        return "", ""
    capabilities = (
        dict(host_capabilities)
        if isinstance(host_capabilities, Mapping)
        else host_runtime_contract.resolve_host_capabilities(host_runtime)
    )
    host_family = str(capabilities.get("host_family") or "").strip().lower()
    host_table = _EXECUTION_PROFILE_RUNTIME_FIELDS_BY_HOST.get(host_family, {})
    model, reasoning_effort = host_table.get(canonical, ("", ""))
    if not bool(capabilities.get("supports_explicit_model_selection")):
        return "", reasoning_effort
    return model, reasoning_effort


def execution_profile_runtime_fields_with_fallback(
    value: Any,
    *,
    host_runtime: Any = "",
    host_capabilities: Mapping[str, Any] | None = None,
    fallback_host_runtime: Any = "codex_cli",
) -> tuple[str, str]:
    """Resolve runtime fields, then fill hostless gaps from an explicit fallback host."""

    model, reasoning_effort = execution_profile_runtime_fields(
        value,
        host_runtime=host_runtime,
        host_capabilities=host_capabilities,
    )
    if model and reasoning_effort:
        return model, reasoning_effort
    fallback_model, fallback_reasoning_effort = execution_profile_runtime_fields(
        value,
        host_runtime=fallback_host_runtime,
    )
    return model or fallback_model, reasoning_effort or fallback_reasoning_effort


@contextlib.contextmanager
def codex_host_runtime_environment_if_missing(
    *,
    session_id: str = "odylith-hostless-audit",
) -> Iterator[None]:
    """Temporarily give hostless audit code a Codex runtime identity."""

    if host_runtime_contract.detect_host_runtime():
        yield
        return
    prior = {key: os.environ.get(key) for key in ("CODEX_THREAD_ID", "CODEX_SHELL")}
    os.environ["CODEX_THREAD_ID"] = session_id
    os.environ["CODEX_SHELL"] = "1"
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def canonical_stream_token(value: Any) -> str:
    """Resolve legacy stream paths onto the canonical agent stream path."""
    token = str(value or "").strip().replace("\\", "/")
    if not token:
        return AGENT_STREAM_PATH
    return _ALIASED_STREAM_PATHS.get(token, token)


def candidate_stream_tokens(value: Any = "") -> tuple[str, ...]:
    """Return the ordered stream-path candidates to probe for an agent ledger."""
    requested = str(value or "").strip().replace("\\", "/")
    canonical = canonical_stream_token(requested)
    candidates: list[str] = []
    for token in (requested, canonical, *LEGACY_AGENT_STREAM_PATHS):
        normalized = str(token or "").strip().replace("\\", "/")
        if not normalized or normalized in candidates:
            continue
        candidates.append(normalized)
    if AGENT_STREAM_PATH not in candidates:
        candidates.insert(0, AGENT_STREAM_PATH)
    return tuple(candidates)


def resolve_agent_stream_path(*, repo_root: Path, value: Any = "") -> Path:
    """Resolve the best existing agent stream path under the repo root."""
    root = Path(repo_root).resolve()
    requested = str(value or "").strip()
    if requested:
        explicit = Path(requested)
        if explicit.is_absolute():
            return explicit.resolve()
    for token in candidate_stream_tokens(value):
        candidate = (root / token).resolve()
        if candidate.exists():
            return candidate
    return (root / AGENT_STREAM_PATH).resolve()


def is_agent_hot_path_profile(value: Any) -> bool:
    """Return whether the profile token names the canonical agent hot path."""
    token = normalize_token(value)
    return token == AGENT_HOT_PATH_PROFILE or token in LEGACY_AGENT_HOT_PATH_PROFILES


def canonical_delivery_profile(value: Any) -> str:
    """Normalize delivery profile names while preserving unknown future tokens."""
    token = normalize_token(value)
    if not token:
        return ""
    if is_agent_hot_path_profile(token):
        return AGENT_HOT_PATH_PROFILE
    return token


def default_event_metadata() -> tuple[str, str]:
    """Return the default author and source fields for agent timeline events."""
    return DEFAULT_AGENT_AUTHOR, DEFAULT_AGENT_SOURCE


def normalize_session_token(value: Any) -> str:
    """Normalize host-provided session identifiers for ledger-safe use."""
    return _SESSION_TOKEN_RE.sub("-", str(value or "").strip()).strip("-")


def _ordered_host_session_env_keys(host_family: str = "") -> tuple[str, ...]:
    """Return host-session env keys with the active host family ordered first."""
    family = str(host_family or "").strip().lower()
    ordered: list[str] = []
    for key in (*_HOST_SESSION_ENV_KEYS_BY_FAMILY.get(family, ()), *_HOST_SESSION_ENV_KEYS):
        if key not in ordered:
            ordered.append(key)
    return tuple(ordered)


def default_host_session_id(
    *,
    environ: Mapping[str, str] | None = None,
    host_family: str = "",
) -> str:
    """Return the best available host session id from the environment."""
    env = os.environ if environ is None else environ
    family = str(host_family or "").strip().lower()
    preferred_keys = _ordered_host_session_env_keys(host_family)
    if family:
        preferred_keys = _HOST_SESSION_ENV_KEYS_BY_FAMILY.get(family, ())
    for key in preferred_keys:
        token = normalize_session_token(env.get(key, ""))
        if token:
            return token
    if family:
        return ""
    for key, value in env.items():
        normalized_key = str(key or "").strip().upper()
        if not normalized_key.endswith(("_THREAD_ID", "_SESSION_ID")):
            continue
        if "CODEX" not in normalized_key and "CLAUDE" not in normalized_key:
            continue
        token = normalize_session_token(value)
        if token:
            return token
    return ""


def resolve_hook_session_id(
    payload: Mapping[str, Any] | None,
    *,
    host_family: str = "",
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve one stable hook session id without fragmenting by turn.

    Hook payloads may expose both chat-scoped ids (`session_id`, `thread_id`)
    and turn-scoped ids (`turn_id`). The intervention ledger, replay, and
    status surfaces need the stable chat identity whenever it exists, so the
    host environment wins over a payload-only `turn_id`.
    """
    mapping = payload if isinstance(payload, Mapping) else {}
    for key in ("session_id", "thread_id"):
        token = normalize_session_token(mapping.get(key, ""))
        if token:
            return token
    default = default_host_session_id(environ=environ, host_family=host_family)
    if default:
        return default
    turn_id = normalize_session_token(mapping.get("turn_id", ""))
    if turn_id:
        return turn_id
    return synthetic_host_session_token(host_family)


def fallback_session_token(value: Any = "", *, pid: int | None = None) -> str:
    """Return a stable session token even when the host exposes no session id."""
    token = normalize_session_token(value)
    if token:
        return token
    return f"{_DEFAULT_SESSION_TOKEN_PREFIX}-{pid if pid is not None else os.getpid()}"


def synthetic_host_session_token(host_family: Any = "", *, pid: int | None = None) -> str:
    """Return a host-local synthetic session id that cannot bleed across hosts."""
    family = normalize_token(host_family) or "host"
    suffix = pid if pid is not None else os.getpid()
    return normalize_session_token(f"{family}-{_DEFAULT_SESSION_TOKEN_PREFIX}-{suffix}")


def timeline_event_id(*, kind: Any, index: Any, ts_iso: Any) -> str:
    """Build the canonical timeline event id used by agent stream ledgers."""
    normalized_kind = normalize_token(kind) or "event"
    normalized_index = str(index if index is not None else "").strip() or "0"
    normalized_ts = str(ts_iso or "").strip()
    return f"{DEFAULT_AGENT_EVENT_PREFIX}:{normalized_kind}:{normalized_index}:{normalized_ts}"
