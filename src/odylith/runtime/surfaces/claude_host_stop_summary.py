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
from odylith.runtime.intervention_engine import conversation_runtime
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator
from odylith.runtime.surfaces import claude_host_shared


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
    if not summary:
        return {}
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
    grounded = bool(prompt_excerpt or summary or changed_paths or workstreams or components)
    request = orchestrator.OrchestrationRequest(
        prompt=prompt_excerpt or summary,
        candidate_paths=changed_paths,
        workstreams=workstreams,
        components=components,
        needs_write=bool(changed_paths),
        evidence_cone_grounded=grounded,
        latency_sensitive=True,
        task_kind="governance_closeout",
        phase="closeout",
        session_id=session_id,
        context_signals={"host_family": "claude"},
    )
    decision = orchestrator.OrchestrationDecision(
        mode="local_only",
        decision_id=f"stop-summary-{session_id or 'claude'}",
        delegate=False,
        parallel_safety="local_only",
        task_family="governance_closeout",
        confidence=2,
        rationale="Claude stop-summary surface",
        refusal_stage="",
        manual_review_recommended=False,
        merge_owner="main_thread",
    )
    return conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=decision,
        adoption={
            "grounded": grounded,
            "route_ready": grounded,
            "grounded_delegate": False,
            "requires_widening": False,
            "narrowing_required": False,
        },
        repo_root=repo_root,
        final_changed_paths=changed_paths,
        changed_path_source="session_event_history" if changed_paths else "",
        turn_phase="stop_summary",
        assistant_summary=summary,
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
    summary = claude_host_shared.meaningful_stop_summary(
        str(payload.get("last_assistant_message", ""))
    )
    if not summary:
        return 0
    workstreams = claude_host_shared.extract_workstreams(summary)
    claude_host_shared.run_compass_log(
        project_dir=repo_root,
        summary=summary,
        workstreams=workstreams,
    )
    bundle = _stop_intervention_bundle(repo_root=repo_root, payload=payload)
    rendered = render_stop_summary(
        repo_root=repo_root,
        payload=payload,
        conversation_bundle_override=bundle,
    )
    if bundle:
        conversation_surface.append_intervention_events(
            repo_root=repo_root,
            bundle=bundle,
            include_proposal=False,
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
