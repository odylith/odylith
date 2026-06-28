from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    CONTRACT_KEYS,
    public_prose_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import component_focus_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import keywords
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent


ROOT = Path(__file__).resolve().parents[3]
CONFIRMED_COMPLETION_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion.py"
CONFIRMED_COMPONENT_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_component_completion.py"
)
CONFIRMED_PREWRITE_GATE_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_prewrite_gate.py"
CONFIRMED_COMPLETION_QUALITY_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_quality.py"
)
CONFIRMED_COMPLETION_TEXT_MODEL_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_completion_text_model.py"
)


def test_confirmed_completion_prewrite_gate_stays_in_dedicated_owner() -> None:
    parent_source = CONFIRMED_COMPLETION_PATH.read_text(encoding="utf-8")
    gate_source = CONFIRMED_PREWRITE_GATE_PATH.read_text(encoding="utf-8")
    component_source = CONFIRMED_COMPONENT_COMPLETION_PATH.read_text(encoding="utf-8")
    quality_source = CONFIRMED_COMPLETION_QUALITY_PATH.read_text(encoding="utf-8")
    text_model_source = CONFIRMED_COMPLETION_TEXT_MODEL_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 800
    assert len(component_source.splitlines()) < 800
    assert "def _artifact_issues" not in parent_source
    assert "run_greenfield_tribunal" not in parent_source
    assert "def _text_needs_repair" not in parent_source
    assert "def _sequence_needs_repair" not in parent_source
    assert "def _has_bad_tail" not in parent_source
    assert "def _project_title" not in parent_source
    assert "def _component_label" not in parent_source
    assert "def _keywords" not in parent_source
    assert "def _component_interfaces" not in parent_source
    assert "def _complete_components" not in parent_source
    assert "def _component_risks" not in parent_source
    assert "def _component_sequence_is_weak" not in parent_source
    assert "def _component_field_is_weak" not in parent_source
    assert "responsibility_from_contract" not in parent_source
    assert "complete_component_rows" in parent_source
    assert "repair_component_sentence_lists" in parent_source
    assert "greenfield_confirmed_completion_text_model as completion_text" in parent_source
    assert "preflight_issues as _preflight_issues" in parent_source
    assert "text_needs_repair as _text_needs_repair" in parent_source
    assert "def complete_component_rows" in component_source
    assert "def repair_component_sentence_lists" in component_source
    assert "def _component_risks" in component_source
    assert "responsibility_from_contract" in component_source
    assert "def preflight_issues" in gate_source
    assert "artifact_tribunal.run_governed_artifact_tribunal" in gate_source
    assert "def text_needs_repair" in quality_source
    assert "def sequence_needs_repair" in quality_source
    assert "def validation_strategy_needs_repair" in quality_source
    assert "def project_title" in text_model_source
    assert "def component_label" in text_model_source
    assert "def keywords" in text_model_source
    assert "greenfield_domain_term_index import label_terms" in text_model_source
    assert "greenfield_domain_term_index import ordered_terms" in text_model_source
    assert 're.findall(r"[A-Za-z0-9][A-Za-z0-9-]*"' not in text_model_source
    assert "for raw in str(value or \"\")" not in text_model_source
    assert "def primary_component_for_backlog" in text_model_source
    assert component_focus_phrase(label="AI CRM Status Windows Service", contract={}, fallback="fallback") == (
        "ai crm status windows"
    )
    assert component_focus_phrase(label="Risk_policy component", contract={}, fallback="fallback") == (
        "risk policy"
    )
    assert component_focus_phrase(label="Flood Shelter Intake System Intake Register Service", contract={}, fallback="fallback") == (
        "flood shelter intake register"
    )
    assert keywords(["Status Windows Service", "Build window proof"]) == {
        "build",
        "proof",
        "service",
        "status",
        "window",
    }
    assert keywords(["source_backed evidence-trails", "2026 proof"]) == {
        "backed",
        "evidence",
        "proof",
        "source",
        "trail",
    }


