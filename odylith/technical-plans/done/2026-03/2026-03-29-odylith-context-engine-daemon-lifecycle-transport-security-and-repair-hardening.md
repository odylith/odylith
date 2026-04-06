Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-014

Goal: Eliminate remaining local daemon leak and trust gaps in Odylith’s
Context Engine without regressing runtime behavior, browser surfaces, or local
operator recovery.

Assumptions:
- The most urgent issue is not a single leaked process observed live today, but
  the remaining contract gap that could still allow leak recurrence or weaker
  local daemon trust.
- The existing daemon server contract is the right baseline; the store-side
  client and repair path need to match it.
- Focused daemon tests plus a widened runtime/browser suite are enough proof
  for this slice.

Constraints:
- Do not regress the public `odylith context-engine` command surface.
- Do not introduce stale Compass or surface regressions while hardening the
  daemon layer.
- Keep the scope local-first and workstation-safe; do not expand into hosted
  daemon behavior.

Reversibility: Reverting this slice restores the looser daemon reuse and repair
behavior, with no data migration required.

Boundary Conditions:
- Scope includes daemon client parity, loopback-only TCP transport acceptance,
  repair cleanup hardening, focused tests, and source-truth closeout.
- Scope excludes unrelated non-Odylith Python processes and broader runtime
  architecture redesign.

Related Bugs:
- [2026-03-29-odylith-context-engine-daemon-transport-auth-and-repair-hardening-gap.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-odylith-context-engine-daemon-transport-auth-and-repair-hardening-gap.md)
- [2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md)

## Context/Problem Statement
- [x] The store-side daemon client still carried drift from the hardened
  CLI-side daemon client.
- [x] Store-side reuse could trust stale or mismatched daemon artifacts.
- [x] TCP transport hints were not constrained tightly enough to the local
  loopback trust boundary.
- [x] Reset-local-state cleanup could delete runtime files while a live daemon
  still existed.
- [x] The product spec and guidance needed to document the stricter daemon
  contract.

## Success Criteria
- [x] Store-side daemon reuse now uses the same metadata and auth-token
  contract as the CLI-side client.
- [x] Non-loopback or mismatched TCP transport hints are rejected.
- [x] Reset-local-state stops the live daemon before cleanup.
- [x] Focused daemon hardening tests exist and pass.
- [x] Broader runtime and browser proof stays green.
- [x] Odylith source truth records the slice as closed work, not ad hoc drift.

## Non-Goals
- [x] Changing the public CLI surface.
- [x] Turning the local daemon into a networked multi-user service.
- [x] Owning unrelated Python processes started by other local tooling.

## Impacted Areas
- [x] [odylith_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [repair.py](/Users/freedom/code/odylith/src/odylith/install/repair.py)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [ODYLITH_CONTEXT_ENGINE.md](/Users/freedom/code/odylith/odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md)
- [x] [test_odylith_context_engine_daemon_hardening.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py)
- [x] [test_repair.py](/Users/freedom/code/odylith/tests/unit/install/test_repair.py)

## Traceability
### Runtime And Repair
- [x] [odylith_context_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [repair.py](/Users/freedom/code/odylith/src/odylith/install/repair.py)

### Product Contract
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [ODYLITH_CONTEXT_ENGINE.md](/Users/freedom/code/odylith/odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md)

### Tests And Proof
- [x] [test_odylith_context_engine_daemon_hardening.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py)
- [x] [test_repair.py](/Users/freedom/code/odylith/tests/unit/install/test_repair.py)
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)

## Risks & Mitigations

- [x] Risk: stricter daemon validation could reject a previously tolerated
  - [ ] Mitigation: TODO (add explicit mitigation).
  daemon state and surprise operators.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [x] Mitigation: fail closed only on clearly unhealthy transport hints and
    preserve standalone fallback behavior.
- [x] Risk: repair cleanup could regress if daemon shutdown becomes brittle.
  - [x] Mitigation: terminate, wait, escalate to kill, and keep direct unit
    coverage on the stubborn-process path.

## Validation/Test Plan
- [x] `python -m py_compile src/odylith/runtime/context_engine/odylith_context_engine.py src/odylith/runtime/context_engine/odylith_context_engine_store.py src/odylith/install/repair.py tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py tests/unit/install/test_repair.py`
- [x] live process audit showed no active `odylith-context-engine` daemon
  residue after the patch set on this machine
- [x] `git diff --check`

## Rollout/Communication
- [x] Ship as a local daemon hardening update with no public migration.
- [x] Update the Context Engine spec and guidance to keep the contract visible.
- [x] Record the bug, backlog, and done plan together.

## Dependencies/Preconditions
- [x] The prior autospawn leak fix already introduced daemon metadata and idle
  semantics that this slice could extend instead of replacing.
- [x] Runtime/browser suites were already stable enough to use as regression
  proof.

## Edge Cases
- [x] Live owner pid can fall back from metadata when the pid file is missing.
- [x] TCP transport artifacts with mismatched pid or non-loopback host fail
  closed.
- [x] Stubborn Watchman subprocesses are killed instead of surviving close.
- [x] Reset-local-state stops a live daemon before deleting runtime files.

## Open Questions/Decisions
- [x] Decision: keep the daemon local-only and harden the existing contract
  rather than expanding networked behavior.
- [x] Decision: treat the store-side client drift as a real product bug, not a
  mere internal cleanup, because it directly affects leak recurrence and local
  security posture.

## Current Outcome
- The CLI-side and store-side Context Engine daemon clients now share the same
  owner, auth, and transport trust model.
- Local TCP transport reuse is loopback-only and rejects mismatched daemon
  ownership hints.
- Repair/reset-local-state no longer deletes runtime files underneath a live
  daemon.
- Focused daemon hardening tests and the broader runtime/browser suite stayed
  green, so Odylith’s local acceleration path is safer without sacrificing
  product stability.
