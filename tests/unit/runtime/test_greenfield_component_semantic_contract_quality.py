from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_component_semantic_contract as semantic_contract
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract import build_component_contract
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import component_contract_issues
from odylith.runtime.domain_intelligence.greenfield_component_terms import action_object_artifact_phrases
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import artifact_phrase_has_clause_shape
from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import context_object_phrases
from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import relation_phrases
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues


ROOT = Path(__file__).resolve().parents[3]
SEMANTIC_CONTRACT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_contract.py"
SEMANTIC_CONTEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_context.py"


def test_component_semantic_context_stays_in_dedicated_owner() -> None:
    contract_source = SEMANTIC_CONTRACT_PATH.read_text(encoding="utf-8")
    context_source = SEMANTIC_CONTEXT_PATH.read_text(encoding="utf-8")

    assert len(contract_source.splitlines()) < 800
    assert "greenfield_component_semantic_context as semantic_context" in contract_source
    assert "def _context_object_phrases" not in contract_source
    assert "def _context_required_phrases" not in contract_source
    assert "def _needs_context_backfill" not in contract_source
    assert "greenfield_domain_term_index import label_terms as _label_terms" in contract_source
    assert "re.findall(r\"[a-z0-9][a-z0-9'-]*\"" not in contract_source
    assert "def _looks_actor_term" not in context_source
    assert "greenfield_actor_terms import looks_actor_term as _looks_actor_term" in context_source
    assert "def context_object_phrases" in context_source
    assert "def context_required_phrases" in context_source
    assert "def needs_context_backfill" in context_source
    assert context_object_phrases(
        "Inspector reviews permit note, missing documents, and timeline evidence.",
        label_terms=["permit", "note"],
        description_terms=["review", "document"],
    ) == ("permit note", "missing document")
    assert semantic_contract._compact_artifact_phrase("source-backed_review record")
    assert not semantic_contract._compact_artifact_phrase("source-backed audit trail evidence record")


def test_component_contract_removes_actor_and_handoff_verbs_from_artifact_nouns() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Visit Capture Service",
            "source_system_description": (
                "captures the service visit, equipment identity, observed condition, "
                "technician note, and correction history"
            ),
        },
        proposal={
            "intent": {
                "title": "Field Service Notebook",
                "first_path": (
                    "A technician opens a new service visit, selects the equipment, records the observed "
                    "condition and note, saves the visit, sees it on the equipment timeline, edits the note "
                    "when a mistake is found, and hands off one service visit with equipment identity, "
                    "condition, note, timestamp, timeline visibility, and follow-up evidence."
                ),
            }
        },
        sibling={"label": "Equipment Timeline Service"},
        previous_label="Equipment Directory",
        next_label="Equipment Timeline Service",
        state_label="Service Visit Record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "hand visit" not in rendered
    assert "technician open" not in rendered
    assert "service visit" in rendered
    assert not generated_semantic_slop_issues(contract)
    evidence_contract = derive_component_semantic_contract(
        {
            "label": "Evidence Annotation and Extraction Service",
            "source_system_description": (
                "links included sources to annotations, captures extracted fields, records source locations, "
                "validates missing evidence, and hands extracted evidence into assessment"
            ),
        },
        proposal={
            "intent": {
                "title": "Structured Evidence Review Workspace",
                "first_path": (
                    "A review lead creates an Evidence Review Project, imports source records, screens independently, "
                    "moves included sources into evidence extraction, records quality assessment, builds a synthesis table, "
                    "and exports a review package with source references and decision history."
                ),
                "proof_boundary": (
                    "Release succeeds when the exported package explains which evidence was extracted, "
                    "which quality assessment was recorded, and which audit events prove the result."
                ),
            }
        },
        sibling={"label": "Quality Assessment and Scoring"},
        previous_label="Independent Screening Workflow",
        next_label="Quality Assessment and Scoring",
        state_label="Evidence Review Project",
    ).fields
    evidence_rendered = json.dumps(evidence_contract, sort_keys=True).casefold()

    assert "hands extracted evidence" not in evidence_rendered
    assert "extracted evidence into assessment" not in evidence_rendered
    assert "extracted evidence" in evidence_rendered
    assert not generated_semantic_slop_issues(evidence_contract)


