from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.common import mermaid_text
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract import boundary_from_contract
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import component_kind_echo_safe_phrase
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import contract_focus
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import proof_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import confirmed_project_brief
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import confirmed_system_description
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import confirmed_system_name
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import expand_internal_system_rows
from odylith.runtime.domain_intelligence import greenfield_confirmed_system_rows
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import flow_label
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority


def test_component_proof_phrases_do_not_echo_short_component_kind_labels() -> None:
    assert component_kind_echo_safe_phrase(label="Review Queue", phrase="queue state result") == "review state result"
    assert component_kind_echo_safe_phrase(label="Queue", phrase="queue state result") == "state result"
    rows = proof_rows(
        label="Review Queue",
        object_list="queue state",
        critical="queue state",
        input_focus="request input",
        output_focus="queue state result",
        sibling_label="Response History Service",
        sibling_focus="response history state",
    )

    assert "Successful path evidence for Review Queue: review state result" in rows[0]
    assert "Review Queue: queue" not in " ".join(rows)


def test_component_proof_focus_skips_action_modified_result_noun_piles() -> None:
    output_focus = contract_focus(
        object_list="exception blocked state, tracker exception, failure reason ledger, use tracker state",
        action_terms=(),
        fallback="downstream state",
        role="output",
    )
    rows = proof_rows(
        label="Exception and Blocked Use Tracker",
        object_list="exception blocked state, use tracker state",
        critical="exception blocked state",
        input_focus="exception reason",
        output_focus=output_focus,
        sibling_label="Review Signoff Ledger",
        sibling_focus="review signoff state",
        preferred_focus="exception blocked state",
    )
    rendered = " ".join([output_focus, *rows]).casefold()

    assert "use tracker state result" not in rendered
    assert "use tracker state evidence" in rendered
    assert "successful path evidence for exception and blocked use tracker: exception blocked state" in rendered
    assert generated_public_copy_issues("component proof rows", rows) == ()


def test_component_boundary_strips_leading_ownership_verbs_from_owned_state() -> None:
    boundary = boundary_from_contract(
        "Evidence Gap Tracker",
        {"owned_state": "owns evidence gap tracker state, local blockers, and recovery context"},
    )

    assert boundary == "Evidence Gap Tracker owns evidence gap tracker state, validation evidence, and local handoff decisions."
    assert "owns owns" not in boundary.casefold()


def test_state_object_descriptor_avoids_adjacent_object_object_copy() -> None:
    state = "Object Loan Condition Case"
    components = [
        {"component_id": "loan-case-intake", "label": "Loan Case Intake Register Service", "active_in_release": True},
        {"component_id": "condition-evidence", "label": "Condition Evidence Ledger", "active_in_release": True},
    ]

    brief = confirmed_project_brief(
        label="Museum Loan Condition Review",
        prompt="Draft a greenfield proposal for a museum loan condition review workspace.",
        release="0.0.1",
        state_object=state,
        evidence_record="Condition Evidence Record",
        human_actors=["Collections Registrar"],
        internal_systems=["Loan case intake register", "Condition evidence ledger"],
    )
    diagrams = confirmed_diagrams(
        label="Museum Loan Condition Review",
        components=components,
        diagram_slugs={
            "context": "context",
            "sequence": "sequence",
            "state_evidence": "state-evidence",
            "component_boundaries": "component-boundaries",
            "ownership": "ownership",
            "proof_review": "proof-review",
        },
        state_object=state,
        evidence_record="Condition Evidence Record",
        human_actors=["Collections Registrar"],
        proof_boundary="Release proof keeps the condition report reviewable.",
    )
    rendered = json.dumps({"brief": brief, "diagrams": diagrams})

    assert "versioned tracked state: object loan condition case" in rendered
    assert "Tracked state<br/>Object Loan Condition Case" in rendered
    assert "state object: object" not in rendered.casefold()
    assert "state object<br/>object" not in rendered.casefold()


