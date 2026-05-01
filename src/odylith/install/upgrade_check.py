"""Remote upgrade advisory checks with conservative local caching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request

from odylith.install.fs import atomic_write_text
from odylith.install.state import AUTHORITATIVE_RELEASE_REPO
from odylith.install.versioning import normalize_version, version_key

UPGRADE_CHECK_SCHEMA_VERSION = "odylith-upgrade-check.v1"
DEFAULT_CHECK_INTERVAL_HOURS = 24 * 7
DEFAULT_TIMEOUT_SECONDS = 2.5
UPGRADE_CHECK_MODE_ENV = "ODYLITH_UPGRADE_CHECK"
UPGRADE_CHECK_INTERVAL_ENV = "ODYLITH_UPGRADE_CHECK_INTERVAL_HOURS"
UPGRADE_CHECK_TIMEOUT_ENV = "ODYLITH_UPGRADE_CHECK_TIMEOUT_SECONDS"
UPGRADE_CHECK_URL_ENV = "ODYLITH_UPGRADE_CHECK_URL"

Urlopen = Callable[..., Any]


@dataclass(frozen=True)
class UpgradeCheckResult:
    status: str
    current_version: str
    latest_version: str = ""
    latest_tag: str = ""
    release_url: str = ""
    published_at: str = ""
    checked_at: str = ""
    next_check_after: str = ""
    from_cache: bool = False
    disabled: bool = False
    error: str = ""
    cache_path: Path | None = None

    @property
    def update_available(self) -> bool:
        if not self.latest_version or not self.current_version:
            return False
        return version_key(self.latest_version) > version_key(self.current_version)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": UPGRADE_CHECK_SCHEMA_VERSION,
            "status": self.status,
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "latest_tag": self.latest_tag,
            "release_url": self.release_url,
            "published_at": self.published_at,
            "checked_at": self.checked_at,
            "next_check_after": self.next_check_after,
            "from_cache": self.from_cache,
            "disabled": self.disabled,
            "update_available": self.update_available,
            "error": self.error,
            "cache_path": str(self.cache_path) if self.cache_path is not None else "",
        }


def upgrade_check_state_path(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / ".odylith" / "state" / "upgrade-check.v1.json"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _parse_datetime(value: object) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _env_flag_disabled() -> bool:
    token = str(os.environ.get(UPGRADE_CHECK_MODE_ENV) or "").strip().lower()
    return token in {"0", "false", "no", "off", "disabled"}


def _float_env(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _check_interval() -> timedelta:
    hours = _float_env(
        UPGRADE_CHECK_INTERVAL_ENV,
        float(DEFAULT_CHECK_INTERVAL_HOURS),
        minimum=1.0,
        maximum=24.0 * 30.0,
    )
    return timedelta(hours=hours)


def _timeout_seconds() -> float:
    return _float_env(
        UPGRADE_CHECK_TIMEOUT_ENV,
        DEFAULT_TIMEOUT_SECONDS,
        minimum=0.25,
        maximum=10.0,
    )


def _default_release_url(repo: str) -> str:
    return f"https://api.github.com/repos/{str(repo or AUTHORITATIVE_RELEASE_REPO).strip()}/releases/latest"


def _release_url(repo: str) -> str:
    return str(os.environ.get(UPGRADE_CHECK_URL_ENV) or "").strip() or _default_release_url(repo)


def _load_payload(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _payload_to_result(
    payload: Mapping[str, object],
    *,
    current_version: str,
    cache_path: Path,
    from_cache: bool,
) -> UpgradeCheckResult:
    latest_version = normalize_version(payload.get("latest_version") or payload.get("version") or "")
    latest_tag = str(payload.get("latest_tag") or payload.get("tag") or "").strip()
    return UpgradeCheckResult(
        status=str(payload.get("status") or "cached").strip() or "cached",
        current_version=normalize_version(current_version or payload.get("current_version") or ""),
        latest_version=latest_version,
        latest_tag=latest_tag,
        release_url=str(payload.get("release_url") or "").strip(),
        published_at=str(payload.get("published_at") or "").strip(),
        checked_at=str(payload.get("checked_at") or "").strip(),
        next_check_after=str(payload.get("next_check_after") or "").strip(),
        from_cache=from_cache,
        disabled=bool(payload.get("disabled")),
        error=str(payload.get("error") or "").strip(),
        cache_path=cache_path,
    )


def load_cached_upgrade_check(
    *,
    repo_root: str | Path,
    current_version: str = "",
) -> UpgradeCheckResult | None:
    path = upgrade_check_state_path(repo_root=repo_root)
    payload = _load_payload(path)
    if not payload:
        return None
    return _payload_to_result(payload, current_version=current_version, cache_path=path, from_cache=True)


def _cache_fresh(payload: Mapping[str, object], *, now: datetime) -> bool:
    next_check_after = _parse_datetime(payload.get("next_check_after"))
    return bool(next_check_after and now < next_check_after)


def _write_result(result: UpgradeCheckResult) -> None:
    if result.cache_path is None:
        return
    result.cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.as_dict()
    payload.pop("from_cache", None)
    payload.pop("cache_path", None)
    atomic_write_text(
        result.cache_path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _extract_release(payload: Mapping[str, Any]) -> tuple[str, str, str, str]:
    tag = str(payload.get("tag_name") or payload.get("tag") or payload.get("latest_tag") or "").strip()
    version = normalize_version(payload.get("version") or tag)
    release_url = str(payload.get("html_url") or payload.get("release_url") or "").strip()
    published_at = str(payload.get("published_at") or "").strip()
    return version, tag, release_url, published_at


def check_for_available_upgrade(
    *,
    repo_root: str | Path,
    current_version: str,
    release_repo: str = AUTHORITATIVE_RELEASE_REPO,
    force: bool = False,
    offline: bool = False,
    now: datetime | None = None,
    urlopen: Urlopen | None = None,
) -> UpgradeCheckResult:
    path = upgrade_check_state_path(repo_root=repo_root)
    normalized_current = normalize_version(current_version)
    now_utc = (now or _now_utc()).astimezone(UTC)
    cached_payload = _load_payload(path)
    if offline:
        cached = _payload_to_result(
            cached_payload,
            current_version=normalized_current,
            cache_path=path,
            from_cache=True,
        ) if cached_payload else None
        return cached or UpgradeCheckResult(
            status="offline_no_cache",
            current_version=normalized_current,
            checked_at=now_utc.isoformat(),
            cache_path=path,
        )
    if _env_flag_disabled():
        return UpgradeCheckResult(
            status="disabled",
            current_version=normalized_current,
            checked_at=now_utc.isoformat(),
            disabled=True,
            cache_path=path,
        )
    if cached_payload and not force and _cache_fresh(cached_payload, now=now_utc):
        return _payload_to_result(
            cached_payload,
            current_version=normalized_current,
            cache_path=path,
            from_cache=True,
        )

    checked_at = now_utc.isoformat()
    next_check_after = (now_utc + _check_interval()).isoformat()
    try:
        request = urllib.request.Request(
            _release_url(release_repo),
            headers={
                "Accept": "application/vnd.github+json, application/json",
                "User-Agent": "odylith-upgrade-check",
            },
        )
        opener = urlopen or urllib.request.urlopen
        with opener(request, timeout=_timeout_seconds()) as response:  # noqa: S310 - advisory metadata only; upgrade verifies signed assets.
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("release endpoint did not return a JSON object")
        latest_version, latest_tag, release_url, published_at = _extract_release(payload)
        if not latest_version:
            raise ValueError("release endpoint did not include a version or tag")
        status = "upgrade_available" if version_key(latest_version) > version_key(normalized_current) else "current"
        result = UpgradeCheckResult(
            status=status,
            current_version=normalized_current,
            latest_version=latest_version,
            latest_tag=latest_tag or f"v{latest_version}",
            release_url=release_url,
            published_at=published_at,
            checked_at=checked_at,
            next_check_after=next_check_after,
            cache_path=path,
        )
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        result = UpgradeCheckResult(
            status="unavailable",
            current_version=normalized_current,
            checked_at=checked_at,
            next_check_after=next_check_after,
            error=f"{type(exc).__name__}: {exc}",
            cache_path=path,
        )
    _write_result(result)
    return result


def upgrade_check_lines(result: UpgradeCheckResult, *, explicit: bool = False) -> tuple[str, ...]:
    if result.disabled:
        return ("Upgrade check: disabled by ODYLITH_UPGRADE_CHECK.",) if explicit else ()
    if result.update_available:
        lines = [
            (
                f"Upgrade available: Odylith {result.latest_version} "
                f"(active {result.current_version or 'unknown'}). "
                "Run `./.odylith/bin/odylith upgrade --repo-root .`."
            )
        ]
        if result.release_url:
            lines.append(f"Release: {result.release_url}")
        if result.from_cache and result.next_check_after:
            lines.append(f"Upgrade check cache: next remote check after {result.next_check_after}.")
        return tuple(lines)
    if result.status in {"current", "cached"} and explicit:
        return (f"Upgrade check: current at {result.latest_version or result.current_version or 'unknown'}.",)
    if result.status == "offline_no_cache" and explicit:
        return ("Upgrade check: offline mode has no cached remote result yet.",)
    if result.status == "unavailable" and explicit:
        return (
            "Upgrade check: remote advisory unavailable or blocked; this is non-fatal.",
            "Odylith will retry after the cache interval. Set ODYLITH_UPGRADE_CHECK=off to disable remote checks.",
        )
    return ()
