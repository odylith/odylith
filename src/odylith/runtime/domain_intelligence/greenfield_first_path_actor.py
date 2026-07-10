"""Resolve actor ownership and title anchors for parsed first-path events."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_trivial_start
from odylith.runtime.domain_intelligence.greenfield_first_path_subject_kind import has_explicit_generic_product_subject
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_ACTOR_TERM_STOPWORDS = {
    "accepted",
    "action",
    "after",
    "before",
    "boundary",
    "complete",
    "create",
    "created",
    "enter",
    "entered",
    "enters",
    "first",
    "greenfield",
    "least",
    "path",
    "person",
    "product",
    "proven",
    "proof",
    "record",
    "recorded",
    "release",
    "state",
    "succeed",
    "succeeds",
    "system",
    "that",
    "their",
    "then",
    "this",
    "user",
    "view",
    "viewed",
    "views",
    "when",
    "with",
}
_NOUN_LIKE_ACTION_TOKENS = frozenset({"record", "report", "surface", "view"})
_ACTION_VERB_PATTERN = action_verb_pattern()
_HUMAN_PRONOUN_SUBJECT_RE = re.compile(
    r"^(?:(?:and|then|later|then\s+later)\s+)?(?:he|she|they)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FirstPathActorAction:
    actor: str
    action: str
    text: str
    human_owned: bool = True


def resolve_first_path_events(
    steps: Sequence[str],
    *,
    lead_actor: str,
    human_actors: Sequence[str],
) -> tuple[FirstPathActorAction, ...]:
    """Return parsed events with actor ownership carried across actorless steps."""

    fallback_actor = first_path_actor_label([lead_actor], fallback=lead_actor)
    current_actor = fallback_actor
    events: list[FirstPathActorAction] = []
    for step in steps:
        text = clean_markdown_text(step).strip(" .")
        if not text:
            continue
        human_pronoun_subject = _has_human_pronoun_subject(text)
        human_owned = not has_explicit_generic_product_subject(text)
        if human_pronoun_subject or not human_owned:
            event_actor = current_actor or fallback_actor
        else:
            event_actor = resolve_first_path_event_actor(
                text,
                human_actors=human_actors,
                fallback=current_actor or fallback_actor,
            )
        if human_owned:
            current_actor = event_actor or current_actor
        action_source = _strip_human_pronoun_subject(text) if human_pronoun_subject else text
        events.append(
            FirstPathActorAction(
                actor=event_actor or fallback_actor,
                action=action_chain_fragment(action_source),
                text=text,
                human_owned=human_owned,
            )
        )
    return tuple(events)


def select_first_path_actor_action(
    events: Sequence[FirstPathActorAction],
    *,
    lead_actor: str,
) -> FirstPathActorAction | None:
    """Keep actor and action from one event, preferring the lead actor's work."""

    actionable = [event for event in events if event.human_owned and event.actor and event.action]
    for event in actionable:
        if same_first_path_actor(event.actor, lead_actor) and not is_first_path_setup_event(event):
            return event
    return next(
        (event for event in actionable if not is_first_path_setup_event(event)),
        actionable[0] if actionable else None,
    )


def resolve_first_path_event_actor(
    value: str,
    *,
    human_actors: Sequence[str],
    fallback: str,
) -> str:
    if _has_human_pronoun_subject(value) or has_explicit_generic_product_subject(value):
        return fallback
    signature = actor_signature(value)
    explicit_subject = _explicit_event_subject(value)
    if not signature and explicit_subject:
        signature = " ".join(ordered_terms(explicit_subject, stopwords=_ACTOR_TERM_STOPWORDS))
    if not signature:
        return fallback
    signature_terms = set(ordered_terms(signature, stopwords=_ACTOR_TERM_STOPWORDS))
    if not signature_terms:
        return fallback
    candidates: list[tuple[int, int, str]] = []
    for row in human_actors:
        label = first_path_actor_label([row], fallback="")
        label_terms = set(ordered_terms(label, stopwords=_ACTOR_TERM_STOPWORDS))
        overlap = len(signature_terms & label_terms)
        if overlap:
            candidates.append((overlap, -len(label_terms), label))
    if not candidates:
        return fallback
    candidates.sort(reverse=True)
    return candidates[0][2]


