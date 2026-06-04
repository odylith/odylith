from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    normalize_contract,
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_targets import (
    operator_component_spec_issues,
    repair_targets_from_spec_issues,
)
from odylith.runtime.domain_intelligence.greenfield_actor_terms import generic_actor_label_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_terms import localize_generic_actor_label
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_actor_terms import starts_with_generic_actor_label
from odylith.runtime.domain_intelligence.greenfield_component_term_index import component_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_term_index import component_local_terms
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_term_index import section_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import looks_action_form
from odylith.runtime.domain_intelligence.greenfield_component_terms import natural_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase_identity_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import term_phrase
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_compounds
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_terms
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import nearby_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import contract_focus
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import contract_list_text
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import state_transition_text
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import status_only_artifact_fragment
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import derive_component_semantic_contract
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import first_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import sentence_fragment
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import domain_label
from odylith.runtime.domain_intelligence.greenfield_text import visible_words
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.governance.component_spec_rendering import build_component_spec


ROOT = Path(__file__).resolve().parents[3]
CONFIRMED_COMPONENTS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py"
CONFIRMED_TEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_text.py"
GREENFIELD_TEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_text.py"
DOMAIN_TERM_INDEX_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py"
CONFIRMED_PROJECT_BRIEF_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_project_brief.py"
CONFIRMED_PROPOSAL_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_proposal.py"
GREENFIELD_COMMAND_TEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_command_text.py"
COMPONENT_CONTRACT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract.py"
COMPONENT_CONTRACT_PROFILES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract_profiles.py"
COMPONENT_CONTRACT_QUALITY_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract_quality.py"
)
COMPONENT_TERM_INDEX_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_term_index.py"
COMPONENT_TERMS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_terms.py"
ACTOR_TERMS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_actor_terms.py"
COMPONENT_TERM_WINDOWS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_term_windows.py"
COMPONENT_CONTRACT_DIFFERENTIATION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract_differentiation.py"
)
COMPONENT_CONTRACT_TARGETS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract_targets.py"
COMPONENT_CONTRACT_FIELDS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_contract_fields.py"
COMPONENT_SEMANTIC_CONTRACT_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_contract.py"
)
COMPONENT_AXES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_axes.py"


def test_confirmed_components_helper_shape_stays_below_soft_limit() -> None:
    source = CONFIRMED_COMPONENTS_PATH.read_text(encoding="utf-8")
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    index_source = DOMAIN_TERM_INDEX_PATH.read_text(encoding="utf-8")

    assert len(source.splitlines()) < 800
    assert source.count("def _title_phrase") == 1
    assert "def _can_clause" not in source
    assert "greenfield_domain_term_index import label_terms" in source
    assert "from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count" in source
    assert "def word_count" in text_source
    assert "for raw in re.findall" not in source
    assert 'len(re.findall(r"[A-Za-z0-9]+"' not in source
    assert 'len(re.findall(r"[a-z0-9]+"' not in source
    assert "def label_terms" in index_source

    assert domain_label("Build a 3D GIS Permit Review App", "") == "3D GIS Permit Review"
    assert domain_label("AI CRM workflows for UI audits", "") == "AI CRM Workflows"
    assert domain_label("", "Create a repair request tracker for contractors") == "Repair Request Tracker Contractors"
    assert word_count("`AI/ML` status review keeps source evidence visible.") == 8
    assert label_terms(
        "Build a 3D GIS Permit Review App",
        stopwords={"build", "a", "app"},
    ) == ["3D", "GIS", "Permit", "Review"]


def test_confirmed_project_brief_stays_in_dedicated_owner() -> None:
    component_source = CONFIRMED_COMPONENTS_PATH.read_text(encoding="utf-8")
    brief_source = CONFIRMED_PROJECT_BRIEF_PATH.read_text(encoding="utf-8")
    proposal_source = CONFIRMED_PROPOSAL_PATH.read_text(encoding="utf-8")
    command_source = GREENFIELD_COMMAND_TEXT_PATH.read_text(encoding="utf-8")

    assert len(component_source.splitlines()) < 800
    assert len(brief_source.splitlines()) < 800
    assert "from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import" in proposal_source
    assert "from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote" in proposal_source
    for moved in ("def confirmed_project_brief", "def _brief_option", "def _checkpoint", "def _brief_clause"):
        assert moved not in component_source
        assert moved in brief_source
    assert "def shell_quote" not in component_source
    assert "def shell_quote" not in brief_source
    assert command_source.count("def shell_quote") == 1


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


