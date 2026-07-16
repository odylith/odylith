"""Recognize direct actor-action clauses in confirmed prompt text."""

from __future__ import annotations

from dataclasses import dataclass
import re

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term


_CONTEXTUAL_CLAUSE_PREFIXES = frozenset(
    {"after", "at", "before", "by", "during", "for", "from", "in", "on", "through", "to", "while", "with", "within"}
)


@dataclass(frozen=True)
class DirectActorActionMatch:
    """Syntactic parts of a direct declarative actor-action sentence."""

    actor: str
    action: str
    gerund: bool


def direct_actor_action_match(value: str) -> DirectActorActionMatch | None:
    """Return direct actor-action parts, excluding a temporal proof tail."""

    match = re.match(
        r"^(?P<actor>(?:a|an|the)?\s*[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+"
        r"(?:(?P<need>(?:needs?|must)\s+to)\s+|(?P<gerund>is|are)\s+)(?P<action>[A-Za-z][A-Za-z0-9 /&'(),-]{4,})$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    action = re.split(r"\s+(?:after|before|between)\s+", match.group("action"), maxsplit=1, flags=re.IGNORECASE)[0]
    return DirectActorActionMatch(
        actor=match.group("actor"),
        action=action,
        gerund=bool(match.group("gerund")),
    )


def leading_actor_action_match(value: str) -> tuple[str, str] | None:
    """Recover a direct actor-led action from a coordinated workflow sentence."""

    clauses = [clause.strip(" .") for clause in re.split(r"\s*,\s*", value) if clause.strip(" .")]
    for index, clause in enumerate(clauses):
        words = [word.strip(".,:;!?()[]{}") for word in clause.split() if word.strip(".,:;!?()[]{}")]
        if not words or words[0].casefold() in _CONTEXTUAL_CLAUSE_PREFIXES:
            continue
        for boundary in range(1, min(6, len(words) - 1) + 1):
            actor_words = words[:boundary]
            if not looks_like_actor_role_term(actor_words[-1]):
                continue
            action = ", ".join((" ".join(words[boundary:]), *clauses[index + 1 :])).strip(" .")
            if looks_like_action_clause(action):
                actor = re.sub(r"^(?:a|an|the)\s+", "", " ".join(actor_words), flags=re.IGNORECASE)
                return actor, action
    return None
