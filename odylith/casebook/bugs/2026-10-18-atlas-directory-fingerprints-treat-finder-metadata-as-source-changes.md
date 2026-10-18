- Bug ID: CB-366

- Status: Open

- Created: 2026-10-18

- Severity: P2

- Reproducibility: Consistent

- Type: Tooling

- Description: The same tracked source is 47 fresh in the primary macOS workspace and 42 fresh with five stale diagrams in its clean proof checkout. Atlas directory fingerprints include untracked .DS_Store files under execution_engine, intervention_engine and discipline. These Finder files must not affect source freshness.

- Impact: A clean release checkout fails the Atlas freshness gate even when tracked source bytes match the reviewed workspace.

- Components Affected: atlas

- Environment(s): Odylith product repository, detached source-local maintainer posture, macOS; clean source checkpoint 7b6cfaffb58f87003c815724c3b2f59e01d315e9.

- Detected By: Explicit complete PR-slice check-only sync in the existing clean proof checkout and independent watched-directory comparison.

- Failure Signature: Primary Atlas 47 fresh/0 stale; clean checkpoint 42 fresh/5 stale: D-002, D-025, D-037, D-038, D-039. Watched directories have no tracked byte differences; only primary untracked .DS_Store files differ.

- Trigger Path: Create .DS_Store inside an Atlas-watched source directory, refresh the catalog, then run odylith sync --check-only on the same committed source without Finder metadata.

- Ownership: Atlas content fingerprinting in ContentFingerprintCache and its existing directory-entry ignore predicate.

- Timeline: Captured 2026-10-18 through `odylith bug capture`.

- Blast Radius: Atlas freshness and release checks for Finder-touched watched source directories; no Greenfield semantic or admission behavior is changed.

- SLO/SLA Impact: Blocks clean-source release validation; no measured production latency breach.

- Data Risk: No source or user-data loss observed. Preserve original fingerprints and failed proof logs.

- Security/Compliance: No credential or permission incident. Meaningful source-file and directory changes must remain detectable.

- Invariant Violated: Equivalent meaningful directory contents must have identical Atlas fingerprints across workspaces regardless of Finder metadata.

- Root Cause: The existing directory filter excludes Python bytecode caches but does not exclude exact .DS_Store basenames.

- Solution: Extend the existing directory fingerprint predicate to ignore only an exact regular-file, non-symlink `.DS_Store`. Keep similarly named files, directories, symlinks, and every other source or resource change visible.

- Verification: Retained clean checkpoint failure is PR35-clean-commit-explicit-governance-check.stdout.log. Before the fix, the targeted suite reports 1 failure and 6 passes. The first correction passed 7 tests. Independent review found that `is_file()` follows symlinks, so the final predicate also refuses symlinks. `PR35-finder-fingerprint-final.stdout.log` records 8 passing targeted tests, including Finder metadata creation/modification/removal, an external-target symlink, and a real-source-change control. A fresh exact-commit clean-source check of all eight requested checks and Atlas 47 fresh/0 stale, followed by CI, remains required and unclaimed.

- Agent Guardrails: Do not copy Finder files into proof, delete them as the product fix, forge fingerprints, ignore arbitrary dotfiles, force refresh over drift, or claim a working-tree pass is clean-source proof.

- Preflight Checks: Run the full explicit PR source slice through check-only from the exact clean commit; a no-argument clean-tree sync may skip and earns no gate credit.

- Related Incidents/Bugs: B-142; CB-054 managed-runtime metadata policy; CB-359 exact Finder exclusion in Compass runtime identity; these are related learning, distinct owners.

- Code References: - src/odylith/runtime/common/diagram_freshness.py
- tests/unit/runtime/test_diagram_freshness.py

- Fix Commit/PR: https://github.com/odylith/odylith/pull/35
