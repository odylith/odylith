- Bug ID: CB-337

- Current Checkpoint Validation: After the separate CB-338 correction, all 3,204 frozen inputs match at terminal completion. The current candidate passes 5,058 runtime, 1,437 install, 180 CLI and 376 browser checks, with the same one documented Radar fixture-state skip and zero failures or errors. Evidence: /private/tmp/odylith-migration-release-scope.nOTGQD/atlas-*-full.xml. This supersedes the earlier snapshot for current regression proof, not the outstanding exact migration assessments or full Greenfield release gates.

- Current Bounded Proof: All 85 focused real-Git, observer, migration-runtime and CLI controls pass in 3.90 seconds after the three reproduced endpoint/materialization failures. Independent re-adjudication finds no remaining bounded P0/P1. The real source-local release comparison against published v0.1.14 now finds 808 consumer-facing paths across five incomplete assessment families and fails approval, instead of returning empty success. This is correct refusal, not completed migration qualification. Evidence: /private/tmp/odylith-migration-release-scope.nOTGQD/migration-focused-final.xml and explicit-release-scope.json.

- Frozen Broad Validation: All 3,201 inputs match after terminal completion: 5,047 runtime, 1,437 install, 180 CLI and 376 browser checks pass with no failures. One Radar browser check is skipped because its fixture does not expose maintainer-only traceability diagnostics. Eight changed-governance desktop/mobile views also pass, but screenshot review finds a separate Atlas explanation defect now tracked as CB-338. These test runtimes are not consumer SLA measurements. The five release assessments, populated installed migration, model quality, host delivery and final holdout remain open.

- Endpoint And Checkout Controls: Three real-Git failures reproduced again on resume. Requiring the published predecessor to be an ancestor is invalid: published v0.1.14 is a sibling release-preparation commit, so comparison must use the two explicitly resolved endpoint trees. Independent review also found that skip-worktree or assume-unchanged flags can hide tracked content behind a reusable missing-file fingerprint. Refuse assessment when relevant tracked paths have these flags; require a materialized, inspectable checkout rather than guessing deletion or altering Git settings. Retain scope-materialization-red.xml and scope-materialization-resume-red.xml; no fallback baseline or assessment waiver is authorized.

- Scope Custody Controls: The first new real-Git pack passes 15 cases after replacing dirty-only discovery. Two additional controls then fail: equal candidate content can reuse one assessment across different predecessors, and path normalization changes a literal backslash/trailing-space filename into a different path. Bind release fingerprints to the resolved predecessor and relevant file mode, and preserve native Git path identity rather than display-string normalization. Retain the initial missing-Git false-success failure and both custody failures under /private/tmp/odylith-migration-release-scope.nOTGQD/. These are bounded release-scope defects, not semantic-model failures.

- Status: FixedPendingRelease

- Fixed In: 0.1.15

- Created: 2026-09-10

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: The canonical release migration gate returns success on a clean candidate while its observer examines no release changes. Committing a consumer-facing change removes the dirty-only obligations instead of preserving release assessment custody.

- Impact: Maintainers can mistake a clean commit for completed migration assessment and ship unassessed changes to already-installed consumers.

- Components Affected: migration-runtime

- Environment(s): Detached maintainer proof checkout at 5fbc51b3ae01f958241b83a85f9dd7c662d2053c, target 0.1.15; local published predecessor v0.1.14 resolves to fae446995e13e12409e50f944a336dbc846db90a.

- Detected By: Fresh goal release-gate audit followed by independent source and governance review.

- Failure Signature: release migration-gate reports ok=true with changed_paths=[], needs=[] and blocked_need_ids=[] on the clean candidate, despite prior incomplete consumer-surface assessments.

- Trigger Path: Commit consumer-facing product changes, then run odylith release migration-gate --repo-root . --target-version 0.1.15 --json.

- Ownership: Maintainer release-gate change-scope admission feeding the existing surface migration observer.

- Timeline: Captured 2026-09-10 through `odylith bug capture`.

- Blast Radius: Clean release candidates with committed guidance, CLI, browser or install-managed changes.

- SLO/SLA Impact: Blocks trustworthy release qualification; no Greenfield latency-budget change is justified.

- Data Risk: The check itself writes no consumer data; omitted assessment can miss migration and preservation hazards.

- Security/Compliance: Release audit completeness is weakened; no exploit or public release impact has been demonstrated.

- Invariant Violated: Required release assessment must cover the candidate delta from its authoritative predecessor, including committed changes; an unexamined required scope cannot pass as zero checks.

- Root Cause: The observer defaults to git status --porcelain and the canonical release gate supplies no release comparison scope. Git errors also collapse to an empty path set.

- Solution: Bind the canonical release gate to an explicit, validated release comparison baseline and include committed plus working changes. Preserve the existing classifier and completed-assessment contract; fail closed when required scope cannot be established.

- Verification: Retained fresh report /private/tmp/odylith-migration-release-scope.nOTGQD/clean-gate-before.json. Require real Git clean/dirty/committed/renamed/deleted and missing-baseline controls, then current release-scope assessment.

- Prevention: Do not use a dirty-worktree observer result as whole-release proof or treat commit as assessment completion.

- Related Incidents/Bugs: CB-135; B-140; B-145; B-142

- Code References: - src/odylith/install/migration_observer.py
