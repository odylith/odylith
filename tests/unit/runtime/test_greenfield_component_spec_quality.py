from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence import (
    greenfield_component_contract as component_contract,
    greenfield_component_contract_differentiation as contract_differentiation,
    greenfield_component_contract_profiles as contract_profiles,
)
from odylith.runtime.domain_intelligence.greenfield_component_axes import derive_component_axis
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    dedupe_text,
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
from odylith.runtime.domain_intelligence.greenfield_component_terms import enrich_owned_state_from_io
from odylith.runtime.domain_intelligence.greenfield_component_terms import looks_action_form
from odylith.runtime.domain_intelligence.greenfield_component_terms import natural_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase_identity_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import term_phrase
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import singularize_last_word
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_compounds
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_terms
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import nearby_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import contract_focus
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import contract_list_text
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import noun_slot_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import proof_rows
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import produced_outputs_text
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import state_transition_text
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import status_only_artifact_fragment
from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import context_anchor_compounds
from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import context_object_phrases
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import derive_component_semantic_contract
from odylith.runtime.domain_intelligence.greenfield_component_narrative_view import component_narrative_view
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import first_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import sentence_fragment
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import domain_label
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_sentence
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import progression_marker_count
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
PROJECT_BRIEF_FIELDS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_project_brief_fields.py"
CONFIRMED_PROPOSAL_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_proposal.py"
GREENFIELD_COMMAND_TEXT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_command_text.py"
COMMON_VALUE_COERCION_PATH = ROOT / "src/odylith/runtime/common/value_coercion.py"
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
COMPONENT_SEMANTIC_CONTEXT_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_semantic_context.py"
)
COMPONENT_AXES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_axes.py"
COMPONENT_NARRATIVE_VIEW_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_narrative_view.py"
)
COMPONENT_SPEC_NARRATIVE_PATH = ROOT / "src/odylith/runtime/governance/component_spec_narrative.py"
SEMANTIC_QUALITY_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_semantic_quality.py"
APPLY_WRITE_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_write.py"


def test_greenfield_platform_helpers_do_not_hardcode_fixture_domains() -> None:
    guarded_roots = [
        ROOT / "src/odylith/runtime/domain_intelligence",
        ROOT / "src/odylith/runtime/project_intelligence",
        ROOT / "src/odylith/runtime/surfaces",
    ]
    forbidden_terms = (
        "arranger",
        "battery",
        "borrower",
        "buyer",
        "calorie",
        "controllable loads",
        "hardware automation",
        "homeowner",
        "market bidding",
        "musician",
        "patient",
        "peptide",
        "projected savings",
        "resident",
        "seller",
        "solar",
        "fifa",
        "football",
        "scoreline",
        "museum",
        "restitution",
        "student",
        "sunburn",
        "sunledger",
        "sunrecover",
        "teacher",
        "technician",
    )

    for path in sorted(path for root in guarded_roots for path in root.rglob("*.py")):
        source = path.read_text(encoding="utf-8").casefold()
        for term in forbidden_terms:
            assert term not in source, f"{path} hardcodes fixture-domain term: {term}"


def test_confirmed_components_helper_shape_stays_below_soft_limit() -> None:
    source = CONFIRMED_COMPONENTS_PATH.read_text(encoding="utf-8")
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    index_source = DOMAIN_TERM_INDEX_PATH.read_text(encoding="utf-8")

    assert len(source.splitlines()) < 800
    assert source.count("def _title_phrase") == 1
    assert "def _can_clause" not in source
    assert "greenfield_domain_term_index import label_terms" in source
    assert "from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count" in source
    assert "greenfield_text import visible_words" in source
    assert "def word_count" in text_source
    assert "for raw in re.findall" not in source
    assert 'len(re.findall(r"[A-Za-z0-9]+"' not in source
    assert 'len(re.findall(r"[a-z0-9]+"' not in source
    assert 're.findall(r"[a-z0-9]+"' not in source
    assert "def label_terms" in index_source

    assert domain_label("Build a 3D GIS Permit Review App", "") == "3D GIS Permit Review"
    assert domain_label("AI CRM workflows for UI audits", "") == "AI CRM Workflows"
    assert domain_label("", "Create a repair request tracker for contractors") == "Repair Request Tracker Contractors"
    assert word_count("`AI/ML` status review keeps source evidence visible.") == 8
    assert visible_words("UI-client dashboard") == ("UI", "client", "dashboard")
    assert (
        progression_marker_count(
            "Draft starts; then evidence is accepted.",
            connectors=("starts", "then"),
            punctuation=";",
        )
        == 3
    )
    assert label_terms(
        "Build a 3D GIS Permit Review App",
        stopwords={"build", "a", "app"},
    ) == ["3D", "GIS", "Permit", "Review"]
    assert confirmed_components(
        label="Permit Review",
        label_slug="permit-review",
        internal_systems=["UI-client dashboard - shows permit review status and source evidence."],
    )[0]["kind"] == "client"
    assert confirmed_components(
        label="Permit Review",
        label_slug="permit-review",
        internal_systems=["External-provider adapter - imports permit status from city records."],
    )[0]["kind"] == "adapter"
    assert confirmed_components(
        label="Review Evidence",
        label_slug="review-evidence",
        internal_systems=["Attachment evidence capture - owns accepted evidence, blocked states, and review handoff."],
        external_systems=["Attachment storage provider."],
    )[0]["kind"] == "service"


