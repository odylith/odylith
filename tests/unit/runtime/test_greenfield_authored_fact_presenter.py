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


@pytest.mark.parametrize("scope_limit", (
    "Outside this first path, observers may inspect receipts.",
    "Batch imports are excluded from the first release.",
    "Do not automate reviewer judgment.",
))
def test_boundary_labels_preserve_source_scope_without_imposing_release_scope(scope_limit: str) -> None:
    project = _project()
    project["authored_facts"]["non_goals"] = [scope_limit]
    frozen = deepcopy(project)
    view = authored_fact_presenter.authored_fact_view(project)
    group = next(row for row in view.boundary_groups if row.key == "non_goals")

    assert group.label == "Scope limits"
    assert group.items == (scope_limit,)
    scalar = greenfield_authored_dashboard.authored_product_boundary(
        components=({"label": "Receipt review"},), internal_systems=(),
        external_systems=(), non_goals=(scope_limit,),
    )
    assert scalar.endswith("Source-stated scope limits:\n" + scope_limit)
    assert project == frozen


def test_authored_fact_view_preserves_unseen_typed_facts_without_prose_parsing() -> None:
    view = authored_fact_presenter.authored_fact_view(_project())

    assert view is not None
    assert [(event.order, event.event_quote) for event in view.events] == [
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


def test_authored_fact_presenter_lists_people_once_and_preserves_first_path() -> None:
    project = _project()
    frozen = deepcopy(project)
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
                "label": "Proposed capabilities",
                "semantic_slot": "owned_capabilities",
                "body": "structured fallback",
            },
        ],
        project=project,
        render_text=_render_text,
    )

    assert story.count("data-authored-event-actor-label") == 0
    assert story.count("data-authored-event-actor-value") == 3
    assert story.count("data-authored-event-details") == 1
    assert story.count("data-authored-event-evidence") == 3
    assert '<details data-authored-event-details open' not in story
    assert story.count("data-authored-event-quote") == 3
    assert story.index(EVENTS[0]) < story.index(EVENTS[1]) < story.index(EVENTS[2])
    assert actors is not None
    assert actors.count("data-authored-actor=") == 2
    assert actors.count('class="project-actor-card project-actor-card-name"') == 2
    assert actors.count('data-authored-fact-list="actor"') == 0
    assert actors.count("data-authored-fact-item") == 0
    assert '<h3>Quartz Keeper</h3>' in actors
    assert '<h3>Silent Reviewer</h3>' in actors
    assert actors.index("Quartz Keeper") < actors.index("Silent Reviewer")
    assert all(event not in actors for event in EVENTS)
    assert "Named in project evidence; no first-path action is assigned." not in actors
    assert project == frozen
    assert story.count('data-authored-fact-list="first_path"') == 1
    assert '<p data-proposed-first-run-label>Proposed first run:</p>' in story
    assert story.count('data-authored-fact-list="owned_capabilities"') == 1
    assert story.count("data-authored-boundary-group") == 4
    assert 'data-authority-kind="provisional_design"' in story
    assert '<h3 data-provisional-design-label>Proposed capabilities</h3>' in story
    assert '<p data-provisional-design-label>' not in story
    assert "Proposed components:" in story
    assert "Named systems:" in story
    assert "Own blue-receipt custody." not in story
    assert "Own amber-ferry evidence." not in story
    assert story.index("Rill Engine") < story.index("Harbor Ledger")
    assert "Beacon Console" in story
    assert story.index("Delta Relay") < story.index("North Archive")
    assert ".;" not in story
    assert ".." not in story


def test_event_narrative_and_closed_evidence_preserve_literal_typed_values() -> None:
    project = _project()
    exact = 'Quartz Keeper keeps café  IDs and <tag> & "proof".\nPreserve the final 日本語 condition.'
    project["authored_facts"]["first_path_relations"][0]["event_quote"] = exact
    frozen = deepcopy(project)
    story = authored_fact_presenter.render_product_story_contract(
        [{"label": "First Path", "semantic_slot": "first_path", "body": "Stale fallback"}],
        project=project, render_text=_render_text,
    )
    assert f'<span data-authored-event-quote>{html.escape(exact)}</span>' in story
    assert f'<dt>Source event</dt><dd>{html.escape(exact)}</dd>' in story
    assert '<dt>Actor</dt><dd data-authored-event-actor-value>Quartz Keeper</dd>' in story
    assert '<dt>Actor kind</dt><dd>human</dd>' in story
    assert 'data-authored-event-details><summary>Supporting details</summary>' in story
    assert story.count("<details") == 1
    assert story.count("<summary>Supporting details</summary>") == 1
    assert story.count("data-authored-event-evidence") == 3
    assert story.index('</ol><details data-authored-event-details>') > story.index(EVENTS[2])
    assert "Actor:" not in story and "Stale fallback" not in story
    assert project == frozen


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
        "Source-stated scope limits:\n"
        "Do not claim live settlement.\n"
        "Do not automate reviewer judgment."
    )


