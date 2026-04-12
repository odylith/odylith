"""Wait-path settlement helpers for Compass standup brief maintenance."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.surfaces import compass_standup_brief_maintenance

_DEFAULT_SETTLE_TIMEOUT_SECONDS = 20.0
_DEFAULT_POLL_INTERVAL_SECONDS = 0.25
_CURRENT_RUNTIME_PATH = "odylith/compass/runtime/current.v1.json"


def provider_deferred_global_windows(*, repo_root: Path) -> tuple[str, ...]:
    """Return any global windows still stuck in transient provider-deferred state."""

    payload = odylith_context_cache.read_json_object((Path(repo_root).resolve() / _CURRENT_RUNTIME_PATH).resolve())
    standup_brief = payload.get("standup_brief") if isinstance(payload, Mapping) else {}
    if not isinstance(standup_brief, Mapping):
        return ()
    deferred: list[str] = []
    for window_key, brief in standup_brief.items():
        if not isinstance(brief, Mapping):
            continue
        diagnostics = brief.get("diagnostics") if isinstance(brief.get("diagnostics"), Mapping) else {}
        reason = str(diagnostics.get("reason", "")).strip().lower()
        if reason == "provider_deferred":
            deferred.append(str(window_key).strip())
    return tuple(sorted(token for token in deferred if token))


def settle_standup_maintenance(
    *,
    repo_root: Path,
    timeout_seconds: float = _DEFAULT_SETTLE_TIMEOUT_SECONDS,
    poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    """Drive or observe pending standup maintenance until it drains or backs off."""

    root = Path(repo_root).resolve()
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    poll_seconds = max(0.05, float(poll_interval_seconds))

    while True:
        if not provider_deferred_global_windows(repo_root=root):
            return {
                "status": "already_settled",
                "request_retained": False,
                "patched_current_runtime": False,
                "next_retry_delay_seconds": None,
                "next_retry_utc": "",
                "warmed": 0,
                "failed": 0,
            }
        request = odylith_context_cache.read_json_object(
            compass_standup_brief_maintenance.maintenance_request_path(repo_root=root)
        )
        if not compass_standup_brief_maintenance._request_has_entries(request):  # noqa: SLF001
            return {
                "status": "idle",
                "request_retained": False,
                "patched_current_runtime": False,
                "next_retry_delay_seconds": None,
                "next_retry_utc": "",
                "warmed": 0,
                "failed": 0,
            }

        state = compass_standup_brief_maintenance._load_state(repo_root=root)  # noqa: SLF001
        active_pid = int(state.get("active_pid", 0) or 0)
        if active_pid > 0 and compass_standup_brief_maintenance._pid_alive(active_pid):  # noqa: SLF001
            if time.monotonic() >= deadline:
                return {
                    "status": "timeout",
                    "request_retained": True,
                    "patched_current_runtime": False,
                    "next_retry_delay_seconds": None,
                    "next_retry_utc": "",
                    "warmed": 0,
                    "failed": 0,
                    "detail": f"maintenance worker {active_pid} did not settle before the wait budget expired",
                }
            time.sleep(poll_seconds)
            continue

        result = compass_standup_brief_maintenance.run_pending_request(
            repo_root=root,
            emit_output=False,
            keep_active_pid=False,
        )
        retained = bool(result.get("request_retained"))
        delay_seconds = result.get("next_retry_delay_seconds")
        if not retained:
            return {
                "status": "drained",
                **result,
            }
        if delay_seconds is not None and float(delay_seconds) > 0.0:
            return {
                "status": "backoff",
                **result,
            }
        if time.monotonic() >= deadline:
            return {
                "status": "timeout",
                **result,
                "detail": "standup maintenance stayed immediately retryable past the wait budget",
            }
        time.sleep(poll_seconds)
