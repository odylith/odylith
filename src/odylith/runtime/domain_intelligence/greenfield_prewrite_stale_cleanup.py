"""Pre-confirm cleanup policy for previously accepted greenfield workstreams."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import datetime as dt
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.governance import backlog_authoring


def accepted_greenfield_workstream_ids(root: Path) -> tuple[str, ...]:
    """Return workstream IDs from the currently accepted greenfield project, if any."""

    path = Path(root).expanduser().resolve() / "odylith/runtime/source/accepted-project.v1.json"
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, Mapping):
        return ()
    if str(payload.get("schema_version", "")).strip() != "odylith.accepted_project.v1":
        return ()
    if str(payload.get("origin", "")).strip() != "greenfield":
        return ()
    created = payload.get("created") if isinstance(payload.get("created"), Mapping) else {}
    rows = created.get("workstreams") if isinstance(created, Mapping) else ()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return ()
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        token = str(row.get("idea_id", "")).strip().upper()
        if token and token not in ids:
            ids.append(token)
    return tuple(ids)


def mark_previous_greenfield_workstreams_stale(
    backlog_result: Mapping[str, Any],
    *,
    stale_ids: Sequence[str],
) -> dict[str, Any]:
    """Mark previously accepted workstreams stale when a rerun replaces them."""

    result = dict(backlog_result)
    previous = {str(value).strip().upper() for value in stale_ids if str(value).strip()}
    if not previous:
        return result
    created_ids = {
        str(row.get("idea_id", "")).strip().upper()
        for row in mapping_rows(result.get("created"))
        if str(row.get("idea_id", "")).strip()
    }
    stale = sorted(previous - created_ids)
    if not stale:
        return result

    raw_specs = result.get("_candidate_idea_specs")
    candidate_specs = dict(raw_specs) if isinstance(raw_specs, Mapping) else {}
    stale_paths = [
        str(getattr(candidate_specs.get(token), "path", ""))
        for token in stale
        if getattr(candidate_specs.get(token), "path", None)
    ]
    for token in stale:
        candidate_specs.pop(token, None)
    result["_candidate_idea_specs"] = candidate_specs
    result["stale_idea_ids"] = sorted(
        {
            *stale,
            *[
                str(value).strip().upper()
                for value in result.get("stale_idea_ids", [])
                if str(value).strip()
            ],
        }
    )
    result["stale_idea_files"] = sorted(
        {
            str(value).strip()
            for value in [*result.get("stale_idea_files", []), *stale_paths]
            if str(value).strip()
        }
    )
    index_text = str(result.get("backlog_index_text", "") or "")
    if index_text:
        result["backlog_index_text"] = backlog_authoring.remove_workstreams_from_backlog_index_text(
            index_text,
            stale_ids=stale,
            today=dt.datetime.now(tz=dt.UTC).date(),
        )
    return result


def remove_prewrite_stale_idea_files(*, root: Path, backlog_result: Mapping[str, Any]) -> None:
    """Apply compiled stale-workstream deletions inside the pre-confirm stage."""

    target_root = Path(root).expanduser().resolve()
    ideas_root = (target_root / "odylith/radar/source/ideas").resolve()
    raw_paths = backlog_result.get("stale_idea_files", ())
    paths = raw_paths if isinstance(raw_paths, Sequence) and not isinstance(raw_paths, str) else ()
    for raw_path in paths:
        candidate = Path(str(raw_path)).expanduser()
        if not candidate.is_absolute():
            candidate = target_root / candidate
        path = candidate.resolve()
        try:
            path.relative_to(ideas_root)
        except ValueError as exc:
            raise ValueError(f"staged stale-workstream deletion escapes Radar ideas root: {raw_path}") from exc
        if path.is_file():
            path.unlink()


def remove_stale_workstream_artifacts(*, root: Path, stale_ids: object) -> None:
    tokens = {
        str(value).strip().upper()
        for value in (stale_ids if isinstance(stale_ids, Sequence) and not isinstance(stale_ids, str) else [])
        if str(value).strip()
    }
    if not tokens:
        return
    target_root = Path(root).expanduser().resolve()
    for token in tokens:
        program_path = target_root / "odylith/radar/source/programs" / f"{token}.execution-waves.v1.json"
        if program_path.is_file():
            program_path.unlink()
    release_events = target_root / "odylith/radar/source/releases/release-assignment-events.v1.jsonl"
    if not release_events.is_file():
        return
    kept: list[str] = []
    changed = False
    for line in release_events.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if str(payload.get("workstream_id", "")).strip().upper() in tokens:
            changed = True
            continue
        kept.append(line)
    if changed:
        release_events.write_text(("\n".join(kept).rstrip() + "\n") if kept else "", encoding="utf-8")


__all__ = [
    "accepted_greenfield_workstream_ids",
    "mark_previous_greenfield_workstreams_stale",
    "remove_prewrite_stale_idea_files",
    "remove_stale_workstream_artifacts",
]
