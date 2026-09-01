"""Exact Project dashboard projection for model-authored Greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    GreenfieldAuthoredSemanticsError,
    component_responsibility_relations_from_intent,
    first_path_context_relations_from_intent,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    build_project_handoff_step_contract,
)
from odylith.runtime.project_intelligence.product_story_contract import (
    PRODUCT_STORY_CARD_SLOTS,
)


def build_authored_greenfield_payload(
    *,
    proposal: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Project already-authored facts without deriving meaning from their prose."""

    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield dashboard requires the model-authored projection origin"
        )
    intent = _required_mapping(proposal, "intent")
    relations = first_path_relations_from_intent(intent)
    context_relations = first_path_context_relations_from_intent(intent)
    component_relations = component_responsibility_relations_from_intent(intent)
    if not relations:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield dashboard requires validated model-authored first-path relations"
        )

    title = _required_text(intent, "title")
    product_story = _required_text(intent, "product_story")
    first_path = _required_text(intent, "first_path")
    proof_boundary = _required_text(intent, "proof_boundary")
    human_actors = _text_values(intent.get("human_actors"))
    internal_systems = _text_values(intent.get("internal_systems"))
    external_systems = _text_values(intent.get("external_systems"))
    non_goals = _text_values(intent.get("non_goals"))
    operational_constraints = _text_values(intent.get("operational_constraints"))
    evidence_requirements = _text_values(intent.get("evidence_requirements"))
    success_metrics = _text_values(intent.get("success_metrics"))
    visible_result = _required_relation_text(relations[-1], "visible_result_quote")
    event_quotes = [_required_relation_text(row, "event_quote") for row in relations]

    release_plan = _mapping(proposal.get("release_plan"))
    observed = _mapping(proposal.get("observed_source"))
    accepted = _mapping(proposal.get("_accepted_project"))
    accepted_project = bool(accepted)
    backlog = _mapping_rows(proposal.get("backlog"))
    components = _mapping_rows(proposal.get("components"))
    diagrams = _mapping_rows(proposal.get("diagrams"))
    release = _first_text(release_plan, "label", "selector") or "first proposed release"
    validation = _statement_values(proposal.get("validation_strategy"))
    assumptions = _statement_values(
        proposal.get("assumptions"),
        keys=("statement", "assumption"),
    )
    questions = _statement_values(
        proposal.get("open_questions"),
        keys=("question", "statement"),
    )
    risk_items = _authored_risk_rows(proposal.get("risks"))
    actors = authored_actor_rows(human_actors=human_actors, relations=relations)
    jobs = _job_rows(backlog=backlog, accepted=accepted)
    governance_titles = _governance_titles(
        backlog=backlog,
        diagrams=diagrams,
        accepted=accepted,
    )
    source_launch = _source_launch(
        title=title,
        first_path=first_path,
        proof_boundary=proof_boundary,
        visible_result=visible_result,
        event_quotes=event_quotes,
        components=components,
        jobs=jobs,
        excluded_scope=_unique([*operational_constraints, *non_goals]),
        context=_mapping(proposal.get("_source_launch") or proposal.get("source_launch")),
    )
    open_items = _unique([*questions, *assumptions])
    known = _unique([product_story, first_path, visible_result, proof_boundary])
    unknown = open_items
    sections = ["product_story"]
    if actors:
        sections.append("participants")
    if risk_items:
        sections.append("risks")
    if jobs:
        sections.append("jobs")
    sections.append("next")

    return {
        "eyebrow": "Project type: greenfield",
        "title": title,
        "intro": product_story,
        "chips": [
            "greenfield",
            "accepted greenfield project" if accepted_project else "greenfield proposal",
            "model-authored typed intent",
        ],
        "focus_label": "Accepted focus" if accepted_project else "Proposed focus",
        "focus": first_path,
        "open_label": "Open questions",
        "open": open_items or ["No authored open question."],
        "product_story_title": "Product Story",
        "product_story_note": "",
        "product_story": _product_story(
            title=title,
            product_story=product_story,
            problem=_first_text(intent, "problem") or product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
            visible_result=visible_result,
            human_actors=human_actors,
            components=components,
            external_systems=external_systems,
            non_goals=non_goals,
            event_quotes=event_quotes,
            actors=actors,
        ),
        "answers": [],
        "risk_title": "Risks",
        "risk_note": "Only risks explicitly present in the model-authored proposal appear here.",
        "risk_items": risk_items,
        "scenario": [
            "Model-authored first path",
            title,
            first_path,
            "The ordered event facts below are the validated authored path.",
            "\n".join(event_quotes),
        ],
        "scenario_details": [
            ("First path", first_path),
            ("Visible result", visible_result),
            ("Proof boundary", proof_boundary),
        ],
        "actors": actors,
        "participants": actors,
        "participants_title": "Who participates?",
        "participants_note": "Human actors typed in the model-authored product intent.",
        "jobs": jobs,
        "jobs_title": f"What is proposed for {release}?",
        "jobs_note": "Model-authored workstreams allocated to the first release.",
        "current": (
            "The model-authored product direction is accepted; implementation evidence does not exist yet."
            if accepted_project
            else "The model-authored product direction is proposed; implementation evidence does not exist yet."
        ),
        "desired": visible_result,
        "question": "What should move next?",
        "recommendation": (
            "Open the first implementation plan from the accepted authored package."
            if accepted_project
            else "Review and either accept or revise the authored package."
        ),
        "options": [
            ("A", "Accept proposed path", "Publish the sealed authored transaction."),
            ("B", "Revise evidence", "Add source evidence and rebuild the authored transaction."),
            ("C", "Reject proposal", "Write no project records."),
        ],
        "host_handoff_title": (
            source_launch["title"] if accepted_project else "How to continue in the host chat"
        ),
        "host_handoff_note": (
            source_launch["note"]
            if accepted_project
            else "Use the hash-bound proposal rail to confirm, edit, or reject this authored package."
        ),
        "host_handoff_steps": (
            source_launch["steps"]
            if accepted_project
            else ["Open the canonical proposal rail in the same host chat."]
        ),
        "host_handoff_prompts": (
            source_launch["prompts"]
            if accepted_project
            else [
                {
                    "label": "Open proposal rail",
                    "when": "Use this before any project records are written.",
                    "prompt": "Show the sealed Greenfield proposal and its CONFIRM, EDIT, and REJECT commands.",
                    "result": "The host shows the only transaction decision rail.",
                    "stop": "Stop before any write until one hash-bound command is chosen.",
                }
            ]
        ),
        "projection": {
            "refreshed_at": "proposal time",
            "origin": AUTHORED_PROJECTION_ORIGIN,
            "maturity": "accepted greenfield direction" if accepted_project else "greenfield proposal",
            "work_mode": "orienting",
            "topology_profile": "proposal-first",
        },
        "claim_evidence": _claim_evidence(
            title=title,
            product_story=product_story,
            first_path=first_path,
            visible_result=visible_result,
            proof_boundary=proof_boundary,
            source=_first_text(observed, "source_posture") or "model-authored product intent",
        ),
        "artifact_coverage": list(governance_titles),
        "topology_spine": _unique([*internal_systems, *external_systems]),
        "contradictions": ["No source-backed implementation state exists yet."],
        "delta": ["This projection begins from the model-authored product intent."],
        "risk_classes": risk_items,
        "audience_emphasis": list(human_actors),
        "degraded_state": [
            "Implementation claims remain unavailable until source and validation evidence exist."
        ],
        "known": known,
        "unknown": unknown,
        "confidence": "Medium",
        "blockers": [(item, "Open", "authored intent") for item in unknown[:4]],
        "sections": sections,
        "work_state_kicker": "Status now",
        "state_title": "Where does this stand?",
        "state_note": "Model-authored direction is separate from source-backed implementation.",
        "current_state_label": "Current state",
        "desired_state_label": "Desired state",
        "next_title": "Start source creation" if accepted_project else "What should move next?",
        "next_note": (
            "Start with the first implementation plan from the accepted authored package."
            if accepted_project
            else "No implementation starts until the sealed proposal is accepted."
        ),
        "governance_titles": governance_titles,
        "sources": {
            "proposal": _first_text(accepted, "source_path")
            or str(Path(repo_root) / "odylith/runtime/source/accepted-project.v1.json")
        },
        "authored_facts": {
            "title": title,
            "product_story": product_story,
            "first_path": first_path,
            "proof_boundary": proof_boundary,
            "visible_result": visible_result,
            "human_actors": list(human_actors),
            "internal_systems": list(internal_systems),
            "external_systems": list(external_systems),
            "non_goals": list(non_goals),
            "operational_constraints": list(operational_constraints),
            "evidence_requirements": list(evidence_requirements),
            "success_metrics": list(success_metrics),
            "first_path_relations": [dict(row) for row in relations],
            "first_path_context_relations": [dict(row) for row in context_relations],
            "component_responsibility_relations": [dict(row) for row in component_relations],
            "validation_strategy": validation,
        },
    }


