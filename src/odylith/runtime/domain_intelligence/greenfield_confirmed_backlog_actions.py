"""Action and actor grammar helpers for confirmed greenfield backlog rows."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_text_model as backlog_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import looks_like_visible_result
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps


def prefer_outcome_title(value: str) -> bool:
    text = str(value or "").casefold()
    words = set(re.findall(r"[a-z][a-z0-9'-]*", text))
    weak = {"consequence", "recap", "reflection"}
    if words & weak:
        return False
    strong = {
        "confirmation",
        "decision",
        "estimate",
        "evidence",
        "plan",
        "recommendation",
        "report",
        "result",
        "status",
        "summary",
    }
    return bool(words & strong)


def workflow_title_action(*, first_path: str, actor: str, fallback: str) -> str:
    fragments = _actor_owned_action_fragments(first_path=first_path, actor=actor, include_visible=False, max_fragments=4)
    terminal = _preferred_terminal_fragment(fragments)
    if terminal:
        action = backlog_text.capability_action_clause(backlog_text.sentence_fragment(terminal))
        if action:
            return _action_with_preservation_constraint(action, first_path=first_path)
    if len(fragments) > 1 and ("," in fragments[0] or "(" in fragments[0]):
        action = backlog_text.capability_action_clause(f"{fragments[0]}, {fragments[1]}")
        if action:
            return _action_with_preservation_constraint(action, first_path=first_path)
    selected = _preferred_title_fragment(fragments)
    if selected:
        action = backlog_text.capability_action_clause(_title_action_fragment(selected))
        if action:
            return _action_with_preservation_constraint(action, first_path=first_path)
    if fallback:
        action = backlog_text.capability_action_clause(_title_action_fragment(fallback))
        return _action_with_preservation_constraint(action, first_path=first_path)
    return ""


def actor_interaction_action(*, first_path: str, actor: str, fallback: str) -> str:
    selected = _actor_owned_action_fragments(first_path=first_path, actor=actor, include_visible=False, max_fragments=3)
    action = join_action_fragments(selected)
    return backlog_text.capability_action_clause(action or fallback)


def actor_appears_in_path(first_path: str, actor: str) -> bool:
    actor_terms = _actor_match_terms(actor)
    if not actor_terms:
        return False
    for step in first_path_steps(first_path):
        signature_terms = _actor_match_terms(actor_signature(step))
        if signature_terms and signature_terms & actor_terms:
            return True
        step_terms = _actor_match_terms(step)
        if step_terms and step_terms & actor_terms:
            return True
    return False


def append_outcome_action(
    *,
    action: str,
    outcome: str,
    outcome_action: str,
    recipient: str,
    known_actors: Sequence[str] | None = None,
) -> str:
    if backlog_text.result_terms_covered(outcome, action) or backlog_text.result_terms_covered(outcome_action, action):
        return ""
    actor_event = actor_owned_outcome_event(
        outcome=outcome,
        outcome_action=outcome_action,
        known_actors=known_actors,
    )
    if actor_event:
        return f", and the product shows that {actor_event}"
    return f", and {recipient_phrase(recipient)} can {outcome_action}" if outcome_action else ""


def missing_input_tail(*, action: str, outcome: str, outcome_already_appended: bool = False) -> str:
    if outcome_already_appended:
        return " while the product gives clear correction guidance when required information is missing"
    if backlog_text.result_terms_covered(outcome, action):
        return " with clear correction guidance when required information is missing"
    return ", and see what to fix when required information is missing"


def workflow_result_sentence(
    *,
    action: str,
    outcome: str,
    outcome_action: str,
    recipient: str,
    known_actors: Sequence[str] | None = None,
) -> str:
    if backlog_text.result_terms_covered(outcome, action) or backlog_text.result_terms_covered(outcome_action, action):
        return "and keeps the saved result reviewable"
    actor_event = actor_owned_outcome_event(
        outcome=outcome,
        outcome_action=outcome_action,
        known_actors=known_actors,
    )
    if actor_event:
        return f"and shows that {actor_event}"
    return f"and lets {recipient_phrase(recipient)} {outcome_action}"


def actor_owned_outcome_event(
    *,
    outcome: str,
    outcome_action: str,
    known_actors: Sequence[str] | None = None,
) -> str:
    """Return an outcome event that already names the actor who performs it."""

    actor, actor_action = backlog_text.actor_action_parts(outcome)
    if not actor or not actor_action:
        actor = actor_signature(outcome)
        actor_action = action_chain_fragment(outcome)
    if not actor or not actor_action:
        return ""
    known_terms = _known_actor_match_terms(known_actors or ())
    if known_terms and not (_actor_match_terms(actor) & known_terms):
        return ""
    if not (
        backlog_text.result_terms_covered(actor_action, outcome_action)
        or backlog_text.result_terms_covered(outcome_action, actor_action)
        or backlog_text.sentence_fragment(actor_action) == backlog_text.sentence_fragment(outcome_action)
    ):
        return ""
    return backlog_text.sentence_fragment(outcome)


def _known_actor_match_terms(values: Sequence[str]) -> set[str]:
    terms: set[str] = set()
    for value in values:
        terms |= _actor_match_terms(backlog_text.actor_label(str(value)))
    return terms


def recipient_phrase(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .")
    if not text:
        return "the user"
    text = backlog_text.inline_actor_subject(text)
    if text.startswith(("the ", "a ", "an ", "one ", "this ", "that ", "each ")):
        return text
    if re.match(r"^[A-Z][A-Za-z0-9' -]*$", text):
        return f"the {backlog_text.inline_actor_subject(text)}"
    return text


def join_distinct_labels(values: list[str | None]) -> str:
    labels: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip(" .")
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        labels.append(text)
        seen.add(key)
    return backlog_text.join_actor_labels(labels, limit=3)


def join_action_fragments(values: list[str]) -> str:
    fragments = [str(value or "").strip(" .") for value in values if str(value or "").strip(" .")]
    if not fragments:
        return ""
    if len(fragments) == 1:
        return fragments[0]
    if len(fragments) == 2:
        return f"{fragments[0]} and {fragments[1]}"
    return f"{', '.join(fragments[:-1])}, and {fragments[-1]}"


def actor_verb(subject: str, *, singular: str, plural: str) -> str:
    text = re.sub(r"\s+", " ", str(subject or "")).strip(" .").casefold()
    text = re.sub(r"^(?:the|these|those|a|an|one|this|that|each)\s+", "", text).strip()
    if not text:
        return singular
    if " and " in text or "," in text:
        return plural
    first = text.split(maxsplit=1)[0]
    plural_heads = {"people", "users", "customers", "operators", "reviewers", "participants", "teams", "leads"}
    if first in plural_heads:
        return plural
    words = text.split()
    if len(words) > 1 and not words[0].endswith("s") and words[1].endswith("ing"):
        return singular
    if words and words[-1].endswith("s") and not words[-1].endswith("ss"):
        return plural
    return singular


def dedupe_repeated_visible_result_tail(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .")
    if not text:
        return ""
    match = re.match(
        r"^(?P<head>.+?),?\s+and\s+(?:see|use|view|read|receive)\s+(?P<tail>[^.]+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return f"{text}."
    head = match.group("head").strip(" ,.")
    tail = match.group("tail").strip(" ,.")
    if backlog_text.result_terms_covered(tail, head):
        return f"{head}."
    return f"{text}."


def state_responsibility_label(state_label: str) -> str:
    text = str(state_label or "").strip(" .")
    if not text:
        return "State responsibility"
    if text.casefold().endswith(" state"):
        return f"{text} responsibility"
    return f"{text} state responsibility"


def parent_opportunity_sentence(
    *,
    capability: str,
    outcome: str,
    outcome_action: str,
    outcome_event: str,
    state_label: str,
    recipient: str,
) -> str:
    proof_subject = _proof_subject_phrase(capability)
    if outcome_action and not _terms_covered(outcome_action, capability) and not _terms_covered(outcome, capability):
        outcome_followup = f"show that {outcome_event}" if outcome_event else f"let {recipient} {outcome_action}"
        return f"Prove the first release path: {proof_subject}, then {outcome_followup}."
    return f"Prove the first release path: {proof_subject}. Keep {state_label} reviewable through success, blocked, and replay evidence."


def parent_product_view_sentence(
    *,
    label: str,
    capability: str,
    outcome: str,
    outcome_action: str,
    outcome_event: str,
    state_label: str,
    recipient: str,
) -> str:
    proof_subject = _proof_subject_phrase(capability)
    if outcome_action and not _terms_covered(outcome_action, capability) and not _terms_covered(outcome, capability):
        outcome_followup = f"showing that {outcome_event}" if outcome_event else f"letting {recipient} {outcome_action}"
        return (
            f"{label} should feel complete when the accepted first path proves {proof_subject} "
            f"while {outcome_followup} and keeping the first-release boundary clear."
        )
    return (
        f"{label} should feel complete when the accepted first path proves {proof_subject} "
        f"while keeping {state_label} clear and making the first-release boundary explicit."
    )


def _preferred_title_fragment(values: list[str]) -> str:
    fragments = [backlog_text.sentence_fragment(value) for value in values if backlog_text.sentence_fragment(value)]
    if not fragments:
        return ""
    first = fragments[0]
    if not _skip_title_setup_fragment(first):
        return first
    for fragment in fragments[1:]:
        if not _skip_title_setup_fragment(fragment):
            return fragment
    return first


def _title_action_fragment(value: str) -> str:
    text = backlog_text.sentence_fragment(value).strip(" .")
    constrained = _compact_preservation_constraint(text)
    return constrained or text


def _action_with_preservation_constraint(action: str, *, first_path: str) -> str:
    text = str(action or "").strip(" .")
    constraint = _preservation_constraint(first_path)
    if not text or not constraint or constraint.casefold() in text.casefold():
        return text
    head = _compact_action_head_for_constraint(text)
    return f"{head or text} with {constraint}"


def _compact_preservation_constraint(value: str) -> str:
    text = str(value or "").strip(" .")
    constraint = _preservation_constraint(text)
    if not constraint:
        return ""
    if not _useful_preservation_constraint(constraint):
        return ""
    marker = "while keeping "
    index = text.casefold().find(marker)
    if index < 0:
        return ""
    before = text[:index].strip(" ,.")
    action_head = _compact_action_head_for_constraint(before)
    if not action_head:
        return ""
    return f"{action_head} with {constraint}"


def _preservation_constraint(value: str) -> str:
    text = str(value or "")
    marker = "while keeping "
    index = text.casefold().find(marker)
    if index < 0:
        return ""
    tail = text[index + len(marker) :]
    constraint = backlog_text.sentence_fragment(_until_boundary(tail)).strip(" ,.")
    return constraint if _useful_preservation_constraint(constraint) else ""


def _useful_preservation_constraint(value: str) -> bool:
    words = backlog_text.semantic_words(value)
    if len(words) < 2 or len(words) > 8:
        return False
    return bool(words & {"clear", "separate", "trusted", "visible", "reviewable", "limited", "bounded"})


def _compact_action_head_for_constraint(value: str) -> str:
    pieces = [
        backlog_text.sentence_fragment(piece).strip(" .")
        for piece in _action_head_pieces(value)
    ]
    for piece in pieces:
        if piece and not _skip_title_setup_fragment(piece):
            return piece
    return next((piece for piece in pieces if piece), "")


def _action_head_pieces(value: str) -> tuple[str, ...]:
    text = str(value or "")
    pieces: list[str] = []
    for comma_part in text.split(","):
        remaining = comma_part.strip()
        while True:
            index = remaining.casefold().find(" and ")
            if index < 0:
                break
            pieces.append(remaining[:index])
            remaining = remaining[index + len(" and ") :]
        pieces.append(remaining)
    return tuple(piece for piece in pieces if piece.strip())


def _until_boundary(value: str) -> str:
    text = str(value or "")
    indexes = [index for mark in ".;" if (index := text.find(mark)) >= 0]
    if not indexes:
        return text
    return text[: min(indexes)]


def _preferred_terminal_fragment(values: list[str]) -> str:
    fragments = [backlog_text.sentence_fragment(value) for value in values if backlog_text.sentence_fragment(value)]
    if len(fragments) < 2:
        return ""
    for fragment in reversed(fragments):
        if re.match(
            r"^(?:accept|approve|complete|finalize|finish|publish|release|send|submit)\b",
            fragment,
            flags=re.IGNORECASE,
        ):
            return fragment
    return ""


def _skip_title_setup_fragment(value: str) -> bool:
    text = str(value or "").strip()
    if re.match(r"^(?:open|launch|start|visit|view)\b", text, flags=re.IGNORECASE):
        return True
    return bool(
        re.match(
            r"^(?:add|create|set\s+up)\s+(?:one\s+|a\s+|an\s+|the\s+)?"
            r"(?:account|asset|child|learner\s+profile|profile|record|workspace)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _actor_owned_action_fragments(*, first_path: str, actor: str, include_visible: bool, max_fragments: int) -> list[str]:
    actor_terms = _actor_match_terms(actor)
    selected: list[str] = []
    selected_keys: set[str] = set()
    visible_seen = False
    for step in first_path_steps(first_path):
        signature_terms = _actor_match_terms(actor_signature(step))
        if actor_terms:
            step_terms = _actor_match_terms(step)
            matched_actor = bool((signature_terms | step_terms) & actor_terms)
            if not matched_actor:
                if selected and visible_seen:
                    break
                continue
        step_visible = bool(visible_result_object(step) or looks_like_visible_result(step))
        if step_visible and not include_visible:
            if selected:
                break
            continue
        fragment = backlog_text.sentence_fragment(action_chain_fragment(step))
        fragment = backlog_text.base_leading_action(backlog_text.strip_actor_prefix(fragment, actor))
        key = fragment.casefold()
        if fragment and key not in selected_keys:
            selected.append(fragment)
            selected_keys.add(key)
        visible_seen = visible_seen or step_visible
        if step_visible and selected:
            break
        if len(selected) >= max_fragments:
            break
    return selected


def _actor_match_terms(value: str) -> set[str]:
    terms: set[str] = set()
    for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", str(value or "")):
        token = word.casefold()
        terms.add(token)
        singular = _singular_actor_match_term(token)
        if singular:
            terms.add(singular)
    return terms - {"actor", "later", "primary", "reviewer", "user"}


def _singular_actor_match_term(value: str) -> str:
    token = str(value or "").casefold().strip(" .")
    if len(token) <= 3 or token.endswith(("ics", "ss", "us")):
        return ""
    if token.endswith("ies"):
        return f"{token[:-3]}y"
    if token.endswith("s"):
        return token[:-1]
    return ""


def _proof_subject_phrase(value: str) -> str:
    phrase = backlog_text.proof_action_subject(value)
    return phrase or value


def _terms_covered(needle: str, haystack: str) -> bool:
    return backlog_text.result_terms_covered(needle, haystack)


__all__ = [
    "actor_verb",
    "actor_appears_in_path",
    "actor_interaction_action",
    "actor_owned_outcome_event",
    "append_outcome_action",
    "dedupe_repeated_visible_result_tail",
    "join_action_fragments",
    "join_distinct_labels",
    "missing_input_tail",
    "parent_opportunity_sentence",
    "parent_product_view_sentence",
    "prefer_outcome_title",
    "recipient_phrase",
    "state_responsibility_label",
    "workflow_result_sentence",
    "workflow_title_action",
]
