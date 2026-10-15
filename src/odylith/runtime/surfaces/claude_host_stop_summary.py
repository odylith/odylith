"""Durably capture meaningful Claude turns without canonical hook writes.

The shared filter selects a complete meaningful sentence. Stop journals it with
its native session identity before deferred chat-delivery confirmation. Ordinary
foreground Compass updates own canonical append and publication. A journal
refusal emits a compact status without claiming the event was saved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import host_intervention_support
from odylith.runtime.surfaces import host_dirty_checkpoint


def _stop_intervention_bundle(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = claude_host_shared.meaningful_stop_summary(
        str(payload.get("last_assistant_message", ""))
    )
    session_id = claude_host_shared.hook_session_id(payload)
    prompt_excerpt = intervention_surface_runtime.recent_session_prompt_excerpt(
        repo_root=repo_root,
        session_id=session_id,
    )
    changed_paths = intervention_surface_runtime.recent_session_changed_paths(
        repo_root=repo_root,
        session_id=session_id,
    )
    workstreams = intervention_surface_runtime.recent_session_ids(
        repo_root=repo_root,
        session_id=session_id,
        field="workstreams",
    )
    components = intervention_surface_runtime.recent_session_ids(
        repo_root=repo_root,
        session_id=session_id,
        field="components",
    )
    return host_intervention_support.build_stop_conversation_bundle(
        repo_root=repo_root,
        host_family="claude",
        session_id=session_id,
        assistant_summary=summary,
        prompt_excerpt=prompt_excerpt,
        changed_paths=changed_paths,
        workstreams=workstreams,
        components=components,
        bundle_override=bundle_override,
    )


def render_stop_summary(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    conversation_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    bundle = _stop_intervention_bundle(
        repo_root=repo_root,
        payload=payload,
        bundle_override=conversation_bundle_override,
    )
    return host_intervention_support.render_stop_bundle_text(
        repo_root=repo_root,
        host_family="claude",
        bundle=bundle,
        session_id=str(payload.get("session_id", "")).strip() or claude_host_shared.hook_session_id(payload),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude stop-summary",
        description="Save meaningful Claude summaries for the next Compass update.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for durable summary capture.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude Stop payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    if bool(payload.get("stop_hook_active")):
        return 0
    session_id = claude_host_shared.hook_session_id(payload)
    message = str(payload.get("last_assistant_message", ""))
    if host_intervention_support.suppress_prompt_live_narration(assistant_summary=message):
        return 0
    summary = claude_host_shared.meaningful_stop_summary(message)
    try:
        saved = not summary or host_dirty_checkpoint.capture_stop_summary(
            repo_root=repo_root,
            host_family="claude",
            session_id=session_id,
            summary=summary,
            workstreams=claude_host_shared.extract_workstreams(summary),
        )
    except host_dirty_checkpoint.HostDirtyCheckpointError:
        saved = False
    status = "" if saved else "Odylith could not save this turn's summary."
    try:
        host_surface_runtime.confirm_assistant_chat_delivery(
            repo_root=repo_root,
            host_family="claude",
            session_id=session_id,
            last_assistant_message=message,
            render_surface="claude_stop",
            defer=True,
        )
    except host_dirty_checkpoint.HostDirtyCheckpointError:
        status = status or "Odylith could not save chat-delivery confirmation."
    if status:
        sys.stdout.write(json.dumps(host_surface_runtime.stop_payload(system_message=status)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
