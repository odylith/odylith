from __future__ import annotations

from pathlib import Path

from odylith.runtime.common.mermaid_text import wrap_mermaid_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    CONFIRMED_INTENT_VALIDATION_STOPWORDS,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_item
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    capitalize_sentence_start_preserving_source_terms,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import inline_list_sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_restates_label_with_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import strip_dangling_tail
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_occurrences
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import system_component_name
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_text import sentence as diagram_sentence
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import gerund_action_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_text import (
    clean_markdown_sentence,
    clean_markdown_text,
    clip_text_at_word_boundary,
    word_occurrences as generic_word_occurrences,
)


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
CONFIRMED_TEXT_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_text.py"
GREENFIELD_TEXT_PATH = DOMAIN_INTELLIGENCE / "greenfield_text.py"


def test_confirmed_intent_list_text_coercion_stays_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    assert "def confirmed_text_values" in text_source
    assert clean_confirmed_text("runs the assimilation quality review review") == (
        "runs the assimilation quality review"
    )
    assert confirmed_text_values(" **Resident** confirms `booking` ") == [
        "Resident confirms booking"
    ]
    assert confirmed_text_values([" - visible bullet text ", "", "`Queue` status"]) == [
        "- visible bullet text",
        "Queue status",
    ]
    assert confirmed_text_values({"mapping": "is not a confirmed list row"}) == []

    for path in (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_actor_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_system_completion.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent_validation.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "def _strings" not in source
        assert "confirmed_text_values" in source


def test_state_object_label_handles_central_thing_tracking_language() -> None:
    label = domain_object_label(
        (
            "The central thing the product tracks is a person's comfort timeline: "
            "a sequence of dated entries with ratings, factors, actions, and derived trends."
        ),
        fallback="Pattern state",
    )

    assert label == "Person's Comfort Timeline"
    assert "Central Thing" not in label
    assert "Product" not in label
    assert domain_object_label(
        (
            "The central thing the product tracks is a person's neck-pain timeline: "
            "dated entries with pain levels, factors, actions, and derived trends."
        ),
        fallback="Pattern state",
    ) == "Person's Neck Pain Timeline"
    assert title_label("source-backed review record") == "Source-backed Review Record"
    assert title_label("high-risk case review") == "High-risk Case Review"
    assert title_label("GLP-1 medication journey") == "GLP-1 Medication Journey"
    assert title_label("revision-round management") == "Revision-round Management"
    assert title_label("scientific-quality reviewer") == "Scientific Quality Reviewer"
    assert title_label("titration-schedule model") == "Titration Schedule Model"
    assert capitalize_sentence_start_preserving_source_terms("mRNA Stability Batch stays reviewable") == (
        "mRNA Stability Batch stays reviewable"
    )
    assert capitalize_sentence_start_preserving_source_terms("workflow stays reviewable") == "Workflow stays reviewable"
    assert sentence_label("GLP-1 Companion") == "GLP-1 companion"
    assert sentence_label("AI/ML Review API") == "AI/ML review API"
    assert (
        sentence_label("School Support Teams Coordinating Student Accommodation Follow-Through need one reviewable workspace")
        == "school support teams coordinating student accommodation follow-through need one reviewable workspace"
    )
    assert sentence_label("Cryo-EM ReviewLedger evidence") == "Cryo-EM ReviewLedger evidence"
    assert focus_label("GLP-1 Companion — Medication Tracking App") == "GLP-1 Companion Medication Tracking"
    assert domain_object_label(
        (
            "The durable thing the product holds is a single user's medication journey: "
            "current medication, dose, schedule, injection history, weight readings, and side effects."
        ),
        fallback="Medication journey",
    ) == "Single User's Medication Journey"
    assert (
        domain_object_label(
            (
                "A live processing pipeline holding ordered streams of signal samples, "
                "each moving through a chain of stages."
            ),
            fallback="Pipeline state",
        )
        == "Live Processing Pipeline"
    )
    assert (
        domain_object_label(
            (
                "The product manages a cooking run, including selected recipe, staged ingredients, "
                "sensor readings, heat and timing state, operator prompts, safety stops, and final serve readiness."
            ),
            fallback="Cooking state",
        )
        == "Cooking Run"
    )
    assert state_detail_summary(
        (
            "The product manages a cooking run, including selected recipe, staged ingredients, "
            "sensor readings, heat and timing state, operator prompts, safety stops, and final serve readiness."
        ),
        state_label="Cooking Run",
    ).startswith("a cooking run, including selected recipe")
    assert (
        domain_object_label(
            (
                "The tutor stores a learner practice record, including prompt, selected answer, feedback, "
                "retry state, mastery flags, and review history."
            ),
            fallback="Practice State",
        )
        == "Learner Practice Record"
    )
    assert (
        domain_object_label(
            (
                "A lab session contains the selected experiment, particle properties, barrier shape, "
                "energy settings, solver settings, visualization state, measured outputs, notes, and saved results."
            ),
            fallback="Lab state",
        )
        == "Lab Session"
    )
    lab_detail = state_detail_summary(
        (
            "A lab session contains the selected experiment, particle properties, barrier shape, "
            "energy settings, solver settings, visualization state, measured outputs, notes, and saved results."
        ),
        state_label="Lab Session",
    )
    assert state_detail_restates_label_with_finite_action(
        lab_detail,
        state_label="Lab Session",
    )
    assert state_detail_summary(
        (
            "The tutor stores a learner practice record, including prompt, selected answer, feedback, "
            "retry state, mastery flags, and review history."
        ),
        state_label="Learner Practice Record",
    ).startswith("a learner practice record, including prompt")
    assert (
        domain_object_label(
            (
                "Permit application records the current status, actor, source input, decision, blocked reason, "
                "evidence links, timestamp, and version history for the accepted first path."
            ),
            fallback="Permit state",
        )
        == "Permit Application"
    )
    assert (
        domain_object_label(
            (
                "Permit packet with parcel details, required document checklist, fee-status note, applicant contact, "
                "completeness state, correction request state, decision result, reason notes, and review evidence."
            ),
            fallback="Permit state",
        )
        == "Permit Packet"
    )
    assert (
        domain_object_label(
            "Public Records Redaction Workspace Intake Register",
            fallback="Public records redaction state",
        )
        == "Public Records Redaction Workspace Intake Register"
    )
    assert (
        join_system_labels(
            [
                "Public Records Redaction Workspace Intake Register — records source input and version history.",
                "Public Records Redaction Workspace Review Workspace — presents current state.",
                "Public Records Redaction Workspace Proof Ledger — keeps validation results.",
            ]
        )
        == (
            "Public Records Redaction Workspace Intake Register, "
            "Public Records Redaction Workspace Review Workspace, "
            "Public Records Redaction Workspace Proof Ledger"
        )
    )


def test_readable_action_chain_compacts_list_heavy_first_path() -> None:
    phrase = readable_action_chain_phrase(
        (
            "open the planner, enter roof details, usage, shading concerns, financing preferences and timeline, "
            "review ranked installation plans, and check cost assumptions and blockers, then see a saved plan record"
        ),
        limit=240,
        max_steps=4,
    )

    assert phrase == (
        "open the planner; enter roof details and related inputs; "
        "review ranked installation plans; check cost assumptions and blockers"
    )
    assert phrase.count(",") == 0
    assert not phrase.endswith(("and", "with", ","))


def test_readable_action_chain_bases_comma_following_finite_verbs() -> None:
    phrase = readable_action_chain_phrase(
        "A physics learner opens a preset experiment, adjusts barrier height and width, runs the simulation.",
        limit=220,
        max_steps=3,
    )

    assert phrase == "open a preset experiment; adjust barrier height and width; run the simulation"
    assert "opens" not in phrase
    assert "adjusts" not in phrase


def test_confirmed_text_collapses_connector_drift_and_inline_metric_lists() -> None:
    assert (
        boundary_clause_item(
            "Do not expand into adjacent workflows, broader automation, and or operational scale until proof exists."
        )
        == "Do not expand into adjacent workflows, broader automation, or operational scale until proof exists"
    )
    assert "and and" not in sentence_text("Keep the slice bounded and and reviewable.")
    assert inline_list_sentence(
        "The first release proves the first path: open the lab; select one preset; adjust controls; run the experiment."
    ) == "The first release proves the first path: open the lab, select one preset, adjust controls, and run the experiment"


def test_confirmed_markdown_cleanup_stays_in_text_owner() -> None:
    text_owner = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    callers = [
        CONFIRMED_TEXT_PATH,
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent.py",
        DOMAIN_INTELLIGENCE / "greenfield_actor_labels.py",
    ]

    assert "def clean_markdown_text" in text_owner
    assert clean_markdown_text(" **Resident** sees `booking` , ready") == "Resident sees booking, ready"
    assert confirmed_text_values(" **Resident** confirms `booking` ") == ["Resident confirms booking"]

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "clean_markdown_text" in source
        assert 'replace("**", "")' not in source
        assert 'replace("__", "")' not in source
        assert 'replace("`", "")' not in source
        assert 're.sub(r"\\s+([,.;:?!])", r"\\1", text)' not in source


def test_inline_markdown_cleanup_shared_by_confirmed_text_callers() -> None:
    callers = [
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_components.py",
        DOMAIN_INTELLIGENCE / "greenfield_first_path_common.py",
        DOMAIN_INTELLIGENCE / "greenfield_sequence_steps.py",
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_diagram_text.py",
        DOMAIN_INTELLIGENCE / "greenfield_semantic_model.py",
        DOMAIN_INTELLIGENCE / "greenfield_component_term_windows.py",
    ]

    assert clean_markdown_text(" **Ops** sees `status` , ready") == "Ops sees status, ready"
    assert clean_markdown_sentence(" **ops** sees `status` , ready.") == "Ops sees status, ready."
    assert clean_first_path_text(" **Ops** sees `status` , ready") == "Ops sees status, ready"
    assert diagram_sentence(" **ops** sees `status` , ready.") == "Ops sees status, ready."
    assert sequence_event_steps("1. Open app. 2. **Ops** adds `status` , ready. 3. Save result.") == [
        "Ops adds status, ready",
        "Save result",
    ]
    assert system_component_name("**AI** `Review` Service") == "AI Review Service"
    assert system_component_name("Weight and side effect tracking service") == "Weight and Side Effect Tracking Service"
    assert literal_label_terms("**Claims** `Review` Store", noise_terms=set()) == ["claim", "review"]
    semantic = semantic_model_mapping(
        build_greenfield_semantic_model(
            title="**Claims** Review",
            state_object="`claim` state",
            first_path="**Reviewer** records `score` , status.",
            proof_boundary="save `score` , ready",
            components=[],
            human_actors=["**Reviewer**"],
        )
    )
    assert semantic["first_path_contract"]["actor"] == "Reviewer"
    assert semantic["first_path_contract"]["events"][0]["text"] == "Reviewer records score, status"

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "clean_markdown_text" in source or "clean_markdown_sentence" in source
        assert "display_text.strip_inline_markdown_emphasis_tokens" not in source
        assert 'replace("`", "")' not in source
        assert 're.sub(r"\\s+([,.;:?!])", r"\\1", text)' not in source


def test_markdown_sentence_casing_stays_in_text_owner() -> None:
    text_owner = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    callers = [
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_diagram_text.py",
        DOMAIN_INTELLIGENCE / "greenfield_sequence_steps.py",
    ]

    assert "def clean_markdown_sentence" in text_owner
    assert clean_markdown_sentence(" **ops** sees `status` , ready.") == "Ops sees status, ready."
    assert clean_markdown_sentence(" **ops** sees `status` , ready?") == "Ops sees status, ready?"
    assert diagram_sentence(" **ops** sees `status` , ready.") == "Ops sees status, ready."
    assert sequence_event_steps("1. Open app. 2. **ops** sees `status` , ready.") == [
        "Ops sees status, ready"
    ]

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "clean_markdown_sentence" in source
        assert "text[:1].upper() + text[1:]" not in source
        assert 'return f"{text}." if text else ""' not in source


def test_first_path_cleanup_normalizes_dash_continuations() -> None:
    assert (
        clean_first_path_text("Records the picked weight —, and opens the timeline.")
        == "Records the picked weight, and opens the timeline."
    )
    assert (
        clean_first_path_text("Logs a reading — then reviews the trend.")
        == "Logs a reading, then reviews the trend."
    )


def test_first_path_gerunds_use_action_phrase_not_object_nouns() -> None:
    assert (
        gerund_action_fragment("A grower defines a block (variety, area, planting year)")
        == "defining a block (variety, area, planting year)"
    )
    assert gerund_action_fragment("A user provides a report") == "providing a report"
    assert gerund_action_fragment("opens a preset experiment") == "opening a preset experiment"
    assert gerund_action_fragment("visits the workspace") == "visiting the workspace"
    assert gerund_action_fragment("edits the record") == "editing the record"
    assert gerund_action_fragment("blocks invalid input") == "blocking invalid input"


def test_first_path_temporal_actions_do_not_gerund_object_lists() -> None:
    first_path = (
        "A grower defines a block (variety, area, planting year), logs a spray application "
        "against it with product, rate, and date, and at harvest records the picked weight "
        "— then opens the block and sees its season timeline plus this year's yield against last year's."
    )

    steps = first_path_steps(first_path)
    capability = first_path_capability_phrase(first_path, gerund=True, max_fragments=7, limit=320)

    assert "A grower records the picked weight at harvest" in steps
    assert "defining a block" in capability
    assert "logging a spray application against it with product, rate and date" in capability
    assert "recording the picked weight at harvest" in capability
    assert "rating and date" not in capability


def test_first_path_gerund_capability_includes_terminal_visible_result() -> None:
    first_path = (
        "A new user records their first entry — rates today's status. "
        "A new user taps the factors that applied. "
        "A new user logs one action they tried. "
        "The next day they log again. "
        "After a handful of entries. "
        "The app shows a simple trend: status over time, and which logged actions line up with better days."
    )

    capability = first_path_capability_phrase(first_path, gerund=True, max_fragments=8, limit=340)

    assert "recording first entry" in capability
    assert "logging again" in capability
    assert "reviewing a simple trend: status over time" in capability


def test_first_path_capability_lowers_sentence_start_visible_result_objects() -> None:
    first_path = (
        "Trial coordinators record eligibility facts, consent versions, family questions. "
        "Clinician review, adverse-event exclusions and ethics-board readiness proof "
        "without making unsafe medical recommendations."
    )

    capability = first_path_capability_phrase(first_path, max_fragments=8, limit=340)
    gerund = first_path_capability_phrase(first_path, gerund=True, max_fragments=8, limit=340)

    assert "see clinician review" in capability
    assert "see Clinician review" not in capability
    assert "Clinician review" not in gerund
    assert "reviewing Clinician review" not in gerund
    assert generated_semantic_slop_issues({"capability": capability, "gerund": gerund}) == []


def test_terminal_proof_noun_phrase_becomes_visible_outcome() -> None:
    first_path = (
        "Researchers record molecule setup, basis-set choices, solver settings, convergence warnings, "
        "result comparisons, peer-review notes. Publication proof without running expensive compute jobs."
    )

    model = first_path_model(first_path)
    capability = first_path_capability_phrase(first_path, gerund=True, max_fragments=8, limit=340)

    assert model.visible_outcome == "Publication proof without running expensive compute jobs"
    assert "publication proof without running expensive compute jobs" in capability
    assert "reviewing notes" not in capability
    assert generated_semantic_slop_issues({"capability": capability}) == []


def test_boundary_clause_questions_become_declarative_scope_text() -> None:
    assert (
        boundary_clause_item("Is regulatory spray compliance in scope for v1 or later?")
        == "regulatory spray compliance scope remains deferred"
    )
    assert (
        boundary_clause_item("Whether applicants authenticate through an existing city identity provider remains deferred.")
        == "whether applicants authenticate through an existing city identity provider remains deferred"
    )
    assert (
        boundary_clause_item("Does this need offline mobile logging?")
        == "scope question remains open: does this need offline mobile logging"
    )


def test_confirmed_intent_semantic_terms_stay_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(
        encoding="utf-8"
    )
    validation_source = (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent_validation.py"
    ).read_text(encoding="utf-8")
    system_rows_source = (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_system_rows.py"
    ).read_text(encoding="utf-8")

    assert "def semantic_terms" in text_source
    assert "stem_ing_minimum_length" in index_source
    assert "ordered_terms(" in text_source
    assert "CONFIRMED_INTENT_VALIDATION_STOPWORDS" in text_source
    assert "normalize_domain_token" not in text_source
    assert "for raw in re.findall" not in text_source
    assert "def _semantic_terms" not in validation_source
    assert "def _semantic_terms" not in system_rows_source
    assert "semantic_terms(" in validation_source
    assert "semantic_terms as _semantic_terms" in system_rows_source
    assert "normalize_domain_token" not in validation_source
    assert "normalize_domain_token" not in system_rows_source

    assert semantic_terms("Race readings and gearbox readings are reviewing status.") == {
        "race",
        "read",
        "gearbox",
        "review",
        "status",
    }
    assert ordered_terms(
        "Race readings and gearbox readings are reviewing status.",
        minimum=3,
        stem_ing=True,
        stem_ing_minimum_length=5,
        stopwords={"and", "are"},
    ) == ["race", "read", "gearbox", "review", "status"]
    assert "product" not in semantic_terms(
        "Product proof keeps a gearbox result ready.",
        stopwords=CONFIRMED_INTENT_VALIDATION_STOPWORDS,
    )


def test_confirmed_project_surface_word_count_stays_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    project_brief_source = (
        DOMAIN_INTELLIGENCE / "greenfield_project_brief.py"
    ).read_text(encoding="utf-8")
    project_intelligence_source = (
        DOMAIN_INTELLIGENCE / "greenfield_project_intelligence.py"
    ).read_text(encoding="utf-8")

    assert "def word_count" in text_source
    assert "def word_occurrences" in text_source
    assert (
        "greenfield_text import word_occurrences as _generic_word_occurrences"
        in text_source
    )
    assert "re.findall(" not in text_source
    assert "greenfield_confirmed_text import word_count" in project_brief_source
    assert "greenfield_confirmed_text import word_count" in project_intelligence_source
    assert "def _word_count" not in project_brief_source
    assert "def _word_count" not in project_intelligence_source
    assert word_count("Source-backed review/triage keeps `AI` CRM status visible.") == 9
    assert word_occurrences("Required proof and required signoff stay visible.", "required") == 2
    assert word_occurrences("`Required` proof and **required** signoff stay visible.", "required") == 2
    assert generic_word_occurrences("Required proof and required signoff stay visible.", "required") == 2


def test_word_boundary_clipping_stays_in_text_owner() -> None:
    text_owner = GREENFIELD_TEXT_PATH.read_text(encoding="utf-8")
    touched_callers = [
        "greenfield_confirmed_text.py",
        "greenfield_first_path_common.py",
        "greenfield_semantic_model.py",
        "greenfield_confirmed_system_rows.py",
        "greenfield_confirmed_diagram_text.py",
        "greenfield_sequence_labeling.py",
        "greenfield_experience.py",
        "greenfield_confirmed_project_brief.py",
    ]

    assert "def clip_text_at_word_boundary" in text_owner
    assert "def strip_dangling_word_tail" in text_owner
    assert clip_text_at_word_boundary(
        "Alpha beta with trailing detail",
        limit=16,
        dangling_words={"with"},
    ) == "Alpha beta"
    assert (
        clip_text_at_word_boundary(
            'baseline trends, capability markers, and clear "what changed" insight',
            limit=52,
        )
        == "baseline trends, capability markers, and clear"
    )
    assert "clear 'what<br" not in wrap_mermaid_label(
        'baseline trends, capability markers, and clear "what changed" insight',
        limit=52,
    )
    assert clip_text_at_word_boundary("IdentifierWithoutSpaces", limit=10) == "Identifier"

    for caller in touched_callers:
        source = (DOMAIN_INTELLIGENCE / caller).read_text(encoding="utf-8")
        assert "clip_text_at_word_boundary" in source
        assert '.rsplit(" ", 1)' not in source


def test_confirmed_tail_repair_strips_clipped_terminal_fragments() -> None:
    assert strip_dangling_tail("The first release narrows scope to a first") == "The first release narrows scope"
    assert strip_dangling_tail("Collect denial reasons, reviewer notes, and final") == (
        "Collect denial reasons, reviewer notes"
    )
    assert strip_dangling_tail("The review status is final") == "The review status is final"


def test_first_path_phrase_clipping_strips_incomplete_terminal_modifier_fragments() -> None:
    phrase = (
        "turn an ambiguous case into a review-ready record using source evidence, explicit review board, "
        "auditable decisions and a final classification recommendation"
    )

    clipped = clip_first_path_phrase(phrase, limit=132)

    assert clipped == (
        "turn an ambiguous case into a review-ready record using source evidence, "
        "explicit review board, auditable decisions"
    )
    assert not clipped.endswith((" and a final", " a final", " final"))
    assert clip_first_path_phrase("mark the review status is final before handoff proof", limit=34) == (
        "mark the review status is final"
    )


def test_confirmed_focus_label_uses_shared_label_terms() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import label_terms" in text_source
    assert 're.findall(r"[A-Za-z0-9]+", title)' not in text_source
    assert label_terms("Source-backed Review Workspace") == ["Source-backed", "Review", "Workspace"]
    assert focus_label("Source-backed Review Workspace") == "Source-backed Review"
    assert focus_label("AI/ML Review Workspace") == "AI ML Review"


def test_confirmed_intent_parser_word_count_stays_in_text_owner() -> None:
    text_source = CONFIRMED_TEXT_PATH.read_text(encoding="utf-8")
    confirmed_intent_source = (
        DOMAIN_INTELLIGENCE / "greenfield_confirmed_intent.py"
    ).read_text(encoding="utf-8")

    assert "def word_count" in text_source
    assert (
        "greenfield_confirmed_text import word_count as _word_count"
        in confirmed_intent_source
    )
    assert "def _word_count" not in confirmed_intent_source
    assert word_count("Accepted `AI` review/triage keeps status visible.") == 7