def test_component_contract_artifact_cleaning_stays_in_text_owner() -> None:
    text_source = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    callers = [
        COMPONENT_CONTRACT_PATH,
        COMPONENT_CONTRACT_PROFILES_PATH,
        COMPONENT_CONTRACT_QUALITY_PATH,
        COMPONENT_CONTRACT_DIFFERENTIATION_PATH,
        DOMAIN_TERM_INDEX_PATH,
        SEMANTIC_QUALITY_PATH,
        COMPONENT_CONTRACT_FIELDS_PATH,
        COMPONENT_SEMANTIC_CONTEXT_PATH,
        COMPONENT_SEMANTIC_CONTRACT_PATH,
        COMPONENT_TERMS_PATH,
    ]

    assert "def clean_artifact_text" in text_source
    assert clean_artifact_text("`Risk review` , ready") == "Risk review, ready"
    assert clean_artifact_text("`Risk review` (blocked) , ready", split_parentheses=True) == "Risk review blocked, ready"
    assert (
        clean_artifact_text(
            "odylith greenfield create --repo-root . --prompt x "
            "--intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm"
        )
        == "odylith greenfield create --repo-root . --prompt x "
        "--intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm"
    )

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "clean_artifact_text" in source
        assert 'clean_text(value).replace("`"' not in source
        assert 'replace("`", "").replace("(", " ").replace(")", " ")' not in source
        assert 're.sub(r"\\s+([,.;:?!])", r"\\1", text)' not in source


def test_component_contract_artifact_sentence_stays_in_text_owner() -> None:
    text_source = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    callers = [
        COMPONENT_CONTRACT_PATH,
        COMPONENT_CONTRACT_QUALITY_PATH,
    ]

    assert "def clean_artifact_sentence" in text_source
    assert clean_artifact_sentence("`risk review` , ready") == "Risk review, ready."
    assert clean_artifact_sentence("`risk review` , ready?") == "Risk review, ready?"
    assert normalize_contract({"owned_state": "`Risk reviewer` guardrails , ready"})[
        "owned_state"
    ] == "Local risk reviewer guardrails, ready."

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "clean_artifact_sentence" in source
        assert 'return text[:1].upper() + text[1:] + "."' not in source


def test_component_spec_narrative_semantics_stay_in_view_owner() -> None:
    renderer_source = COMPONENT_SPEC_NARRATIVE_PATH.read_text(encoding="utf-8")
    view_source = COMPONENT_NARRATIVE_VIEW_PATH.read_text(encoding="utf-8")

    assert "greenfield_component_narrative_view import component_narrative_view" in renderer_source
    assert "def _narrative_role" not in renderer_source
    assert "def _narrative_items" not in renderer_source
    assert "def _transition_material_score" not in renderer_source
    assert "def _state_material_score" not in renderer_source
    assert "def _phrases_too_similar" not in renderer_source
    assert "re.findall" not in renderer_source

    assert "class ComponentNarrativeView" in view_source
    assert "def narrative_role" in view_source
    assert "def transition_material_score" in view_source
    assert "import re" not in view_source
    assert "re." not in view_source


def test_component_narrative_view_derives_roles_and_material_items_without_renderer_rules() -> None:
    view = component_narrative_view(
        label="Planning Engine",
        owns=(
            "planning target result",
            "planning target result state",
            "blocked-state explanation",
            "source evidence attachment",
        ),
        accepts=("progress snapshot", "status window", "validation context"),
        produces=("planning recommendation result", "planning recommendation result", "next-step context"),
        transitions=("draft", "submitted", "blocked", "corrected", "ready-for-next-step"),
        outside=("adjacent component state owned elsewhere", "release approval"),
        proofs=("Replay evidence still connects the actor, input facts, status, and explanation.",),
    )

    assert view.role == "calculation"
    assert view.owned_items == ("planning target result", "blocked-state explanation", "source evidence attachment")
    assert view.produced_items == ("planning recommendation result",)
    assert "ready-for-next-step" in view.transition_items
    assert view.material_transition_count >= 2

    action_noise_view = component_narrative_view(
        label="Experiment Workspace",
        owns=(
            "experiment workspace state",
            "understand one-dimensional tunneling",
            "deterministic sample experiment",
            "scenario experiment workspace",
        ),
        accepts=("preset experiment",),
        produces=("visible result",),
        transitions=("accepted", "blocked", "corrected", "completed"),
        outside=(),
        proofs=("Replay evidence remains reviewable.",),
    )
    assert "understand one-dimensional tunneling" not in action_noise_view.owned_items
    assert "scenario experiment workspace" not in action_noise_view.owned_items
    assert action_noise_view.owned_items == ("experiment workspace state", "deterministic sample experiment")

    handoff_view = component_narrative_view(
        label="Coordinator Review Queue",
        owns=("review request state",),
        accepts=("accepted input facts",),
        produces=("next-step handoff",),
        transitions=("requested", "reviewed", "ready-for-next-step"),
        outside=("release approval",),
        proofs=("Handoff evidence remains replayable.",),
    )
    assert handoff_view.role == "handoff"


def test_component_contract_differentiation_keeps_sibling_boundary_as_component_ownership() -> None:
    axis = derive_component_axis(
        label_text="Crew Assignment Gate Service",
        context_text="owns duplicate review, severity check, assignment decision, blocker reason, and handoff evidence",
    )
    sibling_axis = derive_component_axis(
        label_text="Public Update Status Board Service",
        context_text="owns public update text, response status, publication state, and replayable communication proof",
    )
    assert axis is not None
    assert sibling_axis is not None

    outside = contract_differentiation._outside_boundary(
        axis=axis,
        sibling_axis=sibling_axis,
        sibling_label="Public Update Status Board Service",
    ).casefold()

    assert "public update status board service ownership of local state" in outside
    assert "board a" not in outside
    assert "assignment is" not in outside


