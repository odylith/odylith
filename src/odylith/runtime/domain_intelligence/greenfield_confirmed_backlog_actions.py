"""Action and actor grammar helpers for confirmed greenfield backlog rows."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_text_model as backlog_text
from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term
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
    if words & {"approved", "confirmed"}:
        return True
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
        action = backlog_text.capability_action_clause(_title_action_fragment(backlog_text.strip_actor_prefix(fallback, actor)))
        return _action_with_preservation_constraint(action, first_path=first_path)
    return ""


def actor_interaction_action(*, first_path: str, actor: str, fallback: str) -> str:
    selected = _actor_owned_action_fragments(first_path=first_path, actor=actor, include_visible=False, max_fragments=3)
    action = join_action_fragments(selected)
    return backlog_text.capability_action_clause(action or fallback)


def actor_appears_in_path(first_path: str, actor: str) -> bool:
    actor_label = backlog_text.actor_label(actor)
    actor_terms = _actor_match_terms(actor_label)
    actor_role_terms = _actor_role_match_terms(actor_label)
    if not actor_terms and not _actor_token_tuple(actor_label):
        return False
    for step in first_path_steps(first_path):
        signature = actor_signature(step)
        if _actor_phrase_present(actor_label, signature) or _actor_phrase_present(actor_label, step):
            return True
        signature_terms = _actor_match_terms(signature)
        if _actor_terms_match(actor_terms, actor_role_terms, signature_terms, candidate_is_signature=True):
            return True
        step_terms = _actor_match_terms(step)
        if _actor_terms_match(actor_terms, actor_role_terms, step_terms, candidate_is_signature=False):
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


def review_action_when_action_repeats_outcome(*, action: str, outcome: str) -> str:
    if not backlog_text.result_terms_covered(outcome, action):
        return ""
    text = backlog_text.sentence_fragment(outcome)
    result = re.sub(
        r"^(?:(?:a|an|the)\s+)?(?:accepted|approved|confirmed|published|saved|selected)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")
    if not result or result.casefold() == text.casefold():
        return ""
    if not result.casefold().startswith(("a ", "an ", "the ")):
        result = f"a {result}"
    return f"review {result}"


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
        return _known_actor_outcome_event(
            outcome=outcome,
            outcome_action=outcome_action,
            known_actors=known_actors or (),
        )
    known_terms = _known_actor_match_terms(known_actors or ())
    if known_terms and not (_actor_match_terms(actor) & known_terms):
        return ""
    if not (
        backlog_text.result_terms_covered(actor_action, outcome_action)
        or backlog_text.result_terms_covered(outcome_action, actor_action)
        or backlog_text.sentence_fragment(actor_action) == backlog_text.sentence_fragment(outcome_action)
    ):
        known_event = _known_actor_outcome_event(
            outcome=outcome,
            outcome_action=outcome_action,
            known_actors=known_actors or (),
        )
        return known_event
    return backlog_text.sentence_fragment(outcome)


def _known_actor_outcome_event(*, outcome: str, outcome_action: str, known_actors: Sequence[str]) -> str:
    for row in known_actors:
        label = backlog_text.actor_label(str(row))
        if not label:
            continue
        _head, separator, body = str(row).partition(":")
        action_source = body if separator else str(row)
        action = _actor_row_action(action_source)
        if not action:
            continue
        if (
            backlog_text.result_terms_covered(action, outcome)
            or backlog_text.result_terms_covered(outcome, action)
            or backlog_text.result_terms_covered(action, outcome_action)
            or backlog_text.result_terms_covered(outcome_action, action)
        ):
            return _actor_owned_event_fragment(label=label, action=action)
    return ""


def _actor_row_action(value: str) -> str:
    text = backlog_text.sentence_fragment(value)
    text = re.sub(r"^(?:needs?|need)\s+(?:the\s+product\s+)?to\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+and\s+keep\s+the\s+result\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
    return backlog_text.capability_action_clause(text) or action_chain_fragment(text)


def _actor_owned_event_fragment(*, label: str, action: str) -> str:
    actor = backlog_text.inline_actor_subject(label, fallback="")
    action_text = backlog_text.capability_action_clause(action) or backlog_text.sentence_fragment(action)
    if not actor or not action_text:
        return ""
    if re.match(r"^(?:use|uses)\s+the\s+product\s+to\b", action_text, flags=re.IGNORECASE):
        return backlog_text.inline_actor_event_fragment(label=label, action=action_text)
    is_plural = actor_verb(label, singular="singular", plural="plural") == "plural"
    if is_plural:
        actor = re.sub(r"^the\s+", "", actor, flags=re.IGNORECASE)
    match = re.match(r"^(?P<verb>[A-Za-z]+)\b(?P<tail>.*)$", action_text)
    if not match:
        return backlog_text.sentence_fragment(f"{actor} {action_text}")
    verb = base_action_clause(match.group("verb"))
    if not is_plural:
        verb = third_person_action_verb(verb)
    return backlog_text.sentence_fragment(f"{actor} {verb}{match.group('tail')}")


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
    actor_label = backlog_text.actor_label(actor)
    actor_terms = _actor_match_terms(actor_label)
    actor_role_terms = _actor_role_match_terms(actor_label)
    selected: list[str] = []
    selected_keys: set[str] = set()
    visible_seen = False
    for step in first_path_steps(first_path):
        if actor_terms:
            signature = actor_signature(step)
            matched_signature = _actor_phrase_present(actor_label, signature) or _actor_terms_match(
                actor_terms,
                actor_role_terms,
                _actor_match_terms(signature),
                candidate_is_signature=True,
            )
            matched_step = _actor_phrase_present(actor_label, step) or _actor_terms_match(
                actor_terms,
                actor_role_terms,
                _actor_match_terms(step),
                candidate_is_signature=False,
            )
            if not (matched_signature or matched_step):
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


def _actor_role_match_terms(value: str) -> set[str]:
    return {token for token in _actor_token_tuple(value) if looks_like_actor_role_term(token)}


def _actor_token_tuple(value: str) -> tuple[str, ...]:
    return tuple(word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", str(value or "")))


def _actor_phrase_present(actor: str, candidate: str) -> bool:
    actor_tokens = _actor_token_tuple(actor)
    candidate_tokens = _actor_token_tuple(candidate)
    if not actor_tokens or len(actor_tokens) > len(candidate_tokens):
        return False
    width = len(actor_tokens)
    return any(tuple(candidate_tokens[index : index + width]) == actor_tokens for index in range(0, len(candidate_tokens) - width + 1))


def _actor_terms_match(
    actor_terms: set[str],
    actor_role_terms: set[str],
    candidate_terms: set[str],
    *,
    candidate_is_signature: bool,
) -> bool:
    if not actor_terms or not candidate_terms:
        return False
    overlap = actor_terms & candidate_terms
    if not overlap:
        return False
    if actor_role_terms:
        return bool(actor_role_terms & candidate_terms)
    required_overlap = 1 if candidate_is_signature and len(actor_terms) == 1 else 2
    return len(overlap) >= min(required_overlap, len(actor_terms))


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
