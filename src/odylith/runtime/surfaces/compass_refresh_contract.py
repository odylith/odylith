from __future__ import annotations

DEFAULT_REFRESH_PROFILE = "shell-safe"
FULL_REFRESH_PROFILE = "full"
DEFAULT_SCOPED_PROVIDER_MAX_WORKERS = 4
FULL_REFRESH_SCOPED_PROVIDER_MAX_WORKERS = 6


def normalize_refresh_profile(value: str, *, default: str = DEFAULT_REFRESH_PROFILE) -> str:
    token = str(value).strip().lower()
    if token in {DEFAULT_REFRESH_PROFILE, FULL_REFRESH_PROFILE}:
        return token
    fallback = str(default).strip().lower()
    return fallback if fallback in {DEFAULT_REFRESH_PROFILE, FULL_REFRESH_PROFILE} else DEFAULT_REFRESH_PROFILE


def full_refresh_requested(refresh_profile: str) -> bool:
    return normalize_refresh_profile(refresh_profile) == FULL_REFRESH_PROFILE


def prefer_live_provider(refresh_profile: str) -> bool:
    return full_refresh_requested(refresh_profile)


def allow_stale_cache_recovery(refresh_profile: str) -> bool:
    return not full_refresh_requested(refresh_profile)


def allow_deterministic_fallback(refresh_profile: str) -> bool:
    return not full_refresh_requested(refresh_profile)


def brief_satisfies_full_refresh(brief: object) -> bool:
    if not isinstance(brief, dict):
        return False
    if str(brief.get("status", "")).strip().lower() != "ready":
        return False
    if str(brief.get("notice", "")).strip():
        return False
    return str(brief.get("source", "")).strip().lower() in {"provider", "cache", "composed"}


def scoped_provider_max_workers(refresh_profile: str, *, scoped_packets: int) -> int:
    limit = (
        FULL_REFRESH_SCOPED_PROVIDER_MAX_WORKERS
        if full_refresh_requested(refresh_profile)
        else DEFAULT_SCOPED_PROVIDER_MAX_WORKERS
    )
    return max(1, min(int(limit), int(scoped_packets)))
