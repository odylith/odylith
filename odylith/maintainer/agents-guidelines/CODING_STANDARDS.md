# Maintainer Coding Standards

## Scope And Authority
- This file applies only in the Odylith product repo's maintainer mode under
  `odylith/maintainer/`.
- The shared baseline in
  `../../agents-guidelines/CODING_STANDARDS.md` still applies.
- This file is the authoritative home for maintainer-side coding, testing,
  generated-artifact authoring, release-surface source edits, benchmark
  harness changes, branch/write safety, and implementation-governance
  coupling. Other maintainer-side guidelines should point here instead of
  restating those rules.
- Use
  [RELEASE_BENCHMARKS.md](./RELEASE_BENCHMARKS.md)
  for release-proof metrics, publication gating, and benchmark narrative.
  Use this file for how code, tests, generators, assets, and coupled docs may
  change.

## Engineering Priorities
- For Python engineering in this maintainer lane, clean, simple, and
  efficient engineering prevails over complex engineering when the outcome is
  the same. Default to modular, robust, reliable, reusable designs that stay
  long-term optimal.
- For substantive maintainer coding, scan the bound repo slice deeply enough
  to understand the surrounding contracts, adjacent modules, shared helpers,
  existing validation, and nearby call sites before editing. Do not patch
  from a one-file skim when the real behavior lives across the slice.
- Prefer extending shared helpers, shared contracts, and existing runtime
  primitives over copy-paste or near-duplicate logic.
- Treat AI slop as a regression in this maintainer lane. Avoid placeholder
  abstractions, duplicated wrappers, speculative helper layers, generic
  filler comments, and names or structure that hide the real contract instead
  of clarifying it.
- When maintainer work tightens anti-slop policy, propagate the shared rule to
  the consumer-safe guidance, shared skill, and shipped bundle mirrors in the
  same change so the stronger bar lands across all lanes instead of staying
  maintainer-local.
- Add or tighten inline code documentation when it materially improves local
  understanding of non-obvious invariants, state transitions, pressure cases,
  or boundary assumptions, but do not carpet-bomb obvious code with comment
  noise.
- The maintainer coding bar is sensible, readable code that stays reusable,
  robust, and reliable under extension, debugging, and retry pressure.
- Optimize maintainer changes in this order: correctness and non-regression,
  grounding recall and precision, validation and execution fit, robustness
  across cache states and retries, then speed, then token cost.
- Proof outranks diagnostic in this maintainer lane. Improve the live
  proof outcome first, then improve diagnostic only when it preserves or
  improves proof on the same ladder.
- Lower-tier wins never justify a higher-tier regression. Never accept a
  speed or token win that regresses recall, accuracy, precision, grounding,
  or reliability.

## Anti-Slop Bans
- Treat AI slop as a regression.
- Apply that bar aggressively in this maintainer lane.
- Apply that bar to any codebase or project surface in this lane: services,
  libraries, apps, CLIs, infra glue, scripts, docs, prompts, hooks,
  templates, config, and generated assets all count.
- No transitional states. Do not replace one slop class with another.
- Move ownership, not just file boundaries.
- Do not ship fake modularization. `def _host()` plus a wall of rebound
  private host symbols is banned.
- Do not replace removed shims with transitional alias walls that only rename
  a dense helper cluster without moving the ownership boundary.
- Do not duplicate generic coercion helpers such as `_mapping`,
  `_json_dict`, `_normalize_*`, `_delta`, or `_parts` across files when one
  shared owner is appropriate.
- Do not treat a shared helper or kernel as a cleanup ornament. If a new owner
  lands, adopt it in the touched slice or leave a bounded follow-up tied to
  the same slop class.
- Do not call a slop cleanup complete just because the first smell
  disappeared. If the replacement smell still exists in the touched slice, the
  pass is incomplete.
- Do not keep host-mirror files near-identical when a shared helper, shared
  renderer, or shared formatter would remove the duplicated control flow.
- Do not leave giant renderers, payload builders, routers, or score engines
  phase-mixed when a real owner can separate data prep, view model,
  template/render, or gather/score/decide stages.