def test_confirmed_diagrams_wrap_long_host_derived_flowchart_labels() -> None:
    rows = confirmed_diagrams(
        label="Multi Party Security Disclosure Council",
        diagram_slugs={
            "context": "security-context",
            "sequence": "security-sequence",
            "state_evidence": "security-state-evidence",
            "component_boundaries": "security-component-boundaries",
            "ownership": "security-ownership",
            "proof_review": "security-proof-review",
        },
        components=[
            {
                "component_id": "coordinated-disclosure-intake",
                "label": "Coordinated Security Disclosure Intake and Cross Organization Triage Service",
                "active_in_release": True,
            },
            {
                "component_id": "embargo-resolution-evidence",
                "label": "Embargo Resolution Evidence Custody and Reviewer Signoff Ledger",
                "active_in_release": True,
            },
            {
                "component_id": "publication-decision-control",
                "label": "Public Advisory Publication Decision Control and Partner Notification Desk",
                "active_in_release": True,
            },
        ],
        state_object=(
            "Coordinated disclosure case state for vulnerability intake, embargo decisioning, partner review, "
            "and public advisory readiness"
        ),
        evidence_record=(
            "Embargo resolution evidence record linking finder report, affected partner response, reviewer decision, "
            "and publication approval"
        ),
        proof_boundary=(
            "A release is acceptable only when security, legal, partner, and publication reviewers can trace the "
            "accepted disclosure path without losing evidence custody."
        ),
        human_actors=["Disclosure coordinator", "Security reviewer"],
        external_systems=["External finder report with affected partner references"],
        non_goals=["Automated personalized notification campaigns remain outside the accepted first release."],
    )

    for row in rows:
        validated_mermaid_source(row)


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
    assert sequence["kind"] == "flowchart"
    assert sequence["mermaid_source"].startswith("flowchart LR")
    assert 'actor["Solo performer"]' in sequence["mermaid_source"]
    assert 'C1["Audio Capture and<br/>Pre-processing Service"]' in sequence["mermaid_source"]
    assert 'S1["Open LiveScore"]' in sequence["mermaid_source"]
    assert 'S2["Tap Record"]' in sequence["mermaid_source"]
    assert "roughly 30-second<br/>monophonic line" in sequence["mermaid_source"]
    assert "downloadable PDF<br/>and MusicXML" in sequence["mermaid_source"]
    assert "state, evidence, and next action stay visible" in sequence["mermaid_source"]
    assert "sequenceDiagram" not in sequence["mermaid_source"]
    assert "participant C" not in sequence["mermaid_source"]
    assert "C4-" not in sequence["mermaid_source"]
    assert "<br/>" in sequence["mermaid_source"]
    assert "**" not in sequence["mermaid_source"]
    assert "User action" not in sequence["mermaid_source"]
    assert "Show outcome:" not in sequence["mermaid_source"]
    assert "The first complete path" not in sequence["mermaid_source"]
    assert "…" not in sequence["mermaid_source"]
    assert "component cards to decode" not in copy
    assert "User opens LiveScore" not in sequence["summary"]
    assert "This sequence shows what the first release must prove from Solo performer (primary)" in sequence["summary"]
    assert "solo monophonic instrument single take" in sequence["summary"]
    assert sequence["read_guide"].startswith("Start with the first product action.")
    assert "component handoff" not in sequence["read_guide"]
    assert "component; messages are calls" not in sequence["read_guide"]
    assert "State object" in state_evidence["mermaid_source"]
    assert "Evidence record" in state_evidence["mermaid_source"]
    assert "release boundary" in boundary["mermaid_source"]
    assert ownership["summary"].startswith("Trace release ownership")
    assert "polyphony" not in ownership["summary"]
    assert proof_review["summary"].startswith("Show which first-path result")
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
            "Owns microphone or line-in capture and normalization. The Audio Capture and Pre-processing Service boundary "
            "must show what this boundary receives, produces, records, and makes available next."
        ),
        (
            "Owns product responsibility to perform frame-level pitch tracking. The Pitch and Onset Detection Engine boundary "
            "must show inputs, rule versions, results, and downstream decisions that depended on it."
        ),
        (
            "Owns product responsibility to engrave the score model to PDF and MusicXML. The Score Renderer Service boundary "
            "must show inputs, rule versions, results, and downstream decisions that depended on it."
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
        "the action or decision the product needs next. The Status Dashboard boundary must show what the user saw, submitted, "
        "corrected, or approved and which product state changed after that action."
    )
    assert "Coordinates follow-up actions, reviewer handoff, and blocked-state recovery" in encoded
    assert "responsibility transfers, failure states, recovery actions, and final outcomes" in encoded


