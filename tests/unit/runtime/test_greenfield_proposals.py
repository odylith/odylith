from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path

import pytest

from odylith.runtime.common import mermaid_text
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import PROJECT_INTELLIGENCE_LAYERS
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import build_traceability_graph
from odylith.runtime.governance import release_planning_view_model
from odylith.runtime.project_intelligence import builder as project_intelligence_builder
from odylith.runtime.project_intelligence import greenfield as project_intelligence_greenfield
from odylith.runtime.project_intelligence import presenter as project_intelligence_presenter


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


CONFIRMED_INTENT_TEXT = """Municipal Permit Review Workspace — Product Intent Confirmation

Product story
A city permitting team uses the Municipal Permit Review Workspace to review building permit submissions without losing the connection between applicant documents, zoning checks, reviewer comments, and approval decisions. The product gives permit coordinators and reviewers one place to see what was submitted, what changed, which checks passed, and why a permit is ready, blocked, or rejected.

State object that changes through the first journey
A Permit Review File tracks the permit application, submitted documents, zoning status, reviewer comments, applicant revisions, decision state, and evidence that supports each approval or rejection.

First complete path the product should prove before broader scope
A permit coordinator imports one permit application, a zoning reviewer records a zoning check, the applicant submits one revision, and a supervisor reviews the decision package with traceable documents, comments, checks, and final status.

Human actors
- Permit coordinator — intakes applications and keeps review work moving.
- Zoning reviewer — evaluates parcel, use, setback, and code-check evidence.
- Applicant — submits documents and revisions.
- Review supervisor — approves, blocks, or rejects a decision package.

External systems
- Document intake portal — supplies application packets and revision uploads.
- Parcel zoning data — supplies zoning district, parcel attributes, and rule references.
- Payment ledger — supplies fee status without owning review decisions.

Internal product systems
- Permit file registry — owns permit identity, applicant metadata, submitted documents, and decision state.
- Zoning check ledger — records zoning checks, reviewer comments, rule references, and pass or block outcomes.
- Revision tracker — links applicant revisions to the documents and checks they are meant to address.
- Decision package review — assembles evidence, reviewer notes, unresolved blockers, and final approval state.

Critical assumptions
- Release 0.0.1 is an internal reviewer workspace, not a public application portal.
- Payment status can be referenced but does not decide review readiness.
- Review evidence must remain understandable to permitting staff and applicants.

Ambiguities that would change the first path
1. Does the first release need applicant self-service, or only internal staff review?
2. Are zoning rules imported from a live GIS source, or referenced manually by reviewers?
3. Does final approval require one supervisor or multiple department sign-offs?

Proof boundary
Release 0.0.1 succeeds when a supervisor can inspect one permit review file, see the active submitted documents, zoning check result, applicant revision, reviewer comments, unresolved blockers, and final decision state, and trace every decision back to source documents and reviewer evidence.
"""


def test_confirmed_greenfield_diagrams_use_compact_atlas_narration() -> None:
    first_path = (
        "The first complete path the product must prove is the solo monophonic instrument single take, offline analysis "
        "flow: 1. User opens LiveScore and taps Record. 2. User plays a roughly 30-second monophonic line. "
        "3. User taps Stop. 4. The app shows a rendered score and offers downloadable PDF and MusicXML."
    )
    proof_boundary = (
        "What would count as evidence the wedge works: a recorded solo monophonic take of roughly 30 seconds, played by "
        "a real musician, where the rendered score matches the played pitches and rhythms. What must not be claimed yet: "
        "polyphony, noisy stages, or real-time engraving."
    )
    rows = confirmed_diagrams(
        label="LiveScore: Live Performance",
        diagram_slugs={
            "context": "livescore-context",
            "sequence": "livescore-sequence",
            "state_evidence": "livescore-state-evidence",
            "component_boundaries": "livescore-component-boundaries",
            "ownership": "livescore-ownership",
            "proof_review": "livescore-proof-review",
        },
        components=[
            {
                "component_id": "audio",
                "label": "Audio Capture and Pre-processing Service",
                "responsibility": "Audio capture and pre-processing owns microphone or line-in capture and normalization.",
            },
            {
                "component_id": "pitch",
                "label": "Pitch and Onset Detection Engine",
                "responsibility": "Pitch and onset detection engine performs frame-level pitch tracking.",
            },
            {
                "component_id": "score",
                "label": "Score Renderer Service",
                "responsibility": "Score renderer owns engraves the score model to PDF and MusicXML.",
            },
        ],
        first_path=first_path,
        proof_boundary=proof_boundary,
        state_object="A Take moves from recorded audio to a rendered score with reviewable state.",
        evidence_record="A take evidence packet links audio input, detected notes, score output, and review result.",
        human_actors=["Solo performer (primary): the musician who plays the take."],
        external_systems=["Operating system audio input"],
        internal_systems=["Audio capture", "Pitch detection", "Score rendering"],
        non_goals=["Real-time engraving remains outside the first release."],
    )
    sequence = next(row for row in rows if row["title"] == "First Path Sequence")
    state_evidence = next(row for row in rows if row["title"] == "State and Evidence View")
    boundary = next(row for row in rows if row["title"] == "Component Boundary View")
    ownership = next(row for row in rows if row["title"] == "Ownership and Proof View")
    proof_review = next(row for row in rows if row["title"] == "Release Proof Review")
    copy = json.dumps(rows)

    assert len(rows) == 6
    assert "Walk the accepted first path" not in copy
    assert "participant C1 as Audio Capture and<br/>Pre-processing Service" in sequence["mermaid_source"]
    assert "pass state and evidence" in sequence["mermaid_source"]
    assert "show state, evidence, and blockers" in sequence["mermaid_source"]
    assert "<br/>" in sequence["mermaid_source"]
    assert "**" not in sequence["mermaid_source"]
    assert "The first complete path" not in sequence["mermaid_source"]
    assert "component cards to decode" not in copy
    assert "User opens LiveScore" not in sequence["summary"]
    assert "This sequence shows what the first release must prove from Solo performer (primary)" in sequence["summary"]
    assert "solo monophonic instrument single take" in sequence["summary"]
    assert sequence["read_guide"].startswith("Start with the user action.")
    assert "component handoff" not in sequence["read_guide"]
    assert "component; messages are calls" not in sequence["read_guide"]
    assert "State object" in state_evidence["mermaid_source"]
    assert "Evidence record" in state_evidence["mermaid_source"]
    assert "release boundary" in boundary["mermaid_source"]
    assert ownership["summary"].startswith("Trace release ownership")
    assert "polyphony" not in ownership["summary"]
    assert proof_review["summary"].startswith("Show the review path")
    assert "Outside release" in proof_review["mermaid_source"]
    for row in rows:
        if row["kind"] == "flowchart":
            assert "classDef" in row["mermaid_source"]
    for component in sequence["components"]:
        description = component["description"]
        assert "User opens LiveScore" not in description
        assert "What would count as evidence" not in description
        assert "For the first release" not in description
        assert "owns owns" not in description
        assert len(description) < 260
    assert [row["description"] for row in sequence["components"]] == [
        "Owns microphone or line-in capture and normalization.",
        "Owns frame-level pitch tracking.",
        "Owns engraving of the score model to PDF and MusicXML.",
    ]


def test_mermaid_text_normalizes_sequence_labels_notes_and_messages() -> None:
    source = "\n".join(
        [
            "sequenceDiagram",
            "  %% comment: keep **markers** and semicolon; untouched",
            "  participant A as **Account owner**",
            "  participant C1 as Transaction Ingestion and Normalization Adapter",
            (
                "  A->>C1: this is a very long message label with semicolon; and enough words "
                "that it should wrap inside the diagram lane instead of stretching the canvas"
            ),
            (
                "  Note over A,C1: **This note carries a very long accepted path explanation that "
                "previously leaked outside the sequence note box and made the diagram unreadable for normal people.**"
            ),
        ]
    )

    normalized = mermaid_text.normalize_mermaid_source(source)

    assert "**" not in normalized
    assert "participant A as Account owner" in normalized
    assert "participant C1 as Transaction Ingestion<br/>and Normalization<br/>Adapter" in normalized
    assert "A->>C1: this is a very long message<br/>label with semicolon, and…" in normalized
    assert "Note over A,C1: This note carries a very long<br/>accepted path explanation that<br/>previously leaked outside the…" in normalized


def test_confirmed_greenfield_create_handles_generic_reviewer_and_action_systems(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """Volunteer Equipment Checkout Tracker — Product Intent Confirmation

Product story
A community group needs one reliable place to track shared equipment, who has it, when it is due back, and whether it is safe to lend again. The product helps coordinators avoid lost items, double bookings, and unclear responsibility by turning checkout requests, item condition checks, and returns into one auditable record.

State object that changes through the first journey
An Equipment Item moves from available to reserved to checked out to returned pending inspection to available again, with a condition note and responsible borrower attached to each transition.

First complete path Odylith should prove before broader scope
A coordinator registers one item, a borrower requests it for a date range, the coordinator approves checkout, the borrower returns it, and the coordinator records a return condition so the item can be made available again.

Human actors
- Coordinator — owns the inventory, approves checkouts, and records return condition.
- Borrower — requests equipment, receives checkout approval, and returns the item.
- Reviewer — checks whether the record explains who had the item, when it changed hands, and what condition it returned in.

External systems
- Identity provider for coordinator and borrower sign-in.
- Email or SMS notification channel for checkout reminders, later wave only.

Internal product systems
- Item registry — records equipment identity, ownership, availability status, and condition baseline.
- Checkout request log — captures borrower, requested date range, purpose, and approval status.
- Approval workflow — records coordinator approval or rejection before an item leaves inventory.
- Availability view — shows which items can be borrowed now and why unavailable items are blocked.
- Return inspection record — captures returned condition, damage notes, and whether the item can be lent again.
- Audit trail — records state changes, actor, timestamp, and source for reviewer traceability.

Critical assumptions
- One organization owns the inventory in the first release.
- Payments, deposits, barcode scanning, and multi-location routing are out of scope for release 0.0.1.
- The first proof uses seeded data and does not claim live integrations.

Ambiguities that would change the first path
- Whether borrowers can self-serve approvals or every checkout needs coordinator review.
- Whether item condition needs photos in the first release.
- Whether overdue notifications are required before the first release.

Proof boundary
Release 0.0.1 succeeds when a reviewer can follow one item through registration, reservation, approved checkout, return, condition inspection, and availability restoration without losing the responsible actor, date range, item state, or audit record.
""",
        prompt="Draft a product-first greenfield proposal for a volunteer equipment checkout tracker",
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for a volunteer equipment checkout tracker",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    encoded = json.dumps(proposal)

    assert "Reviewer —" not in encoded
    assert "Volunteer Equipment Checkout reviewer" in encoded
    assert "owns captures" not in encoded
    assert "owns shows" not in encoded
    assert "visibility into which items can be borrowed now" in encoded
    context = next(row for row in proposal["diagrams"] if row["title"] == "System Context View")
    assert "<br/>" in context["mermaid_source"]
    for row in proposal["diagrams"]:
        for component in row["components"]:
            assert component["description"].startswith("Owns ")


def _confirmed_intent() -> dict[str, object]:
    return parse_confirmed_intent_text(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )


def _write_confirmed_intent(repo_root: Path) -> Path:
    path = repo_root / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    _write(path, CONFIRMED_INTENT_TEXT)
    return path


def test_confirmed_intent_parser_keeps_ambiguities_out_of_first_path() -> None:
    intent = _confirmed_intent()

    assert "Does the first release need applicant self-service" not in str(intent["first_path"])
    assert intent["first_path"].endswith("final status.")
    assert intent["ambiguities"] == [
        "Does the first release need applicant self-service, or only internal staff review?",
        "Are zoning rules imported from a live GIS source, or referenced manually by reviewers?",
        "Does final approval require one supervisor or multiple department sign-offs?",
    ]


def test_confirmed_intent_parser_allows_hyphenated_domain_workflow_phrases() -> None:
    text = CONFIRMED_INTENT_TEXT.replace(
        "A permit coordinator imports one permit application, a zoning reviewer records a zoning check, "
        "the applicant submits one revision, and a supervisor reviews the decision package with traceable "
        "documents, comments, checks, and final status.",
        "A permit coordinator uses a mobile-first workflow to import one permit application, a zoning "
        "reviewer records a zoning check, the applicant submits one revision, and a supervisor reviews "
        "the decision package with traceable documents, comments, checks, and final status.",
    )

    intent = parse_confirmed_intent_text(
        text,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )

    assert "mobile-first workflow" in str(intent["first_path"])


def test_confirmed_intent_parser_strips_markdown_emphasis_from_actor_rows() -> None:
    intent = parse_confirmed_intent_text(
        """Account Cleanup — Product Intent Confirmation

Product story
The account owner uses the account cleanup product to find recurring charges they no longer need, understand why each charge is being shown, and cancel one subscription without losing services they still use. The product connects transaction ingestion, recurring-charge detection, user review, and cancellation tracking so the account owner and support reviewer can see what changed and why.

State object that changes through the first journey
A cleanup review tracks transaction history, recurring-charge candidates, user approval, cancellation attempt state, and the next billing-cycle check.

First complete path the product should prove before broader scope
The user imports transaction history, reviews one likely subscription, approves a cancellation attempt, records the outcome, and checks whether the next billing cycle stopped.

Human actors
- **Account owner:** wants to reduce waste without accidentally losing important services.
- **Support reviewer:** checks ambiguous cancellation attempts and user disputes.

External systems
- Bank or card transaction history.
- Merchant cancellation portal or support inbox.

Internal product systems
- Transaction ingestion — imports financial activity and normalizes merchant, date, amount, and account source so cleanup evidence starts from a consistent transaction record.
- Recurring-charge detection — identifies likely subscriptions from repeated charges, merchant cadence, amount patterns, and known billing descriptors while keeping uncertainty visible.
- User review flow — explains evidence to the account owner, captures keep/cancel approval, and prevents cancellation without an explicit user decision.
- Cancellation tracker — records the unsubscribe attempt, merchant response, support reviewer escalation, and follow-up billing status for the next cycle.

Critical assumptions
- Release 0.0.1 guides or records one cancellation path; it does not claim universal automated cancellation.

Ambiguities that would change the first path
- Whether transaction import comes from a live connection or a CSV file.

Proof boundary
Release 0.0.1 succeeds when a reviewer can see the imported transactions, the recurring-charge evidence, the user approval, the cancellation outcome, and the next billing-cycle check.
""",
        prompt="Draft a product-first greenfield proposal for account cleanup.",
    )

    encoded = json.dumps(intent)
    assert "**" not in encoded
    assert "Account owner: wants to reduce waste" in encoded
    assert "Support reviewer: checks ambiguous cancellation attempts" in encoded


def test_confirmed_intent_parser_accepts_internal_external_heading_and_prose_systems() -> None:
    intent = parse_confirmed_intent_text(
        """# Product Intent Confirmation

	Product title:
	Low-Cost Field Water Quality Monitor

	Product story:
	The product is a compact low-cost field water-quality monitor for community groups that need quick local screening before sending samples to a lab. It captures pH, turbidity, temperature, and conductivity readings, guides a non-specialist through calibration, and produces a readable result that explains whether the sample is safe, uncertain, or needs lab review. The value is practical screening without turning the device into a professional laboratory instrument.

	State object that changes through the first journey:
	The primary state object is the water sample assessment. An assessment starts as prepared, tracks calibration state, sample source, readings, confidence bands, battery level, contamination warnings, and reviewer notes, then ends as passed, flagged for retest, escalated to lab review, or safely discarded.

	First complete path the product should prove before broader scope:
	A field volunteer powers on the device, confirms calibration, collects one water sample, records the sample location and source, runs the sensor reading, sees a safe-or-review result, and exports a clear sample assessment with readings, calibration evidence, and next action.

	Main human actors:
	- Field volunteer who collects samples and needs simple prompts, calibration feedback, and a readable result.
	- Program coordinator who reviews sample trends and decides which sites need lab follow-up.
	- Lab reviewer who receives escalated samples and checks whether field evidence is complete enough to trust.

	External systems separated from internal product systems:
	- Water sources, sample containers, calibration solution, and field conditions.
	- Optional lab information system used for escalated samples.

	Internal systems separated from external systems:
	The internal product systems combine a sampling probe and a low-cost sensor board and a calibration controller and a battery enclosure module and a result display and an assessment recorder and a safety cleanup checklist into one portable screening device. These internal systems matter because the product must stay inexpensive and field-ready while still producing trustworthy readings, calibration evidence, contamination handling, runtime status, and clear escalation behavior for the first screening path.

	Critical assumptions:
	- Low cost means community-affordable and bill-of-materials conscious, not laboratory-grade.
	- Field screening means triage evidence only; certified water-safety decisions stay with lab or regulatory review.

	Ambiguities that materially change the proposal:
	- Which measurements belong in release 0.0.1 versus later sensor expansion.
	- Whether sample records stay local-only or sync to a coordinator dashboard.

	Proof boundary:
	Evidence should come from a bench test or field trial showing calibration, sample reading stability, result explanation, battery behavior, and safe cleanup handling. Until then, the product must not claim regulatory certification, laboratory accuracy, contamination-safe handling for every sample type, or reliable operation across all field conditions.
	""",
        prompt="Draft a product-first greenfield proposal for a low-cost field water quality monitor.",
    )

    assert intent["title"] == "Low-Cost Field Water Quality Monitor"
    assert "Water sources" in intent["external_systems"][0]
    internal_systems = intent["internal_systems"]
    assert len(internal_systems) >= 6
    assert any("Calibration Controller" in row for row in internal_systems)
    assert any("Battery Enclosure Module — Owns battery enclosure module. Relevant behavior" in row for row in internal_systems)
    assert any("battery level" in row for row in internal_systems)
    assert not any("Owns the accepted" in row for row in internal_systems)
    assert all("—" in row for row in internal_systems)
    assert not any("External systems" in row for row in internal_systems)


def test_confirmed_intent_rejects_meta_scaffold_instead_of_product_story() -> None:
    bad_intent = """Community Archive — Product Intent Confirmation

Product story
Turn the community archive intent into a clear product narrative, first workflow, state object, and proof boundary before implementation begins. Release 0.0.1 narrows that promise to one first slice and keeps the project readable as one product story.

State object that changes through the first journey
A Community Archive state record stores the workflow result, owner, validation output, reviewer decision, and evidence packet so the release claim can be trusted later.

First complete path the product should prove before broader scope
Start with the community archive first workflow, then replay community archive record and review community archive evidence packet before source work starts.

Human actors
- Community Archive workflow lead and beneficiary — prove one journey from intake to visible completion.
- Community Archive proof lead — decides whether evidence is strong enough to trust the release claim.

Internal product systems
- Community Archive Workflow Service — owns the first workflow.
- Community Archive State Store — owns the state record.
- Community Archive Evidence Review — owns the evidence packet.

Proof boundary
The community archive first workflow passes end to end with fixture-backed inputs and documented non-goals, and every release claim maps to state, validation output, reviewer decision, and evidence packet.
"""

    with pytest.raises(ValueError, match="missing or too thin"):
        parse_confirmed_intent_text(bad_intent, prompt="Create a community archive")


def _ontology_term_labels(rows: object) -> list[str]:
    values = rows if isinstance(rows, list) else []
    labels: list[str] = []
    for row in values:
        text = str(row or "").strip()
        if not text:
            continue
        labels.append(text.split(":", 1)[0].strip().casefold())
    return labels


def _seed_empty_governance_repo(repo_root: Path) -> None:
    empty_backlog_table = (
        "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
    )
    _write(
        repo_root / "odylith/radar/source/INDEX.md",
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-05-03\n\n"
            "## Ranked Active Backlog\n\n"
            f"{empty_backlog_table}"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            f"{empty_backlog_table}"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            f"{empty_backlog_table}"
            "## Reorder Rationale Log\n\n"
        ),
    )
    (repo_root / "odylith/radar/source/ideas").mkdir(parents=True, exist_ok=True)
    _write(
        repo_root / "odylith/atlas/source/catalog/diagrams.v1.json",
        json.dumps({"schema_version": "odylith.diagrams.v1", "diagrams": []}, indent=2) + "\n",
    )


