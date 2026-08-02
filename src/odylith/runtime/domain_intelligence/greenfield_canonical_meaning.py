"""Canonical state and responsibility projections from a Greenfield first path."""

from __future__ import annotations

import re
from collections.abc import Sequence

from odylith.runtime.common.prose_grammar import base_action_verb
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_non_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import indefinite_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import looks_plural
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import strip_action_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import singularize_last_word
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_ACTION_RESPONSIBILITIES = (
    (frozenset({"add", "attach", "capture", "collect", "create", "enter", "intake", "open", "register", "submit", "upload"}), "Intake"),
    (frozenset({"assign"}), "Assignment"),
    (frozenset({"approve"}), "Approval"),
    (frozenset({"calculate", "compute"}), "Calculation"),
    (frozenset({"choose", "select"}), "Selection"),
    (frozenset({"cluster", "group", "organize"}), "Organization"),
    (frozenset({"decompose"}), "Decomposition"),
    (frozenset({"deliver", "display", "publish", "release", "return", "see", "show", "surface"}), "Delivery"),
    (frozenset({"draft"}), "Drafting"),
    (frozenset({"generate", "produce"}), "Generation"),
    (frozenset({"match"}), "Matching"),
    (frozenset({"route"}), "Routing"),
    (frozenset({"preserve", "record", "save", "store", "track"}), "Recordkeeping"),
    (frozenset({"review"}), "Review"),
    (frozenset({"schedule"}), "Scheduling"),
    (frozenset({"score"}), "Scoring"),
    (frozenset({"check", "confirm", "validate", "verify"}), "Validation"),
    (frozenset({"prove"}), "Proof"),
)
_LEADING_OBJECT_WORDS = frozenset({"a", "an", "one", "the", "this", "that"})
_ACTION_OBJECT_LEADING_WORDS = _LEADING_OBJECT_WORDS | {"and", "or"}
_LABEL_STOP_WORDS = frozenset(
    {
        "appropriate",
        "automated",
        "current",
        "new",
        "one",
        "required",
        "selected",
        "the",
        "validated",
    }
)
_STATE_RECORD_SUFFIXES = ("consent", "data", "evidence", "information", "readiness", "status", "tooling")
_WEAK_STATE_OBJECTS = frozenset(
    {
        "current status",
        "details",
        "information",
        "status",
    }
)
_GENERIC_CANONICAL_STATE_TERMS = frozenset(
    {"detail", "details", "information", "item", "object", "record", "state", "status", "thing"}
)


def product_handoff_first_path(*, actor: str, first_path: str) -> str:
    """Make an actor-to-product handoff explicit for command-led product clauses."""

    model = first_path_model(first_path)
    if len(model.steps) < 2:
        return ""
    actor_text = clean_text(actor).strip(" .") or "the primary user"
    first_action = _action_without_subject(model.steps[0])
    if not first_action:
        return ""
    actor_words = actor_text.split()
    plural_actor = bool(actor_words and looks_plural(actor_words[-1]))
    first_clause = base_action_clause(first_action).strip(" .") if plural_actor else _finite_action(first_action)
    if not first_clause:
        return ""
    rows = [f"{actor_text[:1].upper() + actor_text[1:]} {first_clause}"]
    seen_verbs = set(_action_verbs(first_action))
    remaining_explicit_actor_repeats = max(0, _source_actor_mention_count(first_path, actor=actor_text) - 1)
    for step in model.steps[1:]:
        action = _drop_repeated_leading_action(_action_without_subject(step), seen=seen_verbs)
        if not action:
            continue
        seen_verbs.update(_action_verbs(action))
        subject = _explicit_action_subject(step)
        if subject and _actor_key(subject) == _actor_key(actor_text):
            if remaining_explicit_actor_repeats:
                remaining_explicit_actor_repeats -= 1
                rows.append(_sentence_start(step))
            else:
                rows.append(f"The product {_finite_action(action)}")
        elif subject:
            rows.append(_sentence_start(step))
        else:
            rows.append(f"The product {_finite_action(action)}")
    return ". ".join(row.rstrip(" .") for row in rows if row.strip(" .")).rstrip(" .") + "."


