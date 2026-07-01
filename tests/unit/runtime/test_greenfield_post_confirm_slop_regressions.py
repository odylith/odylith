from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.generated_copy_quality import has_inline_role_casing_drift
from odylith.runtime.artifact_quality.greenfield_package_quality import RenderedArtifact
from odylith.runtime.artifact_quality.greenfield_package_quality import _artifact_surface_language_issues
from odylith.runtime.artifact_quality.greenfield_package_quality import _chunk_language_issues
from odylith.runtime.artifact_quality.greenfield_package_quality import _narrative_chunks
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import modal_base_form_drift_phrases
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import proposal_with_component_brief_gate
from odylith.runtime.domain_intelligence.greenfield_component_contract import public_prose_quality_issues
from odylith.runtime.domain_intelligence.greenfield_component_contract import responsibility_from_contract
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_intelligence import complete_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import action_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import component_focus_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import workstream_risk
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import state_object as completion_state_object
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import state_reference
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import workstream_product_view
from odylith.runtime.domain_intelligence.greenfield_component_contract_profiles import status_view_contract
from odylith.runtime.domain_intelligence import greenfield_confirmed_diagram_text as diagram_text
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_actions as backlog_actions
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_text_model as backlog_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_evidence_record_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_backlog_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_program
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_release_plan
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_workstream_titles
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_experience import build_next_steps
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import confirmed_project_brief
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import confirmed_system_name
from odylith.runtime.domain_intelligence.greenfield_quality_gate import _contains_stale_generic_label
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import first_path_flowchart_mermaid
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import object_reference_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import gerund_action_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import looks_like_visible_result
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_view import first_path_semantic_view
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import release_scope_for_component
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import first_path_flowchart_mermaid
from odylith.runtime.domain_intelligence.greenfield_text import normalize_proof_boundary_language
from odylith.runtime.domain_intelligence.greenfield_text import normalize_reviewed_result_nouns
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import build_workstream_domain_intelligence
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import domain_risk_for_row
from odylith.runtime.domain_intelligence.proposal_tribunal_substance import (
    _check_atlas_source_preserves_first_path_tail,
    _check_first_path_flowchart,
)
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec


ROOT = Path(__file__).resolve().parents[3]
FIRST_PATH_SEMANTICS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py"


def _proposal_from_guidance_prompt(prompt: str) -> dict[str, object]:
    intent_text = f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Visible format contract
- Render the visible confirmation as sectioned Markdown.

Original user intent
{prompt}
Next step
- Confirm.
"""
    intent = parse_confirmed_intent_text(intent_text, prompt=prompt)
    return build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=str(intent["title"]),
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
FIRST_PATH_CLAUSES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_clauses.py"
FIRST_PATH_COMMON_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_common.py"
FIRST_PATH_FRAGMENTS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_fragments.py"
FIRST_PATH_VIEW_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_view.py"
FIRST_PATH_TYPES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_types.py"
DOMAIN_TERM_INDEX_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py"
GREENFIELD_TEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_text.py"
SEMANTIC_QUALITY_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_semantic_quality.py"
SEQUENCE_STEPS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_sequence_steps.py"
COMPONENT_TERMS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_terms.py"
CONFIRMED_SYSTEM_ROWS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_rows.py"
CONFIRMED_INTENT_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py"
)
PRODUCT_RISKS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_product_risks.py"
CONFIRMED_DIAGRAM_TEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagram_text.py"


def test_release_suffixed_labels_do_not_duplicate_release_across_governance_surfaces() -> None:
    components = [
        {"component_id": "intake", "label": "Batch Evidence Console Service", "kind": "service"},
        {"component_id": "safety", "label": "Safety Constraint Ledger", "kind": "service"},
        {"component_id": "readiness", "label": "Manufacturing Readiness Surface", "kind": "client"},
    ]
    program = confirmed_program(
        label="Battery Materials Release",
        parent_title="Battery Materials Release Evidence Desk",
        release="0.0.1",
        workflow_title="Record one lab batch",
        boundary_title="Prove safety constraints",
        proof_title="Publish manufacturing readiness",
        components=components,
    )
    release_plan = confirmed_release_plan(
        label="Battery Materials Release",
        label_slug="battery-materials-release",
        release="0.0.1",
        workflow_title="Record one lab batch",
        boundary_title="Prove safety constraints",
        proof_title="Publish manufacturing readiness",
    )
    diagrams = confirmed_diagrams(
        label="Battery Materials Release",
        diagram_slugs={
            "context": "context",
            "sequence": "sequence",
            "state_evidence": "state-evidence",
            "component_boundaries": "component-boundaries",
            "ownership": "ownership",
            "proof_review": "proof-review",
        },
        components=components,
        product_story="Materials teams need release evidence review.",
        first_path="Materials reviewer records one lab batch and approves manufacturing readiness.",
        proof_boundary="First release proves the manufacturing readiness decision.",
        state_object="Batch Release Evidence Record",
        evidence_record="Batch Evidence Console Proof Record",
        human_actors=["Materials reviewer"],
    )
    rendered = json.dumps({"program": program, "release_plan": release_plan, "diagrams": diagrams}, sort_keys=True)
    duplicate_normalized = re.sub(r"<br\s*/?>", " ", rendered, flags=re.IGNORECASE)

    assert not re.search(r"\brelease\s+release\b", duplicate_normalized, flags=re.IGNORECASE)
    assert re.search(r"\bbattery materials release gate\b", rendered, flags=re.IGNORECASE)
    assert "Battery Materials Release release gate" not in rendered


def test_first_path_clause_rendering_stays_in_dedicated_owner() -> None:
    parser_source = FIRST_PATH_SEMANTICS_PATH.read_text(encoding="utf-8")
    clause_source = FIRST_PATH_CLAUSES_PATH.read_text(encoding="utf-8")
    common_source = FIRST_PATH_COMMON_PATH.read_text(encoding="utf-8")
    fragment_source = FIRST_PATH_FRAGMENTS_PATH.read_text(encoding="utf-8")
    view_source = FIRST_PATH_VIEW_PATH.read_text(encoding="utf-8")
    type_source = FIRST_PATH_TYPES_PATH.read_text(encoding="utf-8")
    index_source = DOMAIN_TERM_INDEX_PATH.read_text(encoding="utf-8")

    assert len(parser_source.splitlines()) < 800
    assert len(clause_source.splitlines()) < 800
    assert len(common_source.splitlines()) < 800
    assert len(fragment_source.splitlines()) < 800
    assert len(view_source.splitlines()) < 800
    for moved in (
        "def first_path_clauses",
        "def first_path_action_phrase",
        "def first_path_capability_phrase",
        "def first_path_outcome_phrase",
        "def _first_path_capability_text",
        "def _first_path_action_text",
        "def _first_path_outcome_text",
    ):
        assert moved not in parser_source
        assert moved in clause_source
    for moved in (
        "def clean_visible_result_phrase",
        "def visible_result_object",
        "def action_chain_fragment",
    ):
        assert moved not in parser_source
        assert moved not in clause_source
        assert moved in fragment_source
    for moved in (
        "def clean_first_path_text",
        "def clip_first_path_phrase",
        "def lowercase_leading_article",
    ):
        assert moved not in parser_source
        assert moved not in clause_source
        assert moved not in fragment_source
        assert moved in common_source
    assert "def first_path_model" in parser_source
    assert "greenfield_domain_term_index import label_terms" in parser_source

    assert "len(re.findall" not in parser_source
    assert "def first_path_clauses" in clause_source
    assert "greenfield_first_path_view import first_path_semantic_view" in clause_source
    assert "greenfield_first_path_fragments import action_chain_fragment" not in clause_source
    for duplicated_step_classifier in (
        "def _dash_detail_fragment_keys",
        "def _semantic_terms",
        "def _is_named_product_launcher_fragment",
    ):
        assert duplicated_step_classifier not in clause_source
        assert duplicated_step_classifier in view_source
    assert "def _visible_outcome_covered" not in clause_source
    assert "def covers_visible_object" in view_source
    assert "greenfield_domain_term_index import label_terms" not in clause_source
    assert "greenfield_domain_term_index import ordered_terms" not in clause_source
    assert "normalize_domain_token" not in clause_source
    assert "len(re.findall" not in clause_source
    assert "class FirstPathStepView" in view_source
    assert "class FirstPathSemanticView" in view_source
    assert "def first_path_semantic_view" in view_source
    assert "def first_path_step_view" in view_source
    assert "greenfield_domain_term_index import label_terms" in fragment_source
    assert "greenfield_domain_term_index import ordered_terms" in fragment_source
    assert "greenfield_first_path_common import clean_first_path_text" in clause_source
    assert "greenfield_first_path_common import clean_first_path_text" in parser_source
    assert "MATERIAL_ACTION_RE = re.compile" in common_source
    assert "len(re.findall" not in fragment_source
    assert "len(re.findall" not in common_source
    assert "class FirstPathModel" in type_source
    assert "class FirstPathClauses" in type_source
    assert "def label_terms" in index_source
    assert label_terms("`AI/ML` reviewer records follow-up notes") == [
        "AI",
        "ML",
        "reviewer",
        "records",
        "follow-up",
        "notes",
    ]

    model = first_path_model(
        "A requester opens the app, the AI reviewer records follow-up notes, "
        "and the product displays decision evidence."
    )
    assert model.steps == (
        "The AI reviewer records follow-up notes",
        "The product displays decision evidence",
    )
    assert model.material_action == "Record follow-up notes"


def test_project_intelligence_completion_defaults_do_not_leak_control_plane_names() -> None:
    proposal = {"project_intelligence": {"schema_version": "odylith.greenfield.project_intelligence.v1"}}

    changed = complete_project_intelligence(
        proposal,
        release_selector="0.0.1",
        project_title="Regional Safety Console",
        first_path="A coordinator records a request and a reviewer publishes a status.",
        state_object="corridor readiness record",
        proof_boundary="Release succeeds when the status is reviewable with evidence.",
        text_needs_repair=lambda _value: False,
    )
    rendered = json.dumps(proposal["project_intelligence"], sort_keys=True)

    assert changed
    assert "Radar" not in rendered
    assert "Registry" not in rendered
    assert "Atlas" not in rendered
    assert "Workstream records" in rendered
    assert "Component records" in rendered
    assert "Diagram records" in rendered


def test_first_path_semantic_view_precomputes_step_facts_for_renderers() -> None:
    model = first_path_model(
        "A resident describes a repair, selects an appointment slot, the system confirms the booking, "
        "and shows the resident the next step."
    )

    view = first_path_semantic_view(model)

    assert view.primary_actor_signature == "resident"
    assert view.visible_outcome_object == "The next step"
    assert [(step.fragment, step.actor_signature, step.is_visible_result) for step in view.steps] == [
        ("describe a repair", "resident", False),
        ("select an appointment slot", "resident", False),
        ("review the booking", "", True),
        ("review the next step", "", True),
    ]
    assert view.steps[-1].is_system_generated is True
    assert view.covers_visible_object(view.steps[-1].visible_object)


def test_plural_actor_subjects_and_decision_pair_outcomes_render_as_reviewable_results() -> None:
    first_path = (
        "applicants submit permit packets, reviewers check zoning evidence, inspectors add site findings, "
        "and supervisors approve or reject the permit with an auditable rationale."
    )

    assert action_chain_fragment("Applicants submit permit packets") == "submit permit packets"
    assert actor_signature("Applicants submit permit packets") == "applicant"
    assert actor_signature("Supervisors approve or reject the permit with an auditable rationale") == "supervisor"
    assert first_path_action_phrase(first_path, max_fragments=1) == "submit permit packets"
    assert (
        first_path_capability_phrase(first_path)
        == "submit permit packets, add site findings, and approve or reject the permit with an auditable rationale"
    )
    assert (
        outcome_action_phrase("Supervisors approve or reject the permit with an auditable rationale")
        == "review the approval or rejection of the permit with an auditable rationale"
    )
    assert outcome_action_phrase("Hearing readiness") == "see the hearing readiness"


def test_temporal_choice_tail_expands_into_reviewable_first_path_events() -> None:
    first_path = (
        "homeowners compare roof options, incentives, installer quotes, financing choices, "
        "and projected savings before choosing an installation plan."
    )

    assert first_path_steps(first_path) == (
        "Homeowners compare roof options, incentives, installer quotes, financing choices and projected savings",
        "Choose an installation plan",
    )
    semantic = asdict(
        build_greenfield_semantic_model(
            title="Residential Solar Planning Tool",
            state_object="selected installation plan record",
            first_path=first_path,
            proof_boundary="Release succeeds when the selected installation plan is reviewable.",
            components=[],
            human_actors=["Homeowners: compare options and choose a plan."],
        )
    )

    events = semantic["first_path_contract"]["events"]
    assert len(events) == 3
    assert semantic["first_path_contract"]["visible_result"] == "Selected installation plan"
    assert events[-1]["text"] == "Review evidence for selected installation plan"

    flowchart = first_path_flowchart_mermaid(
        label="Residential Solar Planning Tool",
        actors=["Homeowners: compare options and choose a plan."],
        components=[],
        first_path=first_path,
        semantic_model=semantic,
    )
    assert 'S3["Review selected installation' in flowchart
    assert 'proof["Proof result<br/>Selected installation plan"]' in flowchart


def test_role_gerund_actor_rows_stay_clean_and_grammatical() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
## Classroom Accommodation Plan Tracker

### Product story
A school support team turns an accommodation decision into a classroom-ready plan that teachers can follow while student details stay limited to the people who need them.

### State object
The unit of truth is an accommodation plan record with student-safe identifiers, approved supports, responsible staff, guardian communication status, implementation evidence, missed-support flags, version history, and audit trail.

### First complete path
A support coordinator creates a plan from approved accommodations, assigns teacher responsibilities, marks what information is teacher-visible, and sends the plan for acknowledgment. A teacher opens the plan, acknowledges assigned supports, records implementation evidence, flags a missed support when needed, and the coordinator reviews the evidence and updates plan status.

### Human actors
- Support coordinator creating the plan, assigning responsibilities, and reviewing evidence.
- Classroom teacher acknowledging supports and recording implementation evidence.
- Guardian or family contact receiving appropriate communication status without internal staff notes.

### Proof boundary
Release 0.0.1 succeeds when one coordinator can create a versioned plan, assign teacher responsibilities, restrict sensitive fields by role, a teacher can acknowledge and record evidence, missed support is visible, and the audit trail proves who changed plan status and why.
""",
            prompt="Draft a classroom accommodation plan tracker.",
        )
    )

    actors = "\n".join(intent["human_actors"])
    assert "Classroom Teacher Acknowledging" not in actors
    assert "Support Coordinator Creating" not in actors
    assert "Classroom Teacher: acknowledging supports" in actors
    assert generated_public_copy_issues("actors", actors) == ()


def test_workstream_titles_avoid_clipped_actor_and_material_action_slop() -> None:
    solar = confirmed_workstream_titles(
        label="Residential Solar Quote Workspace",
        components=[{"label": "Home and Usage Intake Surface"}, {"label": "Solar Fit Estimator Service"}],
        internal_systems=[],
        first_path=(
            "A homeowner enters the address, monthly usage, roof details, and installation goal. "
            "The product validates required inputs and shows the homeowner an approved quote summary with assumptions."
        ),
        state_object="Solar quote request",
        proof_boundary="Release 0.0.1 succeeds when the homeowner sees an approved quote summary with assumptions.",
        human_actors=["Homeowner: requesting a plain-language solar quote and reviewing assumptions."],
    )[0]
    public = confirmed_workstream_titles(
        label="Public Response Queue",
        components=[{"label": "Resident Intake Surface"}, {"label": "Triage and Ownership Service"}],
        internal_systems=[],
        first_path="A resident submits a question, receives a tracking status, and waits for an answer.",
        state_object="Resident response case",
        proof_boundary="Release 0.0.1 succeeds when the resident receives an approved answer.",
        human_actors=["Resident: asking a public question and checking response status."],
    )[0]
    research = confirmed_workstream_titles(
        label="Research Reproducibility Review Workspace",
        components=[{"label": "Package Intake Surface"}, {"label": "Rerun Evidence Tracker"}],
        internal_systems=[],
        first_path=(
            "A submitting researcher creates a review record, attaches dataset references, scripts, environment notes, "
            "and expected outputs, then submits for review. A reproducibility reviewer checks the package."
        ),
        state_object="Reproducibility review record for one study package",
        proof_boundary="Release 0.0.1 succeeds when one researcher submits for review and a reviewer records evidence.",
        human_actors=["Submitting Researcher: preparing the analysis package and responding to missing-artifact blockers."],
    )[0]
    operator = confirmed_workstream_titles(
        label="Cooking Robot Controller",
        components=[{"label": "Run Controller Service"}, {"label": "Safety Monitor Service"}],
        internal_systems=[],
        first_path=(
            "Home cook picks a recipe, the controller validates the robot is ready, "
            "runs the step sequence with closed-loop heat and timing control, and reaches a safe-to-serve state."
        ),
        state_object="Cooking Run",
        proof_boundary="Release 0.0.1 succeeds when one operator reaches a safe-to-serve state.",
        human_actors=["Home Cook: chooses a recipe and watches safety status."],
    )[0]
    jet = confirmed_workstream_titles(
        label="Jet Engine Servicing Tracker",
        components=[
            {"label": "Engine and Servicing Record Store"},
            {"label": "Work-order and Task Workflow Engine"},
        ],
        internal_systems=[],
        first_path=(
            "A service planner intakes an engine, opens a work order with its required tasks, "
            "a technician records the work, and a supervisor releases the engine as serviceable."
        ),
        state_object="Servicing Record",
        proof_boundary="Release 0.0.1 succeeds when one engine moves through intake, work order, and release.",
        human_actors=[
            "Service Planner: intakes engines and opens work orders",
            "Maintenance Technician: performs and records tasks",
        ],
    )[0]

    assert solar == "Let Homeowner See an Approved Quote Summary with Assumptions"
    assert public == "Let Resident See a Tracking Status"
    assert research == "Let Submitting Researcher Submit for Review"
    assert not looks_like_visible_result("A submitting researcher submits for review")
    assert operator == "Let Home Cook Pick a Recipe"
    assert jet == "Let Service Planner Intake an Engine"
    assert backlog_text.capability_action_clause("validate the robot is ready and run the step sequence") == (
        "validate the robot is ready and run the step sequence"
    )
    assert action_phrase(
        {
            "intent": {
                "first_path": (
                    "Home cook picks a recipe, the controller validates the robot is ready, "
                    "runs the step sequence, and reaches a safe-to-serve state."
                )
            }
        }
    ) == "validate the robot is ready"
    assert first_path_capability_phrase(
        (
            "Home cook picks a recipe, the controller validates the robot is ready, "
            "runs the step sequence, and reaches a safe-to-serve state."
        ),
        max_fragments=4,
    ).startswith("home cook can pick a recipe")
    joined = "\n".join([solar, public, research])
    assert "Requesting a Plain" not in joined
    assert "Asking a Public" not in joined
    assert "Review Recorded Attaches" not in joined