def _apply_ready_greenfield_fixture(repo_root: Path, prompt: str) -> dict[str, object]:
    _ = repo_root
    proposal = copy.deepcopy(_host_reasoned_ecommerce_proposal())
    title = " ".join(part[:1].upper() + part[1:] for part in greenfield_proposals.slugify(prompt).split("-"))
    title = title or "Host Authored Greenfield Project"
    slug = greenfield_proposals.slugify(title)
    intent = proposal["intent"]
    assert isinstance(intent, dict)
    intent.update({"prompt": prompt, "title": title, "project_slug": slug})
    proposal["project_brief"] = _host_project_brief(title=title, prompt=prompt, release="0.0.1")
    proposal["project_intelligence"] = _host_project_intelligence(title=title, release="0.0.1")
    release_focus = _host_release_focus_for_prompt(prompt)
    release_plan = proposal.get("release_plan")
    if isinstance(release_plan, dict):
        release_plan.update(
            {
                "label": f"{title} first governed release",
                "provisional_release_id": f"release-{slug}-first",
                "strategy": f"Promote the {release_focus} only after validation proof and refreshed release evidence.",
            }
        )
        milestones = release_plan.get("milestones")
        if isinstance(milestones, list):
            for milestone in milestones:
                if isinstance(milestone, dict):
                    milestone["exit_criteria"] = (
                        f"The named product operator accepts the {release_focus}, components, topology, and validation."
                    )
    backlog = proposal.get("backlog")
    if isinstance(backlog, list):
        actor_lines = _host_actor_lines_for_prompt(prompt)
        for row in backlog:
            if isinstance(row, dict):
                row["domain_intelligence"] = _host_domain_intelligence(
                    title=title,
                    row_title=str(row.get("title") or title),
                    actors=actor_lines,
                )
    return greenfield_proposals.normalize_host_reasoned_proposal(proposal)


def _host_reasoned_ecommerce_proposal() -> dict[str, object]:
    proposal: dict[str, object] = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "proposal_first_confirm_before_apply",
        "intent": {
            "prompt": "Build an ecommerce site",
            "title": "Commerce Launch System",
            "project_slug": "commerce-launch-system",
            "reasoning_mode": "host_model_reasoned",
            "evidence_tier": "user_intent",
        },
        "observed_source": {"source_posture": "empty_or_no_app_source"},
        "assumptions": [
            "The first slice should prove browse-to-checkout without claiming payment production readiness.",
            "Inventory, payment, and order state remain separate until source evidence says otherwise.",
        ],
        "open_questions": [
            "Which stack owns the storefront?",
            "Which payment provider or sandbox should shape the first proof?",
        ],
        "risks": [
            "Combining cart, payment, and order state would hide failure recovery.",
        ],
        "security_compliance": {
            "domain": "Ecommerce checkout domain with payment sandbox, order, inventory, and shopper data risk.",
            "security": "Security posture covers payment handoff, session access, retry abuse, and idempotent order recovery.",
            "policy": "Compliance posture keeps PCI/provider policy, privacy, auditability, and accessibility explicit before production payment claims.",
        },
        "validation_strategy": [
            "Checkout happy path and payment failure recovery must both pass.",
            "Order creation must be idempotent under retry and webhook replay.",
        ],
        "program": {
            "shape": "program_with_waves",
            "wave_count": 4,
            "recommended_first_wave": "Checkout spine",
            "blueprint": {
                "program_type": "greenfield_program",
                "parent_workstream": "Govern Commerce Launch System",
                "child_workstream_strategy": "Create child boundaries for storefront, catalog, checkout, and order reliability.",
                "child_workstreams": ["Define Storefront boundary", "Define Checkout boundary"],
                "wave_to_workstream_policy": "Waves are delivery checkpoints; workstreams remain user_intent until source evidence exists.",
                "release_strategy": "Target the accepted first checkout slice to the provisional 0.0.1 release.",
                "recommended_wave_order": ["Checkout spine", "Catalog integrity", "Payment recovery", "Operational hardening"],
                "evidence_tier": "odylith_assumption",
            },
            "waves": [
                {
                    "wave": 1,
                    "label": "Checkout spine",
                    "goal": "Prove browse, cart, checkout handoff, and order draft.",
                    "validation": "Browser proof covers happy path and failed payment recovery.",
                    "workstream_titles": ["Define Storefront boundary"],
                    "component_focus": ["commerce-storefront", "commerce-checkout"],
                    "evidence_tier": "odylith_assumption",
                },
                {
                    "wave": 2,
                    "label": "Catalog integrity",
                    "goal": "Make product, price, inventory, and merchandising reviewable.",
                    "validation": "Price and inventory snapshot rules are explicit.",
                    "workstream_titles": ["Define Catalog boundary"],
                    "component_focus": ["commerce-catalog"],
                    "evidence_tier": "odylith_assumption",
                },
            ],
        },
        "release_plan": {
            "selector": "0.0.1",
            "label": "First governed commerce release",
            "provisional_release_id": "release-commerce-launch-first",
            "strategy": "Promote only after checkout validation and refreshed release evidence.",
            "release_stages": [
                {"stage": "wave-1", "label": "Checkout spine", "release_gate": "Browser and recovery proof pass."},
            ],
            "target_workstream_titles": ["Define Storefront boundary"],
            "milestones": [
                {
                    "name": "Proposal accepted",
                    "exit_criteria": "The commerce operator accepts assumptions, first slice, components, topology, and validation.",
                }
            ],
            "evidence_tier": "odylith_assumption",
        },
        "backlog": [
            {
                "title": "Govern Commerce Launch System",
                "problem": "Commerce builders launching an ecommerce site and shoppers cannot trust checkout until browse, cart, payment handoff, order draft, and recovery evidence are separated.",
                "customer": "Commerce builders and shoppers",
                "opportunity": "Let commerce builders review one checkout-first path with explicit recovery gates before source work expands.",
                "product_view": "Commerce Launch System should let shoppers browse, enter a cart, attempt checkout, and see recoverable payment failure while builders inspect the supporting state and evidence.",
                "success_metrics": [
                    "The checkout spine has a parent workstream and first child boundary.",
                    "Candidate components are user_intent until source evidence exists.",
                    "Architecture diagrams carry distinct system-context and program-wave drafts.",
                ],
                "priority": "P1",
                "sizing": "L",
                "complexity": "High",
                "recommended_first_slice": "Start with checkout spine proof and failed-payment recovery.",
                "evidence_tier": "user_intent",
            },
            {
                "title": "Define Storefront boundary",
                "problem": "The user-facing browse and checkout UI needs a named owner before implementation.",
                "customer": "Shoppers and commerce builders",
                "opportunity": "Keep storefront behavior independently reviewable and testable.",
                "product_view": "Storefront should own browse, cart entry, checkout entry, and user-visible errors.",
                "success_metrics": [
                    "Storefront appears in component specs and architecture diagrams with user_intent evidence.",
                    "Browse-to-cart entry has a first-slice validation gate before implementation.",
                ],
                "priority": "P1",
                "sizing": "M",
                "complexity": "Medium",
                "recommended_first_slice": "Define the checkout route and state contract for browse-to-cart.",
                "component_focus": ["commerce-storefront", "commerce-checkout"],
                "related_diagram_slugs": ["commerce-launch-system-context", "commerce-launch-program-waves"],
                "dependencies": [
                    "Depends on checkout handoff semantics and a catalog read model being explicit before source implementation.",
                ],
                "interfaces": [
                    "Defines browse, cart-entry, checkout-entry, and error-state contracts before code exists.",
                ],
                "validation": [
                    "Browser proof must cover browse-to-cart and failed-checkout messaging before implementation starts.",
                ],
                "evidence_tier": "user_intent",
            },
            {
                "title": "Define Catalog boundary",
                "problem": "Product, price, and inventory rules need a named owner before checkout can be evaluated honestly.",
                "customer": "Builders",
                "opportunity": "Keep product facts and inventory snapshots separate from checkout orchestration.",
                "product_view": "Catalog should own product reads, price snapshots, inventory visibility, and merchandising review boundaries.",
                "success_metrics": [
                    "Catalog appears in component specs and architecture diagrams with user_intent evidence.",
                    "Price and inventory snapshot rules have a first-slice validation gate.",
                ],
                "priority": "P1",
                "sizing": "M",
                "complexity": "Medium",
                "recommended_first_slice": "Define the product, price, and inventory snapshot contract.",
                "component_focus": ["commerce-catalog"],
                "related_diagram_slugs": ["commerce-launch-system-context", "commerce-launch-program-waves"],
                "dependencies": [
                    "Depends on source-backed implementation planning to choose the actual catalog storage boundary.",
                ],
                "interfaces": [
                    "Defines read-only product, price, and inventory snapshot interfaces for checkout.",
                ],
                "validation": [
                    "Contract proof must show checkout reads immutable price and inventory snapshots.",
                ],
                "evidence_tier": "user_intent",
            },
        ],
        "components": [
            {
                "component_id": "commerce-storefront",
                "label": "Storefront",
                "kind": "application",
                "intended_path": "apps/web",
                "responsibility": "Browse, cart entry, checkout entry, and user-facing errors.",
                "boundary": "Owns shopper-facing browse, cart-entry, checkout-entry, and user-visible error states.",
                "dependencies": ["Depends on catalog reads and checkout handoff contracts."],
                "interfaces": ["Browser routes, cart-entry command, checkout-entry command, and error presentation contract."],
                "validation": ["Browser smoke proof for browse-to-cart and failed-checkout messaging."],
                "workstream_titles": ["Define Storefront boundary"],
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            },
            {
                "component_id": "commerce-checkout",
                "label": "Checkout Orchestrator",
                "kind": "service",
                "intended_path": "src/checkout",
                "responsibility": "Payment handoff, order draft, idempotency, and recovery boundaries.",
                "boundary": "Owns checkout handoff, payment sandbox interaction, order draft creation, and retry recovery.",
                "dependencies": ["Depends on storefront checkout entry and catalog price snapshot reads."],
                "interfaces": ["Checkout command, payment provider sandbox adapter, order-draft writer, and retry contract."],
                "validation": ["Contract proof for idempotent order draft creation and failed payment recovery."],
                "workstream_titles": ["Define Storefront boundary"],
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            },
            {
                "component_id": "commerce-catalog",
                "label": "Catalog Boundary",
                "kind": "service",
                "intended_path": "src/catalog",
                "responsibility": "Product facts, price snapshots, inventory visibility, and merchandising review.",
                "boundary": "Owns product facts, price snapshots, inventory visibility, and merchandising review semantics.",
                "dependencies": ["No source dependency is claimed until implementation planning chooses storage."],
                "interfaces": ["Product-read query, price-snapshot query, and inventory-availability query."],
                "validation": ["Contract proof that checkout uses immutable price and inventory snapshots."],
                "workstream_titles": ["Define Catalog boundary"],
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            },
        ],
        "diagrams": [
            {
                "slug": "commerce-launch-system-context",
                "title": "System Context",
                "kind": "flowchart",
                "summary": "Show shopper, storefront, checkout, order, payment, and release-evidence boundaries.",
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": [
                    {
                        "name": "Storefront",
                        "description": "Owns shopper-facing browse, cart entry, checkout entry, and user-visible error evidence.",
                    },
                    {
                        "name": "Checkout Orchestrator",
                        "description": "Owns payment handoff, order draft creation, retry recovery, and validation evidence.",
                    },
                    {
                        "name": "Catalog Boundary",
                        "description": "Owns product facts, price snapshots, inventory visibility, and merchandising review evidence.",
                    },
                ],
                "related_workstream_titles": ["Govern Commerce Launch System", "Define Storefront boundary", "Define Catalog boundary"],
                "intended_paths": ["apps/web", "src/checkout"],
                "watch_paths": [],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "flowchart LR\n"
                    "    subgraph experience_lane[\"Experience lane\"]\n"
                    "      shopper[\"Shopper\"]\n"
                    "      storefront[\"Storefront UI\"]\n"
                    "    end\n"
                    "    subgraph transaction_lane[\"Transaction lane\"]\n"
                    "      checkout[\"Checkout<br/>orchestrator\"]\n"
                    "      payment[\"Payment sandbox\"]\n"
                    "      order[\"Order ledger\"]\n"
                    "    end\n"
                    "    subgraph evidence_lane[\"Evidence lane\"]\n"
                    "      evidence[\"Release<br/>evidence spine\"]\n"
                    "    end\n"
                    "    shopper --> storefront --> checkout\n"
                    "    checkout --> payment\n"
                    "    checkout --> order\n"
                    "    order --> evidence\n"
                    "    payment -. failure recovery .-> checkout\n"
                    "    classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;\n"
                    "    classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;\n"
                    "    classDef evidence fill:#F5F3FF,stroke:#DDD6FE,color:#17233A,stroke-width:1px;\n"
                    "    class shopper,storefront actor;\n"
                    "    class checkout,payment,order service;\n"
                    "    class evidence evidence;\n"
                    "    style experience_lane fill:#FBFDFF,stroke:#BFD7FE,stroke-width:1px,color:#334155\n"
                    "    style transaction_lane fill:#FBFDFF,stroke:#A7E9E3,stroke-width:1px,color:#334155\n"
                    "    style evidence_lane fill:#FBFDFF,stroke:#DDD6FE,stroke-width:1px,color:#334155\n"
                ),
            },
            {
                "slug": "commerce-launch-program-waves",
                "title": "Program Waves",
                "kind": "flowchart",
                "summary": "Show checkout spine, catalog integrity, payment recovery, and hardening waves.",
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": [
                    {"name": "Storefront", "description": "Owns browse-to-cart proof, shopper-facing route ownership, and error evidence."},
                    {"name": "Checkout Orchestrator", "description": "Payment recovery proof and order-state handoff."},
                    {"name": "Catalog Boundary", "description": "Owns price snapshot, inventory review, and checkout validation evidence."},
                ],
                "related_workstream_titles": ["Govern Commerce Launch System", "Define Storefront boundary", "Define Catalog boundary"],
                "intended_paths": ["apps/web", "src/checkout"],
                "watch_paths": [],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "timeline\n"
                    "    title Program Waves\n"
                    "    Checkout spine : Browse-to-cart proof : Payment failure recovery\n"
                    "    Catalog integrity : Price snapshot rules : Inventory review\n"
                    "    Order reliability : Idempotent creation : Webhook replay proof\n"
                    "    Operational hardening : Observability : Release gate\n"
                ),
            },
        ],
    }
    return _complete_host_reasoned_proposal(proposal)


