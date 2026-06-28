"""Project-intelligence completion for confirmed greenfield repair."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_list
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_text
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import PROJECT_INTELLIGENCE_LAYERS
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text

TextRepairPredicate = Callable[[Any], bool]


def complete_project_intelligence(
    proposal: dict[str, Any],
    *,
    release_selector: str,
    project_title: str,
    first_path: str,
    state_object: str,
    proof_boundary: str,
    text_needs_repair: TextRepairPredicate,
) -> bool:
    intelligence = proposal.get("project_intelligence")
    if not isinstance(intelligence, dict):
        return False
    changed = False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    if not clean_generated_text(intelligence.get("purpose")) or text_needs_repair(intelligence.get("purpose")):
        changed |= set_sentence_text(
            intelligence,
            "purpose",
            (
                f"{project_title} translates the accepted product intent into release {release} records "
                "that keep the user outcome, product state, participants, and risks connected."
            ),
        )
    if not clean_generated_text(intelligence.get("coding_posture")) or text_needs_repair(intelligence.get("coding_posture")):
        changed |= set_sentence_text(
            intelligence,
            "coding_posture",
            (
                f"Implementation should start with the smallest proofable slice for {first_path}, "
                "then expand only when validation shows the product outcome is still clear."
            ),
        )
    changed |= _repair_rows(
        intelligence,
        "control_surface_summary",
        _control_rows(
            project_title=project_title,
            first_path=first_path,
            state_object=state_object,
            proof_boundary=proof_boundary,
        ),
        minimum=5,
        text_needs_repair=text_needs_repair,
    )
    changed |= _repair_rows(
        intelligence,
        "customization_flow",
        _flow_rows(project_title=project_title, first_path=first_path, state_object=state_object),
        minimum=4,
        text_needs_repair=text_needs_repair,
    )
    defaults = _layer_defaults(
        project_title=project_title,
        release=release,
        first_path=first_path,
        state_object=state_object,
        proof_boundary=proof_boundary,
    )
    for key in PROJECT_INTELLIGENCE_LAYERS:
        minimum = 3 if key in {"intent", "ontology", "operators", "validation_obligations", "topology", "artifacts"} else 2
        changed |= _repair_rows(
            intelligence,
            key,
            defaults.get(key, ()),
            minimum=minimum,
            text_needs_repair=text_needs_repair,
        )
    return changed


def _repair_rows(
    intelligence: dict[str, Any],
    key: str,
    defaults: Sequence[str],
    *,
    minimum: int,
    text_needs_repair: TextRepairPredicate,
) -> bool:
    existing = list(text_values(intelligence.get(key)))
    clean_existing = [value for value in existing if not text_needs_repair(value)]
    if len(clean_existing) >= minimum and clean_existing == existing:
        return False
    rows = list(unique_text([*clean_existing, *defaults]))
    if len(rows) < minimum:
        rows.extend(
            f"{key.replace('_', ' ').title()} requirement {index} preserves accepted state, evidence, risk, and release proof."
            for index in range(len(rows) + 1, minimum + 1)
        )
    return set_sentence_list(intelligence, key, rows[: max(minimum, len(clean_existing))])


def _control_rows(
    *,
    project_title: str,
    first_path: str,
    state_object: str,
    proof_boundary: str,
) -> tuple[str, ...]:
    return (
        f"{project_title} must keep the first user path visible and understandable: {first_path}",
        f"{project_title} must show which product state changed and why: {state_object}",
        f"{project_title} must keep blockers, explanations, and decisions understandable before release readiness.",
        f"{project_title} must keep access, privacy, audit, retention, recovery, and safety responsibilities explicit.",
        f"{project_title} must block promotion when the product cannot satisfy the accepted outcome: {proof_boundary}",
    )


def _flow_rows(*, project_title: str, first_path: str, state_object: str) -> tuple[str, ...]:
    return (
        f"Capture the accepted user intent for {project_title} before writing governed records.",
        f"Create the smallest release slice that exercises the first path: {first_path}",
        f"Record {state_object} with current status, owner, result, and recovery path.",
        "Refresh workstream, component, diagram, release, and project-view records only after proposal gates pass.",
    )


def _layer_defaults(
    *,
    project_title: str,
    release: str,
    first_path: str,
    state_object: str,
    proof_boundary: str,
) -> dict[str, tuple[str, ...]]:
    return {
        "intent": (
            f"{project_title} exists to make the first user path usable and understandable: {first_path}",
            f"Release {release} stays focused on {state_object}",
            "Deferred variants remain outside scope until their own outcome and validation are explicit.",
        ),
        "scope": (
            f"Release {release} includes the first path, its state changes, and the user-visible result.",
            "Broader workflows, optional variants, and unproved automations stay outside the first release.",
        ),
        "ontology": (
            f"State object: {state_object}",
            "Actor records identify who initiated, reviewed, changed, blocked, or recovered product state.",
            "Review records identify the input, timestamp, status, outcome, and result explanation.",
        ),
        "state": (
            f"{state_object} must expose current status, owner, result, and recovery path.",
            "Blocked, invalid, missing, stale, or disputed states must be visible before release readiness.",
        ),
        "operators": (
            "Task initiators start the accepted first path and need clear feedback when state changes.",
            "Reviewers or owners evaluate evidence, risks, blocked states, and release readiness.",
            "Administrators or maintainers manage access, recovery, audit, and operational boundaries.",
        ),
        "constraints": (
            f"The first release cannot exceed the accepted product promise: {proof_boundary}",
            "Generated records must stay grammatical, specific, non-duplicative, and tied to accepted intent.",
        ),
        "source_of_truth_map": (
            "Accepted intent is the product truth for scope, first path, actors, risks, and proof.",
            "Component records own local implementation truth for state, inputs, outputs, and recovery behavior.",
            "Release evidence owns proof truth for validation output, blocked paths, and promotion decisions.",
        ),
        "evidence": (
            "Success evidence shows the accepted path running from input to visible outcome.",
            "Replay evidence reconstructs state with actor, timestamp, status, and outcome.",
            "Blocked-path evidence proves missing input, invalid state, access failure, or absent proof stops readiness.",
        ),
        "decisions": (
            f"Release {release} can promote only when validation satisfies the accepted product promise.",
            "Deferred scope, unresolved risk, and failed proof must remain visible in governed records.",
        ),
        "assumptions": (
            "Users can identify the accepted first path and the state they expect to change.",
            "The release team can collect enough evidence to prove success, replay, and blocked paths.",
        ),
        "topology": (
            "User-facing surfaces collect accepted inputs, show current state, and expose blockers.",
            "Service or workflow components transform accepted inputs into validated outputs and evidence.",
            "Governance surfaces preserve release proof, component boundaries, diagrams, and traceability.",
        ),
        "invariants": (
            "Every state change keeps an actor, source, timestamp, status, and evidence reference.",
            "Every component keeps its owned state separate from adjacent ownership boundaries.",
        ),
        "risks": (
            f"{project_title} can mislead users if state changes without clear explanation and recovery behavior.",
            "Governed records become unsafe when generated prose is vague, repetitive, clipped, or malformed.",
        ),
        "validation_obligations": (
            f"Validate success for the accepted first path: {first_path}",
            "Validate blocked paths for missing input, invalid state, access failure, privacy risk, and absent evidence.",
            f"Validate release proof against the accepted product promise: {proof_boundary}",
        ),
        "artifacts": (
            "Workstream records state the work to build and why it matters to users.",
            "Component records state ownership, contracts, dependencies, proof, and failure modes.",
            "Diagram records state architecture views, related components, evidence, and refresh ownership.",
        ),
        "owners": (
            "Product owners preserve accepted intent, release scope, user value, and risk evidence.",
            "Engineering owners preserve component contracts, validation output, and implementation evidence.",
        ),
        "execution_memory": (
            "Confirmed intent, repair decisions, validation output, and release proof remain attached to the create.",
            "Future work reuses accepted state, component ownership, and evidence obligations instead of restarting.",
        ),
        "metrics": (
            "Success rate tracks whether the accepted path reaches the intended visible outcome.",
            "Readiness quality tracks proof completeness, blocked-path handling, replayability, and evidence clarity.",
        ),
        "change_model": (
            "Changes are safe when they preserve state ownership, proof evidence, access control, and release scope.",
            "Changes are unsafe when they blur component boundaries or weaken validation obligations.",
        ),
        "invalidation_rules": (
            "Invalidate readiness when required input, evidence, access, replay, or proof output is missing.",
            "Invalidate generated records when prose is malformed, repetitive, interchangeable, or detached from intent.",
        ),
        "conflict_model": (
            "Resolve conflicts by preferring accepted intent, explicit state ownership, and release-review proof.",
            "Escalate conflicts when two components claim the same state, decision, or source of truth.",
        ),
        "transfer_priors": (
            "Carry forward only domain-neutral proof, state, component, and validation patterns.",
            "Do not copy facts from unrelated projects into the current product records.",
        ),
    }


__all__ = ["complete_project_intelligence"]
