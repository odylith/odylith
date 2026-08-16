"""Find explicit material decisions in operator evidence before staging."""

from __future__ import annotations

from dataclasses import dataclass
import re

from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import sentence_fragments
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import explicit_actor_evidence
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


@dataclass(frozen=True)
class ExplicitDecisionGap:
    """One source-grounded question and the canonical fields it must settle."""

    question: str
    required_fields: tuple[str, ...]


_UNKNOWN_PREDICATES = (
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
    " are absent",
    " is absent",
    " disagree",
)
_SUPPLY_PREDICATES = (" are supplied", " is supplied", " are provided", " is provided")
_NEGATED_CONFLICT_ASSERTIONS = (
    "has no contradiction",
    "no ambiguity",
    "no conflict",
    "not ambiguous",
    "not contradictory",
    "not in conflict",
)
_AUTHORITY_TERMS = ("authority", "owner", "approver", "commander")
_RULE_TERMS = ("appeal route", "jurisdiction", "policy", "protocol", "rule", "standard")
_FIELD_TOKEN_RE = re.compile(r"[a-z0-9]+")
_FIELD_DELIMITER_RE = re.compile(r",|\b(?:and|or)\b", flags=re.IGNORECASE)
_ANAPHORIC_FIELDS = frozenset({"both", "either", "it", "them", "they", "those", "those_fields"})
_DECLARED_UNCERTAINTY_PREDICATES = frozenset(
    {
        "are unresolved",
        "is unresolved",
        "are unknown",
        "is unknown",
        "are unspecified",
        "is unspecified",
        "are not specified",
        "is not specified",
    }
)
_PRESENTATION_DETAIL_TERMS = frozenset(
    {
        "color",
        "colour",
        "copy",
        "font",
        "icon",
        "symbol",
        "theme",
        "typography",
        "visual",
        "wording",
    }
)
_PRESENTATION_CONNECTOR_TERMS = frozenset(
    {"and", "choice", "detail", "details", "or", "presentation", "scheme", "style"}
)
_STATE_TRANSITION_RE = re.compile(
    r"\b(?:from\s+[A-Za-z][A-Za-z0-9_-]{0,60}\s+to\s+[A-Za-z][A-Za-z0-9_-]{0,60}|"
    r"[A-Za-z][A-Za-z0-9_-]{0,60}\s+to\s+[A-Za-z][A-Za-z0-9_-]{0,60})\b",
    flags=re.IGNORECASE,
)
_REPORTED_CLAIM_RE = re.compile(
    r"\b(?:one|another|a\s+second|the\s+other)\b[^.!?]{0,80}?"
    r"\b(?:says?|states?|reports?|requires?|directs?)\b\s+(?P<claim>.+)$",
    flags=re.IGNORECASE,
)
_IDENTIFIED_OWNER_RE = re.compile(
    r"\bidentif(?:y|ies)\s+(?:the\s+)?(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+"
    r"as\s+(?:the\s+)?(?P<relation>[A-Za-z][A-Za-z0-9 /&'()-]{0,60}?)\s+owner\b",
    flags=re.IGNORECASE,
)
_BELONGS_TO_ROLE_RE = re.compile(
    r"\b(?P<relation>[A-Za-z][A-Za-z0-9_-]{2,50})\s+belongs?\s+only\s+to\s+"
    r"(?:the\s+)?(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80})$",
    flags=re.IGNORECASE,
)
_PRESERVED_ASSERTIONS_RE = re.compile(
    r"\bboth\s+(?:accounts|claims|sources|statements|versions)\b[^.!?]{0,80}"
    r"\b(?:are|remain|stay)\b[^.!?]{0,40}\b(?:asserted|preserved|retained|true)\b",
    flags=re.IGNORECASE,
)


