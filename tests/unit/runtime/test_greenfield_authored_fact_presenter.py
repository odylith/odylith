from __future__ import annotations

import html
from copy import deepcopy

import pytest

from odylith.runtime.project_intelligence import authored_fact_presenter
from odylith.runtime.project_intelligence import greenfield_authored_dashboard
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import GreenfieldAuthoredSemanticsError
from tests.unit.runtime.greenfield_model_authoring_fixtures import structural_design_fixture


EVENTS = (
    "Quartz Keeper signals amber ferry",
    "Rill Engine writes blue receipt",
    "Quartz Keeper reviews blue receipt",
)
DESIGN_NAMES = ("Receipt entry", "Custody journal", "Evidence view", "Replay checks")


def _design() -> dict:
    design = structural_design_fixture((1, 2, 3))
    for row, name in zip(design["components"], DESIGN_NAMES, strict=True):
        row["name"] = name
    return design


def _project() -> dict[str, object]:
    return {
        "focus": "\n".join(EVENTS),
        "actors": [
            ("Human actor", "Quartz Keeper", "\n".join((EVENTS[0], EVENTS[2]))),
            ("Participant", "Silent Reviewer", "Named in project evidence; no first-path action is assigned."),
        ],
        "authored_facts": {
            "provisional_design": _design(),
            "source_precedence": [],
            "operational_constraints": [],
            "first_path_relations": [
                {
                    "order": 1,
                    "event_quote": EVENTS[0],
                    "actor_kind": "human",
                    "actor_fact_quote": "Quartz Keeper",
                    "visible_result_quote": "",
                },
                {
                    "order": 2,
                    "event_quote": EVENTS[1],
                    "actor_kind": "product",
                    "actor_fact_quote": "Rill Engine",
                    "visible_result_quote": "",
                },
                {
                    "order": 3,
                    "event_quote": EVENTS[2],
                    "actor_kind": "human",
                    "actor_fact_quote": "Quartz Keeper",
                    "visible_result_quote": "blue receipt",
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
        (row["name"], row["responsibility"]) for row in _design()["components"]
    ]
    assert [(group.key, group.items) for group in view.boundary_groups] == [
        ("provisional_components", DESIGN_NAMES),
        ("source_product_systems", ("Rill Engine", "Harbor Ledger", "Beacon Console")),
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
    assert "Proposed first run:" in focus
    assert 'data-authority-kind="provisional_design"' in focus
    assert focus.index(EVENTS[0]) < focus.index(EVENTS[1]) < focus.index(EVENTS[2])
    assert actors is not None
    assert actors.count('data-authored-fact-list="actor"') == 1
    assert actors.count("data-authored-fact-item") == 2
    assert actors.index(EVENTS[0]) < actors.index(EVENTS[2])
    assert "Named in project evidence; no first-path action is assigned." in actors
    assert story.count('data-authored-fact-list="first_path"') == 1
    assert '<p data-proposed-first-run-label>Proposed first run:</p>' in story
    assert story.count('data-authored-fact-list="owned_capabilities"') == 1
    assert story.count("data-authored-boundary-group") == 4
    assert 'data-authority-kind="provisional_design"' in story
    assert '<p data-provisional-design-label>Proposed capabilities:</p>' in story
    assert "Proposed logical components (not deployment commitments)" in story
    assert "Source-stated systems:" in story
    assert "Own blue-receipt custody." not in story
    assert "Own amber-ferry evidence." not in story
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
        first_path="Proposed first run:\n" + "\n".join(EVENTS),
        proof_boundary="A reviewer sees the blue receipt.",
        visible_result="blue receipt",
        human_actors=("Quartz Keeper",),
        internal_systems=("Rill Engine", "Harbor Ledger", "Beacon Console"),
        components=(
            {"label": "Rill Engine", "responsibility": "Own blue-receipt custody.", "authority_kind": "provisional_design"},
            {"label": "Harbor Ledger", "responsibility": "Own amber-ferry evidence.", "authority_kind": "provisional_design"},
        ),
        external_systems=("Delta Relay", "North Archive"),
        non_goals=("Do not claim live settlement.", "Do not automate reviewer judgment."),
        event_quotes=EVENTS,
        actors=(("Human actor", "Quartz Keeper", "\n".join((EVENTS[0], EVENTS[2]))),),
    )
    cards = {row["semantic_slot"]: row["body"] for row in story["release_contract"]}

    assert cards["first_path"] == "Proposed first run:\n" + "\n".join(EVENTS)
    assert cards["owned_capabilities"] == (
        "Proposed capabilities:\n"
        "Rill Engine: Own blue-receipt custody.\n"
        "Harbor Ledger: Own amber-ferry evidence."
    )
    assert cards["product_boundary"] == (
        "Proposed logical components (not deployment commitments):\n"
        "Rill Engine\n"
        "Harbor Ledger\n"
        "Source-stated systems:\nRill Engine\nHarbor Ledger\nBeacon Console\n"
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


def test_result_first_inventory_displays_only_proposed_order_with_stable_source_ids() -> None:
    project = _project()
    facts = project["authored_facts"]
    rows = facts["first_path_relations"]
    facts["first_path_relations"] = [rows[2], rows[0], rows[1]]
    for order, row in enumerate(facts["first_path_relations"], start=1):
        row["order"] = order
    facts["provisional_design"]["first_run"] = {
        "event_orders": [2, 3, 1],
        "rationale": "Prepare the ferry signal and receipt before the receipt review.",
    }
    source_inventory = deepcopy(facts["first_path_relations"])

    view = authored_fact_presenter.authored_fact_view(project)
    assert view is not None
    assert [(event.order, event.text) for event in view.events] == [
        (2, EVENTS[0]), (3, EVENTS[1]), (1, EVENTS[2]),
    ]
    for rendered in (
        authored_fact_presenter.render_authored_focus(project, render_text=_render_text),
        authored_fact_presenter.render_product_story_contract(
            [{"label": "First Path", "semantic_slot": "first_path", "body": "Stale source order"}],
            project=project, render_text=_render_text,
        ),
    ):
        assert rendered.index(EVENTS[0]) < rendered.index(EVENTS[1]) < rendered.index(EVENTS[2])
        assert rendered.index('data-event-order="2"') < rendered.index('data-event-order="3"') < rendered.index('data-event-order="1"')
        assert "Proposed first run:" in rendered
        assert 'data-authority-kind="provisional_design"' in rendered
        assert "Stale source order" not in rendered
    assert facts["first_path_relations"] == source_inventory


def test_authored_fact_presenter_retains_actions_after_the_result() -> None:
    project = _project()
    rows = project["authored_facts"]["first_path_relations"]
    rows[1]["visible_result_quote"] = "blue receipt"
    rows[2]["visible_result_quote"] = ""

    view = authored_fact_presenter.authored_fact_view(project)

    assert view is not None
    assert [(event.order, event.text) for event in view.events] == list(enumerate(EVENTS, 1))
    rendered = authored_fact_presenter.render_authored_focus(project, render_text=_render_text)
    assert rendered.index(EVENTS[1]) < rendered.index(EVENTS[2])


@pytest.mark.parametrize("mutation", [
    "missing_order", "missing_precedence", "precedence_violation",
    "duplicate_result", "malformed_result", "missing_result",
])
def test_invalid_authored_order_never_revives_source_order(mutation: str) -> None:
    project = _project()
    facts = project["authored_facts"]
    if mutation == "missing_order":
        facts["provisional_design"].pop("first_run")
    elif mutation == "missing_precedence":
        facts.pop("source_precedence")
    elif mutation == "precedence_violation":
        facts["operational_constraints"] = ["Write the receipt before the ferry signal."]
        facts["source_precedence"] = [{"before_event": 2, "after_event": 1, "constraint_index": 1}]
    elif mutation == "duplicate_result":
        facts["first_path_relations"][1]["visible_result_quote"] = "blue receipt"
    elif mutation == "malformed_result":
        facts["first_path_relations"][2]["visible_result_quote"] = True
    else:
        facts["first_path_relations"][2]["visible_result_quote"] = ""
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        authored_fact_presenter.render_authored_focus(project, render_text=_render_text)
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        authored_fact_presenter.render_product_story_contract(
            [{"label": "First Path", "semantic_slot": "first_path", "body": "Stale source order"}],
            project=project, render_text=_render_text,
        )


@pytest.mark.parametrize("mutation", ["missing", "authority", "support"])
def test_malformed_design_cannot_fall_back_to_source_owned_capabilities(mutation: str) -> None:
    project = deepcopy(_project())
    facts = project["authored_facts"]
    if mutation == "missing":
        facts.pop("provisional_design")
    elif mutation == "authority":
        facts["provisional_design"]["authority_kind"] = "source_grounded"
    else:
        facts["provisional_design"]["components"][0]["supported_event_orders"] = [99]
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        authored_fact_presenter.authored_fact_view(project)
    with pytest.raises(GreenfieldAuthoredSemanticsError):
        authored_fact_presenter.render_authored_focus(project, render_text=_render_text)
