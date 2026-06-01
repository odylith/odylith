"""Greenfield-origin Project tab adapter."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.artifact_enrichment import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.artifact_enrichment import tribunal_actor_projection
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks_from_proposal
from odylith.runtime.domain_intelligence.greenfield_product_risks import risk_text_has_framework_leak
from odylith.runtime.project_intelligence.job_cards import job_card_summary
from odylith.runtime.project_intelligence.job_cards import job_status_label
from odylith.runtime.project_intelligence.job_cards import low_information_job_body
from odylith.runtime.project_intelligence.product_story import (
    build_greenfield_product_story,
    project_intent_line,
    summarize_first_path,
    summarize_proof,
)
from odylith.runtime.project_intelligence.participants import participant_body
from odylith.runtime.project_intelligence.participants import participant_key
from odylith.runtime.project_intelligence.participants import participant_title
from odylith.runtime.project_intelligence.participants import participant_title_and_body
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
            short(first_path_summary, limit=150, fallback="First proposed path"),
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
                "Use one of these prompts in the same host chat. The confirmed product story, first path, component ownership, "
                "and proof boundary should move together; the product decision owner should not inspect or edit proposal JSON by hand."
            )
        ),
        "host_handoff_steps": (
            list_value(source_launch.get("steps"))
            if accepted_project
            else [
                "Review the Product Story, first path, open questions, and risks on this page.",
                "Choose Accept, Revise, or Reject below.",
                "Paste the chosen prompt into the same host chat that runs Odylith.",
                "Refresh the dashboard after the command finishes to see the accepted or revised project state.",
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


def _accepted_proposal(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    mode = str(value.get("mode", "")).strip()
    schema = str(value.get("schema_version", "")).strip()
    if (
        isinstance(value.get("project_intelligence"), Mapping)
        and (
            "greenfield" in mode
            or schema == "odylith.greenfield.proposal.v1"
            or mode in {"host_reasoned_proposal", "host_reasoned_greenfield_proposal"}
        )
    ):
        return dict(value)
    for key in ("greenfield_proposal", "accepted_proposal", "proposal"):
        nested = value.get(key)
        proposal = _accepted_proposal(nested)
        if proposal:
            return proposal
    return {}


def _proposal_from_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, Mapping):
        return {}
    proposal = _accepted_proposal(raw.get("proposal"))
    if not proposal:
        proposal = _accepted_proposal(raw)
    if not proposal:
        return {}
    if raw.get("schema_version") == "odylith.accepted_project.v1":
        enriched = dict(proposal)
        enriched["_accepted_project"] = {
            "accepted_at": sentence(raw.get("accepted_at")),
            "origin": sentence(raw.get("origin"), "greenfield"),
            "evidence_tier": sentence(raw.get("evidence_tier"), "user_intent"),
            "created": dict_value(raw.get("created")),
            "source_path": str(path),
            "validation_gate": dict_value(raw.get("validation_gate") or raw.get("tribunal")),
        }
        return enriched
    return proposal


def _text_rows(value: object, *, keys: Sequence[str] = ("statement", "question", "risk", "validation", "goal")) -> list[str]:
    rows: list[str] = []
    for item in list_value(value):
        if isinstance(item, Mapping):
            text = next((sentence(item.get(key)) for key in keys if sentence(item.get(key))), "")
        else:
            text = sentence(item)
        if text and text not in rows:
            rows.append(text)
    return rows


def _governance_titles(
    *,
    backlog: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    accepted: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    titles: dict[str, str] = {}
    created = dict_value((accepted or {}).get("created"))
    created_workstreams = [dict(row) for row in list_value(created.get("workstreams")) if isinstance(row, Mapping)]
    created_diagrams = list_value(created.get("diagrams"))

    def add(reference: object, title: object) -> None:
        ref = sentence(reference).upper()
        label = sentence(title)
        if ref and label and re.fullmatch(r"(?:B|D)-\d+", ref):
            titles[ref] = label

    for index, row in enumerate(backlog):
        created_row = created_workstreams[index] if index < len(created_workstreams) else {}
        add(row.get("idea_id") or row.get("id") or created_row.get("idea_id"), row.get("title") or row.get("name") or created_row.get("title"))
    for index, row in enumerate(diagrams):
        created_row = created_diagrams[index] if index < len(created_diagrams) else {}
        if isinstance(created_row, Mapping):
            ref = created_row.get("diagram_id") or created_row.get("id")
            label = created_row.get("title") or created_row.get("name")
        else:
            ref = created_row
            label = ""
        add(
            row.get("diagram_id") or row.get("id") or ref,
            row.get("title") or row.get("name") or row.get("slug") or label,
        )
    return titles


def _lens(*, proposal: Mapping[str, Any], backlog: Sequence[Mapping[str, Any]], components: Sequence[Mapping[str, Any]]) -> str:
    classification = dict_value(proposal.get("classification"))
    for key in ("primary_lens", "domain_lens", "family"):
        token = sentence(classification.get(key))
        if token:
            return token.lower()
    for row in backlog:
        intelligence = row.get("domain_intelligence")
        if not isinstance(intelligence, Mapping):
            continue
        graph = domain_graph_from_workstream(intelligence, row=row, proposal=proposal)
        if graph.primary_lens:
            return graph.primary_lens
    for component in components:
        token = sentence(component.get("kind") or component.get("label"))
        if token:
            return token.lower()
    return "greenfield"


def _first_path(
    *,
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    backlog: Sequence[Mapping[str, Any]],
    validation: Sequence[str] = (),
) -> str:
    validation_first_path = _first_slice_from_validation(validation)
    if validation_first_path:
        return validation_first_path
    for item in backlog:
        title = sentence(item.get("title"))
        if title.lower().startswith("govern "):
            continue
        first_slice = sentence(item.get("recommended_first_slice"))
        if first_slice and not _is_meta_first_path(title=title, first_slice=first_slice):
            return first_slice
    waves = [dict(row) for row in list_value(program.get("waves")) if isinstance(row, Mapping)]
    if waves:
        wave = waves[0]
        return sentence(wave.get("goal") or wave.get("label"), "First proposed wave")
    stages = [dict(row) for row in list_value(release_plan.get("release_stages")) if isinstance(row, Mapping)]
    if stages:
        stage = stages[0]
        return sentence(stage.get("release_gate") or stage.get("label"), "First release gate")
    if backlog:
        return sentence(backlog[0].get("recommended_first_slice") or backlog[0].get("title"), "First proposed workstream")
    return "One accepted path moves from proposal intent to validated first slice."


def _first_slice_from_validation(rows: Sequence[str]) -> str:
    for row in rows:
        label, body = _labeled_text_parts(row)
        normalized = label.replace("_", " ").replace("-", " ").casefold()
        if body and normalized in {
            "first slice proof",
            "first path proof",
            "first slice",
            "first path",
        }:
            return body
    return ""


def _labeled_text_parts(value: object) -> tuple[str, str]:
    text = sentence(value)
    label, sep, body = text.partition(":")
    if not sep:
        return "", text
    return sentence(label), sentence(body)


def _clean_labeled_text(value: object) -> str:
    label, body = _labeled_text_parts(value)
    normalized = label.replace("_", " ").replace("-", " ").casefold()
    if body and normalized in {
        "first slice proof",
        "first path proof",
        "proof",
        "validation",
        "success condition",
    }:
        return body
    return sentence(value)


def _is_meta_first_path(*, title: str, first_slice: str) -> bool:
    text = f"{title} {first_slice}".casefold()
    if not text.strip():
        return False
    if sentence(title).casefold().startswith(("guide ", "shape ", "govern ")):
        return True
    return any(
        marker in text
        for marker in (
            "accept or revise",
            "accept the",
            "component boundaries",
            "proof gates",
            "before implementation planning",
            "coding-readiness",
            "project shape",
            "project direction",
            "proposal review",
        )
    )


def _project_intro(*, title: str, intent: Mapping[str, Any], project: Mapping[str, Any]) -> str:
    candidates = [
        sentence(intent.get("product_story")),
        project_intent_line(project, "project objective"),
        project_intent_line(project, "user or stakeholder outcome"),
        sentence(intent.get("summary")),
        sentence(project.get("purpose")),
    ]
    for candidate in candidates:
        cleaned = _clean_objective_sentence(candidate)
        if cleaned and not _looks_meta_project_line(cleaned):
            return cleaned
    display = _title_case(_project_name_candidate(title) or sentence(title, "Project"))
    return f"{display} is a proposed product; the first path, actors, systems, and proof boundary need product-owner confirmation."


def _looks_meta_project_line(value: str) -> bool:
    lowered = sentence(value).casefold()
    if not lowered:
        return False
    if any(
        marker in lowered
        for marker in (
            "accepted product truth",
            "accepted project truth",
            "before backlog",
            "before any generated artifact",
            "governable as one product spine",
            "governance artifact",
            "proposal expansion",
            "source boundary",
        )
    ):
        return True
    if lowered.startswith("make ") and any(
        marker in lowered
        for marker in (
            "readable and governable",
            "before any generated artifact",
            "governable as one product spine",
            "source boundary",
        )
    ):
        return True
    return lowered.startswith(("capture ", "turn the operator request into"))

def _clean_objective_sentence(value: str) -> str:
    text = sentence(value)
    lowered = text.lower()
    if lowered.startswith("govern "):
        text = text[len("govern "):].strip()
    if text:
        text = text[0].upper() + text[1:]
    return text


def _display_title(*, raw_title: str, intro: str) -> str:
    intro_text = sentence(intro)
    candidates = []
    if raw_title:
        candidates.append(raw_title)
    if intro_text.lower().startswith("govern "):
        candidates.append(intro_text[len("govern "):].strip())
    for article in ("A ", "An ", "The "):
        if intro_text.startswith(article):
            candidates.append(intro_text[len(article):].strip())
            break
    candidates.append(intro_text)
    candidates.append(raw_title)
    for candidate in candidates:
        head = _project_name_candidate(candidate)
        if 8 <= len(head) <= 64:
            return _title_case(head)
    return _clean_display_title(sentence(raw_title, "Greenfield project"))


def _project_name_candidate(value: str) -> str:
    text = _clean_display_title(_strip_prompt_directives(sentence(value)))
    lowered = text.casefold()
    if any(
        marker in lowered
        for marker in (
            "accepted product story",
            "accepted project",
            "source boundary",
            "governable",
            "before any generated artifact",
        )
    ):
        return ""
    for prefix in (
        "draft a greenfield proposal for ",
        "draft a product-first greenfield proposal for ",
        "draft a product first greenfield proposal for ",
        "build an ",
        "build a ",
        "build ",
        "create an ",
        "create a ",
        "create ",
    ):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return _clean_display_title(_title_head(text))


def _title_head(value: str) -> str:
    text = _clean_display_title(sentence(value))
    that_head, that_sep, that_tail = _partition_casefold(text, " that ")
    if that_sep and _is_generic_product_noun(that_head):
        tail_head = _clause_head(that_tail)
        if tail_head:
            return _clean_display_title(f"{that_head.strip()} that {tail_head}")
    for marker in (" that ", " around ", " before ", " with ", " by ", " to "):
        head, sep, tail = _partition_casefold(text, marker)
        if sep:
            if marker == " with " and _should_keep_with_clause(head, tail):
                return _clean_display_title(f"{head.strip(' .')} with {_clause_head(tail)}")
            return _clean_display_title(head)
    return _clean_display_title(text)


def _should_keep_with_clause(head: str, tail: str) -> bool:
    """Keep short product names specific when their differentiator follows ``with``."""

    head_words = sentence(head).split()
    tail_head = _clause_head(tail)
    if not tail_head or len(head_words) > 3:
        return False
    generic_terms = {"app", "application", "platform", "product", "service", "site", "system", "tool"}
    return bool(head_words and head_words[-1].casefold() in generic_terms)


def _strip_prompt_directives(value: str) -> str:
    text = sentence(value)
    if not text:
        return ""
    command_starts = (
        "show ",
        "do not ",
        "don't ",
        "please ",
        "think of ",
        "make sure ",
        "use ",
    )
    kept: list[str] = []
    for raw in re.split(r"(?<=[.!?])\s+", text):
        clause = raw.strip()
        if not clause:
            continue
        lowered = clause.casefold()
        if kept and lowered.startswith(command_starts):
            continue
        kept.append(clause)
    return " ".join(kept) or text


def _is_generic_product_noun(value: str) -> bool:
    normalized = sentence(value).casefold().strip(" .")
    normalized = re.sub(r"^(?:a|an|the)\s+", "", normalized)
    return normalized in {
        "app",
        "application",
        "assistant",
        "platform",
        "product",
        "service",
        "system",
        "tool",
        "workflow",
    }


def _clause_head(value: str) -> str:
    text = sentence(value).strip(" .")
    for marker in (",", ";", ". ", " and ", " while ", " so ", " before "):
        head, sep, _tail = _partition_casefold(text, marker)
        if sep and head.strip():
            return head.strip(" .")
    return text


def _partition_casefold(value: str, marker: str) -> tuple[str, str, str]:
    index = value.casefold().find(marker.casefold())
    if index < 0:
        return value, "", ""
    return value[:index], value[index : index + len(marker)], value[index + len(marker) :]


def _title_case(value: str) -> str:
    preserve = {"AI", "API", "CLI", "CI", "DeFi", "SMB", "UI", "UX"}
    minor_words = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    tokens: list[str] = []
    raw_tokens = _clean_display_title(value).replace("-", " ").split()
    for index, token in enumerate(raw_tokens):
        matched = next((word for word in preserve if token.lower() == word.lower()), "")
        if matched:
            tokens.append(matched)
            continue
        if _has_internal_capital(token):
            tokens.append(token)
            continue
        if index > 0 and token.casefold().strip(":") in minor_words and not raw_tokens[index - 1].endswith(":"):
            tokens.append(token.lower())
            continue
        tokens.append(token[:1].upper() + token[1:].lower())
    return " ".join(tokens)


def _clean_display_title(value: str) -> str:
    text = " ".join(sentence(value).split())
    text = re.sub(r"^[\s\-–—:·|]+", "", text)
    text = re.sub(r"[\s\-–—:·|]+$", "", text)
    return text.strip()


def _has_internal_capital(value: str) -> bool:
    token = value.strip(".,;:!?()[]{}")
    return any(char.islower() for char in token) and any(char.isupper() for char in token[1:])


def _dashboard_open_items(*, questions: Sequence[str], risks: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for item in [*questions[:3], *risks[:2]]:
        excerpt = _dashboard_excerpt(item, limit=150)
        if excerpt and excerpt not in rows:
            rows.append(excerpt)
    return rows[:4]


def _dashboard_excerpt(value: str, *, limit: int = 210) -> str:
    text = summarize_first_path(value) if re.search(r"\b\d+[.)]\s+[A-Z]", sentence(value)) else sentence(value).strip()
    if not text:
        return ""
    for separator in (". ", "; ", ": "):
        head, sep, _tail = text.partition(separator)
        if sep and 42 <= len(head) <= limit:
            return head.rstrip(" ,;:") + ("." if separator == ". " else "")
    return short(text, limit=limit)


def _capitalize_first(value: str) -> str:
    return f"{value[:1].upper()}{value[1:]}" if value else value


def _join_titles(values: Sequence[str]) -> str:
    items = [sentence(value) for value in values if sentence(value)]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _state_object_change(project: Mapping[str, Any]) -> str:
    for row in strings(project.get("state")):
        obj = _state_object_name(row)
        if not obj:
            continue
        states = _state_names(row)
        if len(states) >= 2:
            return short(f"{obj} moves from {states[0]} to {states[-1]}", limit=80)
        return short(f"{obj} becomes the reviewable state object", limit=80)
    return ""


def _state_change_body(project: Mapping[str, Any]) -> str:
    for row in strings(project.get("state")):
        obj = _state_object_name(row)
        owned = _state_owned_pieces(row)
        if obj and owned:
            return short(f"The {obj} is the reviewable domain object: {_join_titles(owned[:4])}.", limit=180)
        if obj:
            return short(f"The {obj} is the state object reviewers should be able to understand, replay, and trust.", limit=180)
    return ""


def _state_object_name(value: object) -> str:
    text = sentence(value)
    patterns = (
        r"(?:primary\s+)?state object is (?:the\s+)?([A-Z][A-Za-z0-9 _/-]{1,48}?)(?:\.|;|,|\s+moves|\s+that|\s+through)",
        r"\bA\s+([A-Z][A-Za-z0-9 _/-]{1,48}?)\s+moves\s+through",
        r"\bAn\s+([A-Z][A-Za-z0-9 _/-]{1,48}?)\s+moves\s+through",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return sentence(match.group(1)).strip(" .")
    return ""


def _state_names(value: object) -> list[str]:
    text = sentence(value)
    names: list[str] = []
    blocked = {"evidence", "flow", "journey", "owns", "path", "proof", "state", "states"}
    for match in re.finditer(r"\b([a-z][a-z0-9_-]{1,32})\s*:", text):
        name = match.group(1).replace("_", " ").replace("-", " ").strip()
        if name.casefold() in blocked or name in names:
            continue
        names.append(name)
    return names[:8]


def _state_owned_pieces(value: object) -> list[str]:
    text = sentence(value)
    match = re.search(r"\bowns\s*:\s*(.+?)(?:\.\s+[A-Z][^.]*(?:changes|moves|must|should)\b|$)", text, flags=re.IGNORECASE)
    if not match:
        return []
    tail = match.group(1).strip(" .")
    pieces = [piece.strip(" .") for piece in re.split(r",|\s+and\s+", tail) if piece.strip(" .")]
    return [piece for piece in pieces if len(piece.split()) <= 8][:6]


def _desired_state(
    *,
    title: str,
    project: Mapping[str, Any],
    project_brief: Mapping[str, Any],
    first_path: str,
    validation: Sequence[str],
    risks: Sequence[str],
    release: str,
) -> str:
    reality = _desired_reality(title=title, project=project, project_brief=project_brief)
    capability = _desired_capability(project=project, project_brief=project_brief, first_path=first_path)
    proof = _desired_proof_summary(validation=validation, first_path=first_path, release=release)
    rows = [
        f"Target reality: {_desired_sentence(reality)}",
        f"User capability: {_desired_sentence(capability)}",
        f"Release trust: {_desired_sentence(proof)}",
    ]
    return " ".join(row for row in rows if row)


def _desired_reality(*, title: str, project: Mapping[str, Any], project_brief: Mapping[str, Any]) -> str:
    explicit = _clean_desired_state(strings(project.get("state")))
    if explicit:
        return _compact_desired_text(explicit)
    state_change = _state_object_change(project)
    if state_change:
        return f"{state_change} with supporting evidence visible."
    purpose = sentence(project_brief.get("purpose") or project_brief.get("summary") or project.get("purpose"))
    if purpose and not _looks_meta_project_line(purpose):
        body = _desired_reality_excerpt(purpose)
        body = _purpose_as_reality(body)
        return _compact_desired_text(body)
    return (
        f"People using {title} can understand the current product state without reconstructing context from scattered inputs."
    )


def _purpose_as_reality(value: str) -> str:
    text = sentence(value).rstrip(".")
    if not text.casefold().startswith("make "):
        return text
    remainder = text[5:].strip()
    head, sep, tail = _partition_casefold(remainder, " by ")
    if sep and head.strip() and tail.strip():
        words = head.strip().split()
        if len(words) >= 2:
            subject = " ".join(words[:-1])
            predicate = words[-1]
            return f"{_capitalize_first(subject)} is {predicate} through {tail.strip()}"
    return f"the team can {text[0].lower() + text[1:] if text else text}"


def _desired_reality_excerpt(value: object) -> str:
    text = sentence(value).rstrip(".")
    if not text:
        return ""
    sentences = [row.rstrip(".") for row in re.split(r"(?<=[.!?])\s+", text) if row.strip()]
    if not sentences:
        return text
    selected: list[str] = []
    for row in sentences:
        if len(" ".join(selected + [row])) > 180:
            break
        selected.append(row)
        if len(selected) >= 1:
            break
    return ". ".join(selected or sentences[:1]).rstrip(".")


def _clean_desired_state(rows: Sequence[str]) -> str:
    for row in rows:
        label, body = _labeled_text_parts(row)
        if label.replace("_", " ").replace("-", " ").casefold() == "desired state" and body:
            cleaned = sentence(body).rstrip(".")
            if cleaned and not _looks_meta_project_line(cleaned):
                return f"{cleaned}."
    return ""


def _desired_capability(*, project: Mapping[str, Any], project_brief: Mapping[str, Any], first_path: str) -> str:
    operator_value = sentence(project_brief.get("operator_value") or project_brief.get("project_outcome"))
    if operator_value and not _looks_proof_or_scope_line(operator_value):
        return _compact_desired_text(operator_value)
    state_body = _state_change_body(project)
    if state_body:
        return _compact_desired_text(state_body)
    path = summarize_first_path(first_path).rstrip(".") or sentence(first_path).rstrip(".")
    if path:
        return "The accepted first-path scenario works as the first usable product capability."
    return "The user can see the relevant object, current state, supporting evidence, and next decision in one place."


def _desired_risk(*, risks: Sequence[str], project: Mapping[str, Any]) -> str:
    risk = _risk_without_embedded_path(risks[0]) if risks else ""
    if risk:
        return f"The system reduces this domain risk first: {risk.rstrip('.')}."
    failure = project_intent_line(project, "what breaks if it fails")
    if failure:
        return f"The system reduces the failure mode where {failure[0].lower() + failure[1:] if failure else failure}."
    return "The system reduces the risk that product claims drift away from their source, time, owner, and evidence."


def _desired_proof(*, validation: Sequence[str], first_path: str, release: str) -> str:
    evidence = _proof_answer_body(validation=validation, first_path=first_path).rstrip(".")
    release_label = sentence(release, "the first release")
    if evidence:
        return f"Release {release_label} succeeds when a reviewer can follow the evidence needed to trust that first release: {evidence}."
    return (
        f"Release {release_label} succeeds when a reviewer can see the active object, current state, source evidence, "
        "changes since the prior state, and the audit trail that explains the result."
    )


def _desired_proof_summary(*, validation: Sequence[str], first_path: str, release: str) -> str:
    release_label = sentence(release, "the first release")
    proof = summarize_proof(validation[0] if validation else "", first_path=first_path)
    if proof and not _looks_path_echo(proof, first_path=first_path):
        return _compact_desired_text(proof)
    return f"Release {release_label} is not trusted until source evidence and validation output prove the accepted scenario."


def _desired_sentence(value: object) -> str:
    text = _compact_desired_text(value)
    return text.rstrip(".") + "." if text else ""


def _compact_desired_text(value: object) -> str:
    text = sentence(value).strip()
    text = re.sub(r"\b\d+[.)]\s+[A-Z].*", "", text).strip(" .")
    text = text.replace("The desired operational reality is that ", "")
    text = text.replace("the desired operational reality is that ", "")
    text = text.replace("The first complete path the product must prove is ", "The accepted scenario is ")
    text = text.replace("The accepted first path passes end to end:", "")
    text = _dashboard_excerpt(text, limit=150)
    return tidy_fragment(text)


def _looks_proof_or_scope_line(value: object) -> bool:
    text = sentence(value).casefold()
    if not text:
        return False
    return any(
        marker in text
        for marker in (
            "what would count as evidence",
            "proof must show",
            "release proof",
            "must not be claimed",
            "no accuracy numbers",
            "passes end to end",
        )
    )


def _risk_without_embedded_path(value: object) -> str:
    text = sentence(value)
    if not text:
        return ""
    head, sep, _tail = text.partition(":")
    if sep and len(head) >= 48:
        return head.rstrip(" .") + "."
    if re.search(r"\b\d+[.)]\s+[A-Z]", text):
        return summarize_first_path(text)
    return text


def _clean_project_purpose(value: object) -> str:
    text = sentence(value)
    lowered = text.casefold()
    if lowered.startswith("make ") and "concrete product program before implementation starts" in lowered:
        return ""
    if "project object captures intent" in lowered:
        return ""
    return text


def _non_goal_rows(project: Mapping[str, Any]) -> list[str]:
    raw = project_intent_line(project, "non-goals")
    if not raw:
        return []
    pieces = [piece.strip(" .") for piece in raw.split(",") if piece.strip(" .")]
    if len(pieces) <= 1:
        pieces = [raw.strip(" .")]
    return [f"Not in the first release: {piece}." for piece in pieces[:4]]


def _host_handoff_prompts(*, title: str, accepted: bool = False) -> list[dict[str, str]]:
    if accepted:
        return [
            {
                "label": "Start implementation plan",
                "when": "Use this now when the product story and first release boundary look right.",
                "prompt": (
                    "Odylith, open the first implementation plan. Show the first source boundary, "
                    "files or modules likely to change, proof gates, blockers, and the exact first coding slice before editing source."
                ),
                "result": "Creates the plan that turns accepted direction into a source-editable slice.",
            },
            {
                "label": "Implement first coding slice",
                "when": "Use this only after the first implementation plan is accepted.",
                "prompt": (
                    "Odylith, implement the first coding slice from the accepted implementation plan. "
                    "Before editing, restate the target files, proof gates, validation commands, and stop conditions."
                ),
                "result": "Starts source edits for the first bounded slice.",
            },
            {
                "label": "Revise project direction",
                "when": "Use this when the accepted product story, actor, first path, or proof boundary is wrong.",
                "prompt": (
                    "Odylith, revise the accepted project direction: change <what is wrong> "
                    "to <what should be true>. Keep the product story, first path, component ownership, release gates, and proof boundary aligned."
                ),
                "result": "Updates the accepted project direction so the dashboard tells the corrected product story.",
            },
            {
                "label": "Pause",
                "when": "Use this when the accepted project should not proceed into planning yet.",
                "prompt": "Odylith, pause implementation planning; keep the accepted project visible but do not start source work.",
                "result": "Keeps project direction visible without implying implementation readiness.",
            },
        ]
    return [
        {
            "label": "Accept it",
            "when": "Use this when the story, first path, actors, open questions, and proof boundary look right.",
            "prompt": "Odylith, apply this greenfield proposal as-is and write the accepted project plan.",
            "result": "Writes the accepted product story, component boundaries, architecture views, release boundary, and proof gates.",
        },
        {
            "label": "Revise it",
            "when": "Use this when the project is close, but the first path, actor, system boundary, proof bar, or exclusions need correction.",
            "prompt": (
                "Odylith, revise this greenfield proposal before applying it: change <what is wrong> to <what should be true>. "
                "Keep the product story, first path, components, risks, and proof gates aligned with the correction. "
                "Do not write project records until I confirm."
            ),
            "result": "Produces a revised proposal for review without mutating accepted project records.",
        },
        {
            "label": "Reject it",
            "when": "Use this when the interpretation is the wrong product or the user intent is not clear enough.",
            "prompt": "Odylith, reject this greenfield proposal. Do not write project records.",
            "result": "Leaves the repo in proposal or blank state so a new intent can be supplied.",
        },
    ]


def _proof_title(validation: Sequence[str], *, first_path: str = "") -> str:
    text = sentence(validation[0] if validation else "")
    if "implementation-backed behavior proof" in text.casefold():
        return "First-slice behavior proof"
    proof = summarize_proof(text, first_path=first_path)
    if proof.casefold().startswith("the accepted first path passes end to end"):
        return "Accepted first path passes end to end"
    return short(proof, limit=70, fallback="First validation path")


def _proof_body(*, validation: Sequence[str], first_path: str) -> str:
    proof = summarize_proof(validation[0] if validation else "", first_path=first_path)
    if proof:
        if proof.casefold().startswith("proof must show "):
            return proof.rstrip(".") + "."
        return proof.rstrip(".") + "."
    path = summarize_first_path(first_path)
    if path:
        return f"{path.rstrip('.')} must pass with reviewer-visible evidence."
    return "Validation path must be confirmed before source-backed claims."


def _proof_answer_body(*, validation: Sequence[str], first_path: str) -> str:
    proof = summarize_proof(validation[0] if validation else "", first_path=first_path)
    if proof and not _looks_path_echo(proof, first_path=first_path):
        return proof.rstrip(".") + "."
    return (
        "Release proof should show the accepted path running end to end with reviewer-visible source evidence, "
        "validation output, explicit non-goals, failure or recovery handling, and an explicit release decision."
    )


def _looks_path_echo(value: object, *, first_path: str) -> bool:
    text = _repeat_key(sentence(value))
    path = _repeat_key(summarize_first_path(first_path) or sentence(first_path))
    if not text:
        return False
    return (
        "first path" in text
        or "first complete path" in text
        or bool(path and (path in text or text in path))
    )


def _scenario_body(*, project: Mapping[str, Any], first_path: str, validation: Sequence[str]) -> str:
    purpose = short(
        _clean_project_purpose(project.get("purpose")) or _clean_objective_sentence(project_intent_line(project, "project objective")),
        limit=260,
        fallback="The proposal names the first project shape.",
    )
    path = (summarize_first_path(first_path) or sentence(first_path)).rstrip(".")
    proof_text = _proof_body(validation=validation, first_path=first_path).rstrip(".")
    return f"{purpose} First path: {path}. Proof needed: {proof_text}."


def _scenario_details(*, first_path: str, validation: Sequence[str], accepted: bool) -> list[tuple[str, str]]:
    path = (summarize_first_path(first_path) or sentence(first_path)).rstrip(".")
    proof = _proof_body(validation=validation, first_path=first_path).rstrip(".")
    evidence = (
        "Accepted direction only; implementation still needs source and validation evidence."
        if accepted
        else "Proposal direction only; the operator still needs to accept or revise it."
    )
    rows = []
    if path:
        rows.append(("First path", path + "."))
    if proof:
        rows.append(("Proof", proof + "."))
    rows.append(("Evidence state", evidence))
    return rows


def _actors(project: Mapping[str, Any], *, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    project_rows = _project_actor_rows(project=project, proposal=proposal)
    if project_rows:
        return project_rows[:6]

    accepted = dict_value(proposal.get("_accepted_project"))
    validation_gate = _accepted_validation_gate(accepted)
    visible_actors = [dict(row) for row in list_value(validation_gate.get("visible_actors")) if isinstance(row, Mapping)]
    if not visible_actors:
        visible_actors = [dict(row) for row in tribunal_actor_projection(proposal)]
    if visible_actors:
        owner_responsibilities = {**_proposal_actor_responsibility_map(proposal), **_owner_responsibility_map(project)}
        rows = [
            (
                "",
                sentence(row.get("visible_actor"), "Project actor"),
                short(
                    owner_responsibilities.get(sentence(row.get("visible_actor")).casefold())
                    or row.get("responsibility"),
                    limit=145,
                ),
            )
            for row in visible_actors[:6]
            if _is_project_actor_label(sentence(row.get("visible_actor")))
        ]
        if rows:
            return _dedupe_actor_rows(rows)[:6]
    rows = []
    for value in strings(project.get("owners"))[:6]:
        head, _, body = value.partition(":")
        title = sentence(head, "Owner")
        if _is_project_actor_label(title):
            rows.append(("", title, short(body or value, limit=145)))
    for value in strings(project.get("operators"))[:3]:
        head, _, body = value.partition(":")
        title = sentence(head, "Product decision owner")
        if _is_project_actor_label(title):
            rows.append(("", title, short(body or value, limit=145)))
    return _dedupe_actor_rows(rows)[:6] or [
        ("", "Product decision owner", "Reviews and accepts or revises the product direction before implementation.")
    ]


def _project_actor_rows(
    *,
    project: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> list[tuple[str, str, str]]:
    """Return Project-facing actors before internal Tribunal role projections."""

    direct_rows: list[tuple[str, str, str]] = []
    direct_rows.extend(_intent_actor_rows(proposal=proposal))
    direct_rows.extend(_domain_actor_rows(proposal=proposal))
    if direct_rows:
        return _dedupe_actor_rows(direct_rows)

    rows: list[tuple[str, str, str]] = []
    rows.extend(_customer_actor_rows(proposal=proposal))
    for value in [*strings(project.get("owners")), *strings(project.get("operators"))]:
        title, body = _actor_title_and_body(value)
        if _is_project_actor_label(title):
            rows.append(("", title, short(body, limit=145)))
    return _dedupe_actor_rows(rows)


def _domain_actor_rows(*, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for item in list_value(proposal.get("backlog")):
        if not isinstance(item, Mapping):
            continue
        intelligence = dict_value(item.get("domain_intelligence"))
        for value in strings(intelligence.get("actors")):
            title, body = _actor_title_and_body(value)
            if _is_project_actor_label(title):
                rows.append(("", title, short(body, limit=145)))
    return _dedupe_actor_rows(rows)


def _intent_actor_rows(*, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    intent = dict_value(proposal.get("intent"))
    context = sentence(intent.get("product_story") or intent.get("summary"))
    for value in strings(intent.get("human_actors")):
        title, body = participant_title_and_body(value, context=context)
        if title and _is_project_actor_label(title):
            rows.append(("", title, body))
    return rows


def _customer_actor_rows(*, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    backlog_items = [item for item in list_value(proposal.get("backlog")) if isinstance(item, Mapping)]
    backlog_items.sort(key=lambda item: 1 if sentence(item.get("title")).casefold().startswith("govern ") else 0)
    for item in backlog_items:
        customer = sentence(item.get("customer"))
        if not customer:
            continue
        context = sentence(item.get("opportunity") or item.get("problem") or item.get("product_view"))
        segments = _customer_segments(customer)
        actor_list = _customer_segments_are_actor_list(customer, segments)
        for segment in segments:
            title = _customer_actor_title(segment)
            if "," in title and not actor_list:
                continue
            if not _is_project_actor_label(title):
                continue
            body = _customer_actor_body(segment=segment, context="" if actor_list else context)
            rows.append(("", title, body))
    return rows


def _customer_segments(value: str) -> list[str]:
    text = display_text(value)
    pieces = [piece.strip(" .") for piece in re.split(r";|\s+;\s+", text) if piece.strip(" .")]
    if len(pieces) == 1 and "," in text:
        comma_pieces = [
            re.sub(r"^(?:and\s+)", "", piece.strip(" ."), flags=re.IGNORECASE)
            for piece in text.split(",")
            if piece.strip(" .")
        ]
        if len(comma_pieces) >= 2 and all(1 <= len(piece.split()) <= 5 for piece in comma_pieces):
            pieces = comma_pieces
    return pieces or ([text] if text else [])


def _customer_segments_are_actor_list(value: str, segments: Sequence[str]) -> bool:
    """Return true when a customer field is only a compact list of roles."""

    text = display_text(value)
    if len(segments) < 2 or "," not in text:
        return False
    for segment in segments:
        clean = display_text(segment)
        if not clean or len(clean.split()) > 6:
            return False
        if _role_description_parts(clean)[1]:
            return False
    return True


def _customer_actor_title(value: str) -> str:
    text = display_text(value).strip(" .")
    text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
    role, _body = _role_description_parts(text)
    if role:
        return short(participant_title(role) or _capitalize_first(role), limit=70)
    for marker in (
        " asking ",
        " auditing ",
        " authorizing ",
        " completing ",
        " configuring ",
        " entering ",
        " filing ",
        " filling ",
        " following up",
        " integrating ",
        " opening ",
        " producing ",
        " reading ",
        " receiving ",
        " registering ",
        " reviewing ",
        " selecting ",
        " submitting ",
        " running ",
        " using ",
        " who ",
        " at ",
    ):
        head, sep, _tail = _partition_casefold(text, marker)
        if sep and head.strip():
            text = head.strip(" .")
            break
    return short(participant_title(_capitalize_first(text)) or _capitalize_first(text), limit=70)


def _customer_actor_body(*, segment: str, context: str) -> str:
    text = display_text(segment).strip(" .")
    title, detail = _role_description_parts(text)
    if not title:
        title = _customer_actor_title(text)
        detail = text
        if title and text.casefold().startswith(title.casefold()):
            detail = text[len(title) :].strip(" .")
    if detail:
        return participant_body(title=title, body=_capitalize_first(detail), context=context)
    return participant_body(title=title, context=context or _default_actor_body(title))


def _actor_title_and_body(value: object) -> tuple[str, str]:
    text = display_text(value)
    if not text:
        return "", ""
    role, role_body = _role_description_parts(text)
    if role:
        title = participant_title(role) or role
        return title, participant_body(title=title, body=role_body, context=_default_actor_body(title))
    head, sep, body = text.partition(":")
    title = participant_title(head) or sentence(head)
    detail = sentence(body if sep else text)
    if not detail or detail.casefold() == title.casefold():
        detail = participant_body(title=title, context=_default_actor_body(title))
    elif detail:
        detail = participant_body(title=title, body=detail[:1].upper() + detail[1:])
    return title, detail


def _role_description_parts(value: str) -> tuple[str, str]:
    text = display_text(value).strip(" .")
    for separator in (" — ", " – ", " - "):
        head, sep, body = text.partition(separator)
        if sep and head.strip() and body.strip():
            return sentence(head), sentence(body)
    head, sep, body = text.partition(":")
    if sep and head.strip() and body.strip() and len(head.split()) <= 10:
        return sentence(head), sentence(body)
    return "", ""


def _default_actor_body(title: str) -> str:
    lowered = title.casefold()
    if any(token in lowered for token in ("owner", "advocate", "user", "customer", "client")):
        return "Uses the product outcome to decide what should happen next."
    if any(token in lowered for token in ("operator", "coordinator", "caretaker", "maintainer")):
        return "Coordinates exceptions and keeps the right people aligned around the product outcome."
    if any(token in lowered for token in ("risk", "safety", "compliance", "privacy")):
        return "Owns the harm, policy, or operational exposure that can block adoption."
    if any(token in lowered for token in ("proof", "evidence", "quality", "validation", "reviewer")):
        return "Decides whether the outcome is clear, explainable, and trustworthy enough to use."
    if any(token in lowered for token in ("build", "implementation", "engineer", "developer")):
        return "Owns the implementation path after the project direction is accepted."
    return "Has a distinct stake in the product outcome and needs enough context to act responsibly."


def _is_project_actor_label(value: str) -> bool:
    label = sentence(value)
    if not label:
        return False
    if len(label.split()) > 10:
        return False
    lowered = label.casefold().replace("_", " ")
    if lowered in {
        "actor",
        "other accepted items",
        "beneficiary advocate",
        "domain operator",
        "risk owner",
        "evidence owner",
        "implementation owner",
        "release owner",
        "project actor",
        "primary user",
    }:
        return False
    if lowered.startswith(("the first-release actors are", "actors involved in")):
        return False
    if "accepted items" in lowered and "intent" in lowered:
        return False
    internal_markers = (
        "program boundary",
        "safety envelope",
        "project intelligence",
        "governance artifact",
        "release gate",
        "proof gate",
        "source boundary",
        "topology spine",
    )
    if any(marker in lowered for marker in internal_markers):
        return False
    system_markers = (
        "unit",
        "core",
        "controller",
        "engine",
        "harness",
        "interface",
        "registry",
        "atlas",
        "radar",
        "compass",
        "casebook",
        "diagram",
    )
    human_markers = (
        "advocate",
        "analyst",
        "approver",
        "caretaker",
        "client",
        "coordinator",
        "customer",
        "engineer",
        "maintainer",
        "operator",
        "owner",
        "person",
        "observer",
        "reviewer",
        "steward",
        "team",
        "user",
        "verifier",
    )
    if any(marker in lowered for marker in system_markers) and not any(
        marker in lowered for marker in human_markers
    ):
        return False
    return True


def _dedupe_actor_rows(rows: Sequence[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    seen: dict[str, int] = {}
    for role, title, body in rows:
        clean_title, clean_body = _actor_display_parts(title=title, body=body)
        key = _actor_dedupe_key(clean_title)
        if not clean_title:
            continue
        if key in seen:
            existing_index = seen[key]
            existing_role, existing_title, existing_body = result[existing_index]
            if _should_replace_actor_body(
                title=existing_title,
                existing_body=existing_body,
                candidate_body=clean_body,
            ):
                result[existing_index] = (
                    existing_role or sentence(role),
                    existing_title,
                    clean_body,
                )
            continue
        seen[key] = len(result)
        result.append((sentence(role), clean_title, clean_body))

    return result


def _should_replace_actor_body(*, title: str, existing_body: str, candidate_body: str) -> bool:
    if not candidate_body:
        return False
    if _is_default_actor_body(title=title, body=existing_body) and not _is_default_actor_body(
        title=title, body=candidate_body
    ):
        return True
    if _looks_generated_actor_context(existing_body) and not _looks_generated_actor_context(candidate_body):
        return True
    return len(candidate_body) > len(existing_body)


def _is_default_actor_body(*, title: str, body: str) -> bool:
    return _repeat_key(body) == _repeat_key(_default_actor_body(title))


def _looks_generated_actor_context(value: str) -> bool:
    lowered = sentence(value).casefold()
    return lowered.startswith(("build the ", "implement ", "turn the confirmed ")) or any(
        marker in lowered
        for marker in (
            "can fail when the first material path action",
            "cannot support release review unless",
            "review output with validation results",
            "as the state and handoff boundary",
        )
    )


def _actor_display_parts(*, title: object, body: object) -> tuple[str, str]:
    clean_title = participant_title(title) or display_text(title)
    clean_body = participant_body(title=clean_title, body=sanitize_actor_body(body))
    role, role_body = _role_description_parts(clean_title)
    if role:
        clean_title = participant_title(role) or role
        if role_body and (not clean_body or clean_body.casefold() == role.casefold()):
            clean_body = participant_body(title=clean_title, body=_capitalize_first(role_body))
    if not clean_body:
        clean_body = _default_actor_body(clean_title)
    return clean_title, clean_body


def _actor_dedupe_key(value: str) -> str:
    key = participant_key(value)
    return key or sentence(value).casefold().strip(" .")


def _dedupe_text(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = sentence(value)
        key = " ".join(text.casefold().split())
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _repeat_key(value: object) -> str:
    text = sentence(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _proposal_actor_responsibility_map(proposal: Mapping[str, Any]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for item in list_value(proposal.get("backlog")):
        if not isinstance(item, Mapping):
            continue
        intelligence = dict_value(item.get("domain_intelligence"))
        for value in strings(intelligence.get("actors")):
            actor, sep, body = display_text(value).partition(":")
            if sep and actor.strip() and body.strip():
                rows.setdefault(actor.strip().casefold(), body.strip()[:1].upper() + body.strip()[1:])
    return rows


def _owner_responsibility_map(project: Mapping[str, Any]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for value in strings(project.get("owners")):
        text = sentence(value)
        if not text:
            continue
        actor = text
        body = text
        for marker in (" owns ", " is responsible for ", " reviews "):
            before, sep, after = text.partition(marker)
            if sep and before.strip() and after.strip():
                actor = before.strip()
                verb = marker.strip().split()[0].capitalize()
                body = f"{verb} {after.strip()}"
                break
        rows[actor.casefold()] = body
    return rows


def _jobs(
    *,
    backlog: Sequence[Mapping[str, Any]],
    program: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]] = (),
    first_path: str = "",
    project_title: str = "",
    accepted: Mapping[str, Any] | None = None,
) -> list[tuple[str, str, str, str]]:
    rows = []
    component_summaries = _component_summary_map(components)
    created_workstreams = _created_workstream_rows(dict_value(accepted))
    seen_body_keys: set[str] = set()
    for index, item in enumerate(backlog[:6]):
        title = sentence(item.get("title"), "Proposed product slice")
        body = _job_body_text(item=item, title=title, first_path=first_path, component_summaries=component_summaries)
        if _looks_path_echo(body, first_path=first_path) or _repeat_key(body) in seen_body_keys:
            body = _job_fallback_body(title)
        seen_body_keys.add(_repeat_key(body))
        status = job_status_label(item.get("evidence_tier"))
        rows.append(
            (
                short(_project_job_heading(title=title, project_title=project_title), limit=78),
                short(body, limit=145),
                status,
                _workstream_reference(item=item, created=created_workstreams[index] if index < len(created_workstreams) else {}),
            )
        )
    if rows:
        return rows
    return [
        (
            short(
                _project_job_heading(
                    title=sentence(row.get("label"), "Proposed release step"),
                    project_title=project_title,
                ),
                limit=78,
            ),
            short(sentence(row.get("goal"), "Proposed delivery step."), limit=145),
            "Proposed",
            _workstream_reference(item=row, created={}),
        )
        for row in [dict(value) for value in list_value(program.get("waves")) if isinstance(value, Mapping)][:6]
    ]


def _project_job_heading(*, title: str, project_title: str) -> str:
    heading = _polish_heading(title)
    project = _polish_heading(project_title)
    if not project:
        return heading
    compact = re.sub(rf"\b{re.escape(project)}\b", "", heading, flags=re.IGNORECASE)
    compact = re.sub(r"\s+", " ", compact).strip(" -:;,.")
    compact = _polish_heading(compact)
    if compact and compact.casefold() != heading.casefold():
        return compact
    return heading


def _created_workstream_rows(accepted: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    created = dict_value(accepted.get("created"))
    return [dict(row) for row in list_value(created.get("workstreams")) if isinstance(row, Mapping)]


def _workstream_reference(*, item: Mapping[str, Any], created: Mapping[str, Any]) -> str:
    for value in (
        item.get("idea_id"),
        item.get("workstream_id"),
        item.get("backlog_id"),
        item.get("id"),
        created.get("idea_id"),
        created.get("workstream_id"),
        created.get("backlog_id"),
        created.get("id"),
    ):
        token = sentence(value).upper()
        if re.fullmatch(r"B-\d+", token):
            return token
    return ""


def _job_body_text(
    *,
    item: Mapping[str, Any],
    title: str,
    first_path: str,
    component_summaries: Mapping[str, str],
) -> str:
    if _is_program_workstream(title):
        return "Keeps the first release centered on one complete user outcome, with explicit limits and proof before source work starts."
    for value in (item.get("product_view"), item.get("problem"), item.get("recommended_first_slice")):
        text = sentence(value)
        if not text or _looks_path_echo(text, first_path=first_path):
            continue
        text = job_card_summary(text)
        if low_information_job_body(text):
            continue
        if re.search(r"\b\d+[.)]\s+[A-Z]", text):
            compact = summarize_first_path(text)
            if compact and not _looks_path_echo(compact, first_path=first_path):
                return compact
        text = re.sub(r"\bShow how The\b", "Show how the", text)
        text = re.sub(r"\bmaps the first path, The\b", "maps the first path, the", text)
        return text
    component_body = _matched_component_summary(title=title, component_summaries=component_summaries)
    component_body = job_card_summary(component_body)
    if component_body and not low_information_job_body(component_body):
        return component_body
    if title.casefold().startswith("prove "):
        return _job_fallback_body(title)
    if " boundary" in title.casefold():
        return _job_fallback_body(title)
    if " proof" in title.casefold():
        return _job_fallback_body(title)
    return _job_fallback_body(title)


def _job_fallback_body(title: str) -> str:
    clean_title = sentence(title, "This product slice")
    subject = re.sub(r"^(?:prove|define|prepare|establish|govern|shape|guide)\s+", "", clean_title, flags=re.IGNORECASE)
    subject = re.sub(r"\s+(?:boundary|release proof|program)$", "", subject, flags=re.IGNORECASE).strip(" .")
    if not subject:
        subject = clean_title
    lowered = clean_title.casefold()
    if _is_program_workstream(clean_title):
        return "Keeps the first release centered on one complete user outcome, with explicit limits and proof before source work starts."
    if " proof" in lowered:
        return f"Packages reviewer-visible proof for {subject} before the release can move forward."
    if " boundary" in lowered:
        return f"Defines what {subject} owns, receives, produces, and must prove for the first release."
    if lowered.startswith("prove "):
        return f"Turns {subject} into a specific release capability with reviewer-visible evidence."
    return f"Turns {subject} into a concrete product slice with a visible result, a blocked path, and a reviewable explanation."


def _polish_heading(value: str) -> str:
    minor_words = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    words = sentence(value).split()
    polished: list[str] = []
    for index, word in enumerate(words):
        core = word.strip("()[]{}.,;:")
        if index > 0 and core.casefold() in minor_words:
            polished.append(word.replace(core, core.lower(), 1))
        else:
            polished.append(word)
    return " ".join(polished)


def _is_program_workstream(title: str) -> bool:
    lowered = sentence(title).casefold()
    return lowered.startswith(("establish ", "govern ", "guide ", "shape ")) and "program" in lowered


def _component_summary_map(components: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for component in components:
        label = sentence(component.get("label") or component.get("name") or component.get("component_id"))
        body = _component_summary(component)
        if label and body:
            rows[_repeat_key(label)] = body
    return rows


def _matched_component_summary(*, title: str, component_summaries: Mapping[str, str]) -> str:
    title_key = _repeat_key(title)
    for label_key, body in component_summaries.items():
        if label_key and label_key in title_key:
            return body
    return ""


def _component_summary(component: Mapping[str, Any]) -> str:
    text = sentence(component.get("responsibility") or component.get("boundary") or component.get("summary"))
    if not text:
        return ""
    head, sep, tail = text.partition(" owns ")
    if sep and tail.strip():
        owned = tail.strip(" .")
        for prefix in ("performs ", "estimates ", "engraves ", "writes ", "renders ", "captures ", "stores ", "produces "):
            if owned.casefold().startswith(prefix):
                return _capitalize_first(owned).rstrip(".") + "."
        return f"Owns {owned.rstrip('.')}."
    text = re.sub(r"\bShow how The\b", "Show how the", text)
    text = re.sub(r"\bmaps the first path, The\b", "maps the first path, the", text)
    return text


def _known(
    *,
    title: str,
    first_path: str,
    release: str,
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    accepted: bool = False,
) -> list[str]:
    rows = [
        "Product direction accepted for planning." if accepted else "Product direction available for review.",
        f"Release target: {release}.",
    ]
    if sentence(first_path):
        rows.append("First path: summarized in the first-path scenario above.")
    shape = _planned_shape_summary(components=components, diagrams=diagrams)
    if shape:
        rows.append(shape)
    if accepted:
        rows.append("Build trust: still requires implementation evidence and validation.")
    return rows


def _unknown(
    *,
    questions: Sequence[str],
    assumptions: Sequence[str],
    risks: Sequence[str],
    non_goals: Sequence[str],
) -> list[str]:
    rows: list[str] = []
    if questions:
        rows.append(f"Decisions still open: {_join_boundary_values([_boundary_summary_item(row) for row in questions[:2]], total=len(questions))}.")
    if non_goals:
        rows.append(f"Outside first release: {_join_boundary_values([_boundary_summary_item(row) for row in non_goals[:3]], total=len(non_goals))}.")
    if assumptions:
        rows.append(f"Assumptions to confirm: {_join_boundary_values([_boundary_summary_item(row) for row in assumptions[:2]], total=len(assumptions))}.")
    if risks:
        rows.append(f"Build risks to control: {_join_boundary_values(_boundary_risk_labels(risks[:3]), total=len(risks))}.")
    return [tidy_fragment(short(row, limit=155)) for row in rows if row][:6] or ["No explicit unresolved proposal item found."]


def _planned_shape_summary(*, components: Sequence[Mapping[str, Any]], diagrams: Sequence[Mapping[str, Any]]) -> str:
    parts: list[str] = []
    if components:
        noun = "component boundary" if len(components) == 1 else "component boundaries"
        parts.append(f"{len(components)} {noun}")
    if diagrams:
        noun = "review view" if len(diagrams) == 1 else "review views"
        parts.append(f"{len(diagrams)} {noun}")
    if not parts:
        return ""
    return f"Planned shape: {' and '.join(parts)}."


def _join_boundary_values(values: Sequence[str], *, total: int) -> str:
    clean_values = [value.strip(" .") for value in values if sentence(value)]
    if not clean_values:
        return "not specified"
    joined = "; ".join(clean_values)
    remaining = max(0, total - len(clean_values))
    if remaining:
        joined = f"{joined}; other accepted items stay outside this summary"
    return joined


def _boundary_summary_item(value: object) -> str:
    text = sentence(value)
    text = re.sub(r"^(?:Not in the first release|Non-goal|Assumption|Question|Risk)\s*:\s*", "", text, flags=re.IGNORECASE)
    for separator in (". ", ": "):
        head, sep, _tail = text.partition(separator)
        if sep and 12 <= len(head.strip()) <= 62:
            text = head
            break
    for marker in (" stay ", " until ", " before ", " for "):
        head, sep, _tail = _partition_casefold(text, marker)
        if sep and 20 <= len(head.strip()) <= 70:
            text = head
            break
    text = _dashboard_excerpt(text, limit=62)
    text = text.strip(" .")
    return tidy_fragment(text) or "unresolved item"


def _boundary_risk_labels(risks: Sequence[str]) -> list[str]:
    labels: list[str] = []
    used: set[str] = set()
    for risk in risks:
        label = _risk_label(_risk_meaning(risk), used=used)
        used.add(label.casefold())
        labels.append(label)
    return labels


def _claim_evidence(
    *,
    title: str,
    intro: str,
    first_path: str,
    validation: Sequence[str],
    questions: Sequence[str],
    observed: Mapping[str, Any],
    accepted: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    source = sentence(observed.get("source_posture"), "greenfield proposal")
    rows = [
        {"claim": "Project identity", "value": title, "evidence": "user-stated", "freshness": "proposal", "owner": "Product decision owner", "source": source},
        {"claim": "Project explanation", "value": short(intro, limit=130), "evidence": "user-stated", "freshness": "proposal", "owner": "Product decision owner", "source": source},
        {"claim": "First path", "value": "Captured in the first-path scenario section.", "evidence": "inferred", "freshness": "proposal", "owner": "Accepted product direction", "source": source},
        {"claim": "Validation path", "value": short(_proof_answer_body(validation=validation, first_path=first_path), limit=130), "evidence": "needs validation", "freshness": "proposal", "owner": "Implementation plan", "source": source},
        {"claim": "Open questions", "value": str(len(questions)), "evidence": "user-stated", "freshness": "proposal", "owner": "Product decision owner", "source": source},
    ]
    accepted_record = dict_value(accepted or {})
    validation_gate = _accepted_validation_gate(accepted_record)
    if validation_gate:
        rows.insert(
            1,
            {
                "claim": "Accepted product check",
                "value": sentence(validation_gate.get("status"), "unknown"),
                "evidence": "governed",
                "freshness": sentence(accepted_record.get("accepted_at"), "accepted project"),
                "owner": "Product acceptance",
                "source": sentence(accepted_record.get("source_path"), "accepted project source"),
            },
        )
    return rows


def _accepted_validation_gate(accepted: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the accepted-project validation result, including legacy records."""
    gate = dict_value(accepted.get("validation_gate"))
    if gate:
        return gate
    return dict_value(accepted.get("tribunal"))