def _dirty_complete_contract() -> dict[str, object]:
    return {
        "owned_state": "Human actors: Reviewer",
        "accepted_inputs": "Accepts representative input covering source, state, and proof plus 1 more",
        "produced_outputs": "Owns the local responsibility and keeps it tied to this product behavior",
        "states_or_transitions": "draft, active, and with clear ownership, protected access, required",
        "outside_boundary": "sibling work when the path is.",
        "local_proof": [
            "Component proof uses representative input covering the accepted first path.",
            "Validate with clear ownership, protected access, required",
        ],
        "upstream_truth": "accepted first-path input",
        "downstream_consumers": "release proof review",
        "unique_failure": "The component can appear complete with",
    }


def test_confirmed_repair_loop_cleans_dirty_public_prose_across_artifact_families(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        confirmed_intent=_confirmed_intent(),
        release_selector="0.0.1",
    )

    proposal["intent"]["proof_boundary"] = "Proof."
    proposal["validation_strategy"] = [
        "Validate with clear ownership, protected access, required",
        "The user verifies that The evidence changed.",
    ]
    proposal["security_compliance"] = {
        "domain": "Human actors: Reviewer",
        "security": "Security posture plus 1 more",
        "policy": "Policy with clear ownership, protected access, required",
    }
    proposal["project_intelligence"]["operators"] = ["Human actors: Reviewer"]
    proposal["risks"] = [
        {
            "id": "RISK-BAD",
            "title": "Human actors: Reviewer",
            "statement": "The release verifies that The proof is present.",
            "mitigation": "Mitigate with",
        }
    ]

    first_backlog = proposal["backlog"][0]
    first_backlog["problem"] = "Human actors: Reviewer"
    first_backlog["customer"] = "Primary user plus 1 more"
    first_backlog["opportunity"] = "Uses Example App to complete A reviewer creates a case."
    first_backlog["product_view"] = "The user inspects The generated state."
    first_backlog["success_metrics"] = ["Validate when the path is."]
    first_backlog["domain_risk"] = "Human actors: Reviewer"
    first_backlog["security_posture"] = "Security posture plus 1 more"
    first_backlog["risks"] = ["Risk with"]
    first_backlog["validation"] = ["Validate with clear ownership, protected access, required"]
    first_backlog["rationale_lines"] = ["Rationale when the path is."]

    for row in proposal["components"][:2]:
        row["component_contract"] = _dirty_complete_contract()
        row["responsibility"] = "Owns the local responsibility and keeps it tied to this product behavior"
        row["boundary"] = "Human actors: Reviewer"
        row["interfaces"] = ["Primary interface plus 1 more"]
        row["dependencies"] = ["Dependency with"]
        row["validation"] = ["Validate with clear ownership, protected access, required"]
        row["risks"] = ["Risk when the path is."]

    proposal["diagrams"][0]["title"] = "Human actors: Reviewer"
    proposal["diagrams"][0]["summary"] = "The user inspects The generated state."

    repaired = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    encoded = json.dumps(repaired)
    for banned in (
        "inspect The",
        "verifies that The",
        "Human actors:",
        "plus 1 more",
        "responsibility and keeps it tied",
        "with clear ownership, protected access, required",
        "when the path is.",
        "to complete A",
    ):
        assert banned not in encoded
    assert public_prose_quality_issues(repaired) == []
    assert component_spec_preflight_issues(repaired) == []

    for row in repaired["components"][:2]:
        assert set(CONTRACT_KEYS) <= set(row["component_contract"])
        contract_text = json.dumps(row["component_contract"]).casefold()
        assert "permit" in contract_text or "zoning" in contract_text or "revision" in contract_text


PEER_REVIEW_INTENT_TEXT = """Science Paper Peer Review App

Product story
A research venue or editorial team needs a structured review workspace for scientific papers. Authors submit manuscripts, editors assign qualified reviewers, reviewers evaluate claims and reproducibility, and the editor reaches a decision with a clear audit trail.

State object
The core state is a review case: a submitted paper, its authors, editorial status, assigned reviewers, review forms, conflicts of interest, decision history, revision rounds, files, comments, and notification state.

First complete path
An author submits a paper. An editor screens it, checks conflicts, assigns reviewers, and tracks review progress. Reviewers submit structured feedback with scores, strengths, weaknesses, reproducibility notes, and recommendation. The editor compares reviews, requests revisions or makes a decision, and the author receives the outcome.

Human actors
- Author submitting a scientific manuscript
- Editor or program chair managing review flow
- Reviewer evaluating scientific quality and reproducibility
- Admin configuring venue policies, templates, deadlines, and permissions

External systems
- Email or notification service
- File storage for manuscripts, supplements, and review attachments
- Identity provider for login and reviewer access

Internal product systems
- Submission intake and manuscript versioning
- Reviewer assignment and conflict-of-interest tracking
- Structured review forms and scoring rubrics
- Editorial decision workflow
- Revision-round management
- Role-based access control and audit history
- Notification and deadline tracking
- Search, filtering, and status dashboards

Critical assumptions
- Human editors make all final decisions.
- Confidential review data must be protected by role and review stage.

Proof boundary
The first proof is a working review cycle from paper submission through editorial decision. It must show correct role-based visibility, reviewer assignment, review submission, deadline tracking, decision history, and a clear author-facing outcome.
"""


