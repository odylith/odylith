"""Project one proposed first run without assigning chronology to source IDs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
    authored_visible_result,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    decision_copy,
)


@dataclass(frozen=True)
class AuthoredEventPresentation:
    """Typed presentation facts for one source-custodied event."""

    order: int
    actor_kind: str
    actor_label: str
    event_quote: str

    @property
    def plain_text(self) -> str:
        """Keep the actor label distinct from the unmodified source quote."""

        return f"Actor: {self.actor_label}\nSource event: {self.event_quote}"


def authored_first_run_relations(intent: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Keep source event identities while following only the validated design."""

    relations = first_path_relations_from_intent(intent)
    if not relations:
        raise ValueError("Greenfield proposed first run requires source-event custody")
    by_order = {row["order"]: row for row in relations}
    first_run = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]["first_run"]
    return tuple(dict(by_order[order]) for order in first_run["event_orders"])


def authored_event_presentation(relation: Mapping[str, Any]) -> AuthoredEventPresentation:
    """Build one presentation only from an already-typed actor/action relation."""

    order = relation.get("order")
    actor_kind = relation.get("actor_kind")
    actor = relation.get("actor_fact_quote")
    event = relation.get("event_quote")
    if (
        type(order) is not int
        or order < 1
        or not isinstance(actor_kind, str)
        or not actor_kind.strip()
        or not isinstance(actor, str)
        or not actor.strip()
        or not isinstance(event, str)
        or not event.strip()
    ):
        raise ValueError("Greenfield event presentation requires typed actor/action custody")
    return AuthoredEventPresentation(
        order=order,
        actor_kind=actor_kind,
        actor_label=actor,
        event_quote=event,
    )


def authored_event_display_text(relation: Mapping[str, Any]) -> str:
    """Present one typed actor/action relation without rewriting its source quote."""

    return authored_event_presentation(relation).plain_text


def authored_first_run_text(intent: Mapping[str, Any]) -> str:
    """Retain complete event quotations and visibly distinguish proposed order."""

    return "Proposed first run:\n" + "\n".join(
        f"Event {row['order']}\n{authored_event_display_text(row)}"
        for row in authored_first_run_relations(intent)
    )


def authored_checkpoint_text(intent: Mapping[str, Any]) -> str:
    """Display a source result or its explicitly provisional proof checkpoint.

    This copy must never be written back into source facts or event relations.
    Relation validation owns whether the targeted assumption is admissible.
    """

    relations = first_path_relations_from_intent(intent)
    result = authored_visible_result(relations)
    if result:
        return result
    checkpoint = decision_copy(intent, "proof_boundary")
    if not relations or intent.get("proof_boundary") or not checkpoint:
        raise ValueError("Greenfield checkpoint requires source custody or a proof assumption")
    return checkpoint
