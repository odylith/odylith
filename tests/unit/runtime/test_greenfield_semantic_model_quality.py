from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_semantic_model import FirstPathContract
from odylith.runtime.domain_intelligence.greenfield_semantic_model import _first_path_contract_claim
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase


def test_semantic_model_prefers_terminal_visible_outcome_over_mid_path_confirmation() -> None:
    first_path = (
        "The first release proves one complete path: a home cook picks a recipe, confirms ingredients are staged, "
        "starts the cooking run, follows prompts when the robot needs input, and sees the run finish in a "
        "safe-to-serve state with emergency stop available throughout."
    )
    proof_boundary = (
        "The first release is proven when one recipe can move from selection to safe-to-serve completion with "
        "staged-ingredient checks, live sensor validation, prompted user actions, emergency stop, replayable run "
        "evidence, and clear failure handling."
    )
    model = build_greenfield_semantic_model(
        title="Cooking Robot Controller",
        state_object=(
            "The product manages a cooking run, including the selected recipe, staged ingredients, "
            "sensor readings, heat and timing state, operator prompts, safety stops, and final serve readiness."
        ),
        first_path=first_path,
        proof_boundary=proof_boundary,
        components=[],
        human_actors=["Home Cook: selects dishes and responds to prompts"],
    )
    contract = model.first_path_contract

    assert model.domain_ontology.state_object == "Cooking Run"
    assert first_path_outcome_phrase(first_path, proof_boundary=proof_boundary) == (
        "a safe-to-serve state with emergency stop available throughout"
    )
    assert contract.visible_result == "a safe-to-serve state with emergency stop available throughout"
    assert [(event.action, event.visible_result) for event in contract.events] == [
        ("picks", False),
        ("confirms", False),
        ("starts", False),
        ("follows", False),
        ("sees", True),
    ]


def test_semantic_model_preserves_conditional_visible_outcome() -> None:
    first_path = (
        "Berth planner can reconcile container discharge, quay crane availability, tug window, and berth occupancy, "
        "then see whether the vessel can sail."
    )
    model = build_greenfield_semantic_model(
        title="Morning Vessel Call",
        state_object="A vessel call record with berth, crane, tug, and occupancy readiness.",
        first_path=first_path,
        proof_boundary="One berth planner can reconcile vessel-call readiness before sail time.",
        components=[],
        human_actors=["Berth Planner"],
    )

    assert first_path_outcome_phrase(first_path) == "whether the vessel can sail"
    assert model.first_path_contract.visible_result == "whether the vessel can sail"


def test_first_path_outcome_does_not_concatenate_title_cased_actor_and_action() -> None:
    first_path = (
        "Home Cook picks a recipe, the controller validates the robot is ready, runs the step sequence, "
        "surfaces progress, and reaches a finished safe state."
    )

    outcome = first_path_outcome_phrase(
        first_path,
        proof_boundary=(
            "First version proves load a recipe, run its steps with closed-loop control, "
            "hit a safe finished state, and honor an emergency stop."
        ),
    )

    assert "cookpicks" not in outcome.casefold()
    assert outcome in {"a finished safe state", "Progress"}


def test_completion_action_phrase_strips_subject_before_user_can_clause() -> None:
    proposal = {
        "intent": {
            "first_path": (
                "Home Cook picks a recipe, the controller validates the robot is ready, runs the step sequence, "
                "surfaces progress, and reaches a finished safe state."
            )
        }
    }

    action = completion_text.action_phrase(proposal)
    product_view = completion_text.workstream_product_view(
        label="Recipe Sequencer",
        action=action,
        outcome="a finished safe state",
    )

    assert action == "pick a recipe"
    assert "user can home cook picks" not in product_view.casefold()
    assert "user can pick a recipe" in product_view.casefold()


def test_semantic_model_attaches_terminal_visible_result_when_record_is_noun_and_verb() -> None:
    first_path = (
        "Record owner records a record, compliance records review evidence, "
        "and the office records readiness."
    )
    model = build_greenfield_semantic_model(
        title="Grants Compliance Record Office",
        state_object="A grant compliance record with evidence, review status, and readiness.",
        first_path=first_path,
        proof_boundary="One record has evidence, review status, and readiness proof.",
        components=[],
        human_actors=["Record owner", "Compliance reviewer"],
        internal_systems=["Record desk", "Evidence log", "Readiness view"],
    )
    contract = model.first_path_contract

    assert contract.visible_result == "Recorded readiness"
    assert [(event.text, event.visible_result) for event in contract.events] == [
        ("Record owner records a record", False),
        ("Compliance records review evidence", False),
        ("The office records readiness", True),
    ]