def test_component_contract_targets_stay_in_dedicated_owner() -> None:
    differentiation_source = COMPONENT_CONTRACT_DIFFERENTIATION_PATH.read_text(encoding="utf-8")
    target_source = COMPONENT_CONTRACT_TARGETS_PATH.read_text(encoding="utf-8")

    assert len(differentiation_source.splitlines()) < 800
    assert "greenfield_component_contract_targets as contract_targets" in differentiation_source
    assert "class _RepairTarget" not in differentiation_source
    assert "def _repair_targets" not in differentiation_source
    assert "def _operator_issue" not in differentiation_source
    assert "def _dedupe_targets" not in differentiation_source
    assert "class RepairTarget" in target_source
    assert "def repair_targets_from_spec_issues" in target_source
    assert "def operator_component_spec_issues" in target_source

    intake = {"label": "Intake Service"}
    review = {"label": "Review Service"}
    targets = repair_targets_from_spec_issues(
        ["component specs `Intake Service` and `Review Service` are too interchangeable"],
        rows_by_label={"Intake Service": intake, "Review Service": review},
        indexes_by_label={"Intake Service": 0, "Review Service": 1},
    )

    assert [target.row for target in targets] == [intake, review]
    assert [target.sibling for target in targets] == [review, intake]
    assert operator_component_spec_issues(
        ["component spec `Intake Service` does not contain enough component-local terms"]
    ) == [
        "Odylith could not derive enough component-local product terms from the accepted intent after deterministic "
        "repair: Intake Service remained too generic."
    ]


