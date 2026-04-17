"""Codex Stop hook logger for meaningful Odylith implementation summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.surfaces import codex_host_shared


def _stop_intervention_bundle(
    *,
    repo_root: str,
    message: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
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
    if not any((summary, prompt_excerpt, changed_paths, workstreams, components)):
        return {}
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=resolved_root,
        host_family="codex",
        turn_phase="stop_summary",
        session_id=session_id,
        prompt_excerpt=prompt_excerpt,
        assistant_summary=summary,
        changed_paths=changed_paths,
        workstreams=workstreams,
        components=components,
    )


def log_codex_stop_summary(repo_root: str = ".", *, message: str) -> bool:
    summary = codex_host_shared.meaningful_stop_summary(message)
    if not summary:
        return False
    return codex_host_shared.run_compass_log(
        project_dir=repo_root,
        summary=summary,
        workstreams=codex_host_shared.extract_workstreams(summary),
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
    if not bundle:
        return ""
    parts: list[str] = []
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )
    recovered_live_text = intervention_surface_runtime.recent_session_live_markdown(
        repo_root=Path(repo_root).expanduser().resolve(),
        session_id=session_id,
    )
    if recovered_live_text and (not live_text or "Odylith can already" in live_text):
        live_text = recovered_live_text
    closeout_text = conversation_surface.render_closeout_text(
        bundle,
        markdown=True,
    )
    for part in (live_text, closeout_text):
        token = str(part or "").strip()
        if token and token not in parts:
            parts.append(token)
    return "\n\n".join(parts).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex stop-summary",
        description="Log a meaningful Codex stop summary to Compass when present.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for launcher resolution.")
    args = parser.parse_args(list(argv or []))
    payload = codex_host_shared.load_payload()
    if bool(payload.get("stop_hook_active")):
        return 0
    message = str(payload.get("last_assistant_message", ""))
    session_id = codex_host_shared.hook_session_id(payload)
    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=args.repo_root,
        host_family="codex",
        session_id=session_id,
        last_assistant_message=message,
        render_surface="codex_stop",
    )
    log_codex_stop_summary(args.repo_root, message=message)
    bundle = _stop_intervention_bundle(
        repo_root=args.repo_root,
        message=message,
        session_id=session_id,
    )
    decision = (
        host_surface_runtime.visible_intervention_decision(
            repo_root=args.repo_root,
            bundle=bundle,
            host_family="codex",
            turn_phase="stop_summary",
            session_id=session_id,
            include_proposal=False,
            include_closeout=True,
        )
        if bundle
        else None
    )
    rendered = (
        decision.visible_markdown
        if decision is not None
        else render_codex_stop_summary(
            args.repo_root,
            message=message,
            session_id=session_id,
            conversation_bundle_override=bundle,
        )
    )
    if bundle and decision is not None:
        host_surface_runtime.append_visible_intervention_events(
            repo_root=Path(args.repo_root).expanduser().resolve(),
            bundle=bundle,
            decision=decision,
            render_surface="codex_stop",
        )
    if rendered:
        sys.stdout.write(
            json.dumps(
                host_surface_runtime.stop_payload(
                    system_message=rendered,
                    block_for_visible_delivery=not host_surface_runtime.visible_delivery_already_present(
                        last_assistant_message=message,
                        visible_text=rendered,
                    ),
                )
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
