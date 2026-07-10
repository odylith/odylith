"""Deterministic Atlas copy for individual Mermaid graph nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract_support import present_verb


_ACTION_RE = re.compile(
    r"\b(action|execute|execution|run|runner|write|create|generate|apply|approve|review|coordinate|release)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GraphNodeCopyContext:
    subject: str
    incoming_sources: str
    outgoing_targets: str
    incoming_conditions: str
    outgoing_conditions: str
    incoming_count: int
    visible_incoming_count: int
    outgoing_count: int
    is_actor: bool
    is_exception: bool
    is_success: bool
    is_action: bool
    is_evidence: bool
    is_input: bool


def describe_node(context: GraphNodeCopyContext) -> str:
    """Return an action-oriented sentence for one graph node."""

    subject = context.subject
    incoming_basis = condition_basis(context.incoming_conditions) if context.incoming_conditions else context.incoming_sources
    outgoing_basis = condition_basis(context.outgoing_conditions)
    subject_be = present_verb(subject, singular="is", plural="are")

    if context.is_actor:
        if context.outgoing_targets:
            return f"{subject} must start this path and supply the action, decision, or review needed by {context.outgoing_targets}."
        return f"{subject} {subject_be} a participant in this path and should have a clear responsibility, input, or result."
    if context.is_exception:
        route = context.incoming_conditions or context.incoming_sources
        if route:
            route_verb = present_verb(route, singular="makes", plural="make")
            stop_verb = present_verb(subject, singular="stops", plural="stop")
            return f"{subject} {stop_verb} normal progress when {route} {route_verb} the next step unsafe or incomplete."
        return f"{subject} {subject_be} the recovery state; work should stay here until the missing proof, owner action, or fault is cleared."
    if context.is_success and context.incoming_count:
        proof = context.incoming_conditions or context.incoming_sources
        if proof:
            return f"{subject} {subject_be} the trusted outcome reached after {proof}; this should mean the diagram's success condition is satisfied."
        return f"{subject} {subject_be} the trusted outcome state for this path."
    if not context.visible_incoming_count and context.outgoing_count:
        if context.outgoing_conditions:
            return (
                f"{subject} {subject_be} the entry responsibility. This step produces the next trusted state based on "
                f"{outgoing_basis}."
            )
        if context.outgoing_targets:
            return f"{subject} {subject_be} the entry responsibility that creates the input needed by {context.outgoing_targets}."
        return f"{subject} {subject_be} the entry responsibility for this diagram."
    if context.outgoing_count > 1:
        decide_verb = present_verb(subject, singular="decides", plural="decide")
        return (
            f"{subject} {decide_verb} between {context.outgoing_targets or 'different outcomes'} based on "
            f"{outgoing_basis or 'the labeled or visual conditions'}."
        )
    if context.is_action and context.outgoing_count:
        perform_verb = present_verb(subject, singular="performs", plural="perform")
        produce_verb = present_verb(subject, singular="produces", plural="produce")
        if incoming_basis:
            return f"{subject} {perform_verb} the bounded action after {incoming_basis} and {produce_verb} evidence for {context.outgoing_targets or 'verification'}."
        return f"{subject} {perform_verb} the bounded action and {produce_verb} evidence for {context.outgoing_targets or 'verification'}."
    if context.incoming_count > 1 and context.outgoing_count:
        join_verb = present_verb(subject, singular="joins", plural="join")
        advance_verb = present_verb(subject, singular="advances", plural="advance")
        basis = incoming_basis or outgoing_basis or "the next condition"
        basis_be = present_verb(basis, singular="is", plural="are")
        return f"{subject} {join_verb} inputs from {context.incoming_sources or 'earlier steps'} and {advance_verb} when {basis} {basis_be} satisfied."
    if context.incoming_count and context.outgoing_count:
        carry_verb = present_verb(subject, singular="carries", plural="carry")
        if context.outgoing_conditions:
            advance_verb = present_verb(subject, singular="advances", plural="advance")
            basis_be = present_verb(outgoing_basis, singular="is", plural="are")
            return f"{subject} {carry_verb} the state forward after {incoming_basis or 'the prerequisite'} and {advance_verb} when {outgoing_basis} {basis_be} satisfied."
        produce_verb = present_verb(subject, singular="produces", plural="produce")
        return f"{subject} {carry_verb} the state forward after {incoming_basis or 'the prerequisite'} and {produce_verb} the input for {context.outgoing_targets or 'the next step'}."
    if context.incoming_count:
        close_verb = present_verb(subject, singular="closes", plural="close")
        return f"{subject} {subject_be} reached after {incoming_basis or 'the incoming condition'} and {close_verb} this path unless another recovery edge is added."
    return f"{subject} {subject_be} a named state or responsibility in this diagram."


def describe_node_role(context: GraphNodeCopyContext) -> str:
    """Return the compact role badge for one graph node."""

    if context.is_actor:
        return "Actor"
    if context.is_exception:
        return "Safety stop"
    if context.is_success and context.incoming_count:
        return "Outcome"
    if not context.visible_incoming_count and context.outgoing_count:
        return "Start"
    if context.is_action:
        return "Action"
    if context.outgoing_count > 1:
        return "Decision"
    if context.is_evidence:
        return "Evidence"
    if context.is_input:
        return "Input"
    if context.incoming_count and not context.outgoing_count:
        return "End"
    return "Step"


def condition_basis(value: str) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    named_results = {
        "closes": "the close condition",
        "compares": "the comparison result",
        "defines": "the defined contract",
        "delivers": "delivery readiness",
        "guards": "the guard decision",
        "proves": "the proof result",
        "records": "the recorded state",
    }
    if text in named_results:
        return named_results[text]
    if text in {"yes", "no", "yes and no", "no and yes"}:
        return "the labeled condition" if " and " not in text else "the labeled conditions"
    return value


def looks_like_action_label(value: str) -> bool:
    text = str(value or "").casefold()
    return bool(_ACTION_RE.search(text) or re.search(r"\b[a-z][a-z0-9-]{2,}ing\b", text))


def looks_like_actor_node(*, node_id: str, primary_label: str) -> bool:
    key = str(node_id or "").casefold()
    if key == "actor" or re.fullmatch(r"actor\d*", key):
        return True
    lowered = str(primary_label or "").casefold()
    tokens = re.findall(r"[a-z][a-z0-9'-]*", lowered)
    if not tokens or len(tokens) > 7:
        return False
    system_tokens = {
        "adapter", "app", "application", "command", "console", "dashboard", "desk", "engine", "form",
        "interface", "intake", "ledger", "model", "platform", "portal", "product", "queue", "register",
        "registry", "service", "store", "surface", "system", "tool", "tracker", "view", "workspace",
    }
    if any(token in system_tokens for token in tokens):
        return False
    if re.match(
        r"^(?:assign|check|choose|collect|compare|create|display|download|enter|export|fix|generate|import|inspect|log|open|prove|record|repair|review|route|save|select|send|show|submit|triage|update|upload|validate|view)\b",
        lowered,
    ):
        return False
    person_tokens = {
        "actor", "actors", "applicant", "applicants", "beneficiary", "beneficiaries", "client", "clients",
        "customer", "customers", "lead", "leads", "operator", "operators", "participant", "participants",
        "performer", "performers", "requester", "requesters", "reviewer", "reviewers", "stakeholder",
        "stakeholders", "user", "users",
    }
    return any(token in person_tokens for token in tokens)
