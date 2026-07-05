from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_apply_semantic
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import APPLY_SEMANTIC_INPUT_VERSION
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import greenfield_apply_semantic_input
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import drop_requirement_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_requirement_control_step
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    compile_greenfield_semantics,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import GreenfieldSemanticCandidate
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    repair_greenfield_semantic_projections,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    select_visible_result_candidate,
)

DOMAIN_INTELLIGENCE = Path(__file__).resolve().parents[3] / "src/odylith/runtime/domain_intelligence"


def test_semantic_compiler_prefers_first_path_result_over_release_proof() -> None:
    first_path = _lifecycle_first_path()
    proof = _lifecycle_proof_boundary()

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)

    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path == "first_path.visible_result"
    assert candidate.text == "same event settled into a finished result with its final status and event list intact"
    assert "version" not in candidate.text.casefold()
    assert "proven when" not in candidate.text.casefold()


def test_semantic_compiler_accepts_release_readiness_as_first_path_result() -> None:
    first_path = (
        "Community stewards track dataset access requests, consent protocols, council decisions, "
        "revocation evidence, research-use limits. Release readiness for shared cultural records."
    )
    proof = (
        "Release 0.0.1 succeeds when the accepted first path is complete, reviewable, and blocked when required. "
        "The product shows the review workspace result, handles missing or invalid input with a clear blocker, "
        "and keeps replayable evidence for review."
    )

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)

    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path == "first_path.visible_result"
    assert candidate.text == "Release readiness for shared cultural records"


def test_semantic_compiler_nominalizes_terse_terminal_result_before_proof_boundary() -> None:
    first_path = "Reporter submits a report; owner reviews it; council publishes proof."
    proof = "Evidence custody and embargo decision."

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)
    report = compile_greenfield_semantics(
        {
            "intent": {"first_path": first_path, "proof_boundary": proof},
            "semantic_model": {"first_path_contract": {"visible_result": proof}},
        }
    )

    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path == "first_path.events.2"
    assert candidate.text == "published proof"
    assert report.status == "passed"
    assert report.quality_scores["proof_result_separation"] == 1.0


def test_semantic_compiler_nominalizes_actor_led_terminal_action_before_proof_boundary() -> None:
    first_path = (
        "Platform operators submit distributed agent jobs, track assigned worker progress, collect execution evidence, "
        "surface blockers, and publish a final run record with reviewer approval."
    )
    proof = "The product shows the workspace result and keeps replayable evidence for review."

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)

    assert candidate.source_kind == "first_path_event"
    assert candidate.text == "published final run record with reviewer approval"
    assert "workspace result" not in candidate.text


def test_semantic_compiler_derives_terminal_approval_result_before_proof_boundary() -> None:
    first_path = (
        "Marine ecologist can register a model candidate, attach dataset identity, run comparison evidence, "
        "review uncertainty, block unsafe claims, and approve only bounded release evidence."
    )
    proof = (
        "Release 0.0.1 succeeds when a researcher can complete one bounded model-risk release gate run, "
        "review inputs, method version, baseline comparison, uncertainty or tolerance, and reproduce the saved result."
    )

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)
    report = compile_greenfield_semantics(
        {
            "intent": {"first_path": first_path, "proof_boundary": proof},
            "semantic_model": {
                "first_path_contract": {
                    "visible_result": "approved bounded release evidence",
                    "events": [{"text": first_path, "visible_result": True}],
                }
            },
        }
    )

    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path.startswith("first_path.")
    assert candidate.text == "the approved bounded release evidence"
    assert "saved result" not in candidate.text
    assert report.status == "passed"


def test_semantic_compiler_keeps_object_list_results_ahead_of_proof_boundary() -> None:
    proof = "The product shows the workspace result and keeps replayable evidence for review."
    disclosure = (
        "Multi-party security disclosure council workspace user coordinates external vulnerability reports, "
        "affected partner review, embargo decisions, evidence custody, legal signoff, and public advisory "
        "release readiness without personalized notification campaigns in the first release."
    )
    spacecraft = (
        "Telemetry claims, fault hypotheses, simulation evidence, command risk, operator approvals, "
        "and recovery state before a corrective procedure is released."
    )

    disclosure_candidate = select_visible_result_candidate(disclosure, proof_boundary=proof)
    spacecraft_candidate = select_visible_result_candidate(spacecraft, proof_boundary=proof)

    assert disclosure_candidate.source_kind == "first_path_event"
    assert disclosure_candidate.text.startswith("coordinated external vulnerability reports")
    assert "workspace result" not in disclosure_candidate.text
    assert spacecraft_candidate.source_path == "first_path.visible_result"
    assert spacecraft_candidate.text.startswith("Telemetry claims")
    assert "workspace result" not in spacecraft_candidate.text


