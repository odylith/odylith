- Bug ID: CB-340

- Status: Open

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Always

- Type: Test

- Description: After the Greenfield graph authority cutover, run_release_proof_steps correctly delegates installed smoke, browser, recovery, and holdout preflight to greenfield-graph-release-proof. The release bootstrap unit guard still asserted the removed direct local_release_smoke.py command and blocked the canonical validation corpus.

- Impact: Canonical maintainer validation fails even though the current graph-native release proof is wired correctly, delaying trustworthy release evidence and encouraging restoration of a superseded proof path.

- Components Affected: release

- Environment(s): Detached source-local maintainer worktree on 2026-08-18 during canonical dev-validate shard 5.

- Detected By: Fail-fast continuation of the canonical 4,399-test dev-validation corpus.

- Failure Signature: test_release_preflight_uses_isolated_temp_dist_dir expects scripts/release/local_release_smoke.py --version ... in bin/_odylith.sh, but the current helper delegates to bin/greenfield-graph-release-proof.

- Trigger Path: PYTHONPATH=src .venv/bin/python -m pytest -q -x tests/unit/install/test_release_bootstrap.py::test_release_preflight_uses_isolated_temp_dist_dir

- Ownership: Release preflight structural contract and graph-native release-proof rail.

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Maintainer dev-validation and any release bootstrap audit relying on the stale literal assertion.

- SLO/SLA Impact: Blocks release convergence but does not affect an already installed consumer runtime.

- Data Risk: No application or governance data is mutated by the failing assertion; the risk is false-negative release evidence.

- Security/Compliance: No direct exposure; stale proof assertions weaken confidence in release-boundary review.

- Invariant Violated: Structural release tests must enforce the current single proof owner and must not require a deleted mechanism.

- Root Cause: Commit 555f72917 moved local smoke under greenfield-graph-release-proof but did not migrate this literal release-bootstrap assertion.

- Solution: Assert the graph-proof command and temp-parent custody at run_release_proof_steps, and assert the retired direct local smoke invocation is absent from that function.

- Rollback/Forward Fix: Forward fix the stale test only; do not restore the direct smoke or duplicate release-proof ownership.

- Verification: Run the exact release-bootstrap node, then rerun canonical shard 5.

- Prevention: When authority moves, pair behavior deletion with a structural inventory that migrates all positive and negative tests for the old call boundary.

- Agent Guardrails: Do not satisfy stale structural tests by reinstating obsolete release mechanisms. Prove the replacement owner and absence of the losing path.

- Preflight Checks: Inspect git history for the authority move and verify greenfield-graph-release-proof still invokes local release smoke internally before changing assertions.

- Regression Tests Added: tests/unit/install/test_release_bootstrap.py::test_release_preflight_uses_isolated_temp_dist_dir

- Version/Build: Greenfield semantic graph source-local release candidate based on bf982b0e.

- Related Incidents/Bugs: CB-337

- Code References: - tests/unit/install/test_release_bootstrap.py
- bin/_odylith.sh
- bin/greenfield-graph-release-proof
