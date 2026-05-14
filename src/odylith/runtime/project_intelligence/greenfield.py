"""Greenfield-origin Project tab adapter."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.artifact_enrichment import domain_graph_from_workstream
from odylith.runtime.domain_intelligence.artifact_enrichment import tribunal_actor_projection
from odylith.runtime.project_intelligence.product_story import build_greenfield_product_story, project_intent_line
from odylith.runtime.project_intelligence.utils import dict_value, list_value, sentence, short, strings


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
    for path in (
        Path(repo_root) / ".odylith" / "runtime" / "greenfield" / "active-proposal.v1.json",
        Path(repo_root) / "odylith-greenfield-proposal.json",
        Path(repo_root) / "greenfield-proposal.json",
    ):
        proposal = _proposal_from_file(path)
        if proposal:
            return proposal
    return {}


def build_greenfield_payload(*, proposal: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    """Compile a proposal-origin Project page without pretending source proof exists."""

    intent = dict_value(proposal.get("intent"))
    project = dict_value(proposal.get("project_intelligence"))
    program = dict_value(proposal.get("program"))
    release_plan = dict_value(proposal.get("release_plan"))
    observed = dict_value(proposal.get("observed_source"))
    backlog = [dict(row) for row in list_value(proposal.get("backlog")) if isinstance(row, Mapping)]
    components = [dict(row) for row in list_value(proposal.get("components")) if isinstance(row, Mapping)]
    diagrams = [dict(row) for row in list_value(proposal.get("diagrams")) if isinstance(row, Mapping)]
    assumptions = _text_rows(proposal.get("assumptions"), keys=("statement", "assumption"))
    questions = _text_rows(proposal.get("open_questions"), keys=("question", "statement"))
    risks = _text_rows(proposal.get("risks"), keys=("statement", "risk", "trigger"))
    validation = _text_rows(proposal.get("validation_strategy"))
    non_goals = _non_goal_rows(project)
    accepted = dict_value(proposal.get("_accepted_project"))
    raw_title = sentence(intent.get("title"), "Greenfield project")
    lens = _lens(proposal=proposal, backlog=backlog, components=components)
    release = sentence(release_plan.get("label") or release_plan.get("selector"), "first proposed release")
    first_path = _first_path(program=program, release_plan=release_plan, backlog=backlog)
    intro = _project_intro(title=raw_title, intent=intent, project=project)
    title = _display_title(raw_title=raw_title, intro=intro)
    purpose = _change_body(project=project, intro=intro, first_path=first_path)
    focus = sentence(release_plan.get("strategy")) or sentence(first_path) or "Review the proposed first path before implementation starts."
    open_items = [*questions[:3], *risks[:2]] or ["No open proposal question found."]
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
    known = _known(title=title, first_path=first_path, release=release, components=components, diagrams=diagrams)
    unknown = _unknown(questions=questions, assumptions=assumptions, risks=risks, non_goals=non_goals)
    actors = _actors(project, proposal=proposal)
    jobs = _jobs(backlog=backlog, program=program)
    product_story = build_greenfield_product_story(
        title=title,
        intro=intro,
        project=project,
        first_path=first_path,
        release=release,
        release_plan=release_plan,
        accepted=accepted,
        backlog=backlog,
        components=components,
        diagrams=diagrams,
        actors=actors,
    )
    sections = ["product_story", "scenario"]
    if actors:
        sections.append("participants")
    if jobs:
        sections.append("jobs")
    sections.extend(["claim_evidence", "boundary", "state", "next", "proof"])
    if risks:
        sections.insert(-3, "posture")
    return {
        "eyebrow": f"Project type: {lens}",
        "title": title,
        "intro": intro,
        "chips": [lens, "greenfield proposal", evidence_state],
        "focus_label": f"Proposed {title} focus",
        "focus": focus,
        "open_label": f"Open {title} questions",
        "open": open_items[:5],
        "product_story_title": "Product Story",
        "product_story_note": "",
        "product_story": product_story,
        "answers": [
            (f"Who uses {title}?", _owner_title(project), _owner_body(project)),
            (f"What changes in {title}?", _state_change(project, first_path=first_path), purpose),
            (f"What matters now for {title}?", "Accept or revise the project shape", "Implementation should wait until assumptions, first path, and proof gates are reviewed."),
            (f"What risk matters for {title}?", _risk_title(risks), risks[0] if risks else "No explicit proposal risk found."),
            (f"What proves {title}?", _proof_title(validation), validation[0] if validation else "Validation path must be confirmed before source-backed claims."),
        ],
        "scenario": [
            "Proposed first path",
            title,
            short(first_path, limit=78, fallback="First proposed path"),
            "Evidence is user-stated or inferred; source validation has not happened yet.",
            _scenario_body(project=project, first_path=first_path, validation=validation),
        ],
        "scenario_title": "Proposed first-path scenario",
        "scenario_note": "Generated from the greenfield proposal; this is not yet source-backed implementation evidence.",
        "actors": actors,
        "participants": actors,
        "participants_title": f"Who participates in {title}?",
        "participants_note": "Actors and owners come from the proposed project record.",
        "jobs": jobs,
        "jobs_title": f"What is proposed for {release}?",
        "jobs_note": "Jobs come from proposal workstreams and wave order.",
        "boundary_title": "What is inside the proposed first boundary?",
        "boundary_note": "This boundary is proposed; it must be accepted or revised before implementation.",
        "included_label": "Proposed first path",
        "excluded_label": "Still unresolved",
        "included": _included(first_path=first_path, components=components, diagrams=diagrams, validation=validation),
        "excluded": unknown,
        "current": f"{title} is a greenfield proposal with {observed.get('source_posture', 'unknown source posture')}; claims are not source-backed implementation evidence yet.",
        "desired": "Accepted project direction with first path, component boundary, topology, and validation obligations ready for a technical plan.",
        "question": f"Should {title} be accepted as the first project shape?",
        "recommendation": "Review and either accept or revise the proposed first path before coding starts.",
        "options": [
            ("A", "Accept proposed path", "Write governed project records, then open the first technical plan."),
            ("B", "Revise assumptions", "Update open questions, proof bar, owner, or first path before any write."),
            ("C", "Stop proposal", "Do not create project records until the intent is clearer."),
        ],
        "next": [
            "Accept or revise project shape",
            "Review assumptions, unresolved questions, first path, and validation obligations before implementation.",
            "Operator",
            "Accepted proposal or revised prompt",
            "Direction choices reviewed",
            "Implementation starts from unstable assumptions",
        ],
        "host_handoff_title": "How to continue in the host chat",
        "host_handoff_note": (
            "Use one of these prompts in Codex, Claude, or another Odylith host. Odylith should handle the proposal "
            "workflow; the operator should not inspect or edit proposal JSON by hand."
        ),
        "host_handoff_steps": [
            "Review the Product Story, first path, open questions, and risks on this page.",
            "Choose Accept, Revise, or Reject below.",
            "Paste the chosen prompt into the same host chat that runs Odylith.",
            "Refresh the dashboard after Odylith finishes to see the accepted or revised project state.",
        ],
        "host_handoff_prompts": _host_handoff_prompts(title=title),
        "projection": {
            "refreshed_at": "proposal time",
            "origin": "greenfield proposal",
            "maturity": "greenfield or thin evidence",
            "work_mode": "orienting",
            "topology_profile": "proposal-first",
        },
        "claim_evidence": claim_evidence,
        "artifact_coverage": [],
        "topology_spine": [],
        "contradictions": ["No source-backed implementation state exists yet for this greenfield proposal."],
        "delta": ["No previous source-backed project state is available; this projection starts from proposal intent."],
        "risk_classes": _risk_classes(risks),
        "validation_posture": [
            {
                "posture": "Project shape",
                "level": "Medium",
                "meaning": "The proposal is clear enough to review, but it is still intent and planning evidence.",
            },
            {
                "posture": "Implementation readiness",
                "level": "Low",
                "meaning": "Do not start building until the first path, proof bar, and risk controls are accepted.",
            },
        ],
        "audience_emphasis": [],
        "degraded_state": ["Greenfield claims are not source-backed until accepted records, implementation, and validation exist."],
        "known": known,
        "unknown": unknown,
        "confidence": "Medium",
        "blockers": [(item, "Open", "proposal") for item in unknown[:4]],
        "sections": sections,
        "claim_evidence_title": f"What can be trusted about {title} right now?",
        "claim_evidence_note": "This separates accepted project intent from proposal assumptions and proof that still has to be earned.",
        "trust_title": f"What is still not source-backed for {title}?",
        "trust_note": "Greenfield uncertainty stays visible until accepted project records and validation exist.",
        "delta_label": "Proposal state",
        "contradictions_label": "Source-backed gap",
        "degraded_label": "Validation gap",
        "posture_title": f"What must be controlled before {title} moves forward?",
        "posture_note": "Takeaway: this is safe to review as a proposal, not safe to treat as working behavior until proof gates and risk controls are accepted.",
        "validation_label": "Current gate",
        "risk_label": "Risks to control first",
        "work_state_kicker": f"{title} status now",
        "state_title": f"Where does {title} stand?",
        "state_note": "This separates proposed truth from source-backed implementation.",
        "current_state_label": "Current state",
        "desired_state_label": "Desired state",
        "next_title": f"What should move next for {title}?",
        "next_note": "No implementation should start until the proposed path is accepted or revised.",
        "next_owner_label": "Owner",
        "next_output_label": "Expected output",
        "next_precondition_label": "Precondition",
        "next_risk_label": "Risk if delayed",
        "proof_title": f"What is known and unproven for {title}?",
        "proof_note": "Known items are proposal facts; unproven items are questions, assumptions, and risks.",
        "known_label": "Known from proposal",
        "unknown_label": "Unproven before build",
        "confidence_label": "Confidence",
        "governance_titles": _governance_titles(backlog=backlog, diagrams=diagrams, accepted=accepted),
        "sources": {
            "proposal": sentence(accepted.get("source_path"))
            or str(Path(repo_root) / ".odylith/runtime/greenfield/active-proposal.v1.json")
        },
    }


def _accepted_proposal(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    mode = str(value.get("mode", "")).strip()
    if "greenfield" in mode and isinstance(value.get("project_intelligence"), Mapping):
        return dict(value)
    for key in ("greenfield_proposal", "accepted_proposal", "proposal"):
        nested = value.get(key)
        if isinstance(nested, Mapping) and "greenfield" in str(nested.get("mode", "")).strip():
            return dict(nested)
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
            "tribunal": dict_value(raw.get("tribunal")),
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


def _first_path(*, program: Mapping[str, Any], release_plan: Mapping[str, Any], backlog: Sequence[Mapping[str, Any]]) -> str:
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
        project_intent_line(project, "project objective"),
        project_intent_line(project, "user or stakeholder outcome"),
        sentence(intent.get("summary")),
        short(project.get("purpose"), limit=220),
    ]
    for candidate in candidates:
        cleaned = _clean_objective_sentence(candidate)
        if cleaned and not _looks_meta_project_line(cleaned):
            return cleaned
    display = _title_case(_project_name_candidate(title) or sentence(title, "Project"))
    return f"{display} is a proposed product; the first path, actors, systems, and proof boundary need operator confirmation."


def _looks_meta_project_line(value: str) -> bool:
    lowered = sentence(value).casefold()
    if not lowered:
        return False
    return any(
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
    ) or lowered.startswith(("make ", "capture ", "turn the operator request into"))

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
    return sentence(raw_title, "Greenfield project")


def _project_name_candidate(value: str) -> str:
    text = _strip_prompt_directives(sentence(value))
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
    return _title_head(text)


def _title_head(value: str) -> str:
    text = sentence(value)
    that_head, that_sep, that_tail = _partition_casefold(text, " that ")
    if that_sep and _is_generic_product_noun(that_head):
        tail_head = _clause_head(that_tail)
        if tail_head:
            return f"{that_head.strip()} that {tail_head}".strip(" .")
    for marker in (" that ", " around ", " before ", " with ", " by ", " to "):
        head, sep, tail = _partition_casefold(text, marker)
        if sep:
            if marker == " with " and _should_keep_with_clause(head, tail):
                return f"{head.strip(' .')} with {_clause_head(tail)}".strip(" .")
            return head.strip(" .")
    return text.strip(" .")


def _should_keep_with_clause(head: str, tail: str) -> bool:
    """Keep short product names specific when their differentiator follows ``with``."""

    head_words = sentence(head).split()
    tail_head = _clause_head(tail)
    if not tail_head or len(head_words) > 3:
        return False
    generic_terms = {"app", "application", "platform", "product", "robot", "service", "site", "system", "tool"}
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
        "robot",
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
    tokens: list[str] = []
    for token in value.replace("-", " ").split():
        matched = next((word for word in preserve if token.lower() == word.lower()), "")
        tokens.append(matched or token[:1].upper() + token[1:].lower())
    return " ".join(tokens)


def _owner_title(project: Mapping[str, Any]) -> str:
    owners = strings(project.get("owners"))
    if not owners:
        return "Operator"
    head = owners[0].split(":", 1)[0]
    for marker in (" owns ", " is responsible for ", " reviews "):
        before, sep, _after = head.partition(marker)
        if sep and before.strip():
            head = before
            break
    return short(head, limit=70)


def _owner_body(project: Mapping[str, Any]) -> str:
    owners = strings(project.get("owners"))
    if not owners:
        return "Owner is user-stated or still unresolved."
    text = owners[0]
    for marker in (" owns ", " is responsible for ", " reviews "):
        before, sep, after = text.partition(marker)
        if sep and after.strip():
            verb = marker.strip().split()[0].capitalize()
            return short(f"{verb} {after.strip()}", limit=135)
    return short(text, limit=135)


def _state_change(project: Mapping[str, Any], *, first_path: str) -> str:
    first_path_text = sentence(first_path)
    if first_path_text:
        natural = _first_path_title(first_path_text)
        if natural:
            return natural
        before, sep, _after = first_path_text.partition(" through ")
        if sep and before.strip():
            return short(before.strip(), limit=80)
        return short(first_path_text, limit=80)
    rows = strings(project.get("state"))
    for row in rows:
        if row.lower().startswith("desired state"):
            return short(row.split(":", 1)[-1], limit=80)
    return "Proposal becomes accepted project direction"


def _first_path_title(value: str) -> str:
    text = sentence(value).strip(" .")
    lowered = text.casefold()
    if lowered.startswith("prove one "):
        text = "One " + text[len("Prove one ") :]
    elif lowered.startswith("prove a "):
        text = "A " + text[len("Prove a ") :]
    elif lowered.startswith("prove an "):
        text = "An " + text[len("Prove an ") :]
    else:
        return ""
    for marker in (" through ", " with ", " before ", " so ", " while "):
        head, sep, _tail = text.partition(marker)
        if sep and head.strip():
            text = head.strip()
            break
    from_head, sep, _tail = text.partition(" from ")
    if sep and from_head.strip():
        text = from_head.strip()
    return short(text, limit=80)


def _change_body(*, project: Mapping[str, Any], intro: str, first_path: str) -> str:
    path = sentence(first_path)
    if path:
        return short(path, limit=180)
    clean_purpose = _clean_project_purpose(project.get("purpose"))
    if clean_purpose:
        return short(clean_purpose, limit=180)
    return short(intro, limit=180)


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


def _risk_title(risks: Sequence[str]) -> str:
    if not risks:
        return "Unvalidated assumptions"
    return _risk_label(_risk_meaning(risks[0]), used=set())


def _host_handoff_prompts(*, title: str) -> list[dict[str, str]]:
    project_name = short(title, limit=90, fallback="this project")
    return [
        {
            "label": "Accept it",
            "when": "Use this when the story, first path, actors, open questions, and proof boundary look right.",
            "prompt": f"Odylith, apply this greenfield proposal for {project_name} as-is and write the governed project records.",
            "result": "Writes the accepted project record, Radar workstreams, Registry components, Atlas diagrams, release boundary, and proof gates.",
        },
        {
            "label": "Revise it",
            "when": "Use this when the project is close, but the first path, actor, system boundary, proof bar, or exclusions need correction.",
            "prompt": (
                "Odylith, revise this greenfield proposal before applying it: change <what is wrong> to <what should be true>. "
                "Keep the product story, first path, components, risks, and proof gates aligned with the correction. "
                "Do not write governed records until I confirm."
            ),
            "result": "Produces a revised proposal for review without mutating governed records.",
        },
        {
            "label": "Reject it",
            "when": "Use this when the interpretation is the wrong product or the user intent is not clear enough.",
            "prompt": f"Odylith, reject this greenfield proposal for {project_name}. Do not write governed records.",
            "result": "Leaves the repo in proposal or blank state so a new intent can be supplied.",
        },
    ]


def _proof_title(validation: Sequence[str]) -> str:
    text = sentence(validation[0] if validation else "")
    if "implementation-backed behavior proof" in text.casefold():
        return "First-slice behavior proof"
    return short(text, limit=70, fallback="First validation path")


def _scenario_body(*, project: Mapping[str, Any], first_path: str, validation: Sequence[str]) -> str:
    purpose = short(
        _clean_project_purpose(project.get("purpose")) or _clean_objective_sentence(project_intent_line(project, "project objective")),
        limit=260,
        fallback="The proposal names the first project shape.",
    )
    proof = validation[0] if validation else "validation obligations must be confirmed before source-backed claims."
    path = sentence(first_path).rstrip(".")
    proof_text = short(proof, limit=220).rstrip(".")
    return f"{purpose} First path: {path}. Proof needed: {proof_text}."


def _actors(project: Mapping[str, Any], *, proposal: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    project_rows = _project_actor_rows(project=project, proposal=proposal)
    if project_rows:
        return project_rows[:6]

    accepted = dict_value(proposal.get("_accepted_project"))
    tribunal = dict_value(accepted.get("tribunal"))
    visible_actors = [dict(row) for row in list_value(tribunal.get("visible_actors")) if isinstance(row, Mapping)]
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
        title = sentence(head, "Operator")
        if _is_project_actor_label(title):
            rows.append(("", title, short(body or value, limit=145)))
    return _dedupe_actor_rows(rows)[:6] or [
        ("", "Project operator", "Reviews and accepts or revises the proposal before implementation.")
    ]


def _project_actor_rows(
    *,
    project: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> list[tuple[str, str, str]]:
    """Return Project-facing actors before internal Tribunal role projections."""

    rows: list[tuple[str, str, str]] = []
    for value in [*strings(project.get("owners")), *strings(project.get("operators"))]:
        title, body = _actor_title_and_body(value)
        if _is_project_actor_label(title):
            rows.append(("", title, short(body, limit=145)))
    for item in list_value(proposal.get("backlog")):
        if not isinstance(item, Mapping):
            continue
        intelligence = dict_value(item.get("domain_intelligence"))
        for value in strings(intelligence.get("actors")):
            title, body = _actor_title_and_body(value)
            if _is_project_actor_label(title):
                rows.append(("", title, short(body, limit=145)))
    return _dedupe_actor_rows(rows)


def _actor_title_and_body(value: object) -> tuple[str, str]:
    text = sentence(value)
    if not text:
        return "", ""
    head, sep, body = text.partition(":")
    title = sentence(head)
    detail = sentence(body if sep else text)
    if not detail or detail.casefold() == title.casefold():
        detail = _default_actor_body(title)
    elif detail:
        detail = detail[:1].upper() + detail[1:]
    return title, detail


def _default_actor_body(title: str) -> str:
    lowered = title.casefold()
    if any(token in lowered for token in ("owner", "advocate", "user", "customer", "merchant", "patient", "client")):
        return "Receives the value of the first project path and decides whether it is acceptable."
    if any(token in lowered for token in ("operator", "coordinator", "caretaker", "maintainer")):
        return "Moves the first path through the real workflow and handles day-to-day exceptions."
    if any(token in lowered for token in ("risk", "safety", "compliance", "privacy")):
        return "Owns the harm, policy, or operational exposure that can block the first release."
    if any(token in lowered for token in ("proof", "evidence", "quality", "validation", "reviewer")):
        return "Decides whether the evidence is strong enough to trust the first path."
    if any(token in lowered for token in ("build", "implementation", "engineer", "developer")):
        return "Owns the implementation path after the project direction is accepted."
    return "Participates in the first project path and keeps its responsibility explicit."


def _is_project_actor_label(value: str) -> bool:
    label = sentence(value)
    if not label:
        return False
    if len(label.split()) > 6:
        return False
    lowered = label.casefold().replace("_", " ")
    if lowered in {
        "actor",
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
        "merchant",
        "operator",
        "owner",
        "patient",
        "person",
        "reviewer",
        "scientist",
        "team",
        "user",
    )
    if any(marker in lowered for marker in system_markers) and not any(
        marker in lowered for marker in human_markers
    ):
        return False
    return True


def _dedupe_actor_rows(rows: Sequence[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for role, title, body in rows:
        clean_title = sentence(title)
        key = clean_title.casefold()
        if not clean_title or key in seen:
            continue
        seen.add(key)
        result.append((sentence(role), clean_title, sentence(body)))
    return result


def _proposal_actor_responsibility_map(proposal: Mapping[str, Any]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for item in list_value(proposal.get("backlog")):
        if not isinstance(item, Mapping):
            continue
        intelligence = dict_value(item.get("domain_intelligence"))
        for value in strings(intelligence.get("actors")):
            actor, sep, body = sentence(value).partition(":")
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


def _jobs(*, backlog: Sequence[Mapping[str, Any]], program: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    rows = []
    for item in backlog[:6]:
        title = sentence(item.get("title"), "Proposed workstream")
        body = sentence(item.get("recommended_first_slice") or item.get("product_view") or item.get("problem"), "Proposal workstream.")
        status = sentence(item.get("evidence_tier"), "proposal")
        rows.append((short(title, limit=78), short(body, limit=145), status))
    if rows:
        return rows
    return [
        (
            short(sentence(row.get("label"), "Proposed wave"), limit=78),
            short(sentence(row.get("goal"), "Proposed delivery wave."), limit=145),
            "proposal",
        )
        for row in [dict(value) for value in list_value(program.get("waves")) if isinstance(value, Mapping)][:6]
    ]


def _included(*, first_path: str, components: Sequence[Mapping[str, Any]], diagrams: Sequence[Mapping[str, Any]], validation: Sequence[str]) -> list[str]:
    rows = [f"First path: {first_path}"]
    rows.extend(f"Component: {sentence(item.get('label') or item.get('component_id'), 'planned component')}" for item in components[:3])
    rows.extend(f"Architecture view: {sentence(item.get('title') or item.get('slug'), 'planned diagram')}" for item in diagrams[:2])
    rows.extend(f"Validation: {item}" for item in validation[:2])
    return [short(row, limit=150) for row in rows if sentence(row)][:6]


def _known(*, title: str, first_path: str, release: str, components: Sequence[Mapping[str, Any]], diagrams: Sequence[Mapping[str, Any]]) -> list[str]:
    clean_path = sentence(first_path).rstrip(".")
    return [
        f"Project intent: {title}.",
        f"First proposed path: {clean_path}.",
        f"Release target: {release}.",
        f"Planned components: {len(components)}.",
        f"Planned architecture views: {len(diagrams)}.",
    ]


def _unknown(
    *,
    questions: Sequence[str],
    assumptions: Sequence[str],
    risks: Sequence[str],
    non_goals: Sequence[str],
) -> list[str]:
    rows = [*questions[:2], *non_goals[:2], *assumptions[:2], *risks[:2]]
    return [short(row, limit=150) for row in rows if row][:6] or ["No explicit unresolved proposal item found."]


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
        {"claim": "Project identity", "value": title, "evidence": "user-stated", "freshness": "proposal", "owner": "Operator", "source": source},
        {"claim": "Project explanation", "value": short(intro, limit=130), "evidence": "user-stated", "freshness": "proposal", "owner": "Operator", "source": source},
        {"claim": "First path", "value": short(first_path, limit=130), "evidence": "inferred", "freshness": "proposal", "owner": "Proposal record", "source": source},
        {"claim": "Validation path", "value": short(validation[0] if validation else "Validation path unresolved", limit=130), "evidence": "needs validation", "freshness": "proposal", "owner": "Technical plan", "source": source},
        {"claim": "Open questions", "value": str(len(questions)), "evidence": "user-stated", "freshness": "proposal", "owner": "Operator", "source": source},
    ]
    accepted_record = dict_value(accepted or {})
    tribunal = dict_value(accepted_record.get("tribunal"))
    if tribunal:
        rows.insert(
            1,
            {
                "claim": "Greenfield Tribunal",
                "value": sentence(tribunal.get("status"), "unknown"),
                "evidence": "governed",
                "freshness": sentence(accepted_record.get("accepted_at"), "accepted project"),
                "owner": "Tribunal",
                "source": sentence(accepted_record.get("source_path"), "accepted project source"),
            },
        )
    return rows


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
    text = sentence(value)
    if text and not text.endswith((".", "!", "?")):
        text += "."
    return short(text, limit=190, fallback="The proposal has a risk that needs an owner and proof gate.")


def _risk_label(value: str, *, used: set[str]) -> str:
    lowered = value.casefold()
    checks = [
        (("electricity", "unattended", "household", "environment"), "Operating environment"),
        (("pump", "motor", "actuation", "robot", "autonomous", "automation", "unattended", "electricity"), "Physical operation safety"),
        (("dose", "dosing", "concentration", "threshold", "limit", "volume", "capped", "bounded"), "Control limits"),
        (("sensor", "signal", "reading", "calibration", "drift", "measurement", "sample"), "Measurement reliability"),
        (("custody", "treasury", "funding", "payment", "repayment", "settlement", "ledger", "capital", "credit", "lender", "liquidity"), "Money movement"),
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
