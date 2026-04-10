status: implementation

idea_id: B-022

title: Honest Benchmark Improvement, Anti-Gaming Integrity, and Independent Proof

date: 2026-03-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: benchmark integrity, honest Odylith-on improvement, benchmark corpus realism, benchmark publication trust, README benchmark proof, and maintainer release discipline

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Odylith's benchmark proof is now important enough that both gaming pressure and real `odylith_on` underperformance must be treated as first-class product risks. The next credibility jump is making the eval hard to cheat while also making Odylith materially better against the honest `odylith_off` baseline.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-31-odylith-raw-codex-baseline-and-four-lane-benchmark-table.md

workstream_type: umbrella

workstream_parent:

workstream_children: B-038, B-039, B-041, B-042, B-043, B-044, B-046

workstream_depends_on: B-020, B-021

workstream_blocks:

related_diagram_ids: D-024

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into: B-038,B-039,B-041,B-042,B-043,B-044,B-046

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

execution_model: standard

## Problem
Odylith now has a benchmark lane that matters. That creates two failure modes:
the benchmark can drift toward flattering proof instead of hard proof, and
Odylith itself can carry avoidable latency, token, or grounding drift against
the honest `odylith_off` baseline while the product story stays ahead of the
runtime.

This can happen through scenario softening, stale runtime truth, weakened
validators, cache-profile cherry-picking, unrealistic required paths, broad
hot-path scans, over-wide governance packets, architecture packet bloat, or
README publication that outruns the real conservative report.

## Customer
- Primary: maintainers and evaluators who need Odylith benchmark claims to be
  auditable and hard to dismiss.
- Secondary: consumers deciding whether Odylith-on is actually smarter, faster,
  cheaper, more reliable, and more accurate than Codex alone in serious repo
  work.

## Opportunity
If Odylith treats anti-gaming and honest product improvement as the same
contract, the benchmark becomes more trustworthy than a typical internal eval
and more useful than a flattering one. That makes README proof defensible and
turns benchmark regressions into product-improvement signals instead of
narrative-management pressure.

## Proposed Solution
Re-scope `B-022` as the umbrella workstream for honest benchmark improvement,
then harden the runner and corpus around adversarial integrity while improving
the weak runtime families without changing the benchmark contract:
- reject stale or unsynced source-truth inputs before publication
- add harder adversarial scenarios that punish benchmark softening
- detect weakened required paths, weakened validators, and cross-profile
  cherry-picking
- make `raw_agent_baseline` the explicit primary honest baseline while keeping
  `odylith_off` as its explicit alias and the repo-scan lane as a secondary
  scaffold control
- replace broad hot-path scans with deterministic path-scoped selection and
  bounded cache reuse
- compact governance and architecture packets so Odylith carries less drag into
  the weak families
- expand the corpus beyond the current suite with additional realistic
  same-task scenarios across the tracked families
- require the published README story to stay conservative and same-scenario
  aligned with the report that actually cleared the gate

## Scope
- encode benchmark anti-gaming rules into maintainer guidance and benchmark
  subsystem source truth
- update Radar, Registry, README, benchmark docs, maintainer guidance, and
  maintainer skills so `raw_agent_baseline` and `odylith_off` are visibly the
  honest benchmark baseline
- add adversarial or integrity-focused benchmark scenarios and checks
- strengthen stale-truth detection before benchmark publication
- add regression tests that fail if maintainers soften the benchmark contract
- improve `release_publication`, `component_governance`,
  `cross_surface_governance_sync`, `docs_code_closeout`,
  `explicit_workstream`, and `architecture` honestly against `odylith_off`
- split active execution into child workstreams so only the slices currently in
  delivery are marked active
- keep README benchmark proof tied to the real conservative report only

## Non-Goals
- inventing hosted eval infrastructure
- optimizing the benchmark by hiding hard workloads
- improving the benchmark by weakening the baseline
- making the benchmark easier to keep green

## Risks
- a stricter benchmark may reduce the published headline advantage at first
- integrity checks can add local benchmark time
- runtime compaction done badly could make Odylith cheaper but less grounded
- anti-gaming rules that are too vague will not survive real release pressure

## Dependencies
- `B-020` made benchmark publication conservative
- `B-021` expands the corpus toward harder complex-repo work

## Success Metrics
- Odylith can no longer improve its published benchmark story by narrowing the
  workload, weakening validators, or hand-picking easier report views
