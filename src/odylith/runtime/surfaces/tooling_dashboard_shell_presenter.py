"""Build reusable template context for the tooling dashboard shell."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from odylith.runtime.governance import proof_state
from odylith.runtime.surfaces import dashboard_template_runtime
from odylith.runtime.surfaces import tooling_dashboard_cheatsheet_presenter
from odylith.runtime.surfaces import tooling_dashboard_release_presenter
from odylith.runtime.surfaces import tooling_dashboard_template_context
from odylith.runtime.surfaces import tooling_dashboard_welcome_presenter


@dataclass(frozen=True)
class MaintainerNote:
    note_id: str
    title: str
    recorded_at: str
    context: str
    section_title: str
    bullets: tuple[str, ...]


def shell_case_preview_rows(case_queue: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Adapt Tribunal case rows into compact shell preview cards."""

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(case_queue):
        if not isinstance(case, Mapping):
            continue
        headline = str(case.get("headline", "")).strip()
        brief = str(case.get("brief", "")).strip()
        decision = str(case.get("decision_at_stake", "")).strip()
        scope_key = str(case.get("scope_key", "")).strip()
        resolved_proof_state = proof_state.normalize_proof_state(case.get("proof_state", {}))
        proof_lines = proof_state.proof_preview_lines(resolved_proof_state, compact=True, limit=4)
        proof_reopen = (
            dict(case.get("proof_reopen", {}))
            if isinstance(case.get("proof_reopen"), Mapping)
            else {}
        )
        reopen_summary = str(proof_reopen.get("summary", "")).strip()
        if reopen_summary and reopen_summary not in proof_lines:
            proof_lines = [reopen_summary, *proof_lines][:4]
        proof_state_resolution = (
            dict(case.get("proof_state_resolution", {}))
            if isinstance(case.get("proof_state_resolution"), Mapping)
            else {}
        )
        if not proof_lines:
            resolution_message = proof_state.proof_resolution_message(proof_state_resolution)
            if resolution_message:
                proof_lines = [resolution_message]
        claim_guard = (
            dict(case.get("claim_guard", {}))
            if isinstance(case.get("claim_guard"), Mapping)
            else {}
        )
        if not scope_key or not headline:
            continue
        rows.append(
            {
                "id": str(case.get("id", "")).strip() or f"case-{index + 1}",
                "rank": int(case.get("rank", index + 1) or (index + 1)),
                "count_label": f"#{int(case.get('rank', index + 1) or (index + 1))}",
                "severity_label": str(case.get("action_label", "")).strip() or "Review manually",
                "primary_scope_key": scope_key,
                "primary_scope_id": str(case.get("scope_id", "")).strip(),
                "title": headline,
                "summary": brief,
                "start_here": decision or brief,
                "start_here_short": decision or brief,
                "proof_state": resolved_proof_state,
                "proof_state_resolution": proof_state_resolution,
                "claim_guard": claim_guard,
                "proof_reopen": proof_reopen,
                "proof_lines": proof_lines,
                "proof_claim": str(claim_guard.get("highest_truthful_claim", "")).strip(),
            }
        )
    return rows


def _default_maintainer_notes() -> tuple[MaintainerNote, ...]:
    return ()


def _coerce_maintainer_notes(payload: Mapping[str, Any]) -> tuple[MaintainerNote, ...]:
    raw_notes = payload.get("maintainer_notes")
    if not isinstance(raw_notes, Sequence) or isinstance(raw_notes, (str, bytes, bytearray)):
        return ()
    notes: list[MaintainerNote] = []
    for index, raw_note in enumerate(raw_notes, start=1):
        if not isinstance(raw_note, Mapping):
            continue
        title = str(raw_note.get("title", "")).strip()
        if not title:
            continue
        bullets_value = raw_note.get("bullets", ())
        bullets: tuple[str, ...] = ()
        if isinstance(bullets_value, Sequence) and not isinstance(bullets_value, (str, bytes, bytearray)):
            bullets = tuple(str(item).strip() for item in bullets_value if str(item).strip())
        notes.append(
            MaintainerNote(
                note_id=str(raw_note.get("note_id", "")).strip() or f"N-{index:03d}",
                title=title,
                recorded_at=str(raw_note.get("recorded_at", "")).strip() or "unknown",
                context=str(raw_note.get("context", "")).strip() or "No developer context recorded.",
                section_title=str(raw_note.get("section_title", "")).strip() or "Pending",
                bullets=bullets,
            )
        )
    return tuple(notes)


def _render_maintainer_notes_html(notes: Sequence[MaintainerNote]) -> str:
    cards = []
    for note in notes:
        bullets_html = "".join(
            f"<li>{html.escape(bullet)}</li>"
            for bullet in note.bullets
        )
        cards.append(
            (
                '<article class="maintainer-note-card" role="listitem">'
                '<div class="maintainer-note-head">'
                f'<span class="maintainer-note-id">{html.escape(note.note_id)}</span>'
                f'<h3 class="maintainer-note-title">{html.escape(note.title)}</h3>'
                "</div>"
                '<div class="maintainer-note-meta">'
                f'<p><strong>Recorded</strong> {html.escape(note.recorded_at)}</p>'
                f'<p><strong>Context</strong> {html.escape(note.context)}</p>'
                "</div>"
                '<div class="maintainer-note-section">'
                f'<p class="maintainer-note-section-title">{html.escape(note.section_title)}</p>'
                f'<ul class="maintainer-note-bullets">{bullets_html}</ul>'
                "</div>"
                "</article>"
            )
        )
    if not cards:
        cards.append(
            (
                '<article class="maintainer-note-card maintainer-note-card-empty" role="listitem">'
                '<div class="maintainer-note-head">'
                '<span class="maintainer-note-id">N-000</span>'
                '<h3 class="maintainer-note-title">No developer notes recorded</h3>'
                "</div>"
                '<p class="maintainer-note-empty-copy">'
                "Add a source-owned developer note before relying on the shell drawer for platform context."
                "</p>"
                "</article>"
            )
        )
    return '<section class="maintainer-note-list" aria-label="Developer notes">' + "".join(cards) + "</section>"


def _render_release_spotlight_html(payload: Mapping[str, Any]) -> str:
    return tooling_dashboard_release_presenter.render_release_spotlight_html(payload)


def _render_welcome_state_html(payload: Mapping[str, Any]) -> str:
    return tooling_dashboard_welcome_presenter.render_welcome_state_html(payload)


def build_template_context(payload: Mapping[str, Any]) -> tooling_dashboard_template_context.ToolingDashboardTemplateContext:
    """Build the reusable template context for one tooling shell render."""

    maintainer_notes_html = _render_maintainer_notes_html(_coerce_maintainer_notes(payload) or _default_maintainer_notes())
    cheatsheet_html = tooling_dashboard_cheatsheet_presenter.render_agent_cheatsheet_html(payload)
    return tooling_dashboard_template_context.build_template_context(
        payload,
        welcome_html=_render_welcome_state_html(payload),
        maintainer_notes_html=maintainer_notes_html,
        cheatsheet_html=cheatsheet_html,
    )



def render_html(payload: Mapping[str, Any]) -> str:
    """Render the tooling shell HTML from a prepared payload."""

    context = build_template_context(payload)
    return dashboard_template_runtime.render_template(
        "tooling_dashboard/page.html.j2",
        **asdict(context),
    )
