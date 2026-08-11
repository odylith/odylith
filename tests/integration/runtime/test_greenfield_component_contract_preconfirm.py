from __future__ import annotations

import json
import subprocess

from odylith.runtime.domain_intelligence import greenfield_component_contract_differentiation as differentiation
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    component_contract_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_index import (
    component_domain_terms,
    component_local_terms,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import (
    generic_contract_placeholder_fragments,
)


def _proposal_from_prompt(tmp_path, prompt: str):  # noqa: ANN001, ANN202
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
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
    return candidate, proposal


def test_preconfirm_component_contracts_keep_local_first_path_meaning(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for a package supply chain exception desk that receives vulnerable "
        "dependency reports, tracks provenance and waiver evidence, coordinates package manager review, "
        "preserves release readiness proof, and blocks shipment until exceptions are approved."
    )
    candidate, proposal = _proposal_from_prompt(tmp_path, prompt)
    specs = differentiation._render_component_specs(proposal)

    assert rendered_component_spec_quality_issues(
        specs,
        project_title=differentiation._project_title(proposal),
    ) == []
    assert not any(str(row.get("label", "")).startswith("Until ") for row in proposal["components"])
    assert any(str(row.get("label", "")).startswith("Shipment Workflow") for row in proposal["components"])
    assert all(str(row.get("title", "")) != "Let Package Are Approved" for row in proposal["backlog"])
    assert all(
        "supply chain exception desk user receive" not in str(row).casefold()
        for row in candidate["human_actors"]
    )
    rendered_contracts = " ".join(
        str(row.get("component_contract", ""))
        for row in proposal["components"]
    ).casefold()
    assert component_contract_issues(proposal) == []
    for row in proposal["components"]:
        contract = row["component_contract"]
        for key in ("accepted_inputs", "produced_outputs"):
            assert generic_contract_placeholder_fragments(str(contract[key])) == ()
    for malformed in (
        "expand adjacent workflow",
        "preserve readiness",
        "shipment until exception",
        "supplies chain",
    ):
        assert malformed not in rendered_contracts

    manager_review = next(
        row
        for row in proposal["components"]
        if str(row.get("label", "")).startswith("Package Manager Review")
    )
    manager_contract = manager_review["component_contract"]
    assert "package review request" in str(manager_contract["accepted_inputs"]).casefold()
    assert "package review record" in str(manager_contract["produced_outputs"]).casefold()

    shipment = next(
        row
        for row in proposal["components"]
        if str(row.get("label", "")).startswith("Shipment Workflow")
    )
    shipment_contract = shipment["component_contract"]
    assert "shipment workflow request" in str(shipment_contract["accepted_inputs"]).casefold()
    assert "shipment workflow record" in str(shipment_contract["produced_outputs"]).casefold()

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
    prompt = (
        "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
        "coordinates review, records evidence custody, decides embargo status, and publishes first release "
        "readiness proof without personalized notification delivery."
    )
    _candidate, proposal = _proposal_from_prompt(tmp_path, prompt)
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
    prompt = (
        "Create a greenfield proposal for an open source security embargo room that receives vulnerability "
        "reports, coordinates maintainer triage, tracks affected package evidence, records disclosure "
        "approvals, and shows advisory readiness without sending public announcements in the first release."
    )
    _candidate, proposal = _proposal_from_prompt(tmp_path, prompt)

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


def test_follow_up_compound_does_not_become_an_action_shaped_state(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for a developer incident runbook readiness tool that lets engineering "
        "leads capture service incidents, map owners to mitigation steps, collect verification evidence, "
        "track follow-up exceptions, and publish release-readiness proof before the next deployment window."
    )
    _candidate, proposal = _proposal_from_prompt(tmp_path, prompt)

    assert component_contract_issues(proposal) == []
    owned_state = " ".join(
        str(row["component_contract"]["owned_state"])
        for row in proposal["components"]
    ).casefold().replace("-", " ")
    assert "follow lifecycle" not in owned_state
    assert "follow up exceptions" in owned_state


def test_generated_coordination_taxonomy_remains_grounded_in_preconfirm_compile(tmp_path) -> None:
    prompts = (
        (
            "flood",
            "Create a greenfield proposal for a flood shelter intake system that helps city staff register "
            "displaced residents, match household needs to shelter capacity, track medical and accessibility "
            "constraints, preserve consent evidence, and produce a daily placement readiness report.",
        ),
        (
            "apprenticeship",
            "Create a greenfield proposal for a regional apprenticeship credential readiness system that lets "
            "training coordinators register apprentices, map completed skills to employer requirements, track "
            "mentor signoff evidence, manage accommodation exceptions, and publish certification readiness for "
            "review by a workforce board.",
        ),
    )
    for slug, prompt in prompts:
        case_root = tmp_path / slug
        _candidate, proposal = _proposal_from_prompt(case_root, prompt)
        transaction = greenfield_proposals.compile_greenfield_create_transaction(
            repo_root=case_root,
            proposal=proposal,
            release_selector="",
            proposal_ready=True,
        )

        assert transaction.verified is True
        assert transaction.quality_manifest["status"] == "passed"
        assert transaction.quality_manifest["issues"] == []


def test_existing_artifact_carrier_does_not_repeat_in_prewrite_registry(tmp_path) -> None:
    prompt = (
        "Draft a greenfield proposal for a lab app where researchers configure and launch an E91 quantum "
        "communication run on real hardware, observe live coincidence counts, Bell inequality checks, CHSH, "
        "QBER, and established key bits, then compare the saved run against prior results."
    )
    _candidate, proposal = _proposal_from_prompt(tmp_path, prompt)
    assert differentiation.differentiate_component_contracts(proposal) is False
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="",
        proposal_ready=True,
    )

    registry_preview = json.dumps(transaction.prewrite_package.component_registry_preview).casefold()
    assert transaction.verified is True
    assert transaction.quality_manifest["status"] == "passed"
    assert "record record" not in registry_preview
    for term in ("e91", "bell inequality", "chsh", "qber"):
        assert term in registry_preview
