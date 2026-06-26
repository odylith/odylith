"""General Product Story projection for the Project tab."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.project_intelligence.focus import backlog_rows_by_id
from odylith.runtime.project_intelligence.narration import evidence_boundary_phrase
from odylith.runtime.project_intelligence.product_story_cards import build_greenfield_story_cards
from odylith.runtime.project_intelligence.summary import action_sentence, concise_text
from odylith.runtime.project_intelligence.utils import (
    dict_value,
    display_text,
    list_value,
    sanitize_actor_body,
    sentence,
    short,
    strings,
)


def build_greenfield_product_story(
    *,
    title: str,
    intro: str,
    intent: Mapping[str, Any] | None = None,
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
    accepted_intent = dict_value(intent)
    objective = (
        _brief_story_line(accepted_intent.get("product_story"))
        or _brief_story_line(accepted_intent.get("problem"))
        or project_intent_line(project, "project objective")
        or _brief_story_line(brief.get("summary"))
        or _brief_story_line(brief.get("purpose"))
    )
    outcome = (
        project_intent_line(project, "user or stakeholder outcome")
        or _brief_story_line(brief.get("operator_value"))
        or _brief_story_line(brief.get("project_outcome"))
    )
    headline = _greenfield_headline(title=title)
    paragraphs = _greenfield_change_story_paragraphs(
        title=title,
        intent=accepted_intent,
        objective=objective,
        intro=intro,
        outcome=outcome,
        first_path=first_path,
        actors=actors,
    )
    release_contract = (
        build_greenfield_story_cards(
            title=title,
            intent=accepted_intent,
            project=project,
            objective=objective,
            outcome=outcome,
            first_path=first_path,
            actors=actors,
            validation=validation,
        )
        if accepted
        else []
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


def _greenfield_headline(*, title: str) -> str:
    return _display_title(title)


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


def _greenfield_change_story_paragraphs(
    *,
    title: str,
    intent: Mapping[str, Any],
    objective: str,
    intro: str,
    outcome: str,
    first_path: str,
    actors: Sequence[tuple[str, str, str]],
) -> list[str]:
    """Narrate the product change before any governance decomposition."""

    why = _why_someone_uses_product(
        title=title,
        story=sentence(intent.get("product_story")) or objective or intro,
        outcome=outcome,
    )
    happens = _what_happens_when_used(first_path=first_path, fallback=outcome or objective)
    ecosystem = _surrounding_ecosystem_paragraph(
        actors=actors,
        story=sentence(intent.get("product_story")),
        outcome=outcome,
        fallback=sentence(intent.get("proof_boundary")) or sentence(intent.get("state_object")),
    )
    rows = [row for row in (why, happens, ecosystem) if row]
    return _dedupe_story_paragraphs(rows)[:3]


def _why_someone_uses_product(*, title: str, story: str, outcome: str) -> str:
    source = _story_sentence(story).rstrip(".")
    if source and not _is_meta_project_line(source):
        sentences = _story_sentences(source)
        return _ensure_period(_story_excerpt(sentences[0] if sentences else source, limit=420))
    outcome_text = _story_sentence(outcome).rstrip(".")
    if outcome_text and not _is_meta_project_line(outcome_text):
        return _ensure_period(_story_excerpt(outcome_text, limit=360))
    return (
        f"{_display_title(title)} exists because the people using it need one understandable way "
        "to move from scattered input to a trusted outcome."
    )


def _what_happens_when_used(*, first_path: str, fallback: str) -> str:
    path = _first_path_concrete_story(first_path) or _story_sentence(fallback).rstrip(".")
    path = _remove_trivial_opening(path)
    if not path:
        return ""
    if re.match(r"^user\s+", path, flags=re.IGNORECASE):
        path = f"the {path[:1].lower()}{path[1:]}"
    path = _capitalize_sentence_starts(_lower_first(path).rstrip("."))
    return _ensure_period(f"When someone uses it, {path}")


def _surrounding_ecosystem_paragraph(
    *,
    actors: Sequence[tuple[str, str, str]],
    story: str,
    outcome: str,
    fallback: str,
) -> str:
    story_tail = _story_tail_for_ecosystem(story)
    clauses = _participant_clauses(actors)
    if story_tail:
        extra = [clause for clause in clauses if not _story_mentions_actor(story_tail, clause)]
        if extra:
            return _ensure_period(f"{story_tail.rstrip('.')}. {extra[0].rstrip('.')}")
        return _ensure_period(story_tail)
    if clauses:
        return _ensure_period(f"After the first result is produced, {_join(clauses[:3])}")
    outcome_text = _story_sentence(outcome).rstrip(".")
    if outcome_text and not _is_meta_project_line(outcome_text):
        return _ensure_period(f"The outcome gives the surrounding participants something concrete to review, trust, or act on: {_lower_first(outcome_text)}")
    fallback_text = _story_sentence(fallback).rstrip(".")
    if fallback_text and not _is_meta_project_line(fallback_text):
        return _ensure_period(f"The surrounding participants use that outcome with the context needed to review it: {_lower_first(fallback_text)}")
    return "The surrounding participants use the resulting record to review what happened, decide the next step, and keep follow-up grounded in the same product outcome."


def _story_tail_for_ecosystem(value: str) -> str:
    sentences = _story_sentences(_story_sentence(value))
    if len(sentences) < 3:
        return ""
    tail = " ".join(sentences[2:]).strip()
    return _story_excerpt(tail, limit=420).rstrip(".") if tail else ""


def _story_mentions_actor(story: str, clause: str) -> bool:
    title = sentence(clause).split(" ", 3)[:2]
    key = " ".join(title).casefold().strip(" .")
    return bool(key and key in sentence(story).casefold())


def _participant_clauses(actors: Sequence[tuple[str, str, str]]) -> list[str]:
    clauses: list[str] = []
    for index, (_role, title, body) in enumerate(actors):
        clean_title = _actor_story_title(title)
        clean_body = _actor_story_detail(body).rstrip(".")
        if not clean_title and not clean_body:
            continue
        if index == 0 and len(actors) > 1:
            continue
        body_lower = clean_body.casefold()
        if "starts the accepted path" in body_lower:
            continue
        if "handles the accepted-path step" in body_lower or "handles the accepted path step" in body_lower:
            clean_body = ""
        clean_body = re.sub(r"\bthe accepted[- ]path\b", "that workflow", clean_body, flags=re.IGNORECASE)
        clean_body = re.sub(r"\baccepted[- ]path\b", "reviewed", clean_body, flags=re.IGNORECASE)
        if re.match(r"^[A-Za-z][A-Za-z-]*ing\b", clean_body):
            clean_body = f"supports by {clean_body}"
        if clean_title and clean_body:
            clauses.append(f"{clean_title} {_lower_first(clean_body)}")
        elif clean_body:
            clauses.append(_lower_first(clean_body))
        elif clean_title:
            clauses.append(f"{clean_title} participates in the reviewed outcome")
        if len(clauses) >= 3:
            break
    return _dedupe(clauses)


def _actor_story_title(value: object) -> str:
    title = display_text(value).strip(" .")
    title = re.sub(r"\s+", " ", title)
    if not title:
        return ""
    title = re.split(r"\b(?:who|that|with|for|and)\b", title, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .,:;")
    if re.search(r"\bproof\s+reviewer\b", title, flags=re.IGNORECASE):
        return "Reviewer"
    tokens = title.split()
    for index, token in enumerate(tokens[1:], start=1):
        if token.strip("()[]{}.,:;").casefold().endswith("ing"):
            title = " ".join(tokens[:index]).strip(" .,:;")
            break
    words = title.split()
    if len(title) > 64 or len(words) > 6 or title.count(",") >= 1:
        return ""
    return title[:1].upper() + title[1:] if title else ""


def _remove_trivial_opening(value: str) -> str:
    text = sentence(value).strip(" .")
    if not text:
        return ""
    text = re.sub(
        r"^((?:A|An|The|One)\s+[^,.;]{1,90}?)\s+opens\s+[^,.;]+,\s*",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def _ensure_period(value: str) -> str:
    text = sentence(value).strip()
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _dedupe_story_paragraphs(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        text = _ensure_period(value)
        if text and not any(_same_story(text, existing) for existing in rows):
            rows.append(text)
    return rows


def _story_contains(container: str, contained: str) -> bool:
    left = _normalized_story_text(container)
    right = _normalized_story_text(contained)
    return bool(left and right and right in left)


def _first_path_concrete_story(value: str) -> str:
    text = _strip_first_path_preface(sentence(value).strip())
    if not text:
        return ""
    model = first_path_model(text)
    if model.steps:
        rows: list[str] = []
        for step in model.steps:
            clean = sentence(step).strip(" .")
            if not clean:
                continue
            clean = _clean_opening_launcher_step(clean)
            if not clean:
                continue
            rows.append(_subjectify_path_step(clean))
            if len(rows) >= 4:
                break
        if rows:
            return _story_excerpt(". ".join(rows), limit=640).rstrip(".")
    if re.search(r"\b1[.)]\s+[A-Z]", text):
        numbered = _numbered_path_story(text)
        if numbered:
            return _story_excerpt(numbered, limit=320).rstrip(".")
        summary = _first_path_summary(text)
        return _story_excerpt(summary, limit=220).rstrip(".") if summary else ""
    sentences = _story_sentences(text)
    concrete = [
        row
        for row in sentences
        if not re.search(r"\b(first complete path|first path|product must prove|release .*proves)\b", row, flags=re.IGNORECASE)
    ]
    chosen = " ".join(concrete[:4]).strip() or _first_path_summary(text)
    chosen = _strip_numbered_steps(chosen)
    return _story_excerpt(chosen, limit=640).rstrip(".") if chosen else ""


def _subjectify_path_step(value: str) -> str:
    text = sentence(value).strip(" .")
    if not text:
        return ""
    text = _normalize_embedded_action_verbs(text)
    subject_action = re.match(
        r"^(?P<subject>(?:the\s+)?(?:user|person|customer|actor|operator|participant|owner|requester|applicant|performer))\s+"
        r"(?P<verb>add|adds|answer|answers|capture|captures|choose|chooses|click|clicks|dismiss|dismisses|enter|enters|log|logs|play|plays|record|records|save|saves|select|selects|submit|submits|tap|taps)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if subject_action:
        subject = subject_action.group("subject")
        verb = third_person_action_verb(subject_action.group("verb"))
        tail = _third_person_compound_tail(subject_action.group("tail"))
        return f"{_lower_first(subject)} {verb}{tail}".strip()
    adverb_action = re.match(
        r"^(?P<prefix>immediately|later|then)\s+(?P<verb>receive|receives|see|sees|view|views|read|reads|get|gets)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if adverb_action:
        prefix = adverb_action.group("prefix").casefold()
        verb = third_person_action_verb(adverb_action.group("verb"))
        return f"the user {prefix} {verb}{adverb_action.group('tail')}".strip()
    product_action = re.match(
        r"^(?P<verb>compare|compares|mark|marks|prompt|prompts|return|returns|show|shows|surface|surfaces|update|updates)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if product_action:
        verb = third_person_action_verb(product_action.group("verb"))
        return f"the product {verb}{product_action.group('tail')}".strip()
    action = re.match(
        r"^(?P<prefix>manually\s+)?(?P<verb>add|adds|answer|answers|capture|captures|choose|chooses|click|clicks|dismiss|dismisses|enter|enters|log|logs|record|records|save|saves|select|selects|submit|submits|tap|taps)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if action:
        prefix = action.group("prefix") or ""
        verb = third_person_action_verb(action.group("verb"))
        tail = _third_person_compound_tail(action.group("tail"))
        return f"the user {prefix}{verb}{tail}".strip()
    return text


def _clean_opening_launcher_step(value: str) -> str:
    text = sentence(value).strip(" .")
    actor_open_then = re.sub(
        r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant|owner|requester|applicant|performer))\s+opens\s+[^,.;]+?\s+and\s+(.+)$",
        r"\1 \2",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if actor_open_then != text:
        text = actor_open_then
    else:
        text = re.sub(
            r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant|owner|requester|applicant|performer))\s+opens\s+[^,.;]+$",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    text = re.sub(r"^((?:the\s+)?product|(?:the\s+)?system|(?:the\s+)?app)\s+opens\s+[^,.;]+(?:\s+and\s+)?", "", text, count=1, flags=re.IGNORECASE)
    if re.match(r"^user\s+", text, flags=re.IGNORECASE):
        text = f"the {text[:1].lower()}{text[1:]}"
    return sentence(text).strip(" .")


def _normalize_embedded_action_verbs(value: str) -> str:
    return re.sub(
        r",\s+and\s+(manually\s+)?(answers?|logs?|enters?|selects?|submits?|saves?|chooses?|clicks?|accepts?|dismisses?|records?|captures?|reviews?|taps?)\b",
        r" and \1\2",
        value,
        flags=re.IGNORECASE,
    )


def _third_person_compound_tail(value: str) -> str:
    return re.sub(
        r"\b(and|or)\s+(answer|answers|capture|captures|choose|chooses|click|clicks|dismiss|dismisses|enter|enters|log|logs|record|records|save|saves|select|selects|submit|submits|tap|taps)\b",
        lambda match: match.group(0) if match.group(2)[:1].isupper() else f"{match.group(1)} {third_person_action_verb(match.group(2))}",
        value,
        flags=re.IGNORECASE,
    )


def _numbered_path_story(value: str) -> str:
    text = sentence(value)
    parts = re.split(r"\s+\d+[.)]\s+", text)
    if len(parts) <= 1:
        return ""
    steps = [_clean_numbered_step(part) for part in parts[1:]]
    steps = [step for step in steps if step]
    if not steps:
        return ""
    return _join_action_steps(steps[:4])


def _clean_numbered_step(value: str) -> str:
    text = sentence(value).strip()
    text = re.sub(r"^[.)\s]+", "", text).strip()
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        return ""
    actor_open_then = re.sub(
        r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant))\s+opens\s+[^,.;]+?\s+and\s+(.+)$",
        r"\1 \2",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if actor_open_then != text:
        text = actor_open_then
    else:
        text = re.sub(
            r"^((?:the\s+)?(?:user|person|customer|actor|operator|participant))\s+opens\s+[^,.;]+$",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    text = re.sub(r"^((?:the\s+)?product|(?:the\s+)?system|(?:the\s+)?app)\s+opens\s+[^,.;]+(?:\s+and\s+)?", "", text, count=1, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .")
    if re.match(r"^user\s+", text, flags=re.IGNORECASE):
        text = f"the {text[:1].lower()}{text[1:]}"
    return _lower_first(text) if text else ""


def _join_action_steps(values: Sequence[str]) -> str:
    steps = [sentence(value).rstrip(".") for value in values if sentence(value)]
    if not steps:
        return ""
    if len(steps) == 1:
        return steps[0]
    if len(steps) == 2:
        return f"{steps[0]}, then {steps[1]}"
    return f"{', '.join(steps[:-1])}, and finally {steps[-1]}"


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


def _normalized_story_text(value: str) -> str:
    return " ".join(sentence(value).casefold().strip(" .").split())


def _same_story(left: str, right: str) -> bool:
    return bool(left and right and _normalized_story_text(left) == _normalized_story_text(right))


def _story_sentence(value: str) -> str:
    text = display_text(value)
    text = _capitalize_first(text)
    return text if text.endswith((".", "?", "!")) else f"{text}." if text else ""


def _capitalize_first(value: str) -> str:
    return f"{value[:1].upper()}{value[1:]}" if value else value


def _lower_first(value: str) -> str:
    text = sentence(value).strip()
    return f"{text[:1].lower()}{text[1:]}" if text else ""


def _capitalize_sentence_starts(value: str) -> str:
    return re.sub(r"(?<=[.!?])\s+([a-z])", lambda match: f" {match.group(1).upper()}", sentence(value).strip())


def _story_actor_items(actors: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {"role": display_text(role), "title": _actor_story_title(title), "body": _actor_story_detail(body)}
        for role, title, body in actors[:4]
        if _actor_story_title(title)
    ]


def _actor_story_detail(value: object) -> str:
    text = sanitize_actor_body(value)
    text = re.sub(r"\bthat\s+The\b", "that the", text)
    text = re.sub(r"\bverifies\s+that\s+The\b", "verifies that the", text)
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
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    head, sep, tail = text.partition(":")
    if sep and len(head) >= 36:
        tail_text = sentence(tail)
        if re.search(r"\b\d+[.)]\s+[A-Z]", tail) or _same_story(tail_text, first_path) or "first path" in head.casefold():
            text = head
    if _same_story(text, first_path):
        return "the first path happened, stayed inside its accepted boundary, and left reviewer-visible evidence"
    if len(text) > 260:
        text = _story_excerpt(text, limit=240).rstrip(".")
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