def explicit_decision_gap(evidence: str) -> ExplicitDecisionGap | None:
    """Return the first explicit material decision without inferring one from domain words."""

    text = clean_markdown_text(evidence)
    lowered = text.casefold()
    if not text:
        return None
    if _first_approval_changes_path(lowered):
        return ExplicitDecisionGap(
            question="Who should own the first approval, initial path, and proof record?",
            required_fields=("first_approval_actor", "first_path", "proof_record_owner"),
        )
    authority_gap = _declared_authority_gap(lowered)
    if authority_gap:
        return authority_gap

    sentences = sentence_fragments(text)
    relation_gap = _relation_level_decision_gap(sentences)
    if relation_gap:
        return relation_gap
    if _actorless_state_transition_requires_role(text, sentences=sentences):
        return ExplicitDecisionGap(
            question="Which role should own this state-changing first path?",
            required_fields=("role",),
        )
    labels = _declared_missing_fields(sentences)
    if "age policy" in lowered and "guardian approval" in lowered and "not specified" in lowered:
        labels.append("guardian approval rule")
    if "public location" in lowered and "location" in lowered and "restricted" in lowered:
        labels.append("location disclosure policy")
    labels = _dedupe_labels(labels)
    if labels:
        return _question_for_labels(labels)
    for sentence in sentences:
        decision = _direct_decision_question(sentence)
        if decision:
            return decision
    return None


def _relation_level_decision_gap(sentences: tuple[str, ...] | list[str]) -> ExplicitDecisionGap | None:
    """Recognize conflicting assignments and paths even when no sentence says `conflict`."""

    owners_by_relation: dict[str, set[str]] = {}
    belongs_claims: list[tuple[str, str]] = []
    for sentence in sentences:
        identified = _IDENTIFIED_OWNER_RE.search(sentence)
        if identified:
            relation = _relation_key(identified.group("relation"))
            owners_by_relation.setdefault(relation, set()).add(_actor_key(identified.group("actor")))
        belongs = _BELONGS_TO_ROLE_RE.search(sentence)
        if belongs:
            claim = (_relation_key(belongs.group("relation")), _actor_key(belongs.group("actor")))
            belongs_claims.append(claim)
            owners_by_relation.setdefault(claim[0], set()).add(claim[1])
    if any(len(actors) > 1 for actors in owners_by_relation.values()):
        return ExplicitDecisionGap(
            question="Which role should own the disputed first-path decision?",
            required_fields=("role",),
        )
    if belongs_claims and any(_PRESERVED_ASSERTIONS_RE.search(sentence) for sentence in sentences):
        for relation, assigned_actor in belongs_claims:
            for sentence in sentences:
                source = prompt_intent_source(sentence)
                if (
                    source.actor
                    and _actor_key(source.actor) != assigned_actor
                    and relation in _relation_key(sentence)
                ):
                    return ExplicitDecisionGap(
                        question="Which role should own the disputed first-path decision?",
                        required_fields=("role",),
                    )

    reported_claims = [
        match.group("claim").strip(" .")
        for sentence in sentences
        if (match := _REPORTED_CLAIM_RE.search(sentence))
    ]
    if len(reported_claims) >= 2:
        claims = " ".join(reported_claims).casefold()
        distinct = len({_field_key(claim) for claim in reported_claims if _field_key(claim)}) >= 2
        path_relation = all(re.search(r"\bfirst\b", claim, flags=re.IGNORECASE) for claim in reported_claims)
        same_action_authority = "same action" in claims and "only" in claims
        if distinct and (path_relation or same_action_authority):
            return ExplicitDecisionGap(
                question="Which asserted behavior should define the first complete path?",
                required_fields=("first_path",),
            )
    return None


def _actorless_state_transition_requires_role(text: str, *, sentences: tuple[str, ...] | list[str]) -> bool:
    if explicit_actor_evidence(text):
        return False
    for sentence in sentences:
        if not _STATE_TRANSITION_RE.search(sentence):
            continue
        source = prompt_intent_source(sentence)
        if source.command_led and not source.actor:
            return True
    return False


def _actor_key(value: str) -> str:
    return "_".join(_FIELD_TOKEN_RE.findall(value.casefold()))


