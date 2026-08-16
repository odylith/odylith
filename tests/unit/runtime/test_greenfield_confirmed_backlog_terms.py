from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import (
    confirmed_backlog_rows,
    confirmed_workstream_titles,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_language import proof_focus_summary
from odylith.runtime.domain_intelligence.greenfield_proof_boundary_text import derived_proof_boundary_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    looks_mechanical_summary,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    normalize_action_clause,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    proof_focus_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    proof_claim_summary,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    problem_actor_subject,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    rationale_lines,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    semantic_words,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    shares_product_terms,
)
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_action_splice_phrase
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_artifact_tail
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_occurrences
from odylith.runtime.domain_intelligence.greenfield_component_contract import public_prose_quality_issues
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import (
    build_workstream_domain_intelligence,
)


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
BACKLOG_TEXT_MODEL_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_backlog_text_model.py"
BACKLOG_LANGUAGE_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_backlog_language.py"


def test_confirmed_backlog_terms_use_shared_domain_index() -> None:
    source = BACKLOG_LANGUAGE_PATH.read_text(encoding="utf-8")
    text_model_source = BACKLOG_TEXT_MODEL_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "greenfield_confirmed_text import word_count" in source
    assert "greenfield_confirmed_text import word_occurrences" in source
    assert "greenfield_domain_term_index import ordered_terms" not in text_model_source
    assert 're.findall(r"[a-z0-9][a-z0-9-]+"' not in source
    assert 'len(re.findall(r"[A-Za-z0-9][A-Za-z0-9' not in source
    assert 'len(re.findall(r"\\brequired\\b"' not in source
    assert semantic_words("Status windows, review services, and source-backed audit trails.") == {
        "audit",
        "review",
        "service",
        "source-backed",
        "status",
        "trail",
        "window",
    }
    assert shares_product_terms(
        "Deliver status windows with proof evidence.",
        "A window proof evidence summary remains visible.",
    )
    assert not shares_product_terms(
        "Deliver the accepted first product path.",
        "The release result lets the user complete that path.",
    )


def test_greenfield_phrase_quality_normalizes_use_action_splices() -> None:
    assert normalize_action_splice_phrase("uses create share-ready summary") == "creates share-ready summary"
    assert (
        normalize_action_splice_phrase("evidence for use create share-ready summary")
        == "evidence for creating share-ready summary"
    )
    assert proof_focus_phrase(
        "Operator approval, with a very long release readiness decision and many additional words, final signoff",
        fallback="fallback",
    ) == "operator approval"
    assert looks_mechanical_summary("required actor identity and required validation context")
    assert word_occurrences("Required proof, source evidence, and required signoff.", "required") == 2
    assert proof_focus_summary("and final approval status") == "final approval status"


def test_confirmed_backlog_public_text_collapses_duplicate_neighbor_terms_generically() -> None:
    assert collapse_adjacent_duplicate_terms("Keep release scope scope small.") == "Keep release scope small."
    assert (
        collapse_adjacent_duplicate_terms("Keep comparison review, review. When the path blocks, explain why.")
        == "Keep comparison review. When the path blocks, explain why."
    )
    assert (
        collapse_adjacent_duplicate_terms("Owner: Let Response Coordinator Register a Shelter - Shelter Manager")
        == "Owner: Let Response Coordinator Register a Shelter Manager"
    )
    assert (
        normalize_artifact_tail("public match summary correction final", carrier_terms={"summary", "status"})
        == "public match summary correction final status"
    )
    assert (
        normalize_artifact_tail("field intake with attribution command", carrier_terms={"command", "intake"})
        == "field intake with attribution command"
    )
    assert normalize_artifact_tail("key established", carrier_terms={"state"}) == "key established"
    assert normalize_artifact_tail("prior runs viewable", carrier_terms={"state"}) == "prior runs viewable"
    assert normalize_artifact_tail("audit and review lifecycle", carrier_terms={"lifecycle"}) == (
        "audit and review lifecycle"
    )

    lines = rationale_lines(
        label="Cooking Robot Controller",
        title="Prove One Complete Cooking Robot Controller Path",
        opportunity="Keep release scope scope narrow before optional expansion.",
        first_slice="scope scope remains centered on one complete path",
        proof_boundary="Release works when one path can be reviewed.",
    )
    packet = build_workstream_domain_intelligence(
        label="Cooking Robot Controller",
        row_title="Prove One Complete Cooking Robot Controller Path",
        problem="A home cook needs one safe cooking path before broader automation.",
        opportunity="Keep release scope scope narrow before optional expansion.",
        product_view="The first path remains inside accepted scope scope until proof passes.",
        first_slice="scope scope remains centered on one complete path",
        metrics=["One path succeeds, blocks, and recovers."],
        dependencies=["Accepted actor and hardware simulator context."],
        interfaces=["Recipe sequence, safety supervisor, and session telemetry."],
        validation=["Run success, blocked-input, and emergency-stop paths."],
        state_object="Cook Session",
        evidence_record="Cook Session Proof Record",
        first_path="A home cook picks a recipe and reviews the finished result.",
        proof_boundary="Release works when one path can be reviewed.",
        human_actors=["Home Cook: selects the recipe."],
        internal_systems=["Recipe Sequencer", "Safety Supervisor"],
        external_systems=["Robot simulator"],
        non_goals=["Broader automation remains deferred."],
    )
    rendered = "\n".join(lines) + "\n" + str(packet)

    assert "scope scope" not in rendered.casefold()
    source = BACKLOG_TEXT_MODEL_PATH.read_text(encoding="utf-8")
    assert 'replace("scope scope"' not in source


