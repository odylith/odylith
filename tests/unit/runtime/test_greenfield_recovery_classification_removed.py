"""Behavior proof for source actions formerly conflated with recovery metadata."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    FIRST_PATH_RELATION_FIELDS,
    authored_component_relation_facts,
)
from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import (
    derive_model_relations,
)


def _fact(
    *,
    fact_index: int,
    field: str,
    quote: str,
    source_start: int,
    projection_path: str,
    projection_start: int,
) -> dict[str, object]:
    length = len(quote.encode("utf-8"))
    return {
        "fact_index": fact_index,
        "field": field,
        "quote": quote,
        "source_start_byte": source_start,
        "source_end_byte": source_start + length,
        "projection_path": projection_path,
        "projection_start_byte": projection_start,
        "projection_end_byte": projection_start + length,
    }


def test_failure_tracking_and_restoration_remain_exact_actions_without_recovery_label() -> None:
    title = "Recovery Console"
    failure_event = "Recovery Console records failed runs"
    restoration_event = "restores service"
    evidence = f"{failure_event} and {restoration_event}"
    first_path = f"{failure_event}\n{restoration_event}"
    restoration_source_start = evidence.index(restoration_event)
    restoration_projection_start = len(failure_event.encode("utf-8")) + 1
    selected_facts = (
        _fact(
            fact_index=1,
            field="title",
            quote=title,
            source_start=0,
            projection_path="/title",
            projection_start=0,
        ),
        _fact(
            fact_index=2,
            field="first_path",
            quote=failure_event,
            source_start=0,
            projection_path="/first_path",
            projection_start=0,
        ),
        _fact(
            fact_index=3,
            field="first_path",
            quote=restoration_event,
            source_start=restoration_source_start,
            projection_path="/first_path",
            projection_start=restoration_projection_start,
        ),
    )

    derived = derive_model_relations(
        events=(
            {
                "actor_fact_quote": title,
                "actor_quote": title,
                "action_quote": "records",
                "target_quote": "failed runs",
            },
            {
                "actor_fact_quote": title,
                "actor_quote": title,
                "action_quote": "restores",
                "target_quote": "service",
            },
        ),
        terminal={"result_quote": "service", "result_occurrence": 1},
        components=({"owner_fact_quote": title, "responsibilities": []},),
        selected_facts=selected_facts,
        first_path=first_path,
        evidence_text=evidence,
    )

    assert [
        (row["event_quote"], row["action_verb_quote"], row["target_quote"])
        for row in derived.first_path_relations
    ] == [
        (failure_event, "records", "failed runs"),
        (restoration_event, "restores", "service"),
    ]
    assert all(set(row) == FIRST_PATH_RELATION_FIELDS for row in derived.first_path_relations)

    components = authored_component_relation_facts(
        title=title,
        internal_systems=(),
        relations=derived.first_path_relations,
        component_responsibility_relations=derived.component_responsibility_relations,
    )

    assert components[0]["owner_bound_events"] == [failure_event, restoration_event]
    assert components[0]["event_targets"] == ["failed runs", "service"]
    assert "recovery_events" not in components[0]
