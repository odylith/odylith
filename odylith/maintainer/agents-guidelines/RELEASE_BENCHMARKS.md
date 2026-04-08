# Release Benchmarks

Scope: Odylith product maintainers in `/Users/freedom/code/odylith` only.

Do not treat this as consumer guidance. Consumer repos should not own or
execute the Odylith release benchmark publishing lane.

## Core Rule
- Every Odylith release candidate must refresh the Codex benchmark report,
  regenerate the benchmark SVGs, and update the repo-root `README.md`
  benchmark snapshot before `make release-preflight`.
- The published benchmark snapshot must come from
  `./.odylith/bin/odylith benchmark --repo-root . --profile proof`, not from
  the default quick lane, a warm-only rerun, or any other hand-picked report.
- The only supported exception is a version-scoped maintainer override
  recorded in `odylith/runtime/source/release-maintainer-overrides.v1.json`.
  That override may downgrade benchmark proof and compare from blocking to
  advisory for one named release version, but it must never become an
  untracked shell-only exception.

## Integrity Non-Negotiable
- Never game the eval.
- Proof trumps diagnostic. If the lanes disagree, optimize to the proof result
  and treat diagnostic only as a mechanism clue for why proof moved.
- Never accept a speed or token win that regresses recall, accuracy, or
  precision.
- Do not remove hard scenarios, loosen required paths, weaken validation
  commands, or narrow the publication lane just to improve the score.
- Do not publish stale, hand-picked, or cross-profile-mixed numbers as if they
  were the benchmark truth.
- If a harder honest corpus makes Odylith look worse, publish the honest result
  and improve the product or the corpus truth instead of sanding the eval down.
- Treat recall, accuracy, and precision as the hard floor. Improving latency or
  budget while weakening those core quality metrics is a benchmark failure, not
  a release win.
- Benchmark changes are only valid when they make the workload more realistic,
  the scoring more conservative, or the proof more reproducible.
- The honest public pair is `odylith_on` versus `odylith_off`, where both
  lanes run through the same live Codex CLI model and reasoning contract.

## Metric Order
Evaluate Odylith benchmark outcomes in this order:
1. correctness and non-regression
2. grounding recall and precision
3. validation success and execution fit
4. robustness and consistency across warm or cold cache state, retries, and recovery
5. latency to a valid outcome
6. prompt and payload efficiency
7. bounded behavior under tighter token budgets

The release decision rule is simple: a lower-tier win never excuses a higher-tier
regression. Faster, cheaper, or smaller does not count if Odylith became less
correct, less grounded, less precise, or less reliable.

Benchmark-lane priority is also explicit:

- `proof` is the governing product comparison and the primary optimization
  target
- `diagnostic` is an internal tuning surface and only counts when it preserves
  or improves `proof`

Status semantics are explicit:

- `Hard quality gate`
  - tiers `1-4`
  - any regression here keeps the benchmark on `hold`
- `Secondary guardrails`
  - tiers `5-7`
  - packet-backed live-proof tighter-budget behavior remains status-blocking
  - time to valid outcome and full-session token spend stay published as
    diagnostics on the live proof lane because they are not solo-user latency
    or initial prompt size
- `Advisory mechanism checks`
  - packet coverage, widening frequency, route posture, and similar mechanism
    signals stay published, but they are not the same thing as the hard
    outcome gate by themselves

Current live-proof secondary guardrail:
- `within_budget_rate` must stay at or above `0.80` on packet-backed sampled slices

Current diagnostic-lane efficiency guardrails:
- median prompt-bundle delta must stay at or below `+64 tokens`
- median total-payload delta must stay at or below `+96 tokens`

The benchmark itself must also stay representative:
- include small, medium, and large or complex repo work
- include single-file, cross-file, and cross-surface changes
- include critical correctness and recovery-sensitive cases
- keep the published proof conservative across warm and cold profiles

