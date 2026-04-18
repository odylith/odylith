"""Signals helpers for the Odylith character layer."""

from __future__ import annotations

import re
from typing import Any, Mapping

from odylith.runtime.character.contract import compact_mapping


_DONE_RE = re.compile(r"\b(done|fixed|resolved|cleared|ship|shipped)\b", re.I)
_BROAD_RE = re.compile(r"\b(go deep|everything|whole repo|look around|audit all|fix all|clean up)\b", re.I)
_QUEUE_RE = re.compile(r"\b(next|queued|backlog|compass queue|case queue)\b", re.I)
_DELEGATE_RE = re.compile(r"\b(delegate|subagent|spawn|parallel|use agents|fan.?out)\b", re.I)
_DELEGATION_SAFETY_RE = re.compile(
    r"\b(no|not|without|avoid|prevent|must not|do not|don't|never)\b.{0,80}\b(delegate|subagent|spawn|parallel|use agents|fan.?out)\b"
    r"|\b(delegate|subagent|spawn|parallel|use agents|fan.?out)\b.{0,80}\b(no|not|without|avoid|prevent|must not|do not|don't|never)\b",
    re.I,
)
_VISIBLE_RE = re.compile(r"\b(visible|intervention|observation|proposal|chat ux|rendered)\b", re.I)
_VISIBLE_PROOF_COMMAND_RE = re.compile(r"\b(?:intervention-status|visible-intervention)\b", re.I)
_VISIBLE_CLAIM_RE = re.compile(r"\b(tell|claim|say|report|announce|active|working|works|proven|proof)\b", re.I)
_PUBLIC_SURFACE_RE = re.compile(
    r"\b(public claim|product claim|release claim|readme|release note|release notes|publish|publication)\b"
    r"|\b(shipped and proven|shipped\b.*\bproven|proven\b.*\bshipped)\b",
    re.I,
)
_PUBLIC_CLAIM_ACTION_RE = re.compile(
    r"\b(update|write|edit|publish|announce|claim|say|report|mention|ship|release)\b",
    re.I,
)
_PROOF_EXECUTION_RE = re.compile(
    r"\b(run|execute|validate|benchmark|measure|prove|test|verify)\b.{0,80}\b(proof|benchmark|validator|validation|test)\b"
    r"|\b(proof|benchmark|validator|validation|test)\b.{0,80}\b(run|execute|validate|measure|prove|test|verify)\b",
    re.I,
)
_MODEL_RE = re.compile(
    r"\b(call the model|ask claude|ask codex|provider call|provider calls|live model|host model call|host model calls|model call|model calls|use tokens|burn credits|spend credits)\b",
    re.I,
)
_CREDIT_SAFETY_RE = re.compile(
    r"\b(no|not|without|avoid|prevent|must not|do not|don't|never|zero)\b.{0,80}\b(model|provider|token|credit|credits)\b"
    r"|\b(model|provider|token|credit|credits)\b.{0,80}\b(no|not|without|avoid|prevent|must not|do not|don't|never|zero)\b",
    re.I,
)
_GOVERNED_SURFACE_RE = re.compile(r"\b(radar|registry|atlas|casebook|compass|governed truth|technical plan|release assignment)\b", re.I)
_CLI_OWNED_SURFACE_RE = re.compile(
    r"\b(radar|backlog|casebook|bug capture|compass|release assignment|program wave|atlas|component register|governed truth writer)\b",
    re.I,
)
_MUTATION_RE = re.compile(r"\b(update|write|edit|modify|change|create|add|remove|delete|record|log|append|hand[- ]?edit|by hand)\b", re.I)
_AUTHORING_COMMAND_RE = re.compile(r"\bodylith\s+(backlog|bug|component|atlas|compass|release|program|governance)\b", re.I)
_QUEUE_ADOPTION_RE = re.compile(r"\b(implement|start|pick up|work on|do this|take|adopt|fix|execute)\b", re.I)
_QUEUE_NON_ADOPTION_RE = re.compile(
    r"\b(no|not|without|avoid|prevent|must not|do not|don't|never)\b.{0,80}\b(next|queued|backlog|compass queue|case queue|pick up|adopt|implement)\b"
    r"|\b(next|queued|backlog|compass queue|case queue|pick up|adopt|implement)\b.{0,80}\b(no|not|without|avoid|prevent|must not|do not|don't|never)\b",
    re.I,
)
_SYSTEMIC_RE = re.compile(r"\b(synergy|synergistic|seamless|integrated|end to end|platform|materialized|policy|policies|enforcement|gaps?|friction|drag|robust|reliable|reusable|refactor)\b", re.I)
_VOICE_TEMPLATE_RE = re.compile(r"\b(voice|experience|posture|scripted|template|templati[sz]ed|rigid|fluid|live)\b", re.I)
_LEARNING_RE = re.compile(r"\b(learn|learning|adaptive|improve|better|memory|priors?|feedback)\b", re.I)


