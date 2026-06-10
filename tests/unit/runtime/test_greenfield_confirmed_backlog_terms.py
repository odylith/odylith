from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import (
    confirmed_backlog_rows,
)
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_occurrences


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
BACKLOG_TEXT_MODEL_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_backlog_text_model.py"


def test_confirmed_backlog_terms_use_shared_domain_index() -> None:
    source = BACKLOG_TEXT_MODEL_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "greenfield_confirmed_text import word_count" in source
    assert "greenfield_confirmed_text import word_occurrences" in source
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
    assert proof_focus_phrase(
        "Operator approval, with a very long release readiness decision and many additional words, final signoff",
        fallback="fallback",
    ) == "operator approval"
    assert looks_mechanical_summary("required actor identity and required validation context")
    assert word_occurrences("Required proof, source evidence, and required signoff.", "required") == 2


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


def test_confirmed_backlog_rationale_uses_distinct_bullet_jobs() -> None:
    lines = rationale_lines(
        label="Choice Practice Journal",
        title="Make Choice Practice Journal Useful for One Complete Outcome",
        opportunity=(
            "Ship one complete outcome: a representative user can create an account, add a learner profile, "
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


def test_confirmed_backlog_rationale_does_not_splice_scope_question_into_wait_clause() -> None:
    lines = rationale_lines(
        label="Cellar",
        title="Make Cellar Useful for One Complete Outcome",
        opportunity="Prove the first vineyard management outcome before optional scope expands.",
        first_slice="Define a block and review the season timeline.",
        proof_boundary="The release works when the block timeline can be reviewed.",
        deferred_scope=("Is regulatory spray compliance in scope for v1 or later?",),
    )
    text = "\n".join(lines)

    assert "? wait" not in text
    assert (
        "- deferred for now: Regulatory spray compliance scope remains deferred; separate owner, acceptance gate, and proof path required."
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
        parent_title="Make Cellar Useful for One Complete Outcome",
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
    workflow_first_slice = rows[1]["recommended_first_slice"]

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