def test_component_contract_keeps_relation_extraction_inside_one_action_clause() -> None:
    assert relation_phrases("Service routes approved packet to audit queue.") == (
        "approved packet to audit queue",
    )
    contract = derive_component_semantic_contract(
        {
            "label": "Export and Deletion Decision Service",
            "source_system_description": (
                "applies consent and retention rules, produces export package state or blocked deletion decision, "
                "and hands evidence to audit"
            ),
        },
        proposal={
            "intent": {
                "title": "Privacy Request Lifecycle Console",
                "first_path": (
                    "A privacy coordinator verifies authority, selects export or deletion, checks retention rules, "
                    "produces an allowed package or blocked decision, and reviews the audit event."
                ),
                "state_object": "A privacy request lifecycle record",
            }
        },
        sibling={"label": "Lifecycle Audit and Review View"},
        previous_label="Protected Record Reference Store",
        next_label="Lifecycle Audit and Review View",
        state_label="Privacy Request Lifecycle Record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "produces export package" not in rendered
    assert "hands evidence to audit" not in rendered
    assert "export package state or blocked deletion decision" in rendered
    assert not generated_semantic_slop_issues(contract)


def test_component_contract_does_not_promote_subordinate_actor_actions_to_owned_state() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Result Status Recordkeeping Service",
            "source_system_description": (
                "records when the representative user records the current status and keeps status, "
                "correction history, blockers, and visible handoff context"
            ),
        },
        proposal={
            "intent": {
                "title": "Permit Review Workspace",
                "first_path": (
                    "A representative user reviews permit details, records the current status, "
                    "and sees a permit review result."
                ),
            }
        },
        sibling=None,
        previous_label="Permit Review Record",
        next_label="",
        state_label="Permit Review Record",
    ).fields

    assert "representative records the current status" not in contract["owned_state"].casefold()
    assert "result status" in contract["owned_state"].casefold()


def test_concrete_component_contract_does_not_import_project_actions_or_non_goals() -> None:
    proposal = {
        "intent": {
            "title": "Controlled Dispatch Desk",
            "first_path": (
                "A dispatch coordinator records an exception, preserves release readiness proof, "
                "and blocks dispatch until approval."
            ),
            "product_story": "The first release proves controlled dispatch without expanding adjacent workflows.",
        }
    }
    readiness = derive_component_semantic_contract(
        {
            "label": "Release Readiness Proof Recordkeeping Service",
            "source_system_description": (
                "records when the dispatch coordinator preserves release readiness proof and keeps status, "
                "correction history, blockers, and visible handoff context"
            ),
        },
        proposal=proposal,
        sibling={"label": "Dispatch Approval"},
        previous_label="Exception Record",
        next_label="Dispatch Approval",
        state_label="Dispatch Exception",
    ).fields
    dispatch = derive_component_semantic_contract(
        {
            "label": "Dispatch Workflow Support Service",
            "source_system_description": (
                "records when the dispatch coordinator blocks dispatch until approval and keeps dispatch status, "
                "blockers, evidence, and visible handoff context"
            ),
        },
        proposal=proposal,
        sibling=None,
        previous_label="Dispatch Approval",
        next_label="",
        state_label="Dispatch Exception",
    ).fields

    rendered = json.dumps({"readiness": readiness, "dispatch": dispatch}, sort_keys=True).casefold()
    assert "preserve readiness" not in readiness["owned_state"].casefold()
    assert "expand adjacent workflow" not in rendered
    assert "dispatch until approval" not in dispatch["owned_state"].casefold()


def test_component_tribunal_rejects_action_and_condition_clauses_in_owned_state() -> None:
    contract = {
        "owned_state": "preserve readiness, dispatch until approval",
        "accepted_inputs": "exception record",
        "produced_outputs": "readiness decision",
        "states_or_transitions": "pending, approved",
        "outside_boundary": "external release decision",
        "local_proof": ["Successful path evidence remains reviewable."],
        "upstream_truth": "exception record",
        "downstream_consumers": "release review",
        "unique_failure": "Missing approval keeps dispatch blocked.",
    }
    issues = component_contract_issues(
        {
            "components": [
                {
                    "label": "Dispatch Workflow Support Service",
                    "component_contract": contract,
                }
            ]
        }
    )

    lowered = [issue.casefold() for issue in issues]
    assert any("contains an action clause preserve readiness" in issue for issue in lowered)
    assert any("contains a condition clause dispatch until approval" in issue for issue in lowered)


def test_artifact_phrase_shape_separates_state_nouns_from_sentence_fragments() -> None:
    assert artifact_phrase_has_clause_shape("when reviewers preserve rationale")
    assert artifact_phrase_has_clause_shape("what is ready status")
    assert artifact_phrase_has_clause_shape("dispatch status until approval")
    assert not artifact_phrase_has_clause_shape("readiness decision record")
    assert not artifact_phrase_has_clause_shape("reports intake status")


