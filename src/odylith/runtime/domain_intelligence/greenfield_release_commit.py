"""Commit precompiled greenfield release-planning writes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import release_planning_contract


def materialize_compiled_release_target(
    *,
    repo_root: Path,
    release_selector: str,
    release_target_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Write the precompiled release target without rebuilding it from proposal text."""

    root = Path(repo_root).resolve()
    result = dict(release_target_result or {})
    release_row = _mapping(result.get("release"))
    release_id = str(release_row.get("release_id", "")).strip()
    if not release_id:
        raise ValueError("compiled release target is missing release.release_id")

    registry_document, event_documents, idea_specs = release_planning_authoring._load_governed_documents(  # noqa: SLF001
        repo_root=root,
    )
    releases = release_planning_authoring._registry_release_rows(registry_document)  # noqa: SLF001
    aliases = release_planning_authoring._registry_alias_map(registry_document)  # noqa: SLF001
    existing = release_planning_authoring._release_row_by_id(releases, release_id)  # noqa: SLF001
    desired_aliases = _desired_aliases(release_selector=release_selector, release_row=release_row)
    changed = False
    if existing is None:
        releases.append(_registry_release_row(release_row))
        changed = True
    else:
        _raise_for_release_drift(existing=existing, compiled=release_row)
    for alias in desired_aliases:
        owner = str(aliases.get(alias, "")).strip()
        if owner and owner != release_id:
            raise ValueError(f"compiled release target alias `{alias}` points to `{owner}` before commit")
        if owner != release_id:
            aliases[alias] = release_id
            changed = True

    document = {
        **dict(registry_document),
        "releases": releases,
        "aliases": aliases,
    }
    if changed:
        document["updated_utc"] = _compiled_update_date(release_row, registry_document=registry_document)
    _validate_release_state(
        repo_root=root,
        registry_document=document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )
    if changed:
        release_planning_authoring._write_registry_document(repo_root=root, document=document)  # noqa: SLF001
    state, payload = _validated_current_release_payload(repo_root=root)
    committed_release = next(
        row for row in payload["catalog"] if str(row.get("release_id", "")).strip() == release_id
    )
    return {
        **result,
        "created": existing is None,
        "dry_run": False,
        "release": committed_release,
        "registry_path": str(state.registry_path),
    }


def materialize_compiled_release_assignment(
    *,
    repo_root: Path,
    release_assignment_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Append precompiled release assignment events without recomputing membership."""

    root = Path(repo_root).resolve()
    result = dict(release_assignment_result or {})
    compiled_events = [_event_payload(row) for row in _mapping_rows(result.get("events"))]
    registry_document, event_documents, idea_specs = release_planning_authoring._load_governed_documents(  # noqa: SLF001
        repo_root=root,
    )
    existing_rendered = {
        release_planning_contract.render_assignment_event(event)
        for event in event_documents
    }
    new_events = [
        event
        for event in compiled_events
        if release_planning_contract.render_assignment_event(event) not in existing_rendered
    ]
    candidate_events = [*event_documents, *new_events]
    _validate_release_state(
        repo_root=root,
        registry_document=registry_document,
        event_documents=candidate_events,
        idea_specs=idea_specs,
    )
    if new_events:
        release_planning_authoring._append_event_documents(repo_root=root, events=new_events)  # noqa: SLF001
    state, payload = _validated_current_release_payload(repo_root=root)
    release_id = str(_mapping(result.get("release")).get("release_id", "")).strip()
    committed_release = (
        next(
            (row for row in payload["catalog"] if str(row.get("release_id", "")).strip() == release_id),
            {},
        )
        if release_id
        else {}
    )
    return {
        **result,
        "dry_run": False,
        "events": new_events,
        "replayed_event_count": len(new_events),
        "release": committed_release or result.get("release", {}),
        "event_log_path": str(state.event_log_path),
    }


def _validated_current_release_payload(*, repo_root: Path) -> tuple[Any, dict[str, Any]]:
    registry_document, event_documents, idea_specs = release_planning_authoring._load_governed_documents(  # noqa: SLF001
        repo_root=repo_root,
    )
    return _validate_release_state(
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )


def _validate_release_state(
    *,
    repo_root: Path,
    registry_document: Mapping[str, Any],
    event_documents: list[dict[str, Any]],
    idea_specs: Mapping[str, Any],
) -> tuple[Any, dict[str, Any]]:
    return release_planning_authoring._validated_state(  # noqa: SLF001
        repo_root=repo_root,
        registry_document=registry_document,
        event_documents=event_documents,
        idea_specs=idea_specs,
    )


def _registry_release_row(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        "release_id": str(row.get("release_id", "")).strip(),
        "status": str(row.get("status", "")).strip() or "planning",
        "version": str(row.get("version", "")).strip(),
        "tag": str(row.get("tag", "")).strip(),
        "name": str(row.get("name", "")).strip(),
        "notes": str(row.get("notes", "")).strip(),
        "created_utc": str(row.get("created_utc", "")).strip(),
        "shipped_utc": str(row.get("shipped_utc", "")).strip(),
        "closed_utc": str(row.get("closed_utc", "")).strip(),
    }


def _raise_for_release_drift(*, existing: Mapping[str, Any], compiled: Mapping[str, Any]) -> None:
    for field in ("status", "version", "tag", "name", "notes", "created_utc", "shipped_utc", "closed_utc"):
        expected = str(compiled.get(field, "")).strip()
        actual = str(existing.get(field, "")).strip()
        if expected and actual and expected != actual:
            release_id = str(compiled.get("release_id", "")).strip()
            raise ValueError(
                f"compiled release target `{release_id}` field `{field}` drifted before commit: "
                f"expected `{expected}`, found `{actual}`"
            )


def _desired_aliases(*, release_selector: str, release_row: Mapping[str, Any]) -> tuple[str, ...]:
    aliases = [
        release_planning_contract.canonical_alias_token(item)
        for item in (*_text_list(release_row.get("aliases")), release_selector)
    ]
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _compiled_update_date(release_row: Mapping[str, Any], *, registry_document: Mapping[str, Any]) -> str:
    return (
        str(registry_document.get("updated_utc", "")).strip()
        or str(release_row.get("created_utc", "")).strip()
        or release_planning_contract.utc_now_iso()[:10]
    )


def _event_payload(row: Mapping[str, Any]) -> dict[str, str]:
    rendered = release_planning_contract.render_assignment_event(row)
    return json.loads(rendered)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _text_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


__all__ = [
    "materialize_compiled_release_assignment",
    "materialize_compiled_release_target",
]
