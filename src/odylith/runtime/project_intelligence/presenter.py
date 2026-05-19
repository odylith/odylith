"""Render the Project tab from the project-intelligence payload."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.deeplinks import deeplink_title_context
from odylith.runtime.project_intelligence.deeplinks import inline_deeplink_html as _deeplink_html
from odylith.runtime.project_intelligence.narration import table_columns as _default_table_columns
from odylith.runtime.project_intelligence.utils import display_text, sentence
from odylith.runtime.surfaces.dashboard_shell_links import radar_workstream_href


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _d(value: object) -> str:
    return _deeplink_html(display_text(value))


def _project_chip_tone(value: object) -> str:
    text = display_text(value).casefold()
    if any(token in text for token in ("risk", "question", "blocker", "unresolved", "missing", "weak", "unproven")):
        return "warning"
    if any(token in text for token in ("accepted", "confirmed", "passed", "source", "user", "inferred", "governed")):
        return "success"
    return "neutral"


def _project_label_chip(value: object) -> str:
    label = display_text(value)
    if not label:
        return ""
    tone = _project_chip_tone(label)
    return f'<span class="project-label-chip project-label-chip-{tone}">{_d(label)}</span>'


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
        kicker = display_text(kicker)
        title = display_text(title)
        body = display_text(body)
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


def _answer_table(items: object) -> str:
    rows: list[str] = []
    for raw in _sequence(items):
        item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
        question, title, body = ("", "", "")
        if len(item) == 2:
            title, body = item
        elif len(item) >= 3:
            question, title, body = item[:3]
        question = display_text(question)
        title = display_text(title)
        body = display_text(body)
        if not question and not title and not body:
            continue
        body_html = ""
        if title:
            body_html += f"<strong>{_d(title)}</strong>"
        if body:
            body_html += f"<p>{_d(body)}</p>"
        rows.append(
            "<tr>"
            f'<th scope="row">{_d(question or "Project question")}</th>'
            f"<td>{body_html}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return (
        '<div class="project-answer-table">'
        "<table><tbody>"
        f"{''.join(rows)}"
        "</tbody></table>"
        "</div>"
    )


def _use_cases(items: object) -> str:
    rows: list[str] = []
    for raw in _sequence(items):
        if isinstance(raw, Mapping):
            title = raw.get("title")
            body = raw.get("body") or raw.get("summary")
            status = raw.get("status") or raw.get("evidence_tier")
            workstream_id = _workstream_id(raw.get("workstream_id") or raw.get("idea_id") or raw.get("id"))
        else:
            item = list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) else []
            if len(item) < 2:
                continue
            title = item[0]
            body = item[1]
            status = item[2] if len(item) > 2 else ""
            workstream_id = _workstream_id(item[3] if len(item) > 3 else "")
        title_html = _job_title_html(title=title, workstream_id=workstream_id)
        id_html = _job_workstream_link(workstream_id=workstream_id, title=title)
        status_html = _project_label_chip(status)
        meta_html = (
            f'<div class="project-job-meta">{id_html}{status_html}</div>' if status_html or id_html else ""
        )
        rows.append(
            '<article class="project-job-card">'
            f"<h3>{title_html}</h3>"
            f"<p>{_d(body)}</p>"
            f"{meta_html}"
            "</article>"
        )
    return "".join(rows)


def _workstream_id(value: object) -> str:
    token = sentence(value).upper()
    return token if re.fullmatch(r"B-\d+", token) else ""


def _job_title_html(*, title: object, workstream_id: str) -> str:
    label = _e(display_text(title))
    if not workstream_id:
        return label
    href = _e(radar_workstream_href(workstream_id))
    aria = _e(f"Open {workstream_id} in Radar")
    return f'<a class="project-job-title-link" target="_top" href="{href}" aria-label="{aria}">{label}</a>'


def _job_workstream_link(*, workstream_id: str, title: object) -> str:
    if not workstream_id:
        return ""
    href = _e(radar_workstream_href(workstream_id))
    tooltip = _e(display_text(title) or workstream_id)
    aria = _e(f"Open {workstream_id} in Radar")
    return (
        '<span class="project-job-workstream">'
        f'<a class="project-workstream-chip project-deeplink project-id-deeplink" target="_top" href="{href}" '
        f'data-tooltip="{tooltip}" aria-label="{aria}">{_e(workstream_id)}</a>'
        "</span>"
    )


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
        rows.append(f'<p class="project-scenario-prose">{_d(fallback)}</p>')
    return "".join(rows)


def _bullets(items: object) -> str:
    values = [_d(item) for item in _sequence(items) if str(item or "").strip()]
    if not values:
        return "<ul><li>No current source-backed item found.</li></ul>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in values) + "</ul>"


def _compact_bullets(items: object, *, limit: int = 4, item_limit: int = 160) -> str:
    raw_values = [str(item).strip() for item in _sequence(items) if str(item or "").strip()]
    if not raw_values:
        return "<ul><li>No current source-backed item found.</li></ul>"
    values = [_d(_compact_sentence(item, limit=item_limit)) for item in raw_values[:limit]]
    if len(raw_values) > limit:
        values.append(f'<span class="project-more-count">+{len(raw_values) - limit} more tracked item{"s" if len(raw_values) - limit != 1 else ""}</span>')
    return "<ul>" + "".join(f"<li>{item}</li>" for item in values) + "</ul>"


def _compact_sentence(value: str, *, limit: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    for separator in (". ", "; ", ": "):
        head, sep, _tail = text.partition(separator)
        if sep and 42 <= len(head) <= limit:
            return head.rstrip(" ,;:") + ("." if separator == ". " else "")
    words = text.split()
    clipped: list[str] = []
    length = 0
    for word in words:
        next_length = length + len(word) + (1 if clipped else 0)
        if next_length > limit:
            break
        clipped.append(word)
        length = next_length
    return " ".join(clipped).rstrip(" ,;:") + "."


def _display_title(value: object) -> str:
    text = " ".join(str(value or "").split()).strip()
    text = re.sub(r"^[\s\-–—:·|]+", "", text)
    text = re.sub(r"[\s\-–—:·|]+$", "", text)
    return text


def _host_handoff(project: Mapping[str, Any]) -> str:
    rows = _mappings(project.get("host_handoff_prompts"))
    if not rows:
        return ""
    steps = [_d(item) for item in _sequence(project.get("host_handoff_steps")) if str(item or "").strip()]
    steps_html = f'<ol>{"".join(f"<li>{item}</li>" for item in steps)}</ol>' if steps else ""
    cards: list[str] = []
    for row in rows:
        label = row.get("label")
        when = row.get("when")
        prompt = row.get("prompt")
        result = row.get("result")
        if not str(prompt or "").strip():
            continue
        cards.append(
            '<article class="project-host-prompt">'
            f"<h4>{_d(label)}</h4>"
            f"<p>{_d(when)}</p>"
            f"<code>{_e(prompt)}</code>"
            f"<span>{_d(result)}</span>"
            "</article>"
        )
    if not cards:
        return ""
    return (
        '<div class="project-host-handoff">'
        f"<h3>{_d(project.get('host_handoff_title'))}</h3>"
        f"<p>{_d(project.get('host_handoff_note'))}</p>"
        f"{steps_html}"
        f'<div class="project-host-prompt-grid">{"".join(cards)}</div>'
        "</div>"
    )


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


def _claim_evidence(project: Mapping[str, Any], columns: Sequence[tuple[str, str]]) -> str:
    rows = _mappings(project.get("claim_evidence"))
    if not rows:
        return _table(rows, columns)
    grouped = _claim_evidence_groups(rows, project=project)
    takeaway = _claim_evidence_takeaway(grouped=grouped, project=project)
    cards = "".join(
        _claim_evidence_card(title=title, body=body, rows=items)
        for title, body, items in grouped
        if items
    )
    if not cards:
        cards = _claim_evidence_card(
            title="Evidence needs review",
            body="The current projection has claim rows, but none could be placed into a readable trust group.",
            rows=rows,
        )
    audit = (
        '<details class="project-evidence-audit">'
        '<summary>View claim audit</summary>'
        f"{_table(rows, columns)}"
        "</details>"
    )
    return f"{takeaway}<div class=\"project-evidence-readout\">{cards}</div>{audit}"


def _claim_evidence_takeaway(
    *, grouped: Sequence[tuple[str, str, list[Mapping[str, Any]]]], project: Mapping[str, Any]
) -> str:
    source_posture = str(project.get("source_posture") or "").strip().casefold()
    origin = " ".join(str(item or "") for item in _sequence(project.get("chips"))).casefold()
    greenfield = "greenfield" in origin or source_posture in {"docs_only", "metadata_only", "empty_or_no_app_source"}
    if greenfield:
        body = (
            "The product direction is accepted enough to plan from, but the software behavior is not trusted yet. "
            "Treat the component shape as proposed until release proof passes with source and validation evidence."
        )
    else:
        body = (
            "Takeaway: trust current source-backed facts first. Treat proposed, stale, missing, or contradicted claims as "
            "work that still needs evidence before it guides implementation."
        )
    counts = [f"{len(rows)} {title.lower()}" for title, _body, rows in grouped if rows]
    count_html = f"<span>{_d('; '.join(counts))}</span>" if counts else ""
    return (
        '<div class="project-evidence-takeaway">'
        "<b>Summary</b>"
        f"<p>{_d(body)}</p>"
        f"{count_html}"
        "</div>"
    )


def _claim_evidence_groups(
    rows: Sequence[Mapping[str, Any]], *, project: Mapping[str, Any]
) -> list[tuple[str, str, list[Mapping[str, Any]]]]:
    known: list[Mapping[str, Any]] = []
    proposed: list[Mapping[str, Any]] = []
    proof: list[Mapping[str, Any]] = []
    source_posture = str(project.get("source_posture") or "").strip().casefold()
    origin = " ".join(str(item or "") for item in _sequence(project.get("chips"))).casefold()
    greenfield = "greenfield" in origin or source_posture in {"docs_only", "metadata_only", "empty_or_no_app_source"}
    for row in rows:
        evidence = str(row.get("evidence") or "").strip().casefold()
        claim = str(row.get("claim") or "").strip().casefold()
        if any(token in claim for token in ("question", "risk", "blocker", "unknown", "gap")):
            proof.append(row)
        elif evidence in {"needs validation", "stale", "contradicted", "missing", "unproven"}:
            proof.append(row)
        elif evidence in {"inferred", "assumed", "proposal", "proposed"}:
            proposed.append(row)
        else:
            known.append(row)
    if greenfield:
        return [
            (
                "Direction accepted",
                "The product story and release boundary can guide planning.",
                known,
            ),
            (
                "Shape to build",
                "These choices describe the planned product shape, not built behavior.",
                proposed,
            ),
            (
                "Proof to earn",
                "These checks decide whether the first release can be trusted.",
                proof,
            ),
        ]
    return [
        (
            "Observed now",
            "These are the current project facts supported by source, runtime, validation, or accepted records.",
            known,
        ),
        (
            "Working hypothesis",
            "These claims may guide the next move, but they need stronger source, owner, or validation evidence.",
            proposed,
        ),
        (
            "Proof gaps",
            "These validation gaps, open questions, or weak claims block stronger confidence.",
            proof,
        ),
    ]


def _claim_evidence_card(*, title: str, body: str, rows: Sequence[Mapping[str, Any]]) -> str:
    items = []
    for row in rows:
        claim = _claim_label(str(row.get("claim") or "").strip() or "Claim")
        value = _claim_card_value(claim=claim, value=row.get("value"))
        evidence = str(row.get("evidence") or "").strip()
        owner = str(row.get("owner") or "").strip()
        meta_parts = [
            part
            for part in (_evidence_phrase(evidence) if evidence else "", f"Owner: {owner}" if owner else "")
            if part
        ]
        meta = " · ".join(meta_parts)
        meta_html = f"<small>{_d(meta)}</small>" if meta else ""
        items.append(f"<li><b>{_d(claim)}</b><span>{_d(value)}</span>{meta_html}</li>")
    return (
        '<article class="project-evidence-card">'
        f"<h3>{_d(title)}</h3>"
        f"<p>{_d(body)}</p>"
        "<ul>"
        + "".join(items)
        + "</ul>"
        "</article>"
    )


def _claim_card_value(*, claim: str, value: object) -> str:
    text = str(value or "").strip() or "No value recorded."
    lowered_claim = claim.casefold()
    if lowered_claim in {"first path", "proof required"}:
        text = re.sub(r"\b\d+[.)]\s+[A-Z].*", "", text).strip(" .")
        text = text.replace("The first complete path the product must prove is ", "")
        text = text.replace("The accepted first path passes end to end:", "Release proof must pass end to end:")
    if lowered_claim == "project promise":
        return "Captured in the Product Story section above."
    if lowered_claim == "proof required" and (
        "reviewer can compare" in text.casefold() or "without trusting implementation prose" in text.casefold()
    ):
        return "Reviewer must see source evidence, validation output, non-goals, and the release decision."
    if lowered_claim == "open questions":
        return text
    return _compact_sentence(text, limit=150)


def _claim_label(value: str) -> str:
    labels = {
        "project identity": "Project",
        "greenfield tribunal": "Accepted product check",
        "validation gate": "Accepted product check",
        "project explanation": "Project promise",
        "first path": "First path",
        "validation path": "Proof required",
        "open questions": "Open questions",
    }
    return labels.get(value.strip().casefold(), value)


def _evidence_phrase(value: str) -> str:
    labels = {
        "user-stated": "Stated by operator",
        "inferred": "Inferred from proposal",
        "assumed": "Assumption",
        "proposal": "Proposal claim",
        "proposed": "Proposal claim",
        "needs validation": "Needs validation",
        "governed": "Accepted by project check",
        "source-backed": "Source-backed",
        "validated": "Validated",
        "operational": "Observed in runtime",
        "stale": "Stale evidence",
        "contradicted": "Conflicting evidence",
        "missing": "Missing evidence",
        "unproven": "Unproven",
    }
    return labels.get(value.strip().casefold(), f"Evidence: {value}")


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
    paragraphs = [str(item).strip() for item in _sequence(story.get("paragraphs")) if str(item or "").strip()]
    supporting_records = [str(item).strip() for item in _sequence(story.get("supporting_records")) if str(item or "").strip()]
    release_contract = _mappings(story.get("release_contract"))
    if not paragraphs and str(standfirst or "").strip():
        paragraphs.append(str(standfirst).strip())
    narrative = _mappings(story.get("narrative"))
    paragraphs.extend(
        " ".join(
            part
            for part in (str(row.get("title") or "").strip(), str(row.get("body") or "").strip())
            if part
        )
        for row in narrative
        if str(row.get("body") or "").strip()
    )
    return _product_story_narrative(
        headline=headline,
        paragraphs=paragraphs,
        release_contract=release_contract,
        supporting_records=supporting_records,
    )


def _product_story_narrative(
    *,
    headline: object,
    paragraphs: Sequence[str],
    release_contract: Sequence[Mapping[str, Any]],
    supporting_records: Sequence[str],
) -> str:
    clean_headline = _display_title(headline)
    headline_html = f"<h3>{_d(clean_headline)}</h3>" if clean_headline else ""
    paragraph_rows = [paragraph for paragraph in paragraphs if str(paragraph or "").strip()]
    first_paragraph = paragraph_rows[:1]
    remaining_paragraphs = paragraph_rows[1:]
    first_html = "".join(f"<p>{_d(paragraph)}</p>" for paragraph in first_paragraph)
    remaining_html = "".join(f"<p>{_d(paragraph)}</p>" for paragraph in remaining_paragraphs)
    contract_html = _product_story_contract(release_contract)
    records_html = (
        '<ul class="project-story-records">'
        + "".join(f"<li>{_d(row)}</li>" for row in supporting_records if str(row or "").strip())
        + "</ul>"
        if supporting_records
        else ""
    )
    return (
        '<article class="project-story-narrative">'
        f"{headline_html}{first_html}{contract_html}{remaining_html}{records_html}"
        "</article>"
    )


def _product_story_contract(rows: Sequence[Mapping[str, Any]]) -> str:
    items = [
        (str(row.get("label") or "").strip(), str(row.get("body") or "").strip())
        for row in rows
        if str(row.get("label") or row.get("body") or "").strip()
    ]
    if not items:
        return ""
    cells = "".join(f"<div><dt>{_d(label)}</dt><dd>{_d(body)}</dd></div>" for label, body in items)
    return f'<dl class="project-story-contract">{cells}</dl>'


def _render_blank_actions(items: object) -> str:
    rows: list[str] = []
    for row in _mappings(items):
        command = str(row.get("command") or "").strip()
        command_html = f"<code>{_e(command)}</code>" if command else ""
        rows.append(
            '<article class="project-empty-action">'
            f"<h3>{_d(row.get('title'))}</h3>"
            f"<p>{_d(row.get('body'))}</p>"
            f"{command_html}"
            "</article>"
        )
    return "".join(rows)


def _render_blank_preview(items: object) -> str:
    rows = _mappings(items)
    if not rows:
        return ""
    return "".join(
        '<article class="project-empty-preview-card">'
        f"<h3>{_d(row.get('title'))}</h3>"
        f"<p>{_d(row.get('body'))}</p>"
        "</article>"
        for row in rows
        if str(row.get("title") or row.get("body") or "").strip()
    )


def _render_blank_readout(items: object) -> str:
    values = [_d(item) for item in _sequence(items) if str(item or "").strip()]
    if not values:
        return ""
    return '<ul class="project-empty-readout">' + "".join(f"<li>{item}</li>" for item in values) + "</ul>"


def _render_blank_project(project: Mapping[str, Any]) -> str:
    chips = "".join(_project_label_chip(chip) for chip in _sequence(project.get("chips")))
    return f"""
