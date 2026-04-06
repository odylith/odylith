- Bug ID: CB-041

- Status: Closed

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The public `odylith subagent-router` and
  `odylith subagent-orchestrator` wrappers injected `--repo-root` ahead of the
  inner subcommand. Honest benchmark validator commands such as
  `odylith subagent-router --repo-root . --help` therefore failed with
  argument-parsing errors instead of exercising the documented public CLI
  contract.

- Impact: Proof runs undercounted validator-backed success on router and
  orchestrator benchmark cases even when the underlying product behavior was
  otherwise correct. That made the benchmark look less trustworthy and pushed
  maintainers toward blaming the corpus or the harness for what was actually a
  broken public command surface.

- Components Affected: `src/odylith/cli.py`,
  `src/odylith/runtime/common/command_surface.py`, benchmark proof validator
  contract, `subagent-router` public CLI wrapper,
  `subagent-orchestrator` public CLI wrapper.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live `odylith benchmark --repo-root . --profile proof`
  reruns and direct public CLI invocations.

- Root Cause: The top-level Odylith CLI treated the router and orchestrator
  wrappers like flat commands and prepended `--repo-root` unconditionally.
  Their inner parsers are verb-first surfaces, so the forwarded argument order
  broke both help-only and verbed invocations.

- Solution: Add a nested-subcommand repo-root forwarding helper that injects
  `--repo-root` after the inner verb when needed and leaves help-only calls
  untouched. Route both manual dispatch and argparse dispatch for
  `subagent-router` and `subagent-orchestrator` through that helper.

- Verification: Direct public help commands now exit `0`, the focused CLI
  regression suite passes, and targeted warm proof rerun `783b4a26c75941d4`
  converts the affected benchmark cases into real validator-backed outcomes.

- Prevention: Treat benchmark validators as first-class public-product
  consumers. If the documented `odylith ...` wrapper is broken, fix the
  wrapper instead of weakening the validator command or bypassing the public
  contract.

- Detected By: Manual proof triage after router and orchestrator benchmark
  cases stayed blocked despite narrow grounded slices and direct evidence that
  the validator commands themselves should have been valid.

- Failure Signature: `odylith subagent-router --repo-root . --help` and
  `odylith subagent-orchestrator --repo-root . --help` exit `2` with
  `invalid choice: '.'`, and proof cases that depend on those validators fail
  without reaching a real validator-backed outcome.

- Trigger Path: `odylith benchmark --repo-root . --profile proof` on scenarios
  that include router or orchestrator validator commands, plus direct public
  CLI usage of those wrappers.

- Ownership: Odylith public command surface and benchmark proof validator
  integrity.

- Timeline: The stricter honest proof lane already exposed prompt and runtime
  defects, but this slice revealed a separate class of problem: the benchmark
  was correctly calling the public validator commands and the product wrapper
  itself was lying about its contract.

- Blast Radius: Proof-lane validation success, expectation success,
  benchmark-trust narrative, and any maintainer or operator using the wrapped
  router or orchestrator help path.

- SLO/SLA Impact: Benchmark proof and direct operator validation both lose
  trust when the documented public wrapper fails on its own minimal contract.

- Data Risk: Low direct data risk, high proof-integrity risk.

- Security/Compliance: None directly.

- Invariant Violated: Public `odylith` wrapper commands must preserve the
  documented verb-first contract of their owned subcommand surfaces.

- Workaround: Call the inner Python modules directly or reorder arguments by
  hand. Not acceptable for proof or for public product ergonomics.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not rewrite benchmark validators away from documented
  public `odylith ...` entrypoints just because the wrapper is broken. Fix the
  product contract first.

- Preflight Checks: Exercise both help-only and verbed calls for wrapped
  nested subcommands before using them as proof validators again.

- Regression Tests Added:
  `test_subagent_router_dispatch_accepts_forwarded_flags`,
  `test_subagent_orchestrator_dispatch_accepts_forwarded_flags`,
  `test_subagent_router_help_does_not_receive_injected_repo_root`,
  `test_subagent_orchestrator_help_does_not_receive_injected_repo_root`

- Monitoring Updates: Benchmark docs and specs now state explicitly that
  broken public validator wrappers are product failures, not benchmark noise.

- Residual Risk: The wrapper contract is fixed, but proof still remains on
  `hold` where Odylith loses honestly on precision-heavy cases.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-live-proof-overstates-paired-session-metrics-and-reuses-packet-era-guardrails.md`,
  `2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md`

- Version/Build: `v0.1.7` benchmark proof hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL=gpt-5.4`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT=medium`

- Customer Comms: Do not dismiss validator failures on router or orchestrator
  benchmark cases as harness weirdness when the public wrapper itself is
  broken. The honest fix is on the product surface.

- Code References: `src/odylith/cli.py`,
  `src/odylith/runtime/common/command_surface.py`,
  `tests/unit/test_cli.py`

- Runbook References: `docs/benchmarks/README.md`,
  `docs/benchmarks/REVIEWER_GUIDE.md`,
  `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
