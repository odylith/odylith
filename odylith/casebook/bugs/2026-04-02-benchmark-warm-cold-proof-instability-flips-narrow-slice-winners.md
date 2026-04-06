- Bug ID: CB-040

- Status: Open

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The strict `proof` lane can still flip the apparent winner
  between `warm` and `cold` cache profiles on the same narrow grounded slices.
  In the targeted `gpt-5.4` / `medium` rerun `827fddc9e6f30902`, architecture
  and explicit-workstream cases alternated between near-perfect precision and
  extreme widening depending on cache posture.

- Impact: Odylith can look materially better after a prompt-contract fix and
  still fail publication because the proof lane is not robust across the cache
  profiles it is supposed to publish conservatively. That weakens benchmark
  trust and makes it hard to tell whether the remaining defect lives in
  retrieval, memory, cache preparation, or live execution drift.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  Odylith context-engine cache posture, proof-lane warm/cold robustness
  contract.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live `odylith benchmark --repo-root . --profile proof`
  runs under `gpt-5.4` / `medium`.

- Root Cause: Partially isolated. The unstable narrow-slice failures were not
  just cache posture; Odylith's live proof handoff was still carrying
  supplemental docs, retrieval-plan doc spillover, and validator-adjacent
  surfaces into scenarios whose truthful required surface was already fully
  covered by the listed anchors. That widened `odylith_on` differently across
  `warm` and `cold` runs and made the cache effect look larger than it really
  was.

- Solution: In progress. Strict bounded proof slices now strip supplemental
  support reads and retrieval-plan doc spillover from the live prompt handoff,
  and the prompt now treats validator-only tests plus generated or rendered
  artifacts as out of scope unless a focused contradiction points there. The
  broader full-corpus proof still needs a rerun to confirm that this fix holds
  outside the targeted narrow-slice sample.

- Verification: Targeted live proof rerun `827fddc9e6f30902` reproduced the
  instability across `architecture-odylith-self-grounding` and
  `wave3-explicit-workstream`. Follow-up rerun `f9fc870105ca9284` still held
  with `-0.435` precision delta on a five-case narrow-slice sample. After the
  strict-boundary suppression fix, rerun `f082b3dc4be2002a` flipped that same
  five-case proof slice to `provisional_pass` with `+0.342` precision delta,
  `-0.342` hallucinated-surface delta, and `-8656.0 ms` latency delta while
  keeping recall and validation flat.

- Prevention: Treat warm/cold robustness as a first-class product requirement.
  Do not narrate a warm-only recovery as a benchmark fix when the conservative
  published proof still flips under cold posture.

- Detected By: Targeted proof rerun after the benchmark live-prompt focus fix.

- Failure Signature: Warm and cold runs on the same case alternate between
  near-perfect precision and broad validator-adjacent or generated-surface
  widening, while recall stays the same and validators or expectation success
  do not fully explain the drift.

- Trigger Path: `odylith benchmark --repo-root . --profile proof --case-id architecture-odylith-self-grounding --case-id orchestration-control-advisory-loop --case-id wave3-explicit-workstream`

- Ownership: Benchmark proof robustness and cache-profile stability.

- Timeline: The first prompt cleanup reduced some widening but left the
  narrow-slice proof sample on `hold`. The stricter boundary suppression pass
  then removed support-read spillover on the same sample and converted the
  targeted proof slice to `provisional_pass`, leaving the broader corpus rerun
  as the next proof obligation.

- Blast Radius: Benchmark publication trust, proof-lane status, README refresh
  credibility, and tuning decisions for Odylith memory or retrieval.

- SLO/SLA Impact: The release-safe proof lane stays on `hold` even when one
  profile looks meaningfully better, which is correct but costly.

- Data Risk: Low direct data risk, high product-proof risk.

- Security/Compliance: None directly.

- Invariant Violated: A release-safe proof lane should not flip from tight
  grounding to extreme widening on the same narrow task just because the cache
  posture changed.

- Workaround: Run targeted warm/cold slices and inspect both individually, but
  do not publish from the easier posture alone.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not call the proof lane fixed until the same scenario
  stays grounded under both `warm` and `cold`.

- Preflight Checks: Diff warm versus cold packet payloads, live prompt text,
  and observed command traces before changing cache-profile publication rules.

- Regression Tests Added: None yet. Needs targeted robustness coverage after
  the underlying cause is isolated.

- Monitoring Updates: Track the next full proof rerun for whether the same
  strict-boundary suppression improvement holds across the wider corpus instead
  of only the five-case narrow-slice sample.

- Residual Risk: Medium-high until the full `gpt-5.4` / `medium` proof corpus
  is rerun. The narrow-slice sample is materially better, but broader
  governance and install families may still hide warm/cold drift.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-live-prompt-surfaced-routing-metadata-instead-of-concrete-focus.md`,
  `2026-04-02-benchmark-live-proof-overstates-paired-session-metrics-and-reuses-packet-era-guardrails.md`

- Version/Build: `v0.1.7` benchmark robustness investigation on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL=gpt-5.4`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT=medium`

- Customer Comms: Do not claim proof-lane stability from a warm-only win. The
  release-safe story still depends on both cache profiles.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `/tmp/odylith-proof-targeted-medium-v2.json`

- Runbook References: `docs/benchmarks/README.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
