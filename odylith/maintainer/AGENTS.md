# Odylith Maintainer AGENTS

Scope: applies to maintainer-only paths under `odylith/maintainer/`.

## Purpose
- Keep Odylith product-maintainer release guidance, release skills, and release
  benchmark publishing rules separate from shared consumer-safe guidance.
- Keep end-to-end Odylith release process out of bundled consumer
  `agents-guidelines/` and `skills/`.

## Working Rule
- Use this subtree only in the Odylith product repo.
- Do not mirror files from this subtree into bundled consumer assets.
- When release work changes the public benchmark story, update the maintainer
  guidance, maintainer skill, generator contract, and repo-root `README.md` in
  the same change.
- Keep the product-repo lanes explicit:
  - pinned dogfood is the default proof posture for the shipped runtime
  - detached `source-local` is the explicit maintainer-only live-source
    execution posture
- This maintainer lane is non-negotiable about branch safety: the Git `main` branch is read-only for authoring, and maintainers never work directly on `main`.
- If a maintainer task needs code edits or any other tracked repo changes while the current branch is `main`, create and switch to a new branch before the first edit, stage, or commit.
- If maintainer work is already on a non-`main` branch, keep using that branch.
- Read-only inspection and canonical release proof against `origin/main` are allowed, but maintainer development does not happen on the Git `main` branch.
- This maintainer lane is also non-negotiable about source-file size
  discipline: the repo-root `800`/`1200`/`2000+` thresholds and `1500` LOC
  test ceiling are hard policy, not optional guidance.
- Any maintainer change that grows a hand-maintained source file past `1200`
  LOC needs an explicit exception and decomposition plan, and any
  hand-maintained source file over `2000` LOC must already have an active
  decomposition workstream before more feature growth lands in it.
- When maintainer work touches a hand-maintained source file that is already
  beyond those thresholds, the default action is to refactor it into multiple
  focused files or modules with robustness, reliability, and reusability as
  explicit goals instead of continuing to extend the oversized file.
- Odylith's managed runtime may still edit any product-repo files; the lane
  distinction is about execution and validation posture, not file-edit
  authority.
- For release, benchmark, and dogfood work, go through Odylith first:
  inspect runtime state, self-host posture, benchmark proof, and maintained
  surfaces through `./.odylith/bin/odylith` before falling back to ad-hoc repo
  search.
- For substantive maintainer work, search the existing workstream, bound plan,
  related bugs, related components, related diagrams, and recent Compass or
  session context first; extend or reopen those records before creating new
  ones.
- When downstream feedback becomes maintainer implementation scope, capture it
  in Casebook first, then update the bound Radar workstream, active plan, and
  impacted Registry component specs before code changes. Do not leave a
  maintainer fix half-governed.
- Queued Radar items, case queues, and shell or Compass queue previews are not
  automatic implementation picks in the maintainer lane. Unless the user
  explicitly asks to work a queued item, do not start implementing it just
  because it is visible in a backlog or Odylith queue surface.
- The dashboard surface header is a non-negotiable frozen contract in this
  maintainer lane, across both pinned dogfood and detached `source-local`
  maintainer-dev posture.
- Do not add, remove, rename, reorder, restyle, repurpose, or otherwise tamper
  with header labels, text, buttons, controls, badges, tabs, version readouts,
  or any other UI artifact in that header.
- Do not use adjacent dashboard, onboarding, release-note, maintainer-note, or
  shell-polish work as justification for touching the header. Leave it alone.
- If the maintainer slice is genuinely new, create the missing workstream and
  bound plan before non-trivial implementation; if it spans multiple release or
  benchmark tracks, use child workstreams or execution waves instead of hiding
  them in one note.
- Keep release-adjacent Registry, Atlas, Casebook, and Compass truth current in
  the same change whenever maintainer work reveals a new failure mode, a stale
  diagram, a changed benchmark story, or a boundary that needs a first-class
  component spec.
- Local maintainer release identity is also non-negotiable in this lane:
  authored maintainer work uses `freedom-research
  <freedom@freedompreetham.org>` for both author and committer config. If
  canonical release-history proof needs to survive platform merge machinery,
  keep the history gate focused on canonical maintainer authorship instead of
  widening local identity policy.
- Before GA, keep first-party GitHub Actions pins in release, release-candidate,
  and test workflows on current immutable SHAs that no longer carry scheduled
  runtime deprecation warnings into the release lane.
- Before GA, keep release-proof unit lanes environment-portable. If a test is
  supposed to prove Codex host-native spawn behavior or Codex CLI execution,
  force or mock that contract inside the test instead of inheriting the
  maintainer machine's ambient host/runtime state.
- Treat parent-shell freshness and child-surface freshness as separate truths.
  A successful wrapper refresh is never enough evidence to imply Compass,
  Radar, Atlas, Registry, or Casebook data is current unless the child
  runtime/surface contract says it was rerendered or the shell explicitly
  projects the gap.
