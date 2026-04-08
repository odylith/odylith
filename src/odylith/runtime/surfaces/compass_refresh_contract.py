from __future__ import annotations

from typing import Any, Mapping


DEFAULT_REFRESH_PROFILE = "shell-safe"
FULL_REFRESH_SCOPED_PROVIDER_MAX_WORKERS = 6
DEFAULT_SCOPED_PROVIDER_MAX_WORKERS = 4


def normalize_refresh_profile(value: str, *, default: str = DEFAULT_REFRESH_PROFILE) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"full", "shell-safe"}:
        return normalized
    return str(default).strip().lower() or DEFAULT_REFRESH_PROFILE


def full_refresh_requested(refresh_profile: str) -> bool:
    return normalize_refresh_profile(refresh_profile) == "full"


def prefer_live_provider(refresh_profile: str) -> bool:
    return full_refresh_requested(refresh_profile)


def allow_stale_cache_recovery(refresh_profile: str) -> bool:
    return not full_refresh_requested(refresh_profile)


def allow_deterministic_fallback(refresh_profile: str) -> bool:
    return not full_refresh_requested(refresh_profile)


def scoped_provider_max_workers(refresh_profile: str, *, scoped_packets: int) -> int:
    ceiling = (
        FULL_REFRESH_SCOPED_PROVIDER_MAX_WORKERS
        if full_refresh_requested(refresh_profile)
        else DEFAULT_SCOPED_PROVIDER_MAX_WORKERS
    )
    return max(1, min(int(ceiling), int(scoped_packets)))


def brief_satisfies_full_refresh(brief: Mapping[str, Any]) -> bool:
    status = str(brief.get("status", "")).strip().lower()
    source = str(brief.get("source", "")).strip().lower()
    notice = brief.get("notice")
    has_notice = isinstance(notice, Mapping) and any(str(notice.get(key, "")).strip() for key in ("reason", "title", "message"))
    return status == "ready" and source in {"provider", "cache"} and not has_notice