def test_semantic_model_first_path_claim_uses_base_action_clause() -> None:
    semantic = asdict(
        build_greenfield_semantic_model(
            title="Classroom Accommodation Plan Tracker",
            state_object="Accommodation plan record",
            first_path=(
                "A support coordinator creates a plan from approved accommodations, assigns teacher responsibilities, "
                "marks what information is teacher-visible, and sends the plan for acknowledgment."
            ),
            proof_boundary="Release 0.0.1 succeeds when one coordinator can create a versioned plan.",
            components=[{"label": "Plan Intake"}],
            human_actors=["Support Coordinator: creating the plan and assigning responsibilities."],
        )
    )

    claim = semantic["proof_obligations"][0]["claim"]
    assert claim.startswith("Support Coordinator can create a plan")
    assert "can complete a support coordinator creates" not in claim.casefold()


def test_modal_drift_detector_allows_plural_objects_but_rejects_finite_actions() -> None:
    assert modal_base_form_drift_phrases("Evaluators can upload benchmark runs and see the visible result.") == []
    assert modal_base_form_drift_phrases("Requesters can submit records requests and see delivery status.") == []
    assert modal_base_form_drift_phrases("Drivers can report issues and see the visible result.") == []
    assert modal_base_form_drift_phrases(
        "Floor Operator can report a blocked aisle and map impacted robots and moves."
    ) == []
    assert modal_base_form_drift_phrases(
        "Floor Operator can report a blocked aisle and sees the result."
    ) == ["and sees"]
    assert modal_base_form_drift_phrases(
        "Release readiness requires evidence that a handoff summary that the incoming lead can acknowledge is correct."
    ) == []
    assert modal_base_form_drift_phrases("A decision about whether a model can progress is shown.") == []
    assert modal_base_form_drift_phrases(
        "The release must still prove: one site ingests readings, produces a plan, and shows the plan."
    ) == []
    assert modal_base_form_drift_phrases(
        "Review evidence must show the promised result: the path produces a plan and correctly raises a warning."
    ) == []
    assert modal_base_form_drift_phrases(
        "One resident can submit one application. The product explains missing input, and leaves the result reviewable."
    ) == []
    assert modal_base_form_drift_phrases("A coordinator accepts jobs that can be scheduled, and follows up.") == []
    assert modal_base_form_drift_phrases(
        "The plan should reduce grid draw, lets the owner approve it, monitors the result, and reports the outcome."
    ) == []
    assert modal_base_form_drift_phrases("Evaluators can runs, inspect failures.") == ["can runs"]
    assert modal_base_form_drift_phrases("Requesters can records proof.") == ["can records"]
    assert modal_base_form_drift_phrases("The user can coordinator creates packet state.") == [
        "can coordinator creates"
    ]
    assert base_gerund_clause("uploading benchmark runs and inspecting failures") == (
        "upload benchmark runs and inspect failures"
    )


def test_actor_led_common_workflow_verbs_compile_to_base_actions() -> None:
    first_path = (
        "A coordinator registers a shelter, updates bed and supply capacity, records a supply request, "
        "assigns a fulfillment owner, and publishes a public availability update with the latest status."
    )

    assert action_chain_fragment("A coordinator registers a shelter") == "register a shelter"
    assert backlog_actions.workflow_title_action(
        first_path=first_path,
        actor="Response Coordinator",
        fallback="register a shelter",
    ) == "register a shelter"
    assert backlog_actions.actor_interaction_action(
        first_path=first_path,
        actor="Response Coordinator",
        fallback="register a shelter",
    ) == "register a shelter"


def test_saved_destination_detector_allows_component_handoff_targets() -> None:
    assert generated_public_copy_issues(
        "component spec",
        "Submission Readiness Gate Service passes readiness gate result to Ledger Outcome Viewer.",
    ) == ()
    assert generated_public_copy_issues(
        "component spec",
        "The workflow saves result to ledger before review.",
    ) == ("component spec leaked saved-destination result prose",)


def test_confirmed_guidance_prompt_modal_objects_and_decisions_stay_coherent() -> None:
    model_prompt = (
        "Draft a greenfield proposal for an AI model evaluation lab where evaluators upload benchmark runs, "
        "risk reviewers inspect failures, and release managers decide whether a model can progress."
    )
    model_proposal = _proposal_from_guidance_prompt(model_prompt)
    model_rendered = json.dumps(model_proposal, sort_keys=True)

    assert greenfield_quality_issues(model_proposal) == []
    assert generated_semantic_slop_issues(model_proposal) == []
    assert model_proposal["semantic_model"]["first_path_contract"]["visible_result"] == (
        "a decision about whether a model can progress"
    )
    assert model_proposal["semantic_model"]["proof_obligations"][0]["claim"] == (
        "Evaluators can upload benchmark runs and inspect failures."
    )
    assert "can runs" not in model_rendered
    assert "can run and inspect failures" not in model_rendered
    assert "can upload benchmark runs and inspecting failures" not in model_rendered
    assert "reach a model can progress" not in model_rendered
    assert "see Release managers decide" not in model_rendered

    records_prompt = (
        "Draft a greenfield proposal for a public records request tracker where requesters submit records requests, "
        "clerks classify exemptions, legal reviewers approve redactions, and requesters see delivery status."
    )
    records_proposal = _proposal_from_guidance_prompt(records_prompt)
    records_rendered = json.dumps(records_proposal, sort_keys=True)

    assert greenfield_quality_issues(records_proposal) == []
    assert generated_semantic_slop_issues(records_proposal) == []
    assert records_proposal["semantic_model"]["proof_obligations"][0]["claim"] == (
        "Requesters can submit records requests, classify exemptions, approve redactions, and see delivery status."
    )
    assert "submit can record requests" not in records_rendered


def test_workflow_opportunity_does_not_repeat_visible_result_when_action_already_names_it() -> None:
    rows = confirmed_backlog_rows(
        label="Offshore Wind Maintenance Planning",
        parent_title="Prove One Complete Offshore Wind Maintenance Planning Path",
        workflow_title="Let Offshore Wind Maintenance Use a Daily Maintenance Plan",
        boundary_title="Keep Published Daily Maintenance Plan Record Clear",
        proof_title="Show Why Published Daily Maintenance Plan Record Can Be Trusted",
        product_story=(
            "Port operators need to compare work windows, resource readiness, and approval evidence before publishing a plan."
        ),
        state_object="A published daily maintenance plan record.",
        evidence_record="Offshore Wind Maintenance Planning Proof Record",
        first_path=(
            "Offshore wind maintenance publishes a daily maintenance plan after comparing telemetry, weather, vessel, "
            "technician, spare-part, and safety approval evidence."
        ),
        proof_boundary="Release succeeds when a daily maintenance plan can be published with reviewable evidence.",
        components=[
            {"component_id": "planner", "label": "Planning Service", "release_scope": "first_path_required"},
            {"component_id": "review", "label": "Review Workspace", "release_scope": "first_path_required"},
            {"component_id": "proof", "label": "Proof Ledger", "release_scope": "first_path_required"},
        ],
        internal_systems=["Planning service", "Review workspace", "Proof ledger"],
        human_actors=["Offshore wind maintenance planner"],
        external_systems=[],
        non_goals=[],
        success_metrics=[],
        problem="Maintenance planners need one clear plan.",
        customer="Maintenance planners",
        opportunity="Publish a reviewable plan.",
        product_view="Planner publishes the plan with evidence.",
        diagram_slugs={
            "context": "context",
            "sequence": "sequence",
            "state_evidence": "state-evidence",
            "component_boundaries": "component-boundaries",
            "ownership": "ownership",
            "proof_review": "proof-review",
        },
    )
    workflow = rows[1]
    text = json.dumps(workflow)

    assert "can review a daily maintenance plan" in text
    assert "keeps the saved result reviewable" in text
    assert "lets the offshore wind maintenance use a daily maintenance plan" not in text


def test_agent_os_confirmed_path_repairs_internal_actions_and_reviewed_result_copy() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
# AI Agent OS

## Product story
AI Agent OS is a workspace-native operating layer for coordinating AI agents as accountable collaborators.

## State object
The core state object is an agent workspace with goals, active tasks, agent roles, tool permissions, source context, memory, artifacts, decisions, validation evidence, and unresolved risks.

## First complete path
A user opens a workspace, describes a project goal, and the system turns that intent into a bounded plan. The OS assigns work to one or more agents, controls tool access, tracks progress, captures artifacts, runs validation, and returns a reviewed outcome with a clear audit trail.

## Human actors
- Operator who sets goals and approves meaningful actions
- Reviewer who inspects agent outputs, evidence, and risks

## Internal product systems
- Intent intake and goal shaping
- Agent orchestration and task routing
- Permission and tool-access control
- Human control surface for status, approvals, and intervention

## Critical assumptions
- Trust, auditability, and recoverability are product requirements, not later enterprise add-ons.

