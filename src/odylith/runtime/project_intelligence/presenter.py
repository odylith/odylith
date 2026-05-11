"""Render the Project tab from the project-intelligence payload."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.deeplinks import inline_deeplink_html as _d
from odylith.runtime.project_intelligence.narration import table_columns as _default_table_columns


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _sequence(value: object) -> list[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _mappings(value: object) -> list[Mapping[str, Any]]:
    return [item for item in _sequence(value) if isinstance(item, Mapping)]


def _cards(items: object, class_name: str = "project-card") -> str:
    cards: list[str] = []
    for raw in _sequence(items):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        kicker, title, body = ("", "", "")
        if len(item) == 2:
            title, body = item
        elif len(item) >= 3:
            kicker, title, body = item[:3]
        if not title and not body:
            continue
        kicker_html = f"<p>{_d(kicker)}</p>" if str(kicker or "").strip() else ""
        cards.append(
            f'<article class="{class_name}">'
            f"{kicker_html}"
            f"<h3>{_d(title)}</h3>"
            f"<span>{_d(body)}</span>"
            "</article>"
        )
    return "".join(cards)


def _use_cases(items: object) -> str:
    rows: list[str] = []
    for raw in _sequence(items):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        if len(item) < 2:
            continue
        title = item[0]
        body = item[1]
        status = item[2] if len(item) > 2 else ""
        rows.append(
            '<article class="project-job-card">'
            f"<h3>{_d(title)}</h3>"
            f"<p>{_d(body)}</p>"
            f"<em>{_d(status)}</em>"
            "</article>"
        )
    return "".join(rows)


def _scenario_details(items: object, fallback: object) -> str:
    rows: list[str] = []
    for raw in _sequence(items):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        if len(item) < 2:
            continue
        label, body = item[:2]
        if not str(label or "").strip() or not str(body or "").strip():
            continue
        rows.append(f"<p><b>{_d(label)}</b><span>{_d(body)}</span></p>")
    if not rows and str(fallback or "").strip():
        rows.append(f"<p><span>{_d(fallback)}</span></p>")
    return "".join(rows)


def _bullets(items: object) -> str:
    values = [_d(item) for item in _sequence(items) if str(item or "").strip()]
    if not values:
        return "<ul><li>No current source-backed item found.</li></ul>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in values) + "</ul>"


def _table(items: object, columns: Sequence[tuple[str, str]]) -> str:
    rows = _mappings(items)
    if not rows:
        width = len(columns)
        return (
            '<div class="project-table"><table><tbody>'
            f'<tr><td colspan="{width}">No current source-backed rows found.</td></tr>'
            "</tbody></table></div>"
        )
    headers = "".join(f"<th>{_e(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = "".join(f"<td>{_d(row.get(key))}</td>" for key, _ in columns)
        body.append(f"<tr>{cells}</tr>")
    return f'<div class="project-table"><table><thead><tr>{headers}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _columns(project: Mapping[str, Any], key: str, fallback: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for raw in _sequence(project.get(key)):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        if len(item) >= 2 and str(item[0] or "").strip() and str(item[1] or "").strip():
            rows.append((str(item[0]), str(item[1])))
    return rows or list(fallback)


def _status_list(items: object, *, title_key: str, body_key: str) -> str:
    rows = _mappings(items)
    if not rows:
        return "<ul><li>No current source-backed item found.</li></ul>"
    return "<ul>" + "".join(f"<li><b>{_d(row.get(title_key))}</b>{_d(row.get(body_key))}</li>" for row in rows) + "</ul>"


def _sentence_lines(value: object) -> list[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return []
    return [line for line in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if line]


def _prose_lines(value: object) -> str:
    lines = _sentence_lines(value)
    if not lines:
        return "<div class=\"project-prose-lines\"><p>No current source-backed item found.</p></div>"
    return '<div class="project-prose-lines">' + "".join(f"<p>{_d(line)}</p>" for line in lines) + "</div>"


def _product_story(value: object) -> str:
    story = value if isinstance(value, Mapping) else {}
    headline = story.get("headline")
    standfirst = story.get("standfirst")
    narrative = _mappings(story.get("narrative"))
    actors = _mappings(story.get("actors"))
    artifacts = _mappings(story.get("artifacts"))
    topology = _mappings(story.get("topology_spine"))
    legacy_paragraphs = [_d(item) for item in _sequence(story.get("paragraphs")) if str(item or "").strip()]

    headline_html = f"<h3>{_d(headline)}</h3>" if str(headline or "").strip() else ""
    standfirst_html = f"<p>{_d(standfirst)}</p>" if str(standfirst or "").strip() else ""
    legacy_html = "".join(f"<p>{paragraph}</p>" for paragraph in legacy_paragraphs)
    narrative_html = "".join(
        '<article class="project-story-point">'
        f"<span>{_d(row.get('label'))}</span>"
        f"<h4>{_d(row.get('title'))}</h4>"
        f"<p>{_d(row.get('body'))}</p>"
        "</article>"
        for row in narrative
        if str(row.get("body") or "").strip()
    )
    actor_html = "".join(
        "<li>"
        f"<b>{_d(row.get('title'))}</b>"
        f"<span>{_d(row.get('body'))}</span>"
        "</li>"
        for row in actors
        if str(row.get("title") or "").strip()
    )
    actors_markup = f'<aside class="project-story-actors"><h4>Actors in the story</h4><ul>{actor_html}</ul></aside>' if actor_html else ""
    topology_markup = _story_topology_spine(
        topology,
        title=story.get("topology_title"),
        note=story.get("topology_note"),
    )
    artifact_intro = story.get("artifact_intro")
    artifact_html = "".join(_story_artifact(row) for row in artifacts)
    artifact_markup = (
        '<div class="project-story-artifacts">'
        f"<p>{_d(artifact_intro)}</p>"
        f'<div class="project-story-artifact-grid">{artifact_html}</div>'
        "</div>"
        if artifact_html
        else ""
    )
    return (
        '<div class="project-story-lede">'
        f'<div class="project-story-body">{headline_html}{standfirst_html}{legacy_html}</div>'
        f"{actors_markup}"
        "</div>"
        f"{topology_markup}"
        f'<div class="project-story-points">{narrative_html}</div>'
        f"{artifact_markup}"
    )


def _story_topology_spine(rows: Sequence[Mapping[str, Any]], *, title: object, note: object) -> str:
    if not rows:
        return ""
    title_html = f"<h3>{_d(title)}</h3>" if str(title or "").strip() else ""
    note_html = f"<p>{_d(note)}</p>" if str(note or "").strip() else ""
    nodes = "".join(
        '<article class="project-story-spine-node">'
        f"<em>{index}</em>"
        f"<span>{_d(row.get('label'))}</span>"
        f"<h4>{_d(row.get('title'))}</h4>"
        f"<p>{_d(row.get('body'))}</p>"
        "</article>"
        for index, row in enumerate(rows, start=1)
        if str(row.get("title") or row.get("body") or "").strip()
    )
    if not nodes:
        return ""
    return (
        '<div class="project-story-spine">'
        f'<div class="project-story-spine-head">{title_html}{note_html}</div>'
        f'<div class="project-story-spine-rail">{nodes}</div>'
        "</div>"
    )


def _story_artifact(group: Mapping[str, Any]) -> str:
    items = _mappings(group.get("items"))
    item_html = "".join(
        "<li>"
        f"<b>{_d(item.get('title'))}</b>"
        f"<span>{_d(item.get('body'))}</span>"
        "</li>"
        for item in items[:5]
        if str(item.get("title") or "").strip()
    )
    if not item_html:
        return ""
    return (
        "<article>"
        f"<span>{_d(group.get('label'))}</span>"
        f"<h3>{_d(group.get('title'))}</h3>"
        f"<p>{_d(group.get('body'))}</p>"
        f"<ul>{item_html}</ul>"
        "</article>"
    )


def _enabled(project: Mapping[str, Any], key: str) -> bool:
    sections = [str(item) for item in _sequence(project.get("sections")) if str(item or "").strip()]
    return key in sections if sections else True


def _fallback_payload() -> dict[str, Any]:
    return {
        "eyebrow": "Project lens · inferred",
        "title": "Project",
        "intro": "No project projection is available yet.",
        "chips": ["Evidence: inferred"],
        "focus_label": "Current project focus",
        "focus": "No source-backed project state is available.",
        "open_label": "Open project risks",
        "open": ["Project source payload missing"],
        "answers": [],
        "scenario": ["Current slice", "Project", "Source-backed page unavailable", "", ""],
        "scenario_title": "Project scenario",
        "scenario_note": "Source-backed scenario unavailable.",
        "actors": [],
        "participants_title": "Who participates?",
        "participants_note": "No source-backed participants found.",
        "participants": [],
        "jobs": [],
        "jobs_title": "What is active?",
        "jobs_note": "No source-backed jobs found.",
        "boundary_title": "What is inside the current boundary?",
        "boundary_note": "No source-backed boundary found.",
        "included_label": "Source-backed coverage",
        "excluded_label": "Unresolved boundary",
        "included": [],
        "excluded": [],
        "current": "Project source projection is missing.",
        "desired": "The Project tab renders from current source-backed project state.",
        "question": "How should the Project page be refreshed?",
        "recommendation": "Rebuild the dashboard after source records exist.",
        "options": [],
        "next": ["Refresh Project page", "Rebuild the Project tab.", "Dashboard", "Source-backed Project tab", "Source records", "Project page stays stale"],
        "known": [],
        "unknown": ["Project source payload missing"],
        "confidence": "Low",
        "blockers": [("Project source payload", "Missing", "dashboard")],
        "projection": {
            "refreshed_at": "not found",
            "origin": "unknown",
            "maturity": "thin evidence",
            "work_mode": "orienting",
            "topology_profile": "unknown",
        },
        "claim_evidence": [],
        "artifact_coverage": [],
        "topology_spine": [],
        "contradictions": ["Project source payload missing."],
        "delta": ["No previous source-backed Project snapshot is available."],
        "risk_classes": [],
        "validation_posture": [],
        "audience_emphasis": [],
        "degraded_state": ["Project source payload missing."],
        "claim_evidence_title": "What evidence exists?",
        "claim_evidence_note": "No Project claim evidence is available yet.",
        "topology_spine_title": "Topology spine",
        "topology_spine_note": "No source-backed topology spine is available yet.",
        "artifact_coverage_title": "Source coverage",
        "artifact_coverage_note": "No source-backed artifact coverage is available yet.",
        "trust_title": "What changed or degrades trust?",
        "trust_note": "No source-backed delta is available yet.",
        "delta_label": "Delta from previous state",
        "contradictions_label": "Contradictions",
        "degraded_label": "Degraded state intelligence",
        "posture_title": "What risk and validation posture matters?",
        "posture_note": "No source-backed risk posture is available yet.",
        "validation_label": "Validation posture",
        "risk_label": "Risk classes",
        "work_state_kicker": "Project status now",
        "state_title": "Project state unavailable",
        "state_note": "No source-backed execution state is available yet.",
        "current_state_label": "Current state",
        "desired_state_label": "Desired state",
        "next_title": "What should move next?",
        "next_note": "No source-backed next action is available yet.",
        "next_owner_label": "Owner",
        "next_output_label": "Expected output",
        "next_precondition_label": "Precondition",
        "next_risk_label": "Risk if delayed",
        "proof_title": "What is known and unproven?",
        "proof_note": "No source-backed proof state is available yet.",
        "known_label": "Known from source records",
        "unknown_label": "Unresolved in current projection",
        "confidence_label": "Confidence",
        **_default_table_columns(),
        "sources": {},
    }


def render_project_html(payload: Mapping[str, Any]) -> str:
    """Render Project tab HTML from a prepared tooling-dashboard payload."""

    project = payload.get("project_intelligence")
    if not isinstance(project, Mapping):
        project = _fallback_payload()
    default_columns = _default_table_columns()
    claim_columns = _columns(project, "claim_evidence_columns", default_columns["claim_evidence_columns"])
    scenario = _sequence(project.get("scenario"))
    _scenario_label, _scenario_name, scenario_headline, scenario_caption, scenario_body = (
        [*scenario, "", "", "", "", ""]
    )[:5]
    next_item = _sequence(project.get("next"))
    next_title, next_detail, next_owner, next_output, next_precondition, next_risk = (
        [*next_item, "", "", "", "", "", ""]
    )[:6]
    chips = "".join(f"<span>{_d(chip)}</span>" for chip in _sequence(project.get("chips")))
    scenario_html = (
        f"""
      <section class="project-panel project-scenario">
        <div class="project-panel-head"><h2>{_d(project.get("scenario_title"))}</h2><p>{_d(project.get("scenario_note"))}</p></div>
        <div class="project-scenario-body">
          <article class="project-scenario-cover"><strong>{_d(scenario_headline)}</strong><span>{_d(scenario_caption)}</span></article>
          <article class="project-scenario-copy">{_scenario_details(project.get("scenario_details"), scenario_body)}</article>
        </div>
      </section>
