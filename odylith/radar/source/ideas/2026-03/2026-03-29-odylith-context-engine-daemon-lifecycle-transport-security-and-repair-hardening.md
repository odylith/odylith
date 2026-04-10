---
status: finished
idea_id: B-014
title: Context Engine Daemon Lifecycle, Transport Security, and Repair Hardening
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: Odylith Context Engine daemon lifecycle, local transport trust boundary, repair reset-local-state flow, runtime watcher cleanup, daemon regression proof
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith cannot claim disciplined local acceleration if its daemon lifecycle and transport trust model drift across two client paths or if repair can orphan background processes. Closing that gap hardens both the product security posture and the local operator experience without changing the public coding workflow, and the risk is high enough that it should be finished immediately once found.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-context-engine-daemon-lifecycle-transport-security-and-repair-hardening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001
workstream_blocks:
related_diagram_ids: D-002,D-018,D-020
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith still had one dangerous split in its local daemon contract. The
CLI-side Context Engine client was hardened, but the store-side client still
trusted stale pid/socket state, did not forward the daemon auth token, and
accepted TCP transport hints more loosely than the runtime contract intended.
The repair reset-local-state path also deleted runtime files without first
stopping a live daemon.

## Customer
- Primary: Odylith maintainers and consumers relying on the local Context
  Engine daemon to accelerate grounded coding work safely.
- Secondary: Odylith operators debugging workstation process lists who need the
  product to fail closed on daemon residue instead of quietly weakening trust.

## Opportunity
If Odylith treats daemon lifecycle, local transport trust, and repair cleanup
as one shared security-sensitive contract, it can prevent process-leak
recurrence, stop trusting stale local transport state, and keep local recovery
credible without changing the user-facing coding workflow.

## Proposed Solution
Bring the store-side daemon client up to the same trust contract as the
CLI-side client, enforce loopback-only TCP transport reuse, keep repair from
deleting runtime files underneath a live daemon, and prove the result with
focused daemon regression tests plus a broader runtime/browser suite.

## Scope
- unify daemon owner-pid and metadata fallback between the CLI-side and
  store-side daemon clients
- forward auth tokens on store-side daemon requests
- reject non-loopback or mismatched TCP transport hints
- stop live Context Engine daemons before reset-local-state cleanup
- keep stubborn Watchman watcher subprocesses from surviving close
- add focused daemon hardening tests and rerun a broader runtime/browser suite
- update the Context Engine spec and guidance to lock the contract in place

## Non-Goals
- changing the public `odylith context-engine` command surface
- redesigning the daemon into a hosted or multi-user service
- solving unrelated Python processes not owned by Odylith

## Risks
- a stricter daemon transport check could reject a previously tolerated but
  unhealthy local daemon state
- repair hardening could regress local recovery if it mishandles daemon stop
  semantics

## Dependencies
- `B-001` established Odylith-owned runtime and governance truth
- [2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md](../../../casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md)
  already hardened detached autospawn and defines the leak class this slice
  must not reopen

## Success Metrics
- store-side daemon reuse follows the same auth and liveness contract as the
  CLI-side client
- non-loopback TCP transport hints are rejected
- repair/reset-local-state stops a live daemon before cleanup
- focused daemon hardening tests stay green
- broader runtime plus headless browser proof stays green

## Validation
- `python -m py_compile src/odylith/runtime/context_engine/odylith_context_engine.py src/odylith/runtime/context_engine/odylith_context_engine_store.py src/odylith/install/repair.py tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py tests/unit/install/test_repair.py`

## Rollout
Ship as an internal daemon-contract hardening slice. No public migration is
needed; the product behavior should simply get safer and more reliable.

## Why Now
Odylith is explicitly selling local acceleration, memory, and governance
discipline. A split daemon trust model undermines all three.

## Product View
If Odylith leaves behind background Python processes or quietly trusts stale
daemon artifacts, it looks sloppy and unsafe. That is unacceptable for a tool
that expects maintainers to trust it inside their repo.

## Impacted Components
- `odylith-context-engine`
- `odylith`

## Interface Changes
- none in the public CLI
- stricter local daemon reuse semantics for non-in-process transport

## Migration/Compatibility
- additive hardening only
- older unhealthy daemon artifacts may now fail closed instead of being reused

## Test Strategy
- add direct daemon-lifecycle and local transport tests
- rerun broader runtime and headless browser proof to catch cross-surface drift

## Open Questions
- should Odylith eventually expose an explicit daemon-audit or daemon-stop-all
  operator command for multi-repo local debugging
