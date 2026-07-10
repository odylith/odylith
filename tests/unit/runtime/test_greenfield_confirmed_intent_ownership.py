from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import completed_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import has_progression_or_outcome
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_document import _looks_like_bare_title
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent


ROOT = Path(__file__).resolve().parents[3]
CONFIRMED_INTENT_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_completion.py"
)
CONFIRMED_INTENT_CONTEXT_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_context_completion.py"
)
CONFIRMED_TITLE_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_title_completion.py"
)
CONFIRMED_ACTOR_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_actor_completion.py"
)
CONFIRMED_SYSTEM_ROWS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_rows.py"
CONFIRMED_INTENT_DOCUMENT_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_document.py"
)
CONFIRMED_SYSTEM_COMPLETION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_system_completion.py"
)
CONFIRMED_INTENT_VALIDATION_PATH = (
    ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_validation.py"
)
CONFIRMED_INTENT_PARSER_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py"


def test_confirmed_intent_actor_completion_stays_in_dedicated_owner() -> None:
    parent_source = CONFIRMED_INTENT_COMPLETION_PATH.read_text(encoding="utf-8")
    actor_source = CONFIRMED_ACTOR_COMPLETION_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 1200
    assert "def _completed_actor_rows" not in parent_source
    assert "def _derived_actor_labels" not in parent_source
    assert "completed_actor_rows as _completed_actor_rows" in parent_source
    assert "def completed_actor_rows" in actor_source
    assert "accepted_actor_label" in actor_source


def test_confirmed_intent_system_rows_stay_in_dedicated_owner() -> None:
    parser_path = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py"
    parser_source = parser_path.read_text(encoding="utf-8")
    document_source = CONFIRMED_INTENT_DOCUMENT_PATH.read_text(encoding="utf-8")
    system_source = CONFIRMED_SYSTEM_ROWS_PATH.read_text(encoding="utf-8")
    validation_source = CONFIRMED_INTENT_VALIDATION_PATH.read_text(encoding="utf-8")

    assert len(parser_source.splitlines()) < 800
    assert len(document_source.splitlines()) < 800
    assert "greenfield_confirmed_intent_document import" in parser_source
    assert "def product_context_paragraphs" in document_source
    assert "def _role_or_system_rows" not in parser_source
    assert "def _system_sentence_row" not in parser_source
    assert "def _validate_confirmed_intent" not in parser_source
    assert "def _qualitative_intent_gaps" not in parser_source
    assert "def _semantic_terms" not in parser_source
    assert "def _semantic_terms" not in system_source
    assert "role_or_system_rows as _role_or_system_rows" in parser_source
    assert "combined_system_rows as _combined_system_rows" in parser_source
    assert "contains_generic_system_scaffold as _contains_generic_system_scaffold" in parser_source
    assert "def combined_system_rows" in system_source
    assert "validate_confirmed_intent as _validate_confirmed_intent" in parser_source
    assert "def role_or_system_rows" in system_source
    assert "def internal_system_rows" in system_source
    assert "looks_like_finite_action" in system_source
    assert "def validate_confirmed_intent" in validation_source
    assert "def _qualitative_intent_gaps" in validation_source
    assert "def _semantic_terms" not in validation_source
    assert "semantic_terms" in validation_source
    assert "def has_progression_or_outcome" in validation_source


def test_confirmed_intent_progression_markers_use_shared_text_owner() -> None:
    validation_source = CONFIRMED_INTENT_VALIDATION_PATH.read_text(encoding="utf-8")

    assert "greenfield_text import progression_marker_count" in validation_source
    assert "len(re.findall" not in validation_source
    assert has_progression_or_outcome("The review record starts as draft and ends as accepted.")
    assert has_progression_or_outcome("The review record captures intake, evidence; decision: archive.")


def test_confirmed_intent_system_completion_stays_in_dedicated_owner() -> None:
    parent_source = CONFIRMED_INTENT_COMPLETION_PATH.read_text(encoding="utf-8")
    completion_source = CONFIRMED_SYSTEM_COMPLETION_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 800
    assert "completed_system_rows as _completed_system_rows" in parent_source
    assert "system_labels as _system_labels" in parent_source
    assert "state_label as _state_label" in parent_source
    for moved in (
        "def _system_row",
        "def _derived_system_rows",
        "def _clean_system_description",
        "def _system_label_head",
        "def _compact_system_label",
        "def _best_context_clause",
        "_SYSTEM_SUFFIXES",
    ):
        assert moved not in parent_source
        assert moved in completion_source
    assert "def completed_system_rows" in completion_source
    assert "def system_labels" in completion_source
    assert "def state_label" in completion_source


