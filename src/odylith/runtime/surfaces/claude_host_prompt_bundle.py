"""Claude Code UserPromptSubmit bundle for Odylith prompt-time context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from odylith.runtime.intervention_engine import prompt_signal_runtime
from odylith.runtime.surfaces import claude_host_prompt_context
from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import host_intervention_support
from odylith.runtime.surfaces import host_prompt_route_locks


def _cheap_bundle_payload(*, additional_context: str = "", system_message: str = "") -> dict[str, object]:
    """Return Claude prompt-bundle JSON without importing the renderer stack."""

    payload: dict[str, object] = {}
    context = str(additional_context or "").strip()
    message = str(system_message or "").strip()
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    if message:
        payload["systemMessage"] = message
    return payload


def render_prompt_bundle_payload(
    *,
    repo_root: Path | str = ".",
    prompt: str,
    session_id: str = "",
    suppress_prompt_first_receipt: bool = False,
) -> dict[str, object]:
    """Render Claude's single prompt-submit payload, if the prompt earns one."""

    route_context = host_prompt_route_locks.route_lock_context(host_family="claude", prompt=prompt)
    if route_context:
        return _cheap_bundle_payload(additional_context=route_context)

    if host_intervention_support.suppress_prompt_live_narration(prompt=prompt):
        return {}
    refs = list(dict.fromkeys(prompt_signal_runtime.ANCHOR_RE.findall(str(prompt or ""))))
    if not refs and not host_intervention_support.prompt_needs_live_bundle(prompt=prompt):
        if suppress_prompt_first_receipt or not host_intervention_support.prompt_first_receipt_eligible(prompt):
            return {}
        receipt = host_intervention_support.prompt_first_receipt_context(
            prompt=prompt,
            repo_root=repo_root,
            host_family="claude",
            session_id=session_id,
        )
        return _cheap_bundle_payload(additional_context=receipt) if receipt else {}

    from odylith.runtime.intervention_engine import host_surface_runtime

    repo_path = Path(repo_root).expanduser().resolve()
    bundle = claude_host_prompt_context._prompt_conversation_bundle(  # noqa: SLF001
        repo_root=repo_path,
        prompt=prompt,
        session_id=session_id,
    )
    bundle = host_intervention_support.ensure_prompt_visible_assist_bundle(bundle)
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=repo_path,
        bundle=bundle,
        host_family="claude",
        turn_phase="prompt_submit",
        session_id=session_id,
        include_proposal=False,
        include_closeout=True,
        developer_include_closeout=True,
        delivery_channel="system_message_and_additional_context",
        delivery_status="assistant_render_required",
    )
    replay = host_intervention_support.preferred_live_replay_markdown(
        repo_root=repo_path,
        host_family="claude",
        session_id=session_id,
    )
    summary = claude_host_prompt_context.render_prompt_context(
        repo_root=repo_path,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    system_message = claude_host_prompt_context.render_prompt_system_message(
        repo_root=repo_path,
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
    if decision.visible_markdown or decision.developer_context:
        host_surface_runtime.append_visible_intervention_events(
            repo_root=repo_path,
            bundle=bundle,
            decision=decision,
            render_surface="claude_user_prompt_submit",
        )
    return host_surface_runtime.claude_prompt_bundle_payload(
        additional_context=summary,
        system_message=system_message,
        include_assist_in_visible_fallback=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude prompt-bundle",
        description="Render bundled Odylith Claude UserPromptSubmit context and teaser output.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith context resolution.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude UserPromptSubmit payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    prompt = str(payload.get("prompt", "")).strip()
    session_id = claude_host_shared.hook_session_id(payload)
    if not host_prompt_route_locks.route_lock_context(host_family="claude", prompt=prompt):
        confirmed_events = host_intervention_support.confirm_last_assistant_message(
            repo_root=repo_root,
            host_family="claude",
            session_id=session_id,
            payload=payload,
            render_surface="claude_user_prompt_submit",
        )
    else:
        confirmed_events = []
    payload_out = render_prompt_bundle_payload(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        suppress_prompt_first_receipt=bool(confirmed_events),
    )
    if payload_out:
        sys.stdout.write(json.dumps(payload_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
