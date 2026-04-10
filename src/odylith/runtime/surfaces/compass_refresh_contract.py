from __future__ import annotations

DEFAULT_REFRESH_PROFILE = "shell-safe"
DEFAULT_SCOPED_PROVIDER_MAX_WORKERS = 4


def normalize_refresh_profile(value: str, *, default: str = DEFAULT_REFRESH_PROFILE) -> str:
    del value
    fallback = str(default).strip().lower()
    return DEFAULT_REFRESH_PROFILE if fallback != DEFAULT_REFRESH_PROFILE else fallback


def prefer_live_provider(refresh_profile: str) -> bool:
    del refresh_profile
    return False


def allow_stale_cache_recovery(refresh_profile: str) -> bool:
    del refresh_profile
    return True


def allow_deterministic_fallback(refresh_profile: str) -> bool:
    del refresh_profile
    return True
def scoped_provider_max_workers(refresh_profile: str, *, scoped_packets: int) -> int:
    del refresh_profile
    return max(1, min(int(DEFAULT_SCOPED_PROVIDER_MAX_WORKERS), int(scoped_packets)))
