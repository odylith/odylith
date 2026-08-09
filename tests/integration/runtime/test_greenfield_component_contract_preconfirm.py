from __future__ import annotations

import subprocess

from odylith.runtime.domain_intelligence import greenfield_component_contract_differentiation as differentiation
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_index import (
    component_domain_terms,
    component_local_terms,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)


def test_preconfirm_component_contracts_keep_local_first_path_meaning(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    prompt = (
        "Create a greenfield proposal for a package supply chain exception desk that receives vulnerable "
        "dependency reports, tracks provenance and waiver evidence, coordinates package manager review, "
        "preserves release readiness proof, and blocks shipment until exceptions are approved."
    )
    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        confirmed_intent=candidate,
        require_completion_ready=False,
    )
    specs = differentiation._render_component_specs(proposal)

    assert rendered_component_spec_quality_issues(
        specs,
        project_title=differentiation._project_title(proposal),
    ) == []
    assert not any(str(row.get("label", "")).startswith("Until ") for row in proposal["components"])
    assert any(str(row.get("label", "")).startswith("Shipment Workflow") for row in proposal["components"])
    assert all(str(row.get("title", "")) != "Let Package Are Approved" for row in proposal["backlog"])
    assert any("See the Blocked Shipment" in str(row.get("title", "")) for row in proposal["backlog"])

    names = tuple(specs)
    name_terms = {name: component_domain_terms(name) for name in names}
    repeated_name_terms = {
        term
        for terms in name_terms.values()
        for term in terms
        if sum(term in sibling_terms for sibling_terms in name_terms.values()) > 1
    }
    spec_terms = {name: component_domain_terms(text) for name, text in specs.items()}
    all_spec_terms = tuple(spec_terms.values())
    for name in names:
        assert len(
            component_local_terms(
                text_terms=spec_terms[name],
                name_terms=name_terms[name],
                all_text_terms=all_spec_terms,
                repeated_name_terms=repeated_name_terms,
            )
        ) >= 4

    intake = next(
        row
        for row in proposal["components"]
        if str(row.get("label", "")).startswith("Vulnerable Dependency Reports")
    )
    intake_io = " ".join(
        str(intake["component_contract"].get(key, ""))
        for key in ("accepted_inputs", "produced_outputs")
    ).casefold()
    for sibling_fact in ("provenance", "waiver", "manager", "readiness", "shipment"):
        assert sibling_fact not in intake_io

    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="",
        proposal_ready=True,
    )

    assert transaction.verified is True
    assert transaction.quality_manifest["status"] == "passed"


def test_sparse_action_components_keep_source_backed_local_meaning(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    prompt = (
        "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
        "coordinates review, records evidence custody, decides embargo status, and publishes first release "
        "readiness proof without personalized notification delivery."
    )
    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        confirmed_intent=candidate,
        require_completion_ready=False,
    )
    specs = differentiation._render_component_specs(proposal)

    assert rendered_component_spec_quality_issues(
        specs,
        project_title=differentiation._project_title(proposal),
    ) == []
    assert any(name.startswith("Reports Intake") for name in specs)
    assert any(name.startswith("Review Coordination") for name in specs)
    rendered = "\n".join(specs.values()).casefold()
    assert "receives reports" in rendered
    assert "coordinates review" in rendered
    assert "review coordination" in rendered

    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="",
        proposal_ready=True,
    )

    assert transaction.verified is True
    assert transaction.quality_manifest["status"] == "passed"
    story_rows = transaction.prewrite_package.project_dashboard_preview["product_story"]["release_contract"]
    cards = {str(row["label"]): str(row["body"]) for row in story_rows}
    assert "personalized notification delivery" in cards["Product Boundary"].casefold()
    for label in ("First Path", "Owned Capabilities", "Proof"):
        assert "personalized notification delivery" not in cards[label].casefold()


def test_open_source_embargo_compiles_a_clean_preconfirm_transaction(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    prompt = (
        "Create a greenfield proposal for an open source security embargo room that receives vulnerability "
        "reports, coordinates maintainer triage, tracks affected package evidence, records disclosure "
        "approvals, and shows advisory readiness without sending public announcements in the first release."
    )
    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        confirmed_intent=candidate,
        require_completion_ready=False,
    )

    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="",
        proposal_ready=True,
    )

    assert transaction.verified is True
    assert transaction.quality_manifest["status"] == "passed"
    assert all(" An Coordinates " not in str(row.get("title", "")) for row in transaction.proposal["backlog"])
    assert any("Coordinate Maintainer Triage" in str(row.get("title", "")) for row in transaction.proposal["backlog"])
