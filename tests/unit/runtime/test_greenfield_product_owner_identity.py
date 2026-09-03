"""Canonical product-owner identity proof for model-authored Greenfield."""

from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import (
    _LIST_FIELDS,
    _TEXT_FIELDS,
)


def _evidence(intent: dict[str, object]) -> str:
    return ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )


def test_title_alias_canonicalizes_to_its_internal_system_owner(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first_path = (
        "Dock attendant Ivo enters a vessel tag and Harbor Desk shows the placement"
    )
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Harbor Desk",
        "first_path": first_path,
        "success_metrics": ["Harbor Desk shows the placement"],
        "component_responsibilities": ["Harbor Desk shows the placement"],
        "internal_systems": ["Harbor Desk"],
    }
    source = _evidence(intent)
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Harbor Desk"],
        first_path_relations=[
            {
                "actor_kind": "human",
                "actor_quote": "Dock attendant Ivo",
                "event_quote": "Dock attendant Ivo enters a vessel tag",
                "action_verb_quote": "enters",
                "target_quote": "a vessel tag",
                "visible_result_quote": "",
                "recovery_path": False,
            },
            {
                "actor_kind": "product",
                "actor_quote": "Harbor Desk",
                "owner_system_quote": "Harbor Desk",
                "event_quote": "Harbor Desk shows the placement",
                "action_verb_quote": "shows",
                "target_quote": "the placement",
                "visible_result_quote": "Harbor Desk shows the placement",
                "recovery_path": False,
            },
        ],
    )

    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(response),
    )

    semantics = candidate["authored_semantics"]
    assert semantics["first_path_relations"][1]["actor_fact_path"] == "/internal_systems/0"
    component = semantics["component_responsibility_relations"][0]
    assert component["owner_system_path"] == "/internal_systems/0"
    assert component["owner_system_quote"] == "Harbor Desk"


def test_two_indistinguishable_internal_system_paths_fail_closed() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "internal_systems": ["Berth map", "Berth map"],
    }
    source = _evidence(intent)
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Berth map"],
    )
    response["facts"]["internal_systems"][1]["occurrence"] = 2  # type: ignore[index]

    with pytest.raises(
        GreenfieldModelAuthoringError,
        match="duplicate labels for distinct product owners",
    ):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )


def test_product_and_human_label_collision_fails_closed() -> None:
    intent = {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Dock attendant Ivo",
    }
    source = _evidence(intent)
    response = authored_response(
        intent,
        evidence_text=source,
        component_responsibility_owners=["Berth map"],
    )

    with pytest.raises(GreenfieldModelAuthoringError, match="unbound first-path actor fact"):
        author_greenfield_intent(
            evidence_text=source,
            provider=StructuredAuthoringProvider(response),
            clock=lambda: 0.0,
        )
