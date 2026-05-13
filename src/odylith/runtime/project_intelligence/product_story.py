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
    product_line = _greenfield_product_line(objective=objective, intro=intro, outcome=outcome)
    headline = _greenfield_headline(
        first_path=first_path,
        title=title,
        product_line=product_line,
        release=release,
    )
    release_contract = _greenfield_release_contract(
        product_line=product_line,
        first_path=first_path,
        release=release,
        release_text=release_text,
        success=success,
        non_goals=non_goals,
        components=components,
    )
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
        "release_contract": release_contract,
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


def _greenfield_headline(*, first_path: str, title: str, product_line: str, release: str) -> str:
    release_label = sentence(release)
    release_prefix = f"Release {release_label}: " if release_label else ""
    path = _story_subject(first_path)
    if path:
        subject = _lower_first(path).strip()
        if subject.startswith(("one ", "a ", "an ")):
            return short(f"{release_prefix}prove {subject} before expanding the product", limit=120)
        return short(f"{release_prefix}prove {subject} before expanding the product", limit=120)
    promise = sentence(product_line).rstrip(".")
    if promise and not _is_meta_project_line(promise):
        return short(f"{release_prefix}{promise}", limit=120)
    clean_title = sentence(title, "Project").rstrip(".")
    suffix = f" release {release_label}" if release_label else " first release"
    return short(f"{clean_title}{suffix} starts with one provable path", limit=120)


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
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
) -> list[str]:
    paragraphs: list[str] = []
    release_label = sentence(release, "0.0.1")
    product_line = _greenfield_product_line(objective=objective, intro=intro, outcome=outcome)
    path_subject = _story_subject(first_path)
    if not product_line and first_path:
        product_line = f"Release {release_label} starts with {_lower_first(_story_sentence(first_path)).rstrip('.')}."
    if product_line:
        paragraph = product_line
        if path_subject:
            paragraph += f" Release {release_label} narrows that promise to {_lower_first(path_subject).rstrip('.')}."
        paragraphs.append(paragraph)
    first_path_clause = _first_path_clause(first_path)
    if first_path_clause:
        paragraphs.append(
            f"The first path {first_path_clause}. "
            f"{_greenfield_proof_sentence(success=success, release_text=release_text, first_path=first_path)}"
        )
    deferred = _deferred_scope_sentence(non_goals=non_goals, failure=failure, release=release_label, subject=path_subject)
    if deferred:
        paragraphs.append(deferred)
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


