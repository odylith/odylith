"""Action and actor grammar helpers for confirmed greenfield backlog rows."""

from __future__ import annotations

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
        "booking",
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
            return action
    if len(fragments) > 1:
        joined = f"{fragments[0]}, {fragments[1]}" if ("," in fragments[0] or "(" in fragments[0]) else join_action_fragments(fragments[:2])
        action = backlog_text.capability_action_clause(joined)
        if action:
            return action
    selected = _preferred_title_fragment(fragments)
    if selected:
        action = backlog_text.capability_action_clause(backlog_text.sentence_fragment(selected))
        if action:
            return action
    if fallback:
        return backlog_text.capability_action_clause(backlog_text.sentence_fragment(fallback))
    return ""


def actor_interaction_action(*, first_path: str, actor: str, fallback: str) -> str:
    selected = _actor_owned_action_fragments(first_path=first_path, actor=actor, include_visible=True, max_fragments=3)
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


def append_outcome_action(*, action: str, outcome: str, outcome_action: str, recipient: str) -> str:
    if backlog_text.result_terms_covered(outcome, action) or backlog_text.result_terms_covered(outcome_action, action):
        return ""
    return f", and {recipient_phrase(recipient)} can {outcome_action}" if outcome_action else ""


def missing_input_tail(*, action: str, outcome: str, outcome_already_appended: bool = False) -> str:
    if outcome_already_appended:
        return " while the product gives clear correction guidance when required information is missing"
    if backlog_text.result_terms_covered(outcome, action):
        return " with clear correction guidance when required information is missing"
    return ", and see what to fix when required information is missing"


def workflow_result_sentence(*, action: str, outcome: str, outcome_action: str, recipient: str) -> str:
    if backlog_text.result_terms_covered(outcome, action) or backlog_text.result_terms_covered(outcome_action, action):
        return "and keeps the saved result reviewable"
    return f"and lets {recipient_phrase(recipient)} {outcome_action}"


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


__all__ = [
    "actor_appears_in_path",
    "actor_interaction_action",
    "append_outcome_action",
    "dedupe_repeated_visible_result_tail",
    "join_action_fragments",
    "join_distinct_labels",
    "missing_input_tail",
    "prefer_outcome_title",
    "recipient_phrase",
    "workflow_result_sentence",
    "workflow_title_action",
]
