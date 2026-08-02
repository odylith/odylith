from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_projection import (
    _diagram_workstream_titles,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_text import (
    _component_review_sentence,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_repair import (
    repair_project_title,
)


def test_imperative_prompt_title_recovers_existing_product_identity() -> None:
    proposal = {
        "intent": {
            "title": "Build An Ecommerce Site With Checkout Recovery",
            "product_story": "Commerce Launch System helps shoppers recover a checkout attempt.",
            "state_object": "checkout record",
            "first_path": "A shopper retries checkout and sees the recovered order draft.",
            "proof_boundary": "Release proof shows one recovered checkout attempt.",
            "human_actors": ["Shopper"],
        },
        "backlog": [{"title": "Govern Commerce Launch System"}],
        "diagrams": [{"summary": "Build an ecommerce site with checkout recovery proof."}],
    }

    assert repair_project_title(proposal) is True
    assert proposal["intent"]["title"] == "Commerce Launch System"
    assert proposal["intent"]["project_slug"] == "commerce-launch-system"
    assert proposal["diagrams"][0]["summary"] == "Commerce Launch System proof."


def test_diagram_proof_reference_uses_an_existing_backlog_workstream() -> None:
    proposal = {
        "backlog": [
            {"title": "Govern Commerce Launch System"},
            {"title": "Define Storefront Boundary"},
            {"title": "Define Catalog Boundary"},
            {"title": "Prepare Catalog Release Proof"},
        ]
    }
    rows = [
        {"related_workstream_titles": ["Govern Commerce Launch System", "Define Storefront Boundary", "Define Catalog Boundary"]},
        {"related_workstream_titles": ["Define Storefront Boundary", "Define Catalog Boundary"]},
        {"related_workstream_titles": ["Define Storefront Boundary", "Define Catalog Boundary", "Prepare Catalog Release Proof"]},
        {"related_workstream_titles": ["Define Catalog Boundary"]},
        {"related_workstream_titles": ["Define Catalog Boundary", "Prepare Catalog Release Proof"]},
        {"related_workstream_titles": ["Prepare Catalog Release Proof"]},
    ]

    assert _diagram_workstream_titles(rows=rows, proposal=proposal) == {
        "parent": "Govern Commerce Launch System",
        "workflow": "Define Storefront Boundary",
        "boundary": "Define Catalog Boundary",
        "proof": "Prepare Catalog Release Proof",
    }


def test_diagram_component_copy_does_not_repeat_a_boundary_suffix() -> None:
    assert _component_review_sentence(
        label="Catalog Boundary",
        subject="catalog state",
        kind="service",
    ).startswith("The Catalog Boundary must show")