def test_confirmed_intent_context_completion_stays_in_dedicated_owner() -> None:
    parent_source = CONFIRMED_INTENT_COMPLETION_PATH.read_text(encoding="utf-8")
    context_source = CONFIRMED_INTENT_CONTEXT_COMPLETION_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 800
    assert "complete_external_boundary as _complete_external_boundary" in parent_source
    assert "normalize_confirmed_actor_context as _normalize_confirmed_actor_context" in parent_source
    assert "def _complete_external_boundary" not in parent_source
    assert "def _normalize_confirmed_actor_context" not in parent_source
    assert "def complete_external_boundary" in context_source
    assert "def normalize_confirmed_actor_context" in context_source


def test_confirmed_intent_completion_title_tokens_use_shared_label_terms() -> None:
    parent_source = CONFIRMED_INTENT_COMPLETION_PATH.read_text(encoding="utf-8")
    title_source = CONFIRMED_TITLE_COMPLETION_PATH.read_text(encoding="utf-8")

    assert "greenfield_confirmed_title_completion import derived_title as _derived_title" in parent_source
    assert "greenfield_domain_term_index import label_terms" in title_source
    assert 're.findall(r"[A-Za-z0-9]+", text)' not in parent_source
    assert 're.findall(r"[A-Za-z0-9]+", label)' not in parent_source
    assert 're.findall(r"[A-Za-z0-9]+", text)' not in title_source
    assert 're.findall(r"[A-Za-z0-9]+", label)' not in title_source
    assert label_terms("AI/ML Review Workspace") == ["AI", "ML", "Review", "Workspace"]

    intent = {
        "title": "A very long title that captures what users want because it follows many details",
        "product_story": (
            "Researchers need a source-backed AI/ML review workspace that keeps review evidence, "
            "reviewer decisions, model notes, and status-window proof clear enough for handoff and release review."
        ),
        "state_object": "AI/ML review record tracks source-backed findings, reviewer decisions, and status-window proof.",
        "first_path": (
            "Reviewer opens the AI/ML review workspace, records source-backed review evidence, compares findings, "
            "and sees status-window proof for the next decision."
        ),
        "proof_boundary": (
            "Release succeeds when the reviewer can inspect source-backed proof, compare review evidence, "
            "and see status-window readiness without broad automation."
        ),
        "internal_systems": ["AI/ML Review Workspace - records source-backed review status and proof windows."],
        "human_actors": ["Research reviewer - checks evidence quality and records review decisions."],
    }

    assert complete_confirmed_intent(intent)["title"] == "AI/ML Review Record Workspace"


def test_confirmed_actor_completion_role_candidates_use_shared_label_terms() -> None:
    actor_source = CONFIRMED_ACTOR_COMPLETION_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import label_terms as _label_terms" in actor_source
    assert 're.findall(r"[A-Za-z][A-Za-z/-]*", sentence)' not in actor_source
    assert label_terms("Source-backed reviewer") == ["Source-backed", "reviewer"]

    intent = {
        "title": "Source-backed Review Workspace",
        "product_story": "A source-backed reviewer compares AI/ML notes and keeps status-window proof clear.",
        "state_object": "Source-backed review record tracks AI/ML notes and status-window proof.",
        "first_path": (
            "Source-backed reviewer opens the AI/ML review workspace, records source-backed evidence, "
            "and sees status-window proof."
        ),
        "human_actors": [],
    }

    labels = [row.split(":", 1)[0] for row in completed_actor_rows(intent, title=intent["title"])]
    assert "Source-backed Reviewer" in labels


def test_confirmed_actor_completion_trims_preposition_and_action_led_role_fragments() -> None:
    runway_intent = {
        "title": "Airport Runway Maintenance Closure Readiness Tool",
        "product_story": (
            "Operations staff record pavement inspection findings, coordinate airline and tower constraints, "
            "preserve NOTAM evidence, track weather windows, and publish reopening readiness for duty manager review."
        ),
        "state_object": "Runway closure readiness record tracks pavement findings, constraints, evidence, and review status.",
        "first_path": (
            "Operations staff record pavement inspection findings. Operations staff coordinates airline and tower constraints. "
            "Operations staff preserves NOTAM evidence. Operations staff tracks weather windows. "
            "Operations staff publishes reopening readiness for duty manager review."
        ),
        "human_actors": [],
    }
    ai_eval_intent = {
        "title": "AI Evaluation Red Team Finding Board",
        "product_story": (
            "The board receives model behavior reports, links reproduction evidence, groups safety policy impacts, "
            "tracks mitigation owner signoff, and publishes model release readiness proof before deployment review."
        ),
        "state_object": "Finding record tracks model behavior, reproduction evidence, mitigation signoff, and readiness proof.",
        "first_path": (
            "An AI Evaluation Red Team Finding Board User can receive model behavior reports. Link reproduction evidence. "
            "Group safety policy impacts. Track mitigation owner signoff. Publish model release readiness proof before a deployment review."
        ),
        "human_actors": [],
    }

    runway_rows = completed_actor_rows(runway_intent, title=runway_intent["title"])
    ai_eval_rows = completed_actor_rows(ai_eval_intent, title=ai_eval_intent["title"])

    assert "Duty Manager: keeps the product outcome aligned" in " ".join(runway_rows)
    assert "For Duty Manager" not in " ".join(runway_rows)
    assert "Finding Board User: uses the product to receive model behavior reports" in " ".join(ai_eval_rows)
    assert "uses the product to AI Evaluation Red Team Finding Board User receives" not in " ".join(ai_eval_rows)
    assert "Mitigation Owner: uses the product to track mitigation owner signoff" in " ".join(ai_eval_rows)


