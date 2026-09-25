- Bug ID: CB-321

- Status: InProgress

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

- Verification: Missing-Playwright regression fails before ledger creation and product execution; SIGINT integration proves no child survives and the ledger terminalizes interrupted. Exact-revision run `7f03f7cf8` then passed browser launch preflight, executed all 24 claimed cases, terminalized the ledger as failed from product-quality results, and left no campaign child processes. Product failures remain governed by their owning Casebook records and do not reopen this harness-lifecycle defect.

- Prevention: Order environment and dependency checks before disclosure/claim and centralize terminal cleanup around the one-shot guard.

- Agent Guardrails: Never run a sealed final holdout until browser launch preflight passes in the exact interpreter; never delete or reuse a claimed ledger.

- Preflight Checks: Exact interpreter imports playwright, launches Chromium at desktop and mobile viewports, dist provenance matches revision, temp parent is empty, ledger absent.

- Monitoring Updates: Emit explicit preflight_failed versus product_failed campaign status and descendant cleanup counts.

- Version/Build: 0.1.15 candidate at 76ed69c95d6fe09c0c67b0e0031be949a9eefd55

- Fixed: Pending

- Fixed In: pending 0.1.15

- Config/Flags: proof-tier=release, include-browser-proof=true, require-release-readiness=true

- Customer Comms: Internal release-blocking harness defect; no consumer release claim.

- Code References: - scripts/release/greenfield_matrix_campaign_runner.py
- scripts/release/greenfield_matrix_campaign_shard_runner.py
- scripts/release/greenfield_final_holdout_guard.py

- Direct-Runner Interrupt Reopen (2026-09-25): Exact v4 holdout execution
  against `d921c00e0` passed browser and distribution preflight, then was
  intentionally interrupted after its first product failure made the release
  floor impossible. The direct `greenfield_preconfirm_matrix.py` BaseException
  path wrote an interruption result inside the lease namespace but could not
  complete the ledger because no retained root manifest existed yet. Its final
  lease cleanup then raised `Directory not empty`, shadowing the original
  interrupt and leaving the one-shot ledger `claimed`. No descendant process
  survived and no consumer records were written, but the terminalization law
  still failed. The existing `seal_interrupted_retained_evidence` utility
  successfully sealed the completed case and partial next-case staging bytes;
  `complete_final_holdout_run` then terminalized the original ledger as
  `interrupted`. The temporary execution root was moved recoverably to Trash
  only after those hashes verified. Reopen this record: direct and campaign
  runners must share one interrupt owner that seals partial evidence before
  lease cleanup and cannot let cleanup exceptions suppress ledger completion.
  Evidence:
  `/private/tmp/odylith-greenfield-final-holdout-20260924-v4-run-ledger.json`
  and
  `/private/tmp/odylith-greenfield-final-holdout-20260924-v4-evidence/retained-evidence-manifest.v1.json`.

- Public release interrupt reproduced (2026-09-25): Exact clean distribution
  `f87596b4d` entered a disclosed 36-case release-tier run after the v6/v7
  structural contract passed. The first three completed cases were already
  release-decisive (`1` pass, `2` fail-closed semantic outcomes), so the
  operator interrupted case four rather than spend the rest of the corpus on
  a mathematically failed gate. The direct runner again wrote
  `final-holdout-interrupted-result.v2.json` inside its lease namespace, did
  not seal the partial retained-evidence root, left the one-shot ledger
  `claimed`, and then replaced the original interrupt with `Directory not
  empty`. No child process survived. The existing interruption sealer
  successfully preserved the three completed cases and partial fourth-case
  bytes, terminalized ledger run
  `96af72eda095f340253fcc0a599c5a0f9bc618959df244458908da4875d529e5`
  as `interrupted`, and allowed exact namespace cleanup. The fix remains the
  existing owning abstraction: the direct runner must write its interruption
  result outside the lease, seal partial evidence before ledger completion,
  complete the ledger exactly once, and only then release the empty namespace.
  Do not weaken one-shot custody or hide cleanup errors.

- Direct-runner correction implemented (2026-09-25): The direct BaseException
  path now persists its interruption result beside the ledger, seals partial
  retained evidence, terminalizes only with that manifest, and preserves the
  active interrupt across lease-release failure. Independent strong review
  found one remaining masking edge: a sealer or ledger-completion exception
  could replace the original KeyboardInterrupt. The final correction catches
  that custody failure, annotates the original exception, and deliberately
  leaves the ledger claimed rather than force-completing it. Successful
  terminalization, sealer-failure, and lease-cleanup tests are green. CB-321
  remains `InProgress` until a rebuilt exact release run proves descendant
  reaping, sealed terminal evidence, and empty namespace end to end.

- Direct-runner source gate (2026-09-25): Main-path claim-to-interrupt wiring
  now has a regression that forces a live campaign `KeyboardInterrupt`, an
  interruption-sealer failure, and the final lease release. The original
  interrupt survives with a custody note, the ledger remains claimed rather
  than being falsely terminalized, the child is no longer live, and the lease
  releases. The focused gate and full install Greenfield suite pass. Keep this
  record `InProgress` until the next exact-distribution release run supplies
  real terminal ledger, retained-manifest, descendant, and empty-namespace
  evidence.
