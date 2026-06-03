from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import derive_component_semantic_contract
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import first_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import sentence_fragment
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.governance.component_spec_rendering import build_component_spec


ROOT = Path(__file__).resolve().parents[3]
CONFIRMED_COMPONENTS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py"
COMPONENT_CONTRACT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract.py"
COMPONENT_CONTRACT_PROFILES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract_profiles.py"


def test_confirmed_components_helper_shape_stays_below_soft_limit() -> None:
    source = CONFIRMED_COMPONENTS_PATH.read_text(encoding="utf-8")

    assert len(source.splitlines()) < 800
    assert source.count("def _title_phrase") == 1
    assert "def _can_clause" not in source


def test_component_contract_profiles_stay_in_dedicated_owner() -> None:
    contract_source = COMPONENT_CONTRACT_PATH.read_text(encoding="utf-8")
    profile_source = COMPONENT_CONTRACT_PROFILES_PATH.read_text(encoding="utf-8")

    assert len(contract_source.splitlines()) < 800
    assert "greenfield_component_contract_profiles as contract_profiles" in contract_source
    assert "def _document_context_contract" not in contract_source
    assert "def _status_view_contract" not in contract_source
    assert "def _document_local_proof" not in contract_source
    assert "def _status_local_proof" not in contract_source
    assert "def document_context_contract" in profile_source
    assert "def status_view_contract" in profile_source
    assert "def _document_local_proof" in profile_source
    assert "def _status_local_proof" in profile_source


def test_greenfield_component_spec_renderer_uses_narrative_distinct_contract_sections() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Planning Engine",
            "source_system_description": "computes plan targets from progress snapshots and status windows with rationale",
        },
        proposal={"intent": {"title": "Generic Planning"}},
        sibling={"label": "Weekly Status Review", "source_system_description": "calculates weekly status and progress state"},
        previous_label="Daily Progress Logging",
        next_label="Weekly Status Review",
        state_label="planning record",
    ).fields

    spec = build_component_spec(
        component_id="planning-engine",
        label="Planning Engine",
        path="src/planning/engine.py",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract=contract,
    )

    assert rendered_component_spec_quality_issues({"Planning Engine": spec}, project_title="Generic Planning") == []
    assert "## Component Brief" not in spec
    assert "## Boundary Narrative" not in spec
    assert "## First Release Proof" not in spec
    assert "## Implementation Starting Point" not in spec
    assert "Planning Engine carries the product logic" in spec
    assert "Component Snapshot" not in spec
    assert "runtime ownership boundary" not in spec
    assert "structured contract below" not in spec
    assert "The local contract centers on" not in spec
    assert "keeps the project honest" not in spec
    assert "Refused domain responsibilities:" not in spec
    assert "Forbidden runtime authorities:" not in spec
    assert "Source-backed proof named by the first implementation plan" not in spec
    assert "computes plan targets input" not in spec.casefold()

    assert "Suggested fixture:" not in spec
    assert "Run one Planning Engine example" not in spec
    assert "Planning Engine shows" in spec
    assert "reaches the visible result" not in spec
    assert "example explains" not in spec
    assert "stops before a trusted result" in spec


def test_greenfield_component_spec_renderer_cleans_guardrail_verb_phrases() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Access and Safety Guardrail",
            "source_system_description": (
                "keeps authorization, shared access, privacy, safety, retention, accessibility, and recovery behavior explicit"
            ),
        },
        proposal={
            "intent": {
                "title": "Generic Review Workspace",
                "first_path": (
                    "A requester enters required details. The workspace checks the details and displays a decision summary."
                ),
                "proof_boundary": "The release is trusted when the result and review trail can be replayed.",
            }
        },
        sibling={"label": "Evidence Log", "source_system_description": "records result and failure reason"},
        previous_label="Evidence Log",
        next_label="Release Review",
        state_label="review workspace state",
    ).fields

    spec = build_component_spec(
        component_id="access-and-safety-guardrail",
        label="Access and Safety Guardrail",
        path="src/review_workspace/access_and_safety_guardrail",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract=contract,
        responsibility="Keeps authorization, shared access, privacy, safety, retention, accessibility, and recovery behavior explicit.",
    )

    assert rendered_component_spec_quality_issues({"Access and Safety Guardrail": spec}, project_title="Generic Review Workspace") == []
    assert generated_semantic_slop_issues(spec) == []
    assert "keeps authorization" not in spec.casefold()
    assert "access keep authorization" not in spec.casefold()
    assert "keeps the project honest" not in spec.casefold()
    assert "the local contract centers on" not in spec.casefold()
    assert "authorization reaches the visible result" not in spec.casefold()
    assert "keeped" not in spec.casefold()
    assert "example explains" not in spec.casefold()
    assert "guide path capture allowed command" not in spec.casefold()
    assert "capture allowed command" not in spec.casefold()