def test_semantic_model_preserves_explicit_actor_subjects_across_multi_actor_path() -> None:
    first_path = (
        "City dispatcher records evacuation support request, "
        "tribal liaison reviews restricted access needs, "
        "hospital coordinator records capacity constraints, "
        "mutual-aid officer confirms resource commitments, "
        "shelter lead records readiness, "
        "and emergency commander publishes public coordination status."
    )
    model = build_greenfield_semantic_model(
        title="Regional Coordination Workspace",
        state_object=(
            "A coordination record with support request, access restriction, capacity constraint, "
            "resource commitment, readiness, and public coordination status."
        ),
        first_path=first_path,
        proof_boundary="One coordination record moves through access, capacity, resource, readiness, and public status proof.",
        components=[],
        human_actors=[
            "City dispatcher",
            "Tribal liaison",
            "Hospital coordinator",
            "Mutual-aid officer",
            "Shelter lead",
            "Emergency commander",
        ],
        internal_systems=[
            "Request intake",
            "Access review board",
            "Capacity ledger",
            "Resource commitment tracker",
            "Readiness board",
            "Public status view",
        ],
    )

    assert [(event.actor, event.text) for event in model.first_path_contract.events] == [
        ("City dispatcher", "City dispatcher records evacuation support request"),
        ("Tribal liaison", "Tribal liaison reviews restricted access needs"),
        ("Hospital coordinator", "Hospital coordinator records capacity constraints"),
        ("Mutual-aid officer", "Mutual-aid officer confirms resource commitments"),
        ("Shelter lead", "Shelter lead records readiness"),
        ("Emergency commander", "Emergency commander publishes public coordination status"),
    ]


def test_semantic_model_claim_normalizes_actor_led_finite_tails() -> None:
    claim = _first_path_contract_claim(
        FirstPathContract(
            actor="Coordinators",
            action="",
            entity="update",
            mutation="",
            required_fields=(),
            persistence="",
            visible_result="proven update with source evidence",
            recovery_path="",
            deferred_scope=(),
            capability="Coordinators updates, assigning response owners, publishing status summaries, and proving every update with source evidence",
            raw_path="",
            events=(),
        )
    )

    assert claim == (
        "Coordinators can update, assign response owners, publish status summaries, "
        "and prove every update with source evidence."
    )


def test_outcome_selector_keeps_confirmed_user_result_before_downstream_handoff() -> None:
    first_path = (
        "The first complete path starts when a resident opens the web app, describes a repair, provides contact and "
        "availability details, reviews an estimate window, selects an appointment slot, and submits the request. "
        "The system confirms the booking, records the selected provider slot, shows the resident what happens next, "
        "and makes the booking available for provider review."
    )
    proof_boundary = (
        "A resident can create a repair request, choose a slot, receive a confirmed booking, and see the next step. "
        "A provider-facing queue receives the booking with the required repair context."
    )

    assert first_path_outcome_phrase(first_path, proof_boundary=proof_boundary) == "a confirmed booking"


def test_outcome_selector_extracts_object_from_coordinated_send_publish_action() -> None:
    first_path = (
        "A communications coordinator records a public question, tags the topic, assigns an owner, drafts a response, "
        "routes it for approval, records approval or requested edits, sends or publishes the approved response, "
        "and reviews the audit trail."
    )

    assert first_path_outcome_phrase(first_path) == "the approved response"


def test_operator_first_path_keeps_modifier_tail_with_visible_outcome() -> None:
    first_path = (
        "Operator picks a recipe, the controller validates the robot is ready, runs the step sequence with "
        "closed-loop heat and timing control, surfaces progress, and reaches a finished, safe-to-serve state, "
        "with an emergency stop available throughout."
    )
    model = build_greenfield_semantic_model(
        title="Cooking Robot Controller",
        state_object="A cook session with active recipe, current step, live sensor readings, and safety status.",
        first_path=first_path,
        proof_boundary=(
            "Release 0.0.1 succeeds when one user can run the first path to a safe finished state with emergency stop."
        ),
        components=[],
        human_actors=["Home Cook: selects dishes and responds to prompts"],
    )
    contract = model.first_path_contract
    rendered = f"{contract.capability} {contract.visible_result}"

    assert first_path_outcome_phrase(first_path) == (
        "a finished, safe-to-serve state with an emergency stop available throughout"
    )
    assert contract.visible_result == "a finished, safe-to-serve state with an emergency stop available throughout"
    assert contract.capability == (
        "picking a recipe, validating the robot is ready, and running the step sequence with closed-loop heat and timing control"
    )
    assert [event.target_entity for event in contract.events[:3]] == ["recipe", "robot ready", "step sequence"]
    assert "mutation `" not in model.proof_obligations[0].required_evidence
    assert generated_semantic_slop_issues({"proof": model.proof_obligations[0].required_evidence}) == []
    assert "Operator picks" not in rendered
    assert "With an emergency stop" not in rendered
    assert generated_public_copy_issues("semantic preview", rendered) == ()