## Working Posture
- Use Odylith-first maintainer workflows when inspecting release readiness,
  dogfood posture, benchmark outputs, and runtime state: prefer `status`,
  `doctor`, `benchmark`, and `validate self-host-posture` before ad-hoc repo
  search.
- Maintainer benchmark work never happens directly on `main`. If the slice
  needs code, docs, or any other tracked repo edits while the current branch
  is `main`, create and switch to a fresh branch before the first edit. If
  work is already on a non-`main` branch, keep using that branch and return to
  canonical `origin/main` only for read-only inspection or release proof.
- Maintainer benchmark work follows the same source-file size discipline as the
  rest of the product repo: `800` LOC soft limit, `1200` LOC explicit
  exception and decomposition-plan trigger, `2000+` red-zone exception only,
  and a `1500` LOC ceiling for tests.
- If benchmark or release work touches a hand-maintained source file already
  beyond those thresholds, treat the change as refactor-first work: split it
  into multiple focused files or modules with robustness, reliability, and
  reusability as explicit goals instead of continuing to grow the oversized
  file in place.
- For release and benchmark publication, pinned dogfood is the authoritative
  proof lane. Detached `source-local` may help with source work, but it does
  not substitute for shipped-runtime proof.
- Post-run adoption-proof sampling is supplementary. It must be bounded and
  degrade cleanly on timeout or transport loss instead of blocking persistence
  of a completed full proof report.
- The raw Codex CLI lane must not inherit repo-authored or user-authored
  guidance by accident. The live benchmark runner should use a temporary
  Codex home that keeps auth plus the pinned model/reasoning contract while
  dropping local developer instructions, plugins, MCP config, and project-doc
  fallback, and the disposable workspace should strip auto-consumed
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
- Because the public live pair may run concurrently, maintainer writeups must
  label published timing as benchmark time to valid outcome, not as claimable
  solo-user latency.
- Benchmark-story work still runs through Odylith's governance loop: search the
  active workstream, bound plan, related bugs, related components, related
  diagrams, and recent Compass/session context first; extend or reopen existing
  truth before creating new records.
- If the benchmark slice is genuinely new, create the missing workstream and
  bound plan before non-trivial publishing changes; if the work spans corpus,
  graphs, and release communication simultaneously, split it with child
  workstreams or execution waves instead of flattening it into one note.
- When benchmark work exposes a new failure mode, stale diagram, or thin
  component boundary, update Casebook, Atlas, Registry, and Compass in the same
  slice instead of leaving that bookkeeping for later.
- Use direct `rg`, source reads, or generator inspection only when Odylith
  reports ambiguity or fallback, or when you need to verify a runtime-generated
  claim against tracked source truth.
- This matches the benchmark contract: recall, accuracy, precision, and
  validation are the hard floor, so speed or token wins do not justify
  bypassing Odylith's own narrowing and proof surfaces.
- Release notes, benchmark writeups, and maintainer handoffs may include at
  most one short end-of-work `Odylith Assist:` line after the measured result
  is already clear. Back it with measured proof and follow the canonical
  closeout contract in
  [Odylith Chatter](../../registry/source/components/odylith-chatter/CURRENT_SPEC.md)
  instead of restating the full branding rubric here. It is a summary aid, not
  the headline proof.

## Canonical Inputs
- Machine-readable report:
  `.odylith/runtime/odylith-benchmarks/latest.v1.json`
- Graph generator:
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`
- Published README benchmark section:
  repo-root `README.md`
- Published SVG outputs:
  - `docs/benchmarks/odylith-benchmark-family-heatmap.svg`
  - `docs/benchmarks/odylith-benchmark-operating-posture.svg`
  - `docs/benchmarks/odylith-benchmark-frontier.svg`

## Required Maintainer Flow
1. Run the current Codex benchmark corpus:
   `./.odylith/bin/odylith benchmark --repo-root . --profile proof`
   The default `quick` lane is developer signal only. Release proof must cover
   both `warm` and `cold` cache profiles and the full-corpus live
   `odylith_on` versus `odylith_off` pair. Packet-and-prompt diagnostics and
   extra control lanes are internal tuning surfaces, not the publication
   contract.
   When the full proof is too large for one local sitting, split it with
   `--family` and/or `--shard-count ... --shard-index ...`, then only publish
   from a completed full proof run.
2. Regenerate the README SVG assets from the latest report:
   `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
