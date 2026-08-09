from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_visible_result_focus import focused_visible_result_object
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import domain_risk_for_row
from odylith.runtime.governance import artifact_tribunal

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_visible_result_object_stays_modal_safe_in_user_can_projection() -> None:
    action = outcome_action_phrase("an invoice anomaly review result with blockers and evidence for review")

    assert action == "review an invoice anomaly review result with blockers and evidence for review"
    assert generated_semantic_slop_issues(f"Result proof confirms the user can {action}.") == []


def test_article_led_blocked_result_stays_a_reviewable_noun_phrase() -> None:
    action = outcome_action_phrase("the blocked shipment until exceptions are approved")

    assert action == "see the blocked shipment until exceptions are approved"
    assert generated_semantic_slop_issues(f"Result proof confirms the user can {action}.") == []


def test_article_led_entities_do_not_inherit_the_blocked_result_rule() -> None:
    assert outcome_action_phrase("the approved vendor") == "reach the approved vendor"
    assert outcome_action_phrase("the confirmed reviewer") == "reach the confirmed reviewer"
    assert outcome_action_phrase("the verified owner") == "review the verified owner"


def test_open_source_product_noun_is_not_carried_as_the_article_an() -> None:
    steps = first_path_steps(
        "An open source security embargo room that receives vulnerability reports, coordinates maintainer triage, "
        "tracks affected package evidence, records disclosure approvals, and shows advisory readiness."
    )

    assert steps[1] == "Coordinate maintainer triage"
    assert all(not step.startswith("An coordinates") for step in steps)


def test_visible_result_focus_strips_non_goal_tails_from_result_identity() -> None:
    assert (
        focused_visible_result_object("the channel assignment plan without automating expert judgment")
        == "the channel assignment plan"
    )
    assert (
        focused_visible_result_object("a reviewable pattern summary without making diagnosis claims")
        == "a reviewable pattern summary"
    )


def test_comma_led_finite_outcome_stays_modal_safe_in_user_can_projection() -> None:
    action = outcome_action_phrase("submits, review notes, decision status, and release proof")

    assert action == "submit, review notes, decision status, and release proof"
    assert generated_semantic_slop_issues(f"Result proof confirms the user can {action}.") == []


def test_child_workstream_risk_projection_preserves_governed_risk_posture() -> None:
    proposal = {
        "intent": {
            "first_path": (
                "Editors collect source clips, assemble a review cut, record rights notes, "
                "and see a publish-ready review packet."
            ),
            "proof_boundary": "Proven when an editor can review a cut with rights notes and blocked publishing states visible.",
            "state_object": "Review packet with cut status, rights notes, blockers, and publish decision.",
        },
        "semantic_model": {"first_path_contract": {"visible_result": "a publish-ready review packet"}},
        "backlog": [
            {"title": "Prove one complete media review path"},
        ],
    }
    row = {
        "title": "Let Editor Assemble Review Cut",
        "problem": "Editors need the review cut, rights notes, and publish decision to stay understandable.",
        "customer": "Editors and release reviewers",
        "opportunity": "Build the narrow review-cut behavior that keeps publish readiness visible.",
        "product_view": "The slice is complete when an editor can assemble a review cut and see publish readiness.",
        "success_metrics": ["Success proof shows a review cut can be assembled.", "Blocked publish state is visible."],
        "security_posture": "Review security: only authorized editors can change private cut state, access decisions, and audit history.",
    }
    proposal["backlog"].append(row)

    risk = domain_risk_for_row(row, proposal)
    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="backlog",
        payload={**row, "risks": [risk], "domain_risk": risk},
    )

    assert risk.startswith("Risk:")
    assert decision.passed


def test_sequence_component_router_does_not_embed_vertical_keyword_tables() -> None:
    source = (
        REPO_ROOT / "src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py"
    ).read_text(encoding="utf-8")

    for token in (
        "adherence",
        "arrival",
        "departure",
        "discount",
        "dose",
        "dosing",
        "price",
        "pricing",
        "quote",
        "timetable",
        "vehicle",
    ):
        assert f'"{token}"' not in source
