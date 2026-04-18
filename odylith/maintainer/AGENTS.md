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
- For Python engineering in this maintainer lane, clean, simple, and efficient
  engineering prevails over complex engineering when the outcome is the same.
  Default to modular, robust, reliable, reusable designs that stay long-term
  optimal.
- For substantive maintainer coding, scan the bound repo slice deeply enough
  to understand the surrounding contracts, adjacent modules, shared helpers,
  existing validation, and nearby call sites before editing. Do not patch from
  a one-file skim when the real behavior lives across the slice.
- Treat AI slop as a regression in this maintainer lane. Avoid placeholder
  abstractions, duplicated wrappers, speculative helper layers, generic filler
  comments, and names or structure that hide the real contract instead of
  clarifying it.
- Add or tighten inline code documentation when it materially improves local
  understanding of non-obvious invariants, state transitions, pressure cases,
  or boundary assumptions, but do not carpet-bomb obvious code with comment
  noise.
- The maintainer coding bar is sensible, readable code that stays reusable,
  robust, and reliable under extension, debugging, and retry pressure.
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
  supposed to prove proof-host native spawn behavior or proof-host CLI execution,
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
- Keep hosted installer generation compatible with the last shipped runtime
  exercised by release smoke. When installer behavior differs between fresh and
  existing repos, branch on repo state using stable commands instead of
  assuming a newly added hidden CLI flag already exists in older shipped
  versions.
- Keep generated hosted installer shell templates strict-mode safe. If the
  template runs under `set -euo pipefail`, initialize every optional local
  before testing it and prove the nested fresh-install path in canonical smoke
  before trusting the change for release.
- Treat verifier-warning cleanup as incomplete unless successful verification
  stays calm in the full shipped lane: hosted installer, pinned dogfood,
  consumer rehearsal, and GA gate. If `OK:` asset proof still arrives wrapped
  in scary trust-warning noise, capture the residual bug for the next release
  instead of calling the warning story done.
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
- Treat live teaser, `**Odylith Observation**`, and `Odylith Proposal` as the
  intervention-engine fast path. Treat `Odylith Assist:` as the chatter-owned
  closeout so maintainer hooks do not drift into one slow, tangled narration
  stack.
- The `**Odylith Observation**` and `**Odylith Proposal**` experience is a
  maintainer-owned brand contract, not optional polish. Any maintainer change
  touching the intervention engine, Chatter, Compass, or host hooks must
  preserve the shipped labels, the one-confirmation proposal flow, and the
  human-feeling markdown UX across detached `source-local`, pinned dogfood,
  and the downstream consumer lane.
- Preserve the shipped shape as well as the words: Observation should look
  like `Odylith Assist`, which means one short labeled line. Proposal should
  be a short ruled block with the heading, a couple of lines, a few bullets,
  and the confirmation line.
- Maintain one stable intervention identity across teaser, Observation, and
  Proposal for the same session-local moment. Later hooks may add evidence or
  surface the first eligible Proposal, but they must not make the same moment
  feel like a fresh branded interruption.
- For Codex and Claude checkpoint hooks, keep the full Observation,
  Proposal, and Assist bundle in hidden developer context for continuity, but
  surface the earned Observation/Proposal beat visibly at the hook moment when
  the host renders hook output. If the host keeps hook output hidden, render
  the assistant-visible fallback Markdown in chat instead of claiming the
  engine is active. Stop is the fallback closeout lane, not the primary
  intervention moment.
- Hook `systemMessage` or `additionalContext` generation is not proof of
  chat-visible UX. The user-visible contract is satisfied only by rendered
  chat text or by a host channel that is proven visible in the active session.
  When in doubt, run `odylith codex visible-intervention` or `odylith claude
  visible-intervention` and show that Markdown directly.
- Make the interjection obvious immediately. Observation should tell the user
  why Odylith is stepping in without making them parse a card full of
  sections, and Proposal copy should sound like a crisp human recommendation
  rather than branded filler.
- Preserve the multiline markdown structure of Observation and Proposal blocks
  end to end. If a maintainer change flattens those sections into single-line
  summaries anywhere in the host or Compass path, treat that as a shipped UX
  regression and fix it before closeout.
- When maintainers show these surfaces to humans in docs, demos, reviews, or
  discussion, render them as Markdown or describe them in prose. Do not
  present them as fenced raw Markdown unless the task is specifically about
  debugging raw markdown text.
- Treat filler demo copy as a regression too. Mockups, screenshots, and sample
  payloads should use concrete governed meaning, not placeholder flourish.
- Treat templated or mechanical intervention copy as a product regression even
  when the facts are technically correct. The default shipped voice must stay
  friendly, delightful, soulful, insightful, simple, clear, accurate,
  precise, and above all human until a later release lands explicit
  voice-pack selection.
- Preview-only proposals remain unappliable until every action in the bundle
  has a safe CLI-backed apply lane. Maintainer changes must not reintroduce
  partial bundle apply just because one surface already has a helper.
- Preserve prompt memory across the full intervention lifecycle. Stop hooks,
  post-edit checkpoints, post-bash checkpoints, apply, and decline events must
  carry or recover the original prompt excerpt so later Odylith reasoning does
  not collapse into self-referential proposal summaries.
- At closeout, you may add at most one short `Odylith Assist:` line if it
  helps summarize what Odylith materially contributed. Prefer
  `**Odylith Assist:**` when Markdown formatting is available; otherwise use
  `Odylith Assist:`. Lead with the user win, link updated governance IDs inline
  when they were actually changed, and when no governed file moved, name the
  affected governance-contract IDs from bounded request or packet truth without
  calling them updated. Frame the edge against `odylith_off` or the broader
  unguided path when the evidence supports it. Keep it crisp, authentic, clear,
  simple, insightful, soulful, friendly, free-flowing, human, and factual. Use
  only concrete observed counts, measured deltas, or validation outcomes; if
  the evidence is thin or the user-facing delta is not clear, omit it.
- Treat Odylith-routed native delegation as the default execution path for
  substantive grounded maintainer work in both maintainer postures when the
  current host supports it. Codex is the currently validated native-spawn
  host; pinned dogfood and detached `source-local` maintainer dev still keep
  the slice local when Odylith says so or when another host has not yet
  proven native spawn.
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