3. Update the repo-root `README.md` benchmark snapshot from that same
   `latest.v1.json` report.
   README numbers and wording must describe the conservative published view,
   not the easiest single-profile snapshot. The public table should center on
   `odylith_on` and `odylith_off`; `odylith_on_no_fanout` and the repo-scan
   lane stay in the internal tracked report for diagnosis.
   If the report came from detached `source-local`, say that explicitly and
   keep the first-release baseline warning visible until
   `docs/benchmarks/release-baselines.v1.json` records a shipped proof.
4. Keep the README benchmark section explicitly Codex-labeled.
5. Validate the graph contract with:
   `PYTHONPATH=src pytest -q tests/unit/runtime/test_odylith_benchmark_graphs.py`

## Publication Contract
- `latest.v1.json` is only release-safe when the selected Codex cache profiles
  all clear the hard quality gate and the published comparison also
  stays inside the explicit lower-tier guardrails whenever the compared lanes
  both produce successful outcomes.
- A detached `source-local` full proof may refresh the current source-tree
  benchmark story, but it does not remove the separate pinned-dogfood release
  proof obligation or the first shipped release-baseline requirement.
- The public comparison must stay conservative across the selected cache
  profiles.
- README and graph wording must keep the measurement basis explicit:
  conservative same-scenario warm/cold publication, time to valid outcome,
  live agent runtime, validator overhead, and full-session token spend are
  distinct metrics.
- `odylith_off` is the reviewer-facing and README-facing name for the raw
  Codex CLI lane. `raw_agent_baseline` is only the internal report alias.
- The primary honest benchmark comparison is `odylith_on` versus
  `odylith_off`.
- If Odylith is named in benchmark prose beyond lane labels, keep that to one
  end-of-work `Odylith Assist:` line grounded in the measured report. Follow
  [Odylith Chatter](../../registry/source/components/odylith-chatter/CURRENT_SPEC.md)
  for the detailed wording contract, avoid mid-analysis brand narration, and
  keep the benchmark lane metadata-only instead of widening required reads just
  to narrate Odylith.
- The public README headline table should keep `odylith_repo_scan_baseline`
  out of the primary story; it remains a secondary scaffold control in the
  tracked report and must never be described as `Odylith off`.
- Do not publish `primary_comparison` or a warm-only green report in README
  when the conservative published view is weaker.

## Graph Contract
- Do not hand-edit the SVGs in `docs/benchmarks/`.
- Preserve the current three-graph set and filenames.
- Preserve the current visual tone and chart semantics from
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`:
  - warm paper background and panel styling
  - red baseline marks for Odylith-off / `raw_agent_baseline`
  - teal Odylith marks for Odylith-on
  - family heatmap for per-family deltas
  - operating-posture view for packet, readiness, and runtime posture
  - frontier view for time to valid outcome vs live session input
- Preserve the repo-root `README.md` graph block order exactly:
  1. `odylith-benchmark-family-heatmap.svg`
  2. `odylith-benchmark-operating-posture.svg`
  3. `odylith-benchmark-frontier.svg`
- Preserve the current Codex framing in graph titles, subtitles, legends, and
  README copy unless the benchmark harness itself changes.
- If the graph style ever changes intentionally, update the generator, the
  README section, and `tests/unit/runtime/test_odylith_benchmark_graphs.py` in
  the same change so the new style becomes the maintained contract.

## Separation Rule
- This maintainer release-benchmark lane belongs only to the Odylith product
  repo.
- Do not mirror this guidance into bundled consumer-side `odylith/`
  instructions or consumer skills.
