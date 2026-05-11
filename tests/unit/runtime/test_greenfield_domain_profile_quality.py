from __future__ import annotations

import json
import re

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues


CASES = [
    {
        "name": "defi_risk_sentinel",
        "prompt": "draft a greenfield proposal for a DeFi risk sentinel app",
        "must": ("wallet", "protocol", "oracle", "liquidity", "alert", "watchlist"),
        "labels": ("Risk Sentinel Console", "Risk Signal Engine", "Scenario Replay Harness"),
        "forbidden": ("checkout", "storefront", "patient intake"),
        "family": "defi_risk",
    },
    {
        "name": "merchant_capital_lending",
        "prompt": "draft a greenfield proposal for a SMB lending application pulling stable coins from DeFi protocols into a merchant on Shopify",
        "must": ("merchant", "funding", "underwriting", "treasury", "repayment", "stablecoin"),
        "labels": ("Merchant Funding Workspace", "Underwriting And Facility Core", "Funding Evidence Harness"),
        "forbidden": ("checkout", "cart", "shopper", "storefront"),
        "family": "capital_merchant_lending",
    },
    {
        "name": "clinical_trial_matching",
        "prompt": "draft a greenfield proposal for a clinical trial patient matching app for oncology coordinators",
        "must": ("patient", "trial", "protocol", "consent", "eligibility", "oncology"),
        "labels": ("Patient Match Review Workbench", "Eligibility Protocol Engine", "Trial Matching Proof Harness"),
        "forbidden": ("defi", "checkout", "robot"),
        "family": "clinical_trial_matching",
    },
    {
        "name": "immigration_legal_intake",
        "prompt": "draft a greenfield proposal for an immigration legal intake app for attorneys and clients",
        "must": ("immigration", "client", "document", "attorney", "consent", "case"),
        "labels": ("Client Intake Workspace", "Case Eligibility And Document Core", "Confidential Intake Proof Harness"),
        "forbidden": ("defi", "checkout", "robot"),
        "family": "legal_intake",
    },
    {
        "name": "bioinformatics_variant_pipeline",
        "prompt": "draft a greenfield proposal for a bioinformatics variant analysis pipeline for clinical genomics",
        "must": ("sample", "variant", "vcf", "qc", "sequencing", "reference"),
        "labels": ("Variant Review Workbench", "Sequencing Analysis Core", "Pipeline Reproducibility Harness"),
        "forbidden": ("defi", "checkout", "robot"),
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
        "forbidden": ("Domain Core", "Verification Harness", "Experience Boundary", "checkout"),
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

UNPROFILED_CASES = [
    (
        "quantum chemistry catalyst screening platform",
        ("quantum", "chemistry", "catalyst", "screening"),
    ),
    (
        "city zoning permit review app",
        ("city", "zoning", "permit", "review"),
    ),
    (
        "carbon credit MRV ledger for forestry projects",
        ("carbon", "credit", "mrv", "forestry"),
    ),
    (
        "teacher lesson plan co-pilot",
        ("teacher", "lesson", "plan"),
    ),
    (
        "wind farm predictive maintenance console",
        ("wind", "farm", "predictive", "maintenance"),
    ),
    (
        "food safety recall traceability system",
        ("food", "safety", "recall", "traceability"),
    ),
]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_greenfield_profiles_capture_prompt_specific_domain_without_surface_leaks(tmp_path, case) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=case["prompt"],
    )["proposal_template"]

    assert "Greenfield Proposal For" not in proposal["intent"]["title"]
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


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_greenfield_cases_pass_product_manager_relevance_filter(tmp_path, case) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=case["prompt"],
    )["proposal_template"]

    assert proposal["artifact_derivation"]["root"] == "project_intelligence"
    assert greenfield_quality_issues(proposal) == []
    project_title = str(proposal["intent"]["title"])
    forbidden_preparation_phrases = (
        "accepted execution spine",
        "created as a new queued workstream",
        "deeper scope decomposition waits",
        "implementation owner starts",
        "before source exists",
        "follow-on implementation planning",
    )

    for row in proposal["backlog"]:
        joined = json.dumps(row, sort_keys=True)
        assert row["project_intelligence_binding"]["source"] == "project_intelligence"
        assert any(_has_token(joined, token) for token in case["must"]), row["title"]
        for phrase in forbidden_preparation_phrases:
            assert phrase not in joined
        if case["family"] != "generic":
            assert project_title not in row["problem"]
            assert project_title not in row["product_view"]

    for component in proposal["components"]:
        joined = json.dumps(component, sort_keys=True)
        assert component["project_intelligence_binding"]["source"] == "project_intelligence"
        assert any(_has_token(joined, token) for token in case["must"]), component["label"]

    diagram_payload = "\n".join(json.dumps(diagram, sort_keys=True) for diagram in proposal["diagrams"])
    assert any(label in diagram_payload for label in case["labels"])
    for diagram in proposal["diagrams"]:
        joined = json.dumps(diagram, sort_keys=True)
        assert diagram["project_intelligence_binding"]["source"] == "project_intelligence"


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
    for token in ("checkout", "patient"):
        assert not _has_token(combined, token), token
    for token in SURFACE_TERMS:
        assert token not in text
        assert token not in diagrams
    assert "atlas_first_draft" not in artifact
    assert len(proposal["diagrams"]) == 10


@pytest.mark.parametrize(("prompt", "tokens"), UNPROFILED_CASES)
def test_unprofiled_greenfield_prompts_still_get_project_specific_workstreams(tmp_path, prompt, tokens) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=f"draft a greenfield proposal for a {prompt}",
    )["proposal_template"]

    assert greenfield_quality_issues(proposal) == []
    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed

    text = greenfield_proposals.format_proposal_text(proposal)
    diagrams = "\n".join(str(row.get("mermaid_source", "")) for row in proposal["diagrams"])
    combined = "\n".join((text, diagrams))

    for token in tokens:
        assert _has_token(combined, token), token
    for row in proposal["backlog"][1:]:
        assert row["title"] not in {
            "Prove first product workflow",
            "Define first domain contract",
            "Prove release harness",
            "Define first operator workflow",
            "Define domain contract and ownership",
            "Add release proof and operations harness",
        }
        assert any(_has_token(json.dumps(row, sort_keys=True), token) for token in tokens)
    for component in proposal["components"]:
        assert component["label"] not in {"Operator Workspace", "Product Model", "Evidence Harness"}
        assert any(_has_token(json.dumps(component, sort_keys=True), token) for token in tokens)
    for token in SURFACE_TERMS + GENERIC_COMPONENT_TERMS:
        assert token not in text
        assert token not in diagrams


def test_greenfield_quality_gate_rejects_control_plane_and_generic_workstream_leaks(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="draft a greenfield proposal for a city zoning permit review app",
    )["proposal_template"]
    proposal["backlog"][1]["title"] = "Define first operator workflow"
    proposal["backlog"][1]["product_view"] = "Radar, Registry, Atlas, and Compass should drive the app workstream."
    proposal["components"][0]["label"] = "Experience Boundary"
    proposal["diagrams"][0]["mermaid_source"] += "  Leak[Odylith surfaces<br/>Radar Registry Atlas Compass]:::note\n"

    issues = greenfield_quality_issues(proposal)

    assert any("Radar" in issue for issue in issues)
    assert any("Experience Boundary" in issue for issue in issues)
    assert any("Define first operator workflow" in issue for issue in issues)


def _has_token(text: str, token: str) -> bool:
    lowered = text.casefold()
    needle = token.casefold()
    if " " in needle or "-" in needle:
        return needle in lowered
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lowered) is not None