def same_first_path_actor(left: str, right: str) -> bool:
    left_tokens = _actor_tokens(first_path_actor_label([left], fallback=left))
    right_tokens = _actor_tokens(first_path_actor_label([right], fallback=right))
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True
    shorter, longer = sorted((left_tokens, right_tokens), key=len)
    width = len(shorter)
    return any(longer[index : index + width] == shorter for index in range(len(longer) - width + 1))


def is_first_path_setup_event(event: FirstPathActorAction) -> bool:
    return is_first_path_setup_action(event.action, source=event.text)


def is_first_path_setup_action(value: str, *, source: str = "") -> bool:
    text = value.strip(" .")
    if is_trivial_start(source or value):
        return True
    if re.match(r"^set\s+up\b", text, flags=re.IGNORECASE):
        return True
    if re.match(r"^(?:open|launch|start|visit|view)\b", text, flags=re.IGNORECASE):
        return not re.search(
            rf"(?:,\s*|\s+and\s+).*\b(?:{_ACTION_VERB_PATTERN})\b",
            text,
            flags=re.IGNORECASE,
        )
    return bool(
        re.match(
            r"^(?:add|create|set\s+up)\s+(?:one\s+|a\s+|an\s+|the\s+)?"
            r"(?:account|asset|child|learner\s+profile|profile|record|workspace)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def first_path_actor_label(values: Sequence[str], *, fallback: str) -> str:
    for value in values:
        text = clean_markdown_text(value).split("\N{EM DASH}", 1)[0].split(":", 1)[0].strip(" .")
        if text:
            return _sentence_safe_actor_label(text)
    return _sentence_safe_actor_label(fallback)


def _has_human_pronoun_subject(value: str) -> bool:
    return bool(_HUMAN_PRONOUN_SUBJECT_RE.match(clean_markdown_text(value).strip(" .,;:")))


def _strip_human_pronoun_subject(value: str) -> str:
    text = clean_markdown_text(value).strip(" .,;:")
    return _HUMAN_PRONOUN_SUBJECT_RE.sub("", text, count=1).strip(" .,;:")


def _explicit_event_subject(value: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", clean_markdown_text(value), flags=re.IGNORECASE).strip(
        " .,;:"
    )
    if not text:
        return ""
    for match in re.finditer(rf"\b({_ACTION_VERB_PATTERN})\b", text, re.IGNORECASE):
        token = match.group(1).casefold()
        if token in _NOUN_LIKE_ACTION_TOKENS and re.match(
            rf"\s+(?:{_ACTION_VERB_PATTERN})\b",
            text[match.end() :],
            re.IGNORECASE,
        ):
            continue
        if match.start() <= 0:
            return ""
        subject = text[: match.start()].strip(" .,;:")
        subject = re.sub(r"^(?:a|an|the|one|this|that|each|another)\s+", "", subject, flags=re.IGNORECASE)
        terms = ordered_terms(subject, stopwords=_ACTOR_TERM_STOPWORDS)
        if not terms or len(terms) > 6:
            return ""
        if re.search(r"\b(?:at|by|for|from|in|of|on|through|to|via|with|without)\b", subject, re.IGNORECASE):
            return ""
        if re.search(
            r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
            subject,
            re.IGNORECASE,
        ):
            return ""
        return subject
    return ""


def _sentence_safe_actor_label(value: str) -> str:
    text = clean_markdown_text(value).strip(" .")
    if not text or not re.search(r"\b(?:and|or)\b", text, flags=re.IGNORECASE):
        return text
    words = [word.strip(".,;:()[]{}") for word in text.split() if word.strip(".,;:()[]{}")]
    if any(any(char.isdigit() for char in word) or (word.isupper() and len(word) > 1) for word in words):
        return text
    if not all(word[:1].isupper() or word.casefold() in {"and", "or"} for word in words):
        return text
    lowered = text.casefold()
    return f"{lowered[:1].upper()}{lowered[1:]}"


def _actor_tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z][a-z0-9'-]*", value.casefold()))


__all__ = [
    "FirstPathActorAction",
    "first_path_actor_label",
    "is_first_path_setup_action",
    "is_first_path_setup_event",
    "resolve_first_path_event_actor",
    "resolve_first_path_events",
    "same_first_path_actor",
    "select_first_path_actor_action",
]