def test_semantic_compiler_uses_confirmed_context_before_proof_for_capability_path() -> None:
    first_path = (
        "A computer vision defect adjudication system user can track image sensor calibration, labeled defect classes, "
        "model confidence, reviewer overrides, production lot disposition, and traceable proof."
    )
    product_view = (
        "Computer Vision Defect Adjudication System earns trust when a computer vision defect adjudication system user "
        "can track image sensor calibration, labeled defect classes, model confidence, reviewer overrides, production lot "
        "disposition, and traceable proof. The visible result is the computer vision defect adjudication result. "
        "The result remains visible, blocked when needed, and reviewable."
    )
    state_object = (
        "A computer vision defect adjudication result record tracks the actor, source input, current status, owner, "
        "blocker, handoff, evidence, and version history for the first path."
    )
    proof = (
        "Release 0.0.1 succeeds when a computer vision defect adjudication system user can complete one representative path. "
        "The product shows the computer vision defect adjudication result, handles missing or invalid input with a clear "
        "blocker, and keeps replayable evidence for review."
    )

    candidate = select_visible_result_candidate(
        first_path,
        proof_boundary=proof,
        product_view=product_view,
        state_object=state_object,
    )
    proposal = ensure_apply_semantic_model(
        {
            "intent": {
                "title": "Computer Vision Defect Adjudication System",
                "first_path": first_path,
                "product_view": product_view,
                "state_object": state_object,
                "proof_boundary": proof,
            },
        },
        refresh=True,
    )
    report = compile_greenfield_semantics(proposal)

    assert candidate.source_kind == "intent_context"
    assert candidate.source_path == "intent.product_view.visible_result"
    assert candidate.text == "the computer vision defect adjudication result"
    assert proposal["apply_semantic_input"]["source_paths"]["visible_result"] == "intent.product_view.visible_result"
    assert proposal["semantic_model"]["first_path_contract"]["visible_result"] == candidate.text
    assert "accepted result" not in proposal["apply_semantic_input"]["first_path"].casefold()
    assert report.status == "passed"
    assert report.quality_scores["proof_result_separation"] == 1.0


def test_semantic_compiler_rejects_object_led_workflow_subjects() -> None:
    report = compile_greenfield_semantics(
        {
            "intent": {
                "first_path": "The decision summary turns an ambiguous waiver packet into a reviewable status.",
                "proof_boundary": (
                    "Release 0.0.1 succeeds when a reviewer can see the reviewable status, resolve missing input, "
                    "and keep evidence available for review."
                ),
            },
            "semantic_model": {
                "first_path_contract": {"visible_result": "a reviewable status"},
            },
        }
    )

    assert report.status == "failed"
    assert any(item.code == "first_path.non_human_workflow_subject" for item in report.counterexamples)


def test_semantic_compiler_prioritizes_terminal_first_path_result_over_long_proof_result() -> None:
    first_path = (
        "The home cook picks a recipe, the controller validates that ingredients are staged and sensors are live, "
        "runs the step sequence with closed-loop heat and timing control, shows progress, and reaches a finished "
        "safe-to-serve state with emergency stop available throughout."
    )
    proof = (
        "Release 0.0.1 succeeds when a home cook can load a structured recipe, run its cooking steps with "
        "closed-loop heat and timing, reach a safe finished state, and trigger emergency stop at any point "
        "in a hardware simulator."
    )

    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)

    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path == "first_path.events.5"
    assert candidate.text == "a finished safe-to-serve state with emergency stop available throughout"
    assert "hardware simulator" not in candidate.text.casefold()


