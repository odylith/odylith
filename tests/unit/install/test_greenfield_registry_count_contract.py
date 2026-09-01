from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_quality_scoring import completion_issues
from greenfield_matrix_package_evidence import _registry_findings
from greenfield_matrix_types import GreenfieldArtifactCounts
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact


def test_completion_has_no_arbitrary_artifact_count_floor() -> None:
    assert not completion_issues(
        counts=GreenfieldArtifactCounts(),
        manifest={"requested_repair_tier": "auto", "repair_tier": "standard", "budget_seconds": 60.0},
        create_returncode=0,
        proposal_seconds=20.0,
        create_seconds=20.0,
    )


def test_completion_still_enforces_transaction_result_and_time() -> None:
    counts = GreenfieldArtifactCounts()

    manifest = {"requested_repair_tier": "auto", "repair_tier": "standard", "budget_seconds": 60.0}
    assert completion_issues(
        counts=counts,
        manifest=manifest,
        create_returncode=2,
        proposal_seconds=20.0,
        create_seconds=20.0,
    )
    assert completion_issues(
        counts=counts,
        manifest=manifest,
        create_returncode=0,
        proposal_seconds=20.0,
        create_seconds=60.0,
    )


def test_registry_readback_rejects_missing_accepted_component_by_exact_set_size() -> None:
    proposal = {
        "intent": {"internal_systems": []},
        "components": [
            {"component_id": f"component-{index}", "release_scope": "first_path_required"}
            for index in range(3)
        ],
    }
    artifacts = tuple(
        RenderedArtifact(
            surface="Registry component spec",
            name=f"component-{index}/CURRENT_SPEC.md",
            text="Source boundary. Trace links. Successful path evidence. Blocked input evidence. Replay evidence.",
        )
        for index in range(2)
    )

    findings = _registry_findings(package=SimpleNamespace(), artifacts=artifacts, proposal=proposal)

    assert any("expected 3, found 2" in finding.message for finding in findings)


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


def test_single_component_registry_does_not_reinterpret_responsibility_prose() -> None:
    findings = _registry_package_findings(responsibility="Records support requests and intake status.")

    assert not any("Calendar Sync imports approved schedule slots" in finding for finding in findings)


def test_single_component_registry_retains_structural_proof_checks() -> None:
    findings = _registry_package_findings(
        responsibility="Records support requests and imports approved schedule slots from Calendar Sync."
    )

    assert not any("accepted internal-system responsibility is not covered" in finding for finding in findings)
