# Release Benchmarks

Scope: Odylith product maintainers in `/Users/freedom/code/odylith` only.

Do not treat this as consumer guidance. Consumer repos should not own or
execute the Odylith release benchmark publishing lane.

Maintainer-side coding, validation-design, generated-artifact authoring,
benchmark harness implementation, graph contract, and branch/write safety
rules live in [CODING_STANDARDS.md](./CODING_STANDARDS.md). This document owns
the release-proof metrics, publication flow, and benchmark narrative.

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
  untracked shell-only exception. If the override decision happens after a
  proof run already started, stop the run, capture the blocker in Casebook,
  and keep the release narrative explicit that the version is benchmark
  advisory rather than benchmark re-proved.

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
  lanes run through the same live host CLI model and reasoning contract.
  Current published release proof remains Codex-host-scoped until another host
  clears the same publication lane.
- That public pair now means `full_product_assistance_vs_raw_agent`, not a
  narrower grounding-only claim. If Odylith uses selected docs,
  execution-governance hints, focused-check shaping, or logged disposable-
  workspace preflight evidence by design, the report and docs must declare
  that explicitly.

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
- include external-wait or resume cases and destructive-scope fail-closed cases
- keep the published proof conservative across warm and cold profiles
- keep the tracked corpus above the seriousness floor:
  `60` implementation scenarios, `35` write-plus-validator scenarios,
  `12` correctness-critical scenarios, mechanism-heavy implementation share at
  or below `40%`, and explicit family coverage for API evolution, stateful
  recovery, external dependency recovery, and destructive-scope control

## Working Posture
- For release and benchmark publication, pinned dogfood is the authoritative
  proof lane. Detached `source-local` may help with source work, but it does
  not substitute for shipped-runtime proof.
- Post-run adoption-proof sampling is supplementary. It must be bounded and
  degrade cleanly on timeout or transport loss instead of blocking persistence
  of a completed full proof report.
- Because the public live pair may run concurrently, maintainer writeups must
  label published timing as benchmark time to valid outcome, not as claimable
  solo-user latency.
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
- If a release note, benchmark writeup, or maintainer demo needs to show the
  conversation-observation experience itself, preserve the shipped
  `**Odylith Observation**` / `**Odylith Proposal**` labels, the fixed
  confirmation text, and the human default voice. Do not benchmark or publish
  a colder mechanical placeholder just because the lane is maintainer-facing.
- Those maintainer-facing examples must also stay prompt-rooted. Do not stage
  demo or benchmark artifacts that reconstruct the experience from terse
  `Odylith Proposal pending.`-style summaries when the richer markdown and
  human prompt context are available.

## Canonical Inputs
- Machine-readable report:
  `.odylith/runtime/odylith-benchmarks/latest.v1.json`
- Publication snapshot writer:
  `src/odylith/runtime/evaluation/odylith_benchmark_publication.py`
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
   `--family` and/or `--shard-count ... --shard-index ...`, then rebuild one
   completed full proof report before publication. For full-corpus shard
   splits, merge the shard history reports with
   `PYTHONPATH=src python3 -m odylith.runtime.evaluation.odylith_benchmark_shard_merge --repo-root . <report-id>...`
   so `latest.v1.json` still comes from one complete proof artifact rather than
   a partial shard snapshot.
2. Regenerate the README SVG assets from the latest report:
   `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
3. Refresh the benchmark snapshot docs and tracked summary from that same
   selected report:
   `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_publication --repo-root .`
   This refreshes:
   - `docs/benchmarks/LIVE_BENCHMARK_SNAPSHOT.md`
   - `docs/benchmarks/GROUNDING_BENCHMARK_SNAPSHOT.md`
   - `docs/benchmarks/BENCHMARK_TABLES.md`
   - `docs/benchmarks/latest-summary.v1.json`
4. Update the repo-root `README.md` benchmark snapshot from that same
   `latest.v1.json` report.
   README numbers and wording must describe the conservative published view,
   not the easiest single-profile snapshot. The public table should center on
   `odylith_on` and `odylith_off`; `odylith_on_no_fanout` and the repo-scan
   lane stay in the internal tracked report for diagnosis.
   If the report came from detached `source-local`, say that explicitly and
   keep the first-release baseline warning visible until
   `docs/benchmarks/release-baselines.v1.json` records a shipped proof.
5. Keep the README benchmark section explicitly Codex-labeled.
6. Validate the graph contract with:
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
- The public comparison must also stay fairness-clean: no undeclared Odylith
  lane affordances, no missing raw prompt-visible path credit, and no report
  that hides comparison-contract or preflight-evidence state.
- README and graph wording must keep the measurement basis explicit:
  conservative same-scenario warm/cold publication, time to valid outcome,
  live agent runtime, validator overhead, and full-session token spend are
  distinct metrics.
- `odylith_off` is the reviewer-facing and README-facing name for the raw
  host CLI lane. `raw_agent_baseline` is only the internal report alias.
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

## Graph And Generated Asset Editing
- Generator, SVG, README-coupling, and graph-test maintenance rules live in
  [CODING_STANDARDS.md](./CODING_STANDARDS.md). Keep this file focused on the
  release benchmark proof and publication contract.

## Separation Rule
- This maintainer release-benchmark lane belongs only to the Odylith product
  repo.
- Do not mirror this guidance into bundled consumer-side `odylith/`
  instructions or consumer skills.
