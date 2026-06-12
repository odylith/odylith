"""Proposal repairs driven by Greenfield post-confirm reviewer lenses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence import greenfield_confirmed_diagrams
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as clean_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


QUALITY_LENS_PROPOSAL_REPAIR_CHECKS = frozenset(
    {
        "complete_first_path",
        "measurable_success",
        "first_release_scope",
        "decision_boundary",
        "state_object",
        "component_topology",
        "atlas_topology",
        "system_boundary",
        "implementation_readiness",
        "proof_boundary",
        "domain_term_coverage",
        "high_risk_assumptions",
        "visible_result",
    }
)
QUALITY_LENS_GATE_ONLY_CHECKS = frozenset({"component_specs", "validation_evidence", "prewrite_safety"})
QUALITY_LENS_REPAIR_OWNER_BY_CHECK = {
    **{check: "proposal_repair" for check in QUALITY_LENS_PROPOSAL_REPAIR_CHECKS},
    **{check: "prewrite_gate" for check in QUALITY_LENS_GATE_ONLY_CHECKS},
}


def repair_proposal_for_quality_lens_gaps(
    proposal: dict[str, Any],
    *,
    quality_lenses: Mapping[str, Any],
    release_selector: str,
) -> bool:
    """Strengthen proposal evidence for failed PM, architecture, engineering, or domain lenses."""

    failed_checks = _failed_check_names(quality_lenses)
    proposal_checks = failed_checks & QUALITY_LENS_PROPOSAL_REPAIR_CHECKS
    if not proposal_checks:
        return False
    changed = False
    if proposal_checks.intersection({"complete_first_path", "state_object", "visible_result"}):
        changed |= _ensure_first_path_contract(proposal)
    if proposal_checks.intersection({"decision_boundary", "high_risk_assumptions", "domain_term_coverage"}):
        changed |= _ensure_decision_boundary(proposal)
        changed |= _carry_assumptions_into_validation(proposal, release_selector=release_selector)
    if proposal_checks.intersection({"measurable_success", "implementation_readiness"}):
        changed |= _ensure_measurable_success(proposal, release_selector=release_selector)
    if proposal_checks.intersection({"system_boundary", "component_topology", "atlas_topology"}):
        changed |= _ensure_system_boundaries(proposal)
        changed |= _ensure_component_topology(proposal)
    if "first_release_scope" in proposal_checks:
        changed |= _ensure_release_scope(proposal, release_selector=release_selector)
    if "atlas_topology" in proposal_checks:
        changed |= _ensure_atlas_topology(proposal)
    if "implementation_readiness" in proposal_checks:
        changed |= _ensure_project_brief_readiness(proposal, release_selector=release_selector)
    if proposal_checks.intersection({"proof_boundary", "visible_result", "domain_term_coverage"}):
        changed |= _ensure_proof_language(proposal, release_selector=release_selector)
    return changed


def quality_lens_repair_owner(check_name: str) -> str:
    """Return the deterministic owner for one reviewer-lens check."""

    return QUALITY_LENS_REPAIR_OWNER_BY_CHECK.get(clean_text(check_name), "")


def _failed_check_names(quality_lenses: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    lenses = quality_lenses.get("lenses")
    if not isinstance(lenses, Mapping):
        return names
    for lens in lenses.values():
        if not isinstance(lens, Mapping):
            continue
        checks = lens.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if isinstance(check, Mapping) and clean_text(check.get("status")).casefold() != "passed":
                name = clean_text(check.get("name"))
                if name:
                    names.add(name)
    return names


def _ensure_first_path_contract(proposal: dict[str, Any]) -> bool:
    intent = _intent(proposal)
    title = completion_text.project_title(proposal)
    changed = False
    if not clean_text(intent.get("state_object")):
        intent["state_object"] = f"{title} state record"
        changed = True
    state = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    if not clean_text(intent.get("first_path")):
        intent["first_path"] = sentence_text(
            (
                f"A representative user can {action}, the product records {state}, "
                f"and the user can {outcome_action} with recovery context."
            ),
            limit=520,
        )
        changed = True
    return changed


def _ensure_decision_boundary(proposal: dict[str, Any]) -> bool:
    intent = _intent(proposal)
    title = completion_text.project_title(proposal)
    state = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    changed = False
    assumptions = proposal.get("assumptions")
    if not isinstance(assumptions, list):
        assumptions = []
        proposal["assumptions"] = assumptions
        changed = True
    existing = {clean_text(row.get("statement")) for row in dict_rows(assumptions)}
    required = [
        (
            "user_intent",
            f"Users can provide the information required to {action} before {title} presents a trusted result.",
        ),
        (
            "odylith_assumption",
            (
                f"{state} must preserve actor, status, result, and recovery context "
                f"when the user needs to {outcome_action}."
            ),
        ),
    ]
    for tier, statement in required:
        sentence = sentence_text(statement, limit=420)
        if sentence in existing:
            continue
        assumptions.append(
            {
                "id": f"A-{len(dict_rows(assumptions)) + 1:03d}",
                "tier": tier,
                "statement": sentence,
                "impact": "Shapes the first-release proof boundary and validation obligations.",
            }
        )
        existing.add(sentence)
        changed = True
    questions = proposal.get("open_questions")
    if not isinstance(questions, list):
        questions = []
        proposal["open_questions"] = questions
        changed = True
    if not dict_rows(questions):
        questions.append(
            {
                "id": "OQ-001",
                "question": sentence_text(
                    (
                        f"Which input, access, or integration boundary must be resolved "
                        f"before {title} implementation starts?"
                    ),
                    limit=360,
                ),
                "impact": "Changes the first release scope, permission model, fixtures, and validation target.",
                "default_if_unanswered": "Use the accepted first-path boundary and deterministic local fixtures.",
            }
        )
        changed = True
    if "human_actors" not in intent and text_values(proposal.get("human_actors")):
        intent["human_actors"] = list(text_values(proposal.get("human_actors")))
        changed = True
    return changed


def _carry_assumptions_into_validation(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    assumptions = [
        clean_text(row.get("statement"))
        for row in dict_rows(proposal.get("assumptions"))
        if clean_text(row.get("statement"))
    ]
    if not assumptions:
        return False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    title = completion_text.project_title(proposal)
    rows = text_values(proposal.get("validation_strategy"))
    additions = [
        sentence_text(
            f"Assumption proof for release {release} checks whether {statement.rstrip('.')}",
            limit=520,
        )
        for statement in assumptions[:3]
    ]
    additions.append(
        sentence_text(
            f"{title} cannot promote until accepted assumptions are visible in validation output and release review.",
            limit=520,
        )
    )
    merged = list(unique_text([*rows, *additions]))
    if list(rows) == merged:
        return False
    proposal["validation_strategy"] = merged
    return True


def _ensure_measurable_success(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    title = completion_text.project_title(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    state = completion_text.state_reference(proposal)
    proof = completion_text.proof_capability_phrase(proposal)
    changed = False
    for index, row in enumerate(dict_rows(proposal.get("backlog")), start=1):
        row_title = clean_text(row.get("title")) or f"{title} workstream {index}"
        metrics = text_values(row.get("success_metrics"))
        additions = [
            sentence_text(f"{row_title} success proof for release {release} covers {proof}.", limit=520),
            sentence_text(
                f"{row_title} result proof confirms the user can {outcome_action} after they {action}.",
                limit=520,
            ),
            sentence_text(
                f"{row_title} blocked-path proof keeps missing input, invalid input, access limits, and recovery context visible.",
                limit=520,
            ),
            sentence_text(
                f"{row_title} evidence proof can reconstruct {state} with actor, status, result, and explanation.",
                limit=520,
            ),
        ]
        merged = list(unique_text([*metrics, *additions]))
        if len(metrics) >= 3 and metrics == merged:
            continue
        row["success_metrics"] = merged[:5]
        changed = True
    return changed


def _ensure_system_boundaries(proposal: dict[str, Any]) -> bool:
    intent = _intent(proposal)
    changed = False
    internal = text_values(intent.get("internal_systems"))
    if len(internal) < 2:
        internal = _component_labels(proposal)[:2] or [
            f"{completion_text.project_title(proposal)} workflow service",
            f"{completion_text.project_title(proposal)} evidence service",
        ]
        if len(internal) == 1:
            internal.append(f"{completion_text.project_title(proposal)} evidence service")
        intent["internal_systems"] = list(unique_text(internal[:2]))
        changed = True
    if "external_systems" not in intent:
        intent["external_systems"] = list(text_values(proposal.get("external_systems")))
        changed = True
    return changed


def _ensure_component_topology(proposal: dict[str, Any]) -> bool:
    components = proposal.get("components")
    if not isinstance(components, list):
        components = []
        proposal["components"] = components
    title = completion_text.project_title(proposal)
    state = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    labels = list(unique_text([*_component_labels(proposal), *text_values(_intent(proposal).get("internal_systems"))]))
    defaults = [
        f"{title} interaction surface",
        f"{title} workflow service",
        f"{title} state service",
        f"{title} proof service",
    ]
    changed = False
    seen_labels = {label.casefold() for label in labels}
    for label in defaults:
        if len(labels) >= 3:
            break
        if label.casefold() in seen_labels:
            continue
        labels.append(label)
        seen_labels.add(label.casefold())
    existing_ids = {clean_text(row.get("component_id")) for row in dict_rows(components)}
    for index, label in enumerate(labels[:3], start=1):
        component_id = slugify(label) or f"component-{index}"
        if component_id in existing_ids:
            continue
        components.append(
            {
                "component_id": _unique_component_id(component_id, existing_ids),
                "label": label,
                "kind": _component_kind(index),
                "intended_path": f"src/{slugify(label) or f'component-{index}'}",
                "responsibility": sentence_text(
                    f"{label} owns the part of {title} that lets a user {action}, tracks {state}, and supports {outcome_action}.",
                    limit=620,
                ),
                "boundary": sentence_text(
                    f"{label} owns its accepted inputs, produced state, validation evidence, recovery context, and local handoff decisions.",
                    limit=520,
                ),
                "interfaces": [
                    sentence_text(
                        f"{label} accepts the facts needed for {action} and returns a result, blocker, or recovery state.",
                        limit=420,
                    )
                ],
                "validation": [
                    sentence_text(
                        f"Validate one successful path, one blocked path, and one recovery path for {label}.",
                        limit=360,
                    )
                ],
                "dependencies": [
                    "Accepted first-path input and the previous product state.",
                    "Release proof review and the next product boundary.",
                ],
                "risks": [
                    sentence_text(
                        f"{label} can mislead users if {outcome} is shown without enough state, evidence, or recovery context.",
                        limit=420,
                    )
                ],
                "release_scope": "first_release",
                "status": "planned",
                "qualification": "candidate",
                "evidence_tier": "user_intent",
            }
        )
        existing_ids.add(component_id)
        changed = True
    for index, row in enumerate(dict_rows(components)):
        if clean_text(row.get("release_scope")):
            continue
        row["release_scope"] = "first_release" if index < 4 else "deferred"
        changed = True
    return changed


def _component_kind(index: int) -> str:
    return ("client", "service", "service", "service")[min(max(index, 1), 4) - 1]


def _unique_component_id(component_id: str, existing_ids: set[str]) -> str:
    candidate = clean_text(component_id)
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{component_id}-{suffix}"
        suffix += 1
    return candidate


def _ensure_release_scope(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    changed = False
    release_plan = proposal.get("release_plan")
    if not isinstance(release_plan, dict):
        release_plan = {}
        proposal["release_plan"] = release_plan
        changed = True
    if clean_text(release_plan.get("selector")) != release:
        release_plan["selector"] = release
        changed = True
    titles = _workstream_titles(proposal)
    target_titles = text_values(release_plan.get("target_workstream_titles"))
    if titles and not target_titles:
        release_plan["target_workstream_titles"] = titles[:3]
        changed = True
    for index, row in enumerate(dict_rows(proposal.get("components"))):
        if clean_text(row.get("release_scope")):
            continue
        row["release_scope"] = "first_release" if index < 4 else "deferred"
        changed = True
    return changed


def _ensure_atlas_topology(proposal: dict[str, Any]) -> bool:
    components = dict_rows(proposal.get("components"))
    if len(components) < 3:
        _ensure_component_topology(proposal)
        components = dict_rows(proposal.get("components"))
    title = completion_text.project_title(proposal)
    base_slug = slugify(title) or "greenfield-project"
    slugs = {
        "context": f"{base_slug}-context",
        "sequence": f"{base_slug}-first-path-sequence",
        "state_evidence": f"{base_slug}-state-evidence",
        "component_boundaries": f"{base_slug}-component-boundaries",
        "ownership": f"{base_slug}-ownership-proof",
        "proof_review": f"{base_slug}-release-proof-review",
    }
    diagrams = greenfield_confirmed_diagrams.confirmed_diagrams(
        label=title,
        components=components,
        diagram_slugs=slugs,
        product_story=clean_text(_intent(proposal).get("product_story")),
        first_path=completion_text.first_path(proposal),
        proof_boundary=completion_text.proof_boundary(proposal),
        state_object=completion_text.state_object(proposal),
        evidence_record=f"{completion_text.state_reference(proposal)} evidence record",
        human_actors=text_values(_intent(proposal).get("human_actors")),
        external_systems=text_values(_intent(proposal).get("external_systems")),
        internal_systems=text_values(_intent(proposal).get("internal_systems")),
        non_goals=text_values(proposal.get("non_goals") or _intent(proposal).get("non_goals")),
        semantic_model=proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else None,
    )
    current = proposal.get("diagrams")
    if isinstance(current, list) and _diagram_rows_render_ready(dict_rows(current)):
        return False
    proposal["diagrams"] = diagrams
    return True


def _diagram_rows_render_ready(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 4:
        return False
    slugs: set[str] = set()
    for row in rows:
        slug = clean_text(row.get("slug"))
        source = clean_text(row.get("mermaid_source") or row.get("source"))
        if not slug or not source or slug in slugs:
            return False
        slugs.add(slug)
    return True


def _ensure_project_brief_readiness(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    brief = proposal.get("project_brief")
    if not isinstance(brief, dict):
        brief = {}
        proposal["project_brief"] = brief
    title = completion_text.project_title(proposal)
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    proof = completion_text.proof_boundary(proposal)
    gates = text_values(brief.get("coding_readiness_gates"))
    required = [
        sentence_text(
            f"The accepted first path is clear enough for a technical plan: a representative user can {action}.",
            limit=420,
        ),
        sentence_text(
            f"Release {release} stays inside the accepted proof boundary: {proof}",
            limit=520,
        ),
        sentence_text(
            f"Implementation can start only after the plan names success, blocked, recovery, access, privacy, and replay proof for {title}.",
            limit=520,
        ),
        sentence_text(
            f"The first workstream must show how the user can {outcome_action} without relying on hidden state or deferred scope.",
            limit=520,
        ),
    ]
    merged = list(unique_text([*gates, *required]))
    changed = False
    if len(gates) < 3 or gates != merged:
        brief["coding_readiness_gates"] = merged[:6]
        changed = True
    options = text_values(brief.get("customization_options"))
    if not options:
        brief["customization_options"] = [
            f"Keep release {release} focused on the accepted first path.",
            "Broaden runtime, integration, or data posture only after the corresponding proof gate is accepted.",
        ]
        changed = True
    if not clean_text(brief.get("purpose")):
        brief["purpose"] = sentence_text(
            f"{title} gives users a clear first release where they can {action} and {outcome_action}.",
            limit=420,
        )
        changed = True
    return changed


def _ensure_proof_language(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    intent = _intent(proposal)
    title = completion_text.project_title(proposal)
    state = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    proof = clean_text(intent.get("proof_boundary"))
    if proof:
        return False
    intent["proof_boundary"] = sentence_text(
        (
            f"Release {release} proof succeeds when a representative user can {action}, "
            f"{title} records {state}, and the product explains {outcome}."
        ),
        limit=620,
    )
    return True


def _intent(proposal: dict[str, Any]) -> dict[str, Any]:
    intent = proposal.get("intent")
    if isinstance(intent, dict):
        return intent
    intent = {}
    proposal["intent"] = intent
    return intent


def _component_labels(proposal: Mapping[str, Any]) -> list[str]:
    return [
        label
        for row in dict_rows(proposal.get("components"))
        if (label := clean_text(row.get("label") or row.get("component_id")))
    ]


def _workstream_titles(proposal: Mapping[str, Any]) -> list[str]:
    return [
        title
        for row in dict_rows(proposal.get("backlog"))
        if (title := clean_text(row.get("title")))
    ]


__all__ = [
    "QUALITY_LENS_GATE_ONLY_CHECKS",
    "QUALITY_LENS_PROPOSAL_REPAIR_CHECKS",
    "QUALITY_LENS_REPAIR_OWNER_BY_CHECK",
    "quality_lens_repair_owner",
    "repair_proposal_for_quality_lens_gaps",
]