def test_greenfield_component_spec_renderer_rejects_mechanical_contract_dump() -> None:
    contract = {
        "owned_state": (
            "Decision and reason-code service state, producing the explainable result, "
            "Related path: review flow captures declared facts, "
            "runs them against configurable review checks, decision reason-code, local blockers, "
            "handoff evidence for application review state"
        ),
        "accepted_inputs": (
            "Required producing the explainable result, decision reason-code command, required fields, "
            "prior state, source evidence, authorized actor, validation notes"
        ),
        "produced_outputs": (
            "Validated producing the explainable result, decision reason-code state, correction marker, "
            "replayable change evidence, blocked-state evidence, reviewer explanation, handoff record"
        ),
        "states_or_transitions": "open, requested, qualified, returned, visible, received, captured, validated, blocked, revised, handed-off",
        "outside_boundary": (
            "Refused domain responsibilities: responsibilities not named by this component boundary; "
            "sibling-owned state: reviewer queue state, case routing; "
            "forbidden runtime authorities: mutation of upstream source truth, silent overwrite of downstream handoff state, release approval"
        ),
        "local_proof": [
            "Decision and Reason-code Service proof ties producing the explainable result, required inputs, produced outputs, blocker behavior, and downstream handoff together",
            "Invalid or missing producing the explainable result blocks trusted downstream state instead of producing Decision and Reason-code Service output",
            "Decision and Reason-code Service replay proof preserves actor, source, validation status, blocker state, and handoff evidence",
        ],
        "upstream_truth": "Qualification Rules Engine",
        "downstream_consumers": "Reviewer Queue Service",
        "unique_failure": (
            "Decision and Reason-code Service can look complete while producing the explainable result is missing, "
            "stale, assigned to the wrong boundary, or released without source evidence, blocker state, or downstream handoff evidence."
        ),
    }

    spec = build_component_spec(
        component_id="decision-and-reason-code-service",
        label="Decision and Reason-code Service",
        path="src/application_review/decision_and_reason_code_service",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-004",),
        diagrams=("D-002",),
        component_contract=contract,
    )

    assert rendered_component_spec_quality_issues({"Decision and Reason-code Service": spec}, project_title="Application Review") == []
    assert "explainable result" in spec
    assert "decision reason-code" in spec
    assert "Qualification Rules Engine" in spec
    assert "Reviewer Queue Service" in spec
    for forbidden in (
        "Component Snapshot",
        "Component planning record for",
        "runtime ownership boundary",
        "structured contract below",
        "It exists to make this failure testable",
        "Related path:",
        "Required producing",
        "Validated producing",
        "Suggested fixture:",
        "Refused domain responsibilities:",
        "Forbidden runtime authorities:",
        "Operator Verification",
        "Related path:",
        "runs them against",
    ):
        assert forbidden not in spec


def test_greenfield_component_ids_remove_product_component_word_overlap() -> None:
    rows = confirmed_components(
        label="Service Goal Planning",
        label_slug="service-goal-planning",
        internal_systems=[
            "Planning Engine: computes plan targets from progress snapshots and status windows.",
        ],
        first_path="A user receives an adjusted plan target.",
        state_object="planning record",
        proof_boundary="Plan adjustment evidence is visible.",
    )

    component_id = str(rows[0]["component_id"])
    assert component_id == "service-goal-planning-engine"
    assert "planning-planning" not in component_id


def test_greenfield_quality_gate_rejects_verb_phrase_slot_filling() -> None:
    issues = public_prose_quality_issues(
        {
            "component_contract": {
                "accepted_inputs": "Planning Engine accepts computes plan targets input.",
                "produced_outputs": "Planning Engine produces computes plan targets result.",
            }
        }
    )

    assert any("verb phrase inserted into contract artifact slot" in issue for issue in issues)


def test_greenfield_quality_gate_rejects_generic_governance_posture_filler() -> None:
    issues = public_prose_quality_issues(
        {
            "problem": "The user path, state, evidence, decision, and follow-up are scattered.",
            "opportunity": "Build the narrow entry, actions, feedback, and handoff before adding scope.",
            "product_view": "Users inspect state profile, the first-path outcome, visible blockers, risk posture, and evidence.",
        }
    )

    assert any("generic governance posture filler" in issue for issue in issues)


def test_greenfield_first_action_clause_stops_before_next_product_action() -> None:
    assert (
        first_action_clause(
            "A requester submits a maintenance request, the product verifies required details, assigns a technician, estimates cost and timing, and notifies the requester."
        )
        == "A requester submits a maintenance request"
    )
    assert sentence_fragment("Validated intake request and downstream handoff") == "validated intake request and downstream handoff"