def _complete_host_reasoned_proposal(proposal: dict[str, object]) -> dict[str, object]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), dict) else {}
    title = str(intent.get("title") or "Host Authored Greenfield Project")
    prompt = str(intent.get("prompt") or title)
    release = "0.0.1"
    proposal["project_brief"] = _host_project_brief(title=title, prompt=prompt, release=release)
    proposal["project_intelligence"] = _host_project_intelligence(title=title, release=release)
    backlog = proposal.get("backlog")
    if isinstance(backlog, list):
        actor_lines = _host_actor_lines_for_prompt(prompt)
        for index, row in enumerate(backlog):
            if not isinstance(row, dict):
                continue
            if index == 0:
                row.setdefault("workstream_type", "program_parent")
            row.setdefault("rationale_lines", _host_rationale_lines(row, prompt=prompt))
            row.setdefault(
                "domain_intelligence",
                _host_domain_intelligence(
                    title=title,
                    row_title=str(row.get("title") or title),
                    actors=actor_lines,
                ),
            )
    return proposal


def _host_actor_lines_for_prompt(prompt: str) -> list[str]:
    if "ecommerce" in prompt.casefold() or "checkout" in prompt.casefold():
        return [
            "Shopper advocate: represents the buyer moving through browse, cart, checkout, failure recovery, and order confirmation.",
            "Commerce operator: owns catalog readiness, checkout handoff, and day-to-day order workflow movement.",
            "Payment risk reviewer: owns payment failure, duplicate order, retry abuse, and provider-policy exposure.",
            "Checkout proof reviewer: decides whether browser, contract, and recovery proof are strong enough to advance release.",
            "Commerce build owner: owns storefront, checkout, catalog, source paths, implementation sequence, and validation commands after planning.",
        ]
    if "plant" in prompt.casefold() or "sensor" in prompt.casefold():
        return [
            "Plant owner advocate: represents the person depending on the monitor to surface plant health before neglect or over-care causes damage.",
            "Care routine operator: owns watering schedule, sensor review, refill workflow, and day-to-day plant-care movement.",
            "Plant safety reviewer: owns overwatering, dry-soil, alert failure, electrical, and unattended-device exposure.",
            "Care proof reviewer: decides whether sensor, watering, alert, and recovery proof is strong enough to advance release.",
            "Plant monitor build owner: owns device controller, plant-state model, source paths, implementation sequence, and validation commands after planning.",
        ]
    return [
        "Product beneficiary advocate: represents the person who receives value from the first path.",
        "Product workflow operator: owns day-to-day movement through the proposed workflow.",
        "Product risk reviewer: owns the unresolved harm, loss, compliance, or operational exposure.",
        "Product proof reviewer: decides whether evidence is strong enough to advance the release.",
        "Product build owner: owns source paths, implementation sequence, and validation commands after planning.",
    ]


def _host_release_focus_for_prompt(prompt: str) -> str:
    lowered = prompt.casefold()
    if "ecommerce" in lowered or "checkout" in lowered:
        return "commerce checkout recovery path"
    if "plant" in lowered or "sensor" in lowered:
        return "plant-care monitoring path"
    if "defi" in lowered or "risk" in lowered:
        return "DeFi risk-monitoring path"
    return "first product path"


def _host_rationale_lines(row: dict[str, object], *, prompt: str) -> list[str]:
    title = str(row.get("title") or "proposed work").strip()
    opportunity = str(row.get("opportunity") or row.get("product_view") or title).strip()
    first_slice = str(row.get("recommended_first_slice") or row.get("product_view") or title).strip()
    metric = next((str(item).strip() for item in row.get("success_metrics", []) if str(item).strip()), first_slice)
    release_focus = _host_release_focus_for_prompt(prompt)
    return [
        f"- why now: {opportunity}",
        f"- expected outcome: {first_slice}",
        f"- tradeoff: {title} keeps the {release_focus} visible while delaying wider automation.",
        f"- deferred for now: broad integrations, irreversible actions, and unrelated platform work wait until {release_focus} proof exists.",
        f"- ranking basis: {metric}",
    ]


def _host_project_brief(*, title: str, prompt: str, release: str) -> dict[str, object]:
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "purpose": f"{title} helps the first user complete one reviewable product path without losing state, owner, failure, or evidence context.",
        "operating_principle": f"Every release {release} claim must connect the user action, state change, owning boundary, validation result, and reviewer-visible evidence.",
        "project_outcome": f"A reviewer can inspect the {title} first path, state change, evidence, non-goals, and release decision before implementation expands scope.",
        "blueprint_sections": [
            {
                "section": "Product story",
                "must_capture": "The user outcome, first path, business value, boundaries, and excluded production claims.",
                "why_it_matters": "It keeps the project understandable before expert records and implementation details appear.",
            },
            {
                "section": "Actors and systems",
                "must_capture": "Human actors, external systems, internal systems, owners, and approval responsibilities.",
                "why_it_matters": "It prevents arbitrary personas and clarifies who changes or absorbs risk.",
            },
            {
                "section": "Owned product boundaries",
                "must_capture": "Which product capability owns each state change, external handoff, evidence source, and release decision.",
                "why_it_matters": "It keeps product understanding ahead of implementation detail and prevents disconnected ownership.",
            },
            {
                "section": "Proof boundary",
                "must_capture": "Evidence tiers, validation commands, failure modes, unresolved assumptions, and promotion gates.",
                "why_it_matters": "It prevents proposal prose from becoming source-backed implementation evidence.",
            },
        ],
        "customization_options": [
            {
                "id": "D1",
                "decision": "First user and job",
                "recommended": "Name the first person who must succeed and the single job that proves value.",
                "choices": ["end user", "operator", "reviewer", "administrator"],
                "impact": "Changes the first path, actors, UI or command surface, access model, and proof target.",
            },
            {
                "id": "D2",
                "decision": "Source and integration boundary",
                "recommended": "Keep integrations fixture-backed until credentials, contracts, and proof requirements are explicit.",
                "choices": ["fixture only", "sandbox provider", "read-only live source", "production integration later"],
                "impact": "Changes security posture, validation harness, architecture diagrams, and release risk.",
            },
            {
                "id": "D3",
                "decision": "Runtime and delivery shape",
                "recommended": "Choose the smallest runtime that can prove the first product journey honestly.",
                "choices": ["local CLI", "web app", "API service", "hybrid surface"],
                "impact": "Changes source paths, validation commands, deployment assumptions, and operator experience.",
            },
            {
                "id": "D4",
                "decision": "Proof bar",
                "recommended": "Require concrete behavior proof before any source-backed or release-ready claim.",
                "choices": ["unit proof", "contract proof", "browser proof", "scenario replay"],
                "impact": "Changes validation obligations, evidence maturity, and release promotion criteria.",
            },
            {
                "id": "D5",
                "decision": "First release ambition",
                "recommended": f"Keep {release} focused on one complete journey and defer broad platform capability.",
                "choices": ["one path", "one path plus audit", "one vertical slice", "multi-lane program"],
                "impact": "Changes backlog depth, component boundaries, wave count, and delivery risk.",
            },
        ],
        "customization_prompts": [
            f"Confirm the primary actor, first journey, and proof bar for the accepted project before writing records.",
            "Revise the external systems, source boundary, or release ambition before proposal apply if any assumption is wrong.",
            "Reject this proposal when the story does not match the business problem or first value path.",
        ],
        "pre_coding_checkpoints": [
            {
                "checkpoint": "Product story accepted",
                "operator_question": "Does the story match the business problem, first user, and first journey?",
                "done_when": "The accepted proposal names the product promise, first path, actors, systems, and non-goals.",
            },
            {
                "checkpoint": "Governance topology aligned",
                "operator_question": "Do workstreams, components, diagrams, release plan, and proof all describe the same project?",
                "done_when": "Workstreams, components, diagrams, release, and validation records share one topology spine.",
            },
            {
                "checkpoint": "Evidence boundary explicit",
                "operator_question": "Which claims are user intent, assumptions, source backed, validated, or operational?",
                "done_when": "Every major claim has a visible evidence tier and unresolved claims remain blocked.",
            },
            {
                "checkpoint": "Implementation lane ready",
                "operator_question": "Which child workstream can start source work without broadening the project?",
                "done_when": "The first child lane has source paths, owners, tests, rollback or recovery posture, and proof commands.",
            },
        ],
        "coding_readiness_gates": [
            f"{title} has an accepted product story with actors, systems, first path, and unresolved assumptions.",
            "The first implementation lane maps to one workstream, one component boundary, one diagram path, and one proof gate.",
            "Every external dependency is fixture-backed, sandboxed, source-backed, or explicitly deferred before source edits start.",
            "The release plan names promotion criteria and does not claim production readiness beyond the accepted first path.",
        ],
        "host_independent_paths": [
            {
                "path": "Confirm product intent",
                "command": f"odylith greenfield propose --repo-root . --prompt {json.dumps(prompt)}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use before proposal expansion so the operator can confirm, edit, or reject the interpretation.",
            },
            {
                "path": "Create confirmed records",
                "command": f"odylith greenfield create --repo-root . --prompt {json.dumps(prompt)} --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release {release}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use after intent confirmation so Odylith builds, validates, gates, writes, and refreshes the proposal-owned records.",
            },
            {
                "path": "Optional proposal review",
                "command": f"odylith greenfield propose --repo-root . --prompt {json.dumps(prompt)} --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use only when a reviewer explicitly asks to inspect the apply-ready JSON before apply.",
            },
        ],
    }