## Proof boundary
The first proof should show that a user can start with a broad goal, get a structured plan, delegate bounded work to agents, inspect progress, approve risky actions, validate outputs, and preserve useful memory for the next session.
""",
            prompt="Draft an AI Agent OS proposal.",
        )
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft an AI Agent OS proposal.",
        title=str(intent["title"]),
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)
    systems = "\n".join(intent.get("internal_systems", []))
    brief = json.dumps(proposal.get("project_brief"), sort_keys=True)

    assert "not later enterprise add-ons" not in "\n".join(intent.get("non_goals", [])).casefold()
    assert first_path_capability_phrase(intent["first_path"], max_fragments=8) == (
        "open a workspace, describe a project goal, and see an outcome with a clear audit trail"
    )
    assert outcome_action_phrase("a reviewed outcome with a clear audit trail") == (
        "review an outcome with a clear audit trail"
    )
    assert "reviewed outcome" not in rendered.casefold()
    assert "review a reviewed outcome" not in rendered.casefold()
    assert "a outcome" not in rendered.casefold()
    assert "covers status approvals" not in rendered.casefold()
    assert "can controls tool access" not in rendered.casefold()
    assert "controls tool access with success" not in rendered.casefold()
    assert "supports status approvals" not in systems.casefold()
    assert "Trust, auditability, and recoverability are product requirements" in brief
    assert generated_semantic_slop_issues(proposal) == []


def test_rendered_package_judgment_rejects_role_quality_failures() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        backlog_result={
            "idea_files": {
                "odylith/radar/source/W-001.md": (
                    "Users can operator controls tool access. "
                    "Users can review a reviewed outcome with a clear audit trail. "
                    "Trust is a product requirement, not later enterprise add-ons. "
                    "- deferred for now: Trust is a product requirement, not later enterprise add-ons waits for a later wave."
                )
            }
        },
        rendered_component_specs={
            "Human Control Surface.md": (
                "Accepted inputs: covers status approvals, authorized actor, and validation context.\n"
                "Produced outputs: gate story name result."
            )
        },
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert any("repeats an outcome modifier" in issue for issue in issues)
    assert any("internal processing as a user capability" in issue for issue in issues)
    assert any("component-contract noun slots" in issue for issue in issues)
    assert any("turns a requirement stated as `not later` into deferred scope" in issue for issue in issues)


def test_reviewed_result_normalization_preserves_multi_word_result_nouns() -> None:
    assert (
        normalize_reviewed_result_nouns("review a reviewed installation plan with blockers")
        == "review an installation plan with blockers"
    )


def test_state_reference_preserves_participial_descriptions_without_embedding_finite_restatements() -> None:
    proposal = {
        "intent": {
            "state_object": (
                "A live processing pipeline holding ordered streams of signal samples, each moving through "
                "a chain of stages (ingest, transform, detect, emit)."
            )
        }
    }

    assert state_reference(proposal) == (
        "a live processing pipeline holding ordered streams of signal samples, each moving through "
        "a chain of stages (ingest, transform, detect, emit)"
    )
    assert "Live Processing Pipeline Holding" not in state_reference(proposal)

    structured = {
        "intent": {
            "state_object": (
                "The unit of truth is a child's growing sense of agency: their profile, "
                "the scenarios they've worked through, and the decisions they made."
            )
        }
    }
    assert state_reference(structured) == "child's growing sense of agency"
    assert "worked through" not in state_reference(structured)

    finite_restatement = {
        "intent": {
            "state_object": (
                "A service readiness record tracks request identity, findings, review status, correction owner, "
                "and completion evidence."
            )
        }
    }
    assert state_reference(finite_restatement) == "service readiness record"
    assert "record tracks" not in state_reference(finite_restatement)
    assert object_reference_phrase(state_reference(finite_restatement)) == "the service readiness record"

    articleless_finite_restatement = {
        "intent": {
            "state_object": (
                "Permit application records the current status, actor, source input, decision, blocked reason, "
                "evidence links, timestamp, and version history for the accepted first path."
            )
        }
    }
    assert state_reference(articleless_finite_restatement) == "permit application"
    assert "records the current status" not in state_reference(articleless_finite_restatement)


def test_confirmed_diagram_labels_summarize_release_proof_and_deferred_scope_before_trimming() -> None:
    proof = (
        "A reviewer can complete one review, catch one mismatch, see correction ownership, "
        "and leave with readiness evidence without claiming automated follow-up."
    )

    assert diagram_text.release_proof_label(proof) == "A reviewer can complete one review, catch one mismatch"
    assert not diagram_text.release_proof_label(proof).endswith(", catch")
    assert diagram_text.semantic_proof_checkpoint(
        {"first_path_contract": {"visible_result": "their estimated total burn compared with the target"}}
    ) == "their estimated total burn compared with the target"
    assert diagram_text.diagram_sentence_label("their estimated total burn compared with the target") == (
        "their estimated total burn compared with the target"
    )
    blocking_proof = (
        "An inspector can complete one inspection, catch one blocking issue, assign one correction, "
        "and leave with readiness evidence."
    )
    assert "catch one blocking issue" in diagram_text.trim(diagram_text.release_proof_label(blocking_proof), 82)
    assert not diagram_text.release_proof_label(blocking_proof).endswith(", assign")
    release_boundary = (
        "Release 0.0.1 is complete when one research lead can map claims to evidence, "
        "resolve one missing-section blocker, and see a readiness decision."
    )
    assert diagram_text.release_proof_label(release_boundary) == "one research lead can map claims to evidence"
    assert diagram_text.deferred_scope_label(release_boundary) == "beyond accepted first path"
    succeeds_boundary = (
        "Release 0.0.1 succeeds when one learner can start a practice session, receive feedback, "
        "and see a learning summary."
    )
    assert diagram_text.deferred_scope_label(succeeds_boundary) == "beyond accepted first path"
    assert (
        diagram_text.deferred_scope_label(
            "Do not expand beyond opening the checklist, recording findings, validating one mismatch, "
            "and producing one readiness proof."
        )
        == "beyond accepted first path"
    )
    assert diagram_text.deferred_scope_label("Do not claim automated follow-up or external integration.") == (
        "automated follow-up or external integration"
    )
    assert diagram_text.deferred_scope_label(
        "Calendar automation, maintenance dispatch, and multi-venue rollout are deferred until the first loop works."
    ) == "Calendar automation, maintenance dispatch, and multi-venue rollout"
    assert diagram_text.deferred_scope_label("Evidence Review History Service") == "Evidence Review History Service"


def test_proof_record_labels_do_not_duplicate_existing_proof_record_names() -> None:
    assert (
        confirmed_evidence_record_label(
            label="Inspection Workspace",
            proof_boundary="The release is proven when evidence is reviewed.",
            internal_systems=["Release Proof Record"],
        )
        == "Release Proof Record"
    )
    assert (
        confirmed_evidence_record_label(
            label="Inspection Workspace",
            proof_boundary="The release is proven when evidence is reviewed.",
            internal_systems=["Readiness Evidence Review"],
        )
        == "Readiness Evidence Review Proof Record"
    )
    assert (
        confirmed_evidence_record_label(
            label="Inspection Workspace",
            proof_boundary="The release is proven when evidence is reviewed.",
            internal_systems=["Release Proof Ledger"],
        )
        == "Release Proof Ledger Record"
    )
    assert diagram_text.proof_evidence_label(
        components=[{"label": "Release Proof Ledger"}],
        fallback="Release Evidence",
    ) == "Release Proof Ledger Record"


def test_result_term_coverage_matches_inflected_result_words_to_base_actions() -> None:
    assert backlog_text.result_terms_covered(
        "published reproducible result packets",
        "research teams register molecular targets; review convergence failures; publish reproducible result packets",
    )


def test_semantic_model_persistence_uses_state_label_instead_of_raw_state_sentence() -> None:
    model = build_greenfield_semantic_model(
        title="Venue Safety Inspection",
        state_object=(
            "A venue inspection record tracks location identity, checklist findings, issue severity, "
            "corrective owner, correction status, review evidence, and opening readiness."
        ),
        first_path=(
            "An inspector opens a checklist, records findings, flags one blocking issue, "
            "and sees whether the venue is ready to open."
        ),
        proof_boundary="An inspector can complete one inspection and leave with readiness evidence.",
        components=[],
        human_actors=["Inspector"],
        external_systems=[],
        internal_systems=["Inspection checklist capture"],
        non_goals=[],
    )

    assert model.first_path_contract.persistence == (
        "the venue inspection record must remain replayable after the accepted first path updates the saved state."
    )
    assert ". must remain replayable" not in model.first_path_contract.persistence


def test_cleaned_text_dedupe_stays_in_text_owner() -> None:
    text_source = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    callers = [
        SEMANTIC_QUALITY_PATH,
        FIRST_PATH_SEMANTICS_PATH,
        FIRST_PATH_CLAUSES_PATH,
    ]

    assert "def unique_text" in text_source
    steps = first_path_steps(
        "1. **Reviewer** records `status`. "
        "2. reviewer records status. "
        "3. Product shows result."
    )
    assert steps == (
        "Reviewer records status",
        "Product shows result",
    )
    assert not generated_semantic_slop_issues(
        [
            "`specific proof` stays visible",
            "specific proof stays visible",
        ],
        root="proof",
    )

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "unique_text" in source
        assert "seen: set[str]" not in source
        assert "key = text.casefold()" not in source
        assert "seen.add(key)" not in source


def test_compound_first_path_splits_allocation_and_result_events_without_domain_rules() -> None:
    first_path = (
        "A regional coordinator opens the dashboard, sees an area where signal growth and capacity pressure "
        "are accelerating past a threshold, drills into the trend, allocates additional response supply and "
        "flags a public advisory, and the incident record updates to reflect the new interventions and a "
        "revised projection — one full loop from signal to decision to recorded action."
    )

    model = first_path_model(first_path)
    sequence = sequence_event_steps(first_path)

    assert model.steps == (
        "A regional coordinator sees an area where signal growth and capacity pressure are accelerating past a threshold",
        "A regional coordinator drills into the trend",
        "A regional coordinator allocates additional response supply and flags a public advisory",
        "The incident record updates to reflect the new interventions and a revised projection",
    )
    assert model.visible_outcome == "The incident record updates to reflect the new interventions and a revised projection"
    assert sequence == [
        "A regional coordinator sees an area where signal growth and capacity pressure are accelerating past a threshold",
        "A regional coordinator drills into the trend",
        "A regional coordinator allocates additional response supply",
        "A regional coordinator flags a public advisory",
        "The incident record updates to reflect the new interventions and a revised projection",
    ]
    assert "one full loop" not in " ".join(sequence).casefold()
    assert gerund_action_fragment("A regional coordinator allocates supply and flags an advisory") == (
        "allocating supply and flagging an advisory"
    )


def test_coordinated_object_phrase_does_not_split_surface_findings_as_action() -> None:
    first_path = (
        "A restaurant manager opens the audit checklist. They scan a station, record ingredient and surface findings, "
        "flag an allergen mismatch, assign a correction owner, mark the correction complete, and see the kitchen "
        "readiness status update for service."
    )

    sequence = sequence_event_steps(first_path)
    clauses = first_path_clauses(first_path)

    assert sequence == [
        "A restaurant manager opens the audit checklist",
        "They scan a station",
        "A restaurant manager records ingredient and surface findings",
        "A restaurant manager flags an allergen mismatch",
        "A restaurant manager assigns a correction owner",
        "A restaurant manager marks the correction complete",
        "A restaurant manager sees the kitchen readiness status update for service",
    ]
    assert "record ingredient and surface findings" in clauses.capability_chain
    assert "surfacing findings" not in clauses.capability_chain
    assert gerund_action_fragment("A restaurant manager records ingredient and surface findings") == (
        "recording ingredient and surface findings"
    )
    assert generated_semantic_slop_issues({"first_path": clauses.capability_chain}) == []


def test_first_path_action_skips_context_and_named_launcher_when_material_actions_follow() -> None:
    first_path = (
        "A participant notices an issue, opens IncidentLog, taps to start a new entry, "
        "marks the location and severity, optionally notes the trigger context, and saves. "
        "The entry appears immediately in the history list, and once a few entries exist the product "
        "shows a simple pattern summary."
    )

    clauses = first_path_clauses(first_path)
    workflow_title, _boundary_title, _proof_title = confirmed_workstream_titles(
        label="IncidentLog",
        components=[
            {"label": "Entry Capture Service"},
            {"label": "History Service"},
            {"label": "Pattern Summary Service"},
            {"label": "Release Proof Service"},
        ],
        internal_systems=[
            "Entry capture",
            "History",
            "Pattern summary",
            "Release proof",
        ],
        first_path=first_path,
        state_object="An incident entry with location, severity, context, and review history.",
        proof_boundary="The proof is one participant capturing an entry and seeing a summary.",
        human_actors=["Affected User"],
    )

    assert first_path_action_phrase(first_path, max_fragments=1) == "tap to start a new entry"
    assert clauses.action_chain == (
        "tap to start a new entry and mark the location and severity, optionally note the trigger context and save"
    )
    assert "notices an issue" not in clauses.action_chain
    assert "opens IncidentLog" not in clauses.action_chain
    assert "optionally notes" not in clauses.action_chain
    assert "optionally notes" not in diagram_text.brief_first_path(first_path)
    assert "optionally note the trigger context" in diagram_text.brief_first_path(first_path)
    assert workflow_title == "Let Affected User See a Simple Pattern Summary"
    assert "Notice" not in workflow_title
    assert "Open IncidentLog" not in workflow_title


def test_backlog_rationale_does_not_clip_connector_interrupter_or_scope_predicate() -> None:
    proof_boundary = (
        "The product is proven when a user can capture an event in seconds and, after several entries, "
        "see a history and a basic pattern summary that reflects their real activity. "
        "External integrations, exports, and multi-user roles are explicitly out of scope for this first proof."
    )

    proof_focus = backlog_text.rationale_proof_focus(
        proof_boundary,
        fallback="tap to start a new entry and review a simple pattern summary",
    )
    release_basis = backlog_text.rationale_release_basis(
        title="Prove One Complete IncidentLog Path",
        label="IncidentLog",
        first_slice="tap to start a new entry, mark the location and severity, and review a simple pattern summary",
        proof_boundary=proof_boundary,
    )
    rationale = backlog_text.rationale_lines(
        label="IncidentLog",
        title="Prove One Complete IncidentLog Path",
        opportunity="Prove One Complete IncidentLog Path gives release planning one complete path",
        first_slice="tap to start a new entry, mark the location and severity, and review a simple pattern summary",
        proof_boundary=proof_boundary,
        deferred_scope=[
            "External integrations, exports, and multi-user roles are explicitly out of scope for this first proof."
        ],
    )

    assert "after several entries" in proof_focus
    assert "see a history and a basic pattern summary" in proof_focus
    assert "after several entries in the same release story" not in release_basis
    assert "see a history and a basic pattern summary" in release_basis
    assert rationale[3].startswith("- deferred for now: Prove One Complete IncidentLog Path:")
    assert "external integrations, exports, and multi-user roles wait for" in rationale[3].casefold()
    assert "out of scope for this first proof wait" not in rationale[3]


def test_package_quality_does_not_split_valid_connector_interrupter_as_dangling_and() -> None:
    text = (
        "The product is proven when a user can capture an event in seconds and, after several entries, "
        "see a history and a basic pattern summary."
    )
    artifact = RenderedArtifact("Project brief preview", "project_brief", text)
    issues = [
        issue
        for chunk in _narrative_chunks(text)
        for issue in _chunk_language_issues(artifact, chunk)
    ]

    assert issues == []
    assert "a user can capture an event in seconds and" not in _narrative_chunks(text)


def test_inline_role_casing_drift_allows_hyphenated_title_labels() -> None:
    assert not has_inline_role_casing_drift("Self-experimenter or Quantified-self User")
    assert not has_inline_role_casing_drift("Actors include Coordinator, Requester, and Equipment Reviewer.")
    assert not has_inline_role_casing_drift("The map shows Coordinator, outside inputs, and Item Record Service.")
    assert has_inline_role_casing_drift("the station Lead cannot act on the result")


def test_accepted_project_memory_normalizes_adverbial_action_copy() -> None:
    payload = build_accepted_project_source_payload(
        proposal={
            "intent": {
                "title": "IncidentLog",
                "first_path": "A user marks a location, optionally notes context, and saves.",
                "summary": "Release stays bounded to: A user marks a location, optionally notes context, and saves.",
            },
            "semantic_model": {
                "first_path_contract": {
                    "events": [
                        {"text": "Mark a location, optionally notes context and save"},
                    ],
                },
            },
        },
        backlog_items=[],
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="release-incidentlog-0-0-1",
        validation_gate={"status": "passed"},
    )
    rendered = json.dumps(payload, sort_keys=True)

    assert "optionally notes" not in rendered
    assert "optionally note context" in rendered


def test_accepted_project_memory_preserves_canonical_apply_first_path_over_event_padding() -> None:
    accepted_path = (
        "Review teams track source evidence, owner attestations, queue holds, inspection outcomes, "
        "exception notes, and release proof before a record closes."
    )
    event_padded_path = (
        "Review teams track source evidence, owner attestations. Queue holds, inspection outcomes, "
        "exception notes, and release proof before a record closes. Review evidence for queue holds."
    )
    payload = build_accepted_project_source_payload(
        proposal={
            "intent": {
                "title": "Review Workspace",
                "first_path": accepted_path,
                "summary": f"Release stays bounded to: {accepted_path}",
            },
            "apply_semantic_input": {"first_path": accepted_path},
            "semantic_model": {
                "first_path_contract": {
                    "raw_path": event_padded_path,
                    "events": [
                        {"text": "Review teams track source evidence, owner attestations"},
                        {"text": "Queue holds, inspection outcomes, exception notes, and release proof before a record closes"},
                        {"text": "Review evidence for queue holds"},
                    ],
                },
            },
        },
        backlog_items=[],
        component_items=[],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="release-review-workspace-0-0-1",
        validation_gate={"status": "passed"},
    )

    proposal = payload["proposal"]

    assert proposal["intent"]["first_path"] == accepted_path
    assert proposal["semantic_model"]["first_path_contract"]["raw_path"] == accepted_path


def test_status_view_responsibility_avoids_presentational_action_splice() -> None:
    responsibility = responsibility_from_contract(
        "Review Assignment and Status Tracking Service",
        {
            "owned_state": "review assignment and status tracking, review status, blocker context, and handoff evidence",
            "accepted_inputs": "submitted permit application",
            "produced_outputs": "review status readout",
            "unique_failure": "review status is missing or stale",
        },
    )

    payload = build_accepted_project_source_payload(
        proposal={
            "intent": {"title": "Permit Portal", "first_path": "Submit application."},
            "components": [{"label": "Review Assignment and Status Tracking Service", "responsibility": responsibility}],
            "semantic_model": {"first_path_contract": {"events": [{"text": "Submit application"}]}},
        },
        backlog_items=[],
        component_items=[{"component_id": "review-status", "label": "Review Assignment and Status Tracking Service", "responsibility": responsibility}],
        diagram_ids=[],
        release_selector="0.0.1",
        release_id="release-permit-0-0-1",
        validation_gate={"status": "passed"},
    )

    rendered = json.dumps(payload, sort_keys=True)
    assert "Presents review assignment" not in rendered
    assert "Keeps review assignment and status tracking" in rendered
    assert generated_public_copy_issues("accepted-project memory preview", payload) == ()


def test_confirmed_project_brief_next_steps_normalize_adverbial_action_copy() -> None:
    brief = confirmed_project_brief(
        label="EventLog",
        prompt="Build a simple event logger",
        release="0.0.1",
        state_object="event record",
        evidence_record="event proof record",
        first_path=(
            "A user opens EventLog, marks the location and severity, optionally notes the trigger context, "
            "and saves. The event appears in history."
        ),
        product_story="EventLog helps a user capture one incident quickly and review it later.",
        proof_boundary="The product is proven when an event can be saved and reviewed.",
        internal_systems=["event capture", "event history"],
    )
    rendered = json.dumps(brief["coding_readiness_gates"], sort_keys=True)

    assert "optionally notes" not in rendered
    assert "optionally note the trigger context" in rendered


def test_confirmed_project_brief_summarizes_long_boundary_without_clipped_tail() -> None:
    brief = confirmed_project_brief(
        label="Regional Coordination Workspace",
        prompt="Coordinate a regional incident across partner teams.",
        release="0.0.1",
        state_object=(
            "A coordination record with support request, access restriction, capacity constraint, "
            "resource commitment, readiness, approval decision, and public coordination status."
        ),
        evidence_record="Coordination Proof Record",
        product_story=(
            "A regional office coordinates partner decisions, separates private evidence from public status, "
            "and publishes a trusted coordination status before field teams act."
        ),
        first_path=(
            "City dispatcher records support request, tribal liaison reviews access needs, hospital coordinator "
            "records capacity constraints, mutual-aid officer confirms resource commitments, shelter lead records "
            "readiness, and emergency commander publishes public coordination status."
        ),
        proof_boundary=(
            "Release 0.0.1 is proven when one support request moves through access review, hospital capacity "
            "constraint recording, resource commitment confirmation, shelter readiness recording, and public "
            "coordination status publication while private resident and partner details remain inside the governed boundary."
        ),
        human_actors=[
            "City dispatcher",
            "Tribal liaison",
            "Hospital coordinator",
            "Mutual-aid officer",
            "Shelter lead",
            "Emergency commander",
        ],
        internal_systems=[
            "Request intake",
            "Access review board",
            "Capacity constraint ledger",
            "Resource commitment tracker",
            "Readiness board",
            "Public coordination status view",
        ],
    )

    outcome = str(brief["project_outcome"])
    assert not outcome.casefold().rstrip(" .").endswith(("remain", "remains", "with"))
    assert "details remain" not in outcome.casefold()
    assert generated_public_copy_issues("project brief preview", outcome) == ()


def test_confirmed_backlog_success_metrics_use_compact_state_reference() -> None:
    intent = parse_confirmed_intent_text(
        """
# Municipal Permit Review Portal

## Product story
A resident submits a building permit application online so the city can check completeness and return an approval or correction request.

## State object
Permit application records the current status, actor, source input, decision, blocked reason, evidence links, timestamp, and version history for the accepted first path.

## First complete path
The resident starts an application, enters project and property details, uploads required documents, pays the fee, and submits the package. The portal validates completeness and returns an approved permit or a correction request.

## Human actors
- Resident applicant
- Permit reviewer

## External systems
- Payment processor

## Internal product systems
- Application intake workflow
- Completeness validation
- Decision response publishing

## Proof boundary
Release 0.0.1 is complete when one resident can submit one application, receive validation feedback, and see a decision or correction request.
"""
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft a municipal permit review portal.",
        title="Municipal Permit Review Portal",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    proposal = normalize_host_reasoned_proposal(proposal)
    for row in proposal.get("backlog", [])[1:]:
        if isinstance(row, dict):
            row["success_metrics"] = []

    completed = complete_confirmed_proposal(proposal, release_selector="0.0.1")
    rendered = json.dumps(completed, sort_keys=True)

    assert "to the permit application records the current status" not in rendered
    assert "to the permit application" in rendered


def test_confirmed_project_brief_localizes_generic_first_path_actor_from_accepted_roles() -> None:
    intent = parse_confirmed_intent_text(
        """
# Cooking Robot Controller

## Product story
A control system turns a recipe into safe repeatable physical cooking. A home cook selects a dish and the controller sequences motions, dosing, heat, and safety stops.

## State object
A cook session: active recipe, current step, sensor readings, actuator state, and safety status.

## First complete path
Operator picks a recipe, the controller validates the robot is ready, runs the step sequence, surfaces progress, and reaches a finished safe state.

## Human actors
- Home cook / operator who selects dishes and responds to prompts
- Kitchen technician who calibrates, maintains, and clears faults
- Recipe author who defines the step-by-step cooking program

## External systems
- Robot hardware: arm actuators, ingredient dispensers, and heat element
- Sensors: temperature probes, scales, and presence sensing
- Emergency-stop hardware interlock

## Internal product systems
- Recipe / step sequencer that interprets cooking programs
- Real-time control loop for heat, timing, and motion
- Safety supervisor that can override the sequencer
- Session and telemetry state tracking the live cook

## Critical assumptions
- A single robot cell per controller instance for the first version
- Recipes are pre-authored structured programs

## Ambiguities
- Software simulation/controller only, or driving real hardware from day one?
- Target host: embedded device, edge box, or general server?

## Proof boundary
First version proves load a recipe, run its steps with closed-loop control, hit a safe finished state, and honor an emergency stop.
""",
        prompt="Draft a greenfield proposal for a cooking robot controller",
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft a greenfield proposal for a cooking robot controller",
        title="Cooking Robot Controller",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    first_path = proposal["project_brief"]["blueprint_sections"][1]["must_capture"]
    rendered = json.dumps(proposal, sort_keys=True)
    issues = greenfield_quality_issues(proposal)

    assert first_path.startswith("Home cook picks a recipe")
    assert "Operator picks a recipe" not in rendered
    assert "Home Cook / Operator" not in rendered
    assert "home cook pick recipe" not in rendered.casefold()
    assert "runs step sequence until" not in rendered.casefold()
    assert "sequence until cooking reach" not in rendered.casefold()
    assert "part of the result, explanation, and evidence it is responsible for" not in rendered
    assert not any("generic actor label `Operator`" in issue for issue in issues)
    assert not any("mixed actor-role casing" in issue for issue in issues)
    assert not any("clipped or unfinished" in issue for issue in issues)


def test_confirmed_intent_accepts_concise_system_actions_and_release_success_proof() -> None:
    intent = parse_confirmed_intent_text(
        """
# Residential Solar Quote Planner

Product story:
A homeowner wants to compare a practical solar installation option without reading a spreadsheet of assumptions. A solar coordinator needs a consistent quote record that explains roof fit, usage assumptions, incentive assumptions, estimated savings, and follow-up risk.

State object:
The central state is a solar quote with homeowner profile, address assumptions, roof area estimate, usage baseline, system size, incentive assumptions, estimated cost, savings range, risk notes, and follow-up status.

First complete path:
A homeowner enters address and usage details, reviews the estimated system size, sees savings and cost assumptions, flags a roof or incentive uncertainty, and sends the quote to a solar coordinator for review.

Human actors:
- Homeowner: provides address and usage assumptions and reviews the quote.
- Solar coordinator: reviews assumptions, explains risk, and decides whether the quote is ready for follow-up.

External systems:
- Utility tariff reference, simulated for the first release.
- Roof imagery service, deferred until manual roof assumptions are stable.

Internal product systems:
- Quote Intake captures homeowner inputs.
- System Sizing Model estimates panel count and production.
- Incentive Assumption Ledger records assumptions and uncertainty.
- Coordinator Review Board decides follow-up readiness.

Critical assumptions:
- Release 0.0.1 handles one address and one quote at a time.
- Estimates are advisory and must show assumptions clearly.

Ambiguities:
- Financing products are deferred.
- Live utility integrations are deferred.