- Do not add filler comments or docstrings. Comments must explain invariants,
  failure modes, boundary assumptions, or non-obvious state transitions.
- New or materially rewritten runtime Python modules must carry a truthful
  module docstring.
- Every anti-slop cleanup must add or update enforcement tests.
- Maintainer anti-slop passes fail closed: do not stop when the touched slice
  still contains the same bounded shim, duplicate-helper, or mirror-drift
  class you set out to remove.
- When install, upgrade, repair, launcher, or bundled project-asset surfaces
  move, proving `tests/unit/install` is mandatory. When browser-proved
  surfaces move, proving the headless browser matrix is mandatory.
- Host-mirror work fails closed as well. If a Codex/Claude or other host pair
  still carries the same duplicated formatter, renderer, or checkpoint control
  flow after the pass, the pass is incomplete; move the shared logic behind a
  real owner before closeout.
- If the anti-slop rule changes in maintainer mode, propagate it through the
  shared consumer-safe guidance, host contracts, install-generated guidance,
  shared skills, and shipped mirrors in the same change.
- When the user asks for repo-wide or lane-wide anti-slop hardening, update
  guidance, skills, install-generated guidance, host contracts, mirrors, and
  enforcement tests together; prose-only hardening is incomplete.
- Use `../../agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md` for the shared
  ban list, decomposition triggers, and proof contract, and use
  `../skills/fail-closed-code-hygiene/` when a maintainer pass is explicitly
  attacking structural slop.

## Non-Negotiable Maintainer Intervention Bar
- Go deep on the bound slice before editing. Understand the surrounding
  modules, shared helpers, call sites, invariants, generated surfaces,
  validators, and user-facing or runtime consequences instead of making
  shallow one-file patches.
- Default to meaningful refactoring across the touched slice when it improves
  clarity, reuse, reliability, and long-term maintainability. Do not preserve
  obvious duplication, brittle flow, awkward layering, dead branches, or
  incidental complexity just to keep the diff smaller.
- The maintainer bar is robust, readable, reliable, logical code that does
  not regress the shipped product contract. Fix bugs, friction, and drag
  discovered in the touched area when they are in scope and can be resolved
  safely in the same change.
- Regression safety is non-negotiable. Run comprehensive contract-focused
  regression validation for the changed slice, and when the change affects UI,
  shell, or browser-proved surfaces, run the full applicable headless browser
  coverage rather than stopping at unit or snapshot evidence.
- Treat "without breaking anything" as a proof obligation, not a slogan:
  preserve behavior intentionally, expand validation when risk rises, and do
  not ship on assumption, partial smoke, or unproved mechanical confidence.
- Add inline documentation aggressively for non-obvious contracts,
  invariants, state transitions, failure modes, and boundary assumptions so
  the next maintainer does not have to rediscover them from scratch. Do not
  add filler comments to code that is already obvious.
- Treat install and bundle mirroring as first-class proof surfaces. When the
  touched change affects guidance, hooks, skills, or install-managed mirrors,
  update the live source and the shipped mirror in the same change and prove
  both with tests before closeout.

## Branch And Write Safety
- The Git `main` branch is read-only for authoring in this maintainer lane.
- If a maintainer task needs code, docs, or any other tracked repo edits while
  the current branch is `main`, create and switch to a fresh branch before
  the first edit, stage, or commit.
- If work is already on a non-`main` branch, keep using that branch. Return to
  `origin/main` only for read-only inspection or canonical release proof.
- Odylith's managed runtime may still edit any product-repo files; the lane
  distinction is about execution and validation posture, not file-edit
  authority.
- Use Odylith-first maintainer workflows when inspecting release readiness,
  dogfood posture, benchmark outputs, and runtime state before falling back to
  ad-hoc repo search.
- Use direct `rg`, source reads, generator inspection, or targeted shell
  inspection only when Odylith explicitly signals fallback or ambiguity, or
  when you are verifying tracked source truth behind a runtime-generated
  claim.

## Governed Change Coupling
- For substantive maintainer work, search the existing workstream, bound plan,
  related bugs, related components, related diagrams, and recent Compass or
  session context first; extend or reopen those records before creating new
  ones.
