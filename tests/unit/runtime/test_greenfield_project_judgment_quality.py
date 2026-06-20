from __future__ import annotations

from odylith.runtime.artifact_quality.greenfield_project_judgment import greenfield_project_judgment_issues
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage


def _proposal(*, state_object: str = "A review record with owner, status, final outcome, and audit history.") -> dict[str, object]:
    return {
        "intent": {
            "title": "ReviewLedger",
            "state_object": state_object,
        },
        "components": [
            {"component_id": "review-record", "label": "Review Record Service"},
            {"component_id": "final-outcome", "label": "Final Outcome Review Service"},
        ],
        "semantic_model": {
            "first_path_contract": {
                "visible_result": "a published final outcome and audit history",
                "events": [
                    {"action": "opens", "text": "A reviewer opens a packet"},
                    {"action": "records", "text": "A reviewer records evidence"},
                    {"action": "approves", "text": "A reviewer approves the final outcome"},
                    {"action": "publishes", "text": "The product publishes a final outcome and audit history"},
                ],
            }
        },
    }


def test_project_judgment_rejects_casing_state_component_and_tail_drift() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(
            state_object="The product keeps a review record with owner, status, final outcome, and audit history."
        ),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The reviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final."
                ),
                "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet until the first outcome works.",
                "Confirm this as the versioned state object: the product keeps a review record with owner and status.",
            ]
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert "greenfield artifacts drift mixed-case source token `ReviewLedger` into `reviewLedger`" in issues
    assert (
        "greenfield artifacts should use state-object label `Review Record` instead of the raw tracking predicate"
        in issues
    )
    assert "greenfield project brief clips component label `Final Outcome Review Service` to `Final`" in issues
    assert "greenfield scope boundary truncates the accepted first-path tail" in issues


def test_project_judgment_rejects_managed_state_predicate_leak() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(
            state_object=(
                "The product manages a cooking run, including selected recipe, staged ingredients, "
                "sensor readings, safety stops, and final serve readiness."
            )
        ),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "Confirm this as the versioned state object: The product manages a cooking run, "
                    "including selected recipe, staged ingredients, sensor readings, safety stops, and final serve readiness."
                ),
            ]
        },
    )

    issues = greenfield_project_judgment_issues(package)

    assert "greenfield artifacts leak a product/system predicate instead of a state-object noun phrase" in issues
    assert "greenfield artifacts should use state-object label `Cooking Run` instead of the raw tracking predicate" in issues


def test_project_judgment_accepts_full_case_label_and_tail_coverage() -> None:
    package = GreenfieldCompletionPackage(
        proposal=_proposal(),
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final Outcome Review Service."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet, "
                    "recording evidence, approving the final outcome, and publishing the final outcome and audit history "
                    "until the first outcome works."
                ),
                "Confirm this as the versioned state object: review record with owner and status.",
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()


def test_project_judgment_treats_repeated_short_actions_as_tail_coverage() -> None:
    proposal = _proposal()
    proposal["semantic_model"] = {
        "first_path_contract": {
            "visible_result": "a simple trend over time",
            "events": [
                {"action": "records", "text": "A user records a first entry"},
                {"action": "logs", "text": "A user logs one action"},
                {"action": "log", "text": "The next day they log again"},
                {"action": "shows", "text": "The product shows a simple trend over time"},
            ],
        }
    }
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final Outcome Review Service."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond recording "
                    "a first entry, logging one action, logging again, and reviewing a simple trend over time "
                    "until the first outcome works."
                ),
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()


def test_project_judgment_requires_high_risk_assumptions_in_rendered_artifacts() -> None:
    proposal = _proposal()
    proposal["assumptions"] = [
        {
            "id": "ASM-001",
            "tier": "user_intent",
            "statement": "Reviewers are authorized staff only, not general public users.",
        }
    ]
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Review Record Service, Final Outcome Review Service."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet, "
                    "recording evidence, approving the final outcome, and publishing the final outcome and audit history "
                    "until the first outcome works."
                ),
            ]
        },
        backlog_result={"idea_files": {"IDEA.md": "Reviewers can publish a final outcome and audit history."}},
    )

    assert (
        "greenfield domain-expert lens omits accepted assumption `ASM-001` from generated artifacts"
        in greenfield_project_judgment_issues(package)
    )

    covered = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview=package.project_brief_preview,
        backlog_result={
            "idea_files": {
                "IDEA.md": "Authorized staff reviewers only can publish a final outcome; the general public is not a user."
            }
        },
    )

    assert greenfield_project_judgment_issues(covered) == ()


def test_project_judgment_allows_single_concept_component_label_without_service_suffix() -> None:
    proposal = _proposal()
    proposal["components"] = [
        {"component_id": "observability", "label": "Observability Service"},
        {"component_id": "pipeline", "label": "Pipeline Control Service"},
    ]
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        project_brief_preview={
            "coding_readiness_gates": [
                (
                    "The ReviewLedger components come from product systems named in the accepted product "
                    "direction: Observability, Pipeline Control."
                ),
                (
                    "Keep 0.0.1 to the accepted first path and non-goals: Do not expand beyond opening a packet, "
                    "recording evidence, approving the final outcome, and publishing the final outcome and audit history "
                    "until the first outcome works."
                ),
            ]
        },
    )

    assert greenfield_project_judgment_issues(package) == ()