<div class="project-surface project-surface-empty">
  <header class="project-hero project-hero-empty">
    <div class="project-hero-main project-hero-main-empty">
      <div class="project-hero-copy">
        <p class="project-eyebrow"><span></span>{_d(project.get("eyebrow"))}</p>
        <h1>{_d(_display_title(project.get("title")))}</h1>
        <p class="project-intro">{_d(project.get("intro"))}</p>
        <div class="project-chips">{chips}</div>
      </div>
    </div>
  </header>

  <main class="project-main">
    <section class="project-panel project-empty-panel">
      <div class="project-panel-head"><h2>{_d(project.get("blank_title"))}</h2><p>{_d(project.get("blank_note"))}</p></div>
      <div class="project-empty-action-grid">{_render_blank_actions(project.get("blank_actions"))}</div>
      {_render_blank_readout(project.get("blank_readout"))}
    </section>
    <section class="project-panel project-empty-preview">
      <div class="project-panel-head"><h2>{_d(project.get("blank_preview_title"))}</h2></div>
      <div class="project-empty-preview-grid">{_render_blank_preview(project.get("blank_preview"))}</div>
    </section>
  </main>
</div>
""".strip()


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
    with deeplink_title_context(project.get("governance_titles")):
        return _render_project_html_project(project)


def _render_project_html_project(project: Mapping[str, Any]) -> str:
    if str(project.get("mode") or "").strip().lower() == "blank":
        return _render_blank_project(project)
    default_columns = _default_table_columns()
    claim_columns = _columns(project, "claim_evidence_columns", default_columns["claim_evidence_columns"])
    scenario = _sequence(project.get("scenario"))
    _scenario_label, _scenario_name, scenario_headline, scenario_caption, scenario_body = (
        [*scenario, "", "", "", "", ""]
    )[:5]
    chips = "".join(_project_label_chip(chip) for chip in _sequence(project.get("chips")))
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
        <div class="project-panel-head"><h2>{_d(project.get("product_story_title"))}</h2>{f'<p>{_d(project.get("product_story_note"))}</p>' if str(project.get("product_story_note") or "").strip() else ''}</div>
        {_product_story(project.get("product_story"))}
      </section>
"""
        if _enabled(project, "product_story")
        else ""
    )
    answer_table = _answer_table(project.get("answers"))
    answers_html = (
        f"""      <section class="project-panel project-answer-strip" aria-label="Project summary table">{answer_table}</section>
"""
        if answer_table
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
    claim_html = ""
    trust_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("trust_title"))}</h2><p>{_d(project.get("trust_note"))}</p></div><div class="project-signal-grid"><article><h3>{_d(project.get("delta_label"))}</h3>{_bullets(project.get("delta"))}</article><article><h3>{_d(project.get("contradictions_label"))}</h3>{_bullets(project.get("contradictions"))}</article><article><h3>{_d(project.get("degraded_label"))}</h3>{_bullets(project.get("degraded_state"))}</article></div></section>
