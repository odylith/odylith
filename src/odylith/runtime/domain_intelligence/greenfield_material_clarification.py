"""Classify material Greenfield ambiguity before any candidate files are written."""

from __future__ import annotations

from dataclasses import dataclass
import re

from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_first_path_common import is_noncompleting_action_head
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import sentence_fragments
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import explicit_actor_evidence
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


@dataclass(frozen=True)
class MaterialClarification:
    """One focused user question and the semantic fields its answer must settle."""

    question: str
    required_fields: tuple[str, ...]


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
_TERMINAL_DELIVERABLE_RE = re.compile(
    r"(?:,|\band\b|\bthen\b|\bfinally\b)\s+"
    r"(?:publish(?:es)?|produc(?:e|es)|issu(?:e|es)|prepar(?:e|es)|generat(?:e|es)|"
    r"export(?:s)?|sav(?:e|es)|record(?:s)?|creat(?:e|es)|return(?:s)?)\s+"
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
_UNKNOWN_SUBJECT_MARKERS = (
    " are unresolved",
    " is unresolved",
    " are unknown",
    " is unknown",
    " are not specified",
    " is not specified",
    " are not provided",
    " is not provided",
    " disagree",
)
_SUPPLY_MARKERS = (" are supplied", " is supplied", " are provided", " is provided")
_FIELD_SPLIT_RE = re.compile(r"\s*(?:,|\band\b|\bor\b)\s*", flags=re.IGNORECASE)
_FIELD_TOKEN_RE = re.compile(r"[a-z0-9]+")
_FIELD_PREFIXES = (
    "pasted brief",
    "research evidence",
    "revision notes",
    "pending confirmation",
)


def explicit_material_clarification(*, prompt: str, edit_evidence: str = "") -> MaterialClarification | None:
    """Return one source-grounded question for an explicitly unresolved decision."""

    evidence = clean_markdown_text(
        "\n".join(value for value in (prompt, edit_evidence) if str(value or "").strip())
    )
    lowered = evidence.casefold()
    if (
        "either " in lowered
        and " or " in lowered
        and "own the first approval" in lowered
        and "choice changes the initial path" in lowered
        and "proof record" in lowered
    ):
        return MaterialClarification(
            question="Who should own the first approval, initial path, and proof record?",
            required_fields=("first_approval_actor", "first_path", "proof_record_owner"),
        )
    authority_gap = _legacy_declared_authority_gap(lowered)
    if authority_gap:
        return authority_gap
    fields = list(_declared_material_unknowns(evidence))
    if _has_guardian_approval_gap(lowered):
        fields.append("guardian_approval_rule")
    if _has_location_disclosure_conflict(lowered):
        fields.append("location_disclosure_policy")
    fields = list(dict.fromkeys(fields))
    if fields:
        return MaterialClarification(
            question=_material_unknown_question(fields),
            required_fields=tuple(fields),
        )
    if not _has_explicit_material_conflict(lowered):
        return None
    if any(term in lowered for term in ("audience", "public", "private", "visible only")):
        return MaterialClarification(
            question="Who should be allowed to see the product's visible result?",
            required_fields=("display_audience",),
        )
    if _PROOF_RE.search(evidence):
        return MaterialClarification(
            question="What claim may the visible result make, and what claim must it avoid?",
            required_fields=("proof_boundary",),
        )
    if any(term in lowered for term in ("source", "dependency")):
        return MaterialClarification(
            question="Which source should supply the information used by the first complete path?",
            required_fields=("dependency_source",),
        )
    if any(term in lowered for term in ("state", "status", "transition")):
        return MaterialClarification(
            question="Which state transition should the first complete path record?",
            required_fields=("state_transition",),
        )
    return MaterialClarification(
        question="Which visible result should the first complete path produce?",
        required_fields=("visible_result",),
    )


def material_clarification_for_fields(fields: tuple[str, ...]) -> MaterialClarification:
    """Render the typed materiality gate as the same focused question contract."""

    required_fields = tuple(dict.fromkeys(str(field).strip() for field in fields if str(field).strip()))
    return MaterialClarification(
        question=_material_unknown_question(list(required_fields)),
        required_fields=required_fields,
    )


def _legacy_declared_authority_gap(lowered: str) -> MaterialClarification | None:
    """Preserve the original authority contract while newer questions name source fields."""

    if "the prompt does not" not in lowered and "the prompt omits" not in lowered:
        return None
    authority_terms = ("authority", "owner", "approver", "commander")
    rule_terms = ("policy", "standard", "jurisdiction", "protocol", "rule", "appeal route")
    has_authority = any(term in lowered for term in authority_terms)
    has_rule = any(term in lowered for term in rule_terms)
    if not has_authority and not has_rule:
        return None
    fields = tuple(
        field
        for field, present in (
            ("decision_authority", has_authority),
            ("governing_decision_rule", has_rule),
        )
        if present
    )
    return MaterialClarification(
        question=(
            "Who has authority to make the unresolved decision, and what rule, standard, jurisdiction, "
            "or appeal route governs it?"
        ),
        required_fields=fields,
    )


def _declared_material_unknowns(evidence: str) -> tuple[str, ...]:
    """Extract decision labels from explicit missing, unresolved, or blocking clauses."""

    fields: list[str] = []
    sentences = sentence_fragments(evidence)
    lowered_evidence = evidence.casefold()
    for sentence in sentences:
        lowered = sentence.casefold().strip()
        clause = _subject_before_marker(sentence, lowered)
        if clause:
            fields.extend(_field_keys(clause))
        supplied = _supplied_clause(sentence, lowered)
        if supplied:
            fields.extend(_field_keys(supplied))
        needed = _needed_before_clause(sentence, lowered)
        if needed:
            fields.extend(_field_keys(needed))
        if "identify " in lowered and any(
            marker in lowered_evidence for marker in (" absent", " unknown", " unresolved", "do not authorize")
        ):
            start = lowered.index("identify ") + len("identify ")
            fields.extend(_field_keys(sentence[start:]))
    return tuple(dict.fromkeys(field for field in fields if field))


def _subject_before_marker(sentence: str, lowered: str) -> str:
    for marker in _UNKNOWN_SUBJECT_MARKERS:
        if marker not in lowered:
            continue
        subject = sentence[: lowered.index(marker)].strip(" .,:;-")
        if ":" in subject and subject.partition(":")[0].casefold().strip() in _FIELD_PREFIXES:
            subject = subject.partition(":")[2].strip()
        return subject
    absent_subject = _absent_decision_subject(sentence, lowered)
    if absent_subject:
        return absent_subject
    if lowered.startswith("no "):
        for marker in _SUPPLY_MARKERS:
            if marker in lowered:
                return sentence[3 : lowered.index(marker)].strip(" .,:;-")
    return ""


def _absent_decision_subject(sentence: str, lowered: str) -> str:
    """Distinguish an unspecified decision from a runtime value that may be absent."""

    for marker in (" are absent", " is absent"):
        if marker not in lowered:
            continue
        subject = sentence[: lowered.index(marker)].strip(" .,:;-")
        for boundary in (" while ", " when ", " if ", ";", ","):
            if boundary in subject.casefold():
                subject = subject[subject.casefold().rfind(boundary) + len(boundary) :].strip()
        key = _field_key(subject)
        if key.endswith(("_authority", "_jurisdiction", "_owner", "_policy", "_protocol", "_rule")):
            return subject
    return ""


def _supplied_clause(sentence: str, lowered: str) -> str:
    if " until " not in lowered:
        return ""
    tail_start = lowered.index(" until ") + len(" until ")
    tail = sentence[tail_start:]
    lowered_tail = lowered[tail_start:]
    for marker in _SUPPLY_MARKERS:
        if marker in lowered_tail:
            return tail[: lowered_tail.index(marker)].strip(" .,:;-")
    return ""


def _needed_before_clause(sentence: str, lowered: str) -> str:
    if "need " not in lowered or " before " not in lowered:
        return ""
    start = lowered.index("need ") + len("need ")
    end = lowered.find(" before ", start)
    return sentence[start:end].strip(" .,:;-") if end > start else ""


def _field_keys(value: str) -> tuple[str, ...]:
    return tuple(
        field
        for part in _FIELD_SPLIT_RE.split(value)
        if (field := _field_key(part))
    )


def _field_key(value: str) -> str:
    words = _FIELD_TOKEN_RE.findall(clean_markdown_text(value).casefold())
    if words and words[0] in {"can", "cannot", "do", "must", "should", "will"}:
        return ""
    while words and words[0] in {"a", "an", "the", "both", "either", "no", "what", "which"}:
        words.pop(0)
    for boundary in ("that", "who", "whose", "when", "while", "so", "before", "until"):
        if boundary in words:
            words = words[: words.index(boundary)]
    key = "_".join(words).strip("_")
    aliases = {
        "country_specific_export_rule": "export_jurisdiction",
        "guardian_approval": "guardian_approval_rule",
    }
    return aliases.get(key, key)


def _material_unknown_question(fields: list[str]) -> str:
    labels = [field.replace("_", " ") for field in fields]
    if len(labels) == 1:
        field_text = labels[0]
    elif len(labels) == 2:
        field_text = f"{labels[0]} and {labels[1]}"
    else:
        field_text = f"{', '.join(labels[:-1])}, and {labels[-1]}"
    return f"Could you specify the {field_text} for this project?"


def _has_guardian_approval_gap(lowered: str) -> bool:
    return "age policy" in lowered and "guardian approval" in lowered and "not specified" in lowered


def _has_location_disclosure_conflict(lowered: str) -> bool:
    return "public location" in lowered and "location" in lowered and "restricted" in lowered


def _has_explicit_material_conflict(lowered: str) -> bool:
    if any(
        marker in lowered
        for marker in ("which is intended", "ask which", "in conflict", "contradict", "mutually exclusive")
    ):
        return True
    return any(
        f"{subject} conflict" in lowered
        for subject in ("accounts", "boundaries", "claims", "descriptions", "instructions", "notes", "requirements", "sources")
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
    return bool(text and (_VISIBLE_RE.search(text) or _TERMINAL_DELIVERABLE_RE.search(text)))


__all__ = [
    "MaterialClarification",
    "explicit_material_clarification",
    "has_explicit_visible_result",
    "incomplete_path_clarification",
    "material_clarification_for_fields",
]