def _host_project_intelligence(*, title: str, release: str) -> dict[str, object]:
    layers = {
        key: [
            f"{key.replace('_', ' ').title()} row one keeps {title} tied to the accepted product story and source boundary.",
            f"{key.replace('_', ' ').title()} row two names the owner, evidence tier, and invalidation trigger for the release.",
        ]
        for key in PROJECT_INTELLIGENCE_LAYERS
    }
    layers["intent"].append(f"Intent row three states the first complete path for the accepted project before broad platform scope.")
    layers["ontology"].append(f"Ontology row three keeps user, state object, evidence record, and release gate distinct for the accepted project.")
    layers["operators"].append(f"Operators row three allows promotion only after validation proof and topology refresh pass.")
    layers["validation_obligations"].append(f"Validation row three blocks release movement when source, fixture, or diagram proof is missing.")
    layers["topology"].append(f"Topology row three links backlog, components, diagrams, release plan, and proof artifacts together.")
    return {
        "schema_version": "odylith.greenfield.project_intelligence.v1",
        "purpose": f"Make {title} readable and governable as one product spine before any generated artifact drives implementation.",
        "coding_posture": "Coding starts only after the accepted project story, first child workstream, component boundary, source paths, and validation commands agree.",
        "control_surface_summary": [
            f"{title} begins as user intent and must not claim source-backed behavior until implementation proof exists.",
            "Backlog records carry product workstreams and the first implementation lane.",
            "Component records carry ownership, interfaces, invariants, and proof obligations.",
            "Diagram records carry topology, state movement, handoffs, controls, and evidence boundaries.",
            f"Release {release} carries only the first path that has accepted validation criteria.",
        ],
        "customization_flow": [
            "Confirm the product story and material ambiguities before proposal expansion.",
            "Review the confirmed proposal for actors, systems, topology, risks, and proof.",
            "Apply the accepted proposal only after deterministic validation and the governed write gate pass.",
            "Start source work only from the accepted child lane with source paths and proof commands.",
        ],
        **layers,
    }


def _host_domain_intelligence(*, title: str, row_title: str, actors: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": "host_reasoned_project",
        "summary": f"{row_title} comes from the accepted project story, with proof and topology kept explicit.",
        "actors": actors or _host_actor_lines_for_prompt(title),
        "intent": [
            f"{row_title} expresses a specific part of the accepted product story for the accepted project.",
            "The row must preserve user value, source boundary, proof gate, and unresolved assumptions.",
        ],
        "scope": [
            f"{row_title} owns its named project slice and does not expand into unrelated implementation scope.",
            "The boundary stays user-intent until source paths, tests, and refreshed evidence exist.",
        ],
        "ontology": [
            f"Actor: the person or team whose job this workstream must make successful for the accepted project.",
            "State object: the project object that changes through the first accepted journey.",
            "Evidence record: the proof artifact that decides whether the claim can advance.",
            "Release gate: the condition that blocks promotion when proof or ownership is missing.",
        ],
        "state": [
            f"Current state is accepted proposal intent for {row_title}, not implementation evidence.",
            "Desired state is source-backed proof with matching workstream, component, diagram, and release records.",
        ],
        "operators": [
            "Accept product intent only after the operator confirms story, actors, systems, and assumptions.",
            "Open implementation work only after the child lane names source paths and proof commands.",
            "Promote evidence only after validation passes and generated surfaces refresh from source truth.",
        ],
        "constraints": [
            "Do not claim production readiness, operational maturity, or source-backed behavior from proposal prose.",
            "Do not let diagrams, components, or releases drift away from the accepted product story.",
        ],
        "source_of_truth_map": [
            "Backlog records own workstream intent, priority, dependencies, risks, and success metrics for this row.",
            "Component records own boundaries, interfaces, invariants, and proof obligations connected to this row.",
            "Diagram records own topology views and must stay linked to the row and component ownership.",
        ],
        "evidence_model": [
            "User intent supports proposal truth but not source-backed implementation claims.",
            "Source-backed evidence requires files, tests, renders, or explicit operational records.",
        ],
        "decisions": [
            "The first decision is whether the operator accepts the story and first path.",
            "The next decision is which child workstream can safely start implementation planning.",
        ],
        "assumptions": [
            "Unanswered product choices remain visible and cannot silently become implementation facts.",
            "External systems are deferred or fixture-backed unless the proposal explicitly proves otherwise.",
        ],
        "topology": [
            f"{row_title} must connect to the project story, component ownership, diagram views, and release proof.",
            "Workstream, component, diagram, validation, and release records form one topology spine.",
        ],
        "invariants": [
            "Every source-backed claim must name its source path or proof artifact.",
            "Every component boundary must have owner, interface, failure mode, and validation obligation.",
        ],
        "risks": [
            "Generic workstream language can hide the real business problem and confuse implementation owners.",
            "Unbound artifacts can make implementation appear ready while the first path remains unproven.",
        ],
        "validation_obligations": [
            "Validate that the story, workstreams, components, diagrams, and release plan describe the same first path.",
            "Validate that missing proof blocks promotion instead of becoming a dashboard claim.",
            "Validate that source edits start only after a child technical plan names paths and tests.",
        ],
        "artifacts": [
            "Backlog row captures the native workstream contract for this slice.",
            "Component records capture ownership, interfaces, and proof obligations for this slice.",
            "Diagram records capture topology and flow claims that reviewers can inspect.",
        ],
        "authority": [
            "The operator owns accepted product intent and any correction to assumptions.",
            "The implementation owner owns source paths only after technical planning is accepted.",
        ],
        "owners": [
            "Product owner owns whether this row still matches the project story.",
            "Proof owner owns whether validation evidence is strong enough to promote the claim.",
        ],
        "execution_memory": [
            "Future agents must start from the accepted story and topology before editing source.",
            "Past proposal prose does not outrank source-backed proof or explicit operator corrections.",
        ],
        "metrics": [
            "Zero orphaned workstreams, components, diagrams, or release gates after apply.",
            "Every first-path claim has a visible evidence tier and validation obligation.",
        ],
        "change_model": [
            "Changing the first path invalidates dependent workstreams, components, diagrams, and release criteria.",
            "Changing an external dependency invalidates source boundary, risk, proof, and topology claims.",
        ],
        "invalidation_rules": [
            "If source proof is missing, the claim stays user-intent or assumption rather than source-backed.",
            "If operator corrections contradict the proposal, governance artifacts must be regenerated or repaired.",
        ],
        "conflict_model": [
            "Accepted product intent beats generated fallback language.",
            "Source-backed tests beat generated dashboard projections when they disagree.",
        ],
        "transfer_priors": [
            "Keep the first path small enough to prove with concrete validation.",
            "Prefer artifact-native enrichment over dumping generic domain-intelligence sections everywhere.",
        ],
    }


def _host_reasoned_recipe_legacy_shape() -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "greenfield",
        "intent": {
            "title": "Recipe-sharing app",
            "summary": "A web app where home cooks publish, browse, and search recipes.",
        },
        "observed_source": {"evidence_tier": "docs_only", "notes": "Empty repo."},
        "assumptions": ["Web-first delivery.", "Relational data store."],
        "open_questions": ["Which runtime should own the first implementation?"],
        "risks": ["Photo upload can expand scope if it is pulled into the first release."],
        "security_compliance": {
            "domain": "Recipe-sharing consumer app with account, recipe visibility, comments, and user-generated content policy risk.",
            "security": "Security posture covers auth sessions, ownership checks, private edits, abuse prevention, and moderation hooks.",
            "policy": "Privacy, public publishing, data retention, accessibility, and moderation policy must be explicit before implementation.",
        },
        "validation_strategy": {
            "release_gate": ["Golden path from sign-up to recipe detail must pass."],
        },
        "program": {
            "waves": [
                {
                    "id": "W1",
                    "title": "Core authoring and browsing",
                    "goal": "Ship account, authoring, browsing, and shared UI shell.",
                    "release": "0.0.1",
                    "workstreams": ["WS-01", "WS-02", "WS-03"],
                },
                {
                    "id": "W2",
                    "title": "Social layer",
                    "goal": "Add favorites and comments after the first release is stable.",
                    "release": "0.1.0",
                    "workstreams": ["WS-04"],
                },
            ]
        },
        "release_plan": [
            {
                "release": "0.0.1",
                "label": "Recipe-sharing 0.0.1",
                "first_target_workstreams": ["WS-01", "WS-02", "WS-03"],
                "exit_criteria": "Golden-path browser E2E, HTTP contract tests, and architecture render proof all pass.",
            },
            {
                "release": "0.1.0",
                "label": "Social layer",
                "first_target_workstreams": ["WS-04"],
                "exit_criteria": "Favorite and comment flows pass with moderation hooks.",
            },
        ],
        "backlog": [
            {
                "id": "WS-00",
                "title": "Recipe-sharing app program",
                "problem": "The repo has no confirmed program, release target, component boundaries, topology, or proof gates.",
                "customer": "Cooks",
                "opportunity": "Create a governed recipe-sharing plan with explicit first release behavior and proof.",
                "product_view": "A browser app where cooks can sign in, publish recipes, browse, and search.",
                "recommended_first_slice": "Create the first governed release lane for accounts, recipe authoring, browsing, and UI shell.",
                "success_metrics": [
                    "First release target includes the wave-one workstreams.",
                    "Component and architecture records are linked to the created workstreams.",
                ],
            },
            {
                "id": "WS-01",
                "title": "Accounts and sessions",
                "problem": "Recipes need an owner before authoring and private edits can be governed.",
                "customer": "Cooks",
                "opportunity": "Account sessions create the ownership claim used by every recipe write.",
                "product_view": "Users can sign up, sign in, sign out, and reach protected routes.",
                "first_slice_proof": "Sign-up, sign-in, sign-out, and protected-route access work in browser and contract tests.",
                "success_metrics": [
                    "Authentication contract tests pass for sign-up, sign-in, sign-out, and current-user endpoints.",
                    "Protected route returns 401 without a session and 200 with a valid session.",
                ],
                "component_focus": ["AccountService", "WebUI"],
                "related_diagram_slugs": ["system-context", "auth-sequence"],
                "dependencies": ["Relational user and session tables."],
                "interfaces": ["HTTP /auth/sign-up, /auth/sign-in, /auth/sign-out, and /auth/me."],
                "validation": ["Browser sign-up to protected route passes."],
            },
            {
                "id": "WS-02",
                "title": "Recipe authoring CRUD",
                "problem": "Signed-in cooks need a safe way to create and edit their own recipes.",
                "customer": "Cooks",
                "opportunity": "Recipe authoring gives the product its durable content spine.",
                "product_view": "Authenticated CRUD over recipes with ingredients, steps, and tags.",
                "first_slice_proof": "A signed-in user creates, edits, and deletes only their own recipe.",
                "success_metrics": [
                    "Recipe CRUD contract tests pass for create, read, update, and delete.",
                    "Cross-user edit and delete attempts return 403.",
                ],
                "component_focus": ["RecipeStore", "AccountService", "WebUI"],
                "related_diagram_slugs": ["system-context", "recipe-domain-er"],
                "dependencies": ["Accounts and sessions must provide ownership claims."],
                "interfaces": ["HTTP /recipes and /recipes/{id} CRUD endpoints."],
                "validation": ["Ownership and CRUD tests pass."],
            },
            {
                "id": "WS-03",
                "title": "Recipe browsing and search",
                "problem": "Anonymous visitors need a way to discover recipes that have been published.",
                "customer": "Readers",
                "opportunity": "Browsing and title search make the first release useful without social features.",
                "product_view": "Anonymous list, detail, pagination, and title-substring search over recipes.",
                "first_slice_proof": "Visitor searches by title and opens a recipe detail page.",
                "success_metrics": [
                    "List, detail, pagination, and search contract tests pass.",
                    "Browser search-to-detail flow passes with seeded data.",
                ],
                "component_focus": ["RecipeStore", "WebUI"],
                "related_diagram_slugs": ["system-context", "recipe-domain-er"],
                "dependencies": ["Recipe authoring seeds published recipe data."],
                "interfaces": ["HTTP /recipes list and search plus /recipes/{id} detail."],
                "validation": ["Browser search-to-detail flow passes."],
            },
            {
                "id": "WS-04",
                "title": "Favorites and comments",
                "problem": "The product needs social signals after the first release is stable.",
                "customer": "Cooks",
                "opportunity": "Favorites and comments create lightweight engagement without disrupting release 0.0.1.",
                "product_view": "Users favorite recipes and comment with moderation hooks.",
                "first_slice_proof": "A user favorites a recipe and comments on it.",
                "success_metrics": [
                    "Favorite contract tests pass.",
                    "Comment moderation smoke test passes.",
                ],
                "component_focus": ["SocialGraph", "WebUI"],
                "related_diagram_slugs": ["system-context"],
                "dependencies": ["Accounts, recipes, and browsing are already live."],
                "interfaces": ["HTTP /favorites and /comments endpoints."],
                "validation": ["Favorite and comment browser path passes."],
            },
        ],
        "components": [
            {
                "id": "AccountService",
                "label": "AccountService",
                "kind": "service",
                "intended_path": "src/services/account_service",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own identity, credentials, sessions, and ownership claims for recipe writes.",
                "boundary": "Identity, credentials, sessions, and user ownership claims only.",
                "interfaces": ["HTTP /auth endpoints and internal session validation."],
                "dependencies": ["Relational data store and password hashing library."],
                "proof_expectations": ["Auth contract tests and session expiry tests pass."],
            },
            {
                "id": "RecipeStore",
                "label": "RecipeStore",
                "kind": "service",
                "intended_path": "src/services/recipe_store",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own recipe persistence, ownership enforcement, ingredients, steps, and tags.",
                "boundary": "Recipe CRUD, child recipe rows, and ownership-scoped writes.",
                "interfaces": ["HTTP /recipes CRUD and read interfaces."],
                "dependencies": ["AccountService ownership claims and relational data store."],
                "proof_expectations": ["CRUD, ownership, and schema migration tests pass."],
            },
            {
                "id": "WebUI",
                "label": "WebUI",
                "kind": "ui",
                "intended_path": "src/web/ui",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own browser routes, forms, navigation, error states, and empty states.",
                "boundary": "Browser rendering and form interaction only; no persistence ownership.",
                "interfaces": ["Browser routes for auth, recipes, search, and future social flows."],
                "dependencies": ["AccountService and RecipeStore HTTP interfaces."],
                "proof_expectations": ["Headless browser normal, empty, and error state matrix passes."],
            },
            {
                "id": "SocialGraph",
                "label": "SocialGraph",
                "kind": "service",
                "intended_path": "src/services/social_graph",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own favorites, comments, social engagement state, and moderation hooks.",
                "boundary": "Social edges, comments, and moderation records only.",
                "interfaces": ["HTTP /favorites and /comments endpoints."],
                "dependencies": ["AccountService users and RecipeStore recipe identifiers."],
                "proof_expectations": ["Favorite, comment, and moderation hook tests pass."],
            },
        ],
        "diagrams": [
            {
                "slug": "system-context",
                "title": "Recipe system context",
                "type": "flowchart",
                "summary": "Top-level flow between browser, services, and data store.",
                "related_workstreams": ["WS-01", "WS-02", "WS-03", "WS-04"],
                "related_components": ["AccountService", "RecipeStore", "WebUI", "SocialGraph"],
                "mermaid_source": (
                    "flowchart LR\n"
                    "  User[Home cook<br/>browser] --> WebUI[WebUI<br/>routes]\n"
                    "  WebUI --> Account[AccountService<br/>sessions]\n"
                    "  WebUI --> Store[RecipeStore<br/>recipe CRUD]\n"
                    "  WebUI --> Social[SocialGraph<br/>favorites]\n"
                    "  Store --> DB[(Relational store)]\n"
                    "  Account --> DB\n"
                    "  Social --> DB\n"
                    "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
                    "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
                    "  classDef data fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
                    "  class User actor;\n"
                    "  class WebUI,Account,Store,Social service;\n"
                    "  class DB data;\n"
                ),
            },
            {
                "slug": "auth-sequence",
                "title": "Authentication sequence",
                "type": "sequenceDiagram",
                "summary": "Sign-in path through browser, WebUI, AccountService, and data store.",
                "related_workstreams": ["WS-01"],
                "related_components": ["AccountService", "WebUI"],
                "mermaid_source": (
                    "sequenceDiagram\n"
                    "  participant U as Browser\n"
                    "  participant W as WebUI\n"
                    "  participant A as AccountService\n"
                    "  U->>W: POST /sign-in\n"
                    "  W->>A: validate credentials\n"
                    "  A-->>W: session token\n"
                    "  W-->>U: Set-Cookie session; 302 /\n"
                ),
            },
            {
                "slug": "recipe-domain-er",
                "title": "Recipe domain ER",
                "type": "erDiagram",
                "summary": "Recipe ownership and child rows for ingredients, steps, and tags.",
                "related_workstreams": ["WS-02", "WS-03"],
                "related_components": ["RecipeStore"],
                "mermaid_source": (
                    "erDiagram\n"
                    "  USER ||--o{ RECIPE : authors\n"
                    "  RECIPE ||--|{ INGREDIENT : has\n"
                    "  RECIPE ||--|{ STEP : has\n"
                    "  RECIPE }o--o{ TAG : tagged_with\n"
                ),
            },
        ],
    }


