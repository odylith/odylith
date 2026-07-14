"""Recognize direct actor-action clauses in confirmed prompt text."""

from __future__ import annotations

from dataclasses import dataclass
import re


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