def test_semantic_compiler_ignores_meta_quality_constraints_as_visible_result() -> None:
    first_path = (
        "Sports medicine coordinator can turn an ambiguous return-to-play case into a review-ready record using "
        "symptom checklist, neurocognitive test, trainer notes, clearance status, explicit expert review, "
        "auditable decision ledger, and a final return recommendation. The request has specialist jargon and "
        "operational handoff, so the artifacts must stay readable without losing domain depth. An architect must "
        "see bounded components, state ownership, events, and projection boundaries. The post-confirm create must "
        "finish all project and governance artifacts under the standard budget."
    )
    proof = (
        "Release 0.0.1 succeeds when the accepted first path is complete, reviewable, and blocked when required. "
        "The product shows the workspace result, handles missing or invalid input with a clear blocker, and keeps "
        "replayable evidence for review."
    )

    model = first_path_model(first_path)
    candidate = select_visible_result_candidate(first_path, proof_boundary=proof)

    assert is_requirement_control_step(
        "The request has specialist jargon and operational handoff, so the artifacts must stay readable without losing domain depth"
    )
    assert drop_requirement_control_steps(
        [
            "Sports medicine coordinator turns an ambiguous return-to-play case into a review-ready record",
            "The request has specialist jargon and operational handoff, so the artifacts must stay readable without losing domain depth",
            "An architect must see bounded components, state ownership, events, and projection boundaries",
            "The post-confirm create must finish all project and governance artifacts under the standard budget",
        ]
    ) == ["Sports medicine coordinator turns an ambiguous return-to-play case into a review-ready record"]
    assert "must stay readable" not in " ".join(model.steps).casefold()
    assert "post-confirm create" not in " ".join(model.steps).casefold()
    assert model.visible_outcome == "A final return recommendation"
    assert candidate.source_kind == "first_path_event"
    assert candidate.source_path == "first_path.visible_result"
    assert candidate.text == "a final return recommendation"
    assert "specialist jargon" not in candidate.text.casefold()


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


def test_semantic_compiler_rejects_poisoned_rendered_projection_surfaces() -> None:
    proposal = _minimal_lifecycle_proposal()
    proof = proposal["intent"]["proof_boundary"]
    poison = f"Operators should trust the visible result produced by {proof}."
    proposal["project_brief"]["project_outcome"] = poison
    proposal["accepted_project"] = {"summary": poison}
    proposal["project_dashboard"] = {"status": {"headline": poison}}

    failed = compile_greenfield_semantics(proposal)

    assert failed.status == "failed"
    paths = {item.path for item in failed.counterexamples}
    assert "project_brief.project_outcome" in paths
    assert "accepted_project.summary" in paths
    assert "project_dashboard.status.headline" in paths

    assert repair_greenfield_semantic_projections(proposal) is True
    assert "visible result produced by" not in json.dumps(proposal["project_brief"]).casefold()


def test_semantic_compiler_rejects_paraphrased_proof_poisoned_projection_surfaces() -> None:
    proposal = _minimal_lifecycle_proposal()
    poison = "Operators use the same event settled into a finished result proven by release evidence to decide the next action."
    proposal["intent"]["product_view"] = poison
    proposal["backlog"][0]["opportunity"] = poison

    failed = compile_greenfield_semantics(proposal)

    assert failed.status == "failed"
    paths = {item.path for item in failed.counterexamples}
    assert "intent.product_view" in paths
    assert "backlog.0.opportunity" in paths


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


def test_apply_semantic_input_records_source_paths_and_semantic_visibility_fallback() -> None:
    proposal = {
        "intent": {
            "title": "Claims Desk",
            "state_object": "Claim packet",
            "first_path": "An analyst enters claim details and links evidence",
            "proof_boundary": "Release 0.0.1 is proven when the assigned claim packet is reviewable.",
        },
        "project_brief": {"first_path": "This fallback should not win."},
        "backlog": [{"recommended_first_slice": "This fallback should also not win."}],
    }
    compiler_input = greenfield_apply_semantic_input(proposal)
    source_paths = dict(compiler_input.source_paths)

    assert compiler_input.schema_version == APPLY_SEMANTIC_INPUT_VERSION
    assert compiler_input.first_path.endswith("The product shows the accepted result for review.")
    assert "then shows the accepted result" not in compiler_input.first_path
    assert source_paths["first_path"] == "intent.first_path+semantic_visible_result_fallback"
    assert source_paths["proof_boundary"] == "intent.proof_boundary"

    ensured = ensure_apply_semantic_model(proposal)
    persisted_input = ensured["apply_semantic_input"]

    assert persisted_input["schema_version"] == APPLY_SEMANTIC_INPUT_VERSION
    assert persisted_input["first_path"].endswith("The product shows the accepted result for review.")
    assert "then shows the accepted result" not in persisted_input["first_path"]
    assert persisted_input["source_paths"]["first_path"] == "intent.first_path+semantic_visible_result_fallback"


