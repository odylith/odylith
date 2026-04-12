- Bug ID: CB-105

- Status: Resolved

- Created: 2026-04-12

- Severity: P1

- Reproducibility: Always

- Type: Performance-Engineering-Learning

- Description: Full governed sync (`odylith sync --force --impact-mode full`)
  took 30.47 seconds on the 91-workstream, 25-component, 36-diagram product
  repo as of 2026-04-12 baseline. The 22-step pipeline executed in a
  shared-nothing posture where every step independently re-derived the repo
  root, consumer profile, registry report, path normalization tokens, backlog
  rows, and projection fingerprints. Nine rounds of profiling — the last two
  using proper statistical methodology (1 warmup + 5 measured iterations with
  median, stdev, and CV% reporting) — drove the total from 30.47s to a
  statistically validated 5.78s median (CV 3.1%), an 81% wall-clock reduction
  with zero governance outcome changes.

- Impact: Every `odylith sync`, every post-edit governance hook, every
  `odylith dashboard refresh`, and every Compass-backed agent startup paid
  the full 30-second tax. At agent interaction cadence this meant governance
  refresh was slower than the edit it was validating, creating pressure to
  skip sync or run it less frequently — exactly the conditions under which
  governance surfaces drift from source truth.

- Components Affected:
  `src/odylith/runtime/governance/sync_workstream_artifacts.py` (22-step
  pipeline executor, `_execute_plan`, `_run_callable_with_heartbeat`,
  `build_sync_execution_plan`),
  `src/odylith/runtime/governance/sync_session.py` (new: `GovernedSyncSession`,
  `get_or_compute`, generation-scoped invalidation),
  `src/odylith/runtime/governance/workstream_inference.py`
  (`normalize_repo_token`, `_normalize_repo_token_cached`),
  `src/odylith/runtime/common/consumer_profile.py`
  (`_consumer_profile_cache_signature`, `load_consumer_profile`,
  `truth_root_path`),
  `src/odylith/runtime/governance/validate_backlog_contract.py`
  (`_validate_idea_specs`, `_parse_idea_spec`),
  `src/odylith/runtime/governance/component_registry_intelligence.py`
  (`_path_matches_prefix`, `build_component_registry_report`,
  `_build_component_registry_report_from_fingerprint`),
  `src/odylith/runtime/governance/delivery_intelligence_engine.py`
  (`build_delivery_intelligence_artifact`),
  `src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py`
  (`warm_projections`, `projection_input_fingerprint`).

- Environment(s): Odylith product repo maintainer mode, detached
  source-local posture on branch `2026/freedom/v0.1.11`. MacOS ARM64.
  Statistically validated on warm page-cache steady state. Cold-start
  overhead adds ~4.3s from OS page-cache priming.

- Root Cause: The sync pipeline was architected for correctness-first
  shared-nothing execution where each of the 22 steps independently
  computed its own view of repo state. This was sound for isolation but
  produced massive redundant computation as the repo grew:

  **84.9 million function calls per sync** at baseline, dominated by:

  1. **`posix.getcwd()`: 355,000 calls** — every path normalization
     resolved the working directory from scratch via a syscall.

  2. **`normalize_repo_token()`: 385,000 calls** — the hot-path
     canonicalizer for every repo-relative path comparison re-derived
     the repo root, consumer profile, and truth root on every call.

  3. **`load_consumer_profile()`: ~6,300 calls** — the consumer profile
     (repo posture, lane, runtime mode) was re-parsed from disk for each
     step independently.

  4. **`build_component_registry_report()`: 22 full rebuilds** — the
     expensive registry intelligence pass (scanning 25 components,
     87 events, 61 meaningful events) ran once per step because no
     shared state existed.

  5. **`_validate_idea_specs()`: 19 full parse passes** — the backlog
     contract validator re-parsed all 91 idea specs from YAML frontmatter
     on each invocation.

  6. **`_path_matches_prefix()`: 158,000 calls** — component-to-path
     matching iterated all prefix combinations without memoization.

  7. **`select.poll()`: 1.2 seconds cumulative** — the heartbeat
     mechanism for 22 threaded step invocations added serialized I/O
     polling overhead.