def _host_reasoned_crispr_without_parent() -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "host_reasoned_greenfield_proposal",
        "intent": {"title": "CRISPR Ethics Review App", "project_slug": "crispr-ethics-review-app"},
        "observed_source": {"summary": "No application source found."},
        "assumptions": ["Single-institution deployment.", "No PHI stored in the first release."],
        "open_questions": ["Are decisions advisory or legally binding later?"],
        "risks": ["DURC protocol details require strict access control and auditability."],
        "security_compliance": {
            "frameworks": ["NIH Guidelines for nucleic acid research.", "USG DURC oversight policy."],
            "scope": ["HIPAA not in 0.0.1 because no PHI is stored.", "WCAG 2.2 AA baseline."],
            "controls": ["Append-only decision ledger.", "Role and COI-aware authorization at read boundary."],
            "risk": "Domain risk centers on sensitive DURC protocol details, audit recovery, and access-control failure.",
        },
        "validation_strategy": ["Role matrix, FSM, ledger, audit, and browser proof gates must pass."],
        "program": {
            "waves": [
                {
                    "id": "W1",
                    "label": "Foundations",
                    "goal": "Prove attributable protocol review through a decision ledger.",
                    "validation_gate": "End-to-end protocol submit, transition, decision, and audit proof passes.",
                    "workstreams": ["WS-IA"],
                },
                {
                    "id": "W2",
                    "label": "Review intelligence",
                    "goal": "Add CRISPR-specific review workflow gates.",
                    "validation_gate": "FSM transition and DURC negative tests pass.",
                    "workstreams": ["WS-WORKFLOW"],
                },
            ]
        },
        "release_plan": {
            "selector": "0.0.1",
            "label": "0.0.1",
            "provisional_release_id": "release-crispr-ethics-0-0-1",
            "target_workstreams": ["WS-IA"],
            "promotion_criteria": ["First-wave authorization and audit gates pass."],
        },
        "backlog": [
            {
                "id": "WS-IA",
                "title": "Identity, sessions, and COI-aware authorization",
                "problem": "Reviewers with conflicts must be blocked at the API read boundary, not only in UI.",
                "customer": "Board chair, reviewers, PI submitters, admins, and regulator read-only users.",
                "opportunity": "Make COI a first-class authorization input before sensitive CRISPR packets exist.",
                "product_view": "Single authorize(actor, action, resource) choke point consumed by every component.",
                "recommended_first_slice": "PI can submit; conflicted reviewer cannot read; regulator can read but not write.",
                "success_metrics": [
                    "Every write endpoint routes through authorize(actor, action, resource) in CI instrumentation.",
                    "Zero conflicted reviewer reads succeed in the API role-matrix integration suite.",
                ],
                "component_focus": ["identity-access"],
                "related_diagram_slugs": ["atlas-topology"],
                "dependencies": ["Audit trail records COI declarations and session events."],
                "interfaces": ["authenticate, authorize, and declare_coi service contracts."],
                "validation": ["Role-matrix and COI negative tests pass at the API boundary."],
            },
            {
                "id": "WS-WORKFLOW",
                "title": "Review workflow phase state machine",
                "problem": "CRISPR reviews need legal transitions and explicit DURC gate enforcement.",
                "customer": "Board chair, reviewers, and auditors reconstructing phase history.",
                "opportunity": "Replace ad-hoc phase updates with deterministic, auditable workflow transitions.",
                "product_view": "Phase FSM exposes transition() and writes audit events for every legal transition.",
                "recommended_first_slice": "Protocol moves from intake through decision; illegal transitions are rejected.",
                "success_metrics": [
                    "Every phase mutation routes through transition() with no direct setter path.",
                    "Every illegal transition leaves state unchanged and returns a structured error.",
                ],
                "component_focus": ["review-workflow-engine"],
                "related_diagram_slugs": ["atlas-topology"],
                "dependencies": ["identity-access authorizes transitions; audit-trail records transition events."],
                "interfaces": ["transition and current_phase service contracts."],
                "validation": ["FSM legal and illegal transition tests pass."],
            },
        ],
        "components": [
            {
                "component_id": "identity-access",
                "label": "Identity Access",
                "kind": "service",
                "intended_path": "src/identity-access",
                "status": "planned",
                "qualification": "candidate",
                "responsibility": "Authentication, sessions, roles, and COI-aware authorization for all review data.",
                "boundary": "Owns identity and authorization checks; no downstream component can bypass authorize().",
                "dependencies": ["audit-trail records declaration events; persistence stores users and roles."],
                "interfaces": ["authenticate, authorize, and declare_coi service contracts."],
                "validation": ["Role-matrix, COI negative, and session-lifecycle tests."],
                "security_posture": ["Authorization enforced at API read boundary, not UI."],
            },
            {
                "component_id": "review-workflow-engine",
                "label": "Review Workflow Engine",
                "kind": "service",
                "intended_path": "src/review-workflow",
                "status": "planned",
                "qualification": "candidate",
                "responsibility": "Authorization-aware phase state machine for CRISPR protocol reviews.",
                "boundary": "Owns legal phase transitions and emits audit events for each transition.",
                "dependencies": ["identity-access authorizes transitions; audit-trail records transition events."],
                "interfaces": ["transition and current_phase service contracts."],
                "validation": ["FSM legal, illegal, idempotency, and authorization tests."],
            },
        ],
        "diagrams": [
            {
                "slug": "atlas-topology",
                "title": "CRISPR Review Topology",
                "kind": "flowchart",
                "summary": "Show authorization and workflow ownership for the first governed release.",
                "link_state": "atlas_first_draft",
                "related_workstreams": ["WS-IA", "WS-WORKFLOW"],
                "components": [
                    {"name": "identity-access", "description": "Auth, sessions, roles, and COI-aware authorization."},
                    {"name": "review-workflow-engine", "description": "Legal phase transitions and audit events."},
                ],
                "mermaid_source": (
                    "flowchart LR\n"
                    "  IA[\"identity-access<br/>COI-aware auth\"] --> WF[\"review-workflow-engine<br/>phase FSM\"]\n"
                    "  classDef auth fill:#eef9f1,stroke:#2f9e44,color:#163d22;\n"
                    "  classDef workflow fill:#f4f7ff,stroke:#3b5bdb,color:#1c2c5b;\n"
                    "  class IA auth;\n"
                    "  class WF workflow;\n"
                ),
            }
        ],
    }


def test_greenfield_prompt_returns_apply_ready_confirmed_proposal(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        confirmed_intent=_confirmed_intent(),
    )

    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    encoded = json.dumps(proposal)
    assert proposal["mode"] == "host_reasoned_greenfield_proposal"
    assert proposal["provider_calls"] == 0
    assert proposal["host_agnostic"] is True
    assert proposal["intent"]["reasoning_mode"] == "odylith_confirmed_apply_ready"
    assert proposal["classification"]["method"] == "confirmed_open_world_product_shape"
    assert proposal["intent"]["title"] == "Municipal Permit Review Workspace"
    assert "catalog" not in proposal
    assert len(proposal["backlog"]) >= 4
    assert len(proposal["components"]) >= 4
    assert len(proposal["diagrams"]) >= 6
    assert {row["title"] for row in proposal["diagrams"]} >= {
        "System Context View",
        "First Path Sequence",
        "State and Evidence View",
        "Component Boundary View",
        "Ownership and Proof View",
        "Release Proof Review",
    }
    assert "Permit file registry" in encoded
    assert "Zoning check ledger" in encoded
    assert "Release 0.0.1 succeeds when a supervisor can inspect one permit review file" in encoded
    assert "Municipal Permit Review Workspace Workflow Service" not in encoded
    assert proposal["project_brief"]["blueprint_sections"]
    assert proposal["project_intelligence"]["intent"]
    assert proposal["observed_source"]["source_posture"] == "empty_or_no_app_source"
    assert "greenfield create" in proposal["apply_commands"][0]
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in proposal["apply_commands"][0]
    assert "--confirm" in proposal["apply_commands"][0]
    assert "--release '0.0.1'" in proposal["apply_commands"][0]
    assert "review-only" in proposal["apply_commands"][1]
    assert "internal apply payload" not in encoded
    assert "active-proposal.v1.json" not in encoded
    assert "Make product-owned systems explicit:" not in encoded
    assert "releaseable" not in encoded
    for row in proposal["backlog"]:
        for line in row.get("rationale_bullets", []):
            assert len(line) <= 260
    assert "host_instruction" not in proposal
    assert "reasoning_contract" not in proposal
    assert "proposal_template" not in proposal
    assert "canonical_proposal" not in proposal
    assert "canonical_proposal_gate" not in proposal


def test_greenfield_confirmed_builder_rejects_shallow_confirmed_intent(tmp_path) -> None:
    with pytest.raises(ValueError, match="requires product story"):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Create a community archive",
            confirmed_intent={"title": "Community Archive"},
        )


