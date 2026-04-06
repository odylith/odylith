Status: In progress

Created: 2026-03-31

Updated: 2026-04-05

Backlog: B-022

Goal: Make `raw_agent_baseline` the true honest Odylith benchmark baseline,
make `odylith_off` its explicit alias, demote the repo-scan lane to an
explicitly secondary scaffold control, and
expand the benchmark corpus while materially improving `odylith_on` against
`odylith_off` through tighter hot-path selection, smaller truthful packets,
and more honest diagnostics instead of a thin snapshot or a flattering story.

Assumptions:
- `raw_agent_baseline` is the honest same-agent, same-repo, no-scaffold
  comparison the benchmark should optimize around first, and `odylith_off`
  should resolve to that same lane everywhere.
- `odylith_repo_scan_baseline` is still useful, but only as a secondary
  control that shows how much precomputed repo-scan scaffolding itself is
  helping.
- A benchmark that honestly compares Odylith to raw Codex may show Odylith as
  slower or more expensive on lower-tier metrics; that is acceptable if the
  higher-tier quality metrics improve.
- The current full source-local proof report `52aa3f76538cf12f` is the latest
  green benchmark posture, while proof report `926bfeab4e887ade` remains the
  protected earlier floor for live quality and efficiency wins and diagnostic
  report `74cbe36427f2c375` remains the protected grounding floor.
- The first passing release should come from the current local LanceDB plus
  Tantivy stack; Vespa remains optional and disabled for the published proof.

Constraints:
- Do not soften the benchmark corpus or weaken validation to flatter Odylith.
- Make `raw_agent_baseline` the explicit primary benchmark comparison without
  removing the repo-scan control from the tracked internal report.
- Keep old report history readable even if the primary baseline contract
  changes.
- Expand the corpus with real additional scenarios instead of relabeling the
  same 24 cases as if the suite became deeper.
- Improve the weak families without using benchmark labels or scenario ids as
  runtime shortcuts.
- Keep benchmark warm preflight fail-closed on empty guidance catalogs and do
  not publish any proof that depends on a zero-guidance benchmark posture.
- Do not make hybrid rerank, Vespa, or any other remote augmentation a
  prerequisite for the first passing proof lane.

Reversibility: Reverting this slice restores the prior contract where the
repo-scan lane acted as the primary benchmark baseline, reduces the corpus
back toward the thinner 24-scenario floor, and removes the stronger honest
baseline story from the README, guidance, and report contract.

Boundary Conditions:
- Scope includes the benchmark runner contract, benchmark corpus, benchmark
  docs, README snapshot table, benchmark component spec, benchmark proof
  diagram, Radar workstream truth, maintainer guidance and skills, and focused
  unit tests.
- Scope excludes hosted eval infrastructure and Claude-native benchmark
  publication.

Related Bugs:
- `CB-027` live benchmark harness still leaks ambient workstation or repo state
  into the raw-Codex control unless the strict sandbox contract holds.
- `CB-029` live benchmark prompt handoff previously dropped Odylith-selected
  docs before the Codex run, corrupting required-path accuracy and prompt-token
  accounting.
- `CB-030` benchmark sandbox strip rules previously deleted truth-bearing
  maintainer docs from disposable worktrees, making some required paths
  unreachable during supposedly fair live runs.
- `CB-031` live observed-path attribution previously counted transitive file
  links printed inside doc contents as if those linked files were directly
  inspected, overstating Odylith surface spread.
- `CB-032` relative latency and token guardrails previously stayed active even
  when `odylith_off` produced no successful outcomes, so faster failure could
  block status against a quality-clearing Odylith run.
- `CB-028` benchmark gate could previously false-pass when both live compared
  lanes failed or timed out.
- `CB-039` live proof prompts could still hand Codex compact routing metadata
  instead of a concrete first-pass read list, which widened `odylith_on`
  despite better internal packet grounding.
- `CB-040` proof still shows warm/cold instability on narrow slices, so prompt
  cleanup alone does not yet make the release-safe publication view robust.