def test_result_status_modifiers_stay_attached_to_visible_outcome() -> None:
    first_path = (
        "A researcher opens the lab, defines a new E91 run, launches it against the hardware, "
        "watches coincidences and the live CHSH value stream in, and ends with a completed run "
        "that reports whether the Bell inequality was violated, the QBER, and the key established, "
        "saved and viewable with prior runs."
    )

    model = first_path_model(first_path)
    outcome = first_path_outcome_phrase(first_path)

    assert len(model.steps) == 5
    assert model.visible_outcome == (
        "The Bell inequality was violated, the QBER, and the established key, saved and viewable with prior runs"
    )
    assert outcome == (
        "the Bell inequality was violated, the QBER, and the established key, saved and viewable with prior runs"
    )
    assert "the key established" not in outcome
    assert "saved and viewable with prior runs" in outcome

    possessive = first_path.replace("the key established", "the user's key established")
    possessive_model = first_path_model(possessive)
    possessive_outcome = first_path_outcome_phrase(possessive)

    assert possessive_model.visible_outcome == (
        "The Bell inequality was violated, the QBER, and the user's established key, saved and viewable with prior runs"
    )
    assert possessive_outcome == (
        "the Bell inequality was violated, the QBER, and the user's established key, saved and viewable with prior runs"
    )
    assert "user's key established" not in possessive_outcome.casefold()


def test_semantic_visible_result_preserves_quoted_result_and_parallel_verbs() -> None:
    first_path = (
        "A user connects a wearable, completes basic health and goal context, grants consent for selected data streams, "
        "and sees an initial dashboard after enough data is available. The first useful experience should show baseline "
        'trends, recovery and exertion patterns, estimated metabolic and biological age indicators, athletic capability '
        'markers, and clear "what changed" insights without making diagnosis claims.'
    )

    outcome = first_path_outcome_phrase(first_path)
    capability = first_path_capability_phrase(first_path)

    assert outcome == 'Clear "what changed" insights without making diagnosis claims'
    assert 'clear "what.' not in outcome.casefold()
    assert 'clear "what' in outcome.casefold() and '" insights' in outcome
    assert "baseline trends" not in outcome.casefold()
    assert "athletic capability markers" not in outcome.casefold()
    assert "grant consent" in capability
    assert "grants consent" not in capability
    assert "grant consent" in first_path_action_phrase(first_path)
    assert generated_public_copy_issues("semantic preview", outcome) == ()
    assert generated_semantic_slop_issues({"outcome": outcome}) == []


def test_semantic_proof_claim_normalizes_coordinated_title_role_actor() -> None:
    model = build_greenfield_semantic_model(
        title="Protocol Effect Tracker",
        state_object="A tracked protocol with active interventions and timestamped measurements.",
        first_path=(
            "A user creates a protocol, logs an active intervention with a start date and dose, "
            "records a baseline measurement, and adds a follow-up measurement."
        ),
        proof_boundary="Proven when a user can create a protocol and view the measurements on one timeline.",
        components=[],
        human_actors=["Self-experimenter or Quantified-self User: tracking their own protocol"],
    )

    claim = model.proof_obligations[0].claim

    assert claim.startswith("Self-experimenter or quantified-self user can create a protocol")
    assert "can complete creating" not in claim
    assert generated_public_copy_issues("claim", claim) == ()


def test_confirmed_intent_normalizes_product_manages_state_object_predicate() -> None:
    completed = complete_confirmed_intent(
        {
            "title": "Cooking Robot Controller",
            "product_story": (
                "A cook needs a safe robot-controlled cooking run with visible progress, prompt handling, "
                "and evidence when the run stops or finishes."
            ),
            "state_object": (
                "The product manages a cooking run, including selected recipe, staged ingredients, "
                "sensor readings, heat and timing state, operator prompts, safety stops, and final serve readiness."
            ),
            "first_path": (
                "Operator picks a recipe, the controller validates readiness, runs the first sequence, "
                "surfaces progress, and reaches a finished safe-to-serve state."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when one operator can choose a recipe, validate readiness, "
                "run the first sequence, see progress, and preserve safety-stop evidence."
            ),
        }
    )

    assert completed["state_object"].startswith("a cooking run, including selected recipe")
    assert "product manages" not in completed["state_object"].casefold()
