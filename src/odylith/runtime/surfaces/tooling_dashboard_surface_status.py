from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.governance import dashboard_refresh_contract


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%SZ")


def build_surface_runtime_status(
    *,
    repo_root: Path,
    shell_rendered_utc: str,
) -> dict[str, dict[str, Any]]:
    compass_status = _build_compass_surface_status(
        repo_root=Path(repo_root).resolve(),
        shell_rendered_utc=shell_rendered_utc,
    )
    if not compass_status:
        return {}
    return {"compass": compass_status}


def _build_compass_surface_status(
    *,
    repo_root: Path,
    shell_rendered_utc: str,
) -> dict[str, Any]:
    del shell_rendered_utc
    payload = _read_json_object(repo_root / "odylith" / "compass" / "runtime" / "current.v1.json")
    if not payload:
        return {}

    generated_utc = str(payload.get("generated_utc", "")).strip()
    runtime_contract = payload.get("runtime_contract")
    contract = dict(runtime_contract) if isinstance(runtime_contract, Mapping) else {}
    last_refresh_attempt = contract.get("last_refresh_attempt")
    attempt = dict(last_refresh_attempt) if isinstance(last_refresh_attempt, Mapping) else {}
    failure_status = _failed_full_refresh_posture(
        payload=payload,
        generated_utc=generated_utc,
        last_refresh_attempt=attempt,
    )
    if failure_status:
        return failure_status
    return {}


def _failed_full_refresh_posture(
    *,
    payload: Mapping[str, Any],
    generated_utc: str,
    last_refresh_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    status = str(last_refresh_attempt.get("status", "")).strip().lower()
    requested_profile = dashboard_refresh_contract.normalize_compass_refresh_profile(
        str(last_refresh_attempt.get("requested_profile", ""))
    )
    if status != "failed" or requested_profile != "full":
        return {}
    warning = str(payload.get("warning", "")).strip()
    if not warning:
        warning = (
            "Requested Compass full refresh failed before a fresh payload was written. "
            f"Showing the prior runtime snapshot from {generated_utc or 'the last successful render'}."
        )
    meta_parts = []
    if generated_utc:
        meta_parts.append(f"Snapshot: {generated_utc}")
    attempted_utc = str(last_refresh_attempt.get("attempted_utc", "")).strip()
    if attempted_utc:
        meta_parts.append(f"Attempted: {attempted_utc}")
    meta_parts.append(
        "Next: "
        + dashboard_refresh_contract.dashboard_refresh_failure_command(
            surface="compass",
            compass_refresh_profile=requested_profile,
        )
    )
    return {
        "visible": True,
        "tone": "warning",
        "kicker": "Compass refresh failed",
        "title": "Showing prior Compass snapshot",
        "body": warning,
        "meta": " · ".join(meta_parts),
        "showReload": False,
        "reloadLabel": "",
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}