def _greenfield_release_contract(
    *,
    product_line: str,
    first_path: str,
    release: str,
    release_text: str,
    success: str,
    non_goals: str,
    components: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    release_label = sentence(release, "0.0.1")
    rows: list[dict[str, str]] = []
    user_value = _contract_body(product_line)
    first_path_body = _contract_body(first_path)
    proof = _greenfield_proof_sentence(success=success, release_text=release_text, first_path=first_path)
    component_text = _join(
        [
            sentence(component.get("label") or component.get("name") or component.get("component_id"))
            for component in components[:4]
        ]
    )
    excluded = _contract_body(non_goals)
    if user_value:
        rows.append({"label": "User value", "body": user_value})
    if first_path_body:
        rows.append({"label": "Core loop", "body": first_path_body})
    if component_text:
        rows.append({"label": "Owned pieces", "body": component_text})
    if proof:
        rows.append({"label": "Proof", "body": proof})
    if excluded:
        rows.append({"label": "Excluded for now", "body": excluded})
    if not rows:
        rows.append({"label": f"Release {release_label} contract", "body": "One accepted path, one proof boundary, and no source-backed implementation claim until validation exists."})
    return rows[:5]


def _contract_body(value: str) -> str:
    text = _story_sentence(value).rstrip(".")
    if not text or _is_meta_project_line(text):
        return ""
    return short(text, limit=190)


def _is_meta_project_line(value: str) -> bool:
    text = sentence(value).casefold()
    if not text:
        return False
    meta_markers = (
        "accept or revise",
        "accept the",
        "accepted product truth",
        "accepted project truth",
        "before backlog",
        "before any generated artifact",
        "before implementation planning",
        "component boundaries",
        "coding-readiness",
        "governance artifact",
        "governance records",
        "governable as one product spine",
        "implementation planning",
        "proof gates",
        "project spine",
        "project shape",
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


def _deferred_scope_sentence(*, non_goals: str, failure: str, release: str, subject: str) -> str:
    excluded = _contract_body(non_goals)
    reason_subject = _lower_first(subject).rstrip(".") if subject else "one bounded first path"
    if excluded:
        return (
            f"Release {release} deliberately excludes {excluded}. "
            f"Those items stay out because the product must prove {reason_subject} before scope expands."
        )
    boundary = _risk_boundary(failure=failure, non_goals=non_goals)
    if boundary.startswith("the failure mode: "):
        return (
            "The first release names the failure mode before implementation turns it into a product claim: "
            f"{boundary.removeprefix('the failure mode: ')}."
        )
    return (
        f"Release {release} keeps broader automation, live integrations, and irreversible decisions outside the first slice "
        f"until the product proves {reason_subject}."
    )


def _greenfield_proof_sentence(*, success: str, release_text: str, first_path: str) -> str:
    proof = next(
        (
            _story_sentence(candidate).rstrip(".")
            for candidate in (success, release_text)
            if _story_sentence(candidate) and not _is_meta_project_line(_story_sentence(candidate))
        ),
        "",
    )
    if proof:
        if proof.casefold().startswith(("promote ", "release ", "only ")):
            return f"{proof}."
        return f"Proof must show {proof[0].lower() + proof[1:] if proof else proof}."
    path = _story_subject(first_path)
    if path:
        return f"Proof must show that {_lower_first(path).rstrip('.')} happened inside the accepted boundary and left reviewer-visible evidence."
    return "Proof must show the first path happened, stayed inside its accepted boundary, and left reviewer-visible evidence."


def _greenfield_artifact_line(
    *,
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
    release: str,
) -> str:
    workstream_text = _first_product_titles(workstreams, fallback="")
    component_text = _first_titles(components[:2], fallback="")
    diagram_text = _first_titles(diagrams[:2], fallback="")
    clauses: list[str] = []
    if workstream_text:
        clauses.append(f"Radar carries the backlog and proof work in {workstream_text}")
    if component_text:
        clauses.append(f"Registry assigns ownership to {component_text}")
    if diagram_text:
        clauses.append(f"Atlas gives reviewers {diagram_text}")
    if not clauses:
        return ""
    return f"After the product path is clear, Odylith decomposes it into governed work: {_join(clauses)}. Together, those records keep release {release} tied to one product promise, one first path, and one proof boundary."


def _greenfield_supporting_records(
    *,
    workstreams: Sequence[Mapping[str, str]],
    components: Sequence[Mapping[str, str]],
    diagrams: Sequence[Mapping[str, str]],
    release: str,
) -> list[str]:
    workstream_text = _first_product_titles(workstreams, fallback="the first workstream sequence", limit=3)
    component_text = _first_titles(components[:3], fallback="the first component boundaries")
    diagram_text = _first_titles(diagrams[:3], fallback="the first architecture views")
    release_label = sentence(release, "0.0.1")
    return [
        f"Radar: {workstream_text}.",
        f"Registry: {component_text}.",
        f"Atlas: {diagram_text}.",
        f"Proof: release {release_label} stays tied to one product promise, one first path, and one evidence boundary.",
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


def _first_path_subject(value: str) -> str:
    text = sentence(value).strip().rstrip(".")
    if not text:
        return ""
    lowered = text.lower()
    if _is_meta_project_line(text):
        return ""
    for prefix in ("prove ", "validate ", "show ", "build ", "create ", "define ", "accept ", "guide ", "shape "):
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            break
    if _is_meta_project_line(text):
        return ""
    for marker in (" from ", " through ", " with ", " before "):
        head, sep, _tail = text.partition(marker)
        if sep and 8 <= len(head) <= 96:
            return sentence(head)
    return short(text, limit=96)


def _first_path_clause(value: str) -> str:
    text = sentence(value).strip().rstrip(".")
    if not text:
        return "proves the first journey"
    if _is_meta_project_line(text):
        return "proves the first usable product path"
    lowered = text.lower()
    for verb in ("prove", "validate", "show", "build", "create", "define"):
        prefix = f"{verb} "
        if lowered.startswith(prefix):
            return f"{verb}s {text[len(prefix):]}"
    return f"moves through {_lower_first(text).rstrip('.')}"


def _story_subject(value: str) -> str:
    text = _first_path_subject(value)
    if not text or _is_meta_project_line(text):
        return ""
    return text


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


def _first_product_titles(values: Sequence[Mapping[str, str]], *, fallback: str, limit: int = 2) -> str:
    titles = [
        title
        for row in values
        if (title := sentence(row.get("title"))) and not _is_meta_record_title(title)
    ][:limit]
    if not titles:
        titles = [sentence(row.get("title")) for row in values[:limit] if sentence(row.get("title"))]
    if not titles:
        return fallback
    return _join(titles)


def _is_meta_record_title(value: str) -> bool:
    text = sentence(value).casefold()
    return text.startswith(("govern project direction", "guide ", "shape ")) or any(
        marker in text
        for marker in (
            "project spine",
            "project direction",
            "project shape",
            "program boundary",
        )
    )


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
