from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
)
from odylith.runtime.domain_intelligence.greenfield_model_direct_evidence_graph import (
    GreenfieldComponentOwnershipError,
    derive_model_relations,
)


def _fact(
    evidence: str,
    *,
    fact_index: int,
    field: str,
    quote: str,
    projection_path: str,
) -> dict[str, Any]:
    evidence_bytes = evidence.encode("utf-8")
    quote_bytes = quote.encode("utf-8")
    source_start = evidence_bytes.find(quote_bytes)
    assert source_start >= 0
    return {
        "fact_index": fact_index,
        "field": field,
        "quote": quote,
        "source_start_byte": source_start,
        "source_end_byte": source_start + len(quote_bytes),
        "projection_path": projection_path,
        "projection_start_byte": 0,
        "projection_end_byte": len(quote_bytes),
    }


def _derive(
    *,
    evidence: str,
    event_quote: str,
    actor_fact_quote: str,
    actor_quote: str,
    action_quote: str,
    target_quote: str,
    owner_fact_quote: str,
    responsibility_quote: str,
    terminal_quote: str,
    selected_facts: Sequence[Mapping[str, Any]],
):
    responsibilities = (
        ({"quote": responsibility_quote, "occurrence": 1},)
        if responsibility_quote
        else ()
    )
    return derive_model_relations(
        events=(
            {
                "actor_fact_quote": actor_fact_quote,
                "actor_quote": actor_quote,
                "action_quote": action_quote,
                "target_quote": target_quote,
            },
        ),
        terminal={"result_quote": terminal_quote, "result_occurrence": 1},
        components=(
            {
                "owner_fact_quote": owner_fact_quote,
                "responsibilities": responsibilities,
            },
        ),
        selected_facts=selected_facts,
        first_path=event_quote,
        evidence_text=evidence,
    )


def test_product_event_responsibility_keeps_its_selected_product_owner() -> None:
    evidence = "Relay Console stores the approved packet and shows a receipt."
    event = "Relay Console stores the approved packet and shows a receipt"
    responsibility = "stores the approved packet"
    facts = (
        _fact(
            evidence,
            fact_index=1,
            field="title",
            quote="Relay Console",
            projection_path="/title",
        ),
        _fact(
            evidence,
            fact_index=2,
            field="first_path",
            quote=event,
            projection_path="/first_path",
        ),
        _fact(
            evidence,
            fact_index=3,
            field="component_responsibilities",
            quote=responsibility,
            projection_path="/component_responsibilities/0",
        ),
    )

    result = _derive(
        evidence=evidence,
        event_quote=event,
        actor_fact_quote="Relay Console",
        actor_quote="Relay Console",
        action_quote="stores",
        target_quote="approved packet",
        owner_fact_quote="Relay Console",
        responsibility_quote=responsibility,
        terminal_quote="receipt",
        selected_facts=facts,
    )

    assert result.component_responsibility_relations[0]["owner_system_path"] == "/title"
    assert result.component_responsibility_relations[0]["first_path_event_order"] == 1


def test_outer_product_capability_may_encompass_a_human_event() -> None:
    capability = (
        "Floodline helps city staff route residents to shelters with visible capacity guidance"
    )
    event = "city staff route residents to shelters"
    evidence = f"{capability}."
    facts = (
        _fact(evidence, fact_index=1, field="title", quote="Floodline", projection_path="/title"),
        _fact(
            evidence,
            fact_index=2,
            field="human_actors",
            quote="city staff",
            projection_path="/human_actors/0",
        ),
        _fact(
            evidence,
            fact_index=3,
            field="first_path",
            quote=event,
            projection_path="/first_path",
        ),
        _fact(
            evidence,
            fact_index=4,
            field="product_story",
            quote=capability,
            projection_path="/product_story",
        ),
        _fact(
            evidence,
            fact_index=5,
            field="component_responsibilities",
            quote=capability,
            projection_path="/component_responsibilities/0",
        ),
    )

    result = _derive(
        evidence=evidence,
        event_quote=event,
        actor_fact_quote="city staff",
        actor_quote="city staff",
        action_quote="route",
        target_quote="residents",
        owner_fact_quote="Floodline",
        responsibility_quote=capability,
        terminal_quote="visible capacity guidance",
        selected_facts=facts,
    )

    relation = result.component_responsibility_relations[0]
    assert relation["owner_system_quote"] == "Floodline"
    assert relation["first_path_event_order"] == 1


