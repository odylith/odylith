# Benchmark
Last updated: 2026-04-08


Last updated (UTC): 2026-04-08

## Purpose
Benchmark is Odylith's local proof subsystem for measuring whether Odylith-on
actually makes agentic coding better than the true `odylith_off` /
`raw_agent_baseline` lane, while still measuring the secondary repo-scan
scaffold control lane. It owns the benchmark corpus, the
runner and publication contract, the generated benchmark report ledger, the
maintained graph pipeline used in README and release proof, and the public
reviewer framing that explains how Odylith should be compared.

## Scope And Non-Goals
### Benchmark owns
- The tracked benchmark corpus in
  `odylith/runtime/source/optimization-evaluation-corpus.v1.json`.
- Local benchmark execution and conservative publication logic in
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`.
- Maintained benchmark graph generation in
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`.
- Public benchmark framing and reviewer guidance under `docs/benchmarks/`.
- Local benchmark history under `.odylith/runtime/odylith-benchmarks/`.
- The release-safe benchmark publication contract used by README and maintainer
  release proof.

### Benchmark does not own
- The grounding, routing, or orchestration runtime it measures.
- Hosted evaluation infrastructure.
- Consumer-repo source truth outside the local Odylith tree.
- Claude-native benchmark claims that do not share the current Codex harness.

## Developer Mental Model
- The corpus defines the scenarios, expectations, and validation hooks that
  Odylith must beat honestly.
- The runner executes those scenarios across multiple cache profiles and modes,
  then publishes a conservative same-scenario comparison instead of the easiest
  green snapshot.
- `odylith_on` measures the real grounded Odylith stack.
- `odylith_on_no_fanout` isolates how much bounded multi-leaf orchestration is
  contributing on top of the same Odylith grounding packet.
- `raw_agent_baseline` is `odylith_off`, or plain-English `Odylith off`: the
  raw Codex CLI control with Odylith grounding disabled.
- `odylith_repo_scan_baseline` is the current repo-scan scaffold control lane.
- The honest primary benchmark comparison is `odylith_on` versus
  `raw_agent_baseline`; the repo-scan lane is secondary context that shows how
  much scaffolding helps.
- The benchmark now also owns a developer-first family taxonomy in
  `src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py`. That
  taxonomy orders the public README table and both proof and diagnostic family
  heatmaps by developer legibility rather than by prompt-cost ranking.
- A live `odylith_on` versus `odylith_off` comparison only counts as benchmark
  proof when both lanes run the same Codex CLI model, reasoning effort,
  sandbox policy, approval posture, validator contract, and stripped workspace
  shape. The only intended lane difference is whether Odylith contributes the
  grounding scaffold.
- The report under `.odylith/runtime/odylith-benchmarks/latest.v1.json` is the
  machine-readable source of truth for publication.
- The README numbers, benchmark explainer, reviewer guide, and canonical SVG
  graphs are derived outputs. They must never outrun the latest validated
  published report or drift away from the benchmark priority order.
- If maintainers explicitly waive proof for one release, that exception must
  be tracked in `odylith/runtime/source/release-maintainer-overrides.v1.json`
  and treated as an advisory downgrade, not as hidden benchmark success.
- Odylith's public benchmark story is benchmark-first: memory, topology,
  governance surfaces, and orchestration are mechanisms that explain the
  execution delta, not the primary scorecard.
- Simulation, reviewer, and closeout artifacts should suppress mid-analysis
  Odylith brand narration. If a writeup or agent handoff names Odylith
  directly beyond lane labels, reserve that for one short end-of-work
  `Odylith Assist:` line, and prefer `**Odylith Assist:**` when Markdown
  formatting is available. Follow the detailed closeout contract in
  [Odylith Chatter](../odylith-chatter/CURRENT_SPEC.md) and keep benchmark
  storytelling anchored in measured proof rather than duplicated branding
  rubric.
- That closeout rule is metadata-only for benchmark families: do not add
  benchmark required paths, hot-path docs, or validation commands just to
  repeat the chatter contract.

## Current Published Posture