def test_confirmed_system_completion_does_not_repeat_focus_words_in_fallback_labels() -> None:
    completed = complete_confirmed_intent(
        {
            "title": "Battery Materials Release Evidence Desk",
            "product_story": (
                "Battery materials program leads need one workspace to collect release evidence, compare safety "
                "constraints, preserve reviewer decisions, and publish manufacturing-readiness status."
            ),
            "state_object": (
                "Batch Release Evidence Record with precursor lot, cell chemistry, lab batch identifier, "
                "reviewer decision, manufacturing readiness status, and replay evidence."
            ),
            "first_path": (
                "Materials intake coordinator records one lab batch, safety reviewer checks blocking observations, "
                "and release owner publishes manufacturing-readiness status with replay evidence."
            ),
            "proof_boundary": (
                "First release proves one lab batch from intake to manufacturing-readiness status with replay proof."
            ),
            "human_actors": ["Materials intake coordinator", "Safety reviewer", "Release owner"],
            "internal_systems": [],
        }
    )
    rendered = json.dumps(completed["internal_systems"], sort_keys=True)

    assert "Evidence Evidence" not in rendered
    assert "Release Evidence Release" not in rendered
    assert "Battery Materials Release Evidence Log" in rendered
    assert "Battery Materials Release Evidence Guardrail" in rendered


def test_confirmed_intent_bare_title_uses_shared_label_terms() -> None:
    parser_source = CONFIRMED_INTENT_PARSER_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import label_terms as _label_terms" in parser_source
    assert "re.findall(r\"[A-Za-z0-9][A-Za-z0-9'-]*\", text)" not in parser_source
    assert label_terms("Source-backed Evidence Workspace") == ["Source-backed", "Evidence", "Workspace"]
    assert _looks_like_bare_title("Source-backed Evidence Workspace")
    assert _looks_like_bare_title("Reviewer needs status proof") is False


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
        """Shared Operations Review - Product Intent Confirmation

Product story
The workspace helps an operator find stale work items, understand why each item needs review, decide whether to keep or close it, and leave a traceable outcome for the next reviewer. The product connects item ingestion, evidence review, operator approval, and follow-up tracking so the operator and support reviewer can see what changed and why.

State object that changes through the first journey
A review record tracks imported items, evidence, operator approval, action state, and the next follow-up check.

First complete path the product should prove before broader scope
The user imports work history, reviews one stale item, approves a close-or-keep decision, records the outcome, and checks whether the next follow-up state changed as expected.

Human actors
- **Primary operator:** wants to reduce stale work without accidentally closing important items.
- **Support reviewer:** checks ambiguous follow-up attempts and user disputes.

External systems
- Work history export.
- External action portal or support inbox.

Internal product systems
- Work item ingestion - imports activity and normalizes item id, source, timestamp, status, and owner so review evidence starts from a consistent record.
- Stale-item detection - identifies likely stale items from repeated inactivity, status age, dependency state, and known workflow markers while keeping uncertainty visible.
- User review flow - explains evidence to the primary operator, captures keep-or-close approval, and prevents action without an explicit user decision.
- Follow-up tracker - records the attempted action, external response, support reviewer escalation, and follow-up status for the next cycle.

Critical assumptions
- Release 0.0.1 guides or records one review path; it does not claim universal automated remediation.

Ambiguities that would change the first path
- Whether work history import comes from a live connection or a file export.

Proof boundary
Release 0.0.1 succeeds when a reviewer can see the imported items, the stale-item evidence, the user approval, the action outcome, and the next follow-up check.
""",
        prompt="Draft a product-first greenfield proposal for a shared operations review workspace.",
    )

    encoded = json.dumps(intent)
    assert "**" not in encoded
    assert "Shared Operations Operator: wants to reduce stale work" in encoded
    assert "Primary operator" not in encoded
    assert "Support reviewer: checks ambiguous follow-up attempts" in encoded


