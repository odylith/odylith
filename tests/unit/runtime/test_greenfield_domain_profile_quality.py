from __future__ import annotations

import json
import re

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals


CASES = [
    {
        "name": "merchant_lending",
        "prompt": "draft a greenfield proposal for a SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify",
        "must": ("merchant", "shopify", "stablecoin", "underwriting", "liquidity", "repayment"),
        "labels": ("Merchant Capital Portal", "Credit And Liquidity Core", "Lending Proof Harness"),
        "forbidden": ("shopper", "cart", "checkout", "storefront", "payment sandbox", "order draft"),
        "family": "defi_merchant_lending",
    },
    {
        "name": "defi_risk_sentinel",
        "prompt": "draft a greenfield proposal for a DeFi risk sentinel app",
        "must": ("wallet", "protocol", "oracle", "liquidity", "alert", "watchlist"),
        "labels": ("Risk Sentinel Console", "Risk Signal Engine", "Scenario Replay Harness"),
        "forbidden": ("shopify", "merchant borrower", "checkout", "storefront"),
        "family": "defi_risk",
    },
    {
        "name": "clinical_trial_matching",
        "prompt": "draft a greenfield proposal for a clinical trial patient matching app for oncology coordinators",
        "must": ("patient", "trial", "protocol", "consent", "eligibility", "oncology"),
        "labels": ("Patient Match Review Workbench", "Eligibility Protocol Engine", "Trial Matching Proof Harness"),
        "forbidden": ("defi", "shopify", "checkout", "stablecoin", "robot"),
        "family": "clinical_trial_matching",
    },
    {
        "name": "immigration_legal_intake",
        "prompt": "draft a greenfield proposal for an immigration legal intake app for attorneys and clients",
        "must": ("immigration", "client", "document", "attorney", "consent", "case"),
        "labels": ("Client Intake Workspace", "Case Eligibility And Document Core", "Confidential Intake Proof Harness"),
        "forbidden": ("defi", "shopify", "checkout", "stablecoin", "robot"),
        "family": "legal_intake",
    },
    {
        "name": "bioinformatics_variant_pipeline",
        "prompt": "draft a greenfield proposal for a bioinformatics variant analysis pipeline for clinical genomics",
        "must": ("sample", "variant", "vcf", "qc", "sequencing", "reference"),
        "labels": ("Variant Review Workbench", "Sequencing Analysis Core", "Pipeline Reproducibility Harness"),
        "forbidden": ("defi", "shopify", "checkout", "stablecoin", "robot"),
        "family": "bioinformatics_variant_pipeline",
    },
    {
        "name": "statistics_notebook_generic",
        "prompt": "Build a statistics notebook repo",
        "must": ("statistics notebook", "product model", "evidence harness", "operator workspace"),
        "labels": (
            "A Statistics Notebook Repo Operator Workspace",
            "A Statistics Notebook Repo Product Model",
            "A Statistics Notebook Repo Evidence Harness",
        ),
        "forbidden": ("Domain Core", "Verification Harness", "Experience Boundary", "shopify", "checkout"),
        "family": "generic",
    },
]

SURFACE_TERMS = (
    "Radar",
    "Registry",
    "Atlas",
    "Compass",
    "Odylith surfaces",
    "governance surfaces",
    "governance records",
    "surface refresh",
    "refreshed surfaces",
)

GENERIC_COMPONENT_TERMS = ("Experience Boundary", "Domain Core", "Verification Harness")


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_greenfield_profiles_capture_prompt_specific_domain_without_surface_leaks(tmp_path, case) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=case["prompt"],
    )["proposal_template"]

    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed

    text = greenfield_proposals.format_proposal_text(proposal)
    artifact = json.dumps(proposal, sort_keys=True)
    diagrams = "\n".join(str(row.get("mermaid_source", "")) for row in proposal["diagrams"])
    combined = "\n".join((text, artifact, diagrams))

    for token in case["must"]:
        assert _has_token(combined, token), token
    for label in case["labels"]:
        assert label in combined
    for token in case["forbidden"]:
        assert not _has_token(combined, token), token
    for token in SURFACE_TERMS:
        assert token not in text
        assert token not in diagrams
    for token in GENERIC_COMPONENT_TERMS:
        assert token not in text
        assert token not in diagrams
    assert "atlas_first_draft" not in artifact

    families = {row["domain_intelligence"]["family"] for row in proposal["backlog"]}
    assert families == {case["family"]}


def test_robot_swarm_greenfield_keeps_robot_domain_language_without_surface_leaks(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="draft a greenfield proposal for a robot swarm logistics app for warehouse picking",
    )["proposal_template"]

    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed

    text = greenfield_proposals.format_proposal_text(proposal)
    artifact = json.dumps(proposal, sort_keys=True)
    diagrams = "\n".join(str(row.get("mermaid_source", "")) for row in proposal["diagrams"])
    combined = "\n".join((text, artifact, diagrams))

    for token in ("robot", "fleet", "dispatch", "conflict", "telemetry", "warehouse"):
        assert _has_token(combined, token), token
    for label in ("Fleet Operations Console", "Robot Coordination Core", "Simulation And Safety Harness"):
        assert label in combined
    for token in ("shopify", "checkout", "stablecoin", "patient"):
        assert not _has_token(combined, token), token
    for token in SURFACE_TERMS:
        assert token not in text
        assert token not in diagrams
    assert "atlas_first_draft" not in artifact
    assert len(proposal["diagrams"]) == 10


def _has_token(text: str, token: str) -> bool:
    lowered = text.casefold()
    needle = token.casefold()
    if " " in needle or "-" in needle:
        return needle in lowered
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lowered) is not None