- When downstream feedback becomes maintainer implementation scope, capture it
  in Casebook first, then update the bound Radar workstream, active plan, and
  impacted Registry component specs before code changes. Do not leave a
  maintainer fix half-governed.
- If the maintainer slice is genuinely new, create the missing workstream and
  bound plan before non-trivial implementation; if it spans multiple release
  or benchmark tracks, use child workstreams or execution waves instead of
  hiding them in one note.
- Keep release-adjacent Registry, Atlas, Casebook, and Compass truth current
  in the same change whenever maintainer work reveals a new failure mode, a
  stale diagram, a changed benchmark story, or a boundary that needs a
  first-class component spec.
- When release work changes the public benchmark story, update the maintainer
  guidance, maintainer skill, generator contract, and repo-root `README.md` in
  the same change.

## Frozen And Coupled Product Contracts
- The dashboard surface header is a non-negotiable frozen contract in this
  maintainer lane across both pinned dogfood and detached `source-local`
  posture.
- Do not add, remove, rename, reorder, restyle, repurpose, or otherwise
  tamper with header labels, text, buttons, controls, badges, tabs, version
  readouts, or any other UI artifact in that header.
- Do not use adjacent dashboard, onboarding, release-note, maintainer-note, or
  shell-polish work as justification for touching the header.
- Treat authored release-note markdown as the single source of truth for the
  consumer upgrade spotlight. For release-facing shell copy, land or update
  `odylith/runtime/source/release-notes/vX.Y.Z.md` first, mirror it into the
  bundle assets, and prove the popup from that exact note instead of patching
  shell-only spotlight text in parallel.
- Treat the release version bump as separate tracked truth, not an implication
  of authored notes or overrides. Before canonical `make release-preflight`
  for `vX.Y.Z`, synchronize `pyproject.toml`,
  `src/odylith/__init__.py`, and
  `odylith/runtime/source/product-version.v1.json` on the release branch.
- Before GA, keep first-party GitHub Actions pins in release,
  release-candidate, and test workflows on current immutable SHAs that no
  longer carry scheduled runtime deprecation warnings into the release lane.

## Source File Discipline
- The repo-root `800`/`1200`/`2000+` thresholds and `1500` LOC test ceiling
  are non-negotiable for hand-maintained Odylith product source in this
  maintainer lane.
- Any maintainer change that grows a hand-maintained source file past `1200`
  LOC needs an explicit exception and decomposition plan, and any
  hand-maintained source file over `2000` LOC must already have an active
  decomposition workstream before more feature growth lands in it.
- In detached `source-local` maintainer dev posture, no red-zone file may take
  net new unrelated feature growth without a same-change ownership extraction
  or decomposition cut. "We will clean it later" is not an acceptable
  maintainer closeout posture for `2000+` LOC source files.
- Apply the same bar to giant functions: a touched `500+` LOC function needs a
  same-change phase extraction unless the change is purely a safety-critical
  repair, and a touched `900+` LOC function is red-zone monolith debt that may
  not take unrelated growth without a same-change decomposition cut.
- When maintainer work touches a hand-maintained source file that is already
  beyond those thresholds, the default action is refactor-first work: split
  it into multiple focused files or modules with robustness, reliability, and
  reusability as explicit goals instead of continuing to extend the oversized
  file.
- Generated or mirrored bundle assets are excluded; govern their
  source-of-truth files instead.
- Prefer targeted decompositions by size x churn x centrality with
  characterization tests first instead of turning release pressure into a
  repo-wide "all files above X" rewrite.

## Generated And Derived Artifact Rules
- When generated surfaces or bundled guidance change, validate both the
  source artifact and the shipped mirror instead of trusting one side alone.
- After changing shell, Compass, Casebook, or other checked-in governed
  surface source truth, rerender the affected tracked surfaces before
  interpreting browser failures. Stale generated artifacts are not evidence
  that the live product contract is still broken.