- `CB-041` public `subagent-router` and `subagent-orchestrator` wrapper
  commands previously misordered `--repo-root`, which broke honest benchmark
  validator calls against the documented public CLI contract.
- `CB-042` Atlas Mermaid preflight could falsely fail valid diagrams on the
  DOMPurify hook-drift path, which blocked strict sync and benchmark-governance
  upkeep until browser-backed scratch validation was added.
- `CB-043` stripped validator-truth files could still be restored from the
  ambient repo root instead of the scoped benchmark snapshot, which let
  unrelated dirty repo state leak back into disposable worktrees immediately
  before validation.
- `CB-044` the shared live-workspace snapshot could still omit dirty
  same-package Python siblings needed for imports, which created false proof
  failures that had nothing to do with `odylith_on` versus `odylith_off`.
- `CB-045` proof could still drop a real Codex result when `result.json` was
  missing even though the same run emitted a schema-valid final `agent_message`
  on the JSON event stream.
- `CB-046` proof support-doc ranking could still prefer generic guidance such
  as `AGENTS.md` or `agents-guidelines/*` over the slice-relevant runbook or
  contract, and strict bounded slices could inherit contradictory widen cues.
- post-run adoption-proof sampling could still hang the benchmark finalizer
  after `148/148` results completed, which blocked report persistence even
  though the full proof corpus had already finished.

## Context/Problem Statement
- [x] The current public benchmark snapshot collapses materially different
      controls into one `Odylith off` story.
- [x] The current `full_scan_baseline` name is less honest than
      `odylith_repo_scan_baseline` about what that lane is actually doing.
- [x] The benchmark report did not expose a first-class `raw_agent_baseline`
      lane for raw Codex without Odylith scaffolds.
- [x] The benchmark contract treated the repo-scan lane as the primary gate
      instead of the raw-agent lane.
- [x] The prior 24-scenario suite was too thin for a credible comprehensive
      same-task benchmark across the tracked families.
- [x] Reviewers could not inspect `odylith_on`, `odylith_on_no_fanout`,
      repo-scan control, and raw-agent control side by side from the published
      benchmark snapshot.
- [x] `B-022` surfaced inconsistently across Radar and plan truth, which made
      active benchmark work look like idea-stage backlog.
- [x] Cold `release_publication` is currently the biggest avoidable latency
      outlier in the honest `odylith_on` versus `odylith_off` comparison.
- [x] `explicit_workstream` and governance-heavy families still carry
      avoidable observed-surface drift and packet drag.
- [x] The live proof lane still narrates paired conservative task-cycle timing
      and full-session token spend with packet-era labels and guardrails, which
      makes the public benchmark story look less believable than the harness
      actually is.
- [x] The live `odylith_on` prompt can still surface internal route metadata or
      compact architecture audit JSON instead of a concrete bounded read list.

## Success Criteria
- [x] The benchmark runner supports a `raw_agent_baseline` mode.
- [x] The benchmark report still tracks four lanes internally:
      `odylith_on`, `odylith_on_no_fanout`, `odylith_repo_scan_baseline`, and
      `raw_agent_baseline`.
- [x] The primary benchmark comparison and published graph story use
      `odylith_on` versus `raw_agent_baseline`, with `odylith_off` documented
      as the same baseline.
- [x] The public README headline table centers on `odylith_on` versus
      `odylith_off`, with row-wise `Delta` and `Why It Matters` columns, while
      the no-fanout and repo-scan lanes stay available only as tracked
      internal scaffold-control context.
- [x] Benchmark docs, Registry truth, Radar truth, maintainer guidance, and
      maintainer skills explicitly describe `raw_agent_baseline` and
      `odylith_off` as the honest benchmark baseline and
      `odylith_repo_scan_baseline` as a secondary scaffold control.
- [x] The benchmark corpus grows beyond 24 total scenarios with additional
      realistic cases across the tracked families.
- [x] Focused benchmark runner, graph, corpus, and hygiene tests cover the new
      baseline contract and corpus expansion.
- [x] `B-022` surfaces as active everywhere, with only the child workstreams
      currently in delivery also marked implementation.
