"""Canonical state and responsibility projections from a Greenfield first path."""

from __future__ import annotations

import re
from collections.abc import Sequence

from odylith.runtime.common.prose_grammar import base_action_verb
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.common.prose_grammar import strip_leading_action_modal
from odylith.runtime.common.prose_grammar import strip_trailing_subject_modal
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_action_homonym_actor_role
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_non_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import indefinite_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import looks_plural
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import strip_action_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import (
    source_boundary_rows_from_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import singularize_last_word
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_transfer_phrases import transfer_object_phrase


_ACTION_RESPONSIBILITIES = (
    (frozenset({"add", "attach", "capture", "collect", "create", "enter", "intake", "open", "receive", "register", "submit", "upload"}), "Intake"),
    (frozenset({"assign"}), "Assignment"),
    (frozenset({"approve"}), "Approval"),
    (frozenset({"calculate", "compute"}), "Calculation"),
    (frozenset({"choose", "select"}), "Selection"),
    (frozenset({"cluster", "group", "organize"}), "Organization"),
    (frozenset({"coordinate"}), "Coordination"),
    (frozenset({"decompose"}), "Decomposition"),
    (frozenset({"decide"}), "Decision"),
    (frozenset({"deliver", "display", "hand", "publish", "release", "return", "see", "show", "surface"}), "Delivery"),
    (frozenset({"draft"}), "Drafting"),
    (frozenset({"generate", "produce"}), "Generation"),
    (frozenset({"match"}), "Matching"),
    (frozenset({"route"}), "Routing"),
    (frozenset({"log", "preserve", "record", "save", "store", "track"}), "Recordkeeping"),
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
_CONTEXTUAL_ON_RE = r"on(?!\s+(?:file|hand|hold|record)\b)"


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


def state_object_from_first_path(
    first_path: str,
    *,
    fallback: str,
    preferred_action: str = "",
) -> str:
    """Return the durable object changed by the first material action."""

    model = first_path_model(first_path)
    action = _action_without_subject(
        clean_text(preferred_action).strip(" .")
        or (model.steps[0] if model.steps else "")
        or model.material_action
    )
    subject = _state_transition_object(first_path) or _action_object(action)
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


def _state_transition_object(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return ""
    changed_subject = re.search(
        r"(?:^|[.!?;]\s+)(?P<object>(?:(?:a|an|the)\s+)?"
        r"[A-Za-z0-9][A-Za-z0-9'/-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'/-]*){0,4}?)\s+"
        r"(?:becomes?|turns?)\s+",
        text,
        flags=re.IGNORECASE,
    )
    if changed_subject:
        subject = changed_subject.group("object").strip(" .")
        if not has_actor_role_word(subject) and not has_non_human_actor_signal(subject):
            return re.sub(r"^(?:a|an|the)\s+", "", subject, flags=re.IGNORECASE)
    moved_object = re.search(
        r"\b(?:moves?|moved)\s+(?P<object>(?:a|an|the)\s+[A-Za-z0-9][A-Za-z0-9'/-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'/-]*){0,4}?)\s+"
        r"(?:from|into|to)\b[^.;]{0,100}\bstate\b",
        text,
        flags=re.IGNORECASE,
    )
    if moved_object:
        return moved_object.group("object").strip(" .")
    kept_object = re.search(
        r"\b(?:keeps?|kept)\s+(?P<object>(?:a|an|the)\s+[A-Za-z0-9][A-Za-z0-9'/-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'/-]*){0,4})\s+"
        r"(?:in|within)\b[^.;]{0,100}\bstate\b",
        text,
        flags=re.IGNORECASE,
    )
    if kept_object:
        return kept_object.group("object").strip(" .")
    entered = re.search(
        r"(?:^|[:.;]\s+)(?P<object>(?:(?:a|an|the)\s+)?"
        r"[A-Za-z0-9][A-Za-z0-9'/-]*(?:\s+[A-Za-z0-9][A-Za-z0-9'/-]*){0,4}?)\s+"
        r"(?:enters?|entered)\s+[^.;]{1,100}\bstate\b",
        text,
        flags=re.IGNORECASE,
    )
    if entered:
        return entered.group("object").strip(" .")
    placed = re.search(
        r"\b(?P<verb>[A-Za-z][A-Za-z'-]*)\s+(?P<object>(?:a|an|the)\s+[^,.;]{1,80}?)\s+"
        r"and\s+places?\s+it\s+in\s+[^.;]{1,100}\bstate\b",
        text,
        flags=re.IGNORECASE,
    )
    if placed and (
        looks_like_base_action_token(base_action_verb(placed.group("verb")))
        or looks_like_finite_action_token(placed.group("verb"))
    ):
        return placed.group("object").strip(" .")
    return ""


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
    external_systems: Sequence[str] = (),
) -> list[str]:
    """Project distinct product responsibilities from first-path actions."""

    model = first_path_model(first_path)
    steps = [
        owned_step
        for step in model.steps
        if clean_text(step).strip(" .")
        and not _external_source_only_step(step, external_systems=external_systems)
        for owned_step in _ownership_steps(clean_text(step).strip(" ."), human_actors=human_actors)
    ]
    if not steps:
        return []
    state_label = _state_label(state_object, fallback=title)
    result_label = _compact_label(visible_result or model.visible_outcome, fallback="Result", max_words=5)
    rows: list[str] = []
    used_responsibilities: set[str] = set()
    merged_nominal_steps: set[int] = set()
    for index, step in enumerate(steps):
        if index in merged_nominal_steps:
            continue
        human_subject = _matching_human_subject(step, human_actors=human_actors)
        nominal_row = _nominal_responsibility_row(
            step,
            human_subject=human_subject,
            source_first_path=first_path,
        )
        if nominal_row:
            rows.append(nominal_row)
            continue
        if human_subject:
            action = _action_after_subject(step, subject=human_subject) or _action_without_subject(step)
            if "Coordination" in _responsibility_labels(action, step=action) and index + 1 < len(steps):
                next_step = steps[index + 1]
                if _nominal_responsibility_row(
                    next_step,
                    human_subject="",
                    source_first_path=first_path,
                ):
                    action = f"{action}, {_lower_sentence_start(next_step)}"
                    merged_nominal_steps.add(index + 1)
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
        gate_subject = _copular_gate_subject(step)
        action_label = _compact_label(
            gate_subject or _action_object_for_owned_clause(action, has_subject=bool(non_human_subject)),
            fallback=state_label,
            max_words=4,
        )
        if gate_subject:
            name = f"{action_label} Validation"
            description = (
                f"enforces {action_label.casefold()} as the release gate and keeps blocked reason, "
                "validation evidence, and release status visible"
            )
        elif index == 0 and "Intake" in responsibilities:
            name = f"{state_label} Intake"
            description = (
                f"captures {state_label.casefold()} input and required context and exposes either a validated or blocked state"
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
            if any(label in {"Approval", "Assignment", "Selection"} for label in responsibilities):
                action_label = singularize_last_word(action_label)
            name = f"{action_label} Workflow" if responsibilities == ["Processing"] else f"{action_label} {suffix}"
            owned_action = _lower_sentence_start(step) if non_human_subject else _finite_action(step)
            description = f"{owned_action} and keeps status, ownership, blockers, and handoff context"
        rows.append(f"{title_case_text(name)} — {description.rstrip('.')}")
    exception_row = _exception_review_system_row(first_path=first_path, state_label=state_label)
    removed_signoff_duplicate = False
    if exception_row:
        retained_rows = [row for row in rows if not _standalone_signoff_record(row)]
        removed_signoff_duplicate = len(retained_rows) != len(rows)
        rows = retained_rows
        if not any("exception" in row.split("—", 1)[0].casefold() for row in rows):
            rows.insert(max(1, len(rows) - 1), exception_row)
    decision_row = _decision_signoff_system_row(first_path=first_path)
    if decision_row and not any(
        {"decision", "signoff"} <= set(re.findall(r"[a-z]+", row.split("—", 1)[0].casefold()))
        for row in rows
    ):
        rows.insert(max(1, len(rows) - 1), decision_row)
    if len(rows) == 1 or (removed_signoff_duplicate and len(rows) < 3):
        rows.append(_result_review_system_row(result_label))
    return list(unique_text(rows))


def _external_source_only_step(value: str, *, external_systems: Sequence[str]) -> bool:
    known_sources = {
        clean_text(source).casefold().strip(" .")
        for source in external_systems
        if clean_text(source)
    }
    if not known_sources:
        return False
    cited_sources = {
        clean_text(source).casefold().strip(" .") for source in source_boundary_rows_from_evidence(value)
    }
    if not cited_sources & known_sources:
        return False
    action = strip_leading_action_modal(_action_without_subject(value))
    words = clean_text(action).casefold().strip(" .").split()
    if len(words) < 2:
        return False
    object_words = words[1:]
    while object_words and object_words[0] in _LEADING_OBJECT_WORDS:
        object_words.pop(0)
    return " ".join(object_words) in known_sources


def _exception_review_system_row(*, first_path: str, state_label: str) -> str:
    text = clean_text(first_path)
    if not re.search(r"\bexceptions?\b", text, flags=re.IGNORECASE):
        return ""
    if not re.search(
        r"\b(?:approv(?:al|e[sd]?)|authori[sz](?:ation|e[sd]?)|decision|sign[ -]?off|waiver)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return ""
    return (
        f"{title_case_text(f'{state_label} Exception Review')} — records exception disposition and signoff for the "
        "accepted path with owner, source evidence, blocked reason, and handoff state visible"
    )


def _decision_signoff_system_row(*, first_path: str) -> str:
    text = clean_text(first_path)
    if not re.search(r"\bdecisions?\b", text, flags=re.IGNORECASE):
        return ""
    if not re.search(
        r"\b(?:approv(?:al|e[sd]?)|authori[sz](?:ation|e[sd]?)|sign[ -]?off)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return ""
    return (
        "Decision and Signoff Review — records the accepted decision and signoff with owner, source evidence, "
        "blocked reason, and handoff state visible"
    )


def _standalone_signoff_record(row: str) -> bool:
    name = clean_text(row).split("—", 1)[0].casefold().strip()
    return bool(re.fullmatch(r"(?:operator\s+)?sign[ -]?off record", name))


def _result_review_system_row(result_label: str) -> str:
    return (
        f"{title_case_text(f'{result_label} Review')} — presents the completed result, known limits, "
        "failure reason, and evidence needed for the next decision"
    )


def _nominal_responsibility_row(step: str, *, human_subject: str, source_first_path: str) -> str:
    if human_subject:
        return ""
    text = clean_text(step).strip(" .")
    if not text:
        return ""
    subject = _explicit_action_subject(text)
    action = _action_after_subject(text, subject=subject) or text
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", action)
    if not words:
        return ""
    first = words[0].casefold()
    base = base_action_verb(first)
    base_action = looks_like_base_action_token(base)
    finite_action = looks_like_finite_action_token(first)
    comma_head = text.split(",", 1)[0].strip()
    comma_head_words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", comma_head)
    action_shaped_list_head = bool(
        "," in text
        and comma_head_words
        and looks_like_finite_action_token(comma_head_words[-1].casefold())
    )
    if subject:
        nominal = not has_actor_role_word(subject) and (
            (base_action and not finite_action) or action_shaped_list_head
        )
    else:
        nominal = (
            len(words) == 2
            and base_action
            and not finite_action
            and _source_list_context_is_nominal(source_first_path, text)
        )
    if not nominal:
        return ""
    label_source = comma_head if comma_head else text
    label = _compact_label(label_source, fallback="Evidence", max_words=5)
    name = label if label.casefold().endswith("record") else f"{label} Record"
    detail = text[:1].casefold() + text[1:]
    return (
        f"{title_case_text(name)} — maintains {detail} with provenance, status, blockers, and handoff context"
    )


def _source_list_context_is_nominal(source: str, item: str) -> bool:
    segments = [clean_text(part).strip(" .") for part in clean_text(source).split(",")]
    item_key = clean_text(item).casefold().strip(" .")
    for index, segment in enumerate(segments):
        segment_key = re.sub(r"^(?:and|or)\s+", "", segment, flags=re.IGNORECASE).casefold()
        if not segment_key.startswith(item_key) or index < 2:
            continue
        prior = [re.sub(r"^(?:and|or)\s+", "", row, flags=re.IGNORECASE) for row in segments[index - 2 : index]]
        if all(not _starts_with_material_action(row) for row in prior):
            return True
    return False


def _starts_with_material_action(value: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", clean_text(value))
    if not words:
        return False
    first = words[0].casefold()
    return looks_like_base_action_token(base_action_verb(first)) or looks_like_finite_action_token(first)


def _action_object(value: str) -> str:
    action = _action_without_subject(value)
    carried_object = transfer_object_phrase(action)
    if carried_object:
        return carried_object
    words = action.split()
    if words:
        first = words[0].casefold().strip(".,;:")
        base = base_action_verb(first)
        if looks_like_base_action_token(base) or looks_like_finite_action_token(first):
            object_start = (
                2 if base == "start" and len(words) > 1 and words[1].casefold() == "with" else 1
            )
            action = " ".join(words[object_start:]).strip(" .")
    chained_action = re.match(
        r"^(?:and|or|then)\s+(?P<verb>[A-Za-z][A-Za-z'-]*)\s+(?P<object>.+)$",
        action,
        flags=re.IGNORECASE,
    )
    if chained_action:
        verb = chained_action.group("verb").casefold()
        base = base_action_verb(verb)
        if looks_like_base_action_token(base) or looks_like_finite_action_token(verb):
            action = chained_action.group("object").strip(" .")
    into_match = re.search(r"\binto\s+(?P<object>(?:a|an|the|one)?\s*[^.;]+)$", action, flags=re.IGNORECASE)
    text = clean_text(into_match.group("object") if into_match else strip_action(action)).strip(" .")
    text = re.split(r"\s*,\s*", text, maxsplit=1)[0]
    words = text.split()
    while words and words[0].casefold().strip(".,;:") in _ACTION_OBJECT_LEADING_WORDS:
        words.pop(0)
    text = " ".join(words).strip(" .")
    text = _before_coordinated_action(text)
    text = re.split(
        rf"\s+(?:based on|for|from|{_CONTEXTUAL_ON_RE}|so that|such as|through|to|until|using|with|without)\s+",
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
    text = re.sub(r"\s*:\s*", " ", text)
    text = re.split(
        rf"\s+(?:after|based on|before|for|from|{_CONTEXTUAL_ON_RE}|so that|such as|through|using|with|without)\s+",
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
    if _copular_gate_subject(step):
        return ["Validation"]
    tokens = set(_action_verbs(_action_without_subject(action)))
    if re.search(r"\bvalidat(?:e[sd]?|ing)\b", step, flags=re.IGNORECASE):
        tokens.add("validate")
    labels = [label for verbs, label in _ACTION_RESPONSIBILITIES if verbs & tokens]
    return list(unique_text(labels))


def _action_without_subject(value: str) -> str:
    text = clean_text(value).strip(" .")
    words = text.split()
    for index in range(1, min(5, len(words) - 1) + 1):
        actor = " ".join(words[:index]).strip(" .")
        action = " ".join(words[index:]).strip(" .")
        if has_action_homonym_actor_role(actor, action):
            return action
    stripped = clean_text(strip_action_subject(text)).strip(" .")
    if stripped and stripped.casefold() != text.casefold():
        return stripped
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
    return strip_trailing_subject_modal(subject)


def _sentence_start(value: str) -> str:
    text = clean_text(value).strip(" .")
    return text[:1].upper() + text[1:] if text else ""


def _matching_human_subject(value: str, *, human_actors: Sequence[str]) -> str:
    text = clean_text(value).strip(" .")
    for row in human_actors:
        label = re.split(r"\s*(?::|—|–)\s*|\s+-\s+", clean_text(row), maxsplit=1)[0].strip(" .")
        if not label:
            continue
        match = _subject_prefix_match(text, label)
        if not match:
            continue
        action = strip_leading_action_modal(text[match.end() :].strip(" ."))
        if _starts_with_material_action(action):
            return match.group("subject")
    subject = _explicit_action_subject(value)
    subject_key = _actor_key(subject)
    if not subject_key:
        return ""
    for row in human_actors:
        label = re.split(r"\s*(?::|—|–)\s*|\s+-\s+", clean_text(row), maxsplit=1)[0]
        label_key = _actor_key(label)
        if label_key and (subject_key == label_key or subject_key.endswith(f" {label_key}")):
            return subject
    return ""


def _actor_key(value: str) -> str:
    words = clean_text(value).casefold().strip(" .").split()
    while words and words[0] in _LEADING_OBJECT_WORDS:
        words.pop(0)
    return " ".join(words)


def _subject_prefix_match(value: str, subject: str) -> re.Match[str] | None:
    article = subject.split(maxsplit=1)[0].casefold()
    optional_article = "" if article in {"a", "an", "the", "one"} else r"(?:(?:a|an|the|one)\s+)?"
    return re.match(rf"^(?P<subject>{optional_article}{re.escape(subject)})\s+", value, flags=re.IGNORECASE)


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
    leading_action = clean_text(action).split(",", 1)[0].strip(" .")
    owned_action = leading_action if _starts_with_material_action(leading_action) else action
    action_object = _compact_label(_action_object(owned_action), fallback=state_label, max_words=4)
    responsibilities = _responsibility_labels(owned_action, step=owned_action)
    actor_ref = _actor_key(actor) or "user"
    actor_action = _human_actor_action(action, actor_ref=actor_ref)
    action_note = f"; First-path action is the {actor_ref} {actor_action}"
    if "Intake" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Intake')} — owns {action_object.casefold()} intake records, status, "
            f"blockers, evidence, and handoff context{action_note}"
        )
    if "Delivery" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Delivery')} — presents {action_object.casefold()} as the visible result "
            f"to the {actor_ref} with status, blockers, explanation, and review evidence{action_note}"
        )
    if "Decision" in responsibilities:
        decision_subject = _decision_subject_label(action_object)
        return (
            f"{title_case_text(f'{decision_subject} Decision Record')} — records the {actor_ref} decision and keeps "
            f"status, rationale, blockers, evidence, and handoff context visible{action_note}"
        )
    if any(label in {"Approval", "Assignment", "Selection"} for label in responsibilities):
        suffix = _join_labels(responsibilities)
        return (
            f"{title_case_text(f'{action_object} {suffix} Record')} — records the {actor_ref} decision and keeps "
            f"status, blockers, evidence, and handoff context visible{action_note}"
        )
    if "Review" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Review Record')} — owns {action_object.casefold()} review records, "
            f"status, blockers, evidence, and handoff context{action_note}"
        )
    if "Recordkeeping" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Recordkeeping')} — owns {action_object.casefold()} records, status, "
            f"correction history, blockers, and handoff context{action_note}"
        )
    if "Coordination" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Coordination')} — owns {action_object.casefold()} coordination records, "
            f"status, blockers, evidence, and handoff context{action_note}"
        )
    if "Validation" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Workflow Support')} — records {action_object.casefold()} validation "
            f"performed by the {actor_ref} and keeps validation status, blockers, evidence, and handoff context visible{action_note}"
        )
    if "Routing" in responsibilities:
        return (
            f"{title_case_text(f'{action_object} Workflow Support')} — records routing of {action_object.casefold()} "
            f"performed by the {actor_ref} and keeps source, destination, status, blockers, and handoff evidence visible{action_note}"
        )
    return (
        f"{title_case_text(f'{action_object} Workflow Support')} — owns {action_object.casefold()} workflow status, "
        f"blockers, evidence, and handoff context{action_note}"
    )


def _decision_subject_label(value: str) -> str:
    words = clean_text(value).casefold().strip(" .").split()
    if words == ["what", "is", "ready"]:
        return "Readiness"
    if words and words[0] in {"what", "whether"}:
        return "Outcome"
    return value


def _human_actor_action(value: str, *, actor_ref: str) -> str:
    actor_words = actor_ref.split()
    if actor_words and looks_plural(actor_words[-1]):
        return base_action_clause(value).strip(" .")
    return _finite_action(value)


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
    gate_subject = _copular_gate_subject(value)
    if gate_subject:
        return gate_subject
    words = clean_text(value).strip(" .").split()
    if not words:
        return ""
    first = words[0].casefold().strip(".,;:")
    if looks_like_base_action_token(base_action_verb(first)) or looks_like_finite_action_token(first):
        return ""
    for end in range(1, min(5, len(words))):
        candidate = " ".join(words[:end]).strip(" ,.;:-")
        if has_non_human_actor_signal(candidate):
            return candidate
    return ""


def _copular_gate_subject(value: str) -> str:
    """Return the state subject in ``<state> is/are the ... gate`` clauses."""

    words = [word.strip(".,;:()[]{}") for word in clean_text(value).split() if word.strip(".,;:()[]{}")]
    lowered = [word.casefold() for word in words]
    for index, token in enumerate(lowered):
        if token not in {"are", "is", "was", "were"} or not 1 <= index <= 5:
            continue
        if "gate" not in lowered[index + 1 :]:
            continue
        subject_words = words[:index]
        if subject_words and subject_words[0].casefold() in {"a", "an", "the"}:
            subject_words = subject_words[1:]
        subject = " ".join(subject_words).strip(" .")
        if subject and not has_actor_role_word(subject):
            return subject
    return ""


def _action_after_subject(value: str, *, subject: str) -> str:
    text = clean_text(value).strip(" .")
    prefix = clean_text(subject).strip(" .")
    if not text or not prefix:
        return ""
    match = _subject_prefix_match(text, prefix)
    if not match:
        return ""
    return strip_leading_action_modal(text[match.end() :].strip(" ."))


def _lower_sentence_start(value: str) -> str:
    text = clean_text(value).strip(" .")
    return text[:1].lower() + text[1:] if text else ""


def _action_verbs(value: str) -> list[str]:
    verbs: list[str] = []
    source = clean_text(value)
    for segment in re.split(r"\s*,\s*(?:and\s+)?|\s+(?:and|or|then)\s+", source, flags=re.IGNORECASE):
        if _source_list_context_is_nominal(source, segment):
            continue
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
