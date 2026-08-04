- Bug ID: CB-321

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The release campaign claimed the one-shot final-holdout ledger and began product execution in an isolated uv environment that lacked Playwright. The first browser proof failed unavailable. SIGINT stopped the parent runner but left the matrix child and an active greenfield propose process orphaned, while the ledger remained claimed instead of terminal interrupted.

- Impact: A valid hidden holdout can be irreversibly consumed by harness setup failure, producing a false zero score and leaving test projects or processes running.

- Components Affected: release

- Environment(s): macOS local release proof, exact revision 76ed69c95d6fe09c0c67b0e0031be949a9eefd55, clean detached worktree, uv-created Python 3.13 environment without Playwright

- Detected By: Fresh sealed 24-case final holdout release campaign

- Failure Signature: Playwright is unavailable: ModuleNotFoundError; after SIGINT child greenfield_preconfirm_matrix.py remained parented to PID 1 and final-holdout ledger status remained claimed

- Trigger Path: greenfield_matrix_campaign_runner.py --require-release-readiness with --final-holdout-run-ledger, followed by SIGINT

- Ownership: Release proof preflight and campaign process lifecycle

- Timeline: Campaign packaging preflight passed; ledger was claimed; case 1 scored 0/10 solely because Playwright was absent; parent was interrupted; child and propose process survived; operator killed both and terminalized the ledger manually as interrupted.

- Blast Radius: Any release proof executed from an environment missing browser dependencies or interrupted while a shard is active

- SLO/SLA Impact: Blocks trustworthy release readiness and wastes independent holdout capacity

- Data Risk: No governed repository writes; temporary generated projects and disclosed holdout state can remain

- Security/Compliance: Compliance and privacy posture: no consumer data was involved, but orphaned processes violate execution-containment policy and can retain hidden evaluation text in temporary state; accessibility proof is also unavailable when browser setup is missing.

- Invariant Violated: A final holdout must be claimed only after all non-product prerequisites pass, and every claimed run must terminate exactly once as passed, failed, or interrupted with no surviving descendants

- Workaround: Install and launch-test Playwright in the runner environment before sealing a fresh holdout; on interruption kill descendants and call complete_final_holdout_run with an interruption artifact.

- Root Cause: Browser dependency readiness is checked inside per-case proof after one-shot claim, and interrupt handling does not reliably cancel subprocess descendants or finalize the claimed ledger.

- Solution: Add a release preflight that imports Playwright and launches required browsers before claim; wrap campaign execution in terminalization and process-group cleanup so BaseException/SIGINT records interrupted and kills all descendants.

- Rollback/Forward Fix: Forward fix the harness; do not weaken browser proof or reuse the consumed holdout.

- Verification: Regression proves missing Playwright fails before ledger creation and product execution; SIGINT integration proves no child survives and ledger terminalizes interrupted; normal release campaign still passes.

- Prevention: Order environment and dependency checks before disclosure/claim and centralize terminal cleanup around the one-shot guard.

- Agent Guardrails: Never run a sealed final holdout until browser launch preflight passes in the exact interpreter; never delete or reuse a claimed ledger.

- Preflight Checks: Exact interpreter imports playwright, launches Chromium at desktop and mobile viewports, dist provenance matches revision, temp parent is empty, ledger absent.

- Monitoring Updates: Emit explicit preflight_failed versus product_failed campaign status and descendant cleanup counts.

- Version/Build: 0.1.15 candidate at 76ed69c95d6fe09c0c67b0e0031be949a9eefd55

- Config/Flags: proof-tier=release, include-browser-proof=true, require-release-readiness=true

- Customer Comms: Internal release-blocking harness defect; no consumer release claim.

- Code References: - scripts/release/greenfield_matrix_campaign_runner.py
- scripts/release/greenfield_matrix_campaign_shard_runner.py
- scripts/release/greenfield_final_holdout_guard.py
