- Bug ID: CB-192

- Status: Open

- Created: 2026-05-09

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A greenfield prompt for SMB lending with stablecoin funding to Shopify merchants produced child workstreams shaped like a generic first operator workflow and retail checkout recovery path instead of merchant-borrower, credit-liquidity, repayment, and regulated proof requirements.

- Impact: Consumer-lane operators saw B-002/B-003/B-004 records that could steer agents toward the wrong product domain before implementation planning.

- Components Affected: domain-intelligence

- Environment(s): Consumer greenfield proposal/apply path for docs-only repos, observed against v0.1.15 local release flow.

- Detected By: Operator QA on applied Radar workstream for SMB lending prompt.

- Failure Signature: B-002 title 'Define first operator workflow' plus shopper/cart/checkout/order/payment recovery language for a Shopify merchant lending/stablecoin prompt.

- Trigger Path: odylith greenfield propose/create --prompt 'SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify'

- Ownership: domain-intelligence greenfield proposal scaffold and workstream backlog row generation

- Timeline: Captured 2026-05-09 through `odylith bug capture`.

- Blast Radius: All domain-profiled greenfield prompts whose child backlog rows were still built from generic scaffold functions.

- SLO/SLA Impact: Greenfield time-to-correct-plan regressed because the first applied workstream required human correction before safe planning.

- Data Risk: No user data loss; product-domain truth risk because regulated lending requirements could be replaced by retail checkout assumptions.

- Security/Compliance: High compliance risk for lending, KYB/AML, stablecoin, no-custody, and production funding boundaries if generated workstreams use the wrong domain.

- Invariant Violated: Greenfield child workstreams must capture product-specific requirements and proof obligations from the inferred domain profile, not generic task shells.

- Root Cause: proposal_scaffold._workflow_backlog_row, _domain_backlog_row, and _verification_backlog_row ignored GreenfieldDomainProfile and emitted generic rows before domain intelligence enrichment attached the correct family metadata.

- Solution: Route backlog row generation through the inferred domain profile and emit merchant-lending, DeFi-risk, and commerce-specific child workstream titles, problems, product views, interfaces, and validation gates.

- Rollback/Forward Fix: Forward fix only; keep schema stable and strengthen generator/tests rather than rewriting applied consumer records from the product repo.

- Verification: PYTHONPATH=src python3 -m pytest tests/unit/runtime/test_greenfield_merchant_lending_profile.py tests/unit/runtime/test_greenfield_intelligence_schema.py tests/unit/runtime/test_greenfield_proposals.py -q

- Prevention: Regression tests assert merchant lending backlog titles and rendered proposal text do not contain shopper/checkout/cart/order/payment-sandbox leakage.

- Agent Guardrails: For greenfield prompts, evaluate product nouns first; do not accept generic B-002/B-003/B-004 shells when a domain profile has product-specific requirements.

- Preflight Checks: Generate the exact operator prompt and inspect backlog titles plus rendered proposal text before release packaging.

- Regression Tests Added: tests/unit/runtime/test_greenfield_merchant_lending_profile.py now asserts merchant-specific workstream titles and absence of checkout leakage.

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- tests/unit/runtime/test_greenfield_merchant_lending_profile.py
