- Bug ID: CB-230

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A KeyboardInterrupt or SystemExit raised after the atomic temp file was created bypassed temp cleanup, so governed target rollback could report success while a random sibling .tmp file remained outside the sealed write set.

- Impact: Post-confirm failure could leave undeclared filesystem residue despite a rolled-back receipt, weakening all-or-nothing transaction custody.

- Components Affected: domain-intelligence

- Environment(s): 0.1.15 source-local ProductCreateTransaction commit path on branch 2026/freedom/v0.1.15

- Detected By: Independent adversarial post-confirm call-graph and interruption probe

- Failure Signature: atomic_write_bytes catches Exception but not KeyboardInterrupt/SystemExit; target restores while .INDEX.md.<random>.tmp remains

- Trigger Path: Interrupt atomic_write_bytes after temp payload fsync begins during apply_compiled_greenfield_repository_write_set

- Ownership: Shared atomic filesystem helper and ProductCreateTransaction rollback boundary

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Any interrupted sealed file write using atomic_write_text or atomic_write_bytes

- SLO/SLA Impact: No latency breach; deterministic post-confirm success and rollback guarantees are violated

- Data Risk: Final governed paths roll back, but undeclared temp bytes can remain on disk

- Security/Compliance: Security: a temp sibling can retain governed content outside the sealed write set. Compliance and policy: rollback evidence becomes incomplete. Privacy, accessibility, and safety: no direct user-facing impact was observed beyond the retained local residue.

- Invariant Violated: Rollback must restore every affected path and leave no unsealed write residue

- Root Cause: Shared atomic helpers cleaned temp files only for Exception, excluding BaseException interruption classes handled by the transaction rollback contract

- Solution: Clean atomic temp siblings for every BaseException before re-raising; retain affected-path rollback for final targets

- Rollback/Forward Fix: Forward fix in the current B-142 checkpoint

- Verification: Real atomic-write interruption after temp creation leaves the original target intact and zero matching temp siblings. The final current-source 13-case compile/create matrix passed in 698.98 seconds. Fresh installed dist 9606871db then passed all 14 standard cases, browser proof 14/14, platform-leakage proof, zero temporary-root cleanup residue, and both rescue paths.

- Prevention: Keep a real temp-creation interruption regression, not only a monkeypatched pre-write failure

- Agent Guardrails: Do not infer clean rollback from final-path restoration alone; inspect sibling temp artifacts

- Preflight Checks: Run atomic interruption and transaction rollback tests before packaged commit-only proof

- Regression Tests Added: test_atomic_write_removes_temp_sibling_when_interrupted_after_write

- Monitoring Updates: Installed matrix cleanup proof must include zero temporary project roots and no write residue

- Version/Build: 0.1.15 fresh installed dist 9606871db

- Config/Flags: Default commit-only transaction path

- Customer Comms: None; caught before release

- Related Incidents/Bugs: CB-229

- Fixed In: 0.1.15 release proof verified; shipment pending

- Code References: - src/odylith/install/fs.py
- src/odylith/runtime/domain_intelligence/greenfield_repository_write_set.py
- src/odylith/runtime/domain_intelligence/greenfield_transaction.py
- tests/unit/runtime/test_greenfield_repository_write_set.py
