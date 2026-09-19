"""Project one proposed first run without assigning chronology to source IDs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
    authored_visible_result,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    decision_copy,
)


def authored_first_run_relations(intent: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Keep source event identities while following only the validated design."""

    relations = first_path_relations_from_intent(intent)
    if not relations:
        raise ValueError("Greenfield proposed first run requires source-event custody")
    by_order = {row["order"]: row for row in relations}
    first_run = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]["first_run"]
    return tuple(dict(by_order[order]) for order in first_run["event_orders"])


def authored_first_run_text(intent: Mapping[str, Any]) -> str:
    """Retain complete event quotations and visibly distinguish proposed order."""

    return "Proposed first run:\n" + "\n".join(
        row["event_quote"] for row in authored_first_run_relations(intent)
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
