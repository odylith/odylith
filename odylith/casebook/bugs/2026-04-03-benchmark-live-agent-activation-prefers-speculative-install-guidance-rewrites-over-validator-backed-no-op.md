- Bug ID: CB-048

- Status: Open

- Created: 2026-04-03

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live `agent_activation` benchmark slice is now grounded
  enough to see the right install code, consumer guidance, and validator
  surfaces, but the `odylith_on` lane still prefers speculative install
  guidance rewrites over a validator-backed no-op or a tightly scoped fix when
  the current tree already satisfies the contract.

- Impact: The developer-core benchmark family still fails to convert improved
  grounding into validator-backed completion. `odylith_on` spends time and
  tokens rewriting install activation wording, can widen into the wrong
  guidance path, and then fails the focused install validators despite the
  checked-in repo already passing them locally.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, activation
  family benchmark corpus contract, install activation handoff, validator-first
  no-op discipline.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live Codex CLI benchmark shards for
  `install-time-agent-activation-contract`.

- Root Cause: Earlier proof misses looked like sandbox incompleteness because
  the disposable workspace was omitting validator companion files and the live
  runner could still inherit ambient user config. After those integrity gaps
  were fixed, the remaining failure became behavioral: the live prompt still
  reads like an instruction to "strengthen" install activation, so the agent
  rewrites already-correct install guidance instead of first proving the narrow
  validator, stopping with no changes when it already passes, or confining any
  fix to the true failing assertion surface.

- Solution: Tighten the live handoff for developer-core install families. The
  prompt must treat supporting docs as read-only unless they are explicit write
  anchors, bias grounded activation and install slices toward validator-backed
  no-op closeout when the current tree already satisfies the contract, and keep
  any widening limited to one concrete contradiction at a time. The corpus and
  prompt payload should also expose the minimal validator-relevant test surface
  when that surface is part of the real contract.

- Verification: Focused live shard reruns on 2026-04-03 showed the activation
  slice reaching full required-path recall and materially better precision
  after the sandbox and support-doc fixes, while still failing the focused
  install validators because the live agent edited install activation wording
  instead of stopping on current truth. The checked-in repo separately passes
  the relevant local install and CLI tests, so this is not a stale source-tree
  failure.

- Prevention: For validation-backed write slices, never phrase the live task as
  an unconditional improvement request when the slice may already be fixed.
  Grounded prompts must let the agent prove "already correct" and stop.

- Detected By: Focused single-lane `odylith_on` debug reruns for
  `install-time-agent-activation-contract` on 2026-04-03 during the B-021
  weak-family recovery pass.

- Failure Signature: The live result reports full or near-full required-path
  recall but fails the focused install validators after changing
  `src/odylith/install/agents.py` or `src/odylith/install/manager.py` to
  "strengthen" activation wording, often missing the exact consumer guidance
  line already asserted by `tests/integration/install/test_manager.py`.

- Trigger Path: `odylith benchmark --repo-root . --mode odylith_on --case-id install-time-agent-activation-contract`
  through the live Codex CLI runner.

- Ownership: Benchmark live prompt discipline, activation-family corpus truth,
  validator-backed no-op behavior.

- Timeline: The slice first looked like a sandbox problem during the broader
  honest-benchmark hardening wave. By 2026-04-03, validator companion snapshot
  completeness and ambient user-config inheritance were fixed, revealing the
  remaining behavioral miss.

- Blast Radius: Developer-facing benchmark credibility, activation-family live
  validation rate, install and upgrade benchmark families that share the same
  prompt posture, and the release push to move from `hold` back to `pass`.

- SLO/SLA Impact: Benchmark completion quality degrades immediately on one of
  the highest-priority developer-core families, and latency or token cost rises
  because the agent spends work proving the wrong thing.

- Data Risk: Low direct data risk; high benchmark quality risk.

- Security/Compliance: No direct security impact; this is a validation and
  benchmark quality failure.

- Invariant Violated: A grounded validation-backed slice must prefer a
  validator-backed no-op when the current tree already satisfies the contract
  over speculative contract rewrites.

- Workaround: Focused local shard debugging and manual validator inspection can
  confirm the failure mode, but there is no acceptable publication workaround.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not treat support docs or guidance text as edit targets
  on activation slices unless they are explicit write anchors or a focused
  validator contradiction points there directly.

- Preflight Checks: Inspect this bug, `CB-027`, `CB-046`, the active B-021
  plan, the activation scenario in
  `odylith/runtime/source/optimization-evaluation-corpus.v1.json`, and the
  live prompt plus payload unit suites before changing this path.

- Regression Tests Added: Pending.

- Monitoring Updates: Track activation-family live reruns for
  `required_path_recall`, `required_path_precision`,
  `hallucinated_surface_rate`, `validation_success_proxy`,
  `expectation_ok`, and the presence of install-guidance-only rewrites in the
  structured live result.

- Residual Risk: Install and upgrade families can continue to look grounded but
  fail validator-backed completion until the no-op bias and read-only support
  doc discipline are restored.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`,
  `2026-04-02-benchmark-support-doc-selector-overweights-generic-guidance-on-proof-slices.md`,
  `2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md`

- Version/Build: `v0.1.7` benchmark weak-family recovery wave in progress on
  2026-04-03.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS`,
  `ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS`,
  `ODYLITH_REASONING_MODEL`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT`.

- Customer Comms: Do not claim the activation-family live path is recovered
  until the focused shard reaches validator-backed success honestly.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/install/agents.py`,
  `src/odylith/install/manager.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
