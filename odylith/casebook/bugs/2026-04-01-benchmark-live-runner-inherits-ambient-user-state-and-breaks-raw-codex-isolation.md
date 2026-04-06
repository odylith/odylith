- Bug ID: CB-027

- Status: Open

- Created: 2026-04-01

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live `odylith_on` versus `odylith_off` benchmark runner
  still allows the raw Codex CLI control to inherit ambient workstation or repo
  state, so the benchmark can compare Odylith against a contaminated baseline
  instead of a truly contained same-task raw Codex lane.

- Impact: Benchmark credibility is at risk. Shared `.odylith` state, global
  caches, host Python or package-manager state, shell startup drift, or desktop
  Codex environment variables can change both quality and latency outcomes and
  make the public `odylith_on` versus `odylith_off` story fail the smell test.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, benchmark
  component integrity contract, temp worktree provisioning, validator
  execution environment, `odylith_off` publication proof.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, local live Codex CLI benchmark runs, and any workstation with
  non-trivial shell, Git, Python, or Codex Desktop state.

- Root Cause: The first live-runner version improved the baseline contract but
  still reused too much host state. The disposable workspace originally shared
  repo `.odylith` runtime state, validator commands could escape into host
  paths, and the Codex subprocess environment was seeded from ambient
  `os.environ`, which exposed pyenv, Homebrew, desktop Codex variables, global
  tool config, and shared cache or temp roots to the benchmark lanes.
  Subsequent weak-family reruns exposed a second, narrower clean-room gap:
  stripped validator-truth files were still being restored from the ambient
  repo root instead of from the scoped benchmark snapshot, which let unrelated
  dirty repo state re-enter disposable worktrees immediately before validation
  (`CB-043`).

- Solution: Build the live benchmark runner around an explicit trust boundary.
  Both lanes must execute in equally stripped disposable workspaces with a
  temporary Codex home, localized cache and temp roots, localized Git and
  Python state, no inherited user shell startup, no plugins, no MCP servers,
  no project-doc fallback, no multi-agent features, and a reportable
  same-model same-reasoning execution contract. Publication must stay blocked
  until the runner proves that isolation end to end. That contract now also
  requires stripped validator truth to be captured from the scoped workspace
  before removal and restored only from that snapshot stash, never from the
  ambient repo root. The live runner now also ignores ambient
  `~/.codex/config.toml` model and reasoning defaults entirely: only explicit
  benchmark env overrides, repo reasoning payload, or the benchmark default
  contract may set the live Codex model or reasoning effort.

- Verification: The contamination was reproduced during the 2026-04-01 honest
  raw-baseline redesign when live runs referenced repo-root `.odylith`
  artifacts and the benchmark harness still inherited workstation variables
  such as pyenv and Codex Desktop state. Focused regressions now cover
  temporary Codex home isolation, validator command rewriting, localized cache
  and temp roots, non-symlinked `.odylith` workspace provisioning, scoped
  validator-truth capture or restore, and live execution contract resolution
  that ignores ambient user Codex defaults. The final clean no-cap rerun is
  still the remaining proof obligation.

- Prevention: Treat the live benchmark harness as a product trust boundary.
  Any shared mutable surface between the workstation and the raw-Codex control
  invalidates publication. Debug convenience is never allowed to soften this
  contract.

- Detected By: User escalation on 2026-04-01 after a supposedly honest live
  `odylith_on` versus `odylith_off` rerun both failed smell tests and produced
  raw-lane behavior that still reflected local repo or workstation state.

- Failure Signature: Live benchmark traces reference
  `/Users/freedom/code/odylith/.odylith/...`, inherited pyenv or desktop Codex
  variables, shared host caches or temp roots, or validator paths that bypass
  the disposable workspace while still being narrated as raw-Codex proof.

- Trigger Path: `odylith benchmark --repo-root . --mode odylith_on --mode odylith_off`
  through the live Codex CLI runner.

- Ownership: Benchmark live-runner isolation and raw-baseline trust boundary.

- Timeline: The raw-baseline redesign surfaced the weaker fake-baseline story,
  then the live runner exposed two deeper integrity failures on the same day:
  the false-pass gate and the raw-lane contamination gap. The gate was fixed;
  the sandbox hardening remains in flight.

- Blast Radius: Public README benchmark claims, maintainer release-proof
  decisions, benchmark family deltas, and any product planning that trusts the
  live `odylith_on` versus `odylith_off` numbers.

- SLO/SLA Impact: Benchmark trust and release readiness degrade immediately.
  Maintainers can waste hours analyzing bad results that are artifacts of the
  harness instead of the product.

- Data Risk: Low direct data risk, but high integrity risk because the harness
  can misrepresent what raw Codex actually did.

- Security/Compliance: This is primarily a benchmark integrity and local trust
  boundary failure, not a remote exploit.

- Invariant Violated: `odylith_off` must be the same raw Codex CLI on the same
  task with the same model and reasoning contract in an equally stripped
  sandbox. Only the Odylith grounding scaffold may differ.

- Workaround: None that is acceptable for publication. Warm targeted reruns and
  manual trace inspection are useful for diagnosis only.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not publish or narrate live benchmark results as
  `odylith_on` versus raw Codex proof until the report shows a strict contained
  sandbox with no shared mutable workstation or repo state.

- Preflight Checks: Inspect this bug, the benchmark component spec, the active
  B-022 benchmark plan, `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  and the live benchmark unit suite before changing the benchmark harness.

- Regression Tests Added: `test_minimal_codex_config_text_disables_guidance_surfaces`,
  `test_resolved_live_execution_contract_prefers_env_over_repo_and_ignores_user_defaults`,
  `test_sandbox_validation_commands_rewrite_repo_venv_paths`,
  `test_sandbox_process_env_uses_local_cache_and_temp_roots`,
  `test_provision_workspace_odylith_root_copies_minimal_state`.

- Monitoring Updates: Live benchmark reports now publish isolation fields such
  as `isolated_codex_home`, `workspace_odylith_isolated`,
  `workspace_venv_symlinked`, `sandboxed_validation_commands`,
  `sandboxed_cache_env`, and the live timeout policy.

- Residual Risk: Until the remaining whitelist environment and no-cap rerun
  land, raw-lane accuracy, latency, and validator outcomes can still reflect
  harness contamination rather than product truth. The remaining scoped
  snapshot gap for dirty same-package Python siblings is tracked separately in
  `CB-044`, and the still-open live activation behavior miss that rewrites
  already-correct install guidance instead of stopping on validator-backed
  truth is tracked separately in `CB-048`.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-gate-can-pass-when-both-live-lanes-fail.md`,
  `2026-04-02-benchmark-validator-truth-restore-rehydrates-ambient-repo-state-outside-scoped-snapshot.md`,
  `2026-04-02-benchmark-scoped-workspace-snapshot-omits-dirty-same-package-python-dependencies.md`

- Version/Build: `v0.1.7` benchmark integrity hardening wave in progress on
  2026-04-01.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS`,
  `ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS`,
  `ODYLITH_REASONING_MODEL`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT`.

- Customer Comms: Public benchmark claims must stay conservative until the
  strict sandbox rerun is complete.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
