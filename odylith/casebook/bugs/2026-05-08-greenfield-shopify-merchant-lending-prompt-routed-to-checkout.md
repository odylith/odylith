- Bug ID: CB-190

- Status: Open

- Created: 2026-05-08

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A fresh greenfield prompt for SMB lending that pulls stablecoins from DeFi protocols to Shopify merchants was classified as generic commerce checkout because Shopify/commerce tokens dominated lending, merchant, stablecoin, and DeFi intent. The proposal and applied governance described shoppers, storefronts, carts, checkout-order core, payment sandbox, failed-payment recovery, and order drafts instead of merchant borrower workflow, credit facility, liquidity, stablecoin disbursement, repayment, and regulated lending posture.

- Impact: Greenfield governance truth can be wrong before implementation starts: Radar, Registry, Atlas, Compass, and release handoff steer agents toward shopper checkout rather than merchant lending.

- Components Affected: domain-intelligence

- Environment(s): Odylith v0.1.15 local dist consumer lane in an empty docs-only repo; reproduced source-local from the product repo on 2026-05-08.

- Detected By: Operator Claude transcript after local v0.1.15 install plus source-local reproduction with greenfield propose --format json.

- Failure Signature: Prompt 'SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify' emitted Commerce Storefront, Checkout And Order Core, Checkout Proof Harness, shopper/cart/order-draft/payment-sandbox ontology, and checkout-first project outcome.

- Trigger Path: odylith greenfield propose --repo-root . --prompt 'SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify'

- Ownership: Domain Intelligence greenfield domain profile, project brief, project intelligence, workstream intelligence, and proposal rendering.

- Timeline: 2026-05-08: operator installed v0.1.15 in a fresh repo, proposed SMB stablecoin lending for Shopify merchants, applied the proposal, and Claude flagged the generic shopper-checkout mismatch after governance writes.

- Blast Radius: Consumer greenfield proposal text/JSON, confirmed create/apply records, parent and child Radar workstreams, Registry component specs, Atlas diagram labels/context, Compass release handoff, and first technical-plan choice.

- SLO/SLA Impact: First-run project setup can burn minutes and send host agents into the wrong B-002 plan; low-latency canonical create still becomes harmful if the domain family is wrong.

- Data Risk: Sensitive Shopify merchant financial data, underwriting inputs, credit facility state, stablecoin liquidity, disbursement, repayment, and audit data were misclassified as shopper checkout/payment data.

- Security/Compliance: KYB, AML, sanctions, lending disclosures, money-transmission/securities review, no-custody, no-private-key, no-live-protocol, and stablecoin risk obligations were omitted or replaced by PCI/payment-provider posture.

- Invariant Violated: Greenfield domain intelligence must preserve primary actor, funding model, data boundary, proof obligations, and compliance posture; a Shopify token must not override lending plus DeFi plus merchant intent into ecommerce checkout.

- Root Cause: Domain profile inference matched commerce tokens before any merchant-lending family existed, and downstream project/workstream scaffolds had no first-class merchant-credit/liquidity/compliance vocabulary.

- Solution: Add a first-class defi_merchant_lending profile with merchant-capital portal, credit-liquidity core, lending proof harness, merchant lending project brief, workstream ontology/operators/validation, regulated risk/compliance posture, and proposal renderer visibility for stablecoin/DeFi and compliance choices.

- Rollback/Forward Fix: Forward fix only: route affected prompts to the new merchant-lending family and keep generic commerce behavior for true shopper checkout prompts.

- Verification: PYTHONPATH=src python3 -m pytest tests/unit/runtime/test_greenfield_merchant_lending_profile.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_greenfield_atlas_contract.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/install/test_local_release_smoke.py tests/unit/test_cli.py -q; source-local CLI propose/create for the transcript prompt passes Tribunal, writes Merchant Capital Portal, Credit And Liquidity Core, Lending Proof Harness, and contains no shopper, checkout, or payment-sandbox profile leakage.

- Prevention: Keep prompt-family precedence tests for mixed-domain prompts where integration surface words such as Shopify can otherwise dominate the real product intent.

- Agent Guardrails: When a proposal prompt names merchant lending, stablecoins, DeFi liquidity, or credit, hosts must review borrower, funding, repayment, and compliance posture before accepting any checkout/storefront scaffold.

- Preflight Checks: Before greenfield apply, inspect the proposal's primary actor, component labels, ontology, risks, and customization options for domain-family mismatch.

- Regression Tests Added: tests/unit/runtime/test_greenfield_merchant_lending_profile.py::test_shopify_stablecoin_merchant_lending_avoids_checkout_profile

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_domain_profile.py
- src/odylith/runtime/domain_intelligence/greenfield_project_brief.py
- src/odylith/runtime/domain_intelligence/greenfield_workstream_intelligence.py