"""
        if _enabled(project, "scenario")
        else ""
    )
    product_story_html = (
        f"""      <section class="project-panel project-product-story">
        <div class="project-panel-head"><h2>{_d(project.get("product_story_title"))}</h2><p>{_d(project.get("product_story_note"))}</p></div>
        {_product_story(project.get("product_story"))}
      </section>
"""
        if _enabled(project, "product_story")
        else ""
    )
    answers_html = (
        f"""      <section class="project-answer-strip"><div class="project-answer-grid">{_cards(project.get("answers"), "project-answer-card")}</div></section>
"""
        if _sequence(project.get("answers"))
        else ""
    )
    participants_html = (
        f"""      <section class="project-panel project-participants"><div class="project-panel-head"><h2>{_d(project.get("participants_title"))}</h2><p>{_d(project.get("participants_note"))}</p></div><div class="project-card-grid project-actor-grid">{_cards(project.get("actors") or project.get("participants"), "project-actor-card")}</div></section>
"""
        if _enabled(project, "participants")
        else ""
    )
    jobs_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("jobs_title"))}</h2><p>{_d(project.get("jobs_note"))}</p></div><div class="project-job-grid">{_use_cases(project.get("jobs"))}</div></section>
"""
        if _enabled(project, "jobs")
        else ""
    )
    claim_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("claim_evidence_title"))}</h2><p>{_d(project.get("claim_evidence_note"))}</p></div>{_table(project.get("claim_evidence"), claim_columns)}</section>
"""
        if _enabled(project, "claim_evidence")
        else ""
    )
    trust_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("trust_title"))}</h2><p>{_d(project.get("trust_note"))}</p></div><div class="project-signal-grid"><article><h3>{_d(project.get("delta_label"))}</h3>{_bullets(project.get("delta"))}</article><article><h3>{_d(project.get("contradictions_label"))}</h3>{_bullets(project.get("contradictions"))}</article><article><h3>{_d(project.get("degraded_label"))}</h3>{_bullets(project.get("degraded_state"))}</article></div></section>
"""
        if _enabled(project, "trust")
        else ""
    )
    posture_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("posture_title"))}</h2><p>{_d(project.get("posture_note"))}</p></div><div class="project-signal-grid project-signal-grid-two"><article><h3>{_d(project.get("validation_label"))}</h3>{_status_list(project.get("validation_posture"), title_key="posture", body_key="meaning")}</article><article><h3>{_d(project.get("risk_label"))}</h3>{_status_list(project.get("risk_classes"), title_key="risk", body_key="meaning")}</article></div></section>
"""
        if _enabled(project, "posture")
        else ""
    )
    boundary_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("boundary_title"))}</h2><p>{_d(project.get("boundary_note"))}</p></div><div class="project-boundary-grid"><article class="project-included"><h3>{_d(project.get("included_label"))}</h3>{_bullets(project.get("included"))}</article><article class="project-excluded"><h3>{_d(project.get("excluded_label"))}</h3>{_bullets(project.get("excluded"))}</article></div></section>
"""
        if _enabled(project, "boundary")
        else ""
    )
    state_html = (
        f"""      <p class="project-section-kicker">{_d(project.get("work_state_kicker"))}</p>
      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("state_title"))}</h2><p>{_d(project.get("state_note"))}</p></div><div class="project-state-grid"><article><h3>{_d(project.get("current_state_label"))}</h3>{_prose_lines(project.get("current"))}</article><strong>to</strong><article><h3>{_d(project.get("desired_state_label"))}</h3>{_prose_lines(project.get("desired"))}</article></div></section>
"""
        if _enabled(project, "state")
        else ""
    )
    next_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("next_title"))}</h2><p>{_d(project.get("next_note"))}</p></div><article class="project-next-card project-next-card-full"><h3>{_d(next_title)}</h3><p>{_d(next_detail)}</p><div><span><b>{_d(project.get("next_owner_label"))}</b>{_d(next_owner)}</span><span><b>{_d(project.get("next_output_label"))}</b>{_d(next_output)}</span><span><b>{_d(project.get("next_precondition_label"))}</b>{_d(next_precondition)}</span><span><b>{_d(project.get("next_risk_label"))}</b>{_d(next_risk)}</span></div></article></section>
