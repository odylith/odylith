"""Shared host-neutral runtime contract helpers for agent execution surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any


AGENT_STREAM_PATH = "odylith/compass/runtime/agent-stream.v1.jsonl"
LEGACY_AGENT_STREAM_PATHS: tuple[str, ...] = ("odylith/compass/runtime/codex-stream.v1.jsonl",)
AGENT_EVENT_KEY = "recent_agent_events"
LEGACY_AGENT_EVENT_KEYS: tuple[str, ...] = ("recent_codex_events",)
AGENT_HOT_PATH_PROFILE = "agent_hot_path"
LEGACY_AGENT_HOT_PATH_PROFILES: tuple[str, ...] = ("codex_hot_path",)

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


def normalize_token(value: Any) -> str:
    return " ".join(str(value or "").split()).strip().lower().replace("-", "_").replace(" ", "_")


def canonical_execution_profile(value: Any) -> str:
    token = normalize_token(value)
    if not token:
        return ""
    if token in CANONICAL_EXECUTION_PROFILES:
        return token
    return _ALIASED_EXECUTION_PROFILES.get(token, token)


def execution_profile_aliases(value: Any) -> tuple[str, ...]:
    canonical = canonical_execution_profile(value)
    if not canonical:
        return ()
    return _EXECUTION_PROFILE_ALIASES.get(canonical, ())


def canonical_stream_token(value: Any) -> str:
    token = str(value or "").strip().replace("\\", "/")
    if not token:
        return AGENT_STREAM_PATH
    return _ALIASED_STREAM_PATHS.get(token, token)


def candidate_stream_tokens(value: Any = "") -> tuple[str, ...]:
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
    token = normalize_token(value)
    return token == AGENT_HOT_PATH_PROFILE or token in LEGACY_AGENT_HOT_PATH_PROFILES


def canonical_delivery_profile(value: Any) -> str:
    token = normalize_token(value)
    if not token:
        return ""
    if is_agent_hot_path_profile(token):
        return AGENT_HOT_PATH_PROFILE
    return token
