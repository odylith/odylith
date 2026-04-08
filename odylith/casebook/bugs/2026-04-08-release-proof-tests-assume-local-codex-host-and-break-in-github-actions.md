- Bug ID: CB-072

- Status: Closed

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The `pytest` and `candidate-proof` release-candidate lanes still
  depended on local Codex-host assumptions inside unit tests. On GitHub-hosted
  runners, the affected tests executed without a native-spawn-capable host
  runtime and without a local `codex` binary, so they failed even though the
  underlying product contract was behaving correctly for that environment.

- Impact: Canonical `v0.1.10` release prep stopped in PR CI before the branch
  could merge to `main`, blocking the normal GA lane on false-negative proof.

- Components Affected: `tests/unit/runtime/test_odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_subagent_reasoning_ladder.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`, release-candidate CI
  proof portability, release component contract.

- Environment(s): Odylith product repo maintainer mode, GitHub Actions PR
  `pytest`, GitHub Actions `candidate-proof`, `v0.1.10` release prep.

- Root Cause: Several tests asserted native-spawn-ready packet fields or Codex
  CLI availability without explicitly pinning the host-runtime contract they
  intended to prove. Locally those tests passed because the maintainer session
  exposed Codex host markers and a real `codex` binary; in GitHub Actions the
  same ambient assumptions were false, so the tests observed the correct
  fail-closed payload shape and treated it as a regression.

- Solution: Make the affected tests deterministic. Tests that prove Codex
  host-native spawn behavior now force a Codex host runtime explicitly, and the
  Codex exec-command unit test now mocks CLI discovery instead of requiring a
  real local binary on the runner.

- Verification: `python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_live_execution.py -k codex_exec_command_disables_plugins_multi_agent_and_personality`;
  `python3 -m pytest -q tests/unit/runtime/test_subagent_reasoning_ladder.py -k "route_request_spawn_payloads_never_inherit_parent_defaults or lifecycle_and_native_spawn_payloads_match_for_every_profile"`;
  `python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py -k "component_governance_hot_path_keeps_exact_governed_slice_grounded or component_honesty_governance_hot_path_stays_route_ready or run_scenario_mode_passes_selected_docs_to_live_prompt_payload or route_ready_hot_path_payload_drops_redundant_prompt_metadata or route_ready_hot_path_packet_skips_packet_metrics_and_handoff_scaffolding"`.

- Prevention: Release-proof tests must make host-runtime and tool-availability
  assumptions explicit. Do not let unit proof silently inherit the maintainer
  workstation's live Codex environment.

- Detected By: `v0.1.10` PR CI and `candidate-proof` while preparing the
  canonical release lane for GA.

- Failure Signature: GitHub Actions `pytest` and `candidate-proof` fail with
  `RuntimeError: Codex CLI binary 'codex' is not available`, missing
  `native_spawn_ready`, or missing `apply_parent_defaults` in otherwise healthy
  route payloads.

- Trigger Path: Run the affected unit tests on a non-Codex host runtime or a
  runner without a local `codex` binary in `PATH`.

- Ownership: Release proof portability, benchmark runner/unit proof contracts,
  subagent-routing unit proof discipline.

- Timeline: surfaced on 2026-04-08 during `v0.1.10` release prep after broader
  local validation had already passed on a Codex-capable maintainer machine.

- Blast Radius: PR mergeability, release-candidate credibility, and canonical
  GA readiness for any release branch validated on GitHub-hosted runners.

- SLO/SLA Impact: No customer outage; release-lane blocker in a P0 maintainer
  path.

- Data Risk: Low data risk, high release-operations risk because the branch
  cannot advance to canonical `main` while the false-negative proof persists.

- Security/Compliance: Low direct security risk; the issue is release proof
  integrity and environmental portability.

- Invariant Violated: Canonical release-proof tests must pass or fail based on
  product behavior, not on incidental maintainer workstation capabilities.

- Workaround: None clean besides re-running on a Codex-capable machine, which
  would hide the real portability gap instead of fixing it.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When a unit test proves host-specific behavior, force the
  intended host/runtime in the test itself. Do not let CI proof depend on the
  ambient local shell or installed CLIs.

- Preflight Checks: Inspect the three failing test modules, confirm the CI log
  signatures, and compare their assumptions with the actual host-runtime
  contract before editing assertions.

- Regression Tests Added: Targeted deterministic host-runtime proof across the
  affected benchmark live-execution, benchmark-runner, and subagent-routing
  test lanes.

- Monitoring Updates: Watch PR `pytest` and `candidate-proof` for renewed
  host-runtime portability failures after future routing or benchmark changes.

- Related Incidents/Bugs:
  [2026-03-28-github-test-workflow-bypasses-hatch-managed-environment.md](2026-03-28-github-test-workflow-bypasses-hatch-managed-environment.md)
  [2026-04-08-release-workflows-still-pin-first-party-actions-on-node-20-runtime.md](2026-04-08-release-workflows-still-pin-first-party-actions-on-node-20-runtime.md)

- Version/Build: branch `2026/freedom/v0.1.10` before canonical merge.

- Customer Comms: internal maintainer-only release-proof portability fix.

- Code References: `tests/unit/runtime/test_odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_subagent_reasoning_ladder.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: current branch `2026/freedom/v0.1.10`, pending commit/push.
