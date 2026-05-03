- Bug ID: CB-163

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-03

- Severity: P2

- Reproducibility: Always

- Type: Tooling

- Description: The context-engine diagnostic benchmark path defaulted to warm cache and could fail in source-local maintainer posture when optional LanceDB/Tantivy dependencies were only available in the managed runtime. A closed stdout pipe during JSON benchmark output also surfaced a Python BrokenPipeError traceback instead of exiting cleanly.

- Impact: Maintainers checking engine readiness could see a failed diagnostic benchmark or noisy traceback even though the cold diagnostic path and managed memory substrate were healthy.

- Components Affected: benchmark

- Environment(s): Odylith product repo dev-maintainer/source-local posture on branch 2026/freedom/v0.1.14.

- Detected By: Manual engine-integrity hardening pass while checking Context Engine and Benchmark activation.

- Failure Signature: RuntimeError: Benchmark warm cache requires an active local LanceDB/Tantivy memory substrate before proof runs; BrokenPipeError: [Errno 32] Broken pipe.

- Trigger Path: PYTHONPATH=src python -m odylith.cli context-engine benchmark --profile diagnostic --no-write-report --json | head -n 1

- Ownership: Benchmark and Context Engine CLI proof lane.

- Timeline: Observed during the 2026-05-03 engine-integrity pass after Context Engine status showed a healthy managed memory substrate but no live daemon.

- Blast Radius: Maintainer diagnostic benchmark runs, source-local readiness checks, and shell pipelines that consume JSON benchmark output.

- SLO/SLA Impact: Low-latency proof lane became noisy or blocked under a valid source-local posture.

- Data Risk: No repo-truth data loss; the failure is diagnostic/output reliability.

- Security/Compliance: No security exposure observed; the issue is CLI robustness and proof-lane availability.

- Invariant Violated: Diagnostic benchmark proof must be available without optional warm-cache dependencies, and CLI JSON producers must not print tracebacks for normal downstream pipe closure.

- Workaround: Pass --cache-profile cold for diagnostic benchmarks and avoid piping JSON to early-closing consumers.

- Root Cause: The diagnostic benchmark profile inherited a warm-cache default, and the Context Engine CLI entrypoint did not catch BrokenPipeError/ConnectionResetError at the top-level command boundary.

- Solution: Default diagnostic benchmark runs to cold cache unless warm is explicitly requested, and wrap the Context Engine CLI main entrypoint so closed stdout pipes exit cleanly.

- Rollback/Forward Fix: Forward fix in 0.1.14; no rollback required.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_context_engine_turn_cli.py tests/unit/runtime/test_odylith_benchmark_runner.py::test_diagnostic_profile_keeps_public_pair_packet_only; PYTHONPATH=src python -m odylith.cli context-engine benchmark --profile diagnostic --limit 5 --no-write-report; set -o pipefail; PYTHONPATH=src python -m odylith.cli context-engine benchmark --profile diagnostic --limit 1 --no-write-report --json | head -n 1 >/dev/null.

- Prevention: Keep diagnostic benchmark defaults dependency-light; keep closed-pipe behavior covered by a CLI regression test.

- Agent Guardrails: Do not treat benchmark proof commands as healthy if they require optional source-local dependencies unrelated to the diagnostic claim.

- Preflight Checks: Run the diagnostic benchmark in source-local posture and with an early-closing pipe before release.

- Regression Tests Added: tests/unit/runtime/test_odylith_context_engine_turn_cli.py::test_context_engine_cli_exits_cleanly_when_stdout_pipe_closes; tests/unit/runtime/test_odylith_benchmark_runner.py::test_diagnostic_profile_keeps_public_pair_packet_only.

- Monitoring Updates: Context Engine status and benchmark summary now remain the monitoring surfaces; no external alerting needed.

- Version/Build: 0.1.14 candidate

- Config/Flags: diagnostic benchmark default cache profile: cold; explicit --cache-profile warm still supported.

- Customer Comms: No public customer communication required unless the diagnostic benchmark failure was seen in a consumer support session.

- Related Incidents/Bugs: Related to prior benchmark shell hangup and BrokenPipe noise records, but this is a distinct context-engine diagnostic output failure.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.14

- Public Response: pending

- Code References: - src/odylith/runtime/context_engine/odylith_context_engine.py
- src/odylith/runtime/evaluation/odylith_benchmark_runner.py