def test_workstream_scope_boundary_preserves_scientific_tail_actions_marked_system_side() -> None:
    first_path = (
        "Physicist can provide inputs, validate units and provenance, run the model, "
        "compare against a baseline, record uncertainty, and save a reviewable result."
    )
    packet = build_workstream_domain_intelligence(
        label="Cryogenic Ion Trap Calibration Workspace",
        row_title="Prove Cryogenic Ion Trap Calibration Intake-to-proof Workspace",
        problem="A physicist needs one bounded calibration run before broader automation.",
        opportunity="Keep the first release inside one reproducible calibration run.",
        product_view="The workspace preserves source data, baseline comparison, uncertainty, and review notes.",
        first_slice="one physicist completes one cryogenic calibration run",
        metrics=["One run succeeds, blocks, and can be reviewed."],
        dependencies=["Accepted physicist and calibration evidence context."],
        interfaces=["Source data, baseline comparison, uncertainty, and review note."],
        validation=["Run success, missing provenance, and baseline comparison paths."],
        state_object="Cryogenic calibration run record",
        evidence_record="Cryogenic calibration proof record",
        first_path=first_path,
        proof_boundary="Release works when one physicist can save a reviewable result with uncertainty.",
        human_actors=["Physicist: reviews calibration results."],
        internal_systems=["Calibration Intake", "Uncertainty Ledger"],
        external_systems=["Lab instrument export"],
        non_goals=["No live instrument control."],
    )
    rendered_constraints = "\n".join(packet["constraints"])

    assert "validate units and provenance" in rendered_constraints
    assert "run the model" in rendered_constraints
    assert "compare against a baseline" in rendered_constraints
    assert "record uncertainty" in rendered_constraints
    assert "save a reviewable result" in rendered_constraints
    assert "review a baseline" not in rendered_constraints
    assert "outcome:" not in rendered_constraints


def test_confirmed_workstream_titles_compact_long_state_changer_without_pronoun_tail() -> None:
    components = [
        {"label": "Warehouse Robot Near-miss Investigation Workspace Intake Register Service"},
        {"label": "Warehouse Robot Near-miss Investigation Workspace Review Workspace"},
        {"label": "Warehouse Robot Near-miss Investigation Workspace Proof Ledger"},
    ]

    _workflow, boundary, _proof = confirmed_workstream_titles(
        label="Warehouse Robot Near-miss",
        components=components,
        internal_systems=[],
        first_path=(
            "Safety leads capture incident telemetry. Safety leads preserve operator statements. "
            "Safety leads map zone controls. Safety leads route maintenance review. "
            "Safety leads publish restart readiness proof before robots return to service."
        ),
        state_object="A maintenance review record tracks actor, source input, status, owner, blocker, and handoff.",
        proof_boundary="Release succeeds when one restart readiness path is reviewable.",
        human_actors=["Safety Leads"],
    )

    assert boundary == "Keep Maintenance Review Record Clear During Review Workflow"
    assert "Changes It" not in boundary
    assert "Investigation Workspace Review Workspace" not in boundary