Proof boundary:
Release 0.0.1 succeeds when one homeowner can produce a reviewable solar quote and one coordinator can decide whether it is ready for follow-up.
""",
        prompt="Create a residential solar quote planner.",
    )
    proposal = build_greenfield_proposal(
        repo_root=Path("/tmp/nonexistent"),
        prompt="Create a residential solar quote planner.",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert len(intent["internal_systems"]) == 4
    assert "Coordinator Review Board" in " ".join(intent["internal_systems"])
    assert len(proposal["backlog"]) >= 3
    assert len(proposal["components"]) >= 3
    assert len(proposal["diagrams"]) >= 2
    assert greenfield_quality_issues(proposal) == []
    assert not re.search(r"\bstate owner\b", rendered, flags=re.IGNORECASE)
    assert not re.search(r"\bevidence owner\b", rendered, flags=re.IGNORECASE)


def test_stale_generic_label_detector_does_not_match_evidence_ownership_words() -> None:
    assert _contains_stale_generic_label("Evidence owner: approves release proof.", "Evidence owner")
    assert not _contains_stale_generic_label(
        "Missing Evidence ownership stays outside the boundary owned by Application Intake.",
        "Evidence owner",
    )


def test_sentence_shaped_internal_systems_keep_concise_component_labels() -> None:
    intent = parse_confirmed_intent_text(
        """
# Cooking Robot Controller

Product story:
A control system turns a recipe into safe, repeatable physical cooking for a home cook. The product coordinates recipe steps, heat, timing, sensors, and emergency stop behavior so the first release can prove a complete supervised cook session without free-form recipe interpretation.

State object:
A cook session with active recipe, current step, live sensor readings, actuator state, and safety status.

First complete path:
The home cook picks a recipe, the controller validates that ingredients are staged and sensors are live, runs the step sequence with closed-loop heat and timing control, shows progress, and reaches a finished safe-to-serve state with emergency stop available throughout.

Human actors:
- Home cook who selects dishes and responds to prompts
- Kitchen technician who calibrates and clears faults

External systems:
- Robot hardware with arm, ingredient dispenser, and heat element interfaces
- Sensors for temperature, load, and presence
- Emergency stop hardware interlock

Internal product systems:
- Recipe sequencer that turns a structured cooking program into ordered actions
- Real-time control loop for heat, timing, and motion
- Safety supervisor that enforces limits, interlocks, and abort logic
- Session telemetry state that records the live cook

Critical assumptions:
- One robot cell per controller instance for the first release
- Recipes are pre-authored structured programs

Ambiguities:
- Whether first release drives real hardware or a simulator

Proof boundary:
Release 0.0.1 succeeds when a home cook can load a structured recipe, run its cooking steps with closed-loop heat and timing, reach a safe finished state, and trigger emergency stop at any point in a hardware simulator.
""",
        prompt="Draft a greenfield proposal for a cooking robot controller",
    )

    proposal = build_greenfield_proposal(
        repo_root=Path("/tmp/nonexistent"),
        prompt="Draft a greenfield proposal for a cooking robot controller",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    labels = [str(row["label"]) for row in proposal["components"]]
    release_labels = [str(row["label"]) for row in active_release_components(proposal["components"])]
    rendered = json.dumps(proposal, sort_keys=True)
    backlog_copy = json.dumps(proposal["backlog"], sort_keys=True)
    readiness_copy = json.dumps(proposal["project_brief"]["coding_readiness_gates"], sort_keys=True)
    prewrite_proposal = proposal_with_component_brief_gate(proposal)
    prewrite_readiness_copy = json.dumps(prewrite_proposal["project_brief"]["coding_readiness_gates"], sort_keys=True)
    release_contract_copy = json.dumps(active_release_components(proposal["components"]), sort_keys=True)
    package = GreenfieldCompletionPackage(proposal=proposal)

    assert any(row.rstrip(".") == "Home Cook: selects dishes and responds to prompts" for row in intent["human_actors"])
    assert not re.search(r"Home Cook: uses the product to .+controller validates", rendered)
    assert "runing" not in rendered.casefold()
    assert "Recipe Sequencer Service" in labels
    assert "Safety Supervisor Service" in labels
    assert "Session Telemetry State Service" not in release_labels
    assert "Session Telemetry State Service" not in release_contract_copy
    assert "Session Telemetry State Service" not in prewrite_readiness_copy
    assert "can consume" not in release_contract_copy
    assert "That Turns" not in rendered
    assert "That Enforces" not in rendered
    assert "progress, and reaches" not in backlog_copy.casefold()
    assert "then let the home cook reach a finished safe-to-serve state" not in backlog_copy.casefold()
    assert " to a finished safe-to-serve state with emergency stop available throughout without" not in backlog_copy.casefold()
    assert "throughout with reviewable" not in backlog_copy.casefold()
    assert not re.search(r"(?<!-)\bserve state\b", readiness_copy.casefold())
    assert "finished safe-to-serve state" in readiness_copy.casefold()
    assert proposal["semantic_model"]["first_path_contract"]["visible_result"] == (
        "a finished safe-to-serve state with emergency stop available throughout"
    )
    assert greenfield_quality_issues(proposal) == []
    assert not any(
        "explanatory component label" in issue for issue in greenfield_rendered_package_quality_issues(package)
    )
    assert _artifact_surface_language_issues(
        RenderedArtifact("Radar workstream", "bad.md", "- The first release proves runing the accepted path.")
    )
    assert _artifact_surface_language_issues(
        RenderedArtifact(
            "Radar workstream",
            "bad.md",
            "- users can reach the finished result without manual interpretation outside the product.",
        )
    )
    assert _artifact_surface_language_issues(
        RenderedArtifact(
            "Radar workstream",
            "bad.md",
            (
                "Prove the first release path: pick a recipe, validate the setup, and see a finished "
                "safe-to-serve state with emergency stop available throughout, then let the home cook reach "
                "a finished safe-to-serve state with emergency stop available throughout."
            ),
        )
    )
    assert _artifact_surface_language_issues(
        RenderedArtifact(
            "Radar workstream",
            "bad.md",
            (
                "The first interaction proves pick a recipe and see a finished safe-to-serve state "
                "with emergency stop available throughout and lets the home cook reach a finished "
                "safe-to-serve state with emergency stop available throughout."
            ),
        )
    )
    assert not _artifact_surface_language_issues(
        RenderedArtifact("Project brief preview", "actors", "Home Cook: selects dishes and responds to prompts.")
    )


def test_confirmed_project_brief_readiness_gates_do_not_embed_raw_action_lists() -> None:
    brief = confirmed_project_brief(
        label="Pattern Relief Notebook",
        prompt="Build a personal pattern notebook",
        release="0.0.1",
        state_object="person comfort timeline",
        evidence_record="trend evidence record",
        product_story=(
            "A person tracking recurring discomfort wants to understand which self-care actions appear to help "
            "over time. The product turns scattered daily notes into a small personal feedback loop: record how "
            "the day felt, record what action was tried, and review the pattern before deciding what to try next."
        ),
        first_path=(
            "A new user records their first entry — rates today's status, taps the factors that applied, and logs "
            "one action they tried. The next day they log again. After a handful of entries, the app shows a simple "
            "trend: status over time, and which logged actions line up with better days."
        ),
        proof_boundary=(
            "A user can log entries over several days and the app renders an honest trend plus an "
            "action-to-outcome signal from their own data."
        ),
        internal_systems=["entry logging", "trend and correlation view"],
    )
    rendered = json.dumps(brief["coding_readiness_gates"], sort_keys=True)

    assert generated_public_copy_issues("pattern readiness gates", brief["coding_readiness_gates"]) == ()
    assert "record how the day felt, record what action was tried" not in rendered
    assert "After a handful of entries." not in rendered
    assert "first implementation lane" in rendered
    assert "record first entry" in rendered
    assert "log again" in rendered
    assert "show a simple trend" in rendered


def test_system_label_join_does_not_clip_labels_containing_and() -> None:
    assert confirmed_system_name("Audit Trail and Records Export: preserves review history.") == "Audit Trail and Records Export"
    assert join_system_labels(
        [
            "Permit Intake and Completeness Check: records submitted materials and intake blockers.",
            "Audit Trail and Records Export: preserves review history and final decision evidence.",
        ],
        limit=4,
    ) == "Permit Intake and Completeness Check, Audit Trail and Records Export"


def test_workstream_intelligence_embeds_actor_problem_as_sentence_text() -> None:
    packet = build_workstream_domain_intelligence(
        label="Municipal Permit Review Workspace",
        row_title="Prove One Complete Municipal Permit Review Workspace Path",
        problem="Applicant needs a dependable way to understand the permit application and decide what to do.",
        opportunity="Help reviewers move one permit application through a decision.",
        product_view="A reviewer publishes the permit decision record with evidence.",
        first_slice="Submit a permit packet and publish the decision record.",
        metrics=["A reviewer can publish one decision record with evidence."],
        dependencies=["Accepted participants and required source context."],
        interfaces=["Permit intake, review checklist, and decision record."],
        validation=["Run the complete user path and one correction path."],
        state_object="Permit Application",
        evidence_record="Audit Trail and Records Export Proof Record",
        first_path="An applicant submits a packet and a reviewer publishes a decision.",
        proof_boundary="Release succeeds when one permit decision can be replayed.",
        human_actors=["Applicant: submits documents.", "Permit reviewer: records decision rationale."],
        internal_systems=["Permit Intake and Completeness Check", "Audit Trail and Records Export"],
        external_systems=["Document upload service"],
        non_goals=["Do not claim every permit type."],
    )

    rendered = json.dumps(packet, sort_keys=True)

    assert "The product problem is applicant needs" in rendered
    assert "The product problem is Applicant needs" not in rendered
    assert generated_semantic_slop_issues(packet) == []


def test_generated_copy_quality_rejects_mixed_adverbial_action_inflection() -> None:
    issues = generated_public_copy_issues(
        "operator next-steps preview",
        {"gate": "The first path is accepted: Mark location, optionally notes context and save."},
    )

    assert any("mixed finite/base action prose" in issue for issue in issues)


def test_generated_copy_quality_rejects_malformed_relative_clause_split() -> None:
    issues = generated_public_copy_issues(
        "Registry component spec `Revision Tracker`",
        "Owned state: applicant revisions to the documents, checks are meant to address, and blocker state.",
    )

    assert any("malformed relative-clause split" in issue for issue in issues)
    assert generated_semantic_slop_issues({"owned_state": "checks are meant to address"}) == [
        "malformed relative-clause split leaked at artifact.owned_state"
    ]


def test_first_path_flowchart_strips_clipped_terminal_final_label() -> None:
    source = (
        "A grant coordinator preserves denial reasons, evidence gaps, appeal package readiness, and final submission state."
    )
    mermaid = first_path_flowchart_mermaid(
        label="Grant Appeal Workspace",
        actors=["Grant coordinator"],
        components=[{"label": "Appeal Package Readiness Service", "release_scope": "first_path_required"}],
        first_path=source,
        semantic_model={
            "first_path_contract": {
                "events": [source],
                "visible_result": "appeal package readiness and final submission state",
            }
        },
    )

    assert "and final\"]" not in mermaid
    assert "and final<br/>" not in mermaid
    assert (
        "final<br/>submission state" in mermaid
        or "final submission<br/>state" in mermaid
        or "final submission state" in mermaid
    )
    assert not _artifact_surface_language_issues(
        RenderedArtifact("Atlas Mermaid", "grant-appeal-first-path.mmd", mermaid, kind="mermaid")
    )


def test_first_path_flowchart_keeps_coordinated_object_tail_and_allows_participant_actor() -> None:
    first_path = (
        "A participant records symptoms, triggers, chosen practice steps, check-in results, "
        "safety boundaries, and progress evidence."
    )
    semantic = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Daily Comfort Practice Coach",
            state_object="comfort practice record",
            first_path=first_path,
            proof_boundary="Release succeeds when progress evidence is reviewable.",
            components=[],
            human_actors=["Daily Comfort Practice Participant"],
        )
    )
    components = [
        {"label": "Intake Register Service", "release_scope": "first_path_required"},
        {"label": "Review Workspace", "release_scope": "first_path_required"},
        {"label": "Proof Ledger", "release_scope": "first_path_required"},
    ]

    steps = sequence_event_steps(first_path, semantic_model=semantic, dedupe=True)
    mermaid = first_path_flowchart_mermaid(
        label="Daily Comfort Practice Coach",
        actors=["Daily Comfort Practice Participant"],
        components=components,
        first_path=first_path,
        semantic_model=semantic,
    )
    issues: list[str] = []
    _check_first_path_flowchart(
        proposal={"intent": {"first_path": first_path}},
        components=components,
        title="First Path Sequence",
        source=mermaid,
        issues=issues,
    )

    assert "Record progress evidence" in steps
    assert "Progresses evidence" not in mermaid
    assert "And progress evidence" not in mermaid
    assert "participant records symptoms" not in mermaid.casefold()
    assert 'S3["Record progress evidence"]' in mermaid
    assert not [issue for issue in issues if "sequence/parser debris" in issue]


def test_package_quality_allows_plural_noun_after_to() -> None:
    text = "Routes comparison evidence to alternatives by fare, travel time, walking time, reliability, and preference."
    issues = _chunk_language_issues(
        RenderedArtifact("Registry component spec", "Option Ranking Engine", text),
        text,
    )

    assert looks_like_finite_action("alternatives placeholder") is False
    assert not any("to alternatives" in issue for issue in issues)


def test_package_quality_allows_noun_compounds_inside_modal_windows() -> None:
    text = "A reviewer can inspect Permit Intake and Completeness Check, Audit Trail and Records Export, and release proof."
    issues = _chunk_language_issues(
        RenderedArtifact("Registry component spec", "Audit Trail and Records Export", text),
        text,
    )
    bad = "A reviewer can submit a packet and records a decision."
    bad_issues = _chunk_language_issues(
        RenderedArtifact("Registry component spec", "Decision Record", bad),
        bad,
    )

    assert not any("and Records" in issue for issue in issues)
    assert any("and records" in issue for issue in bad_issues)


def test_package_quality_allows_terminal_paid_for_phrasal_verb() -> None:
    artifact = RenderedArtifact("Project brief preview", "project_brief", "paid for")

    issues = _chunk_language_issues(artifact, "paid for")

    assert not any("ending in `for`" in issue for issue in issues)


def test_actor_labels_keep_display_casing_but_inline_subjects_are_readable() -> None:
    assert backlog_text.lead_actor_label(["Restaurant Manager: completes the first audit path"]) == "Restaurant Manager"
    assert backlog_text.supporting_actor_label(["Restaurant Manager", "Station Lead: marks fixes complete"]) == "Station Lead"
    assert (
        backlog_text.supporting_actor_label(
            [
                "Football Fan: checking one match",
                "Match Editor or Trusted Feed Operator Confirming Events: confirms event updates",
            ]
        )
        == "Match Editor or Trusted Feed Operator"
    )
    assert (
        backlog_text.inline_actor_subject("Match Editor or Trusted Feed Operator")
        == "the match editor or trusted feed operator"
    )
    assert backlog_text.problem_actor_subject("Station Lead", fallback="user") == "The station lead"
    assert backlog_text.inline_actor_subject("The Restaurant Manager") == "the restaurant manager"
    assert backlog_text.inline_actor_subject("GLP-1 Companion risk reviewer") == "the GLP-1 Companion risk reviewer"

    assert generated_semantic_slop_issues({"bad": "the station Lead cannot act on the result"}) == [
        "inline actor casing drift leaked at artifact.bad"
    ]
    assert generated_semantic_slop_issues({"bad": "home Cook picks a recipe and sees the result"}) == [
        "artifact.bad leaked mixed actor-role casing"
    ]
    assert generated_semantic_slop_issues({"ok": "the GLP-1 Companion risk reviewer can inspect evidence"}) == []
    assert not has_inline_role_casing_drift(
        "The product failure to guard against: Customer and Contact Directory Service can mislead users."
    )
    assert not has_inline_role_casing_drift(
        "Do this before implementation expands so Customer and Contact Directory Service has a tested first slice."
    )
    assert not has_inline_role_casing_drift("Let Shop Owner / Manager Check in a Customer's Firearm")
    assert not has_inline_role_casing_drift(
        "Release scope connects Customer and Firearm Record, Service Ticket Workflow and Status Tracking, and Shop Dashboard and Reporting without absorbing deferred scope."
    )


def test_package_quality_rejects_prepositional_visible_result_splices() -> None:
    assert generated_public_copy_issues(
        "artifact.bad",
        "Prove the first path: home Cook picks a recipe and see With an emergency stop available throughout.",
    ) == (
        "artifact.bad leaked mixed actor-role casing",
        "artifact.bad leaked prepositional visible-result splice",
    )
    assert generated_public_copy_issues(
        "artifact.bad",
        "The product lets the user reach with an emergency stop available throughout.",
    ) == ("artifact.bad leaked prepositional visible-result splice",)


def test_confirmed_intent_completion_expands_thin_actor_rows_before_validation() -> None:
    intent = parse_confirmed_intent_text(
        """
# Public Question Response Tracker

## Product story
A resident needs a clear way to submit one public question, see who owns the response, track status, and receive an answer with reason notes and source references.

## State object
The response record tracks question identity, submitter contact, category, assigned owner, status, source references, draft answer, review notes, published response, and follow-up state.

## First complete path
A resident submits one question, the coordinator assigns an owner, the owner drafts an answer with references, a reviewer approves it, and the resident sees the published response and status history.

## Human actors
- Resident submitting one public question.
- Response coordinator assigning ownership.
- Reviewer approving the answer.

## External systems
- Public web form for submitted questions.
- Reference source for policy or service information.

## Internal product systems
- Question intake and triage.
- Ownership and status tracking.
- Response drafting and review.
- Published response history.

## Critical assumptions
- Release 0.0.1 follows one question at a time.
- The answer must include reason notes or source references before publication.

## Ambiguities
- Which categories require legal or policy review.

## Proof boundary
Release 0.0.1 succeeds when one question moves from submitted to assigned to reviewed to published, with owner, status, reason notes, references, privacy handling, and response history visible.
"""
    )

    assert all(len(row.split()) >= 5 for row in intent["human_actors"])
    assert any(row.startswith("Response Coordinator:") for row in intent["human_actors"])


def test_confirmed_actor_completion_does_not_turn_state_definition_into_action() -> None:
    intent = complete_confirmed_intent(
        parse_confirmed_intent_text(
            """
# Municipal Permit Review Portal

## Product story
A resident submits a building permit application online so the city can check completeness and return an approval or correction request.

## State object
Permit application records the current status, actor, source input, decision, blocked reason, evidence links, timestamp, and version history for the accepted first path.

## First complete path
The resident starts an application, enters project and property details, uploads required documents, pays the fee, and submits the package.

## Human actors
- Resident or contractor applicant
- Permit intake clerk
- Department reviewer

## External systems
- Payment processor

## Internal product systems
- Application intake workflow
- Completeness validation
- Decision response publishing

