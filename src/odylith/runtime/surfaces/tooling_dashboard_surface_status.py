"""Tooling Dashboard Surface Status helpers for the Odylith surfaces layer."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.governance import dashboard_refresh_contract
from odylith.runtime.governance import release_truth_runtime

_COMPASS_STALE_RUNTIME_MINUTES = 90


def now_utc() -> str:
    """Return the current UTC timestamp in the shell-status format."""
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%SZ")


def build_surface_runtime_status(
    *,
    repo_root: Path,
    shell_rendered_utc: str,
) -> dict[str, dict[str, Any]]:
    """Build shell-surface warning payloads for runtime-backed dashboard surfaces."""
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
    """Build the shell status banner for Compass when runtime state warrants it."""
    payload = _read_json_object(repo_root / "odylith" / "compass" / "runtime" / "current.v1.json")
    if not payload:
        return {}

    generated_utc = str(payload.get("generated_utc", "")).strip()
    if str(payload.get("warning", "")).strip():
        return {}
    runtime_contract = payload.get("runtime_contract")
    contract = dict(runtime_contract) if isinstance(runtime_contract, Mapping) else {}
    last_refresh_attempt = contract.get("last_refresh_attempt")
    attempt = dict(last_refresh_attempt) if isinstance(last_refresh_attempt, Mapping) else {}
    failure_status = _failed_refresh_posture(
        payload=payload,
        generated_utc=generated_utc,
        shell_rendered_utc=str(shell_rendered_utc or "").strip(),
        last_refresh_attempt=attempt,
    )
    if failure_status:
        return failure_status
    source_truth_status = _source_truth_drift_posture(
        repo_root=repo_root,
        payload=payload,
    )
    if source_truth_status:
        return source_truth_status
    return {}


def _failed_refresh_posture(
    *,
    payload: Mapping[str, Any],
    generated_utc: str,
    shell_rendered_utc: str,
    last_refresh_attempt: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the warning banner when a relevant Compass refresh failed."""
    status = str(last_refresh_attempt.get("status", "")).strip().lower()
    if status != "failed":
        return {}
    attempted_utc = str(last_refresh_attempt.get("attempted_utc", "")).strip()
    if (
        _runtime_snapshot_is_stale_for_compass_banner(
            generated_utc=generated_utc,
            shell_rendered_utc=shell_rendered_utc,
        )
        and not _refresh_attempt_matches_snapshot(
            generated_utc=generated_utc,
            attempted_utc=attempted_utc,
        )
    ):
        return {}
    warning = str(payload.get("warning", "")).strip()
    if warning:
        return {}
    warning = (
        "Requested Compass refresh failed before a fresh payload was written. "
        f"Showing the prior runtime snapshot from {generated_utc or 'the last successful render'}."
    )
    meta_parts = []
    if generated_utc:
        meta_parts.append(f"Snapshot: {generated_utc}")
    if attempted_utc:
        meta_parts.append(f"Attempted: {attempted_utc}")
    meta_parts.append(
        "Next: "
        + dashboard_refresh_contract.dashboard_refresh_failure_command(
            surface="compass",
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


def _source_truth_drift_posture(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return any shell banner for Compass release-truth drift."""
    drift = release_truth_runtime.build_compass_runtime_truth_drift(
        repo_root=repo_root,
        runtime_payload=payload,
    )
    warning = str(drift.get("warning", "")).strip()
    if not warning:
        return {}
    # Compass already shows release-truth drift inside its own subtle header
    # status banner; suppress the duplicated shell-level warning slab.
    return {}


def _read_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk or return an empty dict on failure."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _parse_utc_token(value: str) -> dt.datetime | None:
    """Parse an ISO-like UTC token into an aware UTC datetime."""
    token = str(value or "").strip()
    if not token:
        return None
    normalized = token.replace("Z", "+00:00") if token.endswith("Z") else token
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def _runtime_snapshot_is_stale_for_compass_banner(
    *,
    generated_utc: str,
    shell_rendered_utc: str,
) -> bool:
    """Return whether the runtime snapshot is stale enough to justify the banner."""
    generated_at = _parse_utc_token(generated_utc)
    rendered_at = _parse_utc_token(shell_rendered_utc)
    if generated_at is None or rendered_at is None:
        return False
    age_minutes = (rendered_at - generated_at).total_seconds() / 60.0
    return age_minutes >= _COMPASS_STALE_RUNTIME_MINUTES


def _refresh_attempt_matches_snapshot(
    *,
    generated_utc: str,
    attempted_utc: str,
) -> bool:
    """Return whether the failed refresh attempt belongs to the shown snapshot."""
    generated_at = _parse_utc_token(generated_utc)
    attempted_at = _parse_utc_token(attempted_utc)
    if generated_at is None or attempted_at is None:
        return False
    gap_minutes = abs((attempted_at - generated_at).total_seconds()) / 60.0
    return gap_minutes <= _COMPASS_STALE_RUNTIME_MINUTES