- Latest published proof report:
  `.odylith/runtime/odylith-benchmarks/latest.v1.json`
  report `52aa3f76538cf12f`, status `provisional_pass`
- Latest published diagnostic report:
  `.odylith/runtime/odylith-benchmarks/latest-diagnostic.v1.json`
  report `74cbe36427f2c375`, status `hold`
- Current published proof deltas versus `odylith_off`:
  `+0.227` recall, `+0.168` precision, `-0.141` hallucinated-surface rate,
  `+0.069` validation success, `+0.330` critical recall,
  `+0.167` critical validation success, `+0.393` expectation success,
  `+0.124` write-surface precision, `-0.170` unnecessary widening,
  `-52,561` median live-session input tokens, `-53,774` median total model
  tokens, and `-12.427s` median time to valid outcome
- Current proof hard-gate blockers:
  none on the current full warm-plus-cold proof
- Current proof secondary guardrails:
  both cache profiles clear the hard gate and `within_budget_rate` is back
  above the `0.80` floor
- Current proof attention families:
  `architecture`, `browser_surface_reliability`, `component_governance`,
  `cross_surface_governance_sync`, `governed_surface_sync`, and
  `orchestration_feedback`
- Current proof memory posture:
  local-memory-first on LanceDB plus Tantivy, with Vespa intentionally
  disabled unless a run explicitly reports otherwise
- Product-repo release-baseline posture:
  the current passing proof is detached `source-local` posture, and
  `benchmark_compare` still reports `warn` until there is a last-shipped
  published release baseline in `docs/benchmarks/release-baselines.v1.json`
- Active release exception:
  `v0.1.10` currently carries a tracked `skip_proof_and_compare` override
  because pinned-dogfood proof run `0047192366d8bf1c` wedged mid-corpus and
  did not persist a fresh release-safe report. That exception is exact-version
  only and moves benchmark runner tuning plus proof restoration to the next
  release.

## Current Benchmark Priorities

- Keep the current `52aa3f76538cf12f` full proof as the new source-local
  floor and reject regressions against its quality, validation, and budget
  wins.
- Preserve bounded benchmark finalization: adoption-proof sampling is
  supplementary and must degrade cleanly on timeout or transport loss instead
  of blocking report persistence after the full corpus finishes.
- Keep the first shipped release proof local-memory-first; hybrid rerank and
  remote retrieval remain experiment lanes until they improve proof without
  harming the current pass.
- Convert the current source-local pass into a pinned-dogfood release proof and
  then record the first shipped release baseline in
  `docs/benchmarks/release-baselines.v1.json`.
- Continue driving the advisory families down without giving back the current
  proof or the `74cbe36427f2c375` diagnostic grounding wins.

## Developer-First Taxonomy

Benchmark publication now leads with the developer-facing core:

- Bug Fixes
- Multi-File Features
- Runtime / Install / Security
- Surface / UI Reliability
- Docs + Code Closeout
- Governance / Release Integrity
- Architecture Review
- Grounding / Orchestration Control

That ordering is non-cosmetic. The benchmark keeps Odylith's governance and
architecture truth, but the public heatmaps and family tables should now start
with the families that look and feel most like normal coding-agent work.

## Public And Maintainer Command Surface
### Public operator entrypoint
- `odylith benchmark --repo-root .`
  Run the fast local developer lane: the honest `odylith_on` versus
  `odylith_off` matched pair on the warm cache profile plus a representative
  family-smoke subset unless the operator narrows it explicitly.
- `odylith benchmark --repo-root . --profile proof`
  Run the full strict publication lane and update `latest.v1.json` only when
  the run covers the full tracked corpus and release-safe mode or cache-profile
  matrix.
- `odylith benchmark --repo-root . --profile proof --family <family> --shard-count N --shard-index K`
  Run a deterministic strict-proof shard without changing scoring, sandbox
  isolation, or matched-pair fairness.

