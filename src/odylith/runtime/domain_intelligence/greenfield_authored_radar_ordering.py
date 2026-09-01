"""Carry model-authored Radar ordering as typed facts and render it once."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


AUTHORED_ORDERING_DECISION_VERSION = "odylith.greenfield.radar-ordering.v1"
_ORDERING_FIELDS = frozenset(
    {
        "version",
        "why_now",
        "expected_outcome",
        "tradeoff",
        "deferred_scope",
        "priority",
        "ranking_basis",
    }
)


def build_authored_ordering_decision(
    *,
    why_now: str,
    expected_outcome: str,
    deferred_scope: Sequence[str],
    ranking_basis: str,
    priority: str = "P1",
    tradeoff: str = "",
) -> dict[str, Any]:
    """Build one closed ordering decision without converting it to prose."""

    decision = {
        "version": AUTHORED_ORDERING_DECISION_VERSION,
        "why_now": str(why_now),
        "expected_outcome": str(expected_outcome),
        "tradeoff": str(tradeoff),
        "deferred_scope": [str(value) for value in deferred_scope],
        "priority": str(priority),
        "ranking_basis": str(ranking_basis),
    }
    return authored_ordering_decision(decision)


def authored_ordering_decision(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Return a validated closed ordering decision."""

    if not isinstance(value, Mapping) or set(value) != _ORDERING_FIELDS:
        raise ValueError("model-authored backlog row has an invalid typed ordering decision")
    if value.get("version") != AUTHORED_ORDERING_DECISION_VERSION:
        raise ValueError("model-authored backlog row has an unsupported ordering decision version")
    required = ("why_now", "expected_outcome", "priority", "ranking_basis")
    if any(not isinstance(value.get(field), str) or not value.get(field) for field in required):
        raise ValueError("model-authored backlog row has an incomplete typed ordering decision")
    tradeoff = value.get("tradeoff")
    deferred_scope = value.get("deferred_scope")
    if not isinstance(tradeoff, str):
        raise ValueError("model-authored backlog row has an invalid typed tradeoff")
    if (
        not isinstance(deferred_scope, Sequence)
        or isinstance(deferred_scope, (str, bytes, bytearray))
        or any(not isinstance(item, str) or not item for item in deferred_scope)
    ):
        raise ValueError("model-authored backlog row has invalid typed deferred scope")
    return {
        "version": AUTHORED_ORDERING_DECISION_VERSION,
        "why_now": value["why_now"],
        "expected_outcome": value["expected_outcome"],
        "tradeoff": tradeoff,
        "deferred_scope": list(deferred_scope),
        "priority": value["priority"],
        "ranking_basis": value["ranking_basis"],
    }


def render_authored_ordering_rationale(value: Mapping[str, Any] | Any) -> list[str]:
    """Render the typed decision as Radar view copy without reading it back."""

    decision = authored_ordering_decision(value)
    lines = [
        f"- why now: {decision['why_now']}",
        f"- expected outcome: {decision['expected_outcome']}",
    ]
    if decision["tradeoff"]:
        lines.append(f"- tradeoff: {decision['tradeoff']}")
    if decision["deferred_scope"]:
        lines.append(f"- deferred for now: {'; '.join(decision['deferred_scope'])}")
    lines.append(
        f"- ranking basis: {decision['priority']} first-release ordering for the accepted first path: "
        f"{decision['ranking_basis']}"
    )
    return lines


__all__ = [
    "AUTHORED_ORDERING_DECISION_VERSION",
    "authored_ordering_decision",
    "build_authored_ordering_decision",
    "render_authored_ordering_rationale",
]
