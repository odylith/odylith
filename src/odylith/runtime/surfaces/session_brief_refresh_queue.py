"""Shared stale-brief refresh queue for host SessionStart hooks."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.context_engine import odylith_context_cache


_CURRENT_RUNTIME_PATH = "odylith/compass/runtime/current.v1.json"
_QUEUE_STATE_PATH = Path(".odylith/runtime/latency-cache/session-brief-refresh-queue.v1.json")


def queue_refresh_if_briefs_stale(*, repo_root: Path, threshold_seconds: int) -> bool:
    try:
        runtime_path = Path(repo_root).resolve() / _CURRENT_RUNTIME_PATH
        if not runtime_path.is_file():
            return False
        with runtime_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        standup_brief = payload.get("standup_brief")
        if not isinstance(standup_brief, Mapping):
            return False
        now = datetime.now(tz=timezone.utc)
        for window_key in ("24h", "48h"):
            brief = standup_brief.get(window_key)
            if not isinstance(brief, Mapping):
                continue
            generated = str(brief.get("generated_utc", "")).strip()
            if not generated:
                continue
            try:
                ts = datetime.fromisoformat(generated.replace("Z", "+00:00"))
                age_seconds = (now - ts).total_seconds()
            except (ValueError, TypeError):
                continue
            if age_seconds <= int(threshold_seconds):
                continue
            marker = f"{window_key}:{generated}"
            if _already_queued(repo_root=repo_root, marker=marker):
                return False
            launcher = Path(repo_root).resolve() / ".odylith" / "bin" / "odylith"
            if not launcher.is_file():
                return False
            subprocess.Popen(
                [str(launcher), "compass", "refresh", "--repo-root", str(repo_root), "--wait"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            _record_queue(repo_root=repo_root, marker=marker, queued_at=now)
            return True
        return False
    except Exception:
        return False


def _already_queued(*, repo_root: Path, marker: str) -> bool:
    payload = _queue_state(repo_root=repo_root)
    return str(payload.get("marker", "")).strip() == str(marker).strip()


def _record_queue(*, repo_root: Path, marker: str, queued_at: datetime) -> None:
    odylith_context_cache.write_json_if_changed(
        repo_root=repo_root,
        path=(Path(repo_root).resolve() / _QUEUE_STATE_PATH).resolve(),
        payload={
            "marker": str(marker).strip(),
            "queued_at_utc": queued_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
    )


def _queue_state(*, repo_root: Path) -> dict[str, Any]:
    path = (Path(repo_root).resolve() / _QUEUE_STATE_PATH).resolve()
    return odylith_context_cache.read_json_object(path)


__all__ = ["queue_refresh_if_briefs_stale"]