## Proof boundary
Release 0.0.1 is complete when one resident can submit one application, receive validation feedback, and see a decision or correction request.
"""
        )
    )
    rendered = " ".join(intent["human_actors"])

    assert "uses the product to record the current status" not in rendered
    assert "Permit Intake Clerk: supplies context" in rendered


def test_visible_result_language_normalization_stays_in_text_owner() -> None:
    text_source = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    callers = [
        FIRST_PATH_FRAGMENTS_PATH,
        SEQUENCE_STEPS_PATH,
        COMPONENT_TERMS_PATH,
        CONFIRMED_SYSTEM_ROWS_PATH,
        CONFIRMED_INTENT_COMPLETION_PATH,
        PRODUCT_RISKS_PATH,
        CONFIRMED_DIAGRAM_TEXT_PATH,
    ]

    assert "def normalize_visible_result_language" in text_source
    assert normalize_visible_result_language(
        "Visible-result event readout plus note on screen, alongside source evidence."
    ) == "visible result readout and note on screen with source evidence."
    assert normalize_visible_result_language(
        "estimated total burn against target plus one concrete recommendation"
    ) == "estimated total burn compared with the target and one concrete recommendation"
    assert normalize_visible_result_language("estimated total burn against target") == (
        "estimated total burn against the target"
    )
    assert normalize_visible_result_language("tracked metrics trended with usage") == "tracked metrics changed with usage"
    assert (
        normalize_visible_result_language("a trend the optimizer reasons against")
        == "a trend the optimizer uses for comparison"
    )
    assert (
        normalize_visible_result_language("issues control actions to downstream systems")
        == "issues control actions for downstream systems"
    )
    assert normalize_visible_result_language(
        "shows progress, and reaches a finished safe-to-serve state with emergency stop available throughout"
    ) == "a finished safe-to-serve state with emergency stop available throughout"

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "normalize_visible_result_language" in source
        assert r"\breadout\s+plus\b" not in source
        assert r"\bon\s+screen,\s+alongside\b" not in source
        assert 'r"\\balongside\\b", "with"' not in source


def test_outcome_action_phrase_does_not_wrap_action_outcomes_as_visible_objects() -> None:
    assert (
        outcome_action_phrase("open a simple recap showing what the child explored and what it was teaching")
        == "open a simple recap showing what the child explored and what it was teaching"
    )
    assert outcome_action_phrase("a simple recap showing what the child explored") == (
        "see a simple recap showing what the child explored"
    )
    assert outcome_action_phrase("a lead creates a readiness review") == "create a readiness review"
    assert (
        outcome_action_phrase("a lead records the launch decision with proof of what was reviewed")
        == "record the launch decision with proof of what was reviewed"
    )
    assert outcome_action_phrase("the publication status") == "see the publication status"


def test_outcome_action_phrase_preserves_leading_acronym_result_objects() -> None:
    assert outcome_action_phrase("NICU acceptance and handoff proof") == "review the NICU acceptance and handoff proof"
    assert outcome_action_phrase("AI/ML review status") == "see the AI/ML review status"


def test_component_focus_phrase_drops_terminal_preposition_from_label_focus() -> None:
    assert (
        component_focus_phrase(
            label="Account and Child Profile Management with Age Bands Service",
            contract={"owned_state": ["Account and child profile management with age bands"]},
            fallback="child profile state",
        )
        == "account and child profile management"
    )


def test_user_can_gate_allows_base_action_with_action_shaped_object() -> None:
    assert generated_semantic_slop_issues(
        "Result proof confirms the user can use Record with a clear explanation."
    ) == []
    assert generated_semantic_slop_issues("The user can coordinator creates packet state.")


def test_project_brief_component_summary_uses_final_component_labels() -> None:
    brief = confirmed_project_brief(
        label="Review Packet Builder",
        prompt="review packet builder",
        release="0.0.1",
        state_object="A Review Packet tracks source items and packet status.",
        evidence_record="Publication Record",
        product_story="A review coordinator assembles a reviewer packet with missing evidence visibility.",
        first_path=(
            "A coordinator creates a review packet, adds source items, assigns a reviewer, "
            "and publishes the packet."
        ),
        proof_boundary="The release is proven when the packet can be reviewed with publication evidence.",
        human_actors=["Review coordinator", "Reviewer"],
        internal_systems=[
            "Packet workspace",
            "Eligibility checklist",
            "Reviewer assignment board",
            "Publication record",
        ],
        component_labels=[
            "Packet Workspace",
            "Eligibility Checklist",
            "Review Assignment Board",
            "Publication Record",
        ],
    )

    component_gate = next(
        gate for gate in brief["coding_readiness_gates"] if "components come from product systems" in gate
    )

    assert "Review Assignment Board" in component_gate
    assert "Reviewer Assignment Board" not in component_gate


def test_confirmed_completion_repairs_actor_led_outcome_after_modal_wrappers(tmp_path: Path) -> None:
    markdown = """
# Operations Readiness Board

## Product story
An operations lead uses the Operations Readiness Board to collect launch tasks, verify required evidence, identify blockers, assign owners, and approve a launch decision with an audit trail. Without it, teams cannot tell whether readiness is complete, blocked, or waiting on a specific owner.

## State object
A Readiness Review tracks launch scope, required checks, evidence attachments, blocker state, owner assignment, approval status, and decision history.

## First complete path
A lead creates a readiness review, adds required checks, marks one check blocked with a clear reason, assigns owners for open checks, accepts evidence for a ready check, and records the launch decision with proof of what was reviewed.

## Human actors
- Operations lead
- Evidence owner
- Approver

## Internal product systems
- Readiness board
- Evidence checklist
- Blocker register
- Decision log

## Assumptions
- The first release supports manual evidence upload.
- Approval can be represented as an internal decision record.

## Ambiguities
- Which external system owns final launch notification?

## Proof boundary
Odylith should prove review creation, evidence tracking, blocked-check handling, owner assignment, decision capture, and audit traceability for one launch readiness journey.
"""
    intent = parse_confirmed_intent_text(markdown, prompt="operations readiness board")
    (tmp_path / "AGENTS.md").write_text("# Repo Root\n\nRegression repo.\n", encoding="utf-8")
    completed = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="operations readiness board",
        confirmed_intent=intent,
        release_selector="0.0.1",
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert "can reach a lead creates" not in rendered
    assert "can create a readiness review" in rendered
    assert generated_semantic_slop_issues(completed, root="proposal") == []


def test_signal_pipeline_first_path_phrases_do_not_leak_modal_or_understand_fragments() -> None:
    proposal = {
        "intent": {
            "first_path": (
                "A signal source connects and pushes a stream of samples; the pipeline ingests them, "
                "applies a configured transform, evaluates a detection rule, and emits a result event "
                "to a sink - all within a bounded latency target."
            ),
            "proof_boundary": (
                "The first path is proven when a sample stream flows end to end - ingest, transform, "
                "detect, emit - under a stated latency target with a resumable offset."
            ),
        }
    }

    action = action_phrase(proposal)
    outcome = outcome_phrase(proposal)
    product_view = workstream_product_view(
        label="Realtime Signal Processing Pipeline",
        action=action,
        outcome=outcome,
    )

    assert action == "connect and push a stream of samples"
    assert outcome == "a result event to a sink"
    assert "understand Pipeline" not in product_view
    assert "connect and pushes" not in product_view
    assert "see a result event to a sink" in product_view
    assert generated_semantic_slop_issues({"product_view": product_view}) == []


def test_workstream_product_view_modalizes_actor_led_actions_without_user_can_splice() -> None:
    product_view = workstream_product_view(
        label="Batch Evidence Console Service",
        action="intake coordinator records one lab batch and precursor lot",
        outcome="approved or rejected manufacturing readiness",
    )

    assert "the intake coordinator can record one lab batch and precursor lot" in product_view
    assert "the user can intake coordinator records" not in product_view
    assert "can records" not in product_view
    assert generated_semantic_slop_issues({"product_view": product_view}) == []


def test_semantic_slop_gate_rejects_multi_word_actor_inside_user_can_clause() -> None:
    public_issues = generated_public_copy_issues(
        "proposal.product_view",
        "Batch Evidence Console Service is complete when the user can intake coordinator records one lab batch.",
    )
    issues = generated_semantic_slop_issues(
        {
            "product_view": (
                "Batch Evidence Console Service is complete when the user can intake coordinator records "
                "one lab batch and precursor lot, see the approved or rejected manufacturing readiness, "
                "and recover cleanly from a bad or incomplete attempt."
            )
        },
        root="proposal",
    )

    assert any("actor-led finite action inside user-can prose" in issue for issue in public_issues)
    assert any("actor-led finite action leaked inside user-can clause" in issue for issue in issues)


def test_copy_and_semantic_gates_reject_gerundized_actor_role_action_splice() -> None:
    bad_capability = (
        "intaking coordinator records one lab batch and precursor lot, checking blocking observations, "
        "and approving or rejecting manufacturing readiness"
    )

    public_issues = generated_public_copy_issues("proposal.semantic_model.first_path_contract.capability", bad_capability)
    semantic_issues = generated_semantic_slop_issues(
        {"semantic_model": {"first_path_contract": {"capability": bad_capability}}},
        root="proposal",
    )

    assert any("gerundized actor-role action prose" in issue for issue in public_issues)
    assert any("gerundized actor-role action leaked" in issue for issue in semantic_issues)


def test_predicate_visible_outcome_does_not_become_user_import_action() -> None:
    first_path = (
        "A homeowner connects inverter, meter, battery, and weather sources. "
        "SunLedger pulls readings and weather, forecasts today's production and demand, "
        "builds a battery and load control plan, shows the homeowner why it should reduce grid draw, "
        "lets them approve it, issues the approved control actions, monitors the result, "
        "and reports whether the plan reduced grid imports without violating reserve or comfort limits."
    )
    proposal = {
        "intent": {
            "first_path": first_path,
            "proof_boundary": (
                "The first proof is one home completing one daily loop: ingest telemetry and weather, "
                "forecast production and demand, create a defensible plan, receive homeowner approval, "
                "dispatch approved battery and load control actions, and report grid-import reduction "
                "against reserve and comfort constraints."
            ),
        }
    }

    clauses = first_path_clauses(first_path)
    outcome = outcome_phrase(proposal)
    product_view = workstream_product_view(
        label="Energy Telemetry Ingestion Service",
        action=action_phrase(proposal),
        outcome=outcome,
    )

    assert clauses.visible_result == "the plan reduced grid imports without violating reserve or comfort limits"
    assert outcome == "the plan reduced grid imports without violating reserve or comfort limits"
    assert outcome_action_phrase(outcome) == "see that the plan reduced grid imports without violating reserve or comfort limits"
    assert "import without violating" not in product_view
    assert "see that the plan reduced grid imports" in product_view
    assert generated_semantic_slop_issues({"product_view": product_view}) == []


def test_actor_owned_workstream_title_base_forms_all_action_verbs() -> None:
    workflow_title, _boundary_title, _proof_title = confirmed_workstream_titles(
        label="Quantum Link Lab",
        components=[
            {"label": "Run Configuration and Validation Service"},
            {"label": "Hardware Control and Run Execution Service"},
            {"label": "Security and Verification Logic Service"},
            {"label": "Results Store and Run History"},
        ],
        internal_systems=[
            "Run configuration and validation",
            "Hardware control and run execution",
            "Security and verification logic",
            "Results store and run history",
        ],
        first_path=(
            "A researcher defines a new E91 run (source, two stations, bases, channel/integration settings), "
            "launches it against the hardware, then sees the Bell inequality was violated and the key established."
        ),
        state_object="A communication run with run configuration, station events, QBER, verification status, and key material.",
        proof_boundary="The proof is one run showing verification status and key establishment.",
        human_actors=["Researcher"],
    )

    assert "Launches" not in workflow_title
    assert workflow_title == "Let Researcher Define a New E91 Run (Source, Two Stations, Bases, Channel and Integration Settings), Launch It Against the Hardware"


def test_actor_owned_workstream_title_uses_first_path_action_when_actor_alias_misses() -> None:
    workflow_title, _boundary_title, _proof_title = confirmed_workstream_titles(
        label="Pattern Relief Notebook",
        components=[
            {"label": "Entry Logging Service"},
            {"label": "Routine Library Service"},
            {"label": "Trend and Correlation View Service"},
            {"label": "Reminder and Streak Nudge Service"},
        ],
        internal_systems=[
            "Entry Logging — daily check-in",
            "Routine Library — saved activities",
            "Trend and Correlation View — trend readout",
            "Reminder and Streak Nudge — reminder controls",
        ],
        first_path=(
            "A new user records their first entry — rates today's status, taps the factors that applied, "
            "and logs one action they tried. The next day they log again. After a handful of entries, "
            "the app shows a simple trend: status over time, and which logged actions line up with better days."
        ),
        state_object=(
            "A person's comfort timeline: dated entries, ratings, contributing factors, actions tried, "
            "saved routines, and derived trends."
        ),
        proof_boundary="The proof is one user logging entries and seeing an honest trend.",
        human_actors=[
            "Person Managing Discomfort: uses Pattern Relief Notebook to complete the first product path."
        ],
    )

    assert workflow_title == "Let Person Managing Discomfort Record First Entry"
    assert "Complete the Accepted Path" not in workflow_title


def test_title_labels_render_and_slash_compounds_as_comma_lists() -> None:
    value = "Scenario library and authoring/curation"

    assert title_label(value) == "Scenario Library, Authoring, and Curation"
    assert title_case_text(value) == "Scenario Library, Authoring, and Curation"


def test_component_responsibility_does_not_prefix_action_clause_with_owns() -> None:
    components = confirmed_components(
        label="Realtime Signal Processing Pipeline",
        label_slug="realtime-signal-processing-pipeline",
        internal_systems=[
            "Ingest layer - accepts streams, normalizes samples, tracks per-stream offsets.",
            "Emit layer - delivers results to configured sinks with delivery guarantees.",
        ],
        first_path=(
            "A signal source connects and pushes a stream of samples. The pipeline emits a result event to a sink."
        ),
        state_object="A live processing pipeline with streams, stage configuration, offsets, and emitted results.",
        proof_boundary="The first path is proven when one stream emits one result event to a sink.",
    )
    rendered = json.dumps(components, sort_keys=True)
    emit = next(row for row in components if row["label"] == "Emit Layer Service")

    assert "Owns delivers" not in rendered
    assert emit["responsibility"].startswith("Delivers results to configured sinks")
    assert generated_semantic_slop_issues(components) == []


def test_completed_internal_system_rows_strip_relative_action_clause_from_label() -> None:
    completed = complete_confirmed_intent(
        {
            "title": "Choice Practice",
            "product_story": "A learner practices choices and a trusted adult reviews a simple recap.",
            "state_object": "A learner practice record with selected choice, consequence note, recap status, and privacy boundary.",
            "first_path": (
                "A parent creates an account and adds a learner. The learner opens a scenario and makes a choice. "
                "The parent opens a recap."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when the parent can create the learner record, the learner can complete "
                "one scenario, and the parent can open the recap."
            ),
            "human_actors": ["Learner", "Parent"],
            "internal_systems": ["Choice-and-consequence engine that records each decision"],
        }
    )

    rendered = json.dumps(completed, ensure_ascii=False, sort_keys=True)

    assert "Choice-and-consequence Engine — records each decision" in rendered
    assert "Engine That" not in rendered


def test_proof_boundary_language_normalization_stays_in_text_owner() -> None:
    text_source = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    diagram_source = CONFIRMED_DIAGRAM_TEXT_PATH.read_text(encoding="utf-8")

    assert "def normalize_proof_boundary_language" in text_source
    assert (
        normalize_proof_boundary_language(
            "Release 0.0.1 is trusted only when the accepted path can be replayed from input through state change."
        )
        == "replay input through state change"
    )
    assert (
        normalize_proof_boundary_language(
            "What would count as evidence the wedge works: a recorded take. "
            "What must not be claimed yet: polyphony."
        )
        == "a recorded take"
    )
    assert normalize_proof_boundary_language("Done means: reviewer sees the blocked reason.") == (
        "reviewer sees the blocked reason"
    )

    assert "normalize_proof_boundary_language" in diagram_source
    assert r"what\s+would\s+count\s+as\s+evidence" not in diagram_source
    assert r"accepted\s+path\s+can\s+be\s+replayed" not in diagram_source
    assert r"first\s+version\s+is\s+proven" not in diagram_source
    assert r"trusted\s+only\s+when" not in diagram_source
    assert r"done\s+means" not in diagram_source


def test_confirmed_completion_repairs_actor_and_visible_result_splices() -> None:
    completed = complete_confirmed_intent(
        {
            "title": "Activity Progress Notebook",
            "product_story": (
                "A person needs a private place to record recurring care activity, compare it with a plan, "
                "and decide what needs attention before the next check-in."
            ),
            "state_object": (
                "The core state is a care progress record with active entries, notes, visible prompts, "
                "current status, and a history of changes."
            ),
            "first_path": (
                "A patient signs in. The patient logs a new activity with timing, note, and status. "
                "The product saves the entry, updates the progress view, and renders the visible result: "
                "the patient sees a clear prompt, updated status, and next action."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when one person can save an entry, see the updated progress view, "
                "and correct the entry while the previous state remains reviewable."
            ),
            "problem": (
                "Activity Progress Notebook is not trustworthy when users need an active and decide what to do "
                "from The patient sees a clear prompt."
            ),
            "human_actors": ["Patient", "Reviewer"],
            "internal_systems": ["Activity Capture", "Progress View"],
        }
    )

    encoded = json.dumps(completed, sort_keys=True)

    assert "can own a named responsibility" not in encoded
    assert "cares about" not in encoded
    assert "active and decide" not in encoded
    assert "from the patient sees" not in encoded.casefold()
    assert "reach the patient sees" not in encoded.casefold()
    assert "Patient needs a dependable way" in completed["problem"]
    assert generated_semantic_slop_issues(completed) == []
    assert public_prose_quality_issues(completed) == []


def test_first_path_clauses_compile_actions_outcomes_and_noun_lists() -> None:
    request_path = (
        "A requester opens the product, selects a request type, enters amount, constraints, "
        "and contact details. The product calculates eligibility and displays a decision "
        "with reason notes."
    )
    care_path = (
        "A patient signs in. The patient logs a new activity with timing, note, and status. "
        "The product saves the entry, updates the progress view, and renders the visible result: "
        "the patient sees a clear prompt, updated status, and next action."
    )
    review_path = (
        "A permit coordinator imports one permit application, a zoning reviewer records a zoning check, "
        "the applicant submits one revision, and a supervisor reviews the decision package with traceable "
        "documents, comments, checks, and final status."
    )

    request = first_path_clauses(request_path)
    care = first_path_clauses(care_path)
    review = first_path_clauses(review_path)
    short_actor_path = (
        "The AI reviewer records a decision. The product displays the decision queue. "
        "A reviewer approves final status."
    )
    dash_explainer_path = (
        "A new user records their first entry — rates today's status, taps the factors that applied, "
        "and logs one action they tried. The product shows a trend with the first useful signal."
    )
    short_actor = first_path_clauses(short_actor_path)
    dash_explainer = first_path_clauses(dash_explainer_path)

    assert request.action_chain == "select a request type and enter amount, constraints and contact details"
    assert request.visible_result == "a decision with reason notes"
    assert request.capability_chain == "select a request type, enter amount, constraints and contact details, and see a decision with reason notes"
    assert "review A decision" not in request.capability_chain
    assert "calculates eligibility" not in request.visible_result
    assert care.action_chain == "log a new activity with timing, note and status"
    assert "signs in" not in care.action_chain
    assert care.visible_result == "a clear prompt, updated status, and next action"
    assert review.action_chain == "import one permit application, record a zoning check, and submit one revision"
    assert review.visible_result == "the decision package with traceable documents, comments, checks, and final status"
    assert short_actor.action_chain == "record a decision"
    assert short_actor.capability_chain == "record a decision and see the decision queue"
    assert "approve final status" not in short_actor.capability_chain
    assert action_chain_fragment("A new user records their first entry — rates today's status") == "record first entry"
    assert dash_explainer.action_chain == "record first entry"
    assert "rates today's status" not in dash_explainer.action_chain
    assert "their first" not in dash_explainer.capability_chain
    assert "rates today's status" not in dash_explainer.capability_chain
    assert base_action_clause("logs progress and reviews weekly status") == "log progress and review weekly status"
    assert base_action_clause("enters a form and submits") == "enter a form and submit"
    assert base_action_clause("checks and controls for drift") == "check and control for drift"
    assert base_action_clause("reviews orders and offers") == "review orders and offers"
    assert base_action_clause("chooses methods and controls for comparison") == "choose methods and controls for comparison"
    assert (
        base_action_clause("uploads controls and records for later review")
        == "upload controls and records for later review"
    )
    assert (
        base_action_clause("requests a slot, receives confirmation, and records next steps")
        == "request a slot, receive confirmation, and record next steps"
    )
    assert (
        base_action_clause("enters project details, uploads required documents, pays the fee")
        == "enter project details, upload required documents, pay the fee"
    )
    assert (
        base_action_clause("selects the permit type, attaches required documents")
        == "select the permit type, attach required documents"
    )
    assert (
        action_chain_fragment("The resident enters project details, uploads required documents, pays the fee")
        == "enter project details, upload required documents, pay the fee"
    )
    assert base_action_clause("comments, checks, and final status") == "comments, checks, and final status"


def test_first_path_gerund_chain_handles_set_draft_and_send_actions() -> None:
    first_path = (
        "The coordinator imports one feedback item, classifies the topic, sets response priority, "
        "drafts a response, sends it for review, receives one requested change, updates the draft, "
        "and the approver sees a publication-ready package with rationale, change history, and blocked-state explanation."
    )
    capability = first_path_capability_phrase(first_path, fallback="review response", gerund=True, max_fragments=8, limit=340)

    assert gerund_action_fragment("sets response priority") == "setting response priority"
    assert "setting response priority" in capability
    assert "drafting a response" in capability
    assert "sending it for review" in capability
    assert gerund_action_fragment("enters details, uploads documents, pays the fee") == (
        "entering details, uploading documents, paying the fee"
    )
    assert "seting" not in capability
    assert "drafts a response" not in capability


def test_actor_role_modifiers_do_not_become_gerund_actions_or_modal_splices() -> None:
    first_path = (
        "Intake coordinator records one lab batch and precursor lot; "
        "checks blocking observations; "
        "process engineer records exception rationale; "
        "approval reviewer approves or rejects manufacturing readiness."
    )

    assert actor_signature("Intake coordinator records one lab batch and precursor lot") == "intake coordinator"
    assert action_chain_fragment("Intake coordinator records one lab batch and precursor lot") == (
        "record one lab batch and precursor lot"
    )
    assert gerund_action_fragment("Intake coordinator records one lab batch and precursor lot") == (
        "recording one lab batch and precursor lot"
    )
    capability = first_path_capability_phrase(first_path, fallback="review readiness", gerund=True, max_fragments=8, limit=360)

    assert "recording one lab batch and precursor lot" in capability
    assert "checking blocking observations" in capability
    assert "approving or rejecting manufacturing readiness" in capability
    assert "intaking coordinator" not in capability
    assert generated_semantic_slop_issues({"capability": capability}) == []


def test_first_path_capability_preserves_routed_review_actions_without_duplicate_outcome() -> None:
    first_path = (
        "A case worker creates an appeal case from a denied grant decision, records evidence, schedules a hearing, "
        "prepares the decision packet, sends the packet for review, and marks the appeal final when the decision is recorded."
    )
    capability = first_path_capability_phrase(first_path, fallback="prepare appeal review", max_fragments=8, limit=400)

    assert action_chain_fragment("A case worker sends the packet for review") == "send the packet for review"
    assert visible_result_object("A case worker sends the packet for review") == ""
    assert "send the packet for review" in capability
    assert "review the packet for review" not in capability
    assert "see a case worker marks" not in capability
    assert capability.count("mark the appeal final") == 1


def test_workstream_risk_uses_compact_state_label_instead_of_field_list() -> None:
    risk = workstream_risk(
        label="Decision and Reason Publisher Service",
        outcome="the decision with reasons",
        state=(
            "a permit application record with applicant identity, parcel address, permit type, required documents, "
            "zoning checks, correction requests, review status, inspection readiness, staff notes, and final decision"
        ),
    )

    assert "permit application record is incomplete" in risk
    assert "applicant identity, parcel address" not in risk
    assert risk.count(",") <= 2


def test_workstream_risk_projects_semantic_result_instead_of_raw_first_path_chain() -> None:
    proposal = {
        "semantic_model": {"first_path_contract": {"visible_result": "a finished safe state"}},
        "backlog": [],
    }
    row = {
        "title": "Coordinate first path",
        "domain_risk": (
            "Operational risk needs review. First path: The operator selects an input, the controller validates "
            "the setup, shows progress, and reaches a finished safe state. Safety posture stays bounded."
        ),
    }
    proposal["backlog"] = [row]

    risk = domain_risk_for_row(row, proposal)

    assert "First path: a finished safe state." in risk
    assert "shows progress, and reaches" not in risk
    assert "Safety posture stays bounded." in risk


def test_actor_verb_treats_singular_actor_with_modifier_nouns_as_singular() -> None:
    assert backlog_actions.actor_verb("the homeowner comparing solar options", singular="provides", plural="provide") == "provides"
    assert backlog_actions.actor_verb("the student choosing recommended books", singular="needs", plural="need") == "needs"
    assert backlog_actions.actor_verb("reviewers checking requests", singular="receives", plural="receive") == "receive"


def test_first_path_model_drops_meta_loop_summary_from_visible_outcome() -> None:
    model = first_path_model(
        "A new user records their first entry — rates today's status, taps the factors that applied, "
        "and logs one action they tried. The next day they log again. After a handful of entries, "
        "the app shows a simple trend: status over time, and which logged actions line up with better days. "
        "That loop — log, repeat, see the pattern — is the smallest version of the whole product working end to end."
    )

    rendered = " ".join([*model.steps, model.visible_outcome, model.material_action])

    assert model.visible_outcome == "A simple trend: status over time, and which logged actions line up with better days"
    assert "That loop" not in rendered
    assert "smallest version of the whole product" not in rendered
    assert generated_semantic_slop_issues({"first_path": model.visible_outcome}) == []


def test_first_path_model_keeps_carried_plural_subject_grammar() -> None:
    model = first_path_model(
        "A user sets up their medication, current dose, and weekly injection day. When a dose is due, "
        "the app reminds them; they confirm the injection, optionally log their weight and any side effects, "
        "and the app records it, advances them along their titration schedule, and shows the next due date."
    )

    rendered = " ".join(model.steps)

    assert "They optionally log their weight and any side effects" in model.steps
    assert "The app advances them along their titration schedule" in model.steps
    assert "They optionally logs" not in rendered
    assert "Optionally log their weight" not in rendered
    assert "Advances them along" not in rendered


def test_multi_actor_first_path_assigns_event_actors_and_cleans_result_copy() -> None:
    markdown = """