"""
        if _enabled(project, "trust")
        else ""
    )
    posture_html = ""
    boundary_html = ""
    state_html = (
        f"""      <p class="project-section-kicker">{_d(project.get("work_state_kicker"))}</p>
      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("state_title"))}</h2><p>{_d(project.get("state_note"))}</p></div><div class="project-state-grid"><article><h3>{_d(project.get("current_state_label"))}</h3>{_prose_lines(project.get("current"))}</article><strong>to</strong><article><h3>{_d(project.get("desired_state_label"))}</h3>{_prose_lines(project.get("desired"))}</article></div></section>
"""
        if _enabled(project, "state")
        else ""
    )
    host_handoff_html = _host_handoff(project)
    next_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("next_title"))}</h2><p>{_d(project.get("next_note"))}</p></div>{host_handoff_html}</section>
"""
        if _enabled(project, "next")
        else ""
    )
    proof_html = (
        f"""      <section class="project-panel"><div class="project-panel-head"><h2>{_d(project.get("proof_title"))}</h2><p>{_d(project.get("proof_note"))}</p></div><div class="project-proof-grid"><article><h3>{_d(project.get("known_label"))}</h3>{_bullets(project.get("known"))}</article><article><h3>{_d(project.get("unknown_label"))}</h3>{_bullets(project.get("unknown"))}</article><article><h3>{_d(project.get("confidence_label"))}</h3><strong>{_d(project.get("confidence"))}</strong><span class="project-meter"><i></i></span><p>{_d(project.get("confidence_note"))}</p></article></div></section>
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
        <h1>{_d(_display_title(project.get("title")))}</h1>
        <p class="project-intro">{_d(project.get("intro"))}</p>
        <div class="project-chips">{chips}</div>
      </div>
      <aside class="project-hero-rail">
        <section class="project-focus-card"><p>{_d(_hero_rail_label(project.get("focus_label"), title=project.get("title"), fallback="Current focus"))}</p><h2>{_d(project.get("focus"))}</h2></section>
        <section class="project-open-card"><p>{_d(_hero_rail_label(project.get("open_label"), title=project.get("title"), fallback="Open questions"))}</p>{_compact_bullets(project.get("open"))}</section>
      </aside>
    </div>
  </header>

  <div class="project-page-grid">
    <main class="project-main">
{product_story_html}{participants_html}{answers_html}{scenario_html}{jobs_html}{claim_html}{trust_html}{posture_html}{boundary_html}{state_html}{next_html}{proof_html}
    </main>
  </div>
</div>
""".strip()


def _hero_rail_label(value: object, *, title: object, fallback: str) -> str:
    """Keep the hero rail labels short after the main hero has named the project."""

    label = sentence(value, fallback)
    project_title = sentence(title)
    if project_title:
        label = re.sub(re.escape(project_title), "", label, flags=re.IGNORECASE)
        label = re.sub(r"\s+", " ", label).strip(" -:|")
    return label or fallback
