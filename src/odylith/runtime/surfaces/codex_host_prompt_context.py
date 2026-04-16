"""Codex UserPromptSubmit hook renderer for explicit Odylith anchors."""

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
from odylith.runtime.surfaces import codex_host_shared


def _prompt_conversation_bundle(
    *,
    repo_root: str,
    prompt: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    observation = intervention_surface_runtime.observation_envelope(
        host_family="codex",
        turn_phase="prompt_submit",
        session_id=session_id,
        prompt_excerpt=prompt,
    )
    if isinstance(intervention_bundle_override, Mapping):
        return {"intervention_bundle": dict(intervention_bundle_override)}
    return conversation_surface.build_conversation_bundle(
        repo_root=Path(repo_root).expanduser().resolve(),
        observation=observation,
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
    bundle = _prompt_conversation_bundle(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
    parts: list[str] = []
    ref = codex_host_shared.prompt_anchor(prompt)
    if ref:
        parts.append(summary_override or codex_host_shared.context_summary(project_dir=repo_root, ref=ref))
    if live_text:
        parts.append(live_text)
    return "\n\n".join(part for part in parts if part).strip()


def render_codex_prompt_system_message(
    *,
    repo_root: str = ".",
    prompt: str,
    session_id: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    bundle = _prompt_conversation_bundle(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    return conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
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
    bundle = _prompt_conversation_bundle(
        repo_root=args.repo_root,
        prompt=prompt,
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
    if not summary and not system_message:
        return 0
    conversation_surface.append_intervention_events(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        bundle=bundle,
        include_proposal=False,
        delivery_channel="assistant_fallback_context",
        delivery_status="assistant_fallback_ready",
        render_surface="codex_user_prompt_submit",
    )
    sys.stdout.write(
        json.dumps(
            host_surface_runtime.codex_prompt_payload(
                additional_context=summary,
                system_message=system_message,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