- Treat parent-shell freshness and child-surface freshness as separate
  truths. A successful wrapper refresh is never enough evidence to imply
  Compass, Radar, Atlas, Registry, or Casebook data is current unless the
  child runtime or surface contract says it was rerendered or the shell
  explicitly projects the gap.
- Treat verifier-warning cleanup as incomplete unless successful verification
  stays calm in the full shipped lane: hosted installer, pinned dogfood,
  consumer rehearsal, and GA gate.
- Do not hand-edit generated benchmark snapshot files when the publication
  writer can derive them from the validated report.
- Do not hand-edit the SVGs in `docs/benchmarks/`.

## Validation And Test Design
- Every maintainer coding change should carry focused validation that proves
  the real contract touched by the change.
- Before GA, keep release-proof unit lanes environment-portable. If a test is
  supposed to prove proof-host native spawn behavior or proof-host CLI
  execution, force or mock that contract inside the test instead of inheriting
  the maintainer machine's ambient host or runtime state.
- Explicit operator-requested Compass `full` refresh is a proof contract in
  this maintainer lane: do not accept a passing result that reused the wrong
  recent runtime payload, landed on deterministic local brief output, or
  skipped browser proof across the required views. The five-minute reuse clamp
  itself is valid, but any reused payload must already satisfy the requested
  full-refresh truth contract.
- Use pinned dogfood whenever the question is "does the shipped Odylith
  runtime behave correctly?". Use detached `source-local` only when the
  question is "do these unreleased `src/odylith/*` changes execute
  correctly?". In that detached posture, use `make dev-validate` for the
  maintainer validation lane rather than treating `make release-preflight` as
  a current-workspace proof command.

## Installer And Compatibility Engineering
- Keep hosted installer generation compatible with the last shipped runtime
  exercised by release smoke. When installer behavior differs between fresh
  and existing repos, branch on repo state using stable commands instead of
  assuming a newly added hidden CLI flag already exists in older shipped
  versions.
- Keep generated hosted installer shell templates strict-mode safe. If the
  template runs under `set -euo pipefail`, initialize every optional local
  before testing it and prove the nested fresh-install path in canonical smoke
  before trusting the change.

## Benchmark Harness And Graph Engineering
- The raw Codex CLI lane must not inherit repo-authored or user-authored
  guidance by accident. The live benchmark runner should use a temporary
  Codex home that keeps auth plus the pinned model and reasoning contract
  while dropping local developer instructions, plugins, MCP config, and
  project-doc fallback. Disposable workspaces should strip auto-consumed
  instruction entrypoints such as `AGENTS.md`, `CLAUDE.md`, `.cursor/`,
  `.windsurf/`, and `.codex/` while preserving truth-bearing repo docs for
  explicit reads.
- Runtime optimizations must stay isolation-safe. The only approved benchmark
  batching is the isolated same-scenario public live pair after request
  preparation. Packet-building and other global-state-sensitive phases stay
  serial.
- On strict bounded proof slices, keep Odylith's live handoff equally strict:
  if the truthful required surface is already the listed anchor set, or the
  family is an exact-path ambiguity probe, suppress supplemental docs,
  implementation anchors, and retrieval-plan doc spillover instead of letting
  `odylith_on` widen by accident.
- On those strict bounded proof slices, validator-only tests and generated or
  rendered artifacts are coverage evidence, not approved first-pass reads,
  unless a focused contradiction points directly at them.
- Benchmark README snapshots, generated summaries, and SVGs must all come from
  the same selected `latest.v1.json` proof artifact. Do not mix cache
  profiles, partial shard snapshots, or hand-picked generated outputs and then
  present them as one benchmark truth.
- Preserve the current three benchmark graph filenames and the repo-root
  `README.md` graph block order:
  1. `odylith-benchmark-family-heatmap.svg`
  2. `odylith-benchmark-operating-posture.svg`
  3. `odylith-benchmark-frontier.svg`
- Preserve the current visual tone and chart semantics from
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py` unless the
  benchmark harness itself changes materially.
- If the graph style changes intentionally, update the generator, the
  `README.md` benchmark section, and
  `tests/unit/runtime/test_odylith_benchmark_graphs.py` in the same change so
  the new style becomes the maintained contract.
