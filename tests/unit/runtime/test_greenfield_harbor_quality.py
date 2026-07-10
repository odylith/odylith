from __future__ import annotations

from dataclasses import asdict
import json

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


HARBOR_CONFIRMED_INTENT_TEXT = """# Harbor Incident Coordination

## Product story
Harbor operations teams need one governed place to coordinate a fuel spill near a berth from first report through containment, reopening approval, closure, and follow-up. The product should preserve who reported the incident, what containment tasks were assigned, why the berth can reopen, and what unresolved follow-up remains.

## State object
The core state is an incident coordination record with location, severity, containment tasks, assignees, berth status, reopening approval, closure timeline, unresolved follow-up, evidence links, and review status.

## First complete path
A dispatcher opens a new incident for a fuel spill near a berth, records an approval for reopening the berth, and closes the incident with a timeline and unresolved follow-up list.

## Human actors
- Dispatcher who opens incidents and coordinates response handoffs
- Harbor supervisor who approves berth reopening and reviews closure evidence
- Response lead who updates containment task status
- Follow-up owner who takes unresolved actions after closure

## External systems
- Port operations schedule
- Environmental reporting inbox
- Berth access control feed

## Internal product systems
- Incident intake workspace
- Containment task tracker
- Reopening approval ledger
- Closure evidence timeline
- Follow-up register

## Critical assumptions
- The first release should prove one incident lifecycle before optimizing for real-time sensor feeds.
- Reopening approval must be explicit and traceable.
- Closure cannot hide unresolved follow-up.

## Ambiguities
- Whether environmental agency submission is required in the first release.
- Whether berth access control must be live or manually referenced.
- Whether follow-up ownership requires due dates in the first release.

## Proof boundary
Release 0.0.1 succeeds when one dispatcher can open the incident, record the reopening approval, close the incident with a timeline, and leave unresolved follow-up visible for review. Live sensor feeds, automatic agency filing, and access-control automation are out of scope for this first proof.
"""


def test_first_path_action_grammar_keeps_close_as_action() -> None:
    first_path = (
        "A dispatcher opens a new incident for a fuel spill near a berth, records an approval for reopening the berth, "
        "and closes the incident with a timeline and unresolved follow-up list."
    )

    assert first_path_steps(first_path) == (
        "A dispatcher opens a new incident for a fuel spill near a berth",
        "A dispatcher records an approval for reopening the berth",
        "A dispatcher closes the incident with a timeline and unresolved follow-up list",
    )
    assert (
        base_action_clause(
            "opens a new incident for a fuel spill near a berth, records an approval for reopening the berth, "
            "and closes the incident with a timeline and unresolved follow-up list"
        )
        == "open a new incident for a fuel spill near a berth, record an approval for reopening the berth, "
        "and close the incident with a timeline and unresolved follow-up list"
    )
    assert first_path_capability_phrase(first_path, max_fragments=7, limit=340) == (
        "open a new incident for a fuel spill near a berth, record an approval for reopening the berth, "
        "and close the incident with a timeline and unresolved follow-up list"
    )
    assert first_path_capability_phrase(first_path, gerund=True, max_fragments=7, limit=340) == (
        "opening a new incident for a fuel spill near a berth, recording an approval for reopening the berth, "
        "and closing the incident with a timeline and unresolved follow-up list"
    )


def test_harbor_prewrite_package_does_not_render_mixed_action_grammar(tmp_path, monkeypatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)
    prompt = "build a harbor incident coordination product"
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent_with_authority(HARBOR_CONFIRMED_INTENT_TEXT, prompt=prompt),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )

    report = build_greenfield_package_report(prewrite.package)
    rendered = json.dumps(asdict(prewrite.package), sort_keys=True, default=str).casefold()

    assert report.passed, "\n".join(report.issues)
    assert "using a dispatcher records" not in rendered
    assert "record an approval for reopening the berth and closes" not in rendered
    assert "recording an approval for reopening the berth and closes" not in rendered
    assert "review the berth" not in rendered
    assert "keep close incident complete timeline visible" not in rendered
    assert "record an approval for reopening the berth, and close the incident" in rendered
    assert "recording an approval for reopening the berth, and closing the incident" in rendered