def test_component_contract_phrase_helpers_stay_in_terms_owner() -> None:
    contract_source = COMPONENT_CONTRACT_PATH.read_text(encoding="utf-8")
    differentiation_source = COMPONENT_CONTRACT_DIFFERENTIATION_PATH.read_text(encoding="utf-8")
    fields_source = COMPONENT_CONTRACT_FIELDS_PATH.read_text(encoding="utf-8")
    text_source = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    quality_source = COMPONENT_CONTRACT_QUALITY_PATH.read_text(encoding="utf-8")
    semantic_source = COMPONENT_SEMANTIC_CONTRACT_PATH.read_text(encoding="utf-8")
    axes_source = COMPONENT_AXES_PATH.read_text(encoding="utf-8")
    term_index_source = COMPONENT_TERM_INDEX_PATH.read_text(encoding="utf-8")
    terms_source = COMPONENT_TERMS_PATH.read_text(encoding="utf-8")
    actor_terms_source = ACTOR_TERMS_PATH.read_text(encoding="utf-8")
    term_windows_source = COMPONENT_TERM_WINDOWS_PATH.read_text(encoding="utf-8")

    assert len(terms_source.splitlines()) < 800
    assert len(term_windows_source.splitlines()) < 800
    assert len(differentiation_source.splitlines()) < 800
    assert len(fields_source.splitlines()) < 800
    assert len(quality_source.splitlines()) < 800
    assert len(term_index_source.splitlines()) < 800
    assert len(axes_source.splitlines()) < 800
    assert "def ordered_domain_terms" in term_index_source
    assert "def component_domain_terms" in term_index_source
    assert "def section_domain_terms" in term_index_source
    assert "def component_local_terms" in term_index_source
    assert "def literal_label_terms" in term_windows_source
    assert "def literal_label_compounds" in term_windows_source
    assert "def nearby_domain_terms" in term_windows_source
    assert "def looks_actor_term" in actor_terms_source
    assert "def generic_actor_label_prefix" in actor_terms_source
    assert "def starts_with_generic_actor_label" in actor_terms_source
    assert "def localize_generic_actor_label" in actor_terms_source
    assert "def visible_words" in text_source
    assert "def looks_action_form" in terms_source
    assert "def _looks_actorish_term" not in terms_source
    assert "greenfield_actor_terms import looks_actor_term" in terms_source
    assert "greenfield_actor_terms import generic_actor_label_prefix" in fields_source
    assert "greenfield_text import visible_words" in fields_source
    assert "greenfield_actor_terms import starts_with_generic_actor_label" in differentiation_source
    assert "greenfield_actor_terms import starts_with_generic_actor_label" in quality_source
    generic_actor_regex = "Operator|Maintainer|Reviewer|Primary user"
    assert generic_actor_regex not in fields_source
    assert generic_actor_regex not in differentiation_source
    assert generic_actor_regex not in quality_source
    assert "def ordered_domain_terms" not in quality_source
    assert "def domain_terms" not in quality_source
    assert "def _section_terms" not in quality_source
    assert "def _local_domain_terms" not in quality_source
    assert "def _term_token" not in quality_source
    assert "def natural_phrase" in terms_source
    assert "def term_phrase" in terms_source
    assert "def _term_phrase" not in contract_source
    assert "def _label_compound_focus" not in contract_source
    assert "def _literal_label_terms" not in contract_source
    assert "def _phrase(" not in differentiation_source
    assert "def _phrase(" not in fields_source
    assert "def literal_label_terms" not in fields_source
    assert "def _content_terms" not in differentiation_source
    assert "def _phrase(" not in semantic_source
    assert "def _phrase_identity_terms" not in semantic_source
    assert "def _content_terms" not in axes_source
    assert "def _term_token" not in axes_source
    assert "def _literal_label_compounds" not in differentiation_source
    assert "def _nearby_content_terms" not in differentiation_source
    assert "def _phrase(" not in axes_source
    assert "def _normalize_axis_text" not in axes_source
    assert "domain_terms(" in axes_source
    assert "term_phrase(" in axes_source
    assert "natural_phrase(" in contract_source
    assert "natural_phrase(" in differentiation_source
    assert "greenfield_component_term_windows import literal_label_compounds" in contract_source
    assert "greenfield_component_term_windows import literal_label_compounds" in differentiation_source
    assert "greenfield_component_term_windows import nearby_domain_terms" in differentiation_source
    assert "greenfield_component_term_windows import" in semantic_source
    assert "literal_label_compounds(" in differentiation_source
    assert "nearby_domain_terms(" in differentiation_source
    assert "greenfield_component_term_index import ordered_domain_terms" in contract_source
    assert "greenfield_domain_term_index import ordered_terms" in contract_source
    assert "greenfield_component_term_index import ordered_domain_terms" in differentiation_source
    assert "greenfield_component_term_index import ordered_domain_terms" in terms_source
    assert "greenfield_domain_term_index import ordered_terms" in terms_source
    assert "greenfield_domain_term_index import ordered_terms" in fields_source
    assert "phrase_identity_terms as _phrase_identity_terms" in semantic_source
    assert "normalize_domain_token" not in terms_source
    assert "normalize_domain_token" not in fields_source
    assert "for raw in re.findall" not in terms_source
    assert "for raw in re.findall" not in fields_source
    assert "re.findall(r\"[A-Za-z][A-Za-z'-]*\"" not in fields_source
    assert "def _word_set" not in contract_source
    assert "re.findall(r\"[a-z0-9][a-z0-9'-]*\"" not in contract_source
    assert "re.findall(r\"[a-z0-9][a-z0-9'-]*\"" not in fields_source
    assert "re.findall(r\"[a-z0-9][a-z0-9'-]*\"" not in differentiation_source
    assert 're.findall(r"[a-z0-9][a-z0-9_-]*"' not in contract_source
    assert 're.findall(r"[a-z0-9][a-z0-9_-]*"' not in differentiation_source
    assert "from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase" in fields_source
    assert "phrase(" in fields_source
    assert "domain_terms(" in differentiation_source

    assert ordered_domain_terms("Planning Engine validates plan targets and status windows.") == [
        "planning",
        "engine",
        "validate",
        "plan",
        "target",
        "window",
    ]
    assert ordered_terms("Status notifications surface", minimum=1) == ["status", "notification", "surface"]
    assert ordered_terms("Evidence uploads service", minimum=1) == ["evidence", "upload", "service"]
    assert component_domain_terms("Planning Engine validates plan targets and status windows.") == {
        "planning",
        "engine",
        "validate",
        "plan",
        "target",
        "window",
    }
    assert "structured" not in section_domain_terms("Structured contract validates plan targets and status windows.")
    assert component_local_terms(
        text_terms={"planning", "window", "shared"},
        name_terms={"planning", "engine"},
        all_text_terms=[{"planning", "window", "shared"}, {"review", "window", "shared"}],
        repeated_name_terms={"window"},
    ) == {"planning", "engine", "shared"}
    assert natural_phrase(["alpha", "beta"]) == "alpha and beta"
    assert natural_phrase(["alpha", "beta", "gamma"]) == "alpha, beta, and gamma"
    assert phrase(["alpha", "beta", "gamma"]) == "alpha, beta, gamma"
    assert term_phrase(["alpha", "beta", "gamma"]) == "alpha beta gamma"
    assert phrase_identity_terms("structured reviewer notes and status windows") == {
        "structured",
        "note",
        "status",
        "window",
    }
    assert looks_actor_term("inspector")
    assert looks_action_form("reviews")
    assert generic_actor_label_prefix("Risk reviewer guardrails") == "risk reviewer"
    assert generic_actor_label_prefix("End-user advocate checklist") == "end-user advocate"
    assert starts_with_generic_actor_label("Project operator: approval packet")
    assert localize_generic_actor_label("Operator approval packet") == "local operator approval packet"
    assert localize_generic_actor_label("Build owner proof") == "local build owner proof"
    assert clean_artifact_phrase("inspector reviews permit note") == "permit note"
    assert clean_artifact_phrase("student submits assignment details") == "assignment details"
    assert clean_artifact_phrase("operator approves safety guardrails") == "safety guardrails"
    assert visible_words("blocked-state update") == ("blocked", "state", "update")
    assert status_only_artifact_fragment("blocked update")
    assert not status_only_artifact_fragment("blocked-state update")
    assert contract_list_text("ranked status windows, blocked update") == "status windows"
    assert contract_focus(
        object_list="Primary user request status",
        action_terms=("record",),
        fallback="",
        role="input",
    ) == "required request status command, required fields, prior state, and explanation context"
    assert contract_focus(
        object_list="Risk reviewer guardrails",
        action_terms=("record",),
        fallback="",
        role="input",
    ) == "required risk guardrails command, required fields, prior state, and explanation context"
    assert contract_focus(
        object_list="Operator approval packet",
        action_terms=("record",),
        fallback="",
        role="input",
    ) == "required local operator approval packet command, required fields, prior state, and explanation context"
    assert normalize_contract({"owned_state": "Risk reviewer guardrails"})["owned_state"] == (
        "Local risk reviewer guardrails."
    )
    assert literal_label_terms("AI CRM Status Windows Viewer", noise_terms={"service"}) == [
        "ai",
        "crm",
        "status",
        "window",
    ]
    assert literal_label_terms("Risk Policy Guardrails Service", noise_terms={"service"}) == [
        "risk",
        "policy",
        "guardrails",
    ]
    assert literal_label_compounds("AI CRM Status Windows Service", noise_terms={"service"}) == [
        "ai crm",
        "crm status",
        "status window",
    ]
    assert literal_label_compounds("Risk Policy Guardrails Service", noise_terms={"service"}) == [
        "risk policy",
        "policy guardrails",
    ]
    assert nearby_domain_terms(
        ["window"],
        "Reviewer opens status windows before window proofs capture source-backed audit trails.",
        noise_terms={"service"},
        window=3,
    ) == ["open", "window", "capture", "source-backed"]
    transition = state_transition_text(
        action_terms=("request", "review"),
        object_phrases=("request status", "reviewed note", "open handoff"),
        context_text="The request status can become visible, reviewed, or blocked.",
        anchor_terms=("status",),
    )
    assert transition == "reviewed, open, requested, received, validated, blocked, revised, ready-for-next-step"


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
