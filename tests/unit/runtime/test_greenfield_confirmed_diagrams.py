from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_text import brief_proof_boundary
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_text import proof_checkpoint_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_text import semantic_proof_checkpoint
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import best_component_node_for_text
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import first_path_flowchart_mermaid
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps


def _diagram_slugs() -> dict[str, str]:
    return {
        "context": "context",
        "sequence": "sequence",
        "state_evidence": "state-evidence",
        "component_boundaries": "component-boundaries",
        "ownership": "ownership",
        "proof_review": "proof-review",
    }


def test_atlas_component_cards_explain_specific_boundary_without_path_boilerplate() -> None:
    rows = confirmed_diagrams(
        label="Operations Platform",
        diagram_slugs=_diagram_slugs(),
        components=[
            {
                "component_id": "source-import",
                "label": "Source Import Adapter",
                "kind": "adapter",
                "responsibility": "External source import",
            },
            {
                "component_id": "decision-scoring",
                "label": "Decision Scoring Engine",
                "kind": "service",
                "responsibility": "Scores candidate decisions with confidence, inputs, and rule version.",
            },
            {
                "component_id": "state-ledger",
                "label": "State Ledger Service",
                "kind": "service",
                "responsibility": "Records versioned state changes, actor, timestamp, and source evidence.",
            },
            {
                "component_id": "exception-review",
                "label": "Exception Review Workflow",
                "kind": "service",
                "responsibility": "Coordinates exception review, handoff, blocked-state recovery, and final outcome.",
            },
            {
                "component_id": "user-review",
                "label": "User Review Surface",
                "kind": "client",
                "responsibility": "Review screen for user approval and correction.",
            },
            {
                "component_id": "assignment-planner",
                "label": "Assignment Planner",
                "kind": "service",
                "responsibility": "Assigns jobs to available resources while respecting priority, capacity, and constraints.",
            },
        ],
    )

    components = {row["name"]: row["description"] for row in rows[0]["components"]}
    encoded = json.dumps(rows)

    assert components["Source Import Adapter"] == (
        "Translates external source import inputs into product-owned records and preserves source provenance. "
        "The Source Import Adapter boundary must show which source supplied the input, what result was accepted, and which error state blocked unsafe input."
    )
    assert components["Decision Scoring Engine"] == (
        "Scores candidate decisions with confidence, inputs, and rule version. The Decision Scoring Engine boundary "
        "must show inputs, rule versions, results, and downstream decisions that depended on it."
    )
    assert components["State Ledger Service"] == (
        "Records versioned state changes, actor, timestamp, and source evidence. The State Ledger Service boundary "
        "must show versioned state, source evidence, and decisions that depended on this record."
    )
    assert components["Exception Review Workflow"] == (
        "Coordinates exception review, handoff, blocked-state recovery, and final outcome. The Exception Review Workflow "
        "boundary must show responsibility transfers, failure states, recovery actions, and final outcomes."
    )
    assert components["User Review Surface"] == (
        "Presents review screen for user approval and correction to users and captures the action or decision the "
        "product needs next. The User Review Surface boundary must show what the user saw, submitted, corrected, or "
        "approved and which product state changed after that action."
    )
    assert components["Assignment Planner"] == (
        "Owns product responsibility to assign jobs to available resources while respecting priority, capacity, "
        "and constraints. The Assignment Planner boundary must show what this boundary receives, produces, records, and makes available next."
    )
    assert "accepted first release path" not in encoded
    assert "for the accepted first" not in encoded
    assert "Owns the responsibility to" not in encoded
    assert "Owns the product responsibility" not in encoded
    assert "hands off" not in encoded
    assert "part of the path" not in encoded
    assert "Design pressure" not in encoded
    assert "Domain evidence" not in encoded
    assert "**" not in encoded
    assert "`" not in encoded


