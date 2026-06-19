from __future__ import annotations

import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    compile_greenfield_semantics,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    repair_greenfield_semantic_projections,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    select_visible_result_candidate,
)


def test_semantic_compiler_prefers_first_path_result_over_release_proof() -> None:
    first_path = _lifecycle_first_path()
    proof = _lifecycle_proof_boundary()

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)

    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path == "first_path.visible_result"
    assert candidate.text == "same event settled into a finished result with its final status and event list intact"
    assert "version" not in candidate.text.casefold()
    assert "proven when" not in candidate.text.casefold()


def test_confirmed_intent_completion_rebuilds_proof_poisoned_product_fields() -> None:
    intent = _lifecycle_intent()
    poison = "the visible result produced by version 0.0.1 is proven when an event can be viewed across its full lifecycle"
    intent["problem"] = f"Operators need a dependable way to understand event state and decide with {poison}."
    intent["opportunity"] = f"Make the first version valuable by ending in {poison}."
    intent["product_view"] = f"Lifecycle Review is useful when operators can use {poison} to decide the next action."
    intent["success_metrics"] = [
        f"Users can see {poison} without manual interpretation.",
        f"Missing input is fixed before {poison} is treated as real.",
        f"Release readiness requires evidence that {poison} is correct.",
    ]

    completed = complete_confirmed_intent(intent)
    rendered = json.dumps(
        {
            "problem": completed["problem"],
            "opportunity": completed["opportunity"],
            "product_view": completed["product_view"],
            "success_metrics": completed["success_metrics"],
        },
        sort_keys=True,
    ).casefold()

    assert "visible result produced by version" not in rendered
    assert "version 0.0.1 is proven when" not in rendered
    assert "same event settled into a finished result" in rendered


def test_semantic_compiler_counterexample_repairs_existing_projection_poisoning() -> None:
    proposal = _minimal_lifecycle_proposal()
    proof = proposal["intent"]["proof_boundary"]
    proposal["intent"]["product_view"] = (
        "Lifecycle Review is useful when operators can confidently use the visible result produced by "
        f"{proof} to decide the next action."
    )
    proposal["backlog"][0]["product_view"] = proposal["intent"]["product_view"]

    failed = compile_greenfield_semantics(proposal)

    assert failed.status == "failed"
    assert any(item.code == "projection.proof_boundary_source" for item in failed.counterexamples)

    assert repair_greenfield_semantic_projections(proposal) is True
    repaired = ensure_apply_semantic_model(proposal, refresh=True)
    passed = compile_greenfield_semantics(repaired)
    rendered = json.dumps(
        {
            "intent_product_view": repaired["intent"]["product_view"],
            "backlog_product_view": repaired["backlog"][0]["product_view"],
            "semantic_visible_result": repaired["semantic_model"]["first_path_contract"]["visible_result"],
        },
        sort_keys=True,
    ).casefold()

    assert passed.status == "passed"
    assert "visible result produced by version" not in rendered
    assert "version 0.0.1 is proven when" not in rendered
    assert repaired["semantic_model"]["first_path_contract"]["visible_result"].startswith("same event settled")


def test_confirmed_intent_completion_does_not_wrap_visible_outcome_as_produced_by() -> None:
    intent = complete_confirmed_intent(
        {
            "title": "Guided Workout Timer",
            "product_story": (
                "Guided Workout Timer helps a trainee run one interval workout with clear timing, hands-free cues, "
                "pause and resume control, and a reviewable session history after the workout ends."
            ),
            "state_object": (
                "A workout session tracks the chosen workout, interval plan, current interval, elapsed time, cue state, "
                "pause state, completion state, and saved history entry."
            ),
            "first_path": (
                "A trainee chooses a workout, starts it, follows each interval with audio and on-screen cues, "
                "marks the session complete, and saves the session to history with date, workout, and total time."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when a trainee can choose a preset workout, complete it, and see the saved "
                "session in history with date, workout, and total time."
            ),
            "human_actors": ["Trainee following a guided workout."],
            "external_systems": ["Optional device wake lock."],
            "internal_systems": ["Workout library.", "Interval timer engine.", "Session history."],
            "assumptions": ["The first release runs locally with preset workouts."],
            "ambiguities": ["Whether custom workout building is first release or deferred."],
        }
    )
    rendered = json.dumps(intent, sort_keys=True).casefold()

    assert "visible result produced by" not in rendered
    assert "saved session" in rendered


def _minimal_lifecycle_proposal() -> dict[str, Any]:
    intent = complete_confirmed_intent(_lifecycle_intent())
    return ensure_apply_semantic_model(
        {
            "intent": intent,
            "project_brief": {
                "first_path": intent["first_path"],
                "proof": intent["proof_boundary"],
                "state_object": intent["state_object"],
            },
            "backlog": [
                {
                    "title": "Review the event lifecycle",
                    "problem": "Operators need a clear event lifecycle view.",
                    "opportunity": "Build the first lifecycle review.",
                    "product_view": "Operators can review the event result.",
                    "success_metrics": ["The result is visible.", "Bad input is blocked.", "Proof is repeatable."],
                    "component_focus": [],
                    "recommended_first_slice": "Review one event lifecycle.",
                    "validation": ["Replay the successful path."],
                }
            ],
            "components": [],
            "diagrams": [],
        },
        refresh=True,
    )


def _lifecycle_intent() -> dict[str, Any]:
    return {
        "title": "Lifecycle Review",
        "product_story": (
            "Lifecycle Review gives operators one place to follow an event from scheduled state through live "
            "updates and into a durable finished result. The product matters because people need the current "
            "status, event trail, and final outcome without reconstructing it from separate systems."
        ),
        "state_object": (
            "The event record contains an identity, schedule, live status, update timeline, final status, "
            "source evidence, correction history, and review decision."
        ),
        "first_path": _lifecycle_first_path(),
        "human_actors": [
            "Operator: a person checking current and finished event status",
            "Reviewer: a person confirming the result is ready to rely on",
        ],
        "external_systems": [
            "Reference data source for scheduled events",
            "Status feed for live updates",
        ],
        "internal_systems": [
            "Schedule service: lists current and upcoming events",
            "Live status service: updates the event status and timeline",
            "Result history store: keeps finished event records available",
            "Review surface: shows the event state and proof before release",
        ],
        "assumptions": [
            "The first release can use deterministic fixtures for scheduled and live event data.",
            "Operators need reviewable event state before broader automation is useful.",
            "Security, privacy, accessibility, audit, and retention duties follow the event state involved.",
        ],
        "ambiguities": [
            "Which source is authoritative if scheduled and live status data disagree?",
            "How quickly must live status changes appear for the first release to be useful?",
        ],
        "proof_boundary": _lifecycle_proof_boundary(),
    }


def _lifecycle_first_path() -> str:
    return (
        "A visitor opens today's events, opens a live event, watches the status and timeline update as the "
        "event progresses, and after completion sees that same event settle into a finished result with its "
        "final status and event list intact."
    )


def _lifecycle_proof_boundary() -> str:
    return (
        "Version 0.0.1 is proven when an event can be viewed across its full lifecycle: appearing as a "
        "scheduled item, showing live status with an event timeline, and settling into a finished result "
        "that remains browsable for at least one event type."
    )
