from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.intervention_engine import conversation_runtime
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_block_string(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    rows: list[str] = []
    blank_run = 0
    for raw_line in text.split("\n"):
        line = str(raw_line).rstrip()
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            rows.append("")
            continue
        blank_run = 0
        rows.append(line)
    return "\n".join(rows).strip()


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = _normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def normalized_session_id(value: Any, *, host_family: str = "") -> str:
    token = _normalize_string(value)
    if token:
        return token
    default = agent_runtime_contract.default_host_session_id()
    if default:
        return default
    family = _normalize_string(host_family).lower() or "host"
    return agent_runtime_contract.fallback_session_token(f"{family}-session")


def compose_host_conversation_bundle(
    *,
    repo_root: Path | str,
    host_family: str,
    turn_phase: str,
    session_id: str = "",
    prompt_excerpt: str = "",
    assistant_summary: str = "",
    changed_paths: Sequence[str] = (),
    workstreams: Sequence[str] = (),
    components: Sequence[str] = (),
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    resolved_root = Path(repo_root).expanduser().resolve()
    normalized_host = _normalize_string(host_family).lower()
    normalized_turn_phase = _normalize_string(turn_phase).lower()
    normalized_session = normalized_session_id(session_id, host_family=normalized_host)
    resolved_prompt = _normalize_string(prompt_excerpt) or intervention_surface_runtime.recent_session_prompt_excerpt(
        repo_root=resolved_root,
        session_id=normalized_session,
    )
    resolved_changed_paths = _normalize_string_list(changed_paths) or intervention_surface_runtime.recent_session_changed_paths(
        repo_root=resolved_root,
        session_id=normalized_session,
    )
    resolved_workstreams = _normalize_string_list(workstreams) or intervention_surface_runtime.recent_session_ids(
        repo_root=resolved_root,
        session_id=normalized_session,
        field="workstreams",
    )
    resolved_components = _normalize_string_list(components) or intervention_surface_runtime.recent_session_ids(
        repo_root=resolved_root,
        session_id=normalized_session,
        field="components",
    )
    summary = _normalize_string(assistant_summary)
    grounded = bool(summary or resolved_prompt or resolved_changed_paths or resolved_workstreams or resolved_components)
    request = orchestrator.OrchestrationRequest(
        prompt=resolved_prompt or summary,
        candidate_paths=resolved_changed_paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
        needs_write=bool(resolved_changed_paths),
        evidence_cone_grounded=grounded,
        latency_sensitive=True,
        task_kind="governance_closeout" if normalized_turn_phase == "stop_summary" else "implementation",
        phase="closeout" if normalized_turn_phase == "stop_summary" else "implementation",
        session_id=normalized_session,
        context_signals={"host_family": normalized_host},
    )
    decision = orchestrator.OrchestrationDecision(
        mode="local_only",
        decision_id=f"{normalized_turn_phase or 'surface'}-{normalized_session or normalized_host or 'host'}",
        delegate=False,
        parallel_safety="local_only",
        task_family="governance_closeout" if normalized_turn_phase == "stop_summary" else "bounded_bugfix",
        confidence=2,
        rationale=f"{normalized_host or 'host'} {normalized_turn_phase or 'surface'} surface",
        refusal_stage="",
        manual_review_recommended=False,
        merge_owner="main_thread",
    )
    bundle = conversation_runtime.compose_conversation_bundle(
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
        final_changed_paths=resolved_changed_paths,
        changed_path_source="supplied_changed_paths" if resolved_changed_paths else "",
        turn_phase=normalized_turn_phase,
        assistant_summary=summary,
    )
    if not isinstance(bundle.get("observation"), Mapping):
        bundle["observation"] = intervention_surface_runtime.observation_envelope(
            host_family=normalized_host,
            turn_phase=normalized_turn_phase,
            session_id=normalized_session,
            prompt_excerpt=resolved_prompt,
            assistant_summary=summary,
            changed_paths=resolved_changed_paths,
            workstreams=resolved_workstreams,
            components=resolved_components,
        )
    return bundle


def render_developer_context(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
    include_closeout: bool,
) -> str:
    if not isinstance(bundle, Mapping):
        return ""
    parts: list[str] = []
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=markdown,
        include_proposal=include_proposal,
    )
    closeout_text = (
        conversation_surface.render_closeout_text(bundle, markdown=markdown)
        if include_closeout
        else ""
    )
    for part in (live_text, closeout_text):
        token = _normalize_block_string(part)
        if token and token not in parts:
            parts.append(token)
    return "\n\n".join(parts).strip()


def render_visible_live_intervention(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
) -> str:
    if not isinstance(bundle, Mapping):
        return ""
    return _normalize_block_string(
        conversation_surface.render_live_text(
            bundle,
            markdown=markdown,
            include_proposal=include_proposal,
        )
    )


def compose_checkpoint_system_message(
    *,
    live_intervention: str = "",
    governance_status: str = "",
) -> str:
    live = _normalize_block_string(live_intervention)
    governance = _normalize_block_string(governance_status)
    if live:
        if governance and any(token in governance.lower() for token in ("failed", "skipped")):
            return f"{live}\n\n{governance}".strip()
        return live
    return governance


def codex_post_tool_payload(
    *,
    developer_context: str = "",
    system_message: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    context = _normalize_block_string(developer_context)
    message = _normalize_block_string(system_message)
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    if message:
        payload["systemMessage"] = message
    return payload


def stop_payload(*, system_message: str = "") -> dict[str, Any]:
    message = _normalize_block_string(system_message)
    return {"systemMessage": message} if message else {}


def claude_post_tool_payload(
    *,
    developer_context: str = "",
    system_message: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    context = _normalize_block_string(developer_context)
    message = _normalize_block_string(system_message)
    if context:
        payload["additionalContext"] = context
    if message:
        payload["systemMessage"] = message
    return payload
