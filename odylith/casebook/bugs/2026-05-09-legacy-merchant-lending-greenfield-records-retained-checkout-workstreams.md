- Bug ID: CB-193

- Status: Open

- Created: 2026-05-09

- Severity: P1

- Reproducibility: Consistent

- Type: UX

- Description: Legacy merchant-lending greenfield records retained checkout workstreams

- Impact: Already-applied Shopify stablecoin SMB lending proposals could keep B-002/B-003/B-004 as shopper checkout, cart, order draft, payment callback, and checkout proof workstreams after fresh-generation fixes, causing agents to plan the wrong product.

- Components Affected: domain-intelligence

- Environment(s): consumer greenfield repo upgraded to v0.1.15 after applying the legacy checkout-shaped merchant-lending scaffold

- Detected By: operator transcript showing B-002 and B-003 rendered as retail checkout workstreams for SMB lending

- Failure Signature: Radar workstreams named Define first operator workflow and Define domain contract and ownership contain shopper, checkout, cart, order draft, payment callback, storefront, checkout-order-core, and checkout-proof-harness language for an SMB lending stablecoin Shopify merchant prompt.

- Trigger Path: odylith greenfield create --prompt 'SMB lending application pulling stable coins from DeFi protocols to merchants on Shopify' --confirm on the bad scaffold, then upgrade/sync

- Ownership: domain-intelligence greenfield scaffold plus legacy backlog normalization

- Timeline: Captured 2026-05-09 through `odylith bug capture`.

- Blast Radius: consumer repos that already applied the misclassified merchant-lending checkout scaffold

- SLO/SLA Impact: High onboarding correctness risk; first technical plans start from the wrong borrower, money-state, and proof model.

- Data Risk: No production data loss; repo-owned governance truth can be semantically poisoned until repaired.

- Security/Compliance: Regulated lending posture can be under-modeled if old checkout/payment semantics hide KYB, AML, liquidity, custody, disbursement, and repayment gates.

- Invariant Violated: Greenfield workstreams must capture product-specific requirements and must not preserve retail-commerce semantics for merchant-lending prompts.

- Root Cause: Fresh-generation hardening did not include an upgrade/sync repair for already-applied consumer Radar records.

- Solution: Add a narrow backlog-normalization repair that detects merchant-lending intent plus retail-checkout leakage and rewrites legacy workstreams to merchant borrower workflow, credit-liquidity contract, and lending proof harness requirements.

- Rollback/Forward Fix: Forward fix only: rewrite poisoned legacy records in place during normalization; do not touch unrelated commerce workstreams or valid merchant-lending records.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_greenfield_merchant_lending_profile.py tests/unit/runtime/test_greenfield_legacy_repairs.py; broader greenfield/CLI, migration, and browser suites.

- Prevention: Keep fresh-generation tests and legacy-repair migration tests paired for each greenfield domain-family correction.

- Agent Guardrails: Do not stop at fresh proposal output; inspect already-applied governance records and add upgrade/sync repair for poisoned project truth.

- Preflight Checks: Search existing Radar workstreams for merchant-lending intent combined with shopper/checkout/cart/order/payment leakage before claiming the fix covers installed repos.

- Regression Tests Added: tests/unit/runtime/test_greenfield_legacy_repairs.py and strengthened merchant-lending proposal leakage assertions.

- Monitoring Updates: Release migration observer marker migration-observer:0.1.15:operator-cli-contracts:13e8531fb4af records the upgrade impact assessment.

- Version/Build: 0.1.15 local release candidate

- Config/Flags: provider-free greenfield proposal/create path

- Customer Comms: Tell affected local testers to upgrade and run odylith sync --repo-root . --force if they already applied the bad scaffold.

- Related Incidents/Bugs: CB-190, CB-191, CB-192

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/governance/greenfield_legacy_repairs.py
- src/odylith/runtime/governance/legacy_backlog_normalization.py
- tests/unit/runtime/test_greenfield_legacy_repairs.py