@pytest.mark.parametrize(
    ("evidence", "title", "event", "actor_field", "actor", "action", "target"),
    (
        (
            "Floodline. City staff route residents to shelters.",
            "Floodline",
            "City staff route residents to shelters",
            "human_actors",
            "City staff",
            "route",
            "residents",
        ),
        (
            "Harbor Desk. Tide API sends berth clearance.",
            "Harbor Desk",
            "Tide API sends berth clearance",
            "external_systems",
            "Tide API",
            "sends",
            "berth clearance",
        ),
    ),
)
def test_non_product_event_is_not_a_product_component_responsibility(
    evidence: str,
    title: str,
    event: str,
    actor_field: str,
    actor: str,
    action: str,
    target: str,
) -> None:
    facts = (
        _fact(evidence, fact_index=1, field="title", quote=title, projection_path="/title"),
        _fact(
            evidence,
            fact_index=2,
            field=actor_field,
            quote=actor,
            projection_path=f"/{actor_field}/0",
        ),
        _fact(
            evidence,
            fact_index=3,
            field="first_path",
            quote=event,
            projection_path="/first_path",
        ),
        _fact(
            evidence,
            fact_index=4,
            field="component_responsibilities",
            quote=event,
            projection_path="/component_responsibilities/0",
        ),
    )

    with pytest.raises(
        GreenfieldComponentOwnershipError,
        match="non-product event",
    ):
        _derive(
            evidence=evidence,
            event_quote=event,
            actor_fact_quote=actor,
            actor_quote=actor,
            action_quote=action,
            target_quote=target,
            owner_fact_quote=title,
            responsibility_quote=event,
            terminal_quote=target,
            selected_facts=facts,
        )


def test_product_event_rejects_a_different_selected_component_owner() -> None:
    evidence = "Harbor Desk. Berth Map stores approved berth state."
    event = "Berth Map stores approved berth state"
    responsibility = "stores approved berth state"
    facts = (
        _fact(evidence, fact_index=1, field="title", quote="Harbor Desk", projection_path="/title"),
        _fact(
            evidence,
            fact_index=2,
            field="internal_systems",
            quote="Berth Map",
            projection_path="/internal_systems/0",
        ),
        _fact(
            evidence,
            fact_index=3,
            field="first_path",
            quote=event,
            projection_path="/first_path",
        ),
        _fact(
            evidence,
            fact_index=4,
            field="component_responsibilities",
            quote=responsibility,
            projection_path="/component_responsibilities/0",
        ),
    )

    with pytest.raises(
        GreenfieldComponentOwnershipError,
        match="contradictory component owners",
    ):
        _derive(
            evidence=evidence,
            event_quote=event,
            actor_fact_quote="Berth Map",
            actor_quote="Berth Map",
            action_quote="stores",
            target_quote="approved berth state",
            owner_fact_quote="Harbor Desk",
            responsibility_quote=responsibility,
            terminal_quote="approved berth state",
            selected_facts=facts,
        )


def test_initial_carried_actor_remains_an_untyped_authored_semantics_failure() -> None:
    evidence = "Analyst Ana uses Relay Console. Later, submits a case."
    event = "submits a case"
    facts = (
        _fact(
            evidence,
            fact_index=1,
            field="title",
            quote="Relay Console",
            projection_path="/title",
        ),
        _fact(
            evidence,
            fact_index=2,
            field="human_actors",
            quote="Analyst Ana",
            projection_path="/human_actors/0",
        ),
        _fact(
            evidence,
            fact_index=3,
            field="first_path",
            quote=event,
            projection_path="/first_path",
        ),
    )

    with pytest.raises(
        GreenfieldAuthoredSemanticsError,
        match="ungrounded first-path actor",
    ) as exc_info:
        _derive(
            evidence=evidence,
            event_quote=event,
            actor_fact_quote="Analyst Ana",
            actor_quote="Analyst Ana",
            action_quote="submits",
            target_quote="case",
            owner_fact_quote="Relay Console",
            responsibility_quote="",
            terminal_quote="case",
            selected_facts=facts,
        )

    assert type(exc_info.value) is GreenfieldAuthoredSemanticsError
