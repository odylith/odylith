- Bug ID: CB-301

- Status: InProgress

- Created: 2026-08-01

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: Fresh install compact guidance omitted Greenfield commit-only boundary

- Impact: Operational and delivery risk: fresh local installs fail release smoke and receive an incomplete explanation of the post-CONFIRM execution boundary, blocking validated deployment handoff.

- Components Affected: odylith

- Environment(s): v0.1.15 local hosted-release assets built from 2eaa2b7d3 on macOS arm64

- Detected By: scripts/release/local_release_smoke.py fresh-install guidance validation

- Failure Signature: fresh install guidance omits proposal-first create commit-only no-work boundary: odylith/AGENTS.md

- Trigger Path: make local-release-assets VERSION=0.1.15 followed by local_release_smoke.py --version 0.1.15

- Ownership: Installer bootstrap guidance projection in src/odylith/install/bootstrap_assets.py

- Timeline: Captured 2026-08-01 through `odylith bug capture`. On 2026-08-02, the full maintainer gate proved that the authored bundle, compact consumer guidance generator, and repo-root managed block had drifted independently: the bundle omitted the exact commit-only sentence, the generated consumer tree used stale command wording, and product-root parity exceeded its 11.6 KB latency guard.

- Blast Radius: All fresh consumer installs generated through the compact repo guidance projection; release validation and first-use operator expectations are affected

- SLO/SLA Impact: Delivery SLO is blocked because a locally built distribution cannot pass the fresh-install smoke gate

- Data Risk: No observed product-data loss; incomplete guidance can cause operators to misunderstand when sealed product bytes are compiled versus committed

- Security/Compliance: Compliance, policy, privacy, accessibility, and safety assessment: no direct exposure observed, but the documented trust boundary is incomplete and must fail closed before distribution

- Invariant Violated: Every installed Greenfield guidance projection must state that CONFIRM performs no product reinterpretation, parsing, or generation

- Root Cause: The same Greenfield decision rail was maintained in the authored bundle, `bootstrap_assets.py`, `install/agents.py`, and repo-root scope block without one parity checkpoint covering all four outputs. A local edit could therefore repair one shipped surface while leaving generated clean installs stale. Accumulated policy narration also pushed the product scope to 12,827 bytes, so copying more text would have repeated the earlier latency failure.

- Failed Mechanism: Updating only `AGENTS.md`, `odylith/AGENTS.md`, the bundle mirror, or `install/agents.py` is incomplete. Raising the byte ceiling or weakening literal install assertions would hide drift rather than preserve the user-visible confirmation contract.

- Solution: Aligned the authored bundle and generated consumer guidance on explicit hash-bound `CONFIRM`, `EDIT`, and `REJECT` commands and the pending transaction path. Reconciled product `AGENTS.md` and Claude bridge generation with their authoritative root scope, retained shorter consumer-only safeguards, and compacted repeated product policy prose to 11,432 bytes while keeping the consumer block at 11,489 bytes. The product block retains the explicit frequent, informative Odylith Assist cadence requested by the operator.

- Verification: `.venv/bin/python -m pytest -q tests/integration/install/test_bundle.py::test_bundle_root_contains_installed_agents_entrypoint tests/integration/install/test_manager.py::test_install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle tests/unit/install/test_agents.py tests/unit/runtime/test_show_capabilities.py::test_managed_guidance_exempts_show_me_from_intervention_proof` passed 12 tests on 2026-08-02. The repository-wide fail-fast gate also caught and prevented an over-compaction that removed the explicit product-mode Assist cadence. Rebuilt-distribution and installed release-smoke proof remain required before this record can move to `FixedPendingRelease`.

- Prevention: Keep byte-level product-root and Claude-bridge parity tests, clean-install guidance assertions, authored bundle assertions, the frequent Assist cadence assertion, and the 11.6 KB managed-block budget in the same release gate. A Greenfield confirmation contract change is incomplete until all of those outputs pass together.
