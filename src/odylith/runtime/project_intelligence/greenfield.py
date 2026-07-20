"""Greenfield-origin Project tab adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.project_intelligence.greenfield_boundary_cards import _claim_evidence
from odylith.runtime.project_intelligence.greenfield_boundary_cards import _dashboard_risk_source
from odylith.runtime.project_intelligence.greenfield_boundary_cards import _known
from odylith.runtime.project_intelligence.greenfield_boundary_cards import _risk_classes
from odylith.runtime.project_intelligence.greenfield_boundary_cards import _risk_items
from odylith.runtime.project_intelligence.greenfield_boundary_cards import _unknown
from odylith.runtime.project_intelligence.greenfield_job_cards import _jobs
from odylith.runtime.project_intelligence.greenfield_participant_cards import _actors
from odylith.runtime.project_intelligence.greenfield_project_text import _dashboard_open_items
from odylith.runtime.project_intelligence.greenfield_project_text import _desired_state
from odylith.runtime.project_intelligence.greenfield_project_text import _display_title
from odylith.runtime.project_intelligence.greenfield_project_text import _host_handoff_prompts
from odylith.runtime.project_intelligence.greenfield_project_text import _non_goal_rows
from odylith.runtime.project_intelligence.greenfield_project_text import _project_intro
from odylith.runtime.project_intelligence.greenfield_project_text import _scenario_body
from odylith.runtime.project_intelligence.greenfield_project_text import _scenario_details
from odylith.runtime.project_intelligence.greenfield_sources import _accepted_proposal
from odylith.runtime.project_intelligence.greenfield_sources import _clean_labeled_text
from odylith.runtime.project_intelligence.greenfield_sources import _first_path
from odylith.runtime.project_intelligence.greenfield_sources import _governance_titles
from odylith.runtime.project_intelligence.greenfield_sources import _lens
from odylith.runtime.project_intelligence.greenfield_sources import _proposal_from_file
from odylith.runtime.project_intelligence.greenfield_sources import _text_rows
from odylith.runtime.project_intelligence.product_story import build_greenfield_product_story
from odylith.runtime.project_intelligence.product_story import summarize_first_path
from odylith.runtime.project_intelligence.source_launch import build_source_launch_handoff
from odylith.runtime.project_intelligence.utils import dict_value, display_text, list_value, sanitize_actor_body, sentence, short, strings
from odylith.runtime.project_intelligence.utils import tidy_fragment


def proposal_from_sources(*, repo_root: Path, shell_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a greenfield proposal carried by runtime payload or local proposal JSON."""

    for key in ("greenfield_proposal", "accepted_proposal", "proposal"):
        value = shell_payload.get(key)
        proposal = _accepted_proposal(value)
        if proposal:
            return proposal
    for path in (
        Path(repo_root) / "odylith" / "runtime" / "source" / "accepted-project.v1.json",
        Path(repo_root) / "odylith" / "runtime" / "source" / "greenfield-project.v1.json",
    ):
        proposal = _proposal_from_file(path)
        if proposal:
            return proposal
    return {}


