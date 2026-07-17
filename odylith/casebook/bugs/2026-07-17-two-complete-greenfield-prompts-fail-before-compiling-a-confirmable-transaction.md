- Bug ID: CB-274

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The installed pre-confirm matrix accepted twelve transaction-ready cases but converted two legitimate `clarification_required` replies into an opaque missing-transaction error. The CLI correctly kept both ambiguous first-path requests no-write; the matrix failed to preserve that outcome. Its browser-proof summary also initially treated the intentional absence of generated surfaces as a failed skipped commit, then needed to bind the exemption to the passed no-write contract.

- Impact: Release diagnostics misrepresented a valid consumer interaction as a transaction failure, obscuring whether a true post-confirm or pre-confirm defect existed.

- Components Affected: domain-intelligence

- Environment(s): Fresh full install of 0.1.15 candidate in the installed pre-confirm and commit-only matrix

- Detected By: Fresh installed-runtime 14-case matrix with browser and rescue coverage

- Failure Signature: `_run_compiled_greenfield_create` replaced a successful `clarification_required` payload with `greenfield propose did not return a ProductCreateTransaction hash and transaction file`. After that routing fix, browser proof emitted `browser proof skipped because commit-only create did not pass` for the same valid no-write path. The first exemption implementation could label a failed no-write clarification `not_applicable` because it only inspected browser fields.

- Trigger Path: Run make greenfield-preconfirm-matrix VERSION=0.1.15 DIST=/tmp/odylith-v0.1.15-kernel-acceptance.

- Ownership: Greenfield installed acceptance matrix and product-intent materiality boundary

- Timeline: Captured 2026-07-17 from fresh installed matrix after twelve other high-variance cases passed.

- Blast Radius: Any unannotated transaction-expected matrix case that legitimately needs one material clarification

- SLO/SLA Impact: Release diagnosis fails closed with misleading evidence, delaying a correct quality decision.

- Data Risk: No known data loss; clarification occurs before any governed write.

- Security/Compliance: Security and policy risk: disclosure and embargo workflows require a user-facing focused question when material, never an opaque failure; no external security exposure is known.

- Invariant Violated: Material ambiguity receives one meaningful no-write clarification before confirmation, and acceptance evidence must preserve that result without inventing a transaction error.

- Workaround: Mark the case `clarification_required` when it intentionally lacks a determinative first path.

- Root Cause: The matrix wrapper required every successful proposal response to contain a transaction hash and file, without recognizing the CLI's first-class `clarification_required` response mode.

- Solution: Preserve the original clarification payload in unexpected transaction-expected cases and classify the two intentionally ambiguous corpus cases as discovery-only `clarification_required` no-write proof. Browser proof reports a clarification case as `not_applicable` only when its no-write quality verdict passed and no browser attempt or browser issue exists; any contrary activity fails closed.

- Rollback/Forward Fix: Forward fix required; do not relax post-confirm checks or bypass pre-confirm quality validation.

- Verification: Matrix unit tests prove preservation of the clarification payload, expected no-write case routing, and fail-closed browser classification, including a failed no-write contract; fresh installed discovery proof must show the two structured clarifications without a create attempt or browser surface proof.

- Prevention: Acceptance wrappers must branch on proposal mode before requiring transaction fields. Release proof remains transaction-only, discovery proof retains clarification evidence, and browser proof must distinguish an absent generated surface from a failed no-write contract or missing required surface validation.

- Agent Guardrails: Do not force ambiguous prompts through compilation and do not relabel a structured clarification as a transaction failure.

- Preflight Checks: Run matrix clarification-routing tests and installed discovery proof before release proof.

- Monitoring Updates: Matrix output retains the original clarification payload, no-write evidence, and the absence of a create command.

- Version/Build: 0.1.15 local release candidate

- Config/Flags: full install; discovery proof with rescue, natural-rescue, and browser enabled

- Customer Comms: No customer communication needed; caught before release.

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_preconfirm_matrix.py
- scripts/release/greenfield_preconfirm_matrix_cases.py
- scripts/release/greenfield_browser_proof_summary.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py