def extract_intent_signals(intent: str, *, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    text = str(intent or "").strip()
    lowered = text.lower()
    facts = compact_mapping(evidence)
    governed_surface = bool(_GOVERNED_SURFACE_RE.search(text))
    cli_owned_surface = bool(_CLI_OWNED_SURFACE_RE.search(text))
    mutation_intent = bool(_MUTATION_RE.search(text)) or bool(facts.get("governed_truth_mutation"))
    authoring_command = bool(_AUTHORING_COMMAND_RE.search(text)) or bool(facts.get("using_cli_writer"))
    queue_mention = bool(_QUEUE_RE.search(text))
    queue_non_adoption = bool(_QUEUE_NON_ADOPTION_RE.search(text))
    queue_adoption = (
        bool(_QUEUE_ADOPTION_RE.search(text)) or "what is next" in lowered or "next?" in lowered
    ) and not queue_non_adoption
    visible_terms = bool(_VISIBLE_RE.search(text))
    visible_proof_command = bool(_VISIBLE_PROOF_COMMAND_RE.search(text))
    visible_claim = bool(facts.get("visible_intervention_claim")) or (
        visible_terms and bool(_VISIBLE_CLAIM_RE.search(text)) and not visible_proof_command
    )
    consumer_mutation_risk = bool(facts.get("consumer_lane_product_mutation")) or (
        "consumer" in lowered and "odylith" in lowered and "fix" in lowered
    )
    credit_safety_intent = bool(_CREDIT_SAFETY_RE.search(text))
    credit_risk = bool(facts.get("model_call_requested")) or (
        bool(_MODEL_RE.search(text)) and not credit_safety_intent
    )
    completion_claim = bool(_DONE_RE.search(text) or facts.get("completion_claim"))
    proof_execution_intent = bool(_PROOF_EXECUTION_RE.search(text))
    public_claim_text = bool(_PUBLIC_SURFACE_RE.search(text)) and bool(_PUBLIC_CLAIM_ACTION_RE.search(text))
    benchmark_claim_risk = bool(facts.get("public_claim")) or (
        public_claim_text and not proof_execution_intent
    )
    governed_truth_risk = bool(facts.get("cli_writer_exists")) or (
        cli_owned_surface
        and mutation_intent
        and not authoring_command
        and not bool(facts.get("allowed_hand_authored_surface"))
    )
    delegation_risk = (
        bool(_DELEGATE_RE.search(text)) or bool(facts.get("delegation_requested"))
    ) and not bool(_DELEGATION_SAFETY_RE.search(text))
    features = {
        "ambiguity": bool(_BROAD_RE.search(text)) or len(text.split()) < 6,
        "proof_risk": completion_claim or "proof" in lowered,
        "completion_claim": completion_claim,
        "proof_execution": proof_execution_intent,
        "governed_truth_risk": governed_truth_risk,
        "delegation_risk": delegation_risk,
        "visibility_risk": visible_claim,
        "recurrence": bool(facts.get("prior_failure") or facts.get("recurrence_count")),
        "lane_boundary_risk": "consumer" in lowered or str(facts.get("lane", "")).strip() == "consumer",
        "benchmark_claim_risk": benchmark_claim_risk,
        "urgency": any(token in lowered for token in ("now", "urgent", "asap", "fast", "quick")),
        "credit_risk": credit_risk,
        "queue_risk": queue_mention and queue_adoption and not bool(facts.get("queue_authorized")),
        "systemic_integration_risk": bool(_SYSTEMIC_RE.search(text)),
        "voice_template_risk": bool(_VOICE_TEMPLATE_RE.search(text)),
        "learning_feedback_risk": bool(_LEARNING_RE.search(text)),
    }
    return {
        "text": text,
        "lowered": lowered,
        "facts": facts,
        "governed_surface": governed_surface,
        "cli_owned_surface": cli_owned_surface,
        "mutation_intent": mutation_intent,
        "authoring_command": authoring_command,
        "queue_mention": queue_mention,
        "queue_adoption": queue_adoption,
        "queue_non_adoption": queue_non_adoption,
        "visible_terms": visible_terms,
        "visible_proof_command": visible_proof_command,
        "visible_claim": visible_claim,
        "completion_claim": completion_claim,
        "consumer_mutation_risk": consumer_mutation_risk,
        "credit_safety_intent": credit_safety_intent,
        "credit_risk": credit_risk,
        "proof_execution_intent": proof_execution_intent,
        "features": features,
    }