- `raw_agent_baseline` is the primary same-task benchmark baseline in the
  runner, graphs, README, Registry truth, Radar truth, and maintainer
  guidance, with `odylith_off` as the explicit alias
- `odylith_on` improves honestly against `odylith_off` in the higher-tier
  metrics while reducing avoidable latency and token drag in the weak families
- the benchmark corpus grows beyond the current suite with additional realistic
  cases across the tracked families
- benchmark publication fails closed when source truth or runtime truth is
  stale
- the benchmark corpus includes adversarial scenarios specifically designed to
  catch eval gaming or proof inflation
- B-022 and the child workstreams currently in delivery surface as active
  everywhere instead of drifting back to queued
- README benchmark claims remain mechanically traceable to the conservative
  published report

## Validation
- `odylith benchmark --repo-root .`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_hygiene.py`
- `git diff --check`

## Rollout
Lock the anti-gaming rules into source truth first, activate the real delivery
workstreams, improve the weak runtime families, then expand and rerun the
corpus, and finally refresh README proof only from the hardened rerun.

## Why Now
Once the benchmark starts shaping product claims, it must also resist the
temptation to shape itself around those claims.

## Product View
If Odylith ever wins by gaming the eval, the proof becomes worse than useless.
If Odylith loses honestly because the runtime is still dragging, that is still
better than teaching the product to optimize the story instead of the outcome.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `subagent-orchestrator`
- `tribunal`
- `dashboard`

## Interface Changes
- benchmark publication becomes stricter about stale truth and conservative
  reporting
- benchmark runtime selection and packet shaping become more bounded in the
  weak families
- maintainers get explicit anti-gaming rules in the benchmark release lane

## Migration/Compatibility
- no consumer migration required
- benchmark history remains readable
- stricter integrity checks may invalidate formerly publishable weak reports

## Test Strategy
- add hygiene tests for benchmark anti-gaming contract text
- add unit tests for selector cacheing, weak-family packet compaction, and
  honest no-regression benchmark deltas
- add runner or corpus checks that fail when benchmark truth is softened
- validate the conservative benchmark lane end to end before README refresh

## Open Questions
- whether a bounded embedded reranker earns its keep after the deterministic
  selector and packet-compaction wave lands

## Current Status
- the latest full honest rerun (`52aa3f76538cf12f`, `2026-04-05T22:51:40Z`)
  is `provisional_pass` on `odylith_on` versus `odylith_off` across the full
  `37`-scenario warm-plus-cold proof corpus
- the hard quality gate and secondary guardrails both clear on the current
  conservative published view, and the published result is no longer relying
  on a single flattering cache posture
- the benchmark runner now fails closed in finalization: bounded adoption-proof
  sampling can no longer hold a completed `148/148` proof report hostage
- the benchmark proof lane also exposed a real public-CLI validator drift:
  `odylith subagent-router --repo-root . --help` and
  `odylith subagent-orchestrator --repo-root . --help` were honest validator
  commands, but the wrapper misordered `--repo-root` and undercounted
  validator-backed proof until `CB-041` was fixed
- benchmark-governance upkeep also exposed an Atlas preflight false-failure:
  valid Mermaid diagrams could fail strict sync on the DOMPurify hook-drift
  path until `CB-042` added browser-backed scratch validation for that known
  runtime mismatch
- the deterministic fairness and boundary wave fixed the real suppressors that
  were keeping proof artificially yellow: scoped validator-truth restore
  (`CB-043`), same-package dirty-sibling snapshotting (`CB-044`), event-stream
  result recovery when `result.json` is missing (`CB-045`), and slice-relevant
  support-doc ranking with strict bounded no-widen behavior (`CB-046`)
- ML and heavier math stay intentionally deferred until the clean-room,
  completion-contract, and selector waves stop moving proof materially; the
  current evidence still says deterministic fixes are returning meaningful
  benchmark gains
- `B-038` recovered the previous proof blockers enough for the full proof to
  pass; the remaining family list is now advisory benchmark steering rather
  than release-blocking proof debt
- product-repo `benchmark_compare` still reports `warn`, but now only because
  there is no first shipped release baseline yet; that is a release-history
  gap, not a benchmark-quality failure
- `B-039` can now resume broader corpus and publication follow-on work from a
  green proof floor instead of a blocked pass-recovery posture