def test_action_object_artifacts_require_a_direct_owned_action_clause() -> None:
    assert action_object_artifact_phrases("captures extracted fields") == ("extracted field capture",)
    assert action_object_artifact_phrases(
        "The service keeps context from teams that capture findings outside the product."
    ) == ()
    assert action_object_artifact_phrases(
        "This boundary is valid when a reviewer validates a packet after approval."
    ) == ()


def test_preservation_responsibility_becomes_owned_artifact_state() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Vendor Audit Retention Ledger",
            "source_system_description": "preserves immutable onboarding history",
        },
        proposal={"intent": {"first_path": "A reviewer approves a vendor and preserves audit history."}},
        sibling=None,
        previous_label="Vendor Decision Service",
        next_label="",
        state_label="Vendor onboarding file",
    ).fields

    assert "immutable onboarding history" in contract["owned_state"].casefold()
    assert "preserves immutable onboarding history" not in json.dumps(contract).casefold()


def test_protected_hyphen_surface_does_not_lowercase_a_generated_component_title() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Clinic Follow Up Coordination Details Review",
            "source_system_description": (
                "reviews clinic follow-up coordination details while preserving status, blockers, and handoff context"
            ),
        },
        proposal={
            "intent": {
                "title": "Clinic Follow Up Coordination Desk",
                "first_path": (
                    "A representative user reviews clinic follow-up coordination details and sees a clear result."
                ),
            }
        },
        sibling={"label": "Status Recordkeeping Service"},
        previous_label="Clinic Intake",
        next_label="Status Recordkeeping Service",
        state_label="Clinic Follow Up Coordination Record",
    ).fields

    assert contract["unique_failure"].startswith("Clinic Follow-Up Coordination Details Review can mislead users")
    assert "clinic follow-up coordination details Review" not in json.dumps(contract)


def test_component_contract_preserves_relative_clause_objects_as_artifacts() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Revision Tracker",
            "source_system_description": "links applicant revisions to the documents and checks they are meant to address",
        },
        proposal={},
        sibling={"label": "Decision Package Review"},
        previous_label="Zoning Check Ledger",
        next_label="Decision Package Review",
        state_label="Permit Review File",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "applicant revisions to the documents and related checks" in rendered
    assert "checks are meant to address" not in rendered
    assert "checks are meant" not in rendered
    assert not generated_semantic_slop_issues(contract)


def test_component_contract_does_not_promote_topic_terms_as_owned_state() -> None:
    proposal = {
        "intent": {
            "title": "Technical Learning Lab",
            "product_story": (
                "A learner needs a guided lab that turns an abstract lecture topic into a visible experiment."
            ),
            "first_path": (
                "A learner opens a preset experiment, adjusts parameters, runs the sample, "
                "watches the result view update, writes an explanation, and saves the session."
            ),
            "state_object": (
                "A lab session contains selected preset, parameter values, run status, probability result, "
                "observation, explanation, review note, blocked reason, and evidence timestamp."
            ),
            "proof_boundary": "Release succeeds when the saved session and evidence timestamp can be reviewed.",
        }
    }

    contract = derive_component_semantic_contract(
        {
            "label": "Technical Learning Lab Experience Guide Service",
            "source_system_description": (
                "presents the current state, missing-information guidance, user-facing confirmation, "
                "and next useful action without owning source records"
            ),
        },
        proposal=proposal,
        sibling={"label": "Evidence Log Service"},
        previous_label="Product Record Service",
        next_label="Evidence Log Service",
        state_label="Lab Session",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()
    owned = contract["owned_state"].casefold()

    assert "turn abstract lecture topic" not in rendered
    assert "topic reviewable" not in rendered
    assert "learning lab," not in owned
    assert "user-facing confirmation" in owned
    assert "missing-information guidance" in owned
    assert "useful action" in owned
    assert not generated_semantic_slop_issues(contract)


def test_validation_gate_contract_uses_the_accepted_gate_subject_without_invented_artifacts() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Temperature Checks Validation Service",
            "source_system_description": (
                "enforces temperature checks as the release gate and keeps blocked reason, "
                "validation evidence, and release status visible"
            ),
        },
        proposal={
            "intent": {
                "first_path": "Temperature checks are the release gate.",
                "assumptions": ["Retain lot temperatures for 18 months and never infer an allergen."],
            }
        },
        sibling=None,
        previous_label="Parcels Delivery Service",
        next_label="",
        state_label="Donated Lot",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert contract["owned_state"] == "temperature check result, blocked reason, validation evidence, release status"
    assert "allowed or blocked release decision" in contract["produced_outputs"]
    assert "retain temperature" not in rendered
    assert "failure reason ledger" not in rendered
    assert "known-limit checkpoint" not in rendered
    assert "recovery-condition ledger" not in rendered
    assert not generated_semantic_slop_issues(contract)


