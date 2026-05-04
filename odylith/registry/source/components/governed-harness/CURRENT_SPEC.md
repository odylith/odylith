# Governed Harness
Last updated: 2026-05-03


## Overview

Governed Harness is the product-owned turn control layer for normal Odylith
consumer prompts, host adapters, tool checks, finalization checks, and
benchmark measurement. It owns the Turn Gate decision contract that converts
grounded Context Engine evidence, Execution Engine admissibility, Proof State
claim tiers, and governance-surface hints into a host-consumable decision,
execution capsule, and receipt.

## Boundary

- **Logical boundary**: Turn Gate classification, evidence sufficiency,
  execution-capsule construction, tool-call admission, stop/finalization claim
  checks, and harness receipts.
- **Evidence anchor**: `src/odylith/runtime/governed_harness/`
- **Kind**: runtime
- **Status**: active
- **Evidence tier**: manifest

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History

- 2026-05-03: Registered `governed-harness` through `odylith component register`. (Plan: [B-118](odylith/radar/radar.html?view=plan&workstream=B-118))

## Contract

Governed Harness exposes a stable CLI and Python API:

- `odylith turn-gate decide --repo-root . --host <host> --mode observe|advise|enforce --prompt-json - --json`
- `odylith turn-gate tool-check --repo-root . --host <host> --decision-id <id> --tool-input-json - --json`
- `odylith turn-gate stop-check --repo-root . --host <host> --decision-id <id> --transcript <path> --json`
- Python APIs: `decide_turn(...)`, `check_tool(...)`, `check_stop(...)`, and
  `non_mutating_completion_admitted(...)`.

The core serializable payloads are `TurnGateDecision`,
`EvidenceGateReport`, `ExecutionCapsule`, `ToolGateDecision`, and
`HarnessReceipt`. A benchmark row may count non-mutating closure only when the
receipt source is `product_turn_gate`, the decision type is
`early_exit_proof`, and the write set is empty.

## Dependencies

- Upstream: Context Engine evidence packets, Execution Engine admissibility and
  validation posture, Proof State claim-tier truth, Registry component truth,
  Casebook/Radar/Atlas/Compass governance signals, Discipline hard laws, and
  host capability metadata.
- Downstream: host hooks and SDK adapters, benchmark live execution,
  benchmark publication reports, completion-claim guards, tool firewalls, and
  release migration proof.

## Test Coverage

- `tests/unit/runtime/test_turn_gate.py`
- `tests/unit/test_cli.py::test_turn_gate_decide_cli_emits_product_receipt`
- `tests/unit/runtime/test_odylith_benchmark_live_execution.py::test_run_live_scenario_uses_turn_gate_early_exit_proof`
