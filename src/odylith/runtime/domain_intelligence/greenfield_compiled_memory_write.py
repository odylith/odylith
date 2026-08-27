"""Persist precompiled Greenfield memory bytes without semantic interpretation."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.domain_intelligence.greenfield_acceptance_contract import (
    ACCEPTED_PROJECT_SOURCE_PATH,
    PROJECT_BRIEF_SOURCE_PATH,
)


def record_compiled_greenfield_acceptance(
    *,
    repo_root: Path,
    accepted_project_preview: Mapping[str, Any],
    project_brief_record_text: str,
    compass_memory_preview: Mapping[str, Any],
) -> dict[str, Any]:
    """Write only the JSON-ready memory already sealed before confirmation."""

    root = Path(repo_root).expanduser().resolve()
    event = _json_mapping(compass_memory_preview, label="compiled Compass memory preview")
    for key in ("kind", "summary", "ts_iso"):
        if not str(event.get(key) or "").strip():
            raise ValueError(f"compiled Compass memory preview is missing {key}")
    stream_path = root / agent_runtime_contract.AGENT_STREAM_PATH
    existing = _matching_event(stream_path, event)
    reused = existing is not None
    if existing is None:
        stream_path.parent.mkdir(parents=True, exist_ok=True)
        with stream_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        existing = event
    accepted_path = root / ACCEPTED_PROJECT_SOURCE_PATH
    accepted_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_path.write_text(
        json.dumps(
            _json_mapping(accepted_project_preview, label="compiled accepted-project preview"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    brief_path = root / PROJECT_BRIEF_SOURCE_PATH
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(str(project_brief_record_text or ""), encoding="utf-8")
    return {
        "recorded": True,
        "reused_existing": reused,
        "stream": Path(agent_runtime_contract.AGENT_STREAM_PATH).as_posix(),
        "accepted_project": Path(ACCEPTED_PROJECT_SOURCE_PATH).as_posix(),
        "project_brief": Path(PROJECT_BRIEF_SOURCE_PATH).as_posix(),
        "event": dict(existing),
    }


def _matching_event(path: Path, expected: Mapping[str, Any]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping) and _json_mapping(value, label="persisted Compass event") == expected:
            return dict(value)
    return None


def _json_mapping(value: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    try:
        normalized = json.loads(json.dumps(dict(value), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not JSON-serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError(f"{label} must be a JSON object")
    return normalized


__all__ = ["record_compiled_greenfield_acceptance"]