- [x] Hot-path selector and packet-compaction changes materially improve the
      weak families without regressing recall, precision, validation, or fit.
- [x] The benchmark report publishes selector and compaction diagnostics that
      explain the remaining hot spots honestly.
- [x] The live proof lane now distinguishes paired task-cycle time, live agent
      runtime, validator overhead, and full-session token spend from
      diagnostic prompt-bundle efficiency so the public benchmark story matches
      the real measurement basis.
- [x] Strict bounded proof slices now strip supplemental support reads and
      retrieval-plan doc spillover when the truthful required surface is the
      listed anchor set, so Odylith stops widening into validator-only or
      generated surfaces on narrow tasks.
- [x] Live proof restore paths now stay scoped to the benchmark workspace
      snapshot; stripped validator-truth files are no longer rehydrated from
      the ambient repo root.
- [x] Shared live-workspace snapshots now preserve dirty same-package Python
      dependencies needed for validator imports in both compared lanes instead
      of creating partial-package proof failures.
- [x] Live proof completion now recovers a schema-valid final benchmark result
      from the Codex JSON event stream when `result.json` is missing, instead
      of treating that transport loss as a product failure.
- [x] Live proof support-doc ranking now prefers slice-relevant contracts and
      runbooks over generic guidance spillover, while strict bounded slices no
      longer inherit broader “go widen” hints from packet uncertainty.