### Maintainer publication helpers
- `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
  Regenerate the canonical README SVG graph set from the current report.
- [Maintainer benchmark release guidance](../../../../maintainer/agents-guidelines/RELEASE_BENCHMARKS.md)
  defines the release-safe publication contract and graph order.

## Repository And Runtime Layout
### Tracked product truth
- `odylith/runtime/source/optimization-evaluation-corpus.v1.json`
  Canonical benchmark corpus and scenario inventory.
- `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`
  Benchmark runner, aggregation, and publication logic.
- `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`
  Canonical graph renderer for the maintained README SVG set.
- `src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py`
  Canonical developer-first family ordering for README and graph publication.
- `README.md`
  Top-level public benchmark framing and current benchmark snapshot.
- `docs/benchmarks/`
  Benchmark explainer, reviewer guidance, and generated graph assets published
  in README.
- `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`
  Maintainer release-proof contract for benchmark publication.
- `odylith/maintainer/skills/release-benchmark-publishing/SKILL.md`
  Maintainer execution guidance for benchmark regeneration and release proof.

### Mutable runtime state
- `.odylith/runtime/odylith-benchmarks/latest.v1.json`
  Current benchmark report used for local inspection and publication.
- `.odylith/runtime/odylith-benchmarks/<report_id>.json`
  Historical benchmark reports retained for comparison and audit.

## Core Benchmark Contract
### Corpus truth
- Each scenario must stay tied to real repo truth, real validation hooks, and
  real expectations. The benchmark is not allowed to soften the workload just
  to improve the score.
- Workstream anchors, owned paths, and expectation surfaces must stay current
  with Radar, Registry, Atlas, and the runtime contracts they exercise.

### Integrity non-negotiable
- Never game the eval.
- Never trade recall, accuracy, or precision away just to make latency or token
  budgets look better.
- Benchmark authors must not improve Odylith's score by removing hard cases,
  loosening required paths, weakening validators, trimming cache profiles, or
  publishing hand-picked report slices.
- Benchmark publication must fail closed on stale source truth, stale runtime
  truth, or README or graph claims that outrun the conservative published
  report.
- If Odylith regresses on a more realistic or more adversarial corpus, the
  product should absorb that signal and improve; the corpus should not be
  softened to preserve flattering numbers.
- Benchmark evolution is allowed only when it makes the eval harder, more
  representative, more reproducible, or more conservative.
- A live raw-Codex baseline is invalid for publication if the disposable
  workspace inherits ambient workstation or repo state beyond the explicit
  shared task contract. Shared `.odylith` runtime state, global Git config,
  host Python or package-manager state, desktop Codex environment variables,
  shared caches, or shell startup drift all count as contamination.
- Benchmark status must fail closed when both compared lanes fail, time out, or
  miss the validator contract. Equal failure is never a pass.
- Validator-backed task success and proxy expectation success must remain
  separately labeled in reports and docs. Packet or expectation proxies are
  diagnostic signals only; they are not the same thing as confirmed validator
  completion.
- Blanket wall-clock overrides that materially distort live matched-pair runs
  are debug tools, not release-safe proof. Published reports must record the
  timeout policy that governed each live run.

### Modes and cache profiles
- The benchmark profiles are `quick`, `proof`, and `diagnostic`.
- `quick` is the default local developer lane: the public matched pair only,
  warm cache only, and representative family-smoke selection unless the
  operator passes explicit filters.
- `proof` is the release-safe publication lane: the full corpus for the live
  `odylith_on` versus `odylith_off` pair plus both `warm` and `cold` cache
  profiles unless the operator passes explicit filters.
- `diagnostic` is the internal tuning lane: it isolates packet and prompt
  creation for `odylith_on` versus `odylith_off` without running the live
  end-to-end Codex pair.
- The proof lane answers:
  - "Does Odylith beat raw Codex CLI on the same live end-to-end task contract?"
  - "What is the full matched-pair time to valid outcome?"
  - "Does Odylith improve required-path coverage, validation, and expectation success on the live run?"
- The diagnostic lane answers:
  - "Does Odylith build a better grounded packet/prompt than `odylith_off`?"
  - "What is the prep-time and prompt-size cost of Odylith’s retrieval/memory layer?"
  - "Does Odylith improve required-path coverage before the model starts working?"
- Those lanes do not carry equal product weight:
  - `proof` is the governing product benchmark and the primary optimization target
  - `diagnostic` is an internal tuning surface and only counts when it preserves or improves `proof`
  - a diagnostic-only win that harms proof is a benchmark regression
- The supported report modes are `odylith_on`, `odylith_on_no_fanout`,
  `odylith_repo_scan_baseline`, and `raw_agent_baseline`.
- `odylith_off` means `raw_agent_baseline`, and plain-English `Odylith off`
  means the same lane.
- The release-safe primary comparison is `odylith_on` versus
  `raw_agent_baseline`.
- Older history artifacts may still carry the legacy repo-scan key
  `full_scan_baseline`; report readers must continue to accept it.
- The release-safe default cache profiles are `warm` and `cold`.
- Warm and cold are both part of the published proof because Odylith should be
  fast and robust across first-read and repeated-read posture, not only in the
  easiest cache state.
- `latest.v1.json` is release-safe only when it comes from a full `proof`
  profile run that covers the full corpus, the default live matched pair, and
  both release-safe cache profiles.
- `latest-proof.v1.json` is the profile-specific proof snapshot.
- `latest-diagnostic.v1.json` is the profile-specific diagnostic snapshot.
- `docs/benchmarks/proof/` and `docs/benchmarks/diagnostic/` carry the
  profile-specific SVG graph sets.
- For live Codex CLI proof, `odylith_on` and `odylith_off` must also share the
  same execution contract fields for resolved CLI binary, model, and reasoning
  effort. A report that mixes those contracts is not a valid same-agent
  comparison.
- Scenario validators are part of that same-task fairness contract. Public
  validator commands must target supported `odylith ...` entrypoints, and
  wrapper surfaces such as `odylith subagent-router` and
  `odylith subagent-orchestrator` must preserve their documented
  `--repo-root` and `--help` behavior. A proof result produced while those
  public validator entrypoints are broken is benchmark-debug evidence, not
  trustworthy publication proof.
- The runner may batch the public live pair only after each lane's request has
  already been prepared. Odylith packet-building, cache-profile preparation,
  and other global-state-sensitive phases stay serial. Only the isolated live
  Codex subprocess phase is allowed to run concurrently, and only for the same
  scenario's `odylith_on` versus `odylith_off` pair.
- Because of that matched-pair batching, published live-proof timing is a
  contention-shared benchmark time-to-valid-outcome measurement, not a
  solo-user latency claim.
- Published live-proof runtime must not collapse to one median-only headline.
  The benchmark contract should publish median plus tail-aware distribution
  context such as mean, `p95`, and full proof pair-wall total across the
  selected cache profiles.
- If Odylith selects docs or contracts for the live evidence cone, those
  surfaces must survive the packet-to-prompt handoff into the live Codex lane.
  Stripping selected docs from the prompt payload invalidates both required-path
  accuracy claims and prompt-token accounting.
- The inverse also matters on strict bounded proof slices. When the scenario's
  truthful required surface is exactly the listed starting anchors, or the
  family is an exact-path ambiguity probe, the live prompt handoff must strip
  supplemental docs, implementation anchors, and retrieval-plan doc lists
  rather than quietly widening `odylith_on`.
- On those strict bounded proof slices, validator command mentions and
  generated or rendered artifacts are coverage evidence, not approved
  first-pass reads. They only become valid read targets when the listed
  anchors or a focused contradiction point directly at them.
- Strict bounded proof slices must not inherit contradictory widen language
  from broader packet uncertainty. If the slice is marked bounded, the live
  prompt stays local even when the parent packet elsewhere recommended a fuller
  scan.
- Sandbox stripping for `odylith_off` and `odylith_on` may remove only
  auto-consumed instruction entrypoints and tool config surfaces. It must not
  delete truth-bearing repo docs, maintainer markdown, or product skill files
  that remain valid explicit read targets during the task.
- If stripped guidance or validator-truth files must reappear before
  validation, they must be restored from a stash captured inside the scoped
  benchmark workspace snapshot, never from the ambient repo root. Restoring
  from repo root reintroduces unrelated dirty state and invalidates proof.
- The shared live-workspace snapshot may not materialize a partial dirty Python
  package. If a dirty selected Python file depends on dirty sibling modules in
  the same package, the snapshot must carry those same-package dirty siblings
  for both compared lanes or fail closed before publication.
- Diagnostic runs must fail closed if any benchmark-owned live Codex
  subprocess or benchmark temp worktree appears during or after the run.
- Live observed-path attribution must count direct listing, search, and file
  inspection behavior, not transitive file-path mentions embedded inside the
  contents of a different file. Otherwise precision and hallucination metrics
  punish link-dense governance docs instead of actual widening.
- Live proof support-doc selection must prefer the most slice-relevant
  contracts or runbooks before generic guidance surfaces. Generic files such
  as `AGENTS.md`, `agents-guidelines/*`, or skills are valid support docs only
  when they are also the most relevant truthful read for the slice.
- Live proof completion recovery must prefer `result.json` but fall back to a
  schema-valid final `agent_message` from the Codex JSON event stream before
  declaring `missing_schema_output`.

### Published proof posture
- The published view strategy is conservative across the selected cache
  profiles.
- README and the canonical SVG graphs must render from the published summary,
  not from `primary_comparison` or a warm-only slice.
- The public README headline table should center on `odylith_on`,
  and `odylith_off`, while the full tracked report still carries
  `odylith_on_no_fanout` and `odylith_repo_scan_baseline` for internal
  attribution and anti-gaming review.
- Packet and prompt creation diagnostics are useful internal tuning signals,
  but they are not the same thing as the live end-to-end product comparison.
- By default, Odylith applies a conservative `20m` timeout to each live Codex
  turn so one stalled scenario cannot hang the benchmark indefinitely.
  Validator timeouts remain operator-controlled. Any operator-supplied timeout
  override or explicit disable must be recorded in the report contract.
- The published table must label live-proof timing and token rows honestly:
  time to valid outcome, live agent runtime, validator overhead,
  full-session input, and total model tokens are all distinct measurements.
- Scenario publication must stay same-scenario conservative; it must not mix
  the best baseline case with the worst Odylith case from different cache
  profiles.

### Public evaluation framing
- Odylith should be evaluated first on whether `odylith_on` improves the
  coding outcome versus `raw_agent_baseline` on the same tasks.
- The benchmark is not trying to prove that Odylith beats the base model's
  weights. It is trying to prove that Odylith supplies a better operating
  policy around the same model.
- In benchmark terms, the relevant multipliers are:
  - model capability
  - context quality
  - search policy
  - validation policy
  - recovery policy
- A benchmark win is meaningful only when Odylith improves those control-plane
  terms without changing the underlying same-task model contract.
- The strongest public proof posture is therefore:
  - same repo
  - same truth-bearing surfaces
  - same model and reasoning contract
  - same sandbox and validator contract
  - different result only because `odylith_on` operationalizes the work better
- `odylith_repo_scan_baseline` is still useful because it shows how much the
  repo-scan scaffold itself is helping, but it is not `Odylith off`.
- Structural feature comparisons are secondary context and only meaningful when
  they are tied back to execution consequences.
- Public measured proof is Codex-first today. Public docs may describe
  Claude-facing benefits from the same grounding and governance layer, but they
  must not overstate those benefits as Claude-native benchmark proof.
- If Odylith only wins when it gets extra hidden truth, that is a weaker story
  than the true benchmark claim and must not be presented as the primary
  proof.
- If `odylith_on` beats `odylith_off` when both lanes can explicitly read the
  same truthful repo surfaces, then Odylith has demonstrated real systems
  value rather than a hidden-information advantage.

### Metrics that matter
Odylith treats benchmark outcome priorities in this order:
1. correctness and non-regression
2. grounding recall and precision
3. validation success and execution fit
4. robustness and consistency across cache states, retries, and recoveries
5. time to a valid outcome
6. prompt-token and total payload efficiency
7. bounded performance under tighter token budgets

In practice that means:
- correctness and non-regression:
  task acceptance, critical validation success, no collateral breakage, and no
  hidden damage to the repo or runtime contract
- grounding recall and precision:
  required-path recall, required-path precision, evidence sufficiency, and low
  hallucinated-surface drift
- validation success and execution fit:
  valid-answer rate, expectation success, write-surface precision, and
  adherence to the intended execution posture
- robustness and consistency:
  warm-plus-cold consistency, rerun stability, bounded recovery after stale or
  ambiguous state, and fail-closed behavior when Odylith cannot ground safely
- time to a valid outcome:
  speed only matters after Odylith is still right, grounded, and safe; on the
  live proof lane this is benchmark time to valid outcome, not solo-user
  latency
- prompt-token and total payload efficiency:
  on the live proof lane these are full-session Codex costs; initial
  prompt-bundle efficiency belongs to the diagnostic lane
- bounded token-budget behavior:
  Odylith should degrade gracefully under tighter budgets rather than winning
  only in generous-token conditions

Benchmark improvement only counts as a real product win when Odylith preserves
or improves the higher-tier quality metrics while keeping the lower-tier speed
and efficiency metrics inside explicit guardrails. Faster or cheaper but less
correct, less grounded, or less reliable is not accepted as product progress.

Publication and release status use these layers:
- `hard quality gate`:
  correctness/non-regression, grounding recall/precision, validation/fit, and
  robustness/consistency all hold the status immediately if they regress
- `secondary guardrails`:
  packet-backed live-proof tighter-budget behavior remains status-blocking;
  architecture-only or other non-packet sampled slices do not fail this
  guardrail just because no packet rows are present; time to valid outcome and
  full-session token cost stay published as diagnostics because they do not
  share the measurement basis of solo-user latency or initial prompt size
- comparative latency and prompt or payload guardrails are only status
  blockers when the compared lanes share the same measurement basis; a failed
  baseline that exits faster or cheaper stays published as a diagnostic, not
  as a blocker
- the candidate-side `within_budget_rate` floor still applies on packet-backed
  sampled slices even when the relative efficiency guardrails are not active
- `advisory mechanism checks`:
  packet coverage, widening frequency, route posture, and related mechanism
  metrics stay published for diagnosis, but they are not the same thing as the
  primary outcome gate by themselves

Current live-proof secondary guardrail:
- `within_budget_rate` must stay at or above `0.80` on packet-backed sampled slices

Current diagnostic-lane efficiency guardrails:
- median prompt-bundle delta must stay at or below `+64 tokens`
- median total-payload delta must stay at or below `+96 tokens`

Supporting measures such as grounded delegation rate, route-ready rate,
expectation success, and operating-posture metrics matter because they explain
how Odylith achieved the result, not just what the scoreboard says.

### Eval quality gates
The benchmark itself is only trustworthy when it also measures the right shape
of work:
- scenario coverage must span small, medium, and large or complex repo work
- coverage must include single-file, cross-file, and cross-surface tasks
- coverage must include correctness-sensitive and recovery-sensitive cases
- the published proof must remain conservative across warm and cold profiles
- singleton sensitive-family latency must not be published from a single noisy
  wall-clock sample when rerun-stability probes disagree
- faster failure must never be treated as a lower-tier benchmark win over a
  slower correct outcome
- benchmark evolution must make the corpus harder, more realistic, or more
  reproducible, never easier

Release-safe benchmark status is distinct from these eval-integrity gates:
- warm and cold cache profiles must both clear the hard quality gate
- when both compared lanes produce successful outcomes, the published
  comparison must also stay inside the explicit lower-tier guardrails above
- advisory mechanism debt must still be published honestly even when it is not
  the direct status blocker

## Cross-Component Control Flow
### 1. Define the benchmark workload
1. The benchmark corpus specifies canonical `scenarios` and
   `architecture_scenarios`, plus workstream anchors, expectations, and
   validation hooks.
2. Registry, Radar, Atlas, and spec truth keep those scenarios grounded in the
   live product.

### 2. Run the benchmark
1. The benchmark runner executes the selected cache profiles for
   `odylith_on`, `odylith_on_no_fanout`, `odylith_repo_scan_baseline`, and
   `raw_agent_baseline`.
2. `odylith_on` measures the real [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
   and [Subagent Orchestrator](../subagent-orchestrator/CURRENT_SPEC.md)
   posture used by the product.
3. The runner writes the latest report and an immutable history artifact under
   `.odylith/runtime/odylith-benchmarks/`, including first-class
   `published_summary`, `published_family_deltas`, `published_mode_table`,
   `tracked_mode_table`, and `robustness_summary` fields for publication and
   internal review consumers.
4. Sensitive singleton families must also record rerun-stability probes with
   fresh same-profile cache preparation and publish family latency from the
   median-of-N probe samples instead of one potentially noisy wall-clock hit.
5. Packet results must publish traced reasoning time plus explicit
   uninstrumented overhead so latency spikes can be diagnosed instead of being
   mistaken for grounding-quality regressions.
6. Live Codex CLI results must also publish the isolation contract that made
   the comparison fair, including whether the run used a temporary Codex home,
   stripped repo guidance, localized validator cache or temp roots, the
   resolved timeout policy, and any remaining contamination risks that still
   invalidate publication.
7. Lane-emitted workspace paths are untrusted input. Invalid or impossible
   path tokens must fail closed into missing attribution rather than crashing
   the benchmark harness.
8. Targeted `proof` reruns such as `--profile proof --case-id ...` remain
   honest tuning slices for the live contract, but they are not release-safe
   publication replacements for the full warm-plus-cold proof lane.

### 3. Publish the proof
1. The graph renderer consumes the latest published report.
2. Maintainer release proof regenerates the README SVG assets and benchmark
   snapshot from that same report.
3. Public benchmark docs and reviewer guidance must stay aligned with that same
   report and the benchmark priority order.
4. The release lane should treat stale graphs, stale README numbers, or stale
   benchmark-framing docs as a publication failure, not as optional polish.

## What Developers Need To Change Together
- Corpus changes:
  update the canonical `scenarios` / `architecture_scenarios` corpus, related
  workstreams, validation hooks, and any benchmark docs or publication
  snapshots that derive from the changed scenarios.
- New benchmark metric:
  update the runner, report summary, graph renderer, and README publication
  wording together so the public proof does not drift from the machine-readable
  report.
- Publication-contract change:
  update the runner, graph renderer, README benchmark section, benchmark docs,
  reviewer guide, and maintainer release guidance in the same slice.
- Public evaluation-frame change:
  update README framing, benchmark explainer, reviewer guidance, and component
  truth together so the benchmark-first comparison contract does not drift back
  toward surface-inventory storytelling.

## Failure And Integrity Posture
- The benchmark must fail closed on broken corpus truth, broken validator
  contracts, or unreadable report inputs.
- Broken public validator wrappers are product failures, not benchmark noise.
  If a documented `odylith ...` validator command misparses, the fix belongs in
  the product command surface before the benchmark story moves forward.
- The benchmark must also fail closed on contaminated live-run isolation. If
  the raw-Codex lane still sees shared workstation or repo state, the result is
  debug-only and must not be narrated as benchmark proof.
- The tracked corpus stays canonical on `scenarios` and
  `architecture_scenarios`; reader support for legacy `cases` keys is only a
  backward-compatibility bridge, not the maintained source-truth shape.
- Odylith must not cherry-pick only the easiest cache profile for publication.
- README and graph publication must not claim a result stronger than the latest
  conservative published report.
- Public docs and reviewer guidance must not drift into treating structural
  overlap or feature-parity tables as the primary proof of product value.
- Odylith must not gain benchmark wins from weakened workload shape, stale
  projection truth, or cross-scenario comparison tricks.
- Historical integrity failures now tracked in Casebook are part of the
  benchmark safety model:
  - `CB-027` records the open live-run contamination and raw-baseline isolation
    gap.
  - `CB-028` records the fixed false-pass gate that previously allowed both
    failed lanes to look provisionally green.
- A slower but more honest benchmark lane is preferable to a flattering but
  weakly grounded benchmark story.
- A faster or cheaper benchmark result that regresses recall, accuracy, or
  precision is also a failure, even if the speed or token headline improves.
- Warm-only or profile-scoped local runs remain useful for debugging, but they
  are not release-safe publication proof unless the report says otherwise.

## Validation Playbook
### Runtime proof
- `odylith benchmark --repo-root .`
- `odylith benchmark --repo-root . --profile proof`
- `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`

### Focused tests
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/test_cli.py`
- `python -m pytest -q tests/unit/runtime/test_tooling_guidance_catalog.py tests/unit/runtime/test_tooling_context_retrieval_guidance.py tests/unit/runtime/test_odylith_benchmark_prompt_regressions.py tests/unit/runtime/test_odylith_benchmark_preflight.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-05 · Implementation:** Refreshed the benchmark publication story to the April 5 source-local full proof pass 52aa3f76538cf12f: README, benchmark docs, registry spec, plans, and radar now reflect that odylith_on clears the hard gate and secondary guardrails against odylith_off while benchmark_compare still warns until the first shipped release baseline exists.
  - Scope: B-021, B-022
  - Evidence: README.md, docs/benchmarks/README.md +3 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-28: Added a first-class local benchmark corpus and proof lane that cleared the initial provisional benchmark gate to `provisional_pass` and refreshed the public README snapshot from real measured behavior. (Plan: [B-009](odylith/radar/radar.html?view=plan&workstream=B-009))
- 2026-03-29: Tightened the benchmark frontier by compacting hot-path overhead, reran the Codex corpus, and regenerated the canonical README graph set from the stronger report. (Plan: [B-019](odylith/radar/radar.html?view=plan&workstream=B-019))
- 2026-03-29: Hardened benchmark integrity with warm-plus-cold conservative publication, explicit published-summary fields, and release-safe README or graph proof driven from the harder benchmark view. (Plan: [B-020](odylith/radar/radar.html?view=plan&workstream=B-020))
- 2026-04-01: Reframed the benchmark component around a real same-model live Codex CLI comparison, documented the strict isolation contract for `odylith_off`, and recorded the false-pass, contamination, prompt-boundary selected-doc loss, over-stripped worktree truth-loss, and transitive-link attribution failure modes discovered during the honest raw-baseline redesign. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022))
- 2026-04-02: Fixed the public subagent validator wrapper contract so proof can call documented `odylith subagent-router` and `odylith subagent-orchestrator` commands without repo-root parse failures, and recorded the resulting validator-backed targeted proof rerun against the honest warm slice. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022))
- 2026-04-02: Tightened the clean-room proof boundary again by restoring validator truth only from the scoped workspace snapshot and by expanding the shared snapshot allowlist to dirty same-package Python siblings needed for imports, so disposable worktrees stop rehydrating unrelated repo state or failing on partial local packages. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022))
- 2026-04-02: Clarified that benchmark wins are meaningful only when Odylith improves the operating policy around the same model under the same repo and same truth contract, and explicitly documented the weaker status of wins that depend on extra hidden information. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022))
- 2026-04-05: Restored canonical benchmark guidance memory, made weak-family packet shaping fail closed before prompt rendering, bounded the post-run adoption-proof finalizer so it cannot hold a completed report hostage, and refreshed the current local-memory-first source-local proof to `52aa3f76538cf12f` `provisional_pass` while the diagnostic grounding floor remains `74cbe36427f2c375` on `hold`. (Plan: [B-021](odylith/radar/radar.html?view=plan&workstream=B-021))
- 2026-04-08: Completed the reasoning-package boundary split with no compatibility shims, refreshed Atlas and delivery-intelligence sync truth to the new reasoning paths, and re-proved the quick source-local architecture shard to `provisional_pass` after the package-separation hardening. (Plan: [B-061](odylith/radar/radar.html?view=plan&workstream=B-061))
