from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_workstream_titles
from odylith.runtime.domain_intelligence.greenfield_first_path_actor import FirstPathActorAction
from odylith.runtime.domain_intelligence.greenfield_first_path_actor import resolve_first_path_events
from odylith.runtime.domain_intelligence.greenfield_first_path_actor import select_first_path_actor_action
from odylith.runtime.domain_intelligence.greenfield_first_path_completeness import has_concise_coordinated_first_path
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps


_CHILD_FIRST_PATH = (
    "A parent or teacher creates an account, adds a child, and picks an age band. "
    "The child opens an illustrated scenario, makes a choice at the decision point, "
    "sees a caring consequence and a one-line reflection, and finishes the moment. "
    "The grown-up later opens a simple recap."
)
_CHILD_ACTORS = [
    "Child learner: makes the choices and does the reflecting",
    "Parent: sets up the child and reviews progress at home",
    "Teacher or counselor: runs it for a small group",
]
_GLP1_FIRST_PATH = (
    "A user sets up their medication, current dose, and weekly injection day. When a dose is due, "
    "the app reminds them; they confirm the injection, optionally log their weight and any side effects, "
    "and the app records it, advances them along their titration schedule, and shows the next due date."
)


def test_semantic_events_and_title_share_child_learner_actor_ownership() -> None:
    model = build_greenfield_semantic_model(
        title="Stand Tall",
        state_object="A private learner practice record",
        first_path=_CHILD_FIRST_PATH,
        proof_boundary="One learner completes a scenario and a parent can review the recap.",
        components=[],
        human_actors=_CHILD_ACTORS,
    )
    title = confirmed_workstream_titles(
        label="Stand Tall",
        components=[
            {"label": "Account and Learner Profile Service"},
            {"label": "Scenario Library Service"},
            {"label": "Choice and Consequence Engine"},
        ],
        internal_systems=[],
        first_path=_CHILD_FIRST_PATH,
        state_object="A private learner practice record",
        proof_boundary="One learner completes a scenario and a parent can review the recap.",
        human_actors=_CHILD_ACTORS,
    )[0]

    assert [(event.actor, event.action) for event in model.first_path_contract.events[:6]] == [
        ("Parent", "creates"),
        ("Parent", "adds"),
        ("Parent", "picks"),
        ("Child learner", "opens"),
        ("Child learner", "makes"),
        ("Child learner", "sees"),
    ]
    assert title == "Let Child Learner Make a Choice at the Decision Point"


def test_actor_object_mentions_do_not_transfer_event_ownership() -> None:
    events = resolve_first_path_events(
        first_path_steps(
            "A parent records learner consent. The learner opens a scenario. The learner chooses a response."
        ),
        lead_actor="Learner",
        human_actors=["Learner", "Parent"],
    )

    assert [(event.actor, event.action) for event in events] == [
        ("Parent", "record learner consent"),
        ("Learner", "open a scenario"),
        ("Learner", "choose a response"),
    ]
    assert select_first_path_actor_action(events, lead_actor="Learner") == FirstPathActorAction(
        actor="Learner",
        action="choose a response",
        text="The learner chooses a response",
    )


def test_parent_lead_skips_account_profile_and_child_setup_before_material_action() -> None:
    events = resolve_first_path_events(
        first_path_steps(
            "A parent creates an account. The parent adds a profile. The parent adds a child. "
            "The parent chooses the first practice scenario."
        ),
        lead_actor="Parent",
        human_actors=["Parent"],
    )

    assert select_first_path_actor_action(events, lead_actor="Parent") == FirstPathActorAction(
        actor="Parent",
        action="choose the first practice scenario",
        text="The parent chooses the first practice scenario",
    )


def test_glp1_pronouns_carry_human_actor_and_system_events_stay_out_of_title_selection() -> None:
    actor = "Person on the GLP-1 Medication"
    events = resolve_first_path_events(
        first_path_steps(_GLP1_FIRST_PATH),
        lead_actor=actor,
        human_actors=[actor],
    )

    assert [event.actor for event in events] == [actor] * 7
    assert [event.human_owned for event in events] == [True, False, True, True, False, False, False]
    assert [event.action for event in events[2:4]] == [
        "confirm the injection",
        "optionally log their weight and any side effects",
    ]
    assert select_first_path_actor_action(events, lead_actor=actor) == FirstPathActorAction(
        actor=actor,
        action="confirm the injection",
        text="They confirm the injection",
    )


