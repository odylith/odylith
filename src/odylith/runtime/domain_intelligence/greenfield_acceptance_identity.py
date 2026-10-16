"""Semantic identity for pre-confirm greenfield acceptance memory."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import datetime as dt
import json
from pathlib import Path
import re
from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.domain_intelligence.proposal_memory import ACCEPTED_PROJECT_SOURCE_PATH
from odylith.runtime.domain_intelligence.proposal_memory import PROJECT_BRIEF_SOURCE_PATH


_ACCEPTED_AT_LINE = re.compile(r"(?m)^- accepted_at: ([^\r\n]+)$")
_ACCEPTED_PROJECT_CREATED_PATH_FIELDS = {
    "components": frozenset({"registry_path", "spec_path"}),
    "workstreams": frozenset({"idea_path"}),
}


def resolve_preconfirm_acceptance_timestamp(
    *,
    repo_root: Path,
    fresh_accepted_at: str,
    accepted_project_preview: Mapping[str, Any],
    project_brief_record_text: str,
    compass_memory_preview: Mapping[str, Any],
    portable_roots: Sequence[Path] = (),
) -> str:
    """Reuse a prior timestamp only when all accepted evidence is coherent."""

    fresh = str(fresh_accepted_at or "").strip()
    if not _valid_accepted_at(fresh):
        return fresh
    if str(accepted_project_preview.get("accepted_at", "")).strip() != fresh:
        return fresh
    if str(compass_memory_preview.get("ts_iso", "")).strip() != fresh:
        return fresh
    if _brief_accepted_at(project_brief_record_text) != fresh:
        return fresh

    root = Path(repo_root).expanduser().resolve()
    prior_project = _read_json_mapping(root / ACCEPTED_PROJECT_SOURCE_PATH)
    prior_brief = _read_text(root / PROJECT_BRIEF_SOURCE_PATH)
    prior_events = _read_compass_events(root / agent_runtime_contract.AGENT_STREAM_PATH)
    if prior_project is None or prior_brief is None or prior_events is None:
        return fresh

    prior_accepted_at = str(prior_project.get("accepted_at", "")).strip()
    if not _valid_accepted_at(prior_accepted_at):
        return fresh
    if _brief_accepted_at(prior_brief) != prior_accepted_at:
        return fresh

    roots = _portable_roots(root, portable_roots)
    expected_project = copy.deepcopy(dict(accepted_project_preview))
    expected_project["accepted_at"] = prior_accepted_at
    if _canonical_accepted_project(expected_project, roots=roots) != _canonical_accepted_project(
        prior_project,
        roots=roots,
    ):
        return fresh

    expected_brief = _brief_with_accepted_at(
        project_brief_record_text,
        accepted_at=prior_accepted_at,
    )
    if expected_brief is None or expected_brief != prior_brief:
        return fresh

    expected_event = copy.deepcopy(dict(compass_memory_preview))
    expected_event["ts_iso"] = prior_accepted_at
    canonical_event = _canonical_compass_event(expected_event, roots=roots)
    if not any(
        _canonical_compass_event(event, roots=roots) == canonical_event
        for event in prior_events
    ):
        return fresh
    return prior_accepted_at


def _read_json_mapping(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = _strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _read_compass_events(path: Path) -> tuple[dict[str, Any], ...] | None:
    text = _read_text(path)
    if text is None:
        return None
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = _strict_json_loads(line)
        except ValueError:
            return None
        if not isinstance(event, Mapping):
            return None
        events.append(dict(event))
    return tuple(events)


def _brief_accepted_at(text: str) -> str:
    matches = _ACCEPTED_AT_LINE.findall(str(text or ""))
    return matches[0].strip() if len(matches) == 1 else ""


def _strict_json_loads(text: str) -> Any:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise ValueError(f"duplicate JSON key: {key}")
            payload[key] = value
        return payload

    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


def _brief_with_accepted_at(text: str, *, accepted_at: str) -> str | None:
    if len(_ACCEPTED_AT_LINE.findall(str(text or ""))) != 1:
        return None
    return _ACCEPTED_AT_LINE.sub(f"- accepted_at: {accepted_at}", str(text), count=1)


def _valid_accepted_at(value: str) -> bool:
    token = str(value or "").strip()
    if not token or token == "prewrite":
        return False
    try:
        parsed = dt.datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _portable_roots(repo_root: Path, roots: Sequence[Path]) -> tuple[Path, ...]:
    resolved: list[Path] = []
    for value in (repo_root, *roots):
        path = Path(value).expanduser().resolve()
        if path not in resolved:
            resolved.append(path)
    return tuple(resolved)


def _canonical_accepted_project(value: Mapping[str, Any], *, roots: Sequence[Path]) -> dict[str, Any]:
    payload = _canonical_value(value)
    created = payload.get("created")
    if not isinstance(created, dict):
        return payload
    for group, path_fields in _ACCEPTED_PROJECT_CREATED_PATH_FIELDS.items():
        rows = created.get(group)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field in path_fields:
                token = row.get(field)
                if isinstance(token, str):
                    row[field] = _canonical_path_token(token, roots=roots)
    return payload


def _canonical_compass_event(value: Mapping[str, Any], *, roots: Sequence[Path]) -> dict[str, Any]:
    payload = _canonical_value(value)
    artifacts = payload.get("artifacts")
    if isinstance(artifacts, list):
        payload["artifacts"] = [
            _canonical_path_token(item, roots=roots) if isinstance(item, str) else item
            for item in artifacts
        ]
    return payload


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(item_key): _canonical_value(item)
            for item_key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _canonical_path_token(value: str, *, roots: Sequence[Path]) -> str:
    token = str(value)
    try:
        path = Path(token).expanduser()
    except (OSError, RuntimeError, ValueError):
        return token
    if path.is_absolute():
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError, ValueError):
            return token
        for root in roots:
            try:
                return resolved.relative_to(root).as_posix()
            except ValueError:
                continue
    return token


__all__ = ["resolve_preconfirm_acceptance_timestamp"]
