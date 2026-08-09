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
    " are missing",
    " is missing",
    " are unspecified",
    " is unspecified",
    " are not specified",
    " is not specified",
    " are not provided",
    " is not provided",
    " are not supplied",
    " is not supplied",
    " disagree",
)
_SUPPLY_MARKERS = (
    " are supplied",
    " is supplied",
    " are provided",
    " is provided",
    " are confirmed",
    " is confirmed",
    " are resolved",
    " is resolved",
    " are named",
    " is named",
)
_FIELD_TOKEN_RE = re.compile(r"[a-z0-9]+")
_FIELD_CONJUNCTION_RE = re.compile(r",|\b(?:and|or)\b", flags=re.IGNORECASE)
_FIELD_PREFIXES = (
    "pasted brief",
    "research evidence",
    "revision notes",
    "pending confirmation",
)
_DEFERRED_DECISION_COMMANDS = ("choose ", "clarify ", "decide ", "determine ", "specify ")
_ANAPHORIC_FIELD_KEYS = frozenset({"both", "it", "them", "they", "those"})


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
        fields.append("guardian approval rule")
    if _has_location_disclosure_conflict(lowered):
        fields.append("location disclosure policy")
    if fields:
        return _clarification_from_source_labels(fields)
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
    """Preserve decision labels from explicit missing, unresolved, or deferred clauses."""

    fields: list[str] = []
    sentences = sentence_fragments(evidence)
    lowered_evidence = evidence.casefold()
    previous_sentence = ""
    for sentence in sentences:
        lowered = sentence.casefold().strip()
        for subject in _gap_subjects(sentence):
            fields.extend(_material_field_labels(subject))
        supplied = _supplied_clause(sentence, lowered)
        if supplied:
            fields.extend(_material_field_labels(supplied))
        needed = _needed_before_clause(sentence, lowered)
        if needed:
            fields.extend(_material_field_labels(needed))
        deferred = _deferred_decision_clause(sentence, previous_sentence=previous_sentence)
        if deferred:
            fields.extend(_material_field_labels(deferred))
        if "identify " in lowered and any(
            marker in lowered_evidence for marker in (" absent", " unknown", " unresolved", "do not authorize")
        ):
            start = lowered.index("identify ") + len("identify ")
            fields.extend(_material_field_labels(sentence[start:]))
        previous_sentence = sentence
    return _dedupe_material_labels(fields)


def _gap_subjects(sentence: str) -> tuple[str, ...]:
    """Return each grammatical subject governed by an explicit unknown predicate."""

    lowered = sentence.casefold()
    occurrences: list[tuple[int, str]] = []
    for marker in _UNKNOWN_SUBJECT_MARKERS:
        start = 0
        while (index := lowered.find(marker, start)) >= 0:
            occurrences.append((index, marker))
            start = index + len(marker)
    subjects: list[str] = []
    cursor = 0
    for index, marker in sorted(occurrences):
        if index < cursor:
            continue
        subject = _decision_subject_tail(sentence[cursor:index])
        if subject:
            subjects.append(subject)
        cursor = index + len(marker)
    for marker in (" are absent", " is absent"):
        index = lowered.find(marker)
        if index < 0:
            continue
        subject = _decision_subject_tail(sentence[:index])
        key = _field_key(subject)
        if key.endswith(("_authority", "_jurisdiction", "_owner", "_policy", "_protocol", "_rule")):
            subjects.append(subject)
    if lowered.startswith("no "):
        for marker in _SUPPLY_MARKERS:
            index = lowered.find(marker)
            if index >= 0:
                subject = _decision_subject_tail(sentence[3:index])
                if subject:
                    subjects.append(subject)
                break
    return tuple(dict.fromkeys(subjects))


def _decision_subject_tail(value: str) -> str:
    text = clean_markdown_text(value).strip(" .,:;-")
    lowered = text.casefold()
    boundaries = tuple(
        index + len(boundary)
        for boundary in (", but ", ", yet ", "; but ", "; yet ")
        if (index := lowered.rfind(boundary)) >= 0
    )
    boundary_end = max(boundaries, default=0)
    text = text[boundary_end:].strip(" .,:;-")
    lowered = text.casefold()
    for prefix in ("and ", "but ", "no ", "yet "):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            lowered = text.casefold()
            break
    if ":" in text and text.partition(":")[0].casefold().strip() in _FIELD_PREFIXES:
        text = text.partition(":")[2].strip()
    return text