def test_glp1_title_uses_confirmation_instead_of_setup_or_system_action() -> None:
    title = confirmed_workstream_titles(
        label="GLP-1 Companion",
        components=[
            {"label": "Medication and Titration Schedule Model Service"},
            {"label": "Injection Log Service"},
        ],
        internal_systems=[],
        first_path=_GLP1_FIRST_PATH,
        state_object="Single User's Medication Journey",
        proof_boundary="One user confirms an injection and sees the next due date.",
        human_actors=["Person on the GLP-1 Medication"],
    )[0]

    assert title == "Let Person on the GLP-1 Confirm the Injection"
    assert "Set Up" not in title
    assert "App Reminds" not in title


def test_actorless_steps_keep_the_fallback_actor_with_the_selected_action() -> None:
    events = resolve_first_path_events(
        first_path_steps("Open the workspace. Approve the release packet."),
        lead_actor="Release Analyst",
        human_actors=["Release Analyst"],
    )

    assert select_first_path_actor_action(events, lead_actor="Release Analyst") == FirstPathActorAction(
        actor="Release Analyst",
        action="approve the release packet",
        text="Approve the release packet",
    )


def test_missing_lead_actor_uses_one_fallback_event_pair() -> None:
    events = resolve_first_path_events(
        first_path_steps("A coordinator opens the workspace. A reviewer approves the release packet."),
        lead_actor="Analyst",
        human_actors=["Analyst", "Coordinator", "Reviewer"],
    )

    assert select_first_path_actor_action(events, lead_actor="Analyst") == FirstPathActorAction(
        actor="Reviewer",
        action="approve the release packet",
        text="A reviewer approves the release packet",
    )


def test_undeclared_generic_subject_keeps_the_accepted_lead_actor() -> None:
    events = resolve_first_path_events(
        first_path_steps("A participant notices an issue. The product shows a pattern summary."),
        lead_actor="Affected User",
        human_actors=["Affected User"],
    )

    assert [event.actor for event in events] == ["Affected User", "Affected User"]
    assert [event.human_owned for event in events] == [True, False]


def test_product_subject_does_not_become_a_synthetic_human_actor() -> None:
    first_path = "A resident submits a repair request. The app routes the request. A coordinator reviews the request."
    actors = ["Resident", "Coordinator"]
    events = resolve_first_path_events(
        first_path_steps(first_path),
        lead_actor="Resident",
        human_actors=actors,
    )
    model = build_greenfield_semantic_model(
        title="Repair Request Tracker",
        state_object="Repair request",
        first_path=first_path,
        proof_boundary="One request reaches coordinator review.",
        components=[],
        human_actors=actors,
    )

    assert [event.actor for event in events] == ["Resident", "Resident", "Coordinator"]
    assert [event.human_owned for event in events] == [True, False, True]
    assert all(event.actor.casefold() != "app" for event in events)
    assert [event.actor for event in model.first_path_contract.events] == ["Resident", "Resident", "Coordinator"]


def test_qualified_product_subject_cannot_supply_a_human_workstream_action() -> None:
    first_path = (
        "A resident opens the workspace. The routing engine assigns a coordinator. "
        "The resident chooses a service window."
    )
    events = resolve_first_path_events(
        first_path_steps(first_path),
        lead_actor="Resident",
        human_actors=["Resident"],
    )
    selected = select_first_path_actor_action(events, lead_actor="Resident")
    title = confirmed_workstream_titles(
        label="Service Window Coordinator",
        components=[{"label": "Routing Engine"}],
        internal_systems=[],
        first_path=first_path,
        state_object="Service request",
        proof_boundary="One resident chooses a service window.",
        human_actors=["Resident"],
    )[0]

    assert [event.human_owned for event in events] == [True, False, True]
    assert selected == FirstPathActorAction(
        actor="Resident",
        action="choose a service window",
        text="The resident chooses a service window",
    )
    assert title == "Let Resident Choose a Service Window"


@pytest.mark.parametrize(
    "system_step",
    (
        "The routing engine automatically assigns a coordinator.",
        "The routing-engine then assigns a coordinator.",
    ),
)
def test_qualified_system_action_with_modifier_cannot_supply_human_title(
    system_step: str,
) -> None:
    first_path = (
        "A resident opens a request. "
        f"{system_step} "
        "The resident chooses a service window."
    )
    events = resolve_first_path_events(
        first_path_steps(first_path),
        lead_actor="Resident",
        human_actors=["Resident"],
    )
    title = confirmed_workstream_titles(
        label="Service Window Coordinator",
        components=[{"label": "Routing Engine"}],
        internal_systems=[],
        first_path=first_path,
        state_object="Service request",
        proof_boundary="One resident chooses a service window.",
        human_actors=["Resident"],
    )[0]

    assert [event.human_owned for event in events] == [True, False, True]
    assert title == "Let Resident Choose a Service Window"


def test_concise_first_path_requires_an_actor_led_action() -> None:
    assert has_concise_coordinated_first_path("A reviewer opens and approves one record.")
    assert not has_concise_coordinated_first_path("The dashboard is working and shows project status.")