def _product_story(
    *,
    title: str,
    product_story: str,
    problem: str,
    first_path: str,
    proof_boundary: str,
    visible_result: str,
    human_actors: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    external_systems: Sequence[str],
    non_goals: Sequence[str],
    event_quotes: Sequence[str],
    actors: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    capabilities = authored_component_capabilities(components)
    bodies = {
        "User Problem": problem,
        "First Path": first_path,
        "Product Boundary": authored_product_boundary(
            components=components,
            external_systems=external_systems,
            non_goals=non_goals,
        ),
        "Owned Capabilities": "; ".join(capabilities),
        "Proof": proof_boundary,
    }
    return {
        "headline": title,
        "standfirst": "",
        "paragraphs": [product_story, *event_quotes],
        "supporting_records": [],
        "release_contract": [
            {"label": label, "semantic_slot": slot, "body": bodies[label]}
            for label, slot in PRODUCT_STORY_CARD_SLOTS
        ],
        "actors": [
            {"role": "human", "title": actor, "body": _actor_body(actor, actors)}
            for actor in human_actors
        ],
        "visible_result": visible_result,
    }


def authored_actor_rows(
    *,
    human_actors: Sequence[str],
    relations: Sequence[Mapping[str, Any]],
) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for actor in human_actors:
        events = [
            _required_relation_text(row, "event_quote")
            for row in relations
            if row.get("actor_kind") == "human" and row.get("actor_fact_quote") == actor
        ]
        rows.append(
            (
                "Human actor",
                actor,
                "\n".join(events) or "Named in the model-authored product intent.",
            )
        )
    return rows


def authored_component_capabilities(
    components: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Return exact component label/responsibility pairs for the capability card."""

    rows: list[str] = []
    for component in components:
        label = _required_text(component, "label")
        responsibility = _required_text(component, "responsibility")
        row = f"{label}: {responsibility}"
        if row not in rows:
            rows.append(row)
    if not rows:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield dashboard requires an authored component capability"
        )
    return tuple(rows)


def authored_product_boundary(
    *,
    components: Sequence[Mapping[str, Any]],
    external_systems: Sequence[str],
    non_goals: Sequence[str],
) -> str:
    """Render exact ownership, external, and exclusion facts as one boundary card."""

    labels = [_required_text(component, "label") for component in components]
    if not labels:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield dashboard requires an authored product boundary"
        )
    rows = [f"Product-owned systems: {'; '.join(labels)}."]
    if external_systems:
        rows.append(f"External systems: {'; '.join(external_systems)}.")
    if non_goals:
        rows.append(f"Excluded from the first release: {'; '.join(non_goals)}.")
    return " ".join(rows)


def _actor_body(actor: str, rows: Sequence[tuple[str, str, str]]) -> str:
    for _role, title, body in rows:
        if title == actor:
            return body
    return "Named in the model-authored product intent."


def _job_rows(
    *,
    backlog: Sequence[Mapping[str, Any]],
    accepted: Mapping[str, Any],
) -> list[tuple[str, str, str, str]]:
    created = _mapping(accepted.get("created"))
    created_rows = _mapping_rows(created.get("workstreams"))
    rows: list[tuple[str, str, str, str]] = []
    for index, item in enumerate(backlog[:6]):
        created_row = created_rows[index] if index < len(created_rows) else {}
        title = _first_text(item, "title", "name") or "Authored workstream"
        body = _first_text(
            item,
            "product_view",
            "problem",
            "recommended_first_slice",
        ) or title
        reference = _first_text(
            item,
            "idea_id",
            "workstream_id",
            "backlog_id",
            "id",
        ) or _first_text(
            created_row,
            "idea_id",
            "workstream_id",
            "backlog_id",
            "id",
        )
        rows.append(
            (
                title,
                body,
                _first_text(item, "evidence_tier") or "user_intent",
                reference,
            )
        )
    return rows


def _authored_risk_rows(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _sequence(value):
        if isinstance(item, Mapping):
            title = _first_text(item, "title", "risk") or "Authored risk"
            meaning = _first_text(item, "statement", "description", "risk", "trigger")
        elif isinstance(item, str):
            title = "Authored risk"
            meaning = item
        else:
            continue
        if meaning:
            rows.append({"risk": title, "meaning": meaning})
    return rows


def _claim_evidence(
    *,
    title: str,
    product_story: str,
    first_path: str,
    visible_result: str,
    proof_boundary: str,
    source: str,
) -> list[dict[str, str]]:
    values = (
        ("Project identity", title),
        ("Product story", product_story),
        ("First path", first_path),
        ("Visible result", visible_result),
        ("Proof boundary", proof_boundary),
    )
    return [
        {
            "claim": claim,
            "value": value,
            "evidence": "model-authored typed intent",
            "freshness": "proposal",
            "owner": "Product decision owner",
            "source": source,
        }
        for claim, value in values
    ]


def _source_launch(
    *,
    title: str,
    first_path: str,
    proof_boundary: str,
    visible_result: str,
    event_quotes: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    jobs: Sequence[tuple[str, str, str, str]],
    excluded_scope: Sequence[str],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    event_sequence = " | ".join(event_quotes)
    component_ids = [
        value
        for row in components
        if (value := _first_text(row, "component_id", "id"))
    ]
    job_ids = [row[3] for row in jobs if len(row) >= 4 and row[3]]
    target = _first_text(context, "start_workstream_id", "project_workstream_id")
    verification_commands = _text_values(context.get("verification_commands"))
    component_text = ", ".join(component_ids) or "the authored component boundary"
    job_text = ", ".join(job_ids) or target or "the authored first workstream"
    prompts = [
        {
            "step_id": "choose_language",
            "label": "Choose implementation language",
            "when": "Use this before creating the first source-editable plan.",
            "prompt": (
                f"Choose and record the implementation language and runtime for {title}. "
                f"Preserve this model-authored first path exactly: {first_path}"
            ),
            "result": "The implementation runtime is explicit before source planning.",
            "stop": "Stop after the language and runtime are recorded.",
        },
        {
            "step_id": "create_plan",
            "label": "Open first implementation plan",
            "when": "Use this after the implementation runtime is explicit.",
            "prompt": (
                f"Create the first implementation plan for {title} and {job_text}. "
                f"Preserve these ordered typed events exactly: {event_sequence}"
            ),
            "result": "The first source boundary and its proof obligations are planned.",
            "stop": "Stop before source edits until the plan is accepted.",
        },
        {
            "step_id": "build_slice",
            "label": "Implement first runnable slice",
            "when": "Use this only after the first implementation plan is accepted.",
            "prompt": (
                f"Implement the smallest runnable slice for {title}. Keep component IDs {component_text}. "
                f"Preserve the authored first path exactly: {first_path}"
            ),
            "result": "The smallest authored path exists as runnable source.",
            "stop": "Stop when the authored path is runnable and no excluded scope was added.",
        },
        {
            "step_id": "prove_behavior",
            "label": "Run authored proof",
            "when": "Use this after the first runnable slice exists.",
            "prompt": (
                f"Validate {title} against this authored proof boundary: {proof_boundary}. "
                f"Confirm this terminal visible result exactly: {visible_result}. "
                "Run every verification command bound to this typed handoff step."
            ),
            "verification_commands": list(verification_commands),
            "result": "The authored path has reviewer-visible validation evidence.",
            "stop": "Stop if the proof boundary or terminal visible result is not satisfied.",
        },
        {
            "step_id": "refresh_governance",
            "label": "Refresh governed records",
            "when": "Use this only after the authored proof passes.",
            "prompt": (
                f"Refresh governed project records for {title}. Preserve component IDs {component_text} "
                f"and workstream IDs {job_text}."
            ),
            "result": "Governed records reflect the validated source implementation.",
            "stop": "Stop after refreshed records validate against the implemented source.",
        },
    ]
    workstream_refs = _unique([*job_ids, target])
    for row in prompts:
        row["contract"] = build_project_handoff_step_contract(
            step_id=str(row["step_id"]),
            project_title=title,
            accepted_first_path=first_path,
            first_release_workstream_refs=workstream_refs,
            proof_boundary=proof_boundary,
            visible_result=visible_result,
            excluded_scope=excluded_scope,
            component_refs=component_ids,
            verification_commands=verification_commands,
        )
    return {
        "title": "First source creation sequence",
        "note": "This sequence carries the validated model-authored facts into source work without reinterpreting them.",
        "steps": [row["label"] for row in prompts],
        "prompts": prompts,
    }


def _governance_titles(
    *,
    backlog: Sequence[Mapping[str, Any]],
    diagrams: Sequence[Mapping[str, Any]],
    accepted: Mapping[str, Any],
) -> dict[str, str]:
    titles: dict[str, str] = {}
    created = _mapping(accepted.get("created"))
    created_workstreams = _mapping_rows(created.get("workstreams"))
    created_diagrams = _sequence(created.get("diagrams"))
    for index, row in enumerate(backlog):
        created_row = created_workstreams[index] if index < len(created_workstreams) else {}
        reference = _first_text(row, "idea_id", "workstream_id", "id") or _first_text(
            created_row,
            "idea_id",
            "workstream_id",
            "id",
        )
        title = _first_text(row, "title", "name") or _first_text(created_row, "title", "name")
        if reference and title:
            titles[reference] = title
    for index, row in enumerate(diagrams):
        created_value = created_diagrams[index] if index < len(created_diagrams) else None
        created_row = created_value if isinstance(created_value, Mapping) else {}
        created_reference = created_value if isinstance(created_value, str) else ""
        reference = _first_text(row, "diagram_id", "id") or _first_text(
            created_row,
            "diagram_id",
            "id",
        ) or created_reference
        title = _first_text(row, "title", "name", "slug") or _first_text(
            created_row,
            "title",
            "name",
        )
        if reference and title:
            titles[reference] = title
    return titles


def _required_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    result = value.get(key)
    if not isinstance(result, Mapping):
        raise GreenfieldAuthoredSemanticsError(
            f"Greenfield dashboard requires authored {key}"
        )
    return result


def _required_text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise GreenfieldAuthoredSemanticsError(
            f"Greenfield dashboard requires authored {key}"
        )
    return result


def _required_relation_text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise GreenfieldAuthoredSemanticsError(
            f"Greenfield dashboard requires authored relation {key}"
        )
    return result


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return list(value)


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in _sequence(value) if isinstance(row, Mapping)]


def _text_values(value: Any) -> list[str]:
    return [row for row in _sequence(value) if isinstance(row, str) and row]


def _statement_values(
    value: Any,
    *,
    keys: Sequence[str] = ("statement", "validation", "goal"),
) -> list[str]:
    rows: list[str] = []
    for item in _sequence(value):
        if isinstance(item, str):
            text = item
        elif isinstance(item, Mapping):
            text = _first_text(item, *keys)
        else:
            text = ""
        if text and text not in rows:
            rows.append(text)
    return rows


def _first_text(value: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        result = value.get(key)
        if isinstance(result, str) and result:
            return result
    return ""


def _unique(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        if value and value not in rows:
            rows.append(value)
    return rows


__all__ = [
    "authored_actor_rows",
    "authored_component_capabilities",
    "authored_product_boundary",
    "build_authored_greenfield_payload",
]
