- Bug ID: CB-102

- Status: Open

- Created: 2026-04-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: `odylith start --repo-root .` returns exit code 1 with
  `selection_state: none` and `selection_reason: "No workstream evidence
  matched the current changed-path set."` when the dirty path set is dominated
  by bundle asset mirror files rather than workstream-specific source code.
  The changed-path workstream inference cannot match a working in-progress
  workstream (e.g., B-083) through the bundle mirror paths alone, so the start
  command falls to a `gated_ambiguous` bootstrap packet with
  `ambiguity_class: no_candidates` instead of routing to the obvious active
  workstream.

- Impact: Agents following the AGENTS.md startup contract receive a
  degraded bootstrap packet and a fallback lane instead of the active
  workstream context. The `narrowing_required: true` guidance forces additional
  manual context lookup steps that should not be needed when a clear in-progress
  workstream is already active.

- Components Affected: `src/odylith/runtime/governance/workstream_inference.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `.odylith/bin/odylith` start command, changed-path to workstream evidence
  matching logic.

- Environment(s): Odylith product repo maintainer mode, branch
  `2026/freedom/v0.1.11`, dirty path set consisting entirely of bundle asset
  mirrors under `src/odylith/bundle/assets/odylith/` and managed surface files
  under `odylith/` (FAQ.md, INSTALL.md, INSTALL_AND_UPGRADE_RUNBOOK.md,
  README.md, atlas/, casebook/, compass/, radar/, registry/ bundle outputs).

- Root Cause: Changed-path workstream inference relies on matching dirty file
  paths against workstream evidence anchors. Bundle asset mirror paths
  (e.g., `src/odylith/bundle/assets/odylith/FAQ.md`) are not themselves
  workstream change-watch paths — the canonical source files are. When a broad
  sync or surface-render pass marks many bundle mirrors as dirty without
  touching any workstream-registered source paths, the inference returns
  `no_candidates` even though the active workstream is unambiguous from other
  signals (Compass context, recent session, plan status).

- Solution: Extend the start bootstrap to fall back to secondary workstream
  signals — recent session context, active Compass workstream, in-progress plan
  status — when changed-path matching returns `no_candidates` on a dirty tree
  that consists entirely of bundle mirror or managed surface output files.
  Alternatively, add bundle mirror root paths as weak-signal evidence anchors
  that contribute to, rather than determine, workstream selection.

- Verification: Reproduce by running `odylith start --repo-root .` on a branch
  where only bundle asset mirrors and managed surface files are dirty while an
  in-progress workstream plan exists. Confirm `selection_state: none` is
  returned. Fix is verified when the start command returns the active workstream
  context even in this dirty-path condition.

- Prevention: Workstream inference must have at least one secondary signal path
  that activates when changed-path matching produces `no_candidates` on a
  known bundle-mirror or surface-output dirty tree pattern.

- Detected By: Running `odylith start --repo-root .` during B-083 Atlas diagram
  authoring on 2026-04-11, with branch `2026/freedom/v0.1.11` carrying a broad
  sync-pass dirty tree.

- Failure Signature: `odylith start` returns exit code 1, `selection_state: none`,
  `ambiguity_class: no_candidates`, and `narrowing_required: true` despite an
  active in-progress workstream and a non-empty dirty path set.

- Trigger Path: Any `odylith start` invocation after a broad surface sync or
  bundle render pass that marks managed output files dirty without touching
  the workstream-registered source files.

- Ownership: `workstream_inference.py`, `odylith_context_engine.py`, start
  bootstrap signal resolution.

- Blast Radius: Every agent turn that follows the `odylith start` startup
  contract on a repo with a broad dirty surface tree. Affected agents receive a
  fallback bootstrap instead of an active workstream packet, increasing the
  chance of ungrounded repo scan as the first action.

- SLO/SLA Impact: No data loss. Workflow degradation — agents must run a manual
  `odylith context <ref>` step to recover grounding that the start command
  should have provided automatically.

- Data Risk: Low.

- Security/Compliance: Low.

- Invariant Violated: `odylith start` should resolve to the active workstream
  when one is unambiguous from Compass, session, or plan signals, regardless of
  whether the dirty path set contains workstream-registered source files.

- Workaround: Run `./.odylith/bin/odylith context --repo-root . <workstream-id>`
  explicitly after a failed start to recover the active workstream packet.

- Rollback/Forward Fix: Forward fix — extend start bootstrap to use secondary
  signals when changed-path matching returns no_candidates.

- Agent Guardrails: If `odylith start` returns `selection_state: none`, run
  `odylith context --repo-root . <ref>` with the known active workstream id
  before proceeding to raw repo scan.

- Preflight Checks: Before diagnosing a no-candidates result as a real routing
  gap, confirm the dirty path set is dominated by bundle mirrors or managed
  output files and not by workstream-registered source files.

- Regression Tests Added: None yet. Add to
  `tests/unit/runtime/test_workstream_inference.py` a case where all dirty
  paths are bundle mirror paths and an active in-progress plan exists; assert
  that the start bootstrap resolves the active workstream via secondary signals.

- Monitoring Updates: Watch for `selection_state: none` in start bootstrap
  output on branches with broad surface-sync dirty trees.

- Residual Risk: Until fixed, agents on bundle-heavy dirty branches must run an
  explicit `odylith context` step to ground each session.

- Related Incidents/Bugs: None directly. Related to the broader B-083
  Claude guidance surface work that triggered the dirty-tree condition.

- Version/Build: Odylith product repo branch `2026/freedom/v0.1.11`,
  2026-04-11.

- Config/Flags: Reproduced with standard `odylith start --repo-root .` on the
  product repo with no special flags.

- Customer Comms: N/A — internal product repo maintainer tooling.

- Code References: `src/odylith/runtime/governance/workstream_inference.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine.py`

- Runbook References: `AGENTS.md`, `odylith/AGENTS.md`,
  `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`

- Fix Commit/PR: Pending.
