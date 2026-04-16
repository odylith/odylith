"""Codex Stop hook logger for meaningful Odylith implementation summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import conversation_runtime
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator
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
    if not summary:
        return {}
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
        context_signals={"host_family": "codex"},
    )
    decision = orchestrator.OrchestrationDecision(
        mode="local_only",
        decision_id=f"stop-summary-{session_id or 'codex'}",
        delegate=False,
        parallel_safety="local_only",
        task_family="governance_closeout",
        confidence=2,
        rationale="Codex stop-summary surface",
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
        repo_root=resolved_root,
        final_changed_paths=changed_paths,
        changed_path_source="session_event_history" if changed_paths else "",
        turn_phase="stop_summary",
        assistant_summary=summary,
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
    log_codex_stop_summary(args.repo_root, message=message)
    bundle = _stop_intervention_bundle(
        repo_root=args.repo_root,
        message=message,
        session_id=session_id,
    )
    rendered = render_codex_stop_summary(
        args.repo_root,
        message=message,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    if bundle:
        conversation_surface.append_intervention_events(
            repo_root=Path(args.repo_root).expanduser().resolve(),
            bundle=bundle,
            include_proposal=False,
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
