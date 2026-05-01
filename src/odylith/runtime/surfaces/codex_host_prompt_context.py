"""Codex UserPromptSubmit hook renderer for explicit Odylith anchors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import prompt_signal_runtime
from odylith.runtime.surfaces import codex_host_shared
from odylith.runtime.surfaces import host_intervention_support
from odylith.runtime.surfaces import host_prompt_route_locks


def _prompt_conversation_bundle(
    *,
    repo_root: str,
    prompt: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return host_intervention_support.build_prompt_conversation_bundle(
        repo_root=repo_root,
        host_family="codex",
        prompt=prompt,
        session_id=session_id,
        bundle_override=bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )


def render_codex_prompt_context(
    repo_root: str = ".",
    *,
    prompt: str,
    session_id: str = "",
    summary_override: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    if host_intervention_support.suppress_prompt_live_narration(prompt=prompt):
        return ""
    ref = prompt_signal_runtime.prompt_anchor(prompt)
    needs_live_bundle = bool(ref) or host_intervention_support.prompt_needs_live_bundle(
        prompt=prompt,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    if not needs_live_bundle:
        return ""
    bundle = _prompt_conversation_bundle(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    anchor_summary = ""
    if ref:
        anchor_summary = summary_override or codex_host_shared.context_summary(project_dir=repo_root, ref=ref)
    return host_intervention_support.render_prompt_bundle_text(
        bundle=bundle,
        anchor_summary=anchor_summary,
        markdown=False,
    )


def render_codex_prompt_system_message(
    *,
    repo_root: str = ".",
    prompt: str,
    session_id: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    return host_intervention_support.render_prompt_system_message(
        repo_root=repo_root,
        host_family="codex",
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex prompt-context",
        description="Render the Odylith-grounded UserPromptSubmit hook output for Codex.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for context resolution.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    payload = codex_host_shared.load_payload()
    prompt = str(payload.get("prompt", "")).strip()
    session_id = codex_host_shared.hook_session_id(payload)
    route_context = host_prompt_route_locks.route_lock_context(host_family="codex", prompt=prompt)
    if route_context:
        sys.stdout.write(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": route_context,
                    }
                }
            )
        )
        return 0
    host_intervention_support.confirm_last_assistant_message(
        repo_root=args.repo_root,
        host_family="codex",
        session_id=session_id,
        payload=payload,
        render_surface="codex_user_prompt_submit",
    )
    if host_intervention_support.suppress_prompt_live_narration(prompt=prompt):
        return 0
    ref = prompt_signal_runtime.prompt_anchor(prompt)
    if not ref and not host_intervention_support.prompt_needs_live_bundle(prompt=prompt):
        return 0
    bundle = _prompt_conversation_bundle(
        repo_root=args.repo_root,
        prompt=prompt,
        session_id=session_id,
    )
    from odylith.runtime.intervention_engine import host_surface_runtime

    bundle = host_intervention_support.ensure_prompt_visible_assist_bundle(bundle)
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=args.repo_root,
        bundle=bundle,
        host_family="codex",
        turn_phase="prompt_submit",
        session_id=session_id,
        include_proposal=False,
        include_closeout=True,
        developer_include_closeout=True,
    )
    replay = host_intervention_support.preferred_live_replay_markdown(
        repo_root=args.repo_root,
        host_family="codex",
        session_id=session_id,
    )
    summary = render_codex_prompt_context(
        args.repo_root,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    system_message = render_codex_prompt_system_message(
        repo_root=args.repo_root,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    summary = (
        host_intervention_support.join_sections(replay, summary)
        if replay
        else host_intervention_support.join_sections(summary, decision.developer_context)
    )
    system_message = replay or decision.visible_markdown or system_message
    if not summary and not system_message:
        return 0
    host_surface_runtime.append_visible_intervention_events(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        bundle=bundle,
        decision=decision,
        render_surface="codex_user_prompt_submit",
    )
    sys.stdout.write(
        json.dumps(
            host_surface_runtime.codex_prompt_payload(
                additional_context=summary,
                system_message=system_message,
                include_assist_in_visible_fallback=False,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