def test_greenfield_text_starts_with_product_intent_confirmation(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Design a mathematics research workspace for spectral graph theory",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Product Intent Confirmation needed" in output
    assert "No files changed." in output
    assert "Host reasoning task" in output
    assert "Write in chat" in output
    assert "Do not" in output
    assert "echo command instructions as the product name" in output
    assert "generate implementation records, architecture records, release waves, validation obligations, or proposal JSON before confirmation" in output
    assert "Original user intent" in output
    assert "Next step" in output
    assert "Confirm: if the interpretation is right" in output
    assert "Edit: if the product story, actors, systems, assumptions, first path, or proof boundary is wrong" in output
    assert "Reject: if this is not the intended product" in output
    assert "No records were written. Confirm, edit, or reject this interpretation." not in output
    assert "greenfield create --repo-root ." in output
    assert "--confirm" in output
    assert "Confirmed CLI after confirmation" in output
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in output
    assert "дж" not in output
    assert "soн" not in output
    assert "..." not in output
    assert "Gate 1 - Interpretation" not in output
    assert "Product workstreams:" not in output
    assert "Candidate product boundaries:" not in output
    assert "Architecture review views:" not in output
    assert "Records after confirmation" not in output
    assert "A Mathematics Research Workspace For Spectral Graph Theory System Overview" not in output
    assert "A Mathematics Research Workspace For Spectral Graph Theory First Slice Flow" not in output
    assert "apply-ready JSON" not in output
    assert "provider_calls_by_odylith_cli" not in output
    assert "mode: host_reasoned_greenfield_proposal" not in output
    assert "shared artifact:" not in output
    assert "Project-first blueprint" not in output
    assert "Workstream domain intelligence" not in output
    assert len(output.splitlines()) <= 38
    assert len(output) <= 3200


def test_greenfield_confirm_intent_shows_direct_apply_handoff(tmp_path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Odylith greenfield proposal: Municipal Permit Review Workspace" in output
    assert "No files changed" in output
    assert "- apply-ready JSON: built, normalized, validated" in output
    assert "- mode: host_reasoned_greenfield_proposal" in output
    assert "Project requirements" in output
    assert "Project-first blueprint" in output
    assert "Backlog proposal" in output
    assert "Planned components" in output
    assert "Draft architecture diagrams" in output
    assert "greenfield create --repo-root ." in output
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in output
    assert "internal apply payload" not in output
    assert "active-proposal.v1.json" not in output
    assert "host_instruction" not in output
    assert "reasoning_contract" not in output


def test_greenfield_confirm_intent_without_intent_file_fails_closed(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--confirm-intent",
        ]
    )

    assert rc == 2
    output = capsys.readouterr().out
    assert "requires --intent-file" in output
    assert "will not write records from a thin prompt" in output


def test_greenfield_text_full_detail_keeps_apply_path_available_after_intent_confirmed(tmp_path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--detail",
            "full",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "Odylith greenfield proposal: Municipal Permit Review Workspace" in output
    assert "Gate 1 - Interpretation" not in output
    assert "Gate 2 - Clarify Before Apply" not in output
    assert "Gate 3 - Proposal Preview" not in output
    assert "Gate 4 - Choose Next Action" not in output
    assert "Backlog proposal" in output
    assert "Planned components" in output
    assert "Draft architecture diagrams" in output
    assert "odylith greenfield create --repo-root ." in output
    assert "--intent-file .odylith/runtime/greenfield/confirmed-intent.md" in output
    assert "--confirm" in output
    assert "internal apply payload" not in output
    assert ".odylith/runtime/greenfield/active-proposal.v1.json" not in output
    assert len(output.splitlines()) <= 270


def test_greenfield_title_preserves_meaningful_trailing_domain_terms(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="field inspection evidence workspace for municipal building permits",
        confirmed_intent=_confirmed_intent(),
    )

    assert proposal["intent"]["title"] == "Municipal Permit Review Workspace"
    assert not proposal["intent"]["title"].endswith(" To")


def test_greenfield_cli_json_defaults_to_intent_confirmation(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build a statistics notebook repo",
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "product_intent_reasoning_request"
    assert payload["provider_calls"] == 0
    assert payload["write_policy"] == "host_reason_product_intent_before_confirmed_greenfield_create"
    assert payload["host_reasoning_task"]["must_include"]
    assert payload["host_reasoning_task"]["must_not"]
    assert "dump a generic template or domain catalog" in payload["host_reasoning_task"]["must_not"]
    assert "backlog" not in payload
    assert "components" not in payload
    assert "diagrams" not in payload


def test_greenfield_cli_json_is_apply_ready_after_intent_confirmation(tmp_path, capsys) -> None:
    _write_confirmed_intent(tmp_path)
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm-intent",
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "host_reasoned_greenfield_proposal"
    assert payload["provider_calls"] == 0
    assert payload["intent"]["reasoning_mode"] == "odylith_confirmed_apply_ready"
    encoded = json.dumps(payload)
    assert "Permit file registry" in encoded
    assert "Zoning check ledger" in encoded
    assert "Municipal Permit Review Workspace Workflow Service" not in encoded
    assert "reasoning_contract" not in payload
    assert "host_instruction" not in payload
    assert "canonical_proposal" not in payload
    assert "proposal_template" not in payload
    assert len(payload["backlog"]) >= 4
    assert len(payload["components"]) >= 3
    assert len(payload["diagrams"]) >= 6


def test_greenfield_validation_rejects_old_generic_risk_boilerplate(tmp_path) -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["risks"][0] = {
        "statement": (
            "Starting implementation without a named product spine, component ownership, and proof gates can create "
            "disconnected source slices."
        )
    }

    with pytest.raises(ValueError, match="generic greenfield boilerplate"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_workstreams_require_host_authored_intelligence(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "plant sensor")
    brief = proposal["project_brief"]

    workflow = next(row for row in proposal["backlog"] if row["title"] == "Define Storefront boundary")
    intelligence = workflow["domain_intelligence"]
    rendered = greenfield_proposals.render_domain_intelligence_section(intelligence)
    project_intelligence = proposal["project_intelligence"]
    project_rendered = greenfield_proposals.render_project_intelligence_section(project_intelligence)

    assert "Host Authored Greenfield Project" not in project_rendered
    assert "Make Plant Sensor" in project_rendered
    assert intelligence["family"] == "host_reasoned_project"
    assert "Actor:" in rendered
    assert "State object:" in rendered
    assert "Evidence record:" in rendered
    assert "Release gate:" in rendered
    assert "source_of_truth_map" in intelligence
    assert "validation_obligations" in intelligence
    assert "conflict_model" in intelligence
    assert "transfer_priors" in intelligence
    assert "Product story" in json.dumps(brief)
    assert "Actors and systems" in json.dumps(brief)
    assert not any(prompt.startswith("defer ") for prompt in brief["customization_prompts"])
    assert all(prompt[:1].isupper() for prompt in brief["customization_prompts"])
    assert "first implementation lane" in " ".join(brief["coding_readiness_gates"]).casefold()
    assert "prompt title" not in rendered.lower()
    risk_text = json.dumps(proposal["risks"])
    assert "Starting implementation without a named product spine" not in risk_text
    assert "under-modeled in broad greenfield prompts" not in risk_text
    proposal_text = greenfield_proposals.format_proposal_text(proposal)
    assert "Product Story" not in proposal_text
    for row in proposal["backlog"]:
        row_rendered = greenfield_proposals.render_domain_intelligence_section(row["domain_intelligence"])
        labels = _ontology_term_labels(row["domain_intelligence"]["ontology"])
        assert len(labels) == len(set(labels))
        assert "owns Own" not in row_rendered
        assert "owns owns" not in row_rendered.casefold()
    greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_tribunal_uses_domain_specific_visible_actors(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "plant sensor")

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    actor_labels = {row["visible_actor"] for row in decision.to_dict()["visible_actors"]}
    stable_roles = {row["stable_role"] for row in decision.to_dict()["visible_actors"]}

    assert decision.passed
    assert "beneficiary_advocate" in stable_roles
    assert "Plant owner advocate" in actor_labels
    assert "Care routine operator" in actor_labels
    assert "Plant safety reviewer" in actor_labels
    assert "Care proof reviewer" in actor_labels
    assert "Plant monitor build owner" in actor_labels
    assert "beneficiary advocate" not in actor_labels
    assert not any("Host Reasoned Project" in label for label in actor_labels)
    assert not any(label in {"Actor", "State object", "Evidence record", "Release gate"} for label in actor_labels)
    assert "stable judgment roles render as domain-specific actors" in decision.dimensions["validation_roles"]


def test_greenfield_artifacts_are_bound_to_project_intelligence_root(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    schema = proposal["project_intelligence"]["schema_version"]
    keys = list(proposal)

    assert keys.index("artifact_derivation") == keys.index("project_intelligence") + 1
    assert proposal["artifact_derivation"]["root"] == "project_intelligence"
    assert proposal["artifact_derivation"]["root_schema_version"] == schema
    assert proposal["release_plan"]["project_intelligence_binding"]["source"] == "project_intelligence"
    assert proposal["program"]["project_intelligence_binding"]["source"] == "project_intelligence"
    for collection in (
        proposal["program"]["waves"],
        proposal["backlog"],
        proposal["components"],
        proposal["diagrams"],
    ):
        for row in collection:
            binding = row["project_intelligence_binding"]
            assert binding["source"] == "project_intelligence"
            assert binding["schema_version"] == schema
            assert binding["artifact_kind"]
            assert binding["artifact_id"]


def test_greenfield_validation_rejects_artifacts_without_project_intelligence_binding(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    proposal["components"][0].pop("project_intelligence_binding")

    with pytest.raises(ValueError, match="project_intelligence_binding"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_tribunal_rejects_unbound_artifact_projection(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    proposal["diagrams"][0].pop("project_intelligence_binding")

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert not decision.passed
    assert any("project_intelligence_binding" in issue for issue in decision.issues)


def test_artifact_enrichment_projects_domain_graph_into_native_artifact_shapes(tmp_path) -> None:
    from odylith.runtime.domain_intelligence.artifact_enrichment import build_artifact_enrichment

    proposal = _apply_ready_greenfield_fixture(tmp_path, "plant sensor")
    row = next(item for item in proposal["backlog"] if item["title"] == "Define Storefront boundary")

    enrichment = build_artifact_enrichment(row=row, proposal=proposal)

    assert "Domain Intelligence" not in enrichment.radar_sections
    assert enrichment.registry_contract["proof_obligations"]
    assert enrichment.atlas_contract["state_objects"]
    assert enrichment.plan_contract["validation"]
    assert enrichment.casebook_contract["prevention_rules"]
    assert enrichment.compass_contract["proof_boundary"]
    assert enrichment.project_contract["first_path"]


def test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _apply_ready_greenfield_fixture(tmp_path, "plant sensor")
    proposal["intent"]["summary"] = "**Primary reviewer** can compare the accepted path, state, and evidence."
    proposal["backlog"][1]["customer"] = "**Primary reviewer** and __source reviewer__"
    proposal["diagrams"][0]["components"][0]["description"] = "__Surface reviewer__ checks the visible behavior boundary."

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    child_specs = [
        Path(row["idea_path"]).read_text(encoding="utf-8")
        for row in result["backlog"]
        if not row["title"].startswith("Govern Commerce Launch System")
    ]
    joined = "\n".join(child_specs)

    assert "## Domain Intelligence" not in joined
    assert "## First Path And Boundary" in joined
    assert "## Domain Model" not in joined
    assert "## Proof And Acceptance Gates" in joined
    assert "## Ownership And Risk" in joined
    assert "Proof:" in joined
    assert "Gate:" in joined
    assert "source-backed implementation claims" in joined
    parent_spec = next(
        Path(row["idea_path"]).read_text(encoding="utf-8")
        for row in result["backlog"]
        if row["title"].startswith("Govern Commerce Launch System")
    )
    all_radar_text = parent_spec + "\n" + joined
    assert "## Project Intelligence" not in all_radar_text
    assert "## Project Brief" not in all_radar_text
    assert "## Project Requirements" not in all_radar_text
    assert "Do not start coding from the proposal closeout" not in all_radar_text
    assert "Starting implementation without a named product spine" not in all_radar_text
    assert "under-modeled in broad greenfield prompts" not in all_radar_text
    assert "Combining cart, payment, and order state would hide failure recovery" in all_radar_text
    assert "owns Own" not in all_radar_text
    assert "owns owns" not in all_radar_text.casefold()
    assert "Which stack owns the storefront?" in all_radar_text
    assert "- R1." not in all_radar_text
    assert "- Q1." not in all_radar_text
    assert "- domain contract.\n" not in all_radar_text
    assert "- command.\n" not in all_radar_text
    assert "release targeting.\n- and proof sequencing." not in all_radar_text
    assert "?.\n" not in all_radar_text
    assert "**Primary reviewer**" not in all_radar_text
    assert "__source reviewer__" not in all_radar_text
    assert "Primary reviewer and source reviewer" in all_radar_text
    accepted_path = tmp_path / "odylith" / "runtime" / "source" / "accepted-project.v1.json"
    accepted_text = accepted_path.read_text(encoding="utf-8")
    accepted = json.loads(accepted_text)
    assert accepted["schema_version"] == "odylith.accepted_project.v1"
    assert accepted["origin"] == "greenfield"
    assert accepted["proposal"]["artifact_derivation"]["root"] == "project_intelligence"
    assert accepted["validation_gate"]["status"] == "passed"
    assert accepted["validation_gate"]["visible_actors"]
    assert '"tribunal"' not in accepted_text
    assert "greenfield-tribunal" not in accepted_text
    assert "governed-artifact-tribunal" not in accepted_text
    assert "**Primary reviewer**" not in accepted_text
    assert "__Surface reviewer__" not in accepted_text


def test_greenfield_apply_feeds_project_tab_from_accepted_project_and_tribunal(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    prompt = "Build an ecommerce site with checkout recovery"
    proposal = _apply_ready_greenfield_fixture(tmp_path, prompt)

    greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    payload = project_intelligence_builder.build_project_intelligence_payload(
        repo_root=tmp_path,
        shell_payload={},
    )
    html = project_intelligence_presenter.render_project_html({"project_intelligence": payload})
    accepted = json.loads((tmp_path / "odylith" / "runtime" / "source" / "accepted-project.v1.json").read_text(encoding="utf-8"))
    backlog_index = (tmp_path / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")
    b002 = accepted["proposal"]["backlog"][1]
    text = json.dumps(payload, sort_keys=True).casefold()

    assert accepted["proposal"]["intent"]["title"] == "Build An Ecommerce Site With Checkout Recovery"
    assert accepted["proposal"]["intent"]["project_slug"] == "build-an-ecommerce-site-with-checkout-recovery"
    assert b002["title"] == "Define Storefront boundary"
    assert b002["problem"].startswith("The user-facing browse and checkout UI")
    assert "created as a new queued workstream" not in backlog_index
    assert "deeper scope decomposition waits" not in backlog_index
    assert "Define Storefront boundary" in backlog_index
    assert "checkout orchestrator" in text
    assert "an-ecommerce-site-with-checkout-recovery" not in text
    assert payload["title"] == "Ecommerce Site with Checkout Recovery"
    assert payload["projection"]["origin"] == "accepted greenfield project"
    assert "accepted greenfield project" in payload["chips"]
    story = payload["product_story"]
    assert story["headline"] == "Release 0.0.1 proves one usable first path"
    assert "Make Build" not in " ".join(story["paragraphs"])
    assert len(story["paragraphs"]) >= 2
    assert any("keeps the work focused" in paragraph for paragraph in story["paragraphs"])
    assert not any("The first path defines" in paragraph for paragraph in story["paragraphs"])
    assert not any("Together, those records keep release" in paragraph for paragraph in story["paragraphs"])
    assert story["supporting_records"] == []
    assert all(term not in json.dumps(story) for term in ("Radar", "Registry", "Atlas", "Compass"))
    assert "Product Story" in html
    assert "Storefront" in html
    assert "Checkout Orchestrator" in html
    assert "Catalog Boundary" in html
    assert "How the story becomes governance" not in html
    assert "Topology spine" not in html
    assert "Story root" not in html
    assert "Project not defined yet" not in html
    assert "Current orienting work" not in html
    assert "No active release detected" not in html
    assert prompt not in json.dumps(story, sort_keys=True)
    assert "checkout" in text
    assert "shopper" in text
    assert "storefront" in text
    assert "funding" not in text
    assert "underwriting" not in text
    assert any("Shopper advocate" == row[1] for row in payload["actors"])
    assert any("Commerce operator" == row[1] for row in payload["actors"])
    assert any("Payment risk reviewer" == row[1] for row in payload["actors"])
    assert any(
        row["claim"] == "Accepted product check" and row["value"] == "passed" and row["source"].endswith("accepted-project.v1.json")
        for row in payload["claim_evidence"]
    )


def test_greenfield_project_tab_participants_prefer_project_actors_over_internal_tribunal_concepts(
    tmp_path,
) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "plant sensor")
    proposal["_accepted_project"] = {
        "validation_gate": {
            "visible_actors": [
                {
                    "stable_role": "beneficiary_advocate",
                    "visible_actor": "Safety envelope",
                    "responsibility": "Protects the person receiving the value.",
                },
                {
                    "stable_role": "domain_operator",
                    "visible_actor": "Program Boundary operator",
                    "responsibility": "Checks workflow coherence.",
                },
                {
                    "stable_role": "evidence_owner",
                    "visible_actor": "Program Boundary proof owner",
                    "responsibility": "Decides proof strength.",
                },
            ]
        }
    }

    payload = project_intelligence_greenfield.build_greenfield_payload(proposal=proposal, repo_root=tmp_path)
    participants = list(payload["participants"])
    titles = [row[1] for row in participants]
    kickers = [row[0] for row in participants]

    assert "Plant owner advocate" in titles
    assert "Care routine operator" in titles
    assert "Plant safety reviewer" in titles
    assert "Safety envelope" not in titles
    assert "Program Boundary operator" not in titles
    assert "Program Boundary proof owner" not in titles
    assert all(kicker == "" for kicker in kickers)
    assert payload["participants_title"] == "Who participates?"
    assert "claim_evidence_title" not in payload
    assert payload["state_title"] == "Where does this stand?"
    assert payload["next_title"] in {"What should move next?", "Start implementation planning"}
    assert proposal["intent"]["title"] not in payload["participants_title"]


def test_greenfield_apply_runs_artifact_tribunal_for_each_atlas_diagram(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _apply_ready_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    original = greenfield_proposals.scaffold_mermaid_diagram.artifact_tribunal.run_governed_artifact_tribunal
    diagram_payloads: list[dict[str, object]] = []

    def capture_tribunal(*, artifact_kind: str, payload: Mapping[str, object]) -> object:
        if artifact_kind == "atlas_diagram":
            diagram_payloads.append(dict(payload))
        return original(artifact_kind=artifact_kind, payload=payload)

    monkeypatch.setattr(
        greenfield_proposals.scaffold_mermaid_diagram.artifact_tribunal,
        "run_governed_artifact_tribunal",
        capture_tribunal,
    )

    greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert len(diagram_payloads) == len(proposal["diagrams"])
    assert all(payload["watch_paths"] for payload in diagram_payloads)


def test_greenfield_normalization_preserves_host_authored_intelligence() -> None:
    proposal = greenfield_proposals.normalize_host_reasoned_proposal(_host_reasoned_ecommerce_proposal())
    child = next(row for row in proposal["backlog"] if row["title"] == "Define Storefront boundary")
    intelligence = child["domain_intelligence"]
    rendered = greenfield_proposals.render_domain_intelligence_section(intelligence)
    brief = proposal["project_brief"]
    project_intelligence = proposal["project_intelligence"]

    assert intelligence["family"] == "host_reasoned_project"
    actor_text = json.dumps(intelligence["actors"])
    assert "Shopper advocate" in actor_text
    assert "Commerce operator" in actor_text
    assert "Payment risk reviewer" in actor_text
    assert "Checkout proof reviewer" in actor_text
    assert "commerce" not in intelligence["family"]
    assert "Payment callback" not in rendered
    assert "Product story" in json.dumps(brief)
    assert "Actors and systems" in json.dumps(brief)
    assert len(brief["customization_options"]) >= 5
    assert len(brief["customization_prompts"]) >= 3
    assert len(brief["coding_readiness_gates"]) >= 4
    assert "Payment callback" not in "\n".join(project_intelligence["ontology"])
    assert set(PROJECT_INTELLIGENCE_LAYERS).issubset(project_intelligence.keys())
    assert len(project_intelligence["change_model"]) >= 2
    greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_normalization_does_not_invent_dependency_gaps() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1].pop("dependencies")
    proposal["backlog"][1].pop("interfaces")
    proposal["components"][0]["dependencies"] = []

    normalized = greenfield_proposals.normalize_host_reasoned_proposal(proposal)
    child = next(row for row in normalized["backlog"] if row["title"] == "Define Storefront boundary")
    component = next(row for row in normalized["components"] if row["component_id"] == "commerce-storefront")

    assert "dependencies" not in child
    assert "interfaces" not in child
    assert component["dependencies"] == []
    assert "planned boundary" not in json.dumps(normalized)
    assert "No upstream component dependency is claimed" not in json.dumps(normalized)


def test_greenfield_normalization_compacts_verbose_release_plan_label_to_selector() -> None:
    proposal = greenfield_proposals.normalize_host_reasoned_proposal(_host_reasoned_recipe_legacy_shape())

    assert proposal["release_plan"]["selector"] == "0.0.1"
    assert proposal["release_plan"]["label"] == "0.0.1"


def test_greenfield_normalization_splits_scalar_quality_fields() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    identity = proposal["backlog"][1]
    identity["success_metrics"] = (
        "Checkout recovery measured by browser proof; "
        "Order idempotency measured by replay contract tests"
    )
    identity.pop("recommended_first_slice")
    identity["validation"] = [
        "Browser proof passes for failed-checkout recovery.",
        "Replay proof blocks duplicate order creation.",
    ]
    proposal["release_plan"]["target_workstreams"] = "Define Storefront boundary, Define Catalog boundary"
    proposal["program"]["waves"][0].pop("validation_gate", None)
    proposal["program"]["waves"][0]["validation"] = [
        "Browse-to-cart proof passes",
        "Failed-payment recovery proof passes",
    ]

    normalized = greenfield_proposals.normalize_host_reasoned_proposal(proposal)
    normalized_identity = next(
        row for row in normalized["backlog"] if row["title"] == "Define Storefront boundary"
    )
    tribunal = greenfield_proposals.run_greenfield_tribunal(normalized, release_selector="0.0.1")

    assert normalized_identity["success_metrics"] == [
        "Checkout recovery measured by browser proof",
        "Order idempotency measured by replay contract tests",
    ]
    assert normalized_identity["recommended_first_slice"] == (
        "Browser proof passes for failed-checkout recovery. Replay proof blocks duplicate order creation."
    )
    assert normalized["release_plan"]["target_workstreams"] == ["Define Storefront boundary", "Define Catalog boundary"]
    assert normalized["program"]["waves"][0]["validation_gate"] == (
        "Browse-to-cart proof passes; Failed-payment recovery proof passes"
    )
    assert "['" not in normalized_identity["recommended_first_slice"]
    assert "['" not in normalized["program"]["waves"][0]["validation_gate"]
    greenfield_proposals.validate_host_reasoned_proposal(normalized)
    assert tribunal.passed


def test_greenfield_apply_scalar_wave_validation_dedupes_handoff_gates(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    identity = proposal["backlog"][1]
    identity["success_metrics"] = (
        "Checkout recovery measured by browser proof; "
        "Order idempotency measured by replay contract tests"
    )
    identity.pop("recommended_first_slice")
    identity["validation"] = [
        "Browser proof passes for failed-checkout recovery",
        "Replay proof blocks duplicate order creation",
    ]
    proposal["program"]["waves"][0].pop("validation_gate", None)
    proposal["program"]["waves"][0]["validation"] = [
        "Browse-to-cart proof passes",
        "Failed-payment recovery proof passes",
    ]

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    first_wave = result["program"]["waves"][0]
    joined_wave_gate = "Browse-to-cart proof passes; Failed-payment recovery proof passes"

    assert first_wave["exit_gate"] == joined_wave_gate
    assert first_wave["validation"] == [
        "Browse-to-cart proof passes",
        "Failed-payment recovery proof passes",
    ]
    assert joined_wave_gate not in result["next_steps"]["validation_gates"]
    assert result["next_steps"]["validation_gates"][-2:] == first_wave["validation"]


def test_greenfield_release_target_label_extracts_numeric_selector_from_custom_text() -> None:
    assert greenfield_proposals.greenfield_programs.compact_release_target_label("Recipe-sharing 0.0.1") == "0.0.1"
    assert greenfield_proposals.greenfield_programs.compact_release_target_label("launch candidate release target") == (
        "launch candidat..."
    )


def test_greenfield_apply_rejects_shallow_child_backlog_metrics(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1]["success_metrics"] = ["Component linked."]

    with pytest.raises(ValueError, match="at least two success_metrics"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_control_plane_terms_in_consumer_product_fields(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1]["success_metrics"][0] = "The checkout boundary appears in Registry and Atlas."
    proposal["components"][0]["description"] = "The storefront succeeds when Radar and Compass expose the work."

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    message = str(excinfo.value)
    assert "greenfield public product content leaks Odylith control-plane term `Radar`" in message
    assert "greenfield public product content leaks Odylith control-plane term `Registry`" in message
    assert "greenfield public product content leaks Odylith control-plane term `Atlas`" in message
    assert "greenfield public product content leaks Odylith control-plane term `Compass`" in message


def test_greenfield_apply_reports_validation_issues_in_one_batch(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1].pop("problem")
    proposal["backlog"][2]["success_metrics"] = ["Too shallow."]
    proposal["components"][0]["responsibility"] = "UI"

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    message = str(excinfo.value)
    assert "greenfield proposal validation failed with" in message
    assert "backlog row 2 `problem` must be non-empty" in message
    assert "backlog row 3 must include at least two success_metrics" in message
    assert "component row 1 `responsibility` must contain at least 6 meaningful words" in message
    assert "auto-enrichment:" in message
    assert "needs operator/proposal input:" in message


def test_greenfield_validation_rejects_missing_project_first_brief(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "warehouse dispatch planning app")
    proposal.pop("project_brief")

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    assert "proposal `project_brief` must be an object" in str(excinfo.value)


def test_greenfield_validation_rejects_missing_project_intelligence(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "warehouse dispatch planning app")
    proposal.pop("project_intelligence")

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    assert "proposal `project_intelligence` must be an object" in str(excinfo.value)


def test_project_brief_blocks_coding_rush_without_domain_scaffold(tmp_path) -> None:
    proposal = _apply_ready_greenfield_fixture(tmp_path, "warehouse dispatch planning app")
    brief = proposal["project_brief"]
    rendered = greenfield_proposals.format_proposal_text(proposal)

    assert "Simulation and hardware boundary" not in json.dumps(brief)
    assert "safety envelope" not in json.dumps(brief)
    assert "Project requirements" in rendered
    assert "Coding starts only after the accepted project story" in rendered
    assert rendered.index("Project requirements") < rendered.index("Backlog proposal")
    assert "greenfield create --repo-root ." in rendered
    assert "Warehouse Dispatch Planning App Operator Workspace" not in rendered


def test_greenfield_apply_rejects_shallow_component_responsibility(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["components"][0]["responsibility"] = "UI stuff."

    with pytest.raises(ValueError, match="responsibility"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_missing_security_compliance_posture(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal.pop("security_compliance")

    with pytest.raises(ValueError, match="security_compliance"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_backlog_overrides_preserve_child_specific_sections() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    child = next(row for row in proposal["backlog"] if row["title"].startswith("Define "))
    args = argparse.Namespace(
        problem="parent",
        customer="parent",
        opportunity="parent",
        product_view="parent",
        success_metrics="parent",
        domain_risk="parent domain risk",
        security_posture="parent security posture",
        priority="P1",
        sizing="M",
        complexity="Medium",
        ordering_rationale="parent",
        section_overrides_by_title=greenfield_proposals._backlog_section_overrides(proposal),
    )

    resolved = backlog_authoring._title_specific_args(title=child["title"], args=args)

    assert resolved.problem == child["problem"]
    assert resolved.product_view == child["product_view"]
    assert child["success_metrics"][0] in resolved.success_metrics


def test_greenfield_apply_bootstraps_first_release_selector(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    refresh_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        greenfield_proposals.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **kwargs: refresh_calls.append(dict(kwargs)),
    )
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["release_plan"].pop("selector")

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="",
    )

    registry = json.loads((tmp_path / "odylith/radar/source/releases/releases.v1.json").read_text(encoding="utf-8"))
    events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8")
    system_context = (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").read_text(encoding="utf-8")
    program_waves = (tmp_path / "odylith/atlas/source/commerce-launch-program-waves.mmd").read_text(encoding="utf-8")
    execution_program = json.loads(
        (tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json").read_text(encoding="utf-8")
    )
    atlas_catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    parent_idea = Path(result["backlog"][0]["idea_path"]).read_text(encoding="utf-8")
    child_idea = Path(result["backlog"][1]["idea_path"]).read_text(encoding="utf-8")
    storefront_spec = (
        tmp_path / "odylith/registry/source/components/commerce-storefront/CURRENT_SPEC.md"
    ).read_text(encoding="utf-8")
    component_registry = json.loads(
        (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    )
    assert result["release_bootstrap"]["created"] is True
    assert registry["aliases"]["0.0.1"] == "release-commerce-launch-first"
    assert registry["aliases"]["current"] == "release-commerce-launch-first"
    assert registry["releases"][0]["name"] == "0.0.1"
    assert len(result["backlog"]) == 3
    assert len(result["components"]) == 3
    assert len(result["diagrams"]) == 2
    assert result["validation_gate"]["status"] == "passed"
    assert result["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert result["dashboard_refresh"]["view"] == "odylith/index.html?tab=project"
    assert refresh_calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surfaces": ("radar", "registry", "atlas", "compass", "tooling_shell"),
            "operation_label": "Greenfield apply dashboard visibility",
        }
    ]
    assert result["program"]["created"] is True
    assert result["program"]["umbrella_id"] == "B-001"
    assert len(result["program"]["waves"]) == 2
    assert result["program"]["waves"][0]["wave_id"] == "W1"
    assert result["program"]["waves"][0]["primary_workstreams"] == ["B-002"]
    assert result["program"]["waves"][1]["wave_id"] == "W2"
    assert result["program"]["waves"][1]["primary_workstreams"] == ["B-003"]
    assert execution_program["waves"][0]["label"] == "Checkout spine"
    assert execution_program["waves"][0]["primary_workstreams"] == ["B-002"]
    assert execution_program["waves"][1]["label"] == "Catalog integrity"
    assert execution_program["waves"][1]["primary_workstreams"] == ["B-003"]
    assert result["release_bootstrap"]["release"]["version"] == "0.0.1"
    assert result["release_bootstrap"]["release"]["tag"] == "v0.0.1"
    assert result["release_bootstrap"]["release"]["name"] == "0.0.1"
    assert result["release_target"]["workstream_ids"] == ["B-001", "B-002"]
    release_payload, release_errors, _release_state = release_planning_view_model.build_release_view_from_repo(
        repo_root=tmp_path,
        idea_specs=None,
    )
    assert release_errors == []
    assert release_payload["current_release"]["release_id"] == "release-commerce-launch-first"
    assert release_payload["current_release"]["display_label"] == "0.0.1"
    assert release_payload["current_release"]["active_workstreams"] == ["B-001", "B-002"]
    assert build_traceability_graph.main(["--repo-root", str(tmp_path)]) == 0
    traceability_graph = json.loads((tmp_path / "odylith/radar/traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert traceability_graph["current_release"]["release_id"] == "release-commerce-launch-first"
    assert traceability_graph["current_release"]["active_workstreams"] == ["B-001", "B-002"]
    assert result["backlog_topology"] == [
        Path(result["backlog"][0]["idea_path"]).relative_to(tmp_path).as_posix(),
        Path(result["backlog"][1]["idea_path"]).relative_to(tmp_path).as_posix(),
        Path(result["backlog"][2]["idea_path"]).relative_to(tmp_path).as_posix(),
    ]
    assert "Payment sandbox" in system_context
    assert "Order reliability" in program_waves
    assert system_context != program_waves
    assert "related_diagram_ids: D-001,D-002" in parent_idea
    assert "related_diagram_ids: D-001,D-002" in child_idea
    assert "## Impacted Components" in child_idea
    assert "`commerce-storefront`" in child_idea
    assert any(result["backlog"][1]["idea_path"] in row["related_backlog"] for row in atlas_catalog["diagrams"])
    storefront = next(row for row in component_registry["components"] if row["component_id"] == "commerce-storefront")
    assert storefront["workstreams"] == ["B-002"]
    assert storefront["diagrams"] == []
    assert storefront["what_it_is"].startswith("Storefront is planned as an application boundary")
    assert "It owns browse, cart entry, checkout entry, and user-facing errors" in storefront["what_it_is"]
    assert "responsible for" not in storefront["what_it_is"]
    assert "It owns browse, cart entry, checkout entry, and user-facing errors" in storefront_spec
    assert "| Workstreams | `B-002` |" in storefront_spec
    assert "| Diagrams | none yet |" in storefront_spec
    assert "Browser smoke proof for browse-to-cart and failed-checkout messaging" in storefront_spec
    assert result["memory"]["recorded"] is True
    assert result["memory"]["event"]["source"] == "domain-intelligence"
    assert '"release_id": "release-commerce-launch-first"' in events


def test_greenfield_apply_reuses_existing_diagram_ids_for_backlog_traceability(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    atlas_catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    atlas_catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith.diagrams.v1",
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "slug": "commerce-launch-system-context",
                        "title": "Old Context",
                    },
                    {
                        "diagram_id": "D-002",
                        "slug": "commerce-launch-program-waves",
                        "title": "Old Waves",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_host_reasoned_ecommerce_proposal(),
        confirm=True,
        release_selector="0.0.1",
    )

    parent_idea = Path(result["backlog"][0]["idea_path"]).read_text(encoding="utf-8")
    child_idea = Path(result["backlog"][1]["idea_path"]).read_text(encoding="utf-8")
    atlas_catalog = json.loads(atlas_catalog_path.read_text(encoding="utf-8"))

    assert result["diagrams"] == ["D-001", "D-002"]
    assert {row["diagram_id"] for row in atlas_catalog["diagrams"]} == {"D-001", "D-002"}
    assert "related_diagram_ids: D-001,D-002" in parent_idea
    assert "related_diagram_ids: D-001,D-002" in child_idea
    assert "D-003" not in parent_idea
    assert "D-003" not in child_idea
    assert build_traceability_graph.main(["--repo-root", str(tmp_path)]) == 0
    traceability_graph = json.loads((tmp_path / "odylith/radar/traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert not any("not found in catalog" in warning for warning in traceability_graph["warnings"])


def test_greenfield_apply_rejects_legacy_recipe_shape_without_host_authored_project_intelligence(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(ValueError, match="project_intelligence|domain_intelligence|program parent"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_recipe_legacy_shape(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()


def test_greenfield_apply_rejects_missing_host_authored_program_parent(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(ValueError, match="program parent|project_intelligence|domain_intelligence"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_crispr_without_parent(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/radar/source/programs").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()


def test_greenfield_apply_writes_host_authored_component_specs(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _apply_ready_greenfield_fixture(tmp_path, "Build an ecommerce checkout recovery product")

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    spec_root = tmp_path / "odylith/registry/source/components"
    storefront_spec = (spec_root / "commerce-storefront/CURRENT_SPEC.md").read_text(encoding="utf-8")
    checkout_spec = (spec_root / "commerce-checkout/CURRENT_SPEC.md").read_text(encoding="utf-8")
    catalog_spec = (spec_root / "commerce-catalog/CURRENT_SPEC.md").read_text(encoding="utf-8")
    atlas_catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))

    assert result["validation_gate"]["status"] == "passed"
    assert [row["label"] for row in proposal["components"]] == [
        "Storefront",
        "Checkout Orchestrator",
        "Catalog Boundary",
    ]
    assert "It owns browse, cart entry, checkout entry, and user-facing errors" in storefront_spec
    assert "It owns payment handoff, order draft, idempotency, and recovery boundaries" in checkout_spec
    assert "It owns product facts, price snapshots, inventory visibility, and merchandising review" in catalog_spec
    assert "| Workstreams | `B-002` |" in storefront_spec
    assert "| Workstreams | `B-002` |" in checkout_spec
    assert "| Workstreams | `B-003` |" in catalog_spec
    assert "Use `B-002` (Define Storefront boundary) as the implementation-plan anchor" in storefront_spec
    assert "Use `B-003` (Define Catalog boundary) as the implementation-plan anchor" in catalog_spec
    assert "Use `B-002` (Define Storefront boundary) as the implementation-plan anchor" not in catalog_spec
    assert "## Component Role" in storefront_spec
    assert "## Interaction Boundary" in storefront_spec
    assert "## Runtime Boundary" in checkout_spec
    assert "## Runtime Boundary" in catalog_spec
    assert "## Storefront Interaction Boundary" not in storefront_spec
    assert "## Checkout Orchestrator Runtime Boundary" not in checkout_spec
    assert "## Catalog Boundary Runtime Boundary" not in catalog_spec
    for text in (storefront_spec, checkout_spec, catalog_spec):
        assert "Experience Boundary" not in text
        assert "registered through `odylith component register`" not in text
        assert "first operator-visible workflow, view or command entrypoint" not in text
        assert "Source-backed runtime behavior until implementation proof lands" not in text
        assert "Production readiness, storage ownership, or external-provider guarantees" not in text
        assert "Starting implementation without a named product spine" not in text
        assert "Security, privacy, accessibility, and operational risks can be under-modeled" not in text
        assert "Security posture starts with authentication or operator access boundaries" not in text
        assert "Policy posture tracks privacy, retention, accessibility" not in text
        assert "The first workstream has a technical plan" not in text
        assert "The workflow boundary appears in Registry and Atlas" not in text
        assert "Registry spec" not in text
        assert "Compass projection" not in text
        assert "Radar lane" not in text
        assert "| Diagrams | `D-001`" not in text
        assert "R1." not in text
        assert "odylith_assumption" not in text
    assert storefront_spec != checkout_spec
    assert checkout_spec != catalog_spec
    assert {row["link_state"] for row in atlas_catalog["diagrams"]} == {"atlas_first_draft"}


def test_greenfield_component_dependency_lines_are_grammatical_from_component_rows() -> None:
    lookup = greenfield_proposals._component_dependency_lookup(
        [
            {
                "component_id": "observation-ledger",
                "label": "Observation Ledger",
                "responsibility": "Capture and serve append-only observations.",
            },
            {
                "component_id": "evidence-linker",
                "label": "Evidence Linker",
                "responsibility": "Bind observations to claims and produce signed evidence bundles.",
            },
            {
                "component_id": "condition-deriver",
                "label": "Condition Deriver",
                "responsibility": "Compute the current condition from the evidence trail.",
            },
        ]
    )

    lines = greenfield_proposals._component_dependency_lines(
        ["observation-ledger", "evidence-linker", "condition-deriver"],
        lookup=lookup,
    )

    assert "Depends on Observation Ledger for capturing and serving append-only observations" in lines
    assert "Depends on Evidence Linker for binding observations to claims and producing signed evidence bundles" in lines
    assert "Depends on Condition Deriver for computing the current condition from the evidence trail" in lines


def test_greenfield_apply_cli_prints_operator_handoff(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_host_reasoned_ecommerce_proposal()), encoding="utf-8")

    rc = greenfield_proposals.main(
        ["apply", "--repo-root", str(tmp_path), "--proposal-file", str(proposal_path), "--confirm", "--release", "0.0.1"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "- project-first workstream: B-001 Govern Commerce Launch System" in out
    assert "- project story: odylith/index.html?tab=project" in out
    assert "- workstream detail: odylith/radar/radar.html?view=plan&workstream=B-001" in out
    assert "- project gate: review direction choices and readiness gates before opening a technical plan; do not edit source from this closeout" in out
    assert "- current project lane: wave Checkout spine | release 0.0.1" in out
    assert "- choose before coding:" in out
    assert "- coding readiness gates:" in out
    assert "- future first implementation lane after gates: B-002 Define Storefront boundary" in out
    assert "- operator handoff:" in out
    assert "./.odylith/bin/odylith validate plan-workstream-binding --repo-root ." in out


def test_greenfield_prompt_paths_do_not_expose_legacy_apply_ready_scaffold(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a home automation product with a physical device and a care outcome.",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert "Product Intent Confirmation needed" in out
    assert "Host reasoning task" in out
    assert "raw greenfield intent" not in out

    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a home automation product with a physical device and a care outcome.",
            "--confirm-intent",
        ]
    )
    out = capsys.readouterr().out

    assert rc == 2
    assert "requires --intent-file" in out
    assert "will not write records from a thin prompt" in out
    assert "internal apply payload" not in out
    assert "active-proposal.v1.json" not in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []


def test_greenfield_create_cli_applies_confirmed_prompt(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    _write_confirmed_intent(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "greenfield create wrote confirmed proposal" in out
    assert "- validation gate: passed" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").is_file()
    accepted = (tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8")
    assert "Permit file registry" in accepted
    assert "Municipal Permit Review Workspace Workflow Service" not in accepted
    assert (tmp_path / "odylith/registry/source/component_registry.v1.json").is_file()
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_create_cli_requires_confirmation_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "warehouse dispatch planning app",
            "--release",
            "0.0.1",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    assert "greenfield create requires --confirm" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_create_cli_requires_confirmed_intent_file_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a greenfield proposal for a municipal permit review workspace",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    assert "requires --intent-file" in out
    assert "will not write records from a thin prompt" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_namespaces_partial_project_diagram_slugs_before_scaffold(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    atlas_catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    atlas_catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith.diagrams.v1",
                "diagrams": [{"diagram_id": "D-001", "slug": "checkout-flow"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["slug"] = "checkout-flow"
    for row in proposal["backlog"]:
        if "related_diagram_slugs" in row:
            row["related_diagram_slugs"] = [
                "checkout-flow" if value == "commerce-launch-system-context" else value
                for value in row["related_diagram_slugs"]
            ]

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    atlas_catalog = json.loads(atlas_catalog_path.read_text(encoding="utf-8"))
    assert result["validation_gate"]["status"] == "passed"
    assert "checkout-flow" in {row["slug"] for row in atlas_catalog["diagrams"]}
    assert "commerce-launch-system-checkout-flow" in {row["slug"] for row in atlas_catalog["diagrams"]}
    assert (tmp_path / "odylith/atlas/source/commerce-launch-system-checkout-flow.mmd").is_file()


def test_greenfield_apply_rolls_back_partial_writes_when_late_step_fails(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    original_index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")

    def fail_scaffold(**_kwargs: object) -> tuple[int, list[str]]:
        return 1, ["FAILED: synthetic scaffold failure"]

    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram, "scaffold_diagram", fail_scaffold)

    with pytest.raises(RuntimeError, match="synthetic scaffold failure"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8") == original_index
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/radar/source/releases").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").exists()


def test_greenfield_apply_rolls_back_generated_surfaces_when_refresh_fails(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    original_index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")

    def fail_refreshes(**_kwargs: object) -> None:
        _write(tmp_path / "odylith/radar/radar.html", "partial dashboard\n")
        _write(tmp_path / "odylith/runtime/delivery_intelligence.v4.json", "{}\n")
        raise RuntimeError("synthetic dashboard refresh failure")

    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", fail_refreshes)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="synthetic dashboard refresh failure"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8") == original_index
    assert not (tmp_path / "odylith/radar/radar.html").exists()
    assert not (tmp_path / "odylith/runtime/delivery_intelligence.v4.json").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").exists()


def test_greenfield_transaction_restores_symlinked_snapshot_root_without_traversal(tmp_path) -> None:
    external_radar = tmp_path / "external-radar"
    external_radar.mkdir()
    _write(external_radar / "outside.md", "external truth\n")
    radar_link = tmp_path / "odylith/radar"
    radar_link.parent.mkdir(parents=True)
    try:
        radar_link.symlink_to(external_radar, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            radar_link.unlink()
            _write(tmp_path / "odylith/radar/partial.md", "partial write\n")
            raise RuntimeError("synthetic failure")

    assert radar_link.is_symlink()
    assert radar_link.resolve() == external_radar.resolve()
    assert (external_radar / "outside.md").read_text(encoding="utf-8") == "external truth\n"
    assert not (tmp_path / "odylith/radar/partial.md").exists()


def test_greenfield_transaction_restores_nested_symlink_without_copying_target(tmp_path) -> None:
    radar_root = tmp_path / "odylith/radar"
    radar_root.mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside\n", encoding="utf-8")
    nested_link = radar_root / "linked.txt"
    try:
        nested_link.symlink_to(outside_file)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            nested_link.unlink()
            nested_link.write_text("regular replacement\n", encoding="utf-8")
            raise RuntimeError("synthetic failure")

    assert nested_link.is_symlink()
    assert nested_link.resolve() == outside_file.resolve()
    assert outside_file.read_text(encoding="utf-8") == "outside\n"


def test_greenfield_apply_requires_confirmation(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)

    with pytest.raises(ValueError, match="--confirm is required"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=False,
            release_selector="0.0.1",
        )


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    def noisy_refresh(**_kwargs: object) -> None:
        print("refresh progress that must not contaminate JSON stdout", flush=True)
        os.write(1, b"fd-level refresh progress must not contaminate JSON stdout\n")

    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", noisy_refresh)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_host_reasoned_ecommerce_proposal()), encoding="utf-8")

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-file",
            str(proposal_path),
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["mode"] == "applied"
    assert payload["atlas_scaffold_logs"]
    assert payload["memory"]["recorded"] is True
    assert payload["memory"]["event"]["source"] == "domain-intelligence"
    assert payload["validation_gate"]["status"] == "passed"
    assert "tribunal" not in payload
    assert all("tribunal" not in line.casefold() for line in payload["atlas_scaffold_logs"])
    assert all("validation_gate" in row and "tribunal" not in row for row in payload["components"])
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert payload["dashboard_refresh"]["view"] == "odylith/index.html?tab=project"
    assert payload["release_target"]["release_id"] == "release-commerce-launch-first"
    assert payload["operator_output"] == [
        "refresh progress that must not contaminate JSON stdout",
        "fd-level refresh progress must not contaminate JSON stdout",
    ]


def test_greenfield_apply_json_error_is_machine_clean(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-json",
            "{not-json",
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["mode"] == "error"
    assert "Expecting property name enclosed in double quotes" in payload["error"]