# Choice Practice Journal

## Product story
Choice Practice Journal gives a learner short practice scenarios and gives a trusted adult a simple recap. The product helps the learner make one choice, understand the immediate consequence, and leave a short reflection without turning the experience into a score, ranking, or behavior label. The adult owns setup and privacy, while the learner remains the person completing the practice moment.

## State object
The product keeps a learner practice record with account owner, learner profile, scenario id, selected choice, consequence note, reflection, recap status, and privacy boundary.

## First complete path
A parent creates an account, adds a learner profile, and picks the age band of eight to ten for the first release. The learner opens an illustrated scenario, makes a choice at the decision point, sees a consequence and a short reflection, and finishes the session. The parent later opens a simple recap of what the learner explored.

## Human actors
- Learner, a child aged eight to ten
- Parent, the account owner at home
- Facilitator, a small-group reviewer
- Scenario author, a content writer

## Internal product systems
- Account and learner profile service
- Scenario library service
- Choice consequence engine
- Reflection capture service
- Adult recap service
- Learner privacy service

## Proof boundary
The first release succeeds when a parent can create an account and learner profile, the learner can complete one scenario with a selected choice and reflection, and the parent can open a recap. Multiple age bands, authoring workflows, reminders, and live classroom management are outside the first proof.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft a greenfield proposal for a learner choice practice journal.",
        title="Choice Practice Journal",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    first_path = proposal["semantic_model"]["first_path_contract"]
    rendered = json.dumps(proposal, sort_keys=True)

    assert first_path["actor"] == "Parent"
    assert first_path["visible_result"] == "a short reflection"
    assert [(event["actor"], event["action"]) for event in first_path["events"]] == [
        ("Parent", "creates"),
        ("Parent", "adds"),
        ("Parent", "picks"),
        ("Learner", "opens"),
        ("Learner", "makes"),
        ("Learner", "sees"),
        ("Parent", "opens"),
    ]
    for banned in (
        "Learner, A Child",
        "uses the product to parent creates",
        "add a learner profile and picks",
        "reflection and finishes",
        "understand The",
        "reach a short reflection",
        "use a short reflection",
        "visible outcome from a short reflection",
        "see a consequence and a short reflection, and see",
        "learner can create an account",
        "where learner can create",
        "Start with this implementation slice",
        "representative user can",
        "shows open",
        "should support the user action: create an account",
        "Build the smallest behavior in Account",
        "The product checks the details, explains missing information before it produces a result, and shows a short reflection",
    ):
        assert banned not in rendered
    assert generated_semantic_slop_issues(proposal) == []


def test_confirmed_jet_engine_external_system_preposition_does_not_stop_post_confirm() -> None:
    markdown = """
# Jet Engine Servicing Tracker

## Product story
A maintenance organization servicing jet engines needs to know, at any moment, where every engine is in its service lifecycle, which engine is on which workstand, what work orders are open against it, which tasks are signed off, and whether it is cleared to return to the aircraft.

## State object
The central object is a servicing record for one engine: its identity, current servicing stage, open work orders, assigned tasks, parts consumed, sign-offs collected, and airworthiness disposition.

## First complete path
A service planner intakes an engine, opens a work order with its required tasks, a technician picks up a task and records the work and parts used, an inspector signs it off, and the supervisor reviews all closed tasks and releases the engine as serviceable.

## Human actors
- Service planner who intakes engines and opens work orders
- Maintenance technician who performs and records tasks
- Quality inspector who signs off completed work
- Maintenance supervisor who reviews and releases the engine

## External systems
- Parts and inventory system for consumed components and stock levels
- OEM or regulatory task-card and service-bulletin source for required work scope
- Aircraft or fleet records system the engine returns to

## Internal product systems
- Engine and servicing-record store that owns the servicing record source of truth
- Work-order and task workflow engine that manages task states and handoff evidence
- Sign-off and airworthiness-disposition tracking that controls inspection and release state
- Status and turnaround reporting views that expose current state and review outcomes

## Proof boundary
Done means the first complete path works end to end on real records: an engine can be intaked, taken through open task, recorded work, inspector sign-off, and supervisor release, with role-gating enforced and a complete queryable history surviving on the engine record.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Draft a greenfield proposal for a jet engine servicing tracker.",
        title="Jet Engine Servicing Tracker",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    proposal = normalize_host_reasoned_proposal(proposal)
    completed = complete_confirmed_proposal(proposal, release_selector="0.0.1")
    rendered = json.dumps(completed, sort_keys=True)

    assert "Aircraft or fleet records system the engine returns to." not in rendered
    assert "Aircraft or fleet records system the engine returns to," not in rendered
    assert "Aircraft or fleet records system the engine returns to;" not in rendered
    assert "uses the product to planner intakes" not in rendered
    assert "intaked" not in rendered
    assert "Aircraft or fleet records system" in rendered
    assert public_prose_quality_issues(completed) == []


def test_confirmed_state_object_normalizes_terminal_hang_off_phrase() -> None:
    intent = parse_confirmed_intent_text(
        """
# Service Job Workspace

## Product story
A team coordinates one service request from intake through completion so every handoff has a clear owner and reviewable result.

## State object
The center of gravity is the service job: a unit of work against one asset, moving through requested, approved, scheduled, in-progress, and completed. Assets and customers are long-lived records the jobs hang off of.

## First complete path
A coordinator opens a service job, assigns a technician, the technician records work, and the customer receives the completed service record.

## Human actors
- Coordinator who schedules and tracks service work.
- Technician who records completed work.
- Customer who receives the completed service record.

## Internal product systems
- Service job lifecycle.
- Customer and asset records.
- Completion record view.

## Proof boundary
The first release succeeds when one service job reaches a completed record with actor, status, assignment, completion evidence, and a customer-visible result.
""",
        prompt="Draft a greenfield proposal for a service job workspace.",
    )

    assert "hang off of" not in intent["state_object"]
    assert intent["state_object"].startswith("the service job:")
    assert intent["state_object"].endswith("linked to the jobs.")
    assert public_prose_quality_issues(intent) == []


def test_atlas_tail_checker_ignores_terminal_first_path_meta_summary() -> None:
    first_path = (
        "A captain submits a service request for a known yacht; a service coordinator reviews it; "
        "the customer receives the finished service record. That single request-to-completed-record path is the proof the product works."
    )
    proposal = {"intent": {"first_path": first_path}}
    source = """
flowchart LR
  actor["User action"]
  S1["Submit a service request"]
  S2["Receive the finished service record"]
  proof["Outcome<br/>the finished service record"]
  actor --> S1
  S1 --> S2
  S2 --> proof
"""
    issues: list[str] = []

    _check_atlas_source_preserves_first_path_tail(
        proposal=proposal,
        title="First Path Sequence",
        source=source,
        kind="flowchart",
        issues=issues,
    )

    assert issues == []


def test_generated_public_copy_rejects_action_shaped_result_and_template_prefix() -> None:
    assert generated_public_copy_issues(
        "Radar workstream",
        "The product checks the details and shows open a simple recap.",
    ) == ("Radar workstream leaked presentational verb/action splice prose",)
    assert generated_public_copy_issues(
        "Radar workstream",
        "Start with this implementation slice: prove the first path.",
    ) == ("Radar workstream leaked repetitive implementation-slice template prose",)
    assert generated_public_copy_issues(
        "Radar workstream",
        "The product shows a short reflection with a clear explanation.",
    ) == ()
    assert generated_public_copy_issues(
        "Project brief",
        "The product turns scattered daily notes into a small feedback loop: record how the day felt, record what action was tried, and review the pattern.",
    ) == ()
    assert generated_public_copy_issues(
        "Registry component spec",
        "Review Packet Builder shows review packet state, review evidence, and packet status.",
    ) == ()
    assert generated_public_copy_issues(
        "Registry component spec",
        "Triage Board shows open questions, selected route evidence, and review status.",
    ) == ()
    assert generated_public_copy_issues(
        "Radar workstream",
        (
            "The case coordinator can accept a water-use claim. "
            "The product checks the details before it produces a result."
        ),
    ) == ()
    assert generated_public_copy_issues(
        "Radar workstream",
        "Let Case Coordinator Accept a Water Use Claim: `docket-readiness-view` (Docket Readiness View Service).",
    ) == ()
    assert generated_public_copy_issues(
        "Radar workstream",
        "The product lets the evidence clerk reach the hearing readiness.",
    ) == ("Radar workstream leaked awkward visible-result action prose",)


def test_generated_public_copy_rejects_duplicate_status_and_clipped_terminals() -> None:
    assert generated_public_copy_issues(
        "accepted-project memory preview",
        {
            "owned_state": (
                "Public Coordination Status View Service owns status status timeline, "
                "current owner, and transition history."
            )
        },
    ) == ("accepted-project memory preview leaked adjacent duplicate word prose",)
    assert generated_public_copy_issues(
        "project brief preview",
        (
            "Release 0.0.1 proves one accepted coordination path while private "
            "details remain"
        ),
    ) == ("project brief preview leaked clipped or dangling public copy",)
    assert generated_public_copy_issues(
        "accepted-project memory preview",
        (
            "Accepts request intake state, request intake, intake state, and actor context. "
            "Plan: odylith/radar/radar.html?view=plan. "
            "flowchart LR action --> domain_state domain_state --> review."
        ),
    ) == ()


def test_status_view_contract_does_not_repeat_status_when_object_already_names_status() -> None:
    contract = status_view_contract(
        label="Public Coordination Status View Service",
        state_label="Public coordination status",
        context="public coordination status",
        previous_label="Coordination ledger",
        next_label="",
    )

    owned_state = str(contract["owned_state"])
    assert "status status" not in owned_state
    assert "public coordination status timeline" in owned_state


def test_release_scope_keeps_visible_result_owner_in_first_release_despite_private_boundary() -> None:
    scope = release_scope_for_component(
        {
            "label": "Public Coordination Status View Service",
            "source_system_description": "Public coordination status view",
            "responsibility": "Owns public coordination status view state and publication handoff.",
            "boundary": "Owns public coordination status timeline and local handoff decisions.",
        },
        first_path=(
            "A coordinator records a support request, a reviewer confirms readiness, "
            "and a commander publishes public coordination status."
        ),
        proof_boundary=(
            "Release 0.0.1 is proven when public coordination status is published "
            "while private resident details remain inside the governed boundary."
        ),
        non_goals=(),
    )

    assert scope == "first_path_required"


def test_confirmed_intent_actor_completion_uses_semantic_steps_not_cross_actor_clause_tail() -> None:
    intent = parse_confirmed_intent_text(
        """
