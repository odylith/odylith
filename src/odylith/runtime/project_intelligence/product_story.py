"""General Product Story projection for the Project tab."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.project_intelligence.focus import backlog_rows_by_id
from odylith.runtime.project_intelligence.narration import evidence_boundary_phrase
from odylith.runtime.project_intelligence.summary import action_sentence, concise_text
from odylith.runtime.project_intelligence.utils import dict_value, list_value, sentence, short, strings


def build_greenfield_product_story(
    *,
    title: str,
    intro: str,
    project: Mapping[str, Any],
    first_path: str,
    release: str,
    release_plan: Mapping[str, Any],
    accepted: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    actors: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    """Build proposal-origin story prose from the accepted project graph."""

    objective = project_intent_line(project, "project objective")
    outcome = project_intent_line(project, "user or stakeholder outcome")
    success = project_intent_line(project, "success condition")
    failure = project_intent_line(project, "what breaks if it fails")
    non_goals = project_intent_line(project, "non-goals")
    first_release = sentence(release_plan.get("strategy"))
    release_text = sentence(first_release or success, f"Release {release} proves the first path before broader buildout.")
    created = dict_value(accepted.get("created"))
    workstream_items = _workstream_story_items(created=created, backlog=backlog)
    component_items = _component_story_items(created=created, components=components)
    diagram_items = _diagram_story_items(created=created, diagrams=diagrams)
    headline = _greenfield_headline(first_path=first_path, title=title)
    paragraphs = _greenfield_paragraphs(
        objective=objective,
        intro=intro,
        outcome=outcome,
        success=success,
        failure=failure,
        non_goals=non_goals,
        first_path=first_path,
        release=release,
        release_text=release_text,
        actors=actors,
        workstreams=workstream_items,
        components=component_items,
        diagrams=diagram_items,
    )
    supporting_records = _greenfield_supporting_records(
        workstreams=workstream_items,
        components=component_items,
        diagrams=diagram_items,
        release=release,
    )
    return {
        "headline": headline,
        "standfirst": "",
        "paragraphs": paragraphs,
        "supporting_records": supporting_records,
        "actors": _story_actor_items(actors),
    }


def build_source_product_story(
    *,
    project_title: str,
    project_intro: str,
    release_label: str,
    work_mode: str,
    current_focus: str,
    next_title: str,
    next_action_text: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    atlas: Mapping[str, Any],
    evidence_sources: Sequence[str],
    blockers: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    """Build source-backed story prose for existing projects and operations."""

    title = sentence(project_title, "Project")
    headline = _source_headline(
        title=title,
        project_intro=project_intro,
        current_focus=current_focus,
        active_workstreams=active_workstreams,
        backlog=backlog,
    )
    current = _source_current_paragraph(
        title=title,
        project_intro=project_intro,
        release_label=release_label,
        work_mode=work_mode,
        current_focus=current_focus,
        next_action_text=next_action_text,
        blockers=blockers,
    )
    artifact = _source_artifact_paragraph(
        active_workstreams=active_workstreams,
        backlog=backlog,
        components=components,
        atlas=atlas,
        evidence_sources=evidence_sources,
    )
    supporting_records = _source_supporting_records(
        active_workstreams=active_workstreams,
        backlog=backlog,
        components=components,
        atlas=atlas,
        evidence_sources=evidence_sources,
    )
    paragraphs = [row for row in (current, artifact) if row]
    return {
        "headline": headline,
        "standfirst": "",
        "paragraphs": paragraphs,
        "supporting_records": supporting_records,
        "actors": [],
    }


def project_intent_line(project: Mapping[str, Any], prefix: str) -> str:
    """Read one named intent line from a canonical greenfield proposal."""

    needle = prefix.strip().lower()
    for raw in strings(project.get("intent")):
        head, sep, body = raw.partition(":")
        if sep and head.strip().lower() == needle:
            return sentence(body)
    return ""


def _greenfield_headline(*, first_path: str, title: str) -> str:
    path = _first_path_subject(first_path)
    if path:
        subject = _lower_first(path).strip()
        if subject.lower().startswith(("one ", "a ", "an ")):
            return f"{_capitalize_first(subject)} the team can prove"
        if subject.lower().startswith("the "):
            return f"One {subject[4:].strip()} the team can prove"
        return f"One {subject} the team can prove"
    clean_title = sentence(title, "Project").rstrip(".")
    return f"{clean_title} starts with one accepted path"


def _source_headline(
    *,
    title: str,
    project_intro: str,
    current_focus: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
) -> str:
    intro_headline = _headline_from_intro(title=title, intro=project_intro)
    if intro_headline:
        return intro_headline
    work = _workstream_names(active_workstreams=active_workstreams, backlog=backlog)
    focus = concise_text(current_focus, limit=92)
    if focus:
        return focus
    if work:
        return f"{title} is centered on {work}"
    return f"{title} has one current project story"


def _source_current_paragraph(
    *,
    title: str,
    project_intro: str,
    release_label: str,
    work_mode: str,
    current_focus: str,
    next_action_text: str,
    blockers: Sequence[tuple[str, str, str]],
) -> str:
    release = sentence(release_label, "current release")
    mode = sentence(work_mode, "current").lower()
    focus = _lower_first(concise_text(current_focus, limit=170, fallback="the current project focus is not available"))
    next_move = _lower_first(action_sentence(next_action_text).rstrip("."))
    risk = _risk_sentence(blockers)
    body = f"{title} is in {mode} mode for {release}."
    body += f" The active work is {focus}."
    if next_move:
        body += f" The next move is to {next_move.removeprefix('to ')}."
    if risk:
        body += f" {risk}"
    return body


def _headline_from_intro(*, title: str, intro: str) -> str:
    text = sentence(intro).rstrip(".")
    if not text:
        return ""
    lowered = text.casefold()
    title_lower = title.casefold()
    for marker in (" helps ", " enables ", " lets "):
        if marker.strip() not in lowered:
            continue
        before, sep, after = text.partition(marker)
        if sep and before.strip().casefold() == title_lower and after.strip():
            return short(f"How {title} {marker.strip()} {after.strip()}", limit=92)
    if lowered.startswith(f"{title_lower} turns "):
        return short(text, limit=92)
    if lowered.startswith(f"{title_lower} is "):
        return short(text, limit=92)
    return ""


def _source_artifact_paragraph(
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    atlas: Mapping[str, Any],
    evidence_sources: Sequence[str],
) -> str:
    work = _workstream_names(active_workstreams=active_workstreams, backlog=backlog)
    component_text = _component_names(components)
    diagram_text = _diagram_names(atlas)
    proof = evidence_boundary_phrase(evidence_sources)
    clauses: list[str] = []
    if work:
        clauses.append(f"Radar carries {work}")
    if component_text:
        clauses.append(f"Registry names the owned boundaries as {component_text}")
    if diagram_text:
        clauses.append(f"Atlas gives reviewers {diagram_text}")
    if proof:
        clauses.append(f"the proof boundary is {proof}")
    if not clauses:
        return "The story is still thin: source records exist, but no connected workstream, component, diagram, or proof boundary is strong enough to narrate yet."
    parts: list[str] = []
    if work:
        parts.append(f"Radar turns the active work into {work}.")
    if component_text:
        parts.append(f"Registry anchors that work in {component_text}.")
    if diagram_text:
        parts.append(f"Atlas gives reviewers {diagram_text}.")
    if proof:
        parts.append(f"Evidence stays bounded to {proof}, so the story does not outrun the source records.")
    return " ".join(parts)


def _project_purpose_clause(value: object) -> str:
    text = sentence(value).rstrip(".")
    if not text:
        return ""
    lowered = text.lower()
    for prefix in (f"{word} helps " for word in ("Odylith", "Project")):
        if lowered.startswith(prefix.lower()):
            return f"help {_lower_first(text[len(prefix) :])}"
    for marker in (" helps ", " enables ", " lets "):
        before, sep, after = text.partition(marker)
        if sep and after.strip():
            verb = {"helps": "help", "enables": "enable", "lets": "let"}[marker.strip()]
            return f"{verb} {after.strip()}"
    return _lower_first(text)


def _source_supporting_records(
    *,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    atlas: Mapping[str, Any],
    evidence_sources: Sequence[str],
) -> list[str]:
    work = _workstream_names(active_workstreams=active_workstreams, backlog=backlog)
    component_text = _component_names(components)
    diagram_text = _diagram_names(atlas)
    proof = evidence_boundary_phrase(evidence_sources)
    rows: list[str] = []
    if work:
        rows.append(f"Radar carries {work}.")
    if component_text:
        rows.append(f"Registry names the owned boundaries as {component_text}.")
    if diagram_text:
        rows.append(f"Atlas gives reviewers {diagram_text}.")
    if proof:
        rows.append(f"Evidence is bounded by {proof}.")
    return rows


def _risk_sentence(blockers: Sequence[tuple[str, str, str]]) -> str:
    if not blockers:
        return ""
    title, detail, owner = blockers[0]
    clean_title = concise_text(title, limit=95)
    if not clean_title or clean_title.lower() == "evidence gap":
        return ""
    owner_text = sentence(owner)
    detail_text = sentence(detail)
    suffix = f" from {owner_text}" if owner_text else ""
    if detail_text:
        return f"The first open risk is {clean_title}{suffix}: {detail_text}."
    return f"The first open risk is {clean_title}{suffix}."


def _workstream_names(*, active_workstreams: Sequence[str], backlog: Mapping[str, Any]) -> str:
    rows_by_id = backlog_rows_by_id(backlog)
    names: list[str] = []
    for workstream_id in active_workstreams[:3]:
        token = sentence(workstream_id)
        row = rows_by_id.get(token, {})
        title = sentence(row.get("title"), token)
        names.append(f"{token} {title}" if token and title and title != token else title or token)
    if not names:
        for row in list(backlog.get("execution", []))[:3] + list(backlog.get("queued", []))[:2]:
            if isinstance(row, Mapping):
                title = sentence(row.get("title") or row.get("idea_id"))
                if title:
                    names.append(title)
    return _join(names)


def _component_names(components: Sequence[Mapping[str, Any]]) -> str:
    names = [
        sentence(component.get("name") or component.get("label") or component.get("component_id"))
        for component in components
    ]
    return _join(_dedupe([name for name in names if name])[:4])


def _diagram_names(atlas: Mapping[str, Any]) -> str:
    active = [row for row in list_value(atlas.get("active")) if isinstance(row, Mapping)]
    rows = active or [row for row in list_value(atlas.get("diagrams")) if isinstance(row, Mapping)]
    names = [
        sentence(row.get("title") or row.get("name") or row.get("diagram_id") or row.get("slug"))
        for row in rows
    ]
    return _join(_dedupe([name for name in names if name])[:3])


def _greenfield_paragraphs(
    *,
    objective: str,
    intro: str,
    outcome: str,
    success: str,
    failure: str,
    non_goals: str,
    first_path: str,
    release: str,
    release_text: str,
    actors: Sequence[tuple[str, str, str]],
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
) -> list[str]:
    paragraphs: list[str] = []
    release_label = sentence(release, "0.0.1")
    product_line = _greenfield_product_line(objective=objective, intro=intro, outcome=outcome)
    path_subject = _first_path_subject(first_path)
    boundary = _risk_boundary(failure=failure, non_goals=non_goals)
    if not product_line and first_path:
        product_line = f"Release {release_label} starts with {_lower_first(first_path).rstrip('.')}."
    if product_line:
        paragraph = product_line
        if path_subject:
            paragraph += f" For release {release_label}, the product narrows to {path_subject}."
        if boundary:
            if boundary.startswith("the failure mode: "):
                paragraph += (
                    " It also names the failure mode before implementation turns it into a product claim: "
                    f"{boundary.removeprefix('the failure mode: ')}."
                )
            else:
                paragraph += f" It also keeps {boundary} outside the first proof until the team chooses those obligations deliberately."
        paragraphs.append(paragraph)
    first_path_clause = _first_path_clause(first_path)
    actor_line = _actor_narrative(actors)
    release_line = _story_sentence(release_text)
    if first_path_clause:
        paragraphs.append(
            f"The first slice {first_path_clause}. "
            f"{actor_line + ' ' if actor_line else ''}"
            f"{release_line or _story_sentence(success) or f'Release {release_label} proves this path before the project expands.'}"
        )
    artifact_line = _greenfield_artifact_line(workstreams=workstreams, components=components, diagrams=diagrams, release=release_label)
    if artifact_line:
        paragraphs.append(artifact_line)
    return [paragraph for paragraph in paragraphs if paragraph]


def _greenfield_product_line(*, objective: str, intro: str, outcome: str) -> str:
    promise = next(
        (
            candidate
            for candidate in (_story_sentence(outcome), _story_sentence(objective), _story_sentence(intro))
            if candidate and not _is_meta_project_line(candidate)
        ),
        "",
    )
    if not promise and intro and not _is_meta_project_line(_story_sentence(intro)):
        promise = _story_sentence(intro)
    if not promise:
        return ""
    if promise.lower().startswith("govern "):
        promise = _capitalize_first(promise[len("govern "):])
    return promise


def _is_meta_project_line(value: str) -> bool:
    text = sentence(value).casefold()
    if not text:
        return False
    meta_markers = (
        "accepted product truth",
        "accepted project truth",
        "before backlog",
        "before any generated artifact",
        "governance artifact",
        "governance records",
        "governable as one product spine",
        "project spine",
        "proposal expansion",
        "source boundary",
    )
    if any(marker in text for marker in meta_markers):
        return True
    return text.startswith(("make ", "capture ", "turn the operator request into"))


def _risk_boundary(*, failure: str, non_goals: str) -> str:
    failure_text = sentence(failure).rstrip(".")
    if failure_text:
        for marker in (" before ", " until ", " without "):
            head, sep, _tail = failure_text.partition(marker)
            if sep and head.strip():
                failure_text = head.strip()
                break
        return short(f"the failure mode: {_lower_first(failure_text)}", limit=145)
    non_goal_text = sentence(non_goals).rstrip(".")
    if non_goal_text:
        return short(f"the later scope: {_lower_first(non_goal_text)}", limit=145)
    return "the later scope: broad automation, live integrations, and irreversible decisions"


def _greenfield_artifact_line(
    *,
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
    release: str,
) -> str:
    workstream_text = _first_titles(workstreams[:2], fallback="")
    component_text = _first_titles(components[:2], fallback="")
    diagram_text = _first_titles(diagrams[:2], fallback="")
    clauses: list[str] = []
    if workstream_text:
        clauses.append(f"Radar turns the story into {workstream_text}")
    if component_text:
        clauses.append(f"Registry gives ownership to {component_text}")
    if diagram_text:
        clauses.append(f"Atlas gives reviewers {diagram_text}")
    if not clauses:
        return ""
    return f"{_join(clauses)}. Together, those records keep release {release} tied to one promise, one first path, and one proof boundary."


def _greenfield_supporting_records(
    *,
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
    release: str,
) -> list[str]:
    workstream_text = _first_titles(workstreams[:3], fallback="the first workstream sequence")
    component_text = _first_titles(components[:3], fallback="the first component boundaries")
    diagram_text = _first_titles(diagrams[:3], fallback="the first architecture views")
    release_label = sentence(release, "0.0.1")
    return [
        f"Radar carries {workstream_text}.",
        f"Registry gives ownership to {component_text}.",
        f"Atlas gives reviewers {diagram_text}.",
        f"Release {release_label} stays tied to one product promise, one first path, and one proof boundary.",
    ]


def _story_sentence(value: str) -> str:
    text = sentence(value).replace("`", "")
    text = _capitalize_first(text)
    return text if text.endswith((".", "?", "!")) else f"{text}." if text else ""


def _capitalize_first(value: str) -> str:
    return f"{value[:1].upper()}{value[1:]}" if value else value


def _lower_first(value: str) -> str:
    text = sentence(value).strip()
    return f"{text[:1].lower()}{text[1:]}" if text else ""


def _story_actor_items(actors: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {"role": sentence(role), "title": sentence(title), "body": sentence(body)}
        for role, title, body in actors[:4]
        if sentence(title)
    ]


def _actor_story(actors: Sequence[tuple[str, str, str]]) -> str:
    names = [sentence(title) for _, title, _ in actors[:4] if sentence(title)]
    if not names:
        return ""
    if len(names) == 1:
        return f"{names[0]} is the first accountable actor."
    return f"{', '.join(names[:-1])}, and {names[-1]} keep the first path accountable."


def _actor_narrative(actors: Sequence[tuple[str, str, str]]) -> str:
    rows: list[str] = []
    for _role, title, body in actors[:4]:
        actor = sentence(title)
        action = _lower_first(body).rstrip(".")
        if actor and action:
            rows.append(f"{actor} {action}")
        elif actor:
            rows.append(actor)
    if not rows:
        return ""
    if len(rows) == 1:
        return f"In this first slice, {rows[0]}."
    return f"In this first slice, {'; '.join(rows[:-1])}; and {rows[-1]}."


def _first_path_subject(value: str) -> str:
    text = sentence(value).strip().rstrip(".")
    if not text:
        return ""
    lowered = text.lower()
    for prefix in ("prove ", "validate ", "show ", "build ", "create ", "define "):
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            break
    for marker in (" from ", " through ", " with ", " before "):
        head, sep, _tail = text.partition(marker)
        if sep and 8 <= len(head) <= 96:
            return sentence(head)
    return short(text, limit=96)


def _first_path_clause(value: str) -> str:
    text = sentence(value).strip().rstrip(".")
    if not text:
        return "proves the first journey"
    lowered = text.lower()
    for verb in ("prove", "validate", "show", "build", "create", "define"):
        prefix = f"{verb} "
        if lowered.startswith(prefix):
            return f"{verb}s {text[len(prefix):]}"
    return f"follows {_lower_first(text).rstrip('.')}"


def _workstream_story_items(*, created: Mapping[str, Any], backlog: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    created_rows = [dict(row) for row in list_value(created.get("workstreams")) if isinstance(row, Mapping)]
    rows = backlog[:5] or created_rows[:5]
    items: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        created_row = created_rows[index] if index < len(created_rows) else {}
        ref = sentence(created_row.get("idea_id"))
        title = _workstream_story_title(row.get("title") or created_row.get("title"))
        body = sentence(row.get("recommended_first_slice") or row.get("product_view") or row.get("problem"))
        items.append({"ref": ref, "title": " ".join(part for part in (ref, title) if part), "body": short(body, limit=170)})
    return items


def _workstream_story_title(value: object) -> str:
    title = sentence(value, "Proposed workstream")
    if title.lower().startswith("govern "):
        return "Govern project direction"
    return title


def _component_story_items(*, created: Mapping[str, Any], components: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    created_rows = [dict(row) for row in list_value(created.get("components")) if isinstance(row, Mapping)]
    rows = components[:5] or created_rows[:5]
    items: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        created_row = created_rows[index] if index < len(created_rows) else {}
        title = sentence(row.get("label") or created_row.get("label") or row.get("component_id"), "Planned component")
        body = sentence(row.get("responsibility") or row.get("boundary") or created_row.get("path"))
        items.append({"ref": sentence(created_row.get("component_id")), "title": title, "body": short(body, limit=170)})
    return items


def _diagram_story_items(*, created: Mapping[str, Any], diagrams: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    ids = [sentence(row) for row in list_value(created.get("diagrams"))]
    rows = diagrams[:5]
    items: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        ref = ids[index] if index < len(ids) else ""
        label = sentence(row.get("title") or row.get("slug"), "Architecture view")
        body = sentence(row.get("operator_question") or row.get("proof_gate") or row.get("link_state"))
        items.append({"ref": ref, "title": " ".join(part for part in (ref, label) if part), "body": short(body, limit=170)})
    if items:
        return items
    return [{"ref": ref, "title": ref, "body": ""} for ref in ids[:5] if ref]


def _first_titles(values: Sequence[Mapping[str, str]], *, fallback: str) -> str:
    titles = [sentence(row.get("title")) for row in values[:3] if sentence(row.get("title"))]
    if not titles:
        return fallback
    return _join(titles)


def _join(values: Sequence[str]) -> str:
    rows = [sentence(value) for value in values if sentence(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _dedupe(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(value)
    return rows