def test_confirmed_workstream_titles_do_not_repeat_clear_when_state_already_names_clarity() -> None:
    components = [
        {"label": "Escalation Intake Register"},
        {"label": "Escalation Review Workspace"},
        {"label": "Escalation Proof Ledger"},
    ]

    _workflow, boundary, _proof = confirmed_workstream_titles(
        label="Escalation Review",
        components=components,
        internal_systems=[],
        first_path="Care coordinators give clinicians a clear escalation packet for review.",
        state_object="Clear Escalation Packet",
        proof_boundary="Release succeeds when the escalation packet is reviewable.",
        human_actors=["Care Coordinators"],
    )

    assert boundary == "Keep Clear Escalation Packet Reviewable During Escalation Review Workspace"
    assert "Clear Escalation Packet Clear" not in boundary


def test_greenfield_quality_gate_allows_product_evidence_packet_language() -> None:
    proposal = {
        "intent": {
            "summary": "The product publishes a reviewed evidence packet with decision proof.",
            "product_story": "A team needs one place to assemble an evidence packet before a final decision is recorded.",
        },
        "backlog": [
            {
                "title": "Publish Review Evidence",
                "problem": "Reviewers need the evidence packet to stay tied to the decision record.",
                "customer": "Review team",
                "opportunity": "Keep response evidence, decision state, and ownership visible.",
                "product_view": "A reviewer can inspect the evidence packet and understand the decision outcome.",
                "success_metrics": ["One evidence packet is reviewed before the decision is closed."],
            }
        ],
    }

    assert greenfield_quality_issues(proposal) == []


def test_workstream_domain_intelligence_system_slots_are_not_clipped() -> None:
    packet = build_workstream_domain_intelligence(
        label="Evidence Routing Console",
        row_title="Prove One Complete Evidence Routing Path",
        problem="Teams need one accountable routing path before broader automation expands.",
        opportunity="Keep release scope narrow while the first routed outcome is proven.",
        product_view="The first path remains reviewable while source input, status, and evidence stay connected.",
        first_slice="A reviewer receives a source packet, routes it to a queue, and records proof.",
        metrics=["One routed path succeeds, blocks, and recovers."],
        dependencies=["Accepted actor and source packet context."],
        interfaces=["Source intake, routing queue, review evidence, and release decision."],
        validation=["Run success, blocked-input, access, replay, and evidence-review paths."],
        state_object="Evidence Routing Case",
        evidence_record="Evidence Routing Proof Record",
        first_path="A reviewer receives a source packet, routes it to a queue, and records proof.",
        proof_boundary="Release works when one route can be reviewed with evidence.",
        human_actors=["Review lead: receives source packets and records decisions."],
        internal_systems=[
            "Source Intake Register that captures incoming packet facts and ownership.",
            "Routing Queue Workspace that shows queue state, blockers, and review status.",
            "Evidence Proof Ledger that records validation output and release decisions.",
        ],
        external_systems=["Source packet feed."],
        non_goals=["Broader routing automation remains deferred."],
    )

    for path in ("operators.1", "topology.0", "owners.0"):
        key, index = path.split(".")
        value = packet[key][int(index)]
        assert public_prose_quality_issues(value) == []
        assert not value.rstrip(".").endswith((" for", " of", " the", " to", " with"))


def test_confirmed_backlog_rationale_keeps_proof_focus_complete() -> None:
    proof_boundary = (
        "The first thing the product must prove is that the intake-to-first-plan path produces a safe, "
        "evidence-grounded recovery plan and correctly raises an escalation warning when severity or warning signs "
        "cross a safety threshold. A close second is that day-over-day check-ins reliably detect whether skin is "
        "healing or worsening."
    )

    summary = proof_claim_summary(proof_boundary, limit=160)
    rationale = "\n".join(
        rationale_lines(
            label="SunRecover",
            title="Recovery plan generator",
            opportunity="SunRecover needs a bounded first release.",
            first_slice="capture an intake and produce a staged recovery plan",
            proof_boundary=proof_boundary,
        )
    )

    assert summary.startswith("the intake-to-first-plan path produces a safe, evidence-grounded recovery plan")
    assert "first thing the product must prove" not in summary
    assert "close second" not in summary.casefold()
    assert "close second" not in rationale.casefold()
    assert "produces a in the same release story" not in rationale
    assert (
        "SunRecover must prove the intake-to-first-plan path produces a safe, evidence-grounded recovery plan"
        in rationale
    )