def test_apply_semantic_input_trusts_terminal_first_path_event_visible_result() -> None:
    proposal = {
        "intent": {
            "title": "Disclosure Council",
            "state_object": "Report",
            "first_path": "Reporter submits a report; owner reviews it; council publishes proof.",
            "proof_boundary": "Evidence custody and embargo decision.",
        },
    }

    compiler_input = greenfield_apply_semantic_input(proposal)
    ensured = ensure_apply_semantic_model(proposal, refresh=True)

    assert compiler_input.first_path == "Reporter submits a report; owner reviews it; council publishes proof."
    assert dict(compiler_input.source_paths)["first_path"] == "intent.first_path"
    assert ensured["semantic_model"]["first_path_contract"]["visible_result"] == "published proof"


def test_apply_semantic_accepts_first_path_event_visible_result_below_proof_boundary_floor(monkeypatch) -> None:
    def semantic_candidate(value: Any, *, proof_boundary: Any = "", **_kwargs: Any) -> GreenfieldSemanticCandidate:
        return GreenfieldSemanticCandidate(
            role="visible_result",
            text="accepted outcome, review status, proof notes, owner decision trail, and evidence state",
            source_kind="first_path_event",
            source_path="first_path.visible_result",
            confidence=0.83,
            provenance=(str(value), str(proof_boundary)),
        )

    monkeypatch.setattr(greenfield_apply_semantic, "select_visible_result_candidate", semantic_candidate)
    proposal = {
        "intent": {
            "title": "Review Workspace",
            "state_object": "Review record",
            "first_path": "Operators collect accepted inputs and review the accepted outcome.",
            "proof_boundary": "Release 0.0.1 is proven when the accepted outcome is reviewable.",
        },
    }

    ensured = greenfield_apply_semantic.ensure_apply_semantic_model(proposal, refresh=True)
    persisted_input = ensured["apply_semantic_input"]

    assert persisted_input["first_path"] == "Operators collect accepted inputs and review the accepted outcome."
    assert persisted_input["source_paths"]["first_path"] == "intent.first_path"


def test_apply_semantic_visibility_fallback_does_not_leave_trailing_comma_step() -> None:
    proposal = {
        "intent": {
            "title": "Checkout Recovery",
            "state_object": "Checkout recovery record",
            "proof_boundary": "Release 0.0.1 is proven when recovery evidence is reviewable.",
        },
        "backlog": [
            {
                "recommended_first_slice": "Start with checkout spine proof and failed-payment recovery.",
            }
        ],
    }

    ensured = ensure_apply_semantic_model(proposal)
    first_path = ensured["semantic_model"]["first_path_contract"]["events"][0]["text"]
    persisted_input = ensured["apply_semantic_input"]["first_path"]

    assert "recovery," not in first_path
    assert ",. Show" not in persisted_input
    assert "Start with checkout spine proof and failed-payment recovery" in persisted_input


def test_apply_semantic_input_is_persisted_when_semantic_model_already_exists() -> None:
    proposal = {
        "intent": {
            "title": "Claims Desk",
            "state_object": "Claim packet",
            "first_path": "An analyst reviews claim evidence and sees an accepted packet.",
            "proof_boundary": "Release proof shows the accepted packet is reviewable.",
        },
        "semantic_model": {"schema_version": "odylith.greenfield.semantic_model.v1"},
    }

    ensured = ensure_apply_semantic_model(proposal)

    assert ensured["semantic_model"] == {"schema_version": "odylith.greenfield.semantic_model.v1"}
    assert ensured["apply_semantic_input"]["schema_version"] == APPLY_SEMANTIC_INPUT_VERSION
    assert ensured["apply_semantic_input"]["source_paths"]["first_path"] == "intent.first_path"


def test_apply_semantic_bridge_uses_first_path_semantics_instead_of_local_visibility_regex() -> None:
    source = (DOMAIN_INTELLIGENCE / "greenfield_apply_semantic.py").read_text(encoding="utf-8")

    assert "import re" not in source
    assert "_VISIBLE_RESULT_RE" not in source
    assert "select_visible_result_candidate(" in source


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