def _dashboard_risk_source(proposal: Mapping[str, Any], *, release: str) -> Sequence[Any]:
    risks = list_value(proposal.get("risks"))
    if risks and not any(risk_text_has_framework_leak(row) for row in risks):
        return risks
    return build_product_risks_from_proposal(proposal, release=release)


def _risk_items(value: object) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    used: set[str] = set()
    for item in list_value(value)[:4]:
        if not isinstance(item, Mapping):
            continue
        meaning = _risk_meaning(
            item.get("statement")
            or item.get("description")
            or item.get("risk")
            or item.get("trigger")
        )
        if not meaning:
            continue
        title = _dashboard_risk_title(sentence(item.get("title")), meaning=meaning, used=used)
        used.add(title.casefold())
        rows.append({"risk": title, "meaning": meaning})
    return rows


def _dashboard_risk_title(value: str, *, meaning: str, used: set[str]) -> str:
    title = _clean_display_title(value)
    if not title or risk_text_has_framework_leak({"title": title}):
        title = _risk_label(meaning, used=used)
    else:
        title = _title_case(short(title, limit=48))
    return _dedupe_label(title, used=used)


def _risk_classes(risks: Sequence[str]) -> list[dict[str, str]]:
    rows = []
    used: set[str] = set()
    for risk in risks[:4]:
        meaning = _risk_meaning(risk)
        label = _risk_label(meaning, used=used)
        used.add(label.casefold())
        rows.append({"risk": label, "meaning": meaning})
    return rows or [{"risk": "Unvalidated proposal", "meaning": "No implementation proof exists yet."}]


