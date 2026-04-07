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
        '<section class="welcome-process-card">'
        '<div class="welcome-process-head">'
        f'<p class="welcome-card-kicker">{html.escape(title)}</p>'
        '<p class="welcome-process-copy">Move from prompt to grounded work without leaving the shell.</p>'
        "</div>"
        '<ol class="welcome-step-list welcome-step-list-process">'
        + "".join(
            '<li class="welcome-step welcome-step-process">'
            f'<span class="welcome-step-index">{index}</span>'
            f'<span class="welcome-step-copy">{html.escape(item)}</span>'
            "</li>"
            for index, item in enumerate(items, start=1)
        )
        + "</ol>"
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
        '<p class="welcome-kicker">Core Surfaces</p>'
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

    quick_steps = _welcome_lines(welcome_state.get("quick_steps"))
    starter_prompt = str(welcome_state.get("starter_prompt", "")).strip()
    auto_refresh_note = str(welcome_state.get("auto_refresh_note", "")).strip()
    dismiss_key = str(welcome_state.get("dismiss_key", "")).strip()
    headline = str(welcome_state.get("headline", "")).strip() or "Odylith is ready in this repository"
    subhead = str(welcome_state.get("subhead", "")).strip() or "Start with one prompt and let Odylith open one real code path."

    notices_html = "".join(_render_welcome_notice(notice) for notice in notices)
    steps_html = _render_welcome_steps("Three quick steps", quick_steps)
    explainers_raw = welcome_state.get("surface_explainers")
    explainers = (
        tuple(dict(item) for item in explainers_raw if isinstance(item, Mapping))
        if isinstance(explainers_raw, Sequence) and not isinstance(explainers_raw, (str, bytes, bytearray))
        else ()
    )
    explainers_html = _render_surface_explainers(explainers)
    hero_badges_html = (
        '<div class="welcome-hero-badges">'
        '<span>Starter prompt ready</span>'
        '<span>Repo-native setup</span>'
        '<span>Cheatsheet built in</span>'
        "</div>"
    )
    auto_refresh_html = f'<p class="welcome-refresh-note">{html.escape(auto_refresh_note)}</p>' if auto_refresh_note else ""
    launchpad_grid_class = "welcome-launchpad-grid welcome-launchpad-grid-single" if not notices_html else "welcome-launchpad-grid"
    launchpad_notices_column_html = (
        '<div class="welcome-launchpad-column">'
        f"{notices_html}"
        "</div>"
        if notices_html
        else ""
    )
    prompt_card_html = (
        '<section class="welcome-prompt-card">'
        '<div class="welcome-prompt-copy">'
        '<div class="welcome-prompt-head">'
        '<p class="welcome-card-kicker">Copy this into your agent</p>'
        '<p class="welcome-prompt-intro">Ground one path, then let Odylith open the first governed records around it.</p>'
        "</div>"
        f"{steps_html}"
        '<div class="welcome-prompt-block">'
        f'<p class="welcome-prompt-text"><strong>"{html.escape(starter_prompt)}"</strong></p>'
        "</div>"
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
        f"{hero_badges_html}"
        "</div>"
        f"{prompt_card_html}"
        "</section>"
        f'<section class="{launchpad_grid_class}">'
        f"{launchpad_notices_column_html}"
        '<div class="welcome-launchpad-column">'
        f"{explainers_html}"
        "</div>"
        "</section>"
        "</div>"
        "</section>"
    )