def test_atlas_visible_result_headers_do_not_repeat_body_result_word() -> None:
    semantic_model = {
        "first_path_contract": {
            "visible_result": "result as a reviewable experiment",
            "events": [{"text": "A researcher saves the result as a reviewable experiment", "visible_result": True}],
        }
    }
    flowchart = first_path_flowchart_mermaid(
        label="Research Model",
        actors=["Researcher: reviews model output"],
        components=[{"component_id": "review", "label": "Review Workspace", "release_scope": "first_path_required"}],
        first_path="A researcher saves the result as a reviewable experiment.",
        semantic_model=semantic_model,
    )
    diagrams = confirmed_diagrams(
        label="Research Model",
        diagram_slugs=_diagram_slugs(),
        components=[{"component_id": "review", "label": "Review Workspace", "release_scope": "first_path_required"}],
        first_path="A researcher saves the result as a reviewable experiment.",
        state_object="A model run record tracks input, output, and review evidence.",
        evidence_record="A review evidence record",
        proof_boundary="Release succeeds when the saved result can be reviewed.",
        human_actors=["Researcher: reviews model output"],
        semantic_model=semantic_model,
    )
    encoded = json.dumps({"flowchart": flowchart, "diagrams": diagrams}, sort_keys=True)

    assert "result result" not in encoded.casefold()
    assert "Proof result<br/>a reviewable experiment" in flowchart
    assert "Visible result<br/>a reviewable experiment" in encoded


def test_confirmed_diagram_text_model_stays_in_dedicated_owner() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    diagram_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py"
    text_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagram_text.py"
    confirmed_text_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_text.py"
    diagram_source = diagram_owner.read_text(encoding="utf-8")
    text_source = text_owner.read_text(encoding="utf-8")
    confirmed_text_source = confirmed_text_owner.read_text(encoding="utf-8")

    assert len(diagram_source.splitlines()) < 800
    assert "greenfield_confirmed_diagram_text as diagram_text" in diagram_source
    assert "def _component_description" not in diagram_source
    assert "def _brief_proof_boundary" not in diagram_source
    assert "def _short_label" not in diagram_source
    assert "def word_count" in confirmed_text_source
    assert "from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count" in text_source
    assert 're.findall(r"[A-Za-z0-9]+"' not in text_source
    assert "def component_description" in text_source
    assert "def brief_proof_boundary" in text_source
    assert "def short_label" in text_source
    assert semantic_proof_checkpoint({"first_path_contract": {"visible_result": "`AI/ML` review status appears"}}) == (
        "AI/ML review status appears"
    )
    assert proof_checkpoint_label("Done means: save the `AI/ML` review status and source note.") == (
        "save the AI/ML review status"
    )


def test_brief_proof_boundary_does_not_clip_terminal_product_show_clause() -> None:
    proof = (
        "Release 0.0.1 succeeds when a warehouse slotting planner user starts a warehouse slotting planner request, "
        "the product records required information, the product shows a reviewable result, "
        "and the product marks the request ready or blocked."
    )

    brief = brief_proof_boundary(proof)

    assert not brief.endswith("product shows")
    assert "product shows." not in brief
    assert "records required information" in brief


def test_component_boundary_wraps_long_deferred_component_identity() -> None:
    rows = confirmed_diagrams(
        label="Evidence Review Workspace",
        diagram_slugs=_diagram_slugs(),
        components=[
            {"component_id": "intake", "label": "Evidence Intake Service", "release_scope": "first_path_required"},
            {
                "component_id": "archive",
                "label": "Evidence Archive and Reviewer Signoff Ledger",
                "release_scope": "deferred",
            },
        ],
    )

    boundary = next(row for row in rows if row["title"] == "Component Boundary View")

    assert "Deferred scope<br/>Evidence Archive and Reviewer<br/>Signoff Ledger" in boundary["mermaid_source"]
    assert "Evidence Archive and Reviewer Signoff Ledger" not in boundary["mermaid_source"]


