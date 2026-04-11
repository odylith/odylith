"""Claude Code PreCompact snapshot writer for the active Odylith slice.

Claude Code fires a ``PreCompact`` hook just before it compacts an active
conversation. This module captures the active Odylith slice - workstream,
brief headline, freshness, and recent execution focus - into the Claude
project auto-memory directory so the compacted context still carries the
grounded anchor on the next turn.

The writer is invoked through ``odylith claude pre-compact-snapshot`` from
the ``PreCompact`` hook entry in ``.claude/settings.json``. It must never
raise into the caller: any failure degrades to a logged no-op so Claude
Code's compaction still proceeds.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.surfaces import claude_host_shared


PRECOMPACT_SNAPSHOT_FILENAME = "odylith-precompact-snapshot.md"
_SNAPSHOT_HEADER = "# Odylith PreCompact Snapshot"
_SNAPSHOT_NOTE = (
    "This note is written by the Odylith PreCompact hook just before Claude Code "
    "compacts the current conversation. Treat it as a grounding anchor, not as "
    "source-of-truth governance."
)


def _iterate_active_workstreams(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    focus = payload.get("execution_focus")
    if not isinstance(focus, Mapping):
        return []
    scope = focus.get("global")
    if not isinstance(scope, Mapping):
        return []
    workstreams = scope.get("workstreams")
    if not isinstance(workstreams, list):
        return []
    collected: list[str] = []
    for token in workstreams:
        value = str(token or "").strip().upper()
        if value and value not in collected:
            collected.append(value)
        if len(collected) >= 6:
            break
    return collected


def _iterate_next_actions(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    actions = payload.get("next_actions")
    if not isinstance(actions, list):
        return []
    lines: list[str] = []
    for entry in actions[:4]:
        if not isinstance(entry, Mapping):
            continue
        idea_id = str(entry.get("idea_id") or "").strip().upper()
        action = claude_host_shared.collapse_whitespace(entry.get("action") or "")
        if not action:
            continue
        lines.append(f"- {idea_id}: {action}" if idea_id else f"- {action}")
    return lines


def build_precompact_snapshot(
    *,
    repo_root: Path | str = ".",
    payload_override: Mapping[str, Any] | None = None,
) -> str:
    """Render the PreCompact snapshot markdown for the current Odylith slice."""
    payload = payload_override if payload_override is not None else claude_host_shared.load_compass_runtime(repo_root)
    lines: list[str] = [_SNAPSHOT_HEADER, "", _SNAPSHOT_NOTE, ""]
    lines.append(f"- Snapshot captured: {claude_host_shared.utc_now_iso()}")
    generated = ""
    if isinstance(payload, Mapping):
        generated = claude_host_shared.collapse_whitespace(
            payload.get("generated_utc") or payload.get("now_local_iso") or ""
        )
    if generated:
        lines.append(f"- Compass runtime generated: {generated}")
    lines.append(f"- Brief freshness: {claude_host_shared.freshness_label(payload)}")
    lines.append(f"- Host family at capture: {claude_host_shared.detect_host_family()}")
    headline = claude_host_shared.active_workstream_headline(payload)
    lines.append("")
    lines.append("## Live Focus")
    if headline:
        lines.append(f"- Headline: {headline}")
    else:
        lines.append("- Headline: (not present in Compass runtime snapshot)")
    active = _iterate_active_workstreams(payload)
    if active:
        lines.append("- Active workstreams:")
        for workstream in active:
            lines.append(f"  - {workstream}")
    else:
        lines.append("- Active workstreams: (not present in Compass runtime snapshot)")
    next_lines = _iterate_next_actions(payload)
    if next_lines:
        lines.append("")
        lines.append("## Next Actions")
        lines.extend(next_lines)
    lines.append("")
    lines.append("## Restart Hint")
    lines.append(
        "- On the next turn, resume from the active workstream above. Re-run "
        "`./.odylith/bin/odylith start --repo-root .` if the Compass runtime "
        "snapshot is older than one hour."
    )
    return "\n".join(lines).rstrip() + "\n"


def write_claude_host_precompact_snapshot(
    *,
    repo_root: Path | str = ".",
    memory_dir_override: Path | None = None,
    payload_override: Mapping[str, Any] | None = None,
) -> Path | None:
    """Write the PreCompact snapshot into the Claude project auto-memory directory.

    Returns the written path on success or ``None`` if any failure prevents
    the write. The caller must never treat a ``None`` result as a fatal
    error: Claude Code's PreCompact hook is best-effort, and Claude's
    compaction must still proceed on failure.
    """
    try:
        root = claude_host_shared.resolve_repo_root(repo_root)
        memory_dir = memory_dir_override if memory_dir_override is not None else claude_host_shared.project_memory_dir(root)
        memory_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = memory_dir / PRECOMPACT_SNAPSHOT_FILENAME
        body = build_precompact_snapshot(repo_root=root, payload_override=payload_override)
        snapshot_path.write_text(body, encoding="utf-8")
        return snapshot_path
    except OSError:
        return None
    except Exception:  # pragma: no cover - defensive safety net
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude pre-compact-snapshot",
        description="Write the active Odylith slice into Claude's project auto-memory directory before compaction.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass runtime resolution.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the 'snapshot written at ...' confirmation line on success.",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    written = write_claude_host_precompact_snapshot(repo_root=args.repo_root)
    if written is None:
        return 0
    if not args.quiet:
        sys.stdout.write(f"Odylith PreCompact snapshot written: {written}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
