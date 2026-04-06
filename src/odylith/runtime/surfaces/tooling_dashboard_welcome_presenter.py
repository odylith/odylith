"""Welcome-state rendering for the tooling dashboard shell."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.surfaces import tooling_dashboard_release_presenter


def _coerce_welcome_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("welcome_state", {})) if isinstance(payload.get("welcome_state"), Mapping) else {}


def _welcome_lines(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _render_welcome_steps(title: str, items: Sequence[str]) -> str:
    if not items:
        return ""
    return (
        '<section class="welcome-card welcome-card-steps">'
        f'<p class="welcome-card-kicker">{html.escape(title)}</p>'
        '<ol class="welcome-step-list">'
        + "".join(
            '<li class="welcome-step">'
            f'<span class="welcome-step-index">{index}</span>'
            f'<span class="welcome-step-copy">{html.escape(item)}</span>'
            "</li>"
            for index, item in enumerate(items, start=1)
        )
        + "</ol>"
        "</section>"
    )


def _render_welcome_action_card(
    *,
    title: str,
    reason: str,
    path_hint: str,
    preview_note: str,
    cta_label: str,
    tab: str,
) -> str:
    return (
        '<section class="welcome-card welcome-card-action">'
        '<div class="welcome-card-copy">'
        f'<p class="welcome-card-kicker">{html.escape(title)}</p>'
        f'<p class="welcome-card-body">{html.escape(reason)}</p>'
        f'<p class="welcome-card-path"><code>{html.escape(path_hint)}</code></p>'
        "</div>"
        '<button type="button" class="welcome-button welcome-button-secondary" '
        f'data-welcome-tab="{html.escape(tab, quote=True)}">{html.escape(cta_label)}</button>'
        "</section>"
    )


def _render_welcome_notice(notice: Mapping[str, Any]) -> str:
    title = str(notice.get("title", "")).strip()
    body = str(notice.get("body", "")).strip()
    code = str(notice.get("code", "")).strip()
    copy_label = str(notice.get("copy_label", "")).strip()
    copy_status = str(notice.get("copy_status", "")).strip()
    copy_text = str(notice.get("copy_text", "")).strip()
    tone = str(notice.get("tone", "")).strip().lower()
    if not title or not body:
        return ""
    tone_class = " welcome-card-warning" if tone == "warning" else ""
    code_html = f'<p class="welcome-card-path"><code>{html.escape(code)}</code></p>' if code else ""
    actions_html = (
        '<div class="welcome-action-row">'
        '<button type="button" class="welcome-button welcome-button-secondary welcome-button-compact" '
        f'data-welcome-copy="true" data-copy-text="{html.escape(copy_text, quote=True)}" '
        f'data-copy-status="{html.escape(copy_status or "Notice copied.", quote=True)}">{html.escape(copy_label)}</button>'
        "</div>"
        if copy_label and copy_text
        else ""
    )
    return (
        f'<section class="welcome-card welcome-card-notice{tone_class}">'
        f'<p class="welcome-card-kicker">{html.escape(title)}</p>'
        f'<p class="welcome-card-body">{html.escape(body)}</p>'
        f"{code_html}"
        f"{actions_html}"
        "</section>"
    )


def _render_welcome_slice_card(slice_state: Mapping[str, Any]) -> str:
    title = str(slice_state.get("title", "")).strip()
    path = str(slice_state.get("path", "")).strip()
    reason = str(slice_state.get("reason", "")).strip()
    guidance_value = slice_state.get("guidance")
    guidance: list[str] = []
    if isinstance(guidance_value, Sequence) and not isinstance(guidance_value, (str, bytes, bytearray)):
        guidance = [str(item).strip() for item in guidance_value if str(item).strip()]
    if not any((title, path, reason, guidance)):
        return ""
    path_html = (
        f'<p class="welcome-slice-path"><code>{html.escape(path)}</code></p>'
        if path
        else '<p class="welcome-slice-empty">No path detected yet</p>'
    )
    guidance_html = (
        '<ul class="welcome-slice-guidance">'
        + "".join(f"<li>{html.escape(item)}</li>" for item in guidance)
        + "</ul>"
        if guidance
        else ""
    )
    return (
        '<section class="welcome-card welcome-card-slice">'
        f'<p class="welcome-card-kicker">{html.escape(title or "Start here")}</p>'
        f"{path_html}"
        f'<p class="welcome-card-body">{html.escape(reason)}</p>'
        f"{guidance_html}"
        "</section>"
    )


def _render_surface_explainers(explainers: Sequence[Mapping[str, Any]]) -> str:
    cards: list[str] = []
    for explainer in explainers:
        surface = str(explainer.get("surface", "")).strip()
        sentence = str(explainer.get("sentence", "")).strip()
        if not surface or not sentence:
            continue
        cards.append(
            '<article class="welcome-explainer-card">'
            f'<p class="welcome-card-kicker">{html.escape(surface)}</p>'
            f'<p class="welcome-card-body">{html.escape(sentence)}</p>'
            "</article>"
        )
    if not cards:
        return ""
    return (
        '<section class="welcome-explainer-strip" aria-label="What each Odylith surface does first">'
        '<div class="welcome-explainer-head">'
        '<p class="welcome-kicker">Surface Guide</p>'
        '<h3 class="welcome-explainer-title">What the core surfaces do first</h3>'
        "</div>"
        '<div class="welcome-explainer-grid">'
        f'{"".join(cards)}'
        "</div>"
        "</section>"
    )


def render_welcome_state_html(payload: Mapping[str, Any]) -> str:
    welcome_state = _coerce_welcome_state(payload)
    release_spotlight_html = tooling_dashboard_release_presenter.render_release_spotlight_html(payload)
    notices_raw = welcome_state.get("notices")
    notices: tuple[dict[str, Any], ...] = ()
    if isinstance(notices_raw, Sequence) and not isinstance(notices_raw, (str, bytes, bytearray)):
        notices = tuple(dict(notice) for notice in notices_raw if isinstance(notice, Mapping))
    show = bool(welcome_state.get("show"))
    if not show and not notices:
        return release_spotlight_html

    if not show:
        notices_html = "".join(_render_welcome_notice(notice) for notice in notices)
        return release_spotlight_html + (
            '<section id="shellWelcomeState" class="welcome-state welcome-state-compact" aria-label="Odylith runtime notices">'
            '<div class="welcome-state-head">'
            '<p class="welcome-kicker">Odylith Notice</p>'
            '<h2 class="welcome-title">Odylith needs attention in this repository</h2>'
            '<p class="welcome-subhead">The shell found a repo-local condition that changes how Odylith behaves here.</p>'
            '<p id="welcomeCopyStatus" class="welcome-copy-status" aria-live="polite"></p>'
            "</div>"
            '<div class="welcome-grid">'
            f"{notices_html}"
            "</div>"
            '<div class="welcome-action-row">'
            '<button id="welcomeDismiss" type="button" class="welcome-button welcome-button-secondary">Dismiss</button>'
            "</div>"
            "</section>"
        )

    chosen_slice = dict(welcome_state.get("chosen_slice", {})) if isinstance(welcome_state.get("chosen_slice"), Mapping) else {}
    quick_steps = _welcome_lines(welcome_state.get("quick_steps"))
    starter_prompt = str(welcome_state.get("starter_prompt", "")).strip()
    auto_refresh_note = str(welcome_state.get("auto_refresh_note", "")).strip()
    dismiss_key = str(welcome_state.get("dismiss_key", "")).strip()
    headline = str(welcome_state.get("headline", "")).strip() or "Odylith is ready in this repository"
    subhead = str(welcome_state.get("subhead", "")).strip() or "Start with one prompt and let Odylith open one real code path."

    backlog = dict(welcome_state.get("backlog", {})) if isinstance(welcome_state.get("backlog"), Mapping) else {}
    component = dict(welcome_state.get("component", {})) if isinstance(welcome_state.get("component"), Mapping) else {}
    atlas = dict(welcome_state.get("atlas", {})) if isinstance(welcome_state.get("atlas"), Mapping) else {}
    record_cards: list[str] = []
    if bool(backlog.get("missing")):
        record_cards.append(
            _render_welcome_action_card(
                title=str(backlog.get("title", "")).strip() or "First Radar item",
                reason=str(backlog.get("reason", "")).strip() or "Open the first Radar item for this slice.",
                path_hint=str(backlog.get("path_hint", "")).strip() or "odylith/radar/source/ideas/",
                preview_note=str(backlog.get("preview_note", "")).strip(),
                cta_label="Open Radar view",
                tab="radar",
            )
        )
    if bool(component.get("missing")):
        record_cards.append(
            _render_welcome_action_card(
                title=str(component.get("title", "")).strip() or "First Registry boundary",
                reason=str(component.get("reason", "")).strip() or "Define the first Registry component for the chosen slice.",
                path_hint=str(component.get("path_hint", "")).strip() or "odylith/registry/source/components/<component>/CURRENT_SPEC.md",
                preview_note=str(component.get("preview_note", "")).strip(),
                cta_label="Open Registry view",
                tab="registry",
            )
        )
    if bool(atlas.get("missing")):
        record_cards.append(
            _render_welcome_action_card(
                title=str(atlas.get("title", "")).strip() or "First Atlas map",
                reason=str(atlas.get("reason", "")).strip() or "Draw the first Atlas diagram for the chosen slice.",
                path_hint=str(atlas.get("path_hint", "")).strip() or "odylith/atlas/source/",
                preview_note=str(atlas.get("preview_note", "")).strip(),
                cta_label="Open Atlas view",
                tab="atlas",
            )
        )

    notices_html = "".join(_render_welcome_notice(notice) for notice in notices)
    chosen_slice_html = _render_welcome_slice_card(chosen_slice)
    steps_html = _render_welcome_steps("Three quick steps", quick_steps)
    explainers_raw = welcome_state.get("surface_explainers")
    explainers = (
        tuple(dict(item) for item in explainers_raw if isinstance(item, Mapping))
        if isinstance(explainers_raw, Sequence) and not isinstance(explainers_raw, (str, bytes, bytearray))
        else ()
    )
    explainers_html = _render_surface_explainers(explainers)
    auto_refresh_html = f'<p class="welcome-refresh-note">{html.escape(auto_refresh_note)}</p>' if auto_refresh_note else ""
    prompt_card_html = (
        '<section class="welcome-prompt-card">'
        '<div class="welcome-prompt-copy">'
        '<p class="welcome-card-kicker">Copy this into your agent</p>'
        f'<p class="welcome-prompt-text"><strong>{html.escape(starter_prompt)}</strong></p>'
        f"{auto_refresh_html}"
        '<p id="welcomeCopyStatus" class="welcome-copy-status" aria-live="polite"></p>'
        "</div>"
        '<div class="welcome-action-row">'
        '<button id="welcomeCopyPrompt" type="button" class="welcome-button" '
        f'data-welcome-copy="true" data-copy-text="{html.escape(starter_prompt, quote=True)}" '
        'data-copy-status="Starter prompt copied. Paste it into your agent.">Copy prompt</button>'
        "</div>"
        "</section>"
    )
    records_html = (
        '<section class="welcome-record-grid">'
        f'{"".join(record_cards)}'
        "</section>"
        if record_cards
        else ""
    )
    return release_spotlight_html + (
        '<section id="shellWelcomeState" class="welcome-state welcome-state-launchpad" aria-label="Odylith first-run welcome state"'
        f' data-welcome-dismiss-key="{html.escape(dismiss_key, quote=True)}">'
        '<button id="welcomeDismiss" type="button" class="welcome-shell-dismiss" aria-label="Hide starter guide" title="Hide starter guide">&times;</button>'
        '<div class="welcome-launchpad-shell">'
        '<section class="welcome-launchpad-hero">'
        '<div class="welcome-launchpad-main">'
        '<div class="welcome-state-head">'
        '<p class="welcome-kicker">First Run</p>'
        f'<h2 class="welcome-title">{html.escape(headline)}</h2>'
        f'<p class="welcome-subhead">{html.escape(subhead)}</p>'
        "</div>"
        f"{prompt_card_html}"
        "</div>"
        '<div class="welcome-launchpad-aside">'
        f"{notices_html}"
        f"{chosen_slice_html}"
        f"{steps_html}"
        "</div>"
        "</section>"
        f"{explainers_html}"
        f"{records_html}"
        "</div>"
        "</section>"
    )