"""
        if _enabled(project, "next")
        else ""
    )
    proof_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("proof_title"))}</h2><p>{_d(project.get("proof_note"))}</p></div><div class="project-proof-grid"><article><h3>{_d(project.get("known_label"))}</h3>{_bullets(project.get("known"))}</article><article><h3>{_d(project.get("unknown_label"))}</h3>{_bullets(project.get("unknown"))}</article><article><h3>{_d(project.get("confidence_label"))}</h3><strong>{_d(project.get("confidence"))}</strong><span class="project-meter"><i></i></span></article></div></section>
"""
        if _enabled(project, "proof")
        else ""
    )
    return f"""
<div class="project-surface">
  <header class="project-hero">
    <div class="project-hero-main">
      <div class="project-hero-copy">
        <p class="project-eyebrow"><span></span>{_d(project.get("eyebrow"))}</p>
        <h1>{_d(project.get("title"))}</h1>
        <p class="project-intro">{_d(project.get("intro"))}</p>
        <div class="project-chips">{chips}</div>
      </div>
      <aside class="project-hero-rail">
        <section class="project-focus-card"><p>{_d(project.get("focus_label"))}</p><h2>{_d(project.get("focus"))}</h2></section>
        <section class="project-open-card"><p>{_d(project.get("open_label"))}</p>{_bullets(project.get("open"))}</section>
      </aside>
    </div>
  </header>

  <div class="project-page-grid">
    <main class="project-main">
{product_story_html}{answers_html}{scenario_html}{participants_html}{jobs_html}{claim_html}{trust_html}{posture_html}{boundary_html}{state_html}{next_html}{proof_html}
    </main>
  </div>
</div>
""".strip()
