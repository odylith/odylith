from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materiality import (
    title_supports_conservative_first_path,
)


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