def test_confirmed_diagrams_keep_deferred_scope_and_proof_record_labels_readable() -> None:
    first_path = (
        "Coordinator records a support request. Reviewer records access restrictions. Capacity lead records capacity limits. "
        "Public coordinator publishes public coordination status."
    )
    state_object = (
        "Coordination record with support request, access restriction, capacity limit, and public coordination status."
    )
    proof_boundary = (
        "Release 0.0.1 is proven when one request moves through access review, capacity recording, "
        "and public coordination status publication while private participant details remain inside the governed boundary."
    )
    components = [
        {
            "component_id": "request-intake",
            "label": "Request Intake Service",
            "kind": "service",
            "release_scope": "first_path_required",
            "responsibility": "Records support request facts and actor context.",
        },
        {
            "component_id": "capacity-ledger",
            "label": "Capacity Limit Ledger",
            "kind": "service",
            "release_scope": "first_path_required",
            "responsibility": "Maintains capacity limits and source notes.",
        },
        {
            "component_id": "public-status",
            "label": "Public Coordination Status View Service",
            "kind": "client",
            "release_scope": "first_path_required",
            "responsibility": "Presents public coordination status, role visibility, and source event history.",
        },
        {
            "component_id": "notification-automation",
            "label": "Notification Automation Service",
            "kind": "service",
            "release_scope": "deferred",
            "responsibility": "Sends reminders or receives external updates after the first release.",
        },
    ]
    semantic_model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Regional Coordination Workspace",
            first_path=first_path,
            state_object=state_object,
            proof_boundary=proof_boundary,
            components=components,
        )
    )

    rows = confirmed_diagrams(
        label="Regional Coordination Workspace",
        diagram_slugs=_diagram_slugs(),
        components=components,
        first_path=first_path,
        proof_boundary=proof_boundary,
        state_object=state_object,
        evidence_record="Coordination Proof Record",
        human_actors=["Coordinator", "Reviewer", "Capacity lead", "Public coordinator"],
        internal_systems=[str(row["label"]) for row in components],
        non_goals=["Do not claim notification automation or receives external updates before the first coordination loop works."],
        semantic_model=semantic_model,
    )
    boundary = next(row for row in rows if row["title"] == "Component Boundary View")
    ownership = next(row for row in rows if row["title"] == "Ownership and Proof View")
    proof_review = next(row for row in rows if row["title"] == "Release Proof Review")
    rendered = json.dumps(rows)
    status_component = next(row for row in boundary["components"] if row["name"] == "Public Coordination Status View Service")

    assert "notification automation<br/>or external updates" in boundary["mermaid_source"]
    assert "notification automation<br/>or external updates" in proof_review["mermaid_source"]
    assert "or receives" not in rendered
    assert status_component["description"].startswith("Presents public coordination status")
    assert "Owns product responsibility to present" not in rendered
    assert "Release proof<br/>Public coordination status" in ownership["mermaid_source"]
    assert "Evidence record<br/>Coordination Proof Record" in proof_review["mermaid_source"]
    assert "Capacity Limit Ledger Record" not in proof_review["mermaid_source"]


def test_context_diagram_strips_deferred_predicate_from_external_labels() -> None:
    rows = confirmed_diagrams(
        label="Coordination Workspace",
        diagram_slugs=_diagram_slugs(),
        components=[
            {
                "component_id": "request-intake",
                "label": "Request Intake Service",
                "kind": "service",
                "release_scope": "first_path_required",
            }
        ],
        external_systems=[
            "Weather alert feeds are deferred.",
            "Emergency dispatch systems are deferred.",
        ],
    )
    context = next(row for row in rows if row["title"] == "System Context View")["mermaid_source"]
    boundary = next(row for row in rows if row["title"] == "Component Boundary View")["mermaid_source"]
    rendered = f"{context}\n{boundary}"

    assert "Weather alert feeds<br/>are" not in rendered
    assert "Emergency dispatch systems<br/>are" not in rendered
    assert "Weather alert feeds" in rendered
    assert "Emergency dispatch systems" in rendered


def test_sequence_event_steps_stay_in_dedicated_owner() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    diagram_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py"
    steps_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_sequence_steps.py"
    index_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py"
    diagram_source = diagram_owner.read_text(encoding="utf-8")
    steps_source = steps_owner.read_text(encoding="utf-8")
    index_source = index_owner.read_text(encoding="utf-8")

    assert len(diagram_source.splitlines()) < 800
    assert "def label_terms" in index_source
    assert "from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps" in diagram_source
    assert "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms" in steps_source
    assert "value_coercion import dedupe_by_key" in steps_source
    assert "sequence_event_steps(first_path, semantic_model=semantic_model)" in diagram_source
    assert "sequence_event_steps(first_path, semantic_model=semantic_model, dedupe=True)" in diagram_source
    for moved in (
        "def _semantic_event_steps",
        "def _drop_launcher_only_steps",
        "def _launcher_only_step",
        "def _normalize_event_step",
        "def _first_path_steps",
        "def _expand_compound_steps",
        "def _dedupe_steps",
    ):
        assert moved not in diagram_source
        assert moved in steps_source
    assert "def sequence_event_steps" in steps_source
    assert 're.findall(r"[A-Za-z0-9]+"' not in steps_source
    assert "seen: set[str]" not in steps_source
    assert "seen.add(" not in steps_source

    assert sequence_event_steps("1. Open app. 2. Add AI/ML result. 3. Save final status.") == [
        "Add AI/ML result",
        "Save final status",
    ]
    assert sequence_event_steps("1. Save result. 2. Save-result. 3. Show proof.") == [
        "Save result",
        "Show proof",
    ]


