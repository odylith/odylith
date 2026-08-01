- Bug ID: CB-301

- Status: Open

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

- Timeline: Captured 2026-08-01 through `odylith bug capture`.

- Blast Radius: All fresh consumer installs generated through the compact repo guidance projection; release validation and first-use operator expectations are affected

- SLO/SLA Impact: Delivery SLO is blocked because a locally built distribution cannot pass the fresh-install smoke gate

- Data Risk: No observed product-data loss; incomplete guidance can cause operators to misunderstand when sealed product bytes are compiled versus committed

- Security/Compliance: Compliance, policy, privacy, accessibility, and safety assessment: no direct exposure observed, but the documented trust boundary is incomplete and must fail closed before distribution

- Invariant Violated: Every installed Greenfield guidance projection must state that CONFIRM performs no product reinterpretation, parsing, or generation
