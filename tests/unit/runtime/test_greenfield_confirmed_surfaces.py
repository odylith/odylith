from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common import mermaid_text
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues


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
    assert "prepare user plays a roughly<br/>30-second monophonic line" in sequence["mermaid_source"]
    assert "show outcome, evidence, and next action" in sequence["mermaid_source"]
    assert "A1->>C1: User opens LiveScore and taps<br/>Record" in sequence["mermaid_source"]
    assert "A1->>C3: 2" not in sequence["mermaid_source"]
    assert "<br/>" in sequence["mermaid_source"]
    assert "**" not in sequence["mermaid_source"]
    assert "The first complete path" not in sequence["mermaid_source"]
    assert "…" not in sequence["mermaid_source"]
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
        (
            "Owns microphone or line-in capture and normalization. Reviewers need to see what this boundary receives, "
            "produces, records, and makes available next."
        ),
        (
            "Owns the product responsibility to perform frame-level pitch tracking. Reviewers need to see the inputs, rule version, result, "
            "and downstream decision that depended on it."
        ),
        (
            "Owns the product responsibility to engrave the score model to PDF and MusicXML. Reviewers need to see the inputs, rule version, result, "
            "and downstream decision that depended on it."
        ),
    ]


def test_confirmed_greenfield_noun_phrase_responsibilities_stay_grammatical() -> None:
    components = confirmed_components(
        label="Operations Review Workspace",
        label_slug="operations-review-workspace",
        internal_systems=[
            "Status dashboard — status dashboard for operator review, queue health, and decision history.",
            "Review coordinator — coordinates follow-up actions, reviewer handoff, and blocked-state recovery.",
        ],
    )
    rows = confirmed_diagrams(
        label="Operations Review Workspace",
        diagram_slugs={
            "context": "operations-context",
            "sequence": "operations-sequence",
            "state_evidence": "operations-state-evidence",
            "component_boundaries": "operations-component-boundaries",
            "ownership": "operations-ownership",
            "proof_review": "operations-proof-review",
        },
        components=components,
        human_actors=["Operator"],
        internal_systems=["Status dashboard", "Review coordinator"],
    )
    encoded = json.dumps({"components": components, "diagrams": rows})
    first_description = rows[0]["components"][0]["description"]

    assert "statu dashboard" not in encoded
    assert "responsibility to status dashboard" not in encoded
    assert components[0]["responsibility"] == "Status dashboard for operator review, queue health, and decision history"
    assert first_description == (
        "Presents status dashboard for operator review, queue health, and decision history to users and captures "
        "the action or decision the product needs next. Reviewers need to see what the user saw, submitted, "
        "corrected, or approved and which product state changed after that action."
    )
    assert "Coordinates follow-up actions, reviewer handoff, and blocked-state recovery" in encoded
    assert "each responsibility transfer, failure state, recovery action, and final outcome" in encoded


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
    assert "A->>C1: this is a very long message<br/>label with semicolon" in normalized
    assert "Note over A,C1: This note carries a very long<br/>accepted path explanation that<br/>previously leaked outside" in normalized
    assert "…" not in normalized


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
- Reviewer dashboard and export — shows a reviewer the item state, borrower, approval, return condition, and audit trail in one readable package.
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
    assert "Reviewer Dashboard" not in encoded
    assert "Review Dashboard and Export" in encoded
    assert "Volunteer Equipment Checkout Reviewer" in encoded
    assert not greenfield_quality_issues(proposal)
    assert "owns captures" not in encoded
    assert "owns shows" not in encoded
    assert "Shows which items can be borrowed now" in encoded
    context = next(row for row in proposal["diagrams"] if row["title"] == "System Context View")
    assert "<br/>" in context["mermaid_source"]
    for row in proposal["diagrams"]:
        for component in row["components"]:
            assert "accepted first release path" not in component["description"]
            assert "owns owns" not in component["description"].casefold()
            assert component["description"].endswith(".")