def build_greenfield_payload(*, proposal: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    """Compile a proposal-origin Project page without pretending source proof exists."""

    intent = dict_value(proposal.get("intent"))
    project = dict_value(proposal.get("project_intelligence"))
    project_brief = dict_value(proposal.get("project_brief"))
    program = dict_value(proposal.get("program"))
    release_plan = dict_value(proposal.get("release_plan"))
    observed = dict_value(proposal.get("observed_source"))
    backlog = [dict(row) for row in list_value(proposal.get("backlog")) if isinstance(row, Mapping)]
    components = [dict(row) for row in list_value(proposal.get("components")) if isinstance(row, Mapping)]
    diagrams = [dict(row) for row in list_value(proposal.get("diagrams")) if isinstance(row, Mapping)]
    release = sentence(release_plan.get("label") or release_plan.get("selector"), "first proposed release")
    risk_source = _dashboard_risk_source(proposal, release=release)
    assumptions = _text_rows(proposal.get("assumptions"), keys=("statement", "assumption"))
    questions = _text_rows(proposal.get("open_questions"), keys=("question", "statement"))
    risks = _text_rows(risk_source, keys=("statement", "risk", "title", "description", "trigger"))
    risk_labels = _text_rows(risk_source, keys=("title", "risk", "statement", "description", "trigger"))
    raw_validation = _text_rows(proposal.get("validation_strategy"))
    validation = [_clean_labeled_text(row) for row in raw_validation]
    non_goals = _non_goal_rows(project)
    accepted = dict_value(proposal.get("_accepted_project"))
    accepted_project = bool(accepted)
    source_launch_context = dict_value(proposal.get("_source_launch") or proposal.get("source_launch"))
    raw_title = sentence(intent.get("title"), "Greenfield project")
    lens = _lens(proposal=proposal, backlog=backlog, components=components)
    first_path = sentence(intent.get("first_path")) or _first_path(
        program=program,
        release_plan=release_plan,
        backlog=backlog,
        validation=raw_validation,
    )
    first_path_summary = summarize_first_path(first_path) or sentence(first_path)
    intro = _project_intro(title=raw_title, intent=intent, project=project)
    title = _display_title(raw_title=raw_title, intro=intro)
    focus = sentence(release_plan.get("strategy")) or sentence(first_path) or "Review the proposed first path before implementation starts."
    open_items = _dashboard_open_items(questions=questions, risks=risk_labels) or ["No open proposal question found."]
    evidence_state = "User-stated and inferred"
    claim_evidence = _claim_evidence(
        title=title,
        intro=intro,
        first_path=first_path,
        validation=validation,
        questions=questions,
        observed=observed,
        accepted=accepted,
    )
    known = _known(
        title=title,
        first_path=first_path,
        release=release,
        components=components,
        diagrams=diagrams,
        accepted=accepted_project,
    )
    unknown = _unknown(questions=questions, assumptions=assumptions, risks=risks, non_goals=non_goals)
    actors = _actors(project, proposal=proposal)
    jobs = _jobs(
        backlog=backlog,
        program=program,
        components=components,
        first_path=first_path,
        project_title=title,
        accepted=accepted,
    )
    product_story = build_greenfield_product_story(
        title=title,
        intro=intro,
        intent=intent,
        project=project,
        project_brief=project_brief,
        first_path=first_path,
        release=release,
        release_plan=release_plan,
        validation=validation,
        accepted=accepted,
        backlog=backlog,
        components=components,
        diagrams=diagrams,
        actors=actors,
    )
    risk_classes = _risk_items(risk_source) or _risk_classes(risks)
    source_launch = (
        build_source_launch_handoff(
            repo_root=repo_root,
            title=title,
            first_path=first_path,
            actors=actors,
            components=components,
            risks=risk_source,
            validation=validation,
            non_goals=non_goals,
            source_launch_context=source_launch_context,
        )
        if accepted_project
        else {}
    )
    sections = ["product_story"]
    if actors:
        sections.append("participants")
    sections.append("risks")
    if jobs:
        sections.append("jobs")
    sections.append("next")
    return {
        "eyebrow": f"Project type: {lens}",
        "title": title,
        "intro": intro,
        "chips": [lens, "accepted greenfield project" if accepted_project else "greenfield proposal", evidence_state],
        "focus_label": "Accepted focus" if accepted_project else "Proposed focus",
        "focus": focus,
        "open_label": "Open questions",
        "open": open_items[:5],
        "product_story_title": "Product Story",
        "product_story_note": "",
        "product_story": product_story,
        "answers": [],
        "risk_title": "Risks",
        "risk_note": "Real-world failure modes that could make this product untrusted, harmful, expensive, or hard to operate.",
        "risk_items": risk_classes,
        "scenario": [
            "Proposed first path",
            title,
            short(first_path_summary, limit=220, fallback="First proposed path"),
            "Evidence is user-stated or inferred; source validation has not happened yet.",
            _scenario_body(project=project, first_path=first_path, validation=validation),
        ],
        "scenario_details": _scenario_details(first_path=first_path, validation=validation, accepted=accepted_project),
        "actors": actors,
        "participants": actors,
        "participants_title": "Who participates?",
        "participants_note": "People named in the accepted product direction.",
        "jobs": jobs,
        "jobs_title": f"What is proposed for {release}?",
        "jobs_note": "Release 0.0.1 work is grouped by the product capabilities named in the accepted direction.",
        "current": (
            f"{title} is an accepted greenfield project with {observed.get('source_posture', 'unknown source posture')}; claims are not source-backed implementation evidence yet."
            if accepted_project
            else f"{title} is a greenfield proposal with {observed.get('source_posture', 'unknown source posture')}; claims are not source-backed implementation evidence yet."
        ),
        "desired": _desired_state(
            title=title,
            project=project,
            project_brief=project_brief,
            first_path=first_path,
            validation=validation,
            risks=risks,
            release=release,
        ),
        "question": "What should move next?",
        "recommendation": (
            "Review the accepted first path, proof gates, and first implementation boundary before coding starts."
            if accepted_project
            else "Review and either accept or revise the proposed first path before coding starts."
        ),
        "options": [
            ("A", "Accept proposed path", "Write accepted project records, then open the first technical plan."),
            ("B", "Revise assumptions", "Update open questions, proof bar, owner, or first path before any write."),
            ("C", "Stop proposal", "Do not create project records until the intent is clearer."),
        ],
        "host_handoff_title": (
            sentence(source_launch.get("title"))
            if accepted_project
            else "How to continue in the host chat"
        ),
        "host_handoff_note": (
            sentence(source_launch.get("note"))
            if accepted_project
            else (
                "Open the canonical proposal rail in the same host chat. It keeps the product story, first path, component "
                "ownership, and proof boundary together; do not inspect or edit proposal JSON by hand."
            )
        ),
        "host_handoff_steps": (
            list_value(source_launch.get("steps"))
            if accepted_project
            else [
                "Review the Product Story, first path, open questions, and risks on this page.",
                "Open the canonical precompiled Greenfield proposal in the same host chat.",
                "Use its hash-bound CONFIRM, EDIT, and REJECT rail.",
                "After CONFIRM, refresh the dashboard to see the committed project state.",
            ]
        ),
        "host_handoff_prompts": (
            list_value(source_launch.get("prompts"))
            if accepted_project
            else _host_handoff_prompts(title=title, accepted=accepted_project)
        ),
        "projection": {
            "refreshed_at": "proposal time",
            "origin": "accepted greenfield project" if accepted_project else "greenfield proposal",
            "maturity": "accepted greenfield direction" if accepted_project else "greenfield or thin evidence",
            "work_mode": "orienting",
            "topology_profile": "proposal-first",
        },
        "claim_evidence": claim_evidence,
        "artifact_coverage": [],
        "topology_spine": [],
        "contradictions": ["No source-backed implementation state exists yet for this greenfield proposal."],
        "delta": ["No previous source-backed project state is available; this projection starts from proposal intent."],
        "risk_classes": risk_classes,
        "audience_emphasis": [],
        "degraded_state": ["Greenfield claims are not source-backed until accepted records, implementation, and validation exist."],
        "known": known,
        "unknown": unknown,
        "confidence": "Medium",
        "blockers": [(item, "Open", "proposal") for item in unknown[:4]],
        "sections": sections,
        "work_state_kicker": "Status now",
        "state_title": "Where does this stand?",
        "state_note": (
            "This separates accepted project direction from source-backed implementation."
            if accepted_project
            else "This separates proposed truth from source-backed implementation."
        ),
        "current_state_label": "Current state",
        "desired_state_label": "Desired state",
        "next_title": (
            sentence(source_launch.get("next_title"), "Start source creation")
            if accepted_project
            else "What should move next?"
        ),
        "next_note": (
            sentence(source_launch.get("next_note"))
            if accepted_project
            else "No implementation should start until the proposed path is accepted or revised."
        ),
        "governance_titles": _governance_titles(backlog=backlog, diagrams=diagrams, accepted=accepted),
        "sources": {
            "proposal": sentence(accepted.get("source_path"))
            or str(Path(repo_root) / "odylith/runtime/source/accepted-project.v1.json")
        },
    }
