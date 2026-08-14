"""Classify material Greenfield ambiguity before any candidate files are written."""

from __future__ import annotations

from dataclasses import dataclass
import re

from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_explicit_decision_gap import explicit_decision_gap
from odylith.runtime.domain_intelligence.greenfield_first_path_common import is_noncompleting_action_head
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import explicit_actor_evidence
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import has_visible_object_list_result
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


@dataclass(frozen=True)
class MaterialClarification:
    """One focused user question and the semantic fields its answer must settle."""

    question: str
    required_fields: tuple[str, ...]


_PROOF_RE = re.compile(
    r"\b(?:proof\s+boundar|claim|declare|diagnos|certif|sign[\s-]?off|safe\s+to|observation\s+record\s+only|"
    r"must\s+not\s+state|may\s+make)\b",
    flags=re.IGNORECASE,
)
_VISIBLE_RE = re.compile(
    r"\b(?:see|sees|show|shows|display|displays|receive|receives|view|views|visible\s+result|"
    r"return|returns|get|gets|(?:issu(?:e|es)|releas(?:e|es)|produc(?:e|es))\s+(?:a|an|the|one))\b",
    flags=re.IGNORECASE,
)
_TERMINAL_DELIVERABLE_RE = re.compile(
    r"(?:,|\band\b|\bthen\b|\bfinally\b)\s+"
    r"(?:publish(?:es)?|produc(?:e|es)|issu(?:e|es)|prepar(?:e|es)|generat(?:e|es)|"
    r"export(?:s)?|releas(?:e|es)|sav(?:e|es)|record(?:s)?|creat(?:e|es)|return(?:s)?)\s+"
    r"(?:an?|the|one|its|their|[A-Za-z0-9])\b[^.!?]{1,180}$",
    flags=re.IGNORECASE,
)
_IDENTITY_SOURCE_RE = re.compile(r"\b(?:codes?|identifiers?|ids?|tags?|tokens?)\b", re.IGNORECASE)
_STATE_ACTION_RE = re.compile(
    r"\b(?:check\s*in|checks\s*in|arriv(?:als?|e|es)|admi(?:t|ts|ssion)|present|attendance)\b",
    flags=re.IGNORECASE,
)
_HIGH_CONSEQUENCE_RE = re.compile(
    r"\b(?:child|children|youth|minor|clinical|medical|health|therapy|treatment|infusion|"
    r"safety|legal|financial|public|private|consent|diagnos|certif)\b",
    flags=re.IGNORECASE,
)
def explicit_material_clarification(*, prompt: str, edit_evidence: str = "") -> MaterialClarification | None:
    """Return one source-grounded question for an explicitly unresolved decision."""

    evidence = clean_markdown_text(
        "\n".join(value for value in (prompt, edit_evidence) if str(value or "").strip())
    )
    gap = explicit_decision_gap(evidence)
    if not gap:
        return None
    return MaterialClarification(question=gap.question, required_fields=gap.required_fields)


def material_clarification_for_fields(fields: tuple[str, ...]) -> MaterialClarification:
    """Render the typed materiality gate as the same focused question contract."""

    required_fields = tuple(dict.fromkeys(str(field).strip() for field in fields if str(field).strip()))
    return MaterialClarification(
        question=_material_unknown_question(list(required_fields)),
        required_fields=required_fields,
    )


def _material_unknown_question(labels: list[str]) -> str:
    if len(labels) == 1:
        field_text = labels[0]
    elif len(labels) == 2:
        separator = ", and " if " and " in labels[0].casefold() else " and "
        field_text = f"{labels[0]}{separator}{labels[1]}"
    else:
        field_text = f"{', '.join(labels[:-1])}, and {labels[-1]}"
    return f"Could you specify the {field_text} for this project?"


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
            or has_human_actor_signal(source.first_path)
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
    if not has_explicit_visible_result(source.first_path):
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
    if required_fields == ("first_path",):
        return MaterialClarification(
            question="What should the user complete first, and what result should they see?",
            required_fields=required_fields,
        )
    clauses = [prompts[field] for field in required_fields]
    if len(clauses) == 1:
        body = clauses[0]
    else:
        body = f"{', '.join(clauses[:-1])}, and {clauses[-1]}"
    return MaterialClarification(
        question=f"For the first complete task, {body}?",
        required_fields=required_fields,
    )


def has_explicit_visible_result(first_path: str) -> bool:
    """Recognize an observed result or a terminal deliverable after prior work."""

    text = " ".join(str(first_path or "").split()).strip(" .")
    if not text:
        return False
    if _VISIBLE_RE.search(text) or _TERMINAL_DELIVERABLE_RE.search(text):
        return True
    return has_visible_object_list_result(text)


__all__ = [
    "MaterialClarification",
    "explicit_material_clarification",
    "has_explicit_visible_result",
    "incomplete_path_clarification",
    "material_clarification_for_fields",
]