def state_object_from_first_path(first_path: str, *, fallback: str) -> str:
    """Return the durable object changed by the first material action."""

    model = first_path_model(first_path)
    action = _action_without_subject((model.steps[0] if model.steps else "") or model.material_action)
    subject = _action_object(action)
    if _weak_state_object(subject):
        subject = ""
    if not subject:
        subject = _action_object(model.visible_outcome)
    if not subject:
        subject = _compact_label(model.visible_outcome, fallback=fallback, max_words=6).casefold()
    subject = singularize_last_word(subject)
    if subject.casefold().endswith(_STATE_RECORD_SUFFIXES):
        subject = f"{subject} record"
    subject = subject or clean_text(fallback).casefold() or "first-path item"
    return f"The primary state object is {indefinite_phrase(subject)}."


def canonical_state_object_is_meaningful(value: str) -> bool:
    """Return whether a bounded canonical state sentence names a concrete object."""

    match = re.fullmatch(
        r"the primary state object is\s+(?:(?:a|an|the|one)\s+)?(?P<object>[^.;]+)\.?",
        clean_text(value).strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    terms = {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", match.group("object"))
        if token.casefold() not in _GENERIC_CANONICAL_STATE_TERMS
    }
    return bool(terms)


def internal_system_rows_from_first_path(
    *,
    title: str,
    first_path: str,
    state_object: str,
    visible_result: str,
    human_actors: Sequence[str] = (),
) -> list[str]:
    """Project distinct product responsibilities from first-path actions."""

    model = first_path_model(first_path)
    steps = [
        owned_step
        for step in model.steps
        if clean_text(step).strip(" .")
        for owned_step in _ownership_steps(clean_text(step).strip(" ."), human_actors=human_actors)
    ]
    if not steps:
        return []
    state_label = _state_label(state_object, fallback=title)
    result_label = _compact_label(visible_result or model.visible_outcome, fallback="Result", max_words=5)
    rows: list[str] = []
    used_responsibilities: set[str] = set()
    for index, step in enumerate(steps):
        human_subject = _matching_human_subject(step, human_actors=human_actors)
        if human_subject:
            action = _action_after_subject(step, subject=human_subject) or _action_without_subject(step)
            rows.append(
                _human_supported_system_row(
                    action=action,
                    actor=human_subject,
                    state_label=state_label,
                )
            )
            continue
        non_human_subject = _non_human_subject_prefix(step)
        action = _action_after_subject(step, subject=non_human_subject) or _action_without_subject(step)
        if index == len(steps) - 1 and _connector_clipped_action(action):
            rows.append(
                f"{title_case_text(f'{result_label} Review')} — presents {result_label.casefold()}, known limits, "
                "failure reason, and evidence needed for the next decision"
            )
            continue
        responsibilities = _responsibility_labels(action, step=step)
        fresh = [label for label in responsibilities if label not in used_responsibilities]
        if fresh:
            responsibilities = fresh
        if not responsibilities:
            responsibilities = ["Processing"]
        used_responsibilities.update(responsibilities)
        action_label = _compact_label(
            _action_object_for_owned_clause(action, has_subject=bool(non_human_subject)),
            fallback=state_label,
            max_words=4,
        )
        if index == 0 and "Intake" in responsibilities:
            name = f"{state_label} Intake"
            description = (
                f"captures {state_label.casefold()} input and required context, then exposes validation or blocked state"
            )
        elif index == len(steps) - 1 and any(
            label in {"Delivery", "Generation", "Proof", "Validation"} for label in responsibilities
        ):
            suffix = _join_labels(responsibilities)
            outcome_label = action_label or result_label
            name = f"{outcome_label} {suffix}" if outcome_label.casefold() not in suffix.casefold() else suffix
            description = f"{_finite_action(step)} and keeps the visible result, failure reason, and review evidence together"
        else:
            suffix = _join_labels(responsibilities)
            name = f"{action_label} Workflow" if responsibilities == ["Processing"] else f"{action_label} {suffix}"
            owned_action = _lower_sentence_start(step) if non_human_subject else _finite_action(step)
            description = f"{owned_action} while preserving status, ownership, blockers, and handoff context"
        rows.append(f"{title_case_text(name)} — {description.rstrip('.')}")
    if len(rows) == 1:
        rows.append(
            f"{title_case_text(f'{result_label} Review')} — presents the completed result, known limits, "
            "failure reason, and evidence needed for the next decision"
        )
    unique_rows = list(unique_text(rows))
    if len(unique_rows) <= 4:
        return unique_rows
    return [*unique_rows[:3], unique_rows[-1]]


def _action_object(value: str) -> str:
    action = _action_without_subject(value)
    words = action.split()
    if words:
        first = words[0].casefold().strip(".,;:")
        base = base_action_verb(first)
        if looks_like_base_action_token(base) or looks_like_finite_action_token(first):
            action = " ".join(words[1:]).strip(" .")
    into_match = re.search(r"\binto\s+(?P<object>(?:a|an|the|one)?\s*[^.;]+)$", action, flags=re.IGNORECASE)
    text = clean_text(into_match.group("object") if into_match else strip_action(action)).strip(" .")
    text = re.split(r"\s*,\s*", text, maxsplit=1)[0]
    words = text.split()
    while words and words[0].casefold().strip(".,;:") in _ACTION_OBJECT_LEADING_WORDS:
        words.pop(0)
    text = " ".join(words).strip(" .")
    text = _before_coordinated_action(text)
    text = re.split(
        r"\s+(?:based on|for|from|so that|such as|through|to|using|with|without)\s+",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return text.strip(" .")


def _action_object_for_owned_clause(value: str, *, has_subject: bool) -> str:
    action = clean_text(value).strip(" .")
    result = _action_object(action)
    if has_subject and result.casefold() == action.casefold():
        words = action.split()
        if len(words) > 1:
            return " ".join(words[1:]).strip(" .")
    return result


def _weak_state_object(value: str) -> bool:
    text = clean_text(value).casefold().strip(" .")
    return not text or text in _WEAK_STATE_OBJECTS or text.endswith(" details")


def _state_label(value: str, *, fallback: str) -> str:
    text = clean_text(value)
    match = re.search(r"\bprimary state object is\s+(?:an|a|the|one)?\s*(?P<label>[^.;]+)", text, flags=re.IGNORECASE)
    if match:
        return _compact_label(match.group("label"), fallback=fallback, max_words=6)
    return _compact_label(text, fallback=fallback, max_words=6)


def _compact_label(value: str, *, fallback: str, max_words: int) -> str:
    text = clean_text(value).strip(" .")
    text = re.split(
        r"\s+(?:after|based on|before|for|from|so that|such as|through|using|with|without)\s+",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    words = [word for word in text.split() if word.casefold().strip(".,;:") not in _LEADING_OBJECT_WORDS]
    filtered = [word for word in words if word.casefold().strip(".,;:") not in _LABEL_STOP_WORDS]
    words = filtered or words
    if len(words) > max_words:
        words = words[-max_words:]
    while words and words[0].casefold().strip(".,;:") in {"and", "or"}:
        words.pop(0)
    return title_case_text(" ".join(words).strip(" .") or fallback)


def _responsibility_labels(action: str, *, step: str) -> list[str]:
    tokens = set(_action_verbs(_action_without_subject(action)))
    if re.search(r"\bvalidat(?:e[sd]?|ing)\b", step, flags=re.IGNORECASE):
        tokens.add("validate")
    labels = [label for verbs, label in _ACTION_RESPONSIBILITIES if verbs & tokens]
    return list(unique_text(labels))


def _action_without_subject(value: str) -> str:
    text = clean_text(value).strip(" .")
    stripped = clean_text(strip_action_subject(text)).strip(" .")
    if stripped and stripped.casefold() != text.casefold():
        return stripped
    words = text.split()
    for index, word in enumerate(words):
        token = word.casefold().strip(".,;:")
        if looks_like_base_action_token(token) or looks_like_finite_action_token(token):
            return " ".join(words[index:]).strip(" .")
    return text


def _explicit_action_subject(value: str) -> str:
    text = clean_text(value).strip(" .")
    action = _action_without_subject(text)
    if not action or action.casefold() == text.casefold():
        return ""
    index = text.casefold().find(action.casefold())
    if index <= 0:
        return ""
    subject = text[:index].strip(" ,.;:-")
    subject = re.sub(r"^(?:and|or|then)\s+", "", subject, flags=re.IGNORECASE).strip(" ,.;:-")
    return subject


def _sentence_start(value: str) -> str:
    text = clean_text(value).strip(" .")
    return text[:1].upper() + text[1:] if text else ""


def _matching_human_subject(value: str, *, human_actors: Sequence[str]) -> str:
    subject = _explicit_action_subject(value)
    subject_key = _actor_key(subject)
    if not subject_key:
        return ""
    for row in human_actors:
        label = re.split(r"\s*(?::|—|–|-)\s*", clean_text(row), maxsplit=1)[0]
        label_key = _actor_key(label)
        if label_key and (subject_key == label_key or subject_key.endswith(f" {label_key}")):
            return subject
    return ""


def _actor_key(value: str) -> str:
    words = clean_text(value).casefold().strip(" .").split()
    while words and words[0] in _LEADING_OBJECT_WORDS:
        words.pop(0)
    return " ".join(words)


def _source_actor_mention_count(value: str, *, actor: str) -> int:
    actor_text = clean_text(actor).strip(" .")
    if not actor_text:
        return 0
    return len(
        re.findall(
            rf"\b(?:(?:a|an|the|one)\s+)?{re.escape(actor_text)}\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _human_supported_system_row(*, action: str, actor: str, state_label: str) -> str:
    action_object = _compact_label(_action_object(action), fallback=state_label, max_words=4)
    responsibilities = _responsibility_labels(action, step=action)
    actor_ref = _actor_key(actor) or "user"
    if "Intake" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Intake')} — captures input and required context provided by the {actor_ref}, "
            "then exposes validation or blocked state"
        )
    if "Delivery" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Delivery')} — presents {action_object.casefold()} as the visible result "
            f"to the {actor_ref} with status, blockers, explanation, and review evidence"
        )
    if any(label in {"Approval", "Assignment", "Selection"} for label in responsibilities):
        suffix = _join_labels(responsibilities)
        return (
            f"{title_case_text(f'{action_object} {suffix} Record')} — records the {actor_ref} decision and keeps "
            "status, blockers, evidence, and handoff context visible"
        )
    if "Review" in responsibilities:
        actor_action = _human_actor_action(action, actor_ref=actor_ref)
        return (
            f"{title_case_text(f'{action_object} Review Record')} — records when the {actor_ref} {actor_action} and "
            "keeps status, blockers, evidence, and handoff context visible"
        )
    if "Recordkeeping" in responsibilities:
        actor_action = _human_actor_action(action, actor_ref=actor_ref)
        return (
            f"{title_case_text(f'{action_object} Recordkeeping')} — records when the {actor_ref} {actor_action} and "
            "keeps status, correction history, blockers, and handoff context visible"
        )
    if "Validation" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Workflow Support')} — records {action_object.casefold()} validation "
            f"performed by the {actor_ref} and keeps validation status, blockers, evidence, and handoff context visible"
        )
    if "Routing" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Workflow Support')} — records routing of {action_object.casefold()} "
            f"performed by the {actor_ref} and keeps source, destination, status, blockers, and handoff evidence visible"
        )
    actor_action = _human_actor_action(action, actor_ref=actor_ref)
    return (
        f"{title_case_text(f'{action_object} Workflow Support')} — records when the {actor_ref} {actor_action} and keeps "
        f"{action_object.casefold()} status, blockers, evidence, and handoff context visible"
    )


def _before_coordinated_action(value: str) -> str:
    text = clean_text(value).strip(" .")
    for match in re.finditer(r"\s+(?:and|or|then)\s+", text, flags=re.IGNORECASE):
        tail = text[match.end() :].strip(" .")
        if _non_human_subject_prefix(tail):
            return text[: match.start()].strip(" .")
        action = _action_without_subject(tail)
        if action and (action.casefold() == tail.casefold() or _explicit_action_subject(tail)):
            first = action.split(maxsplit=1)[0].casefold().strip(".,;:")
            if looks_like_base_action_token(base_action_verb(first)) or looks_like_finite_action_token(first):
                return text[: match.start()].strip(" .")
    return text


def _human_actor_action(value: str, *, actor_ref: str) -> str:
    actor_words = actor_ref.split()
    if actor_words and looks_plural(actor_words[-1]):
        return base_action_clause(value).strip(" .")
    return _finite_action(value)


def _ownership_steps(value: str, *, human_actors: Sequence[str]) -> list[str]:
    text = clean_text(value).strip(" .")
    if not text:
        return []
    for match in re.finditer(r"\s+(?:and|or|then)\s+", text, flags=re.IGNORECASE):
        head = text[: match.start()].strip(" .")
        tail = text[match.end() :].strip(" .")
        if not head or not tail:
            continue
        if _matching_human_subject(tail, human_actors=human_actors) or _non_human_subject_prefix(tail):
            return [head, tail]
    return [text]


def _non_human_subject_prefix(value: str) -> str:
    words = clean_text(value).strip(" .").split()
    if not words:
        return ""
    for end in range(1, min(5, len(words))):
        candidate = " ".join(words[:end]).strip(" ,.;:-")
        if has_non_human_actor_signal(candidate):
            return candidate
    return ""


def _action_after_subject(value: str, *, subject: str) -> str:
    text = clean_text(value).strip(" .")
    prefix = clean_text(subject).strip(" .")
    if not text or not prefix:
        return ""
    return re.sub(rf"^{re.escape(prefix)}\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .")


def _lower_sentence_start(value: str) -> str:
    text = clean_text(value).strip(" .")
    return text[:1].lower() + text[1:] if text else ""


def _action_verbs(value: str) -> list[str]:
    verbs: list[str] = []
    for segment in re.split(r"\s*,\s*(?:and\s+)?|\s+(?:and|or|then)\s+", clean_text(value), flags=re.IGNORECASE):
        first = next(iter(re.findall(r"[A-Za-z]+", segment)), "")
        base = base_action_verb(first)
        if base and (looks_like_base_action_token(base) or looks_like_finite_action_token(first)):
            verbs.append(base)
    return list(unique_text(verbs))


def _drop_repeated_leading_action(value: str, *, seen: set[str]) -> str:
    text = clean_text(value).strip(" .")
    match = re.match(r"^(?P<verb>[A-Za-z]+)\s+and\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
    if not match or base_action_verb(match.group("verb")) not in seen:
        return text
    return match.group("tail").strip(" .")


def _connector_clipped_action(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]+\s+(?:and|or)\b", clean_text(value).strip(" ."), flags=re.IGNORECASE))


def _finite_action(value: str) -> str:
    text = clean_text(value).strip(" .")
    action = _action_without_subject(clean_text(strip_action_subject(text)).strip(" .") or text)
    finite = finite_action_clause(action, default_verb="owns").strip(" .")
    return re.sub(
        r"\b(?P<connector>and|or)\s+(?P<verb>[A-Za-z]+)\b",
        lambda match: (
            f"{match.group('connector')} {third_person_action_verb(match.group('verb'))}"
            if looks_like_base_action_token(match.group("verb"))
            else match.group(0)
        ),
        finite,
        flags=re.IGNORECASE,
    )


def _join_labels(values: Sequence[str]) -> str:
    labels = list(unique_text(values))
    if not labels:
        return "Processing"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


__all__ = [
    "canonical_state_object_is_meaningful",
    "internal_system_rows_from_first_path",
    "product_handoff_first_path",
    "state_object_from_first_path",
]
