- Bug ID: CB-337

- Status: Open

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Always

- Type: Test

- Description: The graph-authority migration updated installed Greenfield guidance to the host-authored Semantic Intent packet and deterministic verification contract, but install tests still assert the retired Odylith-compiles-typed-evidence command-rail wording. Full development validation therefore fails on unchanged baseline assertions even though the installed guidance matches the current architecture.

- Impact: Operational release risk: blocks the full release gate and can pressure maintainers to restore obsolete guidance that misstates semantic ownership.

- Components Affected: odylith

- Environment(s): Odylith product-repo detached source-local validation on branch 2026/freedom/greenfield-radar-opportunity-custody

- Detected By: make dev-validate shard 1 after 199 passing tests

- Failure Signature: test_install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle expected compiles typed evidence in installed odylith/AGENTS.md

- Trigger Path: make dev-validate -> tests/integration/install/test_manager.py::test_install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle

- Ownership: install guidance contract tests and Semantic Intent graph-authority migration

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Fresh-install and upgrade guidance test lanes; release validation attribution

- SLO/SLA Impact: Release delivery SLO is blocked until stale expectations are migrated.

- Data Risk: No customer-data loss risk; test-contract drift only.

- Security/Compliance: Security posture is unchanged and compliance gates remain fail-closed.

- Invariant Violated: Install guidance tests must assert the current public Greenfield architecture and must not require retired semantic ownership wording.

- Root Cause: Commit 555f72917 moved installed guidance from Odylith-owned semantic compilation to host-authored Semantic Intent plus deterministic verification but did not migrate all install assertions.

- Solution: Replace only retired wording assertions with exact current host-reasoning, source-cited packet, independent challenge, deterministic verification, no-regex/no-retry, and transaction-boundary assertions.

- Rollback/Forward Fix: Forward-fix test contract; do not restore retired guidance.

- Verification: Run the exact failing integration node, unit bootstrap guidance test, install guidance bundle tests, then restart make dev-validate.

- Prevention: Require guidance-source and install-test contract migration in the same architecture cut.

- Agent Guardrails: Do not make a stale test pass by reviving a losing semantic mechanism or obsolete prose.

- Preflight Checks: Compare current and HEAD guidance/test history; prove mismatch predates this campaign.

- Regression Tests Added: Existing install guidance tests will be migrated to the current graph-authority contract.

- Related Incidents/Bugs: CB-301

- Code References: - src/odylith/install/bootstrap_assets.py
- src/odylith/bundle/assets/odylith/AGENTS.md
- tests/integration/install/test_manager.py
- tests/unit/install/test_manager.py
