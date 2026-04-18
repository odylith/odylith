"""Auto-promote planning workstreams into implementation from live execution evidence.

This module is intentionally conservative and fail-closed:
- Promotion is one-way (`planning -> implementation`) and never auto-demotes.
- Trigger requires semantic implementation evidence (`implementation|decision`) and
  at least one non-generated source-file touch in the active window.
- Generic/global coordination artifacts are excluded from promotion evidence.

The command updates canonical markdown sources in one pass:
- matching backlog idea spec metadata (`status: implementation`)
- matching row in `odylith/radar/source/INDEX.md` (`status` column)
- append promotion timeline event to Compass stream
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import log_compass_timeline_event as timeline_logger
from odylith.runtime.common import repo_path_resolver
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import workstream_inference as ws_inference


_WORKSTREAM_RE = re.compile(r"^B-\d{3,}$")
_BACKLOG_ROW_COL_COUNT = len(backlog_contract._INDEX_COLS)
_BACKLOG_STATUS_COL_INDEX = backlog_contract._INDEX_COLS.index("status")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Promote planning workstreams to implementation using live evidence.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ideas-root", default="odylith/radar/source/ideas")
    parser.add_argument("--backlog-index", default="odylith/radar/source/INDEX.md")
    parser.add_argument("--stream", default=agent_runtime_contract.AGENT_STREAM_PATH)
    parser.add_argument("--active-window-minutes", type=int, default=15)
    parser.add_argument("--author", default="sync")
    parser.add_argument("--source", default="sync")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, value: str) -> Path:
    """Resolve one promotion path token against the repo root."""

    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=value)


def _parse_ts(raw: str) -> dt.datetime | None:
    token = str(raw or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone()


def _normalize_artifacts(*, repo_root: Path, values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = ws_inference.normalize_repo_token(str(raw or "").strip(), repo_root=repo_root)
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _normalize_workstreams(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip().upper()
        if not _WORKSTREAM_RE.fullmatch(token):
            continue
        if token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _replace_metadata_value(text: str, *, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^(?P<key>{re.escape(key)}):\s*(?P<value>.*)$")
    normalized = str(value).strip()

    def _replacement(match: re.Match[str]) -> str:
        return f"{match.group('key')}: {normalized}"

    updated, count = pattern.subn(_replacement, text, count=1)
    if count == 0:
        raise ValueError(f"missing metadata key `{key}`")
    return updated


def _update_backlog_index_status(index_text: str, *, idea_id: str) -> tuple[str, bool]:
    updated_any = False
    lines = index_text.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if len(cells) < _BACKLOG_ROW_COL_COUNT:
            continue
        if cells[1] != idea_id:
            continue
        if cells[_BACKLOG_STATUS_COL_INDEX].lower() != "planning":
            continue
        cells[_BACKLOG_STATUS_COL_INDEX] = "implementation"
        lines[idx] = "| " + " | ".join(cells) + " |"
        updated_any = True

    if not updated_any:
        return index_text, False

    updated = "\n".join(lines)
    utc_today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    updated = re.sub(
        r"(?m)^Last updated \(UTC\):\s*\d{4}-\d{2}-\d{2}\s*$",
        f"Last updated (UTC): {utc_today}",
        updated,
        count=1,
    )
    if not updated.endswith("\n"):
        updated += "\n"
    return updated, True


def _load_promotion_candidates(
    *,
    repo_root: Path,
    stream_path: Path,
    ws_path_index: Mapping[str, set[str]],
    now: dt.datetime,
    active_window_minutes: int,
) -> dict[str, set[str]]:
    candidates: dict[str, set[str]] = {}
    if not stream_path.is_file():
        return candidates

    cutoff = now - dt.timedelta(minutes=max(1, active_window_minutes))
    for raw in stream_path.read_text(encoding="utf-8").splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue

        kind = str(payload.get("kind", "")).strip().lower()
        if kind not in {"implementation", "decision"}:
            continue

        ts = _parse_ts(str(payload.get("ts_iso", "")).strip())
        if ts is None or ts < cutoff:
            continue

        artifacts = _normalize_artifacts(repo_root=repo_root, values=payload.get("artifacts"))
        source_artifacts = [path for path in artifacts if not ws_inference.is_generated_or_global_path(path)]
        if not source_artifacts:
            continue

        ws_ids = _normalize_workstreams(payload.get("workstreams"))
        if not ws_ids:
            ws_ids = ws_inference.map_paths_to_workstreams(source_artifacts, ws_path_index)
        if not ws_ids:
            continue

        for ws_id in ws_ids:
            candidates.setdefault(ws_id, set()).update(source_artifacts)

    return candidates


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    ideas_root = _resolve(repo_root, str(args.ideas_root))
    backlog_index_path = _resolve(repo_root, str(args.backlog_index))
    stream_path = _resolve(repo_root, str(args.stream))

    if int(args.active_window_minutes) < 1:
        print("workstream phase auto-promotion FAILED")
        print("- active-window-minutes must be >= 1")
        return 2

    idea_specs, errors = backlog_contract._validate_idea_specs(ideas_root)
    if errors:
        print("workstream phase auto-promotion FAILED")
        for entry in errors:
            print(f"- {entry}")
        return 2

    if not backlog_index_path.is_file():
        print("workstream phase auto-promotion FAILED")
        print(f"- missing backlog index: {backlog_index_path}")
        return 2

    now = dt.datetime.now().astimezone()
    ws_path_index = ws_inference.collect_workstream_path_index_from_specs(
        repo_root=repo_root,
        idea_specs=idea_specs,
    )
    candidate_files = _load_promotion_candidates(
        repo_root=repo_root,
        stream_path=stream_path,
        ws_path_index=ws_path_index,
        now=now,
        active_window_minutes=int(args.active_window_minutes),
    )

    promoted: list[tuple[str, str, list[str]]] = []
    for idea_id, source_files in sorted(candidate_files.items()):
        spec = idea_specs.get(idea_id)
        if spec is None:
            continue
        status = str(spec.metadata.get("status", "")).strip().lower()
        if status != "planning":
            continue

        text = spec.path.read_text(encoding="utf-8")
        updated_text = _replace_metadata_value(text, key="status", value="implementation")
        if updated_text != text:
            spec.path.write_text(updated_text, encoding="utf-8")
            promoted.append(
                (
                    idea_id,
                    ws_inference.normalize_repo_token(str(spec.path), repo_root=repo_root),
                    sorted(source_files),
                )
            )

    if not promoted:
        print("workstream phase auto-promotion passed")
        print("- promoted: 0")
        return 0

    backlog_text = backlog_index_path.read_text(encoding="utf-8")
    index_updated = False
    for idea_id, _idea_file, _source_files in promoted:
        backlog_text, changed = _update_backlog_index_status(backlog_text, idea_id=idea_id)
        index_updated = index_updated or changed
    if index_updated:
        backlog_index_path.write_text(backlog_text, encoding="utf-8")

    for idea_id, idea_file, source_files in promoted:
        summary = "Phase advanced: Planning -> Implementation (Live)"
        artifacts = ["odylith/radar/source/INDEX.md", idea_file, *source_files[:6]]
        timeline_logger.append_event(
            repo_root=repo_root,
            stream_path=stream_path,
            kind="implementation",
            summary=summary,
            workstream_values=[idea_id],
            artifact_values=artifacts,
            component_values=[],
            author=str(args.author),
            source=str(args.source),
            context=f"Auto-promotion triggered by live implementation evidence for {idea_id}",
            headline_hint=f"Phase advanced for {idea_id}",
        )

    print("workstream phase auto-promotion passed")
    print(f"- promoted: {len(promoted)}")
    print(f"- backlog_index_updated: {'yes' if index_updated else 'no'}")
    for idea_id, _idea_file, source_files in promoted:
        print(f"- promoted_workstream: {idea_id} (source_files={len(source_files)})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