# Cross Border Coordination

## Product story
A regional office coordinates partner decisions and publishes public status before teams act.

## State object
Coordination record with support request, access restriction, capacity constraint, resource commitment, readiness, and public status.

## First complete path
City dispatcher records evacuation support request, tribal liaison reviews restricted access needs, hospital coordinator records capacity constraints, mutual-aid officer confirms resource commitments, shelter lead records readiness, and emergency commander publishes public coordination status.

## Human actors
- City dispatcher
- Tribal liaison
- Hospital coordinator
- Mutual-aid officer
- Shelter lead
- Emergency commander
- Public information officer

## Internal product systems
- Request intake
- Access review board
- Capacity ledger
- Commitment tracker
- Readiness board
- Public status view

## Proof boundary
Release 0.0.1 is proven when one request moves through access, capacity, commitment, readiness, and public status proof.
""",
        prompt="Create a coordination workspace.",
    )

    rendered = json.dumps(intent, sort_keys=True)
    assert "record capacity constraints, mutual-aid" not in rendered
    assert "Public Information Officer: uses the product to review resource commitments" not in rendered
    assert intent["human_actors"][0] == (
        "City Dispatcher: uses the product to record evacuation support request; "
        "the outcome stays clear enough to choose the next step"
    )
    assert "Hospital Coordinator: uses the product to record capacity constraints;" in rendered
    assert "Mutual Aid Officer: uses the product to confirm resource commitments;" in rendered
    assert "Emergency Commander: uses the product to publish public coordination status;" in rendered
    assert "Public Information Officer: supplies context, reviews the result, or takes the next step named by the first release" in rendered


def test_confirmed_actor_completion_augments_partial_actor_list_from_first_path() -> None:
    completed = complete_confirmed_intent(
        {
            "title": "Multi-jurisdictional Disaster Logistics Coordination Platform",
            "product_story": (
                "The product coordinates a first evacuation logistics path where named operators record, "
                "review, confirm, and publish status without making emergency decisions."
            ),
            "state_object": (
                "A public coordination status record tracks the actor, source input, current status, "
                "owner, blocker, handoff, evidence, and version history for the first path."
            ),
            "first_path": (
                "A city dispatcher records an evacuation support request. A tribal liaison reviews restricted "
                "access needs. A hospital coordinator records capacity constraints. A mutual-aid officer confirms "
                "resource commitments. A shelter lead records readiness. An emergency commander publishes public "
                "coordination status."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when the accepted first path is complete, reviewable, and blocked when "
                "required, with replayable public coordination status evidence."
            ),
            "human_actors": [
                "City Dispatcher: needs the product to record an evacuation support request and keep the result visible and reviewable",
                "Tribal Liaison: needs the product to review restricted access needs and keep the result visible and reviewable",
                "Hospital Coordinator: needs the product to record capacity constraints and keep the result visible and reviewable",
            ],
            "internal_systems": [
                "Intake register records source input.",
                "Review workspace presents current state.",
                "Proof ledger keeps validation evidence.",
            ],
        }
    )

    rendered = json.dumps(completed, sort_keys=True)
    assert "Mutual Aid Officer: uses the product to confirm resource commitments" in rendered
    assert "Shelter Lead: uses the product to record readiness" in rendered
    assert "Emergency Commander: uses the product to publish public coordination status" in rendered
    assert "Evacuation Support" not in rendered
    assert "Reviewable Tribal Liaison" not in rendered


def test_confirmed_project_brief_preserves_complete_first_path_and_actor_boundary() -> None:
    first_path = (
        "A city dispatcher records an evacuation support request. A tribal liaison reviews restricted access needs. "
        "A hospital coordinator records capacity constraints. A mutual-aid officer confirms resource commitments. "
        "A shelter lead records readiness. An emergency commander publishes public coordination status. "
        "First release proves one end-to-end request moves through access, capacity commitment, readiness and public "
        "status without making emergency decisions."
    )
    human_actors = [
        "City Dispatcher: uses the product to record evacuation support request; the outcome stays clear enough to choose the next step",
        "Tribal Liaison: uses the product to review restricted access needs; the outcome stays clear enough to choose the next step",
        "Hospital Coordinator: uses the product to record capacity constraints; the outcome stays clear enough to choose the next step",
        "Mutual Aid Officer: uses the product to confirm resource commitments; the outcome stays clear enough to choose the next step",
        "Shelter Lead: uses the product to record readiness; the outcome stays clear enough to choose the next step",
        "Emergency Commander: uses the product to publish public coordination status; the outcome stays clear enough to choose the next step",
    ]

    brief = confirmed_project_brief(
        label="Multi-jurisdictional Disaster Logistics Coordination Platform",
        prompt="Create a coordination workspace.",
        release="0.0.1",
        state_object="Public coordination status record",
        evidence_record="Coordination proof ledger",
        product_story=(
            "The product coordinates a first evacuation logistics path where named operators record, review, "
            "confirm, and publish status without making emergency decisions."
        ),
        first_path=first_path,
        proof_boundary=(
            "Release 0.0.1 succeeds when the accepted first path is complete, reviewable, and blocked when "
            "required, with replayable public coordination status evidence."
        ),
        human_actors=human_actors,
        internal_systems=[
            "Request intake",
            "Access review board",
            "Capacity ledger",
            "Commitment tracker",
            "Readiness board",
            "Public status view",
        ],
    )
    rendered = json.dumps(brief, sort_keys=True)
    first_path_section = next(row for row in brief["blueprint_sections"] if row["section"] == "First path")
    actor_section = next(row for row in brief["blueprint_sections"] if row["section"] == "Actors and systems")
    readiness_gate = brief["coding_readiness_gates"][1]

    assert "mutual-aid officer confirms resource commitments" in first_path_section["must_capture"]
    assert "emergency commander publishes public coordination status" in first_path_section["must_capture"]
    assert "First release proves" not in first_path_section["must_capture"]
    assert "Mutual Aid Officer" in actor_section["must_capture"]
    assert "Shelter Lead" in actor_section["must_capture"]
    assert "Emergency Commander" in actor_section["must_capture"]
    assert "confirm resource commitments" in readiness_gate
    assert "record readiness" in readiness_gate
    assert "publish public coordination status" in readiness_gate
    assert generated_public_copy_issues("coordination project brief", brief) == ()
    assert "without making emergency decisions" in rendered


def test_operator_next_steps_use_typed_first_path_instead_of_contract_field_dump() -> None:
    first_path = (
        "City dispatcher records evacuation support request. Tribal liaison reviews restricted access needs. "
        "Hospital coordinator records capacity constraints. Mutual-aid officer confirms resource commitments. "
        "Shelter lead records readiness. Emergency commander publishes public coordination status."
    )
    state_object = (
        "Evacuation coordination record with incident area, resident support request, route constraint, "
        "mutual-aid commitment, hospital capacity note, tribal access restriction, shelter readiness, "
        "approval decision, and public coordination status."
    )
    model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Cross Border Wildfire Coordination",
            first_path=first_path,
            state_object=state_object,
            proof_boundary="Public coordination status is visible and reviewable.",
            components=(),
        )
    )
    proposal = {
        "intent": {"title": "Cross Border Wildfire Coordination", "first_path": first_path, "state_object": state_object},
        "semantic_model": model,
        "backlog": [
            {"title": "Prove one path"},
            {
                "title": "Let City Dispatcher See Public Coordination Status",
                "recommended_first_slice": (
                    "One representative path where the city dispatcher can record evacuation support request "
                    "and the tribal liaison can see public coordination status."
                ),
            },
        ],
        "project_brief": {
            "coding_readiness_gates": [
                "The accepted product story names the user problem.",
                "The first implementation lane is ready.",
                "Release 0.0.1 has proof checks for success, failure, replay, and review evidence.",
                "External dependencies are simulated, source-backed, or deferred.",
            ]
        },
    }
    next_steps = build_next_steps(
        proposal=proposal,
        backlog_result={
            "created": [
                {"idea_id": "B-001", "title": "Prove One Complete Cross Border Wildfire Path"},
                {"idea_id": "B-002", "title": "Let City Dispatcher See Public Coordination Status"},
            ]
        },
        first_release_workstreams=["B-001", "B-002"],
        program_result={"umbrella_id": "B-001", "waves": [{"status": "active", "primary_workstreams": ["B-002"]}]},
        release_selector="0.0.1",
    )
    prompt = next_steps["implementation_prompt"]

    assert "Preserve this accepted first path:" in prompt
    assert "records evacuation support request" in prompt
    assert "public coordination status" in prompt
    assert "status evacuation coordination incident area" not in prompt
    assert "route constraint" not in prompt
    assert generated_public_copy_issues("operator next-steps preview", next_steps) == ()


def test_source_launch_prompt_preserves_canonical_apply_first_path_over_project_brief_summary() -> None:
    accepted_path = (
        "Review teams track source evidence, owner attestations, queue holds, inspection outcomes, "
        "exception notes, and release proof before a record closes."
    )
    split_summary = (
        "Review teams track source evidence, owner attestations. Queue holds, inspection outcomes, "
        "exception notes, and release proof before a record closes."
    )
    next_steps = build_next_steps(
        proposal={
            "intent": {"title": "Review Workspace", "first_path": accepted_path},
            "apply_semantic_input": {"first_path": accepted_path},
            "semantic_model": {"first_path_contract": {"raw_path": split_summary}},
            "backlog": [
                {"title": "Prove One Complete Review Path"},
                {"title": "Let Review Teams Track Source Evidence", "recommended_first_slice": "Track source evidence."},
            ],
            "project_brief": {
                "blueprint_sections": [{"section": "First path", "must_capture": split_summary}],
                "coding_readiness_gates": ["The first implementation lane is ready."],
            },
        },
        backlog_result={
            "created": [
                {"idea_id": "B-001", "title": "Prove One Complete Review Path"},
                {"idea_id": "B-002", "title": "Let Review Teams Track Source Evidence"},
            ]
        },
        first_release_workstreams=["B-001", "B-002"],
        program_result={"umbrella_id": "B-001", "waves": [{"status": "active", "primary_workstreams": ["B-002"]}]},
        release_selector="0.0.1",
    )

    prompt = next_steps["implementation_prompt"]

    assert f"Preserve this accepted first path: {accepted_path}" in prompt
    assert "owner attestations. Queue holds" not in prompt


def test_field_heavy_state_object_stays_compact_in_workstream_titles_and_completion_metrics() -> None:
    state_object = (
        "Corridor Readiness Record with route segment, requesting organization, receiving site, operating window, "
        "waiver notes, constraint status, approval decision, public status, and review evidence."
    )
    first_path = (
        "Municipal airspace coordinator records a corridor request, route constraint reviewer checks blocked constraints, "
        "hospital receiving-site coordinator confirms receiving-site readiness, and public information officer publishes a safe operating status."
    )
    components = [
        {"component_id": "corridor_console", "label": "Corridor Readiness Console"},
        {"component_id": "route_ledger", "label": "Route Constraint Ledger"},
        {"component_id": "public_surface", "label": "Public Status Surface"},
    ]
    workflow_title, boundary_title, proof_title = confirmed_workstream_titles(
        label="Regional Drone Corridor Safety Console",
        components=components,
        internal_systems=[
            "Corridor Readiness Console records corridor request evidence.",
            "Route Constraint Ledger keeps route constraints and approval history.",
            "Public Status Surface presents safe operating status.",
        ],
        first_path=first_path,
        state_object=state_object,
        proof_boundary="First release proves one corridor request from intake to public safe operating status.",
        human_actors=["Municipal airspace coordinator", "Public information officer"],
    )
    projected_state = completion_state_object({"intent": {"state_object": state_object}})

    assert "Requesting Organization" not in boundary_title
    assert "Requesting Organization" not in proof_title
    assert "Corridor Readiness Record" in boundary_title
    assert "Corridor Readiness Record" in proof_title
    assert projected_state == "Corridor Readiness Record"
    assert workflow_title
    assert generated_public_copy_issues(
        "field-heavy state titles",
        {"workflow_title": workflow_title, "boundary_title": boundary_title, "proof_title": proof_title},
    ) == ()


def test_accepted_source_launch_prompt_fails_when_state_terms_leak_into_first_path_segment() -> None:
    first_path = "City dispatcher records evacuation support request. Emergency commander publishes public coordination status."
    state_object = "Evacuation coordination record with incident area, route constraint, approval decision, and public coordination status."
    model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="Cross Border Wildfire Coordination",
            first_path=first_path,
            state_object=state_object,
            proof_boundary="Public coordination status is visible and reviewable.",
            components=(),
        )
    )
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {"title": "Cross Border Wildfire Coordination", "first_path": first_path, "state_object": state_object},
            "semantic_model": model,
        },
        release_selector="0.0.1",
        accepted_project_preview={
            "schema_version": "odylith.accepted_project.v1",
            "origin": "greenfield",
            "proposal": {
                "intent": {"title": "Cross Border Wildfire Coordination", "first_path": first_path, "state_object": state_object},
                "semantic_model": model,
            },
            "validation_gate": {"status": "passed"},
            "created": {"workstreams": [], "components": [], "diagrams": [], "release_selector": "0.0.1"},
            "source_launch": {
                "implementation_prompt": (
                    "After project-first scope is accepted, start B-002. Preserve this accepted first path: "
                    "City dispatcher records evacuation support request status evacuation coordination incident area. "
                    "Treat the first workstream as the coding scope."
                )
            },
        },
    )

    report = build_greenfield_package_report(package)

    assert report.status == "failed"
    assert any("mixes state-object terms into the accepted first-path clause" in issue for issue in report.issues)


def test_first_path_clauses_separate_user_action_from_internal_processing() -> None:
    path = (
        "The requester enters the request type, amount, timing constraints, and contact details. "
        "The workspace checks the request against the team rules, asks for missing information when needed, "
        "and displays a decision summary with reason notes. A reviewer can inspect the request, add follow-up notes, "
        "and keep the next action visible."
    )

    clauses = first_path_clauses(path)

    assert clauses.action_chain.startswith("enter the request type")
    assert "checks the request" not in clauses.action_chain
    assert "asks for missing" not in clauses.action_chain
    assert clauses.visible_result == "a decision summary with reason notes"


def test_unheaded_confirmed_intent_paragraphs_do_not_fall_back_to_mechanistic_copy() -> None:
    markdown = """
# Request Review Workspace

A small team needs one place to turn incoming requests into clear review outcomes. Today request details, reviewer notes, and decisions sit in separate messages, so the person asking cannot tell what is missing and the reviewer cannot see why a request moved forward or stopped.

The central object is a tracked request with submitted details, reviewer notes, missing-information prompts, a decision summary, and a history of corrections.

A requester opens the web app, enters a request type, amount, constraints, and contact details. The product checks the request, asks for missing information when required, and displays a decision summary with reason notes. A reviewer can then inspect the request and follow up from the same record.

Release 0.0.1 succeeds when one requester can submit a complete request, see a decision summary with reason notes, correct a missing field, and leave a reviewable record for a reviewer. Live integrations and multi-team routing are out of scope for the first release.

## Human actors
- Requester
- Reviewer

## Internal product systems
- Request Intake — collects required request details and missing-information corrections.
- Review Workspace — shows reviewer notes, decision summary, reason notes, and follow-up context.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Create a request review workspace.",
        title="Request Review Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["state_object"].startswith("a tracked request")
    assert "central object is" not in intent["state_object"].casefold()
    assert intent["first_path"].startswith("A requester opens the web app")
    assert intent["proof_boundary"].startswith("Release 0.0.1 succeeds when one requester")
    assert "Release 0.0.1 succeeds" not in intent["first_path"]
    assert intent["opportunity"] == (
        "Make the first version valuable by proving the smallest complete outcome: "
        "enter a request type, amount, constraints and contact details, ending in a decision summary with reason notes."
    )
    assert "starts one real" not in rendered
    assert "move it through input, review, decision" not in rendered
    assert "can a requester opens" not in rendered
    assert "A decision summary" not in intent["product_view"]
    assert generated_semantic_slop_issues(proposal) == []


