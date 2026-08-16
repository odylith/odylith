from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    rendered_component_spec_quality_issues,
)


def test_rendered_component_spec_quality_rejects_subjectless_calculated_action() -> None:
    spec = """
# Suggestion Service

## Component Role

It should explain how dosage suggestion, adds peptide, and relevant condition is calculated.
"""

    issues = rendered_component_spec_quality_issues(
        {"Suggestion Service": spec},
        project_title="Protocol Workspace",
    )

    assert "component spec Suggestion Service treats action adds peptide as a calculated object" in issues
