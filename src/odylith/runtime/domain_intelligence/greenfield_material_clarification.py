"""Classify material Greenfield ambiguity before any candidate files are written."""

from __future__ import annotations

from dataclasses import dataclass
import re

from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_first_path_common import is_noncompleting_action_head
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import explicit_actor_evidence


@dataclass(frozen=True)
class MaterialClarification:
    """One focused user question and the semantic fields its answer must settle."""

    question: str
    required_fields: tuple[str, ...]


_EXPLICIT_CONTRADICTION_RE = re.compile(
    r"\b(?:conflict|conflicts|conflicting|contradict(?:s|ory)?|mutually\s+exclusive|"
    r"which\s+.+?\s+is\s+intended|ask\s+which)\b",
    flags=re.IGNORECASE,
)
_UNRESOLVED_RE = re.compile(r"\bunresolved\b", flags=re.IGNORECASE)
_OPPOSING_EVIDENCE_RE = re.compile(
    r"\b(?:one\b[^.!?]{0,240}\banother|either\b[^.!?]{0,160}\bor|"
    r"both\b[^.!?]{0,160}\band|must\b[^.!?]{0,160}\bmust\s+not|"
    r"public\b[^.!?]{0,160}\bprivate|private\b[^.!?]{0,160}\bpublic)\b",
    flags=re.IGNORECASE,
)
_AUDIENCE_RE = re.compile(
    r"\b(?:audience|public|private|who\s+(?:may|can)\s+(?:see|view)|"
    r"visible\s+only|display\s+is\s+for)\b",
    flags=re.IGNORECASE,
)
_PROOF_RE = re.compile(
    r"\b(?:proof\s+boundar|claim|declare|diagnos|certif|safe\s+to|observation\s+record\s+only|"
    r"must\s+not\s+state|may\s+make)\b",
    flags=re.IGNORECASE,
)
_VISIBLE_RE = re.compile(
    r"\b(?:see|sees|show|shows|display|displays|receive|receives|view|views|visible\s+result|"
    r"return|returns|get|gets)\b",
    flags=re.IGNORECASE,
)
_IDENTITY_SOURCE_RE = re.compile(r"\b(?:codes?|identifiers?|ids?|tags?|tokens?)\b", re.IGNORECASE)
_STATE_ACTION_RE = re.compile(
    r"\b(?:check\s*in|checks\s*in|arriv(?:als?|e|es)|admi(?:t|ts|ssion)|present|attendance)\b",
    flags=re.IGNORECASE,
)
_HIGH_CONSEQUENCE_RE = re.compile(
    r"\b(?:child|children|youth|minor|patient|medical|health|safety|legal|financial|"
    r"public|private|consent|diagnos|certif)\b",
    flags=re.IGNORECASE,
)


def explicit_material_clarification(*, prompt: str, edit_evidence: str = "") -> MaterialClarification | None:
    """Return a field-specific clarification for an explicit material contradiction."""

    evidence = "\n".join(value for value in (prompt, edit_evidence) if str(value or "").strip())
    if not _has_explicit_material_conflict(evidence):
        return None
    if _AUDIENCE_RE.search(evidence):
        return MaterialClarification(
            question="Who should be allowed to see the product's visible result?",
            required_fields=("display_audience",),
        )
    if _PROOF_RE.search(evidence):
        return MaterialClarification(
            question="What claim may the visible result make, and what claim must it avoid?",
            required_fields=("proof_boundary",),
        )
    if re.search(r"\b(?:source|dependency)\b", evidence, flags=re.IGNORECASE):
        return MaterialClarification(
            question="Which source should supply the information used by the first complete path?",
            required_fields=("dependency_source",),
        )
    if re.search(r"\b(?:state|status|transition)\b", evidence, flags=re.IGNORECASE):
        return MaterialClarification(
            question="Which state transition should the first complete path record?",
            required_fields=("state_transition",),
        )
    return MaterialClarification(
        question="Which visible result should the first complete path produce?",
        required_fields=("visible_result",),
    )


def _has_explicit_material_conflict(value: str) -> bool:
    return bool(
        _EXPLICIT_CONTRADICTION_RE.search(value)
        or (_UNRESOLVED_RE.search(value) and _OPPOSING_EVIDENCE_RE.search(value))
    )


def incomplete_path_clarification(*, prompt: str, edit_evidence: str = "") -> MaterialClarification:
    """Ask one compact question that names the unresolved parts of a thin path."""

    evidence = edit_evidence.strip() or prompt
    source = prompt_intent_source(evidence)
    model = first_path_model(source.first_path)
    explicit_actor = explicit_actor_evidence(evidence)
    grounded_human_actor = bool(
        source.actor
        and not is_automated_actor(source.actor)
        and (
            has_human_actor_signal(source.actor)
            or explicit_actor.casefold() == source.actor.casefold()
        )
    )
    action_head = model.material_action.split(maxsplit=1)[0] if model.material_action else ""
    if (
        not model.material_action
        or not grounded_human_actor
        or is_noncompleting_action_head(action_head)
    ):
        return MaterialClarification(
            question=(
                "What is the first complete task the product should help a person finish, "
                "and what result should they see?"
            ),
            required_fields=("first_path",),
        )
    fields: list[str] = []
    if not _VISIBLE_RE.search(source.first_path):
        fields.append("visible_result")
    if len(model.steps) < 2 and _STATE_ACTION_RE.search(source.first_path):
        fields.append("state_transition")
    if _IDENTITY_SOURCE_RE.search(source.first_path) and not re.search(
        r"\b(?:comes?\s+from|suppl(?:y|ies)|provid(?:e|es)|read\s+from|imports?)\b",
        evidence,
        flags=re.IGNORECASE,
    ):
        fields.append("dependency_source")
    if _HIGH_CONSEQUENCE_RE.search(evidence) and not _PROOF_RE.search(evidence):
        fields.append("proof_boundary")
    required_fields = tuple(dict.fromkeys(fields)) or ("first_path",)
    prompts = {
        "state_transition": "what state should change",
        "visible_result": "what result should the user see",
        "dependency_source": "which source should supply the needed details",
        "proof_boundary": "what proof or safety boundary should apply",
        "first_path": "what complete task should the user finish",
    }
    clauses = [prompts[field] for field in required_fields]
    if len(clauses) == 1:
        body = clauses[0]
    else:
        body = f"{', '.join(clauses[:-1])}, and {clauses[-1]}"
    return MaterialClarification(
        question=f"For the first complete task, {body}?",
        required_fields=required_fields,
    )


__all__ = ["MaterialClarification", "explicit_material_clarification", "incomplete_path_clarification"]
