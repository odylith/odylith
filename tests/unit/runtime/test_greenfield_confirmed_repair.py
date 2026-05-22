from __future__ import annotations

import json

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    CONTRACT_KEYS,
    public_prose_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent


def _dirty_complete_contract() -> dict[str, object]:
    return {
        "owned_state": "Human actors: Reviewer",
        "accepted_inputs": "Accepts representative input covering source, state, and proof plus 1 more",
        "produced_outputs": "Owns the local responsibility and keeps it tied to this product behavior",
        "states_or_transitions": "draft, active, and with clear ownership, protected access, required",
        "outside_boundary": "sibling work when the path is.",
        "local_proof": [
            "Component proof uses representative input covering the accepted first path.",
            "Validate with clear ownership, protected access, required",
        ],
        "upstream_truth": "accepted first-path input",
        "downstream_consumers": "release proof review",
        "unique_failure": "The component can appear complete with",
    }


def test_confirmed_repair_loop_cleans_dirty_public_prose_across_artifact_families(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        confirmed_intent=_confirmed_intent(),
        release_selector="0.0.1",
    )

    proposal["intent"]["proof_boundary"] = "Proof."
    proposal["validation_strategy"] = [
        "Validate with clear ownership, protected access, required",
        "The user verifies that The evidence changed.",
    ]
    proposal["security_compliance"] = {
        "domain": "Human actors: Reviewer",
        "security": "Security posture plus 1 more",
        "policy": "Policy with clear ownership, protected access, required",
    }
    proposal["project_intelligence"]["operators"] = ["Human actors: Reviewer"]
    proposal["risks"] = [
        {
            "id": "RISK-BAD",
            "title": "Human actors: Reviewer",
            "statement": "The release verifies that The proof is present.",
            "mitigation": "Mitigate with",
        }
    ]

    first_backlog = proposal["backlog"][0]
    first_backlog["problem"] = "Human actors: Reviewer"
    first_backlog["customer"] = "Primary user plus 1 more"
    first_backlog["opportunity"] = "Uses Example App to complete A reviewer creates a case."
    first_backlog["product_view"] = "The user inspects The generated state."
    first_backlog["success_metrics"] = ["Validate when the path is."]
    first_backlog["domain_risk"] = "Human actors: Reviewer"
    first_backlog["security_posture"] = "Security posture plus 1 more"
    first_backlog["risks"] = ["Risk with"]
    first_backlog["validation"] = ["Validate with clear ownership, protected access, required"]
    first_backlog["rationale_lines"] = ["Rationale when the path is."]

    for row in proposal["components"][:2]:
        row["component_contract"] = _dirty_complete_contract()
        row["responsibility"] = "Owns the local responsibility and keeps it tied to this product behavior"
        row["boundary"] = "Human actors: Reviewer"
        row["interfaces"] = ["Primary interface plus 1 more"]
        row["dependencies"] = ["Dependency with"]
        row["validation"] = ["Validate with clear ownership, protected access, required"]
        row["risks"] = ["Risk when the path is."]

    proposal["diagrams"][0]["title"] = "Human actors: Reviewer"
    proposal["diagrams"][0]["summary"] = "The user inspects The generated state."

    repaired = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    encoded = json.dumps(repaired)
    for banned in (
        "inspect The",
        "verifies that The",
        "Human actors:",
        "plus 1 more",
        "responsibility and keeps it tied",
        "with clear ownership, protected access, required",
        "when the path is.",
        "to complete A",
    ):
        assert banned not in encoded
    assert public_prose_quality_issues(repaired) == []
    assert component_spec_preflight_issues(repaired) == []

    for row in repaired["components"][:2]:
        assert set(CONTRACT_KEYS) <= set(row["component_contract"])
        contract_text = json.dumps(row["component_contract"]).casefold()
        assert "permit" in contract_text or "zoning" in contract_text or "revision" in contract_text