def test_derived_proof_boundary_removes_ranking_wrappers_without_dropping_claims() -> None:
    raw = (
        "The first thing the product must prove is that one review produces a signed receipt. "
        "A close second is that an auditor can inspect the receipt."
    )

    assert derived_proof_boundary_text(raw) == (
        "One review produces a signed receipt. An auditor can inspect the receipt."
    )


def test_derived_proof_boundary_preserves_actor_led_visible_result_sentence() -> None:
    proof = "The first thing the reviewer sees is a signed badge."

    assert derived_proof_boundary_text(proof) == proof


def test_proof_claim_summary_removes_a_clipped_output_verb_and_connector() -> None:
    proof_boundary = (
        "Release succeeds when staff register requests, match needs to capacity, track accessibility constraints, "
        "preserve consent evidence, and produce"
    )

    summary = proof_claim_summary(proof_boundary, limit=300)

    assert summary.endswith("preserve consent evidence")
    assert not summary.endswith((" and", " produce"))


def test_proof_claim_summary_preserves_a_complete_reviewability_predicate() -> None:
    proof_boundary = (
        "Release 0.0.1 succeeds when the accepted first path is complete and "
        "the simulation evidence remains reviewable."
    )

    assert proof_claim_summary(proof_boundary) == (
        "the accepted first path is complete and the simulation evidence remains reviewable"
    )


def test_ranking_basis_does_not_repeat_a_secondary_visible_result_sentence() -> None:
    lines = rationale_lines(
        label="Permit Review Workspace",
        title="Prove One Complete Permit Review Path",
        opportunity="Prove one permit review before optional scope expands.",
        first_slice="Clerks submit permits and review status.",
        proof_boundary=(
            "Release 0.0.1 succeeds when clerks submit permits and review status. "
            "The product shows the permit review result before adjacent scope enters the release."
        ),
    )

    ranking_basis = lines[-1]
    assert "clerks submit permits and review status" in ranking_basis.casefold()
    assert "The product shows the permit review result" not in ranking_basis


def test_confirmed_backlog_rationale_uses_distinct_bullet_jobs() -> None:
    lines = rationale_lines(
        label="Choice Practice Journal",
        title="Prove One Complete Choice Practice Journal Path",
        opportunity=(
            "Prove the first release path: a representative user can create an account, add a learner profile, "
            "pick the age band, open a scenario, make a choice, and see a short reflection."
        ),
        first_slice=(
            "Deliver one complete path where a user can create an account, add a learner profile, pick the age band, "
            "open a scenario, make a choice, and see a short reflection."
        ),
        proof_boundary=(
            "The first release succeeds when a parent can create an account and learner profile, the learner can "
            "complete one scenario with a selected choice and reflection, and the parent can open a recap. "
            "Multiple age bands, authoring workflows, reminders, and live classroom management are outside the first proof."
        ),
    )
    text = "\n".join(lines)

    assert text.count("complete path where") <= 1
    assert "Adjacent Choice Practice Journal workflows" not in text
    assert "Multiple age bands, authoring workflows, reminders, and live classroom management" in text


def test_confirmed_backlog_deferred_rationale_is_scoped_to_workstream_title() -> None:
    shared_deferred_scope = [
        "Do not expand into adjacent workflows, broader automation, or operational scale until the first outcome works."
    ]
    first = rationale_lines(
        label="Permit Desk",
        title="Prepare Permit Intake Evidence",
        opportunity="Prove the first permit intake path before optional scope expands.",
        first_slice="Capture one permit packet and keep blockers visible.",
        proof_boundary="Release works when one permit packet can be reviewed.",
        deferred_scope=shared_deferred_scope,
    )
    second = rationale_lines(
        label="Permit Desk",
        title="Show Permit Review Decision",
        opportunity="Prove the first permit review path before optional scope expands.",
        first_slice="Review one permit packet and show the decision evidence.",
        proof_boundary="Release works when one decision can be reviewed.",
        deferred_scope=shared_deferred_scope,
    )

    assert first[3] != second[3]
    assert first[3].startswith("- deferred for now: Prepare Permit Intake Evidence:")
    assert second[3].startswith("- deferred for now: Show Permit Review Decision:")
    assert "adjacent workflows" in first[3]
    assert "adjacent workflows" in second[3]