def test_confirmed_peer_review_shape_stays_component_specific_and_actor_complete(tmp_path) -> None:
    intent = parse_confirmed_intent_text(
        PEER_REVIEW_INTENT_TEXT,
        prompt="Draft a product-first greenfield proposal for a science research paper peer review app.",
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for a science research paper peer review app.",
        confirmed_intent=intent,
        release_selector="0.0.1",
    )

    payload = build_greenfield_payload(proposal=proposal, repo_root=tmp_path)
    participant_titles = [row[1] for row in payload["participants"]]
    assert len(participant_titles) >= 4
    assert "Scientific Manuscript Author" in participant_titles
    assert "Editor or Program Chair" in participant_titles
    assert "Scientific Quality and Reproducibility Reviewer" in participant_titles
    assert "Venue Policies, Templates, Deadlines, and Permissions Admin" in participant_titles
    assert all(" Managing " not in f" {title} " for title in participant_titles)

    components = {row["label"]: row for row in proposal["components"]}
    submission = components["Submission Intake and Manuscript Versioning Service"]["component_contract"]
    assignment = components["Review Assignment and Conflict-of-interest Tracking"]["component_contract"]
    scoring = components["Structured Review Forms and Scoring Rubrics"]["component_contract"]
    decision = components["Editorial Decision Workflow Service"]["component_contract"]
    revision = components["Revision-round Management Service"]["component_contract"]
    access = components["Role-based Access Control and Audit History Service"]["component_contract"]
    notification = components["Notification and Deadline Tracking Service"]["component_contract"]
    dashboard = components["Search, Filtering, and Status Dashboards Surface"]["component_contract"]

    assert "submission intake" in submission["owned_state"].casefold()
    assert "manuscript versioning" in submission["owned_state"].casefold()
    assert "assignment routing" not in " ".join([submission["owned_state"], submission["accepted_inputs"], submission["produced_outputs"]]).casefold()
    assert "review assignment" in assignment["owned_state"].casefold()
    assert "conflict" in assignment["owned_state"].casefold()
    scoring_owned = scoring["owned_state"].casefold()
    assert "scoring" in scoring_owned
    assert "rubric" in scoring_owned
    assert "editorial decision" in decision["owned_state"].casefold()
    assert "revision round" in revision["owned_state"].casefold().replace("-", " ")
    assert "role-based access" in access["owned_state"].casefold()
    assert "notification" in notification["owned_state"].casefold()
    assert "search" in dashboard["owned_state"].casefold()

    encoded = json.dumps(proposal)
    for banned in (
        "preserves handles",
        "maintains defines",
        "refuses refuses",
        "scor,",
        "shows whether The",
        "inspect the core state is",
        "plus 1 more",
        "responsibility and keeps it tied",
    ):
        assert banned not in encoded
    assert public_prose_quality_issues(proposal) == []

    mermaid_sources = "\n".join(str(row.get("mermaid_source", "")) for row in proposal["diagrams"])
    assert "…" not in mermaid_sources
    assert "..." not in mermaid_sources
    assert "sequenceDiagram" not in mermaid_sources
    assert "flowchart" in mermaid_sources
    assert "Scientific Manuscript" in mermaid_sources
    assert "Submission Intake and" in mermaid_sources
    assert "Structured Review Forms and" in mermaid_sources
    assert "Editorial Decision Workflow" in mermaid_sources
    assert 'S1["Submit a paper"]' in mermaid_sources
    assert "Receive the outcome" in mermaid_sources

    assert component_spec_preflight_issues(proposal) == []
