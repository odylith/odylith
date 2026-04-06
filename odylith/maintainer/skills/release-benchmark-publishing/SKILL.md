# Release Benchmark Publishing

Use this skill only in the Odylith product repo when preparing a release or
refreshing the public benchmark story in the repo-root `README.md`.

Do not use this skill in consumer repos.

## Maintainer Mode
- Use pinned dogfood when proving the shipped benchmark and release story.
- Use detached `source-local` only when current unreleased `src/odylith/*`
  changes need to execute before you return to pinned dogfood for proof.
- Source-tree-only helpers such as the benchmark graph generator or source-tree
  pytest commands may run on the product repo toolchain with `PYTHONPATH=src`;
  that is a maintainer dev detail, not a consumer contract.

## Goal
- Recover and maintain the governed release slice while refreshing the public
  benchmark story.
- Refresh the current Codex benchmark snapshot.
- Regenerate the canonical README benchmark SVGs.
- Update the repo-root `README.md` benchmark numbers and wording from the same
  benchmark report.
- Preserve the current benchmark graph style and tone across releases.
- Publish only the conservative `--profile proof` Codex view, not the default
  quick lane or the most flattering single-profile report.
- Treat `proof` as the governing product benchmark and `diagnostic` as a
  secondary tuning surface. A diagnostic gain does not count if it hurts the
  live `proof` result.

## Canonical Files
- Benchmark report:
  `.odylith/runtime/odylith-benchmarks/latest.v1.json`
- README:
  `README.md`
- Graph generator:
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`
- Graph outputs:
  - `docs/benchmarks/odylith-benchmark-family-heatmap.svg`
  - `docs/benchmarks/odylith-benchmark-quality-frontier.svg`
  - `docs/benchmarks/odylith-benchmark-frontier.svg`
  - `docs/benchmarks/odylith-benchmark-operating-posture.svg`
- Maintainer rule:
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

## Canonical Flow
1. Recover the current governed slice with Odylith first:
   search the active workstream, bound plan, related bugs, related components,
   related diagrams, and recent Compass/session context; extend or reopen
   existing truth before creating new records.
2. If the benchmark-publication slice is genuinely new, create the missing
   workstream and bound plan before non-trivial publishing changes; if the work
   spans multiple release lanes, split it with child workstreams or execution
   waves.
3. Run the Codex benchmark corpus:
   `./.odylith/bin/odylith benchmark --repo-root . --profile proof`
   The default `quick` lane is developer signal only. Use `proof` so
   `latest.v1.json` covers both `warm` and `cold` for the live
   `odylith_on` versus `odylith_off` pair. If internal tuning needs isolated
   packet or prompt measurements, run `--profile diagnostic` separately and do
   not publish that as the product comparison. If the proof run needs to be
   split operationally, use deterministic `--family` or shard flags and
   publish only from the completed full proof report.
4. Regenerate the graph assets from the latest report:
   `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
5. Update the repo-root `README.md` benchmark snapshot from that same report.
   Make the README explicit that the snapshot is Codex-only and conservative
   across the published cache profiles, that `odylith_off` is the raw Codex
   CLI lane, that `raw_agent_baseline` is only the internal report alias, and
   that `odylith_repo_scan_baseline` is only a secondary scaffold control kept
   in the tracked report rather than the headline public table.
   The README should also stay explicit that the public pair uses the same
   live Codex CLI model and reasoning contract with an isolated temporary
   Codex home and stripped repo-authored guidance surfaces, that published
   timing is benchmark time to valid outcome rather than solo-user latency, and
   that published token cost is full-session spend rather than the initial
   prompt size.
   If the report came from detached `source-local`, say that explicitly and
   keep the first-release baseline warning visible until
   `docs/benchmarks/release-baselines.v1.json` records a shipped proof.
   When a proof slice is intentionally strict-bounded, keep that contract
   visible in the narrative: supplemental docs and implementation anchors may
   be suppressed when the truthful required surface is already the listed
   anchor set, and validator-only tests or generated artifacts do not count as
   approved first-pass reads unless a focused contradiction points directly
   there.
   If the closeout would benefit from naming Odylith directly, keep it to one
   short end-of-work `Odylith assist:` line backed by measured proof, and
   follow the detailed wording contract in
   [Odylith Chatter](../../registry/source/components/odylith-chatter/CURRENT_SPEC.md)
   instead of expanding the benchmark lane's own prompt tax.
6. Keep the README graph order and tone unchanged unless the product is intentionally adding benchmark-marketing cuts from the same report:
   - family heatmap
   - quality frontier
   - frontier
   - operating posture
7. Keep the README graph block in this exact order:
   - `odylith-benchmark-family-heatmap.svg`
   - `odylith-benchmark-quality-frontier.svg`
   - `odylith-benchmark-frontier.svg`
   - `odylith-benchmark-operating-posture.svg`
8. If the benchmark slice surfaced a named failure mode, stale diagram, or thin
   component boundary, update Casebook, Atlas, Registry, and Compass in the
   same change.
9. Run:
   `PYTHONPATH=src pytest -q tests/unit/runtime/test_odylith_benchmark_graphs.py`

## Non-Negotiables
- The README benchmark section must stay explicitly Codex-labeled.
- The README benchmark section must describe the conservative published view,
  not `primary_comparison` when they differ.
- Benchmark status semantics must stay explicit:
  - correctness, grounding, validation/fit, and robustness are the hard gate
  - tighter-budget behavior is the live-proof secondary guardrail
  - time to valid outcome and full-session token spend stay published as
    live-proof diagnostics, not solo-user or initial-prompt claims
  - prompt/payload efficiency thresholds belong to the diagnostic lane
  - packet coverage, widening frequency, route posture, and similar mechanism
    signals stay published as advisory context
  - current live-proof guardrail is `within_budget_rate >= 0.80`
- Benchmark publication does not waive Odylith governance upkeep: do not leave
  the workstream, plan, bug memory, component specs, diagrams, or Compass
  context stale after changing the public benchmark story.
- Do not substitute screenshots, ad hoc chart exports, or different filenames.
- Do not hand-edit the generated SVGs.
- Preserve the current beige/paper visual direction, red baseline marks, teal
  Odylith marks, and the current benchmark-graph narrative unless the product
  is making an intentional benchmark-style redesign.
- `odylith_off` in README, graphs, and review framing is the raw Codex CLI
  lane. `raw_agent_baseline` is only the internal report alias for that lane.
- `odylith_repo_scan_baseline` is the repo-scan scaffold control, not the
  honest no-scaffold baseline, and it should stay out of the primary public
  README table.
- The public pair must hold the same live Codex CLI model and reasoning
  contract on both lanes, and it must run with an isolated temporary Codex
  home plus stripped repo-authored guidance surfaces instead of inheriting
  local skills, plugins, MCP config, or `AGENTS.md` state by accident.
- Post-run adoption-proof sampling is supplementary. It must be bounded and
  degrade cleanly on timeout or transport loss instead of blocking
  persistence of a completed full proof report.
- Any Odylith-by-name closeout note must stay final-only, soulful,
  friendly, authentic, and factual, and it must point to concrete measured
  proof rather than generic product praise. Follow the canonical closeout
  contract in
  [Odylith Chatter](../../registry/source/components/odylith-chatter/CURRENT_SPEC.md).
- If the style changes intentionally, update the generator, README, and graph
  tests in the same change.