def _risk_meaning(value: object) -> str:
    text = _risk_without_embedded_path(value)
    if text and not text.endswith((".", "!", "?")):
        text += "."
    if len(text) > 220:
        first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
        if len(first_sentence) >= 42:
            return first_sentence
    return short(text, limit=240, fallback="The product has a real-world risk that needs an owner and validation.")


def _risk_label(value: str, *, used: set[str]) -> str:
    lowered = value.casefold()
    checks = [
        (("concentration", "threshold", "limit", "volume", "capped", "bounded"), "Control limits"),
        (("signal", "reading", "calibration", "drift", "measurement", "sample"), "Measurement reliability"),
        (("compliance", "privacy", "security", "jurisdiction", "kyc", "kyb", "aml", "regulated", "legal"), "Compliance boundary"),
        (("integration", "external", "api", "provider", "dependency", "webhook", "connector"), "External dependency"),
        (("owner", "approval", "handoff", "review", "responsibility", "operator"), "Ownership clarity"),
        (("rollback", "retry", "recovery", "blocked", "fail", "fault"), "Recovery path"),
        (("claim", "mislead", "status", "confidence", "trust"), "User trust"),
        (("harm", "damage", "loss", "safety", "unsafe", "hazard"), "Safety boundary"),
    ]
    for needles, label in checks:
        if any(needle in lowered for needle in needles):
            return _dedupe_label(label, used=used)
    return _dedupe_label("Proposal risk", used=used)


def _dedupe_label(label: str, *, used: set[str]) -> str:
    if label.casefold() not in used:
        return label
    return f"Additional {label.casefold()}"
