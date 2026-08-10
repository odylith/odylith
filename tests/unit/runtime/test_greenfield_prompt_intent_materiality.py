from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_explicit_decision_gap import explicit_decision_gap
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materiality import (
    title_supports_conservative_first_path,
)


def test_runtime_missing_evidence_condition_is_not_a_user_decision_gap() -> None:
    assert explicit_decision_gap(
        "The team resolves disagreements, records disagreement history, and blocks export when required evidence is missing."
    ) is None

    gap = explicit_decision_gap(
        "The allocation rule and cancellation authority are unspecified."
    )
    assert gap is not None
    assert gap.required_fields == ("allocation_rule", "cancellation_authority")


def test_runtime_condition_does_not_hide_a_material_authority_gap() -> None:
    gap = explicit_decision_gap(
        "Exports pause when evidence is missing, and when the escalation authority is unspecified the queue stays blocked."
    )

    assert gap is not None
    assert gap.required_fields == ("escalation_authority",)


@pytest.mark.parametrize(
    ("evidence", "required_field"),
    (
        ("When the release threshold is unspecified, publication remains blocked.", "release_threshold"),
        ("When the retention period is unspecified, publication remains blocked.", "retention_period"),
    ),
)
def test_declared_conditional_uncertainty_is_a_material_gap(evidence: str, required_field: str) -> None:
    gap = explicit_decision_gap(evidence)

    assert gap is not None
    assert gap.required_fields == (required_field,)


def test_disjunctive_runtime_condition_names_the_material_gap_cleanly() -> None:
    gap = explicit_decision_gap(
        "Exports pause when evidence is missing or the escalation authority is unspecified."
    )

    assert gap is not None
    assert gap.required_fields == ("escalation_authority",)
    assert "the or the" not in gap.question.casefold()


@pytest.mark.parametrize(
    ("title", "evidence"),
    (
        ("city zoning permit review app", "Draft a greenfield proposal for a city zoning permit review app."),
        ("food safety recall traceability system", "Draft a greenfield proposal for a food safety recall traceability system."),
        ("quantum chemistry catalyst screening platform", "Draft a greenfield proposal for a quantum chemistry catalyst screening platform."),
    ),
)
def test_domain_anchored_titles_can_seed_a_conservative_first_path(title: str, evidence: str) -> None:
    assert title_supports_conservative_first_path(title=title, evidence=evidence)


def test_ordinary_title_assumptions_do_not_block_a_conservative_first_path() -> None:
    assert title_supports_conservative_first_path(
        title="collaborative request coordination system",
        evidence="Create collaborative request coordination system with a default starting view.",
    )


@pytest.mark.parametrize(
    "operating_mode_alternative",
    (
        "manual or automated",
        "live or fixture",
        "self-service or staff-review",
    ),
)
def test_title_only_operating_mode_alternatives_require_clarification(
    operating_mode_alternative: str,
) -> None:
    assert not title_supports_conservative_first_path(
        title="collaborative request coordination system",
        evidence=f"Create collaborative request coordination system: {operating_mode_alternative}.",
    )


@pytest.mark.parametrize(
    ("title", "evidence"),
    (
        ("assay review", "Create assay review."),
        ("service workspace for repairs and scheduling", "Create a service workspace for repairs and scheduling."),
        ("extension publisher release notes tool", "Create a tool for extension publishers to use for release notes."),
        ("cell therapy proposal", "Create a cell therapy proposal with several possible operating paths."),
    ),
)
def test_generic_or_materially_ambiguous_titles_still_require_a_first_path(title: str, evidence: str) -> None:
    assert not title_supports_conservative_first_path(title=title, evidence=evidence)
