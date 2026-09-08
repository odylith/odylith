- Bug ID: CB-305

- Browser-Readable Publication Candidate (2026-09-08): An isolated single-HTML-pointer prototype passes four file/HTTP desktop/mobile schedules in 47.69 seconds. All 36 normal/history observations pin the real shell and child resources to one complete snapshot, including delayed first iframe loads, pre/post-pointer SIGKILL, a second interrupted writer after a successful later update, and historical links. Twenty additional observations cover malformed/invalid entry state and missing files without live fallback; missing-file handling remains browser-native error behavior, not polished product recovery UX, and no empty baseline was proved. A controlled two-case HTTP comparison passes in 4.89 seconds: under identical Last-Modified timestamps the embedded-only entry stays stale, while a no-store read of the same canonical entry reaches the new snapshot. This is synthetic writer/browser-carrier evidence, not production journal integration or a fix. Preserve all failed controls, including a final-fragment test mistake, the cache observation, and the incomplete disk-full run. Repeated owned fixture copies were archived recoverably and final fixture storage was reduced to 474 MiB using isolated-copy hardlinks and atomic replacement. Evidence and explicit integration limits: /private/tmp/odylith-dashboard-pointer-comparison.a7ZCxp/review.md. The next implementation must replace JSON authority rather than mirror it, seal an acyclic publication identity, reserve the entry in write/readback ownership, initialize a safe baseline, publish immutable later-writer successors, and preserve reviewed-hash links and recovery. Source remains unchanged; CB-305 stays Open/P0.

- Interrupted Initial Publication Reopen (2026-09-08): Current revision d2ccfbcb95f exposes the live tree after SIGKILL releases the writer lock when no active generation exists. Independent first-write injection leaves one new Radar file and one old file; the canonical current-view resolver still returns live_without_generation. Killing after all compatibility copies but before pointer publication also exposes an unpublished package. The after-pointer control correctly returns the immutable generation. Evidence: /private/tmp/odylith-confirm-read-proof.4PUYEv/red.xml (two failed visibility checks, one passing published control). Existing recovery tests repair or verify journals before inspection and therefore do not establish reader safety during the stopped-before-recovery interval. Keep publication/recovery state owned by the existing journal validator; require a settled journal before returning live fallback, without performing recovery or mutation from a reader. This reopens source-level visibility proof; actual canonical reader coverage and installed/browser proof remain separate open obligations.

- Helper-Only Fix Rejected (2026-09-08): A journal-validation guard made all three direct-helper probes pass, but independent reachability review found both production handoff callers supply explicit transaction hashes and bypass that branch. The real shell opens relative mutable child files; an opener-only check would also release its read lock before browser fetches. The two-source-file experiment was withdrawn completely. Do not revive this unused guard as consumer closure or duplicate journal-container policy: the prototype also mishandled the existing manual-recovery container. Applicability report: /private/tmp/odylith-host-confirmation-proof.czLkUO/visibility-applicability-review.md.

- Actual Dashboard Crash Reproduction (2026-09-08): An isolated copy of the real rendered shell and Atlas/Radar pages was sealed with exactly two instrumented HTML changes. Existing writer fault injection killed the child after its first atomic file write. Actual Chromium shell/iframe navigation at 1440px and 430px showed SEALED NEXT in Atlas and BASELINE in Radar before recovery. The after-pointer control showed SEALED NEXT in both. Normal-state proof has zero page errors and zero bad HTTP responses; screenshots were inspected. Both fault fixtures were then deterministically recovered to terminal aborted/closed journals. Evidence: /private/tmp/odylith-confirm-read-proof.4PUYEv/consumer-normal-red.xml (one failed phase, one passing phase, each at two widths) and consumer-normal/ observations/screenshots. Preserve the earlier path-setup error and degraded-image replay separately. This is an instrumented real-browser publication-law counterexample, not native model quality, installed distribution, or complete UX qualification. The next owner correction must bind the actual shell and all relative child resources to one complete immutable generation; keep only the journaled-crash-recovery claim until canonical reader coverage is proved. Current unchanged kernel suites still pass 114 tests in 26.09 seconds, illustrating their coverage gap rather than resolving it.