def _relation_key(value: str) -> str:
    words = _FIELD_TOKEN_RE.findall(value.casefold())
    normalized = ["approv" if word.startswith("approv") else word for word in words]
    return "_".join(normalized)


def _first_approval_changes_path(lowered: str) -> bool:
    return all(
        phrase in lowered
        for phrase in ("either ", " or ", "own the first approval", "choice changes the initial path", "proof record")
    )


def _declared_authority_gap(lowered: str) -> ExplicitDecisionGap | None:
    if "the prompt does not" not in lowered and "the prompt omits" not in lowered:
        return None
    has_authority = any(term in lowered for term in _AUTHORITY_TERMS)
    has_rule = any(term in lowered for term in _RULE_TERMS)
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
    return ExplicitDecisionGap(
        question=(
            "Who has authority to make the unresolved decision, and what rule, standard, jurisdiction, "
            "or appeal route governs it?"
        ),
        required_fields=fields,
    )


def _direct_decision_question(sentence: str) -> ExplicitDecisionGap | None:
    lowered = sentence.casefold().strip()
    if any(assertion in lowered for assertion in _NEGATED_CONFLICT_ASSERTIONS):
        return None
    if "contradicts itself" in lowered or (
        "one passage says" in lowered and "later passage says" in lowered
    ):
        return ExplicitDecisionGap(
            question="Which of the conflicting rules should govern the first complete path?",
            required_fields=("first_path",),
        )
    if "silent about who" in lowered:
        tail = sentence[lowered.index("who") :].strip(" .")
        return ExplicitDecisionGap(
            question=_as_question(tail),
            required_fields=("human_actors",),
        )
    uncertainty_markers = (
        "does not identify whether",
        "does not state whether",
        "never says whether",
        "does not say whether",
    )
    if any(marker in lowered for marker in uncertainty_markers):
        tail = sentence[lowered.index("whether") :].strip(" .")
        choice = tail[len("whether") :].strip()
        return ExplicitDecisionGap(
            question=_actor_choice_question(choice),
            required_fields=("human_actors",),
        )
    if "no rule to choose between" in lowered and " or " in lowered:
        decision = sentence.split(",", maxsplit=1)[0].strip(" .")
        for prefix in ("The prompt says ", "The request says "):
            if decision.startswith(prefix):
                decision = decision[len(prefix) :]
                break
        actors, action = actor_led_action_parts(decision)
        if actors and action:
            question = f"Who should {action}: {actors}?"
        else:
            question = "Which of the named roles should own this decision?"
        return ExplicitDecisionGap(
            question=question,
            required_fields=("human_actors",),
        )
    return None


def _actor_choice_question(choice: str) -> str:
    lowered = choice.casefold()
    for separator, prompt_verb, action_verb in (
        (" owns ", "should", "own "),
        (" may ", "may", ""),
        (" can ", "can", ""),
    ):
        index = lowered.find(separator)
        if index < 0:
            continue
        actors = choice[:index].strip(" .")
        action = action_verb + choice[index + len(separator) :].strip(" .")
        return f"Who {prompt_verb} {action}: {actors}?"
    return "Who should own the unresolved role decision?"


