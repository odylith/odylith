"""Repair known consumer runtime noise from released Odylith installs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from odylith.install.fs import atomic_write_text, display_path

_COMPASS_STREAM_RELS: tuple[Path, ...] = (
    Path("odylith/compass/runtime/agent-stream.v1.jsonl"),
    Path("odylith/compass/runtime/codex-stream.v1.jsonl"),
)
_PRODUCT_VISIBILITY_WORKSTREAM = "B-096"
_PRODUCT_VISIBILITY_BUG = "CB-122"
_STALE_VISIBILITY_PHRASES: tuple[str, ...] = (
    "show the next odylith observation",
    "odylith is ready to speak",
    "transcript confirmation",
    "consistent visible lane",
    "brand promise",
)
_SUSPECT_KINDS: tuple[str, ...] = (
    "ambient_signal",
    "assist_closeout",
    "intervention_card",
    "proposal",
)
_WORKSTREAM_RE = re.compile(r"^idea_id:\s*(?P<id>B-\d+)\s*$", re.MULTILINE)
_BUG_RE = re.compile(r"^- Bug ID:\s*(?P<id>CB-\d+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ConsumerInterventionNoiseRepair:
    """Summary of stale consumer intervention-event cleanup."""

    changed_paths: tuple[str, ...] = ()
    repaired_streams: tuple[str, ...] = ()
    removed_events: int = 0
    skipped_reason: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.changed_paths)


def repair_stale_consumer_intervention_noise(
    *,
    repo_root: Path,
    consumer_repo: bool,
) -> ConsumerInterventionNoiseRepair:
    """Remove stale 0.1.11 Claude visibility noise from consumer Compass streams."""

    root = Path(repo_root).expanduser().resolve()
    if not consumer_repo:
        return ConsumerInterventionNoiseRepair(skipped_reason="not a consumer repo")

    local_workstreams = _local_workstream_ids(root)
    local_bugs = _local_bug_ids(root)
    removed_total = 0
    repaired_streams: list[str] = []
    changed_paths: list[str] = []

    for relative in _COMPASS_STREAM_RELS:
        stream_path = root / relative
        if not stream_path.is_file():
            continue
        try:
            lines = stream_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        kept: list[str] = []
        removed = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                kept.append(line)
                continue
            if isinstance(event, dict) and _is_stale_visibility_event(
                event,
                local_workstreams=local_workstreams,
                local_bugs=local_bugs,
            ):
                removed += 1
                continue
            kept.append(line)

        if removed <= 0:
            continue
        atomic_write_text(
            stream_path,
            "\n".join(kept).rstrip() + ("\n" if kept else ""),
            encoding="utf-8",
        )
        removed_total += removed
        repaired_streams.append(display_path(repo_root=root, path=stream_path))
        changed_paths.append(display_path(repo_root=root, path=stream_path))

    if removed_total <= 0:
        return ConsumerInterventionNoiseRepair(skipped_reason="no stale intervention events found")
    return ConsumerInterventionNoiseRepair(
        changed_paths=tuple(dict.fromkeys(changed_paths)),
        repaired_streams=tuple(dict.fromkeys(repaired_streams)),
        removed_events=removed_total,
    )


def _is_stale_visibility_event(
    event: Mapping[str, Any],
    *,
    local_workstreams: set[str],
    local_bugs: set[str],
) -> bool:
    serialized = json.dumps(event, ensure_ascii=False, sort_keys=True)
    text = serialized.casefold()
    host_family = str(event.get("host_family", "")).strip().casefold()
    render_surface = str(event.get("render_surface", "")).strip().casefold()
    kind = str(event.get("kind", "")).strip().casefold()
    suspect_surface = (
        host_family == "claude"
        or render_surface.startswith("claude_")
        or kind in _SUSPECT_KINDS
    )
    if not suspect_surface:
        return False
    if any(phrase in text for phrase in _STALE_VISIBILITY_PHRASES):
        return True
    if (
        _PRODUCT_VISIBILITY_WORKSTREAM not in local_workstreams
        and _PRODUCT_VISIBILITY_WORKSTREAM.casefold() in text
    ):
        return True
    if (
        _PRODUCT_VISIBILITY_BUG not in local_bugs
        and _PRODUCT_VISIBILITY_BUG.casefold() in text
    ):
        return True
    return False


def _local_workstream_ids(repo_root: Path) -> set[str]:
    return _ids_from_markdown(root=repo_root / "odylith/radar/source", pattern=_WORKSTREAM_RE)


def _local_bug_ids(repo_root: Path) -> set[str]:
    return _ids_from_markdown(root=repo_root / "odylith/casebook/bugs", pattern=_BUG_RE)


def _ids_from_markdown(*, root: Path, pattern: re.Pattern[str]) -> set[str]:
    ids: set[str] = set()
    if not root.is_dir():
        return ids
    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        ids.update(match.group("id") for match in pattern.finditer(text))
    return ids
