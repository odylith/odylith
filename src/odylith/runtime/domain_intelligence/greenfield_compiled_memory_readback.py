"""Readback checks for compiled greenfield memory transaction records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.proposal_memory import acceptance_event_signature
from odylith.runtime.domain_intelligence.proposal_memory import compiled_project_brief_record_text


def raise_for_compiled_memory_readback(
    *,
    root: Path,
    prewrite_package: GreenfieldCompletionPackage,
    memory_record: Mapping[str, Any],
) -> None:
    """Validate committed memory surfaces against the compiled transaction preview."""

    event = memory_record.get("event") if isinstance(memory_record.get("event"), Mapping) else {}
    accepted_at = str(event.get("ts_iso", "")).strip()
    expected_accepted_project = dict(prewrite_package.accepted_project_preview or {})
    expected_accepted_project["accepted_at"] = accepted_at
    expected_accepted_project = _json_comparable_mapping(expected_accepted_project)
    actual_accepted_project = _read_json_mapping(root / "odylith/runtime/source/accepted-project.v1.json")
    expected_project_brief = compiled_project_brief_record_text(
        prewrite_package.project_brief_record_text,
        accepted_at=accepted_at,
    )
    actual_project_brief = _read_text(root / "odylith/runtime/source/project-brief.v1.md")
    issues: list[str] = []
    if actual_accepted_project != expected_accepted_project:
        issues.append("accepted project record does not match compiled transaction preview")
    if actual_project_brief != expected_project_brief:
        issues.append("project brief record does not match compiled transaction text")
    if not _compass_event_matches_compiled_preview(root=root, event=event, prewrite_package=prewrite_package):
        issues.append("Compass memory event does not match compiled transaction preview")
    persisted_event = _read_persisted_compass_event(root=root, prewrite_package=prewrite_package, memory_record=memory_record)
    if not persisted_event:
        issues.append("Compass memory stream does not contain compiled transaction event")
    elif _json_comparable_mapping(persisted_event) != _json_comparable_mapping(event):
        issues.append("Compass memory event record does not match persisted stream event")
    if issues:
        detail = "\n".join(f"- {issue}" for issue in dedupe_strings(issues))
        raise ValueError(f"greenfield post-confirm compiled memory readback failed with {len(issues)} issue(s):\n{detail}")


def _compass_event_matches_compiled_preview(
    *,
    root: Path,
    event: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage,
) -> bool:
    preview = prewrite_package.compass_memory_preview
    if not isinstance(preview, Mapping) or not isinstance(event, Mapping) or not event:
        return False
    if acceptance_event_signature(repo_root=root, event=event) != acceptance_event_signature(repo_root=root, event=preview):
        return False
    for key in (
        "kind",
        "summary",
        "author",
        "source",
        "context",
        "headline_hint",
        "evidence_tier",
        "work_category",
    ):
        if key in preview and str(event.get(key, "")).strip() != str(preview.get(key, "")).strip():
            return False
    return True


def _read_persisted_compass_event(
    *,
    root: Path,
    prewrite_package: GreenfieldCompletionPackage,
    memory_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    stream_path = _memory_stream_path(root=root, memory_record=memory_record)
    if not stream_path.is_file():
        return {}
    for line in stream_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, Mapping) and _compass_event_matches_compiled_preview(
            root=root,
            event=event,
            prewrite_package=prewrite_package,
        ):
            return event
    return {}


def _memory_stream_path(*, root: Path, memory_record: Mapping[str, Any]) -> Path:
    token = str(memory_record.get("stream", "")).strip()
    if not token:
        return root / agent_runtime_contract.AGENT_STREAM_PATH
    path = Path(token).expanduser()
    return path if path.is_absolute() else root / path


def _json_comparable_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("compiled memory preview is not JSON-serializable for readback") from exc
    return normalized if isinstance(normalized, Mapping) else {}


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


__all__ = ["raise_for_compiled_memory_readback"]
