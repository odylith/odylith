"""Shared helpers for host-specific prompt and stop intervention renderers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import alignment_context
from odylith.runtime.intervention_engine import conversation_closeout
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import fact_producer_runtime
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
_PROMPT_VISIBLE_ASSIST_MARKDOWN = (
    "**Odylith Assist:** surfaced this visibility issue in normal chat where you can inspect it."
)
_PROMPT_VISIBLE_ASSIST_PLAIN = (
    "Odylith Assist: surfaced this visibility issue in normal chat where you can inspect it."
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


def contains_assist(value: object) -> bool:
    """Return whether a rendered chat block already carries an Odylith Assist line."""

    return "odylith assist:" in str(value or "").casefold()


def suppress_prompt_live_narration(*, prompt: Any = "", assistant_summary: Any = "") -> bool:
    """Return whether a first-match stdout route should stay narration-free."""
    return fact_producer_runtime.is_passthrough_prompt(prompt) or fact_producer_runtime.is_cli_help_output(
        assistant_summary
    )


def preferred_live_replay_markdown(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    include_assist: bool = False,
) -> str:
    """Return the current pending live replay bundle for prompt and checkpoint recovery."""
    return visibility_replay.preferred_replayable_chat_markdown(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        include_assist=include_assist,
        include_teaser=False,
    )


def confirm_last_assistant_message(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    payload: Mapping[str, Any] | None,
    render_surface: str,
) -> list[dict[str, Any]]:
    """Promote the previous assistant turn to chat-confirmed when the payload carries it."""
    if not isinstance(payload, Mapping):
        return []
    message = str(payload.get("last_assistant_message", "")).strip()
    if not message:
        return []
    return host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message=message,
        render_surface=render_surface,
    )


def looks_like_teaser_live_text(value: str) -> bool:
    """Return whether the live text is still only a teaser beat."""
    text = str(value or "").strip()
    if not text:
        return False
    body = visibility_contract.strip_live_boundary(text)
    if body.startswith("Odylith Observation:") and "**Odylith Observation:**" not in body:
        return True
    if any(label in body for label in _LIVE_BLOCK_LABELS):
        return False
    return "Odylith" in body


def merge_replay_with_closeout(
    *,
    replay: str,
    closeout_text: str,
    supplemental_inside_live_with_assist: bool = False,
) -> str:
    """Combine replayed live blocks with a closeout without duplicating assists."""
    visible_replay = str(replay or "").strip()
    closeout = str(closeout_text or "").strip()
    if not visible_replay:
        return visibility_contract.compose_visible_markdown(closeout)
    if not closeout or "Odylith Assist:" in visible_replay or "**Odylith Assist:**" in visible_replay:
        return visibility_contract.compose_visible_markdown(visible_replay)
    return visibility_contract.compose_visible_markdown(
        visible_replay,
        closeout,
        supplemental_inside_live_with_assist=supplemental_inside_live_with_assist,
    )


def prompt_visible_assist_text(bundle: Mapping[str, Any] | object) -> tuple[str, str]:
    """Return the prompt-submit Assist text, preferring a bundle-owned closeout."""

    existing_markdown = conversation_surface.render_closeout_text(bundle, markdown=True)
    existing_plain = conversation_surface.render_closeout_text(bundle, markdown=False)
    return (
        existing_markdown or _PROMPT_VISIBLE_ASSIST_MARKDOWN,
        existing_plain or _PROMPT_VISIBLE_ASSIST_PLAIN,
    )


def prompt_visibility_feedback_requested(bundle: Mapping[str, Any] | object) -> bool:
    """Return whether the prompt explicitly reports missing Odylith visibility."""

    observation = _alignment_mapping(bundle, "observation") if isinstance(bundle, Mapping) else {}
    return conversation_closeout.visibility_feedback_requested(
        prompt=observation.get("prompt_excerpt"),
        assistant_summary=observation.get("assistant_summary", ""),
    )


def ensure_prompt_visible_assist_bundle(bundle: Mapping[str, Any] | object) -> dict[str, Any]:
    """Ensure prompt-submit rendering can close with one Assist line.

    Prompt hooks may be the only user-visible Odylith lane in a host session.
    This keeps the default Assist text owned by the shared host prompt support
    layer instead of duplicating it across Codex, Claude, and the manual
    visible-intervention recovery.
    """

    updated = dict(bundle) if isinstance(bundle, Mapping) else {}
    if conversation_surface.render_closeout_text(updated, markdown=True):
        return updated
    markdown_text, plain_text = prompt_visible_assist_text(updated)
    style = (
        "prompt_visible_feedback"
        if prompt_visibility_feedback_requested(updated)
        else "prompt_visible_fallback"
    )
    updated["closeout_bundle"] = {
        "eligible": True,
        "style": style,
        "label": "Odylith Assist:",
        "preferred_markdown_label": "**Odylith Assist:**",
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "proof": markdown_text.removeprefix("**Odylith Assist:** ").rstrip("."),
    }
    return updated


def compose_prompt_visible_markdown(*, visible_markdown: str, bundle: Mapping[str, Any] | object) -> str:
    """Append prompt-submit Assist to visible Markdown, or return Assist alone."""

    visible = visibility_contract.normalize_block_string(visible_markdown)
    if contains_assist(visible):
        return visibility_contract.compose_visible_markdown(visible)
    assisted_bundle = ensure_prompt_visible_assist_bundle(bundle)
    assist_markdown, _assist_plain = prompt_visible_assist_text(assisted_bundle)
    return visibility_contract.compose_visible_markdown(visible, assist_markdown)


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
    if suppress_prompt_live_narration(prompt=prompt):
        return {}
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
        alignment_proof=_alignment_mapping(alignment, "alignment_proof"),
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
    if suppress_prompt_live_narration(prompt=prompt):
        return ""
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    bundle = ensure_prompt_visible_assist_bundle(
        build_prompt_conversation_bundle(
            repo_root=root,
            host_family=normalized_host,
            prompt=prompt,
            session_id=session_id,
            bundle_override=conversation_bundle_override,
            intervention_bundle_override=intervention_bundle_override,
        )
    )
    include_closeout = True
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=root,
        bundle=bundle,
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        include_proposal=False,
        include_closeout=include_closeout,
        developer_include_closeout=include_closeout,
    )
    replay = preferred_live_replay_markdown(
        repo_root=root,
        host_family=normalized_host,
        session_id=session_id,
        include_assist=True,
    )
    if replay:
        closeout_text = conversation_surface.render_closeout_text(bundle, markdown=True)
        return merge_replay_with_closeout(
            replay=replay,
            closeout_text=closeout_text,
            supplemental_inside_live_with_assist=True,
        )
    visible = decision.visible_markdown or conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
    return compose_prompt_visible_markdown(visible_markdown=visible, bundle=bundle)


def render_prompt_bundle_text(
    *,
    bundle: Mapping[str, Any] | dict[str, Any],
    anchor_summary: str = "",
    markdown: bool = False,
) -> str:
    """Render prompt-context text from an anchor summary plus live conversation state."""
    observation = bundle.get("observation") if isinstance(bundle, Mapping) else {}
    if isinstance(observation, Mapping) and suppress_prompt_live_narration(
        prompt=observation.get("prompt_excerpt")
    ):
        return visibility_contract.normalize_string(anchor_summary)
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=markdown,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
    return join_sections(anchor_summary, live_text)


def build_stop_conversation_bundle(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    assistant_summary: str,
    prompt_excerpt: str,
    changed_paths: list[str],
    workstreams: list[str],
    components: list[str],
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stop-summary bundle shared by Codex and Claude hooks."""
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    if suppress_prompt_live_narration(prompt=prompt_excerpt, assistant_summary=assistant_summary) and not any(
        (changed_paths, workstreams, components)
    ):
        return {}
    if not any((assistant_summary, prompt_excerpt, changed_paths, workstreams, components)):
        return {}
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=root,
        host_family=normalized_host,
        turn_phase="stop_summary",
        session_id=session_id,
        prompt_excerpt=prompt_excerpt,
        assistant_summary=assistant_summary,
        changed_paths=changed_paths,
        workstreams=workstreams,
        components=components,
    )


def render_stop_bundle_text(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    bundle: Mapping[str, Any] | dict[str, Any],
) -> str:
    """Render stop-summary text from a normalized host conversation bundle."""
    if not bundle:
        return ""
    observation = bundle.get("observation") if isinstance(bundle, Mapping) else {}
    if isinstance(observation, Mapping) and suppress_prompt_live_narration(
        prompt=observation.get("prompt_excerpt"),
        assistant_summary=observation.get("assistant_summary"),
    ):
        return ""
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )
    recovered_live_text = visibility_replay.replayable_chat_markdown(
        repo_root=root,
        host_family=normalized_host,
        session_id=session_id,
        max_live_blocks=4,
        ambient_cap=3,
        include_assist=True,
        include_teaser=True,
    )
    if recovered_live_text and (
        not live_text or looks_like_teaser_live_text(live_text)
    ):
        live_text = recovered_live_text
    closeout_text = conversation_surface.render_closeout_text(
        bundle,
        markdown=True,
    )
    return merge_replay_with_closeout(replay=live_text, closeout_text=closeout_text)