def test_release_proof_frame_does_not_collapse_first_path_events() -> None:
    first_path = (
        "The first release proves one complete path: a home cook picks a recipe, "
        "confirms ingredients are staged, starts the cooking run, follows prompts "
        "when the robot needs input, and sees the run finish in a safe-to-serve "
        "state with emergency stop available throughout."
    )

    model = first_path_model(first_path)
    steps = sequence_event_steps(first_path, dedupe=True)

    assert model.steps == (
        "A home cook picks a recipe",
        "A home cook confirms ingredients are staged",
        "A home cook starts the cooking run",
        "A home cook follows prompts when the robot needs input",
        "A home cook sees the run finish in a safe-to-serve state with emergency stop available throughout",
    )
    assert model.visible_outcome == "See the run finish in a safe-to-serve state with emergency stop available throughout"
    assert len(steps) == 5
    assert steps[-1].startswith("A home cook sees the run finish")


def test_first_path_flowchart_terminal_label_preserves_distinctive_tail_terms() -> None:
    first_path = (
        "Educators submit lesson plans. Elders review cultural context. "
        "Coordinators record learner progress evidence."
    )
    components = [
        {"component_id": "intake", "label": "Lesson Plan Intake Register", "release_scope": "first_path_required"},
        {"component_id": "review", "label": "Cultural Context Review Workspace", "release_scope": "first_path_required"},
        {"component_id": "evidence", "label": "Learner Progress Evidence Ledger", "release_scope": "first_path_required"},
    ]
    semantic_model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Curriculum Evidence Circle",
            first_path=first_path,
            state_object="Lesson plan record",
            proof_boundary="Release succeeds when learner progress evidence is reviewable.",
            components=components,
        )
    )

    mermaid = first_path_flowchart_mermaid(
        label="Curriculum Evidence Circle",
        actors=["Educators", "Elders", "Coordinators"],
        components=components,
        first_path=first_path,
        semantic_model=semantic_model,
    )

    assert "Record learner progress<br/>evidence" in mermaid
    assert 'S3["Progress evidence"]' not in mermaid


def test_release_proof_control_does_not_render_as_first_path_step() -> None:
    first_path = (
        "A city dispatcher records an evacuation support request. A tribal liaison reviews restricted access needs. "
        "A hospital coordinator records capacity constraints. A mutual-aid officer confirms resource commitments. "
        "A shelter lead records readiness. An emergency commander publishes public coordination status. "
        "First release proves one end-to-end request moves through access, capacity commitment, readiness and public "
        "status without making emergency decisions."
    )
    actors = [
        "City Dispatcher: uses the product to record evacuation support request.",
        "Tribal Liaison: uses the product to review restricted access needs.",
        "Hospital Coordinator: uses the product to record capacity constraints.",
        "Mutual Aid Officer: uses the product to confirm resource commitments.",
        "Shelter Lead: uses the product to record readiness.",
        "Emergency Commander: uses the product to publish public coordination status.",
    ]
    components = [
        {"component_id": "request-intake", "label": "Request Intake", "release_scope": "first_path_required"},
        {"component_id": "access-review", "label": "Access Review Board", "release_scope": "first_path_required"},
        {"component_id": "capacity-ledger", "label": "Capacity Ledger", "release_scope": "first_path_required"},
        {"component_id": "commitment-tracker", "label": "Commitment Tracker", "release_scope": "first_path_required"},
        {"component_id": "readiness-board", "label": "Readiness Board", "release_scope": "first_path_required"},
        {"component_id": "public-status", "label": "Public Status View", "release_scope": "first_path_required"},
    ]
    semantic_model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Multi-jurisdictional Coordination Workspace",
            first_path=first_path,
            state_object="Public coordination status record",
            proof_boundary="Release 0.0.1 succeeds when public coordination status evidence is reviewable.",
            components=components,
        )
    )

    steps = sequence_event_steps(first_path, semantic_model=semantic_model, dedupe=True)
    diagrams = confirmed_diagrams(
        label="Multi-jurisdictional Coordination Workspace",
        diagram_slugs=_diagram_slugs(),
        components=components,
        first_path=first_path,
        state_object="Public coordination status record",
        evidence_record="Coordination proof ledger",
        human_actors=actors,
        proof_boundary="Release 0.0.1 succeeds when public coordination status evidence is reviewable.",
        semantic_model=semantic_model,
    )
    context = next(row for row in diagrams if row["slug"] == "context")["mermaid_source"]
    sequence = next(row for row in diagrams if row["slug"] == "sequence")["mermaid_source"]
    state_evidence = next(row for row in diagrams if row["slug"] == "state-evidence")["mermaid_source"]

    assert steps == [
        "A city dispatcher records an evacuation support request",
        "A tribal liaison reviews restricted access needs",
        "A hospital coordinator records capacity constraints",
        "A mutual-aid officer confirms resource commitments",
        "A shelter lead records readiness",
        "An emergency commander publishes public coordination status",
    ]
    assert "Emergency Commander" in context
    event_text = " ".join(str(row["text"]) for row in semantic_model["first_path_contract"]["events"])
    assert "First release proves" not in event_text
    assert "without making emergency decisions" not in event_text
    assert "First release proves" not in sequence
    assert "without making" not in sequence
    assert "Confirm resource commitments" in sequence
    assert "Publish public coordination" in sequence
    assert "First action<br/>Record an evacuation support" in state_evidence
    assert "needs the product" not in state_evidence


