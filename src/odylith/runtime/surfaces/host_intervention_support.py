"""Shared helpers for host-specific prompt and stop intervention renderers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import alignment_context
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine import visibility_replay


_LIVE_BLOCK_LABELS: tuple[str, ...] = (
    "Odylith Observation:",
    "Odylith Proposal:",
    "Odylith Insight:",
    "Odylith History:",
    "Odylith Risks:",
)


def _alignment_mapping(alignment: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = alignment.get(key)
    return value if isinstance(value, Mapping) else {}


def _alignment_list(alignment: Mapping[str, Any], key: str) -> list[Any]:
    value = alignment.get(key)
    return value if isinstance(value, list) else []


def join_sections(*values: Any) -> str:
    """Join unique normalized chat sections with one blank line between them."""
    return visibility_contract.join_blocks(*values)


def looks_like_teaser_live_text(value: str) -> bool:
    """Return whether the live text is still only a teaser beat."""
    text = str(value or "").strip()
    if not text:
        return False
    if any(label in text for label in _LIVE_BLOCK_LABELS):
        return False
    return "Odylith" in text


def merge_replay_with_closeout(*, replay: str, closeout_text: str) -> str:
    """Combine replayed live blocks with a closeout without duplicating assists."""
    visible_replay = str(replay or "").strip()
    closeout = str(closeout_text or "").strip()
    if not visible_replay:
        return closeout
    if not closeout or "Odylith Assist:" in visible_replay or "**Odylith Assist:**" in visible_replay:
        return visible_replay
    return join_sections(visible_replay, closeout)


def build_prompt_conversation_bundle(
    *,
    repo_root: Path | str,
    host_family: str,
    prompt: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the prompt-submit bundle shared by Codex and Claude hooks."""
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    if isinstance(intervention_bundle_override, Mapping):
        return {"intervention_bundle": dict(intervention_bundle_override)}
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    alignment = alignment_context.build_host_alignment_context(
        repo_root=root,
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        prompt_excerpt=prompt,
    )
    observation = intervention_surface_runtime.observation_envelope(
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        prompt_excerpt=prompt,
        workstreams=_alignment_list(alignment, "workstreams"),
        components=_alignment_list(alignment, "components"),
        bugs=_alignment_list(alignment, "bugs"),
        diagrams=_alignment_list(alignment, "diagrams"),
        context_packet_summary=_alignment_mapping(alignment, "context_packet"),
        execution_engine_summary=_alignment_mapping(alignment, "execution_engine_summary"),
        memory_summary=_alignment_mapping(alignment, "memory_summary"),
        tribunal_summary=_alignment_mapping(alignment, "tribunal_summary"),
        visibility_summary=_alignment_mapping(alignment, "visibility_summary"),
        delivery_snapshot=_alignment_mapping(alignment, "delivery_snapshot"),
    )
    return conversation_surface.build_conversation_bundle(
        repo_root=root,
        observation=observation,
    )


def render_prompt_system_message(
    *,
    repo_root: Path | str,
    host_family: str,
    prompt: str,
    session_id: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    """Render the host-visible prompt-submit fallback/system-message text."""
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    bundle = build_prompt_conversation_bundle(
        repo_root=root,
        host_family=normalized_host,
        prompt=prompt,
        session_id=session_id,
        bundle_override=conversation_bundle_override,
        intervention_bundle_override=intervention_bundle_override,
    )
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=root,
        bundle=bundle,
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        include_proposal=False,
        include_closeout=False,
    )
    replay = visibility_replay.replayable_chat_markdown(
        repo_root=root,
        host_family=normalized_host,
        session_id=session_id,
        include_assist=False,
        include_teaser=False,
    )
    if replay:
        return replay
    return decision.visible_markdown or conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