def test_authored_fact_presenter_keeps_scalar_story_for_legacy_project() -> None:
    project = {"focus": "One legacy focus sentence."}
    assert authored_fact_presenter.authored_fact_view(project) is None
    rendered = authored_fact_presenter.render_product_story_contract(
        [{"label": "First Path", "semantic_slot": "first_path", "body": project["focus"]}],
        project=project, render_text=_render_text,
    )
    assert "One legacy focus sentence." in rendered
    assert "data-authored-fact-item" not in rendered


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
    assert [(event.order, event.event_quote) for event in view.events] == [
        (2, EVENTS[0]), (3, EVENTS[1]), (1, EVENTS[2]),
    ]
    for rendered in (
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
    assert [(event.order, event.event_quote) for event in view.events] == list(enumerate(EVENTS, 1))
    rendered = authored_fact_presenter.render_product_story_contract(
        [{"label": "First Path", "semantic_slot": "first_path", "body": ""}],
        project=project, render_text=_render_text,
    )
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


def test_structured_risk_card_preserves_exact_fields_and_traceability() -> None:
    row = {
        "key": "retention-boundary", "risk": "Data retention risk",
        "statement": "Personal records could outlive the stated retention period.",
        "mitigation": "Delete only after the review period ends.",
        "trigger": "The review period ends before deletion succeeds.",
        "verification": "A failed deletion retains the pending status.",
        "scope": "Components: archive; workstreams: cleanup; source events: 2.",
        "scope_paths": [{"event_order": 2, "component_key": "archive", "workstream_key": "cleanup"}],
    }
    before = deepcopy(row)
    rendered = authored_fact_presenter.render_authored_risk_cards([row], render_text=_render_text)
    assert "<h3>Data retention risk</h3>" in rendered
    assert '<p class="project-risk-statement" data-risk-statement>' in rendered
    assert '<p data-risk-mitigation>' in rendered
    assert '<details class="project-risk-details"><summary>Risk details</summary>' in rendered
    assert "Proposed category" not in rendered
    for key in ("statement", "mitigation", "trigger", "verification", "scope"):
        assert rendered.count(row[key]) == 1
    assert "Source event 2 · Component archive · Workstream cleanup" in rendered
    assert 'data-risk-key="retention-boundary"' in rendered
    assert row == before


def test_category_backed_risk_uses_statement_as_heading_and_discloses_category() -> None:
    row = {
        "key": 'privacy-"boundary"',
        "category": "privacy",
        "risk": "Privacy & access risk",
        "statement": "A reviewer <could> see records outside the approved account boundary.",
        "mitigation": "Require account-scoped access & record every review.",
        "trigger": "A reviewer opens a record from another account.",
        "verification": "The cross-account request is denied and audited.",
        "scope": "Components: review; workstreams: access; source events: 3.",
        "scope_paths": [{"event_order": 3, "component_key": "review", "workstream_key": "access"}],
    }
    before = deepcopy(row)

    rendered = authored_fact_presenter.render_authored_risk_cards([row], render_text=_render_text)

    assert rendered.count("<h3") == 1
    assert (
        '<h3 class="project-risk-statement" data-risk-statement>'
        "A reviewer &lt;could&gt; see records outside the approved account boundary.</h3>"
    ) in rendered
    assert "<h3>Privacy &amp; access risk</h3>" not in rendered
    assert '<details class="project-risk-details"><summary>Risk details</summary>' in rendered
    assert "<details open" not in rendered
    assert "<dt>Proposed category</dt><dd>Privacy &amp; access risk</dd>" in rendered
    assert "<p data-risk-mitigation>Require account-scoped access &amp; record every review.</p>" in rendered
    assert "Source event 3 · Component review · Workstream access" in rendered
    assert 'data-risk-key="privacy-&quot;boundary&quot;"' in rendered
    assert row == before


def test_no_material_risk_keeps_named_heading_and_explanatory_statement() -> None:
    row = {
        "key": "no-material-risk",
        "risk": "No material risk identified",
        "meaning": "No source-backed material risk was identified for this project.",
    }

    rendered = authored_fact_presenter.render_authored_risk_cards([row], render_text=_render_text)

    assert "<h3>No material risk identified</h3>" in rendered
    assert (
        '<p class="project-risk-statement" data-risk-statement>'
        "No source-backed material risk was identified for this project.</p>"
    ) in rendered
    assert "project-risk-details" not in rendered
    assert "Proposed category" not in rendered


def _declared_path_project() -> dict:
    quotes = (
        "Author opens a conformance record.",
        "Maintainer links the component contract.",
        "QA records keyboard results.",
        "Reviewer records the disposition.",
        "Manager verifies the published status.",
        "Manager publishes the status.",
    )
    rows = [
        {"order": order, "event_quote": quote, "actor_kind": "human",
         "actor_fact_quote": quote.split()[0],
         "visible_result_quote": "published status" if order == 5 else ""}
        for order, quote in enumerate(quotes, 1)
    ]
    design = structural_design_fixture(tuple(range(1, 7)))
    design["first_run"] = {
        "event_orders": [1, 2, 3, 4, 6, 5],
        "rationale": "Publish the status before its verification.",
    }
    return {"authored_facts": {
        "authored_semantics_version": "odylith.greenfield.authored-semantics.v19",
        "source_event_relations": rows,
        "first_path_relations": deepcopy(rows[:5]),
        "provisional_design": design,
        "source_precedence": [{"before_event": 6, "after_event": 5, "constraint_index": 1}],
        "operational_constraints": ["Publish the status before verifying it."],
    }}


@pytest.mark.parametrize("proposed_orders", [[1, 2, 3, 4, 6, 5], [3, 1, 2, 4, 6, 5]])
def test_current_first_path_html_uses_declared_five_without_changing_proposed_six(proposed_orders) -> None:
    project = _declared_path_project()
    project["authored_facts"]["provisional_design"]["first_run"]["event_orders"] = proposed_orders
    before = deepcopy(project)
    view = authored_fact_presenter.authored_fact_view(project)
    assert [event.order for event in view.events] == proposed_orders
    assert [event.order for event in view.declared_events] == [1, 2, 3, 4, 5]
    rendered = authored_fact_presenter.render_product_story_contract(
        [{"label": "First Path", "semantic_slot": "first_path", "body": "Stale fallback"}],
        project=project, render_text=_render_text,
    )
    assert rendered.count("data-authored-event-quote") == 5
    assert 'data-event-order="6"' not in rendered
    assert "Proposed first run:" not in rendered
    assert 'data-authority-kind="source_grounded"' in rendered
    for row in project["authored_facts"]["first_path_relations"]:
        assert rendered.count(_render_text(row["event_quote"])) == 2
        assert f'data-authored-event-actor-value>{row["actor_fact_quote"]}</dd>' in rendered
    assert "Stale fallback" not in rendered
    assert '<details data-authored-event-details open' not in rendered
    assert project == before


@pytest.mark.parametrize("damage", [
    "missing", "empty", "scalar", "missing_order", "duplicate", "unknown_order",
    "boolean_order", "changed_quote", "changed_actor",
])
def test_current_declared_path_malformed_or_missing_never_uses_proposed_fallback(damage) -> None:
    project = _declared_path_project()
    facts = project["authored_facts"]
    rows = facts["first_path_relations"]
    if damage == "missing":
        facts.pop("first_path_relations")
    elif damage == "empty":
        rows.clear()
    elif damage == "scalar":
        facts["first_path_relations"] = "Author opens a conformance record."
    elif damage == "missing_order":
        rows[0].pop("order")
    elif damage == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif damage == "unknown_order":
        rows[0]["order"] = 99
    elif damage == "boolean_order":
        rows[0]["order"] = True
    elif damage == "changed_quote":
        rows[0]["event_quote"] = "Author approves the record."
    elif damage == "changed_actor":
        rows[0]["actor_fact_quote"] = "Manager"
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="declared path"):
        authored_fact_presenter.render_product_story_contract(
            [{"label": "First Path", "semantic_slot": "first_path", "body": "Plausible fallback"}],
            project=project, render_text=_render_text,
        )
