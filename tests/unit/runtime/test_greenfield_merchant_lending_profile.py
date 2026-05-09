from __future__ import annotations

import json

from odylith.runtime.domain_intelligence import greenfield_proposals


PROMPT = "SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify"


def test_shopify_stablecoin_merchant_lending_avoids_checkout_profile(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=PROMPT,
    )["proposal_template"]
    text = greenfield_proposals.format_proposal_text(proposal)
    combined = json.dumps(proposal, sort_keys=True).casefold()

    components = {row["label"]: row for row in proposal["components"]}
    backlog_titles = [row["title"] for row in proposal["backlog"]]
    assert set(components) == {"Merchant Capital Portal", "Credit And Liquidity Core", "Lending Proof Harness"}
    assert "Define first operator workflow" not in backlog_titles
    assert "Define domain contract and ownership" not in backlog_titles
    assert "Add release proof and operations harness" not in backlog_titles
    assert "Prove merchant borrower application and funding-status workflow" in backlog_titles
    assert "Define credit facility, liquidity, and repayment contract" in backlog_titles
    assert "Prove merchant lending fixtures and regulated proof harness" in backlog_titles
    assert "should become a merchant-capital product" in proposal["project_brief"]["project_outcome"]
    assert "SMB borrower journey" in proposal["project_brief"]["project_outcome"]
    assert "Shopify merchant-data boundary" in proposal["project_brief"]["project_outcome"]
    assert "Merchant borrower:" in "\n".join(proposal["project_intelligence"]["ontology"])
    assert "Shopify commerce snapshot:" in "\n".join(proposal["project_intelligence"]["ontology"])
    assert "Stablecoin disbursement:" in "\n".join(proposal["project_intelligence"]["ontology"])
    assert "kyb" in combined
    assert "aml" in combined
    assert "repayment" in combined
    assert "liquidity shortfall" in combined
    assert "no live defi protocol calls" in combined
    assert "defi_merchant_lending" in combined
    assert "Stablecoin and DeFi liquidity posture" in text
    assert "Compliance and lending posture" in text

    forbidden_positive_checkout = [
        "commerce product whose first release proves the shopper path",
        "checkout-first path",
        "commerce storefront",
        "checkout and order core",
        "checkout proof harness",
        "payment sandbox only",
        "purchase path: browse",
        "browse -> cart",
        "cart: mutable shopper intent",
        "order draft:",
        "payment callback:",
        "shopper-facing flow",
    ]
    for phrase in forbidden_positive_checkout:
        assert phrase not in combined
        assert phrase not in text.casefold()
    assert "shopper" not in combined
    assert "cart" not in text.casefold()
    assert "checkout" not in text.casefold()
    assert "payment sandbox" not in text.casefold()
    for control_plane_phrase in (
        "governance records",
        "governance surfaces",
        "governed control surface",
        "Odylith assumptions",
        "Odylith owns",
        "Tribunal",
        "Control Surface",
        "proof surface",
        "app-surface",
        "Radar",
        "Registry",
        "Atlas",
        "Compass",
    ):
        assert control_plane_phrase not in text

    workflow = next(row for row in proposal["backlog"] if row["id"] == "WS-01")
    workflow_text = json.dumps(workflow, sort_keys=True).casefold()
    assert "merchant-borrower workflow" in workflow_text
    assert "shopify snapshot consent" in workflow_text
    assert "eligibility" in workflow_text
    assert "liquidity_blocked" in workflow_text
    assert "compliance_blocked" in workflow_text
    assert "repayment_due" in workflow_text
    assert "consumer retail" not in workflow_text
    assert "card-payment" not in workflow_text

    for row in proposal["backlog"]:
        assert row["domain_intelligence"]["family"] == "defi_merchant_lending"
        rendered = greenfield_proposals.render_domain_intelligence_section(row["domain_intelligence"])
        assert "Shopify merchant" in rendered
        assert "stablecoin" in rendered
        assert "checkout" not in rendered.casefold()
        assert "payment sandbox" not in rendered.casefold()

    assert "Agent-quality metric: no visible canonical-object patching loop" in text
    assert "schema-repair" not in text.casefold()
    assert "schema repair" not in text.casefold()
    assert "repair loop" not in text.casefold()
    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed
