"""Compass Refresh Contract helpers for the Odylith surfaces layer."""

from __future__ import annotations

DEFAULT_REFRESH_PROFILE = "shell-safe"
SEALED_PRECONFIRM_REFRESH_PROFILE = "sealed-preconfirm"
DEFAULT_SCOPED_PROVIDER_MAX_WORKERS = 4
_SUPPORTED_REFRESH_PROFILES = {
    DEFAULT_REFRESH_PROFILE,
    SEALED_PRECONFIRM_REFRESH_PROFILE,
}


def normalize_refresh_profile(value: str, *, default: str = DEFAULT_REFRESH_PROFILE) -> str:
    fallback = str(default).strip().lower()
    if fallback not in _SUPPORTED_REFRESH_PROFILES:
        fallback = DEFAULT_REFRESH_PROFILE
    token = str(value).strip().lower()
    return token if token in _SUPPORTED_REFRESH_PROFILES else fallback


def allow_global_provider(refresh_profile: str) -> bool:
    del refresh_profile
    return False


def prefer_live_provider(refresh_profile: str) -> bool:
    del refresh_profile
    return False


def scoped_provider_max_workers(refresh_profile: str, *, scoped_packets: int) -> int:
    del refresh_profile
    return max(1, min(int(DEFAULT_SCOPED_PROVIDER_MAX_WORKERS), int(scoped_packets)))