- Status: Open

- Created: 2026-08-02

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: After a Greenfield generation became active, later governed writers changed the live managed tree without a shared completion signal. The post-confirm reader could keep presenting the immutable onboarding generation as current, while naive drift routing could expose an in-progress or failed partial writer.

- Impact: Users could be sent to stale governance state after successful later writes, or to uncertain partial live bytes if drift were handled without writer coordination.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 maintainer source and installed Greenfield contract

- Detected By: Adversarial transaction and recovery review under B-142

- Failure Signature: Active generation remains status=active after a later managed-path mutation; no production supersession caller distinguishes successful, failed, and in-flight writers. Adversarial recovery review also found that installed generation observation pinned metadata without the sealed expected write set, allowing manifest-consistent but corrupted after-image bytes to satisfy the proof, and that matrix navigation checks ignored the emitted `dashboard_path` and `project_url`.

- Trigger Path: Greenfield CONFIRM followed by any supported Odylith CLI command that mutates GREENFIELD_REPOSITORY_WRITE_PATHS

- Ownership: Domain Intelligence Greenfield transaction and canonical handoff boundary

- Timeline: Captured 2026-08-02 through `odylith bug capture`.

- Blast Radius: All Greenfield repositories that receive later Radar, Registry, Atlas, Compass, Casebook, shell, or bundle mutations

- SLO/SLA Impact: Blocks release claim for package-level canonical visibility

- Data Risk: No sealed bytes are lost; stale or partial governance visibility can misdirect subsequent work.

- Security/Compliance: No direct security escalation; integrity and auditability boundary violated.

- Invariant Violated: Canonical readers must resolve a coherent active generation and move to live truth only after a successful changed writer completes.

- Root Cause: The active-generation pointer had no cooperating later-writer boundary; supersession existed only as an unused primitive and reader drift alone could not distinguish success from partial failure. The recovery harness validated generation identity but did not provide the expected sealed write set to byte-level after-state validation, while navigation proof remained bound only to legacy route aliases.

- Solution: Serialize supported CLI mutations with the Greenfield repository lock, retain the old generation while a writer runs, supersede only after zero-exit changed managed readback, fail closed on unexplained drift, and retain exact reviewed-generation routes.

- Rollback/Forward Fix: Forward fix; preserve immutable generations and existing journals.

- Verification: 84 focused atomic/custody tests pass, including in-flight reader, changed success, failed partial, no-op, exact receipt, and lock contention cases; real CLI contract tests cover immutable navigation. The recovery harness now loads the sealed expected write set, corrupts a generation byte while preserving pointer and manifest metadata, and observes invalid readback. Matrix navigation proof binds `dashboard_path`, `project_url`, compatibility path, view status, and transaction hash to the reviewed immutable generation dashboard and requires that file to exist. These checks are included in the 460-test touched source checkpoint; clean installed fault and browser proof remains open.

- Prevention: Keep command_may_mutate_greenfield_managed_paths conservative, require run_with_greenfield_managed_mutation_boundary around top-level CLI dispatch, and block merges unless test_greenfield_managed_mutation_boundary.py proves changed-success, failed, no-op, and contention behavior.

- Agent Guardrails: Never route live on fingerprint drift without a durable writer completion signal; never supersede before successful changed readback.

- Preflight Checks: Run the managed mutation boundary tests, generation/journal tests, host confirmation tests, and Atlas D-043 freshness check.

- Regression Tests Added: tests/unit/runtime/test_greenfield_managed_mutation_boundary.py

- Related Incidents/Bugs: CB-304; B-142

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_managed_mutation_boundary.py
- src/odylith/runtime/domain_intelligence/greenfield_post_confirm_handoff.py
- tests/unit/runtime/test_greenfield_managed_mutation_boundary.py
