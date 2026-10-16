"""Durably capture meaningful Codex summaries without canonical hook writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.surfaces import codex_host_shared
from odylith.runtime.surfaces import host_intervention_support
from odylith.runtime.surfaces import host_hook_execution
from odylith.runtime.surfaces import host_dirty_checkpoint


# The native hook has a 20-second outer timeout; leave launcher and owned
# process cleanup headroom instead of granting each phase a fresh timeout.
_STOP_BUDGET_SECONDS = 14.0


def _stop_intervention_bundle(
    *,
    repo_root: str,
    message: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = codex_host_shared.meaningful_stop_summary(message)
    resolved_root = Path(repo_root).expanduser().resolve()
    prompt_excerpt = intervention_surface_runtime.recent_session_prompt_excerpt(
        repo_root=resolved_root,
        session_id=session_id,
    )
    changed_paths = intervention_surface_runtime.recent_session_changed_paths(
        repo_root=resolved_root,
        session_id=session_id,
    )
    workstreams = intervention_surface_runtime.recent_session_ids(
        repo_root=resolved_root,
        session_id=session_id,
        field="workstreams",
    )
    components = intervention_surface_runtime.recent_session_ids(
        repo_root=resolved_root,
        session_id=session_id,
        field="components",
    )
    return host_intervention_support.build_stop_conversation_bundle(
        repo_root=resolved_root,
        host_family="codex",
        session_id=session_id,
        assistant_summary=summary,
        prompt_excerpt=prompt_excerpt,
        changed_paths=changed_paths,
        workstreams=workstreams,
        components=components,
        bundle_override=bundle_override,
    )


def render_codex_stop_summary(
    repo_root: str = ".",
    *,
    message: str,
    session_id: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    bundle = _stop_intervention_bundle(
        repo_root=repo_root,
        message=message,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
    )
    return host_intervention_support.render_stop_bundle_text(
        repo_root=Path(repo_root).expanduser().resolve(),
        host_family="codex",
        bundle=bundle,
        session_id=session_id,
    )


def _run_stop_summary(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex stop-summary",
        description="Save a meaningful Codex summary for the next Compass update.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for durable summary capture.")
    args = parser.parse_args(list(argv or []))
    payload = codex_host_shared.load_payload()
    if bool(payload.get("stop_hook_active")):
        return 0
    message = str(payload.get("last_assistant_message", ""))
    session_id = codex_host_shared.hook_session_id(payload)
    if host_intervention_support.suppress_prompt_live_narration(assistant_summary=message):
        return 0
    summary = codex_host_shared.meaningful_stop_summary(message)
    try:
        saved = not summary or host_dirty_checkpoint.capture_stop_summary(
            repo_root=args.repo_root,
            host_family="codex",
            session_id=session_id,
            summary=summary,
            workstreams=codex_host_shared.extract_workstreams(summary),
        )
    except host_dirty_checkpoint.HostDirtyCheckpointError:
        saved = False
    status = "" if saved else "Odylith could not save this turn's summary."
    try:
        host_surface_runtime.confirm_assistant_chat_delivery(
            repo_root=args.repo_root,
            host_family="codex",
            session_id=session_id,
            last_assistant_message=message,
            render_surface="codex_stop",
            defer=True,
        )
    except host_dirty_checkpoint.HostDirtyCheckpointError:
        status = status or "Odylith could not save chat-delivery confirmation."
    if status:
        sys.stdout.write(json.dumps(host_surface_runtime.stop_payload(system_message=status)))
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        with host_hook_execution.hook_budget(seconds=_STOP_BUDGET_SECONDS):
            return _run_stop_summary(argv)
    except host_hook_execution.HookBudgetExpired:
        sys.stdout.write(json.dumps(host_surface_runtime.stop_payload(
            system_message=(
                "Odylith Stop capture did not complete. "
                "This turn's summary may not be saved."
            ),
        )))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