- Solution: Four waves of optimization, each validated by profiling:

  **Wave 1 — GovernedSyncSession (R2: 30.47s → 10.87s)**

  Introduced `sync_session.py` with a `GovernedSyncSession` dataclass
  using `contextvars.ContextVar` for process-local shared state. The
  session provides `get_or_compute(namespace, key, builder)` for
  session-scoped memoization with generation-aware invalidation via
  `bump_generation()`. Steps that mutate truth (repo_owned_truth,
  generated_surfaces) bump the generation and selectively invalidate
  dependent namespaces, while read-only validation steps freely reuse
  cached derivations.

  Key reuse targets:
  - Consumer profile loaded once, reused across 22 steps
  - Registry report built once, reused for validation, Compass, and
    surface renders
  - Backlog rows parsed once, shared across Compass, Radar, and
    delivery intelligence

  Result: 84.9M → 43.8M calls (48% reduction), 30.47s → 10.87s.

  **Wave 2 — Path interning and repo-root caching (R3-R4: 10.87s → 9.94s)**

  `normalize_repo_token()` was wrapped with `@lru_cache(maxsize=262144)`
  via `_normalize_repo_token_cached`, eliminating 76% of calls
  (385K → 92K). The `posix.getcwd()` syscall was eliminated entirely
  (355K → 0) by hoisting the repo root from the session context instead
  of re-resolving via `os.getcwd()` on every normalization.

  Result: 43.8M → 32.0M calls, 10.87s → 9.94s.

  **Wave 3 — Fingerprint-gated computation (R4 steady state)**

  `build_component_registry_report()` was wrapped with a fingerprint
  gate (`_build_component_registry_report_from_fingerprint`) that
  computes a content hash of inputs and skips the full rebuild when
  the fingerprint matches the cached result. The 22 per-step full
  rebuilds collapsed to 1 initial build + 21 fingerprint-match skips.

  `_validate_idea_specs()` was refactored to
  `_validate_idea_specs_uncached` with session-scoped caching,
  reducing 19 full YAML parse passes to 4.

  **Wave 4 — Compass context hoisting and heartbeat tuning (R7-R8)**

  Compass governance context (backlog rows, component lookup, delivery
  intelligence) was hoisted into the sync session so the Compass render
  step — the single largest step at 46% of total runtime — reuses
  pre-computed state instead of re-deriving it. Heartbeat pacing was
  tuned to reduce `select.poll()` overhead.