def test_confirmed_backlog_rationale_does_not_splice_scope_question_into_wait_clause() -> None:
    lines = rationale_lines(
        label="Cellar",
        title="Prove One Complete Cellar Path",
        opportunity="Prove the first vineyard management outcome before optional scope expands.",
        first_slice="Define a block and review the season timeline.",
        proof_boundary="The release works when the block timeline can be reviewed.",
        deferred_scope=("Is regulatory spray compliance in scope for v1 or later?",),
    )
    text = "\n".join(lines)

    assert "? wait" not in text
    assert (
        "- deferred for now: Prove One Complete Cellar Path: Regulatory spray compliance scope remains deferred; separate owner, acceptance gate, and proof path required."
        in text
    )


def test_confirmed_backlog_rationale_does_not_add_wait_after_deferral_predicate() -> None:
    lines = rationale_lines(
        label="Teaching Lab",
        title="Prove One Complete Teaching Lab Path",
        opportunity="Prove the first simulated lab workflow before optional scope expands.",
        first_slice="Create one simulated experiment and review the evidence.",
        proof_boundary="Release works when one simulated experiment can be reviewed.",
        deferred_scope=("Grading automation and LMS sync remain deferred.",),
    )
    text = "\n".join(lines)

    assert "remain deferred wait" not in text
    assert (
        "- deferred for now: Prove One Complete Teaching Lab Path: Grading automation and LMS sync remain deferred; separate owner, acceptance gate, and proof path required."
        in text
    )


def test_confirmed_backlog_first_slice_preserves_object_lists_and_can_clause_grammar() -> None:
    first_path = (
        "A grower defines a block (variety, area, planting year), logs a spray application "
        "against it with product, rate, and date, and at harvest records the picked weight "
        "— then opens the block and sees its season timeline plus this year's yield against last year's."
    )
    rows = confirmed_backlog_rows(
        label="Cellar",
        parent_title="Prove One Complete Cellar Path",
        workflow_title="Let Grower Owner Define a Block",
        boundary_title="Keep Block Clear and Reviewable",
        proof_title="Show Why Block Can Be Trusted",
        state_object="Block",
        evidence_record="Task Planning Proof Record",
        product_story="A working grower needs one place to run the vineyard year.",
        first_path=first_path,
        proof_boundary=(
            "v1 is proven when a grower can define a block, log a dated spray and a harvest weight "
            "against it, and open that block to see its season timeline and yield."
        ),
        human_actors=["Grower / owner - defines blocks and reviews the season."],
        internal_systems=["Block registry", "Activity log", "Task planning"],
        external_systems=[],
        non_goals=[],
        components=[
            {"component_id": "block-record-service", "label": "Block Record Service"},
            {"component_id": "activity-log-service", "label": "Activity Log Service"},
            {"component_id": "task-planning-service", "label": "Task Planning Service"},
        ],
        diagram_slugs={
            "context": "context",
            "sequence": "sequence",
            "state_evidence": "state-evidence",
            "component_boundaries": "component-boundaries",
            "ownership": "ownership",
            "proof_review": "proof-review",
        },
    )
    parent_row = rows[0]
    workflow_first_slice = rows[1]["recommended_first_slice"]

    assert parent_row["title"] == "Prove One Complete Cellar Path"
    assert parent_row["opportunity"].startswith("Prove the first release path:")
    assert "Ship one complete outcome" not in parent_row["opportunity"]
    assert (
        normalize_action_clause(
            "define a block, log a spray application with product, rate and date, and record the picked weight"
        )
        == "define a block, log a spray application with product, rate and date, and record the picked weight"
    )
    assert "rate and date and record" not in workflow_first_slice
    assert "and lets" not in workflow_first_slice
    assert ", and the grower / owner can see" in workflow_first_slice
    assert "while the product gives clear correction guidance" in workflow_first_slice


def test_problem_actor_subject_preserves_acronym_number_tokens() -> None:
    assert problem_actor_subject("Person on the GLP-1 Medication", fallback="user") == "The person on the GLP-1 Medication"
    assert problem_actor_subject("API Owner", fallback="user") == "The API Owner"
