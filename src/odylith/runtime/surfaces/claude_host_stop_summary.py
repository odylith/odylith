"""Claude Code Stop hook: meaningful stop-summary Compass log.

When a Claude Code turn ends, the ``Stop`` hook fires with the
assistant's last message. This baked module mirrors the legacy
``.claude/hooks/log-stop-summary.py`` script. It filters out trivial,
question-shaped, or offer-shaped stop messages and only logs a Compass
``implementation`` event when the message looks like a real action
summary (action verb present, length above the noise floor, no
``Would you like ...`` opening).

The hook never blocks the turn-ending event. All failures degrade to
a no-op return so a missing launcher, missing snapshot, or unparseable
payload never breaks Claude Code's stop dispatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.intervention_engine import visibility_replay
from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import host_intervention_support


def _stop_intervention_bundle(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
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
    if not any((summary, prompt_excerpt, changed_paths, workstreams, components)):
        return {}
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=repo_root,
        host_family="claude",
        turn_phase="stop_summary",
        session_id=session_id,
        prompt_excerpt=prompt_excerpt,
        assistant_summary=summary,
        changed_paths=changed_paths,
        workstreams=workstreams,
        components=components,
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
    if not bundle:
        return ""
    parts: list[str] = []
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )
    recovered_live_text = visibility_replay.replayable_chat_markdown(
        repo_root=repo_root,
        host_family="claude",
        session_id=str(payload.get("session_id", "")).strip() or claude_host_shared.hook_session_id(payload),
        max_live_blocks=4,
        ambient_cap=3,
        include_assist=False,
        include_teaser=True,
    )
    if recovered_live_text and (
        not live_text or host_intervention_support.looks_like_teaser_live_text(live_text)
    ):
        live_text = recovered_live_text
    closeout_text = conversation_surface.render_closeout_text(
        bundle,
        markdown=True,
    )
    for part in (live_text, closeout_text):
        token = str(part or "").strip()
        if token and token not in parts:
            parts.append(token)
    return host_intervention_support.join_sections(*parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude stop-summary",
        description="Log meaningful Claude stop summaries to Compass.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Compass log dispatch.")
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
    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=repo_root,
        host_family="claude",
        session_id=session_id,
        last_assistant_message=str(payload.get("last_assistant_message", "")),
        render_surface="claude_stop",
    )
    summary = claude_host_shared.meaningful_stop_summary(
        str(payload.get("last_assistant_message", ""))
    )
    workstreams = claude_host_shared.extract_workstreams(summary)
    if summary:
        claude_host_shared.run_compass_log(
            project_dir=repo_root,
            summary=summary,
            workstreams=workstreams,
        )
    bundle = _stop_intervention_bundle(repo_root=repo_root, payload=payload)
    decision = (
        host_surface_runtime.visible_intervention_decision(
            repo_root=repo_root,
            bundle=bundle,
            host_family="claude",
            turn_phase="stop_summary",
            session_id=session_id,
            include_proposal=False,
            include_closeout=True,
        )
        if bundle
        else None
    )
    replay = visibility_replay.replayable_chat_markdown(
        repo_root=repo_root,
        host_family="claude",
        session_id=session_id,
        max_live_blocks=4,
        ambient_cap=3,
        include_assist=True,
        include_teaser=False,
    )
    closeout_text = (
        conversation_surface.render_closeout_text(bundle, markdown=True)
        if bundle
        else ""
    )
    rendered = (
        host_intervention_support.merge_replay_with_closeout(replay=replay, closeout_text=closeout_text)
        if replay
        else decision.visible_markdown
        if decision is not None
        else render_stop_summary(
            repo_root=repo_root,
            payload=payload,
            conversation_bundle_override=bundle,
        )
    )
    if bundle and decision is not None:
        host_surface_runtime.append_visible_intervention_events(
            repo_root=repo_root,
            bundle=bundle,
            decision=decision,
            render_surface="claude_stop",
        )
    if rendered:
        sys.stdout.write(
            json.dumps(
                host_surface_runtime.stop_payload(
                    system_message=rendered,
                    block_for_visible_delivery=not host_surface_runtime.visible_delivery_already_present(
                        last_assistant_message=str(payload.get("last_assistant_message", "")),
                        visible_text=rendered,
                    ),
                )
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
