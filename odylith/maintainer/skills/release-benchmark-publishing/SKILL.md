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
- Refresh the current published proof-host benchmark snapshot.
- Regenerate the canonical README benchmark SVGs.
- Update the repo-root `README.md` benchmark numbers and wording from the same
  benchmark report.
- Preserve the current benchmark graph style and tone across releases.
- Publish only the conservative `--profile proof` view for the current proof host, not the default
  quick lane or the most flattering single-profile report.
- Treat `proof` as the governing product benchmark and `diagnostic` as a
  secondary tuning surface. A diagnostic gain does not count if it hurts the
  live `proof` result.

## Canonical Files
- Benchmark report:
  `.odylith/runtime/odylith-benchmarks/latest.v1.json`
- Release planning registry:
  `odylith/radar/source/releases/releases.v1.json`
- Release planning history:
  `odylith/radar/source/releases/release-assignment-events.v1.jsonl`
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
   Treat repo-local release planning as part of that same governed slice:
   inspect `odylith release list --repo-root .` and
   `odylith release show current --repo-root .` when the benchmark story is
   preparing a release-bound candidate.
2. If the benchmark-publication slice is genuinely new, create the missing
   workstream and bound plan before non-trivial publishing changes; if the work
   spans multiple release lanes, split it with child workstreams or execution
   waves.
3. Reconcile release-planning truth for the candidate version before changing
   public copy:
   - ensure the candidate release record carries the correct `version` or tag
   - if the matching authored release note already exists, leave `name` empty
     to inherit the note title or set that exact same title
   - move any carry-forward workstreams to the follow-on release instead of
     leaving them attached to the shipped line in public-facing planning truth
4. Run the release-proof benchmark corpus:
   `./.odylith/bin/odylith benchmark --repo-root . --profile proof`
   The default `quick` lane is developer signal only. Use `proof` so
   `latest.v1.json` covers both `warm` and `cold` for the live
   `odylith_on` versus `odylith_off` pair. If internal tuning needs isolated
   packet or prompt measurements, run `--profile diagnostic` separately and do
   not publish that as the product comparison. If the proof run needs to be
   split operationally, use deterministic `--family` or shard flags and
   publish only from the completed full proof report. For full-corpus shard
   splits, merge the shard history reports with
   `PYTHONPATH=src python3 -m odylith.runtime.evaluation.odylith_benchmark_shard_merge --repo-root . <report-id>...`
   before regenerating graphs or README copy. If maintainers activate a
   version-scoped benchmark override instead, stop the in-flight proof run,
   record the override in `odylith/runtime/source/release-maintainer-overrides.v1.json`,
   and update Casebook plus the bound release workstream and plan before
   continuing the release lane.
5. Regenerate the graph assets from the latest report:
   `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
6. Update the repo-root `README.md` benchmark snapshot from that same report.
   Make the README explicit that the current published snapshot is Codex-host-scoped and conservative
   across the published cache profiles, that `odylith_off` is the raw host
   CLI lane, that `raw_agent_baseline` is only the internal report alias, and
   that `odylith_repo_scan_baseline` is only a secondary scaffold control kept
   in the tracked report rather than the headline public table.
   The README should also stay explicit that the public pair uses the same
   live proof-host CLI model and reasoning contract with an isolated temporary
   host home and stripped repo-authored guidance surfaces, that published
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
   short end-of-work `Odylith Assist:` line backed by measured proof, and
   follow the detailed wording contract in
   [Odylith Chatter](../../registry/source/components/odylith-chatter/CURRENT_SPEC.md)
   instead of expanding the benchmark lane's own prompt tax.
7. Keep the README graph order and tone unchanged unless the product is intentionally adding benchmark-marketing cuts from the same report:
   - family heatmap
   - quality frontier
   - frontier
   - operating posture
8. Keep the README graph block in this exact order:
   - `odylith-benchmark-family-heatmap.svg`
   - `odylith-benchmark-quality-frontier.svg`
   - `odylith-benchmark-frontier.svg`
   - `odylith-benchmark-operating-posture.svg`
9. If the benchmark slice surfaced a named failure mode, stale diagram, or thin
   component boundary, update Casebook, Atlas, Registry, and Compass in the
   same change.
10. Run:
   `PYTHONPATH=src pytest -q tests/unit/runtime/test_odylith_benchmark_graphs.py`

## Non-Negotiables
- The README benchmark section must stay explicit about the current proof host.
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
- When the benchmark story is release-bound, do not let public benchmark copy
  drift from repo-local release planning truth. Candidate release naming,
  carried work, and `current` or `next` alias ownership must agree with the
  release note and the public launch framing.
- Do not substitute screenshots, ad hoc chart exports, or different filenames.
- Do not hand-edit the generated SVGs.
- Preserve the current beige/paper visual direction, red baseline marks, teal
  Odylith marks, and the current benchmark-graph narrative unless the product
  is making an intentional benchmark-style redesign.
- `odylith_off` in README, graphs, and review framing is the raw host CLI
  lane. `raw_agent_baseline` is only the internal report alias for that lane.
- `odylith_repo_scan_baseline` is the repo-scan scaffold control, not the
  honest no-scaffold baseline, and it should stay out of the primary public
  README table.
- The public pair must hold the same live proof-host CLI model and reasoning
  contract on both lanes, and it must run with an isolated temporary host
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