def test_parenthetical_system_descriptor_stays_one_component_row() -> None:
    rows = expand_internal_system_rows(
        ["Trend and correlation view (pattern over time, action-to-outcome signal)"],
        context_text="",
    )

    assert len(rows) == 1
    assert rows[0].startswith("Trend and Correlation View — ")
    assert "pattern over time" in rows[0]
    assert "action-to-outcome signal" in rows[0]
    assert "Correlation View (pattern Over" not in rows[0]


def test_purpose_clause_system_row_keeps_purpose_out_of_component_identity() -> None:
    rows = expand_internal_system_rows(
        ["Reminder/streak nudge to sustain the daily habit"],
        context_text="",
    )
    components = confirmed_components(
        label="Habit Tracker",
        label_slug="habit-tracker",
        internal_systems=rows,
    )

    assert rows == ["Reminder and Streak Nudge — supports the daily habit"]
    assert components[0]["label"] == "Reminder and Streak Nudge Service"
    assert components[0]["component_id"] == "reminder-and-streak-nudge"
    assert "Maintains sustain" not in json.dumps(components)
    assert "helps sustain" not in json.dumps(components)
    assert "to Sustain" not in components[0]["label"]


def test_ownership_clause_system_row_keeps_responsibility_out_of_component_identity() -> None:
    row = "Request intake register owns request identity, documents, and submitted state"
    rows = expand_internal_system_rows([row], context_text="")
    components = confirmed_components(
        label="Review Workspace",
        label_slug="review-workspace",
        internal_systems=rows,
    )

    assert confirmed_system_name(row) == "Request intake register"
    assert confirmed_system_description(row).startswith("owns request identity")
    assert rows[0].startswith("Request Intake Register — owns request identity")
    assert components[0]["label"] == "Request Intake Register Service"
    assert "Owns Request Identity" not in components[0]["label"]


def test_short_system_description_uses_direct_preservation_prose() -> None:
    description = greenfield_confirmed_system_rows._contextualized_system_body(  # noqa: SLF001
        name="Recipe Sequencer",
        body="tracks",
        context_text="",
    )

    assert description == "keeps recipe sequencer state, validation result, blocker state, and handoff evidence together"
    assert "while keeping" not in description


def test_long_system_descriptors_do_not_become_component_identity() -> None:
    rows = expand_internal_system_rows(
        [
            "Medication and titration-schedule model that knows dose steps and timing",
            "Weight and side effect tracking with trend views over time",
        ],
        context_text="",
    )
    components = confirmed_components(
        label="Medication Companion",
        label_slug="medication-companion",
        internal_systems=rows,
    )
    encoded = json.dumps(components)

    assert components[0]["component_id"] == "medication-and-titration-schedule-model"
    assert components[0]["label"] == "Medication and Titration Schedule Model Service"
    assert components[0]["source_system_description"] == "knows dose steps and timing"
    assert components[1]["component_id"] == "weight-and-side-effect-tracking"
    assert components[1]["label"] == "Weight and Side Effect Tracking Service"
    assert components[1]["source_system_description"] == "supports trend views over time"
    assert "That Knows" not in encoded
    assert "with Trend Views" not in encoded


