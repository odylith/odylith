from __future__ import annotations

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_semantic_model import FirstPathContract
from odylith.runtime.domain_intelligence.greenfield_semantic_model import _first_path_contract_claim
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
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
