- Bug ID: CB-365

- Status: Open

- Created: 2026-10-17

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The session-brief-runtime-path-ambiguity corpus scenario names the same pytest node twice under its old test_odylith_benchmark_runner.py module. The unchanged function now lives in test_benchmark_context_packet_contracts.py. In completed full B 2a741e4ffa9ec90d at canonical H 9d3674c0a, focused precheck and final validation exit 4 with not found, causing an unnecessary host escalation and a blocked outcome. A fresh direct old-node reproduction also exits 4 with no tests run. This is an evaluator address defect, not demonstrated failure of the session-brief implementation.

- Impact: A valid existing behavior check cannot run; the benchmark reports failed validation and spends avoidable host time.

- Components Affected: benchmark

- Environment(s): Product repo v0.1.15 detached source-local; full 82-scenario warm/cold B 2a741e4ffa9ec90d at H 9d3674c0a and primary authoring checkout direct pytest reproduction.

- Detected By: Read-only diagnosis of retained full proof, followed by direct old-node reproduction with bytecode and pytest cache disabled.

- Failure Signature: pytest exits 4: not found tests/unit/runtime/test_odylith_benchmark_runner.py::test_session_brief_exact_path_hot_path_keeps_only_live_narrowing_signal; no tests ran.

- Trigger Path: Corpus session-brief-runtime-path-ambiguity validation_commands and focused_local_checks at optimization-evaluation-corpus.v1.json lines 184 and 187.

- Ownership: Benchmark corpus validator addresses and moved-test ownership.

- Timeline: Captured 2026-10-17 through `odylith bug capture`.

- Blast Radius: The session brief exact runtime-path ambiguity benchmark scenario and release-proof interpretation.

- SLO/SLA Impact: Retained candidate outcome takes 66.905 seconds and blocks validation; the prior validated focused closure took 3.315 seconds. This does not explain or waive the separate failed global timing comparison.

- Data Risk: No product data loss; benchmark attribution and qualification accuracy are affected. Retain original reports unchanged.

- Security/Compliance: No direct security or compliance defect established; strict validation must remain required.

- Invariant Violated: A corpus validator must resolve the same existing behavior test after its owning module moves, without substituting easier assertions or changing the measured contract.

- Root Cause: The test function moved to tests/unit/runtime/test_benchmark_context_packet_contracts.py while both scenario command addresses retained the old module.

- Solution: Change only the two module paths to the existing moved owner, keeping the test name, scenario meaning, expectations, execution profile, budgets and every threshold exact.

- Source Admission: The two-address correction is an authored corpus change with an exact bundled mirror. Existing selective admission owns the Casebook, Radar, plan, Registry, Atlas, and release-note surfaces, but no owner admits this canonical corpus pair. Every other managed-generation command correctly refuses the full five-file delta. Extend the existing authored-selective owner only for this canonical source in the detached source-local product lane: require its coupled mirror, regular files, unchanged modes, source/mirror equality, confinement, the existing strict delta fence, and a final lane and intent recheck. Do not add a command, broad allowlist, force path, repair path, reinstall path, or manual publisher. The selected generation stays active until the normal successor switch succeeds.

- Rollback/Forward Fix: Forward fix the two corpus addresses in the existing authoring checkout; retain H 9d3674c0a and its original B/comparison as historical proof of that source.

- Verification: Fresh direct old-address reproduction exits 4 with no tests run and the exact not-found signature. The same existing function at test_benchmark_context_packet_contracts.py:162 passes directly: 1 passed in 0.78 seconds, with bytecode and pytest cache disabled and test-module SHA-256 3520c915541720dac492d791196236fc72514a46e5570d33e15ce4221f26bfcb unchanged. The retained before and existing-node JSON receipts contain exact commands and outputs. The two source-corpus addresses and identical bundle mirror are now corrected. The unchanged moved test plus five existing canonical corpus checks pass after the patch: 6 passed in 0.75 seconds. Normalized corpus loading retains all 82 scenarios and resolves both commands to that same existing function. Only those address strings change; no scenario, expectation, profile, budget or threshold changes. This unreleased source patch receives no old H/B credit; its source-publication adoption remains pending under the existing guard.

- Admission Evidence: `maintainer-corpus-source-adoption-diagnosis.md` (SHA-256 `687ecb448082fdb335a9ce7bc9cdde4ace818201218c39e5dabf207df8d8f056`) verifies the selected generation is intact and identifies exactly five intended deltas: this Casebook record, B-142, the active plan, and the canonical corpus source with its mirror. The bounded admission implementation passes `318` tests in `15.44s` across six existing modules, including supported CLI corpus-only and mixed-Casebook admission/publication in disposable fixtures. No primary publication has occurred; this is not new H/B credit.

- Prevention: When a corpus-referenced test moves, update its explicit validator addresses and collect the existing node before source freeze.

- Agent Guardrails: Do not weaken CB-364 latency/token checks or the failed predecessor timing rule, alter original B bytes, claim old proof for changed source, or access the protected final.

- Preflight Checks: Search existing Casebook; retain exact old-node exit 4; verify the target function exists at the new owner; confirm managed publication is stable and clean before governed writes.

- Version/Build: 0.1.15; observed canonical H 9d3674c0a4384e76279d42985c862eaa712046f7; correction remains unreleased.

- Related Incidents/Bugs: CB-347; CB-364; B-141; B-142

- Code References: - odylith/runtime/source/optimization-evaluation-corpus.v1.json
- tests/unit/runtime/test_benchmark_context_packet_contracts.py

- Runbook References: - odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md