def test_confirmed_completion_writes_human_capability_and_visible_result_copy() -> None:
    markdown = """
# RepairDesk - Neighborhood Repair Booking

## Product story
Residents need a simple way to get small home repairs scheduled without making repeated calls, guessing availability, or losing track of what was promised. RepairDesk gives one household a clear booking path for a repair request and gives a local repair coordinator enough detail to accept, schedule, or reject the job.

## State object
The product keeps a repair request with customer contact information, location, repair category, description, preferred appointment windows, quoted status, scheduling status, coordinator decision, and customer-visible confirmation.

## First complete path
A resident opens the web app, describes a repair, chooses appointment windows, and submits the request. RepairDesk checks that the request has enough detail, records it, shows the resident a confirmation with next steps, and places the request in a coordinator queue for scheduling.

## Human actors
- Resident: requests a repair and needs a clear confirmation of what happens next.
- Repair coordinator: reviews new requests, accepts jobs that can be scheduled, and follows up when details are missing.

## Internal product systems
- Repair intake: captures the request and validates required detail.
- Scheduling queue: keeps accepted requests visible for coordinator review.
- Customer confirmation: shows the resident the submitted request, status, and next step.

## Proof boundary
The release is good enough when a resident can submit a complete repair request, see a confirmation, and a coordinator can find the same request with the details needed to schedule or ask for corrections. Emergency dispatch, payment, technician routing, and live calendar integration are deferred.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Neighborhood repair booking web app.",
        title="RepairDesk - Neighborhood Repair Booking",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    posture_text = json.dumps(
        {
            "opportunity": intent.get("opportunity"),
            "product_view": intent.get("product_view"),
            "success_metrics": intent.get("success_metrics"),
            "project_brief": proposal.get("project_brief"),
        },
        sort_keys=True,
    ).casefold()

    assert "can a resident opens" not in rendered
    assert "a user can resident" not in rendered
    assert "user can resident submits" not in rendered
    assert "resident a confirmation" not in posture_text
    assert "visible outcome from" not in posture_text
    assert "description" in intent["state_object"].casefold()
    assert "describe a repair" in intent["product_view"].casefold()
    assert "open the web app" not in intent["product_view"].casefold()
    assert "a confirmation with next steps" in intent["product_view"].casefold()
    assert "Keep Repair Request Clear and Reviewable" in [row["title"] for row in proposal["backlog"]]
    assert all("Product Keeps" not in row["title"] for row in proposal["backlog"])
    assert all(len(row["title"].split()) <= 12 for row in proposal["backlog"])
    assert "contrastive domain drift" not in rendered
    assert generated_semantic_slop_issues(proposal) == []


def test_component_spec_narration_filters_action_fragments_from_artifact_phrases() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Coordinator Review Queue",
            "source_system_description": (
                "the coordinator can find the request with the details needed to schedule or reject it"
            ),
        },
        proposal={
            "intent": {
                "title": "Neighborhood Repair Booking",
                "first_path": (
                    "A resident describes a repair, submits the request, and sees a confirmation with next steps. "
                    "The coordinator can find the request with the details needed to schedule or reject it."
                ),
                "proof_boundary": (
                    "The release is good enough when the request can be scheduled or rejected from the saved details."
                ),
            }
        },
        sibling={
            "label": "Customer Confirmation and Status View Service",
            "source_system_description": "shows the submitted request, status, and next step",
        },
        previous_label="Repair Request Intake Service",
        next_label="Customer Confirmation and Status View Service",
        state_label="Repair Request",
    ).fields
    spec = build_narrative_component_spec(
        component_id="coordinator-review-queue",
        label="Coordinator Review Queue",
        path="src/example/coordinator_review_queue",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility="keeps accepted repair requests visible for coordinator review",
        implementation_handoff={"workstream_id": "B-002", "workstream_title": "Keep Requests Reviewable"},
        component_contract=contract,
    ).casefold()

    assert "coordinator find" not in spec
    assert "request needed" not in spec
    assert "state for customer confirmation" not in spec
    assert "responsibilities not named by this component boundary" not in spec
    assert "correction marker travels" not in spec
    assert "scheduled rejected" not in spec
    assert "travel with enough context from" in spec
    assert generated_semantic_slop_issues(contract) == []


def test_component_spec_narration_rejects_derived_system_description_debris() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Request Workflow Planner Surface",
            "source_system_description": (
                "captures user actions, explains blocked states, and keeps the next visible step tied to: "
                "a requester opens the web app, enters a request, and sees a decision summary"
            ),
        },
        proposal={
            "intent": {
                "title": "Request Review Workspace",
                "first_path": (
                    "A requester opens the web app, enters a request, corrects missing information, "
                    "and sees a decision summary with reason notes."
                ),
                "state_object": "The product keeps a tracked request with status, reason notes, and correction history.",
                "proof_boundary": "The release works when the request can be submitted, corrected, and reviewed.",
            }
        },
        sibling={
            "label": "Request Evidence Log",
            "source_system_description": "records the result, validation status, and reviewable proof",
        },
        previous_label="Request Intake",
        next_label="Request Evidence Log",
        state_label="Tracked Request",
    ).fields
    spec = build_narrative_component_spec(
        component_id="request-workflow-planner",
        label="Request Workflow Planner Surface",
        path="src/example/request_workflow_planner",
        kind="client",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-003",),
        diagrams=("D-002",),
        responsibility="shows the request status and next step",
        implementation_handoff={"workstream_id": "B-003", "workstream_title": "Keep Request State Understandable"},
        component_contract=contract,
    ).casefold()

    assert "user actions, explains" not in spec
    assert "tied to:" not in spec
    assert "opens the web" not in spec
    assert "owns identity" not in spec
    assert "blocked states, and next visible step" not in spec
    assert "run one request workflow planner" not in spec
    assert "run one blocked" not in spec
    assert "replay evidence for request workflow planner surface" in spec
    assert generated_semantic_slop_issues(contract) == []


def test_status_view_registry_spec_preserves_complete_failure_clause() -> None:
    contract = status_view_contract(
        label="Public Coordination Status View Service",
        state_label="Coordination Status",
        context="Public coordination status view publishes lifecycle status, role visibility, and source event history.",
        previous_label="Shelter Readiness Board Service",
        next_label="Status viewers and release proof review",
    )

    spec = build_narrative_component_spec(
        component_id="public-coordination-status-view",
        label="Public Coordination Status View Service",
        path="src/example/public_coordination_status_view",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-004",),
        diagrams=("D-002",),
        responsibility="keeps public coordination status visible without rewriting source records",
        implementation_handoff={"workstream_id": "B-004", "workstream_title": "Show Trusted Status"},
        component_contract=contract,
    )
    lowered = spec.casefold()

    assert "the product failure to guard against: an invalid transition can look valid" in lowered
    assert "wrong role can see private status" in lowered
    assert "an can look lifecycle event" not in lowered
    assert generated_public_copy_issues("Registry component spec `Public Coordination Status View Service`", spec) == ()


def test_unheaded_confirmation_preserves_story_state_path_and_proof_boundaries() -> None:
    markdown = """
# Neighborhood Repair Booking

Residents need a simple way to get small home repairs scheduled without making repeated calls, guessing availability, or losing track of what was promised. The product gives one household a clear booking path for a repair request and gives a local repair coordinator enough detail to accept, schedule, or reject the job.

The product keeps a repair request with customer contact information, location, repair category, description, preferred appointment windows, quoted status, scheduling status, coordinator decision, and customer-visible confirmation.

A resident opens the web app, describes a repair, chooses appointment windows, and submits the request. The product checks that the request has enough detail, records it, shows the resident a confirmation with next steps, and places the request in a coordinator queue for scheduling.

The release is good enough when a resident can submit a complete repair request, see a confirmation, and a coordinator can find the same request with the details needed to schedule or ask for corrections.
"""

    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Neighborhood repair booking web app.",
        title="Neighborhood Repair Booking",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert intent["product_story"].startswith("Residents need a simple way")
    assert intent["state_object"].startswith("a repair request")
    assert intent["first_path"].startswith("A resident opens the web app")
    assert intent["proof_boundary"].startswith("The release is good enough")
    assert "The release is good enough" not in intent["first_path"]
    assert "Customer:" not in " ".join(intent["human_actors"])
    assert "operator:" not in " ".join(intent["human_actors"]).casefold()
    assert "request with the details needed to schedule" not in proposal["backlog"][0]["recommended_first_slice"]
    assert "shows the resident:" not in rendered
    assert "resident and shows the resident" not in rendered
    assert "customer, local repair coordinator" not in rendered
    assert "neighborhood repair booking operator" not in rendered
    assert "dispatch payment technician" not in rendered
    assert "user can resident" not in rendered
    assert "coordinator find" not in rendered
    assert "user actions, explains" not in rendered
    assert "tied to:" not in rendered
    assert "needed for a resident opens" not in rendered
    assert "product keeps a repair request" not in rendered
    assert "produce and review a confirmation with next steps" in rendered
    assert generated_semantic_slop_issues(proposal) == []


def test_unheaded_intent_without_actor_section_derives_stable_roles_and_short_workstream_titles() -> None:
    markdown = """
# Request Review Workspace

A small operations team receives important requests through scattered messages and shared notes. They need one place where a requester can send a complete request, see whether it is accepted or blocked, and understand what happens next without chasing the team for status.

The central state is a tracked request with requester identity, requested amount, requested timing, constraints, decision summary, reason notes, follow-up owner, and visible blocked-state history.

The requester enters the request type, amount, timing constraints, and contact details. The workspace checks the request against the team rules, asks for missing information when needed, and displays a decision summary with reason notes. A reviewer can inspect the request, add follow-up notes, and keep the next action visible.

The first release succeeds when one requester can submit a complete request and one reviewer can confidently decide whether to accept it, return it for missing information, or keep it visible for follow-up. Multi-team routing, external integrations, automated approvals, and long-term analytics stay outside the first release.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Create a request review workspace.",
        title="Request Review Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)
    titles = [row["title"] for row in proposal["backlog"]]
    actor_labels = [row.split(":", 1)[0] for row in intent["human_actors"]]

    assert "Requester" in actor_labels
    assert "Request Reviewer" in actor_labels
    assert "Reviewer" not in actor_labels
    assert "Where a Requester" not in rendered
    assert "Chasing the Team" not in rendered
    assert "Notes a Reviewer" not in rendered
    assert "And One Reviewer" not in rendered
    assert "Reviewer Can" not in rendered
    assert "other accepted items" not in rendered.casefold()
    assert "other accepted actors" not in rendered.casefold()
    generated_backlog_text = json.dumps(
        [
            {
                "problem": row.get("problem"),
                "opportunity": row.get("opportunity"),
                "product_view": row.get("product_view"),
                "recommended_first_slice": row.get("recommended_first_slice"),
                "success_metrics": row.get("success_metrics"),
                "rationale_lines": row.get("rationale_lines"),
            }
            for row in proposal["backlog"]
        ],
        sort_keys=True,
    )
    assert "checks the request against the team rules, asks" not in generated_backlog_text
    assert "inspect the request, and add follow-up notes" not in generated_backlog_text
    assert "the team can prove Release 0.0.1 is trusted only" not in rendered
    assert "Release 0.0.1 is trusted only when the accepted path" not in rendered
    assert "accepted path can be replayed from input through state change" not in rendered
    assert "operating reality clear enough" not in rendered
    assert "The weak inputs are the request type and add follow-up notes" not in rendered
    assert "guide path capture allowed command" not in rendered.casefold()
    assert "capture allowed command" not in rendered.casefold()
    assert "responsibilities not named by this component boundary" not in rendered.casefold()
    assert "before this component can guide" not in rendered.casefold()
    assert all("Multi-team Routing" not in title for title in titles)
    assert all(len(title.split()) <= 12 for title in titles)
    assert any(title.startswith("Let Requester See a Decision Summary") for title in titles)
    assert "long-term analytics" not in proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()
    assert generated_semantic_slop_issues(proposal) == []


def test_plain_participants_section_does_not_poison_radar_titles_or_first_path() -> None:
    markdown = """
# Neighborhood Repair Booking

Residents need a calmer way to turn small home repair problems into confirmed appointments. The product lets a resident describe the repair, add availability, see an estimate window, choose a provider slot, and finish with a booking they can trust.

The core state is one repair request and its booking history: resident contact details, repair description, estimate window, selected appointment slot, provider assignment, booking confirmation, and any blocker that prevents a reliable appointment.

The first complete path starts when a resident opens the web app, describes a repair, provides contact and availability details, reviews an estimate window, selects an appointment slot, and submits the request. The system confirms the booking, records the selected provider slot, shows the resident what happens next, and makes the booking available for provider review.

Participants:
- Resident: needs a clear repair appointment without repeated calls or uncertainty.
- Local provider: receives complete repair bookings with enough context to prepare for the visit.
- Coordinator: maintains provider availability and resolves blocked or unclear bookings.

Internal product systems:
- Repair request intake.
- Estimate and slot selection.
- Booking confirmation.
- Provider review queue.

Assumptions:
- Payments, emergency dispatch, and provider marketplace ranking are later scope.

Proof boundary:
- A resident can create a repair request, choose a slot, receive a confirmed booking, and see the next step.
- A provider-facing queue receives the booking with the required repair context.
- Missing contact details, unavailable slots, or incomplete repair descriptions block confirmation instead of producing a misleading booking.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Neighborhood repair booking web app.",
        title="Neighborhood Repair Booking",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)
    titles = [row["title"] for row in proposal["backlog"]]

    assert intent["first_path"].startswith("The first complete path starts when a resident opens")
    assert intent["human_actors"][0].startswith("Resident:")
    assert "Participants Resident" not in rendered
    assert "Resident Resident" not in rendered
    assert "Need A Calmer Way" not in " ".join(titles)
    assert any(title == "Let Resident Reach a Confirmed Booking" for title in titles)
    generated_backlog_text = json.dumps(
        [
            {
                "title": row.get("title"),
                "problem": row.get("problem"),
                "opportunity": row.get("opportunity"),
                "product_view": row.get("product_view"),
                "recommended_first_slice": row.get("recommended_first_slice"),
                "success_metrics": row.get("success_metrics"),
            }
            for row in proposal["backlog"]
        ],
        sort_keys=True,
    )
    workflow = proposal["backlog"][1]
    assert workflow["problem"].startswith("The resident needs the first interaction to let them reach a confirmed booking")
    assert "where trust can be lost first" not in generated_backlog_text.casefold()
    assert "replaying the whole workflow by hand" not in generated_backlog_text.casefold()
    assert "proof boundary" not in workflow["problem"].casefold()
    assert "the local provider can use the saved context" in " ".join(workflow["success_metrics"]).casefold()
    assert "complete path starts when" not in generated_backlog_text.casefold()
    assert "visible outcome from a confirmed booking" not in rendered.casefold()
    assert "a confirmed booking" in rendered
    assert generated_semantic_slop_issues(proposal) == []

    contract = derive_component_semantic_contract(
        proposal["components"][0],
        proposal=proposal,
        sibling=proposal["components"][1],
        previous_label="",
        next_label=proposal["components"][1]["label"],
        state_label="Repair Request",
    ).fields
    spec = build_narrative_component_spec(
        component_id=proposal["components"][0]["component_id"],
        label=proposal["components"][0]["label"],
        path="src/example/repair_request_intake",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility=proposal["components"][0].get("responsibility", ""),
        implementation_handoff={"workstream_id": "B-002", "workstream_title": workflow["title"]},
        component_contract=contract,
    )
    contract_text = json.dumps(contract, sort_keys=True).casefold()
    spec_text = spec.casefold()

    assert "center of gravity" not in spec_text
    assert "create repair request" not in contract_text
    assert "describe repair" not in contract_text
    assert "booking required" not in contract_text
    assert "intake service state update" not in contract_text
    assert "failure avoided" not in spec_text
    assert "responsible for the first product information" in spec_text
    assert "missing contact detail" in spec_text


def test_component_contract_uses_readable_irregular_lifecycle_verbs() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Progress View",
            "source_system_description": "shows saved entries, sends a correction prompt, and lets the user see the current status",
        },
        proposal={
            "intent": {
                "title": "Activity Progress Notebook",
                "first_path": (
                    "A person records an entry, sees the updated status, sends a correction, and the product shows the final view."
                ),
            }
        },
        sibling={"label": "Entry Capture"},
        previous_label="Entry Capture",
        next_label="Review View",
        state_label="Progress Record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "seed" not in rendered
    assert "keeped" not in rendered
    assert "sended" not in rendered
    assert "showed" not in rendered
    assert "seen" in rendered or "shown" in rendered or "sent" in rendered
    assert generated_semantic_slop_issues(contract) == []
    assert public_prose_quality_issues(contract) == []


def test_first_path_flowchart_drops_launcher_auth_step_and_keeps_domain_routing() -> None:
    mermaid = first_path_flowchart_mermaid(
        label="Activity Progress Notebook",
        actors=["Patient", "Reviewer"],
        components=[
            {"label": "Activity Capture", "release_scope": "first_path_required"},
            {"label": "Progress View", "release_scope": "first_path_required"},
            {"label": "Summary Review", "release_scope": "supporting"},
        ],
        first_path=(
            "A patient signs in. The patient logs a new activity. "
            "The product updates the progress view and the patient sees the result."
        ),
        semantic_model={
            "first_path_contract": {
                "events": [
                    {"text": "A patient signs in."},
                    {"text": "The patient logs a new activity with timing and note."},
                        {"text": "The workspace checks the activity against the saved preferences."},
                        {"text": "The product updates the progress view."},
                        {"text": "A reviewer can inspect the activity."},
                        {"text": "A reviewer can add follow-up notes and keep the next action visible."},
                        {"text": "The patient sees the result and next action."},
                ]
            }
        },
    )

    assert "signs in" not in mermaid.casefold()
    assert "C4" not in mermaid
    assert "Activity Capture" in mermaid
    assert "Progress View" in mermaid
    assert "User action" not in mermaid
    assert "Show outcome:" not in mermaid
    assert "Proof result" in mermaid
    assert "Done means" not in mermaid
    assert "patient sees" not in mermaid.casefold()
    assert "Activity against" not in mermaid
    assert "workspace checks" in mermaid.casefold()
    assert "Can inspect" not in mermaid
    assert "Reviewer inspects" in mermaid
    assert "and keep the next action" not in mermaid
    assert "Reviewer adds follow-up notes<br/>and keeps the next action" in mermaid


def test_public_quality_gate_rejects_raw_contract_parser_debris() -> None:
    issues = public_prose_quality_issues(
        {
            "component_contract": {
                "outside_boundary": (
                    "responsibilities not named by this component boundary; guide path capture allowed command; "
                    "exposes blocked states"
                ),
                "dependencies": [
                    "Coordinates with Intake Service so upstream state is available before this component can guide the first path."
                ],
            }
        }
    )

    joined = " ".join(issues)
    assert "mechanical boundary placeholder" in joined
    assert "parser action debris" in joined
    assert "mechanical dependency scaffold" in joined


def test_thin_prompt_recovery_preserves_input_list_before_purpose_tail(tmp_path: Path) -> None:
    prompt = (
        "Create a solar energy assessment workspace where a homeowner enters roof details, utility usage, "
        "shading concerns, and financing preferences so a coordinator can prepare a reviewed solar recommendation "
        "with savings, risk, and installation readiness."
    )
    intent = parse_confirmed_intent_text(prompt, prompt=prompt, fallback_title="Solar Energy Assessment Workspace")
    model = first_path_model(str(intent["first_path"]))

    assert "roof details" in intent["first_path"]
    assert "utility usage" in intent["first_path"]
    assert "shading concerns" in intent["first_path"]
    assert "financing preferences" in intent["first_path"]
    assert model.steps == (
        "A homeowner enters roof details, utility usage, shading concerns, and financing preferences",
        "Coordinator prepares a reviewed solar recommendation with savings, risk and installation readiness",
    )
    assert [row.split(":", 1)[0] for row in intent["human_actors"]] == ["Homeowner", "Coordinator"]

    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert "financing preferences so a coordinator:" not in rendered
    assert "actors include homeowner, financing preferences" not in rendered
    assert "first-path state: homeowner, financing preferences" not in rendered
    assert "roof details" in rendered
    assert "utility usage" in rendered
    assert "shading concerns" in rendered
    assert "financing preferences" in rendered
    assert "solar recommendation" in rendered
    assert generated_semantic_slop_issues(proposal) == []
    assert public_prose_quality_issues(proposal) == []
