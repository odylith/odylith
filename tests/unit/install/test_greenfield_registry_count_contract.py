from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_quality_scoring import completion_issues
from greenfield_matrix_quality_scoring import required_count_minimums
from greenfield_matrix_package_evidence import _registry_findings
from greenfield_matrix_types import GreenfieldArtifactCounts
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact


def _complete_counts(*, observed: int, expected: int) -> GreenfieldArtifactCounts:
    return GreenfieldArtifactCounts(
        radar_workstreams=4,
        registry_component_specs=observed,
        expected_registry_components=expected,
        atlas_mermaid_sources=4,
        compass_records=1,
        release_records=1,
        project_brief_records=1,
        trace_nodes=12,
        trace_workstreams=4,
        rendered_surfaces=6,
        rendered_surface_payloads=12,
        atlas_rendered_assets=8,
        domain_term_hits=3,
        required_domain_terms=3,
        project_implementation_prompts=5,
    )


def test_registry_floor_matches_a_two_component_accepted_transaction() -> None:
    counts = _complete_counts(observed=2, expected=2)

    assert required_count_minimums(counts)["Registry component specs"] == 2
    assert not [
        issue
        for issue in completion_issues(counts=counts, create_returncode=0, create_seconds=20.0)
        if issue.startswith("Registry component specs incomplete")
    ]


def test_registry_floor_rejects_missing_accepted_component() -> None:
    counts = _complete_counts(observed=2, expected=3)

    assert "Registry component specs incomplete: expected at least 3, found 2" in completion_issues(
        counts=counts,
        create_returncode=0,
        create_seconds=20.0,
    )


def _registry_package_findings(*, responsibility: str) -> list[str]:
    proposal = {
        "intent": {"internal_systems": ["Calendar Sync imports approved schedule slots."]},
        "components": [
            {
                "status": "active",
                "label": "Request Intake",
                "responsibility": responsibility,
                "boundary": "Owns request intake state.",
            }
        ],
    }
    spec = RenderedArtifact(
        surface="Registry component spec",
        name="request-intake/CURRENT_SPEC.md",
        text=(responsibility + " Source boundary. Trace links. Successful path evidence. Blocked input evidence. Replay evidence. ") * 8,
    )
    return [
        finding.message
        for finding in _registry_findings(
            package=SimpleNamespace(),
            artifacts=(spec,),
            proposal=proposal,
        )
    ]


def test_single_component_registry_must_cover_each_accepted_responsibility() -> None:
    findings = _registry_package_findings(responsibility="Records support requests and intake status.")

    assert any("Calendar Sync imports approved schedule slots" in finding for finding in findings)


def test_single_component_registry_can_cover_multiple_accepted_responsibilities() -> None:
    findings = _registry_package_findings(
        responsibility="Records support requests and imports approved schedule slots from Calendar Sync."
    )

    assert not any("accepted internal-system responsibility is not covered" in finding for finding in findings)