def test_generic_component_contract_builder_prefers_semantic_artifacts_over_raw_action_focus() -> None:
    proposal = {
        "intent": {
            "title": "Learning Simulation Lab",
            "product_story": (
                "Learners need a bounded simulation workspace with traceable parameters, results, "
                "explanations, and review evidence."
            ),
            "first_path": (
                "A learner selects a scenario, adjusts width and energy, runs the deterministic experiment, "
                "reviews the result, checks misconception prompts, and exports a reviewable summary."
            ),
            "state_object": (
                "A learning experiment record tracks scenario, width, energy, units, result, explanation, "
                "misconception checks, and export evidence."
            ),
            "proof_boundary": "Release succeeds when one run and one export remain traceable.",
        }
    }
    parameter = build_component_contract(
        {
            "label": "Parameter Control Surface",
            "kind": "surface",
            "source_system_description": (
                "captures barrier width and particle energy choices, enforces bounds, "
                "and keeps unit conversions visible"
            ),
        },
        proposal=proposal,
        previous_label="Scenario Preset Surface",
        next_label="Simulation Runner",
    )
    review = build_component_contract(
        {
            "label": "Misconception and Export Review Surface",
            "kind": "surface",
            "source_system_description": (
                "checks the learner explanation for required assumptions, units, and misconception prompts "
                "before producing a teacher-reviewable export"
            ),
        },
        proposal=proposal,
        previous_label="Attempt Comparison Workspace",
        next_label="Release Review",
    )
    rendered = json.dumps({"parameter": parameter, "review": review}, sort_keys=True).casefold()

    assert "barrier width and particle energy choices, enforces bounds" not in rendered
    assert "checks the learner explanation" not in rendered
    assert "surface owns" not in rendered
    assert "parameter control bound" not in rendered
    assert "blocked." not in rendered
    assert "particle energy choices" in rendered
    assert "misconception prompts" in rendered
    assert not generated_semantic_slop_issues(parameter)
    assert not generated_semantic_slop_issues(review)


def test_profile_triggered_component_contracts_still_use_semantic_basis() -> None:
    proposal = {
        "intent": {
            "title": "Vendor Onboarding Review",
            "first_path": (
                "A vendor submits onboarding documents, the product validates required files, runs compliance "
                "checks, routes risk review to procurement, records approval or blocked reason, notifies the vendor, "
                "marks spend readiness, and preserves audit history."
            ),
            "state_object": (
                "A vendor onboarding file tracks vendor identity, submitted documents, compliance checklist, risk "
                "review, approval decision, blocked reason, spend-readiness status, notification status, and audit "
                "history."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when one vendor can submit documents, missing files block review, required "
                "checks are recorded, procurement can approve or block readiness with a reason, the vendor "
                "notification is recorded, and audit history can replay the decision."
            ),
        }
    }

    packet = build_component_contract(
        {
            "label": "Packet Intake Service",
            "kind": "service",
            "source_system_description": (
                "captures vendor identity, submitted documents, required files, and missing-document blockers"
            ),
        },
        proposal=proposal,
        previous_label="Vendor Intake",
        next_label="Review Workspace",
    )
    status = build_component_contract(
        {
            "label": "Status History View Service",
            "kind": "service",
            "source_system_description": (
                "shows approval status, blocked reason, vendor notification state, and audit history for reviewers"
            ),
        },
        proposal=proposal,
        previous_label="Decision Service",
        next_label="Release Review",
    )
    rendered = json.dumps({"packet": packet, "status": status}, sort_keys=True).casefold()

    assert "vendor identity" in rendered
    assert "missing-document blockers" in rendered
    assert "vendor notification state" in rendered
    assert "audit history" in rendered
    assert "context bundle creation" not in rendered
    assert "current next-action owner" not in rendered
    assert not generated_semantic_slop_issues(packet)
    assert not generated_semantic_slop_issues(status)