def test_exact_string_dedupe_stays_in_common_value_owner() -> None:
    common_source = COMMON_VALUE_COERCION_PATH.read_text(encoding="utf-8")
    callers = [
        COMPONENT_AXES_PATH,
        COMPONENT_CONTRACT_DIFFERENTIATION_PATH,
        COMPONENT_CONTRACT_QUALITY_PATH,
        APPLY_WRITE_PATH,
    ]

    assert "def dedupe_strings" in common_source
    assert dedupe_strings([" Alpha ", "Alpha", "alpha", "", "Beta"]) == [
        "Alpha",
        "alpha",
        "Beta",
    ]
    assert dedupe_text(["`Alpha`", "Alpha", " alpha "]) == ["Alpha", "alpha"]
    assert contract_differentiation._unique_terms([" Alpha ", "alpha", "Beta"]) == [
        "alpha",
        "beta",
    ]
    axis = derive_component_axis(
        label_text="Status Panel",
        context_text="status panel validates source evidence for reviewers",
    )
    assert axis is not None
    assert axis.triggers == ("panel", "validate")

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "value_coercion import dedupe_strings" in source
        assert "seen: set[str]" not in source
        assert "seen.add(" not in source
    assert "def _unique(" not in COMPONENT_AXES_PATH.read_text(encoding="utf-8")
    assert "def _unique_strings" not in APPLY_WRITE_PATH.read_text(encoding="utf-8")


def test_confirmed_project_brief_stays_in_dedicated_owner() -> None:
    component_source = CONFIRMED_COMPONENTS_PATH.read_text(encoding="utf-8")
    brief_source = CONFIRMED_PROJECT_BRIEF_PATH.read_text(encoding="utf-8")
    field_source = PROJECT_BRIEF_FIELDS_PATH.read_text(encoding="utf-8")
    proposal_source = CONFIRMED_PROPOSAL_PATH.read_text(encoding="utf-8")
    command_source = GREENFIELD_COMMAND_TEXT_PATH.read_text(encoding="utf-8")

    assert len(component_source.splitlines()) < 800
    assert len(brief_source.splitlines()) < 800
    assert "from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import" in proposal_source
    assert "from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote" in proposal_source
    for moved in ("def confirmed_project_brief", "def _brief_clause"):
        assert moved not in component_source
        assert moved in brief_source
    for moved in ("def brief_option", "def checkpoint"):
        assert moved not in component_source
        assert moved in field_source
    assert "greenfield_project_brief_fields import brief_option as _brief_option" in brief_source
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
    assert "greenfield_domain_term_index import label_terms" in profile_source
    assert 're.findall(r"[A-Za-z0-9-]+"' not in profile_source
    assert (
        contract_profiles._object_phrase("The Primary source-backed_review record")
        == "source-backed review record"
    )