def test_confirmed_personal_pattern_artifacts_do_not_leak_placeholder_labels(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """Pattern Relief Notebook

Product story
A person tracking recurring discomfort wants to understand which self-care actions appear to help over time. The product turns scattered daily notes into a small personal feedback loop: record how the day felt, record what action was tried, and review the pattern before deciding what to try next.

State object
The central thing the product tracks is a person's comfort timeline: a sequence of dated entries, each holding a rating, contributing factors, and the self-care actions tried. Around that sit saved routines and derived trends that connect actions to outcomes.

First complete path
A new user logs one entry. The entry captures a rating for the day, the factors that applied, and one action that was tried. The next day the user logs another entry. After several entries, the app builds a simple trend over time. The app then highlights which logged actions line up with better days. The user reviews that trend and sees the first signal connecting an action to better days.

Human actors
- Person managing their own discomfort (primary user, self-tracking)
- Optionally, a coach or clinician the person shares a summary with (read-only, later)

External systems
- None required for the first complete path

Internal product systems
- Entry logging and daily check-in
- Routine library (saved activities the user can attach to an entry)
- Trend and correlation view (pattern over time, action-to-outcome signal)
- Daily reminder and streak tracking

Critical assumptions
- Single-user, self-reported data; no diagnosis is claimed.

Ambiguities
- Platform: native mobile, web app, or both.

Proof boundary
The first version is proven when a user can log entries over several days and the app renders an honest trend plus an action-to-outcome signal from their own data. External integrations, sharing, and reminders are outside the first proof bar.
""",
        prompt="Draft a greenfield proposal for a personal pattern tracker.",
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a personal pattern tracker.",
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    public_proposal = {key: value for key, value in proposal.items() if key != "product_intent_authority"}
    rendered = json.dumps(public_proposal, sort_keys=True)
    titles = [row["title"] for row in proposal["backlog"]]
    components = [row["label"] for row in proposal["components"]]

    assert "Person Managing Discomfort" in rendered
    assert "Coach or Clinician" not in rendered
    assert "Coach or Clinician" in json.dumps(proposal["product_intent_authority"], sort_keys=True)
    assert "Pattern Relief User" not in rendered
    assert "Central Thing the Product" not in rendered
    assert "the optionally" not in rendered.casefold()
    assert "uses the product to central thing" not in rendered.casefold()
    assert "uses the product to person's" not in rendered.casefold()
    assert "after several entries, the app builds" not in rendered
    assert "Trend and Correlation View (pattern Over" not in rendered
    assert any(title == "Keep Person's Comfort Timeline Clear and Reviewable" for title in titles)
    assert any(component == "Trend and Correlation View Service" for component in components)
    assert not greenfield_quality_issues(proposal)


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


def test_mermaid_text_counts_numbered_flowchart_nodes_once() -> None:
    source = "\n".join(
        [
            "flowchart LR",
            '  S1["Open request"]',
            '  S2["Check evidence"]',
            '  S2["Duplicate evidence definition"]',
            '  S10["Publish outcome"]',
            '  C1["Intake service"]',
        ]
    )

    assert mermaid_text.numbered_flowchart_node_ids(source, prefix="S") == (
        "S1",
        "S2",
        "S10",
    )
    assert mermaid_text.numbered_flowchart_node_count(source, prefix="S") == 3
    assert mermaid_text.numbered_flowchart_node_count(source, prefix="C") == 1


def test_mermaid_label_wrapping_carries_dangling_connector_to_next_line() -> None:
    wrapped = mermaid_text.wrap_mermaid_label(
        "Saved session in history with date, workout, and total time",
        width=30,
        max_lines=5,
        limit=168,
    )

    assert "history with<br/>date" not in wrapped
    assert "history<br/>with date" in wrapped
    assert all(not part.endswith(" with") for part in wrapped.split("<br/>"))
    anchored = mermaid_text.wrap_mermaid_label(
        "Show both points on the metric's timeline with the intervention overlaid",
        width=30,
        max_lines=5,
        limit=168,
    )
    assert "points on<br/>the metric" not in anchored
    assert "points<br/>on the metric" in anchored
    assert all(
        not part.casefold().endswith((" on", " the", " with"))
        for part in anchored.split("<br/>")
    )


def test_mermaid_label_clipping_removes_incomplete_terminal_actions() -> None:
    source = "The workspace records the selected object code and the final summary includes its review destination"

    wrapped = mermaid_text.wrap_mermaid_label(source, width=30, max_lines=4, limit=76)
    visible = wrapped.replace("<br/>", " ")

    assert visible.endswith("the final summary")
    assert not generated_public_copy_issues("Atlas Mermaid", f'flowchart LR A["{wrapped}"]')
    assert mermaid_text.wrap_mermaid_label("The final summary includes more", limit=29) == "The final summary"


def test_flow_label_preserves_valid_noun_final_copy_without_clipping() -> None:
    source = "The workspace tracks every patient sample return"

    assert flow_label(source, width=80, max_lines=4, limit=120) == source
    wrapped = mermaid_text.wrap_mermaid_label(
        "The workspace tracks every patient sample return notice",
        width=24,
        max_lines=4,
        limit=51,
    )
    assert "sample return" in wrapped.replace("<br/>", " ")


def test_mermaid_quality_extracts_visible_labels_from_compact_flowchart_source() -> None:
    source = (
        'flowchart LR actor["Trainee"] S1["Saved session in history<br/>with date, workout, and total time"] '
        'S1 --> proof proof["Proof result<br/>Saved session in history<br/>with date, workout, and total time"] '
        "classDef step fill:#FFFFFF,stroke:#CBD5E1,color:#17233A,stroke-width:1px;"
    )

    units = mermaid_text.visible_mermaid_label_quality_texts(source)

    assert "Trainee" in units
    assert "Saved session in history with date, workout, and total time" in units
    assert "Saved session in history" in units
    assert "with date, workout, and total time" in units
    assert all("flowchart" not in unit and "classDef" not in unit for unit in units)


def test_confirmed_greenfield_create_handles_generic_reviewer_and_action_systems(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """Volunteer Equipment Checkout Tracker — Product Intent Confirmation

Product story
A community group needs one reliable place to track shared equipment, who has it, when it is due back, and whether it is safe to lend again. The product helps coordinators avoid lost items, double bookings, and unclear responsibility by turning checkout requests, item condition checks, and returns into one auditable record.

State object that changes through the first journey
An Equipment Item moves from available to reserved to checked out to returned pending inspection to available again, with a condition note and responsible requester attached to each transition.

First complete path Odylith should prove before broader scope
A coordinator registers one item, a requester requests it for a date range, the coordinator approves checkout, the requester returns it, and the coordinator records a return condition so the item can be made available again.

Human actors
- Coordinator — owns the inventory, approves checkouts, and records return condition.
- Requester — requests equipment, receives checkout approval, and returns the item.
- Reviewer — checks whether the record explains who had the item, when it changed hands, and what condition it returned in.

External systems
- Identity provider for coordinator and requester sign-in.
- Email or SMS notification channel for checkout reminders, later wave only.

Internal product systems
- Item registry — records equipment identity, ownership, availability status, and condition baseline.
- Checkout request log — captures requester, requested date range, purpose, and approval status.
- Approval workflow — records coordinator approval or rejection before an item leaves inventory.
- Availability view — shows which items can be requested now and why unavailable items are blocked.
- Return inspection record — captures returned condition, damage notes, and whether the item can be lent again.
- Reviewer dashboard and export — shows a reviewer the item state, requester, approval, return condition, and audit trail in one readable package.
- Audit trail — records state changes, actor, timestamp, and source for reviewer traceability.

Critical assumptions
- One organization owns the inventory in the first release.
- Payments, deposits, barcode scanning, and multi-location routing are out of scope for release 0.0.1.
- The first proof uses seeded data and does not claim live integrations.

Ambiguities that would change the first path
- Whether requesters can self-serve approvals or every checkout needs coordinator review.
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
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    encoded = json.dumps(proposal)

    assert "Reviewer —" not in encoded
    assert "Reviewer Dashboard" not in encoded
    assert "Review Dashboard and Export" in encoded
    assert "volunteer equipment checkout reviewer" in encoded.casefold()
    assert not greenfield_quality_issues(proposal)
    assert " bes " not in encoded.casefold()
    assert "owns captures" not in encoded
    assert "owns shows" not in encoded
    assert "Shows which items can be requested now" in encoded
    context = next(row for row in proposal["diagrams"] if row["title"] == "System Context View")
    assert "<br/>" in context["mermaid_source"]
    for row in proposal["diagrams"]:
        for component in row["components"]:
            assert "accepted first release path" not in component["description"]
            assert "owns owns" not in component["description"].casefold()
            assert component["description"].endswith(".")
