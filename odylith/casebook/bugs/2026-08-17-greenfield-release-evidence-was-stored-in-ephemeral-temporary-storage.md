- Bug ID: CB-330

- Status: Open

- Created: 2026-08-17

- Severity: P1

- Reproducibility: Consistent

- Type: DataLoss

- Description: An environment refresh removed the private release worktree, immutable development plan and receipts, deterministic-law report, and the frozen untouched holdout because all were under /private/tmp.

- Impact: Release evidence could no longer be verified or reused; the complete cohort must be rerun and a new independently frozen holdout must be created.

- Components Affected: release

- Environment(s): Odylith Greenfield maintainer release lane using /private/tmp evidence paths

- Detected By: Deep session resume after environment refresh

- Failure Signature: Registered Git worktrees were prunable and every named /private/tmp evidence and holdout path was absent.

- Trigger Path: Environment cleanup between paused release sessions

- Ownership: Greenfield release evidence custody and holdout runner

- Timeline: Captured 2026-08-17 through `odylith bug capture`.

- Blast Radius: Development receipts, deterministic-law artifacts, worktree state, and untouched holdout evidence stored under ephemeral paths

- SLO/SLA Impact: Delivery risk: invalidated release evidence and delayed the final holdout gate.

- Data Risk: Operational data risk: maintainer release evidence was lost. No user-owned project or committed customer data was deleted.

- Security/Compliance: Evidence-provenance risk: missing artifacts cannot be reconstructed from hashes or treated as passed; no credential or customer-data exposure occurred.

- Invariant Violated: Immutable release evidence and untouched holdout custody must survive session and environment lifecycle until release completes.

- Workaround: Recreate the pushed branch in persistent storage, regenerate executable evidence, rerun fresh assignments, and create a new independent untouched holdout.

- Root Cause: The release process treated /private/tmp as durable evidence storage and lacked a preflight that rejects ephemeral worktree, development-plan, and holdout paths.

- Solution: Use a persistent release-evidence root, bind every artifact by canonical hash, reject ephemeral evidence locations before expensive runs, and retain the new holdout until final adjudication and cleanup.

- Rollback/Forward Fix: Forward-fix release evidence custody; never recreate missing evidence from remembered hashes.

- Verification: The c21 branch was restored under a persistent Codex worktree, deterministic laws were rerun, and a new 24-case plan and bundle were written under persistent evidence storage. Holdout replacement remains pending.

- Prevention: Add an evidence-root durability preflight to development and final-holdout runners and document terminal cleanup boundaries.

- Agent Guardrails: Never claim lost temporary receipts as valid evidence, never reuse their hashes as substitutes, and never place the replacement holdout under /private/tmp.

- Preflight Checks: Persistent path, filesystem existence, ownership, free space, non-ephemeral policy, clean revision, and absent run ledger.

- Version/Build: pre-release c21 successor

- Related Incidents/Bugs: CB-329

- Code References: - scripts/release/greenfield_semantic_development_cohort.py
- scripts/release/greenfield_final_holdout_run.py