def test_sequence_diagram_term_routing_uses_shared_index() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    diagram_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_sequence_diagram.py"
    index_owner = repo_root / "src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py"
    diagram_source = diagram_owner.read_text(encoding="utf-8")
    index_source = index_owner.read_text(encoding="utf-8")

    assert "def ordered_terms" in index_source
    assert "stem_ing" in index_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms"
        in diagram_source
    )
    assert "def _domain_terms" not in diagram_source
    assert "normalize_domain_token" not in diagram_source
    assert "stem_ing=True" in diagram_source

    assert ordered_terms("Race readings and reviewing status.", stopwords={"and"}, stem_ing=True) == [
        "race",
        "read",
        "review",
        "status",
    ]
    assert (
        best_component_node_for_text(
            "reviewing race readings",
            components=[
                {"label": "Generic queue", "responsibility": "stores status"},
                {"label": "Race read review", "responsibility": "reviews telemetry reading"},
            ],
        )
        == "component2"
    )


def test_sequence_event_steps_preserve_action_later_decision_tail() -> None:
    steps = sequence_event_steps(
        "A user adds a person to follow, chooses approved public data sources, sees recent activity signals with source links, "
        "reviews risk and context summaries, adds selected items to a watchlist, and records whether they plan to research, "
        "ignore, or act later.",
        dedupe=True,
    )

    assert steps[-1] == "A user records whether they plan to research, ignore, or act later"


def test_sequence_event_steps_keep_coordinated_object_lists_with_prior_action() -> None:
    steps = sequence_event_steps(
        "A permit coordinator imports one permit application, a zoning reviewer records a zoning check, "
        "the applicant submits one revision, and a supervisor reviews the decision package with traceable "
        "documents, comments, checks, and final status.",
        dedupe=True,
    )

    assert steps == [
        "A permit coordinator imports one permit application",
        "A zoning reviewer records a zoning check",
        "The applicant submits one revision",
        "A supervisor reviews the decision package with traceable documents, comments, checks, and final status",
    ]


def test_sequence_event_steps_keep_connector_led_object_tails_with_prior_action() -> None:
    steps = sequence_event_steps(
        "A coordinator creates a draft request, attaches subject identity and required request context, "
        "validates uploaded documents, sends the packet to a destination team, sees received status, "
        "handles an accept, decline, or more-info request, schedules the request when accepted, "
        "and reviews the completed status history.",
        dedupe=True,
    )

    assert "Required request context" not in steps
    assert "Or more-info request" not in steps
    assert any("attaches subject identity" in step and "required request context" in step for step in steps)
    assert any("handles an accept" in step and "more-info request" in step for step in steps)


def test_sequence_event_steps_keep_long_evidence_list_inside_action_step() -> None:
    steps = sequence_event_steps(
        "Mobility operations lead can turn an ambiguous disengagement event into a review-ready record "
        "using vehicle logs, scene annotation, remote-operator notes, weather context, explicit expert review, "
        "auditable decision ledger, and a final disengagement review recommendation.",
        dedupe=True,
    )

    assert steps == [
        "Mobility operations lead turns an ambiguous disengagement event into a review-ready record using vehicle logs, "
        "scene annotation, remote-operator notes, weather context, explicit expert review, auditable decision ledger, "
        "and a final disengagement review recommendation"
    ]
    assert "Explicit expert review, auditable decision ledger" not in steps
    assert "And a final disengagement review recommendation" not in steps
