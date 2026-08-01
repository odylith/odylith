from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import (
    build_greenfield_completion_report,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_drift import (
    contrastive_domain_drift_issues,
    semantic_repetition_issues,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority


def test_confirmed_build_preserves_accepted_intent_evidence_for_post_confirm_gates(tmp_path):
    intent = parse_confirmed_intent_text(
        """
# Personal Progress Journal

## Product story
A private app helps people understand recurring daily patterns over time. It lets them record
entries, context, reminders, mood, sleep, and notes, then turns that history into trends they
can review or share with a coach.

## State object
The core state is a personal progress timeline: dated events, context notes, goals, reminders,
insights, and shareable summaries.

## First complete path
A user creates a private profile, sets their main goal, logs a few days of entries, reviews trend
summaries, sees possible pattern correlations, and exports a clear report for a coaching session.

## Human actors
- Person tracking progress
- Coach reviewing exported summaries
- Support/admin role for account and privacy operations

## External systems
- Mobile OS notifications for reminders
- Secure authentication provider
- Optional PDF or share-link export for reviewers

## Internal product systems
- Profile and consent settings
- Daily logging and timeline system
- Reminder and habit scheduler
- Pattern and correlation insight engine
- Report export system
- Privacy, audit, retention, and account controls
- Accessible mobile UI layer

## Critical assumptions
- This is a tracking product, not a professional authority.
- The first release prioritizes individual self-tracking over team workflows.
- Users need fast daily entry, not long forms.
- Insights should be framed as possible patterns, not confirmed causes.

## Ambiguities
- Whether coach accounts are needed in the first release.
- Whether reminders must use live mobile notifications in the first release.

## Proof boundary
The first proof should show that a real user can complete daily tracking with minimal friction,
review meaningful trends, and export a readable summary without the product making unsafe claims.
"""
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="build a personal progress journal",
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")
    rendered = str(proposal)

    assert report.passed
    assert "Mobile OS notifications for reminders" in proposal["intent"]["external_systems"]
    assert "personalized automation" not in rendered.casefold()
    assert contrastive_domain_drift_issues(proposal, proposal["semantic_model"]) == []
    assert semantic_repetition_issues(proposal) == []


def test_confirmed_build_repairs_role_only_actor_labels_before_quality_gate(tmp_path):
    intent = parse_confirmed_intent_text(
        """
# Agent Execution Control Room

## Product story
An operations team needs a governed control room for supervising autonomous work runs. The
product lets an operator define a run objective, approve boundaries, monitor execution steps,
capture evidence, pause risky activity, and produce an accountable review record after the run
finishes.

## State object
The core state is an execution run: objective, allowed actions, blocked actions, assigned agent,
live step log, evidence references, intervention decisions, risk flags, final outcome, and
post-run review notes.

## First complete path
An operator creates a run, defines allowed and blocked actions, starts the agent, watches live
steps, pauses one risky step, records the intervention decision, resumes or stops the run, and
exports a post-run review record.

## Human actors
- Operator supervising an execution run
- Reviewer approving high-risk boundaries
- Auditor inspecting evidence after completion

## External systems
- Identity provider for operator authentication
- Job runner that executes approved work
- Evidence storage for run artifacts

## Internal product systems
- Run intake and boundary approval
- Live execution timeline
- Intervention and pause controls
- Evidence capture and review package
- Audit-ready post-run report

## Critical assumptions
- Operators need control and accountability, not uncontrolled automation.
- The first release focuses on one governed execution lane.
- Every intervention needs a reason and timestamp.

## Ambiguities
- Whether approval is synchronous or asynchronous.
- Which job runner is the first integration.

## Proof boundary
The first proof should show that an operator can define a run, supervise live progress, intervene
on a risky step, and produce an accountable review record with evidence and decisions.
"""
    )

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="create an agent execution control room",
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )

    rendered = str(proposal)
    assert "Agent execution operator: supervising an execution run" in rendered
    assert "High-risk boundaries reviewer: approving high-risk boundaries" in rendered
    assert proposal["intent"]["human_actors"][0] == "Agent execution operator: supervising an execution run"
    assert "customer': 'Operator'" not in rendered
    assert "['Operator']" not in rendered