def test_confirmed_intent_internal_systems_do_not_splice_related_path_fragments() -> None:
    intent = parse_confirmed_intent_text(
        """# Application Review

## Product Story
Application Review gives people a short guided review flow that captures the facts needed for a preliminary eligibility decision, evaluates them against configurable review rules, and returns an explainable result without pretending to be a final approval.

## State Object
An application review record tracks applicant identity, selected request type, declared facts, requested amount or scope, supporting details, rule evaluation results, decision reason-code, local blockers, and reviewer handoff evidence.

## First Complete Path
An applicant opens the product, selects a request type, enters declared facts, requested amount or scope, and basic identity details. They submit the application, the rules engine calculates review checks, and the product returns a plain-language result: likely eligible, conditionally eligible, or not yet eligible, with reason codes and next steps.

## Human Actors
- Applicant filling out intake and reading their decision.
- Reviewer reading eligible or conditional applications and following up.
- Administrator configuring review rules and thresholds.

## External Systems
- Identity verification provider.
- External verification provider is deferred from the first release.

## Internal Product Systems
- Intake and Application: captures request type, declared facts, amount or scope, identity details, validation blockers, and submission state.
- Qualification Rules Engine: calculates review checks, applies thresholds, records rule version, and blocks stale or missing inputs.
- Decision and Reason-code Service: produces the explainable result, reason codes, next steps, and handoff evidence.
- Reviewer Queue Service: shows submitted applications, decision status, blockers, and follow-up context.
- Rule/Threshold Store: owned by the administrator for policy rules, threshold versions, and change evidence.

## Critical Assumptions
- Release 0.0.1 is preliminary eligibility only, not final approval.
- External verification integrations are deferred until the manual review loop works.

## Ambiguities
- Exact eligibility thresholds need administrator configuration.

## Proof Boundary
Release 0.0.1 succeeds when one applicant can enter the required details, submit the application, receive an explainable preliminary eligibility result with reason codes, and leave a reviewable handoff for a reviewer without claiming final approval.
""",
        prompt="Create an application review product.",
    )

    joined = json.dumps(intent)
    assert "Related path:" not in joined
    assert "Runs it against" not in joined
    assert "declared facts" in joined
    systems = "\n".join(intent["internal_systems"])
    assert "Decision and Reason-code Service" in systems
    assert "produces the explainable result" in systems
    assert "Rule/Threshold Store" in systems
    assert "keeps rule/threshold state under the named owner" in systems


def test_confirmed_intent_parser_accepts_current_sectioned_confirmation_contract() -> None:
    intent = parse_confirmed_intent_text(
        """Product Intent Confirmation

Inventory Service Quality Tracker

Product story
A small operations team needs one place to see whether service inventory is ready for daily work. The product turns intake records, inspection notes, stock counts, and repair status into a clear readiness view so a coordinator can decide what can be assigned, what needs attention, and what should stay out of circulation.

State object
The state object is an inventory readiness record: item identity, current condition, availability, inspection history, open repair notes, assignment status, and reviewer decision.

First complete path
A coordinator imports a small item list, opens one item, records an inspection, marks one repair blocker, clears that blocker, and sees the item move from unavailable to ready with a traceable explanation.

Human actors
- Coordinator: reviews readiness and decides what can be used.
- Inspector: records condition and repair evidence.
- Operations reviewer: checks whether readiness claims are supported.

External systems
- CSV or spreadsheet exports from the current inventory system.
- Repair notes, inspection photos, and assignment records.

Internal product systems
- Inventory import and normalization: converts item lists into stable records with item identity, condition, source, and assignment context.
- Readiness state tracker: records availability, blockers, repair status, reviewer decision, and the state transitions that explain why an item is ready.
- Inspection and repair evidence log: captures inspection notes, repair evidence, blocker clearance, and reviewer-visible history.

Critical assumptions
- The first release is an internal operations tool.
- Imports can start from CSV before live integrations exist.

Ambiguities
- Whether item identity comes from barcode, SKU, asset tag, or manual entry.
- Whether repair evidence must include images in the first release.

Proof boundary
Release 0.0.1 is trusted only when one item can move through import, inspection, blocker, repair clearance, and ready decision with evidence that a reviewer can inspect. It must not claim live integrations, automatic repair diagnosis, or production-scale assignment planning yet.

Next step
Confirm: create the governed greenfield records from this accepted interpretation.
Edit: revise the product story, first path, actors, systems, assumptions, ambiguities, or proof boundary before writing records.
Reject: stop without writing records.
""",
        prompt="Draft a product-first greenfield proposal for an inventory service quality tracker.",
    )

    assert intent["state_object"].startswith("an inventory readiness record")
    assert str(intent["first_path"]).startswith("A coordinator imports a small item list")
    assert "Next step" not in str(intent["proof_boundary"])
    assert len(intent["internal_systems"]) == 3