- [x] Benchmark guidance memory now resolves from the canonical manifest under
      `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, with
      family-aware retrieval and fail-closed preflight coverage checks.
- [x] Weak-family packet shaping now suppresses miss recovery and unrelated
      support-doc spillover on `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`,
      `daemon_security`, `cross_file_feature`, and narrow orchestration
      families when the slice is already grounded.
- [x] The benchmark runner and new guidance-focused unit suites pass with
      deterministic compact payloads and restored guidance counts.
- [ ] The corpus grows beyond the current 30-scenario suite with deeper weak
      family coverage.
- [ ] The next proof rerun must clear both cache profiles, keep
      `within_budget_rate >= 0.80`, and hold or improve the current
      `926bfeab4e887ade` wins before the public headline moves.

## Non-Goals
- [ ] Turning the benchmark into a raw-agent-only story that hides the
      repo-scan scaffold control.
- [ ] Introducing hosted benchmark orchestration.
- [ ] Hand-tuning the raw-agent control to flatter Odylith.
- [ ] Using benchmark scenario ids or labels as runtime retrieval hints.

## Impacted Areas
- [ ] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [ ] [odylith_benchmark_isolation.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_isolation.py)
- [ ] [odylith_benchmark_live_execution.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py)
- [ ] [command_surface.py](/Users/freedom/code/odylith/src/odylith/runtime/common/command_surface.py)
- [ ] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [ ] [odylith_benchmark_graphs.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_graphs.py)
- [ ] [odylith_benchmark_marketing_graphs.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_marketing_graphs.py)
- [ ] [odylith_benchmark_live_prompt.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py)
- [ ] [odylith_benchmark_prompt_payloads.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py)
- [ ] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [ ] [README.md](/Users/freedom/code/odylith/README.md)
- [ ] [docs/benchmarks/README.md](/Users/freedom/code/odylith/docs/benchmarks/README.md)
- [ ] [docs/benchmarks/REVIEWER_GUIDE.md](/Users/freedom/code/odylith/docs/benchmarks/REVIEWER_GUIDE.md)
- [ ] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [ ] [odylith/radar/source/ideas/2026-03/2026-03-29-odylith-benchmark-anti-gaming-adversarial-corpus-integrity-and-independent-proof.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-29-odylith-benchmark-anti-gaming-adversarial-corpus-integrity-and-independent-proof.md)
- [ ] [2026-03-31-odylith-benchmark-hot-path-selector-compaction-and-cold-path-improvement.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-31-odylith-benchmark-hot-path-selector-compaction-and-cold-path-improvement.md)
- [ ] [2026-03-31-odylith-benchmark-corpus-expansion-diagnostics-and-publication-refresh.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-31-odylith-benchmark-corpus-expansion-diagnostics-and-publication-refresh.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/atlas/CURRENT_SPEC.md)
- [ ] [odylith-benchmark-proof-and-publication-lane.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd)
- [ ] [RELEASE_BENCHMARKS.md](/Users/freedom/code/odylith/odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md)
- [ ] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [ ] [test_odylith_benchmark_graphs.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_graphs.py)
- [ ] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)
- [ ] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)
- [ ] [test_hygiene.py](/Users/freedom/code/odylith/tests/unit/runtime/test_hygiene.py)

## Risks & Mitigations

- [ ] Risk: the new raw-agent lane makes the harness look harsher or more
      asymmetric than the previous story.
  - [ ] Mitigation: accept the harsher comparison honestly and explain that
        repo-scan remains available as a secondary scaffold control rather than
        the benchmark gate.
- [ ] Risk: report readers confuse the repo-scan control with the raw-agent
      control.
  - [ ] Mitigation: rename the repo-scan lane honestly in public-facing table
        labels and docs.
- [ ] Risk: the corpus expansion becomes shallow box-ticking instead of real
      coverage depth.
  - [ ] Mitigation: add new scenarios only when they introduce a distinct
        grounded slice, validation posture, or governance surface combination.
- [ ] Risk: benchmark history or graphs break on older reports.
  - [ ] Mitigation: keep old report reading compatible while publishing the new
        lane and labels.
- [ ] Risk: hot-path pruning improves latency by reducing grounding quality.
  - [ ] Mitigation: add no-regression tests on recall, precision, validation,
        and observed-path grounding for the weak families before publishing.
- [ ] Risk: workstream split adds more governance drift instead of less.
  - [ ] Mitigation: update the parent, child records, Radar index, plan index,
        and refreshed benchmark/dashboard surfaces in the same change.

## Validation/Test Plan
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_hygiene.py`
- [x] `python -m pytest -q tests/unit/runtime/test_tooling_guidance_catalog.py tests/unit/runtime/test_tooling_context_retrieval_guidance.py tests/unit/runtime/test_odylith_benchmark_prompt_regressions.py tests/unit/runtime/test_odylith_benchmark_preflight.py`
- [x] `python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py -q`
- [x] `PYTHONPATH=src python3 -m odylith.cli benchmark --repo-root .`
- [x] `PYTHONPATH=src python3 -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
- [x] `./.odylith/bin/odylith sync --repo-root .`
- [x] `git diff --check`

## Rollout/Communication
- [x] README benchmark snapshot publishes the primary public comparison table
      while the full tracked report still retains the repo-scan control lane.
- [x] Benchmark docs explain why the repo-scan control and raw-agent control
      are both present and why the raw-agent lane is the honest primary
      comparison.
- [x] README and dashboard-facing benchmark surfaces refresh from the rerun
      that includes the selector, packet-compaction, and corpus changes.

## Execution Waves
- [x] Wave 1: establish the honest `odylith_on` versus `odylith_off`
      contract, anti-gaming rails, four-lane tracked report, and conservative
      publication story.
- [x] Wave 2: land deterministic fairness and boundedness recovery across
      snapshot restore, event-stream completion recovery, guidance memory, and
      support-doc relevance.
- [x] Wave 3: recover already-grounded repair families with truthful
      validator-backed no-op behavior; `daemon_security` now clears both warm
      and cold proof against `odylith_off`.
- [x] Wave 4: finish the remaining live weak-family proof reruns with real
      time budgets for `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`, and the
      remaining publication-bound governed slices so the full proof clears.
- [x] Wave 5: resume the `B-039` publication-refresh wave from the passing
      report `52aa3f76538cf12f`, regenerate the governed benchmark surfaces,
      and keep the public story tied to that exact artifact.

## Closeout / Cleanup Rules
- [ ] Keep `B-022` as the umbrella proof-governance workstream until the next
      full proof passes. Child workstreams should not stay marked active once
      their remaining scope is either finished or intentionally deferred.
- [ ] Close `B-038` when the remaining weak live families clear on targeted
      warm and cold proof without giving back the current floor.
- [ ] Keep `B-039` queued, not pseudo-active, until the runtime weak-family
      blockers are actually cleared and a real publication refresh is ready.
- [ ] Close `B-022` only after:
      1. both cache profiles clear on the next full proof,
      2. `within_budget_rate >= 0.80`,
      3. the result holds or improves the `926bfeab4e887ade` wins, and
      4. README, benchmark docs, Registry, Radar, Atlas, Compass, and related
         generated surfaces are all refreshed from that passing report.

## Current Outcome
- [x] Bound to `B-022`; the honest-baseline contract is already in flight.
- [x] `B-022` is now the umbrella for the active implementation children
      `B-038` and `B-039`.
- [x] The April 5 full proof rerun `52aa3f76538cf12f` is now the current
      green benchmark posture: `provisional_pass` across the full `37`
      scenarios and both cache profiles with `+0.227` recall,
      `+0.168` precision, `-0.141` hallucinated-surface rate,
      `+0.069` validation success, `+0.393` expectation success,
      `-52561` median live-session input tokens, `-53774` median total-model
      tokens, and `-12426.968 ms` median time to valid outcome against
      `odylith_off`.
- [x] The benchmark finalizer is now bounded: post-run adoption-proof sampling
      can no longer keep a completed `148/148` full proof from being written
      after corpus execution is already done.
- [x] The latest honest rerun (`17c5358cee7c6a36`) now clears the hard quality
      gate and secondary guardrails against `odylith_off`.
- [x] Targeted proof rerun `f082b3dc4be2002a` flipped the five-case
      narrow-slice sample from a `hold` with `-0.435` precision delta and
      `+39579.338 ms` latency delta to a `provisional_pass` with `+0.342`
      precision delta and `-8656.0 ms` latency delta against `odylith_off`.
- [x] The benchmark-component governance miss is now route-ready, which lifts
      the published validation delta to `+0.900` and expectation-success delta
      to `+0.933` without weakening the corpus.
- [x] Architecture is no longer a weak family; the hot-path selector and
      packet-compaction wave materially improved the published result.
- [x] Live proof timing and graph language now say `time to valid outcome`
      instead of generic `latency`, which makes the public measurement basis
      legible to normal readers.
- [x] The live `odylith_on` prompt now renders concrete starting files,
      supporting docs/contracts, architecture required reads, and bounded
      widening guidance instead of raw route metadata.
- [x] Public `odylith subagent-router` and
      `odylith subagent-orchestrator` wrappers now preserve the documented
      verb-first `--repo-root` contract, so benchmark validators can call the
      honest public CLI instead of failing on argument parsing.
- [x] Targeted proof rerun `827fddc9e6f30902` materially improved the warm
      precision and observed-path counts on architecture, orchestration, and
      governance-heavy slices without weakening the raw Codex lane.
- [x] The next proof-first deterministic wave is now in flight on a focused
      weak-family rerun after fixing event-stream result recovery (`CB-045`)
      and support-doc relevance plus strict-boundary no-widen behavior
      (`CB-046`).
      explicit-workstream slices, but it also exposed a still-open warm/cold
      robustness bug (`CB-040`) that keeps the conservative proof story on
      hold.
- [x] Targeted warm proof rerun `783b4a26c75941d4` converted the affected
      router or orchestrator validator cases from parse failures into real
      validator-backed outcomes; the 7-pair slice finished in
      `565038.008 ms` total pair wall clock with `80719.715 ms` average pair
      wall clock, but precision-heavy router and ledger cases still keep the
      slice on `hold`.
- [x] Atlas Mermaid preflight no longer false-fails valid diagrams on the
      DOMPurify hook-drift path; `odylith atlas auto-update --repo-root .
      --all-stale --fail-on-stale` now refreshes all `24` diagrams to fresh
      and strict `odylith sync --repo-root . --force --impact-mode selective`
      passes again (`CB-042`).
- [x] Targeted weak-family proof rerun `b77ee8df90889a2a` proved the next
      losses were still harness truth-boundary bugs, not honest product
      weakness alone: validator truth was rehydrating from ambient repo state
      (`CB-043`) and the shared snapshot could omit dirty same-package Python
      imports (`CB-044`).
- [x] The current deterministic fairness wave now captures validator truth from
      the scoped workspace snapshot and expands the shared snapshot allowlist
      to dirty same-package Python siblings for both compared lanes, so
      `odylith_off` is not weakened and `odylith_on` is not punished by a
      partial disposable package.
- [x] The current pass-recovery wave restored canonical guidance memory,
      propagated family hints into packet finalization and retrieval, and made
      benchmark warm preflight fail closed when guidance chunk, source-doc, or
      task-family coverage is empty.
- [x] Weak-family prompt shaping now keeps `required_paths` authoritative and
      removes selected-doc spillover on `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`,
      `daemon_security`, `cross_file_feature`, and narrow orchestration
      families.
- [x] The targeted unit suite now passes for guidance catalog resolution,
      family-aware guidance retrieval, prompt regressions, benchmark preflight,
      and the full benchmark runner packet contract.
- [x] Detached `source-local` shard execution is now diagnosed correctly: the
      benchmark must run from the repo `.venv` or warm proof can fail
      preflight with a false missing-memory-substrate error even when the real
      local LanceDB/Tantivy stack is healthy.
- [x] The April 5 weak-family diagnostic rerun `3365a99e8040d980` now gives a
      truthful packet-level read on the blocking families after the pass-
      recovery wave: every current weak family scores `1.0` recall, `1.0`
      precision, and `0.0` widening against `odylith_off`, so the remaining
      publication blocker is the live proof lane rather than the bounded
      packet contract.
- [x] Packet diagnostics now score the same supplemented prompt payload that
      the live lane renders, which removes a false gap where `odylith_on`
      could be handed the right guidance docs live but still be penalized in
      packet recall and selected-doc accounting.
- [x] Focused `component_governance` proof rerun `d776d9e3dc22bd09` confirms
      that the current hold is no longer a widening loss on that family:
      recall `1.0`, precision `1.0`, hallucinated surfaces `0.0`,
      unnecessary-write widening `0.0`, and `within_budget 1.0` all hold
      against `odylith_off`, while validation and expectation stay at `0.0`
      only because the local `60s` Codex timeout truncated completion before
      the validator-backed final answer landed.
- [x] Focused warm `daemon_security` proof rerun `f610654ed299d4f0` now clears
      the family cleanly against the honest raw baseline: `odylith_on`
      completes with validator-backed no-op, full recall, full precision, zero
      hallucinated surfaces, zero widening, `-228502.018 ms` latency delta,
      and `-1344532` total-token delta against `odylith_off`.
- [x] Focused cold `daemon_security` proof rerun `21d2c37e284693e4` also
      clears the family with the same no-op boundedness and even larger raw-
      baseline deltas: `-299735.027 ms` latency and `-2040183` total tokens
      while holding full recall, full precision, zero hallucinated surfaces,
      and zero widening.
- [x] The daemon-security scenario now uses the same honest allow-no-op
      contract already applied to other already-grounded repair families, and
      the live prompt explicitly treats a passing focused daemon validator as
      current workspace truth instead of pushing speculative transport or
      auth-token rewrites.
- [x] Detached daemon teardown is now resilient to client disconnect during
      focused benchmark cleanup, so shard stderr no longer fills with
      `BrokenPipeError` noise that obscures real failure diagnosis.
- [ ] Re-run the targeted weak-family proof slice and then the full proof
      corpus after `CB-043` and `CB-044` to confirm the cleaner sandbox moves
      real proof instead of just the unit suite.
- [ ] The next scope still needs to grow the corpus beyond the current
      30-scenario suite, close the remaining advisory governance-packet
      coverage debt, and clear the current warm/cold plus within-budget
      blockers without giving back the `926bfeab4e887ade` wins.
