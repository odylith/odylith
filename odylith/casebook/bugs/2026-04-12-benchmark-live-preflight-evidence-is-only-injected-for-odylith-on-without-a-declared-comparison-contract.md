- Bug ID: CB-106

- Status: Open

- Created: 2026-04-12

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark runner can execute scenario-declared focused
  local checks only for `odylith_on` and inject their results into the prompt
  as current workspace evidence even though the published primary comparison
  still describes the live pair as if the only intended lane difference were
  grounding scaffold.

- Impact: The benchmark can overstate how isolated the `odylith_on` versus
  `odylith_off` comparison really is. Reviewers can read the proof as a
  grounding-only ablation while the live `odylith_on` lane is benefiting from
  broader product affordances that change both prompt evidence and, in some
  no-op cases, completion basis.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, benchmark
  publication contract, benchmark component spec, README benchmark framing.

- Environment(s): Odylith product repo maintainer mode, live Codex benchmark
  lanes, proof and diagnostic publication flow.

- Root Cause: The benchmark product evolved into a broader Odylith assistance
  stack, but the live comparison contract and report fields were not updated to
  declare preflight evidence as an allowed `odylith_on` affordance. The runner
  therefore changed live proof semantics without a matching public contract.

- Solution: Redefine the primary benchmark claim honestly as
  `full_product_assistance_vs_raw_agent`, enumerate allowed `odylith_on`
  affordances, log preflight evidence commands and status in the live payload,
  and mark any focused no-op proxy outcome explicitly so the benchmark no
  longer hides the basis for an Odylith-only advantage.

- Verification: Add live-execution and runner coverage for preflight evidence
  logging, fairness contract reporting, focused no-op proxy basis, and
  full-product contract labels; rerun proof and diagnostic benchmark profiles.

- Prevention: When a benchmark lane gains a new product affordance, the lane
  contract, report payload, docs, graphs, and acceptance wording must be
  updated in the same change.

- Detected By: Maintainer fairness review of the live `odylith_on` versus
  `odylith_off` benchmark pair.

- Failure Signature: `odylith_on` prompt payload contains current workspace
  focused-check results, `odylith_off` does not, and the published benchmark
  story still implies grounding-only lane differences.

- Trigger Path: `odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark live-lane contract, fairness reporting, and publication
  semantics.

- Timeline: The live benchmark kept evolving toward the real Odylith product
  stack, but the contract wording did not keep up with the preflight-evidence
  path.

- Blast Radius: Benchmark credibility, release proof interpretation, execution-
  governance value claims, and any public story about `odylith_on` versus
  `odylith_off`.

- SLO/SLA Impact: No direct service impact, but high benchmark-trust impact.

- Data Risk: Low direct data risk; high interpretability and fairness risk.

- Security/Compliance: None directly.

- Invariant Violated: The published benchmark comparison contract must match the
  real lane affordances. Hidden or undeclared `odylith_on`-only preflight
  evidence is not acceptable.

- Workaround: Manually explain that the live pair measures more than grounding.
  Not acceptable as a release-proof contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not claim a narrower ablation than the runner actually
  executes. If a lane gets preflight evidence, the benchmark report must
  declare it.

- Preflight Checks: Inspect live-execution preflight commands, prompt payload
  sections, result status basis, and benchmark report comparison metadata
  together.

- Regression Tests Added: Pending.

- Monitoring Updates: Pending benchmark report fields for comparison contract,
  preflight evidence mode, commands, result status, and fairness findings.

- Residual Risk: Even after contract repair, a full-product comparison still
  needs a serious corpus and honest docs or the proof will remain easy to
  dismiss.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-live-proof-overstates-paired-session-metrics-and-reuses-packet-era-guardrails.md`
  and
  `2026-04-02-benchmark-live-prompt-surfaced-routing-metadata-instead-of-concrete-focus.md`

- Version/Build: `v0.1.11` benchmark fairness hardening wave on 2026-04-12.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`

- Customer Comms: Benchmark docs and README should say the primary comparison
  measures the full Odylith assistance stack versus the raw host agent.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