- Explicit operator-requested Compass `full` refresh is a non-negotiable proof
  contract in this maintainer lane: do not accept a passing result that reused
  the wrong recent runtime payload, landed on deterministic local brief
  output, or skipped browser proof across global 24h/48h plus
  current-workstream scoped views. The five-minute reuse clamp itself is valid;
  after changing shell, Compass, Casebook, or other checked-in governed
  surface source truth, rerender the affected tracked surfaces before
  interpreting browser failures. Stale generated artifacts are not evidence
  that the live product contract is still broken.
  the bar is that any reused payload must already satisfy the requested
  full-refresh truth contract.
- Treat authored release-note markdown as the single source of truth for the
  consumer upgrade spotlight. For release-facing shell copy, land or update
  `odylith/runtime/source/release-notes/vX.Y.Z.md` first, mirror it into the
  bundle assets, and prove the popup from that exact note instead of patching
  shell-only spotlight text in parallel.
- Treat the release version bump as separate tracked truth, not an implication
  of authored notes or overrides. Before canonical `make release-preflight`
  for `vX.Y.Z`, land the matching `pyproject.toml` version and synchronize
  `src/odylith/__init__.py` plus
  `odylith/runtime/source/product-version.v1.json` on the release branch, then
  return to `main` for canonical proof.
- Use direct `rg`, source reads, generator inspection, or targeted shell
  inspection only when Odylith explicitly signals fallback or ambiguity, or
  when you are verifying tracked source truth behind a runtime-generated
  claim.
- Keep maintainer and dogfood progress updates task-first. Do not narrate
  startup, routing, packet-selection, or degraded-attempt history unless a
  literal command, a live blocker, or a runtime-lane distinction matters.
- Keep Odylith ambient by default during work. If a routing or governance fact
  materially changes the next move, weave it into the update first and reserve
  explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels
  for rare high-signal moments.
- At closeout, you may add at most one short `Odylith Assist:` line if it
  helps summarize what Odylith materially contributed. Prefer
  `**Odylith Assist:**` when Markdown formatting is available; otherwise use
  `Odylith Assist:`. Lead with the user win, link updated governance ids inline
  when they were actually changed, and frame the edge against `odylith_off` or
  the broader unguided path when the evidence supports it. Keep it crisp,
  authentic, clear, simple, insightful, soulful, friendly, free-flowing,
  human, and factual. Use only concrete observed counts, measured deltas, or
  validation outcomes; if the evidence is thin or the user-facing delta is not
  clear, omit it.
- In Codex, treat Odylith-routed native spawn as the default execution path
  for substantive grounded maintainer work in both maintainer postures:
  pinned dogfood and detached `source-local` maintainer dev, unless Odylith
  explicitly keeps the slice local.
- This is the benchmark-safe posture: optimize in this order:
  correctness and non-regression, grounding recall and precision, validation
  and execution fit, robustness across cache states and retries, then speed,
  then token cost. Lower-tier wins never justify a higher-tier regression.
- Proof outranks diagnostic in this maintainer lane. Improve the live
  `--profile proof` outcome first, then improve diagnostic only when it
  preserves or improves proof on the same metric ladder.
- A diagnostic-only gain that harms proof is a regression, not a benchmark
  win.
- If a maintainer explicitly waives benchmark proof for one exact release
  version, stop any in-flight proof run, record the override in
  `odylith/runtime/source/release-maintainer-overrides.v1.json`, bind the
  blocker into Casebook plus the active workstream/plan and the impacted
  Registry specs, and describe that release as benchmark-advisory rather than
  benchmark-proved.
- Use pinned dogfood whenever the question is "does the shipped Odylith
  runtime behave correctly?". Use detached `source-local` only when the
  question is "do these unreleased `src/odylith/*` changes execute
  correctly?". In that detached posture, use `make dev-validate` for the
  maintainer validation lane rather than treating `make release-preflight` as a
  current-workspace proof command.
- Follow the repo-root source-file size discipline in this maintainer lane, and
  do not turn release pressure into a repo-wide "all files above X" rewrite.
- For large-file maintainability work, prioritize targeted decompositions by
  size x churn x centrality with characterization tests first.
- Never game the eval.
- Never accept a benchmark improvement that gets faster or cheaper by becoming
  less accurate, less precise, or less recall-grounded.
- In benchmark publication and review framing, `odylith_off` means
  `raw_agent_baseline`; the repo-scan lane is a separate scaffold control.
- Treat benchmark softening, scenario cherry-picking, validator weakening,
  stale-report publication, or README claim inflation as a product failure, not
  as acceptable release polish.

## Routing
- Release benchmark publishing: `agents-guidelines/RELEASE_BENCHMARKS.md`
- Canonical release order: `../MAINTAINER_RELEASE_RUNBOOK.md`

## Skills
- `skills/release-benchmark-publishing/`
