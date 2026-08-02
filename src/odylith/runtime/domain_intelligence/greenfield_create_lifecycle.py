"""Deterministic public lifecycle for a Greenfield create transaction."""

from __future__ import annotations

from collections.abc import Sequence


CREATE_LIFECYCLE_VERSION = "odylith.greenfield.create-lifecycle.v1"

DRAFT = "DRAFT"
SEALED = "SEALED"
PREPARED = "PREPARED"
PUBLISHING = "PUBLISHING"
PUBLISHED = "PUBLISHED"
VERIFIED = "VERIFIED"
CLOSED = "CLOSED"
ABORTED = "ABORTED"
RECOVERY_REQUIRED = "RECOVERY_REQUIRED"

CREATE_LIFECYCLE_STATES = frozenset(
    {
        DRAFT,
        SEALED,
        PREPARED,
        PUBLISHING,
        PUBLISHED,
        VERIFIED,
        CLOSED,
        ABORTED,
        RECOVERY_REQUIRED,
    }
)
_ALLOWED_TRANSITIONS = {
    DRAFT: frozenset({SEALED, ABORTED}),
    SEALED: frozenset({PREPARED, ABORTED}),
    PREPARED: frozenset({PUBLISHING, ABORTED}),
    PUBLISHING: frozenset({PUBLISHED, RECOVERY_REQUIRED}),
    PUBLISHED: frozenset({VERIFIED, RECOVERY_REQUIRED}),
    VERIFIED: frozenset({CLOSED}),
    CLOSED: frozenset(),
    ABORTED: frozenset(),
    RECOVERY_REQUIRED: frozenset(),
}


def lifecycle_history_for_journal_state(state: str) -> tuple[str, ...]:
    """Return the minimum truthful public history for one internal journal state."""

    histories = {
        "preparing": (DRAFT, SEALED),
        "prepared": (DRAFT, SEALED, PREPARED),
        "projecting": (DRAFT, SEALED, PREPARED),
        "published": (DRAFT, SEALED, PREPARED, PUBLISHING, PUBLISHED),
        "verified": (DRAFT, SEALED, PREPARED, PUBLISHING, PUBLISHED, VERIFIED),
        "closed": (DRAFT, SEALED, PREPARED, PUBLISHING, PUBLISHED, VERIFIED, CLOSED),
        "aborted": (DRAFT, SEALED, PREPARED, ABORTED),
        "recovery_required": (DRAFT, SEALED, PREPARED, PUBLISHING, RECOVERY_REQUIRED),
    }
    try:
        return histories[state]
    except KeyError as error:
        raise ValueError(f"unsupported Greenfield journal lifecycle state: {state}") from error


def advance_lifecycle_for_journal_state(history: Sequence[str], state: str) -> tuple[str, ...]:
    """Advance an existing history to the public state implied by a journal transition."""

    current = require_create_lifecycle_history(history)
    target = lifecycle_history_for_journal_state(state)
    if state == "aborted" and current[-1] in {DRAFT, SEALED, PREPARED}:
        additions = (ABORTED,)
    elif state == "recovery_required" and current[-1] in {PUBLISHING, PUBLISHED}:
        additions = (RECOVERY_REQUIRED,)
    else:
        common = 0
        for left, right in zip(current, target, strict=False):
            if left != right:
                break
            common += 1
        if common != len(current):
            raise ValueError("Greenfield create lifecycle cannot rewrite durable history")
        additions = target[common:]
    result = (*current, *additions)
    return require_create_lifecycle_history(result)


def require_create_lifecycle_history(value: Sequence[str]) -> tuple[str, ...]:
    """Validate one non-empty, non-repeating lifecycle path."""

    if isinstance(value, (str, bytes, bytearray)) or not value:
        raise ValueError("Greenfield create lifecycle history is missing")
    history = tuple(str(state or "").strip() for state in value)
    if history[0] != DRAFT or any(state not in CREATE_LIFECYCLE_STATES for state in history):
        raise ValueError("Greenfield create lifecycle history is invalid")
    if len(set(history)) != len(history):
        raise ValueError("Greenfield create lifecycle history repeats a state")
    for before, after in zip(history, history[1:], strict=False):
        if after not in _ALLOWED_TRANSITIONS[before]:
            raise ValueError(f"Greenfield create lifecycle transition {before} -> {after} is invalid")
    return history


__all__ = [
    "ABORTED",
    "CLOSED",
    "CREATE_LIFECYCLE_STATES",
    "CREATE_LIFECYCLE_VERSION",
    "DRAFT",
    "PREPARED",
    "PUBLISHED",
    "PUBLISHING",
    "RECOVERY_REQUIRED",
    "SEALED",
    "VERIFIED",
    "advance_lifecycle_for_journal_state",
    "lifecycle_history_for_journal_state",
    "require_create_lifecycle_history",
]
