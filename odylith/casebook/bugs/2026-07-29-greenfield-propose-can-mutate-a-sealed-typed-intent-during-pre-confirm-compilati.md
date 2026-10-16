- Bug ID: CB-298

- Status: Open

- Created: 2026-07-29

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: A normal EDIT flow stages a typed Product Intent and seals its authority, but deterministic proposal completion can change proposal.intent before transaction creation. Strict authority binding then rejects the package, so the user receives a pre-confirm error instead of a creation-ready preview.

- Impact: A normal prompt plus a plain-language EDIT cannot reach CONFIRM despite having sufficient product evidence.

- Components Affected: greenfield-preconfirm-compiler

- Environment(s): Product-repo source-local CLI verification

- Detected By: Greenfield CLI path suite and direct propose reproduction

- Failure Signature: ProductCreateTransaction proposal facts do not match its sealed Product Intent authority

- Trigger Path: propose -> materialize typed intent -> deterministic completion -> compile transaction

- Ownership: Greenfield pre-confirm compiler

- Timeline: Observed during CLI/source-bundle proof after fixture-only authority repairs passed.

- Blast Radius: Any proposal whose deterministic completion repairs or enriches typed intent after candidate authority creation

- SLO/SLA Impact: Blocks the main pre-confirm transaction flow and prevents a usable confirmation preview

- Data Risk: No governed write occurs; the strict authority check fails closed before CONFIRM

- Security/Compliance: Sealed custody requires the final transaction facts to match the reviewed authority; silent post-seal semantic mutation breaks audit integrity.

- Invariant Violated: All typed-intent normalisation and deterministic completion must finish before authority sealing and transaction compilation.

- Workaround: None for a user; do not ask for schema-shaped input or a second confirmation.

- Root Cause: The compiler accepts a sealed candidate intent but later completion writes derived facts back into proposal.intent without rebuilding the pre-confirm authority at the correct boundary.

- Solution: Move typed intent completion before the authority seal, or preserve authority-bound intent as immutable through proposal compilation; do not weaken the strict binding.

- Rollback/Forward Fix: No rollback needed because no governed write happens; forward-fix pre-confirm ordering and keep fail-closed verification.

- Verification: Reproduce the visible-result EDIT flow, then run CLI/source-bundle, custody, browser, and installed matrices.

- Prevention: Assert proposal product_facts_sha256 still equals authority after every pre-confirm compiler stage before creating the transaction.

- Agent Guardrails: Never repair typed Product Intent after its authority is sealed; EDIT must rebuild a fresh package before showing CONFIRM.

- Preflight Checks: Compare final proposal intent facts hash with authority before serialising the transaction preview.

- Regression Tests Added: CLI visible-result EDIT regression and confirmed-intent file flows cover the user path.

- Monitoring Updates: Casebook record tracks the pre-confirm authority drift until release proof completes.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals.py