def _supplied_clause(sentence: str, lowered: str) -> str:
    if " until " not in lowered:
        return ""
    tail_start = lowered.index(" until ") + len(" until ")
    tail = sentence[tail_start:]
    lowered_tail = lowered[tail_start:]
    for marker in _SUPPLY_MARKERS:
        if marker in lowered_tail:
            value = tail[: lowered_tail.index(marker)].strip(" .,:;-")
            return "" if _field_key(value) in _ANAPHORIC_FIELD_KEYS else value
    return ""


def _needed_before_clause(sentence: str, lowered: str) -> str:
    if "need " not in lowered or " before " not in lowered:
        return ""
    start = lowered.index("need ") + len("need ")
    end = lowered.find(" before ", start)
    return sentence[start:end].strip(" .,:;-") if end > start else ""


def _deferred_decision_clause(sentence: str, *, previous_sentence: str) -> str:
    lowered = sentence.casefold().strip()
    if not lowered.startswith(("do not choose ", "don't choose ")) or " without " not in lowered:
        return ""
    previous = clean_markdown_text(previous_sentence).strip(" .")
    previous_lowered = previous.casefold()
    for command in _DEFERRED_DECISION_COMMANDS:
        if previous_lowered.startswith(command):
            return previous[len(command) :].strip(" .,:;-")
    return ""


def _material_field_labels(value: str) -> tuple[str, ...]:
    text = _decision_subject_tail(value)
    labels = tuple(_field_display_label(part) for part in _split_material_fields(text))
    return tuple(label for label in labels if _field_key(label))


def _dedupe_material_labels(labels: list[str]) -> tuple[str, ...]:
    """Prefer the most specific source label when a later clause uses shorthand."""

    kept: list[str] = []
    for label in labels:
        key = _field_key(label)
        if not key:
            continue
        tokens = frozenset(key.split("_"))
        existing_tokens = [frozenset(_field_key(item).split("_")) for item in kept]
        if any(tokens <= item for item in existing_tokens):
            continue
        kept = [item for item, item_tokens in zip(kept, existing_tokens, strict=True) if not item_tokens < tokens]
        kept.append(label)
    return tuple(kept)


def _split_material_fields(value: str) -> tuple[str, ...]:
    text = clean_markdown_text(value).strip(" .,:;-")
    if not text:
        return ()
    fields: list[str] = []
    start = 0
    lowered = text.casefold()
    for match in _FIELD_CONJUNCTION_RE.finditer(text):
        delimiter = match.group(0).casefold()
        if delimiter == "and":
            between = lowered.rfind("between ", start, match.start())
            prior_and = lowered.rfind(" and ", start, match.start())
            if between >= start and prior_and < between:
                continue
        left = text[start:match.start()].strip(" .,:;-")
        right = text[match.end():].strip(" .,:;-")
        if delimiter != "," and not _is_field_conjunction(left=left, right=right):
            continue
        if left:
            fields.append(left)
        start = match.end()
    tail = text[start:].strip(" .,:;-")
    if tail:
        fields.append(tail)
    return tuple(fields or (text,))


def _is_field_conjunction(*, left: str, right: str) -> bool:
    left_words = _FIELD_TOKEN_RE.findall(left.casefold())
    right_words = _FIELD_TOKEN_RE.findall(right.casefold())
    if not left_words or not right_words:
        return False
    if right_words[0] in {"what", "which", "who", "whose"}:
        return True
    return len(left_words) == len(right_words) == 1 or (len(left_words) >= 2 and len(right_words) >= 2)


def _field_display_label(value: str) -> str:
    words = clean_markdown_text(value).strip(" .,:;-").split()
    while words and words[0].casefold() in {"a", "an", "the", "both", "either", "no", "what", "which"}:
        words.pop(0)
    return " ".join(words).strip()


def _field_key(value: str) -> str:
    words = _FIELD_TOKEN_RE.findall(_field_display_label(value).casefold())
    if words and words[0] in {"can", "cannot", "do", "must", "should", "will"}:
        return ""
    key = "_".join(words).strip("_")
    if key in _ANAPHORIC_FIELD_KEYS:
        return ""
    aliases = {
        "country_specific_export_rule": "export_jurisdiction",
        "guardian_approval": "guardian_approval_rule",
    }
    return aliases.get(key, key)


def _clarification_from_source_labels(labels: list[str]) -> MaterialClarification:
    keyed_labels: dict[str, str] = {}
    for label in labels:
        field_id = _field_key(label)
        if field_id:
            keyed_labels.setdefault(field_id, _field_display_label(label))
    return MaterialClarification(
        question=_material_unknown_question(list(keyed_labels.values())),
        required_fields=tuple(keyed_labels),
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