- Verification: Nine profiling rounds, with methodology improving across
  the campaign:

  **Single-shot rounds (R1-R7)** used `cProfile` with monkey-patched
  `_execute_plan` for per-step wall-clock timing. These established
  call-count reduction trends (noise-immune) but produced unreliable
  wall-clock numbers due to OS I/O variance. R5 and R6 were discarded
  entirely — identical code to R4 produced 27.1s (vs R4's 9.94s) due
  to system-level I/O noise (per-call lstat/json/open times were 2-3x
  higher while call counts were identical).

  **Statistical rounds (R8-R9)** used 1 warmup iteration (discarded) +
  5 measured iterations with median, min, max, stdev, and coefficient
  of variation (CV%) per step.

  | Round | Total | Calls | Method | CV% | Key commit |
  |-------|-------|-------|--------|-----|------------|
  | R1 | 30.47s | 84.9M | single-shot | — | baseline |
  | R2 | 10.87s | 43.8M | single-shot | — | GovernedSyncSession |
  | R3 | 10.11s | 37.0M | single-shot | — | session v2 |
  | R4 | 9.94s | 32.0M | single-shot | — | path interning |
  | R5 | 27.09s | 33.9M | single-shot | — | DISCARD: system noise |
  | R6 | 27.14s | 33.6M | single-shot | — | DISCARD: system noise |
  | R7 | 10.10s | 32.8M | single-shot | — | Compass context hoist |
  | R8 | 5.78s | — | median/5, warmup/1 | 3.1 | same as R7 |
  | R9 | 6.07s | — | median/5, warmup/1 | 13.9 | heartbeat + Compass cut |

  R8 and R9 are statistically equivalent — the three commits between
  them (heartbeat pacing, narration retune, Compass latency cut) did
  not produce a measurable warm-state improvement beyond noise.

  Final validated step profile (R8 median):

  | Step | Median | % of total | CV% |
  |------|--------|------------|-----|
  | Compass render | 2.682s | 46.4% | 7.7 |
  | Delivery intelligence | 0.590s | 10.2% | 4.5 |
  | Radar render | 0.378s | 6.5% | 3.6 |
  | Casebook render | 0.369s | 6.4% | 4.7 |
  | Registry render | 0.333s | 5.8% | 3.9 |
  | Shell render | 0.295s | 5.1% | 4.8 |
  | Registry spec sync (1st) | 0.255s | 4.4% | 3.5 |
  | Registry spec sync (2nd) | 0.203s | 3.5% | 2.9 |
  | All validation steps (1-11) | ~0.45s | 7.7% | <12 |

  Governance outcomes unchanged: 1875 tests passed, 0 failed. All 22
  sync steps produce identical outputs. `odylith sync --check-only`
  passes on the optimized tree.

- Prevention: The `GovernedSyncSession` architecture prevents regression
  to shared-nothing execution by making session-scoped reuse the default
  code path. New steps automatically inherit cached derivations. The
  generation-aware invalidation model means mutation steps (which bump
  the generation) correctly invalidate downstream caches without
  requiring explicit wiring per step.

  The profiling methodology learning is equally important: single-shot
  profiling of I/O-bound workloads is unreliable. OS page-cache state,
  background processes, and filesystem metadata caching can produce
  2-3x wall-clock variance between identical runs. Call counts are
  noise-immune and should drive optimization targeting. Wall-clock
  claims require warmup + multiple iterations + variance reporting.

- Detected By: Profiling campaign initiated during B-091 workstream
  implementation. Baseline measurement revealed the 30-second cost
  that had been absorbed as "sync is slow" without quantification.

- Failure Signature: `odylith sync --force --impact-mode full` taking
  30+ seconds on a repo with 91 workstreams, 25 components, and 36
  diagrams — a duration that grows super-linearly with repo size due
  to redundant O(steps × entities) recomputation.

- Trigger Path: Every `odylith sync` invocation, whether manual,
  hook-triggered, or agent-initiated.

- Ownership: Sync execution engine, governed-sync session architecture,
  B-091 workstream.

- Timeline:
  - 2026-04-12: R1 baseline profiling (30.47s, 84.9M calls)
  - 2026-04-12: R2-R4 session hoisting and path interning (→ 9.94s)
  - 2026-04-12: R5-R6 discarded (system I/O noise identified)
  - 2026-04-12: R7 clean rerun confirms 10.1s cold
  - 2026-04-12: R8 first statistical profiling (5.78s median, CV 3.1%)
  - 2026-04-12: R9 post-Compass-cut profiling (6.07s median, CV 13.9%)
  - 2026-04-12: Campaign concluded at 81% reduction with clear next targets

- Blast Radius: Every governance surface refresh, every agent startup
  that touches Compass, every post-edit hook, and every interactive
  `odylith sync` invocation. The improvement compounds: at typical
  agent interaction cadence (5-15 syncs per session), the cumulative
  savings are 2-6 minutes per session.

- Remaining Optimization Targets:
  1. **Compass render (2.68s, 46%)** — `load_backlog_rows` shared compute
     is partially hoisted but Compass still does significant internal
     derivation. Further hoisting of the standup brief narrative cache
     and release-target computation into the session would reduce this.
  2. **Delivery intelligence (0.59s, 10%)** — fingerprint-gated skip is
     partially implemented but the artifact still rebuilds on some
     generation bumps where the delivery inputs have not actually changed.
  3. **Dual registry spec sync (0.46s combined, 8%)** — the pipeline runs
     registry spec sync twice (step 14 and step 22); deduplicating when
     no intervening mutation changes registry inputs would save ~0.2s.
  4. **Cold-start page-cache penalty (~4.3s)** — the gap between cold
     (10.1s) and warm (5.8s) is almost entirely OS page-cache priming.
     A persistent sync daemon that keeps the working set hot would
     eliminate this, but adds operational complexity.

- Architectural Lessons:
  1. **Session-scoped memoization via ContextVar** is the right primitive
     for pipeline-internal reuse. It respects Python's threading model,
     does not leak across process boundaries, and the generation-aware
     invalidation model maps cleanly onto the sync pipeline's mutation
     semantics.
  2. **Call-count profiling is noise-immune; wall-clock profiling is not.**
     The R5/R6 incident — where identical code measured 27s instead of
     10s — proved that single-shot wall-clock numbers are unreliable for
     I/O-bound workloads. Call counts drove correct optimization
     targeting throughout; wall-clock validation required statistical
     methodology.
  3. **The Pareto frontier is steep.** Four optimization waves produced
     an 81% reduction. The remaining 5.8s is dominated by Compass
     (46%) — a single step that does genuine computation (narrative
     generation, release-target evaluation, timeline construction).
     Further gains require either parallelizing Compass internals or
     making Compass incremental, both of which are architecturally
     harder than the session-hoisting work that delivered the first 81%.
  4. **Shared-nothing is correct but expensive.** The original
     architecture was right to isolate steps for correctness — each
     step could reason about a clean world. The session model preserves
     that correctness guarantee (read-only reuse with explicit
     invalidation on mutation) while eliminating the computational cost.
     The key insight is that most sync steps are pure readers of the
     same facts; only a few steps mutate truth.
  5. **Warmup runs reveal the real steady-state.** The 10.1s cold →
     5.8s warm gap is not optimization — it is OS page-cache behavior.
     Reporting cold numbers as the optimization target would have
     directed effort at the wrong layer. The warmup methodology
     correctly separated algorithmic improvement from filesystem
     caching effects.

- Invariant Violated: No invariant was violated — this is a performance
  engineering learning, not a correctness bug. The sync pipeline
  produced correct outputs throughout; it simply did so with O(steps²)
  redundant computation that the session model reduced to O(steps).

- SLO/SLA Impact: Sync duration directly affects agent interaction
  latency and governance surface freshness. At 30s, sync was slower
  than typical edit cycles, creating incentive to skip refresh. At
  5.8s, sync is fast enough to run on every meaningful edit without
  breaking flow.

- Data Risk: None. All optimizations preserve output equivalence —
  the cached derivations produce bit-identical results to the
  uncached paths. The generation-aware invalidation model ensures
  stale cached state is never served after a mutation step.

- Security/Compliance: No security impact. Session state is
  process-local (ContextVar), never persisted to network-accessible
  storage, and scoped to a single sync execution lifetime.
