- Bug ID: CB-086

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass still carried a second minute-scale `full` refresh idea
  in product code, guidance, and release/governance memory even after the
  bounded `odylith compass refresh` contract became the only operator path that
  met the product's cost and speed bar. The leftover lane no longer belonged in
  the architecture: it kept stale branches alive in runtime code, preserved
  docs that sounded like Compass had a deeper truth mode, and invited future
  regressions back toward multi-minute rerenders and higher model spend.

- Impact: A ghost deep-refresh lane makes Compass harder to reason about and
  cheaper to regress. Even if operators cannot invoke it directly, leaving it
  alive in code and governed memory keeps product pressure pointed at the wrong
  fix and weakens the one-bounded-refresh contract that now carries Compass.

- Components Affected: `src/odylith/runtime/surfaces/compass_refresh_contract.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  Compass release notes, Compass and Dashboard current specs, B-025 and B-060
  governed workstream memory, browser and runtime regression tests.

- Environment(s): product-repo maintainer mode, shipped guidance, release-note
  surfaces, and any future code path that might have revived the retired
  deeper-refresh contract.

- Root Cause: Compass hardening fixed operator behavior before product memory
  fully caught up. The public CLI and shell already centered on one bounded
  refresh contract, but internal helpers, tests, and governed narrative still
  treated `full` as a meaningful mode instead of historical baggage that
  needed to be retired.

- Solution: Retire the minute-scale `full` lane entirely. Normalize any legacy
  `full` token onto the bounded `shell-safe` contract, remove parser choices
  and internal branches that still special-cased deep refresh, update release
  notes and governed workstream memory to describe one Compass refresh contract
  only, and add Casebook memory that says Compass must never regrow a second
  expensive truth lane.

- Verification: Fixed on 2026-04-09. Focused Compass refresh/runtime tests,
  render tests, release-note tests, shell onboarding browser proof, and
  `git diff --check` passed after the retirement pass removed stale `full`
  routing and updated governed records.

- Prevention: Compass may keep one bounded refresh contract only. If a future
  change needs more freshness or more narration quality, it must improve the
  bounded path or move work upstream; it must not reintroduce a second
  user-facing or product-promised deep-refresh lane.

- Detected By: Maintainer review after the latest runtime-cost hardening showed
  that multi-minute `full strict live refresh` still existed as product memory
  even though it no longer met the product bar.

- Failure Signature: Compass specs, release notes, tests, or runtime code still
  talk about `full` refresh, deep rerender, or a second expensive truth lane
  after the bounded contract is already the only acceptable product behavior.

- Ownership: Compass refresh architecture, Compass product spec, Dashboard
  wrapper contract, release-note truth, and Compass governance memory.

- Invariant Violated: Compass must not expose or preserve a second minute-scale
  deep-refresh mode after the product decides that one bounded refresh
  contract is the only acceptable architecture.

- Related Incidents/Bugs:
  [2026-04-08-explicit-compass-full-refresh-can-pass-with-deterministic-or-stale-runtime-state.md](2026-04-08-explicit-compass-full-refresh-can-pass-with-deterministic-or-stale-runtime-state.md)
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)

- Fix Commit/PR: `2026/freedom/v0.1.11` Compass retirement hardening branch.