def _declared_missing_fields(sentences: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    previous = ""
    for sentence in sentences:
        labels.extend(_subjects_for_predicates(sentence, _UNKNOWN_PREDICATES))
        labels.extend(_required_supply_subjects(sentence))
        labels.extend(_needed_before_subjects(sentence))
        labels.extend(_negative_supply_subjects(sentence))
        lowered = sentence.casefold().strip()
        if lowered.endswith((" conflict", " conflicts")) and not lowered.endswith((" the conflict", " a conflict")):
            predicate = " conflicts" if lowered.endswith(" conflicts") else " conflict"
            labels.extend(_labels(sentence[: -len(predicate)]))
        if (
            any(value in lowered for value in ("those fields are absent", "those terms are absent"))
            and "identify " in previous.casefold()
        ):
            labels.extend(_labels(previous[previous.casefold().index("identify ") + len("identify ") :]))
        if lowered.startswith(("do not choose ", "don't choose ")) and " without " in lowered:
            previous_lowered = previous.casefold().strip()
            for command in ("choose ", "clarify ", "decide ", "determine ", "specify "):
                if previous_lowered.startswith(command):
                    labels.extend(_labels(previous[len(command) :]))
                    break
        previous = sentence
    return labels


def _subjects_for_predicates(sentence: str, predicates: tuple[str, ...]) -> list[str]:
    lowered = sentence.casefold()
    occurrences = sorted(
        (index, predicate)
        for predicate in predicates
        for index in _all_indexes(lowered, predicate)
    )
    labels: list[str] = []
    cursor = 0
    for index, predicate in occurrences:
        if index < cursor:
            continue
        subject_source = sentence[cursor:index]
        subject = _subject_tail(subject_source)
        if _runtime_condition_before_predicate(subject_source):
            subject = re.sub(r"^(?:if|when|whenever)\s+", "", subject, flags=re.IGNORECASE)
            if not _material_decision_subject(subject, predicate=predicate):
                cursor = index + len(predicate)
                continue
        if predicate in {" are absent", " is absent"} and not _material_decision_subject(
            subject, predicate=predicate
        ):
            cursor = index + len(predicate)
            continue
        if subject:
            labels.extend(_labels(subject))
        cursor = index + len(predicate)
    return labels


def _runtime_condition_before_predicate(value: str) -> bool:
    """Keep blocked-state conditions out of explicit user-decision gaps."""

    return bool(re.search(r"\b(?:if|when|whenever)\s+[^.;]{1,160}$", value, flags=re.IGNORECASE))


def _material_decision_subject(value: str, *, predicate: str) -> bool:
    key = _field_key(value)
    if predicate.strip() in _DECLARED_UNCERTAINTY_PREDICATES:
        return bool(key and key not in _ANAPHORIC_FIELDS)
    return key.endswith(("_authority", "_jurisdiction", "_owner", "_policy", "_protocol", "_rule"))


def _required_supply_subjects(sentence: str) -> list[str]:
    lowered = sentence.casefold()
    if " until " not in lowered:
        return []
    tail_start = lowered.rindex(" until ") + len(" until ")
    tail = sentence[tail_start:]
    lowered_tail = lowered[tail_start:]
    for predicate in _SUPPLY_PREDICATES:
        index = lowered_tail.find(predicate)
        if index >= 0:
            return _labels(tail[:index])
    return []


def _needed_before_subjects(sentence: str) -> list[str]:
    lowered = sentence.casefold()
    need_index = lowered.find("need ")
    before_index = lowered.find(" before ", need_index + len("need "))
    if need_index < 0 or before_index < 0:
        return []
    return _labels(sentence[need_index + len("need ") : before_index])


def _negative_supply_subjects(sentence: str) -> list[str]:
    lowered = sentence.casefold().strip()
    if not lowered.startswith("no "):
        return []
    for predicate in _SUPPLY_PREDICATES:
        index = lowered.find(predicate)
        if index >= 0:
            if re.search(r"\b(?:after|before|unless|until|when)\b", lowered[index + len(predicate) :]):
                return []
            return _labels(sentence[3:index])
    return []


def _subject_tail(value: str) -> str:
    text = clean_markdown_text(value).strip(" .,:;-")
    lowered = text.casefold()
    for boundary in (", but ", ", yet ", "; but ", "; yet ", ", and "):
        if boundary in lowered:
            index = lowered.rindex(boundary) + len(boundary)
            text = text[index:].strip(" .,:;-")
            lowered = text.casefold()
    if " until " in lowered:
        text = text[lowered.rindex(" until ") + len(" until ") :].strip(" .,:;-")
    for prefix in ("and ", "but ", "no ", "or ", "yet "):
        if text.casefold().startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return text


def _labels(value: str) -> list[str]:
    text = _subject_tail(value)
    if not text:
        return []
    parts: list[str] = []
    start = 0
    lowered = text.casefold()
    for match in _FIELD_DELIMITER_RE.finditer(text):
        delimiter = match.group(0).casefold()
        if delimiter == "and" and _and_belongs_to_between(lowered, start=start, index=match.start()):
            continue
        left = text[start : match.start()].strip(" .,:;-")
        right = text[match.end() :].strip(" .,:;-")
        if delimiter != "," and not _field_conjunction(left=left, right=right):
            continue
        if left:
            parts.append(left)
        start = match.end()
    tail = text[start:].strip(" .,:;-")
    if tail:
        parts.append(tail)
    return [_display_label(part) for part in (parts or [text]) if _field_key(part)]


def _and_belongs_to_between(lowered: str, *, start: int, index: int) -> bool:
    between = lowered.rfind("between ", start, index)
    prior_and = lowered.rfind(" and ", start, index)
    return between >= start and prior_and < between


def _field_conjunction(*, left: str, right: str) -> bool:
    left_words = _FIELD_TOKEN_RE.findall(left.casefold())
    right_words = _FIELD_TOKEN_RE.findall(right.casefold())
    if not left_words or not right_words:
        return False
    if right_words[0] in {"what", "which", "who", "whose"}:
        return True
    return len(left_words) == len(right_words) == 1 or (len(left_words) >= 2 and len(right_words) >= 2)


def _display_label(value: str) -> str:
    words = clean_markdown_text(value).strip(" .,:;-").split()
    while words and words[0].casefold() in {
        "a",
        "an",
        "the",
        "both",
        "either",
        "no",
        "those",
        "what",
        "which",
    }:
        words.pop(0)
    return " ".join(words).strip()


def _field_key(value: str) -> str:
    words = _FIELD_TOKEN_RE.findall(_display_label(value).casefold())
    if words and words[0] in {"can", "cannot", "do", "must", "should", "will"}:
        return ""
    key = "_".join(words).strip("_")
    aliases = {
        "country_specific_export_rule": "export_jurisdiction",
        "guardian_approval": "guardian_approval_rule",
        "proof_boundaries": "proof_boundary",
    }
    return "" if key in _ANAPHORIC_FIELDS else aliases.get(key, key)


def _dedupe_labels(labels: list[str]) -> list[str]:
    kept: list[str] = []
    for label in labels:
        key = _field_key(label)
        if not key or _is_presentation_only_gap(key):
            continue
        tokens = frozenset(key.split("_"))
        existing = [frozenset(_field_key(item).split("_")) for item in kept]
        if any(tokens <= item for item in existing):
            continue
        kept = [item for item, item_tokens in zip(kept, existing, strict=True) if not item_tokens < tokens]
        kept.append(_display_label(label))
    return kept


def _is_presentation_only_gap(key: str) -> bool:
    tokens = set(str(key or "").split("_"))
    details = tokens - _PRESENTATION_CONNECTOR_TERMS
    return bool(details and details <= _PRESENTATION_DETAIL_TERMS)


def _question_for_labels(labels: list[str]) -> ExplicitDecisionGap:
    fields = tuple(_field_key(label) for label in labels)
    if len(labels) == 1:
        field_text = labels[0]
    elif len(labels) == 2:
        separator = ", and " if " and " in labels[0].casefold() else " and "
        field_text = f"{labels[0]}{separator}{labels[1]}"
    else:
        field_text = f"{', '.join(labels[:-1])}, and {labels[-1]}"
    return ExplicitDecisionGap(
        question=f"Could you specify the {field_text} for this project?",
        required_fields=fields,
    )


def _all_indexes(value: str, needle: str) -> tuple[int, ...]:
    indexes: list[int] = []
    start = 0
    while (index := value.find(needle, start)) >= 0:
        end = index + len(needle)
        if end >= len(value) or not value[end].isalnum():
            indexes.append(index)
        start = index + len(needle)
    return tuple(indexes)


def _as_question(value: str) -> str:
    text = " ".join(value.strip().split()).rstrip(".?!")
    return text[:1].upper() + text[1:] + "?"


__all__ = ["ExplicitDecisionGap", "explicit_decision_gap"]