def test_document_contract_does_not_duplicate_downstream_preposition() -> None:
    contract = contract_profiles.document_context_contract(
        label="Proof Ledger",
        state_label="proof record",
        context="lifecycle",
        previous_label="Review Workspace",
        next_label="",
    )

    assert "for for lifecycle" not in " ".join(str(value) for value in contract.values()).casefold()
    document_contract = contract_profiles.document_context_contract(
        label="Packet Intake Service",
        state_label="permit application packet",
        context="records applicant identity, required documents, uploaded files, and missing document blockers",
        previous_label="Intake Workspace",
        next_label="Completeness Check Service",
    )
    status_contract = contract_profiles.status_view_contract(
        label="Status View Service",
        state_label="permit application packet",
        context="shows submitted, blocked, stale, and completed status transitions",
        previous_label="Packet Intake Service",
        next_label="Release review",
    )

    for contract in (document_contract, status_contract):
        proof_text = " ".join(contract["local_proof"])
        assert "Successful path evidence for" in proof_text
        assert "Blocked input evidence for" in proof_text
        assert "Replay evidence for" in proof_text

    status_contract_text = json.dumps(status_contract, sort_keys=True).casefold()
    assert "source freshness marker" in status_contract_text
    assert "source event markers" in status_contract_text
    assert "notification" not in status_contract_text


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
    assert "value_coercion import dedupe_by_key" in target_source
    assert "seen.add(marker)" not in target_source

    intake = {"label": "Intake Service"}
    review = {"label": "Review Service"}
    targets = repair_targets_from_spec_issues(
        ["component specs `Intake Service` and `Review Service` are too interchangeable"],
        rows_by_label={"Intake Service": intake, "Review Service": review},
        indexes_by_label={"Intake Service": 0, "Review Service": 1},
    )
    repeated_targets = repair_targets_from_spec_issues(
        [
            "component specs `Intake Service` and `Review Service` are too interchangeable",
            "component specs `Intake Service` and `Review Service` are too interchangeable",
        ],
        rows_by_label={"Intake Service": intake, "Review Service": review},
        indexes_by_label={"Intake Service": 0, "Review Service": 1},
    )

    assert [target.row for target in targets] == [intake, review]
    assert [target.sibling for target in targets] == [review, intake]
    assert [target.row for target in repeated_targets] == [intake, review]
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
    assert "greenfield_domain_term_index import label_terms" in term_windows_source
    assert "re.findall" not in term_windows_source
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
    assert "greenfield_text import visible_words" in differentiation_source
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
    assert "greenfield_text import visible_words" in contract_source
    assert "greenfield_component_term_index import ordered_domain_terms" in differentiation_source
    assert "greenfield_component_term_index import ordered_domain_terms" in terms_source
    assert "greenfield_domain_term_index import ordered_terms" in terms_source
    assert "greenfield_text import visible_words" in terms_source
    assert "greenfield_domain_term_index import ordered_terms" in fields_source
    assert "phrase_identity_terms as _phrase_identity_terms" in semantic_source
    assert "normalize_domain_token" not in terms_source
    assert "normalize_domain_token" not in fields_source
    assert "for raw in re.findall" not in terms_source
    assert 're.findall(r"[a-z0-9]+", lowered)' not in terms_source
    assert "for raw in re.findall" not in fields_source
    assert 're.findall(r"[a-z0-9]+"' not in differentiation_source
    assert "re.findall(r\"[A-Za-z][A-Za-z'-]*\"" not in fields_source
    assert "def _word_set" not in contract_source
    assert "re.findall(r\"[a-z0-9][a-z0-9'-]*\"" not in contract_source
    assert "re.findall(r\"\\b(?:draft|submitted|sent|received|accepted" not in contract_source
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
    assert clean_artifact_phrase("participant submits intake package") == "intake package"
    assert clean_artifact_phrase("operator approves safety guardrails") == "safety guardrails"
    assert clean_artifact_phrase("user adds protocol") == "protocol"
    assert clean_artifact_phrase("individual user adds protocol") == "protocol"
    assert clean_artifact_phrase("representative user protocol") == "protocol"
    assert clean_artifact_phrase("running protocol") == "running protocol"
    assert clean_artifact_phrase("dashboard visibly updates web/ui surface") == "web/ui surface state"
    assert clean_artifact_phrase("presents approval packet as the visible result to permit clerks") == "approval packet"
    assert clean_artifact_phrase("descriptions mechanism") == "descriptions"
    assert clean_artifact_phrase("metric moved usage protocol") == "usage protocol metric"
    assert clean_artifact_phrase("metric changed usage protocol") == "usage protocol metric"
    assert clean_artifact_phrase("pass or block outcomes") == "pass or block outcomes"
    assert clean_artifact_phrase("value relevant condition") == "relevant condition"
    assert clean_artifact_phrase("body composition data such") == "body composition data"
    assert clean_artifact_phrase("combines reference ranges") == "reference ranges"
    assert clean_artifact_phrase("hand extracted evidence into assessment") == "extracted evidence"
    assert clean_artifact_phrase("hand hygiene record") == "hand hygiene record"
    assert clean_artifact_phrase("home cook pick recipe") == ""
    assert clean_artifact_phrase("runs step sequence until") == "step sequence"
    assert clean_artifact_phrase("sequence until cooking reach") == ""
    assert clean_artifact_phrase("recipe move readiness") == "recipe readiness"
    assert clean_artifact_phrase("cooking reach finished state") == "finished state"
    assert clean_artifact_phrase("gate story name result") == ""
    assert visible_words("blocked-state update") == ("blocked", "state", "update")
    assert component_contract._state_terms_from_context(
        "submitted draft was blocked-state, ready, recovered, and ready again"
    ) == ("submitted", "draft", "blocked", "ready", "recovered")
    assert contract_differentiation._trigger_hits(("status", "window"), "Status-window proof") == 2
    assert status_only_artifact_fragment("blocked update")
    assert not status_only_artifact_fragment("blocked-state update")
    assert status_only_artifact_fragment("gate story name result")
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
    suggested_adjustment = contract_focus(
        object_list="suggested adjustment",
        action_terms=("suggest",),
        fallback="adjustment",
        role="output",
        contract_terms=("adjustment",),
    )
    assert "suggestion" not in suggested_adjustment.casefold()
    assert "recommendation" in suggested_adjustment.casefold()
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
    assert literal_label_terms("Source-backed_review Status Windows Service", noise_terms={"service"}) == [
        "source-backed_review",
        "status",
        "window",
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
    assert literal_label_compounds("Source-backed_review Status Windows Service", noise_terms={"service"}) == [
        "source-backed_review status",
        "status window",
    ]
    assert nearby_domain_terms(
        ["window"],
        "Reviewer opens status windows before window proofs capture source-backed audit trails.",
        noise_terms={"service"},
        window=3,
    ) == ["open", "window", "capture", "source-backed"]
    assert nearby_domain_terms(
        ["source-backed"],
        "Source-backed_review windows keep source-backed audit trails and status-window proof.",
        noise_terms={"service"},
        window=3,
    ) == ["source-backed_review", "window", "keep", "source-backed", "audit", "trail"]
    transition = state_transition_text(
        action_terms=("request", "review"),
        object_phrases=("request status", "reviewed note", "open handoff"),
        context_text="The request status can become visible, reviewed, or blocked.",
        anchor_terms=("status",),
    )
    assert transition == "reviewed, open, requested, received, validated, blocked, revised, ready-for-next-step"
    action_transition = state_transition_text(
        action_terms=("run", "pick", "reach"),
        object_phrases=("step sequence", "recipe readiness"),
    )
    assert "runed" not in action_transition
    assert "run" in action_transition
    assert "picked" in action_transition
    assert "reached" in action_transition


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
    assert "Successful path evidence for Planning Engine" in spec
    assert "reaches the visible result" not in spec
    assert "example explains" not in spec
    assert "stops before a trusted result" in spec


def test_greenfield_component_spec_renderer_normalizes_boundary_component_label_casing() -> None:
    spec = build_narrative_component_spec(
        component_id="decision-service",
        label="Decision Service",
        path="src/example/decision_service.py",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract={
            "owned_state": "decision record, blocked reason, and audit marker",
            "accepted_inputs": "retention rules, consent state, and protected record reference",
            "produced_outputs": "blocked deletion decision and lifecycle status",
            "states_or_transitions": "received, checked, blocked, accepted, and reviewed",
            "upstream_truth": "Protected Record Reference Store ownership",
            "downstream_consumers": "Audit and Review lifecycle View",
            "outside_boundary": "adjacent component state, original input facts, and upstream source truth",
            "local_proof": ["Replay one blocked decision with the rule and lifecycle marker visible."],
            "unique_failure": "blocked deletion decision loses its retention rule explanation",
        },
    )

    assert "Audit and Review Lifecycle View can consume" in spec
    assert "Audit and Review lifecycle View can consume" not in spec
    assert generated_public_copy_issues("Registry component spec `Decision Service`", spec) == ()


def test_greenfield_component_spec_renderer_preserves_explicit_transition_terms() -> None:
    spec = build_narrative_component_spec(
        component_id="status-view-service",
        label="Status View Service",
        path="src/example/status_view_service.py",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-004",),
        component_contract={
            "owned_state": "status timeline, current owner, transition history, blocked indicators, and audit trail",
            "accepted_inputs": "status timeline input, prior state, authorized actor, and validation context",
            "produced_outputs": "role-appropriate status view, current owner, and transition-validation display",
            "states_or_transitions": (
                "Draft, sent, received, accepted, declined, more-info-requested, scheduled, "
                "completed, blocked, stale, corrected, handed-off"
            ),
            "upstream_truth": "Lifecycle Tracking Service ownership",
            "downstream_consumers": "Release review",
            "outside_boundary": "adjacent component state, original input facts, and upstream source truth",
            "local_proof": ["Replay one status view with actor, input facts, status, and explanation still aligned."],
            "unique_failure": "Status View Service can mislead users if status history is stale or missing.",
        },
    )

    lowered = spec.casefold()
    for transition in ("sent", "received", "accepted", "declined", "scheduled", "completed"):
        assert transition in lowered
    assert "should make accepted, blocked, corrected, completed, and handed-off states explicit" not in spec


def test_component_semantic_contract_preserves_local_proof_boundary_obligations() -> None:
    proposal = {
        "intent": {
            "state_object": "A request handoff record tracks subject identity and uploaded request context.",
            "first_path": (
                "A coordinator creates a draft request, attaches subject identity and required request context, "
                "validates uploaded documents, and sends the packet to a destination team."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when missing documentation blocks submission, uploaded context stays attached "
                "to the correct request, unauthorized users cannot view or mutate request context, and status history "
                "is traceable to source events."
            ),
        }
    }
    row = {
        "label": "Document and Context Handling Surface",
        "source_system_description": (
            "creates request packets, attaches subject identity, validates uploaded documents, blocks missing "
            "required documentation, records request context provenance, protects sensitive request materials, "
            "and hands context into request lifecycle tracking"
        ),
    }

    contract = component_contract.build_component_contract(
        row,
        proposal=proposal,
        previous_label="Recipient Matching Surface",
        next_label="Request Lifecycle Tracking Service",
    )
    spec = build_component_spec(
        component_id="document-context-handling-surface",
        label="Document and Context Handling Surface",
        path="src/request_handoff/document_context.py",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract=contract,
    )

    assert "unauthorized users cannot view or mutate request context" in " ".join(contract["local_proof"]).casefold()
    assert "1 succeeds when" not in " ".join(contract["local_proof"]).casefold()
    assert "unauthorized users cannot view or mutate request context" in spec.casefold()
    assert "1 succeeds when" not in spec.casefold()
    assert rendered_component_spec_quality_issues({"Document and Context Handling Surface": spec}, project_title="Request Handoff Workspace") == []


def test_complete_profile_component_contract_rebuilds_to_preserve_semantic_proof_boundary() -> None:
    proposal = {
        "intent": {
            "state_object": "A request handoff record tracks subject identity and uploaded request context.",
            "first_path": (
                "A coordinator creates a draft request, attaches subject identity and required request context, "
                "validates uploaded documents, and sends the packet to a destination team."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when missing documentation blocks submission, uploaded context stays attached "
                "to the correct request, unauthorized users cannot view or mutate request context, and status history "
                "is traceable to source events."
            ),
        }
    }
    row = {
        "label": "Document and Context Handling Surface",
        "source_system_description": (
            "creates request packets, attaches subject identity, validates uploaded documents, blocks missing "
            "required documentation, records request context provenance, protects sensitive request materials, "
            "and hands context into request lifecycle tracking"
        ),
        "component_contract": {
            "owned_state": "request context, uploaded documents, subject identity, and packet attachment state",
            "accepted_inputs": "request packet, subject identity, uploaded documents, and coordinator context",
            "produced_outputs": "attached request context and blocked missing-document state",
            "states_or_transitions": "draft, attached, validated, blocked, and sent",
            "upstream_truth": "recipient matching surface ownership",
            "downstream_consumers": "request lifecycle tracking service",
            "outside_boundary": "destination-team lifecycle state and reviewer decision ownership",
            "local_proof": ["Replay one document attachment with packet, subject identity, and blocked state aligned."],
            "unique_failure": "Request context can separate from the packet or bypass required document checks.",
        },
    }

    contract = component_contract.ensure_component_contract(
        row,
        proposal=proposal,
        previous_label="Recipient Matching Surface",
        next_label="Request Lifecycle Tracking Service",
    )

    assert "unauthorized users cannot view or mutate request context" in " ".join(contract["local_proof"]).casefold()
    assert "1 succeeds when" not in " ".join(contract["local_proof"]).casefold()


def test_greenfield_component_spec_renderer_collapses_adjacent_duplicate_terms() -> None:
    spec = build_narrative_component_spec(
        component_id="quote-review-handoff",
        label="Quote Review Handoff Preserves Risk Notes, Follow Up Status, and Coordinator Decision",
        path="src/example/quote_review_handoff.py",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract={
            "owned_state": "risk notes, follow-up status, and coordinator decision decision",
            "accepted_inputs": "quote assumptions, roof uncertainty, and homeowner handoff context",
            "produced_outputs": "coordinator decision decision and review-ready quote status",
            "states_or_transitions": "flagged, reviewed, decided, and handed off",
            "upstream_truth": "Solar Fit Estimator Service",
            "downstream_consumers": "Coordinator Review Queue",
            "outside_boundary": "utility tariffs, roof imagery, and financing approval",
            "local_proof": ["Replay one quote handoff with risk notes and coordinator decision visible."],
            "unique_failure": "coordinator decision decision loses the risk note explanation",
        },
    )

    assert "decision decision" not in spec.casefold()
    assert generated_public_copy_issues(
        "Registry component spec `Quote Review Handoff Preserves Risk Notes, Follow Up Status, and Coordinator Decision`",
        spec,
    ) == ()


def test_greenfield_component_spec_renderer_uses_neutral_implementation_anchor() -> None:
    spec = build_narrative_component_spec(
        component_id="review-workspace",
        label="Review Workspace",
        path="src/example/review_workspace",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-003",),
        implementation_handoff={
            "workstream_id": "B-003",
            "workstream_title": "Keep Consequence Record Clear After Review Workspace Changes It",
            "first_slice": "When Review Workspace receives missing or invalid input, keep the result reviewable.",
            "release_selector": "0.0.1",
            "wave_label": "Review state and evidence boundary",
        },
        component_contract={
            "owned_state": "user-facing confirmation, review note, and failure reason ledger",
            "accepted_inputs": "profile choice, missing input, and correction context",
            "produced_outputs": "user-facing confirmation, review note, blocked-state detail, and next-step context",
            "states_or_transitions": "accepted, blocked, corrected, completed, and handed-off",
            "upstream_truth": "Intake Register Service",
            "downstream_consumers": "Proof Ledger",
            "outside_boundary": "adjacent component state, original input facts, and broader rollout decisions",
            "local_proof": [
                "Successful path evidence for Review Workspace: user-facing confirmation, required inputs, visible result, and reviewer explanation.",
                "Blocked input evidence for Review Workspace: missing or malformed input, stops before a trusted result, and recovery explanation.",
                "Replay evidence for Review Workspace: actor, input facts, status, and explanation.",
            ],
            "unique_failure": "Review Workspace can mislead users if user-facing confirmation is missing or stale.",
        },
    )

    assert "Use B-003" not in spec
    assert "Implementation anchor for Review Workspace: B-003" in spec
    assert generated_public_copy_issues("Registry component spec `Review Workspace`", spec) == ()


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


def test_greenfield_component_proof_rows_collapse_repeated_result_phrase() -> None:
    rows = proof_rows(
        label="Release Guardrail Service",
        object_list="result result, known limit, recovery condition",
        critical="result result",
        input_focus="known limit",
        output_focus="result result, recovery condition",
        sibling_label="Evidence Log Service",
        sibling_focus="evidence log state",
    )
    text = " ".join(rows).casefold()

    assert "result result" not in text
    assert "trusted result" in text


def test_greenfield_component_output_text_collapse_repeated_result_phrase() -> None:
    text = produced_outputs_text("decision ledger, result result, state update")

    assert "result result" not in text.casefold()
    assert "decision ledger" in text


def test_greenfield_component_phrase_cleaner_keeps_status_modifiers_attached_to_carrier() -> None:
    assert clean_artifact_phrase("lifecycle fixture live final") == "fixture lifecycle state"
    assert clean_artifact_phrase("live final state") == "final status"
    assert clean_artifact_phrase("match move state") == "match lifecycle state"
    assert clean_artifact_phrase("decide next match intake") == "match intake"
    assert clean_artifact_phrase("correction history match data") == "match data correction history"
    assert clean_artifact_phrase("history match event") == "match event history"
    assert clean_artifact_phrase("history match notification channel") == "match notification channel history"
    assert clean_artifact_phrase("match record command") == "match record"
    assert clean_artifact_phrase("live match status proposal") == "live match status"
    assert clean_artifact_phrase("timeline live") == "live timeline"
    assert clean_artifact_phrase("result final") == "final result"
    assert clean_artifact_phrase("settling finished result remain") == "finished result"
    assert clean_artifact_phrase("review readiness") == "review readiness"
    assert clean_artifact_phrase("visible blockers") == "visible blockers"
    assert clean_artifact_phrase("prior runs viewable") != "viewable state"
    assert singularize_last_word("input matches") == "input match"
    assert singularize_last_word("review boxes") == "review box"
    assert generated_public_copy_issues("sample", "The catalog owns the entities records attach to.") == (
        "sample leaked malformed relation phrase",
    )


def test_greenfield_owned_state_enrichment_cleans_io_clauses_before_lifting() -> None:
    enriched = enrich_owned_state_from_io(
        "parameter control state",
        {
            "accepted_inputs": (
                "Barrier width and particle energy choices, enforces bounds, "
                "and keeps unit conversions visible"
            ),
            "produced_outputs": (
                "checks the learner explanation for required assumptions before producing an export, "
                "misconception prompt result"
            ),
        },
        noise_terms={"state"},
    ).casefold()

    assert "barrier width and particle energy choices" in enriched
    assert "misconception prompt result" in enriched
    assert "checks the learner explanation" not in enriched
    assert "enforces bounds" not in enriched
    assert "keeps unit conversions visible" not in enriched


def test_greenfield_narrative_component_spec_avoids_relation_tail_and_status_clip() -> None:
    contract = {
        "owned_state": "Lifecycle fixture live final, live final result, reference entity record.",
        "accepted_inputs": "Lifecycle fixture live final input, prior state, validation context.",
        "produced_outputs": "Lifecycle fixture live final result, state update, blocked-state detail.",
        "states_or_transitions": "open, scheduled, live, final, blocked, ready-for-next-step",
        "outside_boundary": "adjacent component state, upstream source truth, release approval.",
        "local_proof": [
            "Successful path evidence for Reference Service: live final result, required inputs, visible result, and reviewer explanation.",
            "Blocked input evidence for Reference Service: missing or malformed input, stops before a trusted result, and recovery explanation.",
            "Replay evidence for Reference Service: actor, input facts, status, explanation, and proof trail.",
        ],
        "upstream_truth": "Accepted first-path input.",
        "downstream_consumers": "Release review.",
        "unique_failure": "Reference Service can mislead users if live final result is missing or stale.",
    }

    spec = build_component_spec(
        component_id="reference-service",
        label="Reference Service",
        path="src/example/reference_service",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility="the entities records attach to",
        component_contract=contract,
    )
    issues = greenfield_rendered_package_quality_issues(
        SimpleNamespace(
            proposal={},
            rendered_component_specs={"Reference Service": spec},
        )
    )

    assert "Accepted intent centers Reference Service on the stated relationship" in spec
    assert "the entities records attach to." not in spec
    assert not [issue for issue in issues if "clipped or dangling phrase ending" in issue]


def test_decision_component_specs_do_not_repeat_generic_opening_sentence() -> None:
    specs: dict[str, str] = {}
    for label in ("Recipe Decision Service", "Safety Decision Service", "Recovery Decision Service"):
        specs[label] = build_narrative_component_spec(
            component_id=label.casefold().replace(" ", "-"),
            label=label,
            path=f"src/example/{label.casefold().replace(' ', '_')}",
            kind="service",
            status="planned",
            sources=("user_intent",),
            workstreams=("B-002",),
            diagrams=("D-002",),
            responsibility="turns prepared evidence into a decision with rationale and blocked-state detail",
            component_contract={
                "owned_state": f"{label} state, rationale, blocked-state detail, and review evidence",
                "accepted_inputs": "prepared evidence, prior state, authorized actor, and validation context",
                "produced_outputs": "decision result, rationale, and blocked-state detail",
                "states_or_transitions": "open, evaluated, blocked, revised, and ready-for-next-step",
                "outside_boundary": "upstream source truth and final release approval",
                "local_proof": [
                    f"Successful path evidence for {label}: decision result, visible result, and persisted explanation.",
                    f"Blocked input evidence for {label}: invalid input, no misleading result, and recovery explanation.",
                    f"Replay evidence for {label}: actor, input facts, decision result, rationale, and proof trail.",
                ],
                "upstream_truth": "Prepared evidence",
                "downstream_consumers": "Release review",
                "unique_failure": f"{label} can mislead users if rationale is missing or stale.",
            },
        )

    issues = greenfield_rendered_package_quality_issues(
        SimpleNamespace(
            proposal={},
            rendered_component_specs=specs,
        )
    )
    rendered = "\n".join(specs.values())

    assert "The spec should stay focused on" not in rendered
    assert "repeats a noncanonical sentence" not in "\n".join(issues)


def test_component_specs_use_label_role_before_generic_decision_terms() -> None:
    specs = {
        label: build_narrative_component_spec(
            component_id=label.casefold().replace(" ", "-"),
            label=label,
            path=f"src/example/{label.casefold().replace(' ', '_')}",
            kind="service",
            status="planned",
            sources=("user_intent",),
            workstreams=("B-002",),
            diagrams=("D-002",),
            responsibility="keeps local state, rationale, blocked-state detail, and handoff proof reviewable",
            component_contract={
                "owned_state": f"{label} state, required inputs, blocked-case evidence, and handoff proof",
                "accepted_inputs": "accepted input facts, prior state, authorized actor, and validation context",
                "produced_outputs": "result, rationale, blocked-state detail, and next-step handoff",
                "states_or_transitions": (
                    "staged, selected state, prompted, requested state, received state, accepted state, "
                    "applied, checked, completed state, created, and decided"
                ),
                "outside_boundary": "upstream source truth and final release approval",
                "local_proof": [
                    f"Successful path evidence for {label}: local state, required inputs, visible result, and reviewer explanation.",
                    f"Blocked input evidence for {label}: invalid input, no misleading result, and recovery explanation.",
                    f"Replay evidence for {label}: actor, input facts, status, and proof trail.",
                ],
                "upstream_truth": "Accepted input context",
                "downstream_consumers": "Release review",
                "unique_failure": f"{label} can mislead users if local state is missing or stale.",
            },
        )
        for label in (
            "Ingredient Readiness Service",
            "Cooking Run Orchestration Service",
            "Safety Stop and Recovery Service",
        )
    }
    rendered = "\n".join(specs.values())
    issues = greenfield_rendered_package_quality_issues(
        SimpleNamespace(
            proposal={},
            rendered_component_specs=specs,
        )
    )

    assert "Ingredient Readiness Service checks whether the next product step has the conditions it needs" in rendered
    assert "Cooking Run Orchestration Service coordinates the ordered work that moves the first path forward" in rendered
    assert "Safety Stop and Recovery Service protects the first path when an unsafe, invalid, or blocked condition appears" in rendered
    assert "turns prepared evidence into a product outcome" not in rendered
    assert "the important lifecycle is staged, selected state, prompted" not in rendered
    assert "The lifecycle for Ingredient Readiness Service should make accepted, blocked, corrected, completed, and handed-off states explicit" in rendered
    assert "repeats a noncanonical sentence" not in "\n".join(issues)


def test_component_contract_focus_does_not_clip_confirmed_first_path_tail() -> None:
    contract = component_contract.ensure_component_contract(
        {
            "label": "Session Telemetry State Service",
            "kind": "service",
            "source_system_description": (
                "owns session telemetry state that records the live cook state, required inputs, "
                "blocked-case evidence links, and handoff boundaries for the confirmed first path"
            ),
        },
        proposal={"title": "Example Product", "state_object": "Cook Session"},
        previous_label="Safety Supervisor Service",
        next_label="",
    )
    rendered = " ".join(str(value) for value in contract.values())

    assert "handoff boundaries f" not in rendered
    assert "handoff boundaries" in rendered


def test_component_contract_artifact_slots_nominalize_validation_action_clauses() -> None:
    assert noun_slot_artifact_phrase("cover successful completion") == "successful completion evidence"
    assert noun_slot_artifact_phrase("cover successful completion evidence") == "successful completion evidence"
    normalized = normalize_contract(
        {
            "owned_state": "cover successful completion evidence",
            "accepted_inputs": "cover successful completion",
            "produced_outputs": "cover successful completion evidence, completion builder",
            "states_or_transitions": "validated state, blocked state",
            "outside_boundary": "adjacent state",
            "local_proof": ["Successful path evidence: cover successful completion, required inputs."],
            "upstream_truth": "upstream state",
            "downstream_consumers": "release review",
            "unique_failure": "missing successful completion evidence",
        }
    )
    assert "cover successful" not in " ".join(str(value) for value in normalized.values()).casefold()
    assert "validated state" in normalized["states_or_transitions"].casefold()
    assert (
        contract_focus(
            object_list="cover successful completion",
            action_terms=("record",),
            fallback="completion record",
            role="output",
        )
        == "validated successful completion evidence state, correction marker, and replayable change evidence"
    )


def test_component_specs_suppress_generated_contract_boilerplate_as_accepted_intent() -> None:
    spec = build_narrative_component_spec(
        component_id="session-state",
        label="Session State Service",
        path="src/example/session_state",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility=(
            "owns session state, required inputs, blocked-case evidence links, "
            "and handoff boundaries for the confirmed first path"
        ),
        component_contract={
            "owned_state": "session state, blocker, recovery note, and review evidence",
            "accepted_inputs": "accepted input facts, prior state, authorized actor, and validation context",
            "produced_outputs": "state update, blocked-state explanation, and next-step context",
            "states_or_transitions": "accepted, blocked, corrected, completed, and handed-off",
            "outside_boundary": "upstream source truth and final release approval",
            "local_proof": [
                "Successful path evidence for Session State Service: state update, visible result, and persisted explanation.",
                "Blocked input evidence for Session State Service: invalid input, no misleading result, and recovery explanation.",
                "Replay evidence for Session State Service: actor, input facts, status, and proof trail.",
            ],
            "upstream_truth": "Accepted input context",
            "downstream_consumers": "Release review",
            "unique_failure": "Session State Service can mislead users if state is missing or stale.",
        },
    )

    assert "Accepted intent centers Session State Service on" not in spec
    assert "blocked-case evidence links" not in spec
    assert "handoff boundaries for the confirmed first path" not in spec


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


def test_rendered_component_spec_quality_rejects_visible_copy_slop() -> None:
    spec = """
# Usage Logging Service

## Component Role

Usage Logging Service is the place where the product turns prepared evidence into an explained outcome.
It should explain how dosage suggestion, user adds peptide, and relevant condition is calculated.
The summary keeps schedule reviewable while keeping protocol status visible.

### Accepts

Accepted input context.
"""

    issues = rendered_component_spec_quality_issues({"Usage Logging Service": spec}, project_title="PeptideTrack")

    assert any("generic outcome boilerplate" in issue for issue in issues)
    assert any("accepted-input placeholder" in issue for issue in issues)
    assert any("repeated keeping summary" in issue for issue in issues)
    assert any("treats action user adds peptide as a calculated object" in issue for issue in issues)


def test_narrative_component_spec_splits_keeping_summary_without_repetition() -> None:
    spec = build_narrative_component_spec(
        component_id="review-evidence-panel",
        label="Review Evidence Panel",
        path="src/match/review_evidence_panel",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        responsibility="keeps corrections and finalization while keeping required inputs, blockers, and proof evidence clear",
        component_contract={
            "owned_state": "public match summary correction final status, correction history, and replay evidence",
            "accepted_inputs": "score event correction, source actor, prior state, and validation context",
            "produced_outputs": "public match summary correction final status, correction history, and review outcome",
            "states_or_transitions": "scheduled, corrected, reviewed, final status, and ready-for-next-step",
            "outside_boundary": "score entry ownership and release approval",
            "local_proof": [
                "Successful path evidence for Review Evidence Panel: correction history, visible result, and persisted explanation.",
                "Blocked input evidence for Review Evidence Panel: invalid correction input, no misleading result, and recovery explanation.",
                "Replay evidence for Review Evidence Panel: actor, input facts, status, explanation, and proof trail.",
            ],
            "upstream_truth": "Score Event Ledger",
            "downstream_consumers": "release review",
            "unique_failure": "Review Evidence Panel can mislead users if correction history is missing, stale, or shown without enough explanation to recover.",
        },
    )
    issues = rendered_component_spec_quality_issues({"Review Evidence Panel": spec}, project_title="Community Match Tracker")

    assert "while keeping" not in spec
    assert "It keeps inputs, blockers, and proof evidence clear." in spec
    assert "Evidence for review evidence" not in spec
    assert "Review Evidence Panel preserves the proof that makes the first release reviewable." in spec
    assert "- Keep score entry ownership" not in spec
    assert "Review Evidence Panel keeps score entry ownership" in spec
    assert not any("repeated keeping summary" in issue for issue in issues)


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


def test_greenfield_quality_gate_allows_block_record_component_labels_in_proof_slots() -> None:
    rows = proof_rows(
        label="Block Record Service",
        object_list="block record, unit truth block, registry state",
        critical="block record",
        input_focus="required block record input",
        output_focus="block record result, registry state, and review evidence",
        sibling_label="Activity Log Service",
        sibling_focus="activity log state",
    )

    issues = public_prose_quality_issues(
        {
            "components": [
                {
                    "validation": rows,
                    "component_contract": {"local_proof": rows},
                }
            ],
            "semantic_model": {"components": [{"proof_obligations": rows}]},
        }
    )

    assert not issues
    assert rows[0].startswith("Successful path evidence for Block Record Service:")
    assert "Block Record Service shows" not in " ".join(rows)


def test_greenfield_truth_unit_context_renders_artifact_record_not_word_soup() -> None:
    text = (
        "The core unit of truth is a Block: a named, mapped planting of one grape variety. "
        "Each block carries its vines and activity history."
    )

    phrases = context_object_phrases(
        text,
        label_terms=("block",),
        description_terms=("block", "registry", "record"),
    )
    compounds = context_anchor_compounds(text, anchor_terms=("block", "registry", "record"))

    assert "block record" in phrases
    assert "block record" in compounds
    assert "unit truth block" not in phrases
    assert "unit truth block" not in compounds


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
