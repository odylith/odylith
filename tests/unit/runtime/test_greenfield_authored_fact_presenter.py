from __future__ import annotations

import html

from odylith.runtime.project_intelligence import authored_fact_presenter
from odylith.runtime.project_intelligence import greenfield_authored_dashboard


EVENTS = (
    "Quartz Keeper signals amber ferry",
    "Rill Engine writes blue receipt",
    "Quartz Keeper reviews blue receipt",
)


def _project() -> dict[str, object]:
    return {
        "focus": "\n".join(EVENTS),
        "actors": [
            ("Human actor", "Quartz Keeper", "\n".join((EVENTS[0], EVENTS[2]))),
            ("Human actor", "Silent Reviewer", "Named in the model-authored product intent."),
        ],
        "authored_facts": {
            "first_path_relations": [
                {
                    "order": 1,
                    "event_quote": EVENTS[0],
                    "actor_kind": "human",
                    "actor_quote": "Quartz Keeper",
                    "actor_fact_quote": "Quartz Keeper",
                },
                {
                    "order": 2,
                    "event_quote": EVENTS[1],
                    "actor_kind": "product",
                    "actor_quote": "Rill Engine",
                    "actor_fact_quote": "Rill Engine",
                },
                {
                    "order": 3,
                    "event_quote": EVENTS[2],
                    "actor_kind": "human",
                    "actor_quote": "Quartz Keeper",
                    "actor_fact_quote": "Quartz Keeper",
                },
            ],
            "component_responsibility_relations": [
                {
                    "owner_system_quote": "Rill Engine",
                    "responsibility_quote": "Own blue-receipt custody.",
                },
                {
                    "owner_system_quote": "Harbor Ledger",
                    "responsibility_quote": "Own amber-ferry evidence.",
                },
            ],
            "human_actors": ["Quartz Keeper", "Silent Reviewer"],
            "internal_systems": ["Rill Engine", "Harbor Ledger", "Beacon Console"],
            "external_systems": ["Delta Relay", "North Archive"],
            "non_goals": ["Do not claim live settlement.", "Do not automate reviewer judgment."],
        },
    }


def _render_text(value: object) -> str:
    return html.escape(str(value or ""))


def test_authored_fact_view_preserves_unseen_typed_facts_without_prose_parsing() -> None:
    view = authored_fact_presenter.authored_fact_view(_project())

    assert view is not None
    assert [(event.order, event.text) for event in view.events] == [
        (1, EVENTS[0]),
        (2, EVENTS[1]),
        (3, EVENTS[2]),
    ]
    assert [(row.owner, row.responsibility) for row in view.capabilities] == [
        ("Rill Engine", "Own blue-receipt custody."),
        ("Harbor Ledger", "Own amber-ferry evidence."),
    ]
    assert [(group.key, group.items) for group in view.boundary_groups] == [
        ("product_owned_systems", ("Rill Engine", "Harbor Ledger", "Beacon Console")),
        ("external_systems", ("Delta Relay", "North Archive")),
        (
            "non_goals",
            ("Do not claim live settlement.", "Do not automate reviewer judgment."),
        ),
    ]


def test_authored_fact_presenter_renders_repeated_nodes_in_exact_order() -> None:
    project = _project()
    focus = authored_fact_presenter.render_authored_focus(project, render_text=_render_text)
    actors = authored_fact_presenter.render_authored_actor_cards(
        project["actors"],
        project=project,
        render_text=_render_text,
    )
    story = authored_fact_presenter.render_product_story_contract(
        [
            {"label": "First Path", "semantic_slot": "first_path", "body": "\n".join(EVENTS)},
            {
                "label": "Product Boundary",
                "semantic_slot": "product_boundary",
                "body": "structured fallback",
            },
            {
                "label": "Owned Capabilities",
                "semantic_slot": "owned_capabilities",
                "body": "structured fallback",
            },
        ],
        project=project,
        render_text=_render_text,
    )

    assert focus.count("data-authored-fact-item") == 3
    assert focus.index(EVENTS[0]) < focus.index(EVENTS[1]) < focus.index(EVENTS[2])
    assert actors is not None
    assert actors.count('data-authored-fact-list="actor"') == 1
    assert actors.count("data-authored-fact-item") == 2
    assert actors.index(EVENTS[0]) < actors.index(EVENTS[2])
    assert "Named in the model-authored product intent." in actors
    assert story.count('data-authored-fact-list="first_path"') == 1
    assert story.count('data-authored-fact-list="owned_capabilities"') == 1
    assert story.count("data-authored-boundary-group") == 3
    assert story.index("Rill Engine") < story.index("Harbor Ledger")
    assert "Beacon Console" in story
    assert story.index("Delta Relay") < story.index("North Archive")
    assert ".;" not in story
    assert ".." not in story


def test_greenfield_story_fallback_bodies_preserve_structured_boundaries() -> None:
    story = greenfield_authored_dashboard._product_story(
        title="Quartz Relay",
        product_story="Quartz Relay keeps one reviewable receipt path.",
        problem="Reviewers cannot trace receipt custody.",
        first_path=" ".join(EVENTS),
        proof_boundary="A reviewer sees the blue receipt.",
        visible_result="blue receipt",
        human_actors=("Quartz Keeper",),
        components=(
            {"label": "Rill Engine", "responsibility": "Own blue-receipt custody."},
            {"label": "Harbor Ledger", "responsibility": "Own amber-ferry evidence."},
        ),
        external_systems=("Delta Relay", "North Archive"),
        non_goals=("Do not claim live settlement.", "Do not automate reviewer judgment."),
        event_quotes=EVENTS,
        actors=(("Human actor", "Quartz Keeper", "\n".join((EVENTS[0], EVENTS[2]))),),
    )
    cards = {row["semantic_slot"]: row["body"] for row in story["release_contract"]}

    assert cards["first_path"] == "\n".join(EVENTS)
    assert cards["owned_capabilities"] == (
        "Rill Engine: Own blue-receipt custody.\n"
        "Harbor Ledger: Own amber-ferry evidence."
    )
    assert cards["product_boundary"] == (
        "Product-owned systems:\n"
        "Rill Engine\n"
        "Harbor Ledger\n"
        "External systems:\n"
        "Delta Relay\n"
        "North Archive\n"
        "Excluded from the first release:\n"
        "Do not claim live settlement.\n"
        "Do not automate reviewer judgment."
    )


def test_authored_fact_presenter_keeps_scalar_fallback_for_legacy_project() -> None:
    project = {"focus": "One legacy focus sentence."}

    assert authored_fact_presenter.authored_fact_view(project) is None
    assert authored_fact_presenter.render_authored_focus(
        project,
        render_text=_render_text,
    ) == "<h2>One legacy focus sentence.</h2>"
