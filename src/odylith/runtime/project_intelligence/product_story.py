"""General Product Story projection for the Project tab."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.project_intelligence.focus import backlog_rows_by_id
from odylith.runtime.project_intelligence.narration import evidence_boundary_phrase
from odylith.runtime.project_intelligence.summary import action_sentence, concise_text
from odylith.runtime.project_intelligence.utils import dict_value, display_text, list_value, sentence, short, strings


def build_greenfield_product_story(
    *,
    title: str,
    intro: str,
    project: Mapping[str, Any],
    project_brief: Mapping[str, Any] | None = None,
    first_path: str,
    release: str,
    release_plan: Mapping[str, Any],
    validation: Sequence[str] = (),
    accepted: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    actors: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    """Build proposal-origin story prose from the accepted project graph."""

    brief = dict_value(project_brief)
    objective = (
        project_intent_line(project, "project objective")
        or _brief_story_line(brief.get("summary"))
        or _brief_story_line(brief.get("purpose"))
    )
    outcome = (
        project_intent_line(project, "user or stakeholder outcome")
        or _brief_story_line(brief.get("operator_value"))
        or _brief_story_line(brief.get("project_outcome"))
    )
    success = project_intent_line(project, "success condition") or _brief_story_line((validation or [""])[0])
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
        outcome=outcome,
        release=release,
        release_text=release_text,
        success=success,
        non_goals=non_goals,
        operating_principle=_brief_story_line(brief.get("operating_principle")),
        validation=validation,
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
        actors=actors,
    )
    return {
        "headline": headline,
        "standfirst": "",
        "paragraphs": paragraphs,
        "supporting_records": [],
        "release_contract": release_contract,
        "actors": _story_actor_items(actors),
    }


def build_source_product_story(
    *,
    project_title: str,
    project_intro: str,
    release_label: str,
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
    narrative = _source_narrative_paragraphs(
        title=title,
        project_intro=project_intro,
        release_label=release_label,
        current_focus=current_focus,
        active_workstreams=active_workstreams,
        backlog=backlog,
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
    paragraphs = [*narrative, *([artifact] if artifact else [])]
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


def summarize_first_path(value: object) -> str:
    """Return a compact, product-facing first-path phrase without step dumps."""

    return _first_path_summary(sentence(value))


def summarize_proof(value: object, *, first_path: str = "") -> str:
    """Return a compact proof phrase without repeating numbered first-path steps."""

    return _proof_claim(sentence(value), first_path=first_path)


def _brief_story_line(value: object) -> str:
    text = sentence(value)
    if not text:
        return ""
    return "" if _is_meta_project_line(text) else text


def _greenfield_headline(*, first_path: str, title: str, product_line: str, release: str) -> str:
    release_label = sentence(release)
    if release_label:
        return f"Release {release_label} proves one usable first path"
    return "Proves one usable first path"


def _display_title(value: object) -> str:
    text = sentence(value, "Project").rstrip(".")
    text = text.lstrip(" -–—:·|").rstrip(" -–—:·|")
    return text or "Project"


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


def _headline_from_intro(*, title: str, intro: str) -> str:
    text = sentence(intro).rstrip(".")
    if not text or _is_component_inventory_line(text):
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


def _source_narrative_paragraphs(
    *,
    title: str,
    project_intro: str,
    release_label: str,
    current_focus: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    next_action_text: str,
    blockers: Sequence[tuple[str, str, str]],
) -> list[str]:
    intro = _source_product_intro(title=title, project_intro=project_intro)
    workflow = _source_workflow_paragraph(
        release_label=release_label,
        current_focus=current_focus,
        active_workstreams=active_workstreams,
        backlog=backlog,
        next_action_text=next_action_text,
    )
    proof = _source_proof_paragraph(release_label=release_label, blockers=blockers)
    return [row for row in (intro, workflow, proof) if row]


def _source_product_intro(*, title: str, project_intro: str) -> str:
    intro = sentence(project_intro).rstrip(".")
    if intro and not _is_component_inventory_line(intro):
        return f"{intro}."
    return (
        f"{title} is a product with a source-backed governance view, but its product story still needs "
        "a clearer user, problem, workflow, and proof boundary before implementation claims move forward."
    )


def _source_workflow_paragraph(
    *,
    release_label: str,
    current_focus: str,
    active_workstreams: Sequence[str],
    backlog: Mapping[str, Any],
    next_action_text: str,
) -> str:
    release = sentence(release_label, "current release")
    workflow = _source_workflow_phrase(active_workstreams=active_workstreams, backlog=backlog)
    focus = concise_text(current_focus, limit=120)
    if _is_acceptance_headline(focus):
        focus = ""
    next_move = _lower_first(action_sentence(next_action_text).rstrip("."))
    if workflow:
        body = f"The first usable workflow for {release} is {workflow}."
    elif focus:
        body = f"The first usable workflow for {release} is the current focus: {_lower_first(focus).rstrip('.')}."
    else:
        body = f"The first usable workflow for {release} still needs to be named in source records."
    if next_move:
        body += f" The next move is to {next_move.removeprefix('to ')}."
    return body


def _source_proof_paragraph(*, release_label: str, blockers: Sequence[tuple[str, str, str]]) -> str:
    release = sentence(release_label, "current release")
    body = (
        f"Release {release} is coherent when the product workflow, owned boundaries, topology, "
        "and validation evidence agree before implementation readiness is claimed."
    )
    risk = _risk_sentence(blockers)
    if risk:
        body += f" {risk}"
    return body


def _source_workflow_phrase(*, active_workstreams: Sequence[str], backlog: Mapping[str, Any]) -> str:
    rows_by_id = backlog_rows_by_id(backlog)
    titles: list[str] = []
    for workstream_id in active_workstreams:
        token = sentence(workstream_id)
        row = rows_by_id.get(token, {})
        title = sentence(row.get("title"))
        if not title or _is_meta_record_title(title):
            continue
        titles.append(_lower_first(title).rstrip("."))
        if len(titles) >= 2:
            break
    if not titles:
        for row in list(backlog.get("execution", []))[:3] + list(backlog.get("queued", []))[:2]:
            if not isinstance(row, Mapping):
                continue
            title = sentence(row.get("title") or row.get("idea_id"))
            if not title or _is_meta_record_title(title):
                continue
            titles.append(_lower_first(title).rstrip("."))
            if len(titles) >= 2:
                break
    return _join(titles)


def _is_acceptance_headline(value: str) -> bool:
    text = sentence(value).casefold()
    return text.startswith(("greenfield proposal accepted for ", "accepted greenfield proposal for "))


def _is_component_inventory_line(value: str) -> bool:
    text = sentence(value).casefold()
    if not text:
        return False
    return (
        (" component responsible for " in text)
        or (" component that " in text and "initial evidence anchor" in text)
        or (" with `" in text and " as its initial" in text)
        or ("responsible for own " in text)
    )


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
        parts.append(f"After the product story is clear, Radar turns the active work into {work}.")
    if component_text:
        parts.append(f"Registry anchors that work in {component_text}.")
    if diagram_text:
        parts.append(f"Atlas gives reviewers {diagram_text}.")
    if proof:
        parts.append(f"Evidence stays bounded to {proof}, so the story does not outrun the source records.")
    return " ".join(parts)


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
    actors: Sequence[tuple[str, str, str]],
) -> list[str]:
    paragraphs: list[str] = []
    release_label = sentence(release, "0.0.1")
    product_line = _greenfield_product_line(objective=objective, intro=intro, outcome=outcome)
    path_story = _first_path_concrete_story(first_path)
    actor_intro = _actor_journey_intro(actors)
    if actor_intro and path_story:
        paragraphs.append(f"{actor_intro} Release {release_label} keeps the work focused: {_capitalize_first(path_story).rstrip('.')}.")
    elif product_line and path_story and not _story_contains(product_line, path_story):
        paragraphs.append(
            f"{product_line.rstrip()} Release {release_label} keeps the work focused: {_lower_first(path_story).rstrip('.')}."
        )
    elif product_line:
        paragraphs.append(product_line)
    elif path_story:
        paragraphs.append(f"This release proves the first useful path: {_lower_first(path_story).rstrip('.')}.")
    proof_sentence = _greenfield_bottom_line(
        release=release_label,
        first_path=first_path,
        success=success,
        release_text=release_text,
    )
    if proof_sentence and not any(_same_story(proof_sentence, paragraph) for paragraph in paragraphs):
        paragraphs.append(proof_sentence)
    return [paragraph for paragraph in paragraphs if paragraph]


def _greenfield_product_line(*, objective: str, intro: str, outcome: str) -> str:
    promise = next(
        (
            candidate
            for candidate in (_story_sentence(objective), _story_sentence(intro), _story_sentence(outcome))
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


def _is_compact_proof_repeat(value: str) -> bool:
    text = sentence(value).strip()
    return text.casefold().startswith("proof must show ") and len(text) <= 92


def _greenfield_release_contract(
    *,
    product_line: str,
    first_path: str,
    outcome: str,
    release: str,
    release_text: str,
    success: str,
    non_goals: str,
    operating_principle: str,
    validation: Sequence[str],
    components: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    user_problem = _contract_user_problem(product_line=product_line, first_path=first_path, outcome=outcome)
    first_path_body = _contract_first_path_body(first_path)
    boundary = _contract_product_boundary_body(non_goals=non_goals, validation=validation, success=success)
    component_names = [
        _capability_name(component.get("label") or component.get("name") or component.get("component_id"))
        for component in components
    ]
    component_text = _contract_component_list(component_names)
    proof_source = _contract_proof_candidate(validation) or _greenfield_proof_sentence(
        success=success,
        release_text=release_text,
        first_path=first_path,
    )
    proof_body = _contract_proof_body(proof_source, first_path=first_path)
    if user_problem:
        rows.append({"label": "User problem", "body": user_problem})
    if first_path_body:
        rows.append({"label": "First path", "body": first_path_body})
    if boundary:
        rows.append({"label": "Product boundary", "body": boundary})
    component_body = _contract_body(component_text)
    if component_body:
        rows.append({"label": "Owned capabilities", "body": component_body})
    if proof_body:
        rows.append({"label": "Proof", "body": proof_body})
    if not rows:
        rows.append({"label": "Release contract", "body": "One accepted path, one proof boundary, and no source-backed implementation claim until validation exists."})
    return rows[:5]


def _story_contains(container: str, contained: str) -> bool:
    left = _normalized_story_text(container)
    right = _normalized_story_text(contained)
    return bool(left and right and right in left)


def _first_path_concrete_story(value: str) -> str:
    text = _strip_first_path_preface(sentence(value).strip())
    if not text:
        return ""
    if re.search(r"\b1[.)]\s+[A-Z]", text):
        summary = _first_path_summary(text)
        return _story_excerpt(summary, limit=220).rstrip(".") if summary else ""
    sentences = _story_sentences(text)
    concrete = [
        row
        for row in sentences
        if not re.search(r"\b(first complete path|first path|product must prove|release .*proves)\b", row, flags=re.IGNORECASE)
    ]
    chosen = " ".join(concrete[:2]).strip() or _first_path_summary(text)
    chosen = _strip_numbered_steps(chosen)
    return _story_excerpt(chosen, limit=320).rstrip(".") if chosen else ""


def _greenfield_bottom_line(*, release: str, first_path: str, success: str, release_text: str) -> str:
    path = _first_path_concrete_story(first_path)
    if path:
        return (
            f"Bottom line: release {sentence(release, '0.0.1')} succeeds when the first path produces its user-visible result "
            "and leaves enough evidence for review."
        )
    proof = _greenfield_proof_sentence(success=success, release_text=release_text, first_path=first_path)
    proof = _contract_proof_body(proof, first_path=first_path)
    if proof:
        return f"Bottom line: release {sentence(release, '0.0.1')} succeeds when {proof[0].lower() + proof[1:] if proof else proof}"
    return f"Bottom line: release {sentence(release, '0.0.1')} succeeds when the accepted path runs end to end and can be reviewed."


def _contract_user_problem(*, product_line: str, first_path: str, outcome: str) -> str:
    text = _story_sentence(product_line).rstrip(".")
    if text and not _is_meta_project_line(text):
        sentences = _story_sentences(text)
        if sentences:
            markers = ("need", "fail", "stuck", "without", "cannot", "can't", "hard", "expensive", "unsafe", "problem")
            for pool in (sentences[1:], sentences):
                for row in pool:
                    if any(marker in row.casefold() for marker in markers):
                        return _story_excerpt(row, limit=230)
            return _story_excerpt(sentences[0], limit=230)
        return _story_excerpt(text, limit=230)
    outcome_text = _story_sentence(outcome).rstrip(".")
    if outcome_text and not _is_meta_project_line(outcome_text):
        return _story_excerpt(outcome_text, limit=230)
    path = _first_path_concrete_story(first_path)
    if path:
        return _story_excerpt(f"The first useful user problem is visible through this path: {path}", limit=190)
    return ""


def _actor_journey_intro(actors: Sequence[tuple[str, str, str]]) -> str:
    for _role, title, body in actors:
        actor = display_text(title).rstrip(".")
        detail = display_text(body).rstrip(".")
        if not actor:
            continue
        subject = actor if re.match(r"^(?:a|an|the)\b", actor, flags=re.IGNORECASE) else f"The {_lower_first(actor).rstrip('.')}"
        if detail.casefold().startswith("who "):
            detail = detail[4:].strip()
        if detail:
            return _story_excerpt(f"{subject} {_lower_first(detail).rstrip('.')}.", limit=190)
        return _story_excerpt(f"{subject} has one concrete first journey to complete.", limit=190)
    return ""


def _contract_first_path_body(first_path: str) -> str:
    concrete = _first_path_concrete_story(first_path)
    if concrete:
        return _story_excerpt(concrete, limit=230)
    return _contract_path_body(first_path)


def _contract_product_boundary_body(*, non_goals: str, validation: Sequence[str], success: str) -> str:
    excluded = _contract_body(non_goals)
    if excluded:
        return excluded
    for candidate in [*validation, success]:
        text = sentence(candidate)
        if not text:
            continue
        for marker in ("must not claim", "does not claim", "does not include", "no "):
            index = text.casefold().find(marker)
            if index >= 0:
                boundary = text[index:]
                boundary = re.sub(r"^must not claim\s+", "This release does not claim ", boundary, flags=re.IGNORECASE)
                return _story_excerpt(boundary, limit=190)
    return "This release supports only the accepted first path; broader variants stay outside until their own proof exists."


def _capability_name(value: object) -> str:
    text = _display_name(value).strip()
    text = re.sub(r"\s+Service$", "", text)
    return text


def _contract_body(value: str) -> str:
    text = _story_sentence(value).rstrip(".")
    if not text or _is_meta_project_line(text):
        return ""
    return _story_excerpt(text, limit=150)


def _contract_path_body(value: str) -> str:
    text = _first_path_subject(value) or _first_path_summary(value) or _story_sentence(value).rstrip(".")
    if not text or _is_meta_project_line(text):
        return ""
    return _story_excerpt(text, limit=150)


def _contract_component_list(values: Sequence[str], *, limit: int = 3) -> str:
    rows = [sentence(value).rstrip(".") for value in values if sentence(value)]
    if not rows:
        return ""
    selected = rows[:limit]
    body = _join(selected)
    overflow = len(rows) - len(selected)
    if overflow > 0:
        body = f"{body}, plus {overflow} more"
    return body


def _contract_proof_body(value: str, *, first_path: str = "") -> str:
    text = sentence(value).strip()
    text = _strip_numbered_steps(text)
    text = _strip_proof_preface(text)
    if _contract_path_echo(text):
        return (
            "Proof must show the accepted path works on representative input, records the user-visible result, "
            "and exposes the evidence, non-goals, and release decision for review."
        )
    if first_path and _same_story(text, first_path):
        return (
            "Proof must show the accepted path works on representative input, records the user-visible result, "
            "and exposes the evidence, non-goals, and release decision for review."
        )
    head, sep, _tail = text.partition(":")
    if sep and len(head) >= 42:
        return head.rstrip(".") + "."
    return _story_excerpt(_story_sentence(text).rstrip("."), limit=320)


def _contract_proof_candidate(validation: Sequence[str]) -> str:
    rows = [_strip_proof_preface(_story_sentence(candidate).rstrip(".")) for candidate in validation]
    for tokens in (
        ("release proof", "proof boundary", "evidence means"),
        ("evidence", "source", "non-goal", "verified", "reviewer-visible"),
    ):
        for text in rows:
            if not text or _is_meta_project_line(text) or _contract_path_echo(text):
                continue
            lowered = text.casefold()
            if any(token in lowered for token in tokens):
                return text
    return ""


def _strip_proof_preface(value: str) -> str:
    text = sentence(value).strip()
    evidence_rewrite = re.sub(r"^evidence means\s+", "Evidence must show ", text, count=1, flags=re.IGNORECASE).strip()
    if evidence_rewrite != text:
        return _capitalize_first(evidence_rewrite)
    patterns = (
        r"^the release proof matches the accepted proof boundary\s*:\s*",
        r"^release proof matches the accepted proof boundary\s*:\s*",
        r"^proof boundary\s*:\s*",
        r"^proof required\s*:\s*",
        r"^proof must show\s*:\s*",
    )
    for pattern in patterns:
        rewritten = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if rewritten != text:
            return _capitalize_first(rewritten)
    return text


def _contract_path_echo(value: str) -> bool:
    text = sentence(value).casefold()
    return "first path" in text or "first complete path" in text or "passes end to end" in text


def _story_excerpt(value: str, *, limit: int) -> str:
    text = sentence(value).strip()
    if len(text) <= limit:
        return _clean_excerpt_tail(text.rstrip(".") + ".")
    sentences = _story_sentences(text)
    selected: list[str] = []
    total = 0
    for row in sentences:
        row_len = len(row) + (1 if selected else 0)
        if selected and total + row_len > limit:
            break
        if not selected and len(row) > limit:
            break
        selected.append(row)
        total += row_len
    if selected:
        return _clean_excerpt_tail(" ".join(selected).rstrip(".") + ".")
    words: list[str] = []
    total = 0
    for word in text.split():
        next_total = total + len(word) + (1 if words else 0)
        if next_total > limit:
            break
        words.append(word)
        total = next_total
    while words and words[-1].casefold().strip(".,;:") in {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        words.pop()
    return _clean_excerpt_tail((" ".join(words).rstrip(" ,;:") or text[:limit].rstrip(" ,;:")).rstrip(".") + ".")


def _clean_excerpt_tail(value: str) -> str:
    text = re.sub(r"(?::\s*)?\b\d+\.$", ".", sentence(value).strip())
    text = re.sub(
        r"\b(?:a|an|and|as|at|by|before|for|from|in|inside|of|on|or|outside|the|to|until|with|without)\.$",
        ".",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+\.", ".", text)
    return text


def _display_name(value: object) -> str:
    text = sentence(value).strip()
    minor_words = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    tokens: list[str] = []
    raw_tokens = text.split()
    for index, token in enumerate(raw_tokens):
        stripped = token.strip(".,;:!?()[]{}")
        if (
            index > 0
            and stripped.casefold() in minor_words
            and not raw_tokens[index - 1].endswith(":")
            and not _has_internal_capital(stripped)
        ):
            tokens.append(token.replace(stripped, stripped.casefold()))
        else:
            tokens.append(token)
    return " ".join(tokens)


def _has_internal_capital(value: str) -> bool:
    return any(char.islower() for char in value) and any(char.isupper() for char in value[1:])


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
    if text.startswith("make ") and any(
        marker in text
        for marker in (
            "readable and governable",
            "before any generated artifact",
            "governable as one product spine",
            "source boundary",
        )
    ):
        return True
    return text.startswith(("capture ", "turn the operator request into"))


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
    if excluded:
        return (
            f"Release {release} deliberately excludes {excluded}. "
            "Those items stay out until the accepted scenario has reviewer-visible proof."
        )
    boundary = _risk_boundary(failure=failure, non_goals=non_goals)
    if boundary.startswith("the failure mode: "):
        return (
            "The first release names the failure mode before implementation turns it into a product claim: "
            f"{boundary.removeprefix('the failure mode: ')}."
        )
    return (
        f"Release {release} keeps broader automation, live integrations, and irreversible decisions outside the first slice "
        "until reviewer-visible proof exists."
    )


def _greenfield_proof_sentence(*, success: str, release_text: str, first_path: str) -> str:
    proof = next(
        (
            _proof_claim(_story_sentence(candidate).rstrip("."), first_path=first_path)
            for candidate in (success, release_text)
            if _story_sentence(candidate) and not _is_meta_project_line(_story_sentence(candidate))
        ),
        "",
    )
    if proof:
        if _normalized_story_text(proof) == _normalized_story_text(first_path):
            return "Proof must show the first path happened, stayed inside its accepted boundary, and left reviewer-visible evidence."
        if proof.casefold().startswith("proof must show "):
            return proof.rstrip(".") + "."
        if proof.casefold().startswith(("promote ", "release ", "only ")):
            return f"{proof}."
        return f"Proof must show {proof[0].lower() + proof[1:] if proof else proof}."
    path = _story_subject(first_path)
    if path:
        return f"Proof must show that {_lower_first(path).rstrip('.')} happened inside the accepted boundary and left reviewer-visible evidence."
    return "Proof must show the first path happened, stayed inside its accepted boundary, and left reviewer-visible evidence."


def _normalized_story_text(value: str) -> str:
    return " ".join(sentence(value).casefold().strip(" .").split())


def _same_story(left: str, right: str) -> bool:
    return bool(left and right and _normalized_story_text(left) == _normalized_story_text(right))


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
    text = display_text(value)
    text = _capitalize_first(text)
    return text if text.endswith((".", "?", "!")) else f"{text}." if text else ""


def _capitalize_first(value: str) -> str:
    return f"{value[:1].upper()}{value[1:]}" if value else value


def _lower_first(value: str) -> str:
    text = sentence(value).strip()
    return f"{text[:1].lower()}{text[1:]}" if text else ""


def _story_actor_items(actors: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {"role": display_text(role), "title": display_text(title), "body": display_text(body)}
        for role, title, body in actors[:4]
        if display_text(title)
    ]


def _first_path_subject(value: str) -> str:
    text = _first_path_summary(value).rstrip(".")
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


def _story_subject(value: str) -> str:
    text = _first_path_subject(value)
    if not text or _is_meta_project_line(text):
        return ""
    return text


def _first_path_summary(value: str) -> str:
    text = _strip_numbered_steps(_story_sentence(value)).strip()
    text = re.sub(r"\s*:\s*\.$", ".", text).strip()
    text = re.sub(r"\bflow\s*:\s*(?:\.)?$", "flow.", text, flags=re.IGNORECASE).strip()
    text = _strip_first_path_preface(text)
    return text if text.endswith((".", "?", "!")) else f"{text}." if text else ""


def _strip_numbered_steps(value: str) -> str:
    text = sentence(value).strip()
    if not text:
        return ""
    text = re.split(r"\s+\d+[.)]\s+(?=[A-Z])", text, maxsplit=1)[0].strip()
    text = re.sub(r"(?::\s*)?\b\d+[.)]\s*$", "", text).strip()
    text = re.sub(r"\s*:\s*$", "", text).strip()
    return text if text.endswith((".", "?", "!")) else f"{text}." if text else ""


def _strip_first_path_preface(value: str) -> str:
    text = sentence(value).strip()
    patterns = (
        r"^the first complete path to prove should be\s*:?\s+",
        r"^first complete path to prove should be\s*:?\s+",
        r"^the first complete path should prove\s*:?\s+",
        r"^first complete path should prove\s*:?\s+",
        r"^the first complete path to prove is\s+",
        r"^first complete path to prove is\s+",
        r"^the first complete path is\s+",
        r"^first complete path is\s+",
        r"^the first path is\s+",
        r"^first path is\s+",
        r"^the first complete path (?:the product|this product|the system|release [^ ]+)?\s*must prove is\s+",
        r"^first complete path (?:the product|this product|the system|release [^ ]+)?\s*must prove is\s+",
        r"^the first path (?:the product|this product|the system|release [^ ]+)?\s*must prove is\s+",
        r"^first path (?:the product|this product|the system|release [^ ]+)?\s*must prove is\s+",
        r"^the first usable capability is this path:\s+",
        r"^first path:\s+",
    )
    for pattern in patterns:
        rewritten = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if rewritten != text:
            return _capitalize_first(rewritten)
    return text


def _story_sentences(value: str) -> list[str]:
    text = sentence(value).strip()
    if not text:
        return []
    return [
        row.strip()
        for row in re.split(r"(?<=[.!?])\s+(?=(?!\d+[.)]\s)[A-Z0-9])", text)
        if row.strip()
    ]


def _proof_claim(value: str, *, first_path: str) -> str:
    text = _strip_numbered_steps(value).rstrip(".")
    head, sep, tail = text.partition(":")
    if sep and len(head) >= 36:
        tail_text = sentence(tail)
        if re.search(r"\b\d+[.)]\s+[A-Z]", tail) or _same_story(tail_text, first_path) or "first path" in head.casefold():
            text = head
    if _same_story(text, first_path):
        return "the first path happened, stayed inside its accepted boundary, and left reviewer-visible evidence"
    if len(text) > 180:
        text = _story_excerpt(text, limit=170).rstrip(".")
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
